"""PocketQube orientation estimate from accelerometer and magnetometer data (GS4).

Axis convention from the Mission Guide: +X (roll) east, +Y (pitch) south,
+Z (yaw) nadir. This is a right-handed, Z-down frame, so the standard
aerospace (NED-style) tilt-compensated compass equations apply. The
accelerometer is expected to report specific force, i.e. about -9.81 m/s^2
on Z when the satellite is level and at rest.
"""

from dataclasses import dataclass
from math import atan2, cos, degrees, hypot, sin

Vector3 = tuple[float, float, float]


@dataclass(frozen=True)
class Attitude:
    roll: float   # degrees
    pitch: float  # degrees
    yaw: float    # degrees, heading of +X from magnetic north, 0..360


def estimate_attitude(acceleration: Vector3, magnetic_field: Vector3) -> Attitude:
    ax, ay, az = acceleration
    mx, my, mz = magnetic_field

    roll = atan2(-ay, -az)
    pitch = atan2(ax, hypot(ay, az))

    horizontal_x = mx * cos(pitch) + (my * sin(roll) + mz * cos(roll)) * sin(pitch)
    horizontal_y = my * cos(roll) - mz * sin(roll)
    yaw = atan2(-horizontal_y, horizontal_x)

    return Attitude(
        roll=degrees(roll),
        pitch=degrees(pitch),
        yaw=degrees(yaw) % 360.0,
    )
