"""Reusable building blocks. Every panel on screen is a ``Card`` so the
layout stays uniform: same border, padding, header and spacing."""

import math
from collections import deque

import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListView,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from gcs.config import PLOT_HISTORY_LIMIT
from gcs.ui import theme

PLACEHOLDER = "—"
EMPTY_PLOT_TEXT = "Waiting for telemetry"
Y_AXIS_WIDTH = 72  # fixed so plot areas line up across cards
EARTH_RADIUS_M = 6_371_000.0
POPUP_EXTRA_WIDTH = 48  # item padding, border and scroll bar


def _label(text: str = "", object_name: str = "") -> QLabel:
    label = QLabel(text)
    if object_name:
        label.setObjectName(object_name)
    return label


def make_section_title(text: str) -> QLabel:
    return _label(text.upper(), "SectionTitle")


def make_badge(text: str = "", level: str = "idle") -> QLabel:
    badge = _label(text, "Badge")
    badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    theme.set_level(badge, level)
    return badge


class ComboBox(QComboBox):
    """Drop-down whose popup uses the light theme and shows the selected option in bold."""

    def __init__(self) -> None:
        super().__init__()
        self.setView(QListView())  # a plain list view honours the item style sheet on every platform
        self.currentIndexChanged.connect(self._bold_current)
        self.model().rowsInserted.connect(self._bold_current)

    def showPopup(self) -> None:
        # Widen the list to its longest (bold) option so no option is elided.
        content_width = self.view().sizeHintForColumn(0) + POPUP_EXTRA_WIDTH
        self.view().setMinimumWidth(max(content_width, self.width()))
        super().showPopup()

    def _bold_current(self) -> None:
        for index in range(self.count()):
            font = self.font()
            font.setBold(index == self.currentIndex())
            self.setItemData(index, font, Qt.ItemDataRole.FontRole)


class Card(QFrame):
    """White panel with a bold title, an optional large live value with its
    unit on the right, and a body layout for content."""

    def __init__(self, title: str, unit: str = "") -> None:
        super().__init__()
        self.setObjectName("Card")
        self._value = _label(PLACEHOLDER, "BigValue")
        self._value.setVisible(bool(unit))
        unit_label = _label(unit, "Unit")
        unit_label.setVisible(bool(unit))

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)
        header.addWidget(_label(title, "CardTitle"), alignment=Qt.AlignmentFlag.AlignVCenter)
        header.addStretch()
        header.addWidget(self._value, alignment=Qt.AlignmentFlag.AlignBaseline)
        header.addWidget(unit_label, alignment=Qt.AlignmentFlag.AlignBaseline)

        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(6)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 10)
        layout.setSpacing(4)
        layout.addLayout(header)
        layout.addLayout(self.body, stretch=1)

    def set_value(self, text: str) -> None:
        self._value.setText(text)

    def add_caption(self) -> QLabel:
        """A line under the title for text too wide for the header."""
        caption = _label(object_name="Caption")
        caption.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.body.addWidget(caption)
        return caption


# --- Plots --------------------------------------------------------------------

def make_plot_widget() -> pg.PlotWidget:
    widget = pg.PlotWidget()
    plot = widget.getPlotItem()
    plot.hideButtons()
    plot.setMenuEnabled(False)
    plot.setMouseEnabled(x=False, y=False)
    plot.showGrid(x=True, y=True, alpha=theme.GRID_ALPHA)
    for side in ("bottom", "left"):
        axis = plot.getAxis(side)
        axis.setPen(pg.mkPen(theme.TEXT, width=theme.AXIS_LINE_WIDTH))
        axis.setTextPen(pg.mkPen(theme.TEXT))
        axis.setTickFont(theme.bold_font())
        axis.setStyle(maxTickLevel=0)  # major grid lines only: less clutter
        axis.enableAutoSIPrefix(False)
    plot.getAxis("left").setWidth(Y_AXIS_WIDTH)
    widget.setMinimumSize(180, 110)
    return widget


class PlotArea(QWidget):
    """Plot with an empty-state message shown until the first sample arrives."""

    def __init__(self, plot_widget: pg.PlotWidget, empty_text: str = EMPTY_PLOT_TEXT) -> None:
        super().__init__()
        empty = _label(empty_text, "EmptyState")
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._stack = QStackedLayout(self)
        self._stack.addWidget(empty)
        self._stack.addWidget(plot_widget)

    def show_plot(self, visible: bool) -> None:
        self._stack.setCurrentIndex(1 if visible else 0)


class SeriesLegend(QWidget):
    """Legend with the latest value of each series: coloured name over the value."""

    def __init__(self, names: tuple[str, ...]) -> None:
        super().__init__()
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(0)
        self._values: list[QLabel] = []
        for column, name in enumerate(names):
            grid.addWidget(_label(f"<span style='color:{theme.series_color(column)}'>■</span> {name}",
                                  "Caption"), 0, column)
            value = _label(PLACEHOLDER, "PropertyValue")
            grid.addWidget(value, 1, column)
            self._values.append(value)
            grid.setColumnStretch(column, 1)

    def show_values(self, numbers: list[str]) -> None:
        for label, number in zip(self._values, numbers):
            label.setText(number)


class PlotCard(Card):
    """Live time-series plot against mission time.

    A single-series card shows the latest value large in the header; a
    multi-series card shows a legend with each series' latest value.
    """

    def __init__(self, title: str, unit: str, series: tuple[str, ...] = ("",), decimals: int = 1) -> None:
        is_single = len(series) == 1
        super().__init__(title if is_single else f"{title} ({unit})", unit if is_single else "")
        self._series_names = series
        self._decimals = decimals
        plot_widget = make_plot_widget()
        self._times: deque[float] = deque(maxlen=PLOT_HISTORY_LIMIT)
        self._values = [deque(maxlen=PLOT_HISTORY_LIMIT) for _ in series]
        self._curves = [plot_widget.plot(pen=theme.series_pen(index)) for index in range(len(series))]
        self._legend = None if is_single else SeriesLegend(series)
        if self._legend is not None:
            self.body.addWidget(self._legend)
        self._area = PlotArea(plot_widget)
        self.body.addWidget(self._area, stretch=1)
        self.clear_data()

    def append(self, time: float, *values: float) -> None:
        self._times.append(time)
        times = list(self._times)
        for history, curve, value in zip(self._values, self._curves, values, strict=True):
            history.append(value)
            curve.setData(times, list(history))
        self._area.show_plot(True)
        self._show_latest([f"{value:.{self._decimals}f}" for value in values])

    def clear_data(self) -> None:
        self._times.clear()
        for history, curve in zip(self._values, self._curves):
            history.clear()
            curve.setData([], [])
        self._area.show_plot(False)
        self._show_latest([PLACEHOLDER] * len(self._series_names))

    def _show_latest(self, numbers: list[str]) -> None:
        if self._legend is None:
            self.set_value(numbers[0])
        else:
            self._legend.show_values(numbers)


class GpsTrackCard(Card):
    """GNSS ground track with the latest fix highlighted.

    Plotted as east/north metres from the first fix so the axes stay
    readable; the absolute latitude and longitude are shown above the plot.
    """

    def __init__(self) -> None:
        super().__init__("GPS Track (m from first fix)")
        plot_widget = make_plot_widget()
        plot_widget.getPlotItem().setAspectLocked(True)
        self._origin: tuple[float, float] | None = None
        self._norths: deque[float] = deque(maxlen=PLOT_HISTORY_LIMIT)
        self._easts: deque[float] = deque(maxlen=PLOT_HISTORY_LIMIT)
        self._track = plot_widget.plot(pen=theme.series_pen(0))
        self._position = plot_widget.plot(
            pen=None, symbol="o", symbolSize=16,
            symbolBrush=theme.SERIES_COLORS[1], symbolPen=pg.mkPen(theme.TEXT, width=2))
        self._caption = self.add_caption()
        self._area = PlotArea(plot_widget)
        self.body.addWidget(self._area, stretch=1)
        self.clear_data()

    def append(self, latitude: float, longitude: float) -> None:
        if latitude == 0.0 and longitude == 0.0:  # receiver has no fix yet
            return
        if self._origin is None:
            self._origin = (latitude, longitude)
        north, east = _offset_metres(self._origin, latitude, longitude)
        self._norths.append(north)
        self._easts.append(east)
        self._track.setData(list(self._easts), list(self._norths))
        self._position.setData([east], [north])
        self._area.show_plot(True)
        self._show_position(f"{latitude:.6f}", f"{longitude:.6f}")

    def clear_data(self) -> None:
        self._origin = None
        self._norths.clear()
        self._easts.clear()
        self._track.setData([], [])
        self._position.setData([], [])
        self._area.show_plot(False)
        self._show_position(PLACEHOLDER, PLACEHOLDER)

    def _show_position(self, latitude: str, longitude: str) -> None:
        size = theme.EMPHASIS_FONT_SIZE_PT
        self._caption.setText(f"Lat <b style='font-size:{size}pt'>{latitude}</b>&nbsp;&nbsp;&nbsp;"
                              f"Lon <b style='font-size:{size}pt'>{longitude}</b>")


def _offset_metres(origin: tuple[float, float], latitude: float, longitude: float) -> tuple[float, float]:
    """North and east distance from origin (equirectangular, accurate over a few km)."""
    origin_latitude, origin_longitude = origin
    north = math.radians(latitude - origin_latitude) * EARTH_RADIUS_M
    east = math.radians(longitude - origin_longitude) * EARTH_RADIUS_M * math.cos(math.radians(origin_latitude))
    return north, east


# --- Text read-outs -----------------------------------------------------------

class PropertyList(QWidget):
    """Sectioned 'name ..... value' rows for non-plotted telemetry (GS3, GS5)."""

    def __init__(self) -> None:
        super().__init__()
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(12)
        self._grid.setVerticalSpacing(3)
        self._grid.setColumnStretch(1, 1)
        self._values: dict[str, QLabel] = {}
        self._badges: dict[str, QLabel] = {}

    def add_section(self, title: str) -> None:
        row = self._grid.rowCount()
        if row:
            self._grid.setRowMinimumHeight(row, 8)
            row += 1
        self._grid.addWidget(make_section_title(title), row, 0, 1, 2)

    def add_row(self, name: str) -> None:
        value = _label(PLACEHOLDER, "PropertyValue")
        value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._add(name, value)
        self._values[name] = value

    def add_badge_row(self, name: str) -> None:
        badge = make_badge(PLACEHOLDER)
        badge.setMinimumWidth(130)
        self._add(name, badge, Qt.AlignmentFlag.AlignRight)
        self._badges[name] = badge

    def set_text(self, name: str, text: str) -> None:
        self._values[name].setText(text)

    def set_badge(self, name: str, active: bool, on_text: str, off_text: str) -> None:
        badge = self._badges[name]
        badge.setText(on_text if active else off_text)
        theme.set_level(badge, "ok" if active else "idle")

    def clear(self) -> None:
        for value in self._values.values():
            value.setText(PLACEHOLDER)
        for badge in self._badges.values():
            badge.setText(PLACEHOLDER)
            theme.set_level(badge, "idle")

    def _add(self, name: str, widget: QWidget, alignment: Qt.AlignmentFlag | None = None) -> None:
        row = self._grid.rowCount()
        self._grid.addWidget(_label(name, "PropertyName"), row, 0)
        if alignment is None:
            self._grid.addWidget(widget, row, 1)
        else:
            self._grid.addWidget(widget, row, 1, alignment)


class VectorTable(QWidget):
    """Three-axis sensor values in aligned X / Y / Z columns."""

    AXES = ("X", "Y", "Z")

    def __init__(self, rows: list[str]) -> None:
        super().__init__()
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(3)
        grid.setColumnStretch(0, 1)
        for column, axis in enumerate(self.AXES, start=1):
            header = _label(axis, "SectionTitle")
            header.setAlignment(Qt.AlignmentFlag.AlignRight)
            grid.addWidget(header, 0, column)
            grid.setColumnMinimumWidth(column, 62)
        self._cells: dict[str, list[QLabel]] = {}
        for row, name in enumerate(rows, start=1):
            grid.addWidget(_label(name, "PropertyName"), row, 0)
            cells = []
            for column in range(1, len(self.AXES) + 1):
                cell = _label(PLACEHOLDER, "PropertyValue")
                cell.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                grid.addWidget(cell, row, column)
                cells.append(cell)
            self._cells[name] = cells

    def set_row(self, name: str, values: tuple[float, float, float], decimals: int) -> None:
        for cell, value in zip(self._cells[name], values):
            cell.setText(f"{value:.{decimals}f}")

    def clear(self) -> None:
        for cells in self._cells.values():
            for cell in cells:
                cell.setText(PLACEHOLDER)


class StateStepper(QWidget):
    """Vertical list of flight states: completed, current and pending."""

    def __init__(self, states: list[str]) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self._labels: dict[str, QLabel] = {}
        for state in states:
            label = _label(object_name="PropertyValue")
            layout.addWidget(label)
            self._labels[state] = label
        self.set_current(None)

    def set_current(self, current: str | None) -> None:
        names = list(self._labels)
        current_index = names.index(current) if current in names else -1
        for index, (state, label) in enumerate(self._labels.items()):
            text = state.replace("_", " ")
            if index < current_index:
                label.setText(f"<span style='color:{theme.OK}'>✔&nbsp; {text}</span>")
            elif index == current_index:
                label.setText(f"<span style='color:{theme.ACCENT}'>▶&nbsp; {text}</span>")
            else:
                label.setText(f"<span style='color:{theme.INACTIVE}; font-weight:normal'>○&nbsp; {text}</span>")


def make_divider() -> QFrame:
    divider = QFrame()
    divider.setObjectName("Divider")
    return divider
