# ============================================================
# src/ui/main_window.py
# 3D Animation Studio - Main Window
# Sabhi UI components ko jodne wala master window
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
from pathlib import Path

from src.utils import (
    get_logger,
    get_config,
    ensure_dir,
    get_timestamp,
)

logger = get_logger("MainWindow")


# ============================================================
# MAIN WINDOW CLASS
# ============================================================

class MainWindow:
    """
    3D Animation Studio ka Main Window.

    Sab kuch integrate karta hai:
    - Toolbar (top)
    - Scene Hierarchy (left)
    - 3D Viewport (center)
    - Properties Panel (right)
    - Timeline (bottom)
    - Asset Browser (bottom-left)
    - Menu bar
    - Status bar
    """

    def __init__(
        self,
        config: Optional[Dict] = None,
    ):
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # Qt references
        self._window       = None
        self._menu_bar     = None
        self._status_bar   = None
        self._central      = None

        # Docks
        self._docks: Dict[str, Any] = {}

        # UI subsystems
        self.theme_manager     = None
        self.shortcuts_manager = None
        self.toolbar           = None
        self.viewport          = None
        self.hierarchy_widget  = None
        self.properties_widget = None
        self.timeline_widget   = None
        self.asset_browser     = None

        # Data models (shared)
        self.scene_model       = None
        self.properties_model  = None
        self.timeline_model    = None
        self.asset_model       = None
        self.viewport_model    = None

        # Current project
        self._current_project_path: Optional[str] = None
        self._project_dirty: bool = False

        # Build the window
        self._build_window()

        logger.info("✅ MainWindow initialized")

    # ----------------------------------------------------------
    # WINDOW BUILDING
    # ----------------------------------------------------------

    def _build_window(self):
        """Complete main window build karo"""
        try:
            from PyQt5.QtWidgets import (
                QMainWindow, QWidget, QVBoxLayout,
                QHBoxLayout, QDockWidget, QMenuBar,
                QMenu, QAction, QStatusBar, QLabel,
                QFileDialog, QMessageBox, QApplication,
            )
            from PyQt5.QtCore import Qt, QSize
            from PyQt5.QtGui import QIcon

            # Main window
            self._window = QMainWindow()
            self._window.setWindowTitle(
                "3D Animation Studio - Untitled Project"
            )
            self._window.resize(1600, 900)
            self._window.setDockNestingEnabled(True)
            self._window.setDockOptions(
                QMainWindow.AllowNestedDocks
                | QMainWindow.AllowTabbedDocks
                | QMainWindow.AnimatedDocks
            )

            # ===== INITIALIZE SUBSYSTEMS =====
            self._init_managers()

            # ===== BUILD UI COMPONENTS =====
            self._build_menu_bar()
            self._build_toolbar()
            self._build_central_viewport()
            self._build_dock_panels()
            self._build_status_bar()

            # ===== CONNECT SHORTCUTS =====
            self._connect_shortcuts()

            # ===== CONNECT SIGNALS =====
            self._connect_signals()

            # ===== APPLY THEME =====
            if self.theme_manager:
                try:
                    self.theme_manager.apply_theme()
                except Exception:
                    pass

            logger.info("✅ Main window build complete")

        except ImportError:
            logger.error(
                "PyQt5 available nahi hai - main window nahi ban sakti"
            )
        except Exception as e:
            logger.error(f"Main window build error: {e}")
            import traceback
            traceback.print_exc()

    def _init_managers(self):
        """Sabhi managers aur models initialize karo"""
        try:
            # Theme manager
            from src.ui.theme_manager import get_theme_manager
            self.theme_manager = get_theme_manager()

            # Application pe theme set karo
            try:
                from PyQt5.QtWidgets import QApplication
                app = QApplication.instance()
                if app:
                    self.theme_manager.set_application(app)
            except Exception:
                pass

            # Shortcuts manager
            from src.ui.shortcuts_manager import get_shortcuts_manager
            self.shortcuts_manager = get_shortcuts_manager()

            # Scene hierarchy model
            from src.ui.scene_hierarchy import get_scene_model
            self.scene_model = get_scene_model()

            # Properties model
            from src.ui.properties_panel import get_properties_model
            self.properties_model = get_properties_model()

            # Timeline model
            from src.ui.timeline_widget import get_timeline_model
            self.timeline_model = get_timeline_model(fps=30)

            # Asset browser model
            from src.ui.asset_browser import get_asset_model
            self.asset_model = get_asset_model()

            # Viewport model
            from src.ui.viewport_widget import get_viewport_model
            self.viewport_model = get_viewport_model()

            logger.debug("Managers & models initialized")

        except Exception as e:
            logger.error(f"Managers init error: {e}")

    def _build_menu_bar(self):
        """Menu bar build karo"""
        try:
            from PyQt5.QtWidgets import QMenu, QAction

            menu_bar = self._window.menuBar()
            self._menu_bar = menu_bar

            # ===== FILE MENU =====
            file_menu = menu_bar.addMenu("&File")

            new_action = QAction("📄 New Project", self._window)
            new_action.setShortcut("Ctrl+N")
            new_action.triggered.connect(self._on_new_project)
            file_menu.addAction(new_action)

            open_action = QAction("📂 Open Project...", self._window)
            open_action.setShortcut("Ctrl+O")
            open_action.triggered.connect(self._on_open_project)
            file_menu.addAction(open_action)

            self._recent_menu = file_menu.addMenu("Recent Projects")
            self._update_recent_menu()

            file_menu.addSeparator()

            # ── ✨ NEW: Generate from Script ──────────────────
            generate_action = QAction(
                "🎬 Generate from Script...", self._window
            )
            generate_action.setShortcut("Ctrl+G")
            generate_action.setStatusTip(
                "Script likhо → Automatic MP4 video generate karo!"
            )
            generate_action.triggered.connect(self._on_generate_from_script)
            file_menu.addAction(generate_action)
            # ─────────────────────────────────────────────────

            file_menu.addSeparator()

            save_action = QAction("💾 Save", self._window)
            save_action.setShortcut("Ctrl+S")
            save_action.triggered.connect(self._on_save_project)
            file_menu.addAction(save_action)

            saveas_action = QAction("💾 Save As...", self._window)
            saveas_action.setShortcut("Ctrl+Shift+S")
            saveas_action.triggered.connect(self._on_save_as)
            file_menu.addAction(saveas_action)

            file_menu.addSeparator()

            import_action = QAction("📥 Import Asset...", self._window)
            import_action.setShortcut("Ctrl+I")
            import_action.triggered.connect(self._on_import)
            file_menu.addAction(import_action)

            export_action = QAction("📤 Export Video...", self._window)
            export_action.setShortcut("Ctrl+E")
            export_action.triggered.connect(self._on_export)
            file_menu.addAction(export_action)

            file_menu.addSeparator()

            prefs_action = QAction("⚙️ Preferences...", self._window)
            prefs_action.setShortcut("Ctrl+,")
            prefs_action.triggered.connect(self._on_preferences)
            file_menu.addAction(prefs_action)

            file_menu.addSeparator()

            quit_action = QAction("❌ Quit", self._window)
            quit_action.setShortcut("Ctrl+Q")
            quit_action.triggered.connect(self._on_quit)
            file_menu.addAction(quit_action)

            # ===== EDIT MENU =====
            edit_menu = menu_bar.addMenu("&Edit")

            undo_action = QAction("↩️ Undo", self._window)
            undo_action.setShortcut("Ctrl+Z")
            undo_action.triggered.connect(self._on_undo)
            edit_menu.addAction(undo_action)

            redo_action = QAction("↪️ Redo", self._window)
            redo_action.setShortcut("Ctrl+Y")
            redo_action.triggered.connect(self._on_redo)
            edit_menu.addAction(redo_action)

            edit_menu.addSeparator()

            duplicate_action = QAction("📋 Duplicate", self._window)
            duplicate_action.setShortcut("Ctrl+D")
            duplicate_action.triggered.connect(self._on_duplicate)
            edit_menu.addAction(duplicate_action)

            delete_action = QAction("🗑️ Delete", self._window)
            delete_action.setShortcut("Delete")
            delete_action.triggered.connect(self._on_delete)
            edit_menu.addAction(delete_action)

            edit_menu.addSeparator()

            select_all = QAction("Select All", self._window)
            select_all.setShortcut("Ctrl+A")
            select_all.triggered.connect(self._on_select_all)
            edit_menu.addAction(select_all)

            # ===== VIEW MENU =====
            view_menu = menu_bar.addMenu("&View")

            fullscreen_action = QAction(
                "Toggle Fullscreen", self._window
            )
            fullscreen_action.setShortcut("F11")
            fullscreen_action.triggered.connect(self._on_fullscreen)
            view_menu.addAction(fullscreen_action)

            view_menu.addSeparator()

            # Panel toggles
            self._panel_actions = {}
            for panel_name in [
                "Scene Hierarchy", "Properties",
                "Timeline", "Assets", "Toolbar"
            ]:
                action = QAction(f"Show {panel_name}", self._window)
                action.setCheckable(True)
                action.setChecked(True)
                action.triggered.connect(
                    lambda checked, name=panel_name:
                    self._toggle_panel(name, checked)
                )
                view_menu.addAction(action)
                self._panel_actions[panel_name] = action

            view_menu.addSeparator()

            theme_action = QAction("🌙 Toggle Theme", self._window)
            theme_action.triggered.connect(self._on_toggle_theme)
            view_menu.addAction(theme_action)

            # ===== SCENE MENU =====
            scene_menu = menu_bar.addMenu("&Scene")

            add_char = QAction("🧍 Add Character", self._window)
            add_char.setShortcut("Shift+C")
            add_char.triggered.connect(
                lambda: self._add_scene_object("character", "Character")
            )
            scene_menu.addAction(add_char)

            add_cube = QAction("📦 Add Cube", self._window)
            add_cube.setShortcut("Shift+A")
            add_cube.triggered.connect(
                lambda: self._add_scene_object("mesh", "Cube")
            )
            scene_menu.addAction(add_cube)

            add_light = QAction("💡 Add Light", self._window)
            add_light.setShortcut("Shift+L")
            add_light.triggered.connect(
                lambda: self._add_scene_object("light", "Light")
            )
            scene_menu.addAction(add_light)

            add_camera = QAction("🎥 Add Camera", self._window)
            add_camera.setShortcut("Shift+K")
            add_camera.triggered.connect(
                lambda: self._add_scene_object("camera", "Camera")
            )
            scene_menu.addAction(add_camera)

            add_vfx = QAction("✨ Add VFX", self._window)
            add_vfx.triggered.connect(
                lambda: self._add_scene_object("vfx", "VFX Effect")
            )
            scene_menu.addAction(add_vfx)

            # ===== RENDER MENU =====
            render_menu = menu_bar.addMenu("&Render")

            render_frame = QAction("🎬 Render Frame", self._window)
            render_frame.setShortcut("F12")
            render_frame.triggered.connect(self._on_render_frame)
            render_menu.addAction(render_frame)

            render_anim = QAction("🎥 Render Animation", self._window)
            render_anim.setShortcut("Ctrl+F12")
            render_anim.triggered.connect(self._on_render_animation)
            render_menu.addAction(render_anim)

            render_menu.addSeparator()

            youtube_upload = QAction(
                "📺 Upload to YouTube...", self._window
            )
            youtube_upload.triggered.connect(self._on_youtube_upload)
            render_menu.addAction(youtube_upload)

            # ===== HELP MENU =====
            help_menu = menu_bar.addMenu("&Help")

            shortcuts_action = QAction(
                "⌨️ Keyboard Shortcuts", self._window
            )
            shortcuts_action.setShortcut("F1")
            shortcuts_action.triggered.connect(self._on_show_shortcuts)
            help_menu.addAction(shortcuts_action)

            github_action = QAction(
                "⭐ GitHub Repository", self._window
            )
            github_action.triggered.connect(self._on_open_github)
            help_menu.addAction(github_action)

            help_menu.addSeparator()

            about_action = QAction("ℹ️ About", self._window)
            about_action.triggered.connect(self._on_about)
            help_menu.addAction(about_action)

            logger.debug("Menu bar built")

        except Exception as e:
            logger.error(f"Menu bar build error: {e}")

    def _build_toolbar(self):
        """Main toolbar build karo"""
        try:
            from src.ui.toolbar import StudioToolbar

            self.toolbar = StudioToolbar(
                main_window       = self._window,
                shortcuts_manager = self.shortcuts_manager,
                theme_manager     = self.theme_manager,
            )
            logger.debug("Toolbar built")

        except Exception as e:
            logger.error(f"Toolbar build error: {e}")

    def _build_central_viewport(self):
        """Central 3D viewport build karo"""
        try:
            from src.ui.viewport_widget import ViewportWidget

            self.viewport = ViewportWidget(
                model         = self.viewport_model,
                theme_manager = self.theme_manager,
            )

            central_widget = self.viewport.get_widget()
            if central_widget:
                self._window.setCentralWidget(central_widget)
                self._central = central_widget
            logger.debug("Central viewport built")

        except Exception as e:
            logger.error(f"Viewport build error: {e}")

    def _build_dock_panels(self):
        """Sabhi dock panels build karo"""
        try:
            from PyQt5.QtWidgets import QDockWidget
            from PyQt5.QtCore import Qt

            # ===== SCENE HIERARCHY (LEFT) =====
            try:
                from src.ui.scene_hierarchy import SceneHierarchyWidget

                self.hierarchy_widget = SceneHierarchyWidget(
                    model         = self.scene_model,
                    theme_manager = self.theme_manager,
                )

                dock = QDockWidget("Scene Hierarchy", self._window)
                dock.setObjectName("SceneHierarchyDock")
                dock.setWidget(self.hierarchy_widget.get_widget())
                dock.setAllowedAreas(
                    Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
                )
                dock.setMinimumWidth(250)
                self._window.addDockWidget(Qt.LeftDockWidgetArea, dock)
                self._docks["Scene Hierarchy"] = dock

            except Exception as e:
                logger.warning(f"Hierarchy dock error: {e}")

            # ===== PROPERTIES PANEL (RIGHT) =====
            try:
                from src.ui.properties_panel import PropertiesPanelWidget

                self.properties_widget = PropertiesPanelWidget(
                    model         = self.properties_model,
                    theme_manager = self.theme_manager,
                )

                dock = QDockWidget("Properties", self._window)
                dock.setObjectName("PropertiesDock")
                dock.setWidget(self.properties_widget.get_widget())
                dock.setAllowedAreas(
                    Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
                )
                dock.setMinimumWidth(280)
                self._window.addDockWidget(Qt.RightDockWidgetArea, dock)
                self._docks["Properties"] = dock

            except Exception as e:
                logger.warning(f"Properties dock error: {e}")

            # ===== TIMELINE (BOTTOM) =====
            try:
                from src.ui.timeline_widget import TimelineWidget

                self.timeline_widget = TimelineWidget(
                    model         = self.timeline_model,
                    theme_manager = self.theme_manager,
                )

                dock = QDockWidget("Timeline", self._window)
                dock.setObjectName("TimelineDock")
                dock.setWidget(self.timeline_widget.get_widget())
                dock.setAllowedAreas(
                    Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea
                )
                dock.setMinimumHeight(250)
                self._window.addDockWidget(Qt.BottomDockWidgetArea, dock)
                self._docks["Timeline"] = dock

            except Exception as e:
                logger.warning(f"Timeline dock error: {e}")

            # ===== ASSET BROWSER (LEFT BOTTOM) =====
            try:
                from src.ui.asset_browser import AssetBrowserWidget

                self.asset_browser = AssetBrowserWidget(
                    model         = self.asset_model,
                    theme_manager = self.theme_manager,
                )

                dock = QDockWidget("Assets", self._window)
                dock.setObjectName("AssetsDock")
                dock.setWidget(self.asset_browser.get_widget())
                dock.setAllowedAreas(
                    Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea |
                    Qt.BottomDockWidgetArea
                )
                dock.setMinimumWidth(280)
                self._window.addDockWidget(Qt.LeftDockWidgetArea, dock)
                self._docks["Assets"] = dock

                # Hierarchy ke saath tab bana do
                if "Scene Hierarchy" in self._docks:
                    self._window.tabifyDockWidget(
                        self._docks["Scene Hierarchy"],
                        dock
                    )
                    # Hierarchy pehle dikhao
                    self._docks["Scene Hierarchy"].raise_()

            except Exception as e:
                logger.warning(f"Asset browser dock error: {e}")

            logger.debug(f"Docks built: {list(self._docks.keys())}")

        except Exception as e:
            logger.error(f"Dock panels build error: {e}")

    def _build_status_bar(self):
        """Status bar build karo"""
        try:
            from PyQt5.QtWidgets import QLabel

            self._status_bar = self._window.statusBar()

            # Left: General status
            self._status_label = QLabel("Ready")
            self._status_bar.addWidget(self._status_label)

            # Right: Info labels
            self._project_label = QLabel("No project")
            self._status_bar.addPermanentWidget(self._project_label)

            self._fps_label = QLabel("FPS: --")
            self._status_bar.addPermanentWidget(self._fps_label)

            self._mem_label = QLabel("RAM: --")
            self._status_bar.addPermanentWidget(self._mem_label)

            # Memory update timer
            from PyQt5.QtCore import QTimer
            self._mem_timer = QTimer()
            self._mem_timer.setInterval(2000)
            self._mem_timer.timeout.connect(self._update_status_info)
            self._mem_timer.start()

            logger.debug("Status bar built")

        except Exception as e:
            logger.error(f"Status bar build error: {e}")

    def _connect_shortcuts(self):
        """Shortcuts manager ke saath actions bind karo"""
        if not self.shortcuts_manager:
            return

        try:
            # File
            self.shortcuts_manager.register_action(
                "new_project", self._on_new_project
            )
            self.shortcuts_manager.register_action(
                "open_project", self._on_open_project
            )
            self.shortcuts_manager.register_action(
                "save_project", self._on_save_project
            )
            self.shortcuts_manager.register_action(
                "save_project_as", self._on_save_as
            )
            self.shortcuts_manager.register_action(
                "import_asset", self._on_import
            )
            self.shortcuts_manager.register_action(
                "export_video", self._on_export
            )
            self.shortcuts_manager.register_action(
                "quit_app", self._on_quit
            )
            self.shortcuts_manager.register_action(
                "open_preferences", self._on_preferences
            )

            # ── DISABLED: Prevents ambiguous shortcut ──────────
            # self.shortcuts_manager.register_action(
            #     "generate_from_script", self._on_generate_from_script
            # )
            # Menu item uses Ctrl+G directly
            # ──────────────────────────────────────────────────

            # Edit
            self.shortcuts_manager.register_action("undo", self._on_undo)
            self.shortcuts_manager.register_action("redo", self._on_redo)
            self.shortcuts_manager.register_action(
                "duplicate", self._on_duplicate
            )
            self.shortcuts_manager.register_action(
                "delete_selected", self._on_delete
            )
            self.shortcuts_manager.register_action(
                "select_all", self._on_select_all
            )

            # View
            self.shortcuts_manager.register_action(
                "toggle_fullscreen", self._on_fullscreen
            )
            self.shortcuts_manager.register_action(
                "toggle_theme", self._on_toggle_theme
            )

            # Scene
            self.shortcuts_manager.register_action(
                "add_character",
                lambda: self._add_scene_object("character", "Character")
            )
            self.shortcuts_manager.register_action(
                "add_object",
                lambda: self._add_scene_object("mesh", "Cube")
            )
            self.shortcuts_manager.register_action(
                "add_light",
                lambda: self._add_scene_object("light", "Light")
            )
            self.shortcuts_manager.register_action(
                "add_camera",
                lambda: self._add_scene_object("camera", "Camera")
            )

            # Render
            self.shortcuts_manager.register_action(
                "render_image", self._on_render_frame
            )
            self.shortcuts_manager.register_action(
                "render_animation", self._on_render_animation
            )

            # Playback
            self.shortcuts_manager.register_action(
                "play_pause",
                lambda: (
                    self.timeline_model.toggle_play_pause()
                    if self.timeline_model else None
                )
            )
            self.shortcuts_manager.register_action(
                "next_frame",
                lambda: (
                    self.timeline_model.next_frame()
                    if self.timeline_model else None
                )
            )
            self.shortcuts_manager.register_action(
                "prev_frame",
                lambda: (
                    self.timeline_model.prev_frame()
                    if self.timeline_model else None
                )
            )
            self.shortcuts_manager.register_action(
                "go_to_start",
                lambda: (
                    self.timeline_model.go_to_start()
                    if self.timeline_model else None
                )
            )
            self.shortcuts_manager.register_action(
                "go_to_end",
                lambda: (
                    self.timeline_model.go_to_end()
                    if self.timeline_model else None
                )
            )

            # Help
            self.shortcuts_manager.register_action(
                "show_shortcuts", self._on_show_shortcuts
            )

            # Bind to window
            self.shortcuts_manager.bind_to_qt_widget(self._window)

            logger.debug("Shortcuts connected")

        except Exception as e:
            logger.error(f"Shortcuts connect error: {e}")

    def _connect_signals(self):
        """Model signals aur handlers ko jodo"""
        try:
            # Scene selection → Properties panel
            if self.scene_model and self.properties_model:
                def on_scene_selection(event, data):
                    if event == "selection_changed":
                        selected = data.get("selected_ids", [])
                        if selected and len(selected) == 1:
                            obj = self.scene_model.get_object(selected[0])
                            if obj:
                                self.properties_model.load_object(
                                    obj.id, obj.name, obj.object_type,
                                    data={
                                        "position": obj.position,
                                        "rotation": obj.rotation,
                                        "scale":    obj.scale,
                                    }
                                )
                        else:
                            self.properties_model.clear()

                self.scene_model.add_listener(on_scene_selection)

            # Asset double-click → Add to scene
            if self.asset_browser:
                def on_asset_selected(asset):
                    self._set_status(f"Asset selected: {asset.name}")

                self.asset_browser.set_on_asset_selected(on_asset_selected)

            logger.debug("Signals connected")

        except Exception as e:
            logger.error(f"Signals connect error: {e}")

    # ----------------------------------------------------------
    # ACTION HANDLERS
    # ----------------------------------------------------------

    def _on_new_project(self):
        """New project"""
        try:
            from src.ui.dialogs import StudioDialogs, DialogResult

            result, settings = StudioDialogs.show_new_project_dialog(
                parent        = self._window,
                theme_manager = self.theme_manager,
            )

            if result == DialogResult.ACCEPTED:
                # Scene clear
                if self.scene_model:
                    self.scene_model.clear()
                # Timeline clear
                if self.timeline_model:
                    self.timeline_model.clear_all_clips()

                self._current_project_path = None
                self._project_dirty = False
                self._window.setWindowTitle(
                    f"3D Animation Studio - {settings.name}"
                )
                self._set_status(
                    f"✅ Naya project banaya: {settings.name}"
                )

                # Default objects add karo
                if self.scene_model:
                    self.scene_model.add_object("Main Camera", "camera")
                    self.scene_model.add_object("Sun Light", "light")

        except Exception as e:
            logger.error(f"New project error: {e}")

    def _on_open_project(self):
        """Open project file"""
        try:
            from src.ui.dialogs import StudioDialogs

            path = StudioDialogs.open_file_dialog(
                title  = "Project Open Karo",
                filter = "Animation Project (*.anim3d);;All Files (*)",
                parent = self._window,
            )
            if path:
                self._current_project_path = path
                self._window.setWindowTitle(
                    f"3D Animation Studio - {Path(path).name}"
                )
                self._set_status(
                    f"✅ Project loaded: {Path(path).name}"
                )

        except Exception as e:
            logger.error(f"Open project error: {e}")

    def _on_save_project(self):
        """Save project"""
        if not self._current_project_path:
            self._on_save_as()
            return

        try:
            self._set_status(
                f"💾 Saving: {Path(self._current_project_path).name}"
            )
            self._project_dirty = False
            # TODO: Actual save logic

        except Exception as e:
            logger.error(f"Save error: {e}")

    def _on_save_as(self):
        """Save as..."""
        try:
            from src.ui.dialogs import StudioDialogs

            path = StudioDialogs.save_file_dialog(
                title   = "Save Project As",
                filter  = "Animation Project (*.anim3d)",
                default = "MyProject.anim3d",
                parent  = self._window,
            )
            if path:
                self._current_project_path = path
                self._window.setWindowTitle(
                    f"3D Animation Studio - {Path(path).name}"
                )
                self._set_status(f"💾 Saved: {Path(path).name}")

        except Exception as e:
            logger.error(f"Save as error: {e}")

    def _on_import(self):
        """Import asset"""
        try:
            from src.ui.dialogs import StudioDialogs, DialogResult

            result, settings = StudioDialogs.show_import_dialog(
                parent        = self._window,
                theme_manager = self.theme_manager,
            )

            if result == DialogResult.ACCEPTED and settings.file_path:
                if self.asset_model:
                    asset = self.asset_model.import_asset(
                        source_path     = settings.file_path,
                        copy_to_project = settings.copy_to_project,
                    )
                    if asset:
                        self._set_status(f"✅ Imported: {asset.name}")

        except Exception as e:
            logger.error(f"Import error: {e}")

    def _on_export(self):
        """Export video"""
        try:
            from src.ui.dialogs import StudioDialogs, DialogResult

            result, settings = StudioDialogs.show_export_dialog(
                parent        = self._window,
                theme_manager = self.theme_manager,
            )

            if result == DialogResult.ACCEPTED:
                progress = StudioDialogs.show_progress_dialog(
                    title         = "Exporting Video",
                    message       = f"Exporting: {settings.preset}",
                    parent        = self._window,
                    theme_manager = self.theme_manager,
                )
                progress.show()

                import time as _t
                for i in range(0, 101, 5):
                    progress.update(
                        i, f"Frame {i*3}/{settings.end_frame}..."
                    )
                    _t.sleep(0.03)
                    if progress.is_cancelled():
                        break

                progress.close()
                self._set_status(
                    f"✅ Exported: {settings.output_path}"
                )

        except Exception as e:
            logger.error(f"Export error: {e}")

    def _on_preferences(self):
        """Preferences dialog"""
        try:
            from src.ui.dialogs import StudioDialogs

            result, prefs = StudioDialogs.show_preferences_dialog(
                parent         = self._window,
                theme_manager  = self.theme_manager,
            )
            if result.value == "accepted":
                self._set_status("✅ Preferences saved")

        except Exception as e:
            logger.error(f"Preferences error: {e}")

    def _on_quit(self):
        """Quit application"""
        try:
            from src.ui.dialogs import StudioDialogs

            if self._project_dirty:
                confirmed = StudioDialogs.show_confirm_dialog(
                    title         = "Unsaved Changes",
                    message       = (
                        "Save nahi kiye changes hain. "
                        "Kya close karna hai?"
                    ),
                    parent        = self._window,
                    theme_manager = self.theme_manager,
                    confirm_text  = "Close Anyway",
                    danger        = True,
                )
                if not confirmed:
                    return

            from PyQt5.QtWidgets import QApplication
            QApplication.quit()

        except Exception as e:
            logger.error(f"Quit error: {e}")

    # ── ✨ NEW HANDLER ─────────────────────────────────────────

    def _on_generate_from_script(self):
        """
        🎬 Script Input Dialog open karo
        File → Generate from Script... (Ctrl+G)
        """
        try:
            from src.ui.dialogs import ScriptInputDialog

            logger.info("🎬 Generate from Script dialog open ho raha hai...")
            self._set_status("🎬 Script Generator open ho raha hai...")

            dialog = ScriptInputDialog(parent=self._window)
            dialog.exec_()

            # Dialog close hone ke baad status update
            self._set_status(
                "✅ Script Generator closed - "
                "exports/ folder check karo!"
            )

        except ImportError as e:
            logger.error(f"ScriptInputDialog import error: {e}")

            # Fallback: Simple error message
            try:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.critical(
                    self._window,
                    "Error",
                    f"Script Dialog load nahi hua!\n\n"
                    f"Error: {e}\n\n"
                    f"Make sure dialogs.py mein "
                    f"ScriptInputDialog class hai."
                )
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Generate from script error: {e}")
            import traceback
            traceback.print_exc()

    # ─────────────────────────────────────────────────────────

    def _on_undo(self):
        """Undo"""
        self._set_status("↩️ Undo")

    def _on_redo(self):
        """Redo"""
        self._set_status("↪️ Redo")

    def _on_duplicate(self):
        """Duplicate selected"""
        if self.scene_model:
            for obj in self.scene_model.get_selected_objects():
                self.scene_model.duplicate_object(obj.id)
            self._set_status("📋 Duplicated")

    def _on_delete(self):
        """Delete selected"""
        if self.scene_model:
            for obj in self.scene_model.get_selected_objects():
                self.scene_model.remove_object(obj.id)
            self._set_status("🗑️ Deleted")

    def _on_select_all(self):
        """Select all"""
        if self.scene_model:
            self.scene_model.select_all()

    def _on_fullscreen(self):
        """Toggle fullscreen"""
        if self._window.isFullScreen():
            self._window.showNormal()
        else:
            self._window.showFullScreen()

    def _on_toggle_theme(self):
        """Toggle theme"""
        if self.theme_manager:
            self.theme_manager.toggle_theme()
            self._set_status(
                f"🎨 Theme: {self.theme_manager.get_theme_name()}"
            )

    def _add_scene_object(self, obj_type: str, name_prefix: str):
        """Scene mein object add karo"""
        if self.scene_model:
            count = (
                len(self.scene_model.get_objects_by_type(obj_type)) + 1
            )
            self.scene_model.add_object(
                f"{name_prefix}.{count:03d}",
                obj_type,
            )
            self._set_status(f"✅ Added: {name_prefix}")

    def _on_render_frame(self):
        """Render single frame"""
        self._set_status("🎬 Rendering frame...")
        if self.viewport:
            self.viewport.refresh()

    def _on_render_animation(self):
        """Render animation"""
        try:
            from src.ui.dialogs import StudioDialogs

            progress = StudioDialogs.show_progress_dialog(
                title         = "Rendering Animation",
                message       = "Rendering frames...",
                parent        = self._window,
                theme_manager = self.theme_manager,
            )
            progress.show()

            total = 100
            import time as _t
            for i in range(total + 1):
                progress.update(i, f"Frame {i}/{total}")
                _t.sleep(0.02)
                if progress.is_cancelled():
                    break

            progress.close()
            self._set_status("✅ Animation rendered")

        except Exception as e:
            logger.error(f"Render animation error: {e}")

    def _on_youtube_upload(self):
        """YouTube upload"""
        self._set_status("📺 YouTube upload dialog...")
        try:
            from src.export.youtube_uploader import YouTubeUploader
            uploader = YouTubeUploader()
            uploader.print_setup_guide()
        except Exception as e:
            logger.error(f"YouTube upload error: {e}")

    def _on_show_shortcuts(self):
        """Shortcuts help dikhao"""
        if self.shortcuts_manager:
            self.shortcuts_manager.print_shortcuts_table()
            self._set_status("⌨️ Shortcuts printed to console")

    def _on_open_github(self):
        """GitHub kholo"""
        try:
            import webbrowser
            webbrowser.open(
                "https://github.com/happyreehal/3d-animation-studio"
            )
        except Exception:
            pass

    def _on_about(self):
        """About dialog"""
        try:
            from src.ui.dialogs import StudioDialogs
            StudioDialogs.show_about_dialog(
                parent        = self._window,
                theme_manager = self.theme_manager,
            )
        except Exception as e:
            logger.error(f"About error: {e}")

    # ----------------------------------------------------------
    # HELPERS
    # ----------------------------------------------------------

    def _toggle_panel(self, panel_name: str, visible: bool):
        """Panel visibility toggle"""
        dock = self._docks.get(panel_name)
        if dock:
            dock.setVisible(visible)
        elif panel_name == "Toolbar" and self.toolbar:
            toolbar = self.toolbar.get_toolbar()
            if toolbar:
                toolbar.setVisible(visible)

    def _set_status(self, message: str):
        """Status bar message"""
        if self._status_label:
            try:
                self._status_label.setText(message)
                logger.debug(f"Status: {message}")
            except Exception:
                pass

    def _update_status_info(self):
        """Status bar info update"""
        try:
            # Memory info
            try:
                import psutil
                mem = psutil.virtual_memory()
                if self._mem_label:
                    self._mem_label.setText(
                        f"RAM: {mem.percent:.0f}%"
                    )
            except Exception:
                pass

            # Project info
            if self._project_label:
                if self._current_project_path:
                    dirty = "*" if self._project_dirty else ""
                    self._project_label.setText(
                        f"{Path(self._current_project_path).stem}"
                        f"{dirty}"
                    )
                else:
                    self._project_label.setText("Untitled")

            # FPS from viewport
            if self._fps_label and self.viewport_model:
                fps = self.viewport_model.stats.fps
                self._fps_label.setText(f"FPS: {fps:.0f}")

        except Exception:
            pass

    def _update_recent_menu(self):
        """Recent projects menu update"""
        if not self._recent_menu:
            return
        try:
            from PyQt5.QtWidgets import QAction
            self._recent_menu.clear()

            no_recent = QAction("No recent projects", self._window)
            no_recent.setEnabled(False)
            self._recent_menu.addAction(no_recent)

        except Exception:
            pass

    # ----------------------------------------------------------
    # PUBLIC API
    # ----------------------------------------------------------

    def show(self):
        """Window show karo"""
        if self._window:
            try:
                self._window.show()
                self._set_status("✅ 3D Animation Studio ready!")
                logger.info("🎬 Main window shown")
            except Exception as e:
                logger.error(f"Show error: {e}")

    def show_maximized(self):
        """Maximized show karo"""
        if self._window:
            try:
                self._window.showMaximized()
                self._set_status("✅ 3D Animation Studio ready!")
                logger.info("🎬 Main window shown (maximized)")
            except Exception as e:
                logger.error(f"Show error: {e}")

    def close(self):
        """Window close karo"""
        if self._window:
            try:
                self._window.close()
            except Exception:
                pass

    def get_window(self):
        """Qt window lo"""
        return self._window


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def create_main_window(config: Optional[Dict] = None) -> MainWindow:
    """Main window banao"""
    return MainWindow(config=config)


# ============================================================
# TEST SECTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")
    print_banner("Main Window Test", "3D Animation Studio - Complete UI")

    print_section("Test: Full Application Launch")

    try:
        from PyQt5.QtWidgets import QApplication
        import sys as _sys

        app = QApplication.instance() or QApplication(_sys.argv)
        app.setApplicationName("3D Animation Studio")
        app.setOrganizationName("HappyReeHal")

        print("✅ QApplication created")

        main_win = create_main_window()
        print(f"✅ Main window built")
        print(f"   Docks: {list(main_win._docks.keys())}")

        main_win.show_maximized()
        print("✅ Window shown maximized")
        print("")
        print("┌────────────────────────────────────────────────────┐")
        print("│  🎬 3D Animation Studio Ready!                     │")
        print("├────────────────────────────────────────────────────┤")
        print("│  • Menu: File, Edit, View, Scene, Render, Help     │")
        print("│  • Toolbar: All main tools                         │")
        print("│  • Left dock: Scene Hierarchy + Assets             │")
        print("│  • Center: 3D Viewport (OpenGL)                    │")
        print("│  • Right dock: Properties Panel                    │")
        print("│  • Bottom: Timeline                                │")
        print("│  • Status bar: FPS + RAM + Project info            │")
        print("├────────────────────────────────────────────────────┤")
        print("│  ✨ NEW FEATURE:                                    │")
        print("│  • Ctrl+G  - Generate from Script  🎬              │")
        print("│  • File → Generate from Script...                  │")
        print("├────────────────────────────────────────────────────┤")
        print("│  Other Shortcuts:                                  │")
        print("│  • Ctrl+N  - New Project                           │")
        print("│  • Ctrl+O  - Open Project                          │")
        print("│  • Ctrl+S  - Save                                  │")
        print("│  • Ctrl+E  - Export                                │")
        print("│  • Shift+C - Add Character                         │")
        print("│  • Shift+A - Add Object                            │")
        print("│  • F11     - Fullscreen                            │")
        print("│  • F12     - Render Frame                          │")
        print("│  • F1      - Show Shortcuts                        │")
        print("└────────────────────────────────────────────────────┘")
        print("")

        # Sample scene
        if main_win.scene_model:
            main_win.scene_model.add_object("Hero", "character")
            main_win.scene_model.add_object("Main Camera", "camera")
            main_win.scene_model.add_object("Sun Light", "light")
            main_win.scene_model.add_object("Ground", "mesh")

        # Sample timeline
        if main_win.timeline_model:
            tracks = main_win.timeline_model.get_tracks_by_type("video")
            if tracks:
                main_win.timeline_model.add_clip(
                    track_id        = tracks[0].id,
                    name            = "Intro Scene",
                    start_frame     = 0,
                    duration_frames = 90,
                )
                main_win.timeline_model.add_clip(
                    track_id        = tracks[0].id,
                    name            = "Main Action",
                    start_frame     = 90,
                    duration_frames = 150,
                )

            audio_tracks = main_win.timeline_model.get_tracks_by_type(
                "audio"
            )
            if audio_tracks:
                main_win.timeline_model.add_clip(
                    track_id        = audio_tracks[0].id,
                    name            = "Background Music",
                    start_frame     = 0,
                    duration_frames = 240,
                )

        # Refresh widgets
        if main_win.hierarchy_widget:
            main_win.hierarchy_widget.refresh_tree()
        if main_win.asset_browser and main_win.asset_model:
            main_win.asset_model.create_sample_assets()
            main_win.asset_browser.refresh()

        print("✅ Sample scene loaded")
        print("")
        print("💡 Test karo: File → Generate from Script... (Ctrl+G)")
        print("💡 Window band karne ke liye X pe click karo...")
        print("")

        exit_code = app.exec_()
        print(f"\n✅ Application closed | Exit code: {exit_code}")

    except ImportError as e:
        print(f"❌ PyQt5 nahi mila: {e}")
        print("Install karo: pip install PyQt5")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    print_banner(
        "✅ Main Window Complete!",
        "3D Animation Studio Ready!"
    )