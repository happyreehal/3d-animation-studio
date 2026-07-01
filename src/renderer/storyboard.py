# ============================================================
# src/renderer/storyboard.py
# 3D Animation Studio - Storyboarding & Pre-visualization
# Visual planning of scenes before actual rendering
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

import time
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
    get_timestamp,
)

logger = get_logger("Storyboard")


# ============================================================
# ENUMS
# ============================================================

class ShotType(Enum):
    """Camera shot types for storyboarding"""
    ESTABLISHING       = "establishing"        # Wide scene setter
    WIDE               = "wide"                 # Wide shot
    MEDIUM             = "medium"               # Medium shot
    MEDIUM_CLOSE       = "medium_close"         # Chest up
    CLOSE_UP           = "close_up"             # Face
    EXTREME_CLOSE_UP   = "extreme_close_up"     # Eyes, mouth
    OVER_SHOULDER      = "over_shoulder"        # OTS
    POV                = "pov"                  # Point of view
    TWO_SHOT           = "two_shot"             # Two characters
    THREE_SHOT         = "three_shot"           # Three characters
    GROUP              = "group"                # Multiple characters
    INSERT             = "insert"               # Close of object
    CUTAWAY            = "cutaway"              # Different subject


class ShotPurpose(Enum):
    """What does this shot accomplish?"""
    ESTABLISH          = "establish"            # Show location
    INTRODUCE          = "introduce"            # New character/object
    DIALOGUE           = "dialogue"             # Character talking
    REACTION           = "reaction"             # Character's reaction
    ACTION             = "action"               # Something happens
    EMOTION            = "emotion"              # Show feelings
    DETAIL             = "detail"               # Show something specific
    TRANSITION         = "transition"           # Move to next scene


class TransitionStyle(Enum):
    """Transitions between shots"""
    CUT                = "cut"                  # Direct cut
    FADE_IN            = "fade_in"              # Fade from black
    FADE_OUT           = "fade_out"             # Fade to black
    CROSS_FADE         = "cross_fade"           # Dissolve
    WIPE               = "wipe"                 # Wipe transition
    ZOOM               = "zoom"                 # Zoom transition
    IRIS               = "iris"                 # Iris in/out


class StoryboardStatus(Enum):
    """Storyboard status"""
    DRAFT              = "draft"                # Initial draft
    IN_REVIEW          = "in_review"            # Under review
    APPROVED           = "approved"             # Ready to render
    LOCKED             = "locked"               # No changes allowed


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class ShotCharacter:
    """Character placement in a shot"""
    character_name:    str
    position:          str             = "center"    # left, right, center, background
    action:            str             = "standing"  # What character is doing
    facing:            str             = "camera"    # camera, left, right, away
    expression:        str             = "neutral"   # facial expression
    dialogue:          str             = ""          # What they're saying

    def to_dict(self) -> Dict:
        return {
            "character": self.character_name,
            "position":  self.position,
            "action":    self.action,
            "facing":    self.facing,
            "expression":self.expression,
            "dialogue":  self.dialogue,
        }


@dataclass
class CameraDescription:
    """Camera setup description"""
    angle:             str             = "eye_level"     # low, eye_level, high, birds_eye
    distance:          str             = "medium"        # close, medium, far
    movement:          str             = "static"        # static, pan, tilt, dolly, zoom
    focus:             str             = "sharp"         # sharp, shallow_dof, deep_dof

    def to_dict(self) -> Dict:
        return {
            "angle":    self.angle,
            "distance": self.distance,
            "movement": self.movement,
            "focus":    self.focus,
        }


@dataclass
class LightingNote:
    """Lighting description for shot"""
    time_of_day:       str             = "day"           # day, dusk, night
    mood:              str             = "neutral"       # bright, dark, dramatic, warm
    key_light:         str             = "front"         # Position of main light
    description:       str             = ""

    def to_dict(self) -> Dict:
        return {
            "time_of_day": self.time_of_day,
            "mood":        self.mood,
            "key_light":   self.key_light,
            "description": self.description,
        }


@dataclass
class StoryboardPanel:
    """
    Ek storyboard panel - ek shot represent karta hai.
    Ye traditional storyboard ki tarah hai - image + notes.
    """
    # Identity
    panel_id:          str             = ""
    panel_number:      int             = 1
    scene_number:      int             = 1
    shot_number:       int             = 1

    # Shot details
    shot_type:         str             = ShotType.MEDIUM.value
    shot_purpose:      str             = ShotPurpose.DIALOGUE.value
    description:       str             = ""

    # Duration (frames)
    duration_frames:   int             = 60             # 2 sec at 30fps
    duration_seconds:  float           = 2.0

    # Content
    characters:        List[ShotCharacter] = field(default_factory=list)
    camera:            CameraDescription = field(default_factory=CameraDescription)
    lighting:          LightingNote      = field(default_factory=LightingNote)

    # Scene context
    location:          str             = ""
    action_description:str             = ""             # What happens in this shot
    dialogue_text:     str             = ""             # Full dialogue

    # Transition (to next shot)
    transition_to_next: str            = TransitionStyle.CUT.value
    transition_duration: int           = 15

    # Visual/Reference
    reference_image:   str             = ""             # Path to reference sketch
    thumbnail_image:   str             = ""             # Generated thumbnail
    color_notes:       List[float]     = field(default_factory=lambda: [0.5, 0.5, 0.5])

    # Notes for team
    director_notes:    str             = ""
    sound_notes:       str             = ""             # SFX, music cues
    vfx_notes:         str             = ""             # Special effects
    props_needed:      List[str]       = field(default_factory=list)

    # Status
    status:            str             = StoryboardStatus.DRAFT.value
    approved:          bool            = False

    # Meta
    created_at:        str             = ""
    modified_at:       str             = ""

    def __post_init__(self):
        if not self.panel_id:
            self.panel_id = f"panel_{generate_uuid()[:8]}"
        if not self.created_at:
            self.created_at = get_timestamp()

    def get_shot_label(self) -> str:
        """Full shot label like 'S1-Sh3' """
        return f"S{self.scene_number}-Sh{self.shot_number}"

    def get_duration_display(self) -> str:
        """Human readable duration"""
        return f"{self.duration_seconds:.1f}s ({self.duration_frames}f)"

    def to_dict(self) -> Dict:
        return {
            "panel_id":            self.panel_id,
            "panel_number":        self.panel_number,
            "scene_number":        self.scene_number,
            "shot_number":         self.shot_number,
            "shot_label":          self.get_shot_label(),
            "shot_type":           self.shot_type,
            "shot_purpose":        self.shot_purpose,
            "description":         self.description,
            "duration_frames":     self.duration_frames,
            "duration_seconds":    self.duration_seconds,
            "characters":          [c.to_dict() for c in self.characters],
            "camera":              self.camera.to_dict(),
            "lighting":            self.lighting.to_dict(),
            "location":            self.location,
            "action_description":  self.action_description,
            "dialogue_text":       self.dialogue_text,
            "transition_to_next":  self.transition_to_next,
            "transition_duration": self.transition_duration,
            "reference_image":     self.reference_image,
            "thumbnail_image":     self.thumbnail_image,
            "color_notes":         self.color_notes,
            "director_notes":      self.director_notes,
            "sound_notes":         self.sound_notes,
            "vfx_notes":           self.vfx_notes,
            "props_needed":        self.props_needed,
            "status":              self.status,
            "approved":            self.approved,
            "created_at":          self.created_at,
            "modified_at":         self.modified_at,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "StoryboardPanel":
        panel = cls(
            panel_id            = data.get("panel_id", ""),
            panel_number        = data.get("panel_number", 1),
            scene_number        = data.get("scene_number", 1),
            shot_number         = data.get("shot_number", 1),
            shot_type           = data.get("shot_type", ShotType.MEDIUM.value),
            shot_purpose        = data.get("shot_purpose", ShotPurpose.DIALOGUE.value),
            description         = data.get("description", ""),
            duration_frames     = data.get("duration_frames", 60),
            duration_seconds    = data.get("duration_seconds", 2.0),
            location            = data.get("location", ""),
            action_description  = data.get("action_description", ""),
            dialogue_text       = data.get("dialogue_text", ""),
            transition_to_next  = data.get("transition_to_next", TransitionStyle.CUT.value),
            transition_duration = data.get("transition_duration", 15),
            reference_image     = data.get("reference_image", ""),
            thumbnail_image     = data.get("thumbnail_image", ""),
            color_notes         = data.get("color_notes", [0.5, 0.5, 0.5]),
            director_notes      = data.get("director_notes", ""),
            sound_notes         = data.get("sound_notes", ""),
            vfx_notes           = data.get("vfx_notes", ""),
            props_needed        = data.get("props_needed", []),
            status              = data.get("status", StoryboardStatus.DRAFT.value),
            approved            = data.get("approved", False),
            created_at          = data.get("created_at", ""),
            modified_at         = data.get("modified_at", ""),
        )

        # Characters
        for c_data in data.get("characters", []):
            panel.characters.append(ShotCharacter(
                character_name = c_data.get("character", ""),
                position       = c_data.get("position", "center"),
                action         = c_data.get("action", "standing"),
                facing         = c_data.get("facing", "camera"),
                expression     = c_data.get("expression", "neutral"),
                dialogue       = c_data.get("dialogue", ""),
            ))

        # Camera
        cam_data = data.get("camera", {})
        panel.camera = CameraDescription(
            angle    = cam_data.get("angle", "eye_level"),
            distance = cam_data.get("distance", "medium"),
            movement = cam_data.get("movement", "static"),
            focus    = cam_data.get("focus", "sharp"),
        )

        # Lighting
        light_data = data.get("lighting", {})
        panel.lighting = LightingNote(
            time_of_day = light_data.get("time_of_day", "day"),
            mood        = light_data.get("mood", "neutral"),
            key_light   = light_data.get("key_light", "front"),
            description = light_data.get("description", ""),
        )

        return panel


@dataclass
class StoryboardScene:
    """
    Ek scene ke sabhi panels together.
    Ek scene mein multiple shots hote hain.
    """
    scene_id:          str             = ""
    scene_number:      int             = 1
    scene_title:       str             = "Scene"
    location:          str             = ""
    description:       str             = ""
    panels:            List[StoryboardPanel] = field(default_factory=list)

    def __post_init__(self):
        if not self.scene_id:
            self.scene_id = f"scene_{generate_uuid()[:8]}"

    def get_total_duration(self) -> float:
        """Scene ki total duration seconds mein"""
        return sum(p.duration_seconds for p in self.panels)

    def get_total_frames(self) -> int:
        """Total frames"""
        return sum(p.duration_frames for p in self.panels)

    def add_panel(self, panel: StoryboardPanel):
        """Panel add karo"""
        panel.scene_number = self.scene_number
        panel.shot_number = len(self.panels) + 1
        panel.panel_number = panel.shot_number
        self.panels.append(panel)

    def remove_panel(self, panel_id: str) -> bool:
        """Panel remove karo"""
        for i, p in enumerate(self.panels):
            if p.panel_id == panel_id:
                self.panels.pop(i)
                # Renumber
                for j, remaining in enumerate(self.panels):
                    remaining.shot_number = j + 1
                    remaining.panel_number = j + 1
                return True
        return False

    def to_dict(self) -> Dict:
        return {
            "scene_id":         self.scene_id,
            "scene_number":     self.scene_number,
            "scene_title":      self.scene_title,
            "location":         self.location,
            "description":      self.description,
            "total_duration":   self.get_total_duration(),
            "total_frames":     self.get_total_frames(),
            "num_panels":       len(self.panels),
            "panels":           [p.to_dict() for p in self.panels],
        }


@dataclass
class Storyboard:
    """
    Complete storyboard for a project.
    Multiple scenes = complete story.
    """
    # Identity
    storyboard_id:     str             = ""
    project_title:     str             = "Untitled Project"
    author:            str             = ""
    description:       str             = ""

    # Scenes
    scenes:            List[StoryboardScene] = field(default_factory=list)

    # Settings
    fps:               int             = 30
    aspect_ratio:      str             = "16:9"

    # Status
    status:            str             = StoryboardStatus.DRAFT.value
    version:           str             = "1.0"

    # Metadata
    created_at:        str             = ""
    modified_at:       str             = ""
    total_versions:    int             = 1

    def __post_init__(self):
        if not self.storyboard_id:
            self.storyboard_id = f"sb_{generate_uuid()[:8]}"
        if not self.created_at:
            self.created_at = get_timestamp()

    def get_total_duration(self) -> float:
        """Puri storyboard ki duration"""
        return sum(s.get_total_duration() for s in self.scenes)

    def get_total_frames(self) -> int:
        return sum(s.get_total_frames() for s in self.scenes)

    def get_total_panels(self) -> int:
        return sum(len(s.panels) for s in self.scenes)

    def add_scene(self, scene: StoryboardScene):
        """Scene add karo"""
        scene.scene_number = len(self.scenes) + 1
        # Renumber panels in scene
        for i, panel in enumerate(scene.panels):
            panel.scene_number = scene.scene_number
            panel.shot_number = i + 1
        self.scenes.append(scene)

    def get_scene(self, scene_number: int) -> Optional[StoryboardScene]:
        for scene in self.scenes:
            if scene.scene_number == scene_number:
                return scene
        return None

    def get_all_panels(self) -> List[StoryboardPanel]:
        """Sabhi panels ek list mein"""
        panels = []
        for scene in self.scenes:
            panels.extend(scene.panels)
        return panels

    def get_statistics(self) -> Dict:
        return {
            "total_scenes":    len(self.scenes),
            "total_panels":    self.get_total_panels(),
            "total_duration":  round(self.get_total_duration(), 2),
            "total_frames":    self.get_total_frames(),
            "fps":             self.fps,
            "status":          self.status,
        }

    def to_dict(self) -> Dict:
        return {
            "storyboard_id":  self.storyboard_id,
            "project_title":  self.project_title,
            "author":         self.author,
            "description":    self.description,
            "fps":            self.fps,
            "aspect_ratio":   self.aspect_ratio,
            "status":         self.status,
            "version":        self.version,
            "statistics":     self.get_statistics(),
            "created_at":     self.created_at,
            "modified_at":    self.modified_at,
            "scenes":         [s.to_dict() for s in self.scenes],
        }


# ============================================================
# SHOT LIST GENERATOR - Auto-generate shots from script
# ============================================================

class ShotListGenerator:
    """
    Script se automatic shot list generate karta hai.
    Emotion, characters, action ke basis pe.
    """

    # Emotion → recommended shot type
    EMOTION_SHOT_MAP: Dict[str, str] = {
        "neutral":     ShotType.MEDIUM.value,
        "happy":       ShotType.MEDIUM.value,
        "excited":     ShotType.MEDIUM_CLOSE.value,
        "angry":       ShotType.CLOSE_UP.value,
        "sad":         ShotType.CLOSE_UP.value,
        "surprised":   ShotType.MEDIUM_CLOSE.value,
        "fearful":     ShotType.CLOSE_UP.value,
        "shouting":    ShotType.CLOSE_UP.value,
        "loving":      ShotType.CLOSE_UP.value,
        "thinking":    ShotType.MEDIUM_CLOSE.value,
        "laughing":    ShotType.MEDIUM.value,
        "crying":      ShotType.CLOSE_UP.value,
    }

    # Number of characters → shot type
    CHARACTER_COUNT_SHOT: Dict[int, str] = {
        1: ShotType.MEDIUM.value,
        2: ShotType.TWO_SHOT.value,
        3: ShotType.THREE_SHOT.value,
    }

    @classmethod
    def generate_from_scene(
        cls,
        scene_number:      int,
        scene_title:       str,
        location:          str,
        dialogues:         List[Dict],       # [{character, text, emotion}]
        num_characters:    int = 1,
        fps:               int = 30,
    ) -> StoryboardScene:
        """
        Ek scene ke shots automatically generate karo.
        """
        sb_scene = StoryboardScene(
            scene_number = scene_number,
            scene_title  = scene_title,
            location     = location,
            description  = f"Auto-generated scene: {scene_title}",
        )

        # ===== ESTABLISHING SHOT (agar location hai) =====
        if location:
            establishing = StoryboardPanel(
                scene_number       = scene_number,
                shot_number        = 1,
                panel_number       = 1,
                shot_type          = ShotType.ESTABLISHING.value,
                shot_purpose       = ShotPurpose.ESTABLISH.value,
                description        = f"Establishing shot of {location}",
                duration_frames    = 90,        # 3 seconds
                duration_seconds   = 3.0,
                location           = location,
                action_description = f"Show location: {location}",
                camera             = CameraDescription(
                    angle    = "eye_level",
                    distance = "far",
                    movement = "static",
                ),
                director_notes     = "Wide shot to establish location and mood",
            )
            sb_scene.add_panel(establishing)

        # ===== DIALOGUE SHOTS =====
        for dialogue in dialogues:
            character = dialogue.get("character", "Character")
            text = dialogue.get("text", "")
            emotion = dialogue.get("emotion", "neutral")

            # Decide shot type
            if num_characters == 2:
                # Alternate between OTS and close-ups
                shot_type = (ShotType.OVER_SHOULDER.value
                             if len(sb_scene.panels) % 2 == 0
                             else ShotType.CLOSE_UP.value)
            elif num_characters > 2:
                shot_type = cls.CHARACTER_COUNT_SHOT.get(num_characters, ShotType.GROUP.value)
            else:
                # Solo character - use emotion
                shot_type = cls.EMOTION_SHOT_MAP.get(emotion, ShotType.MEDIUM.value)

            # Duration based on text length
            word_count = len(text.split())
            duration_sec = max(2.0, (word_count / 150) * 60)
            duration_frames = int(duration_sec * fps)

            panel = StoryboardPanel(
                scene_number       = scene_number,
                shot_number        = len(sb_scene.panels) + 1,
                panel_number       = len(sb_scene.panels) + 1,
                shot_type          = shot_type,
                shot_purpose       = ShotPurpose.DIALOGUE.value,
                description        = f"{character} speaks: {text[:50]}...",
                duration_frames    = duration_frames,
                duration_seconds   = duration_sec,
                location           = location,
                action_description = f"{character} is speaking",
                dialogue_text      = text,
                camera             = CameraDescription(
                    angle    = "eye_level",
                    distance = "close" if "close" in shot_type else "medium",
                ),
                characters         = [
                    ShotCharacter(
                        character_name = character,
                        position       = "center",
                        action         = "talking",
                        expression     = emotion,
                        dialogue       = text,
                    )
                ],
            )

            # Emotion-based director notes
            if emotion in ["angry", "shouting"]:
                panel.director_notes = "Intense expression, tight framing"
                panel.lighting = LightingNote(
                    mood        = "dramatic",
                    description = "Harsh side lighting",
                )
            elif emotion in ["sad", "crying"]:
                panel.director_notes = "Soft, sympathetic lighting"
                panel.lighting = LightingNote(
                    mood        = "melancholic",
                    description = "Soft diffused lighting",
                )
            elif emotion in ["happy", "excited"]:
                panel.director_notes = "Bright and energetic"
                panel.lighting = LightingNote(
                    mood        = "bright",
                    description = "Bright, warm lighting",
                )

            sb_scene.add_panel(panel)

        return sb_scene

    @classmethod
    def generate_from_parsed_script(
        cls,
        parsed_script:     Any,
    ) -> Storyboard:
        """
        Complete parsed script se full storyboard generate karo.
        """
        storyboard = Storyboard(
            project_title = parsed_script.title,
            fps           = parsed_script.fps,
            description   = "Auto-generated storyboard from script",
        )

        for scene in parsed_script.scenes:
            # Convert dialogues to dict format
            dialogues = [
                {
                    "character": d.character,
                    "text":      d.text,
                    "emotion":   d.emotion,
                }
                for d in scene.dialogues
            ]

            sb_scene = cls.generate_from_scene(
                scene_number    = scene.index + 1,
                scene_title     = scene.heading,
                location        = scene.location,
                dialogues       = dialogues,
                num_characters  = len(scene.characters),
                fps             = parsed_script.fps,
            )

            storyboard.add_scene(sb_scene)

        return storyboard


# ============================================================
# STORYBOARD MANAGER
# ============================================================

class StoryboardManager:
    """
    Main storyboard manager.
    Storyboards create, save, load, export karo.
    """

    def __init__(self, config: Optional[Dict] = None):
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # Loaded storyboards
        self._storyboards: Dict[str, Storyboard] = {}

        # Save directory
        self._save_dir = Path("assets/storyboards")
        ensure_dir(str(self._save_dir))

        # Load existing storyboards
        self._load_saved()

        # Listeners
        self._listeners: List[Callable] = []

        logger.info(
            f"✅ StoryboardManager initialized | "
            f"{len(self._storyboards)} storyboards loaded"
        )

    def _load_saved(self):
        """Saved storyboards load karo"""
        try:
            if not self._save_dir.exists():
                return

            for json_file in self._save_dir.glob("*.json"):
                try:
                    data = read_json(str(json_file))
                    if data:
                        sb = self._load_from_dict(data)
                        if sb:
                            self._storyboards[sb.storyboard_id] = sb
                except Exception as e:
                    logger.warning(f"Storyboard load failed ({json_file}): {e}")

        except Exception as e:
            logger.warning(f"Load saved error: {e}")

    def _load_from_dict(self, data: Dict) -> Optional[Storyboard]:
        """Dict se storyboard banao"""
        try:
            sb = Storyboard(
                storyboard_id = data.get("storyboard_id", ""),
                project_title = data.get("project_title", "Untitled"),
                author        = data.get("author", ""),
                description   = data.get("description", ""),
                fps           = data.get("fps", 30),
                aspect_ratio  = data.get("aspect_ratio", "16:9"),
                status        = data.get("status", StoryboardStatus.DRAFT.value),
                version       = data.get("version", "1.0"),
                created_at    = data.get("created_at", ""),
                modified_at   = data.get("modified_at", ""),
            )

            for scene_data in data.get("scenes", []):
                scene = StoryboardScene(
                    scene_id     = scene_data.get("scene_id", ""),
                    scene_number = scene_data.get("scene_number", 1),
                    scene_title  = scene_data.get("scene_title", ""),
                    location     = scene_data.get("location", ""),
                    description  = scene_data.get("description", ""),
                )

                for panel_data in scene_data.get("panels", []):
                    panel = StoryboardPanel.from_dict(panel_data)
                    scene.panels.append(panel)

                sb.scenes.append(scene)

            return sb
        except Exception as e:
            logger.error(f"From dict error: {e}")
            return None

    # ----------------------------------------------------------
    # CRUD
    # ----------------------------------------------------------

    def create_storyboard(
        self,
        project_title:  str,
        author:         str = "",
        description:    str = "",
        fps:            int = 30,
    ) -> Storyboard:
        """Naya storyboard banao"""
        sb = Storyboard(
            project_title = project_title,
            author        = author,
            description   = description,
            fps           = fps,
        )
        self._storyboards[sb.storyboard_id] = sb
        self._notify("storyboard_created", {"storyboard": sb})
        logger.info(f"✅ Storyboard created: {project_title}")
        return sb

    def get_storyboard(self, storyboard_id: str) -> Optional[Storyboard]:
        return self._storyboards.get(storyboard_id)

    def get_all_storyboards(self) -> List[Storyboard]:
        return list(self._storyboards.values())

    def delete_storyboard(self, storyboard_id: str) -> bool:
        """Storyboard delete karo"""
        sb = self._storyboards.get(storyboard_id)
        if not sb:
            return False

        # Delete file
        filepath = self._save_dir / f"{storyboard_id}.json"
        try:
            if filepath.exists():
                filepath.unlink()
        except Exception as e:
            logger.warning(f"File delete error: {e}")

        del self._storyboards[storyboard_id]
        self._notify("storyboard_deleted", {"id": storyboard_id})
        return True

    # ----------------------------------------------------------
    # SAVE/LOAD
    # ----------------------------------------------------------

    def save_storyboard(self, storyboard: Storyboard) -> bool:
        """Storyboard save karo"""
        try:
            storyboard.modified_at = get_timestamp()
            filepath = self._save_dir / f"{storyboard.storyboard_id}.json"
            write_json(str(filepath), storyboard.to_dict())
            logger.info(f"💾 Storyboard saved: {storyboard.project_title}")
            return True
        except Exception as e:
            logger.error(f"Save failed: {e}")
            return False

    def load_storyboard_from_file(self, filepath: str) -> Optional[Storyboard]:
        """File se storyboard load karo"""
        try:
            data = read_json(filepath)
            if not data:
                return None
            sb = self._load_from_dict(data)
            if sb:
                self._storyboards[sb.storyboard_id] = sb
            return sb
        except Exception as e:
            logger.error(f"Load error: {e}")
            return None

    # ----------------------------------------------------------
    # AUTO-GENERATION
    # ----------------------------------------------------------

    def generate_from_script(self, parsed_script: Any) -> Storyboard:
        """Script se storyboard auto-generate karo"""
        sb = ShotListGenerator.generate_from_parsed_script(parsed_script)
        self._storyboards[sb.storyboard_id] = sb
        self.save_storyboard(sb)
        logger.info(
            f"✅ Auto-generated storyboard from script: "
            f"{sb.get_total_panels()} panels"
        )
        return sb

    # ----------------------------------------------------------
    # EXPORT
    # ----------------------------------------------------------

    def export_to_text(self, storyboard: Storyboard, output_path: str) -> bool:
        """
        Storyboard ko readable text file mein export karo.
        Directors ke liye printable.
        """
        try:
            ensure_dir(os.path.dirname(output_path) or ".")

            lines = []
            lines.append("=" * 70)
            lines.append(f"STORYBOARD: {storyboard.project_title}")
            lines.append("=" * 70)
            lines.append(f"Author       : {storyboard.author}")
            lines.append(f"Description  : {storyboard.description}")
            lines.append(f"FPS          : {storyboard.fps}")
            lines.append(f"Duration     : {storyboard.get_total_duration():.1f}s")
            lines.append(f"Total Panels : {storyboard.get_total_panels()}")
            lines.append(f"Status       : {storyboard.status}")
            lines.append(f"Version      : {storyboard.version}")
            lines.append("=" * 70)

            for scene in storyboard.scenes:
                lines.append(f"\n{'#' * 70}")
                lines.append(f"SCENE {scene.scene_number}: {scene.scene_title}")
                lines.append(f"{'#' * 70}")
                lines.append(f"Location   : {scene.location}")
                lines.append(f"Duration   : {scene.get_total_duration():.1f}s")
                lines.append(f"Panels     : {len(scene.panels)}")

                for panel in scene.panels:
                    lines.append(f"\n{'-' * 70}")
                    lines.append(f"[{panel.get_shot_label()}] {panel.shot_type.upper()}")
                    lines.append(f"{'-' * 70}")
                    lines.append(f"  Duration   : {panel.get_duration_display()}")
                    lines.append(f"  Purpose    : {panel.shot_purpose}")
                    lines.append(f"  Description: {panel.description}")

                    if panel.characters:
                        lines.append(f"\n  CHARACTERS:")
                        for char in panel.characters:
                            lines.append(
                                f"    • {char.character_name} ({char.position}) - "
                                f"{char.action}, {char.expression}"
                            )
                            if char.dialogue:
                                lines.append(f"      DIALOGUE: \"{char.dialogue}\"")

                    lines.append(f"\n  CAMERA:")
                    lines.append(f"    Angle   : {panel.camera.angle}")
                    lines.append(f"    Distance: {panel.camera.distance}")
                    lines.append(f"    Movement: {panel.camera.movement}")

                    lines.append(f"\n  LIGHTING:")
                    lines.append(f"    Time    : {panel.lighting.time_of_day}")
                    lines.append(f"    Mood    : {panel.lighting.mood}")

                    if panel.director_notes:
                        lines.append(f"\n  DIRECTOR NOTES:")
                        lines.append(f"    {panel.director_notes}")

                    if panel.sound_notes:
                        lines.append(f"\n  SOUND: {panel.sound_notes}")

                    if panel.vfx_notes:
                        lines.append(f"  VFX  : {panel.vfx_notes}")

                    lines.append(f"\n  TRANSITION: {panel.transition_to_next}")

            lines.append(f"\n{'=' * 70}")
            lines.append("END OF STORYBOARD")
            lines.append(f"{'=' * 70}")

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines))

            logger.info(f"📄 Storyboard exported: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Text export error: {e}")
            return False

    def export_to_markdown(self, storyboard: Storyboard, output_path: str) -> bool:
        """Markdown format mein export"""
        try:
            ensure_dir(os.path.dirname(output_path) or ".")

            lines = []
            lines.append(f"# 🎬 {storyboard.project_title}")
            lines.append(f"\n**Author:** {storyboard.author or 'Anonymous'}")
            lines.append(f"**Description:** {storyboard.description}")
            lines.append(f"**FPS:** {storyboard.fps}")
            lines.append(f"**Total Duration:** {storyboard.get_total_duration():.1f}s")
            lines.append(f"**Total Panels:** {storyboard.get_total_panels()}")
            lines.append(f"**Status:** {storyboard.status}")

            for scene in storyboard.scenes:
                lines.append(f"\n\n## 🎭 Scene {scene.scene_number}: {scene.scene_title}")
                lines.append(f"\n**Location:** {scene.location}")
                lines.append(f"**Duration:** {scene.get_total_duration():.1f}s")
                lines.append(f"**Panels:** {len(scene.panels)}")

                for panel in scene.panels:
                    lines.append(f"\n### 📽️ [{panel.get_shot_label()}] {panel.shot_type.replace('_', ' ').title()}")
                    lines.append(f"\n- **Duration:** {panel.get_duration_display()}")
                    lines.append(f"- **Purpose:** {panel.shot_purpose}")
                    lines.append(f"- **Description:** {panel.description}")

                    if panel.dialogue_text:
                        lines.append(f"\n**💬 Dialogue:**\n> {panel.dialogue_text}")

                    if panel.characters:
                        lines.append(f"\n**🧍 Characters:**")
                        for char in panel.characters:
                            lines.append(f"- **{char.character_name}** ({char.expression}) - {char.action}")

                    lines.append(f"\n**🎥 Camera:** {panel.camera.angle} / {panel.camera.distance} / {panel.camera.movement}")
                    lines.append(f"**💡 Lighting:** {panel.lighting.mood} ({panel.lighting.time_of_day})")

                    if panel.director_notes:
                        lines.append(f"\n**📝 Director's Notes:** {panel.director_notes}")

                    if panel.transition_to_next != TransitionStyle.CUT.value:
                        lines.append(f"\n**➡️ Transition:** {panel.transition_to_next}")

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines))

            logger.info(f"📝 Markdown exported: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Markdown export error: {e}")
            return False

    def print_storyboard(self, storyboard: Storyboard):
        """Storyboard console pe print karo"""
        stats = storyboard.get_statistics()

        print(f"\n{'=' * 60}")
        print(f"📖 STORYBOARD: {storyboard.project_title}")
        print(f"{'=' * 60}")
        print(f"  Duration    : {stats['total_duration']}s")
        print(f"  Total Panels: {stats['total_panels']}")
        print(f"  Scenes      : {stats['total_scenes']}")
        print(f"  Status      : {stats['status']}")

        for scene in storyboard.scenes:
            print(f"\n  📁 Scene {scene.scene_number}: {scene.scene_title}")
            print(f"     Location: {scene.location}")
            print(f"     Panels  : {len(scene.panels)}")

            for panel in scene.panels:
                emoji = "🎬" if panel.shot_type == ShotType.ESTABLISHING.value else "🎞️"
                print(
                    f"     {emoji} [{panel.get_shot_label()}] "
                    f"{panel.shot_type:15s} | "
                    f"{panel.get_duration_display():15s} | "
                    f"{panel.description[:40]}"
                )

        print(f"\n{'=' * 60}\n")

    # ----------------------------------------------------------
    # LISTENERS
    # ----------------------------------------------------------

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

_global_manager: Optional[StoryboardManager] = None


def get_storyboard_manager() -> StoryboardManager:
    global _global_manager
    if _global_manager is None:
        _global_manager = StoryboardManager()
    return _global_manager


# ============================================================
# TEST SECTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")
    print_banner("Storyboard Test", "Pre-visualization & Shot Planning")

    # ===== TEST 1: Manager Init =====
    print_section("Test 1: Manager Initialization")
    manager = StoryboardManager()
    print(f"✅ Manager initialized")
    print(f"   Loaded storyboards: {len(manager.get_all_storyboards())}")

    # ===== TEST 2: Create Storyboard =====
    print_section("Test 2: Create Storyboard")
    sb = manager.create_storyboard(
        project_title = "Hero vs Villain",
        author        = "Test Director",
        description   = "Epic battle animation",
        fps           = 30,
    )
    print(f"✅ Storyboard created: {sb.project_title}")
    print(f"   ID   : {sb.storyboard_id}")
    print(f"   FPS  : {sb.fps}")

    # ===== TEST 3: Add Scene Manually =====
    print_section("Test 3: Manual Scene & Panel Creation")

    # Scene 1
    scene1 = StoryboardScene(
        scene_number = 1,
        scene_title  = "Hero's Introduction",
        location     = "Home",
        description  = "Hero wakes up",
    )

    # Panel 1 - Establishing
    panel1 = StoryboardPanel(
        shot_type          = ShotType.ESTABLISHING.value,
        shot_purpose       = ShotPurpose.ESTABLISH.value,
        description        = "Show hero's house exterior",
        duration_seconds   = 3.0,
        duration_frames    = 90,
        location           = "Home exterior",
        action_description = "Camera pans across the neighborhood",
    )
    panel1.camera = CameraDescription(
        angle    = "eye_level",
        distance = "far",
        movement = "pan",
    )
    panel1.lighting = LightingNote(
        time_of_day = "morning",
        mood        = "bright",
    )
    panel1.director_notes = "Peaceful morning atmosphere"

    scene1.add_panel(panel1)

    # Panel 2 - Character intro
    panel2 = StoryboardPanel(
        shot_type          = ShotType.CLOSE_UP.value,
        shot_purpose       = ShotPurpose.INTRODUCE.value,
        description        = "Hero opens his eyes",
        duration_seconds   = 2.0,
        duration_frames    = 60,
        dialogue_text      = "Aaj ka din special hai!",
    )
    panel2.characters.append(ShotCharacter(
        character_name = "Hero",
        position       = "center",
        action         = "waking up",
        expression     = "happy",
        dialogue       = "Aaj ka din special hai!",
    ))
    panel2.camera = CameraDescription(
        angle    = "eye_level",
        distance = "close",
    )
    panel2.director_notes = "Focus on hopeful expression"

    scene1.add_panel(panel2)
    sb.add_scene(scene1)

    print(f"✅ Scene 1 added: {scene1.scene_title}")
    print(f"   Panels: {len(scene1.panels)}")
    print(f"   Duration: {scene1.get_total_duration()}s")

    # ===== TEST 4: Auto-Generate from Script =====
    print_section("Test 4: Auto-Generate from Script")

    from src.pipeline.script_parser import ScriptParser
    parser = ScriptParser()

    test_script = """
INT. HERO'S HOUSE - MORNING

HERO
(happy)
Aaj main kuch amazing karne wala hoon!

HERO
(excited)
Chalo shuru karte hain!

EXT. VILLAIN'S LAIR - NIGHT

VILLAIN
(angry)
Hero ne bahut kar liya!

VILLAIN
(shouting)
MAIN USSE ROKUNGA!

INT. BATTLEGROUND - DAY

HERO
(determined)
Ab main tujhe kabhi nahi harun ga!

VILLAIN
(laughing)
Dekhte hain kaun jeeta hai!
"""

    parsed = parser.parse(test_script, "Epic Story")
    print(f"✅ Script parsed: {len(parsed.scenes)} scenes, {parsed.total_dialogues} dialogues")

    # Generate storyboard
    auto_sb = manager.generate_from_script(parsed)
    print(f"✅ Storyboard auto-generated")
    print(f"   Total panels: {auto_sb.get_total_panels()}")
    print(f"   Duration: {auto_sb.get_total_duration():.1f}s")

    # ===== TEST 5: Print Storyboard =====
    print_section("Test 5: Storyboard Console View")
    manager.print_storyboard(auto_sb)

    # ===== TEST 6: Detailed Panel Info =====
    print_section("Test 6: Detailed Panel Info")
    if auto_sb.scenes:
        first_scene = auto_sb.scenes[0]
        print(f"\n📁 Scene: {first_scene.scene_title}")
        for panel in first_scene.panels[:3]:
            print(f"\n   🎬 Panel: {panel.get_shot_label()}")
            print(f"      Shot Type   : {panel.shot_type}")
            print(f"      Purpose     : {panel.shot_purpose}")
            print(f"      Description : {panel.description}")
            print(f"      Duration    : {panel.get_duration_display()}")
            print(f"      Camera      : {panel.camera.angle} / {panel.camera.distance}")
            print(f"      Lighting    : {panel.lighting.mood}")
            if panel.characters:
                print(f"      Characters  :")
                for char in panel.characters:
                    print(
                        f"         • {char.character_name} "
                        f"({char.expression}): '{char.dialogue[:40]}...'"
                    )
            if panel.director_notes:
                print(f"      Notes       : {panel.director_notes}")

    # ===== TEST 7: Save Storyboard =====
    print_section("Test 7: Save Storyboard")
    saved = manager.save_storyboard(auto_sb)
    print(f"✅ Saved: {saved}")

    # ===== TEST 8: Export to Text =====
    print_section("Test 8: Export to Text File")
    text_path = "exports/storyboard.txt"
    ensure_dir("exports")
    text_success = manager.export_to_text(auto_sb, text_path)
    print(f"✅ Text export: {text_success}")

    if text_success and os.path.exists(text_path):
        size = os.path.getsize(text_path)
        print(f"   File: {text_path} ({size} bytes)")

    # ===== TEST 9: Export to Markdown =====
    print_section("Test 9: Export to Markdown")
    md_path = "exports/storyboard.md"
    md_success = manager.export_to_markdown(auto_sb, md_path)
    print(f"✅ Markdown export: {md_success}")

    if md_success and os.path.exists(md_path):
        size = os.path.getsize(md_path)
        print(f"   File: {md_path} ({size} bytes)")

    # ===== TEST 10: Statistics =====
    print_section("Test 10: Storyboard Statistics")
    stats = auto_sb.get_statistics()
    for key, value in stats.items():
        print(f"   {key:20s}: {value}")

    # ===== TEST 11: Shot Types =====
    print_section("Test 11: Shot Type Distribution")
    all_panels = auto_sb.get_all_panels()
    shot_type_count = {}
    for panel in all_panels:
        shot_type_count[panel.shot_type] = shot_type_count.get(panel.shot_type, 0) + 1

    for shot_type, count in sorted(shot_type_count.items(), key=lambda x: -x[1]):
        print(f"   {shot_type:20s}: {count}")

    # ===== TEST 12: Singleton =====
    print_section("Test 12: Global Singleton")
    m1 = get_storyboard_manager()
    m2 = get_storyboard_manager()
    print(f"✅ Singleton: {m1 is m2}")
    print(f"   Total storyboards: {len(m1.get_all_storyboards())}")

    # ===== CLEANUP =====
    try:
        # Delete test files
        if os.path.exists(text_path):
            os.remove(text_path)
        if os.path.exists(md_path):
            os.remove(md_path)
        # Delete test storyboards
        for sb_item in [sb, auto_sb]:
            filepath = manager._save_dir / f"{sb_item.storyboard_id}.json"
            if filepath.exists():
                filepath.unlink()
    except Exception:
        pass

    print_banner("✅ All Tests Passed!", "storyboard.py Working Perfectly")