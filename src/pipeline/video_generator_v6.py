# ============================================================
# src/pipeline/video_generator_v6.py
# V6 - Full Body Characters + Multi-Voice + Music
# ============================================================

import sys
import os
if __name__ == "__main__":
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.dirname(os.path.dirname(_current_dir))
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

import subprocess
import shutil
import time
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter

from src.utils import get_logger

logger = get_logger("VideoGeneratorV6")


@dataclass
class DialogueItem:
    character: str
    text: str
    emotion: str = "neutral"
    audio_path: str = ""
    duration: float = 0.0
    color: Tuple[int, int, int] = (255, 255, 255)
    voice_profile: any = None


@dataclass
class VideoResult:
    success: bool = False
    video_path: str = ""
    audio_path: str = ""
    duration: float = 0.0
    total_frames: int = 0
    file_size: int = 0
    error: str = ""
    characters_used: List[str] = field(default_factory=list)
    music_mood: str = ""


CHARACTER_COLORS = {
    "HERO":      (0, 212, 255),
    "HEROINE":   (255, 105, 180),
    "VILLAIN":   (200, 30, 30),
    "CHILD":     (255, 165, 0),
    "OLD_MAN":   (150, 150, 150),
    "OLD_WOMAN": (200, 170, 170),
    "NARRATOR":  (255, 200, 0),
    "BOY":       (100, 200, 100),
    "GIRL":      (255, 192, 203),
    "TEACHER":   (255, 215, 0),
    "BOSS":      (138, 43, 226),
    "ROBOT":     (0, 255, 255),
    "GHOST":     (200, 200, 255),
}


def get_character_color(name):
    from src.ai.voice_profiles import CHARACTER_ALIASES
    upper = name.upper().replace(" ", "_")
    if upper in CHARACTER_COLORS:
        return CHARACTER_COLORS[upper]
    for canonical, aliases in CHARACTER_ALIASES.items():
        for alias in aliases:
            if alias in upper:
                return CHARACTER_COLORS.get(canonical, (255, 255, 255))
    return (255, 255, 255)


# ============================================================
# CHARACTER DRAWING - Full Body Stick Figures
# ============================================================

def draw_full_body_character(
    draw,
    center_x: int,
    center_y: int,
    scale: float,
    color: Tuple[int, int, int],
    emotion: str = "neutral",
    speaking_frame: int = 0,
):
    """
    Draw a full-body character with emotion-based pose
    speaking_frame: 0-3 for mouth animation
    """
    # Body proportions (scale = 1.0 means 400px tall character)
    head_radius = int(50 * scale)
    body_length = int(150 * scale)
    arm_length = int(90 * scale)
    leg_length = int(120 * scale)
    thickness = max(3, int(8 * scale))
    
    # Colors
    skin_color = (255, 220, 177)
    body_color = color
    dark_color = (max(0, color[0]-50), max(0, color[1]-50), max(0, color[2]-50))
    
    # ===== HEAD =====
    head_x = center_x
    head_y = center_y - body_length - head_radius
    
    # Head circle (skin colored)
    draw.ellipse(
        [head_x - head_radius, head_y - head_radius,
         head_x + head_radius, head_y + head_radius],
        fill=skin_color,
        outline=(80, 60, 40),
        width=thickness
    )
    
    # Eyes (emotion-based)
    eye_y = head_y - 10
    left_eye_x = head_x - 18
    right_eye_x = head_x + 18
    eye_radius = 6
    
    if emotion in ["angry", "furious"]:
        # Angry eyes - slanted lines
        draw.line([left_eye_x - 10, eye_y - 5, left_eye_x + 10, eye_y + 5], 
                 fill=(0, 0, 0), width=4)
        draw.line([right_eye_x - 10, eye_y + 5, right_eye_x + 10, eye_y - 5],
                 fill=(0, 0, 0), width=4)
    elif emotion in ["sad", "crying"]:
        # Sad eyes - drooping
        draw.arc([left_eye_x - 8, eye_y - 8, left_eye_x + 8, eye_y + 8],
                180, 360, fill=(0, 0, 0), width=3)
        draw.arc([right_eye_x - 8, eye_y - 8, right_eye_x + 8, eye_y + 8],
                180, 360, fill=(0, 0, 0), width=3)
    elif emotion in ["surprised", "shocked"]:
        # Wide open eyes
        draw.ellipse([left_eye_x - 10, eye_y - 10, left_eye_x + 10, eye_y + 10],
                    fill=(255, 255, 255), outline=(0, 0, 0), width=2)
        draw.ellipse([left_eye_x - 5, eye_y - 5, left_eye_x + 5, eye_y + 5],
                    fill=(0, 0, 0))
        draw.ellipse([right_eye_x - 10, eye_y - 10, right_eye_x + 10, eye_y + 10],
                    fill=(255, 255, 255), outline=(0, 0, 0), width=2)
        draw.ellipse([right_eye_x - 5, eye_y - 5, right_eye_x + 5, eye_y + 5],
                    fill=(0, 0, 0))
    else:
        # Normal eyes - simple dots
        draw.ellipse([left_eye_x - eye_radius, eye_y - eye_radius,
                     left_eye_x + eye_radius, eye_y + eye_radius], fill=(0, 0, 0))
        draw.ellipse([right_eye_x - eye_radius, eye_y - eye_radius,
                     right_eye_x + eye_radius, eye_y + eye_radius], fill=(0, 0, 0))
    
    # Eyebrows for emotions
    if emotion in ["angry", "furious"]:
        draw.line([left_eye_x - 12, eye_y - 15, left_eye_x + 12, eye_y - 10],
                 fill=(60, 40, 20), width=4)
        draw.line([right_eye_x - 12, eye_y - 10, right_eye_x + 12, eye_y - 15],
                 fill=(60, 40, 20), width=4)
    elif emotion in ["sad", "crying"]:
        draw.line([left_eye_x - 12, eye_y - 10, left_eye_x + 12, eye_y - 15],
                 fill=(60, 40, 20), width=3)
        draw.line([right_eye_x - 12, eye_y - 15, right_eye_x + 12, eye_y - 10],
                 fill=(60, 40, 20), width=3)
    elif emotion in ["happy", "excited"]:
        draw.arc([left_eye_x - 12, eye_y - 18, left_eye_x + 12, eye_y - 10],
                180, 360, fill=(60, 40, 20), width=3)
        draw.arc([right_eye_x - 12, eye_y - 18, right_eye_x + 12, eye_y - 10],
                180, 360, fill=(60, 40, 20), width=3)
    
    # Mouth (with speaking animation)
    mouth_y = head_y + 15
    
    if speaking_frame == 0:
        # Closed mouth
        if emotion in ["happy", "excited"]:
            # Smile
            draw.arc([head_x - 20, mouth_y - 10, head_x + 20, mouth_y + 15],
                    0, 180, fill=(200, 50, 50), width=4)
        elif emotion in ["sad", "crying"]:
            # Frown
            draw.arc([head_x - 20, mouth_y, head_x + 20, mouth_y + 20],
                    180, 360, fill=(200, 50, 50), width=4)
        elif emotion in ["angry", "furious"]:
            # Straight line
            draw.line([head_x - 15, mouth_y + 5, head_x + 15, mouth_y + 5],
                     fill=(200, 50, 50), width=4)
        else:
            # Neutral
            draw.line([head_x - 12, mouth_y + 5, head_x + 12, mouth_y + 5],
                     fill=(150, 50, 50), width=3)
    elif speaking_frame == 1:
        # Slightly open
        draw.ellipse([head_x - 8, mouth_y - 3, head_x + 8, mouth_y + 8],
                    fill=(80, 40, 40), outline=(200, 50, 50), width=2)
    elif speaking_frame == 2:
        # Wide open (O shape)
        draw.ellipse([head_x - 12, mouth_y - 5, head_x + 12, mouth_y + 15],
                    fill=(80, 40, 40), outline=(200, 50, 50), width=2)
    else:
        # Medium open
        draw.ellipse([head_x - 10, mouth_y - 2, head_x + 10, mouth_y + 10],
                    fill=(80, 40, 40), outline=(200, 50, 50), width=2)
    
    # ===== NECK =====
    neck_y = head_y + head_radius
    draw.line([head_x, neck_y, head_x, neck_y + 20],
             fill=skin_color, width=thickness * 2)
    
    # ===== BODY =====
    body_top_y = neck_y + 20
    body_bottom_y = body_top_y + body_length
    
    # Body (torso as rectangle with rounded top)
    body_width = int(60 * scale)
    draw.rectangle(
        [head_x - body_width, body_top_y,
         head_x + body_width, body_bottom_y],
        fill=body_color,
        outline=dark_color,
        width=thickness
    )
    
    # Add character letter on body
    from PIL import ImageFont
    try:
        font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", int(50 * scale))
        letter = get_character_letter(color)
        draw.text(
            (head_x, body_top_y + body_length // 2),
            letter,
            fill=(255, 255, 255),
            font=font,
            anchor='mm'
        )
    except:
        pass
    
    # ===== ARMS (emotion-based positions) =====
    shoulder_y = body_top_y + 20
    left_shoulder_x = head_x - body_width
    right_shoulder_x = head_x + body_width
    
    if emotion in ["happy", "excited"]:
        # Arms UP
        draw.line([left_shoulder_x, shoulder_y,
                  left_shoulder_x - 40, shoulder_y - arm_length],
                 fill=skin_color, width=thickness * 2)
        draw.line([right_shoulder_x, shoulder_y,
                  right_shoulder_x + 40, shoulder_y - arm_length],
                 fill=skin_color, width=thickness * 2)
    elif emotion in ["angry", "furious"]:
        # Arms on hips
        draw.line([left_shoulder_x, shoulder_y,
                  left_shoulder_x - 30, shoulder_y + 50],
                 fill=skin_color, width=thickness * 2)
        draw.line([left_shoulder_x - 30, shoulder_y + 50,
                  left_shoulder_x, shoulder_y + 100],
                 fill=skin_color, width=thickness * 2)
        draw.line([right_shoulder_x, shoulder_y,
                  right_shoulder_x + 30, shoulder_y + 50],
                 fill=skin_color, width=thickness * 2)
        draw.line([right_shoulder_x + 30, shoulder_y + 50,
                  right_shoulder_x, shoulder_y + 100],
                 fill=skin_color, width=thickness * 2)
    elif emotion in ["surprised", "shocked"]:
        # Arms wide open
        draw.line([left_shoulder_x, shoulder_y,
                  left_shoulder_x - arm_length, shoulder_y - 20],
                 fill=skin_color, width=thickness * 2)
        draw.line([right_shoulder_x, shoulder_y,
                  right_shoulder_x + arm_length, shoulder_y - 20],
                 fill=skin_color, width=thickness * 2)
    elif emotion in ["sad", "crying"]:
        # Arms down and slightly forward
        draw.line([left_shoulder_x, shoulder_y,
                  left_shoulder_x - 20, shoulder_y + arm_length],
                 fill=skin_color, width=thickness * 2)
        draw.line([right_shoulder_x, shoulder_y,
                  right_shoulder_x + 20, shoulder_y + arm_length],
                 fill=skin_color, width=thickness * 2)
    else:
        # Neutral - arms down at sides
        draw.line([left_shoulder_x, shoulder_y,
                  left_shoulder_x - 15, shoulder_y + arm_length],
                 fill=skin_color, width=thickness * 2)
        draw.line([right_shoulder_x, shoulder_y,
                  right_shoulder_x + 15, shoulder_y + arm_length],
                 fill=skin_color, width=thickness * 2)
    
    # Hands (small circles at end of arms)
    hand_size = int(15 * scale)
    if emotion in ["happy", "excited"]:
        draw.ellipse([left_shoulder_x - 40 - hand_size, shoulder_y - arm_length - hand_size,
                     left_shoulder_x - 40 + hand_size, shoulder_y - arm_length + hand_size],
                    fill=skin_color, outline=(80, 60, 40), width=2)
        draw.ellipse([right_shoulder_x + 40 - hand_size, shoulder_y - arm_length - hand_size,
                     right_shoulder_x + 40 + hand_size, shoulder_y - arm_length + hand_size],
                    fill=skin_color, outline=(80, 60, 40), width=2)
    
    # ===== LEGS =====
    leg_top_y = body_bottom_y
    
    # Left leg
    draw.line([head_x - 20, leg_top_y,
              head_x - 25, leg_top_y + leg_length],
             fill=(50, 50, 100), width=thickness * 3)
    # Right leg
    draw.line([head_x + 20, leg_top_y,
              head_x + 25, leg_top_y + leg_length],
             fill=(50, 50, 100), width=thickness * 3)
    
    # Feet
    foot_size = int(20 * scale)
    draw.ellipse([head_x - 25 - foot_size, leg_top_y + leg_length - 5,
                 head_x - 25 + foot_size, leg_top_y + leg_length + 15],
                fill=(30, 30, 30), outline=(0, 0, 0), width=2)
    draw.ellipse([head_x + 25 - foot_size, leg_top_y + leg_length - 5,
                 head_x + 25 + foot_size, leg_top_y + leg_length + 15],
                fill=(30, 30, 30), outline=(0, 0, 0), width=2)


def get_character_letter(color):
    """Get letter based on color match"""
    color_to_letter = {
        (0, 212, 255): "H",     # HERO
        (255, 105, 180): "L",   # HEROINE
        (200, 30, 30): "V",     # VILLAIN
        (255, 165, 0): "C",     # CHILD
        (150, 150, 150): "E",   # OLD_MAN
        (255, 200, 0): "N",     # NARRATOR
    }
    return color_to_letter.get(color, "?")


# ============================================================
# MAIN GENERATOR V6
# ============================================================

class VideoGeneratorV6:
    def __init__(self, add_music=True):
        self.fps = 30
        self.resolution = (1920, 1080)
        self.add_music = add_music
        self.music_mixer = None
        
        if add_music:
            try:
                from src.audio.music_library import MusicMixer
                self.music_mixer = MusicMixer()
            except:
                pass
        
        logger.info("✅ VideoGeneratorV6 initialized (Full Body Characters)")

    def generate_video(self, dialogues, output_path, title="My Animation"):
        result = VideoResult()
        
        try:
            logger.info(f"🎬 V6 Generating: {title}")
            
            timestamp = int(time.time())
            temp_dir = Path("temp") / f"v6_{timestamp}"
            temp_dir.mkdir(parents=True, exist_ok=True)
            frames_dir = temp_dir / "frames"
            frames_dir.mkdir(exist_ok=True)
            
            # Generate voices
            logger.info("[1/5] Generating voices...")
            items = self._generate_audios(dialogues, temp_dir)
            if not items:
                result.error = "No audio"
                return result
            
            result.characters_used = list(set([d.character for d in items]))
            
            # Merge
            logger.info("[2/5] Merging audios...")
            voice_merged = self._merge_audios(items, temp_dir)
            if not voice_merged:
                result.error = "Merge failed"
                return result
            
            # Music
            logger.info("[3/5] Adding music...")
            final_audio = voice_merged
            if self.add_music and self.music_mixer:
                emotion = self._get_dominant_emotion(items)
                music_mixed = temp_dir / "with_music.wav"
                if self.music_mixer.mix_voice_with_music(
                    str(voice_merged), str(music_mixed),
                    emotion=emotion, music_volume=0.10, voice_volume=1.0
                ):
                    final_audio = music_mixed
                    result.music_mood = emotion
            
            total_duration = sum(d.duration for d in items)
            
            # Frames with full body characters
            logger.info("[4/5] Creating frames with FULL BODY characters...")
            total_frames = self._create_frames(items, frames_dir, total_duration, title)
            
            if total_frames == 0:
                result.error = "Frames failed"
                return result
            
            # Final video
            logger.info("[5/5] Encoding video...")
            output_dir = Path(output_path).parent
            if str(output_dir):
                output_dir.mkdir(parents=True, exist_ok=True)
            
            if self._create_final_video(frames_dir, final_audio, output_path):
                result.success = True
                result.video_path = output_path
                result.duration = total_duration
                result.total_frames = total_frames
                result.file_size = os.path.getsize(output_path)
                
                logger.info(f"✅ Video: {output_path}")
                logger.info(f"   Size: {result.file_size/1024:.2f} KB")
            else:
                result.error = "Encoding failed"
            
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
            
            return result
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            result.error = str(e)
            return result

    def _get_dominant_emotion(self, items):
        emotions = [i.emotion for i in items if i.emotion and i.emotion != "neutral"]
        if not emotions:
            return "neutral"
        return Counter(emotions).most_common(1)[0][0]

    def _generate_audios(self, dialogues, temp_dir):
        from src.ai.voice_profiles import find_voice_profile
        from gtts import gTTS
        
        items = []
        for i, dlg in enumerate(dialogues):
            character = dlg.get("character", "SPEAKER")
            text = dlg.get("text", "")
            emotion = dlg.get("emotion", "neutral")
            
            if not text:
                continue
            
            profile = find_voice_profile(character)
            logger.info(f"  [{i+1}] {character}")
            
            try:
                mp3 = temp_dir / f"a_{i:03d}.mp3"
                tts = gTTS(text=text, lang=profile.language, 
                          tld=profile.tld, slow=profile.speed)
                tts.save(str(mp3))
                
                wav = temp_dir / f"a_{i:03d}.wav"
                subprocess.run([
                    'ffmpeg', '-y', '-i', str(mp3),
                    '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2',
                    str(wav)
                ], capture_output=True)
                
                if profile.pitch_shift != 0 or profile.speed_multiplier != 1.0:
                    wav = self._apply_effects(wav, profile, temp_dir, i)
                
                mp3.unlink(missing_ok=True)
                
                duration = self._get_duration(str(wav))
                
                items.append(DialogueItem(
                    character=character,
                    text=text,
                    emotion=emotion,
                    audio_path=str(wav),
                    duration=duration,
                    color=get_character_color(character),
                    voice_profile=profile,
                ))
                
            except Exception as e:
                logger.error(f"  {e}")
        
        return items

    def _apply_effects(self, input_file, profile, temp_dir, index):
        try:
            output_file = temp_dir / f"a_{index:03d}_p.wav"
            filters = []
            
            if profile.pitch_shift != 0:
                rate = 2 ** (profile.pitch_shift / 12)
                filters.append(f"asetrate=44100*{rate}")
                filters.append(f"aresample=44100")
            
            if profile.speed_multiplier != 1.0:
                filters.append(f"atempo={profile.speed_multiplier}")
            
            if not filters:
                return input_file
            
            subprocess.run([
                'ffmpeg', '-y', '-i', str(input_file),
                '-af', ",".join(filters), str(output_file)
            ], capture_output=True)
            
            if output_file.exists():
                input_file.unlink(missing_ok=True)
                return output_file
            return input_file
        except:
            return input_file

    def _get_duration(self, path):
        try:
            r = subprocess.run([
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', path
            ], capture_output=True, text=True, timeout=10)
            return float(r.stdout.strip())
        except:
            return 3.0

    def _merge_audios(self, items, temp_dir):
        try:
            concat = temp_dir / "concat.txt"
            with open(concat, 'w', encoding='utf-8') as f:
                for item in items:
                    f.write(f"file '{os.path.abspath(item.audio_path).replace(chr(92), '/')}'\n")
            
            merged = temp_dir / "merged.wav"
            subprocess.run([
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                '-i', str(concat), '-c', 'copy', str(merged)
            ], capture_output=True, timeout=60)
            
            return merged if merged.exists() else None
        except:
            return None

    def _create_frames(self, items, frames_dir, total_duration, title):
        from PIL import Image, ImageDraw, ImageFont
        
        # Fonts
        font_paths = ["C:\\Windows\\Fonts\\Nirmala.ttf", "C:\\Windows\\Fonts\\arial.ttf"]
        fonts = {}
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    fonts = {
                        'title': ImageFont.truetype(fp, 55),
                        'name': ImageFont.truetype(fp, 65),
                        'emotion': ImageFont.truetype(fp, 35),
                        'dialogue': ImageFont.truetype(fp, 45),
                        'footer': ImageFont.truetype(fp, 25),
                    }
                    break
                except:
                    continue
        
        if not fonts:
            d = ImageFont.load_default()
            fonts = {k: d for k in ['title', 'name', 'emotion', 'dialogue', 'footer']}
        
        # Timings
        timings = []
        current_time = 0
        for i, item in enumerate(items):
            timings.append((current_time, current_time + item.duration, i))
            current_time += item.duration
        
        total_frames = int(total_duration * self.fps)
        logger.info(f"   Creating {total_frames} frames...")
        
        for frame_num in range(total_frames):
            current_time = frame_num / self.fps
            
            current_idx = 0
            for start, end, idx in timings:
                if start <= current_time < end:
                    current_idx = idx
                    break
            
            item = items[current_idx]
            
            # Speaking animation frame (cycles 0-3)
            dialogue_start = timings[current_idx][0]
            dialogue_time = current_time - dialogue_start
            speaking_frame = int(dialogue_time * 8) % 4
            
            # Create frame
            img = Image.new('RGB', self.resolution, color=(20, 20, 35))
            draw = ImageDraw.Draw(img)
            
            # Gradient background (simulated)
            for y in range(0, 1080, 4):
                color_value = int(20 + (y / 1080) * 15)
                draw.rectangle([0, y, 1920, y+4], fill=(color_value, color_value, color_value + 10))
            
            # Header
            draw.rectangle([0, 0, 1920, 90], fill=(15, 15, 30))
            draw.text((60, 45), f"SCENE {current_idx + 1}",
                     fill=(0, 212, 255), font=fonts['title'], anchor='lm')
            
            if self.add_music:
                draw.text((1860, 45), "MUSIC ON",
                         fill=(255, 200, 0), font=fonts['emotion'], anchor='rm')
            
            # ===== FULL BODY CHARACTER (CENTER LEFT) =====
            character_x = 500
            character_y = 700  # Feet position
            
            draw_full_body_character(
                draw=draw,
                center_x=character_x,
                center_y=character_y,
                scale=1.2,
                color=item.color,
                emotion=item.emotion,
                speaking_frame=speaking_frame
            )
            
            # ===== CHARACTER INFO (RIGHT SIDE) =====
            info_x = 1050
            
            # Character name
            draw.text((info_x, 250), item.character,
                     fill=item.color, font=fonts['name'], anchor='lm')
            
            # Emotion
            if item.emotion and item.emotion != "neutral":
                draw.text((info_x, 340), f"[{item.emotion}]",
                         fill=(200, 200, 200), font=fonts['emotion'], anchor='lm')
            
            # Voice info
            if item.voice_profile:
                draw.text((info_x, 400), item.voice_profile.name,
                         fill=(150, 150, 180), font=fonts['footer'], anchor='lm')
            
            # ===== DIALOGUE BOX (BOTTOM) =====
            draw.rectangle([100, 830, 1820, 990],
                          fill=(25, 25, 45), outline=item.color, width=4)
            
            # Wrap text
            text = item.text
            max_chars = 50 if any(ord(c) > 127 for c in text) else 70
            
            words = text.split()
            lines = []
            current = ""
            for word in words:
                if len(current) + len(word) < max_chars:
                    current += word + " "
                else:
                    lines.append(current.strip())
                    current = word + " "
            if current:
                lines.append(current.strip())
            
            y_start = 910 - (len(lines) * 25)
            for i, line in enumerate(lines):
                draw.text((960, y_start + i * 55), line,
                         fill=(255, 255, 255), font=fonts['dialogue'], anchor='mm')
            
            # ===== FOOTER =====
            draw.rectangle([0, 1000, 1920, 1080], fill=(15, 15, 30))
            
            progress = (frame_num + 1) / total_frames * 100
            bar_width = int(1920 * progress / 100)
            draw.rectangle([0, 1000, 1920, 1010], fill=(40, 40, 70))
            draw.rectangle([0, 1000, bar_width, 1010], fill=(0, 212, 255))
            
            music_txt = " | MUSIC" if self.add_music else ""
            info = f"{title}{music_txt} | {current_time:.1f}s / {total_duration:.1f}s | {progress:.0f}%"
            draw.text((960, 1045), info,
                     fill=(180, 180, 200), font=fonts['footer'], anchor='mm')
            
            # Save
            img.save(str(frames_dir / f"frame_{frame_num:06d}.png"), 'PNG')
            
            if frame_num % 60 == 0:
                logger.debug(f"      Frame {frame_num}/{total_frames}")
        
        return total_frames

    def _create_final_video(self, frames_dir, audio_file, output_path):
        try:
            subprocess.run([
                'ffmpeg', '-y',
                '-framerate', str(self.fps),
                '-i', str(frames_dir / 'frame_%06d.png'),
                '-i', str(audio_file),
                '-map', '0:v:0', '-map', '1:a:0',
                '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
                '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '192k', '-ar', '44100',
                '-vf', f'scale={self.resolution[0]}:{self.resolution[1]}',
                '-shortest', output_path
            ], capture_output=True, timeout=300)
            
            return os.path.exists(output_path)
        except Exception as e:
            logger.error(f"Video error: {e}")
            return False


# ============================================================
# EASY USE
# ============================================================

def create_video_v6(script_text, output_path="exports/output_v6.mp4",
                    title="My Animation", add_music=True):
    dialogues = []
    for line in script_text.strip().split('\n'):
        line = line.strip()
        if not line or ':' not in line:
            continue
        
        parts = line.split(':', 1)
        character = parts[0].strip()
        rest = parts[1].strip()
        
        emotion = "neutral"
        if rest.startswith('(') and ')' in rest:
            end = rest.index(')')
            emotion = rest[1:end].strip()
            rest = rest[end+1:].strip()
        
        dialogues.append({"character": character, "text": rest, "emotion": emotion})
    
    generator = VideoGeneratorV6(add_music=add_music)
    return generator.generate_video(dialogues, output_path, title)


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner
    setup_logging(log_level="INFO")
    
    print_banner("V6 Test", "FULL BODY CHARACTERS!")
    
    script = """HERO: (happy) Namaste! Aaj main bahut khush hoon!
VILLAIN: (angry) Ruko! Main tumhe rokunga!
CHILD: (surprised) Wow! Kya baat hai!
OLD_MAN: (sad) Beta, mujhe dukh hai.
HEROINE: (excited) Chalo saath mein jitte hain!
NARRATOR: (neutral) Aur kahani aage badhi."""
    
    print("\n📝 6 characters with different emotions")
    print("🎬 Generating V6 with FULL BODY characters...")
    
    result = create_video_v6(
        script_text=script,
        output_path="exports/v6_full_body.mp4",
        title="Full Body Characters Test",
        add_music=True,
    )
    
    if result.success:
        print(f"\n✅ SUCCESS!")
        print(f"   Video: {result.video_path}")
        print(f"   Size: {result.file_size/1024:.2f} KB")
        print(f"   Duration: {result.duration:.2f}s")
        
        try:
            os.startfile(os.path.abspath(result.video_path))
        except:
            print(f"\nManual open: {os.path.abspath(result.video_path)}")
    else:
        print(f"\n❌ FAILED: {result.error}")