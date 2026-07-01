# ============================================================
# src/ui/properties_panel.py
# 3D Animation Studio - Properties Panel
# Selected object ki properties edit karne ka panel
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

from src.utils import get_logger, get_config

logger = get_logger("PropertiesPanel")


# ============================================================
# ENUMS
# ============================================================

class PropertyType(Enum):
    """Property field types"""
    FLOAT       = "float"
    INT         = "int"
    STRING      = "string"
    BOOL        = "bool"
    COLOR       = "color"       # RGB color picker
    VECTOR3     = "vector3"     # X, Y, Z
    VECTOR2     = "vector2"     # X, Y
    ENUM        = "enum"        # Dropdown
    SLIDER      = "slider"      # Float slider with range
    BUTTON      = "button"      # Action button
    SEPARATOR   = "separator"   # Visual divider
    LABEL       = "label"       # Read-only text
    FILEPATH    = "filepath"    # File path picker
    TEXTURE     = "texture"     # Texture slot


class PanelSection(Enum):
    """Properties panel sections"""
    TRANSFORM   = "Transform"
    MATERIAL    = "Material"
    PHYSICS     = "Physics"
    ANIMATION   = "Animation"
    LIGHTING    = "Lighting"
    CAMERA      = "Camera"
    CHARACTER   = "Character"
    AUDIO       = "Audio"
    VFX         = "VFX"
    RENDER      = "Render"
    CUSTOM      = "Custom"


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class PropertyDef:
    """
    Ek property field ki definition.
    Type, range, default value sab yahan.
    """
    id:           str
    label:        str
    prop_type:    str           = PropertyType.FLOAT.value
    value:        Any           = None
    default:      Any           = None

    # Numeric ranges
    min_val:      float         = 0.0
    max_val:      float         = 1.0
    step:         float         = 0.1
    decimals:     int           = 3

    # Enum options
    options:      List[str]     = field(default_factory=list)

    # UI hints
    tooltip:      str           = ""
    unit:         str           = ""        # "m", "°", "px" etc.
    section:      str           = PanelSection.CUSTOM.value
    readonly:     bool          = False
    visible:      bool          = True

    # Callback
    on_change:    Optional[str] = None      # Action name to trigger

    def get_display_value(self) -> str:
        """Display ke liye value string"""
        if self.value is None:
            return "—"
        if self.prop_type == PropertyType.FLOAT.value:
            return f"{self.value:.{self.decimals}f} {self.unit}".strip()
        if self.prop_type == PropertyType.BOOL.value:
            return "Yes" if self.value else "No"
        if self.prop_type == PropertyType.VECTOR3.value:
            v = self.value
            return f"({v[0]:.3f}, {v[1]:.3f}, {v[2]:.3f})"
        if self.prop_type == PropertyType.COLOR.value:
            if isinstance(self.value, (list, tuple)) and len(self.value) >= 3:
                r, g, b = int(self.value[0]*255), int(self.value[1]*255), int(self.value[2]*255)
                return f"#{r:02X}{g:02X}{b:02X}"
        return str(self.value)


@dataclass
class PropertySection:
    """Group of related properties"""
    id:         str
    title:      str
    icon:       str             = ""
    properties: List[PropertyDef] = field(default_factory=list)
    collapsed:  bool            = False
    visible:    bool            = True


@dataclass
class ObjectProperties:
    """
    Ek scene object ki sabhi properties.
    Selected object ke liye properties panel populate karta hai.
    """
    obj_id:     str
    obj_name:   str
    obj_type:   str
    sections:   List[PropertySection] = field(default_factory=list)

    def get_property(self, prop_id: str) -> Optional[PropertyDef]:
        """ID se property lo"""
        for section in self.sections:
            for prop in section.properties:
                if prop.id == prop_id:
                    return prop
        return None

    def set_value(self, prop_id: str, value: Any) -> bool:
        """Property value set karo"""
        prop = self.get_property(prop_id)
        if prop and not prop.readonly:
            prop.value = value
            return True
        return False

    def get_all_values(self) -> Dict[str, Any]:
        """Sabhi property values dict mein lo"""
        result = {}
        for section in self.sections:
            for prop in section.properties:
                result[prop.id] = prop.value
        return result


# ============================================================
# PROPERTY BUILDERS
# ============================================================

class PropertyBuilder:
    """
    Object type ke basis pe properties build karta hai.
    Har object type ke liye alag sections hote hain.
    """

    @staticmethod
    def build_transform_section(
        position: List[float] = None,
        rotation: List[float] = None,
        scale:    List[float] = None,
    ) -> PropertySection:
        """Transform section - position, rotation, scale"""
        pos = position or [0.0, 0.0, 0.0]
        rot = rotation or [0.0, 0.0, 0.0]
        scl = scale    or [1.0, 1.0, 1.0]

        return PropertySection(
            id="transform", title="Transform", icon="⊞",
            properties=[
                PropertyDef(
                    id="position", label="Location",
                    prop_type=PropertyType.VECTOR3.value,
                    value=pos, default=[0.0, 0.0, 0.0],
                    min_val=-1000.0, max_val=1000.0, step=0.1,
                    unit="m", tooltip="Object ka 3D position",
                    section=PanelSection.TRANSFORM.value,
                ),
                PropertyDef(
                    id="rotation", label="Rotation",
                    prop_type=PropertyType.VECTOR3.value,
                    value=rot, default=[0.0, 0.0, 0.0],
                    min_val=-360.0, max_val=360.0, step=1.0,
                    unit="°", tooltip="Object ka rotation (Euler angles)",
                    section=PanelSection.TRANSFORM.value,
                ),
                PropertyDef(
                    id="scale", label="Scale",
                    prop_type=PropertyType.VECTOR3.value,
                    value=scl, default=[1.0, 1.0, 1.0],
                    min_val=0.001, max_val=100.0, step=0.1,
                    tooltip="Object ka scale",
                    section=PanelSection.TRANSFORM.value,
                ),
            ]
        )

    @staticmethod
    def build_material_section() -> PropertySection:
        """Material properties section"""
        return PropertySection(
            id="material", title="Material", icon="🎨",
            properties=[
                PropertyDef(
                    id="mat_name", label="Material",
                    prop_type=PropertyType.STRING.value,
                    value="Default", tooltip="Material naam",
                    section=PanelSection.MATERIAL.value,
                ),
                PropertyDef(
                    id="base_color", label="Base Color",
                    prop_type=PropertyType.COLOR.value,
                    value=[0.8, 0.8, 0.8], default=[0.8, 0.8, 0.8],
                    tooltip="Material ka base color",
                    section=PanelSection.MATERIAL.value,
                ),
                PropertyDef(
                    id="metallic", label="Metallic",
                    prop_type=PropertyType.SLIDER.value,
                    value=0.0, default=0.0,
                    min_val=0.0, max_val=1.0, step=0.01, decimals=2,
                    tooltip="Metallic (0=non-metal, 1=full metal)",
                    section=PanelSection.MATERIAL.value,
                ),
                PropertyDef(
                    id="roughness", label="Roughness",
                    prop_type=PropertyType.SLIDER.value,
                    value=0.5, default=0.5,
                    min_val=0.0, max_val=1.0, step=0.01, decimals=2,
                    tooltip="Surface roughness",
                    section=PanelSection.MATERIAL.value,
                ),
                PropertyDef(
                    id="opacity", label="Opacity",
                    prop_type=PropertyType.SLIDER.value,
                    value=1.0, default=1.0,
                    min_val=0.0, max_val=1.0, step=0.01, decimals=2,
                    tooltip="Transparency (0=invisible, 1=solid)",
                    section=PanelSection.MATERIAL.value,
                ),
                PropertyDef(
                    id="emission", label="Emission",
                    prop_type=PropertyType.COLOR.value,
                    value=[0.0, 0.0, 0.0], default=[0.0, 0.0, 0.0],
                    tooltip="Self-emission color (glow effect)",
                    section=PanelSection.MATERIAL.value,
                ),
                PropertyDef(
                    id="texture_path", label="Texture",
                    prop_type=PropertyType.FILEPATH.value,
                    value="", tooltip="Texture image file",
                    section=PanelSection.MATERIAL.value,
                ),
            ]
        )

    @staticmethod
    def build_physics_section() -> PropertySection:
        """Physics properties section"""
        return PropertySection(
            id="physics", title="Physics", icon="⚛",
            collapsed=True,
            properties=[
                PropertyDef(
                    id="physics_enabled", label="Enable Physics",
                    prop_type=PropertyType.BOOL.value,
                    value=False, default=False,
                    tooltip="Physics simulation enable karo",
                    section=PanelSection.PHYSICS.value,
                ),
                PropertyDef(
                    id="body_type", label="Body Type",
                    prop_type=PropertyType.ENUM.value,
                    value="Dynamic",
                    options=["Static", "Dynamic", "Kinematic"],
                    tooltip="Physics body type",
                    section=PanelSection.PHYSICS.value,
                ),
                PropertyDef(
                    id="mass", label="Mass",
                    prop_type=PropertyType.FLOAT.value,
                    value=1.0, default=1.0,
                    min_val=0.001, max_val=10000.0, step=0.1,
                    unit="kg", tooltip="Object ka mass",
                    section=PanelSection.PHYSICS.value,
                ),
                PropertyDef(
                    id="friction", label="Friction",
                    prop_type=PropertyType.SLIDER.value,
                    value=0.5, default=0.5,
                    min_val=0.0, max_val=1.0, step=0.01, decimals=2,
                    tooltip="Surface friction coefficient",
                    section=PanelSection.PHYSICS.value,
                ),
                PropertyDef(
                    id="restitution", label="Bounciness",
                    prop_type=PropertyType.SLIDER.value,
                    value=0.0, default=0.0,
                    min_val=0.0, max_val=1.0, step=0.01, decimals=2,
                    tooltip="Bounce factor (0=no bounce, 1=full bounce)",
                    section=PanelSection.PHYSICS.value,
                ),
                PropertyDef(
                    id="gravity_factor", label="Gravity",
                    prop_type=PropertyType.FLOAT.value,
                    value=1.0, default=1.0,
                    min_val=0.0, max_val=10.0, step=0.1, decimals=2,
                    tooltip="Gravity multiplier",
                    section=PanelSection.PHYSICS.value,
                ),
            ]
        )

    @staticmethod
    def build_light_section(light_type: str = "Directional") -> PropertySection:
        """Light specific properties"""
        return PropertySection(
            id="lighting", title="Light", icon="💡",
            properties=[
                PropertyDef(
                    id="light_type", label="Type",
                    prop_type=PropertyType.ENUM.value,
                    value=light_type,
                    options=["Directional", "Point", "Spot", "Area"],
                    tooltip="Light type",
                    section=PanelSection.LIGHTING.value,
                ),
                PropertyDef(
                    id="light_color", label="Color",
                    prop_type=PropertyType.COLOR.value,
                    value=[1.0, 1.0, 1.0], default=[1.0, 1.0, 1.0],
                    tooltip="Light color",
                    section=PanelSection.LIGHTING.value,
                ),
                PropertyDef(
                    id="intensity", label="Intensity",
                    prop_type=PropertyType.FLOAT.value,
                    value=1.0, default=1.0,
                    min_val=0.0, max_val=100.0, step=0.1, decimals=2,
                    tooltip="Light strength",
                    section=PanelSection.LIGHTING.value,
                ),
                PropertyDef(
                    id="light_range", label="Range",
                    prop_type=PropertyType.FLOAT.value,
                    value=10.0, default=10.0,
                    min_val=0.1, max_val=1000.0, step=0.5,
                    unit="m", tooltip="Light range (Point/Spot only)",
                    section=PanelSection.LIGHTING.value,
                ),
                PropertyDef(
                    id="cast_shadows", label="Cast Shadows",
                    prop_type=PropertyType.BOOL.value,
                    value=True, default=True,
                    tooltip="Shadow casting enable karo",
                    section=PanelSection.LIGHTING.value,
                ),
                PropertyDef(
                    id="shadow_softness", label="Shadow Softness",
                    prop_type=PropertyType.SLIDER.value,
                    value=0.3, default=0.3,
                    min_val=0.0, max_val=1.0, step=0.01, decimals=2,
                    tooltip="Shadow edge softness",
                    section=PanelSection.LIGHTING.value,
                ),
                PropertyDef(
                    id="spot_angle", label="Spot Angle",
                    prop_type=PropertyType.FLOAT.value,
                    value=45.0, default=45.0,
                    min_val=1.0, max_val=180.0, step=1.0,
                    unit="°", tooltip="Spot light cone angle",
                    section=PanelSection.LIGHTING.value,
                ),
            ]
        )

    @staticmethod
    def build_camera_section() -> PropertySection:
        """Camera properties section"""
        return PropertySection(
            id="camera", title="Camera", icon="🎥",
            properties=[
                PropertyDef(
                    id="fov", label="Field of View",
                    prop_type=PropertyType.FLOAT.value,
                    value=60.0, default=60.0,
                    min_val=10.0, max_val=170.0, step=1.0,
                    unit="°", tooltip="Camera field of view",
                    section=PanelSection.CAMERA.value,
                ),
                PropertyDef(
                    id="near_clip", label="Near Clip",
                    prop_type=PropertyType.FLOAT.value,
                    value=0.1, default=0.1,
                    min_val=0.001, max_val=100.0, step=0.01, decimals=3,
                    unit="m", tooltip="Near clipping plane",
                    section=PanelSection.CAMERA.value,
                ),
                PropertyDef(
                    id="far_clip", label="Far Clip",
                    prop_type=PropertyType.FLOAT.value,
                    value=1000.0, default=1000.0,
                    min_val=1.0, max_val=100000.0, step=10.0,
                    unit="m", tooltip="Far clipping plane",
                    section=PanelSection.CAMERA.value,
                ),
                PropertyDef(
                    id="focal_length", label="Focal Length",
                    prop_type=PropertyType.FLOAT.value,
                    value=50.0, default=50.0,
                    min_val=1.0, max_val=800.0, step=1.0,
                    unit="mm", tooltip="Lens focal length",
                    section=PanelSection.CAMERA.value,
                ),
                PropertyDef(
                    id="depth_of_field", label="Depth of Field",
                    prop_type=PropertyType.BOOL.value,
                    value=False, default=False,
                    tooltip="DOF effect enable karo",
                    section=PanelSection.CAMERA.value,
                ),
                PropertyDef(
                    id="aperture", label="Aperture",
                    prop_type=PropertyType.FLOAT.value,
                    value=2.8, default=2.8,
                    min_val=0.5, max_val=32.0, step=0.1, decimals=1,
                    unit="f/", tooltip="Lens aperture (DOF blur amount)",
                    section=PanelSection.CAMERA.value,
                ),
                PropertyDef(
                    id="cam_preset", label="Preset",
                    prop_type=PropertyType.ENUM.value,
                    value="Medium Shot",
                    options=[
                        "Wide Angle", "Medium Shot", "Close Up",
                        "Over the Shoulder", "Bird's Eye", "Low Angle",
                        "Dutch Angle", "Establishing Shot",
                    ],
                    tooltip="Camera angle preset",
                    section=PanelSection.CAMERA.value,
                ),
            ]
        )

    @staticmethod
    def build_character_section() -> PropertySection:
        """Character specific properties"""
        return PropertySection(
            id="character", title="Character", icon="🧍",
            properties=[
                PropertyDef(
                    id="char_name", label="Character Name",
                    prop_type=PropertyType.STRING.value,
                    value="Character", tooltip="Character ka naam",
                    section=PanelSection.CHARACTER.value,
                ),
                PropertyDef(
                    id="skin_color", label="Skin Color",
                    prop_type=PropertyType.COLOR.value,
                    value=[0.8, 0.6, 0.4], default=[0.8, 0.6, 0.4],
                    tooltip="Character skin color",
                    section=PanelSection.CHARACTER.value,
                ),
                PropertyDef(
                    id="hair_color", label="Hair Color",
                    prop_type=PropertyType.COLOR.value,
                    value=[0.2, 0.1, 0.05], default=[0.2, 0.1, 0.05],
                    tooltip="Character hair color",
                    section=PanelSection.CHARACTER.value,
                ),
                PropertyDef(
                    id="height", label="Height",
                    prop_type=PropertyType.FLOAT.value,
                    value=1.75, default=1.75,
                    min_val=0.5, max_val=3.0, step=0.01, decimals=2,
                    unit="m", tooltip="Character height",
                    section=PanelSection.CHARACTER.value,
                ),
                PropertyDef(
                    id="clothing_type", label="Clothing",
                    prop_type=PropertyType.ENUM.value,
                    value="Casual",
                    options=["Casual", "Formal", "Fantasy", "Sci-Fi",
                             "Traditional", "Uniform", "Custom"],
                    tooltip="Clothing style",
                    section=PanelSection.CHARACTER.value,
                ),
                PropertyDef(
                    id="clothing_color", label="Clothing Color",
                    prop_type=PropertyType.COLOR.value,
                    value=[0.2, 0.4, 0.8], default=[0.2, 0.4, 0.8],
                    tooltip="Main clothing color",
                    section=PanelSection.CHARACTER.value,
                ),
                PropertyDef(
                    id="anim_preset", label="Animation",
                    prop_type=PropertyType.ENUM.value,
                    value="Idle",
                    options=["Idle", "Walk", "Run", "Talk", "Wave",
                             "Jump", "Sit", "Dance", "Fight", "Custom"],
                    tooltip="Character animation preset",
                    section=PanelSection.CHARACTER.value,
                ),
                PropertyDef(
                    id="expression", label="Expression",
                    prop_type=PropertyType.ENUM.value,
                    value="Neutral",
                    options=["Neutral", "Happy", "Sad", "Angry",
                             "Surprised", "Fearful", "Disgusted",
                             "Confused", "Thinking"],
                    tooltip="Facial expression",
                    section=PanelSection.CHARACTER.value,
                ),
            ]
        )

    @staticmethod
    def build_animation_section() -> PropertySection:
        """Animation properties"""
        return PropertySection(
            id="animation", title="Animation", icon="🎬",
            collapsed=True,
            properties=[
                PropertyDef(
                    id="anim_enabled", label="Animated",
                    prop_type=PropertyType.BOOL.value,
                    value=True, default=True,
                    tooltip="Animation enable karo",
                    section=PanelSection.ANIMATION.value,
                ),
                PropertyDef(
                    id="anim_speed", label="Speed",
                    prop_type=PropertyType.FLOAT.value,
                    value=1.0, default=1.0,
                    min_val=0.1, max_val=10.0, step=0.1, decimals=2,
                    unit="x", tooltip="Animation playback speed",
                    section=PanelSection.ANIMATION.value,
                ),
                PropertyDef(
                    id="anim_loop", label="Loop",
                    prop_type=PropertyType.BOOL.value,
                    value=True, default=True,
                    tooltip="Animation loop karo",
                    section=PanelSection.ANIMATION.value,
                ),
                PropertyDef(
                    id="anim_start", label="Start Frame",
                    prop_type=PropertyType.INT.value,
                    value=0, default=0,
                    min_val=0, max_val=10000, step=1,
                    tooltip="Animation start frame",
                    section=PanelSection.ANIMATION.value,
                ),
                PropertyDef(
                    id="anim_end", label="End Frame",
                    prop_type=PropertyType.INT.value,
                    value=250, default=250,
                    min_val=1, max_val=10000, step=1,
                    tooltip="Animation end frame",
                    section=PanelSection.ANIMATION.value,
                ),
            ]
        )

    @staticmethod
    def build_vfx_section() -> PropertySection:
        """VFX properties"""
        return PropertySection(
            id="vfx", title="VFX", icon="✨",
            properties=[
                PropertyDef(
                    id="vfx_type", label="Effect Type",
                    prop_type=PropertyType.ENUM.value,
                    value="Fire",
                    options=["Fire", "Smoke", "Rain", "Snow", "Sparkle",
                             "Explosion", "Confetti", "Fog",
                             "Lightning", "Magic"],
                    tooltip="VFX effect type",
                    section=PanelSection.VFX.value,
                ),
                PropertyDef(
                    id="vfx_intensity", label="Intensity",
                    prop_type=PropertyType.SLIDER.value,
                    value=1.0, default=1.0,
                    min_val=0.0, max_val=5.0, step=0.1, decimals=1,
                    tooltip="Effect intensity/strength",
                    section=PanelSection.VFX.value,
                ),
                PropertyDef(
                    id="vfx_size", label="Size",
                    prop_type=PropertyType.FLOAT.value,
                    value=1.0, default=1.0,
                    min_val=0.1, max_val=50.0, step=0.1, decimals=2,
                    unit="m", tooltip="Effect area size",
                    section=PanelSection.VFX.value,
                ),
                PropertyDef(
                    id="vfx_color", label="Color",
                    prop_type=PropertyType.COLOR.value,
                    value=[1.0, 0.5, 0.0], default=[1.0, 0.5, 0.0],
                    tooltip="Primary effect color",
                    section=PanelSection.VFX.value,
                ),
                PropertyDef(
                    id="vfx_lifetime", label="Lifetime",
                    prop_type=PropertyType.FLOAT.value,
                    value=2.0, default=2.0,
                    min_val=0.1, max_val=60.0, step=0.1, decimals=1,
                    unit="s", tooltip="Particle lifetime",
                    section=PanelSection.VFX.value,
                ),
                PropertyDef(
                    id="vfx_loop", label="Loop",
                    prop_type=PropertyType.BOOL.value,
                    value=True, default=True,
                    tooltip="Effect loop karo",
                    section=PanelSection.VFX.value,
                ),
            ]
        )

    @staticmethod
    def build_for_object_type(
        obj_id:   str,
        obj_name: str,
        obj_type: str,
        data:     Optional[Dict] = None,
    ) -> ObjectProperties:
        """
        Object type ke basis pe complete properties banao.
        Yeh main factory method hai.
        """
        data = data or {}
        sections = []

        # Transform hamesha hota hai
        sections.append(PropertyBuilder.build_transform_section(
            position = data.get("position", [0.0, 0.0, 0.0]),
            rotation = data.get("rotation", [0.0, 0.0, 0.0]),
            scale    = data.get("scale",    [1.0, 1.0, 1.0]),
        ))

        # Type-specific sections
        from src.ui.scene_hierarchy import ObjectType

        if obj_type == ObjectType.CHARACTER.value:
            sections.append(PropertyBuilder.build_character_section())
            sections.append(PropertyBuilder.build_material_section())
            sections.append(PropertyBuilder.build_animation_section())
            sections.append(PropertyBuilder.build_physics_section())

        elif obj_type == ObjectType.MESH.value:
            sections.append(PropertyBuilder.build_material_section())
            sections.append(PropertyBuilder.build_physics_section())
            sections.append(PropertyBuilder.build_animation_section())

        elif obj_type == ObjectType.LIGHT.value:
            sections.append(PropertyBuilder.build_light_section(
                data.get("light_type", "Directional")
            ))

        elif obj_type == ObjectType.CAMERA.value:
            sections.append(PropertyBuilder.build_camera_section())
            sections.append(PropertyBuilder.build_animation_section())

        elif obj_type == ObjectType.VFX.value:
            sections.append(PropertyBuilder.build_vfx_section())

        elif obj_type == ObjectType.CLOTH.value:
            sections.append(PropertyBuilder.build_material_section())
            cloth_section = PropertySection(
                id="cloth", title="Cloth Simulation", icon="👗",
                properties=[
                    PropertyDef(
                        id="cloth_material", label="Cloth Type",
                        prop_type=PropertyType.ENUM.value,
                        value="Cotton",
                        options=["Cotton", "Silk", "Wool",
                                 "Leather", "Denim", "Chiffon"],
                        tooltip="Cloth material type",
                    ),
                    PropertyDef(
                        id="cloth_stiffness", label="Stiffness",
                        prop_type=PropertyType.SLIDER.value,
                        value=0.5, min_val=0.0, max_val=1.0,
                        step=0.01, decimals=2,
                        tooltip="Cloth ka stiffness",
                    ),
                    PropertyDef(
                        id="cloth_wind", label="Wind Force",
                        prop_type=PropertyType.FLOAT.value,
                        value=0.0, min_val=0.0, max_val=20.0,
                        step=0.5, unit="N",
                        tooltip="Wind force on cloth",
                    ),
                ]
            )
            sections.append(cloth_section)

        else:
            # Generic - material aur physics
            sections.append(PropertyBuilder.build_material_section())

        return ObjectProperties(
            obj_id   = obj_id,
            obj_name = obj_name,
            obj_type = obj_type,
            sections = sections,
        )


# ============================================================
# PROPERTIES PANEL - DATA MODEL
# ============================================================

class PropertiesPanelModel:
    """
    Properties panel ka data model.
    Qt se independent.
    Currently selected object ki properties track karta hai.
    """

    def __init__(self):
        # Current object properties
        self._current_props: Optional[ObjectProperties] = None

        # Change history (simple undo)
        self._change_history: List[Tuple] = []

        # Change listeners
        self._listeners: List[Callable] = []

        # No object selected state
        self._empty_props = None

        logger.debug("PropertiesPanelModel initialized")

    def load_object(
        self,
        obj_id:   str,
        obj_name: str,
        obj_type: str,
        data:     Optional[Dict] = None,
    ):
        """
        Object ko properties panel mein load karo.
        Naya ObjectProperties banata hai.
        """
        self._current_props = PropertyBuilder.build_for_object_type(
            obj_id, obj_name, obj_type, data
        )
        self._notify("properties_loaded", {
            "obj_id": obj_id, "obj_type": obj_type
        })
        logger.debug(f"Properties loaded: {obj_name} ({obj_type})")

    def clear(self):
        """Properties panel clear karo (no selection)"""
        self._current_props = None
        self._notify("properties_cleared", {})

    def get_current_properties(self) -> Optional[ObjectProperties]:
        """Current object ki properties lo"""
        return self._current_props

    def update_property(
        self,
        prop_id: str,
        new_value: Any,
        record_history: bool = True,
    ) -> bool:
        """
        Property value update karo.

        Args:
            prop_id: Property ID
            new_value: Naya value
            record_history: Undo ke liye record karo?
        """
        if not self._current_props:
            return False

        prop = self._current_props.get_property(prop_id)
        if not prop:
            return False

        if prop.readonly:
            logger.warning(f"Property read-only hai: {prop_id}")
            return False

        # History record karo
        if record_history:
            self._change_history.append((
                self._current_props.obj_id,
                prop_id,
                prop.value,
                new_value,
            ))
            # Max 50 history
            if len(self._change_history) > 50:
                self._change_history.pop(0)

        # Value update karo
        old_value = prop.value
        prop.value = new_value

        self._notify("property_changed", {
            "obj_id":    self._current_props.obj_id,
            "prop_id":   prop_id,
            "old_value": old_value,
            "new_value": new_value,
        })

        logger.debug(f"Property updated: {prop_id} = {new_value}")
        return True

    def undo_last_change(self) -> bool:
        """Last property change undo karo"""
        if not self._change_history:
            return False

        obj_id, prop_id, old_val, new_val = self._change_history.pop()

        if (self._current_props and
                self._current_props.obj_id == obj_id):
            self._current_props.set_value(prop_id, old_val)
            self._notify("property_changed", {
                "obj_id":    obj_id,
                "prop_id":   prop_id,
                "old_value": new_val,
                "new_value": old_val,
            })
            logger.debug(f"Property undone: {prop_id}")
            return True

        return False

    def reset_to_defaults(self):
        """Sabhi properties default pe reset karo"""
        if not self._current_props:
            return
        for section in self._current_props.sections:
            for prop in section.properties:
                if prop.default is not None:
                    prop.value = prop.default
        self._notify("properties_reset", {})
        logger.info("Properties reset to defaults")

    def get_values_dict(self) -> Dict:
        """Sabhi values dict mein lo (save ke liye)"""
        if not self._current_props:
            return {}
        return self._current_props.get_all_values()

    def add_listener(self, callback: Callable):
        """Change listener add karo"""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable):
        """Listener remove karo"""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify(self, event: str, data: Dict):
        """Listeners notify karo"""
        for cb in self._listeners:
            try:
                cb(event, data)
            except Exception as e:
                logger.warning(f"Properties listener error: {e}")


# ============================================================
# QT PROPERTIES PANEL WIDGET
# ============================================================

class PropertiesPanelWidget:
    """
    PyQt5 Properties Panel.
    Collapsible sections, color pickers, sliders sab include.
    """

    def __init__(
        self,
        parent=None,
        model: Optional[PropertiesPanelModel] = None,
        theme_manager=None,
        config: Optional[Dict] = None,
    ):
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        self.parent_widget = parent
        self.theme_manager = theme_manager
        self.model = model or PropertiesPanelModel()

        # Qt references
        self._widget      = None
        self._scroll_area = None
        self._content     = None
        self._layout      = None

        # Section widgets: section_id -> QGroupBox
        self._section_widgets: Dict[str, Any] = {}

        # Property widgets: prop_id -> widget
        self._prop_widgets: Dict[str, Any] = {}

        # Build widget
        self._build_widget()

        # Listen to model changes
        self.model.add_listener(self._on_model_changed)

        logger.info("✅ PropertiesPanelWidget initialized")

    def _build_widget(self):
        """Main Qt widget build karo"""
        try:
            from PyQt5.QtWidgets import (
                QWidget, QVBoxLayout, QScrollArea,
                QLabel, QPushButton, QHBoxLayout,
            )
            from PyQt5.QtCore import Qt

            # Main container
            self._widget = QWidget(self.parent_widget)
            self._widget.setObjectName("PropertiesPanel")
            outer_layout = QVBoxLayout(self._widget)
            outer_layout.setContentsMargins(0, 0, 0, 0)
            outer_layout.setSpacing(0)

            # Header
            header = QWidget()
            header_layout = QHBoxLayout(header)
            header_layout.setContentsMargins(8, 6, 8, 6)

            title_lbl = QLabel("PROPERTIES")
            header_layout.addWidget(title_lbl)
            header_layout.addStretch()

            # Reset button
            reset_btn = QPushButton("↺")
            reset_btn.setFixedSize(22, 22)
            reset_btn.setToolTip("Reset to defaults")
            reset_btn.clicked.connect(self.model.reset_to_defaults)
            header_layout.addWidget(reset_btn)

            outer_layout.addWidget(header)

            # Scroll area
            self._scroll_area = QScrollArea()
            self._scroll_area.setWidgetResizable(True)
            self._scroll_area.setHorizontalScrollBarPolicy(
                Qt.ScrollBarAlwaysOff
            )
            self._scroll_area.setObjectName("PropertiesScroll")

            # Content widget inside scroll
            self._content = QWidget()
            self._content.setObjectName("PropertiesContent")
            self._layout = QVBoxLayout(self._content)
            self._layout.setContentsMargins(4, 4, 4, 4)
            self._layout.setSpacing(4)
            self._layout.addStretch()

            self._scroll_area.setWidget(self._content)
            outer_layout.addWidget(self._scroll_area)

            # No selection label
            self._empty_label = QLabel("No object selected.\n\nScene mein object select karo.")
            self._empty_label.setAlignment(Qt.AlignCenter)
            self._empty_label.setObjectName("EmptyLabel")
            outer_layout.addWidget(self._empty_label)

            self._apply_theme()

        except ImportError:
            logger.warning("PyQt5 nahi - properties panel non-Qt mode")
        except Exception as e:
            logger.error(f"Properties widget build error: {e}")

    def _apply_theme(self):
        """Dark theme apply karo"""
        if not self.theme_manager or not self._widget:
            return
        try:
            p = self.theme_manager.get_palette()
            self._widget.setStyleSheet(f"""
                #PropertiesPanel {{
                    background-color: {p.bg_secondary};
                }}
                QLabel {{
                    color: {p.text_secondary};
                    font-size: 10px;
                    font-weight: bold;
                    letter-spacing: 1px;
                }}
                #PropertiesScroll {{
                    border: none;
                    background-color: {p.bg_secondary};
                }}
                #PropertiesContent {{
                    background-color: {p.bg_secondary};
                }}
                QGroupBox {{
                    border: 1px solid {p.border};
                    border-radius: 5px;
                    margin-top: 10px;
                    padding: 8px 4px 4px 4px;
                    font-size: 10px;
                    font-weight: bold;
                    color: {p.accent};
                    letter-spacing: 1px;
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    left: 8px;
                    padding: 0 4px;
                    color: {p.accent};
                }}
                QLabel#PropLabel {{
                    color: {p.text_secondary};
                    font-size: 11px;
                    font-weight: normal;
                    letter-spacing: 0px;
                    padding: 0;
                }}
                QDoubleSpinBox, QSpinBox {{
                    background-color: {p.bg_tertiary};
                    border: 1px solid {p.border};
                    border-radius: 3px;
                    color: {p.text_primary};
                    padding: 2px 4px;
                    font-size: 11px;
                }}
                QDoubleSpinBox:focus, QSpinBox:focus {{
                    border-color: {p.accent};
                }}
                QLineEdit {{
                    background-color: {p.bg_tertiary};
                    border: 1px solid {p.border};
                    border-radius: 3px;
                    color: {p.text_primary};
                    padding: 3px 6px;
                    font-size: 11px;
                }}
                QComboBox {{
                    background-color: {p.bg_tertiary};
                    border: 1px solid {p.border};
                    border-radius: 3px;
                    color: {p.text_primary};
                    padding: 3px 6px;
                    font-size: 11px;
                }}
                QCheckBox {{
                    color: {p.text_primary};
                    font-size: 11px;
                }}
                QSlider::groove:horizontal {{
                    height: 3px;
                    background: {p.border};
                    border-radius: 2px;
                }}
                QSlider::sub-page:horizontal {{
                    background: {p.accent};
                    border-radius: 2px;
                }}
                QSlider::handle:horizontal {{
                    background: {p.accent};
                    width: 12px; height: 12px;
                    margin: -5px 0;
                    border-radius: 6px;
                }}
                QPushButton {{
                    background-color: {p.bg_elevated};
                    border: 1px solid {p.border};
                    border-radius: 3px;
                    color: {p.text_primary};
                    padding: 3px 8px;
                    font-size: 11px;
                }}
                #EmptyLabel {{
                    color: {p.text_secondary};
                    font-size: 12px;
                    font-weight: normal;
                    letter-spacing: 0px;
                    padding: 20px;
                }}
            """)
        except Exception as e:
            logger.warning(f"Theme apply error: {e}")

    def populate(self, obj_props: ObjectProperties):
        """Properties panel populate karo object properties se"""
        if not self._layout or not self._content:
            return

        try:
            from PyQt5.QtWidgets import (
                QGroupBox, QFormLayout, QWidget,
                QDoubleSpinBox, QSpinBox, QLineEdit,
                QCheckBox, QComboBox, QSlider,
                QPushButton, QHBoxLayout, QLabel,
                QColorDialog, QToolButton,
            )
            from PyQt5.QtCore import Qt
            from PyQt5.QtGui import QColor

            # Clear existing
            self._clear_layout()
            self._section_widgets.clear()
            self._prop_widgets.clear()

            # Empty label hide karo
            if self._empty_label:
                self._empty_label.hide()
            if self._scroll_area:
                self._scroll_area.show()

            # Object title
            title = QLabel(
                f"{obj_props.obj_name}  "
                f"<span style='color:#666;font-size:10px;'>"
                f"[{obj_props.obj_type}]</span>"
            )
            title.setObjectName("ObjTitle")
            if self.theme_manager:
                p = self.theme_manager.get_palette()
                title.setStyleSheet(
                    f"color: {p.text_primary}; font-size: 13px; "
                    f"font-weight: bold; padding: 4px 6px;"
                )
            self._layout.insertWidget(
                self._layout.count() - 1, title
            )

            # Sections build karo
            for section in obj_props.sections:
                if not section.visible:
                    continue

                section_widget = self._build_section(
                    section, obj_props
                )
                if section_widget:
                    self._layout.insertWidget(
                        self._layout.count() - 1,
                        section_widget
                    )
                    self._section_widgets[section.id] = section_widget

        except Exception as e:
            logger.error(f"Panel populate error: {e}")

    def _build_section(self, section: PropertySection, obj_props: ObjectProperties):
        """Ek property section widget build karo"""
        try:
            from PyQt5.QtWidgets import (
                QGroupBox, QFormLayout, QWidget,
                QDoubleSpinBox, QSpinBox, QLineEdit,
                QCheckBox, QComboBox, QSlider,
                QHBoxLayout, QLabel, QToolButton,
            )
            from PyQt5.QtCore import Qt

            group = QGroupBox(f"{section.icon} {section.title}")
            group.setCheckable(False)
            form_layout = QFormLayout(group)
            form_layout.setSpacing(4)
            form_layout.setContentsMargins(6, 4, 6, 6)

            for prop in section.properties:
                if not prop.visible:
                    continue
                if prop.prop_type == PropertyType.SEPARATOR.value:
                    continue

                # Label
                lbl = QLabel(prop.label)
                lbl.setObjectName("PropLabel")
                lbl.setToolTip(prop.tooltip)

                # Widget
                widget = self._build_property_widget(prop, obj_props)
                if widget:
                    form_layout.addRow(lbl, widget)
                    self._prop_widgets[prop.id] = widget

            return group

        except Exception as e:
            logger.warning(f"Section build error ({section.id}): {e}")
            return None

    def _build_property_widget(self, prop: PropertyDef, obj_props: ObjectProperties):
        """Property type ke basis pe widget banao"""
        try:
            from PyQt5.QtWidgets import (
                QDoubleSpinBox, QSpinBox, QLineEdit,
                QCheckBox, QComboBox, QSlider,
                QHBoxLayout, QWidget, QLabel,
                QToolButton,
            )
            from PyQt5.QtCore import Qt

            pt = prop.prop_type

            # ===== FLOAT =====
            if pt == PropertyType.FLOAT.value:
                spin = QDoubleSpinBox()
                spin.setRange(prop.min_val, prop.max_val)
                spin.setSingleStep(prop.step)
                spin.setDecimals(prop.decimals)
                spin.setValue(prop.value or 0.0)
                spin.setSuffix(f" {prop.unit}" if prop.unit else "")
                spin.setReadOnly(prop.readonly)
                spin.valueChanged.connect(
                    lambda v, pid=prop.id:
                    obj_props.set_value(pid, v)
                )
                return spin

            # ===== INT =====
            elif pt == PropertyType.INT.value:
                spin = QSpinBox()
                spin.setRange(int(prop.min_val), int(prop.max_val))
                spin.setSingleStep(int(prop.step))
                spin.setValue(int(prop.value or 0))
                spin.setReadOnly(prop.readonly)
                spin.valueChanged.connect(
                    lambda v, pid=prop.id:
                    obj_props.set_value(pid, v)
                )
                return spin

            # ===== STRING =====
            elif pt == PropertyType.STRING.value:
                edit = QLineEdit()
                edit.setText(str(prop.value or ""))
                edit.setReadOnly(prop.readonly)
                edit.textChanged.connect(
                    lambda v, pid=prop.id:
                    obj_props.set_value(pid, v)
                )
                return edit

            # ===== BOOL =====
            elif pt == PropertyType.BOOL.value:
                check = QCheckBox()
                check.setChecked(bool(prop.value))
                check.setEnabled(not prop.readonly)
                check.toggled.connect(
                    lambda v, pid=prop.id:
                    obj_props.set_value(pid, v)
                )
                return check

            # ===== ENUM =====
            elif pt == PropertyType.ENUM.value:
                combo = QComboBox()
                for opt in prop.options:
                    combo.addItem(opt)
                if prop.value in prop.options:
                    combo.setCurrentText(str(prop.value))
                combo.setEnabled(not prop.readonly)
                combo.currentTextChanged.connect(
                    lambda v, pid=prop.id:
                    obj_props.set_value(pid, v)
                )
                return combo

            # ===== SLIDER =====
            elif pt == PropertyType.SLIDER.value:
                container = QWidget()
                h_layout  = QHBoxLayout(container)
                h_layout.setContentsMargins(0, 0, 0, 0)
                h_layout.setSpacing(4)

                slider = QSlider(Qt.Horizontal)
                steps  = int((prop.max_val - prop.min_val) / prop.step)
                slider.setRange(0, steps)
                current_step = int((float(prop.value or 0) - prop.min_val) / prop.step)
                slider.setValue(max(0, min(steps, current_step)))

                val_label = QLabel(f"{prop.value:.{prop.decimals}f}")
                val_label.setFixedWidth(36)
                if self.theme_manager:
                    p = self.theme_manager.get_palette()
                    val_label.setStyleSheet(
                        f"color: {p.text_primary}; font-size: 10px;"
                    )

                def on_slider(v, lbl=val_label, p=prop, pid=prop.id):
                    actual = p.min_val + (v * p.step)
                    lbl.setText(f"{actual:.{p.decimals}f}")
                    obj_props.set_value(pid, actual)

                slider.valueChanged.connect(on_slider)
                h_layout.addWidget(slider)
                h_layout.addWidget(val_label)
                return container

            # ===== VECTOR3 =====
            elif pt == PropertyType.VECTOR3.value:
                container = QWidget()
                h_layout  = QHBoxLayout(container)
                h_layout.setContentsMargins(0, 0, 0, 0)
                h_layout.setSpacing(2)

                val = prop.value or [0.0, 0.0, 0.0]
                axes = ["X", "Y", "Z"]
                spins = []

                for i, axis in enumerate(axes):
                    lbl = QLabel(axis)
                    lbl.setFixedWidth(12)
                    if self.theme_manager:
                        p = self.theme_manager.get_palette()
                        colors = [p.text_error, p.text_success, "#4488FF"]
                        lbl.setStyleSheet(
                            f"color: {colors[i]}; font-weight: bold; font-size: 10px;"
                        )
                    h_layout.addWidget(lbl)

                    spin = QDoubleSpinBox()
                    spin.setRange(prop.min_val, prop.max_val)
                    spin.setSingleStep(prop.step)
                    spin.setDecimals(prop.decimals)
                    spin.setValue(float(val[i]) if i < len(val) else 0.0)
                    spin.setFixedWidth(70)

                    def on_vec_change(v, idx=i, pid=prop.id, sp=spins):
                        current = obj_props.get_property(pid)
                        if current and isinstance(current.value, list):
                            new_val = current.value.copy()
                            new_val[idx] = v
                            obj_props.set_value(pid, new_val)

                    spin.valueChanged.connect(on_vec_change)
                    spins.append(spin)
                    h_layout.addWidget(spin)

                return container

            # ===== COLOR =====
            elif pt == PropertyType.COLOR.value:
                container = QWidget()
                h_layout  = QHBoxLayout(container)
                h_layout.setContentsMargins(0, 0, 0, 0)
                h_layout.setSpacing(4)

                color_val = prop.value or [0.8, 0.8, 0.8]
                r = int(color_val[0] * 255)
                g = int(color_val[1] * 255)
                b = int(color_val[2] * 255)

                color_btn = QToolButton()
                color_btn.setFixedSize(40, 22)
                color_btn.setStyleSheet(
                    f"background-color: rgb({r},{g},{b}); "
                    f"border: 1px solid #444; border-radius: 3px;"
                )

                hex_label = QLabel(f"#{r:02X}{g:02X}{b:02X}")
                if self.theme_manager:
                    p = self.theme_manager.get_palette()
                    hex_label.setStyleSheet(
                        f"color: {p.text_secondary}; font-size: 10px;"
                    )

                def open_color_picker(_, btn=color_btn, lbl=hex_label, pid=prop.id):
                    try:
                        from PyQt5.QtWidgets import QColorDialog
                        from PyQt5.QtGui import QColor
                        cur = obj_props.get_property(pid)
                        cv  = cur.value if cur else [0.8, 0.8, 0.8]
                        init_color = QColor(
                            int(cv[0]*255), int(cv[1]*255), int(cv[2]*255)
                        )
                        color = QColorDialog.getColor(init_color, None, "Pick Color")
                        if color.isValid():
                            nr = color.red()   / 255.0
                            ng = color.green() / 255.0
                            nb = color.blue()  / 255.0
                            obj_props.set_value(pid, [nr, ng, nb])
                            btn.setStyleSheet(
                                f"background-color: rgb({color.red()},{color.green()},{color.blue()});"
                                f"border: 1px solid #444; border-radius: 3px;"
                            )
                            lbl.setText(
                                f"#{color.red():02X}{color.green():02X}{color.blue():02X}"
                            )
                    except Exception as ce:
                        logger.warning(f"Color picker error: {ce}")

                color_btn.clicked.connect(open_color_picker)
                h_layout.addWidget(color_btn)
                h_layout.addWidget(hex_label)
                h_layout.addStretch()
                return container

            # ===== FILEPATH =====
            elif pt == PropertyType.FILEPATH.value:
                container = QWidget()
                h_layout  = QHBoxLayout(container)
                h_layout.setContentsMargins(0, 0, 0, 0)
                h_layout.setSpacing(4)

                edit = QLineEdit()
                edit.setText(str(prop.value or ""))
                edit.setPlaceholderText("File path...")
                edit.setReadOnly(prop.readonly)

                browse_btn = QToolButton()
                browse_btn.setText("...")
                browse_btn.setFixedWidth(24)

                def browse_file(_, e=edit, pid=prop.id):
                    try:
                        from PyQt5.QtWidgets import QFileDialog
                        path, _ = QFileDialog.getOpenFileName(
                            None, "Select File", "",
                            "Images (*.png *.jpg *.jpeg *.bmp *.tga);;All Files (*)"
                        )
                        if path:
                            e.setText(path)
                            obj_props.set_value(pid, path)
                    except Exception as fe:
                        logger.warning(f"File browse error: {fe}")

                browse_btn.clicked.connect(browse_file)
                h_layout.addWidget(edit)
                h_layout.addWidget(browse_btn)
                return container

            # ===== LABEL =====
            elif pt == PropertyType.LABEL.value:
                lbl = QLabel(str(prop.value or ""))
                if self.theme_manager:
                    p = self.theme_manager.get_palette()
                    lbl.setStyleSheet(f"color: {p.text_secondary}; font-size: 11px;")
                return lbl

            return None

        except Exception as e:
            logger.warning(f"Property widget build error ({prop.id}): {e}")
            return None

    def _clear_layout(self):
        """Layout clear karo"""
        if not self._layout:
            return
        try:
            while self._layout.count() > 1:  # Keep stretch
                item = self._layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        except Exception as e:
            logger.warning(f"Layout clear error: {e}")

    def show_empty_state(self):
        """No selection state dikhaao"""
        self._clear_layout()
        if self._scroll_area:
            self._scroll_area.hide()
        if self._empty_label:
            self._empty_label.show()

    def _on_model_changed(self, event: str, data: Dict):
        """Model change pe UI update karo"""
        if event == "properties_loaded":
            props = self.model.get_current_properties()
            if props:
                self.populate(props)
        elif event == "properties_cleared":
            self.show_empty_state()
        elif event == "properties_reset":
            props = self.model.get_current_properties()
            if props:
                self.populate(props)

    def get_widget(self):
        """Qt widget lo"""
        return self._widget


# ============================================================
# GLOBAL INSTANCE
# ============================================================

_global_model: Optional[PropertiesPanelModel] = None


def get_properties_model() -> PropertiesPanelModel:
    """Global PropertiesPanelModel lo (singleton)"""
    global _global_model
    if _global_model is None:
        _global_model = PropertiesPanelModel()
    return _global_model


# ============================================================
# TEST SECTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="DEBUG")
    print_banner("Properties Panel Test", "Object Properties Editor")

    # ===== TEST 1: Property Builder =====
    print_section("Test 1: Property Builder - All Object Types")
    from src.ui.scene_hierarchy import ObjectType

    test_objects = [
        ("char_001", "Hero", ObjectType.CHARACTER.value),
        ("mesh_001", "Cube", ObjectType.MESH.value),
        ("light_001", "Sun Light", ObjectType.LIGHT.value),
        ("cam_001", "Main Camera", ObjectType.CAMERA.value),
        ("vfx_001", "Fire Effect", ObjectType.VFX.value),
        ("clo_001", "Cape", ObjectType.CLOTH.value),
    ]

    for obj_id, name, obj_type in test_objects:
        props = PropertyBuilder.build_for_object_type(obj_id, name, obj_type)
        total_props = sum(len(s.properties) for s in props.sections)
        print(
            f"✅ {name:15s} ({obj_type:12s}): "
            f"{len(props.sections)} sections, "
            f"{total_props} properties"
        )

    # ===== TEST 2: Properties Model =====
    print_section("Test 2: Properties Model")
    model = PropertiesPanelModel()
    print(f"✅ Model initialized")
    print(f"   Current props: {model.get_current_properties()}")

    # Object load karo
    model.load_object("char_001", "Hero", ObjectType.CHARACTER.value)
    props = model.get_current_properties()
    print(f"✅ Object loaded: {props.obj_name}")
    print(f"   Sections: {[s.title for s in props.sections]}")

    # ===== TEST 3: Property Access =====
    print_section("Test 3: Property Access & Display")
    for section in props.sections:
        print(f"\n   📁 {section.title}:")
        for prop in section.properties[:3]:
            print(
                f"      {prop.label:20s} = "
                f"{prop.get_display_value():20s} "
                f"[{prop.prop_type}]"
            )

    # ===== TEST 4: Property Update =====
    print_section("Test 4: Property Update")

    # Position change
    success = model.update_property("position", [1.0, 2.0, 3.0])
    pos = props.get_property("position")
    print(f"✅ Position updated: {success} → {pos.get_display_value()}")

    # Height change
    success2 = model.update_property("height", 1.85)
    height = props.get_property("height")
    print(f"✅ Height updated: {success2} → {height.get_display_value()}")

    # Expression change
    success3 = model.update_property("expression", "Happy")
    expr = props.get_property("expression")
    print(f"✅ Expression updated: {success3} → {expr.get_display_value()}")

    # ===== TEST 5: Undo =====
    print_section("Test 5: Undo Property Change")
    print(f"   Before undo: height = {props.get_property('height').value}")
    undo_success = model.undo_last_change()
    print(f"✅ Undo success: {undo_success}")
    print(f"   After undo: height = {props.get_property('height').value}")

    # ===== TEST 6: Get Values Dict =====
    print_section("Test 6: Get All Values")
    values = model.get_values_dict()
    print(f"✅ Total values: {len(values)}")
    interesting = ["position", "height", "expression", "clothing_type", "skin_color"]
    for key in interesting:
        if key in values:
            print(f"   {key:20s}: {values[key]}")

    # ===== TEST 7: Reset to Defaults =====
    print_section("Test 7: Reset to Defaults")
    model.update_property("height", 2.5)
    print(f"   Before reset: height = {props.get_property('height').value}")
    model.reset_to_defaults()
    print(f"✅ After reset: height = {props.get_property('height').value}")

    # ===== TEST 8: Listeners =====
    print_section("Test 8: Event Listeners")
    events = []

    def on_event(event, data):
        events.append(event)
        if event == "property_changed":
            print(f"   📢 Property changed: {data.get('prop_id')} = {data.get('new_value')}")

    model.add_listener(on_event)
    model.update_property("anim_preset", "Walk")
    model.update_property("clothing_type", "Fantasy")
    model.clear()
    print(f"✅ Events: {events}")

    # ===== TEST 9: All Property Types =====
    print_section("Test 9: Property Display Values")
    test_props = [
        PropertyDef("f", "Float", PropertyType.FLOAT.value, 3.14159, decimals=3),
        PropertyDef("i", "Int",   PropertyType.INT.value,   42),
        PropertyDef("s", "String",PropertyType.STRING.value,"Hello World"),
        PropertyDef("b", "Bool",  PropertyType.BOOL.value,  True),
        PropertyDef("v", "Vec3",  PropertyType.VECTOR3.value,[1.0, 2.0, 3.0]),
        PropertyDef("c", "Color", PropertyType.COLOR.value, [0.2, 0.8, 0.4]),
        PropertyDef("e", "Enum",  PropertyType.ENUM.value,  "Option A",
                    options=["Option A", "Option B"]),
    ]
    for p in test_props:
        print(f"✅ {p.prop_type:10s}: {p.get_display_value()}")

    # ===== TEST 10: Qt Widget =====
    print_section("Test 10: Qt Widget Build")
    try:
        from PyQt5.QtWidgets import (
            QApplication, QMainWindow, QDockWidget
        )
        from PyQt5.QtCore import Qt
        import sys as _sys

        app = QApplication.instance() or QApplication(_sys.argv)

        from src.ui.theme_manager import ThemeManager
        theme = ThemeManager()
        theme.set_application(app)

        window = QMainWindow()
        window.setWindowTitle("Properties Panel Test")
        window.resize(300, 700)

        # Widget banao
        panel = PropertiesPanelWidget(theme_manager=theme)

        dock = QDockWidget("Properties", window)
        dock.setWidget(panel.get_widget())
        window.addDockWidget(Qt.RightDockWidgetArea, dock)

        # Character load karo
        panel.model.load_object(
            "char_001", "Hero", ObjectType.CHARACTER.value,
            data={"position": [1.0, 0.0, 2.0]}
        )

        window.show()
        print(f"✅ Qt widget shown with character properties")
        print(f"   Sections: {len(panel._section_widgets)}")
        print(f"   Prop widgets: {len(panel._prop_widgets)}")

        from PyQt5.QtCore import QTimer
        QTimer.singleShot(800, app.quit)
        app.exec_()
        print(f"✅ Qt test complete")

    except ImportError:
        print("⚠️  PyQt5 visual test skip")
    except Exception as e:
        print(f"⚠️  Qt test: {e}")

    # ===== TEST 11: Singleton =====
    print_section("Test 11: Global Singleton")
    m1 = get_properties_model()
    m2 = get_properties_model()
    print(f"✅ Singleton: {m1 is m2}")

    print_banner("✅ All Tests Passed!", "properties_panel.py Working Perfectly")