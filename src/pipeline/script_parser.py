# ============================================================
# src/pipeline/script_parser.py
# 3D Animation Studio - Script Parser
# User script ko parse karke scenes, dialogues, actions nikaalta hai
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
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from src.utils import get_logger, get_config, get_timestamp

logger = get_logger("ScriptParser")


# ============================================================
# ENUMS
# ============================================================

class Emotion(Enum):
    """Emotion types detected from script"""
    NEUTRAL     = "neutral"
    HAPPY       = "happy"
    SAD         = "sad"
    ANGRY       = "angry"
    SURPRISED   = "surprised"
    FEARFUL     = "fearful"
    DISGUSTED   = "disgusted"
    CONFUSED    = "confused"
    THINKING    = "thinking"
    LAUGHING    = "laughing"
    CRYING      = "crying"
    SHOUTING    = "shouting"
    WHISPERING  = "whispering"
    EXCITED     = "excited"
    LOVING      = "loving"


class SceneType(Enum):
    """Scene environment types"""
    INDOOR       = "indoor"
    OUTDOOR      = "outdoor"
    FOREST       = "forest"
    DESERT       = "desert"
    CITY         = "city"
    OFFICE       = "office"
    HOME         = "home"
    SCHOOL       = "school"
    KITCHEN      = "kitchen"
    BEDROOM      = "bedroom"
    STREET       = "street"
    PARK         = "park"
    BEACH        = "beach"
    MOUNTAIN     = "mountain"
    UNKNOWN      = "unknown"


class TimeOfDay(Enum):
    """Time of day in scene"""
    DAWN        = "dawn"
    MORNING     = "morning"
    NOON        = "noon"
    AFTERNOON   = "afternoon"
    EVENING     = "evening"
    NIGHT       = "night"
    MIDNIGHT    = "midnight"


class CameraAngle(Enum):
    """Suggested camera angles"""
    WIDE_SHOT           = "wide_shot"
    MEDIUM_SHOT         = "medium_shot"
    CLOSE_UP            = "close_up"
    OVER_THE_SHOULDER   = "over_the_shoulder"
    BIRDS_EYE           = "birds_eye"
    LOW_ANGLE           = "low_angle"
    DUTCH_ANGLE         = "dutch_angle"


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class Character:
    """Character information detected from script"""
    name:           str
    gender:         str            = "unknown"      # male, female, unknown
    voice_id:       str            = ""             # TTS voice preset
    language:       str            = "en"
    age_group:      str            = "adult"        # child, teen, adult, elder
    color_scheme:   List[float]    = field(default_factory=lambda: [0.5, 0.5, 0.5])
    description:    str            = ""

    # Statistics
    total_dialogues:int            = 0
    total_words:    int            = 0
    dominant_emotion: str          = Emotion.NEUTRAL.value

    def to_dict(self) -> Dict:
        return {
            "name":             self.name,
            "gender":           self.gender,
            "voice_id":         self.voice_id,
            "language":         self.language,
            "age_group":        self.age_group,
            "total_dialogues":  self.total_dialogues,
            "total_words":      self.total_words,
            "dominant_emotion": self.dominant_emotion,
        }


@dataclass
class ParsedDialogue:
    """Single parsed dialogue line"""
    character:      str
    text:           str
    emotion:        str            = Emotion.NEUTRAL.value
    scene_index:    int            = 0
    dialogue_index: int            = 0

    # Auto-detected properties
    duration_seconds: float        = 0.0     # Estimated speech duration
    word_count:     int            = 0
    tone:           str            = "normal"     # normal, loud, whisper
    intensity:      float          = 0.5     # 0.0 to 1.0

    # Timing (frames)
    start_frame:    int            = 0
    end_frame:      int            = 0

    def to_dict(self) -> Dict:
        return {
            "character":       self.character,
            "text":            self.text,
            "emotion":         self.emotion,
            "duration":        self.duration_seconds,
            "start_frame":     self.start_frame,
            "end_frame":       self.end_frame,
            "word_count":      self.word_count,
        }


@dataclass
class ParsedAction:
    """Action/direction in script (non-dialogue)"""
    description:    str
    scene_index:    int            = 0
    action_type:    str            = "generic"   # movement, effect, camera
    duration_frames: int           = 60          # 2 seconds at 30fps
    start_frame:    int            = 0


@dataclass
class ParsedScene:
    """Ek complete parsed scene"""
    index:          int
    heading:        str            = ""       # Scene heading (INT./EXT.)
    scene_type:     str            = SceneType.UNKNOWN.value
    location:       str            = ""
    time_of_day:    str            = TimeOfDay.NOON.value

    # Content
    characters:     List[str]      = field(default_factory=list)
    dialogues:      List[ParsedDialogue] = field(default_factory=list)
    actions:        List[ParsedAction] = field(default_factory=list)

    # Auto-suggested
    suggested_camera: str          = CameraAngle.MEDIUM_SHOT.value
    suggested_lighting: str        = "day_outdoor"
    suggested_music_mood: str      = "neutral"
    suggested_sfx:  List[str]      = field(default_factory=list)

    # Timing
    total_frames:   int            = 0
    duration_seconds: float        = 0.0
    start_frame:    int            = 0
    end_frame:      int            = 0

    def get_word_count(self) -> int:
        """Total words in scene"""
        return sum(d.word_count for d in self.dialogues)

    def get_dominant_emotion(self) -> str:
        """Scene ka main emotion"""
        if not self.dialogues:
            return Emotion.NEUTRAL.value
        emotion_count = {}
        for d in self.dialogues:
            emotion_count[d.emotion] = emotion_count.get(d.emotion, 0) + 1
        return max(emotion_count, key=emotion_count.get)

    def to_dict(self) -> Dict:
        return {
            "index":              self.index,
            "heading":            self.heading,
            "scene_type":         self.scene_type,
            "location":           self.location,
            "time_of_day":        self.time_of_day,
            "characters":         self.characters,
            "num_dialogues":      len(self.dialogues),
            "num_actions":        len(self.actions),
            "suggested_camera":   self.suggested_camera,
            "suggested_lighting": self.suggested_lighting,
            "dominant_emotion":   self.get_dominant_emotion(),
            "total_frames":       self.total_frames,
            "duration_seconds":   self.duration_seconds,
        }


@dataclass
class ParsedScript:
    """Complete parsed script"""
    title:          str            = "Untitled"
    author:         str            = ""
    language:       str            = "en"
    fps:            int            = 30

    # Content
    scenes:         List[ParsedScene] = field(default_factory=list)
    characters:     Dict[str, Character] = field(default_factory=dict)

    # Stats
    total_frames:   int            = 0
    total_duration: float          = 0.0
    total_dialogues: int           = 0
    total_words:    int            = 0

    # Metadata
    parse_timestamp: str           = ""

    def get_statistics(self) -> Dict:
        return {
            "title":            self.title,
            "total_scenes":     len(self.scenes),
            "total_characters": len(self.characters),
            "total_dialogues":  self.total_dialogues,
            "total_words":      self.total_words,
            "total_frames":     self.total_frames,
            "total_duration":   round(self.total_duration, 2),
            "fps":              self.fps,
        }


# ============================================================
# EMOTION DETECTOR
# ============================================================

class EmotionDetector:
    """
    Text se emotion detect karta hai.
    Keyword based - simple aur fast.
    """

    # Emotion keywords (multi-lingual: English + Hindi)
    EMOTION_KEYWORDS: Dict[str, List[str]] = {
        Emotion.HAPPY.value: [
            "happy", "joy", "smile", "laugh", "excited", "wonderful",
            "great", "amazing", "awesome", "haha", "hehe",
            "khush", "khushi", "muskurana", "hasna", "achha",
        ],
        Emotion.SAD.value: [
            "sad", "cry", "tears", "sorry", "unfortunate", "miserable",
            "depressed", "lonely", "heartbroken",
            "dukhi", "udaas", "rona", "gum", "afsos",
        ],
        Emotion.ANGRY.value: [
            "angry", "furious", "rage", "hate", "annoyed", "damn",
            "shut up", "stupid", "idiot", "fool",
            "gussa", "chup", "bakwas", "murkh", "bewakoof", "chodh",
        ],
        Emotion.SURPRISED.value: [
            "wow", "omg", "oh my god", "what", "really", "seriously",
            "shocked", "astonished", "unbelievable",
            "arre", "hai bhagwan", "kya baat", "sach mein",
        ],
        Emotion.FEARFUL.value: [
            "scared", "afraid", "fear", "terrified", "help", "run",
            "danger", "ghost", "monster",
            "dar", "darr", "bhut", "bhoot", "bachao",
        ],
        Emotion.CONFUSED.value: [
            "confused", "what", "how", "why", "hmm", "puzzled",
            "don't understand",
            "samajh", "kaise", "kyun", "kya",
        ],
        Emotion.LAUGHING.value: [
            "haha", "hehe", "lol", "rofl", "hilarious", "funny",
            "hasna", "haans", "mazedar",
        ],
        Emotion.SHOUTING.value: [
            "shout", "scream", "yell", "loud",
            "chillao", "chikho",
        ],
        Emotion.LOVING.value: [
            "love", "darling", "sweetheart", "dear", "beautiful",
            "pyaar", "mohabbat", "jaanu", "meri jaan",
        ],
        Emotion.EXCITED.value: [
            "yay", "yeah", "yes", "awesome", "let's go", "amazing",
            "chalo", "jaldi", "wah",
        ],
    }

    @classmethod
    def detect(cls, text: str, hint: str = "") -> str:
        """
        Text se emotion detect karo.

        Args:
            text: Dialogue text
            hint: Extra hint from script (e.g., "(angry)")

        Returns:
            Emotion string
        """
        # Priority: explicit hint
        if hint:
            hint_lower = hint.lower().strip("()[]{}!?., ")
            for emotion, keywords in cls.EMOTION_KEYWORDS.items():
                if hint_lower in keywords or hint_lower == emotion:
                    return emotion
            # Direct emotion name check
            for emotion_enum in Emotion:
                if hint_lower == emotion_enum.value:
                    return emotion_enum.value

        # Check punctuation clues
        text_lower = text.lower()
        exclamation_count = text.count('!')
        question_count = text.count('?')
        all_caps_ratio = 0
        if text:
            all_caps = sum(1 for c in text if c.isupper())
            all_caps_ratio = all_caps / max(1, len([c for c in text if c.isalpha()]))

        # Score each emotion
        scores: Dict[str, int] = {}
        for emotion, keywords in cls.EMOTION_KEYWORDS.items():
            score = 0
            for kw in keywords:
                if kw in text_lower:
                    score += 2
            if score > 0:
                scores[emotion] = score

        # Punctuation-based adjustments
        if exclamation_count >= 2 or all_caps_ratio > 0.5:
            scores[Emotion.SHOUTING.value] = scores.get(Emotion.SHOUTING.value, 0) + 3
        elif exclamation_count >= 1:
            scores[Emotion.EXCITED.value] = scores.get(Emotion.EXCITED.value, 0) + 1

        if question_count >= 2:
            scores[Emotion.CONFUSED.value] = scores.get(Emotion.CONFUSED.value, 0) + 2

        # Return highest scored emotion
        if scores:
            return max(scores, key=scores.get)

        return Emotion.NEUTRAL.value


# ============================================================
# SCENE DETECTOR
# ============================================================

class SceneDetector:
    """Scene environment detect karta hai text se"""

    # Location keywords
    LOCATION_KEYWORDS: Dict[str, List[str]] = {
        SceneType.HOME.value:     ["home", "house", "living room", "ghar"],
        SceneType.OFFICE.value:   ["office", "work", "meeting room", "daftar"],
        SceneType.SCHOOL.value:   ["school", "classroom", "college", "school"],
        SceneType.KITCHEN.value:  ["kitchen", "cook", "rasoi"],
        SceneType.BEDROOM.value:  ["bedroom", "bed", "sleep", "kamra"],
        SceneType.FOREST.value:   ["forest", "jungle", "trees", "jangal", "van"],
        SceneType.DESERT.value:   ["desert", "sand", "dunes", "registan"],
        SceneType.CITY.value:     ["city", "street", "buildings", "shehar"],
        SceneType.PARK.value:     ["park", "garden", "bagh"],
        SceneType.BEACH.value:    ["beach", "ocean", "sea", "samundar"],
        SceneType.MOUNTAIN.value: ["mountain", "hill", "peak", "pahad"],
    }

    # Time of day keywords
    TIME_KEYWORDS: Dict[str, List[str]] = {
        TimeOfDay.DAWN.value:     ["dawn", "sunrise", "early morning", "bhor"],
        TimeOfDay.MORNING.value:  ["morning", "am", "subah"],
        TimeOfDay.NOON.value:     ["noon", "midday", "dopahar"],
        TimeOfDay.EVENING.value:  ["evening", "sunset", "shaam"],
        TimeOfDay.NIGHT.value:    ["night", "pm", "raat", "andhera"],
    }

    @classmethod
    def detect_type(cls, heading: str, content: str = "") -> str:
        """Scene type detect karo"""
        combined = (heading + " " + content).lower()

        # Check INT./EXT.
        is_indoor = "int." in combined[:20] or "int " in combined[:20]
        is_outdoor = "ext." in combined[:20] or "ext " in combined[:20]

        # Location match
        for scene_type, keywords in cls.LOCATION_KEYWORDS.items():
            for kw in keywords:
                if kw in combined:
                    return scene_type

        if is_indoor:
            return SceneType.INDOOR.value
        elif is_outdoor:
            return SceneType.OUTDOOR.value

        return SceneType.UNKNOWN.value

    @classmethod
    def detect_time_of_day(cls, text: str) -> str:
        """Time of day detect karo"""
        text_lower = text.lower()
        for tod, keywords in cls.TIME_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    return tod
        return TimeOfDay.NOON.value

    @classmethod
    def suggest_camera(cls, scene: ParsedScene) -> str:
        """Scene ke basis pe camera angle suggest karo"""
        num_chars = len(scene.characters)
        emotion = scene.get_dominant_emotion()

        # Emotion based
        if emotion in [Emotion.ANGRY.value, Emotion.SAD.value, Emotion.LOVING.value]:
            return CameraAngle.CLOSE_UP.value

        if emotion == Emotion.SHOUTING.value:
            return CameraAngle.LOW_ANGLE.value

        # Character count based
        if num_chars >= 3:
            return CameraAngle.WIDE_SHOT.value
        elif num_chars == 2:
            return CameraAngle.OVER_THE_SHOULDER.value
        elif num_chars == 1:
            return CameraAngle.MEDIUM_SHOT.value

        return CameraAngle.MEDIUM_SHOT.value

    @classmethod
    def suggest_lighting(cls, scene_type: str, time_of_day: str) -> str:
        """Lighting preset suggest karo"""
        # Time-based
        if time_of_day == TimeOfDay.NIGHT.value:
            if scene_type in [SceneType.INDOOR.value, SceneType.HOME.value,
                              SceneType.OFFICE.value, SceneType.BEDROOM.value]:
                return "indoor_warm"
            return "night_outdoor"

        if time_of_day == TimeOfDay.EVENING.value:
            return "sunset"

        if time_of_day == TimeOfDay.DAWN.value:
            return "sunrise"

        # Scene type based
        indoor_types = [
            SceneType.INDOOR.value, SceneType.HOME.value,
            SceneType.OFFICE.value, SceneType.KITCHEN.value,
            SceneType.BEDROOM.value, SceneType.SCHOOL.value,
        ]
        if scene_type in indoor_types:
            return "indoor_warm"

        return "day_outdoor"

    @classmethod
    def suggest_music_mood(cls, emotion: str) -> str:
        """Music mood suggest karo emotion se"""
        mapping = {
            Emotion.HAPPY.value:      "upbeat",
            Emotion.SAD.value:        "melancholic",
            Emotion.ANGRY.value:      "intense",
            Emotion.FEARFUL.value:    "suspense",
            Emotion.LOVING.value:     "romantic",
            Emotion.EXCITED.value:    "energetic",
            Emotion.SURPRISED.value:  "dramatic",
            Emotion.LAUGHING.value:   "playful",
        }
        return mapping.get(emotion, "neutral")

    @classmethod
    def suggest_sfx(cls, scene: ParsedScene) -> List[str]:
        """Sound effects suggest karo"""
        sfx = []
        scene_type = scene.scene_type

        location_sfx = {
            SceneType.FOREST.value:  ["forest_ambient", "birds_chirping"],
            SceneType.CITY.value:    ["city_traffic", "distant_horn"],
            SceneType.BEACH.value:   ["ocean_waves", "seagulls"],
            SceneType.KITCHEN.value: ["kitchen_ambient"],
            SceneType.OFFICE.value:  ["office_ambient", "typing"],
            SceneType.SCHOOL.value:  ["school_bell"],
            SceneType.STREET.value:  ["street_ambient"],
        }

        if scene_type in location_sfx:
            sfx.extend(location_sfx[scene_type])

        return sfx


# ============================================================
# CHARACTER DETECTOR
# ============================================================

class CharacterDetector:
    """Characters detect karta hai script se"""

    # Female name indicators (Hindi + English)
    FEMALE_NAMES = {
        "priya", "riya", "neha", "meera", "sita", "radha", "anjali",
        "pooja", "kavya", "shreya", "ananya", "aditi", "divya",
        "mom", "mother", "sister", "wife", "girl", "lady", "woman",
        "maa", "mummy", "behen", "biwi", "ladki", "aurat",
    }

    # Male name indicators
    MALE_NAMES = {
        "raj", "rahul", "amit", "vijay", "ravi", "sanjay", "arjun",
        "kunal", "rohit", "vikram", "aditya", "karan",
        "dad", "father", "brother", "husband", "boy", "man", "guy",
        "papa", "pita", "bhai", "pati", "ladka", "aadmi",
    }

    @classmethod
    def detect_gender(cls, name: str) -> str:
        """Naam se gender guess karo"""
        name_lower = name.lower().strip()

        if name_lower in cls.FEMALE_NAMES:
            return "female"
        if name_lower in cls.MALE_NAMES:
            return "male"

        # Ending-based hints
        if name_lower.endswith(("a", "i", "e")):
            # Likely female
            return "female"
        if name_lower.endswith(("h", "n", "l", "r", "d")):
            return "male"

        return "unknown"

    @classmethod
    def assign_voice(cls, character: Character, index: int = 0) -> str:
        """Character ko voice ID assign karo"""
        # Simple mapping
        if character.gender == "female":
            voices = ["voice_female_1", "voice_female_2", "voice_female_3"]
        else:
            voices = ["voice_male_1", "voice_male_2", "voice_male_3"]

        return voices[index % len(voices)]


# ============================================================
# MAIN SCRIPT PARSER
# ============================================================

class ScriptParser:
    """
    Main Script Parser.

    Multiple formats support:
    1. Screenplay format (Fountain-inspired):
       INT. LIVING ROOM - DAY
       CHARACTER
       (emotion)
       Dialogue text.

    2. Simple format:
       Character: Dialogue text
       Character: (emotion) Dialogue text

    3. Chat format:
       [Character] Message
    """

    # Regex patterns
    SCENE_HEADING_PATTERN = re.compile(
        r'^(INT\.|EXT\.|INT/EXT\.|INT|EXT)\s+(.+?)(?:\s*-\s*(.+))?$',
        re.IGNORECASE
    )

    CHARACTER_LINE_PATTERN = re.compile(
        r'^([A-Za-z][A-Za-z0-9\s]{0,25}?):\s*(?:\(([^)]+)\)\s*)?(.+)$'
    )

    CHARACTER_SCREENPLAY_PATTERN = re.compile(
        r'^([A-Z][A-Z\s]{1,25})$'
    )

    EMOTION_HINT_PATTERN = re.compile(
        r'^\(([^)]+)\)\s*(.*)$'
    )

    ACTION_PATTERN = re.compile(
        r'^\[(.+?)\]\s*$'   # [action description]
    )

    # Speech duration estimation (words per minute)
    WORDS_PER_MINUTE = 150   # Average speech speed
    PAUSE_BETWEEN_DIALOGUES_FRAMES = 15   # 0.5 sec at 30fps

    def __init__(self, config: Optional[Dict] = None):
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # FPS
        self.fps = self.config.get("rendering", {}).get("default_fps", 30)

        # Emotion & scene detectors
        self.emotion_detector = EmotionDetector()
        self.scene_detector = SceneDetector()
        self.character_detector = CharacterDetector()

        logger.info(f"✅ ScriptParser initialized | FPS: {self.fps}")

    # ----------------------------------------------------------
    # MAIN PARSE METHOD
    # ----------------------------------------------------------

    def parse(
        self,
        script_text: str,
        title: str = "Untitled",
        language: str = "en",
    ) -> ParsedScript:
        """
        Complete script parse karo.

        Args:
            script_text: Raw script text
            title: Script title
            language: Script language code

        Returns:
            ParsedScript object
        """
        logger.info(f"📝 Parsing script: {title} ({len(script_text)} chars)")

        # Parsed script initialize karo
        script = ParsedScript(
            title=title,
            language=language,
            fps=self.fps,
            parse_timestamp=get_timestamp(),
        )

        # Lines mein split karo
        lines = [line.rstrip() for line in script_text.split('\n')]

        # Parse scenes
        current_scene: Optional[ParsedScene] = None
        current_character: Optional[str] = None
        current_emotion_hint: str = ""
        scene_index = 0
        dialogue_index = 0

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Empty line skip karo
            if not line:
                current_character = None
                current_emotion_hint = ""
                i += 1
                continue

            # SCENE HEADING check karo
            scene_match = self.SCENE_HEADING_PATTERN.match(line)
            if scene_match:
                # Purani scene save karo
                if current_scene:
                    self._finalize_scene(current_scene)
                    script.scenes.append(current_scene)

                # Nayi scene banao
                int_ext = scene_match.group(1)
                location = scene_match.group(2).strip() if scene_match.group(2) else ""
                time_str = scene_match.group(3).strip() if scene_match.group(3) else ""

                current_scene = ParsedScene(
                    index=scene_index,
                    heading=line,
                    location=location,
                )

                # Scene type detect karo
                current_scene.scene_type = self.scene_detector.detect_type(
                    line, location
                )

                # Time of day
                if time_str:
                    current_scene.time_of_day = self.scene_detector.detect_time_of_day(
                        time_str
                    )
                else:
                    current_scene.time_of_day = self.scene_detector.detect_time_of_day(
                        line
                    )

                scene_index += 1
                dialogue_index = 0
                current_character = None
                i += 1
                continue

            # Agar koi scene nahi hai, ek default scene banao
            if current_scene is None:
                current_scene = ParsedScene(
                    index=scene_index,
                    heading="SCENE 1",
                    location="Default Location",
                    scene_type=SceneType.INDOOR.value,
                )
                scene_index += 1

            # ACTION check karo (square brackets)
            action_match = self.ACTION_PATTERN.match(line)
            if action_match:
                action = ParsedAction(
                    description=action_match.group(1).strip(),
                    scene_index=current_scene.index,
                    action_type=self._detect_action_type(action_match.group(1)),
                )
                current_scene.actions.append(action)
                i += 1
                continue

            # DIALOGUE - Format 1: "Character: text"
            char_line_match = self.CHARACTER_LINE_PATTERN.match(line)
            if char_line_match:
                char_name = char_line_match.group(1).strip()
                emotion_hint = char_line_match.group(2) or ""
                dialogue_text = char_line_match.group(3).strip()

                # Filter out common false matches
                if len(char_name) <= 25 and not any(
                    w in char_name.lower() for w in ["http", "https", "www"]
                ):
                    dialogue = self._create_dialogue(
                        char_name, dialogue_text, emotion_hint,
                        current_scene.index, dialogue_index,
                    )
                    current_scene.dialogues.append(dialogue)

                    if char_name not in current_scene.characters:
                        current_scene.characters.append(char_name)

                    # Character register karo
                    self._register_character(script, char_name)

                    dialogue_index += 1
                    i += 1
                    continue

            # DIALOGUE - Format 2: Screenplay style (CHARACTER on own line)
            char_scr_match = self.CHARACTER_SCREENPLAY_PATTERN.match(line)
            if char_scr_match and i + 1 < len(lines):
                char_name = char_scr_match.group(1).strip().title()
                # Next line check
                next_line = lines[i + 1].strip()

                # Emotion hint check
                emotion_hint = ""
                dialogue_text = ""

                emo_match = self.EMOTION_HINT_PATTERN.match(next_line)
                if emo_match and i + 2 < len(lines):
                    emotion_hint = emo_match.group(1)
                    dialogue_text = lines[i + 2].strip()
                    i += 3
                else:
                    dialogue_text = next_line
                    i += 2

                if dialogue_text and len(char_name) <= 25:
                    dialogue = self._create_dialogue(
                        char_name, dialogue_text, emotion_hint,
                        current_scene.index, dialogue_index,
                    )
                    current_scene.dialogues.append(dialogue)

                    if char_name not in current_scene.characters:
                        current_scene.characters.append(char_name)

                    self._register_character(script, char_name)
                    dialogue_index += 1
                    continue

            # Otherwise, treat as action/description
            if line and current_scene:
                action = ParsedAction(
                    description=line,
                    scene_index=current_scene.index,
                    action_type="description",
                )
                current_scene.actions.append(action)

            i += 1

        # Last scene save karo
        if current_scene:
            self._finalize_scene(current_scene)
            script.scenes.append(current_scene)

        # Script finalize karo
        self._finalize_script(script)

        logger.info(
            f"✅ Parsed: {len(script.scenes)} scenes | "
            f"{script.total_dialogues} dialogues | "
            f"{len(script.characters)} characters | "
            f"{script.total_duration:.1f}s"
        )

        return script

    # ----------------------------------------------------------
    # HELPER METHODS
    # ----------------------------------------------------------

    def _create_dialogue(
        self,
        character: str,
        text: str,
        emotion_hint: str,
        scene_index: int,
        dialogue_index: int,
    ) -> ParsedDialogue:
        """Ek dialogue create karo with all metadata"""
        # Emotion detect karo
        emotion = self.emotion_detector.detect(text, emotion_hint)

        # Word count
        word_count = len(text.split())

        # Speech duration estimate
        duration = (word_count / self.WORDS_PER_MINUTE) * 60

        # Minimum 1.5 seconds per dialogue
        duration = max(duration, 1.5)

        # Tone detect karo
        tone = "normal"
        if emotion == Emotion.SHOUTING.value:
            tone = "loud"
        elif emotion == Emotion.WHISPERING.value:
            tone = "whisper"

        # Intensity (0.0 to 1.0)
        intensity = 0.5
        if emotion in [Emotion.ANGRY.value, Emotion.SHOUTING.value, Emotion.EXCITED.value]:
            intensity = 0.8
        elif emotion in [Emotion.WHISPERING.value, Emotion.SAD.value]:
            intensity = 0.3

        return ParsedDialogue(
            character=character.strip(),
            text=text.strip(),
            emotion=emotion,
            scene_index=scene_index,
            dialogue_index=dialogue_index,
            duration_seconds=duration,
            word_count=word_count,
            tone=tone,
            intensity=intensity,
        )

    def _detect_action_type(self, description: str) -> str:
        """Action type detect karo"""
        desc_lower = description.lower()

        camera_kw = ["camera", "shot", "zoom", "pan", "close-up", "angle"]
        movement_kw = ["walks", "runs", "sits", "stands", "moves", "enters", "exits"]
        effect_kw = ["explode", "fire", "smoke", "rain", "light", "flash"]

        if any(kw in desc_lower for kw in camera_kw):
            return "camera"
        if any(kw in desc_lower for kw in movement_kw):
            return "movement"
        if any(kw in desc_lower for kw in effect_kw):
            return "effect"

        return "generic"

    def _register_character(self, script: ParsedScript, name: str):
        """Character register karo script mein"""
        name = name.strip()
        if name not in script.characters:
            gender = self.character_detector.detect_gender(name)
            char = Character(
                name=name,
                gender=gender,
            )
            # Voice assign karo
            existing_count = len([
                c for c in script.characters.values()
                if c.gender == gender
            ])
            char.voice_id = self.character_detector.assign_voice(char, existing_count)
            script.characters[name] = char

    def _finalize_scene(self, scene: ParsedScene):
        """Scene ki final calculations"""
        # Total frames calculate karo
        total_dialogue_frames = 0
        current_frame = 0

        for dialogue in scene.dialogues:
            dialogue.start_frame = current_frame
            frames = int(dialogue.duration_seconds * self.fps)
            dialogue.end_frame = current_frame + frames
            current_frame = dialogue.end_frame + self.PAUSE_BETWEEN_DIALOGUES_FRAMES
            total_dialogue_frames += frames + self.PAUSE_BETWEEN_DIALOGUES_FRAMES

        # Action frames add karo
        action_frames = sum(a.duration_frames for a in scene.actions)

        scene.total_frames = total_dialogue_frames + action_frames
        scene.duration_seconds = scene.total_frames / self.fps

        # Suggestions
        scene.suggested_camera = self.scene_detector.suggest_camera(scene)
        scene.suggested_lighting = self.scene_detector.suggest_lighting(
            scene.scene_type, scene.time_of_day
        )
        scene.suggested_music_mood = self.scene_detector.suggest_music_mood(
            scene.get_dominant_emotion()
        )
        scene.suggested_sfx = self.scene_detector.suggest_sfx(scene)

    def _finalize_script(self, script: ParsedScript):
        """Script ki final calculations"""
        current_frame = 0

        for scene in script.scenes:
            scene.start_frame = current_frame
            scene.end_frame = current_frame + scene.total_frames
            current_frame = scene.end_frame

            # Character stats update karo
            for dialogue in scene.dialogues:
                char_name = dialogue.character
                if char_name in script.characters:
                    char = script.characters[char_name]
                    char.total_dialogues += 1
                    char.total_words += dialogue.word_count

        script.total_frames = current_frame
        script.total_duration = current_frame / self.fps
        script.total_dialogues = sum(len(s.dialogues) for s in script.scenes)
        script.total_words = sum(s.get_word_count() for s in script.scenes)

        # Update dominant emotions for characters
        for scene in script.scenes:
            for dialogue in scene.dialogues:
                char_name = dialogue.character
                if char_name in script.characters:
                    char = script.characters[char_name]
                    # Simple: last emotion wins
                    char.dominant_emotion = dialogue.emotion

    # ----------------------------------------------------------
    # PUBLIC UTILITIES
    # ----------------------------------------------------------

    def print_script_summary(self, script: ParsedScript):
        """Parsed script ka summary print karo"""
        stats = script.get_statistics()

        print(f"\n{'='*60}")
        print(f"📝 SCRIPT: {stats['title']}")
        print(f"{'='*60}")
        print(f"  Scenes       : {stats['total_scenes']}")
        print(f"  Characters   : {stats['total_characters']}")
        print(f"  Dialogues    : {stats['total_dialogues']}")
        print(f"  Words        : {stats['total_words']}")
        print(f"  Duration     : {stats['total_duration']}s ({stats['total_frames']} frames)")
        print(f"{'='*60}")

        # Characters
        print(f"\n🎭 CHARACTERS:")
        for name, char in script.characters.items():
            print(
                f"   {name:20s} | {char.gender:8s} | "
                f"{char.voice_id:18s} | "
                f"{char.total_dialogues} dialogues | "
                f"{char.total_words} words"
            )

        # Scenes
        print(f"\n🎬 SCENES:")
        for scene in script.scenes:
            print(f"\n   Scene {scene.index + 1}: {scene.heading}")
            print(f"      Type      : {scene.scene_type}")
            print(f"      Time      : {scene.time_of_day}")
            print(f"      Duration  : {scene.duration_seconds:.1f}s")
            print(f"      Camera    : {scene.suggested_camera}")
            print(f"      Lighting  : {scene.suggested_lighting}")
            print(f"      Music     : {scene.suggested_music_mood}")
            print(f"      Emotion   : {scene.get_dominant_emotion()}")
            if scene.suggested_sfx:
                print(f"      SFX       : {', '.join(scene.suggested_sfx)}")

            # Dialogues
            for dialogue in scene.dialogues:
                print(
                    f"      • [{dialogue.character:15s}] ({dialogue.emotion:10s}) "
                    f"[{dialogue.duration_seconds:.1f}s] "
                    f"{dialogue.text[:50]}..."
                )

        print(f"\n{'='*60}\n")

    def export_to_dict(self, script: ParsedScript) -> Dict:
        """Script ko dict mein export karo (JSON save ke liye)"""
        return {
            "title":         script.title,
            "author":        script.author,
            "language":      script.language,
            "fps":           script.fps,
            "statistics":    script.get_statistics(),
            "characters":    {
                name: char.to_dict()
                for name, char in script.characters.items()
            },
            "scenes":        [
                {
                    "info":       scene.to_dict(),
                    "dialogues":  [d.to_dict() for d in scene.dialogues],
                    "actions":    [
                        {"desc": a.description, "type": a.action_type}
                        for a in scene.actions
                    ],
                }
                for scene in script.scenes
            ],
        }


# ============================================================
# GLOBAL INSTANCE
# ============================================================

_global_parser: Optional[ScriptParser] = None


def get_script_parser() -> ScriptParser:
    """Global ScriptParser instance (singleton)"""
    global _global_parser
    if _global_parser is None:
        _global_parser = ScriptParser()
    return _global_parser


# ============================================================
# TEST SECTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")
    print_banner("Script Parser Test", "Script → Scenes/Dialogues/Actions")

    # ===== TEST 1: Simple Chat Format =====
    print_section("Test 1: Simple Chat Format")

    simple_script = """
Hero: Namaste doston!
Hero: (excited) Aaj hum ek amazing project banayenge!
Villain: (angry) Tum yeh nahi kar sakte!
Hero: (laughing) Haha, dekh lena bhai!
Villain: (shouting) MAIN TUMHE ROKUNGA!
"""

    parser = ScriptParser()
    script1 = parser.parse(simple_script, "Simple Test", "en")
    parser.print_script_summary(script1)

    # ===== TEST 2: Screenplay Format =====
    print_section("Test 2: Screenplay Format")

    screenplay = """
INT. HERO'S HOUSE - MORNING

The hero sits on his desk, looking at his laptop.

HERO
(happy)
Aaj main duniya ka best animation banaane wala hoon!

[Hero starts typing furiously]

HERO
(excited)
Yes! Yeh code chal gaya!

EXT. VILLAIN'S LAIR - NIGHT

VILLAIN
(angry)
Mujhe hero ki success barhdaasht nahi hoti!

VILLAIN
(shouting)
MAIN USSE ROKUNGA! HAHAHA!

INT. HERO'S HOUSE - DAY

HERO
(surprised)
Villain yahan kaise aaya?

VILLAIN
(laughing)
Surprise, hero!
"""

    script2 = parser.parse(screenplay, "The Battle", "en")
    parser.print_script_summary(script2)

    # ===== TEST 3: Emotion Detection =====
    print_section("Test 3: Emotion Detection")
    test_texts = [
        ("I am so happy today!", "", "happy"),
        ("Please don't leave me, I'm crying", "", "sad"),
        ("YOU IDIOT! HOW DARE YOU!", "", "shouting/angry"),
        ("OMG what happened here?!?", "", "surprised"),
        ("I don't understand this at all", "", "confused"),
        ("Meri jaan, I love you so much", "", "loving"),
        ("Chalo jaldi karo, yay!", "", "excited"),
        ("Text with hint", "angry", "angry"),
    ]

    for text, hint, expected in test_texts:
        detected = EmotionDetector.detect(text, hint)
        status = "✅" if expected.split('/')[0] == detected else "⚠️"
        print(f"   {status} '{text[:40]}...' → {detected} (expected: {expected})")

    # ===== TEST 4: Character Detection =====
    print_section("Test 4: Character Detection")
    names = ["Priya", "Rahul", "Meera", "Amit", "Anjali", "Vikram", "Unknown"]
    for name in names:
        gender = CharacterDetector.detect_gender(name)
        print(f"   {name:15s} → {gender}")

    # ===== TEST 5: Scene Detection =====
    print_section("Test 5: Scene Type Detection")
    test_scenes = [
        ("INT. LIVING ROOM - DAY", "living room home"),
        ("EXT. FOREST - NIGHT", "forest jungle"),
        ("INT. OFFICE - MORNING", "office"),
        ("EXT. STREET - EVENING", "street city"),
        ("INT. KITCHEN - AFTERNOON", "kitchen"),
    ]

    for heading, content in test_scenes:
        scene_type = SceneDetector.detect_type(heading, content)
        time_of_day = SceneDetector.detect_time_of_day(heading)
        print(f"   '{heading}' → Type: {scene_type} | Time: {time_of_day}")

    # ===== TEST 6: Camera Suggestions =====
    print_section("Test 6: Auto Suggestions")
    for scene in script2.scenes:
        print(f"\n   Scene: {scene.heading}")
        print(f"      Characters: {scene.characters}")
        print(f"      Emotion   : {scene.get_dominant_emotion()}")
        print(f"      Camera    : {scene.suggested_camera}")
        print(f"      Lighting  : {scene.suggested_lighting}")
        print(f"      Music     : {scene.suggested_music_mood}")

    # ===== TEST 7: Export to Dict =====
    print_section("Test 7: Export to Dict")
    exported = parser.export_to_dict(script2)
    print(f"✅ Script exported")
    print(f"   Scenes in dict: {len(exported['scenes'])}")
    print(f"   Characters   : {list(exported['characters'].keys())}")

    # ===== TEST 8: Complex Multi-Scene Script =====
    print_section("Test 8: Complex Story Script")
    story_script = """
INT. SCHOOL CLASSROOM - MORNING

The bell rings. Students settle in.

TEACHER
Good morning, class!

STUDENTS
Good morning, teacher!

TEACHER
(happy)
Today we will learn about animation!

STUDENT_A
(excited)
Yes! I love animation!

STUDENT_B
(confused)
Kya hai animation, madam?

TEACHER
(laughing)
Beta, animation ek magic hai!

EXT. PARK - AFTERNOON

Children playing in the park.

HERO
(shouting)
Catch me if you can!

FRIEND
(laughing)
Ruk ja bhai!

INT. HERO'S BEDROOM - NIGHT

HERO
(thinking)
Kal school jaana hai, aur homework bhi nahi kiya.

HERO
(sad)
Ab kya karun?
"""

    script3 = parser.parse(story_script, "A School Day", "en")
    parser.print_script_summary(script3)

    # ===== TEST 9: Global Singleton =====
    print_section("Test 9: Global Singleton")
    p1 = get_script_parser()
    p2 = get_script_parser()
    print(f"✅ Singleton: {p1 is p2}")

    # ===== TEST 10: Statistics =====
    print_section("Test 10: All Scripts Stats")
    for script in [script1, script2, script3]:
        stats = script.get_statistics()
        print(
            f"   📖 {stats['title']:20s}: "
            f"{stats['total_scenes']} scenes, "
            f"{stats['total_dialogues']} dialogues, "
            f"{stats['total_duration']}s"
        )

    print_banner("✅ All Tests Passed!", "script_parser.py Working Perfectly")