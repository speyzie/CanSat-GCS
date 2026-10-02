"""Uplink command definitions (Mission Guide: Commands section).

Wire format sent to the ground radio bridge:

    CMD,<TEAM_ID><C|P>,<NAME>[,<ARG>...]

The bridge forwards the command over ESP-NOW only to the addressed device
(X5). The flight software echoes it without commas, e.g. ``SIMP101325``.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from gcs.telemetry import Device


@dataclass(frozen=True)
class Command:
    target: Device
    name: str
    args: tuple[str, ...] = ()

    def encode(self, team_id: str) -> str:
        return ",".join(("CMD", f"{team_id}{self.target.value}", self.name, *self.args))

    @property
    def echo(self) -> str:
        """Expected CMD_ECHO text: the command without commas or team ID."""
        return self.name + "".join(self.args)

    def __str__(self) -> str:
        return " ".join((self.target.title, self.name, *self.args))


# --- Commands supported by both devices -----------------------------------

def simulation_enable(target: Device) -> Command:
    return Command(target, "SIM", ("ENABLE",))


def simulation_activate(target: Device) -> Command:
    return Command(target, "SIM", ("ACTIVATE",))


def simulation_disable(target: Device) -> Command:
    return Command(target, "SIM", ("DISABLE",))


def simulated_pressure(target: Device, pascals: int) -> Command:
    return Command(target, "SIMP", (str(pascals),))


def set_time_utc(target: Device) -> Command:
    """F3: sets mission clock to current UTC time."""
    return Command(target, "ST", (datetime.now(UTC).strftime("%H:%M:%S"),))


# --- Container commands -----------------------------------------------------

def calibrate_altitude() -> Command:
    return Command(Device.CONTAINER, "CAL")


def arm_launch_detection() -> Command:
    return Command(Device.CONTAINER, "ARM")


def release_pocketqube() -> Command:
    return Command(Device.CONTAINER, "MEC", ("RELEASE", "OPEN"))


def close_release_mechanism() -> Command:
    return Command(Device.CONTAINER, "MEC", ("RELEASE", "CLOSE"))


# --- PocketQube commands ------------------------------------------------------

def deploy_solar_panel(panel_number: int) -> Command:
    return Command(Device.POCKETQUBE, "MEC", (f"PANEL{panel_number}", "DEPLOY"))


def deploy_boom() -> Command:
    return Command(Device.POCKETQUBE, "MEC", ("BOOM", "DEPLOY"))


def camera_recording(enabled: bool) -> Command:
    return Command(Device.POCKETQUBE, "CAM", ("ON" if enabled else "OFF",))


def rotate_camera(degrees: int) -> Command:
    """C11 / PQ18: rotates camera view about the nadir axis; sign gives direction."""
    return Command(Device.POCKETQUBE, "CAM", ("ROT", f"{degrees:+d}"))


def custom(target: Device, text: str) -> Command:
    name, *args = [part.strip() for part in text.split(",") if part.strip()]
    return Command(target, name.upper(), tuple(args))
