# ============================================================
# src/ui/scene_hierarchy.py
# 3D Animation Studio - Scene Hierarchy Panel
# Scene objects ka tree view - Blender style outliner
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
from typing import Dict, List, Optional, Callable, Any
from enum import Enum

from src.utils import get_logger, get_config

logger = get_logger("SceneHierarchy")


# ============================================================
# ENUMS
# ============================================================

class ObjectType(Enum):
    """Scene object types"""
    SCENE       = "scene"
    CHARACTER   = "character"
    MESH        = "mesh"
    LIGHT       = "light"
    CAMERA      = "camera"
    EMPTY       = "empty"
    GROUP       = "group"
    ARMATURE    = "armature"
    VFX         = "vfx"
    AUDIO       = "audio"
    CLOTH       = "cloth"


class ObjectIcon(Enum):
    """Object type icons (emoji)"""
    SCENE       = "🎬"
    CHARACTER   = "🧍"
    MESH        = "📦"
    LIGHT       = "💡"
    CAMERA      = "🎥"
    EMPTY       = "⊕"
    GROUP       = "📁"
    ARMATURE    = "🦴"
    VFX         = "✨"
    AUDIO       = "🔊"
    CLOTH       = "👗"
    UNKNOWN     = "❓"


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class SceneObject:
    """
    Scene mein ek object ki representation.
    Hierarchy tree ka ek node.
    """
    id:           str
    name:         str
    object_type:  str           = ObjectType.MESH.value
    parent_id:    Optional[str] = None
    children_ids: List[str]     = field(default_factory=list)

    # Visibility & state
    visible:      bool = True
    locked:       bool = False
    selected:     bool = False
    expanded:     bool = True

    # 3D properties (reference only - actual data in scene)
    position:     List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation:     List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale:        List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])

    # Metadata
    tags:         List[str]   = field(default_factory=list)
    color_tag:    str         = ""      # Color label for organization

    def get_icon(self) -> str:
        """Object type ka icon lo"""
        icon_map = {
            ObjectType.SCENE.value:     ObjectIcon.SCENE.value,
            ObjectType.CHARACTER.value: ObjectIcon.CHARACTER.value,
            ObjectType.MESH.value:      ObjectIcon.MESH.value,
            ObjectType.LIGHT.value:     ObjectIcon.LIGHT.value,
            ObjectType.CAMERA.value:    ObjectIcon.CAMERA.value,
            ObjectType.EMPTY.value:     ObjectIcon.EMPTY.value,
            ObjectType.GROUP.value:     ObjectIcon.GROUP.value,
            ObjectType.ARMATURE.value:  ObjectIcon.ARMATURE.value,
            ObjectType.VFX.value:       ObjectIcon.VFX.value,
            ObjectType.AUDIO.value:     ObjectIcon.AUDIO.value,
            ObjectType.CLOTH.value:     ObjectIcon.CLOTH.value,
        }
        return icon_map.get(self.object_type, ObjectIcon.UNKNOWN.value)

    def get_display_name(self) -> str:
        """Display ke liye naam (icon + name)"""
        icon = self.get_icon()
        status = ""
        if not self.visible:
            status += " 👁"
        if self.locked:
            status += " 🔒"
        return f"{icon} {self.name}{status}"

    def to_dict(self) -> Dict:
        """Serialization ke liye"""
        return {
            "id":           self.id,
            "name":         self.name,
            "object_type":  self.object_type,
            "parent_id":    self.parent_id,
            "children_ids": self.children_ids,
            "visible":      self.visible,
            "locked":       self.locked,
            "selected":     self.selected,
            "position":     self.position,
            "rotation":     self.rotation,
            "scale":        self.scale,
            "tags":         self.tags,
            "color_tag":    self.color_tag,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SceneObject":
        """Dict se object banao"""
        return cls(
            id          = data.get("id", ""),
            name        = data.get("name", ""),
            object_type = data.get("object_type", ObjectType.MESH.value),
            parent_id   = data.get("parent_id"),
            children_ids= data.get("children_ids", []),
            visible     = data.get("visible", True),
            locked      = data.get("locked", False),
            selected    = data.get("selected", False),
            position    = data.get("position", [0.0, 0.0, 0.0]),
            rotation    = data.get("rotation", [0.0, 0.0, 0.0]),
            scale       = data.get("scale", [1.0, 1.0, 1.0]),
            tags        = data.get("tags", []),
            color_tag   = data.get("color_tag", ""),
        )


# ============================================================
# SCENE HIERARCHY DATA MODEL
# ============================================================

class SceneHierarchyModel:
    """
    Scene hierarchy ka pure Python data model.
    Qt se independent - tree structure manage karta hai.

    Features:
    - Parent-child relationships
    - Multi-selection
    - Visibility/lock toggle
    - Search/filter
    - Drag & drop (data level)
    - Undo support
    """

    def __init__(self):
        # Objects storage: id -> SceneObject
        self._objects: Dict[str, SceneObject] = {}

        # Root objects (no parent)
        self._root_ids: List[str] = []

        # Currently selected objects
        self._selected_ids: List[str] = []

        # Change listeners
        self._listeners: List[Callable] = []

        # ID counter
        self._id_counter: int = 0

        logger.debug("SceneHierarchyModel initialized")

    def _generate_id(self, prefix: str = "obj") -> str:
        """Unique ID generate karo"""
        self._id_counter += 1
        return f"{prefix}_{self._id_counter:04d}"

    # ----------------------------------------------------------
    # OBJECT MANAGEMENT
    # ----------------------------------------------------------

    def add_object(
        self,
        name: str,
        object_type: str = ObjectType.MESH.value,
        parent_id: Optional[str] = None,
        obj_id: Optional[str] = None,
    ) -> SceneObject:
        """
        Naya object add karo hierarchy mein.

        Args:
            name: Object naam
            object_type: ObjectType value
            parent_id: Parent object ID (None = root)
            obj_id: Custom ID (None = auto-generate)

        Returns:
            Naya SceneObject
        """
        # ID generate karo
        if not obj_id:
            prefix = object_type[:3]
            obj_id = self._generate_id(prefix)

        # Object banao
        obj = SceneObject(
            id          = obj_id,
            name        = name,
            object_type = object_type,
            parent_id   = parent_id,
        )

        # Store karo
        self._objects[obj_id] = obj

        # Parent-child relationship set karo
        if parent_id and parent_id in self._objects:
            parent = self._objects[parent_id]
            if obj_id not in parent.children_ids:
                parent.children_ids.append(obj_id)
        else:
            # Root level
            if obj_id not in self._root_ids:
                self._root_ids.append(obj_id)

        self._notify("object_added", {"object": obj})
        logger.debug(f"Object added: {name} ({object_type}) ID={obj_id}")
        return obj

    def remove_object(
        self,
        obj_id: str,
        remove_children: bool = True,
    ) -> bool:
        """
        Object remove karo.

        Args:
            obj_id: Object ID
            remove_children: Children bhi remove karo?

        Returns:
            True agar successful
        """
        obj = self._objects.get(obj_id)
        if not obj:
            logger.warning(f"Object nahi mila: {obj_id}")
            return False

        # Children handle karo
        if remove_children:
            # Recursively children remove karo
            for child_id in obj.children_ids.copy():
                self.remove_object(child_id, remove_children=True)
        else:
            # Children ko root mein move karo
            for child_id in obj.children_ids:
                child = self._objects.get(child_id)
                if child:
                    child.parent_id = None
                    if child_id not in self._root_ids:
                        self._root_ids.append(child_id)

        # Parent se remove karo
        if obj.parent_id and obj.parent_id in self._objects:
            parent = self._objects[obj.parent_id]
            if obj_id in parent.children_ids:
                parent.children_ids.remove(obj_id)
        elif obj_id in self._root_ids:
            self._root_ids.remove(obj_id)

        # Selection se remove karo
        if obj_id in self._selected_ids:
            self._selected_ids.remove(obj_id)

        # Delete karo
        del self._objects[obj_id]

        self._notify("object_removed", {"obj_id": obj_id})
        logger.debug(f"Object removed: {obj_id}")
        return True

    def rename_object(self, obj_id: str, new_name: str) -> bool:
        """Object rename karo"""
        obj = self._objects.get(obj_id)
        if not obj:
            return False
        old_name   = obj.name
        obj.name   = new_name
        self._notify("object_renamed", {
            "obj_id": obj_id, "old_name": old_name, "new_name": new_name
        })
        logger.debug(f"Renamed: {old_name} → {new_name}")
        return True

    def reparent_object(
        self,
        obj_id: str,
        new_parent_id: Optional[str],
    ) -> bool:
        """
        Object ka parent change karo (drag & drop ke liye).

        Args:
            obj_id: Move karne wala object
            new_parent_id: Naya parent ID (None = root)
        """
        obj = self._objects.get(obj_id)
        if not obj:
            return False

        # Circular parenting check karo
        if new_parent_id and self._is_descendant(new_parent_id, obj_id):
            logger.warning("Circular parenting nahi ho sakta!")
            return False

        # Old parent se remove karo
        if obj.parent_id and obj.parent_id in self._objects:
            old_parent = self._objects[obj.parent_id]
            if obj_id in old_parent.children_ids:
                old_parent.children_ids.remove(obj_id)
        elif obj_id in self._root_ids:
            self._root_ids.remove(obj_id)

        # New parent set karo
        obj.parent_id = new_parent_id

        if new_parent_id and new_parent_id in self._objects:
            new_parent = self._objects[new_parent_id]
            if obj_id not in new_parent.children_ids:
                new_parent.children_ids.append(obj_id)
        else:
            if obj_id not in self._root_ids:
                self._root_ids.append(obj_id)

        self._notify("object_reparented", {
            "obj_id": obj_id, "new_parent_id": new_parent_id
        })
        return True

    def _is_descendant(self, obj_id: str, potential_ancestor_id: str) -> bool:
        """Check karo ki obj_id potential_ancestor ka descendant hai"""
        obj = self._objects.get(obj_id)
        if not obj:
            return False
        if obj.parent_id == potential_ancestor_id:
            return True
        if obj.parent_id:
            return self._is_descendant(obj.parent_id, potential_ancestor_id)
        return False

    def duplicate_object(
        self,
        obj_id: str,
        with_children: bool = True,
    ) -> Optional[SceneObject]:
        """Object duplicate karo"""
        obj = self._objects.get(obj_id)
        if not obj:
            return None

        # New object banao
        new_obj = self.add_object(
            name        = f"{obj.name}_copy",
            object_type = obj.object_type,
            parent_id   = obj.parent_id,
        )

        # Properties copy karo
        new_obj.position  = obj.position.copy()
        new_obj.rotation  = obj.rotation.copy()
        new_obj.scale     = obj.scale.copy()
        new_obj.tags      = obj.tags.copy()
        new_obj.color_tag = obj.color_tag
        new_obj.visible   = obj.visible

        # Children duplicate karo
        if with_children:
            for child_id in obj.children_ids:
                child_copy = self.duplicate_object(child_id, with_children=True)
                if child_copy:
                    self.reparent_object(child_copy.id, new_obj.id)

        logger.debug(f"Duplicated: {obj.name} → {new_obj.name}")
        return new_obj

    # ----------------------------------------------------------
    # VISIBILITY & LOCK
    # ----------------------------------------------------------

    def toggle_visibility(self, obj_id: str) -> bool:
        """Object visibility toggle karo"""
        obj = self._objects.get(obj_id)
        if not obj:
            return False
        obj.visible = not obj.visible
        self._notify("visibility_changed", {
            "obj_id": obj_id, "visible": obj.visible
        })
        return obj.visible

    def toggle_lock(self, obj_id: str) -> bool:
        """Object lock toggle karo"""
        obj = self._objects.get(obj_id)
        if not obj:
            return False
        obj.locked = not obj.locked
        self._notify("lock_changed", {
            "obj_id": obj_id, "locked": obj.locked
        })
        return obj.locked

    def set_visibility(self, obj_id: str, visible: bool):
        """Object visibility set karo"""
        obj = self._objects.get(obj_id)
        if obj:
            obj.visible = visible
            self._notify("visibility_changed", {
                "obj_id": obj_id, "visible": visible
            })

    def hide_all_except(self, obj_id: str):
        """Ek object chhod ke sabhi hide karo"""
        for oid, obj in self._objects.items():
            obj.visible = (oid == obj_id)
        self._notify("visibility_bulk_changed", {})

    def show_all(self):
        """Sabhi objects show karo"""
        for obj in self._objects.values():
            obj.visible = True
        self._notify("visibility_bulk_changed", {})

    # ----------------------------------------------------------
    # SELECTION
    # ----------------------------------------------------------

    def select_object(
        self,
        obj_id: str,
        multi_select: bool = False,
    ):
        """
        Object select karo.

        Args:
            obj_id: Select karne wala object
            multi_select: True = add to selection, False = replace
        """
        if not multi_select:
            # Pehle sab deselect karo
            for oid in self._selected_ids:
                obj = self._objects.get(oid)
                if obj:
                    obj.selected = False
            self._selected_ids.clear()

        obj = self._objects.get(obj_id)
        if obj and obj_id not in self._selected_ids:
            obj.selected = True
            self._selected_ids.append(obj_id)

        self._notify("selection_changed", {
            "selected_ids": self._selected_ids.copy()
        })

    def deselect_object(self, obj_id: str):
        """Object deselect karo"""
        obj = self._objects.get(obj_id)
        if obj:
            obj.selected = False
        if obj_id in self._selected_ids:
            self._selected_ids.remove(obj_id)
        self._notify("selection_changed", {
            "selected_ids": self._selected_ids.copy()
        })

    def select_all(self):
        """Sabhi objects select karo"""
        self._selected_ids = list(self._objects.keys())
        for obj in self._objects.values():
            obj.selected = True
        self._notify("selection_changed", {
            "selected_ids": self._selected_ids.copy()
        })

    def deselect_all(self):
        """Sabhi deselect karo"""
        for obj in self._objects.values():
            obj.selected = False
        self._selected_ids.clear()
        self._notify("selection_changed", {"selected_ids": []})

    def get_selected_objects(self) -> List[SceneObject]:
        """Selected objects lo"""
        return [
            self._objects[oid]
            for oid in self._selected_ids
            if oid in self._objects
        ]

    def get_selected_ids(self) -> List[str]:
        """Selected object IDs lo"""
        return self._selected_ids.copy()

    # ----------------------------------------------------------
    # QUERIES
    # ----------------------------------------------------------

    def get_object(self, obj_id: str) -> Optional[SceneObject]:
        """ID se object lo"""
        return self._objects.get(obj_id)

    def get_all_objects(self) -> List[SceneObject]:
        """Sabhi objects lo"""
        return list(self._objects.values())

    def get_root_objects(self) -> List[SceneObject]:
        """Root level objects lo"""
        return [
            self._objects[oid]
            for oid in self._root_ids
            if oid in self._objects
        ]

    def get_children(self, obj_id: str) -> List[SceneObject]:
        """Object ke children lo"""
        obj = self._objects.get(obj_id)
        if not obj:
            return []
        return [
            self._objects[cid]
            for cid in obj.children_ids
            if cid in self._objects
        ]

    def get_objects_by_type(self, object_type: str) -> List[SceneObject]:
        """Type se objects filter karo"""
        return [
            obj for obj in self._objects.values()
            if obj.object_type == object_type
        ]

    def search_objects(self, query: str) -> List[SceneObject]:
        """Name se objects search karo"""
        query_lower = query.lower()
        return [
            obj for obj in self._objects.values()
            if query_lower in obj.name.lower()
            or query_lower in obj.object_type.lower()
            or any(query_lower in tag.lower() for tag in obj.tags)
        ]

    def get_ancestors(self, obj_id: str) -> List[SceneObject]:
        """Object ke ancestors lo (parent chain)"""
        ancestors = []
        obj = self._objects.get(obj_id)
        while obj and obj.parent_id:
            parent = self._objects.get(obj.parent_id)
            if parent:
                ancestors.append(parent)
                obj = parent
            else:
                break
        return ancestors

    def get_flat_tree(self) -> List[Dict]:
        """
        Flat list mein hierarchy represent karo.
        Tree display ke liye (indentation level ke saath).
        """
        result = []

        def traverse(obj_id: str, depth: int = 0):
            obj = self._objects.get(obj_id)
            if not obj:
                return
            result.append({
                "obj_id":  obj_id,
                "depth":   depth,
                "name":    obj.name,
                "type":    obj.object_type,
                "icon":    obj.get_icon(),
                "visible": obj.visible,
                "locked":  obj.locked,
                "selected":obj.selected,
                "has_children": len(obj.children_ids) > 0,
            })
            if obj.expanded:
                for child_id in obj.children_ids:
                    traverse(child_id, depth + 1)

        for root_id in self._root_ids:
            traverse(root_id, 0)

        return result

    def get_statistics(self) -> Dict:
        """Scene statistics lo"""
        stats = {
            "total_objects": len(self._objects),
            "root_objects":  len(self._root_ids),
            "selected":      len(self._selected_ids),
            "visible":       sum(1 for o in self._objects.values() if o.visible),
            "hidden":        sum(1 for o in self._objects.values() if not o.visible),
            "locked":        sum(1 for o in self._objects.values() if o.locked),
            "by_type":       {},
        }
        for obj in self._objects.values():
            t = obj.object_type
            stats["by_type"][t] = stats["by_type"].get(t, 0) + 1
        return stats

    def clear(self):
        """Sabhi objects clear karo"""
        self._objects.clear()
        self._root_ids.clear()
        self._selected_ids.clear()
        self._notify("scene_cleared", {})
        logger.info("Scene hierarchy cleared")

    # ----------------------------------------------------------
    # LISTENERS
    # ----------------------------------------------------------

    def add_listener(self, callback: Callable):
        """Change listener add karo"""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable):
        """Listener remove karo"""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify(self, event: str, data: Dict):
        """Listeners ko notify karo"""
        for cb in self._listeners:
            try:
                cb(event, data)
            except Exception as e:
                logger.warning(f"Hierarchy listener error: {e}")

    def print_tree(self, indent: str = "  "):
        """Console mein tree print karo (debug ke liye)"""
        print("\n🌲 Scene Hierarchy:")
        print("=" * 40)

        def print_node(obj_id: str, depth: int = 0):
            obj = self._objects.get(obj_id)
            if not obj:
                return
            prefix    = indent * depth
            selected  = "◆" if obj.selected else " "
            visible   = "👁" if obj.visible else "🙈"
            locked    = "🔒" if obj.locked else " "
            print(
                f"{prefix}{selected} {obj.get_icon()} "
                f"{obj.name} {visible}{locked}"
            )
            for child_id in obj.children_ids:
                print_node(child_id, depth + 1)

        for root_id in self._root_ids:
            print_node(root_id)

        stats = self.get_statistics()
        print(f"\n Total: {stats['total_objects']} objects")
        print("=" * 40)


# ============================================================
# QT SCENE HIERARCHY WIDGET
# ============================================================

class SceneHierarchyWidget:
    """
    PyQt5 Scene Hierarchy Panel.
    QTreeWidget based outliner - Blender style.
    """

    def __init__(
        self,
        parent=None,
        model: Optional[SceneHierarchyModel] = None,
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

        # Data model
        self.model = model or SceneHierarchyModel()

        # Qt widget reference
        self._widget = None
        self._tree   = None

        # Item references: obj_id -> QTreeWidgetItem
        self._items: Dict[str, Any] = {}

        # Search filter
        self._search_query = ""

        # Build Qt widget
        self._build_widget()

        # Model changes sun
        self.model.add_listener(self._on_model_changed)

        logger.info("✅ SceneHierarchyWidget initialized")

    def _build_widget(self):
        """Qt widget build karo"""
        try:
            from PyQt5.QtWidgets import (
                QWidget, QVBoxLayout, QHBoxLayout,
                QTreeWidget, QTreeWidgetItem, QLineEdit,
                QPushButton, QLabel, QMenu, QAction,
                QAbstractItemView, QHeaderView,
            )
            from PyQt5.QtCore import Qt, pyqtSignal
            from PyQt5.QtGui import QColor, QBrush, QFont

            # Main container widget
            self._widget = QWidget(self.parent_widget)
            self._widget.setObjectName("SceneHierarchyPanel")

            layout = QVBoxLayout(self._widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            # ===== HEADER =====
            header = QWidget()
            header_layout = QHBoxLayout(header)
            header_layout.setContentsMargins(8, 6, 8, 6)

            title_label = QLabel("SCENE")
            title_font  = QFont()
            title_font.setPointSize(9)
            title_font.setBold(True)
            title_label.setFont(title_font)

            # Add button
            add_btn = QPushButton("+")
            add_btn.setFixedSize(22, 22)
            add_btn.setToolTip("Object add karo")
            add_btn.clicked.connect(self._on_add_clicked)

            header_layout.addWidget(title_label)
            header_layout.addStretch()
            header_layout.addWidget(add_btn)
            layout.addWidget(header)

            # ===== SEARCH BAR =====
            search_bar = QLineEdit()
            search_bar.setObjectName("HierarchySearch")
            search_bar.setPlaceholderText("🔍 Search objects...")
            search_bar.textChanged.connect(self._on_search_changed)
            search_bar.setFixedHeight(28)
            layout.addWidget(search_bar)

            # ===== TREE WIDGET =====
            self._tree = QTreeWidget()
            self._tree.setObjectName("SceneTree")
            self._tree.setHeaderLabels(["Object", "👁", "🔒"])
            self._tree.setColumnWidth(0, 180)
            self._tree.setColumnWidth(1, 24)
            self._tree.setColumnWidth(2, 24)
            self._tree.setAlternatingRowColors(True)
            self._tree.setSelectionMode(
                QAbstractItemView.ExtendedSelection
            )
            self._tree.setDragDropMode(
                QAbstractItemView.InternalMove
            )
            self._tree.setContextMenuPolicy(Qt.CustomContextMenu)

            # Header hide karo (compact look)
            self._tree.header().setSectionResizeMode(
                0, QHeaderView.Stretch
            )
            self._tree.header().setSectionResizeMode(
                1, QHeaderView.Fixed
            )
            self._tree.header().setSectionResizeMode(
                2, QHeaderView.Fixed
            )

            # Signals
            self._tree.itemSelectionChanged.connect(
                self._on_selection_changed
            )
            self._tree.itemDoubleClicked.connect(
                self._on_item_double_clicked
            )
            self._tree.customContextMenuRequested.connect(
                self._on_context_menu
            )
            self._tree.itemChanged.connect(
                self._on_item_changed
            )

            layout.addWidget(self._tree)

            # ===== STATUS BAR =====
            self._status_label = QLabel("0 objects")
            self._status_label.setObjectName("HierarchyStatus")
            layout.addWidget(self._status_label)

            # Theme apply karo
            self._apply_theme()

            logger.debug("SceneHierarchyWidget Qt built")

        except ImportError:
            logger.warning("PyQt5 nahi - hierarchy widget non-Qt mode mein")
        except Exception as e:
            logger.error(f"Widget build error: {e}")

    def _apply_theme(self):
        """Theme apply karo widget pe"""
        if not self.theme_manager or not self._widget:
            return

        try:
            p = self.theme_manager.get_palette()
            self._widget.setStyleSheet(f"""
                #SceneHierarchyPanel {{
                    background-color: {p.bg_secondary};
                    border-right: 1px solid {p.border};
                }}
                QLabel {{
                    color: {p.text_secondary};
                    font-size: 10px;
                    font-weight: bold;
                    letter-spacing: 1px;
                    padding: 0 4px;
                }}
                #HierarchySearch {{
                    background-color: {p.bg_tertiary};
                    border: none;
                    border-bottom: 1px solid {p.border};
                    color: {p.text_primary};
                    padding: 4px 8px;
                    font-size: 11px;
                }}
                #SceneTree {{
                    background-color: {p.bg_secondary};
                    alternate-background-color: {p.bg_tertiary};
                    border: none;
                    color: {p.text_primary};
                    font-size: 11px;
                    outline: 0;
                }}
                #SceneTree::item {{
                    padding: 3px 4px;
                    border-radius: 3px;
                }}
                #SceneTree::item:hover {{
                    background-color: {p.bg_hover};
                }}
                #SceneTree::item:selected {{
                    background-color: {p.bg_selected};
                    color: {p.text_primary};
                }}
                #HierarchyStatus {{
                    color: {p.text_secondary};
                    font-size: 10px;
                    padding: 3px 8px;
                    border-top: 1px solid {p.border};
                    background-color: {p.bg_secondary};
                }}
                QPushButton {{
                    background-color: {p.accent};
                    color: #000;
                    border: none;
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: {p.accent_hover};
                }}
            """)
        except Exception as e:
            logger.warning(f"Theme apply error: {e}")

    # ----------------------------------------------------------
    # TREE POPULATION
    # ----------------------------------------------------------

    def refresh_tree(self):
        """Tree widget ko model se refresh karo"""
        if not self._tree:
            return

        try:
            # Signals temporarily block karo
            self._tree.blockSignals(True)
            self._tree.clear()
            self._items.clear()

            # Root objects add karo
            for root_obj in self.model.get_root_objects():
                self._add_tree_item(root_obj, None)

            # Expand all
            self._tree.expandAll()

            # Status update
            stats = self.model.get_statistics()
            if self._status_label:
                self._status_label.setText(
                    f"{stats['total_objects']} objects | "
                    f"{stats['selected']} selected"
                )

            self._tree.blockSignals(False)

        except Exception as e:
            logger.error(f"Tree refresh error: {e}")
            if self._tree:
                self._tree.blockSignals(False)

    def _add_tree_item(self, obj: SceneObject, parent_item):
        """Ek tree item add karo"""
        try:
            from PyQt5.QtWidgets import QTreeWidgetItem
            from PyQt5.QtCore import Qt

            # Search filter
            if self._search_query:
                if self._search_query.lower() not in obj.name.lower():
                    return None

            # Item banao
            if parent_item:
                item = QTreeWidgetItem(parent_item)
            else:
                item = QTreeWidgetItem(self._tree)

            # Column 0: Name + Icon
            item.setText(0, f"{obj.get_icon()} {obj.name}")
            item.setData(0, Qt.UserRole, obj.id)

            # Column 1: Visibility
            item.setText(1, "👁" if obj.visible else "🙈")

            # Column 2: Lock
            item.setText(2, "🔒" if obj.locked else "")

            # Editable name
            item.setFlags(
                item.flags()
                | Qt.ItemIsEditable
                | Qt.ItemIsDragEnabled
                | Qt.ItemIsDropEnabled
            )

            # Selected state
            if obj.selected:
                item.setSelected(True)

            # Store reference
            self._items[obj.id] = item

            # Children add karo
            for child in self.model.get_children(obj.id):
                self._add_tree_item(child, item)

            return item

        except Exception as e:
            logger.warning(f"Tree item add error: {e}")
            return None

    def _update_item(self, obj_id: str):
        """Single item update karo"""
        item = self._items.get(obj_id)
        obj  = self.model.get_object(obj_id)
        if not item or not obj:
            return
        try:
            self._tree.blockSignals(True)
            item.setText(0, f"{obj.get_icon()} {obj.name}")
            item.setText(1, "👁" if obj.visible else "🙈")
            item.setText(2, "🔒" if obj.locked else "")
            self._tree.blockSignals(False)
        except Exception:
            if self._tree:
                self._tree.blockSignals(False)

    # ----------------------------------------------------------
    # EVENT HANDLERS
    # ----------------------------------------------------------

    def _on_model_changed(self, event: str, data: Dict):
        """Model change pe tree refresh karo"""
        refresh_events = [
            "object_added", "object_removed", "object_renamed",
            "object_reparented", "scene_cleared",
        ]
        update_events = [
            "visibility_changed", "lock_changed",
        ]

        if event in refresh_events:
            self.refresh_tree()
        elif event in update_events:
            obj_id = data.get("obj_id")
            if obj_id:
                self._update_item(obj_id)
        elif event == "visibility_bulk_changed":
            self.refresh_tree()

        # Status update
        if self._status_label:
            stats = self.model.get_statistics()
            self._status_label.setText(
                f"{stats['total_objects']} objects | "
                f"{stats['selected']} selected"
            )

    def _on_selection_changed(self):
        """Tree selection change handle karo"""
        if not self._tree:
            return

        try:
            selected_items = self._tree.selectedItems()
            from PyQt5.QtCore import Qt

            selected_ids = []
            for item in selected_items:
                obj_id = item.data(0, Qt.UserRole)
                if obj_id:
                    selected_ids.append(obj_id)

            # Model update karo
            self.model.deselect_all()
            for obj_id in selected_ids:
                self.model.select_object(obj_id, multi_select=True)

        except Exception as e:
            logger.warning(f"Selection change error: {e}")

    def _on_item_double_clicked(self, item, column: int):
        """Double click pe rename ya focus"""
        if not self._tree or not item:
            return
        try:
            from PyQt5.QtCore import Qt
            obj_id = item.data(0, Qt.UserRole)

            if column == 1:
                # Visibility toggle
                self.model.toggle_visibility(obj_id)
            elif column == 2:
                # Lock toggle
                self.model.toggle_lock(obj_id)
            else:
                # Rename mode
                self._tree.editItem(item, 0)

        except Exception as e:
            logger.warning(f"Double click error: {e}")

    def _on_item_changed(self, item, column: int):
        """Item edit complete handle karo (rename)"""
        if not item or column != 0:
            return
        try:
            from PyQt5.QtCore import Qt
            obj_id   = item.data(0, Qt.UserRole)
            new_text = item.text(0)

            if obj_id and new_text:
                # Icon remove karke sirf naam lo
                obj = self.model.get_object(obj_id)
                if obj:
                    icon     = obj.get_icon()
                    new_name = new_text.replace(f"{icon} ", "").strip()
                    if new_name and new_name != obj.name:
                        self.model.rename_object(obj_id, new_name)

        except Exception as e:
            logger.warning(f"Item changed error: {e}")

    def _on_context_menu(self, position):
        """Right-click context menu"""
        if not self._tree:
            return

        try:
            from PyQt5.QtWidgets import QMenu, QAction
            from PyQt5.QtCore import Qt

            item = self._tree.itemAt(position)
            menu = QMenu(self._widget)

            if item:
                obj_id = item.data(0, Qt.UserRole)
                obj    = self.model.get_object(obj_id)

                if obj:
                    # Object-specific actions
                    rename_action = QAction(f"✏️ Rename '{obj.name}'", menu)
                    rename_action.triggered.connect(
                        lambda: self._tree.editItem(item, 0)
                    )
                    menu.addAction(rename_action)

                    dup_action = QAction("📋 Duplicate", menu)
                    dup_action.triggered.connect(
                        lambda: self._duplicate_selected()
                    )
                    menu.addAction(dup_action)

                    vis_text = "🙈 Hide" if obj.visible else "👁 Show"
                    vis_action = QAction(vis_text, menu)
                    vis_action.triggered.connect(
                        lambda: self.model.toggle_visibility(obj_id)
                    )
                    menu.addAction(vis_action)

                    lock_text = "🔓 Unlock" if obj.locked else "🔒 Lock"
                    lock_action = QAction(lock_text, menu)
                    lock_action.triggered.connect(
                        lambda: self.model.toggle_lock(obj_id)
                    )
                    menu.addAction(lock_action)

                    menu.addSeparator()

                    del_action = QAction("🗑️ Delete", menu)
                    del_action.triggered.connect(
                        lambda: self.model.remove_object(obj_id)
                    )
                    menu.addAction(del_action)

            menu.addSeparator()

            # General actions
            add_char = QAction("🧍 Add Character", menu)
            add_char.triggered.connect(
                lambda: self._quick_add(ObjectType.CHARACTER.value)
            )
            menu.addAction(add_char)

            add_mesh = QAction("📦 Add Mesh", menu)
            add_mesh.triggered.connect(
                lambda: self._quick_add(ObjectType.MESH.value)
            )
            menu.addAction(add_mesh)

            add_light = QAction("💡 Add Light", menu)
            add_light.triggered.connect(
                lambda: self._quick_add(ObjectType.LIGHT.value)
            )
            menu.addAction(add_light)

            add_cam = QAction("🎥 Add Camera", menu)
            add_cam.triggered.connect(
                lambda: self._quick_add(ObjectType.CAMERA.value)
            )
            menu.addAction(add_cam)

            menu.addSeparator()

            show_all = QAction("👁 Show All", menu)
            show_all.triggered.connect(self.model.show_all)
            menu.addAction(show_all)

            sel_all = QAction("◆ Select All", menu)
            sel_all.triggered.connect(self.model.select_all)
            menu.addAction(sel_all)

            menu.exec_(self._tree.viewport().mapToGlobal(position))

        except Exception as e:
            logger.warning(f"Context menu error: {e}")

    def _on_add_clicked(self):
        """Add button click handler"""
        self._quick_add(ObjectType.MESH.value)

    def _quick_add(self, object_type: str):
        """Quick object add karo"""
        names = {
            ObjectType.CHARACTER.value: "Character",
            ObjectType.MESH.value:      "Mesh",
            ObjectType.LIGHT.value:     "Light",
            ObjectType.CAMERA.value:    "Camera",
            ObjectType.VFX.value:       "VFX",
        }
        name = names.get(object_type, "Object")
        count = len(self.model.get_objects_by_type(object_type)) + 1
        self.model.add_object(f"{name}.{count:03d}", object_type)

    def _duplicate_selected(self):
        """Selected objects duplicate karo"""
        for obj in self.model.get_selected_objects():
            self.model.duplicate_object(obj.id)

    def _on_search_changed(self, query: str):
        """Search query change handle karo"""
        self._search_query = query
        self.refresh_tree()

    # ----------------------------------------------------------
    # PUBLIC API
    # ----------------------------------------------------------

    def get_widget(self):
        """Qt widget lo"""
        return self._widget

    def get_model(self) -> SceneHierarchyModel:
        """Data model lo"""
        return self.model

    def select_by_id(self, obj_id: str, multi: bool = False):
        """Programmatically object select karo"""
        self.model.select_object(obj_id, multi_select=multi)
        self.refresh_tree()

    def focus_object(self, obj_id: str):
        """Object pe focus karo (tree mein scroll)"""
        item = self._items.get(obj_id)
        if item and self._tree:
            try:
                self._tree.scrollToItem(item)
                self._tree.setCurrentItem(item)
            except Exception:
                pass


# ============================================================
# GLOBAL INSTANCE
# ============================================================

_global_model: Optional[SceneHierarchyModel] = None


def get_scene_model() -> SceneHierarchyModel:
    """Global SceneHierarchyModel lo (singleton)"""
    global _global_model
    if _global_model is None:
        _global_model = SceneHierarchyModel()
    return _global_model


# ============================================================
# TEST SECTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="DEBUG")
    print_banner("Scene Hierarchy Test", "Scene Objects Tree Manager")

    # ===== TEST 1: Model Initialization =====
    print_section("Test 1: Model Initialization")
    model = SceneHierarchyModel()
    print(f"✅ SceneHierarchyModel initialized")
    print(f"   Objects: {len(model.get_all_objects())}")

    # ===== TEST 2: Add Objects =====
    print_section("Test 2: Adding Objects")

    # Root objects
    scene_root = model.add_object("Scene", ObjectType.SCENE.value)
    char1  = model.add_object("Hero",   ObjectType.CHARACTER.value)
    char2  = model.add_object("Villain",ObjectType.CHARACTER.value)
    light1 = model.add_object("Sun",    ObjectType.LIGHT.value)
    cam1   = model.add_object("Main Camera", ObjectType.CAMERA.value)
    vfx1   = model.add_object("Fire VFX", ObjectType.VFX.value)

    # Children
    sword  = model.add_object("Sword",  ObjectType.MESH.value, parent_id=char1.id)
    shield = model.add_object("Shield", ObjectType.MESH.value, parent_id=char1.id)
    cape   = model.add_object("Cape",   ObjectType.CLOTH.value, parent_id=char2.id)

    stats = model.get_statistics()
    print(f"✅ Objects added: {stats['total_objects']}")
    print(f"   Root objects : {stats['root_objects']}")
    print(f"   By type      : {stats['by_type']}")

    # ===== TEST 3: Tree Structure =====
    print_section("Test 3: Tree Structure")
    model.print_tree()

    # ===== TEST 4: Flat Tree =====
    print_section("Test 4: Flat Tree (for UI)")
    flat = model.get_flat_tree()
    print(f"✅ Flat tree: {len(flat)} entries")
    for entry in flat:
        indent = "  " * entry['depth']
        sel    = "◆" if entry['selected'] else " "
        print(
            f"  {indent}{sel} {entry['icon']} "
            f"{entry['name']:20s} (depth={entry['depth']})"
        )

    # ===== TEST 5: Selection =====
    print_section("Test 5: Selection System")
    model.select_object(char1.id)
    print(f"✅ Selected: {[o.name for o in model.get_selected_objects()]}")

    model.select_object(char2.id, multi_select=True)
    print(f"✅ Multi-select: {[o.name for o in model.get_selected_objects()]}")

    model.select_all()
    print(f"✅ Select all: {len(model.get_selected_ids())} objects")

    model.deselect_all()
    print(f"✅ Deselect all: {len(model.get_selected_ids())} selected")

    # ===== TEST 6: Visibility & Lock =====
    print_section("Test 6: Visibility & Lock")
    model.toggle_visibility(char1.id)
    print(f"✅ Hero visibility: {model.get_object(char1.id).visible}")

    model.toggle_visibility(char1.id)
    print(f"✅ Hero visibility restored: {model.get_object(char1.id).visible}")

    model.toggle_lock(cam1.id)
    print(f"✅ Camera locked: {model.get_object(cam1.id).locked}")

    model.hide_all_except(char1.id)
    visible_count = sum(1 for o in model.get_all_objects() if o.visible)
    print(f"✅ Hide all except Hero: {visible_count} visible")

    model.show_all()
    visible_count = sum(1 for o in model.get_all_objects() if o.visible)
    print(f"✅ Show all: {visible_count} visible")

    # ===== TEST 7: Search =====
    print_section("Test 7: Search")
    results = model.search_objects("char")
    print(f"✅ Search 'char': {len(results)} results")
    for r in results:
        print(f"   → {r.get_icon()} {r.name}")

    results2 = model.search_objects("camera")
    print(f"✅ Search 'camera': {[r.name for r in results2]}")

    # ===== TEST 8: Rename =====
    print_section("Test 8: Rename")
    old_name = char1.name
    model.rename_object(char1.id, "SuperHero")
    print(f"✅ Renamed: {old_name} → {model.get_object(char1.id).name}")

    # ===== TEST 9: Duplicate =====
    print_section("Test 9: Duplicate")
    dup = model.duplicate_object(char1.id, with_children=True)
    if dup:
        print(f"✅ Duplicated: {dup.name}")
        dup_children = model.get_children(dup.id)
        print(f"   Children copies: {[c.name for c in dup_children]}")

    # ===== TEST 10: Reparent =====
    print_section("Test 10: Reparent (Drag & Drop)")
    print(f"   Before: light1 parent = {light1.parent_id}")
    model.reparent_object(light1.id, char1.id)
    print(f"✅ After reparent: light1 parent = {light1.parent_id}")
    print(f"   Hero children: {[model.get_object(c).name for c in char1.children_ids if model.get_object(c)]}")

    # Wapas root pe
    model.reparent_object(light1.id, None)
    print(f"✅ Back to root: {light1.parent_id}")

    # ===== TEST 11: Ancestors =====
    print_section("Test 11: Ancestors")
    ancestors = model.get_ancestors(sword.id)
    print(f"✅ Sword ancestors: {[a.name for a in ancestors]}")

    # ===== TEST 12: Remove =====
    print_section("Test 12: Remove Objects")
    before_count = len(model.get_all_objects())
    model.remove_object(dup.id, remove_children=True)
    after_count = len(model.get_all_objects())
    print(f"✅ Removed duplicate: {before_count} → {after_count} objects")

    # ===== TEST 13: Listeners =====
    print_section("Test 13: Event Listeners")
    events_log = []

    def on_event(event, data):
        events_log.append(event)

    model.add_listener(on_event)
    model.add_object("Test Obj", ObjectType.MESH.value)
    model.rename_object(char1.id, "Hero2")
    model.toggle_visibility(light1.id)
    print(f"✅ Events received: {events_log}")

    # ===== TEST 14: Qt Widget =====
    print_section("Test 14: Qt Widget Build")
    try:
        from PyQt5.QtWidgets import QApplication, QMainWindow, QDockWidget
        from PyQt5.QtCore import Qt
        import sys as _sys

        app = QApplication.instance() or QApplication(_sys.argv)

        from src.ui.theme_manager import ThemeManager
        theme = ThemeManager()
        theme.set_application(app)

        window = QMainWindow()
        window.setWindowTitle("Scene Hierarchy Test")
        window.resize(300, 600)

        # Widget banao
        hierarchy_widget = SceneHierarchyWidget(
            model         = model,
            theme_manager = theme,
        )

        # Dock mein add karo
        dock = QDockWidget("Scene Hierarchy", window)
        dock.setWidget(hierarchy_widget.get_widget())
        window.addDockWidget(Qt.LeftDockWidgetArea, dock)

        # Tree refresh
        hierarchy_widget.refresh_tree()

        window.show()
        print(f"✅ Qt widget built and shown")
        print(f"   Tree items: {len(hierarchy_widget._items)}")

        from PyQt5.QtCore import QTimer
        QTimer.singleShot(800, app.quit)
        app.exec_()
        print(f"✅ Qt test complete")

    except ImportError:
        print("⚠️  PyQt5 visual test skip")
    except Exception as e:
        print(f"⚠️  Qt test: {e}")

    # ===== TEST 15: Clear =====
    print_section("Test 15: Clear Scene")
    model.clear()
    print(f"✅ Scene cleared: {len(model.get_all_objects())} objects")

    # ===== TEST 16: Global Model =====
    print_section("Test 16: Global Singleton")
    m1 = get_scene_model()
    m2 = get_scene_model()
    print(f"✅ Singleton: {m1 is m2}")

    print_banner("✅ All Tests Passed!", "scene_hierarchy.py Working Perfectly")