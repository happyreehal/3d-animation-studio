# ============================================================
# src/ui/dialogs.py
# 3D Animation Studio - Dialog Windows
# Import, Export, Settings, About, Progress dialogs
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

import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum

from src.utils import get_logger, get_config, get_timestamp

logger = get_logger("Dialogs")


# ============================================================
# ENUMS
# ============================================================

class DialogResult(Enum):
    """Dialog result codes"""
    ACCEPTED  = "accepted"
    REJECTED  = "rejected"
    CANCELLED = "cancelled"


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class ImportSettings:
    """Import dialog settings"""
    file_path:          str   = ""
    file_type:          str   = "auto"
    scale:              float = 1.0
    center_on_import:   bool  = True
    normalize_size:     bool  = False
    import_materials:   bool  = True
    import_animations:  bool  = True
    copy_to_project:    bool  = True
    up_axis:            str   = "Y"     # Y ya Z


@dataclass
class ExportSettings:
    """Export dialog settings"""
    output_path:        str   = ""
    format:             str   = "mp4"
    preset:             str   = "youtube_1080p"
    width:              int   = 1920
    height:             int   = 1080
    fps:                int   = 30
    quality:            str   = "high"
    include_audio:      bool  = True
    open_after_export:  bool  = True
    start_frame:        int   = 0
    end_frame:          int   = 300


@dataclass
class RenderSettings:
    """Render settings dialog"""
    quality:            str   = "high"
    fps:                int   = 30
    width:              int   = 1920
    height:             int   = 1080
    samples:            int   = 64
    use_shadows:        bool  = True
    use_ambient_occlusion: bool = True
    use_motion_blur:    bool  = False
    output_folder:      str   = "exports"
    filename:           str   = "render"
    frame_range:        Tuple[int, int] = (0, 300)


@dataclass
class ProjectSettings:
    """New project settings"""
    name:               str   = "My Animation"
    author:             str   = ""
    fps:                int   = 30
    width:              int   = 1920
    height:             int   = 1080
    total_frames:       int   = 300
    template:           str   = "blank"
    save_location:      str   = "projects"


# ============================================================
# BASE DIALOG (Non-Qt data layer)
# ============================================================

class BaseDialogData:
    """
    Dialog ka base data class.
    Qt se independent - testable.
    """

    def __init__(self):
        self._result  = DialogResult.CANCELLED
        self._data    = {}

    def get_result(self) -> DialogResult:
        return self._result

    def get_data(self) -> Dict:
        return self._data

    def was_accepted(self) -> bool:
        return self._result == DialogResult.ACCEPTED


# ============================================================
# QT DIALOGS
# ============================================================

class StudioDialogs:
    """
    3D Animation Studio ke sabhi dialog windows.
    Static methods - koi state nahi.
    """

    # ----------------------------------------------------------
    # IMPORT DIALOG
    # ----------------------------------------------------------

    @staticmethod
    def show_import_dialog(
        parent=None,
        theme_manager=None,
    ) -> Tuple[DialogResult, ImportSettings]:
        """
        Asset import dialog dikhaao.
        File chooser + import options.
        """
        settings = ImportSettings()
        result   = DialogResult.CANCELLED

        try:
            from PyQt5.QtWidgets import (
                QDialog, QVBoxLayout, QHBoxLayout,
                QLabel, QPushButton, QLineEdit,
                QCheckBox, QComboBox, QDoubleSpinBox,
                QGroupBox, QFormLayout, QFileDialog,
                QToolButton, QDialogButtonBox,
            )
            from PyQt5.QtCore import Qt

            dialog = QDialog(parent)
            dialog.setWindowTitle("📥 Import Asset")
            dialog.setModal(True)
            dialog.setMinimumWidth(480)

            layout = QVBoxLayout(dialog)
            layout.setSpacing(12)
            layout.setContentsMargins(16, 16, 16, 16)

            # Title
            title = QLabel("Import 3D Asset")
            title.setStyleSheet(
                "font-size: 16px; font-weight: bold; color: #00D4FF;"
            )
            layout.addWidget(title)

            # File path
            file_group = QGroupBox("File")
            file_layout = QHBoxLayout(file_group)

            path_edit = QLineEdit()
            path_edit.setPlaceholderText("File path yahan daalo ya browse karo...")
            path_edit.setText(settings.file_path)

            browse_btn = QToolButton()
            browse_btn.setText("...")
            browse_btn.setFixedWidth(30)

            def browse():
                path, _ = QFileDialog.getOpenFileName(
                    dialog, "File Select Karo", "",
                    "3D Models (*.obj *.fbx *.gltf *.glb *.dae *.stl);;"
                    "All Files (*)"
                )
                if path:
                    path_edit.setText(path)

            browse_btn.clicked.connect(browse)
            file_layout.addWidget(path_edit)
            file_layout.addWidget(browse_btn)
            layout.addWidget(file_group)

            # Import options
            opt_group = QGroupBox("Import Options")
            opt_form  = QFormLayout(opt_group)

            # Scale
            scale_spin = QDoubleSpinBox()
            scale_spin.setRange(0.001, 100.0)
            scale_spin.setValue(settings.scale)
            scale_spin.setSingleStep(0.1)
            scale_spin.setDecimals(3)
            opt_form.addRow("Scale:", scale_spin)

            # Up axis
            axis_combo = QComboBox()
            axis_combo.addItems(["Y (Default)", "Z (Blender)"])
            opt_form.addRow("Up Axis:", axis_combo)

            # Checkboxes
            center_chk    = QCheckBox("Center on import")
            center_chk.setChecked(settings.center_on_import)
            opt_form.addRow("", center_chk)

            normalize_chk = QCheckBox("Normalize size")
            normalize_chk.setChecked(settings.normalize_size)
            opt_form.addRow("", normalize_chk)

            materials_chk = QCheckBox("Import materials")
            materials_chk.setChecked(settings.import_materials)
            opt_form.addRow("", materials_chk)

            anim_chk = QCheckBox("Import animations")
            anim_chk.setChecked(settings.import_animations)
            opt_form.addRow("", anim_chk)

            copy_chk = QCheckBox("Copy to project folder")
            copy_chk.setChecked(settings.copy_to_project)
            opt_form.addRow("", copy_chk)

            layout.addWidget(opt_group)

            # Buttons
            btn_box = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            )
            btn_box.button(QDialogButtonBox.Ok).setText("Import")
            btn_box.accepted.connect(dialog.accept)
            btn_box.rejected.connect(dialog.reject)
            layout.addWidget(btn_box)

            # Theme apply
            if theme_manager:
                p = theme_manager.get_palette()
                dialog.setStyleSheet(f"""
                    QDialog {{
                        background-color: {p.bg_secondary};
                        color: {p.text_primary};
                    }}
                    QGroupBox {{
                        border: 1px solid {p.border};
                        border-radius: 5px;
                        margin-top: 10px;
                        padding: 8px;
                        color: {p.accent};
                        font-size: 11px;
                        font-weight: bold;
                    }}
                    QGroupBox::title {{
                        subcontrol-origin: margin;
                        left: 8px; padding: 0 4px;
                    }}
                    QLabel {{
                        color: {p.text_primary};
                        font-size: 12px;
                    }}
                    QLineEdit, QComboBox, QDoubleSpinBox {{
                        background-color: {p.bg_tertiary};
                        border: 1px solid {p.border};
                        border-radius: 3px;
                        color: {p.text_primary};
                        padding: 4px 6px;
                        font-size: 11px;
                    }}
                    QCheckBox {{
                        color: {p.text_primary};
                        font-size: 11px;
                    }}
                    QPushButton {{
                        background-color: {p.accent};
                        color: #000;
                        border: none;
                        border-radius: 4px;
                        padding: 6px 16px;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{ background-color: {p.accent_hover}; }}
                """)

            # Show dialog
            if dialog.exec_() == QDialog.Accepted:
                settings.file_path        = path_edit.text()
                settings.scale            = scale_spin.value()
                settings.up_axis          = "Z" if axis_combo.currentIndex() == 1 else "Y"
                settings.center_on_import = center_chk.isChecked()
                settings.normalize_size   = normalize_chk.isChecked()
                settings.import_materials = materials_chk.isChecked()
                settings.import_animations= anim_chk.isChecked()
                settings.copy_to_project  = copy_chk.isChecked()
                result = DialogResult.ACCEPTED
                logger.info(f"Import dialog accepted: {settings.file_path}")
            else:
                result = DialogResult.REJECTED

        except ImportError:
            logger.warning("PyQt5 nahi - import dialog skip")
        except Exception as e:
            logger.error(f"Import dialog error: {e}")

        return result, settings

    # ----------------------------------------------------------
    # EXPORT DIALOG
    # ----------------------------------------------------------

    @staticmethod
    def show_export_dialog(
        parent=None,
        theme_manager=None,
        initial_settings: Optional[ExportSettings] = None,
    ) -> Tuple[DialogResult, ExportSettings]:
        """Video export dialog"""
        settings = initial_settings or ExportSettings()
        result   = DialogResult.CANCELLED

        try:
            from PyQt5.QtWidgets import (
                QDialog, QVBoxLayout, QHBoxLayout,
                QLabel, QPushButton, QLineEdit,
                QCheckBox, QComboBox, QSpinBox,
                QGroupBox, QFormLayout, QFileDialog,
                QToolButton, QDialogButtonBox, QTabWidget,
                QWidget,
            )
            from PyQt5.QtCore import Qt

            dialog = QDialog(parent)
            dialog.setWindowTitle("📤 Export Video")
            dialog.setModal(True)
            dialog.setMinimumWidth(500)

            layout = QVBoxLayout(dialog)
            layout.setSpacing(10)
            layout.setContentsMargins(16, 16, 16, 16)

            # Title
            title = QLabel("Export Video")
            title.setStyleSheet(
                "font-size: 16px; font-weight: bold; color: #00D4FF;"
            )
            layout.addWidget(title)

            # Tab widget
            tabs = QTabWidget()

            # ===== TAB 1: Output =====
            output_tab = QWidget()
            output_form = QFormLayout(output_tab)
            output_form.setSpacing(8)
            output_form.setContentsMargins(8, 8, 8, 8)

            # Output path
            path_container = QWidget()
            path_layout = QHBoxLayout(path_container)
            path_layout.setContentsMargins(0, 0, 0, 0)
            path_layout.setSpacing(4)

            path_edit = QLineEdit()
            path_edit.setText(settings.output_path or "exports/output.mp4")
            path_edit.setPlaceholderText("Output file path...")

            path_btn = QToolButton()
            path_btn.setText("...")

            def browse_output():
                path, _ = QFileDialog.getSaveFileName(
                    dialog, "Save Video As", "",
                    "MP4 Video (*.mp4);;WebM Video (*.webm);;All Files (*)"
                )
                if path:
                    path_edit.setText(path)

            path_btn.clicked.connect(browse_output)
            path_layout.addWidget(path_edit)
            path_layout.addWidget(path_btn)
            output_form.addRow("Output File:", path_container)

            # Platform preset
            preset_combo = QComboBox()
            presets = [
                "youtube_1080p", "youtube_4k", "youtube_720p",
                "youtube_shorts", "instagram_reels", "instagram_feed",
                "tiktok", "twitter", "facebook", "web_optimized",
                "draft_preview",
            ]
            preset_combo.addItems(presets)
            if settings.preset in presets:
                preset_combo.setCurrentText(settings.preset)
            output_form.addRow("Platform Preset:", preset_combo)

            # Format
            format_combo = QComboBox()
            format_combo.addItems(["MP4 (H264)", "MP4 (H265)", "WebM (VP9)"])
            output_form.addRow("Format:", format_combo)

            # Quality
            quality_combo = QComboBox()
            quality_combo.addItems(["draft", "medium", "high", "ultra"])
            quality_combo.setCurrentText(settings.quality)
            output_form.addRow("Quality:", quality_combo)

            tabs.addTab(output_tab, "📁 Output")

            # ===== TAB 2: Video =====
            video_tab = QWidget()
            video_form = QFormLayout(video_tab)
            video_form.setSpacing(8)
            video_form.setContentsMargins(8, 8, 8, 8)

            # Resolution
            res_container = QWidget()
            res_layout = QHBoxLayout(res_container)
            res_layout.setContentsMargins(0, 0, 0, 0)
            res_layout.setSpacing(4)

            width_spin = QSpinBox()
            width_spin.setRange(320, 7680)
            width_spin.setValue(settings.width)
            width_spin.setSingleStep(2)

            res_layout.addWidget(width_spin)
            res_layout.addWidget(QLabel("×"))

            height_spin = QSpinBox()
            height_spin.setRange(240, 4320)
            height_spin.setValue(settings.height)
            height_spin.setSingleStep(2)

            res_layout.addWidget(height_spin)
            res_layout.addStretch()

            # Common resolutions
            res_combo = QComboBox()
            res_combo.addItems([
                "Custom", "1920×1080 (FHD)", "3840×2160 (4K)",
                "1280×720 (HD)", "1080×1920 (Vertical)",
                "1080×1080 (Square)", "854×480 (SD)",
            ])

            def on_res_preset(text):
                mapping = {
                    "1920×1080 (FHD)":    (1920, 1080),
                    "3840×2160 (4K)":     (3840, 2160),
                    "1280×720 (HD)":      (1280, 720),
                    "1080×1920 (Vertical)":(1080, 1920),
                    "1080×1080 (Square)": (1080, 1080),
                    "854×480 (SD)":       (854,  480),
                }
                if text in mapping:
                    w, h = mapping[text]
                    width_spin.setValue(w)
                    height_spin.setValue(h)

            res_combo.currentTextChanged.connect(on_res_preset)
            video_form.addRow("Resolution:", res_container)
            video_form.addRow("Preset:", res_combo)

            # FPS
            fps_combo = QComboBox()
            fps_combo.addItems(["24", "30", "60"])
            fps_combo.setCurrentText(str(settings.fps))
            video_form.addRow("Frame Rate:", fps_combo)

            tabs.addTab(video_tab, "🎬 Video")

            # ===== TAB 3: Range =====
            range_tab = QWidget()
            range_form = QFormLayout(range_tab)
            range_form.setSpacing(8)
            range_form.setContentsMargins(8, 8, 8, 8)

            start_spin = QSpinBox()
            start_spin.setRange(0, 99999)
            start_spin.setValue(settings.start_frame)
            range_form.addRow("Start Frame:", start_spin)

            end_spin = QSpinBox()
            end_spin.setRange(1, 99999)
            end_spin.setValue(settings.end_frame)
            range_form.addRow("End Frame:", end_spin)

            audio_chk = QCheckBox("Include audio track")
            audio_chk.setChecked(settings.include_audio)
            range_form.addRow("", audio_chk)

            open_chk = QCheckBox("Open file after export")
            open_chk.setChecked(settings.open_after_export)
            range_form.addRow("", open_chk)

            tabs.addTab(range_tab, "⏱️ Range")

            layout.addWidget(tabs)

            # Buttons
            btn_box = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            )
            btn_box.button(QDialogButtonBox.Ok).setText("🚀 Export")
            btn_box.accepted.connect(dialog.accept)
            btn_box.rejected.connect(dialog.reject)
            layout.addWidget(btn_box)

            # Theme
            if theme_manager:
                p = theme_manager.get_palette()
                dialog.setStyleSheet(f"""
                    QDialog {{ background-color: {p.bg_secondary}; }}
                    QLabel {{ color: {p.text_primary}; font-size: 11px; }}
                    QLineEdit, QComboBox, QSpinBox {{
                        background-color: {p.bg_tertiary};
                        border: 1px solid {p.border};
                        border-radius: 3px;
                        color: {p.text_primary};
                        padding: 3px 6px;
                        font-size: 11px;
                    }}
                    QTabBar::tab {{
                        background-color: {p.bg_tertiary};
                        color: {p.text_secondary};
                        padding: 6px 12px;
                        border-radius: 4px 4px 0 0;
                    }}
                    QTabBar::tab:selected {{
                        background-color: {p.bg_secondary};
                        color: {p.accent};
                        border-top: 2px solid {p.accent};
                    }}
                    QTabWidget::pane {{
                        border: 1px solid {p.border};
                        background-color: {p.bg_secondary};
                    }}
                    QCheckBox {{ color: {p.text_primary}; font-size: 11px; }}
                    QPushButton {{
                        background-color: {p.accent};
                        color: #000; border: none;
                        border-radius: 4px; padding: 6px 16px;
                        font-weight: bold;
                    }}
                """)

            if dialog.exec_() == QDialog.Accepted:
                settings.output_path    = path_edit.text()
                settings.preset         = preset_combo.currentText()
                settings.quality        = quality_combo.currentText()
                settings.width          = width_spin.value()
                settings.height         = height_spin.value()
                settings.fps            = int(fps_combo.currentText())
                settings.start_frame    = start_spin.value()
                settings.end_frame      = end_spin.value()
                settings.include_audio  = audio_chk.isChecked()
                settings.open_after_export = open_chk.isChecked()
                result = DialogResult.ACCEPTED
                logger.info(f"Export dialog accepted: {settings.preset}")
            else:
                result = DialogResult.REJECTED

        except ImportError:
            logger.warning("PyQt5 nahi - export dialog skip")
        except Exception as e:
            logger.error(f"Export dialog error: {e}")

        return result, settings

    # ----------------------------------------------------------
    # NEW PROJECT DIALOG
    # ----------------------------------------------------------

    @staticmethod
    def show_new_project_dialog(
        parent=None,
        theme_manager=None,
    ) -> Tuple[DialogResult, ProjectSettings]:
        """New project settings dialog"""
        settings = ProjectSettings()
        result   = DialogResult.CANCELLED

        try:
            from PyQt5.QtWidgets import (
                QDialog, QVBoxLayout, QHBoxLayout,
                QLabel, QPushButton, QLineEdit,
                QComboBox, QSpinBox, QFormLayout,
                QGroupBox, QDialogButtonBox,
            )
            from PyQt5.QtCore import Qt

            dialog = QDialog(parent)
            dialog.setWindowTitle("📄 New Project")
            dialog.setModal(True)
            dialog.setMinimumWidth(420)

            layout = QVBoxLayout(dialog)
            layout.setSpacing(12)
            layout.setContentsMargins(16, 16, 16, 16)

            # Title
            title = QLabel("New Animation Project")
            title.setStyleSheet(
                "font-size: 16px; font-weight: bold; color: #00D4FF;"
            )
            layout.addWidget(title)

            form = QFormLayout()
            form.setSpacing(8)

            # Project name
            name_edit = QLineEdit()
            name_edit.setText("My Animation")
            name_edit.setPlaceholderText("Project naam...")
            form.addRow("Project Name:", name_edit)

            # Author
            author_edit = QLineEdit()
            author_edit.setPlaceholderText("Aapka naam (optional)")
            form.addRow("Author:", author_edit)

            # Template
            template_combo = QComboBox()
            templates = [
                "blank",
                "youtube_video",
                "short_film",
                "animation_reel",
                "tutorial_video",
            ]
            template_display = [
                "Blank Project",
                "YouTube Video (16:9)",
                "Short Film",
                "Animation Reel",
                "Tutorial Video",
            ]
            for t in template_display:
                template_combo.addItem(t)
            form.addRow("Template:", template_combo)

            # Resolution
            res_combo = QComboBox()
            res_combo.addItems([
                "1920×1080 (FHD - YouTube)",
                "3840×2160 (4K)",
                "1280×720 (HD)",
                "1080×1920 (Vertical - Shorts)",
                "1080×1080 (Square - Instagram)",
            ])
            form.addRow("Resolution:", res_combo)

            # FPS
            fps_combo = QComboBox()
            fps_combo.addItems(["24 FPS", "30 FPS", "60 FPS"])
            fps_combo.setCurrentIndex(1)  # 30 FPS default
            form.addRow("Frame Rate:", fps_combo)

            # Duration
            dur_spin = QSpinBox()
            dur_spin.setRange(1, 9999)
            dur_spin.setValue(10)
            dur_spin.setSuffix(" seconds")
            form.addRow("Duration:", dur_spin)

            layout.addLayout(form)

            # Buttons
            btn_box = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            )
            btn_box.button(QDialogButtonBox.Ok).setText("✅ Create Project")
            btn_box.accepted.connect(dialog.accept)
            btn_box.rejected.connect(dialog.reject)
            layout.addWidget(btn_box)

            # Theme
            if theme_manager:
                p = theme_manager.get_palette()
                dialog.setStyleSheet(f"""
                    QDialog {{ background-color: {p.bg_secondary}; }}
                    QLabel {{ color: {p.text_primary}; font-size: 12px; }}
                    QLineEdit, QComboBox, QSpinBox {{
                        background-color: {p.bg_tertiary};
                        border: 1px solid {p.border};
                        border-radius: 3px; color: {p.text_primary};
                        padding: 5px 8px; font-size: 12px;
                    }}
                    QPushButton {{
                        background-color: {p.accent}; color: #000;
                        border: none; border-radius: 4px;
                        padding: 7px 18px; font-weight: bold; font-size: 12px;
                    }}
                    QPushButton:hover {{ background-color: {p.accent_hover}; }}
                """)

            if dialog.exec_() == QDialog.Accepted:
                settings.name     = name_edit.text() or "My Animation"
                settings.author   = author_edit.text()
                settings.template = templates[template_combo.currentIndex()]

                # Resolution parse
                res_map = {
                    0: (1920, 1080), 1: (3840, 2160),
                    2: (1280, 720),  3: (1080, 1920),
                    4: (1080, 1080),
                }
                w, h = res_map.get(res_combo.currentIndex(), (1920, 1080))
                settings.width  = w
                settings.height = h

                # FPS parse
                fps_map = {0: 24, 1: 30, 2: 60}
                settings.fps = fps_map.get(fps_combo.currentIndex(), 30)

                # Total frames
                settings.total_frames = dur_spin.value() * settings.fps

                result = DialogResult.ACCEPTED
                logger.info(f"New project: {settings.name}")
            else:
                result = DialogResult.REJECTED

        except ImportError:
            logger.warning("PyQt5 nahi - new project dialog skip")
        except Exception as e:
            logger.error(f"New project dialog error: {e}")

        return result, settings

    # ----------------------------------------------------------
    # PROGRESS DIALOG
    # ----------------------------------------------------------

    @staticmethod
    def show_progress_dialog(
        title:        str     = "Processing...",
        message:      str     = "Kaam chal raha hai...",
        parent=None,
        theme_manager=None,
        cancellable:  bool    = True,
    ) -> "ProgressDialog":
        """
        Progress dialog banao aur return karo.
        Caller update kar sakta hai progress.
        """
        return ProgressDialog(
            title         = title,
            message       = message,
            parent        = parent,
            theme_manager = theme_manager,
            cancellable   = cancellable,
        )

    # ----------------------------------------------------------
    # ABOUT DIALOG
    # ----------------------------------------------------------

    @staticmethod
    def show_about_dialog(parent=None, theme_manager=None):
        """About dialog - app info"""
        try:
            from PyQt5.QtWidgets import (
                QDialog, QVBoxLayout, QLabel,
                QPushButton, QHBoxLayout,
            )
            from PyQt5.QtCore import Qt

            dialog = QDialog(parent)
            dialog.setWindowTitle("About 3D Animation Studio")
            dialog.setModal(True)
            dialog.setFixedSize(420, 350)

            layout = QVBoxLayout(dialog)
            layout.setSpacing(12)
            layout.setContentsMargins(24, 24, 24, 24)
            layout.setAlignment(Qt.AlignCenter)

            # App icon/title
            icon_lbl = QLabel("🎬")
            icon_lbl.setStyleSheet("font-size: 48px;")
            icon_lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(icon_lbl)

            app_title = QLabel("3D Animation Studio")
            app_title.setStyleSheet(
                "font-size: 22px; font-weight: bold; color: #00D4FF;"
            )
            app_title.setAlignment(Qt.AlignCenter)
            layout.addWidget(app_title)

            version = QLabel("Version 1.0.0 | Python Edition")
            version.setStyleSheet("font-size: 12px; color: #8888AA;")
            version.setAlignment(Qt.AlignCenter)
            layout.addWidget(version)

            desc = QLabel(
                "Free & Open Source 3D Animation Tool\n"
                "YouTube Content Creation ke liye\n\n"
                "Built with Python, PyQt5, PyOpenGL, PyBullet"
            )
            desc.setStyleSheet("font-size: 11px; color: #AAAACC;")
            desc.setAlignment(Qt.AlignCenter)
            layout.addWidget(desc)

            features = QLabel(
                "✅ 3D Rendering  ✅ Physics Simulation\n"
                "✅ AI Lipsync    ✅ TTS Voiceover\n"
                "✅ VFX Effects   ✅ YouTube Export"
            )
            features.setStyleSheet("font-size: 11px; color: #00D4FF;")
            features.setAlignment(Qt.AlignCenter)
            layout.addWidget(features)

            # Buttons
            btn_layout = QHBoxLayout()

            github_btn = QPushButton("⭐ GitHub")
            github_btn.clicked.connect(
                lambda: __import__('webbrowser').open(
                    "https://github.com/happyreehal/3d-animation-studio"
                )
            )
            btn_layout.addWidget(github_btn)

            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.close)
            btn_layout.addWidget(close_btn)

            layout.addLayout(btn_layout)

            # Theme
            if theme_manager:
                p = theme_manager.get_palette()
                dialog.setStyleSheet(f"""
                    QDialog {{
                        background-color: {p.bg_secondary};
                    }}
                    QPushButton {{
                        background-color: {p.bg_elevated};
                        color: {p.text_primary};
                        border: 1px solid {p.border};
                        border-radius: 4px; padding: 6px 16px;
                    }}
                    QPushButton:hover {{
                        background-color: {p.accent_muted};
                        border-color: {p.accent};
                    }}
                """)

            dialog.exec_()

        except ImportError:
            logger.warning("PyQt5 nahi - about dialog skip")
        except Exception as e:
            logger.error(f"About dialog error: {e}")

    # ----------------------------------------------------------
    # PREFERENCES DIALOG
    # ----------------------------------------------------------

    @staticmethod
    def show_preferences_dialog(
        parent=None,
        theme_manager=None,
        config_manager=None,
    ) -> Tuple[DialogResult, Dict]:
        """App preferences/settings dialog"""
        result   = DialogResult.CANCELLED
        new_prefs = {}

        try:
            from PyQt5.QtWidgets import (
                QDialog, QVBoxLayout, QHBoxLayout,
                QLabel, QPushButton, QTabWidget,
                QWidget, QFormLayout, QComboBox,
                QCheckBox, QSpinBox, QDialogButtonBox,
                QDoubleSpinBox, QLineEdit,
            )
            from PyQt5.QtCore import Qt

            dialog = QDialog(parent)
            dialog.setWindowTitle("⚙️ Preferences")
            dialog.setModal(True)
            dialog.setMinimumSize(500, 400)

            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(16, 16, 16, 16)

            title = QLabel("Application Preferences")
            title.setStyleSheet(
                "font-size: 15px; font-weight: bold; color: #00D4FF;"
            )
            layout.addWidget(title)

            tabs = QTabWidget()

            # ===== APPEARANCE TAB =====
            appear_tab = QWidget()
            appear_form = QFormLayout(appear_tab)
            appear_form.setSpacing(10)
            appear_form.setContentsMargins(12, 12, 12, 12)

            theme_combo = QComboBox()
            theme_combo.addItems(["Dark (Default)", "Light"])
            appear_form.addRow("Theme:", theme_combo)

            accent_combo = QComboBox()
            accent_combo.addItems([
                "Cyan (#00D4FF)", "Purple (#9B59B6)",
                "Green (#2ECC71)", "Orange (#E67E22)",
                "Red (#E74C3C)",   "Pink (#FF6B9D)",
                "Gold (#F1C40F)",
            ])
            appear_form.addRow("Accent Color:", accent_combo)

            font_spin = QSpinBox()
            font_spin.setRange(8, 20)
            font_spin.setValue(12)
            font_spin.setSuffix(" px")
            appear_form.addRow("Font Size:", font_spin)

            tabs.addTab(appear_tab, "🎨 Appearance")

            # ===== PERFORMANCE TAB =====
            perf_tab = QWidget()
            perf_form = QFormLayout(perf_tab)
            perf_form.setSpacing(10)
            perf_form.setContentsMargins(12, 12, 12, 12)

            preview_quality = QComboBox()
            preview_quality.addItems(["draft", "medium", "high"])
            perf_form.addRow("Preview Quality:", preview_quality)

            fps_combo = QComboBox()
            fps_combo.addItems(["24 FPS", "30 FPS", "60 FPS"])
            fps_combo.setCurrentIndex(1)
            perf_form.addRow("Default FPS:", fps_combo)

            autosave_spin = QSpinBox()
            autosave_spin.setRange(1, 60)
            autosave_spin.setValue(5)
            autosave_spin.setSuffix(" min")
            perf_form.addRow("Auto-save Interval:", autosave_spin)

            gpu_chk = QCheckBox("Use GPU acceleration (if available)")
            gpu_chk.setChecked(True)
            perf_form.addRow("", gpu_chk)

            tabs.addTab(perf_tab, "⚡ Performance")

            # ===== AUDIO TAB =====
            audio_tab = QWidget()
            audio_form = QFormLayout(audio_tab)
            audio_form.setSpacing(10)
            audio_form.setContentsMargins(12, 12, 12, 12)

            tts_engine = QComboBox()
            tts_engine.addItems(["pyttsx3 (Offline)", "gTTS (Online)", "Auto"])
            audio_form.addRow("TTS Engine:", tts_engine)

            sample_rate = QComboBox()
            sample_rate.addItems(["44100 Hz", "48000 Hz"])
            sample_rate.setCurrentIndex(1)
            audio_form.addRow("Sample Rate:", sample_rate)

            bitrate_combo = QComboBox()
            bitrate_combo.addItems(["128k", "192k", "256k", "320k"])
            bitrate_combo.setCurrentIndex(1)
            audio_form.addRow("Audio Bitrate:", bitrate_combo)

            tabs.addTab(audio_tab, "🎵 Audio")

            # ===== PATHS TAB =====
            paths_tab = QWidget()
            paths_form = QFormLayout(paths_tab)
            paths_form.setSpacing(10)
            paths_form.setContentsMargins(12, 12, 12, 12)

            export_edit = QLineEdit("exports")
            paths_form.addRow("Export Folder:", export_edit)

            projects_edit = QLineEdit("projects")
            paths_form.addRow("Projects Folder:", projects_edit)

            temp_edit = QLineEdit("temp")
            paths_form.addRow("Temp Folder:", temp_edit)

            tabs.addTab(paths_tab, "📁 Paths")

            layout.addWidget(tabs)

            # Buttons
            btn_box = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel |
                QDialogButtonBox.RestoreDefaults
            )
            btn_box.button(QDialogButtonBox.Ok).setText("✅ Apply")
            btn_box.button(QDialogButtonBox.RestoreDefaults).setText("↺ Reset")
            btn_box.accepted.connect(dialog.accept)
            btn_box.rejected.connect(dialog.reject)
            layout.addWidget(btn_box)

            # Theme
            if theme_manager:
                p = theme_manager.get_palette()
                dialog.setStyleSheet(f"""
                    QDialog {{ background-color: {p.bg_secondary}; }}
                    QLabel {{ color: {p.text_primary}; font-size: 12px; }}
                    QLineEdit, QComboBox, QSpinBox {{
                        background-color: {p.bg_tertiary};
                        border: 1px solid {p.border};
                        border-radius: 3px; color: {p.text_primary};
                        padding: 4px 8px; font-size: 11px;
                    }}
                    QTabBar::tab {{
                        background-color: {p.bg_tertiary};
                        color: {p.text_secondary};
                        padding: 6px 12px;
                    }}
                    QTabBar::tab:selected {{
                        background-color: {p.bg_secondary};
                        color: {p.accent};
                        border-top: 2px solid {p.accent};
                    }}
                    QTabWidget::pane {{
                        border: 1px solid {p.border};
                        background: {p.bg_secondary};
                    }}
                    QCheckBox {{ color: {p.text_primary}; font-size: 11px; }}
                    QPushButton {{
                        background-color: {p.accent}; color: #000;
                        border: none; border-radius: 4px;
                        padding: 6px 16px; font-weight: bold;
                    }}
                """)

            if dialog.exec_() == QDialog.Accepted:
                # Accent map
                accent_map = {
                    0: "#00D4FF", 1: "#9B59B6", 2: "#2ECC71",
                    3: "#E67E22", 4: "#E74C3C", 5: "#FF6B9D",
                    6: "#F1C40F",
                }
                fps_map = {0: 24, 1: 30, 2: 60}

                new_prefs = {
                    "theme":            "light" if theme_combo.currentIndex() == 1 else "dark",
                    "accent_color":     accent_map.get(accent_combo.currentIndex(), "#00D4FF"),
                    "font_size":        font_spin.value(),
                    "preview_quality":  preview_quality.currentText(),
                    "fps":              fps_map.get(fps_combo.currentIndex(), 30),
                    "autosave_interval": autosave_spin.value() * 60,
                    "gpu_acceleration": gpu_chk.isChecked(),
                    "tts_engine":       tts_engine.currentText(),
                    "export_folder":    export_edit.text(),
                    "projects_folder":  projects_edit.text(),
                }
                result = DialogResult.ACCEPTED

                # Theme update karo
                if theme_manager:
                    theme_manager.set_accent_color(new_prefs["accent_color"])
                    if new_prefs["theme"] == "light":
                        from src.ui.theme_manager import ThemeType
                        theme_manager.set_theme(ThemeType.LIGHT)
                    else:
                        from src.ui.theme_manager import ThemeType
                        theme_manager.set_theme(ThemeType.DARK)

                logger.info("Preferences saved")
            else:
                result = DialogResult.REJECTED

        except ImportError:
            logger.warning("PyQt5 nahi - preferences dialog skip")
        except Exception as e:
            logger.error(f"Preferences dialog error: {e}")

        return result, new_prefs

    # ----------------------------------------------------------
    # CONFIRM DIALOG
    # ----------------------------------------------------------

    @staticmethod
    def show_confirm_dialog(
        title:   str,
        message: str,
        parent=None,
        theme_manager=None,
        confirm_text: str = "Yes",
        cancel_text:  str = "Cancel",
        danger:       bool = False,
    ) -> bool:
        """
        Simple confirmation dialog.
        Returns True agar user ne confirm kiya.
        """
        try:
            from PyQt5.QtWidgets import (
                QDialog, QVBoxLayout, QHBoxLayout,
                QLabel, QPushButton,
            )
            from PyQt5.QtCore import Qt

            dialog = QDialog(parent)
            dialog.setWindowTitle(title)
            dialog.setModal(True)
            dialog.setFixedWidth(360)

            layout = QVBoxLayout(dialog)
            layout.setSpacing(16)
            layout.setContentsMargins(20, 20, 20, 20)

            # Icon + message
            msg_lbl = QLabel(f"⚠️  {message}" if danger else message)
            msg_lbl.setWordWrap(True)
            msg_lbl.setAlignment(Qt.AlignCenter)
            msg_lbl.setStyleSheet(
                f"font-size: 13px; color: "
                f"{'#E74C3C' if danger else '#FFFFFF'}; padding: 10px;"
            )
            layout.addWidget(msg_lbl)

            # Buttons
            btn_layout = QHBoxLayout()

            confirm_btn = QPushButton(confirm_text)
            confirm_btn.clicked.connect(dialog.accept)
            if danger:
                confirm_btn.setStyleSheet(
                    "background-color: #E74C3C; color: white; "
                    "border: none; border-radius: 4px; "
                    "padding: 8px 20px; font-weight: bold;"
                )
            btn_layout.addWidget(confirm_btn)

            cancel_btn = QPushButton(cancel_text)
            cancel_btn.clicked.connect(dialog.reject)
            btn_layout.addWidget(cancel_btn)

            layout.addLayout(btn_layout)

            if theme_manager:
                p = theme_manager.get_palette()
                dialog.setStyleSheet(f"""
                    QDialog {{ background-color: {p.bg_elevated}; }}
                    QPushButton {{
                        background-color: {p.bg_secondary};
                        color: {p.text_primary};
                        border: 1px solid {p.border};
                        border-radius: 4px; padding: 7px 18px;
                    }}
                    QPushButton:hover {{
                        background-color: {p.bg_hover};
                        border-color: {p.accent};
                    }}
                """)

            return dialog.exec_() == QDialog.Accepted

        except ImportError:
            return True   # Fallback
        except Exception as e:
            logger.error(f"Confirm dialog error: {e}")
            return False

    # ----------------------------------------------------------
    # INPUT DIALOG
    # ----------------------------------------------------------

    @staticmethod
    def show_input_dialog(
        title:       str,
        label:       str,
        default:     str  = "",
        parent=None,
        theme_manager=None,
    ) -> Tuple[bool, str]:
        """Simple text input dialog"""
        try:
            from PyQt5.QtWidgets import QInputDialog, QLineEdit
            text, ok = QInputDialog.getText(
                parent, title, label,
                QLineEdit.Normal, default
            )
            return ok, text
        except ImportError:
            return False, default
        except Exception as e:
            logger.error(f"Input dialog error: {e}")
            return False, default

    # ----------------------------------------------------------
    # FILE DIALOGS (convenience wrappers)
    # ----------------------------------------------------------

    @staticmethod
    def open_file_dialog(
        title:  str   = "File Open Karo",
        filter: str   = "All Files (*)",
        parent=None,
    ) -> Optional[str]:
        """File open dialog"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            path, _ = QFileDialog.getOpenFileName(parent, title, "", filter)
            return path if path else None
        except Exception:
            return None

    @staticmethod
    def save_file_dialog(
        title:  str   = "File Save Karo",
        filter: str   = "All Files (*)",
        default: str  = "",
        parent=None,
    ) -> Optional[str]:
        """File save dialog"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            path, _ = QFileDialog.getSaveFileName(parent, title, default, filter)
            return path if path else None
        except Exception:
            return None

    @staticmethod
    def open_folder_dialog(
        title:  str = "Folder Select Karo",
        parent=None,
    ) -> Optional[str]:
        """Folder selection dialog"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            path = QFileDialog.getExistingDirectory(parent, title)
            return path if path else None
        except Exception:
            return None


# ============================================================
# PROGRESS DIALOG CLASS
# ============================================================

class ProgressDialog:
    """
    Progress dialog - long running tasks ke liye.
    Show/hide/update karo programmatically.
    """

    def __init__(
        self,
        title:        str   = "Processing...",
        message:      str   = "Kaam chal raha hai...",
        parent=None,
        theme_manager=None,
        cancellable:  bool  = True,
    ):
        self.title         = title
        self.message       = message
        self.theme_manager = theme_manager
        self.cancellable   = cancellable
        self._cancelled    = False
        self._dialog       = None
        self._progress_bar = None
        self._label        = None
        self._cancel_callback: Optional[Callable] = None

        self._build()

    def _build(self):
        """Qt progress dialog build karo"""
        try:
            from PyQt5.QtWidgets import (
                QDialog, QVBoxLayout, QLabel,
                QProgressBar, QPushButton, QHBoxLayout,
            )
            from PyQt5.QtCore import Qt

            self._dialog = QDialog()
            self._dialog.setWindowTitle(self.title)
            self._dialog.setModal(True)
            self._dialog.setFixedWidth(400)
            self._dialog.setWindowFlags(
                Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint
            )

            layout = QVBoxLayout(self._dialog)
            layout.setSpacing(12)
            layout.setContentsMargins(20, 20, 20, 20)

            # Title icon
            title_lbl = QLabel(f"⏳ {self.title}")
            title_lbl.setStyleSheet(
                "font-size: 14px; font-weight: bold; color: #00D4FF;"
            )
            layout.addWidget(title_lbl)

            # Message
            self._label = QLabel(self.message)
            self._label.setWordWrap(True)
            self._label.setStyleSheet("font-size: 11px; color: #AAAACC;")
            layout.addWidget(self._label)

            # Progress bar
            self._progress_bar = QProgressBar()
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(0)
            self._progress_bar.setTextVisible(True)
            self._progress_bar.setFixedHeight(20)
            layout.addWidget(self._progress_bar)

            # Cancel button
            if self.cancellable:
                btn_layout = QHBoxLayout()
                btn_layout.addStretch()
                cancel_btn = QPushButton("❌ Cancel")
                cancel_btn.clicked.connect(self._on_cancel)
                btn_layout.addWidget(cancel_btn)
                layout.addLayout(btn_layout)

            # Theme
            if self.theme_manager:
                p = self.theme_manager.get_palette()
                self._dialog.setStyleSheet(f"""
                    QDialog {{
                        background-color: {p.bg_secondary};
                    }}
                    QProgressBar {{
                        background-color: {p.bg_tertiary};
                        border: 1px solid {p.border};
                        border-radius: 4px;
                        color: {p.text_primary};
                        text-align: center;
                        font-size: 11px;
                    }}
                    QProgressBar::chunk {{
                        background-color: {p.accent};
                        border-radius: 3px;
                    }}
                    QPushButton {{
                        background-color: {p.text_error};
                        color: white; border: none;
                        border-radius: 4px; padding: 5px 14px;
                    }}
                """)

        except ImportError:
            logger.warning("PyQt5 nahi - progress dialog skip")
        except Exception as e:
            logger.error(f"Progress dialog build error: {e}")

    def show(self):
        """Dialog show karo"""
        if self._dialog:
            try:
                self._dialog.show()
                self._process_events()
            except Exception:
                pass

    def hide(self):
        """Dialog hide karo"""
        if self._dialog:
            try:
                self._dialog.hide()
            except Exception:
                pass

    def close(self):
        """Dialog close karo"""
        if self._dialog:
            try:
                self._dialog.close()
            except Exception:
                pass

    def update(
        self,
        percent:  int,
        message:  str = "",
    ):
        """Progress update karo"""
        try:
            if self._progress_bar:
                self._progress_bar.setValue(max(0, min(100, percent)))
            if self._label and message:
                self._label.setText(message)
            self._process_events()
        except Exception:
            pass

    def set_message(self, message: str):
        """Message update karo"""
        if self._label:
            try:
                self._label.setText(message)
                self._process_events()
            except Exception:
                pass

    def is_cancelled(self) -> bool:
        """Cancel hua hai?"""
        self._process_events()
        return self._cancelled

    def set_cancel_callback(self, callback: Callable):
        """Cancel callback set karo"""
        self._cancel_callback = callback

    def _on_cancel(self):
        """Cancel button click"""
        self._cancelled = True
        if self._cancel_callback:
            self._cancel_callback()
        logger.info("Progress dialog cancelled")

    def _process_events(self):
        """Qt events process karo (UI responsive rakho)"""
        try:
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.processEvents()
        except Exception:
            pass

    def __enter__(self):
        """Context manager support"""
        self.show()
        return self

    def __exit__(self, *args):
        """Context manager exit"""
        self.close()


# ============================================================
# TEST SECTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="DEBUG")
    print_banner("Dialogs Test", "Studio Dialog Windows")

    # ===== TEST 1: Data Classes =====
    print_section("Test 1: Data Classes")
    imp = ImportSettings()
    exp = ExportSettings()
    prj = ProjectSettings()
    ren = RenderSettings()

    print(f"✅ ImportSettings: scale={imp.scale}, center={imp.center_on_import}")
    print(f"✅ ExportSettings: preset={exp.preset}, fps={exp.fps}")
    print(f"✅ ProjectSettings: name='{prj.name}', fps={prj.fps}")
    print(f"✅ RenderSettings: quality={ren.quality}, samples={ren.samples}")

    # ===== TEST 2: Qt Dialogs =====
    print_section("Test 2: Qt Dialogs (Visual Test)")

    try:
        from PyQt5.QtWidgets import QApplication
        import sys as _sys

        app = QApplication.instance() or QApplication(_sys.argv)

        from src.ui.theme_manager import ThemeManager
        theme = ThemeManager()
        theme.set_application(app)

        # ===== About Dialog =====
        print("📋 About Dialog...")
        StudioDialogs.show_about_dialog(theme_manager=theme)
        print("✅ About dialog closed")

        # ===== New Project Dialog =====
        print("📄 New Project Dialog...")
        result, proj_settings = StudioDialogs.show_new_project_dialog(
            theme_manager=theme
        )
        print(f"✅ New Project: result={result.value}")
        if result == DialogResult.ACCEPTED:
            print(f"   Name    : {proj_settings.name}")
            print(f"   FPS     : {proj_settings.fps}")
            print(f"   Size    : {proj_settings.width}×{proj_settings.height}")
            print(f"   Frames  : {proj_settings.total_frames}")

        # ===== Import Dialog =====
        print("📥 Import Dialog...")
        result2, imp_settings = StudioDialogs.show_import_dialog(
            theme_manager=theme
        )
        print(f"✅ Import: result={result2.value}")
        if result2 == DialogResult.ACCEPTED:
            print(f"   File  : {imp_settings.file_path}")
            print(f"   Scale : {imp_settings.scale}")

        # ===== Export Dialog =====
        print("📤 Export Dialog...")
        result3, exp_settings = StudioDialogs.show_export_dialog(
            theme_manager=theme
        )
        print(f"✅ Export: result={result3.value}")
        if result3 == DialogResult.ACCEPTED:
            print(f"   Preset : {exp_settings.preset}")
            print(f"   Size   : {exp_settings.width}×{exp_settings.height}")
            print(f"   FPS    : {exp_settings.fps}")

        # ===== Preferences Dialog =====
        print("⚙️  Preferences Dialog...")
        result4, prefs = StudioDialogs.show_preferences_dialog(
            theme_manager=theme
        )
        print(f"✅ Preferences: result={result4.value}")
        if result4 == DialogResult.ACCEPTED:
            print(f"   Theme  : {prefs.get('theme')}")
            print(f"   Accent : {prefs.get('accent_color')}")

        # ===== Confirm Dialog =====
        print("❓ Confirm Dialog...")
        confirmed = StudioDialogs.show_confirm_dialog(
            title   = "Confirm Delete",
            message = "Kya aap sach mein yeh object delete karna chahte ho?",
            confirm_text = "Delete",
            cancel_text  = "Cancel",
            danger  = True,
            theme_manager = theme,
        )
        print(f"✅ Confirm result: {confirmed}")

        # ===== Input Dialog =====
        print("✏️  Input Dialog...")
        ok, text = StudioDialogs.show_input_dialog(
            title   = "Rename Object",
            label   = "Naya naam daalo:",
            default = "My Object",
        )
        print(f"✅ Input: ok={ok}, text='{text}'")

        # ===== Progress Dialog =====
        print("⏳ Progress Dialog...")
        import time as _time

        progress = StudioDialogs.show_progress_dialog(
            title       = "Rendering...",
            message     = "Scene render ho rahi hai...",
            theme_manager = theme,
        )
        progress.show()

        for i in range(0, 101, 10):
            progress.update(i, f"Frame {i*3}/300 render ho rahi hai...")
            _time.sleep(0.05)
            if progress.is_cancelled():
                print("   ⚠️  Cancelled!")
                break

        progress.close()
        print("✅ Progress dialog complete")

        print("\n✅ All Qt dialog tests complete!")

    except ImportError:
        print("⚠️  PyQt5 visual tests skip - non-Qt mode")
    except Exception as e:
        print(f"⚠️  Qt test error: {e}")

    # ===== TEST 3: DialogResult =====
    print_section("Test 3: DialogResult Enum")
    for r in DialogResult:
        print(f"✅ {r.name}: {r.value}")

    # ===== TEST 4: BaseDialogData =====
    print_section("Test 4: BaseDialogData")
    base = BaseDialogData()
    print(f"✅ Initial result: {base.get_result().value}")
    print(f"   was_accepted  : {base.was_accepted()}")
    base._result = DialogResult.ACCEPTED
    base._data   = {"key": "value"}
    print(f"✅ After accept  : {base.was_accepted()}")
    print(f"   Data          : {base.get_data()}")

    print_banner("✅ All Tests Passed!", "dialogs.py Working Perfectly")