"""Buttons needed."""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Create the switches to identify cleanable rooms."""
    coordinator = entry.runtime_data.local_coordinator
    cloudCoordinator = entry.runtime_data.cloud_coordinator
    entities = []

    # Only robots docked to a recognized Clean Base can evac -- same check
    # sensor.py's RoombaCleanBase uses to decide "Not Available" vs a real
    # dock state.
    local_data = coordinator.data or {}
    if (local_data.get("dock") or {}).get("known"):
        entities.append(EmptyBinButton(entry))

    if cloudCoordinator and cloudCoordinator.data:
        blid = entry.runtime_data.robot_blid
        # Get cloud data for the specific robot
        if blid in cloudCoordinator.data:
            cloud_data = cloudCoordinator.data
            # Create button entities from cloud data
            if "favorites" in cloud_data:
                entities.extend(
                    [FavoriteButton(entry, fav) for fav in cloud_data["favorites"]]
                )
    async_add_entities(entities)


class EmptyBinButton(ButtonEntity):
    """A button entity to empty the robot's bin into its Clean Base."""

    _attr_has_entity_name = True
    _attr_name = "Empty Bin"
    _attr_icon = "mdi:delete-restore"

    def __init__(self, entry) -> None:
        """Create the empty bin button."""
        self._entry = entry
        self._attr_unique_id = f"{entry.unique_id}_empty_bin"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.unique_id)},
            "name": entry.title,
            "manufacturer": "iRobot",
        }

    async def async_press(self):
        """Tell the Clean Base to empty the bin."""
        await self.hass.services.async_call(
            DOMAIN,
            "rest980_action",
            service_data={
                "action": "evac",
                "base_url": self._entry.data["base_url"],
            },
        )


class FavoriteButton(ButtonEntity):
    """A button entity to initiate iRobot favorite routines."""

    def __init__(self, entry, data) -> None:
        """Creates a button entity for entries."""
        self._attr_name = f"{data['name']}"
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{data['favorite_id']}"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_extra_state_attributes = data
        self._data = data
        self._attr_icon = "mdi:star"
        self._attr_entity_registry_enabled_default = not data.get("hidden", False)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.unique_id)},
            "name": entry.title,
            "manufacturer": "iRobot",
        }

    async def async_press(self):
        """Send command out to clean with the ID."""
        await self.hass.services.async_call(
            DOMAIN,
            "rest980_clean",
            service_data={
                "base_url": self._entry.data["base_url"],
                "payload": self._data.get("commanddefs")[0],
            },
        )
