# ============================================================
# 3D ANIMATION STUDIO - Advanced Logging System
# ============================================================
# Features:
# - Colored console output (dark theme friendly)
# - File rotation (logs bahut bade na hon)
# - Separate log files per module
# - Performance logging
# - Error tracking with stack traces
# - Log level management
# ============================================================

import logging
import logging.handlers
import os
import sys
import traceback
from datetime import datetime
from typing import Optional, Dict
from pathlib import Path

# ============================================================
# COLOR CODES (ANSI) - Console Output Ke Liye
# ============================================================

class Colors:
    """ANSI color codes for terminal output"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Background colors
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


# Windows me colors enable karne ke liye
def enable_windows_colors():
    """Windows terminal me ANSI colors enable karta hai"""
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # Enable ANSI processing
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass


# ============================================================
# COLORED FORMATTER
# ============================================================

class ColoredFormatter(logging.Formatter):
    """
    Custom formatter jo different log levels ke liye
    different colors use karta hai.
    """

    # Level → Color mapping
    LEVEL_COLORS = {
        "DEBUG": Colors.DIM + Colors.CYAN,
        "INFO": Colors.BRIGHT_GREEN,
        "WARNING": Colors.BRIGHT_YELLOW,
        "ERROR": Colors.BRIGHT_RED,
        "CRITICAL": Colors.BOLD + Colors.BG_RED + Colors.WHITE,
    }

    # Level → Symbol mapping
    LEVEL_SYMBOLS = {
        "DEBUG": "🔍",
        "INFO": "ℹ️ ",
        "WARNING": "⚠️ ",
        "ERROR": "❌",
        "CRITICAL": "🔥",
    }

    def __init__(self, use_colors: bool = True, use_symbols: bool = True):
        super().__init__()
        self.use_colors = use_colors
        self.use_symbols = use_symbols

    def format(self, record: logging.LogRecord) -> str:
        # Timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")

        # Level with color
        level_name = record.levelname
        if self.use_colors:
            level_color = self.LEVEL_COLORS.get(level_name, "")
            colored_level = f"{level_color}{level_name:8s}{Colors.RESET}"
        else:
            colored_level = f"{level_name:8s}"

        # Symbol
        symbol = self.LEVEL_SYMBOLS.get(level_name, " ") if self.use_symbols else ""

        # Logger name (module)
        if self.use_colors:
            logger_name = f"{Colors.BLUE}{record.name:20s}{Colors.RESET}"
        else:
            logger_name = f"{record.name:20s}"

        # Message
        message = record.getMessage()
        if self.use_colors:
            if level_name == "ERROR" or level_name == "CRITICAL":
                message = f"{Colors.BRIGHT_RED}{message}{Colors.RESET}"
            elif level_name == "WARNING":
                message = f"{Colors.YELLOW}{message}{Colors.RESET}"

        # Timestamp with dim color
        if self.use_colors:
            timestamp = f"{Colors.DIM}{timestamp}{Colors.RESET}"

        # Final format
        formatted = f"{timestamp} {symbol} {colored_level} │ {logger_name} │ {message}"

        # Exception info agar hai
        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)

        return formatted


# ============================================================
# FILE FORMATTER (Colors ke bina)
# ============================================================

class FileFormatter(logging.Formatter):
    """File logging ke liye plain formatter (no colors)"""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)-20s | %(filename)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


# ============================================================
# LOGGER MANAGER
# ============================================================

class LoggerManager:
    """
    Central logger manager.
    Poore project me consistent logging ke liye.
    """

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        """Singleton pattern - sirf ek instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, logs_dir: Optional[str] = None,
                 log_level: str = "DEBUG",
                 max_file_size_mb: int = 10,
                 backup_count: int = 5,
                 use_colors: bool = True):
        """
        Args:
            logs_dir: Logs kahan save honge
            log_level: DEBUG, INFO, WARNING, ERROR, CRITICAL
            max_file_size_mb: Max log file size (rotation ke liye)
            backup_count: Kitne backup log files rakhne hain
            use_colors: Console me colors use kare ya nahi
        """
        if self._initialized:
            return

        self._initialized = True

        # Windows colors enable karo
        enable_windows_colors()

        # Default logs directory
        if logs_dir is None:
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            logs_dir = os.path.join(project_root, "logs")

        self.logs_dir = logs_dir
        self.log_level = self._parse_level(log_level)
        self.max_file_size = max_file_size_mb * 1024 * 1024  # MB to bytes
        self.backup_count = backup_count
        self.use_colors = use_colors

        # Logs directory banao
        os.makedirs(self.logs_dir, exist_ok=True)

        # Loggers dictionary
        self.loggers: Dict[str, logging.Logger] = {}

        # Session log file (main log jisme sab kuch aayega)
        self.session_log_file = os.path.join(
            self.logs_dir,
            f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

        # Error log file (sirf errors)
        self.error_log_file = os.path.join(self.logs_dir, "errors.log")

        # Setup root logger
        self._setup_root_logger()

        # Purane logs cleanup karo
        self._cleanup_old_logs()

    def _parse_level(self, level: str) -> int:
        """String log level ko int me convert karta hai"""
        levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        return levels.get(level.upper(), logging.DEBUG)

    def _setup_root_logger(self):
        """Root logger configure karta hai"""
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)

        # Purane handlers hatao (agar koi hain)
        root_logger.handlers.clear()

        # 1. Console Handler (colored)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(
            ColoredFormatter(use_colors=self.use_colors, use_symbols=True)
        )
        root_logger.addHandler(console_handler)

        # 2. Session File Handler (rotating)
        session_handler = logging.handlers.RotatingFileHandler(
            self.session_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding="utf-8"
        )
        session_handler.setLevel(logging.DEBUG)  # File me sab kuch save karo
        session_handler.setFormatter(FileFormatter())
        root_logger.addHandler(session_handler)

        # 3. Error File Handler (sirf errors)
        error_handler = logging.handlers.RotatingFileHandler(
            self.error_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(FileFormatter())
        root_logger.addHandler(error_handler)

        # Third-party libraries ka verbose logging suppress karo
        self._suppress_third_party()

    def _suppress_third_party(self):
        """Third-party libraries ke unnecessary logs suppress karta hai"""
        suppress_list = [
            "PIL", "urllib3", "matplotlib", "numba",
            "torch", "transformers", "trimesh",
            "OpenGL", "asyncio", "pyglet",
        ]
        for lib in suppress_list:
            logging.getLogger(lib).setLevel(logging.WARNING)

    def _cleanup_old_logs(self, max_age_days: int = 7):
        """
        Purane log files delete karta hai.
        Disk space bachane ke liye.
        """
        try:
            now = datetime.now()
            for filename in os.listdir(self.logs_dir):
                filepath = os.path.join(self.logs_dir, filename)
                if os.path.isfile(filepath) and filename.startswith("session_"):
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    age_days = (now - file_time).days
                    if age_days > max_age_days:
                        try:
                            os.remove(filepath)
                        except Exception:
                            pass
        except Exception:
            pass

    def get_logger(self, name: str) -> logging.Logger:
        """
        Naya logger create karta hai ya existing return karta hai.

        Usage:
            logger = LoggerManager().get_logger("MyModule")
            logger.info("Hello")
        """
        if name not in self.loggers:
            logger = logging.getLogger(name)
            self.loggers[name] = logger
        return self.loggers[name]

    def set_level(self, level: str):
        """Runtime me log level change karta hai"""
        new_level = self._parse_level(level)
        self.log_level = new_level

        root_logger = logging.getLogger()
        root_logger.setLevel(new_level)

        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and \
               not isinstance(handler, logging.FileHandler):
                handler.setLevel(new_level)

    def get_log_file_path(self) -> str:
        """Current session log file ka path return karta hai"""
        return self.session_log_file

    def get_error_log_path(self) -> str:
        """Error log file ka path return karta hai"""
        return self.error_log_file


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def get_logger(name: str) -> logging.Logger:
    """
    Quick access function.

    Usage:
        from src.utils.logger import get_logger
        logger = get_logger("MyModule")
        logger.info("Hello world")
    """
    manager = LoggerManager()
    return manager.get_logger(name)


def setup_logging(logs_dir: Optional[str] = None,
                  log_level: str = "DEBUG",
                  use_colors: bool = True) -> LoggerManager:
    """
    Logging system initialize karta hai.
    App start hote hi call karna chahiye.

    Usage:
        from src.utils.logger import setup_logging
        setup_logging()
    """
    return LoggerManager(
        logs_dir=logs_dir,
        log_level=log_level,
        use_colors=use_colors
    )


def log_exception(logger: logging.Logger, exception: Exception,
                  context: str = ""):
    """
    Exception ko detailed stack trace ke saath log karta hai.

    Usage:
        try:
            risky_operation()
        except Exception as e:
            log_exception(logger, e, "During risky operation")
    """
    tb_str = traceback.format_exception(
        type(exception), exception, exception.__traceback__
    )
    tb_text = "".join(tb_str)

    if context:
        logger.error(f"{context}: {exception}")
    else:
        logger.error(f"Exception: {exception}")

    logger.error(f"Traceback:\n{tb_text}")


def log_performance(logger: logging.Logger, operation: str,
                    duration_seconds: float,
                    threshold_seconds: float = 1.0):
    """
    Performance metrics log karta hai.
    Slow operations ko warning ke saath log karta hai.
    """
    if duration_seconds > threshold_seconds:
        logger.warning(
            f"SLOW: {operation} took {duration_seconds:.3f}s "
            f"(threshold: {threshold_seconds}s)"
        )
    else:
        logger.debug(f"{operation} completed in {duration_seconds:.3f}s")


# ============================================================
# CONTEXT MANAGERS
# ============================================================

class LogContext:
    """
    Context manager jo entry/exit log karta hai.

    Usage:
        with LogContext(logger, "Loading model"):
            load_heavy_model()
    """
    def __init__(self, logger: logging.Logger, operation: str,
                 log_level: str = "INFO"):
        self.logger = logger
        self.operation = operation
        self.log_level = log_level.upper()
        self.start_time = None

    def __enter__(self):
        import time
        self.start_time = time.time()
        self._log(f"▶ Starting: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        duration = time.time() - self.start_time

        if exc_type is None:
            self._log(f"✓ Completed: {self.operation} ({duration:.2f}s)")
        else:
            self.logger.error(
                f"✗ Failed: {self.operation} ({duration:.2f}s) - {exc_val}"
            )
        return False  # Exception ko propagate karo

    def _log(self, message: str):
        level_map = {
            "DEBUG": self.logger.debug,
            "INFO": self.logger.info,
            "WARNING": self.logger.warning,
            "ERROR": self.logger.error,
        }
        log_func = level_map.get(self.log_level, self.logger.info)
        log_func(message)


# ============================================================
# BANNER PRINTING
# ============================================================

def print_banner(title: str, subtitle: str = "", width: int = 70):
    """
    Beautiful banner print karta hai.
    App start hote waqt use karo.
    """
    logger = get_logger("Banner")

    line = "═" * width
    logger.info(line)

    # Title centered
    padding = (width - len(title)) // 2
    logger.info(" " * padding + title)

    if subtitle:
        sub_padding = (width - len(subtitle)) // 2
        logger.info(" " * sub_padding + subtitle)

    logger.info(line)


def print_section(section_name: str, width: int = 70):
    """Section separator print karta hai"""
    logger = get_logger("Section")
    logger.info("─" * width)
    logger.info(f"  {section_name}")
    logger.info("─" * width)


# ============================================================
# TEST FUNCTION
# ============================================================

if __name__ == "__main__":
    # Logging setup karo
    setup_logging(log_level="DEBUG")

    # Banner print karo
    print_banner(
        "3D Animation Studio",
        "Logger Module Test v1.0.0"
    )

    # Test different log levels
    logger = get_logger("TestModule")

    logger.debug("This is a DEBUG message - for developers")
    logger.info("This is an INFO message - general information")
    logger.warning("This is a WARNING - something might be wrong")
    logger.error("This is an ERROR - something went wrong")
    logger.critical("This is CRITICAL - major issue!")

    print_section("Testing Context Manager")

    # Test context manager
    import time
    with LogContext(logger, "Simulating heavy operation"):
        time.sleep(0.5)

    print_section("Testing Exception Logging")

    # Test exception logging
    try:
        result = 10 / 0
    except Exception as e:
        log_exception(logger, e, "Division by zero test")

    print_section("Testing Performance Logging")

    # Test performance logging
    log_performance(logger, "Fast operation", 0.05, threshold_seconds=1.0)
    log_performance(logger, "Slow operation", 2.5, threshold_seconds=1.0)

    print_section("Log File Locations")

    manager = LoggerManager()
    logger.info(f"Session log: {manager.get_log_file_path()}")
    logger.info(f"Error log: {manager.get_error_log_path()}")

    print_banner("✅ All Tests Passed", "Logger Module Working")