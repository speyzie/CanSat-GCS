"""Telemetry packet models and parsing (Mission Guide: Telemetry section).

Packets arrive as ASCII CSV lines. The ID field (e.g. ``1000C`` / ``1000P``)
identifies the team and the device that sent the packet.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar


class Device(Enum):
    CONTAINER = "C"
    POCKETQUBE = "P"

    @property
    def title(self) -> str:
        return "Container" if self is Device.CONTAINER else "PocketQube"


class TelemetryError(ValueError):
    """Raised when a line is not a valid telemetry packet."""


MODE_NAMES = {"F": "FLIGHT", "S": "SIMULATION"}


class FlightState(Enum):
    LAUNCH_PAD = "LAUNCH_PAD"
    ASCENT = "ASCENT"
    APOGEE = "APOGEE"
    PQ_RELEASE = "PQ_RELEASE"


class _FieldReader:
    """Reads CSV fields sequentially, converting each to the expected type."""

    def __init__(self, fields: list[str]) -> None:
        self._fields = fields
        self._index = 0

    def text(self) -> str:
        if self._index >= len(self._fields):
            raise TelemetryError(f"missing field #{self._index + 1}")
        value = self._fields[self._index]
        self._index += 1
        return value

    def number(self) -> float:
        return self._convert(float)

    def integer(self) -> int:
        return self._convert(int)

    def hex(self) -> int:
        return self._convert(lambda value: int(value, 16))

    def remaining(self) -> tuple[str, ...]:
        rest = tuple(self._fields[self._index:])
        self._index = len(self._fields)
        return rest

    def _convert(self, converter):
        value = self.text()
        try:
            return converter(value)
        except ValueError:
            raise TelemetryError(f"field #{self._index} has invalid value '{value}'") from None


@dataclass(frozen=True)
class ContainerPacket:
    FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        "ID", "MISSION_TIME", "PACKET_COUNT", "COMMAND_COUNT", "MODE", "ALTITUDE",
        "PRESSURE", "TEMPERATURE", "BATT_V", "BATT_I", "MECH_STATE", "STATE", "CMD_ECHO",
    )

    team_id: str
    mission_time: float
    packet_count: int
    command_count: int
    mode: str
    altitude: float
    pressure: float
    temperature: float
    battery_voltage: float
    battery_current: float
    mech_state: int
    state: str
    cmd_echo: str
    raw_fields: tuple[str, ...]

    @property
    def release_activated(self) -> bool:
        return bool(self.mech_state & 0b01)

    @property
    def pocketqube_released(self) -> bool:
        return bool(self.mech_state & 0b10)

    @classmethod
    def from_fields(cls, fields: list[str]) -> ContainerPacket:
        reader = _FieldReader(fields)
        packet = cls(
            team_id=reader.text()[:-1],
            mission_time=reader.number(),
            packet_count=reader.integer(),
            command_count=reader.integer(),
            mode=reader.text(),
            altitude=reader.number(),
            pressure=reader.number(),
            temperature=reader.number(),
            battery_voltage=reader.number(),
            battery_current=reader.number(),
            mech_state=reader.hex(),
            state=reader.text(),
            cmd_echo=reader.text(),
            raw_fields=tuple(fields),
        )
        if reader.remaining():
            raise TelemetryError(f"container packet has more than {len(cls.FIELD_NAMES)} fields")
        return packet


@dataclass(frozen=True)
class PocketQubePacket:
    FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        "ID", "MODE", "MISSION_TIME", "PACKET_COUNT", "COMMAND_COUNT", "ALTITUDE",
        "TEMPERATURE", "PRESSURE", "VOLTAGE", "CURRENT", "GNSS_TIME", "GNSS_ALTITUDE",
        "GNSS_LATITUDE", "GNSS_LONGITUDE", "GNSS_SATS", "ROT_RATE_X", "ROT_RATE_Y",
        "ROT_RATE_Z", "ACCEL_X", "ACCEL_Y", "ACCEL_Z", "MAG_X", "MAG_Y", "MAG_Z",
        "SOLAR_1", "SOLAR_2", "MECH_STATE", "CMD_ECHO",
    )
    # Team-defined trailing fields; their count depends on the team implementation.
    EXTRA_FIELD_NAMES: ClassVar[tuple[str, ...]] = ("IMAGE_STABILIZATION", "SCIENCE_EXP")

    team_id: str
    mode: str
    mission_time: float
    packet_count: int
    command_count: int
    altitude: float
    temperature: float
    pressure: float
    voltage: float
    current: float
    gnss_time: str
    gnss_altitude: float
    gnss_latitude: float
    gnss_longitude: float
    gnss_sats: int
    rotation_rate: tuple[float, float, float]
    acceleration: tuple[float, float, float]
    magnetic_field: tuple[float, float, float]
    solar_1: float
    solar_2: float
    mech_state: int
    cmd_echo: str
    extra_fields: tuple[str, ...]
    raw_fields: tuple[str, ...]

    @property
    def solar_panel_1_deployed(self) -> bool:
        return bool(self.mech_state & 0b0001)

    @property
    def solar_panel_2_deployed(self) -> bool:
        return bool(self.mech_state & 0b0010)

    @property
    def boom_deployed(self) -> bool:
        return bool(self.mech_state & 0b0100)

    @property
    def camera_recording(self) -> bool:
        return bool(self.mech_state & 0b1000)

    @classmethod
    def from_fields(cls, fields: list[str]) -> PocketQubePacket:
        reader = _FieldReader(fields)
        return cls(
            team_id=reader.text()[:-1],
            mode=reader.text(),
            mission_time=reader.number(),
            packet_count=reader.integer(),
            command_count=reader.integer(),
            altitude=reader.number(),
            temperature=reader.number(),
            pressure=reader.number(),
            voltage=reader.number(),
            current=reader.number(),
            gnss_time=reader.text(),
            gnss_altitude=reader.number(),
            gnss_latitude=reader.number(),
            gnss_longitude=reader.number(),
            gnss_sats=reader.integer(),
            rotation_rate=(reader.number(), reader.number(), reader.number()),
            acceleration=(reader.number(), reader.number(), reader.number()),
            magnetic_field=(reader.number(), reader.number(), reader.number()),
            solar_1=reader.number(),
            solar_2=reader.number(),
            mech_state=reader.hex(),
            cmd_echo=reader.text(),
            extra_fields=reader.remaining(),
            raw_fields=tuple(fields),
        )


TelemetryPacket = ContainerPacket | PocketQubePacket

_PACKET_TYPES: dict[Device, type[ContainerPacket] | type[PocketQubePacket]] = {
    Device.CONTAINER: ContainerPacket,
    Device.POCKETQUBE: PocketQubePacket,
}


def device_of(packet: TelemetryPacket) -> Device:
    return Device.CONTAINER if isinstance(packet, ContainerPacket) else Device.POCKETQUBE


def parse_packet(line: str) -> TelemetryPacket:
    """Parses one telemetry line. Raises TelemetryError for malformed lines."""
    fields = [field.strip() for field in line.strip().split(",")]
    device_id = fields[0]
    if len(device_id) < 2:
        raise TelemetryError(f"invalid packet ID '{device_id}'")
    try:
        device = Device(device_id[-1].upper())
    except ValueError:
        raise TelemetryError(f"unknown device suffix in ID '{device_id}'") from None
    return _PACKET_TYPES[device].from_fields(fields)
