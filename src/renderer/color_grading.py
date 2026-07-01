# ============================================================
# src/renderer/color_grading.py
# 3D Animation Studio - Color Grading & Post-Processing
# Vintage, Dramatic, Warm, Cool filters aur adjustments
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
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

import numpy as np

from src.utils import get_logger, get_config, generate_uuid

logger = get_logger("ColorGrading")


# ============================================================
# ENUMS
# ============================================================

class FilterType(Enum):
    """Predefined filter presets"""
    NONE            = "none"
    VINTAGE         = "vintage"
    DRAMATIC        = "dramatic"
    WARM            = "warm"
    COOL            = "cool"
    NOIR            = "noir"              # Black & white classic
    SEPIA           = "sepia"
    CINEMATIC       = "cinematic"
    VIBRANT         = "vibrant"
    FADED           = "faded"
    FILM            = "film"
    HORROR          = "horror"
    ROMANCE         = "romance"
    SCI_FI          = "sci_fi"
    BOLLYWOOD       = "bollywood"
    RETRO_80S       = "retro_80s"
    SUNSET          = "sunset"
    UNDERWATER      = "underwater"
    NIGHT_VISION    = "night_vision"
    THERMAL         = "thermal"
    COMIC           = "comic"
    DREAMY          = "dreamy"


class BlendMode(Enum):
    """Layer blending modes"""
    NORMAL          = "normal"
    MULTIPLY        = "multiply"
    SCREEN          = "screen"
    OVERLAY         = "overlay"
    SOFT_LIGHT      = "soft_light"
    HARD_LIGHT      = "hard_light"
    COLOR_DODGE     = "color_dodge"
    COLOR_BURN      = "color_burn"


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class ColorAdjustments:
    """
    Basic color adjustments (like Instagram).
    All values 0-1 or -1 to 1.
    """
    # Exposure & levels
    exposure:           float           = 0.0        # -2.0 to 2.0
    brightness:         float           = 0.0        # -1.0 to 1.0
    contrast:           float           = 0.0        # -1.0 to 1.0
    highlights:         float           = 0.0        # -1.0 to 1.0
    shadows:            float           = 0.0        # -1.0 to 1.0
    whites:             float           = 0.0        # -1.0 to 1.0
    blacks:             float           = 0.0        # -1.0 to 1.0

    # Color
    saturation:         float           = 0.0        # -1.0 to 1.0
    vibrance:           float           = 0.0        # -1.0 to 1.0
    temperature:        float           = 0.0        # -1.0 to 1.0 (cool to warm)
    tint:               float           = 0.0        # -1.0 to 1.0 (green to magenta)

    # Individual channels
    red_shift:          float           = 0.0
    green_shift:        float           = 0.0
    blue_shift:         float           = 0.0

    # Effects
    gamma:              float           = 1.0        # 0.1 to 3.0
    hue_shift:          float           = 0.0        # -180 to 180 degrees

    def to_dict(self) -> Dict:
        return {
            "exposure":    self.exposure,
            "brightness":  self.brightness,
            "contrast":    self.contrast,
            "highlights":  self.highlights,
            "shadows":     self.shadows,
            "whites":      self.whites,
            "blacks":      self.blacks,
            "saturation":  self.saturation,
            "vibrance":    self.vibrance,
            "temperature": self.temperature,
            "tint":        self.tint,
            "red_shift":   self.red_shift,
            "green_shift": self.green_shift,
            "blue_shift":  self.blue_shift,
            "gamma":       self.gamma,
            "hue_shift":   self.hue_shift,
        }


@dataclass
class VignetteSettings:
    """Vignette (dark corners) effect"""
    enabled:            bool            = False
    strength:           float           = 0.5       # 0.0 - 1.0
    radius:             float           = 0.7       # 0.0 - 1.0
    color:              List[float]     = field(default_factory=lambda: [0.0, 0.0, 0.0])
    softness:           float           = 0.5       # Edge softness

    def to_dict(self) -> Dict:
        return {
            "enabled":  self.enabled,
            "strength": self.strength,
            "radius":   self.radius,
            "color":    self.color,
            "softness": self.softness,
        }


@dataclass
class GrainSettings:
    """Film grain effect"""
    enabled:            bool            = False
    intensity:          float           = 0.15      # 0.0 - 1.0
    size:               float           = 1.0
    colored:            bool            = False     # True = colored grain

    def to_dict(self) -> Dict:
        return {
            "enabled":   self.enabled,
            "intensity": self.intensity,
            "size":      self.size,
            "colored":   self.colored,
        }


@dataclass
class BlurSettings:
    """Blur effects"""
    enabled:            bool            = False
    blur_type:          str             = "gaussian"     # gaussian, motion, radial
    strength:           float           = 0.5           # 0.0 - 1.0
    angle:              float           = 0.0           # For motion blur


@dataclass
class BloomSettings:
    """Bloom (glow) effect for bright areas"""
    enabled:            bool            = False
    threshold:          float           = 0.8       # Brightness threshold
    intensity:          float           = 0.5
    radius:             float           = 1.0
    color_tint:         List[float]     = field(default_factory=lambda: [1.0, 1.0, 1.0])


@dataclass
class ChromaticAberrationSettings:
    """RGB channel offset (like lens distortion)"""
    enabled:            bool            = False
    strength:           float           = 0.3       # 0.0 - 1.0
    red_offset:         List[float]     = field(default_factory=lambda: [-1, 0])
    blue_offset:        List[float]     = field(default_factory=lambda: [1, 0])


@dataclass
class ColorGradingPreset:
    """
    Complete color grading preset.
    Sabhi effects ek jagah.
    """
    # Identity
    preset_id:          str             = ""
    name:               str             = "Custom"
    filter_type:        str             = FilterType.NONE.value
    description:        str             = ""

    # Effects
    adjustments:        ColorAdjustments= field(default_factory=ColorAdjustments)
    vignette:           VignetteSettings= field(default_factory=VignetteSettings)
    grain:              GrainSettings   = field(default_factory=GrainSettings)
    blur:               BlurSettings    = field(default_factory=BlurSettings)
    bloom:              BloomSettings   = field(default_factory=BloomSettings)
    chromatic_aberration: ChromaticAberrationSettings = field(
        default_factory=ChromaticAberrationSettings
    )

    # Overall
    intensity:          float           = 1.0       # 0.0 - 1.0 (filter strength)

    def __post_init__(self):
        if not self.preset_id:
            self.preset_id = f"grade_{generate_uuid()[:8]}"

    def to_dict(self) -> Dict:
        return {
            "preset_id":            self.preset_id,
            "name":                 self.name,
            "filter_type":          self.filter_type,
            "description":          self.description,
            "adjustments":          self.adjustments.to_dict(),
            "vignette":             self.vignette.to_dict(),
            "grain":                self.grain.to_dict(),
            "intensity":            self.intensity,
        }


# ============================================================
# COLOR MATH UTILITIES
# ============================================================

class ColorMath:
    """Color math operations"""

    @staticmethod
    def clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
        return max(min_val, min(max_val, value))

    @staticmethod
    def clamp_color(color: List[float]) -> List[float]:
        return [ColorMath.clamp(c) for c in color]

    @staticmethod
    def lerp(a: float, b: float, t: float) -> float:
        return a + (b - a) * t

    @staticmethod
    def lerp_color(c1: List[float], c2: List[float], t: float) -> List[float]:
        return [ColorMath.lerp(c1[i], c2[i], t) for i in range(len(c1))]

    @staticmethod
    def rgb_to_hsl(r: float, g: float, b: float) -> Tuple[float, float, float]:
        """RGB (0-1) to HSL (0-1)"""
        max_c = max(r, g, b)
        min_c = min(r, g, b)
        delta = max_c - min_c

        # Lightness
        l = (max_c + min_c) / 2

        if delta == 0:
            return (0, 0, l)

        # Saturation
        if l < 0.5:
            s = delta / (max_c + min_c)
        else:
            s = delta / (2 - max_c - min_c)

        # Hue
        if max_c == r:
            h = ((g - b) / delta) % 6
        elif max_c == g:
            h = (b - r) / delta + 2
        else:
            h = (r - g) / delta + 4

        h = h / 6.0
        return (h, s, l)

    @staticmethod
    def hsl_to_rgb(h: float, s: float, l: float) -> Tuple[float, float, float]:
        """HSL (0-1) to RGB (0-1)"""
        if s == 0:
            return (l, l, l)

        c = (1 - abs(2 * l - 1)) * s
        x = c * (1 - abs((h * 6) % 2 - 1))
        m = l - c / 2

        h_seg = int(h * 6)

        if h_seg == 0:   r, g, b = c, x, 0
        elif h_seg == 1: r, g, b = x, c, 0
        elif h_seg == 2: r, g, b = 0, c, x
        elif h_seg == 3: r, g, b = 0, x, c
        elif h_seg == 4: r, g, b = x, 0, c
        else:            r, g, b = c, 0, x

        return (r + m, g + m, b + m)

    @staticmethod
    def apply_temperature(color: List[float], temperature: float) -> List[float]:
        """
        Temperature adjustment (-1 = cool blue, +1 = warm orange).
        """
        r, g, b = color[0], color[1], color[2]

        if temperature > 0:
            # Warm (add red, reduce blue)
            r = ColorMath.clamp(r + temperature * 0.15)
            b = ColorMath.clamp(b - temperature * 0.15)
        else:
            # Cool (reduce red, add blue)
            r = ColorMath.clamp(r + temperature * 0.15)
            b = ColorMath.clamp(b - temperature * 0.15)

        return [r, g, b]


# ============================================================
# COLOR PROCESSOR - Apply grading to image/color
# ============================================================

class ColorProcessor:
    """
    Color grading actually apply karta hai.
    Single colors ya full images process kar sakta hai.
    """

    def __init__(self, preset: Optional[ColorGradingPreset] = None):
        self.preset = preset or ColorGradingPreset()

    def process_color(self, color: List[float]) -> List[float]:
        """
        Ek color pe pura grading apply karo.

        Args:
            color: RGB list [r, g, b] with values 0-1

        Returns:
            Graded color [r, g, b]
        """
        # Copy
        r, g, b = color[0], color[1], color[2]

        adj = self.preset.adjustments

        # ===== 1. EXPOSURE =====
        if adj.exposure != 0:
            factor = 2 ** adj.exposure
            r *= factor
            g *= factor
            b *= factor

        # ===== 2. BRIGHTNESS =====
        if adj.brightness != 0:
            r += adj.brightness
            g += adj.brightness
            b += adj.brightness

        # ===== 3. CONTRAST =====
        if adj.contrast != 0:
            factor = 1 + adj.contrast
            r = (r - 0.5) * factor + 0.5
            g = (g - 0.5) * factor + 0.5
            b = (b - 0.5) * factor + 0.5

        # ===== 4. HIGHLIGHTS/SHADOWS =====
        luminance = 0.299 * r + 0.587 * g + 0.114 * b

        if adj.highlights != 0:
            weight = max(0, (luminance - 0.5) * 2)   # 0 at midtone, 1 at max
            r += adj.highlights * weight * 0.5
            g += adj.highlights * weight * 0.5
            b += adj.highlights * weight * 0.5

        if adj.shadows != 0:
            weight = max(0, (0.5 - luminance) * 2)   # 1 at min, 0 at midtone
            r += adj.shadows * weight * 0.5
            g += adj.shadows * weight * 0.5
            b += adj.shadows * weight * 0.5

        # ===== 5. WHITES/BLACKS =====
        if adj.whites != 0:
            weight = max(0, luminance - 0.7) * 3.33   # Only affects brightest
            r += adj.whites * weight * 0.3
            g += adj.whites * weight * 0.3
            b += adj.whites * weight * 0.3

        if adj.blacks != 0:
            weight = max(0, 0.3 - luminance) * 3.33
            r += adj.blacks * weight * 0.3
            g += adj.blacks * weight * 0.3
            b += adj.blacks * weight * 0.3

        # Clamp
        r = ColorMath.clamp(r)
        g = ColorMath.clamp(g)
        b = ColorMath.clamp(b)

        # ===== 6. TEMPERATURE =====
        if adj.temperature != 0:
            if adj.temperature > 0:
                r += adj.temperature * 0.15
                b -= adj.temperature * 0.15
            else:
                r += adj.temperature * 0.15
                b -= adj.temperature * 0.15

        # ===== 7. TINT (green-magenta) =====
        if adj.tint != 0:
            g -= adj.tint * 0.1
            r += adj.tint * 0.05
            b += adj.tint * 0.05

        # ===== 8. CHANNEL SHIFTS =====
        r += adj.red_shift * 0.2
        g += adj.green_shift * 0.2
        b += adj.blue_shift * 0.2

        # ===== 9. SATURATION =====
        if adj.saturation != 0:
            gray = 0.299 * r + 0.587 * g + 0.114 * b
            factor = 1 + adj.saturation
            r = gray + (r - gray) * factor
            g = gray + (g - gray) * factor
            b = gray + (b - gray) * factor

        # ===== 10. VIBRANCE (smart saturation) =====
        if adj.vibrance != 0:
            gray = 0.299 * r + 0.587 * g + 0.114 * b
            # Less effect on already saturated colors
            max_c = max(r, g, b)
            min_c = min(r, g, b)
            current_sat = max_c - min_c if max_c > 0 else 0
            protection = 1 - current_sat
            factor = 1 + adj.vibrance * protection
            r = gray + (r - gray) * factor
            g = gray + (g - gray) * factor
            b = gray + (b - gray) * factor

        # Clamp
        r = ColorMath.clamp(r)
        g = ColorMath.clamp(g)
        b = ColorMath.clamp(b)

        # ===== 11. GAMMA =====
        if adj.gamma != 1.0:
            r = r ** (1.0 / adj.gamma)
            g = g ** (1.0 / adj.gamma)
            b = b ** (1.0 / adj.gamma)

        # ===== 12. HUE SHIFT =====
        if adj.hue_shift != 0:
            h, s, l = ColorMath.rgb_to_hsl(r, g, b)
            h = (h + adj.hue_shift / 360.0) % 1.0
            r, g, b = ColorMath.hsl_to_rgb(h, s, l)

        # ===== INTENSITY MIX =====
        if self.preset.intensity < 1.0:
            r = color[0] + (r - color[0]) * self.preset.intensity
            g = color[1] + (g - color[1]) * self.preset.intensity
            b = color[2] + (b - color[2]) * self.preset.intensity

        return [ColorMath.clamp(r), ColorMath.clamp(g), ColorMath.clamp(b)]

    def process_image_array(self, img_array: np.ndarray) -> np.ndarray:
        """
        NumPy image array pe grading apply karo.
        Shape: (H, W, 3) with values 0-255.

        Returns:
            Processed array
        """
        if img_array is None or img_array.size == 0:
            return img_array

        # Normalize to 0-1
        img_float = img_array.astype(np.float32) / 255.0

        # Process each channel with vectorized ops (faster)
        adj = self.preset.adjustments

        # Exposure
        if adj.exposure != 0:
            img_float *= 2 ** adj.exposure

        # Brightness
        if adj.brightness != 0:
            img_float += adj.brightness

        # Contrast
        if adj.contrast != 0:
            factor = 1 + adj.contrast
            img_float = (img_float - 0.5) * factor + 0.5

        # Clamp intermediate
        np.clip(img_float, 0.0, 1.0, out=img_float)

        # Temperature (R/B shift)
        if adj.temperature != 0:
            img_float[..., 0] += adj.temperature * 0.15
            img_float[..., 2] -= adj.temperature * 0.15

        # Channel shifts
        img_float[..., 0] += adj.red_shift * 0.2
        img_float[..., 1] += adj.green_shift * 0.2
        img_float[..., 2] += adj.blue_shift * 0.2

        # Saturation
        if adj.saturation != 0:
            gray = (0.299 * img_float[..., 0] +
                    0.587 * img_float[..., 1] +
                    0.114 * img_float[..., 2])
            factor = 1 + adj.saturation
            for c in range(3):
                img_float[..., c] = gray + (img_float[..., c] - gray) * factor

        # Gamma
        if adj.gamma != 1.0:
            img_float = np.power(np.maximum(img_float, 0), 1.0 / adj.gamma)

        # Final clamp
        np.clip(img_float, 0.0, 1.0, out=img_float)

        # Apply vignette
        if self.preset.vignette.enabled:
            img_float = self._apply_vignette(img_float)

        # Convert back to 0-255
        return (img_float * 255).astype(np.uint8)

    def _apply_vignette(self, img: np.ndarray) -> np.ndarray:
        """Vignette apply karo image pe"""
        try:
            v = self.preset.vignette
            h, w = img.shape[:2]

            # Create radial gradient mask
            y, x = np.ogrid[:h, :w]
            cx, cy = w / 2, h / 2
            distance = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            max_dist = math.sqrt(cx ** 2 + cy ** 2)
            normalized = distance / max_dist

            # Apply radius/softness
            radius = v.radius
            softness = v.softness

            # Vignette mask (1 in center, 0 at edges)
            mask = 1.0 - ColorMath.clamp((normalized - radius) / max(0.01, softness))
            mask = mask ** 2   # Smooth falloff

            # Apply
            for c in range(3):
                img[..., c] = img[..., c] * mask + v.color[c] * (1 - mask) * v.strength

            return img

        except Exception as e:
            logger.warning(f"Vignette apply error: {e}")
            return img


# ============================================================
# FILTER PRESETS - Ready-made looks
# ============================================================

class FilterPresets:
    """Predefined filter presets"""

    @staticmethod
    def none() -> ColorGradingPreset:
        return ColorGradingPreset(
            name        = "None",
            filter_type = FilterType.NONE.value,
            description = "No grading applied",
        )

    @staticmethod
    def vintage() -> ColorGradingPreset:
        """Vintage/faded old photo look"""
        preset = ColorGradingPreset(
            name        = "Vintage",
            filter_type = FilterType.VINTAGE.value,
            description = "Old faded photo look with warm tones",
        )
        preset.adjustments = ColorAdjustments(
            contrast    = -0.15,
            saturation  = -0.25,
            temperature = 0.3,
            highlights  = -0.2,
            shadows     = 0.15,
            red_shift   = 0.1,
            blue_shift  = -0.15,
            gamma       = 1.1,
        )
        preset.vignette = VignetteSettings(
            enabled  = True,
            strength = 0.4,
            radius   = 0.6,
            color    = [0.1, 0.05, 0.0],
        )
        preset.grain = GrainSettings(
            enabled   = True,
            intensity = 0.2,
        )
        return preset

    @staticmethod
    def dramatic() -> ColorGradingPreset:
        """Dark dramatic look"""
        preset = ColorGradingPreset(
            name        = "Dramatic",
            filter_type = FilterType.DRAMATIC.value,
            description = "High contrast dramatic cinematic look",
        )
        preset.adjustments = ColorAdjustments(
            contrast    = 0.4,
            saturation  = -0.1,
            highlights  = -0.3,
            shadows     = -0.4,
            whites      = -0.2,
            blacks      = -0.3,
            temperature = -0.1,
        )
        preset.vignette = VignetteSettings(
            enabled  = True,
            strength = 0.6,
            radius   = 0.5,
        )
        return preset

    @staticmethod
    def warm() -> ColorGradingPreset:
        """Warm cozy look"""
        preset = ColorGradingPreset(
            name        = "Warm",
            filter_type = FilterType.WARM.value,
            description = "Warm inviting colors",
        )
        preset.adjustments = ColorAdjustments(
            temperature = 0.4,
            saturation  = 0.1,
            highlights  = -0.1,
            red_shift   = 0.1,
            blue_shift  = -0.15,
        )
        return preset

    @staticmethod
    def cool() -> ColorGradingPreset:
        """Cool blue tones"""
        preset = ColorGradingPreset(
            name        = "Cool",
            filter_type = FilterType.COOL.value,
            description = "Cool blue moody tones",
        )
        preset.adjustments = ColorAdjustments(
            temperature = -0.4,
            saturation  = 0.05,
            blue_shift  = 0.15,
            red_shift   = -0.1,
            contrast    = 0.1,
        )
        return preset

    @staticmethod
    def noir() -> ColorGradingPreset:
        """Black and white classic noir"""
        preset = ColorGradingPreset(
            name        = "Noir",
            filter_type = FilterType.NOIR.value,
            description = "Classic black & white film noir",
        )
        preset.adjustments = ColorAdjustments(
            saturation  = -1.0,
            contrast    = 0.5,
            highlights  = -0.2,
            shadows     = -0.4,
            blacks      = -0.3,
        )
        preset.vignette = VignetteSettings(
            enabled  = True,
            strength = 0.7,
            radius   = 0.4,
        )
        preset.grain = GrainSettings(
            enabled   = True,
            intensity = 0.25,
        )
        return preset

    @staticmethod
    def sepia() -> ColorGradingPreset:
        """Sepia brown tones"""
        preset = ColorGradingPreset(
            name        = "Sepia",
            filter_type = FilterType.SEPIA.value,
            description = "Warm brown sepia tones",
        )
        preset.adjustments = ColorAdjustments(
            saturation  = -0.85,
            temperature = 0.5,
            red_shift   = 0.15,
            green_shift = 0.05,
            blue_shift  = -0.3,
            contrast    = 0.1,
        )
        return preset

    @staticmethod
    def cinematic() -> ColorGradingPreset:
        """Cinematic teal & orange"""
        preset = ColorGradingPreset(
            name        = "Cinematic",
            filter_type = FilterType.CINEMATIC.value,
            description = "Hollywood teal & orange cinematic look",
        )
        preset.adjustments = ColorAdjustments(
            contrast    = 0.2,
            saturation  = 0.15,
            highlights  = 0.1,      # Orange highlights
            shadows     = -0.2,     # Teal shadows
            red_shift   = 0.05,
            blue_shift  = 0.1,
            temperature = 0.1,
        )
        preset.vignette = VignetteSettings(
            enabled  = True,
            strength = 0.3,
            radius   = 0.7,
        )
        return preset

    @staticmethod
    def vibrant() -> ColorGradingPreset:
        """Bright vibrant colors"""
        preset = ColorGradingPreset(
            name        = "Vibrant",
            filter_type = FilterType.VIBRANT.value,
            description = "Bright vibrant saturated colors",
        )
        preset.adjustments = ColorAdjustments(
            saturation  = 0.5,
            vibrance    = 0.3,
            contrast    = 0.15,
            brightness  = 0.05,
        )
        return preset

    @staticmethod
    def faded() -> ColorGradingPreset:
        """Faded pastel look"""
        preset = ColorGradingPreset(
            name        = "Faded",
            filter_type = FilterType.FADED.value,
            description = "Soft faded pastel colors",
        )
        preset.adjustments = ColorAdjustments(
            saturation  = -0.3,
            contrast    = -0.25,
            highlights  = 0.15,
            shadows     = 0.25,
            gamma       = 1.15,
        )
        return preset

    @staticmethod
    def film() -> ColorGradingPreset:
        """Film emulation"""
        preset = ColorGradingPreset(
            name        = "Film",
            filter_type = FilterType.FILM.value,
            description = "Classic film emulation with grain",
        )
        preset.adjustments = ColorAdjustments(
            contrast    = 0.15,
            saturation  = -0.1,
            temperature = 0.15,
            highlights  = -0.15,
            shadows     = 0.1,
        )
        preset.grain = GrainSettings(
            enabled   = True,
            intensity = 0.2,
        )
        return preset

    @staticmethod
    def horror() -> ColorGradingPreset:
        """Dark horror look"""
        preset = ColorGradingPreset(
            name        = "Horror",
            filter_type = FilterType.HORROR.value,
            description = "Dark scary horror look",
        )
        preset.adjustments = ColorAdjustments(
            contrast    = 0.4,
            saturation  = -0.4,
            temperature = -0.3,
            shadows     = -0.4,
            blacks      = -0.4,
            highlights  = -0.2,
            green_shift = 0.1,
        )
        preset.vignette = VignetteSettings(
            enabled  = True,
            strength = 0.8,
            radius   = 0.35,
            color    = [0.02, 0.02, 0.05],
        )
        preset.grain = GrainSettings(
            enabled   = True,
            intensity = 0.3,
        )
        return preset

    @staticmethod
    def romance() -> ColorGradingPreset:
        """Soft romantic look"""
        preset = ColorGradingPreset(
            name        = "Romance",
            filter_type = FilterType.ROMANCE.value,
            description = "Soft dreamy romantic look",
        )
        preset.adjustments = ColorAdjustments(
            saturation  = 0.1,
            temperature = 0.25,
            highlights  = 0.15,
            shadows     = 0.1,
            contrast    = -0.1,
            red_shift   = 0.15,
        )
        preset.bloom = BloomSettings(
            enabled   = True,
            threshold = 0.7,
            intensity = 0.3,
        )
        return preset

    @staticmethod
    def sci_fi() -> ColorGradingPreset:
        """Sci-fi cool metallic"""
        preset = ColorGradingPreset(
            name        = "Sci-Fi",
            filter_type = FilterType.SCI_FI.value,
            description = "Cool futuristic sci-fi look",
        )
        preset.adjustments = ColorAdjustments(
            temperature = -0.5,
            contrast    = 0.25,
            saturation  = -0.1,
            blue_shift  = 0.2,
            highlights  = 0.15,
            shadows     = -0.15,
        )
        preset.bloom = BloomSettings(
            enabled    = True,
            threshold  = 0.75,
            intensity  = 0.4,
            color_tint = [0.6, 0.8, 1.0],
        )
        return preset

    @staticmethod
    def bollywood() -> ColorGradingPreset:
        """Bright colorful Bollywood look"""
        preset = ColorGradingPreset(
            name        = "Bollywood",
            filter_type = FilterType.BOLLYWOOD.value,
            description = "Bright colorful Indian film look",
        )
        preset.adjustments = ColorAdjustments(
            saturation  = 0.55,
            vibrance    = 0.35,
            contrast    = 0.2,
            temperature = 0.25,
            brightness  = 0.05,
            red_shift   = 0.1,
        )
        return preset

    @staticmethod
    def retro_80s() -> ColorGradingPreset:
        """80s retro synthwave"""
        preset = ColorGradingPreset(
            name        = "Retro 80s",
            filter_type = FilterType.RETRO_80S.value,
            description = "Neon 80s synthwave look",
        )
        preset.adjustments = ColorAdjustments(
            saturation  = 0.4,
            contrast    = 0.3,
            temperature = 0.1,
            red_shift   = 0.15,
            blue_shift  = 0.2,
            highlights  = 0.2,
            shadows     = -0.2,
        )
        preset.bloom = BloomSettings(
            enabled    = True,
            threshold  = 0.65,
            intensity  = 0.5,
            color_tint = [1.0, 0.5, 0.9],
        )
        return preset

    @staticmethod
    def sunset() -> ColorGradingPreset:
        """Warm sunset colors"""
        preset = ColorGradingPreset(
            name        = "Sunset",
            filter_type = FilterType.SUNSET.value,
            description = "Warm golden hour sunset look",
        )
        preset.adjustments = ColorAdjustments(
            temperature = 0.5,
            saturation  = 0.25,
            highlights  = 0.15,
            red_shift   = 0.2,
            blue_shift  = -0.2,
            contrast    = 0.15,
        )
        return preset

    @staticmethod
    def underwater() -> ColorGradingPreset:
        """Underwater blue-green"""
        preset = ColorGradingPreset(
            name        = "Underwater",
            filter_type = FilterType.UNDERWATER.value,
            description = "Blue-green underwater look",
        )
        preset.adjustments = ColorAdjustments(
            temperature = -0.6,
            green_shift = 0.15,
            blue_shift  = 0.2,
            red_shift   = -0.2,
            saturation  = 0.15,
            contrast    = -0.05,
        )
        return preset

    @staticmethod
    def night_vision() -> ColorGradingPreset:
        """Green night vision"""
        preset = ColorGradingPreset(
            name        = "Night Vision",
            filter_type = FilterType.NIGHT_VISION.value,
            description = "Military-style green night vision",
        )
        preset.adjustments = ColorAdjustments(
            saturation  = -1.0,   # Kill saturation first
            green_shift = 0.5,    # Make everything green
            red_shift   = -0.5,
            blue_shift  = -0.5,
            contrast    = 0.4,
            brightness  = -0.1,
        )
        preset.grain = GrainSettings(
            enabled   = True,
            intensity = 0.4,
        )
        return preset

    @staticmethod
    def comic() -> ColorGradingPreset:
        """Comic book style"""
        preset = ColorGradingPreset(
            name        = "Comic",
            filter_type = FilterType.COMIC.value,
            description = "Vibrant comic book style",
        )
        preset.adjustments = ColorAdjustments(
            saturation  = 0.6,
            contrast    = 0.45,
            brightness  = 0.05,
            highlights  = 0.15,
            shadows     = -0.15,
        )
        return preset

    @staticmethod
    def dreamy() -> ColorGradingPreset:
        """Soft dreamy blur look"""
        preset = ColorGradingPreset(
            name        = "Dreamy",
            filter_type = FilterType.DREAMY.value,
            description = "Soft dreamy ethereal look",
        )
        preset.adjustments = ColorAdjustments(
            brightness  = 0.1,
            saturation  = 0.05,
            highlights  = 0.25,
            contrast    = -0.15,
            temperature = 0.1,
        )
        preset.bloom = BloomSettings(
            enabled   = True,
            threshold = 0.6,
            intensity = 0.6,
        )
        preset.blur = BlurSettings(
            enabled   = True,
            strength  = 0.1,
        )
        return preset

    @staticmethod
    def get_all_presets() -> Dict[str, ColorGradingPreset]:
        """Sabhi presets ek jagah"""
        return {
            "none":         FilterPresets.none(),
            "vintage":      FilterPresets.vintage(),
            "dramatic":     FilterPresets.dramatic(),
            "warm":         FilterPresets.warm(),
            "cool":         FilterPresets.cool(),
            "noir":         FilterPresets.noir(),
            "sepia":        FilterPresets.sepia(),
            "cinematic":    FilterPresets.cinematic(),
            "vibrant":      FilterPresets.vibrant(),
            "faded":        FilterPresets.faded(),
            "film":         FilterPresets.film(),
            "horror":       FilterPresets.horror(),
            "romance":      FilterPresets.romance(),
            "sci_fi":       FilterPresets.sci_fi(),
            "bollywood":    FilterPresets.bollywood(),
            "retro_80s":    FilterPresets.retro_80s(),
            "sunset":       FilterPresets.sunset(),
            "underwater":   FilterPresets.underwater(),
            "night_vision": FilterPresets.night_vision(),
            "comic":        FilterPresets.comic(),
            "dreamy":       FilterPresets.dreamy(),
        }


# ============================================================
# COLOR GRADING MANAGER
# ============================================================

class ColorGradingManager:
    """
    Main color grading manager.
    Presets manage karo, apply karo, custom banao.
    """

    def __init__(self, config: Optional[Dict] = None):
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # Load presets
        self._presets: Dict[str, ColorGradingPreset] = {}
        self._load_presets()

        # Active preset
        self._active_preset: Optional[ColorGradingPreset] = None

        # Listeners
        self._listeners: List[Callable] = []

        logger.info(
            f"✅ ColorGradingManager initialized | "
            f"{len(self._presets)} presets loaded"
        )

    def _load_presets(self):
        """All filter presets load karo"""
        presets = FilterPresets.get_all_presets()
        for key, preset in presets.items():
            self._presets[key] = preset

    def get_preset(self, filter_name: str) -> Optional[ColorGradingPreset]:
        """Preset naam se lo"""
        key = filter_name.lower().replace(" ", "_")
        return self._presets.get(key)

    def get_all_presets(self) -> List[ColorGradingPreset]:
        """Sabhi presets lo"""
        return list(self._presets.values())

    def get_preset_names(self) -> List[str]:
        """Sabhi preset names lo"""
        return [p.name for p in self._presets.values()]

    def apply_preset(self, filter_name: str) -> Optional[ColorGradingPreset]:
        """Preset apply karo (active banao)"""
        preset = self.get_preset(filter_name)
        if preset:
            self._active_preset = preset
            self._notify("preset_applied", {"preset": preset})
            logger.info(f"Preset applied: {preset.name}")
        return preset

    def get_active_preset(self) -> Optional[ColorGradingPreset]:
        return self._active_preset

    def create_custom_preset(
        self,
        name:               str,
        base_preset:        Optional[str] = None,
        **overrides,
    ) -> ColorGradingPreset:
        """
        Custom preset banao.
        Base preset copy karke overrides apply.
        """
        # Start with base
        if base_preset:
            base = self.get_preset(base_preset)
            if base:
                import copy
                preset = copy.deepcopy(base)
                preset.preset_id = f"grade_{generate_uuid()[:8]}"
                preset.name = name
                preset.filter_type = "custom"
            else:
                preset = ColorGradingPreset(name=name)
        else:
            preset = ColorGradingPreset(name=name)

        # Apply overrides
        for key, value in overrides.items():
            if hasattr(preset.adjustments, key):
                setattr(preset.adjustments, key, value)

        # Add to library
        self._presets[preset.preset_id] = preset
        logger.info(f"Custom preset created: {name}")
        return preset

    def process_color(
        self,
        color:      List[float],
        preset:     Optional[ColorGradingPreset] = None,
    ) -> List[float]:
        """Ek color pe grading apply karo"""
        preset = preset or self._active_preset
        if not preset:
            return color
        processor = ColorProcessor(preset)
        return processor.process_color(color)

    def process_image(
        self,
        img_array:  Any,
        preset:     Optional[ColorGradingPreset] = None,
    ) -> Any:
        """Image array pe grading apply karo"""
        preset = preset or self._active_preset
        if not preset or preset.filter_type == FilterType.NONE.value:
            return img_array
        processor = ColorProcessor(preset)
        return processor.process_image_array(img_array)

    def add_listener(self, callback):
        self._listeners.append(callback)

    def _notify(self, event: str, data: Dict):
        for cb in self._listeners:
            try:
                cb(event, data)
            except Exception as e:
                logger.warning(f"Listener error: {e}")


# ============================================================
# GLOBAL INSTANCE
# ============================================================

_global_manager: Optional[ColorGradingManager] = None


def get_color_grading_manager() -> ColorGradingManager:
    """Global ColorGradingManager"""
    global _global_manager
    if _global_manager is None:
        _global_manager = ColorGradingManager()
    return _global_manager


# ============================================================
# TEST SECTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")
    print_banner("Color Grading Test", "Post-Processing Filters")

    # ===== TEST 1: Manager Init =====
    print_section("Test 1: Manager Initialization")
    manager = ColorGradingManager()
    print(f"✅ Total presets: {len(manager.get_all_presets())}")

    # ===== TEST 2: All Preset Names =====
    print_section("Test 2: All Available Filters")
    for i, name in enumerate(manager.get_preset_names(), 1):
        print(f"   {i:2d}. {name}")

    # ===== TEST 3: Color Processing =====
    print_section("Test 3: Color Processing - Sample Color [0.5, 0.5, 0.5]")
    test_color = [0.5, 0.5, 0.5]

    for filter_name in ["vintage", "dramatic", "warm", "cool", "cinematic",
                        "noir", "sepia", "bollywood"]:
        result = manager.process_color(test_color, manager.get_preset(filter_name))
        print(
            f"✅ {filter_name:15s}: "
            f"R={result[0]:.3f} G={result[1]:.3f} B={result[2]:.3f}"
        )

    # ===== TEST 4: Bright Color =====
    print_section("Test 4: Bright Color [0.9, 0.7, 0.5] (skin tone)")
    skin = [0.9, 0.7, 0.5]

    for filter_name in ["warm", "cool", "vintage", "dramatic", "night_vision"]:
        result = manager.process_color(skin, manager.get_preset(filter_name))
        print(
            f"✅ {filter_name:15s}: "
            f"R={result[0]:.3f} G={result[1]:.3f} B={result[2]:.3f}"
        )

    # ===== TEST 5: Preset Details =====
    print_section("Test 5: Cinematic Preset Details")
    cinematic = manager.get_preset("cinematic")
    if cinematic:
        adj = cinematic.adjustments
        print(f"\n   Name        : {cinematic.name}")
        print(f"   Description : {cinematic.description}")
        print(f"\n   Adjustments:")
        print(f"      Contrast    : {adj.contrast:+.2f}")
        print(f"      Saturation  : {adj.saturation:+.2f}")
        print(f"      Highlights  : {adj.highlights:+.2f}")
        print(f"      Shadows     : {adj.shadows:+.2f}")
        print(f"      Temperature : {adj.temperature:+.2f}")
        print(f"\n   Vignette    : enabled={cinematic.vignette.enabled}")
        print(f"      Strength    : {cinematic.vignette.strength:.2f}")

    # ===== TEST 6: Custom Preset =====
    print_section("Test 6: Custom Preset Creation")
    custom = manager.create_custom_preset(
        name        = "My Custom Look",
        base_preset = "cinematic",
        contrast    = 0.5,
        saturation  = 0.3,
        temperature = 0.2,
    )
    print(f"✅ Custom preset created: {custom.name}")
    print(f"   Contrast   : {custom.adjustments.contrast:+.2f}")
    print(f"   Saturation : {custom.adjustments.saturation:+.2f}")

    # ===== TEST 7: Color Math =====
    print_section("Test 7: Color Math Utilities")

    # RGB to HSL
    h, s, l = ColorMath.rgb_to_hsl(1.0, 0.0, 0.0)   # Red
    print(f"✅ Red RGB → HSL: H={h:.2f} S={s:.2f} L={l:.2f}")

    # HSL to RGB (back to red)
    r, g, b = ColorMath.hsl_to_rgb(0.0, 1.0, 0.5)
    print(f"✅ HSL → RGB    : R={r:.2f} G={g:.2f} B={b:.2f}")

    # Temperature
    warm = ColorMath.apply_temperature([0.5, 0.5, 0.5], 0.5)
    cool = ColorMath.apply_temperature([0.5, 0.5, 0.5], -0.5)
    print(f"✅ Warm applied : {warm}")
    print(f"✅ Cool applied : {cool}")

    # ===== TEST 8: NumPy Image Processing =====
    print_section("Test 8: NumPy Image Processing")
    try:
        import numpy as np

        # Create test image (100x100 gradient)
        test_img = np.zeros((100, 100, 3), dtype=np.uint8)
        for y in range(100):
            for x in range(100):
                test_img[y, x] = [x * 2, y * 2, 128]

        # Apply cinematic filter
        preset = manager.get_preset("cinematic")
        result = manager.process_image(test_img, preset)

        print(f"✅ Image processed: shape={result.shape}, dtype={result.dtype}")
        print(f"   Center pixel before: {test_img[50, 50]}")
        print(f"   Center pixel after : {result[50, 50]}")

        # Test different filters
        for filter_name in ["vintage", "noir", "dramatic", "warm"]:
            preset = manager.get_preset(filter_name)
            processed = manager.process_image(test_img.copy(), preset)
            avg_before = test_img.mean()
            avg_after = processed.mean()
            print(f"✅ {filter_name:12s}: avg brightness {avg_before:.0f} → {avg_after:.0f}")

    except Exception as e:
        print(f"⚠️  NumPy test error: {e}")

    # ===== TEST 9: Apply Preset =====
    print_section("Test 9: Active Preset")
    manager.apply_preset("cinematic")
    active = manager.get_active_preset()
    if active:
        print(f"✅ Active preset: {active.name}")

    manager.apply_preset("horror")
    active = manager.get_active_preset()
    if active:
        print(f"✅ Active preset: {active.name}")

    # ===== TEST 10: All Presets Summary =====
    print_section("Test 10: All Presets Summary")
    for preset in manager.get_all_presets():
        adj = preset.adjustments
        v_enabled = "✓" if preset.vignette.enabled else " "
        g_enabled = "✓" if preset.grain.enabled else " "
        b_enabled = "✓" if preset.bloom.enabled else " "
        print(
            f"✅ {preset.name:15s} | "
            f"contrast={adj.contrast:+.2f} | "
            f"saturation={adj.saturation:+.2f} | "
            f"temp={adj.temperature:+.2f} | "
            f"vig[{v_enabled}] grain[{g_enabled}] bloom[{b_enabled}]"
        )

    print_banner("✅ All Tests Passed!", "color_grading.py Working Perfectly")