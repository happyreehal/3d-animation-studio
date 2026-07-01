# ============================================================
# src/ui/__init__.py
# 3D Animation Studio - UI Package
# Sabhi UI components ka centralized access
# ============================================================

# Theme Manager
from src.ui.theme_manager import (
    ThemeManager,
    ThemeType,
    AccentColor,
    ColorPalette,
    FontSettings,
    LIGHT_PALETTE,
    QSSGenerator,
    get_theme_manager,
)

# Shortcuts Manager
from src.ui.shortcuts_manager import (
    ShortcutsManager,
    Shortcut,
    ShortcutCategory,
    ShortcutContext,
    ShortcutConflict,
    DefaultShortcuts,
    get_shortcuts_manager,
)

# Toolbar
from src.ui.toolbar import (
    StudioToolbar,
    ToolbarAction,
    ToolbarGroup,
    ToolbarState,
    ToolbarDefinition,
    ToolType,
    ButtonStyle,
    get_toolbar_info,
)

# Scene Hierarchy
from src.ui.scene_hierarchy import (
    SceneHierarchyWidget,
    SceneHierarchyModel,
    SceneObject,
    ObjectType,
    ObjectIcon,
    get_scene_model,
)

# Properties Panel
from src.ui.properties_panel import (
    PropertiesPanelWidget,
    PropertiesPanelModel,
    PropertyDef,
    PropertySection,
    ObjectProperties,
    PropertyBuilder,
    PropertyType,
    PanelSection,
    get_properties_model,
)

# Asset Browser
from src.ui.asset_browser import (
    AssetBrowserWidget,
    AssetBrowserModel,
    AssetItem,
    AssetFilter,
    AssetType,
    AssetStatus,
    ViewMode,
    TYPE_DISPLAY,
    TYPE_ICONS,
    EXT_TO_TYPE,
    get_asset_model,
)

# Timeline
from src.ui.timeline_widget import (
    TimelineWidget,
    TimelineModel,
    TimelineTrack,
    TimelineClip,
    TimelineMarker,
    ClipTransition,
    TrackType,
    ClipType,
    TransitionType,
    PlaybackState,
    get_timeline_model,
)

# Viewport
from src.ui.viewport_widget import (
    ViewportWidget,
    ViewportModel,
    ViewportCamera,
    ViewportSettings,
    GridSettings,
    ViewportStats,
    ViewportMode,
    ProjectionType,
    ViewPreset,
    NavigationMode,
    get_viewport_model,
)

# Dialogs
from src.ui.dialogs import (
    StudioDialogs,
    ProgressDialog,
    BaseDialogData,
    DialogResult,
    ImportSettings,
    ExportSettings,
    RenderSettings,
    ProjectSettings,
)

# Main Window
from src.ui.main_window import (
    MainWindow,
    create_main_window,
)


__all__ = [
    # Theme
    "ThemeManager", "ThemeType", "AccentColor",
    "ColorPalette", "FontSettings", "LIGHT_PALETTE",
    "QSSGenerator", "get_theme_manager",

    # Shortcuts
    "ShortcutsManager", "Shortcut", "ShortcutCategory",
    "ShortcutContext", "ShortcutConflict", "DefaultShortcuts",
    "get_shortcuts_manager",

    # Toolbar
    "StudioToolbar", "ToolbarAction", "ToolbarGroup",
    "ToolbarState", "ToolbarDefinition", "ToolType",
    "ButtonStyle", "get_toolbar_info",

    # Scene Hierarchy
    "SceneHierarchyWidget", "SceneHierarchyModel",
    "SceneObject", "ObjectType", "ObjectIcon",
    "get_scene_model",

    # Properties
    "PropertiesPanelWidget", "PropertiesPanelModel",
    "PropertyDef", "PropertySection", "ObjectProperties",
    "PropertyBuilder", "PropertyType", "PanelSection",
    "get_properties_model",

    # Assets
    "AssetBrowserWidget", "AssetBrowserModel",
    "AssetItem", "AssetFilter", "AssetType",
    "AssetStatus", "ViewMode", "TYPE_DISPLAY",
    "TYPE_ICONS", "EXT_TO_TYPE", "get_asset_model",

    # Timeline
    "TimelineWidget", "TimelineModel", "TimelineTrack",
    "TimelineClip", "TimelineMarker", "ClipTransition",
    "TrackType", "ClipType", "TransitionType",
    "PlaybackState", "get_timeline_model",

    # Viewport
    "ViewportWidget", "ViewportModel", "ViewportCamera",
    "ViewportSettings", "GridSettings", "ViewportStats",
    "ViewportMode", "ProjectionType", "ViewPreset",
    "NavigationMode", "get_viewport_model",

    # Dialogs
    "StudioDialogs", "ProgressDialog", "BaseDialogData",
    "DialogResult", "ImportSettings", "ExportSettings",
    "RenderSettings", "ProjectSettings",

    # Main Window
    "MainWindow", "create_main_window",
]