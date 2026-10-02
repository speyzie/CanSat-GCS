"""Always-visible summary of both devices (GS1, GS11).

Each side shows the flight state, altitude in large digits, packets received
by the ground station, packets missed (gaps in PACKET_COUNT), the device's
own packet number, mode, last command echo and time since the last packet.
"""

from PyQt6.QtCore import QElapsedTimer, Qt, QTimer
from PyQt6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QWidget

from gcs.ground_station import ReceptionCounters
from gcs.telemetry import MODE_NAMES, ContainerPacket, Device, FlightState, PocketQubePacket
from gcs.ui import theme
from gcs.ui.widgets import PLACEHOLDER, make_badge

STALE_AFTER_SECONDS = 2.0
LOST_AFTER_SECONDS = 5.0
AGE_REFRESH_MS = 250

_STATE_LEVELS = {
    FlightState.LAUNCH_PAD.value: "active",
    FlightState.ASCENT.value: "active",
    FlightState.APOGEE.value: "active",
    FlightState.PQ_RELEASE.value: "ok",
}


def _metric(name: str, value: str, color: str = theme.TEXT) -> str:
    return (f"<span style='color:{theme.SECONDARY_TEXT}'>{name}</span>&nbsp;"
            f"<b style='color:{color}'>{value}</b>")


class DeviceSummary(QFrame):
    def __init__(self, device: Device, idle_state: str) -> None:
        super().__init__()
        self.setObjectName("Card")
        self._idle_state = idle_state
        self._since_last_packet = QElapsedTimer()

        name = QLabel(device.title.upper())
        name.setObjectName("DeviceName")
        self._state = make_badge()
        self._age = QLabel()
        self._altitude = QLabel()
        self._altitude.setObjectName("BigValue")
        altitude_unit = QLabel("m")
        altitude_unit.setObjectName("Unit")
        self._received = QLabel()
        self._missed = QLabel()
        self._packet_number = QLabel()
        self._mode = QLabel()
        self._echo = QLabel()

        top = QHBoxLayout()
        top.setSpacing(10)
        top.addWidget(name)
        top.addWidget(self._state)
        top.addStretch()
        top.addWidget(self._age)

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(22)
        metrics.setVerticalSpacing(0)
        metrics.addWidget(self._received, 0, 0)
        metrics.addWidget(self._missed, 0, 1)
        metrics.addWidget(self._packet_number, 0, 2)
        metrics.addWidget(self._mode, 1, 0)
        metrics.addWidget(self._echo, 1, 1, 1, 2)
        metrics.setColumnStretch(3, 1)

        bottom = QHBoxLayout()
        bottom.setSpacing(6)
        altitude_name = QLabel("Altitude")
        altitude_name.setObjectName("Caption")
        bottom.addWidget(altitude_name, alignment=Qt.AlignmentFlag.AlignBaseline)
        bottom.addWidget(self._altitude, alignment=Qt.AlignmentFlag.AlignBaseline)
        bottom.addWidget(altitude_unit, alignment=Qt.AlignmentFlag.AlignBaseline)
        bottom.addSpacing(24)
        bottom.addLayout(metrics, stretch=1)

        layout = QGridLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setVerticalSpacing(2)
        layout.addLayout(top, 0, 0)
        layout.addLayout(bottom, 1, 0)

        age_timer = QTimer(self)
        age_timer.timeout.connect(self._update_age)
        age_timer.start(AGE_REFRESH_MS)
        self.clear()

    def show_packet(self, altitude: float, packet_number: int, mode: str, cmd_echo: str,
                    state: str, level: str) -> None:
        self._since_last_packet.start()
        self._altitude.setText(f"{altitude:.1f}")
        self._packet_number.setText(_metric("Packet #", str(packet_number)))
        self._mode.setText(_metric("Mode", MODE_NAMES.get(mode, mode),
                                   theme.WARNING if mode == "S" else theme.TEXT))
        self._echo.setText(_metric("Echo", cmd_echo))
        self._state.setText(state)
        theme.set_level(self._state, level)
        self._update_age()

    def show_counts(self, received: int, missed: int) -> None:
        self._received.setText(_metric("Received", str(received)))
        self._missed.setText(_metric("Missed", str(missed), theme.ALARM if missed else theme.TEXT))

    def clear(self) -> None:
        self._since_last_packet.invalidate()
        self._state.setText(self._idle_state)
        theme.set_level(self._state, "idle")
        self._altitude.setText(PLACEHOLDER)
        self.show_counts(0, 0)
        self._packet_number.setText(_metric("Packet #", PLACEHOLDER))
        self._mode.setText(_metric("Mode", PLACEHOLDER))
        self._echo.setText(_metric("Echo", PLACEHOLDER))
        self._update_age()

    def _update_age(self) -> None:
        if not self._since_last_packet.isValid():
            self._age.setText(_metric("Last packet", "none", theme.INACTIVE))
            return
        seconds = self._since_last_packet.elapsed() / 1000.0
        if seconds >= LOST_AFTER_SECONDS:
            color = theme.ALARM
        elif seconds >= STALE_AFTER_SECONDS:
            color = theme.WARNING
        else:
            color = theme.OK
        self._age.setText(_metric("Last packet", f"{seconds:.1f} s ago", color))


class StatusStrip(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._summaries = {
            Device.CONTAINER: DeviceSummary(Device.CONTAINER, "NO DATA"),
            Device.POCKETQUBE: DeviceSummary(Device.POCKETQUBE, "STOWED"),
        }
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        for summary in self._summaries.values():
            layout.addWidget(summary, stretch=1)

    def show_container(self, packet: ContainerPacket) -> None:
        self._summaries[Device.CONTAINER].show_packet(
            packet.altitude, packet.packet_count, packet.mode, packet.cmd_echo,
            packet.state.replace("_", " "), _STATE_LEVELS.get(packet.state, "warning"))

    def show_pocketqube(self, packet: PocketQubePacket) -> None:
        self._summaries[Device.POCKETQUBE].show_packet(
            packet.altitude, packet.packet_count, packet.mode, packet.cmd_echo, "TRANSMITTING", "ok")

    def show_counters(self, counters: ReceptionCounters) -> None:
        for device, summary in self._summaries.items():
            summary.show_counts(counters.received[device], counters.missed[device])

    def clear(self) -> None:
        for summary in self._summaries.values():
            summary.clear()
