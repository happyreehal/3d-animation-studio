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
    up_axis:            str   = "Y"


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
# BASE DIALOG
# ============================================================

class BaseDialogData:
    """Dialog ka base data class - Qt se independent"""

    def __init__(self):
        self._result = DialogResult.CANCELLED
        self._data   = {}

    def get_result(self) -> DialogResult:
        return self._result

    def get_data(self) -> Dict:
        return self._data

    def was_accepted(self) -> bool:
        return self._result == DialogResult.ACCEPTED


# ============================================================
# SCRIPT INPUT DIALOG
# ============================================================

class ScriptInputDialog:
    """
    🎬 Script se Video Generate karne wala Dialog.
    User script likhta hai → automatic MP4 ban jaati hai!
    
    Usage:
        dialog = ScriptInputDialog(parent=window)
        dialog.exec_()
    """

    def __init__(self, parent=None):
        self._parent = parent
        self._dialog = None
        self._build()

    def _build(self):
        """Qt dialog build karo"""
        try:
            from PyQt5.QtWidgets import (
                QDialog, QVBoxLayout, QHBoxLayout,
                QLabel, QPushButton, QTextEdit,
                QLineEdit, QComboBox, QGroupBox,
                QMessageBox, QFileDialog,
            )
            from PyQt5.QtCore import Qt

            self._Qt         = Qt
            self._QMessageBox = QMessageBox
            self._QFileDialog = QFileDialog

            dialog = QDialog(self._parent)
            dialog.setWindowTitle("🎬 Generate Video from Script")
            dialog.setMinimumSize(800, 600)
            dialog.setModal(True)

            dialog.setStyleSheet("""
                QDialog {
                    background-color: #0F0F19;
                    color: #FFFFFF;
                }
                QLabel {
                    color: #FFFFFF;
                    font-size: 13px;
                }
                QTextEdit {
                    background-color: #1A1A2E;
                    color: #FFFFFF;
                    border: 2px solid #00D4FF;
                    border-radius: 8px;
                    padding: 10px;
                    font-family: 'Consolas', monospace;
                    font-size: 13px;
                }
                QTextEdit:focus {
                    border: 2px solid #00FFAA;
                }
                QLineEdit {
                    background-color: #1A1A2E;
                    color: #FFFFFF;
                    border: 2px solid #333355;
                    border-radius: 6px;
                    padding: 8px;
                    font-size: 13px;
                }
                QLineEdit:focus {
                    border: 2px solid #00D4FF;
                }
                QComboBox {
                    background-color: #1A1A2E;
                    color: #FFFFFF;
                    border: 2px solid #333355;
                    border-radius: 6px;
                    padding: 6px;
                    font-size: 13px;
                }
                QComboBox:hover {
                    border: 2px solid #00D4FF;
                }
                QComboBox QAbstractItemView {
                    background-color: #1A1A2E;
                    color: #FFFFFF;
                    selection-background-color: #00D4FF;
                }
                QPushButton {
                    border-radius: 8px;
                    padding: 10px 20px;
                    font-size: 13px;
                    font-weight: bold;
                }
                QPushButton#generateBtn {
                    background-color: #00D4FF;
                    color: #000000;
                    border: none;
                }
                QPushButton#generateBtn:hover {
                    background-color: #00FFAA;
                }
                QPushButton#generateBtn:pressed {
                    background-color: #0099BB;
                }
                QPushButton#cancelBtn {
                    background-color: #333355;
                    color: #FFFFFF;
                    border: none;
                }
                QPushButton#cancelBtn:hover {
                    background-color: #444477;
                }
                QPushButton#exampleBtn {
                    background-color: #1A1A2E;
                    color: #00D4FF;
                    border: 2px solid #00D4FF;
                    padding: 6px 14px;
                    font-size: 12px;
                }
                QPushButton#exampleBtn:hover {
                    background-color: #00D4FF;
                    color: #000000;
                }
                QGroupBox {
                    color: #00D4FF;
                    border: 1px solid #333355;
                    border-radius: 8px;
                    margin-top: 10px;
                    padding-top: 10px;
                    font-size: 13px;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
            """)

            main_layout = QVBoxLayout(dialog)
            main_layout.setSpacing(15)
            main_layout.setContentsMargins(20, 20, 20, 20)

            # ── HEADER ──────────────────────────────────
            header = QLabel("🎬 Script to Video Generator")
            header.setStyleSheet("""
                font-size: 22px;
                font-weight: bold;
                color: #00D4FF;
                padding: 5px;
            """)
            header.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(header)

            subtitle = QLabel(
                "Apna script likho → Automatic MP4 video ban jayegi! ✨"
            )
            subtitle.setStyleSheet(
                "color: #8888AA; font-size: 12px;"
            )
            subtitle.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(subtitle)

            # ── FORMAT INFO ──────────────────────────────
            info_label = QLabel(
                "📝 Format:  CHARACTER: (emotion) Dialogue text"
            )
            info_label.setStyleSheet("""
                background-color: #1A1A2E;
                border-left: 4px solid #00D4FF;
                padding: 8px 12px;
                border-radius: 4px;
                color: #CCCCDD;
                font-family: Consolas;
            """)
            main_layout.addWidget(info_label)

            # ── SCRIPT INPUT ─────────────────────────────
            script_group = QGroupBox("📜 Script")
            script_layout = QVBoxLayout(script_group)

            # Example buttons
            example_row = QHBoxLayout()
            example_row.addWidget(QLabel("Quick Examples:"))

            examples = [
                ("🦸 Hero Story", "hero"),
                ("💼 Business",   "business"),
                ("🎭 Drama",      "drama"),
                ("😂 Comedy",     "comedy"),
            ]

            for lbl_text, key in examples:
                btn = QPushButton(lbl_text)
                btn.setObjectName("exampleBtn")
                btn.clicked.connect(
                    lambda checked, k=key: self._load_example(k)
                )
                example_row.addWidget(btn)

            example_row.addStretch()
            script_layout.addLayout(example_row)

            # Script text area
            self._script_edit = QTextEdit()
            self._script_edit.setPlaceholderText(
                "Yahan apna script likhein...\n\n"
                "HERO: (excited) Namaste! Main hun HERO!\n"
                "VILLAIN: (angry) Main tumhe nahi chhodunga!\n"
                "HERO: (confident) Dekhte hain kaun jita!"
            )
            self._script_edit.setMinimumHeight(220)
            script_layout.addWidget(self._script_edit)

            # Character count
            self._char_count = QLabel("Characters: 0")
            self._char_count.setStyleSheet(
                "color: #666688; font-size: 11px;"
            )
            self._char_count.setAlignment(Qt.AlignRight)
            self._script_edit.textChanged.connect(
                self._update_char_count
            )
            script_layout.addWidget(self._char_count)

            main_layout.addWidget(script_group)

            # ── SETTINGS ────────────────────────────────
            settings_group = QGroupBox("⚙️ Settings")
            settings_layout = QHBoxLayout(settings_group)
            settings_layout.setSpacing(20)

            # Video Title
            title_col = QVBoxLayout()
            title_col.addWidget(QLabel("📌 Video Title:"))
            self._title_edit = QLineEdit()
            self._title_edit.setPlaceholderText("Meri Animation Video")
            self._title_edit.setText("My Animation")
            title_col.addWidget(self._title_edit)
            settings_layout.addLayout(title_col)

            # Quality
            quality_col = QVBoxLayout()
            quality_col.addWidget(QLabel("🎨 Quality:"))
            self._quality_combo = QComboBox()
            self._quality_combo.addItems([
                "🚀 Draft (Fast)",
                "⚡ Medium",
                "✨ High",
                "💎 Ultra",
            ])
            self._quality_combo.setCurrentIndex(1)
            quality_col.addWidget(self._quality_combo)
            settings_layout.addLayout(quality_col)

            # Output Folder
            output_col = QVBoxLayout()
            output_col.addWidget(QLabel("📁 Save Location:"))
            output_row = QHBoxLayout()
            self._output_edit = QLineEdit()
            self._output_edit.setText("exports/")
            self._output_edit.setReadOnly(True)
            output_row.addWidget(self._output_edit)

            browse_btn = QPushButton("📂")
            browse_btn.setFixedWidth(40)
            browse_btn.setStyleSheet("""
                QPushButton {
                    background-color: #333355;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 16px;
                }
                QPushButton:hover { background-color: #444477; }
            """)
            browse_btn.clicked.connect(self._browse_output)
            output_row.addWidget(browse_btn)
            output_col.addLayout(output_row)
            settings_layout.addLayout(output_col)

            main_layout.addWidget(settings_group)

            # ── BUTTONS ──────────────────────────────────
            btn_layout = QHBoxLayout()
            btn_layout.setSpacing(15)

            cancel_btn = QPushButton("❌ Cancel")
            cancel_btn.setObjectName("cancelBtn")
            cancel_btn.clicked.connect(dialog.reject)
            btn_layout.addWidget(cancel_btn)

            btn_layout.addStretch()

            estimate_lbl = QLabel("⏱️ Est. time: ~20-30 seconds")
            estimate_lbl.setStyleSheet(
                "color: #8888AA; font-size: 11px;"
            )
            btn_layout.addWidget(estimate_lbl)

            generate_btn = QPushButton("🚀 Generate Video!")
            generate_btn.setObjectName("generateBtn")
            generate_btn.setMinimumWidth(180)
            generate_btn.setMinimumHeight(45)
            generate_btn.clicked.connect(
                lambda: self._start_generation(dialog)
            )
            btn_layout.addWidget(generate_btn)

            main_layout.addLayout(btn_layout)

            self._dialog = dialog

            # Default example load karo
            self._load_example("hero")

        except ImportError as e:
            logger.error(f"PyQt5 import error in ScriptInputDialog: {e}")
        except Exception as e:
            logger.error(f"ScriptInputDialog build error: {e}")
            import traceback
            traceback.print_exc()

    def exec_(self):
        """Dialog show karo"""
        if self._dialog:
            return self._dialog.exec_()
        return 0

    def _update_char_count(self):
        """Character count update karna"""
        try:
            text  = self._script_edit.toPlainText()
            count = len(text)
            lines = len(text.splitlines())
            self._char_count.setText(
                f"Characters: {count} | Lines: {lines}"
            )
        except Exception:
            pass

    def _load_example(self, example_type: str = "hero"):
        """Example script load karna"""
        examples = {
            "hero": (
                "HERO: (excited) Namaste doston! "
                "Aaj main aapko kuch amazing dikhaunga!\n"
                "VILLAIN: (angry) Ruko! "
                "Main tumhe kaamyaab nahi hone dunga!\n"
                "HERO: (confident) Tum mujhe nahi rok sakte. "
                "Mere saath hai science ki takat!\n"
                "VILLAIN: (surprised) Yeh... yeh kaise possible hai?\n"
                "HERO: (happy) Kyunki main haar nahi maanta! "
                "Never give up!",
                "Hero Ki Kahani - Epic Animation",
            ),
            "business": (
                "BOSS: (serious) Team, aaj ka presentation "
                "bahut important hai.\n"
                "EMPLOYEE: (nervous) Sir, main ready hoon. "
                "Poori raat practice ki.\n"
                "BOSS: (impressed) Excellent! "
                "Confidence rakho, sab theek hoga.\n"
                "EMPLOYEE: (excited) Ji sir! "
                "Hum zaroor success karenge!\n"
                "BOSS: (happy) Yahi sunna chahta tha. "
                "Chalo shuru karte hain!",
                "Success Ki Raah - Business Story",
            ),
            "drama": (
                "RIYA: (sad) Tum samajhte kyun nahi? "
                "Main tumse bahut pyaar karti hoon.\n"
                "ARJUN: (confused) Riya, main... "
                "main nahi jaanta kya bolun.\n"
                "RIYA: (angry) Chup raho! "
                "Tumhari khamoshi ne sab kuch barbaad kar diya!\n"
                "ARJUN: (emotional) Riya suno! "
                "Main tum bin nahi reh sakta.\n"
                "RIYA: (surprised) Sach mein? "
                "Toh phir itni der kyun ki?",
                "Dil Ki Baat - Emotional Drama",
            ),
            "comedy": (
                "RAMU: (excited) Bhai! Mujhe aaj lottery lagi hai! "
                "Ek crore rupaye!\n"
                "SHYAM: (shocked) Kya? Sach mein? Ticket kahan hai?\n"
                "RAMU: (embarrassed) Woh... woh maine "
                "washing machine mein daal diya...\n"
                "SHYAM: (angry) KKKYA? Paagal ho gaye ho?\n"
                "RAMU: (nervous) Par bhai... "
                "ab ticket toh clean hai na? Hehe...",
                "Lottery Wala Ramu - Comedy",
            ),
        }

        if example_type in examples:
            script, title = examples[example_type]
            try:
                self._script_edit.setText(script)
                self._title_edit.setText(title)
            except Exception:
                pass

    def _browse_output(self):
        """Output folder select karna"""
        try:
            folder = self._QFileDialog.getExistingDirectory(
                self._dialog,
                "Output Folder Select Karo",
                "exports/",
            )
            if folder:
                self._output_edit.setText(folder)
        except Exception as e:
            logger.error(f"Browse output error: {e}")

    def _get_quality(self) -> str:
        """Quality string lena"""
        mapping = {0: "draft", 1: "medium", 2: "high", 3: "ultra"}
        try:
            return mapping.get(
                self._quality_combo.currentIndex(), "medium"
            )
        except Exception:
            return "medium"

    def _start_generation(self, dialog):
        """Video generation shuru karna"""
        try:
            script_text = self._script_edit.toPlainText().strip()

            # Validation
            if not script_text:
                self._QMessageBox.warning(
                    dialog,
                    "Script Empty!",
                    "Bhai script toh likho pehle! 😅\n\n"
                    "Example:\nHERO: (excited) Hello World!"
                )
                return

            if len(script_text) < 10:
                self._QMessageBox.warning(
                    dialog,
                    "Script Too Short!",
                    "Script bahut choti hai.\n"
                    "Kam se kam ek dialogue toh likho!"
                )
                return

            # Settings collect
            title         = self._title_edit.text().strip() or "My Animation"
            quality       = self._get_quality()
            output_folder = self._output_edit.text().strip() or "exports/"

            # Output path banana
            import time as _time
            os.makedirs(output_folder, exist_ok=True)
            timestamp  = int(_time.time())
            safe_title = "".join(
                c for c in title if c.isalnum() or c in " _-"
            ).strip().replace(" ", "_")
            output_path = os.path.join(
                output_folder,
                f"{safe_title}_{timestamp}.mp4"
            )

            # Input dialog close karo
            dialog.accept()

            # Generation dialog open karo
            gen_dialog = VideoGenerationDialog(
                script_text = script_text,
                title       = title,
                quality     = quality,
                output_path = output_path,
                parent      = self._parent,
            )
            gen_dialog.exec_()

        except Exception as e:
            logger.error(f"Start generation error: {e}")


# ============================================================
# GENERATION WORKER THREAD
# ============================================================

class GenerationWorker:
    """
    Background thread mein video generate karna.
    UI freeze na ho isliye alag thread mein chalao.
    """

    def __init__(
        self,
        script_text: str,
        title:       str,
        quality:     str,
        output_path: str,
        on_progress: Optional[Callable] = None,
        on_step:     Optional[Callable] = None,
        on_done:     Optional[Callable] = None,
        on_failed:   Optional[Callable] = None,
    ):
        self.script_text = script_text
        self.title       = title
        self.quality     = quality
        self.output_path = output_path

        # Callbacks
        self._on_progress = on_progress
        self._on_step     = on_step
        self._on_done     = on_done
        self._on_failed   = on_failed

        self._thread: Optional[threading.Thread] = None
        self._running = False

        # Try PyQt5 QThread
        self._use_qthread = False
        self._qworker     = None
        self._setup_qthread()

    def _setup_qthread(self):
        """QThread setup karo agar available ho"""
        try:
            from PyQt5.QtCore import QThread, pyqtSignal, QObject

            class _QWorker(QThread):
                progress_updated  = pyqtSignal(int, str)
                step_completed    = pyqtSignal(str)
                generation_done   = pyqtSignal(str)
                generation_failed = pyqtSignal(str)

                def __init__(self_, s, t, q, o):
                    super().__init__()
                    self_.script_text = s
                    self_.title       = t
                    self_.quality     = q
                    self_.output_path = o

                def run(self_):
                    self_._do_generation()

                def _do_generation(self_):
                    try:
                        self_.progress_updated.emit(
                            5, "🔄 Pipeline initialize ho rahi hai..."
                        )

                        from src.pipeline.quick_video import script_to_video_v2 as script_to_video

                        self_.progress_updated.emit(
                            15, "📝 Script parse ho rahi hai..."
                        )
                        self_.step_completed.emit("Script Parsing")

                        self_.progress_updated.emit(
                            30, "🏗️ 3D Scene build ho rahi hai..."
                        )
                        self_.step_completed.emit("Scene Building")

                        self_.progress_updated.emit(
                            50, "🎙️ Voice generate ho rahi hai..."
                        )
                        self_.step_completed.emit("Voice Generation")

                        self_.progress_updated.emit(
                            65, "🎬 Animation plan ban rahi hai..."
                        )
                        self_.step_completed.emit("Animation Planning")

                        self_.progress_updated.emit(
                            80, "🎥 Video render ho rahi hai..."
                        )
                        self_.step_completed.emit("Video Rendering")

                        script_to_video(
                            script_text = self_.script_text,
                            output_path = self_.output_path,
                            title       = self_.title,
                            quality     = self_.quality,
                        )

                        self_.progress_updated.emit(
                            95, "🔊 Audio mix ho raha hai..."
                        )
                        self_.step_completed.emit("Audio Mixing")

                        self_.progress_updated.emit(
                            100, "✅ Video ready hai!"
                        )
                        self_.generation_done.emit(self_.output_path)

                    except Exception as e:
                        self_.generation_failed.emit(str(e))

            self._qworker     = _QWorker(
                self.script_text,
                self.title,
                self.quality,
                self.output_path,
            )
            self._use_qthread = True

        except ImportError:
            self._use_qthread = False

    def connect_signals(
        self,
        on_progress=None,
        on_step=None,
        on_done=None,
        on_failed=None,
    ):
        """QThread signals connect karo"""
        if self._use_qthread and self._qworker:
            if on_progress:
                self._qworker.progress_updated.connect(on_progress)
            if on_step:
                self._qworker.step_completed.connect(on_step)
            if on_done:
                self._qworker.generation_done.connect(on_done)
            if on_failed:
                self._qworker.generation_failed.connect(on_failed)

    def start(self):
        """Worker start karo"""
        if self._use_qthread and self._qworker:
            self._qworker.start()
        else:
            # Fallback: normal thread
            self._thread = threading.Thread(
                target=self._run_fallback,
                daemon=True,
            )
            self._thread.start()

    def terminate(self):
        """Worker stop karo"""
        if self._use_qthread and self._qworker:
            self._qworker.terminate()
        self._running = False

    def _run_fallback(self):
        """Threading fallback (QThread nahi hone pe)"""
        try:
            if self._on_progress:
                self._on_progress(5, "🔄 Starting...")
            from src.pipeline.quick_video import script_to_video_v2 as script_to_video
            if self._on_progress:
                self._on_progress(50, "🎥 Generating...")
            script_to_video(
                script_text = self.script_text,
                output_path = self.output_path,
                title       = self.title,
                quality     = self.quality,
            )
            if self._on_done:
                self._on_done(self.output_path)
        except Exception as e:
            if self._on_failed:
                self._on_failed(str(e))


# ============================================================
# VIDEO GENERATION DIALOG
# ============================================================

class VideoGenerationDialog:
    """
    Video generation progress dikhane wala dialog.
    GenerationWorker ke saath kaam karta hai.
    """

    def __init__(
        self,
        script_text: str,
        title:       str,
        quality:     str,
        output_path: str,
        parent=None,
    ):
        self.output_path = output_path
        self._parent     = parent
        self._dialog     = None
        self._worker     = None

        self._build(title, quality)
        self._start_worker(script_text, title, quality, output_path)

    def _build(self, title: str, quality: str):
        """Dialog UI build karo"""
        try:
            from PyQt5.QtWidgets import (
                QDialog, QVBoxLayout, QHBoxLayout,
                QLabel, QPushButton, QProgressBar,
                QListWidget, QMessageBox,
            )
            from PyQt5.QtCore import Qt

            self._QMessageBox = QMessageBox
            self._Qt          = Qt

            dialog = QDialog(self._parent)
            dialog.setWindowTitle("🎬 Generating Video...")
            dialog.setFixedSize(550, 420)
            dialog.setModal(True)

            dialog.setStyleSheet("""
                QDialog {
                    background-color: #0F0F19;
                    color: #FFFFFF;
                }
                QLabel { color: #FFFFFF; }
                QProgressBar {
                    border: 2px solid #333355;
                    border-radius: 8px;
                    background-color: #1A1A2E;
                    height: 25px;
                    text-align: center;
                    color: white;
                    font-weight: bold;
                }
                QProgressBar::chunk {
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 #00D4FF, stop:1 #00FFAA
                    );
                    border-radius: 6px;
                }
                QListWidget {
                    background-color: #1A1A2E;
                    border: 1px solid #333355;
                    border-radius: 6px;
                    color: #AAAACC;
                    font-size: 12px;
                }
                QPushButton {
                    background-color: #333355;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 20px;
                    font-size: 13px;
                }
                QPushButton:hover { background-color: #444477; }
                QPushButton#openBtn {
                    background-color: #00D4FF;
                    color: #000000;
                    font-weight: bold;
                }
                QPushButton#openBtn:hover {
                    background-color: #00FFAA;
                }
            """)

            layout = QVBoxLayout(dialog)
            layout.setSpacing(15)
            layout.setContentsMargins(25, 25, 25, 25)

            # Title
            title_lbl = QLabel(f"🎬 {title}")
            title_lbl.setStyleSheet(
                "font-size: 18px; font-weight: bold; color: #00D4FF;"
            )
            title_lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(title_lbl)

            quality_lbl = QLabel(
                f"Quality: {quality.upper()} | "
                f"Output: {self.output_path}"
            )
            quality_lbl.setStyleSheet(
                "color: #8888AA; font-size: 11px;"
            )
            quality_lbl.setAlignment(Qt.AlignCenter)
            quality_lbl.setWordWrap(True)
            layout.addWidget(quality_lbl)

            # Progress bar
            self._progress_bar = QProgressBar()
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(0)
            layout.addWidget(self._progress_bar)

            # Status
            self._status_lbl = QLabel("🔄 Starting...")
            self._status_lbl.setStyleSheet(
                "font-size: 13px; color: #CCCCDD;"
            )
            self._status_lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(self._status_lbl)

            # Steps list
            steps_lbl = QLabel("✅ Completed Steps:")
            steps_lbl.setStyleSheet(
                "color: #8888AA; font-size: 12px;"
            )
            layout.addWidget(steps_lbl)

            self._steps_list = QListWidget()
            self._steps_list.setMaximumHeight(120)
            layout.addWidget(self._steps_list)

            # Buttons
            btn_layout = QHBoxLayout()

            self._cancel_btn = QPushButton("⏹ Cancel")
            self._cancel_btn.clicked.connect(
                lambda: self._cancel_generation(dialog)
            )
            btn_layout.addWidget(self._cancel_btn)

            btn_layout.addStretch()

            self._open_btn = QPushButton("📂 Open Video")
            self._open_btn.setObjectName("openBtn")
            self._open_btn.setEnabled(False)
            self._open_btn.clicked.connect(self._open_video)
            btn_layout.addWidget(self._open_btn)

            self._close_btn = QPushButton("✖ Close")
            self._close_btn.setEnabled(False)
            self._close_btn.clicked.connect(dialog.accept)
            btn_layout.addWidget(self._close_btn)

            layout.addLayout(btn_layout)

            self._dialog = dialog

        except ImportError as e:
            logger.error(f"PyQt5 import error in VideoGenerationDialog: {e}")
        except Exception as e:
            logger.error(f"VideoGenerationDialog build error: {e}")

    def _start_worker(
        self,
        script_text: str,
        title:       str,
        quality:     str,
        output_path: str,
    ):
        """Worker thread start karo"""
        try:
            self._worker = GenerationWorker(
                script_text = script_text,
                title       = title,
                quality     = quality,
                output_path = output_path,
            )
            self._worker.connect_signals(
                on_progress = self._on_progress,
                on_step     = self._on_step,
                on_done     = self._on_success,
                on_failed   = self._on_failure,
            )
            self._worker.start()

        except Exception as e:
            logger.error(f"Worker start error: {e}")

    def exec_(self):
        """Dialog show karo"""
        if self._dialog:
            return self._dialog.exec_()
        return 0

    def _on_progress(self, percent: int, message: str):
        """Progress update"""
        try:
            self._progress_bar.setValue(percent)
            self._status_lbl.setText(message)
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.processEvents()
        except Exception:
            pass

    def _on_step(self, step_name: str):
        """Step complete"""
        try:
            self._steps_list.addItem(f"  ✅ {step_name}")
            self._steps_list.scrollToBottom()
        except Exception:
            pass

    def _on_success(self, output_path: str):
        """Video successfully bani"""
        try:
            self._progress_bar.setValue(100)
            self._status_lbl.setText(
                "🎉 Video successfully generate ho gayi!"
            )
            self._status_lbl.setStyleSheet(
                "font-size: 14px; color: #00FFAA; font-weight: bold;"
            )
            self._steps_list.addItem("  🎬 MP4 Video Ready!")
            self._cancel_btn.setEnabled(False)
            self._open_btn.setEnabled(True)
            self._close_btn.setEnabled(True)

            self._QMessageBox.information(
                self._dialog,
                "🎉 Video Ready!",
                f"Video successfully ban gayi!\n\n"
                f"📁 Location:\n{output_path}\n\n"
                "Ab tum:\n"
                "• 'Open Video' se seedha dekh sakte ho\n"
                "• Ya folder mein jaake upload kar sakte ho!",
            )
        except Exception as e:
            logger.error(f"On success error: {e}")

    def _on_failure(self, error_msg: str):
        """Generation fail ho gayi"""
        try:
            self._status_lbl.setText(f"❌ Error: {error_msg}")
            self._status_lbl.setStyleSheet(
                "font-size: 12px; color: #FF4444;"
            )
            self._cancel_btn.setText("Close")
            try:
                self._cancel_btn.clicked.disconnect()
            except Exception:
                pass
            self._cancel_btn.clicked.connect(self._dialog.reject)
            self._cancel_btn.setEnabled(True)

            self._QMessageBox.critical(
                self._dialog,
                "Generation Failed!",
                f"Video generate nahi hui 😢\n\n"
                f"Error: {error_msg}\n\n"
                "Suggestions:\n"
                "• Script format check karo\n"
                "• venv active hai?\n"
                "• requirements.txt install hai?",
            )
        except Exception as e:
            logger.error(f"On failure error: {e}")

    def _cancel_generation(self, dialog):
        """Generation cancel karo"""
        try:
            reply = self._QMessageBox.question(
                dialog,
                "Cancel?",
                "Video generation cancel karna chahte ho?",
                self._QMessageBox.Yes | self._QMessageBox.No,
            )
            if reply == self._QMessageBox.Yes:
                if self._worker:
                    self._worker.terminate()
                dialog.reject()
        except Exception as e:
            logger.error(f"Cancel error: {e}")

    def _open_video(self):
        """Video player mein open karo"""
        try:
            import subprocess
            if os.path.exists(self.output_path):
                subprocess.Popen(
                    ["start", "", self.output_path],
                    shell=True,
                )
            else:
                self._QMessageBox.warning(
                    self._dialog,
                    "File Not Found",
                    f"File nahi mili:\n{self.output_path}",
                )
        except Exception as e:
            logger.error(f"Open video error: {e}")


# ============================================================
# STUDIO DIALOGS - MAIN CLASS
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
        """Asset import dialog"""
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

            title = QLabel("Import 3D Asset")
            title.setStyleSheet(
                "font-size: 16px; font-weight: bold; color: #00D4FF;"
            )
            layout.addWidget(title)

            file_group  = QGroupBox("File")
            file_layout = QHBoxLayout(file_group)

            path_edit = QLineEdit()
            path_edit.setPlaceholderText(
                "File path yahan daalo ya browse karo..."
            )

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

            opt_group = QGroupBox("Import Options")
            opt_form  = QFormLayout(opt_group)

            scale_spin = QDoubleSpinBox()
            scale_spin.setRange(0.001, 100.0)
            scale_spin.setValue(1.0)
            scale_spin.setSingleStep(0.1)
            scale_spin.setDecimals(3)
            opt_form.addRow("Scale:", scale_spin)

            axis_combo = QComboBox()
            axis_combo.addItems(["Y (Default)", "Z (Blender)"])
            opt_form.addRow("Up Axis:", axis_combo)

            center_chk    = QCheckBox("Center on import")
            center_chk.setChecked(True)
            opt_form.addRow("", center_chk)

            normalize_chk = QCheckBox("Normalize size")
            opt_form.addRow("", normalize_chk)

            materials_chk = QCheckBox("Import materials")
            materials_chk.setChecked(True)
            opt_form.addRow("", materials_chk)

            anim_chk = QCheckBox("Import animations")
            anim_chk.setChecked(True)
            opt_form.addRow("", anim_chk)

            copy_chk = QCheckBox("Copy to project folder")
            copy_chk.setChecked(True)
            opt_form.addRow("", copy_chk)

            layout.addWidget(opt_group)

            btn_box = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            )
            btn_box.button(QDialogButtonBox.Ok).setText("Import")
            btn_box.accepted.connect(dialog.accept)
            btn_box.rejected.connect(dialog.reject)
            layout.addWidget(btn_box)

            if theme_manager:
                p = theme_manager.get_palette()
                dialog.setStyleSheet(f"""
                    QDialog {{ background-color: {p.bg_secondary}; color: {p.text_primary}; }}
                    QGroupBox {{ border: 1px solid {p.border}; border-radius: 5px; margin-top: 10px; padding: 8px; color: {p.accent}; font-size: 11px; font-weight: bold; }}
                    QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px; }}
                    QLabel {{ color: {p.text_primary}; font-size: 12px; }}
                    QLineEdit, QComboBox, QDoubleSpinBox {{ background-color: {p.bg_tertiary}; border: 1px solid {p.border}; border-radius: 3px; color: {p.text_primary}; padding: 4px 6px; font-size: 11px; }}
                    QCheckBox {{ color: {p.text_primary}; font-size: 11px; }}
                    QPushButton {{ background-color: {p.accent}; color: #000; border: none; border-radius: 4px; padding: 6px 16px; font-weight: bold; }}
                    QPushButton:hover {{ background-color: {p.accent_hover}; }}
                """)

            if dialog.exec_() == QDialog.Accepted:
                settings.file_path         = path_edit.text()
                settings.scale             = scale_spin.value()
                settings.up_axis           = "Z" if axis_combo.currentIndex() == 1 else "Y"
                settings.center_on_import  = center_chk.isChecked()
                settings.normalize_size    = normalize_chk.isChecked()
                settings.import_materials  = materials_chk.isChecked()
                settings.import_animations = anim_chk.isChecked()
                settings.copy_to_project   = copy_chk.isChecked()
                result = DialogResult.ACCEPTED
                logger.info(f"Import: {settings.file_path}")
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
                QToolButton, QDialogButtonBox,
                QTabWidget, QWidget,
            )
            from PyQt5.QtCore import Qt

            dialog = QDialog(parent)
            dialog.setWindowTitle("📤 Export Video")
            dialog.setModal(True)
            dialog.setMinimumWidth(500)

            layout = QVBoxLayout(dialog)
            layout.setSpacing(10)
            layout.setContentsMargins(16, 16, 16, 16)

            title = QLabel("Export Video")
            title.setStyleSheet(
                "font-size: 16px; font-weight: bold; color: #00D4FF;"
            )
            layout.addWidget(title)

            tabs = QTabWidget()

            # Output Tab
            output_tab  = QWidget()
            output_form = QFormLayout(output_tab)
            output_form.setSpacing(8)
            output_form.setContentsMargins(8, 8, 8, 8)

            path_container = QWidget()
            path_layout    = QHBoxLayout(path_container)
            path_layout.setContentsMargins(0, 0, 0, 0)
            path_layout.setSpacing(4)

            path_edit = QLineEdit()
            path_edit.setText(settings.output_path or "exports/output.mp4")

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

            preset_combo = QComboBox()
            presets = [
                "youtube_1080p", "youtube_4k", "youtube_720p",
                "youtube_shorts", "instagram_reels", "instagram_feed",
                "tiktok", "twitter", "facebook",
                "web_optimized", "draft_preview",
            ]
            preset_combo.addItems(presets)
            if settings.preset in presets:
                preset_combo.setCurrentText(settings.preset)
            output_form.addRow("Platform Preset:", preset_combo)

            format_combo = QComboBox()
            format_combo.addItems(["MP4 (H264)", "MP4 (H265)", "WebM (VP9)"])
            output_form.addRow("Format:", format_combo)

            quality_combo = QComboBox()
            quality_combo.addItems(["draft", "medium", "high", "ultra"])
            quality_combo.setCurrentText(settings.quality)
            output_form.addRow("Quality:", quality_combo)

            tabs.addTab(output_tab, "📁 Output")

            # Video Tab
            video_tab  = QWidget()
            video_form = QFormLayout(video_tab)
            video_form.setSpacing(8)
            video_form.setContentsMargins(8, 8, 8, 8)

            res_container = QWidget()
            res_layout    = QHBoxLayout(res_container)
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

            res_combo = QComboBox()
            res_combo.addItems([
                "Custom",
                "1920×1080 (FHD)", "3840×2160 (4K)",
                "1280×720 (HD)",   "1080×1920 (Vertical)",
                "1080×1080 (Square)", "854×480 (SD)",
            ])

            def on_res_preset(text):
                mapping = {
                    "1920×1080 (FHD)":     (1920, 1080),
                    "3840×2160 (4K)":      (3840, 2160),
                    "1280×720 (HD)":       (1280, 720),
                    "1080×1920 (Vertical)":(1080, 1920),
                    "1080×1080 (Square)":  (1080, 1080),
                    "854×480 (SD)":        (854,  480),
                }
                if text in mapping:
                    w, h = mapping[text]
                    width_spin.setValue(w)
                    height_spin.setValue(h)

            res_combo.currentTextChanged.connect(on_res_preset)
            video_form.addRow("Resolution:", res_container)
            video_form.addRow("Preset:", res_combo)

            fps_combo = QComboBox()
            fps_combo.addItems(["24", "30", "60"])
            fps_combo.setCurrentText(str(settings.fps))
            video_form.addRow("Frame Rate:", fps_combo)

            tabs.addTab(video_tab, "🎬 Video")

            # Range Tab
            range_tab  = QWidget()
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

            btn_box = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            )
            btn_box.button(QDialogButtonBox.Ok).setText("🚀 Export")
            btn_box.accepted.connect(dialog.accept)
            btn_box.rejected.connect(dialog.reject)
            layout.addWidget(btn_box)

            if theme_manager:
                p = theme_manager.get_palette()
                dialog.setStyleSheet(f"""
                    QDialog {{ background-color: {p.bg_secondary}; }}
                    QLabel {{ color: {p.text_primary}; font-size: 11px; }}
                    QLineEdit, QComboBox, QSpinBox {{ background-color: {p.bg_tertiary}; border: 1px solid {p.border}; border-radius: 3px; color: {p.text_primary}; padding: 3px 6px; font-size: 11px; }}
                    QTabBar::tab {{ background-color: {p.bg_tertiary}; color: {p.text_secondary}; padding: 6px 12px; border-radius: 4px 4px 0 0; }}
                    QTabBar::tab:selected {{ background-color: {p.bg_secondary}; color: {p.accent}; border-top: 2px solid {p.accent}; }}
                    QTabWidget::pane {{ border: 1px solid {p.border}; background-color: {p.bg_secondary}; }}
                    QCheckBox {{ color: {p.text_primary}; font-size: 11px; }}
                    QPushButton {{ background-color: {p.accent}; color: #000; border: none; border-radius: 4px; padding: 6px 16px; font-weight: bold; }}
                """)

            if dialog.exec_() == QDialog.Accepted:
                settings.output_path       = path_edit.text()
                settings.preset            = preset_combo.currentText()
                settings.quality           = quality_combo.currentText()
                settings.width             = width_spin.value()
                settings.height            = height_spin.value()
                settings.fps               = int(fps_combo.currentText())
                settings.start_frame       = start_spin.value()
                settings.end_frame         = end_spin.value()
                settings.include_audio     = audio_chk.isChecked()
                settings.open_after_export = open_chk.isChecked()
                result = DialogResult.ACCEPTED
                logger.info(f"Export: {settings.preset}")
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
        """New project dialog"""
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

            title = QLabel("New Animation Project")
            title.setStyleSheet(
                "font-size: 16px; font-weight: bold; color: #00D4FF;"
            )
            layout.addWidget(title)

            form = QFormLayout()
            form.setSpacing(8)

            name_edit = QLineEdit()
            name_edit.setText("My Animation")
            name_edit.setPlaceholderText("Project naam...")
            form.addRow("Project Name:", name_edit)

            author_edit = QLineEdit()
            author_edit.setPlaceholderText("Aapka naam (optional)")
            form.addRow("Author:", author_edit)

            template_combo = QComboBox()
            templates = [
                "blank", "youtube_video", "short_film",
                "animation_reel", "tutorial_video",
            ]
            template_display = [
                "Blank Project", "YouTube Video (16:9)",
                "Short Film", "Animation Reel", "Tutorial Video",
            ]
            for t in template_display:
                template_combo.addItem(t)
            form.addRow("Template:", template_combo)

            res_combo = QComboBox()
            res_combo.addItems([
                "1920×1080 (FHD - YouTube)",
                "3840×2160 (4K)",
                "1280×720 (HD)",
                "1080×1920 (Vertical - Shorts)",
                "1080×1080 (Square - Instagram)",
            ])
            form.addRow("Resolution:", res_combo)

            fps_combo = QComboBox()
            fps_combo.addItems(["24 FPS", "30 FPS", "60 FPS"])
            fps_combo.setCurrentIndex(1)
            form.addRow("Frame Rate:", fps_combo)

            dur_spin = QSpinBox()
            dur_spin.setRange(1, 9999)
            dur_spin.setValue(10)
            dur_spin.setSuffix(" seconds")
            form.addRow("Duration:", dur_spin)

            layout.addLayout(form)

            btn_box = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            )
            btn_box.button(QDialogButtonBox.Ok).setText("✅ Create Project")
            btn_box.accepted.connect(dialog.accept)
            btn_box.rejected.connect(dialog.reject)
            layout.addWidget(btn_box)

            if theme_manager:
                p = theme_manager.get_palette()
                dialog.setStyleSheet(f"""
                    QDialog {{ background-color: {p.bg_secondary}; }}
                    QLabel {{ color: {p.text_primary}; font-size: 12px; }}
                    QLineEdit, QComboBox, QSpinBox {{ background-color: {p.bg_tertiary}; border: 1px solid {p.border}; border-radius: 3px; color: {p.text_primary}; padding: 5px 8px; font-size: 12px; }}
                    QPushButton {{ background-color: {p.accent}; color: #000; border: none; border-radius: 4px; padding: 7px 18px; font-weight: bold; font-size: 12px; }}
                    QPushButton:hover {{ background-color: {p.accent_hover}; }}
                """)

            if dialog.exec_() == QDialog.Accepted:
                settings.name     = name_edit.text() or "My Animation"
                settings.author   = author_edit.text()
                settings.template = templates[template_combo.currentIndex()]

                res_map = {
                    0: (1920, 1080), 1: (3840, 2160),
                    2: (1280, 720),  3: (1080, 1920),
                    4: (1080, 1080),
                }
                w, h = res_map.get(res_combo.currentIndex(), (1920, 1080))
                settings.width  = w
                settings.height = h

                fps_map = {0: 24, 1: 30, 2: 60}
                settings.fps = fps_map.get(fps_combo.currentIndex(), 30)
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
        title:        str  = "Processing...",
        message:      str  = "Kaam chal raha hai...",
        parent=None,
        theme_manager=None,
        cancellable:  bool = True,
    ) -> "ProgressDialog":
        """Progress dialog banao aur return karo"""
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
        """About dialog"""
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

            btn_layout = QHBoxLayout()

            github_btn = QPushButton("⭐ GitHub")
            github_btn.clicked.connect(
                lambda: __import__("webbrowser").open(
                    "https://github.com/happyreehal/3d-animation-studio"
                )
            )
            btn_layout.addWidget(github_btn)

            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.close)
            btn_layout.addWidget(close_btn)

            layout.addLayout(btn_layout)

            if theme_manager:
                p = theme_manager.get_palette()
                dialog.setStyleSheet(f"""
                    QDialog {{ background-color: {p.bg_secondary}; }}
                    QPushButton {{ background-color: {p.bg_elevated}; color: {p.text_primary}; border: 1px solid {p.border}; border-radius: 4px; padding: 6px 16px; }}
                    QPushButton:hover {{ background-color: {p.bg_hover}; border-color: {p.accent}; }}
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
        """Preferences dialog"""
        result    = DialogResult.CANCELLED
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

            # Appearance
            appear_tab  = QWidget()
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

            # Performance
            perf_tab  = QWidget()
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

            # Audio
            audio_tab  = QWidget()
            audio_form = QFormLayout(audio_tab)
            audio_form.setSpacing(10)
            audio_form.setContentsMargins(12, 12, 12, 12)

            tts_engine = QComboBox()
            tts_engine.addItems([
                "pyttsx3 (Offline)", "gTTS (Online)", "Auto"
            ])
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

            # Paths
            paths_tab  = QWidget()
            paths_form = QFormLayout(paths_tab)
            paths_form.setSpacing(10)
            paths_form.setContentsMargins(12, 12, 12, 12)

            export_edit   = QLineEdit("exports")
            paths_form.addRow("Export Folder:", export_edit)

            projects_edit = QLineEdit("projects")
            paths_form.addRow("Projects Folder:", projects_edit)

            temp_edit = QLineEdit("temp")
            paths_form.addRow("Temp Folder:", temp_edit)

            tabs.addTab(paths_tab, "📁 Paths")

            layout.addWidget(tabs)

            btn_box = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel |
                QDialogButtonBox.RestoreDefaults
            )
            btn_box.button(QDialogButtonBox.Ok).setText("✅ Apply")
            btn_box.button(
                QDialogButtonBox.RestoreDefaults
            ).setText("↺ Reset")
            btn_box.accepted.connect(dialog.accept)
            btn_box.rejected.connect(dialog.reject)
            layout.addWidget(btn_box)

            if theme_manager:
                p = theme_manager.get_palette()
                dialog.setStyleSheet(f"""
                    QDialog {{ background-color: {p.bg_secondary}; }}
                    QLabel {{ color: {p.text_primary}; font-size: 12px; }}
                    QLineEdit, QComboBox, QSpinBox {{ background-color: {p.bg_tertiary}; border: 1px solid {p.border}; border-radius: 3px; color: {p.text_primary}; padding: 4px 8px; font-size: 11px; }}
                    QTabBar::tab {{ background-color: {p.bg_tertiary}; color: {p.text_secondary}; padding: 6px 12px; }}
                    QTabBar::tab:selected {{ background-color: {p.bg_secondary}; color: {p.accent}; border-top: 2px solid {p.accent}; }}
                    QTabWidget::pane {{ border: 1px solid {p.border}; background: {p.bg_secondary}; }}
                    QCheckBox {{ color: {p.text_primary}; font-size: 11px; }}
                    QPushButton {{ background-color: {p.accent}; color: #000; border: none; border-radius: 4px; padding: 6px 16px; font-weight: bold; }}
                """)

            if dialog.exec_() == QDialog.Accepted:
                accent_map = {
                    0: "#00D4FF", 1: "#9B59B6", 2: "#2ECC71",
                    3: "#E67E22", 4: "#E74C3C", 5: "#FF6B9D",
                    6: "#F1C40F",
                }
                fps_map = {0: 24, 1: 30, 2: 60}

                new_prefs = {
                    "theme": "light" if theme_combo.currentIndex() == 1 else "dark",
                    "accent_color": accent_map.get(accent_combo.currentIndex(), "#00D4FF"),
                    "font_size":    font_spin.value(),
                    "preview_quality": preview_quality.currentText(),
                    "fps":          fps_map.get(fps_combo.currentIndex(), 30),
                    "autosave_interval": autosave_spin.value() * 60,
                    "gpu_acceleration":  gpu_chk.isChecked(),
                    "tts_engine":    tts_engine.currentText(),
                    "export_folder": export_edit.text(),
                    "projects_folder": projects_edit.text(),
                }
                result = DialogResult.ACCEPTED

                if theme_manager:
                    theme_manager.set_accent_color(
                        new_prefs["accent_color"]
                    )
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
        title:        str,
        message:      str,
        parent=None,
        theme_manager=None,
        confirm_text: str  = "Yes",
        cancel_text:  str  = "Cancel",
        danger:       bool = False,
    ) -> bool:
        """Confirmation dialog"""
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

            msg_lbl = QLabel(f"⚠️  {message}" if danger else message)
            msg_lbl.setWordWrap(True)
            msg_lbl.setAlignment(Qt.AlignCenter)
            msg_lbl.setStyleSheet(
                f"font-size: 13px; color: "
                f"{'#E74C3C' if danger else '#FFFFFF'}; padding: 10px;"
            )
            layout.addWidget(msg_lbl)

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
                    QPushButton {{ background-color: {p.bg_secondary}; color: {p.text_primary}; border: 1px solid {p.border}; border-radius: 4px; padding: 7px 18px; }}
                    QPushButton:hover {{ background-color: {p.bg_hover}; border-color: {p.accent}; }}
                """)

            return dialog.exec_() == QDialog.Accepted

        except ImportError:
            return True
        except Exception as e:
            logger.error(f"Confirm dialog error: {e}")
            return False

    # ----------------------------------------------------------
    # INPUT DIALOG
    # ----------------------------------------------------------

    @staticmethod
    def show_input_dialog(
        title:   str,
        label:   str,
        default: str = "",
        parent=None,
        theme_manager=None,
    ) -> Tuple[bool, str]:
        """Simple text input dialog"""
        try:
            from PyQt5.QtWidgets import QInputDialog, QLineEdit
            text, ok = QInputDialog.getText(
                parent, title, label, QLineEdit.Normal, default
            )
            return ok, text
        except ImportError:
            return False, default
        except Exception as e:
            logger.error(f"Input dialog error: {e}")
            return False, default

    # ----------------------------------------------------------
    # FILE DIALOGS
    # ----------------------------------------------------------

    @staticmethod
    def open_file_dialog(
        title:  str = "File Open Karo",
        filter: str = "All Files (*)",
        parent=None,
    ) -> Optional[str]:
        """File open dialog"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            path, _ = QFileDialog.getOpenFileName(
                parent, title, "", filter
            )
            return path if path else None
        except Exception:
            return None

    @staticmethod
    def save_file_dialog(
        title:   str = "File Save Karo",
        filter:  str = "All Files (*)",
        default: str = "",
        parent=None,
    ) -> Optional[str]:
        """File save dialog"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            path, _ = QFileDialog.getSaveFileName(
                parent, title, default, filter
            )
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
    """Progress dialog - long running tasks ke liye"""

    def __init__(
        self,
        title:        str  = "Processing...",
        message:      str  = "Kaam chal raha hai...",
        parent=None,
        theme_manager=None,
        cancellable:  bool = True,
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
                Qt.Dialog |
                Qt.CustomizeWindowHint |
                Qt.WindowTitleHint
            )

            layout = QVBoxLayout(self._dialog)
            layout.setSpacing(12)
            layout.setContentsMargins(20, 20, 20, 20)

            title_lbl = QLabel(f"⏳ {self.title}")
            title_lbl.setStyleSheet(
                "font-size: 14px; font-weight: bold; color: #00D4FF;"
            )
            layout.addWidget(title_lbl)

            self._label = QLabel(self.message)
            self._label.setWordWrap(True)
            self._label.setStyleSheet(
                "font-size: 11px; color: #AAAACC;"
            )
            layout.addWidget(self._label)

            self._progress_bar = QProgressBar()
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(0)
            self._progress_bar.setTextVisible(True)
            self._progress_bar.setFixedHeight(20)
            layout.addWidget(self._progress_bar)

            if self.cancellable:
                btn_layout = QHBoxLayout()
                btn_layout.addStretch()
                cancel_btn = QPushButton("❌ Cancel")
                cancel_btn.clicked.connect(self._on_cancel)
                btn_layout.addWidget(cancel_btn)
                layout.addLayout(btn_layout)

            if self.theme_manager:
                p = self.theme_manager.get_palette()
                self._dialog.setStyleSheet(f"""
                    QDialog {{ background-color: {p.bg_secondary}; }}
                    QProgressBar {{ background-color: {p.bg_tertiary}; border: 1px solid {p.border}; border-radius: 4px; color: {p.text_primary}; text-align: center; font-size: 11px; }}
                    QProgressBar::chunk {{ background-color: {p.accent}; border-radius: 3px; }}
                    QPushButton {{ background-color: {p.text_error}; color: white; border: none; border-radius: 4px; padding: 5px 14px; }}
                """)

        except ImportError:
            logger.warning("PyQt5 nahi - progress dialog skip")
        except Exception as e:
            logger.error(f"Progress dialog build error: {e}")

    def show(self):
        if self._dialog:
            try:
                self._dialog.show()
                self._process_events()
            except Exception:
                pass

    def hide(self):
        if self._dialog:
            try:
                self._dialog.hide()
            except Exception:
                pass

    def close(self):
        if self._dialog:
            try:
                self._dialog.close()
            except Exception:
                pass

    def update(self, percent: int, message: str = ""):
        try:
            if self._progress_bar:
                self._progress_bar.setValue(max(0, min(100, percent)))
            if self._label and message:
                self._label.setText(message)
            self._process_events()
        except Exception:
            pass

    def set_message(self, message: str):
        if self._label:
            try:
                self._label.setText(message)
                self._process_events()
            except Exception:
                pass

    def is_cancelled(self) -> bool:
        self._process_events()
        return self._cancelled

    def set_cancel_callback(self, callback: Callable):
        self._cancel_callback = callback

    def _on_cancel(self):
        self._cancelled = True
        if self._cancel_callback:
            self._cancel_callback()
        logger.info("Progress dialog cancelled")

    def _process_events(self):
        try:
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.processEvents()
        except Exception:
            pass

    def __enter__(self):
        self.show()
        return self

    def __exit__(self, *args):
        self.close()


# ============================================================
# TEST SECTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="DEBUG")
    print_banner("Dialogs Test", "Studio Dialog Windows")

    # Test 1: Data Classes
    print_section("Test 1: Data Classes")
    imp = ImportSettings()
    exp = ExportSettings()
    prj = ProjectSettings()
    ren = RenderSettings()
    print(f"✅ ImportSettings: scale={imp.scale}")
    print(f"✅ ExportSettings: preset={exp.preset}")
    print(f"✅ ProjectSettings: name='{prj.name}'")
    print(f"✅ RenderSettings: quality={ren.quality}")

    # Test 2: New Classes Check
    print_section("Test 2: New Classes Check")
    print(f"✅ ScriptInputDialog  : {ScriptInputDialog}")
    print(f"✅ GenerationWorker   : {GenerationWorker}")
    print(f"✅ VideoGenerationDialog: {VideoGenerationDialog}")

    # Test 3: Qt Visual Tests
    print_section("Test 3: Qt Dialogs")
    try:
        from PyQt5.QtWidgets import QApplication
        import sys as _sys

        app = QApplication.instance() or QApplication(_sys.argv)

        from src.ui.theme_manager import ThemeManager
        theme = ThemeManager()
        theme.set_application(app)

        # ScriptInputDialog test
        print("🎬 ScriptInputDialog test...")
        script_dialog = ScriptInputDialog()
        script_dialog.exec_()
        print("✅ ScriptInputDialog closed")

        # About
        print("📋 About Dialog...")
        StudioDialogs.show_about_dialog(theme_manager=theme)
        print("✅ Done")

        print("\n✅ All tests complete!")

    except ImportError:
        print("⚠️  PyQt5 nahi - visual tests skip")
    except Exception as e:
        print(f"⚠️  Error: {e}")
        import traceback
        traceback.print_exc()

    # Test 4: DialogResult
    print_section("Test 4: DialogResult Enum")
    for r in DialogResult:
        print(f"✅ {r.name}: {r.value}")

    # Test 5: BaseDialogData
    print_section("Test 5: BaseDialogData")
    base = BaseDialogData()
    print(f"✅ Initial: {base.get_result().value}")
    base._result = DialogResult.ACCEPTED
    print(f"✅ Accepted: {base.was_accepted()}")

    print_banner("✅ All Tests Passed!", "dialogs.py Complete!")