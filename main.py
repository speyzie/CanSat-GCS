"""Entry point of the CanSat 2027 ground control station."""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from gcs.config import TELEMETRY_DIRECTORY
from gcs.ground_station import GroundStation
from gcs.settings import AppSettings
from gcs.ui.main_window import MainWindow
from gcs.ui.theme import apply_theme


def main() -> int:
    app = QApplication(sys.argv)
    apply_theme(app)
    settings = AppSettings()
    data_directory = Path(__file__).resolve().parent / TELEMETRY_DIRECTORY
    station = GroundStation(data_directory, settings.team_id)
    window = MainWindow(station, settings)
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
