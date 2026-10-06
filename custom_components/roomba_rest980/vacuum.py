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

try:
    from homeassistant.components.vacuum import Segment

    _HAS_CLEAN_AREA = hasattr(VacuumEntityFeature, "CLEAN_AREA")
except ImportError:
    _HAS_CLEAN_AREA = False

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
if _HAS_CLEAN_AREA:
    SUPPORT_ROBOT = SUPPORT_ROBOT | VacuumEntityFeature.CLEAN_AREA


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
        self._segment_map: dict[str, dict[str, Any]] = {}

    def _handle_coordinator_update(self):
        """Update all attributes."""
        data = self.coordinator.data or {}
        status = data.get("cleanMissionStatus", {})
        bin_data = data.get("bin") or {}
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
        extra_attributes = createExtendedAttributes(self)
        extra_attributes.update(
            {
                # HA's vacuum entity no longer defines _attr_battery_level; read it from the payload.
                "battery_level": data.get("batPct"),
                "bin_full": bin_data.get("full"),
                "bin_present": bin_data.get("present"),
            }
        )
        self._attr_extra_state_attributes = extra_attributes
        self._async_write_ha_state()

    def _build_clean_params(self) -> dict[str, Any]:
        """Build Roomba cleaning parameters from current mode selections."""
        runtime_data = self._entry.runtime_data

        if runtime_data.vacuum_mode == "vacuum":
            operating_mode = OPERATING_MODE_VACUUM
        else:
            operating_mode = OPERATING_MODE_MOP

        if runtime_data.mop_mode == "low":
            wet_mode = MOP_MODE_LOW
        elif runtime_data.mop_mode == "medium":
            wet_mode = MOP_MODE_MEDIUM
        else:
            wet_mode = MOP_MODE_HIGH

        return {
            "noAutoPasses": True,
            "operatingMode": operating_mode,
            "padWetness": {
                "disposable": wet_mode,
                "reusable": wet_mode,
            },
            "twoPass": False,
            "swScrub": 0,
        }

    async def async_get_segments(self) -> list:
        """Return the cleanable segments reported by the vacuum.

        Each Roomba region and zone from the active persistent map is
        returned as a Segment with a composite ID that encodes the
        region_id, type (rid/zid), and pmap_id so that
        async_clean_segments can reconstruct the Roomba REST payload.
        """
        if not _HAS_CLEAN_AREA:
            return []

        segments: list[Segment] = []
        self._segment_map.clear()

        robot_data = self._entry.runtime_data.cloud_coordinator.data
        if not robot_data or "pmaps" not in robot_data:
            return segments

        for pmap in robot_data["pmaps"]:
            try:
                details = pmap["active_pmapv_details"]
                pmap_id = details["active_pmapv"]["pmap_id"]
                map_name = details["map_header"]["name"]

                for region in details.get("regions", []):
                    seg_id = f"{region['id']}:rid:{pmap_id}"
                    name = region.get("name") or "Unnamed Room"
                    segments.append(
                        Segment(id=seg_id, name=name, group=map_name)
                    )
                    self._segment_map[seg_id] = {
                        "type": "rid",
                        "region_id": region["id"],
                        "pmap_id": pmap_id,
                    }

                for zone in details.get("zones", []):
                    seg_id = f"{zone['id']}:zid:{pmap_id}"
                    name = zone.get("name") or "Unnamed Zone"
                    segments.append(
                        Segment(id=seg_id, name=name, group=map_name)
                    )
                    self._segment_map[seg_id] = {
                        "type": "zid",
                        "region_id": zone["id"],
                        "pmap_id": pmap_id,
                    }
            except (KeyError, TypeError) as err:
                _LOGGER.warning("Failed to parse pmap segments: %s", err)

        _LOGGER.debug("Discovered %d vacuum segments", len(segments))
        return segments

    async def async_clean_segments(
        self, segment_ids: list[str], **kwargs: Any
    ) -> None:
        if not segment_ids:
            return

        # Ensure the segment map is populated
        if not self._segment_map:
            await self.async_get_segments()

        params = self._build_clean_params()

        regions_by_pmap: dict[str, list[dict[str, Any]]] = {}
        for seg_id in segment_ids:
            seg_data = self._segment_map.get(seg_id)
            if not seg_data:
                parts = seg_id.split(":")
                if len(parts) != 3:
                    _LOGGER.warning("Unknown segment ID: %s", seg_id)
                    continue
                seg_data = {
                    "region_id": parts[0],
                    "type": parts[1],
                    "pmap_id": parts[2],
                }

            region = {
                "type": seg_data["type"],
                "region_id": seg_data["region_id"],
                "params": params,
            }
            regions_by_pmap.setdefault(seg_data["pmap_id"], []).append(region)

        for pmap_id, regions in regions_by_pmap.items():
            payload = {
                "ordered": 1,
                "pmap_id": pmap_id,
                "regions": regions,
            }
            _LOGGER.info(
                "Starting area clean: pmap=%s, regions=%s", pmap_id, regions
            )
            await self.hass.services.async_call(
                DOMAIN,
                "rest980_clean",
                payload,
                blocking=True,
            )

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

    async def call_rest980_action(self, action):
        await self.hass.services.async_call(
            DOMAIN,
            "rest980_action",
            service_data={
                "action": action,
                "base_url": self._entry.data["base_url"],
            },
            blocking=True,
        )

    async def async_clean_spot(self, **kwargs):
        """Spot clean."""
        #NOTE: I believe this is a cloud method

    async def async_start(self):
        """Start cleaning floors, check if any are selected or just clean everything."""
        data = self.coordinator.data or {}
        status = data.get("cleanMissionStatus", {})
        phase = status.get("phase")
        cycle = status.get("cycle")

        if phase in {"stop", "pause"} or (cycle == "none" and phase == "resume"):
            await self.call_rest980_action("resume")
            return

        try:
            # Get selected rooms from switches (if available)
            payload = []
            regions = []

            # Check if we have room selection switches available
            domain_data = self._entry.runtime_data.switched_rooms
            selected_rooms = []

            # Find all room switches that are turned on
            for key, entity in domain_data.items():
                if (
                    key.startswith("select.")
                    and hasattr(entity, "current_option")
                    and entity.current_option != "Don't Clean"
                ):
                    selected_rooms.append(entity)

            # If we have specific rooms selected, use targeted cleaning
            if selected_rooms:
                # Build regions list from selected rooms
                regions = [
                    room.get_region_json()
                    for room in selected_rooms
                    if hasattr(room, "get_region_json")
                ]

            # If we have specific regions selected, use targeted cleaning
            if regions:
                payload = {
                    "ordered": 1,
                    "pmap_id": selected_rooms[0].pmap_id,
                    "regions": regions,
                }

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
                        "payload": {"action": "start"},
                        "base_url": self._entry.data["base_url"],
                    },
                    blocking=True,
                )
            
            # Deselect rooms
            for room in selected_rooms:
                await room.async_select_option("Don't Clean")
        except (KeyError, AttributeError, ValueError, Exception) as e:
            _LOGGER.error("Failed to start cleaning due to configuration error: %s", e)

    async def async_stop(self) -> None:
        """Stop the action."""
        await self.call_rest980_action("stop")

    async def async_pause(self):
        """Pause the current action."""
        await self.call_rest980_action("pause")

    async def async_return_to_base(self):
        """Calls the Roomba back to its dock."""
        await self.call_rest980_action("pause")
        await asyncio.sleep(2)
        await self.call_rest980_action("dock")

    async def async_send_command(
        self,
        command: str,
        params: dict[str, any] | list[any] | None = None,
        **kwargs: any,
    ) -> None:
        """Send a command to a vacuum cleaner."""

        if command == "start":
            regions = [
                {
                    "type": "rid",
                    "region_id": region.get("region_id"),
                    "params": {
                        "noAutoPasses": False,
                        "twoPass": region.get("params", {}).get("twoPass"),
                    },
                }
                for region in params.get("regions", [])
            ]

            if regions:
                payload = {
                    "ordered": 1,
                    "pmap_id": self._attr_extra_state_attributes.get("pmap0_id", ""),
                    "regions": regions,
                }
            else:
                payload = {"action": "start"}

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
            raise NotImplementedError(f"Command not implemented: {command}")
