"""A generic sensor to provide the coordinator and device info."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class RoombaSensor(CoordinatorEntity, SensorEntity):
    """Generic Roomba sensor to provide coordinator."""

    _attr_has_entity_name = True
    _rs_given_info: tuple[str, str] = ("Sensor", "sensor")

    def __init__(self, coordinator, entry) -> None:
        """Create a new generic sensor."""
        super().__init__(coordinator)
        _LOGGER.debug("Entry unique_id: %s", entry.unique_id)
        self._entry = entry
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_has_entity_name = True
        self._attr_name = self._rs_given_info[0]
        self._attr_unique_id = f"{entry.unique_id}_{self._rs_given_info[1]}"

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

    def isMissionActive(self) -> bool:
        """Return whether or not there is a mission in progress."""
        data = self.coordinator.data or {}
        status = data.get("cleanMissionStatus", {})
        # Mission State
        phase = status.get("phase")
        battery = data.get("batPct")
        state = False
        if status.get("mssnStrtTm"):
            state = True
        if phase == "charge" and battery == 100:
            state = False
        return state

    def returnIn(self, mapping: dict[str, str], index: str) -> str:
        """Default or map value."""
        mapping.get(index, index)

    def _get_default(self, key: str, default: str):
        return self.coordinator.data.get(key, default)


class RoombaCloudSensor(CoordinatorEntity, SensorEntity):
    """Generic Roomba sensor to provide coordinator."""

    _attr_has_entity_name = True
    _rs_given_info: tuple[str, str] = ("Sensor", "sensor")

    def __init__(self, coordinator, entry) -> None:
        """Create a new generic sensor."""
        super().__init__(coordinator)
        _LOGGER.debug("Entry unique_id: %s", entry.unique_id)
        self._entry = entry
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_has_entity_name = True
        self._attr_name = self._rs_given_info[0]
        self._attr_unique_id = f"{entry.unique_id}_{self._rs_given_info[1]}"
        if not entry.data["cloud_api"]:
            self._attr_available = False

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
