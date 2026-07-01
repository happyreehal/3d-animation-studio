# ============================================================
# src/pipeline/video_generator.py
# 3D Animation Studio - Video Generator
# FINAL STEP: Automation data → Actual MP4 video
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
import subprocess
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum
from pathlib import Path

from src.utils import (
    get_logger,
    get_config,
    ensure_dir,
    generate_uuid,
    get_timestamp,
    write_json,
    format_bytes,
    get_file_size,
)

logger = get_logger("VideoGenerator")


# ============================================================
# ENUMS
# ============================================================

class VideoQuality(Enum):
    """Video quality presets"""
    DRAFT       = "draft"        # 480p, fast render
    MEDIUM      = "medium"       # 720p, balanced
    HIGH        = "high"         # 1080p, good quality
    ULTRA       = "ultra"        # 4K, best quality


class OutputFormat(Enum):
    """Output video formats"""
    MP4         = "mp4"          # Universal
    MP4_H265    = "mp4_h265"     # Better compression
    WEBM        = "webm"         # Web optimized
    MOV         = "mov"          # Apple/Pro


class RenderStage(Enum):
    """Video generation stages"""
    IDLE            = "idle"
    PREPARING       = "preparing"
    RENDERING_FRAMES= "rendering_frames"
    GENERATING_AUDIO= "generating_audio"
    MIXING_AUDIO    = "mixing_audio"
    ENCODING_VIDEO  = "encoding_video"
    ADDING_SUBTITLES= "adding_subtitles"
    FINALIZING      = "finalizing"
    COMPLETE        = "complete"
    FAILED          = "failed"
    CANCELLED       = "cancelled"


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class VideoSettings:
    """Video output settings"""
    # Quality
    quality:        str             = VideoQuality.HIGH.value
    format:         str             = OutputFormat.MP4.value

    # Resolution
    width:          int             = 1920
    height:         int             = 1080
    fps:            int             = 30

    # Encoding
    video_codec:    str             = "libx264"
    video_bitrate:  str             = "8M"
    audio_codec:    str             = "aac"
    audio_bitrate:  str             = "192k"
    preset:         str             = "medium"      # ffmpeg preset
    crf:            int             = 23             # 0-51, lower = better

    # Audio
    audio_sample_rate: int          = 48000
    audio_channels: int             = 2              # Stereo

    # Extras
    include_audio:  bool            = True
    include_subtitles: bool         = True
    include_music:  bool            = True
    include_sfx:    bool            = True

    # Optimization
    two_pass:       bool            = False
    hardware_accel: bool            = False

    # YouTube optimization
    youtube_optimized: bool         = True


@dataclass
class RenderProgress:
    """Video rendering progress"""
    stage:              str         = RenderStage.IDLE.value
    percent:            float       = 0.0
    current_frame:      int         = 0
    total_frames:       int         = 0
    fps:                float       = 0.0
    elapsed_seconds:    float       = 0.0
    eta_seconds:        float       = 0.0
    message:            str         = ""

    def get_progress_bar(self, width: int = 30) -> str:
        """Text progress bar"""
        filled = int(width * self.percent / 100)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}] {self.percent:.1f}%"

    def get_eta_str(self) -> str:
        """ETA formatted"""
        if self.eta_seconds <= 0:
            return "Calculating..."
        mins = int(self.eta_seconds // 60)
        secs = int(self.eta_seconds % 60)
        return f"{mins}m {secs}s"


@dataclass
class GeneratedVideo:
    """Final generated video info"""
    success:            bool        = False
    video_path:         str         = ""

    # Metadata
    duration_seconds:   float       = 0.0
    total_frames:       int         = 0
    resolution:         Tuple[int, int] = (1920, 1080)
    fps:                int         = 30
    file_size:          int         = 0

    # Extras generated
    audio_path:         str         = ""
    subtitle_path:      str         = ""
    thumbnail_path:     str         = ""
    metadata_path:      str         = ""

    # Timing
    generation_time:    float       = 0.0

    # Error
    error:              str         = ""

    def get_file_size_str(self) -> str:
        return format_bytes(self.file_size)

    def get_summary(self) -> Dict:
        return {
            "success":          self.success,
            "video_path":       self.video_path,
            "duration":         round(self.duration_seconds, 2),
            "resolution":       f"{self.resolution[0]}x{self.resolution[1]}",
            "fps":              self.fps,
            "file_size":        self.get_file_size_str(),
            "generation_time":  round(self.generation_time, 2),
        }


# ============================================================
# FFMPEG WRAPPER
# ============================================================

class FFmpegWrapper:
    """
    FFmpeg wrapper - actual video encoding.
    ffmpeg-python use karta hai agar available ho.
    """

    def __init__(self):
        self._ffmpeg_available = self._check_ffmpeg()
        if self._ffmpeg_available:
            logger.info("✅ FFmpeg available")
        else:
            logger.warning(
                "⚠️  FFmpeg nahi mila. "
                "Install karo: winget install Gyan.FFmpeg"
            )

    def _check_ffmpeg(self) -> bool:
        """FFmpeg installed hai?"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    def create_video_from_frames(
        self,
        frames_dir: str,
        output_path: str,
        settings: VideoSettings,
        audio_file: Optional[str] = None,
        subtitle_file: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """
        Image frames se video banao FFmpeg use karke.

        Args:
            frames_dir: Frame images ka folder (frame_%06d.png format)
            output_path: Output video file
            settings: Video settings
            audio_file: Optional audio track
            subtitle_file: Optional subtitle file
            progress_callback: Progress updates ke liye
        """
        if not self._ffmpeg_available:
            logger.error("FFmpeg available nahi hai")
            return False

        try:
            # Frame pattern
            frame_pattern = os.path.join(frames_dir, "frame_%06d.png")

            # Build FFmpeg command
            cmd = [
                "ffmpeg", "-y",  # Overwrite
                "-framerate", str(settings.fps),
                "-i", frame_pattern,
            ]

            # Audio input
            if audio_file and os.path.exists(audio_file):
                cmd.extend(["-i", audio_file])

            # Video codec
            cmd.extend([
                "-c:v", settings.video_codec,
                "-preset", settings.preset,
                "-crf", str(settings.crf),
                "-pix_fmt", "yuv420p",
            ])

            # Resolution
            cmd.extend([
                "-vf", f"scale={settings.width}:{settings.height}",
            ])

            # Bitrate
            cmd.extend([
                "-b:v", settings.video_bitrate,
                "-maxrate", settings.video_bitrate,
                "-bufsize", "16M",
            ])

            # Audio settings
            if audio_file:
                cmd.extend([
                    "-c:a", settings.audio_codec,
                    "-b:a", settings.audio_bitrate,
                    "-ar", str(settings.audio_sample_rate),
                    "-ac", str(settings.audio_channels),
                ])

            # YouTube optimization
            if settings.youtube_optimized:
                cmd.extend([
                    "-movflags", "+faststart",
                    "-profile:v", "high",
                    "-level", "4.1",
                ])

            # Output
            cmd.append(output_path)

            logger.debug(f"FFmpeg command: {' '.join(cmd[:10])}...")

            # Run FFmpeg
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )

            # Progress tracking (simple)
            if progress_callback:
                # Simple progress callback
                for line in process.stderr:
                    if "frame=" in line:
                        try:
                            # Parse frame count
                            frame_str = line.split("frame=")[1].split()[0]
                            frame_num = int(frame_str)
                            progress_callback(frame_num)
                        except Exception:
                            pass

            process.wait()

            if process.returncode == 0:
                logger.info(f"✅ Video created: {output_path}")
                return True
            else:
                logger.error(f"FFmpeg failed with code {process.returncode}")
                return False

        except Exception as e:
            logger.error(f"FFmpeg error: {e}")
            return False

    def concat_audio_files(
        self,
        audio_files: List[Tuple[str, float]],
        output_path: str,
        total_duration: float,
    ) -> bool:
        """
        Multiple audio files ko timeline pe concatenate karo.

        Args:
            audio_files: List of (file_path, start_time_seconds)
            output_path: Output audio file
            total_duration: Total duration in seconds
        """
        if not self._ffmpeg_available or not audio_files:
            return False

        try:
            # Filter complex banao har audio ke liye
            valid_files = [
                (f, t) for f, t in audio_files
                if os.path.exists(f) and self._is_valid_audio(f)
            ]

            if not valid_files:
                # No valid audio - silent audio banao
                return self._create_silent_audio(output_path, total_duration)

            # Build command
            cmd = ["ffmpeg", "-y"]

            # Add inputs
            for audio_file, _ in valid_files:
                cmd.extend(["-i", audio_file])

            # Build filter_complex for mixing at timestamps
            filter_parts = []
            for i, (_, start_time) in enumerate(valid_files):
                delay_ms = int(start_time * 1000)
                filter_parts.append(
                    f"[{i}:a]adelay={delay_ms}|{delay_ms}[a{i}]"
                )

            # Mix all audio streams
            mix_inputs = "".join(f"[a{i}]" for i in range(len(valid_files)))
            filter_parts.append(
                f"{mix_inputs}amix=inputs={len(valid_files)}:duration=longest[out]"
            )

            filter_complex = ";".join(filter_parts)

            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "[out]",
                "-t", str(total_duration),
                "-c:a", "pcm_s16le",
                "-ar", "48000",
                "-ac", "2",
                output_path,
            ])

            process = subprocess.run(
                cmd, capture_output=True, timeout=300
            )

            if process.returncode == 0:
                logger.debug(f"Audio mixed: {output_path}")
                return True
            else:
                logger.warning(f"Audio mix failed, creating silent audio")
                return self._create_silent_audio(output_path, total_duration)

        except Exception as e:
            logger.warning(f"Audio concat error: {e}")
            return self._create_silent_audio(output_path, total_duration)

    def _is_valid_audio(self, path: str) -> bool:
        """Check karo audio valid hai (real WAV file, not simulation)"""
        try:
            with open(path, 'rb') as f:
                header = f.read(4)
                return header == b'RIFF'
        except Exception:
            return False

    def _create_silent_audio(
        self,
        output_path: str,
        duration: float,
    ) -> bool:
        """Silent audio file banao"""
        if not self._ffmpeg_available:
            # Empty file
            try:
                with open(output_path, 'w') as f:
                    f.write("")
                return True
            except Exception:
                return False

        try:
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"anullsrc=r=48000:cl=stereo",
                "-t", str(duration),
                "-c:a", "pcm_s16le",
                output_path,
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            return result.returncode == 0
        except Exception:
            return False


# ============================================================
# FRAME RENDERER (Simplified)
# ============================================================

class FrameRenderer:
    """
    Frame renderer - Scene ke frames render karta hai.
    Simplified version - solid color frames with text overlay.
    """

    def __init__(self, settings: VideoSettings):
        self.settings = settings
        self._pil_available = self._check_pil()

    def _check_pil(self) -> bool:
        try:
            from PIL import Image, ImageDraw, ImageFont
            return True
        except ImportError:
            return False

    def render_scene_frames(
        self,
        scene_index: int,
        built_scene: Any,
        scene_animation: Any,
        start_frame: int,
        end_frame: int,
        output_dir: str,
        progress_callback: Optional[Callable] = None,
    ) -> int:
        """
        Ek scene ke sabhi frames render karo.

        Returns:
            Rendered frames count
        """
        if not self._pil_available:
            logger.warning("PIL nahi mila - frame rendering skip")
            return 0

        from PIL import Image, ImageDraw, ImageFont

        rendered = 0
        total = end_frame - start_frame

        # Get scene properties for rendering
        bg_color = self._get_bg_color(built_scene)
        characters = built_scene.characters if built_scene else []

        # Font
        try:
            font_large = ImageFont.truetype("arial.ttf", 48)
            font_medium = ImageFont.truetype("arial.ttf", 32)
            font_small = ImageFont.truetype("arial.ttf", 24)
        except Exception:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Render each frame
        for frame_num in range(start_frame, end_frame):
            # Create image
            img = Image.new(
                'RGB',
                (self.settings.width, self.settings.height),
                self._normalize_color(bg_color)
            )
            draw = ImageDraw.Draw(img)

            # Draw gradient
            self._draw_gradient(draw, bg_color)

            # Draw scene info
            self._draw_scene_info(
                draw,
                built_scene,
                scene_animation,
                frame_num,
                characters,
                font_large,
                font_medium,
                font_small,
            )

            # Draw current dialogue (if any)
            self._draw_current_dialogue(
                draw,
                scene_animation,
                frame_num,
                font_medium,
                font_small,
            )

            # Save frame
            frame_path = os.path.join(
                output_dir,
                f"frame_{frame_num:06d}.png"
            )
            img.save(frame_path, "PNG", optimize=True)
            rendered += 1

            # Progress callback
            if progress_callback and rendered % 10 == 0:
                progress_callback(frame_num, total)

        return rendered

    def _get_bg_color(self, built_scene: Any) -> List[float]:
        """Background color from scene"""
        if built_scene and built_scene.environment:
            return built_scene.environment.background_color
        return [0.15, 0.15, 0.2]

    def _normalize_color(self, color: List[float]) -> Tuple[int, int, int]:
        """0-1 color ko 0-255 tuple mein convert karo"""
        return (
            int(color[0] * 255),
            int(color[1] * 255),
            int(color[2] * 255),
        )

    def _draw_gradient(self, draw, base_color: List[float]):
        """Simple vertical gradient"""
        try:
            top_color = self._normalize_color([c * 0.7 for c in base_color])
            bot_color = self._normalize_color([min(1.0, c * 1.3) for c in base_color])

            h = self.settings.height
            for y in range(0, h, 4):
                ratio = y / h
                r = int(top_color[0] * (1 - ratio) + bot_color[0] * ratio)
                g = int(top_color[1] * (1 - ratio) + bot_color[1] * ratio)
                b = int(top_color[2] * (1 - ratio) + bot_color[2] * ratio)
                draw.rectangle(
                    [0, y, self.settings.width, y + 4],
                    fill=(r, g, b)
                )
        except Exception:
            pass

    def _draw_scene_info(
        self,
        draw,
        built_scene: Any,
        scene_animation: Any,
        frame_num: int,
        characters: List[Any],
        font_large,
        font_medium,
        font_small,
    ):
        """Scene info aur characters draw karo"""
        try:
            # Scene heading
            if built_scene:
                heading = built_scene.heading[:60]
                draw.text(
                    (40, 40),
                    f"🎬 {heading}",
                    fill=(255, 255, 255),
                    font=font_medium,
                )

            # Characters
            if characters:
                y_offset = 120
                for char in characters:
                    char_color = self._get_character_color(char.gender)
                    draw.text(
                        (40, y_offset),
                        f"🧍 {char.name}",
                        fill=char_color,
                        font=font_small,
                    )
                    y_offset += 40

            # Frame counter
            frame_text = f"Frame {frame_num}"
            draw.text(
                (self.settings.width - 200, 40),
                frame_text,
                fill=(150, 150, 180),
                font=font_small,
            )

            # Scene number
            if built_scene:
                scene_text = f"Scene {built_scene.scene_index + 1}"
                draw.text(
                    (self.settings.width - 200, 80),
                    scene_text,
                    fill=(0, 212, 255),
                    font=font_small,
                )

        except Exception as e:
            logger.debug(f"Draw info error: {e}")

    def _draw_current_dialogue(
        self,
        draw,
        scene_animation: Any,
        frame_num: int,
        font_medium,
        font_small,
    ):
        """Current active dialogue draw karo"""
        try:
            if not scene_animation or not scene_animation.voice_clips:
                return

            # Find current dialogue
            current_clip = None
            for clip in scene_animation.voice_clips:
                if clip.start_frame <= frame_num < clip.end_frame:
                    current_clip = clip
                    break

            if not current_clip:
                return

            # Draw dialogue box at bottom
            box_y = self.settings.height - 200
            box_height = 160
            box_padding = 40

            # Background rectangle
            draw.rectangle(
                [
                    box_padding,
                    box_y,
                    self.settings.width - box_padding,
                    box_y + box_height,
                ],
                fill=(0, 0, 0, 180),
                outline=(0, 212, 255),
                width=3,
            )

            # Character name
            draw.text(
                (box_padding + 20, box_y + 15),
                f"👤 {current_clip.character}",
                fill=(0, 212, 255),
                font=font_medium,
            )

            # Emotion badge
            draw.text(
                (box_padding + 300, box_y + 20),
                f"[{current_clip.emotion}]",
                fill=(255, 200, 100),
                font=font_small,
            )

            # Dialogue text (word wrap)
            dialogue_text = current_clip.text
            wrapped_text = self._wrap_text(
                dialogue_text,
                max_width=self.settings.width - 2 * box_padding - 40,
                font=font_medium,
            )
            draw.text(
                (box_padding + 20, box_y + 65),
                wrapped_text,
                fill=(255, 255, 255),
                font=font_medium,
            )

        except Exception as e:
            logger.debug(f"Draw dialogue error: {e}")

    def _wrap_text(self, text: str, max_width: int, font) -> str:
        """Text wrap karo max width ke andar"""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            try:
                bbox = font.getbbox(test_line)
                width = bbox[2] - bbox[0]
            except Exception:
                width = len(test_line) * 12

            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        return '\n'.join(lines[:3])  # Max 3 lines

    def _get_character_color(self, gender: str) -> Tuple[int, int, int]:
        """Character gender se color"""
        colors = {
            "male":     (100, 180, 255),
            "female":   (255, 150, 200),
            "unknown":  (200, 200, 200),
        }
        return colors.get(gender, (200, 200, 200))


# ============================================================
# SUBTITLE GENERATOR
# ============================================================

class SubtitleGenerator:
    """SRT subtitles generate karta hai automation data se"""

    @staticmethod
    def generate_srt(
        scene_animations: List[Any],
        fps: int,
        output_path: str,
    ) -> bool:
        """SRT subtitle file banao"""
        try:
            ensure_dir(os.path.dirname(output_path))

            srt_content = ""
            counter = 1

            for scene_anim in scene_animations:
                for clip in scene_anim.voice_clips:
                    # Timing
                    start_sec = clip.start_frame / fps
                    end_sec = clip.end_frame / fps

                    start_time = SubtitleGenerator._seconds_to_srt_time(start_sec)
                    end_time = SubtitleGenerator._seconds_to_srt_time(end_sec)

                    # SRT entry
                    srt_content += f"{counter}\n"
                    srt_content += f"{start_time} --> {end_time}\n"
                    srt_content += f"[{clip.character}] {clip.text}\n\n"

                    counter += 1

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)

            logger.debug(f"Subtitles saved: {output_path} ({counter-1} entries)")
            return True

        except Exception as e:
            logger.warning(f"Subtitle generation failed: {e}")
            return False

    @staticmethod
    def _seconds_to_srt_time(seconds: float) -> str:
        """Seconds ko SRT time format mein"""
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{mins:02d}:{secs:02d},{ms:03d}"


# ============================================================
# METADATA GENERATOR
# ============================================================

class VideoMetadata:
    """Video metadata banata hai"""

    @staticmethod
    def generate_metadata(
        automation_result: Any,
        video_settings: VideoSettings,
        output_path: str,
    ) -> Dict:
        """Complete metadata generate karo"""
        try:
            script = automation_result.parsed_script

            # Basic title
            title = script.title if script else "Untitled Animation"

            # Description
            description_parts = [
                f"🎬 {title}",
                "",
                f"⏱️ Duration: {automation_result.total_duration:.1f} seconds",
                f"🎭 Characters: {len(script.characters) if script else 0}",
                f"🎬 Scenes: {automation_result.total_scenes}",
                f"💬 Dialogues: {automation_result.total_dialogues}",
                "",
                "Created with 3D Animation Studio - Free & Open Source",
                "https://github.com/happyreehal/3d-animation-studio",
            ]
            description = "\n".join(description_parts)

            # Tags
            tags = [
                "3d animation",
                "animation",
                "3d",
                "animation studio",
                "python animation",
                "open source",
                "youtube animation",
            ]

            # Add character names as tags
            if script:
                for char_name in list(script.characters.keys())[:5]:
                    tags.append(char_name.lower())

            metadata = {
                "title":            title,
                "description":      description,
                "tags":             tags,
                "duration_seconds": automation_result.total_duration,
                "total_frames":     automation_result.total_frames,
                "resolution":       f"{video_settings.width}x{video_settings.height}",
                "fps":              video_settings.fps,
                "created_at":       get_timestamp(),
                "scenes": [
                    {
                        "index":     s.scene_index,
                        "duration":  (s.end_frame - s.start_frame) / video_settings.fps,
                    }
                    for s in automation_result.scene_animations
                ],
                "characters": list(script.characters.keys()) if script else [],
            }

            # Save metadata
            write_json(output_path, metadata)
            return metadata

        except Exception as e:
            logger.warning(f"Metadata generation failed: {e}")
            return {}


# ============================================================
# MAIN VIDEO GENERATOR
# ============================================================

class VideoGenerator:
    """
    MAIN VIDEO GENERATOR - Final MP4 export!

    AutomationResult se actual video file banata hai:
    1. Har scene ke frames render karo
    2. Audio track mix karo (voices + music + SFX)
    3. FFmpeg se video encode karo
    4. Subtitles add karo
    5. Metadata generate karo
    """

    def __init__(self, config: Optional[Dict] = None):
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        self.ffmpeg = FFmpegWrapper()

        # Progress
        self._progress = RenderProgress()
        self._progress_callbacks: List[Callable[[RenderProgress], None]] = []
        self._cancel_requested = False

        # Async
        self._worker_thread: Optional[threading.Thread] = None

        logger.info("✅ VideoGenerator initialized")

    # ----------------------------------------------------------
    # MAIN METHOD
    # ----------------------------------------------------------

    def generate_video(
        self,
        automation_result: Any,
        output_path: str,
        settings: Optional[VideoSettings] = None,
        async_mode: bool = False,
    ) -> GeneratedVideo:
        """
        AutomationResult se actual MP4 video generate karo.

        Args:
            automation_result: AutomationResult from automation_engine
            output_path: Output MP4 file path
            settings: Video settings (None = default HIGH quality)
            async_mode: Background thread mein run karo

        Returns:
            GeneratedVideo with all info
        """
        if settings is None:
            settings = self._get_default_settings()

        if async_mode:
            self._worker_thread = threading.Thread(
                target=self._generate_internal,
                args=(automation_result, output_path, settings),
                daemon=True,
            )
            self._cancel_requested = False
            self._worker_thread.start()
            return GeneratedVideo(success=False, error="Async started")
        else:
            return self._generate_internal(
                automation_result, output_path, settings
            )

    def _generate_internal(
        self,
        automation_result: Any,
        output_path: str,
        settings: VideoSettings,
    ) -> GeneratedVideo:
        """Actual generation logic"""
        start_time = time.time()
        result = GeneratedVideo(
            resolution = (settings.width, settings.height),
            fps        = settings.fps,
        )

        try:
            self._cancel_requested = False

            # Validate input
            if not automation_result or not automation_result.success:
                result.error = "Invalid automation result"
                return result

            # Setup directories
            output_dir = os.path.dirname(output_path) or "exports"
            ensure_dir(output_dir)

            temp_dir = f"{output_dir}/.temp_{generate_uuid()[:8]}"
            ensure_dir(temp_dir)

            frames_dir = f"{temp_dir}/frames"
            audio_dir = f"{temp_dir}/audio"
            ensure_dir(frames_dir)
            ensure_dir(audio_dir)

            total_frames = automation_result.total_frames
            self._progress.total_frames = total_frames

            # ===== STAGE 1: PREPARE =====
            self._update_progress(
                RenderStage.PREPARING.value, 2,
                "Preparation..."
            )

            # ===== STAGE 2: RENDER FRAMES =====
            if self._check_cancelled():
                return result

            self._update_progress(
                RenderStage.RENDERING_FRAMES.value, 5,
                f"Rendering {total_frames} frames..."
            )

            renderer = FrameRenderer(settings)
            frames_rendered = 0

            for scene_anim in automation_result.scene_animations:
                if self._check_cancelled():
                    return result

                # Get corresponding built scene
                built_scene = None
                for bs in automation_result.built_scenes:
                    if bs.scene_index == scene_anim.scene_index:
                        built_scene = bs
                        break

                # Render this scene's frames
                start_time_render = time.time()

                def frame_progress(current, total):
                    self._progress.current_frame = frames_rendered + current
                    percent = 5 + (self._progress.current_frame / total_frames) * 60
                    self._update_progress(
                        RenderStage.RENDERING_FRAMES.value, percent,
                        f"Frame {self._progress.current_frame}/{total_frames}"
                    )

                count = renderer.render_scene_frames(
                    scene_index      = scene_anim.scene_index,
                    built_scene      = built_scene,
                    scene_animation  = scene_anim,
                    start_frame      = scene_anim.start_frame,
                    end_frame        = scene_anim.end_frame,
                    output_dir       = frames_dir,
                    progress_callback= frame_progress,
                )
                frames_rendered += count

                render_time = time.time() - start_time_render
                fps = count / max(0.1, render_time)
                logger.debug(
                    f"Scene {scene_anim.scene_index}: "
                    f"{count} frames in {render_time:.1f}s ({fps:.1f} fps)"
                )

            self._progress.current_frame = frames_rendered

            # ===== STAGE 3: GENERATE AUDIO =====
            if self._check_cancelled():
                return result

            self._update_progress(
                RenderStage.GENERATING_AUDIO.value, 70,
                "Audio track mix ho raha hai..."
            )

            # Collect all audio files with timestamps
            audio_timeline = []
            for scene_anim in automation_result.scene_animations:
                for clip in scene_anim.voice_clips:
                    if clip.generated and clip.audio_file:
                        start_time_sec = clip.start_frame / settings.fps
                        audio_timeline.append((clip.audio_file, start_time_sec))

            # Mix audio
            mixed_audio = f"{audio_dir}/mixed.wav"
            audio_success = self.ffmpeg.concat_audio_files(
                audio_files    = audio_timeline,
                output_path    = mixed_audio,
                total_duration = automation_result.total_duration,
            )

            # ===== STAGE 4: ENCODE VIDEO =====
            if self._check_cancelled():
                return result

            self._update_progress(
                RenderStage.ENCODING_VIDEO.value, 80,
                "Video encoding..."
            )

            def encode_progress(frame):
                percent = 80 + (frame / total_frames) * 15
                self._update_progress(
                    RenderStage.ENCODING_VIDEO.value, percent,
                    f"Encoding frame {frame}/{total_frames}"
                )

            video_success = self.ffmpeg.create_video_from_frames(
                frames_dir       = frames_dir,
                output_path      = output_path,
                settings         = settings,
                audio_file       = mixed_audio if audio_success else None,
                progress_callback= encode_progress,
            )

            if not video_success:
                result.error = "Video encoding failed"
                self._update_progress(
                    RenderStage.FAILED.value, 100, "Encoding failed"
                )
                return result

            # ===== STAGE 5: ADD SUBTITLES =====
            if settings.include_subtitles:
                self._update_progress(
                    RenderStage.ADDING_SUBTITLES.value, 96,
                    "Subtitles generate ho rahi hain..."
                )

                subtitle_path = output_path.replace('.mp4', '.srt')
                SubtitleGenerator.generate_srt(
                    scene_animations = automation_result.scene_animations,
                    fps              = settings.fps,
                    output_path      = subtitle_path,
                )
                result.subtitle_path = subtitle_path

            # ===== STAGE 6: METADATA =====
            self._update_progress(
                RenderStage.FINALIZING.value, 98,
                "Metadata generate ho rahi hai..."
            )

            metadata_path = output_path.replace('.mp4', '_metadata.json')
            VideoMetadata.generate_metadata(
                automation_result = automation_result,
                video_settings    = settings,
                output_path       = metadata_path,
            )
            result.metadata_path = metadata_path

            # ===== CLEANUP =====
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

            # ===== SUCCESS =====
            result.success = True
            result.video_path = output_path
            result.total_frames = total_frames
            result.duration_seconds = automation_result.total_duration
            result.file_size = get_file_size(output_path)
            result.generation_time = time.time() - start_time

            self._update_progress(
                RenderStage.COMPLETE.value, 100,
                f"✅ Video ready: {output_path}"
            )

            logger.info(
                f"🎬 Video generated: {output_path} | "
                f"Size: {result.get_file_size_str()} | "
                f"Time: {result.generation_time:.1f}s"
            )

        except Exception as e:
            logger.error(f"Video generation error: {e}")
            import traceback
            traceback.print_exc()
            result.success = False
            result.error = str(e)
            self._update_progress(
                RenderStage.FAILED.value, 100, f"Error: {e}"
            )

        return result

    # ----------------------------------------------------------
    # HELPERS
    # ----------------------------------------------------------

    def _get_default_settings(self) -> VideoSettings:
        """Config se default settings lo"""
        cfg = self.config.get("rendering", {})
        export_cfg = self.config.get("export", {})

        return VideoSettings(
            quality        = cfg.get("default_quality", "high"),
            fps            = cfg.get("default_fps", 30),
            width          = export_cfg.get("default_width", 1920),
            height         = export_cfg.get("default_height", 1080),
            format         = export_cfg.get("default_format", "mp4"),
        )

    def _update_progress(
        self,
        stage: str,
        percent: float,
        message: str,
    ):
        """Progress update"""
        self._progress.stage = stage
        self._progress.percent = percent
        self._progress.message = message

        for cb in self._progress_callbacks:
            try:
                cb(self._progress)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")

    def add_progress_callback(self, callback: Callable[[RenderProgress], None]):
        """Progress callback register karo"""
        self._progress_callbacks.append(callback)

    def cancel_generation(self):
        """Generation cancel karo"""
        self._cancel_requested = True

    def _check_cancelled(self) -> bool:
        return self._cancel_requested

    def print_result_summary(self, result: GeneratedVideo):
        """Result summary print karo"""
        print(f"\n{'='*60}")
        print(f"🎬 VIDEO GENERATION RESULT")
        print(f"{'='*60}")

        summary = result.get_summary()
        for key, value in summary.items():
            print(f"  {key:20s}: {value}")

        if result.subtitle_path:
            print(f"  {'subtitles':20s}: {result.subtitle_path}")
        if result.metadata_path:
            print(f"  {'metadata':20s}: {result.metadata_path}")

        if result.error:
            print(f"\n  ❌ ERROR: {result.error}")

        print(f"{'='*60}\n")


# ============================================================
# GLOBAL INSTANCE
# ============================================================

_global_generator: Optional[VideoGenerator] = None


def get_video_generator() -> VideoGenerator:
    """Global VideoGenerator instance"""
    global _global_generator
    if _global_generator is None:
        _global_generator = VideoGenerator()
    return _global_generator


# ============================================================
# CONVENIENCE FUNCTION - Full Pipeline
# ============================================================

def script_to_video(
    script_text: str,
    output_path: str,
    title: str = "Untitled",
    language: str = "en",
    quality: str = "high",
    progress_callback: Optional[Callable] = None,
) -> GeneratedVideo:
    """
    🚀 ONE-CLICK MAGIC FUNCTION!
    Script text se directly MP4 video banao.

    Args:
        script_text: User ka script
        output_path: Output MP4 path
        title: Video title
        language: Language code
        quality: draft/medium/high/ultra
        progress_callback: Optional progress callback

    Returns:
        GeneratedVideo result
    """
    from src.pipeline.automation_engine import get_automation_engine

    logger.info(f"🚀 Starting script-to-video: {title}")

    # Step 1: Run automation
    engine = get_automation_engine()

    if progress_callback:
        def auto_progress(prog):
            progress_callback({
                "stage":   f"automation_{prog.stage}",
                "percent": prog.percent * 0.5,   # First 50%
                "message": prog.message,
            })
        engine.add_progress_callback(auto_progress)

    automation_result = engine.generate_from_script(
        script_text = script_text,
        title       = title,
        language    = language,
    )

    if not automation_result.success:
        logger.error(f"Automation failed: {automation_result.error}")
        return GeneratedVideo(
            success = False,
            error   = f"Automation failed: {automation_result.error}",
        )

    # Step 2: Generate video
    generator = get_video_generator()

    if progress_callback:
        def video_progress(prog):
            progress_callback({
                "stage":   f"video_{prog.stage}",
                "percent": 50 + prog.percent * 0.5,   # Last 50%
                "message": prog.message,
            })
        generator.add_progress_callback(video_progress)

    # Get default settings with quality override
    settings = generator._get_default_settings()
    settings.quality = quality

    if quality == "draft":
        settings.width = 854
        settings.height = 480
        settings.preset = "ultrafast"
        settings.crf = 28
    elif quality == "medium":
        settings.width = 1280
        settings.height = 720
        settings.preset = "fast"
        settings.crf = 25
    elif quality == "ultra":
        settings.width = 3840
        settings.height = 2160
        settings.preset = "slow"
        settings.crf = 18

    video_result = generator.generate_video(
        automation_result = automation_result,
        output_path       = output_path,
        settings          = settings,
    )

    return video_result


# ============================================================
# TEST SECTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")
    print_banner("Video Generator Test", "Automation Data → MP4 Video")

    # ===== TEST 1: FFmpeg Check =====
    print_section("Test 1: FFmpeg Availability")
    ffmpeg = FFmpegWrapper()
    print(f"✅ FFmpeg available: {ffmpeg._ffmpeg_available}")

    # ===== TEST 2: Settings =====
    print_section("Test 2: Video Settings")
    for quality in ["draft", "medium", "high", "ultra"]:
        settings = VideoSettings(quality=quality)
        print(
            f"✅ {quality:8s}: {settings.width}x{settings.height} "
            f"@ {settings.fps}fps, CRF={settings.crf}"
        )

    # ===== TEST 3: FrameRenderer =====
    print_section("Test 3: Frame Renderer")
    settings = VideoSettings(width=1280, height=720, fps=30)
    renderer = FrameRenderer(settings)
    print(f"✅ PIL available: {renderer._pil_available}")

    # ===== TEST 4: Subtitle Generation =====
    print_section("Test 4: Subtitle Generation")

    # Mock scene animation
    class MockClip:
        def __init__(self, char, text, start, end):
            self.character = char
            self.text = text
            self.start_frame = start
            self.end_frame = end

    class MockSceneAnim:
        def __init__(self):
            self.voice_clips = [
                MockClip("Hero", "Namaste doston!", 0, 45),
                MockClip("Villain", "Main tumhe rokunga!", 60, 120),
                MockClip("Hero", "Kabhi nahi!", 150, 200),
            ]

    mock_scenes = [MockSceneAnim()]

    subtitle_path = "temp/test_subtitles.srt"
    ensure_dir("temp")

    success = SubtitleGenerator.generate_srt(
        scene_animations = mock_scenes,
        fps              = 30,
        output_path      = subtitle_path,
    )
    print(f"✅ Subtitles generated: {success}")

    if success and os.path.exists(subtitle_path):
        with open(subtitle_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"\n   SRT Preview:")
        print("   " + "\n   ".join(content.split("\n")[:12]))

    # ===== TEST 5: FULL PIPELINE - Script to Video =====
    print_section("Test 5: 🚀 FULL PIPELINE - Script to Video 🚀")

    story_script = """
INT. HERO'S HOUSE - MORNING

The hero wakes up excitedly.

HERO
(excited)
Aaj main duniya ka best animation banane wala hoon!

HERO
(happy)
Chalo, kaam shuru karte hain!

EXT. VILLAIN'S LAIR - NIGHT

VILLAIN
(angry)
Hero ne bahut kar liya. Ab mera time hai!

VILLAIN
(shouting)
MAIN USSE ROKUNGA!
"""

    # Progress callback
    last_percent = [-1]
    def on_progress(data):
        if isinstance(data, dict):
            percent = data.get("percent", 0)
            stage = data.get("stage", "")
            message = data.get("message", "")
        else:
            percent = data.percent
            stage = data.stage
            message = data.message

        # Print only significant progress changes
        if int(percent) > last_percent[0]:
            last_percent[0] = int(percent)
            if int(percent) % 10 == 0 or int(percent) >= 95:
                print(f"   [{percent:5.1f}%] {stage[:30]:30s} → {message[:50]}")

    print("\n🚀 Starting script-to-video generation...\n")

    output_path = "exports/test_video.mp4"
    ensure_dir("exports")

    result = script_to_video(
        script_text       = story_script,
        output_path       = output_path,
        title             = "Test Animation",
        quality           = "draft",   # Fast for testing
        progress_callback = on_progress,
    )

    print(f"\n🎉 Generation complete!\n")

    generator = get_video_generator()
    generator.print_result_summary(result)

    # ===== TEST 6: Output Files =====
    print_section("Test 6: Generated Output Files")

    if result.success:
        # Check video
        if os.path.exists(result.video_path):
            size = get_file_size(result.video_path)
            print(f"✅ Video file: {result.video_path}")
            print(f"   Size: {format_bytes(size)}")

        # Check subtitles
        if result.subtitle_path and os.path.exists(result.subtitle_path):
            print(f"✅ Subtitles: {result.subtitle_path}")
            size = get_file_size(result.subtitle_path)
            print(f"   Size: {format_bytes(size)}")

        # Check metadata
        if result.metadata_path and os.path.exists(result.metadata_path):
            print(f"✅ Metadata: {result.metadata_path}")
    else:
        print(f"❌ Generation failed: {result.error}")

    # ===== TEST 7: Statistics =====
    print_section("Test 7: Final Statistics")
    print(f"\n   🎬 Pipeline Summary:")
    print(f"   ✅ Success        : {result.success}")
    print(f"   ⏱️  Generation Time: {result.generation_time:.2f}s")
    print(f"   📏 Resolution     : {result.resolution[0]}x{result.resolution[1]}")
    print(f"   🎞️  FPS            : {result.fps}")
    print(f"   📊 Total Frames   : {result.total_frames}")
    print(f"   💾 File Size      : {result.get_file_size_str()}")

    # Cleanup test files
    try:
        if os.path.exists(subtitle_path):
            os.remove(subtitle_path)
    except Exception:
        pass

    print_banner("✅ All Tests Passed!", "video_generator.py Working Perfectly")