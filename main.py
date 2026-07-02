# ============================================================
# 3D ANIMATION STUDIO - Main Entry Point
# Version: 1.0.0
# ============================================================

import sys
import os
import json
import logging
from datetime import datetime

# ============================================================
# PATH SETUP - Sabse pehle paths set karo
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
BACKUPS_DIR = os.path.join(BASE_DIR, "backups")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
CACHE_DIR = os.path.join(BASE_DIR, "cache")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

sys.path.insert(0, BASE_DIR)
sys.path.insert(0, SRC_DIR)

# ============================================================
# DIRECTORY CREATION - Zaroori folders banao
# ============================================================

REQUIRED_DIRS = [
    SRC_DIR,
    ASSETS_DIR,
    PROJECTS_DIR,
    BACKUPS_DIR,
    TEMP_DIR,
    EXPORTS_DIR,
    CACHE_DIR,
    LOGS_DIR,
    os.path.join(ASSETS_DIR, "models"),
    os.path.join(ASSETS_DIR, "textures"),
    os.path.join(ASSETS_DIR, "audio"),
    os.path.join(ASSETS_DIR, "audio", "music"),
    os.path.join(ASSETS_DIR, "audio", "sfx"),
    os.path.join(ASSETS_DIR, "audio", "ambient"),
    os.path.join(ASSETS_DIR, "presets"),
    os.path.join(ASSETS_DIR, "presets", "characters"),
    os.path.join(ASSETS_DIR, "presets", "scenes"),
    os.path.join(ASSETS_DIR, "presets", "animations"),
    os.path.join(SRC_DIR, "core"),
    os.path.join(SRC_DIR, "renderer"),
    os.path.join(SRC_DIR, "physics"),
    os.path.join(SRC_DIR, "ai"),
    os.path.join(SRC_DIR, "audio"),
    os.path.join(SRC_DIR, "ui"),
    os.path.join(SRC_DIR, "timeline"),
    os.path.join(SRC_DIR, "export"),
    os.path.join(SRC_DIR, "utils"),
]

def create_required_directories():
    """Saare zaroori directories banata hai"""
    for directory in REQUIRED_DIRS:
        os.makedirs(directory, exist_ok=True)

# ============================================================
# LOGGING SETUP
# ============================================================

def setup_logging():
    """
    Logging system setup karta hai.
    - File mein bhi save hoga
    - Console mein bhi dikhega
    """
    log_filename = os.path.join(
        LOGS_DIR,
        f"studio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_filename, encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Third-party libraries ke verbose logs suppress karo
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("numba").setLevel(logging.WARNING)
    logging.getLogger("torch").setLevel(logging.WARNING)

    logger = logging.getLogger("Main")
    logger.info("=" * 60)
    logger.info("3D Animation Studio - Starting Up")
    logger.info(f"Version: 1.0.0")
    logger.info(f"Base Directory: {BASE_DIR}")
    logger.info(f"Log File: {log_filename}")
    logger.info("=" * 60)

    return logger

# ============================================================
# CONFIG LOADER
# ============================================================

def load_config():
    """
    config.json load karta hai.
    Agar file missing ho to error deta hai.
    """
    config_path = os.path.join(BASE_DIR, "config.json")

    if not os.path.exists(config_path):
        print(f"[CRITICAL ERROR] config.json not found at: {config_path}")
        print("Please make sure config.json exists in the project root.")
        sys.exit(1)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        print(f"[CRITICAL ERROR] config.json is invalid: {e}")
        sys.exit(1)

# ============================================================
# DEPENDENCY CHECKER
# ============================================================

def check_dependencies():
    """
    Saari required libraries check karta hai.
    Missing libraries ki list deta hai.
    """
    logger = logging.getLogger("DependencyChecker")

    required_packages = {
        "PyQt5": "PyQt5",
        "OpenGL": "PyOpenGL",
        "moderngl": "moderngl",
        "numpy": "numpy",
        "scipy": "scipy",
        "PIL": "Pillow",
        "cv2": "opencv-python",
        "trimesh": "trimesh",
        "pybullet": "pybullet",
        "librosa": "librosa",
        "soundfile": "soundfile",
        "pydub": "pydub",
        "ffmpeg": "ffmpeg-python",
        "tqdm": "tqdm",
        "requests": "requests",
        "psutil": "psutil",
        "imageio": "imageio",
        "pyrr": "pyrr",
    }

    missing = []
    available = []

    for import_name, package_name in required_packages.items():
        try:
            __import__(import_name)
            available.append(package_name)
        except ImportError:
            missing.append(package_name)

    logger.info(f"Available packages: {len(available)}/{len(required_packages)}")

    if missing:
        logger.warning(f"Missing packages: {missing}")
        logger.warning(
            "Run: pip install -r requirements.txt"
        )
        return False, missing

    logger.info("All core dependencies are available.")
    return True, []

# ============================================================
# PYQT5 CHECK - GUI ke liye
# ============================================================

def check_qt():
    """PyQt5 specifically check karta hai kyunki ye sabse zaroori hai"""
    try:
        from PyQt5.QtWidgets import QApplication  # type: ignore[import]
        import importlib
        importlib.import_module("PyQt5.QtCore")
        return True
    except ImportError:
        print("[CRITICAL ERROR] PyQt5 is not installed.")
        print("Run: pip install PyQt5")
        sys.exit(1)

# ============================================================
# SPLASH SCREEN
# ============================================================

def show_splash(app):
    """
    App start hote waqt splash screen dikhata hai.
    Loading progress bhi dikhata hai.
    """
    from PyQt5.QtWidgets import QSplashScreen, QLabel
    from PyQt5.QtGui import QPixmap, QColor, QFont, QPainter, QLinearGradient  # type: ignore[import]
    from PyQt5.QtCore import Qt, QTimer

    # Splash screen image banao (custom drawn)
    width, height = 700, 400
    pixmap = QPixmap(width, height)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Background gradient - dark theme
    gradient = QLinearGradient(0, 0, width, height)
    gradient.setColorAt(0.0, QColor(15, 15, 25))
    gradient.setColorAt(0.5, QColor(25, 25, 40))
    gradient.setColorAt(1.0, QColor(10, 10, 20))
    painter.fillRect(0, 0, width, height, gradient)

    # Border
    from PyQt5.QtGui import QPen
    painter.setPen(QPen(QColor(0, 212, 255), 2))
    painter.drawRect(1, 1, width - 2, height - 2)

    # Title Text
    painter.setPen(QColor(0, 212, 255))
    title_font = QFont("Segoe UI", 32, QFont.Bold)
    painter.setFont(title_font)
    painter.drawText(0, 0, width, 200, Qt.AlignCenter, "3D Animation Studio")

    # Subtitle
    painter.setPen(QColor(180, 180, 200))
    sub_font = QFont("Segoe UI", 12)
    painter.setFont(sub_font)
    painter.drawText(0, 160, width, 50, Qt.AlignCenter, "Free & Open Source | YouTube Content Creator Tool")

    # Version
    painter.setPen(QColor(100, 100, 120))
    ver_font = QFont("Segoe UI", 10)
    painter.setFont(ver_font)
    painter.drawText(0, 340, width, 40, Qt.AlignCenter, "Version 1.0.0 | Initializing...")

    painter.end()

    splash = QSplashScreen(pixmap, Qt.WindowStaysOnTopHint)
    splash.setWindowFlags(Qt.SplashScreen | Qt.WindowStaysOnTopHint)
    splash.show()
    app.processEvents()

    return splash

def update_splash(splash, app, message, progress=0):
    """Splash screen message update karta hai"""
    from PyQt5.QtCore import Qt
    splash.showMessage(
        f"  {message}",
        Qt.AlignBottom | Qt.AlignLeft,
        __import__("PyQt5.QtGui", fromlist=["QColor"]).QColor(0, 212, 255)
    )
    app.processEvents()

# ============================================================
# MAIN APPLICATION CLASS
# ============================================================

class AnimationStudioApp:
    """
    Main Application Controller.
    Saari components ko initialize aur manage karta hai.
    """

    def __init__(self):
        self.logger = logging.getLogger("AnimationStudioApp")
        self.config = None
        self.qt_app = None
        self.main_window = None
        self.splash = None

    def initialize(self):
        """Step by step initialization"""

        # Step 1: Config load karo
        self.logger.info("Loading configuration...")
        self.config = load_config()
        self.logger.info("Configuration loaded successfully.")

        # Step 2: Qt Application banao
        self.logger.info("Initializing Qt Application...")
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt

        self.qt_app = QApplication(sys.argv)
        self.qt_app.setApplicationName(self.config["app"]["name"])
        self.qt_app.setApplicationVersion(self.config["app"]["version"])
        self.qt_app.setOrganizationName("AnimationStudio")

        # High DPI support
        self.qt_app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        self.qt_app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        self.logger.info("Qt Application initialized.")

        # Step 3: Splash screen dikhao
        self.splash = show_splash(self.qt_app)

        # Step 4: Dependencies check karo
        update_splash(self.splash, self.qt_app, "Checking dependencies...", 10)
        deps_ok, missing = check_dependencies()
        if not deps_ok:
            self.logger.warning(f"Some packages missing: {missing}")

        # Step 5: Core systems initialize karo
        update_splash(self.splash, self.qt_app, "Initializing core systems...", 20)
        self._init_core_systems()

        # Step 6: Renderer initialize karo
        update_splash(self.splash, self.qt_app, "Setting up renderer...", 35)
        self._init_renderer()

        # Step 7: Physics initialize karo
        update_splash(self.splash, self.qt_app, "Loading physics engine...", 50)
        self._init_physics()

        # Step 8: AI systems initialize karo
        update_splash(self.splash, self.qt_app, "Loading AI systems...", 65)
        self._init_ai_systems()

        # Step 9: Audio initialize karo
        update_splash(self.splash, self.qt_app, "Initializing audio engine...", 80)
        self._init_audio()

        # Step 10: Main Window banao
        update_splash(self.splash, self.qt_app, "Building user interface...", 90)
        self._init_main_window()

        # Step 11: Final setup
        update_splash(self.splash, self.qt_app, "Ready!", 100)

        return True

    def _init_core_systems(self):
        """Core utility systems initialize karta hai"""
        try:
            from src.core.project_manager import ProjectManager
            from src.core.asset_library import AssetLibrary
            from src.core.auto_save import AutoSaveSystem

            self.project_manager = ProjectManager(self.config, BASE_DIR)
            self.asset_library = AssetLibrary(self.config, BASE_DIR)
            self.auto_save = AutoSaveSystem(self.config)

            self.logger.info("Core systems initialized.")
        except ImportError as e:
            self.logger.warning(f"Core system import pending: {e}")
            # Placeholder - file banane ke baad kaam karega
            self.project_manager = None
            self.asset_library = None
            self.auto_save = None

    def _init_renderer(self):
        """3D Renderer initialize karta hai"""
        try:
            from src.renderer.render_engine import RenderEngine
            self.render_engine = RenderEngine(self.config)
            self.logger.info("Render engine initialized.")
        except ImportError as e:
            self.logger.warning(f"Renderer import pending: {e}")
            self.render_engine = None

    def _init_physics(self):
        """Physics engine initialize karta hai"""
        try:
            from src.physics.physics_engine import PhysicsEngine
            self.physics_engine = PhysicsEngine(self.config)
            self.logger.info("Physics engine initialized.")
        except ImportError as e:
            self.logger.warning(f"Physics import pending: {e}")
            self.physics_engine = None

    def _init_ai_systems(self):
        """AI systems initialize karta hai"""
        try:
            from src.ai.tts_engine import TTSEngine
            from src.ai.lipsync_engine import LipsyncEngine
            from src.ai.expression_engine import ExpressionEngine

            self.tts_engine = TTSEngine(self.config)
            self.lipsync_engine = LipsyncEngine(self.config)
            self.expression_engine = ExpressionEngine(self.config)

            self.logger.info("AI systems initialized.")
        except ImportError as e:
            self.logger.warning(f"AI systems import pending: {e}")
            self.tts_engine = None
            self.lipsync_engine = None
            self.expression_engine = None

    def _init_audio(self):
        """Audio engine initialize karta hai"""
        try:
            from src.audio.audio_engine import AudioEngine
            self.audio_engine = AudioEngine(self.config)
            self.logger.info("Audio engine initialized.")
        except ImportError as e:
            self.logger.warning(f"Audio import pending: {e}")
            self.audio_engine = None

    def _init_main_window(self):
        """Main UI Window banata hai"""
        try:
            from src.ui.main_window import MainWindow

            # Naya MainWindow sirf config leta hai
            self.main_window_wrapper = MainWindow(config=self.config)
            # Actual Qt window nikaal lo
            self.main_window = self.main_window_wrapper.get_window()

            # Sample scene load karo demo ke liye
            self._load_sample_scene()

            self.logger.info("Main window created.")
        except ImportError as e:
            self.logger.warning(f"UI import pending: {e}")
            self._create_placeholder_window()
        except Exception as e:
            self.logger.error(f"Main window error: {e}")
            import traceback
            traceback.print_exc()
            self._create_placeholder_window()

    def _load_sample_scene(self):
        """Sample scene aur assets load karo demo ke liye"""
        try:
            if not self.main_window_wrapper:
                return

            wrapper = self.main_window_wrapper

            # Sample scene objects
            if wrapper.scene_model:
                wrapper.scene_model.add_object("Main Camera", "camera")
                wrapper.scene_model.add_object("Sun Light", "light")
                wrapper.scene_model.add_object("Ground Plane", "mesh")
                wrapper.scene_model.add_object("Hero Character", "character")

                if wrapper.hierarchy_widget:
                    wrapper.hierarchy_widget.refresh_tree()

            # Sample timeline clips
            if wrapper.timeline_model:
                video_tracks = wrapper.timeline_model.get_tracks_by_type("video")
                if video_tracks:
                    wrapper.timeline_model.add_clip(
                        video_tracks[0].id, "Intro Scene", 0, 90
                    )
                    wrapper.timeline_model.add_clip(
                        video_tracks[0].id, "Main Content", 90, 180
                    )

                audio_tracks = wrapper.timeline_model.get_tracks_by_type("audio")
                if audio_tracks:
                    wrapper.timeline_model.add_clip(
                        audio_tracks[0].id, "Background Music", 0, 270
                    )

            # Sample assets
            if wrapper.asset_model:
                if len(wrapper.asset_model.get_all_assets()) < 5:
                    wrapper.asset_model.create_sample_assets()
                if wrapper.asset_browser:
                    wrapper.asset_browser.refresh()

            self.logger.info("Sample scene loaded")

        except Exception as e:
            self.logger.warning(f"Sample scene load warning: {e}")
    def _create_placeholder_window(self):
        """
        Jab tak saari files na ban jayein,
        ye placeholder window dikhata hai.
        """
        from PyQt5.QtWidgets import (
            QMainWindow, QLabel, QVBoxLayout,
            QWidget, QProgressBar
        )
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QFont, QColor, QPalette # type: ignore

        class PlaceholderWindow(QMainWindow):
            def __init__(self):
                super().__init__()
                self.setWindowTitle("3D Animation Studio v1.0.0")
                self.setMinimumSize(1200, 700)
                self.setStyleSheet("""
                    QMainWindow {
                        background-color: #0F0F19;
                    }
                    QLabel {
                        color: #00D4FF;
                        font-family: 'Segoe UI';
                    }
                    QProgressBar {
                        border: 2px solid #00D4FF;
                        border-radius: 5px;
                        background-color: #1A1A2E;
                        color: white;
                        text-align: center;
                    }
                    QProgressBar::chunk {
                        background-color: #00D4FF;
                        border-radius: 3px;
                    }
                """)

                central = QWidget()
                self.setCentralWidget(central)
                layout = QVBoxLayout(central)
                layout.setAlignment(Qt.AlignCenter)
                layout.setSpacing(20)

                title = QLabel("3D Animation Studio")
                title.setFont(QFont("Segoe UI", 36, QFont.Bold))
                title.setAlignment(Qt.AlignCenter)

                subtitle = QLabel(
                    "System Initialized Successfully\n"
                    "UI Components Loading..."
                )
                subtitle.setFont(QFont("Segoe UI", 14))
                subtitle.setAlignment(Qt.AlignCenter)
                subtitle.setStyleSheet("color: #8888AA;")

                status = QLabel(
                    "✅ Config Loaded\n"
                    "✅ Logging Active\n"
                    "✅ Directories Created\n"
                    "⏳ UI Files Being Built..."
                )
                status.setFont(QFont("Segoe UI", 12))
                status.setAlignment(Qt.AlignCenter)
                status.setStyleSheet("color: #00FF88;")

                layout.addWidget(title)
                layout.addWidget(subtitle)
                layout.addWidget(status)

        self.main_window = PlaceholderWindow()
        self.logger.info("Placeholder window created.")

    def run(self):
        """Application run karta hai"""
        try:
            self.logger.info("Starting application...")

            # Initialize karo
            self.initialize()

            # Splash close karo, main window dikhao
            import time
            time.sleep(0.5)

            if self.main_window:
                # Center the window
                from PyQt5.QtWidgets import QDesktopWidget
                screen = QDesktopWidget().screenGeometry()
                window_size = self.main_window.size()
                x = (screen.width() - window_size.width()) // 2
                y = (screen.height() - window_size.height()) // 2
                self.main_window.move(x, y)

                self.main_window.show()

            # Splash screen close karo
            if self.splash:
                self.splash.finish(self.main_window)

            self.logger.info("Application is running.")
            self.logger.info("=" * 60)

            # Qt event loop start karo
            exit_code = self.qt_app.exec_()

            self.logger.info("Application closing...")
            self._cleanup()

            return exit_code

        except Exception as e:
            self.logger.critical(f"Fatal error: {e}", exc_info=True)
            self._show_error(str(e))
            return 1

    def _cleanup(self):
        """App close hone par cleanup karta hai"""
        self.logger.info("Running cleanup...")

        try:
            if self.auto_save:
                self.auto_save.stop()
            if self.physics_engine:
                self.physics_engine.shutdown()
            if self.audio_engine:
                self.audio_engine.shutdown()
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")

        # Temp files saaf karo
        try:
            import shutil
            if os.path.exists(TEMP_DIR):
                for f in os.listdir(TEMP_DIR):
                    file_path = os.path.join(TEMP_DIR, f)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                    except Exception:
                        pass
        except Exception as e:
            self.logger.error(f"Temp cleanup error: {e}")

        self.logger.info("Cleanup complete. Goodbye!")

    def _show_error(self, message):
        """Fatal error dialog dikhata hai"""
        try:
            from PyQt5.QtWidgets import QMessageBox, QApplication
            if not QApplication.instance():
                app = QApplication(sys.argv)

            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("3D Animation Studio - Fatal Error")
            msg.setText("A fatal error occurred:")
            msg.setDetailedText(message)
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #1A1A2E;
                    color: white;
                }
            """)
            msg.exec_()
        except Exception:
            print(f"\n[FATAL ERROR] {message}\n")

# ============================================================
# ENTRY POINT
# ============================================================

def main():
    """Main entry point"""

    # Directories create karo
    create_required_directories()

    # Logging setup karo
    logger = setup_logging()

    # PyQt5 check karo
    check_qt()

    # Application start karo
    app = AnimationStudioApp()
    exit_code = app.run()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()