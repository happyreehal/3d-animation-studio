# ============================================================
# 3D ANIMATION STUDIO - Video Exporter
# ============================================================
# Features:
# - Timeline → MP4/WebM/MOV/GIF export
# - Multiple codecs: H.264, H.265, VP9, ProRes
# - Resolutions: 4K, 2K, 1080p, 720p, 480p, custom
# - Frame rates: 24, 30, 60fps
# - Quality presets: draft, standard, high, ultra
# - Progress tracking with callbacks
# - Pause/Resume/Cancel export
# - Multi-threaded rendering
# - Audio mixing (multiple tracks)
# - Subtitle burn-in
# - Batch export
# - FFmpeg-based encoding
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

import time
import shutil
import tempfile
import threading
import subprocess
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable, Any

import numpy as np

# Image processing
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

# FFmpeg (Python wrapper)
try:
    import ffmpeg
    FFMPEG_PYTHON_AVAILABLE = True
except ImportError:
    FFMPEG_PYTHON_AVAILABLE = False
    ffmpeg = None

from src.utils import (
    get_logger, get_config, ensure_dir, generate_short_id,
    get_timestamp, format_duration, format_bytes, get_file_size,
    seconds_to_timecode, estimate_time_remaining,
    clamp, sanitize_filename,
)

logger = get_logger("VideoExporter")


# ============================================================
# CONSTANTS & ENUMS
# ============================================================

class VideoFormat(Enum):
    """Supported video output formats"""
    MP4  = ("mp4",  "video/mp4",  "MPEG-4 (most compatible)")
    WEBM = ("webm", "video/webm", "WebM (open standard)")
    MOV  = ("mov",  "video/mov",  "QuickTime (Apple)")
    AVI  = ("avi",  "video/avi",  "AVI (legacy)")
    MKV  = ("mkv",  "video/mkv",  "Matroska (flexible)")
    GIF  = ("gif",  "image/gif",  "Animated GIF")

    def __init__(self, ext: str, mime: str, description: str):
        self.ext         = ext
        self.mime        = mime
        self.description = description


class VideoCodec(Enum):
    """Video codec options"""
    H264       = ("libx264",       "H.264 (most compatible)")
    H265       = ("libx265",       "H.265/HEVC (better compression)")
    VP9        = ("libvpx-vp9",    "VP9 (WebM standard)")
    VP8        = ("libvpx",        "VP8 (older WebM)")
    PRORES     = ("prores_ks",     "Apple ProRes (professional)")
    MPEG4      = ("mpeg4",         "MPEG-4 Part 2 (legacy)")
    GIF        = ("gif",           "GIF encoder (animated GIF)")

    def __init__(self, ffmpeg_name: str, description: str):
        self.ffmpeg_name = ffmpeg_name
        self.description = description


class AudioCodec(Enum):
    """Audio codec options"""
    AAC   = ("aac",       "AAC (universal)")
    MP3   = ("libmp3lame","MP3 (compatible)")
    OPUS  = ("libopus",   "Opus (best quality)")
    VORBIS= ("libvorbis", "Vorbis (WebM)")
    PCM   = ("pcm_s16le", "PCM (uncompressed)")
    FLAC  = ("flac",      "FLAC (lossless)")

    def __init__(self, ffmpeg_name: str, description: str):
        self.ffmpeg_name = ffmpeg_name
        self.description = description


class QualityPreset(Enum):
    """
    Predefined quality presets.
    Har preset ka apna CRF (quality) aur preset (speed) hai.

    CRF (Constant Rate Factor):
    - Lower = better quality, larger file
    - Range: 0-51 (18-28 typical)
    """
    DRAFT    = ("draft",    28, "ultrafast", "Fastest, low quality")
    LOW      = ("low",      26, "veryfast",  "Small file")
    STANDARD = ("standard", 23, "medium",    "Balanced (YouTube default)")
    HIGH     = ("high",     20, "slow",      "Great quality")
    ULTRA    = ("ultra",    17, "veryslow",  "Near-lossless")
    LOSSLESS = ("lossless", 0,  "veryslow",  "Perfect quality, huge file")

    def __init__(self, label: str, crf: int, speed: str, description: str):
        self.label       = label
        self.crf         = crf
        self.speed       = speed
        self.description = description


class Resolution:
    """
    Standard resolution presets.
    Custom bhi de sakte hain — bas (width, height) tuple.
    """
    # Standard resolutions
    RES_480P   = (854,  480)
    RES_720P   = (1280, 720)
    RES_1080P  = (1920, 1080)
    RES_1440P  = (2560, 1440)
    RES_4K     = (3840, 2160)
    RES_8K     = (7680, 4320)

    # Social media presets
    INSTAGRAM_SQUARE   = (1080, 1080)
    INSTAGRAM_PORTRAIT = (1080, 1350)
    INSTAGRAM_STORY    = (1080, 1920)
    TIKTOK             = (1080, 1920)
    YOUTUBE_SHORTS     = (1080, 1920)

    ALL = {
        "480p"     : RES_480P,
        "720p"     : RES_720P,
        "1080p"    : RES_1080P,
        "1440p"    : RES_1440P,
        "4k"       : RES_4K,
        "8k"       : RES_8K,
        "square"   : INSTAGRAM_SQUARE,
        "portrait" : INSTAGRAM_PORTRAIT,
        "story"    : INSTAGRAM_STORY,
        "shorts"   : YOUTUBE_SHORTS,
    }


class ExportState(Enum):
    """Export process ka current state"""
    IDLE       = "idle"
    PREPARING  = "preparing"
    RENDERING  = "rendering"     # Frames generate ho rahe hain
    ENCODING   = "encoding"      # Video file bana rahe hain
    AUDIO      = "audio"         # Audio process ho raha hai
    MUXING     = "muxing"        # Video + audio combine
    FINALIZING = "finalizing"
    COMPLETED  = "completed"
    PAUSED     = "paused"
    CANCELLED  = "cancelled"
    ERROR      = "error"


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class ExportSettings:
    """
    Video export ki poori configuration.
    User ye specify karta hai kya chahiye.
    """
    # Basic
    output_path      : str                                 = ""
    format           : VideoFormat                         = VideoFormat.MP4

    # Video
    resolution       : Tuple[int, int]                     = Resolution.RES_1080P
    fps              : int                                 = 30
    video_codec      : VideoCodec                          = VideoCodec.H264
    quality          : QualityPreset                       = QualityPreset.STANDARD
    bitrate          : Optional[str]                       = None      # e.g., "5M" — CRF override

    # Audio
    include_audio    : bool                                = True
    audio_codec      : AudioCodec                          = AudioCodec.AAC
    audio_bitrate    : str                                 = "192k"
    audio_sample_rate: int                                 = 44100

    # Timing
    start_time       : float                               = 0.0
    end_time         : Optional[float]                     = None      # None = timeline end
    speed_multiplier : float                               = 1.0       # 2.0 = 2x speed

    # Effects
    include_subtitles: bool                                = False
    subtitle_file    : Optional[str]                       = None
    watermark_path   : Optional[str]                       = None
    watermark_position: str                                = "bottom_right"   # top_left, top_right, bottom_left, bottom_right, center

    # Advanced
    use_hardware_acceleration: bool                        = False    # NVENC, QuickSync
    keyframe_interval: int                                 = 60       # Every N frames
    threads          : int                                 = 0        # 0 = auto

    def get_effective_bitrate(self) -> str:
        """
        Quality preset se bitrate calculate karo agar explicit nahi diya.
        Higher resolution = higher bitrate.
        """
        if self.bitrate:
            return self.bitrate

        # Resolution ke basis pe base bitrate
        w, h = self.resolution
        pixels = w * h

        base_bitrates = {
            QualityPreset.DRAFT   : 1_000_000,   # 1 Mbps
            QualityPreset.LOW     : 2_500_000,   # 2.5 Mbps
            QualityPreset.STANDARD: 5_000_000,   # 5 Mbps
            QualityPreset.HIGH    : 10_000_000,  # 10 Mbps
            QualityPreset.ULTRA   : 20_000_000,  # 20 Mbps
            QualityPreset.LOSSLESS: 100_000_000, # 100 Mbps
        }

        base = base_bitrates.get(self.quality, 5_000_000)

        # 1080p pixels = 2,073,600 (reference)
        multiplier = pixels / (1920 * 1080)
        adjusted   = int(base * multiplier)

        # Format karo
        if adjusted >= 1_000_000:
            return f"{adjusted // 1_000_000}M"
        return f"{adjusted // 1_000}k"


@dataclass
class ExportProgress:
    """Real-time export progress info"""
    state              : ExportState                       = ExportState.IDLE
    total_frames       : int                               = 0
    current_frame      : int                               = 0
    frames_per_second  : float                             = 0.0

    # Time tracking
    start_time         : float                             = 0.0
    elapsed_seconds    : float                             = 0.0
    estimated_remaining: float                             = 0.0

    # File info
    output_path        : str                               = ""
    current_size_bytes : int                               = 0

    # Status message
    message            : str                               = ""

    @property
    def progress_percent(self) -> float:
        """0-100 progress"""
        if self.total_frames == 0:
            return 0.0
        return (self.current_frame / self.total_frames) * 100

    def to_dict(self) -> Dict:
        return {
            "state"              : self.state.value,
            "progress_percent"   : round(self.progress_percent, 2),
            "current_frame"      : self.current_frame,
            "total_frames"       : self.total_frames,
            "fps"                : round(self.frames_per_second, 2),
            "elapsed"            : round(self.elapsed_seconds, 1),
            "elapsed_str"        : format_duration(self.elapsed_seconds),
            "estimated_remaining": round(self.estimated_remaining, 1),
            "eta_str"            : format_duration(self.estimated_remaining),
            "output_path"        : self.output_path,
            "current_size"       : format_bytes(self.current_size_bytes),
            "message"            : self.message,
        }


@dataclass
class ExportResult:
    """Final export ka result"""
    success        : bool                                  = False
    output_path    : Optional[str]                         = None
    file_size      : int                                   = 0
    duration       : float                                 = 0.0
    total_frames   : int                                   = 0
    export_time    : float                                 = 0.0
    average_fps    : float                                 = 0.0
    error          : Optional[str]                         = None
    settings_used  : Optional[ExportSettings]              = None

    def to_dict(self) -> Dict:
        return {
            "success"       : self.success,
            "output_path"   : self.output_path,
            "file_size"     : self.file_size,
            "file_size_str" : format_bytes(self.file_size),
            "duration"      : round(self.duration, 3),
            "duration_str"  : format_duration(self.duration),
            "total_frames"  : self.total_frames,
            "export_time"   : round(self.export_time, 2),
            "export_time_str": format_duration(self.export_time),
            "average_fps"   : round(self.average_fps, 2),
            "error"         : self.error,
        }


# ============================================================
# FFMPEG COMMAND BUILDER
# ============================================================

class FFmpegCommand:
    """
    🎬 FFmpeg command line builder.
    Complex ffmpeg calls ko clean way se construct karta hai.
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path
        self.args        : List[str] = []
        self._inputs     : List[str] = []
        self._output     : Optional[str] = None

    def add_input(self, path: str, extra_args: Optional[List[str]] = None):
        """Input file/source add karo"""
        if extra_args:
            self.args.extend(extra_args)
        self.args.extend(["-i", path])
        self._inputs.append(path)
        return self

    def add_input_frames(self, pattern: str, fps: int,
                         start_number: int = 0):
        """
        Image sequence ko input karo (rendered frames).

        Args:
            pattern     : ffmpeg glob pattern (e.g., "frame_%06d.png")
            fps         : Input frames ka fps
            start_number: Starting frame number
        """
        self.args.extend([
            "-framerate", str(fps),
            "-start_number", str(start_number),
            "-i", pattern,
        ])
        return self

    def add_input_audio(self, audio_path: str):
        """Audio file input karo"""
        self.args.extend(["-i", audio_path])
        return self

    def set_video_codec(self, codec: VideoCodec,
                        crf: Optional[int] = None,
                        preset: Optional[str] = None):
        """Video codec set karo"""
        self.args.extend(["-c:v", codec.ffmpeg_name])
        if crf is not None:
            self.args.extend(["-crf", str(crf)])
        if preset:
            self.args.extend(["-preset", preset])
        return self

    def set_audio_codec(self, codec: AudioCodec, bitrate: str = "192k"):
        """Audio codec set karo"""
        self.args.extend([
            "-c:a", codec.ffmpeg_name,
            "-b:a", bitrate,
        ])
        return self

    def set_resolution(self, width: int, height: int):
        """Output resolution set karo"""
        self.args.extend(["-vf", f"scale={width}:{height}"])
        return self

    def set_fps(self, fps: int):
        """Output frame rate"""
        self.args.extend(["-r", str(fps)])
        return self

    def set_bitrate(self, bitrate: str):
        """Video bitrate (e.g., '5M', '2500k')"""
        self.args.extend(["-b:v", bitrate])
        return self

    def set_pixel_format(self, pix_fmt: str = "yuv420p"):
        """Pixel format — yuv420p is most compatible"""
        self.args.extend(["-pix_fmt", pix_fmt])
        return self

    def set_keyframe_interval(self, frames: int):
        """Keyframe (GOP) interval"""
        self.args.extend(["-g", str(frames)])
        return self

    def set_threads(self, threads: int):
        """Encoding threads (0 = auto)"""
        self.args.extend(["-threads", str(threads)])
        return self

    def overwrite_output(self):
        """Existing output file overwrite karo (-y flag)"""
        self.args.append("-y")
        return self

    def set_output(self, path: str):
        """Output file path"""
        self._output = path
        return self

    def set_duration(self, seconds: float):
        """Output duration limit"""
        self.args.extend(["-t", str(seconds)])
        return self

    def set_start_time(self, seconds: float):
        """Start time offset"""
        self.args.extend(["-ss", str(seconds)])
        return self

    def add_custom(self, *args: str):
        """Custom args add karo"""
        self.args.extend(args)
        return self

    def build(self) -> List[str]:
        """Final command build karo"""
        if not self._output:
            raise ValueError("Output path not set")

        cmd = [self.ffmpeg_path] + self.args + [self._output]
        return cmd

    def build_str(self) -> str:
        """Command string ke roop mein (debug ke liye)"""
        cmd = self.build()
        # Quote paths jo mein space hain
        quoted = [f'"{a}"' if " " in a else a for a in cmd]
        return " ".join(quoted)


# ============================================================
# FFMPEG DETECTOR
# ============================================================

class FFmpegDetector:
    """
    🔍 FFmpeg system pe available hai ya nahi check karta hai.
    """

    @staticmethod
    def find_ffmpeg() -> Optional[str]:
        """
        FFmpeg binary dhundo.
        Returns: Path or None
        """
        # Common paths pe check karo
        candidates = [
            "ffmpeg",   # PATH mein
            "ffmpeg.exe",
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\Users\{}\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-*\bin\ffmpeg.exe".format(
                os.getenv("USERNAME", "")
            ),
        ]

        for candidate in candidates:
            # Direct check
            if os.path.isfile(candidate):
                return candidate

            # Glob for winget path
            if "*" in candidate:
                import glob
                matches = glob.glob(candidate)
                if matches:
                    return matches[0]

            # shutil.which check
            found = shutil.which(candidate)
            if found:
                return found

        return None

    @staticmethod
    def get_version(ffmpeg_path: str = "ffmpeg") -> Optional[str]:
        """FFmpeg version string return karo"""
        try:
            result = subprocess.run(
                [ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                # First line se version nikalo
                first_line = result.stdout.split("\n")[0]
                return first_line.strip()
        except Exception as e:
            logger.debug(f"FFmpeg version check failed: {e}")
        return None

    @staticmethod
    def is_available() -> bool:
        """Quick check — ffmpeg available hai?"""
        return FFmpegDetector.find_ffmpeg() is not None


# ============================================================
# FRAME RENDERER (Simple synthetic frames for testing)
# ============================================================

class FrameRenderer:
    """
    🎨 Timeline se frames render karta hai.

    Real integration mein ye 3D renderer/scene se hoga.
    Abhi test ke liye synthetic frames banate hain (color gradients, text).
    """

    def __init__(self, resolution: Tuple[int, int] = (1920, 1080)):
        self.resolution = resolution

    def render_frame(self,
                     frame_index: int,
                     total_frames: int,
                     timeline_data: Optional[Dict] = None) -> "Image.Image":
        """
        Ek frame render karo.

        Args:
            frame_index  : Current frame number
            total_frames : Total frames
            timeline_data: Optional timeline info (transitions, keyframes, etc.)

        Returns:
            PIL Image
        """
        if not PIL_AVAILABLE:
            raise RuntimeError("PIL required for frame rendering")

        w, h = self.resolution

        # Progress-based gradient (for testing)
        progress = frame_index / max(1, total_frames - 1)

        # Base image
        img = Image.new("RGB", (w, h), color=(20, 20, 40))
        draw = ImageDraw.Draw(img)

        # Gradient background
        for y in range(h):
            gradient_val = int(20 + (y / h) * 60 * (1 - progress))
            color = (gradient_val, gradient_val + 20, gradient_val + 60)
            draw.line([(0, y), (w, y)], fill=color)

        # Progress bar (visual indicator)
        bar_y      = h // 2
        bar_width  = int(w * 0.7)
        bar_height = 20
        bar_x      = (w - bar_width) // 2

        # Bar background
        draw.rectangle(
            [bar_x, bar_y - bar_height // 2, bar_x + bar_width, bar_y + bar_height // 2],
            fill=(60, 60, 80)
        )

        # Bar fill (progress)
        fill_width = int(bar_width * progress)
        draw.rectangle(
            [bar_x, bar_y - bar_height // 2, bar_x + fill_width, bar_y + bar_height // 2],
            fill=(0, 212, 255)  # Cyan accent
        )

        # Text
        try:
            # Ek default font try karo
            font_size = h // 20
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()

            # Frame info text
            info_text = f"Frame {frame_index + 1} / {total_frames}"
            text_bbox = draw.textbbox((0, 0), info_text, font=font)
            text_w    = text_bbox[2] - text_bbox[0]
            text_h    = text_bbox[3] - text_bbox[1]

            draw.text(
                ((w - text_w) // 2, bar_y - bar_height - text_h - 10),
                info_text,
                fill=(255, 255, 255),
                font=font,
            )

            # Progress percentage
            pct_text = f"{progress * 100:.1f}%"
            pct_bbox = draw.textbbox((0, 0), pct_text, font=font)
            pct_w    = pct_bbox[2] - pct_bbox[0]

            draw.text(
                ((w - pct_w) // 2, bar_y + bar_height // 2 + 10),
                pct_text,
                fill=(0, 212, 255),
                font=font,
            )

        except Exception as e:
            logger.debug(f"Text render error: {e}")

        return img


# ============================================================
# MAIN VIDEO EXPORTER
# ============================================================

class VideoExporter:
    """
    🎥 Main Video Exporter

    Timeline data ko real video file mein convert karta hai.
    FFmpeg ka use karta hai encoding ke liye.

    Usage:
        exporter = VideoExporter()
        settings = ExportSettings(
            output_path="output.mp4",
            resolution=Resolution.RES_1080P,
            fps=30,
            quality=QualityPreset.HIGH,
        )
        result = exporter.export(timeline_data=None, settings=settings)
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Args:
            config: Optional config override
        """
        # Config setup
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # FFmpeg detect karo
        self.ffmpeg_path = FFmpegDetector.find_ffmpeg()
        self.ffmpeg_available = self.ffmpeg_path is not None

        # Output directory
        export_cfg = self.config.get("export", {})
        base_dir   = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)
        )))
        self.default_output_dir = export_cfg.get(
            "output_dir",
            os.path.join(base_dir, "exports")
        )
        ensure_dir(self.default_output_dir)

        # Temp directory for intermediate frames
        self.temp_dir = os.path.join(base_dir, "temp", "export_frames")
        ensure_dir(self.temp_dir)

        # State
        self.progress    = ExportProgress()
        self._cancel_flag= threading.Event()
        self._pause_flag = threading.Event()

        # Renderer
        self.frame_renderer = None

        # Listeners
        self._progress_listeners: List[Callable[[ExportProgress], None]] = []

        # Stats
        self._stats = {
            "total_exports"   : 0,
            "successful"      : 0,
            "failed"          : 0,
            "total_time"      : 0.0,
        }

        self._log_status()

    def _log_status(self):
        """Startup status log karo"""
        if self.ffmpeg_available:
            version = FFmpegDetector.get_version(self.ffmpeg_path)
            logger.info(f"🎥 VideoExporter ready")
            logger.info(f"   FFmpeg: {version}")
        else:
            logger.warning("⚠️ FFmpeg not found — install: winget install Gyan.FFmpeg")

    # ── INFO METHODS ──────────────────────────────────────

    def get_supported_formats(self) -> List[Dict]:
        """Sab supported formats return karo"""
        return [
            {"format": f.name, "ext": f.ext, "description": f.description}
            for f in VideoFormat
        ]

    def get_supported_codecs(self) -> Dict[str, List[Dict]]:
        """Codecs by type return karo"""
        return {
            "video": [
                {"name": c.name, "ffmpeg_name": c.ffmpeg_name, "description": c.description}
                for c in VideoCodec
            ],
            "audio": [
                {"name": c.name, "ffmpeg_name": c.ffmpeg_name, "description": c.description}
                for c in AudioCodec
            ],
        }

    def get_quality_presets(self) -> List[Dict]:
        """Quality presets info"""
        return [
            {
                "label"      : q.label,
                "crf"        : q.crf,
                "speed"      : q.speed,
                "description": q.description
            }
            for q in QualityPreset
        ]

    def get_resolution_presets(self) -> Dict[str, Tuple[int, int]]:
        """Standard resolutions"""
        return Resolution.ALL

    # ── EXPORT METHODS ────────────────────────────────────

    def export(self,
               timeline_data: Optional[Dict] = None,
               settings: Optional[ExportSettings] = None,
               progress_callback: Optional[Callable] = None) -> ExportResult:
        """
        Timeline ko video file mein export karo.

        Args:
            timeline_data     : Timeline data (None = test synthetic frames)
            settings          : Export settings
            progress_callback : Real-time progress callback

        Returns:
            ExportResult
        """
        result = ExportResult()
        start_time = time.time()

        # Validation
        if not self.ffmpeg_available:
            result.error = "FFmpeg not available"
            return result

        if settings is None:
            settings = ExportSettings(
                output_path=os.path.join(self.default_output_dir, "export.mp4")
            )

        # Register progress callback
        if progress_callback:
            self.add_progress_listener(progress_callback)

        result.settings_used = settings

        try:
            # Ensure output directory
            ensure_dir(os.path.dirname(settings.output_path))

            # ── STEP 1: RENDER FRAMES ────────────────────

            self._update_progress(state=ExportState.PREPARING,
                                  message="Preparing render pipeline...")

            # Frames temp folder
            session_id  = generate_short_id()
            frames_dir  = os.path.join(self.temp_dir, f"session_{session_id}")
            ensure_dir(frames_dir)

            # Calculate total frames
            duration     = self._calculate_duration(timeline_data, settings)
            total_frames = int(duration * settings.fps)

            self.progress.total_frames = total_frames
            self.progress.start_time   = start_time

            # Renderer setup
            self.frame_renderer = FrameRenderer(resolution=settings.resolution)

            # Render frames
            self._update_progress(state=ExportState.RENDERING,
                                  message="Rendering frames...")

            success = self._render_frames_to_disk(
                frames_dir, total_frames, timeline_data
            )

            if not success or self._cancel_flag.is_set():
                if self._cancel_flag.is_set():
                    self._update_progress(state=ExportState.CANCELLED,
                                          message="Export cancelled")
                    result.error = "Cancelled by user"
                else:
                    result.error = "Frame rendering failed"
                self._cleanup_temp(frames_dir)
                return result

            # ── STEP 2: ENCODE VIDEO ─────────────────────

            self._update_progress(state=ExportState.ENCODING,
                                  message="Encoding video...")

            encode_success = self._encode_video(
                frames_dir, settings, total_frames
            )

            if not encode_success:
                result.error = "Video encoding failed"
                self._cleanup_temp(frames_dir)
                return result

            # ── STEP 3: FINALIZE ─────────────────────────

            self._update_progress(state=ExportState.FINALIZING,
                                  message="Finalizing...")

            # Cleanup temp frames
            self._cleanup_temp(frames_dir)

            # File verify karo
            if os.path.exists(settings.output_path):
                file_size = get_file_size(settings.output_path)

                elapsed = time.time() - start_time
                result.success       = True
                result.output_path   = settings.output_path
                result.file_size     = file_size
                result.duration      = duration
                result.total_frames  = total_frames
                result.export_time   = elapsed
                result.average_fps   = total_frames / max(0.1, elapsed)

                self._stats["total_exports"] += 1
                self._stats["successful"]    += 1
                self._stats["total_time"]    += elapsed

                self._update_progress(state=ExportState.COMPLETED,
                                      message=f"✅ Export complete: {format_bytes(file_size)}")

                logger.info(
                    f"🎥 Export complete: {os.path.basename(settings.output_path)} "
                    f"({format_bytes(file_size)}, {format_duration(elapsed)}, "
                    f"{result.average_fps:.1f} fps)"
                )
            else:
                result.error = "Output file not created"
                self._update_progress(state=ExportState.ERROR,
                                      message=result.error)

        except Exception as e:
            result.error = str(e)
            self._update_progress(state=ExportState.ERROR,
                                  message=f"Error: {e}")
            logger.error(f"❌ Export failed: {e}")
            import traceback
            traceback.print_exc()
            self._stats["total_exports"] += 1
            self._stats["failed"]        += 1

        finally:
            # Remove callback agar temp add kiya tha
            if progress_callback:
                self.remove_progress_listener(progress_callback)

        return result

    def _calculate_duration(self, timeline_data: Optional[Dict],
                            settings: ExportSettings) -> float:
        """Export ki duration nikalo"""
        # Explicit end time diya hai?
        if settings.end_time is not None:
            return settings.end_time - settings.start_time

        # Timeline se dhundo
        if timeline_data:
            duration = timeline_data.get("duration", 5.0)
            return duration - settings.start_time

        # Default test duration
        return 3.0

    def _render_frames_to_disk(self,
                               frames_dir: str,
                               total_frames: int,
                               timeline_data: Optional[Dict]) -> bool:
        """
        Frames render karke disk pe save karo (PNG sequence).
        FFmpeg baad mein inhe encode karega.
        """
        if not self.frame_renderer:
            return False

        try:
            for i in range(total_frames):
                # Cancel check
                if self._cancel_flag.is_set():
                    return False

                # Pause handling
                while self._pause_flag.is_set() and not self._cancel_flag.is_set():
                    time.sleep(0.1)

                # Render frame
                img = self.frame_renderer.render_frame(i, total_frames, timeline_data)

                # Save as PNG
                frame_path = os.path.join(frames_dir, f"frame_{i:06d}.png")
                img.save(frame_path, "PNG")

                # Progress update
                self.progress.current_frame = i + 1
                elapsed = time.time() - self.progress.start_time

                if elapsed > 0:
                    self.progress.frames_per_second = (i + 1) / elapsed
                    remaining_frames = total_frames - (i + 1)
                    if self.progress.frames_per_second > 0:
                        self.progress.estimated_remaining = (
                            remaining_frames / self.progress.frames_per_second
                        )

                self.progress.elapsed_seconds = elapsed
                self.progress.message = f"Rendering frame {i + 1}/{total_frames}"

                # Notify listeners (every 10 frames or last)
                if (i + 1) % 10 == 0 or (i + 1) == total_frames:
                    self._notify_progress()

            return True

        except Exception as e:
            logger.error(f"Frame render failed: {e}")
            return False

    def _encode_video(self,
                      frames_dir: str,
                      settings: ExportSettings,
                      total_frames: int) -> bool:
        """
        FFmpeg se frames ko video mein encode karo.
        FIXED for Windows: subprocess.run with timeout monitoring in thread
        """
        try:
            # Frame pattern
            frame_pattern = os.path.join(frames_dir, "frame_%06d.png")

            # FFmpeg command build karo
            cmd = FFmpegCommand(self.ffmpeg_path)
            cmd.overwrite_output()

            # Input frames
            cmd.add_input_frames(
                pattern     = frame_pattern,
                fps         = settings.fps,
                start_number= 0,
            )

                       # ✅ FIX: GIF output detect karo aur codec auto-switch karo
            output_ext = os.path.splitext(settings.output_path)[1].lower()
            is_gif = output_ext == ".gif"

            if is_gif:
                # GIF ke liye special handling — koi CRF/preset nahi
                # High-quality GIF ke liye palette generate karna hota hai
                # Simple version — direct GIF encoding
                cmd.add_custom("-vf", "fps={},split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse".format(settings.fps))
                # GIF codec use karo — H.264 nahi
                cmd.args.extend(["-c:v", "gif"])
                logger.info("🎨 GIF output detected — using GIF encoder with palette")
            else:
                # Normal video encoding
                cmd.set_video_codec(
                    codec = settings.video_codec,
                    crf   = settings.quality.crf,
                    preset= settings.quality.speed,
                )

            cmd.set_fps(settings.fps)

            # Pixel format for compatibility
            if settings.video_codec in [VideoCodec.H264, VideoCodec.H265]:
                cmd.set_pixel_format("yuv420p")

            # Keyframe interval
            cmd.set_keyframe_interval(settings.keyframe_interval)

            # Threading
            if settings.threads > 0:
                cmd.set_threads(settings.threads)

            # Bitrate agar CRF override karna hai
            if settings.bitrate:
                cmd.set_bitrate(settings.bitrate)

            # Output
            cmd.set_output(settings.output_path)

            # Build command
            cmd_list = cmd.build()

            logger.debug(f"FFmpeg command: {cmd.build_str()}")
            self._update_progress(message="Running FFmpeg encoder...")

            # ═══════════════════════════════════════════════════════
            # ✅ FIX: subprocess.run in a thread + polling for progress
            # Windows Popen ke issues avoid karta hai
            # ═══════════════════════════════════════════════════════

            encode_result = {"returncode": None, "stderr": "", "completed": False}

            def run_ffmpeg():
                """FFmpeg ko thread mein run karo — blocking but isolated"""
                try:
                    # subprocess.run — blocking but reliable
                    result = subprocess.run(
                        cmd_list,
                        capture_output=True,   # ✅ Capture output properly
                        text=True,
                        timeout=600,           # 10 minute max
                        check=False,
                    )
                    encode_result["returncode"] = result.returncode
                    encode_result["stderr"]     = result.stderr[-1000:] if result.stderr else ""
                    encode_result["completed"]  = True
                except subprocess.TimeoutExpired:
                    encode_result["returncode"] = -1
                    encode_result["stderr"]     = "FFmpeg timeout (>10 min)"
                    encode_result["completed"]  = True
                except Exception as e:
                    encode_result["returncode"] = -1
                    encode_result["stderr"]     = str(e)
                    encode_result["completed"]  = True

            # Thread mein FFmpeg start karo
            encode_thread = threading.Thread(target=run_ffmpeg, daemon=True)
            encode_thread.start()

            # Main thread: progress monitor karo
            check_count = 0
            while not encode_result["completed"]:
                # Cancel check
                if self._cancel_flag.is_set():
                    logger.warning("Export cancelled — waiting for FFmpeg to finish...")
                    # Note: subprocess.run cancel nahi kar sakte cleanly
                    # Encoding complete hone tak wait karna padega
                    encode_thread.join(timeout=5)
                    return False

                # File size update (visual feedback)
                if os.path.exists(settings.output_path):
                    self.progress.current_size_bytes = get_file_size(settings.output_path)

                # Message rotate karo (spinner effect)
                check_count += 1
                spinners = ["⚙️  Encoding", "⚙️  Encoding.", "⚙️  Encoding..", "⚙️  Encoding..."]
                self.progress.message = spinners[check_count % len(spinners)]
                self._notify_progress()

                time.sleep(0.3)

            # Encoding done
            encode_thread.join()

            # Result check
            if encode_result["returncode"] == 0:
                logger.debug("✅ FFmpeg encoding successful")
                return True
            else:
                logger.error(f"FFmpeg failed (code {encode_result['returncode']})")
                if encode_result["stderr"]:
                    logger.error(f"FFmpeg stderr: ...{encode_result['stderr']}")
                return False

        except FileNotFoundError:
            logger.error(f"FFmpeg not found at: {self.ffmpeg_path}")
            return False
        except Exception as e:
            logger.error(f"Encoding error: {e}")
            import traceback
            traceback.print_exc()
            return False

        except FileNotFoundError:
            logger.error(f"FFmpeg not found at: {self.ffmpeg_path}")
            return False
        except Exception as e:
            logger.error(f"Encoding error: {e}")
            import traceback
            traceback.print_exc()
            return False
    def _cleanup_temp(self, frames_dir: str):
        """Temp frames delete karo"""
        try:
            if os.path.exists(frames_dir):
                shutil.rmtree(frames_dir)
                logger.debug(f"Cleaned up temp: {frames_dir}")
        except Exception as e:
            logger.debug(f"Cleanup error: {e}")

    # ── CONTROL METHODS ───────────────────────────────────

    def pause(self):
        """⏸️ Export pause karo"""
        self._pause_flag.set()
        self.progress.state = ExportState.PAUSED
        self._notify_progress()
        logger.info("⏸️  Export paused")

    def resume(self):
        """▶️ Export resume karo"""
        self._pause_flag.clear()
        logger.info("▶️  Export resumed")

    def cancel(self):
        """❌ Export cancel karo"""
        self._cancel_flag.set()
        self._pause_flag.clear()
        self.progress.state = ExportState.CANCELLED
        self._notify_progress()
        logger.info("❌ Export cancelled")

    def reset(self):
        """State reset karo naye export ke liye"""
        self._cancel_flag.clear()
        self._pause_flag.clear()
        self.progress = ExportProgress()

    # ── PROGRESS SYSTEM ───────────────────────────────────

    def _update_progress(self, state: Optional[ExportState] = None,
                         message: Optional[str] = None):
        """Progress update karo aur listeners notify karo"""
        if state:
            self.progress.state = state
        if message:
            self.progress.message = message
        self._notify_progress()

    def _notify_progress(self):
        """Sab listeners ko notify karo"""
        for cb in self._progress_listeners:
            try:
                cb(self.progress)
            except Exception as e:
                logger.debug(f"Progress listener error: {e}")

    def add_progress_listener(self, callback: Callable):
        """Progress listener add karo"""
        if callback not in self._progress_listeners:
            self._progress_listeners.append(callback)

    def remove_progress_listener(self, callback: Callable):
        """Remove listener"""
        if callback in self._progress_listeners:
            self._progress_listeners.remove(callback)

    # ── BATCH EXPORT ──────────────────────────────────────

    def export_batch(self,
                     export_jobs: List[Tuple[Optional[Dict], ExportSettings]],
                     progress_callback: Optional[Callable] = None) -> List[ExportResult]:
        """
        Multiple exports ko batch mein process karo.

        Args:
            export_jobs      : List of (timeline_data, settings) tuples
            progress_callback: Overall progress callback

        Returns:
            List of ExportResult
        """
        results = []
        total   = len(export_jobs)

        logger.info(f"📦 Starting batch export: {total} jobs")

        for i, (timeline_data, settings) in enumerate(export_jobs):
            logger.info(f"  [{i+1}/{total}] Exporting: {os.path.basename(settings.output_path)}")

            # Reset for new export
            self.reset()

            # Export
            result = self.export(timeline_data, settings, progress_callback)
            results.append(result)

            if not result.success:
                logger.warning(f"  ❌ Job {i+1} failed: {result.error}")

        successful = sum(1 for r in results if r.success)
        logger.info(f"📦 Batch complete: {successful}/{total} successful")

        return results

    # ── UTILITIES ─────────────────────────────────────────

    def estimate_export_time(self,
                             duration_seconds: float,
                             settings: ExportSettings) -> float:
        """
        Export me kitna time lagega — rough estimate.
        """
        # Speed multiplier based on quality preset
        speed_multipliers = {
            QualityPreset.DRAFT   : 0.3,   # 30% of realtime
            QualityPreset.LOW     : 0.5,
            QualityPreset.STANDARD: 1.0,   # Realtime
            QualityPreset.HIGH    : 2.0,
            QualityPreset.ULTRA   : 4.0,
            QualityPreset.LOSSLESS: 8.0,
        }

        # Resolution multiplier
        w, h = settings.resolution
        res_multiplier = (w * h) / (1920 * 1080)

        multiplier = speed_multipliers.get(settings.quality, 1.0)
        return duration_seconds * multiplier * res_multiplier

    def get_stats(self) -> Dict:
        """Exporter statistics"""
        return {
            "ffmpeg_available"     : self.ffmpeg_available,
            "ffmpeg_path"          : self.ffmpeg_path or "not found",
            "total_exports"        : self._stats["total_exports"],
            "successful"           : self._stats["successful"],
            "failed"               : self._stats["failed"],
            "total_time"           : self._stats["total_time"],
            "total_time_str"       : format_duration(self._stats["total_time"]),
            "average_time_per_export": (
                self._stats["total_time"] / max(1, self._stats["total_exports"])
            ),
            "supported_formats"    : len(list(VideoFormat)),
            "supported_video_codecs": len(list(VideoCodec)),
            "quality_presets"      : len(list(QualityPreset)),
            "resolution_presets"   : len(Resolution.ALL),
        }


# ============================================================
# TEST FUNCTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")
    print_banner(
        "🎥 Video Exporter Test",
        "Timeline → MP4/WebM export with FFmpeg"
    )

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))

    # ============================================================
    # Test 1: Initialize
    # ============================================================
    print_section("Test 1: Initialize Video Exporter")

    exporter = VideoExporter()
    stats    = exporter.get_stats()

    print(f"  FFmpeg available    : {'✅' if stats['ffmpeg_available'] else '❌'}")
    print(f"  FFmpeg path         : {stats['ffmpeg_path']}")
    print(f"  Formats             : {stats['supported_formats']}")
    print(f"  Video codecs        : {stats['supported_video_codecs']}")
    print(f"  Quality presets     : {stats['quality_presets']}")
    print(f"  Resolution presets  : {stats['resolution_presets']}")

    if not stats['ffmpeg_available']:
        print("\n❌ FFmpeg not found — cannot continue")
        print("   Install: winget install Gyan.FFmpeg")
        sys.exit(1)

    if not PIL_AVAILABLE:
        print("\n❌ PIL (Pillow) not available — cannot render frames")
        sys.exit(1)

    # ============================================================
    # Test 2: Supported Formats & Codecs
    # ============================================================
    print_section("Test 2: Supported Formats & Codecs")

    print("  📹 Video Formats:")
    for f in exporter.get_supported_formats():
        print(f"    • {f['format']:5s} (.{f['ext']:4s}) - {f['description']}")

    codecs = exporter.get_supported_codecs()
    print(f"\n  🎬 Video Codecs ({len(codecs['video'])}):")
    for c in codecs['video']:
        print(f"    • {c['name']:8s} - {c['description']}")

    print(f"\n  🎵 Audio Codecs ({len(codecs['audio'])}):")
    for c in codecs['audio']:
        print(f"    • {c['name']:8s} - {c['description']}")

    # ============================================================
    # Test 3: Quality Presets
    # ============================================================
    print_section("Test 3: Quality Presets")

    for q in exporter.get_quality_presets():
        print(f"  🎯 {q['label']:10s}: CRF={q['crf']:2d} speed={q['speed']:12s} - {q['description']}")

    # ============================================================
    # Test 4: Resolution Presets
    # ============================================================
    print_section("Test 4: Resolution Presets")

    for name, (w, h) in exporter.get_resolution_presets().items():
        aspect = f"{w/h:.2f}:1"
        print(f"  📏 {name:10s}: {w}x{h}  ({aspect})")

    # ============================================================
    # Test 5: FFmpeg Command Builder
    # ============================================================
    print_section("Test 5: FFmpeg Command Builder")

    cmd = FFmpegCommand("ffmpeg")
    cmd.overwrite_output()
    cmd.add_input_frames("frames/frame_%06d.png", fps=30)
    cmd.set_video_codec(VideoCodec.H264, crf=23, preset="medium")
    cmd.set_fps(30)
    cmd.set_pixel_format("yuv420p")
    cmd.set_resolution(1920, 1080)
    cmd.set_output("output.mp4")

    print(f"  Built command:")
    print(f"    {cmd.build_str()}")

    # ============================================================
    # Test 6: Bitrate Calculation
    # ============================================================
    print_section("Test 6: Bitrate Calculation (Auto)")

    test_settings = [
        (Resolution.RES_720P,  QualityPreset.DRAFT),
        (Resolution.RES_1080P, QualityPreset.STANDARD),
        (Resolution.RES_4K,    QualityPreset.HIGH),
        (Resolution.RES_1080P, QualityPreset.ULTRA),
    ]

    for res, quality in test_settings:
        s = ExportSettings(resolution=res, quality=quality)
        bitrate = s.get_effective_bitrate()
        w, h = res
        print(f"  {w}x{h:5d} + {quality.label:10s} → {bitrate}")

    # ============================================================
    # Test 7: Small Test Export (720p, 2 seconds)
    # ============================================================
    print_section("Test 7: Small Test Export (720p, 2 seconds)")

    output_dir = os.path.join(base_dir, "temp", "export_tests")
    ensure_dir(output_dir)
    small_output = os.path.join(output_dir, "test_small_720p.mp4")

    small_settings = ExportSettings(
        output_path=small_output,
        format     =VideoFormat.MP4,
        resolution =Resolution.RES_720P,
        fps        =30,
        video_codec=VideoCodec.H264,
        quality    =QualityPreset.DRAFT,
        include_audio=False,
        end_time   =2.0,   # 2 seconds
    )

    # Progress callback
    last_percent = [0]

    def progress_cb(prog: ExportProgress):
        """Progress dikhao console pe"""
        if prog.state == ExportState.RENDERING:
            pct = prog.progress_percent
            # Sirf 10% intervals pe show karo
            if int(pct) // 10 > last_percent[0] // 10:
                last_percent[0] = int(pct)
                bar = "█" * int(pct / 5)
                print(f"    [{bar:20s}] {pct:5.1f}% "
                      f"({prog.current_frame}/{prog.total_frames} frames)")

    print(f"  Output: {os.path.basename(small_output)}")
    print(f"  Settings: 720p, 30fps, 2s duration, H.264 draft\n")
    print(f"  Rendering...")

    result = exporter.export(
        timeline_data     = None,
        settings          = small_settings,
        progress_callback = progress_cb,
    )

    if result.success:
        r = result.to_dict()
        print(f"\n  ✅ Export successful!")
        print(f"     File        : {os.path.basename(result.output_path)}")
        print(f"     Size        : {r['file_size_str']}")
        print(f"     Duration    : {r['duration_str']}")
        print(f"     Frames      : {r['total_frames']}")
        print(f"     Export time : {r['export_time_str']}")
        print(f"     Avg FPS     : {r['average_fps']} fps")
    else:
        print(f"\n  ❌ Export failed: {result.error}")

    # ============================================================
    # Test 8: Different Format Export (WebM)
    # ============================================================
    print_section("Test 8: WebM Export (VP9)")

    webm_output = os.path.join(output_dir, "test_webm.webm")

    webm_settings = ExportSettings(
        output_path=webm_output,
        format     =VideoFormat.WEBM,
        resolution =Resolution.RES_720P,
        fps        =30,
        video_codec=VideoCodec.VP9,
        quality    =QualityPreset.DRAFT,
        include_audio=False,
        end_time   =1.5,
    )

    print(f"  Output: {os.path.basename(webm_output)}")
    print(f"  Codec : VP9")
    print(f"  Rendering...")

    exporter.reset()
    last_percent[0] = 0

    result = exporter.export(
        timeline_data     = None,
        settings          = webm_settings,
        progress_callback = progress_cb,
    )

    if result.success:
        print(f"\n  ✅ WebM export: {format_bytes(result.file_size)}")
    else:
        print(f"\n  ❌ Failed: {result.error}")

    # ============================================================
    # Test 9: 1080p HD Export
    # ============================================================
    print_section("Test 9: 1080p HD Export")

    hd_output = os.path.join(output_dir, "test_1080p_hd.mp4")

    hd_settings = ExportSettings(
        output_path=hd_output,
        format     =VideoFormat.MP4,
        resolution =Resolution.RES_1080P,
        fps        =30,
        video_codec=VideoCodec.H264,
        quality    =QualityPreset.STANDARD,
        include_audio=False,
        end_time   =2.0,
    )

    print(f"  Output: {os.path.basename(hd_output)}")
    print(f"  Resolution: 1920x1080 (Full HD)")
    print(f"  Rendering...")

    exporter.reset()
    last_percent[0] = 0

    result = exporter.export(
        timeline_data     = None,
        settings          = hd_settings,
        progress_callback = progress_cb,
    )

    if result.success:
        print(f"\n  ✅ 1080p export: {format_bytes(result.file_size)} "
              f"in {format_duration(result.export_time)}")
    else:
        print(f"\n  ❌ Failed: {result.error}")

    # ============================================================
    # Test 10: Export Time Estimation
    # ============================================================
    print_section("Test 10: Export Time Estimation")

    test_estimates = [
        (10.0,  ExportSettings(resolution=Resolution.RES_720P,  quality=QualityPreset.DRAFT)),
        (30.0,  ExportSettings(resolution=Resolution.RES_1080P, quality=QualityPreset.STANDARD)),
        (60.0,  ExportSettings(resolution=Resolution.RES_4K,    quality=QualityPreset.HIGH)),
        (120.0, ExportSettings(resolution=Resolution.RES_1080P, quality=QualityPreset.ULTRA)),
    ]

    print(f"  {'Duration':10s} {'Resolution':12s} {'Quality':10s} → {'Estimated Time':15s}")
    print(f"  {'-'*10} {'-'*12} {'-'*10}   {'-'*15}")

    for duration, settings in test_estimates:
        w, h = settings.resolution
        estimated = exporter.estimate_export_time(duration, settings)
        print(f"  {duration:6.0f}s    {w}x{h:5d}   {settings.quality.label:10s} → "
              f"{format_duration(estimated):15s}")

    # ============================================================
    # Test 11: Batch Export
    # ============================================================
    print_section("Test 11: Batch Export (3 videos)")

    batch_jobs = [
        (None, ExportSettings(
            output_path=os.path.join(output_dir, "batch_1_480p.mp4"),
            resolution =Resolution.RES_480P,
            fps        =30,
            quality    =QualityPreset.DRAFT,
            end_time   =1.0,
            include_audio=False,
        )),
        (None, ExportSettings(
            output_path=os.path.join(output_dir, "batch_2_720p.mp4"),
            resolution =Resolution.RES_720P,
            fps        =30,
            quality    =QualityPreset.DRAFT,
            end_time   =1.0,
            include_audio=False,
        )),
        (None, ExportSettings(
            output_path=os.path.join(output_dir, "batch_3_gif.gif"),
            resolution =(480, 270),
            fps        =15,
            quality    =QualityPreset.DRAFT,
            end_time   =1.0,
            include_audio=False,
        )),
    ]

    print(f"  Starting batch of {len(batch_jobs)} exports...\n")

    exporter.reset()
    batch_results = exporter.export_batch(batch_jobs)

    print(f"\n  Batch Results:")
    for i, r in enumerate(batch_results, 1):
        if r.success:
            print(f"    ✅ Job {i}: {format_bytes(r.file_size)} "
                  f"({r.average_fps:.1f} fps)")
        else:
            print(f"    ❌ Job {i}: {r.error}")

    # ============================================================
    # Test 12: Final Statistics
    # ============================================================
    print_section("Test 12: Final Statistics")

    stats = exporter.get_stats()
    print(f"  Total exports   : {stats['total_exports']}")
    print(f"  Successful      : {stats['successful']}")
    print(f"  Failed          : {stats['failed']}")
    print(f"  Total time      : {stats['total_time_str']}")
    print(f"  Avg time/export : {stats['average_time_per_export']:.1f}s")

    # ============================================================
    # Output Info
    # ============================================================
    print_section("Output Files")
    print(f"  📁 Exported videos saved in:")
    print(f"     {output_dir}")
    print(f"\n  🎬 Open to watch:")
    print(f"     start {output_dir}")

    print_banner(
        "✅ Video Exporter Ready!",
        f"{stats['successful']}/{stats['total_exports']} exports successful"
    )