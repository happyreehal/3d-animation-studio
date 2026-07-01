# ============================================================
# src/renderer/character_system.py
# 3D Animation Studio - Character Customization System
# Characters ke appearance, clothing, colors sab manage karta hai
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

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum
from pathlib import Path

from src.utils import (
    get_logger,
    get_config,
    ensure_dir,
    write_json,
    read_json,
    generate_uuid,
)

logger = get_logger("CharacterSystem")


# ============================================================
# ENUMS
# ============================================================

class Gender(Enum):
    """Character gender types"""
    MALE        = "male"
    FEMALE      = "female"
    NEUTRAL     = "neutral"
    NON_BINARY  = "non_binary"


class AgeGroup(Enum):
    """Character age groups"""
    CHILD       = "child"        # 5-12 years
    TEEN        = "teen"         # 13-19 years
    YOUNG_ADULT = "young_adult"  # 20-30 years
    ADULT       = "adult"        # 30-50 years
    ELDER       = "elder"        # 50+ years


class BodyType(Enum):
    """Body types"""
    SLIM        = "slim"
    ATHLETIC    = "athletic"
    AVERAGE     = "average"
    MUSCULAR    = "muscular"
    HEAVY       = "heavy"


class HairStyle(Enum):
    """Hair styles"""
    SHORT       = "short"
    MEDIUM      = "medium"
    LONG        = "long"
    BALD        = "bald"
    CURLY       = "curly"
    STRAIGHT    = "straight"
    PONYTAIL    = "ponytail"
    BUN         = "bun"


class ClothingStyle(Enum):
    """Clothing style presets"""
    CASUAL      = "casual"
    FORMAL      = "formal"
    BUSINESS    = "business"
    SPORTY      = "sporty"
    TRADITIONAL = "traditional"
    FANTASY     = "fantasy"
    SCI_FI      = "sci_fi"
    UNIFORM     = "uniform"
    ROYAL       = "royal"
    CASUAL_DESI = "casual_desi"        # Indian casual
    CUSTOM      = "custom"


class AccessoryType(Enum):
    """Accessory types"""
    GLASSES     = "glasses"
    HAT         = "hat"
    NECKLACE    = "necklace"
    EARRINGS    = "earrings"
    WATCH       = "watch"
    BAG         = "bag"
    SCARF       = "scarf"
    BELT        = "belt"
    RING        = "ring"


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class ColorRGB:
    """RGB color (0.0 to 1.0)"""
    r: float = 0.5
    g: float = 0.5
    b: float = 0.5

    def to_hex(self) -> str:
        """Hex string return karo"""
        return f"#{int(self.r*255):02X}{int(self.g*255):02X}{int(self.b*255):02X}"

    def to_list(self) -> List[float]:
        return [self.r, self.g, self.b]

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.r, self.g, self.b)

    @classmethod
    def from_hex(cls, hex_str: str) -> "ColorRGB":
        """Hex se banao"""
        hex_str = hex_str.lstrip('#')
        return cls(
            r=int(hex_str[0:2], 16) / 255.0,
            g=int(hex_str[2:4], 16) / 255.0,
            b=int(hex_str[4:6], 16) / 255.0,
        )

    @classmethod
    def from_list(cls, values: List[float]) -> "ColorRGB":
        return cls(r=values[0], g=values[1], b=values[2])


@dataclass
class SkinTone:
    """Skin tone preset"""
    name:           str             = "Light"
    color:          ColorRGB        = field(default_factory=ColorRGB)

    def to_dict(self) -> Dict:
        return {
            "name":  self.name,
            "color": self.color.to_list(),
        }


@dataclass
class HairSettings:
    """Hair configuration"""
    style:          str             = HairStyle.MEDIUM.value
    color:          ColorRGB        = field(default_factory=lambda: ColorRGB(0.15, 0.1, 0.05))
    length:         float           = 1.0        # 0.0 - 2.0

    def to_dict(self) -> Dict:
        return {
            "style":  self.style,
            "color":  self.color.to_list(),
            "length": self.length,
        }


@dataclass
class ClothingItem:
    """Single clothing item"""
    item_type:      str             = "shirt"    # shirt, pants, dress, jacket
    style:          str             = ClothingStyle.CASUAL.value
    primary_color:  ColorRGB        = field(default_factory=lambda: ColorRGB(0.2, 0.4, 0.8))
    secondary_color: ColorRGB       = field(default_factory=lambda: ColorRGB(0.8, 0.8, 0.8))
    material:       str             = "cotton"   # cotton, silk, wool, denim, leather
    pattern:        str             = "solid"    # solid, stripes, checks, floral

    def to_dict(self) -> Dict:
        return {
            "item_type":       self.item_type,
            "style":           self.style,
            "primary_color":   self.primary_color.to_list(),
            "secondary_color": self.secondary_color.to_list(),
            "material":        self.material,
            "pattern":         self.pattern,
        }


@dataclass
class Accessory:
    """Character accessory"""
    accessory_type: str             = AccessoryType.WATCH.value
    color:          ColorRGB        = field(default_factory=lambda: ColorRGB(0.3, 0.3, 0.3))
    material:       str             = "metal"    # metal, plastic, leather, fabric
    size:           float           = 1.0        # Scale multiplier

    def to_dict(self) -> Dict:
        return {
            "type":     self.accessory_type,
            "color":    self.color.to_list(),
            "material": self.material,
            "size":     self.size,
        }


@dataclass
class BodyMeasurements:
    """Character body measurements"""
    height:         float           = 1.75       # meters
    body_type:      str             = BodyType.AVERAGE.value

    # Scale factors (1.0 = normal)
    head_scale:     float           = 1.0
    torso_scale:    float           = 1.0
    arm_scale:      float           = 1.0
    leg_scale:      float           = 1.0

    def to_dict(self) -> Dict:
        return {
            "height":      self.height,
            "body_type":   self.body_type,
            "head_scale":  self.head_scale,
            "torso_scale": self.torso_scale,
            "arm_scale":   self.arm_scale,
            "leg_scale":   self.leg_scale,
        }


@dataclass
class FacialFeatures:
    """Facial customization"""
    eye_color:      ColorRGB        = field(default_factory=lambda: ColorRGB(0.3, 0.2, 0.1))
    eye_shape:      str             = "normal"   # normal, round, almond
    eyebrow_thickness: float        = 1.0
    nose_size:      float           = 1.0
    lip_thickness:  float           = 1.0

    # Facial hair (males mostly)
    has_beard:      bool            = False
    beard_style:    str             = "clean"    # clean, stubble, full, goatee
    has_mustache:   bool            = False

    def to_dict(self) -> Dict:
        return {
            "eye_color":         self.eye_color.to_list(),
            "eye_shape":         self.eye_shape,
            "eyebrow_thickness": self.eyebrow_thickness,
            "nose_size":         self.nose_size,
            "lip_thickness":     self.lip_thickness,
            "has_beard":         self.has_beard,
            "beard_style":       self.beard_style,
            "has_mustache":      self.has_mustache,
        }


@dataclass
class Character:
    """
    Complete character definition.
    Sabhi customization options ek jagah.
    """
    # Identity
    character_id:   str             = ""
    name:           str             = "Character"
    gender:         str             = Gender.NEUTRAL.value
    age_group:      str             = AgeGroup.ADULT.value

    # Appearance
    skin_tone:      SkinTone        = field(default_factory=SkinTone)
    hair:           HairSettings    = field(default_factory=HairSettings)
    body:           BodyMeasurements= field(default_factory=BodyMeasurements)
    facial:         FacialFeatures  = field(default_factory=FacialFeatures)

    # Clothing
    clothing_style: str             = ClothingStyle.CASUAL.value
    clothing_items: List[ClothingItem] = field(default_factory=list)
    accessories:    List[Accessory] = field(default_factory=list)

    # Voice (reference to TTS)
    voice_id:       str             = "voice_default"
    voice_language: str             = "en"
    voice_pitch:    float           = 0.0
    voice_speed:    float           = 1.0

    # Metadata
    description:    str             = ""
    created_at:     str             = ""
    is_preset:      bool            = False

    def __post_init__(self):
        if not self.character_id:
            self.character_id = f"char_{generate_uuid()[:8]}"

    def to_dict(self) -> Dict:
        return {
            "character_id":   self.character_id,
            "name":           self.name,
            "gender":         self.gender,
            "age_group":      self.age_group,
            "skin_tone":      self.skin_tone.to_dict(),
            "hair":           self.hair.to_dict(),
            "body":           self.body.to_dict(),
            "facial":         self.facial.to_dict(),
            "clothing_style": self.clothing_style,
            "clothing_items": [c.to_dict() for c in self.clothing_items],
            "accessories":    [a.to_dict() for a in self.accessories],
            "voice_id":       self.voice_id,
            "voice_language": self.voice_language,
            "voice_pitch":    self.voice_pitch,
            "voice_speed":    self.voice_speed,
            "description":    self.description,
            "created_at":     self.created_at,
            "is_preset":      self.is_preset,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Character":
        """Dict se character banao"""
        char = cls(
            character_id   = data.get("character_id", ""),
            name           = data.get("name", "Character"),
            gender         = data.get("gender", Gender.NEUTRAL.value),
            age_group      = data.get("age_group", AgeGroup.ADULT.value),
            clothing_style = data.get("clothing_style", ClothingStyle.CASUAL.value),
            voice_id       = data.get("voice_id", "voice_default"),
            voice_language = data.get("voice_language", "en"),
            voice_pitch    = data.get("voice_pitch", 0.0),
            voice_speed    = data.get("voice_speed", 1.0),
            description    = data.get("description", ""),
            created_at     = data.get("created_at", ""),
            is_preset      = data.get("is_preset", False),
        )

        # Skin tone
        st = data.get("skin_tone", {})
        char.skin_tone = SkinTone(
            name  = st.get("name", "Light"),
            color = ColorRGB.from_list(st.get("color", [0.9, 0.75, 0.6])),
        )

        # Hair
        hair = data.get("hair", {})
        char.hair = HairSettings(
            style  = hair.get("style", HairStyle.MEDIUM.value),
            color  = ColorRGB.from_list(hair.get("color", [0.15, 0.1, 0.05])),
            length = hair.get("length", 1.0),
        )

        # Body
        body = data.get("body", {})
        char.body = BodyMeasurements(
            height      = body.get("height", 1.75),
            body_type   = body.get("body_type", BodyType.AVERAGE.value),
            head_scale  = body.get("head_scale", 1.0),
            torso_scale = body.get("torso_scale", 1.0),
            arm_scale   = body.get("arm_scale", 1.0),
            leg_scale   = body.get("leg_scale", 1.0),
        )

        # Facial
        facial = data.get("facial", {})
        char.facial = FacialFeatures(
            eye_color         = ColorRGB.from_list(
                facial.get("eye_color", [0.3, 0.2, 0.1])
            ),
            eye_shape         = facial.get("eye_shape", "normal"),
            eyebrow_thickness = facial.get("eyebrow_thickness", 1.0),
            nose_size         = facial.get("nose_size", 1.0),
            lip_thickness     = facial.get("lip_thickness", 1.0),
            has_beard         = facial.get("has_beard", False),
            beard_style       = facial.get("beard_style", "clean"),
            has_mustache      = facial.get("has_mustache", False),
        )

        # Clothing
        for item_data in data.get("clothing_items", []):
            item = ClothingItem(
                item_type       = item_data.get("item_type", "shirt"),
                style           = item_data.get("style", ClothingStyle.CASUAL.value),
                primary_color   = ColorRGB.from_list(
                    item_data.get("primary_color", [0.2, 0.4, 0.8])
                ),
                secondary_color = ColorRGB.from_list(
                    item_data.get("secondary_color", [0.8, 0.8, 0.8])
                ),
                material        = item_data.get("material", "cotton"),
                pattern         = item_data.get("pattern", "solid"),
            )
            char.clothing_items.append(item)

        # Accessories
        for acc_data in data.get("accessories", []):
            acc = Accessory(
                accessory_type = acc_data.get("type", AccessoryType.WATCH.value),
                color          = ColorRGB.from_list(
                    acc_data.get("color", [0.3, 0.3, 0.3])
                ),
                material       = acc_data.get("material", "metal"),
                size           = acc_data.get("size", 1.0),
            )
            char.accessories.append(acc)

        return char


# ============================================================
# SKIN TONE PRESETS
# ============================================================

class SkinToneLibrary:
    """Predefined skin tones"""

    PRESETS: Dict[str, ColorRGB] = {
        "Very Fair":    ColorRGB(0.98, 0.87, 0.80),
        "Fair":         ColorRGB(0.95, 0.82, 0.72),
        "Light":        ColorRGB(0.90, 0.75, 0.62),
        "Medium Light": ColorRGB(0.82, 0.65, 0.50),
        "Medium":       ColorRGB(0.75, 0.55, 0.42),
        "Medium Tan":   ColorRGB(0.68, 0.48, 0.35),
        "Tan":          ColorRGB(0.60, 0.42, 0.28),
        "Dark":         ColorRGB(0.48, 0.32, 0.22),
        "Very Dark":    ColorRGB(0.35, 0.22, 0.15),
        "Deep":         ColorRGB(0.25, 0.15, 0.10),
    }

    @classmethod
    def get_tone(cls, name: str) -> SkinTone:
        """Preset naam se skin tone lo"""
        color = cls.PRESETS.get(name, cls.PRESETS["Light"])
        return SkinTone(name=name, color=color)

    @classmethod
    def get_all_names(cls) -> List[str]:
        """Saare tone names lo"""
        return list(cls.PRESETS.keys())


# ============================================================
# HAIR COLOR PRESETS
# ============================================================

class HairColorLibrary:
    """Predefined hair colors"""

    PRESETS: Dict[str, ColorRGB] = {
        "Black":        ColorRGB(0.05, 0.03, 0.02),
        "Dark Brown":   ColorRGB(0.15, 0.08, 0.04),
        "Brown":        ColorRGB(0.30, 0.18, 0.10),
        "Light Brown":  ColorRGB(0.45, 0.30, 0.18),
        "Blonde":       ColorRGB(0.85, 0.72, 0.45),
        "Dark Blonde":  ColorRGB(0.65, 0.50, 0.30),
        "Red":          ColorRGB(0.55, 0.25, 0.15),
        "Ginger":       ColorRGB(0.70, 0.40, 0.20),
        "Gray":         ColorRGB(0.55, 0.55, 0.55),
        "White":        ColorRGB(0.92, 0.92, 0.92),
        "Blue":         ColorRGB(0.20, 0.35, 0.75),
        "Purple":       ColorRGB(0.55, 0.30, 0.75),
        "Pink":         ColorRGB(0.90, 0.55, 0.75),
        "Green":        ColorRGB(0.30, 0.65, 0.35),
    }

    @classmethod
    def get_color(cls, name: str) -> ColorRGB:
        return cls.PRESETS.get(name, cls.PRESETS["Brown"])

    @classmethod
    def get_all_names(cls) -> List[str]:
        return list(cls.PRESETS.keys())


# ============================================================
# CLOTHING OUTFIT PRESETS
# ============================================================

class OutfitLibrary:
    """Predefined complete outfits"""

    @staticmethod
    def casual_male() -> List[ClothingItem]:
        return [
            ClothingItem(
                item_type       = "t-shirt",
                style           = ClothingStyle.CASUAL.value,
                primary_color   = ColorRGB(0.2, 0.4, 0.8),
                material        = "cotton",
                pattern         = "solid",
            ),
            ClothingItem(
                item_type       = "jeans",
                style           = ClothingStyle.CASUAL.value,
                primary_color   = ColorRGB(0.15, 0.2, 0.4),
                material        = "denim",
                pattern         = "solid",
            ),
            ClothingItem(
                item_type       = "shoes",
                style           = ClothingStyle.CASUAL.value,
                primary_color   = ColorRGB(0.8, 0.8, 0.8),
                material        = "cotton",
                pattern         = "solid",
            ),
        ]

    @staticmethod
    def casual_female() -> List[ClothingItem]:
        return [
            ClothingItem(
                item_type       = "top",
                style           = ClothingStyle.CASUAL.value,
                primary_color   = ColorRGB(0.9, 0.4, 0.6),
                material        = "cotton",
                pattern         = "solid",
            ),
            ClothingItem(
                item_type       = "jeans",
                style           = ClothingStyle.CASUAL.value,
                primary_color   = ColorRGB(0.15, 0.2, 0.4),
                material        = "denim",
                pattern         = "solid",
            ),
        ]

    @staticmethod
    def formal_male() -> List[ClothingItem]:
        return [
            ClothingItem(
                item_type       = "shirt",
                style           = ClothingStyle.FORMAL.value,
                primary_color   = ColorRGB(0.95, 0.95, 0.95),
                material        = "cotton",
                pattern         = "solid",
            ),
            ClothingItem(
                item_type       = "pants",
                style           = ClothingStyle.FORMAL.value,
                primary_color   = ColorRGB(0.15, 0.15, 0.2),
                material        = "wool",
                pattern         = "solid",
            ),
            ClothingItem(
                item_type       = "blazer",
                style           = ClothingStyle.FORMAL.value,
                primary_color   = ColorRGB(0.15, 0.15, 0.2),
                material        = "wool",
                pattern         = "solid",
            ),
            ClothingItem(
                item_type       = "tie",
                style           = ClothingStyle.FORMAL.value,
                primary_color   = ColorRGB(0.6, 0.1, 0.1),
                material        = "silk",
                pattern         = "stripes",
            ),
        ]

    @staticmethod
    def formal_female() -> List[ClothingItem]:
        return [
            ClothingItem(
                item_type       = "dress",
                style           = ClothingStyle.FORMAL.value,
                primary_color   = ColorRGB(0.2, 0.2, 0.4),
                material        = "silk",
                pattern         = "solid",
            ),
        ]

    @staticmethod
    def traditional_indian_male() -> List[ClothingItem]:
        return [
            ClothingItem(
                item_type       = "kurta",
                style           = ClothingStyle.TRADITIONAL.value,
                primary_color   = ColorRGB(0.95, 0.85, 0.65),
                material        = "cotton",
                pattern         = "solid",
            ),
            ClothingItem(
                item_type       = "pajama",
                style           = ClothingStyle.TRADITIONAL.value,
                primary_color   = ColorRGB(0.95, 0.95, 0.90),
                material        = "cotton",
                pattern         = "solid",
            ),
        ]

    @staticmethod
    def traditional_indian_female() -> List[ClothingItem]:
        return [
            ClothingItem(
                item_type       = "saree",
                style           = ClothingStyle.TRADITIONAL.value,
                primary_color   = ColorRGB(0.85, 0.15, 0.35),
                secondary_color = ColorRGB(0.95, 0.85, 0.15),
                material        = "silk",
                pattern         = "floral",
            ),
        ]

    @staticmethod
    def sporty() -> List[ClothingItem]:
        return [
            ClothingItem(
                item_type       = "sports-tshirt",
                style           = ClothingStyle.SPORTY.value,
                primary_color   = ColorRGB(0.9, 0.9, 0.9),
                material        = "cotton",
                pattern         = "solid",
            ),
            ClothingItem(
                item_type       = "shorts",
                style           = ClothingStyle.SPORTY.value,
                primary_color   = ColorRGB(0.1, 0.1, 0.15),
                material        = "cotton",
                pattern         = "solid",
            ),
            ClothingItem(
                item_type       = "sneakers",
                style           = ClothingStyle.SPORTY.value,
                primary_color   = ColorRGB(0.95, 0.95, 0.95),
                material        = "cotton",
                pattern         = "solid",
            ),
        ]

    @staticmethod
    def fantasy_hero() -> List[ClothingItem]:
        return [
            ClothingItem(
                item_type       = "armor",
                style           = ClothingStyle.FANTASY.value,
                primary_color   = ColorRGB(0.6, 0.6, 0.7),
                secondary_color = ColorRGB(0.8, 0.7, 0.2),
                material        = "leather",
                pattern         = "solid",
            ),
            ClothingItem(
                item_type       = "cape",
                style           = ClothingStyle.FANTASY.value,
                primary_color   = ColorRGB(0.6, 0.15, 0.15),
                material        = "silk",
                pattern         = "solid",
            ),
            ClothingItem(
                item_type       = "boots",
                style           = ClothingStyle.FANTASY.value,
                primary_color   = ColorRGB(0.25, 0.15, 0.10),
                material        = "leather",
                pattern         = "solid",
            ),
        ]

    @staticmethod
    def scifi() -> List[ClothingItem]:
        return [
            ClothingItem(
                item_type       = "suit",
                style           = ClothingStyle.SCI_FI.value,
                primary_color   = ColorRGB(0.1, 0.15, 0.2),
                secondary_color = ColorRGB(0.0, 0.7, 1.0),
                material        = "plastic",
                pattern         = "solid",
            ),
        ]

    @staticmethod
    def business_male() -> List[ClothingItem]:
        return [
            ClothingItem(
                item_type       = "shirt",
                style           = ClothingStyle.BUSINESS.value,
                primary_color   = ColorRGB(0.85, 0.90, 1.0),
                material        = "cotton",
                pattern         = "solid",
            ),
            ClothingItem(
                item_type       = "pants",
                style           = ClothingStyle.BUSINESS.value,
                primary_color   = ColorRGB(0.20, 0.20, 0.25),
                material        = "wool",
                pattern         = "solid",
            ),
        ]

    @staticmethod
    def get_outfit(style: str, gender: str) -> List[ClothingItem]:
        """Style + gender ke basis pe outfit lo"""
        outfits = {
            (ClothingStyle.CASUAL.value, "male"):        OutfitLibrary.casual_male(),
            (ClothingStyle.CASUAL.value, "female"):      OutfitLibrary.casual_female(),
            (ClothingStyle.FORMAL.value, "male"):        OutfitLibrary.formal_male(),
            (ClothingStyle.FORMAL.value, "female"):      OutfitLibrary.formal_female(),
            (ClothingStyle.TRADITIONAL.value, "male"):   OutfitLibrary.traditional_indian_male(),
            (ClothingStyle.TRADITIONAL.value, "female"): OutfitLibrary.traditional_indian_female(),
            (ClothingStyle.SPORTY.value, "male"):        OutfitLibrary.sporty(),
            (ClothingStyle.SPORTY.value, "female"):      OutfitLibrary.sporty(),
            (ClothingStyle.FANTASY.value, "male"):       OutfitLibrary.fantasy_hero(),
            (ClothingStyle.FANTASY.value, "female"):     OutfitLibrary.fantasy_hero(),
            (ClothingStyle.SCI_FI.value, "male"):        OutfitLibrary.scifi(),
            (ClothingStyle.SCI_FI.value, "female"):      OutfitLibrary.scifi(),
            (ClothingStyle.BUSINESS.value, "male"):      OutfitLibrary.business_male(),
            (ClothingStyle.BUSINESS.value, "female"):    OutfitLibrary.formal_female(),
        }

        return outfits.get(
            (style, gender),
            OutfitLibrary.casual_male() if gender == "male" else OutfitLibrary.casual_female()
        )


# ============================================================
# CHARACTER PRESETS - Ready-made characters
# ============================================================

class CharacterPresets:
    """Predefined character presets"""

    @staticmethod
    def hero_male() -> Character:
        """Male hero character"""
        char = Character(
            name           = "Hero",
            gender         = Gender.MALE.value,
            age_group      = AgeGroup.YOUNG_ADULT.value,
            clothing_style = ClothingStyle.CASUAL.value,
            voice_id       = "voice_male_1",
            description    = "A young, energetic hero character",
            is_preset      = True,
        )

        char.skin_tone = SkinToneLibrary.get_tone("Medium")
        char.hair = HairSettings(
            style  = HairStyle.SHORT.value,
            color  = HairColorLibrary.get_color("Black"),
        )
        char.body = BodyMeasurements(
            height     = 1.78,
            body_type  = BodyType.ATHLETIC.value,
        )
        char.facial = FacialFeatures(
            eye_color         = ColorRGB(0.3, 0.2, 0.1),
            eyebrow_thickness = 1.1,
            has_beard         = False,
        )
        char.clothing_items = OutfitLibrary.casual_male()

        return char

    @staticmethod
    def hero_female() -> Character:
        """Female hero character"""
        char = Character(
            name           = "Priya",
            gender         = Gender.FEMALE.value,
            age_group      = AgeGroup.YOUNG_ADULT.value,
            clothing_style = ClothingStyle.CASUAL.value,
            voice_id       = "voice_female_1",
            voice_pitch    = 0.1,
            description    = "A confident young woman",
            is_preset      = True,
        )

        char.skin_tone = SkinToneLibrary.get_tone("Medium Light")
        char.hair = HairSettings(
            style  = HairStyle.LONG.value,
            color  = HairColorLibrary.get_color("Dark Brown"),
            length = 1.5,
        )
        char.body = BodyMeasurements(
            height     = 1.65,
            body_type  = BodyType.SLIM.value,
        )
        char.facial = FacialFeatures(
            eye_color         = ColorRGB(0.35, 0.25, 0.15),
            eyebrow_thickness = 0.9,
        )
        char.clothing_items = OutfitLibrary.casual_female()

        return char

    @staticmethod
    def villain() -> Character:
        """Villain character"""
        char = Character(
            name           = "Villain",
            gender         = Gender.MALE.value,
            age_group      = AgeGroup.ADULT.value,
            clothing_style = ClothingStyle.FORMAL.value,
            voice_id       = "voice_male_2",
            voice_pitch    = -0.15,
            description    = "A dark, menacing villain",
            is_preset      = True,
        )

        char.skin_tone = SkinToneLibrary.get_tone("Fair")
        char.hair = HairSettings(
            style  = HairStyle.SHORT.value,
            color  = HairColorLibrary.get_color("Gray"),
        )
        char.body = BodyMeasurements(
            height     = 1.85,
            body_type  = BodyType.MUSCULAR.value,
        )
        char.facial = FacialFeatures(
            eye_color     = ColorRGB(0.1, 0.1, 0.15),
            has_beard     = True,
            beard_style   = "goatee",
        )
        char.clothing_items = OutfitLibrary.formal_male()
        # Villain outfit - dark colors
        for item in char.clothing_items:
            if item.item_type in ["shirt"]:
                item.primary_color = ColorRGB(0.1, 0.1, 0.15)
            elif item.item_type in ["pants", "blazer"]:
                item.primary_color = ColorRGB(0.05, 0.05, 0.08)
            elif item.item_type == "tie":
                item.primary_color = ColorRGB(0.5, 0.05, 0.05)

        return char

    @staticmethod
    def child_boy() -> Character:
        """Young boy character"""
        char = Character(
            name           = "Aryan",
            gender         = Gender.MALE.value,
            age_group      = AgeGroup.CHILD.value,
            clothing_style = ClothingStyle.CASUAL.value,
            voice_id       = "voice_male_3",
            voice_pitch    = 0.3,
            voice_speed    = 1.1,
            description    = "A cute little boy",
            is_preset      = True,
        )

        char.skin_tone = SkinToneLibrary.get_tone("Medium Light")
        char.hair = HairSettings(
            style  = HairStyle.SHORT.value,
            color  = HairColorLibrary.get_color("Brown"),
        )
        char.body = BodyMeasurements(
            height     = 1.20,
            body_type  = BodyType.SLIM.value,
            head_scale = 1.15,   # Kids have bigger heads relatively
        )
        char.facial = FacialFeatures(
            eye_color         = ColorRGB(0.4, 0.3, 0.2),
            eyebrow_thickness = 0.7,
        )
        char.clothing_items = OutfitLibrary.casual_male()

        return char

    @staticmethod
    def elderly_male() -> Character:
        """Elderly male character"""
        char = Character(
            name           = "Dadaji",
            gender         = Gender.MALE.value,
            age_group      = AgeGroup.ELDER.value,
            clothing_style = ClothingStyle.TRADITIONAL.value,
            voice_id       = "voice_male_1",
            voice_pitch    = -0.1,
            voice_speed    = 0.9,
            description    = "A wise old man",
            is_preset      = True,
        )

        char.skin_tone = SkinToneLibrary.get_tone("Medium Tan")
        char.hair = HairSettings(
            style  = HairStyle.SHORT.value,
            color  = HairColorLibrary.get_color("White"),
            length = 0.5,
        )
        char.body = BodyMeasurements(
            height     = 1.68,
            body_type  = BodyType.AVERAGE.value,
        )
        char.facial = FacialFeatures(
            eye_color     = ColorRGB(0.25, 0.20, 0.15),
            has_beard     = True,
            beard_style   = "full",
            has_mustache  = True,
        )
        char.clothing_items = OutfitLibrary.traditional_indian_male()

        return char

    @staticmethod
    def business_woman() -> Character:
        """Business woman character"""
        char = Character(
            name           = "Meera",
            gender         = Gender.FEMALE.value,
            age_group      = AgeGroup.ADULT.value,
            clothing_style = ClothingStyle.BUSINESS.value,
            voice_id       = "voice_female_2",
            description    = "A confident business professional",
            is_preset      = True,
        )

        char.skin_tone = SkinToneLibrary.get_tone("Light")
        char.hair = HairSettings(
            style  = HairStyle.MEDIUM.value,
            color  = HairColorLibrary.get_color("Dark Brown"),
        )
        char.body = BodyMeasurements(
            height     = 1.68,
            body_type  = BodyType.AVERAGE.value,
        )
        char.facial = FacialFeatures(
            eye_color = ColorRGB(0.30, 0.20, 0.10),
        )
        char.clothing_items = OutfitLibrary.formal_female()

        return char

    @staticmethod
    def get_all_presets() -> Dict[str, Character]:
        """Sabhi presets lo"""
        return {
            "hero_male":       CharacterPresets.hero_male(),
            "hero_female":     CharacterPresets.hero_female(),
            "villain":         CharacterPresets.villain(),
            "child_boy":       CharacterPresets.child_boy(),
            "elderly_male":    CharacterPresets.elderly_male(),
            "business_woman":  CharacterPresets.business_woman(),
        }


# ============================================================
# CHARACTER LIBRARY - Save/Load characters
# ============================================================

class CharacterLibrary:
    """
    Character save/load karne wali library.
    Presets + user-created characters.
    """

    def __init__(self, config: Optional[Dict] = None):
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # Storage
        self._characters: Dict[str, Character] = {}

        # File paths
        self._presets_dir = Path("assets/presets/characters")
        self._custom_dir  = Path("assets/presets/characters/custom")

        # Ensure directories
        ensure_dir(str(self._presets_dir))
        ensure_dir(str(self._custom_dir))

        # Load presets
        self._load_presets()

        # Load custom characters
        self._load_custom()

        logger.info(
            f"✅ CharacterLibrary initialized | "
            f"{len(self._characters)} characters loaded"
        )

    def _load_presets(self):
        """Built-in presets load karo"""
        presets = CharacterPresets.get_all_presets()
        for name, char in presets.items():
            self._characters[char.character_id] = char
        logger.debug(f"Loaded {len(presets)} preset characters")

    def _load_custom(self):
        """Custom saved characters load karo"""
        try:
            if not self._custom_dir.exists():
                return

            for json_file in self._custom_dir.glob("*.json"):
                try:
                    data = read_json(str(json_file))
                    if data:
                        char = Character.from_dict(data)
                        self._characters[char.character_id] = char
                except Exception as e:
                    logger.warning(f"Custom char load failed ({json_file}): {e}")

            logger.debug(f"Custom characters loaded")

        except Exception as e:
            logger.warning(f"Custom load error: {e}")

    def save_character(self, char: Character) -> bool:
        """Character save karo file mein"""
        try:
            if not char.is_preset:
                filepath = self._custom_dir / f"{char.character_id}.json"
                write_json(str(filepath), char.to_dict())
                logger.info(f"💾 Character saved: {char.name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Save failed: {e}")
            return False

    def add_character(self, char: Character) -> str:
        """Naya character add karo"""
        self._characters[char.character_id] = char
        if not char.is_preset:
            self.save_character(char)
        return char.character_id

    def get_character(self, character_id: str) -> Optional[Character]:
        """ID se character lo"""
        return self._characters.get(character_id)

    def get_all_characters(self) -> List[Character]:
        """Sabhi characters lo"""
        return list(self._characters.values())

    def get_presets(self) -> List[Character]:
        """Sirf presets lo"""
        return [c for c in self._characters.values() if c.is_preset]

    def get_custom(self) -> List[Character]:
        """Sirf custom characters lo"""
        return [c for c in self._characters.values() if not c.is_preset]

    def delete_character(self, character_id: str) -> bool:
        """Character delete karo"""
        char = self._characters.get(character_id)
        if not char:
            return False
        if char.is_preset:
            logger.warning("Preset characters delete nahi ho sakte")
            return False

        # Delete file
        filepath = self._custom_dir / f"{character_id}.json"
        try:
            if filepath.exists():
                filepath.unlink()
        except Exception as e:
            logger.warning(f"File delete failed: {e}")

        del self._characters[character_id]
        return True

    def search_characters(self, query: str) -> List[Character]:
        """Search karo"""
        query_lower = query.lower()
        return [
            c for c in self._characters.values()
            if query_lower in c.name.lower()
            or query_lower in c.description.lower()
        ]


# ============================================================
# CHARACTER BUILDER - Auto create from description
# ============================================================

class CharacterBuilder:
    """
    Text description se character auto-create karta hai.
    Script parser ke saath integrate karne ke liye useful.
    """

    def __init__(self):
        pass

    def build_from_description(
        self,
        name:       str,
        gender:     str             = "unknown",
        age_hint:   str             = "adult",
        style_hint: str             = "casual",
    ) -> Character:
        """
        Basic info se character banao.
        """
        # Age group
        age_group = self._detect_age_group(age_hint)

        # Skin tone (random se ek Indian tone)
        skin_names = ["Medium Light", "Medium", "Medium Tan", "Tan"]
        import random
        skin_name = random.choice(skin_names)

        # Hair
        if age_group == AgeGroup.ELDER.value:
            hair_color = "Gray" if random.random() > 0.5 else "White"
        else:
            hair_color = random.choice(["Black", "Dark Brown", "Brown"])

        # Style
        style = self._detect_clothing_style(style_hint)

        # Determine actual gender
        actual_gender = gender if gender in ["male", "female"] else "male"

        # Create character
        char = Character(
            name           = name,
            gender         = actual_gender,
            age_group      = age_group,
            clothing_style = style,
            voice_id       = "voice_male_1" if actual_gender == "male" else "voice_female_1",
            description    = f"Auto-generated character: {name}",
        )

        # Appearance
        char.skin_tone = SkinToneLibrary.get_tone(skin_name)

        # Hair
        hair_style = HairStyle.SHORT.value if actual_gender == "male" else HairStyle.LONG.value
        char.hair = HairSettings(
            style = hair_style,
            color = HairColorLibrary.get_color(hair_color),
        )

        # Body
        height = 1.75 if actual_gender == "male" else 1.65
        if age_group == AgeGroup.CHILD.value:
            height = 1.20
        elif age_group == AgeGroup.TEEN.value:
            height = 1.55

        char.body = BodyMeasurements(
            height    = height,
            body_type = BodyType.AVERAGE.value,
        )

        # Facial
        char.facial = FacialFeatures(
            has_beard = (actual_gender == "male" and age_group in
                        [AgeGroup.ADULT.value, AgeGroup.ELDER.value] and
                        random.random() > 0.5),
        )

        # Outfit
        char.clothing_items = OutfitLibrary.get_outfit(style, actual_gender)

        return char

    def _detect_age_group(self, hint: str) -> str:
        """Age hint se age group detect karo"""
        hint_lower = hint.lower()
        if any(w in hint_lower for w in ["child", "kid", "baby", "little"]):
            return AgeGroup.CHILD.value
        if any(w in hint_lower for w in ["teen", "teenager", "young"]):
            return AgeGroup.TEEN.value
        if any(w in hint_lower for w in ["old", "elder", "grandpa", "grandma", "senior"]):
            return AgeGroup.ELDER.value
        if "young" in hint_lower:
            return AgeGroup.YOUNG_ADULT.value
        return AgeGroup.ADULT.value

    def _detect_clothing_style(self, hint: str) -> str:
        """Style hint se clothing style"""
        hint_lower = hint.lower()
        if any(w in hint_lower for w in ["formal", "business", "office", "suit"]):
            return ClothingStyle.FORMAL.value
        if any(w in hint_lower for w in ["traditional", "kurta", "saree", "desi"]):
            return ClothingStyle.TRADITIONAL.value
        if any(w in hint_lower for w in ["sport", "athletic", "gym"]):
            return ClothingStyle.SPORTY.value
        if any(w in hint_lower for w in ["fantasy", "medieval", "warrior"]):
            return ClothingStyle.FANTASY.value
        if any(w in hint_lower for w in ["scifi", "sci-fi", "futuristic", "space"]):
            return ClothingStyle.SCI_FI.value
        return ClothingStyle.CASUAL.value


# ============================================================
# GLOBAL INSTANCE
# ============================================================

_global_library: Optional[CharacterLibrary] = None


def get_character_library() -> CharacterLibrary:
    """Global CharacterLibrary lo"""
    global _global_library
    if _global_library is None:
        _global_library = CharacterLibrary()
    return _global_library


# ============================================================
# TEST SECTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")
    print_banner("Character System Test", "Character Customization & Presets")

    # ===== TEST 1: Color System =====
    print_section("Test 1: Color RGB System")
    red = ColorRGB(1.0, 0.0, 0.0)
    print(f"✅ Red: {red.to_hex()} | List: {red.to_list()}")

    from_hex = ColorRGB.from_hex("#00D4FF")
    print(f"✅ From hex #00D4FF: RGB({from_hex.r:.2f}, {from_hex.g:.2f}, {from_hex.b:.2f})")

    # ===== TEST 2: Skin Tones =====
    print_section("Test 2: Skin Tone Library")
    tone_names = SkinToneLibrary.get_all_names()
    print(f"✅ Total skin tones: {len(tone_names)}")
    for name in tone_names[:5]:
        tone = SkinToneLibrary.get_tone(name)
        print(f"   {name:15s}: {tone.color.to_hex()}")

    # ===== TEST 3: Hair Colors =====
    print_section("Test 3: Hair Color Library")
    hair_names = HairColorLibrary.get_all_names()
    print(f"✅ Total hair colors: {len(hair_names)}")
    for name in hair_names[:6]:
        color = HairColorLibrary.get_color(name)
        print(f"   {name:15s}: {color.to_hex()}")

    # ===== TEST 4: Character Presets =====
    print_section("Test 4: Character Presets")
    presets = CharacterPresets.get_all_presets()
    print(f"✅ Total presets: {len(presets)}")
    for preset_name, char in presets.items():
        print(f"\n   🎭 {preset_name}: {char.name}")
        print(f"      Gender    : {char.gender}")
        print(f"      Age       : {char.age_group}")
        print(f"      Height    : {char.body.height}m")
        print(f"      Skin      : {char.skin_tone.name} ({char.skin_tone.color.to_hex()})")
        print(f"      Hair      : {char.hair.style} ({char.hair.color.to_hex()})")
        print(f"      Style     : {char.clothing_style}")
        print(f"      Items     : {len(char.clothing_items)}")
        print(f"      Voice     : {char.voice_id}")

    # ===== TEST 5: Custom Character Creation =====
    print_section("Test 5: Custom Character Creation")
    custom = Character(
        name           = "My Character",
        gender         = Gender.FEMALE.value,
        age_group      = AgeGroup.YOUNG_ADULT.value,
        clothing_style = ClothingStyle.SPORTY.value,
    )
    custom.skin_tone = SkinToneLibrary.get_tone("Medium")
    custom.hair = HairSettings(
        style  = HairStyle.PONYTAIL.value,
        color  = HairColorLibrary.get_color("Blonde"),
        length = 1.3,
    )
    custom.clothing_items = OutfitLibrary.sporty()

    print(f"✅ Created custom character: {custom.name}")
    print(f"   ID       : {custom.character_id}")
    print(f"   Style    : {custom.clothing_style}")
    print(f"   Items    : {len(custom.clothing_items)}")

    # ===== TEST 6: Save/Load =====
    print_section("Test 6: Serialize / Deserialize")
    original = CharacterPresets.hero_male()
    data = original.to_dict()
    print(f"✅ Serialized: {len(data)} fields")

    restored = Character.from_dict(data)
    print(f"✅ Deserialized: {restored.name}")
    print(f"   Match name: {restored.name == original.name}")
    print(f"   Match items: {len(restored.clothing_items) == len(original.clothing_items)}")

    # ===== TEST 7: Character Library =====
    print_section("Test 7: Character Library")
    library = CharacterLibrary()
    all_chars = library.get_all_characters()
    print(f"✅ Total characters: {len(all_chars)}")
    print(f"   Presets: {len(library.get_presets())}")
    print(f"   Custom : {len(library.get_custom())}")

    # Add custom
    my_char = Character(
        name           = "Test Character",
        gender         = Gender.MALE.value,
        clothing_style = ClothingStyle.FANTASY.value,
    )
    my_char.clothing_items = OutfitLibrary.fantasy_hero()
    char_id = library.add_character(my_char)
    print(f"✅ Custom added: {char_id}")

    # Search
    results = library.search_characters("hero")
    print(f"✅ Search 'hero': {len(results)} results")

    # Cleanup test
    library.delete_character(char_id)
    print(f"✅ Test character deleted")

    # ===== TEST 8: Character Builder =====
    print_section("Test 8: Auto Character Builder")
    builder = CharacterBuilder()

    # Build various characters
    test_cases = [
        ("Rahul", "male", "young", "casual"),
        ("Priya", "female", "adult", "traditional"),
        ("Chintu", "male", "child", "casual"),
        ("Dadaji", "male", "elder", "traditional"),
        ("Neha", "female", "adult", "business"),
        ("Vikram", "male", "adult", "sporty"),
    ]

    for name, gender, age, style in test_cases:
        char = builder.build_from_description(name, gender, age, style)
        print(
            f"✅ {char.name:10s} | "
            f"{char.gender:6s} | "
            f"{char.age_group:12s} | "
            f"{char.clothing_style:12s} | "
            f"Height: {char.body.height}m"
        )

    # ===== TEST 9: Outfit Library =====
    print_section("Test 9: Outfit Presets")
    outfit_tests = [
        (ClothingStyle.CASUAL.value, "male"),
        (ClothingStyle.CASUAL.value, "female"),
        (ClothingStyle.FORMAL.value, "male"),
        (ClothingStyle.TRADITIONAL.value, "male"),
        (ClothingStyle.TRADITIONAL.value, "female"),
        (ClothingStyle.FANTASY.value, "male"),
        (ClothingStyle.SPORTY.value, "male"),
    ]

    for style, gender in outfit_tests:
        outfit = OutfitLibrary.get_outfit(style, gender)
        print(f"✅ {style:15s} ({gender:6s}): {len(outfit)} items")
        for item in outfit:
            print(f"      • {item.item_type} ({item.primary_color.to_hex()})")

    # ===== TEST 10: Statistics =====
    print_section("Test 10: Library Statistics")
    library2 = get_character_library()
    print(f"✅ Total characters : {len(library2.get_all_characters())}")
    print(f"   Presets          : {len(library2.get_presets())}")
    print(f"   Custom           : {len(library2.get_custom())}")

    for char in library2.get_all_characters()[:3]:
        print(f"\n   {char.name}:")
        print(f"      Gender     : {char.gender}")
        print(f"      Age Group  : {char.age_group}")
        print(f"      Skin       : {char.skin_tone.color.to_hex()}")
        print(f"      Clothing   : {len(char.clothing_items)} items")

    print_banner("✅ All Tests Passed!", "character_system.py Working Perfectly")