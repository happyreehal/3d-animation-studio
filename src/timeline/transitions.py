# ============================================================
# 3D ANIMATION STUDIO - Transitions Engine
# ============================================================
# Features:
# - Video transitions: fade, dissolve, wipe, slide, zoom, blur, flash
# - Audio transitions: crossfade, fade in/out with curves
# - Text transitions: typewriter, slide, zoom, fade
# - Custom easing (uses keyframe_system)
# - Overlap control between clips
# - Preview generation (frame-by-frame progress)
# - Ready-made preset library
# - Effect strength control (0-1 intensity)
# - Direction control (in/out/both)
# - Timeline & Keyframe integration
# - JSON serialization
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
from typing import Dict, List, Optional, Tuple, Callable, Any

import numpy as np

from src.utils import (
    get_logger, get_config, ensure_dir, generate_short_id,
    get_timestamp, format_duration, read_json, write_json,
    clamp, lerp,
)

# Keyframe system se easings import karo — consistent behavior ke liye
from src.timeline.keyframe_system import (
    InterpolationType, evaluate_easing, BezierCurve,
)

logger = get_logger("Transitions")


# ============================================================
# CONSTANTS & ENUMS
# ============================================================

class TransitionCategory(Enum):
    """Transition ki broad category — kis type ka content pe apply hoga"""
    VIDEO    = "video"       # Video/image clips ke beech
    AUDIO    = "audio"       # Audio clips ke beech
    TEXT     = "text"        # Text/subtitle clips
    UNIVERSAL= "universal"   # Har type pe kaam karega


class TransitionType(Enum):
    """
    Different visual transition effects.
    Har type ka apna progress calculation logic hai.
    """
    # Basic
    NONE           = "none"              # No transition (hard cut)
    FADE           = "fade"              # Fade to black/color
    CROSS_DISSOLVE = "cross_dissolve"    # Blend between A and B

    # Directional wipes
    WIPE_LEFT      = "wipe_left"         # A → B, wipe from right to left
    WIPE_RIGHT     = "wipe_right"        # A → B, wipe from left to right
    WIPE_UP        = "wipe_up"
    WIPE_DOWN      = "wipe_down"
    WIPE_DIAGONAL  = "wipe_diagonal"     # Corner-to-corner

    # Slides
    SLIDE_LEFT     = "slide_left"        # B slides in from right
    SLIDE_RIGHT    = "slide_right"
    SLIDE_UP       = "slide_up"
    SLIDE_DOWN     = "slide_down"

    # Zooms
    ZOOM_IN        = "zoom_in"           # B zooms in from center
    ZOOM_OUT       = "zoom_out"          # A zooms out revealing B

    # Special effects
    BLUR           = "blur"              # Motion blur
    FLASH          = "flash"             # Bright flash
    PIXELATE       = "pixelate"          # 8-bit style
    IRIS_OPEN      = "iris_open"         # Circle opens from center
    IRIS_CLOSE     = "iris_close"        # Circle closes
    ROTATE         = "rotate"            # Rotation transition
    COLOR_SPLASH   = "color_splash"      # Color-based reveal

    # Audio
    AUDIO_CROSSFADE = "audio_crossfade"
    AUDIO_FADE_IN   = "audio_fade_in"
    AUDIO_FADE_OUT  = "audio_fade_out"

    # Text
    TEXT_TYPEWRITER = "text_typewriter"  # Character by character
    TEXT_SLIDE_UP   = "text_slide_up"
    TEXT_ZOOM_IN    = "text_zoom_in"
    TEXT_FADE_IN    = "text_fade_in"


class TransitionDirection(Enum):
    """Transition kis direction mein play hoga"""
    IN         = "in"           # Clip aa raha hai (entrance)
    OUT        = "out"          # Clip ja raha hai (exit)
    BOTH       = "both"         # Beech mein (crossfade jaisa)


# ============================================================
# TRANSITION FRAME — Single time point ka state
# ============================================================

@dataclass
class TransitionFrame:
    """
    Ek transition ke ek moment ka state.
    Renderer ye use karke actual pixels compose karta hai.
    """
    time            : float                       = 0.0     # Absolute time
    progress        : float                       = 0.0     # 0-1 (eased)
    raw_progress    : float                       = 0.0     # 0-1 (linear, no easing)

    # Compositing values
    clip_a_opacity  : float                       = 1.0     # Outgoing clip
    clip_b_opacity  : float                       = 0.0     # Incoming clip

    # Transformations for clip A (outgoing)
    clip_a_offset_x : float                       = 0.0     # -1 to 1 (screen units)
    clip_a_offset_y : float                       = 0.0
    clip_a_scale    : float                       = 1.0
    clip_a_rotation : float                       = 0.0

    # Transformations for clip B (incoming)
    clip_b_offset_x : float                       = 0.0
    clip_b_offset_y : float                       = 0.0
    clip_b_scale    : float                       = 1.0
    clip_b_rotation : float                       = 0.0

    # Effect-specific values
    blur_amount     : float                       = 0.0     # 0-1 blur intensity
    flash_intensity : float                       = 0.0     # 0-1 white flash
    wipe_position   : float                       = 0.0     # 0-1 wipe line position
    iris_radius     : float                       = 0.0     # 0-1 iris size

    # Color overlay
    overlay_color   : Tuple[float, float, float] = (0.0, 0.0, 0.0)
    overlay_alpha   : float                       = 0.0

    # Text-specific
    visible_chars   : int                         = 0       # Typewriter effect

    # Effect metadata (renderer ke liye instructions)
    effect_type     : str                         = "cross_dissolve"

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["overlay_color"] = list(self.overlay_color)
        return d


# ============================================================
# TRANSITION CONFIG
# ============================================================

@dataclass
class TransitionConfig:
    """
    Ek transition ki poori configuration.
    Ye 'template' hai — actual apply karne pe TransitionFrames generate hote hain.
    """
    id              : str                       = field(default_factory=generate_short_id)
    name            : str                       = "Transition"
    transition_type : TransitionType            = TransitionType.CROSS_DISSOLVE
    category        : TransitionCategory        = TransitionCategory.VIDEO

    # Timing
    duration        : float                     = 1.0       # Total seconds
    overlap         : float                     = 0.5       # 0-1, kitna clips overlap karein

    # Direction
    direction       : TransitionDirection       = TransitionDirection.BOTH

    # Easing
    easing          : InterpolationType         = InterpolationType.EASE_IN_OUT_CUBIC
    custom_bezier   : Optional[BezierCurve]     = None      # Custom curve override

    # Effect parameters
    intensity       : float                     = 1.0       # 0-1 effect strength

    # Fade specific
    fade_color      : Tuple[float, float, float] = (0.0, 0.0, 0.0)   # Fade to color

    # Text specific
    total_chars     : int                       = 0         # Typewriter ke liye

    # Metadata
    description     : str                       = ""
    tags            : List[str]                 = field(default_factory=list)

    def to_dict(self) -> Dict:
        d = {
            "id"             : self.id,
            "name"           : self.name,
            "transition_type": self.transition_type.value,
            "category"       : self.category.value,
            "duration"       : self.duration,
            "overlap"        : self.overlap,
            "direction"      : self.direction.value,
            "easing"         : self.easing.value,
            "intensity"      : self.intensity,
            "fade_color"     : list(self.fade_color),
            "total_chars"    : self.total_chars,
            "description"    : self.description,
            "tags"           : self.tags,
        }
        if self.custom_bezier:
            d["custom_bezier"] = self.custom_bezier.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> "TransitionConfig":
        config = cls(
            id             = data.get("id", generate_short_id()),
            name           = data.get("name", "Transition"),
            transition_type= TransitionType(data.get("transition_type", "cross_dissolve")),
            category       = TransitionCategory(data.get("category", "video")),
            duration       = data.get("duration", 1.0),
            overlap        = data.get("overlap", 0.5),
            direction      = TransitionDirection(data.get("direction", "both")),
            easing         = InterpolationType(data.get("easing", "ease_in_out_cubic")),
            intensity      = data.get("intensity", 1.0),
            fade_color     = tuple(data.get("fade_color", [0.0, 0.0, 0.0])),
            total_chars    = data.get("total_chars", 0),
            description    = data.get("description", ""),
            tags           = data.get("tags", []),
        )
        if "custom_bezier" in data:
            config.custom_bezier = BezierCurve.from_dict(data["custom_bezier"])
        return config


# ============================================================
# TRANSITION CALCULATORS — Frame Generation Logic
# ============================================================

class TransitionCalculator:
    """
    🎨 Ek specific transition type ka logic.
    Progress (0-1) leta hai aur TransitionFrame return karta hai.
    Har transition type ka apna calculator hai.
    """

    @staticmethod
    def calculate(config: TransitionConfig,
                  progress: float,
                  time: float) -> TransitionFrame:
        """
        Given transition config aur progress ke liye frame calculate karo.

        Args:
            config   : TransitionConfig
            progress : Eased progress 0-1
            time     : Absolute time
        """
        # Base frame
        frame = TransitionFrame(
            time         = time,
            progress     = progress,
            raw_progress = progress,
            effect_type  = config.transition_type.value,
        )

        ttype = config.transition_type
        p     = clamp(progress, 0.0, 1.0)
        i     = clamp(config.intensity, 0.0, 1.0)

        # ── FADE / DISSOLVE ────────────────────────────────

        if ttype == TransitionType.NONE:
            # Hard cut
            frame.clip_a_opacity = 1.0 if p < 0.5 else 0.0
            frame.clip_b_opacity = 1.0 if p >= 0.5 else 0.0

        elif ttype == TransitionType.FADE:
            # Fade to color (like a fade to black)
            # First half: A fades to color, second half: color fades to B
            if p < 0.5:
                # Phase 1: A → color
                phase_p = p * 2.0
                frame.clip_a_opacity = 1.0 - phase_p
                frame.clip_b_opacity = 0.0
                frame.overlay_color  = config.fade_color
                frame.overlay_alpha  = phase_p * i
            else:
                # Phase 2: color → B
                phase_p = (p - 0.5) * 2.0
                frame.clip_a_opacity = 0.0
                frame.clip_b_opacity = phase_p
                frame.overlay_color  = config.fade_color
                frame.overlay_alpha  = (1.0 - phase_p) * i

        elif ttype == TransitionType.CROSS_DISSOLVE:
            # Smooth blend — A fades out while B fades in
            frame.clip_a_opacity = (1.0 - p) * i + (1.0 - i)
            frame.clip_b_opacity = p * i

        # ── WIPES ──────────────────────────────────────────

        elif ttype == TransitionType.WIPE_LEFT:
            # B revealed from right side moving left
            frame.clip_a_opacity = 1.0
            frame.clip_b_opacity = 1.0
            frame.wipe_position  = 1.0 - p   # 1.0 (right) → 0.0 (left)

        elif ttype == TransitionType.WIPE_RIGHT:
            frame.clip_a_opacity = 1.0
            frame.clip_b_opacity = 1.0
            frame.wipe_position  = p         # 0.0 (left) → 1.0 (right)

        elif ttype == TransitionType.WIPE_UP:
            frame.clip_a_opacity = 1.0
            frame.clip_b_opacity = 1.0
            frame.wipe_position  = 1.0 - p

        elif ttype == TransitionType.WIPE_DOWN:
            frame.clip_a_opacity = 1.0
            frame.clip_b_opacity = 1.0
            frame.wipe_position  = p

        elif ttype == TransitionType.WIPE_DIAGONAL:
            frame.clip_a_opacity = 1.0
            frame.clip_b_opacity = 1.0
            frame.wipe_position  = p

        # ── SLIDES ─────────────────────────────────────────

        elif ttype == TransitionType.SLIDE_LEFT:
            # B aata hai right se, A jaata hai left
            frame.clip_a_opacity  = 1.0
            frame.clip_b_opacity  = 1.0
            frame.clip_a_offset_x = -p            # A moves left
            frame.clip_b_offset_x = (1.0 - p)     # B starts right, moves to center

        elif ttype == TransitionType.SLIDE_RIGHT:
            frame.clip_a_opacity  = 1.0
            frame.clip_b_opacity  = 1.0
            frame.clip_a_offset_x = p
            frame.clip_b_offset_x = -(1.0 - p)

        elif ttype == TransitionType.SLIDE_UP:
            frame.clip_a_opacity  = 1.0
            frame.clip_b_opacity  = 1.0
            frame.clip_a_offset_y = -p
            frame.clip_b_offset_y = (1.0 - p)

        elif ttype == TransitionType.SLIDE_DOWN:
            frame.clip_a_opacity  = 1.0
            frame.clip_b_opacity  = 1.0
            frame.clip_a_offset_y = p
            frame.clip_b_offset_y = -(1.0 - p)

        # ── ZOOMS ──────────────────────────────────────────

        elif ttype == TransitionType.ZOOM_IN:
            # B zooms in from small to full
            frame.clip_a_opacity = 1.0 - p
            frame.clip_b_opacity = p
            frame.clip_b_scale   = 0.1 + (0.9 * p)   # 0.1 → 1.0

        elif ttype == TransitionType.ZOOM_OUT:
            # A zooms out, revealing B behind
            frame.clip_a_opacity = 1.0 - p
            frame.clip_b_opacity = p
            frame.clip_a_scale   = 1.0 + (2.0 * p * i)   # 1.0 → 3.0

        # ── SPECIAL EFFECTS ────────────────────────────────

        elif ttype == TransitionType.BLUR:
            # Motion blur transition
            # A blurs out, B blurs in
            frame.clip_a_opacity = 1.0 - p
            frame.clip_b_opacity = p
            # Blur peaks at middle
            frame.blur_amount    = math.sin(p * math.pi) * i

        elif ttype == TransitionType.FLASH:
            # Bright flash at middle
            # A fades to white, B fades from white
            flash_curve = math.sin(p * math.pi)   # 0 → 1 → 0
            frame.clip_a_opacity = (1.0 - p) * (1.0 - flash_curve * 0.7)
            frame.clip_b_opacity = p * (1.0 - flash_curve * 0.7)
            frame.flash_intensity = flash_curve * i
            frame.overlay_color   = (1.0, 1.0, 1.0)
            frame.overlay_alpha   = flash_curve * i

        elif ttype == TransitionType.PIXELATE:
            # Pixelation peaks at middle
            pixel_curve          = math.sin(p * math.pi)
            frame.clip_a_opacity = 1.0 - p
            frame.clip_b_opacity = p
            frame.blur_amount    = pixel_curve * i  # Reuse blur for pixelation intensity

        elif ttype == TransitionType.IRIS_OPEN:
            # Circle opens from center revealing B
            frame.clip_a_opacity = 1.0
            frame.clip_b_opacity = 1.0
            frame.iris_radius    = p

        elif ttype == TransitionType.IRIS_CLOSE:
            # Circle closes hiding A revealing B
            frame.clip_a_opacity = 1.0
            frame.clip_b_opacity = 1.0
            frame.iris_radius    = 1.0 - p

        elif ttype == TransitionType.ROTATE:
            # A rotates out, B rotates in
            frame.clip_a_opacity  = 1.0 - p
            frame.clip_b_opacity  = p
            frame.clip_a_rotation = p * 360.0 * i     # 0° → 360°
            frame.clip_b_rotation = (1.0 - p) * -360.0 * i
            frame.clip_a_scale    = 1.0 - (p * 0.3)   # Slight shrink
            frame.clip_b_scale    = 0.7 + (p * 0.3)

        elif ttype == TransitionType.COLOR_SPLASH:
            # Color wave sweeps across
            frame.clip_a_opacity = 1.0 - p
            frame.clip_b_opacity = p
            # Overlay color pulse at middle
            color_curve          = math.sin(p * math.pi) * i
            frame.overlay_color  = config.fade_color
            frame.overlay_alpha  = color_curve * 0.6

        # ── AUDIO TRANSITIONS ──────────────────────────────

        elif ttype == TransitionType.AUDIO_CROSSFADE:
            # A volume decreases, B volume increases (equal-power curve)
            frame.clip_a_opacity = math.cos(p * math.pi / 2)   # Cosine curve
            frame.clip_b_opacity = math.sin(p * math.pi / 2)

        elif ttype == TransitionType.AUDIO_FADE_IN:
            # Silence → B
            frame.clip_a_opacity = 0.0
            frame.clip_b_opacity = p * i

        elif ttype == TransitionType.AUDIO_FADE_OUT:
            # A → silence
            frame.clip_a_opacity = (1.0 - p) * i
            frame.clip_b_opacity = 0.0

        # ── TEXT TRANSITIONS ───────────────────────────────

        elif ttype == TransitionType.TEXT_TYPEWRITER:
            # Characters reveal one by one
            frame.clip_a_opacity = 0.0
            frame.clip_b_opacity = 1.0
            frame.visible_chars  = int(p * config.total_chars)

        elif ttype == TransitionType.TEXT_SLIDE_UP:
            frame.clip_a_opacity  = 0.0
            frame.clip_b_opacity  = p
            frame.clip_b_offset_y = -(1.0 - p) * 0.3

        elif ttype == TransitionType.TEXT_ZOOM_IN:
            frame.clip_a_opacity = 0.0
            frame.clip_b_opacity = p
            frame.clip_b_scale   = 0.5 + (0.5 * p)

        elif ttype == TransitionType.TEXT_FADE_IN:
            frame.clip_a_opacity = 0.0
            frame.clip_b_opacity = p * i

        else:
            # Fallback — cross dissolve
            frame.clip_a_opacity = 1.0 - p
            frame.clip_b_opacity = p

        return frame


# ============================================================
# TRANSITION INSTANCE — Applied Transition on Timeline
# ============================================================

@dataclass
class TransitionInstance:
    """
    Ek specific place pe applied transition.
    Timeline ke do clips ke beech (clip_a → clip_b).
    """
    id           : str                         = field(default_factory=generate_short_id)
    config       : TransitionConfig            = field(default_factory=TransitionConfig)

    # Placement
    start_time   : float                       = 0.0        # Absolute timeline time
    clip_a_id    : Optional[str]               = None       # Outgoing clip
    clip_b_id    : Optional[str]               = None       # Incoming clip
    track_id     : Optional[str]               = None       # Kis track pe hai

    # State
    enabled      : bool                        = True
    locked       : bool                        = False

    @property
    def end_time(self) -> float:
        return self.start_time + self.config.duration

    @property
    def midpoint(self) -> float:
        return self.start_time + (self.config.duration / 2.0)

    def contains_time(self, time: float) -> bool:
        """Check karo agar time transition ke andar hai"""
        return self.start_time <= time <= self.end_time

    def get_raw_progress(self, time: float) -> float:
        """Given time pe linear progress (0-1)"""
        if not self.contains_time(time) or self.config.duration <= 0:
            return 0.0
        return (time - self.start_time) / self.config.duration

    def evaluate(self, time: float) -> Optional[TransitionFrame]:
        """
        Given time pe transition ka frame calculate karo.

        Returns:
            TransitionFrame ya None (agar transition ke bahar)
        """
        if not self.enabled:
            return None

        if not self.contains_time(time):
            return None

        # Raw progress
        raw_p = self.get_raw_progress(time)

        # Apply easing
        if self.config.custom_bezier:
            eased_p = self.config.custom_bezier.evaluate(raw_p)
        else:
            eased_p = evaluate_easing(self.config.easing, raw_p)

        # Frame calculate karo
        frame              = TransitionCalculator.calculate(
            self.config, eased_p, time
        )
        frame.raw_progress = raw_p
        return frame

    def to_dict(self) -> Dict:
        return {
            "id"        : self.id,
            "config"    : self.config.to_dict(),
            "start_time": self.start_time,
            "clip_a_id" : self.clip_a_id,
            "clip_b_id" : self.clip_b_id,
            "track_id"  : self.track_id,
            "enabled"   : self.enabled,
            "locked"    : self.locked,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "TransitionInstance":
        return cls(
            id        = data.get("id", generate_short_id()),
            config    = TransitionConfig.from_dict(data.get("config", {})),
            start_time= data.get("start_time", 0.0),
            clip_a_id = data.get("clip_a_id"),
            clip_b_id = data.get("clip_b_id"),
            track_id  = data.get("track_id"),
            enabled   = data.get("enabled", True),
            locked    = data.get("locked", False),
        )


# ============================================================
# TRANSITION PRESETS — Ready-made Templates
# ============================================================

class TransitionPresets:
    """
    🎨 Ready-made transition presets — different styles ke liye.
    YouTube-friendly, cinematic, energetic options.
    """

    # ── FADE / DISSOLVE ──────────────────────────────────

    @staticmethod
    def fade_to_black(duration: float = 0.8) -> TransitionConfig:
        """Classic cinema fade to black"""
        return TransitionConfig(
            name           = "Fade to Black",
            transition_type= TransitionType.FADE,
            category       = TransitionCategory.VIDEO,
            duration       = duration,
            easing         = InterpolationType.EASE_IN_OUT_CUBIC,
            fade_color     = (0.0, 0.0, 0.0),
            description    = "Fade through black — dramatic",
            tags           = ["cinematic", "dramatic"],
        )

    @staticmethod
    def fade_to_white(duration: float = 0.6) -> TransitionConfig:
        """Bright fade to white"""
        return TransitionConfig(
            name           = "Fade to White",
            transition_type= TransitionType.FADE,
            duration       = duration,
            fade_color     = (1.0, 1.0, 1.0),
            description    = "Bright fade — heavenly/dream",
            tags           = ["bright", "dreamy"],
        )

    @staticmethod
    def smooth_dissolve(duration: float = 0.5) -> TransitionConfig:
        """Standard smooth dissolve"""
        return TransitionConfig(
            name           = "Smooth Dissolve",
            transition_type= TransitionType.CROSS_DISSOLVE,
            duration       = duration,
            easing         = InterpolationType.EASE_IN_OUT_CUBIC,
            description    = "Classic cross-dissolve",
            tags           = ["smooth", "classic"],
        )

    @staticmethod
    def quick_dissolve(duration: float = 0.25) -> TransitionConfig:
        """Fast punchy dissolve"""
        return TransitionConfig(
            name           = "Quick Dissolve",
            transition_type= TransitionType.CROSS_DISSOLVE,
            duration       = duration,
            easing         = InterpolationType.LINEAR,
            description    = "Fast dissolve — energetic pace",
            tags           = ["fast", "energetic"],
        )

    # ── ACTION / EXCITING ────────────────────────────────

    @staticmethod
    def flash_cut(duration: float = 0.3) -> TransitionConfig:
        """Bright flash — action/impact"""
        return TransitionConfig(
            name           = "Flash Cut",
            transition_type= TransitionType.FLASH,
            duration       = duration,
            intensity      = 1.0,
            easing         = InterpolationType.EASE_OUT_QUAD,
            description    = "Bright flash — perfect for reveals",
            tags           = ["action", "impact"],
        )

    @staticmethod
    def zoom_punch(duration: float = 0.4) -> TransitionConfig:
        """Zoom in with punch"""
        return TransitionConfig(
            name           = "Zoom Punch",
            transition_type= TransitionType.ZOOM_IN,
            duration       = duration,
            intensity      = 1.0,
            easing         = InterpolationType.EASE_OUT_CUBIC,
            description    = "Zoom in with impact",
            tags           = ["action", "youtube"],
        )

    @staticmethod
    def zoom_out_reveal(duration: float = 0.7) -> TransitionConfig:
        """Zoom out revealing new scene"""
        return TransitionConfig(
            name           = "Zoom Out Reveal",
            transition_type= TransitionType.ZOOM_OUT,
            duration       = duration,
            intensity      = 0.8,
            easing         = InterpolationType.EASE_IN_OUT_CUBIC,
            description    = "Zoom out to reveal new content",
            tags           = ["cinematic", "reveal"],
        )

    # ── DIRECTIONAL ──────────────────────────────────────

    @staticmethod
    def slide_left(duration: float = 0.5) -> TransitionConfig:
        """Slide from right to left"""
        return TransitionConfig(
            name           = "Slide Left",
            transition_type= TransitionType.SLIDE_LEFT,
            duration       = duration,
            easing         = InterpolationType.EASE_IN_OUT_QUAD,
            description    = "Clip slides in from right",
            tags           = ["directional", "modern"],
        )

    @staticmethod
    def slide_right(duration: float = 0.5) -> TransitionConfig:
        """Slide from left to right"""
        return TransitionConfig(
            name           = "Slide Right",
            transition_type= TransitionType.SLIDE_RIGHT,
            duration       = duration,
            easing         = InterpolationType.EASE_IN_OUT_QUAD,
            tags           = ["directional", "modern"],
        )

    @staticmethod
    def slide_up(duration: float = 0.5) -> TransitionConfig:
        """Slide up from bottom"""
        return TransitionConfig(
            name           = "Slide Up",
            transition_type= TransitionType.SLIDE_UP,
            duration       = duration,
            easing         = InterpolationType.EASE_IN_OUT_QUAD,
            tags           = ["directional"],
        )

    @staticmethod
    def wipe_left(duration: float = 0.6) -> TransitionConfig:
        """Wipe transition — right to left"""
        return TransitionConfig(
            name           = "Wipe Left",
            transition_type= TransitionType.WIPE_LEFT,
            duration       = duration,
            easing         = InterpolationType.LINEAR,
            description    = "Old-school wipe transition",
            tags           = ["classic", "retro"],
        )

    # ── STYLISH / SPECIAL ────────────────────────────────

    @staticmethod
    def cinematic_blur(duration: float = 0.6) -> TransitionConfig:
        """Motion blur transition"""
        return TransitionConfig(
            name           = "Cinematic Blur",
            transition_type= TransitionType.BLUR,
            duration       = duration,
            intensity      = 0.9,
            easing         = InterpolationType.EASE_IN_OUT_CUBIC,
            description    = "Smooth motion blur",
            tags           = ["cinematic", "smooth"],
        )

    @staticmethod
    def retro_pixelate(duration: float = 0.5) -> TransitionConfig:
        """8-bit style pixelation"""
        return TransitionConfig(
            name           = "Retro Pixelate",
            transition_type= TransitionType.PIXELATE,
            duration       = duration,
            intensity      = 1.0,
            description    = "8-bit style pixelation",
            tags           = ["retro", "game"],
        )

    @staticmethod
    def iris_open(duration: float = 0.7) -> TransitionConfig:
        """Iris opens — old cinema style"""
        return TransitionConfig(
            name           = "Iris Open",
            transition_type= TransitionType.IRIS_OPEN,
            duration       = duration,
            easing         = InterpolationType.EASE_OUT_CUBIC,
            description    = "Classic iris opening",
            tags           = ["cinematic", "vintage"],
        )

    @staticmethod
    def rotation_spin(duration: float = 0.8) -> TransitionConfig:
        """Rotating transition"""
        return TransitionConfig(
            name           = "Rotation Spin",
            transition_type= TransitionType.ROTATE,
            duration       = duration,
            intensity      = 0.8,
            easing         = InterpolationType.EASE_IN_OUT_CUBIC,
            description    = "Spinning rotation between clips",
            tags           = ["energetic", "playful"],
        )

    @staticmethod
    def color_wash(duration: float = 0.6,
                    color: Tuple[float, float, float] = (1.0, 0.3, 0.3)) -> TransitionConfig:
        """Color splash transition"""
        return TransitionConfig(
            name           = "Color Wash",
            transition_type= TransitionType.COLOR_SPLASH,
            duration       = duration,
            fade_color     = color,
            intensity      = 0.7,
            description    = "Colored wave transition",
            tags           = ["colorful", "modern"],
        )

    # ── AUDIO PRESETS ────────────────────────────────────

    @staticmethod
    def audio_crossfade(duration: float = 0.5) -> TransitionConfig:
        """Smooth audio crossfade"""
        return TransitionConfig(
            name           = "Audio Crossfade",
            transition_type= TransitionType.AUDIO_CROSSFADE,
            category       = TransitionCategory.AUDIO,
            duration       = duration,
            easing         = InterpolationType.LINEAR,   # Equal-power built-in
            description    = "Smooth audio transition",
            tags           = ["audio", "smooth"],
        )

    @staticmethod
    def audio_fade_in(duration: float = 1.0) -> TransitionConfig:
        """Audio fade in from silence"""
        return TransitionConfig(
            name           = "Audio Fade In",
            transition_type= TransitionType.AUDIO_FADE_IN,
            category       = TransitionCategory.AUDIO,
            duration       = duration,
            easing         = InterpolationType.EASE_OUT_CUBIC,
            tags           = ["audio"],
        )

    @staticmethod
    def audio_fade_out(duration: float = 1.5) -> TransitionConfig:
        """Audio fade out to silence"""
        return TransitionConfig(
            name           = "Audio Fade Out",
            transition_type= TransitionType.AUDIO_FADE_OUT,
            category       = TransitionCategory.AUDIO,
            duration       = duration,
            easing         = InterpolationType.EASE_IN_CUBIC,
            tags           = ["audio"],
        )

    # ── TEXT PRESETS ─────────────────────────────────────

    @staticmethod
    def text_typewriter(duration: float = 1.5,
                         total_chars: int = 20) -> TransitionConfig:
        """Character-by-character typewriter"""
        return TransitionConfig(
            name           = "Typewriter",
            transition_type= TransitionType.TEXT_TYPEWRITER,
            category       = TransitionCategory.TEXT,
            duration       = duration,
            total_chars    = total_chars,
            easing         = InterpolationType.LINEAR,
            description    = "Type each character one by one",
            tags           = ["text", "retro"],
        )

    @staticmethod
    def text_slide_up(duration: float = 0.5) -> TransitionConfig:
        """Text slides up from bottom"""
        return TransitionConfig(
            name           = "Text Slide Up",
            transition_type= TransitionType.TEXT_SLIDE_UP,
            category       = TransitionCategory.TEXT,
            duration       = duration,
            easing         = InterpolationType.EASE_OUT_CUBIC,
            tags           = ["text", "smooth"],
        )

    @staticmethod
    def text_zoom_in(duration: float = 0.4) -> TransitionConfig:
        """Text grows from small"""
        return TransitionConfig(
            name           = "Text Zoom In",
            transition_type= TransitionType.TEXT_ZOOM_IN,
            category       = TransitionCategory.TEXT,
            duration       = duration,
            easing         = InterpolationType.EASE_OUT_BACK if False else InterpolationType.BACK,
            tags           = ["text", "energetic"],
        )

    # ── GET ALL PRESETS ──────────────────────────────────

    @classmethod
    def get_all(cls) -> List[TransitionConfig]:
        """Sab presets ki list return karo"""
        return [
            # Fade / Dissolve
            cls.fade_to_black(),
            cls.fade_to_white(),
            cls.smooth_dissolve(),
            cls.quick_dissolve(),

            # Action
            cls.flash_cut(),
            cls.zoom_punch(),
            cls.zoom_out_reveal(),

            # Directional
            cls.slide_left(),
            cls.slide_right(),
            cls.slide_up(),
            cls.wipe_left(),

            # Stylish
            cls.cinematic_blur(),
            cls.retro_pixelate(),
            cls.iris_open(),
            cls.rotation_spin(),
            cls.color_wash(),

            # Audio
            cls.audio_crossfade(),
            cls.audio_fade_in(),
            cls.audio_fade_out(),

            # Text
            cls.text_typewriter(),
            cls.text_slide_up(),
            cls.text_zoom_in(),
        ]

    @classmethod
    def get_by_category(cls, category: TransitionCategory) -> List[TransitionConfig]:
        """Category-wise presets"""
        return [p for p in cls.get_all() if p.category == category]

    @classmethod
    def get_by_tag(cls, tag: str) -> List[TransitionConfig]:
        """Tag-based search"""
        return [p for p in cls.get_all() if tag.lower() in [t.lower() for t in p.tags]]


# ============================================================
# MAIN TRANSITIONS ENGINE
# ============================================================

class TransitionsEngine:
    """
    🎬 Main Transitions Engine

    Sabhi transition instances manage karta hai.
    Timeline se integrate hoke playback ke waqt frames evaluate karta hai.

    Usage:
        engine = TransitionsEngine()
        config = TransitionPresets.smooth_dissolve(duration=1.0)
        instance = engine.create_transition(config, start_time=5.0,
                                              clip_a_id="c1", clip_b_id="c2")
        frame = engine.evaluate_at_time(5.5)  # Middle of transition
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

        # Instances registry
        self.instances: Dict[str, TransitionInstance] = {}

        # Stats
        self._stats = {
            "total_created"    : 0,
            "total_evaluations": 0,
            "total_previews"   : 0,
        }

        # Listeners
        self._listeners: List[Callable] = []

        logger.info(f"🎬 TransitionsEngine initialized (fps: {self.fps})")

    # ── INSTANCE MANAGEMENT ───────────────────────────────

    def create_transition(self,
                          config: TransitionConfig,
                          start_time: float = 0.0,
                          clip_a_id: Optional[str] = None,
                          clip_b_id: Optional[str] = None,
                          track_id: Optional[str] = None) -> TransitionInstance:
        """
        Naya transition instance banao aur register karo.
        """
        instance = TransitionInstance(
            config     = config,
            start_time = start_time,
            clip_a_id  = clip_a_id,
            clip_b_id  = clip_b_id,
            track_id   = track_id,
        )

        self.instances[instance.id] = instance
        self._stats["total_created"] += 1

        self._notify_listeners("transition_added", {
            "instance_id": instance.id,
            "config_name": config.name,
        })

        logger.info(
            f"🎬 Transition added: '{config.name}' @ {start_time:.2f}s "
            f"({config.duration:.1f}s)"
        )
        return instance

    def get_transition(self, instance_id: str) -> Optional[TransitionInstance]:
        return self.instances.get(instance_id)

    def remove_transition(self, instance_id: str) -> bool:
        if instance_id in self.instances:
            del self.instances[instance_id]
            self._notify_listeners("transition_removed", {"instance_id": instance_id})
            return True
        return False

    def clear_all(self):
        count = len(self.instances)
        self.instances.clear()
        logger.info(f"🗑️  Cleared {count} transitions")

    def list_transitions(self) -> List[TransitionInstance]:
        """Sab instances (sorted by start_time)"""
        return sorted(self.instances.values(), key=lambda i: i.start_time)

    def get_transitions_at_time(self, time: float) -> List[TransitionInstance]:
        """Given time pe active transitions"""
        return [i for i in self.instances.values() if i.contains_time(time)]

    def get_transitions_on_track(self, track_id: str) -> List[TransitionInstance]:
        """Specific track ke transitions"""
        return [i for i in self.instances.values() if i.track_id == track_id]

    # ── EVALUATION ────────────────────────────────────────

    def evaluate_at_time(self, time: float) -> List[TransitionFrame]:
        """
        Given time pe sab active transitions ke frames return karo.

        Multiple transitions ek saath ho sakte hain different tracks pe.
        """
        active = self.get_transitions_at_time(time)
        frames = []

        for instance in active:
            frame = instance.evaluate(time)
            if frame:
                frames.append(frame)

        self._stats["total_evaluations"] += 1
        return frames

    def evaluate_instance(self, instance_id: str,
                          time: float) -> Optional[TransitionFrame]:
        """Specific instance ke liye frame"""
        instance = self.get_transition(instance_id)
        if instance:
            return instance.evaluate(time)
        return None

    # ── PREVIEW GENERATION ────────────────────────────────

    def generate_preview(self,
                         config: TransitionConfig,
                         num_frames: int = 10) -> List[TransitionFrame]:
        """
        Ek transition config ka preview banao.
        UI mein thumbnails dikhane ke liye useful.

        Args:
            config    : TransitionConfig to preview
            num_frames: Kitne preview frames chahiye

        Returns:
            List of TransitionFrames from start to end
        """
        # Temporary instance banao preview ke liye
        temp_instance = TransitionInstance(config=config, start_time=0.0)

        frames = []
        for i in range(num_frames):
            # Evenly distributed times
            t     = (i / max(1, num_frames - 1)) * config.duration
            frame = temp_instance.evaluate(t)
            if frame:
                frames.append(frame)

        self._stats["total_previews"] += 1
        return frames

    def bake_transition(self,
                        instance_id: str,
                        fps: Optional[int] = None) -> List[TransitionFrame]:
        """
        Transition ko frame-by-frame data mein bake karo.
        Rendering ke waqt use karne ke liye.
        """
        instance = self.get_transition(instance_id)
        if not instance:
            return []

        if fps is None:
            fps = self.fps

        total_frames = int(instance.config.duration * fps) + 1
        frame_time   = 1.0 / fps

        frames = []
        for i in range(total_frames):
            t = instance.start_time + (i * frame_time)
            frame = instance.evaluate(t)
            if frame:
                frames.append(frame)

        return frames

    # ── LISTENERS ─────────────────────────────────────────

    def add_listener(self, callback: Callable):
        """Event listener add karo"""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def _notify_listeners(self, event_type: str, data: Dict):
        for cb in self._listeners:
            try:
                cb(event_type, data)
            except Exception as e:
                logger.debug(f"Listener error: {e}")

    # ── SERIALIZATION ─────────────────────────────────────

    def save_to_file(self, filepath: str) -> bool:
        """Sab transitions JSON mein save karo"""
        try:
            data = {
                "fps"        : self.fps,
                "instances"  : {iid: i.to_dict() for iid, i in self.instances.items()},
                "saved_at"   : get_timestamp(),
            }
            ensure_dir(os.path.dirname(filepath))
            return write_json(filepath, data)
        except Exception as e:
            logger.error(f"Save failed: {e}")
            return False

    def load_from_file(self, filepath: str) -> bool:
        """JSON se transitions load karo"""
        try:
            data = read_json(filepath)
            if not data:
                return False

            self.fps = data.get("fps", 30)
            self.instances.clear()

            for iid, idata in data.get("instances", {}).items():
                self.instances[iid] = TransitionInstance.from_dict(idata)

            logger.info(f"📂 Loaded {len(self.instances)} transitions")
            return True
        except Exception as e:
            logger.error(f"Load failed: {e}")
            return False

    def get_stats(self) -> Dict:
        """Engine statistics"""
        return {
            "fps"              : self.fps,
            "total_instances"  : len(self.instances),
            "total_presets"    : len(TransitionPresets.get_all()),
            "total_types"      : len(TransitionType),
            "total_created"    : self._stats["total_created"],
            "total_evaluations": self._stats["total_evaluations"],
            "total_previews"   : self._stats["total_previews"],
        }


# ============================================================
# TEST FUNCTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")
    print_banner(
        "🎬 Transitions Engine Test",
        "Video/audio/text transitions with easing curves"
    )

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))

    # ============================================================
    # Test 1: Initialize
    # ============================================================
    print_section("Test 1: Initialize Transitions Engine")

    engine = TransitionsEngine()
    stats  = engine.get_stats()

    print(f"  FPS              : {stats['fps']}")
    print(f"  Transition types : {stats['total_types']}")
    print(f"  Ready presets    : {stats['total_presets']}")

    # ============================================================
    # Test 2: Available Transition Types
    # ============================================================
    print_section("Test 2: Available Transition Types")

    categories = {}
    for ttype in TransitionType:
        cat = "audio" if "audio" in ttype.value else \
              "text"  if "text"  in ttype.value else "video"
        categories.setdefault(cat, []).append(ttype.value)

    for cat, types in categories.items():
        icon = {"video": "🎬", "audio": "🎵", "text": "📝"}.get(cat, "▪️")
        print(f"\n  {icon} {cat.upper()} ({len(types)}):")
        for t in types:
            print(f"     • {t}")

    # ============================================================
    # Test 3: Preset Library
    # ============================================================
    print_section("Test 3: Transition Presets Library")

    presets = TransitionPresets.get_all()
    print(f"  Total presets: {len(presets)}\n")

    # Group by category
    by_cat = {}
    for p in presets:
        by_cat.setdefault(p.category.value, []).append(p)

    for cat, plist in by_cat.items():
        print(f"  📂 {cat.upper()} ({len(plist)}):")
        for p in plist:
            tags_str = ", ".join(p.tags) if p.tags else ""
            print(f"     • {p.name:22s} ({p.duration:.1f}s) [{tags_str}]")

    # ============================================================
    # Test 4: Cross Dissolve Preview
    # ============================================================
    print_section("Test 4: Cross Dissolve Preview")

    dissolve = TransitionPresets.smooth_dissolve(duration=1.0)
    preview  = engine.generate_preview(dissolve, num_frames=11)

    print("  Progress → Clip A Opacity | Clip B Opacity")
    for frame in preview:
        bar_a = "█" * int(frame.clip_a_opacity * 20)
        bar_b = "█" * int(frame.clip_b_opacity * 20)
        print(f"    {frame.raw_progress:.2f} → A:{frame.clip_a_opacity:.2f} "
              f"{bar_a:20s} | B:{frame.clip_b_opacity:.2f} {bar_b:20s}")

    # ============================================================
    # Test 5: Fade to Black
    # ============================================================
    print_section("Test 5: Fade to Black Preview")

    fade = TransitionPresets.fade_to_black(duration=1.0)
    preview = engine.generate_preview(fade, num_frames=11)

    print("  Progress → A Opacity | B Opacity | Overlay Alpha (black)")
    for frame in preview:
        overlay_bar = "█" * int(frame.overlay_alpha * 20)
        print(f"    {frame.raw_progress:.2f} → A:{frame.clip_a_opacity:.2f} "
              f"| B:{frame.clip_b_opacity:.2f} | Overlay:{frame.overlay_alpha:.2f} {overlay_bar}")

    # ============================================================
    # Test 6: Slide Transitions
    # ============================================================
    print_section("Test 6: Slide Left Transition")

    slide = TransitionPresets.slide_left(duration=1.0)
    preview = engine.generate_preview(slide, num_frames=6)

    print("  Progress → Clip A offset X | Clip B offset X")
    for frame in preview:
        print(f"    {frame.raw_progress:.2f} → A:{frame.clip_a_offset_x:+.2f} "
              f"| B:{frame.clip_b_offset_x:+.2f}")

    # ============================================================
    # Test 7: Zoom Transitions
    # ============================================================
    print_section("Test 7: Zoom Transitions")

    print("\n  🔍 ZOOM IN:")
    zoom_in = TransitionPresets.zoom_punch(duration=1.0)
    preview = engine.generate_preview(zoom_in, num_frames=6)
    for frame in preview:
        scale_bar = "█" * int(frame.clip_b_scale * 20)
        print(f"    {frame.raw_progress:.2f} → B scale:{frame.clip_b_scale:.2f} {scale_bar}")

    print("\n  🔍 ZOOM OUT:")
    zoom_out = TransitionPresets.zoom_out_reveal(duration=1.0)
    preview = engine.generate_preview(zoom_out, num_frames=6)
    for frame in preview:
        print(f"    {frame.raw_progress:.2f} → A scale:{frame.clip_a_scale:.2f} "
              f"opacity:{frame.clip_a_opacity:.2f}")

    # ============================================================
    # Test 8: Flash Transition (Peak Analysis)
    # ============================================================
    print_section("Test 8: Flash Cut (Peak at Middle)")

    flash = TransitionPresets.flash_cut(duration=1.0)
    preview = engine.generate_preview(flash, num_frames=11)

    print("  Progress → Flash Intensity")
    for frame in preview:
        bar = "█" * int(frame.flash_intensity * 40)
        print(f"    {frame.raw_progress:.2f} → {frame.flash_intensity:.3f} {bar}")

    # ============================================================
    # Test 9: Rotate Transition
    # ============================================================
    print_section("Test 9: Rotation Spin")

    rotate = TransitionPresets.rotation_spin(duration=1.0)
    preview = engine.generate_preview(rotate, num_frames=6)

    print("  Progress → Clip A rotation | Clip B rotation | scales")
    for frame in preview:
        print(f"    {frame.raw_progress:.2f} → A:{frame.clip_a_rotation:+7.1f}° "
              f"scale:{frame.clip_a_scale:.2f} | B:{frame.clip_b_rotation:+7.1f}° "
              f"scale:{frame.clip_b_scale:.2f}")

    # ============================================================
    # Test 10: Audio Crossfade (Equal Power)
    # ============================================================
    print_section("Test 10: Audio Crossfade (Equal Power Curve)")

    audio_fade = TransitionPresets.audio_crossfade(duration=1.0)
    preview = engine.generate_preview(audio_fade, num_frames=11)

    print("  Progress → A Vol | B Vol | Sum (energy)")
    for frame in preview:
        total = frame.clip_a_opacity + frame.clip_b_opacity
        bar_a = "▓" * int(frame.clip_a_opacity * 20)
        bar_b = "░" * int(frame.clip_b_opacity * 20)
        print(f"    {frame.raw_progress:.2f} → A:{frame.clip_a_opacity:.2f} "
              f"{bar_a:20s} B:{frame.clip_b_opacity:.2f} {bar_b:20s} Σ:{total:.3f}")

    # ============================================================
    # Test 11: Text Typewriter
    # ============================================================
    print_section("Test 11: Text Typewriter Transition")

    text = "Hello World from AI!"
    typewriter = TransitionPresets.text_typewriter(duration=1.0, total_chars=len(text))
    preview = engine.generate_preview(typewriter, num_frames=len(text) + 1)

    print(f"  Text: '{text}'")
    print("  Progressive reveal:\n")
    for frame in preview:
        visible = text[:frame.visible_chars]
        print(f"    {frame.raw_progress:.2f} → '{visible}'")

    # ============================================================
    # Test 12: Create Timeline Instances
    # ============================================================
    print_section("Test 12: Timeline Instance Management")

    # Multiple transitions banao different times pe
    instances_data = [
        (0.0,  TransitionPresets.fade_to_black(duration=0.5)),
        (3.0,  TransitionPresets.smooth_dissolve(duration=0.8)),
        (7.0,  TransitionPresets.flash_cut(duration=0.3)),
        (12.0, TransitionPresets.zoom_punch(duration=0.6)),
        (18.0, TransitionPresets.slide_left(duration=0.7)),
    ]

    for start, config in instances_data:
        engine.create_transition(
            config    = config,
            start_time= start,
            clip_a_id = f"clip_before_{start}",
            clip_b_id = f"clip_after_{start}",
        )

    print(f"\n  Created {len(engine.instances)} transitions:")
    for instance in engine.list_transitions():
        print(f"    {instance.start_time:5.1f}s → {instance.end_time:5.1f}s | "
              f"{instance.config.name}")

    # ============================================================
    # Test 13: Query Active Transitions
    # ============================================================
    print_section("Test 13: Query Transitions at Specific Times")

    query_times = [0.25, 3.4, 7.15, 12.3, 18.35, 25.0]

    for t in query_times:
        active = engine.get_transitions_at_time(t)
        print(f"\n  At t={t:.2f}s:")
        if active:
            for instance in active:
                progress = instance.get_raw_progress(t)
                print(f"    ▶️  {instance.config.name} @ {progress*100:.1f}% progress")
        else:
            print(f"    (no active transitions)")

    # ============================================================
    # Test 14: Evaluate Frames at Time
    # ============================================================
    print_section("Test 14: Evaluate Frames at Different Times")

    for t in [0.25, 3.4, 7.15]:
        frames = engine.evaluate_at_time(t)
        print(f"\n  At t={t}s:")
        for f in frames:
            print(f"    {f.effect_type:20s} progress={f.progress:.3f} "
                  f"A_opacity={f.clip_a_opacity:.2f} B_opacity={f.clip_b_opacity:.2f}")

    # ============================================================
    # Test 15: Bake Transition to Frames
    # ============================================================
    print_section("Test 15: Bake Transition (Frame-by-Frame)")

    # Ek instance select karo
    if engine.instances:
        first_id = list(engine.instances.keys())[0]
        instance = engine.instances[first_id]

        baked = engine.bake_transition(first_id, fps=30)
        print(f"  Baked '{instance.config.name}': {len(baked)} frames @ 30fps")
        print(f"  Duration: {instance.config.duration}s\n")

        # Show first 3 and last 3
        print("  First 3 frames:")
        for f in baked[:3]:
            print(f"    t={f.time:.3f}s  progress={f.progress:.3f}")

        print("  Last 3 frames:")
        for f in baked[-3:]:
            print(f"    t={f.time:.3f}s  progress={f.progress:.3f}")

    # ============================================================
    # Test 16: Search Presets by Tag
    # ============================================================
    print_section("Test 16: Search Presets by Tags")

    tags_to_test = ["cinematic", "action", "smooth", "retro", "audio", "text"]

    for tag in tags_to_test:
        results = TransitionPresets.get_by_tag(tag)
        print(f"\n  🏷️  Tag '{tag}': {len(results)} presets")
        for r in results[:3]:
            print(f"     • {r.name}")

    # ============================================================
    # Test 17: Save & Load
    # ============================================================
    print_section("Test 17: Save & Load Transitions")

    output_dir = os.path.join(base_dir, "temp", "transitions_tests")
    ensure_dir(output_dir)
    save_path = os.path.join(output_dir, "test_transitions.json")

    success = engine.save_to_file(save_path)
    if success:
        from src.utils import get_file_size, format_bytes
        size = format_bytes(get_file_size(save_path))
        print(f"  ✅ Saved: {os.path.basename(save_path)} ({size})")

        # Reload
        new_engine = TransitionsEngine()
        loaded = new_engine.load_from_file(save_path)

        if loaded:
            new_stats = new_engine.get_stats()
            print(f"\n  ✅ Reloaded successfully:")
            print(f"     Total instances: {new_stats['total_instances']}")

            # Verify values match
            orig_frames = engine.evaluate_at_time(3.4)
            new_frames  = new_engine.evaluate_at_time(3.4)
            match = len(orig_frames) == len(new_frames)
            print(f"     Verify match   : {'✅' if match else '⚠️'}")

    # ============================================================
    # Test 18: Final Statistics
    # ============================================================
    print_section("Test 18: Final Statistics")

    stats = engine.get_stats()
    print(f"  FPS               : {stats['fps']}")
    print(f"  Total instances   : {stats['total_instances']}")
    print(f"  Ready presets     : {stats['total_presets']}")
    print(f"  Total types       : {stats['total_types']}")
    print(f"  Instances created : {stats['total_created']}")
    print(f"  Evaluations       : {stats['total_evaluations']}")
    print(f"  Previews generated: {stats['total_previews']}")

    print_section("Output Files")
    print(f"  📁 Data saved in:")
    print(f"     {output_dir}")

    print_banner(
        "✅ Transitions Engine Ready!",
        f"{stats['total_types']} types | {stats['total_presets']} presets | "
        f"{stats['total_instances']} instances"
    )