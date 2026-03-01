"""Buttons needed."""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Create the switches to identify cleanable rooms."""
    _LOGGER.warning("step 0")
    cloudCoordinator = entry.runtime_data.cloud_coordinator
    entities = []
    _LOGGER.warning("step 1")
    if cloudCoordinator and cloudCoordinator.data:
        _LOGGER.warning("step 2 ")
        blid = entry.runtime_data.robot_blid
        # Get cloud data for the specific robot
        if blid in cloudCoordinator.data:
            _LOGGER.warning("step 3 ")
            cloud_data = cloudCoordinator.data[blid]
           
            if "pmaps" in cloud_data:
                _LOGGER.warning("step 4")
                for pmap in cloud_data["pmaps"]:
                    try:
                    
                        entities.extend(
                            [
                                RoomButton(
                                    entry,
                                    region["name"] or "Unnamed Room",
                                    region,
                                    pmap,
                                )
                                for region in pmap["active_pmapv_details"]["regions"]
                            ]
                        )
                       
                    except (KeyError, TypeError) as e:
                        _LOGGER.warning(
                            "Failed to create pmap entity for %s: %s",
                            pmap.get("pmap_id", "unknown"),
                            e,
                        )
                       
    for ent in entities:
        entry.runtime_data.switched_rooms[f"button.{ent.unique_id}"] = ent
    async_add_entities(entities)

class RoomButton(ButtonEntity):
    """A button entity to initiate iRobot favorite routines."""

    def __init__(self, entry, name, data, pmap) -> None:
        """Creates a button entity for entries."""
        self._attr_name = name
        self._entry = entry
        self._attr_unique_id = f"{entry.unique_id}_p_{data['id']}_{pmap['active_pmapv_details']['active_pmapv']['pmap_id']}"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_extra_state_attributes = data
        self._data = data
        self._attr_icon = "mdi:broom"
        self._attr_entity_registry_enabled_default = not data.get("hidden", False)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.unique_id)},
            "name": entry.title,
            "manufacturer": "iRobot",
        }
        self.is_active = True
        self.room_json = {
            "region_id": data["id"],
            "type": "rid",
            "params": {"noAutoPasses": False, "twoPass": False},
            }

    async def async_press(self):
        """Send command out to clean with the ID."""
        self.is_active = not self.is_active
        self._async_write_ha_state()
       
