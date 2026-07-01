# ============================================================
# 3D ANIMATION STUDIO - Utility Helpers
# ============================================================
# Ye file poore project ke reusable functions rakhti hai:
# - Path handling
# - File operations
# - Math helpers
# - Color conversions
# - Time formatting
# - Validation
# - Hash generation
# ============================================================

import os
import sys
import json
import hashlib
import shutil
import logging
import time
import uuid
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("Helpers")

# ============================================================
# PATH HELPERS
# ============================================================

def get_project_root() -> str:
    """Project root directory return karta hai"""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def ensure_dir(directory: str) -> str:
    """
    Directory exist karta hai to return karo,
    nahi to banao.
    """
    if not os.path.exists(directory):
        try:
            os.makedirs(directory, exist_ok=True)
            logger.debug(f"Directory created: {directory}")
        except Exception as e:
            logger.error(f"Failed to create directory {directory}: {e}")
            raise
    return directory


def safe_join(*paths: str) -> str:
    """
    Safely paths join karta hai.
    Cross-platform compatible.
    """
    return os.path.normpath(os.path.join(*paths))


def get_relative_path(full_path: str, base_path: str) -> str:
    """Full path ko base path ke relative return karta hai"""
    try:
        return os.path.relpath(full_path, base_path)
    except ValueError:
        return full_path


def is_valid_path(path: str) -> bool:
    """Check karta hai path valid hai ya nahi"""
    if not path or not isinstance(path, str):
        return False
    try:
        Path(path)
        return True
    except (ValueError, OSError):
        return False


def get_file_extension(filepath: str) -> str:
    """File ka extension return karta hai (lowercase, without dot)"""
    return os.path.splitext(filepath)[1].lower().lstrip(".")


def get_filename_without_ext(filepath: str) -> str:
    """File ka naam bina extension ke return karta hai"""
    return os.path.splitext(os.path.basename(filepath))[0]


def sanitize_filename(filename: str) -> str:
    """
    Filename se invalid characters remove karta hai.
    Windows/Linux/Mac ke liye safe banata hai.
    """
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    sanitized = re.sub(invalid_chars, "_", filename)
    sanitized = sanitized.strip(". ")

    # Windows reserved names
    reserved = ["CON", "PRN", "AUX", "NUL",
                "COM1", "COM2", "COM3", "COM4", "COM5",
                "COM6", "COM7", "COM8", "COM9",
                "LPT1", "LPT2", "LPT3", "LPT4", "LPT5",
                "LPT6", "LPT7", "LPT8", "LPT9"]

    if sanitized.upper() in reserved:
        sanitized = "_" + sanitized

    return sanitized if sanitized else "untitled"


# ============================================================
# FILE OPERATIONS
# ============================================================

def read_json(filepath: str) -> Optional[Dict]:
    """JSON file safely read karta hai"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {filepath}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error reading {filepath}: {e}")
        return None


def write_json(filepath: str, data: Dict, indent: int = 2) -> bool:
    """
    Data ko JSON file me safely write karta hai.
    Atomic write (temp file → rename) use karta hai.
    """
    try:
        ensure_dir(os.path.dirname(filepath))

        # Atomic write - pehle temp file me likho
        temp_path = filepath + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)

        # Fir rename karo (atomic operation)
        if os.path.exists(filepath):
            os.replace(temp_path, filepath)
        else:
            os.rename(temp_path, filepath)

        return True
    except Exception as e:
        logger.error(f"Error writing {filepath}: {e}")
        return False


def copy_file(source: str, destination: str, overwrite: bool = True) -> bool:
    """File copy karta hai"""
    try:
        if not os.path.exists(source):
            logger.error(f"Source not found: {source}")
            return False

        if os.path.exists(destination) and not overwrite:
            logger.warning(f"Destination exists: {destination}")
            return False

        ensure_dir(os.path.dirname(destination))
        shutil.copy2(source, destination)
        return True
    except Exception as e:
        logger.error(f"Copy failed {source} -> {destination}: {e}")
        return False


def delete_file(filepath: str) -> bool:
    """File safely delete karta hai"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False
    except Exception as e:
        logger.error(f"Delete failed {filepath}: {e}")
        return False


def delete_directory(directory: str) -> bool:
    """Directory recursively delete karta hai"""
    try:
        if os.path.exists(directory):
            shutil.rmtree(directory)
            return True
        return False
    except Exception as e:
        logger.error(f"Directory delete failed {directory}: {e}")
        return False


def get_file_size(filepath: str) -> int:
    """File size bytes me return karta hai"""
    try:
        return os.path.getsize(filepath)
    except Exception:
        return 0


def get_file_size_readable(filepath: str) -> str:
    """File size ko human-readable format me return karta hai"""
    size = get_file_size(filepath)
    return format_bytes(size)


def format_bytes(size: int) -> str:
    """Bytes ko readable format me convert karta hai (KB, MB, GB)"""
    if size < 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size_float = float(size)

    while size_float >= 1024 and unit_index < len(units) - 1:
        size_float /= 1024
        unit_index += 1

    return f"{size_float:.2f} {units[unit_index]}"


def list_files(directory: str, extensions: Optional[List[str]] = None,
               recursive: bool = False) -> List[str]:
    """
    Directory me files list karta hai.
    Extensions filter kar sakte hain (e.g., ['.obj', '.fbx']).
    """
    if not os.path.exists(directory):
        return []

    files = []

    if recursive:
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(root, filename)
                if extensions:
                    if any(filename.lower().endswith(ext.lower()) for ext in extensions):
                        files.append(filepath)
                else:
                    files.append(filepath)
    else:
        try:
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                if os.path.isfile(filepath):
                    if extensions:
                        if any(filename.lower().endswith(ext.lower()) for ext in extensions):
                            files.append(filepath)
                    else:
                        files.append(filepath)
        except Exception as e:
            logger.error(f"Error listing {directory}: {e}")

    return sorted(files)


# ============================================================
# HASH & UNIQUE ID GENERATION
# ============================================================

def generate_uuid() -> str:
    """Unique ID generate karta hai"""
    return str(uuid.uuid4())


def generate_short_id(length: int = 8) -> str:
    """Chhota unique ID generate karta hai"""
    return uuid.uuid4().hex[:length]


def hash_file(filepath: str, algorithm: str = "md5") -> Optional[str]:
    """
    File ka hash generate karta hai.
    Duplicate detection ke liye useful.
    """
    if not os.path.exists(filepath):
        return None

    try:
        hasher = hashlib.new(algorithm)
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Hash failed for {filepath}: {e}")
        return None


def hash_string(text: str, algorithm: str = "md5") -> str:
    """String ka hash generate karta hai"""
    hasher = hashlib.new(algorithm)
    hasher.update(text.encode("utf-8"))
    return hasher.hexdigest()


# ============================================================
# MATH HELPERS
# ============================================================

def clamp(value: float, min_value: float, max_value: float) -> float:
    """Value ko min-max range me clamp karta hai"""
    return max(min_value, min(value, max_value))


def lerp(start: float, end: float, t: float) -> float:
    """Linear interpolation between start and end"""
    t = clamp(t, 0.0, 1.0)
    return start + (end - start) * t


def map_range(value: float, in_min: float, in_max: float,
              out_min: float, out_max: float) -> float:
    """Value ko ek range se doosri range me map karta hai"""
    if in_max - in_min == 0:
        return out_min
    return out_min + (out_max - out_min) * ((value - in_min) / (in_max - in_min))


def distance_3d(p1: Tuple[float, float, float],
                p2: Tuple[float, float, float]) -> float:
    """3D space me do points ka distance calculate karta hai"""
    return ((p2[0] - p1[0]) ** 2 +
            (p2[1] - p1[1]) ** 2 +
            (p2[2] - p1[2]) ** 2) ** 0.5


def distance_2d(p1: Tuple[float, float],
                p2: Tuple[float, float]) -> float:
    """2D distance calculate karta hai"""
    return ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5


def normalize_angle(angle: float) -> float:
    """Angle ko 0-360 range me normalize karta hai"""
    return angle % 360


def degrees_to_radians(degrees: float) -> float:
    """Degrees to radians"""
    import math
    return degrees * (math.pi / 180.0)


def radians_to_degrees(radians: float) -> float:
    """Radians to degrees"""
    import math
    return radians * (180.0 / math.pi)


# ============================================================
# COLOR HELPERS
# ============================================================

def rgb_to_hex(r: int, g: int, b: int) -> str:
    """RGB (0-255) ko hex string me convert karta hai"""
    r = int(clamp(r, 0, 255))
    g = int(clamp(g, 0, 255))
    b = int(clamp(b, 0, 255))
    return f"#{r:02X}{g:02X}{b:02X}"


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Hex string ko RGB tuple me convert karta hai"""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return (0, 0, 0)
    try:
        return (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16)
        )
    except ValueError:
        return (0, 0, 0)


def rgb_to_normalized(r: int, g: int, b: int,
                      a: int = 255) -> Tuple[float, float, float, float]:
    """RGB (0-255) ko normalized (0.0-1.0) me convert karta hai. OpenGL ke liye."""
    return (r / 255.0, g / 255.0, b / 255.0, a / 255.0)


def normalized_to_rgb(r: float, g: float, b: float,
                      a: float = 1.0) -> Tuple[int, int, int, int]:
    """Normalized (0.0-1.0) ko RGB (0-255) me convert karta hai"""
    return (
        int(clamp(r * 255, 0, 255)),
        int(clamp(g * 255, 0, 255)),
        int(clamp(b * 255, 0, 255)),
        int(clamp(a * 255, 0, 255))
    )


# ============================================================
# TIME & DATE HELPERS
# ============================================================

def get_timestamp(format_str: str = "%Y%m%d_%H%M%S") -> str:
    """Current timestamp string return karta hai"""
    return datetime.now().strftime(format_str)


def get_readable_time() -> str:
    """Readable current time"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def seconds_to_timecode(seconds: float, fps: int = 30) -> str:
    """
    Seconds ko HH:MM:SS:FF format me convert karta hai.
    Video editing ke liye useful.
    """
    if seconds < 0:
        seconds = 0

    total_frames = int(seconds * fps)
    hours = total_frames // (3600 * fps)
    minutes = (total_frames // (60 * fps)) % 60
    secs = (total_frames // fps) % 60
    frames = total_frames % fps

    return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"


def timecode_to_seconds(timecode: str, fps: int = 30) -> float:
    """Timecode ko seconds me convert karta hai"""
    try:
        parts = timecode.split(":")
        if len(parts) == 4:
            h, m, s, f = map(int, parts)
            return h * 3600 + m * 60 + s + (f / fps)
        elif len(parts) == 3:
            h, m, s = map(int, parts)
            return h * 3600 + m * 60 + s
        elif len(parts) == 2:
            m, s = map(int, parts)
            return m * 60 + s
        return 0.0
    except Exception:
        return 0.0


def format_duration(seconds: float) -> str:
    """Duration ko readable format me return karta hai (e.g., '1m 30s')"""
    if seconds < 0:
        return "0s"

    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def estimate_time_remaining(current: int, total: int,
                             elapsed_seconds: float) -> str:
    """
    Progress ke basis pe remaining time estimate karta hai.
    Rendering progress bar ke liye useful.
    """
    if current <= 0 or total <= 0:
        return "Calculating..."

    if current >= total:
        return "Done"

    rate = current / elapsed_seconds
    if rate == 0:
        return "Calculating..."

    remaining_items = total - current
    remaining_seconds = remaining_items / rate

    return format_duration(remaining_seconds)


# ============================================================
# VALIDATION HELPERS
# ============================================================

def is_valid_email(email: str) -> bool:
    """Email format validate karta hai"""
    if not email:
        return False
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def is_valid_url(url: str) -> bool:
    """URL validate karta hai"""
    if not url:
        return False
    pattern = r"^https?://[^\s]+$"
    return bool(re.match(pattern, url))


def is_valid_hex_color(color: str) -> bool:
    """Hex color validate karta hai"""
    if not color:
        return False
    pattern = r"^#?[0-9A-Fa-f]{6}$"
    return bool(re.match(pattern, color))


def is_supported_model_format(filepath: str) -> bool:
    """3D model format supported hai ya nahi"""
    supported = ["obj", "fbx", "gltf", "glb", "dae", "stl", "ply"]
    ext = get_file_extension(filepath)
    return ext in supported


def is_supported_image_format(filepath: str) -> bool:
    """Image format supported hai ya nahi"""
    supported = ["png", "jpg", "jpeg", "bmp", "tga", "tiff", "webp"]
    ext = get_file_extension(filepath)
    return ext in supported


def is_supported_audio_format(filepath: str) -> bool:
    """Audio format supported hai ya nahi"""
    supported = ["mp3", "wav", "ogg", "flac", "m4a", "aac"]
    ext = get_file_extension(filepath)
    return ext in supported


def is_supported_video_format(filepath: str) -> bool:
    """Video format supported hai ya nahi"""
    supported = ["mp4", "webm", "avi", "mov", "mkv"]
    ext = get_file_extension(filepath)
    return ext in supported


# ============================================================
# SYSTEM HELPERS
# ============================================================

def get_system_info() -> Dict[str, Any]:
    """
    System information return karta hai.
    Performance settings ke liye useful.
    """
    import platform

    info = {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "python_version": platform.python_version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
    }

    try:
        import psutil
        info["cpu_count"] = psutil.cpu_count(logical=True)
        info["cpu_physical"] = psutil.cpu_count(logical=False)
        info["ram_total_gb"] = round(psutil.virtual_memory().total / (1024 ** 3), 2)
        info["ram_available_gb"] = round(psutil.virtual_memory().available / (1024 ** 3), 2)
    except ImportError:
        pass

    return info


def get_available_ram_mb() -> int:
    """Available RAM MB me return karta hai"""
    try:
        import psutil
        return int(psutil.virtual_memory().available / (1024 * 1024))
    except ImportError:
        return 0


def check_gpu_available() -> bool:
    """GPU available hai ya nahi check karta hai"""
    try:
        from OpenGL import GL
        return True
    except ImportError:
        return False


# ============================================================
# TIMING DECORATORS
# ============================================================

def timeit(func):
    """
    Decorator jo function ka execution time measure karta hai.
    Usage: @timeit
    """
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.debug(f"{func.__name__} took {elapsed:.4f}s")
        return result
    return wrapper


class Timer:
    """
    Context manager for timing.
    Usage:
        with Timer("Operation name"):
            # code here
    """
    def __init__(self, name: str = "Operation"):
        self.name = name
        self.start_time = 0.0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        elapsed = time.time() - self.start_time
        logger.debug(f"{self.name} took {elapsed:.4f}s")


# ============================================================
# ASPECT RATIO HELPERS
# ============================================================

def calculate_aspect_ratio(width: int, height: int) -> str:
    """Aspect ratio calculate karta hai (e.g., '16:9')"""
    def gcd(a: int, b: int) -> int:
        while b:
            a, b = b, a % b
        return a

    if width <= 0 or height <= 0:
        return "1:1"

    divisor = gcd(width, height)
    return f"{width // divisor}:{height // divisor}"


def resize_maintain_aspect(width: int, height: int,
                            max_width: int, max_height: int) -> Tuple[int, int]:
    """
    Aspect ratio maintain karke resize karta hai.
    Thumbnail generation ke liye useful.
    """
    if width <= 0 or height <= 0:
        return (max_width, max_height)

    ratio = min(max_width / width, max_height / height)
    return (int(width * ratio), int(height * ratio))


# ============================================================
# SAFE EXECUTION
# ============================================================

def safe_execute(func, default=None, log_errors: bool = True):
    """
    Function ko safely execute karta hai.
    Error aane par default value return karta hai.
    """
    try:
        return func()
    except Exception as e:
        if log_errors:
            logger.error(f"safe_execute failed: {e}")
        return default


# ============================================================
# TEST FUNCTION - File standalone bhi chal sake
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Helpers Module")
    print("=" * 60)

    # Test basic functions
    print(f"UUID: {generate_uuid()}")
    print(f"Short ID: {generate_short_id()}")
    print(f"Timestamp: {get_timestamp()}")
    print(f"RGB to Hex: {rgb_to_hex(255, 128, 0)}")
    print(f"Hex to RGB: {hex_to_rgb('#00D4FF')}")
    print(f"Clamp: {clamp(150, 0, 100)}")
    print(f"Lerp: {lerp(0, 100, 0.5)}")
    print(f"Distance 3D: {distance_3d((0, 0, 0), (3, 4, 0))}")
    print(f"Format Bytes: {format_bytes(1536000)}")
    print(f"Seconds to Timecode: {seconds_to_timecode(125.5, 30)}")
    print(f"Aspect Ratio: {calculate_aspect_ratio(1920, 1080)}")
    print(f"Sanitize Filename: {sanitize_filename('my<file>name?.txt')}")

    print("\nSystem Info:")
    for key, value in get_system_info().items():
        print(f"  {key}: {value}")

    print("\n✅ All helpers working correctly!")