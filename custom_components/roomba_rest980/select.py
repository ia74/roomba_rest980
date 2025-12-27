"""Switches needed."""

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, regionTypeMappings, zoneTypeMappings

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Create the switches to identify cleanable rooms."""
    cloudCoordinator = entry.runtime_data.cloud_coordinator
    entities = []
    if cloudCoordinator and cloudCoordinator.data:
        blid = entry.runtime_data.robot_blid
        # Get cloud data for the specific robot
        if blid in cloudCoordinator.data:
            cloud_data = cloudCoordinator.data[blid]
            # Create pmap entities from cloud data
            if "pmaps" in cloud_data:
                for pmap in cloud_data["pmaps"]:
                    try:
                        entities.extend(
                            [
                                CleanRoomPasses(
                                    entry,
                                    region["name"] or "Unnamed Room",
                                    region,
                                    pmap,
                                )
                                for region in pmap["active_pmapv_details"]["regions"]
                            ]
                            + [
                                CleanRoomPasses(
                                    entry,
                                    region["name"] or "Unnamed Zone",
                                    region,
                                    pmap,
                                    True,
                                )
                                for region in pmap["active_pmapv_details"]["zones"]
                            ]
                        )
                    except (KeyError, TypeError) as e:
                        _LOGGER.warning(
                            "Failed to create pmap entity for %s: %s",
                            pmap.get("pmap_id", "unknown"),
                            e,
                        )
    for ent in entities:
        entry.runtime_data.switched_rooms[f"select.{ent.unique_id}"] = ent
    async_add_entities(entities)


class CleanRoomPasses(SelectEntity):
    """A number entity to determine how many passes a room should be cleaned with."""

    def __init__(self, entry, name, data, pmap, zone=False) -> None:
        """Creates a switch entity for rooms."""
        self._attr_name = (
            f"Clean {pmap['active_pmapv_details']['map_header']['name']}: {name}"
        )
        self._entry = entry
        self._attr_unique_id = f"{entry.unique_id}_p_{data['id']}_{'z' if zone else 'r'}_{pmap['active_pmapv_details']['active_pmapv']['pmap_id']}"
        self._attached = f"{entry.unique_id}_{data['id']}_{'z' if zone else 'r'}_{pmap['active_pmapv_details']['active_pmapv']['pmap_id']}"
        self._attr_current_option = "Don't Clean"
        self._attr_options = ["Don't Clean", "One Pass", "Two Passes"]
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.unique_id)},
            "name": entry.title,
            "manufacturer": "iRobot",
        }
        self.room_json = {
            "region_id": data["id"],
            "type": "rid",
            "params": {"noAutoPasses": False, "twoPass": False},
        }
        self._attr_extra_state_attributes = {
            "room_data": data,
            "room_json": self.room_json,
        }
        if zone:
            self.room_json["type"] = "zid"
            icon = zoneTypeMappings.get(
                data["zone_type"], zoneTypeMappings.get("default")
            )
        else:
            # autodetect icon
            icon = regionTypeMappings.get(
                data["region_type"], regionTypeMappings.get("default")
            )
        self._attr_icon = icon

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option == "Two Passes":
            self.room_json["params"] = {"noAutoPasses": True, "twoPass": True}
        elif option == "One Pass":
            self.room_json["params"] = {"noAutoPasses": False, "twoPass": False}
        self._attr_extra_state_attributes["room_json"] = self.room_json
        self._attr_current_option = option
        self._async_write_ha_state()

    def get_region_json(self):
        """Return robot-readable JSON to identify the room to start cleaning it."""
        return self.room_json
