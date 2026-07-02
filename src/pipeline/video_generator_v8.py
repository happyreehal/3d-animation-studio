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
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter

from src.utils import get_logger

logger = get_logger("VideoGeneratorV8")


@dataclass
class DialogueItem:
    character: str
    text: str
    emotion: str = "neutral"
    audio_path: str = ""
    duration: float = 0.0
    color: Tuple[int, int, int] = (255, 255, 255)
    voice_profile: any = None
    image_path: str = ""
    face_coords: Optional[Tuple[int, int, int, int]] = None


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
    "HERO":      (255, 200, 50),
    "HEROINE":   (255, 105, 180),
    "VILLAIN":   (200, 30, 30),
    "CHILD":     (50, 150, 255),
    "OLD_MAN":   (150, 150, 150),
    "NARRATOR":  (255, 200, 100),
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


def get_character_image_path(character_name):
    from src.ai.voice_profiles import CHARACTER_ALIASES
    
    project_root = Path(__file__).parent.parent.parent
    chars_dir = project_root / "assets" / "characters"
    
    upper = character_name.upper().replace(" ", "_")
    folder_name = upper.lower()
    
    idle_path = chars_dir / folder_name / "idle.png"
    if idle_path.exists():
        return str(idle_path)
    
    for canonical, aliases in CHARACTER_ALIASES.items():
        for alias in aliases:
            if alias in upper:
                idle_path = chars_dir / canonical.lower() / "idle.png"
                if idle_path.exists():
                    return str(idle_path)
    
    default_path = chars_dir / "hero" / "idle.png"
    if default_path.exists():
        return str(default_path)
    
    return None


def detect_face_in_image(image_path):
    """Detect face location in character image using OpenCV"""
    try:
        import cv2
        
        img = cv2.imread(image_path)
        if img is None:
            return None
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Load face cascade
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) > 0:
            # Get largest face
            largest = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = largest
            logger.info(f"   Face detected: ({x}, {y}) size {w}x{h}")
            return (int(x), int(y), int(w), int(h))
        
        # Fallback: estimate face position (upper 1/3 of image)
        h, w = img.shape[:2]
        face_x = int(w * 0.35)
        face_y = int(h * 0.08)
        face_w = int(w * 0.3)
        face_h = int(h * 0.2)
        logger.info(f"   Face estimated (no detection): {face_x},{face_y}")
        return (face_x, face_y, face_w, face_h)
        
    except ImportError:
        logger.warning("OpenCV not installed, using estimated face position")
        return None
    except Exception as e:
        logger.error(f"Face detection error: {e}")
        return None


class VideoGeneratorV8:
    def __init__(self, add_music=True):
        self.fps = 30
        self.resolution = (1920, 1080)
        self.add_music = add_music
        self.music_mixer = None
        self._image_cache = {}
        self._face_cache = {}
        
        if add_music:
            try:
                from src.audio.music_library import MusicMixer
                self.music_mixer = MusicMixer()
            except:
                pass
        
        logger.info("✅ VideoGeneratorV8 initialized (Talking Animation)")

    def generate_video(self, dialogues, output_path, title="My Animation"):
        result = VideoResult()
        
        try:
            logger.info(f"🎬 V8 Generating: {title}")
            
            timestamp = int(time.time())
            temp_dir = Path("temp") / f"v8_{timestamp}"
            temp_dir.mkdir(parents=True, exist_ok=True)
            frames_dir = temp_dir / "frames"
            frames_dir.mkdir(exist_ok=True)
            
            logger.info("[1/5] Generating voices...")
            items = self._generate_audios(dialogues, temp_dir)
            if not items:
                result.error = "No audio"
                return result
            
            result.characters_used = list(set([d.character for d in items]))
            
            logger.info("[2/5] Merging audios...")
            voice_merged = self._merge_audios(items, temp_dir)
            if not voice_merged:
                result.error = "Merge failed"
                return result
            
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
            
            logger.info("[4/5] Creating frames with TALKING animation...")
            total_frames = self._create_frames(items, frames_dir, total_duration, title)
            
            if total_frames == 0:
                result.error = "Frames failed"
                return result
            
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

    def _load_character_image(self, image_path):
        if image_path in self._image_cache:
            return self._image_cache[image_path]
        
        try:
            from PIL import Image
            img = Image.open(image_path).convert('RGBA')
            self._image_cache[image_path] = img
            return img
        except Exception as e:
            logger.error(f"Image load error: {e}")
            return None

    def _get_face_coords(self, image_path):
        if image_path in self._face_cache:
            return self._face_cache[image_path]
        
        coords = detect_face_in_image(image_path)
        self._face_cache[image_path] = coords
        return coords

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
            image_path = get_character_image_path(character)
            face_coords = None
            
            if image_path:
                face_coords = self._get_face_coords(image_path)
            
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
                    image_path=image_path or "",
                    face_coords=face_coords,
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

    def _animate_character_frame(self, char_img, face_coords, 
                                  speaking_frame, dialogue_time, emotion):
        """Add talking animation to character image"""
        from PIL import Image, ImageDraw
        
        # Create a copy to draw on
        animated = char_img.copy()
        draw = ImageDraw.Draw(animated)
        
        if not face_coords:
            return animated
        
        face_x, face_y, face_w, face_h = face_coords
        
        # Calculate mouth position (lower 1/3 of face)
        mouth_center_x = face_x + face_w // 2
        mouth_center_y = face_y + int(face_h * 0.72)
        
        # Mouth size based on face
        mouth_width = int(face_w * 0.25)
        mouth_height = int(face_h * 0.08)
        
        # ===== MOUTH ANIMATION (Speaking) =====
        # Cycle through mouth states while speaking
        speaking_state = int(dialogue_time * 8) % 4  # 0, 1, 2, 3
        
        if speaking_state == 0:
            # Closed
            mouth_h = int(mouth_height * 0.3)
            mouth_w = int(mouth_width * 0.8)
            
            # Draw closed mouth (thin line)
            draw.ellipse(
                [mouth_center_x - mouth_w // 2, mouth_center_y - mouth_h // 2,
                 mouth_center_x + mouth_w // 2, mouth_center_y + mouth_h // 2],
                fill=(80, 40, 40),
                outline=(150, 50, 50),
                width=2
            )
        elif speaking_state == 1:
            # Small open
            mouth_h = int(mouth_height * 0.8)
            mouth_w = int(mouth_width * 0.7)
            
            draw.ellipse(
                [mouth_center_x - mouth_w // 2, mouth_center_y - mouth_h // 2,
                 mouth_center_x + mouth_w // 2, mouth_center_y + mouth_h // 2],
                fill=(60, 30, 30),
                outline=(150, 50, 50),
                width=3
            )
            # Teeth line
            draw.line(
                [mouth_center_x - mouth_w // 3, mouth_center_y - 1,
                 mouth_center_x + mouth_w // 3, mouth_center_y - 1],
                fill=(255, 255, 255),
                width=2
            )
        elif speaking_state == 2:
            # Wide open (talking)
            mouth_h = int(mouth_height * 1.5)
            mouth_w = int(mouth_width * 1.1)
            
            draw.ellipse(
                [mouth_center_x - mouth_w // 2, mouth_center_y - mouth_h // 2,
                 mouth_center_x + mouth_w // 2, mouth_center_y + mouth_h // 2],
                fill=(50, 20, 20),
                outline=(150, 50, 50),
                width=3
            )
            # Teeth
            draw.rectangle(
                [mouth_center_x - mouth_w // 3, mouth_center_y - mouth_h // 4,
                 mouth_center_x + mouth_w // 3, mouth_center_y - mouth_h // 6],
                fill=(255, 255, 255),
                outline=(200, 200, 200),
                width=1
            )
            # Tongue hint
            draw.ellipse(
                [mouth_center_x - mouth_w // 4, mouth_center_y + 2,
                 mouth_center_x + mouth_w // 4, mouth_center_y + mouth_h // 3],
                fill=(180, 80, 80)
            )
        else:
            # Medium open
            mouth_h = int(mouth_height * 1.1)
            mouth_w = int(mouth_width * 0.95)
            
            draw.ellipse(
                [mouth_center_x - mouth_w // 2, mouth_center_y - mouth_h // 2,
                 mouth_center_x + mouth_w // 2, mouth_center_y + mouth_h // 2],
                fill=(60, 30, 30),
                outline=(150, 50, 50),
                width=3
            )
            # Teeth
            draw.line(
                [mouth_center_x - mouth_w // 3, mouth_center_y - mouth_h // 4,
                 mouth_center_x + mouth_w // 3, mouth_center_y - mouth_h // 4],
                fill=(255, 255, 255),
                width=3
            )
        
        # ===== EYE BLINK ANIMATION =====
        # Blink every 3-4 seconds
        blink_time = dialogue_time % 3.5
        is_blinking = blink_time < 0.15  # Blink for 0.15 seconds
        
        if is_blinking:
            # Draw closed eyes (horizontal lines) over character's eyes
            eye_y = face_y + int(face_h * 0.4)
            eye_left_x = face_x + int(face_w * 0.3)
            eye_right_x = face_x + int(face_w * 0.7)
            eye_width = int(face_w * 0.12)
            
            # Left eye (closed)
            draw.line(
                [eye_left_x - eye_width // 2, eye_y,
                 eye_left_x + eye_width // 2, eye_y],
                fill=(80, 60, 40),
                width=4
            )
            
            # Right eye (closed)
            draw.line(
                [eye_right_x - eye_width // 2, eye_y,
                 eye_right_x + eye_width // 2, eye_y],
                fill=(80, 60, 40),
                width=4
            )
        
        # ===== EMOTION OVERLAY =====
        if emotion in ["angry", "furious"]:
            # Red tint on cheeks
            cheek_y = face_y + int(face_h * 0.55)
            cheek_left_x = face_x + int(face_w * 0.2)
            cheek_right_x = face_x + int(face_w * 0.8)
            cheek_size = int(face_w * 0.12)
            
            # Semi-transparent red cheeks
            overlay = Image.new('RGBA', animated.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            
            overlay_draw.ellipse(
                [cheek_left_x - cheek_size, cheek_y - cheek_size // 2,
                 cheek_left_x + cheek_size, cheek_y + cheek_size // 2],
                fill=(255, 50, 50, 80)
            )
            overlay_draw.ellipse(
                [cheek_right_x - cheek_size, cheek_y - cheek_size // 2,
                 cheek_right_x + cheek_size, cheek_y + cheek_size // 2],
                fill=(255, 50, 50, 80)
            )
            
            animated = Image.alpha_composite(animated.convert('RGBA'), overlay)
            
        elif emotion in ["sad", "crying"]:
            # Blue tint
            overlay = Image.new('RGBA', animated.size, (0, 0, 100, 30))
            animated = Image.alpha_composite(animated.convert('RGBA'), overlay)
            
            # Draw tears
            if int(dialogue_time * 2) % 2 == 0:
                tear_y = face_y + int(face_h * 0.5)
                tear_left_x = face_x + int(face_w * 0.35)
                tear_right_x = face_x + int(face_w * 0.65)
                
                draw = ImageDraw.Draw(animated)
                draw.ellipse(
                    [tear_left_x - 3, tear_y, tear_left_x + 3, tear_y + 15],
                    fill=(100, 150, 255, 200)
                )
                draw.ellipse(
                    [tear_right_x - 3, tear_y, tear_right_x + 3, tear_y + 15],
                    fill=(100, 150, 255, 200)
                )
        
        elif emotion in ["surprised", "shocked"]:
            # Draw exclamation mark near head
            excl_x = face_x + face_w + 20
            excl_y = face_y - 30
            
            draw.rectangle(
                [excl_x, excl_y, excl_x + 15, excl_y + 60],
                fill=(255, 200, 0),
                outline=(200, 100, 0),
                width=2
            )
            draw.ellipse(
                [excl_x, excl_y + 70, excl_x + 15, excl_y + 85],
                fill=(255, 200, 0),
                outline=(200, 100, 0),
                width=2
            )
        
        return animated

    def _create_frames(self, items, frames_dir, total_duration, title):
        from PIL import Image, ImageDraw, ImageFont
        
        font_paths = ["C:\\Windows\\Fonts\\Nirmala.ttf", "C:\\Windows\\Fonts\\arial.ttf"]
        fonts = {}
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    fonts = {
                        'title': ImageFont.truetype(fp, 55),
                        'name': ImageFont.truetype(fp, 80),
                        'emotion': ImageFont.truetype(fp, 40),
                        'voice_info': ImageFont.truetype(fp, 28),
                        'dialogue': ImageFont.truetype(fp, 48),
                        'footer': ImageFont.truetype(fp, 25),
                    }
                    break
                except:
                    continue
        
        if not fonts:
            d = ImageFont.load_default()
            fonts = {k: d for k in ['title', 'name', 'emotion', 'voice_info', 'dialogue', 'footer']}
        
        # Timings
        timings = []
        current_time = 0
        for i, item in enumerate(items):
            timings.append((current_time, current_time + item.duration, i))
            current_time += item.duration
        
        total_frames = int(total_duration * self.fps)
        logger.info(f"   Creating {total_frames} frames...")
        
        # Pre-load images
        for item in items:
            if item.image_path:
                self._load_character_image(item.image_path)
        
        for frame_num in range(total_frames):
            current_time = frame_num / self.fps
            
            current_idx = 0
            for start, end, idx in timings:
                if start <= current_time < end:
                    current_idx = idx
                    break
            
            item = items[current_idx]
            
            dialogue_start = timings[current_idx][0]
            dialogue_time = current_time - dialogue_start
            
            # Subtle head bob (up/down movement)
            head_bob = int(math.sin(dialogue_time * 4) * 8)
            
            # Subtle breathing zoom (very slight)
            zoom_factor = 1.0 + math.sin(dialogue_time * 2) * 0.01
            
            # Create frame
            img = Image.new('RGB', self.resolution, color=(20, 20, 40))
            draw = ImageDraw.Draw(img)
            
            # Gradient background
            for y in range(0, 1080, 8):
                brightness = int(15 + (y / 1080) * 20)
                color = (brightness, brightness, brightness + 15)
                draw.rectangle([0, y, 1920, y + 8], fill=color)
            
            # Header
            draw.rectangle([0, 0, 1920, 100], fill=(15, 15, 30))
            draw.text((60, 50), f"SCENE {current_idx + 1}",
                     fill=(0, 212, 255), font=fonts['title'], anchor='lm')
            
            if self.add_music:
                draw.text((1860, 50), "MUSIC ON",
                         fill=(255, 200, 0), font=fonts['emotion'], anchor='rm')
            
            # ===== CHARACTER IMAGE WITH ANIMATION =====
            if item.image_path:
                char_img = self._load_character_image(item.image_path)
                
                if char_img:
                    # Animate the character
                    animated_char = self._animate_character_frame(
                        char_img, item.face_coords, 
                        frame_num, dialogue_time, item.emotion
                    )
                    
                    # Resize
                    target_height = 800
                    aspect = animated_char.width / animated_char.height
                    target_width = int(target_height * aspect)
                    
                    # Apply zoom
                    display_width = int(target_width * zoom_factor)
                    display_height = int(target_height * zoom_factor)
                    
                    resized = animated_char.resize(
                        (display_width, display_height),
                        Image.Resampling.LANCZOS
                    )
                    
                    # Position with head bob
                    char_x = 200 - (display_width - target_width) // 2
                    char_y = 130 + head_bob - (display_height - target_height) // 2
                    
                    if resized.mode == 'RGBA':
                        img.paste(resized, (char_x, char_y), resized)
                    else:
                        img.paste(resized, (char_x, char_y))
                    
                    draw = ImageDraw.Draw(img)
            
            # Character info (right side)
            info_x = 1150
            
            draw.text((info_x, 250), item.character,
                     fill=item.color, font=fonts['name'], anchor='lm')
            
            if item.emotion and item.emotion != "neutral":
                draw.rectangle(
                    [info_x - 20, 340, info_x + 250, 400],
                    fill=(40, 40, 60), outline=item.color, width=3
                )
                draw.text((info_x + 115, 370), f"[{item.emotion}]",
                         fill=(255, 255, 255), font=fonts['emotion'], anchor='mm')
            
            if item.voice_profile:
                draw.text((info_x, 440), f"Voice: {item.voice_profile.name}",
                         fill=(180, 180, 200), font=fonts['voice_info'], anchor='lm')
            
            # Speaking indicator (animated dots)
            speaking_dots = int(dialogue_time * 4) % 4
            dots_text = "." * (speaking_dots + 1)
            draw.text((info_x, 520), f"Speaking{dots_text}",
                     fill=item.color, font=fonts['voice_info'], anchor='lm')
            
            # Dialogue box
            draw.rectangle(
                [80, 830, 1840, 990],
                fill=(20, 20, 40), outline=item.color, width=5
            )
            
            draw.rectangle([80, 830, 100, 990], fill=item.color)
            
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
            
            # Footer
            draw.rectangle([0, 1000, 1920, 1080], fill=(15, 15, 30))
            
            progress = (frame_num + 1) / total_frames * 100
            bar_width = int(1920 * progress / 100)
            
            draw.rectangle([0, 1000, 1920, 1010], fill=(40, 40, 70))
            draw.rectangle([0, 1000, bar_width, 1010], fill=(0, 212, 255))
            
            music_txt = " | MUSIC" if self.add_music else ""
            info = f"{title}{music_txt} | {current_time:.1f}s / {total_duration:.1f}s | {progress:.0f}%"
            draw.text((960, 1045), info,
                     fill=(180, 180, 200), font=fonts['footer'], anchor='mm')
            
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


def create_video_v8(script_text, output_path="exports/output_v8.mp4",
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
    
    generator = VideoGeneratorV8(add_music=add_music)
    return generator.generate_video(dialogues, output_path, title)


if __name__ == "__main__":
    from src.utils import setup_logging, print_banner
    setup_logging(log_level="INFO")
    
    print_banner("V8 Test", "TALKING ANIMATION!")
    
    script = """HERO: (excited) Namaste doston! Aaj bahut khas din hai!
VILLAIN: (angry) Ruko! Main tumhe kabhi jitne nahi dunga!
HEROINE: (happy) Chinta mat karo hero, main tumhare saath hoon!
CHILD: (surprised) Wow! Yeh kya ho raha hai!
OLD_MAN: (calm) Beta shanti rakho, sab theek ho jayega.
NARRATOR: (neutral) Aur is tarah adventure aage badha!"""
    
    print("\n📝 6 characters with TALKING ANIMATION!")
    print("🎬 Features:")
    print("  ✅ Mouth movement while speaking")
    print("  ✅ Eye blinking")
    print("  ✅ Head bobbing")
    print("  ✅ Breathing zoom")
    print("  ✅ Emotion overlays (angry cheeks, sad tears)")
    
    result = create_video_v8(
        script_text=script,
        output_path="exports/v8_talking.mp4",
        title="Talking Animation Test",
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
            print(f"\nManual: {os.path.abspath(result.video_path)}")
    else:
        print(f"\n❌ FAILED: {result.error}")