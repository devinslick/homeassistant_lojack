from scripts.debug_location import get_location_data_like_tracker


def test_get_location_data_prefers_coordinates():
    asset_location_old = {
        "coordinates": {"latitude": 12.3456, "longitude": -98.7654},
        "accuracy": 20,
        "address": "123 Example St",
        "timestamp": "2026-01-30T12:34:56Z",
        "speed": 37.5,
        "heading": 180,
        "raw": {},
    }

    asset_old = {"id": "vehicle_1", "name": "My Car", "location": asset_location_old}

    loc = get_location_data_like_tracker(asset_old)

    assert loc["latitude"] == 12.3456
    assert loc["longitude"] == -98.7654


def test_get_location_data_falls_back_to_top_level():
    asset_location_new = {
        "coordinates": {"latitude": 12.3456, "longitude": -98.7654},
        "latitude": 98.7654,
        "longitude": -12.3456,
        "accuracy": 20,
        "address": "123 Example St",
        "timestamp": "2026-01-30T12:34:56Z",
        "speed": 37.5,
        "heading": 180,
        "raw": {},
    }

    asset_new = {"id": "vehicle_1", "name": "My Car", "location": asset_location_new}

    # Function prefers nested coordinates over top-level keys
    loc = get_location_data_like_tracker(asset_new)

    assert loc["latitude"] == 12.3456
    assert loc["longitude"] == -98.7654
