# ============================================================
# 3D ANIMATION STUDIO - Sound Effects Engine
# ============================================================
# Features:
# - SFX library with preset catalog
# - Synthetic sound generation (no external samples needed)
# - Audio effects: reverb, echo, EQ, compression, distortion
# - Pitch shift & time stretch (librosa)
# - Voice effects: robot, chipmunk, deep, radio
# - Ambient sound layering
# - Preset categories: nature, urban, cinematic, action
# - Effect chains (multiple effects sequentially)
# - Favorites & custom SFX import
# - Preview playback integration
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

import math
import time
import json
import random
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable, Any

import numpy as np

# Audio libraries
try:
    from pydub import AudioSegment
    from pydub.generators import Sine, Square, Sawtooth, WhiteNoise
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
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    librosa = None

try:
    from scipy import signal as scipy_signal
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    scipy_signal = None

from src.utils import (
    get_logger, get_config, ensure_dir, generate_short_id,
    get_timestamp, format_duration, format_bytes, get_file_size,
    clamp, lerp,
)

logger = get_logger("SoundEffects")


# ============================================================
# CONSTANTS & ENUMS
# ============================================================

class SFXCategory(Enum):
    """Sound effect categories — browsing ke liye"""
    IMPACT     = "impact"       # Hits, punches, crashes
    UI         = "ui"           # Button clicks, notifications
    NATURE     = "nature"       # Rain, wind, thunder
    URBAN      = "urban"        # Traffic, crowd, cafe
    ACTION     = "action"       # Explosions, gunshots, whooshes
    HORROR     = "horror"       # Scary, tension, jumpscares
    COMEDY     = "comedy"       # Cartoon, funny sounds
    CINEMATIC  = "cinematic"    # Movie-style effects
    ANIMAL     = "animal"       # Dog, cat, birds, etc.
    HUMAN      = "human"        # Footsteps, breathing, claps
    MUSICAL    = "musical"      # Chords, jingles, stingers
    MECHANICAL = "mechanical"   # Engine, door, machinery


class EffectType(Enum):
    """Audio effect types — processing ke liye"""
    REVERB      = "reverb"      # Space simulation
    ECHO        = "echo"        # Delayed repeats
    DELAY       = "delay"       # Simple delay
    LOWPASS     = "lowpass"     # High freq remove
    HIGHPASS    = "highpass"    # Low freq remove
    BANDPASS    = "bandpass"    # Mid range keep
    COMPRESSOR  = "compressor"  # Dynamic range
    DISTORTION  = "distortion"  # Harmonic distortion
    OVERDRIVE   = "overdrive"   # Warm distortion
    BITCRUSH    = "bitcrush"    # 8-bit style
    CHORUS      = "chorus"      # Doubling effect
    TREMOLO     = "tremolo"     # Volume modulation
    PITCH_SHIFT = "pitch_shift" # Pitch change
    TIME_STRETCH= "time_stretch"# Speed without pitch
    NORMALIZE   = "normalize"   # Auto-level


class ReverbPreset(Enum):
    """Reverb presets — different environments simulate"""
    ROOM       = ("room",       0.15, 0.30)   # Small room
    HALL       = ("hall",       0.40, 0.55)   # Concert hall
    CATHEDRAL  = ("cathedral",  0.70, 0.75)   # Large cathedral
    CAVE       = ("cave",       0.55, 0.65)   # Cave/dungeon
    BATHROOM   = ("bathroom",   0.25, 0.45)   # Tiled bathroom
    STADIUM    = ("stadium",    0.85, 0.80)   # Open stadium
    PLATE      = ("plate",      0.35, 0.50)   # Classic plate reverb

    def __init__(self, label: str, decay: float, wet: float):
        self.label = label
        self.decay = decay  # 0-1 — reverb tail length
        self.wet   = wet    # 0-1 — dry/wet mix


class VoiceEffect(Enum):
    """Voice modification presets"""
    NORMAL    = "normal"
    ROBOT     = "robot"        # Metallic, monotone
    CHIPMUNK  = "chipmunk"     # High pitched
    DEEP      = "deep"         # Low pitched (villain)
    RADIO     = "radio"        # Old radio effect
    UNDERWATER= "underwater"   # Muffled
    TELEPHONE = "telephone"    # Phone call quality
    GHOST     = "ghost"        # Spooky reverb
    MONSTER   = "monster"      # Deep + distortion


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class SFXPreset:
    """
    Sound effect preset — synthetic sound generator ka blueprint.
    Har preset apne parameters se ek unique sound generate karta hai.
    """
    name        : str                                    # Human-readable naam
    category    : SFXCategory                           # Category enum
    duration_ms : int                       = 1000     # Length in milliseconds
    description : str                        = ""       # Kya sound hai
    tags        : List[str]                 = field(default_factory=list)

    # Synthesis parameters (generator function ke liye)
    base_freq       : float = 440.0     # Hz — base frequency
    freq_end        : float = 440.0     # End frequency (for sweeps)
    volume          : float = 0.7       # 0-1
    noise_amount    : float = 0.0       # 0-1 — noise mixing
    attack_ms       : int   = 10        # Fade-in time
    decay_ms        : int   = 500       # Fade-out time

    def to_dict(self) -> Dict:
        return {
            "name"        : self.name,
            "category"    : self.category.value,
            "duration_ms" : self.duration_ms,
            "description" : self.description,
            "tags"        : self.tags,
            "base_freq"   : self.base_freq,
            "volume"      : self.volume,
        }


@dataclass
class EffectResult:
    """Effect processing ka result"""
    success     : bool                    = False
    output_path : Optional[str]           = None
    duration    : float                    = 0.0
    file_size   : int                      = 0
    effect_used : str                      = ""
    error       : Optional[str]           = None
    processing_time : float                = 0.0


# ============================================================
# SFX SYNTHESIZER — Programmatically Generate Sounds
# ============================================================

class SFXSynthesizer:
    """
    🎵 Sounds ko code se generate karta hai — koi external files nahi chahiye.

    Ye pydub generators use karta hai — Sine/Square/Sawtooth/WhiteNoise ko
    combine karke realistic sound effects banata hai.
    """

    SAMPLE_RATE = 44100

    @staticmethod
    def _check_pydub() -> bool:
        if not PYDUB_AVAILABLE:
            logger.error("pydub required for SFX synthesis")
            return False
        return True

    # ── BASIC WAVEFORMS ──────────────────────────────────

    @classmethod
    def sine_tone(cls, freq: float = 440.0,
                  duration_ms: int = 1000,
                  volume: float = 0.5) -> Optional[AudioSegment]:
        """Simple sine wave — clean pure tone"""
        if not cls._check_pydub():
            return None
        try:
            tone = Sine(freq).to_audio_segment(duration=duration_ms)
            # Volume dB me convert karo
            db = 20 * math.log10(max(0.01, volume))
            return tone + db
        except Exception as e:
            logger.error(f"Sine tone failed: {e}")
            return None

    @classmethod
    def noise(cls, duration_ms: int = 1000,
              volume: float = 0.3) -> Optional[AudioSegment]:
        """White noise — hiss/static sound"""
        if not cls._check_pydub():
            return None
        try:
            n = WhiteNoise().to_audio_segment(duration=duration_ms)
            db = 20 * math.log10(max(0.01, volume))
            return n + db
        except Exception as e:
            logger.error(f"Noise failed: {e}")
            return None

    @classmethod
    def sweep(cls, start_freq: float, end_freq: float,
              duration_ms: int = 1000,
              volume: float = 0.5) -> Optional[AudioSegment]:
        """
        Frequency sweep — low se high ya high se low.
        Whoosh, laser, spaceship sounds ke liye useful.
        """
        if not cls._check_pydub():
            return None
        try:
            # Multiple short segments join karke sweep create karo
            num_steps = 50
            step_duration = duration_ms // num_steps
            segments = []

            for i in range(num_steps):
                t = i / (num_steps - 1)
                # Logarithmic interpolation for natural sweep
                freq = start_freq * ((end_freq / start_freq) ** t)
                seg = Sine(freq).to_audio_segment(duration=step_duration)
                segments.append(seg)

            result = sum(segments)
            db = 20 * math.log10(max(0.01, volume))
            return result + db
        except Exception as e:
            logger.error(f"Sweep failed: {e}")
            return None

    # ── PRESET SFX GENERATORS ────────────────────────────

    @classmethod
    def generate_click(cls) -> Optional[AudioSegment]:
        """UI click — sharp short beep"""
        tone = cls.sine_tone(freq=800, duration_ms=50, volume=0.5)
        if tone:
            tone = tone.fade_in(2).fade_out(30)
        return tone

    @classmethod
    def generate_notification(cls) -> Optional[AudioSegment]:
        """Notification chime — 2-tone bell"""
        if not cls._check_pydub():
            return None
        try:
            tone1 = cls.sine_tone(880, 150, 0.5)
            tone2 = cls.sine_tone(1108, 300, 0.5)
            if tone1 and tone2:
                return (tone1 + tone2).fade_out(200)
        except Exception as e:
            logger.error(f"Notification failed: {e}")
        return None

    @classmethod
    def generate_beep(cls) -> Optional[AudioSegment]:
        """Simple beep — computer alert"""
        return cls.sine_tone(1000, 200, 0.5)

    @classmethod
    def generate_whoosh(cls) -> Optional[AudioSegment]:
        """Whoosh — object moving fast"""
        if not cls._check_pydub():
            return None
        try:
            # Noise sweep with pitch curve
            n = cls.noise(duration_ms=500, volume=0.4)
            sw = cls.sweep(200, 2000, 500, 0.3)
            if n and sw:
                combined = n.overlay(sw)
                return combined.fade_in(50).fade_out(150)
        except Exception as e:
            logger.error(f"Whoosh failed: {e}")
        return None

    @classmethod
    def generate_impact(cls) -> Optional[AudioSegment]:
        """Impact hit — punch/hit sound"""
        if not cls._check_pydub():
            return None
        try:
            # Low freq boom + noise burst
            boom = cls.sine_tone(60, 300, 0.9)
            noise_burst = cls.noise(100, 0.5)
            if boom and noise_burst:
                combined = boom.overlay(noise_burst)
                return combined.fade_out(250)
        except Exception as e:
            logger.error(f"Impact failed: {e}")
        return None

    @classmethod
    def generate_explosion(cls) -> Optional[AudioSegment]:
        """Explosion — big boom with rumble"""
        if not cls._check_pydub():
            return None
        try:
            # Low freq boom
            boom = cls.sine_tone(50, 800, 1.0)
            # Noise blast
            blast = cls.noise(1000, 0.7)
            # Sub bass
            sub = cls.sine_tone(30, 1200, 0.8)

            if boom and blast and sub:
                combined = sub.overlay(boom).overlay(blast)
                return combined.fade_out(800)
        except Exception as e:
            logger.error(f"Explosion failed: {e}")
        return None

    @classmethod
    def generate_thunder(cls) -> Optional[AudioSegment]:
        """Thunder rumble"""
        if not cls._check_pydub():
            return None
        try:
            # Multiple noise layers with low frequency
            n1 = cls.noise(2000, 0.5)
            sub1 = cls.sine_tone(40, 2000, 0.7)
            sub2 = cls.sine_tone(60, 2000, 0.5)

            if n1 and sub1 and sub2:
                combined = n1.overlay(sub1).overlay(sub2)
                return combined.fade_in(100).fade_out(1500)
        except Exception as e:
            logger.error(f"Thunder failed: {e}")
        return None

    @classmethod
    def generate_rain(cls, duration_ms: int = 3000) -> Optional[AudioSegment]:
        """Rain — high freq filtered noise (loopable)"""
        if not cls._check_pydub():
            return None
        try:
            # White noise ki filtered layers
            base = cls.noise(duration_ms, 0.35)
            if base:
                # High-pass filter jaise effect banao overlays se
                high_freq = cls.noise(duration_ms, 0.2)
                return base.overlay(high_freq)
        except Exception as e:
            logger.error(f"Rain failed: {e}")
        return None

    @classmethod
    def generate_wind(cls, duration_ms: int = 3000) -> Optional[AudioSegment]:
        """Wind — low freq filtered noise"""
        if not cls._check_pydub():
            return None
        try:
            n = cls.noise(duration_ms, 0.5)
            if n:
                # Slow pitch modulation ke liye multiple sines
                mod = cls.sine_tone(100, duration_ms, 0.15)
                if mod:
                    return n.overlay(mod).fade_in(500).fade_out(500)
                return n.fade_in(500).fade_out(500)
        except Exception as e:
            logger.error(f"Wind failed: {e}")
        return None

    @classmethod
    def generate_laser(cls) -> Optional[AudioSegment]:
        """Laser gun — sci-fi zap"""
        return cls.sweep(2000, 200, 400, 0.6)

    @classmethod
    def generate_power_up(cls) -> Optional[AudioSegment]:
        """Power up — video game ascending sound"""
        return cls.sweep(200, 1500, 600, 0.5)

    @classmethod
    def generate_power_down(cls) -> Optional[AudioSegment]:
        """Power down — descending sound"""
        return cls.sweep(1500, 200, 800, 0.5)

    @classmethod
    def generate_coin(cls) -> Optional[AudioSegment]:
        """Coin pickup — classic mario style"""
        if not cls._check_pydub():
            return None
        try:
            tone1 = cls.sine_tone(988, 100, 0.5)   # B5
            tone2 = cls.sine_tone(1319, 300, 0.5)  # E6
            if tone1 and tone2:
                return (tone1 + tone2).fade_out(200)
        except Exception as e:
            logger.error(f"Coin failed: {e}")
        return None

    @classmethod
    def generate_heartbeat(cls) -> Optional[AudioSegment]:
        """Heartbeat — thump-thump"""
        if not cls._check_pydub():
            return None
        try:
            thump1 = cls.sine_tone(60, 100, 0.9).fade_out(90)
            silence1 = AudioSegment.silent(duration=100)
            thump2 = cls.sine_tone(50, 150, 0.7).fade_out(130)
            silence2 = AudioSegment.silent(duration=550)
            return thump1 + silence1 + thump2 + silence2
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
        return None

    @classmethod
    def generate_footstep(cls) -> Optional[AudioSegment]:
        """Footstep — quick thud"""
        if not cls._check_pydub():
            return None
        try:
            thud = cls.sine_tone(80, 80, 0.6)
            crunch = cls.noise(50, 0.3)
            if thud and crunch:
                return thud.overlay(crunch).fade_out(70)
        except Exception as e:
            logger.error(f"Footstep failed: {e}")
        return None

    @classmethod
    def generate_glass_break(cls) -> Optional[AudioSegment]:
        """Glass shatter"""
        if not cls._check_pydub():
            return None
        try:
            # High freq noise burst with quick decay
            n = cls.noise(500, 0.7)
            high = cls.sine_tone(2500, 200, 0.4)
            if n and high:
                return n.overlay(high).fade_out(400)
        except Exception as e:
            logger.error(f"Glass break failed: {e}")
        return None

    @classmethod
    def generate_alarm(cls) -> Optional[AudioSegment]:
        """Alarm — oscillating high tone"""
        if not cls._check_pydub():
            return None
        try:
            # 3 pulses
            tone_high = cls.sine_tone(1000, 200, 0.7)
            tone_low  = cls.sine_tone(700, 200, 0.7)
            if tone_high and tone_low:
                pattern = tone_high + tone_low
                return pattern + pattern + pattern
        except Exception as e:
            logger.error(f"Alarm failed: {e}")
        return None

    @classmethod
    def generate_success(cls) -> Optional[AudioSegment]:
        """Success chime — ascending happy tones"""
        if not cls._check_pydub():
            return None
        try:
            t1 = cls.sine_tone(523, 100, 0.5)   # C5
            t2 = cls.sine_tone(659, 100, 0.5)   # E5
            t3 = cls.sine_tone(784, 200, 0.5)   # G5
            if t1 and t2 and t3:
                return (t1 + t2 + t3).fade_out(150)
        except Exception as e:
            logger.error(f"Success failed: {e}")
        return None

    @classmethod
    def generate_error(cls) -> Optional[AudioSegment]:
        """Error buzz — low double buzz"""
        if not cls._check_pydub():
            return None
        try:
            buzz1 = cls.sine_tone(200, 200, 0.5)
            silence = AudioSegment.silent(duration=50)
            buzz2 = cls.sine_tone(200, 200, 0.5)
            if buzz1 and buzz2:
                return buzz1 + silence + buzz2
        except Exception as e:
            logger.error(f"Error failed: {e}")
        return None


# ============================================================
# AUDIO EFFECTS PROCESSOR
# ============================================================

class AudioEffectsProcessor:
    """
    🎛️ Audio ko process karke effects apply karta hai.
    Reverb, echo, filters, distortion — sab yahan.
    """

    @staticmethod
    def _check_pydub() -> bool:
        if not PYDUB_AVAILABLE:
            logger.error("pydub required for effects")
            return False
        return True

    # ── SPACE / TIME EFFECTS ─────────────────────────────

    @staticmethod
    def reverb(audio: AudioSegment,
               preset: ReverbPreset = ReverbPreset.HALL,
               wet: Optional[float] = None) -> AudioSegment:
        """
        Reverb effect — space simulation.
        Multiple delayed echoes overlay karke create karte hain.

        Args:
            audio  : Input audio
            preset : ReverbPreset (ROOM, HALL, CATHEDRAL, etc.)
            wet    : Dry/wet mix (0-1). None = preset default
        """
        if not AudioEffectsProcessor._check_pydub():
            return audio

        try:
            wet_amount = wet if wet is not None else preset.wet
            decay      = preset.decay

            # Multiple delay taps banao
            num_taps = 8
            result   = audio

            for i in range(num_taps):
                # Har tap ka delay time increasing
                delay_ms = int(20 + i * 40 * (1 + decay))
                # Volume decay
                tap_volume_db = -6 - (i * 3 * (1 - decay))

                # Delayed copy banao
                delayed = AudioSegment.silent(duration=delay_ms) + audio
                delayed = delayed + tap_volume_db

                # Original ke length ke barabar trim karo
                delayed = delayed[:len(audio) + delay_ms]

                # Wet amount ke saath mix
                wet_db = 20 * math.log10(max(0.01, wet_amount * (1 - i * 0.15)))
                delayed = delayed + wet_db

                result = result.overlay(delayed)

            return result

        except Exception as e:
            logger.error(f"Reverb failed: {e}")
            return audio

    @staticmethod
    def echo(audio: AudioSegment,
             delay_ms: int = 300,
             decay: float = 0.5,
             repeats: int = 3) -> AudioSegment:
        """
        Echo effect — distinct delayed repeats.

        Args:
            delay_ms : Har repeat ke beech gap
            decay    : Volume decrease per repeat (0-1)
            repeats  : Kitne echoes
        """
        if not AudioEffectsProcessor._check_pydub():
            return audio

        try:
            result = audio

            for i in range(1, repeats + 1):
                # i-th echo
                total_delay = delay_ms * i
                echo_volume = decay ** i

                # Volume dB me
                echo_db = 20 * math.log10(max(0.01, echo_volume))

                # Delay + audio
                echoed = AudioSegment.silent(duration=total_delay) + audio
                echoed = echoed + echo_db

                result = result.overlay(echoed)

            return result

        except Exception as e:
            logger.error(f"Echo failed: {e}")
            return audio

    @staticmethod
    def delay(audio: AudioSegment, delay_ms: int = 250,
              wet: float = 0.5) -> AudioSegment:
        """Simple single delay"""
        if not AudioEffectsProcessor._check_pydub():
            return audio

        try:
            wet_db  = 20 * math.log10(max(0.01, wet))
            delayed = (AudioSegment.silent(duration=delay_ms) + audio) + wet_db
            return audio.overlay(delayed)
        except Exception as e:
            logger.error(f"Delay failed: {e}")
            return audio

    # ── FILTER EFFECTS ───────────────────────────────────

    @staticmethod
    def lowpass_filter(audio: AudioSegment, cutoff_hz: int = 1000) -> AudioSegment:
        """
        Low-pass filter — high frequencies remove karo.
        Muffled/underwater effect ke liye useful.
        """
        if not AudioEffectsProcessor._check_pydub():
            return audio
        try:
            return audio.low_pass_filter(cutoff_hz)
        except Exception as e:
            logger.error(f"Lowpass failed: {e}")
            return audio

    @staticmethod
    def highpass_filter(audio: AudioSegment, cutoff_hz: int = 200) -> AudioSegment:
        """
        High-pass filter — low frequencies remove karo.
        Thin/radio effect ke liye useful.
        """
        if not AudioEffectsProcessor._check_pydub():
            return audio
        try:
            return audio.high_pass_filter(cutoff_hz)
        except Exception as e:
            logger.error(f"Highpass failed: {e}")
            return audio

    @staticmethod
    def bandpass_filter(audio: AudioSegment,
                        low_hz: int = 300,
                        high_hz: int = 3000) -> AudioSegment:
        """Bandpass — sirf specific frequency range keep karo"""
        if not AudioEffectsProcessor._check_pydub():
            return audio
        try:
            filtered = audio.high_pass_filter(low_hz)
            filtered = filtered.low_pass_filter(high_hz)
            return filtered
        except Exception as e:
            logger.error(f"Bandpass failed: {e}")
            return audio

    # ── DYNAMICS ─────────────────────────────────────────

    @staticmethod
    def compressor(audio: AudioSegment,
                   threshold_db: float = -20.0,
                   ratio: float = 4.0) -> AudioSegment:
        """
        Compressor — loud parts kam, soft parts zyada.
        Voice/music ko balance karne ke liye.

        Args:
            threshold_db : Isse loud sab compress hoga
            ratio        : Compression amount (4:1 typical)
        """
        if not AudioEffectsProcessor._check_pydub():
            return audio

        try:
            # pydub ka built-in compressor
            from pydub.effects import compress_dynamic_range
            return compress_dynamic_range(
                audio,
                threshold=threshold_db,
                ratio=ratio,
                attack=5.0,
                release=50.0,
            )
        except Exception as e:
            logger.error(f"Compressor failed: {e}")
            return audio

    @staticmethod
    def normalize(audio: AudioSegment,
                  target_db: float = -3.0) -> AudioSegment:
        """
        Normalize — peak level ko target tak lao.
        Consistent volume ke liye.
        """
        if not AudioEffectsProcessor._check_pydub():
            return audio
        try:
            current_peak = audio.max_dBFS
            if current_peak == float("-inf"):
                return audio
            change = target_db - current_peak
            return audio + change
        except Exception as e:
            logger.error(f"Normalize failed: {e}")
            return audio

    # ── DISTORTION EFFECTS ───────────────────────────────

    @staticmethod
    def distortion(audio: AudioSegment,
                   gain: float = 10.0,
                   mix: float = 0.7) -> AudioSegment:
        """
        Distortion — signal ko clip karke harmonic distortion add karo.

        Args:
            gain: Distortion amount
            mix : Dry/wet ratio (0-1)
        """
        if not AudioEffectsProcessor._check_pydub():
            return audio

        try:
            # Volume boost karo — natural clipping hogi
            boosted = audio + gain

            # Mix ke liye original ke saath blend karo
            mix_db_wet = 20 * math.log10(max(0.01, mix))
            mix_db_dry = 20 * math.log10(max(0.01, 1 - mix))

            wet = boosted + mix_db_wet
            dry = audio + mix_db_dry

            return dry.overlay(wet)
        except Exception as e:
            logger.error(f"Distortion failed: {e}")
            return audio

    @staticmethod
    def bitcrush(audio: AudioSegment,
                 bit_depth: int = 4) -> AudioSegment:
        """
        Bitcrush — 8-bit / lo-fi effect.
        Sample resolution reduce karta hai.

        Args:
            bit_depth: Target bit depth (1-8 = crunchy, 8-16 = subtle)
        """
        if not AudioEffectsProcessor._check_pydub():
            return audio

        try:
            # Raw samples nikalo
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)

            # Original bit depth se normalize karo
            max_val = 2 ** (audio.sample_width * 8 - 1)
            samples_norm = samples / max_val

            # Quantization steps calculate karo
            steps      = 2 ** bit_depth
            quantized  = np.round(samples_norm * steps) / steps
            crushed    = (quantized * max_val).astype(samples.dtype)

            # Back to AudioSegment
            return audio._spawn(crushed.tobytes())
        except Exception as e:
            logger.error(f"Bitcrush failed: {e}")
            return audio

    # ── MODULATION EFFECTS ───────────────────────────────

    @staticmethod
    def tremolo(audio: AudioSegment,
                rate_hz: float = 5.0,
                depth: float = 0.5) -> AudioSegment:
        """
        Tremolo — rhythmic volume modulation.

        Args:
            rate_hz: Modulation speed (5Hz = fast, 1Hz = slow)
            depth  : Modulation depth 0-1
        """
        if not AudioEffectsProcessor._check_pydub():
            return audio

        try:
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            n       = len(samples)
            sr      = audio.frame_rate

            # LFO (Low Frequency Oscillator) banao
            t   = np.arange(n) / sr
            lfo = 1.0 - depth * (0.5 + 0.5 * np.sin(2 * np.pi * rate_hz * t))

            # Multi-channel adjust
            if audio.channels == 2 and n % 2 == 0:
                lfo = np.repeat(lfo[:n // 2], 2)[:n]

            modulated = (samples * lfo).astype(samples.dtype)
            return audio._spawn(modulated.tobytes())
        except Exception as e:
            logger.error(f"Tremolo failed: {e}")
            return audio

    # ── PITCH & TIME EFFECTS ─────────────────────────────

    @staticmethod
    def pitch_shift(audio: AudioSegment,
                    semitones: float = 0.0) -> AudioSegment:
        """
        Pitch change — speed ko affect kiye bina pitch badlo.
        librosa chahiye better quality ke liye.

        Args:
            semitones: +12 = octave up, -12 = octave down
        """
        if semitones == 0:
            return audio

        # librosa method (preferred)
        if LIBROSA_AVAILABLE:
            try:
                samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
                max_val = 2 ** (audio.sample_width * 8 - 1)
                samples_norm = samples / max_val

                # Stereo handling
                if audio.channels == 2:
                    samples_norm = samples_norm.reshape(-1, 2).T

                shifted = librosa.effects.pitch_shift(
                    samples_norm,
                    sr=audio.frame_rate,
                    n_steps=semitones,
                )

                # Back to interleaved
                if audio.channels == 2:
                    shifted = shifted.T.flatten()

                shifted_int = (shifted * max_val).astype(samples.dtype)
                return audio._spawn(shifted_int.tobytes())
            except Exception as e:
                logger.warning(f"librosa pitch shift failed: {e}, using fallback")

        # Fallback: pydub method (pitch aur speed dono change hote hain)
        if AudioEffectsProcessor._check_pydub():
            try:
                # Frame rate change karo — natural pitch shift
                pitch_multiplier = 2 ** (semitones / 12.0)
                new_frame_rate   = int(audio.frame_rate * pitch_multiplier)
                shifted = audio._spawn(audio.raw_data, overrides={
                    "frame_rate": new_frame_rate
                })
                return shifted.set_frame_rate(audio.frame_rate)
            except Exception as e:
                logger.error(f"Pitch shift failed: {e}")

        return audio

    @staticmethod
    def time_stretch(audio: AudioSegment,
                     factor: float = 1.0) -> AudioSegment:
        """
        Time stretch — pitch ko affect kiye bina speed badlo.
        librosa chahiye.

        Args:
            factor: 2.0 = double speed, 0.5 = half speed
        """
        if factor == 1.0:
            return audio

        if not LIBROSA_AVAILABLE:
            logger.warning("librosa needed for time stretch")
            return audio

        try:
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            max_val = 2 ** (audio.sample_width * 8 - 1)
            samples_norm = samples / max_val

            if audio.channels == 2:
                samples_norm = samples_norm.reshape(-1, 2).T

            stretched = librosa.effects.time_stretch(samples_norm, rate=factor)

            if audio.channels == 2:
                stretched = stretched.T.flatten()

            stretched_int = (stretched * max_val).astype(samples.dtype)
            return audio._spawn(stretched_int.tobytes())
        except Exception as e:
            logger.error(f"Time stretch failed: {e}")
            return audio


# ============================================================
# VOICE EFFECTS
# ============================================================

class VoiceEffectsProcessor:
    """
    🎤 Voice-specific effects — character voices banane ke liye.
    TTS output ya recorded voice pe apply karo.
    """

    @staticmethod
    def apply(audio: AudioSegment, effect: VoiceEffect) -> AudioSegment:
        """
        Voice effect apply karo.

        Args:
            audio : Input voice audio
            effect: VoiceEffect enum se preset
        """
        if not PYDUB_AVAILABLE:
            return audio

        try:
            fx = AudioEffectsProcessor

            if effect == VoiceEffect.NORMAL:
                return audio

            elif effect == VoiceEffect.ROBOT:
                # Metallic robot: pitch shift + bitcrush + slight reverb
                result = fx.pitch_shift(audio, semitones=-2)
                result = fx.bitcrush(result, bit_depth=6)
                result = fx.tremolo(result, rate_hz=20, depth=0.3)
                return result

            elif effect == VoiceEffect.CHIPMUNK:
                # High pitched cartoon voice
                return fx.pitch_shift(audio, semitones=+8)

            elif effect == VoiceEffect.DEEP:
                # Villain / monster voice
                return fx.pitch_shift(audio, semitones=-6)

            elif effect == VoiceEffect.RADIO:
                # Old radio: bandpass + slight distortion
                result = fx.bandpass_filter(audio, low_hz=400, high_hz=3000)
                result = fx.distortion(result, gain=3, mix=0.4)
                return result

            elif effect == VoiceEffect.UNDERWATER:
                # Muffled underwater
                result = fx.lowpass_filter(audio, cutoff_hz=800)
                result = fx.reverb(result, ReverbPreset.CAVE, wet=0.5)
                return result

            elif effect == VoiceEffect.TELEPHONE:
                # Phone call quality
                return fx.bandpass_filter(audio, low_hz=300, high_hz=3400)

            elif effect == VoiceEffect.GHOST:
                # Spooky ghost voice
                result = fx.pitch_shift(audio, semitones=-3)
                result = fx.reverb(result, ReverbPreset.CATHEDRAL, wet=0.8)
                result = fx.tremolo(result, rate_hz=3, depth=0.4)
                return result

            elif effect == VoiceEffect.MONSTER:
                # Deep monster growl
                result = fx.pitch_shift(audio, semitones=-8)
                result = fx.distortion(result, gain=6, mix=0.5)
                result = fx.reverb(result, ReverbPreset.CAVE, wet=0.4)
                return result

            return audio

        except Exception as e:
            logger.error(f"Voice effect '{effect.value}' failed: {e}")
            return audio


# ============================================================
# SFX LIBRARY — Preset Catalog Management
# ============================================================

class SFXLibrary:
    """
    📚 Sound effects ka catalog manager.

    Presets ko categories mein organize karta hai, favorites track karta hai,
    aur custom SFX import karne deta hai.
    """

    def __init__(self, library_dir: Optional[str] = None):
        """
        Args:
            library_dir: SFX files store karne ki jagah
        """
        if library_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)
            )))
            library_dir = os.path.join(base_dir, "assets", "audio", "sfx")

        self.library_dir = Path(library_dir)
        ensure_dir(str(self.library_dir))

        # Presets registry
        self._presets: Dict[str, SFXPreset] = {}

        # Favorites list
        self._favorites: set = set()
        self._favorites_file = self.library_dir / "favorites.json"

        # Custom SFX files (user imported)
        self._custom_sfx: Dict[str, str] = {}   # name → filepath

        # Register default presets
        self._register_default_presets()

        # Load favorites
        self._load_favorites()

        logger.info(
            f"📚 SFX Library initialized: {len(self._presets)} presets, "
            f"{len(self._favorites)} favorites"
        )

    def _register_default_presets(self):
        """Sabhi default presets register karo"""
        defaults = [
            # UI sounds
            SFXPreset("click", SFXCategory.UI, 50, "Sharp UI click", ["ui", "button"]),
            SFXPreset("beep", SFXCategory.UI, 200, "Computer beep", ["ui", "alert"]),
            SFXPreset("notification", SFXCategory.UI, 450, "2-tone chime", ["ui", "chime"]),
            SFXPreset("success", SFXCategory.UI, 400, "Success ascending chime", ["ui", "positive"]),
            SFXPreset("error", SFXCategory.UI, 450, "Error double buzz", ["ui", "negative"]),
            SFXPreset("alarm", SFXCategory.UI, 1200, "Oscillating alarm", ["ui", "urgent"]),

            # Impact sounds
            SFXPreset("impact", SFXCategory.IMPACT, 300, "Hard impact hit", ["hit", "punch"]),
            SFXPreset("explosion", SFXCategory.ACTION, 1200, "Big explosion boom", ["boom", "blast"]),
            SFXPreset("glass_break", SFXCategory.IMPACT, 500, "Glass shatter", ["break", "crash"]),

            # Nature sounds
            SFXPreset("thunder", SFXCategory.NATURE, 2000, "Thunder rumble", ["weather", "storm"]),
            SFXPreset("rain", SFXCategory.NATURE, 3000, "Rain ambience (loopable)", ["weather", "ambient"]),
            SFXPreset("wind", SFXCategory.NATURE, 3000, "Wind ambience (loopable)", ["weather", "ambient"]),

            # Action sounds
            SFXPreset("whoosh", SFXCategory.ACTION, 500, "Fast movement whoosh", ["swipe", "movement"]),
            SFXPreset("laser", SFXCategory.ACTION, 400, "Sci-fi laser zap", ["scifi", "weapon"]),

            # Human sounds
            SFXPreset("footstep", SFXCategory.HUMAN, 80, "Walking footstep", ["walk", "movement"]),
            SFXPreset("heartbeat", SFXCategory.HUMAN, 900, "Heartbeat thump", ["body", "tension"]),

            # Musical
            SFXPreset("coin", SFXCategory.MUSICAL, 400, "Video game coin pickup", ["game", "reward"]),
            SFXPreset("power_up", SFXCategory.MUSICAL, 600, "Ascending power up", ["game", "positive"]),
            SFXPreset("power_down", SFXCategory.MUSICAL, 800, "Descending power down", ["game", "negative"]),
        ]

        for preset in defaults:
            self._presets[preset.name] = preset

    # ── PRESET ACCESS ─────────────────────────────────────

    def get_preset(self, name: str) -> Optional[SFXPreset]:
        """Preset by naam"""
        return self._presets.get(name)

    def list_presets(self,
                     category: Optional[SFXCategory] = None) -> List[SFXPreset]:
        """Sab presets return karo — optionally filtered by category"""
        presets = list(self._presets.values())
        if category:
            presets = [p for p in presets if p.category == category]
        return presets

    def search_presets(self, query: str) -> List[SFXPreset]:
        """Search by name/tags/description"""
        query = query.lower()
        results = []

        for preset in self._presets.values():
            # Check name, description, tags
            if (query in preset.name.lower()
                or query in preset.description.lower()
                or any(query in tag.lower() for tag in preset.tags)):
                results.append(preset)

        return results

    def get_categories(self) -> List[SFXCategory]:
        """Sab available categories"""
        return list(SFXCategory)

    def get_presets_by_category(self) -> Dict[str, List[SFXPreset]]:
        """Category-wise grouped presets"""
        grouped = {}
        for category in SFXCategory:
            grouped[category.value] = self.list_presets(category)
        return grouped

    # ── FAVORITES ─────────────────────────────────────────

    def add_favorite(self, preset_name: str) -> bool:
        """Preset ko favorites mein add karo"""
        if preset_name in self._presets or preset_name in self._custom_sfx:
            self._favorites.add(preset_name)
            self._save_favorites()
            logger.debug(f"⭐ Added to favorites: {preset_name}")
            return True
        return False

    def remove_favorite(self, preset_name: str) -> bool:
        """Favorites se hatao"""
        if preset_name in self._favorites:
            self._favorites.remove(preset_name)
            self._save_favorites()
            return True
        return False

    def is_favorite(self, preset_name: str) -> bool:
        return preset_name in self._favorites

    def get_favorites(self) -> List[str]:
        """Sab favorite names"""
        return sorted(list(self._favorites))

    def _load_favorites(self):
        """Favorites file load karo"""
        try:
            if self._favorites_file.exists():
                with open(self._favorites_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._favorites = set(data.get("favorites", []))
        except Exception as e:
            logger.debug(f"Favorites load: {e}")

    def _save_favorites(self):
        """Favorites file save karo"""
        try:
            with open(self._favorites_file, "w", encoding="utf-8") as f:
                json.dump({"favorites": sorted(list(self._favorites))}, f, indent=2)
        except Exception as e:
            logger.warning(f"Favorites save failed: {e}")

    # ── CUSTOM SFX IMPORT ─────────────────────────────────

    def import_custom_sfx(self, filepath: str,
                          name: Optional[str] = None) -> bool:
        """
        User-provided audio file ko library mein register karo.

        Args:
            filepath: Audio file path
            name    : Custom name (None = filename se auto)
        """
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return False

        if name is None:
            name = os.path.splitext(os.path.basename(filepath))[0]

        self._custom_sfx[name] = filepath
        logger.info(f"📁 Imported custom SFX: {name}")
        return True

    def get_custom_sfx(self, name: str) -> Optional[str]:
        """Custom SFX ka filepath"""
        return self._custom_sfx.get(name)

    def list_custom_sfx(self) -> List[str]:
        """Sab custom SFX names"""
        return list(self._custom_sfx.keys())


# ============================================================
# EFFECT CHAIN — Multiple Effects Sequentially
# ============================================================

class EffectChain:
    """
    🔗 Multiple effects ko sequentially apply karta hai.
    Guitar pedalboard jaise concept.

    Usage:
        chain = EffectChain()
        chain.add(EffectType.REVERB, preset=ReverbPreset.HALL)
        chain.add(EffectType.COMPRESSOR)
        processed = chain.process(audio)
    """

    def __init__(self):
        self._effects: List[Tuple[EffectType, Dict[str, Any]]] = []

    def add(self, effect: EffectType, **params) -> "EffectChain":
        """Effect add karo (chainable)"""
        self._effects.append((effect, params))
        return self  # Chain calls ke liye

    def clear(self):
        """Sab effects hatao"""
        self._effects.clear()

    def process(self, audio: AudioSegment) -> AudioSegment:
        """Sab effects sequentially apply karo"""
        if not PYDUB_AVAILABLE:
            return audio

        result = audio
        fx     = AudioEffectsProcessor

        for effect, params in self._effects:
            try:
                if effect == EffectType.REVERB:
                    preset = params.get("preset", ReverbPreset.HALL)
                    wet    = params.get("wet")
                    result = fx.reverb(result, preset, wet)

                elif effect == EffectType.ECHO:
                    result = fx.echo(
                        result,
                        delay_ms=params.get("delay_ms", 300),
                        decay   =params.get("decay", 0.5),
                        repeats =params.get("repeats", 3),
                    )

                elif effect == EffectType.DELAY:
                    result = fx.delay(
                        result,
                        delay_ms=params.get("delay_ms", 250),
                        wet     =params.get("wet", 0.5),
                    )

                elif effect == EffectType.LOWPASS:
                    result = fx.lowpass_filter(result, params.get("cutoff_hz", 1000))

                elif effect == EffectType.HIGHPASS:
                    result = fx.highpass_filter(result, params.get("cutoff_hz", 200))

                elif effect == EffectType.BANDPASS:
                    result = fx.bandpass_filter(
                        result,
                        low_hz =params.get("low_hz", 300),
                        high_hz=params.get("high_hz", 3000),
                    )

                elif effect == EffectType.COMPRESSOR:
                    result = fx.compressor(
                        result,
                        threshold_db=params.get("threshold_db", -20.0),
                        ratio       =params.get("ratio", 4.0),
                    )

                elif effect == EffectType.NORMALIZE:
                    result = fx.normalize(result, params.get("target_db", -3.0))

                elif effect == EffectType.DISTORTION:
                    result = fx.distortion(
                        result,
                        gain=params.get("gain", 10.0),
                        mix =params.get("mix", 0.7),
                    )

                elif effect == EffectType.BITCRUSH:
                    result = fx.bitcrush(result, params.get("bit_depth", 4))

                elif effect == EffectType.TREMOLO:
                    result = fx.tremolo(
                        result,
                        rate_hz=params.get("rate_hz", 5.0),
                        depth  =params.get("depth", 0.5),
                    )

                elif effect == EffectType.PITCH_SHIFT:
                    result = fx.pitch_shift(result, params.get("semitones", 0.0))

                elif effect == EffectType.TIME_STRETCH:
                    result = fx.time_stretch(result, params.get("factor", 1.0))

            except Exception as e:
                logger.error(f"Effect {effect.value} failed in chain: {e}")

        return result

    def __len__(self):
        return len(self._effects)


# ============================================================
# MAIN SOUND EFFECTS ENGINE
# ============================================================

class SoundEffectsEngine:
    """
    🔊 Main Sound Effects Engine

    Sub-systems ko orchestrate karta hai:
    - SFX synthesis (SFXSynthesizer)
    - Effects processing (AudioEffectsProcessor)
    - Voice effects (VoiceEffectsProcessor)
    - Library management (SFXLibrary)
    """

    def __init__(self, config: Optional[Dict] = None):
        # Config setup
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # Output directory
        audio_cfg = self.config.get("audio", {})
        base_dir  = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)
        )))
        self.output_dir = audio_cfg.get(
            "sfx_output_dir",
            os.path.join(base_dir, "assets", "audio", "sfx", "generated")
        )
        ensure_dir(self.output_dir)

        # Sub-systems
        self.synthesizer   = SFXSynthesizer()
        self.effects       = AudioEffectsProcessor()
        self.voice_effects = VoiceEffectsProcessor()
        self.library       = SFXLibrary()

        # Stats
        self.total_generated = 0
        self.total_processed = 0

        logger.info(
            f"🔊 SoundEffectsEngine initialized "
            f"({len(self.library.list_presets())} presets available)"
        )

    # ── SFX GENERATION ────────────────────────────────────

    def generate_sfx(self, preset_name: str,
                     output_path: Optional[str] = None) -> Optional[AudioSegment]:
        """
        Preset se SFX generate karo.

        Args:
            preset_name : Preset ka naam (library.list_presets() se dekho)
            output_path : Save karne ki jagah (None = return only, no save)

        Returns:
            AudioSegment agar success
        """
        if not PYDUB_AVAILABLE:
            logger.error("pydub required")
            return None

        # Generator method map — preset name to synthesizer method
        generators = {
            "click"        : self.synthesizer.generate_click,
            "beep"         : self.synthesizer.generate_beep,
            "notification" : self.synthesizer.generate_notification,
            "success"      : self.synthesizer.generate_success,
            "error"        : self.synthesizer.generate_error,
            "alarm"        : self.synthesizer.generate_alarm,
            "impact"       : self.synthesizer.generate_impact,
            "explosion"    : self.synthesizer.generate_explosion,
            "glass_break"  : self.synthesizer.generate_glass_break,
            "thunder"      : self.synthesizer.generate_thunder,
            "rain"         : self.synthesizer.generate_rain,
            "wind"         : self.synthesizer.generate_wind,
            "whoosh"       : self.synthesizer.generate_whoosh,
            "laser"        : self.synthesizer.generate_laser,
            "footstep"     : self.synthesizer.generate_footstep,
            "heartbeat"    : self.synthesizer.generate_heartbeat,
            "coin"         : self.synthesizer.generate_coin,
            "power_up"     : self.synthesizer.generate_power_up,
            "power_down"   : self.synthesizer.generate_power_down,
        }

        # Preset exist karta hai?
        gen_func = generators.get(preset_name)
        if gen_func is None:
            logger.error(f"Unknown SFX preset: {preset_name}")
            return None

        # Generate karo
        try:
            audio = gen_func()
            if audio is None:
                return None

            # Save agar path diya
            if output_path:
                ensure_dir(os.path.dirname(output_path))
                audio.export(output_path, format="wav")
                logger.info(f"🎵 Generated: {preset_name} → {os.path.basename(output_path)}")
            else:
                logger.debug(f"🎵 Generated: {preset_name} (in-memory)")

            self.total_generated += 1
            return audio

        except Exception as e:
            logger.error(f"SFX generation '{preset_name}' failed: {e}")
            return None

    def generate_all_presets(self, output_dir: Optional[str] = None) -> Dict[str, str]:
        """
        Sab presets generate karke files banao.
        Sample library banane ke liye useful.

        Returns:
            Dict[preset_name → filepath]
        """
        if output_dir is None:
            output_dir = self.output_dir
        ensure_dir(output_dir)

        results = {}
        presets = self.library.list_presets()

        logger.info(f"🎵 Generating {len(presets)} presets...")

        for preset in presets:
            output_path = os.path.join(output_dir, f"{preset.name}.wav")
            audio = self.generate_sfx(preset.name, output_path)
            if audio is not None:
                results[preset.name] = output_path

        logger.info(f"✅ Generated {len(results)}/{len(presets)} presets")
        return results

    # ── EFFECT APPLICATION ────────────────────────────────

    def apply_effect(self,
                     audio: AudioSegment,
                     effect: EffectType,
                     **params) -> Optional[AudioSegment]:
        """
        Single effect apply karo audio pe.
        Advanced use ke liye EffectChain use karo.
        """
        chain = EffectChain()
        chain.add(effect, **params)
        result = chain.process(audio)
        self.total_processed += 1
        return result

    def apply_voice_effect(self,
                           audio: AudioSegment,
                           effect: VoiceEffect) -> AudioSegment:
        """Voice modification apply karo"""
        result = self.voice_effects.apply(audio, effect)
        self.total_processed += 1
        return result

    def process_file(self,
                     input_path: str,
                     output_path: str,
                     chain: EffectChain) -> EffectResult:
        """
        Audio file load karo, effect chain apply karo, save karo.

        Args:
            input_path : Input audio file
            output_path: Output audio file
            chain      : EffectChain object
        """
        result = EffectResult()
        start  = time.time()

        if not PYDUB_AVAILABLE:
            result.error = "pydub not available"
            return result

        try:
            # Load
            audio = AudioSegment.from_file(input_path)

            # Process
            processed = chain.process(audio)

            # Save
            ensure_dir(os.path.dirname(output_path))
            processed.export(output_path, format="wav")

            result.success        = True
            result.output_path    = output_path
            result.duration       = len(processed) / 1000.0
            result.file_size      = get_file_size(output_path)
            result.effect_used    = f"chain ({len(chain)} effects)"
            result.processing_time= time.time() - start

            logger.info(
                f"✅ Processed: {os.path.basename(input_path)} → "
                f"{os.path.basename(output_path)} ({result.processing_time:.2f}s)"
            )

        except Exception as e:
            result.error = str(e)
            logger.error(f"❌ Processing failed: {e}")

        return result

    # ── AMBIENCE LAYERING ─────────────────────────────────

    def create_ambience(self,
                        layers: List[Tuple[str, float]],
                        duration_ms: int = 5000,
                        output_path: Optional[str] = None) -> Optional[AudioSegment]:
        """
        Multiple SFX layer karke ambience banao.

        Args:
            layers      : List of (preset_name, volume) tuples
            duration_ms : Ambience ki total duration
            output_path : Save location

        Example:
            engine.create_ambience([
                ("rain", 0.6),
                ("wind", 0.4),
                ("thunder", 0.3),
            ], duration_ms=10000)
        """
        if not PYDUB_AVAILABLE or not layers:
            return None

        try:
            # Base silent track
            base = AudioSegment.silent(duration=duration_ms)

            for preset_name, volume in layers:
                # Generate SFX
                sfx = self.generate_sfx(preset_name)
                if sfx is None:
                    logger.warning(f"Skipping unknown SFX: {preset_name}")
                    continue

                # Loop karo agar zaroori ho
                while len(sfx) < duration_ms:
                    sfx = sfx + sfx

                sfx = sfx[:duration_ms]

                # Volume adjust
                vol_db = 20 * math.log10(max(0.01, volume))
                sfx    = sfx + vol_db

                # Overlay
                base = base.overlay(sfx)

            # Save
            if output_path:
                ensure_dir(os.path.dirname(output_path))
                base.export(output_path, format="wav")
                logger.info(f"🌊 Ambience created: {os.path.basename(output_path)}")

            return base

        except Exception as e:
            logger.error(f"Ambience creation failed: {e}")
            return None

    # ── UTILITIES ─────────────────────────────────────────

    def get_stats(self) -> Dict:
        """Engine statistics"""
        return {
            "total_generated"    : self.total_generated,
            "total_processed"    : self.total_processed,
            "preset_count"       : len(self.library.list_presets()),
            "favorites_count"    : len(self.library.get_favorites()),
            "custom_sfx_count"   : len(self.library.list_custom_sfx()),
            "categories"         : [c.value for c in SFXCategory],
            "effect_types"       : [e.value for e in EffectType],
            "voice_effects"      : [v.value for v in VoiceEffect],
            "reverb_presets"     : [r.label for r in ReverbPreset],
            "backends"           : {
                "pydub"     : PYDUB_AVAILABLE,
                "soundfile" : SOUNDFILE_AVAILABLE,
                "librosa"   : LIBROSA_AVAILABLE,
                "scipy"     : SCIPY_AVAILABLE,
            }
        }


# ============================================================
# TEST FUNCTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")
    print_banner(
        "🔊 Sound Effects Engine Test",
        "SFX generation, audio effects, voice modification"
    )

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))

    output_dir = os.path.join(base_dir, "temp", "sfx_tests")
    ensure_dir(output_dir)

    # ============================================================
    # Test 1: Initialize
    # ============================================================
    print_section("Test 1: Initialize Sound Effects Engine")

    engine = SoundEffectsEngine()
    stats  = engine.get_stats()

    print(f"  Presets available : {stats['preset_count']}")
    print(f"  Categories        : {len(stats['categories'])}")
    print(f"  Effect types      : {len(stats['effect_types'])}")
    print(f"  Voice effects     : {len(stats['voice_effects'])}")
    print(f"  Reverb presets    : {len(stats['reverb_presets'])}")
    print(f"\n  Backends:")
    for name, avail in stats['backends'].items():
        status = "✅" if avail else "❌"
        print(f"    {status} {name}")

    if not PYDUB_AVAILABLE:
        print("\n❌ pydub required - cannot continue")
        sys.exit(1)

    # ============================================================
    # Test 2: Library — Preset Catalog
    # ============================================================
    print_section("Test 2: SFX Preset Library")

    grouped = engine.library.get_presets_by_category()

    for category, presets in grouped.items():
        if presets:
            print(f"\n  📂 {category.upper()} ({len(presets)}):")
            for p in presets:
                print(f"     • {p.name:15s} — {p.description}")

    # ============================================================
    # Test 3: Search Presets
    # ============================================================
    print_section("Test 3: Search Presets")

    search_queries = ["ui", "weather", "game", "impact"]

    for query in search_queries:
        results = engine.library.search_presets(query)
        print(f"\n  🔍 Search '{query}': {len(results)} results")
        for r in results[:3]:
            print(f"     • {r.name} ({r.category.value})")

    # ============================================================
    # Test 4: Generate Individual SFX
    # ============================================================
    print_section("Test 4: Generate Individual SFX Samples")

    samples_to_generate = [
        "click", "notification", "success", "error",
        "impact", "explosion", "whoosh", "laser",
        "coin", "power_up", "heartbeat", "thunder",
    ]

    print(f"  Generating {len(samples_to_generate)} samples...")
    generated = 0

    for name in samples_to_generate:
        out_path = os.path.join(output_dir, f"sfx_{name}.wav")
        audio    = engine.generate_sfx(name, out_path)

        if audio is not None:
            size = format_bytes(get_file_size(out_path))
            duration = len(audio) / 1000.0
            print(f"    ✅ {name:15s}: {duration:.2f}s, {size}")
            generated += 1
        else:
            print(f"    ❌ {name}: failed")

    print(f"\n  Total: {generated}/{len(samples_to_generate)} generated")

    # ============================================================
    # Test 5: Audio Effects — Reverb
    # ============================================================
    print_section("Test 5: Reverb Effects")

    # Base audio for testing
    base_audio = engine.synthesizer.sine_tone(freq=440, duration_ms=500, volume=0.5)

    if base_audio:
        # Different reverb presets
        for preset in [ReverbPreset.ROOM, ReverbPreset.HALL, ReverbPreset.CATHEDRAL]:
            reverb_audio = engine.effects.reverb(base_audio, preset)
            out_path     = os.path.join(output_dir, f"reverb_{preset.label}.wav")
            reverb_audio.export(out_path, format="wav")

            duration = len(reverb_audio) / 1000.0
            size     = format_bytes(get_file_size(out_path))
            print(f"    ✅ Reverb {preset.label:10s}: {duration:.2f}s, {size}")

    # ============================================================
    # Test 6: Filter Effects
    # ============================================================
    print_section("Test 6: Filter Effects")

    # White noise for demonstrating filters
    noise_audio = engine.synthesizer.noise(duration_ms=1000, volume=0.4)

    if noise_audio:
        filters = [
            ("lowpass_500Hz",  lambda a: engine.effects.lowpass_filter(a, 500)),
            ("highpass_2000Hz", lambda a: engine.effects.highpass_filter(a, 2000)),
            ("bandpass_500_2000", lambda a: engine.effects.bandpass_filter(a, 500, 2000)),
        ]

        for name, filter_func in filters:
            filtered = filter_func(noise_audio)
            out_path = os.path.join(output_dir, f"filter_{name}.wav")
            filtered.export(out_path, format="wav")
            print(f"    ✅ {name}")

    # ============================================================
    # Test 7: Distortion & Bitcrush
    # ============================================================
    print_section("Test 7: Distortion Effects")

    # Sine wave to distort
    clean = engine.synthesizer.sine_tone(freq=440, duration_ms=500, volume=0.3)

    if clean:
        # Distortion
        distorted = engine.effects.distortion(clean, gain=15, mix=0.8)
        distorted.export(os.path.join(output_dir, "distortion.wav"), format="wav")
        print(f"    ✅ Distortion applied")

        # Bitcrush
        crushed = engine.effects.bitcrush(clean, bit_depth=3)
        crushed.export(os.path.join(output_dir, "bitcrush.wav"), format="wav")
        print(f"    ✅ Bitcrush applied (3-bit)")

    # ============================================================
    # Test 8: Echo & Delay
    # ============================================================
    print_section("Test 8: Time-based Effects")

    click = engine.synthesizer.generate_click()

    if click:
        # Echo
        echoed = engine.effects.echo(click, delay_ms=200, decay=0.6, repeats=5)
        echoed.export(os.path.join(output_dir, "echo.wav"), format="wav")
        print(f"    ✅ Echo: 5 repeats, 200ms delay")

        # Delay
        delayed = engine.effects.delay(click, delay_ms=500, wet=0.7)
        delayed.export(os.path.join(output_dir, "delay.wav"), format="wav")
        print(f"    ✅ Delay: 500ms, 70% wet")

    # ============================================================
    # Test 9: Pitch Shift
    # ============================================================
    print_section("Test 9: Pitch Shift")

    tone = engine.synthesizer.sine_tone(freq=440, duration_ms=500, volume=0.5)

    if tone:
        pitch_variants = [
            ("pitch_up_5",   +5),
            ("pitch_up_12",  +12),
            ("pitch_down_5", -5),
            ("pitch_down_12",-12),
        ]

        for name, semitones in pitch_variants:
            shifted = engine.effects.pitch_shift(tone, semitones)
            shifted.export(os.path.join(output_dir, f"{name}.wav"), format="wav")
            marker = "up" if semitones > 0 else "down"
            print(f"    ✅ Pitch {marker} {abs(semitones)} semitones")

    # ============================================================
    # Test 10: Effect Chain — Multiple Effects
    # ============================================================
    print_section("Test 10: Effect Chain (Multiple Effects)")

    click = engine.synthesizer.generate_click()

    if click:
        # Guitar pedal style chain
        chain = EffectChain()
        chain.add(EffectType.PITCH_SHIFT, semitones=-3)
        chain.add(EffectType.DISTORTION, gain=8, mix=0.6)
        chain.add(EffectType.REVERB, preset=ReverbPreset.HALL)
        chain.add(EffectType.NORMALIZE, target_db=-3.0)

        print(f"    Chain has {len(chain)} effects")

        processed = chain.process(click)
        out_path  = os.path.join(output_dir, "effect_chain.wav")
        processed.export(out_path, format="wav")

        size = format_bytes(get_file_size(out_path))
        print(f"    ✅ Chain processed: {size}")

    # ============================================================
    # Test 11: Voice Effects
    # ============================================================
    print_section("Test 11: Voice Effects")

    # TTS audio dhundo pehle
    tts_dir  = os.path.join(base_dir, "temp", "tts_tests")
    tts_file = None

    if os.path.exists(tts_dir):
        for f in os.listdir(tts_dir):
            if f.endswith(".wav"):
                tts_file = os.path.join(tts_dir, f)
                break

    if tts_file:
        print(f"    Using TTS file: {os.path.basename(tts_file)}")
        source_audio = AudioSegment.from_file(tts_file)
    else:
        print("    ⚠️  No TTS audio found, using synth tone")
        source_audio = engine.synthesizer.sine_tone(440, 1500, 0.5)

    if source_audio:
        voice_variants = [
            VoiceEffect.ROBOT,
            VoiceEffect.CHIPMUNK,
            VoiceEffect.DEEP,
            VoiceEffect.RADIO,
            VoiceEffect.UNDERWATER,
            VoiceEffect.GHOST,
            VoiceEffect.MONSTER,
        ]

        for effect in voice_variants:
            result   = engine.apply_voice_effect(source_audio, effect)
            out_path = os.path.join(output_dir, f"voice_{effect.value}.wav")
            result.export(out_path, format="wav")

            size = format_bytes(get_file_size(out_path))
            print(f"    ✅ Voice {effect.value:12s}: {size}")

    # ============================================================
    # Test 12: Ambience Layering
    # ============================================================
    print_section("Test 12: Ambience Creation (Layering)")

    ambient_scenes = [
        ("storm_ambience", [
            ("rain", 0.6),
            ("wind", 0.4),
            ("thunder", 0.4),
        ]),
        ("peaceful_ambience", [
            ("rain", 0.3),
            ("wind", 0.2),
        ]),
    ]

    for scene_name, layers in ambient_scenes:
        out_path = os.path.join(output_dir, f"{scene_name}.wav")
        result   = engine.create_ambience(
            layers=layers,
            duration_ms=5000,
            output_path=out_path
        )

        if result:
            size = format_bytes(get_file_size(out_path))
            duration = len(result) / 1000.0
            print(f"    ✅ {scene_name}: {duration:.1f}s, {size}")
            print(f"       Layers: {', '.join(f'{n}({v:.1f})' for n, v in layers)}")

    # ============================================================
    # Test 13: Favorites Management
    # ============================================================
    print_section("Test 13: Favorites System")

    favorites_to_add = ["click", "whoosh", "explosion", "success"]

    for name in favorites_to_add:
        engine.library.add_favorite(name)

    favs = engine.library.get_favorites()
    print(f"    ⭐ Favorites: {len(favs)}")
    for f in favs:
        marker = "⭐" if engine.library.is_favorite(f) else "  "
        print(f"      {marker} {f}")

    # ============================================================
    # Test 14: Final Statistics
    # ============================================================
    print_section("Test 14: Final Statistics")

    stats = engine.get_stats()
    print(f"  Total SFX generated : {stats['total_generated']}")
    print(f"  Total effects applied: {stats['total_processed']}")
    print(f"  Presets in library  : {stats['preset_count']}")
    print(f"  Favorites           : {stats['favorites_count']}")

    # ============================================================
    # Info
    # ============================================================
    print_section("Output Files")
    print(f"  📁 All SFX files saved in:")
    print(f"     {output_dir}")
    print(f"\n  🎧 Open to listen:")
    print(f"     start {output_dir}")

    print_banner(
        "✅ Sound Effects Engine Ready!",
        f"{stats['total_generated']} SFX generated | "
        f"{stats['total_processed']} effects applied"
    )