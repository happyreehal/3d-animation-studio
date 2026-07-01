# ============================================================
# 3D ANIMATION STUDIO - Keyframe Animation System
# ============================================================
# Features:
# - Keyframe-based property animation
# - Multi-property tracks (position, rotation, scale, etc.)
# - Multiple interpolation modes:
#   * Linear, Step, Bezier
#   * Easing: quad, cubic, quart, quint, sine, expo
#   * Special: back, elastic, bounce
# - Custom tangent handles (Bezier)
# - Auto-tangent smoothing
# - Vector properties (Vec3 for position/rotation)
# - Color animation (RGB interpolation)
# - Keyframe presets library
# - Animation baking (convert to frame-by-frame)
# - Property binding (link across objects)
# - JSON serialization
# - Timeline integration
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
import copy
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Callable, Any, Union

import numpy as np

from src.utils import (
    get_logger, get_config, ensure_dir, generate_short_id,
    get_timestamp, format_duration, read_json, write_json,
    clamp, lerp,
)

logger = get_logger("Keyframe")


# ============================================================
# CONSTANTS & ENUMS
# ============================================================

class InterpolationType(Enum):
    """
    Keyframes ke beech values kaise interpolate hongi.
    Har type ka apna curve hai.
    """
    # Basic
    STEP        = "step"          # No interpolation (hold value)
    LINEAR      = "linear"        # Straight line
    BEZIER      = "bezier"        # Custom curve with tangents

    # Easing (Robert Penner's equations)
    EASE_IN         = "ease_in"           # Slow start, fast end
    EASE_OUT        = "ease_out"          # Fast start, slow end
    EASE_IN_OUT     = "ease_in_out"       # Slow start & end
    EASE_IN_QUAD    = "ease_in_quad"
    EASE_IN_OUT_QUAD   = "ease_in_out_quad"
    EASE_IN_OUT_CUBIC  = "ease_in_out_cubic"
    EASE_IN_OUT_SINE   = "ease_in_out_sine" 
    EASE_OUT_QUAD   = "ease_out_quad"
    EASE_IN_CUBIC   = "ease_in_cubic"
    EASE_OUT_CUBIC  = "ease_out_cubic"
    EASE_IN_QUART   = "ease_in_quart"
    EASE_OUT_QUART  = "ease_out_quart"
    EASE_IN_SINE    = "ease_in_sine"
    EASE_OUT_SINE   = "ease_out_sine"
    EASE_IN_EXPO    = "ease_in_expo"
    EASE_OUT_EXPO   = "ease_out_expo"

    # Special
    BACK        = "back"          # Overshoot & come back
    ELASTIC     = "elastic"       # Spring bounce
    BOUNCE      = "bounce"        # Ball bounce


class PropertyType(Enum):
    """
    Animatable property types.
    Har type ka alag interpolation logic hai.
    """
    FLOAT       = "float"         # Single number (opacity, FOV)
    INT         = "int"           # Integer (frame index)
    VEC2        = "vec2"          # 2D vector (UV, screen pos)
    VEC3        = "vec3"          # 3D vector (position, rotation, scale)
    VEC4        = "vec4"          # 4D vector (quaternion, RGBA)
    COLOR       = "color"         # RGB [0-1]
    BOOL        = "bool"          # True/False (step only)


# ============================================================
# EASING FUNCTIONS — Robert Penner's Equations
# ============================================================

class Easing:
    """
    🎨 Standard easing functions collection.
    Ye all t ko 0-1 range mein lete hain aur transformed 0-1 return karte hain.

    Reference: https://easings.net/
    """

    # ── LINEAR & STEP ──────────────────────────────────

    @staticmethod
    def linear(t: float) -> float:
        return t

    @staticmethod
    def step(t: float) -> float:
        """No interpolation — hold value tak next keyframe"""
        return 0.0 if t < 1.0 else 1.0

    # ── QUAD (t²) ──────────────────────────────────────

    @staticmethod
    def ease_in_quad(t: float) -> float:
        return t * t

    @staticmethod
    def ease_out_quad(t: float) -> float:
        return 1.0 - (1.0 - t) ** 2

    @staticmethod
    def ease_in_out_quad(t: float) -> float:
        if t < 0.5:
            return 2 * t * t
        return 1 - ((-2 * t + 2) ** 2) / 2

    # ── CUBIC (t³) ─────────────────────────────────────

    @staticmethod
    def ease_in_cubic(t: float) -> float:
        return t ** 3

    @staticmethod
    def ease_out_cubic(t: float) -> float:
        return 1 - (1 - t) ** 3

    @staticmethod
    def ease_in_out_cubic(t: float) -> float:
        if t < 0.5:
            return 4 * t ** 3
        return 1 - ((-2 * t + 2) ** 3) / 2

    # ── QUART (t⁴) ─────────────────────────────────────

    @staticmethod
    def ease_in_quart(t: float) -> float:
        return t ** 4

    @staticmethod
    def ease_out_quart(t: float) -> float:
        return 1 - (1 - t) ** 4

    # ── SINE ───────────────────────────────────────────

    @staticmethod
    def ease_in_sine(t: float) -> float:
        return 1 - math.cos((t * math.pi) / 2)

    @staticmethod
    def ease_out_sine(t: float) -> float:
        return math.sin((t * math.pi) / 2)

    @staticmethod
    def ease_in_out_sine(t: float) -> float:
        return -(math.cos(math.pi * t) - 1) / 2

    # ── EXPONENTIAL ────────────────────────────────────

    @staticmethod
    def ease_in_expo(t: float) -> float:
        if t == 0:
            return 0
        return 2 ** (10 * (t - 1))

    @staticmethod
    def ease_out_expo(t: float) -> float:
        if t == 1:
            return 1
        return 1 - (2 ** (-10 * t))

    # ── BACK (Overshoot) ───────────────────────────────

    @staticmethod
    def ease_in_back(t: float) -> float:
        """Slight backward motion before forward"""
        c1 = 1.70158
        c3 = c1 + 1
        return c3 * t ** 3 - c1 * t ** 2

    @staticmethod
    def ease_out_back(t: float) -> float:
        """Overshoot then settle"""
        c1 = 1.70158
        c3 = c1 + 1
        return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2

    # ── ELASTIC (Spring) ───────────────────────────────

    @staticmethod
    def ease_in_elastic(t: float) -> float:
        """Spring-like bounce at start"""
        if t == 0 or t == 1:
            return t
        c4 = (2 * math.pi) / 3
        return -(2 ** (10 * (t - 1))) * math.sin((t - 1.1) * c4)

    @staticmethod
    def ease_out_elastic(t: float) -> float:
        """Spring-like bounce at end"""
        if t == 0 or t == 1:
            return t
        c4 = (2 * math.pi) / 3
        return (2 ** (-10 * t)) * math.sin((t - 0.1) * c4) + 1

    # ── BOUNCE (Ball drop) ─────────────────────────────

    @staticmethod
    def ease_out_bounce(t: float) -> float:
        """Ball bouncing on ground"""
        n1 = 7.5625
        d1 = 2.75

        if t < 1 / d1:
            return n1 * t * t
        elif t < 2 / d1:
            t -= 1.5 / d1
            return n1 * t * t + 0.75
        elif t < 2.5 / d1:
            t -= 2.25 / d1
            return n1 * t * t + 0.9375
        else:
            t -= 2.625 / d1
            return n1 * t * t + 0.984375

    @staticmethod
    def ease_in_bounce(t: float) -> float:
        """Ball bounce inverted"""
        return 1 - Easing.ease_out_bounce(1 - t)


# ============================================================
# INTERPOLATION MAPPING
# ============================================================

# Map InterpolationType → easing function
_INTERPOLATION_FUNCTIONS: Dict[InterpolationType, Callable[[float], float]] = {
    InterpolationType.STEP           : Easing.step,
    InterpolationType.LINEAR         : Easing.linear,

    InterpolationType.EASE_IN        : Easing.ease_in_cubic,
    InterpolationType.EASE_OUT       : Easing.ease_out_cubic,
    InterpolationType.EASE_IN_OUT    : Easing.ease_in_out_cubic,

    InterpolationType.EASE_IN_QUAD   : Easing.ease_in_quad,
    InterpolationType.EASE_IN_OUT_QUAD  : Easing.ease_in_out_quad, 
    InterpolationType.EASE_IN_OUT_CUBIC : Easing.ease_in_out_cubic,
    InterpolationType.EASE_IN_OUT_SINE  : Easing.ease_in_out_sine,
    InterpolationType.EASE_OUT_QUAD  : Easing.ease_out_quad,
    InterpolationType.EASE_IN_CUBIC  : Easing.ease_in_cubic,
    InterpolationType.EASE_OUT_CUBIC : Easing.ease_out_cubic,
    InterpolationType.EASE_IN_QUART  : Easing.ease_in_quart,
    InterpolationType.EASE_OUT_QUART : Easing.ease_out_quart,
    InterpolationType.EASE_IN_SINE   : Easing.ease_in_sine,
    InterpolationType.EASE_OUT_SINE  : Easing.ease_out_sine,
    InterpolationType.EASE_IN_EXPO   : Easing.ease_in_expo,
    InterpolationType.EASE_OUT_EXPO  : Easing.ease_out_expo,

    InterpolationType.BACK           : Easing.ease_out_back,
    InterpolationType.ELASTIC        : Easing.ease_out_elastic,
    InterpolationType.BOUNCE         : Easing.ease_out_bounce,
}


def evaluate_easing(interp: InterpolationType, t: float) -> float:
    """
    Given interpolation type ke liye t (0-1) ko transform karo.

    Args:
        interp: InterpolationType
        t     : Normalized time 0-1

    Returns:
        Transformed value 0-1 (or beyond for overshoot easings)
    """
    t = clamp(t, 0.0, 1.0)
    func = _INTERPOLATION_FUNCTIONS.get(interp, Easing.linear)
    try:
        return func(t)
    except Exception as e:
        logger.debug(f"Easing '{interp.value}' failed: {e}")
        return t


# ============================================================
# BEZIER CURVE — Custom Interpolation
# ============================================================

class BezierCurve:
    """
    🎨 Cubic Bezier curve for custom easing.
    2 control points (P1, P2) between endpoints (0,0) → (1,1)

    P1(x1, y1), P2(x2, y2) both in 0-1 range.

    CSS transition-timing-function ke jaisa hai:
        ease     → cubic-bezier(0.25, 0.1, 0.25, 1.0)
        linear   → cubic-bezier(0.0,  0.0, 1.0,  1.0)
        ease-in  → cubic-bezier(0.42, 0.0, 1.0,  1.0)
    """

    def __init__(self,
                 x1: float = 0.25, y1: float = 0.1,
                 x2: float = 0.25, y2: float = 1.0):
        self.x1 = clamp(x1, 0.0, 1.0)
        self.y1 = y1  # Can overshoot
        self.x2 = clamp(x2, 0.0, 1.0)
        self.y2 = y2

    def evaluate(self, t: float) -> float:
        """
        Bezier curve evaluate karo t pe.
        Uses De Casteljau's algorithm for numeric stability.
        """
        t = clamp(t, 0.0, 1.0)

        # Cubic Bezier formula:
        # B(t) = (1-t)³P0 + 3(1-t)²t*P1 + 3(1-t)t²*P2 + t³*P3
        # P0 = (0,0), P3 = (1,1)

        # Y calculate karo (progress value)
        u   = 1 - t
        y   = 3 * u * u * t * self.y1 \
            + 3 * u * t * t * self.y2 \
            + t * t * t
        return y

    def to_dict(self) -> Dict:
        return {"x1": self.x1, "y1": self.y1, "x2": self.x2, "y2": self.y2}

    @classmethod
    def from_dict(cls, data: Dict) -> "BezierCurve":
        return cls(
            x1=data.get("x1", 0.25), y1=data.get("y1", 0.1),
            x2=data.get("x2", 0.25), y2=data.get("y2", 1.0),
        )

    # ── PRESET BEZIER CURVES ─────────────────────────────

    @classmethod
    def ease(cls) -> "BezierCurve":
        """CSS 'ease' equivalent — default smooth curve"""
        return cls(0.25, 0.1, 0.25, 1.0)

    @classmethod
    def linear(cls) -> "BezierCurve":
        return cls(0.0, 0.0, 1.0, 1.0)

    @classmethod
    def ease_in(cls) -> "BezierCurve":
        return cls(0.42, 0.0, 1.0, 1.0)

    @classmethod
    def ease_out(cls) -> "BezierCurve":
        return cls(0.0, 0.0, 0.58, 1.0)

    @classmethod
    def ease_in_out(cls) -> "BezierCurve":
        return cls(0.42, 0.0, 0.58, 1.0)

    @classmethod
    def anticipate(cls) -> "BezierCurve":
        """Slight backward movement before forward"""
        return cls(0.5, -0.5, 0.5, 1.0)


# ============================================================
# VALUE INTERPOLATION — Different types ke liye
# ============================================================

class ValueInterpolator:
    """
    🔀 Different property types ke values ko interpolate karta hai.
    Float, vector, color — sab handle karta hai.
    """

    @staticmethod
    def interpolate(from_val: Any, to_val: Any, t: float,
                    property_type: PropertyType) -> Any:
        """
        Do values ke beech interpolate karo based on property type.

        Args:
            from_val      : Start value
            to_val        : End value
            t             : Progress 0-1 (already eased)
            property_type : PropertyType enum
        """
        t = clamp(t, 0.0, 1.0)

        try:
            # BOOL — step interpolation only
            if property_type == PropertyType.BOOL:
                return to_val if t >= 0.5 else from_val

            # INT — linear then round
            elif property_type == PropertyType.INT:
                result = lerp(float(from_val), float(to_val), t)
                return int(round(result))

            # FLOAT — simple lerp
            elif property_type == PropertyType.FLOAT:
                return lerp(float(from_val), float(to_val), t)

            # VEC2, VEC3, VEC4 — component-wise lerp
            elif property_type in [PropertyType.VEC2, PropertyType.VEC3, PropertyType.VEC4]:
                from_arr = np.array(from_val, dtype=np.float32)
                to_arr   = np.array(to_val,   dtype=np.float32)
                result   = from_arr + (to_arr - from_arr) * t
                return result.tolist()

            # COLOR — RGB space lerp (simple, not perceptually accurate)
            elif property_type == PropertyType.COLOR:
                from_arr = np.array(from_val, dtype=np.float32)
                to_arr   = np.array(to_val,   dtype=np.float32)
                result   = from_arr + (to_arr - from_arr) * t
                # Clamp to 0-1
                result   = np.clip(result, 0.0, 1.0)
                return result.tolist()

            # Fallback — treat as float
            return lerp(float(from_val), float(to_val), t)

        except Exception as e:
            logger.debug(f"Interpolation failed: {e}")
            return from_val


# ============================================================
# KEYFRAME
# ============================================================

@dataclass
class Keyframe:
    """
    🔑 Single keyframe — time pe ek specific value.

    Ye animation ka basic building block hai.
    Har keyframe ka apna time, value, aur interpolation method hota hai.
    """
    id            : str                       = field(default_factory=generate_short_id)
    time          : float                     = 0.0     # Timeline pe kab
    value         : Any                       = 0.0     # Kya value hogi
    interpolation : InterpolationType         = InterpolationType.LINEAR

    # Bezier custom curve (agar interpolation == BEZIER)
    bezier_curve  : Optional[BezierCurve]     = None

    # Tangent handles (for advanced curve editor)
    tangent_in    : Optional[Tuple[float, float]] = None   # (x, y) offset
    tangent_out   : Optional[Tuple[float, float]] = None

    # Metadata
    label         : str                       = ""       # Optional label
    locked        : bool                      = False    # Prevent editing
    selected      : bool                      = False    # UI selection state

    def to_dict(self) -> Dict:
        d = {
            "id"           : self.id,
            "time"         : self.time,
            "value"        : self.value,
            "interpolation": self.interpolation.value,
            "label"        : self.label,
            "locked"       : self.locked,
        }
        if self.bezier_curve:
            d["bezier_curve"] = self.bezier_curve.to_dict()
        if self.tangent_in:
            d["tangent_in"]  = list(self.tangent_in)
        if self.tangent_out:
            d["tangent_out"] = list(self.tangent_out)
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> "Keyframe":
        kf = cls(
            id           = data.get("id", generate_short_id()),
            time         = data.get("time", 0.0),
            value        = data.get("value", 0.0),
            interpolation= InterpolationType(data.get("interpolation", "linear")),
            label        = data.get("label", ""),
            locked       = data.get("locked", False),
        )
        if "bezier_curve" in data:
            kf.bezier_curve = BezierCurve.from_dict(data["bezier_curve"])
        if "tangent_in" in data:
            kf.tangent_in   = tuple(data["tangent_in"])
        if "tangent_out" in data:
            kf.tangent_out  = tuple(data["tangent_out"])
        return kf


# ============================================================
# KEYFRAME TRACK
# ============================================================

class KeyframeTrack:
    """
    🎬 Ek property ke keyframes ka collection.

    Har KeyframeTrack ek property animate karta hai.
    Time-sorted keyframes list rakhta hai aur evaluate karta hai.

    Example:
        pos_x_track = KeyframeTrack("camera.position.x", PropertyType.FLOAT)
        pos_x_track.add_keyframe(0.0, 0.0)
        pos_x_track.add_keyframe(2.0, 10.0, InterpolationType.EASE_OUT)

        value_at_1s = pos_x_track.evaluate(1.0)  # Smooth interpolated
    """

    def __init__(self,
                 property_name: str,
                 property_type: PropertyType = PropertyType.FLOAT,
                 default_value: Any = None):
        """
        Args:
            property_name : Dot notation (e.g., "camera.position.x")
            property_type : PropertyType enum
            default_value : Value jab koi keyframe nahi (fallback)
        """
        self.id            = generate_short_id()
        self.property_name = property_name
        self.property_type = property_type
        self.default_value = default_value if default_value is not None else self._get_default()

        # Sorted keyframes list
        self.keyframes: List[Keyframe] = []

        # State
        self.enabled       = True    # Animation active?
        self.color         = "#00D4FF"

    def _get_default(self) -> Any:
        """Property type ke basis pe default value"""
        defaults = {
            PropertyType.FLOAT : 0.0,
            PropertyType.INT   : 0,
            PropertyType.VEC2  : [0.0, 0.0],
            PropertyType.VEC3  : [0.0, 0.0, 0.0],
            PropertyType.VEC4  : [0.0, 0.0, 0.0, 0.0],
            PropertyType.COLOR : [1.0, 1.0, 1.0],
            PropertyType.BOOL  : False,
        }
        return defaults.get(self.property_type, 0.0)

    # ── KEYFRAME MANAGEMENT ───────────────────────────────

    def add_keyframe(self,
                     time: float,
                     value: Any,
                     interpolation: InterpolationType = InterpolationType.LINEAR,
                     bezier_curve: Optional[BezierCurve] = None,
                     label: str = "") -> Keyframe:
        """
        Naya keyframe add karo.
        Agar same time pe keyframe hai toh replace ho jaayega.
        """
        # Existing keyframe check karo same time pe
        for i, kf in enumerate(self.keyframes):
            if abs(kf.time - time) < 0.0001:
                if kf.locked:
                    logger.warning(f"Keyframe at {time}s is locked")
                    return kf
                # Replace
                kf.value         = value
                kf.interpolation = interpolation
                if bezier_curve:
                    kf.bezier_curve = bezier_curve
                logger.debug(f"🔑 Replaced keyframe @ {time:.3f}s")
                return kf

        # Naya keyframe banao
        kf = Keyframe(
            time         = time,
            value        = value,
            interpolation= interpolation,
            bezier_curve = bezier_curve,
            label        = label,
        )
        self.keyframes.append(kf)
        # Time-sorted rakhna hai efficient lookup ke liye
        self.keyframes.sort(key=lambda k: k.time)

        logger.debug(f"🔑 Added keyframe @ {time:.3f}s ({interpolation.value})")
        return kf

    def remove_keyframe(self, kf_id: str) -> bool:
        """Keyframe remove karo by ID"""
        for i, kf in enumerate(self.keyframes):
            if kf.id == kf_id:
                if kf.locked:
                    return False
                del self.keyframes[i]
                return True
        return False

    def remove_keyframe_at_time(self, time: float,
                                 threshold: float = 0.01) -> bool:
        """Given time ke aas paas keyframe remove karo"""
        for i, kf in enumerate(self.keyframes):
            if abs(kf.time - time) < threshold:
                if kf.locked:
                    return False
                del self.keyframes[i]
                return True
        return False

    def get_keyframe(self, kf_id: str) -> Optional[Keyframe]:
        for kf in self.keyframes:
            if kf.id == kf_id:
                return kf
        return None

    def get_keyframe_at_time(self, time: float,
                              threshold: float = 0.01) -> Optional[Keyframe]:
        """Given time ke aas paas keyframe find karo"""
        for kf in self.keyframes:
            if abs(kf.time - time) < threshold:
                return kf
        return None

    def move_keyframe(self, kf_id: str, new_time: float) -> bool:
        """Keyframe ko new time pe move karo"""
        kf = self.get_keyframe(kf_id)
        if kf is None or kf.locked:
            return False

        kf.time = max(0.0, new_time)
        self.keyframes.sort(key=lambda k: k.time)
        return True

    def clear(self):
        """Sab keyframes remove karo"""
        self.keyframes = [kf for kf in self.keyframes if kf.locked]

    # ── EVALUATION — Core Interpolation Logic ─────────────

    def evaluate(self, time: float) -> Any:
        """
        Given time pe interpolated value return karo.

        Ye main function hai — timeline playback ke waqt call hota hai.
        """
        if not self.enabled or not self.keyframes:
            return self.default_value

        # Boundary cases
        first_kf = self.keyframes[0]
        last_kf  = self.keyframes[-1]

        # Time before first keyframe → use first value
        if time <= first_kf.time:
            return first_kf.value

        # Time after last keyframe → use last value
        if time >= last_kf.time:
            return last_kf.value

        # Find surrounding keyframes
        for i in range(len(self.keyframes) - 1):
            kf1 = self.keyframes[i]
            kf2 = self.keyframes[i + 1]

            if kf1.time <= time <= kf2.time:
                # Interpolate between kf1 and kf2
                return self._interpolate_between(kf1, kf2, time)

        return self.default_value

    def _interpolate_between(self, kf1: Keyframe, kf2: Keyframe,
                             time: float) -> Any:
        """Do keyframes ke beech interpolate karo"""
        duration = kf2.time - kf1.time
        if duration <= 0:
            return kf1.value

        # Normalized time (0-1)
        t = (time - kf1.time) / duration

        # Apply easing/interpolation
        if kf1.interpolation == InterpolationType.STEP:
            # Step — value hold karo
            eased_t = 0.0

        elif kf1.interpolation == InterpolationType.BEZIER and kf1.bezier_curve:
            # Custom bezier
            eased_t = kf1.bezier_curve.evaluate(t)

        else:
            # Standard easing
            eased_t = evaluate_easing(kf1.interpolation, t)

        # Value interpolate karo based on property type
        return ValueInterpolator.interpolate(
            kf1.value, kf2.value, eased_t, self.property_type
        )

    # ── UTILITY METHODS ───────────────────────────────────

    def get_duration(self) -> float:
        """Track ki total animation duration"""
        if not self.keyframes:
            return 0.0
        return self.keyframes[-1].time

    def get_time_range(self) -> Tuple[float, float]:
        """First aur last keyframe times"""
        if not self.keyframes:
            return (0.0, 0.0)
        return (self.keyframes[0].time, self.keyframes[-1].time)

    def bake(self, fps: int = 30,
             start_time: Optional[float] = None,
             end_time: Optional[float] = None) -> List[Tuple[float, Any]]:
        """
        Animation ko frame-by-frame values mein convert karo.
        Export/rendering ke liye useful.

        Returns:
            List of (time, value) tuples for every frame
        """
        if not self.keyframes:
            return []

        if start_time is None:
            start_time = self.keyframes[0].time
        if end_time is None:
            end_time = self.keyframes[-1].time

        frame_duration = 1.0 / fps
        total_frames   = int((end_time - start_time) * fps) + 1

        baked = []
        for frame in range(total_frames):
            t     = start_time + (frame * frame_duration)
            value = self.evaluate(t)
            baked.append((t, value))

        return baked

    def copy(self) -> "KeyframeTrack":
        """Track ki deep copy banao"""
        new_track = KeyframeTrack(
            property_name = self.property_name,
            property_type = self.property_type,
            default_value = copy.deepcopy(self.default_value),
        )
        new_track.enabled = self.enabled
        new_track.color   = self.color

        for kf in self.keyframes:
            new_kf = copy.deepcopy(kf)
            new_kf.id = generate_short_id()  # New ID
            new_track.keyframes.append(new_kf)

        return new_track

    # ── SERIALIZATION ─────────────────────────────────────

    def to_dict(self) -> Dict:
        return {
            "id"           : self.id,
            "property_name": self.property_name,
            "property_type": self.property_type.value,
            "default_value": self.default_value,
            "enabled"      : self.enabled,
            "color"        : self.color,
            "keyframes"    : [kf.to_dict() for kf in self.keyframes],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "KeyframeTrack":
        track = cls(
            property_name = data.get("property_name", "unknown"),
            property_type = PropertyType(data.get("property_type", "float")),
            default_value = data.get("default_value"),
        )
        track.id      = data.get("id", track.id)
        track.enabled = data.get("enabled", True)
        track.color   = data.get("color", "#00D4FF")

        for kf_data in data.get("keyframes", []):
            track.keyframes.append(Keyframe.from_dict(kf_data))
        track.keyframes.sort(key=lambda k: k.time)

        return track


# ============================================================
# ANIMATION GROUP — Multiple Tracks Together
# ============================================================

class AnimationGroup:
    """
    🎭 Multiple related tracks ka group.

    E.g., ek object ke position (x, y, z), rotation, scale
    sab ek group mein rakhte hain manage karne ke liye.

    Usage:
        char_anim = AnimationGroup("Hero Character")
        char_anim.add_track("position_x", PropertyType.FLOAT)
        char_anim.add_track("position_y", PropertyType.FLOAT)
        char_anim.add_track("rotation",   PropertyType.VEC3)

        # Get all values at time
        values = char_anim.evaluate_all(1.5)
        # {"position_x": 5.2, "position_y": 3.1, "rotation": [0, 45, 0]}
    """

    def __init__(self, name: str = "Animation Group"):
        self.id      = generate_short_id()
        self.name    = name
        self.tracks  : Dict[str, KeyframeTrack] = {}    # property_name → track
        self.enabled = True

    def add_track(self, property_name: str,
                  property_type: PropertyType = PropertyType.FLOAT,
                  default_value: Any = None) -> KeyframeTrack:
        """Naya track add karo group mein"""
        track = KeyframeTrack(property_name, property_type, default_value)
        self.tracks[property_name] = track
        logger.debug(f"🎬 Added track '{property_name}' to group '{self.name}'")
        return track

    def get_track(self, property_name: str) -> Optional[KeyframeTrack]:
        return self.tracks.get(property_name)

    def remove_track(self, property_name: str) -> bool:
        if property_name in self.tracks:
            del self.tracks[property_name]
            return True
        return False

    def evaluate_all(self, time: float) -> Dict[str, Any]:
        """Sab tracks ki values ek dict mein return karo"""
        if not self.enabled:
            return {}

        result = {}
        for prop_name, track in self.tracks.items():
            result[prop_name] = track.evaluate(time)
        return result

    def get_duration(self) -> float:
        """Group ki max duration"""
        if not self.tracks:
            return 0.0
        return max(t.get_duration() for t in self.tracks.values())

    def get_all_keyframe_times(self) -> List[float]:
        """Sab tracks ke unique keyframe times (sorted)"""
        times = set()
        for track in self.tracks.values():
            for kf in track.keyframes:
                times.add(kf.time)
        return sorted(times)

    def to_dict(self) -> Dict:
        return {
            "id"     : self.id,
            "name"   : self.name,
            "enabled": self.enabled,
            "tracks" : {name: t.to_dict() for name, t in self.tracks.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "AnimationGroup":
        group = cls(name=data.get("name", "Group"))
        group.id      = data.get("id", group.id)
        group.enabled = data.get("enabled", True)

        for prop_name, track_data in data.get("tracks", {}).items():
            group.tracks[prop_name] = KeyframeTrack.from_dict(track_data)

        return group


# ============================================================
# KEYFRAME PRESETS — Ready-made Animations
# ============================================================

class KeyframePresets:
    """
    🎨 Ready-made animation presets — common animations ke liye.
    """

    @staticmethod
    def fade_in(duration: float = 1.0,
                start_time: float = 0.0) -> KeyframeTrack:
        """Opacity 0 → 1 fade in"""
        track = KeyframeTrack("opacity", PropertyType.FLOAT, default_value=0.0)
        track.add_keyframe(start_time, 0.0, InterpolationType.EASE_OUT)
        track.add_keyframe(start_time + duration, 1.0)
        return track

    @staticmethod
    def fade_out(duration: float = 1.0,
                 start_time: float = 0.0) -> KeyframeTrack:
        """Opacity 1 → 0 fade out"""
        track = KeyframeTrack("opacity", PropertyType.FLOAT, default_value=1.0)
        track.add_keyframe(start_time, 1.0, InterpolationType.EASE_IN)
        track.add_keyframe(start_time + duration, 0.0)
        return track

    @staticmethod
    def slide_in_from_left(distance: float = 100.0,
                           duration: float = 0.6,
                           start_time: float = 0.0) -> KeyframeTrack:
        """Position X: -distance → 0"""
        track = KeyframeTrack("position_x", PropertyType.FLOAT)
        track.add_keyframe(start_time, -distance, InterpolationType.EASE_OUT_QUART)
        track.add_keyframe(start_time + duration, 0.0)
        return track

    @staticmethod
    def bounce_in(duration: float = 1.0,
                  start_time: float = 0.0) -> KeyframeTrack:
        """Scale 0 → 1 with bounce"""
        track = KeyframeTrack("scale", PropertyType.FLOAT, default_value=0.0)
        track.add_keyframe(start_time, 0.0, InterpolationType.BOUNCE)
        track.add_keyframe(start_time + duration, 1.0)
        return track

    @staticmethod
    def elastic_appear(duration: float = 0.8,
                       start_time: float = 0.0) -> KeyframeTrack:
        """Elastic scale entrance"""
        track = KeyframeTrack("scale", PropertyType.FLOAT, default_value=0.0)
        track.add_keyframe(start_time, 0.0, InterpolationType.ELASTIC)
        track.add_keyframe(start_time + duration, 1.0)
        return track

    @staticmethod
    def rotate_360(duration: float = 2.0,
                   start_time: float = 0.0,
                   axis: str = "y") -> KeyframeTrack:
        """Full 360° rotation"""
        track = KeyframeTrack(f"rotation_{axis}", PropertyType.FLOAT)
        track.add_keyframe(start_time, 0.0, InterpolationType.LINEAR)
        track.add_keyframe(start_time + duration, 360.0)
        return track

    @staticmethod
    def pulse(base_value: float = 1.0,
              peak_value: float = 1.2,
              cycles: int = 3,
              duration: float = 1.5,
              start_time: float = 0.0) -> KeyframeTrack:
        """Pulse effect — scale grow/shrink repeatedly"""
        track = KeyframeTrack("scale", PropertyType.FLOAT, default_value=base_value)
        cycle_duration = duration / cycles

        for i in range(cycles):
            cycle_start = start_time + i * cycle_duration
            track.add_keyframe(cycle_start, base_value, InterpolationType.EASE_IN_OUT_SINE)
            track.add_keyframe(cycle_start + cycle_duration / 2, peak_value,
                              InterpolationType.EASE_IN_OUT_SINE)

        track.add_keyframe(start_time + duration, base_value)
        return track

    @staticmethod
    def camera_pan(from_pos: List[float],
                   to_pos: List[float],
                   duration: float = 3.0,
                   start_time: float = 0.0) -> KeyframeTrack:
        """Camera position pan (VEC3)"""
        track = KeyframeTrack("camera_position", PropertyType.VEC3)
        track.add_keyframe(start_time, from_pos, InterpolationType.EASE_IN_OUT_CUBIC)
        track.add_keyframe(start_time + duration, to_pos)
        return track

    @staticmethod
    def color_flash(from_color: List[float] = None,
                    flash_color: List[float] = None,
                    duration: float = 0.3,
                    start_time: float = 0.0) -> KeyframeTrack:
        """Quick color flash effect"""
        if from_color is None:
            from_color = [1.0, 1.0, 1.0]
        if flash_color is None:
            flash_color = [1.0, 0.3, 0.3]  # Red flash

        track = KeyframeTrack("color", PropertyType.COLOR, default_value=from_color)
        track.add_keyframe(start_time, from_color, InterpolationType.EASE_IN)
        track.add_keyframe(start_time + duration / 2, flash_color, InterpolationType.EASE_OUT)
        track.add_keyframe(start_time + duration, from_color)
        return track


# ============================================================
# MAIN KEYFRAME ENGINE
# ============================================================

class KeyframeEngine:
    """
    🎬 Main Keyframe Animation Engine

    Central hub — sab animation groups aur tracks manage karta hai.
    Timeline se integrate hota hai.
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

        # FPS
        render_cfg = self.config.get("rendering", {})
        self.fps   = render_cfg.get("default_fps", 30)

        # Animation groups (objects)
        self.groups: Dict[str, AnimationGroup] = {}

        # Standalone tracks (not in any group)
        self.tracks: Dict[str, KeyframeTrack] = {}

        # Stats
        self._stats = {
            "total_evaluations": 0,
            "total_bakes"      : 0,
        }

        logger.info(f"🎬 KeyframeEngine initialized (fps: {self.fps})")

    # ── GROUP MANAGEMENT ──────────────────────────────────

    def create_group(self, name: str) -> AnimationGroup:
        """Naya animation group banao"""
        group = AnimationGroup(name)
        self.groups[group.id] = group
        logger.info(f"🎭 Group created: '{name}'")
        return group

    def get_group(self, group_id: str) -> Optional[AnimationGroup]:
        return self.groups.get(group_id)

    def get_group_by_name(self, name: str) -> Optional[AnimationGroup]:
        for g in self.groups.values():
            if g.name == name:
                return g
        return None

    def remove_group(self, group_id: str) -> bool:
        if group_id in self.groups:
            del self.groups[group_id]
            return True
        return False

    # ── TRACK MANAGEMENT ──────────────────────────────────

    def create_track(self,
                     property_name: str,
                     property_type: PropertyType = PropertyType.FLOAT,
                     default_value: Any = None) -> KeyframeTrack:
        """Standalone track banao (kisi group mein nahi)"""
        track = KeyframeTrack(property_name, property_type, default_value)
        self.tracks[track.id] = track
        return track

    def add_track(self, track: KeyframeTrack) -> str:
        """Existing track add karo"""
        self.tracks[track.id] = track
        return track.id

    # ── EVALUATION ────────────────────────────────────────

    def evaluate_all(self, time: float) -> Dict[str, Dict[str, Any]]:
        """
        Sab groups aur tracks ke values evaluate karo given time pe.

        Returns:
            {
                "group_name": {"property1": value, "property2": value},
                ...
            }
        """
        result = {}

        # Groups evaluate karo
        for group_id, group in self.groups.items():
            result[group.name] = group.evaluate_all(time)

        # Standalone tracks
        if self.tracks:
            standalone = {}
            for track in self.tracks.values():
                standalone[track.property_name] = track.evaluate(time)
            result["_standalone"] = standalone

        self._stats["total_evaluations"] += 1
        return result

    # ── BAKING ────────────────────────────────────────────

    def bake_all(self,
                 fps: Optional[int] = None,
                 start_time: float = 0.0,
                 end_time: Optional[float] = None) -> Dict:
        """
        Sab animations ko frame-by-frame data mein convert karo.
        Rendering / export ke liye.
        """
        if fps is None:
            fps = self.fps

        if end_time is None:
            end_time = self.get_max_duration()

        result = {
            "fps"       : fps,
            "start_time": start_time,
            "end_time"  : end_time,
            "groups"    : {},
            "tracks"    : {},
        }

        # Groups bake karo
        for group in self.groups.values():
            group_data = {}
            for prop_name, track in group.tracks.items():
                group_data[prop_name] = track.bake(fps, start_time, end_time)
            result["groups"][group.name] = group_data

        # Standalone tracks
        for track in self.tracks.values():
            result["tracks"][track.property_name] = track.bake(fps, start_time, end_time)

        self._stats["total_bakes"] += 1
        logger.info(f"🍞 Baked animation: {start_time:.1f}s → {end_time:.1f}s @ {fps}fps")
        return result

    # ── UTILITIES ─────────────────────────────────────────

    def get_max_duration(self) -> float:
        """Sab animations ka max duration"""
        max_dur = 0.0
        for g in self.groups.values():
            max_dur = max(max_dur, g.get_duration())
        for t in self.tracks.values():
            max_dur = max(max_dur, t.get_duration())
        return max_dur

    def get_all_keyframe_times(self) -> List[float]:
        """Sab groups/tracks ke unique keyframe times"""
        times = set()
        for g in self.groups.values():
            times.update(g.get_all_keyframe_times())
        for t in self.tracks.values():
            for kf in t.keyframes:
                times.add(kf.time)
        return sorted(times)

    def clear_all(self):
        """Sab animations clear karo"""
        self.groups.clear()
        self.tracks.clear()
        logger.info("🗑️  Cleared all animations")

    # ── SERIALIZATION ─────────────────────────────────────

    def save_to_file(self, filepath: str) -> bool:
        """JSON mein save karo"""
        try:
            data = {
                "fps"    : self.fps,
                "groups" : {gid: g.to_dict() for gid, g in self.groups.items()},
                "tracks" : {tid: t.to_dict() for tid, t in self.tracks.items()},
                "saved_at": get_timestamp(),
            }
            ensure_dir(os.path.dirname(filepath))
            return write_json(filepath, data)
        except Exception as e:
            logger.error(f"Save failed: {e}")
            return False

    def load_from_file(self, filepath: str) -> bool:
        """JSON se load karo"""
        try:
            data = read_json(filepath)
            if not data:
                return False

            self.fps = data.get("fps", 30)
            self.groups.clear()
            self.tracks.clear()

            for gid, gdata in data.get("groups", {}).items():
                self.groups[gid] = AnimationGroup.from_dict(gdata)

            for tid, tdata in data.get("tracks", {}).items():
                self.tracks[tid] = KeyframeTrack.from_dict(tdata)

            logger.info(f"📂 Loaded from: {os.path.basename(filepath)}")
            return True
        except Exception as e:
            logger.error(f"Load failed: {e}")
            return False

    def get_stats(self) -> Dict:
        """Engine statistics"""
        total_keyframes = 0
        total_tracks    = 0

        for g in self.groups.values():
            total_tracks += len(g.tracks)
            for t in g.tracks.values():
                total_keyframes += len(t.keyframes)

        total_tracks += len(self.tracks)
        for t in self.tracks.values():
            total_keyframes += len(t.keyframes)

        return {
            "fps"               : self.fps,
            "total_groups"      : len(self.groups),
            "total_tracks"      : total_tracks,
            "total_keyframes"   : total_keyframes,
            "max_duration"      : self.get_max_duration(),
            "total_evaluations" : self._stats["total_evaluations"],
            "total_bakes"       : self._stats["total_bakes"],
        }


# ============================================================
# TEST FUNCTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")
    print_banner(
        "🔑 Keyframe System Test",
        "Property animation with easing, curves, presets"
    )

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))

    # ============================================================
    # Test 1: Initialize Engine
    # ============================================================
    print_section("Test 1: Initialize Keyframe Engine")

    engine = KeyframeEngine()
    stats  = engine.get_stats()

    print(f"  FPS              : {stats['fps']}")
    print(f"  Interpolations   : {len(InterpolationType)}")
    print(f"  Property types   : {len(PropertyType)}")

    # ============================================================
    # Test 2: Easing Functions Comparison
    # ============================================================
    print_section("Test 2: Easing Functions (visualization)")

    easings_to_test = [
        InterpolationType.LINEAR,
        InterpolationType.EASE_IN_CUBIC,
        InterpolationType.EASE_OUT_CUBIC,
        InterpolationType.EASE_IN_OUT_CUBIC,
        InterpolationType.BACK,
        InterpolationType.ELASTIC,
        InterpolationType.BOUNCE,
    ]

    # Print curves as ASCII
    print("  Time  →  Progress at t=0.0, 0.2, 0.4, 0.6, 0.8, 1.0\n")

    for interp in easings_to_test:
        values = [evaluate_easing(interp, t) for t in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]]
        values_str = "  ".join(f"{v:+.2f}" for v in values)
        print(f"  {interp.value:20s}: {values_str}")

    # ============================================================
    # Test 3: Simple Float Track
    # ============================================================
    print_section("Test 3: Simple Float Track (Opacity Animation)")

    opacity_track = KeyframeTrack("opacity", PropertyType.FLOAT, default_value=0.0)
    opacity_track.add_keyframe(0.0, 0.0, InterpolationType.EASE_OUT_CUBIC)
    opacity_track.add_keyframe(1.5, 1.0, InterpolationType.EASE_IN_CUBIC)
    opacity_track.add_keyframe(3.0, 0.5)
    opacity_track.add_keyframe(4.0, 1.0, InterpolationType.BOUNCE)

    print(f"  Track: '{opacity_track.property_name}'")
    print(f"  Keyframes: {len(opacity_track.keyframes)}\n")
    print("  Evaluated values:")

    test_times = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    for t in test_times:
        v = opacity_track.evaluate(t)
        bar = "█" * int(v * 30)
        print(f"    t={t:.1f}s → {v:.3f}  {bar}")

    # ============================================================
    # Test 4: Vector Track (3D Position)
    # ============================================================
    print_section("Test 4: Vector Track (3D Position)")

    pos_track = KeyframeTrack("position", PropertyType.VEC3,
                                default_value=[0.0, 0.0, 0.0])
    pos_track.add_keyframe(0.0, [0.0, 0.0, 0.0], InterpolationType.EASE_IN_OUT_CUBIC)
    pos_track.add_keyframe(2.0, [10.0, 5.0, -3.0], InterpolationType.EASE_OUT)
    pos_track.add_keyframe(4.0, [0.0, 10.0, 0.0])

    print("  Position over time:")
    for t in [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]:
        pos = pos_track.evaluate(t)
        print(f"    t={t:.1f}s → x={pos[0]:+6.2f}, y={pos[1]:+6.2f}, z={pos[2]:+6.2f}")

    # ============================================================
    # Test 5: Color Animation
    # ============================================================
    print_section("Test 5: Color Animation (RGB)")

    color_track = KeyframeTrack("color", PropertyType.COLOR,
                                 default_value=[1.0, 1.0, 1.0])
    color_track.add_keyframe(0.0, [1.0, 0.0, 0.0], InterpolationType.LINEAR)  # Red
    color_track.add_keyframe(1.5, [0.0, 1.0, 0.0], InterpolationType.LINEAR)  # Green
    color_track.add_keyframe(3.0, [0.0, 0.0, 1.0])                              # Blue

    print("  Color transition (RGB):")
    for t in [0.0, 0.75, 1.5, 2.25, 3.0]:
        c = color_track.evaluate(t)
        hex_color = f"#{int(c[0]*255):02X}{int(c[1]*255):02X}{int(c[2]*255):02X}"
        print(f"    t={t:.2f}s → R={c[0]:.2f} G={c[1]:.2f} B={c[2]:.2f}  {hex_color}")

    # ============================================================
    # Test 6: Bezier Curves
    # ============================================================
    print_section("Test 6: Custom Bezier Curves")

    bezier_track = KeyframeTrack("bezier_test", PropertyType.FLOAT, 0.0)

    # Custom bezier curve
    anticipate = BezierCurve.anticipate()
    bezier_track.add_keyframe(0.0, 0.0,
                              InterpolationType.BEZIER,
                              bezier_curve=anticipate)
    bezier_track.add_keyframe(1.0, 100.0)

    print("  Anticipate bezier (backward before forward):")
    for t in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 0.9, 1.0]:
        v = bezier_track.evaluate(t)
        print(f"    t={t:.1f}s → {v:+7.2f}")

    # Preset bezier tests
    print("\n  Bezier presets @ t=0.5:")
    presets = {
        "linear"      : BezierCurve.linear(),
        "ease"        : BezierCurve.ease(),
        "ease_in"     : BezierCurve.ease_in(),
        "ease_out"    : BezierCurve.ease_out(),
        "ease_in_out" : BezierCurve.ease_in_out(),
    }
    for name, curve in presets.items():
        val = curve.evaluate(0.5)
        print(f"    {name:15s}: {val:.4f}")

    # ============================================================
    # Test 7: Animation Group (Character Rig)
    # ============================================================
    print_section("Test 7: Animation Group (Character Animation)")

    hero = engine.create_group("Hero Character")

    # Position track
    pos_x = hero.add_track("position_x", PropertyType.FLOAT)
    pos_x.add_keyframe(0.0, -5.0, InterpolationType.EASE_OUT_CUBIC)
    pos_x.add_keyframe(2.0, 5.0)

    # Rotation track
    rot_y = hero.add_track("rotation_y", PropertyType.FLOAT)
    rot_y.add_keyframe(0.0, 0.0, InterpolationType.LINEAR)
    rot_y.add_keyframe(2.0, 360.0)

    # Scale track
    scale = hero.add_track("scale", PropertyType.FLOAT, default_value=1.0)
    scale.add_keyframe(0.0, 0.5, InterpolationType.ELASTIC)
    scale.add_keyframe(1.0, 1.0)
    scale.add_keyframe(2.0, 1.0)

    # Evaluate at different times
    print("  Character state over time:\n")
    for t in [0.0, 0.5, 1.0, 1.5, 2.0]:
        values = hero.evaluate_all(t)
        print(f"    t={t:.1f}s:")
        for prop, val in values.items():
            if isinstance(val, float):
                print(f"      {prop:15s} = {val:+7.2f}")
            else:
                print(f"      {prop:15s} = {val}")

    # ============================================================
    # Test 8: Preset Animations
    # ============================================================
    print_section("Test 8: Preset Animations Library")

    presets_to_test = [
        ("Fade In",      KeyframePresets.fade_in(duration=1.0)),
        ("Fade Out",     KeyframePresets.fade_out(duration=1.0)),
        ("Slide In",     KeyframePresets.slide_in_from_left(distance=100, duration=0.6)),
        ("Bounce In",    KeyframePresets.bounce_in(duration=1.0)),
        ("Elastic",      KeyframePresets.elastic_appear(duration=0.8)),
        ("360 Rotation", KeyframePresets.rotate_360(duration=2.0)),
    ]

    for name, track in presets_to_test:
        duration = track.get_duration()
        start_val = track.evaluate(0.0)
        end_val   = track.evaluate(duration)
        keyframes = len(track.keyframes)

        # Format values
        start_str = f"{start_val:.2f}" if isinstance(start_val, (int, float)) else str(start_val)
        end_str   = f"{end_val:.2f}" if isinstance(end_val, (int, float)) else str(end_val)

        print(f"  📦 {name:15s}: {keyframes} kfs | {duration:.1f}s | "
              f"{start_str} → {end_str}")

    # ============================================================
    # Test 9: Pulse Effect (Complex Animation)
    # ============================================================
    print_section("Test 9: Complex Pulse Animation")

    pulse = KeyframePresets.pulse(base_value=1.0, peak_value=1.5,
                                    cycles=3, duration=2.0)
    print(f"  Pulse animation: {len(pulse.keyframes)} keyframes")
    print(f"  Duration: {pulse.get_duration()}s\n")

    print("  Scale over time (should oscillate):")
    for t in [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]:
        v = pulse.evaluate(t)
        bar = "█" * int((v - 1.0) * 60 + 1)
        print(f"    t={t:.2f}s → scale={v:.3f}  {bar}")

    # ============================================================
    # Test 10: Animation Baking
    # ============================================================
    print_section("Test 10: Animation Baking (Frame-by-Frame)")

    # Create simple animation
    bake_track = KeyframeTrack("test_bake", PropertyType.FLOAT)
    bake_track.add_keyframe(0.0, 0.0, InterpolationType.EASE_IN_OUT_CUBIC)
    bake_track.add_keyframe(1.0, 100.0)

    baked = bake_track.bake(fps=30)
    print(f"  Baked {len(baked)} frames @ 30fps")
    print(f"  First 5 frames:")
    for time_val, value in baked[:5]:
        print(f"    frame={engine.fps * time_val:5.1f}  t={time_val:.3f}s  value={value:.3f}")
    print(f"  ...")
    print(f"  Last 3 frames:")
    for time_val, value in baked[-3:]:
        print(f"    frame={engine.fps * time_val:5.1f}  t={time_val:.3f}s  value={value:.3f}")

    # ============================================================
    # Test 11: Engine-level Evaluate All
    # ============================================================
    print_section("Test 11: Full Engine Evaluation")

    # Add some more groups
    camera_group = engine.create_group("Camera")
    cam_pos = camera_group.add_track("position", PropertyType.VEC3)
    cam_pos.add_keyframe(0.0, [0.0, 0.0, 10.0], InterpolationType.EASE_IN_OUT_CUBIC)
    cam_pos.add_keyframe(3.0, [5.0, 5.0, 8.0])

    print("  All engine values at different times:\n")
    for t in [0.0, 1.0, 2.0, 3.0]:
        print(f"  ⏱️  t={t}s:")
        all_values = engine.evaluate_all(t)
        for group_name, props in all_values.items():
            print(f"     {group_name}:")
            for prop, val in props.items():
                if isinstance(val, list):
                    val_str = f"[{', '.join(f'{v:+.2f}' for v in val)}]"
                elif isinstance(val, float):
                    val_str = f"{val:+.3f}"
                else:
                    val_str = str(val)
                print(f"       {prop:15s} = {val_str}")

    # ============================================================
    # Test 12: Save & Load
    # ============================================================
    print_section("Test 12: Save & Load Animation Data")

    output_dir = os.path.join(base_dir, "temp", "keyframe_tests")
    ensure_dir(output_dir)
    save_path = os.path.join(output_dir, "test_keyframes.json")

    success = engine.save_to_file(save_path)
    if success:
        from src.utils import get_file_size, format_bytes
        size = format_bytes(get_file_size(save_path))
        print(f"  ✅ Saved: {os.path.basename(save_path)} ({size})")

        # Reload
        new_engine = KeyframeEngine()
        loaded = new_engine.load_from_file(save_path)

        if loaded:
            new_stats = new_engine.get_stats()
            print(f"\n  ✅ Reloaded successfully:")
            print(f"     Groups        : {new_stats['total_groups']}")
            print(f"     Tracks        : {new_stats['total_tracks']}")
            print(f"     Keyframes     : {new_stats['total_keyframes']}")
            print(f"     Max duration  : {new_stats['max_duration']:.2f}s")

            # Verify values match
            orig_val = engine.evaluate_all(1.0)
            new_val  = new_engine.evaluate_all(1.0)
            match    = orig_val == new_val
            print(f"     Values match  : {'✅' if match else '⚠️'}")

    # ============================================================
    # Test 13: Final Statistics
    # ============================================================
    print_section("Test 13: Final Statistics")

    stats = engine.get_stats()
    print(f"  FPS               : {stats['fps']}")
    print(f"  Groups            : {stats['total_groups']}")
    print(f"  Tracks            : {stats['total_tracks']}")
    print(f"  Keyframes         : {stats['total_keyframes']}")
    print(f"  Max duration      : {stats['max_duration']:.2f}s")
    print(f"  Total evaluations : {stats['total_evaluations']}")
    print(f"  Total bakes       : {stats['total_bakes']}")

    print_section("Output Files")
    print(f"  📁 Data saved in:")
    print(f"     {output_dir}")

    print_banner(
        "✅ Keyframe System Ready!",
        f"{len(InterpolationType)} interpolation types | "
        f"{stats['total_keyframes']} keyframes created"
    )