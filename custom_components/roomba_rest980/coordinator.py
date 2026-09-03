"""Data update coordinator for Roomba REST980."""

import asyncio
import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import (
    ConfigEntryAuthFailed,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .CloudApi import iRobotCloudApi, AuthenticationError, CloudApiError
from .const import DEFAULT_CLOUD_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class RoombaDataCoordinator(DataUpdateCoordinator):
    """Data coordinator for Roomba REST980 integration."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="rest980 API data",
            config_entry=config_entry,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.session = async_get_clientsession(hass)  # Use HA’s shared session
        self.url = config_entry.data["base_url"]

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with asyncio.timeout(10):
                async with self.session.get(f"{self.url}/api/local/info/state") as resp:
                    resp.raise_for_status()
                    return await resp.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err


class RoombaCloudCoordinator(DataUpdateCoordinator):
    """Data coordinator for Roomba REST980 integration."""

    api: iRobotCloudApi

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="iRobot Cloud API data",
            config_entry=config_entry,
            update_interval=DEFAULT_CLOUD_SCAN_INTERVAL,
        )
        self.username = config_entry.data["irobot_username"]
        self.password = config_entry.data["irobot_password"]
        self.session = async_get_clientsession(hass)
        self.api = iRobotCloudApi(self.username, self.password, self.session)
        self._entry = config_entry

    async def _async_setup(self):
        try:
            await self.api.authenticate()
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(f"Cloud API error: {err}") from err
        except CloudApiError as err:
            raise ConfigEntryNotReady(f"Cloud API error: {err}") from err

    async def _async_update_data(self):
        # Every roomba_rest980 config entry (one per physical robot) used to run
        # its own RoombaCloudCoordinator that called get_all_robots_data(), which
        # sequentially fetches mission history + pmaps + map imagery for *every*
        # robot on the iRobot account. With N robots linked to one account that's
        # up to 3N+2 sequential AWS-signed HTTP calls per coordinator, N times
        # over -- O(N^2) total work for O(N) useful data, since (per sensor.py,
        # camera.py, select.py) each entry only ever reads its own robot_blid's
        # slice back out. That's what was blowing the 10s timeout with more than
        # one or two robots on an account.
        #
        # Fix: once this entry's robot_blid is known (matched in __init__.py's
        # _async_setup_cloud), fetch only that robot's data. Before it's known
        # (the very first refresh, which _async_setup_cloud's matching pass
        # depends on), use the free cached robot_info from login instead of the
        # expensive per-robot fetch -- matching only needs name/sku/softwareVer,
        # not mission history or maps. `schedules`/`favorites` are account-level
        # (read by button.py across all entries) so they're still fetched here
        # every cycle, but that's 2 calls, not the O(N) map/mission fetch.
        try:
            async with asyncio.timeout(20):
                blid = getattr(self._entry.runtime_data, "robot_blid", None)
                if blid and blid in self.api.robots:
                    all_data = {blid: await self.api.get_robot_data(blid)}
                else:
                    all_data = self.api.get_cached_robots_info()

                all_data["schedules"] = await self.api.get_schedules()
                all_data["favorites"] = await self.api.get_favorites()
                return all_data
        except (aiohttp.ClientError, TimeoutError) as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
