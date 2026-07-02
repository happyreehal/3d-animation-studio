# ============================================================
# src/audio/music_library.py
# Background Music System with Auto-Generation
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

import subprocess
import glob
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import random

from src.utils import get_logger

logger = get_logger("MusicLibrary")


# ============================================================
# MOODS
# ============================================================

class MusicMood(Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ACTION = "action"
    EMOTIONAL = "emotional"
    SUSPENSE = "suspense"


# Emotion → Mood mapping
EMOTION_TO_MOOD = {
    "happy": MusicMood.HAPPY,
    "excited": MusicMood.HAPPY,
    "cheerful": MusicMood.HAPPY,
    
    "sad": MusicMood.SAD,
    "emotional": MusicMood.EMOTIONAL,
    "crying": MusicMood.EMOTIONAL,
    
    "angry": MusicMood.ACTION,
    "furious": MusicMood.ACTION,
    "aggressive": MusicMood.ACTION,
    
    "surprised": MusicMood.SUSPENSE,
    "shocked": MusicMood.SUSPENSE,
    "nervous": MusicMood.SUSPENSE,
    
    "confident": MusicMood.NEUTRAL,
    "calm": MusicMood.NEUTRAL,
    "neutral": MusicMood.NEUTRAL,
    "serious": MusicMood.NEUTRAL,
}


# ============================================================
# MUSIC LIBRARY
# ============================================================

class MusicLibrary:
    """Background music manager"""
    
    def __init__(self):
        self.music_dir = Path("assets/music")
        self.music_dir.mkdir(parents=True, exist_ok=True)
        
        # Category subdirs
        for mood in MusicMood:
            (self.music_dir / mood.value).mkdir(exist_ok=True)
        
        logger.info("✅ MusicLibrary initialized")

    def get_music_for_emotion(self, emotion: str) -> Optional[str]:
        """Emotion ke basis pe music path lo"""
        mood = EMOTION_TO_MOOD.get(emotion.lower(), MusicMood.NEUTRAL)
        return self.get_music_by_mood(mood)

    def get_music_by_mood(self, mood: MusicMood) -> Optional[str]:
        """Mood ke basis pe random music lo"""
        mood_dir = self.music_dir / mood.value
        
        # Search for audio files
        audio_files = []
        for ext in ['*.mp3', '*.wav', '*.ogg', '*.m4a']:
            audio_files.extend(glob.glob(str(mood_dir / ext)))
        
        if audio_files:
            selected = random.choice(audio_files)
            logger.info(f"🎵 Music selected: {mood.value} → {os.path.basename(selected)}")
            return selected
        
        logger.warning(f"⚠️  No music files in {mood_dir}")
        return None

    def generate_default_music(self, mood: MusicMood, duration: float, output_path: str) -> bool:
        """
        Simple background music generate karo agar files nahi hain
        Uses FFmpeg to create ambient tones
        """
        try:
            # Different frequencies for different moods
            mood_configs = {
                MusicMood.HAPPY: {
                    "freq": "sine=frequency=440:duration={dur}",
                    "volume": "0.15"
                },
                MusicMood.SAD: {
                    "freq": "sine=frequency=220:duration={dur}",
                    "volume": "0.12"
                },
                MusicMood.ACTION: {
                    "freq": "sine=frequency=110:duration={dur}",
                    "volume": "0.18"
                },
                MusicMood.NEUTRAL: {
                    "freq": "sine=frequency=330:duration={dur}",
                    "volume": "0.10"
                },
                MusicMood.EMOTIONAL: {
                    "freq": "sine=frequency=277:duration={dur}",
                    "volume": "0.13"
                },
                MusicMood.SUSPENSE: {
                    "freq": "sine=frequency=165:duration={dur}",
                    "volume": "0.14"
                },
            }
            
            config = mood_configs.get(mood, mood_configs[MusicMood.NEUTRAL])
            
            # Generate tone
            filter_str = config["freq"].format(dur=duration)
            
            cmd = [
                'ffmpeg', '-y',
                '-f', 'lavfi',
                '-i', filter_str,
                '-af', f'volume={config["volume"]}',
                '-ac', '2',
                '-ar', '44100',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if os.path.exists(output_path):
                logger.info(f"✅ Generated music: {output_path}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Music generation error: {e}")
            return False

    def get_or_generate_music(
        self,
        emotion: str,
        duration: float,
        output_path: str
    ) -> Optional[str]:
        """
        Music lo - agar file hai to use karo,
        nahi to auto-generate karo
        """
        # Try to get existing music
        music_path = self.get_music_for_emotion(emotion)
        
        if music_path and os.path.exists(music_path):
            return music_path
        
        # Generate default music
        logger.info(f"🎵 Generating ambient music for '{emotion}'...")
        mood = EMOTION_TO_MOOD.get(emotion.lower(), MusicMood.NEUTRAL)
        
        if self.generate_default_music(mood, duration, output_path):
            return output_path
        
        return None


# ============================================================
# MUSIC MIXER
# ============================================================

class MusicMixer:
    """Music + Voice audio mixer"""
    
    def __init__(self):
        self.music_lib = MusicLibrary()
    
    def mix_voice_with_music(
        self,
        voice_audio: str,
        output_audio: str,
        emotion: str = "neutral",
        music_volume: float = 0.15,
        voice_volume: float = 1.0,
    ) -> bool:
        """
        Voice audio ke saath background music mix karo
        Music low volume rahega taki voice clear ho
        """
        try:
            # Get voice duration
            duration = self._get_duration(voice_audio)
            
            # Get music
            temp_music = "temp_music.wav"
            music_path = self.music_lib.get_or_generate_music(
                emotion=emotion,
                duration=duration,
                output_path=temp_music,
            )
            
            if not music_path:
                logger.warning("No music available, skipping mix")
                return False
            
            # Mix using FFmpeg
            cmd = [
                'ffmpeg', '-y',
                '-i', voice_audio,   # Input 0: voice
                '-i', music_path,    # Input 1: music
                '-filter_complex',
                f'[0:a]volume={voice_volume}[voice];'
                f'[1:a]volume={music_volume},atrim=0:{duration}[music];'
                f'[voice][music]amix=inputs=2:duration=first:dropout_transition=2[out]',
                '-map', '[out]',
                '-ac', '2',
                '-ar', '44100',
                output_audio
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            # Cleanup temp music
            if music_path == temp_music:
                try:
                    os.remove(temp_music)
                except:
                    pass
            
            if os.path.exists(output_audio):
                logger.info(f"✅ Voice + Music mixed: {output_audio}")
                return True
            else:
                logger.error(f"Mix failed: {result.stderr[-200:]}")
                return False
            
        except Exception as e:
            logger.error(f"Mix error: {e}")
            return False
    
    def _get_duration(self, audio_path: str) -> float:
        """Audio duration lo"""
        try:
            result = subprocess.run([
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                audio_path
            ], capture_output=True, text=True, timeout=10)
            return float(result.stdout.strip())
        except:
            return 10.0


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner
    setup_logging(log_level="INFO")
    
    print_banner("Music Library Test", "Background Music System")
    
    # Test 1: Create library
    lib = MusicLibrary()
    print(f"\n✅ Music library at: {lib.music_dir}")
    
    # Test 2: Generate default music for each mood
    print("\n" + "=" * 60)
    print("GENERATING DEFAULT MUSIC")
    print("=" * 60)
    
    for mood in MusicMood:
        output = f"test_music_{mood.value}.wav"
        print(f"\nGenerating {mood.value}...")
        
        if lib.generate_default_music(mood, 5.0, output):
            size = os.path.getsize(output)
            print(f"  ✅ Generated: {size:,} bytes")
        else:
            print(f"  ❌ Failed")
    
    # Test 3: Emotion mapping
    print("\n" + "=" * 60)
    print("EMOTION → MOOD MAPPING")
    print("=" * 60)
    
    test_emotions = [
        "happy", "sad", "angry", "excited", "calm",
        "surprised", "nervous", "confident", "emotional"
    ]
    
    for emotion in test_emotions:
        mood = EMOTION_TO_MOOD.get(emotion.lower(), MusicMood.NEUTRAL)
        print(f"  {emotion:15s} → {mood.value}")
    
    print("\n" + "=" * 60)
    print("✅ Music Library Ready!")
    print("=" * 60)
    print("\nAdd real music files to:")
    print(f"  {lib.music_dir}/happy/")
    print(f"  {lib.music_dir}/sad/")
    print(f"  {lib.music_dir}/action/")
    print(f"  ...")
    print("\nOr default ambient tones will be generated!")