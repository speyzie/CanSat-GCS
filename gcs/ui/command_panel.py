"""Command column (GS6, GS17, F3), always visible next to the pages.

Shows each recent command with its acknowledgement status, so the operator
knows whether the device actually executed it.
"""

from collections.abc import Callable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QGridLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gcs import commands
from gcs.command_tracker import CommandRecord, CommandStatus
from gcs.commands import Command
from gcs.telemetry import Device
from gcs.ui import theme
from gcs.ui.widgets import Card, make_section_title

COLUMN_WIDTH = 310
SPACING = 8

_STATUS_STYLES = {
    CommandStatus.PENDING: ("…", theme.WARNING),
    CommandStatus.ACKNOWLEDGED: ("✔", theme.OK),
    CommandStatus.NO_ECHO: ("✖", theme.ALARM),
}


class CommandPanel(QWidget):
    command_requested = pyqtSignal(Command)

    def __init__(self) -> None:
        super().__init__()
        self.setFixedWidth(COLUMN_WIDTH)
        self._buttons: list[QPushButton] = []
        self._history = QLabel()
        self._history.setTextFormat(Qt.TextFormat.RichText)
        self._history.setAlignment(Qt.AlignmentFlag.AlignTop)

        status_card = Card("Command Status")
        status_card.body.addWidget(self._history)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self._container_card())
        layout.addWidget(self._pocketqube_card())
        layout.addWidget(status_card, stretch=1)
        self.show_history([])

    def in_scroll_area(self) -> QScrollArea:
        """Keeps every button usable on short screens instead of squeezing them."""
        scroll = QScrollArea()
        scroll.setWidget(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFixedWidth(COLUMN_WIDTH + scroll.verticalScrollBar().sizeHint().width())
        return scroll

    def set_connected(self, connected: bool) -> None:
        for button in self._buttons:
            button.setEnabled(connected)

    def show_history(self, records: list[CommandRecord]) -> None:
        if not records:
            self._history.setText(f"<span style='color:{theme.INACTIVE}'>No commands sent</span>")
            return
        self._history.setText("<br>".join(_format_record(record) for record in records))

    # --- Cards ----------------------------------------------------------------

    def _container_card(self) -> Card:
        card = Card("Container")
        grid = _grid(card)
        grid.addWidget(self._button("Set UTC Time", lambda: commands.set_time_utc(Device.CONTAINER)), 0, 0)
        grid.addWidget(self._button("Calibrate", commands.calibrate_altitude), 0, 1)
        grid.addWidget(self._button("Arm", commands.arm_launch_detection), 1, 0)
        grid.addWidget(self._button("Close Release", commands.close_release_mechanism), 1, 1)
        release = self._button("Release PocketQube", commands.release_pocketqube, role="primary",
                               confirmation="Release the PocketQube from the container now?")
        grid.addWidget(release, 2, 0, 1, 2)
        return card

    def _pocketqube_card(self) -> Card:
        card = Card("PocketQube")
        grid = _grid(card)
        grid.addWidget(self._button("Camera On", lambda: commands.camera_recording(True)), 0, 0)
        grid.addWidget(self._button("Camera Off", lambda: commands.camera_recording(False)), 0, 1)
        grid.addWidget(self._button("Solar Panel 1", lambda: commands.deploy_solar_panel(1)), 1, 0)
        grid.addWidget(self._button("Solar Panel 2", lambda: commands.deploy_solar_panel(2)), 1, 1)
        grid.addWidget(self._button("Deploy Boom", commands.deploy_boom, role="primary"), 2, 0, 1, 2)

        self._rotation = QSpinBox()
        self._rotation.setRange(1, 360)
        self._rotation.setValue(90)
        self._rotation.setSuffix("°")
        card.body.addWidget(make_section_title("Rotate camera view"))
        rotation = QGridLayout()
        rotation.setSpacing(SPACING)
        rotation.addWidget(self._rotation, 0, 0)
        rotation.addWidget(self._button("CW", lambda: commands.rotate_camera(self._rotation.value())), 0, 1)
        rotation.addWidget(self._button("CCW", lambda: commands.rotate_camera(-self._rotation.value())), 0, 2)
        card.body.addLayout(rotation)
        return card

    # --- Helpers --------------------------------------------------------------

    def _button(self, text: str, make_command: Callable[[], Command], role: str = "",
                confirmation: str = "") -> QPushButton:
        button = QPushButton(text)
        if role:
            button.setProperty("role", role)
        button.clicked.connect(lambda: self._request(make_command, confirmation))
        self._buttons.append(button)
        return button

    def _request(self, make_command: Callable[[], Command], confirmation: str) -> None:
        if confirmation:
            answer = QMessageBox.question(self, "Confirm Command", confirmation)
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.command_requested.emit(make_command())


def _grid(card: Card) -> QGridLayout:
    grid = QGridLayout()
    grid.setSpacing(SPACING)
    grid.setColumnStretch(0, 1)
    grid.setColumnStretch(1, 1)
    card.body.addLayout(grid)
    return grid


def _format_record(record: CommandRecord) -> str:
    symbol, color = _STATUS_STYLES[record.status]
    command = record.command
    text = f"{command.target.value} {command.echo}"
    detail = f" {record.response_seconds:.1f} s" if record.response_seconds is not None else ""
    if record.status is CommandStatus.NO_ECHO:
        detail = " no echo"
    return (f"<b style='color:{color}'>{symbol}</b> <b>{text}</b>"
            f"<span style='color:{theme.SECONDARY_TEXT}'>{detail}</span>")
