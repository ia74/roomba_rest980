"""Create sensors that poll Roomba's data."""

import logging

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    PERCENTAGE,
    UnitOfArea,
    UnitOfTime,
    SIGNAL_STRENGTH_DECIBELS,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util import dt as dt_util

from .const import (
    cleanBaseMappings,
    errorMappings,
    jobInitiatorMappings,
    mopRanks,
    notReadyMappings,
    padMappings,
    phaseMappings,
)
from .RoombaSensor import RoombaCloudSensor, RoombaSensor

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Create the sensors needed to poll Roomba's data."""
    coordinator = entry.runtime_data.local_coordinator
    cloudCoordinator = entry.runtime_data.cloud_coordinator
    async_add_entities(
        [
            RoombaAttributes(coordinator, entry),
            RoombaBatterySensor(coordinator, entry),
            RoombaBinSensor(coordinator, entry),
            RoombaJobInitiator(coordinator, entry),
            RoombaPhase(coordinator, entry),
            RoombaTotalArea(coordinator, entry),
            RoombaTotalTime(coordinator, entry),
            RoombaCleanBase(coordinator, entry),
            RoombaTotalJobs(coordinator, entry),
            RoombaMissionStartTime(coordinator, entry),
            RoombaMissionElapsedTime(coordinator, entry),
            RoombaRechargeTime(coordinator, entry),
            RoombaMissionExpireTime(coordinator, entry),
            RoombaCarpetBoostMode(coordinator, entry),
            RoombaCleanEdges(coordinator, entry),
            RoombaCleanMode(coordinator, entry),
            RoombaNotReady(coordinator, entry),
            RoombaError(coordinator, entry),
            RoombaIP(coordinator, entry),
            RoombaRSSI(coordinator, entry),
            RoombaNetworkNoise(coordinator, entry),
            RoombaSNR(coordinator, entry),
            RoombaCloudAttributes(cloudCoordinator, entry),
            MopCleanMode(coordinator, entry),
            MopBehavior(coordinator, entry),
            MopPad(coordinator, entry),
            MopTank(coordinator, entry),
            MopTankLevel(coordinator, entry),
        ],
        update_before_add=True,
    )

    # Create cloud pmap entities if cloud data is available
    cloud_entities = []
    if cloudCoordinator and cloudCoordinator.data:
        blid = entry.runtime_data.robot_blid
        # Get cloud data for the specific robot
        if blid in cloudCoordinator.data:
            cloud_data = cloudCoordinator.data[blid]
            # Create pmap entities from cloud data
            if "pmaps" in cloud_data:
                for pmap in cloud_data["pmaps"]:
                    try:
                        cloud_entities.append(
                            RoombaCloudPmap(cloudCoordinator, entry, pmap)
                        )
                    except (KeyError, TypeError) as e:
                        _LOGGER.warning(
                            "Failed to create pmap entity for %s: %s",
                            pmap.get("pmap_id", "unknown"),
                            e,
                        )
    if cloud_entities:
        async_add_entities(cloud_entities)


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
            self._attr_available = False
            self.async_write_ha_state()
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
        self._attr_options = list(padMappings.values())
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:shimmer"

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        data = self.coordinator.data or {}
        status = data.get("cleanMissionStatus", {})
        notReady = status.get("notReady")
        detectedPad = data.get("detectedPad", False)
        if not detectedPad:
            self._attr_available = False
            self.async_write_ha_state()
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


class RoombaBatterySensor(RoombaSensor):
    """Read the battery level of the Roomba."""

    _rs_given_info = ("Battery", "battery")

    def __init__(self, coordinator, entry) -> None:
        """Create a new battery level sensor."""
        super().__init__(coordinator, entry)
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        data = self.coordinator.data or {}
        self._attr_native_value = data.get("batPct", 0)
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Return all the attributes returned by rest980."""
        return self._get_default("batInfo", {})

    @property
    def icon(self):
        """Return a dynamic icon based on battery percentage."""
        batLevel = self.native_value or 0
        if batLevel >= 95:
            return "mdi:battery"
        if batLevel >= 60:
            return "mdi:battery-60"
        if batLevel >= 30:
            return "mdi:battery-30"
        if batLevel < 30:
            return "mdi:battery-alert"
        return "mdi:battery"


class RoombaAttributes(RoombaSensor):
    """A simple sensor that returns all given datapoints without modification."""

    _rs_given_info = ("Local Raw Attributes", "attributes")

    def __init__(self, coordinator, entry) -> None:
        """Create the sensor."""
        super().__init__(coordinator, entry)
        self._attr_icon = "mdi:lan-connect"
        self._attr_entity_registry_enabled_default = True

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        self._attr_native_value = (
            "Available" if self.coordinator.data else "Unavailable"
        )
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Return all the attributes returned by rest980."""
        return self.coordinator.data or {}


class RoombaCloudAttributes(RoombaCloudSensor):
    """A simple sensor that returns all given datapoints without modification."""

    _rs_given_info = ("Cloud Raw Attributes", "cloud_attributes")

    def __init__(self, coordinator, entry) -> None:
        """Create the sensor."""
        super().__init__(coordinator, entry)
        self._attr_icon = "mdi:cloud-braces"
        self._attr_entity_registry_enabled_default = True

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        self._attr_native_value = (
            "Available" if self.coordinator.data else "Unavailable"
        )
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Return all the attributes returned by iRobot's cloud."""
        return self.coordinator.data.get(self._entry.runtime_data.robot_blid) or {}


class RoombaCloudPmap(RoombaCloudSensor):
    """Sensor for Roomba persistent map (pmap) data from cloud."""

    def __init__(self, coordinator, entry, pmap) -> None:
        """Initialize the pmap sensor with data from cloud API."""
        # Handle different pmap data structures
        header = pmap["active_pmapv_details"]["map_header"]
        pmap_name = header.get("name", "Unknown Map")
        pmap_id = header.get("id", "unknown")

        self._rs_given_info = (pmap_name, pmap_id)
        super().__init__(coordinator, entry)

        self._attr_extra_state_attributes = pmap


class RoombaPhase(RoombaSensor):
    """A simple sensor that returns the phase of the Roomba."""

    _rs_given_info = ("Phase", "phase")

    def __init__(self, coordinator, entry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry)
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = list(phaseMappings.values())
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        data = self.coordinator.data or {}
        status = data.get("cleanMissionStatus", {})
        # Mission State
        cycle = status.get("cycle")
        phase = status.get("phase")
        battery = data.get("batPct")

        if phase == "charge" and battery == 100:
            rPhase = "Idle"
        elif cycle == "none" and phase == "stop":
            rPhase = "Stopped"
        else:
            rPhase = phaseMappings.get(phase, "Unknown")
        self._attr_native_value = rPhase
        self.async_write_ha_state()

    @property
    def icon(self):
        """Return the current phase of the Roomba."""
        data = self.coordinator.data or {}
        status = data.get("cleanMissionStatus", {})
        # Mission State
        cycle = status.get("cycle")
        phase = status.get("phase")

        if cycle == "none" and phase == "stop":
            return "mdi:progress-alert"
        return "mdi:progress-helper"


class RoombaCleanBase(RoombaSensor):
    """A simple sensor that returns the phase of the Roomba."""

    _rs_given_info = ("Clean Base", "clean_base")

    def __init__(self, coordinator, entry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry)
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = list(cleanBaseMappings.values())
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:trash-can"

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        data = self.coordinator.data or {}
        dock = data.get("dock")
        dockState = dock.get("state")
        self._attr_native_value = cleanBaseMappings.get(dockState, "Unknown")
        self.async_write_ha_state()


class RoombaIP(RoombaSensor):
    """A simple sensor that returns the state of the two pass mode of the Roomba."""

    _rs_given_info = ("IP", "ip")

    def __init__(self, coordinator, entry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry)
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:ip"

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        data = self.coordinator.data or {}
        net_info = data.get("netinfo")
        self._attr_native_value = net_info.get("addr", "n-a")
        self.async_write_ha_state()


class RoombaRSSI(RoombaSensor):
    """A simple sensor that returns the state of the RSSI of the Roomba."""

    _rs_given_info = ("RSSI", "rssi")

    def __init__(self, coordinator, entry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry)
        self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
        self._attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:signal"

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        data = self.coordinator.data or {}
        signal_info = data.get("signal")
        self._attr_native_value = signal_info.get("rssi", "n-a")
        self.async_write_ha_state()


class RoombaSNR(RoombaSensor):
    """A simple sensor that returns the state of the signal to noise ratio of the Roomba."""

    _rs_given_info = ("SNR", "snr")

    def __init__(self, coordinator, entry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry)
        self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
        self._attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:signal"

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        data = self.coordinator.data or {}
        signal_info = data.get("signal")
        self._attr_native_value = signal_info.get("snr", "n-a")
        self.async_write_ha_state()


class RoombaNetworkNoise(RoombaSensor):
    """A simple sensor that returns the state of the network noise of the Roomba."""

    _rs_given_info = ("Signal Noise", "signal_noise")

    def __init__(self, coordinator, entry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry)
        self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
        self._attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:signal"

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        data = self.coordinator.data or {}
        signal_info = data.get("signal")
        self._attr_native_value = signal_info.get("noise", "n-a")
        self.async_write_ha_state()


class RoombaBinSensor(RoombaSensor):
    """Read the bin data of the Roomba."""

    _rs_given_info = ("Bin", "bin")

    def __init__(self, coordinator, entry) -> None:
        """Create a new battery level sensor."""
        super().__init__(coordinator, entry)
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = ["Not Full", "Full"]
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def extra_state_attributes(self):
        """Return all the attributes about the bin."""
        return self._get_default("bin", {})

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        self._attr_native_value = (
            "Full" if self._get_default("bin", {}).get("full") else "Not Full"
        )
        self.async_write_ha_state()

    @property
    def icon(self):
        """Return a dynamic icon based on bin being full or not."""
        full: bool = self._get_default("bin", {}).get("full")
        return "mdi:trash-can-outline" if not full else "mdi:trash-can"


class RoombaJobInitiator(RoombaSensor):
    """Read the job initiator of the Roomba."""

    _rs_given_info = ("Job Initiator", "job_initiator")

    def __init__(self, coordinator, entry) -> None:
        """Create a new job initiator reading."""
        super().__init__(coordinator, entry)
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = list(jobInitiatorMappings.values())
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:cursor-pointer"

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        data = self.coordinator.data or {}
        status = data.get("cleanMissionStatus", {})
        initiator = status.get("initiator") or "none"
        self._attr_native_value = jobInitiatorMappings.get(initiator, "Unknown")
        self.async_write_ha_state()


class RoombaMissionStartTime(RoombaSensor):
    """Read the mission start time of the Roomba."""

    _rs_given_info = ("Job Start Time", "job_start_time")

    def __init__(self, coordinator, entry) -> None:
        """Create a new job start time reading."""
        super().__init__(coordinator, entry)
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_icon = "mdi:clock-start"

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        if not self.isMissionActive():
            self._attr_available = False
            self._attr_native_value = None
        else:
            data = self.coordinator.data or {}
            status = data.get("cleanMissionStatus", {})
            missionStartTime = status.get("mssnStrtTm")  # Unix timestamp in seconds?

            if missionStartTime:
                self._attr_available = True
                try:
                    self._attr_native_value = dt_util.utc_from_timestamp(
                        missionStartTime
                    )
                except (TypeError, ValueError):
                    self._attr_native_value = None
            else:
                self._attr_native_value = None
                self._attr_available = False

        self.async_write_ha_state()


class RoombaMissionElapsedTime(RoombaSensor):
    """Read the mission elapsed time of the Roomba."""

    _rs_given_info = ("Job Elapsed Time", "job_elapsed_time")

    def __init__(self, coordinator, entry) -> None:
        """Create a new job elapsed time reading."""
        super().__init__(coordinator, entry)
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_icon = "mdi:timeline-clock"

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        if not self.isMissionActive():
            self._attr_available = False
            self._attr_native_value = None
        else:
            data = self.coordinator.data or {}
            status = data.get("cleanMissionStatus", {})
            missionStartTime = status.get("mssnStrtTm")  # Unix timestamp in seconds?

            if missionStartTime:
                if missionStartTime != 0:
                    self._attr_available = True
                    try:
                        elapsed_time = dt_util.utcnow() - dt_util.utc_from_timestamp(
                            missionStartTime
                        )
                        # Convert timedelta to minutes
                        self._attr_native_value = elapsed_time.total_seconds() / 60
                    except (TypeError, ValueError):
                        self._attr_native_value = None
            else:
                self._attr_native_value = None
                self._attr_available = False

        self.async_write_ha_state()


class RoombaRechargeTime(RoombaSensor):
    """Read the mission start time of the Roomba."""

    _rs_given_info = ("Recharge Time", "job_recharge_time")

    def __init__(self, coordinator, entry) -> None:
        """Create a new job recharge time reading."""
        super().__init__(coordinator, entry)
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_icon = "mdi:battery-clock"

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        data = self.coordinator.data or {}
        status = data.get("cleanMissionStatus", {})
        estimatedRechargeTime = status.get("rechrgTm")  # Unix timestamp in seconds?

        if estimatedRechargeTime:
            if estimatedRechargeTime != 0:
                self._attr_available = True
                try:
                    self._attr_native_value = dt_util.utc_from_timestamp(
                        estimatedRechargeTime
                    )
                except (TypeError, ValueError):
                    self._attr_native_value = None
        else:
            self._attr_native_value = None
            self._attr_available = False

        self.async_write_ha_state()


class RoombaCarpetBoostMode(RoombaSensor):
    """Read the mission start time of the Roomba."""

    _rs_given_info = ("Carpet Boost", "carpet_boost")

    def __init__(self, coordinator, entry) -> None:
        """Create a new job carpet boost mode."""
        super().__init__(coordinator, entry)
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = ["Eco", "Performance", "Auto", "n-a"]
        self._attr_icon = "mdi:rug"

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        data = self.coordinator.data or {}
        vacuumHigh = data.get("vacHigh")
        carpetBoost = data.get("carpetBoost")

        if vacuumHigh is not None:
            if not vacuumHigh and not carpetBoost:
                self._attr_native_value = "Eco"
            elif vacuumHigh and not carpetBoost:
                self._attr_native_value = "Performance"
            else:
                self._attr_native_value = "Auto"
        else:
            self._attr_native_value = "n-a"

        self.async_write_ha_state()


class RoombaCleanEdges(RoombaSensor):
    """Read the mission start time of the Roomba."""

    _rs_given_info = ("Clean Edges", "clean_edges")

    def __init__(self, coordinator, entry) -> None:
        """Create a new clean_edges sensor."""
        super().__init__(coordinator, entry)
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = ["Yes", "No", "n-a"]
        self._attr_icon = "mdi:wall"

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        data = self.coordinator.data or {}
        openOnly = data.get("openOnly")

        if openOnly is not None:
            if openOnly:
                self._attr_native_value = "No"
            else:
                self._attr_native_value = "Yes"
        else:
            self._attr_native_value = "n-a"

        self.async_write_ha_state()


class RoombaError(RoombaSensor):
    """Read the error message of the Roomba."""

    _rs_given_info = ("Error Message", "error")

    def __init__(self, coordinator, entry) -> None:
        """Create a new error sensor."""
        super().__init__(coordinator, entry)
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = list(errorMappings.values())
        self._attr_icon = "mdi:robot-vacuum-alert"

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        data = self.coordinator.data or {}
        nr = data.get("cleanMissionStatus", {}).get("error")
        self._attr_native_value = errorMappings.get(nr, nr)

        self.async_write_ha_state()


class RoombaNotReady(RoombaSensor):
    """Read the not ready message of the Roomba."""

    _rs_given_info = ("Not Ready", "not_ready")

    def __init__(self, coordinator, entry) -> None:
        """Create a new not_ready sensor."""
        super().__init__(coordinator, entry)
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = list(notReadyMappings.values())
        self._attr_icon = "mdi:clock-alert"

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        data = self.coordinator.data or {}
        nr = data.get("cleanMissionStatus", {}).get("notReady")
        self._attr_native_value = notReadyMappings.get(nr, nr)

        self.async_write_ha_state()


class RoombaCleanMode(RoombaSensor):
    """Read the clean mode of the Roomba."""

    _rs_given_info = ("Clean Mode", "clean_mode")

    def __init__(self, coordinator, entry) -> None:
        """Create a new clean_edges sensor."""
        super().__init__(coordinator, entry)
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = ["One", "Two", "Auto", "n-a"]
        self._attr_icon = "mdi:broom"

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        data = self.coordinator.data or {}
        noAutoPasses = data.get("noAutoPasses")
        twoPass = data.get("twoPass")
        if noAutoPasses is not None and twoPass is not None:
            if noAutoPasses is True and twoPass is False:
                self._attr_native_value = "One"
            elif noAutoPasses is True and twoPass is True:
                self._attr_native_value = "Two"
            else:
                self._attr_native_value = "Auto"
        else:
            self._attr_native_value = "n-a"

        self.async_write_ha_state()


class RoombaMissionExpireTime(RoombaSensor):
    """Read the mission start time of the Roomba."""

    _rs_given_info = ("Job Expire Time", "job_expire_time")

    def __init__(self, coordinator, entry) -> None:
        """Create a new job recharge time reading."""
        super().__init__(coordinator, entry)
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_icon = "mdi:timeline-alert"

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        data = self.coordinator.data or {}
        status = data.get("cleanMissionStatus", {})
        expireTime = status.get("expireTm")  # Unix timestamp in seconds?

        if expireTime:
            if expireTime != 0:
                self._attr_available = True
                try:
                    self._attr_native_value = dt_util.utc_from_timestamp(expireTime)
                except (TypeError, ValueError):
                    self._attr_native_value = None
                    self._attr_available = False
        else:
            self._attr_native_value = None
            self._attr_available = False

        self.async_write_ha_state()


class RoombaTotalArea(RoombaSensor):
    """Read the job initiator of the Roomba."""

    _rs_given_info = ("Total Area", "total_area")

    def __init__(self, coordinator, entry) -> None:
        """Create a new job initiator reading."""
        super().__init__(coordinator, entry)
        self._attr_device_class = SensorDeviceClass.AREA
        self._attr_native_unit_of_measurement = UnitOfArea.SQUARE_METERS
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:texture-box"

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        data = self.coordinator.data or {}
        runtimeStats = data.get("runtimeStats") or {}
        sqft = runtimeStats.get("sqft")
        self._attr_native_value = sqft
        self.async_write_ha_state()


class RoombaTotalTime(RoombaSensor):
    """Read the total time the Roomba."""

    _rs_given_info = ("Total Time", "total_time")

    def __init__(self, coordinator, entry) -> None:
        """Create a new job initiator reading."""
        super().__init__(coordinator, entry)
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:clock-time-five"

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        data = self.coordinator.data or {}
        runtimeStats = data.get("runtimeStats") or {}
        hr = runtimeStats.get("hr")
        timeMin = runtimeStats.get("min")
        self._attr_native_value = (hr * 60) + timeMin
        self.async_write_ha_state()


class RoombaTotalJobs(RoombaSensor):
    """Read the total jobs from the Roomba."""

    _rs_given_info = ("Total Jobs", "total_jobs")

    def __init__(self, coordinator, entry) -> None:
        """Create a new job initiator reading."""
        super().__init__(coordinator, entry)
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:transmission-tower"

    def _handle_coordinator_update(self):
        """Update sensor when coordinator data changes."""
        data = self.coordinator.data or {}
        bbmssn = data.get("bbmssn") or {}
        self._attr_native_value = bbmssn.get("nMssn")
        self.async_write_ha_state()
