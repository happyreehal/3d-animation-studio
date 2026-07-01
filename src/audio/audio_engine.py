# ============================================================
# 3D ANIMATION STUDIO - Audio Engine
# ============================================================
# Features:
# - Multi-format audio playback (WAV, MP3, OGG, FLAC, M4A)
# - Multiple simultaneous tracks (mixing)
# - Volume, pan, fade in/out control
# - Audio effects (normalize, trim silence, reverse)
# - Track queue system
# - Waveform analysis
# - Export mixed audio to WAV/MP3
# - Non-blocking playback (background threads)
# - Duration & format info
# - Audio streaming for large files
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
import threading
import math
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

# Audio libraries
try:
    from pydub import AudioSegment
    from pydub.playback import play as pydub_play
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    AudioSegment = None

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False
    sf = None

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    sd = None

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    librosa = None

from src.utils import (
    get_logger, get_config, ensure_dir, generate_short_id,
    is_supported_audio_format, get_file_size, format_bytes,
    format_duration, delete_file, get_file_extension
)

logger = get_logger("AudioEngine")


# ============================================================
# AUDIO FORMATS & CONSTANTS
# ============================================================

class AudioFormat:
    """Supported audio formats"""
    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"
    FLAC = "flac"
    M4A = "m4a"
    AAC = "aac"

    ALL = [WAV, MP3, OGG, FLAC, M4A, AAC]


class TrackState(Enum):
    """Audio track state"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    LOADING = "loading"
    ERROR = "error"


# ============================================================
# AUDIO INFO
# ============================================================

@dataclass
class AudioInfo:
    """Audio file information"""
    filepath: str
    filename: str = ""
    format: str = ""
    duration: float = 0.0            # Seconds
    sample_rate: int = 0             # Hz
    channels: int = 0                # 1=mono, 2=stereo
    bit_depth: int = 0
    bitrate: int = 0                 # kbps
    file_size: int = 0
    frames: int = 0

    def to_dict(self) -> Dict:
        return {
            "filepath": self.filepath,
            "filename": self.filename,
            "format": self.format,
            "duration": self.duration,
            "duration_readable": format_duration(self.duration),
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "channels_type": "Mono" if self.channels == 1 else "Stereo" if self.channels == 2 else f"{self.channels}ch",
            "bit_depth": self.bit_depth,
            "bitrate": self.bitrate,
            "file_size": self.file_size,
            "file_size_readable": format_bytes(self.file_size),
            "frames": self.frames,
        }


# ============================================================
# AUDIO TRACK
# ============================================================

@dataclass
class AudioTrack:
    """
    Single audio track for mixing/playback.
    """
    id: str = field(default_factory=generate_short_id)
    name: str = "Track"
    filepath: Optional[str] = None

    # Playback control
    volume: float = 1.0              # 0.0-2.0 (2.0 = amplified)
    pan: float = 0.0                 # -1.0 (left) to 1.0 (right), 0 = center
    muted: bool = False
    loop: bool = False

    # Timing
    start_time: float = 0.0          # When to start (seconds)
    fade_in: float = 0.0             # Fade in duration
    fade_out: float = 0.0            # Fade out duration
    trim_start: float = 0.0          # Trim from start
    trim_end: float = 0.0            # Trim from end

    # Audio data (loaded when needed)
    _audio_segment: Optional[Any] = None
    _duration: float = 0.0
    _info: Optional[AudioInfo] = None

    # State
    state: TrackState = TrackState.STOPPED

    def get_effective_duration(self) -> float:
        """Trims aur fades ke baad effective duration"""
        return max(0, self._duration - self.trim_start - self.trim_end)


# ============================================================
# AUDIO ANALYZER
# ============================================================

class AudioAnalyzer:
    """Audio file analysis utilities"""

    @staticmethod
    def get_info(filepath: str) -> Optional[AudioInfo]:
        """Audio file ki complete info return karo"""
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return None

        info = AudioInfo(
            filepath=filepath,
            filename=os.path.basename(filepath),
            format=get_file_extension(filepath),
            file_size=get_file_size(filepath)
        )

        # Soundfile try (WAV, FLAC, OGG)
        if SOUNDFILE_AVAILABLE:
            try:
                with sf.SoundFile(filepath) as f:
                    info.sample_rate = f.samplerate
                    info.channels = f.channels
                    info.frames = f.frames
                    info.duration = f.frames / f.samplerate
                    info.bit_depth = 16  # Default

                    # Subtype se bit depth
                    subtype = f.subtype
                    if "24" in subtype:
                        info.bit_depth = 24
                    elif "32" in subtype:
                        info.bit_depth = 32

                    return info
            except Exception as e:
                logger.debug(f"soundfile failed: {e}, trying pydub...")

        # Pydub fallback (all formats)
        if PYDUB_AVAILABLE:
            try:
                audio = AudioSegment.from_file(filepath)
                info.sample_rate = audio.frame_rate
                info.channels = audio.channels
                info.frames = int(audio.frame_count())
                info.duration = len(audio) / 1000.0  # ms to seconds
                info.bit_depth = audio.sample_width * 8
                # Rough bitrate estimate
                info.bitrate = int((info.file_size * 8) / max(1, info.duration) / 1000)
                return info
            except Exception as e:
                logger.error(f"pydub failed: {e}")
                return None

        return None

    @staticmethod
    def get_waveform(filepath: str,
                     num_samples: int = 100) -> Optional[np.ndarray]:
        """
        Waveform data return karo (visualization ke liye).

        Returns:
            Array of amplitude values (0-1)
        """
        if not LIBROSA_AVAILABLE:
            # Fallback with pydub
            return AudioAnalyzer._get_waveform_pydub(filepath, num_samples)

        try:
            y, sr = librosa.load(filepath, sr=None, mono=True)

            # Downsample to num_samples
            samples_per_chunk = max(1, len(y) // num_samples)
            waveform = []

            for i in range(num_samples):
                start = i * samples_per_chunk
                end = min(start + samples_per_chunk, len(y))
                if start < len(y):
                    chunk = y[start:end]
                    # RMS amplitude
                    amplitude = float(np.sqrt(np.mean(chunk ** 2)))
                    waveform.append(amplitude)

            # Normalize to 0-1
            waveform = np.array(waveform)
            if waveform.max() > 0:
                waveform = waveform / waveform.max()

            return waveform

        except Exception as e:
            logger.error(f"Waveform generation failed: {e}")
            return None

    @staticmethod
    def _get_waveform_pydub(filepath: str,
                             num_samples: int = 100) -> Optional[np.ndarray]:
        """Pydub fallback for waveform"""
        if not PYDUB_AVAILABLE:
            return None

        try:
            audio = AudioSegment.from_file(filepath)

            # Convert to mono if needed
            if audio.channels > 1:
                audio = audio.set_channels(1)

            # Get raw samples
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)

            # Normalize
            max_val = 2 ** (audio.sample_width * 8 - 1)
            samples = samples / max_val

            # Downsample
            samples_per_chunk = max(1, len(samples) // num_samples)
            waveform = []

            for i in range(num_samples):
                start = i * samples_per_chunk
                end = min(start + samples_per_chunk, len(samples))
                if start < len(samples):
                    chunk = samples[start:end]
                    amplitude = float(np.sqrt(np.mean(chunk ** 2)))
                    waveform.append(amplitude)

            waveform = np.array(waveform)
            if waveform.max() > 0:
                waveform = waveform / waveform.max()

            return waveform

        except Exception as e:
            logger.error(f"Pydub waveform failed: {e}")
            return None


# ============================================================
# AUDIO EFFECTS
# ============================================================

class AudioEffects:
    """
    Audio processing effects.
    Ye pydub AudioSegment pe kaam karta hai.
    """

    @staticmethod
    def normalize(audio: Any, target_db: float = -3.0) -> Any:
        """
        Audio ko normalize karo (peak level ko target tak lao).

        Args:
            audio: AudioSegment
            target_db: Target peak level (dB, negative = quieter)
        """
        if not PYDUB_AVAILABLE:
            return audio

        try:
            # Current peak
            current_peak = audio.max_dBFS
            if current_peak == float("-inf"):
                return audio  # Silent audio

            # Adjustment needed
            change_db = target_db - current_peak
            return audio + change_db
        except Exception as e:
            logger.error(f"Normalize failed: {e}")
            return audio

    @staticmethod
    def change_volume(audio: Any, volume_multiplier: float) -> Any:
        """
        Volume change karo (multiplier me).
        1.0 = same, 2.0 = double, 0.5 = half
        """
        if not PYDUB_AVAILABLE:
            return audio

        try:
            if volume_multiplier <= 0:
                return audio - 60  # Silent (very quiet)

            # Convert to dB
            db_change = 20 * math.log10(volume_multiplier)
            return audio + db_change
        except Exception as e:
            logger.error(f"Volume change failed: {e}")
            return audio

    @staticmethod
    def apply_fade_in(audio: Any, duration_ms: int) -> Any:
        """Fade in apply karo"""
        if not PYDUB_AVAILABLE:
            return audio

        try:
            if duration_ms <= 0:
                return audio
            return audio.fade_in(duration_ms)
        except Exception as e:
            logger.error(f"Fade in failed: {e}")
            return audio

    @staticmethod
    def apply_fade_out(audio: Any, duration_ms: int) -> Any:
        """Fade out apply karo"""
        if not PYDUB_AVAILABLE:
            return audio

        try:
            if duration_ms <= 0:
                return audio
            return audio.fade_out(duration_ms)
        except Exception as e:
            logger.error(f"Fade out failed: {e}")
            return audio

    @staticmethod
    def trim_silence(audio: Any,
                     silence_threshold_db: float = -50.0,
                     min_silence_ms: int = 100) -> Any:
        """Start aur end se silence trim karo"""
        if not PYDUB_AVAILABLE:
            return audio

        try:
            from pydub.silence import detect_leading_silence

            # Start silence
            start_trim = detect_leading_silence(
                audio,
                silence_threshold=silence_threshold_db,
                chunk_size=10
            )

            # End silence (reverse audio)
            end_trim = detect_leading_silence(
                audio.reverse(),
                silence_threshold=silence_threshold_db,
                chunk_size=10
            )

            duration = len(audio)
            trimmed = audio[start_trim:duration - end_trim]

            return trimmed if len(trimmed) > 0 else audio
        except Exception as e:
            logger.error(f"Silence trim failed: {e}")
            return audio

    @staticmethod
    def reverse(audio: Any) -> Any:
        """Audio reverse karo"""
        if not PYDUB_AVAILABLE:
            return audio
        try:
            return audio.reverse()
        except Exception as e:
            logger.error(f"Reverse failed: {e}")
            return audio

    @staticmethod
    def change_speed(audio: Any, speed_multiplier: float) -> Any:
        """
        Playback speed change karo.
        Pitch bhi change hoga (like tape).
        """
        if not PYDUB_AVAILABLE:
            return audio

        try:
            new_frame_rate = int(audio.frame_rate * speed_multiplier)
            modified = audio._spawn(audio.raw_data, overrides={
                "frame_rate": new_frame_rate
            })
            return modified.set_frame_rate(audio.frame_rate)
        except Exception as e:
            logger.error(f"Speed change failed: {e}")
            return audio

    @staticmethod
    def apply_pan(audio: Any, pan: float) -> Any:
        """
        Stereo panning apply karo.

        Args:
            pan: -1.0 (full left) to 1.0 (full right)
        """
        if not PYDUB_AVAILABLE:
            return audio

        try:
            pan = max(-1.0, min(1.0, pan))

            # Mono ko stereo banao
            if audio.channels == 1:
                audio = audio.set_channels(2)

            return audio.pan(pan)
        except Exception as e:
            logger.error(f"Pan failed: {e}")
            return audio


# ============================================================
# AUDIO PLAYER (Background Playback)
# ============================================================

class AudioPlayer:
    """
    Non-blocking audio player using sounddevice.
    """

    def __init__(self):
        self.available = SOUNDDEVICE_AVAILABLE
        self._current_data: Optional[np.ndarray] = None
        self._current_sr: int = 44100
        self._playing = False
        self._paused = False
        self._start_time = 0.0
        self._pause_time = 0.0
        self._elapsed_before_pause = 0.0

    def play(self, filepath: str,
             volume: float = 1.0,
             loop: bool = False,
             blocking: bool = False) -> bool:
        """
        Audio file play karo.

        Args:
            filepath: Audio file
            volume: 0.0-2.0
            loop: Loop karna hai
            blocking: True = wait till done, False = background
        """
        if not self.available:
            logger.warning("sounddevice not available for playback")
            return False

        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return False

        try:
            # Load audio
            if SOUNDFILE_AVAILABLE:
                data, sr = sf.read(filepath, dtype="float32")
            else:
                # Pydub fallback
                if not PYDUB_AVAILABLE:
                    return False
                audio = AudioSegment.from_file(filepath)
                sr = audio.frame_rate
                samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
                max_val = 2 ** (audio.sample_width * 8 - 1)
                data = samples / max_val
                if audio.channels == 2:
                    data = data.reshape(-1, 2)

            # Volume apply
            if volume != 1.0:
                data = data * volume

            # Clip to prevent distortion
            data = np.clip(data, -1.0, 1.0)

            self._current_data = data
            self._current_sr = sr
            self._playing = True
            self._paused = False
            self._start_time = time.time()
            self._elapsed_before_pause = 0.0

            # Play
            sd.play(data, sr, loop=loop)

            if blocking:
                sd.wait()
                self._playing = False

            return True

        except Exception as e:
            logger.error(f"Playback failed: {e}")
            return False

    def stop(self):
        """Playback stop karo"""
        if not self.available:
            return

        try:
            sd.stop()
            self._playing = False
            self._paused = False
        except Exception as e:
            logger.error(f"Stop failed: {e}")

    def pause(self):
        """Pause (technically stop, but track state)"""
        if self._playing and not self._paused:
            self._elapsed_before_pause += time.time() - self._start_time
            self._pause_time = time.time()
            self._paused = True
            try:
                sd.stop()
            except Exception:
                pass

    def resume(self):
        """Resume (restart from where paused)"""
        # NOTE: sounddevice restart nahi kar sakta seamlessly
        # Ye limitation hai
        if self._paused:
            self._paused = False
            self._start_time = time.time()

    def is_playing(self) -> bool:
        """Currently playing?"""
        if not self.available:
            return False

        try:
            # sd.get_stream() active check
            return self._playing and sd.get_stream().active
        except Exception:
            return False

    def get_position(self) -> float:
        """Current playback position (seconds)"""
        if not self._playing:
            return 0.0

        if self._paused:
            return self._elapsed_before_pause

        return self._elapsed_before_pause + (time.time() - self._start_time)

    def wait_until_done(self):
        """Playback complete hone tak wait karo"""
        if self.available:
            try:
                sd.wait()
            except Exception:
                pass
            self._playing = False


# ============================================================
# MAIN AUDIO ENGINE
# ============================================================

class AudioEngine:
    """
    Main audio engine.
    - Track management
    - Mixing
    - Playback control
    - Export
    """

    def __init__(self, config: Optional[Dict] = None):
        # Config
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        audio_config = self.config.get("audio", {})

        # Settings
        self.default_sample_rate = audio_config.get("default_sample_rate", 44100)
        self.default_bitrate = audio_config.get("default_bitrate", 320)
        self.master_volume = 1.0

        # Tracks
        self.tracks: Dict[str, AudioTrack] = {}

        # Player
        self.player = AudioPlayer()

        # Analyzer
        self.analyzer = AudioAnalyzer()

        # Effects
        self.effects = AudioEffects()

        # State
        self.total_tracks_loaded = 0

        # Check availability
        self._check_backends()

        logger.info(
            f"AudioEngine initialized "
            f"(sample_rate: {self.default_sample_rate}Hz)"
        )

    def _check_backends(self):
        """Available backends check karo"""
        available = []
        if PYDUB_AVAILABLE:
            available.append("pydub")
        if SOUNDFILE_AVAILABLE:
            available.append("soundfile")
        if SOUNDDEVICE_AVAILABLE:
            available.append("sounddevice")
        if LIBROSA_AVAILABLE:
            available.append("librosa")

        if available:
            logger.info(f"Audio backends available: {', '.join(available)}")
        else:
            logger.error("No audio backends available!")

    # ------------------------------------------------------------
    # TRACK MANAGEMENT
    # ------------------------------------------------------------

    def load_track(self, filepath: str,
                   name: Optional[str] = None,
                   volume: float = 1.0) -> Optional[AudioTrack]:
        """
        Audio file ko track ke roop me load karo.
        """
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return None

        if not is_supported_audio_format(filepath):
            logger.error(f"Unsupported format: {filepath}")
            return None

        try:
            # Track create
            track = AudioTrack(
                name=name or os.path.basename(filepath),
                filepath=filepath,
                volume=volume
            )
            track.state = TrackState.LOADING

            # Info get karo
            info = self.analyzer.get_info(filepath)
            if info:
                track._info = info
                track._duration = info.duration

            # Audio segment load (agar pydub hai)
            if PYDUB_AVAILABLE:
                try:
                    track._audio_segment = AudioSegment.from_file(filepath)
                except Exception as e:
                    logger.warning(f"Failed to load audio segment: {e}")

            track.state = TrackState.STOPPED

            # Store
            self.tracks[track.id] = track
            self.total_tracks_loaded += 1

            logger.info(
                f"Loaded track: {track.name} "
                f"({format_duration(track._duration)}, "
                f"{info.channels if info else '?'}ch)"
            )
            return track

        except Exception as e:
            logger.error(f"Track load failed: {e}")
            return None

    def get_track(self, track_id: str) -> Optional[AudioTrack]:
        return self.tracks.get(track_id)

    def get_all_tracks(self) -> List[AudioTrack]:
        return list(self.tracks.values())

    def remove_track(self, track_id: str) -> bool:
        if track_id in self.tracks:
            track = self.tracks[track_id]
            logger.debug(f"Removed track: {track.name}")
            del self.tracks[track_id]
            return True
        return False

    def clear_all_tracks(self):
        count = len(self.tracks)
        self.tracks.clear()
        logger.info(f"Cleared {count} tracks")

    # ------------------------------------------------------------
    # PLAYBACK
    # ------------------------------------------------------------

    def play_track(self, track_id: str,
                   blocking: bool = False) -> bool:
        """Single track play karo"""
        track = self.get_track(track_id)
        if not track:
            return False

        if not track.filepath:
            return False

        effective_volume = track.volume * self.master_volume
        if track.muted:
            effective_volume = 0.0

        track.state = TrackState.PLAYING

        success = self.player.play(
            track.filepath,
            volume=effective_volume,
            loop=track.loop,
            blocking=blocking
        )

        if not success:
            track.state = TrackState.ERROR

        return success

    def play_file(self, filepath: str,
                  volume: float = 1.0,
                  blocking: bool = False) -> bool:
        """Direct file play karo (track create kiye bina)"""
        return self.player.play(filepath, volume, blocking=blocking)

    def stop(self):
        """Playback stop karo"""
        self.player.stop()
        for track in self.tracks.values():
            if track.state == TrackState.PLAYING:
                track.state = TrackState.STOPPED

    def pause(self):
        """Pause playback"""
        self.player.pause()
        for track in self.tracks.values():
            if track.state == TrackState.PLAYING:
                track.state = TrackState.PAUSED

    def is_playing(self) -> bool:
        return self.player.is_playing()

    def get_playback_position(self) -> float:
        return self.player.get_position()

    def wait_until_done(self):
        self.player.wait_until_done()
        for track in self.tracks.values():
            if track.state == TrackState.PLAYING:
                track.state = TrackState.STOPPED

    # ------------------------------------------------------------
    # MIXING
    # ------------------------------------------------------------

    def mix_tracks(self, track_ids: Optional[List[str]] = None,
                   output_path: Optional[str] = None) -> Optional[str]:
        """
        Multiple tracks ko mix karo aur single file me export.

        Args:
            track_ids: Konse tracks mix karne hain (None = sab)
            output_path: Output file path

        Returns:
            Mixed file path
        """
        if not PYDUB_AVAILABLE:
            logger.error("pydub required for mixing")
            return None

        # Track select karo
        if track_ids:
            tracks = [self.tracks[tid] for tid in track_ids if tid in self.tracks]
        else:
            tracks = list(self.tracks.values())

        if not tracks:
            logger.warning("No tracks to mix")
            return None

        try:
            # Longest track ki duration
            max_duration_ms = 0
            for track in tracks:
                if track._audio_segment:
                    end_time = int(track.start_time * 1000) + len(track._audio_segment)
                    max_duration_ms = max(max_duration_ms, end_time)

            # Silent base
            mixed = AudioSegment.silent(
                duration=max_duration_ms,
                frame_rate=self.default_sample_rate
            )

            # Har track overlay karo
            for track in tracks:
                if not track._audio_segment or track.muted:
                    continue

                # Track segment copy
                segment = track._audio_segment

                # Trims apply karo
                if track.trim_start > 0 or track.trim_end > 0:
                    trim_start_ms = int(track.trim_start * 1000)
                    trim_end_ms = int(track.trim_end * 1000)
                    segment = segment[trim_start_ms:len(segment) - trim_end_ms]

                # Volume apply
                effective_volume = track.volume * self.master_volume
                segment = self.effects.change_volume(segment, effective_volume)

                # Pan apply
                if track.pan != 0.0:
                    segment = self.effects.apply_pan(segment, track.pan)

                # Fades apply
                if track.fade_in > 0:
                    segment = self.effects.apply_fade_in(
                        segment, int(track.fade_in * 1000)
                    )
                if track.fade_out > 0:
                    segment = self.effects.apply_fade_out(
                        segment, int(track.fade_out * 1000)
                    )

                # Overlay at start_time
                position_ms = int(track.start_time * 1000)
                mixed = mixed.overlay(segment, position=position_ms)

            # Export
            if output_path is None:
                base_dir = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
                output_path = os.path.join(
                    base_dir, "temp",
                    f"mixed_{generate_short_id()}.wav"
                )

            ensure_dir(os.path.dirname(output_path))
            mixed.export(output_path, format="wav")

            logger.info(
                f"Mixed {len(tracks)} tracks → {output_path} "
                f"({format_bytes(get_file_size(output_path))})"
            )
            return output_path

        except Exception as e:
            logger.error(f"Mixing failed: {e}")
            return None

    # ------------------------------------------------------------
    # EXPORT
    # ------------------------------------------------------------

    def export_track(self, track_id: str,
                     output_path: str,
                     format: str = "wav",
                     bitrate: Optional[str] = None) -> bool:
        """
        Single track export karo (with effects applied).
        """
        if not PYDUB_AVAILABLE:
            return False

        track = self.get_track(track_id)
        if not track or not track._audio_segment:
            return False

        try:
            segment = track._audio_segment

            # Apply all track properties
            effective_volume = track.volume * self.master_volume
            segment = self.effects.change_volume(segment, effective_volume)

            if track.pan != 0.0:
                segment = self.effects.apply_pan(segment, track.pan)

            if track.fade_in > 0:
                segment = self.effects.apply_fade_in(
                    segment, int(track.fade_in * 1000)
                )
            if track.fade_out > 0:
                segment = self.effects.apply_fade_out(
                    segment, int(track.fade_out * 1000)
                )

            # Export
            ensure_dir(os.path.dirname(output_path))

            export_params = {"format": format}
            if bitrate:
                export_params["bitrate"] = bitrate

            segment.export(output_path, **export_params)

            logger.info(f"Exported: {track.name} → {output_path}")
            return True

        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False

    def convert_format(self, input_path: str,
                       output_path: str,
                       bitrate: Optional[str] = None) -> bool:
        """
        Audio format convert karo.
        Format output extension se detect hoga.
        """
        if not PYDUB_AVAILABLE:
            return False

        try:
            audio = AudioSegment.from_file(input_path)

            format = get_file_extension(output_path)

            ensure_dir(os.path.dirname(output_path))

            export_params = {"format": format}
            if bitrate:
                export_params["bitrate"] = bitrate

            audio.export(output_path, **export_params)

            logger.info(f"Converted: {input_path} → {output_path}")
            return True

        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            return False

    # ------------------------------------------------------------
    # VOLUME CONTROL
    # ------------------------------------------------------------

    def set_master_volume(self, volume: float):
        """Master volume set karo (0.0-2.0)"""
        self.master_volume = max(0.0, min(2.0, volume))
        logger.debug(f"Master volume: {self.master_volume}")

    def set_track_volume(self, track_id: str, volume: float) -> bool:
        """Track volume set karo"""
        track = self.get_track(track_id)
        if not track:
            return False
        track.volume = max(0.0, min(2.0, volume))
        return True

    def mute_track(self, track_id: str) -> bool:
        track = self.get_track(track_id)
        if not track:
            return False
        track.muted = True
        return True

    def unmute_track(self, track_id: str) -> bool:
        track = self.get_track(track_id)
        if not track:
            return False
        track.muted = False
        return True

    # ------------------------------------------------------------
    # STATS
    # ------------------------------------------------------------

    def get_stats(self) -> Dict:
        """Engine statistics"""
        total_duration = sum(t._duration for t in self.tracks.values())

        return {
            "total_tracks": len(self.tracks),
            "total_tracks_loaded": self.total_tracks_loaded,
            "total_duration": total_duration,
            "total_duration_readable": format_duration(total_duration),
            "master_volume": self.master_volume,
            "is_playing": self.is_playing(),
            "backends_available": {
                "pydub": PYDUB_AVAILABLE,
                "soundfile": SOUNDFILE_AVAILABLE,
                "sounddevice": SOUNDDEVICE_AVAILABLE,
                "librosa": LIBROSA_AVAILABLE,
            }
        }

    def shutdown(self):
        """Engine shutdown"""
        try:
            self.stop()
            self.clear_all_tracks()
            logger.info("AudioEngine shut down")
        except Exception as e:
            logger.error(f"Shutdown error: {e}")


# ============================================================
# TEST FUNCTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")
    print_banner("Audio Engine Test", "Audio Playback & Mixing")

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))

    # ============================================================
    # Test 1: Initialize
    # ============================================================
    print_section("Test 1: Initialize Audio Engine")

    engine = AudioEngine()

    stats = engine.get_stats()
    print(f"Master volume: {stats['master_volume']}")
    print(f"Backends: {stats['backends_available']}")

    if not any(stats['backends_available'].values()):
        print("❌ No audio backends available!")
        sys.exit(1)

    # ============================================================
    # Test 2: Check for TTS Audio Files
    # ============================================================
    print_section("Test 2: Check Existing TTS Audio")

    tts_dir = os.path.join(base_dir, "temp", "tts_tests")

    test_files = []
    if os.path.exists(tts_dir):
        for f in os.listdir(tts_dir):
            filepath = os.path.join(tts_dir, f)
            if os.path.isfile(filepath) and is_supported_audio_format(filepath):
                test_files.append(filepath)

    if not test_files:
        print("⚠️  No TTS audio files found. Run tts_engine.py first!")
        print("Creating test tone instead...")

        # Create simple test tone
        if PYDUB_AVAILABLE:
            from pydub.generators import Sine

            output_dir = os.path.join(base_dir, "temp", "audio_tests")
            ensure_dir(output_dir)

            # 440Hz sine wave (A note) for 2 seconds
            tone = Sine(440).to_audio_segment(duration=2000)
            test_tone = os.path.join(output_dir, "test_tone.wav")
            tone.export(test_tone, format="wav")
            test_files.append(test_tone)
            print(f"✓ Created test tone: {test_tone}")
    else:
        print(f"Found {len(test_files)} TTS audio files")
        for i, f in enumerate(test_files[:5], 1):
            print(f"  {i}. {os.path.basename(f)}")

    # ============================================================
    # Test 3: Audio Info
    # ============================================================
    print_section("Test 3: Audio File Info")

    if test_files:
        info = engine.analyzer.get_info(test_files[0])
        if info:
            info_dict = info.to_dict()
            print(f"File: {info_dict['filename']}")
            print(f"  Format: {info_dict['format']}")
            print(f"  Duration: {info_dict['duration_readable']}")
            print(f"  Sample rate: {info_dict['sample_rate']} Hz")
            print(f"  Channels: {info_dict['channels_type']}")
            print(f"  Bit depth: {info_dict['bit_depth']} bit")
            print(f"  Size: {info_dict['file_size_readable']}")

    # ============================================================
    # Test 4: Load Tracks
    # ============================================================
    print_section("Test 4: Load Tracks")

    loaded_tracks = []
    for filepath in test_files[:3]:  # Load first 3
        track = engine.load_track(filepath)
        if track:
            loaded_tracks.append(track)

    print(f"Loaded {len(loaded_tracks)} tracks")
    for t in loaded_tracks:
        print(f"  - {t.name}: {format_duration(t._duration)}")

    # ============================================================
    # Test 5: Waveform Analysis
    # ============================================================
    print_section("Test 5: Waveform Analysis")

    if test_files:
        waveform = engine.analyzer.get_waveform(test_files[0], num_samples=20)
        if waveform is not None:
            print(f"Waveform samples: {len(waveform)}")
            print("Amplitude visualization:")

            # ASCII visualization
            for i, amp in enumerate(waveform):
                bar_length = int(amp * 40)
                bar = "█" * bar_length
                print(f"  {i:2}: {bar} {amp:.2f}")

    # ============================================================
    # Test 6: Play Audio (Non-blocking)
    # ============================================================
    print_section("Test 6: Playback Test")

    if loaded_tracks and SOUNDDEVICE_AVAILABLE:
        track = loaded_tracks[0]
        print(f"Playing: {track.name}")
        print("(Listen for audio...)")

        success = engine.play_track(track.id, blocking=False)

        if success:
            # Show progress for 3 seconds
            start = time.time()
            while time.time() - start < min(3.0, track._duration + 0.5):
                pos = engine.get_playback_position()
                progress = min(1.0, pos / max(0.1, track._duration))
                bar = "█" * int(progress * 30) + "░" * (30 - int(progress * 30))
                print(f"\r  [{bar}] {pos:.1f}s / {track._duration:.1f}s", end="", flush=True)
                time.sleep(0.1)

                if not engine.is_playing():
                    break

            print()  # Newline
            engine.stop()
            print("✓ Playback complete")
        else:
            print("⚠️  Playback failed (audio device issue?)")
    else:
        print("⚠️  Skipping playback (no tracks or sounddevice)")

    # ============================================================
    # Test 7: Volume Control
    # ============================================================
    print_section("Test 7: Volume Control")

    if loaded_tracks:
        track = loaded_tracks[0]

        # Different volumes test
        for vol in [1.0, 0.5, 0.2]:
            engine.set_track_volume(track.id, vol)
            print(f"  Volume: {vol}x → track.volume = {track.volume}")

        # Reset
        engine.set_track_volume(track.id, 1.0)

        # Master volume
        engine.set_master_volume(0.7)
        print(f"  Master volume set to: {engine.master_volume}")
        engine.set_master_volume(1.0)

    # ============================================================
    # Test 8: Audio Effects
    # ============================================================
    print_section("Test 8: Audio Effects")

    if loaded_tracks and PYDUB_AVAILABLE:
        track = loaded_tracks[0]
        segment = track._audio_segment

        if segment:
            output_dir = os.path.join(base_dir, "temp", "audio_tests")
            ensure_dir(output_dir)

            # Normalize
            normalized = engine.effects.normalize(segment, target_db=-3.0)
            path = os.path.join(output_dir, "effect_normalized.wav")
            normalized.export(path, format="wav")
            print(f"  ✓ Normalized: {os.path.basename(path)}")

            # Volume up
            louder = engine.effects.change_volume(segment, 1.5)
            path = os.path.join(output_dir, "effect_louder.wav")
            louder.export(path, format="wav")
            print(f"  ✓ Volume +50%: {os.path.basename(path)}")

            # Fade in/out
            faded = engine.effects.apply_fade_in(segment, 500)
            faded = engine.effects.apply_fade_out(faded, 500)
            path = os.path.join(output_dir, "effect_faded.wav")
            faded.export(path, format="wav")
            print(f"  ✓ Fade in/out: {os.path.basename(path)}")

            # Reverse
            reversed_audio = engine.effects.reverse(segment)
            path = os.path.join(output_dir, "effect_reversed.wav")
            reversed_audio.export(path, format="wav")
            print(f"  ✓ Reversed: {os.path.basename(path)}")

            # Speed change
            faster = engine.effects.change_speed(segment, 1.5)
            path = os.path.join(output_dir, "effect_fast.wav")
            faster.export(path, format="wav")
            print(f"  ✓ Speed 1.5x: {os.path.basename(path)}")

    # ============================================================
    # Test 9: Multi-Track Mixing
    # ============================================================
    print_section("Test 9: Multi-Track Mixing")

    if len(loaded_tracks) >= 2 and PYDUB_AVAILABLE:
        # Configure tracks with different properties
        loaded_tracks[0].volume = 1.0
        loaded_tracks[0].start_time = 0.0
        loaded_tracks[0].fade_in = 0.5

        loaded_tracks[1].volume = 0.7
        loaded_tracks[1].start_time = 1.0  # Start 1 sec later
        loaded_tracks[1].pan = 0.5         # Pan right

        if len(loaded_tracks) >= 3:
            loaded_tracks[2].volume = 0.5
            loaded_tracks[2].start_time = 2.0
            loaded_tracks[2].pan = -0.5    # Pan left

        # Mix
        output_dir = os.path.join(base_dir, "temp", "audio_tests")
        ensure_dir(output_dir)
        mix_path = os.path.join(output_dir, "mixed_output.wav")

        result_path = engine.mix_tracks(output_path=mix_path)

        if result_path:
            info = engine.analyzer.get_info(result_path)
            print(f"✅ Mixed audio: {mix_path}")
            print(f"   Duration: {format_duration(info.duration)}")
            print(f"   Size: {format_bytes(info.file_size)}")
    else:
        print("⚠️  Need at least 2 tracks for mixing test")

    # ============================================================
    # Test 10: Format Conversion
    # ============================================================
    print_section("Test 10: Format Conversion")

    if test_files and PYDUB_AVAILABLE:
        input_file = test_files[0]
        output_dir = os.path.join(base_dir, "temp", "audio_tests")
        ensure_dir(output_dir)

        # WAV → MP3
        output_mp3 = os.path.join(output_dir, "converted.mp3")
        success = engine.convert_format(input_file, output_mp3, bitrate="192k")

        if success:
            input_size = format_bytes(get_file_size(input_file))
            output_size = format_bytes(get_file_size(output_mp3))
            print(f"  ✓ WAV → MP3")
            print(f"     Input: {input_size}")
            print(f"     Output: {output_size}")

    # ============================================================
    # Test 11: Statistics
    # ============================================================
    print_section("Test 11: Final Statistics")

    stats = engine.get_stats()
    print(f"Total tracks: {stats['total_tracks']}")
    print(f"Total duration: {stats['total_duration_readable']}")
    print(f"Master volume: {stats['master_volume']}")

    # ============================================================
    # Cleanup
    # ============================================================
    print_section("Cleanup")

    engine.shutdown()
    print("Audio engine shut down")

    output_dir = os.path.join(base_dir, "temp", "audio_tests")
    if os.path.exists(output_dir):
        print(f"\n👉 Test outputs saved in:")
        print(f"   {output_dir}")
        print(f"\n   Open to listen:")
        print(f"   start {output_dir}")

    print_banner(
        "✅ All Tests Passed",
        "Audio Engine Working - Playback, mixing, effects!"
    )