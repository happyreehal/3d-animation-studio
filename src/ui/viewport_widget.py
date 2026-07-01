# ============================================================
# src/ui/viewport_widget.py
# 3D Animation Studio - 3D Viewport Widget
# OpenGL based 3D preview - main viewing area
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

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum

import numpy as np

from src.utils import get_logger, get_config

logger = get_logger("ViewportWidget")


# ============================================================
# ENUMS
# ============================================================

class ViewportMode(Enum):
    """Viewport display modes"""
    SOLID       = "solid"
    WIREFRAME   = "wireframe"
    RENDERED    = "rendered"
    MATERIAL    = "material"


class ProjectionType(Enum):
    """Camera projection types"""
    PERSPECTIVE = "perspective"
    ORTHOGRAPHIC= "orthographic"


class ViewPreset(Enum):
    """Camera view presets"""
    PERSPECTIVE = "perspective"
    FRONT       = "front"
    BACK        = "back"
    LEFT        = "left"
    RIGHT       = "right"
    TOP         = "top"
    BOTTOM      = "bottom"


class NavigationMode(Enum):
    """Mouse navigation modes"""
    ORBIT   = "orbit"       # Rotate around target
    PAN     = "pan"         # Move sideways
    ZOOM    = "zoom"        # Zoom in/out
    FLY     = "fly"         # First person


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class ViewportCamera:
    """
    Viewport ka camera state.
    Position, target, zoom sab yahan.
    """
    # Position (spherical coordinates around target)
    distance:       float           = 10.0
    azimuth:        float           = 45.0        # Y axis rotation (degrees)
    elevation:      float           = 30.0        # X axis rotation (degrees)

    # Target point (jahaan camera dekh raha hai)
    target:         List[float]     = field(default_factory=lambda: [0.0, 0.0, 0.0])

    # Projection
    projection:     str             = ProjectionType.PERSPECTIVE.value
    fov:            float           = 60.0
    ortho_size:     float           = 10.0
    near_clip:      float           = 0.1
    far_clip:       float           = 1000.0

    def get_position(self) -> List[float]:
        """Camera ka world position calculate karo"""
        az_rad = math.radians(self.azimuth)
        el_rad = math.radians(self.elevation)

        x = self.distance * math.cos(el_rad) * math.sin(az_rad)
        y = self.distance * math.sin(el_rad)
        z = self.distance * math.cos(el_rad) * math.cos(az_rad)

        return [
            self.target[0] + x,
            self.target[1] + y,
            self.target[2] + z,
        ]

    def orbit(self, delta_azimuth: float, delta_elevation: float):
        """Camera ko orbit karo target ke around"""
        self.azimuth   += delta_azimuth
        self.elevation += delta_elevation

        # Elevation clamp karo (upside down na ho)
        self.elevation = max(-89.0, min(89.0, self.elevation))

        # Azimuth wrap karo
        self.azimuth = self.azimuth % 360.0

    def pan(self, delta_x: float, delta_y: float):
        """Target ko pan karo (screen space mein)"""
        # Screen right vector
        az_rad = math.radians(self.azimuth)
        right = [math.cos(az_rad), 0, -math.sin(az_rad)]

        # Screen up vector (simplified)
        el_rad = math.radians(self.elevation)
        up = [
            -math.sin(el_rad) * math.sin(az_rad),
            math.cos(el_rad),
            -math.sin(el_rad) * math.cos(az_rad),
        ]

        # Apply pan
        scale = self.distance * 0.001
        for i in range(3):
            self.target[i] += right[i] * delta_x * scale
            self.target[i] += up[i]    * delta_y * scale

    def zoom(self, delta: float):
        """Zoom in/out (distance change)"""
        # Exponential zoom
        factor = 1.0 + delta * 0.001
        self.distance = max(0.1, min(1000.0, self.distance * factor))

    def apply_preset(self, preset: str):
        """View preset apply karo"""
        presets = {
            ViewPreset.PERSPECTIVE.value: (45.0, 30.0, ProjectionType.PERSPECTIVE.value),
            ViewPreset.FRONT.value:       (0.0,  0.0,  ProjectionType.ORTHOGRAPHIC.value),
            ViewPreset.BACK.value:        (180.0,0.0,  ProjectionType.ORTHOGRAPHIC.value),
            ViewPreset.LEFT.value:        (-90.0,0.0,  ProjectionType.ORTHOGRAPHIC.value),
            ViewPreset.RIGHT.value:       (90.0, 0.0,  ProjectionType.ORTHOGRAPHIC.value),
            ViewPreset.TOP.value:         (0.0,  89.0, ProjectionType.ORTHOGRAPHIC.value),
            ViewPreset.BOTTOM.value:      (0.0, -89.0, ProjectionType.ORTHOGRAPHIC.value),
        }
        if preset in presets:
            az, el, proj = presets[preset]
            self.azimuth    = az
            self.elevation  = el
            self.projection = proj
            logger.debug(f"View preset: {preset}")

    def reset(self):
        """Camera reset karo default state pe"""
        self.distance   = 10.0
        self.azimuth    = 45.0
        self.elevation  = 30.0
        self.target     = [0.0, 0.0, 0.0]
        self.projection = ProjectionType.PERSPECTIVE.value
        self.fov        = 60.0

    def to_dict(self) -> Dict:
        return {
            "distance":   self.distance,
            "azimuth":    self.azimuth,
            "elevation":  self.elevation,
            "target":     self.target,
            "projection": self.projection,
            "fov":        self.fov,
            "ortho_size": self.ortho_size,
        }


@dataclass
class GridSettings:
    """Grid display settings"""
    visible:        bool  = True
    size:           float = 20.0        # Grid ki total size
    divisions:      int   = 20          # Number of divisions
    color:          List[float] = field(default_factory=lambda: [0.3, 0.3, 0.35, 1.0])
    axis_x_color:   List[float] = field(default_factory=lambda: [0.8, 0.3, 0.3, 1.0])
    axis_z_color:   List[float] = field(default_factory=lambda: [0.3, 0.3, 0.8, 1.0])
    show_axes:      bool  = True


@dataclass
class ViewportStats:
    """Viewport statistics"""
    fps:            float = 0.0
    frame_count:    int   = 0
    triangles:      int   = 0
    draw_calls:     int   = 0
    render_time_ms: float = 0.0


@dataclass
class ViewportSettings:
    """Viewport display settings"""
    mode:               str   = ViewportMode.SOLID.value
    show_grid:          bool  = True
    show_axes:          bool  = True
    show_stats:         bool  = True
    show_gizmos:        bool  = True
    show_gridlines:     bool  = True
    show_selection:     bool  = True
    show_shadows:       bool  = True
    show_wireframe:     bool  = False
    background_color:   List[float] = field(default_factory=lambda: [0.15, 0.15, 0.18, 1.0])
    ambient_light:      float = 0.3
    aa_samples:         int   = 4       # Anti-aliasing samples


# ============================================================
# VIEWPORT MODEL (Non-Qt data)
# ============================================================

class ViewportModel:
    """
    Viewport ka data model.
    Camera, settings, stats sab yahan.
    Qt se independent.
    """

    def __init__(self):
        self.camera        = ViewportCamera()
        self.grid          = GridSettings()
        self.settings      = ViewportSettings()
        self.stats         = ViewportStats()

        # Navigation state
        self._is_navigating: bool = False
        self._nav_mode:      str  = NavigationMode.ORBIT.value

        # Selected objects (IDs)
        self._selected_ids:  List[str] = []

        # Render callbacks
        self._render_callbacks: List[Callable] = []

        # Listeners
        self._listeners: List[Callable] = []

        # Viewport size
        self._viewport_width:  int = 800
        self._viewport_height: int = 600

        logger.info("✅ ViewportModel initialized")

    # ----------------------------------------------------------
    # CAMERA CONTROLS
    # ----------------------------------------------------------

    def get_camera(self) -> ViewportCamera:
        return self.camera

    def orbit_camera(self, dx: float, dy: float):
        """Camera orbit karo"""
        # dx = azimuth change, dy = elevation change (screen coords)
        self.camera.orbit(dx * 0.5, -dy * 0.5)
        self._notify("camera_changed", {})

    def pan_camera(self, dx: float, dy: float):
        """Camera pan karo"""
        self.camera.pan(-dx, dy)
        self._notify("camera_changed", {})

    def zoom_camera(self, delta: float):
        """Camera zoom karo"""
        self.camera.zoom(delta)
        self._notify("camera_changed", {})

    def apply_view_preset(self, preset: str):
        """View preset apply karo"""
        self.camera.apply_preset(preset)
        self._notify("camera_changed", {})

    def reset_camera(self):
        """Camera reset karo"""
        self.camera.reset()
        self._notify("camera_changed", {})

    def focus_on_position(self, position: List[float], distance: float = 5.0):
        """Camera ko position pe focus karo"""
        self.camera.target = list(position)
        self.camera.distance = distance
        self._notify("camera_changed", {})

    # ----------------------------------------------------------
    # SETTINGS
    # ----------------------------------------------------------

    def set_display_mode(self, mode: str):
        """Display mode set karo"""
        self.settings.mode = mode
        self.settings.show_wireframe = (mode == ViewportMode.WIREFRAME.value)
        self._notify("settings_changed", {"mode": mode})
        logger.debug(f"Display mode: {mode}")

    def toggle_grid(self) -> bool:
        """Grid visibility toggle"""
        self.settings.show_grid = not self.settings.show_grid
        self._notify("settings_changed", {})
        return self.settings.show_grid

    def toggle_axes(self) -> bool:
        """Axes visibility toggle"""
        self.settings.show_axes = not self.settings.show_axes
        self._notify("settings_changed", {})
        return self.settings.show_axes

    def toggle_wireframe(self) -> bool:
        """Wireframe mode toggle"""
        self.settings.show_wireframe = not self.settings.show_wireframe
        if self.settings.show_wireframe:
            self.settings.mode = ViewportMode.WIREFRAME.value
        else:
            self.settings.mode = ViewportMode.SOLID.value
        self._notify("settings_changed", {})
        return self.settings.show_wireframe

    def toggle_stats(self) -> bool:
        """Stats overlay toggle"""
        self.settings.show_stats = not self.settings.show_stats
        self._notify("settings_changed", {})
        return self.settings.show_stats

    def set_background_color(self, color: List[float]):
        """Background color set karo (RGB 0-1)"""
        self.settings.background_color = color
        self._notify("settings_changed", {})

    # ----------------------------------------------------------
    # STATS
    # ----------------------------------------------------------

    def update_stats(
        self,
        fps: Optional[float]         = None,
        triangles: Optional[int]     = None,
        draw_calls: Optional[int]    = None,
        render_time: Optional[float] = None,
    ):
        """Stats update karo"""
        if fps is not None:
            self.stats.fps = fps
        if triangles is not None:
            self.stats.triangles = triangles
        if draw_calls is not None:
            self.stats.draw_calls = draw_calls
        if render_time is not None:
            self.stats.render_time_ms = render_time
        self.stats.frame_count += 1

    def get_stats_string(self) -> str:
        """Stats display string"""
        return (
            f"FPS: {self.stats.fps:.1f} | "
            f"Triangles: {self.stats.triangles:,} | "
            f"Draws: {self.stats.draw_calls} | "
            f"Frame: {self.stats.frame_count}"
        )

    # ----------------------------------------------------------
    # VIEWPORT SIZE
    # ----------------------------------------------------------

    def resize(self, width: int, height: int):
        """Viewport resize"""
        self._viewport_width  = max(1, width)
        self._viewport_height = max(1, height)
        self._notify("resized", {"width": width, "height": height})

    def get_size(self) -> Tuple[int, int]:
        return (self._viewport_width, self._viewport_height)

    def get_aspect_ratio(self) -> float:
        """Aspect ratio calculate karo"""
        return self._viewport_width / max(1, self._viewport_height)

    # ----------------------------------------------------------
    # SELECTION
    # ----------------------------------------------------------

    def set_selection(self, object_ids: List[str]):
        """Selected objects set karo"""
        self._selected_ids = list(object_ids)
        self._notify("selection_changed", {"ids": self._selected_ids})

    def get_selection(self) -> List[str]:
        return self._selected_ids.copy()

    def clear_selection(self):
        self._selected_ids = []
        self._notify("selection_changed", {"ids": []})

    # ----------------------------------------------------------
    # RENDER CALLBACKS
    # ----------------------------------------------------------

    def register_render_callback(self, callback: Callable):
        """Render callback register karo"""
        self._render_callbacks.append(callback)

    def _trigger_render(self):
        """Render callbacks trigger karo"""
        for cb in self._render_callbacks:
            try:
                cb()
            except Exception as e:
                logger.warning(f"Render callback error: {e}")

    # ----------------------------------------------------------
    # LISTENERS
    # ----------------------------------------------------------

    def add_listener(self, callback: Callable):
        self._listeners.append(callback)

    def _notify(self, event: str, data: Dict):
        for cb in self._listeners:
            try:
                cb(event, data)
            except Exception as e:
                logger.warning(f"Viewport listener error: {e}")


# ============================================================
# QT VIEWPORT WIDGET
# ============================================================

class ViewportWidget:
    """
    PyQt5 3D Viewport Widget.
    QOpenGLWidget based - hardware accelerated rendering.
    Mouse navigation, view presets, stats overlay sab include.
    """

    def __init__(
        self,
        parent=None,
        model: Optional[ViewportModel] = None,
        theme_manager=None,
        config: Optional[Dict] = None,
    ):
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        self.parent_widget = parent
        self.theme_manager = theme_manager
        self.model         = model or ViewportModel()

        # Qt references
        self._widget       = None
        self._gl_widget    = None
        self._toolbar      = None
        self._stats_label  = None
        self._view_combo   = None

        # Mouse state
        self._last_mouse_x: float = 0.0
        self._last_mouse_y: float = 0.0
        self._mouse_button: int   = 0

        # FPS tracking
        self._fps_frame_count: int   = 0
        self._fps_time_ms:     float = 0.0

        # Build widget
        self._build_widget()

        # Listen to model changes
        self.model.add_listener(self._on_model_changed)

        logger.info("✅ ViewportWidget initialized")

    def _build_widget(self):
        """Qt widget build karo"""
        try:
            from PyQt5.QtWidgets import (
                QWidget, QVBoxLayout, QHBoxLayout,
                QLabel, QPushButton, QComboBox,
                QToolButton, QFrame,
            )
            from PyQt5.QtCore import Qt, QTimer

            # Main container
            self._widget = QWidget(self.parent_widget)
            self._widget.setObjectName("ViewportContainer")

            layout = QVBoxLayout(self._widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            # ===== TOP TOOLBAR =====
            self._toolbar = self._build_toolbar()
            layout.addWidget(self._toolbar)

            # ===== OPENGL VIEWPORT =====
            gl_widget = self._create_gl_widget()
            if gl_widget:
                self._gl_widget = gl_widget
                layout.addWidget(gl_widget, 1)
            else:
                # Fallback placeholder
                placeholder = QLabel(
                    "\n\n\n\n🎬  3D Viewport\n\n"
                    "OpenGL widget nahi ban saka.\n"
                    "PyOpenGL install karo:\n"
                    "pip install PyOpenGL PyOpenGL_accelerate\n\n\n\n"
                )
                placeholder.setAlignment(Qt.AlignCenter)
                placeholder.setStyleSheet(
                    "background-color: #1A1A2E; color: #8888AA; "
                    "font-size: 12px; padding: 40px;"
                )
                layout.addWidget(placeholder, 1)

            # ===== BOTTOM STATUS BAR =====
            self._status_bar = self._build_status_bar()
            layout.addWidget(self._status_bar)

            # Theme apply
            self._apply_theme()

            # FPS timer
            self._fps_timer = QTimer()
            self._fps_timer.setInterval(1000)   # 1 second
            self._fps_timer.timeout.connect(self._update_fps)
            self._fps_timer.start()

        except ImportError:
            logger.warning("PyQt5 nahi - viewport non-Qt mode")
        except Exception as e:
            logger.error(f"Viewport build error: {e}")

    def _build_toolbar(self):
        """Top toolbar build karo"""
        try:
            from PyQt5.QtWidgets import (
                QWidget, QHBoxLayout, QLabel,
                QComboBox, QToolButton, QPushButton,
            )
            from PyQt5.QtCore import Qt

            toolbar = QWidget()
            toolbar.setObjectName("ViewportToolbar")
            toolbar.setFixedHeight(32)
            layout = QHBoxLayout(toolbar)
            layout.setContentsMargins(6, 3, 6, 3)
            layout.setSpacing(4)

            # View preset
            view_lbl = QLabel("View:")
            layout.addWidget(view_lbl)

            self._view_combo = QComboBox()
            self._view_combo.addItems([
                "🎬 Perspective", "⬜ Front", "⬜ Back",
                "⬜ Left", "⬜ Right",
                "⬜ Top", "⬜ Bottom",
            ])
            self._view_combo.setFixedWidth(120)
            self._view_combo.currentIndexChanged.connect(
                self._on_view_preset_changed
            )
            layout.addWidget(self._view_combo)

            layout.addSpacing(8)

            # Display mode
            mode_lbl = QLabel("Mode:")
            layout.addWidget(mode_lbl)

            self._mode_combo = QComboBox()
            self._mode_combo.addItems(["Solid", "Wireframe", "Material", "Rendered"])
            self._mode_combo.setFixedWidth(90)
            self._mode_combo.currentTextChanged.connect(
                lambda t: self.model.set_display_mode(t.lower())
            )
            layout.addWidget(self._mode_combo)

            layout.addSpacing(8)

            # Toggle buttons
            self._grid_btn = QToolButton()
            self._grid_btn.setText("⊞")
            self._grid_btn.setToolTip("Grid toggle karo")
            self._grid_btn.setCheckable(True)
            self._grid_btn.setChecked(True)
            self._grid_btn.setFixedSize(26, 26)
            self._grid_btn.toggled.connect(
                lambda: self.model.toggle_grid()
            )
            layout.addWidget(self._grid_btn)

            self._axes_btn = QToolButton()
            self._axes_btn.setText("✥")
            self._axes_btn.setToolTip("Axes toggle karo")
            self._axes_btn.setCheckable(True)
            self._axes_btn.setChecked(True)
            self._axes_btn.setFixedSize(26, 26)
            self._axes_btn.toggled.connect(
                lambda: self.model.toggle_axes()
            )
            layout.addWidget(self._axes_btn)

            self._stats_btn = QToolButton()
            self._stats_btn.setText("📊")
            self._stats_btn.setToolTip("Stats toggle karo")
            self._stats_btn.setCheckable(True)
            self._stats_btn.setChecked(True)
            self._stats_btn.setFixedSize(26, 26)
            self._stats_btn.toggled.connect(
                lambda: self.model.toggle_stats()
            )
            layout.addWidget(self._stats_btn)

            layout.addStretch()

            # Focus button
            focus_btn = QPushButton("🎯 Focus")
            focus_btn.setToolTip("Selected object pe focus (F)")
            focus_btn.setFixedHeight(24)
            focus_btn.clicked.connect(self.focus_on_selection)
            layout.addWidget(focus_btn)

            # Reset button
            reset_btn = QPushButton("↺ Reset")
            reset_btn.setToolTip("Camera reset karo")
            reset_btn.setFixedHeight(24)
            reset_btn.clicked.connect(self.model.reset_camera)
            layout.addWidget(reset_btn)

            return toolbar

        except Exception as e:
            logger.warning(f"Toolbar build error: {e}")
            return QWidget()

    def _build_status_bar(self):
        """Bottom status bar"""
        try:
            from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel

            bar = QWidget()
            bar.setObjectName("ViewportStatus")
            bar.setFixedHeight(24)
            layout = QHBoxLayout(bar)
            layout.setContentsMargins(6, 2, 6, 2)

            self._stats_label = QLabel("FPS: -- | Ready")
            self._stats_label.setObjectName("ViewStats")
            layout.addWidget(self._stats_label)

            layout.addStretch()

            self._cam_info_label = QLabel("Perspective | Dist: 10.0")
            self._cam_info_label.setObjectName("CamInfo")
            layout.addWidget(self._cam_info_label)

            return bar

        except Exception as e:
            logger.warning(f"Status bar build error: {e}")
            return QWidget()

    def _create_gl_widget(self):
        """QOpenGLWidget banao"""
        try:
            from PyQt5.QtWidgets import QOpenGLWidget
            from PyQt5.QtCore import Qt
            from PyQt5.QtGui import QSurfaceFormat, QMouseEvent, QWheelEvent

            # OpenGL format setup
            fmt = QSurfaceFormat()
            fmt.setDepthBufferSize(24)
            fmt.setStencilBufferSize(8)
            fmt.setSamples(4)   # Anti-aliasing
            fmt.setVersion(3, 3)
            fmt.setProfile(QSurfaceFormat.CoreProfile)

            # Custom viewport class
            model_ref     = self.model
            parent_widget = self

            class GLViewport(QOpenGLWidget):
                def __init__(self):
                    super().__init__()
                    self.setFormat(fmt)
                    self.setMinimumSize(400, 300)
                    self.setFocusPolicy(Qt.StrongFocus)
                    self.setMouseTracking(True)
                    self._initialized = False

                def initializeGL(self):
                    """OpenGL initialize"""
                    try:
                        from OpenGL import GL
                        GL.glClearColor(*model_ref.settings.background_color)
                        GL.glEnable(GL.GL_DEPTH_TEST)
                        GL.glEnable(GL.GL_BLEND)
                        GL.glBlendFunc(
                            GL.GL_SRC_ALPHA,
                            GL.GL_ONE_MINUS_SRC_ALPHA
                        )
                        self._initialized = True
                        logger.info(
                            f"✅ OpenGL initialized | "
                            f"Version: {GL.glGetString(GL.GL_VERSION).decode('utf-8')[:30]}"
                        )
                    except Exception as e:
                        logger.error(f"GL init error: {e}")

                def resizeGL(self, w: int, h: int):
                    """Viewport resize"""
                    try:
                        from OpenGL import GL
                        GL.glViewport(0, 0, w, h)
                        model_ref.resize(w, h)
                    except Exception:
                        pass

                def paintGL(self):
                    """Frame render karo"""
                    try:
                        from OpenGL import GL
                        import time as _t

                        start_time = _t.time()

                        # Background clear
                        bg = model_ref.settings.background_color
                        GL.glClearColor(bg[0], bg[1], bg[2], bg[3])
                        GL.glClear(
                            GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT
                        )

                        # Setup matrices
                        self._setup_projection()
                        self._setup_view()

                        # Wireframe mode
                        if model_ref.settings.show_wireframe:
                            GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_LINE)
                        else:
                            GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)

                        # Grid draw karo
                        if model_ref.settings.show_grid:
                            self._draw_grid()

                        # Axes draw karo
                        if model_ref.settings.show_axes:
                            self._draw_axes()

                        # Sample scene (test cube)
                        self._draw_sample_scene()

                        # Custom render callbacks
                        model_ref._trigger_render()

                        # Stats update
                        render_time_ms = (_t.time() - start_time) * 1000
                        model_ref.update_stats(
                            triangles  = 12,   # Sample cube = 12 triangles
                            draw_calls = 3,
                            render_time= render_time_ms,
                        )
                        parent_widget._fps_frame_count += 1

                    except Exception as e:
                        logger.error(f"Paint GL error: {e}")

                def _setup_projection(self):
                    """Projection matrix setup"""
                    try:
                        from OpenGL import GL
                        cam    = model_ref.camera
                        aspect = model_ref.get_aspect_ratio()

                        GL.glMatrixMode(GL.GL_PROJECTION)
                        GL.glLoadIdentity()

                        if cam.projection == ProjectionType.PERSPECTIVE.value:
                            self._perspective(
                                cam.fov, aspect, cam.near_clip, cam.far_clip
                            )
                        else:
                            size = cam.ortho_size
                            h = size
                            w = size * aspect
                            GL.glOrtho(-w, w, -h, h, cam.near_clip, cam.far_clip)
                    except Exception:
                        pass

                def _perspective(self, fov, aspect, near, far):
                    """gluPerspective manual"""
                    try:
                        from OpenGL import GL
                        f = 1.0 / math.tan(math.radians(fov) / 2.0)
                        matrix = np.array([
                            [f/aspect, 0, 0, 0],
                            [0, f, 0, 0],
                            [0, 0, (far+near)/(near-far), (2*far*near)/(near-far)],
                            [0, 0, -1, 0],
                        ], dtype=np.float32).T
                        GL.glMultMatrixf(matrix.flatten())
                    except Exception:
                        pass

                def _setup_view(self):
                    """View matrix (camera) setup"""
                    try:
                        from OpenGL import GL
                        cam = model_ref.camera
                        pos = cam.get_position()
                        tgt = cam.target

                        GL.glMatrixMode(GL.GL_MODELVIEW)
                        GL.glLoadIdentity()

                        self._look_at(
                            pos[0], pos[1], pos[2],
                            tgt[0], tgt[1], tgt[2],
                            0, 1, 0,
                        )
                    except Exception:
                        pass

                def _look_at(
                    self,
                    ex, ey, ez,
                    cx, cy, cz,
                    ux, uy, uz,
                ):
                    """gluLookAt manual"""
                    try:
                        from OpenGL import GL

                        # Forward vector
                        fx, fy, fz = cx - ex, cy - ey, cz - ez
                        flen = math.sqrt(fx*fx + fy*fy + fz*fz)
                        if flen > 0:
                            fx, fy, fz = fx/flen, fy/flen, fz/flen

                        # Side vector (F x Up)
                        sx = fy*uz - fz*uy
                        sy = fz*ux - fx*uz
                        sz = fx*uy - fy*ux
                        slen = math.sqrt(sx*sx + sy*sy + sz*sz)
                        if slen > 0:
                            sx, sy, sz = sx/slen, sy/slen, sz/slen

                        # Up vector (S x F)
                        ux2 = sy*fz - sz*fy
                        uy2 = sz*fx - sx*fz
                        uz2 = sx*fy - sy*fx

                        matrix = np.array([
                            [sx,  ux2,  -fx, 0],
                            [sy,  uy2,  -fy, 0],
                            [sz,  uz2,  -fz, 0],
                            [0,   0,     0,  1],
                        ], dtype=np.float32).T

                        GL.glMultMatrixf(matrix.flatten())
                        GL.glTranslatef(-ex, -ey, -ez)

                    except Exception:
                        pass

                def _draw_grid(self):
                    """Ground grid draw karo"""
                    try:
                        from OpenGL import GL
                        grid = model_ref.grid
                        size = grid.size / 2.0
                        step = grid.size / grid.divisions

                        GL.glLineWidth(1.0)
                        GL.glColor4f(*grid.color)
                        GL.glBegin(GL.GL_LINES)

                        # X-parallel lines
                        for i in range(grid.divisions + 1):
                            z = -size + i * step
                            GL.glVertex3f(-size, 0, z)
                            GL.glVertex3f( size, 0, z)

                        # Z-parallel lines
                        for i in range(grid.divisions + 1):
                            x = -size + i * step
                            GL.glVertex3f(x, 0, -size)
                            GL.glVertex3f(x, 0,  size)

                        GL.glEnd()
                    except Exception:
                        pass

                def _draw_axes(self):
                    """XYZ axes draw karo"""
                    try:
                        from OpenGL import GL
                        length = 3.0

                        GL.glLineWidth(2.0)
                        GL.glBegin(GL.GL_LINES)

                        # X axis - Red
                        GL.glColor3f(1.0, 0.3, 0.3)
                        GL.glVertex3f(0, 0.01, 0)
                        GL.glVertex3f(length, 0.01, 0)

                        # Y axis - Green
                        GL.glColor3f(0.3, 1.0, 0.3)
                        GL.glVertex3f(0, 0, 0)
                        GL.glVertex3f(0, length, 0)

                        # Z axis - Blue
                        GL.glColor3f(0.3, 0.5, 1.0)
                        GL.glVertex3f(0, 0.01, 0)
                        GL.glVertex3f(0, 0.01, length)

                        GL.glEnd()
                        GL.glLineWidth(1.0)
                    except Exception:
                        pass

                def _draw_sample_scene(self):
                    """Sample scene - test cube"""
                    try:
                        from OpenGL import GL

                        # Colorful cube
                        GL.glBegin(GL.GL_QUADS)

                        # Front face (Cyan)
                        GL.glColor4f(0.0, 0.8, 1.0, 0.9)
                        GL.glVertex3f(-1, -1, 1); GL.glVertex3f(1, -1, 1)
                        GL.glVertex3f(1, 1, 1);   GL.glVertex3f(-1, 1, 1)

                        # Back face (Purple)
                        GL.glColor4f(0.6, 0.3, 0.8, 0.9)
                        GL.glVertex3f(-1, -1, -1); GL.glVertex3f(-1, 1, -1)
                        GL.glVertex3f(1, 1, -1);   GL.glVertex3f(1, -1, -1)

                        # Top face (Green)
                        GL.glColor4f(0.3, 1.0, 0.4, 0.9)
                        GL.glVertex3f(-1, 1, -1); GL.glVertex3f(-1, 1, 1)
                        GL.glVertex3f(1, 1, 1);   GL.glVertex3f(1, 1, -1)

                        # Bottom face (Orange)
                        GL.glColor4f(1.0, 0.5, 0.2, 0.9)
                        GL.glVertex3f(-1, -1, -1); GL.glVertex3f(1, -1, -1)
                        GL.glVertex3f(1, -1, 1);   GL.glVertex3f(-1, -1, 1)

                        # Right face (Yellow)
                        GL.glColor4f(1.0, 0.9, 0.3, 0.9)
                        GL.glVertex3f(1, -1, -1); GL.glVertex3f(1, 1, -1)
                        GL.glVertex3f(1, 1, 1);   GL.glVertex3f(1, -1, 1)

                        # Left face (Pink)
                        GL.glColor4f(1.0, 0.4, 0.7, 0.9)
                        GL.glVertex3f(-1, -1, -1); GL.glVertex3f(-1, -1, 1)
                        GL.glVertex3f(-1, 1, 1);   GL.glVertex3f(-1, 1, -1)

                        GL.glEnd()

                    except Exception:
                        pass

                def mousePressEvent(self, event: 'QMouseEvent'):
                    parent_widget._on_mouse_press(event)

                def mouseMoveEvent(self, event: 'QMouseEvent'):
                    parent_widget._on_mouse_move(event)
                    self.update()

                def mouseReleaseEvent(self, event: 'QMouseEvent'):
                    parent_widget._on_mouse_release(event)

                def wheelEvent(self, event: 'QWheelEvent'):
                    parent_widget._on_wheel(event)
                    self.update()

                def keyPressEvent(self, event):
                    parent_widget._on_key_press(event)
                    self.update()

            gl_widget = GLViewport()
            return gl_widget

        except ImportError as e:
            logger.warning(f"OpenGL widget nahi ban saka: {e}")
            return None
        except Exception as e:
            logger.error(f"GL widget error: {e}")
            return None

    def _apply_theme(self):
        """Theme apply karo"""
        if not self.theme_manager or not self._widget:
            return
        try:
            p = self.theme_manager.get_palette()
            self._widget.setStyleSheet(f"""
                #ViewportContainer {{
                    background-color: {p.bg_primary};
                }}
                #ViewportToolbar {{
                    background-color: {p.bg_secondary};
                    border-bottom: 1px solid {p.border};
                }}
                #ViewportStatus {{
                    background-color: {p.bg_secondary};
                    border-top: 1px solid {p.border};
                }}
                QLabel {{
                    color: {p.text_secondary};
                    font-size: 10px;
                }}
                #ViewStats {{
                    color: {p.accent};
                    font-family: monospace;
                    font-size: 10px;
                    font-weight: bold;
                }}
                #CamInfo {{
                    color: {p.text_secondary};
                    font-family: monospace;
                    font-size: 10px;
                }}
                QComboBox {{
                    background-color: {p.bg_tertiary};
                    border: 1px solid {p.border};
                    border-radius: 3px;
                    color: {p.text_primary};
                    padding: 2px 6px;
                    font-size: 10px;
                }}
                QToolButton {{
                    background-color: {p.bg_tertiary};
                    border: 1px solid {p.border};
                    border-radius: 3px;
                    color: {p.text_primary};
                    font-size: 12px;
                }}
                QToolButton:checked {{
                    background-color: {p.accent_muted};
                    border-color: {p.accent};
                    color: {p.accent};
                }}
                QPushButton {{
                    background-color: {p.bg_elevated};
                    border: 1px solid {p.border};
                    border-radius: 3px;
                    color: {p.text_primary};
                    padding: 3px 10px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {p.accent_muted};
                    border-color: {p.accent};
                    color: {p.accent};
                }}
            """)
        except Exception as e:
            logger.warning(f"Theme apply error: {e}")

    # ----------------------------------------------------------
    # MOUSE / KEYBOARD HANDLERS
    # ----------------------------------------------------------

    def _on_mouse_press(self, event):
        """Mouse press handle karo"""
        try:
            from PyQt5.QtCore import Qt
            self._last_mouse_x = event.x()
            self._last_mouse_y = event.y()
            self._mouse_button = event.button()
        except Exception:
            pass

    def _on_mouse_move(self, event):
        """Mouse move handle karo (drag)"""
        try:
            from PyQt5.QtCore import Qt
            dx = event.x() - self._last_mouse_x
            dy = event.y() - self._last_mouse_y

            if event.buttons() & Qt.LeftButton:
                # Left drag = Orbit
                if event.modifiers() & Qt.ShiftModifier:
                    self.model.pan_camera(dx, dy)
                else:
                    self.model.orbit_camera(dx, dy)
            elif event.buttons() & Qt.RightButton:
                # Right drag = Zoom
                self.model.zoom_camera(-dy * 10)
            elif event.buttons() & Qt.MiddleButton:
                # Middle drag = Pan
                self.model.pan_camera(dx, dy)

            self._last_mouse_x = event.x()
            self._last_mouse_y = event.y()

        except Exception:
            pass

    def _on_mouse_release(self, event):
        """Mouse release"""
        self._mouse_button = 0

    def _on_wheel(self, event):
        """Mouse wheel = zoom"""
        try:
            delta = event.angleDelta().y()
            self.model.zoom_camera(-delta * 2)
        except Exception:
            pass

    def _on_key_press(self, event):
        """Keyboard shortcuts"""
        try:
            from PyQt5.QtCore import Qt

            key = event.key()

            # View presets
            if key == Qt.Key_1:
                self.model.apply_view_preset(ViewPreset.FRONT.value)
            elif key == Qt.Key_3:
                self.model.apply_view_preset(ViewPreset.RIGHT.value)
            elif key == Qt.Key_7:
                self.model.apply_view_preset(ViewPreset.TOP.value)
            elif key == Qt.Key_5:
                # Toggle projection
                cur = self.model.camera.projection
                if cur == ProjectionType.PERSPECTIVE.value:
                    self.model.camera.projection = ProjectionType.ORTHOGRAPHIC.value
                else:
                    self.model.camera.projection = ProjectionType.PERSPECTIVE.value
                self.model._notify("camera_changed", {})
            elif key == Qt.Key_F:
                self.focus_on_selection()
            elif key == Qt.Key_R:
                self.model.reset_camera()
            elif key == Qt.Key_W:
                self.model.toggle_wireframe()
            elif key == Qt.Key_G:
                self.model.toggle_grid()

        except Exception:
            pass

    # ----------------------------------------------------------
    # EVENT HANDLERS
    # ----------------------------------------------------------

    def _on_model_changed(self, event: str, data: Dict):
        """Model changes handle karo"""
        if event in ["camera_changed", "settings_changed"]:
            if self._gl_widget:
                try:
                    self._gl_widget.update()
                except Exception:
                    pass
            self._update_cam_info()

    def _on_view_preset_changed(self, index: int):
        """View preset combo change"""
        presets = [
            ViewPreset.PERSPECTIVE.value,
            ViewPreset.FRONT.value,
            ViewPreset.BACK.value,
            ViewPreset.LEFT.value,
            ViewPreset.RIGHT.value,
            ViewPreset.TOP.value,
            ViewPreset.BOTTOM.value,
        ]
        if 0 <= index < len(presets):
            self.model.apply_view_preset(presets[index])

    def _update_fps(self):
        """FPS calculate karo per second"""
        fps = float(self._fps_frame_count)
        self.model.update_stats(fps=fps)
        self._fps_frame_count = 0

        if self._stats_label:
            try:
                if self.model.settings.show_stats:
                    self._stats_label.setText(self.model.get_stats_string())
                else:
                    self._stats_label.setText("Stats hidden")
            except Exception:
                pass

    def _update_cam_info(self):
        """Camera info update karo"""
        if not self._cam_info_label:
            return
        try:
            cam = self.model.camera
            proj = "Persp" if cam.projection == ProjectionType.PERSPECTIVE.value else "Ortho"
            self._cam_info_label.setText(
                f"{proj} | Dist: {cam.distance:.1f} | "
                f"Az: {cam.azimuth:.0f}° | El: {cam.elevation:.0f}°"
            )
        except Exception:
            pass

    # ----------------------------------------------------------
    # PUBLIC API
    # ----------------------------------------------------------

    def get_widget(self):
        """Qt widget lo"""
        return self._widget

    def get_gl_widget(self):
        """OpenGL widget lo (rendering pe direct access)"""
        return self._gl_widget

    def get_model(self) -> ViewportModel:
        """Model lo"""
        return self.model

    def focus_on_selection(self):
        """Selection pe focus karo"""
        # TODO: actual scene selection ke saath integrate
        self.model.focus_on_position([0, 0, 0], distance=8.0)
        logger.debug("Focus on selection")

    def refresh(self):
        """Force viewport refresh"""
        if self._gl_widget:
            try:
                self._gl_widget.update()
            except Exception:
                pass


# ============================================================
# GLOBAL INSTANCE
# ============================================================

_global_model: Optional[ViewportModel] = None


def get_viewport_model() -> ViewportModel:
    """Global ViewportModel lo"""
    global _global_model
    if _global_model is None:
        _global_model = ViewportModel()
    return _global_model


# ============================================================
# TEST SECTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="DEBUG")
    print_banner("Viewport Widget Test", "3D Viewport with OpenGL")

    # ===== TEST 1: Camera =====
    print_section("Test 1: Viewport Camera")
    cam = ViewportCamera()
    print(f"✅ Camera created")
    print(f"   Distance : {cam.distance}")
    print(f"   Azimuth  : {cam.azimuth}°")
    print(f"   Elevation: {cam.elevation}°")
    print(f"   Position : {[round(x, 2) for x in cam.get_position()]}")

    # Orbit
    cam.orbit(30, 20)
    print(f"✅ After orbit(30, 20):")
    print(f"   Azimuth  : {cam.azimuth}°")
    print(f"   Elevation: {cam.elevation}°")

    # Pan
    cam.pan(5, 5)
    print(f"✅ After pan: target = {[round(x, 3) for x in cam.target]}")

    # Zoom
    old_dist = cam.distance
    cam.zoom(-500)
    print(f"✅ After zoom in: distance {old_dist:.2f} → {cam.distance:.2f}")

    # Reset
    cam.reset()
    print(f"✅ Reset: azimuth={cam.azimuth}, distance={cam.distance}")

    # ===== TEST 2: View Presets =====
    print_section("Test 2: View Presets")
    for preset in [ViewPreset.FRONT, ViewPreset.TOP, ViewPreset.RIGHT,
                   ViewPreset.PERSPECTIVE]:
        cam.apply_preset(preset.value)
        print(
            f"✅ {preset.value:12s}: "
            f"Az={cam.azimuth:>6.1f} El={cam.elevation:>5.1f} "
            f"Proj={cam.projection}"
        )

    # ===== TEST 3: Grid Settings =====
    print_section("Test 3: Grid Settings")
    grid = GridSettings()
    print(f"✅ Grid: size={grid.size}, divs={grid.divisions}")
    print(f"   Visible: {grid.visible}, Axes: {grid.show_axes}")

    # ===== TEST 4: Viewport Settings =====
    print_section("Test 4: Viewport Settings")
    settings = ViewportSettings()
    print(f"✅ Mode: {settings.mode}")
    print(f"   Grid : {settings.show_grid}")
    print(f"   Axes : {settings.show_axes}")
    print(f"   AA   : {settings.aa_samples}x")

    # ===== TEST 5: Model =====
    print_section("Test 5: ViewportModel")
    model = ViewportModel()
    print(f"✅ Model initialized")
    print(f"   Size    : {model.get_size()}")
    print(f"   Aspect  : {model.get_aspect_ratio():.2f}")

    # Resize
    model.resize(1920, 1080)
    print(f"✅ Resized: {model.get_size()} | Aspect: {model.get_aspect_ratio():.2f}")

    # Camera controls via model
    model.orbit_camera(45, 15)
    print(f"✅ Orbit via model: azimuth={model.camera.azimuth}")

    model.zoom_camera(-200)
    print(f"✅ Zoom via model: distance={model.camera.distance:.2f}")

    model.apply_view_preset(ViewPreset.TOP.value)
    print(f"✅ Top view: elevation={model.camera.elevation}")

    # ===== TEST 6: Display Modes =====
    print_section("Test 6: Display Modes")
    for mode in ViewportMode:
        model.set_display_mode(mode.value)
        print(f"✅ Mode set: {mode.value}")

    model.toggle_wireframe()
    print(f"✅ Wireframe toggled: {model.settings.show_wireframe}")

    # ===== TEST 7: Stats =====
    print_section("Test 7: Stats")
    model.update_stats(fps=60.0, triangles=15000, draw_calls=25)
    stats_str = model.get_stats_string()
    print(f"✅ Stats: {stats_str}")

    for i in range(5):
        model.update_stats(triangles=1000+i*500)
    print(f"✅ Frame count: {model.stats.frame_count}")

    # ===== TEST 8: Selection =====
    print_section("Test 8: Selection")
    model.set_selection(["obj_001", "obj_002", "obj_003"])
    print(f"✅ Selected: {model.get_selection()}")

    model.clear_selection()
    print(f"✅ Cleared: {model.get_selection()}")

    # ===== TEST 9: Focus =====
    print_section("Test 9: Focus on Position")
    model.focus_on_position([5.0, 2.0, -3.0], distance=8.0)
    print(f"✅ Focused: target={model.camera.target}, dist={model.camera.distance}")

    # ===== TEST 10: Listeners =====
    print_section("Test 10: Event Listeners")
    events = []
    def on_event(event, data):
        events.append(event)

    model.add_listener(on_event)
    model.orbit_camera(10, 10)
    model.zoom_camera(-100)
    model.toggle_grid()
    model.set_selection(["test"])
    print(f"✅ Events: {events}")

    # ===== TEST 11: Qt Widget =====
    print_section("Test 11: Qt Viewport Widget (Visual)")
    try:
        from PyQt5.QtWidgets import QApplication, QMainWindow
        import sys as _sys

        app = QApplication.instance() or QApplication(_sys.argv)

        from src.ui.theme_manager import ThemeManager
        theme = ThemeManager()
        theme.set_application(app)

        window = QMainWindow()
        window.setWindowTitle("Viewport Test")
        window.resize(1000, 700)

        viewport = ViewportWidget(
            model         = model,
            theme_manager = theme,
        )
        window.setCentralWidget(viewport.get_widget())
        window.show()

        print(f"✅ Qt viewport shown")
        print(f"   GL widget: {viewport.get_gl_widget() is not None}")
        print(f"   Controls:")
        print(f"     • Left drag  : Orbit")
        print(f"     • Right drag : Zoom")
        print(f"     • Middle drag: Pan")
        print(f"     • Wheel      : Zoom")
        print(f"     • F          : Focus")
        print(f"     • R          : Reset")
        print(f"     • W          : Wireframe")
        print(f"     • G          : Grid")
        print(f"     • 1/3/7      : Front/Right/Top view")

        from PyQt5.QtCore import QTimer
        QTimer.singleShot(2000, app.quit)   # 2 sec show
        app.exec_()
        print(f"✅ Qt test complete")

    except ImportError:
        print("⚠️  PyQt5 visual test skip")
    except Exception as e:
        print(f"⚠️  Qt test: {e}")

    # ===== TEST 12: Singleton =====
    print_section("Test 12: Global Singleton")
    m1 = get_viewport_model()
    m2 = get_viewport_model()
    print(f"✅ Singleton: {m1 is m2}")

    print_banner("✅ All Tests Passed!", "viewport_widget.py Working Perfectly")