"""Config flow for LoJack integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from lojack_clients.identity import AuthenticatedClient as IdentityClient
from lojack_clients.identity.api.default import get_identity_token
from lojack_clients.services import AuthenticatedClient as ServicesClient
from lojack_clients.services.api.default import get_all_user_assets

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    username = data[CONF_USERNAME]
    password = data[CONF_PASSWORD]

    try:
        # Test authentication
        result = await hass.async_add_executor_job(
            _test_authentication, username, password
        )
        if not result["success"]:
            raise InvalidAuth(result.get("error", "Unknown authentication error"))

        return {
            "title": f"LoJack ({username})",
            "asset_count": result.get("asset_count", 0),
        }
    except InvalidAuth:
        raise
    except Exception as err:
        _LOGGER.error("Unexpected error during authentication: %s", err)
        raise CannotConnect(f"Connection error: {err}") from err


def _test_authentication(username: str, password: str) -> dict[str, Any]:
    """Test authentication with LoJack API (blocking)."""
    try:
        # Create identity client and get token
        identity_client = IdentityClient.from_login(username, password)
        token_response = get_identity_token.sync(client=identity_client)

        if token_response is None or not hasattr(token_response, 'token'):
            return {"success": False, "error": "Failed to get authentication token"}

        # Create services client and test by fetching assets
        services_client = ServicesClient.from_token(token_response.token)
        assets_response = get_all_user_assets.sync(client=services_client)

        asset_count = 0
        if assets_response and hasattr(assets_response, 'assets'):
            asset_count = len(assets_response.assets) if assets_response.assets else 0

        return {"success": True, "asset_count": asset_count}

    except Exception as err:
        error_str = str(err).lower()
        if "401" in str(err) or "unauthorized" in error_str:
            return {"success": False, "error": "Invalid username or password"}
        if "connection" in error_str or "network" in error_str:
            return {"success": False, "error": "Connection error"}
        return {"success": False, "error": str(err)}


class LoJackConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LoJack."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Check if this account is already configured
                await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauthorization."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauthorization confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            reauth_entry = self._get_reauth_entry()
            try:
                user_input[CONF_USERNAME] = reauth_entry.data[CONF_USERNAME]
                await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data={**reauth_entry.data, **user_input},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
