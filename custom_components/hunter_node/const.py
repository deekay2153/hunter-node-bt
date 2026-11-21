from datetime import timedelta

DOMAIN = "hunter_node"
CONF_PIN = "pin"
CONF_STATION = "station"  # version 1 entries: one zone
CONF_STATIONS = "stations"  # list of zone numbers 1-4
STATION_CHOICES = [1, 2, 3, 4]

IDLE_INTERVAL = timedelta(minutes=30)  # battery device: keep idle connections rare
RUNNING_INTERVAL = timedelta(seconds=30)
DEFAULT_RUN_MINUTES = 10

CONTROLLER_STATES = [
    "idle",
    "manual_station",
    "system_off",
    "programmable_off",
    "rain_off",
    "rain_delay",
    "soil_off",
    "program_a_running",
    "program_b_running",
    "program_c_running",
    "manual_run_all",
    "manual_program_a",
    "manual_program_b",
    "manual_program_c",
]
