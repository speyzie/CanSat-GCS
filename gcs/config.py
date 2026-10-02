"""Static configuration values for the ground station."""

from pathlib import Path

DEFAULT_TEAM_ID = "1000"

BAUD_RATES = (9600, 57600, 115200, 230400, 460800, 921600)
DEFAULT_BAUD_RATE = 115200

TELEMETRY_DIRECTORY = Path("flight_data")

SIMULATION_INTERVAL_MS = 1000  # GS8: simulated pressure is sent at 1 Hz

PLOT_HISTORY_LIMIT = 10_000
