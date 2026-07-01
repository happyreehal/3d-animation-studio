# ============================================================
# src/pipeline/__init__.py
# 3D Animation Studio - Pipeline Package
# Complete Script-to-Video Automation Pipeline
# ============================================================

# Script Parser
from src.pipeline.script_parser import (
    ScriptParser,
    ParsedScript,
    ParsedScene,
    ParsedDialogue,
    ParsedAction,
    Character,
    Emotion,
    SceneType,
    TimeOfDay,
    CameraAngle,
    EmotionDetector,
    SceneDetector,
    CharacterDetector,
    get_script_parser,
)

# Scene Builder
from src.pipeline.scene_builder import (
    SceneBuilder,
    BuiltScene,
    SceneCharacter,
    SceneLight,
    SceneCamera,
    SceneEnvironment,
    SceneAudio,
    CharacterPosition,
    LayoutType,
    CharacterPositioner,
    LightingBuilder,
    CameraBuilder,
    EnvironmentBuilder,
    AudioBuilder,
    VFXBuilder,
    get_scene_builder,
)

# Automation Engine
from src.pipeline.automation_engine import (
    AutomationEngine,
    AutomationResult,
    GenerationProgress,
    GenerationStage,
    SceneAnimationData,
    VoiceClip,
    LipsyncData,
    ExpressionKeyframe,
    CharacterAnimationPlan,
    CameraKeyframe,
    CameraPlan,
    SFXTrigger,
    MusicTrack,
    AnimationType,
    AnimationPlanner,
    CameraPlanner,
    SFXPlanner,
    TTSInterface,
    LipsyncInterface,
    get_automation_engine,
)

# Video Generator
from src.pipeline.video_generator import (
    VideoGenerator,
    VideoSettings,
    GeneratedVideo,
    RenderProgress,
    RenderStage,
    VideoQuality,
    OutputFormat,
    FFmpegWrapper,
    FrameRenderer,
    SubtitleGenerator,
    VideoMetadata,
    get_video_generator,
    script_to_video,  # 🚀 ONE-CLICK MAGIC FUNCTION
)


__all__ = [
    # Script Parser
    "ScriptParser", "ParsedScript", "ParsedScene",
    "ParsedDialogue", "ParsedAction", "Character",
    "Emotion", "SceneType", "TimeOfDay", "CameraAngle",
    "EmotionDetector", "SceneDetector", "CharacterDetector",
    "get_script_parser",

    # Scene Builder
    "SceneBuilder", "BuiltScene", "SceneCharacter",
    "SceneLight", "SceneCamera", "SceneEnvironment",
    "SceneAudio", "CharacterPosition", "LayoutType",
    "CharacterPositioner", "LightingBuilder",
    "CameraBuilder", "EnvironmentBuilder", "AudioBuilder",
    "VFXBuilder", "get_scene_builder",

    # Automation Engine
    "AutomationEngine", "AutomationResult",
    "GenerationProgress", "GenerationStage",
    "SceneAnimationData", "VoiceClip", "LipsyncData",
    "ExpressionKeyframe", "CharacterAnimationPlan",
    "CameraKeyframe", "CameraPlan", "SFXTrigger",
    "MusicTrack", "AnimationType", "AnimationPlanner",
    "CameraPlanner", "SFXPlanner",
    "TTSInterface", "LipsyncInterface",
    "get_automation_engine",

    # Video Generator
    "VideoGenerator", "VideoSettings", "GeneratedVideo",
    "RenderProgress", "RenderStage", "VideoQuality",
    "OutputFormat", "FFmpegWrapper", "FrameRenderer",
    "SubtitleGenerator", "VideoMetadata",
    "get_video_generator", "script_to_video",
]