"""Constants for the Free Sleep integration."""

DOMAIN = "free_sleep"

CONF_HOST = "host"
CONF_PORT = "port"

DEFAULT_PORT = 3000
SCAN_INTERVAL_SECONDS = 30

# Temperature range (Fahrenheit) from the free-sleep deviceStatusSchema
MIN_TEMP_F = 55
MAX_TEMP_F = 110

PLATFORMS = [
    "binary_sensor",
    "button",
    "climate",
    "number",
    "sensor",
    "switch",
    "time",
]
