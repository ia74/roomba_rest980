"""Switches needed."""

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, regionTypeMappings, zoneTypeMappings

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Create the switches to identify cleanable rooms."""
    entities = []
   
    entities.extend([VacuumModesSelect(entry)])
    entities.extend([MopIntensitySelect(entry)])

    async_add_entities(entities)

class VacuumModesSelect(SelectEntity):
    """A number entity to determine how many passes a room should be cleaned with."""

    def __init__(self, entry) -> None:
        """Creates a switch entity for rooms."""
        self._attr_name = (
            f"Vacuum mode"
        )
        self._entry = entry
        self._attr_unique_id = f"{entry.unique_id}_ModeSelect"
        self._attached = self._attr_unique_id
        self._attr_current_option = "Sweeping"
        self._attr_options = ["Sweeping", "Sweeping and mopping"]
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.unique_id)},
            "name": entry.title,
            "manufacturer": "iRobot",
        }

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        self._attr_current_option = option
        self._entry.runtime_data.vacuum_mode = option
        self._async_write_ha_state()

class MopIntensitySelect(SelectEntity):
    """A number entity to determine how many passes a room should be cleaned with."""

    def __init__(self, entry) -> None:
        """Creates a switch entity for rooms."""
        self._attr_name = (
            f"Mop intensity"
        )
        self._entry = entry
        self._attr_unique_id = f"{entry.unique_id}_mop_intensity"
        self._attached = self._attr_unique_id
        self._attr_current_option = "medium"
        self._attr_options = ["low", "medium", "high"]
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.unique_id)},
            "name": entry.title,
            "manufacturer": "iRobot",
        }

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        self._attr_current_option = option
        self._entry.runtime_data.mop_mode = option
        self._async_write_ha_state()