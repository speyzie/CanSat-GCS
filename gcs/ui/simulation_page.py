"""Simulation mode page (GS7, GS8, GS16, F4-F6).

Workflow: load the judges' pressure profile, send SIM ENABLE and SIM ACTIVATE,
then stream SIMP values at 1 Hz. Commands go to both devices so the
container and the PocketQube fly the same profile.
"""

from collections.abc import Callable
from pathlib import Path

import pyqtgraph as pg
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QGridLayout, QLabel, QPushButton, QWidget

from gcs import commands
from gcs.commands import Command
from gcs.simulation import SimulationPlayer, load_pressure_profile
from gcs.telemetry import Device
from gcs.ui import theme
from gcs.ui.pages import CARD_SPACING, info_card, page_grid
from gcs.ui.widgets import PLACEHOLDER, Card, PlotArea, make_plot_widget, make_section_title


class SimulationPage(QWidget):
    command_requested = pyqtSignal(Command)
    message = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._connected = False
        self._player = SimulationPlayer(self)
        self._player.pressure_due.connect(self._send_pressure)
        self._player.finished.connect(self._on_finished)

        self._profile_name = QLabel("No profile loaded")
        self._profile_name.setWordWrap(True)
        self._load_button = QPushButton("Load Profile…")
        self._load_button.clicked.connect(self._load_profile)

        self._enable_button = self._mode_button("SIM ENABLE", commands.simulation_enable)
        self._activate_button = self._mode_button("SIM ACTIVATE", commands.simulation_activate)
        self._disable_button = QPushButton("SIM DISABLE")
        self._disable_button.setProperty("role", "danger")
        self._disable_button.clicked.connect(self._disable)

        self._start_button = QPushButton("Start SIMP (1 Hz)")
        self._start_button.setProperty("role", "primary")
        self._start_button.clicked.connect(self._start)
        self._stop_button = QPushButton("Stop")
        self._stop_button.clicked.connect(self._stop)
        self._progress = QLabel()

        self._plot_widget = make_plot_widget()
        self._profile_curve = self._plot_widget.plot(pen=theme.series_pen(0))
        self._marker = pg.InfiniteLine(angle=90, pen=pg.mkPen(theme.SERIES_COLORS[1], width=3))
        self._marker.setVisible(False)
        self._plot_widget.addItem(self._marker)
        self._plot_area = PlotArea(self._plot_widget, "Load the pressure profile provided by the judges")

        self._build_layout()
        self._show_progress(0, 0, None)
        self._refresh_buttons()

    def _build_layout(self) -> None:
        playback_buttons = QWidget()
        buttons = QGridLayout(playback_buttons)
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(CARD_SPACING)
        buttons.addWidget(self._start_button, 0, 0)
        buttons.addWidget(self._stop_button, 0, 1)
        buttons.setColumnStretch(0, 2)
        buttons.setColumnStretch(1, 1)

        controls = info_card(
            "Procedure",
            make_section_title("1. Profile"), self._load_button, self._profile_name,
            make_section_title("2. Mode (both devices)"),
            self._enable_button, self._activate_button, self._disable_button,
            make_section_title("3. Pressure uplink"), playback_buttons, self._progress,
        )
        chart_card = Card("Pressure Profile (Pa vs s)")
        chart_card.body.addWidget(self._plot_area, stretch=1)

        grid = page_grid(self, rows=1, plot_columns=1)
        grid.addWidget(controls, 0, 0)
        grid.addWidget(chart_card, 0, 1)

    def set_connected(self, connected: bool) -> None:
        self._connected = connected
        if not connected:
            self._player.stop()
        self._refresh_buttons()

    # --- Actions --------------------------------------------------------------

    def _mode_button(self, text: str, make_command: Callable[[Device], Command]) -> QPushButton:
        button = QPushButton(text)
        button.clicked.connect(lambda: self._send_to_both(make_command))
        return button

    def _send_to_both(self, make_command: Callable[[Device], Command]) -> None:
        for device in Device:
            self.command_requested.emit(make_command(device))

    def _disable(self) -> None:
        self._player.stop()
        self._send_to_both(commands.simulation_disable)
        self._refresh_buttons()

    def _start(self) -> None:
        self._player.start()
        self._refresh_buttons()

    def _stop(self) -> None:
        self._player.stop()
        self._refresh_buttons()

    def _send_pressure(self, pascals: int, sample: int, total: int) -> None:
        self._send_to_both(lambda device: commands.simulated_pressure(device, pascals))
        self._show_progress(sample, total, pascals)

    def _on_finished(self) -> None:
        self.message.emit("Simulation profile completed")
        self._refresh_buttons()

    def _load_profile(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open Pressure Profile", "", "Profile files (*.csv *.txt);;All files (*)",
            options=theme.FILE_DIALOG_OPTIONS)
        if file_name:
            self.load_profile(Path(file_name))

    def load_profile(self, path: Path) -> None:
        try:
            pressures = load_pressure_profile(path)
        except (OSError, ValueError) as error:
            self.message.emit(f"Could not load profile: {error}")
            return
        self._player.load(pressures)
        self._profile_curve.setData(list(range(1, len(pressures) + 1)), pressures)
        self._plot_area.show_plot(True)
        self._profile_name.setText(f"<b>{path.name}</b><br>{len(pressures)} samples · {len(pressures)} s")
        self._show_progress(0, len(pressures), None)
        self.message.emit(f"Loaded simulation profile {path.name} ({len(pressures)} samples)")
        self._refresh_buttons()

    # --- Presentation ---------------------------------------------------------

    def _show_progress(self, sample: int, total: int, pascals: int | None) -> None:
        pressure = PLACEHOLDER if pascals is None else f"{pascals} Pa"
        self._progress.setText(f"Sample <b>{sample} / {total}</b><br>Last SIMP <b>{pressure}</b>")
        self._marker.setVisible(sample > 0)
        self._marker.setValue(sample)

    def _refresh_buttons(self) -> None:
        running = self._player.is_running
        for button in (self._enable_button, self._activate_button, self._disable_button):
            button.setEnabled(self._connected)
        self._start_button.setEnabled(self._connected and self._player.is_loaded and not running)
        self._stop_button.setEnabled(running)
        self._load_button.setEnabled(not running)
