"""Application core: connects the serial link, telemetry parsing, logging and commands."""

from dataclasses import dataclass, field
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from gcs.command_tracker import CommandTracker
from gcs.commands import Command
from gcs.csv_logger import TelemetryCsvLogger
from gcs.links import SerialLink
from gcs.telemetry import (
    ContainerPacket,
    Device,
    PocketQubePacket,
    TelemetryError,
    TelemetryPacket,
    device_of,
    parse_packet,
)

ACK_CHECK_INTERVAL_MS = 500
UNTRACKED_COMMANDS = ("SIMP",)  # sent every second during simulation; progress is shown elsewhere


def _per_device() -> dict[Device, int]:
    return dict.fromkeys(Device, 0)


@dataclass
class ReceptionCounters:
    received: dict[Device, int] = field(default_factory=_per_device)  # GS11
    missed: dict[Device, int] = field(default_factory=_per_device)    # gaps in PACKET_COUNT
    other_team: int = 0
    invalid: int = 0


class GroundStation(QObject):
    container_packet_received = pyqtSignal(ContainerPacket)
    pocketqube_packet_received = pyqtSignal(PocketQubePacket)
    counters_changed = pyqtSignal(ReceptionCounters)
    commands_changed = pyqtSignal(list)  # list[CommandRecord], newest first
    connection_changed = pyqtSignal(bool)
    session_reset = pyqtSignal()
    event_logged = pyqtSignal(str)

    def __init__(self, data_directory: Path, team_id: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._data_directory = data_directory
        self._team_id = team_id
        self._logger = TelemetryCsvLogger(data_directory, team_id)
        self._link: SerialLink | None = None
        self._counters = ReceptionCounters()
        self._last_packet_count: dict[Device, int | None] = dict.fromkeys(Device)
        self._last_command_count: dict[Device, int | None] = dict.fromkeys(Device)
        self._tracker = CommandTracker()
        self._ack_timer = QTimer(self)
        self._ack_timer.timeout.connect(self._expire_commands)
        self._ack_timer.start(ACK_CHECK_INTERVAL_MS)

    @property
    def team_id(self) -> str:
        return self._team_id

    @property
    def link_description(self) -> str:
        return self._link.description if self._link else ""

    @property
    def logger(self) -> TelemetryCsvLogger:
        return self._logger

    def set_team_id(self, team_id: str) -> None:
        if team_id == self._team_id:
            return
        self._logger.close()
        self._team_id = team_id
        self._logger = TelemetryCsvLogger(self._data_directory, team_id)

    # --- Link management ------------------------------------------------------

    def connect_serial(self, port_name: str, baud_rate: int) -> bool:
        self.disconnect_link()
        link = SerialLink(port_name, baud_rate, self)
        if not link.open():
            self.event_logged.emit(f"Could not open {link.description}")
            link.deleteLater()
            return False
        link.line_received.connect(self._handle_line)
        link.error_occurred.connect(lambda message: self.event_logged.emit(f"Link error: {message}"))
        self._link = link
        self.event_logged.emit(f"Connected to {link.description}")
        self.connection_changed.emit(True)
        return True

    def disconnect_link(self) -> None:
        if self._link is None:
            return
        self._link.close()
        self._link.deleteLater()
        self._link = None
        self._logger.close()
        self.event_logged.emit("Disconnected")
        self.connection_changed.emit(False)

    # --- Commands -------------------------------------------------------------

    def send(self, command: Command) -> None:
        if self._link is None:
            self.event_logged.emit(f"Not connected, command not sent: {command}")
            return
        encoded = command.encode(self._team_id)
        self._link.write_line(encoded)
        if command.name in UNTRACKED_COMMANDS:
            return
        self.event_logged.emit(f"TX  {encoded}")
        self._tracker.sent(command, self._last_command_count[command.target])
        self.commands_changed.emit(self._tracker.records)

    def _expire_commands(self) -> None:
        expired = self._tracker.expire()
        for record in expired:
            self.event_logged.emit(f"No echo for {record.command}")
        if expired:
            self.commands_changed.emit(self._tracker.records)

    # --- Session --------------------------------------------------------------

    def reset_session(self) -> None:
        """Archives the current CSV files and clears counters before a new flight."""
        self._logger.archive()
        self._counters = ReceptionCounters()
        self._last_packet_count = dict.fromkeys(Device)
        self._last_command_count = dict.fromkeys(Device)
        self._tracker.clear()
        self.counters_changed.emit(self._counters)
        self.commands_changed.emit(self._tracker.records)
        self.session_reset.emit()
        self.event_logged.emit("New flight: previous CSV files archived")

    def export_csv(self, destination: Path) -> bool:
        try:
            exported = self._logger.export_to(destination)
        except OSError as error:
            self.event_logged.emit(f"Export failed: {error}")
            return False
        names = ", ".join(path.name for path in exported) or "no files yet"
        self.event_logged.emit(f"Exported to {destination}: {names}")
        return bool(exported)

    def shutdown(self) -> None:
        self.disconnect_link()
        self._logger.close()

    # --- Telemetry handling ---------------------------------------------------

    def _handle_line(self, line: str) -> None:
        try:
            packet = parse_packet(line)
        except TelemetryError as error:
            self._counters.invalid += 1
            self.event_logged.emit(f"Invalid packet ({error}): {line}")
            self.counters_changed.emit(self._counters)
            return

        if packet.team_id != self._team_id:  # X4: only our team's telemetry
            self._counters.other_team += 1
            self.counters_changed.emit(self._counters)
            return

        device = device_of(packet)
        self._logger.write(packet)
        self._count(device, packet)
        self._last_command_count[device] = packet.command_count
        if self._tracker.echo_received(device, packet.cmd_echo, packet.command_count):
            self.commands_changed.emit(self._tracker.records)
        if isinstance(packet, ContainerPacket):
            self.container_packet_received.emit(packet)
        else:
            self.pocketqube_packet_received.emit(packet)

    def _count(self, device: Device, packet: TelemetryPacket) -> None:
        self._counters.received[device] += 1
        previous = self._last_packet_count[device]
        if previous is not None and packet.packet_count > previous + 1:
            self._counters.missed[device] += packet.packet_count - previous - 1
        self._last_packet_count[device] = packet.packet_count
        self.counters_changed.emit(self._counters)
