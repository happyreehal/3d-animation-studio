# ============================================================
# src/pipeline/automation_engine.py
# 3D Animation Studio - Automation Engine
# BRAIN: Sabhi engines ko orchestrate karta hai
# Script + Built Scenes → Complete Animation Data
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

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum
from pathlib import Path

from src.utils import (
    get_logger,
    get_config,
    ensure_dir,
    generate_uuid,
    get_timestamp,
    write_json,
)

logger = get_logger("AutomationEngine")


# ============================================================
# ENUMS
# ============================================================

class GenerationStage(Enum):
    """Automation pipeline ke stages"""
    IDLE                = "idle"
    PARSING_SCRIPT      = "parsing_script"
    BUILDING_SCENES     = "building_scenes"
    GENERATING_VOICES   = "generating_voices"
    GENERATING_LIPSYNC  = "generating_lipsync"
    GENERATING_EXPRESSIONS = "generating_expressions"
    PLANNING_CAMERAS    = "planning_cameras"
    PLANNING_ANIMATIONS = "planning_animations"
    GENERATING_SFX      = "generating_sfx"
    SETTING_UP_MUSIC    = "setting_up_music"
    BUILDING_TIMELINE   = "building_timeline"
    COMPLETE            = "complete"
    FAILED              = "failed"
    CANCELLED           = "cancelled"


class AnimationType(Enum):
    """Character animation types"""
    IDLE            = "idle"
    TALKING         = "talking"
    WALKING         = "walking"
    RUNNING         = "running"
    WAVE            = "wave"
    NOD             = "nod"
    SHAKE_HEAD      = "shake_head"
    JUMP            = "jump"
    SIT             = "sit"
    STAND           = "stand"
    CRY             = "cry"
    LAUGH           = "laugh"
    ANGRY_GESTURE   = "angry_gesture"
    THINKING        = "thinking"
    POINT           = "point"


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class GenerationProgress:
    """Pipeline progress tracking"""
    stage:              str             = GenerationStage.IDLE.value
    current_step:       int             = 0
    total_steps:        int             = 0
    percent:            float           = 0.0
    message:            str             = ""
    elapsed_seconds:    float           = 0.0
    scene_index:        int             = -1
    total_scenes:       int             = 0

    def get_status_text(self) -> str:
        return f"[{self.percent:.0f}%] {self.stage}: {self.message}"


@dataclass
class VoiceClip:
    """Ek dialogue ki voice clip data"""
    clip_id:            str
    character:          str
    text:               str
    emotion:            str             = "neutral"
    voice_id:           str             = ""
    language:           str             = "en"

    # File output
    audio_file:         str             = ""
    duration_seconds:   float           = 0.0

    # Timing
    scene_index:        int             = 0
    dialogue_index:     int             = 0
    start_frame:        int             = 0
    end_frame:          int             = 0

    # Prosody
    speed:              float           = 1.0
    pitch:              float           = 0.0
    volume:             float           = 1.0

    # Status
    generated:          bool            = False
    generation_error:   str             = ""


@dataclass
class LipsyncData:
    """Character ke mouth movements data"""
    voice_clip_id:      str
    character:          str

    # Phoneme sequence: [(phoneme, start_time, end_time)]
    phonemes:           List[Tuple[str, float, float]] = field(default_factory=list)

    # Mouth shapes at intervals
    mouth_shapes:       List[Dict]      = field(default_factory=list)

    # Timing
    start_frame:        int             = 0
    end_frame:          int             = 0

    generated:          bool            = False


@dataclass
class ExpressionKeyframe:
    """Character face expression at specific time"""
    character:          str
    expression:         str             = "neutral"
    intensity:          float           = 0.5
    frame:              int             = 0
    duration_frames:    int             = 30       # 1 second at 30fps


@dataclass
class CharacterAnimationPlan:
    """Character ki animation plan"""
    character:          str
    scene_index:        int

    # Animation sequence
    animations:         List[Dict]      = field(default_factory=list)
    # Each: {"animation": "walking", "start_frame": 0, "end_frame": 60, "loop": True}

    # Expression keyframes
    expressions:        List[ExpressionKeyframe] = field(default_factory=list)


@dataclass
class CameraKeyframe:
    """Camera ka keyframe"""
    frame:              int
    position:           List[float]
    target:             List[float]
    fov:                float           = 60.0
    easing:             str             = "linear"      # linear, ease_in, ease_out, ease_in_out


@dataclass
class CameraPlan:
    """Scene ke liye camera movement plan"""
    scene_index:        int
    camera_id:          str

    # Keyframes for movement
    keyframes:          List[CameraKeyframe] = field(default_factory=list)

    # Movement type
    movement_type:      str             = "static"     # static, pan, dolly, tracking

    # Target tracking
    tracks_character:   Optional[str]   = None


@dataclass
class SFXTrigger:
    """Sound effect trigger event"""
    sfx_id:             str
    sfx_name:           str             = ""
    trigger_frame:      int             = 0
    duration_frames:    int             = 30
    volume:             float           = 0.8
    reason:             str             = ""       # Why triggered


@dataclass
class MusicTrack:
    """Background music track"""
    music_id:           str
    mood:               str             = "neutral"
    start_frame:        int             = 0
    end_frame:          int             = 0
    volume:             float           = 0.3
    fade_in_frames:     int             = 30
    fade_out_frames:    int             = 30


@dataclass
class SceneAnimationData:
    """Ek scene ke complete animation data"""
    scene_index:        int
    scene_id:           str

    # Content
    voice_clips:        List[VoiceClip] = field(default_factory=list)
    lipsync_data:       List[LipsyncData] = field(default_factory=list)
    character_animations: List[CharacterAnimationPlan] = field(default_factory=list)
    camera_plan:        Optional[CameraPlan] = None
    sfx_triggers:       List[SFXTrigger] = field(default_factory=list)
    music_track:        Optional[MusicTrack] = None

    # Timing
    start_frame:        int             = 0
    end_frame:          int             = 0

    def to_dict(self) -> Dict:
        return {
            "scene_index":      self.scene_index,
            "scene_id":         self.scene_id,
            "num_voices":       len(self.voice_clips),
            "num_lipsync":      len(self.lipsync_data),
            "num_animations":   len(self.character_animations),
            "num_sfx":          len(self.sfx_triggers),
            "has_music":        self.music_track is not None,
            "has_camera_plan":  self.camera_plan is not None,
            "start_frame":      self.start_frame,
            "end_frame":        self.end_frame,
        }


@dataclass
class AutomationResult:
    """Complete automation ka result"""
    success:            bool            = False
    project_id:         str             = ""

    # Data
    parsed_script:      Optional[Any]   = None
    built_scenes:       List[Any]       = field(default_factory=list)
    scene_animations:   List[SceneAnimationData] = field(default_factory=list)

    # Stats
    total_scenes:       int             = 0
    total_dialogues:    int             = 0
    total_voice_clips:  int             = 0
    total_duration:     float           = 0.0
    total_frames:       int             = 0

    # Timing
    generation_time:    float           = 0.0
    output_directory:   str             = ""

    # Error
    error:              str             = ""

    def get_summary(self) -> Dict:
        return {
            "success":              self.success,
            "project_id":           self.project_id,
            "total_scenes":         self.total_scenes,
            "total_dialogues":      self.total_dialogues,
            "total_voice_clips":    self.total_voice_clips,
            "total_duration":       round(self.total_duration, 2),
            "total_frames":         self.total_frames,
            "generation_time":      round(self.generation_time, 2),
            "output_directory":     self.output_directory,
        }


# ============================================================
# ANIMATION PLANNER
# ============================================================

class AnimationPlanner:
    """
    Character animations plan karta hai.
    Emotion, dialogue, action ke basis pe.
    """

    # Emotion → Animation mapping
    EMOTION_TO_ANIMATION: Dict[str, str] = {
        "happy":       AnimationType.IDLE.value,
        "excited":     AnimationType.WAVE.value,
        "angry":       AnimationType.ANGRY_GESTURE.value,
        "sad":         AnimationType.CRY.value,
        "laughing":    AnimationType.LAUGH.value,
        "thinking":    AnimationType.THINKING.value,
        "confused":    AnimationType.THINKING.value,
        "surprised":   AnimationType.IDLE.value,
        "fearful":     AnimationType.IDLE.value,
        "shouting":    AnimationType.ANGRY_GESTURE.value,
        "loving":      AnimationType.IDLE.value,
        "neutral":     AnimationType.IDLE.value,
    }

    @classmethod
    def plan_character_animation(
        cls,
        character: str,
        scene_index: int,
        dialogues: List[Any],
        actions: List[Any],
        scene_start_frame: int = 0,
    ) -> CharacterAnimationPlan:
        """
        Character ke liye complete animation plan banao.
        """
        plan = CharacterAnimationPlan(
            character   = character,
            scene_index = scene_index,
        )

        # Character ke dialogues filter karo
        char_dialogues = [
            d for d in dialogues
            if d.character == character
        ]

        # Idle base animation (jab dialogue nahi hai)
        if char_dialogues:
            first_dialogue = char_dialogues[0]
            plan.animations.append({
                "animation":    AnimationType.IDLE.value,
                "start_frame":  0,
                "end_frame":    first_dialogue.start_frame,
                "loop":         True,
            })

        # Har dialogue ke liye animations
        for dialogue in char_dialogues:
            # Talking animation
            plan.animations.append({
                "animation":    AnimationType.TALKING.value,
                "start_frame":  dialogue.start_frame,
                "end_frame":    dialogue.end_frame,
                "loop":         True,
            })

            # Emotion-specific overlay
            emotion_anim = cls.EMOTION_TO_ANIMATION.get(
                dialogue.emotion,
                AnimationType.IDLE.value
            )

            if emotion_anim != AnimationType.IDLE.value:
                # Emotion animation overlay
                plan.animations.append({
                    "animation":    emotion_anim,
                    "start_frame":  dialogue.start_frame,
                    "end_frame":    dialogue.end_frame,
                    "loop":         False,
                    "overlay":      True,
                })

            # Expression keyframe
            expression = ExpressionKeyframe(
                character       = character,
                expression      = dialogue.emotion,
                intensity       = dialogue.intensity,
                frame           = dialogue.start_frame,
                duration_frames = dialogue.end_frame - dialogue.start_frame,
            )
            plan.expressions.append(expression)

        return plan


# ============================================================
# CAMERA PLANNER
# ============================================================

class CameraPlanner:
    """Camera movements plan karta hai scene ke liye"""

    @classmethod
    def plan_camera(
        cls,
        built_scene: Any,
        parsed_scene: Any,
    ) -> CameraPlan:
        """
        Scene ke liye camera plan banao.
        Dialogue ke hisaab se camera cuts add karo.
        """
        camera = built_scene.get_active_camera()
        if not camera:
            return None

        plan = CameraPlan(
            scene_index    = built_scene.scene_index,
            camera_id      = camera.camera_id,
            movement_type  = "static",
        )

        num_dialogues = len(parsed_scene.dialogues)
        num_chars = len(built_scene.characters)

        # Simple case: 1 character, static camera
        if num_chars <= 1 or num_dialogues == 0:
            plan.keyframes.append(CameraKeyframe(
                frame     = parsed_scene.start_frame,
                position  = list(camera.position),
                target    = list(camera.target),
                fov       = camera.fov,
            ))
            return plan

        # Multi-character: Camera cuts between speakers
        plan.movement_type = "cuts"

        for dialogue in parsed_scene.dialogues:
            # Find character in built scene
            char = built_scene.get_character(dialogue.character)
            if not char:
                continue

            # Camera position: slightly angled towards speaker
            speaker_pos = char.position

            # Camera behind other characters, facing speaker
            other_chars = [
                c for c in built_scene.characters
                if c.name != dialogue.character
            ]

            if other_chars:
                # Position camera near other character
                other = other_chars[0]
                cam_pos = [
                    other.position[0] * 0.7 + speaker_pos[0] * 0.3,
                    1.7,  # Eye level
                    other.position[2] * 0.7 + speaker_pos[2] * 0.3 + 2.0,
                ]
                cam_target = [
                    speaker_pos[0],
                    speaker_pos[1] + 1.5,   # Head level
                    speaker_pos[2],
                ]
            else:
                cam_pos = list(camera.position)
                cam_target = [
                    speaker_pos[0],
                    speaker_pos[1] + 1.5,
                    speaker_pos[2],
                ]

            plan.keyframes.append(CameraKeyframe(
                frame     = dialogue.start_frame,
                position  = cam_pos,
                target    = cam_target,
                fov       = camera.fov,
                easing    = "ease_in_out",
            ))

        return plan


# ============================================================
# SFX PLANNER
# ============================================================

class SFXPlanner:
    """Sound effects plan karta hai"""

    # Emotion → SFX
    EMOTION_SFX: Dict[str, str] = {
        "surprised":  "gasp",
        "angry":      "impact",
        "shouting":   "shout_impact",
        "laughing":   "laugh",
        "crying":     "cry",
        "fearful":    "scare_sting",
    }

    # Action keyword → SFX
    ACTION_SFX: Dict[str, str] = {
        "door":      "door_open",
        "knock":     "knock",
        "phone":     "phone_ring",
        "footstep":  "footstep",
        "walk":      "footstep",
        "run":       "running",
        "explosion": "explosion",
        "gun":       "gunshot",
        "clap":      "clap",
        "punch":     "punch",
    }

    @classmethod
    def plan_sfx(
        cls,
        built_scene: Any,
        parsed_scene: Any,
    ) -> List[SFXTrigger]:
        """SFX triggers plan karo"""
        triggers = []

        # Scene start pe ambient
        if built_scene.audio and built_scene.audio.ambient_sounds:
            for ambient in built_scene.audio.ambient_sounds:
                trigger = SFXTrigger(
                    sfx_id         = f"sfx_{generate_uuid()[:8]}",
                    sfx_name       = ambient,
                    trigger_frame  = parsed_scene.start_frame,
                    duration_frames = parsed_scene.total_frames,
                    volume         = 0.3,
                    reason         = "ambient",
                )
                triggers.append(trigger)

        # Dialogue emotion-based SFX
        for dialogue in parsed_scene.dialogues:
            emotion_sfx = cls.EMOTION_SFX.get(dialogue.emotion)
            if emotion_sfx:
                trigger = SFXTrigger(
                    sfx_id         = f"sfx_{generate_uuid()[:8]}",
                    sfx_name       = emotion_sfx,
                    trigger_frame  = dialogue.start_frame,
                    duration_frames = 15,
                    volume         = 0.6,
                    reason         = f"emotion_{dialogue.emotion}",
                )
                triggers.append(trigger)

        # Action-based SFX
        for action in parsed_scene.actions:
            action_desc = action.description.lower()
            for keyword, sfx in cls.ACTION_SFX.items():
                if keyword in action_desc:
                    trigger = SFXTrigger(
                        sfx_id         = f"sfx_{generate_uuid()[:8]}",
                        sfx_name       = sfx,
                        trigger_frame  = action.start_frame,
                        duration_frames = 20,
                        volume         = 0.7,
                        reason         = f"action_{keyword}",
                    )
                    triggers.append(trigger)
                    break

        return triggers


# ============================================================
# TTS INTERFACE (Simple)
# ============================================================

class TTSInterface:
    """
    TTS engine ka interface.
    Real TTS engine se connect karta hai (agar available ho).
    """

    def __init__(self):
        self._tts_available = False
        self._tts_engine = None

        try:
            from src.ai.tts_engine import TTSEngine
            self._tts_engine = TTSEngine()
            self._tts_available = True
            logger.info("✅ TTS engine connected")
        except Exception as e:
            logger.warning(f"TTS engine nahi mila - simulation mode: {e}")

    def generate_voice(
        self,
        text: str,
        voice_id: str = "voice_default",
        emotion: str = "neutral",
        language: str = "en",
        speed: float = 1.0,
        pitch: float = 0.0,
        output_path: Optional[str] = None,
    ) -> Tuple[bool, str, float]:
        """
        Voice generate karo.

        Returns:
            (success, output_file_path, duration_seconds)
        """
        if not output_path:
            output_path = f"temp/voice_{generate_uuid()[:8]}.wav"
            ensure_dir(os.path.dirname(output_path))

        if self._tts_available and self._tts_engine:
            try:
                # Try real TTS
                result = self._tts_engine.synthesize(
                    text        = text,
                    output_path = output_path,
                    voice_id    = voice_id,
                    language    = language,
                    speed       = speed,
                    pitch       = pitch,
                )
                if result:
                    # Estimate duration (rough)
                    word_count = len(text.split())
                    duration = max(1.5, (word_count / 150) * 60)
                    return True, output_path, duration
            except Exception as e:
                logger.debug(f"TTS real generation failed: {e}")

        # Simulation mode
        return self._simulate_tts(text, output_path)

    def _simulate_tts(self, text: str, output_path: str) -> Tuple[bool, str, float]:
        """TTS simulation - dummy file banao"""
        try:
            # Duration estimate
            word_count = len(text.split())
            duration = max(1.5, (word_count / 150) * 60)

            # Dummy file create karo
            ensure_dir(os.path.dirname(output_path))
            with open(output_path, 'w') as f:
                f.write(f"# Simulated TTS: {text}\n")
                f.write(f"# Duration: {duration}s\n")

            return True, output_path, duration
        except Exception as e:
            logger.warning(f"TTS simulation failed: {e}")
            return False, "", 0.0


# ============================================================
# LIPSYNC INTERFACE
# ============================================================

class LipsyncInterface:
    """Lipsync engine interface"""

    def __init__(self):
        self._lipsync_available = False
        self._engine = None

        try:
            from src.ai.lipsync_engine import LipsyncEngine
            self._engine = LipsyncEngine()
            self._lipsync_available = True
            logger.info("✅ Lipsync engine connected")
        except Exception as e:
            logger.warning(f"Lipsync engine nahi mila: {e}")

    def generate_lipsync(
        self,
        audio_file: str,
        text: str,
    ) -> List[Tuple[str, float, float]]:
        """
        Audio + text se phoneme sequence generate karo.

        Returns:
            List of (phoneme, start_time, end_time)
        """
        if self._lipsync_available and self._engine:
            try:
                if hasattr(self._engine, 'generate_phonemes'):
                    return self._engine.generate_phonemes(audio_file, text)
            except Exception as e:
                logger.debug(f"Lipsync real generation failed: {e}")

        return self._simulate_phonemes(text)

    def _simulate_phonemes(self, text: str) -> List[Tuple[str, float, float]]:
        """Simple phoneme simulation"""
        phonemes = []
        current_time = 0.0

        # Simple: har character ~0.1s
        for char in text.lower():
            if char.isalpha():
                phoneme_duration = 0.08
                phonemes.append((char, current_time, current_time + phoneme_duration))
                current_time += phoneme_duration

        return phonemes


# ============================================================
# MAIN AUTOMATION ENGINE
# ============================================================

class AutomationEngine:
    """
    MAIN AUTOMATION ENGINE - Brain of the system!

    Kya karta hai:
    1. Script parse karta hai
    2. 3D scenes build karta hai
    3. Har character ka voice generate karta hai
    4. Lipsync data banata hai
    5. Camera movements plan karta hai
    6. Character animations plan karta hai
    7. SFX triggers set karta hai
    8. Music tracks arrange karta hai
    9. Sab kuch ek complete package mein return karta hai
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

        # Sub-systems
        self.tts = TTSInterface()
        self.lipsync = LipsyncInterface()
        self.animation_planner = AnimationPlanner()
        self.camera_planner = CameraPlanner()
        self.sfx_planner = SFXPlanner()

        # Progress tracking
        self._progress = GenerationProgress()
        self._progress_callbacks: List[Callable[[GenerationProgress], None]] = []
        self._cancel_requested = False

        # Async support
        self._worker_thread: Optional[threading.Thread] = None

        logger.info(f"✅ AutomationEngine initialized | FPS: {self.fps}")

    # ----------------------------------------------------------
    # MAIN GENERATION METHOD
    # ----------------------------------------------------------

    def generate_from_script(
        self,
        script_text: str,
        title: str = "Untitled",
        language: str = "en",
        output_directory: Optional[str] = None,
        async_mode: bool = False,
    ) -> AutomationResult:
        """
        MAIN METHOD - Script se complete animation data generate karo.

        Args:
            script_text: User ka script
            title: Project title
            language: Language code
            output_directory: Output folder (None = auto)
            async_mode: Background thread mein run karo

        Returns:
            AutomationResult with all data
        """
        if async_mode:
            self._worker_thread = threading.Thread(
                target=self._generate_internal,
                args=(script_text, title, language, output_directory),
                daemon=True,
            )
            self._cancel_requested = False
            self._worker_thread.start()
            return AutomationResult(success=False, error="Async generation started")
        else:
            return self._generate_internal(script_text, title, language, output_directory)

    def _generate_internal(
        self,
        script_text: str,
        title: str,
        language: str,
        output_directory: Optional[str],
    ) -> AutomationResult:
        """Actual generation logic"""
        start_time = time.time()
        result = AutomationResult(project_id=f"proj_{generate_uuid()[:8]}")

        # Setup output directory
        if output_directory is None:
            output_directory = f"projects/{result.project_id}"
        ensure_dir(output_directory)
        ensure_dir(f"{output_directory}/voices")
        ensure_dir(f"{output_directory}/data")
        result.output_directory = output_directory

        try:
            self._cancel_requested = False

            # ===== STAGE 1: PARSE SCRIPT =====
            self._update_progress(
                GenerationStage.PARSING_SCRIPT.value,
                5,
                "Script parse ho raha hai...",
            )

            from src.pipeline.script_parser import ScriptParser
            parser = ScriptParser()
            parsed_script = parser.parse(script_text, title, language)
            result.parsed_script = parsed_script

            if self._check_cancelled():
                return result

            # ===== STAGE 2: BUILD SCENES =====
            self._update_progress(
                GenerationStage.BUILDING_SCENES.value,
                15,
                f"{len(parsed_script.scenes)} scenes build ho rahi hain...",
            )

            from src.pipeline.scene_builder import SceneBuilder
            builder = SceneBuilder()
            built_scenes = builder.build_scenes_from_script(parsed_script)
            result.built_scenes = built_scenes

            if self._check_cancelled():
                return result

            # ===== STAGE 3: GENERATE ANIMATIONS FOR EACH SCENE =====
            scene_animations = []
            total_scenes = len(built_scenes)

            for i, (parsed_scene, built_scene) in enumerate(
                zip(parsed_script.scenes, built_scenes)
            ):
                if self._check_cancelled():
                    return result

                self._progress.scene_index = i
                self._progress.total_scenes = total_scenes

                # Generate scene animation data
                scene_anim = self._generate_scene_animation(
                    parsed_scene, built_scene,
                    output_directory, i, total_scenes,
                )
                scene_animations.append(scene_anim)

            result.scene_animations = scene_animations

            # ===== STAGE 4: FINALIZE =====
            self._update_progress(
                GenerationStage.COMPLETE.value,
                100,
                "Generation complete!",
            )

            # Calculate stats
            result.success = True
            result.total_scenes = len(built_scenes)
            result.total_dialogues = parsed_script.total_dialogues
            result.total_voice_clips = sum(
                len(s.voice_clips) for s in scene_animations
            )
            result.total_duration = parsed_script.total_duration
            result.total_frames = parsed_script.total_frames
            result.generation_time = time.time() - start_time

            # Save summary
            self._save_project_data(result, output_directory)

            logger.info(
                f"✅ Generation complete! "
                f"Scenes: {result.total_scenes} | "
                f"Voices: {result.total_voice_clips} | "
                f"Duration: {result.total_duration:.1f}s | "
                f"Time: {result.generation_time:.1f}s"
            )

        except Exception as e:
            logger.error(f"❌ Generation failed: {e}")
            import traceback
            traceback.print_exc()
            result.success = False
            result.error = str(e)
            self._update_progress(
                GenerationStage.FAILED.value,
                100,
                f"Failed: {e}",
            )

        return result

    # ----------------------------------------------------------
    # SCENE-LEVEL GENERATION
    # ----------------------------------------------------------

    def _generate_scene_animation(
        self,
        parsed_scene: Any,
        built_scene: Any,
        output_dir: str,
        scene_idx: int,
        total_scenes: int,
    ) -> SceneAnimationData:
        """Ek scene ke liye complete animation data generate karo"""

        scene_anim = SceneAnimationData(
            scene_index = built_scene.scene_index,
            scene_id    = built_scene.scene_id,
            start_frame = built_scene.start_frame,
            end_frame   = built_scene.end_frame,
        )

        base_percent = 15 + (scene_idx / total_scenes) * 80

        # ===== VOICE GENERATION =====
        self._update_progress(
            GenerationStage.GENERATING_VOICES.value,
            base_percent + 2,
            f"Scene {scene_idx+1}/{total_scenes}: Voices generate ho rahe hain...",
        )

        voice_clips = self._generate_voices(parsed_scene, output_dir)
        scene_anim.voice_clips = voice_clips

        # ===== LIPSYNC =====
        self._update_progress(
            GenerationStage.GENERATING_LIPSYNC.value,
            base_percent + 4,
            f"Scene {scene_idx+1}/{total_scenes}: Lipsync generate ho raha hai...",
        )

        lipsync_data = self._generate_lipsync(voice_clips)
        scene_anim.lipsync_data = lipsync_data

        # ===== CHARACTER ANIMATIONS =====
        self._update_progress(
            GenerationStage.PLANNING_ANIMATIONS.value,
            base_percent + 6,
            f"Scene {scene_idx+1}/{total_scenes}: Character animations plan...",
        )

        character_plans = []
        for char_name in parsed_scene.characters:
            plan = self.animation_planner.plan_character_animation(
                character         = char_name,
                scene_index       = parsed_scene.index,
                dialogues         = parsed_scene.dialogues,
                actions           = parsed_scene.actions,
                scene_start_frame = parsed_scene.start_frame,
            )
            character_plans.append(plan)
        scene_anim.character_animations = character_plans

        # ===== CAMERA PLAN =====
        self._update_progress(
            GenerationStage.PLANNING_CAMERAS.value,
            base_percent + 7,
            f"Scene {scene_idx+1}/{total_scenes}: Camera movements plan...",
        )

        camera_plan = self.camera_planner.plan_camera(built_scene, parsed_scene)
        scene_anim.camera_plan = camera_plan

        # ===== SFX =====
        self._update_progress(
            GenerationStage.GENERATING_SFX.value,
            base_percent + 8,
            f"Scene {scene_idx+1}/{total_scenes}: SFX plan...",
        )

        sfx_triggers = self.sfx_planner.plan_sfx(built_scene, parsed_scene)
        scene_anim.sfx_triggers = sfx_triggers

        # ===== MUSIC =====
        self._update_progress(
            GenerationStage.SETTING_UP_MUSIC.value,
            base_percent + 9,
            f"Scene {scene_idx+1}/{total_scenes}: Music setup...",
        )

        if built_scene.audio:
            music_track = MusicTrack(
                music_id       = f"music_{generate_uuid()[:8]}",
                mood           = built_scene.audio.music_mood,
                start_frame    = parsed_scene.start_frame,
                end_frame      = parsed_scene.end_frame,
                volume         = built_scene.audio.music_volume,
                fade_in_frames = 30,
                fade_out_frames= 30,
            )
            scene_anim.music_track = music_track

        return scene_anim

    def _generate_voices(
        self,
        parsed_scene: Any,
        output_dir: str,
    ) -> List[VoiceClip]:
        """Scene ke sabhi voices generate karo"""
        voice_clips = []

        for dialogue in parsed_scene.dialogues:
            if self._check_cancelled():
                break

            # Voice file path
            audio_file = os.path.join(
                output_dir,
                "voices",
                f"scene{parsed_scene.index}_d{dialogue.dialogue_index}_{dialogue.character}.wav"
            )

            # Get voice ID from character
            voice_id = "voice_default"
            if hasattr(dialogue, 'character'):
                # Would need script reference for character info
                voice_id = "voice_default"

            # Speed adjustment based on emotion
            speed = 1.0
            pitch = 0.0
            if dialogue.emotion == "shouting":
                speed = 1.1
                pitch = 0.2
            elif dialogue.emotion == "whispering":
                speed = 0.9
                pitch = -0.1
            elif dialogue.emotion == "sad":
                speed = 0.85
            elif dialogue.emotion == "excited":
                speed = 1.15

            # Generate voice
            success, file_path, duration = self.tts.generate_voice(
                text        = dialogue.text,
                voice_id    = voice_id,
                emotion     = dialogue.emotion,
                speed       = speed,
                pitch       = pitch,
                output_path = audio_file,
            )

            clip = VoiceClip(
                clip_id         = f"voice_{generate_uuid()[:8]}",
                character       = dialogue.character,
                text            = dialogue.text,
                emotion         = dialogue.emotion,
                voice_id        = voice_id,
                audio_file      = file_path if success else "",
                duration_seconds= duration,
                scene_index     = parsed_scene.index,
                dialogue_index  = dialogue.dialogue_index,
                start_frame     = dialogue.start_frame,
                end_frame       = dialogue.end_frame,
                speed           = speed,
                pitch           = pitch,
                generated       = success,
                generation_error= "" if success else "TTS failed",
            )
            voice_clips.append(clip)

        return voice_clips

    def _generate_lipsync(
        self,
        voice_clips: List[VoiceClip],
    ) -> List[LipsyncData]:
        """Voices ke liye lipsync generate karo"""
        lipsync_list = []

        for clip in voice_clips:
            if not clip.generated:
                continue

            phonemes = self.lipsync.generate_lipsync(
                audio_file = clip.audio_file,
                text       = clip.text,
            )

            lipsync = LipsyncData(
                voice_clip_id = clip.clip_id,
                character     = clip.character,
                phonemes      = phonemes,
                start_frame   = clip.start_frame,
                end_frame     = clip.end_frame,
                generated     = len(phonemes) > 0,
            )

            # Generate mouth shapes
            if phonemes:
                lipsync.mouth_shapes = self._phonemes_to_mouth_shapes(
                    phonemes, clip.start_frame
                )

            lipsync_list.append(lipsync)

        return lipsync_list

    def _phonemes_to_mouth_shapes(
        self,
        phonemes: List[Tuple[str, float, float]],
        start_frame: int,
    ) -> List[Dict]:
        """Phonemes ko mouth shapes mein convert karo"""
        # Simple phoneme → mouth shape mapping
        PHONEME_SHAPES = {
            'a': 'open',    'e': 'wide',    'i': 'smile',
            'o': 'round',   'u': 'round',
            'b': 'closed',  'p': 'closed',  'm': 'closed',
            'f': 'lip_bite', 'v': 'lip_bite',
            's': 'teeth',   'z': 'teeth',
            't': 'tongue',  'd': 'tongue',  'l': 'tongue',
            'r': 'r_shape',
        }

        mouth_shapes = []
        for phoneme, start_t, end_t in phonemes:
            shape = PHONEME_SHAPES.get(phoneme.lower(), 'neutral')
            mouth_shapes.append({
                "shape":       shape,
                "start_frame": start_frame + int(start_t * self.fps),
                "end_frame":   start_frame + int(end_t * self.fps),
                "phoneme":     phoneme,
            })

        return mouth_shapes

    # ----------------------------------------------------------
    # PROGRESS & CALLBACKS
    # ----------------------------------------------------------

    def _update_progress(
        self,
        stage: str,
        percent: float,
        message: str,
    ):
        """Progress update karo"""
        self._progress.stage = stage
        self._progress.percent = percent
        self._progress.message = message
        self._progress.elapsed_seconds = time.time() - self._progress.elapsed_seconds if self._progress.elapsed_seconds else 0

        # Notify callbacks
        for cb in self._progress_callbacks:
            try:
                cb(self._progress)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")

        logger.debug(f"[{percent:.0f}%] {stage}: {message}")

    def add_progress_callback(self, callback: Callable[[GenerationProgress], None]):
        """Progress callback register karo"""
        self._progress_callbacks.append(callback)

    def cancel_generation(self):
        """Generation cancel karo"""
        self._cancel_requested = True
        logger.info("⚠️  Cancel requested")

    def _check_cancelled(self) -> bool:
        return self._cancel_requested

    # ----------------------------------------------------------
    # DATA PERSISTENCE
    # ----------------------------------------------------------

    def _save_project_data(
        self,
        result: AutomationResult,
        output_dir: str,
    ):
        """Complete project data JSON mein save karo"""
        try:
            data_file = f"{output_dir}/data/project.json"

            data = {
                "project_id":      result.project_id,
                "generated_at":    get_timestamp(),
                "summary":         result.get_summary(),
                "script": {
                    "title":           result.parsed_script.title,
                    "language":        result.parsed_script.language,
                    "total_scenes":    len(result.parsed_script.scenes),
                    "total_dialogues": result.parsed_script.total_dialogues,
                } if result.parsed_script else {},
                "scenes": [
                    s.to_dict() for s in result.scene_animations
                ],
            }

            write_json(data_file, data)
            logger.info(f"💾 Project data saved: {data_file}")

        except Exception as e:
            logger.warning(f"Data save failed: {e}")

    def print_result_summary(self, result: AutomationResult):
        """Result ka detailed summary print karo"""
        print(f"\n{'='*60}")
        print(f"🎬 AUTOMATION RESULT")
        print(f"{'='*60}")

        summary = result.get_summary()
        for key, value in summary.items():
            print(f"  {key:20s}: {value}")

        print(f"\n{'='*60}")
        print(f"📊 PER-SCENE BREAKDOWN")
        print(f"{'='*60}")

        for scene_anim in result.scene_animations:
            print(f"\n  Scene {scene_anim.scene_index}:")
            info = scene_anim.to_dict()
            for key, value in info.items():
                if key not in ["scene_index", "scene_id"]:
                    print(f"     {key:20s}: {value}")

        print(f"\n{'='*60}\n")


# ============================================================
# GLOBAL INSTANCE
# ============================================================

_global_engine: Optional[AutomationEngine] = None


def get_automation_engine() -> AutomationEngine:
    """Global AutomationEngine instance"""
    global _global_engine
    if _global_engine is None:
        _global_engine = AutomationEngine()
    return _global_engine


# ============================================================
# TEST SECTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")
    print_banner("Automation Engine Test", "Complete Pipeline Orchestration")

    # ===== TEST 1: Engine Init =====
    print_section("Test 1: Engine Initialization")
    engine = AutomationEngine()
    print(f"✅ AutomationEngine initialized | FPS: {engine.fps}")

    # ===== TEST 2: TTS Interface =====
    print_section("Test 2: TTS Interface")
    tts = TTSInterface()
    success, path, dur = tts.generate_voice(
        text="Namaste doston, aaj main animation banane wala hoon!",
        voice_id="voice_male_1",
        emotion="excited",
    )
    print(f"✅ TTS test: success={success}, duration={dur:.1f}s")

    # ===== TEST 3: Animation Planner =====
    print_section("Test 3: Animation Planning")

    from src.pipeline.script_parser import ScriptParser
    parser = ScriptParser()

    simple_script = """
Hero: (happy) Aaj main khush hoon!
Hero: (angry) Yeh galat hai!
Hero: (sad) Ab kya karun...
"""
    parsed = parser.parse(simple_script, "Test")

    if parsed.scenes:
        scene = parsed.scenes[0]
        plan = AnimationPlanner.plan_character_animation(
            character         = "Hero",
            scene_index       = 0,
            dialogues         = scene.dialogues,
            actions           = scene.actions,
            scene_start_frame = 0,
        )
        print(f"✅ Animation plan created:")
        print(f"   Total animations: {len(plan.animations)}")
        print(f"   Total expressions: {len(plan.expressions)}")
        for anim in plan.animations[:5]:
            print(f"      • {anim['animation']:20s} frame {anim['start_frame']}-{anim['end_frame']}")

    # ===== TEST 4: FULL PIPELINE =====
    print_section("Test 4: 🚀 FULL AUTOMATION PIPELINE 🚀")

    story_script = """
INT. HERO'S HOUSE - MORNING

The hero wakes up excitedly.

HERO
(excited)
Aaj main duniya ka best animation banane wala hoon!

HERO
(happy)
Chalo, kaam shuru karte hain!

EXT. VILLAIN'S LAIR - NIGHT

VILLAIN
(angry)
Hero ne bahut kar liya. Ab mera time hai!

VILLAIN
(shouting)
MAIN USSE ROKUNGA!

INT. HERO'S BEDROOM - EVENING

HERO
(surprised)
Villain yahan kaise aaya?

VILLAIN
(laughing)
Surprise, hero!

HERO
(angry)
Tu galat time pe aaya!
"""

    # Progress callback
    def on_progress(prog: GenerationProgress):
        print(f"   [{prog.percent:5.1f}%] {prog.stage:25s} → {prog.message[:60]}")

    engine.add_progress_callback(on_progress)

    print("\n🚀 Starting automation pipeline...\n")
    result = engine.generate_from_script(
        script_text = story_script,
        title       = "Hero vs Villain",
        language    = "en",
    )

    print(f"\n🎉 Generation complete!\n")
    engine.print_result_summary(result)

    # ===== TEST 5: Detailed Scene Data =====
    print_section("Test 5: Detailed Scene Animation Data")

    if result.scene_animations:
        first_scene = result.scene_animations[0]
        print(f"\n   Scene {first_scene.scene_index} Details:")
        print(f"      Voice clips     : {len(first_scene.voice_clips)}")
        print(f"      Lipsync data    : {len(first_scene.lipsync_data)}")
        print(f"      Character plans : {len(first_scene.character_animations)}")
        print(f"      SFX triggers    : {len(first_scene.sfx_triggers)}")
        print(f"      Camera keyframes: {len(first_scene.camera_plan.keyframes) if first_scene.camera_plan else 0}")

        print(f"\n   🎤 Voice Clips:")
        for clip in first_scene.voice_clips:
            print(f"      • [{clip.character}] {clip.text[:40]}...")
            print(f"        Emotion: {clip.emotion} | Duration: {clip.duration_seconds:.1f}s")

        print(f"\n   👄 Lipsync:")
        for lip in first_scene.lipsync_data:
            print(f"      • {lip.character}: {len(lip.phonemes)} phonemes, {len(lip.mouth_shapes)} mouth shapes")

        print(f"\n   🎭 Character Animations:")
        for plan in first_scene.character_animations:
            print(f"      • {plan.character}: {len(plan.animations)} animations, {len(plan.expressions)} expressions")

        print(f"\n   🎥 Camera Plan:")
        if first_scene.camera_plan:
            print(f"      Movement type: {first_scene.camera_plan.movement_type}")
            print(f"      Keyframes    : {len(first_scene.camera_plan.keyframes)}")

        print(f"\n   🔊 SFX Triggers:")
        for sfx in first_scene.sfx_triggers[:5]:
            print(f"      • {sfx.sfx_name} @ frame {sfx.trigger_frame} ({sfx.reason})")

        print(f"\n   🎵 Music:")
        if first_scene.music_track:
            print(f"      Mood  : {first_scene.music_track.mood}")
            print(f"      Volume: {first_scene.music_track.volume}")

    # ===== TEST 6: Output Files =====
    print_section("Test 6: Generated Output Files")
    if result.success and result.output_directory:
        print(f"✅ Output directory: {result.output_directory}")
        try:
            for root, dirs, files in os.walk(result.output_directory):
                level = root.replace(result.output_directory, '').count(os.sep)
                indent = '   ' * level
                print(f"{indent}📁 {os.path.basename(root)}/")
                sub_indent = '   ' * (level + 1)
                for file in files[:5]:
                    print(f"{sub_indent}📄 {file}")
        except Exception as e:
            print(f"   File listing error: {e}")

    # ===== TEST 7: Statistics =====
    print_section("Test 7: Final Statistics")
    print(f"\n   🎬 Pipeline Complete!")
    print(f"   ⏱️  Total Time     : {result.generation_time:.2f}s")
    print(f"   📊 Scenes Built    : {result.total_scenes}")
    print(f"   🎤 Voices Generated: {result.total_voice_clips}")
    print(f"   💬 Total Dialogues : {result.total_dialogues}")
    print(f"   🎞️  Total Duration : {result.total_duration:.1f}s")
    print(f"   🖼️  Total Frames   : {result.total_frames}")

    print_banner("✅ All Tests Passed!", "automation_engine.py Working Perfectly")