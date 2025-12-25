"""Switches needed."""

import logging

from homeassistant.components.switch import SwitchEntity
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
                                RoomSwitch(
                                    entry, region["name"] or "Unnamed Room", region
                                )
                                for region in pmap["active_pmapv_details"]["regions"]
                            ],
                        )
                        entities.extend(
                            [
                                RoomSwitch(
                                    entry,
                                    region["name"] or "Unnamed Zone",
                                    region,
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
        entry.runtime_data.switched_rooms[f"switch.{ent.unique_id}"] = ent
    async_add_entities(entities)


class RoomSwitch(SwitchEntity):
    """A switch entity to determine whether or not a room should be cleaned by the vacuum."""

    def __init__(self, entry, name, data, zone=False) -> None:
        """Creates a switch entity for rooms."""
        self._attr_name = f"Clean {name}"
        self._attr_unique_id = f"{entry.unique_id}_{data['id']}"
        self._is_on = False
        self._room_json = {"region_id": data["id"], "type": "rid"}
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_extra_state_attributes = data
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.unique_id)},
            "name": entry.title,
            "manufacturer": "iRobot",
        }
        if zone:
            self._room_json["type"] = "zid"
            icon = zoneTypeMappings.get(
                data["zone_type"], zoneTypeMappings.get("default")
            )
        else:
            # autodetect icon
            icon = regionTypeMappings.get(
                data["region_type"], regionTypeMappings.get("default")
            )
        self._attr_icon = icon

    @property
    def is_on(self):
        """Does the user want the room to be cleaned?"""
        return self._is_on

    async def async_turn_on(self, **kwargs):
        """Yes."""
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """No."""
        self._is_on = False
        self.async_write_ha_state()

    def get_region_json(self):
        """Return robot-readable JSON to identify the room to start cleaning it."""
        return self._room_json
