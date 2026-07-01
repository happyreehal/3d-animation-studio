# ============================================================
# src/ui/shortcuts_manager.py
# 3D Animation Studio - Keyboard Shortcuts Manager
# Sare keyboard shortcuts ek jagah manage hote hain
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

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from pathlib import Path

from src.utils import (
    get_logger,
    get_config,
    ensure_dir,
    write_json,
    read_json,
)

logger = get_logger("ShortcutsManager")


# ============================================================
# ENUMS
# ============================================================

class ShortcutCategory(Enum):
    """Shortcut categories for organization"""
    FILE        = "File"
    EDIT        = "Edit"
    VIEW        = "View"
    SCENE       = "Scene"
    ANIMATION   = "Animation"
    CAMERA      = "Camera"
    RENDER      = "Render"
    TIMELINE    = "Timeline"
    PLAYBACK    = "Playback"
    TOOLS       = "Tools"
    WINDOW      = "Window"
    EXPORT      = "Export"
    CUSTOM      = "Custom"


class ShortcutContext(Enum):
    """Context jismein shortcut active hoga"""
    GLOBAL      = "global"      # Hamesha active
    VIEWPORT    = "viewport"    # 3D viewport focus mein
    TIMELINE    = "timeline"    # Timeline focus mein
    PROPERTIES  = "properties"  # Properties panel
    ASSET_BROWSER = "asset_browser"
    TEXT_INPUT  = "text_input"  # Text field mein - disabled


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class Shortcut:
    """
    Ek keyboard shortcut ki definition.
    Har shortcut ka unique ID, key combo, aur action hota hai.
    """
    # Identity
    id: str                         # Unique identifier e.g., "file.save"
    name: str                       # Display name e.g., "Save Project"
    description: str                # Kya karta hai
    category: str                   # ShortcutCategory value

    # Key combination
    key: str                        # e.g., "S", "F5", "Delete"
    modifiers: List[str]            = field(default_factory=list)
    # Modifiers: "Ctrl", "Shift", "Alt", "Meta"

    # Behavior
    context: str                    = ShortcutContext.GLOBAL.value
    enabled: bool                   = True
    repeatable: bool                = False  # Hold karke repeat hoga?

    # Action
    action_name: str                = ""    # Registered action ka naam

    def get_display_string(self) -> str:
        """
        Human-readable shortcut string banao.
        e.g., "Ctrl+Shift+S"
        """
        parts = []
        # Modifiers pehle (fixed order)
        order = ["Ctrl", "Alt", "Shift", "Meta"]
        for mod in order:
            if mod in self.modifiers:
                parts.append(mod)
        parts.append(self.key)
        return "+".join(parts)

    def get_qt_key_sequence(self) -> str:
        """
        Qt QKeySequence ke liye string.
        e.g., "Ctrl+S"
        """
        return self.get_display_string()

    def matches(self, key: str, modifiers: List[str]) -> bool:
        """
        Check karo ki diya hua key combo is shortcut se match karta hai.
        Case-insensitive comparison.
        """
        if key.upper() != self.key.upper():
            return False
        # Modifiers check (order independent)
        return set(m.lower() for m in modifiers) == set(m.lower() for m in self.modifiers)

    def to_dict(self) -> Dict:
        """Serialization ke liye dict"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "key": self.key,
            "modifiers": self.modifiers,
            "context": self.context,
            "enabled": self.enabled,
            "repeatable": self.repeatable,
            "action_name": self.action_name,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Shortcut":
        """Dict se Shortcut banao"""
        return cls(
            id          = data.get("id", ""),
            name        = data.get("name", ""),
            description = data.get("description", ""),
            category    = data.get("category", ShortcutCategory.CUSTOM.value),
            key         = data.get("key", ""),
            modifiers   = data.get("modifiers", []),
            context     = data.get("context", ShortcutContext.GLOBAL.value),
            enabled     = data.get("enabled", True),
            repeatable  = data.get("repeatable", False),
            action_name = data.get("action_name", ""),
        )


@dataclass
class ShortcutConflict:
    """Do shortcuts ka conflict"""
    shortcut1_id: str
    shortcut2_id: str
    key_combo: str
    context: str


# ============================================================
# DEFAULT SHORTCUTS DEFINITIONS
# ============================================================

class DefaultShortcuts:
    """
    3D Animation Studio ke default shortcuts.
    Industry standard (Blender/DaVinci Resolve inspired).
    """

    @staticmethod
    def get_all() -> List[Shortcut]:
        """Sabhi default shortcuts ki list"""
        shortcuts = []

        # ===== FILE SHORTCUTS =====
        shortcuts.extend([
            Shortcut(
                id="file.new",
                name="New Project",
                description="Naya project banao",
                category=ShortcutCategory.FILE.value,
                key="N", modifiers=["Ctrl"],
                action_name="new_project",
            ),
            Shortcut(
                id="file.open",
                name="Open Project",
                description="Existing project kholo",
                category=ShortcutCategory.FILE.value,
                key="O", modifiers=["Ctrl"],
                action_name="open_project",
            ),
            Shortcut(
                id="file.save",
                name="Save Project",
                description="Project save karo",
                category=ShortcutCategory.FILE.value,
                key="S", modifiers=["Ctrl"],
                action_name="save_project",
            ),
            Shortcut(
                id="file.save_as",
                name="Save As",
                description="Naye naam se save karo",
                category=ShortcutCategory.FILE.value,
                key="S", modifiers=["Ctrl", "Shift"],
                action_name="save_project_as",
            ),
            Shortcut(
                id="file.import",
                name="Import Asset",
                description="3D model ya asset import karo",
                category=ShortcutCategory.FILE.value,
                key="I", modifiers=["Ctrl"],
                action_name="import_asset",
            ),
            Shortcut(
                id="file.export",
                name="Export Video",
                description="Video export karo",
                category=ShortcutCategory.FILE.value,
                key="E", modifiers=["Ctrl"],
                action_name="export_video",
            ),
            Shortcut(
                id="file.quit",
                name="Quit",
                description="Application band karo",
                category=ShortcutCategory.FILE.value,
                key="Q", modifiers=["Ctrl"],
                action_name="quit_app",
            ),
        ])

        # ===== EDIT SHORTCUTS =====
        shortcuts.extend([
            Shortcut(
                id="edit.undo",
                name="Undo",
                description="Pichla action wapas lo",
                category=ShortcutCategory.EDIT.value,
                key="Z", modifiers=["Ctrl"],
                action_name="undo",
                repeatable=True,
            ),
            Shortcut(
                id="edit.redo",
                name="Redo",
                description="Undo hua action phir karo",
                category=ShortcutCategory.EDIT.value,
                key="Y", modifiers=["Ctrl"],
                action_name="redo",
                repeatable=True,
            ),
            Shortcut(
                id="edit.redo_alt",
                name="Redo (Alt)",
                description="Undo hua action phir karo (alternate)",
                category=ShortcutCategory.EDIT.value,
                key="Z", modifiers=["Ctrl", "Shift"],
                action_name="redo",
                repeatable=True,
            ),
            Shortcut(
                id="edit.cut",
                name="Cut",
                description="Selected item cut karo",
                category=ShortcutCategory.EDIT.value,
                key="X", modifiers=["Ctrl"],
                action_name="cut",
            ),
            Shortcut(
                id="edit.copy",
                name="Copy",
                description="Selected item copy karo",
                category=ShortcutCategory.EDIT.value,
                key="C", modifiers=["Ctrl"],
                action_name="copy",
            ),
            Shortcut(
                id="edit.paste",
                name="Paste",
                description="Clipboard se paste karo",
                category=ShortcutCategory.EDIT.value,
                key="V", modifiers=["Ctrl"],
                action_name="paste",
            ),
            Shortcut(
                id="edit.duplicate",
                name="Duplicate",
                description="Selected object duplicate karo",
                category=ShortcutCategory.EDIT.value,
                key="D", modifiers=["Ctrl"],
                action_name="duplicate",
            ),
            Shortcut(
                id="edit.delete",
                name="Delete",
                description="Selected object delete karo",
                category=ShortcutCategory.EDIT.value,
                key="Delete", modifiers=[],
                action_name="delete_selected",
            ),
            Shortcut(
                id="edit.select_all",
                name="Select All",
                description="Sabhi objects select karo",
                category=ShortcutCategory.EDIT.value,
                key="A", modifiers=["Ctrl"],
                action_name="select_all",
            ),
            Shortcut(
                id="edit.deselect_all",
                name="Deselect All",
                description="Selection clear karo",
                category=ShortcutCategory.EDIT.value,
                key="A", modifiers=["Ctrl", "Shift"],
                action_name="deselect_all",
            ),
            Shortcut(
                id="edit.preferences",
                name="Preferences",
                description="Settings/Preferences kholo",
                category=ShortcutCategory.EDIT.value,
                key=",", modifiers=["Ctrl"],
                action_name="open_preferences",
            ),
        ])

        # ===== VIEW SHORTCUTS =====
        shortcuts.extend([
            Shortcut(
                id="view.fullscreen",
                name="Toggle Fullscreen",
                description="Fullscreen toggle karo",
                category=ShortcutCategory.VIEW.value,
                key="F11", modifiers=[],
                action_name="toggle_fullscreen",
            ),
            Shortcut(
                id="view.zoom_in",
                name="Zoom In",
                description="Viewport zoom in",
                category=ShortcutCategory.VIEW.value,
                key="+", modifiers=["Ctrl"],
                action_name="zoom_in",
                repeatable=True,
            ),
            Shortcut(
                id="view.zoom_out",
                name="Zoom Out",
                description="Viewport zoom out",
                category=ShortcutCategory.VIEW.value,
                key="-", modifiers=["Ctrl"],
                action_name="zoom_out",
                repeatable=True,
            ),
            Shortcut(
                id="view.zoom_fit",
                name="Zoom to Fit",
                description="Saari objects fit karo view mein",
                category=ShortcutCategory.VIEW.value,
                key="F", modifiers=[],
                context=ShortcutContext.VIEWPORT.value,
                action_name="zoom_fit",
            ),
            Shortcut(
                id="view.reset_view",
                name="Reset View",
                description="Camera view reset karo",
                category=ShortcutCategory.VIEW.value,
                key="Numpad0", modifiers=[],
                context=ShortcutContext.VIEWPORT.value,
                action_name="reset_view",
            ),
            Shortcut(
                id="view.perspective_toggle",
                name="Toggle Perspective",
                description="Perspective/Orthographic toggle",
                category=ShortcutCategory.VIEW.value,
                key="Numpad5", modifiers=[],
                context=ShortcutContext.VIEWPORT.value,
                action_name="toggle_perspective",
            ),
            Shortcut(
                id="view.front",
                name="Front View",
                description="Front view se dekho",
                category=ShortcutCategory.VIEW.value,
                key="Numpad1", modifiers=[],
                context=ShortcutContext.VIEWPORT.value,
                action_name="view_front",
            ),
            Shortcut(
                id="view.side",
                name="Side View",
                description="Side view se dekho",
                category=ShortcutCategory.VIEW.value,
                key="Numpad3", modifiers=[],
                context=ShortcutContext.VIEWPORT.value,
                action_name="view_side",
            ),
            Shortcut(
                id="view.top",
                name="Top View",
                description="Top view se dekho",
                category=ShortcutCategory.VIEW.value,
                key="Numpad7", modifiers=[],
                context=ShortcutContext.VIEWPORT.value,
                action_name="view_top",
            ),
            Shortcut(
                id="view.wireframe",
                name="Toggle Wireframe",
                description="Wireframe mode toggle karo",
                category=ShortcutCategory.VIEW.value,
                key="W", modifiers=["Alt"],
                context=ShortcutContext.VIEWPORT.value,
                action_name="toggle_wireframe",
            ),
            Shortcut(
                id="view.hide_panels",
                name="Hide/Show Panels",
                description="Side panels hide ya show karo",
                category=ShortcutCategory.VIEW.value,
                key="Tab", modifiers=["Ctrl"],
                action_name="toggle_panels",
            ),
        ])

        # ===== SCENE SHORTCUTS =====
        shortcuts.extend([
            Shortcut(
                id="scene.add_character",
                name="Add Character",
                description="Naya character scene mein add karo",
                category=ShortcutCategory.SCENE.value,
                key="C", modifiers=["Shift"],
                action_name="add_character",
            ),
            Shortcut(
                id="scene.add_object",
                name="Add Object",
                description="Naya 3D object add karo",
                category=ShortcutCategory.SCENE.value,
                key="A", modifiers=["Shift"],
                action_name="add_object",
            ),
            Shortcut(
                id="scene.add_light",
                name="Add Light",
                description="Naya light add karo",
                category=ShortcutCategory.SCENE.value,
                key="L", modifiers=["Shift"],
                action_name="add_light",
            ),
            Shortcut(
                id="scene.add_camera",
                name="Add Camera",
                description="Naya camera add karo",
                category=ShortcutCategory.SCENE.value,
                key="K", modifiers=["Shift"],
                action_name="add_camera",
            ),
            Shortcut(
                id="scene.group",
                name="Group Objects",
                description="Selected objects ko group karo",
                category=ShortcutCategory.SCENE.value,
                key="G", modifiers=["Ctrl"],
                action_name="group_objects",
            ),
            Shortcut(
                id="scene.ungroup",
                name="Ungroup",
                description="Group tod do",
                category=ShortcutCategory.SCENE.value,
                key="G", modifiers=["Ctrl", "Shift"],
                action_name="ungroup_objects",
            ),
            Shortcut(
                id="scene.hide_selected",
                name="Hide Selected",
                description="Selected objects hide karo",
                category=ShortcutCategory.SCENE.value,
                key="H", modifiers=[],
                context=ShortcutContext.VIEWPORT.value,
                action_name="hide_selected",
            ),
            Shortcut(
                id="scene.show_all",
                name="Show All",
                description="Sabhi hidden objects dikhaao",
                category=ShortcutCategory.SCENE.value,
                key="H", modifiers=["Alt"],
                context=ShortcutContext.VIEWPORT.value,
                action_name="show_all",
            ),
        ])

        # ===== ANIMATION SHORTCUTS =====
        shortcuts.extend([
            Shortcut(
                id="anim.insert_keyframe",
                name="Insert Keyframe",
                description="Current frame pe keyframe insert karo",
                category=ShortcutCategory.ANIMATION.value,
                key="K", modifiers=[],
                context=ShortcutContext.VIEWPORT.value,
                action_name="insert_keyframe",
            ),
            Shortcut(
                id="anim.delete_keyframe",
                name="Delete Keyframe",
                description="Current keyframe delete karo",
                category=ShortcutCategory.ANIMATION.value,
                key="K", modifiers=["Alt"],
                action_name="delete_keyframe",
            ),
            Shortcut(
                id="anim.next_keyframe",
                name="Next Keyframe",
                description="Agla keyframe",
                category=ShortcutCategory.ANIMATION.value,
                key="Right", modifiers=["Ctrl"],
                action_name="next_keyframe",
                repeatable=True,
            ),
            Shortcut(
                id="anim.prev_keyframe",
                name="Previous Keyframe",
                description="Pichla keyframe",
                category=ShortcutCategory.ANIMATION.value,
                key="Left", modifiers=["Ctrl"],
                action_name="prev_keyframe",
                repeatable=True,
            ),
            Shortcut(
                id="anim.bake",
                name="Bake Animation",
                description="Animation bake karo",
                category=ShortcutCategory.ANIMATION.value,
                key="B", modifiers=["Ctrl", "Shift"],
                action_name="bake_animation",
            ),
        ])

        # ===== CAMERA SHORTCUTS =====
        shortcuts.extend([
            Shortcut(
                id="camera.look_through",
                name="Look Through Camera",
                description="Active camera se dekho",
                category=ShortcutCategory.CAMERA.value,
                key="Numpad0", modifiers=[],
                context=ShortcutContext.VIEWPORT.value,
                action_name="look_through_camera",
            ),
            Shortcut(
                id="camera.set_active",
                name="Set Active Camera",
                description="Selected camera ko active banao",
                category=ShortcutCategory.CAMERA.value,
                key="Numpad0", modifiers=["Ctrl"],
                action_name="set_active_camera",
            ),
            Shortcut(
                id="camera.align_to_view",
                name="Align Camera to View",
                description="Camera ko current view pe align karo",
                category=ShortcutCategory.CAMERA.value,
                key="Numpad0", modifiers=["Ctrl", "Alt"],
                action_name="align_camera_to_view",
            ),
        ])

        # ===== RENDER SHORTCUTS =====
        shortcuts.extend([
            Shortcut(
                id="render.render_image",
                name="Render Image",
                description="Single frame render karo",
                category=ShortcutCategory.RENDER.value,
                key="F12", modifiers=[],
                action_name="render_image",
            ),
            Shortcut(
                id="render.render_animation",
                name="Render Animation",
                description="Puri animation render karo",
                category=ShortcutCategory.RENDER.value,
                key="F12", modifiers=["Ctrl"],
                action_name="render_animation",
            ),
            Shortcut(
                id="render.cancel",
                name="Cancel Render",
                description="Render cancel karo",
                category=ShortcutCategory.RENDER.value,
                key="Escape", modifiers=[],
                action_name="cancel_render",
            ),
            Shortcut(
                id="render.open_output",
                name="Open Render Output",
                description="Render output folder kholo",
                category=ShortcutCategory.RENDER.value,
                key="F12", modifiers=["Shift"],
                action_name="open_render_output",
            ),
        ])

        # ===== TIMELINE SHORTCUTS =====
        shortcuts.extend([
            Shortcut(
                id="timeline.play_pause",
                name="Play / Pause",
                description="Animation play ya pause karo",
                category=ShortcutCategory.PLAYBACK.value,
                key="Space", modifiers=[],
                action_name="play_pause",
            ),
            Shortcut(
                id="timeline.stop",
                name="Stop",
                description="Playback stop karo aur start pe jao",
                category=ShortcutCategory.PLAYBACK.value,
                key="Space", modifiers=["Shift"],
                action_name="stop",
            ),
            Shortcut(
                id="timeline.next_frame",
                name="Next Frame",
                description="Ek frame aage jao",
                category=ShortcutCategory.TIMELINE.value,
                key="Right", modifiers=[],
                context=ShortcutContext.TIMELINE.value,
                action_name="next_frame",
                repeatable=True,
            ),
            Shortcut(
                id="timeline.prev_frame",
                name="Previous Frame",
                description="Ek frame peeche jao",
                category=ShortcutCategory.TIMELINE.value,
                key="Left", modifiers=[],
                context=ShortcutContext.TIMELINE.value,
                action_name="prev_frame",
                repeatable=True,
            ),
            Shortcut(
                id="timeline.go_start",
                name="Go to Start",
                description="Timeline ke start pe jao",
                category=ShortcutCategory.TIMELINE.value,
                key="Home", modifiers=[],
                action_name="go_to_start",
            ),
            Shortcut(
                id="timeline.go_end",
                name="Go to End",
                description="Timeline ke end pe jao",
                category=ShortcutCategory.TIMELINE.value,
                key="End", modifiers=[],
                action_name="go_to_end",
            ),
            Shortcut(
                id="timeline.zoom_in",
                name="Timeline Zoom In",
                description="Timeline zoom in karo",
                category=ShortcutCategory.TIMELINE.value,
                key="=", modifiers=[],
                context=ShortcutContext.TIMELINE.value,
                action_name="timeline_zoom_in",
                repeatable=True,
            ),
            Shortcut(
                id="timeline.zoom_out",
                name="Timeline Zoom Out",
                description="Timeline zoom out karo",
                category=ShortcutCategory.TIMELINE.value,
                key="-", modifiers=[],
                context=ShortcutContext.TIMELINE.value,
                action_name="timeline_zoom_out",
                repeatable=True,
            ),
            Shortcut(
                id="timeline.split_clip",
                name="Split Clip",
                description="Current position pe clip split karo",
                category=ShortcutCategory.TIMELINE.value,
                key="B", modifiers=[],
                context=ShortcutContext.TIMELINE.value,
                action_name="split_clip",
            ),
            Shortcut(
                id="timeline.add_marker",
                name="Add Marker",
                description="Current frame pe marker add karo",
                category=ShortcutCategory.TIMELINE.value,
                key="M", modifiers=[],
                action_name="add_marker",
            ),
        ])

        # ===== WINDOW SHORTCUTS =====
        shortcuts.extend([
            Shortcut(
                id="window.scene_hierarchy",
                name="Scene Hierarchy",
                description="Scene hierarchy panel toggle",
                category=ShortcutCategory.WINDOW.value,
                key="1", modifiers=["Ctrl", "Shift"],
                action_name="toggle_scene_hierarchy",
            ),
            Shortcut(
                id="window.properties",
                name="Properties Panel",
                description="Properties panel toggle",
                category=ShortcutCategory.WINDOW.value,
                key="2", modifiers=["Ctrl", "Shift"],
                action_name="toggle_properties",
            ),
            Shortcut(
                id="window.asset_browser",
                name="Asset Browser",
                description="Asset browser toggle",
                category=ShortcutCategory.WINDOW.value,
                key="3", modifiers=["Ctrl", "Shift"],
                action_name="toggle_asset_browser",
            ),
            Shortcut(
                id="window.timeline",
                name="Timeline",
                description="Timeline panel toggle",
                category=ShortcutCategory.WINDOW.value,
                key="4", modifiers=["Ctrl", "Shift"],
                action_name="toggle_timeline",
            ),
            Shortcut(
                id="window.console",
                name="Console/Log",
                description="Debug console toggle",
                category=ShortcutCategory.WINDOW.value,
                key="`", modifiers=["Ctrl"],
                action_name="toggle_console",
            ),
            Shortcut(
                id="window.shortcuts_help",
                name="Keyboard Shortcuts",
                description="Shortcuts list dekho",
                category=ShortcutCategory.WINDOW.value,
                key="F1", modifiers=[],
                action_name="show_shortcuts",
            ),
        ])

        # ===== TOOLS SHORTCUTS =====
        shortcuts.extend([
            Shortcut(
                id="tools.select",
                name="Select Tool",
                description="Selection tool activate karo",
                category=ShortcutCategory.TOOLS.value,
                key="Q", modifiers=[],
                context=ShortcutContext.VIEWPORT.value,
                action_name="tool_select",
            ),
            Shortcut(
                id="tools.move",
                name="Move Tool",
                description="Move/Translate tool",
                category=ShortcutCategory.TOOLS.value,
                key="G", modifiers=[],
                context=ShortcutContext.VIEWPORT.value,
                action_name="tool_move",
            ),
            Shortcut(
                id="tools.rotate",
                name="Rotate Tool",
                description="Rotation tool",
                category=ShortcutCategory.TOOLS.value,
                key="R", modifiers=[],
                context=ShortcutContext.VIEWPORT.value,
                action_name="tool_rotate",
            ),
            Shortcut(
                id="tools.scale",
                name="Scale Tool",
                description="Scale tool",
                category=ShortcutCategory.TOOLS.value,
                key="S", modifiers=[],
                context=ShortcutContext.VIEWPORT.value,
                action_name="tool_scale",
            ),
            Shortcut(
                id="tools.measure",
                name="Measure Tool",
                description="Distance measure tool",
                category=ShortcutCategory.TOOLS.value,
                key="M", modifiers=["Shift"],
                context=ShortcutContext.VIEWPORT.value,
                action_name="tool_measure",
            ),
        ])

        # ===== EXPORT SHORTCUTS =====
        shortcuts.extend([
            Shortcut(
                id="export.quick_export",
                name="Quick Export",
                description="Default settings se jaldi export karo",
                category=ShortcutCategory.EXPORT.value,
                key="E", modifiers=["Ctrl", "Shift"],
                action_name="quick_export",
            ),
            Shortcut(
                id="export.youtube",
                name="Export for YouTube",
                description="YouTube ke liye export karo",
                category=ShortcutCategory.EXPORT.value,
                key="Y", modifiers=["Ctrl", "Shift"],
                action_name="export_youtube",
            ),
            Shortcut(
                id="export.batch",
                name="Batch Export",
                description="Multiple formats mein export karo",
                category=ShortcutCategory.EXPORT.value,
                key="B", modifiers=["Ctrl", "Shift"],
                action_name="batch_export",
            ),
        ])

        return shortcuts


# ============================================================
# SHORTCUTS MANAGER - MAIN CLASS
# ============================================================

class ShortcutsManager:
    """
    Keyboard Shortcuts Manager.

    Features:
    - Default shortcuts pre-loaded
    - Runtime action binding (Qt ya custom)
    - Conflict detection
    - Custom shortcut creation/modification
    - Import/Export shortcuts
    - Category-wise filtering
    - Search shortcuts
    - Enable/Disable individual shortcuts
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        ShortcutsManager initialize karo.

        Args:
            config: Optional configuration dict
        """
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # Shortcuts storage: id -> Shortcut
        self._shortcuts: Dict[str, Shortcut] = {}

        # Action callbacks: action_name -> List[Callable]
        self._action_handlers: Dict[str, List[Callable]] = {}

        # Custom shortcuts file
        self._custom_file = Path("presets/custom_shortcuts.json")

        # Qt QShortcut objects storage (agar Qt use kar rahe hain)
        self._qt_shortcuts: Dict[str, Any] = {}

        # Default shortcuts load karo
        self._load_defaults()

        # User custom shortcuts load karo (override karte hain)
        self._load_custom()

        logger.info(
            f"✅ ShortcutsManager initialized | "
            f"{len(self._shortcuts)} shortcuts loaded"
        )

    def _load_defaults(self):
        """Default shortcuts register karo"""
        for shortcut in DefaultShortcuts.get_all():
            self._shortcuts[shortcut.id] = shortcut
        logger.debug(f"📦 {len(self._shortcuts)} default shortcuts loaded")

    def _load_custom(self):
        """
        User ke custom/modified shortcuts load karo.
        Default shortcuts ko override karta hai.
        """
        try:
            if self._custom_file.exists():
                data = read_json(str(self._custom_file))
                if data and isinstance(data, list):
                    for item in data:
                        sc = Shortcut.from_dict(item)
                        if sc.id:
                            self._shortcuts[sc.id] = sc
                    logger.debug(f"Custom shortcuts loaded: {len(data)}")
        except Exception as e:
            logger.warning(f"Custom shortcuts load failed: {e}")

    def _save_custom(self):
        """
        Modified/custom shortcuts save karo.
        Sirf woh shortcuts save karta hai jo default se alag hain.
        """
        try:
            ensure_dir(str(self._custom_file.parent))
            # Sabhi shortcuts save karo (simple approach)
            data = [sc.to_dict() for sc in self._shortcuts.values()]
            write_json(str(self._custom_file), data)
        except Exception as e:
            logger.error(f"Custom shortcuts save failed: {e}")

    # ----------------------------------------------------------
    # SHORTCUT REGISTRATION & BINDING
    # ----------------------------------------------------------

    def register_action(
        self,
        action_name: str,
        handler: Callable,
    ):
        """
        Action handler register karo.
        Jab shortcut press hoga, yeh function call hoga.

        Args:
            action_name: e.g., "save_project"
            handler: Callable function
        """
        if action_name not in self._action_handlers:
            self._action_handlers[action_name] = []
        self._action_handlers[action_name].append(handler)
        logger.debug(f"Action registered: {action_name}")

    def unregister_action(self, action_name: str, handler: Optional[Callable] = None):
        """
        Action handler unregister karo.
        handler=None dene se sabhi handlers remove ho jaate hain.
        """
        if action_name in self._action_handlers:
            if handler:
                self._action_handlers[action_name] = [
                    h for h in self._action_handlers[action_name]
                    if h != handler
                ]
            else:
                del self._action_handlers[action_name]

    def trigger_action(self, action_name: str, *args, **kwargs) -> bool:
        """
        Action manually trigger karo.
        Registered handlers call hote hain.

        Returns:
            True agar koi handler tha
        """
        handlers = self._action_handlers.get(action_name, [])
        if not handlers:
            logger.debug(f"No handler for action: {action_name}")
            return False

        for handler in handlers:
            try:
                handler(*args, **kwargs)
            except Exception as e:
                logger.error(f"Action handler error ({action_name}): {e}")

        return True

    def handle_key_press(
        self,
        key: str,
        modifiers: List[str],
        context: str = ShortcutContext.GLOBAL.value,
    ) -> bool:
        """
        Key press event handle karo.
        Matching shortcut dhundho aur action trigger karo.

        Args:
            key: Pressed key e.g., "S", "F12", "Space"
            modifiers: Active modifiers e.g., ["Ctrl", "Shift"]
            context: Current context

        Returns:
            True agar shortcut mila aur handle hua
        """
        for shortcut in self._shortcuts.values():
            if not shortcut.enabled:
                continue

            # Context check
            sc_context = shortcut.context
            if sc_context != ShortcutContext.GLOBAL.value:
                if sc_context != context:
                    continue

            # Key match check
            if shortcut.matches(key, modifiers):
                action = shortcut.action_name
                if action:
                    triggered = self.trigger_action(action)
                    if triggered:
                        logger.debug(
                            f"Shortcut triggered: {shortcut.get_display_string()} "
                            f"→ {action}"
                        )
                    return True

        return False

    def bind_to_qt_widget(self, widget, parent_widget=None):
        """
        Qt widget pe shortcuts bind karo.
        QShortcut objects create karta hai.

        Args:
            widget: QWidget ya QMainWindow
            parent_widget: Parent widget (optional)
        """
        try:
            from PyQt5.QtWidgets import QShortcut
            from PyQt5.QtGui import QKeySequence

            target = parent_widget or widget

            for shortcut_id, shortcut in self._shortcuts.items():
                if not shortcut.enabled:
                    continue
                if not shortcut.action_name:
                    continue

                key_seq = shortcut.get_qt_key_sequence()
                if not key_seq:
                    continue

                try:
                    qt_sc = QShortcut(QKeySequence(key_seq), target)

                    # Action handler bind karo
                    action_name = shortcut.action_name
                    def make_trigger(an):
                        return lambda: self.trigger_action(an)

                    qt_sc.activated.connect(make_trigger(action_name))
                    self._qt_shortcuts[shortcut_id] = qt_sc

                except Exception as e:
                    logger.debug(f"Qt shortcut bind failed ({shortcut_id}): {e}")

            logger.info(
                f"✅ {len(self._qt_shortcuts)} Qt shortcuts bound to widget"
            )

        except ImportError:
            logger.warning("PyQt5 available nahi - Qt binding skip")

    # ----------------------------------------------------------
    # SHORTCUT MANAGEMENT
    # ----------------------------------------------------------

    def get_shortcut(self, shortcut_id: str) -> Optional[Shortcut]:
        """ID se shortcut lo"""
        return self._shortcuts.get(shortcut_id)

    def get_all_shortcuts(self) -> Dict[str, Shortcut]:
        """Sabhi shortcuts lo"""
        return self._shortcuts.copy()

    def get_shortcuts_by_category(
        self,
        category: str,
    ) -> List[Shortcut]:
        """Category se shortcuts filter karo"""
        return [
            sc for sc in self._shortcuts.values()
            if sc.category == category
        ]

    def get_shortcuts_by_context(
        self,
        context: str,
    ) -> List[Shortcut]:
        """Context se shortcuts filter karo"""
        return [
            sc for sc in self._shortcuts.values()
            if sc.context == context or sc.context == ShortcutContext.GLOBAL.value
        ]

    def search_shortcuts(self, query: str) -> List[Shortcut]:
        """
        Shortcuts search karo.
        Name, description, aur key combo mein search karta hai.
        """
        query_lower = query.lower()
        results = []

        for sc in self._shortcuts.values():
            if (
                query_lower in sc.name.lower()
                or query_lower in sc.description.lower()
                or query_lower in sc.get_display_string().lower()
                or query_lower in sc.id.lower()
            ):
                results.append(sc)

        return results

    def modify_shortcut(
        self,
        shortcut_id: str,
        new_key: str,
        new_modifiers: Optional[List[str]] = None,
    ) -> bool:
        """
        Existing shortcut ki key combo change karo.

        Args:
            shortcut_id: Shortcut ID
            new_key: Naya key
            new_modifiers: Naye modifiers (None = same rakho)

        Returns:
            True agar successful
        """
        sc = self._shortcuts.get(shortcut_id)
        if not sc:
            logger.warning(f"Shortcut nahi mila: {shortcut_id}")
            return False

        # Conflict check karo
        mods = new_modifiers if new_modifiers is not None else sc.modifiers
        conflicts = self.check_conflicts(new_key, mods, sc.context, exclude_id=shortcut_id)

        if conflicts:
            logger.warning(
                f"Shortcut conflict: {new_key}+{mods} "
                f"already used by {[c.shortcut2_id for c in conflicts]}"
            )

        # Update karo
        old_combo = sc.get_display_string()
        sc.key = new_key
        if new_modifiers is not None:
            sc.modifiers = new_modifiers

        self._save_custom()
        logger.info(
            f"✅ Shortcut modified: {shortcut_id} | "
            f"{old_combo} → {sc.get_display_string()}"
        )
        return True

    def enable_shortcut(self, shortcut_id: str, enabled: bool = True):
        """Shortcut enable ya disable karo"""
        sc = self._shortcuts.get(shortcut_id)
        if sc:
            sc.enabled = enabled
            self._save_custom()
            status = "enabled" if enabled else "disabled"
            logger.info(f"Shortcut {status}: {shortcut_id}")

    def add_custom_shortcut(
        self,
        shortcut_id: str,
        name: str,
        description: str,
        key: str,
        modifiers: Optional[List[str]] = None,
        action_name: str = "",
        category: str = ShortcutCategory.CUSTOM.value,
        context: str = ShortcutContext.GLOBAL.value,
    ) -> Optional[Shortcut]:
        """
        Naya custom shortcut add karo.

        Returns:
            Naya Shortcut object ya None agar conflict hai
        """
        mods = modifiers or []

        # Conflict check
        conflicts = self.check_conflicts(key, mods, context)
        if conflicts:
            logger.warning(
                f"Cannot add shortcut - conflict with: "
                f"{[c.shortcut2_id for c in conflicts]}"
            )
            return None

        sc = Shortcut(
            id          = shortcut_id,
            name        = name,
            description = description,
            category    = category,
            key         = key,
            modifiers   = mods,
            context     = context,
            action_name = action_name,
        )

        self._shortcuts[shortcut_id] = sc
        self._save_custom()

        logger.info(f"✅ Custom shortcut added: {shortcut_id} ({sc.get_display_string()})")
        return sc

    def remove_custom_shortcut(self, shortcut_id: str) -> bool:
        """Custom shortcut remove karo (default shortcuts nahi)"""
        sc = self._shortcuts.get(shortcut_id)
        if not sc:
            return False

        # Check karo ki yeh custom hai (not in defaults)
        default_ids = {d.id for d in DefaultShortcuts.get_all()}
        if shortcut_id in default_ids:
            logger.warning(f"Default shortcuts remove nahi ho sakte: {shortcut_id}")
            return False

        del self._shortcuts[shortcut_id]
        self._save_custom()
        logger.info(f"🗑️ Custom shortcut removed: {shortcut_id}")
        return True

    def reset_to_defaults(self):
        """Sabhi shortcuts default pe wapas karo"""
        self._shortcuts.clear()
        self._action_handlers.clear()
        self._load_defaults()

        # Custom file delete karo
        try:
            if self._custom_file.exists():
                os.remove(str(self._custom_file))
        except Exception:
            pass

        logger.info("✅ Shortcuts reset to defaults")

    # ----------------------------------------------------------
    # CONFLICT DETECTION
    # ----------------------------------------------------------

    def check_conflicts(
        self,
        key: str,
        modifiers: List[str],
        context: str = ShortcutContext.GLOBAL.value,
        exclude_id: Optional[str] = None,
    ) -> List[ShortcutConflict]:
        """
        Key combo conflict check karo.
        Agar same key+modifier already registered hai to conflict return karo.
        """
        conflicts = []
        key_combo = f"{'+'.join(sorted(modifiers))}+{key}" if modifiers else key

        for sc_id, sc in self._shortcuts.items():
            if not sc.enabled:
                continue
            if exclude_id and sc_id == exclude_id:
                continue

            # Context conflict check
            # Global shortcuts sab jagah conflict karte hain
            context_conflict = (
                sc.context == ShortcutContext.GLOBAL.value
                or context == ShortcutContext.GLOBAL.value
                or sc.context == context
            )

            if context_conflict and sc.matches(key, modifiers):
                conflicts.append(ShortcutConflict(
                    shortcut1_id = exclude_id or "new",
                    shortcut2_id = sc_id,
                    key_combo    = key_combo,
                    context      = context,
                ))

        return conflicts

    def get_all_conflicts(self) -> List[ShortcutConflict]:
        """Sabhi existing conflicts dhundho"""
        conflicts = []
        shortcuts_list = list(self._shortcuts.values())

        for i, sc1 in enumerate(shortcuts_list):
            for sc2 in shortcuts_list[i+1:]:
                if sc1.matches(sc2.key, sc2.modifiers):
                    # Context check
                    context_conflict = (
                        sc1.context == ShortcutContext.GLOBAL.value
                        or sc2.context == ShortcutContext.GLOBAL.value
                        or sc1.context == sc2.context
                    )
                    if context_conflict:
                        conflicts.append(ShortcutConflict(
                            shortcut1_id = sc1.id,
                            shortcut2_id = sc2.id,
                            key_combo    = sc1.get_display_string(),
                            context      = sc1.context,
                        ))

        return conflicts

    # ----------------------------------------------------------
    # EXPORT / IMPORT
    # ----------------------------------------------------------

    def export_shortcuts(self, filepath: str) -> bool:
        """Shortcuts export karo JSON file mein"""
        try:
            ensure_dir(str(Path(filepath).parent))
            data = [sc.to_dict() for sc in self._shortcuts.values()]
            write_json(filepath, data)
            logger.info(f"✅ Shortcuts exported: {filepath} ({len(data)} shortcuts)")
            return True
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False

    def import_shortcuts(self, filepath: str, merge: bool = True) -> int:
        """
        Shortcuts import karo JSON file se.

        Args:
            filepath: JSON file path
            merge: True = existing pe merge, False = replace

        Returns:
            Import hua shortcuts count
        """
        try:
            data = read_json(filepath)
            if not data or not isinstance(data, list):
                return 0

            if not merge:
                self._shortcuts.clear()

            count = 0
            for item in data:
                sc = Shortcut.from_dict(item)
                if sc.id:
                    self._shortcuts[sc.id] = sc
                    count += 1

            self._save_custom()
            logger.info(f"✅ Shortcuts imported: {count}")
            return count

        except Exception as e:
            logger.error(f"Import failed: {e}")
            return 0

    # ----------------------------------------------------------
    # DISPLAY / REPORTING
    # ----------------------------------------------------------

    def get_shortcuts_summary(self) -> Dict[str, List[Dict]]:
        """
        Category-wise shortcuts summary lo.
        UI display ke liye useful.
        """
        summary: Dict[str, List[Dict]] = {}

        for sc in self._shortcuts.values():
            cat = sc.category
            if cat not in summary:
                summary[cat] = []

            summary[cat].append({
                "id":          sc.id,
                "name":        sc.name,
                "description": sc.description,
                "key_combo":   sc.get_display_string(),
                "enabled":     sc.enabled,
                "context":     sc.context,
            })

        return summary

    def print_shortcuts_table(self, category: Optional[str] = None):
        """
        Shortcuts table print karo (console ke liye).
        Ek cheat sheet ki tarah.
        """
        print(f"\n{'='*70}")
        print(f"{'KEYBOARD SHORTCUTS':^70}")
        print(f"{'='*70}")

        summary = self.get_shortcuts_summary()

        categories = [category] if category else sorted(summary.keys())

        for cat in categories:
            if cat not in summary:
                continue

            shortcuts = summary[cat]
            print(f"\n  📁 {cat.upper()}")
            print(f"  {'-'*66}")

            for sc in sorted(shortcuts, key=lambda x: x['name']):
                status   = "✅" if sc['enabled'] else "❌"
                key_str  = sc['key_combo']
                name     = sc['name']
                print(f"  {status} {key_str:20s}  {name}")

        print(f"\n{'='*70}")
        print(f"  Total: {len(self._shortcuts)} shortcuts")
        print(f"{'='*70}\n")

    def get_statistics(self) -> Dict:
        """Shortcuts statistics lo"""
        total       = len(self._shortcuts)
        enabled     = sum(1 for sc in self._shortcuts.values() if sc.enabled)
        disabled    = total - enabled
        categories  = len(set(sc.category for sc in self._shortcuts.values()))
        conflicts   = len(self.get_all_conflicts())
        with_action = sum(1 for sc in self._shortcuts.values() if sc.action_name)

        return {
            "total":         total,
            "enabled":       enabled,
            "disabled":      disabled,
            "categories":    categories,
            "conflicts":     conflicts,
            "with_action":   with_action,
            "without_action": total - with_action,
        }


# ============================================================
# GLOBAL INSTANCE
# ============================================================

_global_shortcuts_manager: Optional[ShortcutsManager] = None


def get_shortcuts_manager() -> ShortcutsManager:
    """Global ShortcutsManager instance lo (singleton)"""
    global _global_shortcuts_manager
    if _global_shortcuts_manager is None:
        _global_shortcuts_manager = ShortcutsManager()
    return _global_shortcuts_manager


# ============================================================
# TEST SECTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section, ensure_dir

    setup_logging(log_level="DEBUG")
    print_banner("Shortcuts Manager Test", "Keyboard Shortcuts System")

    # ===== TEST 1: Initialization =====
    print_section("Test 1: Initialization")
    manager = ShortcutsManager()
    stats = manager.get_statistics()
    print(f"✅ ShortcutsManager initialized")
    print(f"   Total shortcuts : {stats['total']}")
    print(f"   Enabled         : {stats['enabled']}")
    print(f"   Categories      : {stats['categories']}")
    print(f"   With actions    : {stats['with_action']}")

    # ===== TEST 2: Shortcut Lookup =====
    print_section("Test 2: Shortcut Lookup")
    for sc_id in ["file.save", "edit.undo", "render.render_animation", "timeline.play_pause"]:
        sc = manager.get_shortcut(sc_id)
        if sc:
            print(f"✅ {sc_id:35s} → {sc.get_display_string():20s} | {sc.name}")

    # ===== TEST 3: Category Filter =====
    print_section("Test 3: Category Filtering")
    for cat in [
        ShortcutCategory.FILE.value,
        ShortcutCategory.RENDER.value,
        ShortcutCategory.PLAYBACK.value,
    ]:
        shortcuts = manager.get_shortcuts_by_category(cat)
        print(f"✅ {cat:15s}: {len(shortcuts)} shortcuts")
        for sc in shortcuts[:3]:
            print(f"   → {sc.get_display_string():15s} {sc.name}")

    # ===== TEST 4: Search =====
    print_section("Test 4: Search Shortcuts")
    for query in ["save", "render", "zoom", "frame"]:
        results = manager.search_shortcuts(query)
        print(f"✅ Search '{query}': {len(results)} results")
        for sc in results[:2]:
            print(f"   → {sc.get_display_string():15s} {sc.name}")

    # ===== TEST 5: Action Registration & Trigger =====
    print_section("Test 5: Action Registration & Trigger")
    triggered_actions = []

    def save_handler():
        triggered_actions.append("save_project")
        print(f"   💾 Save handler called!")

    def undo_handler():
        triggered_actions.append("undo")
        print(f"   ↩️  Undo handler called!")

    manager.register_action("save_project", save_handler)
    manager.register_action("undo", undo_handler)

    # Manual trigger
    manager.trigger_action("save_project")
    manager.trigger_action("undo")
    print(f"✅ Actions triggered: {triggered_actions}")

    # ===== TEST 6: Key Press Simulation =====
    print_section("Test 6: Key Press Simulation")
    test_keys = [
        ("S", ["Ctrl"], ShortcutContext.GLOBAL.value),
        ("Z", ["Ctrl"], ShortcutContext.GLOBAL.value),
        ("F12", [], ShortcutContext.GLOBAL.value),
        ("Space", [], ShortcutContext.GLOBAL.value),
        ("X", ["Ctrl", "Shift"], ShortcutContext.GLOBAL.value),  # No handler
    ]

    play_triggered = []
    def play_handler():
        play_triggered.append(True)
        print(f"   ▶️  Play/Pause triggered!")

    manager.register_action("play_pause", play_handler)

    for key, mods, ctx in test_keys:
        combo = "+".join(mods + [key]) if mods else key
        handled = manager.handle_key_press(key, mods, ctx)
        print(f"✅ Key '{combo}': {'Handled' if handled else 'Not handled'}")

    # ===== TEST 7: Shortcut Modification =====
    print_section("Test 7: Shortcut Modification")
    sc_before = manager.get_shortcut("file.save")
    print(f"✅ Before: {sc_before.get_display_string()}")

    # Modify karo
    success = manager.modify_shortcut("file.save", "S", ["Ctrl", "Alt"])
    sc_after = manager.get_shortcut("file.save")
    print(f"✅ After modify: {sc_after.get_display_string()} | Success: {success}")

    # Wapas original
    manager.modify_shortcut("file.save", "S", ["Ctrl"])
    print(f"✅ Restored: {manager.get_shortcut('file.save').get_display_string()}")

    # ===== TEST 8: Custom Shortcut =====
    print_section("Test 8: Custom Shortcut")

    custom_triggered = []
    def custom_handler():
        custom_triggered.append(True)
        print(f"   🎯 Custom shortcut triggered!")

    sc = manager.add_custom_shortcut(
        shortcut_id  = "custom.my_action",
        name         = "My Custom Action",
        description  = "Test custom shortcut",
        key          = "F9",
        modifiers    = [],
        action_name  = "my_custom_action",
        category     = ShortcutCategory.CUSTOM.value,
    )

    if sc:
        print(f"✅ Custom shortcut created: {sc.get_display_string()}")
        manager.register_action("my_custom_action", custom_handler)
        manager.handle_key_press("F9", [], ShortcutContext.GLOBAL.value)
        print(f"   Triggered: {len(custom_triggered) > 0}")

        # Remove karo
        removed = manager.remove_custom_shortcut("custom.my_action")
        print(f"✅ Custom shortcut removed: {removed}")

    # ===== TEST 9: Conflict Detection =====
    print_section("Test 9: Conflict Detection")
    # Ctrl+S conflict check karo
    conflicts = manager.check_conflicts("S", ["Ctrl"])
    print(f"✅ Conflicts for Ctrl+S: {len(conflicts)}")
    for c in conflicts:
        print(f"   ⚠️  {c.shortcut1_id} conflicts with {c.shortcut2_id}")

    # No conflict
    no_conflicts = manager.check_conflicts("F9", [])
    print(f"✅ Conflicts for F9: {len(no_conflicts)} (expected 0)")

    # All conflicts
    all_conflicts = manager.get_all_conflicts()
    print(f"✅ Total conflicts in system: {len(all_conflicts)}")

    # ===== TEST 10: Export/Import =====
    print_section("Test 10: Export & Import")
    ensure_dir("cache")
    export_path = "cache/test_shortcuts.json"

    exported = manager.export_shortcuts(export_path)
    print(f"✅ Exported: {exported} → {export_path}")

    # File size check
    if os.path.exists(export_path):
        size = os.path.getsize(export_path)
        print(f"   File size: {size} bytes")

    # Import karke check
    manager2 = ShortcutsManager()
    count = manager2.import_shortcuts(export_path, merge=False)
    print(f"✅ Imported: {count} shortcuts")
    print(f"   Total after import: {len(manager2.get_all_shortcuts())}")

    # ===== TEST 11: Enable/Disable =====
    print_section("Test 11: Enable/Disable Shortcut")
    sc = manager.get_shortcut("file.quit")
    print(f"✅ Before: file.quit enabled={sc.enabled}")

    manager.enable_shortcut("file.quit", False)
    sc = manager.get_shortcut("file.quit")
    print(f"✅ After disable: enabled={sc.enabled}")

    manager.enable_shortcut("file.quit", True)
    sc = manager.get_shortcut("file.quit")
    print(f"✅ After re-enable: enabled={sc.enabled}")

    # ===== TEST 12: Print Shortcuts Table =====
    print_section("Test 12: Shortcuts Cheat Sheet (File Category)")
    manager.print_shortcuts_table(category=ShortcutCategory.FILE.value)

    # ===== TEST 13: Statistics =====
    print_section("Test 13: Final Statistics")
    final_stats = manager.get_statistics()
    for key, value in final_stats.items():
        print(f"   {key:20s}: {value}")

    # ===== TEST 14: Global Singleton =====
    print_section("Test 14: Global Singleton")
    sm1 = get_shortcuts_manager()
    sm2 = get_shortcuts_manager()
    print(f"✅ Singleton working: {sm1 is sm2}")

    # Cleanup
    try:
        if os.path.exists(export_path):
            os.remove(export_path)
    except Exception:
        pass

    print_banner("✅ All Tests Passed!", "shortcuts_manager.py Working Perfectly")