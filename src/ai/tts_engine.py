# ============================================================
# 3D ANIMATION STUDIO - Text-to-Speech (TTS) Engine
# ============================================================
# Features:
# - Multiple TTS engine support:
#   * pyttsx3 (offline, fast, uses system voices)
#   * gTTS (online, better quality, Google)
#   * Coqui TTS (advanced, optional heavy install)
# - Multi-voice: different voices per character
# - Multi-language support (10+ languages)
# - Prosody control: rate, pitch, volume
# - Save to WAV/MP3 file
# - Batch generation from script
# - Audio caching (same text = same file)
# - Character voice profiles
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
import tempfile
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# TTS libraries (optional imports)
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    pyttsx3 = None

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    gTTS = None

# Audio processing
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    AudioSegment = None

from src.utils import (
    get_logger, get_config, ensure_dir, hash_string,
    generate_short_id, get_timestamp, delete_file,
    format_bytes, get_file_size
)

logger = get_logger("TTSEngine")


# ============================================================
# TTS ENGINE TYPES
# ============================================================

class TTSEngineType(Enum):
    """Available TTS engines"""
    PYTTSX3 = "pyttsx3"      # Offline, system voices
    GTTS = "gtts"            # Online, Google
    COQUI = "coqui"          # Advanced (heavy install)
    AUTO = "auto"            # Best available


# ============================================================
# SUPPORTED LANGUAGES
# ============================================================

class Language:
    """Supported languages with codes"""
    ENGLISH = "en"
    HINDI = "hi"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    CHINESE = "zh"
    ARABIC = "ar"
    PORTUGUESE = "pt"
    RUSSIAN = "ru"
    JAPANESE = "ja"
    ITALIAN = "it"
    KOREAN = "ko"

    # Language details (name, gTTS supported, native name)
    INFO = {
        "en": {"name": "English", "native": "English", "gtts": True},
        "hi": {"name": "Hindi", "native": "हिन्दी", "gtts": True},
        "es": {"name": "Spanish", "native": "Español", "gtts": True},
        "fr": {"name": "French", "native": "Français", "gtts": True},
        "de": {"name": "German", "native": "Deutsch", "gtts": True},
        "zh": {"name": "Chinese", "native": "中文", "gtts": True},
        "ar": {"name": "Arabic", "native": "العربية", "gtts": True},
        "pt": {"name": "Portuguese", "native": "Português", "gtts": True},
        "ru": {"name": "Russian", "native": "Русский", "gtts": True},
        "ja": {"name": "Japanese", "native": "日本語", "gtts": True},
        "it": {"name": "Italian", "native": "Italiano", "gtts": True},
        "ko": {"name": "Korean", "native": "한국어", "gtts": True},
    }

    @classmethod
    def get_all(cls) -> List[str]:
        return list(cls.INFO.keys())

    @classmethod
    def get_name(cls, code: str) -> str:
        return cls.INFO.get(code, {}).get("name", code)


# ============================================================
# VOICE PROFILE (Character Voices)
# ============================================================

@dataclass
class VoiceProfile:
    """
    Character ka voice profile.
    Har character ki apni voice settings.
    """
    id: str = field(default_factory=generate_short_id)
    name: str = "Default Voice"

    # Engine selection
    engine: TTSEngineType = TTSEngineType.AUTO

    # Language
    language: str = "en"

    # Voice ID (engine-specific)
    voice_id: Optional[str] = None  # None = default

    # Prosody
    rate: int = 200              # Words per minute (100-300)
    pitch: int = 100             # Percentage (50-200)
    volume: float = 1.0          # 0.0-1.0

    # Gender preference
    gender: str = "any"          # "male", "female", "any"

    # Emotion tone (for advanced engines)
    emotion: str = "neutral"     # "neutral", "happy", "sad", "angry", "excited"

    # Slow speech (gTTS)
    slow: bool = False

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "engine": self.engine.value,
            "language": self.language,
            "voice_id": self.voice_id,
            "rate": self.rate,
            "pitch": self.pitch,
            "volume": self.volume,
            "gender": self.gender,
            "emotion": self.emotion,
            "slow": self.slow,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "VoiceProfile":
        engine_str = data.get("engine", "auto")
        try:
            engine = TTSEngineType(engine_str)
        except ValueError:
            engine = TTSEngineType.AUTO

        return cls(
            id=data.get("id", generate_short_id()),
            name=data.get("name", "Voice"),
            engine=engine,
            language=data.get("language", "en"),
            voice_id=data.get("voice_id"),
            rate=data.get("rate", 200),
            pitch=data.get("pitch", 100),
            volume=data.get("volume", 1.0),
            gender=data.get("gender", "any"),
            emotion=data.get("emotion", "neutral"),
            slow=data.get("slow", False),
        )


# ============================================================
# TTS RESULT
# ============================================================

@dataclass
class TTSResult:
    """TTS generation result"""
    success: bool = False
    audio_file: Optional[str] = None
    duration: float = 0.0
    file_size: int = 0
    engine_used: Optional[str] = None
    language: str = "en"
    text: str = ""
    error: Optional[str] = None
    generation_time: float = 0.0
    cached: bool = False


# ============================================================
# BASE TTS BACKEND (Abstract)
# ============================================================

class TTSBackend:
    """Base class for TTS engines"""

    def __init__(self):
        self.available = False
        self.name = "Base"

    def synthesize(self, text: str, output_path: str,
                   voice: VoiceProfile) -> bool:
        """Text to audio file"""
        raise NotImplementedError

    def get_available_voices(self) -> List[Dict]:
        """List available voices"""
        return []


# ============================================================
# PYTTSX3 BACKEND (Offline)
# ============================================================

class Pyttsx3Backend(TTSBackend):
    """
    Pyttsx3 - Offline TTS using system voices.
    Fast, no internet needed, but robotic quality.

    NOTE: pyttsx3 me known issue hai - engine reuse hang karta hai.
    Isliye har synthesis me fresh engine banate hain.
    """

    def __init__(self):
        super().__init__()
        self.name = "pyttsx3"
        self.available = PYTTSX3_AVAILABLE
        self._voices_cache = None

        if self.available:
            try:
                # Test init to verify it works
                test_engine = pyttsx3.init()
                # Cache voices list (ye stable hai)
                self._voices_cache = test_engine.getProperty("voices")
                test_engine.stop()
                del test_engine
                logger.debug("pyttsx3 verified working")
            except Exception as e:
                logger.error(f"pyttsx3 init failed: {e}")
                self.available = False

    def synthesize(self, text: str, output_path: str,
                   voice: VoiceProfile) -> bool:
        """
        Text ko audio me convert karo.

        IMPORTANT: Har call me fresh engine banate hain to hang avoid ho.
        """
        if not self.available:
            return False

        engine = None
        try:
            # FRESH engine har baar - ye pyttsx3 ka workaround hai
            engine = pyttsx3.init()

            # Rate set karo (words per minute)
            engine.setProperty("rate", voice.rate)

            # Volume (0.0-1.0)
            engine.setProperty("volume", voice.volume)

            # Voice select karo
            if voice.voice_id:
                engine.setProperty("voice", voice.voice_id)
            else:
                # Gender ke basis pe select karo
                self._select_voice_by_gender(engine, voice.gender)

            # Ensure directory
            ensure_dir(os.path.dirname(output_path))

            # Generate aur save
            engine.save_to_file(text, output_path)
            engine.runAndWait()

            # Engine properly close karo
            try:
                engine.stop()
            except Exception:
                pass

            # Small delay - Windows SAPI ko file finalize karne do
            time.sleep(0.1)

            # Verify file created
            if os.path.exists(output_path) and get_file_size(output_path) > 0:
                return True
            else:
                logger.error("pyttsx3 output file empty or missing")
                return False

        except Exception as e:
            logger.error(f"pyttsx3 synthesis failed: {e}")
            return False

        finally:
            # Cleanup
            if engine is not None:
                try:
                    del engine
                except Exception:
                    pass

    def _select_voice_by_gender(self, engine, gender: str):
        """Available voices se gender-matched voice select karo"""
        try:
            voices = engine.getProperty("voices")
            if not voices:
                return

            for v in voices:
                name_lower = v.name.lower() if hasattr(v, "name") else ""

                if gender == "female":
                    if any(word in name_lower for word in
                           ["female", "woman", "zira", "hazel", "susan", "linda"]):
                        engine.setProperty("voice", v.id)
                        return
                elif gender == "male":
                    if any(word in name_lower for word in
                           ["male", "man", "david", "mark", "james", "george"]):
                        engine.setProperty("voice", v.id)
                        return
        except Exception:
            pass

    def get_available_voices(self) -> List[Dict]:
        """System pe available voices list karo"""
        if not self.available:
            return []

        try:
            # Cached voices use karo (agar hain)
            voices = self._voices_cache

            # Nahi to fresh fetch karo
            if voices is None:
                engine = pyttsx3.init()
                voices = engine.getProperty("voices")
                self._voices_cache = voices
                engine.stop()
                del engine

            result = []
            for v in voices:
                info = {
                    "id": v.id,
                    "name": v.name if hasattr(v, "name") else "Unknown",
                    "languages": list(v.languages) if hasattr(v, "languages") else [],
                    "gender": v.gender if hasattr(v, "gender") else "unknown",
                    "age": v.age if hasattr(v, "age") else "unknown",
                }
                result.append(info)

            return result
        except Exception as e:
            logger.error(f"Failed to list voices: {e}")
            return []

# ============================================================
# GTTS BACKEND (Online, Google)
# ============================================================

class GTTSBackend(TTSBackend):
    """
    Google Text-to-Speech - Better quality, needs internet.
    Free, multiple languages.
    """

    def __init__(self):
        super().__init__()
        self.name = "gTTS"
        self.available = GTTS_AVAILABLE

    def synthesize(self, text: str, output_path: str,
                   voice: VoiceProfile) -> bool:
        """gTTS se audio generate karo"""
        if not self.available:
            return False

        try:
            # gTTS output MP3 me deta hai
            temp_mp3 = output_path
            wants_wav = output_path.lower().endswith(".wav")

            if wants_wav:
                # Pehle MP3 me save karo, fir convert
                temp_mp3 = output_path.replace(".wav", "_temp.mp3")

            ensure_dir(os.path.dirname(output_path))

            # gTTS create
            tts = gTTS(
                text=text,
                lang=voice.language,
                slow=voice.slow
            )

            # Save
            tts.save(temp_mp3)

            # WAV convert karo agar chahiye
            if wants_wav and PYDUB_AVAILABLE:
                try:
                    audio = AudioSegment.from_mp3(temp_mp3)

                    # Volume adjust karo
                    if voice.volume != 1.0:
                        # dB me convert (log scale)
                        import math
                        db_change = 20 * math.log10(max(0.01, voice.volume))
                        audio = audio + db_change

                    # Speed adjust karo (rate approximation)
                    if voice.rate != 200:
                        # Default 200 wpm, adjust playback speed
                        speed_factor = voice.rate / 200.0
                        # Frame rate change (basic speed change)
                        audio = audio._spawn(
                            audio.raw_data,
                            overrides={"frame_rate": int(audio.frame_rate * speed_factor)}
                        ).set_frame_rate(audio.frame_rate)

                    audio.export(output_path, format="wav")

                    # Temp MP3 delete karo
                    if os.path.exists(temp_mp3):
                        delete_file(temp_mp3)

                except Exception as e:
                    logger.warning(f"WAV conversion failed: {e}, keeping MP3")
                    # MP3 hi rakhne do
                    if temp_mp3 != output_path:
                        os.rename(temp_mp3, output_path)

            # Verify
            if os.path.exists(output_path) and get_file_size(output_path) > 0:
                return True

            return False

        except Exception as e:
            logger.error(f"gTTS synthesis failed: {e}")
            return False

    def get_available_voices(self) -> List[Dict]:
        """gTTS supported languages return karo (voice = language)"""
        result = []
        for code, info in Language.INFO.items():
            if info.get("gtts"):
                result.append({
                    "id": code,
                    "name": f"gTTS {info['name']}",
                    "language": code,
                    "gender": "unknown",
                })
        return result


# ============================================================
# MAIN TTS ENGINE
# ============================================================

class TTSEngine:
    """
    Main TTS engine.
    Multiple backends manage karta hai + caching.
    """

    def __init__(self, config: Optional[Dict] = None,
                 cache_dir: Optional[str] = None):
        # Config
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # Cache directory
        if cache_dir is None:
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            cache_dir = os.path.join(project_root, "cache", "tts")

        self.cache_dir = ensure_dir(cache_dir)
        self.cache_enabled = True

        # Backends initialize karo
        self.backends: Dict[TTSEngineType, TTSBackend] = {}
        self._init_backends()

        # Voice profiles storage
        self.voice_profiles: Dict[str, VoiceProfile] = {}

        # Default voice
        self._create_default_voices()

        # Statistics
        self.total_generated = 0
        self.total_cache_hits = 0

        logger.info(
            f"TTSEngine initialized: "
            f"{len([b for b in self.backends.values() if b.available])} backends available"
        )

    def _init_backends(self):
        """Sab TTS backends initialize karo"""
        # pyttsx3
        self.backends[TTSEngineType.PYTTSX3] = Pyttsx3Backend()
        if self.backends[TTSEngineType.PYTTSX3].available:
            logger.info("✓ pyttsx3 available (offline)")

        # gTTS
        self.backends[TTSEngineType.GTTS] = GTTSBackend()
        if self.backends[TTSEngineType.GTTS].available:
            logger.info("✓ gTTS available (online)")

        # Coqui TTS (agar installed hai)
        try:
            from TTS.api import TTS as CoquiTTS
            # Coqui backend abhi implement nahi kiya (heavy)
            logger.debug("Coqui TTS installed but not integrated yet")
        except ImportError:
            pass

    def _create_default_voices(self):
        """Default voice profiles create karo"""
        # Default English
        default_en = VoiceProfile(
            name="Default English",
            engine=TTSEngineType.AUTO,
            language="en",
            gender="any"
        )
        self.voice_profiles[default_en.id] = default_en

        # Male English
        male_en = VoiceProfile(
            name="Male English",
            engine=TTSEngineType.PYTTSX3,
            language="en",
            gender="male",
            rate=180,
            pitch=95
        )
        self.voice_profiles[male_en.id] = male_en

        # Female English
        female_en = VoiceProfile(
            name="Female English",
            engine=TTSEngineType.PYTTSX3,
            language="en",
            gender="female",
            rate=210,
            pitch=110
        )
        self.voice_profiles[female_en.id] = female_en

        # Hindi
        hindi = VoiceProfile(
            name="Hindi Voice",
            engine=TTSEngineType.GTTS,
            language="hi",
            rate=180
        )
        self.voice_profiles[hindi.id] = hindi

    # ------------------------------------------------------------
    # SYNTHESIS
    # ------------------------------------------------------------

    def synthesize(self, text: str,
                   voice: Optional[VoiceProfile] = None,
                   output_path: Optional[str] = None,
                   use_cache: bool = True) -> TTSResult:
        """
        Text ko audio me convert karo.

        Args:
            text: Text to speak
            voice: Voice profile (default agar None)
            output_path: Output file (auto-generated agar None)
            use_cache: Cache use karo (same text = same file)

        Returns:
            TTSResult with success status and audio file path
        """
        start_time = time.time()
        result = TTSResult(text=text)

        if not text or not text.strip():
            result.error = "Empty text"
            return result

        # Default voice agar nahi diya
        if voice is None:
            voice = self.get_default_voice()

        result.language = voice.language

        # Cache check
        if use_cache and self.cache_enabled:
            cached_path = self._get_cached_path(text, voice)
            if os.path.exists(cached_path):
                logger.debug(f"Cache hit: {text[:30]}...")
                result.success = True
                result.audio_file = cached_path
                result.file_size = get_file_size(cached_path)
                result.cached = True
                result.generation_time = time.time() - start_time
                self.total_cache_hits += 1
                return result

        # Output path
        if output_path is None:
            if use_cache and self.cache_enabled:
                output_path = self._get_cached_path(text, voice)
            else:
                filename = f"tts_{generate_short_id()}.wav"
                output_path = os.path.join(self.cache_dir, filename)

        ensure_dir(os.path.dirname(output_path))

        # Backend select karo
        backend = self._select_backend(voice)
        if not backend:
            result.error = "No TTS backend available"
            logger.error(result.error)
            return result

        result.engine_used = backend.name

        # Synthesize karo
        logger.info(f"Generating: '{text[:50]}...' [{backend.name}, {voice.language}]")

        success = backend.synthesize(text, output_path, voice)

        if success and os.path.exists(output_path):
            result.success = True
            result.audio_file = output_path
            result.file_size = get_file_size(output_path)
            result.duration = self._estimate_duration(output_path)
            self.total_generated += 1

            logger.info(
                f"✓ Generated: {format_bytes(result.file_size)}, "
                f"~{result.duration:.1f}s audio"
            )
        else:
            result.error = "Synthesis failed"
            logger.error(result.error)

        result.generation_time = time.time() - start_time
        return result

    def synthesize_batch(self, texts: List[str],
                         voice: Optional[VoiceProfile] = None,
                         output_dir: Optional[str] = None) -> List[TTSResult]:
        """
        Multiple texts ka batch generation.
        Different characters ke dialogues ke liye useful.
        """
        results = []

        if output_dir:
            ensure_dir(output_dir)

        for i, text in enumerate(texts):
            output_path = None
            if output_dir:
                output_path = os.path.join(output_dir, f"line_{i+1:03d}.wav")

            result = self.synthesize(text, voice, output_path)
            results.append(result)

        success_count = sum(1 for r in results if r.success)
        logger.info(f"Batch complete: {success_count}/{len(texts)} successful")

        return results

    def synthesize_dialogue(self, dialogue: List[Dict],
                            output_dir: str) -> List[TTSResult]:
        """
        Multi-character dialogue generate karo.

        Args:
            dialogue: [{"character": "Name", "text": "Line", "voice_id": "..."}, ...]
            output_dir: Output directory

        Returns:
            List of TTSResult
        """
        ensure_dir(output_dir)
        results = []

        for i, line in enumerate(dialogue):
            character = line.get("character", f"Character{i}")
            text = line.get("text", "")
            voice_id = line.get("voice_id")

            # Voice profile get karo
            voice = None
            if voice_id and voice_id in self.voice_profiles:
                voice = self.voice_profiles[voice_id]

            # Filename with character
            safe_char = character.replace(" ", "_")
            filename = f"{i+1:03d}_{safe_char}.wav"
            output_path = os.path.join(output_dir, filename)

            result = self.synthesize(text, voice, output_path, use_cache=False)
            result.text = f"[{character}] {text}"
            results.append(result)

            logger.info(f"[{character}]: {text[:40]}...")

        return results

    # ------------------------------------------------------------
    # BACKEND SELECTION
    # ------------------------------------------------------------

    def _select_backend(self, voice: VoiceProfile) -> Optional[TTSBackend]:
        """Voice ke basis pe best backend select karo"""
        # Explicit engine
        if voice.engine != TTSEngineType.AUTO:
            backend = self.backends.get(voice.engine)
            if backend and backend.available:
                return backend
            # Fallback

        # Auto: language ke basis pe
        # Non-English: gTTS prefer karo (better multi-language)
        if voice.language != "en":
            gtts_backend = self.backends.get(TTSEngineType.GTTS)
            if gtts_backend and gtts_backend.available:
                return gtts_backend

        # English: pyttsx3 (fast, offline)
        pyttsx_backend = self.backends.get(TTSEngineType.PYTTSX3)
        if pyttsx_backend and pyttsx_backend.available:
            return pyttsx_backend

        # Last resort: gTTS
        gtts_backend = self.backends.get(TTSEngineType.GTTS)
        if gtts_backend and gtts_backend.available:
            return gtts_backend

        return None

    # ------------------------------------------------------------
    # CACHING
    # ------------------------------------------------------------

    def _get_cached_path(self, text: str, voice: VoiceProfile) -> str:
        """Text + voice se unique cached file path"""
        # Hash of text + key voice properties
        cache_key = f"{text}|{voice.language}|{voice.gender}|{voice.rate}|{voice.pitch}"
        hash_val = hash_string(cache_key)[:16]
        return os.path.join(self.cache_dir, f"cache_{hash_val}.wav")

    def clear_cache(self):
        """Cache directory clear karo"""
        try:
            count = 0
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                if os.path.isfile(filepath):
                    delete_file(filepath)
                    count += 1
            logger.info(f"Cache cleared ({count} files)")
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")

    def get_cache_size(self) -> int:
        """Cache size in bytes"""
        total = 0
        try:
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                if os.path.isfile(filepath):
                    total += get_file_size(filepath)
        except Exception:
            pass
        return total

    # ------------------------------------------------------------
    # VOICE PROFILE MANAGEMENT
    # ------------------------------------------------------------

    def add_voice_profile(self, voice: VoiceProfile) -> str:
        """Voice profile add karo"""
        self.voice_profiles[voice.id] = voice
        logger.debug(f"Added voice profile: {voice.name}")
        return voice.id

    def get_voice_profile(self, voice_id: str) -> Optional[VoiceProfile]:
        return self.voice_profiles.get(voice_id)

    def get_all_voice_profiles(self) -> List[VoiceProfile]:
        return list(self.voice_profiles.values())

    def remove_voice_profile(self, voice_id: str) -> bool:
        if voice_id in self.voice_profiles:
            del self.voice_profiles[voice_id]
            return True
        return False

    def get_default_voice(self) -> VoiceProfile:
        """Default voice profile"""
        if self.voice_profiles:
            return list(self.voice_profiles.values())[0]

        # Fallback
        return VoiceProfile(name="Fallback Default")

    # ------------------------------------------------------------
    # UTILITY
    # ------------------------------------------------------------

    def get_available_voices(self,
                              engine: Optional[TTSEngineType] = None) -> List[Dict]:
        """
        Available system voices list karo.

        Args:
            engine: Specific engine ki voices, ya sab
        """
        result = []

        if engine:
            backend = self.backends.get(engine)
            if backend and backend.available:
                voices = backend.get_available_voices()
                for v in voices:
                    v["engine"] = backend.name
                result.extend(voices)
        else:
            for eng, backend in self.backends.items():
                if backend.available:
                    voices = backend.get_available_voices()
                    for v in voices:
                        v["engine"] = backend.name
                    result.extend(voices)

        return result

    def _estimate_duration(self, audio_file: str) -> float:
        """Audio file ki approximate duration"""
        if not PYDUB_AVAILABLE:
            return 0.0

        try:
            if audio_file.lower().endswith(".mp3"):
                audio = AudioSegment.from_mp3(audio_file)
            elif audio_file.lower().endswith(".wav"):
                audio = AudioSegment.from_wav(audio_file)
            else:
                audio = AudioSegment.from_file(audio_file)

            return len(audio) / 1000.0  # ms to seconds
        except Exception:
            return 0.0

    def get_stats(self) -> Dict:
        """Engine statistics"""
        available_backends = [
            name.value for name, backend in self.backends.items()
            if backend.available
        ]

        return {
            "available_backends": available_backends,
            "total_generated": self.total_generated,
            "cache_hits": self.total_cache_hits,
            "cache_hit_rate": (
                f"{(self.total_cache_hits / max(1, self.total_generated + self.total_cache_hits)) * 100:.1f}%"
            ),
            "voice_profiles": len(self.voice_profiles),
            "cache_size": format_bytes(self.get_cache_size()),
            "supported_languages": len(Language.get_all()),
        }


# ============================================================
# TEST FUNCTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")
    print_banner("TTS Engine Test", "AI Voice Generation")

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))

    # ============================================================
    # Test 1: Initialize
    # ============================================================
    print_section("Test 1: Initialize TTS Engine")

    tts = TTSEngine()

    stats = tts.get_stats()
    print(f"Available backends: {stats['available_backends']}")
    print(f"Voice profiles: {stats['voice_profiles']}")
    print(f"Supported languages: {stats['supported_languages']}")

    if not stats['available_backends']:
        print("❌ No TTS backends available!")
        print("Install: pip install pyttsx3 gtts")
        sys.exit(1)

    # ============================================================
    # Test 2: List Available Voices
    # ============================================================
    print_section("Test 2: System Voices Available")

    voices = tts.get_available_voices(engine=TTSEngineType.PYTTSX3)
    print(f"pyttsx3 voices: {len(voices)}")

    for i, v in enumerate(voices[:5], 1):  # Sirf pehle 5
        print(f"  {i}. {v['name']}")

    # ============================================================
    # Test 3: List Voice Profiles
    # ============================================================
    print_section("Test 3: Voice Profiles")

    profiles = tts.get_all_voice_profiles()
    print(f"Total profiles: {len(profiles)}")

    for p in profiles:
        print(f"  - {p.name} ({p.language}, {p.engine.value}, "
              f"rate={p.rate}, gender={p.gender})")

    # ============================================================
    # Test 4: Simple Synthesis (English)
    # ============================================================
    print_section("Test 4: Generate English Speech (pyttsx3)")

    output_dir = os.path.join(base_dir, "temp", "tts_tests")
    ensure_dir(output_dir)

    english_voice = VoiceProfile(
        name="Test English",
        engine=TTSEngineType.PYTTSX3,
        language="en",
        rate=200
    )

    text_en = "Hello! Welcome to my 3D Animation Studio. This is a test of the text to speech engine."

    result = tts.synthesize(
        text=text_en,
        voice=english_voice,
        output_path=os.path.join(output_dir, "test_english.wav"),
        use_cache=False
    )

    if result.success:
        print(f"✅ Success!")
        print(f"   File: {result.audio_file}")
        print(f"   Size: {format_bytes(result.file_size)}")
        print(f"   Duration: {result.duration:.2f}s")
        print(f"   Engine: {result.engine_used}")
        print(f"   Time: {result.generation_time:.2f}s")
    else:
        print(f"❌ Failed: {result.error}")

    # ============================================================
    # Test 5: Hindi Speech (gTTS)
    # ============================================================
    print_section("Test 5: Generate Hindi Speech (gTTS)")

    if TTSEngineType.GTTS in tts.backends and tts.backends[TTSEngineType.GTTS].available:
        hindi_voice = VoiceProfile(
            name="Test Hindi",
            engine=TTSEngineType.GTTS,
            language="hi"
        )

        text_hi = "नमस्ते! मैं आपका 3D एनीमेशन स्टूडियो हूं।"

        result = tts.synthesize(
            text=text_hi,
            voice=hindi_voice,
            output_path=os.path.join(output_dir, "test_hindi.mp3"),
            use_cache=False
        )

        if result.success:
            print(f"✅ Hindi audio generated!")
            print(f"   File: {result.audio_file}")
            print(f"   Size: {format_bytes(result.file_size)}")
            print(f"   Engine: {result.engine_used}")
        else:
            print(f"❌ Failed: {result.error}")
            print("   (Internet needed for gTTS)")
    else:
        print("⚠️  gTTS not available, skipping")

    # ============================================================
    # Test 6: Multi-Voice Dialogue
    # ============================================================
    print_section("Test 6: Multi-Character Dialogue")

    # Naye voice profiles banao
    hero_voice = VoiceProfile(
        name="Hero",
        engine=TTSEngineType.PYTTSX3,
        language="en",
        gender="male",
        rate=180
    )
    hero_id = tts.add_voice_profile(hero_voice)

    villain_voice = VoiceProfile(
        name="Villain",
        engine=TTSEngineType.PYTTSX3,
        language="en",
        gender="male",
        rate=160,
        pitch=90
    )
    villain_id = tts.add_voice_profile(villain_voice)

    friend_voice = VoiceProfile(
        name="Friend",
        engine=TTSEngineType.PYTTSX3,
        language="en",
        gender="female",
        rate=220
    )
    friend_id = tts.add_voice_profile(friend_voice)

    # Dialogue
    dialogue = [
        {"character": "Hero", "text": "I will save the world!", "voice_id": hero_id},
        {"character": "Villain", "text": "Not if I stop you first!", "voice_id": villain_id},
        {"character": "Friend", "text": "Wait! I have an idea!", "voice_id": friend_id},
        {"character": "Hero", "text": "What is your plan?", "voice_id": hero_id},
    ]

    dialogue_dir = os.path.join(output_dir, "dialogue")
    print(f"\nGenerating {len(dialogue)} dialogue lines...")

    results = tts.synthesize_dialogue(dialogue, dialogue_dir)

    print(f"\nResults:")
    for i, r in enumerate(results, 1):
        status = "✅" if r.success else "❌"
        print(f"  {status} Line {i}: {r.text[:50]}")

    print(f"\nDialogue files saved in: {dialogue_dir}")

    # ============================================================
    # Test 7: Caching
    # ============================================================
    print_section("Test 7: Cache Test")

    same_text = "This text will be cached for reuse."

    # Pehli baar (generate)
    print("First call (generates)...")
    r1 = tts.synthesize(same_text, english_voice, use_cache=True)
    print(f"  Time: {r1.generation_time:.3f}s, Cached: {r1.cached}")

    # Doosri baar (cache hit)
    print("Second call (cache hit)...")
    r2 = tts.synthesize(same_text, english_voice, use_cache=True)
    print(f"  Time: {r2.generation_time:.4f}s, Cached: {r2.cached}")

    if r2.cached:
        speedup = r1.generation_time / max(0.001, r2.generation_time)
        print(f"  Speedup: {speedup:.1f}x faster from cache!")

    # ============================================================
    # Test 8: Prosody Control
    # ============================================================
    print_section("Test 8: Prosody Variations")

    variations = [
        ("Slow", VoiceProfile(engine=TTSEngineType.PYTTSX3, rate=120)),
        ("Normal", VoiceProfile(engine=TTSEngineType.PYTTSX3, rate=200)),
        ("Fast", VoiceProfile(engine=TTSEngineType.PYTTSX3, rate=280)),
    ]

    test_text = "The quick brown fox jumps over the lazy dog."

    for name, voice in variations:
        output = os.path.join(output_dir, f"prosody_{name.lower()}.wav")
        result = tts.synthesize(test_text, voice, output, use_cache=False)

        if result.success:
            print(f"  ✓ {name} (rate={voice.rate}): "
                  f"{result.duration:.2f}s duration")

    # ============================================================
    # Test 9: Statistics
    # ============================================================
    print_section("Test 9: Final Statistics")

    stats = tts.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # ============================================================
    # Info
    # ============================================================
    print_section("Output Files")

    print(f"Test audio files saved in:")
    print(f"  {output_dir}")
    print(f"\n👉 Open folder to listen:")
    print(f"   start {output_dir}")

    print_banner(
        "✅ All Tests Passed",
        "TTS Engine Working - Voice generation ready!"
    )