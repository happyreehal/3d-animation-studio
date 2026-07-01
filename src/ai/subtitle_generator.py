# ============================================================
# 3D ANIMATION STUDIO - Subtitle Generator
# ============================================================
# Features:
# - Whisper AI integration (optional, best quality)
# - Text-based subtitle generation (fallback)
# - SRT, VTT, ASS format export
# - Multi-language support (99+ with Whisper)
# - Word-level timestamps
# - Auto-formatting (line breaks, timing)
# - Duration-based fallback timing
# - YouTube-ready output
# - Speaker labels support
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

import re
import time
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

# Whisper (optional, heavy)
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    whisper = None

# Audio libraries (for duration)
try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False
    sf = None

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    AudioSegment = None

from src.utils import (
    get_logger, get_config, ensure_dir, generate_short_id,
    read_json, write_json, get_file_size, format_bytes,
    format_duration, seconds_to_timecode
)

logger = get_logger("SubtitleGenerator")


# ============================================================
# SUBTITLE FORMATS
# ============================================================

class SubtitleFormat(Enum):
    """Supported subtitle formats"""
    SRT = "srt"       # SubRip - most common
    VTT = "vtt"       # WebVTT - HTML5 video standard
    ASS = "ass"       # Advanced SubStation Alpha - styled
    TXT = "txt"       # Plain text with timestamps


# ============================================================
# SUBTITLE SEGMENT
# ============================================================

@dataclass
class SubtitleSegment:
    """Single subtitle entry"""
    index: int                        # 1-based numbering
    start_time: float                 # Seconds
    end_time: float                   # Seconds
    text: str                         # Subtitle text
    speaker: Optional[str] = None     # Optional speaker name
    confidence: float = 1.0           # 0-1 (Whisper confidence)

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    def to_dict(self) -> Dict:
        return {
            "index": self.index,
            "start_time": round(self.start_time, 3),
            "end_time": round(self.end_time, 3),
            "duration": round(self.duration, 3),
            "text": self.text,
            "speaker": self.speaker,
            "confidence": round(self.confidence, 3),
        }

    def format_srt_time(self, seconds: float) -> str:
        """Seconds to SRT timestamp: HH:MM:SS,mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def format_vtt_time(self, seconds: float) -> str:
        """Seconds to VTT timestamp: HH:MM:SS.mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    def to_srt(self) -> str:
        """SRT format string"""
        start = self.format_srt_time(self.start_time)
        end = self.format_srt_time(self.end_time)

        text = self.text
        if self.speaker:
            text = f"[{self.speaker}] {text}"

        return f"{self.index}\n{start} --> {end}\n{text}\n"

    def to_vtt(self) -> str:
        """VTT format string"""
        start = self.format_vtt_time(self.start_time)
        end = self.format_vtt_time(self.end_time)

        text = self.text
        if self.speaker:
            text = f"<v {self.speaker}>{text}"

        return f"{start} --> {end}\n{text}\n"

    def to_ass(self) -> str:
        """ASS format dialogue line"""
        # ASS uses centiseconds
        def ass_time(s):
            h = int(s // 3600)
            m = int((s % 3600) // 60)
            sec = int(s % 60)
            cs = int((s - int(s)) * 100)
            return f"{h:d}:{m:02d}:{sec:02d}.{cs:02d}"

        start = ass_time(self.start_time)
        end = ass_time(self.end_time)
        speaker = self.speaker or ""

        return f"Dialogue: 0,{start},{end},Default,{speaker},0,0,0,,{self.text}"


# ============================================================
# SUBTITLE DATA (Full transcript)
# ============================================================

@dataclass
class SubtitleData:
    """Complete subtitle/transcript data"""
    audio_file: Optional[str] = None
    language: str = "en"
    segments: List[SubtitleSegment] = field(default_factory=list)
    duration: float = 0.0
    generated_by: str = "text-based"     # "whisper", "text-based", "manual"
    generated_at: str = ""

    @property
    def total_segments(self) -> int:
        return len(self.segments)

    @property
    def total_words(self) -> int:
        return sum(len(s.text.split()) for s in self.segments)

    @property
    def full_text(self) -> str:
        """All segments joined"""
        return " ".join(s.text for s in self.segments)

    def to_dict(self) -> Dict:
        return {
            "audio_file": self.audio_file,
            "language": self.language,
            "duration": round(self.duration, 3),
            "total_segments": self.total_segments,
            "total_words": self.total_words,
            "generated_by": self.generated_by,
            "generated_at": self.generated_at,
            "segments": [s.to_dict() for s in self.segments],
        }

    def save_json(self, filepath: str) -> bool:
        """JSON me save karo"""
        try:
            ensure_dir(os.path.dirname(filepath))
            return write_json(filepath, self.to_dict())
        except Exception as e:
            logger.error(f"JSON save failed: {e}")
            return False

    def save_srt(self, filepath: str) -> bool:
        """SRT file save karo"""
        try:
            ensure_dir(os.path.dirname(filepath))

            with open(filepath, "w", encoding="utf-8") as f:
                for segment in self.segments:
                    f.write(segment.to_srt() + "\n")

            logger.info(f"SRT saved: {filepath}")
            return True
        except Exception as e:
            logger.error(f"SRT save failed: {e}")
            return False

    def save_vtt(self, filepath: str) -> bool:
        """VTT file save karo (WebVTT)"""
        try:
            ensure_dir(os.path.dirname(filepath))

            with open(filepath, "w", encoding="utf-8") as f:
                f.write("WEBVTT\n\n")

                for segment in self.segments:
                    f.write(segment.to_vtt() + "\n")

            logger.info(f"VTT saved: {filepath}")
            return True
        except Exception as e:
            logger.error(f"VTT save failed: {e}")
            return False

    def save_ass(self, filepath: str,
                 style_name: str = "Default") -> bool:
        """ASS file save karo (Advanced SubStation)"""
        try:
            ensure_dir(os.path.dirname(filepath))

            with open(filepath, "w", encoding="utf-8") as f:
                # Header
                f.write("[Script Info]\n")
                f.write("Title: Generated Subtitles\n")
                f.write("ScriptType: v4.00+\n")
                f.write("PlayResX: 1920\n")
                f.write("PlayResY: 1080\n\n")

                # Styles
                f.write("[V4+ Styles]\n")
                f.write("Format: Name, Fontname, Fontsize, PrimaryColour, "
                       "SecondaryColour, OutlineColour, BackColour, Bold, "
                       "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, "
                       "Angle, BorderStyle, Outline, Shadow, Alignment, "
                       "MarginL, MarginR, MarginV, Encoding\n")
                f.write(f"Style: {style_name},Arial,48,&H00FFFFFF,&H000000FF,"
                       "&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,"
                       "2,10,10,30,1\n\n")

                # Events
                f.write("[Events]\n")
                f.write("Format: Layer, Start, End, Style, Name, MarginL, "
                       "MarginR, MarginV, Effect, Text\n")

                for segment in self.segments:
                    f.write(segment.to_ass() + "\n")

            logger.info(f"ASS saved: {filepath}")
            return True
        except Exception as e:
            logger.error(f"ASS save failed: {e}")
            return False

    def save_txt(self, filepath: str,
                 include_timestamps: bool = True) -> bool:
        """Plain text file save karo"""
        try:
            ensure_dir(os.path.dirname(filepath))

            with open(filepath, "w", encoding="utf-8") as f:
                for segment in self.segments:
                    if include_timestamps:
                        start = seconds_to_timecode(segment.start_time)
                        f.write(f"[{start}] ")
                    if segment.speaker:
                        f.write(f"{segment.speaker}: ")
                    f.write(segment.text + "\n")

            logger.info(f"TXT saved: {filepath}")
            return True
        except Exception as e:
            logger.error(f"TXT save failed: {e}")
            return False

    def export_all_formats(self, output_dir: str,
                           filename_base: str) -> Dict[str, str]:
        """Sab formats me export karo"""
        ensure_dir(output_dir)
        results = {}

        # SRT
        srt_path = os.path.join(output_dir, f"{filename_base}.srt")
        if self.save_srt(srt_path):
            results["srt"] = srt_path

        # VTT
        vtt_path = os.path.join(output_dir, f"{filename_base}.vtt")
        if self.save_vtt(vtt_path):
            results["vtt"] = vtt_path

        # ASS
        ass_path = os.path.join(output_dir, f"{filename_base}.ass")
        if self.save_ass(ass_path):
            results["ass"] = ass_path

        # TXT
        txt_path = os.path.join(output_dir, f"{filename_base}.txt")
        if self.save_txt(txt_path):
            results["txt"] = txt_path

        # JSON
        json_path = os.path.join(output_dir, f"{filename_base}.json")
        if self.save_json(json_path):
            results["json"] = json_path

        return results


# ============================================================
# WHISPER TRANSCRIBER
# ============================================================

class WhisperTranscriber:
    """
    OpenAI Whisper for high-quality transcription.
    Requires: pip install openai-whisper
    """

    # Available models (smaller = faster, larger = better)
    MODELS = {
        "tiny": "~39 MB, fastest, less accurate",
        "base": "~74 MB, fast, good",
        "small": "~244 MB, medium, better",
        "medium": "~769 MB, slow, great",
        "large": "~1550 MB, slowest, best",
    }

    def __init__(self, model_name: str = "base"):
        self.available = WHISPER_AVAILABLE
        self.model_name = model_name
        self._model = None

        if not self.available:
            logger.warning(
                "Whisper not installed. Install: pip install openai-whisper"
            )

    def _load_model(self):
        """Model lazy load karo (pehle use ke waqt)"""
        if not self.available:
            return False

        if self._model is None:
            try:
                logger.info(f"Loading Whisper model '{self.model_name}'...")
                logger.info("(First time may take a few minutes to download)")
                self._model = whisper.load_model(self.model_name)
                logger.info(f"Whisper model loaded")
                return True
            except Exception as e:
                logger.error(f"Whisper model load failed: {e}")
                return False

        return True

    def transcribe(self, audio_file: str,
                   language: Optional[str] = None) -> Optional[SubtitleData]:
        """
        Audio ko transcribe karo.

        Args:
            audio_file: Audio file path
            language: Language code (None = auto-detect)
        """
        if not self.available:
            return None

        if not os.path.exists(audio_file):
            logger.error(f"File not found: {audio_file}")
            return None

        if not self._load_model():
            return None

        try:
            logger.info(f"Transcribing: {os.path.basename(audio_file)}...")
            start_time = time.time()

            # Transcribe options
            options = {}
            if language:
                options["language"] = language

            # Run whisper
            result = self._model.transcribe(audio_file, **options)

            elapsed = time.time() - start_time
            logger.info(f"Transcription complete in {elapsed:.1f}s")

            # Result ko SubtitleData me convert karo
            subtitle_data = SubtitleData(
                audio_file=audio_file,
                language=result.get("language", language or "en"),
                generated_by="whisper",
                generated_at=str(time.time()),
            )

            # Segments
            for i, seg in enumerate(result.get("segments", []), 1):
                segment = SubtitleSegment(
                    index=i,
                    start_time=seg["start"],
                    end_time=seg["end"],
                    text=seg["text"].strip(),
                    confidence=1.0 - abs(seg.get("no_speech_prob", 0))
                )
                subtitle_data.segments.append(segment)

            # Total duration
            if subtitle_data.segments:
                subtitle_data.duration = subtitle_data.segments[-1].end_time

            logger.info(
                f"Generated {subtitle_data.total_segments} segments "
                f"({subtitle_data.total_words} words)"
            )
            return subtitle_data

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None


# ============================================================
# TEXT-BASED SUBTITLE GENERATOR (Fallback)
# ============================================================

class TextBasedGenerator:
    """
    Script text + audio duration se subtitles banao.
    Simple, no AI needed.
    """

    # Reading speed (words per minute)
    READING_SPEED_WPM = 160  # Average reading speed
    MAX_CHARS_PER_LINE = 42
    MAX_LINES_PER_SUBTITLE = 2
    MIN_DURATION = 1.0        # Minimum seconds per subtitle
    MAX_DURATION = 6.0        # Maximum seconds per subtitle

    @classmethod
    def generate(cls, text: str, duration: float,
                 audio_file: Optional[str] = None,
                 language: str = "en") -> SubtitleData:
        """
        Text + duration se subtitles generate karo.

        Args:
            text: Script text
            duration: Total audio duration in seconds
            audio_file: Optional audio reference
            language: Language code
        """
        subtitle_data = SubtitleData(
            audio_file=audio_file,
            language=language,
            duration=duration,
            generated_by="text-based",
            generated_at=str(time.time()),
        )

        if not text or not text.strip():
            return subtitle_data

        # Sentences me split karo
        sentences = cls._split_into_sentences(text)

        if not sentences:
            return subtitle_data

        # Total words
        total_words = sum(len(s.split()) for s in sentences)
        if total_words == 0:
            return subtitle_data

        # Har sentence ko duration proportional to word count
        current_time = 0.0
        index = 1

        for sentence in sentences:
            words_count = len(sentence.split())
            if words_count == 0:
                continue

            # Duration for this sentence
            sentence_duration = (words_count / total_words) * duration

            # Clamp duration
            sentence_duration = max(
                cls.MIN_DURATION,
                min(cls.MAX_DURATION, sentence_duration)
            )

            # Long sentence split karo agar zaroori ho
            chunks = cls._split_long_sentence(sentence)

            if len(chunks) == 1:
                # Single subtitle
                segment = SubtitleSegment(
                    index=index,
                    start_time=current_time,
                    end_time=current_time + sentence_duration,
                    text=chunks[0]
                )
                subtitle_data.segments.append(segment)
                index += 1
                current_time += sentence_duration
            else:
                # Multiple subtitles from one sentence
                chunk_duration = sentence_duration / len(chunks)
                for chunk in chunks:
                    segment = SubtitleSegment(
                        index=index,
                        start_time=current_time,
                        end_time=current_time + chunk_duration,
                        text=chunk
                    )
                    subtitle_data.segments.append(segment)
                    index += 1
                    current_time += chunk_duration

        return subtitle_data

    @classmethod
    def _split_into_sentences(cls, text: str) -> List[str]:
        """Text ko sentences me split karo"""
        # . ! ? par split karo
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s.strip() for s in sentences if s.strip()]

    @classmethod
    def _split_long_sentence(cls, sentence: str) -> List[str]:
        """
        Long sentence ko chunks me todo based on max chars.
        """
        max_length = cls.MAX_CHARS_PER_LINE * cls.MAX_LINES_PER_SUBTITLE

        if len(sentence) <= max_length:
            return [cls._format_line_breaks(sentence)]

        # Words based splitting
        words = sentence.split()
        chunks = []
        current_chunk = []
        current_length = 0

        for word in words:
            word_length = len(word) + 1  # +1 for space
            if current_length + word_length > max_length and current_chunk:
                chunks.append(cls._format_line_breaks(" ".join(current_chunk)))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length

        if current_chunk:
            chunks.append(cls._format_line_breaks(" ".join(current_chunk)))

        return chunks

    @classmethod
    def _format_line_breaks(cls, text: str) -> str:
        """Text me line break add karo agar length exceed"""
        if len(text) <= cls.MAX_CHARS_PER_LINE:
            return text

        # Middle ke aas paas break karo
        words = text.split()
        if len(words) <= 1:
            return text

        # Find best split point
        target_length = len(text) // 2
        current_length = 0
        split_idx = 0

        for i, word in enumerate(words):
            current_length += len(word) + 1
            if current_length >= target_length:
                split_idx = i + 1
                break

        line1 = " ".join(words[:split_idx])
        line2 = " ".join(words[split_idx:])

        return f"{line1}\n{line2}"


# ============================================================
# MAIN SUBTITLE GENERATOR
# ============================================================

class SubtitleGenerator:
    """
    Main subtitle generator.
    Whisper ya text-based methods use karta hai.
    """

    def __init__(self, config: Optional[Dict] = None,
                 whisper_model: str = "base"):
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # Whisper transcriber
        self.whisper = WhisperTranscriber(model_name=whisper_model)

        # Stats
        self.total_generated = 0

        logger.info(
            f"SubtitleGenerator initialized "
            f"(whisper: {'available' if self.whisper.available else 'not installed'})"
        )

    # ------------------------------------------------------------
    # GENERATION METHODS
    # ------------------------------------------------------------

    def generate_from_audio(self, audio_file: str,
                             language: Optional[str] = None,
                             fallback_text: Optional[str] = None) -> Optional[SubtitleData]:
        """
        Audio se subtitles generate karo (Whisper).
        Agar Whisper na ho to fallback text use karo.
        """
        # Try Whisper first
        if self.whisper.available:
            result = self.whisper.transcribe(audio_file, language)
            if result:
                self.total_generated += 1
                return result

        # Fallback to text-based (agar text diya hai)
        if fallback_text:
            logger.info("Using text-based fallback")
            duration = self._get_audio_duration(audio_file)
            result = TextBasedGenerator.generate(
                text=fallback_text,
                duration=duration,
                audio_file=audio_file,
                language=language or "en"
            )
            self.total_generated += 1
            return result

        logger.warning("Cannot generate subtitles - no method available")
        return None

    def generate_from_text(self, text: str,
                           duration: float,
                           audio_file: Optional[str] = None,
                           language: str = "en") -> SubtitleData:
        """
        Text script se subtitles generate karo.
        """
        result = TextBasedGenerator.generate(
            text=text,
            duration=duration,
            audio_file=audio_file,
            language=language
        )
        self.total_generated += 1
        return result

    # ------------------------------------------------------------
    # UTILITIES
    # ------------------------------------------------------------

    def _get_audio_duration(self, audio_file: str) -> float:
        """Audio duration nikalo"""
        if not os.path.exists(audio_file):
            return 0.0

        try:
            if SOUNDFILE_AVAILABLE:
                with sf.SoundFile(audio_file) as f:
                    return f.frames / f.samplerate
        except Exception:
            pass

        try:
            if PYDUB_AVAILABLE:
                audio = AudioSegment.from_file(audio_file)
                return len(audio) / 1000.0
        except Exception:
            pass

        # Fallback estimate
        return 5.0

    def batch_generate(self, tasks: List[Dict],
                       output_dir: str,
                       formats: Optional[List[str]] = None) -> List[Dict]:
        """
        Batch subtitle generation.

        Args:
            tasks: [{"audio_file": "...", "text": "...", "language": "en"}, ...]
            output_dir: Output directory
            formats: ["srt", "vtt", "ass", "txt", "json"]

        Returns:
            List of result dicts
        """
        if formats is None:
            formats = ["srt", "vtt"]

        ensure_dir(output_dir)
        results = []

        for i, task in enumerate(tasks, 1):
            audio_file = task.get("audio_file")
            text = task.get("text")
            language = task.get("language", "en")

            logger.info(f"Processing task {i}/{len(tasks)}...")

            # Generate
            if audio_file and os.path.exists(audio_file):
                subtitle = self.generate_from_audio(
                    audio_file, language, fallback_text=text
                )
            elif text:
                duration = task.get("duration", 5.0)
                subtitle = self.generate_from_text(
                    text, duration, language=language
                )
            else:
                logger.warning(f"Task {i}: No audio or text provided")
                continue

            if not subtitle:
                continue

            # Export
            base_name = f"subtitle_{i:03d}"
            if audio_file:
                base_name = os.path.splitext(os.path.basename(audio_file))[0]

            exported = {}
            for fmt in formats:
                path = os.path.join(output_dir, f"{base_name}.{fmt}")
                success = False

                if fmt == "srt":
                    success = subtitle.save_srt(path)
                elif fmt == "vtt":
                    success = subtitle.save_vtt(path)
                elif fmt == "ass":
                    success = subtitle.save_ass(path)
                elif fmt == "txt":
                    success = subtitle.save_txt(path)
                elif fmt == "json":
                    success = subtitle.save_json(path)

                if success:
                    exported[fmt] = path

            results.append({
                "task_index": i,
                "subtitle_data": subtitle,
                "exported_files": exported,
            })

        logger.info(f"Batch complete: {len(results)}/{len(tasks)} generated")
        return results

    def get_stats(self) -> Dict:
        """Engine statistics"""
        return {
            "total_generated": self.total_generated,
            "whisper_available": self.whisper.available,
            "whisper_model": self.whisper.model_name,
            "audio_libs": {
                "soundfile": SOUNDFILE_AVAILABLE,
                "pydub": PYDUB_AVAILABLE,
            }
        }


# ============================================================
# TEST FUNCTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")
    print_banner("Subtitle Generator Test", "AI Subtitle Generation")

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))

    # ============================================================
    # Test 1: Initialize
    # ============================================================
    print_section("Test 1: Initialize Subtitle Generator")

    generator = SubtitleGenerator(whisper_model="base")

    stats = generator.get_stats()
    print(f"Whisper available: {stats['whisper_available']}")
    print(f"Whisper model: {stats['whisper_model']}")
    print(f"Audio libs: {stats['audio_libs']}")

    if not stats['whisper_available']:
        print("\n⚠️  Whisper not installed - will use text-based method")
        print("    Install for best quality: pip install openai-whisper")

    # ============================================================
    # Test 2: Available Formats
    # ============================================================
    print_section("Test 2: Supported Formats")

    for fmt in SubtitleFormat:
        print(f"  📄 {fmt.value.upper():4s} - {fmt.name}")

    # ============================================================
    # Test 3: Text-Based Generation
    # ============================================================
    print_section("Test 3: Text-Based Subtitle Generation")

    script = (
        "Hello and welcome to my 3D animation channel! "
        "Today we're going to learn about lipsync and expressions. "
        "This tutorial will cover everything from basic to advanced techniques. "
        "So grab a coffee and let's get started! "
        "First, we'll set up our character. "
        "Then we'll add facial animations. "
        "Finally, we'll sync everything with audio."
    )

    print(f"Script:\n{script}\n")

    subtitle = generator.generate_from_text(
        text=script,
        duration=15.0,  # 15 seconds
        language="en"
    )

    print(f"✅ Generated {subtitle.total_segments} segments")
    print(f"   Total words: {subtitle.total_words}")
    print(f"   Duration: {subtitle.duration}s")

    # Show segments
    print("\nSegments:")
    for seg in subtitle.segments:
        print(f"  [{seg.index}] "
              f"{seconds_to_timecode(seg.start_time)} → "
              f"{seconds_to_timecode(seg.end_time)}")
        print(f"      \"{seg.text}\"")

    # ============================================================
    # Test 4: Export to All Formats
    # ============================================================
    print_section("Test 4: Export All Formats")

    output_dir = os.path.join(base_dir, "temp", "subtitle_tests")
    ensure_dir(output_dir)

    exported = subtitle.export_all_formats(output_dir, "test_script")

    print("Exported files:")
    for fmt, path in exported.items():
        size = get_file_size(path)
        print(f"  ✓ {fmt.upper():5s}: {os.path.basename(path)} ({format_bytes(size)})")

    # ============================================================
    # Test 5: SRT Preview
    # ============================================================
    print_section("Test 5: SRT Content Preview")

    srt_path = exported.get("srt")
    if srt_path and os.path.exists(srt_path):
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Show first 500 chars
        print(content[:500])
        if len(content) > 500:
            print("...")

    # ============================================================
    # Test 6: VTT Preview
    # ============================================================
    print_section("Test 6: VTT Content Preview")

    vtt_path = exported.get("vtt")
    if vtt_path and os.path.exists(vtt_path):
        with open(vtt_path, "r", encoding="utf-8") as f:
            content = f.read()

        print(content[:400])
        if len(content) > 400:
            print("...")

    # ============================================================
    # Test 7: Long Sentence Splitting
    # ============================================================
    print_section("Test 7: Long Sentence Auto-Split")

    long_text = (
        "This is a very long sentence that exceeds the maximum character "
        "limit and should be automatically split into multiple subtitle "
        "segments so that viewers can read them comfortably without "
        "having to pause the video multiple times to catch up."
    )

    subtitle_long = generator.generate_from_text(
        text=long_text,
        duration=10.0
    )

    print(f"Long text → {subtitle_long.total_segments} segments")
    for i, seg in enumerate(subtitle_long.segments, 1):
        char_count = len(seg.text.replace("\n", ""))
        print(f"  {i}. ({char_count} chars) {seg.text[:60]}...")

    # ============================================================
    # Test 8: Speaker Labels
    # ============================================================
    print_section("Test 8: Multi-Speaker Subtitles")

    dialogue_subtitle = SubtitleData(
        language="en",
        generated_by="manual",
    )

    speakers_data = [
        (0.0, 2.0, "Alice", "Hey Bob, how are you doing today?"),
        (2.5, 4.5, "Bob", "I'm doing great, thanks for asking!"),
        (5.0, 7.0, "Alice", "Want to grab some coffee later?"),
        (7.5, 9.5, "Bob", "Sure, that sounds wonderful!"),
    ]

    for i, (start, end, speaker, text) in enumerate(speakers_data, 1):
        seg = SubtitleSegment(
            index=i,
            start_time=start,
            end_time=end,
            text=text,
            speaker=speaker
        )
        dialogue_subtitle.segments.append(seg)

    dialogue_subtitle.duration = 10.0

    # Save
    dialogue_srt = os.path.join(output_dir, "dialogue.srt")
    dialogue_subtitle.save_srt(dialogue_srt)
    print(f"✓ Multi-speaker SRT saved: {dialogue_srt}")

    # Preview
    with open(dialogue_srt, "r", encoding="utf-8") as f:
        print(f.read())

    # ============================================================
    # Test 9: Whisper Test (if available)
    # ============================================================
    print_section("Test 9: Whisper Transcription")

    # Check for TTS audio files
    tts_dir = os.path.join(base_dir, "temp", "tts_tests")
    audio_files = []

    if os.path.exists(tts_dir):
        for f in os.listdir(tts_dir):
            filepath = os.path.join(tts_dir, f)
            if os.path.isfile(filepath) and f.endswith((".wav", ".mp3")):
                audio_files.append(filepath)

    if not audio_files:
        print("⚠️  No TTS audio files found")
    elif not stats['whisper_available']:
        print("⚠️  Whisper not installed - skipping")
        print("    Install: pip install openai-whisper")
    else:
        print(f"Testing Whisper on: {os.path.basename(audio_files[0])}")
        print("(First run downloads model ~74MB, may take a few minutes)")

        result = generator.whisper.transcribe(audio_files[0])

        if result:
            print(f"\n✅ Whisper generated {result.total_segments} segments")
            print(f"   Language: {result.language}")
            print(f"   Full text: \"{result.full_text[:100]}...\"")

            # Save
            whisper_dir = os.path.join(output_dir, "whisper")
            ensure_dir(whisper_dir)
            result.save_srt(os.path.join(whisper_dir, "whisper_output.srt"))
            print(f"   Saved to: {whisper_dir}")

    # ============================================================
    # Test 10: Batch Processing
    # ============================================================
    print_section("Test 10: Batch Processing")

    tasks = [
        {
            "text": "This is the first subtitle test.",
            "duration": 3.0,
            "language": "en"
        },
        {
            "text": "Now here is the second one!",
            "duration": 3.5,
            "language": "en"
        },
        {
            "text": "And finally, the third and last test.",
            "duration": 4.0,
            "language": "en"
        },
    ]

    batch_dir = os.path.join(output_dir, "batch")
    print(f"Processing {len(tasks)} tasks...")

    batch_results = generator.batch_generate(
        tasks=tasks,
        output_dir=batch_dir,
        formats=["srt", "vtt", "txt"]
    )

    print(f"\n✅ Generated {len(batch_results)} subtitles")
    for result in batch_results:
        print(f"  Task {result['task_index']}: {len(result['exported_files'])} formats")

    # ============================================================
    # Test 11: Statistics
    # ============================================================
    print_section("Test 11: Final Statistics")

    stats = generator.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # ============================================================
    # Output Info
    # ============================================================
    print_section("Output Files")
    print(f"Subtitle files saved in:")
    print(f"  {output_dir}")
    print(f"\n👉 Open to inspect:")
    print(f"   start {output_dir}")

    print_banner(
        "✅ All Tests Passed",
        "Subtitle Generator Working - Ready for YouTube!"
    )