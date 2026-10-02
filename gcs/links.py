"""USB serial link to the ground radio bridge (ESP-NOW, or the optional XBee backup)."""

from dataclasses import dataclass

from PyQt6.QtCore import QIODevice, QObject, pyqtSignal
from PyQt6.QtSerialPort import QSerialPort, QSerialPortInfo

_USB_HINTS = ("usb", "uart", "cp210", "ch340", "ch910", "ftdi", "silicon labs", "espressif")


@dataclass(frozen=True)
class SerialPortChoice:
    name: str
    label: str
    is_usb: bool


def available_serial_ports() -> list[SerialPortChoice]:
    """Lists serial ports with a readable label, USB adapters first."""
    choices = []
    for port in QSerialPortInfo.availablePorts():
        details = " ".join((port.portName(), port.description(), port.manufacturer())).lower()
        is_usb = any(hint in details for hint in _USB_HINTS)
        description = port.description() or port.manufacturer()
        label = f"{port.portName()} — {description}" if description else port.portName()
        choices.append(SerialPortChoice(port.portName(), label, is_usb))
    return sorted(choices, key=lambda choice: (not choice.is_usb, choice.name))


class SerialLink(QObject):
    line_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, port_name: str, baud_rate: int, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._buffer = bytearray()
        self._port = QSerialPort(self)
        self._port.setPortName(port_name)
        self._port.setBaudRate(baud_rate)
        self._port.readyRead.connect(self._read_available)
        self._port.errorOccurred.connect(self._report_error)

    @property
    def description(self) -> str:
        return f"{self._port.portName()} @ {self._port.baudRate()}"

    def open(self) -> bool:
        return self._port.open(QIODevice.OpenModeFlag.ReadWrite)

    def close(self) -> None:
        if self._port.isOpen():
            self._port.close()

    def write_line(self, line: str) -> None:
        self._port.write((line + "\r\n").encode("ascii"))

    def _read_available(self) -> None:
        # Packets end with a carriage return; a line feed is accepted as well.
        self._buffer.extend(bytes(self._port.readAll()).replace(b"\n", b"\r"))
        *complete_lines, remainder = self._buffer.split(b"\r")
        self._buffer = bytearray(remainder)
        for raw_line in complete_lines:
            line = raw_line.decode("ascii", errors="replace").strip()
            if line:
                self.line_received.emit(line)

    def _report_error(self, error: QSerialPort.SerialPortError) -> None:
        if error != QSerialPort.SerialPortError.NoError:
            self.error_occurred.emit(self._port.errorString())
