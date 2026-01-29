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
    ATTR_GPS_QUALITY,
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
    KMH_TO_MPH,
    KM_TO_MILES,
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

    # Create a device tracker for each asset
    if coordinator.data and DATA_ASSETS in coordinator.data:
        for asset_id, asset in coordinator.data[DATA_ASSETS].items():
            entities.append(
                LoJackDeviceTracker(
                    coordinator,
                    entry,
                    asset_id,
                    asset,
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
        asset_id: str,
        asset: Any,
    ) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator)
        self._entry = entry
        self._asset_id = asset_id
        self._asset = asset

        # Extract vehicle info for device identification
        self._vin = self._get_attr(asset, "vin", "")
        self._make = self._get_attr(asset, "make", "")
        self._model = self._get_attr(asset, "model", "")
        self._year = self._get_attr(asset, "year", "")
        self._color = self._get_attr(asset, "color", "")
        self._name = self._get_attr(asset, "name", "") or self._get_attr(
            asset, "alias", ""
        )

        # Generate a friendly name
        if self._name:
            self._friendly_name = self._name
        elif self._year and self._make and self._model:
            self._friendly_name = f"{self._year} {self._make} {self._model}"
        else:
            self._friendly_name = f"Vehicle {asset_id}"

        # Set unique ID
        self._attr_unique_id = f"{DOMAIN}_{asset_id}"

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

        # Try nested attributes (e.g., for location.coordinates)
        if hasattr(obj, 'attributes') and obj.attributes:
            attrs = obj.attributes
            if hasattr(attrs, attr):
                return getattr(attrs, attr, default)
            if isinstance(attrs, dict):
                return attrs.get(attr, default)

        return default

    def _get_location(self, asset: Any) -> dict[str, Any]:
        """Extract location data from asset."""
        location_data = {
            "latitude": None,
            "longitude": None,
            "accuracy": None,
        }

        if asset is None:
            return location_data

        # Try to get location from asset.location
        location = self._get_attr(asset, "location")
        if location:
            # Try coordinates object
            coords = self._get_attr(location, "coordinates")
            if coords:
                location_data["latitude"] = self._get_attr(coords, "latitude")
                location_data["longitude"] = self._get_attr(coords, "longitude")
            else:
                # Try direct lat/lng on location
                location_data["latitude"] = self._get_attr(location, "latitude")
                location_data["longitude"] = self._get_attr(location, "longitude")

            location_data["accuracy"] = self._get_attr(location, "accuracy")

        # Try direct lat/lng on asset
        if location_data["latitude"] is None:
            location_data["latitude"] = self._get_attr(asset, "latitude")
            location_data["longitude"] = self._get_attr(asset, "longitude")

        return location_data

    @property
    def current_asset(self) -> Any:
        """Get the current asset data from coordinator."""
        if (
            self.coordinator.data
            and DATA_ASSETS in self.coordinator.data
            and self._asset_id in self.coordinator.data[DATA_ASSETS]
        ):
            return self.coordinator.data[DATA_ASSETS][self._asset_id]
        return self._asset

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
        location = self._get_location(self.current_asset)
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
        location = self._get_location(self.current_asset)
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
        location = self._get_location(self.current_asset)
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
        # Return None as this isn't a 0-100 battery level
        return None

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        info = {
            "identifiers": {(DOMAIN, self._asset_id)},
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
        asset = self.current_asset
        attrs: dict[str, Any] = {}

        # Vehicle identification
        vin = self._get_attr(asset, "vin")
        if vin:
            attrs[ATTR_VIN] = vin

        make = self._get_attr(asset, "make")
        if make:
            attrs[ATTR_MAKE] = make

        model = self._get_attr(asset, "model")
        if model:
            attrs[ATTR_MODEL] = model

        year = self._get_attr(asset, "year")
        if year:
            attrs[ATTR_YEAR] = year

        color = self._get_attr(asset, "color")
        if color:
            attrs[ATTR_COLOR] = color

        license_plate = self._get_attr(asset, "licensePlate") or self._get_attr(
            asset, "license_plate"
        )
        if license_plate:
            attrs[ATTR_LICENSE_PLATE] = license_plate

        # Location-related attributes
        location = self._get_attr(asset, "location")
        if location:
            # Address
            address = self._get_attr(location, "address")
            if address:
                # Address might be an object with formatted string
                if hasattr(address, "formatted"):
                    attrs[ATTR_ADDRESS] = address.formatted
                elif isinstance(address, str):
                    attrs[ATTR_ADDRESS] = address
                elif isinstance(address, dict):
                    attrs[ATTR_ADDRESS] = address.get("formatted", str(address))

            # GPS quality
            gps_quality = self._get_attr(location, "gpsFixQuality") or self._get_attr(
                location, "gps_fix_quality"
            )
            if gps_quality:
                attrs[ATTR_GPS_QUALITY] = str(gps_quality)

        # Vehicle telemetry
        speed = self._get_attr(asset, "speed")
        if speed is not None:
            try:
                # Convert from km/h to mph
                attrs[ATTR_SPEED] = round(float(speed) * KMH_TO_MPH, 1)
            except (ValueError, TypeError):
                pass

        heading = self._get_attr(asset, "heading")
        if heading is not None:
            try:
                attrs[ATTR_HEADING] = float(heading)
            except (ValueError, TypeError):
                pass

        odometer = self._get_attr(asset, "odometer")
        if odometer is not None:
            try:
                # Convert from km to miles
                attrs[ATTR_ODOMETER] = round(float(odometer) * KM_TO_MILES, 1)
            except (ValueError, TypeError):
                pass

        battery_voltage = self._get_attr(asset, "batteryVoltage") or self._get_attr(
            asset, "battery_voltage"
        )
        if battery_voltage is not None:
            try:
                attrs[ATTR_BATTERY_VOLTAGE] = round(float(battery_voltage), 2)
            except (ValueError, TypeError):
                pass

        # Timestamps
        last_updated = (
            self._get_attr(asset, "lastUpdated")
            or self._get_attr(asset, "last_updated")
            or self._get_attr(asset, "timestamp")
        )
        if last_updated:
            attrs[ATTR_LAST_UPDATED] = str(last_updated)

        return attrs

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
