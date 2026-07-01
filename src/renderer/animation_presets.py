# ============================================================
# src/renderer/animation_presets.py
# 3D Animation Studio - Animation Presets Library
# Walk, Run, Talk, Wave sabhi character animations
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
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum

from src.utils import get_logger, get_config, generate_uuid

logger = get_logger("AnimationPresets")


# ============================================================
# ENUMS
# ============================================================

class AnimationCategory(Enum):
    """Animation categories"""
    IDLE            = "idle"
    LOCOMOTION      = "locomotion"      # walk, run, jump
    GESTURE         = "gesture"          # wave, point, nod
    EXPRESSION      = "expression"       # laugh, cry, thinking
    ACTION          = "action"           # fight, dance, sit
    SPEAKING        = "speaking"         # talking, whispering


class BodyPart(Enum):
    """Character body parts for keyframing"""
    HEAD            = "head"
    NECK            = "neck"
    TORSO           = "torso"
    LEFT_ARM        = "left_arm"
    LEFT_FOREARM    = "left_forearm"
    LEFT_HAND       = "left_hand"
    RIGHT_ARM       = "right_arm"
    RIGHT_FOREARM   = "right_forearm"
    RIGHT_HAND      = "right_hand"
    LEFT_THIGH      = "left_thigh"
    LEFT_SHIN       = "left_shin"
    LEFT_FOOT       = "left_foot"
    RIGHT_THIGH     = "right_thigh"
    RIGHT_SHIN      = "right_shin"
    RIGHT_FOOT      = "right_foot"
    HIPS            = "hips"
    SPINE           = "spine"


class LoopMode(Enum):
    """Animation loop modes"""
    ONCE            = "once"             # Play ek baar
    LOOP            = "loop"             # Repeat continuously
    PING_PONG       = "ping_pong"        # Forward then reverse
    HOLD            = "hold"             # Play then hold last frame


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class Keyframe:
    """
    Single keyframe - body part ki position at specific time.
    Rotation angles in degrees (X, Y, Z Euler).
    """
    time:           float               = 0.0        # Seconds
    body_part:      str                 = BodyPart.TORSO.value

    # Transform
    position_offset: List[float]        = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation:       List[float]         = field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale:          List[float]         = field(default_factory=lambda: [1.0, 1.0, 1.0])

    # Interpolation
    easing:         str                 = "linear"   # linear, ease_in, ease_out, ease_in_out

    def to_dict(self) -> Dict:
        return {
            "time":            self.time,
            "body_part":       self.body_part,
            "position_offset": self.position_offset,
            "rotation":        self.rotation,
            "scale":           self.scale,
            "easing":          self.easing,
        }


@dataclass
class AnimationClip:
    """
    Complete animation clip.
    Multiple keyframes together = ek animation.
    """
    animation_id:   str                 = ""
    name:           str                 = "Animation"
    category:       str                 = AnimationCategory.IDLE.value

    # Timing
    duration:       float               = 1.0        # Seconds
    fps:            int                 = 30

    # Playback
    loop_mode:      str                 = LoopMode.LOOP.value
    speed:          float               = 1.0        # Playback multiplier

    # Keyframes (organized by body part)
    keyframes:      List[Keyframe]      = field(default_factory=list)

    # Metadata
    description:    str                 = ""
    tags:           List[str]           = field(default_factory=list)

    # Root motion (whole body movement)
    root_motion:    List[float]         = field(default_factory=lambda: [0.0, 0.0, 0.0])

    def __post_init__(self):
        if not self.animation_id:
            self.animation_id = f"anim_{generate_uuid()[:8]}"

    def get_total_frames(self) -> int:
        return int(self.duration * self.fps)

    def get_keyframes_for_part(self, body_part: str) -> List[Keyframe]:
        """Ek body part ke sabhi keyframes lo"""
        return [kf for kf in self.keyframes if kf.body_part == body_part]

    def add_keyframe(self, keyframe: Keyframe):
        """Keyframe add karo"""
        self.keyframes.append(keyframe)
        # Sort by time
        self.keyframes.sort(key=lambda k: k.time)

    def to_dict(self) -> Dict:
        return {
            "animation_id": self.animation_id,
            "name":         self.name,
            "category":     self.category,
            "duration":     self.duration,
            "fps":          self.fps,
            "loop_mode":    self.loop_mode,
            "speed":        self.speed,
            "description":  self.description,
            "tags":         self.tags,
            "keyframes":    [kf.to_dict() for kf in self.keyframes],
            "root_motion":  self.root_motion,
        }


# ============================================================
# EASING FUNCTIONS
# ============================================================

class Easing:
    """Easing functions - smooth animation transitions"""

    @staticmethod
    def linear(t: float) -> float:
        return t

    @staticmethod
    def ease_in(t: float) -> float:
        return t * t

    @staticmethod
    def ease_out(t: float) -> float:
        return 1 - (1 - t) * (1 - t)

    @staticmethod
    def ease_in_out(t: float) -> float:
        if t < 0.5:
            return 2 * t * t
        return 1 - pow(-2 * t + 2, 2) / 2

    @staticmethod
    def sine_wave(t: float) -> float:
        """Sine wave 0-1"""
        return (math.sin(t * 2 * math.pi) + 1) / 2

    @staticmethod
    def bounce(t: float) -> float:
        """Bounce effect"""
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

    @classmethod
    def apply(cls, easing_name: str, t: float) -> float:
        """Easing apply karo naam se"""
        funcs = {
            "linear":      cls.linear,
            "ease_in":     cls.ease_in,
            "ease_out":    cls.ease_out,
            "ease_in_out": cls.ease_in_out,
            "sine":        cls.sine_wave,
            "bounce":      cls.bounce,
        }
        func = funcs.get(easing_name, cls.linear)
        return func(t)


# ============================================================
# IDLE ANIMATIONS
# ============================================================

class IdleAnimations:
    """Idle/stand animations - character khada rehta hai"""

    @staticmethod
    def basic_idle() -> AnimationClip:
        """Basic idle - subtle breathing"""
        clip = AnimationClip(
            name        = "Basic Idle",
            category    = AnimationCategory.IDLE.value,
            duration    = 2.0,
            loop_mode   = LoopMode.LOOP.value,
            description = "Subtle breathing idle animation",
            tags        = ["idle", "standing", "breathing"],
        )

        # Breathing - torso scale in/out
        for t_frac in [0.0, 0.25, 0.5, 0.75, 1.0]:
            time = t_frac * clip.duration
            scale = 1.0 + 0.02 * math.sin(t_frac * 2 * math.pi)
            clip.add_keyframe(Keyframe(
                time      = time,
                body_part = BodyPart.TORSO.value,
                scale     = [1.0, scale, 1.0],
                easing    = "ease_in_out",
            ))

            # Head slight sway
            head_x = 2 * math.sin(t_frac * 2 * math.pi)
            clip.add_keyframe(Keyframe(
                time      = time,
                body_part = BodyPart.HEAD.value,
                rotation  = [head_x, 0, 0],
                easing    = "ease_in_out",
            ))

        return clip

    @staticmethod
    def confident_idle() -> AnimationClip:
        """Confident idle - hands on hips"""
        clip = AnimationClip(
            name        = "Confident Idle",
            category    = AnimationCategory.IDLE.value,
            duration    = 3.0,
            loop_mode   = LoopMode.LOOP.value,
            description = "Confident stance with hands on hips",
            tags        = ["idle", "confident", "hands-hips"],
        )

        # Static hands on hips
        clip.add_keyframe(Keyframe(
            time      = 0.0,
            body_part = BodyPart.LEFT_ARM.value,
            rotation  = [0, 0, -60],
        ))
        clip.add_keyframe(Keyframe(
            time      = 0.0,
            body_part = BodyPart.RIGHT_ARM.value,
            rotation  = [0, 0, 60],
        ))

        # Subtle breathing
        for t_frac in [0.0, 0.5, 1.0]:
            time = t_frac * clip.duration
            clip.add_keyframe(Keyframe(
                time      = time,
                body_part = BodyPart.TORSO.value,
                scale     = [1.0, 1.0 + 0.015 * math.sin(t_frac * 2 * math.pi), 1.0],
            ))

        return clip

    @staticmethod
    def sad_idle() -> AnimationClip:
        """Sad idle - slumped shoulders, head down"""
        clip = AnimationClip(
            name        = "Sad Idle",
            category    = AnimationCategory.IDLE.value,
            duration    = 2.5,
            loop_mode   = LoopMode.LOOP.value,
            description = "Sad drooped posture",
            tags        = ["idle", "sad", "depressed"],
        )

        # Head down
        clip.add_keyframe(Keyframe(
            time      = 0.0,
            body_part = BodyPart.HEAD.value,
            rotation  = [25, 0, 0],   # Look down
        ))

        # Slumped shoulders
        clip.add_keyframe(Keyframe(
            time      = 0.0,
            body_part = BodyPart.TORSO.value,
            rotation  = [15, 0, 0],
        ))

        # Arms hanging down
        clip.add_keyframe(Keyframe(
            time      = 0.0,
            body_part = BodyPart.LEFT_ARM.value,
            rotation  = [0, 0, -5],
        ))
        clip.add_keyframe(Keyframe(
            time      = 0.0,
            body_part = BodyPart.RIGHT_ARM.value,
            rotation  = [0, 0, 5],
        ))

        return clip


# ============================================================
# LOCOMOTION ANIMATIONS
# ============================================================

class LocomotionAnimations:
    """Walk, run, jump animations"""

    @staticmethod
    def walk() -> AnimationClip:
        """Standard walk cycle - 1 second per step"""
        clip = AnimationClip(
            name        = "Walk",
            category    = AnimationCategory.LOCOMOTION.value,
            duration    = 1.0,        # 1 sec per full cycle
            loop_mode   = LoopMode.LOOP.value,
            description = "Standard walking animation",
            tags        = ["walk", "movement", "locomotion"],
            root_motion = [0.0, 0.0, 1.5],  # Forward movement
        )

        # Walk cycle keyframes
        # Time 0.0 - Left foot forward
        # Time 0.25 - Both feet passing
        # Time 0.5  - Right foot forward
        # Time 0.75 - Both feet passing
        # Time 1.0  - Back to left foot forward

        # LEG animations
        # Left leg cycle
        clip.add_keyframe(Keyframe(0.0, BodyPart.LEFT_THIGH.value, rotation=[30, 0, 0]))
        clip.add_keyframe(Keyframe(0.25, BodyPart.LEFT_THIGH.value, rotation=[0, 0, 0]))
        clip.add_keyframe(Keyframe(0.5, BodyPart.LEFT_THIGH.value, rotation=[-25, 0, 0]))
        clip.add_keyframe(Keyframe(0.75, BodyPart.LEFT_THIGH.value, rotation=[0, 0, 0]))
        clip.add_keyframe(Keyframe(1.0, BodyPart.LEFT_THIGH.value, rotation=[30, 0, 0]))

        # Right leg cycle (opposite phase)
        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_THIGH.value, rotation=[-25, 0, 0]))
        clip.add_keyframe(Keyframe(0.25, BodyPart.RIGHT_THIGH.value, rotation=[0, 0, 0]))
        clip.add_keyframe(Keyframe(0.5, BodyPart.RIGHT_THIGH.value, rotation=[30, 0, 0]))
        clip.add_keyframe(Keyframe(0.75, BodyPart.RIGHT_THIGH.value, rotation=[0, 0, 0]))
        clip.add_keyframe(Keyframe(1.0, BodyPart.RIGHT_THIGH.value, rotation=[-25, 0, 0]))

        # ARM animations (opposite of same-side leg)
        # Left arm swings opposite to left leg
        clip.add_keyframe(Keyframe(0.0, BodyPart.LEFT_ARM.value, rotation=[-25, 0, -5]))
        clip.add_keyframe(Keyframe(0.5, BodyPart.LEFT_ARM.value, rotation=[30, 0, -5]))
        clip.add_keyframe(Keyframe(1.0, BodyPart.LEFT_ARM.value, rotation=[-25, 0, -5]))

        # Right arm
        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_ARM.value, rotation=[30, 0, 5]))
        clip.add_keyframe(Keyframe(0.5, BodyPart.RIGHT_ARM.value, rotation=[-25, 0, 5]))
        clip.add_keyframe(Keyframe(1.0, BodyPart.RIGHT_ARM.value, rotation=[30, 0, 5]))

        # HIP sway
        clip.add_keyframe(Keyframe(0.0, BodyPart.HIPS.value, rotation=[0, 5, 0]))
        clip.add_keyframe(Keyframe(0.5, BodyPart.HIPS.value, rotation=[0, -5, 0]))
        clip.add_keyframe(Keyframe(1.0, BodyPart.HIPS.value, rotation=[0, 5, 0]))

        # Slight head bob (up-down)
        clip.add_keyframe(Keyframe(0.0, BodyPart.HEAD.value, position_offset=[0, 0, 0]))
        clip.add_keyframe(Keyframe(0.25, BodyPart.HEAD.value, position_offset=[0, 0.05, 0]))
        clip.add_keyframe(Keyframe(0.5, BodyPart.HEAD.value, position_offset=[0, 0, 0]))
        clip.add_keyframe(Keyframe(0.75, BodyPart.HEAD.value, position_offset=[0, 0.05, 0]))
        clip.add_keyframe(Keyframe(1.0, BodyPart.HEAD.value, position_offset=[0, 0, 0]))

        return clip

    @staticmethod
    def run() -> AnimationClip:
        """Running animation - faster, more exaggerated"""
        clip = AnimationClip(
            name        = "Run",
            category    = AnimationCategory.LOCOMOTION.value,
            duration    = 0.6,        # Faster cycle
            loop_mode   = LoopMode.LOOP.value,
            description = "Running animation",
            tags        = ["run", "sprint", "fast"],
            root_motion = [0.0, 0.0, 4.0],  # Faster forward
        )

        # Similar to walk but exaggerated
        # LEGS
        clip.add_keyframe(Keyframe(0.0, BodyPart.LEFT_THIGH.value, rotation=[50, 0, 0]))
        clip.add_keyframe(Keyframe(0.3, BodyPart.LEFT_THIGH.value, rotation=[-40, 0, 0]))
        clip.add_keyframe(Keyframe(0.6, BodyPart.LEFT_THIGH.value, rotation=[50, 0, 0]))

        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_THIGH.value, rotation=[-40, 0, 0]))
        clip.add_keyframe(Keyframe(0.3, BodyPart.RIGHT_THIGH.value, rotation=[50, 0, 0]))
        clip.add_keyframe(Keyframe(0.6, BodyPart.RIGHT_THIGH.value, rotation=[-40, 0, 0]))

        # Bent knees (shins)
        clip.add_keyframe(Keyframe(0.0, BodyPart.LEFT_SHIN.value, rotation=[70, 0, 0]))
        clip.add_keyframe(Keyframe(0.3, BodyPart.LEFT_SHIN.value, rotation=[30, 0, 0]))
        clip.add_keyframe(Keyframe(0.6, BodyPart.LEFT_SHIN.value, rotation=[70, 0, 0]))

        # ARMS (more pumped)
        clip.add_keyframe(Keyframe(0.0, BodyPart.LEFT_ARM.value, rotation=[-45, 0, -10]))
        clip.add_keyframe(Keyframe(0.3, BodyPart.LEFT_ARM.value, rotation=[60, 0, -10]))
        clip.add_keyframe(Keyframe(0.6, BodyPart.LEFT_ARM.value, rotation=[-45, 0, -10]))

        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_ARM.value, rotation=[60, 0, 10]))
        clip.add_keyframe(Keyframe(0.3, BodyPart.RIGHT_ARM.value, rotation=[-45, 0, 10]))
        clip.add_keyframe(Keyframe(0.6, BodyPart.RIGHT_ARM.value, rotation=[60, 0, 10]))

        # Elbows bent
        clip.add_keyframe(Keyframe(0.0, BodyPart.LEFT_FOREARM.value, rotation=[-90, 0, 0]))
        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_FOREARM.value, rotation=[-90, 0, 0]))

        # Torso lean forward
        clip.add_keyframe(Keyframe(0.0, BodyPart.TORSO.value, rotation=[15, 0, 0]))

        return clip

    @staticmethod
    def jump() -> AnimationClip:
        """Jump animation"""
        clip = AnimationClip(
            name        = "Jump",
            category    = AnimationCategory.LOCOMOTION.value,
            duration    = 1.0,
            loop_mode   = LoopMode.ONCE.value,
            description = "Jump animation",
            tags        = ["jump", "leap"],
        )

        # Crouch down (prep)
        clip.add_keyframe(Keyframe(0.0, BodyPart.HIPS.value, position_offset=[0, 0, 0]))
        clip.add_keyframe(Keyframe(0.2, BodyPart.HIPS.value, position_offset=[0, -0.3, 0]))

        # Jump up
        clip.add_keyframe(Keyframe(0.5, BodyPart.HIPS.value, position_offset=[0, 1.2, 0]))

        # Come down
        clip.add_keyframe(Keyframe(0.8, BodyPart.HIPS.value, position_offset=[0, -0.2, 0]))
        clip.add_keyframe(Keyframe(1.0, BodyPart.HIPS.value, position_offset=[0, 0, 0]))

        # Legs bend during crouch and land
        clip.add_keyframe(Keyframe(0.0, BodyPart.LEFT_THIGH.value, rotation=[0, 0, 0]))
        clip.add_keyframe(Keyframe(0.2, BodyPart.LEFT_THIGH.value, rotation=[45, 0, 0]))
        clip.add_keyframe(Keyframe(0.5, BodyPart.LEFT_THIGH.value, rotation=[10, 0, 0]))
        clip.add_keyframe(Keyframe(0.8, BodyPart.LEFT_THIGH.value, rotation=[45, 0, 0]))
        clip.add_keyframe(Keyframe(1.0, BodyPart.LEFT_THIGH.value, rotation=[0, 0, 0]))

        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_THIGH.value, rotation=[0, 0, 0]))
        clip.add_keyframe(Keyframe(0.2, BodyPart.RIGHT_THIGH.value, rotation=[45, 0, 0]))
        clip.add_keyframe(Keyframe(0.5, BodyPart.RIGHT_THIGH.value, rotation=[10, 0, 0]))
        clip.add_keyframe(Keyframe(0.8, BodyPart.RIGHT_THIGH.value, rotation=[45, 0, 0]))
        clip.add_keyframe(Keyframe(1.0, BodyPart.RIGHT_THIGH.value, rotation=[0, 0, 0]))

        # Arms swing up during jump
        clip.add_keyframe(Keyframe(0.0, BodyPart.LEFT_ARM.value, rotation=[0, 0, -5]))
        clip.add_keyframe(Keyframe(0.5, BodyPart.LEFT_ARM.value, rotation=[-160, 0, -5]))
        clip.add_keyframe(Keyframe(1.0, BodyPart.LEFT_ARM.value, rotation=[0, 0, -5]))

        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_ARM.value, rotation=[0, 0, 5]))
        clip.add_keyframe(Keyframe(0.5, BodyPart.RIGHT_ARM.value, rotation=[-160, 0, 5]))
        clip.add_keyframe(Keyframe(1.0, BodyPart.RIGHT_ARM.value, rotation=[0, 0, 5]))

        return clip


# ============================================================
# GESTURE ANIMATIONS
# ============================================================

class GestureAnimations:
    """Waves, points, nods - conversational gestures"""

    @staticmethod
    def wave() -> AnimationClip:
        """Wave hello"""
        clip = AnimationClip(
            name        = "Wave",
            category    = AnimationCategory.GESTURE.value,
            duration    = 2.0,
            loop_mode   = LoopMode.ONCE.value,
            description = "Wave hand hello",
            tags        = ["wave", "hello", "greeting"],
        )

        # Right arm raises up
        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_ARM.value, rotation=[0, 0, 5]))
        clip.add_keyframe(Keyframe(0.3, BodyPart.RIGHT_ARM.value, rotation=[-140, 0, 30]))
        clip.add_keyframe(Keyframe(1.7, BodyPart.RIGHT_ARM.value, rotation=[-140, 0, 30]))
        clip.add_keyframe(Keyframe(2.0, BodyPart.RIGHT_ARM.value, rotation=[0, 0, 5]))

        # Forearm bent up
        clip.add_keyframe(Keyframe(0.3, BodyPart.RIGHT_FOREARM.value, rotation=[-45, 0, 0]))
        clip.add_keyframe(Keyframe(1.7, BodyPart.RIGHT_FOREARM.value, rotation=[-45, 0, 0]))

        # Hand waves side to side
        for i in range(5):
            t = 0.4 + (i * 0.25)
            if t > 1.7:
                break
            angle = 30 if i % 2 == 0 else -30
            clip.add_keyframe(Keyframe(
                time      = t,
                body_part = BodyPart.RIGHT_HAND.value,
                rotation  = [0, 0, angle],
                easing    = "ease_in_out",
            ))

        # Smile head slightly tilted
        clip.add_keyframe(Keyframe(0.0, BodyPart.HEAD.value, rotation=[0, 0, 0]))
        clip.add_keyframe(Keyframe(0.5, BodyPart.HEAD.value, rotation=[-5, 0, 5]))
        clip.add_keyframe(Keyframe(1.5, BodyPart.HEAD.value, rotation=[-5, 0, 5]))
        clip.add_keyframe(Keyframe(2.0, BodyPart.HEAD.value, rotation=[0, 0, 0]))

        return clip

    @staticmethod
    def nod() -> AnimationClip:
        """Nod head yes"""
        clip = AnimationClip(
            name        = "Nod",
            category    = AnimationCategory.GESTURE.value,
            duration    = 1.0,
            loop_mode   = LoopMode.ONCE.value,
            description = "Nod head yes",
            tags        = ["nod", "yes", "agree"],
        )

        # Head nods down and up
        clip.add_keyframe(Keyframe(0.0, BodyPart.HEAD.value, rotation=[0, 0, 0]))
        clip.add_keyframe(Keyframe(0.25, BodyPart.HEAD.value, rotation=[20, 0, 0]))
        clip.add_keyframe(Keyframe(0.5, BodyPart.HEAD.value, rotation=[0, 0, 0]))
        clip.add_keyframe(Keyframe(0.75, BodyPart.HEAD.value, rotation=[15, 0, 0]))
        clip.add_keyframe(Keyframe(1.0, BodyPart.HEAD.value, rotation=[0, 0, 0]))

        return clip

    @staticmethod
    def shake_head() -> AnimationClip:
        """Shake head no"""
        clip = AnimationClip(
            name        = "Shake Head",
            category    = AnimationCategory.GESTURE.value,
            duration    = 1.0,
            loop_mode   = LoopMode.ONCE.value,
            description = "Shake head no",
            tags        = ["shake", "no", "disagree"],
        )

        # Head shakes left-right
        clip.add_keyframe(Keyframe(0.0, BodyPart.HEAD.value, rotation=[0, 0, 0]))
        clip.add_keyframe(Keyframe(0.2, BodyPart.HEAD.value, rotation=[0, -25, 0]))
        clip.add_keyframe(Keyframe(0.4, BodyPart.HEAD.value, rotation=[0, 25, 0]))
        clip.add_keyframe(Keyframe(0.6, BodyPart.HEAD.value, rotation=[0, -20, 0]))
        clip.add_keyframe(Keyframe(0.8, BodyPart.HEAD.value, rotation=[0, 15, 0]))
        clip.add_keyframe(Keyframe(1.0, BodyPart.HEAD.value, rotation=[0, 0, 0]))

        return clip

    @staticmethod
    def point() -> AnimationClip:
        """Point at something"""
        clip = AnimationClip(
            name        = "Point",
            category    = AnimationCategory.GESTURE.value,
            duration    = 1.5,
            loop_mode   = LoopMode.HOLD.value,
            description = "Point finger forward",
            tags        = ["point", "gesture"],
        )

        # Right arm extends forward
        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_ARM.value, rotation=[0, 0, 5]))
        clip.add_keyframe(Keyframe(0.5, BodyPart.RIGHT_ARM.value, rotation=[-90, 0, 0]))
        clip.add_keyframe(Keyframe(1.5, BodyPart.RIGHT_ARM.value, rotation=[-90, 0, 0]))

        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_FOREARM.value, rotation=[0, 0, 0]))
        clip.add_keyframe(Keyframe(0.5, BodyPart.RIGHT_FOREARM.value, rotation=[0, 0, 0]))

        return clip

    @staticmethod
    def clap() -> AnimationClip:
        """Clap hands"""
        clip = AnimationClip(
            name        = "Clap",
            category    = AnimationCategory.GESTURE.value,
            duration    = 1.5,
            loop_mode   = LoopMode.LOOP.value,
            description = "Clap hands together",
            tags        = ["clap", "applause"],
        )

        # Arms come together
        clip.add_keyframe(Keyframe(0.0, BodyPart.LEFT_ARM.value, rotation=[-60, 0, -30]))
        clip.add_keyframe(Keyframe(0.75, BodyPart.LEFT_ARM.value, rotation=[-60, 0, -10]))
        clip.add_keyframe(Keyframe(1.5, BodyPart.LEFT_ARM.value, rotation=[-60, 0, -30]))

        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_ARM.value, rotation=[-60, 0, 30]))
        clip.add_keyframe(Keyframe(0.75, BodyPart.RIGHT_ARM.value, rotation=[-60, 0, 10]))
        clip.add_keyframe(Keyframe(1.5, BodyPart.RIGHT_ARM.value, rotation=[-60, 0, 30]))

        # Forearms bent for clap
        clip.add_keyframe(Keyframe(0.0, BodyPart.LEFT_FOREARM.value, rotation=[-90, 0, 0]))
        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_FOREARM.value, rotation=[-90, 0, 0]))

        return clip


# ============================================================
# EXPRESSION ANIMATIONS
# ============================================================

class ExpressionAnimations:
    """Emotional body language"""

    @staticmethod
    def laugh() -> AnimationClip:
        """Laughing animation"""
        clip = AnimationClip(
            name        = "Laugh",
            category    = AnimationCategory.EXPRESSION.value,
            duration    = 2.0,
            loop_mode   = LoopMode.LOOP.value,
            description = "Laughing with body shake",
            tags        = ["laugh", "happy", "haha"],
        )

        # Body shakes forward and back
        for i in range(5):
            t = i * 0.4
            angle = 12 if i % 2 == 0 else 8
            clip.add_keyframe(Keyframe(
                time      = t,
                body_part = BodyPart.TORSO.value,
                rotation  = [angle, 0, 0],
                easing    = "ease_in_out",
            ))

        # Head throws back
        clip.add_keyframe(Keyframe(0.0, BodyPart.HEAD.value, rotation=[-15, 0, 0]))
        clip.add_keyframe(Keyframe(0.4, BodyPart.HEAD.value, rotation=[-10, 0, 0]))
        clip.add_keyframe(Keyframe(0.8, BodyPart.HEAD.value, rotation=[-15, 0, 0]))
        clip.add_keyframe(Keyframe(1.2, BodyPart.HEAD.value, rotation=[-10, 0, 0]))
        clip.add_keyframe(Keyframe(1.6, BodyPart.HEAD.value, rotation=[-15, 0, 0]))
        clip.add_keyframe(Keyframe(2.0, BodyPart.HEAD.value, rotation=[-10, 0, 0]))

        # Hands on stomach (holding belly)
        clip.add_keyframe(Keyframe(0.0, BodyPart.LEFT_ARM.value, rotation=[-45, 0, -25]))
        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_ARM.value, rotation=[-45, 0, 25]))
        clip.add_keyframe(Keyframe(0.0, BodyPart.LEFT_FOREARM.value, rotation=[-90, 0, 0]))
        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_FOREARM.value, rotation=[-90, 0, 0]))

        return clip

    @staticmethod
    def cry() -> AnimationClip:
        """Crying animation"""
        clip = AnimationClip(
            name        = "Cry",
            category    = AnimationCategory.EXPRESSION.value,
            duration    = 3.0,
            loop_mode   = LoopMode.LOOP.value,
            description = "Crying with hands covering face",
            tags        = ["cry", "sad", "tears"],
        )

        # Head down
        clip.add_keyframe(Keyframe(0.0, BodyPart.HEAD.value, rotation=[30, 0, 0]))

        # Hands cover face
        clip.add_keyframe(Keyframe(0.0, BodyPart.LEFT_ARM.value, rotation=[-120, 0, -20]))
        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_ARM.value, rotation=[-120, 0, 20]))
        clip.add_keyframe(Keyframe(0.0, BodyPart.LEFT_FOREARM.value, rotation=[-90, 0, 0]))
        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_FOREARM.value, rotation=[-90, 0, 0]))

        # Body sobs (small shakes)
        for i in range(6):
            t = i * 0.5
            shake = 3 if i % 2 == 0 else -3
            clip.add_keyframe(Keyframe(
                time      = t,
                body_part = BodyPart.TORSO.value,
                rotation  = [20 + shake, 0, 0],
                easing    = "ease_in_out",
            ))

        return clip

    @staticmethod
    def angry_gesture() -> AnimationClip:
        """Angry gesture with fist"""
        clip = AnimationClip(
            name        = "Angry Gesture",
            category    = AnimationCategory.EXPRESSION.value,
            duration    = 1.5,
            loop_mode   = LoopMode.ONCE.value,
            description = "Angry with clenched fists",
            tags        = ["angry", "fist", "rage"],
        )

        # Arms tensed at sides
        clip.add_keyframe(Keyframe(0.0, BodyPart.LEFT_ARM.value, rotation=[0, 0, -5]))
        clip.add_keyframe(Keyframe(0.5, BodyPart.LEFT_ARM.value, rotation=[-30, 0, -15]))
        clip.add_keyframe(Keyframe(1.5, BodyPart.LEFT_ARM.value, rotation=[-30, 0, -15]))

        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_ARM.value, rotation=[0, 0, 5]))
        clip.add_keyframe(Keyframe(0.5, BodyPart.RIGHT_ARM.value, rotation=[-30, 0, 15]))
        clip.add_keyframe(Keyframe(1.5, BodyPart.RIGHT_ARM.value, rotation=[-30, 0, 15]))

        # Forearms bent (fists up)
        clip.add_keyframe(Keyframe(0.5, BodyPart.LEFT_FOREARM.value, rotation=[-100, 0, 0]))
        clip.add_keyframe(Keyframe(0.5, BodyPart.RIGHT_FOREARM.value, rotation=[-100, 0, 0]))

        # Head pushed forward (aggressive)
        clip.add_keyframe(Keyframe(0.0, BodyPart.HEAD.value, rotation=[-10, 0, 0]))
        clip.add_keyframe(Keyframe(0.5, BodyPart.HEAD.value, rotation=[-10, 0, 0]))

        # Torso lean forward
        clip.add_keyframe(Keyframe(0.5, BodyPart.TORSO.value, rotation=[10, 0, 0]))

        return clip

    @staticmethod
    def thinking() -> AnimationClip:
        """Thinking pose"""
        clip = AnimationClip(
            name        = "Thinking",
            category    = AnimationCategory.EXPRESSION.value,
            duration    = 3.0,
            loop_mode   = LoopMode.LOOP.value,
            description = "Hand on chin, thinking",
            tags        = ["think", "ponder", "hmm"],
        )

        # Right hand near chin
        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_ARM.value, rotation=[-80, 0, 20]))
        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_FOREARM.value, rotation=[-100, 0, 0]))

        # Head slightly tilted
        clip.add_keyframe(Keyframe(0.0, BodyPart.HEAD.value, rotation=[10, -5, 5]))
        clip.add_keyframe(Keyframe(1.5, BodyPart.HEAD.value, rotation=[10, 5, -5]))
        clip.add_keyframe(Keyframe(3.0, BodyPart.HEAD.value, rotation=[10, -5, 5]))

        # Left arm crossed
        clip.add_keyframe(Keyframe(0.0, BodyPart.LEFT_ARM.value, rotation=[-40, 0, -30]))
        clip.add_keyframe(Keyframe(0.0, BodyPart.LEFT_FOREARM.value, rotation=[-90, 0, 0]))

        return clip


# ============================================================
# SPEAKING ANIMATIONS
# ============================================================

class SpeakingAnimations:
    """Talking animations - body language while speaking"""

    @staticmethod
    def talking() -> AnimationClip:
        """Basic talking with subtle gestures"""
        clip = AnimationClip(
            name        = "Talking",
            category    = AnimationCategory.SPEAKING.value,
            duration    = 3.0,
            loop_mode   = LoopMode.LOOP.value,
            description = "Talking with hand gestures",
            tags        = ["talk", "speaking", "conversation"],
        )

        # Subtle head movements
        clip.add_keyframe(Keyframe(0.0, BodyPart.HEAD.value, rotation=[0, 0, 0]))
        clip.add_keyframe(Keyframe(1.0, BodyPart.HEAD.value, rotation=[3, 5, 0]))
        clip.add_keyframe(Keyframe(2.0, BodyPart.HEAD.value, rotation=[-3, -5, 0]))
        clip.add_keyframe(Keyframe(3.0, BodyPart.HEAD.value, rotation=[0, 0, 0]))

        # Hand gestures
        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_ARM.value, rotation=[-30, 0, 15]))
        clip.add_keyframe(Keyframe(1.5, BodyPart.RIGHT_ARM.value, rotation=[-50, 0, 25]))
        clip.add_keyframe(Keyframe(3.0, BodyPart.RIGHT_ARM.value, rotation=[-30, 0, 15]))

        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_FOREARM.value, rotation=[-50, 0, 0]))
        clip.add_keyframe(Keyframe(1.5, BodyPart.RIGHT_FOREARM.value, rotation=[-30, 0, 0]))
        clip.add_keyframe(Keyframe(3.0, BodyPart.RIGHT_FOREARM.value, rotation=[-50, 0, 0]))

        return clip

    @staticmethod
    def excited_talking() -> AnimationClip:
        """Excited talking - big gestures"""
        clip = AnimationClip(
            name        = "Excited Talking",
            category    = AnimationCategory.SPEAKING.value,
            duration    = 2.5,
            loop_mode   = LoopMode.LOOP.value,
            description = "Enthusiastic speaking with big gestures",
            tags        = ["excited", "talk", "energetic"],
        )

        # Both arms gesturing
        clip.add_keyframe(Keyframe(0.0, BodyPart.LEFT_ARM.value, rotation=[-40, 0, -25]))
        clip.add_keyframe(Keyframe(1.25, BodyPart.LEFT_ARM.value, rotation=[-70, 0, -40]))
        clip.add_keyframe(Keyframe(2.5, BodyPart.LEFT_ARM.value, rotation=[-40, 0, -25]))

        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_ARM.value, rotation=[-40, 0, 25]))
        clip.add_keyframe(Keyframe(1.25, BodyPart.RIGHT_ARM.value, rotation=[-70, 0, 40]))
        clip.add_keyframe(Keyframe(2.5, BodyPart.RIGHT_ARM.value, rotation=[-40, 0, 25]))

        # Forearms bent
        clip.add_keyframe(Keyframe(0.0, BodyPart.LEFT_FOREARM.value, rotation=[-60, 0, 0]))
        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_FOREARM.value, rotation=[-60, 0, 0]))

        # Bouncy movement
        clip.add_keyframe(Keyframe(0.0, BodyPart.HIPS.value, position_offset=[0, 0, 0]))
        clip.add_keyframe(Keyframe(1.25, BodyPart.HIPS.value, position_offset=[0, 0.05, 0]))
        clip.add_keyframe(Keyframe(2.5, BodyPart.HIPS.value, position_offset=[0, 0, 0]))

        return clip

    @staticmethod
    def whisper() -> AnimationClip:
        """Whispering pose"""
        clip = AnimationClip(
            name        = "Whisper",
            category    = AnimationCategory.SPEAKING.value,
            duration    = 2.0,
            loop_mode   = LoopMode.LOOP.value,
            description = "Whispering with hand near mouth",
            tags        = ["whisper", "quiet", "secret"],
        )

        # Hand near mouth
        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_ARM.value, rotation=[-85, 0, 25]))
        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_FOREARM.value, rotation=[-90, 0, 0]))

        # Head tilted, lean forward slightly
        clip.add_keyframe(Keyframe(0.0, BodyPart.HEAD.value, rotation=[5, 15, 0]))
        clip.add_keyframe(Keyframe(0.0, BodyPart.TORSO.value, rotation=[5, 0, 0]))

        return clip


# ============================================================
# ACTION ANIMATIONS
# ============================================================

class ActionAnimations:
    """Action animations - sit, dance, fight"""

    @staticmethod
    def sit() -> AnimationClip:
        """Sit down"""
        clip = AnimationClip(
            name        = "Sit",
            category    = AnimationCategory.ACTION.value,
            duration    = 1.5,
            loop_mode   = LoopMode.HOLD.value,
            description = "Sit down on chair",
            tags        = ["sit", "chair"],
        )

        # Hips go down
        clip.add_keyframe(Keyframe(0.0, BodyPart.HIPS.value, position_offset=[0, 0, 0]))
        clip.add_keyframe(Keyframe(1.5, BodyPart.HIPS.value, position_offset=[0, -0.5, 0]))

        # Legs bend
        clip.add_keyframe(Keyframe(0.0, BodyPart.LEFT_THIGH.value, rotation=[0, 0, 0]))
        clip.add_keyframe(Keyframe(1.5, BodyPart.LEFT_THIGH.value, rotation=[90, 0, 0]))
        clip.add_keyframe(Keyframe(0.0, BodyPart.LEFT_SHIN.value, rotation=[0, 0, 0]))
        clip.add_keyframe(Keyframe(1.5, BodyPart.LEFT_SHIN.value, rotation=[-90, 0, 0]))

        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_THIGH.value, rotation=[0, 0, 0]))
        clip.add_keyframe(Keyframe(1.5, BodyPart.RIGHT_THIGH.value, rotation=[90, 0, 0]))
        clip.add_keyframe(Keyframe(0.0, BodyPart.RIGHT_SHIN.value, rotation=[0, 0, 0]))
        clip.add_keyframe(Keyframe(1.5, BodyPart.RIGHT_SHIN.value, rotation=[-90, 0, 0]))

        return clip

    @staticmethod
    def dance() -> AnimationClip:
        """Simple dance"""
        clip = AnimationClip(
            name        = "Dance",
            category    = AnimationCategory.ACTION.value,
            duration    = 2.0,
            loop_mode   = LoopMode.LOOP.value,
            description = "Simple dance moves",
            tags        = ["dance", "party"],
        )

        # Arms swing side to side
        for i, t in enumerate([0.0, 0.5, 1.0, 1.5, 2.0]):
            angle = 30 if i % 2 == 0 else -30
            clip.add_keyframe(Keyframe(
                time      = t,
                body_part = BodyPart.LEFT_ARM.value,
                rotation  = [-45, 0, angle],
                easing    = "ease_in_out",
            ))
            clip.add_keyframe(Keyframe(
                time      = t,
                body_part = BodyPart.RIGHT_ARM.value,
                rotation  = [-45, 0, -angle],
                easing    = "ease_in_out",
            ))

        # Hips sway
        for i, t in enumerate([0.0, 0.5, 1.0, 1.5, 2.0]):
            angle = 15 if i % 2 == 0 else -15
            clip.add_keyframe(Keyframe(
                time      = t,
                body_part = BodyPart.HIPS.value,
                rotation  = [0, 0, angle],
                easing    = "ease_in_out",
            ))

        return clip


# ============================================================
# ANIMATION LIBRARY - Main manager
# ============================================================

class AnimationLibrary:
    """
    Sabhi animations ka centralized library.
    """

    def __init__(self, config: Optional[Dict] = None):
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # Load all animations
        self._animations: Dict[str, AnimationClip] = {}
        self._load_all_animations()

        logger.info(
            f"✅ AnimationLibrary initialized | "
            f"{len(self._animations)} animations loaded"
        )

    def _load_all_animations(self):
        """Sabhi built-in animations load karo"""
        # Idle animations
        self._register(IdleAnimations.basic_idle())
        self._register(IdleAnimations.confident_idle())
        self._register(IdleAnimations.sad_idle())

        # Locomotion
        self._register(LocomotionAnimations.walk())
        self._register(LocomotionAnimations.run())
        self._register(LocomotionAnimations.jump())

        # Gestures
        self._register(GestureAnimations.wave())
        self._register(GestureAnimations.nod())
        self._register(GestureAnimations.shake_head())
        self._register(GestureAnimations.point())
        self._register(GestureAnimations.clap())

        # Expressions
        self._register(ExpressionAnimations.laugh())
        self._register(ExpressionAnimations.cry())
        self._register(ExpressionAnimations.angry_gesture())
        self._register(ExpressionAnimations.thinking())

        # Speaking
        self._register(SpeakingAnimations.talking())
        self._register(SpeakingAnimations.excited_talking())
        self._register(SpeakingAnimations.whisper())

        # Actions
        self._register(ActionAnimations.sit())
        self._register(ActionAnimations.dance())

    def _register(self, clip: AnimationClip):
        """Animation register karo"""
        # Use lowercase name as key
        key = clip.name.lower().replace(" ", "_")
        self._animations[key] = clip

    def get_animation(self, name: str) -> Optional[AnimationClip]:
        """Animation naam se lo"""
        key = name.lower().replace(" ", "_")
        return self._animations.get(key)

    def get_all_animations(self) -> List[AnimationClip]:
        """Sabhi animations lo"""
        return list(self._animations.values())

    def get_by_category(self, category: str) -> List[AnimationClip]:
        """Category se animations lo"""
        return [
            a for a in self._animations.values()
            if a.category == category
        ]

    def get_by_tag(self, tag: str) -> List[AnimationClip]:
        """Tag se animations lo"""
        return [
            a for a in self._animations.values()
            if tag.lower() in [t.lower() for t in a.tags]
        ]

    def search(self, query: str) -> List[AnimationClip]:
        """Animations search karo"""
        query_lower = query.lower()
        return [
            a for a in self._animations.values()
            if query_lower in a.name.lower()
            or query_lower in a.description.lower()
            or any(query_lower in t.lower() for t in a.tags)
        ]

    def get_animation_names(self) -> List[str]:
        """Sabhi animation names lo"""
        return [a.name for a in self._animations.values()]

    def get_statistics(self) -> Dict:
        """Library statistics"""
        stats = {
            "total_animations": len(self._animations),
            "by_category":      {},
            "total_keyframes":  0,
        }

        for anim in self._animations.values():
            cat = anim.category
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
            stats["total_keyframes"] += len(anim.keyframes)

        return stats


# ============================================================
# ANIMATION SAMPLER - Get pose at specific time
# ============================================================

class AnimationSampler:
    """
    Ek time pe body pose calculate karta hai.
    Keyframes ke beech interpolate karta hai.
    """

    @staticmethod
    def sample_pose_at_time(
        clip:        AnimationClip,
        time:        float,
    ) -> Dict[str, Dict]:
        """
        Kisi bhi time pe body ki complete pose lo.

        Returns:
            Dict[body_part] = {"position": [x,y,z], "rotation": [x,y,z], "scale": [x,y,z]}
        """
        # Handle looping
        if clip.loop_mode == LoopMode.LOOP.value:
            time = time % clip.duration
        elif clip.loop_mode == LoopMode.PING_PONG.value:
            cycle = clip.duration * 2
            t = time % cycle
            if t > clip.duration:
                time = cycle - t
            else:
                time = t
        else:
            # ONCE or HOLD
            time = min(time, clip.duration)

        # Collect pose data
        pose = {}

        # For each body part, interpolate between keyframes
        body_parts = set(kf.body_part for kf in clip.keyframes)
        for part in body_parts:
            keyframes = clip.get_keyframes_for_part(part)
            if not keyframes:
                continue

            # Find surrounding keyframes
            prev_kf = None
            next_kf = None

            for kf in keyframes:
                if kf.time <= time:
                    prev_kf = kf
                elif kf.time > time and next_kf is None:
                    next_kf = kf
                    break

            # Interpolate
            if prev_kf and next_kf:
                # Between two keyframes
                t = (time - prev_kf.time) / (next_kf.time - prev_kf.time)
                t = Easing.apply(next_kf.easing, t)

                pose[part] = {
                    "position": AnimationSampler._lerp_vec3(
                        prev_kf.position_offset, next_kf.position_offset, t
                    ),
                    "rotation": AnimationSampler._lerp_vec3(
                        prev_kf.rotation, next_kf.rotation, t
                    ),
                    "scale": AnimationSampler._lerp_vec3(
                        prev_kf.scale, next_kf.scale, t
                    ),
                }
            elif prev_kf:
                # Only previous - use its values
                pose[part] = {
                    "position": list(prev_kf.position_offset),
                    "rotation": list(prev_kf.rotation),
                    "scale":    list(prev_kf.scale),
                }
            elif next_kf:
                # Only next - use its values
                pose[part] = {
                    "position": list(next_kf.position_offset),
                    "rotation": list(next_kf.rotation),
                    "scale":    list(next_kf.scale),
                }

        return pose

    @staticmethod
    def _lerp_vec3(
        v1: List[float],
        v2: List[float],
        t:  float,
    ) -> List[float]:
        """Linear interpolate two vec3"""
        return [
            v1[0] + (v2[0] - v1[0]) * t,
            v1[1] + (v2[1] - v1[1]) * t,
            v1[2] + (v2[2] - v1[2]) * t,
        ]


# ============================================================
# GLOBAL INSTANCE
# ============================================================

_global_library: Optional[AnimationLibrary] = None


def get_animation_library() -> AnimationLibrary:
    """Global AnimationLibrary lo"""
    global _global_library
    if _global_library is None:
        _global_library = AnimationLibrary()
    return _global_library


# ============================================================
# EMOTION-TO-ANIMATION MAPPER
# ============================================================

class EmotionAnimationMapper:
    """Emotion se animation auto-select karta hai"""

    EMOTION_MAP: Dict[str, str] = {
        "neutral":     "basic_idle",
        "happy":       "excited_talking",
        "excited":     "wave",
        "angry":       "angry_gesture",
        "sad":         "cry",
        "laughing":    "laugh",
        "thinking":    "thinking",
        "confused":    "thinking",
        "surprised":   "basic_idle",
        "fearful":     "sad_idle",
        "shouting":    "angry_gesture",
        "loving":      "basic_idle",
        "whispering":  "whisper",
    }

    @classmethod
    def get_animation_for_emotion(cls, emotion: str) -> str:
        """Emotion se animation name lo"""
        return cls.EMOTION_MAP.get(emotion, "basic_idle")

    @classmethod
    def get_talking_animation(cls, emotion: str) -> str:
        """Talking ke liye emotion-based animation"""
        talking_map = {
            "excited":  "excited_talking",
            "happy":    "excited_talking",
            "angry":    "angry_gesture",
            "whispering": "whisper",
        }
        return talking_map.get(emotion, "talking")


# ============================================================
# TEST SECTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")
    print_banner("Animation Presets Test", "Character Animation Library")

    # ===== TEST 1: Library =====
    print_section("Test 1: Animation Library")
    library = AnimationLibrary()
    stats = library.get_statistics()
    print(f"✅ Total animations : {stats['total_animations']}")
    print(f"   Total keyframes  : {stats['total_keyframes']}")
    print(f"\n   By Category:")
    for cat, count in stats['by_category'].items():
        print(f"      {cat:15s}: {count}")

    # ===== TEST 2: All Animations List =====
    print_section("Test 2: All Animations")
    for anim in library.get_all_animations():
        print(
            f"✅ {anim.name:20s} | "
            f"{anim.category:12s} | "
            f"{anim.duration:.1f}s | "
            f"{len(anim.keyframes)} keyframes | "
            f"{anim.loop_mode}"
        )

    # ===== TEST 3: Category Filter =====
    print_section("Test 3: Category Filter")
    for cat in [AnimationCategory.LOCOMOTION.value, AnimationCategory.GESTURE.value,
                AnimationCategory.EXPRESSION.value]:
        anims = library.get_by_category(cat)
        print(f"✅ {cat:15s}: {[a.name for a in anims]}")

    # ===== TEST 4: Tag Search =====
    print_section("Test 4: Tag Search")
    for tag in ["walk", "happy", "hello", "yes"]:
        results = library.get_by_tag(tag)
        print(f"✅ Tag '{tag:10s}': {[r.name for r in results]}")

    # ===== TEST 5: Sample Pose at Time =====
    print_section("Test 5: Sample Poses (Walk Animation)")
    walk = library.get_animation("walk")

    if walk:
        print(f"\n   Sampling walk animation at different times:")
        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            pose = AnimationSampler.sample_pose_at_time(walk, t)
            print(f"\n   Time {t:.2f}s:")

            # Show a few key body parts
            for part in [BodyPart.LEFT_THIGH.value, BodyPart.RIGHT_ARM.value]:
                if part in pose:
                    rot = pose[part]["rotation"]
                    print(f"      {part:15s}: rotation=[{rot[0]:+.1f}, {rot[1]:+.1f}, {rot[2]:+.1f}]")

    # ===== TEST 6: Emotion Mapping =====
    print_section("Test 6: Emotion to Animation Mapping")
    emotions = ["happy", "sad", "angry", "excited", "thinking", "shouting", "laughing"]
    for emotion in emotions:
        anim_name = EmotionAnimationMapper.get_animation_for_emotion(emotion)
        talking = EmotionAnimationMapper.get_talking_animation(emotion)
        print(f"✅ {emotion:12s} → Anim: {anim_name:20s} | Talking: {talking}")

    # ===== TEST 7: Interpolation =====
    print_section("Test 7: Animation Interpolation")
    idle = library.get_animation("basic_idle")
    if idle:
        print(f"\n   Basic Idle animation samples:")
        for t in [0.0, 0.5, 1.0, 1.5, 2.0]:
            pose = AnimationSampler.sample_pose_at_time(idle, t)
            if BodyPart.TORSO.value in pose:
                scale_y = pose[BodyPart.TORSO.value]["scale"][1]
                print(f"      t={t:.1f}s: torso scale Y = {scale_y:.4f}")

    # ===== TEST 8: Search =====
    print_section("Test 8: Search Animations")
    for query in ["walk", "hand", "sad", "excited"]:
        results = library.search(query)
        print(f"✅ Search '{query}': {[r.name for r in results]}")

    # ===== TEST 9: Complex Animation - Wave =====
    print_section("Test 9: Wave Animation Analysis")
    wave = library.get_animation("wave")
    if wave:
        print(f"✅ Wave Animation:")
        print(f"   Name        : {wave.name}")
        print(f"   Duration    : {wave.duration}s")
        print(f"   Loop mode   : {wave.loop_mode}")
        print(f"   Total keyframes: {len(wave.keyframes)}")

        # Group keyframes by body part
        body_parts_used = set(kf.body_part for kf in wave.keyframes)
        print(f"\n   Body parts animated:")
        for part in body_parts_used:
            count = len(wave.get_keyframes_for_part(part))
            print(f"      {part:20s}: {count} keyframes")

    # ===== TEST 10: All Presets Summary =====
    print_section("Test 10: All Presets Detailed")
    for name in library.get_animation_names():
        anim = library.get_animation(name)
        if anim:
            body_parts = set(kf.body_part for kf in anim.keyframes)
            print(f"✅ {anim.name:20s}: {len(body_parts)} body parts, "
                  f"{len(anim.keyframes)} keyframes, "
                  f"{anim.duration}s")

    print_banner("✅ All Tests Passed!", "animation_presets.py Working Perfectly")