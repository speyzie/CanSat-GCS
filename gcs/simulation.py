"""Simulation mode support (GS7, GS8, GS16).

Reads a judge-provided barometric pressure profile and emits one value per
second. Each non-empty, non-comment line must end with the pressure in
pascals, so both plain values (``101325``) and command-style lines
(``CMD,$,SIMP,101325``) are accepted.
"""

from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from gcs.config import SIMULATION_INTERVAL_MS


def load_pressure_profile(path: Path) -> list[int]:
    pressures = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        last_field = line.split(",")[-1].strip()
        try:
            pressures.append(round(float(last_field)))
        except ValueError:
            raise ValueError(f"line {line_number}: '{last_field}' is not a pressure value") from None
    if not pressures:
        raise ValueError("profile contains no pressure values")
    return pressures


class SimulationPlayer(QObject):
    pressure_due = pyqtSignal(int, int, int)  # pascals, sample number, total samples
    finished = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._pressures: list[int] = []
        self._index = 0
        self._timer = QTimer(self)
        self._timer.setInterval(SIMULATION_INTERVAL_MS)
        self._timer.timeout.connect(self._emit_next)

    @property
    def is_loaded(self) -> bool:
        return bool(self._pressures)

    @property
    def is_running(self) -> bool:
        return self._timer.isActive()

    def load(self, pressures: list[int]) -> None:
        self.stop()
        self._pressures = pressures
        self._index = 0

    def start(self) -> None:
        if not self.is_loaded or self.is_running:
            return
        if self._index >= len(self._pressures):
            self._index = 0
        self._emit_next()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def _emit_next(self) -> None:
        if self._index >= len(self._pressures):
            self.stop()
            self.finished.emit()
            return
        self._index += 1
        self.pressure_due.emit(self._pressures[self._index - 1], self._index, len(self._pressures))
