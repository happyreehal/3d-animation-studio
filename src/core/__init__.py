# ============================================================
# 3D ANIMATION STUDIO - Core Package
# ============================================================
# Core business logic modules.
#
# Usage:
#     from src.core import ProjectManager, AssetLibrary
#     from src.core import AutoSaveSystem, Scene, Project
# ============================================================

# Project Manager exports
from src.core.project_manager import (
    ProjectManager,
    Project,
    Scene,
    UndoRedoManager,
    Command,
    SetValueCommand,
    AddObjectCommand,
    RemoveObjectCommand,
)

# Asset Library exports
from src.core.asset_library import (
    AssetLibrary,
    Asset,
    AssetCategory,
)

# Auto-Save exports
from src.core.auto_save import (
    AutoSaveSystem,
    SaveState,
    SaveEvent,
    SessionRecovery,
)


__version__ = "1.0.0"
__all__ = [
    # Project
    "ProjectManager", "Project", "Scene",
    "UndoRedoManager", "Command",
    "SetValueCommand", "AddObjectCommand", "RemoveObjectCommand",

    # Assets
    "AssetLibrary", "Asset", "AssetCategory",

    # Auto-save
    "AutoSaveSystem", "SaveState", "SaveEvent", "SessionRecovery",
]