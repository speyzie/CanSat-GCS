"""Telemetry pages. Each page has an information card on the left
(non-plotted telemetry, GS3/GS5) and a uniform grid of plot cards
(GS2/GS4). Packet number, mode and command echo are shown for both devices
in the status strip, so they are not repeated here."""

from PyQt6.QtWidgets import QGridLayout, QWidget

from gcs.attitude import estimate_attitude
from gcs.telemetry import ContainerPacket, FlightState, PocketQubePacket
from gcs.ui.widgets import (
    PLACEHOLDER,
    Card,
    GpsTrackCard,
    PlotCard,
    PropertyList,
    StateStepper,
    VectorTable,
    make_section_title,
)

INFO_COLUMN_WIDTH = 330
CARD_SPACING = 10
PAGE_TOP_MARGIN = 12  # gap between the tab bar and the cards


def page_grid(page: QWidget, rows: int, plot_columns: int) -> QGridLayout:
    """Grid with a fixed-width information column and equal plot cells."""
    page.setObjectName("Page")
    grid = QGridLayout(page)
    grid.setContentsMargins(0, PAGE_TOP_MARGIN, 0, 0)
    grid.setSpacing(CARD_SPACING)
    grid.setColumnMinimumWidth(0, INFO_COLUMN_WIDTH)
    for column in range(1, plot_columns + 1):
        grid.setColumnStretch(column, 1)
    for row in range(rows):
        grid.setRowStretch(row, 1)
    return grid


def info_card(title: str, *contents: QWidget) -> Card:
    card = Card(title)
    card.setFixedWidth(INFO_COLUMN_WIDTH)
    for content in contents:
        card.body.addWidget(content)
    card.body.addStretch()
    return card


class ContainerPage(QWidget):
    ID = "ID"
    MISSION_TIME = "Mission time"
    COMMAND_COUNT = "Commands received"
    PRESSURE = "Pressure"
    BATTERY_VOLTAGE = "Battery voltage"
    MECH_STATE = "MECH_STATE"
    RELEASE = "Release mechanism"
    POCKETQUBE = "PocketQube"

    def __init__(self) -> None:
        super().__init__()
        self._stepper = StateStepper([state.value for state in FlightState])
        self._properties = PropertyList()
        self._properties.add_section("Mission")
        for name in (self.ID, self.MISSION_TIME, self.COMMAND_COUNT):
            self._properties.add_row(name)
        self._properties.add_section("Sensors")
        for name in (self.PRESSURE, self.BATTERY_VOLTAGE):
            self._properties.add_row(name)
        self._properties.add_section("Mechanisms")
        self._properties.add_row(self.MECH_STATE)
        self._properties.add_badge_row(self.RELEASE)
        self._properties.add_badge_row(self.POCKETQUBE)

        self._altitude = PlotCard("Altitude", "m")
        self._temperature = PlotCard("Temperature", "°C")
        self._current = PlotCard("Battery Current", "mA", decimals=0)

        grid = page_grid(self, rows=2, plot_columns=2)
        grid.addWidget(info_card("Flight Status", make_section_title("Flight state"), self._stepper, self._properties), 0, 0, 2, 1)
        grid.addWidget(self._altitude, 0, 1, 1, 2)
        grid.addWidget(self._temperature, 1, 1)
        grid.addWidget(self._current, 1, 2)
        self.clear()

    def show_packet(self, packet: ContainerPacket) -> None:
        self._altitude.append(packet.mission_time, packet.altitude)
        self._temperature.append(packet.mission_time, packet.temperature)
        self._current.append(packet.mission_time, packet.battery_current)
        self._stepper.set_current(packet.state)

        properties = self._properties
        properties.set_text(self.ID, f"{packet.team_id}C")
        properties.set_text(self.MISSION_TIME, f"{packet.mission_time:.3f} s")
        properties.set_text(self.COMMAND_COUNT, str(packet.command_count))
        properties.set_text(self.PRESSURE, f"{packet.pressure:.0f} Pa")
        properties.set_text(self.BATTERY_VOLTAGE, f"{packet.battery_voltage:.2f} V")
        properties.set_text(self.MECH_STATE, f"0x{packet.mech_state:02X}")
        properties.set_badge(self.RELEASE, packet.release_activated, "ACTIVATED", "IDLE")
        properties.set_badge(self.POCKETQUBE, packet.pocketqube_released, "RELEASED", "STOWED")

    def clear(self) -> None:
        for card in (self._altitude, self._temperature, self._current):
            card.clear_data()
        self._properties.clear()
        self._stepper.set_current(None)


class PocketQubePage(QWidget):
    ID = "ID"
    MISSION_TIME = "Mission time"
    GNSS_TIME = "GNSS time"
    COMMAND_COUNT = "Commands received"
    PRESSURE = "Pressure"
    GNSS_ALTITUDE = "GNSS altitude"
    GNSS_SATS = "GNSS satellites"
    STABILIZATION = "Stabilization"
    SCIENCE = "Science exp."

    ROTATION_RATE = "Rate (°/s)"
    ACCELERATION = "Accel (m/s²)"
    MAGNETIC_FIELD = "Mag (mG)"

    SOLAR_PANEL_1 = "Solar panel 1"
    SOLAR_PANEL_2 = "Solar panel 2"
    BOOM = "Magnetometer boom"
    CAMERA = "Camera"
    MECH_STATE = "MECH_STATE"

    def __init__(self) -> None:
        super().__init__()
        self._properties = PropertyList()
        sections = {
            "Mission": (self.ID, self.MISSION_TIME, self.GNSS_TIME, self.COMMAND_COUNT),
            "Sensors": (self.PRESSURE, self.GNSS_ALTITUDE, self.GNSS_SATS),
            "Payload": (self.STABILIZATION, self.SCIENCE),
        }
        for title, names in sections.items():
            self._properties.add_section(title)
            for name in names:
                self._properties.add_row(name)
        self._imu = VectorTable([self.ROTATION_RATE, self.ACCELERATION, self.MAGNETIC_FIELD])

        self._mechanisms = PropertyList()
        for name in (self.SOLAR_PANEL_1, self.SOLAR_PANEL_2, self.BOOM, self.CAMERA):
            self._mechanisms.add_badge_row(name)
        self._mechanisms.add_row(self.MECH_STATE)
        mechanisms_card = Card("Mechanisms")
        mechanisms_card.body.addWidget(self._mechanisms)
        mechanisms_card.body.addStretch()

        self._altitude = PlotCard("Altitude", "m")
        self._temperature = PlotCard("Temperature", "°C")
        self._voltage = PlotCard("Battery Voltage", "V")
        self._current = PlotCard("Battery Current", "mA", decimals=0)
        self._solar = PlotCard("Solar Panels", "V", ("Panel 1", "Panel 2"), decimals=2)
        self._orientation = PlotCard("Orientation", "°", ("Roll", "Pitch", "Yaw"), decimals=0)
        self._gps = GpsTrackCard()
        self._plot_cards = (self._altitude, self._temperature, self._voltage, self._current,
                            self._solar, self._orientation, self._gps)

        grid = page_grid(self, rows=3, plot_columns=3)
        grid.addWidget(info_card("Telemetry", self._properties, make_section_title("Inertial sensors"), self._imu), 0, 0, 3, 1)
        grid.addWidget(self._altitude, 0, 1)
        grid.addWidget(self._temperature, 0, 2)
        grid.addWidget(self._gps, 0, 3, 2, 1)
        grid.addWidget(self._voltage, 1, 1)
        grid.addWidget(self._current, 1, 2)
        grid.addWidget(self._solar, 2, 1)
        grid.addWidget(self._orientation, 2, 2)
        grid.addWidget(mechanisms_card, 2, 3)
        self.clear()

    def show_packet(self, packet: PocketQubePacket) -> None:
        self._update_plots(packet)
        self._update_properties(packet)
        self._update_mechanisms(packet)

    def _update_plots(self, packet: PocketQubePacket) -> None:
        time = packet.mission_time
        attitude = estimate_attitude(packet.acceleration, packet.magnetic_field)
        self._altitude.append(time, packet.altitude)
        self._temperature.append(time, packet.temperature)
        self._voltage.append(time, packet.voltage)
        self._current.append(time, packet.current)
        self._solar.append(time, packet.solar_1, packet.solar_2)
        self._orientation.append(time, attitude.roll, attitude.pitch, attitude.yaw)
        self._gps.append(packet.gnss_latitude, packet.gnss_longitude)

    def _update_properties(self, packet: PocketQubePacket) -> None:
        stabilization, science = _split_extra_fields(packet.extra_fields)
        properties = self._properties
        properties.set_text(self.ID, f"{packet.team_id}P")
        properties.set_text(self.MISSION_TIME, f"{packet.mission_time:.2f} s")
        properties.set_text(self.GNSS_TIME, packet.gnss_time)
        properties.set_text(self.COMMAND_COUNT, str(packet.command_count))
        properties.set_text(self.PRESSURE, f"{packet.pressure:.0f} Pa")
        properties.set_text(self.GNSS_ALTITUDE, f"{packet.gnss_altitude:.1f} m")
        properties.set_text(self.GNSS_SATS, str(packet.gnss_sats))
        properties.set_text(self.STABILIZATION, stabilization)
        properties.set_text(self.SCIENCE, science)
        self._imu.set_row(self.ROTATION_RATE, packet.rotation_rate, 1)
        self._imu.set_row(self.ACCELERATION, packet.acceleration, 2)
        self._imu.set_row(self.MAGNETIC_FIELD, packet.magnetic_field, 0)

    def _update_mechanisms(self, packet: PocketQubePacket) -> None:
        mechanisms = self._mechanisms
        mechanisms.set_badge(self.SOLAR_PANEL_1, packet.solar_panel_1_deployed, "DEPLOYED", "STOWED")
        mechanisms.set_badge(self.SOLAR_PANEL_2, packet.solar_panel_2_deployed, "DEPLOYED", "STOWED")
        mechanisms.set_badge(self.BOOM, packet.boom_deployed, "DEPLOYED", "STOWED")
        mechanisms.set_badge(self.CAMERA, packet.camera_recording, "RECORDING", "OFF")
        mechanisms.set_text(self.MECH_STATE, f"0x{packet.mech_state:02X}")

    def clear(self) -> None:
        for card in self._plot_cards:
            card.clear_data()
        self._properties.clear()
        self._imu.clear()
        self._mechanisms.clear()


def _split_extra_fields(extra_fields: tuple[str, ...]) -> tuple[str, str]:
    """The first field after CMD_ECHO is image stabilization data, the rest is science data."""
    stabilization = extra_fields[0] if extra_fields else PLACEHOLDER
    science = " ".join(extra_fields[1:]) or PLACEHOLDER
    return stabilization, science
