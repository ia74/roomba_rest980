"""Roomba integration using an external Rest980 server."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN
from .coordinator import RoombaDataCoordinator, RoombaCloudCoordinator
import voluptuous as vol

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setup Roombas with the Rest980 base url."""
    coordinator = RoombaDataCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id + "_coordinator"] = coordinator
    hass.data[DOMAIN][entry.entry_id + "_blid"] = "unknown"

    # Set up cloud coordinator if enabled
    if entry.data["cloud_api"]:
        cc = RoombaCloudCoordinator(hass, entry)
        hass.data[DOMAIN][entry.entry_id + "_cloud"] = cc

        # Start background task for cloud setup and BLID matching
        hass.async_create_task(_async_setup_cloud(hass, entry, coordinator, cc))
    else:
        hass.data[DOMAIN][entry.entry_id + "_cloud"] = {}

    # Register services
    await _async_register_services(hass)

    # Forward platforms; create tasks but await to ensure no failure?
    await hass.config_entries.async_forward_entry_setups(entry, ["vacuum", "sensor"])

    return True


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services."""

    async def handle_vacuum_clean(call: ServiceCall) -> None:
        """Handle vacuum clean service call."""
        try:
            payload = call.data["payload"]
            base_url = call.data["base_url"]

            session = async_get_clientsession(hass)
            async with session.post(
                f"{base_url}/api/local/action/cleanRoom",
                headers={"content-type": "application/json"},
                json=payload,
            ) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to send clean command: %s", response.status)
                else:
                    _LOGGER.debug("Clean command sent successfully")
        except Exception as e:  # pylint: disable=broad-except
            _LOGGER.error("Error sending clean command: %s", e)

    async def handle_action(call: ServiceCall) -> None:
        """Handle action service call."""
        try:
            action = call.data["action"]
            base_url = call.data["base_url"]

            session = async_get_clientsession(hass)
            async with session.get(
                f"{base_url}/api/local/action/{action}",
            ) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to send clean command: %s", response.status)
                else:
                    _LOGGER.debug("Action sent successfully")
        except Exception as e:  # pylint: disable=broad-except
            _LOGGER.error("Error sending clean command: %s", e)

    # Register services if not already registered
    if not hass.services.has_service(DOMAIN, "rest980_clean"):
        hass.services.async_register(
            DOMAIN,
            "rest980_clean",
            handle_vacuum_clean,
            vol.Schema({vol.Required("payload"): dict, vol.Required("base_url"): str}),
        )

    if not hass.services.has_service(DOMAIN, "rest980_action"):
        hass.services.async_register(
            DOMAIN,
            "rest980_action",
            handle_action,
            vol.Schema({vol.Required("action"): str, vol.Required("base_url"): str}),
        )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Safely remove Roombas."""
    await hass.config_entries.async_unload_platforms(
        entry, ["vacuum", "sensor", "switch"]
    )
    hass.data[DOMAIN].pop(entry.entry_id + "_coordinator")
    return True


async def _async_setup_cloud(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: RoombaDataCoordinator,
    cloud_coordinator: RoombaCloudCoordinator,
) -> None:
    """Set up cloud coordinator and perform BLID matching in background."""
    try:
        # Refresh cloud data
        await cloud_coordinator.async_config_entry_first_refresh()

        # Perform BLID matching if not already stored
        if "blid" not in entry.data:
            await _async_match_blid(hass, entry, coordinator, cloud_coordinator)

        await hass.config_entries.async_forward_entry_setups(
            entry, ["switch", "button"]
        )

    except Exception as e:  # pylint: disable=broad-except
        _LOGGER.error("Failed to set up cloud coordinator: %s", e)
        # Set empty cloud data so entities can still be created
        hass.data[DOMAIN][entry.entry_id + "_cloud"] = {}


async def _async_match_blid(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: RoombaDataCoordinator,
    cloud_coordinator: RoombaCloudCoordinator,
) -> None:
    """Match local Roomba with cloud robot by comparing device info."""
    try:
        for blid, robo in cloud_coordinator.data.items():
            try:
                # Get cloud robot info
                robot_info = robo.get("robot_info") or {}
                cloud_sku = robot_info.get("sku")
                cloud_sw_ver = robot_info.get("softwareVer")
                cloud_name = robot_info.get("name")

                # Get local robot info
                local_data = coordinator.data or {}
                local_name = local_data.get("name", "Roomba")
                local_sw_ver = local_data.get("softwareVer")
                local_sku = local_data.get("sku")

                # Match robots by SKU, software version, and name
                if (
                    cloud_sku == local_sku
                    and cloud_sw_ver == local_sw_ver
                    and cloud_name == local_name
                ):
                    hass.data[DOMAIN][entry.entry_id + "_blid"] = blid
                    _LOGGER.info("Matched local Roomba with cloud robot %s", blid)
                    break

            except (KeyError, TypeError) as e:
                _LOGGER.debug("Error matching robot %s: %s", blid, e)
        else:
            _LOGGER.warning("Could not match local Roomba with any cloud robot")

    except Exception as e:  # pylint: disable=broad-except
        _LOGGER.error("Error during BLID matching: %s", e)
