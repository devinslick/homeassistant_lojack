"""Device tracker platform for LoJack integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_ADDRESS,
    ATTR_BATTERY_VOLTAGE,
    ATTR_COLOR,
    ATTR_HEADING,
    ATTR_LAST_UPDATED,
    ATTR_LICENSE_PLATE,
    ATTR_MAKE,
    ATTR_MODEL,
    ATTR_ODOMETER,
    ATTR_SPEED,
    ATTR_VIN,
    ATTR_YEAR,
    DATA_ASSETS,
    DATA_COORDINATOR,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LoJack device tracker from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    entities: list[LoJackDeviceTracker] = []

    # Create a device tracker for each device
    if coordinator.data and DATA_ASSETS in coordinator.data:
        for device_id, device in coordinator.data[DATA_ASSETS].items():
            entities.append(
                LoJackDeviceTracker(
                    coordinator,
                    entry,
                    device_id,
                    device,
                )
            )

    async_add_entities(entities)


class LoJackDeviceTracker(CoordinatorEntity, TrackerEntity):
    """Representation of a LoJack device tracker."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        device_id: str,
        device: Any,
    ) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator)
        self._entry = entry
        self._device_id = device_id
        self._device = device

        # Extract vehicle info for device identification
        self._vin = self._get_attr(device, "vin", "")
        self._make = self._get_attr(device, "make", "")
        self._model = self._get_attr(device, "model", "")
        self._year = str(self._get_attr(device, "year", "") or "")
        self._color = self._get_attr(device, "color", "")
        self._name = self._get_attr(device, "name", "")

        # Generate a friendly name
        if self._name:
            self._friendly_name = self._name
        elif self._year and self._make and self._model:
            self._friendly_name = f"{self._year} {self._make} {self._model}"
        else:
            self._friendly_name = f"Vehicle {device_id}"

        # Set unique ID
        self._attr_unique_id = f"{DOMAIN}_{device_id}"

    def _get_attr(self, obj: Any, attr: str, default: Any = None) -> Any:
        """Safely get an attribute from an object."""
        if obj is None:
            return default

        # Try direct attribute access
        if hasattr(obj, attr):
            value = getattr(obj, attr, default)
            return value if value is not None else default

        # Try dictionary access
        if isinstance(obj, dict):
            return obj.get(attr, default)

        return default

    def _get_location_data(self, device: Any) -> dict[str, Any]:
        """Extract location data from device."""
        location_data = {
            "latitude": None,
            "longitude": None,
            "accuracy": None,
            "address": None,
            "speed": None,
            "heading": None,
            "timestamp": None,
        }

        if device is None:
            return location_data

        # Try to get location from device._location (set by coordinator)
        location = self._get_attr(device, "_location") or self._get_attr(device, "location")

        if location:
            # Some coordinator/client implementations nest coords under `coordinates`.
            coords = self._get_attr(location, "coordinates")

            if coords:
                location_data["latitude"] = self._get_attr(coords, "latitude")
                location_data["longitude"] = self._get_attr(coords, "longitude")
            else:
                location_data["latitude"] = self._get_attr(location, "latitude")
                location_data["longitude"] = self._get_attr(location, "longitude")

            location_data["accuracy"] = self._get_attr(location, "accuracy")
            location_data["address"] = self._get_attr(location, "address")
            location_data["speed"] = self._get_attr(location, "speed")
            location_data["heading"] = self._get_attr(location, "heading")
            location_data["timestamp"] = self._get_attr(location, "timestamp")

        return location_data

    @property
    def current_device(self) -> Any:
        """Get the current device data from coordinator."""
        if (
            self.coordinator.data
            and DATA_ASSETS in self.coordinator.data
            and self._device_id in self.coordinator.data[DATA_ASSETS]
        ):
            return self.coordinator.data[DATA_ASSETS][self._device_id]
        return self._device

    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self._friendly_name

    @property
    def source_type(self) -> SourceType:
        """Return the source type of the device."""
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        """Return the latitude of the device."""
        location = self._get_location_data(self.current_device)
        lat = location.get("latitude")
        if lat is not None:
            try:
                return float(lat)
            except (ValueError, TypeError):
                return None
        return None

    @property
    def longitude(self) -> float | None:
        """Return the longitude of the device."""
        location = self._get_location_data(self.current_device)
        lng = location.get("longitude")
        if lng is not None:
            try:
                return float(lng)
            except (ValueError, TypeError):
                return None
        return None

    @property
    def location_accuracy(self) -> int:
        """Return the location accuracy of the device."""
        location = self._get_location_data(self.current_device)
        accuracy = location.get("accuracy")
        if accuracy is not None:
            try:
                return int(accuracy)
            except (ValueError, TypeError):
                return 0
        return 0

    @property
    def battery_level(self) -> int | None:
        """Return the battery level of the device (if applicable)."""
        # LoJack devices report vehicle battery voltage, not percentage
        return None

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._friendly_name,
            "manufacturer": "Spireon LoJack",
        }

        if self._make:
            info["model"] = f"{self._make} {self._model}" if self._model else self._make

        if self._vin:
            info["serial_number"] = self._vin

        return info

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        device = self.current_device
        attrs: dict[str, Any] = {}

        # Vehicle identification
        vin = self._get_attr(device, "vin")
        if vin:
            attrs[ATTR_VIN] = vin

        make = self._get_attr(device, "make")
        if make:
            attrs[ATTR_MAKE] = make

        model = self._get_attr(device, "model")
        if model:
            attrs[ATTR_MODEL] = model

        year = self._get_attr(device, "year")
        if year:
            attrs[ATTR_YEAR] = str(year)

        color = self._get_attr(device, "color")
        if color:
            attrs[ATTR_COLOR] = color

        license_plate = self._get_attr(device, "license_plate")
        if license_plate:
            attrs[ATTR_LICENSE_PLATE] = license_plate

        odometer = self._get_attr(device, "odometer")
        if odometer is not None:
            try:
                attrs[ATTR_ODOMETER] = round(float(odometer), 1)
            except (ValueError, TypeError):
                pass

        battery_voltage = self._get_attr(device, "battery_voltage")
        if battery_voltage is not None:
            try:
                attrs[ATTR_BATTERY_VOLTAGE] = round(float(battery_voltage), 2)
            except (ValueError, TypeError):
                pass

        # Location-related attributes
        location = self._get_location_data(device)

        if location.get("address"):
            addr = location["address"]
            # If the address is a dict, format common parts into a readable string
            if isinstance(addr, dict):
                parts: list[str] = []
                # Common keys returned by the API
                for key in ("line1", "line2", "city", "stateOrProvince", "postalCode"):
                    # Support both camelCase and lowercase keys just in case
                    val = addr.get(key)
                    if val is None:
                        val = addr.get(key.lower())
                    if val:
                        parts.append(str(val))

                if parts:
                    attrs[ATTR_ADDRESS] = ", ".join(parts)
                else:
                    attrs[ATTR_ADDRESS] = str(addr)
            else:
                attrs[ATTR_ADDRESS] = str(addr)

        if location.get("speed") is not None:
            try:
                attrs[ATTR_SPEED] = round(float(location["speed"]), 1)
            except (ValueError, TypeError):
                pass

        if location.get("heading") is not None:
            try:
                attrs[ATTR_HEADING] = float(location["heading"])
            except (ValueError, TypeError):
                pass

        if location.get("timestamp"):
            attrs[ATTR_LAST_UPDATED] = str(location["timestamp"])

        return attrs

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
