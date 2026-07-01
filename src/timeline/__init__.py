# ============================================================
# 3D ANIMATION STUDIO - Timeline Module
# ============================================================
# Complete timeline system for animation:
#
#   ⏱️  Timeline Editor    - Multi-track timeline with clips
#   🔑 Keyframe System    - Property animation with easings
#   🎬 Transitions        - Cinematic transitions between clips
#
# Clean import pattern:
#   from src.timeline import Timeline, KeyframeEngine, TransitionsEngine
# ============================================================

# ===== PATH SETUP (must be at TOP, before any src.* imports) =====
# Standalone run ke liye zaroori - `python src/timeline/__init__.py`
import sys
import os
if __name__ == "__main__":
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.dirname(os.path.dirname(_current_dir))
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
# =================================================================

# ------------------------------------------------------------
# TIMELINE EDITOR - Multi-track Timeline
# ------------------------------------------------------------
from src.timeline.timeline_editor import (
    # Main class
    Timeline,

    # Data classes
    Track,
    Clip,
    TimeMarker,

    # Sub-systems
    SnapManager,
    UndoRedoManager,

    # Commands (undo/redo)
    TimelineCommand,
    AddClipCommand,
    RemoveClipCommand,
    MoveClipCommand,

    # Enums
    TrackType,
    ClipType,
    PlaybackState,
    SnapMode,
    RippleMode,
)

# ------------------------------------------------------------
# KEYFRAME SYSTEM - Property Animation
# ------------------------------------------------------------
from src.timeline.keyframe_system import (
    # Main class
    KeyframeEngine,

    # Data classes
    Keyframe,
    KeyframeTrack,
    AnimationGroup,

    # Interpolation
    BezierCurve,
    Easing,
    ValueInterpolator,
    evaluate_easing,

    # Presets
    KeyframePresets,

    # Enums
    InterpolationType,
    PropertyType,
)

# ------------------------------------------------------------
# TRANSITIONS - Cinematic Transitions
# ------------------------------------------------------------
from src.timeline.transitions import (
    # Main class
    TransitionsEngine,

    # Data classes
    TransitionConfig,
    TransitionInstance,
    TransitionFrame,

    # Sub-systems
    TransitionCalculator,

    # Presets
    TransitionPresets,

    # Enums
    TransitionType,
    TransitionCategory,
    TransitionDirection,
)


# ============================================================
# PUBLIC API - Explicit exports
# ============================================================
# Ye list define karti hai ki `from src.timeline import *` pe kya milega

__all__ = [
    # ── Timeline Editor ───────────────────────────────────
    "Timeline",
    "Track",
    "Clip",
    "TimeMarker",
    "SnapManager",
    "UndoRedoManager",
    "TimelineCommand",
    "AddClipCommand",
    "RemoveClipCommand",
    "MoveClipCommand",
    "TrackType",
    "ClipType",
    "PlaybackState",
    "SnapMode",
    "RippleMode",

    # ── Keyframe System ───────────────────────────────────
    "KeyframeEngine",
    "Keyframe",
    "KeyframeTrack",
    "AnimationGroup",
    "BezierCurve",
    "Easing",
    "ValueInterpolator",
    "evaluate_easing",
    "KeyframePresets",
    "InterpolationType",
    "PropertyType",

    # ── Transitions ───────────────────────────────────────
    "TransitionsEngine",
    "TransitionConfig",
    "TransitionInstance",
    "TransitionFrame",
    "TransitionCalculator",
    "TransitionPresets",
    "TransitionType",
    "TransitionCategory",
    "TransitionDirection",
]


# ============================================================
# MODULE METADATA
# ============================================================

__version__ = "1.0.0"
__author__ = "3D Animation Studio"
__description__ = "Complete timeline system: multi-track editor, keyframes, transitions"


# ============================================================
# TEST / VERIFICATION
# ============================================================
# File standalone bhi run kar sakte ho verify karne ke liye

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")

    print_banner(
        "⏱️ Timeline Module - Import Verification",
        f"v{__version__} | {len(__all__)} components loaded"
    )

    # ── Test 1: All Imports Work ──────────────────────────
    print_section("Test 1: Module Structure Check")

    modules_info = {
        "⏱️ Timeline Editor": [
            "Timeline", "Track", "Clip", "TimeMarker",
            "SnapManager", "UndoRedoManager",
            "TimelineCommand", "AddClipCommand", "RemoveClipCommand", "MoveClipCommand",
            "TrackType", "ClipType", "PlaybackState", "SnapMode", "RippleMode",
        ],
        "🔑 Keyframe System": [
            "KeyframeEngine", "Keyframe", "KeyframeTrack", "AnimationGroup",
            "BezierCurve", "Easing", "ValueInterpolator", "evaluate_easing",
            "KeyframePresets", "InterpolationType", "PropertyType",
        ],
        "🎬 Transitions": [
            "TransitionsEngine", "TransitionConfig", "TransitionInstance",
            "TransitionFrame", "TransitionCalculator", "TransitionPresets",
            "TransitionType", "TransitionCategory", "TransitionDirection",
        ],
    }

    total_ok   = 0
    total_fail = 0

    for module_name, components in modules_info.items():
        print(f"\n  {module_name}:")
        for comp in components:
            exists = comp in globals()
            status = "✅" if exists else "❌"
            print(f"    {status} {comp}")
            if exists:
                total_ok += 1
            else:
                total_fail += 1

    # ── Test 2: Key Enums / Constants ─────────────────────
    print_section("Test 2: Key Enums / Constants")

    print(f"  TrackType         : {[t.value for t in TrackType]}")
    print(f"  ClipType          : {len(list(ClipType))} types")
    print(f"  PlaybackState     : {[s.value for s in PlaybackState]}")
    print(f"  SnapMode          : {[s.value for s in SnapMode]}")
    print(f"  RippleMode        : {[r.value for r in RippleMode]}")
    print(f"  InterpolationType : {len(list(InterpolationType))} types")
    print(f"  PropertyType      : {[p.value for p in PropertyType]}")
    print(f"  TransitionType    : {len(list(TransitionType))} types")
    print(f"  TransitionCategory: {[c.value for c in TransitionCategory]}")

    # ── Test 3: Quick Instantiation ───────────────────────
    print_section("Test 3: Quick Instantiation Test")

    instantiation_ok = True

    try:
        # Timeline
        timeline = Timeline(name="Test Timeline", fps=30)
        print(f"  ✅ Timeline           : '{timeline.name}' @ {timeline.fps}fps")

        # Add a track
        video_track = timeline.add_track("Video", TrackType.VIDEO)
        print(f"  ✅ Track added        : {video_track.name}")

        # Keyframe Engine
        kf_engine = KeyframeEngine()
        print(f"  ✅ KeyframeEngine     : fps={kf_engine.fps}")

        # Add animation
        opacity_track = KeyframeTrack("opacity", PropertyType.FLOAT)
        opacity_track.add_keyframe(0.0, 0.0, InterpolationType.EASE_OUT_CUBIC)
        opacity_track.add_keyframe(1.0, 1.0)
        kf_engine.add_track(opacity_track)
        print(f"  ✅ KeyframeTrack      : {len(opacity_track.keyframes)} keyframes")

        # Transitions Engine
        tr_engine = TransitionsEngine()
        print(f"  ✅ TransitionsEngine  : {len(TransitionPresets.get_all())} presets")

    except Exception as e:
        print(f"  ❌ Instantiation failed: {e}")
        import traceback
        traceback.print_exc()
        instantiation_ok = False

    # ── Test 4: Cross-Module Integration ──────────────────
    print_section("Test 4: Cross-Module Integration (Full Workflow)")

    try:
        print("  🔗 Building complete animation workflow...\n")

        # 1. Create timeline
        anim_timeline = Timeline(name="Animation Test", fps=30)
        video_tr    = anim_timeline.add_track("Video",    TrackType.VIDEO)
        audio_tr    = anim_timeline.add_track("Audio",    TrackType.AUDIO)
        print("     ✅ Timeline with 2 tracks created")

        # 2. Add clips
        clip1 = Clip(name="Scene 1", clip_type=ClipType.SCENE_3D,
                     start_time=0.0, duration=3.0)
        clip2 = Clip(name="Scene 2", clip_type=ClipType.SCENE_3D,
                     start_time=3.0, duration=3.0)
        anim_timeline.add_clip(video_tr.id, clip1)
        anim_timeline.add_clip(video_tr.id, clip2)
        print("     ✅ 2 clips added to video track")

        # 3. Add keyframe animation on clip1's position
        anim_engine = KeyframeEngine()
        char_group  = anim_engine.create_group("Character")
        pos_track   = char_group.add_track("position_x", PropertyType.FLOAT)
        pos_track.add_keyframe(0.0, -5.0, InterpolationType.EASE_IN_OUT_CUBIC)
        pos_track.add_keyframe(3.0, 5.0)
        print("     ✅ Keyframe animation added (character moves)")

        # 4. Add transition between clips
        tr_engine_workflow = TransitionsEngine()
        dissolve = TransitionPresets.smooth_dissolve(duration=0.5)
        tr_instance = tr_engine_workflow.create_transition(
            config    = dissolve,
            start_time= 2.75,   # Overlap with clip end
            clip_a_id = clip1.id,
            clip_b_id = clip2.id,
            track_id  = video_tr.id,
        )
        print("     ✅ Smooth dissolve transition added")

        # 5. Evaluate everything at time t=1.5s (middle of clip1)
        print("\n  🎯 Evaluate everything at t=1.5s:")

        # Get active clips
        active_clips = anim_timeline.get_clips_at_time(1.5)
        for track_id, clips in active_clips.items():
            track_obj = anim_timeline.get_track(track_id)
            for c in clips:
                print(f"     ▶️  Active clip [{track_obj.name}]: {c.name}")

        # Get animation values
        anim_values = anim_engine.evaluate_all(1.5)
        for group_name, props in anim_values.items():
            for prop, val in props.items():
                if isinstance(val, float):
                    print(f"     🎬 {group_name}.{prop} = {val:+.3f}")

        # Get transition frames
        tr_frames = tr_engine_workflow.evaluate_at_time(2.9)  # Mid transition
        for tf in tr_frames:
            print(f"     🎨 Transition '{tf.effect_type}': "
                  f"A={tf.clip_a_opacity:.2f} B={tf.clip_b_opacity:.2f}")

        print("\n     ✅ All 3 systems working together!")

    except Exception as e:
        print(f"  ⚠️  Integration issue: {e}")
        import traceback
        traceback.print_exc()

    # ── Test 5: Integration with Other Modules ────────────
    print_section("Test 5: Integration with Other Modules")

    try:
        from src.ai import TTSEngine
        from src.audio import AudioEngine
        from src.timeline import Timeline

        print("  🔗 All modules importable together:")
        print("     ✅ from src.ai import TTSEngine")
        print("     ✅ from src.audio import AudioEngine")
        print("     ✅ from src.timeline import Timeline, KeyframeEngine")
        print("     ✅ from src.timeline import TransitionsEngine")

        print("\n  💡 Full pipeline workflow:")
        print("     1. tts.synthesize('Hello!') → audio_file.wav")
        print("     2. audio.load_track(audio_file) → track")
        print("     3. clip = Clip(clip_type=ClipType.TTS, source_path=audio_file)")
        print("     4. timeline.add_clip(track_id, clip)")
        print("     5. kf_engine.add_keyframe(...) → property animation")
        print("     6. tr_engine.create_transition(...) → smooth cuts")

    except ImportError as e:
        print(f"  ⚠️  Some modules not available: {e}")

    # ── Final Summary ─────────────────────────────────────
    print_section("Summary")

    print(f"  Components exported : {len(__all__)}")
    print(f"  Imports verified    : {total_ok}/{total_ok + total_fail}")
    print(f"  Instantiation       : {'✅ OK' if instantiation_ok else '❌ FAIL'}")

    if total_fail == 0 and instantiation_ok:
        print_banner(
            "✅ Timeline Module Ready!",
            f"All {len(__all__)} components working | v{__version__}"
        )
    else:
        print_banner(
            "⚠️ Some Issues Found",
            f"Failed: {total_fail} components | Check imports"
        )