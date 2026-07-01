# ============================================================
# 3D ANIMATION STUDIO - AI Module
# ============================================================
# AI-powered features for content creation:
#
#   🎤 TTS Engine          - Text-to-Speech (pyttsx3, gTTS, Coqui)
#   👄 Lipsync Engine      - Audio → mouth shapes (visemes)
#   😊 Expression Engine   - Text → facial expressions
#   📝 Subtitle Generator  - Whisper AI + text-based subtitles
#
# Clean import pattern:
#   from src.ai import TTSEngine, LipsyncEngine, ExpressionEngine
# ============================================================

# ===== PATH SETUP (must be at TOP, before any src.* imports) =====
# Standalone run ke liye zaroori - `python src/ai/__init__.py`
import sys
import os
if __name__ == "__main__":
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.dirname(os.path.dirname(_current_dir))
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
# =================================================================

# ------------------------------------------------------------
# TTS ENGINE - Text-to-Speech
# ------------------------------------------------------------
from src.ai.tts_engine import (
    # Main class
    TTSEngine,

    # Backends
    TTSBackend,
    Pyttsx3Backend,
    GTTSBackend,

    # Data classes
    VoiceProfile,
    TTSResult,

    # Enums / Constants
    TTSEngineType,
    Language,
)

# ------------------------------------------------------------
# LIPSYNC ENGINE - Audio → Mouth shapes
# ------------------------------------------------------------
from src.ai.lipsync_engine import (
    # Main class
    LipsyncEngine,

    # Lipsync methods (backends)
    AmplitudeLipsync,
    SpectralLipsync,
    TextBasedLipsync,

    # Phoneme / Viseme system
    Viseme,
    PhonemeMapper,
    SimplePhonemeExtractor,

    # Data classes
    LipsyncFrame,
    LipsyncData,
)

# ------------------------------------------------------------
# EXPRESSION ENGINE - Facial expressions
# ------------------------------------------------------------
from src.ai.expression_engine import (
    # Main class
    ExpressionEngine,

    # Detection
    EmotionDetector,
    EmotionKeywords,

    # Enums
    Emotion,
    Intensity,

    # Data classes
    FacialBlendShapes,
    ExpressionFrame,
    ExpressionData,
)

# ------------------------------------------------------------
# SUBTITLE GENERATOR - Whisper + text-based
# ------------------------------------------------------------
from src.ai.subtitle_generator import (
    # Main class
    SubtitleGenerator,

    # Generators (backends)
    WhisperTranscriber,
    TextBasedGenerator,

    # Data classes
    SubtitleSegment,
    SubtitleData,

    # Enums
    SubtitleFormat,
)


# ============================================================
# PUBLIC API - Explicit exports
# ============================================================
# Ye list define karti hai ki `from src.ai import *` pe kya milega
# Aur IDE autocomplete ko bhi help karti hai.

__all__ = [
    # ── TTS Engine ────────────────────────────────────────
    "TTSEngine",
    "TTSBackend",
    "Pyttsx3Backend",
    "GTTSBackend",
    "VoiceProfile",
    "TTSResult",
    "TTSEngineType",
    "Language",

    # ── Lipsync Engine ────────────────────────────────────
    "LipsyncEngine",
    "AmplitudeLipsync",
    "SpectralLipsync",
    "TextBasedLipsync",
    "Viseme",
    "PhonemeMapper",
    "SimplePhonemeExtractor",
    "LipsyncFrame",
    "LipsyncData",

    # ── Expression Engine ─────────────────────────────────
    "ExpressionEngine",
    "EmotionDetector",
    "EmotionKeywords",
    "Emotion",
    "Intensity",
    "FacialBlendShapes",
    "ExpressionFrame",
    "ExpressionData",

    # ── Subtitle Generator ────────────────────────────────
    "SubtitleGenerator",
    "WhisperTranscriber",
    "TextBasedGenerator",
    "SubtitleSegment",
    "SubtitleData",
    "SubtitleFormat",
]


# ============================================================
# MODULE METADATA
# ============================================================

__version__ = "1.0.0"
__author__ = "3D Animation Studio"
__description__ = "AI-powered features: TTS, Lipsync, Expression, Subtitles"


# ============================================================
# TEST / VERIFICATION
# ============================================================
# File standalone bhi run kar sakte ho verify karne ke liye

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")

    print_banner(
        "🤖 AI Module - Import Verification",
        f"v{__version__} | {len(__all__)} components loaded"
    )

    # ── Test 1: All Imports Work ──────────────────────────
    print_section("Test 1: Module Structure Check")

    modules_info = {
        "🎤 TTS Engine": [
            "TTSEngine", "Pyttsx3Backend", "GTTSBackend",
            "VoiceProfile", "TTSResult", "TTSEngineType", "Language",
        ],
        "👄 Lipsync Engine": [
            "LipsyncEngine", "AmplitudeLipsync", "SpectralLipsync",
            "TextBasedLipsync", "Viseme", "PhonemeMapper",
            "LipsyncFrame", "LipsyncData",
        ],
        "😊 Expression Engine": [
            "ExpressionEngine", "EmotionDetector", "Emotion",
            "FacialBlendShapes", "ExpressionFrame", "ExpressionData",
        ],
        "📝 Subtitle Generator": [
            "SubtitleGenerator", "WhisperTranscriber", "TextBasedGenerator",
            "SubtitleSegment", "SubtitleData", "SubtitleFormat",
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

    # ── Test 2: Enum Values Check ─────────────────────────
    print_section("Test 2: Key Enums / Constants")

    print(f"  TTSEngineType : {[e.value for e in TTSEngineType]}")
    print(f"  Emotion       : {[e.value for e in Emotion]}")
    print(f"  Viseme count  : {len([v for v in Viseme])}")
    print(f"  Languages     : {len(Language.get_all())}")
    print(f"  SubtitleFormat: {[f.value for f in SubtitleFormat]}")

    # ── Test 3: Instantiation Check ───────────────────────
    print_section("Test 3: Quick Instantiation Test")

    try:
        # Bas objects create karke check karo - errors detect ho jayenge
        tts = TTSEngine()
        print(f"  ✅ TTSEngine       : {len([b for b in tts.backends.values() if b.available])} backends ready")

        lip = LipsyncEngine()
        print(f"  ✅ LipsyncEngine   : fps={lip.default_fps}")

        expr = ExpressionEngine()
        print(f"  ✅ ExpressionEngine: language={expr.language}")

        sub = SubtitleGenerator()
        print(f"  ✅ SubtitleGenerator: whisper={sub.whisper.available}")

        instantiation_ok = True
    except Exception as e:
        print(f"  ❌ Instantiation failed: {e}")
        instantiation_ok = False

    # ── Final Summary ─────────────────────────────────────
    print_section("Summary")

    print(f"  Components exported : {len(__all__)}")
    print(f"  Imports verified    : {total_ok}/{total_ok + total_fail}")
    print(f"  Instantiation       : {'✅ OK' if instantiation_ok else '❌ FAIL'}")

    if total_fail == 0 and instantiation_ok:
        print_banner(
            "✅ AI Module Ready!",
            f"All {len(__all__)} components working | v{__version__}"
        )
    else:
        print_banner(
            "⚠️ Some Issues Found",
            f"Failed: {total_fail} components | Check imports"
        )