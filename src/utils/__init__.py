# ============================================================
# 3D ANIMATION STUDIO - Utils Package
# ============================================================
# Utility modules ka centralized access.
#
# Usage:
#     from src.utils import get_logger, get_config
#     from src.utils import ensure_dir, read_json
# ============================================================

# Logger exports
from src.utils.logger import (
    get_logger,
    setup_logging,
    log_exception,
    log_performance,
    print_banner,
    print_section,
    LogContext,
    LoggerManager,
    Colors,
)

# Config exports
from src.utils.config_manager import (
    get_config,
    init_config,
    ConfigManager,
    ConfigValidator,
)

# Helpers - Path & File
from src.utils.helpers import (
    # Path helpers
    get_project_root,
    ensure_dir,
    safe_join,
    get_relative_path,
    is_valid_path,
    get_file_extension,
    get_filename_without_ext,
    sanitize_filename,

    # File operations
    read_json,
    write_json,
    copy_file,
    delete_file,
    delete_directory,
    get_file_size,
    get_file_size_readable,
    format_bytes,
    list_files,

    # Hash & IDs
    generate_uuid,
    generate_short_id,
    hash_file,
    hash_string,

    # Math
    clamp,
    lerp,
    map_range,
    distance_3d,
    distance_2d,
    normalize_angle,
    degrees_to_radians,
    radians_to_degrees,

    # Color
    rgb_to_hex,
    hex_to_rgb,
    rgb_to_normalized,
    normalized_to_rgb,

    # Time
    get_timestamp,
    get_readable_time,
    seconds_to_timecode,
    timecode_to_seconds,
    format_duration,
    estimate_time_remaining,

    # Validation
    is_valid_email,
    is_valid_url,
    is_valid_hex_color,
    is_supported_model_format,
    is_supported_image_format,
    is_supported_audio_format,
    is_supported_video_format,

    # System
    get_system_info,
    get_available_ram_mb,
    check_gpu_available,

    # Timing
    timeit,
    Timer,

    # Aspect ratio
    calculate_aspect_ratio,
    resize_maintain_aspect,

    # Safety
    safe_execute,
)

# File manager exports
from src.utils.file_manager import (
    ProjectFileManager,
    TempFileManager,
    ProjectCompressor,
    DiskSpaceMonitor,
)


# Version info
__version__ = "1.0.0"
__all__ = [
    # Logger
    "get_logger", "setup_logging", "log_exception", "log_performance",
    "print_banner", "print_section", "LogContext", "LoggerManager", "Colors",

    # Config
    "get_config", "init_config", "ConfigManager", "ConfigValidator",

    # Helpers
    "get_project_root", "ensure_dir", "safe_join", "get_relative_path",
    "is_valid_path", "get_file_extension", "get_filename_without_ext",
    "sanitize_filename",
    "read_json", "write_json", "copy_file", "delete_file", "delete_directory",
    "get_file_size", "get_file_size_readable", "format_bytes", "list_files",
    "generate_uuid", "generate_short_id", "hash_file", "hash_string",
    "clamp", "lerp", "map_range", "distance_3d", "distance_2d",
    "normalize_angle", "degrees_to_radians", "radians_to_degrees",
    "rgb_to_hex", "hex_to_rgb", "rgb_to_normalized", "normalized_to_rgb",
    "get_timestamp", "get_readable_time", "seconds_to_timecode",
    "timecode_to_seconds", "format_duration", "estimate_time_remaining",
    "is_valid_email", "is_valid_url", "is_valid_hex_color",
    "is_supported_model_format", "is_supported_image_format",
    "is_supported_audio_format", "is_supported_video_format",
    "get_system_info", "get_available_ram_mb", "check_gpu_available",
    "timeit", "Timer",
    "calculate_aspect_ratio", "resize_maintain_aspect", "safe_execute",

    # File manager
    "ProjectFileManager", "TempFileManager", "ProjectCompressor",
    "DiskSpaceMonitor",
]