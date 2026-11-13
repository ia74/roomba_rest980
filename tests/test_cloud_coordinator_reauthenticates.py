"""Regression test for issue #61.

When the cloud login failed during setup, _async_setup() never ran again and
every later refresh hit "Not authenticated. Call authenticate() first." until
the entry was reloaded by hand. See custom_components/roomba_rest980/coordinator.py.
"""

import asyncio
import sys
import types

import _ha_stub_setup  # noqa: F401  (import for side effects: registers HA stubs)
from _ha_stub_setup import _load_real_module


class ConfigEntryAuthFailed(Exception):
    pass


class UpdateFailed(Exception):
    pass


class ConfigEntryNotReady(Exception):
    pass


_update_coordinator = sys.modules["homeassistant.helpers.update_coordinator"]
_update_coordinator.ConfigEntryAuthFailed = ConfigEntryAuthFailed
_update_coordinator.UpdateFailed = UpdateFailed

_config_entries = types.ModuleType("homeassistant.config_entries")
_config_entries.ConfigEntry = object
sys.modules["homeassistant.config_entries"] = _config_entries

_exceptions = types.ModuleType("homeassistant.exceptions")
_exceptions.ConfigEntryNotReady = ConfigEntryNotReady
sys.modules["homeassistant.exceptions"] = _exceptions

_aiohttp_client = types.ModuleType("homeassistant.helpers.aiohttp_client")
_aiohttp_client.async_get_clientsession = lambda hass: None
sys.modules["homeassistant.helpers.aiohttp_client"] = _aiohttp_client

CloudApi = _load_real_module("CloudApi")
coordinator = _load_real_module("coordinator")


class FakeApi:
    credentials = None
    robots = {}

    async def authenticate(self):
        self.credentials = {"CognitoId": "us-east-1:abc"}

    def get_cached_robots_info(self):
        return {}

    async def get_schedules(self):
        if not self.credentials:
            raise CloudApi.AuthenticationError("Not authenticated. Call authenticate() first.")
        return []

    async def get_favorites(self):
        return []


class FakeEntry:
    runtime_data = types.SimpleNamespace(robot_blid=None)


def test_update_logs_in_again_after_failed_setup_login():
    cloud = coordinator.RoombaCloudCoordinator.__new__(coordinator.RoombaCloudCoordinator)
    cloud.api = FakeApi()
    cloud._entry = FakeEntry()
    cloud._rate_limited_count = 0

    data = asyncio.run(cloud._async_update_data())

    assert data["schedules"] == []
