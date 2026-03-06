"""The vacuum."""

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
    #| VacuumEntityFeature.CLEAN_SPOT
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
    vacuum = RoombaVacuum(hass, entry.runtime_data.local_coordinator, entry)
    async_add_entities(
        [vacuum]
    )
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})
    hass.data[DOMAIN][entry.entry_id]["vacuum"] = vacuum


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
        if cycle == "none" and not_ready == 39:
            self._attr_activity = VacuumActivity.IDLE
        if not_ready and not_ready > 0:
            self._attr_activity = VacuumActivity.ERROR
        if cycle in ["clean", "quick", "spot", "train"] or phase in {"hwMidMsn"}:
            self._attr_activity = VacuumActivity.CLEANING
        if cycle in ["evac", "dock"] or phase in {
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

    @property
    def device_info(self) -> DeviceInfo:
        """Return the Roomba's device information."""
        data = self.coordinator.data or {}
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.unique_id)},
            name=data.get("name", "Roomba"),
            manufacturer="iRobot",
            model="Roomba",
            model_id=data.get("sku"),
            sw_version=data.get("softwareVer"),
        )

    async def async_clean_spot(self, **kwargs):
        """Spot clean."""

    async def async_start(self):
        """Start cleaning floors, check if any are selected or just clean everything."""
        _LOGGER.warning("chce zaczac sprzatac")
        data = self.coordinator.data or {}
        if data.get("phase") == "stop":
            await self.hass.services.async_call(
                DOMAIN,
                "rest980_action",
                service_data={
                    "action": "resume",
                    "base_url": self._entry.data["base_url"],
                },
                blocking=True,
            )
            return

        try:
            # Get selected rooms from switches (if available)
            payload = []
            regions = []

            # Check if we have room selection switches available
            selected_rooms = list(self._entry.runtime_data.rooms_to_clean.values())
            _LOGGER.warning(selected_rooms)
            if self._entry.runtime_data.vacuum_mode=="vacuum":
                operatingMode=2
            else:
                operatingMode=6
                
            if self._entry.runtime_data.mop_mode=="low":
                wetMode=1
            elif self._entry.runtime_data.mop_mode=="medium":
                wetMode=2
            else:
                wetMode=3
               
            params={
                    "noAutoPasses":True,
                    "operatingMode": operatingMode,
                    "padWetness": {
                        "disposable": wetMode,
                        "reusable": wetMode,
                    },
                    "twoPass": False,
                    "swScrub": 0,
            }
            # If we have specific regions selected, use targeted cleaning
            if selected_rooms:
                for room_id in selected_rooms:
                    regions.append({
                        "params":params,
                        "type": "rid",
                        "region_id": room_id,
                    })
                    
                payload = {
                    "ordered": 1,
                    "pmap_id": self._attr_extra_state_attributes.get("pmap0_id", ""),
                    "regions": regions,
                }
                self._entry.runtime_data.rooms_to_clean.clear()
                _LOGGER.warning(payload)
                
                await self.hass.services.async_call(
                    DOMAIN,
                    "rest980_clean",
                    service_data={
                        "payload": payload,
                        "base_url": self._entry.data["base_url"],
                    },
                    blocking=True,
                )
            else:
                # No specific rooms selected, start general clean
                _LOGGER.info("Starting general cleaning (no specific rooms selected)")
                await self.hass.services.async_call(
                    DOMAIN,
                    "rest980_clean",
                    service_data={
                        #"payload": {"action": "start"},
                        "payload":{"params": params},
                        "base_url": self._entry.data["base_url"],
                    },
                    blocking=True,
                )
        except (KeyError, AttributeError, ValueError, Exception) as e:
            _LOGGER.error("Failed to start cleaning due to configuration error: %s", e)

    async def async_stop(self) -> None:
        """Stop the action."""
        await self.hass.services.async_call(
            DOMAIN,
            "rest980_action",
            service_data={
                "action": "stop",
                "base_url": self._entry.data["base_url"],
            },
            blocking=True,
        )

    async def async_pause(self):
        """Pause the current action."""
        await self.hass.services.async_call(
            DOMAIN,
            "rest980_action",
            service_data={
                "action": "pause",
                "base_url": self._entry.data["base_url"],
            },
            blocking=True,
        )

    async def async_return_to_base(self):
        """Calls the Roomba back to its dock."""
        await self.hass.services.async_call(
            DOMAIN,
            "rest980_action",
            service_data={
                "action": "dock",
                "base_url": self._entry.data["base_url"],
            },
            blocking=True,
        )
