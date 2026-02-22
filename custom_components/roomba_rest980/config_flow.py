"""The configuration flow for the robot."""

import asyncio
import hashlib
import logging

from aiohttp import ClientConnectorError, ClientError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .CloudApi import AuthenticationError, iRobotCloudApi
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required("base_url"): str,
        vol.Required("cloud_api", default=True): bool,
    }
)

CLOUD_SCHEMA = vol.Schema(
    {
        vol.Required("irobot_username"): str,
        vol.Required("irobot_password"): str,
    }
)


class RoombaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow."""

    VERSION = 2

    _proposed_name: str
    _user_data: dict[str, any]

    async def async_step_reauth(self, entry_data: dict[str, any]) -> ConfigFlowResult:
        """Perform reauth upon an API authentication error."""
        await self.hass.config_entries.async_reload(self._reauth_entry_id)
        return self.async_abort(reason="reauth_successful")

    async def async_step_cloud(self, user_input=None) -> ConfigFlowResult:
        """Show user the setup for the cloud API."""
        if user_input is not None:
            errors = {}
            async with iRobotCloudApi(
                user_input["irobot_username"], user_input["irobot_password"]
            ) as api:
                try:
                    await api.authenticate()
                except AuthenticationError:
                    errors["base"] = "cloud_authentication_error"
                except Exception:  # Allowed in config flow for robustness
                    errors["base"] = "unknown"
            if errors:
                return self.async_show_form(
                    step_id="cloud",
                    data_schema=CLOUD_SCHEMA,
                    errors=errors,
                )

            if hasattr(self, "_user_data"):
                data = {**self._user_data, **user_input}
                return self.async_create_entry(
                    title=self._proposed_name,
                    data=data,
                )
            return self.async_abort(reason="missing_user_data")

        return self.async_show_form(step_id="cloud", data_schema=CLOUD_SCHEMA)

    async def test_local(self, user_input):
        """Test connection to local rest980 API."""
        session = async_get_clientsession(self.hass)
        async with session.get(
            f"{user_input['base_url']}/api/local/info/state"
        ) as resp:
            data = await resp.json() or {}
            if data == {}:
                raise ValueError("No data returned from device")

            unique_id = hashlib.md5(user_input["base_url"].encode()).hexdigest()[:8]

            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()
            return data

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        """Show the user the input for the base url."""
        if user_input is not None:
            errors = {}
            try:
                async with asyncio.timeout(10):
                    device_data = await self.test_local(user_input)
            except TimeoutError:
                errors["base"] = "local_cannot_connect"
            except (ClientError, ClientConnectorError, OSError):
                errors["base"] = "local_cannot_connect"
            except ValueError:
                errors["base"] = "local_connected_no_data"
            except Exception:  # Allowed in config flow for robustness
                errors["base"] = "unknown"

            if errors:
                return self.async_show_form(
                    step_id="user",
                    data_schema=USER_SCHEMA,
                    errors=errors,
                )

            # Use device name if available, otherwise fall back to URL
            device_name = device_data.get("name", "Roomba")
            self._proposed_name = f"{device_name}"

            if not user_input["cloud_api"]:
                return self.async_create_entry(
                    title=self._proposed_name,
                    data=user_input,
                )
            # Store user data for use in cloud step
            self._user_data = user_input
            return self.async_show_form(step_id="cloud", data_schema=CLOUD_SCHEMA)
        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA)
