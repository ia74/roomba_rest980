"""The vacuum."""

import asyncio
import logging

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .LegacyCompatibility import createExtendedAttributes

_LOGGER = logging.getLogger(__name__)

SUPPORT_ROBOT = (
    VacuumEntityFeature.START
    | VacuumEntityFeature.RETURN_HOME
    | VacuumEntityFeature.CLEAN_SPOT
    | VacuumEntityFeature.MAP
    | VacuumEntityFeature.SEND_COMMAND
    | VacuumEntityFeature.STATE
    | VacuumEntityFeature.STOP
    | VacuumEntityFeature.PAUSE
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Create the vacuum."""
    async_add_entities(
        [RoombaVacuum(hass, entry.runtime_data.local_coordinator, entry)]
    )


PENDING_UPLOAD = 39
NOT_AVAILABLE = 0

class RoombaVacuum(CoordinatorEntity, StateVacuumEntity):
    """The Rest980 controlled vacuum."""



    def __init__(self, hass: HomeAssistant, coordinator, entry: ConfigEntry) -> None:
        """Setup the robot."""
        super().__init__(coordinator)
        self.hass = hass
        self._entry: ConfigEntry = entry
        self._attr_supported_features = SUPPORT_ROBOT
        self._attr_unique_id = f"{entry.unique_id}_vacuum"
        self._attr_name = entry.title

    def _handle_coordinator_update(self):
        """Update all attributes."""
        data = self.coordinator.data or {}
        status = data.get("cleanMissionStatus", {})
        cycle = status.get("cycle")
        phase = status.get("phase")
        not_ready = status.get("notReady")

        self._attr_activity = VacuumActivity.IDLE
        if cycle == "none" and not_ready == PENDING_UPLOAD:
            self._attr_activity = VacuumActivity.IDLE
        
        if not_ready and not_ready > NOT_AVAILABLE: # Not ready, and code is an error
            self._attr_activity = VacuumActivity.ERROR
        
        if cycle in {"clean", "quick", "spot", "train"} or phase in {"hwMidMsn"}:
            self._attr_activity = VacuumActivity.CLEANING
        
        if phase in {"stop", "pause"}:
            self._attr_activity = VacuumActivity.PAUSED
        
        if cycle in {"evac", "dock"} or phase in {
            "charge",
        }:  # Emptying Roomba Bin to Dock, Entering Dock
            self._attr_activity = VacuumActivity.DOCKED
        
        if phase in {
            "hmUsrDock",
            "hmPostMsn",
        }:  # Sent Home, Mid Dock, Final Dock
            self._attr_activity = VacuumActivity.RETURNING

        self._attr_available = data != {}
        self._attr_extra_state_attributes = createExtendedAttributes(self)
        self._async_write_ha_state()


