"""Constants for the LoJack integration."""

DOMAIN = "lojack"

# Platforms
PLATFORMS = ["device_tracker"]

# Polling intervals (in minutes)
DEFAULT_POLL_INTERVAL = 5
MIN_POLL_INTERVAL = 1
MAX_POLL_INTERVAL = 60

# Data keys
DATA_CLIENT = "client"
DATA_COORDINATOR = "coordinator"
DATA_ASSETS = "assets"

# Attribute keys
ATTR_BATTERY_VOLTAGE = "battery_voltage"
ATTR_SPEED = "speed"
ATTR_ODOMETER = "odometer"
ATTR_HEADING = "heading"
ATTR_LAST_UPDATED = "last_updated"
ATTR_VIN = "vin"
ATTR_MAKE = "make"
ATTR_MODEL = "model"
ATTR_YEAR = "year"
ATTR_COLOR = "color"
ATTR_LICENSE_PLATE = "license_plate"
ATTR_ADDRESS = "address"
