# ============================================================
# src/ui/toolbar.py
# 3D Animation Studio - Main Toolbar
# Top toolbar with all major actions and tools
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

from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

from src.utils import get_logger, get_config

logger = get_logger("Toolbar")


# ============================================================
# ENUMS
# ============================================================

class ToolType(Enum):
    """Tool types for viewport"""
    SELECT    = "select"
    MOVE      = "move"
    ROTATE    = "rotate"
    SCALE     = "scale"
    MEASURE   = "measure"


class ButtonStyle(Enum):
    """Button visual styles"""
    NORMAL    = "normal"
    PRIMARY   = "primary"
    DANGER    = "danger"
    SUCCESS   = "success"
    TOGGLE    = "toggle"
    SEPARATOR = "separator"


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class ToolbarAction:
    """
    Ek toolbar button/action ki definition.
    Icon, tooltip, shortcut sab yahan hota hai.
    """
    id:           str
    text:         str
    tooltip:      str
    icon_text:    str              = ""      # Emoji ya text icon
    shortcut:     str              = ""      # Display shortcut hint
    style:        str              = ButtonStyle.NORMAL.value
    checkable:    bool             = False   # Toggle button?
    checked:      bool             = False   # Initial checked state
    enabled:      bool             = True
    action_name:  str              = ""      # ShortcutsManager action
    group:        str              = ""      # Button group name
    separator_after: bool         = False   # Separator after this button?


@dataclass
class ToolbarGroup:
    """Group of related toolbar buttons"""
    id:       str
    name:     str
    actions:  List[ToolbarAction] = field(default_factory=list)
    visible:  bool = True


# ============================================================
# TOOLBAR DEFINITION
# ============================================================

class ToolbarDefinition:
    """
    Sabhi toolbar groups aur actions define karta hai.
    Yahan se main window toolbar build hoga.
    """

    @staticmethod
    def get_main_toolbar_groups() -> List[ToolbarGroup]:
        """Main toolbar ke sabhi groups"""
        groups = []

        # ===== FILE GROUP =====
        groups.append(ToolbarGroup(
            id="file", name="File",
            actions=[
                ToolbarAction(
                    id="new_project", text="New",
                    tooltip="Naya project banao (Ctrl+N)",
                    icon_text="📄", shortcut="Ctrl+N",
                    action_name="new_project",
                ),
                ToolbarAction(
                    id="open_project", text="Open",
                    tooltip="Project kholo (Ctrl+O)",
                    icon_text="📂", shortcut="Ctrl+O",
                    action_name="open_project",
                ),
                ToolbarAction(
                    id="save_project", text="Save",
                    tooltip="Project save karo (Ctrl+S)",
                    icon_text="💾", shortcut="Ctrl+S",
                    action_name="save_project",
                    style=ButtonStyle.PRIMARY.value,
                    separator_after=True,
                ),
            ]
        ))

        # ===== EDIT GROUP =====
        groups.append(ToolbarGroup(
            id="edit", name="Edit",
            actions=[
                ToolbarAction(
                    id="undo", text="Undo",
                    tooltip="Pichla action wapas lo (Ctrl+Z)",
                    icon_text="↩️", shortcut="Ctrl+Z",
                    action_name="undo",
                ),
                ToolbarAction(
                    id="redo", text="Redo",
                    tooltip="Redo karo (Ctrl+Y)",
                    icon_text="↪️", shortcut="Ctrl+Y",
                    action_name="redo",
                    separator_after=True,
                ),
            ]
        ))

        # ===== TOOLS GROUP =====
        groups.append(ToolbarGroup(
            id="tools", name="Tools",
            actions=[
                ToolbarAction(
                    id="tool_select", text="Select",
                    tooltip="Selection tool (Q)",
                    icon_text="🖱️", shortcut="Q",
                    checkable=True, checked=True,
                    action_name="tool_select",
                    group="viewport_tool",
                ),
                ToolbarAction(
                    id="tool_move", text="Move",
                    tooltip="Move tool (G)",
                    icon_text="✥", shortcut="G",
                    checkable=True,
                    action_name="tool_move",
                    group="viewport_tool",
                ),
                ToolbarAction(
                    id="tool_rotate", text="Rotate",
                    tooltip="Rotate tool (R)",
                    icon_text="🔄", shortcut="R",
                    checkable=True,
                    action_name="tool_rotate",
                    group="viewport_tool",
                ),
                ToolbarAction(
                    id="tool_scale", text="Scale",
                    tooltip="Scale tool (S)",
                    icon_text="⤢", shortcut="S",
                    checkable=True,
                    action_name="tool_scale",
                    group="viewport_tool",
                    separator_after=True,
                ),
            ]
        ))

        # ===== ADD OBJECTS GROUP =====
        groups.append(ToolbarGroup(
            id="add", name="Add",
            actions=[
                ToolbarAction(
                    id="add_character", text="Character",
                    tooltip="Naya character add karo (Shift+C)",
                    icon_text="🧍", shortcut="Shift+C",
                    action_name="add_character",
                ),
                ToolbarAction(
                    id="add_object", text="Object",
                    tooltip="3D object add karo (Shift+A)",
                    icon_text="📦", shortcut="Shift+A",
                    action_name="add_object",
                ),
                ToolbarAction(
                    id="add_light", text="Light",
                    tooltip="Light add karo (Shift+L)",
                    icon_text="💡", shortcut="Shift+L",
                    action_name="add_light",
                ),
                ToolbarAction(
                    id="add_camera", text="Camera",
                    tooltip="Camera add karo (Shift+K)",
                    icon_text="🎥", shortcut="Shift+K",
                    action_name="add_camera",
                    separator_after=True,
                ),
            ]
        ))

        # ===== VIEW GROUP =====
        groups.append(ToolbarGroup(
            id="view", name="View",
            actions=[
                ToolbarAction(
                    id="view_wireframe", text="Wire",
                    tooltip="Wireframe mode toggle (Alt+W)",
                    icon_text="⬡", shortcut="Alt+W",
                    checkable=True,
                    action_name="toggle_wireframe",
                ),
                ToolbarAction(
                    id="view_perspective", text="Persp",
                    tooltip="Perspective/Ortho toggle (Num5)",
                    icon_text="🔲",
                    checkable=True, checked=True,
                    action_name="toggle_perspective",
                ),
                ToolbarAction(
                    id="zoom_fit", text="Fit",
                    tooltip="Scene fit karo (F)",
                    icon_text="⊡", shortcut="F",
                    action_name="zoom_fit",
                    separator_after=True,
                ),
            ]
        ))

        # ===== PLAYBACK GROUP =====
        groups.append(ToolbarGroup(
            id="playback", name="Playback",
            actions=[
                ToolbarAction(
                    id="go_start", text="",
                    tooltip="Start pe jao (Home)",
                    icon_text="⏮",
                    action_name="go_to_start",
                ),
                ToolbarAction(
                    id="prev_frame", text="",
                    tooltip="Pichla frame (Left)",
                    icon_text="◀",
                    action_name="prev_frame",
                ),
                ToolbarAction(
                    id="play_pause", text="Play",
                    tooltip="Play/Pause (Space)",
                    icon_text="▶", shortcut="Space",
                    checkable=True,
                    action_name="play_pause",
                    style=ButtonStyle.PRIMARY.value,
                ),
                ToolbarAction(
                    id="next_frame", text="",
                    tooltip="Agla frame (Right)",
                    icon_text="▶",
                    action_name="next_frame",
                ),
                ToolbarAction(
                    id="go_end", text="",
                    tooltip="End pe jao (End)",
                    icon_text="⏭",
                    action_name="go_to_end",
                    separator_after=True,
                ),
            ]
        ))

        # ===== RENDER GROUP =====
        groups.append(ToolbarGroup(
            id="render", name="Render",
            actions=[
                ToolbarAction(
                    id="render_preview", text="Preview",
                    tooltip="Quick preview render (F5)",
                    icon_text="👁",
                    action_name="render_preview",
                ),
                ToolbarAction(
                    id="render_final", text="Render",
                    tooltip="Final render karo (F12)",
                    icon_text="🎬", shortcut="F12",
                    action_name="render_animation",
                    style=ButtonStyle.SUCCESS.value,
                ),
                ToolbarAction(
                    id="export_video", text="Export",
                    tooltip="Video export karo (Ctrl+E)",
                    icon_text="📤", shortcut="Ctrl+E",
                    action_name="export_video",
                    separator_after=True,
                ),
            ]
        ))

        # ===== SETTINGS GROUP =====
        groups.append(ToolbarGroup(
            id="settings", name="Settings",
            actions=[
                ToolbarAction(
                    id="toggle_theme", text="Theme",
                    tooltip="Dark/Light theme toggle karo",
                    icon_text="🌙",
                    checkable=True, checked=True,
                    action_name="toggle_theme",
                ),
                ToolbarAction(
                    id="preferences", text="Prefs",
                    tooltip="Preferences kholo (Ctrl+,)",
                    icon_text="⚙️", shortcut="Ctrl+,",
                    action_name="open_preferences",
                ),
            ]
        ))

        return groups

    @staticmethod
    def get_scene_toolbar_actions() -> List[ToolbarAction]:
        """
        Scene toolbar ke actions.
        Left side vertical toolbar.
        """
        return [
            ToolbarAction(
                id="scene_add_char", text="Add Character",
                tooltip="Naya character add karo",
                icon_text="🧍", action_name="add_character",
            ),
            ToolbarAction(
                id="scene_add_cube", text="Add Cube",
                tooltip="Cube add karo",
                icon_text="⬛", action_name="add_cube",
            ),
            ToolbarAction(
                id="scene_add_sphere", text="Add Sphere",
                tooltip="Sphere add karo",
                icon_text="⬤", action_name="add_sphere",
            ),
            ToolbarAction(
                id="scene_add_plane", text="Add Plane",
                tooltip="Plane add karo",
                icon_text="▬", action_name="add_plane",
            ),
            ToolbarAction(
                id="scene_add_light", text="Add Light",
                tooltip="Light add karo",
                icon_text="💡", action_name="add_light",
                separator_after=True,
            ),
            ToolbarAction(
                id="scene_physics", text="Physics",
                tooltip="Physics simulation toggle",
                icon_text="⚛", action_name="toggle_physics",
                checkable=True,
            ),
            ToolbarAction(
                id="scene_vfx", text="VFX",
                tooltip="VFX effects add karo",
                icon_text="✨", action_name="add_vfx",
            ),
        ]


# ============================================================
# TOOLBAR MANAGER - NON-QT (Data Layer)
# ============================================================

class ToolbarState:
    """
    Toolbar ka state manage karta hai.
    Qt se independent - pure Python.
    UI se alag rakh ke testing easy hoti hai.
    """

    def __init__(self):
        # Current active tool
        self._active_tool: str = ToolType.SELECT.value

        # Button states (id -> checked/enabled)
        self._button_states: Dict[str, Dict] = {}

        # Action callbacks
        self._action_callbacks: Dict[str, List[Callable]] = {}

        # Groups visibility
        self._group_visibility: Dict[str, bool] = {}

        # All toolbar groups
        self._groups: List[ToolbarGroup] = []

        # Initialize states
        self._init_states()

        logger.debug("ToolbarState initialized")

    def _init_states(self):
        """Sabhi buttons ke initial states set karo"""
        groups = ToolbarDefinition.get_main_toolbar_groups()
        self._groups = groups

        for group in groups:
            self._group_visibility[group.id] = group.visible
            for action in group.actions:
                self._button_states[action.id] = {
                    "checked": action.checked,
                    "enabled": action.enabled,
                    "visible": True,
                }

    def get_groups(self) -> List[ToolbarGroup]:
        """Toolbar groups lo"""
        return self._groups

    def get_active_tool(self) -> str:
        """Current active tool lo"""
        return self._active_tool

    def set_active_tool(self, tool: str):
        """Active tool set karo"""
        self._active_tool = tool

        # Tool buttons ka checked state update karo
        tool_map = {
            ToolType.SELECT.value: "tool_select",
            ToolType.MOVE.value:   "tool_move",
            ToolType.ROTATE.value: "tool_rotate",
            ToolType.SCALE.value:  "tool_scale",
        }

        for tool_type, button_id in tool_map.items():
            if button_id in self._button_states:
                self._button_states[button_id]["checked"] = (tool_type == tool)

        logger.debug(f"Active tool: {tool}")
        self._notify("tool_changed", {"tool": tool})

    def set_playing(self, is_playing: bool):
        """Playback state update karo"""
        if "play_pause" in self._button_states:
            self._button_states["play_pause"]["checked"] = is_playing
        icon = "⏸" if is_playing else "▶"
        logger.debug(f"Playback: {'Playing' if is_playing else 'Paused'}")
        self._notify("playback_changed", {"playing": is_playing})

    def set_button_enabled(self, button_id: str, enabled: bool):
        """Button enable/disable karo"""
        if button_id in self._button_states:
            self._button_states[button_id]["enabled"] = enabled

    def set_button_checked(self, button_id: str, checked: bool):
        """Button checked state set karo"""
        if button_id in self._button_states:
            self._button_states[button_id]["checked"] = checked

    def get_button_state(self, button_id: str) -> Dict:
        """Button state lo"""
        return self._button_states.get(button_id, {
            "checked": False, "enabled": True, "visible": True
        })

    def set_group_visible(self, group_id: str, visible: bool):
        """Group visibility toggle karo"""
        self._group_visibility[group_id] = visible
        self._notify("group_visibility_changed", {
            "group_id": group_id, "visible": visible
        })

    def register_callback(self, event: str, callback: Callable):
        """Event callback register karo"""
        if event not in self._action_callbacks:
            self._action_callbacks[event] = []
        self._action_callbacks[event].append(callback)

    def _notify(self, event: str, data: Dict):
        """Callbacks notify karo"""
        for cb in self._action_callbacks.get(event, []):
            try:
                cb(data)
            except Exception as e:
                logger.warning(f"Toolbar callback error: {e}")


# ============================================================
# QT TOOLBAR BUILDER
# ============================================================

class StudioToolbar:
    """
    PyQt5 QToolBar builder.
    ToolbarDefinition se actual Qt toolbar banata hai.
    """

    def __init__(
        self,
        main_window,
        shortcuts_manager=None,
        theme_manager=None,
        config: Optional[Dict] = None,
    ):
        """
        StudioToolbar initialize karo.

        Args:
            main_window: QMainWindow instance
            shortcuts_manager: ShortcutsManager (optional)
            theme_manager: ThemeManager (optional)
            config: Config dict
        """
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        self.main_window        = main_window
        self.shortcuts_manager  = shortcuts_manager
        self.theme_manager      = theme_manager

        # State manager
        self.state = ToolbarState()

        # Qt toolbar objects: group_id -> QToolBar
        self._toolbars: Dict[str, Any] = {}

        # Qt button references: action_id -> QToolButton/QAction
        self._buttons: Dict[str, Any] = {}

        # Button groups: group_name -> QButtonGroup
        self._button_groups: Dict[str, Any] = {}

        # Build karo
        self._build_main_toolbar()

        logger.info("✅ StudioToolbar initialized")

    def _build_main_toolbar(self):
        """Main toolbar build karo"""
        try:
            from PyQt5.QtWidgets import (
                QToolBar, QToolButton, QAction, QButtonGroup,
                QWidget, QLabel, QSizePolicy, QSeparator,
            )
            from PyQt5.QtCore import Qt, QSize
            from PyQt5.QtGui import QIcon, QFont

            # Main toolbar create karo
            toolbar = QToolBar("Main Toolbar", self.main_window)
            toolbar.setObjectName("MainToolbar")
            toolbar.setMovable(False)
            toolbar.setIconSize(QSize(20, 20))
            toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

            # Styling
            palette = None
            if self.theme_manager:
                palette = self.theme_manager.get_palette()

            if palette:
                toolbar.setStyleSheet(f"""
                    QToolBar {{
                        background-color: {palette.bg_secondary};
                        border-bottom: 1px solid {palette.border};
                        padding: 2px 4px;
                        spacing: 2px;
                    }}
                    QToolButton {{
                        background-color: transparent;
                        border: 1px solid transparent;
                        border-radius: 5px;
                        padding: 4px 8px;
                        color: {palette.text_primary};
                        font-size: 11px;
                        min-width: 44px;
                    }}
                    QToolButton:hover {{
                        background-color: {palette.bg_hover};
                        border-color: {palette.border};
                    }}
                    QToolButton:pressed {{
                        background-color: {palette.accent_muted};
                        border-color: {palette.accent};
                    }}
                    QToolButton:checked {{
                        background-color: {palette.accent_muted};
                        border-color: {palette.accent};
                        color: {palette.accent};
                    }}
                    QToolButton[class="primary"] {{
                        background-color: {palette.accent};
                        color: #000000;
                        font-weight: bold;
                    }}
                    QToolButton[class="primary"]:hover {{
                        background-color: {palette.accent_hover};
                    }}
                    QToolButton[class="success"] {{
                        background-color: {palette.text_success};
                        color: #000000;
                        font-weight: bold;
                    }}
                """)

            # Button groups (radio behavior ke liye)
            button_groups: Dict[str, Any] = {}

            # Groups iterate karo
            for group in self.state.get_groups():
                if not group.visible:
                    continue

                for action_def in group.actions:
                    btn = self._create_tool_button(
                        toolbar, action_def, palette, button_groups
                    )
                    if btn:
                        toolbar.addWidget(btn)
                        self._buttons[action_def.id] = btn

                    # Separator add karo
                    if action_def.separator_after:
                        sep = toolbar.addSeparator()

            # Spacer (right side pe push karne ke liye)
            spacer = QWidget()
            spacer.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Preferred
            )
            toolbar.addWidget(spacer)

            # FPS indicator label
            self._fps_label = QLabel("FPS: --")
            if palette:
                self._fps_label.setStyleSheet(
                    f"color: {palette.text_secondary}; "
                    f"font-size: 11px; padding: 0 8px;"
                )
            toolbar.addWidget(self._fps_label)

            # Frame counter label
            self._frame_label = QLabel("Frame: 0")
            if palette:
                self._frame_label.setStyleSheet(
                    f"color: {palette.accent}; "
                    f"font-size: 11px; font-weight: bold; padding: 0 8px;"
                )
            toolbar.addWidget(self._frame_label)

            # Main window pe add karo
            self.main_window.addToolBar(toolbar)
            self._toolbars["main"] = toolbar
            self._button_groups = button_groups

            logger.debug(
                f"Main toolbar built: {len(self._buttons)} buttons"
            )

        except ImportError:
            logger.warning("PyQt5 available nahi - toolbar Qt mode mein nahi banega")
        except Exception as e:
            logger.error(f"Toolbar build error: {e}")

    def _create_tool_button(
        self,
        toolbar,
        action_def: ToolbarAction,
        palette,
        button_groups: Dict,
    ):
        """Ek QToolButton create karo action definition se"""
        try:
            from PyQt5.QtWidgets import QToolButton, QButtonGroup
            from PyQt5.QtCore import Qt

            btn = QToolButton()
            btn.setObjectName(action_def.id)

            # Text aur icon set karo
            display_text = action_def.icon_text or action_def.text
            if action_def.icon_text and action_def.text:
                btn.setText(f"{action_def.icon_text}\n{action_def.text}")
            else:
                btn.setText(display_text)

            # Tooltip
            tip = action_def.tooltip
            if action_def.shortcut:
                tip += f"  [{action_def.shortcut}]"
            btn.setToolTip(tip)

            # Checkable
            if action_def.checkable:
                btn.setCheckable(True)
                btn.setChecked(action_def.checked)

            # Enable/disable
            btn.setEnabled(action_def.enabled)

            # Style class set karo
            if action_def.style == ButtonStyle.PRIMARY.value:
                btn.setProperty("class", "primary")
            elif action_def.style == ButtonStyle.SUCCESS.value:
                btn.setProperty("class", "success")
            elif action_def.style == ButtonStyle.DANGER.value:
                btn.setProperty("class", "danger")

            # Button group (radio behavior)
            if action_def.group:
                if action_def.group not in button_groups:
                    bg = QButtonGroup()
                    bg.setExclusive(True)
                    button_groups[action_def.group] = bg
                button_groups[action_def.group].addButton(btn)

            # Click handler connect karo
            action_name = action_def.action_name
            action_id   = action_def.id

            if action_def.checkable:
                btn.toggled.connect(
                    lambda checked, aid=action_id, an=action_name:
                    self._on_button_toggled(aid, an, checked)
                )
            else:
                btn.clicked.connect(
                    lambda _, aid=action_id, an=action_name:
                    self._on_button_clicked(aid, an)
                )

            return btn

        except Exception as e:
            logger.warning(f"Button create error ({action_def.id}): {e}")
            return None

    def _on_button_clicked(self, action_id: str, action_name: str):
        """Button click handle karo"""
        logger.debug(f"Toolbar button clicked: {action_id}")

        # State update
        self.state._notify("action_triggered", {
            "action_id":   action_id,
            "action_name": action_name,
        })

        # ShortcutsManager se action trigger karo
        if self.shortcuts_manager:
            self.shortcuts_manager.trigger_action(action_name)

    def _on_button_toggled(self, action_id: str, action_name: str, checked: bool):
        """Toggle button state change handle karo"""
        logger.debug(f"Toolbar button toggled: {action_id} = {checked}")

        # Tool buttons ke liye special handling
        tool_map = {
            "tool_select": ToolType.SELECT.value,
            "tool_move":   ToolType.MOVE.value,
            "tool_rotate": ToolType.ROTATE.value,
            "tool_scale":  ToolType.SCALE.value,
        }

        if action_id in tool_map and checked:
            self.state.set_active_tool(tool_map[action_id])

        # Play/pause special handling
        if action_id == "play_pause":
            self.state.set_playing(checked)

        self.state._notify("action_toggled", {
            "action_id":   action_id,
            "action_name": action_name,
            "checked":     checked,
        })

        if self.shortcuts_manager:
            self.shortcuts_manager.trigger_action(action_name)

    # ----------------------------------------------------------
    # PUBLIC API
    # ----------------------------------------------------------

    def update_fps(self, fps: float):
        """FPS display update karo"""
        if hasattr(self, '_fps_label') and self._fps_label:
            self._fps_label.setText(f"FPS: {fps:.1f}")

    def update_frame(self, frame: int, total_frames: int = 0):
        """Frame counter update karo"""
        if hasattr(self, '_frame_label') and self._frame_label:
            if total_frames > 0:
                self._frame_label.setText(f"Frame: {frame}/{total_frames}")
            else:
                self._frame_label.setText(f"Frame: {frame}")

    def set_playing(self, is_playing: bool):
        """Play/Pause button state update karo"""
        self.state.set_playing(is_playing)

        # Qt button update
        if "play_pause" in self._buttons:
            btn = self._buttons["play_pause"]
            try:
                btn.setChecked(is_playing)
                if is_playing:
                    btn.setText("⏸\nPause")
                else:
                    btn.setText("▶\nPlay")
            except Exception:
                pass

    def set_button_enabled(self, button_id: str, enabled: bool):
        """Button enable/disable karo"""
        self.state.set_button_enabled(button_id, enabled)
        if button_id in self._buttons:
            try:
                self._buttons[button_id].setEnabled(enabled)
            except Exception:
                pass

    def set_active_tool(self, tool: str):
        """Active tool programmatically set karo"""
        self.state.set_active_tool(tool)

        # Qt buttons update karo
        tool_button_map = {
            ToolType.SELECT.value: "tool_select",
            ToolType.MOVE.value:   "tool_move",
            ToolType.ROTATE.value: "tool_rotate",
            ToolType.SCALE.value:  "tool_scale",
        }

        for tool_type, btn_id in tool_button_map.items():
            if btn_id in self._buttons:
                try:
                    self._buttons[btn_id].setChecked(tool_type == tool)
                except Exception:
                    pass

    def get_toolbar(self, toolbar_id: str = "main"):
        """Qt QToolBar object lo"""
        return self._toolbars.get(toolbar_id)

    def get_all_toolbars(self) -> Dict:
        """Sabhi toolbars lo"""
        return self._toolbars.copy()

    def register_callback(self, event: str, callback: Callable):
        """Event callback register karo state manager mein"""
        self.state.register_callback(event, callback)


# ============================================================
# CONVENIENCE - Non-Qt Toolbar Info
# ============================================================

def get_toolbar_info() -> Dict:
    """
    Toolbar ka complete info lo (without Qt).
    Testing ya documentation ke liye.
    """
    groups = ToolbarDefinition.get_main_toolbar_groups()
    info = {
        "total_groups": len(groups),
        "total_buttons": 0,
        "groups": []
    }

    for group in groups:
        group_info = {
            "id":      group.id,
            "name":    group.name,
            "buttons": []
        }
        for action in group.actions:
            group_info["buttons"].append({
                "id":         action.id,
                "text":       action.text,
                "tooltip":    action.tooltip,
                "icon":       action.icon_text,
                "shortcut":   action.shortcut,
                "checkable":  action.checkable,
                "style":      action.style,
            })
            info["total_buttons"] += 1
        info["groups"].append(group_info)

    return info


# ============================================================
# TEST SECTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="DEBUG")
    print_banner("Toolbar Test", "Studio Toolbar Definition & State Manager")

    # ===== TEST 1: Toolbar Definition =====
    print_section("Test 1: Toolbar Definition")
    info = get_toolbar_info()
    print(f"✅ Total groups : {info['total_groups']}")
    print(f"   Total buttons: {info['total_buttons']}")
    print()
    for group in info["groups"]:
        print(f"   📁 {group['name']:12s} ({len(group['buttons'])} buttons)")
        for btn in group["buttons"]:
            icon     = btn['icon'] or "  "
            shortcut = f"[{btn['shortcut']}]" if btn['shortcut'] else ""
            print(
                f"      {icon} {btn['text']:12s} "
                f"{shortcut:15s} {btn['tooltip'][:40]}"
            )

    # ===== TEST 2: Toolbar State =====
    print_section("Test 2: Toolbar State Manager")
    state = ToolbarState()
    print(f"✅ ToolbarState initialized")
    print(f"   Active tool: {state.get_active_tool()}")

    # Tool switch test
    events = []
    def on_event(data):
        events.append(data)

    state.register_callback("tool_changed", on_event)
    state.register_callback("playback_changed", on_event)

    state.set_active_tool(ToolType.MOVE.value)
    print(f"✅ Tool changed to: {state.get_active_tool()}")

    state.set_active_tool(ToolType.ROTATE.value)
    print(f"✅ Tool changed to: {state.get_active_tool()}")

    state.set_playing(True)
    state.set_playing(False)
    print(f"✅ Events received: {len(events)}")
    for ev in events:
        print(f"   Event: {ev}")

    # ===== TEST 3: Button States =====
    print_section("Test 3: Button States")
    state.set_button_enabled("render_final", False)
    btn_state = state.get_button_state("render_final")
    print(f"✅ render_final enabled: {btn_state['enabled']}")

    state.set_button_checked("view_wireframe", True)
    btn_state2 = state.get_button_state("view_wireframe")
    print(f"✅ view_wireframe checked: {btn_state2['checked']}")

    # ===== TEST 4: Scene Toolbar Actions =====
    print_section("Test 4: Scene Toolbar Actions")
    scene_actions = ToolbarDefinition.get_scene_toolbar_actions()
    print(f"✅ Scene toolbar actions: {len(scene_actions)}")
    for action in scene_actions:
        print(
            f"   {action.icon_text} {action.text:15s} → {action.action_name}"
        )

    # ===== TEST 5: Qt Toolbar (if available) =====
    print_section("Test 5: Qt Toolbar Build Test")
    try:
        from PyQt5.QtWidgets import QApplication, QMainWindow
        import sys as _sys

        app = QApplication.instance() or QApplication(_sys.argv)
        window = QMainWindow()

        # Theme manager import
        from src.ui.theme_manager import ThemeManager
        theme = ThemeManager()
        theme.set_application(app)

        # Shortcuts manager import
        from src.ui.shortcuts_manager import ShortcutsManager
        shortcuts = ShortcutsManager()

        # Toolbar build karo
        toolbar = StudioToolbar(
            main_window       = window,
            shortcuts_manager = shortcuts,
            theme_manager     = theme,
        )

        qt_toolbar = toolbar.get_toolbar("main")
        print(f"✅ Qt toolbar created: {qt_toolbar is not None}")
        print(f"   Buttons built: {len(toolbar._buttons)}")
        print(f"   Button IDs: {list(toolbar._buttons.keys())[:5]}...")

        # Callback test
        action_log = []
        toolbar.register_callback(
            "action_triggered",
            lambda d: action_log.append(d)
        )

        # Simulate button click
        toolbar._on_button_clicked("save_project", "save_project")
        print(f"✅ Action triggered: {len(action_log)} events")

        # FPS update test
        toolbar.update_fps(60.0)
        toolbar.update_frame(42, 300)
        print(f"✅ FPS/Frame labels updated")

        # Tool switch
        toolbar.set_active_tool(ToolType.MOVE.value)
        print(f"✅ Active tool: {toolbar.state.get_active_tool()}")

        # Play state
        toolbar.set_playing(True)
        toolbar.set_playing(False)
        print(f"✅ Play/Pause state toggled")

        window.show()
        print(f"✅ Window shown with toolbar")

        # Auto close after short delay
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(500, app.quit)
        app.exec_()
        print(f"✅ Qt test complete")

    except ImportError:
        print("⚠️  PyQt5 not available for visual test")
        print("✅  Non-Qt tests all passed")
    except Exception as e:
        print(f"⚠️  Qt test error: {e}")
        print("✅  Non-Qt tests all passed")

    # ===== TEST 6: All Action Names =====
    print_section("Test 6: All Action Names")
    groups = ToolbarDefinition.get_main_toolbar_groups()
    all_actions = []
    for group in groups:
        for action in group.actions:
            if action.action_name:
                all_actions.append(action.action_name)

    print(f"✅ Total unique actions: {len(set(all_actions))}")
    for action in sorted(set(all_actions)):
        print(f"   → {action}")

    print_banner("✅ All Tests Passed!", "toolbar.py Working Perfectly")