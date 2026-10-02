"""CSV telemetry files required by GS13 and the Telemetry Data Files section.

One file per device, named ``Flight_<TEAM_ID>C.csv`` and ``Flight_<TEAM_ID>P.csv``,
with a header row and Excel-compatible formatting.
"""

import csv
import shutil
from datetime import datetime
from pathlib import Path
from typing import TextIO

from gcs.telemetry import ContainerPacket, Device, PocketQubePacket, TelemetryPacket, device_of

_HEADERS: dict[Device, tuple[str, ...]] = {
    Device.CONTAINER: ContainerPacket.FIELD_NAMES,
    Device.POCKETQUBE: PocketQubePacket.FIELD_NAMES + PocketQubePacket.EXTRA_FIELD_NAMES,
}


def flight_file_name(team_id: str, device: Device) -> str:
    return f"Flight_{team_id}{device.value}.csv"


class TelemetryCsvLogger:
    def __init__(self, directory: Path, team_id: str) -> None:
        self._directory = directory
        self._team_id = team_id
        self._files: dict[Device, TextIO] = {}

    @property
    def directory(self) -> Path:
        return self._directory

    def file_path(self, device: Device) -> Path:
        return self._directory / flight_file_name(self._team_id, device)

    def write(self, packet: TelemetryPacket) -> None:
        file = self._open(device_of(packet))
        csv.writer(file).writerow(packet.raw_fields)
        file.flush()

    def close(self) -> None:
        for file in self._files.values():
            file.close()
        self._files.clear()

    def archive(self) -> None:
        """Moves existing files aside so a new flight starts with empty files."""
        self.close()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for device in Device:
            path = self.file_path(device)
            if path.exists():
                path.rename(path.with_name(f"{path.stem}_{stamp}{path.suffix}"))

    def export_to(self, destination: Path) -> list[Path]:
        """Copies the flight files to a destination such as the judges' USB stick."""
        for file in self._files.values():
            file.flush()
        exported = []
        for device in Device:
            source = self.file_path(device)
            if source.exists():
                exported.append(Path(shutil.copy2(source, destination / source.name)))
        return exported

    def _open(self, device: Device) -> TextIO:
        if device not in self._files:
            self._directory.mkdir(parents=True, exist_ok=True)
            path = self.file_path(device)
            is_new = not path.exists() or path.stat().st_size == 0
            file = path.open("a", newline="", encoding="ascii", errors="replace")
            if is_new:
                csv.writer(file).writerow(_HEADERS[device])
            self._files[device] = file
        return self._files[device]
