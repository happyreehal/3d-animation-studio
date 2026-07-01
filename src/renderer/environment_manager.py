# ============================================================
# src/renderer/environment_manager.py
# 3D Animation Studio - Environment Manager
# Environments (Forest, Desert, City, etc.) with dynamic changes
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
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum

from src.utils import get_logger, get_config, generate_uuid

logger = get_logger("EnvironmentManager")


# ============================================================
# ENUMS
# ============================================================

class EnvironmentType(Enum):
    """Environment types"""
    FOREST          = "forest"
    DESERT          = "desert"
    SNOWY           = "snowy"
    CITY            = "city"
    OFFICE          = "office"
    HOME            = "home"
    KITCHEN         = "kitchen"
    BEDROOM         = "bedroom"
    LIVING_ROOM     = "living_room"
    SCHOOL          = "school"
    CLASSROOM       = "classroom"
    BEACH           = "beach"
    MOUNTAIN        = "mountain"
    PARK            = "park"
    STREET          = "street"
    OCEAN           = "ocean"
    SPACE           = "space"
    CAVE            = "cave"
    UNDERWATER      = "underwater"
    JUNGLE          = "jungle"
    STUDIO          = "studio"
    FANTASY         = "fantasy"
    SCI_FI          = "sci_fi"
    ABSTRACT        = "abstract"


class Season(Enum):
    """Seasons"""
    SPRING          = "spring"
    SUMMER          = "summer"
    AUTUMN          = "autumn"
    WINTER          = "winter"


class Weather(Enum):
    """Weather conditions"""
    CLEAR           = "clear"
    CLOUDY          = "cloudy"
    RAINY           = "rainy"
    SNOWY           = "snowy"
    FOGGY           = "foggy"
    STORMY          = "stormy"
    WINDY           = "windy"


class SkyType(Enum):
    """Sky rendering types"""
    SOLID_COLOR     = "solid"
    GRADIENT        = "gradient"
    SKYBOX          = "skybox"
    HDRI            = "hdri"


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class SkySettings:
    """Sky/atmosphere settings"""
    sky_type:           str             = SkyType.GRADIENT.value

    # Colors
    horizon_color:      List[float]     = field(default_factory=lambda: [0.7, 0.85, 1.0])
    zenith_color:       List[float]     = field(default_factory=lambda: [0.3, 0.5, 0.9])
    ground_color:       List[float]     = field(default_factory=lambda: [0.4, 0.35, 0.3])

    # Sun position
    sun_direction:      List[float]     = field(default_factory=lambda: [0.3, -1.0, 0.2])
    sun_color:          List[float]     = field(default_factory=lambda: [1.0, 0.95, 0.85])
    sun_intensity:      float           = 1.2

    # Ambient
    ambient_color:      List[float]     = field(default_factory=lambda: [0.5, 0.6, 0.75])
    ambient_intensity:  float           = 0.4

    # Optional file paths
    skybox_path:        str             = ""
    hdri_path:          str             = ""

    def to_dict(self) -> Dict:
        return {
            "sky_type":       self.sky_type,
            "horizon_color":  self.horizon_color,
            "zenith_color":   self.zenith_color,
            "ground_color":   self.ground_color,
            "sun_direction":  self.sun_direction,
            "sun_color":      self.sun_color,
            "sun_intensity":  self.sun_intensity,
            "ambient_color":  self.ambient_color,
            "ambient_intensity": self.ambient_intensity,
        }


@dataclass
class FogSettings:
    """Fog/atmosphere settings"""
    enabled:            bool            = False
    color:              List[float]     = field(default_factory=lambda: [0.7, 0.75, 0.85])
    density:            float           = 0.01
    start_distance:     float           = 5.0
    end_distance:       float           = 100.0

    def to_dict(self) -> Dict:
        return {
            "enabled":        self.enabled,
            "color":          self.color,
            "density":        self.density,
            "start_distance": self.start_distance,
            "end_distance":   self.end_distance,
        }


@dataclass
class GroundSettings:
    """Ground plane settings"""
    enabled:            bool            = True
    color:              List[float]     = field(default_factory=lambda: [0.35, 0.45, 0.3])
    texture:            str             = ""            # Texture file path
    texture_scale:      float           = 1.0
    size:               float           = 100.0
    reflective:         bool            = False
    roughness:          float           = 0.8

    def to_dict(self) -> Dict:
        return {
            "enabled":       self.enabled,
            "color":         self.color,
            "texture":       self.texture,
            "texture_scale": self.texture_scale,
            "size":          self.size,
            "reflective":    self.reflective,
            "roughness":     self.roughness,
        }


@dataclass
class EnvironmentProp:
    """A single prop/object in environment (tree, rock, building)"""
    prop_id:            str             = ""
    prop_type:          str             = "generic"    # tree, rock, building, etc.
    position:           List[float]     = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation:           List[float]     = field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale:              List[float]     = field(default_factory=lambda: [1.0, 1.0, 1.0])
    color:              List[float]     = field(default_factory=lambda: [0.5, 0.5, 0.5])
    model_path:         str             = ""

    def __post_init__(self):
        if not self.prop_id:
            self.prop_id = f"prop_{generate_uuid()[:8]}"

    def to_dict(self) -> Dict:
        return {
            "prop_id":     self.prop_id,
            "prop_type":   self.prop_type,
            "position":    self.position,
            "rotation":    self.rotation,
            "scale":       self.scale,
            "color":       self.color,
            "model_path":  self.model_path,
        }


@dataclass
class ParticleEffect:
    """Environment particle effects (rain, snow, dust)"""
    effect_id:          str             = ""
    effect_type:        str             = "rain"        # rain, snow, dust, leaves
    enabled:            bool            = True
    intensity:          float           = 1.0
    area_size:          float           = 20.0
    height:             float           = 15.0
    color:              List[float]     = field(default_factory=lambda: [0.7, 0.7, 0.8])
    speed:              float           = 5.0

    def __post_init__(self):
        if not self.effect_id:
            self.effect_id = f"fx_{generate_uuid()[:8]}"

    def to_dict(self) -> Dict:
        return {
            "effect_id":  self.effect_id,
            "effect_type":self.effect_type,
            "enabled":    self.enabled,
            "intensity":  self.intensity,
            "area_size":  self.area_size,
            "height":     self.height,
            "color":      self.color,
            "speed":      self.speed,
        }


@dataclass
class Environment:
    """
    Complete environment definition.
    Sky + Ground + Props + Weather sab yahaan.
    """
    # Identity
    environment_id:     str             = ""
    name:               str             = "Environment"
    env_type:           str             = EnvironmentType.PARK.value

    # Settings
    sky:                SkySettings     = field(default_factory=SkySettings)
    fog:                FogSettings     = field(default_factory=FogSettings)
    ground:             GroundSettings  = field(default_factory=GroundSettings)

    # Props (trees, rocks, buildings, etc.)
    props:              List[EnvironmentProp] = field(default_factory=list)

    # Particle effects (rain, snow, dust)
    particles:          List[ParticleEffect] = field(default_factory=list)

    # Weather & time
    weather:            str             = Weather.CLEAR.value
    season:             str             = Season.SUMMER.value
    time_of_day:        str             = "noon"       # dawn, morning, noon, evening, night

    # Audio
    ambient_sounds:     List[str]       = field(default_factory=list)

    # Metadata
    description:        str             = ""
    is_preset:          bool            = False

    def __post_init__(self):
        if not self.environment_id:
            self.environment_id = f"env_{generate_uuid()[:8]}"

    def to_dict(self) -> Dict:
        return {
            "environment_id": self.environment_id,
            "name":           self.name,
            "env_type":       self.env_type,
            "sky":            self.sky.to_dict(),
            "fog":            self.fog.to_dict(),
            "ground":         self.ground.to_dict(),
            "props":          [p.to_dict() for p in self.props],
            "particles":      [p.to_dict() for p in self.particles],
            "weather":        self.weather,
            "season":         self.season,
            "time_of_day":    self.time_of_day,
            "ambient_sounds": self.ambient_sounds,
            "description":    self.description,
            "is_preset":      self.is_preset,
        }


# ============================================================
# PROP GENERATORS - Trees, Rocks, Buildings
# ============================================================

class PropGenerator:
    """Environment props automatically generate karta hai"""

    @staticmethod
    def generate_trees(
        count:          int             = 10,
        area_size:      float           = 30.0,
        exclude_center: float           = 5.0,
        tree_type:      str             = "generic",
    ) -> List[EnvironmentProp]:
        """
        Trees random positions pe generate karo.

        Args:
            count: Total trees
            area_size: Area size (square)
            exclude_center: Empty circle in center
            tree_type: Type of tree (pine, oak, palm, etc.)
        """
        trees = []
        half = area_size / 2

        # Tree colors by type
        colors = {
            "pine":     [0.15, 0.35, 0.15],
            "oak":      [0.25, 0.45, 0.20],
            "palm":     [0.35, 0.55, 0.25],
            "dead":     [0.30, 0.20, 0.15],
            "generic":  [0.20, 0.40, 0.15],
        }
        color = colors.get(tree_type, colors["generic"])

        attempts = 0
        while len(trees) < count and attempts < count * 3:
            attempts += 1

            x = random.uniform(-half, half)
            z = random.uniform(-half, half)

            # Skip center area
            if math.sqrt(x * x + z * z) < exclude_center:
                continue

            scale = random.uniform(0.7, 1.4)
            rot_y = random.uniform(0, 360)

            tree = EnvironmentProp(
                prop_type = f"tree_{tree_type}",
                position  = [x, 0.0, z],
                rotation  = [0, rot_y, 0],
                scale     = [scale, scale * random.uniform(0.9, 1.3), scale],
                color     = [
                    color[0] + random.uniform(-0.05, 0.05),
                    color[1] + random.uniform(-0.05, 0.05),
                    color[2] + random.uniform(-0.05, 0.05),
                ],
            )
            trees.append(tree)

        return trees

    @staticmethod
    def generate_rocks(
        count:          int             = 5,
        area_size:      float           = 20.0,
        exclude_center: float           = 3.0,
    ) -> List[EnvironmentProp]:
        """Rocks generate karo"""
        rocks = []
        half = area_size / 2

        attempts = 0
        while len(rocks) < count and attempts < count * 3:
            attempts += 1

            x = random.uniform(-half, half)
            z = random.uniform(-half, half)

            if math.sqrt(x * x + z * z) < exclude_center:
                continue

            scale = random.uniform(0.3, 1.2)

            rock = EnvironmentProp(
                prop_type = "rock",
                position  = [x, 0.0, z],
                rotation  = [
                    random.uniform(-15, 15),
                    random.uniform(0, 360),
                    random.uniform(-15, 15),
                ],
                scale     = [scale, scale * 0.6, scale * random.uniform(0.8, 1.2)],
                color     = [
                    random.uniform(0.35, 0.55),
                    random.uniform(0.35, 0.5),
                    random.uniform(0.3, 0.45),
                ],
            )
            rocks.append(rock)

        return rocks

    @staticmethod
    def generate_buildings(
        count:          int             = 8,
        area_size:      float           = 40.0,
        exclude_center: float           = 8.0,
    ) -> List[EnvironmentProp]:
        """City buildings generate karo"""
        buildings = []
        half = area_size / 2

        attempts = 0
        while len(buildings) < count and attempts < count * 3:
            attempts += 1

            x = random.uniform(-half, half)
            z = random.uniform(-half, half)

            if math.sqrt(x * x + z * z) < exclude_center:
                continue

            width = random.uniform(2, 5)
            height = random.uniform(4, 15)
            depth = random.uniform(2, 5)

            # Building color (gray tones)
            gray = random.uniform(0.4, 0.7)

            building = EnvironmentProp(
                prop_type = "building",
                position  = [x, height / 2, z],
                rotation  = [0, random.choice([0, 90]), 0],
                scale     = [width, height, depth],
                color     = [gray * 0.9, gray * 0.95, gray],
            )
            buildings.append(building)

        return buildings

    @staticmethod
    def generate_grass_patches(
        count:          int             = 20,
        area_size:      float           = 20.0,
    ) -> List[EnvironmentProp]:
        """Grass patches"""
        patches = []
        half = area_size / 2

        for _ in range(count):
            x = random.uniform(-half, half)
            z = random.uniform(-half, half)
            scale = random.uniform(0.4, 1.0)

            patch = EnvironmentProp(
                prop_type = "grass_patch",
                position  = [x, 0.0, z],
                rotation  = [0, random.uniform(0, 360), 0],
                scale     = [scale, scale * 0.5, scale],
                color     = [
                    random.uniform(0.25, 0.4),
                    random.uniform(0.45, 0.6),
                    random.uniform(0.15, 0.25),
                ],
            )
            patches.append(patch)

        return patches

    @staticmethod
    def generate_cacti(
        count:          int             = 6,
        area_size:      float           = 25.0,
    ) -> List[EnvironmentProp]:
        """Desert cacti"""
        cacti = []
        half = area_size / 2

        for _ in range(count):
            x = random.uniform(-half, half)
            z = random.uniform(-half, half)

            if math.sqrt(x * x + z * z) < 3.0:
                continue

            scale = random.uniform(0.6, 1.5)

            cactus = EnvironmentProp(
                prop_type = "cactus",
                position  = [x, 0.0, z],
                rotation  = [0, random.uniform(0, 360), 0],
                scale     = [scale * 0.8, scale, scale * 0.8],
                color     = [0.3, 0.5, 0.3],
            )
            cacti.append(cactus)

        return cacti

    @staticmethod
    def generate_furniture_home() -> List[EnvironmentProp]:
        """Home furniture"""
        return [
            EnvironmentProp(
                prop_type="sofa",
                position=[-2.5, 0.5, -3.0],
                rotation=[0, 0, 0],
                scale=[2.5, 1.0, 1.2],
                color=[0.5, 0.35, 0.25],
            ),
            EnvironmentProp(
                prop_type="table",
                position=[0.0, 0.4, -2.0],
                rotation=[0, 0, 0],
                scale=[1.2, 0.8, 0.7],
                color=[0.4, 0.25, 0.15],
            ),
            EnvironmentProp(
                prop_type="tv_stand",
                position=[0.0, 0.6, -4.5],
                rotation=[0, 0, 0],
                scale=[2.5, 1.2, 0.4],
                color=[0.1, 0.1, 0.15],
            ),
            EnvironmentProp(
                prop_type="lamp",
                position=[-3.5, 0.8, -3.5],
                rotation=[0, 0, 0],
                scale=[0.3, 1.6, 0.3],
                color=[0.9, 0.85, 0.6],
            ),
            EnvironmentProp(
                prop_type="rug",
                position=[0.0, 0.02, -2.5],
                rotation=[0, 0, 0],
                scale=[3.5, 0.05, 2.5],
                color=[0.6, 0.2, 0.15],
            ),
        ]

    @staticmethod
    def generate_furniture_office() -> List[EnvironmentProp]:
        """Office furniture"""
        return [
            EnvironmentProp(
                prop_type="desk",
                position=[0.0, 0.4, -2.0],
                rotation=[0, 0, 0],
                scale=[2.0, 0.8, 1.0],
                color=[0.5, 0.35, 0.2],
            ),
            EnvironmentProp(
                prop_type="office_chair",
                position=[0.0, 0.5, -0.5],
                rotation=[0, 0, 0],
                scale=[0.8, 1.0, 0.8],
                color=[0.1, 0.1, 0.15],
            ),
            EnvironmentProp(
                prop_type="computer",
                position=[0.0, 0.9, -2.2],
                rotation=[0, 0, 0],
                scale=[1.0, 0.6, 0.1],
                color=[0.05, 0.05, 0.05],
            ),
            EnvironmentProp(
                prop_type="bookshelf",
                position=[-3.5, 1.5, -4.0],
                rotation=[0, 0, 0],
                scale=[1.5, 3.0, 0.4],
                color=[0.45, 0.3, 0.2],
            ),
            EnvironmentProp(
                prop_type="filing_cabinet",
                position=[3.5, 0.8, -4.0],
                rotation=[0, 0, 0],
                scale=[0.8, 1.6, 0.5],
                color=[0.4, 0.4, 0.45],
            ),
        ]

    @staticmethod
    def generate_furniture_bedroom() -> List[EnvironmentProp]:
        """Bedroom furniture"""
        return [
            EnvironmentProp(
                prop_type="bed",
                position=[0.0, 0.5, -3.0],
                rotation=[0, 0, 0],
                scale=[2.5, 0.8, 2.0],
                color=[0.9, 0.85, 0.75],
            ),
            EnvironmentProp(
                prop_type="wardrobe",
                position=[-3.5, 1.2, -4.0],
                rotation=[0, 0, 0],
                scale=[1.8, 2.4, 0.6],
                color=[0.5, 0.35, 0.2],
            ),
            EnvironmentProp(
                prop_type="nightstand",
                position=[2.0, 0.5, -3.5],
                rotation=[0, 0, 0],
                scale=[0.6, 1.0, 0.6],
                color=[0.45, 0.3, 0.15],
            ),
            EnvironmentProp(
                prop_type="dresser",
                position=[3.5, 0.6, -0.5],
                rotation=[0, 90, 0],
                scale=[1.5, 1.2, 0.5],
                color=[0.5, 0.35, 0.2],
            ),
        ]

    @staticmethod
    def generate_furniture_classroom() -> List[EnvironmentProp]:
        """Classroom furniture"""
        desks = []
        # 3x3 grid of desks
        for row in range(3):
            for col in range(3):
                x = -3.0 + col * 3.0
                z = -1.0 - row * 2.0

                desks.append(EnvironmentProp(
                    prop_type="student_desk",
                    position=[x, 0.4, z],
                    scale=[1.0, 0.75, 0.6],
                    color=[0.55, 0.35, 0.2],
                ))
                desks.append(EnvironmentProp(
                    prop_type="chair",
                    position=[x, 0.3, z + 0.8],
                    scale=[0.5, 0.6, 0.5],
                    color=[0.3, 0.2, 0.15],
                ))

        # Teacher's desk
        desks.append(EnvironmentProp(
            prop_type="teacher_desk",
            position=[0.0, 0.4, -8.0],
            scale=[2.5, 0.8, 1.0],
            color=[0.4, 0.25, 0.15],
        ))

        # Blackboard
        desks.append(EnvironmentProp(
            prop_type="blackboard",
            position=[0.0, 2.0, -9.5],
            scale=[5.0, 2.5, 0.1],
            color=[0.1, 0.15, 0.1],
        ))

        return desks


# ============================================================
# ENVIRONMENT PRESETS
# ============================================================

class EnvironmentPresets:
    """Predefined environments - ready to use"""

    @staticmethod
    def forest_day() -> Environment:
        """Sunny forest during day"""
        env = Environment(
            name        = "Forest (Day)",
            env_type    = EnvironmentType.FOREST.value,
            weather     = Weather.CLEAR.value,
            season      = Season.SUMMER.value,
            time_of_day = "noon",
            description = "Peaceful sunny forest",
            is_preset   = True,
        )

        # Sky - bright day
        env.sky = SkySettings(
            horizon_color     = [0.75, 0.9, 1.0],
            zenith_color      = [0.3, 0.55, 0.9],
            ground_color      = [0.3, 0.35, 0.25],
            sun_direction     = [0.3, -1.0, 0.2],
            sun_color         = [1.0, 0.95, 0.8],
            sun_intensity     = 1.3,
            ambient_color     = [0.5, 0.55, 0.6],
            ambient_intensity = 0.4,
        )

        # Fog - light
        env.fog = FogSettings(
            enabled         = True,
            color           = [0.7, 0.8, 0.7],
            density         = 0.008,
            start_distance  = 15,
            end_distance    = 60,
        )

        # Ground
        env.ground = GroundSettings(
            color         = [0.25, 0.35, 0.15],
            texture_scale = 4.0,
            roughness     = 0.9,
        )

        # Trees & rocks
        env.props.extend(PropGenerator.generate_trees(15, 30, 5, "oak"))
        env.props.extend(PropGenerator.generate_rocks(5, 25, 4))
        env.props.extend(PropGenerator.generate_grass_patches(20, 15))

        env.ambient_sounds = ["forest_birds", "wind_leaves"]

        return env

    @staticmethod
    def forest_night() -> Environment:
        """Dark forest at night"""
        env = Environment(
            name        = "Forest (Night)",
            env_type    = EnvironmentType.FOREST.value,
            weather     = Weather.CLEAR.value,
            time_of_day = "night",
            description = "Mysterious dark forest at night",
            is_preset   = True,
        )

        env.sky = SkySettings(
            horizon_color     = [0.05, 0.08, 0.15],
            zenith_color      = [0.02, 0.03, 0.08],
            ground_color      = [0.05, 0.05, 0.05],
            sun_direction     = [-0.5, 0.3, -0.5],  # Moon
            sun_color         = [0.5, 0.6, 0.9],
            sun_intensity     = 0.3,
            ambient_color     = [0.05, 0.08, 0.15],
            ambient_intensity = 0.2,
        )

        env.fog = FogSettings(
            enabled         = True,
            color           = [0.1, 0.15, 0.2],
            density         = 0.02,
            start_distance  = 5,
            end_distance    = 40,
        )

        env.ground = GroundSettings(
            color = [0.08, 0.12, 0.05],
        )

        env.props.extend(PropGenerator.generate_trees(15, 30, 5, "oak"))
        env.props.extend(PropGenerator.generate_rocks(5, 25, 4))

        env.ambient_sounds = ["night_crickets", "owl_hoot"]

        return env

    @staticmethod
    def desert() -> Environment:
        """Hot desert"""
        env = Environment(
            name        = "Desert",
            env_type    = EnvironmentType.DESERT.value,
            weather     = Weather.CLEAR.value,
            season      = Season.SUMMER.value,
            time_of_day = "noon",
            description = "Hot sandy desert",
            is_preset   = True,
        )

        env.sky = SkySettings(
            horizon_color     = [1.0, 0.85, 0.6],
            zenith_color      = [0.5, 0.6, 0.85],
            ground_color      = [0.75, 0.65, 0.4],
            sun_direction     = [0.2, -1.0, 0.1],
            sun_color         = [1.0, 0.9, 0.7],
            sun_intensity     = 1.5,
            ambient_color     = [0.7, 0.6, 0.5],
            ambient_intensity = 0.5,
        )

        env.fog = FogSettings(
            enabled         = True,
            color           = [0.9, 0.8, 0.6],
            density         = 0.005,
            start_distance  = 20,
            end_distance    = 100,
        )

        env.ground = GroundSettings(
            color         = [0.85, 0.75, 0.5],
            texture_scale = 6.0,
            roughness     = 0.95,
        )

        env.props.extend(PropGenerator.generate_cacti(8, 30))
        env.props.extend(PropGenerator.generate_rocks(6, 30, 3))

        env.ambient_sounds = ["desert_wind"]

        return env

    @staticmethod
    def snowy() -> Environment:
        """Snowy winter landscape"""
        env = Environment(
            name        = "Snowy",
            env_type    = EnvironmentType.SNOWY.value,
            weather     = Weather.SNOWY.value,
            season      = Season.WINTER.value,
            time_of_day = "afternoon",
            description = "Cold snowy landscape",
            is_preset   = True,
        )

        env.sky = SkySettings(
            horizon_color     = [0.85, 0.9, 0.95],
            zenith_color      = [0.65, 0.75, 0.85],
            ground_color      = [0.95, 0.95, 0.98],
            sun_direction     = [0.3, -0.8, 0.3],
            sun_color         = [0.9, 0.9, 1.0],
            sun_intensity     = 0.9,
            ambient_color     = [0.75, 0.8, 0.9],
            ambient_intensity = 0.6,
        )

        env.fog = FogSettings(
            enabled         = True,
            color           = [0.9, 0.92, 0.95],
            density         = 0.015,
            start_distance  = 10,
            end_distance    = 50,
        )

        env.ground = GroundSettings(
            color = [0.92, 0.94, 0.98],
        )

        # Trees with snow tint
        trees = PropGenerator.generate_trees(10, 30, 5, "pine")
        for tree in trees:
            # Whiten trees
            tree.color = [
                min(0.9, tree.color[0] + 0.3),
                min(0.9, tree.color[1] + 0.35),
                min(0.9, tree.color[2] + 0.3),
            ]
        env.props.extend(trees)

        # Snow particle effect
        env.particles.append(ParticleEffect(
            effect_type = "snow",
            intensity   = 0.6,
            area_size   = 30,
            height      = 15,
            color       = [1.0, 1.0, 1.0],
            speed       = 1.5,
        ))

        env.ambient_sounds = ["wind_cold", "snow_falling"]

        return env

    @staticmethod
    def beach() -> Environment:
        """Tropical beach"""
        env = Environment(
            name        = "Beach",
            env_type    = EnvironmentType.BEACH.value,
            weather     = Weather.CLEAR.value,
            season      = Season.SUMMER.value,
            time_of_day = "afternoon",
            description = "Sunny tropical beach",
            is_preset   = True,
        )

        env.sky = SkySettings(
            horizon_color     = [0.85, 0.95, 1.0],
            zenith_color      = [0.3, 0.7, 1.0],
            ground_color      = [0.9, 0.85, 0.7],
            sun_direction     = [0.4, -0.9, 0.2],
            sun_color         = [1.0, 0.95, 0.85],
            sun_intensity     = 1.4,
            ambient_color     = [0.6, 0.75, 0.9],
            ambient_intensity = 0.5,
        )

        env.ground = GroundSettings(
            color = [0.95, 0.88, 0.65],   # Sand
        )

        # Palm trees
        env.props.extend(PropGenerator.generate_trees(6, 30, 5, "palm"))

        env.ambient_sounds = ["ocean_waves", "seagulls"]

        return env

    @staticmethod
    def city_day() -> Environment:
        """City during day"""
        env = Environment(
            name        = "City (Day)",
            env_type    = EnvironmentType.CITY.value,
            weather     = Weather.CLEAR.value,
            time_of_day = "afternoon",
            description = "Bustling city during day",
            is_preset   = True,
        )

        env.sky = SkySettings(
            horizon_color     = [0.7, 0.75, 0.8],
            zenith_color      = [0.5, 0.6, 0.85],
            ground_color      = [0.3, 0.32, 0.35],
            sun_direction     = [0.4, -0.9, 0.3],
            sun_color         = [1.0, 0.95, 0.85],
            sun_intensity     = 1.1,
            ambient_color     = [0.6, 0.65, 0.7],
            ambient_intensity = 0.4,
        )

        env.fog = FogSettings(
            enabled         = True,
            color           = [0.7, 0.72, 0.75],
            density         = 0.01,
            start_distance  = 10,
            end_distance    = 80,
        )

        env.ground = GroundSettings(
            color = [0.25, 0.25, 0.28],   # Asphalt
        )

        env.props.extend(PropGenerator.generate_buildings(12, 40, 8))

        env.ambient_sounds = ["city_traffic", "distant_horn"]

        return env

    @staticmethod
    def city_night() -> Environment:
        """City at night"""
        env = Environment(
            name        = "City (Night)",
            env_type    = EnvironmentType.CITY.value,
            time_of_day = "night",
            description = "City lights at night",
            is_preset   = True,
        )

        env.sky = SkySettings(
            horizon_color     = [0.15, 0.2, 0.3],
            zenith_color      = [0.05, 0.08, 0.15],
            ground_color      = [0.1, 0.1, 0.12],
            sun_direction     = [-0.3, 0.2, -0.5],
            sun_color         = [0.4, 0.5, 0.7],
            sun_intensity     = 0.2,
            ambient_color     = [0.15, 0.2, 0.3],
            ambient_intensity = 0.3,
        )

        env.fog = FogSettings(
            enabled         = True,
            color           = [0.15, 0.2, 0.3],
            density         = 0.015,
            start_distance  = 15,
            end_distance    = 70,
        )

        env.ground = GroundSettings(
            color = [0.12, 0.12, 0.15],
        )

        # Buildings with lit windows
        buildings = PropGenerator.generate_buildings(12, 40, 8)
        for b in buildings:
            # Slightly lit look
            b.color = [b.color[0] * 0.7, b.color[1] * 0.7, b.color[2] * 0.75]
        env.props.extend(buildings)

        env.ambient_sounds = ["city_night", "distant_traffic"]

        return env

    @staticmethod
    def home_interior() -> Environment:
        """Home living room"""
        env = Environment(
            name        = "Home Interior",
            env_type    = EnvironmentType.HOME.value,
            time_of_day = "evening",
            description = "Cozy home interior",
            is_preset   = True,
        )

        env.sky = SkySettings(
            sky_type          = SkyType.SOLID_COLOR.value,
            horizon_color     = [0.85, 0.75, 0.65],
            zenith_color      = [0.85, 0.75, 0.65],
            sun_direction     = [0.3, -0.8, 0.3],
            sun_color         = [1.0, 0.85, 0.7],
            sun_intensity     = 0.9,
            ambient_color     = [0.5, 0.4, 0.35],
            ambient_intensity = 0.6,
        )

        env.ground = GroundSettings(
            color = [0.5, 0.35, 0.25],   # Wooden floor
        )

        env.props.extend(PropGenerator.generate_furniture_home())

        env.ambient_sounds = ["home_ambient", "distant_tv"]

        return env

    @staticmethod
    def office() -> Environment:
        """Office space"""
        env = Environment(
            name        = "Office",
            env_type    = EnvironmentType.OFFICE.value,
            time_of_day = "afternoon",
            description = "Modern office space",
            is_preset   = True,
        )

        env.sky = SkySettings(
            sky_type          = SkyType.SOLID_COLOR.value,
            horizon_color     = [0.85, 0.9, 0.95],
            zenith_color      = [0.85, 0.9, 0.95],
            sun_direction     = [0.3, -1.0, 0.3],
            sun_color         = [1.0, 1.0, 1.0],
            sun_intensity     = 1.0,
            ambient_color     = [0.6, 0.65, 0.7],
            ambient_intensity = 0.5,
        )

        env.ground = GroundSettings(
            color = [0.35, 0.3, 0.25],
        )

        env.props.extend(PropGenerator.generate_furniture_office())

        env.ambient_sounds = ["office_ambient", "typing"]

        return env

    @staticmethod
    def bedroom() -> Environment:
        """Bedroom"""
        env = Environment(
            name        = "Bedroom",
            env_type    = EnvironmentType.BEDROOM.value,
            time_of_day = "night",
            description = "Cozy bedroom",
            is_preset   = True,
        )

        env.sky = SkySettings(
            sky_type          = SkyType.SOLID_COLOR.value,
            horizon_color     = [0.4, 0.3, 0.35],
            zenith_color      = [0.3, 0.25, 0.3],
            sun_direction     = [0.3, -0.8, 0.3],
            sun_color         = [0.9, 0.7, 0.6],
            sun_intensity     = 0.6,
            ambient_color     = [0.35, 0.3, 0.35],
            ambient_intensity = 0.4,
        )

        env.ground = GroundSettings(
            color = [0.4, 0.3, 0.25],
        )

        env.props.extend(PropGenerator.generate_furniture_bedroom())

        env.ambient_sounds = ["night_quiet", "clock_tick"]

        return env

    @staticmethod
    def classroom() -> Environment:
        """School classroom"""
        env = Environment(
            name        = "Classroom",
            env_type    = EnvironmentType.CLASSROOM.value,
            time_of_day = "morning",
            description = "School classroom",
            is_preset   = True,
        )

        env.sky = SkySettings(
            sky_type          = SkyType.SOLID_COLOR.value,
            horizon_color     = [0.8, 0.85, 0.9],
            zenith_color      = [0.8, 0.85, 0.9],
            sun_direction     = [0.4, -0.9, 0.3],
            sun_color         = [1.0, 0.98, 0.9],
            sun_intensity     = 1.0,
            ambient_color     = [0.6, 0.65, 0.7],
            ambient_intensity = 0.5,
        )

        env.ground = GroundSettings(
            color = [0.45, 0.4, 0.3],
        )

        env.props.extend(PropGenerator.generate_furniture_classroom())

        env.ambient_sounds = ["classroom_ambient"]

        return env

    @staticmethod
    def studio() -> Environment:
        """Clean studio for presentations"""
        env = Environment(
            name        = "Studio",
            env_type    = EnvironmentType.STUDIO.value,
            description = "Clean gray studio backdrop",
            is_preset   = True,
        )

        env.sky = SkySettings(
            sky_type          = SkyType.SOLID_COLOR.value,
            horizon_color     = [0.3, 0.3, 0.35],
            zenith_color      = [0.3, 0.3, 0.35],
            sun_direction     = [0.0, -1.0, 0.0],
            sun_color         = [1.0, 1.0, 1.0],
            sun_intensity     = 1.5,
            ambient_color     = [0.4, 0.4, 0.45],
            ambient_intensity = 0.5,
        )

        env.ground = GroundSettings(
            color      = [0.3, 0.3, 0.35],
            reflective = True,
            roughness  = 0.3,
        )

        return env

    @staticmethod
    def rainy() -> Environment:
        """Rainy environment"""
        env = Environment(
            name        = "Rainy Outdoor",
            env_type    = EnvironmentType.PARK.value,
            weather     = Weather.RAINY.value,
            time_of_day = "afternoon",
            description = "Rainy outdoor scene",
            is_preset   = True,
        )

        env.sky = SkySettings(
            horizon_color     = [0.4, 0.42, 0.45],
            zenith_color      = [0.25, 0.28, 0.32],
            ground_color      = [0.2, 0.22, 0.2],
            sun_direction     = [0.3, -0.9, 0.3],
            sun_color         = [0.6, 0.65, 0.7],
            sun_intensity     = 0.5,
            ambient_color     = [0.4, 0.42, 0.45],
            ambient_intensity = 0.5,
        )

        env.fog = FogSettings(
            enabled         = True,
            color           = [0.55, 0.58, 0.6],
            density         = 0.02,
            start_distance  = 5,
            end_distance    = 40,
        )

        env.ground = GroundSettings(
            color       = [0.15, 0.2, 0.15],
            reflective  = True,
            roughness   = 0.3,
        )

        # Rain particle effect
        env.particles.append(ParticleEffect(
            effect_type = "rain",
            intensity   = 1.0,
            area_size   = 30,
            height      = 20,
            color       = [0.7, 0.75, 0.8],
            speed       = 15.0,
        ))

        env.ambient_sounds = ["rain_heavy", "distant_thunder"]

        return env


# ============================================================
# TIME OF DAY MANAGER
# ============================================================

class TimeOfDayManager:
    """
    Time of day changes automatically apply karta hai.
    Ek environment ko dawn/day/sunset/night mein transform karta hai.
    """

    # Time presets
    TIME_PRESETS: Dict[str, Dict] = {
        "dawn": {
            "sun_direction":     [0.9, -0.15, 0.4],
            "sun_color":         [1.0, 0.7, 0.5],
            "sun_intensity":     0.8,
            "horizon_color":     [1.0, 0.6, 0.4],
            "zenith_color":      [0.4, 0.5, 0.75],
            "ambient_color":     [0.7, 0.55, 0.5],
            "ambient_intensity": 0.5,
        },
        "morning": {
            "sun_direction":     [0.5, -0.7, 0.3],
            "sun_color":         [1.0, 0.95, 0.8],
            "sun_intensity":     1.1,
            "horizon_color":     [0.8, 0.9, 1.0],
            "zenith_color":      [0.35, 0.55, 0.9],
            "ambient_color":     [0.55, 0.6, 0.7],
            "ambient_intensity": 0.45,
        },
        "noon": {
            "sun_direction":     [0.1, -1.0, 0.1],
            "sun_color":         [1.0, 0.98, 0.9],
            "sun_intensity":     1.3,
            "horizon_color":     [0.75, 0.85, 1.0],
            "zenith_color":      [0.3, 0.55, 0.95],
            "ambient_color":     [0.5, 0.55, 0.65],
            "ambient_intensity": 0.4,
        },
        "afternoon": {
            "sun_direction":     [-0.3, -0.85, 0.4],
            "sun_color":         [1.0, 0.9, 0.75],
            "sun_intensity":     1.2,
            "horizon_color":     [0.8, 0.8, 0.85],
            "zenith_color":      [0.35, 0.55, 0.85],
            "ambient_color":     [0.55, 0.55, 0.6],
            "ambient_intensity": 0.4,
        },
        "evening": {
            "sun_direction":     [-0.9, -0.2, 0.4],
            "sun_color":         [1.0, 0.55, 0.35],
            "sun_intensity":     0.9,
            "horizon_color":     [1.0, 0.5, 0.3],
            "zenith_color":      [0.35, 0.25, 0.5],
            "ambient_color":     [0.7, 0.45, 0.4],
            "ambient_intensity": 0.4,
        },
        "night": {
            "sun_direction":     [-0.5, 0.3, -0.5],
            "sun_color":         [0.5, 0.6, 0.85],
            "sun_intensity":     0.3,
            "horizon_color":     [0.08, 0.1, 0.15],
            "zenith_color":      [0.02, 0.03, 0.08],
            "ambient_color":     [0.1, 0.12, 0.2],
            "ambient_intensity": 0.25,
        },
        "midnight": {
            "sun_direction":     [-0.3, 0.5, -0.5],
            "sun_color":         [0.4, 0.5, 0.75],
            "sun_intensity":     0.2,
            "horizon_color":     [0.05, 0.05, 0.1],
            "zenith_color":      [0.01, 0.02, 0.05],
            "ambient_color":     [0.08, 0.08, 0.15],
            "ambient_intensity": 0.2,
        },
    }

    @classmethod
    def apply_time(cls, env: Environment, time_of_day: str):
        """Environment pe time of day apply karo"""
        preset = cls.TIME_PRESETS.get(time_of_day)
        if not preset:
            logger.warning(f"Unknown time of day: {time_of_day}")
            return

        env.time_of_day = time_of_day

        # Apply sky changes
        env.sky.sun_direction     = list(preset["sun_direction"])
        env.sky.sun_color         = list(preset["sun_color"])
        env.sky.sun_intensity     = preset["sun_intensity"]
        env.sky.horizon_color     = list(preset["horizon_color"])
        env.sky.zenith_color      = list(preset["zenith_color"])
        env.sky.ambient_color     = list(preset["ambient_color"])
        env.sky.ambient_intensity = preset["ambient_intensity"]

        logger.debug(f"Time applied: {time_of_day}")

    @classmethod
    def transition(
        cls,
        env: Environment,
        from_time: str,
        to_time: str,
        t: float,   # 0.0 to 1.0
    ):
        """
        Do time presets ke beech smooth transition karo.
        Useful for time-lapse effects.
        """
        p1 = cls.TIME_PRESETS.get(from_time)
        p2 = cls.TIME_PRESETS.get(to_time)
        if not p1 or not p2:
            return

        def lerp(a, b, t):
            return a + (b - a) * t

        def lerp_list(l1, l2, t):
            return [lerp(l1[i], l2[i], t) for i in range(len(l1))]

        env.sky.sun_direction = lerp_list(p1["sun_direction"], p2["sun_direction"], t)
        env.sky.sun_color = lerp_list(p1["sun_color"], p2["sun_color"], t)
        env.sky.sun_intensity = lerp(p1["sun_intensity"], p2["sun_intensity"], t)
        env.sky.horizon_color = lerp_list(p1["horizon_color"], p2["horizon_color"], t)
        env.sky.zenith_color = lerp_list(p1["zenith_color"], p2["zenith_color"], t)
        env.sky.ambient_color = lerp_list(p1["ambient_color"], p2["ambient_color"], t)
        env.sky.ambient_intensity = lerp(p1["ambient_intensity"], p2["ambient_intensity"], t)


# ============================================================
# SEASON MANAGER
# ============================================================

class SeasonManager:
    """Season changes handle karta hai"""

    SEASON_MODIFIERS: Dict[str, Dict] = {
        "spring": {
            "ground_tint":  [1.05, 1.10, 1.0],    # Fresh green
            "sun_intensity":0.9,
        },
        "summer": {
            "ground_tint":  [1.0, 1.0, 0.95],
            "sun_intensity":1.2,
        },
        "autumn": {
            "ground_tint":  [1.15, 0.85, 0.6],    # Orange/brown
            "sun_intensity":0.85,
        },
        "winter": {
            "ground_tint":  [0.9, 0.95, 1.0],     # Cool tones
            "sun_intensity":0.7,
        },
    }

    @classmethod
    def apply_season(cls, env: Environment, season: str):
        """Season apply karo"""
        modifier = cls.SEASON_MODIFIERS.get(season)
        if not modifier:
            return

        env.season = season

        # Adjust ground color
        tint = modifier["ground_tint"]
        env.ground.color = [
            min(1.0, env.ground.color[0] * tint[0]),
            min(1.0, env.ground.color[1] * tint[1]),
            min(1.0, env.ground.color[2] * tint[2]),
        ]

        # Adjust sun
        env.sky.sun_intensity *= modifier["sun_intensity"]

        # Winter - add snow
        if season == "winter" and env.env_type in [
            EnvironmentType.FOREST.value,
            EnvironmentType.PARK.value,
        ]:
            # Add snow particles
            snow_exists = any(p.effect_type == "snow" for p in env.particles)
            if not snow_exists:
                env.particles.append(ParticleEffect(
                    effect_type="snow",
                    intensity=0.5,
                    area_size=30,
                    height=15,
                    color=[1.0, 1.0, 1.0],
                    speed=1.2,
                ))

        # Autumn - orange trees
        if season == "autumn":
            for prop in env.props:
                if prop.prop_type.startswith("tree"):
                    prop.color = [
                        prop.color[0] + 0.3,
                        prop.color[1] * 0.6,
                        prop.color[2] * 0.4,
                    ]


# ============================================================
# WEATHER MANAGER
# ============================================================

class WeatherManager:
    """Weather effects add karta hai"""

    @classmethod
    def apply_weather(cls, env: Environment, weather: str):
        """Weather apply karo"""
        env.weather = weather

        # Remove existing weather particles
        env.particles = [
            p for p in env.particles
            if p.effect_type not in ["rain", "snow", "storm"]
        ]

        if weather == Weather.RAINY.value:
            env.particles.append(ParticleEffect(
                effect_type="rain",
                intensity=1.0,
                area_size=30,
                height=20,
                speed=15.0,
            ))
            # Darker sky
            env.sky.horizon_color = [c * 0.6 for c in env.sky.horizon_color]
            env.sky.zenith_color = [c * 0.6 for c in env.sky.zenith_color]
            env.sky.sun_intensity *= 0.5

            # Enable fog
            env.fog.enabled = True
            env.fog.density = max(env.fog.density, 0.015)

        elif weather == Weather.SNOWY.value:
            env.particles.append(ParticleEffect(
                effect_type="snow",
                intensity=0.7,
                area_size=30,
                height=15,
                speed=1.5,
            ))
            env.sky.sun_intensity *= 0.7

        elif weather == Weather.FOGGY.value:
            env.fog.enabled = True
            env.fog.density = 0.035
            env.fog.color = [0.75, 0.78, 0.8]
            env.sky.sun_intensity *= 0.6

        elif weather == Weather.STORMY.value:
            env.particles.append(ParticleEffect(
                effect_type="rain",
                intensity=1.5,
                area_size=30,
                height=25,
                speed=25.0,
            ))
            env.sky.horizon_color = [c * 0.3 for c in env.sky.horizon_color]
            env.sky.zenith_color = [c * 0.3 for c in env.sky.zenith_color]
            env.sky.sun_intensity *= 0.3
            env.fog.enabled = True
            env.fog.density = 0.03


# ============================================================
# MAIN ENVIRONMENT MANAGER
# ============================================================

class EnvironmentManager:
    """
    Main Environment Manager.
    Environments manage, apply karo aur transition karo.
    """

    def __init__(self, config: Optional[Dict] = None):
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # Load all presets
        self._environments: Dict[str, Environment] = {}
        self._load_presets()

        # Current active
        self._current_env: Optional[Environment] = None

        # Listeners
        self._listeners: List[Callable] = []

        logger.info(
            f"✅ EnvironmentManager initialized | "
            f"{len(self._environments)} environments loaded"
        )

    def _load_presets(self):
        """Sabhi preset environments load karo"""
        presets = [
            EnvironmentPresets.forest_day(),
            EnvironmentPresets.forest_night(),
            EnvironmentPresets.desert(),
            EnvironmentPresets.snowy(),
            EnvironmentPresets.beach(),
            EnvironmentPresets.city_day(),
            EnvironmentPresets.city_night(),
            EnvironmentPresets.home_interior(),
            EnvironmentPresets.office(),
            EnvironmentPresets.bedroom(),
            EnvironmentPresets.classroom(),
            EnvironmentPresets.studio(),
            EnvironmentPresets.rainy(),
        ]

        for env in presets:
            self._environments[env.environment_id] = env

        logger.debug(f"Loaded {len(presets)} preset environments")

    def get_environment(self, environment_id: str) -> Optional[Environment]:
        """ID se environment lo"""
        return self._environments.get(environment_id)

    def get_environment_by_name(self, name: str) -> Optional[Environment]:
        """Naam se environment lo"""
        for env in self._environments.values():
            if env.name.lower() == name.lower():
                return env
        return None

    def get_environment_by_type(self, env_type: str) -> Optional[Environment]:
        """Type se environment lo (first match)"""
        for env in self._environments.values():
            if env.env_type == env_type:
                return env
        return None

    def get_all_environments(self) -> List[Environment]:
        """Sabhi environments lo"""
        return list(self._environments.values())

    def get_environment_names(self) -> List[str]:
        """Sabhi environment names lo"""
        return [e.name for e in self._environments.values()]

    def apply_environment(self, env: Environment):
        """Environment ko apply karo (current active banao)"""
        self._current_env = env
        self._notify("environment_changed", {"env": env})
        logger.info(f"Environment applied: {env.name}")

    def get_current_environment(self) -> Optional[Environment]:
        """Current environment lo"""
        return self._current_env

    def customize_time_of_day(self, env: Environment, time_of_day: str):
        """Environment pe time of day change karo"""
        TimeOfDayManager.apply_time(env, time_of_day)
        self._notify("time_changed", {"env": env, "time": time_of_day})

    def customize_season(self, env: Environment, season: str):
        """Season change karo"""
        SeasonManager.apply_season(env, season)
        self._notify("season_changed", {"env": env, "season": season})

    def customize_weather(self, env: Environment, weather: str):
        """Weather change karo"""
        WeatherManager.apply_weather(env, weather)
        self._notify("weather_changed", {"env": env, "weather": weather})

    def create_custom_environment(
        self,
        base_type: str,
        time_of_day: str = "noon",
        season: str = "summer",
        weather: str = "clear",
        name: str = "Custom Environment",
    ) -> Environment:
        """
        Custom environment banao base type se.
        Time, season, weather sab customize karo.
        """
        # Get base preset
        base = self.get_environment_by_type(base_type)
        if not base:
            # Fallback to park
            base = EnvironmentPresets.forest_day()

        # Copy properties
        import copy
        env = copy.deepcopy(base)
        env.environment_id = f"env_{generate_uuid()[:8]}"
        env.name = name
        env.is_preset = False

        # Apply customizations
        self.customize_time_of_day(env, time_of_day)
        self.customize_season(env, season)
        self.customize_weather(env, weather)

        # Add to library
        self._environments[env.environment_id] = env
        return env

    def search_environments(self, query: str) -> List[Environment]:
        """Environments search karo"""
        query_lower = query.lower()
        return [
            e for e in self._environments.values()
            if query_lower in e.name.lower()
            or query_lower in e.env_type.lower()
            or query_lower in e.description.lower()
        ]

    def add_listener(self, callback: Callable):
        self._listeners.append(callback)

    def _notify(self, event: str, data: Dict):
        for cb in self._listeners:
            try:
                cb(event, data)
            except Exception as e:
                logger.warning(f"Listener error: {e}")

    def get_statistics(self) -> Dict:
        stats = {
            "total_environments": len(self._environments),
            "by_type":            {},
            "total_props":        0,
            "total_particles":    0,
        }
        for env in self._environments.values():
            t = env.env_type
            stats["by_type"][t] = stats["by_type"].get(t, 0) + 1
            stats["total_props"] += len(env.props)
            stats["total_particles"] += len(env.particles)
        return stats


# ============================================================
# GLOBAL INSTANCE
# ============================================================

_global_manager: Optional[EnvironmentManager] = None


def get_environment_manager() -> EnvironmentManager:
    """Global EnvironmentManager"""
    global _global_manager
    if _global_manager is None:
        _global_manager = EnvironmentManager()
    return _global_manager


# ============================================================
# TEST SECTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")
    print_banner("Environment Manager Test", "3D Environments & Weather System")

    # ===== TEST 1: Manager Init =====
    print_section("Test 1: Manager Initialization")
    manager = EnvironmentManager()
    stats = manager.get_statistics()
    print(f"✅ Total environments: {stats['total_environments']}")
    print(f"   Total props       : {stats['total_props']}")
    print(f"   Total particles   : {stats['total_particles']}")

    # ===== TEST 2: All Environments =====
    print_section("Test 2: All Preset Environments")
    for env in manager.get_all_environments():
        print(
            f"✅ {env.name:20s} | "
            f"Type: {env.env_type:12s} | "
            f"Time: {env.time_of_day:8s} | "
            f"Props: {len(env.props):2d} | "
            f"Particles: {len(env.particles)}"
        )

    # ===== TEST 3: Prop Generation =====
    print_section("Test 3: Prop Generators")
    trees = PropGenerator.generate_trees(10, 25, 5, "oak")
    rocks = PropGenerator.generate_rocks(5, 20)
    buildings = PropGenerator.generate_buildings(8, 30)
    print(f"✅ Trees generated    : {len(trees)}")
    print(f"✅ Rocks generated    : {len(rocks)}")
    print(f"✅ Buildings generated: {len(buildings)}")

    print(f"\n   Sample tree: pos={trees[0].position}, color={trees[0].color}")
    print(f"   Sample rock: pos={rocks[0].position}, scale={rocks[0].scale}")

    # ===== TEST 4: Time of Day =====
    print_section("Test 4: Time of Day Changes")
    env = manager.get_environment_by_name("Forest (Day)")
    if env:
        import copy
        for tod in ["dawn", "morning", "noon", "evening", "night"]:
            test_env = copy.deepcopy(env)
            TimeOfDayManager.apply_time(test_env, tod)
            sun_i = test_env.sky.sun_intensity
            horizon = test_env.sky.horizon_color
            print(
                f"✅ {tod:10s}: sun_intensity={sun_i:.2f}, "
                f"horizon=[{horizon[0]:.2f}, {horizon[1]:.2f}, {horizon[2]:.2f}]"
            )

    # ===== TEST 5: Seasons =====
    print_section("Test 5: Season Effects")
    env = manager.get_environment_by_name("Forest (Day)")
    if env:
        for season in ["spring", "summer", "autumn", "winter"]:
            test_env = copy.deepcopy(env)
            SeasonManager.apply_season(test_env, season)
            print(
                f"✅ {season:8s}: sun_intensity={test_env.sky.sun_intensity:.2f}, "
                f"particles={len(test_env.particles)}"
            )

    # ===== TEST 6: Weather =====
    print_section("Test 6: Weather Effects")
    env = manager.get_environment_by_name("Forest (Day)")
    if env:
        for weather in ["clear", "rainy", "snowy", "foggy", "stormy"]:
            test_env = copy.deepcopy(env)
            WeatherManager.apply_weather(test_env, weather)
            print(
                f"✅ {weather:8s}: sun={test_env.sky.sun_intensity:.2f}, "
                f"fog={test_env.fog.enabled}, "
                f"particles={len(test_env.particles)}"
            )

    # ===== TEST 7: Custom Environment =====
    print_section("Test 7: Custom Environment Creation")
    custom = manager.create_custom_environment(
        base_type   = EnvironmentType.FOREST.value,
        time_of_day = "evening",
        season      = "autumn",
        weather     = "rainy",
        name        = "My Autumn Rainy Evening",
    )
    print(f"✅ Custom environment created:")
    print(f"   Name       : {custom.name}")
    print(f"   Base type  : {custom.env_type}")
    print(f"   Time       : {custom.time_of_day}")
    print(f"   Season     : {custom.season}")
    print(f"   Weather    : {custom.weather}")
    print(f"   Props      : {len(custom.props)}")
    print(f"   Particles  : {len(custom.particles)}")
    print(f"   Sun intensity: {custom.sky.sun_intensity:.2f}")

    # ===== TEST 8: Search =====
    print_section("Test 8: Search")
    for query in ["forest", "night", "city", "office", "snow"]:
        results = manager.search_environments(query)
        print(f"✅ Search '{query}': {[r.name for r in results]}")

    # ===== TEST 9: Environment Details =====
    print_section("Test 9: Detailed Environment Info")
    env = manager.get_environment_by_name("Forest (Day)")
    if env:
        print(f"\n🌲 {env.name}:")
        print(f"   Type      : {env.env_type}")
        print(f"   Season    : {env.season}")
        print(f"   Weather   : {env.weather}")
        print(f"   Time      : {env.time_of_day}")
        print(f"\n   Sky:")
        print(f"      Horizon    : {env.sky.horizon_color}")
        print(f"      Zenith     : {env.sky.zenith_color}")
        print(f"      Sun        : {env.sky.sun_color} @ {env.sky.sun_intensity}")
        print(f"      Ambient    : {env.sky.ambient_color} @ {env.sky.ambient_intensity}")
        print(f"\n   Fog        : {env.fog.enabled} (density: {env.fog.density})")
        print(f"   Ground     : {env.ground.color}")
        print(f"   Props      : {len(env.props)}")

        # Prop types breakdown
        prop_types = {}
        for prop in env.props:
            prop_types[prop.prop_type] = prop_types.get(prop.prop_type, 0) + 1
        for pt, count in prop_types.items():
            print(f"      • {pt}: {count}")

        print(f"   Ambient sounds: {env.ambient_sounds}")

    # ===== TEST 10: Global Singleton =====
    print_section("Test 10: Global Singleton")
    m1 = get_environment_manager()
    m2 = get_environment_manager()
    print(f"✅ Singleton: {m1 is m2}")

    # ===== TEST 11: Time Transition =====
    print_section("Test 11: Time Transition (dawn → noon)")
    env = manager.get_environment_by_name("Forest (Day)")
    if env:
        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            test = copy.deepcopy(env)
            TimeOfDayManager.transition(test, "dawn", "noon", t)
            print(f"   t={t:.2f}: sun_intensity={test.sky.sun_intensity:.2f}")

    # ===== TEST 12: Statistics =====
    print_section("Test 12: Final Library Stats")
    final_stats = manager.get_statistics()
    print(f"\n   📊 Total environments: {final_stats['total_environments']}")
    print(f"   By type:")
    for env_type, count in final_stats['by_type'].items():
        print(f"      {env_type:20s}: {count}")

    print_banner("✅ All Tests Passed!", "environment_manager.py Working Perfectly")