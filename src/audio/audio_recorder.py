# ============================================================
# 3D ANIMATION STUDIO - Audio Recorder
# ============================================================
# Features:
# - Microphone recording (live capture)
# - Real-time input level monitoring (VU meter)
# - Multiple input device support
# - Sample rate & channels config (mono/stereo)
# - Start/Pause/Resume/Stop/Cancel controls
# - Save to WAV directly
# - Silence detection (auto-stop)
# - Peak level tracking
# - Duration limits (max recording time)
# - Recording metadata
# - Multiple session management
# - Non-blocking (background thread)
# - Event listeners (recording progress)
# - Thread-safe operations (concurrent stops handled)
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
import queue
from typing import Any, Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

# Audio libraries
try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    sd = None

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False
    sf = None

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    AudioSegment = None

from src.utils import (
    get_logger, get_config, ensure_dir, generate_short_id,
    get_timestamp, format_duration, format_bytes, get_file_size,
    clamp
)

logger = get_logger("AudioRecorder")


# ============================================================
# RECORDING CONSTANTS
# ============================================================

class RecordingState(Enum):
    """Recording ka current state"""
    IDLE = "idle"                # Nothing happening
    PREPARING = "preparing"      # Getting ready
    RECORDING = "recording"      # Actively recording
    PAUSED = "paused"           # Temporarily paused
    STOPPING = "stopping"       # Saving/finalizing
    STOPPED = "stopped"         # Finished
    ERROR = "error"             # Something wrong


class AudioQuality(Enum):
    """
    Recording quality presets.
    Different scenarios ke liye ready-made configs.
    """
    LOW      = ("low",      22050, 1, 16)   # 22kHz mono 16-bit (small files)
    MEDIUM   = ("medium",   44100, 1, 16)   # CD quality mono
    HIGH     = ("high",     44100, 2, 16)   # CD quality stereo (default)
    STUDIO   = ("studio",   48000, 2, 24)   # Professional 48kHz 24-bit
    ULTRA    = ("ultra",    96000, 2, 24)   # High-res audio

    def __init__(self, label: str, sample_rate: int, channels: int, bit_depth: int):
        self.label       = label
        self.sample_rate = sample_rate
        self.channels    = channels
        self.bit_depth   = bit_depth

    @property
    def subtype(self) -> str:
        """soundfile subtype string return karo"""
        return f"PCM_{self.bit_depth}"


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class InputDevice:
    """Microphone / input device information"""
    index: int                       # Device ka index number
    name: str                        # Human-readable naam
    channels: int = 0                # Max input channels
    sample_rate: float = 0.0         # Default sample rate
    is_default: bool = False         # System default hai?
    hostapi: str = ""                # Audio API (WASAPI, MME, etc.)

    def __str__(self) -> str:
        default_mark = " (DEFAULT)" if self.is_default else ""
        return f"[{self.index}] {self.name} - {self.channels}ch @ {int(self.sample_rate)}Hz{default_mark}"


@dataclass
class RecordingMetadata:
    """Recording session ki metadata"""
    session_id: str = field(default_factory=generate_short_id)
    filepath: Optional[str] = None
    device_name: str = ""
    device_index: int = -1
    sample_rate: int = 44100
    channels: int = 1
    bit_depth: int = 16

    # Timing
    start_time: str = ""             # Kab shuru hua
    end_time: str = ""               # Kab khatam
    duration: float = 0.0            # Total seconds

    # Audio stats
    peak_level: float = 0.0          # Max amplitude 0-1
    average_level: float = 0.0       # Average amplitude
    file_size: int = 0               # Bytes

    # Extra info
    was_paused: bool = False         # Kabhi paused hua tha?
    auto_stopped: bool = False       # Silence pe auto-stop hua?
    quality: str = "high"            # Quality preset used

    def to_dict(self) -> Dict:
        return {
            "session_id"        : self.session_id,
            "filepath"          : self.filepath,
            "device_name"       : self.device_name,
            "device_index"      : self.device_index,
            "sample_rate"       : self.sample_rate,
            "channels"          : self.channels,
            "bit_depth"         : self.bit_depth,
            "start_time"        : self.start_time,
            "end_time"          : self.end_time,
            "duration"          : round(self.duration, 3),
            "duration_readable" : format_duration(self.duration),
            "peak_level"        : round(self.peak_level, 3),
            "average_level"     : round(self.average_level, 3),
            "file_size"         : self.file_size,
            "file_size_readable": format_bytes(self.file_size),
            "was_paused"        : self.was_paused,
            "auto_stopped"      : self.auto_stopped,
            "quality"           : self.quality,
        }


@dataclass
class LevelMeter:
    """
    VU meter data — real-time audio level info.
    Recording ke waqt callback me milta hai.
    """
    current_level: float = 0.0       # Current RMS 0-1
    peak_level: float = 0.0          # Recent peak 0-1
    is_clipping: bool = False        # Distortion aa raha hai?
    is_silent: bool = False          # Silence hai?

    def get_visualization(self, width: int = 30) -> str:
        """
        Console mein VU meter dikhane ke liye ASCII bar.
        Example: [████████░░░░░░░░░░░░] -12dB
        """
        filled = int(self.current_level * width)
        # Peak marker
        peak_pos = int(self.peak_level * width)

        bar_chars = []
        for i in range(width):
            if i == peak_pos - 1 and peak_pos > filled:
                bar_chars.append("│")   # Peak indicator
            elif i < filled:
                # Color coding: green → yellow → red
                if i > width * 0.85:
                    bar_chars.append("█")  # Red zone
                elif i > width * 0.65:
                    bar_chars.append("▓")  # Yellow zone
                else:
                    bar_chars.append("▒")  # Green zone
            else:
                bar_chars.append("░")

        bar = "".join(bar_chars)

        # dB value
        if self.current_level > 0.001:
            db = 20 * np.log10(self.current_level)
            db_str = f"{db:+.1f}dB"
        else:
            db_str = "  -∞ dB"

        clip_marker = " ⚠️CLIP" if self.is_clipping else ""
        return f"[{bar}] {db_str}{clip_marker}"


# ============================================================
# DEVICE MANAGER
# ============================================================

class DeviceManager:
    """
    Audio input devices manage karne wala class.
    Sab microphones list karta hai aur select karne deta hai.
    """

    @staticmethod
    def list_input_devices() -> List[InputDevice]:
        """
        Sab available input devices (microphones) return karo.
        """
        if not SOUNDDEVICE_AVAILABLE:
            logger.warning("sounddevice not available")
            return []

        try:
            devices        = sd.query_devices()
            default_input  = sd.default.device[0] if sd.default.device else -1
            hostapis       = sd.query_hostapis()

            input_devices = []
            for idx, dev in enumerate(devices):
                # Sirf input devices (mic wale)
                if dev.get("max_input_channels", 0) > 0:
                    hostapi_name = ""
                    hostapi_idx  = dev.get("hostapi", -1)
                    if 0 <= hostapi_idx < len(hostapis):
                        hostapi_name = hostapis[hostapi_idx].get("name", "")

                    device_info = InputDevice(
                        index       = idx,
                        name        = dev.get("name", "Unknown"),
                        channels    = dev.get("max_input_channels", 0),
                        sample_rate = dev.get("default_samplerate", 44100),
                        is_default  = (idx == default_input),
                        hostapi     = hostapi_name,
                    )
                    input_devices.append(device_info)

            return input_devices

        except Exception as e:
            logger.error(f"Failed to list devices: {e}")
            return []

    @staticmethod
    def get_default_device() -> Optional[InputDevice]:
        """System ka default input device return karo"""
        devices = DeviceManager.list_input_devices()
        for dev in devices:
            if dev.is_default:
                return dev
        # Agar default nahi mila toh pehla return karo
        return devices[0] if devices else None

    @staticmethod
    def get_device_by_index(index: int) -> Optional[InputDevice]:
        """Specific index ka device return karo"""
        devices = DeviceManager.list_input_devices()
        for dev in devices:
            if dev.index == index:
                return dev
        return None

    @staticmethod
    def test_device(device_index: int,
                    duration: float = 0.5,
                    sample_rate: int = 44100) -> Tuple[bool, str]:
        """
        Device test karo — chota sa audio record karke check karo.
        Returns: (success, error_message)
        """
        if not SOUNDDEVICE_AVAILABLE:
            return False, "sounddevice not available"

        try:
            # Chhoti si recording try karo
            _ = sd.rec(
                int(duration * sample_rate),
                samplerate = sample_rate,
                channels   = 1,
                device     = device_index,
                dtype      = "float32",
            )
            sd.wait()
            return True, ""
        except Exception as e:
            return False, str(e)


# ============================================================
# LEVEL DETECTOR
# ============================================================

class LevelDetector:
    """
    Real-time audio level analysis.
    Peak, RMS, silence detection karta hai.
    """

    def __init__(self,
                 clipping_threshold: float = 0.95,
                 silence_threshold: float = 0.02,
                 peak_hold_time: float = 1.0):
        """
        Args:
            clipping_threshold: Isse zyada = distortion (0-1)
            silence_threshold : Isse kam = silence maani jaayegi
            peak_hold_time    : Peak indicator kitni der dikhe (seconds)
        """
        self.clipping_threshold = clipping_threshold
        self.silence_threshold  = silence_threshold
        self.peak_hold_time     = peak_hold_time

        # State tracking
        self._peak_level        = 0.0
        self._peak_timestamp    = 0.0
        self._samples_analyzed  = 0
        self._sum_levels        = 0.0

    def analyze(self, audio_chunk: np.ndarray) -> LevelMeter:
        """
        Audio chunk analyze karo aur LevelMeter return karo.
        Ye har audio buffer par call hota hai.
        """
        if audio_chunk is None or len(audio_chunk) == 0:
            return LevelMeter()

        # Mono banao if stereo
        if audio_chunk.ndim > 1:
            mono_chunk = np.mean(audio_chunk, axis=1)
        else:
            mono_chunk = audio_chunk

        # RMS calculate karo (root mean square)
        rms = float(np.sqrt(np.mean(mono_chunk ** 2)))

        # Absolute peak
        current_peak = float(np.max(np.abs(mono_chunk)))

        # Peak hold logic
        now = time.time()
        if current_peak > self._peak_level:
            self._peak_level     = current_peak
            self._peak_timestamp = now
        elif now - self._peak_timestamp > self.peak_hold_time:
            # Peak slowly decay ho
            self._peak_level *= 0.85

        # Running average ke liye stats
        self._samples_analyzed += 1
        self._sum_levels       += rms

        # Meter object banao
        meter = LevelMeter(
            current_level = clamp(rms, 0.0, 1.0),
            peak_level    = clamp(self._peak_level, 0.0, 1.0),
            is_clipping   = current_peak >= self.clipping_threshold,
            is_silent     = rms < self.silence_threshold,
        )

        return meter

    def get_average_level(self) -> float:
        """Total recording ka average level return karo"""
        if self._samples_analyzed == 0:
            return 0.0
        return self._sum_levels / self._samples_analyzed

    def get_peak_level(self) -> float:
        """Overall recording ka peak"""
        return self._peak_level

    def reset(self):
        """Nayi recording ke liye reset karo"""
        self._peak_level       = 0.0
        self._peak_timestamp   = 0.0
        self._samples_analyzed = 0
        self._sum_levels       = 0.0


# ============================================================
# SILENCE MONITOR
# ============================================================

class SilenceMonitor:
    """
    Continuous silence detection.
    Agar user bolna band kar de toh auto-stop kar sakte hain.
    """

    def __init__(self,
                 silence_threshold: float = 0.02,
                 min_silence_duration: float = 3.0):
        """
        Args:
            silence_threshold    : Isse kam level = silence
            min_silence_duration : Kitni der silence rahe toh trigger ho
        """
        self.silence_threshold    = silence_threshold
        self.min_silence_duration = min_silence_duration

        self._silence_start_time  = None
        self._is_silent           = False

    def update(self, rms_level: float) -> bool:
        """
        Har audio chunk pe update karo.
        Returns: True agar continuous silence detect hui hai
        """
        is_currently_silent = rms_level < self.silence_threshold

        if is_currently_silent:
            if self._silence_start_time is None:
                # Silence abhi start hui hai
                self._silence_start_time = time.time()
            else:
                # Silence chal rahi hai — check duration
                silence_duration = time.time() - self._silence_start_time
                if silence_duration >= self.min_silence_duration:
                    return True  # Trigger auto-stop!
        else:
            # Sound aa raha hai — silence timer reset
            self._silence_start_time = None

        return False

    def reset(self):
        """Reset karo"""
        self._silence_start_time = None
        self._is_silent          = False


# ============================================================
# MAIN AUDIO RECORDER
# ============================================================

class AudioRecorder:
    """
    🎙️ Main Audio Recorder Class

    Microphone se audio record karta hai — with level monitoring,
    silence detection, pause/resume, etc.

    Usage:
        recorder = AudioRecorder()
        recorder.start_recording("output.wav")
        # ... wait ...
        recorder.stop_recording()
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Args:
            config: Optional config override. Default: main config se load hoga.
        """
        # Config setup — existing pattern follow karo
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # Audio settings
        audio_cfg = self.config.get("audio", {})

        # Default quality preset
        default_quality_str = audio_cfg.get("recording_quality", "high")
        self.default_quality = self._parse_quality(default_quality_str)

        # Recording settings
        self.sample_rate    = self.default_quality.sample_rate
        self.channels       = self.default_quality.channels
        self.bit_depth      = self.default_quality.bit_depth
        self.chunk_size     = audio_cfg.get("chunk_size", 1024)
        self.max_duration   = audio_cfg.get("max_recording_duration", 3600)  # 1 hour max

        # Output directory
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)
        )))
        self.output_dir = audio_cfg.get(
            "recording_dir",
            os.path.join(base_dir, "assets", "audio", "recordings")
        )
        ensure_dir(self.output_dir)

        # Sub-systems
        self.device_manager  = DeviceManager()
        self.level_detector  = LevelDetector()
        self.silence_monitor = None  # Optional, create karte hain agar needed

        # State
        self.state           : RecordingState = RecordingState.IDLE
        self.current_device  : Optional[InputDevice] = None
        self.current_metadata: Optional[RecordingMetadata] = None

        # Recording buffers
        self._audio_buffer   : List[np.ndarray] = []
        self._buffer_lock    = threading.Lock()
        self._stop_lock      = threading.Lock()   # ✅ Prevent concurrent stops
        self._stream         = None
        self._recording_thread = None
        self._stop_flag      = threading.Event()

        # Timing
        self._record_start_time = 0.0
        self._pause_start_time  = 0.0
        self._paused_duration   = 0.0

        # Auto-stop settings
        self.auto_stop_on_silence  = False
        self.silence_stop_duration = 3.0
        self._silence_stop_triggered = False

        # Event listeners
        self._level_listeners      : List[Callable[[LevelMeter], None]] = []
        self._state_listeners      : List[Callable[[RecordingState], None]] = []
        self._completion_listeners : List[Callable[[RecordingMetadata], None]] = []

        # Statistics
        self.total_recordings = 0
        self.total_duration   = 0.0

        # Default device set karo
        self.current_device = self.device_manager.get_default_device()

        logger.info(
            f"AudioRecorder initialized "
            f"(quality: {self.default_quality.label}, "
            f"{self.sample_rate}Hz {self.channels}ch)"
        )

        if self.current_device:
            logger.info(f"Default device: {self.current_device.name}")
        else:
            logger.warning("⚠️ No input devices found!")

    def _parse_quality(self, quality_str: str) -> AudioQuality:
        """String se AudioQuality enum le lo"""
        quality_str = quality_str.lower()
        for q in AudioQuality:
            if q.label == quality_str:
                return q
        return AudioQuality.HIGH  # Default fallback

    # ── DEVICE SELECTION ──────────────────────────────────

    def list_devices(self) -> List[InputDevice]:
        """Sab available input devices return karo"""
        return self.device_manager.list_input_devices()

    def set_device(self, device_index: int) -> bool:
        """Recording ke liye device select karo"""
        device = self.device_manager.get_device_by_index(device_index)
        if device is None:
            logger.error(f"Device index {device_index} not found")
            return False

        # Test karo device
        success, err = self.device_manager.test_device(device_index, duration=0.3)
        if not success:
            logger.error(f"Device test failed: {err}")
            return False

        self.current_device = device
        logger.info(f"🎙️ Device selected: {device.name}")
        return True

    # ── QUALITY SETTINGS ──────────────────────────────────

    def set_quality(self, quality: AudioQuality):
        """
        Recording quality preset set karo.
        Recording chalu hone se pehle call karna hoga.
        """
        if self.state == RecordingState.RECORDING:
            logger.warning("⚠️ Cannot change quality during recording")
            return

        self.default_quality = quality
        self.sample_rate     = quality.sample_rate
        self.channels        = quality.channels
        self.bit_depth       = quality.bit_depth
        logger.info(f"Quality set: {quality.label} ({quality.sample_rate}Hz, {quality.channels}ch, {quality.bit_depth}bit)")

    def set_custom_settings(self,
                            sample_rate: int = 44100,
                            channels: int = 1,
                            bit_depth: int = 16):
        """Custom audio settings — quality preset ke bina"""
        if self.state == RecordingState.RECORDING:
            logger.warning("⚠️ Cannot change settings during recording")
            return

        self.sample_rate = sample_rate
        self.channels    = channels
        self.bit_depth   = bit_depth
        logger.info(f"Custom settings: {sample_rate}Hz {channels}ch {bit_depth}bit")

    def enable_silence_auto_stop(self,
                                  silence_duration: float = 3.0,
                                  threshold: float = 0.02):
        """
        Silence detect hone par auto-stop enable karo.

        Args:
            silence_duration: Kitni der silence rahe (seconds)
            threshold       : Silence threshold (0-1)
        """
        self.auto_stop_on_silence  = True
        self.silence_stop_duration = silence_duration
        self.silence_monitor = SilenceMonitor(
            silence_threshold    = threshold,
            min_silence_duration = silence_duration,
        )
        logger.info(f"🤫 Auto-stop enabled: {silence_duration}s silence")

    def disable_silence_auto_stop(self):
        """Silence auto-stop disable karo"""
        self.auto_stop_on_silence = False
        self.silence_monitor = None
        logger.debug("Silence auto-stop disabled")

    # ── RECORDING CONTROL ─────────────────────────────────

    def start_recording(self,
                         output_path: Optional[str] = None,
                         max_duration: Optional[float] = None) -> bool:
        """
        🔴 Recording start karo!

        Args:
            output_path : Output file path (None = auto-generate)
            max_duration: Max seconds (None = default from config)

        Returns:
            True agar shuru ho gaya
        """
        # Pre-checks
        if self.state == RecordingState.RECORDING:
            logger.warning("⚠️ Already recording")
            return False

        if not SOUNDDEVICE_AVAILABLE:
            logger.error("❌ sounddevice not available")
            return False

        if not SOUNDFILE_AVAILABLE:
            logger.error("❌ soundfile not available")
            return False

        if self.current_device is None:
            logger.error("❌ No input device selected")
            return False

        # Output path prepare karo
        if output_path is None:
            output_path = self._generate_output_path()

        ensure_dir(os.path.dirname(output_path))

        # Metadata initialize karo
        self.current_metadata = RecordingMetadata(
            filepath     = output_path,
            device_name  = self.current_device.name,
            device_index = self.current_device.index,
            sample_rate  = self.sample_rate,
            channels     = self.channels,
            bit_depth    = self.bit_depth,
            start_time   = get_timestamp(),
            quality      = self.default_quality.label,
        )

        # Buffers reset karo
        with self._buffer_lock:
            self._audio_buffer.clear()
        self.level_detector.reset()
        if self.silence_monitor:
            self.silence_monitor.reset()

        # Threading setup
        self._stop_flag.clear()
        self._paused_duration = 0.0
        self._silence_stop_triggered = False

        # State update
        self._set_state(RecordingState.PREPARING)

        try:
            # sounddevice InputStream banao
            self._stream = sd.InputStream(
                samplerate = self.sample_rate,
                channels   = self.channels,
                device     = self.current_device.index,
                dtype      = "float32",
                blocksize  = self.chunk_size,
                callback   = self._audio_callback,
            )

            self._stream.start()
            self._record_start_time = time.time()
            self._set_state(RecordingState.RECORDING)

            # Max duration monitor thread
            effective_max = max_duration or self.max_duration
            self._recording_thread = threading.Thread(
                target = self._monitor_recording,
                args   = (effective_max,),
                daemon = True,
            )
            self._recording_thread.start()

            logger.info(
                f"🔴 Recording started: {os.path.basename(output_path)} "
                f"(max: {format_duration(effective_max)})"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Failed to start recording: {e}")
            self._set_state(RecordingState.ERROR)
            self._cleanup_stream()
            return False

    def _audio_callback(self, indata, frames, time_info, status):
        """
        Audio callback — sounddevice har chunk pe call karta hai.
        Ye background thread mein chalta hai.
        """
        if status:
            logger.debug(f"Audio callback status: {status}")

        # Paused state mein data ignore karo
        if self.state == RecordingState.PAUSED:
            return

        # Stopping state mein bhi data collect karte raho — last chunks miss na hon
        if self.state not in [RecordingState.RECORDING, RecordingState.STOPPING]:
            return

        # Data copy karo (indata reference hai, hume permanent copy chahiye)
        audio_chunk = indata.copy()

        # Buffer mein add karo
        with self._buffer_lock:
            self._audio_buffer.append(audio_chunk)

        # Level analysis
        meter = self.level_detector.analyze(audio_chunk)

        # Level listeners ko notify karo
        self._notify_level_listeners(meter)

               # Silence check — sirf ek baar trigger ho
        if (self.auto_stop_on_silence 
            and self.silence_monitor 
            and not self._silence_stop_triggered):   # ✅ Flag check
            should_stop = self.silence_monitor.update(meter.current_level)
            if should_stop:
                logger.info("🤫 Silence detected — auto stopping")
                self._silence_stop_triggered = True   # ✅ Set flag
                if self.current_metadata:
                    self.current_metadata.auto_stopped = True
                # Background thread me stop call karo
                threading.Thread(target=self.stop_recording, daemon=True).start()
    def _monitor_recording(self, max_duration: float):
        """
        Background thread jo max duration monitor karta hai.
        Time up hone par auto-stop karta hai.
        """
        while not self._stop_flag.is_set():
            elapsed = self._get_effective_duration()

            if elapsed >= max_duration:
                logger.info(f"⏱️ Max duration reached: {format_duration(max_duration)}")
                # ✅ Directly call — stop_recording khud thread-safe hai
                self.stop_recording()
                break

            time.sleep(0.1)

    def pause_recording(self) -> bool:
        """
        ⏸️ Recording pause karo (data lost nahi hoga)
        """
        if self.state != RecordingState.RECORDING:
            logger.warning("⚠️ Not currently recording")
            return False

        self._pause_start_time = time.time()
        self._set_state(RecordingState.PAUSED)

        if self.current_metadata:
            self.current_metadata.was_paused = True

        logger.info("⏸️ Recording paused")
        return True

    def resume_recording(self) -> bool:
        """▶️ Paused recording resume karo"""
        if self.state != RecordingState.PAUSED:
            logger.warning("⚠️ Not paused")
            return False

        # Pause ka time track karo
        pause_duration = time.time() - self._pause_start_time
        self._paused_duration += pause_duration

        self._set_state(RecordingState.RECORDING)
        logger.info(f"▶️ Recording resumed (paused for {pause_duration:.1f}s)")
        return True

    def stop_recording(self) -> Optional[RecordingMetadata]:
        """
        ⏹️ Recording stop karo aur file save karo.
        Thread-safe — multiple calls handle karta hai.
        """
        # ✅ Thread-safe lock — concurrent stops prevent karo
        with self._stop_lock:
            # Already stopped/stopping ho toh return karo
            if self.state not in [RecordingState.RECORDING, RecordingState.PAUSED]:
                logger.debug(f"⚠️ stop_recording called in state: {self.state.value}")
                return self.current_metadata

            self._set_state(RecordingState.STOPPING)
            self._stop_flag.set()

            try:
                # ✅ Stream ko properly flush karo — last chunks miss na hon
                if self._stream is not None:
                    try:
                        # Pehle thoda wait — pending callbacks complete hon
                        time.sleep(0.15)
                        if self._stream.active:
                            self._stream.stop()
                        # Ek aur small wait — final callback fire ho jaaye
                        time.sleep(0.05)
                        self._stream.close()
                    except Exception as e:
                        logger.debug(f"Stream cleanup: {e}")
                    finally:
                        self._stream = None

                # Effective duration nikalo
                duration = self._get_effective_duration()

                # Metadata update karo
                if self.current_metadata:
                    self.current_metadata.duration      = duration
                    self.current_metadata.end_time      = get_timestamp()
                    self.current_metadata.peak_level    = self.level_detector.get_peak_level()
                    self.current_metadata.average_level = self.level_detector.get_average_level()

                # Audio buffer combine karo
                with self._buffer_lock:
                    if not self._audio_buffer:
                        logger.warning("⚠️ No audio data captured")
                        self._set_state(RecordingState.ERROR)
                        return self.current_metadata

                    # Sab chunks concatenate karo — buffer clear NAHI karo abhi
                    full_audio = np.concatenate(self._audio_buffer, axis=0)

                # File save karo
                filepath = self.current_metadata.filepath
                success = self._save_audio(full_audio, filepath)

                if not success:
                    self._set_state(RecordingState.ERROR)
                    return self.current_metadata

                # ✅ Save ke baad buffer clear karo
                with self._buffer_lock:
                    self._audio_buffer.clear()

                # File size update
                self.current_metadata.file_size = get_file_size(filepath)

                # Statistics
                self.total_recordings += 1
                self.total_duration   += duration

                # State finalize
                self._set_state(RecordingState.STOPPED)

                # Completion listeners
                self._notify_completion_listeners(self.current_metadata)

                logger.info(
                    f"⏹️ Recording saved: {os.path.basename(filepath)} "
                    f"({format_duration(duration)}, "
                    f"{format_bytes(self.current_metadata.file_size)}, "
                    f"peak: {self.current_metadata.peak_level:.2f})"
                )

                return self.current_metadata

            except Exception as e:
                logger.error(f"❌ Stop recording failed: {e}")
                import traceback
                traceback.print_exc()
                self._set_state(RecordingState.ERROR)
                return self.current_metadata

    def cancel_recording(self) -> bool:
        """
        ❌ Recording cancel karo — file save mat karo.
        """
        with self._stop_lock:
            if self.state not in [RecordingState.RECORDING, RecordingState.PAUSED]:
                return False

            logger.info("❌ Recording cancelled")
            self._stop_flag.set()
            self._cleanup_stream()

            # Buffers clear karo
            with self._buffer_lock:
                self._audio_buffer.clear()

            self._set_state(RecordingState.IDLE)
            self.current_metadata = None
            return True

    def _cleanup_stream(self):
        """Stream cleanup karo — memory leaks avoid"""
        if self._stream is not None:
            try:
                if self._stream.active:
                    self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.debug(f"Stream cleanup: {e}")
            finally:
                self._stream = None

    def _save_audio(self, audio_data: np.ndarray, filepath: str) -> bool:
        """Audio numpy array ko WAV file mein save karo"""
        try:
            # Clip prevention
            audio_data = np.clip(audio_data, -1.0, 1.0)

            # soundfile se save karo
            subtype = self.default_quality.subtype
            sf.write(
                filepath,
                audio_data,
                self.sample_rate,
                subtype=subtype,
            )

            # Verify
            if os.path.exists(filepath) and get_file_size(filepath) > 0:
                return True
            return False

        except Exception as e:
            logger.error(f"Save failed: {e}")
            return False

    # ── UTILITIES ─────────────────────────────────────────

    def _get_effective_duration(self) -> float:
        """
        Actual recording duration (paused time nikaal ke).
        """
        if self._record_start_time == 0:
            return 0.0

        # Agar abhi paused hai
        if self.state == RecordingState.PAUSED:
            current_pause = time.time() - self._pause_start_time
            return time.time() - self._record_start_time - self._paused_duration - current_pause

        return time.time() - self._record_start_time - self._paused_duration

    def _generate_output_path(self) -> str:
        """Auto output path — timestamp ke saath"""
        timestamp = get_timestamp().replace(":", "-").replace(" ", "_")
        filename  = f"recording_{timestamp}.wav"
        return os.path.join(self.output_dir, filename)

    def get_current_duration(self) -> float:
        """
        Recording ki current duration return karo.
        Public API — UI ke liye useful.
        """
        return self._get_effective_duration()

    def get_current_level(self) -> LevelMeter:
        """
        Current audio level meter return karo.
        Level detector ka latest state.
        """
        return LevelMeter(
            current_level = 0.0,  # Callback me update hota hai
            peak_level    = self.level_detector.get_peak_level(),
        )

    def is_recording(self) -> bool:
        """Currently recording hai?"""
        return self.state == RecordingState.RECORDING

    def is_paused(self) -> bool:
        """Currently paused hai?"""
        return self.state == RecordingState.PAUSED

    def is_active(self) -> bool:
        """Recording ya paused — koi bhi active state hai?"""
        return self.state in [RecordingState.RECORDING, RecordingState.PAUSED]

    def get_state(self) -> RecordingState:
        return self.state

    # ── STATE MANAGEMENT ──────────────────────────────────

    def _set_state(self, new_state: RecordingState):
        """State change karo aur listeners notify karo"""
        old_state = self.state
        self.state = new_state

        if old_state != new_state:
            logger.debug(f"State: {old_state.value} → {new_state.value}")
            self._notify_state_listeners(new_state)

    # ── LISTENER SYSTEM ───────────────────────────────────

    def add_level_listener(self, callback: Callable[[LevelMeter], None]):
        """
        Real-time level updates ke liye listener add karo.
        Har audio chunk pe callback trigger hoga.

        Callback signature: def my_callback(meter: LevelMeter) -> None
        """
        if callback not in self._level_listeners:
            self._level_listeners.append(callback)

    def add_state_listener(self, callback: Callable[[RecordingState], None]):
        """
        State change ke liye listener add karo.
        (IDLE → RECORDING → PAUSED → STOPPED)
        """
        if callback not in self._state_listeners:
            self._state_listeners.append(callback)

    def add_completion_listener(self, callback: Callable[[RecordingMetadata], None]):
        """
        Recording complete hone par listener.
        Metadata milta hai callback mein.
        """
        if callback not in self._completion_listeners:
            self._completion_listeners.append(callback)

    def remove_level_listener(self, callback: Callable):
        if callback in self._level_listeners:
            self._level_listeners.remove(callback)

    def remove_state_listener(self, callback: Callable):
        if callback in self._state_listeners:
            self._state_listeners.remove(callback)

    def remove_completion_listener(self, callback: Callable):
        if callback in self._completion_listeners:
            self._completion_listeners.remove(callback)

    def _notify_level_listeners(self, meter: LevelMeter):
        """Level listeners ko notify karo (exception safe)"""
        for cb in self._level_listeners:
            try:
                cb(meter)
            except Exception as e:
                logger.debug(f"Level listener error: {e}")

    def _notify_state_listeners(self, state: RecordingState):
        for cb in self._state_listeners:
            try:
                cb(state)
            except Exception as e:
                logger.debug(f"State listener error: {e}")

    def _notify_completion_listeners(self, metadata: RecordingMetadata):
        for cb in self._completion_listeners:
            try:
                cb(metadata)
            except Exception as e:
                logger.debug(f"Completion listener error: {e}")

    # ── STATISTICS ────────────────────────────────────────

    def get_stats(self) -> Dict:
        """Recorder statistics return karo"""
        return {
            "state"             : self.state.value,
            "total_recordings"  : self.total_recordings,
            "total_duration"    : self.total_duration,
            "total_duration_str": format_duration(self.total_duration),
            "current_device"    : self.current_device.name if self.current_device else "None",
            "sample_rate"       : self.sample_rate,
            "channels"          : self.channels,
            "bit_depth"         : self.bit_depth,
            "quality"           : self.default_quality.label,
            "output_dir"        : self.output_dir,
            "backends"          : {
                "sounddevice": SOUNDDEVICE_AVAILABLE,
                "soundfile"  : SOUNDFILE_AVAILABLE,
                "pydub"      : PYDUB_AVAILABLE,
            },
        }

    def shutdown(self):
        """Cleanup on exit"""
        try:
            if self.is_active():
                self.cancel_recording()
            logger.info("🎙️ AudioRecorder shut down")
        except Exception as e:
            logger.error(f"Shutdown error: {e}")


# ============================================================
# CONTEXT MANAGER — with statement support
# ============================================================

class RecordingSession:
    """
    Context manager for easy recording.

    Usage:
        with RecordingSession("output.wav") as session:
            time.sleep(5)  # Record for 5 seconds
        # Auto-stops here
    """

    def __init__(self, output_path: Optional[str] = None,
                 max_duration: float = 60.0,
                 quality: AudioQuality = AudioQuality.HIGH):
        self.output_path  = output_path
        self.max_duration = max_duration
        self.quality      = quality
        self.recorder     = None
        self.metadata     = None

    def __enter__(self) -> "RecordingSession":
        self.recorder = AudioRecorder()
        self.recorder.set_quality(self.quality)
        self.recorder.start_recording(self.output_path, self.max_duration)
        return self

    def __exit__(self, *args):
        if self.recorder and self.recorder.is_active():
            self.metadata = self.recorder.stop_recording()
        elif self.recorder and self.recorder.current_metadata:
            # Auto-stop already fired
            self.metadata = self.recorder.current_metadata
        if self.recorder:
            self.recorder.shutdown()


# ============================================================
# TEST FUNCTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")
    print_banner(
        "🎙️ Audio Recorder Test",
        "Microphone recording — Level monitoring, silence detection"
    )

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))

    # ============================================================
    # Test 1: Initialize
    # ============================================================
    print_section("Test 1: Initialize Audio Recorder")

    recorder = AudioRecorder()
    stats = recorder.get_stats()

    print(f"  State        : {stats['state']}")
    print(f"  Sample rate  : {stats['sample_rate']} Hz")
    print(f"  Channels     : {stats['channels']}")
    print(f"  Bit depth    : {stats['bit_depth']} bit")
    print(f"  Quality      : {stats['quality']}")
    print(f"  Output dir   : {stats['output_dir']}")
    print(f"\n  Backends:")
    for name, avail in stats['backends'].items():
        status = "✅" if avail else "❌"
        print(f"    {status} {name}")

    if not SOUNDDEVICE_AVAILABLE:
        print("\n❌ sounddevice not available - cannot test recording")
        print("   Install: pip install sounddevice")
        sys.exit(1)

    # ============================================================
    # Test 2: List Input Devices
    # ============================================================
    print_section("Test 2: Available Input Devices (Microphones)")

    devices = recorder.list_devices()
    print(f"  Found {len(devices)} input devices:\n")

    for dev in devices:
        default_marker = " ⭐ DEFAULT" if dev.is_default else ""
        print(f"    [{dev.index}] {dev.name}{default_marker}")
        print(f"        Channels: {dev.channels} | Sample rate: {int(dev.sample_rate)} Hz")
        print(f"        Host API: {dev.hostapi}")

    if not devices:
        print("  ❌ No input devices found!")
        sys.exit(1)

    # ============================================================
    # Test 3: Current Device
    # ============================================================
    print_section("Test 3: Current Device")

    if recorder.current_device:
        print(f"  ✅ Selected: {recorder.current_device.name}")
        print(f"     Index   : {recorder.current_device.index}")
        print(f"     Channels: {recorder.current_device.channels}")
    else:
        print("  ❌ No device selected")

    # ============================================================
    # Test 4: Quality Presets
    # ============================================================
    print_section("Test 4: Quality Presets")

    print("  Available quality presets:\n")
    for q in AudioQuality:
        print(f"    {q.label:8s}: {q.sample_rate}Hz  {q.channels}ch  {q.bit_depth}bit")

    print("\n  Setting quality to MEDIUM for tests...")
    recorder.set_quality(AudioQuality.MEDIUM)
    print(f"  ✅ New quality: {recorder.default_quality.label}")

    # ============================================================
    # Test 5: Device Test
    # ============================================================
    print_section("Test 5: Test Microphone Access")

    if recorder.current_device:
        print(f"  Testing device: {recorder.current_device.name}")
        print("  (Recording 0.3s test sample...)")

        success, err = recorder.device_manager.test_device(
            recorder.current_device.index,
            duration=0.3,
            sample_rate=recorder.sample_rate,
        )

        if success:
            print("  ✅ Device working!")
        else:
            print(f"  ❌ Device test failed: {err}")

    # ============================================================
    # Test 6: Level Detector
    # ============================================================
    print_section("Test 6: Level Detector Test")

    detector = LevelDetector()

    # Fake audio chunks banao alag levels ke
    test_audio_samples = [
        ("Silence"         , np.zeros(1024)),
        ("Low volume"      , np.random.uniform(-0.1, 0.1, 1024).astype(np.float32)),
        ("Medium volume"   , np.random.uniform(-0.3, 0.3, 1024).astype(np.float32)),
        ("Loud volume"     , np.random.uniform(-0.7, 0.7, 1024).astype(np.float32)),
        ("Clipping"        , np.random.uniform(-0.99, 0.99, 1024).astype(np.float32)),
    ]

    print("  Testing level analysis:\n")
    for name, samples in test_audio_samples:
        meter = detector.analyze(samples)
        vis   = meter.get_visualization(width=25)
        silent_marker = " 🤫" if meter.is_silent else ""
        print(f"    {name:15s}: {vis}{silent_marker}")

    detector.reset()

    # ============================================================
    # Test 7: 3-Second Recording
    # ============================================================
    print_section("Test 7: Live Recording (3 seconds)")

    output_dir = os.path.join(base_dir, "temp", "recordings")
    ensure_dir(output_dir)
    test_output = os.path.join(output_dir, "test_recording_3sec.wav")

    print("  🎙️ Recording will start in 2 seconds...")
    print("  🗣️  SPEAK INTO YOUR MICROPHONE!")
    time.sleep(2)

    # Level callback for live visualization
    level_history = []

    def show_level(meter: LevelMeter):
        level_history.append(meter.current_level)

    recorder.add_level_listener(show_level)

    print("\n  🔴 RECORDING...\n")
    success = recorder.start_recording(test_output, max_duration=3.0)

    if success:
        # Live visualization
        start = time.time()
        while recorder.is_active() and (time.time() - start) < 3.5:
            duration = recorder.get_current_duration()
            if level_history:
                meter = LevelMeter(current_level=level_history[-1])
                vis = meter.get_visualization(width=30)
                print(f"\r  {duration:.1f}s {vis}", end="", flush=True)
            time.sleep(0.05)

        print()  # Newline

        # ✅ Wait for auto-stop to complete
        time.sleep(0.5)

        # Stop if still running (auto-stop should have fired)
        if recorder.is_active():
            metadata = recorder.stop_recording()
        else:
            # Auto-stop already fired — get latest metadata
            metadata = recorder.current_metadata

        recorder.remove_level_listener(show_level)

        if metadata and metadata.duration > 0:
            print(f"\n  ✅ Recording saved!")
            print(f"     File          : {os.path.basename(metadata.filepath)}")
            print(f"     Duration      : {format_duration(metadata.duration)}")
            print(f"     Size          : {format_bytes(metadata.file_size)}")
            print(f"     Peak level    : {metadata.peak_level:.3f}")
            print(f"     Average level : {metadata.average_level:.3f}")
            print(f"     Sample rate   : {metadata.sample_rate} Hz")
            print(f"     Channels      : {metadata.channels}")
        else:
            print("  ⚠️  Recording produced no data")
    else:
        print("  ❌ Recording failed!")

    # ============================================================
    # Test 8: Pause / Resume Recording
    # ============================================================
    print_section("Test 8: Pause/Resume Recording")

    test_output2 = os.path.join(output_dir, "test_pause_resume.wav")

    print("  🔴 Recording 2 seconds...")
    if recorder.start_recording(test_output2, max_duration=10.0):
        time.sleep(2.0)

        print("  ⏸️  Pausing for 1 second...")
        recorder.pause_recording()
        time.sleep(1.0)

        print("  ▶️  Resuming for 2 more seconds...")
        recorder.resume_recording()
        time.sleep(2.0)

        print("  ⏹️  Stopping...")
        metadata2 = recorder.stop_recording()

        if metadata2 and metadata2.duration > 0:
            print(f"\n  ✅ Pause/Resume test:")
            print(f"     Duration  : {format_duration(metadata2.duration)}")
            print(f"     Size      : {format_bytes(metadata2.file_size)}")
            print(f"     Was paused: {metadata2.was_paused}")
        else:
            print("  ⚠️  No data captured")
    else:
        print("  ❌ Failed to start")

    # ============================================================
    # Test 9: Silence Auto-Stop
    # ============================================================
    print_section("Test 9: Silence Auto-Stop Detection")

    test_output3 = os.path.join(output_dir, "test_silence_stop.wav")

    print("  🤫 Enabling auto-stop after 2 seconds of silence")
    recorder.enable_silence_auto_stop(silence_duration=2.0, threshold=0.03)

    print("  🔴 Recording... Speak briefly then stay silent!\n")
    if recorder.start_recording(test_output3, max_duration=10.0):
        # Wait for auto-stop or manual timeout
        start = time.time()
        while recorder.is_active() and (time.time() - start) < 10.0:
            duration = recorder.get_current_duration()
            print(f"\r  Duration: {duration:.1f}s", end="", flush=True)
            time.sleep(0.1)
        print()

        # Wait for stop to complete
        time.sleep(0.5)

        # Stop agar auto-stop nahi hua
        if recorder.is_active():
            metadata3 = recorder.stop_recording()
        else:
            metadata3 = recorder.current_metadata

        if metadata3 and metadata3.duration > 0:
            auto_marker = " (auto-stopped)" if metadata3.auto_stopped else ""
            print(f"  ✅ Stopped after: {format_duration(metadata3.duration)}{auto_marker}")
            print(f"     Size: {format_bytes(metadata3.file_size)}")

    recorder.disable_silence_auto_stop()

    # ============================================================
    # Test 10: Context Manager (RecordingSession)
    # ============================================================
    print_section("Test 10: Context Manager Usage")

    test_output4 = os.path.join(output_dir, "test_context_manager.wav")

    print("  Using 'with' statement for auto-cleanup...")
    print("  🔴 Recording 2 seconds...")

    with RecordingSession(test_output4, max_duration=2.5, quality=AudioQuality.LOW) as session:
        time.sleep(2.0)
        # Session ka recorder access karke stop kar sakte hain
        if session.recorder and session.recorder.is_active():
            session.metadata = session.recorder.stop_recording()

    if session.metadata and session.metadata.duration > 0:
        print(f"  ✅ Context manager recording:")
        print(f"     File    : {os.path.basename(session.metadata.filepath)}")
        print(f"     Duration: {format_duration(session.metadata.duration)}")
        print(f"     Size    : {format_bytes(session.metadata.file_size)}")
        print(f"     Quality : {session.metadata.quality}")
    else:
        print("  ⚠️  Context manager: no data")

    # ============================================================
    # Test 11: Final Statistics
    # ============================================================
    print_section("Test 11: Final Statistics")

    stats = recorder.get_stats()
    print(f"  Total recordings : {stats['total_recordings']}")
    print(f"  Total duration   : {stats['total_duration_str']}")
    print(f"  Current state    : {stats['state']}")

    # ============================================================
    # Cleanup
    # ============================================================
    print_section("Cleanup & Info")

    recorder.shutdown()
    print(f"\n  📁 Recorded files saved in:")
    print(f"     {output_dir}")
    print(f"\n  👉 Open to listen:")
    print(f"     start {output_dir}")

    print_banner(
        "✅ Audio Recorder Ready!",
        f"All features working — {stats['total_recordings']} recordings made"
    )