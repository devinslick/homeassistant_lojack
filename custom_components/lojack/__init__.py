"""The LoJack integration for Home Assistant."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from lojack_clients import LoJackClient
from lojack_clients.exceptions import AuthenticationError, ApiError

from .const import (
    DATA_ASSETS,
    DATA_CLIENT,
    DATA_COORDINATOR,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
)

if TYPE_CHECKING:
    from lojack_clients.api import LoJackClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS_LIST: list[Platform] = [Platform.DEVICE_TRACKER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LoJack from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    try:
        client = await _authenticate(hass, username, password)
    except AuthenticationError as err:
        raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
    except ApiError as err:
        raise ConfigEntryAuthFailed(f"API error: {err}") from err
    except Exception as err:
        _LOGGER.error("Failed to authenticate with LoJack: %s", err)
        raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err

    # Create the data update coordinator
    coordinator = LoJackDataUpdateCoordinator(hass, client, entry)

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


async def _authenticate(hass: HomeAssistant, username: str, password: str) -> "LoJackClient":
    """Authenticate with LoJack and return an async LoJackClient."""
    from lojack_clients import LoJackClient

    session = async_get_clientsession(hass)

    # v0.3.0 API: create(username, password, session=session)
    client = await LoJackClient.create(username, password, session=session)
    return client


async def _refresh_token(hass: HomeAssistant, username: str, password: str) -> "LoJackClient":
    """Refresh the authentication by creating a new client."""
    return await _authenticate(hass, username, password)


class LoJackDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching LoJack data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: "LoJackClient",
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
            devices = await self.client.list_devices()

            assets_data: dict[str, Any] = {}

            for device in devices:
                device_id = getattr(device, "id", None)
                if not device_id:
                    continue

                # Try to get latest location
                try:
                    location = await device.get_location()
                except Exception:
                    location = None

                asset: dict[str, Any] = {
                    "id": device_id,
                    "name": getattr(device, "name", None),
                    "vin": getattr(device, "vin", None),
                    "make": getattr(device, "make", None),
                    "model": getattr(device, "model", None),
                    "year": getattr(device, "year", None),
                    "licensePlate": getattr(device, "license_plate", None),
                    "odometer": getattr(device, "odometer", None),
                }

                if location:
                    coords = None
                    if getattr(location, "latitude", None) is not None and getattr(location, "longitude", None) is not None:
                        coords = {
                            "latitude": getattr(location, "latitude", None),
                            "longitude": getattr(location, "longitude", None),
                        }

                    asset_location: dict[str, Any] = {
                        "coordinates": coords,
                        "accuracy": getattr(location, "accuracy", None),
                        "address": getattr(location, "address", None),
                        "timestamp": getattr(location, "timestamp", None),
                        "speed": getattr(location, "speed", None),
                        "heading": getattr(location, "heading", None),
                        "raw": getattr(location, "raw", None),
                    }

                    asset["location"] = asset_location

                assets_data[str(device_id)] = asset

            return {DATA_ASSETS: assets_data}

        except AuthenticationError as err:
            _LOGGER.info("Token expired, refreshing...")
            try:
                self.client = await _refresh_token(self.hass, self._username, self._password)
                return await self._async_update_data()
            except Exception as refresh_err:
                raise ConfigEntryAuthFailed(
                    f"Failed to refresh token: {refresh_err}"
                ) from refresh_err

        except ApiError as err:
            raise UpdateFailed(f"Error fetching LoJack data: {err}") from err

        except Exception as err:
            if "401" in str(err) or "unauthorized" in str(err).lower():
                _LOGGER.info("Token expired, refreshing...")
                try:
                    self.client = await _refresh_token(self.hass, self._username, self._password)
                    return await self._async_update_data()
                except Exception as refresh_err:
                    raise ConfigEntryAuthFailed(
                        f"Failed to refresh token: {refresh_err}"
                    ) from refresh_err
            raise UpdateFailed(f"Error fetching LoJack data: {err}") from err
