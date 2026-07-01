# ============================================================
# 3D ANIMATION STUDIO - Asset Library (Core)
# ============================================================
# Features:
# - Asset discovery aur cataloging
# - Categories: models, textures, audio, presets
# - Search & filter
# - Thumbnails generation
# - Asset metadata (tags, description, custom fields)
# - Import external assets
# - Favorites system
# - Recently used tracking
# - Asset validation
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
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path

from src.utils.logger import get_logger
from src.utils.helpers import (
    ensure_dir, safe_join, sanitize_filename, generate_short_id,
    read_json, write_json, hash_file, format_bytes, get_file_size,
    get_timestamp, delete_file, list_files, get_file_extension,
    get_filename_without_ext, is_supported_model_format,
    is_supported_image_format, is_supported_audio_format,
    is_supported_video_format, copy_file
)
from src.utils.config_manager import get_config

logger = get_logger("AssetLibrary")


# ============================================================
# ASSET CATEGORIES
# ============================================================

class AssetCategory:
    """Asset categories constants"""
    MODEL = "model"
    TEXTURE = "texture"
    AUDIO_MUSIC = "audio_music"
    AUDIO_SFX = "audio_sfx"
    AUDIO_AMBIENT = "audio_ambient"
    VIDEO = "video"
    PRESET_CHARACTER = "preset_character"
    PRESET_SCENE = "preset_scene"
    PRESET_ANIMATION = "preset_animation"
    PRESET_MATERIAL = "preset_material"

    ALL = [
        MODEL, TEXTURE,
        AUDIO_MUSIC, AUDIO_SFX, AUDIO_AMBIENT,
        VIDEO,
        PRESET_CHARACTER, PRESET_SCENE,
        PRESET_ANIMATION, PRESET_MATERIAL
    ]

    # Category → folder mapping
    FOLDER_MAP = {
        MODEL: "models",
        TEXTURE: "textures",
        AUDIO_MUSIC: "audio/music",
        AUDIO_SFX: "audio/sfx",
        AUDIO_AMBIENT: "audio/ambient",
        VIDEO: "videos",
        PRESET_CHARACTER: "presets/characters",
        PRESET_SCENE: "presets/scenes",
        PRESET_ANIMATION: "presets/animations",
        PRESET_MATERIAL: "presets/materials",
    }

    # Category → validator function
    @staticmethod
    def get_validator(category: str) -> Callable[[str], bool]:
        validators = {
            AssetCategory.MODEL: is_supported_model_format,
            AssetCategory.TEXTURE: is_supported_image_format,
            AssetCategory.AUDIO_MUSIC: is_supported_audio_format,
            AssetCategory.AUDIO_SFX: is_supported_audio_format,
            AssetCategory.AUDIO_AMBIENT: is_supported_audio_format,
            AssetCategory.VIDEO: is_supported_video_format,
        }
        # Presets JSON files hain
        return validators.get(category, lambda f: True)


# ============================================================
# ASSET CLASS - Single Asset Data
# ============================================================

class Asset:
    """Single asset ka data"""

    def __init__(self, filepath: str, category: str,
                 asset_id: Optional[str] = None):
        self.id = asset_id or generate_short_id()
        self.filepath = filepath
        self.category = category
        self.filename = os.path.basename(filepath)
        self.name = get_filename_without_ext(filepath)
        self.extension = get_file_extension(filepath)

        # Metadata (default)
        self.description = ""
        self.tags: List[str] = []
        self.author = ""
        self.thumbnail_path: Optional[str] = None
        self.size = get_file_size(filepath) if os.path.exists(filepath) else 0
        self.added_at = get_timestamp()
        self.last_used = None
        self.use_count = 0
        self.is_favorite = False
        self.custom_data: Dict = {}

    def to_dict(self) -> Dict:
        """Asset ko dict me convert karo"""
        return {
            "id": self.id,
            "filepath": self.filepath,
            "category": self.category,
            "filename": self.filename,
            "name": self.name,
            "extension": self.extension,
            "description": self.description,
            "tags": self.tags,
            "author": self.author,
            "thumbnail_path": self.thumbnail_path,
            "size": self.size,
            "size_readable": format_bytes(self.size),
            "added_at": self.added_at,
            "last_used": self.last_used,
            "use_count": self.use_count,
            "is_favorite": self.is_favorite,
            "custom_data": self.custom_data,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Asset":
        """Dict se asset create karo"""
        asset = cls(
            filepath=data.get("filepath", ""),
            category=data.get("category", "unknown"),
            asset_id=data.get("id")
        )
        asset.filename = data.get("filename", asset.filename)
        asset.name = data.get("name", asset.name)
        asset.extension = data.get("extension", asset.extension)
        asset.description = data.get("description", "")
        asset.tags = data.get("tags", [])
        asset.author = data.get("author", "")
        asset.thumbnail_path = data.get("thumbnail_path")
        asset.size = data.get("size", 0)
        asset.added_at = data.get("added_at", get_timestamp())
        asset.last_used = data.get("last_used")
        asset.use_count = data.get("use_count", 0)
        asset.is_favorite = data.get("is_favorite", False)
        asset.custom_data = data.get("custom_data", {})
        return asset

    def exists(self) -> bool:
        """File actually exist karti hai?"""
        return os.path.exists(self.filepath)

    def touch(self):
        """Usage record karo"""
        self.last_used = get_timestamp()
        self.use_count += 1


# ============================================================
# ASSET LIBRARY - Main Class
# ============================================================

class AssetLibrary:
    """
    Central asset library.
    - Assets discover karta hai
    - Metadata manage karta hai
    - Search/filter karta hai
    - Import/export
    """

    LIBRARY_INDEX_FILE = "asset_index.json"

    def __init__(self, config: Optional[Dict] = None,
                 base_dir: Optional[str] = None):
        # Config
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # Base dir
        if base_dir is None:
            base_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
        self.base_dir = base_dir

        # Assets directory
        self.assets_dir = os.path.join(base_dir, "assets")
        ensure_dir(self.assets_dir)

        # Index file (metadata storage)
        self.index_file = os.path.join(self.assets_dir, self.LIBRARY_INDEX_FILE)

        # Thumbnails directory
        self.thumbnails_dir = os.path.join(self.assets_dir, ".thumbnails")
        ensure_dir(self.thumbnails_dir)

        # In-memory catalog
        self._assets: Dict[str, Asset] = {}  # id → Asset
        self._by_category: Dict[str, List[str]] = {}  # category → [ids]

        # Category folders banao
        self._create_category_folders()

        # Existing index load karo
        self.load_index()

        # Naye files discover karo
        self.scan_all_categories()

        logger.info(f"AssetLibrary initialized with {len(self._assets)} assets")

    # ------------------------------------------------------------
    # INITIALIZATION
    # ------------------------------------------------------------

    def _create_category_folders(self):
        """Har category ke liye folder banao"""
        for category, folder in AssetCategory.FOLDER_MAP.items():
            folder_path = os.path.join(self.assets_dir, folder)
            ensure_dir(folder_path)

    def _get_category_folder(self, category: str) -> Optional[str]:
        """Category ka folder path"""
        folder = AssetCategory.FOLDER_MAP.get(category)
        if folder:
            return os.path.join(self.assets_dir, folder)
        return None

    # ------------------------------------------------------------
    # INDEX (Metadata) LOAD/SAVE
    # ------------------------------------------------------------

    def load_index(self) -> bool:
        """Index file se assets load karo"""
        try:
            if not os.path.exists(self.index_file):
                logger.debug("No index file - starting fresh")
                return True

            data = read_json(self.index_file)
            if not data:
                return False

            assets_data = data.get("assets", [])
            for asset_data in assets_data:
                asset = Asset.from_dict(asset_data)

                # Sirf existing files load karo
                if asset.exists():
                    self._assets[asset.id] = asset
                    self._add_to_category_index(asset)

            logger.info(f"Loaded {len(self._assets)} assets from index")
            return True

        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return False

    def save_index(self) -> bool:
        """Index file me assets save karo"""
        try:
            data = {
                "version": "1.0.0",
                "updated_at": get_timestamp(),
                "total_assets": len(self._assets),
                "assets": [asset.to_dict() for asset in self._assets.values()]
            }
            success = write_json(self.index_file, data)
            if success:
                logger.debug(f"Index saved with {len(self._assets)} assets")
            return success

        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            return False

    def _add_to_category_index(self, asset: Asset):
        """Category index me add karo"""
        if asset.category not in self._by_category:
            self._by_category[asset.category] = []
        if asset.id not in self._by_category[asset.category]:
            self._by_category[asset.category].append(asset.id)

    def _remove_from_category_index(self, asset: Asset):
        """Category index se hatao"""
        if asset.category in self._by_category:
            if asset.id in self._by_category[asset.category]:
                self._by_category[asset.category].remove(asset.id)

    # ------------------------------------------------------------
    # SCANNING (Auto-Discovery)
    # ------------------------------------------------------------

    def scan_all_categories(self):
        """Saari categories scan karo naye files ke liye"""
        total_new = 0
        for category in AssetCategory.ALL:
            new_count = self.scan_category(category)
            total_new += new_count

        if total_new > 0:
            logger.info(f"Discovered {total_new} new assets")
            self.save_index()

    def scan_category(self, category: str) -> int:
        """
        Specific category ke folder me scan karo.
        Returns: naye assets ki count
        """
        folder = self._get_category_folder(category)
        if not folder or not os.path.exists(folder):
            return 0

        validator = AssetCategory.get_validator(category)
        new_count = 0

        # Existing filepaths (fast lookup ke liye set)
        existing_paths = {a.filepath for a in self._assets.values()}

        # Recursively scan
        for root, dirs, files in os.walk(folder):
            # Hidden folders skip karo
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            for filename in files:
                if filename.startswith("."):
                    continue

                filepath = os.path.join(root, filename)

                # Already index me hai?
                if filepath in existing_paths:
                    continue

                # Format validate karo
                if not validator(filepath):
                    continue

                # Add karo
                asset = Asset(filepath=filepath, category=category)
                self._assets[asset.id] = asset
                self._add_to_category_index(asset)
                new_count += 1

                logger.debug(f"Added: {asset.name} ({category})")

        return new_count

    def refresh(self):
        """Full refresh - purane invalid assets hatao aur naye discover karo"""
        # Purane (missing files) hatao
        removed = []
        for asset_id, asset in list(self._assets.items()):
            if not asset.exists():
                removed.append(asset_id)
                self._remove_from_category_index(asset)
                del self._assets[asset_id]

        if removed:
            logger.info(f"Removed {len(removed)} missing assets")

        # Naye discover karo
        self.scan_all_categories()

    # ------------------------------------------------------------
    # ASSET IMPORT (External files se)
    # ------------------------------------------------------------

    def import_asset(self, source_path: str, category: str,
                     new_name: Optional[str] = None,
                     tags: Optional[List[str]] = None,
                     description: str = "",
                     copy_file_flag: bool = True) -> Optional[Asset]:
        """
        External file ko library me import karo.

        Args:
            source_path: Source file path
            category: Asset category
            new_name: Naya naam (optional)
            tags: Tags list
            description: Description
            copy_file_flag: True to copy, False to reference

        Returns:
            Created Asset object
        """
        try:
            if not os.path.exists(source_path):
                logger.error(f"Source not found: {source_path}")
                return None

            # Validate format
            validator = AssetCategory.get_validator(category)
            if not validator(source_path):
                logger.error(f"Invalid format for {category}: {source_path}")
                return None

            # Destination determine karo
            if copy_file_flag:
                folder = self._get_category_folder(category)
                if not folder:
                    logger.error(f"No folder for category: {category}")
                    return None

                # Filename
                if new_name:
                    ext = get_file_extension(source_path)
                    filename = sanitize_filename(new_name) + "." + ext
                else:
                    filename = os.path.basename(source_path)
                    filename = sanitize_filename(filename)

                dest_path = os.path.join(folder, filename)

                # Duplicate check
                if os.path.exists(dest_path):
                    base = get_filename_without_ext(filename)
                    ext = get_file_extension(filename)
                    counter = 1
                    while os.path.exists(dest_path):
                        new_filename = f"{base}_{counter}.{ext}"
                        dest_path = os.path.join(folder, new_filename)
                        counter += 1

                # Copy file
                if not copy_file(source_path, dest_path, overwrite=False):
                    return None

                final_path = dest_path
            else:
                final_path = source_path

            # Asset create karo
            asset = Asset(filepath=final_path, category=category)
            if new_name:
                asset.name = new_name
            if tags:
                asset.tags = tags
            if description:
                asset.description = description

            # Add to library
            self._assets[asset.id] = asset
            self._add_to_category_index(asset)
            self.save_index()

            logger.info(f"Imported: {asset.name} ({category})")
            return asset

        except Exception as e:
            logger.error(f"Import failed: {e}")
            return None

    def import_batch(self, source_folder: str, category: str,
                     recursive: bool = True) -> int:
        """
        Folder se batch import.
        Returns: imported count
        """
        if not os.path.exists(source_folder):
            return 0

        validator = AssetCategory.get_validator(category)
        imported = 0

        if recursive:
            for root, _, files in os.walk(source_folder):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    if validator(filepath):
                        if self.import_asset(filepath, category):
                            imported += 1
        else:
            for filename in os.listdir(source_folder):
                filepath = os.path.join(source_folder, filename)
                if os.path.isfile(filepath) and validator(filepath):
                    if self.import_asset(filepath, category):
                        imported += 1

        logger.info(f"Batch imported {imported} assets")
        return imported

    # ------------------------------------------------------------
    # ASSET RETRIEVAL
    # ------------------------------------------------------------

    def get_asset(self, asset_id: str) -> Optional[Asset]:
        """ID se asset get karo"""
        return self._assets.get(asset_id)

    def get_by_category(self, category: str) -> List[Asset]:
        """Category ke saare assets"""
        ids = self._by_category.get(category, [])
        return [self._assets[aid] for aid in ids if aid in self._assets]

    def get_all_assets(self) -> List[Asset]:
        """Saare assets"""
        return list(self._assets.values())

    def get_favorites(self) -> List[Asset]:
        """Favorite assets"""
        return [a for a in self._assets.values() if a.is_favorite]

    def get_recently_used(self, limit: int = 10) -> List[Asset]:
        """Recently used assets"""
        used = [a for a in self._assets.values() if a.last_used]
        used.sort(key=lambda a: a.last_used or "", reverse=True)
        return used[:limit]

    def get_most_used(self, limit: int = 10) -> List[Asset]:
        """Most used assets"""
        all_assets = sorted(
            self._assets.values(),
            key=lambda a: a.use_count,
            reverse=True
        )
        return [a for a in all_assets if a.use_count > 0][:limit]

    # ------------------------------------------------------------
    # SEARCH & FILTER
    # ------------------------------------------------------------

    def search(self, query: str,
               category: Optional[str] = None,
               tags: Optional[List[str]] = None) -> List[Asset]:
        """
        Assets search karo.

        Args:
            query: Search text (name/description me match)
            category: Optional category filter
            tags: Optional tags (kisi bhi tag ka match)
        """
        query_lower = query.lower() if query else ""
        results = []

        for asset in self._assets.values():
            # Category filter
            if category and asset.category != category:
                continue

            # Tags filter
            if tags:
                if not any(tag.lower() in [t.lower() for t in asset.tags]
                          for tag in tags):
                    continue

            # Query match
            if query_lower:
                if (query_lower in asset.name.lower() or
                    query_lower in asset.description.lower() or
                    any(query_lower in tag.lower() for tag in asset.tags)):
                    results.append(asset)
            else:
                results.append(asset)

        return results

    def filter_by_extension(self, extensions: List[str]) -> List[Asset]:
        """Extension se filter karo"""
        exts_lower = [e.lower().lstrip(".") for e in extensions]
        return [a for a in self._assets.values()
                if a.extension.lower() in exts_lower]

    def filter_by_size(self, min_size: int = 0,
                       max_size: Optional[int] = None) -> List[Asset]:
        """Size range se filter karo"""
        results = []
        for asset in self._assets.values():
            if asset.size < min_size:
                continue
            if max_size is not None and asset.size > max_size:
                continue
            results.append(asset)
        return results

    # ------------------------------------------------------------
    # ASSET MANAGEMENT
    # ------------------------------------------------------------

    def update_metadata(self, asset_id: str, **updates) -> bool:
        """Asset metadata update karo"""
        asset = self.get_asset(asset_id)
        if not asset:
            return False

        allowed_fields = ["name", "description", "tags", "author",
                          "is_favorite", "custom_data"]

        for field, value in updates.items():
            if field in allowed_fields:
                setattr(asset, field, value)

        self.save_index()
        logger.debug(f"Updated metadata: {asset.name}")
        return True

    def add_tags(self, asset_id: str, tags: List[str]) -> bool:
        """Tags add karo"""
        asset = self.get_asset(asset_id)
        if not asset:
            return False

        for tag in tags:
            if tag not in asset.tags:
                asset.tags.append(tag)

        self.save_index()
        return True

    def remove_tags(self, asset_id: str, tags: List[str]) -> bool:
        """Tags remove karo"""
        asset = self.get_asset(asset_id)
        if not asset:
            return False

        asset.tags = [t for t in asset.tags if t not in tags]
        self.save_index()
        return True

    def toggle_favorite(self, asset_id: str) -> bool:
        """Favorite toggle karo"""
        asset = self.get_asset(asset_id)
        if not asset:
            return False

        asset.is_favorite = not asset.is_favorite
        self.save_index()
        return asset.is_favorite

    def mark_used(self, asset_id: str):
        """Asset use record karo"""
        asset = self.get_asset(asset_id)
        if asset:
            asset.touch()
            self.save_index()

    def delete_asset(self, asset_id: str,
                     delete_file_flag: bool = False) -> bool:
        """
        Asset library se hatao.

        Args:
            delete_file_flag: True to physical file bhi delete karo
        """
        asset = self.get_asset(asset_id)
        if not asset:
            return False

        try:
            # File delete karo (agar chahiye)
            if delete_file_flag and asset.exists():
                delete_file(asset.filepath)
                logger.info(f"Deleted file: {asset.filepath}")

            # Thumbnail delete karo
            if asset.thumbnail_path and os.path.exists(asset.thumbnail_path):
                delete_file(asset.thumbnail_path)

            # Library se hatao
            self._remove_from_category_index(asset)
            del self._assets[asset_id]

            self.save_index()
            logger.info(f"Removed from library: {asset.name}")
            return True

        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False

    # ------------------------------------------------------------
    # ALL TAGS (Unique tags across library)
    # ------------------------------------------------------------

    def get_all_tags(self) -> List[str]:
        """Library me use ho rahe saare unique tags"""
        tags_set = set()
        for asset in self._assets.values():
            tags_set.update(asset.tags)
        return sorted(list(tags_set))

    def get_tag_counts(self) -> Dict[str, int]:
        """Har tag ki count"""
        counts = {}
        for asset in self._assets.values():
            for tag in asset.tags:
                counts[tag] = counts.get(tag, 0) + 1
        return counts

    # ------------------------------------------------------------
    # STATISTICS
    # ------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Library statistics"""
        stats = {
            "total_assets": len(self._assets),
            "total_size": 0,
            "by_category": {},
            "favorites_count": 0,
            "used_count": 0,
        }

        for asset in self._assets.values():
            stats["total_size"] += asset.size

            cat = asset.category
            if cat not in stats["by_category"]:
                stats["by_category"][cat] = {"count": 0, "size": 0}
            stats["by_category"][cat]["count"] += 1
            stats["by_category"][cat]["size"] += asset.size

            if asset.is_favorite:
                stats["favorites_count"] += 1
            if asset.use_count > 0:
                stats["used_count"] += 1

        stats["total_size_readable"] = format_bytes(stats["total_size"])

        for cat_data in stats["by_category"].values():
            cat_data["size_readable"] = format_bytes(cat_data["size"])

        return stats


# ============================================================
# TEST FUNCTION
# ============================================================

if __name__ == "__main__":
    from src.utils.logger import setup_logging, print_banner, print_section

    setup_logging(log_level="DEBUG")
    print_banner("Asset Library Test", "Testing asset management")

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))

    # ============================================================
    # Test 1: Initialize
    # ============================================================
    print_section("Test 1: Initialize Library")

    library = AssetLibrary(base_dir=base_dir)
    print(f"Library initialized")
    print(f"Assets directory: {library.assets_dir}")
    print(f"Initial assets: {len(library.get_all_assets())}")

    # ============================================================
    # Test 2: Create Dummy Assets (for testing)
    # ============================================================
    print_section("Test 2: Create Test Assets")

    # Ek test model file banao (fake OBJ)
    test_model_content = "# Fake OBJ file for testing\nv 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n"
    test_model_path = os.path.join(library.assets_dir, "models", "test_cube.obj")
    ensure_dir(os.path.dirname(test_model_path))
    with open(test_model_path, "w") as f:
        f.write(test_model_content)
    print(f"Created test model: test_cube.obj")

    # Test preset (JSON file)
    test_preset_path = os.path.join(
        library.assets_dir, "presets", "characters", "test_hero.json"
    )
    ensure_dir(os.path.dirname(test_preset_path))
    write_json(test_preset_path, {
        "name": "Test Hero",
        "height": 1.75,
        "clothing": "casual"
    })
    print(f"Created test preset: test_hero.json")

    # ============================================================
    # Test 3: Scan & Discover
    # ============================================================
    print_section("Test 3: Scan for Assets")

    library.refresh()
    all_assets = library.get_all_assets()
    print(f"Total assets after scan: {len(all_assets)}")

    for asset in all_assets:
        print(f"  - {asset.name} ({asset.category}) {asset.extension}")

    # ============================================================
    # Test 4: Get by Category
    # ============================================================
    print_section("Test 4: Category Filtering")

    models = library.get_by_category(AssetCategory.MODEL)
    print(f"Models: {len(models)}")

    presets = library.get_by_category(AssetCategory.PRESET_CHARACTER)
    print(f"Character presets: {len(presets)}")

    # ============================================================
    # Test 5: Metadata Update
    # ============================================================
    print_section("Test 5: Update Metadata")

    if all_assets:
        first = all_assets[0]
        library.update_metadata(
            first.id,
            description="Test cube for demo",
            tags=["test", "geometry", "demo"],
            author="Test User"
        )

        updated = library.get_asset(first.id)
        print(f"Name: {updated.name}")
        print(f"Description: {updated.description}")
        print(f"Tags: {updated.tags}")
        print(f"Author: {updated.author}")

    # ============================================================
    # Test 6: Favorites
    # ============================================================
    print_section("Test 6: Favorites")

    if all_assets:
        library.toggle_favorite(all_assets[0].id)
        favorites = library.get_favorites()
        print(f"Favorites count: {len(favorites)}")
        for f in favorites:
            print(f"  ⭐ {f.name}")

    # ============================================================
    # Test 7: Usage Tracking
    # ============================================================
    print_section("Test 7: Usage Tracking")

    if all_assets:
        library.mark_used(all_assets[0].id)
        library.mark_used(all_assets[0].id)
        library.mark_used(all_assets[0].id)

        used = library.get_asset(all_assets[0].id)
        print(f"Use count: {used.use_count}")
        print(f"Last used: {used.last_used}")

        recent = library.get_recently_used(limit=5)
        print(f"Recently used: {len(recent)}")

    # ============================================================
    # Test 8: Search
    # ============================================================
    print_section("Test 8: Search")

    results = library.search("cube")
    print(f"Search 'cube': {len(results)} results")

    results = library.search("", tags=["test"])
    print(f"Tag 'test': {len(results)} results")

    all_tags = library.get_all_tags()
    print(f"All tags: {all_tags}")

    # ============================================================
    # Test 9: Statistics
    # ============================================================
    print_section("Test 9: Library Statistics")

    stats = library.get_stats()
    print(f"Total assets: {stats['total_assets']}")
    print(f"Total size: {stats['total_size_readable']}")
    print(f"Favorites: {stats['favorites_count']}")
    print(f"Used: {stats['used_count']}")
    print("By category:")
    for cat, data in stats['by_category'].items():
        print(f"  - {cat}: {data['count']} ({data['size_readable']})")

    # ============================================================
    # Cleanup
    # ============================================================
    print_section("Cleanup")

    # Test files delete karo
    for asset in library.get_all_assets():
        if "test_" in asset.name:
            library.delete_asset(asset.id, delete_file_flag=True)
            print(f"Deleted: {asset.name}")

    # Index file bhi hatao (test ka)
    delete_file(library.index_file)
    print("Test index cleared")

    print_banner("✅ All Tests Passed", "Asset Library Working")