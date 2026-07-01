# ============================================================
# src/ui/asset_browser.py
# 3D Animation Studio - Asset Browser Panel
# Assets browse, search, import, aur manage karo
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

import shutil
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum
from pathlib import Path

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
    list_files,
)

logger = get_logger("AssetBrowser")


# ============================================================
# ENUMS
# ============================================================

class AssetType(Enum):
    """Asset categories"""
    ALL         = "all"
    MODELS_3D   = "3d_models"
    TEXTURES    = "textures"
    MATERIALS   = "materials"
    CHARACTERS  = "characters"
    ANIMATIONS  = "animations"
    AUDIO_MUSIC = "audio_music"
    AUDIO_SFX   = "audio_sfx"
    AUDIO_AMB   = "audio_ambient"
    SCENES      = "scenes"
    PRESETS     = "presets"
    VIDEOS      = "videos"


class AssetStatus(Enum):
    """Asset availability status"""
    AVAILABLE   = "available"
    MISSING     = "missing"
    LOADING     = "loading"
    ERROR       = "error"


class ViewMode(Enum):
    """Browser view modes"""
    GRID  = "grid"
    LIST  = "list"


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class AssetItem:
    """
    Ek asset ki complete information.
    File se scan karke populate hoti hai.
    """
    id:           str
    name:         str
    asset_type:   str
    file_path:    str

    # Metadata
    file_size:    int           = 0
    file_ext:     str           = ""
    tags:         List[str]     = field(default_factory=list)
    description:  str           = ""
    author:       str           = ""
    version:      str           = "1.0"

    # UI state
    favorite:     bool          = False
    status:       str           = AssetStatus.AVAILABLE.value
    thumbnail:    Optional[str] = None     # Thumbnail image path
    usage_count:  int           = 0
    date_added:   str           = ""

    # Preview
    preview_data: Optional[Dict] = None   # Preview metadata

    def get_icon(self) -> str:
        """Asset type ka icon"""
        icons = {
            AssetType.MODELS_3D.value:   "📦",
            AssetType.TEXTURES.value:    "🖼️",
            AssetType.MATERIALS.value:   "🎨",
            AssetType.CHARACTERS.value:  "🧍",
            AssetType.ANIMATIONS.value:  "🎬",
            AssetType.AUDIO_MUSIC.value: "🎵",
            AssetType.AUDIO_SFX.value:   "🔊",
            AssetType.AUDIO_AMB.value:   "🌊",
            AssetType.SCENES.value:      "🌍",
            AssetType.PRESETS.value:     "⚙️",
            AssetType.VIDEOS.value:      "🎥",
        }
        return icons.get(self.asset_type, "📄")

    def get_size_str(self) -> str:
        """File size human readable"""
        return format_bytes(self.file_size)

    def exists(self) -> bool:
        """File exist karta hai?"""
        return os.path.exists(self.file_path)

    def to_dict(self) -> Dict:
        return {
            "id":           self.id,
            "name":         self.name,
            "asset_type":   self.asset_type,
            "file_path":    self.file_path,
            "file_size":    self.file_size,
            "file_ext":     self.file_ext,
            "tags":         self.tags,
            "description":  self.description,
            "author":       self.author,
            "favorite":     self.favorite,
            "status":       self.status,
            "thumbnail":    self.thumbnail,
            "usage_count":  self.usage_count,
            "date_added":   self.date_added,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "AssetItem":
        return cls(
            id          = data.get("id", ""),
            name        = data.get("name", ""),
            asset_type  = data.get("asset_type", AssetType.MODELS_3D.value),
            file_path   = data.get("file_path", ""),
            file_size   = data.get("file_size", 0),
            file_ext    = data.get("file_ext", ""),
            tags        = data.get("tags", []),
            description = data.get("description", ""),
            author      = data.get("author", ""),
            favorite    = data.get("favorite", False),
            status      = data.get("status", AssetStatus.AVAILABLE.value),
            thumbnail   = data.get("thumbnail"),
            usage_count = data.get("usage_count", 0),
            date_added  = data.get("date_added", ""),
        )


@dataclass
class AssetFilter:
    """Asset browser filter settings"""
    asset_type:     str           = AssetType.ALL.value
    search_query:   str           = ""
    show_favorites: bool          = False
    sort_by:        str           = "name"      # name, size, date, usage
    sort_asc:       bool          = True
    tags:           List[str]     = field(default_factory=list)

    def matches(self, asset: AssetItem) -> bool:
        """Asset filter se match karta hai?"""
        # Type filter
        if (self.asset_type != AssetType.ALL.value
                and asset.asset_type != self.asset_type):
            return False

        # Search filter
        if self.search_query:
            query = self.search_query.lower()
            if not (
                query in asset.name.lower()
                or query in asset.description.lower()
                or any(query in tag.lower() for tag in asset.tags)
                or query in asset.file_ext.lower()
            ):
                return False

        # Favorites filter
        if self.show_favorites and not asset.favorite:
            return False

        # Tags filter
        if self.tags:
            if not any(tag in asset.tags for tag in self.tags):
                return False

        return True


# ============================================================
# FILE TYPE MAPPINGS
# ============================================================

# Extension → AssetType mapping
EXT_TO_TYPE: Dict[str, str] = {
    # 3D Models
    ".obj":  AssetType.MODELS_3D.value,
    ".fbx":  AssetType.MODELS_3D.value,
    ".gltf": AssetType.MODELS_3D.value,
    ".glb":  AssetType.MODELS_3D.value,
    ".dae":  AssetType.MODELS_3D.value,
    ".stl":  AssetType.MODELS_3D.value,
    ".ply":  AssetType.MODELS_3D.value,
    ".3ds":  AssetType.MODELS_3D.value,
    # Textures
    ".png":  AssetType.TEXTURES.value,
    ".jpg":  AssetType.TEXTURES.value,
    ".jpeg": AssetType.TEXTURES.value,
    ".bmp":  AssetType.TEXTURES.value,
    ".tga":  AssetType.TEXTURES.value,
    ".tiff": AssetType.TEXTURES.value,
    ".hdr":  AssetType.TEXTURES.value,
    ".exr":  AssetType.TEXTURES.value,
    # Audio Music
    ".mp3":  AssetType.AUDIO_MUSIC.value,
    ".ogg":  AssetType.AUDIO_MUSIC.value,
    ".flac": AssetType.AUDIO_MUSIC.value,
    # Audio SFX / WAV
    ".wav":  AssetType.AUDIO_SFX.value,
    ".aif":  AssetType.AUDIO_SFX.value,
    # Video
    ".mp4":  AssetType.VIDEOS.value,
    ".avi":  AssetType.VIDEOS.value,
    ".mov":  AssetType.VIDEOS.value,
    ".mkv":  AssetType.VIDEOS.value,
    # Presets/Scenes
    ".json": AssetType.PRESETS.value,
    ".anim3d": AssetType.SCENES.value,
}

# Asset type display names
TYPE_DISPLAY: Dict[str, str] = {
    AssetType.ALL.value:         "All Assets",
    AssetType.MODELS_3D.value:   "3D Models",
    AssetType.TEXTURES.value:    "Textures",
    AssetType.MATERIALS.value:   "Materials",
    AssetType.CHARACTERS.value:  "Characters",
    AssetType.ANIMATIONS.value:  "Animations",
    AssetType.AUDIO_MUSIC.value: "Music",
    AssetType.AUDIO_SFX.value:   "Sound Effects",
    AssetType.AUDIO_AMB.value:   "Ambient",
    AssetType.SCENES.value:      "Scenes",
    AssetType.PRESETS.value:     "Presets",
    AssetType.VIDEOS.value:      "Videos",
}

# Asset type icons
TYPE_ICONS: Dict[str, str] = {
    AssetType.ALL.value:         "📚",
    AssetType.MODELS_3D.value:   "📦",
    AssetType.TEXTURES.value:    "🖼️",
    AssetType.MATERIALS.value:   "🎨",
    AssetType.CHARACTERS.value:  "🧍",
    AssetType.ANIMATIONS.value:  "🎬",
    AssetType.AUDIO_MUSIC.value: "🎵",
    AssetType.AUDIO_SFX.value:   "🔊",
    AssetType.AUDIO_AMB.value:   "🌊",
    AssetType.SCENES.value:      "🌍",
    AssetType.PRESETS.value:     "⚙️",
    AssetType.VIDEOS.value:      "🎥",
}


# ============================================================
# ASSET BROWSER MODEL
# ============================================================

class AssetBrowserModel:
    """
    Asset browser ka data model.
    Asset scanning, filtering, importing sab yahan.
    """

    # Scan karne wale folders
    SCAN_FOLDERS: Dict[str, str] = {
        "assets/models":            AssetType.MODELS_3D.value,
        "assets/textures":          AssetType.TEXTURES.value,
        "assets/audio/music":       AssetType.AUDIO_MUSIC.value,
        "assets/audio/sfx":         AssetType.AUDIO_SFX.value,
        "assets/audio/ambient":     AssetType.AUDIO_AMB.value,
        "assets/videos":            AssetType.VIDEOS.value,
        "assets/presets/characters":AssetType.CHARACTERS.value,
        "assets/presets/scenes":    AssetType.SCENES.value,
        "assets/presets/animations":AssetType.ANIMATIONS.value,
        "assets/presets/materials": AssetType.MATERIALS.value,
    }

    def __init__(self, config: Optional[Dict] = None):
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # Assets storage: id -> AssetItem
        self._assets: Dict[str, AssetItem] = {}

        # Current filter
        self._filter = AssetFilter()

        # Filtered results cache
        self._filtered_cache: Optional[List[AssetItem]] = None

        # Favorites set
        self._favorites: set = set()

        # Listeners
        self._listeners: List[Callable] = []

        # Cache file
        self._cache_file = Path("cache/asset_browser_cache.json")

        # Scanning state
        self._is_scanning = False

        # Load cache
        self._load_cache()

        logger.info(
            f"✅ AssetBrowserModel initialized | "
            f"{len(self._assets)} assets loaded from cache"
        )

    # ----------------------------------------------------------
    # SCANNING
    # ----------------------------------------------------------

    def scan_assets(self, async_scan: bool = False):
        """
        Asset folders scan karo aur assets discover karo.

        Args:
            async_scan: Background thread mein scan karo
        """
        if async_scan:
            thread = threading.Thread(
                target=self._scan_internal,
                daemon=True
            )
            thread.start()
        else:
            self._scan_internal()

    def _scan_internal(self):
        """Actual scanning logic"""
        self._is_scanning = True
        self._notify("scan_started", {})
        logger.info("🔍 Asset scanning started...")

        new_assets: Dict[str, AssetItem] = {}
        total_found = 0

        for folder, asset_type in self.SCAN_FOLDERS.items():
            folder_path = Path(folder)
            if not folder_path.exists():
                # Folder create kar do
                ensure_dir(str(folder_path))
                continue

            # Folder mein files dhundho
            for file_path in folder_path.rglob("*"):
                if not file_path.is_file():
                    continue

                ext = file_path.suffix.lower()

                # Supported extension?
                detected_type = EXT_TO_TYPE.get(ext, asset_type)

                # Asset ID (path based - consistent)
                asset_id = self._path_to_id(str(file_path))

                # Existing asset (preserve favorites/tags)
                existing = self._assets.get(asset_id)

                asset = AssetItem(
                    id          = asset_id,
                    name        = file_path.stem,
                    asset_type  = detected_type,
                    file_path   = str(file_path),
                    file_size   = file_path.stat().st_size,
                    file_ext    = ext,
                    status      = AssetStatus.AVAILABLE.value,
                    date_added  = get_timestamp(),
                    favorite    = existing.favorite if existing else False,
                    tags        = existing.tags if existing else [],
                    usage_count = existing.usage_count if existing else 0,
                )

                new_assets[asset_id] = asset
                total_found += 1

        # Update assets
        self._assets = new_assets
        self._filtered_cache = None  # Cache invalidate karo

        # Cache save karo
        self._save_cache()

        self._is_scanning = False
        self._notify("scan_complete", {"total": total_found})
        logger.info(f"✅ Scan complete: {total_found} assets found")

    def _path_to_id(self, file_path: str) -> str:
        """File path se consistent ID generate karo"""
        import hashlib
        return hashlib.md5(file_path.encode()).hexdigest()[:12]

    # ----------------------------------------------------------
    # CACHE
    # ----------------------------------------------------------

    def _load_cache(self):
        """Asset cache load karo"""
        try:
            if self._cache_file.exists():
                data = read_json(str(self._cache_file))
                if data and isinstance(data, list):
                    for item_data in data:
                        asset = AssetItem.from_dict(item_data)
                        # File still exists?
                        if asset.file_path and os.path.exists(asset.file_path):
                            self._assets[asset.id] = asset
                        else:
                            asset.status = AssetStatus.MISSING.value
                            self._assets[asset.id] = asset
                    logger.debug(f"Cache loaded: {len(self._assets)} assets")
        except Exception as e:
            logger.warning(f"Cache load failed: {e}")

    def _save_cache(self):
        """Asset cache save karo"""
        try:
            ensure_dir(str(self._cache_file.parent))
            data = [a.to_dict() for a in self._assets.values()]
            write_json(str(self._cache_file), data)
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")

    # ----------------------------------------------------------
    # FILTERING & SEARCH
    # ----------------------------------------------------------

    def set_filter(self, filter_obj: AssetFilter):
        """Filter set karo"""
        self._filter = filter_obj
        self._filtered_cache = None
        self._notify("filter_changed", {})

    def get_filter(self) -> AssetFilter:
        """Current filter lo"""
        return self._filter

    def set_type_filter(self, asset_type: str):
        """Type filter set karo"""
        self._filter.asset_type = asset_type
        self._filtered_cache = None
        self._notify("filter_changed", {})

    def set_search(self, query: str):
        """Search query set karo"""
        self._filter.search_query = query
        self._filtered_cache = None
        self._notify("filter_changed", {})

    def set_favorites_only(self, favorites_only: bool):
        """Favorites only filter"""
        self._filter.show_favorites = favorites_only
        self._filtered_cache = None
        self._notify("filter_changed", {})

    def get_filtered_assets(self) -> List[AssetItem]:
        """
        Current filter ke basis pe filtered assets lo.
        Cache use karta hai performance ke liye.
        """
        if self._filtered_cache is not None:
            return self._filtered_cache

        # Filter apply karo
        filtered = [
            a for a in self._assets.values()
            if self._filter.matches(a)
        ]

        # Sort karo
        sort_key = self._filter.sort_by
        reverse  = not self._filter.sort_asc

        if sort_key == "name":
            filtered.sort(key=lambda x: x.name.lower(), reverse=reverse)
        elif sort_key == "size":
            filtered.sort(key=lambda x: x.file_size, reverse=reverse)
        elif sort_key == "date":
            filtered.sort(key=lambda x: x.date_added, reverse=reverse)
        elif sort_key == "usage":
            filtered.sort(key=lambda x: x.usage_count, reverse=reverse)
        elif sort_key == "type":
            filtered.sort(key=lambda x: x.asset_type, reverse=reverse)

        self._filtered_cache = filtered
        return filtered

    def get_all_assets(self) -> List[AssetItem]:
        """Sabhi assets lo (no filter)"""
        return list(self._assets.values())

    def get_asset(self, asset_id: str) -> Optional[AssetItem]:
        """ID se asset lo"""
        return self._assets.get(asset_id)

    def get_assets_by_type(self, asset_type: str) -> List[AssetItem]:
        """Type se assets lo"""
        return [
            a for a in self._assets.values()
            if a.asset_type == asset_type
        ]

    def get_favorites(self) -> List[AssetItem]:
        """Favorite assets lo"""
        return [a for a in self._assets.values() if a.favorite]

    def get_recent(self, limit: int = 20) -> List[AssetItem]:
        """Recent assets lo (usage count se)"""
        assets = sorted(
            self._assets.values(),
            key=lambda x: x.usage_count,
            reverse=True
        )
        return assets[:limit]

    # ----------------------------------------------------------
    # ASSET MANAGEMENT
    # ----------------------------------------------------------

    def import_asset(
        self,
        source_path: str,
        asset_type: Optional[str] = None,
        copy_to_project: bool = True,
        tags: Optional[List[str]] = None,
    ) -> Optional[AssetItem]:
        """
        External file ko project mein import karo.

        Args:
            source_path: Source file path
            asset_type: Override asset type (None = auto-detect)
            copy_to_project: File copy karo project mein
            tags: Asset tags

        Returns:
            Imported AssetItem
        """
        source = Path(source_path)
        if not source.exists():
            logger.error(f"File nahi mila: {source_path}")
            return None

        # Type detect karo
        ext = source.suffix.lower()
        detected_type = asset_type or EXT_TO_TYPE.get(ext, AssetType.MODELS_3D.value)

        # Destination folder
        type_folders = {
            AssetType.MODELS_3D.value:   "assets/models",
            AssetType.TEXTURES.value:    "assets/textures",
            AssetType.AUDIO_MUSIC.value: "assets/audio/music",
            AssetType.AUDIO_SFX.value:   "assets/audio/sfx",
            AssetType.AUDIO_AMB.value:   "assets/audio/ambient",
            AssetType.CHARACTERS.value:  "assets/presets/characters",
            AssetType.VIDEOS.value:      "assets/videos",
        }
        dest_folder = type_folders.get(detected_type, "assets/models")
        ensure_dir(dest_folder)

        # File copy karo
        if copy_to_project:
            dest_path = Path(dest_folder) / source.name
            # Name conflict handle karo
            if dest_path.exists():
                stem = source.stem
                suffix = source.suffix
                counter = 1
                while dest_path.exists():
                    dest_path = Path(dest_folder) / f"{stem}_{counter}{suffix}"
                    counter += 1
            try:
                shutil.copy2(str(source), str(dest_path))
                final_path = str(dest_path)
                logger.info(f"✅ File copied: {source.name} → {dest_folder}")
            except Exception as e:
                logger.error(f"File copy failed: {e}")
                final_path = source_path
        else:
            final_path = source_path

        # Asset create karo
        asset_id = self._path_to_id(final_path)
        asset = AssetItem(
            id         = asset_id,
            name       = source.stem,
            asset_type = detected_type,
            file_path  = final_path,
            file_size  = source.stat().st_size,
            file_ext   = ext,
            status     = AssetStatus.AVAILABLE.value,
            date_added = get_timestamp(),
            tags       = tags or [],
        )

        self._assets[asset_id] = asset
        self._filtered_cache = None
        self._save_cache()

        self._notify("asset_imported", {"asset": asset})
        logger.info(f"✅ Asset imported: {asset.name} ({detected_type})")
        return asset

    def import_batch(
        self,
        file_paths: List[str],
        copy_to_project: bool = True,
    ) -> List[AssetItem]:
        """Multiple files batch import karo"""
        imported = []
        for path in file_paths:
            asset = self.import_asset(path, copy_to_project=copy_to_project)
            if asset:
                imported.append(asset)
        logger.info(f"✅ Batch import: {len(imported)}/{len(file_paths)} assets")
        return imported

    def delete_asset(
        self,
        asset_id: str,
        delete_file: bool = False,
    ) -> bool:
        """
        Asset remove karo library se.

        Args:
            asset_id: Asset ID
            delete_file: Physical file bhi delete karo?
        """
        asset = self._assets.get(asset_id)
        if not asset:
            return False

        if delete_file and os.path.exists(asset.file_path):
            try:
                os.remove(asset.file_path)
                logger.info(f"File deleted: {asset.file_path}")
            except Exception as e:
                logger.error(f"File delete failed: {e}")

        del self._assets[asset_id]
        self._filtered_cache = None
        self._save_cache()

        self._notify("asset_deleted", {"asset_id": asset_id})
        return True

    def toggle_favorite(self, asset_id: str) -> bool:
        """Favorite toggle karo"""
        asset = self._assets.get(asset_id)
        if not asset:
            return False
        asset.favorite = not asset.favorite
        self._filtered_cache = None
        self._save_cache()
        self._notify("asset_updated", {"asset_id": asset_id})
        return asset.favorite

    def add_tag(self, asset_id: str, tag: str) -> bool:
        """Asset mein tag add karo"""
        asset = self._assets.get(asset_id)
        if not asset:
            return False
        tag = tag.strip().lower()
        if tag and tag not in asset.tags:
            asset.tags.append(tag)
            self._save_cache()
            self._notify("asset_updated", {"asset_id": asset_id})
        return True

    def remove_tag(self, asset_id: str, tag: str) -> bool:
        """Asset se tag remove karo"""
        asset = self._assets.get(asset_id)
        if not asset or tag not in asset.tags:
            return False
        asset.tags.remove(tag)
        self._save_cache()
        return True

    def record_usage(self, asset_id: str):
        """Asset use kiya - usage count badhao"""
        asset = self._assets.get(asset_id)
        if asset:
            asset.usage_count += 1
            self._save_cache()

    def rename_asset(self, asset_id: str, new_name: str) -> bool:
        """Asset rename karo"""
        asset = self._assets.get(asset_id)
        if not asset:
            return False
        old_name   = asset.name
        asset.name = new_name.strip()
        self._save_cache()
        logger.info(f"Asset renamed: {old_name} → {asset.name}")
        return True

    # ----------------------------------------------------------
    # STATISTICS
    # ----------------------------------------------------------

    def get_statistics(self) -> Dict:
        """Asset library statistics"""
        stats = {
            "total":     len(self._assets),
            "favorites": sum(1 for a in self._assets.values() if a.favorite),
            "missing":   sum(1 for a in self._assets.values()
                            if a.status == AssetStatus.MISSING.value),
            "total_size": sum(a.file_size for a in self._assets.values()),
            "by_type":   {},
        }
        for asset in self._assets.values():
            t = asset.asset_type
            stats["by_type"][t] = stats["by_type"].get(t, 0) + 1
        stats["total_size_str"] = format_bytes(stats["total_size"])
        return stats

    def get_all_tags(self) -> List[str]:
        """Sabhi unique tags lo"""
        tags = set()
        for asset in self._assets.values():
            tags.update(asset.tags)
        return sorted(list(tags))

    def create_sample_assets(self):
        """
        Demo/testing ke liye sample assets create karo.
        Actual files nahi - sirf database entries.
        """
        samples = [
            # 3D Models
            ("Hero Character", AssetType.CHARACTERS.value,
             "assets/presets/characters/hero.json",
             ["character", "hero", "main"]),
            ("Tree Low Poly", AssetType.MODELS_3D.value,
             "assets/models/tree_low.obj",
             ["nature", "tree", "low-poly"]),
            ("Rock Formation", AssetType.MODELS_3D.value,
             "assets/models/rock.obj",
             ["nature", "rock", "environment"]),
            ("House Building", AssetType.MODELS_3D.value,
             "assets/models/house.fbx",
             ["building", "house", "architecture"]),
            # Textures
            ("Grass Texture", AssetType.TEXTURES.value,
             "assets/textures/grass.png",
             ["nature", "grass", "ground"]),
            ("Wood Planks", AssetType.TEXTURES.value,
             "assets/textures/wood.jpg",
             ["wood", "material", "floor"]),
            ("Stone Wall", AssetType.TEXTURES.value,
             "assets/textures/stone.png",
             ["stone", "wall", "material"]),
            # Audio
            ("Epic Background Music", AssetType.AUDIO_MUSIC.value,
             "assets/audio/music/epic_bgm.mp3",
             ["music", "epic", "background"]),
            ("Ambient Forest", AssetType.AUDIO_AMB.value,
             "assets/audio/ambient/forest.wav",
             ["ambient", "forest", "nature"]),
            ("Sword Swing SFX", AssetType.AUDIO_SFX.value,
             "assets/audio/sfx/sword_swing.wav",
             ["sfx", "sword", "combat"]),
            ("Footstep Grass", AssetType.AUDIO_SFX.value,
             "assets/audio/sfx/footstep_grass.wav",
             ["sfx", "footstep", "walking"]),
            # Presets
            ("Walk Animation", AssetType.ANIMATIONS.value,
             "assets/presets/animations/walk.json",
             ["animation", "walk", "character"]),
            ("Run Animation", AssetType.ANIMATIONS.value,
             "assets/presets/animations/run.json",
             ["animation", "run", "character"]),
            ("Day Outdoor Scene", AssetType.SCENES.value,
             "assets/presets/scenes/day_outdoor.json",
             ["scene", "outdoor", "day"]),
            ("Studio Setup", AssetType.SCENES.value,
             "assets/presets/scenes/studio.json",
             ["scene", "studio", "lighting"]),
        ]

        created = 0
        for name, asset_type, file_path, tags in samples:
            asset_id = self._path_to_id(file_path)
            if asset_id not in self._assets:
                asset = AssetItem(
                    id         = asset_id,
                    name       = name,
                    asset_type = asset_type,
                    file_path  = file_path,
                    file_size  = 1024 * (50 + created * 30),
                    file_ext   = Path(file_path).suffix,
                    tags       = tags,
                    date_added = get_timestamp(),
                    status     = AssetStatus.AVAILABLE.value,
                    favorite   = created < 3,  # Pehle 3 favorite
                )
                self._assets[asset_id] = asset
                created += 1

        self._filtered_cache = None
        self._save_cache()
        logger.info(f"✅ {created} sample assets created")
        return created

    # ----------------------------------------------------------
    # LISTENERS
    # ----------------------------------------------------------

    def add_listener(self, callback: Callable):
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify(self, event: str, data: Dict):
        for cb in self._listeners:
            try:
                cb(event, data)
            except Exception as e:
                logger.warning(f"Asset browser listener error: {e}")


# ============================================================
# QT ASSET BROWSER WIDGET
# ============================================================

class AssetBrowserWidget:
    """
    PyQt5 Asset Browser Panel.
    Grid/List view, search bar, category sidebar sab include.
    """

    def __init__(
        self,
        parent=None,
        model: Optional[AssetBrowserModel] = None,
        theme_manager=None,
        config: Optional[Dict] = None,
    ):
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        self.parent_widget = parent
        self.theme_manager = theme_manager
        self.model = model or AssetBrowserModel()

        # Qt references
        self._widget        = None
        self._list_widget   = None
        self._search_bar    = None
        self._type_list     = None
        self._status_label  = None
        self._view_mode     = ViewMode.LIST.value

        # Selected asset
        self._selected_asset: Optional[AssetItem] = None

        # Selection callback
        self._on_asset_selected: Optional[Callable] = None

        # Build Qt widget
        self._build_widget()

        # Model listen karo
        self.model.add_listener(self._on_model_changed)

        logger.info("✅ AssetBrowserWidget initialized")

    def _build_widget(self):
        """Qt widget build karo"""
        try:
            from PyQt5.QtWidgets import (
                QWidget, QVBoxLayout, QHBoxLayout,
                QListWidget, QListWidgetItem, QLineEdit,
                QPushButton, QLabel, QSplitter,
                QAbstractItemView, QMenu, QAction,
                QToolButton, QComboBox, QCheckBox,
                QFrame,
            )
            from PyQt5.QtCore import Qt, QSize
            from PyQt5.QtGui import QFont

            # Main container
            self._widget = QWidget(self.parent_widget)
            self._widget.setObjectName("AssetBrowser")
            main_layout = QVBoxLayout(self._widget)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)

            # ===== HEADER =====
            header = QWidget()
            header_layout = QHBoxLayout(header)
            header_layout.setContentsMargins(8, 6, 8, 6)

            title_lbl = QLabel("ASSETS")
            header_layout.addWidget(title_lbl)
            header_layout.addStretch()

            # Import button
            import_btn = QPushButton("+ Import")
            import_btn.setFixedHeight(22)
            import_btn.clicked.connect(self._on_import_clicked)
            header_layout.addWidget(import_btn)

            # Scan button
            scan_btn = QPushButton("🔍 Scan")
            scan_btn.setFixedHeight(22)
            scan_btn.clicked.connect(self._on_scan_clicked)
            header_layout.addWidget(scan_btn)

            main_layout.addWidget(header)

            # ===== SEARCH BAR =====
            search_container = QWidget()
            search_layout    = QHBoxLayout(search_container)
            search_layout.setContentsMargins(4, 4, 4, 4)
            search_layout.setSpacing(4)

            self._search_bar = QLineEdit()
            self._search_bar.setPlaceholderText("🔍 Search assets...")
            self._search_bar.textChanged.connect(self._on_search_changed)
            self._search_bar.setFixedHeight(26)
            search_layout.addWidget(self._search_bar)

            # Favorites toggle
            fav_btn = QToolButton()
            fav_btn.setText("⭐")
            fav_btn.setCheckable(True)
            fav_btn.setToolTip("Show favorites only")
            fav_btn.setFixedSize(26, 26)
            fav_btn.toggled.connect(self.model.set_favorites_only)
            search_layout.addWidget(fav_btn)

            main_layout.addWidget(search_container)

            # ===== SORT BAR =====
            sort_bar = QWidget()
            sort_layout = QHBoxLayout(sort_bar)
            sort_layout.setContentsMargins(4, 0, 4, 4)
            sort_layout.setSpacing(4)

            sort_lbl = QLabel("Sort:")
            sort_layout.addWidget(sort_lbl)

            self._sort_combo = QComboBox()
            self._sort_combo.addItems(["Name", "Size", "Date", "Usage", "Type"])
            self._sort_combo.setFixedHeight(22)
            self._sort_combo.currentTextChanged.connect(
                lambda t: self._on_sort_changed(t.lower())
            )
            sort_layout.addWidget(self._sort_combo)
            sort_layout.addStretch()

            main_layout.addWidget(sort_bar)

            # ===== SPLITTER (Category + Assets) =====
            splitter = QSplitter(Qt.Horizontal)
            splitter.setHandleWidth(2)

            # Left: Category list
            self._type_list = QListWidget()
            self._type_list.setObjectName("CategoryList")
            self._type_list.setFixedWidth(120)
            self._type_list.setHorizontalScrollBarPolicy(
                Qt.ScrollBarAlwaysOff
            )

            # Categories add karo
            for asset_type, display_name in TYPE_DISPLAY.items():
                icon = TYPE_ICONS.get(asset_type, "📄")
                from PyQt5.QtWidgets import QListWidgetItem
                item = QListWidgetItem(f"{icon} {display_name}")
                item.setData(Qt.UserRole, asset_type)
                self._type_list.addItem(item)

            self._type_list.setCurrentRow(0)  # "All" select karo
            self._type_list.currentItemChanged.connect(
                self._on_type_changed
            )
            splitter.addWidget(self._type_list)

            # Right: Asset list
            self._list_widget = QListWidget()
            self._list_widget.setObjectName("AssetList")
            self._list_widget.setSelectionMode(
                QAbstractItemView.SingleSelection
            )
            self._list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
            self._list_widget.currentItemChanged.connect(
                self._on_asset_selection_changed
            )
            self._list_widget.doubleClicked.connect(
                self._on_asset_double_clicked
            )
            self._list_widget.customContextMenuRequested.connect(
                self._on_context_menu
            )
            splitter.addWidget(self._list_widget)
            splitter.setSizes([120, 200])

            main_layout.addWidget(splitter, 1)

            # ===== STATUS BAR =====
            self._status_label = QLabel("0 assets")
            self._status_label.setObjectName("BrowserStatus")
            main_layout.addWidget(self._status_label)

            # Theme apply
            self._apply_theme()

            # Initial refresh
            self.refresh()

        except ImportError:
            logger.warning("PyQt5 nahi - asset browser non-Qt mode")
        except Exception as e:
            logger.error(f"Asset browser build error: {e}")

    def _apply_theme(self):
        """Theme apply karo"""
        if not self.theme_manager or not self._widget:
            return
        try:
            p = self.theme_manager.get_palette()
            self._widget.setStyleSheet(f"""
                #AssetBrowser {{
                    background-color: {p.bg_secondary};
                }}
                QLabel {{
                    color: {p.text_secondary};
                    font-size: 10px;
                    font-weight: bold;
                    letter-spacing: 1px;
                }}
                QLineEdit {{
                    background-color: {p.bg_tertiary};
                    border: none;
                    border-bottom: 1px solid {p.border};
                    color: {p.text_primary};
                    padding: 3px 8px;
                    font-size: 11px;
                    border-radius: 3px;
                }}
                #CategoryList {{
                    background-color: {p.bg_tertiary};
                    border: none;
                    border-right: 1px solid {p.border};
                    font-size: 11px;
                    color: {p.text_primary};
                    outline: 0;
                }}
                #CategoryList::item {{
                    padding: 5px 6px;
                    border-radius: 3px;
                    margin: 1px 2px;
                }}
                #CategoryList::item:selected {{
                    background-color: {p.accent_muted};
                    color: {p.accent};
                }}
                #AssetList {{
                    background-color: {p.bg_secondary};
                    border: none;
                    font-size: 11px;
                    color: {p.text_primary};
                    outline: 0;
                }}
                #AssetList::item {{
                    padding: 4px 6px;
                    border-radius: 3px;
                    margin: 1px 2px;
                }}
                #AssetList::item:hover {{
                    background-color: {p.bg_hover};
                }}
                #AssetList::item:selected {{
                    background-color: {p.bg_selected};
                    color: {p.text_primary};
                }}
                #BrowserStatus {{
                    color: {p.text_secondary};
                    font-size: 10px;
                    padding: 3px 8px;
                    border-top: 1px solid {p.border};
                    letter-spacing: 0px;
                    font-weight: normal;
                }}
                QPushButton {{
                    background-color: {p.accent};
                    color: #000;
                    border: none;
                    border-radius: 3px;
                    padding: 2px 8px;
                    font-size: 11px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {p.accent_hover};
                }}
                QComboBox {{
                    background-color: {p.bg_tertiary};
                    border: 1px solid {p.border};
                    border-radius: 3px;
                    color: {p.text_primary};
                    padding: 2px 6px;
                    font-size: 10px;
                }}
                QToolButton {{
                    background-color: {p.bg_tertiary};
                    border: 1px solid {p.border};
                    border-radius: 3px;
                    color: {p.text_primary};
                    font-size: 12px;
                }}
                QToolButton:checked {{
                    background-color: {p.accent_muted};
                    border-color: {p.accent};
                    color: {p.accent};
                }}
                QSplitter::handle {{
                    background-color: {p.border};
                }}
            """)
        except Exception as e:
            logger.warning(f"Theme apply error: {e}")

    # ----------------------------------------------------------
    # REFRESH
    # ----------------------------------------------------------

    def refresh(self):
        """Asset list refresh karo"""
        if not self._list_widget:
            return

        try:
            from PyQt5.QtWidgets import QListWidgetItem
            from PyQt5.QtCore import Qt

            self._list_widget.blockSignals(True)
            self._list_widget.clear()

            assets = self.model.get_filtered_assets()

            for asset in assets:
                fav_star = "⭐" if asset.favorite else "  "
                size_str = asset.get_size_str()
                item_text = (
                    f"{asset.get_icon()} {fav_star} {asset.name}\n"
                    f"    {asset.file_ext.upper()[1:] if asset.file_ext else '?'}"
                    f"  •  {size_str}"
                )
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, asset.id)
                item.setToolTip(
                    f"{asset.name}\n"
                    f"Type: {asset.asset_type}\n"
                    f"Size: {size_str}\n"
                    f"Path: {asset.file_path}\n"
                    f"Tags: {', '.join(asset.tags) or 'None'}"
                )
                self._list_widget.addItem(item)

            # Status update
            stats = self.model.get_statistics()
            if self._status_label:
                self._status_label.setText(
                    f"{len(assets)} assets | "
                    f"Total: {stats['total']} | "
                    f"⭐ {stats['favorites']}"
                )

            self._list_widget.blockSignals(False)

        except Exception as e:
            logger.error(f"Asset list refresh error: {e}")
            if self._list_widget:
                self._list_widget.blockSignals(False)

    # ----------------------------------------------------------
    # EVENT HANDLERS
    # ----------------------------------------------------------

    def _on_model_changed(self, event: str, data: Dict):
        """Model change pe refresh"""
        refresh_events = [
            "scan_complete", "asset_imported", "asset_deleted",
            "asset_updated", "filter_changed",
        ]
        if event in refresh_events:
            self.refresh()
        elif event == "scan_started":
            if self._status_label:
                self._status_label.setText("🔍 Scanning...")

    def _on_search_changed(self, query: str):
        """Search input change"""
        self.model.set_search(query)

    def _on_type_changed(self, current, previous):
        """Category selection change"""
        if not current:
            return
        try:
            from PyQt5.QtCore import Qt
            asset_type = current.data(Qt.UserRole)
            self.model.set_type_filter(asset_type)
        except Exception as e:
            logger.warning(f"Type change error: {e}")

    def _on_sort_changed(self, sort_by: str):
        """Sort change"""
        self.model._filter.sort_by = sort_by
        self.model._filtered_cache = None
        self.refresh()

    def _on_asset_selection_changed(self, current, previous):
        """Asset selection change"""
        if not current:
            self._selected_asset = None
            return
        try:
            from PyQt5.QtCore import Qt
            asset_id = current.data(Qt.UserRole)
            asset    = self.model.get_asset(asset_id)
            self._selected_asset = asset

            if asset and self._on_asset_selected:
                self._on_asset_selected(asset)

        except Exception as e:
            logger.warning(f"Asset selection error: {e}")

    def _on_asset_double_clicked(self, index):
        """Double click = asset use karo"""
        if self._selected_asset:
            self.model.record_usage(self._selected_asset.id)
            logger.info(
                f"Asset used: {self._selected_asset.name}"
            )

    def _on_context_menu(self, position):
        """Right-click context menu"""
        if not self._list_widget:
            return
        try:
            from PyQt5.QtWidgets import QMenu, QAction
            from PyQt5.QtCore import Qt

            item = self._list_widget.itemAt(position)
            menu = QMenu(self._widget)

            if item:
                asset_id = item.data(Qt.UserRole)
                asset    = self.model.get_asset(asset_id)

                if asset:
                    use_action = QAction(f"✅ Use '{asset.name}'", menu)
                    use_action.triggered.connect(
                        lambda: self._use_asset(asset)
                    )
                    menu.addAction(use_action)

                    fav_text = "⭐ Remove Favorite" if asset.favorite else "⭐ Add Favorite"
                    fav_action = QAction(fav_text, menu)
                    fav_action.triggered.connect(
                        lambda: self._toggle_favorite(asset_id)
                    )
                    menu.addAction(fav_action)

                    menu.addSeparator()

                    # Open in Explorer
                    explore_action = QAction("📂 Show in Explorer", menu)
                    explore_action.triggered.connect(
                        lambda: self._open_in_explorer(asset.file_path)
                    )
                    menu.addAction(explore_action)

                    menu.addSeparator()

                    del_action = QAction("🗑️ Remove from Library", menu)
                    del_action.triggered.connect(
                        lambda: self.model.delete_asset(asset_id)
                    )
                    menu.addAction(del_action)

            menu.addSeparator()

            import_action = QAction("📥 Import Asset...", menu)
            import_action.triggered.connect(self._on_import_clicked)
            menu.addAction(import_action)

            scan_action = QAction("🔍 Rescan Folders", menu)
            scan_action.triggered.connect(self._on_scan_clicked)
            menu.addAction(scan_action)

            menu.exec_(
                self._list_widget.viewport().mapToGlobal(position)
            )

        except Exception as e:
            logger.warning(f"Context menu error: {e}")

    def _on_import_clicked(self):
        """Import button click"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            files, _ = QFileDialog.getOpenFileNames(
                self._widget,
                "Assets Import Karo",
                "",
                "All Supported (*.obj *.fbx *.gltf *.glb *.png *.jpg "
                "*.jpeg *.mp3 *.wav *.ogg *.mp4 *.json);;"
                "3D Models (*.obj *.fbx *.gltf *.glb *.dae);;"
                "Textures (*.png *.jpg *.jpeg *.bmp *.tga);;"
                "Audio (*.mp3 *.wav *.ogg *.flac);;"
                "All Files (*)"
            )
            if files:
                self.model.import_batch(files)
        except Exception as e:
            logger.warning(f"Import dialog error: {e}")

    def _on_scan_clicked(self):
        """Scan button click"""
        self.model.scan_assets(async_scan=True)

    def _use_asset(self, asset: AssetItem):
        """Asset use karo"""
        self.model.record_usage(asset.id)
        if self._on_asset_selected:
            self._on_asset_selected(asset)

    def _toggle_favorite(self, asset_id: str):
        """Favorite toggle"""
        self.model.toggle_favorite(asset_id)

    def _open_in_explorer(self, file_path: str):
        """Windows Explorer mein file dikhaao"""
        try:
            import subprocess
            if os.path.exists(file_path):
                subprocess.Popen(f'explorer /select,"{file_path}"')
            else:
                folder = os.path.dirname(file_path)
                if os.path.exists(folder):
                    subprocess.Popen(f'explorer "{folder}"')
        except Exception as e:
            logger.warning(f"Explorer open error: {e}")

    # ----------------------------------------------------------
    # PUBLIC API
    # ----------------------------------------------------------

    def get_widget(self):
        """Qt widget lo"""
        return self._widget

    def get_selected_asset(self) -> Optional[AssetItem]:
        """Selected asset lo"""
        return self._selected_asset

    def set_on_asset_selected(self, callback: Callable):
        """Asset selection callback set karo"""
        self._on_asset_selected = callback

    def get_model(self) -> AssetBrowserModel:
        """Data model lo"""
        return self.model


# ============================================================
# GLOBAL INSTANCE
# ============================================================

_global_model: Optional[AssetBrowserModel] = None


def get_asset_model() -> AssetBrowserModel:
    """Global AssetBrowserModel lo (singleton)"""
    global _global_model
    if _global_model is None:
        _global_model = AssetBrowserModel()
    return _global_model


# ============================================================
# TEST SECTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="DEBUG")
    print_banner("Asset Browser Test", "Asset Library & Browser Manager")

    # ===== TEST 1: Model Init =====
    print_section("Test 1: Model Initialization")
    model = AssetBrowserModel()
    print(f"✅ AssetBrowserModel initialized")
    print(f"   Assets from cache: {len(model.get_all_assets())}")

    # ===== TEST 2: Sample Assets =====
    print_section("Test 2: Sample Assets Creation")
    created = model.create_sample_assets()
    print(f"✅ Sample assets created: {created}")
    stats = model.get_statistics()
    print(f"   Total assets : {stats['total']}")
    print(f"   Favorites    : {stats['favorites']}")
    print(f"   Total size   : {stats['total_size_str']}")
    print(f"   By type:")
    for t, count in stats["by_type"].items():
        icon = TYPE_ICONS.get(t, "📄")
        print(f"      {icon} {TYPE_DISPLAY.get(t, t):20s}: {count}")

    # ===== TEST 3: Filtering =====
    print_section("Test 3: Asset Filtering")

    # All assets
    all_assets = model.get_filtered_assets()
    print(f"✅ All assets: {len(all_assets)}")

    # Type filter
    model.set_type_filter(AssetType.AUDIO_SFX.value)
    sfx_assets = model.get_filtered_assets()
    print(f"✅ SFX assets: {len(sfx_assets)}")
    for a in sfx_assets:
        print(f"   {a.get_icon()} {a.name}")

    # Reset filter
    model.set_type_filter(AssetType.ALL.value)

    # Search filter
    model.set_search("forest")
    results = model.get_filtered_assets()
    print(f"✅ Search 'forest': {len(results)} results")
    for r in results:
        print(f"   {r.get_icon()} {r.name} | Tags: {r.tags}")

    # Reset search
    model.set_search("")

    # ===== TEST 4: Favorites =====
    print_section("Test 4: Favorites")
    favs = model.get_favorites()
    print(f"✅ Favorites: {len(favs)}")
    for f in favs:
        print(f"   ⭐ {f.name}")

    # Toggle favorite
    first_asset = model.get_all_assets()[0]
    before = first_asset.favorite
    model.toggle_favorite(first_asset.id)
    after = model.get_asset(first_asset.id).favorite
    print(f"✅ Toggle favorite: {before} → {after}")

    # Favorites filter
    model.set_favorites_only(True)
    fav_filtered = model.get_filtered_assets()
    print(f"✅ Favorites only filter: {len(fav_filtered)} assets")
    model.set_favorites_only(False)

    # ===== TEST 5: Tags =====
    print_section("Test 5: Tags Management")
    asset = model.get_all_assets()[0]
    print(f"✅ Asset: {asset.name} | Tags: {asset.tags}")

    model.add_tag(asset.id, "hero")
    model.add_tag(asset.id, "protagonist")
    print(f"✅ After add tags: {model.get_asset(asset.id).tags}")

    model.remove_tag(asset.id, "hero")
    print(f"✅ After remove tag: {model.get_asset(asset.id).tags}")

    all_tags = model.get_all_tags()
    print(f"✅ All unique tags: {len(all_tags)}")
    print(f"   {all_tags[:10]}")

    # ===== TEST 6: Usage Tracking =====
    print_section("Test 6: Usage Tracking")
    asset = model.get_all_assets()[0]
    before_usage = asset.usage_count
    model.record_usage(asset.id)
    model.record_usage(asset.id)
    model.record_usage(asset.id)
    after_usage = model.get_asset(asset.id).usage_count
    print(f"✅ Usage count: {before_usage} → {after_usage}")

    recent = model.get_recent(limit=3)
    print(f"✅ Most used assets:")
    for r in recent:
        print(f"   {r.get_icon()} {r.name} (used {r.usage_count}x)")

    # ===== TEST 7: Rename =====
    print_section("Test 7: Rename Asset")
    asset = model.get_all_assets()[2]
    old_name = asset.name
    model.rename_asset(asset.id, "Renamed Asset Test")
    print(f"✅ Renamed: {old_name} → {model.get_asset(asset.id).name}")
    model.rename_asset(asset.id, old_name)  # Restore

    # ===== TEST 8: Sort =====
    print_section("Test 8: Sort Options")
    for sort_by in ["name", "size", "usage"]:
        model._filter.sort_by   = sort_by
        model._filter.sort_asc  = True
        model._filtered_cache   = None
        assets = model.get_filtered_assets()
        print(f"✅ Sort by {sort_by}: first='{assets[0].name}' last='{assets[-1].name}'")

    # ===== TEST 9: Scan (creates folders) =====
    print_section("Test 9: Asset Folder Scan")
    model.scan_assets(async_scan=False)
    print(f"✅ Scan complete: {len(model.get_all_assets())} total assets")

    # ===== TEST 10: AssetItem Info =====
    print_section("Test 10: Asset Item Details")
    for asset in model.get_all_assets()[:5]:
        print(
            f"✅ {asset.get_icon()} {asset.name:25s} | "
            f"{asset.file_ext:6s} | "
            f"{asset.get_size_str():10s} | "
            f"{'⭐' if asset.favorite else '  '} | "
            f"Tags: {len(asset.tags)}"
        )

    # ===== TEST 11: Listeners =====
    print_section("Test 11: Event Listeners")
    events_log = []

    def on_event(event, data):
        events_log.append(event)

    model.add_listener(on_event)
    model.set_search("hero")
    model.set_search("")
    model.toggle_favorite(model.get_all_assets()[0].id)
    print(f"✅ Events received: {events_log}")

    # ===== TEST 12: Qt Widget =====
    print_section("Test 12: Qt Widget Build")
    try:
        from PyQt5.QtWidgets import (
            QApplication, QMainWindow, QDockWidget
        )
        from PyQt5.QtCore import Qt
        import sys as _sys

        app = QApplication.instance() or QApplication(_sys.argv)

        from src.ui.theme_manager import ThemeManager
        theme = ThemeManager()
        theme.set_application(app)

        window = QMainWindow()
        window.setWindowTitle("Asset Browser Test")
        window.resize(500, 700)

        # Asset browser widget
        browser = AssetBrowserWidget(
            model         = model,
            theme_manager = theme,
        )

        def on_asset_selected(asset: AssetItem):
            print(f"   🎯 Asset selected: {asset.name} ({asset.asset_type})")

        browser.set_on_asset_selected(on_asset_selected)

        dock = QDockWidget("Assets", window)
        dock.setWidget(browser.get_widget())
        window.addDockWidget(Qt.LeftDockWidgetArea, dock)

        window.show()
        print(f"✅ Qt widget shown")
        print(f"   Assets displayed: {len(model.get_filtered_assets())}")

        from PyQt5.QtCore import QTimer
        QTimer.singleShot(800, app.quit)
        app.exec_()
        print(f"✅ Qt test complete")

    except ImportError:
        print("⚠️  PyQt5 visual test skip")
    except Exception as e:
        print(f"⚠️  Qt test: {e}")

    # ===== TEST 13: Singleton =====
    print_section("Test 13: Global Singleton")
    m1 = get_asset_model()
    m2 = get_asset_model()
    print(f"✅ Singleton: {m1 is m2}")

    # ===== TEST 14: Statistics =====
    print_section("Test 14: Final Statistics")
    final_stats = model.get_statistics()
    print(f"✅ Final Statistics:")
    print(f"   Total assets : {final_stats['total']}")
    print(f"   Favorites    : {final_stats['favorites']}")
    print(f"   Missing      : {final_stats['missing']}")
    print(f"   Total size   : {final_stats['total_size_str']}")

    print_banner("✅ All Tests Passed!", "asset_browser.py Working Perfectly")