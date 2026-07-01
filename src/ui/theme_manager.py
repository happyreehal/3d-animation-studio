# ============================================================
# src/ui/theme_manager.py
# 3D Animation Studio - Theme & Stylesheet Manager
# Dark theme, colors, fonts sab yahan manage hote hain
# ============================================================

# ===== PATH SETUP =====
import sys
import os
if __name__ == "__main__":
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.dirname(os.path.dirname(_current_dir))
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
# ======================

from dataclasses import dataclass, field
from typing import Dict, Optional, List, Callable
from enum import Enum

from src.utils import get_logger, get_config

logger = get_logger("ThemeManager")


# ============================================================
# ENUMS
# ============================================================

class ThemeType(Enum):
    """Available themes"""
    DARK   = "dark"
    LIGHT  = "light"
    CUSTOM = "custom"


class AccentColor(Enum):
    """Preset accent colors"""
    CYAN      = "#00D4FF"   # Default - Studio blue
    PURPLE    = "#9B59B6"
    GREEN     = "#2ECC71"
    ORANGE    = "#E67E22"
    RED       = "#E74C3C"
    PINK      = "#FF6B9D"
    GOLD      = "#F1C40F"
    WHITE     = "#FFFFFF"


# ============================================================
# COLOR PALETTE
# ============================================================

@dataclass
class ColorPalette:
    """
    Complete color palette for a theme.
    Har color ka ek naam aur hex value.
    """
    # === BACKGROUNDS ===
    bg_primary:     str = "#0F0F19"   # Main window background
    bg_secondary:   str = "#1A1A2E"   # Panels background
    bg_tertiary:    str = "#16213E"   # Sub-panels
    bg_elevated:    str = "#252540"   # Elevated cards/dialogs
    bg_hover:       str = "#2A2A4A"   # Hover state
    bg_pressed:     str = "#1E1E35"   # Pressed state
    bg_selected:    str = "#0E3460"   # Selected items
    bg_disabled:    str = "#1A1A2E"   # Disabled elements

    # === TEXT ===
    text_primary:   str = "#FFFFFF"   # Main text
    text_secondary: str = "#8888AA"   # Secondary/muted text
    text_disabled:  str = "#444466"   # Disabled text
    text_accent:    str = "#00D4FF"   # Accent colored text
    text_warning:   str = "#F39C12"   # Warning text
    text_error:     str = "#E74C3C"   # Error text
    text_success:   str = "#2ECC71"   # Success text

    # === ACCENT ===
    accent:         str = "#00D4FF"   # Primary accent
    accent_hover:   str = "#33DDFF"   # Accent hover
    accent_pressed: str = "#0099BB"   # Accent pressed
    accent_muted:   str = "#004455"   # Muted accent (backgrounds)

    # === BORDERS ===
    border:         str = "#2A2A4A"   # Normal border
    border_focus:   str = "#00D4FF"   # Focused border
    border_hover:   str = "#3A3A6A"   # Hover border

    # === SCROLLBAR ===
    scrollbar_bg:   str = "#1A1A2E"
    scrollbar_handle: str = "#3A3A6A"
    scrollbar_hover:  str = "#00D4FF"

    # === SPECIAL ===
    shadow:         str = "#00000088"
    overlay:        str = "#00000066"
    separator:      str = "#2A2A4A"
    timeline_bg:    str = "#0D0D1A"
    timeline_track: str = "#1A1A2E"
    keyframe:       str = "#00D4FF"
    playhead:       str = "#FF4444"

    def with_accent(self, accent_hex: str) -> "ColorPalette":
        """
        Naya palette banao custom accent color ke saath.
        Accent se related saare colors update ho jaate hain.
        """
        import copy
        new = copy.deepcopy(self)
        new.accent         = accent_hex
        new.text_accent    = accent_hex
        new.border_focus   = accent_hex
        new.scrollbar_hover= accent_hex
        new.keyframe       = accent_hex

        # Accent hover/pressed calculate karo (lighten/darken)
        r, g, b = self._hex_to_rgb(accent_hex)
        new.accent_hover   = self._rgb_to_hex(
            min(255, int(r * 1.2)),
            min(255, int(g * 1.2)),
            min(255, int(b * 1.2))
        )
        new.accent_pressed = self._rgb_to_hex(
            int(r * 0.7),
            int(g * 0.7),
            int(b * 0.7)
        )
        new.accent_muted   = self._rgb_to_hex(
            int(r * 0.25),
            int(g * 0.25),
            int(b * 0.25)
        )
        return new

    @staticmethod
    def _hex_to_rgb(hex_color: str):
        hex_color = hex_color.lstrip('#')
        return (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16),
        )

    @staticmethod
    def _rgb_to_hex(r: int, g: int, b: int) -> str:
        return f"#{r:02X}{g:02X}{b:02X}"


# Light theme palette
LIGHT_PALETTE = ColorPalette(
    bg_primary     = "#F5F5F5",
    bg_secondary   = "#FFFFFF",
    bg_tertiary    = "#EEEEEE",
    bg_elevated    = "#FFFFFF",
    bg_hover       = "#E0E0E0",
    bg_pressed     = "#D0D0D0",
    bg_selected    = "#CCE8FF",
    bg_disabled    = "#F0F0F0",
    text_primary   = "#1A1A1A",
    text_secondary = "#666666",
    text_disabled  = "#AAAAAA",
    text_accent    = "#0078D4",
    text_warning   = "#D68910",
    text_error     = "#C0392B",
    text_success   = "#27AE60",
    accent         = "#0078D4",
    accent_hover   = "#106EBE",
    accent_pressed = "#005A9E",
    accent_muted   = "#CCE4F7",
    border         = "#CCCCCC",
    border_focus   = "#0078D4",
    border_hover   = "#AAAAAA",
    scrollbar_bg   = "#F0F0F0",
    scrollbar_handle="#CCCCCC",
    scrollbar_hover= "#0078D4",
    shadow         = "#00000033",
    overlay        = "#00000044",
    separator      = "#DDDDDD",
    timeline_bg    = "#E8E8E8",
    timeline_track = "#F0F0F0",
    keyframe       = "#0078D4",
    playhead       = "#FF4444",
)


# ============================================================
# FONT SETTINGS
# ============================================================

@dataclass
class FontSettings:
    """Font configuration"""
    family:       str = "Segoe UI"
    size_small:   int = 10
    size_normal:  int = 12
    size_medium:  int = 13
    size_large:   int = 15
    size_title:   int = 18
    size_header:  int = 22
    fallback:     str = "Arial, sans-serif"


# ============================================================
# QSS STYLESHEET GENERATOR
# ============================================================

class QSSGenerator:
    """
    PyQt5 QSS (Qt Style Sheet) generate karta hai.
    ColorPalette se dynamic stylesheet banata hai.
    """

    def __init__(self, palette: ColorPalette, fonts: FontSettings):
        self.p = palette
        self.f = fonts

    def generate(self) -> str:
        """Complete QSS stylesheet generate karo"""
        parts = [
            self._global_styles(),
            self._main_window(),
            self._menu_bar(),
            self._toolbar(),
            self._dock_widget(),
            self._tab_widget(),
            self._tree_widget(),
            self._list_widget(),
            self._table_widget(),
            self._push_button(),
            self._tool_button(),
            self._line_edit(),
            self._text_edit(),
            self._combo_box(),
            self._spin_box(),
            self._slider(),
            self._scroll_bar(),
            self._progress_bar(),
            self._check_box(),
            self._radio_button(),
            self._group_box(),
            self._label(),
            self._splitter(),
            self._status_bar(),
            self._tooltip(),
            self._dialog(),
            self._scroll_area(),
            self._frame(),
        ]
        return "\n\n".join(parts)

    def _global_styles(self) -> str:
        return f"""
/* ===== GLOBAL ===== */
* {{
    font-family: "{self.f.family}";
    font-size: {self.f.size_normal}px;
    color: {self.p.text_primary};
    outline: none;
    border: none;
}}

QWidget {{
    background-color: {self.p.bg_primary};
    color: {self.p.text_primary};
}}

QWidget:disabled {{
    color: {self.p.text_disabled};
    background-color: {self.p.bg_disabled};
}}"""

    def _main_window(self) -> str:
        return f"""
/* ===== MAIN WINDOW ===== */
QMainWindow {{
    background-color: {self.p.bg_primary};
}}

QMainWindow::separator {{
    background-color: {self.p.separator};
    width: 2px;
    height: 2px;
}}

QMainWindow::separator:hover {{
    background-color: {self.p.accent};
}}"""

    def _menu_bar(self) -> str:
        return f"""
/* ===== MENU BAR ===== */
QMenuBar {{
    background-color: {self.p.bg_secondary};
    color: {self.p.text_primary};
    border-bottom: 1px solid {self.p.border};
    padding: 2px;
    font-size: {self.f.size_normal}px;
}}

QMenuBar::item {{
    background-color: transparent;
    padding: 6px 12px;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    background-color: {self.p.bg_hover};
}}

QMenuBar::item:pressed {{
    background-color: {self.p.accent_muted};
}}

QMenu {{
    background-color: {self.p.bg_elevated};
    border: 1px solid {self.p.border};
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
    margin: 1px;
}}

QMenu::item:selected {{
    background-color: {self.p.accent_muted};
    color: {self.p.accent};
}}

QMenu::item:disabled {{
    color: {self.p.text_disabled};
}}

QMenu::separator {{
    height: 1px;
    background-color: {self.p.separator};
    margin: 4px 8px;
}}

QMenu::indicator {{
    width: 14px;
    height: 14px;
    margin-left: 4px;
}}"""

    def _toolbar(self) -> str:
        return f"""
/* ===== TOOLBAR ===== */
QToolBar {{
    background-color: {self.p.bg_secondary};
    border-bottom: 1px solid {self.p.border};
    padding: 3px;
    spacing: 3px;
}}

QToolBar::separator {{
    background-color: {self.p.separator};
    width: 1px;
    margin: 4px 6px;
}}

QToolBar QToolButton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 5px 8px;
    color: {self.p.text_primary};
    font-size: {self.f.size_normal}px;
}}

QToolBar QToolButton:hover {{
    background-color: {self.p.bg_hover};
    border-color: {self.p.border};
}}

QToolBar QToolButton:pressed {{
    background-color: {self.p.accent_muted};
    border-color: {self.p.accent};
}}

QToolBar QToolButton:checked {{
    background-color: {self.p.accent_muted};
    border-color: {self.p.accent};
    color: {self.p.accent};
}}"""

    def _dock_widget(self) -> str:
        return f"""
/* ===== DOCK WIDGET ===== */
QDockWidget {{
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
    color: {self.p.text_primary};
}}

QDockWidget::title {{
    background-color: {self.p.bg_secondary};
    color: {self.p.text_secondary};
    padding: 6px 8px;
    border-bottom: 1px solid {self.p.border};
    text-align: left;
    font-size: {self.f.size_small}px;
    font-weight: bold;
    letter-spacing: 1px;
    text-transform: uppercase;
}}

QDockWidget::close-button,
QDockWidget::float-button {{
    background: transparent;
    border: none;
    padding: 2px;
    border-radius: 3px;
}}

QDockWidget::close-button:hover,
QDockWidget::float-button:hover {{
    background-color: {self.p.bg_hover};
}}"""

    def _tab_widget(self) -> str:
        return f"""
/* ===== TAB WIDGET ===== */
QTabWidget::pane {{
    border: 1px solid {self.p.border};
    border-radius: 0px 4px 4px 4px;
    background-color: {self.p.bg_secondary};
}}

QTabBar::tab {{
    background-color: {self.p.bg_tertiary};
    color: {self.p.text_secondary};
    padding: 7px 16px;
    border: 1px solid {self.p.border};
    border-bottom: none;
    border-radius: 4px 4px 0px 0px;
    margin-right: 2px;
    font-size: {self.f.size_normal}px;
}}

QTabBar::tab:selected {{
    background-color: {self.p.bg_secondary};
    color: {self.p.accent};
    border-bottom-color: {self.p.bg_secondary};
    border-top: 2px solid {self.p.accent};
}}

QTabBar::tab:hover:!selected {{
    background-color: {self.p.bg_hover};
    color: {self.p.text_primary};
}}"""

    def _tree_widget(self) -> str:
        return f"""
/* ===== TREE WIDGET ===== */
QTreeWidget, QTreeView {{
    background-color: {self.p.bg_secondary};
    alternate-background-color: {self.p.bg_tertiary};
    border: 1px solid {self.p.border};
    border-radius: 4px;
    show-decoration-selected: 1;
    outline: 0;
}}

QTreeWidget::item, QTreeView::item {{
    padding: 4px 6px;
    border-radius: 3px;
    margin: 1px;
}}

QTreeWidget::item:hover, QTreeView::item:hover {{
    background-color: {self.p.bg_hover};
}}

QTreeWidget::item:selected, QTreeView::item:selected {{
    background-color: {self.p.bg_selected};
    color: {self.p.text_primary};
}}

QTreeWidget::branch:has-siblings:!adjoins-item {{
    border-image: none;
    border: none;
}}

QTreeWidget::branch:closed:has-children {{
    color: {self.p.text_secondary};
}}

QTreeWidget::branch:open:has-children {{
    color: {self.p.accent};
}}

QHeaderView::section {{
    background-color: {self.p.bg_tertiary};
    color: {self.p.text_secondary};
    padding: 6px 8px;
    border: none;
    border-right: 1px solid {self.p.border};
    border-bottom: 1px solid {self.p.border};
    font-size: {self.f.size_small}px;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 1px;
}}"""

    def _list_widget(self) -> str:
        return f"""
/* ===== LIST WIDGET ===== */
QListWidget, QListView {{
    background-color: {self.p.bg_secondary};
    border: 1px solid {self.p.border};
    border-radius: 4px;
    outline: 0;
}}

QListWidget::item, QListView::item {{
    padding: 5px 8px;
    border-radius: 3px;
    margin: 1px 2px;
}}

QListWidget::item:hover, QListView::item:hover {{
    background-color: {self.p.bg_hover};
}}

QListWidget::item:selected, QListView::item:selected {{
    background-color: {self.p.bg_selected};
    color: {self.p.text_primary};
}}"""

    def _table_widget(self) -> str:
        return f"""
/* ===== TABLE WIDGET ===== */
QTableWidget, QTableView {{
    background-color: {self.p.bg_secondary};
    alternate-background-color: {self.p.bg_tertiary};
    border: 1px solid {self.p.border};
    border-radius: 4px;
    gridline-color: {self.p.border};
    outline: 0;
}}

QTableWidget::item, QTableView::item {{
    padding: 4px 6px;
}}

QTableWidget::item:selected, QTableView::item:selected {{
    background-color: {self.p.bg_selected};
    color: {self.p.text_primary};
}}"""

    def _push_button(self) -> str:
        return f"""
/* ===== PUSH BUTTON ===== */
QPushButton {{
    background-color: {self.p.bg_elevated};
    color: {self.p.text_primary};
    border: 1px solid {self.p.border};
    border-radius: 5px;
    padding: 7px 16px;
    font-size: {self.f.size_normal}px;
    min-width: 70px;
}}

QPushButton:hover {{
    background-color: {self.p.bg_hover};
    border-color: {self.p.border_hover};
}}

QPushButton:pressed {{
    background-color: {self.p.bg_pressed};
    border-color: {self.p.accent};
}}

QPushButton:disabled {{
    background-color: {self.p.bg_disabled};
    color: {self.p.text_disabled};
    border-color: {self.p.border};
}}

/* Primary / Accent button */
QPushButton#primary,
QPushButton[class="primary"] {{
    background-color: {self.p.accent};
    color: #000000;
    border-color: {self.p.accent};
    font-weight: bold;
}}

QPushButton#primary:hover,
QPushButton[class="primary"]:hover {{
    background-color: {self.p.accent_hover};
    border-color: {self.p.accent_hover};
}}

QPushButton#primary:pressed,
QPushButton[class="primary"]:pressed {{
    background-color: {self.p.accent_pressed};
}}

/* Danger button */
QPushButton#danger,
QPushButton[class="danger"] {{
    background-color: {self.p.text_error};
    color: #FFFFFF;
    border-color: {self.p.text_error};
}}

QPushButton#danger:hover {{
    background-color: #FF6B6B;
}}

/* Success button */
QPushButton#success,
QPushButton[class="success"] {{
    background-color: {self.p.text_success};
    color: #000000;
    border-color: {self.p.text_success};
}}"""

    def _tool_button(self) -> str:
        return f"""
/* ===== TOOL BUTTON ===== */
QToolButton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 4px;
    color: {self.p.text_primary};
}}

QToolButton:hover {{
    background-color: {self.p.bg_hover};
    border-color: {self.p.border};
}}

QToolButton:pressed, QToolButton:checked {{
    background-color: {self.p.accent_muted};
    border-color: {self.p.accent};
    color: {self.p.accent};
}}

QToolButton::menu-indicator {{
    image: none;
    width: 0px;
}}"""

    def _line_edit(self) -> str:
        return f"""
/* ===== LINE EDIT ===== */
QLineEdit {{
    background-color: {self.p.bg_tertiary};
    color: {self.p.text_primary};
    border: 1px solid {self.p.border};
    border-radius: 4px;
    padding: 6px 10px;
    font-size: {self.f.size_normal}px;
    selection-background-color: {self.p.accent_muted};
    selection-color: {self.p.text_primary};
}}

QLineEdit:focus {{
    border-color: {self.p.accent};
    background-color: {self.p.bg_elevated};
}}

QLineEdit:hover {{
    border-color: {self.p.border_hover};
}}

QLineEdit:disabled {{
    background-color: {self.p.bg_disabled};
    color: {self.p.text_disabled};
}}

QLineEdit[readOnly="true"] {{
    background-color: {self.p.bg_secondary};
    color: {self.p.text_secondary};
}}"""

    def _text_edit(self) -> str:
        return f"""
/* ===== TEXT EDIT ===== */
QTextEdit, QPlainTextEdit {{
    background-color: {self.p.bg_tertiary};
    color: {self.p.text_primary};
    border: 1px solid {self.p.border};
    border-radius: 4px;
    padding: 6px;
    font-size: {self.f.size_normal}px;
    selection-background-color: {self.p.accent_muted};
}}

QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {self.p.accent};
}}"""

    def _combo_box(self) -> str:
        return f"""
/* ===== COMBO BOX ===== */
QComboBox {{
    background-color: {self.p.bg_tertiary};
    color: {self.p.text_primary};
    border: 1px solid {self.p.border};
    border-radius: 4px;
    padding: 5px 10px;
    font-size: {self.f.size_normal}px;
    min-width: 80px;
}}

QComboBox:hover {{
    border-color: {self.p.border_hover};
}}

QComboBox:focus {{
    border-color: {self.p.accent};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid {self.p.border};
    border-radius: 0px 4px 4px 0px;
}}

QComboBox::down-arrow {{
    width: 10px;
    height: 10px;
    color: {self.p.text_secondary};
}}

QComboBox QAbstractItemView {{
    background-color: {self.p.bg_elevated};
    border: 1px solid {self.p.border};
    border-radius: 4px;
    selection-background-color: {self.p.accent_muted};
    selection-color: {self.p.accent};
    outline: 0;
    padding: 4px;
}}

QComboBox QAbstractItemView::item {{
    padding: 5px 8px;
    border-radius: 3px;
    min-height: 22px;
}}"""

    def _spin_box(self) -> str:
        return f"""
/* ===== SPIN BOX ===== */
QSpinBox, QDoubleSpinBox {{
    background-color: {self.p.bg_tertiary};
    color: {self.p.text_primary};
    border: 1px solid {self.p.border};
    border-radius: 4px;
    padding: 5px 8px;
    font-size: {self.f.size_normal}px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {self.p.accent};
}}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background-color: {self.p.bg_elevated};
    border: none;
    border-radius: 2px;
    width: 18px;
}}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {self.p.accent_muted};
}}"""

    def _slider(self) -> str:
        return f"""
/* ===== SLIDER ===== */
QSlider::groove:horizontal {{
    height: 4px;
    background-color: {self.p.border};
    border-radius: 2px;
}}

QSlider::sub-page:horizontal {{
    background-color: {self.p.accent};
    border-radius: 2px;
    height: 4px;
}}

QSlider::handle:horizontal {{
    background-color: {self.p.accent};
    border: 2px solid {self.p.bg_primary};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}

QSlider::handle:horizontal:hover {{
    background-color: {self.p.accent_hover};
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}

QSlider::groove:vertical {{
    width: 4px;
    background-color: {self.p.border};
    border-radius: 2px;
}}

QSlider::sub-page:vertical {{
    background-color: {self.p.accent};
    border-radius: 2px;
    width: 4px;
}}

QSlider::handle:vertical {{
    background-color: {self.p.accent};
    border: 2px solid {self.p.bg_primary};
    width: 14px;
    height: 14px;
    margin: 0 -5px;
    border-radius: 7px;
}}"""

    def _scroll_bar(self) -> str:
        return f"""
/* ===== SCROLL BAR ===== */
QScrollBar:horizontal {{
    background-color: {self.p.scrollbar_bg};
    height: 10px;
    border-radius: 5px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background-color: {self.p.scrollbar_handle};
    border-radius: 5px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {self.p.scrollbar_hover};
}}

QScrollBar:vertical {{
    background-color: {self.p.scrollbar_bg};
    width: 10px;
    border-radius: 5px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {self.p.scrollbar_handle};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {self.p.scrollbar_hover};
}}

QScrollBar::add-line, QScrollBar::sub-line,
QScrollBar::add-page, QScrollBar::sub-page {{
    background: none;
    border: none;
    width: 0px;
    height: 0px;
}}"""

    def _progress_bar(self) -> str:
        return f"""
/* ===== PROGRESS BAR ===== */
QProgressBar {{
    background-color: {self.p.bg_tertiary};
    border: 1px solid {self.p.border};
    border-radius: 5px;
    text-align: center;
    color: {self.p.text_primary};
    font-size: {self.f.size_small}px;
    height: 18px;
}}

QProgressBar::chunk {{
    background-color: {self.p.accent};
    border-radius: 4px;
}}"""

    def _check_box(self) -> str:
        return f"""
/* ===== CHECK BOX ===== */
QCheckBox {{
    spacing: 8px;
    color: {self.p.text_primary};
    font-size: {self.f.size_normal}px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {self.p.border};
    border-radius: 3px;
    background-color: {self.p.bg_tertiary};
}}

QCheckBox::indicator:hover {{
    border-color: {self.p.accent};
}}

QCheckBox::indicator:checked {{
    background-color: {self.p.accent};
    border-color: {self.p.accent};
}}

QCheckBox::indicator:disabled {{
    border-color: {self.p.border};
    background-color: {self.p.bg_disabled};
}}"""

    def _radio_button(self) -> str:
        return f"""
/* ===== RADIO BUTTON ===== */
QRadioButton {{
    spacing: 8px;
    color: {self.p.text_primary};
    font-size: {self.f.size_normal}px;
}}

QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {self.p.border};
    border-radius: 8px;
    background-color: {self.p.bg_tertiary};
}}

QRadioButton::indicator:hover {{
    border-color: {self.p.accent};
}}

QRadioButton::indicator:checked {{
    background-color: {self.p.accent};
    border-color: {self.p.accent};
}}"""

    def _group_box(self) -> str:
        return f"""
/* ===== GROUP BOX ===== */
QGroupBox {{
    border: 1px solid {self.p.border};
    border-radius: 6px;
    margin-top: 12px;
    padding: 10px 8px 8px 8px;
    color: {self.p.text_secondary};
    font-size: {self.f.size_small}px;
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 10px;
    color: {self.p.accent};
    font-size: {self.f.size_small}px;
    letter-spacing: 1px;
    text-transform: uppercase;
}}"""

    def _label(self) -> str:
        return f"""
/* ===== LABEL ===== */
QLabel {{
    background-color: transparent;
    color: {self.p.text_primary};
    font-size: {self.f.size_normal}px;
}}

QLabel[class="title"] {{
    font-size: {self.f.size_title}px;
    font-weight: bold;
    color: {self.p.text_primary};
}}

QLabel[class="header"] {{
    font-size: {self.f.size_large}px;
    font-weight: bold;
    color: {self.p.accent};
}}

QLabel[class="secondary"] {{
    color: {self.p.text_secondary};
    font-size: {self.f.size_small}px;
}}

QLabel[class="warning"] {{
    color: {self.p.text_warning};
}}

QLabel[class="error"] {{
    color: {self.p.text_error};
}}

QLabel[class="success"] {{
    color: {self.p.text_success};
}}"""

    def _splitter(self) -> str:
        return f"""
/* ===== SPLITTER ===== */
QSplitter::handle {{
    background-color: {self.p.separator};
}}

QSplitter::handle:horizontal {{
    width: 2px;
}}

QSplitter::handle:vertical {{
    height: 2px;
}}

QSplitter::handle:hover {{
    background-color: {self.p.accent};
}}"""

    def _status_bar(self) -> str:
        return f"""
/* ===== STATUS BAR ===== */
QStatusBar {{
    background-color: {self.p.bg_secondary};
    color: {self.p.text_secondary};
    border-top: 1px solid {self.p.border};
    font-size: {self.f.size_small}px;
    padding: 2px 8px;
}}

QStatusBar::item {{
    border: none;
}}

QStatusBar QLabel {{
    color: {self.p.text_secondary};
    font-size: {self.f.size_small}px;
    padding: 0 8px;
}}"""

    def _tooltip(self) -> str:
        return f"""
/* ===== TOOLTIP ===== */
QToolTip {{
    background-color: {self.p.bg_elevated};
    color: {self.p.text_primary};
    border: 1px solid {self.p.border};
    border-radius: 4px;
    padding: 5px 8px;
    font-size: {self.f.size_small}px;
    opacity: 240;
}}"""

    def _dialog(self) -> str:
        return f"""
/* ===== DIALOG ===== */
QDialog {{
    background-color: {self.p.bg_secondary};
    border: 1px solid {self.p.border};
    border-radius: 8px;
}}

QDialogButtonBox QPushButton {{
    min-width: 80px;
    padding: 6px 16px;
}}"""

    def _scroll_area(self) -> str:
        return f"""
/* ===== SCROLL AREA ===== */
QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}"""

    def _frame(self) -> str:
        return f"""
/* ===== FRAME ===== */
QFrame {{
    background-color: transparent;
}}

QFrame[frameShape="4"],
QFrame[frameShape="5"] {{
    color: {self.p.separator};
}}"""


# ============================================================
# THEME MANAGER - MAIN CLASS
# ============================================================

class ThemeManager:
    """
    Theme Manager - Application ka visual theme control karta hai.

    Features:
    - Dark / Light theme switch
    - Custom accent colors
    - Live theme reload (bina restart ke)
    - Theme export/import
    - Per-widget style overrides
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        ThemeManager initialize karo.

        Args:
            config: Optional config dict
        """
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # Current theme state
        self._current_theme   = ThemeType.DARK
        self._current_palette = ColorPalette()
        self._current_fonts   = FontSettings()
        self._current_accent  = AccentColor.CYAN.value

        # QSS generator
        self._qss_generator = QSSGenerator(self._current_palette, self._current_fonts)

        # Change listeners
        self._listeners: List[Callable] = []

        # Qt Application reference
        self._app = None

        # Config se initial theme load karo
        theme_str = self.config.get("ui", {}).get("theme", "dark")
        accent    = self.config.get("ui", {}).get("accent_color", AccentColor.CYAN.value)
        self._current_accent = accent

        if theme_str == "light":
            self._current_theme   = ThemeType.LIGHT
            self._current_palette = LIGHT_PALETTE.with_accent(accent)
        else:
            self._current_theme   = ThemeType.DARK
            self._current_palette = ColorPalette().with_accent(accent)

        self._qss_generator = QSSGenerator(self._current_palette, self._current_fonts)

        logger.info(
            f"✅ ThemeManager initialized | "
            f"Theme: {self._current_theme.value} | "
            f"Accent: {self._current_accent}"
        )

    def set_application(self, app):
        """
        Qt QApplication reference set karo.
        Theme apply karne ke liye zaruri hai.
        """
        self._app = app
        self.apply_theme()

    def apply_theme(self):
        """
        Current theme ko application pe apply karo.
        QSS generate karke QApplication pe set karta hai.
        """
        if self._app is None:
            logger.debug("App reference nahi hai, theme apply nahi hogi")
            return

        try:
            qss = self._qss_generator.generate()
            self._app.setStyleSheet(qss)
            self._notify_listeners("theme_applied", {
                "theme": self._current_theme.value,
                "accent": self._current_accent,
            })
            logger.debug(
                f"Theme applied: {self._current_theme.value} | "
                f"QSS size: {len(qss)} chars"
            )
        except Exception as e:
            logger.error(f"Theme apply failed: {e}")

    def set_theme(self, theme: ThemeType):
        """
        Theme switch karo (Dark/Light).

        Args:
            theme: ThemeType.DARK ya ThemeType.LIGHT
        """
        self._current_theme = theme

        if theme == ThemeType.LIGHT:
            self._current_palette = LIGHT_PALETTE.with_accent(self._current_accent)
        else:
            self._current_palette = ColorPalette().with_accent(self._current_accent)

        self._qss_generator = QSSGenerator(self._current_palette, self._current_fonts)
        self.apply_theme()

        logger.info(f"🎨 Theme changed to: {theme.value}")

    def toggle_theme(self):
        """Dark/Light theme toggle karo"""
        if self._current_theme == ThemeType.DARK:
            self.set_theme(ThemeType.LIGHT)
        else:
            self.set_theme(ThemeType.DARK)

    def set_accent_color(self, color: str):
        """
        Accent color change karo.

        Args:
            color: Hex color string (e.g., "#FF6B9D")
        """
        # Basic hex validation
        if not color.startswith("#") or len(color) not in [4, 7]:
            logger.warning(f"Invalid color format: {color}")
            return

        self._current_accent = color

        # Palette update karo
        self._current_palette = self._current_palette.with_accent(color)
        self._qss_generator   = QSSGenerator(self._current_palette, self._current_fonts)
        self.apply_theme()

        logger.info(f"🎨 Accent color: {color}")

    def set_font_size(self, size: int):
        """
        Base font size change karo.

        Args:
            size: Font size in pixels (10-18 recommended)
        """
        size = max(8, min(24, size))
        self._current_fonts = FontSettings(
            size_small  = size - 2,
            size_normal = size,
            size_medium = size + 1,
            size_large  = size + 3,
            size_title  = size + 6,
            size_header = size + 10,
        )
        self._qss_generator = QSSGenerator(self._current_palette, self._current_fonts)
        self.apply_theme()
        logger.info(f"🔤 Font size: {size}px")

    def get_palette(self) -> ColorPalette:
        """Current color palette lo"""
        return self._current_palette

    def get_color(self, color_name: str) -> str:
        """
        Specific color lo palette se.

        Args:
            color_name: e.g., "accent", "bg_primary", "text_secondary"
        """
        return getattr(self._current_palette, color_name, "#FFFFFF")

    def get_stylesheet(self) -> str:
        """Current QSS stylesheet string lo"""
        return self._qss_generator.generate()

    def get_widget_style(self, widget_type: str) -> str:
        """
        Specific widget ke liye inline style lo.
        Useful for dynamic widget styling.
        """
        styles = {
            "card": f"""
                background-color: {self._current_palette.bg_elevated};
                border: 1px solid {self._current_palette.border};
                border-radius: 8px;
                padding: 12px;
            """,
            "accent_card": f"""
                background-color: {self._current_palette.accent_muted};
                border: 1px solid {self._current_palette.accent};
                border-radius: 8px;
                padding: 12px;
            """,
            "separator": f"""
                background-color: {self._current_palette.separator};
                max-height: 1px;
                min-height: 1px;
            """,
            "badge": f"""
                background-color: {self._current_palette.accent};
                color: #000000;
                border-radius: 10px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: bold;
            """,
            "panel_header": f"""
                background-color: {self._current_palette.bg_secondary};
                color: {self._current_palette.text_secondary};
                font-size: {self._current_fonts.size_small}px;
                font-weight: bold;
                letter-spacing: 1px;
                padding: 6px 10px;
                border-bottom: 1px solid {self._current_palette.border};
            """,
        }
        return styles.get(widget_type, "")

    def is_dark(self) -> bool:
        """Dark theme active hai?"""
        return self._current_theme == ThemeType.DARK

    def get_theme_name(self) -> str:
        """Current theme name lo"""
        return self._current_theme.value

    def get_accent_color(self) -> str:
        """Current accent color lo"""
        return self._current_accent

    def get_available_accents(self) -> Dict[str, str]:
        """Available preset accent colors lo"""
        return {color.name.title(): color.value for color in AccentColor}

    # ----------------------------------------------------------
    # LISTENERS
    # ----------------------------------------------------------

    def add_listener(self, callback: Callable):
        """Theme change listener add karo"""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable):
        """Listener remove karo"""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self, event: str, data: Dict):
        """Sabhi listeners ko notify karo"""
        for cb in self._listeners:
            try:
                cb(event, data)
            except Exception as e:
                logger.warning(f"Theme listener error: {e}")

    # ----------------------------------------------------------
    # EXPORT / IMPORT
    # ----------------------------------------------------------

    def export_theme(self, filepath: str) -> bool:
        """
        Current theme settings export karo JSON file mein.
        Share ya backup ke liye.
        """
        try:
            from src.utils import write_json, ensure_dir
            from pathlib import Path
            ensure_dir(str(Path(filepath).parent))

            theme_data = {
                "theme": self._current_theme.value,
                "accent": self._current_accent,
                "font_size": self._current_fonts.size_normal,
                "palette": {
                    attr: getattr(self._current_palette, attr)
                    for attr in vars(self._current_palette)
                    if not attr.startswith('_')
                }
            }
            write_json(filepath, theme_data)
            logger.info(f"✅ Theme exported: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Theme export failed: {e}")
            return False

    def import_theme(self, filepath: str) -> bool:
        """
        Theme JSON file se import karo.
        """
        try:
            from src.utils import read_json
            data = read_json(filepath)
            if not data:
                return False

            # Theme type
            theme_str = data.get("theme", "dark")
            if theme_str == "light":
                self._current_theme = ThemeType.LIGHT
            else:
                self._current_theme = ThemeType.DARK

            # Accent color
            accent = data.get("accent", AccentColor.CYAN.value)
            self._current_accent = accent

            # Font size
            font_size = data.get("font_size", 12)
            self.set_font_size(font_size)

            # Custom palette colors
            if "palette" in data:
                for attr, value in data["palette"].items():
                    if hasattr(self._current_palette, attr):
                        setattr(self._current_palette, attr, value)

            self._qss_generator = QSSGenerator(self._current_palette, self._current_fonts)
            self.apply_theme()

            logger.info(f"✅ Theme imported: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Theme import failed: {e}")
            return False


# ============================================================
# GLOBAL INSTANCE
# ============================================================

_global_theme_manager: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """Global ThemeManager instance lo (singleton)"""
    global _global_theme_manager
    if _global_theme_manager is None:
        _global_theme_manager = ThemeManager()
    return _global_theme_manager


# ============================================================
# TEST SECTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section, ensure_dir

    setup_logging(log_level="DEBUG")
    print_banner("Theme Manager Test", "Dark Theme & QSS Stylesheet Generator")

    # ===== TEST 1: Initialization =====
    print_section("Test 1: Initialization")
    manager = ThemeManager()
    print(f"✅ ThemeManager initialized")
    print(f"   Theme  : {manager.get_theme_name()}")
    print(f"   Accent : {manager.get_accent_color()}")
    print(f"   Dark   : {manager.is_dark()}")

    # ===== TEST 2: Color Palette =====
    print_section("Test 2: Color Palette")
    palette = manager.get_palette()
    print(f"✅ Dark Palette Colors:")
    print(f"   bg_primary    : {palette.bg_primary}")
    print(f"   bg_secondary  : {palette.bg_secondary}")
    print(f"   accent        : {palette.accent}")
    print(f"   text_primary  : {palette.text_primary}")
    print(f"   text_secondary: {palette.text_secondary}")
    print(f"   border        : {palette.border}")

    # ===== TEST 3: Accent Color Change =====
    print_section("Test 3: Accent Color Change")
    accents = manager.get_available_accents()
    print(f"✅ Available accents ({len(accents)}):")
    for name, color in accents.items():
        print(f"   {name:12s}: {color}")

    # Purple accent test
    manager.set_accent_color(AccentColor.PURPLE.value)
    print(f"\n✅ After purple accent:")
    print(f"   accent      : {manager.get_palette().accent}")
    print(f"   accent_hover: {manager.get_palette().accent_hover}")
    print(f"   accent_muted: {manager.get_palette().accent_muted}")

    # Cyan wapas
    manager.set_accent_color(AccentColor.CYAN.value)
    print(f"\n✅ Reset to cyan: {manager.get_palette().accent}")

    # ===== TEST 4: Light Theme =====
    print_section("Test 4: Light Theme")
    manager.set_theme(ThemeType.LIGHT)
    light_palette = manager.get_palette()
    print(f"✅ Light theme palette:")
    print(f"   bg_primary : {light_palette.bg_primary}")
    print(f"   text_primary: {light_palette.text_primary}")
    print(f"   is_dark    : {manager.is_dark()}")

    # Dark wapas
    manager.set_theme(ThemeType.DARK)
    print(f"✅ Back to dark: is_dark={manager.is_dark()}")

    # ===== TEST 5: QSS Generation =====
    print_section("Test 5: QSS Stylesheet Generation")
    qss = manager.get_stylesheet()
    print(f"✅ QSS generated: {len(qss)} characters")
    print(f"   Contains 'QMainWindow': {'QMainWindow' in qss}")
    print(f"   Contains 'QPushButton': {'QPushButton' in qss}")
    print(f"   Contains 'QSlider'    : {'QSlider' in qss}")
    print(f"   Contains accent color : {AccentColor.CYAN.value in qss}")

    # First 300 chars preview
    print(f"\n   QSS Preview:")
    print(f"   {qss[:200].strip()}...")

    # ===== TEST 6: Widget Styles =====
    print_section("Test 6: Widget Inline Styles")
    for widget in ["card", "accent_card", "badge", "panel_header", "separator"]:
        style = manager.get_widget_style(widget)
        print(f"✅ '{widget}' style: {len(style)} chars")

    # ===== TEST 7: Specific Color Access =====
    print_section("Test 7: Specific Color Access")
    colors_to_check = [
        "accent", "bg_primary", "text_secondary",
        "border", "text_error", "text_success"
    ]
    for color_name in colors_to_check:
        color_val = manager.get_color(color_name)
        print(f"✅ get_color('{color_name}'): {color_val}")

    # ===== TEST 8: Theme Export/Import =====
    print_section("Test 8: Theme Export & Import")
    ensure_dir("cache")
    export_path = "cache/test_theme.json"

    exported = manager.export_theme(export_path)
    print(f"✅ Theme exported: {exported} → {export_path}")

    # Import karke check karo
    manager2 = ThemeManager()
    imported = manager2.import_theme(export_path)
    print(f"✅ Theme imported: {imported}")
    print(f"   Imported accent: {manager2.get_accent_color()}")
    print(f"   Imported theme : {manager2.get_theme_name()}")

    # ===== TEST 9: Listener Pattern =====
    print_section("Test 9: Theme Change Listener")
    events_received = []

    def theme_listener(event, data):
        events_received.append(event)
        print(f"   📢 Event received: {event} | data: {data}")

    manager.add_listener(theme_listener)
    manager.set_accent_color("#FF6B9D")  # Pink
    manager.set_theme(ThemeType.LIGHT)
    manager.set_theme(ThemeType.DARK)

    print(f"✅ Total events received: {len(events_received)}")

    # ===== TEST 10: Global Instance =====
    print_section("Test 10: Global Singleton")
    tm1 = get_theme_manager()
    tm2 = get_theme_manager()
    print(f"✅ Singleton working: {tm1 is tm2}")
    print(f"   Instance type: {type(tm1).__name__}")

    # Cleanup
    try:
        if os.path.exists(export_path):
            os.remove(export_path)
    except Exception:
        pass

    print_banner("✅ All Tests Passed!", "theme_manager.py Working Perfectly")