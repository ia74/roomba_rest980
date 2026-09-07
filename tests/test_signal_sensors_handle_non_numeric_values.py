"""Regression tests for issue #55.

rest980 reports "n-a"/"n/a" strings for the rssi/snr/noise signal fields
(and unmapped strings for "phase") while the Roomba is asleep or docked.
These sensors are declared with device classes that Home Assistant validates
strictly: SIGNAL_STRENGTH requires a numeric native_value (or None), and
ENUM requires the native_value to be one of the sensor's declared
_attr_options. Passing the raw placeholder strings through raised
ValueError inside Home Assistant's state-writing machinery every update
cycle. See custom_components/roomba_rest980/sensor.py for the fix.
"""

import _ha_stub_setup  # noqa: F401  (import for side effects: registers HA stubs)

from custom_components.roomba_rest980.sensor import (
    RoombaNetworkNoise,
    RoombaPhase,
    RoombaRSSI,
    RoombaSNR,
)


class FakeCoordinator:
    def __init__(self, data):
        self.data = data


class FakeEntry:
    unique_id = "test_entry"


def _make(cls, data):
    entity = cls(FakeCoordinator(data), FakeEntry())
    entity._handle_coordinator_update()
    return entity


def test_rssi_coerces_non_numeric_placeholder_to_none():
    entity = _make(RoombaRSSI, {"signal": {"rssi": "n-a"}})
    assert entity.native_value is None


def test_rssi_passes_through_numeric_value():
    entity = _make(RoombaRSSI, {"signal": {"rssi": -55}})
    assert entity.native_value == -55


def test_rssi_defaults_to_none_when_key_missing():
    entity = _make(RoombaRSSI, {"signal": {}})
    assert entity.native_value is None


def test_snr_coerces_non_numeric_placeholder_to_none():
    entity = _make(RoombaSNR, {"signal": {"snr": "n/a"}})
    assert entity.native_value is None


def test_snr_passes_through_numeric_value():
    entity = _make(RoombaSNR, {"signal": {"snr": 20}})
    assert entity.native_value == 20


def test_network_noise_coerces_non_numeric_placeholder_to_none():
    entity = _make(RoombaNetworkNoise, {"signal": {"noise": "n/a"}})
    assert entity.native_value is None


def test_phase_unknown_fallback_is_a_declared_option():
    entity = _make(RoombaPhase, {"cleanMissionStatus": {"cycle": "clean", "phase": "some_unmapped_phase"}})
    assert entity.native_value in entity._attr_options


def test_phase_reports_unknown_for_an_unrecognized_phase_value():
    entity = _make(RoombaPhase, {"cleanMissionStatus": {"cycle": "clean", "phase": "some_unmapped_phase"}})
    assert entity.native_value == "Unknown"
