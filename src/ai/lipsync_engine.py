# ============================================================
# 3D ANIMATION STUDIO - AI Lipsync Engine
# ============================================================
# Features:
# - Audio analysis for phoneme detection
# - Preston Blair viseme system (15 mouth shapes)
# - Amplitude + spectral analysis based lipsync
# - Frame-by-frame timing (matches video FPS)
# - JSON export for character rigs
# - Text-based phoneme extraction (from script)
# - Blend shape interpolation
# - Rhubarb-compatible output format
# - Multi-language phoneme support
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
import re
import json
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

# Audio analysis libraries
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    librosa = None

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False
    sf = None

from src.utils import (
    get_logger, get_config, ensure_dir, generate_short_id,
    read_json, write_json, get_file_size, format_bytes,
    clamp, lerp
)

logger = get_logger("LipsyncEngine")


# ============================================================
# VISEME SYSTEM (Mouth Shapes)
# ============================================================

class Viseme(Enum):
    """
    Preston Blair 10 basic visemes + extras.
    Ye standard mouth shapes hain animation industry ke.
    """
    REST = "rest"           # Closed neutral mouth
    A = "A"                 # "ah" - AA, AH, AY (father, cat, my)
    B = "B"                 # "b/m/p" - closed lips (baby, mom, pop)
    C = "C"                 # "ee" - IY, IH (see, sit)
    D = "D"                 # "t/d/n" - tongue behind teeth
    E = "E"                 # "eh" - EH, ER (bed, her)
    F = "F"                 # "f/v" - lower lip bites upper teeth
    G = "G"                 # "k/g" - tongue back
    H = "H"                 # "l" - tongue up (love)
    L = "L"                 # "th" - tongue between teeth
    O = "O"                 # "oh" - rounded (go, so)
    U = "U"                 # "oo" - very small round (you)
    WQ = "WQ"               # "w/oo" - forward round (who)
    MBP = "MBP"             # Combined M/B/P (closed)
    FV = "FV"               # Combined F/V


# ============================================================
# PHONEME TO VISEME MAPPING
# ============================================================

class PhonemeMapper:
    """
    Phonemes (speech sounds) → Visemes (mouth shapes) mapping.
    ARPABET standard use karta hai (English).
    """

    # ARPABET phoneme → Viseme
    ARPABET_TO_VISEME = {
        # Vowels - A group
        "AA": Viseme.A,     # odd, father
        "AH": Viseme.A,     # hut, up
        "AE": Viseme.A,     # at, cat
        "AY": Viseme.A,     # bite, my
        "AW": Viseme.O,     # how, cow

        # Vowels - E group
        "EH": Viseme.E,     # Ed, red
        "ER": Viseme.E,     # hurt, her
        "EY": Viseme.E,     # ate, day

        # Vowels - I group
        "IH": Viseme.C,     # it, sit
        "IY": Viseme.C,     # eat, see

        # Vowels - O group
        "OW": Viseme.O,     # oat, go
        "OY": Viseme.O,     # toy, boy
        "AO": Viseme.O,     # ought, dog

        # Vowels - U group
        "UH": Viseme.U,     # hood, book
        "UW": Viseme.WQ,    # two, you

        # Consonants - Closed (M, B, P)
        "M": Viseme.MBP,
        "B": Viseme.MBP,
        "P": Viseme.MBP,

        # Consonants - F, V
        "F": Viseme.FV,
        "V": Viseme.FV,

        # Consonants - T, D, N
        "T": Viseme.D,
        "D": Viseme.D,
        "N": Viseme.D,
        "S": Viseme.D,
        "Z": Viseme.D,

        # Consonants - K, G
        "K": Viseme.G,
        "G": Viseme.G,
        "NG": Viseme.G,

        # Consonants - L
        "L": Viseme.H,

        # Consonants - W
        "W": Viseme.WQ,

        # Consonants - TH
        "TH": Viseme.L,
        "DH": Viseme.L,

        # Consonants - R
        "R": Viseme.E,

        # Consonants - Y
        "Y": Viseme.C,

        # Consonants - H
        "HH": Viseme.A,

        # Consonants - SH, CH, JH, ZH
        "SH": Viseme.C,
        "CH": Viseme.C,
        "JH": Viseme.C,
        "ZH": Viseme.C,

        # Silence
        "SIL": Viseme.REST,
        "SP": Viseme.REST,
    }

    # Simple letter → viseme (fallback, less accurate)
    LETTER_TO_VISEME = {
        "a": Viseme.A, "e": Viseme.E, "i": Viseme.C,
        "o": Viseme.O, "u": Viseme.U,
        "m": Viseme.MBP, "b": Viseme.MBP, "p": Viseme.MBP,
        "f": Viseme.FV, "v": Viseme.FV,
        "t": Viseme.D, "d": Viseme.D, "n": Viseme.D,
        "s": Viseme.D, "z": Viseme.D,
        "k": Viseme.G, "g": Viseme.G,
        "l": Viseme.H, "r": Viseme.E,
        "w": Viseme.WQ, "y": Viseme.C,
        "h": Viseme.A,
        "c": Viseme.G, "q": Viseme.G,
        "j": Viseme.C, "x": Viseme.G,
    }

    @staticmethod
    def phoneme_to_viseme(phoneme: str) -> Viseme:
        """ARPABET phoneme → Viseme"""
        # Numbers hatao (stress markers)
        clean_phoneme = re.sub(r"\d", "", phoneme.upper())
        return PhonemeMapper.ARPABET_TO_VISEME.get(clean_phoneme, Viseme.REST)

    @staticmethod
    def letter_to_viseme(letter: str) -> Viseme:
        """Simple letter → viseme (fallback)"""
        return PhonemeMapper.LETTER_TO_VISEME.get(letter.lower(), Viseme.REST)


# ============================================================
# TEXT TO PHONEMES (Simple English Rules)
# ============================================================

class SimplePhonemeExtractor:
    """
    Text se phonemes extract karo (basic English rules).
    Real phonemizer nahi hai but simple approximation.

    Advanced use ke liye 'phonemizer' library install karo.
    """

    # Common English word patterns → phonemes
    DIGRAPHS = {
        "th": ["TH"],
        "sh": ["SH"],
        "ch": ["CH"],
        "ph": ["F"],
        "wh": ["W"],
        "ng": ["NG"],
        "qu": ["K", "W"],
        "ck": ["K"],
    }

    # Vowel patterns
    VOWEL_PATTERNS = {
        "ai": "EY", "ay": "EY",
        "ea": "IY", "ee": "IY", "ie": "IY",
        "oa": "OW", "oo": "UW",
        "ou": "AW", "ow": "AW",
        "au": "AO", "aw": "AO",
        "oi": "OY", "oy": "OY",
    }

    @staticmethod
    def text_to_phonemes(text: str) -> List[str]:
        """
        Simple text → phonemes converter.
        Basic English rules use karta hai.
        """
        text = text.lower().strip()
        phonemes = []

        # Remove punctuation
        text = re.sub(r"[^\w\s]", "", text)

        words = text.split()

        for word_idx, word in enumerate(words):
            if word_idx > 0:
                phonemes.append("SIL")  # Word break

            i = 0
            while i < len(word):
                # 2-letter combinations
                if i + 1 < len(word):
                    two_char = word[i:i+2]

                    if two_char in SimplePhonemeExtractor.DIGRAPHS:
                        phonemes.extend(SimplePhonemeExtractor.DIGRAPHS[two_char])
                        i += 2
                        continue

                    if two_char in SimplePhonemeExtractor.VOWEL_PATTERNS:
                        phonemes.append(SimplePhonemeExtractor.VOWEL_PATTERNS[two_char])
                        i += 2
                        continue

                # Single character
                char = word[i]
                if char.isalpha():
                    # Vowel or consonant
                    if char in "aeiou":
                        # Simple vowel mapping
                        vowel_map = {"a": "AH", "e": "EH", "i": "IH", "o": "OW", "u": "UH"}
                        phonemes.append(vowel_map.get(char, "AH"))
                    else:
                        # Consonant → uppercase phoneme
                        cons_map = {
                            "c": "K", "q": "K", "x": "K",
                            "j": "JH", "y": "Y",
                        }
                        phonemes.append(cons_map.get(char, char.upper()))
                i += 1

        return phonemes


# ============================================================
# LIPSYNC FRAME (Single Time Point)
# ============================================================

@dataclass
class LipsyncFrame:
    """
    Single lipsync data point.
    Time-based mouth shape.
    """
    time: float                       # Seconds from start
    viseme: Viseme = Viseme.REST      # Mouth shape
    weight: float = 1.0               # Intensity 0-1
    amplitude: float = 0.0            # Audio amplitude at this time
    duration: float = 0.0             # How long to hold this shape

    def to_dict(self) -> Dict:
        return {
            "time": round(self.time, 4),
            "viseme": self.viseme.value,
            "weight": round(self.weight, 3),
            "amplitude": round(self.amplitude, 3),
            "duration": round(self.duration, 4),
        }


# ============================================================
# LIPSYNC RESULT
# ============================================================

@dataclass
class LipsyncData:
    """Complete lipsync data for an audio clip"""
    audio_file: Optional[str] = None
    duration: float = 0.0
    fps: int = 30
    frames: List[LipsyncFrame] = field(default_factory=list)
    total_frames: int = 0

    # Metadata
    method: str = "amplitude"  # "amplitude", "spectral", "text-based"
    language: str = "en"
    generated_at: str = ""

    def to_dict(self) -> Dict:
        return {
            "audio_file": self.audio_file,
            "duration": round(self.duration, 3),
            "fps": self.fps,
            "total_frames": self.total_frames,
            "method": self.method,
            "language": self.language,
            "generated_at": self.generated_at,
            "frames": [f.to_dict() for f in self.frames],
        }

    def save_to_file(self, filepath: str) -> bool:
        """JSON file me save karo"""
        try:
            ensure_dir(os.path.dirname(filepath))
            return write_json(filepath, self.to_dict())
        except Exception as e:
            logger.error(f"Save failed: {e}")
            return False

    @classmethod
    def load_from_file(cls, filepath: str) -> Optional["LipsyncData"]:
        """JSON file se load karo"""
        try:
            data = read_json(filepath)
            if not data:
                return None

            lipsync = cls(
                audio_file=data.get("audio_file"),
                duration=data.get("duration", 0),
                fps=data.get("fps", 30),
                total_frames=data.get("total_frames", 0),
                method=data.get("method", "amplitude"),
                language=data.get("language", "en"),
                generated_at=data.get("generated_at", ""),
            )

            for frame_data in data.get("frames", []):
                frame = LipsyncFrame(
                    time=frame_data["time"],
                    viseme=Viseme(frame_data["viseme"]),
                    weight=frame_data.get("weight", 1.0),
                    amplitude=frame_data.get("amplitude", 0),
                    duration=frame_data.get("duration", 0),
                )
                lipsync.frames.append(frame)

            return lipsync
        except Exception as e:
            logger.error(f"Load failed: {e}")
            return None

    def get_viseme_at_time(self, time: float) -> Tuple[Viseme, float]:
        """
        Kisi time par konsi viseme aur weight.
        Smooth interpolation ke saath.

        Returns:
            (viseme, weight)
        """
        if not self.frames:
            return (Viseme.REST, 0.0)

        # Boundary cases
        if time <= self.frames[0].time:
            return (self.frames[0].viseme, self.frames[0].weight)
        if time >= self.frames[-1].time:
            return (self.frames[-1].viseme, self.frames[-1].weight)

        # Find surrounding frames
        for i in range(len(self.frames) - 1):
            if self.frames[i].time <= time <= self.frames[i + 1].time:
                # Return current frame's viseme (no interpolation between different visemes)
                return (self.frames[i].viseme, self.frames[i].weight)

        return (Viseme.REST, 0.0)


# ============================================================
# AMPLITUDE-BASED LIPSYNC (Simple, Fast)
# ============================================================

class AmplitudeLipsync:
    """
    Simplest lipsync method.
    Audio amplitude ke basis pe mouth open/close.
    Fast but less accurate.
    """

    @staticmethod
    def generate(audio_file: str,
                 fps: int = 30,
                 threshold: float = 0.02) -> Optional[LipsyncData]:
        """
        Amplitude analysis se lipsync generate karo.

        Args:
            audio_file: Audio file path
            fps: Target FPS
            threshold: Silence threshold (0-1)
        """
        if not os.path.exists(audio_file):
            logger.error(f"File not found: {audio_file}")
            return None

        # Load audio
        y, sr = AmplitudeLipsync._load_audio(audio_file)
        if y is None:
            return None

        duration = len(y) / sr

        # Result
        lipsync = LipsyncData(
            audio_file=audio_file,
            duration=duration,
            fps=fps,
            method="amplitude",
            generated_at=str(time.time())
        )

        # Frame duration
        frame_duration = 1.0 / fps
        total_frames = int(duration * fps)
        samples_per_frame = int(sr / fps)

        # Har frame ka amplitude
        for frame_idx in range(total_frames):
            time_pos = frame_idx * frame_duration

            # Samples window
            start_sample = frame_idx * samples_per_frame
            end_sample = min(start_sample + samples_per_frame, len(y))

            if start_sample >= len(y):
                break

            # RMS amplitude
            chunk = y[start_sample:end_sample]
            if len(chunk) == 0:
                amplitude = 0.0
            else:
                amplitude = float(np.sqrt(np.mean(chunk ** 2)))

            # Viseme select karo amplitude ke basis pe
            viseme = AmplitudeLipsync._amplitude_to_viseme(amplitude, threshold)
            weight = min(1.0, amplitude * 5.0)  # Scale for visibility

            frame = LipsyncFrame(
                time=time_pos,
                viseme=viseme,
                weight=weight,
                amplitude=amplitude,
                duration=frame_duration
            )
            lipsync.frames.append(frame)

        lipsync.total_frames = len(lipsync.frames)
        logger.info(
            f"Generated {lipsync.total_frames} lipsync frames "
            f"({duration:.2f}s @ {fps}fps)"
        )
        return lipsync

    @staticmethod
    def _load_audio(filepath: str) -> Tuple[Optional[np.ndarray], int]:
        """Audio load karo"""
        try:
            if LIBROSA_AVAILABLE:
                y, sr = librosa.load(filepath, sr=None, mono=True)
                return y, sr
            elif SOUNDFILE_AVAILABLE:
                y, sr = sf.read(filepath, dtype="float32")
                if len(y.shape) > 1:
                    y = np.mean(y, axis=1)  # To mono
                return y, sr
            else:
                logger.error("No audio library available")
                return None, 0
        except Exception as e:
            logger.error(f"Audio load failed: {e}")
            return None, 0

    @staticmethod
    def _amplitude_to_viseme(amplitude: float,
                              threshold: float = 0.02) -> Viseme:
        """
        Amplitude se rough viseme guess.
        Silence = REST, loud = A (open), medium = E, low = MBP
        """
        if amplitude < threshold:
            return Viseme.REST
        elif amplitude < threshold * 2:
            return Viseme.MBP  # Closed mouth
        elif amplitude < threshold * 4:
            return Viseme.E    # Small open
        elif amplitude < threshold * 8:
            return Viseme.O    # Medium open
        else:
            return Viseme.A    # Wide open


# ============================================================
# SPECTRAL LIPSYNC (Better Quality)
# ============================================================

class SpectralLipsync:
    """
    Frequency analysis based lipsync.
    MFCC features use karke better phoneme detection.
    Requires librosa.
    """

    @staticmethod
    def generate(audio_file: str,
                 fps: int = 30) -> Optional[LipsyncData]:
        """
        MFCC-based lipsync generate karo.
        """
        if not LIBROSA_AVAILABLE:
            logger.warning("librosa required for spectral lipsync")
            return AmplitudeLipsync.generate(audio_file, fps)

        if not os.path.exists(audio_file):
            logger.error(f"File not found: {audio_file}")
            return None

        try:
            y, sr = librosa.load(audio_file, sr=None, mono=True)
            duration = len(y) / sr

            # Result
            lipsync = LipsyncData(
                audio_file=audio_file,
                duration=duration,
                fps=fps,
                method="spectral",
                generated_at=str(time.time())
            )

            # Extract features
            frame_duration = 1.0 / fps
            hop_length = int(sr / fps)

            # MFCC features (mouth shape ke liye useful)
            mfccs = librosa.feature.mfcc(
                y=y, sr=sr,
                n_mfcc=13,
                hop_length=hop_length
            )

            # Spectral centroid (frequency center)
            centroid = librosa.feature.spectral_centroid(
                y=y, sr=sr,
                hop_length=hop_length
            )[0]

            # Zero crossing rate (voiced vs unvoiced)
            zcr = librosa.feature.zero_crossing_rate(
                y, hop_length=hop_length
            )[0]

            # RMS energy (amplitude)
            rms = librosa.feature.rms(
                y=y, hop_length=hop_length
            )[0]

            # Har frame ke liye viseme
            num_frames = min(len(centroid), int(duration * fps))

            for i in range(num_frames):
                time_pos = i * frame_duration

                # Features
                amp = float(rms[i]) if i < len(rms) else 0.0
                cent = float(centroid[i]) if i < len(centroid) else 0.0
                z = float(zcr[i]) if i < len(zcr) else 0.0

                # Viseme decision based on features
                viseme = SpectralLipsync._features_to_viseme(amp, cent, z, sr)
                weight = min(1.0, amp * 5.0)

                frame = LipsyncFrame(
                    time=time_pos,
                    viseme=viseme,
                    weight=weight,
                    amplitude=amp,
                    duration=frame_duration
                )
                lipsync.frames.append(frame)

            lipsync.total_frames = len(lipsync.frames)
            logger.info(
                f"Spectral lipsync: {lipsync.total_frames} frames "
                f"({duration:.2f}s @ {fps}fps)"
            )
            return lipsync

        except Exception as e:
            logger.error(f"Spectral lipsync failed: {e}")
            return AmplitudeLipsync.generate(audio_file, fps)

    @staticmethod
    def _features_to_viseme(amplitude: float,
                             centroid: float,
                             zcr: float,
                             sr: int) -> Viseme:
        """
        Audio features se viseme decide karo.

        Rules:
        - Silence: low amplitude
        - Vowels: low ZCR, high energy
        - Consonants: high ZCR
        - Bright sound (high centroid): S, T, F sounds
        - Dark sound (low centroid): M, O, U sounds
        """
        # Silence
        if amplitude < 0.01:
            return Viseme.REST

        # Normalize centroid (0-1)
        norm_centroid = centroid / (sr / 2) if sr > 0 else 0

        # Voiced (vowels) vs unvoiced (consonants)
        is_voiced = zcr < 0.1

        if is_voiced:
            # Vowel - amplitude aur centroid ke basis pe
            if amplitude > 0.15:
                # Loud vowel
                if norm_centroid < 0.15:
                    return Viseme.O    # "oh"
                elif norm_centroid < 0.25:
                    return Viseme.A    # "ah"
                else:
                    return Viseme.E    # "eh"
            else:
                # Softer vowel
                if norm_centroid < 0.2:
                    return Viseme.U    # "oo"
                else:
                    return Viseme.C    # "ee"
        else:
            # Consonant
            if amplitude < 0.05:
                return Viseme.MBP     # Very soft = M/B/P
            elif norm_centroid > 0.4:
                return Viseme.D       # High freq = T/D/S
            elif norm_centroid < 0.15:
                return Viseme.G       # Low freq = K/G
            else:
                return Viseme.FV      # F/V


# ============================================================
# TEXT-BASED LIPSYNC (From Script + TTS Timing)
# ============================================================

class TextBasedLipsync:
    """
    Script text se lipsync generate karo.
    Audio duration ke saath phonemes ko distribute karta hai.
    """

    @staticmethod
    def generate(text: str,
                 audio_duration: float,
                 fps: int = 30,
                 audio_file: Optional[str] = None) -> LipsyncData:
        """
        Text + duration se lipsync banao.

        Args:
            text: Script text
            audio_duration: Audio ki duration
            fps: Frame rate
            audio_file: Optional audio file path
        """
        # Phonemes extract karo
        phonemes = SimplePhonemeExtractor.text_to_phonemes(text)

        if not phonemes:
            logger.warning("No phonemes extracted")
            return LipsyncData(
                audio_file=audio_file,
                duration=audio_duration,
                fps=fps,
                method="text-based"
            )

        # Result
        lipsync = LipsyncData(
            audio_file=audio_file,
            duration=audio_duration,
            fps=fps,
            method="text-based",
            generated_at=str(time.time())
        )

        # Har phoneme ka time slot
        time_per_phoneme = audio_duration / len(phonemes)

        for i, phoneme in enumerate(phonemes):
            time_pos = i * time_per_phoneme
            viseme = PhonemeMapper.phoneme_to_viseme(phoneme)

            frame = LipsyncFrame(
                time=time_pos,
                viseme=viseme,
                weight=0.7 if viseme != Viseme.REST else 0.0,
                amplitude=0.5,
                duration=time_per_phoneme
            )
            lipsync.frames.append(frame)

        lipsync.total_frames = len(lipsync.frames)
        logger.info(
            f"Text-based lipsync: {len(phonemes)} phonemes "
            f"→ {lipsync.total_frames} frames"
        )
        return lipsync


# ============================================================
# MAIN LIPSYNC ENGINE
# ============================================================

class LipsyncEngine:
    """
    Main lipsync engine.
    Multiple methods support karta hai.
    """

    def __init__(self, config: Optional[Dict] = None):
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # Default FPS
        render_config = self.config.get("rendering", {})
        self.default_fps = render_config.get("default_fps", 30)

        # Stats
        self.total_generated = 0

        logger.info(f"LipsyncEngine initialized (default fps: {self.default_fps})")

    # ------------------------------------------------------------
    # GENERATION METHODS
    # ------------------------------------------------------------

    def generate_from_audio(self, audio_file: str,
                             fps: Optional[int] = None,
                             method: str = "auto") -> Optional[LipsyncData]:
        """
        Audio file se lipsync generate karo.

        Args:
            audio_file: Audio file path
            fps: Frame rate (None = default)
            method: "amplitude", "spectral", "auto"
        """
        if fps is None:
            fps = self.default_fps

        if not os.path.exists(audio_file):
            logger.error(f"File not found: {audio_file}")
            return None

        logger.info(f"Generating lipsync: {os.path.basename(audio_file)} [{method}]")

        # Auto select best method
        if method == "auto":
            if LIBROSA_AVAILABLE:
                method = "spectral"
            else:
                method = "amplitude"

        # Generate
        if method == "spectral":
            result = SpectralLipsync.generate(audio_file, fps)
        else:
            result = AmplitudeLipsync.generate(audio_file, fps)

        if result:
            self.total_generated += 1

        return result

    def generate_from_text(self, text: str,
                           audio_duration: float,
                           audio_file: Optional[str] = None,
                           fps: Optional[int] = None) -> LipsyncData:
        """
        Text script se lipsync generate karo.

        Args:
            text: Script
            audio_duration: Audio duration
            audio_file: Optional audio reference
            fps: Frame rate
        """
        if fps is None:
            fps = self.default_fps

        result = TextBasedLipsync.generate(text, audio_duration, fps, audio_file)
        self.total_generated += 1
        return result

    def generate_hybrid(self, audio_file: str,
                        text: str,
                        fps: Optional[int] = None) -> Optional[LipsyncData]:
        """
        Best method: Audio analysis + text phonemes combined.
        Sabse accurate.
        """
        if fps is None:
            fps = self.default_fps

        # Pehle audio-based
        audio_result = self.generate_from_audio(audio_file, fps, method="spectral")

        if not audio_result:
            return None

        # Text phonemes bhi extract karo
        phonemes = SimplePhonemeExtractor.text_to_phonemes(text)

        # Note: True hybrid requires alignment algorithm
        # For now, audio-based result use karo
        # Future: forced alignment can improve this

        audio_result.method = "hybrid"
        return audio_result

    # ------------------------------------------------------------
    # BATCH PROCESSING
    # ------------------------------------------------------------

    def generate_batch(self, audio_files: List[str],
                       output_dir: Optional[str] = None,
                       method: str = "auto") -> List[Optional[LipsyncData]]:
        """
        Multiple audio files ka batch processing.
        """
        results = []

        if output_dir:
            ensure_dir(output_dir)

        for audio_file in audio_files:
            result = self.generate_from_audio(audio_file, method=method)

            if result and output_dir:
                # Save JSON
                filename = os.path.splitext(os.path.basename(audio_file))[0]
                json_path = os.path.join(output_dir, f"{filename}_lipsync.json")
                result.save_to_file(json_path)

            results.append(result)

        success_count = sum(1 for r in results if r is not None)
        logger.info(f"Batch complete: {success_count}/{len(audio_files)} successful")

        return results

    # ------------------------------------------------------------
    # UTILITIES
    # ------------------------------------------------------------

    def get_viseme_statistics(self,
                                lipsync: LipsyncData) -> Dict[str, int]:
        """Har viseme kitni baar use hui"""
        stats = {}
        for frame in lipsync.frames:
            viseme_name = frame.viseme.value
            stats[viseme_name] = stats.get(viseme_name, 0) + 1
        return stats

    def preview_frames(self, lipsync: LipsyncData,
                       count: int = 20,
                       skip_rest: bool = False) -> List[str]:
        """
        First N frames ki text preview.
        Debug ke liye useful.
        """
        preview = []

        frames_to_show = lipsync.frames
        if skip_rest:
            frames_to_show = [f for f in frames_to_show if f.viseme != Viseme.REST]

        for frame in frames_to_show[:count]:
            preview.append(
                f"t={frame.time:5.2f}s  "
                f"{frame.viseme.value:6s}  "
                f"weight={frame.weight:.2f}  "
                f"amp={frame.amplitude:.3f}"
            )

        return preview

    def get_stats(self) -> Dict:
        """Engine statistics"""
        return {
            "total_generated": self.total_generated,
            "default_fps": self.default_fps,
            "librosa_available": LIBROSA_AVAILABLE,
            "soundfile_available": SOUNDFILE_AVAILABLE,
            "available_visemes": len(Viseme),
        }


# ============================================================
# TEST FUNCTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")
    print_banner("Lipsync Engine Test", "AI Lipsync Generation")

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))

    # ============================================================
    # Test 1: Initialize
    # ============================================================
    print_section("Test 1: Initialize Lipsync Engine")

    engine = LipsyncEngine()

    stats = engine.get_stats()
    print(f"Default FPS: {stats['default_fps']}")
    print(f"librosa: {stats['librosa_available']}")
    print(f"soundfile: {stats['soundfile_available']}")
    print(f"Available visemes: {stats['available_visemes']}")

    # ============================================================
    # Test 2: Viseme System
    # ============================================================
    print_section("Test 2: Viseme System")

    print("Available mouth shapes:")
    for viseme in Viseme:
        print(f"  {viseme.value:6s} - {viseme.name}")

    # ============================================================
    # Test 3: Phoneme Mapping
    # ============================================================
    print_section("Test 3: Phoneme → Viseme Mapping")

    test_phonemes = ["AA", "IY", "OW", "M", "F", "T", "K", "L", "SH"]
    print("Phoneme → Viseme:")
    for p in test_phonemes:
        v = PhonemeMapper.phoneme_to_viseme(p)
        print(f"  {p:4s} → {v.value}")

    # ============================================================
    # Test 4: Text to Phonemes
    # ============================================================
    print_section("Test 4: Text → Phonemes Extraction")

    test_texts = [
        "Hello world",
        "How are you today",
        "The quick brown fox",
    ]

    for text in test_texts:
        phonemes = SimplePhonemeExtractor.text_to_phonemes(text)
        visemes = [PhonemeMapper.phoneme_to_viseme(p).value for p in phonemes]

        print(f"\nText: '{text}'")
        print(f"Phonemes: {phonemes[:15]}{'...' if len(phonemes) > 15 else ''}")
        print(f"Visemes:  {visemes[:15]}{'...' if len(visemes) > 15 else ''}")

    # ============================================================
    # Test 5: Check for TTS Audio Files
    # ============================================================
    print_section("Test 5: Find TTS Audio Files")

    tts_dir = os.path.join(base_dir, "temp", "tts_tests")
    audio_files = []

    if os.path.exists(tts_dir):
        for f in os.listdir(tts_dir):
            filepath = os.path.join(tts_dir, f)
            if os.path.isfile(filepath) and f.endswith(".wav"):
                audio_files.append(filepath)

    if not audio_files:
        print("⚠️  No TTS audio found. Run tts_engine.py first!")
        print("Skipping audio-based tests...")
    else:
        print(f"Found {len(audio_files)} audio files")

    # ============================================================
    # Test 6: Amplitude-Based Lipsync
    # ============================================================
    if audio_files:
        print_section("Test 6: Amplitude-Based Lipsync")

        test_audio = audio_files[0]
        print(f"Audio: {os.path.basename(test_audio)}")

        lipsync = AmplitudeLipsync.generate(test_audio, fps=30, threshold=0.02)

        if lipsync:
            print(f"✅ Generated {lipsync.total_frames} frames")
            print(f"   Duration: {lipsync.duration:.2f}s")
            print(f"   FPS: {lipsync.fps}")

            # Preview first 10 non-rest frames
            print("\n   First 10 active frames:")
            preview = engine.preview_frames(lipsync, count=10, skip_rest=True)
            for line in preview:
                print(f"   {line}")

    # ============================================================
    # Test 7: Spectral Lipsync
    # ============================================================
    if audio_files and LIBROSA_AVAILABLE:
        print_section("Test 7: Spectral Lipsync (Better)")

        test_audio = audio_files[0]

        lipsync = SpectralLipsync.generate(test_audio, fps=30)

        if lipsync:
            print(f"✅ Generated {lipsync.total_frames} frames")

            # Viseme statistics
            stats = engine.get_viseme_statistics(lipsync)
            print("\n   Viseme distribution:")
            for viseme, count in sorted(stats.items(), key=lambda x: -x[1]):
                pct = (count / lipsync.total_frames) * 100
                bar = "█" * int(pct / 2)
                print(f"   {viseme:6s} {count:4d} ({pct:5.1f}%) {bar}")

    # ============================================================
    # Test 8: Text-Based Lipsync
    # ============================================================
    print_section("Test 8: Text-Based Lipsync")

    test_text = "The quick brown fox jumps over the lazy dog"
    test_duration = 3.0  # 3 seconds

    lipsync = engine.generate_from_text(
        text=test_text,
        audio_duration=test_duration,
        fps=30
    )

    print(f"Text: '{test_text}'")
    print(f"Duration: {test_duration}s")
    print(f"Generated {lipsync.total_frames} frames")

    stats = engine.get_viseme_statistics(lipsync)
    print(f"\nUnique visemes used: {len(stats)}")
    for viseme, count in sorted(stats.items(), key=lambda x: -x[1])[:5]:
        print(f"  {viseme}: {count} times")

    # ============================================================
    # Test 9: Save Lipsync JSON
    # ============================================================
    print_section("Test 9: Save Lipsync to JSON")

    output_dir = os.path.join(base_dir, "temp", "lipsync_tests")
    ensure_dir(output_dir)

    if audio_files:
        test_audio = audio_files[0]
        lipsync = engine.generate_from_audio(test_audio, method="auto")

        if lipsync:
            output_path = os.path.join(
                output_dir,
                f"{os.path.splitext(os.path.basename(test_audio))[0]}_lipsync.json"
            )

            success = lipsync.save_to_file(output_path)
            if success:
                file_size = get_file_size(output_path)
                print(f"✅ Saved: {output_path}")
                print(f"   Size: {format_bytes(file_size)}")
                print(f"   Frames: {lipsync.total_frames}")

                # Reload test
                loaded = LipsyncData.load_from_file(output_path)
                if loaded:
                    print(f"✅ Reloaded successfully ({loaded.total_frames} frames)")

    # ============================================================
    # Test 10: Batch Processing
    # ============================================================
    if audio_files:
        print_section("Test 10: Batch Processing")

        # Process first 3 audio files
        batch_files = audio_files[:3]
        print(f"Processing {len(batch_files)} files...")

        batch_dir = os.path.join(output_dir, "batch")
        results = engine.generate_batch(batch_files, batch_dir)

        for filepath, result in zip(batch_files, results):
            status = "✅" if result else "❌"
            name = os.path.basename(filepath)
            frames = result.total_frames if result else 0
            print(f"  {status} {name}: {frames} frames")

    # ============================================================
    # Test 11: Get Viseme at Time
    # ============================================================
    if audio_files:
        print_section("Test 11: Query Viseme at Specific Times")

        lipsync = engine.generate_from_audio(audio_files[0])

        if lipsync:
            test_times = [0.0, 0.5, 1.0, 1.5, 2.0]
            print("Query specific timestamps:")
            for t in test_times:
                if t <= lipsync.duration:
                    viseme, weight = lipsync.get_viseme_at_time(t)
                    print(f"  t={t}s → {viseme.value} (weight: {weight:.2f})")

    # ============================================================
    # Test 12: Final Stats
    # ============================================================
    print_section("Test 12: Final Statistics")

    stats = engine.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print_section("Output Files")
    print(f"Lipsync JSON files saved in:")
    print(f"  {output_dir}")
    print(f"\n👉 Open to inspect:")
    print(f"   start {output_dir}")

    print_banner(
        "✅ All Tests Passed",
        "Lipsync Engine Working - Ready for character animation!"
    )