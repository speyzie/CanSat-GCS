"""Operator preferences remembered between sessions."""

from PyQt6.QtCore import QSettings

from gcs.config import DEFAULT_BAUD_RATE, DEFAULT_TEAM_ID


class AppSettings:
    def __init__(self) -> None:
        self._store = QSettings("CanSat", "GroundStation2027")

    @property
    def team_id(self) -> str:
        return str(self._store.value("team_id", DEFAULT_TEAM_ID))

    @team_id.setter
    def team_id(self, value: str) -> None:
        self._store.setValue("team_id", value)

    @property
    def port_name(self) -> str:
        return str(self._store.value("port_name", ""))

    @port_name.setter
    def port_name(self, value: str) -> None:
        self._store.setValue("port_name", value)

    @property
    def baud_rate(self) -> int:
        return int(self._store.value("baud_rate", DEFAULT_BAUD_RATE))

    @baud_rate.setter
    def baud_rate(self, value: int) -> None:
        self._store.setValue("baud_rate", value)

    @property
    def export_directory(self) -> str:
        return str(self._store.value("export_directory", ""))

    @export_directory.setter
    def export_directory(self, value: str) -> None:
        self._store.setValue("export_directory", value)
