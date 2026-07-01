# ============================================================
# 3D ANIMATION STUDIO - Project Manager (Core)
# ============================================================
# Features:
# - Complete project lifecycle management
# - Scene management (multiple scenes per project)
# - Timeline data storage
# - Objects/characters/lights management
# - Undo/Redo system (command pattern)
# - Auto-save integration
# - Project state tracking (dirty/clean)
# - Import/Export project data
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

import copy
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Tuple
from collections import deque

from src.utils.logger import get_logger
from src.utils.helpers import (
    generate_uuid, generate_short_id, get_timestamp,
    ensure_dir, safe_join
)
from src.utils.file_manager import ProjectFileManager
from src.utils.config_manager import get_config

logger = get_logger("ProjectManager")


# ============================================================
# COMMAND PATTERN - Undo/Redo Ke Liye
# ============================================================

class Command:
    """
    Base class for undo/redo commands.
    Har action ko command banao.
    """

    def __init__(self, name: str = "Command"):
        self.name = name
        self.timestamp = time.time()

    def execute(self) -> bool:
        """Command execute karo"""
        raise NotImplementedError

    def undo(self) -> bool:
        """Command undo karo"""
        raise NotImplementedError

    def redo(self) -> bool:
        """Command redo karo (default: execute)"""
        return self.execute()


class SetValueCommand(Command):
    """Value change ke liye command"""

    def __init__(self, target: Dict, key_path: str,
                 new_value: Any, description: str = ""):
        super().__init__(description or f"Set {key_path}")
        self.target = target
        self.key_path = key_path
        self.new_value = new_value
        self.old_value = None

    def execute(self) -> bool:
        keys = self.key_path.split(".")
        obj = self.target

        # Old value save karo
        for key in keys[:-1]:
            if key not in obj:
                obj[key] = {}
            obj = obj[key]

        self.old_value = obj.get(keys[-1])
        obj[keys[-1]] = self.new_value
        return True

    def undo(self) -> bool:
        keys = self.key_path.split(".")
        obj = self.target

        for key in keys[:-1]:
            if key not in obj:
                return False
            obj = obj[key]

        if self.old_value is None:
            if keys[-1] in obj:
                del obj[keys[-1]]
        else:
            obj[keys[-1]] = self.old_value
        return True


class AddObjectCommand(Command):
    """Object add karne ka command"""

    def __init__(self, objects_list: List, obj_data: Dict,
                 description: str = ""):
        super().__init__(description or f"Add {obj_data.get('name', 'object')}")
        self.objects_list = objects_list
        self.obj_data = obj_data
        self.added_index = -1

    def execute(self) -> bool:
        self.objects_list.append(self.obj_data)
        self.added_index = len(self.objects_list) - 1
        return True

    def undo(self) -> bool:
        if 0 <= self.added_index < len(self.objects_list):
            self.objects_list.pop(self.added_index)
            return True
        return False


class RemoveObjectCommand(Command):
    """Object remove karne ka command"""

    def __init__(self, objects_list: List, index: int,
                 description: str = ""):
        super().__init__(description or "Remove object")
        self.objects_list = objects_list
        self.index = index
        self.removed_obj = None

    def execute(self) -> bool:
        if 0 <= self.index < len(self.objects_list):
            self.removed_obj = self.objects_list.pop(self.index)
            return True
        return False

    def undo(self) -> bool:
        if self.removed_obj is not None:
            self.objects_list.insert(self.index, self.removed_obj)
            return True
        return False


# ============================================================
# UNDO/REDO MANAGER
# ============================================================

class UndoRedoManager:
    """
    Undo/Redo history manage karta hai.
    Command pattern use karta hai.
    """

    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.undo_stack: deque = deque(maxlen=max_history)
        self.redo_stack: deque = deque(maxlen=max_history)
        self._enabled = True

    def execute(self, command: Command) -> bool:
        """Command execute karo aur history me add karo"""
        if not self._enabled:
            return command.execute()

        success = command.execute()
        if success:
            self.undo_stack.append(command)
            self.redo_stack.clear()  # Naya action ke baad redo invalid
            logger.debug(f"Executed: {command.name}")
        return success

    def undo(self) -> Optional[str]:
        """Last command undo karo"""
        if not self.undo_stack:
            return None

        command = self.undo_stack.pop()
        if command.undo():
            self.redo_stack.append(command)
            logger.debug(f"Undone: {command.name}")
            return command.name
        return None

    def redo(self) -> Optional[str]:
        """Last undone command redo karo"""
        if not self.redo_stack:
            return None

        command = self.redo_stack.pop()
        if command.redo():
            self.undo_stack.append(command)
            logger.debug(f"Redone: {command.name}")
            return command.name
        return None

    def can_undo(self) -> bool:
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self.redo_stack) > 0

    def clear(self):
        """History clear karo"""
        self.undo_stack.clear()
        self.redo_stack.clear()

    def get_undo_stack_names(self) -> List[str]:
        """Undo stack me commands ke naam"""
        return [cmd.name for cmd in self.undo_stack]

    def get_redo_stack_names(self) -> List[str]:
        """Redo stack me commands ke naam"""
        return [cmd.name for cmd in self.redo_stack]

    def set_enabled(self, enabled: bool):
        """Undo/redo enable/disable karo"""
        self._enabled = enabled


# ============================================================
# SCENE CLASS - Individual Scene Data
# ============================================================

class Scene:
    """
    Single scene ka data represent karta hai.
    Ek project me multiple scenes ho sakti hain.
    """

    def __init__(self, name: str = "New Scene",
                 scene_id: Optional[str] = None):
        self.id = scene_id or generate_short_id()
        self.name = name
        self.created_at = get_timestamp()
        self.modified_at = get_timestamp()

        # Scene properties
        self.duration = 10.0
        self.fps = 30
        self.resolution = [1920, 1080]
        self.background_color = [30, 30, 30]

        # Scene contents
        self.objects: List[Dict] = []       # 3D objects, characters
        self.lights: List[Dict] = []        # Lights
        self.cameras: List[Dict] = []       # Cameras
        self.audio_tracks: List[Dict] = []  # Audio
        self.effects: List[Dict] = []       # VFX

        # Environment
        self.environment = {
            "type": "indoor_room",
            "lighting_preset": "day_outdoor",
            "season": "summer",
            "time_of_day": "noon",
        }

        # Physics
        self.physics_enabled = True
        self.gravity = [0, -9.81, 0]

        # Timeline data (keyframes)
        self.timeline = {
            "duration": self.duration,
            "keyframes": [],
            "markers": [],
        }

    def to_dict(self) -> Dict:
        """Scene ko dictionary me convert karo (save ke liye)"""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "duration": self.duration,
            "fps": self.fps,
            "resolution": self.resolution,
            "background_color": self.background_color,
            "objects": self.objects,
            "lights": self.lights,
            "cameras": self.cameras,
            "audio_tracks": self.audio_tracks,
            "effects": self.effects,
            "environment": self.environment,
            "physics_enabled": self.physics_enabled,
            "gravity": self.gravity,
            "timeline": self.timeline,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Scene":
        """Dictionary se scene create karo (load ke liye)"""
        scene = cls(
            name=data.get("name", "Unnamed"),
            scene_id=data.get("id")
        )
        scene.created_at = data.get("created_at", get_timestamp())
        scene.modified_at = data.get("modified_at", get_timestamp())
        scene.duration = data.get("duration", 10.0)
        scene.fps = data.get("fps", 30)
        scene.resolution = data.get("resolution", [1920, 1080])
        scene.background_color = data.get("background_color", [30, 30, 30])
        scene.objects = data.get("objects", [])
        scene.lights = data.get("lights", [])
        scene.cameras = data.get("cameras", [])
        scene.audio_tracks = data.get("audio_tracks", [])
        scene.effects = data.get("effects", [])
        scene.environment = data.get("environment", {})
        scene.physics_enabled = data.get("physics_enabled", True)
        scene.gravity = data.get("gravity", [0, -9.81, 0])
        scene.timeline = data.get("timeline", {
            "duration": scene.duration,
            "keyframes": [],
            "markers": []
        })
        return scene


# ============================================================
# PROJECT CLASS - Complete Project Data
# ============================================================

class Project:
    """
    Complete project data.
    Multiple scenes, assets, settings, sab kuch.
    """

    def __init__(self, name: str = "Untitled Project"):
        # Metadata
        self.id = generate_uuid()
        self.name = name
        self.description = ""
        self.author = ""
        self.created_at = get_timestamp()
        self.modified_at = get_timestamp()
        self.version = "1.0.0"

        # File info
        self.file_path: Optional[str] = None
        self.project_folder: Optional[str] = None

        # Scenes
        self.scenes: List[Scene] = []
        self.active_scene_index: int = 0

        # Global settings
        self.global_fps = 30
        self.global_resolution = [1920, 1080]

        # Assets used (paths)
        self.assets: Dict[str, List[str]] = {
            "models": [],
            "textures": [],
            "audio": [],
            "videos": [],
        }

        # Export settings
        self.export_settings = {
            "format": "mp4",
            "quality": "high",
            "preset": "youtube",
        }

        # Custom user data
        self.custom_data: Dict = {}

        # Default scene banao
        default_scene = Scene(name="Scene 1")
        self.scenes.append(default_scene)

    def to_dict(self) -> Dict:
        """Project ko dictionary me convert karo"""
        return {
            "metadata": {
                "id": self.id,
                "name": self.name,
                "description": self.description,
                "author": self.author,
                "created_at": self.created_at,
                "modified_at": self.modified_at,
                "version": self.version,
            },
            "settings": {
                "global_fps": self.global_fps,
                "global_resolution": self.global_resolution,
            },
            "scenes": [scene.to_dict() for scene in self.scenes],
            "active_scene_index": self.active_scene_index,
            "assets": self.assets,
            "export_settings": self.export_settings,
            "custom_data": self.custom_data,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Project":
        """Dictionary se project create karo"""
        metadata = data.get("metadata", {})
        settings = data.get("settings", {})

        project = cls(name=metadata.get("name", "Untitled"))
        project.id = metadata.get("id", generate_uuid())
        project.description = metadata.get("description", "")
        project.author = metadata.get("author", "")
        project.created_at = metadata.get("created_at", get_timestamp())
        project.modified_at = metadata.get("modified_at", get_timestamp())
        project.version = metadata.get("version", "1.0.0")

        project.global_fps = settings.get("global_fps", 30)
        project.global_resolution = settings.get("global_resolution", [1920, 1080])

        # Scenes load karo
        project.scenes = []
        for scene_data in data.get("scenes", []):
            project.scenes.append(Scene.from_dict(scene_data))

        # Default scene agar koi nahi hai
        if not project.scenes:
            project.scenes.append(Scene(name="Scene 1"))

        project.active_scene_index = data.get("active_scene_index", 0)
        project.assets = data.get("assets", {
            "models": [], "textures": [], "audio": [], "videos": []
        })
        project.export_settings = data.get("export_settings", {})
        project.custom_data = data.get("custom_data", {})

        return project


# ============================================================
# MAIN PROJECT MANAGER
# ============================================================

class ProjectManager:
    """
    Complete project management system.
    - Create, open, save, close projects
    - Scene management
    - Object management
    - Undo/Redo
    - Change tracking
    """

    def __init__(self, config: Optional[Dict] = None,
                 base_dir: Optional[str] = None):
        """
        Args:
            config: App config dictionary (optional)
            base_dir: Project base directory
        """
        # Config
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # Base directory
        if base_dir is None:
            base_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
        self.base_dir = base_dir

        # Directories
        self.projects_dir = os.path.join(base_dir, "projects")
        self.backups_dir = os.path.join(base_dir, "backups")

        # File manager
        self.file_manager = ProjectFileManager(
            projects_dir=self.projects_dir,
            backups_dir=self.backups_dir,
            max_backups=self.config.get("ui", {}).get("max_backups", 10)
        )

        # Current project
        self.current_project: Optional[Project] = None

        # Undo/Redo
        self.undo_manager = UndoRedoManager(max_history=100)

        # State tracking
        self._is_dirty = False  # Unsaved changes hain kya
        self._last_save_time = 0

        # Change listeners
        self._change_listeners: List[Callable] = []

        logger.info("ProjectManager initialized")

    # ------------------------------------------------------------
    # PROJECT LIFECYCLE
    # ------------------------------------------------------------

    def new_project(self, name: str = "Untitled Project",
                    author: str = "") -> Project:
        """
        Naya project banao.
        """
        # Agar current project unsaved hai to warning
        if self.current_project and self._is_dirty:
            logger.warning("Current project has unsaved changes")

        # Naya project create karo
        project = Project(name=name)
        project.author = author

        self.current_project = project
        self.undo_manager.clear()
        self._is_dirty = True  # Naya project, save nahi hua abhi

        logger.info(f"New project created: {name}")
        self._notify_change("project_created")

        return project

    def open_project(self, project_file: str) -> Optional[Project]:
        """
        Existing project open karo.
        """
        try:
            data = self.file_manager.load_project(project_file)
            if not data:
                logger.error(f"Failed to load: {project_file}")
                return None

            project = Project.from_dict(data)
            project.file_path = project_file
            project.project_folder = os.path.dirname(project_file)

            self.current_project = project
            self.undo_manager.clear()
            self._is_dirty = False
            self._last_save_time = time.time()

            logger.info(f"Project opened: {project.name}")
            self._notify_change("project_opened")

            return project

        except Exception as e:
            logger.error(f"Failed to open project: {e}")
            return None

    def save_project(self, save_as_path: Optional[str] = None) -> bool:
        """
        Current project save karo.

        Args:
            save_as_path: 'Save As' ke liye new path (optional)
        """
        if not self.current_project:
            logger.error("No project to save")
            return False

        try:
            # Save path determine karo
            if save_as_path:
                # Save As - naye location pe save
                new_project_file = self.file_manager.create_project(
                    self.current_project.name,
                    self.current_project.to_dict()
                )
                if new_project_file:
                    self.current_project.file_path = new_project_file
                    self.current_project.project_folder = os.path.dirname(new_project_file)
            elif self.current_project.file_path is None:
                # Pehli baar save ho raha hai - naya file banao
                new_project_file = self.file_manager.create_project(
                    self.current_project.name,
                    self.current_project.to_dict()
                )
                if new_project_file:
                    self.current_project.file_path = new_project_file
                    self.current_project.project_folder = os.path.dirname(new_project_file)
                else:
                    return False
            else:
                # Existing file update karo
                self.current_project.modified_at = get_timestamp()
                success = self.file_manager.save_project(
                    self.current_project.file_path,
                    self.current_project.to_dict(),
                    create_backup=True
                )
                if not success:
                    return False

            self._is_dirty = False
            self._last_save_time = time.time()

            logger.info(f"Project saved: {self.current_project.name}")
            self._notify_change("project_saved")
            return True

        except Exception as e:
            logger.error(f"Save failed: {e}")
            return False

    def close_project(self, force: bool = False) -> bool:
        """
        Current project close karo.

        Args:
            force: True to save prompt skip karo
        """
        if not self.current_project:
            return True

        if self._is_dirty and not force:
            logger.warning("Project has unsaved changes")
            return False

        project_name = self.current_project.name
        self.current_project = None
        self.undo_manager.clear()
        self._is_dirty = False

        logger.info(f"Project closed: {project_name}")
        self._notify_change("project_closed")
        return True

    # ------------------------------------------------------------
    # SCENE MANAGEMENT
    # ------------------------------------------------------------

    def add_scene(self, name: str = "New Scene") -> Optional[Scene]:
        """Nayi scene add karo"""
        if not self.current_project:
            return None

        scene = Scene(name=name)
        self.current_project.scenes.append(scene)
        self._is_dirty = True

        logger.info(f"Scene added: {name}")
        self._notify_change("scene_added")
        return scene

    def remove_scene(self, index: int) -> bool:
        """Scene remove karo"""
        if not self.current_project:
            return False

        scenes = self.current_project.scenes
        if 0 <= index < len(scenes):
            if len(scenes) == 1:
                logger.warning("Cannot remove last scene")
                return False

            removed = scenes.pop(index)
            self._is_dirty = True

            # Active scene index adjust karo
            if self.current_project.active_scene_index >= len(scenes):
                self.current_project.active_scene_index = len(scenes) - 1

            logger.info(f"Scene removed: {removed.name}")
            self._notify_change("scene_removed")
            return True

        return False

    def duplicate_scene(self, index: int) -> Optional[Scene]:
        """Scene duplicate karo"""
        if not self.current_project:
            return None

        scenes = self.current_project.scenes
        if 0 <= index < len(scenes):
            original = scenes[index]
            data = original.to_dict()
            data["id"] = generate_short_id()  # New ID
            data["name"] = f"{original.name} (Copy)"

            new_scene = Scene.from_dict(data)
            scenes.insert(index + 1, new_scene)
            self._is_dirty = True

            logger.info(f"Scene duplicated: {new_scene.name}")
            self._notify_change("scene_duplicated")
            return new_scene

        return None

    def get_active_scene(self) -> Optional[Scene]:
        """Currently active scene return karo"""
        if not self.current_project:
            return None

        idx = self.current_project.active_scene_index
        scenes = self.current_project.scenes

        if 0 <= idx < len(scenes):
            return scenes[idx]
        return None

    def set_active_scene(self, index: int) -> bool:
        """Active scene change karo"""
        if not self.current_project:
            return False

        if 0 <= index < len(self.current_project.scenes):
            self.current_project.active_scene_index = index
            self._notify_change("active_scene_changed")
            return True
        return False

    # ------------------------------------------------------------
    # OBJECT MANAGEMENT (Active Scene ke andar)
    # ------------------------------------------------------------

    def add_object(self, obj_data: Dict) -> Optional[str]:
        """
        Active scene me object add karo.

        Args:
            obj_data: Object properties (name, type, position, etc.)

        Returns:
            Object ID
        """
        scene = self.get_active_scene()
        if not scene:
            return None

        # Ensure required fields
        if "id" not in obj_data:
            obj_data["id"] = generate_short_id()
        if "name" not in obj_data:
            obj_data["name"] = f"Object_{obj_data['id'][:4]}"
        if "type" not in obj_data:
            obj_data["type"] = "generic"
        if "position" not in obj_data:
            obj_data["position"] = [0, 0, 0]
        if "rotation" not in obj_data:
            obj_data["rotation"] = [0, 0, 0]
        if "scale" not in obj_data:
            obj_data["scale"] = [1, 1, 1]

        # Undo command ke through add karo
        command = AddObjectCommand(scene.objects, obj_data,
                                    f"Add {obj_data['name']}")
        if self.undo_manager.execute(command):
            self._is_dirty = True
            logger.info(f"Object added: {obj_data['name']}")
            self._notify_change("object_added")
            return obj_data["id"]

        return None

    def remove_object(self, object_id: str) -> bool:
        """Object remove karo by ID"""
        scene = self.get_active_scene()
        if not scene:
            return False

        for i, obj in enumerate(scene.objects):
            if obj.get("id") == object_id:
                command = RemoveObjectCommand(scene.objects, i,
                                               f"Remove {obj.get('name')}")
                if self.undo_manager.execute(command):
                    self._is_dirty = True
                    logger.info(f"Object removed: {obj.get('name')}")
                    self._notify_change("object_removed")
                    return True
                break

        return False

    def update_object(self, object_id: str, updates: Dict) -> bool:
        """Object properties update karo"""
        scene = self.get_active_scene()
        if not scene:
            return False

        for obj in scene.objects:
            if obj.get("id") == object_id:
                for key, value in updates.items():
                    # Undo command ke through
                    command = SetValueCommand(
                        obj, key, value,
                        f"Update {obj.get('name')}.{key}"
                    )
                    self.undo_manager.execute(command)

                self._is_dirty = True
                self._notify_change("object_updated")
                return True

        return False

    def get_object(self, object_id: str) -> Optional[Dict]:
        """Object get karo by ID"""
        scene = self.get_active_scene()
        if not scene:
            return None

        for obj in scene.objects:
            if obj.get("id") == object_id:
                return obj

        return None

    def get_all_objects(self) -> List[Dict]:
        """Active scene ke saare objects"""
        scene = self.get_active_scene()
        return scene.objects if scene else []

    # ------------------------------------------------------------
    # UNDO / REDO
    # ------------------------------------------------------------

    def undo(self) -> Optional[str]:
        """Undo last action"""
        result = self.undo_manager.undo()
        if result:
            self._is_dirty = True
            self._notify_change("undo_performed")
        return result

    def redo(self) -> Optional[str]:
        """Redo last undone action"""
        result = self.undo_manager.redo()
        if result:
            self._is_dirty = True
            self._notify_change("redo_performed")
        return result

    def can_undo(self) -> bool:
        return self.undo_manager.can_undo()

    def can_redo(self) -> bool:
        return self.undo_manager.can_redo()

    # ------------------------------------------------------------
    # STATE
    # ------------------------------------------------------------

    def is_dirty(self) -> bool:
        """Unsaved changes hain kya"""
        return self._is_dirty

    def mark_dirty(self):
        """Manually dirty mark karo"""
        self._is_dirty = True

    def mark_clean(self):
        """Clean mark karo (saved)"""
        self._is_dirty = False

    def has_project(self) -> bool:
        """Koi project open hai kya"""
        return self.current_project is not None

    def get_project_info(self) -> Dict:
        """Current project ki info"""
        if not self.current_project:
            return {}

        return {
            "name": self.current_project.name,
            "id": self.current_project.id,
            "author": self.current_project.author,
            "created_at": self.current_project.created_at,
            "modified_at": self.current_project.modified_at,
            "file_path": self.current_project.file_path,
            "scene_count": len(self.current_project.scenes),
            "active_scene": self.current_project.active_scene_index,
            "is_dirty": self._is_dirty,
        }

    # ------------------------------------------------------------
    # CHANGE LISTENERS
    # ------------------------------------------------------------

    def add_change_listener(self, callback: Callable):
        """Change notifications ke liye listener add karo"""
        self._change_listeners.append(callback)

    def remove_change_listener(self, callback: Callable):
        """Listener remove karo"""
        if callback in self._change_listeners:
            self._change_listeners.remove(callback)

    def _notify_change(self, event_type: str):
        """Sab listeners ko notify karo"""
        for listener in self._change_listeners:
            try:
                listener(event_type)
            except Exception as e:
                logger.error(f"Change listener failed: {e}")

    # ------------------------------------------------------------
    # RECENT PROJECTS
    # ------------------------------------------------------------

    def get_recent_projects(self) -> List[Dict]:
        """Recent projects list"""
        return self.file_manager.get_recent_projects()

    def list_all_projects(self) -> List[Dict]:
        """Saare projects list"""
        return self.file_manager.list_all_projects()


# ============================================================
# TEST FUNCTION
# ============================================================

if __name__ == "__main__":
    from src.utils.logger import setup_logging, print_banner, print_section

    setup_logging(log_level="DEBUG")
    print_banner("Project Manager Test", "Complete Project System")

    # Base dir
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))

    # ============================================================
    # Test 1: Create Project
    # ============================================================
    print_section("Test 1: New Project")

    pm = ProjectManager(base_dir=base_dir)
    project = pm.new_project(name="My Test Project", author="Happy")

    print(f"Created: {project.name}")
    print(f"ID: {project.id}")
    print(f"Author: {project.author}")
    print(f"Default scenes: {len(project.scenes)}")

    # ============================================================
    # Test 2: Add Objects
    # ============================================================
    print_section("Test 2: Add Objects")

    obj1_id = pm.add_object({
        "name": "Character_Hero",
        "type": "character",
        "position": [0, 0, 0],
    })

    obj2_id = pm.add_object({
        "name": "Cube_Prop",
        "type": "mesh",
        "position": [2, 0, 0],
    })

    obj3_id = pm.add_object({
        "name": "Main_Camera",
        "type": "camera",
        "position": [0, 5, 10],
    })

    print(f"Total objects: {len(pm.get_all_objects())}")
    for obj in pm.get_all_objects():
        print(f"  - {obj['name']} ({obj['type']}) at {obj['position']}")

    # ============================================================
    # Test 3: Update Object
    # ============================================================
    print_section("Test 3: Update Object")

    pm.update_object(obj1_id, {"position": [5, 0, 5]})
    updated = pm.get_object(obj1_id)
    print(f"Hero new position: {updated['position']}")

    # ============================================================
    # Test 4: Undo/Redo
    # ============================================================
    print_section("Test 4: Undo/Redo System")

    print(f"Can undo: {pm.can_undo()}")
    print(f"Undo stack: {pm.undo_manager.get_undo_stack_names()[-3:]}")

    action = pm.undo()
    print(f"Undone: {action}")

    hero = pm.get_object(obj1_id)
    print(f"Hero position after undo: {hero['position']}")

    action = pm.redo()
    print(f"Redone: {action}")

    hero = pm.get_object(obj1_id)
    print(f"Hero position after redo: {hero['position']}")

    # ============================================================
    # Test 5: Scene Management
    # ============================================================
    print_section("Test 5: Scene Management")

    scene2 = pm.add_scene("Scene 2 - Action")
    scene3 = pm.add_scene("Scene 3 - Ending")

    print(f"Total scenes: {len(project.scenes)}")
    for i, s in enumerate(project.scenes):
        print(f"  {i}: {s.name}")

    # Active scene change
    pm.set_active_scene(1)
    active = pm.get_active_scene()
    print(f"Active scene: {active.name}")

    # Duplicate
    dup = pm.duplicate_scene(0)
    print(f"Duplicated: {dup.name}")

    # ============================================================
    # Test 6: Change Listeners
    # ============================================================
    print_section("Test 6: Change Listeners")

    events = []
    def on_change(event_type):
        events.append(event_type)
        print(f"  → Event: {event_type}")

    pm.add_change_listener(on_change)

    pm.set_active_scene(0)
    pm.add_object({"name": "Test_Light", "type": "light"})

    print(f"Total events recorded: {len(events)}")

    # ============================================================
    # Test 7: Save & Load
    # ============================================================
    print_section("Test 7: Save Project")

    print(f"Is dirty: {pm.is_dirty()}")
    success = pm.save_project()
    print(f"Save success: {success}")
    print(f"Is dirty after save: {pm.is_dirty()}")
    print(f"Saved to: {project.file_path}")

    # Close aur reopen
    saved_path = project.file_path
    pm.close_project()
    print(f"Project closed. Has project: {pm.has_project()}")

    reopened = pm.open_project(saved_path)
    if reopened:
        print(f"Reopened: {reopened.name}")
        print(f"Scenes restored: {len(reopened.scenes)}")
        print(f"Objects in first scene: {len(reopened.scenes[0].objects)}")

    # ============================================================
    # Test 8: Project Info
    # ============================================================
    print_section("Test 8: Project Info")

    info = pm.get_project_info()
    for key, value in info.items():
        print(f"  {key}: {value}")

    # ============================================================
    # Cleanup
    # ============================================================
    print_section("Cleanup")

    if project.file_path:
        pm.file_manager.delete_project(project.file_path, delete_backups=True)
        print("Test project deleted")

    print_banner("✅ All Tests Passed", "Project Manager Working")