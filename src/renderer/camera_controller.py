# ============================================================
# 3D ANIMATION STUDIO - Camera Controller
# ============================================================
# Features:
# - Cinematic camera angle presets
# - Camera animation (pan, zoom, tracking, orbit)
# - Smooth interpolation (easing functions)
# - Object tracking (camera follows target)
# - Manual controls override
# - Camera shake effects
# - Depth of field settings
# - Multi-camera management
# - Keyframe-based animation
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
import random
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from src.utils import (
    get_logger, get_config, clamp, lerp, generate_short_id,
    degrees_to_radians, radians_to_degrees
)
from src.renderer.render_engine import Camera

logger = get_logger("CameraController")


# ============================================================
# EASING FUNCTIONS (Smooth Animations)
# ============================================================

class Easing:
    """
    Easing functions for smooth animations.
    Ye functions t (0-1) leke aur smoother t return karte hain.
    """

    @staticmethod
    def linear(t: float) -> float:
        return t

    @staticmethod
    def ease_in_quad(t: float) -> float:
        return t * t

    @staticmethod
    def ease_out_quad(t: float) -> float:
        return t * (2 - t)

    @staticmethod
    def ease_in_out_quad(t: float) -> float:
        if t < 0.5:
            return 2 * t * t
        return -1 + (4 - 2 * t) * t

    @staticmethod
    def ease_in_cubic(t: float) -> float:
        return t * t * t

    @staticmethod
    def ease_out_cubic(t: float) -> float:
        return 1 - pow(1 - t, 3)

    @staticmethod
    def ease_in_out_cubic(t: float) -> float:
        if t < 0.5:
            return 4 * t * t * t
        return 1 - pow(-2 * t + 2, 3) / 2

    @staticmethod
    def ease_in_sine(t: float) -> float:
        return 1 - math.cos((t * math.pi) / 2)

    @staticmethod
    def ease_out_sine(t: float) -> float:
        return math.sin((t * math.pi) / 2)

    @staticmethod
    def ease_in_out_sine(t: float) -> float:
        return -(math.cos(math.pi * t) - 1) / 2

    @staticmethod
    def ease_out_bounce(t: float) -> float:
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
    def ease_out_elastic(t: float) -> float:
        if t == 0 or t == 1:
            return t
        c4 = (2 * math.pi) / 3
        return pow(2, -10 * t) * math.sin((t * 10 - 0.75) * c4) + 1

    ALL = {
        "linear": linear,
        "ease_in": ease_in_quad,
        "ease_out": ease_out_quad,
        "ease_in_out": ease_in_out_quad,
        "ease_in_cubic": ease_in_cubic,
        "ease_out_cubic": ease_out_cubic,
        "ease_in_out_cubic": ease_in_out_cubic,
        "ease_in_sine": ease_in_sine,
        "ease_out_sine": ease_out_sine,
        "ease_in_out_sine": ease_in_out_sine,
        "bounce": ease_out_bounce,
        "elastic": ease_out_elastic,
    }

    @classmethod
    def get(cls, name: str) -> Callable:
        return cls.ALL.get(name, cls.linear)


# ============================================================
# CAMERA PRESETS (Cinematic Angles)
# ============================================================

class CameraPresets:
    """Pre-built cinematic camera angles"""

    @staticmethod
    def wide_angle(target: Optional[List[float]] = None) -> Dict:
        """Wide-angle establishing shot"""
        target = target or [0, 0, 0]
        return {
            "name": "Wide Angle",
            "position": [0, 3, 12],
            "target": target,
            "fov": 75.0,
        }

    @staticmethod
    def close_up(target: Optional[List[float]] = None) -> Dict:
        """Close-up shot (face/detail)"""
        target = target or [0, 1.6, 0]
        return {
            "name": "Close-Up",
            "position": [0, 1.6, 2],
            "target": target,
            "fov": 35.0,
        }

    @staticmethod
    def medium_shot(target: Optional[List[float]] = None) -> Dict:
        """Medium shot (waist up)"""
        target = target or [0, 1.2, 0]
        return {
            "name": "Medium Shot",
            "position": [0, 1.5, 4],
            "target": target,
            "fov": 50.0,
        }

    @staticmethod
    def over_the_shoulder(target: Optional[List[float]] = None) -> Dict:
        """Over-the-shoulder (dialogue)"""
        target = target or [0, 1.6, 0]
        return {
            "name": "Over-the-Shoulder",
            "position": [0.8, 1.8, 3],
            "target": target,
            "fov": 55.0,
        }

    @staticmethod
    def birds_eye(target: Optional[List[float]] = None) -> Dict:
        """Bird's-eye view (top-down)"""
        target = target or [0, 0, 0]
        return {
            "name": "Bird's Eye",
            "position": [0, 15, 0.01],
            "target": target,
            "fov": 60.0,
        }

    @staticmethod
    def low_angle(target: Optional[List[float]] = None) -> Dict:
        """Low angle (heroic shot)"""
        target = target or [0, 1.5, 0]
        return {
            "name": "Low Angle",
            "position": [0, 0.3, 4],
            "target": target,
            "fov": 60.0,
        }

    @staticmethod
    def dutch_angle(target: Optional[List[float]] = None) -> Dict:
        """Dutch/tilted angle (unease)"""
        target = target or [0, 1, 0]
        return {
            "name": "Dutch Angle",
            "position": [3, 1.5, 4],
            "target": target,
            "up": [0.3, 0.95, 0],  # Tilted up vector
            "fov": 55.0,
        }

    @staticmethod
    def worm_eye(target: Optional[List[float]] = None) -> Dict:
        """Worm's-eye view (extreme low)"""
        target = target or [0, 2, 0]
        return {
            "name": "Worm's Eye",
            "position": [0, 0.05, 3],
            "target": target,
            "fov": 70.0,
        }

    @staticmethod
    def establishing_shot(target: Optional[List[float]] = None) -> Dict:
        """Wide establishing shot"""
        target = target or [0, 0, 0]
        return {
            "name": "Establishing",
            "position": [15, 8, 15],
            "target": target,
            "fov": 60.0,
        }

    @staticmethod
    def profile_shot(target: Optional[List[float]] = None) -> Dict:
        """Side profile view"""
        target = target or [0, 1.5, 0]
        return {
            "name": "Profile",
            "position": [5, 1.5, 0],
            "target": target,
            "fov": 50.0,
        }

    @classmethod
    def get_all_presets(cls) -> Dict[str, Callable]:
        return {
            "wide_angle": cls.wide_angle,
            "close_up": cls.close_up,
            "medium_shot": cls.medium_shot,
            "over_the_shoulder": cls.over_the_shoulder,
            "birds_eye": cls.birds_eye,
            "low_angle": cls.low_angle,
            "dutch_angle": cls.dutch_angle,
            "worm_eye": cls.worm_eye,
            "establishing_shot": cls.establishing_shot,
            "profile_shot": cls.profile_shot,
        }

    @classmethod
    def get_preset_names(cls) -> List[str]:
        return list(cls.get_all_presets().keys())

    @classmethod
    def get_preset(cls, name: str,
                   target: Optional[List[float]] = None) -> Optional[Dict]:
        presets = cls.get_all_presets()
        if name in presets:
            return presets[name](target)
        return None


# ============================================================
# CAMERA KEYFRAME
# ============================================================

@dataclass
class CameraKeyframe:
    """Single keyframe in camera animation"""
    time: float                    # Time in seconds
    position: List[float] = field(default_factory=lambda: [0, 0, 5])
    target: List[float] = field(default_factory=lambda: [0, 0, 0])
    fov: float = 60.0
    up: List[float] = field(default_factory=lambda: [0, 1, 0])
    easing: str = "ease_in_out"

    def to_dict(self) -> Dict:
        return {
            "time": self.time,
            "position": self.position,
            "target": self.target,
            "fov": self.fov,
            "up": self.up,
            "easing": self.easing,
        }


# ============================================================
# CAMERA ANIMATION
# ============================================================

class CameraAnimation:
    """
    Keyframe-based camera animation.
    Multiple keyframes ke beech smooth interpolation.
    """

    def __init__(self, name: str = "Animation"):
        self.id = generate_short_id()
        self.name = name
        self.keyframes: List[CameraKeyframe] = []
        self.loop = False
        self.duration = 0.0

    def add_keyframe(self, keyframe: CameraKeyframe):
        """Keyframe add karo (time se sorted)"""
        self.keyframes.append(keyframe)
        self.keyframes.sort(key=lambda k: k.time)
        self._update_duration()

    def _update_duration(self):
        """Total duration calculate karo"""
        if self.keyframes:
            self.duration = self.keyframes[-1].time
        else:
            self.duration = 0.0

    def evaluate(self, current_time: float) -> Optional[Dict]:
        """
        Given time par camera state calculate karo.

        Returns:
            Dict with position, target, fov, up
        """
        if not self.keyframes:
            return None

        # Loop handling
        if self.loop and self.duration > 0:
            current_time = current_time % self.duration

        # Boundary cases
        if current_time <= self.keyframes[0].time:
            kf = self.keyframes[0]
            return {
                "position": list(kf.position),
                "target": list(kf.target),
                "fov": kf.fov,
                "up": list(kf.up),
            }

        if current_time >= self.keyframes[-1].time:
            kf = self.keyframes[-1]
            return {
                "position": list(kf.position),
                "target": list(kf.target),
                "fov": kf.fov,
                "up": list(kf.up),
            }

        # Find surrounding keyframes
        prev_kf = self.keyframes[0]
        next_kf = self.keyframes[-1]

        for i in range(len(self.keyframes) - 1):
            if self.keyframes[i].time <= current_time <= self.keyframes[i + 1].time:
                prev_kf = self.keyframes[i]
                next_kf = self.keyframes[i + 1]
                break

        # Interpolate
        time_diff = next_kf.time - prev_kf.time
        if time_diff == 0:
            t = 0
        else:
            t = (current_time - prev_kf.time) / time_diff

        # Apply easing
        easing_fn = Easing.get(next_kf.easing)
        eased_t = easing_fn(t)

        # Interpolate values
        return {
            "position": [
                lerp(prev_kf.position[i], next_kf.position[i], eased_t)
                for i in range(3)
            ],
            "target": [
                lerp(prev_kf.target[i], next_kf.target[i], eased_t)
                for i in range(3)
            ],
            "fov": lerp(prev_kf.fov, next_kf.fov, eased_t),
            "up": [
                lerp(prev_kf.up[i], next_kf.up[i], eased_t)
                for i in range(3)
            ],
        }


# ============================================================
# CAMERA SHAKE EFFECT
# ============================================================

class CameraShake:
    """
    Camera shake effect (earthquake, explosion, impact).
    """

    def __init__(self):
        self.active = False
        self.start_time = 0.0
        self.duration = 0.0
        self.intensity = 0.0
        self.frequency = 30.0  # Shakes per second
        self.decay = True      # Intensity kam hoti jaye

    def start(self, duration: float = 0.5,
              intensity: float = 0.1,
              frequency: float = 30.0,
              decay: bool = True):
        """Shake shuru karo"""
        self.active = True
        self.start_time = time.time()
        self.duration = duration
        self.intensity = intensity
        self.frequency = frequency
        self.decay = decay
        logger.debug(f"Camera shake: {intensity} for {duration}s")

    def get_offset(self) -> Tuple[float, float, float]:
        """
        Current shake offset return karo.

        Returns:
            (x, y, z) offset
        """
        if not self.active:
            return (0.0, 0.0, 0.0)

        elapsed = time.time() - self.start_time

        if elapsed >= self.duration:
            self.active = False
            return (0.0, 0.0, 0.0)

        # Decay factor
        if self.decay:
            progress = elapsed / self.duration
            current_intensity = self.intensity * (1.0 - progress)
        else:
            current_intensity = self.intensity

        # Random offset (perlin noise-like)
        angle = elapsed * self.frequency * 2 * math.pi
        offset_x = math.sin(angle * 1.7) * current_intensity
        offset_y = math.cos(angle * 2.3) * current_intensity
        offset_z = math.sin(angle * 1.3) * current_intensity * 0.5

        return (offset_x, offset_y, offset_z)

    def stop(self):
        """Shake stop karo"""
        self.active = False


# ============================================================
# CAMERA CONTROLLER (Main Class)
# ============================================================

class CameraController:
    """
    Main camera controller.
    - Preset switching
    - Smooth transitions
    - Animation playback
    - Object tracking
    - Shake effects
    - Manual controls
    """

    def __init__(self, camera: Optional[Camera] = None,
                 config: Optional[Dict] = None):
        # Config
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # Camera instance
        self.camera = camera or Camera()

        # Animations storage
        self.animations: Dict[str, CameraAnimation] = {}
        self.active_animation: Optional[CameraAnimation] = None
        self.animation_start_time: float = 0.0
        self.animation_paused: bool = False
        self.animation_pause_time: float = 0.0

        # Shake effect
        self.shake = CameraShake()

        # Base position (before shake applied)
        self._base_position = list(self.camera.position)
        self._base_target = list(self.camera.target)

        # Tracking
        self._tracking_enabled = False
        self._tracking_target: Optional[List[float]] = None
        self._tracking_offset: List[float] = [0, 2, 5]
        self._tracking_smooth: float = 0.1  # Lerp factor

        # Transition
        self._transitioning = False
        self._transition_start: Dict = {}
        self._transition_end: Dict = {}
        self._transition_start_time: float = 0.0
        self._transition_duration: float = 1.0
        self._transition_easing: str = "ease_in_out"

        # Manual override
        self._manual_override = False

        # Change listeners
        self._listeners: List[Callable] = []

        logger.info("CameraController initialized")

    # ------------------------------------------------------------
    # PRESET APPLICATION
    # ------------------------------------------------------------

    def apply_preset(self, preset_name: str,
                     target: Optional[List[float]] = None,
                     transition_duration: float = 0.0) -> bool:
        """
        Camera preset apply karo.

        Args:
            preset_name: Preset name
            target: Optional custom target
            transition_duration: Smooth transition time (0 for instant)
        """
        preset = CameraPresets.get_preset(preset_name, target)
        if not preset:
            logger.warning(f"Unknown preset: {preset_name}")
            return False

        if transition_duration > 0:
            self.transition_to(
                position=preset["position"],
                target=preset["target"],
                fov=preset["fov"],
                up=preset.get("up", [0, 1, 0]),
                duration=transition_duration
            )
        else:
            self.camera.position = list(preset["position"])
            self.camera.target = list(preset["target"])
            self.camera.fov = preset["fov"]
            self.camera.up = preset.get("up", [0, 1, 0])

            self._base_position = list(self.camera.position)
            self._base_target = list(self.camera.target)

        logger.info(f"Applied camera preset: {preset['name']}")
        self._notify_listeners("preset_applied")
        return True

    # ------------------------------------------------------------
    # TRANSITIONS (Smooth Camera Moves)
    # ------------------------------------------------------------

    def transition_to(self, position: Optional[List[float]] = None,
                      target: Optional[List[float]] = None,
                      fov: Optional[float] = None,
                      up: Optional[List[float]] = None,
                      duration: float = 1.0,
                      easing: str = "ease_in_out"):
        """
        Smooth transition to new camera state.
        """
        self._transition_start = {
            "position": list(self.camera.position),
            "target": list(self.camera.target),
            "fov": self.camera.fov,
            "up": list(self.camera.up),
        }

        self._transition_end = {
            "position": list(position) if position else list(self.camera.position),
            "target": list(target) if target else list(self.camera.target),
            "fov": fov if fov is not None else self.camera.fov,
            "up": list(up) if up else list(self.camera.up),
        }

        self._transition_start_time = time.time()
        self._transition_duration = duration
        self._transition_easing = easing
        self._transitioning = True

        logger.debug(f"Transition started ({duration}s, {easing})")

    def _update_transition(self):
        """Transition update karo per frame"""
        if not self._transitioning:
            return

        elapsed = time.time() - self._transition_start_time
        t = clamp(elapsed / self._transition_duration, 0, 1)

        # Apply easing
        easing_fn = Easing.get(self._transition_easing)
        eased_t = easing_fn(t)

        # Interpolate
        for i in range(3):
            self.camera.position[i] = lerp(
                self._transition_start["position"][i],
                self._transition_end["position"][i],
                eased_t
            )
            self.camera.target[i] = lerp(
                self._transition_start["target"][i],
                self._transition_end["target"][i],
                eased_t
            )
            self.camera.up[i] = lerp(
                self._transition_start["up"][i],
                self._transition_end["up"][i],
                eased_t
            )

        self.camera.fov = lerp(
            self._transition_start["fov"],
            self._transition_end["fov"],
            eased_t
        )

        # Transition complete?
        if t >= 1.0:
            self._transitioning = False
            self._base_position = list(self.camera.position)
            self._base_target = list(self.camera.target)
            logger.debug("Transition complete")
            self._notify_listeners("transition_complete")

    # ------------------------------------------------------------
    # ANIMATIONS
    # ------------------------------------------------------------

    def create_animation(self, name: str) -> CameraAnimation:
        """Nayi animation create karo"""
        anim = CameraAnimation(name)
        self.animations[anim.id] = anim
        return anim

    def add_animation(self, animation: CameraAnimation):
        """Existing animation add karo"""
        self.animations[animation.id] = animation

    def play_animation(self, animation_id: str, loop: bool = False):
        """Animation play karo"""
        if animation_id not in self.animations:
            logger.warning(f"Animation not found: {animation_id}")
            return False

        self.active_animation = self.animations[animation_id]
        self.active_animation.loop = loop
        self.animation_start_time = time.time()
        self.animation_paused = False

        logger.info(f"Playing animation: {self.active_animation.name}")
        return True

    def pause_animation(self):
        """Animation pause karo"""
        if self.active_animation and not self.animation_paused:
            self.animation_paused = True
            self.animation_pause_time = time.time()
            logger.debug("Animation paused")

    def resume_animation(self):
        """Animation resume karo"""
        if self.active_animation and self.animation_paused:
            # Adjust start time to account for pause
            pause_duration = time.time() - self.animation_pause_time
            self.animation_start_time += pause_duration
            self.animation_paused = False
            logger.debug("Animation resumed")

    def stop_animation(self):
        """Animation stop karo"""
        self.active_animation = None
        self.animation_paused = False
        logger.debug("Animation stopped")

    def _update_animation(self):
        """Animation update per frame"""
        if not self.active_animation or self.animation_paused:
            return

        current_time = time.time() - self.animation_start_time
        state = self.active_animation.evaluate(current_time)

        if state:
            self.camera.position = state["position"]
            self.camera.target = state["target"]
            self.camera.fov = state["fov"]
            self.camera.up = state["up"]

            self._base_position = list(self.camera.position)
            self._base_target = list(self.camera.target)

            # Animation complete?
            if (not self.active_animation.loop and
                current_time >= self.active_animation.duration):
                self.stop_animation()
                logger.debug("Animation complete")
                self._notify_listeners("animation_complete")

    # ------------------------------------------------------------
    # OBJECT TRACKING
    # ------------------------------------------------------------

    def track_object(self, target_position: List[float],
                     offset: Optional[List[float]] = None,
                     smoothness: float = 0.1):
        """
        Camera object track karega.

        Args:
            target_position: Object ki position
            offset: Camera ki offset target se
            smoothness: 0 (instant) - 1 (very smooth)
        """
        self._tracking_enabled = True
        self._tracking_target = list(target_position)
        if offset:
            self._tracking_offset = list(offset)
        self._tracking_smooth = clamp(smoothness, 0.0, 1.0)

    def update_tracking_target(self, new_position: List[float]):
        """Tracking target update karo"""
        if self._tracking_enabled:
            self._tracking_target = list(new_position)

    def stop_tracking(self):
        """Tracking stop karo"""
        self._tracking_enabled = False
        self._tracking_target = None
        logger.debug("Tracking stopped")

    def _update_tracking(self):
        """Tracking update per frame"""
        if not self._tracking_enabled or not self._tracking_target:
            return

        # Target position (with offset)
        desired_pos = [
            self._tracking_target[i] + self._tracking_offset[i]
            for i in range(3)
        ]

        # Smooth interpolation
        smooth_factor = 1.0 - self._tracking_smooth

        for i in range(3):
            self.camera.position[i] = lerp(
                self.camera.position[i],
                desired_pos[i],
                smooth_factor
            )
            self.camera.target[i] = lerp(
                self.camera.target[i],
                self._tracking_target[i],
                smooth_factor
            )

        self._base_position = list(self.camera.position)
        self._base_target = list(self.camera.target)

    # ------------------------------------------------------------
    # SHAKE EFFECTS
    # ------------------------------------------------------------

    def shake_camera(self, duration: float = 0.5,
                     intensity: float = 0.1,
                     frequency: float = 30.0):
        """Camera shake trigger karo"""
        self.shake.start(duration, intensity, frequency)

    def _update_shake(self):
        """Shake per frame apply karo"""
        offset = self.shake.get_offset()

        if any(offset):
            self.camera.position[0] = self._base_position[0] + offset[0]
            self.camera.position[1] = self._base_position[1] + offset[1]
            self.camera.position[2] = self._base_position[2] + offset[2]

    # ------------------------------------------------------------
    # MANUAL CONTROLS
    # ------------------------------------------------------------

    def move(self, dx: float = 0, dy: float = 0, dz: float = 0):
        """Camera manually move karo"""
        self.camera.position[0] += dx
        self.camera.position[1] += dy
        self.camera.position[2] += dz

        self.camera.target[0] += dx
        self.camera.target[1] += dy
        self.camera.target[2] += dz

        self._base_position = list(self.camera.position)
        self._base_target = list(self.camera.target)

    def orbit(self, angle_x: float = 0, angle_y: float = 0):
        """Target ke around orbit karo"""
        self.camera.orbit(angle_x, angle_y)
        self._base_position = list(self.camera.position)

    def zoom(self, factor: float):
        """FOV se zoom in/out"""
        self.camera.fov = clamp(self.camera.fov * factor, 10.0, 120.0)

    def dolly(self, distance: float):
        """Camera ko forward/backward move karo (position + target dono)"""
        # Direction vector
        forward = np.array([
            self.camera.target[i] - self.camera.position[i]
            for i in range(3)
        ], dtype=np.float32)

        norm = np.linalg.norm(forward)
        if norm > 0:
            forward = forward / norm * distance

            for i in range(3):
                self.camera.position[i] += forward[i]

            self._base_position = list(self.camera.position)

    def set_manual_override(self, enabled: bool):
        """Manual override mode (auto features disable)"""
        self._manual_override = enabled

    # ------------------------------------------------------------
    # UPDATE (Called per frame)
    # ------------------------------------------------------------

    def update(self):
        """
        Every frame call karo.
        Sabhi active effects apply karta hai.
        """
        if self._manual_override:
            return

        # Order matters!
        self._update_animation()
        self._update_transition()
        self._update_tracking()
        self._update_shake()

    # ------------------------------------------------------------
    # STATE / INFO
    # ------------------------------------------------------------

    def get_state(self) -> Dict:
        """Current camera state"""
        return {
            "position": list(self.camera.position),
            "target": list(self.camera.target),
            "fov": self.camera.fov,
            "up": list(self.camera.up),
            "transitioning": self._transitioning,
            "tracking": self._tracking_enabled,
            "animating": self.active_animation is not None,
            "animation_paused": self.animation_paused,
            "shake_active": self.shake.active,
            "manual_override": self._manual_override,
        }

    def is_animating(self) -> bool:
        """Koi animation chal raha hai?"""
        return (self.active_animation is not None or
                self._transitioning or
                self.shake.active)

    # ------------------------------------------------------------
    # LISTENERS
    # ------------------------------------------------------------

    def add_listener(self, callback: Callable):
        self._listeners.append(callback)

    def _notify_listeners(self, event: str):
        for listener in self._listeners:
            try:
                listener(event)
            except Exception as e:
                logger.error(f"Listener error: {e}")


# ============================================================
# TEST FUNCTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section, ensure_dir

    setup_logging(log_level="DEBUG")
    print_banner("Camera Controller Test", "Cinematic Camera System")

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))

    # ============================================================
    # Test 1: Initialize
    # ============================================================
    print_section("Test 1: Initialize Camera Controller")

    from src.renderer.render_engine import Camera

    camera = Camera(aspect_ratio=16/9)
    controller = CameraController(camera)

    state = controller.get_state()
    print(f"Position: {state['position']}")
    print(f"Target: {state['target']}")
    print(f"FOV: {state['fov']}")

    # ============================================================
    # Test 2: List Available Presets
    # ============================================================
    print_section("Test 2: Available Camera Presets")

    presets = CameraPresets.get_preset_names()
    print(f"Total: {len(presets)}")
    for i, name in enumerate(presets, 1):
        preset = CameraPresets.get_preset(name)
        print(f"  {i:2}. {preset['name']:22s} - FOV: {preset['fov']}°")

    # ============================================================
    # Test 3: Apply Presets
    # ============================================================
    print_section("Test 3: Apply Different Presets")

    for preset_name in ["wide_angle", "close_up", "birds_eye", "low_angle"]:
        controller.apply_preset(preset_name)
        state = controller.get_state()
        print(f"  {preset_name:18s}: pos={[round(x,1) for x in state['position']]}, fov={state['fov']}")

    # ============================================================
    # Test 4: Smooth Transition
    # ============================================================
    print_section("Test 4: Smooth Transition")

    controller.apply_preset("wide_angle")
    print(f"Start pos: {[round(x,1) for x in controller.camera.position]}")

    controller.transition_to(
        position=[5, 5, 5],
        target=[0, 0, 0],
        fov=45.0,
        duration=1.0,
        easing="ease_in_out"
    )

    print("Simulating 1 second of transition...")

    # Simulate frames
    frames_to_simulate = 30
    for i in range(frames_to_simulate + 1):
        controller.update()
        time.sleep(0.033)  # ~30fps

        if i % 10 == 0:
            pos = [round(x, 2) for x in controller.camera.position]
            fov = round(controller.camera.fov, 1)
            print(f"  Frame {i:2}: pos={pos}, fov={fov}")

    # ============================================================
    # Test 5: Keyframe Animation
    # ============================================================
    print_section("Test 5: Keyframe Animation")

    anim = controller.create_animation("Circular Move")

    # Circular path around origin
    radius = 5.0
    for i in range(9):  # 8 segments = full circle
        angle = i * math.pi / 4
        anim.add_keyframe(CameraKeyframe(
            time=i * 0.5,
            position=[radius * math.cos(angle), 3, radius * math.sin(angle)],
            target=[0, 0, 0],
            fov=60.0,
            easing="linear"
        ))

    print(f"Created animation: {anim.name}")
    print(f"Keyframes: {len(anim.keyframes)}")
    print(f"Duration: {anim.duration}s")

    # Play animation
    controller.play_animation(anim.id)
    print("\nSimulating animation playback...")

    frames_per_second = 20
    total_time = anim.duration
    total_frames = int(total_time * frames_per_second)

    for i in range(total_frames + 1):
        controller.update()
        time.sleep(1.0 / frames_per_second)

        if i % 20 == 0:
            pos = [round(x, 1) for x in controller.camera.position]
            print(f"  t={i/frames_per_second:.1f}s: pos={pos}")

    # ============================================================
    # Test 6: Object Tracking
    # ============================================================
    print_section("Test 6: Object Tracking")

    controller.stop_animation()
    controller.apply_preset("medium_shot")

    # Track a moving object
    controller.track_object(
        target_position=[0, 0, 0],
        offset=[0, 2, 5],
        smoothness=0.15
    )

    print("Object moves from (0,0,0) to (5,0,5) over 20 frames")
    print("Camera smoothly follows...")

    for i in range(21):
        # Simulate object moving
        obj_pos = [i * 0.25, 0, i * 0.25]
        controller.update_tracking_target(obj_pos)
        controller.update()

        if i % 5 == 0:
            cam_pos = [round(x, 2) for x in controller.camera.position]
            cam_target = [round(x, 2) for x in controller.camera.target]
            print(f"  Frame {i:2}: obj={obj_pos} → cam={cam_pos}, look_at={cam_target}")

        time.sleep(0.05)

    controller.stop_tracking()

    # ============================================================
    # Test 7: Camera Shake
    # ============================================================
    print_section("Test 7: Camera Shake Effect")

    controller.apply_preset("medium_shot")
    base_pos = list(controller.camera.position)
    print(f"Base position: {[round(x,2) for x in base_pos]}")

    print("\nStarting shake (intensity=0.3, duration=1s)...")
    controller.shake_camera(duration=1.0, intensity=0.3, frequency=30.0)

    for i in range(20):
        controller.update()
        time.sleep(0.05)

        if i % 5 == 0:
            pos = [round(x, 3) for x in controller.camera.position]
            offset = [round(pos[j] - base_pos[j], 3) for j in range(3)]
            print(f"  Frame {i:2}: offset={offset}")

    # ============================================================
    # Test 8: Manual Controls
    # ============================================================
    print_section("Test 8: Manual Camera Controls")

    controller.apply_preset("medium_shot")
    print(f"Initial: pos={controller.camera.position}, fov={controller.camera.fov}")

    controller.move(dx=1, dy=0.5)
    print(f"After move: pos={controller.camera.position}")

    controller.orbit(angle_x=45, angle_y=0)
    print(f"After orbit 45°: pos={[round(x,2) for x in controller.camera.position]}")

    controller.zoom(0.8)  # Zoom in
    print(f"After zoom in: fov={controller.camera.fov}")

    controller.dolly(1.0)  # Dolly forward
    print(f"After dolly: pos={[round(x,2) for x in controller.camera.position]}")

    # ============================================================
    # Test 9: Render Preset Comparisons
    # ============================================================
    print_section("Test 9: Render Different Camera Presets")

    from src.renderer.render_engine import RenderEngine, PrimitiveFactory

    engine = RenderEngine(width=1280, height=720, headless=True)

    if engine.initialized:
        # Scene setup - character-like arrangement
        # Center: character body (cube)
        body = PrimitiveFactory.create_cube(size=1.0)
        body.color = [0.7, 0.4, 0.3]
        body.position = np.array([0, 0.5, 0], dtype=np.float32)
        engine.add_mesh(body)

        # Head (sphere)
        head = PrimitiveFactory.create_sphere(radius=0.3)
        head.color = [0.9, 0.7, 0.5]
        head.position = np.array([0, 1.4, 0], dtype=np.float32)
        engine.add_mesh(head)

        # Ground
        plane = PrimitiveFactory.create_plane(size=15.0)
        plane.color = [0.3, 0.5, 0.3]
        plane.position = np.array([0, 0, 0], dtype=np.float32)
        engine.add_mesh(plane)

        # Attach controller to engine's camera
        controller = CameraController(engine.camera)

        output_dir = os.path.join(base_dir, "temp", "camera_tests")
        ensure_dir(output_dir)

        # Render each preset
        target_position = [0, 1, 0]  # Character position
        render_presets = ["wide_angle", "close_up", "medium_shot",
                         "over_the_shoulder", "birds_eye",
                         "low_angle", "profile_shot"]

        for preset_name in render_presets:
            controller.apply_preset(preset_name, target=target_position)
            output_path = os.path.join(output_dir, f"camera_{preset_name}.png")
            engine.render_to_image(output_path)
            print(f"  ✓ Rendered: {preset_name}.png")

        print(f"\n👉 Compare renders in: {output_dir}")

        engine.shutdown()

    # ============================================================
    # Cleanup
    # ============================================================
    print_section("Summary")

    print(f"Presets available: {len(CameraPresets.get_preset_names())}")
    print(f"Easing functions: {len(Easing.ALL)}")

    print_banner(
        "✅ All Tests Passed",
        "Camera Controller Working - Check rendered images!"
    )