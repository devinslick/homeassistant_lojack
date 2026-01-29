"""The LoJack integration for Home Assistant."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from lojack_clients.identity import AuthenticatedClient as IdentityClient
from lojack_clients.identity.api.default import get_identity_token
from lojack_clients.services import AuthenticatedClient as ServicesClient
from lojack_clients.services.api.default import get_all_user_assets, get_asset

from .const import (
    CONF_PASSWORD,
    CONF_TOKEN,
    CONF_TOKEN_EXPIRES,
    CONF_USERNAME,
    DATA_ASSETS,
    DATA_CLIENT,
    DATA_COORDINATOR,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS_LIST: list[Platform] = [Platform.DEVICE_TRACKER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LoJack from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    try:
        # Authenticate and get services client
        client = await hass.async_add_executor_job(
            _authenticate, username, password
        )
    except Exception as err:
        _LOGGER.error("Failed to authenticate with LoJack: %s", err)
        raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err

    # Create the data update coordinator
    coordinator = LoJackDataUpdateCoordinator(
        hass,
        client,
        entry,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_CLIENT: client,
        DATA_COORDINATOR: coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS_LIST)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS_LIST)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


def _authenticate(username: str, password: str) -> ServicesClient:
    """Authenticate with LoJack and return a services client."""
    # Create identity client and get token
    identity_client = IdentityClient.from_login(username, password)
    token_response = get_identity_token.sync(client=identity_client)

    if token_response is None:
        raise ConfigEntryAuthFailed("Failed to get authentication token")

    # Create services client with the token
    services_client = ServicesClient.from_token(token_response.token)

    return services_client


def _refresh_token(username: str, password: str) -> ServicesClient:
    """Refresh the authentication token."""
    return _authenticate(username, password)


class LoJackDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching LoJack data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: ServicesClient,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        self.client = client
        self.entry = entry
        self._username = entry.data[CONF_USERNAME]
        self._password = entry.data[CONF_PASSWORD]

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                minutes=entry.options.get("poll_interval", DEFAULT_POLL_INTERVAL)
            ),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from LoJack API."""
        try:
            # Get all assets for the user
            assets_response = await self.hass.async_add_executor_job(
                self._fetch_assets
            )

            if assets_response is None:
                raise UpdateFailed("Failed to fetch assets from LoJack")

            # Process assets into a dictionary keyed by asset ID
            assets_data: dict[str, Any] = {}

            if hasattr(assets_response, 'assets') and assets_response.assets:
                for asset in assets_response.assets:
                    asset_id = str(asset.id) if hasattr(asset, 'id') else None
                    if asset_id:
                        # Fetch detailed asset info including location
                        detailed_asset = await self.hass.async_add_executor_job(
                            self._fetch_asset_detail, asset_id
                        )
                        if detailed_asset:
                            assets_data[asset_id] = detailed_asset
                        else:
                            assets_data[asset_id] = asset

            return {DATA_ASSETS: assets_data}

        except Exception as err:
            # Try to refresh the token if we get an auth error
            if "401" in str(err) or "unauthorized" in str(err).lower():
                _LOGGER.info("Token expired, refreshing...")
                try:
                    self.client = await self.hass.async_add_executor_job(
                        _refresh_token, self._username, self._password
                    )
                    # Retry the fetch
                    return await self._async_update_data()
                except Exception as refresh_err:
                    raise ConfigEntryAuthFailed(
                        f"Failed to refresh token: {refresh_err}"
                    ) from refresh_err
            raise UpdateFailed(f"Error fetching LoJack data: {err}") from err

    def _fetch_assets(self):
        """Fetch all user assets (blocking)."""
        return get_all_user_assets.sync(client=self.client)

    def _fetch_asset_detail(self, asset_id: str):
        """Fetch detailed asset information (blocking)."""
        try:
            return get_asset.sync(id=asset_id, client=self.client)
        except Exception as err:
            _LOGGER.warning("Failed to fetch details for asset %s: %s", asset_id, err)
            return None
