"""Sunlight-readable theme (GS12).

Dark text on a light background, 14 pt minimum font size, bold plot traces
and bold axes. Hierarchy comes from size and weight rather than colour:
live values are the largest text, colour is reserved for status. Digits are
tabular so changing numbers do not jitter. All styling lives here; widgets
only set object names and the dynamic ``level`` property.
"""

from pathlib import Path

import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import QApplication, QFileDialog, QWidget

FONT_SIZE_PT = 14            # GS12 minimum, used for all regular text
EMPHASIS_FONT_SIZE_PT = 16   # property values, device names
VALUE_FONT_SIZE_PT = 22      # live values next to plots and in the status strip
PLOT_LINE_WIDTH = 3
AXIS_LINE_WIDTH = 2

WINDOW_BACKGROUND = "#e6eaef"
CARD_BACKGROUND = "#ffffff"
CARD_BORDER = "#c5ccd5"
TEXT = "#0b0f14"
SECONDARY_TEXT = "#39424e"
ACCENT = "#0a3d8f"
OK = "#0d6b2a"
WARNING = "#9a5200"
ALARM = "#b3140f"
INACTIVE = "#5d6673"
GRID_ALPHA = 0.25

SERIES_COLORS = ("#0a3d8f", "#c0261b", "#0f7a31", "#6a2c91")

_ICONS = (Path(__file__).parent / "icons").as_posix()

STYLE_SHEET = f"""
* {{
    font-size: {FONT_SIZE_PT}pt;
    color: {TEXT};
}}
QMainWindow, QWidget#Page {{
    background: {WINDOW_BACKGROUND};
}}
QFrame#Card, QFrame#Bar {{
    background: {CARD_BACKGROUND};
    border: 1px solid {CARD_BORDER};
    border-radius: 8px;
}}
QFrame#Card QLabel, QFrame#Bar QLabel {{
    background: transparent;
}}
QLabel#CardTitle {{
    font-weight: bold;
}}
QLabel#Caption, QLabel#PropertyName, QLabel#Unit {{
    color: {SECONDARY_TEXT};
}}
QLabel#SectionTitle {{
    color: {SECONDARY_TEXT};
    font-weight: bold;
}}
QLabel#BigValue {{
    font-size: {VALUE_FONT_SIZE_PT}pt;
    font-weight: bold;
}}
QLabel#PropertyValue {{
    font-size: {EMPHASIS_FONT_SIZE_PT}pt;
    font-weight: bold;
}}
QLabel#DeviceName, QLabel#AppTitle {{
    font-size: {EMPHASIS_FONT_SIZE_PT}pt;
    font-weight: bold;
    color: {ACCENT};
}}
QLabel#EmptyState {{
    color: {INACTIVE};
    font-weight: bold;
}}
QLabel#Badge {{
    font-weight: bold;
    border-radius: 5px;
    padding: 2px 10px;
    color: white;
    background: {ACCENT};
}}
QLabel#Badge[level="idle"] {{ background: #eceff3; color: {INACTIVE}; border: 1px solid {CARD_BORDER}; }}
QLabel#Badge[level="ok"] {{ background: {OK}; }}
QLabel#Badge[level="warning"] {{ background: {WARNING}; }}
QLabel#Badge[level="alarm"] {{ background: {ALARM}; }}
QLabel#Clock {{
    font-size: 20pt;
    font-weight: bold;
}}
QFrame#Divider {{
    background: {CARD_BORDER};
    max-height: 1px;
    min-height: 1px;
}}
QPushButton {{
    background: #eef1f5;
    border: 1px solid #8f99a6;
    border-radius: 6px;
    padding: 6px 10px;
    font-weight: bold;
    min-height: 30px;
}}
QPushButton:hover {{ background: #dfe5ec; }}
QPushButton:pressed {{ background: #cbd3dd; }}
QPushButton:disabled {{ color: #8a929c; background: #f3f5f7; border-color: #cfd4da; }}
QPushButton[role="primary"] {{ background: {ACCENT}; border-color: {ACCENT}; color: white; }}
QPushButton[role="primary"]:hover {{ background: #0c4aa8; }}
QPushButton[role="primary"]:disabled {{ background: #a7b8d2; border-color: #a7b8d2; color: white; }}
QPushButton[size="compact"] {{ min-height: 20px; padding: 3px 12px; }}
QPushButton[role="danger"] {{ background: #fdeceb; border-color: {ALARM}; color: {ALARM}; }}
QPushButton[role="danger"]:disabled {{ background: #f3f5f7; border-color: #cfd4da; color: #8a929c; }}
QLineEdit, QComboBox, QSpinBox {{
    background: white;
    border: 1px solid #8f99a6;
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 28px;
}}
QComboBox::drop-down {{
    border: none;
    width: 30px;
}}
QComboBox::down-arrow {{
    image: url({_ICONS}/chevron_down.svg);
    width: 16px;
    height: 16px;
}}
QSpinBox::up-button, QSpinBox::down-button {{
    subcontrol-origin: padding;
    width: 26px;
    border: none;
    border-left: 1px solid #c5ccd5;
    background: #eef1f5;
}}
QSpinBox::up-button {{ subcontrol-position: top right; border-top-right-radius: 5px; }}
QSpinBox::down-button {{ subcontrol-position: bottom right; border-bottom-right-radius: 5px; }}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background: #dfe5ec; }}
QSpinBox::up-arrow {{ image: url({_ICONS}/chevron_up.svg); width: 12px; height: 12px; }}
QSpinBox::down-arrow {{ image: url({_ICONS}/chevron_down.svg); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
    background: white;
    color: {TEXT};
    border: 1px solid #8f99a6;
    outline: none;
    padding: 4px;
    selection-background-color: {ACCENT};
    selection-color: white;
}}
QComboBox QAbstractItemView::item {{
    color: {TEXT};
    background: white;
    min-height: 32px;
    padding: 0 8px;
}}
QComboBox QAbstractItemView::item:hover,
QComboBox QAbstractItemView::item:selected {{
    color: white;
    background: {ACCENT};
}}
QPlainTextEdit {{
    background: white;
    border: none;
    font-family: Menlo, Consolas, monospace;
}}
QTabBar {{ background: {WINDOW_BACKGROUND}; }}
QTabBar::tab {{
    background: {WINDOW_BACKGROUND};
    border: none;
    border-bottom: 3px solid transparent;
    padding: 10px 20px 10px 20px;
    font-size: {EMPHASIS_FONT_SIZE_PT}pt;
    font-weight: bold;
    color: {SECONDARY_TEXT};
}}
QTabBar::tab:selected {{ color: {ACCENT}; border-bottom: 3px solid {ACCENT}; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QToolTip {{ color: {TEXT}; background: white; border: 1px solid {CARD_BORDER}; }}
"""


def _light_palette() -> QPalette:
    """Light palette regardless of the OS appearance, so native popups, dialogs
    and spin boxes never render dark text on a dark (dark mode) background."""
    palette = QPalette()
    colors = {
        QPalette.ColorRole.Window: WINDOW_BACKGROUND,
        QPalette.ColorRole.WindowText: TEXT,
        QPalette.ColorRole.Base: "#ffffff",
        QPalette.ColorRole.AlternateBase: "#f3f5f7",
        QPalette.ColorRole.Text: TEXT,
        QPalette.ColorRole.Button: "#eef1f5",
        QPalette.ColorRole.ButtonText: TEXT,
        QPalette.ColorRole.Highlight: ACCENT,
        QPalette.ColorRole.HighlightedText: "#ffffff",
        QPalette.ColorRole.ToolTipBase: "#ffffff",
        QPalette.ColorRole.ToolTipText: TEXT,
        QPalette.ColorRole.PlaceholderText: INACTIVE,
    }
    for role, color in colors.items():
        palette.setColor(role, QColor(color))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(INACTIVE))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(INACTIVE))
    return palette


def apply_theme(app: QApplication) -> None:
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    app.setPalette(_light_palette())
    font = app.font()
    font.setPointSize(FONT_SIZE_PT)
    font.setFeature(QFont.Tag("tnum"), 1)  # tabular digits: numbers keep their width
    app.setFont(font)
    app.setStyleSheet(STYLE_SHEET)
    pg.setConfigOptions(background=CARD_BACKGROUND, foreground=TEXT, antialias=True)


def bold_font(size: int = FONT_SIZE_PT) -> QFont:
    font = QFont()
    font.setPointSize(size)
    font.setBold(True)
    font.setFeature(QFont.Tag("tnum"), 1)
    return font


# Qt's own file dialog follows the style sheet (fonts >= 14 pt); the native one does not.
FILE_DIALOG_OPTIONS = QFileDialog.Option.DontUseNativeDialog


def series_color(index: int) -> str:
    return SERIES_COLORS[index % len(SERIES_COLORS)]


def series_pen(index: int) -> pg.QtGui.QPen:
    return pg.mkPen(series_color(index), width=PLOT_LINE_WIDTH)


def set_level(widget: QWidget, level: str) -> None:
    """Switches a dynamic style property (e.g. badge colour) and re-polishes."""
    widget.setProperty("level", level)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
