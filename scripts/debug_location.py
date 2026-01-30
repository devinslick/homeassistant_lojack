# Reproduce how coordinator builds asset['location'] vs how device_tracker reads it

def _get_attr(obj, attr, default=None):
    if obj is None:
        return default
    if hasattr(obj, attr):
        value = getattr(obj, attr, default)
        return value if value is not None else default
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return default


def get_location_data_like_tracker(device):
    """Mimic LoJackDeviceTracker._get_location_data"""
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

    location = _get_attr(device, "_location") or _get_attr(device, "location")

    if location:
        # Prefer nested `coordinates` if present, otherwise use top-level keys
        coords = _get_attr(location, "coordinates")
        if coords:
            location_data["latitude"] = _get_attr(coords, "latitude")
            location_data["longitude"] = _get_attr(coords, "longitude")
        else:
            location_data["latitude"] = _get_attr(location, "latitude")
            location_data["longitude"] = _get_attr(location, "longitude")

        location_data["accuracy"] = _get_attr(location, "accuracy")
        location_data["address"] = _get_attr(location, "address")
        location_data["speed"] = _get_attr(location, "speed")
        location_data["heading"] = _get_attr(location, "heading")
        location_data["timestamp"] = _get_attr(location, "timestamp")

    return location_data


if __name__ == '__main__':
    # Scenario A: coordinator builds nested-only coordinates (old behavior)
    asset_location_old = {
        "coordinates": {"latitude": 12.3456, "longitude": -98.7654},
        "accuracy": 20,
        "address": "123 Example St",
        "timestamp": "2026-01-30T12:34:56Z",
        "speed": 37.5,
        "heading": 180,
        "raw": {},
    }

    asset_old = {
        "id": "vehicle_1",
        "name": "My Car",
        "location": asset_location_old,
    }

    # Scenario B: coordinator includes top-level latitude/longitude (patched behavior)
    asset_location_new = {
        "coordinates": {"latitude": 12.3456, "longitude": -98.7654},
        "latitude": 12.3456,
        "longitude": -98.7654,
        "accuracy": 20,
        "address": "123 Example St",
        "timestamp": "2026-01-30T12:34:56Z",
        "speed": 37.5,
        "heading": 180,
        "raw": {},
    }

    asset_new = {
        "id": "vehicle_1",
        "name": "My Car",
        "location": asset_location_new,
    }

    print("Scenario A - old coordinator (nested coordinates only)")
    print(asset_old)
    print("Extracted by tracker:")
    print(get_location_data_like_tracker(asset_old))
    print()

    print("Scenario B - patched coordinator (top-level latitude/longitude present)")
    print(asset_new)
    print("Extracted by tracker:")
    print(get_location_data_like_tracker(asset_new))
