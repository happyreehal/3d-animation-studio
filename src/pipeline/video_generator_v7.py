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

logger = get_logger("VideoGeneratorV7")


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
    "OLD_WOMAN": (200, 170, 170),
    "NARRATOR":  (255, 200, 100),
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


def get_character_image_path(character_name):
    """Get path to character image, fallback if not found"""
    from src.ai.voice_profiles import CHARACTER_ALIASES
    
    project_root = Path(__file__).parent.parent.parent
    chars_dir = project_root / "assets" / "characters"
    
    # Direct match
    upper = character_name.upper().replace(" ", "_")
    folder_name = upper.lower()
    
    idle_path = chars_dir / folder_name / "idle.png"
    if idle_path.exists():
        return str(idle_path)
    
    # Try aliases
    for canonical, aliases in CHARACTER_ALIASES.items():
        for alias in aliases:
            if alias in upper:
                idle_path = chars_dir / canonical.lower() / "idle.png"
                if idle_path.exists():
                    return str(idle_path)
    
    # Default to HERO
    default_path = chars_dir / "hero" / "idle.png"
    if default_path.exists():
        return str(default_path)
    
    return None


class VideoGeneratorV7:
    def __init__(self, add_music=True):
        self.fps = 30
        self.resolution = (1920, 1080)
        self.add_music = add_music
        self.music_mixer = None
        
        # Cache loaded character images
        self._image_cache = {}
        
        if add_music:
            try:
                from src.audio.music_library import MusicMixer
                self.music_mixer = MusicMixer()
            except:
                pass
        
        logger.info("✅ VideoGeneratorV7 initialized (Pixar Characters)")

    def generate_video(self, dialogues, output_path, title="My Animation"):
        result = VideoResult()
        
        try:
            logger.info(f"🎬 V7 Generating: {title}")
            
            timestamp = int(time.time())
            temp_dir = Path("temp") / f"v7_{timestamp}"
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
            
            # Merge audios
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
            
            # Frames with Pixar characters
            logger.info("[4/5] Creating frames with PIXAR characters...")
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
                logger.info(f"   Characters: {result.characters_used}")
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
        """Load and cache character image"""
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
            
            logger.info(f"  [{i+1}] {character}")
            if image_path:
                logger.info(f"      Image: {os.path.basename(image_path)}")
            
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
        
        # Pre-load all character images
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
            
            # Speaking animation - subtle scale pulse
            dialogue_start = timings[current_idx][0]
            dialogue_time = current_time - dialogue_start
            pulse = math.sin(dialogue_time * 6) * 0.02  # +/- 2% scale
            
            # Create frame
            img = Image.new('RGB', self.resolution, color=(20, 20, 40))
            draw = ImageDraw.Draw(img)
            
            # Gradient background
            for y in range(0, 1080, 8):
                brightness = int(15 + (y / 1080) * 20)
                color = (brightness, brightness, brightness + 15)
                draw.rectangle([0, y, 1920, y + 8], fill=color)
            
            # ===== HEADER =====
            draw.rectangle([0, 0, 1920, 100], fill=(15, 15, 30))
            
            # Scene number
            draw.text((60, 50), f"SCENE {current_idx + 1}",
                     fill=(0, 212, 255), font=fonts['title'], anchor='lm')
            
            # Music indicator
            if self.add_music:
                draw.text((1860, 50), "MUSIC ON",
                         fill=(255, 200, 0), font=fonts['emotion'], anchor='rm')
            
            # ===== CHARACTER IMAGE (LEFT SIDE) =====
            if item.image_path:
                char_img = self._load_character_image(item.image_path)
                
                if char_img:
                    # Target size for character (fits in left half)
                    target_height = 800
                    aspect = char_img.width / char_img.height
                    target_width = int(target_height * aspect)
                    
                    # Apply pulse animation
                    scale_factor = 1.0 + pulse
                    display_width = int(target_width * scale_factor)
                    display_height = int(target_height * scale_factor)
                    
                    # Resize
                    resized = char_img.resize(
                        (display_width, display_height),
                        Image.Resampling.LANCZOS
                    )
                    
                    # Position (center-left)
                    char_x = 200
                    char_y = 130
                    
                    # Paste with alpha channel
                    if resized.mode == 'RGBA':
                        img.paste(resized, (char_x, char_y), resized)
                    else:
                        img.paste(resized, (char_x, char_y))
                    
                    # Draw stayed after paste
                    draw = ImageDraw.Draw(img)
            
            # ===== CHARACTER INFO (RIGHT SIDE) =====
            info_x = 1150
            
            # Character name
            draw.text((info_x, 250), item.character,
                     fill=item.color, font=fonts['name'], anchor='lm')
            
            # Emotion tag
            if item.emotion and item.emotion != "neutral":
                # Emotion badge background
                draw.rectangle(
                    [info_x - 20, 340, info_x + 250, 400],
                    fill=(40, 40, 60),
                    outline=item.color,
                    width=3
                )
                draw.text((info_x + 115, 370), f"[{item.emotion}]",
                         fill=(255, 255, 255), font=fonts['emotion'], anchor='mm')
            
            # Voice info
            if item.voice_profile:
                draw.text((info_x, 440), f"Voice: {item.voice_profile.name}",
                         fill=(180, 180, 200), font=fonts['voice_info'], anchor='lm')
            
            # ===== DIALOGUE BOX (BOTTOM) =====
            # Dialogue background
            draw.rectangle(
                [80, 830, 1840, 990],
                fill=(20, 20, 40),
                outline=item.color,
                width=5
            )
            
            # Speech indicator (colored bar on left)
            draw.rectangle(
                [80, 830, 100, 990],
                fill=item.color
            )
            
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
            
            # Progress bar
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


def create_video_v7(script_text, output_path="exports/output_v7.mp4",
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
    
    generator = VideoGeneratorV7(add_music=add_music)
    return generator.generate_video(dialogues, output_path, title)


if __name__ == "__main__":
    from src.utils import setup_logging, print_banner
    setup_logging(log_level="INFO")
    
    print_banner("V7 Test", "PIXAR CHARACTERS!")
    
    script = """HERO: (excited) Namaste doston! Aaj hum ek nayi kahani suru karte hain!
HEROINE: (happy) Main bhi is adventure mein aapke saath hoon!
VILLAIN: (angry) Ruko! Main tumhe kabhi jitne nahi dunga!
CHILD: (surprised) Papa dekho villain kitna khatarnak hai!
OLD_MAN: (calm) Beta chinta mat karo, hero zaroor jitega.
NARRATOR: (neutral) Aur is tarah shuru hui ek epic kahani!"""
    
    print("\n📝 6 characters with Pixar-quality images!")
    print("🎬 Generating V7...")
    
    result = create_video_v7(
        script_text=script,
        output_path="exports/v7_pixar_characters.mp4",
        title="Pixar Characters Test",
        add_music=True,
    )
    
    if result.success:
        print(f"\n✅ SUCCESS!")
        print(f"   Video: {result.video_path}")
        print(f"   Size: {result.file_size/1024:.2f} KB")
        print(f"   Duration: {result.duration:.2f}s")
        print(f"   Characters: {result.characters_used}")
        print(f"   Music: {result.music_mood}")
        
        try:
            os.startfile(os.path.abspath(result.video_path))
        except:
            print(f"\nManual: {os.path.abspath(result.video_path)}")
    else:
        print(f"\n❌ FAILED: {result.error}")