"""The vacuum."""

import asyncio
import logging
from typing import Any

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.vacuum import Segment

from .const import DOMAIN
from .LegacyCompatibility import createExtendedAttributes

_LOGGER = logging.getLogger(__name__)

# HA 2026.3+ area cleaning support (Segment dataclass + CLEAN_AREA feature flag)
try:
    from homeassistant.components.vacuum import Segment

    _HAS_CLEAN_AREA = hasattr(VacuumEntityFeature, "CLEAN_AREA")
except ImportError:
    _HAS_CLEAN_AREA = False

SUPPORT_ROBOT = (
    VacuumEntityFeature.START
    | VacuumEntityFeature.RETURN_HOME
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
        self._segment_map: dict[str, dict[str, Any]] = {}

    def _handle_coordinator_update(self):
        """Update all attributes."""
        data = self.coordinator.data or {}
        status = data.get("cleanMissionStatus", {})
        bin_data = data.get("bin") or {}
        cycle = status.get("cycle")
        phase = status.get("phase")
        not_ready = status.get("notReady")
        paused_activity = getattr(VacuumActivity, "PAUSED", VacuumActivity.IDLE)

        self._attr_activity = VacuumActivity.IDLE
        if cycle == "none" and not_ready == 39:
            self._attr_activity = VacuumActivity.IDLE
        elif not_ready and not_ready > 0:
            self._attr_activity = VacuumActivity.ERROR
        elif phase in {"pause", "stop"}:
            self._attr_activity = paused_activity
        elif phase in {
            "hmUsrDock",
            "hmPostMsn",
        }:  # Sent Home, Mid Dock, Final Dock
            self._attr_activity = VacuumActivity.RETURNING
        elif cycle in ["evac", "dock"] or phase in {
            "charge",
        }:  # Emptying Roomba Bin to Dock, Entering Dock
            self._attr_activity = VacuumActivity.DOCKED
        elif cycle in ["clean", "quick", "spot", "train"] or phase in {"hwMidMsn"}:
            self._attr_activity = VacuumActivity.CLEANING

        self._attr_available = data != {}
        self._attr_battery_level = data.get("batPct")

        extra_attributes = createExtendedAttributes(self)
        extra_attributes.update(
            {
                "battery_level": self._attr_battery_level,
                "bin_full": bin_data.get("full"),
                "bin_present": bin_data.get("present"),
            }
        )
        self._attr_extra_state_attributes = extra_attributes
        self._async_write_ha_state()

    @property
    def battery_level(self) -> int | None:
        """Return the vacuum battery level as expected by HA vacuum cards."""
        return self.coordinator.data.get("batPct") if self.coordinator.data else None

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
        _LOGGER.warrning("async_clean_spot kwargs: %s", kwargs)

    async def async_start(self):
        """Start cleaning floors, check if any are selected or just clean everything."""
        data = self.coordinator.data or {}
        status = data.get("cleanMissionStatus", {})
        phase = status.get("phase")
        cycle = status.get("cycle")

        if phase in {"stop", "pause"} or (cycle == "none" and phase == "resume"):
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
            params = self._build_clean_params()

            # Check if we have room selection switches available
            selected_rooms = list(self._entry.runtime_data.rooms_to_clean.values())
            _LOGGER.warning(selected_rooms)
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
                "action": "pause",
                "base_url": self._entry.data["base_url"],
            },
            blocking=True,
        )
        await asyncio.sleep(2)
        await self.hass.services.async_call(
            DOMAIN,
            "rest980_action",
            service_data={
                "action": "dock",
                "base_url": self._entry.data["base_url"],
            },
            blocking=True,
        )

    # --- HA 2026.3 vacuum area cleaning support ---

    def _get_cloud_robot_data(self) -> dict[str, Any] | None:
        """Return cloud data for this robot, or None if unavailable."""
        runtime_data = self._entry.runtime_data
        if (
            not runtime_data.cloud_coordinator
            or not runtime_data.cloud_coordinator.data
            or not runtime_data.robot_blid
        ):
            return None
        return runtime_data.cloud_coordinator.data.get(runtime_data.robot_blid)

    def _build_clean_params(self) -> dict[str, Any]:
        """Build Roomba cleaning parameters from current mode selections."""
        runtime_data = self._entry.runtime_data

        if runtime_data.vacuum_mode == "vacuum":
            operating_mode = 2
        else:
            operating_mode = 6

        if runtime_data.mop_mode == "low":
            wet_mode = 1
        elif runtime_data.mop_mode == "medium":
            wet_mode = 2
        else:
            wet_mode = 3

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

        robot_data = self._get_cloud_robot_data()
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
        """Clean the specified segments.

        Segment IDs are composite strings produced by async_get_segments
        in the format ``region_id:type:pmap_id``.  They are grouped by
        pmap_id and sent to the Roomba REST980 cleanRoom endpoint.
        """
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
                service_data={
                    "payload": payload,
                    "base_url": self._entry.data["base_url"],
                },
                blocking=True,
            )
