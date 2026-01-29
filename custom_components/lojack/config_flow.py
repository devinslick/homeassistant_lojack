"""Config flow for LoJack integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    username = data[CONF_USERNAME]
    password = data[CONF_PASSWORD]

    # Test authentication
    result = await hass.async_add_executor_job(
        _test_authentication, username, password
    )
    if not result["success"]:
        raise CannotConnect(result.get("error", "Unknown authentication error"))

    return {
        "title": f"LoJack ({username})",
        "asset_count": result.get("asset_count", 0),
    }


def _test_authentication(username: str, password: str) -> dict[str, Any]:
    """Test authentication with LoJack API (blocking)."""
    try:
        from lojack_clients.identity import AuthenticatedClient as IdentityClient
        from lojack_clients.identity.api.default import get_identity_token
        from lojack_clients.services import AuthenticatedClient as ServicesClient
        from lojack_clients.services.api.default import get_all_user_assets

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


class LoJackConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LoJack."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
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


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""
