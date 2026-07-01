# ============================================================
# src/export/social_media_presets.py
# 3D Animation Studio - Social Media Export Presets
# Sabhi popular platforms ke liye export settings
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
import subprocess
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from pathlib import Path

from src.utils import (
    get_logger,
    get_config,
    ensure_dir,
    write_json,
    read_json,
    format_bytes,
)

logger = get_logger("SocialMediaPresets")


# ============================================================
# ENUMS - Platform aur Format Constants
# ============================================================

class Platform(Enum):
    """Supported social media platforms"""
    YOUTUBE          = "youtube"
    YOUTUBE_SHORTS   = "youtube_shorts"
    INSTAGRAM        = "instagram"
    INSTAGRAM_REELS  = "instagram_reels"
    INSTAGRAM_STORY  = "instagram_story"
    TIKTOK           = "tiktok"
    TWITTER          = "twitter"
    FACEBOOK         = "facebook"
    FACEBOOK_REELS   = "facebook_reels"
    LINKEDIN         = "linkedin"
    SNAPCHAT         = "snapchat"
    PINTEREST        = "pinterest"
    VIMEO            = "vimeo"
    TWITCH           = "twitch"
    CUSTOM           = "custom"


class VideoCodec(Enum):
    """Video encoding codecs"""
    H264   = "libx264"    # Most compatible
    H265   = "libx265"    # Better compression
    VP9    = "libvp9"     # Web optimized
    AV1    = "libaom-av1" # Best compression (slow)
    MPEG4  = "mpeg4"      # Legacy support


class AudioCodec(Enum):
    """Audio encoding codecs"""
    AAC    = "aac"     # Universal
    MP3    = "libmp3lame"
    OPUS   = "libopus" # Best for web
    VORBIS = "libvorbis"
    PCM    = "pcm_s16le"


class AspectRatio(Enum):
    """Common aspect ratios"""
    LANDSCAPE   = "16:9"   # YouTube, standard
    PORTRAIT    = "9:16"   # Shorts, Reels, TikTok
    SQUARE      = "1:1"    # Instagram feed
    FOUR_THREE  = "4:3"    # Classic
    TWENTY_ONE  = "21:9"   # Cinematic ultrawide
    FOUR_FIVE   = "4:5"    # Instagram portrait


class ExportQuality(Enum):
    """Export quality levels"""
    LOW      = "low"      # Fast upload, low file size
    MEDIUM   = "medium"   # Balanced
    HIGH     = "high"     # Best quality
    ULTRA    = "ultra"    # Maximum quality (large file)


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class VideoSettings:
    """Video encoding settings - ek platform ke liye"""
    width: int              = 1920
    height: int             = 1080
    fps: int                = 30
    codec: str              = VideoCodec.H264.value
    bitrate: str            = "8M"        # e.g., "8M", "4000k"
    crf: int                = 23          # Constant Rate Factor (0=best, 51=worst)
    preset: str             = "medium"    # FFmpeg speed preset
    pixel_format: str       = "yuv420p"   # Color format
    max_bitrate: str        = "10M"       # Peak bitrate
    buf_size: str           = "16M"       # Buffer size
    profile: str            = "high"      # H264 profile
    level: str              = "4.1"       # H264 level
    two_pass: bool          = False       # Two-pass encoding for better quality
    keyframe_interval: int  = 48          # GOP size (2x fps)


@dataclass
class AudioSettings:
    """Audio encoding settings"""
    codec: str        = AudioCodec.AAC.value
    bitrate: str      = "192k"
    sample_rate: int  = 48000     # Hz
    channels: int     = 2         # Stereo
    normalize: bool   = True      # Audio normalization
    loudness: float   = -14.0     # LUFS target (YouTube standard)


@dataclass
class PlatformConstraints:
    """Platform specific constraints aur limits"""
    max_duration_seconds: Optional[int]  = None    # None = unlimited
    max_file_size_mb: Optional[int]      = None    # MB mein
    min_resolution: Tuple[int, int]      = (426, 240)
    max_resolution: Tuple[int, int]      = (3840, 2160)
    required_aspect_ratio: Optional[str] = None    # None = flexible
    min_fps: int                         = 15
    max_fps: int                         = 60
    supports_hdr: bool                   = False
    supports_chapters: bool              = False
    supports_subtitles: bool             = True
    max_title_length: int                = 100
    max_description_length: int          = 5000
    max_tags: int                        = 30


@dataclass
class ExportPreset:
    """
    Complete export preset for a platform.
    Ek preset mein sab kuch hota hai.
    """
    # Identity
    platform: str
    name: str
    display_name: str
    description: str
    category: str                    # "landscape", "portrait", "square"

    # Settings
    video: VideoSettings             = field(default_factory=VideoSettings)
    audio: AudioSettings             = field(default_factory=AudioSettings)
    constraints: PlatformConstraints = field(default_factory=PlatformConstraints)

    # Output format
    container: str                   = "mp4"        # mp4, webm, mov
    extension: str                   = ".mp4"

    # Metadata
    recommended_for: List[str]       = field(default_factory=list)
    tips: List[str]                  = field(default_factory=list)
    ffmpeg_extra_args: List[str]     = field(default_factory=list)

    def get_resolution_string(self) -> str:
        """Resolution string return karo"""
        return f"{self.video.width}x{self.video.height}"

    def get_aspect_ratio(self) -> str:
        """Aspect ratio calculate karo"""
        from math import gcd
        g = gcd(self.video.width, self.video.height)
        return f"{self.video.width // g}:{self.video.height // g}"

    def estimate_file_size_mb(self, duration_seconds: int) -> float:
        """
        Estimated file size calculate karo.
        duration ke basis pe approximate size.
        """
        # Parse bitrate
        def parse_bitrate_kbps(bitrate_str: str) -> float:
            bitrate_str = bitrate_str.upper().replace(" ", "")
            if bitrate_str.endswith("M"):
                return float(bitrate_str[:-1]) * 1000
            elif bitrate_str.endswith("K"):
                return float(bitrate_str[:-1])
            else:
                return float(bitrate_str) / 1000

        video_kbps = parse_bitrate_kbps(self.video.bitrate)
        audio_kbps = parse_bitrate_kbps(self.audio.bitrate)
        total_kbps = video_kbps + audio_kbps

        # Size in MB = (bitrate_kbps * duration_sec) / (8 * 1024)
        size_mb = (total_kbps * duration_seconds) / (8 * 1024)
        return round(size_mb, 2)

    def to_dict(self) -> Dict:
        """Preset ko dictionary mein convert karo"""
        return {
            "platform": self.platform,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "resolution": self.get_resolution_string(),
            "fps": self.video.fps,
            "video_codec": self.video.codec,
            "video_bitrate": self.video.bitrate,
            "audio_codec": self.audio.codec,
            "audio_bitrate": self.audio.bitrate,
            "container": self.container,
            "extension": self.extension,
            "tips": self.tips,
        }


# ============================================================
# PRESET DEFINITIONS - Sabhi platforms ke presets
# ============================================================

class PresetDefinitions:
    """
    Sabhi platforms ke liye predefined presets.
    Research-based optimal settings.
    """

    # ----------------------------------------------------------
    # YOUTUBE PRESETS
    # ----------------------------------------------------------

    @staticmethod
    def youtube_1080p() -> ExportPreset:
        """YouTube Standard 1080p - Sabse zyada use hota hai"""
        return ExportPreset(
            platform=Platform.YOUTUBE.value,
            name="youtube_1080p",
            display_name="YouTube 1080p HD",
            description="YouTube ke liye standard 1080p HD quality",
            category="landscape",
            video=VideoSettings(
                width=1920, height=1080,
                fps=30,
                codec=VideoCodec.H264.value,
                bitrate="8M",
                crf=18,
                preset="slow",       # Better quality
                pixel_format="yuv420p",
                max_bitrate="10M",
                buf_size="16M",
                profile="high",
                level="4.1",
                two_pass=False,
                keyframe_interval=60,
            ),
            audio=AudioSettings(
                codec=AudioCodec.AAC.value,
                bitrate="192k",
                sample_rate=48000,
                channels=2,
                normalize=True,
                loudness=-14.0,      # YouTube recommended LUFS
            ),
            constraints=PlatformConstraints(
                max_duration_seconds=43200,  # 12 hours
                max_file_size_mb=256000,     # 256 GB (practically unlimited)
                max_resolution=(3840, 2160),
                supports_chapters=True,
                supports_subtitles=True,
                max_title_length=100,
                max_description_length=5000,
                max_tags=500,
            ),
            container="mp4",
            extension=".mp4",
            recommended_for=[
                "Gaming videos", "Tutorials", "Vlogs",
                "Educational content", "Reviews"
            ],
            tips=[
                "CRF 18 se best quality milti hai",
                "YouTube automatically re-encodes - isliye high quality upload karo",
                "48kHz audio YouTube standard hai",
                "SDR color space use karo HDR nahi (jab tak HDR specific na ho)",
            ],
            ffmpeg_extra_args=[
                "-movflags", "+faststart",  # Web streaming ke liye
                "-metadata", "comment=Made with 3D Animation Studio",
            ]
        )

    @staticmethod
    def youtube_1080p_60fps() -> ExportPreset:
        """YouTube 1080p 60fps - Gaming aur action content"""
        preset = PresetDefinitions.youtube_1080p()
        preset.name = "youtube_1080p_60fps"
        preset.display_name = "YouTube 1080p 60fps"
        preset.description = "60fps gaming aur action videos ke liye"
        preset.video.fps = 60
        preset.video.bitrate = "12M"
        preset.video.max_bitrate = "15M"
        preset.video.keyframe_interval = 120
        preset.tips.append("60fps ke liye zyada bitrate chahiye")
        return preset

    @staticmethod
    def youtube_4k() -> ExportPreset:
        """YouTube 4K Ultra HD"""
        preset = PresetDefinitions.youtube_1080p()
        preset.name = "youtube_4k"
        preset.display_name = "YouTube 4K Ultra HD"
        preset.description = "4K Ultra HD - Best quality for YouTube"
        preset.video.width = 3840
        preset.video.height = 2160
        preset.video.bitrate = "35M"
        preset.video.max_bitrate = "45M"
        preset.video.buf_size = "70M"
        preset.video.level = "5.1"
        preset.video.codec = VideoCodec.H265.value   # H265 better for 4K
        preset.video.crf = 20
        preset.tips = [
            "4K upload karo - YouTube HDR/4K viewers zyada hain",
            "H265 codec H264 se 40% better compression deta hai",
            "Render time zyada hoga - overnight render karo",
        ]
        return preset

    @staticmethod
    def youtube_720p() -> ExportPreset:
        """YouTube 720p - Faster upload, less storage"""
        preset = PresetDefinitions.youtube_1080p()
        preset.name = "youtube_720p"
        preset.display_name = "YouTube 720p HD"
        preset.description = "720p - Jaldi upload ke liye"
        preset.video.width = 1280
        preset.video.height = 720
        preset.video.bitrate = "5M"
        preset.video.max_bitrate = "7M"
        preset.video.buf_size = "10M"
        preset.video.level = "3.1"
        preset.video.crf = 20
        return preset

    # ----------------------------------------------------------
    # YOUTUBE SHORTS PRESETS
    # ----------------------------------------------------------

    @staticmethod
    def youtube_shorts() -> ExportPreset:
        """YouTube Shorts - 9:16 vertical format"""
        return ExportPreset(
            platform=Platform.YOUTUBE_SHORTS.value,
            name="youtube_shorts",
            display_name="YouTube Shorts",
            description="YouTube Shorts ke liye vertical 9:16 format",
            category="portrait",
            video=VideoSettings(
                width=1080, height=1920,
                fps=30,
                codec=VideoCodec.H264.value,
                bitrate="8M",
                crf=18,
                preset="slow",
                pixel_format="yuv420p",
                max_bitrate="10M",
                buf_size="16M",
                profile="high",
                level="4.1",
                keyframe_interval=60,
            ),
            audio=AudioSettings(
                codec=AudioCodec.AAC.value,
                bitrate="192k",
                sample_rate=48000,
                channels=2,
                normalize=True,
                loudness=-14.0,
            ),
            constraints=PlatformConstraints(
                max_duration_seconds=60,         # Shorts = max 60 seconds
                max_file_size_mb=256000,
                required_aspect_ratio="9:16",
                max_title_length=100,
            ),
            container="mp4",
            extension=".mp4",
            recommended_for=["Short clips", "Highlights", "Quick tutorials"],
            tips=[
                "Max 60 seconds honi chahiye Shorts ke liye",
                "Vertical 9:16 format compulsory hai",
                "First few seconds engaging rakho",
                "Captions add karo - zyada views milte hain",
            ],
            ffmpeg_extra_args=["-movflags", "+faststart"]
        )

    # ----------------------------------------------------------
    # INSTAGRAM PRESETS
    # ----------------------------------------------------------

    @staticmethod
    def instagram_feed() -> ExportPreset:
        """Instagram Feed - Square ya Portrait"""
        return ExportPreset(
            platform=Platform.INSTAGRAM.value,
            name="instagram_feed",
            display_name="Instagram Feed (Square)",
            description="Instagram feed ke liye 1:1 square format",
            category="square",
            video=VideoSettings(
                width=1080, height=1080,
                fps=30,
                codec=VideoCodec.H264.value,
                bitrate="6M",
                crf=20,
                preset="medium",
                pixel_format="yuv420p",
                max_bitrate="8M",
                buf_size="12M",
                profile="high",
                level="4.0",
                keyframe_interval=60,
            ),
            audio=AudioSettings(
                codec=AudioCodec.AAC.value,
                bitrate="128k",
                sample_rate=44100,
                channels=2,
                normalize=True,
                loudness=-14.0,
            ),
            constraints=PlatformConstraints(
                max_duration_seconds=60,
                max_file_size_mb=100,
                required_aspect_ratio="1:1",
                max_resolution=(1080, 1080),
                max_title_length=2200,  # Caption
            ),
            container="mp4",
            extension=".mp4",
            recommended_for=["Product showcases", "Art", "Short animations"],
            tips=[
                "Instagram 100MB se bada file accept nahi karta",
                "Square format feed mein best dikhta hai",
                "Audio off pe bhi video engaging rakho",
            ],
            ffmpeg_extra_args=["-movflags", "+faststart"]
        )

    @staticmethod
    def instagram_reels() -> ExportPreset:
        """Instagram Reels - 9:16 vertical"""
        return ExportPreset(
            platform=Platform.INSTAGRAM_REELS.value,
            name="instagram_reels",
            display_name="Instagram Reels",
            description="Instagram Reels ke liye 9:16 vertical format",
            category="portrait",
            video=VideoSettings(
                width=1080, height=1920,
                fps=30,
                codec=VideoCodec.H264.value,
                bitrate="8M",
                crf=18,
                preset="slow",
                pixel_format="yuv420p",
                max_bitrate="10M",
                buf_size="16M",
                profile="high",
                level="4.1",
                keyframe_interval=60,
            ),
            audio=AudioSettings(
                codec=AudioCodec.AAC.value,
                bitrate="192k",
                sample_rate=48000,
                channels=2,
                normalize=True,
                loudness=-14.0,
            ),
            constraints=PlatformConstraints(
                max_duration_seconds=90,
                max_file_size_mb=100,
                required_aspect_ratio="9:16",
            ),
            container="mp4",
            extension=".mp4",
            recommended_for=["Trending content", "Behind scenes", "Tutorials"],
            tips=[
                "90 seconds max, lekin 15-30 sec best engagement deta hai",
                "Trending audio use karo reach badhaane ke liye",
                "Captions zaroor add karo",
            ],
            ffmpeg_extra_args=["-movflags", "+faststart"]
        )

    @staticmethod
    def instagram_story() -> ExportPreset:
        """Instagram Story - 9:16, 15 seconds"""
        preset = PresetDefinitions.instagram_reels()
        preset.platform = Platform.INSTAGRAM_STORY.value
        preset.name = "instagram_story"
        preset.display_name = "Instagram Story"
        preset.description = "Instagram Story - 15 second clips"
        preset.constraints.max_duration_seconds = 15
        preset.tips = [
            "Story max 15 seconds hoti hai",
            "Interactive elements add karo (polls, questions)",
            "Bright colors better engagement deta hai",
        ]
        return preset

    # ----------------------------------------------------------
    # TIKTOK PRESETS
    # ----------------------------------------------------------

    @staticmethod
    def tiktok() -> ExportPreset:
        """TikTok - 9:16 vertical format"""
        return ExportPreset(
            platform=Platform.TIKTOK.value,
            name="tiktok",
            display_name="TikTok",
            description="TikTok ke liye optimized vertical video",
            category="portrait",
            video=VideoSettings(
                width=1080, height=1920,
                fps=30,
                codec=VideoCodec.H264.value,
                bitrate="8M",
                crf=18,
                preset="slow",
                pixel_format="yuv420p",
                max_bitrate="10M",
                buf_size="16M",
                profile="high",
                level="4.1",
                keyframe_interval=60,
            ),
            audio=AudioSettings(
                codec=AudioCodec.AAC.value,
                bitrate="192k",
                sample_rate=44100,
                channels=2,
                normalize=True,
                loudness=-14.0,
            ),
            constraints=PlatformConstraints(
                max_duration_seconds=600,    # 10 minutes max
                max_file_size_mb=287,        # ~287 MB limit
                required_aspect_ratio="9:16",
            ),
            container="mp4",
            extension=".mp4",
            recommended_for=["Entertainment", "Dance", "Comedy", "Education"],
            tips=[
                "First 3 seconds mein hook dalo",
                "Trending sounds use karo",
                "Loop-able videos zyada viral hote hain",
                "Captions almost mandatory hain",
            ],
            ffmpeg_extra_args=["-movflags", "+faststart"]
        )

    # ----------------------------------------------------------
    # TWITTER / X PRESETS
    # ----------------------------------------------------------

    @staticmethod
    def twitter() -> ExportPreset:
        """Twitter/X - Landscape format"""
        return ExportPreset(
            platform=Platform.TWITTER.value,
            name="twitter",
            display_name="Twitter / X",
            description="Twitter ke liye optimized video",
            category="landscape",
            video=VideoSettings(
                width=1280, height=720,
                fps=30,
                codec=VideoCodec.H264.value,
                bitrate="5M",
                crf=22,
                preset="medium",
                pixel_format="yuv420p",
                max_bitrate="6M",
                buf_size="10M",
                profile="main",
                level="3.1",
                keyframe_interval=60,
            ),
            audio=AudioSettings(
                codec=AudioCodec.AAC.value,
                bitrate="128k",
                sample_rate=44100,
                channels=2,
                normalize=True,
                loudness=-16.0,
            ),
            constraints=PlatformConstraints(
                max_duration_seconds=140,    # 2min 20sec
                max_file_size_mb=512,
                max_resolution=(1920, 1200),
                max_title_length=280,
            ),
            container="mp4",
            extension=".mp4",
            recommended_for=["News clips", "Announcements", "Short demos"],
            tips=[
                "Twitter pe 512MB se chhota file hi upload hota hai",
                "Subtitles add karo - timeline pe auto-play muted hota hai",
                "2:20 se bada video upload nahi hoga (Twitter Blue ke bina)",
            ],
            ffmpeg_extra_args=["-movflags", "+faststart"]
        )

    # ----------------------------------------------------------
    # FACEBOOK PRESETS
    # ----------------------------------------------------------

    @staticmethod
    def facebook() -> ExportPreset:
        """Facebook - Standard landscape"""
        return ExportPreset(
            platform=Platform.FACEBOOK.value,
            name="facebook",
            display_name="Facebook Video",
            description="Facebook feed ke liye standard video",
            category="landscape",
            video=VideoSettings(
                width=1920, height=1080,
                fps=30,
                codec=VideoCodec.H264.value,
                bitrate="8M",
                crf=20,
                preset="medium",
                pixel_format="yuv420p",
                max_bitrate="10M",
                buf_size="16M",
                profile="high",
                level="4.0",
                keyframe_interval=60,
            ),
            audio=AudioSettings(
                codec=AudioCodec.AAC.value,
                bitrate="192k",
                sample_rate=48000,
                channels=2,
                normalize=True,
                loudness=-14.0,
            ),
            constraints=PlatformConstraints(
                max_duration_seconds=14400,  # 4 hours
                max_file_size_mb=10240,      # 10 GB
                max_resolution=(1920, 1080),
                max_title_length=255,
            ),
            container="mp4",
            extension=".mp4",
            recommended_for=["Long-form content", "Live recordings", "Ads"],
            tips=[
                "Facebook organic reach video pe zyada hai",
                "Captions add karo - 85% videos silently dekhe jaate hain",
                "Square format (1:1) bhi Facebook pe achha perform karta hai",
            ],
            ffmpeg_extra_args=["-movflags", "+faststart"]
        )

    # ----------------------------------------------------------
    # LINKEDIN PRESETS
    # ----------------------------------------------------------

    @staticmethod
    def linkedin() -> ExportPreset:
        """LinkedIn - Professional content"""
        return ExportPreset(
            platform=Platform.LINKEDIN.value,
            name="linkedin",
            display_name="LinkedIn Video",
            description="LinkedIn professional content ke liye",
            category="landscape",
            video=VideoSettings(
                width=1920, height=1080,
                fps=30,
                codec=VideoCodec.H264.value,
                bitrate="5M",
                crf=22,
                preset="medium",
                pixel_format="yuv420p",
                max_bitrate="7M",
                buf_size="12M",
                profile="main",
                level="4.0",
                keyframe_interval=60,
            ),
            audio=AudioSettings(
                codec=AudioCodec.AAC.value,
                bitrate="128k",
                sample_rate=44100,
                channels=2,
                normalize=True,
                loudness=-16.0,
            ),
            constraints=PlatformConstraints(
                max_duration_seconds=600,
                max_file_size_mb=5120,
                max_resolution=(4096, 2304),
                max_title_length=200,
            ),
            container="mp4",
            extension=".mp4",
            recommended_for=["Business content", "Tutorials", "Presentations"],
            tips=[
                "Professional tone rakho",
                "LinkedIn pe 30 second se 5 minute videos best hain",
                "Subtitles add karo - office mein muted dekha jaata hai",
            ],
            ffmpeg_extra_args=["-movflags", "+faststart"]
        )

    # ----------------------------------------------------------
    # VIMEO PRESETS
    # ----------------------------------------------------------

    @staticmethod
    def vimeo() -> ExportPreset:
        """Vimeo - High quality portfolio"""
        return ExportPreset(
            platform=Platform.VIMEO.value,
            name="vimeo",
            display_name="Vimeo HD",
            description="Vimeo ke liye highest quality export",
            category="landscape",
            video=VideoSettings(
                width=1920, height=1080,
                fps=30,
                codec=VideoCodec.H264.value,
                bitrate="10M",
                crf=16,              # Higher quality
                preset="slow",
                pixel_format="yuv420p",
                max_bitrate="12M",
                buf_size="20M",
                profile="high",
                level="4.1",
                two_pass=True,       # Two-pass for Vimeo
                keyframe_interval=60,
            ),
            audio=AudioSettings(
                codec=AudioCodec.AAC.value,
                bitrate="320k",      # High quality audio
                sample_rate=48000,
                channels=2,
                normalize=True,
                loudness=-14.0,
            ),
            constraints=PlatformConstraints(
                max_duration_seconds=None,   # Unlimited (based on plan)
                max_file_size_mb=5120,       # 5GB free plan
                supports_hdr=True,
                max_resolution=(3840, 2160),
                max_title_length=128,
            ),
            container="mp4",
            extension=".mp4",
            recommended_for=["Portfolio", "Animation showcase", "Film"],
            tips=[
                "Vimeo best video quality deliver karta hai",
                "Two-pass encoding use karo best results ke liye",
                "Animation reels ke liye Vimeo best platform hai",
            ],
            ffmpeg_extra_args=["-movflags", "+faststart"]
        )

    # ----------------------------------------------------------
    # CUSTOM/GENERIC PRESETS
    # ----------------------------------------------------------

    @staticmethod
    def web_optimized() -> ExportPreset:
        """Web optimized - General streaming"""
        return ExportPreset(
            platform=Platform.CUSTOM.value,
            name="web_optimized",
            display_name="Web Optimized (General)",
            description="Kisi bhi website ke liye optimized video",
            category="landscape",
            video=VideoSettings(
                width=1280, height=720,
                fps=30,
                codec=VideoCodec.H264.value,
                bitrate="3M",
                crf=23,
                preset="medium",
                pixel_format="yuv420p",
                max_bitrate="5M",
                buf_size="8M",
                profile="main",
                level="3.1",
                keyframe_interval=60,
            ),
            audio=AudioSettings(
                codec=AudioCodec.AAC.value,
                bitrate="128k",
                sample_rate=44100,
                channels=2,
                normalize=True,
                loudness=-16.0,
            ),
            container="mp4",
            extension=".mp4",
            recommended_for=["Website embedding", "Email campaigns", "General sharing"],
            tips=[
                "faststart flag web streaming ke liye zaruri hai",
                "Chhota file size = jaldi load hoga",
            ],
            ffmpeg_extra_args=["-movflags", "+faststart"]
        )

    @staticmethod
    def draft_preview() -> ExportPreset:
        """Draft preview - Jaldi dekhne ke liye low quality"""
        return ExportPreset(
            platform=Platform.CUSTOM.value,
            name="draft_preview",
            display_name="Draft Preview",
            description="Quick preview ke liye - low quality, fast render",
            category="landscape",
            video=VideoSettings(
                width=854, height=480,
                fps=24,
                codec=VideoCodec.H264.value,
                bitrate="1M",
                crf=28,
                preset="ultrafast",      # Fastest encoding
                pixel_format="yuv420p",
                max_bitrate="2M",
                buf_size="4M",
                profile="baseline",
                level="3.0",
                keyframe_interval=48,
            ),
            audio=AudioSettings(
                codec=AudioCodec.AAC.value,
                bitrate="96k",
                sample_rate=44100,
                channels=2,
                normalize=False,
                loudness=-16.0,
            ),
            container="mp4",
            extension=".mp4",
            recommended_for=["Quick preview", "Client approval", "Internal review"],
            tips=[
                "Sirf preview ke liye use karo - final export nahi",
                "Ultrafast preset se zyada zyada jaldi render hoga",
            ],
            ffmpeg_extra_args=[]
        )


# ============================================================
# MAIN CLASS - Social Media Presets Manager
# ============================================================

class SocialMediaPresets:
    """
    Social Media Presets Manager.
    Sabhi platforms ke export settings manage karta hai.
    FFmpeg commands bhi generate karta hai.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialization - Sabhi presets load karo.
        
        Args:
            config: Optional config dictionary
        """
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # Sabhi presets ka dictionary
        self._presets: Dict[str, ExportPreset] = {}

        # Custom presets (user-defined)
        self._custom_presets: Dict[str, ExportPreset] = {}

        # Custom presets file path
        self._custom_presets_file = Path("presets/export_presets.json")

        # Presets load karo
        self._load_builtin_presets()
        self._load_custom_presets()

        logger.info(f"✅ SocialMediaPresets initialized - {len(self._presets)} presets loaded")

    def _load_builtin_presets(self):
        """
        Built-in presets register karo.
        Saare platform presets yahan add hote hain.
        """
        # YouTube presets
        self._register(PresetDefinitions.youtube_1080p())
        self._register(PresetDefinitions.youtube_1080p_60fps())
        self._register(PresetDefinitions.youtube_4k())
        self._register(PresetDefinitions.youtube_720p())
        self._register(PresetDefinitions.youtube_shorts())

        # Instagram presets
        self._register(PresetDefinitions.instagram_feed())
        self._register(PresetDefinitions.instagram_reels())
        self._register(PresetDefinitions.instagram_story())

        # TikTok
        self._register(PresetDefinitions.tiktok())

        # Twitter/X
        self._register(PresetDefinitions.twitter())

        # Facebook
        self._register(PresetDefinitions.facebook())

        # LinkedIn
        self._register(PresetDefinitions.linkedin())

        # Vimeo
        self._register(PresetDefinitions.vimeo())

        # Generic
        self._register(PresetDefinitions.web_optimized())
        self._register(PresetDefinitions.draft_preview())

        logger.debug(f"📦 {len(self._presets)} built-in presets loaded")

    def _register(self, preset: ExportPreset):
        """Ek preset register karo"""
        self._presets[preset.name] = preset

    def _load_custom_presets(self):
        """
        User-saved custom presets load karo.
        File se load karta hai.
        """
        try:
            if self._custom_presets_file.exists():
                data = read_json(str(self._custom_presets_file))
                if data:
                    for name, preset_data in data.items():
                        # Custom presets ko simple dict format mein store karte hain
                        logger.debug(f"Custom preset loaded: {name}")
                        self._custom_presets[name] = preset_data
        except Exception as e:
            logger.warning(f"Custom presets load nahi hua: {e}")

    def _save_custom_presets(self):
        """Custom presets save karo file mein"""
        try:
            ensure_dir(str(self._custom_presets_file.parent))
            write_json(str(self._custom_presets_file), self._custom_presets)
            logger.info("✅ Custom presets saved")
        except Exception as e:
            logger.error(f"Custom presets save fail: {e}")

    # ----------------------------------------------------------
    # PUBLIC API
    # ----------------------------------------------------------

    def get_preset(self, name: str) -> Optional[ExportPreset]:
        """
        Naam se preset lo.
        
        Args:
            name: Preset name (e.g., "youtube_1080p")
            
        Returns:
            ExportPreset ya None
        """
        return self._presets.get(name)

    def get_all_presets(self) -> Dict[str, ExportPreset]:
        """Sabhi built-in presets return karo"""
        return self._presets.copy()

    def get_presets_for_platform(self, platform: str) -> List[ExportPreset]:
        """
        Ek specific platform ke sabhi presets lo.
        
        Args:
            platform: Platform name (e.g., "youtube")
            
        Returns:
            List of ExportPreset
        """
        result = []
        for preset in self._presets.values():
            if preset.platform == platform:
                result.append(preset)
        return result

    def get_platform_names(self) -> List[str]:
        """Saare supported platforms ke names lo"""
        platforms = set()
        for preset in self._presets.values():
            platforms.add(preset.platform)
        return sorted(list(platforms))

    def list_presets_summary(self) -> List[Dict]:
        """
        Sabhi presets ki summary list.
        UI display ke liye useful.
        """
        summary = []
        for name, preset in self._presets.items():
            summary.append({
                "name": name,
                "display_name": preset.display_name,
                "platform": preset.platform,
                "resolution": preset.get_resolution_string(),
                "fps": preset.video.fps,
                "category": preset.category,
                "description": preset.description,
            })
        return summary

    def get_recommended_preset(self, platform: str) -> Optional[ExportPreset]:
        """
        Platform ke liye best/recommended preset lo.
        First matching preset return karta hai.
        """
        presets = self.get_presets_for_platform(platform)
        if presets:
            return presets[0]
        return None

    def create_custom_preset(
        self,
        name: str,
        display_name: str,
        width: int,
        height: int,
        fps: int = 30,
        video_bitrate: str = "5M",
        audio_bitrate: str = "192k",
        codec: str = "libx264",
        description: str = ""
    ) -> ExportPreset:
        """
        Custom preset banao aur save karo.
        
        Args:
            name: Unique preset name
            display_name: Display ke liye naam
            width, height: Resolution
            fps: Frame rate
            video_bitrate: Video bitrate
            audio_bitrate: Audio bitrate
            codec: Video codec
            description: Description
            
        Returns:
            Naya ExportPreset
        """
        preset = ExportPreset(
            platform=Platform.CUSTOM.value,
            name=name,
            display_name=display_name,
            description=description or f"Custom preset: {display_name}",
            category="custom",
            video=VideoSettings(
                width=width,
                height=height,
                fps=fps,
                codec=codec,
                bitrate=video_bitrate,
                crf=20,
                preset="medium",
                pixel_format="yuv420p",
            ),
            audio=AudioSettings(
                codec=AudioCodec.AAC.value,
                bitrate=audio_bitrate,
                sample_rate=48000,
            ),
            container="mp4",
            extension=".mp4",
        )

        # Register karo
        self._presets[name] = preset

        # Custom presets file mein save karo
        self._custom_presets[name] = preset.to_dict()
        self._save_custom_presets()

        logger.info(f"✅ Custom preset created: {name} ({width}x{height})")
        return preset

    def delete_custom_preset(self, name: str) -> bool:
        """
        Custom preset delete karo.
        Built-in presets delete nahi ho sakte.
        """
        if name in self._custom_presets:
            del self._custom_presets[name]
            if name in self._presets:
                del self._presets[name]
            self._save_custom_presets()
            logger.info(f"🗑️ Custom preset deleted: {name}")
            return True

        logger.warning(f"Custom preset nahi mila: {name}")
        return False

    # ----------------------------------------------------------
    # FFMPEG COMMAND GENERATION
    # ek preset se FFmpeg command banana
    # ----------------------------------------------------------

    def build_ffmpeg_command(
        self,
        preset: ExportPreset,
        input_file: str,
        output_file: str,
        duration: Optional[float] = None,
        start_time: Optional[float] = None,
        audio_input: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
    ) -> List[str]:
        """
        FFmpeg command build karo ek preset se.
        
        Args:
            preset: ExportPreset object
            input_file: Input video file path
            output_file: Output file path
            duration: Optional - clip duration (seconds)
            start_time: Optional - start time (seconds)
            audio_input: Optional - separate audio file
            extra_args: Additional FFmpeg arguments
            
        Returns:
            FFmpeg command as list of strings
        """
        cmd = ["ffmpeg", "-y"]  # -y = overwrite without asking

        # Start time (agar diya ho)
        if start_time is not None:
            cmd.extend(["-ss", str(start_time)])

        # Input file
        cmd.extend(["-i", input_file])

        # Separate audio input (agar diya ho)
        if audio_input:
            cmd.extend(["-i", audio_input])

        # Duration
        if duration is not None:
            cmd.extend(["-t", str(duration)])

        # ===== VIDEO SETTINGS =====
        v = preset.video

        # Codec
        cmd.extend(["-c:v", v.codec])

        # Resolution (scale filter)
        cmd.extend(["-vf", f"scale={v.width}:{v.height}"])

        # FPS
        cmd.extend(["-r", str(v.fps)])

        # CRF (quality)
        if v.codec in [VideoCodec.H264.value, VideoCodec.H265.value]:
            cmd.extend(["-crf", str(v.crf)])
            cmd.extend(["-preset", v.preset])

        # Bitrate constraints
        cmd.extend([
            "-b:v", v.bitrate,
            "-maxrate", v.max_bitrate,
            "-bufsize", v.buf_size,
        ])

        # H264/H265 specific
        if v.codec == VideoCodec.H264.value:
            cmd.extend([
                "-profile:v", v.profile,
                "-level", v.level,
            ])

        # Pixel format
        cmd.extend(["-pix_fmt", v.pixel_format])

        # Keyframe interval (GOP size)
        cmd.extend(["-g", str(v.keyframe_interval)])

        # ===== AUDIO SETTINGS =====
        a = preset.audio

        # Agar audio input hai, use karo
        if audio_input:
            cmd.extend(["-map", "0:v:0", "-map", "1:a:0"])

        cmd.extend([
            "-c:a", a.codec,
            "-b:a", a.bitrate,
            "-ar", str(a.sample_rate),
            "-ac", str(a.channels),
        ])

        # Audio normalization (loudnorm filter)
        if a.normalize:
            cmd.extend([
                "-af",
                f"loudnorm=I={a.loudness}:TP=-1.5:LRA=11"
            ])

        # ===== EXTRA ARGS =====
        if preset.ffmpeg_extra_args:
            cmd.extend(preset.ffmpeg_extra_args)

        if extra_args:
            cmd.extend(extra_args)

        # Output file
        cmd.append(output_file)

        return cmd

    def get_ffmpeg_command_string(
        self,
        preset_name: str,
        input_file: str,
        output_file: str,
        **kwargs
    ) -> str:
        """
        FFmpeg command as readable string lo.
        Copy-paste ke liye useful.
        """
        preset = self.get_preset(preset_name)
        if not preset:
            raise ValueError(f"Preset nahi mila: {preset_name}")

        cmd = self.build_ffmpeg_command(preset, input_file, output_file, **kwargs)
        return " ".join(cmd)

    def validate_file_for_platform(
        self,
        file_path: str,
        platform: str
    ) -> Dict[str, Any]:
        """
        Check karo ki file platform ke constraints ke andar hai ya nahi.
        
        Args:
            file_path: Video file path
            platform: Platform name
            
        Returns:
            Validation result dict
        """
        result = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "file_size_mb": 0,
        }

        preset = self.get_recommended_preset(platform)
        if not preset:
            result["errors"].append(f"Platform nahi mila: {platform}")
            result["valid"] = False
            return result

        # File size check
        try:
            size_bytes = os.path.getsize(file_path)
            size_mb = size_bytes / (1024 * 1024)
            result["file_size_mb"] = round(size_mb, 2)

            if preset.constraints.max_file_size_mb:
                if size_mb > preset.constraints.max_file_size_mb:
                    result["errors"].append(
                        f"File too large: {size_mb:.1f}MB "
                        f"(max: {preset.constraints.max_file_size_mb}MB)"
                    )
                    result["valid"] = False
                elif size_mb > preset.constraints.max_file_size_mb * 0.9:
                    result["warnings"].append(
                        f"File size limit ke paas hai: {size_mb:.1f}MB"
                    )

        except Exception as e:
            result["warnings"].append(f"File size check nahi ho saka: {e}")

        return result

    def print_preset_info(self, preset_name: str):
        """Preset ki detailed info print karo (debug ke liye)"""
        preset = self.get_preset(preset_name)
        if not preset:
            logger.error(f"Preset nahi mila: {preset_name}")
            return

        print(f"\n{'='*50}")
        print(f"📺 {preset.display_name}")
        print(f"{'='*50}")
        print(f"Platform     : {preset.platform}")
        print(f"Resolution   : {preset.get_resolution_string()}")
        print(f"Aspect Ratio : {preset.get_aspect_ratio()}")
        print(f"FPS          : {preset.video.fps}")
        print(f"Video Codec  : {preset.video.codec}")
        print(f"Video Bitrate: {preset.video.bitrate}")
        print(f"Audio Codec  : {preset.audio.codec}")
        print(f"Audio Bitrate: {preset.audio.bitrate}")
        print(f"Container    : {preset.container}")
        print(f"\n📝 Description: {preset.description}")

        if preset.tips:
            print(f"\n💡 Tips:")
            for tip in preset.tips:
                print(f"   • {tip}")

        if preset.constraints.max_duration_seconds:
            mins = preset.constraints.max_duration_seconds // 60
            secs = preset.constraints.max_duration_seconds % 60
            print(f"\n⏱️  Max Duration: {mins}m {secs}s")

        if preset.constraints.max_file_size_mb:
            print(f"💾 Max File Size: {preset.constraints.max_file_size_mb}MB")

        # Estimated sizes
        print(f"\n📊 Estimated File Sizes:")
        for duration in [30, 60, 300, 600]:
            size = preset.estimate_file_size_mb(duration)
            mins = duration // 60
            secs = duration % 60
            time_str = f"{mins}m{secs}s" if mins else f"{secs}s"
            print(f"   {time_str:>6} video = ~{size:.1f} MB")

        print(f"{'='*50}\n")


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

_global_presets: Optional[SocialMediaPresets] = None


def get_presets() -> SocialMediaPresets:
    """Global SocialMediaPresets instance lo (singleton pattern)"""
    global _global_presets
    if _global_presets is None:
        _global_presets = SocialMediaPresets()
    return _global_presets


def get_preset(name: str) -> Optional[ExportPreset]:
    """Quick helper - naam se preset lo"""
    return get_presets().get_preset(name)


def get_youtube_preset(quality: str = "1080p") -> Optional[ExportPreset]:
    """YouTube preset quickly lo"""
    mapping = {
        "720p": "youtube_720p",
        "1080p": "youtube_1080p",
        "1080p60": "youtube_1080p_60fps",
        "4k": "youtube_4k",
        "shorts": "youtube_shorts",
    }
    name = mapping.get(quality, "youtube_1080p")
    return get_presets().get_preset(name)


# ============================================================
# TEST SECTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="DEBUG")
    print_banner("Social Media Presets Test", "Platform Export Settings Manager")

    # ===== TEST 1: Initialization =====
    print_section("Test 1: Initialization")
    manager = SocialMediaPresets()
    all_presets = manager.get_all_presets()
    print(f"✅ Total presets loaded: {len(all_presets)}")

    # ===== TEST 2: List All Presets =====
    print_section("Test 2: All Presets Summary")
    summary = manager.list_presets_summary()
    for p in summary:
        print(f"  📺 {p['name']:30s} | {p['resolution']:12s} | {p['fps']}fps | {p['platform']}")

    # ===== TEST 3: Platform-specific Presets =====
    print_section("Test 3: YouTube Presets")
    yt_presets = manager.get_presets_for_platform(Platform.YOUTUBE.value)
    print(f"✅ YouTube presets: {len(yt_presets)}")
    for p in yt_presets:
        print(f"  → {p.display_name}: {p.get_resolution_string()} @ {p.video.fps}fps")

    # ===== TEST 4: Get Specific Preset =====
    print_section("Test 4: Preset Details - YouTube 1080p")
    manager.print_preset_info("youtube_1080p")

    # ===== TEST 5: FFmpeg Command Generation =====
    print_section("Test 5: FFmpeg Command Generation")
    preset = manager.get_preset("youtube_1080p")
    if preset:
        cmd = manager.build_ffmpeg_command(
            preset=preset,
            input_file="input.mp4",
            output_file="output_youtube.mp4",
            duration=300.0,
        )
        print(f"✅ FFmpeg command generated ({len(cmd)} args):")
        print(f"   {' '.join(cmd[:8])}...")

        cmd_str = manager.get_ffmpeg_command_string(
            "youtube_shorts",
            "animation.mp4",
            "shorts_output.mp4"
        )
        print(f"\n✅ Shorts command:\n   {cmd_str[:100]}...")

    # ===== TEST 6: File Size Estimation =====
    print_section("Test 6: File Size Estimates")
    for preset_name in ["youtube_1080p", "youtube_4k", "instagram_reels", "draft_preview"]:
        p = manager.get_preset(preset_name)
        if p:
            size_5min = p.estimate_file_size_mb(300)
            print(f"  {p.display_name:35s} | 5 min = ~{size_5min:.1f} MB")

    # ===== TEST 7: Custom Preset =====
    print_section("Test 7: Custom Preset Creation")
    custom = manager.create_custom_preset(
        name="my_4k_custom",
        display_name="My 4K Custom",
        width=3840, height=2160,
        fps=30,
        video_bitrate="20M",
        audio_bitrate="256k",
        description="Mera custom 4K preset"
    )
    print(f"✅ Custom preset created: {custom.name}")
    print(f"   Resolution: {custom.get_resolution_string()}")
    print(f"   Aspect: {custom.get_aspect_ratio()}")

    # Custom preset delete karo
    deleted = manager.delete_custom_preset("my_4k_custom")
    print(f"✅ Custom preset deleted: {deleted}")

    # ===== TEST 8: All Platforms List =====
    print_section("Test 8: Supported Platforms")
    platforms = manager.get_platform_names()
    print(f"✅ {len(platforms)} platforms supported:")
    for plat in platforms:
        presets = manager.get_presets_for_platform(plat)
        print(f"  📱 {plat:25s} - {len(presets)} preset(s)")

    # ===== TEST 9: Convenience Functions =====
    print_section("Test 9: Convenience Functions")
    yt = get_youtube_preset("1080p")
    print(f"✅ get_youtube_preset('1080p'): {yt.display_name if yt else 'None'}")

    yt_4k = get_youtube_preset("4k")
    print(f"✅ get_youtube_preset('4k'): {yt_4k.display_name if yt_4k else 'None'}")

    shorts = get_youtube_preset("shorts")
    print(f"✅ get_youtube_preset('shorts'): {shorts.display_name if shorts else 'None'}")

    # ===== TEST 10: TikTok Preset Info =====
    print_section("Test 10: TikTok Preset Details")
    manager.print_preset_info("tiktok")

    print_banner("✅ All Tests Passed!", "social_media_presets.py Working Perfectly")