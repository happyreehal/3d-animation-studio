# ============================================================
# src/pipeline/quick_video.py
# Quick Video Generator - Uses V2 Engine
# Drop-in replacement for script_to_video()
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

from dataclasses import dataclass
from typing import Optional

from src.utils import get_logger

logger = get_logger("QuickVideo")


@dataclass
class QuickVideoResult:
    """Video generation result"""
    success: bool = False
    video_path: str = ""
    duration_seconds: float = 0.0
    total_frames: int = 0
    file_size: int = 0
    error: str = ""


def script_to_video_v2(
    script_text: str,
    output_path: str = "exports/output.mp4",
    title: str = "My Animation",
    quality: str = "high",
) -> QuickVideoResult:
    """
    Script se video banao - REAL TTS with Hindi support!
    
    Args:
        script_text: Script in format "CHARACTER: (emotion) text"
        output_path: Where to save MP4
        title: Video title
        quality: draft/medium/high/ultra
    
    Returns:
        QuickVideoResult with video info
    
    Example:
        result = script_to_video_v2(
            "HERO: (excited) Namaste!\\nVILLAIN: (angry) Ruko!",
            "exports/my_video.mp4",
            "My Story"
        )
    """
    result = QuickVideoResult()
    
    try:
        logger.info(f"Starting video generation: {title}")
        
        # Import V2 generator
        from src.pipeline.video_generator_v5 import create_video_v5 as create_video_from_script        
        # Ensure exports folder exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Generate video
        v2_result = create_video_from_script(
            script_text=script_text,
            output_path=output_path,
            title=title,
        )
        
        # Map results
        result.success = v2_result.success
        result.video_path = v2_result.video_path
        result.duration_seconds = v2_result.duration
        result.total_frames = v2_result.total_frames
        result.file_size = v2_result.file_size
        result.error = v2_result.error
        
        if result.success:
            logger.info(f"✅ Video created: {output_path}")
            logger.info(f"   Size: {result.file_size/1024:.2f} KB")
            logger.info(f"   Duration: {result.duration_seconds:.2f}s")
        else:
            logger.error(f"❌ Failed: {result.error}")
        
        return result
        
    except Exception as e:
        logger.error(f"Video generation error: {e}")
        import traceback
        traceback.print_exc()
        result.error = str(e)
        return result


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner
    setup_logging(log_level="INFO")
    
    print_banner("Quick Video Generator Test", "V2 Integration Test")
    
    # Test script
    script = """HERO: (excited) Namaste doston! Aaj main aapko dikhaunga kuch amazing!
VILLAIN: (angry) Nahi! Main tumhe rokunga!
HERO: (confident) Tum mujhe kabhi rok nahi sakte!"""
    
    print("\n📝 Test script:")
    print(script)
    
    print("\n🎬 Generating video...")
    
    result = script_to_video_v2(
        script_text=script,
        output_path="exports/quick_test.mp4",
        title="Quick Video Test",
        quality="high"
    )
    
    if result.success:
        print(f"\n✅ SUCCESS!")
        print(f"   Video: {result.video_path}")
        print(f"   Size: {result.file_size/1024:.2f} KB")
        print(f"   Duration: {result.duration_seconds:.2f}s")
        
        # Open video
        try:
            os.startfile(os.path.abspath(result.video_path))
        except:
            print(f"Manual open: {os.path.abspath(result.video_path)}")
    else:
        print(f"\n❌ FAILED!")
        print(f"   Error: {result.error}")