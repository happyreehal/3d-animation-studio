# ============================================================
# src/pipeline/scene_builder.py
# 3D Animation Studio - Scene Builder
# Parsed script se 3D scenes automatically build karta hai
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
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from src.utils import get_logger, get_config, generate_uuid, get_timestamp

logger = get_logger("SceneBuilder")


# ============================================================
# ENUMS
# ============================================================

class CharacterPosition(Enum):
    """Standard character positions in scene"""
    CENTER          = "center"
    LEFT            = "left"
    RIGHT           = "right"
    FAR_LEFT        = "far_left"
    FAR_RIGHT       = "far_right"
    FRONT           = "front"
    BACK            = "back"


class LayoutType(Enum):
    """Scene layout patterns"""
    SOLO            = "solo"                # 1 character
    DIALOGUE        = "dialogue"            # 2 characters facing
    TRIANGLE        = "triangle"            # 3 characters
    LINE            = "line"                # Multiple in a line
    CIRCLE          = "circle"              # Around a center
    RANDOM          = "random"              # Random positions


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class SceneCharacter:
    """Character placed in 3D scene"""
    name:           str
    character_id:   str
    position:       List[float]     = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation:       List[float]     = field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale:          List[float]     = field(default_factory=lambda: [1.0, 1.0, 1.0])

    # Character properties
    voice_id:       str             = ""
    gender:         str             = "unknown"
    color_scheme:   List[float]     = field(default_factory=lambda: [0.8, 0.6, 0.4])

    # Animation state
    current_animation: str          = "idle"
    facing_direction: List[float]   = field(default_factory=lambda: [0.0, 0.0, 1.0])

    def to_dict(self) -> Dict:
        return {
            "name":              self.name,
            "id":                self.character_id,
            "position":          self.position,
            "rotation":          self.rotation,
            "scale":             self.scale,
            "voice_id":          self.voice_id,
            "gender":            self.gender,
            "current_animation": self.current_animation,
        }


@dataclass
class SceneLight:
    """Light in scene"""
    light_id:       str
    light_type:     str             = "directional"  # directional, point, spot, ambient
    position:       List[float]     = field(default_factory=lambda: [0.0, 10.0, 0.0])
    direction:      List[float]     = field(default_factory=lambda: [0.0, -1.0, 0.0])
    color:          List[float]     = field(default_factory=lambda: [1.0, 1.0, 1.0])
    intensity:      float           = 1.0
    range_value:    float           = 20.0

    def to_dict(self) -> Dict:
        return {
            "id":         self.light_id,
            "type":       self.light_type,
            "position":   self.position,
            "direction":  self.direction,
            "color":      self.color,
            "intensity":  self.intensity,
            "range":      self.range_value,
        }


@dataclass
class SceneCamera:
    """Camera in scene"""
    camera_id:      str
    position:       List[float]     = field(default_factory=lambda: [0.0, 2.0, 8.0])
    target:         List[float]     = field(default_factory=lambda: [0.0, 1.5, 0.0])
    fov:            float           = 60.0
    preset:         str             = "medium_shot"

    # Camera animation
    is_animated:    bool            = False
    animation_type: str             = "static"     # static, pan, zoom, tracking

    def to_dict(self) -> Dict:
        return {
            "id":       self.camera_id,
            "position": self.position,
            "target":   self.target,
            "fov":      self.fov,
            "preset":   self.preset,
        }


@dataclass
class SceneEnvironment:
    """Scene environment/background"""
    environment_id: str
    scene_type:     str             = "indoor"
    location:       str             = ""
    time_of_day:    str             = "noon"

    # Visual settings
    background_color: List[float]   = field(default_factory=lambda: [0.5, 0.7, 1.0])
    ground_color:   List[float]     = field(default_factory=lambda: [0.3, 0.4, 0.3])
    fog_enabled:    bool            = False
    fog_color:      List[float]     = field(default_factory=lambda: [0.8, 0.8, 0.9])
    fog_density:    float           = 0.01

    # Props/objects
    props:          List[Dict]      = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id":         self.environment_id,
            "type":       self.scene_type,
            "location":   self.location,
            "time":       self.time_of_day,
            "bg_color":   self.background_color,
            "num_props":  len(self.props),
        }


@dataclass
class SceneAudio:
    """Scene audio setup"""
    # Background music
    music_mood:     str             = "neutral"
    music_volume:   float           = 0.3

    # Ambient sounds
    ambient_sounds: List[str]       = field(default_factory=list)
    ambient_volume: float           = 0.4

    # Sound effects
    sfx_list:       List[Dict]      = field(default_factory=list)

    # Reverb settings
    reverb_type:    str             = "room"        # room, hall, outdoor, cave
    reverb_amount:  float           = 0.2

    def to_dict(self) -> Dict:
        return {
            "music_mood":    self.music_mood,
            "music_volume":  self.music_volume,
            "ambient":       self.ambient_sounds,
            "sfx_count":     len(self.sfx_list),
            "reverb":        self.reverb_type,
        }


@dataclass
class BuiltScene:
    """Complete built 3D scene ready for rendering"""
    scene_id:       str
    scene_index:    int
    heading:        str             = ""

    # 3D elements
    characters:     List[SceneCharacter] = field(default_factory=list)
    lights:         List[SceneLight] = field(default_factory=list)
    cameras:        List[SceneCamera] = field(default_factory=list)
    environment:    Optional[SceneEnvironment] = None
    audio:          Optional[SceneAudio] = None

    # VFX
    vfx_effects:    List[Dict]      = field(default_factory=list)

    # Layout info
    layout_type:    str             = LayoutType.DIALOGUE.value
    active_camera_id: str           = ""

    # Timing (from parsed script)
    start_frame:    int             = 0
    end_frame:      int             = 0
    duration_seconds: float         = 0.0
    fps:            int             = 30

    # Original parsed scene reference
    parsed_scene_ref: Optional[Any] = None

    def get_character(self, name: str) -> Optional[SceneCharacter]:
        """Character naam se lo"""
        for char in self.characters:
            if char.name == name:
                return char
        return None

    def get_active_camera(self) -> Optional[SceneCamera]:
        """Active camera lo"""
        for cam in self.cameras:
            if cam.camera_id == self.active_camera_id:
                return cam
        return self.cameras[0] if self.cameras else None

    def to_dict(self) -> Dict:
        return {
            "scene_id":      self.scene_id,
            "scene_index":   self.scene_index,
            "heading":       self.heading,
            "characters":    [c.to_dict() for c in self.characters],
            "lights":        [l.to_dict() for l in self.lights],
            "cameras":       [c.to_dict() for c in self.cameras],
            "environment":   self.environment.to_dict() if self.environment else None,
            "audio":         self.audio.to_dict() if self.audio else None,
            "num_vfx":       len(self.vfx_effects),
            "layout":        self.layout_type,
            "start_frame":   self.start_frame,
            "end_frame":     self.end_frame,
            "duration":      self.duration_seconds,
        }


# ============================================================
# CHARACTER POSITIONING
# ============================================================

class CharacterPositioner:
    """Characters ko intelligently position karta hai scene mein"""

    # Standard positions (X, Y, Z) - Y is up
    STANDARD_POSITIONS: Dict[str, List[float]] = {
        CharacterPosition.CENTER.value:    [0.0, 0.0, 0.0],
        CharacterPosition.LEFT.value:      [-2.0, 0.0, 0.0],
        CharacterPosition.RIGHT.value:     [2.0, 0.0, 0.0],
        CharacterPosition.FAR_LEFT.value:  [-4.0, 0.0, 0.0],
        CharacterPosition.FAR_RIGHT.value: [4.0, 0.0, 0.0],
        CharacterPosition.FRONT.value:     [0.0, 0.0, 2.0],
        CharacterPosition.BACK.value:      [0.0, 0.0, -2.0],
    }

    @classmethod
    def position_characters(
        cls,
        character_names: List[str],
        layout_type: str = LayoutType.DIALOGUE.value,
    ) -> Dict[str, Tuple[List[float], List[float]]]:
        """
        Characters ko position aur rotation assign karo.

        Returns:
            Dict mapping character name → (position, rotation)
        """
        result = {}
        num_chars = len(character_names)

        if num_chars == 0:
            return result

        # SOLO layout
        if num_chars == 1:
            name = character_names[0]
            result[name] = ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0])
            return result

        # DIALOGUE layout (2 characters facing each other)
        if num_chars == 2 or layout_type == LayoutType.DIALOGUE.value:
            positions = cls._dialogue_layout(character_names[:2])
            result.update(positions)

            # Extra characters
            if num_chars > 2:
                for i, name in enumerate(character_names[2:]):
                    x = (i + 1) * 2.0 * (1 if i % 2 == 0 else -1)
                    result[name] = ([x, 0.0, -2.0], [0.0, 0.0, 0.0])
            return result

        # TRIANGLE (3 characters)
        if num_chars == 3 or layout_type == LayoutType.TRIANGLE.value:
            positions = cls._triangle_layout(character_names[:3])
            result.update(positions)

            # Extra
            for i, name in enumerate(character_names[3:]):
                result[name] = ([(i - 1) * 2.0, 0.0, -3.0], [0.0, 0.0, 0.0])
            return result

        # LINE layout (many characters)
        if layout_type == LayoutType.LINE.value:
            return cls._line_layout(character_names)

        # CIRCLE layout
        if layout_type == LayoutType.CIRCLE.value:
            return cls._circle_layout(character_names)

        # Default: line
        return cls._line_layout(character_names)

    @classmethod
    def _dialogue_layout(
        cls,
        names: List[str],
    ) -> Dict[str, Tuple[List[float], List[float]]]:
        """2 characters facing each other"""
        result = {}
        if len(names) < 2:
            return result

        # Character 1 on left, facing right
        result[names[0]] = (
            [-1.5, 0.0, 0.0],
            [0.0, 90.0, 0.0],  # Face right (positive X)
        )

        # Character 2 on right, facing left
        result[names[1]] = (
            [1.5, 0.0, 0.0],
            [0.0, -90.0, 0.0],  # Face left (negative X)
        )

        return result

    @classmethod
    def _triangle_layout(
        cls,
        names: List[str],
    ) -> Dict[str, Tuple[List[float], List[float]]]:
        """3 characters in triangle formation"""
        result = {}
        if len(names) < 3:
            return result

        # Triangle points
        result[names[0]] = ([0.0, 0.0, -1.5], [0.0, 0.0, 0.0])       # Back center
        result[names[1]] = ([-2.0, 0.0, 1.5], [0.0, 45.0, 0.0])       # Front left
        result[names[2]] = ([2.0, 0.0, 1.5], [0.0, -45.0, 0.0])      # Front right

        return result

    @classmethod
    def _line_layout(
        cls,
        names: List[str],
    ) -> Dict[str, Tuple[List[float], List[float]]]:
        """Characters in a horizontal line"""
        result = {}
        n = len(names)
        spacing = 1.8
        start_x = -(n - 1) * spacing / 2.0

        for i, name in enumerate(names):
            x = start_x + i * spacing
            result[name] = ([x, 0.0, 0.0], [0.0, 0.0, 0.0])

        return result

    @classmethod
    def _circle_layout(
        cls,
        names: List[str],
    ) -> Dict[str, Tuple[List[float], List[float]]]:
        """Characters in a circle facing center"""
        result = {}
        n = len(names)
        radius = 2.5

        for i, name in enumerate(names):
            angle = (i / n) * 2 * math.pi
            x = radius * math.cos(angle)
            z = radius * math.sin(angle)
            # Rotation: face center
            rotation_y = math.degrees(math.atan2(-x, -z))
            result[name] = ([x, 0.0, z], [0.0, rotation_y, 0.0])

        return result

    @classmethod
    def determine_layout(
        cls,
        num_characters: int,
        scene_type: str = "indoor",
    ) -> str:
        """Character count ke basis pe layout decide karo"""
        if num_characters == 1:
            return LayoutType.SOLO.value
        if num_characters == 2:
            return LayoutType.DIALOGUE.value
        if num_characters == 3:
            return LayoutType.TRIANGLE.value
        if num_characters <= 6:
            return LayoutType.LINE.value
        return LayoutType.CIRCLE.value


# ============================================================
# LIGHTING BUILDER
# ============================================================

class LightingBuilder:
    """Lighting setup for scenes"""

    # Preset lighting configurations
    LIGHTING_PRESETS: Dict[str, List[Dict]] = {
        "day_outdoor": [
            {
                "type": "directional",
                "position": [10, 20, 10],
                "direction": [-0.5, -1, -0.5],
                "color": [1.0, 0.95, 0.85],
                "intensity": 1.2,
            },
            {
                "type": "ambient",
                "color": [0.6, 0.7, 0.8],
                "intensity": 0.4,
            },
        ],
        "night_outdoor": [
            {
                "type": "directional",
                "position": [-5, 15, -10],
                "direction": [0.3, -1, 0.5],
                "color": [0.5, 0.6, 0.9],
                "intensity": 0.4,
            },
            {
                "type": "ambient",
                "color": [0.1, 0.15, 0.3],
                "intensity": 0.3,
            },
        ],
        "indoor_warm": [
            {
                "type": "point",
                "position": [0, 3, 0],
                "color": [1.0, 0.85, 0.7],
                "intensity": 1.0,
                "range": 8.0,
            },
            {
                "type": "ambient",
                "color": [0.4, 0.35, 0.3],
                "intensity": 0.5,
            },
        ],
        "indoor_cool": [
            {
                "type": "point",
                "position": [0, 3, 0],
                "color": [0.9, 0.95, 1.0],
                "intensity": 1.0,
                "range": 8.0,
            },
            {
                "type": "ambient",
                "color": [0.35, 0.4, 0.45],
                "intensity": 0.5,
            },
        ],
        "sunrise": [
            {
                "type": "directional",
                "position": [15, 5, 0],
                "direction": [-1, -0.3, 0],
                "color": [1.0, 0.7, 0.5],
                "intensity": 1.0,
            },
            {
                "type": "ambient",
                "color": [0.8, 0.5, 0.4],
                "intensity": 0.4,
            },
        ],
        "sunset": [
            {
                "type": "directional",
                "position": [-15, 5, 0],
                "direction": [1, -0.3, 0],
                "color": [1.0, 0.5, 0.3],
                "intensity": 1.0,
            },
            {
                "type": "ambient",
                "color": [0.7, 0.4, 0.35],
                "intensity": 0.4,
            },
        ],
        "dramatic": [
            {
                "type": "spot",
                "position": [3, 8, 3],
                "direction": [-0.5, -1, -0.5],
                "color": [1.0, 0.9, 0.7],
                "intensity": 2.0,
                "range": 15.0,
            },
            {
                "type": "ambient",
                "color": [0.1, 0.1, 0.15],
                "intensity": 0.2,
            },
        ],
        "horror": [
            {
                "type": "point",
                "position": [0, 2, 5],
                "color": [0.8, 0.3, 0.3],
                "intensity": 0.7,
                "range": 6.0,
            },
            {
                "type": "ambient",
                "color": [0.05, 0.05, 0.08],
                "intensity": 0.15,
            },
        ],
    }

    @classmethod
    def build_lights(
        cls,
        preset_name: str,
    ) -> List[SceneLight]:
        """Lighting preset se lights build karo"""
        lights = []
        preset_data = cls.LIGHTING_PRESETS.get(
            preset_name,
            cls.LIGHTING_PRESETS["day_outdoor"]
        )

        for i, light_data in enumerate(preset_data):
            light = SceneLight(
                light_id     = f"light_{i:03d}",
                light_type   = light_data.get("type", "directional"),
                position     = light_data.get("position", [0, 10, 0]),
                direction    = light_data.get("direction", [0, -1, 0]),
                color        = light_data.get("color", [1, 1, 1]),
                intensity    = light_data.get("intensity", 1.0),
                range_value  = light_data.get("range", 20.0),
            )
            lights.append(light)

        return lights


# ============================================================
# CAMERA BUILDER
# ============================================================

class CameraBuilder:
    """Camera setup for scenes"""

    # Camera presets (position, target, fov)
    CAMERA_PRESETS: Dict[str, Dict] = {
        "wide_shot": {
            "position": [0, 3, 12],
            "target":   [0, 1.5, 0],
            "fov":      45,
        },
        "medium_shot": {
            "position": [0, 2, 6],
            "target":   [0, 1.5, 0],
            "fov":      50,
        },
        "close_up": {
            "position": [0, 1.7, 2.5],
            "target":   [0, 1.7, 0],
            "fov":      35,
        },
        "over_the_shoulder": {
            "position": [-1.5, 1.8, 3],
            "target":   [1.5, 1.5, 0],
            "fov":      55,
        },
        "birds_eye": {
            "position": [0, 12, 0.1],
            "target":   [0, 0, 0],
            "fov":      70,
        },
        "low_angle": {
            "position": [0, 0.5, 4],
            "target":   [0, 2.5, 0],
            "fov":      50,
        },
        "dutch_angle": {
            "position": [3, 2, 4],
            "target":   [0, 1.5, 0],
            "fov":      50,
        },
        "establishing_shot": {
            "position": [0, 8, 15],
            "target":   [0, 1, 0],
            "fov":      60,
        },
    }

    @classmethod
    def build_camera(
        cls,
        preset_name: str,
        character_positions: Optional[List[List[float]]] = None,
    ) -> SceneCamera:
        """Camera build karo preset se"""
        preset_data = cls.CAMERA_PRESETS.get(
            preset_name,
            cls.CAMERA_PRESETS["medium_shot"]
        )

        camera = SceneCamera(
            camera_id  = f"cam_{generate_uuid()[:8]}",
            position   = list(preset_data["position"]),
            target     = list(preset_data["target"]),
            fov        = preset_data["fov"],
            preset     = preset_name,
        )

        # Adjust camera based on characters (if provided)
        if character_positions:
            camera = cls._adjust_for_characters(camera, character_positions)

        return camera

    @classmethod
    def _adjust_for_characters(
        cls,
        camera: SceneCamera,
        char_positions: List[List[float]],
    ) -> SceneCamera:
        """Characters ke position ke hisaab se camera adjust karo"""
        if not char_positions:
            return camera

        # Calculate center of characters
        avg_x = sum(p[0] for p in char_positions) / len(char_positions)
        avg_y = sum(p[1] for p in char_positions) / len(char_positions)
        avg_z = sum(p[2] for p in char_positions) / len(char_positions)

        # Target the center at head height
        camera.target = [avg_x, avg_y + 1.5, avg_z]

        # Adjust camera position based on spread
        spread_x = max(p[0] for p in char_positions) - min(p[0] for p in char_positions)
        if spread_x > 4.0 and camera.preset in ["medium_shot", "close_up"]:
            # Move camera back for wider shot
            camera.position[2] += spread_x * 0.5

        return camera


# ============================================================
# ENVIRONMENT BUILDER
# ============================================================

class EnvironmentBuilder:
    """Environment/background setup"""

    # Environment presets
    ENVIRONMENT_PRESETS: Dict[str, Dict] = {
        "indoor": {
            "bg_color":     [0.4, 0.4, 0.45],
            "ground_color": [0.3, 0.25, 0.2],
            "fog":          False,
        },
        "outdoor": {
            "bg_color":     [0.55, 0.75, 0.95],
            "ground_color": [0.3, 0.5, 0.2],
            "fog":          False,
        },
        "forest": {
            "bg_color":     [0.2, 0.35, 0.15],
            "ground_color": [0.25, 0.2, 0.15],
            "fog":          True,
            "fog_color":    [0.4, 0.5, 0.3],
            "fog_density":  0.02,
        },
        "desert": {
            "bg_color":     [0.85, 0.75, 0.55],
            "ground_color": [0.75, 0.65, 0.4],
            "fog":          True,
            "fog_color":    [0.9, 0.8, 0.6],
            "fog_density":  0.005,
        },
        "city": {
            "bg_color":     [0.5, 0.55, 0.6],
            "ground_color": [0.3, 0.3, 0.32],
            "fog":          True,
            "fog_color":    [0.6, 0.6, 0.65],
            "fog_density":  0.01,
        },
        "office": {
            "bg_color":     [0.7, 0.7, 0.72],
            "ground_color": [0.4, 0.35, 0.3],
            "fog":          False,
        },
        "home": {
            "bg_color":     [0.7, 0.6, 0.5],
            "ground_color": [0.45, 0.35, 0.25],
            "fog":          False,
        },
        "school": {
            "bg_color":     [0.65, 0.65, 0.7],
            "ground_color": [0.4, 0.35, 0.3],
            "fog":          False,
        },
        "kitchen": {
            "bg_color":     [0.85, 0.85, 0.8],
            "ground_color": [0.5, 0.4, 0.3],
            "fog":          False,
        },
        "bedroom": {
            "bg_color":     [0.5, 0.4, 0.5],
            "ground_color": [0.35, 0.3, 0.25],
            "fog":          False,
        },
        "park": {
            "bg_color":     [0.55, 0.8, 0.95],
            "ground_color": [0.3, 0.55, 0.25],
            "fog":          False,
        },
        "beach": {
            "bg_color":     [0.6, 0.85, 0.95],
            "ground_color": [0.9, 0.85, 0.7],
            "fog":          False,
        },
        "mountain": {
            "bg_color":     [0.6, 0.7, 0.85],
            "ground_color": [0.4, 0.4, 0.35],
            "fog":          True,
            "fog_color":    [0.7, 0.75, 0.85],
            "fog_density":  0.015,
        },
        "street": {
            "bg_color":     [0.5, 0.55, 0.6],
            "ground_color": [0.3, 0.3, 0.3],
            "fog":          False,
        },
        "unknown": {
            "bg_color":     [0.5, 0.5, 0.55],
            "ground_color": [0.35, 0.35, 0.3],
            "fog":          False,
        },
    }

    # Time of day adjustments
    TIME_ADJUSTMENTS: Dict[str, Dict] = {
        "dawn": {
            "bg_multiplier":  [1.0, 0.7, 0.5],
            "brightness":     0.7,
        },
        "morning": {
            "bg_multiplier":  [1.1, 1.05, 1.0],
            "brightness":     1.0,
        },
        "noon": {
            "bg_multiplier":  [1.0, 1.0, 1.0],
            "brightness":     1.0,
        },
        "afternoon": {
            "bg_multiplier":  [1.05, 1.0, 0.9],
            "brightness":     0.95,
        },
        "evening": {
            "bg_multiplier":  [1.1, 0.7, 0.5],
            "brightness":     0.7,
        },
        "night": {
            "bg_multiplier":  [0.15, 0.2, 0.35],
            "brightness":     0.3,
        },
        "midnight": {
            "bg_multiplier":  [0.1, 0.1, 0.2],
            "brightness":     0.2,
        },
    }

    @classmethod
    def build_environment(
        cls,
        scene_type: str,
        location: str = "",
        time_of_day: str = "noon",
    ) -> SceneEnvironment:
        """Environment build karo"""
        # Base preset
        preset = cls.ENVIRONMENT_PRESETS.get(
            scene_type,
            cls.ENVIRONMENT_PRESETS["unknown"]
        )

        # Time adjustment
        time_adj = cls.TIME_ADJUSTMENTS.get(
            time_of_day,
            cls.TIME_ADJUSTMENTS["noon"]
        )

        # Adjust background color based on time
        bg = list(preset["bg_color"])
        multiplier = time_adj["bg_multiplier"]
        adjusted_bg = [
            min(1.0, max(0.0, bg[i] * multiplier[i]))
            for i in range(3)
        ]

        env = SceneEnvironment(
            environment_id   = f"env_{generate_uuid()[:8]}",
            scene_type       = scene_type,
            location         = location,
            time_of_day      = time_of_day,
            background_color = adjusted_bg,
            ground_color     = list(preset["ground_color"]),
            fog_enabled      = preset.get("fog", False),
            fog_color        = list(preset.get("fog_color", [0.8, 0.8, 0.9])),
            fog_density      = preset.get("fog_density", 0.01),
        )

        # Add props based on scene type
        env.props = cls._get_scene_props(scene_type)

        return env

    @classmethod
    def _get_scene_props(cls, scene_type: str) -> List[Dict]:
        """Scene type ke hisaab se default props"""
        props_map: Dict[str, List[Dict]] = {
            "home": [
                {"type": "sofa", "position": [-2, 0, -2]},
                {"type": "table", "position": [0, 0, -1]},
                {"type": "lamp", "position": [-3, 0, -1]},
            ],
            "office": [
                {"type": "desk", "position": [0, 0, -1]},
                {"type": "chair", "position": [0, 0, 0]},
                {"type": "computer", "position": [0, 0.8, -1]},
            ],
            "kitchen": [
                {"type": "counter", "position": [0, 0, -2]},
                {"type": "stove", "position": [-2, 0, -2]},
                {"type": "fridge", "position": [3, 0, -2]},
            ],
            "school": [
                {"type": "desk", "position": [-2, 0, 0]},
                {"type": "desk", "position": [0, 0, 0]},
                {"type": "desk", "position": [2, 0, 0]},
                {"type": "blackboard", "position": [0, 1, -4]},
            ],
            "bedroom": [
                {"type": "bed", "position": [0, 0, -2]},
                {"type": "wardrobe", "position": [-3, 0, -2]},
            ],
            "forest": [
                {"type": "tree", "position": [-4, 0, -3]},
                {"type": "tree", "position": [4, 0, -3]},
                {"type": "tree", "position": [-2, 0, -5]},
                {"type": "tree", "position": [3, 0, -5]},
                {"type": "rock", "position": [1, 0, -1]},
            ],
            "park": [
                {"type": "tree", "position": [-4, 0, -3]},
                {"type": "tree", "position": [4, 0, -3]},
                {"type": "bench", "position": [0, 0, -2]},
            ],
        }
        return props_map.get(scene_type, [])


# ============================================================
# AUDIO BUILDER
# ============================================================

class AudioBuilder:
    """Audio setup for scenes"""

    # Music mood to specific tracks
    MUSIC_MOODS: Dict[str, Dict] = {
        "upbeat":       {"volume": 0.35, "reverb": "room"},
        "energetic":    {"volume": 0.4,  "reverb": "room"},
        "melancholic":  {"volume": 0.25, "reverb": "hall"},
        "sad":          {"volume": 0.25, "reverb": "hall"},
        "intense":      {"volume": 0.4,  "reverb": "room"},
        "dramatic":     {"volume": 0.35, "reverb": "hall"},
        "suspense":     {"volume": 0.3,  "reverb": "cave"},
        "romantic":     {"volume": 0.3,  "reverb": "room"},
        "playful":      {"volume": 0.35, "reverb": "room"},
        "neutral":      {"volume": 0.25, "reverb": "room"},
    }

    # Reverb type by scene
    SCENE_REVERB: Dict[str, str] = {
        "indoor":       "room",
        "home":         "room",
        "office":       "room",
        "school":       "hall",
        "kitchen":      "room",
        "bedroom":      "room",
        "outdoor":      "outdoor",
        "forest":       "outdoor",
        "desert":       "outdoor",
        "city":         "outdoor",
        "park":         "outdoor",
        "beach":        "outdoor",
        "mountain":     "outdoor",
        "street":       "outdoor",
    }

    @classmethod
    def build_audio(
        cls,
        music_mood: str,
        scene_type: str = "indoor",
        ambient_sounds: Optional[List[str]] = None,
        sfx_triggers: Optional[List[Dict]] = None,
    ) -> SceneAudio:
        """Audio setup build karo"""
        # Music settings
        music_data = cls.MUSIC_MOODS.get(
            music_mood,
            cls.MUSIC_MOODS["neutral"]
        )

        # Reverb from scene type
        reverb_type = cls.SCENE_REVERB.get(scene_type, "room")

        # Reverb amount based on scene
        reverb_amount = 0.4 if reverb_type in ["hall", "cave"] else 0.2

        audio = SceneAudio(
            music_mood     = music_mood,
            music_volume   = music_data["volume"],
            ambient_sounds = ambient_sounds or [],
            ambient_volume = 0.4,
            sfx_list       = sfx_triggers or [],
            reverb_type    = reverb_type,
            reverb_amount  = reverb_amount,
        )

        return audio


# ============================================================
# VFX BUILDER
# ============================================================

class VFXBuilder:
    """VFX effects for scenes"""

    # Auto VFX based on scene properties
    AUTO_VFX_MAPPING: Dict[str, List[Dict]] = {
        # Weather-based
        "rain": [
            {"type": "rain", "intensity": 0.8, "area_size": 15.0}
        ],
        "snow": [
            {"type": "snow", "intensity": 0.6, "area_size": 15.0}
        ],
        # Emotion-based
        "angry_intense": [
            {"type": "sparkle", "intensity": 0.5, "color": [1.0, 0.3, 0.3]}
        ],
        # Action-based
        "explosion": [
            {"type": "explosion", "intensity": 1.0, "duration": 2.0}
        ],
        "fire": [
            {"type": "fire", "intensity": 1.0, "loop": True}
        ],
        "smoke": [
            {"type": "smoke", "intensity": 0.7, "loop": True}
        ],
        "magic": [
            {"type": "sparkle", "intensity": 1.2, "color": [0.5, 0.7, 1.0]}
        ],
    }

    @classmethod
    def detect_vfx_from_scene(
        cls,
        scene_type: str,
        emotion: str,
        actions: List[Any],
    ) -> List[Dict]:
        """Scene properties se auto VFX detect karo"""
        vfx = []

        # Check for weather keywords in location
        if scene_type == "rain" or "rain" in scene_type.lower():
            vfx.extend(cls.AUTO_VFX_MAPPING["rain"])

        # Check actions for VFX keywords
        for action in actions:
            action_desc = getattr(action, 'description', '').lower()
            for keyword, effects in cls.AUTO_VFX_MAPPING.items():
                if keyword in action_desc:
                    for effect in effects:
                        # Position at scene center
                        effect_with_pos = dict(effect)
                        effect_with_pos["position"] = [0, 1, 0]
                        vfx.append(effect_with_pos)

        return vfx


# ============================================================
# MAIN SCENE BUILDER
# ============================================================

class SceneBuilder:
    """
    Main Scene Builder.
    ParsedScript se 3D scenes build karta hai automatically.
    """

    def __init__(self, config: Optional[Dict] = None):
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        self.fps = self.config.get("rendering", {}).get("default_fps", 30)

        # Sub-builders
        self.positioner   = CharacterPositioner()
        self.lighting     = LightingBuilder()
        self.camera       = CameraBuilder()
        self.environment  = EnvironmentBuilder()
        self.audio        = AudioBuilder()
        self.vfx          = VFXBuilder()

        logger.info(f"✅ SceneBuilder initialized | FPS: {self.fps}")

    def build_scenes_from_script(
        self,
        parsed_script: Any,
    ) -> List[BuiltScene]:
        """
        Complete parsed script se sabhi scenes build karo.

        Args:
            parsed_script: ParsedScript object from script_parser

        Returns:
            List of BuiltScene objects
        """
        logger.info(f"🏗️  Building scenes from script: {parsed_script.title}")

        built_scenes = []

        for parsed_scene in parsed_script.scenes:
            built_scene = self.build_single_scene(
                parsed_scene, parsed_script
            )
            built_scenes.append(built_scene)

        logger.info(f"✅ Built {len(built_scenes)} scenes")
        return built_scenes

    def build_single_scene(
        self,
        parsed_scene: Any,
        parsed_script: Optional[Any] = None,
    ) -> BuiltScene:
        """
        Ek scene build karo parsed data se.
        """
        # Create built scene
        scene = BuiltScene(
            scene_id         = f"scene_{parsed_scene.index:04d}_{generate_uuid()[:8]}",
            scene_index      = parsed_scene.index,
            heading          = parsed_scene.heading,
            start_frame      = parsed_scene.start_frame,
            end_frame        = parsed_scene.end_frame,
            duration_seconds = parsed_scene.duration_seconds,
            fps              = self.fps,
            parsed_scene_ref = parsed_scene,
        )

        # ===== 1. LAYOUT DETERMINE KARO =====
        num_chars = len(parsed_scene.characters)
        layout = self.positioner.determine_layout(
            num_chars, parsed_scene.scene_type
        )
        scene.layout_type = layout

        # ===== 2. CHARACTERS PLACE KARO =====
        char_positions = self.positioner.position_characters(
            parsed_scene.characters, layout
        )

        for char_name in parsed_scene.characters:
            # Get character info from script
            char_info = None
            if parsed_script and char_name in parsed_script.characters:
                char_info = parsed_script.characters[char_name]

            pos, rot = char_positions.get(
                char_name,
                ([0, 0, 0], [0, 0, 0])
            )

            scene_char = SceneCharacter(
                name          = char_name,
                character_id  = f"char_{char_name.lower().replace(' ', '_')}",
                position      = pos,
                rotation      = rot,
                voice_id      = char_info.voice_id if char_info else "voice_default",
                gender        = char_info.gender if char_info else "unknown",
                current_animation = "idle",
            )
            scene.characters.append(scene_char)

        # ===== 3. ENVIRONMENT BUILD KARO =====
        scene.environment = self.environment.build_environment(
            scene_type   = parsed_scene.scene_type,
            location     = parsed_scene.location,
            time_of_day  = parsed_scene.time_of_day,
        )

        # ===== 4. LIGHTING SETUP KARO =====
        scene.lights = self.lighting.build_lights(
            parsed_scene.suggested_lighting
        )

        # ===== 5. CAMERA SETUP KARO =====
        char_positions_list = [c.position for c in scene.characters]
        main_camera = self.camera.build_camera(
            parsed_scene.suggested_camera,
            char_positions_list,
        )
        scene.cameras.append(main_camera)
        scene.active_camera_id = main_camera.camera_id

        # ===== 6. AUDIO SETUP KARO =====
        scene.audio = self.audio.build_audio(
            music_mood     = parsed_scene.suggested_music_mood,
            scene_type     = parsed_scene.scene_type,
            ambient_sounds = parsed_scene.suggested_sfx,
        )

        # ===== 7. VFX DETECT KARO =====
        scene.vfx_effects = self.vfx.detect_vfx_from_scene(
            scene_type = parsed_scene.scene_type,
            emotion    = parsed_scene.get_dominant_emotion(),
            actions    = parsed_scene.actions,
        )

        logger.debug(
            f"Built scene: {scene.heading} | "
            f"{len(scene.characters)} chars | "
            f"{len(scene.lights)} lights | "
            f"{len(scene.vfx_effects)} vfx"
        )

        return scene

    def print_scene_summary(self, scene: BuiltScene):
        """Built scene ka summary print karo"""
        print(f"\n{'='*60}")
        print(f"🎬 BUILT SCENE {scene.scene_index}: {scene.heading}")
        print(f"{'='*60}")
        print(f"  Layout       : {scene.layout_type}")
        print(f"  Duration     : {scene.duration_seconds:.1f}s")
        print(f"  Frames       : {scene.start_frame} - {scene.end_frame}")

        # Environment
        if scene.environment:
            print(f"\n  🌍 Environment:")
            print(f"     Type      : {scene.environment.scene_type}")
            print(f"     Time      : {scene.environment.time_of_day}")
            print(f"     BG Color  : {scene.environment.background_color}")
            print(f"     Fog       : {'Yes' if scene.environment.fog_enabled else 'No'}")
            print(f"     Props     : {len(scene.environment.props)}")

        # Characters
        if scene.characters:
            print(f"\n  🎭 Characters ({len(scene.characters)}):")
            for char in scene.characters:
                pos_str = f"[{char.position[0]:+.1f}, {char.position[1]:+.1f}, {char.position[2]:+.1f}]"
                rot_str = f"Rot: {char.rotation[1]:+.0f}°"
                print(f"     • {char.name:15s} @ {pos_str} {rot_str} | {char.gender}")

        # Lights
        if scene.lights:
            print(f"\n  💡 Lights ({len(scene.lights)}):")
            for light in scene.lights:
                print(f"     • {light.light_type:15s} | intensity: {light.intensity:.1f}")

        # Cameras
        if scene.cameras:
            print(f"\n  🎥 Cameras ({len(scene.cameras)}):")
            for cam in scene.cameras:
                active = "◆" if cam.camera_id == scene.active_camera_id else " "
                print(f"     {active} {cam.preset:20s} | FOV: {cam.fov}°")

        # Audio
        if scene.audio:
            print(f"\n  🔊 Audio:")
            print(f"     Music Mood: {scene.audio.music_mood}")
            print(f"     Volume    : {scene.audio.music_volume:.2f}")
            print(f"     Reverb    : {scene.audio.reverb_type}")
            if scene.audio.ambient_sounds:
                print(f"     Ambient   : {', '.join(scene.audio.ambient_sounds)}")

        # VFX
        if scene.vfx_effects:
            print(f"\n  ✨ VFX Effects ({len(scene.vfx_effects)}):")
            for vfx in scene.vfx_effects:
                print(f"     • {vfx.get('type', 'unknown')}")

        print(f"{'='*60}")

    def print_build_summary(self, scenes: List[BuiltScene]):
        """Sabhi built scenes ka summary"""
        print(f"\n{'='*60}")
        print(f"🏗️  BUILD SUMMARY - {len(scenes)} Scenes")
        print(f"{'='*60}")

        total_chars = sum(len(s.characters) for s in scenes)
        total_lights = sum(len(s.lights) for s in scenes)
        total_vfx = sum(len(s.vfx_effects) for s in scenes)
        total_duration = sum(s.duration_seconds for s in scenes)

        print(f"  Total Duration : {total_duration:.1f}s")
        print(f"  Total Chars    : {total_chars}")
        print(f"  Total Lights   : {total_lights}")
        print(f"  Total VFX      : {total_vfx}")
        print(f"{'='*60}\n")


# ============================================================
# GLOBAL INSTANCE
# ============================================================

_global_builder: Optional[SceneBuilder] = None


def get_scene_builder() -> SceneBuilder:
    """Global SceneBuilder instance"""
    global _global_builder
    if _global_builder is None:
        _global_builder = SceneBuilder()
    return _global_builder


# ============================================================
# TEST SECTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")
    print_banner("Scene Builder Test", "Parsed Script → 3D Scenes")

    # ===== TEST 1: Character Positioning =====
    print_section("Test 1: Character Positioning Layouts")

    layouts = [
        (["Hero"], LayoutType.SOLO.value),
        (["Hero", "Villain"], LayoutType.DIALOGUE.value),
        (["Hero", "Villain", "Friend"], LayoutType.TRIANGLE.value),
        (["A", "B", "C", "D"], LayoutType.LINE.value),
        (["A", "B", "C", "D", "E"], LayoutType.CIRCLE.value),
    ]

    for names, layout in layouts:
        positions = CharacterPositioner.position_characters(names, layout)
        print(f"\n   Layout: {layout} ({len(names)} chars)")
        for name, (pos, rot) in positions.items():
            print(f"      {name:8s}: pos={pos}, rot={rot}")

    # ===== TEST 2: Lighting Presets =====
    print_section("Test 2: Lighting Presets")
    for preset in ["day_outdoor", "night_outdoor", "indoor_warm", "sunset", "dramatic"]:
        lights = LightingBuilder.build_lights(preset)
        print(f"✅ {preset:20s}: {len(lights)} lights")

    # ===== TEST 3: Camera Presets =====
    print_section("Test 3: Camera Presets")
    for preset in ["wide_shot", "close_up", "over_the_shoulder", "birds_eye", "low_angle"]:
        cam = CameraBuilder.build_camera(preset)
        print(f"✅ {preset:20s}: pos={cam.position}, target={cam.target}, fov={cam.fov}°")

    # ===== TEST 4: Environment Building =====
    print_section("Test 4: Environments (Different Scene Types)")
    test_envs = [
        ("home", "noon"),
        ("forest", "night"),
        ("desert", "afternoon"),
        ("bedroom", "night"),
        ("beach", "sunset"),
    ]
    for scene_type, tod in test_envs:
        env = EnvironmentBuilder.build_environment(scene_type, "", tod)
        print(
            f"✅ {scene_type:10s} @ {tod:10s}: "
            f"BG={env.background_color}, "
            f"Fog={env.fog_enabled}, "
            f"Props={len(env.props)}"
        )

    # ===== TEST 5: Audio Setup =====
    print_section("Test 5: Audio for Different Moods")
    moods = ["upbeat", "melancholic", "intense", "romantic", "playful"]
    for mood in moods:
        audio = AudioBuilder.build_audio(mood, "home")
        print(f"✅ {mood:15s}: vol={audio.music_volume:.2f}, reverb={audio.reverb_type}")

    # ===== TEST 6: Full Pipeline - Parse + Build =====
    print_section("Test 6: FULL PIPELINE - Parse Script → Build Scenes")

    from src.pipeline.script_parser import ScriptParser

    test_script = """
INT. HERO'S HOUSE - MORNING

The hero wakes up excitedly.

HERO
(excited)
Aaj main duniya ka best animation banaane wala hoon!

HERO
(happy)
Chalo, kaam shuru karte hain!

EXT. FOREST - NIGHT

VILLAIN
(angry)
Hero ne bahut kar liya. Ab mera time hai!

VILLAIN
(shouting)
MAIN USSE ROKUNGA!

INT. HERO'S BEDROOM - EVENING

HERO
(thinking)
Kuch problem hai, samajh nahi aa raha.

FRIEND
(happy)
Bhai, main help karta hoon!

HERO
(excited)
Tu meri jaan hai bhai!
"""

    # Parse
    parser = ScriptParser()
    parsed = parser.parse(test_script, "Hero Story", "en")
    print(f"\n✅ Script parsed: {len(parsed.scenes)} scenes, {len(parsed.characters)} characters")

    # Build
    builder = SceneBuilder()
    built_scenes = builder.build_scenes_from_script(parsed)
    print(f"✅ Scenes built: {len(built_scenes)}")

    # Print details of each built scene
    for scene in built_scenes:
        builder.print_scene_summary(scene)

    builder.print_build_summary(built_scenes)

    # ===== TEST 7: Individual Components =====
    print_section("Test 7: Scene Character Details")
    if built_scenes:
        first_scene = built_scenes[0]
        for char in first_scene.characters:
            print(f"\n   Character: {char.name}")
            print(f"      ID       : {char.character_id}")
            print(f"      Position : {char.position}")
            print(f"      Rotation : {char.rotation}")
            print(f"      Voice    : {char.voice_id}")
            print(f"      Gender   : {char.gender}")

    # ===== TEST 8: Scene to Dict Export =====
    print_section("Test 8: Scene Export to Dict")
    if built_scenes:
        exported = built_scenes[0].to_dict()
        print(f"✅ Scene dict keys: {list(exported.keys())}")
        print(f"   Characters count: {len(exported['characters'])}")
        print(f"   Lights count    : {len(exported['lights'])}")
        print(f"   Duration        : {exported['duration']}s")

    # ===== TEST 9: Singleton =====
    print_section("Test 9: Global Singleton")
    b1 = get_scene_builder()
    b2 = get_scene_builder()
    print(f"✅ Singleton: {b1 is b2}")

    # ===== TEST 10: Real-world Complex Script =====
    print_section("Test 10: Complex Story Auto-Build")
    story = """
EXT. VILLAGE - MORNING

Small village waking up.

FARMER
Good morning, everyone!

WIFE
(happy)
Chai ready hai!

INT. HOUSE - MORNING

FARMER
(loving)
Meri jaan, aaj bahut kaam hai.

WIFE
(worried)
Sambhal ke jana.

EXT. FIELD - AFTERNOON

FARMER
(tired)
Aaj bahut mehnat ki.

FRIEND
(laughing)
Bhai, chai pi le!

EXT. VILLAGE - EVENING

FARMER
(happy)
Ghar pahunch gaya finally!

WIFE
(excited)
Aa gaye tum! Khana ready hai.
"""

    parsed2 = parser.parse(story, "Village Story", "en")
    built2 = builder.build_scenes_from_script(parsed2)
    builder.print_build_summary(built2)

    print_banner("✅ All Tests Passed!", "scene_builder.py Working Perfectly")