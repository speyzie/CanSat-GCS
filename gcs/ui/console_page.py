"""Console page: flight data files, rejected packets, custom commands and
the event log."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QGridLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QWidget

from gcs import commands
from gcs.commands import Command
from gcs.ground_station import ReceptionCounters
from gcs.telemetry import Device
from gcs.ui.pages import CARD_SPACING, info_card, page_grid
from gcs.ui.widgets import Card, ComboBox, PropertyList, make_section_title

EVENT_LOG_LINES = 2000


class ConsolePage(QWidget):
    command_requested = pyqtSignal(Command)

    DIRECTORY = "Folder"
    CONTAINER_FILE = "Container"
    POCKETQUBE_FILE = "PocketQube"
    OTHER_TEAM = "Other team"
    INVALID = "Invalid"

    def __init__(self) -> None:
        super().__init__()
        self._files = PropertyList()
        self._files.add_section("Flight data (GS13)")
        for name in (self.DIRECTORY, self.CONTAINER_FILE, self.POCKETQUBE_FILE):
            self._files.add_row(name)
        self._files.add_section("Rejected packets")
        for name in (self.OTHER_TEAM, self.INVALID):
            self._files.add_row(name)

        self._target = ComboBox()
        for device in Device:
            self._target.addItem(device.title, device)
        self._text = QLineEdit()
        self._text.setPlaceholderText("NAME,ARG,…")
        self._text.returnPressed.connect(self._send_custom)
        self._send_button = QPushButton("Send")
        self._send_button.clicked.connect(self._send_custom)
        custom = QWidget()
        custom_grid = QGridLayout(custom)
        custom_grid.setContentsMargins(0, 0, 0, 0)
        custom_grid.setSpacing(CARD_SPACING)
        custom_grid.addWidget(self._text, 0, 0, 1, 2)
        custom_grid.addWidget(self._target, 1, 0)
        custom_grid.addWidget(self._send_button, 1, 1)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(EVENT_LOG_LINES)
        log_card = Card("Event Log")
        log_card.body.addWidget(self._log)

        grid = page_grid(self, rows=1, plot_columns=1)
        grid.addWidget(info_card("Data and Commands", self._files, make_section_title("Custom command"), custom,
                                 QLabel("Sent as CMD,<TEAM><C|P>,NAME,ARG")), 0, 0)
        grid.addWidget(log_card, 0, 1)

    def set_connected(self, connected: bool) -> None:
        self._send_button.setEnabled(connected)

    def show_files(self, directory: str, container_file: str, pocketqube_file: str) -> None:
        self._files.set_text(self.DIRECTORY, directory)
        self._files.set_text(self.CONTAINER_FILE, container_file)
        self._files.set_text(self.POCKETQUBE_FILE, pocketqube_file)

    def show_counters(self, counters: ReceptionCounters) -> None:
        self._files.set_text(self.OTHER_TEAM, str(counters.other_team))
        self._files.set_text(self.INVALID, str(counters.invalid))

    def append_log(self, line: str) -> None:
        self._log.appendPlainText(line)

    def _send_custom(self) -> None:
        text = self._text.text().strip(" ,")
        if not text or not self._send_button.isEnabled():
            return
        self.command_requested.emit(commands.custom(self._target.currentData(), text))
        self._text.clear()
