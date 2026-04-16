"""Data update coordinator for Roomba REST980."""

import asyncio
import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import (
    ConfigEntryAuthFailed,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .misc.CloudApi import iRobotCloudApi, AuthenticationError, CloudApiError
from .const import DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class RoombaDataCoordinator(DataUpdateCoordinator):
    """Data coordinator for Roomba REST980 integration."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="rest980 API data",
            config_entry=config_entry,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.session = async_get_clientsession(hass)  # Use HA’s shared session
        self.url = config_entry.data["base_url"]

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with asyncio.timeout(10):
                async with self.session.get(f"{self.url}/api/local/info/state") as resp:
                    resp.raise_for_status()
                    return await resp.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err


class RoombaCloudCoordinator(DataUpdateCoordinator):
    """Data coordinator for Roomba REST980 integration."""

    api: iRobotCloudApi

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="iRobot Cloud API data",
            config_entry=config_entry,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.username = config_entry.data["irobot_username"]
        self.password = config_entry.data["irobot_password"]
        self.session = async_get_clientsession(hass)
        self.api = iRobotCloudApi(self.username, self.password, self.session)

    async def _async_setup(self):
        try:
            await self.api.authenticate()
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(f"Cloud API error: {err}") from err
        except CloudApiError as err:
            raise ConfigEntryNotReady(f"Cloud API error: {err}") from err

    async def _async_update_data(self):
        try:
            async with asyncio.timeout(10):
                return await self.api.get_all_robots_data()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
