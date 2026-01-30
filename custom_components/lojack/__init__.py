"""The LoJack integration for Home Assistant."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from lojack_clients import LoJackClient
from lojack_clients.exceptions import AuthenticationError, ApiError

from .const import (
    DATA_ASSETS,
    DATA_CLIENT,
    DATA_COORDINATOR,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS_LIST: list[Platform] = [Platform.DEVICE_TRACKER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LoJack from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    try:
        # Create and authenticate client
        client = await LoJackClient.create(username, password)
    except AuthenticationError as err:
        raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
    except ApiError as err:
        raise ConfigEntryAuthFailed(f"API error: {err}") from err

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
        data = hass.data[DOMAIN].pop(entry.entry_id)
        client: LoJackClient = data[DATA_CLIENT]
        await client.close()

    return unload_ok


class LoJackDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching LoJack data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: LoJackClient,
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
            # Get all devices for the user
            devices = await self.client.list_devices()

            # Process devices into a dictionary keyed by device ID
            assets_data: dict[str, Any] = {}

            for device in devices:
                device_id = str(device.id) if hasattr(device, 'id') else None
                if device_id:
                    # Get location for the device
                    try:
                        location = await device.get_location()
                        device._location = location
                    except Exception as loc_err:
                        _LOGGER.debug("Could not get location for device %s: %s", device_id, loc_err)
                    assets_data[device_id] = device

            return {DATA_ASSETS: assets_data}

        except AuthenticationError as err:
            # Try to re-authenticate
            _LOGGER.info("Token expired, re-authenticating...")
            try:
                self.client = await LoJackClient.create(self._username, self._password)
                # Retry the fetch
                return await self._async_update_data()
            except AuthenticationError as refresh_err:
                raise ConfigEntryAuthFailed(
                    f"Re-authentication failed: {refresh_err}"
                ) from refresh_err

        except ApiError as err:
            raise UpdateFailed(f"Error fetching LoJack data: {err}") from err
