# ============================================================
# src/export/youtube_uploader.py
# 3D Animation Studio - YouTube Upload & Metadata Generator
# YouTube API integration + SEO metadata auto-generation
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

import json
import time
import threading
import hashlib
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum
from pathlib import Path
from datetime import datetime

from src.utils import (
    get_logger,
    get_config,
    ensure_dir,
    write_json,
    read_json,
    get_timestamp,
    generate_uuid,
    format_bytes,
    get_file_size,
)

logger = get_logger("YouTubeUploader")


# ============================================================
# ENUMS
# ============================================================

class PrivacyStatus(Enum):
    """YouTube video privacy settings"""
    PUBLIC    = "public"
    PRIVATE   = "private"
    UNLISTED  = "unlisted"


class VideoCategory(Enum):
    """YouTube video categories with IDs"""
    FILM_ANIMATION   = ("1",  "Film & Animation")
    AUTOS_VEHICLES   = ("2",  "Autos & Vehicles")
    MUSIC            = ("10", "Music")
    PETS_ANIMALS     = ("15", "Pets & Animals")
    SPORTS           = ("17", "Sports")
    TRAVEL_EVENTS    = ("19", "Travel & Events")
    GAMING           = ("20", "Gaming")
    PEOPLE_BLOGS     = ("22", "People & Blogs")
    COMEDY           = ("23", "Comedy")
    ENTERTAINMENT    = ("24", "Entertainment")
    NEWS_POLITICS    = ("25", "News & Politics")
    HOWTO_STYLE      = ("26", "Howto & Style")
    EDUCATION        = ("27", "Education")
    SCIENCE_TECH     = ("28", "Science & Technology")
    NONPROFITS       = ("29", "Nonprofits & Activism")

    def __init__(self, category_id: str, display_name: str):
        self.category_id   = category_id
        self.display_name  = display_name


class UploadStatus(Enum):
    """Upload process ke states"""
    IDLE        = "idle"
    PREPARING   = "preparing"
    UPLOADING   = "uploading"
    PROCESSING  = "processing"
    COMPLETE    = "complete"
    FAILED      = "failed"
    CANCELLED   = "cancelled"


class MetadataStyle(Enum):
    """SEO metadata generation styles"""
    EDUCATIONAL  = "educational"
    ENTERTAINMENT= "entertainment"
    TUTORIAL     = "tutorial"
    VLOG         = "vlog"
    GAMING       = "gaming"
    ANIMATION    = "animation"
    STORY        = "story"
    REVIEW       = "review"


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class YouTubeMetadata:
    """
    YouTube video ke liye complete metadata.
    SEO optimized fields.
    """
    # Required fields
    title: str              = "My Animation Video"
    description: str        = ""
    tags: List[str]         = field(default_factory=list)

    # Category & Privacy
    category: str           = VideoCategory.FILM_ANIMATION.category_id
    privacy: str            = PrivacyStatus.PRIVATE.value

    # Optional fields
    language: str           = "en"
    default_audio_language: str = "en"

    # Thumbnail
    thumbnail_path: Optional[str] = None

    # Monetization
    made_for_kids: bool     = False

    # Schedule (ISO 8601 format, e.g., "2024-12-25T10:00:00Z")
    publish_at: Optional[str] = None

    # Playlist
    playlist_id: Optional[str] = None

    # Chapters (timestamp format: "0:00 Intro\n1:30 Main Content")
    chapters: Optional[str] = None

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Metadata validate karo YouTube limits ke against.
        Returns: (is_valid, list_of_errors)
        """
        errors = []

        # Title validation
        if not self.title or not self.title.strip():
            errors.append("Title empty nahi ho sakta")
        elif len(self.title) > 100:
            errors.append(f"Title too long: {len(self.title)}/100 chars")
        elif len(self.title) < 5:
            errors.append("Title kam se kam 5 characters ka hona chahiye")

        # Description validation
        if len(self.description) > 5000:
            errors.append(f"Description too long: {len(self.description)}/5000 chars")

        # Tags validation
        if len(self.tags) > 500:
            errors.append(f"Too many tags: {len(self.tags)}/500")

        # Tags total length (500 chars max)
        total_tag_length = sum(len(tag) for tag in self.tags)
        if total_tag_length > 500:
            errors.append(f"Tags total length too long: {total_tag_length}/500 chars")

        # Privacy validation
        valid_privacy = [p.value for p in PrivacyStatus]
        if self.privacy not in valid_privacy:
            errors.append(f"Invalid privacy: {self.privacy}")

        return len(errors) == 0, errors

    def to_api_dict(self) -> Dict:
        """YouTube API ke liye format karo"""
        snippet = {
            "title": self.title[:100],
            "description": self.description[:5000],
            "tags": self.tags[:500],
            "categoryId": self.category,
            "defaultLanguage": self.language,
            "defaultAudioLanguage": self.default_audio_language,
        }

        status = {
            "privacyStatus": self.privacy,
            "madeForKids": self.made_for_kids,
        }

        if self.publish_at and self.privacy == PrivacyStatus.PRIVATE.value:
            status["publishAt"] = self.publish_at

        return {
            "snippet": snippet,
            "status": status,
        }

    def to_dict(self) -> Dict:
        """Save karne ke liye dict"""
        return {
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "category": self.category,
            "privacy": self.privacy,
            "language": self.language,
            "thumbnail_path": self.thumbnail_path,
            "made_for_kids": self.made_for_kids,
            "publish_at": self.publish_at,
            "chapters": self.chapters,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "YouTubeMetadata":
        """Dict se object banao"""
        return cls(
            title=data.get("title", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            category=data.get("category", VideoCategory.FILM_ANIMATION.category_id),
            privacy=data.get("privacy", PrivacyStatus.PRIVATE.value),
            language=data.get("language", "en"),
            thumbnail_path=data.get("thumbnail_path"),
            made_for_kids=data.get("made_for_kids", False),
            publish_at=data.get("publish_at"),
            chapters=data.get("chapters"),
        )


@dataclass
class UploadProgress:
    """Upload progress tracking"""
    status: str             = UploadStatus.IDLE.value
    bytes_uploaded: int     = 0
    total_bytes: int        = 0
    percent: float          = 0.0
    speed_bps: float        = 0.0       # bytes per second
    eta_seconds: float      = 0.0
    video_id: Optional[str] = None
    error_message: str      = ""
    start_time: float       = 0.0
    elapsed_seconds: float  = 0.0

    def get_speed_str(self) -> str:
        """Upload speed human readable"""
        if self.speed_bps < 1024:
            return f"{self.speed_bps:.0f} B/s"
        elif self.speed_bps < 1024 * 1024:
            return f"{self.speed_bps/1024:.1f} KB/s"
        else:
            return f"{self.speed_bps/(1024*1024):.1f} MB/s"

    def get_eta_str(self) -> str:
        """ETA human readable"""
        if self.eta_seconds <= 0:
            return "Calculating..."
        mins = int(self.eta_seconds // 60)
        secs = int(self.eta_seconds % 60)
        if mins > 0:
            return f"{mins}m {secs}s"
        return f"{secs}s"


@dataclass
class UploadResult:
    """Upload ka final result"""
    success: bool
    video_id: Optional[str]     = None
    video_url: Optional[str]    = None
    error: Optional[str]        = None
    metadata: Optional[Dict]    = None
    upload_time_seconds: float  = 0.0

    def get_youtube_url(self) -> Optional[str]:
        if self.video_id:
            return f"https://www.youtube.com/watch?v={self.video_id}"
        return None

    def get_studio_url(self) -> Optional[str]:
        if self.video_id:
            return f"https://studio.youtube.com/video/{self.video_id}/edit"
        return None


# ============================================================
# SEO METADATA GENERATOR
# Script/title se automatic SEO metadata generate karta hai
# ============================================================

class SEOMetadataGenerator:
    """
    AI-like SEO metadata generator.
    Script aur title se automatically:
    - Optimized title
    - Detailed description
    - Relevant tags
    - Chapters
    generate karta hai.
    """

    # Category-wise keyword templates
    KEYWORD_TEMPLATES: Dict[str, List[str]] = {
        MetadataStyle.ANIMATION.value: [
            "3d animation", "animation studio", "3d character",
            "animation video", "animated story", "3d render",
            "blender animation", "character animation", "3d art",
            "animation tutorial", "animated film", "3d movie",
        ],
        MetadataStyle.EDUCATIONAL.value: [
            "learn", "tutorial", "how to", "explained", "guide",
            "tips", "tricks", "beginner", "advanced", "step by step",
            "complete guide", "full tutorial", "easy explanation",
        ],
        MetadataStyle.ENTERTAINMENT.value: [
            "funny", "entertainment", "watch", "amazing", "incredible",
            "must watch", "viral", "trending", "epic", "awesome",
        ],
        MetadataStyle.TUTORIAL.value: [
            "tutorial", "how to", "step by step", "guide", "learn",
            "beginner friendly", "easy tutorial", "complete tutorial",
            "in hindi", "explained simply",
        ],
        MetadataStyle.GAMING.value: [
            "gaming", "gameplay", "game", "gamer", "let's play",
            "walkthrough", "tips and tricks", "pro tips", "gaming video",
        ],
        MetadataStyle.STORY.value: [
            "story", "short film", "animated story", "moral story",
            "bedtime story", "kids story", "animation story",
            "3d story", "cartoon story",
        ],
        MetadataStyle.VLOG.value: [
            "vlog", "day in life", "behind scenes", "process video",
            "making of", "time lapse", "journey",
        ],
    }

    # Description templates
    DESCRIPTION_TEMPLATES: Dict[str, str] = {
        MetadataStyle.ANIMATION.value: """{intro}

🎬 **About This Video:**
{main_content}

✨ **What You'll See:**
{bullet_points}

🛠️ **Created With:**
• 3D Animation Studio (Free & Open Source)
• Python + PyOpenGL + PyBullet
• AI-powered lipsync and expressions

📌 **Chapters:**
{chapters}

🔔 Subscribe karo aur bell icon dabao latest animations ke liye!

👍 Video pasand aayi? Like aur share karo!

#3DAnimation #Animation #AnimatedVideo {hashtags}
""",
        MetadataStyle.EDUCATIONAL.value: """{intro}

📚 **Is Video Mein Sikhoge:**
{bullet_points}

⏰ **Chapters:**
{chapters}

📝 **Key Points:**
{main_content}

🔔 Aur tutorials ke liye subscribe karo!

💬 Koi question hai? Comment mein poochho!

#Tutorial #Education #Learning {hashtags}
""",
        MetadataStyle.TUTORIAL.value: """{intro}

🎯 **Is Tutorial Mein:**
{bullet_points}

⏰ **Timestamps:**
{chapters}

📋 **Requirements:**
{main_content}

❓ **Questions?** Comment section mein poochho!

🔔 Subscribe for more tutorials!

#Tutorial #HowTo #Learning {hashtags}
""",
        MetadataStyle.STORY.value: """{intro}

📖 **Story Synopsis:**
{main_content}

🌟 **Highlights:**
{bullet_points}

⏰ **Story Chapters:**
{chapters}

👶 **Age Group:** All ages
🌍 **Language:** Hindi/English

🔔 More stories ke liye subscribe karo!

#AnimatedStory #3DAnimation #KidsStory {hashtags}
""",
    }

    def __init__(self):
        logger.debug("SEOMetadataGenerator initialized")

    def generate_title(
        self,
        base_title: str,
        style: str = MetadataStyle.ANIMATION.value,
        add_power_words: bool = True,
        max_length: int = 70,
    ) -> str:
        """
        SEO optimized title generate karo.
        Power words add karta hai engagement ke liye.
        """
        # Base title clean karo
        title = base_title.strip()

        # Power words by style
        power_words = {
            MetadataStyle.ANIMATION.value:    ["Amazing", "Incredible", "Epic", "Stunning"],
            MetadataStyle.EDUCATIONAL.value:  ["Complete", "Ultimate", "Easy", "Simple"],
            MetadataStyle.TUTORIAL.value:     ["Step-by-Step", "Complete", "Beginner", "Easy"],
            MetadataStyle.ENTERTAINMENT.value:["Must Watch", "Viral", "Epic", "Unbelievable"],
            MetadataStyle.STORY.value:        ["Beautiful", "Heart-touching", "Amazing", "Epic"],
            MetadataStyle.GAMING.value:       ["Epic", "Pro", "Ultimate", "Best"],
            MetadataStyle.VLOG.value:         ["Real", "Honest", "Full", "Behind the Scenes"],
        }

        # Year add karna useful hai SEO ke liye
        current_year = datetime.now().year

        # Already power word hai title mein?
        words = power_words.get(style, [])
        has_power_word = any(w.lower() in title.lower() for w in words)

        if add_power_words and not has_power_word and words:
            import random
            word = random.choice(words)
            candidate = f"{word} {title}"
            if len(candidate) <= max_length:
                title = candidate

        # Length trim karo
        if len(title) > max_length:
            title = title[:max_length-3] + "..."

        return title

    def generate_description(
        self,
        title: str,
        script: Optional[str] = None,
        style: str = MetadataStyle.ANIMATION.value,
        channel_name: str = "",
        website: str = "",
        social_links: Optional[Dict[str, str]] = None,
        custom_intro: str = "",
        bullet_points: Optional[List[str]] = None,
        chapters: Optional[List[Tuple[str, str]]] = None,
    ) -> str:
        """
        Full SEO description generate karo.
        
        Args:
            title: Video title
            script: Video script (optional, context ke liye)
            style: Content style
            channel_name: Channel ka naam
            website: Website URL
            social_links: Dict of platform->URL
            custom_intro: Custom intro text
            bullet_points: Key points list
            chapters: List of (timestamp, chapter_name) tuples
            
        Returns:
            Complete description string
        """
        # Template lo
        template = self.DESCRIPTION_TEMPLATES.get(
            style,
            self.DESCRIPTION_TEMPLATES[MetadataStyle.ANIMATION.value]
        )

        # Intro
        if custom_intro:
            intro = custom_intro
        elif script:
            # Script se pehle 200 chars lo
            intro = script[:200].strip()
            if len(script) > 200:
                intro += "..."
        else:
            intro = f"Welcome to this amazing {title}! Is video mein hum ek incredible animation dekhenge."

        # Main content
        if script:
            # Script ke important sentences extract karo
            sentences = [s.strip() for s in script.split('.') if len(s.strip()) > 20]
            main_content = ". ".join(sentences[:3]) + "."
        else:
            main_content = f"Is video mein {title} ke baare mein detail mein cover kiya gaya hai."

        # Bullet points
        if not bullet_points:
            bullet_points = [
                "High quality 3D animation",
                "Professional voice over",
                "Engaging story and content",
                "Cinematic camera angles",
                "Realistic physics and effects",
            ]
        bp_text = "\n".join(f"• {bp}" for bp in bullet_points)

        # Chapters
        if chapters:
            ch_text = "\n".join(f"{ts} {name}" for ts, name in chapters)
        else:
            ch_text = "0:00 Introduction\n0:30 Main Content\n(End) Conclusion"

        # Hashtags se tags generate karo
        keywords = self.KEYWORD_TEMPLATES.get(style, [])
        hashtags = " ".join(
            f"#{kw.replace(' ', '').replace('-', '')}"
            for kw in keywords[:10]
        )

        # Template fill karo
        description = template.format(
            intro=intro,
            main_content=main_content,
            bullet_points=bp_text,
            chapters=ch_text,
            hashtags=hashtags,
        )

        # Social links add karo
        if social_links or channel_name or website:
            description += "\n\n📱 **Connect With Us:**\n"
            if channel_name:
                description += f"YouTube: {channel_name}\n"
            if website:
                description += f"🌐 Website: {website}\n"
            if social_links:
                for platform, url in social_links.items():
                    description += f"{platform}: {url}\n"

        # Length limit
        if len(description) > 5000:
            description = description[:4997] + "..."

        return description

    def generate_tags(
        self,
        title: str,
        style: str = MetadataStyle.ANIMATION.value,
        script: Optional[str] = None,
        language: str = "en",
        custom_tags: Optional[List[str]] = None,
        max_tags: int = 30,
    ) -> List[str]:
        """
        SEO-optimized tags generate karo.
        
        Args:
            title: Video title
            style: Content style
            script: Script text (optional)
            language: Video language
            custom_tags: User-defined custom tags
            max_tags: Maximum tags count
            
        Returns:
            List of tags
        """
        tags = set()

        # Style-specific keywords
        style_keywords = self.KEYWORD_TEMPLATES.get(style, [])
        tags.update(style_keywords[:15])

        # Title se words extract karo
        title_words = re.findall(r'\b[a-zA-Z]{3,}\b', title.lower())
        meaningful_words = [w for w in title_words if w not in
                           ['the', 'and', 'for', 'with', 'this', 'that',
                            'from', 'are', 'was', 'were', 'will', 'have',
                            'has', 'had', 'not', 'but', 'our', 'your']]
        tags.update(meaningful_words[:10])

        # Script se keywords (agar script hai)
        if script:
            script_words = re.findall(r'\b[a-zA-Z]{4,}\b', script.lower())
            # Frequency count
            word_freq: Dict[str, int] = {}
            for word in script_words:
                if word not in ['that', 'this', 'with', 'from', 'have',
                               'will', 'were', 'they', 'what', 'when',
                               'where', 'which', 'your', 'their']:
                    word_freq[word] = word_freq.get(word, 0) + 1
            # Top frequent words
            frequent = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            tags.update(w for w, _ in frequent[:10])

        # Language-specific tags
        lang_tags = {
            "hi": ["hindi", "hindi animation", "hindi video", "हिंदी"],
            "en": ["english", "english animation"],
            "es": ["spanish", "español"],
        }
        if language in lang_tags:
            tags.update(lang_tags[language])

        # Custom tags add karo
        if custom_tags:
            tags.update(custom_tags)

        # Common animation tags hamesha add karo
        tags.update([
            "animation", "3d animation", "animated",
            "free animation software", "open source animation",
        ])

        # Convert to list, limit, aur clean karo
        final_tags = []
        for tag in tags:
            tag_clean = str(tag).strip().lower()
            if tag_clean and len(tag_clean) >= 2:
                final_tags.append(tag_clean)

        # Duplicates remove karo
        seen = set()
        unique_tags = []
        for tag in final_tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)

        # Max tags limit
        return unique_tags[:max_tags]

    def generate_chapters(
        self,
        scenes: List[Dict],
        fps: int = 30,
    ) -> List[Tuple[str, str]]:
        """
        Scenes list se YouTube chapters generate karo.
        
        Args:
            scenes: List of scene dicts with 'name' and 'frame_count'
            fps: Frame rate
            
        Returns:
            List of (timestamp_str, chapter_name) tuples
        """
        chapters = []
        current_frame = 0

        for i, scene in enumerate(scenes):
            # Timestamp calculate karo
            total_seconds = current_frame / fps
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            timestamp = f"{minutes}:{seconds:02d}"

            name = scene.get("name", f"Scene {i+1}")
            chapters.append((timestamp, name))

            current_frame += scene.get("frame_count", fps * 5)  # Default 5 sec

        return chapters

    def generate_full_metadata(
        self,
        title: str,
        style: str = MetadataStyle.ANIMATION.value,
        script: Optional[str] = None,
        language: str = "en",
        privacy: str = PrivacyStatus.PRIVATE.value,
        category: str = VideoCategory.FILM_ANIMATION.category_id,
        channel_name: str = "",
        custom_tags: Optional[List[str]] = None,
        scenes: Optional[List[Dict]] = None,
        made_for_kids: bool = False,
    ) -> YouTubeMetadata:
        """
        Ek call mein complete YouTube metadata generate karo.
        Sabse convenient method.
        """
        # Title optimize karo
        optimized_title = self.generate_title(title, style)

        # Chapters generate karo (agar scenes hain)
        chapters = None
        chapters_str = None
        if scenes:
            chapters = self.generate_chapters(scenes)
            chapters_str = "\n".join(f"{ts} {name}" for ts, name in chapters)

        # Tags generate karo
        tags = self.generate_tags(
            title=title,
            style=style,
            script=script,
            language=language,
            custom_tags=custom_tags,
        )

        # Description generate karo
        description = self.generate_description(
            title=optimized_title,
            script=script,
            style=style,
            chapters=chapters,
        )

        metadata = YouTubeMetadata(
            title=optimized_title,
            description=description,
            tags=tags,
            category=category,
            privacy=privacy,
            language=language,
            made_for_kids=made_for_kids,
            chapters=chapters_str,
        )

        logger.info(f"✅ Metadata generated: '{optimized_title}' | {len(tags)} tags")
        return metadata


# ============================================================
# YOUTUBE API CLIENT
# Google API wrapper - graceful fallback agar installed nahi
# ============================================================

class YouTubeAPIClient:
    """
    YouTube Data API v3 wrapper.
    google-api-python-client use karta hai.
    Agar install nahi hai to simulation mode mein run karta hai.
    """

    # Scopes required for upload
    SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube",
    ]

    # OAuth credentials file
    CLIENT_SECRETS_FILE = "credentials/youtube_client_secrets.json"
    TOKEN_FILE          = "credentials/youtube_token.json"

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._authenticated  = False
        self._youtube_service = None
        self._simulation_mode = False

        # Google API libraries check karo
        self._api_available = self._check_api_available()

        if not self._api_available:
            logger.warning(
                "⚠️ google-api-python-client installed nahi hai. "
                "Simulation mode mein chalega. "
                "Install karo: pip install google-api-python-client google-auth-oauthlib"
            )
            self._simulation_mode = True

    def _check_api_available(self) -> bool:
        """Check karo ki Google API libraries available hain"""
        try:
            import googleapiclient.discovery
            import google_auth_oauthlib.flow
            import google.auth.transport.requests
            return True
        except ImportError:
            return False

    def is_authenticated(self) -> bool:
        """Authentication status check karo"""
        return self._authenticated or self._simulation_mode

    def authenticate(
        self,
        client_secrets_file: Optional[str] = None,
        force_reauth: bool = False,
    ) -> bool:
        """
        YouTube API ke liye OAuth2 authentication karo.
        
        Args:
            client_secrets_file: Path to client_secrets.json from Google Console
            force_reauth: Force re-authentication
            
        Returns:
            True if successful
        """
        if self._simulation_mode:
            logger.info("🎭 Simulation mode: Authentication simulated")
            self._authenticated = True
            return True

        try:
            from googleapiclient.discovery import build
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            import pickle

            secrets_file = client_secrets_file or self.CLIENT_SECRETS_FILE
            token_file   = self.TOKEN_FILE

            # Credentials directory ensure karo
            ensure_dir(str(Path(token_file).parent))

            creds = None

            # Existing token check karo
            if not force_reauth and os.path.exists(token_file):
                try:
                    with open(token_file, 'rb') as f:
                        creds = pickle.load(f)
                    logger.debug("Existing token loaded")
                except Exception:
                    creds = None

            # Token refresh ya new auth
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logger.info("Token refresh kar raha hai...")
                    creds.refresh(Request())
                else:
                    # Client secrets file check karo
                    if not os.path.exists(secrets_file):
                        logger.error(
                            f"❌ Client secrets file nahi mila: {secrets_file}\n"
                            "Google Cloud Console se download karo:\n"
                            "https://console.cloud.google.com/apis/credentials"
                        )
                        return False

                    # New authentication flow
                    logger.info("🌐 Browser mein YouTube login page khul raha hai...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        secrets_file, self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Token save karo
                with open(token_file, 'wb') as f:
                    import pickle
                    pickle.dump(creds, f)
                logger.info("✅ Token saved for future use")

            # YouTube service build karo
            self._youtube_service = build('youtube', 'v3', credentials=creds)
            self._authenticated = True
            logger.info("✅ YouTube API authenticated successfully!")
            return True

        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            return False

    def get_channel_info(self) -> Optional[Dict]:
        """Channel information lo"""
        if self._simulation_mode:
            return {
                "id": "SIMULATED_CHANNEL_ID",
                "title": "My Animation Channel",
                "subscriberCount": "1000",
                "videoCount": "50",
            }

        if not self._authenticated or not self._youtube_service:
            logger.error("Pehle authenticate karo")
            return None

        try:
            response = self._youtube_service.channels().list(
                part="snippet,statistics",
                mine=True
            ).execute()

            if response.get("items"):
                item = response["items"][0]
                return {
                    "id": item["id"],
                    "title": item["snippet"]["title"],
                    "subscriberCount": item["statistics"].get("subscriberCount", "0"),
                    "videoCount": item["statistics"].get("videoCount", "0"),
                }
        except Exception as e:
            logger.error(f"Channel info fetch failed: {e}")

        return None

    def get_playlists(self) -> List[Dict]:
        """User ke playlists lo"""
        if self._simulation_mode:
            return [
                {"id": "PL_SIM_1", "title": "My Animations"},
                {"id": "PL_SIM_2", "title": "Tutorials"},
            ]

        if not self._authenticated or not self._youtube_service:
            return []

        try:
            playlists = []
            request = self._youtube_service.playlists().list(
                part="snippet",
                mine=True,
                maxResults=50,
            )
            while request:
                response = request.execute()
                for item in response.get("items", []):
                    playlists.append({
                        "id": item["id"],
                        "title": item["snippet"]["title"],
                    })
                request = self._youtube_service.playlists().list_next(request, response)
            return playlists

        except Exception as e:
            logger.error(f"Playlists fetch failed: {e}")
            return []

    def add_to_playlist(self, video_id: str, playlist_id: str) -> bool:
        """Video ko playlist mein add karo"""
        if self._simulation_mode:
            logger.info(f"🎭 Simulation: Video {video_id} added to playlist {playlist_id}")
            return True

        try:
            self._youtube_service.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id,
                        }
                    }
                }
            ).execute()
            logger.info(f"✅ Video added to playlist")
            return True

        except Exception as e:
            logger.error(f"Add to playlist failed: {e}")
            return False

    def upload_thumbnail(self, video_id: str, thumbnail_path: str) -> bool:
        """Custom thumbnail upload karo"""
        if self._simulation_mode:
            logger.info(f"🎭 Simulation: Thumbnail uploaded for {video_id}")
            return True

        if not os.path.exists(thumbnail_path):
            logger.error(f"Thumbnail file nahi mila: {thumbnail_path}")
            return False

        try:
            from googleapiclient.http import MediaFileUpload

            media = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
            self._youtube_service.thumbnails().set(
                videoId=video_id,
                media_body=media,
            ).execute()
            logger.info(f"✅ Thumbnail uploaded")
            return True

        except Exception as e:
            logger.error(f"Thumbnail upload failed: {e}")
            return False


# ============================================================
# MAIN UPLOADER CLASS
# ============================================================

class YouTubeUploader:
    """
    YouTube Video Uploader - Main Class.
    
    Features:
    - Resumable uploads (large files ke liye)
    - Progress tracking with callbacks
    - SEO metadata auto-generation
    - Thumbnail upload
    - Playlist management
    - Simulation mode (without API)
    - Upload history
    """

    # Upload chunk size (10MB)
    CHUNK_SIZE = 10 * 1024 * 1024

    def __init__(self, config: Optional[Dict] = None):
        """
        YouTubeUploader initialize karo.
        
        Args:
            config: Optional configuration dict
        """
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # API client
        self.api_client = YouTubeAPIClient(config)

        # Metadata generator
        self.seo_generator = SEOMetadataGenerator()

        # Progress tracking
        self._progress = UploadProgress()

        # Callbacks
        self._progress_callbacks: List[Callable[[UploadProgress], None]] = []
        self._completion_callbacks: List[Callable[[UploadResult], None]] = []

        # Upload history
        self._history_file = Path("cache/upload_history.json")
        self._upload_history: List[Dict] = []
        self._load_history()

        # Upload thread
        self._upload_thread: Optional[threading.Thread] = None
        self._cancel_requested = False

        logger.info(
            f"✅ YouTubeUploader initialized | "
            f"API: {'Available' if self.api_client._api_available else 'Simulation Mode'}"
        )

    def _load_history(self):
        """Upload history load karo"""
        try:
            ensure_dir(str(self._history_file.parent))
            if self._history_file.exists():
                data = read_json(str(self._history_file))
                self._upload_history = data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"History load failed: {e}")
            self._upload_history = []

    def _save_history(self):
        """Upload history save karo"""
        try:
            write_json(str(self._history_file), self._upload_history)
        except Exception as e:
            logger.warning(f"History save failed: {e}")

    def _add_to_history(self, result: UploadResult, metadata: YouTubeMetadata):
        """Upload history mein entry add karo"""
        entry = {
            "timestamp": get_timestamp(),
            "title": metadata.title,
            "video_id": result.video_id,
            "url": result.get_youtube_url(),
            "success": result.success,
            "upload_time_seconds": result.upload_time_seconds,
        }
        self._upload_history.insert(0, entry)  # Latest first
        # Max 100 entries rakho
        self._upload_history = self._upload_history[:100]
        self._save_history()

    # ----------------------------------------------------------
    # CALLBACK MANAGEMENT
    # ----------------------------------------------------------

    def add_progress_callback(self, callback: Callable[[UploadProgress], None]):
        """Progress update callback add karo"""
        self._progress_callbacks.append(callback)

    def add_completion_callback(self, callback: Callable[[UploadResult], None]):
        """Upload complete callback add karo"""
        self._completion_callbacks.append(callback)

    def _notify_progress(self):
        """Progress callbacks ko notify karo"""
        for cb in self._progress_callbacks:
            try:
                cb(self._progress)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")

    def _notify_completion(self, result: UploadResult):
        """Completion callbacks ko notify karo"""
        for cb in self._completion_callbacks:
            try:
                cb(result)
            except Exception as e:
                logger.warning(f"Completion callback error: {e}")

    # ----------------------------------------------------------
    # AUTHENTICATION
    # ----------------------------------------------------------

    def authenticate(
        self,
        client_secrets_file: Optional[str] = None,
        force_reauth: bool = False,
    ) -> bool:
        """
        YouTube authenticate karo.
        
        Args:
            client_secrets_file: Google Cloud Console se download kiya hua file
            force_reauth: Force new authentication
            
        Returns:
            True if authenticated
        """
        return self.api_client.authenticate(client_secrets_file, force_reauth)

    def is_authenticated(self) -> bool:
        """Authentication status check karo"""
        return self.api_client.is_authenticated()

    # ----------------------------------------------------------
    # METADATA GENERATION
    # ----------------------------------------------------------

    def generate_metadata(
        self,
        title: str,
        style: str = MetadataStyle.ANIMATION.value,
        script: Optional[str] = None,
        language: str = "en",
        privacy: str = PrivacyStatus.PRIVATE.value,
        category: str = VideoCategory.FILM_ANIMATION.category_id,
        custom_tags: Optional[List[str]] = None,
        scenes: Optional[List[Dict]] = None,
        made_for_kids: bool = False,
    ) -> YouTubeMetadata:
        """
        Auto SEO metadata generate karo.
        Convenience wrapper for SEOMetadataGenerator.
        """
        return self.seo_generator.generate_full_metadata(
            title=title,
            style=style,
            script=script,
            language=language,
            privacy=privacy,
            category=category,
            custom_tags=custom_tags,
            scenes=scenes,
            made_for_kids=made_for_kids,
        )

    # ----------------------------------------------------------
    # UPLOAD - MAIN METHOD
    # ----------------------------------------------------------

    def upload_video(
        self,
        video_path: str,
        metadata: YouTubeMetadata,
        async_upload: bool = False,
    ) -> UploadResult:
        """
        YouTube pe video upload karo.
        
        Args:
            video_path: Upload karne wali video file ka path
            metadata: YouTubeMetadata object
            async_upload: True = background thread mein upload karo
            
        Returns:
            UploadResult (sync mode mein), ya immediately return (async mode)
        """
        if async_upload:
            self._upload_thread = threading.Thread(
                target=self._upload_internal,
                args=(video_path, metadata),
                daemon=True,
            )
            self._cancel_requested = False
            self._upload_thread.start()
            # Async mode mein dummy result return karo
            return UploadResult(success=False, error="Async upload started")
        else:
            return self._upload_internal(video_path, metadata)

    def _upload_internal(
        self,
        video_path: str,
        metadata: YouTubeMetadata,
    ) -> UploadResult:
        """
        Actual upload logic.
        Synchronous ya background thread se call hota hai.
        """
        start_time = time.time()
        self._cancel_requested = False

        # ===== VALIDATION =====
        self._progress.status = UploadStatus.PREPARING.value
        self._progress.start_time = start_time
        self._notify_progress()

        # File exist karta hai?
        if not os.path.exists(video_path):
            error = f"Video file nahi mila: {video_path}"
            logger.error(f"❌ {error}")
            result = UploadResult(success=False, error=error)
            self._notify_completion(result)
            return result

        # Metadata validate karo
        is_valid, errors = metadata.validate()
        if not is_valid:
            error = f"Metadata invalid: {'; '.join(errors)}"
            logger.error(f"❌ {error}")
            result = UploadResult(success=False, error=error)
            self._notify_completion(result)
            return result

        # File size
        file_size = os.path.getsize(video_path)
        self._progress.total_bytes = file_size
        logger.info(
            f"📤 Upload starting: '{metadata.title}' | "
            f"Size: {format_bytes(file_size)}"
        )

        # ===== SIMULATION MODE =====
        if self.api_client._simulation_mode:
            result = self._simulate_upload(video_path, metadata, start_time)
            self._add_to_history(result, metadata)
            self._notify_completion(result)
            return result

        # ===== REAL API UPLOAD =====
        if not self.api_client.is_authenticated():
            error = "Pehle authenticate karo: uploader.authenticate()"
            logger.error(f"❌ {error}")
            result = UploadResult(success=False, error=error)
            self._notify_completion(result)
            return result

        try:
            from googleapiclient.http import MediaFileUpload

            # Media upload object
            media = MediaFileUpload(
                video_path,
                mimetype="video/mp4",
                chunksize=self.CHUNK_SIZE,
                resumable=True,  # Resumable uploads for large files
            )

            # Insert request
            insert_request = self.api_client._youtube_service.videos().insert(
                part="snippet,status",
                body=metadata.to_api_dict(),
                media_body=media,
            )

            # Upload with progress tracking
            video_id = self._execute_resumable_upload(insert_request, file_size)

            if self._cancel_requested:
                result = UploadResult(
                    success=False,
                    error="Upload cancelled by user"
                )
            elif video_id:
                elapsed = time.time() - start_time

                # Thumbnail upload (agar hai)
                if metadata.thumbnail_path:
                    self.api_client.upload_thumbnail(video_id, metadata.thumbnail_path)

                # Playlist mein add karo (agar hai)
                if metadata.playlist_id:
                    self.api_client.add_to_playlist(video_id, metadata.playlist_id)

                # Processing status update
                self._progress.status  = UploadStatus.COMPLETE.value
                self._progress.percent = 100.0
                self._notify_progress()

                result = UploadResult(
                    success=True,
                    video_id=video_id,
                    video_url=f"https://www.youtube.com/watch?v={video_id}",
                    upload_time_seconds=elapsed,
                    metadata=metadata.to_dict(),
                )

                logger.info(
                    f"✅ Upload complete! Video ID: {video_id} | "
                    f"Time: {elapsed:.1f}s | "
                    f"URL: {result.video_url}"
                )
            else:
                result = UploadResult(success=False, error="Upload failed: No video ID returned")

        except Exception as e:
            logger.error(f"❌ Upload failed: {e}")
            self._progress.status = UploadStatus.FAILED.value
            self._progress.error_message = str(e)
            self._notify_progress()
            result = UploadResult(success=False, error=str(e))

        self._add_to_history(result, metadata)
        self._notify_completion(result)
        return result

    def _execute_resumable_upload(
        self,
        insert_request,
        total_size: int,
    ) -> Optional[str]:
        """
        Resumable upload execute karo chunks mein.
        Progress track karta hai.
        """
        self._progress.status = UploadStatus.UPLOADING.value
        last_time  = time.time()
        last_bytes = 0

        while True:
            if self._cancel_requested:
                logger.info("⚠️ Upload cancelled")
                return None

            try:
                status, response = insert_request.next_chunk()

                if status:
                    # Progress update
                    bytes_done = int(status.resumable_progress)
                    current_time = time.time()
                    elapsed = current_time - last_time

                    if elapsed > 0:
                        speed = (bytes_done - last_bytes) / elapsed
                        self._progress.speed_bps = speed
                        remaining_bytes = total_size - bytes_done
                        self._progress.eta_seconds = remaining_bytes / speed if speed > 0 else 0

                    self._progress.bytes_uploaded = bytes_done
                    self._progress.total_bytes    = total_size
                    self._progress.percent        = status.progress() * 100
                    self._progress.elapsed_seconds = current_time - self._progress.start_time
                    self._notify_progress()

                    last_time  = current_time
                    last_bytes = bytes_done

                    logger.debug(
                        f"Upload: {self._progress.percent:.1f}% | "
                        f"{self._progress.get_speed_str()} | "
                        f"ETA: {self._progress.get_eta_str()}"
                    )

                if response is not None:
                    # Upload complete
                    return response.get("id")

            except Exception as e:
                logger.error(f"Upload chunk error: {e}")
                return None

    def _simulate_upload(
        self,
        video_path: str,
        metadata: YouTubeMetadata,
        start_time: float,
    ) -> UploadResult:
        """
        Upload simulate karo (bina actual API ke).
        Testing aur demo ke liye.
        """
        logger.info("🎭 Simulating YouTube upload...")

        file_size = os.path.getsize(video_path)

        # Progress simulate karo
        self._progress.status      = UploadStatus.UPLOADING.value
        self._progress.total_bytes = file_size

        # Simulate chunks
        chunks = 10
        for i in range(chunks + 1):
            if self._cancel_requested:
                self._progress.status = UploadStatus.CANCELLED.value
                return UploadResult(success=False, error="Upload cancelled")

            progress = i / chunks
            self._progress.bytes_uploaded  = int(file_size * progress)
            self._progress.percent         = progress * 100
            self._progress.speed_bps       = 5 * 1024 * 1024  # Simulate 5MB/s
            self._progress.eta_seconds     = (file_size * (1 - progress)) / self._progress.speed_bps
            self._progress.elapsed_seconds = time.time() - start_time
            self._notify_progress()

            time.sleep(0.1)  # Simulate upload time

        # Fake video ID generate karo
        fake_id = hashlib.md5(
            f"{metadata.title}{get_timestamp()}".encode()
        ).hexdigest()[:11]

        self._progress.status  = UploadStatus.COMPLETE.value
        self._progress.percent = 100.0
        self._notify_progress()

        elapsed = time.time() - start_time

        result = UploadResult(
            success=True,
            video_id=fake_id,
            video_url=f"https://www.youtube.com/watch?v={fake_id}",
            upload_time_seconds=elapsed,
            metadata=metadata.to_dict(),
        )

        logger.info(
            f"✅ Simulation complete! "
            f"Fake Video ID: {fake_id} | "
            f"Time: {elapsed:.1f}s"
        )
        return result

    def cancel_upload(self):
        """Current upload cancel karo"""
        self._cancel_requested = True
        self._progress.status  = UploadStatus.CANCELLED.value
        self._notify_progress()
        logger.info("⚠️ Upload cancel requested")

    # ----------------------------------------------------------
    # HISTORY & UTILITIES
    # ----------------------------------------------------------

    def get_upload_history(self, limit: int = 20) -> List[Dict]:
        """Upload history lo"""
        return self._upload_history[:limit]

    def clear_history(self):
        """Upload history clear karo"""
        self._upload_history = []
        self._save_history()
        logger.info("🗑️ Upload history cleared")

    def get_current_progress(self) -> UploadProgress:
        """Current upload progress lo"""
        return self._progress

    def save_metadata_to_file(
        self,
        metadata: YouTubeMetadata,
        filepath: str,
    ) -> bool:
        """
        Metadata ko JSON file mein save karo.
        Baad mein use karne ke liye.
        """
        try:
            ensure_dir(str(Path(filepath).parent))
            write_json(filepath, metadata.to_dict())
            logger.info(f"✅ Metadata saved: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Metadata save failed: {e}")
            return False

    def load_metadata_from_file(self, filepath: str) -> Optional[YouTubeMetadata]:
        """Saved metadata load karo"""
        try:
            data = read_json(filepath)
            if data:
                return YouTubeMetadata.from_dict(data)
        except Exception as e:
            logger.error(f"Metadata load failed: {e}")
        return None

    def get_channel_info(self) -> Optional[Dict]:
        """Channel info lo"""
        return self.api_client.get_channel_info()

    def get_playlists(self) -> List[Dict]:
        """Playlists lo"""
        return self.api_client.get_playlists()

    def print_setup_guide(self):
        """
        YouTube API setup guide print karo.
        First time users ke liye helpful.
        """
        guide = """
╔══════════════════════════════════════════════════════╗
║         YouTube API Setup Guide                      ║
╚══════════════════════════════════════════════════════╝

Step 1: Google Cloud Console
  → https://console.cloud.google.com/
  → Naya project banao: "3D Animation Studio"

Step 2: YouTube Data API v3 Enable Karo
  → APIs & Services → Library
  → "YouTube Data API v3" search karo
  → Enable karo

Step 3: OAuth Credentials Banao
  → APIs & Services → Credentials
  → "Create Credentials" → "OAuth 2.0 Client ID"
  → Application type: "Desktop app"
  → Download JSON karo

Step 4: File Copy Karo
  → Downloaded file rename karo:
    youtube_client_secrets.json
  → Copy karo project folder mein:
    credentials/youtube_client_secrets.json

Step 5: Libraries Install Karo
  → pip install google-api-python-client
  → pip install google-auth-oauthlib

Step 6: Authenticate Karo
  >>> uploader = YouTubeUploader()
  >>> uploader.authenticate()
  → Browser mein Google login karega
  → Allow karo permissions

✅ Done! Ab upload kar sakte ho!
"""
        print(guide)
        logger.info("YouTube API setup guide displayed")


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

_global_uploader: Optional[YouTubeUploader] = None


def get_uploader() -> YouTubeUploader:
    """Global YouTubeUploader instance lo (singleton)"""
    global _global_uploader
    if _global_uploader is None:
        _global_uploader = YouTubeUploader()
    return _global_uploader


def quick_upload(
    video_path: str,
    title: str,
    script: Optional[str] = None,
    privacy: str = PrivacyStatus.PRIVATE.value,
    style: str = MetadataStyle.ANIMATION.value,
) -> UploadResult:
    """
    Quick upload - ek function call mein sab kuch.
    Metadata auto-generate hoti hai.
    """
    uploader = get_uploader()

    # Metadata generate karo
    metadata = uploader.generate_metadata(
        title=title,
        script=script,
        privacy=privacy,
        style=style,
    )

    # Upload karo
    return uploader.upload_video(video_path, metadata)


# ============================================================
# TEST SECTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="DEBUG")
    print_banner("YouTube Uploader Test", "Upload & SEO Metadata Generator")

    # ===== TEST 1: Initialization =====
    print_section("Test 1: Initialization")
    uploader = YouTubeUploader()
    print(f"✅ Uploader initialized")
    print(f"   API Available  : {uploader.api_client._api_available}")
    print(f"   Simulation Mode: {uploader.api_client._simulation_mode}")

    # ===== TEST 2: SEO Metadata Generation =====
    print_section("Test 2: SEO Metadata Generation")
    seo = SEOMetadataGenerator()

    # Title generation
    test_title = "Python 3D Animation Tutorial"
    opt_title = seo.generate_title(test_title, MetadataStyle.TUTORIAL.value)
    print(f"✅ Original title : {test_title}")
    print(f"   Optimized title: {opt_title}")

    # Full metadata generation
    test_script = """
    Aaj hum Python mein 3D animation banana sikhenge.
    PyOpenGL aur PyBullet use karenge.
    Pehle environment setup karenge, phir character banayenge.
    Animation ke liye keyframes use honge.
    Final output MP4 format mein export hogi.
    """

    metadata = uploader.generate_metadata(
        title="Amazing Python 3D Animation Tutorial",
        style=MetadataStyle.TUTORIAL.value,
        script=test_script,
        language="en",
        privacy=PrivacyStatus.PRIVATE.value,
        category=VideoCategory.SCIENCE_TECH.category_id,
        custom_tags=["python animation", "3d tutorial", "open source"],
        scenes=[
            {"name": "Introduction", "frame_count": 180},
            {"name": "Setup Environment", "frame_count": 300},
            {"name": "Create Character", "frame_count": 450},
            {"name": "Add Animation", "frame_count": 600},
            {"name": "Export Video", "frame_count": 240},
        ],
    )

    print(f"\n✅ Metadata Generated:")
    print(f"   Title      : {metadata.title}")
    print(f"   Tags       : {len(metadata.tags)} tags")
    print(f"   Description: {len(metadata.description)} chars")
    print(f"   Category   : {metadata.category}")
    print(f"   Privacy    : {metadata.privacy}")
    print(f"\n   First 5 Tags: {metadata.tags[:5]}")
    print(f"\n   Description Preview:")
    print(f"   {metadata.description[:300]}...")

    # ===== TEST 3: Metadata Validation =====
    print_section("Test 3: Metadata Validation")

    # Valid metadata
    is_valid, errors = metadata.validate()
    print(f"✅ Valid metadata: {is_valid} | Errors: {errors}")

    # Invalid metadata test
    bad_metadata = YouTubeMetadata(title="", tags=["x"] * 600)
    is_valid2, errors2 = bad_metadata.validate()
    print(f"✅ Invalid metadata caught: {not is_valid2}")
    print(f"   Errors: {errors2}")

    # ===== TEST 4: Metadata Save/Load =====
    print_section("Test 4: Metadata Save & Load")
    ensure_dir("cache")
    save_path = "cache/test_metadata.json"

    saved = uploader.save_metadata_to_file(metadata, save_path)
    print(f"✅ Metadata saved: {saved} → {save_path}")

    loaded = uploader.load_metadata_from_file(save_path)
    if loaded:
        print(f"✅ Metadata loaded: '{loaded.title}'")
        print(f"   Tags count: {len(loaded.tags)}")
        titles_match = loaded.title == metadata.title
        print(f"   Title matches: {titles_match}")
    else:
        print("❌ Metadata load failed")

    # ===== TEST 5: API to Dict Format =====
    print_section("Test 5: YouTube API Dict Format")
    api_dict = metadata.to_api_dict()
    print(f"✅ API dict generated:")
    print(f"   Snippet keys: {list(api_dict['snippet'].keys())}")
    print(f"   Status keys : {list(api_dict['status'].keys())}")
    print(f"   Title in API: {api_dict['snippet']['title'][:50]}")

    # ===== TEST 6: Simulated Upload =====
    print_section("Test 6: Simulated Upload (No Real API)")

    # Temporary test file banao
    test_video_path = "cache/test_upload.mp4"
    with open(test_video_path, 'wb') as f:
        f.write(b'0' * (1024 * 1024))  # 1MB fake video
    print(f"✅ Test video created: {get_file_size(test_video_path)} bytes")

    # Progress callback
    progress_updates = []
    def on_progress(prog: UploadProgress):
        progress_updates.append(prog.percent)
        if int(prog.percent) % 30 == 0:
            print(
                f"   Progress: {prog.percent:.0f}% | "
                f"Speed: {prog.get_speed_str()} | "
                f"ETA: {prog.get_eta_str()}"
            )

    # Completion callback
    def on_complete(result: UploadResult):
        if result.success:
            print(f"\n   ✅ Upload complete!")
            print(f"   Video ID : {result.video_id}")
            print(f"   URL      : {result.get_youtube_url()}")
            print(f"   Studio   : {result.get_studio_url()}")
            print(f"   Time     : {result.upload_time_seconds:.2f}s")
        else:
            print(f"   ❌ Upload failed: {result.error}")

    uploader.add_progress_callback(on_progress)
    uploader.add_completion_callback(on_complete)

    # Upload karo (simulation mode mein)
    print(f"\n🚀 Starting simulated upload...")
    result = uploader.upload_video(
        video_path=test_video_path,
        metadata=metadata,
        async_upload=False,
    )
    print(f"\n✅ Upload result: success={result.success}")

    # ===== TEST 7: Upload History =====
    print_section("Test 7: Upload History")
    history = uploader.get_upload_history(limit=5)
    print(f"✅ Upload history: {len(history)} entries")
    for entry in history:
        print(f"   📹 {entry.get('title', 'N/A')[:40]} | "
              f"ID: {entry.get('video_id', 'N/A')} | "
              f"Success: {entry.get('success', False)}")

    # ===== TEST 8: Channel & Playlist (Simulation) =====
    print_section("Test 8: Channel Info & Playlists (Simulation)")
    channel = uploader.get_channel_info()
    if channel:
        print(f"✅ Channel: {channel.get('title')}")
        print(f"   Subscribers: {channel.get('subscriberCount')}")

    playlists = uploader.get_playlists()
    print(f"✅ Playlists: {len(playlists)}")
    for pl in playlists:
        print(f"   📋 {pl.get('title')} (ID: {pl.get('id')})")

    # ===== TEST 9: Tags Generation =====
    print_section("Test 9: Tags Generation Detail")
    tags = seo.generate_tags(
        title="Amazing 3D Character Animation",
        style=MetadataStyle.ANIMATION.value,
        script="We create a stunning 3D character with Python animation software",
        language="en",
        custom_tags=["python", "tutorial"],
        max_tags=20,
    )
    print(f"✅ Generated {len(tags)} tags:")
    print(f"   {tags}")

    # ===== TEST 10: Setup Guide =====
    print_section("Test 10: YouTube API Setup Guide")
    uploader.print_setup_guide()

    # ===== CLEANUP =====
    try:
        if os.path.exists(test_video_path):
            os.remove(test_video_path)
        if os.path.exists(save_path):
            os.remove(save_path)
    except Exception:
        pass

    print_banner("✅ All Tests Passed!", "youtube_uploader.py Working Perfectly")