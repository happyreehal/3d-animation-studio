# ============================================================
# src/ai/voice_profiles.py
# Voice Profile System - Different voices per character
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

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

from src.utils import get_logger

logger = get_logger("VoiceProfiles")


# ============================================================
# ENUMS
# ============================================================

class Gender(Enum):
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"


class AgeGroup(Enum):
    CHILD = "child"        # 5-12
    YOUNG = "young"        # 13-25
    ADULT = "adult"        # 26-50
    OLD = "old"            # 50+


class VoiceStyle(Enum):
    NORMAL = "normal"
    DEEP = "deep"
    HIGH_PITCH = "high"
    ROBOTIC = "robotic"
    ECHOING = "echoing"


# ============================================================
# VOICE PROFILE
# ============================================================

@dataclass
class VoiceProfile:
    """Character voice profile"""
    
    # Identity
    name: str = "Default"
    description: str = ""
    
    # Voice characteristics
    gender: Gender = Gender.NEUTRAL
    age_group: AgeGroup = AgeGroup.ADULT
    style: VoiceStyle = VoiceStyle.NORMAL
    
    # TTS settings
    language: str = "hi"        # hi, en, etc.
    tld: str = "co.in"          # co.in, co.uk, us, com.au
    speed: bool = False         # False=normal, True=slow
    
    # Audio processing (for post-generation)
    pitch_shift: float = 0.0    # -5 to +5 semitones
    speed_multiplier: float = 1.0  # 0.5 to 2.0
    volume_boost: float = 1.0   # 0.5 to 2.0
    
    # Metadata
    emoji: str = "🎙️"


# ============================================================
# PRESET PROFILES
# ============================================================

PRESET_VOICES: Dict[str, VoiceProfile] = {
    
    # ========== HEROES ==========
    "HERO": VoiceProfile(
        name="Hero (Male Indian)",
        description="Young confident male, Indian accent",
        gender=Gender.MALE,
        age_group=AgeGroup.YOUNG,
        style=VoiceStyle.NORMAL,
        language="hi",
        tld="co.in",
        speed=False,
        pitch_shift=-1.0,      # Slightly deeper
        speed_multiplier=1.0,
        emoji="🦸",
    ),
    
    "HEROINE": VoiceProfile(
        name="Heroine (Female Indian)",
        description="Young female, Indian accent, warm",
        gender=Gender.FEMALE,
        age_group=AgeGroup.YOUNG,
        style=VoiceStyle.NORMAL,
        language="hi",
        tld="co.in",
        speed=False,
        pitch_shift=1.5,       # Slightly higher
        speed_multiplier=1.05,
        emoji="🦸‍♀️",
    ),
    
    # ========== VILLAINS ==========
    "VILLAIN": VoiceProfile(
        name="Villain (Deep Male)",
        description="Deep menacing male voice",
        gender=Gender.MALE,
        age_group=AgeGroup.ADULT,
        style=VoiceStyle.DEEP,
        language="hi",
        tld="co.uk",
        speed=False,
        pitch_shift=-3.0,      # Much deeper
        speed_multiplier=0.9,  # Slightly slower
        emoji="🦹",
    ),
    
    "DARK_LORD": VoiceProfile(
        name="Dark Lord (Very Deep)",
        description="Ancient evil voice",
        gender=Gender.MALE,
        age_group=AgeGroup.OLD,
        style=VoiceStyle.DEEP,
        language="hi",
        tld="co.uk",
        speed=False,
        pitch_shift=-5.0,      # Very deep
        speed_multiplier=0.85,
        emoji="👹",
    ),
    
    # ========== CHILDREN ==========
    "CHILD": VoiceProfile(
        name="Child (High Pitch)",
        description="Young child voice",
        gender=Gender.NEUTRAL,
        age_group=AgeGroup.CHILD,
        style=VoiceStyle.HIGH_PITCH,
        language="hi",
        tld="co.in",
        speed=False,
        pitch_shift=4.0,       # Very high
        speed_multiplier=1.1,  # Faster
        emoji="👶",
    ),
    
    "BOY": VoiceProfile(
        name="Boy (Young Male)",
        description="Young boy voice",
        gender=Gender.MALE,
        age_group=AgeGroup.CHILD,
        style=VoiceStyle.NORMAL,
        language="hi",
        tld="co.in",
        speed=False,
        pitch_shift=2.5,
        speed_multiplier=1.05,
        emoji="👦",
    ),
    
    "GIRL": VoiceProfile(
        name="Girl (Young Female)",
        description="Young girl voice",
        gender=Gender.FEMALE,
        age_group=AgeGroup.CHILD,
        style=VoiceStyle.HIGH_PITCH,
        language="hi",
        tld="co.in",
        speed=False,
        pitch_shift=3.5,
        speed_multiplier=1.05,
        emoji="👧",
    ),
    
    # ========== ELDERS ==========
    "OLD_MAN": VoiceProfile(
        name="Old Man (Wise)",
        description="Elderly wise male voice",
        gender=Gender.MALE,
        age_group=AgeGroup.OLD,
        style=VoiceStyle.DEEP,
        language="hi",
        tld="co.uk",
        speed=True,            # Slower
        pitch_shift=-1.5,
        speed_multiplier=0.85,
        emoji="👴",
    ),
    
    "OLD_WOMAN": VoiceProfile(
        name="Old Woman (Grandmother)",
        description="Elderly female voice",
        gender=Gender.FEMALE,
        age_group=AgeGroup.OLD,
        style=VoiceStyle.NORMAL,
        language="hi",
        tld="co.in",
        speed=True,
        pitch_shift=0.5,
        speed_multiplier=0.9,
        emoji="👵",
    ),
    
    # ========== SPECIAL ==========
    "NARRATOR": VoiceProfile(
        name="Narrator (Storyteller)",
        description="Calm, deep, storytelling voice",
        gender=Gender.MALE,
        age_group=AgeGroup.ADULT,
        style=VoiceStyle.NORMAL,
        language="hi",
        tld="com.au",          # Australian - unique tone
        speed=False,
        pitch_shift=-1.0,
        speed_multiplier=0.95,
        emoji="📖",
    ),
    
    "ROBOT": VoiceProfile(
        name="Robot (Mechanical)",
        description="Robotic monotone voice",
        gender=Gender.NEUTRAL,
        age_group=AgeGroup.ADULT,
        style=VoiceStyle.ROBOTIC,
        language="en",
        tld="us",
        speed=False,
        pitch_shift=0.0,
        speed_multiplier=1.0,
        emoji="🤖",
    ),
    
    "GHOST": VoiceProfile(
        name="Ghost (Ethereal)",
        description="Ghostly ethereal voice",
        gender=Gender.NEUTRAL,
        age_group=AgeGroup.ADULT,
        style=VoiceStyle.ECHOING,
        language="hi",
        tld="co.uk",
        speed=True,
        pitch_shift=-2.0,
        speed_multiplier=0.8,
        emoji="👻",
    ),
    
    "TEACHER": VoiceProfile(
        name="Teacher (Professional)",
        description="Clear professional voice",
        gender=Gender.FEMALE,
        age_group=AgeGroup.ADULT,
        style=VoiceStyle.NORMAL,
        language="hi",
        tld="co.in",
        speed=False,
        pitch_shift=0.0,
        speed_multiplier=1.0,
        emoji="👩‍🏫",
    ),
    
    "BOSS": VoiceProfile(
        name="Boss (Authoritative)",
        description="Strong authoritative voice",
        gender=Gender.MALE,
        age_group=AgeGroup.ADULT,
        style=VoiceStyle.NORMAL,
        language="hi",
        tld="us",
        speed=False,
        pitch_shift=-2.0,
        speed_multiplier=0.95,
        emoji="💼",
    ),
}


# ============================================================
# CHARACTER NAME MATCHING
# ============================================================

# Common character name variations
CHARACTER_ALIASES = {
    # Heroes
    "HERO": ["HERO", "PROTAGONIST", "MAIN", "PROTAGONIST"],
    "HEROINE": ["HEROINE", "LEAD_GIRL", "LEAD_FEMALE"],
    
    # Villains
    "VILLAIN": ["VILLAIN", "ANTAGONIST", "BAD_GUY", "ENEMY", "ANTI"],
    "DARK_LORD": ["DARK_LORD", "DEMON_KING", "EVIL"],
    
    # Children
    "CHILD": ["CHILD", "KID", "BACCHA", "BACCHI"],
    "BOY": ["BOY", "LADKA", "STUDENT"],
    "GIRL": ["GIRL", "LADKI"],
    
    # Elders
    "OLD_MAN": ["OLD_MAN", "GRANDPA", "DADA", "DADAJI", "ELDER", "BUDHA", "NANA"],
    "OLD_WOMAN": ["OLD_WOMAN", "GRANDMA", "DADI", "NANI", "BUDHI"],
    
    # Special
    "NARRATOR": ["NARRATOR", "STORYTELLER", "VOICE"],
    "ROBOT": ["ROBOT", "AI", "MACHINE", "COMPUTER"],
    "GHOST": ["GHOST", "SPIRIT", "BHOOT"],
    "TEACHER": ["TEACHER", "GURU", "PROFESSOR", "MAAM", "SIR"],
    "BOSS": ["BOSS", "MANAGER", "CEO", "OWNER"],
}


def find_voice_profile(character_name: str) -> VoiceProfile:
    """
    Character name se voice profile match karo
    Better detection with common Indian names
    """
    if not character_name:
        return PRESET_VOICES["HERO"]
    
    upper_name = character_name.upper().replace(" ", "_")
    
    # Direct match
    if upper_name in PRESET_VOICES:
        return PRESET_VOICES[upper_name]
    
    # Alias match
    for canonical, aliases in CHARACTER_ALIASES.items():
        for alias in aliases:
            if alias in upper_name:
                return PRESET_VOICES.get(canonical, PRESET_VOICES["HERO"])
    
    # Partial match
    for name in PRESET_VOICES:
        if name in upper_name or upper_name in name:
            return PRESET_VOICES[name]
    
    # ========== SMART GENDER DETECTION ==========
    
    # Female name endings/patterns
    female_indicators = [
        "SITA", "GITA", "RITA", "MITA", "NITA", "GITU",
        "PRIYA", "MAYA", "KAYA", "TARA", "NEHA", "REKHA",
        "MEENA", "TEENA", "REENA", "BEENA", "SHEENA",
        "DEVI", "MATA", "MAA", "AUNTIE", "AUNTY", "DIDI",
        "BEHEN", "BEHAN", "BAHU", "PATNI", "WIFE",
        "PRINCESS", "QUEEN", "RANI", "MADAM", "MADAAM",
        "LATA", "SITA", "KAVITA", "SANGEETA", "SUNITA",
    ]
    
    # Male name endings/patterns  
    male_indicators = [
        "KUMAR", "SINGH", "SHARMA", "GUPTA", "VERMA",
        "RAJ", "RAM", "SHYAM", "RAJU", "MUNNA", "CHOTU",
        "BHAI", "BHAIYA", "PAPA", "PITA", "UNCLE", "CHACHA",
        "MAMA", "TAU", "DADA", "NANA", "BABA", "PATI",
        "HUSBAND", "PRINCE", "KING", "RAJA", "SAHAB",
        "AJAY", "VIJAY", "SANJAY", "RAJESH", "SURESH",
        "MAHESH", "DINESH", "RAMESH", "MUKESH", "LOKESH",
    ]
    
    # Check female
    for indicator in female_indicators:
        if indicator in upper_name:
            logger.debug(f"Female detected: {character_name} → {indicator}")
            return PRESET_VOICES["HEROINE"]
    
    # Check male
    for indicator in male_indicators:
        if indicator in upper_name:
            logger.debug(f"Male detected: {character_name} → {indicator}")
            return PRESET_VOICES["HERO"]
    
    # Check by ending letters (common Indian patterns)
    # Female endings: A, I, ITA, IKA, etc.
    if upper_name.endswith(('A', 'I', 'IE', 'YA')):
        # But not male endings like NA, TRA
        if not upper_name.endswith(('NA', 'TRA', 'RAJA', 'DA')):
            return PRESET_VOICES["HEROINE"]
    
    # Default - male HERO
    return PRESET_VOICES["HERO"]

# ============================================================
# LIST FUNCTIONS
# ============================================================

def list_all_voices() -> List[Dict]:
    """Sab available voices list karo"""
    voices = []
    for key, profile in PRESET_VOICES.items():
        voices.append({
            "key": key,
            "name": profile.name,
            "description": profile.description,
            "gender": profile.gender.value,
            "age": profile.age_group.value,
            "emoji": profile.emoji,
        })
    return voices


def print_voice_catalog():
    """Voice catalog print karo"""
    print("\n" + "=" * 60)
    print("VOICE CATALOG")
    print("=" * 60)
    
    for key, profile in PRESET_VOICES.items():
        print(f"\n{profile.emoji} {key}")
        print(f"   Name: {profile.name}")
        print(f"   {profile.description}")
        print(f"   Gender: {profile.gender.value} | Age: {profile.age_group.value}")
        print(f"   Language: {profile.language} | TLD: {profile.tld}")
        print(f"   Pitch: {profile.pitch_shift:+.1f} | Speed: {profile.speed_multiplier}x")


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner
    setup_logging(log_level="INFO")
    
    print_banner("Voice Profiles Test", "Character Voice System")
    
    # Test 1: Print catalog
    print_voice_catalog()
    
    # Test 2: Character matching
    print("\n\n" + "=" * 60)
    print("CHARACTER NAME MATCHING TEST")
    print("=" * 60)
    
    test_names = [
        "HERO", "VILLAIN", "CHILD",
        "DADI", "GRANDMA", "NANA",
        "STUDENT", "ROBOT_1", "GHOST_KING",
        "RAJU", "RAM", "SITA",
        "UNKNOWN_CHARACTER"
    ]
    
    for name in test_names:
        profile = find_voice_profile(name)
        print(f"\n  '{name}' → {profile.emoji} {profile.name}")
        print(f"     Gender: {profile.gender.value}, Age: {profile.age_group.value}")
        print(f"     TLD: {profile.tld}, Pitch: {profile.pitch_shift:+.1f}")
    
    print("\n" + "=" * 60)
    print("✅ Voice Profile System Ready!")
    print("=" * 60)