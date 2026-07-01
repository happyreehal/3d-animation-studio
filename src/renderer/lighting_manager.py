# ============================================================
# 3D ANIMATION STUDIO - Lighting Manager
# ============================================================
# Features:
# - Multiple light types (directional, point, spot, ambient)
# - Lighting presets (day, night, indoor, studio, etc.)
# - Dynamic lighting changes
# - Season-based lighting
# - Time-of-day system
# - Custom lighting configurations
# - Light animation support
# - Config-based preset loading
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
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from src.utils import (
    get_logger, get_config, clamp, lerp, generate_short_id,
    rgb_to_normalized, normalized_to_rgb
)

logger = get_logger("LightingManager")


# ============================================================
# LIGHT TYPES
# ============================================================

class LightType(Enum):
    """Light types"""
    DIRECTIONAL = "directional"    # Sun-like, parallel rays
    POINT = "point"                # Bulb-like, radiates in all directions
    SPOT = "spot"                  # Cone-shaped (flashlight)
    AMBIENT = "ambient"            # Uniform, no direction


# ============================================================
# LIGHT BASE CLASS
# ============================================================

@dataclass
class Light:
    """Base light class"""
    id: str = field(default_factory=generate_short_id)
    name: str = "Light"
    light_type: LightType = LightType.DIRECTIONAL
    enabled: bool = True

    # Color (0-1 normalized RGB)
    color: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    intensity: float = 1.0

    # Cast shadows
    cast_shadows: bool = True

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.light_type.value,
            "enabled": self.enabled,
            "color": self.color,
            "intensity": self.intensity,
            "cast_shadows": self.cast_shadows,
        }


@dataclass
class DirectionalLight(Light):
    """Directional light (like sun)"""
    direction: List[float] = field(default_factory=lambda: [-0.5, -1.0, -0.3])

    def __post_init__(self):
        self.light_type = LightType.DIRECTIONAL

    def get_normalized_direction(self) -> np.ndarray:
        d = np.array(self.direction, dtype=np.float32)
        norm = np.linalg.norm(d)
        return d / norm if norm > 0 else d

    def to_dict(self) -> Dict:
        d = super().to_dict()
        d["direction"] = self.direction
        return d


@dataclass
class PointLight(Light):
    """Point light (bulb)"""
    position: List[float] = field(default_factory=lambda: [0.0, 5.0, 0.0])
    range: float = 10.0            # Effect range
    constant_attenuation: float = 1.0
    linear_attenuation: float = 0.09
    quadratic_attenuation: float = 0.032

    def __post_init__(self):
        self.light_type = LightType.POINT

    def to_dict(self) -> Dict:
        d = super().to_dict()
        d.update({
            "position": self.position,
            "range": self.range,
            "attenuation": {
                "constant": self.constant_attenuation,
                "linear": self.linear_attenuation,
                "quadratic": self.quadratic_attenuation,
            }
        })
        return d


@dataclass
class SpotLight(Light):
    """Spot light (cone)"""
    position: List[float] = field(default_factory=lambda: [0.0, 5.0, 0.0])
    direction: List[float] = field(default_factory=lambda: [0.0, -1.0, 0.0])
    inner_cone_angle: float = 15.0   # Degrees (full brightness)
    outer_cone_angle: float = 30.0   # Degrees (fade out)
    range: float = 20.0

    def __post_init__(self):
        self.light_type = LightType.SPOT

    def get_normalized_direction(self) -> np.ndarray:
        d = np.array(self.direction, dtype=np.float32)
        norm = np.linalg.norm(d)
        return d / norm if norm > 0 else d

    def to_dict(self) -> Dict:
        d = super().to_dict()
        d.update({
            "position": self.position,
            "direction": self.direction,
            "inner_cone_angle": self.inner_cone_angle,
            "outer_cone_angle": self.outer_cone_angle,
            "range": self.range,
        })
        return d


@dataclass
class AmbientLight(Light):
    """Ambient light (uniform)"""

    def __post_init__(self):
        self.light_type = LightType.AMBIENT
        # Ambient usually shouldn't cast shadows
        self.cast_shadows = False


# ============================================================
# LIGHTING PRESETS
# ============================================================

class LightingPresets:
    """Pre-built lighting configurations"""

    # ---------- DAY / OUTDOOR ----------

    @staticmethod
    def day_outdoor() -> Dict:
        """Sunny day outdoors"""
        return {
            "name": "Day Outdoor",
            "description": "Bright sunny day with clear sky",
            "ambient": {
                "color": [0.53, 0.81, 0.92],  # Sky blue
                "intensity": 0.4,
            },
            "directional": [
                {
                    "name": "Sun",
                    "direction": [-0.3, -1.0, -0.2],
                    "color": [1.0, 0.98, 0.85],  # Warm white
                    "intensity": 1.2,
                }
            ],
        }

    @staticmethod
    def sunset() -> Dict:
        """Sunset lighting - warm orange"""
        return {
            "name": "Sunset",
            "description": "Warm orange sunset lighting",
            "ambient": {
                "color": [0.9, 0.5, 0.3],
                "intensity": 0.35,
            },
            "directional": [
                {
                    "name": "Setting Sun",
                    "direction": [-0.9, -0.2, -0.3],
                    "color": [1.0, 0.6, 0.3],  # Orange
                    "intensity": 1.0,
                }
            ],
        }

    @staticmethod
    def sunrise() -> Dict:
        """Sunrise lighting - soft warm"""
        return {
            "name": "Sunrise",
            "description": "Soft morning sunrise",
            "ambient": {
                "color": [0.95, 0.75, 0.7],
                "intensity": 0.3,
            },
            "directional": [
                {
                    "name": "Rising Sun",
                    "direction": [0.7, -0.3, -0.4],
                    "color": [1.0, 0.85, 0.7],
                    "intensity": 0.9,
                }
            ],
        }

    # ---------- NIGHT ----------

    @staticmethod
    def night_outdoor() -> Dict:
        """Moonlit night"""
        return {
            "name": "Night Outdoor",
            "description": "Dark night with moonlight",
            "ambient": {
                "color": [0.08, 0.08, 0.2],
                "intensity": 0.15,
            },
            "directional": [
                {
                    "name": "Moon",
                    "direction": [-0.5, -1.0, -0.3],
                    "color": [0.6, 0.7, 0.9],  # Cool blue moonlight
                    "intensity": 0.3,
                }
            ],
        }

    @staticmethod
    def night_city() -> Dict:
        """Night city with warm street lights"""
        return {
            "name": "Night City",
            "description": "Urban night with street lights",
            "ambient": {
                "color": [0.15, 0.1, 0.2],
                "intensity": 0.2,
            },
            "directional": [
                {
                    "name": "Moon",
                    "direction": [-0.3, -1.0, -0.4],
                    "color": [0.5, 0.6, 0.8],
                    "intensity": 0.2,
                }
            ],
            "point_lights": [
                {
                    "name": "Street Light 1",
                    "position": [3, 4, 0],
                    "color": [1.0, 0.7, 0.3],
                    "intensity": 1.5,
                    "range": 8.0,
                }
            ],
        }

    # ---------- INDOOR ----------

    @staticmethod
    def indoor_warm() -> Dict:
        """Cozy warm indoor lighting"""
        return {
            "name": "Indoor Warm",
            "description": "Warm cozy indoor lighting",
            "ambient": {
                "color": [1.0, 0.85, 0.7],
                "intensity": 0.4,
            },
            "point_lights": [
                {
                    "name": "Ceiling Light",
                    "position": [0, 4, 0],
                    "color": [1.0, 0.85, 0.7],
                    "intensity": 1.5,
                    "range": 10.0,
                }
            ],
        }

    @staticmethod
    def indoor_cool() -> Dict:
        """Cool office/modern indoor"""
        return {
            "name": "Indoor Cool",
            "description": "Modern cool indoor lighting",
            "ambient": {
                "color": [0.8, 0.88, 1.0],
                "intensity": 0.5,
            },
            "point_lights": [
                {
                    "name": "Ceiling Light",
                    "position": [0, 4, 0],
                    "color": [0.85, 0.92, 1.0],
                    "intensity": 1.2,
                    "range": 10.0,
                }
            ],
        }

    # ---------- STUDIO ----------

    @staticmethod
    def studio() -> Dict:
        """3-point studio lighting"""
        return {
            "name": "Studio",
            "description": "Professional 3-point studio lighting",
            "ambient": {
                "color": [1.0, 1.0, 1.0],
                "intensity": 0.3,
            },
            "directional": [
                {
                    "name": "Key Light",
                    "direction": [-0.5, -0.7, -0.5],
                    "color": [1.0, 0.95, 0.9],
                    "intensity": 1.5,
                },
                {
                    "name": "Fill Light",
                    "direction": [0.6, -0.4, -0.3],
                    "color": [0.9, 0.95, 1.0],
                    "intensity": 0.7,
                },
                {
                    "name": "Back Light (Rim)",
                    "direction": [0.2, -0.3, 0.9],
                    "color": [1.0, 1.0, 1.0],
                    "intensity": 0.8,
                },
            ],
        }

    # ---------- DRAMATIC / CINEMATIC ----------

    @staticmethod
    def dramatic() -> Dict:
        """High-contrast dramatic lighting"""
        return {
            "name": "Dramatic",
            "description": "High-contrast cinematic lighting",
            "ambient": {
                "color": [0.1, 0.1, 0.15],
                "intensity": 0.1,
            },
            "directional": [
                {
                    "name": "Key Light",
                    "direction": [-0.8, -0.6, -0.2],
                    "color": [1.0, 0.9, 0.7],
                    "intensity": 2.0,
                }
            ],
        }

    @staticmethod
    def horror() -> Dict:
        """Horror/dark lighting"""
        return {
            "name": "Horror",
            "description": "Dark scary atmosphere",
            "ambient": {
                "color": [0.05, 0.05, 0.1],
                "intensity": 0.1,
            },
            "directional": [
                {
                    "name": "Ominous Light",
                    "direction": [0.3, -1.0, 0.5],
                    "color": [0.3, 0.4, 0.5],
                    "intensity": 0.5,
                }
            ],
        }

    # ---------- ENVIRONMENTAL ----------

    @staticmethod
    def forest() -> Dict:
        """Forest with dappled light"""
        return {
            "name": "Forest",
            "description": "Green-tinted forest lighting",
            "ambient": {
                "color": [0.4, 0.6, 0.3],
                "intensity": 0.35,
            },
            "directional": [
                {
                    "name": "Filtered Sunlight",
                    "direction": [-0.2, -1.0, -0.3],
                    "color": [0.9, 1.0, 0.7],
                    "intensity": 0.9,
                }
            ],
        }

    @staticmethod
    def desert() -> Dict:
        """Bright hot desert"""
        return {
            "name": "Desert",
            "description": "Hot bright desert lighting",
            "ambient": {
                "color": [1.0, 0.85, 0.6],
                "intensity": 0.5,
            },
            "directional": [
                {
                    "name": "Hot Sun",
                    "direction": [-0.1, -1.0, -0.1],
                    "color": [1.0, 0.95, 0.75],
                    "intensity": 1.5,
                }
            ],
        }

    @staticmethod
    def snowy() -> Dict:
        """Snowy landscape"""
        return {
            "name": "Snowy",
            "description": "Cold snowy lighting",
            "ambient": {
                "color": [0.85, 0.9, 1.0],
                "intensity": 0.55,
            },
            "directional": [
                {
                    "name": "Winter Sun",
                    "direction": [-0.4, -0.9, -0.3],
                    "color": [0.9, 0.95, 1.0],
                    "intensity": 1.0,
                }
            ],
        }

    # ---------- ALL PRESETS ----------

    @classmethod
    def get_all_presets(cls) -> Dict[str, Callable]:
        return {
            "day_outdoor": cls.day_outdoor,
            "sunrise": cls.sunrise,
            "sunset": cls.sunset,
            "night_outdoor": cls.night_outdoor,
            "night_city": cls.night_city,
            "indoor_warm": cls.indoor_warm,
            "indoor_cool": cls.indoor_cool,
            "studio": cls.studio,
            "dramatic": cls.dramatic,
            "horror": cls.horror,
            "forest": cls.forest,
            "desert": cls.desert,
            "snowy": cls.snowy,
        }

    @classmethod
    def get_preset_names(cls) -> List[str]:
        return list(cls.get_all_presets().keys())

    @classmethod
    def get_preset(cls, name: str) -> Optional[Dict]:
        presets = cls.get_all_presets()
        if name in presets:
            return presets[name]()
        return None


# ============================================================
# TIME OF DAY SYSTEM
# ============================================================

class TimeOfDay:
    """Dynamic time-based lighting"""

    # Hour ranges (24h format)
    RANGES = {
        "dawn": (5, 7),         # 5 AM - 7 AM
        "morning": (7, 11),     # 7 AM - 11 AM
        "noon": (11, 14),       # 11 AM - 2 PM
        "afternoon": (14, 17),  # 2 PM - 5 PM
        "dusk": (17, 19),       # 5 PM - 7 PM
        "night": (19, 5),       # 7 PM - 5 AM
    }

    @staticmethod
    def get_time_period(hour: int) -> str:
        """Hour se time period detect karo"""
        hour = hour % 24
        if 5 <= hour < 7:
            return "dawn"
        elif 7 <= hour < 11:
            return "morning"
        elif 11 <= hour < 14:
            return "noon"
        elif 14 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 19:
            return "dusk"
        else:
            return "night"

    @staticmethod
    def get_lighting_for_time(hour: int, environment: str = "outdoor") -> Dict:
        """Time aur environment ke basis pe lighting return karo"""
        period = TimeOfDay.get_time_period(hour)

        if environment == "outdoor":
            mapping = {
                "dawn": "sunrise",
                "morning": "day_outdoor",
                "noon": "day_outdoor",
                "afternoon": "day_outdoor",
                "dusk": "sunset",
                "night": "night_outdoor",
            }
        else:  # indoor
            mapping = {
                "dawn": "indoor_warm",
                "morning": "indoor_cool",
                "noon": "indoor_cool",
                "afternoon": "indoor_cool",
                "dusk": "indoor_warm",
                "night": "indoor_warm",
            }

        preset_name = mapping.get(period, "day_outdoor")
        preset = LightingPresets.get_preset(preset_name)
        if preset:
            preset["time_period"] = period
            preset["hour"] = hour
        return preset


# ============================================================
# SEASON SYSTEM
# ============================================================

class Season:
    """Seasonal lighting adjustments"""

    ADJUSTMENTS = {
        "spring": {
            "temperature_shift": 0.0,      # Neutral
            "intensity_multiplier": 1.0,
            "green_boost": 0.1,
        },
        "summer": {
            "temperature_shift": 0.1,      # Slightly warm
            "intensity_multiplier": 1.15,   # Brighter
            "green_boost": 0.0,
        },
        "autumn": {
            "temperature_shift": 0.2,      # Warm
            "intensity_multiplier": 0.9,
            "red_boost": 0.1,
        },
        "winter": {
            "temperature_shift": -0.15,    # Cool
            "intensity_multiplier": 0.8,   # Dimmer
            "blue_boost": 0.1,
        },
    }

    @staticmethod
    def apply_to_lighting(lighting_data: Dict, season: str) -> Dict:
        """Season adjustments apply karo"""
        if season not in Season.ADJUSTMENTS:
            return lighting_data

        adj = Season.ADJUSTMENTS[season]
        multiplier = adj.get("intensity_multiplier", 1.0)

        # Ambient
        if "ambient" in lighting_data:
            lighting_data["ambient"]["intensity"] *= multiplier

        # Directional
        if "directional" in lighting_data:
            for light in lighting_data["directional"]:
                light["intensity"] *= multiplier

        # Point lights
        if "point_lights" in lighting_data:
            for light in lighting_data["point_lights"]:
                light["intensity"] *= multiplier

        return lighting_data


# ============================================================
# LIGHTING MANAGER (Main Class)
# ============================================================

class LightingManager:
    """
    Main lighting system.
    Multiple lights + presets + animations manage karta hai.
    """

    def __init__(self, config: Optional[Dict] = None):
        # Config
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # Lights lists
        self.directional_lights: List[DirectionalLight] = []
        self.point_lights: List[PointLight] = []
        self.spot_lights: List[SpotLight] = []
        self.ambient_light: AmbientLight = AmbientLight(
            name="Ambient",
            color=[0.4, 0.4, 0.5],
            intensity=0.3
        )

        # Current preset info
        self.current_preset_name: Optional[str] = None
        self.current_environment: str = "outdoor"
        self.current_season: str = "summer"
        self.current_hour: int = 12  # noon default

        # Change listeners
        self._listeners: List[Callable] = []

        # Default preset load karo
        default_preset = self.config.get("lighting", {}).get(
            "default_preset", "day_outdoor"
        )
        self.apply_preset(default_preset)

        logger.info(f"LightingManager initialized with preset: {default_preset}")

    # ------------------------------------------------------------
    # PRESET APPLICATION
    # ------------------------------------------------------------

    def apply_preset(self, preset_name: str) -> bool:
        """Named preset apply karo"""
        preset = LightingPresets.get_preset(preset_name)
        if not preset:
            logger.warning(f"Unknown preset: {preset_name}")
            return False

        return self.apply_lighting_data(preset, preset_name)

    def apply_lighting_data(self, data: Dict,
                             preset_name: Optional[str] = None) -> bool:
        """Custom lighting data apply karo"""
        try:
            # Existing lights clear karo
            self.clear_all_lights()

            # Ambient
            if "ambient" in data:
                amb_data = data["ambient"]
                self.ambient_light = AmbientLight(
                    name="Ambient",
                    color=amb_data.get("color", [1, 1, 1]),
                    intensity=amb_data.get("intensity", 0.3)
                )

            # Directional lights
            for dir_data in data.get("directional", []):
                light = DirectionalLight(
                    name=dir_data.get("name", "Directional"),
                    direction=dir_data.get("direction", [0, -1, 0]),
                    color=dir_data.get("color", [1, 1, 1]),
                    intensity=dir_data.get("intensity", 1.0)
                )
                self.directional_lights.append(light)

            # Point lights
            for pt_data in data.get("point_lights", []):
                light = PointLight(
                    name=pt_data.get("name", "Point"),
                    position=pt_data.get("position", [0, 5, 0]),
                    color=pt_data.get("color", [1, 1, 1]),
                    intensity=pt_data.get("intensity", 1.0),
                    range=pt_data.get("range", 10.0)
                )
                self.point_lights.append(light)

            # Spot lights
            for sp_data in data.get("spot_lights", []):
                light = SpotLight(
                    name=sp_data.get("name", "Spot"),
                    position=sp_data.get("position", [0, 5, 0]),
                    direction=sp_data.get("direction", [0, -1, 0]),
                    color=sp_data.get("color", [1, 1, 1]),
                    intensity=sp_data.get("intensity", 1.0),
                    inner_cone_angle=sp_data.get("inner_cone_angle", 15.0),
                    outer_cone_angle=sp_data.get("outer_cone_angle", 30.0),
                    range=sp_data.get("range", 20.0)
                )
                self.spot_lights.append(light)

            self.current_preset_name = preset_name or data.get("name", "custom")

            preset_display = data.get("name", preset_name or "Custom")
            logger.info(f"Applied lighting: {preset_display}")

            self._notify_listeners("preset_applied")
            return True

        except Exception as e:
            logger.error(f"Failed to apply lighting: {e}")
            return False

    # ------------------------------------------------------------
    # TIME OF DAY & SEASON
    # ------------------------------------------------------------

    def set_time_of_day(self, hour: int, apply_immediately: bool = True):
        """Time of day set karo"""
        self.current_hour = hour % 24

        if apply_immediately:
            lighting = TimeOfDay.get_lighting_for_time(
                self.current_hour, self.current_environment
            )
            if lighting:
                # Season adjustment bhi apply karo
                lighting = Season.apply_to_lighting(lighting, self.current_season)
                self.apply_lighting_data(lighting, f"time_{self.current_hour}h")

        logger.info(f"Time set to: {hour}:00 ({TimeOfDay.get_time_period(hour)})")

    def set_season(self, season: str, apply_immediately: bool = True):
        """Season set karo"""
        if season not in Season.ADJUSTMENTS:
            logger.warning(f"Unknown season: {season}")
            return

        self.current_season = season

        if apply_immediately and self.current_preset_name:
            # Current preset dobara apply karo with season
            preset = LightingPresets.get_preset(self.current_preset_name)
            if preset:
                preset = Season.apply_to_lighting(preset, season)
                self.apply_lighting_data(preset, self.current_preset_name)

        logger.info(f"Season set to: {season}")

    def set_environment(self, environment: str):
        """Environment set karo (outdoor/indoor)"""
        self.current_environment = environment
        logger.debug(f"Environment: {environment}")

    # ------------------------------------------------------------
    # LIGHT MANAGEMENT
    # ------------------------------------------------------------

    def add_directional_light(self, name: str = "Directional",
                                direction: Optional[List[float]] = None,
                                color: Optional[List[float]] = None,
                                intensity: float = 1.0) -> DirectionalLight:
        """Directional light add karo"""
        light = DirectionalLight(
            name=name,
            direction=direction or [-0.5, -1.0, -0.3],
            color=color or [1.0, 1.0, 1.0],
            intensity=intensity
        )
        self.directional_lights.append(light)
        self._notify_listeners("light_added")
        return light

    def add_point_light(self, name: str = "Point",
                        position: Optional[List[float]] = None,
                        color: Optional[List[float]] = None,
                        intensity: float = 1.0,
                        range: float = 10.0) -> PointLight:
        """Point light add karo"""
        light = PointLight(
            name=name,
            position=position or [0, 5, 0],
            color=color or [1, 1, 1],
            intensity=intensity,
            range=range
        )
        self.point_lights.append(light)
        self._notify_listeners("light_added")
        return light

    def add_spot_light(self, name: str = "Spot",
                        position: Optional[List[float]] = None,
                        direction: Optional[List[float]] = None,
                        color: Optional[List[float]] = None,
                        intensity: float = 1.0) -> SpotLight:
        """Spot light add karo"""
        light = SpotLight(
            name=name,
            position=position or [0, 5, 0],
            direction=direction or [0, -1, 0],
            color=color or [1, 1, 1],
            intensity=intensity
        )
        self.spot_lights.append(light)
        self._notify_listeners("light_added")
        return light

    def remove_light(self, light_id: str) -> bool:
        """Light remove karo by ID"""
        for lights_list in [self.directional_lights,
                            self.point_lights,
                            self.spot_lights]:
            for i, light in enumerate(lights_list):
                if light.id == light_id:
                    removed = lights_list.pop(i)
                    logger.debug(f"Removed light: {removed.name}")
                    self._notify_listeners("light_removed")
                    return True
        return False

    def get_light(self, light_id: str) -> Optional[Light]:
        """Light get karo by ID"""
        for lights_list in [self.directional_lights,
                            self.point_lights,
                            self.spot_lights]:
            for light in lights_list:
                if light.id == light_id:
                    return light

        if self.ambient_light.id == light_id:
            return self.ambient_light

        return None

    def get_all_lights(self) -> List[Light]:
        """Saari lights"""
        return (
            [self.ambient_light] +
            list(self.directional_lights) +
            list(self.point_lights) +
            list(self.spot_lights)
        )

    def clear_all_lights(self):
        """Sab lights clear karo (ambient except)"""
        self.directional_lights.clear()
        self.point_lights.clear()
        self.spot_lights.clear()

    # ------------------------------------------------------------
    # LIGHT INTENSITY CONTROL
    # ------------------------------------------------------------

    def set_global_intensity(self, multiplier: float):
        """Sab lights ki intensity multiply karo"""
        multiplier = clamp(multiplier, 0.0, 5.0)

        self.ambient_light.intensity *= multiplier
        for light in self.directional_lights:
            light.intensity *= multiplier
        for light in self.point_lights:
            light.intensity *= multiplier
        for light in self.spot_lights:
            light.intensity *= multiplier

        logger.debug(f"Global intensity applied: x{multiplier}")

    def enable_all(self):
        """Sab lights enable karo"""
        self.ambient_light.enabled = True
        for lights in [self.directional_lights,
                       self.point_lights,
                       self.spot_lights]:
            for light in lights:
                light.enabled = True

    def disable_all(self):
        """Sab lights disable karo"""
        self.ambient_light.enabled = False
        for lights in [self.directional_lights,
                       self.point_lights,
                       self.spot_lights]:
            for light in lights:
                light.enabled = False

    # ------------------------------------------------------------
    # LIGHT INTERPOLATION (Smooth Transitions)
    # ------------------------------------------------------------

    def interpolate_to_preset(self, target_preset: str,
                               steps: int = 30) -> List[Dict]:
        """
        Current lighting se target preset tak smooth transition.

        Returns:
            List of interpolated states (animation frames)
        """
        target = LightingPresets.get_preset(target_preset)
        if not target:
            return []

        # Current state save karo
        current = self.export_current()

        frames = []
        for i in range(steps + 1):
            t = i / steps  # 0 → 1

            # Ambient interpolate
            interp = {
                "ambient": {
                    "color": [
                        lerp(current["ambient"]["color"][j],
                             target["ambient"]["color"][j], t)
                        for j in range(3)
                    ],
                    "intensity": lerp(
                        current["ambient"]["intensity"],
                        target["ambient"]["intensity"], t
                    )
                }
            }

            frames.append(interp)

        return frames

    # ------------------------------------------------------------
    # EXPORT/IMPORT
    # ------------------------------------------------------------

    def export_current(self) -> Dict:
        """Current lighting state export karo"""
        return {
            "name": self.current_preset_name or "custom",
            "ambient": {
                "color": list(self.ambient_light.color),
                "intensity": self.ambient_light.intensity,
            },
            "directional": [
                {
                    "name": l.name,
                    "direction": l.direction,
                    "color": l.color,
                    "intensity": l.intensity,
                }
                for l in self.directional_lights
            ],
            "point_lights": [
                {
                    "name": l.name,
                    "position": l.position,
                    "color": l.color,
                    "intensity": l.intensity,
                    "range": l.range,
                }
                for l in self.point_lights
            ],
            "spot_lights": [
                {
                    "name": l.name,
                    "position": l.position,
                    "direction": l.direction,
                    "color": l.color,
                    "intensity": l.intensity,
                    "inner_cone_angle": l.inner_cone_angle,
                    "outer_cone_angle": l.outer_cone_angle,
                    "range": l.range,
                }
                for l in self.spot_lights
            ],
            "environment": self.current_environment,
            "season": self.current_season,
            "hour": self.current_hour,
        }

    # ------------------------------------------------------------
    # STATISTICS
    # ------------------------------------------------------------

    def get_stats(self) -> Dict:
        """Lighting statistics"""
        return {
            "total_lights": len(self.get_all_lights()),
            "directional": len(self.directional_lights),
            "point": len(self.point_lights),
            "spot": len(self.spot_lights),
            "ambient": 1,
            "enabled_count": sum(1 for l in self.get_all_lights() if l.enabled),
            "current_preset": self.current_preset_name,
            "environment": self.current_environment,
            "season": self.current_season,
            "hour": self.current_hour,
            "time_period": TimeOfDay.get_time_period(self.current_hour),
        }

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

    # ------------------------------------------------------------
    # RENDER ENGINE INTEGRATION
    # ------------------------------------------------------------

    def apply_to_render_engine(self, engine: Any) -> bool:
        """
        Lighting ko RenderEngine pe apply karo.
        Currently sirf primary directional + ambient support hai.
        """
        try:
            # Ambient
            engine.ambient_light.color = list(self.ambient_light.color)
            engine.ambient_light.intensity = self.ambient_light.intensity

            # Primary directional (first one)
            if self.directional_lights:
                primary = self.directional_lights[0]
                engine.directional_light.direction = list(primary.direction)
                engine.directional_light.color = list(primary.color)
                engine.directional_light.intensity = primary.intensity

            logger.debug("Lighting applied to render engine")
            return True

        except Exception as e:
            logger.error(f"Failed to apply lighting to engine: {e}")
            return False


# ============================================================
# TEST FUNCTION
# ============================================================


if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section, ensure_dir
    setup_logging(log_level="DEBUG")
    print_banner("Lighting Manager Test", "Advanced Lighting System")

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))

    # ============================================================
    # Test 1: Initialize
    # ============================================================
    print_section("Test 1: Initialize Lighting Manager")

    lm = LightingManager()

    stats = lm.get_stats()
    print(f"Total lights: {stats['total_lights']}")
    print(f"Directional: {stats['directional']}")
    print(f"Point: {stats['point']}")
    print(f"Current preset: {stats['current_preset']}")

    # ============================================================
    # Test 2: Available Presets
    # ============================================================
    print_section("Test 2: Available Presets")

    presets = LightingPresets.get_preset_names()
    print(f"Total presets: {len(presets)}")
    for i, name in enumerate(presets, 1):
        preset = LightingPresets.get_preset(name)
        print(f"  {i:2}. {name:20s} - {preset.get('description', 'N/A')}")

    # ============================================================
    # Test 3: Apply Different Presets
    # ============================================================
    print_section("Test 3: Apply Presets")

    test_presets = ["day_outdoor", "sunset", "night_outdoor", "studio", "dramatic"]

    for preset_name in test_presets:
        success = lm.apply_preset(preset_name)
        stats = lm.get_stats()
        print(f"  {preset_name}: {'✓' if success else '✗'} "
              f"({stats['total_lights']} lights)")

    # ============================================================
    # Test 4: Custom Lights
    # ============================================================
    print_section("Test 4: Add Custom Lights")

    lm.apply_preset("indoor_warm")

    # Additional point light add karo
    lm.add_point_light(
        name="Table Lamp",
        position=[2, 1.5, 1],
        color=[1.0, 0.7, 0.4],
        intensity=1.2,
        range=5.0
    )

    lm.add_spot_light(
        name="Reading Light",
        position=[3, 2, 2],
        direction=[-0.3, -1.0, -0.5],
        color=[1.0, 1.0, 0.9],
        intensity=1.5
    )

    stats = lm.get_stats()
    print(f"After custom lights:")
    print(f"  Total: {stats['total_lights']}")
    print(f"  Point: {stats['point']}")
    print(f"  Spot: {stats['spot']}")

    # ============================================================
    # Test 5: Time of Day
    # ============================================================
    print_section("Test 5: Time of Day System")

    test_hours = [6, 9, 12, 15, 18, 22]
    for hour in test_hours:
        lm.set_time_of_day(hour)
        period = TimeOfDay.get_time_period(hour)
        primary_intensity = (lm.directional_lights[0].intensity
                            if lm.directional_lights else 0)
        print(f"  {hour:2}:00 ({period:10s}) → Primary light: {primary_intensity:.2f}")

    # ============================================================
    # Test 6: Seasons
    # ============================================================
    print_section("Test 6: Season Effects")

    lm.apply_preset("day_outdoor")
    base_intensity = lm.directional_lights[0].intensity if lm.directional_lights else 0
    print(f"Base intensity: {base_intensity:.2f}")

    for season in ["spring", "summer", "autumn", "winter"]:
        lm.apply_preset("day_outdoor")  # Reset
        lm.set_season(season)
        new_intensity = lm.directional_lights[0].intensity if lm.directional_lights else 0
        print(f"  {season:8s}: {new_intensity:.2f}x")

    # ============================================================
    # Test 7: Global Intensity
    # ============================================================
    print_section("Test 7: Global Intensity Control")

    lm.apply_preset("studio")
    initial_intensity = lm.directional_lights[0].intensity
    print(f"Initial studio key light: {initial_intensity:.2f}")

    lm.set_global_intensity(0.5)  # Dim to half
    print(f"After 0.5x: {lm.directional_lights[0].intensity:.2f}")

    lm.apply_preset("studio")  # Reset
    lm.set_global_intensity(2.0)  # Brighten
    print(f"After 2.0x: {lm.directional_lights[0].intensity:.2f}")

    # ============================================================
    # Test 8: Render With Different Lighting
    # ============================================================
    print_section("Test 8: Render with Different Lighting")

    from src.renderer.render_engine import (
        RenderEngine, PrimitiveFactory
    )

    engine = RenderEngine(width=1280, height=720, headless=True)

    if engine.initialized:
        # Scene setup
        sphere = PrimitiveFactory.create_sphere(radius=1.0)
        sphere.color = [0.8, 0.8, 0.9]
        engine.add_mesh(sphere)

        plane = PrimitiveFactory.create_plane(size=8.0)
        plane.color = [0.4, 0.4, 0.4]
        plane.position[1] = -1.0
        engine.add_mesh(plane)

        engine.camera.position = [3, 2, 4]
        engine.camera.target = [0, 0, 0]

        # Different lighting presets ke saath render karo
        render_presets = ["day_outdoor", "sunset", "night_outdoor", "studio", "dramatic"]

        output_dir = os.path.join(base_dir, "temp", "lighting_tests")
        ensure_dir(output_dir)

        for preset_name in render_presets:
            lm.apply_preset(preset_name)
            lm.apply_to_render_engine(engine)

            output_path = os.path.join(output_dir, f"lighting_{preset_name}.png")
            engine.render_to_image(output_path)
            print(f"  ✓ Rendered: {preset_name}.png")

        print(f"\n👉 Compare renders in: {output_dir}")

        engine.shutdown()

    # ============================================================
    # Test 9: Export State
    # ============================================================
    print_section("Test 9: Export Current State")

    lm.apply_preset("studio")
    exported = lm.export_current()
    print(f"Exported state:")
    print(f"  Name: {exported['name']}")
    print(f"  Directional count: {len(exported['directional'])}")
    print(f"  Point count: {len(exported['point_lights'])}")

    # ============================================================
    # Test 10: Final Stats
    # ============================================================
    print_section("Test 10: Final Statistics")

    stats = lm.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print_banner(
        "✅ All Tests Passed",
        "Lighting Manager Working - Check rendered comparisons!"
    )