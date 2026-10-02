"""Header bar (team, serial link, UTC clock) and the flight data actions
shown next to the page tabs (CSV export for the judges, new flight)."""

from datetime import UTC, datetime

from PyQt6.QtCore import QRegularExpression, QTimer, pyqtSignal
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget

from gcs.config import BAUD_RATES
from gcs.links import available_serial_ports
from gcs.ui import theme
from gcs.ui.widgets import ComboBox, make_badge

CLOCK_REFRESH_MS = 1000


class HeaderBar(QFrame):
    serial_requested = pyqtSignal(str, int)  # port name, baud rate
    disconnect_requested = pyqtSignal()
    team_id_changed = pyqtSignal(str)

    def __init__(self, team_id: str, port_name: str, baud_rate: int) -> None:
        super().__init__()
        self.setObjectName("Bar")
        self._connected = False
        self._preferred_port = port_name

        title = QLabel("CanSat 2027 GCS")
        title.setObjectName("AppTitle")

        self._team_id = QLineEdit(team_id)
        self._team_id.setValidator(QRegularExpressionValidator(QRegularExpression(r"\d{4}")))
        self._team_id.setFixedWidth(76)
        self._team_id.setToolTip("Four digit team number; only packets with this ID are accepted (X4)")
        self._team_id.editingFinished.connect(self._emit_team_id)

        self._port = ComboBox()
        self._port.setMinimumWidth(260)
        self._port.setToolTip("Ground radio (ESP-NOW bridge or backup XBee)")
        self._refresh_button = QPushButton("Refresh")
        self._refresh_button.clicked.connect(self.refresh_ports)

        self._baud = ComboBox()
        for rate in BAUD_RATES:
            self._baud.addItem(str(rate), rate)
        self._baud.setCurrentText(str(baud_rate))

        self._connect_button = QPushButton()
        self._connect_button.setProperty("role", "primary")
        self._connect_button.setMinimumWidth(130)
        self._connect_button.clicked.connect(self._on_connect_clicked)

        self._link = make_badge()
        self._clock = QLabel()
        self._clock.setObjectName("Clock")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 6)
        layout.setSpacing(8)
        layout.addWidget(title)
        layout.addSpacing(18)
        for widget in (QLabel("Team"), self._team_id, QLabel("Radio"), self._port, self._refresh_button,
                       self._baud, self._connect_button, self._link):
            layout.addWidget(widget)
        layout.addStretch()
        layout.addWidget(self._clock)

        clock_timer = QTimer(self)
        clock_timer.timeout.connect(self._update_clock)
        clock_timer.start(CLOCK_REFRESH_MS)
        self._update_clock()
        self.refresh_ports()
        self.set_connected(False)

    def refresh_ports(self) -> None:
        selected = self._port.currentData() or self._preferred_port
        self._port.clear()
        for choice in available_serial_ports():
            self._port.addItem(choice.label, choice.name)
        index = self._port.findData(selected)
        self._port.setCurrentIndex(max(index, 0))
        if self._port.count() == 0:
            self._port.addItem("No serial ports found", "")

    def set_connected(self, connected: bool, description: str = "") -> None:
        self._connected = connected
        self._connect_button.setText("Disconnect" if connected else "Connect")
        for widget in (self._team_id, self._port, self._refresh_button, self._baud):
            widget.setEnabled(not connected)
        self._link.setText(f"LINK {description}" if connected else "OFFLINE")
        theme.set_level(self._link, "ok" if connected else "idle")

    def _on_connect_clicked(self) -> None:
        if self._connected:
            self.disconnect_requested.emit()
        elif self._port.currentData():
            self.serial_requested.emit(self._port.currentData(), self._baud.currentData())

    def _emit_team_id(self) -> None:
        if self._team_id.hasAcceptableInput():
            self.team_id_changed.emit(self._team_id.text())

    def _update_clock(self) -> None:
        self._clock.setText(datetime.now(UTC).strftime("%H:%M:%S UTC"))


class FlightDataActions(QWidget):
    """Shown at the right of the page tabs so the judges' CSV export is one click away (GS13)."""

    export_requested = pyqtSignal()
    new_flight_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._recording = make_badge()
        export_button = QPushButton("Export CSV to USB…")
        export_button.setProperty("role", "primary")
        export_button.setProperty("size", "compact")
        export_button.clicked.connect(self.export_requested)
        new_flight_button = QPushButton("New Flight…")
        new_flight_button.setProperty("size", "compact")
        new_flight_button.setToolTip("Archive the current CSV files and reset plots and counters")
        new_flight_button.clicked.connect(self.new_flight_requested)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self._recording)
        layout.addWidget(export_button)
        layout.addWidget(new_flight_button)
        self.set_recording(False)

    def set_recording(self, recording: bool) -> None:
        self._recording.setText("● CSV LOGGING" if recording else "CSV IDLE")
        theme.set_level(self._recording, "alarm" if recording else "idle")
