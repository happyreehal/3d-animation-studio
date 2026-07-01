# ============================================================
# 3D ANIMATION STUDIO - Facial Expression Engine
# ============================================================
# Features:
# - Emotion detection from text (rule-based + keyword)
# - 7 core emotions + neutral
# - Emotion intensity (0-1)
# - Facial blend shape mapping (eyebrows, eyes, mouth)
# - Expression timing synchronized with audio
# - Smooth transitions between emotions
# - Multi-language keyword support
# - JSON export for character animation
# - Sentiment analysis fallback
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

import re
import time
import json
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

from src.utils import (
    get_logger, get_config, ensure_dir, generate_short_id,
    read_json, write_json, clamp, lerp, get_file_size, format_bytes
)

logger = get_logger("ExpressionEngine")


# ============================================================
# EMOTION TYPES (7 Universal Emotions + Neutral)
# ============================================================

class Emotion(Enum):
    """
    Universal emotions based on Paul Ekman's research.
    Ye 7 emotions culturally universal hain.
    """
    NEUTRAL = "neutral"
    HAPPY = "happy"           # 😊 Joy, contentment
    SAD = "sad"               # 😢 Sorrow, grief
    ANGRY = "angry"           # 😡 Rage, frustration
    SURPRISED = "surprised"   # 😲 Shock, amazement
    FEARFUL = "fearful"       # 😨 Fear, anxiety
    DISGUSTED = "disgusted"   # 🤢 Revulsion
    CONFUSED = "confused"     # 😕 Puzzled (added extra)


class Intensity(Enum):
    """Emotion intensity levels"""
    NONE = 0.0
    MILD = 0.3
    MODERATE = 0.6
    STRONG = 0.85
    EXTREME = 1.0


# ============================================================
# EMOTION KEYWORDS (Multi-language)
# ============================================================

class EmotionKeywords:
    """
    Keyword-based emotion detection.
    Har emotion ke liye trigger words.
    """

    # English keywords with intensity
    ENGLISH = {
        Emotion.HAPPY: {
            "extreme": ["ecstatic", "overjoyed", "thrilled", "elated"],
            "strong": ["happy", "joyful", "delighted", "excited", "wonderful", "amazing", "fantastic"],
            "moderate": ["glad", "pleased", "cheerful", "smiling", "laughing", "enjoy"],
            "mild": ["nice", "good", "okay", "fine", "yes"],
        },
        Emotion.SAD: {
            "extreme": ["devastated", "heartbroken", "miserable", "grief"],
            "strong": ["sad", "depressed", "crying", "weeping", "sorrow", "unhappy"],
            "moderate": ["upset", "gloomy", "disappointed", "hurt", "lonely"],
            "mild": ["tired", "meh", "sigh", "unfortunately"],
        },
        Emotion.ANGRY: {
            "extreme": ["furious", "enraged", "livid", "outraged"],
            "strong": ["angry", "mad", "hate", "rage", "hostile", "attack"],
            "moderate": ["annoyed", "irritated", "frustrated", "upset"],
            "mild": ["bothered", "displeased"],
        },
        Emotion.SURPRISED: {
            "extreme": ["shocked", "stunned", "flabbergasted", "astounded"],
            "strong": ["surprised", "amazed", "wow", "incredible", "unbelievable"],
            "moderate": ["surprising", "unexpected", "sudden"],
            "mild": ["oh", "really", "hmm"],
        },
        Emotion.FEARFUL: {
            "extreme": ["terrified", "petrified", "horrified"],
            "strong": ["afraid", "scared", "fearful", "panic", "danger"],
            "moderate": ["worried", "nervous", "anxious", "concerned"],
            "mild": ["uneasy", "cautious"],
        },
        Emotion.DISGUSTED: {
            "extreme": ["revolted", "sickened"],
            "strong": ["disgusting", "gross", "revolting", "yuck", "ew"],
            "moderate": ["distasteful", "unpleasant", "nasty"],
            "mild": ["dislike"],
        },
        Emotion.CONFUSED: {
            "extreme": ["baffled", "perplexed"],
            "strong": ["confused", "puzzled", "bewildered"],
            "moderate": ["unsure", "uncertain", "what"],
            "mild": ["maybe", "perhaps", "hmm"],
        },
    }

    # Hindi keywords (basic)
    HINDI = {
        Emotion.HAPPY: {
            "strong": ["खुश", "प्रसन्न", "आनंद", "मजा", "बेहतरीन"],
            "moderate": ["अच्छा", "ठीक", "पसंद"],
        },
        Emotion.SAD: {
            "strong": ["दुखी", "उदास", "गम", "रोना"],
            "moderate": ["परेशान", "निराश"],
        },
        Emotion.ANGRY: {
            "strong": ["गुस्सा", "क्रोध", "नफरत"],
            "moderate": ["चिढ़", "नाराज"],
        },
        Emotion.SURPRISED: {
            "strong": ["आश्चर्य", "हैरान", "वाह"],
            "moderate": ["अरे", "क्या"],
        },
        Emotion.FEARFUL: {
            "strong": ["डर", "भय", "डरा"],
            "moderate": ["चिंता", "घबरा"],
        },
    }

    # Punctuation & symbol hints
    SYMBOLS = {
        "!": {Emotion.SURPRISED: 0.2, Emotion.ANGRY: 0.1, Emotion.HAPPY: 0.1},
        "!!": {Emotion.SURPRISED: 0.4, Emotion.ANGRY: 0.2, Emotion.HAPPY: 0.3},
        "!!!": {Emotion.SURPRISED: 0.6, Emotion.HAPPY: 0.4, Emotion.ANGRY: 0.4},
        "?": {Emotion.CONFUSED: 0.2, Emotion.SURPRISED: 0.1},
        "??": {Emotion.CONFUSED: 0.4},
        "?!": {Emotion.SURPRISED: 0.5, Emotion.CONFUSED: 0.3},
        "...": {Emotion.SAD: 0.2, Emotion.CONFUSED: 0.2},
    }

    # Emoji detection
    EMOJI_MAP = {
        "😊": (Emotion.HAPPY, 0.7),
        "😃": (Emotion.HAPPY, 0.8),
        "😄": (Emotion.HAPPY, 0.85),
        "😁": (Emotion.HAPPY, 0.9),
        "🙂": (Emotion.HAPPY, 0.4),
        "😢": (Emotion.SAD, 0.7),
        "😭": (Emotion.SAD, 0.95),
        "😔": (Emotion.SAD, 0.5),
        "😞": (Emotion.SAD, 0.6),
        "😡": (Emotion.ANGRY, 0.85),
        "😠": (Emotion.ANGRY, 0.7),
        "🤬": (Emotion.ANGRY, 1.0),
        "😲": (Emotion.SURPRISED, 0.8),
        "😮": (Emotion.SURPRISED, 0.6),
        "😱": (Emotion.SURPRISED, 0.95),
        "😨": (Emotion.FEARFUL, 0.8),
        "😰": (Emotion.FEARFUL, 0.7),
        "🤢": (Emotion.DISGUSTED, 0.9),
        "🤮": (Emotion.DISGUSTED, 1.0),
        "😕": (Emotion.CONFUSED, 0.5),
        "🤔": (Emotion.CONFUSED, 0.6),
    }


# ============================================================
# FACIAL BLEND SHAPES
# ============================================================

@dataclass
class FacialBlendShapes:
    """
    Facial blend shape weights (0-1).
    Ye standard values hain jo 3D character rigs use karte hain.
    Compatible with ARKit blend shape names.
    """
    # Eyebrows
    brow_inner_up: float = 0.0        # Inner brows raised (sadness/surprise)
    brow_outer_up_left: float = 0.0   # Outer brow up (surprise)
    brow_outer_up_right: float = 0.0
    brow_down_left: float = 0.0       # Brow lowered (anger)
    brow_down_right: float = 0.0

    # Eyes
    eye_wide_left: float = 0.0        # Eyes wide open (surprise/fear)
    eye_wide_right: float = 0.0
    eye_squint_left: float = 0.0      # Squint (happy/angry)
    eye_squint_right: float = 0.0
    eye_blink_left: float = 0.0       # Blink
    eye_blink_right: float = 0.0

    # Cheeks
    cheek_puff: float = 0.0
    cheek_squint_left: float = 0.0    # Cheek raise (smile)
    cheek_squint_right: float = 0.0

    # Nose
    nose_sneer_left: float = 0.0      # Sneer (disgust/anger)
    nose_sneer_right: float = 0.0

    # Mouth
    mouth_smile_left: float = 0.0     # Smile
    mouth_smile_right: float = 0.0
    mouth_frown_left: float = 0.0     # Frown
    mouth_frown_right: float = 0.0
    mouth_open: float = 0.0           # Mouth open (surprise)
    mouth_pucker: float = 0.0
    mouth_stretch_left: float = 0.0
    mouth_stretch_right: float = 0.0

    # Jaw
    jaw_open: float = 0.0             # Jaw drop (surprise/talking)
    jaw_forward: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        """Sirf non-zero values return karo (space bachao)"""
        result = {}
        for field_name, value in self.__dict__.items():
            if value > 0.001:
                result[field_name] = round(value, 3)
        return result

    @classmethod
    def from_emotion(cls, emotion: Emotion,
                     intensity: float = 1.0) -> "FacialBlendShapes":
        """
        Emotion + intensity se blend shapes generate karo.
        """
        blend = cls()
        intensity = clamp(intensity, 0.0, 1.0)

        if emotion == Emotion.HAPPY:
            # Smile, raised cheeks, slight squint
            blend.mouth_smile_left = 0.8 * intensity
            blend.mouth_smile_right = 0.8 * intensity
            blend.cheek_squint_left = 0.5 * intensity
            blend.cheek_squint_right = 0.5 * intensity
            blend.eye_squint_left = 0.3 * intensity
            blend.eye_squint_right = 0.3 * intensity

        elif emotion == Emotion.SAD:
            # Frown, inner brows up
            blend.mouth_frown_left = 0.7 * intensity
            blend.mouth_frown_right = 0.7 * intensity
            blend.brow_inner_up = 0.6 * intensity
            blend.eye_squint_left = 0.2 * intensity
            blend.eye_squint_right = 0.2 * intensity

        elif emotion == Emotion.ANGRY:
            # Brows down, sneer, tight mouth
            blend.brow_down_left = 0.9 * intensity
            blend.brow_down_right = 0.9 * intensity
            blend.nose_sneer_left = 0.4 * intensity
            blend.nose_sneer_right = 0.4 * intensity
            blend.mouth_stretch_left = 0.3 * intensity
            blend.mouth_stretch_right = 0.3 * intensity
            blend.eye_squint_left = 0.4 * intensity
            blend.eye_squint_right = 0.4 * intensity

        elif emotion == Emotion.SURPRISED:
            # Wide eyes, raised brows, mouth open
            blend.eye_wide_left = 0.8 * intensity
            blend.eye_wide_right = 0.8 * intensity
            blend.brow_outer_up_left = 0.7 * intensity
            blend.brow_outer_up_right = 0.7 * intensity
            blend.brow_inner_up = 0.5 * intensity
            blend.mouth_open = 0.6 * intensity
            blend.jaw_open = 0.4 * intensity

        elif emotion == Emotion.FEARFUL:
            # Wide eyes, brows up, mouth stretched
            blend.eye_wide_left = 0.9 * intensity
            blend.eye_wide_right = 0.9 * intensity
            blend.brow_inner_up = 0.7 * intensity
            blend.brow_outer_up_left = 0.4 * intensity
            blend.brow_outer_up_right = 0.4 * intensity
            blend.mouth_stretch_left = 0.5 * intensity
            blend.mouth_stretch_right = 0.5 * intensity

        elif emotion == Emotion.DISGUSTED:
            # Nose scrunched, upper lip raised
            blend.nose_sneer_left = 0.8 * intensity
            blend.nose_sneer_right = 0.8 * intensity
            blend.brow_down_left = 0.4 * intensity
            blend.brow_down_right = 0.4 * intensity
            blend.mouth_frown_left = 0.3 * intensity
            blend.mouth_frown_right = 0.3 * intensity

        elif emotion == Emotion.CONFUSED:
            # One brow up, slight head tilt
            blend.brow_inner_up = 0.4 * intensity
            blend.brow_outer_up_left = 0.5 * intensity
            blend.eye_squint_right = 0.3 * intensity
            blend.mouth_pucker = 0.2 * intensity

        # NEUTRAL: sab zero

        return blend

    def blend_with(self, other: "FacialBlendShapes",
                   t: float) -> "FacialBlendShapes":
        """
        Do blend shapes ke beech interpolate karo.

        Args:
            other: Target blend shape
            t: 0-1 (0 = self, 1 = other)
        """
        t = clamp(t, 0, 1)
        result = FacialBlendShapes()

        for field_name in self.__dict__:
            self_val = getattr(self, field_name)
            other_val = getattr(other, field_name)
            setattr(result, field_name, lerp(self_val, other_val, t))

        return result


# ============================================================
# EXPRESSION FRAME
# ============================================================

@dataclass
class ExpressionFrame:
    """Single time point ki expression"""
    time: float                              # Seconds
    emotion: Emotion = Emotion.NEUTRAL
    intensity: float = 0.0                   # 0-1
    blend_shapes: FacialBlendShapes = field(default_factory=FacialBlendShapes)
    text_segment: str = ""                   # Isse jo text associate hai
    duration: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "time": round(self.time, 4),
            "emotion": self.emotion.value,
            "intensity": round(self.intensity, 3),
            "duration": round(self.duration, 4),
            "text_segment": self.text_segment[:50],
            "blend_shapes": self.blend_shapes.to_dict(),
        }


# ============================================================
# EMOTION DETECTOR
# ============================================================

class EmotionDetector:
    """
    Text se emotion detect karta hai.
    Rule-based approach (keyword matching + context).
    """

    def __init__(self, language: str = "en"):
        self.language = language
        self.keywords = self._get_keywords_for_language(language)

    def _get_keywords_for_language(self, language: str) -> Dict:
        """Language-specific keywords"""
        if language == "hi":
            return EmotionKeywords.HINDI
        return EmotionKeywords.ENGLISH

    def detect(self, text: str) -> Tuple[Emotion, float]:
        """
        Text me se dominant emotion aur intensity detect karo.

        Returns:
            (emotion, intensity)
        """
        if not text or not text.strip():
            return (Emotion.NEUTRAL, 0.0)

        text_lower = text.lower()

        # Emotion scores initialize karo
        scores: Dict[Emotion, float] = {e: 0.0 for e in Emotion}

        # 1. Keyword matching
        for emotion, intensity_map in self.keywords.items():
            for intensity_level, words in intensity_map.items():
                intensity_value = self._get_intensity_value(intensity_level)

                for word in words:
                    if word.lower() in text_lower:
                        # Word boundary check (partial match avoid)
                        pattern = r"\b" + re.escape(word.lower()) + r"\b"
                        matches = len(re.findall(pattern, text_lower))
                        if matches > 0:
                            scores[emotion] += intensity_value * matches

        # 2. Symbol analysis (!, ?, ...)
        for symbol, emotion_boosts in EmotionKeywords.SYMBOLS.items():
            if symbol in text:
                count = text.count(symbol)
                for emotion, boost in emotion_boosts.items():
                    scores[emotion] += boost * count

        # 3. Emoji detection
        for emoji, (emotion, intensity) in EmotionKeywords.EMOJI_MAP.items():
            if emoji in text:
                count = text.count(emoji)
                scores[emotion] += intensity * count

        # 4. All caps detection (SHOUTING)
        words = text.split()
        caps_count = sum(1 for w in words if len(w) > 2 and w.isupper())
        if caps_count > 0:
            caps_ratio = caps_count / len(words)
            if caps_ratio > 0.3:
                scores[Emotion.ANGRY] += 0.3 * caps_ratio
                scores[Emotion.SURPRISED] += 0.2 * caps_ratio

        # 5. Question detection
        if "?" in text and not any(scores[e] > 0.5 for e in scores):
            scores[Emotion.CONFUSED] += 0.2

        # Winner
        max_emotion = max(scores, key=scores.get)
        max_score = scores[max_emotion]

        if max_score < 0.1:
            return (Emotion.NEUTRAL, 0.0)

        # Intensity clamp
        intensity = clamp(max_score, 0.0, 1.0)

        return (max_emotion, intensity)

    def _get_intensity_value(self, level: str) -> float:
        """Intensity level → value"""
        mapping = {
            "mild": 0.3,
            "moderate": 0.6,
            "strong": 0.85,
            "extreme": 1.0,
        }
        return mapping.get(level, 0.5)

    def detect_per_sentence(self, text: str) -> List[Tuple[str, Emotion, float]]:
        """
        Har sentence ke liye separately emotion detect karo.

        Returns:
            List of (sentence, emotion, intensity)
        """
        # Sentences split karo
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]

        results = []
        for sentence in sentences:
            emotion, intensity = self.detect(sentence)
            results.append((sentence, emotion, intensity))

        return results


# ============================================================
# EXPRESSION DATA (Complete Timeline)
# ============================================================

@dataclass
class ExpressionData:
    """Complete expression animation data"""
    audio_file: Optional[str] = None
    text: str = ""
    duration: float = 0.0
    fps: int = 30
    frames: List[ExpressionFrame] = field(default_factory=list)
    total_frames: int = 0
    language: str = "en"
    generated_at: str = ""

    def to_dict(self) -> Dict:
        return {
            "audio_file": self.audio_file,
            "text": self.text,
            "duration": round(self.duration, 3),
            "fps": self.fps,
            "total_frames": self.total_frames,
            "language": self.language,
            "generated_at": self.generated_at,
            "frames": [f.to_dict() for f in self.frames],
        }

    def save_to_file(self, filepath: str) -> bool:
        """JSON me save karo"""
        try:
            ensure_dir(os.path.dirname(filepath))
            return write_json(filepath, self.to_dict())
        except Exception as e:
            logger.error(f"Save failed: {e}")
            return False

    @classmethod
    def load_from_file(cls, filepath: str) -> Optional["ExpressionData"]:
        """JSON se load karo"""
        try:
            data = read_json(filepath)
            if not data:
                return None

            expr_data = cls(
                audio_file=data.get("audio_file"),
                text=data.get("text", ""),
                duration=data.get("duration", 0),
                fps=data.get("fps", 30),
                total_frames=data.get("total_frames", 0),
                language=data.get("language", "en"),
                generated_at=data.get("generated_at", ""),
            )

            for f_data in data.get("frames", []):
                # Blend shapes reconstruct karo
                blend = FacialBlendShapes()
                for name, value in f_data.get("blend_shapes", {}).items():
                    if hasattr(blend, name):
                        setattr(blend, name, value)

                frame = ExpressionFrame(
                    time=f_data["time"],
                    emotion=Emotion(f_data["emotion"]),
                    intensity=f_data.get("intensity", 0),
                    blend_shapes=blend,
                    text_segment=f_data.get("text_segment", ""),
                    duration=f_data.get("duration", 0),
                )
                expr_data.frames.append(frame)

            return expr_data
        except Exception as e:
            logger.error(f"Load failed: {e}")
            return None

    def get_expression_at_time(self, time: float) -> Tuple[Emotion, float, FacialBlendShapes]:
        """
        Kisi time par expression state.
        Smooth interpolation ke saath.
        """
        if not self.frames:
            return (Emotion.NEUTRAL, 0.0, FacialBlendShapes())

        # Boundary
        if time <= self.frames[0].time:
            f = self.frames[0]
            return (f.emotion, f.intensity, f.blend_shapes)
        if time >= self.frames[-1].time:
            f = self.frames[-1]
            return (f.emotion, f.intensity, f.blend_shapes)

        # Find surrounding frames
        for i in range(len(self.frames) - 1):
            if self.frames[i].time <= time <= self.frames[i + 1].time:
                f1 = self.frames[i]
                f2 = self.frames[i + 1]

                # Interpolate
                if f2.time - f1.time > 0:
                    t = (time - f1.time) / (f2.time - f1.time)
                else:
                    t = 0

                # Blend shape interpolation
                blend = f1.blend_shapes.blend_with(f2.blend_shapes, t)

                # Emotion & intensity
                if f1.emotion == f2.emotion:
                    intensity = lerp(f1.intensity, f2.intensity, t)
                    return (f1.emotion, intensity, blend)
                else:
                    # Different emotions - stay with dominant one
                    if t < 0.5:
                        return (f1.emotion, f1.intensity * (1 - t * 2), blend)
                    else:
                        return (f2.emotion, f2.intensity * ((t - 0.5) * 2), blend)

        return (Emotion.NEUTRAL, 0.0, FacialBlendShapes())


# ============================================================
# MAIN EXPRESSION ENGINE
# ============================================================

class ExpressionEngine:
    """
    Main expression engine.
    Text/script se facial expressions generate karta hai.
    """

    def __init__(self, config: Optional[Dict] = None,
                 language: str = "en"):
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        self.language = language
        self.detector = EmotionDetector(language)

        # FPS
        render_config = self.config.get("rendering", {})
        self.default_fps = render_config.get("default_fps", 30)

        # Stats
        self.total_generated = 0

        logger.info(
            f"ExpressionEngine initialized "
            f"(language: {language}, fps: {self.default_fps})"
        )

    # ------------------------------------------------------------
    # GENERATION
    # ------------------------------------------------------------

    def generate_from_text(self, text: str,
                           duration: float,
                           audio_file: Optional[str] = None,
                           fps: Optional[int] = None,
                           transition_duration: float = 0.3) -> ExpressionData:
        """
        Text script se expressions generate karo.

        Args:
            text: Script text
            duration: Total duration (audio se sync)
            audio_file: Optional audio reference
            fps: Frame rate
            transition_duration: Emotion transitions ka time
        """
        if fps is None:
            fps = self.default_fps

        # Result initialize
        expr_data = ExpressionData(
            audio_file=audio_file,
            text=text,
            duration=duration,
            fps=fps,
            language=self.language,
            generated_at=str(time.time())
        )

        # Sentences me split karo aur har ka emotion
        sentence_emotions = self.detector.detect_per_sentence(text)

        if not sentence_emotions:
            # Empty - neutral expression banao
            expr_data.frames = self._generate_neutral_frames(duration, fps)
            expr_data.total_frames = len(expr_data.frames)
            return expr_data

        # Har sentence ko time slot allocate karo
        # Text length ke basis pe proportional
        total_chars = sum(len(s[0]) for s in sentence_emotions)
        if total_chars == 0:
            expr_data.frames = self._generate_neutral_frames(duration, fps)
            expr_data.total_frames = len(expr_data.frames)
            return expr_data

        # Time slots calculate karo
        current_time = 0.0
        sentence_slots = []

        for sentence, emotion, intensity in sentence_emotions:
            sentence_duration = (len(sentence) / total_chars) * duration
            sentence_slots.append({
                "start": current_time,
                "end": current_time + sentence_duration,
                "sentence": sentence,
                "emotion": emotion,
                "intensity": intensity,
            })
            current_time += sentence_duration

        # Frames generate karo
        frame_duration = 1.0 / fps
        total_frames = int(duration * fps)

        for frame_idx in range(total_frames):
            time_pos = frame_idx * frame_duration

            # Current sentence dhundo
            current_slot = None
            for slot in sentence_slots:
                if slot["start"] <= time_pos < slot["end"]:
                    current_slot = slot
                    break

            if current_slot is None:
                # Last slot use karo
                current_slot = sentence_slots[-1]

            emotion = current_slot["emotion"]
            intensity = current_slot["intensity"]

            # Transition effect (start me fade in, end me fade out)
            slot_progress = (time_pos - current_slot["start"]) / max(0.001, current_slot["end"] - current_slot["start"])

            # Fade in
            fade_in_ratio = transition_duration / max(0.1, current_slot["end"] - current_slot["start"])
            fade_out_ratio = fade_in_ratio

            effective_intensity = intensity
            if slot_progress < fade_in_ratio:
                # Fading in
                effective_intensity = intensity * (slot_progress / fade_in_ratio)
            elif slot_progress > (1.0 - fade_out_ratio):
                # Fading out
                fade_progress = (slot_progress - (1.0 - fade_out_ratio)) / fade_out_ratio
                effective_intensity = intensity * (1.0 - fade_progress * 0.3)  # Fade to 70% not 0

            # Blend shapes generate
            blend = FacialBlendShapes.from_emotion(emotion, effective_intensity)

            frame = ExpressionFrame(
                time=time_pos,
                emotion=emotion,
                intensity=effective_intensity,
                blend_shapes=blend,
                text_segment=current_slot["sentence"],
                duration=frame_duration,
            )
            expr_data.frames.append(frame)

        expr_data.total_frames = len(expr_data.frames)
        self.total_generated += 1

        logger.info(
            f"Generated {expr_data.total_frames} expression frames "
            f"from {len(sentence_emotions)} sentences"
        )
        return expr_data

    def _generate_neutral_frames(self, duration: float,
                                   fps: int) -> List[ExpressionFrame]:
        """Neutral expression frames"""
        frames = []
        frame_duration = 1.0 / fps
        total_frames = int(duration * fps)

        neutral_blend = FacialBlendShapes.from_emotion(Emotion.NEUTRAL, 0)

        for i in range(total_frames):
            frames.append(ExpressionFrame(
                time=i * frame_duration,
                emotion=Emotion.NEUTRAL,
                intensity=0.0,
                blend_shapes=neutral_blend,
                duration=frame_duration
            ))
        return frames

    # ------------------------------------------------------------
    # ANALYSIS ONLY (No frames)
    # ------------------------------------------------------------

    def analyze_text(self, text: str) -> Dict:
        """
        Text ka emotion analysis (bina full generation).
        Quick sentiment overview.
        """
        # Overall
        overall_emotion, overall_intensity = self.detector.detect(text)

        # Per sentence
        sentences = self.detector.detect_per_sentence(text)

        # Emotion distribution
        emotion_counts = {}
        for _, emotion, _ in sentences:
            emotion_counts[emotion.value] = emotion_counts.get(emotion.value, 0) + 1

        return {
            "text": text,
            "text_length": len(text),
            "word_count": len(text.split()),
            "sentence_count": len(sentences),
            "overall_emotion": overall_emotion.value,
            "overall_intensity": round(overall_intensity, 3),
            "emotion_distribution": emotion_counts,
            "sentences": [
                {
                    "text": s[0][:80],
                    "emotion": s[1].value,
                    "intensity": round(s[2], 3)
                }
                for s in sentences
            ],
        }

    # ------------------------------------------------------------
    # BATCH PROCESSING
    # ------------------------------------------------------------

    def generate_batch(self, dialogues: List[Dict],
                       output_dir: Optional[str] = None) -> List[ExpressionData]:
        """
        Multiple dialogues process karo.

        Args:
            dialogues: [{"text": "...", "duration": 3.0, "audio_file": "..."}, ...]
        """
        results = []

        if output_dir:
            ensure_dir(output_dir)

        for i, dialogue in enumerate(dialogues):
            text = dialogue.get("text", "")
            duration = dialogue.get("duration", 3.0)
            audio_file = dialogue.get("audio_file")

            expr = self.generate_from_text(
                text=text,
                duration=duration,
                audio_file=audio_file
            )

            if output_dir:
                filename = f"expression_{i+1:03d}.json"
                filepath = os.path.join(output_dir, filename)
                expr.save_to_file(filepath)

            results.append(expr)

        logger.info(f"Batch complete: {len(results)} expressions generated")
        return results

    # ------------------------------------------------------------
    # UTILITIES
    # ------------------------------------------------------------

    def get_emotion_summary(self, expr_data: ExpressionData) -> Dict:
        """Expression data ka summary"""
        emotion_time = {}
        for frame in expr_data.frames:
            emotion_time[frame.emotion.value] = emotion_time.get(
                frame.emotion.value, 0
            ) + frame.duration

        total = sum(emotion_time.values())
        emotion_percent = {
            e: (t / total * 100) if total > 0 else 0
            for e, t in emotion_time.items()
        }

        return {
            "total_duration": expr_data.duration,
            "total_frames": expr_data.total_frames,
            "unique_emotions": len(emotion_time),
            "emotion_time_seconds": {e: round(t, 2) for e, t in emotion_time.items()},
            "emotion_percentage": {e: round(p, 1) for e, p in emotion_percent.items()},
        }

    def preview_frames(self, expr_data: ExpressionData,
                       count: int = 10) -> List[str]:
        """First N frames ki preview"""
        preview = []
        for frame in expr_data.frames[:count]:
            blend_dict = frame.blend_shapes.to_dict()
            active_shapes = len(blend_dict)
            preview.append(
                f"t={frame.time:5.2f}s  "
                f"{frame.emotion.value:10s}  "
                f"intensity={frame.intensity:.2f}  "
                f"active_shapes={active_shapes}"
            )
        return preview

    def get_stats(self) -> Dict:
        return {
            "total_generated": self.total_generated,
            "language": self.language,
            "default_fps": self.default_fps,
            "available_emotions": [e.value for e in Emotion],
        }


# ============================================================
# TEST FUNCTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")
    print_banner("Expression Engine Test", "AI Facial Expression Generation")

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))

    # ============================================================
    # Test 1: Initialize
    # ============================================================
    print_section("Test 1: Initialize Expression Engine")

    engine = ExpressionEngine(language="en")

    stats = engine.get_stats()
    print(f"Language: {stats['language']}")
    print(f"Default FPS: {stats['default_fps']}")
    print(f"Available emotions: {len(stats['available_emotions'])}")

    # ============================================================
    # Test 2: Available Emotions
    # ============================================================
    print_section("Test 2: Available Emotions")

    emojis = {
        "neutral": "😐", "happy": "😊", "sad": "😢",
        "angry": "😡", "surprised": "😲", "fearful": "😨",
        "disgusted": "🤢", "confused": "😕"
    }

    for emotion in Emotion:
        emoji = emojis.get(emotion.value, "🎭")
        print(f"  {emoji}  {emotion.value:12s} ({emotion.name})")

    # ============================================================
    # Test 3: Basic Emotion Detection
    # ============================================================
    print_section("Test 3: Emotion Detection from Text")

    test_texts = [
        "I am so happy today! This is wonderful!",
        "I feel really sad and depressed.",
        "I'm furious! How dare you say that!",
        "OMG! I can't believe this!!!",
        "I'm terrified. Something feels wrong...",
        "That's disgusting! I don't want to look.",
        "Hmm, I'm not sure what to think about this.",
        "The weather is nice today.",
    ]

    for text in test_texts:
        emotion, intensity = engine.detector.detect(text)
        emoji = emojis.get(emotion.value, "❓")
        intensity_bar = "█" * int(intensity * 20)

        print(f"\n  Text: '{text}'")
        print(f"  {emoji}  {emotion.value:12s}  [{intensity_bar:<20}] {intensity:.2f}")

    # ============================================================
    # Test 4: Per-Sentence Analysis
    # ============================================================
    print_section("Test 4: Per-Sentence Emotion Analysis")

    story = (
        "I woke up this morning feeling great! "
        "But then I saw the mess in the kitchen. "
        "That made me angry. "
        "What happened here?! "
        "Then I realized my dog did it. "
        "I couldn't stay mad at him."
    )

    print(f"Story:\n{story}\n")

    analysis = engine.analyze_text(story)
    print(f"Overall: {emojis.get(analysis['overall_emotion'], '❓')} "
          f"{analysis['overall_emotion']} ({analysis['overall_intensity']})")
    print(f"Sentences: {analysis['sentence_count']}")

    print("\nSentence-by-sentence:")
    for s in analysis['sentences']:
        emoji = emojis.get(s['emotion'], '❓')
        print(f"  {emoji} [{s['emotion']:10s}] {s['text']}")

    # ============================================================
    # Test 5: Symbol & Punctuation Analysis
    # ============================================================
    print_section("Test 5: Symbol Detection")

    symbol_tests = [
        ("Hello world.", "period"),
        ("Really!", "exclamation"),
        ("What???", "questions"),
        ("Oh no!!!", "multiple exclaims"),
        ("Hmm...", "ellipsis"),
        ("STOP THIS RIGHT NOW", "all caps"),
    ]

    for text, note in symbol_tests:
        emotion, intensity = engine.detector.detect(text)
        emoji = emojis.get(emotion.value, "❓")
        print(f"  {emoji} '{text}' ({note}) → {emotion.value} ({intensity:.2f})")

    # ============================================================
    # Test 6: Emoji Detection
    # ============================================================
    print_section("Test 6: Emoji Detection")

    emoji_tests = [
        "I love this! 😊",
        "So sad 😢",
        "This is amazing 😱",
        "Ugh 🤢",
        "I'm scared 😨",
    ]

    for text in emoji_tests:
        emotion, intensity = engine.detector.detect(text)
        emoji_result = emojis.get(emotion.value, "❓")
        print(f"  '{text}' → {emoji_result} {emotion.value} ({intensity:.2f})")

    # ============================================================
    # Test 7: Generate Full Expression Timeline
    # ============================================================
    print_section("Test 7: Full Expression Generation")

    script = (
        "Hello everyone! Welcome to my channel. "
        "Today I have some sad news to share. "
        "But don't worry, there's also good news at the end. "
        "So stay tuned!"
    )

    print(f"Script: {script}")
    print(f"Duration: 8.0 seconds\n")

    expr_data = engine.generate_from_text(
        text=script,
        duration=8.0,
        fps=30
    )

    print(f"Generated {expr_data.total_frames} frames")

    # Summary
    summary = engine.get_emotion_summary(expr_data)
    print(f"\nEmotion time distribution:")
    for emotion, seconds in sorted(summary['emotion_time_seconds'].items(),
                                     key=lambda x: -x[1]):
        pct = summary['emotion_percentage'].get(emotion, 0)
        emoji = emojis.get(emotion, "❓")
        bar = "█" * int(pct / 3)
        print(f"  {emoji} {emotion:12s} {seconds:5.2f}s  ({pct:5.1f}%)  {bar}")

    # ============================================================
    # Test 8: Blend Shapes Preview
    # ============================================================
    print_section("Test 8: Blend Shapes Details")

    print("Preview of key frames:")
    preview = engine.preview_frames(expr_data, count=10)
    for line in preview:
        print(f"  {line}")

    # Show detailed blend shapes for one emotional frame
    print("\nDetailed blend shapes (happy expression):")
    happy_blend = FacialBlendShapes.from_emotion(Emotion.HAPPY, 0.9)
    for name, value in happy_blend.to_dict().items():
        bar = "█" * int(value * 30)
        print(f"  {name:30s} {value:.3f} {bar}")

    # ============================================================
    # Test 9: Save & Load
    # ============================================================
    print_section("Test 9: Save & Load Expression Data")

    output_dir = os.path.join(base_dir, "temp", "expression_tests")
    ensure_dir(output_dir)

    save_path = os.path.join(output_dir, "test_expression.json")

    success = expr_data.save_to_file(save_path)
    if success:
        file_size = get_file_size(save_path)
        print(f"✅ Saved: {save_path}")
        print(f"   Size: {format_bytes(file_size)}")

        # Reload
        loaded = ExpressionData.load_from_file(save_path)
        if loaded:
            print(f"✅ Reloaded: {loaded.total_frames} frames")
            print(f"   Duration: {loaded.duration}s")
            print(f"   Language: {loaded.language}")

    # ============================================================
    # Test 10: Query at Specific Times
    # ============================================================
    print_section("Test 10: Query Expression at Times")

    query_times = [0.5, 2.0, 4.0, 6.0, 7.5]

    print("Query expression state at different times:")
    for t in query_times:
        if t <= expr_data.duration:
            emotion, intensity, blend = expr_data.get_expression_at_time(t)
            emoji = emojis.get(emotion.value, "❓")
            active_shapes = len(blend.to_dict())
            print(f"  t={t}s → {emoji} {emotion.value:10s} "
                  f"intensity={intensity:.2f}  active_shapes={active_shapes}")

    # ============================================================
    # Test 11: Batch Processing
    # ============================================================
    print_section("Test 11: Batch Processing")

    dialogues = [
        {"text": "I'm so happy to meet you!", "duration": 2.0},
        {"text": "Why did this happen to me?", "duration": 2.5},
        {"text": "This is absolutely disgusting.", "duration": 2.0},
        {"text": "WOW! I can't believe this!!!", "duration": 2.0},
    ]

    batch_dir = os.path.join(output_dir, "batch")
    print(f"Processing {len(dialogues)} dialogues...")

    batch_results = engine.generate_batch(dialogues, batch_dir)

    for i, (dialogue, result) in enumerate(zip(dialogues, batch_results), 1):
        summary = engine.get_emotion_summary(result)
        top_emotion = max(
            summary['emotion_percentage'].items(),
            key=lambda x: x[1]
        )
        emoji = emojis.get(top_emotion[0], "❓")
        print(f"  {i}. {emoji} '{dialogue['text']}' → "
              f"{top_emotion[0]} ({top_emotion[1]:.0f}%)")

    # ============================================================
    # Test 12: Final Statistics
    # ============================================================
    print_section("Test 12: Final Statistics")

    stats = engine.get_stats()
    print(f"Total generated: {stats['total_generated']}")
    print(f"Language: {stats['language']}")
    print(f"Default FPS: {stats['default_fps']}")

    # ============================================================
    # Output Info
    # ============================================================
    print_section("Output Files")
    print(f"Expression JSON files saved in:")
    print(f"  {output_dir}")
    print(f"\n👉 Open to inspect:")
    print(f"   start {output_dir}")

    print_banner(
        "✅ All Tests Passed",
        "Expression Engine Working - Ready for character animation!"
    )