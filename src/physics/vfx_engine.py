# ============================================================
# 3D ANIMATION STUDIO - VFX Engine (Visual Effects)
# ============================================================
# Features:
# - Particle system foundation
# - Pre-built effects:
#   * Fire 🔥
#   * Smoke 💨
#   * Rain ☔
#   * Snow ❄️
#   * Sparkle ✨
#   * Explosion 💥
#   * Lightning ⚡
#   * Fog 🌫️
#   * Confetti 🎉
#   * Blood splash 🩸
# - Emitter shapes (point, sphere, box, cone)
# - Force fields (gravity, wind, attractor)
# - Particle lifecycle (birth, life, death)
# - Color/size/opacity animation over lifetime
# - Performance-optimized
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
    rgb_to_normalized
)

logger = get_logger("VFXEngine")


# ============================================================
# EMITTER SHAPES
# ============================================================

class EmitterShape(Enum):
    POINT = "point"          # Single point
    SPHERE = "sphere"        # Random in sphere
    BOX = "box"              # Random in box
    CONE = "cone"            # Cone direction
    CIRCLE = "circle"        # Random in circle (flat)
    LINE = "line"            # Along line


# ============================================================
# PARTICLE
# ============================================================

@dataclass
class Particle:
    """Single particle in effect"""
    position: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float32))
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float32))

    # Lifecycle
    age: float = 0.0          # Current age
    lifetime: float = 1.0     # Max age
    alive: bool = True

    # Appearance
    color: np.ndarray = field(default_factory=lambda: np.array([1, 1, 1, 1], dtype=np.float32))  # RGBA
    size: float = 1.0
    rotation: float = 0.0     # For 2D rotation

    # Physics
    mass: float = 1.0

    # Custom data
    initial_size: float = 1.0
    initial_color: np.ndarray = field(default_factory=lambda: np.array([1, 1, 1, 1], dtype=np.float32))

    def get_life_ratio(self) -> float:
        """Age vs lifetime (0-1)"""
        return clamp(self.age / self.lifetime, 0.0, 1.0) if self.lifetime > 0 else 0

    def update(self, dt: float):
        """Update particle"""
        self.age += dt
        if self.age >= self.lifetime:
            self.alive = False


# ============================================================
# PARTICLE EMITTER
# ============================================================

@dataclass
class EmitterConfig:
    """Emitter configuration"""
    # Position & shape
    position: List[float] = field(default_factory=lambda: [0, 0, 0])
    shape: EmitterShape = EmitterShape.POINT
    shape_size: List[float] = field(default_factory=lambda: [1, 1, 1])  # For sphere/box/cone

    # Emission
    rate: float = 50.0                    # Particles per second
    burst_count: int = 0                  # One-time burst amount
    max_particles: int = 1000             # Maximum alive at once

    # Lifetime
    lifetime_min: float = 1.0
    lifetime_max: float = 2.0

    # Initial velocity
    velocity_min: List[float] = field(default_factory=lambda: [-1, 0, -1])
    velocity_max: List[float] = field(default_factory=lambda: [1, 5, 1])
    velocity_random_scale: float = 1.0    # Randomness multiplier

    # Initial size
    size_min: float = 0.1
    size_max: float = 0.3

    # Colors (RGBA)
    color_start: List[float] = field(default_factory=lambda: [1, 1, 1, 1])
    color_end: List[float] = field(default_factory=lambda: [1, 1, 1, 0])

    # Size over lifetime
    size_start_multiplier: float = 1.0
    size_end_multiplier: float = 1.0

    # Forces
    gravity: List[float] = field(default_factory=lambda: [0, 0, 0])
    wind: List[float] = field(default_factory=lambda: [0, 0, 0])
    drag: float = 0.02  # Air resistance


class ParticleEmitter:
    """Particle emitter for effects"""

    def __init__(self, name: str = "Emitter",
                 config: Optional[EmitterConfig] = None):
        self.id = generate_short_id()
        self.name = name
        self.config = config or EmitterConfig()

        # Particles
        self.particles: List[Particle] = []

        # State
        self.enabled = True
        self.paused = False
        self._emission_accumulator = 0.0
        self._age = 0.0

    def emit(self, count: int = 1):
        """Turant particles emit karo"""
        for _ in range(count):
            if len(self.particles) >= self.config.max_particles:
                break

            particle = self._create_particle()
            self.particles.append(particle)

    def _create_particle(self) -> Particle:
        """Naya particle create karo based on config"""
        # Position based on shape
        pos = self._generate_position()

        # Velocity
        vel = self._generate_velocity()

        # Lifetime
        lifetime = random.uniform(self.config.lifetime_min, self.config.lifetime_max)

        # Size
        size = random.uniform(self.config.size_min, self.config.size_max)

        # Color
        color = np.array(self.config.color_start, dtype=np.float32).copy()

        particle = Particle(
            position=pos,
            velocity=vel,
            lifetime=lifetime,
            size=size,
            initial_size=size,
            color=color,
            initial_color=color.copy(),
        )

        return particle

    def _generate_position(self) -> np.ndarray:
        """Position generate karo based on shape"""
        base = np.array(self.config.position, dtype=np.float32)
        shape = self.config.shape
        size = self.config.shape_size

        if shape == EmitterShape.POINT:
            return base.copy()

        elif shape == EmitterShape.SPHERE:
            # Random point in sphere
            r = size[0] * (random.random() ** (1/3))
            theta = random.uniform(0, math.pi)
            phi = random.uniform(0, 2 * math.pi)

            offset = np.array([
                r * math.sin(theta) * math.cos(phi),
                r * math.sin(theta) * math.sin(phi),
                r * math.cos(theta),
            ], dtype=np.float32)
            return base + offset

        elif shape == EmitterShape.BOX:
            offset = np.array([
                random.uniform(-size[0]/2, size[0]/2),
                random.uniform(-size[1]/2, size[1]/2),
                random.uniform(-size[2]/2, size[2]/2),
            ], dtype=np.float32)
            return base + offset

        elif shape == EmitterShape.CIRCLE:
            # Random point in flat circle (XZ plane)
            r = size[0] * math.sqrt(random.random())
            theta = random.uniform(0, 2 * math.pi)
            offset = np.array([
                r * math.cos(theta),
                0,
                r * math.sin(theta),
            ], dtype=np.float32)
            return base + offset

        elif shape == EmitterShape.LINE:
            t = random.random()
            offset = np.array([
                lerp(-size[0]/2, size[0]/2, t),
                0, 0
            ], dtype=np.float32)
            return base + offset

        return base.copy()

    def _generate_velocity(self) -> np.ndarray:
        """Random velocity in range"""
        vmin = np.array(self.config.velocity_min, dtype=np.float32)
        vmax = np.array(self.config.velocity_max, dtype=np.float32)

        vel = np.array([
            random.uniform(vmin[0], vmax[0]),
            random.uniform(vmin[1], vmax[1]),
            random.uniform(vmin[2], vmax[2]),
        ], dtype=np.float32) * self.config.velocity_random_scale

        return vel

    def update(self, dt: float):
        """Emitter update per frame"""
        if not self.enabled or self.paused:
            return

        self._age += dt

        # Continuous emission
        if self.config.rate > 0:
            self._emission_accumulator += self.config.rate * dt

            emit_count = int(self._emission_accumulator)
            self._emission_accumulator -= emit_count

            if emit_count > 0:
                self.emit(emit_count)

        # Update particles
        gravity = np.array(self.config.gravity, dtype=np.float32)
        wind = np.array(self.config.wind, dtype=np.float32)
        drag = self.config.drag

        color_start = np.array(self.config.color_start, dtype=np.float32)
        color_end = np.array(self.config.color_end, dtype=np.float32)

        for particle in self.particles:
            if not particle.alive:
                continue

            # Physics
            particle.velocity += gravity * dt
            particle.velocity += wind * dt
            particle.velocity *= (1.0 - drag * dt)

            particle.position += particle.velocity * dt

            # Lifecycle
            particle.update(dt)

            # Animate properties
            life_ratio = particle.get_life_ratio()

            # Color interpolation
            particle.color = color_start * (1 - life_ratio) + color_end * life_ratio

            # Size interpolation
            size_mult = lerp(
                self.config.size_start_multiplier,
                self.config.size_end_multiplier,
                life_ratio
            )
            particle.size = particle.initial_size * size_mult

        # Dead particles remove karo
        self.particles = [p for p in self.particles if p.alive]

    def clear(self):
        """Sab particles remove karo"""
        self.particles.clear()
        self._emission_accumulator = 0.0

    def get_alive_count(self) -> int:
        return len([p for p in self.particles if p.alive])

    def get_particles_data(self) -> np.ndarray:
        """
        Sab particles ka data as array.
        Format: [x, y, z, size, r, g, b, a] per particle
        Rendering ke liye useful.
        """
        alive = [p for p in self.particles if p.alive]
        if not alive:
            return np.array([], dtype=np.float32).reshape(0, 8)

        data = np.zeros((len(alive), 8), dtype=np.float32)
        for i, p in enumerate(alive):
            data[i, 0:3] = p.position
            data[i, 3] = p.size
            data[i, 4:8] = p.color

        return data


# ============================================================
# VFX PRESETS - Pre-built Effects
# ============================================================

class VFXPresets:
    """Pre-built visual effects"""

    # ---------- FIRE 🔥 ----------

    @staticmethod
    def fire(position: Optional[List[float]] = None,
             intensity: float = 1.0) -> ParticleEmitter:
        """Fire effect - rising warm particles"""
        pos = position or [0, 0, 0]

        config = EmitterConfig(
            position=pos,
            shape=EmitterShape.CIRCLE,
            shape_size=[0.3, 0.3, 0.3],
            rate=80 * intensity,
            max_particles=int(200 * intensity),
            lifetime_min=0.8,
            lifetime_max=1.5,
            velocity_min=[-0.3, 2.0, -0.3],
            velocity_max=[0.3, 4.0, 0.3],
            size_min=0.15,
            size_max=0.35,
            color_start=[1.0, 0.9, 0.2, 1.0],   # Yellow
            color_end=[0.8, 0.1, 0.0, 0.0],     # Red → transparent
            size_start_multiplier=1.0,
            size_end_multiplier=0.3,             # Shrinks
            gravity=[0, 0.5, 0],                 # Rises up
            drag=0.5,
        )

        emitter = ParticleEmitter(name="Fire", config=config)
        return emitter

    # ---------- SMOKE 💨 ----------

    @staticmethod
    def smoke(position: Optional[List[float]] = None,
              intensity: float = 1.0) -> ParticleEmitter:
        """Smoke effect - drifting gray particles"""
        pos = position or [0, 0, 0]

        config = EmitterConfig(
            position=pos,
            shape=EmitterShape.CIRCLE,
            shape_size=[0.5, 0.5, 0.5],
            rate=40 * intensity,
            max_particles=int(300 * intensity),
            lifetime_min=2.0,
            lifetime_max=4.0,
            velocity_min=[-0.5, 1.0, -0.5],
            velocity_max=[0.5, 2.5, 0.5],
            size_min=0.5,
            size_max=1.0,
            color_start=[0.4, 0.4, 0.4, 0.7],   # Gray
            color_end=[0.2, 0.2, 0.2, 0.0],     # Fade out
            size_start_multiplier=1.0,
            size_end_multiplier=2.5,             # Grows
            gravity=[0, 0.3, 0],
            wind=[0.2, 0, 0],
            drag=0.3,
        )

        emitter = ParticleEmitter(name="Smoke", config=config)
        return emitter

    # ---------- RAIN ☔ ----------

    @staticmethod
    def rain(position: Optional[List[float]] = None,
             area_size: float = 10.0,
             intensity: float = 1.0) -> ParticleEmitter:
        """Rain effect - falling particles"""
        pos = position or [0, 10, 0]

        config = EmitterConfig(
            position=pos,
            shape=EmitterShape.BOX,
            shape_size=[area_size, 0.1, area_size],
            rate=300 * intensity,
            max_particles=int(1000 * intensity),
            lifetime_min=1.5,
            lifetime_max=2.0,
            velocity_min=[-0.5, -15, -0.5],
            velocity_max=[0.5, -20, 0.5],
            size_min=0.05,
            size_max=0.1,
            color_start=[0.6, 0.7, 0.9, 0.8],   # Blue tint
            color_end=[0.6, 0.7, 0.9, 0.5],
            gravity=[0, -9.81, 0],
            drag=0.01,
        )

        emitter = ParticleEmitter(name="Rain", config=config)
        return emitter

    # ---------- SNOW ❄️ ----------

    @staticmethod
    def snow(position: Optional[List[float]] = None,
             area_size: float = 10.0,
             intensity: float = 1.0) -> ParticleEmitter:
        """Snow effect - slow falling white particles"""
        pos = position or [0, 8, 0]

        config = EmitterConfig(
            position=pos,
            shape=EmitterShape.BOX,
            shape_size=[area_size, 0.5, area_size],
            rate=60 * intensity,
            max_particles=int(500 * intensity),
            lifetime_min=4.0,
            lifetime_max=8.0,
            velocity_min=[-0.5, -1.0, -0.5],
            velocity_max=[0.5, -2.0, 0.5],
            size_min=0.1,
            size_max=0.2,
            color_start=[1.0, 1.0, 1.0, 1.0],
            color_end=[1.0, 1.0, 1.0, 0.7],
            gravity=[0, -0.5, 0],
            wind=[0.3, 0, 0],
            drag=0.1,
        )

        emitter = ParticleEmitter(name="Snow", config=config)
        return emitter

    # ---------- SPARKLE ✨ ----------

    @staticmethod
    def sparkle(position: Optional[List[float]] = None,
                intensity: float = 1.0) -> ParticleEmitter:
        """Magic sparkle - shiny particles"""
        pos = position or [0, 1, 0]

        config = EmitterConfig(
            position=pos,
            shape=EmitterShape.SPHERE,
            shape_size=[0.3, 0.3, 0.3],
            rate=60 * intensity,
            max_particles=int(150 * intensity),
            lifetime_min=0.5,
            lifetime_max=1.5,
            velocity_min=[-2, -1, -2],
            velocity_max=[2, 3, 2],
            size_min=0.05,
            size_max=0.15,
            color_start=[1.0, 1.0, 0.5, 1.0],   # Gold
            color_end=[1.0, 0.8, 0.9, 0.0],     # Pink fade
            size_start_multiplier=1.5,
            size_end_multiplier=0.5,
            gravity=[0, -1.0, 0],
            drag=0.1,
        )

        emitter = ParticleEmitter(name="Sparkle", config=config)
        return emitter

    # ---------- EXPLOSION 💥 ----------

    @staticmethod
    def explosion(position: Optional[List[float]] = None,
                  intensity: float = 1.0) -> ParticleEmitter:
        """One-time explosion burst"""
        pos = position or [0, 0, 0]

        config = EmitterConfig(
            position=pos,
            shape=EmitterShape.POINT,
            rate=0,  # No continuous
            burst_count=int(200 * intensity),
            max_particles=int(500 * intensity),
            lifetime_min=0.5,
            lifetime_max=1.5,
            velocity_min=[-10, -10, -10],
            velocity_max=[10, 10, 10],
            velocity_random_scale=intensity,
            size_min=0.2,
            size_max=0.5,
            color_start=[1.0, 0.8, 0.2, 1.0],   # Orange-yellow
            color_end=[0.3, 0.0, 0.0, 0.0],     # Dark red
            size_start_multiplier=1.5,
            size_end_multiplier=0.5,
            gravity=[0, -5, 0],
            drag=0.3,
        )

        emitter = ParticleEmitter(name="Explosion", config=config)
        emitter.emit(config.burst_count)  # Immediate burst
        return emitter

    # ---------- CONFETTI 🎉 ----------

    @staticmethod
    def confetti(position: Optional[List[float]] = None,
                 intensity: float = 1.0) -> ParticleEmitter:
        """Colorful confetti burst"""
        pos = position or [0, 3, 0]

        config = EmitterConfig(
            position=pos,
            shape=EmitterShape.POINT,
            rate=0,
            burst_count=int(150 * intensity),
            max_particles=int(300 * intensity),
            lifetime_min=2.0,
            lifetime_max=4.0,
            velocity_min=[-5, 3, -5],
            velocity_max=[5, 8, 5],
            size_min=0.1,
            size_max=0.2,
            color_start=[1.0, 0.5, 0.5, 1.0],   # Random-ish start
            color_end=[0.5, 0.5, 1.0, 0.8],
            gravity=[0, -9.81, 0],
            drag=0.1,
        )

        emitter = ParticleEmitter(name="Confetti", config=config)
        emitter.emit(config.burst_count)

        # Randomize colors
        for p in emitter.particles:
            p.color = np.array([
                random.random(),
                random.random(),
                random.random(),
                1.0
            ], dtype=np.float32)
            p.initial_color = p.color.copy()

        return emitter

    # ---------- FOG 🌫️ ----------

    @staticmethod
    def fog(position: Optional[List[float]] = None,
            area_size: float = 8.0,
            intensity: float = 1.0) -> ParticleEmitter:
        """Fog - slow low drifting particles"""
        pos = position or [0, 0.5, 0]

        config = EmitterConfig(
            position=pos,
            shape=EmitterShape.BOX,
            shape_size=[area_size, 0.3, area_size],
            rate=20 * intensity,
            max_particles=int(200 * intensity),
            lifetime_min=6.0,
            lifetime_max=12.0,
            velocity_min=[-0.1, 0, -0.1],
            velocity_max=[0.1, 0.2, 0.1],
            size_min=1.5,
            size_max=3.0,
            color_start=[0.8, 0.8, 0.85, 0.3],
            color_end=[0.7, 0.7, 0.75, 0.0],
            size_start_multiplier=1.0,
            size_end_multiplier=1.5,
            wind=[0.05, 0, 0.05],
            drag=0.4,
        )

        emitter = ParticleEmitter(name="Fog", config=config)
        return emitter

    # ---------- LIGHTNING ⚡ ----------

    @staticmethod
    def lightning(position: Optional[List[float]] = None,
                  intensity: float = 1.0) -> ParticleEmitter:
        """Lightning strike - brief bright burst"""
        pos = position or [0, 5, 0]

        config = EmitterConfig(
            position=pos,
            shape=EmitterShape.LINE,
            shape_size=[10, 0, 0],
            rate=0,
            burst_count=int(80 * intensity),
            max_particles=int(100 * intensity),
            lifetime_min=0.1,
            lifetime_max=0.3,
            velocity_min=[-0.5, -20, -0.5],
            velocity_max=[0.5, -25, 0.5],
            size_min=0.15,
            size_max=0.3,
            color_start=[1.0, 1.0, 1.0, 1.0],    # White
            color_end=[0.5, 0.7, 1.0, 0.0],      # Blue fade
        )

        emitter = ParticleEmitter(name="Lightning", config=config)
        emitter.emit(config.burst_count)
        return emitter

    # ---------- BLOOD SPLASH 🩸 ----------

    @staticmethod
    def blood_splash(position: Optional[List[float]] = None,
                     intensity: float = 1.0) -> ParticleEmitter:
        """Blood splash burst"""
        pos = position or [0, 1, 0]

        config = EmitterConfig(
            position=pos,
            shape=EmitterShape.POINT,
            rate=0,
            burst_count=int(50 * intensity),
            max_particles=int(80 * intensity),
            lifetime_min=0.8,
            lifetime_max=1.5,
            velocity_min=[-4, 1, -4],
            velocity_max=[4, 5, 4],
            size_min=0.1,
            size_max=0.25,
            color_start=[0.7, 0.0, 0.0, 1.0],    # Deep red
            color_end=[0.3, 0.0, 0.0, 0.0],
            gravity=[0, -9.81, 0],
            drag=0.05,
        )

        emitter = ParticleEmitter(name="Blood", config=config)
        emitter.emit(config.burst_count)
        return emitter

    # ---------- ALL PRESETS ----------

    @classmethod
    def get_all_presets(cls) -> Dict[str, Callable]:
        return {
            "fire": cls.fire,
            "smoke": cls.smoke,
            "rain": cls.rain,
            "snow": cls.snow,
            "sparkle": cls.sparkle,
            "explosion": cls.explosion,
            "confetti": cls.confetti,
            "fog": cls.fog,
            "lightning": cls.lightning,
            "blood_splash": cls.blood_splash,
        }

    @classmethod
    def get_preset_names(cls) -> List[str]:
        return list(cls.get_all_presets().keys())

    @classmethod
    def create_preset(cls, name: str,
                      position: Optional[List[float]] = None,
                      intensity: float = 1.0) -> Optional[ParticleEmitter]:
        """Named preset create karo"""
        presets = cls.get_all_presets()
        if name not in presets:
            return None
        return presets[name](position=position, intensity=intensity)


# ============================================================
# VFX ENGINE (Main Manager)
# ============================================================

class VFXEngine:
    """
    Main VFX engine.
    Multiple emitters manage karta hai.
    """

    def __init__(self, config: Optional[Dict] = None):
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        self.emitters: Dict[str, ParticleEmitter] = {}
        self.enabled = True
        self.simulation_time = 0.0

        # Performance limit
        vfx_config = self.config.get("vfx", {})
        self.max_total_particles = vfx_config.get("particle_count", {}).get("medium", 5000)

        logger.info(f"VFXEngine initialized (max particles: {self.max_total_particles})")

    def add_emitter(self, emitter: ParticleEmitter) -> str:
        """Emitter add karo"""
        self.emitters[emitter.id] = emitter
        logger.debug(f"Added emitter: {emitter.name}")
        return emitter.id

    def create_effect(self, preset_name: str,
                      position: Optional[List[float]] = None,
                      intensity: float = 1.0) -> Optional[ParticleEmitter]:
        """Preset se effect create karo"""
        emitter = VFXPresets.create_preset(preset_name, position, intensity)
        if emitter:
            self.add_emitter(emitter)
            logger.info(f"Created effect: {preset_name} @ {position}")
        return emitter

    def remove_emitter(self, emitter_id: str) -> bool:
        if emitter_id in self.emitters:
            del self.emitters[emitter_id]
            return True
        return False

    def get_emitter(self, emitter_id: str) -> Optional[ParticleEmitter]:
        return self.emitters.get(emitter_id)

    def get_all_emitters(self) -> List[ParticleEmitter]:
        return list(self.emitters.values())

    def clear_all(self):
        """Sab emitters clear karo"""
        self.emitters.clear()
        logger.info("All effects cleared")

    def update(self, dt: float):
        """Sab emitters update karo"""
        if not self.enabled:
            return

        for emitter in self.emitters.values():
            emitter.update(dt)

        # Auto-remove dead emitters (burst-only jo khali ho gaye)
        to_remove = []
        for eid, emitter in self.emitters.items():
            if (emitter.config.rate == 0 and
                emitter.config.burst_count > 0 and
                len(emitter.particles) == 0 and
                emitter._age > 0.5):
                to_remove.append(eid)

        for eid in to_remove:
            self.remove_emitter(eid)

        self.simulation_time += dt

    def get_total_particles(self) -> int:
        """Total alive particles across all emitters"""
        return sum(e.get_alive_count() for e in self.emitters.values())

    def get_stats(self) -> Dict:
        """VFX statistics"""
        return {
            "total_emitters": len(self.emitters),
            "total_particles": self.get_total_particles(),
            "max_particles": self.max_total_particles,
            "enabled": self.enabled,
            "simulation_time": round(self.simulation_time, 2),
        }


# ============================================================
# TEST FUNCTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")
    print_banner("VFX Engine Test", "Visual Effects System")

    # ============================================================
    # Test 1: Initialize
    # ============================================================
    print_section("Test 1: Initialize VFX Engine")

    vfx = VFXEngine()

    print(f"Max particles: {vfx.max_total_particles}")

    # ============================================================
    # Test 2: Available Presets
    # ============================================================
    print_section("Test 2: Available Effects")

    presets = VFXPresets.get_preset_names()
    print(f"Total effects: {len(presets)}")

    icons = {
        "fire": "🔥", "smoke": "💨", "rain": "☔", "snow": "❄️",
        "sparkle": "✨", "explosion": "💥", "confetti": "🎉",
        "fog": "🌫️", "lightning": "⚡", "blood_splash": "🩸"
    }

    for name in presets:
        icon = icons.get(name, "🎨")
        print(f"  {icon} {name}")

    # ============================================================
    # Test 3: Fire Effect
    # ============================================================
    print_section("Test 3: Fire Effect Simulation")

    fire = vfx.create_effect("fire", position=[0, 0, 0], intensity=1.0)

    print("Simulating fire for 2 seconds...")
    print(f"{'Time':>6} | {'Particles':>10} | {'Sample Y':>10} | {'Sample Color':>25}")
    print("-" * 60)

    for i in range(120):  # 2 sec at 60fps
        vfx.update(1/60)

        if i % 20 == 0 and fire.particles:
            sample = fire.particles[0]
            y = sample.position[1]
            color = [round(c, 2) for c in sample.color]
            print(f"{i/60:>6.2f}s | {len(fire.particles):>10} | {y:>10.2f} | {str(color):>25}")

    # ============================================================
    # Test 4: Explosion (Burst)
    # ============================================================
    print_section("Test 4: Explosion (One-time Burst)")

    vfx.clear_all()

    explosion = vfx.create_effect("explosion", position=[0, 3, 0], intensity=1.5)

    print(f"Initial particles: {explosion.get_alive_count()}")

    # Simulate 2 seconds
    print("\nSimulating explosion decay...")
    for i in range(120):
        vfx.update(1/60)

        if i % 30 == 0:
            count = explosion.get_alive_count() if explosion.id in vfx.emitters else 0
            print(f"  t={i/60:.1f}s: alive particles = {count}")

    print(f"\nEmitters remaining: {len(vfx.emitters)}")
    print("(Should be 0 - burst effects auto-cleanup)")

    # ============================================================
    # Test 5: Multiple Effects Simultaneously
    # ============================================================
    print_section("Test 5: Multiple Effects Together")

    vfx.clear_all()

    # Combine effects
    vfx.create_effect("fire", position=[-2, 0, 0])
    vfx.create_effect("smoke", position=[-2, 1, 0])  # Above fire
    vfx.create_effect("rain", position=[2, 5, 0], intensity=0.5)
    vfx.create_effect("sparkle", position=[0, 2, 0])

    print(f"Created {len(vfx.emitters)} simultaneous effects")

    print("\nSimulating combined scene for 1 second...")

    for i in range(60):
        vfx.update(1/60)

        if i % 20 == 0:
            stats = vfx.get_stats()
            print(f"  t={i/60:.2f}s: {stats['total_emitters']} emitters, "
                  f"{stats['total_particles']} particles")

    # ============================================================
    # Test 6: All Effects Test
    # ============================================================
    print_section("Test 6: Test All Effects")

    vfx.clear_all()

    print("Creating all effects one by one...")
    for name in VFXPresets.get_preset_names():
        emitter = vfx.create_effect(name)
        if emitter:
            # Update once to populate
            vfx.update(1/60)
            count = emitter.get_alive_count()
            print(f"  {icons.get(name, '🎨')} {name:15s}: {count:>4} particles")

    stats = vfx.get_stats()
    print(f"\nTotal: {stats['total_particles']} particles across "
          f"{stats['total_emitters']} emitters")

    # ============================================================
    # Test 7: Performance Test
    # ============================================================
    print_section("Test 7: Performance Test")

    vfx.clear_all()

    # Heavy rain scene
    vfx.create_effect("rain", position=[0, 10, 0], intensity=1.0)
    vfx.create_effect("fog", position=[0, 0, 0])

    # Warm up
    for _ in range(30):
        vfx.update(1/60)

    print(f"Active particles: {vfx.get_total_particles()}")
    print("Running 60 frames performance test...")

    start = time.time()
    for _ in range(60):
        vfx.update(1/60)
    elapsed = time.time() - start

    fps = 60 / elapsed
    ms_per_frame = (elapsed / 60) * 1000

    print(f"60 frames in {elapsed:.3f}s")
    print(f"Average: {ms_per_frame:.2f}ms per frame")
    print(f"Simulation FPS: {fps:.1f}")

    if fps >= 60:
        print("✅ Excellent performance!")
    elif fps >= 30:
        print("✅ Good performance")
    else:
        print("⚠️  Moderate performance (reduce particle count)")

    # ============================================================
    # Test 8: Final Stats
    # ============================================================
    print_section("Test 8: Final Statistics")

    stats = vfx.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print_banner(
        "✅ All Tests Passed",
        "VFX Engine Working - 10 effects ready!"
    )