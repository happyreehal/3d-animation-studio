# ============================================================
# 3D ANIMATION STUDIO - Audio Module
# ============================================================
# Complete audio system for content creation:
#
#   🎵 Audio Engine       - Multi-track playback, mixing, effects
#   🎙️ Audio Recorder     - Live microphone recording with VU meter
#   🔊 Sound Effects      - SFX synthesis, effects processing, voice mods
#
# Clean import pattern:
#   from src.audio import AudioEngine, AudioRecorder, SoundEffectsEngine
# ============================================================

# ===== PATH SETUP (must be at TOP, before any src.* imports) =====
# Standalone run ke liye zaroori - `python src/audio/__init__.py`
import sys
import os
if __name__ == "__main__":
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.dirname(os.path.dirname(_current_dir))
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
# =================================================================

# ------------------------------------------------------------
# AUDIO ENGINE - Playback, Mixing, Effects
# ------------------------------------------------------------
from src.audio.audio_engine import (
    # Main class
    AudioEngine,

    # Sub-systems
    AudioPlayer,
    AudioAnalyzer,
    AudioEffects,

    # Data classes
    AudioInfo,
    AudioTrack,

    # Enums / Constants
    AudioFormat,
    TrackState,
)

# ------------------------------------------------------------
# AUDIO RECORDER - Microphone Recording
# ------------------------------------------------------------
from src.audio.audio_recorder import (
    # Main class
    AudioRecorder,

    # Sub-systems
    DeviceManager,
    LevelDetector,
    SilenceMonitor,

    # Data classes
    InputDevice,
    RecordingMetadata,
    LevelMeter,

    # Context manager
    RecordingSession,

    # Enums
    RecordingState,
    AudioQuality,
)

# ------------------------------------------------------------
# SOUND EFFECTS - SFX Generation & Audio Processing
# ------------------------------------------------------------
from src.audio.sound_effects import (
    # Main class
    SoundEffectsEngine,

    # Sub-systems
    SFXSynthesizer,
    AudioEffectsProcessor,
    VoiceEffectsProcessor,
    SFXLibrary,
    EffectChain,

    # Data classes
    SFXPreset,
    EffectResult,

    # Enums
    SFXCategory,
    EffectType,
    ReverbPreset,
    VoiceEffect,
)


# ============================================================
# PUBLIC API - Explicit exports
# ============================================================
# Ye list define karti hai ki `from src.audio import *` pe kya milega
# Aur IDE autocomplete ko bhi help karti hai.

__all__ = [
    # ── Audio Engine ──────────────────────────────────────
    "AudioEngine",
    "AudioPlayer",
    "AudioAnalyzer",
    "AudioEffects",
    "AudioInfo",
    "AudioTrack",
    "AudioFormat",
    "TrackState",

    # ── Audio Recorder ────────────────────────────────────
    "AudioRecorder",
    "DeviceManager",
    "LevelDetector",
    "SilenceMonitor",
    "InputDevice",
    "RecordingMetadata",
    "LevelMeter",
    "RecordingSession",
    "RecordingState",
    "AudioQuality",

    # ── Sound Effects ─────────────────────────────────────
    "SoundEffectsEngine",
    "SFXSynthesizer",
    "AudioEffectsProcessor",
    "VoiceEffectsProcessor",
    "SFXLibrary",
    "EffectChain",
    "SFXPreset",
    "EffectResult",
    "SFXCategory",
    "EffectType",
    "ReverbPreset",
    "VoiceEffect",
]


# ============================================================
# MODULE METADATA
# ============================================================

__version__ = "1.0.0"
__author__ = "3D Animation Studio"
__description__ = "Complete audio system: playback, recording, SFX, effects"


# ============================================================
# TEST / VERIFICATION
# ============================================================
# File standalone bhi run kar sakte ho verify karne ke liye

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")

    print_banner(
        "🔊 Audio Module - Import Verification",
        f"v{__version__} | {len(__all__)} components loaded"
    )

    # ── Test 1: All Imports Work ──────────────────────────
    print_section("Test 1: Module Structure Check")

    modules_info = {
        "🎵 Audio Engine": [
            "AudioEngine", "AudioPlayer", "AudioAnalyzer", "AudioEffects",
            "AudioInfo", "AudioTrack", "AudioFormat", "TrackState",
        ],
        "🎙️ Audio Recorder": [
            "AudioRecorder", "DeviceManager", "LevelDetector", "SilenceMonitor",
            "InputDevice", "RecordingMetadata", "LevelMeter",
            "RecordingSession", "RecordingState", "AudioQuality",
        ],
        "🔊 Sound Effects": [
            "SoundEffectsEngine", "SFXSynthesizer", "AudioEffectsProcessor",
            "VoiceEffectsProcessor", "SFXLibrary", "EffectChain",
            "SFXPreset", "EffectResult", "SFXCategory", "EffectType",
            "ReverbPreset", "VoiceEffect",
        ],
    }

    total_ok = 0
    total_fail = 0

    for module_name, components in modules_info.items():
        print(f"\n  {module_name}:")
        for comp in components:
            # Check if component exists in namespace
            exists = comp in globals()
            status = "✅" if exists else "❌"
            print(f"    {status} {comp}")
            if exists:
                total_ok += 1
            else:
                total_fail += 1

    # ── Test 2: Key Enums / Constants ─────────────────────
    print_section("Test 2: Key Enums / Constants")

    print(f"  AudioFormat     : {AudioFormat.ALL}")
    print(f"  TrackState      : {[s.value for s in TrackState]}")
    print(f"  RecordingState  : {[s.value for s in RecordingState]}")
    print(f"  AudioQuality    : {[q.label for q in AudioQuality]}")
    print(f"  SFXCategory     : {len(list(SFXCategory))} categories")
    print(f"  EffectType      : {len(list(EffectType))} effect types")
    print(f"  ReverbPreset    : {[r.label for r in ReverbPreset]}")
    print(f"  VoiceEffect     : {[v.value for v in VoiceEffect]}")

    # ── Test 3: Instantiation Check ───────────────────────
    print_section("Test 3: Quick Instantiation Test")

    instantiation_ok = True

    try:
        # Audio Engine
        audio_engine = AudioEngine()
        backends_active = sum(
            1 for v in audio_engine.get_stats()["backends_available"].values() if v
        )
        print(f"  ✅ AudioEngine        : {backends_active}/4 backends active")

        # Audio Recorder
        recorder = AudioRecorder()
        devices = len(recorder.list_devices())
        print(f"  ✅ AudioRecorder      : {devices} input devices found")

        # Sound Effects Engine
        sfx_engine = SoundEffectsEngine()
        presets = len(sfx_engine.library.list_presets())
        print(f"  ✅ SoundEffectsEngine : {presets} SFX presets ready")

        # Cleanup
        audio_engine.shutdown()
        recorder.shutdown()

    except Exception as e:
        print(f"  ❌ Instantiation failed: {e}")
        import traceback
        traceback.print_exc()
        instantiation_ok = False

    # ── Test 4: Cross-Module Integration Test ─────────────
    print_section("Test 4: Cross-Module Integration")

    try:
        # SFX se audio generate karo, phir AudioEngine mein use karo
        print("  🔗 Testing SFX → AudioEngine integration...")

        sfx = SoundEffectsEngine()
        base_dir = os.path.dirname(os.path.dirname(_current_dir if __name__ == "__main__" else os.path.abspath(__file__)))
        temp_dir = os.path.join(base_dir, "temp", "audio_module_test")
        os.makedirs(temp_dir, exist_ok=True)

        # Ek SFX generate karke save karo
        test_sfx_path = os.path.join(temp_dir, "test_integration.wav")
        audio = sfx.generate_sfx("click", test_sfx_path)

        if audio and os.path.exists(test_sfx_path):
            print(f"     ✅ SFX generated: {os.path.basename(test_sfx_path)}")

            # AudioEngine mein load karo
            engine = AudioEngine()
            track = engine.load_track(test_sfx_path, name="Integration Test")

            if track:
                print(f"     ✅ Loaded into AudioEngine: {track.name}")
                print(f"     ✅ Track duration: {track._duration:.3f}s")

                # Cleanup
                engine.shutdown()
            else:
                print(f"     ⚠️  Track load failed")
        else:
            print(f"     ⚠️  SFX generation failed")

    except Exception as e:
        print(f"  ⚠️  Integration test issue: {e}")

    # ── Test 5: Audio + AI Integration (Optional) ─────────
    print_section("Test 5: Audio + AI Integration Check")

    try:
        # Check if TTS output can be used with audio module
        from src.ai import TTSEngine

        print("  🔗 Audio + AI modules can be imported together")
        print("     ✅ from src.ai import TTSEngine")
        print("     ✅ from src.audio import AudioEngine")
        print("\n  💡 Example workflow:")
        print("     tts = TTSEngine()")
        print("     result = tts.synthesize('Hello!', voice)")
        print("     audio = AudioEngine()")
        print("     track = audio.load_track(result.audio_file)")

    except ImportError:
        print("  ⚠️  AI module not available (this is optional)")

    # ── Final Summary ─────────────────────────────────────
    print_section("Summary")

    print(f"  Components exported : {len(__all__)}")
    print(f"  Imports verified    : {total_ok}/{total_ok + total_fail}")
    print(f"  Instantiation       : {'✅ OK' if instantiation_ok else '❌ FAIL'}")

    if total_fail == 0 and instantiation_ok:
        print_banner(
            "✅ Audio Module Ready!",
            f"All {len(__all__)} components working | v{__version__}"
        )
    else:
        print_banner(
            "⚠️ Some Issues Found",
            f"Failed: {total_fail} components | Check imports"
        )