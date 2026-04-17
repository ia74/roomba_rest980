"""The Roomba Mop specific sensors."""

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.entity import EntityCategory

from .const import mopRanks, padMappings
from .RoombaSensor import RoombaSensor


class MopCleanMode(RoombaSensor):
    """A simple sensor that returns the clean mode of the mop."""

    _rs_given_info = ("Mop Clean Mode", "mop_clean_mode")

    def __init__(self, coordinator, entry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry)
        self._attr_device_class = SensorDeviceClass.ENUM
        # self._attr_options = list(cleanBaseMappings.values()) #TODO: Update with real value list
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:auto-mode"

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        data = self.coordinator.data or {}
        padWetness = data.get("padWetness")
        if not padWetness:
            return
        if isinstance(padWetness, dict):
            # priority: disposable > reusable
            if "disposable" in padWetness:
                mode = "Disposable" if padWetness["disposable"] else "Indisposable"
            elif "reusable" in padWetness:
                mode = "Reusable" if padWetness["reusable"] else "Nonreusable"
            else:
                mode = "Unknown"
        else:
            mode = padWetness
        self._attr_native_value = mode
        self.async_write_ha_state()


class MopBehavior(RoombaSensor):
    """A simple sensor that returns the behavior of the mop."""

    _rs_given_info = ("Mop Behavior", "mop_behavior")

    def __init__(self, coordinator, entry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry)
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = [
            *list(mopRanks.values()),
            "Dirty Pause",
            "Dirty Pause + Dry",
            "Dirty Pause + Dry + Wash",
            "Dry",
            "Dry + Wash",
            "Wash",
        ]
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:shimmer"

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        data = self.coordinator.data or {}
        rankOverlap = data.get("rankOverlap", False)
        if not rankOverlap:
            if data.get("padDryAllowed"):
                dirty_pause = data.get("padDirtyPause", 0) == 1
                dry_allowed = data.get("padDryAllowed", 0) == 1
                wash_allowed = data.get("padWashAllowed", 0) == 1
                modes = []
                if dirty_pause:
                    modes.append("Dirty Pause")
                if dry_allowed:
                    modes.append("Dry")
                if wash_allowed:
                    modes.append("Wash")

                value = " + ".join(modes)
                self._attr_native_value = value
                self.async_write_ha_state()
                return
            self._attr_available = False
            self.async_write_ha_state()
            return
        self._attr_native_value = mopRanks.get(rankOverlap, rankOverlap)
        self.async_write_ha_state()


class MopPad(RoombaSensor):
    """A simple sensor that returns the pad type of the mop."""

    _rs_given_info = ("Mop Pad", "mop_pad")

    def __init__(self, coordinator, entry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry)
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = list(padMappings.values())
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:shimmer"

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        data = self.coordinator.data or {}
        detectedPad = data.get("detectedPad", "invalid")
        self._attr_native_value = padMappings.get(detectedPad, detectedPad)
        self.async_write_ha_state()


class MopTank(RoombaSensor):
    """A simple sensor that returns the status of the tank of the mop."""

    _rs_given_info = ("Mop Tank", "mop_tank")

    def __init__(self, coordinator, entry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry)
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = ["Fill Tank", "Ready", "Lid Open", "Tank Missing"]
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:shimmer"

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        data = self.coordinator.data or {}
        status = data.get("cleanMissionStatus", {})
        notReady = status.get("notReady")
        detectedPad = data.get("detectedPad", False)
        if not detectedPad:
            return
        tankPresent = data.get("tankPresent", False)
        lidOpen = data.get("lidOpen", False)
        if tankPresent:
            if notReady == 31:  # Fill Tank
                tankState = "Fill Tank"
            elif not lidOpen:
                tankState = "Ready"
            elif lidOpen:
                tankState = "Lid Open"
        else:
            tankState = "Tank Missing"
        self._attr_native_value = tankState
        self.async_write_ha_state()


class MopTankLevel(RoombaSensor):
    """A simple sensor that returns the level of the tank of the mop."""

    _rs_given_info = ("Mop Tank Level", "mop_tank_level")

    def __init__(self, coordinator, entry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry)
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:cup-water"

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        data = self.coordinator.data or {}
        tankLvl = data.get("tankLvl")
        self._attr_native_value = tankLvl
        self.async_write_ha_state()
