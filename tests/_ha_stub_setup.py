"""Minimal Home Assistant stubs so sensor.py can be imported and tested
without installing the full homeassistant PyPI package.

This registers just enough of the homeassistant.* API surface that
custom_components/roomba_rest980/{const,RoombaSensor,sensor}.py touch at
module scope, then loads those three files directly via importlib so the
tests exercise the REAL patched source rather than a reimplementation.
The package's real __init__.py is intentionally bypassed since it pulls in
much heavier imports (ConfigEntry, ServiceCall, config_validation,
aiohttp_client, select.py, ...) that aren't needed to test sensor.py.
"""

import enum
import importlib.util
import os
import sys
import types

# ---------------------------------------------------------------------------
# homeassistant.const
# ---------------------------------------------------------------------------
const_mod = types.ModuleType("homeassistant.const")
const_mod.PERCENTAGE = "%"
const_mod.SIGNAL_STRENGTH_DECIBELS = "dB"
const_mod.SIGNAL_STRENGTH_DECIBELS_MILLIWATT = "dBm"


class UnitOfArea(str, enum.Enum):
    SQUARE_METERS = "m²"


class UnitOfTime(str, enum.Enum):
    MINUTES = "min"


const_mod.UnitOfArea = UnitOfArea
const_mod.UnitOfTime = UnitOfTime

# ---------------------------------------------------------------------------
# homeassistant.components.sensor
# ---------------------------------------------------------------------------
components_mod = types.ModuleType("homeassistant.components")
components_sensor_mod = types.ModuleType("homeassistant.components.sensor")


class SensorDeviceClass(str, enum.Enum):
    ENUM = "enum"
    SIGNAL_STRENGTH = "signal_strength"
    TIMESTAMP = "timestamp"
    DURATION = "duration"
    AREA = "area"


class SensorEntity:
    """Bare-bones stand-in for homeassistant.components.sensor.SensorEntity."""

    _attr_available = True
    _attr_native_value = None
    _attr_options = None
    _attr_device_class = None
    _attr_native_unit_of_measurement = None
    _attr_entity_category = None
    _attr_icon = None
    _attr_entity_registry_enabled_default = False
    _attr_extra_state_attributes = None

    @property
    def native_value(self):
        return self._attr_native_value

    @property
    def available(self):
        return self._attr_available


components_sensor_mod.SensorDeviceClass = SensorDeviceClass
components_sensor_mod.SensorEntity = SensorEntity

# ---------------------------------------------------------------------------
# homeassistant.core
# ---------------------------------------------------------------------------
core_mod = types.ModuleType("homeassistant.core")


class HomeAssistant:
    pass


core_mod.HomeAssistant = HomeAssistant

# ---------------------------------------------------------------------------
# homeassistant.helpers, .entity, .device_registry, .update_coordinator
# ---------------------------------------------------------------------------
helpers_mod = types.ModuleType("homeassistant.helpers")

helpers_entity_mod = types.ModuleType("homeassistant.helpers.entity")


class EntityCategory(str, enum.Enum):
    DIAGNOSTIC = "diagnostic"
    CONFIG = "config"


helpers_entity_mod.EntityCategory = EntityCategory

helpers_device_registry_mod = types.ModuleType("homeassistant.helpers.device_registry")


class DeviceInfo(dict):
    pass


helpers_device_registry_mod.DeviceInfo = DeviceInfo

helpers_update_coordinator_mod = types.ModuleType(
    "homeassistant.helpers.update_coordinator"
)


class CoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator

    def async_write_ha_state(self):
        pass


class DataUpdateCoordinator:
    pass


helpers_update_coordinator_mod.CoordinatorEntity = CoordinatorEntity
helpers_update_coordinator_mod.DataUpdateCoordinator = DataUpdateCoordinator

# ---------------------------------------------------------------------------
# homeassistant.util.dt
# ---------------------------------------------------------------------------
util_mod = types.ModuleType("homeassistant.util")
util_dt_mod = types.ModuleType("homeassistant.util.dt")

import datetime as _datetime


def utc_from_timestamp(timestamp):
    return _datetime.datetime.fromtimestamp(timestamp, tz=_datetime.timezone.utc)


def utcnow():
    return _datetime.datetime.now(tz=_datetime.timezone.utc)


util_dt_mod.utc_from_timestamp = utc_from_timestamp
util_dt_mod.utcnow = utcnow

# ---------------------------------------------------------------------------
# Register everything in sys.modules
# ---------------------------------------------------------------------------
homeassistant_mod = types.ModuleType("homeassistant")

sys.modules["homeassistant"] = homeassistant_mod
sys.modules["homeassistant.const"] = const_mod
sys.modules["homeassistant.components"] = components_mod
sys.modules["homeassistant.components.sensor"] = components_sensor_mod
sys.modules["homeassistant.core"] = core_mod
sys.modules["homeassistant.helpers"] = helpers_mod
sys.modules["homeassistant.helpers.entity"] = helpers_entity_mod
sys.modules["homeassistant.helpers.device_registry"] = helpers_device_registry_mod
sys.modules["homeassistant.helpers.update_coordinator"] = helpers_update_coordinator_mod
sys.modules["homeassistant.util"] = util_mod
sys.modules["homeassistant.util.dt"] = util_dt_mod

# ---------------------------------------------------------------------------
# Fake custom_components.roomba_rest980 package, loading real source files
# directly (bypassing the real, heavier __init__.py).
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_INTEGRATION_DIR = os.path.join(_REPO_ROOT, "custom_components", "roomba_rest980")
_PKG = "custom_components.roomba_rest980"

custom_components_pkg = types.ModuleType("custom_components")
custom_components_pkg.__path__ = [os.path.join(_REPO_ROOT, "custom_components")]
sys.modules["custom_components"] = custom_components_pkg

roomba_pkg = types.ModuleType(_PKG)
roomba_pkg.__path__ = [_INTEGRATION_DIR]
sys.modules[_PKG] = roomba_pkg


def _load_real_module(name):
    file_path = os.path.join(_INTEGRATION_DIR, f"{name}.py")
    spec = importlib.util.spec_from_file_location(f"{_PKG}.{name}", file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"{_PKG}.{name}"] = module
    spec.loader.exec_module(module)
    return module


_load_real_module("const")
_load_real_module("RoombaSensor")
_load_real_module("sensor")
