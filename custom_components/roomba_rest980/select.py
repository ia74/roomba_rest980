"""Switches needed."""

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, regionTypeMappings, zoneTypeMappings

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Create the switches to identify available cleaning modes."""
    entities = []
   
    entities.extend([VacuumModesSelect(entry)])
    entities.extend([MopIntensitySelect(entry)])

    async_add_entities(entities)

class VacuumModesSelect(SelectEntity):
    """Entity to determine which cleaning mode the vacuum should use."""

    def __init__(self, entry) -> None:
        """Creates a switch entity for rooms."""
        self._attr_name = (
            f"Cleaning mode"
        )
        self._entry = entry
        self._attr_unique_id = f"{entry.unique_id}_mode_select"
        self._attached = self._attr_unique_id
        self._attr_current_option = "vacuum"
        self._attr_options = ["vacuum", "mop", "vacuum_and_mop"]
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
    """Entity to determine which mop intensity the vacuum should use."""

    def __init__(self, entry) -> None:
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