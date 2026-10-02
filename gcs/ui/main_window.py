"""Main window: lays out the header, status strip, pages and command column,
and wires them to the ground station.

    ┌ header: team · radio · connect · link · UTC clock ─────────────────┐
    │ status strip: container summary   │ PocketQube summary             │
    ├ tabs: Container | PocketQube | Simulation | Console   [CSV actions]┤
    │ page                                              │ command column │
    └───────────────────────────────────────────────────┴────────────────┘

Sized for a single laptop screen so the station fits on one table (GS18).
"""

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from gcs.ground_station import GroundStation, ReceptionCounters
from gcs.settings import AppSettings
from gcs.telemetry import Device, PocketQubePacket
from gcs.ui import theme
from gcs.ui.bars import FlightDataActions, HeaderBar
from gcs.ui.command_panel import CommandPanel
from gcs.ui.console_page import ConsolePage
from gcs.ui.pages import CARD_SPACING, ContainerPage, PocketQubePage
from gcs.ui.simulation_page import SimulationPage
from gcs.ui.status_strip import StatusStrip

REMOVABLE_DRIVES = Path("/Volumes")  # where macOS mounts USB sticks
WINDOW_MARGIN = 10
MINIMUM_SIZE = (1280, 760)


class MainWindow(QMainWindow):
    def __init__(self, station: GroundStation, settings: AppSettings) -> None:
        super().__init__()
        self._station = station
        self._settings = settings
        self._follow_pocketqube = True
        self.setMinimumSize(*MINIMUM_SIZE)

        self._header = HeaderBar(station.team_id, settings.port_name, settings.baud_rate)
        self._status = StatusStrip()
        self._tabs = QTabBar()
        self._pages = QStackedWidget()
        self._container_page = ContainerPage()
        self._pocketqube_page = PocketQubePage()
        self._simulation_page = SimulationPage()
        self._console_page = ConsolePage()
        self._data_actions = FlightDataActions()
        self._commands = CommandPanel()

        self._build_layout()
        self._connect_signals()
        self._update_title()
        self._set_connected(False)
        self._show_counters(ReceptionCounters())
        self._show_files()

    # --- Layout ---------------------------------------------------------------

    def _build_layout(self) -> None:
        pages = {"Container": self._container_page, "PocketQube": self._pocketqube_page,
                 "Simulation": self._simulation_page, "Console": self._console_page}
        for title, page in pages.items():
            self._tabs.addTab(title)
            self._pages.addWidget(page)
        self._tabs.setDrawBase(False)
        self._tabs.currentChanged.connect(self._pages.setCurrentIndex)

        # Tabs and flight data actions share one row, each at its natural height.
        navigation = QHBoxLayout()
        navigation.addWidget(self._tabs, alignment=Qt.AlignmentFlag.AlignBottom)
        navigation.addStretch()
        navigation.addWidget(self._data_actions, alignment=Qt.AlignmentFlag.AlignVCenter)

        content = QVBoxLayout()
        content.setSpacing(0)
        content.addLayout(navigation)
        content.addWidget(self._pages, stretch=1)

        body = QHBoxLayout()
        body.setSpacing(CARD_SPACING)
        body.addLayout(content, stretch=1)
        body.addWidget(self._commands.in_scroll_area())

        central = QWidget()
        central.setObjectName("Page")
        layout = QVBoxLayout(central)
        layout.setContentsMargins(WINDOW_MARGIN, WINDOW_MARGIN, WINDOW_MARGIN, WINDOW_MARGIN)
        layout.setSpacing(CARD_SPACING)
        layout.addWidget(self._header)
        layout.addWidget(self._status)
        layout.addLayout(body, stretch=1)
        self.setCentralWidget(central)

    def _connect_signals(self) -> None:
        self._header.serial_requested.connect(self._connect_serial)
        self._header.disconnect_requested.connect(self._station.disconnect_link)
        self._header.team_id_changed.connect(self._change_team_id)

        for source in (self._commands, self._simulation_page, self._console_page):
            source.command_requested.connect(self._station.send)
        self._simulation_page.message.connect(self._log)
        self._data_actions.export_requested.connect(self._export_csv)
        self._data_actions.new_flight_requested.connect(self._confirm_new_flight)

        station = self._station
        station.container_packet_received.connect(self._container_page.show_packet)
        station.container_packet_received.connect(self._status.show_container)
        station.pocketqube_packet_received.connect(self._pocketqube_page.show_packet)
        station.pocketqube_packet_received.connect(self._status.show_pocketqube)
        station.pocketqube_packet_received.connect(self._follow_pocketqube_release)
        station.counters_changed.connect(self._show_counters)
        station.commands_changed.connect(self._commands.show_history)
        station.connection_changed.connect(self._set_connected)
        station.session_reset.connect(self._clear_displays)
        station.event_logged.connect(self._log)

    # --- Slots ----------------------------------------------------------------

    def _connect_serial(self, port_name: str, baud_rate: int) -> None:
        if self._station.connect_serial(port_name, baud_rate):
            self._settings.port_name = port_name
            self._settings.baud_rate = baud_rate

    def _change_team_id(self, team_id: str) -> None:
        self._station.set_team_id(team_id)
        self._settings.team_id = team_id
        self._update_title()
        self._show_files()

    def _set_connected(self, connected: bool) -> None:
        self._header.set_connected(connected, self._station.link_description)
        self._commands.set_connected(connected)
        self._simulation_page.set_connected(connected)
        self._console_page.set_connected(connected)
        self._data_actions.set_recording(connected)

    def _follow_pocketqube_release(self, _packet: PocketQubePacket) -> None:
        """Opens the PocketQube page once, when it starts transmitting after release."""
        if self._follow_pocketqube and self._pages.currentWidget() is self._container_page:
            self._tabs.setCurrentIndex(self._pages.indexOf(self._pocketqube_page))
        self._follow_pocketqube = False

    def _show_counters(self, counters: ReceptionCounters) -> None:
        self._status.show_counters(counters)
        self._console_page.show_counters(counters)

    def _show_files(self) -> None:
        logger = self._station.logger
        self._console_page.show_files(
            logger.directory.name,
            logger.file_path(Device.CONTAINER).name,
            logger.file_path(Device.POCKETQUBE).name,
        )

    def _clear_displays(self) -> None:
        self._container_page.clear()
        self._pocketqube_page.clear()
        self._status.clear()
        self._follow_pocketqube = True

    def _export_csv(self) -> None:
        directory = self._choose_usb_drive()
        if not directory:
            return
        self._settings.export_directory = directory
        if self._station.export_csv(Path(directory)):
            QMessageBox.information(self, "Export CSV", f"Flight files copied to\n{directory}")
        else:
            QMessageBox.warning(self, "Export CSV", "No flight files were exported. See the Console page.")

    def _choose_usb_drive(self) -> str:
        start = self._settings.export_directory or str(REMOVABLE_DRIVES)
        dialog = QFileDialog(self, "Select USB Drive", start)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOptions(QFileDialog.Option.ShowDirsOnly | theme.FILE_DIALOG_OPTIONS)
        shortcuts = [path for path in (REMOVABLE_DRIVES, Path.home()) if path.exists()]
        dialog.setSidebarUrls([QUrl.fromLocalFile(str(path)) for path in shortcuts])
        dialog.resize(900, 560)
        if dialog.exec() != QFileDialog.DialogCode.Accepted:
            return ""
        return dialog.selectedFiles()[0]

    def _confirm_new_flight(self) -> None:
        answer = QMessageBox.question(
            self, "New Flight",
            "Archive the current CSV files and reset all plots and packet counters?")
        if answer == QMessageBox.StandardButton.Yes:
            self._station.reset_session()

    def _log(self, message: str) -> None:
        self._console_page.append_log(f"{datetime.now():%H:%M:%S}  {message}")

    def _update_title(self) -> None:
        self.setWindowTitle(f"CanSat 2027 Ground Station — Team {self._station.team_id}")

    def closeEvent(self, event: QCloseEvent) -> None:
        self._station.shutdown()
        super().closeEvent(event)
