# ============================================================
# 3D ANIMATION STUDIO - Timeline Editor
# ============================================================
# Features:
# - Multi-track timeline (video, audio, subtitle, effect)
# - Clip management: add/move/trim/split/delete/duplicate
# - Frame-perfect precision (60fps, 30fps, 24fps)
# - Time markers with labels & colors
# - Ripple edit (move one, adjust others)
# - Snapping (to frames, markers, other clips)
# - Playhead control (play/pause/scrub/step)
# - Track locking & muting
# - Undo/redo command system
# - Groups & nested clips
# - Export/import timeline data (JSON)
# - Integration with AI (TTS, Lipsync, Expression) & Audio
# - Event listeners (timeline changes)
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

import time
import json
import copy
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Callable, Any

from src.utils import (
    get_logger, get_config, ensure_dir, generate_short_id,
    get_timestamp, format_duration, seconds_to_timecode,
    read_json, write_json, clamp, lerp,
)

logger = get_logger("Timeline")


# ============================================================
# CONSTANTS & ENUMS
# ============================================================

class TrackType(Enum):
    """
    Timeline track types — kya content hold karta hai.
    Har type ka apna behavior aur constraints hain.
    """
    VIDEO     = "video"       # 3D scenes, images, video clips
    AUDIO     = "audio"       # Dialogue, music, SFX
    SUBTITLE  = "subtitle"    # Text overlays, captions
    EFFECT    = "effect"      # Color grading, transitions
    MARKER    = "marker"      # Time labels/cues (metadata)
    CAMERA    = "camera"      # Camera animation keyframes
    LIGHTING  = "lighting"    # Lighting changes


class ClipType(Enum):
    """Clip content types"""
    VIDEO       = "video"
    AUDIO       = "audio"
    IMAGE       = "image"
    TEXT        = "text"
    SCENE_3D    = "scene_3d"    # 3D scene reference
    LIPSYNC     = "lipsync"     # LipsyncData reference
    EXPRESSION  = "expression"  # ExpressionData reference
    EFFECT      = "effect"      # Effect preset
    TTS         = "tts"         # TTS-generated audio
    TRANSITION  = "transition"  # Between two clips


class PlaybackState(Enum):
    """Timeline playback state"""
    STOPPED  = "stopped"
    PLAYING  = "playing"
    PAUSED   = "paused"
    SCRUBBING= "scrubbing"    # User dragging playhead


class SnapMode(Enum):
    """Snapping behavior"""
    NONE       = "none"       # Free positioning
    FRAMES     = "frames"     # Snap to frame boundaries
    SECONDS    = "seconds"    # Snap to whole seconds
    MARKERS    = "markers"    # Snap to time markers
    CLIPS      = "clips"      # Snap to other clip edges
    ALL        = "all"        # Snap to all above


class RippleMode(Enum):
    """Ripple edit behavior"""
    OFF       = "off"         # Just move selected clip
    TRACK     = "track"       # Move only clips on same track
    ALL       = "all"         # Move clips on all tracks


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class TimeMarker:
    """
    ⚠️ Time marker — timeline pe label lagane ke liye.
    Scene changes, chapters, cues track karne ke liye useful.
    """
    id          : str                       = field(default_factory=generate_short_id)
    time        : float                     = 0.0       # Position in seconds
    label       : str                       = "Marker"
    color       : str                       = "#00D4FF" # Hex color for UI
    description : str                       = ""
    is_chapter  : bool                      = False     # YouTube chapter marker?

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "TimeMarker":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Clip:
    """
    🎬 Timeline pe ek content piece.
    Ye actual content ka reference hai — file, ID, ya inline data.
    """
    id            : str                             = field(default_factory=generate_short_id)
    name          : str                             = "Clip"
    clip_type     : ClipType                        = ClipType.VIDEO

    # Position & timing
    start_time    : float                           = 0.0    # Timeline pe kab shuru
    duration      : float                           = 1.0    # Kitna length hai
    trim_start    : float                           = 0.0    # Source se kahan se start karo
    trim_end      : float                           = 0.0    # Source ke end se kitna cut karo

    # Content reference
    source_path   : Optional[str]                   = None   # File path (audio/video)
    source_id     : Optional[str]                   = None   # Reference to asset/scene
    text_content  : str                             = ""     # For text clips
    metadata      : Dict[str, Any]                  = field(default_factory=dict)

    # Visual/UI
    color         : str                             = "#4A90E2"
    thumbnail     : Optional[str]                   = None

    # Properties
    volume        : float                           = 1.0    # For audio clips
    opacity       : float                           = 1.0    # For video clips
    speed         : float                           = 1.0    # Playback speed multiplier
    muted         : bool                            = False
    locked        : bool                            = False  # Prevent editing

    # Effects on this clip
    effects       : List[Dict]                      = field(default_factory=list)

    # Grouping
    group_id      : Optional[str]                   = None

    # Fade in/out (seconds)
    fade_in       : float                           = 0.0
    fade_out      : float                           = 0.0

    @property
    def end_time(self) -> float:
        """Timeline pe clip kab end hoga"""
        return self.start_time + self.duration

    @property
    def source_duration(self) -> float:
        """Original source ki full duration (trim se pehle)"""
        return self.duration + self.trim_start + self.trim_end

    def contains_time(self, time: float) -> bool:
        """Check if given time falls within this clip"""
        return self.start_time <= time < self.end_time

    def get_local_time(self, timeline_time: float) -> float:
        """
        Timeline time ko clip ke local time mein convert karo.
        Trim + speed adjust hote hain.
        """
        if not self.contains_time(timeline_time):
            return 0.0
        offset = timeline_time - self.start_time
        return self.trim_start + (offset * self.speed)

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["clip_type"] = self.clip_type.value
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> "Clip":
        # Enum convert karo
        if "clip_type" in data and isinstance(data["clip_type"], str):
            data["clip_type"] = ClipType(data["clip_type"])

        # Filter to known fields
        valid_data = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_data)


@dataclass
class Track:
    """
    📊 Timeline track — ek horizontal row jo clips hold karti hai.
    Har track ka apna type aur properties hote hain.
    """
    id          : str                       = field(default_factory=generate_short_id)
    name        : str                       = "Track"
    track_type  : TrackType                 = TrackType.VIDEO
    clips       : List[Clip]                = field(default_factory=list)

    # Track properties
    height      : int                       = 60        # UI height in pixels
    color       : str                       = "#2D2D3E"
    order       : int                       = 0         # Display order (top to bottom)

    # Track state
    muted       : bool                      = False
    solo        : bool                      = False     # Only this track plays
    locked      : bool                      = False     # Prevent editing
    visible     : bool                      = True
    volume      : float                     = 1.0       # Audio tracks

    def add_clip(self, clip: Clip) -> bool:
        """Clip add karo track pe (sorted by start_time)"""
        if self.locked:
            logger.warning(f"Track '{self.name}' is locked")
            return False

        self.clips.append(clip)
        # Sort by start time for efficient lookup
        self.clips.sort(key=lambda c: c.start_time)
        return True

    def remove_clip(self, clip_id: str) -> bool:
        """Clip remove karo by ID"""
        if self.locked:
            return False

        for i, c in enumerate(self.clips):
            if c.id == clip_id:
                del self.clips[i]
                return True
        return False

    def get_clip(self, clip_id: str) -> Optional[Clip]:
        """Clip find karo by ID"""
        for c in self.clips:
            if c.id == clip_id:
                return c
        return None

    def get_clips_at_time(self, time: float) -> List[Clip]:
        """Given time pe active clips return karo"""
        return [c for c in self.clips if c.contains_time(time)]

    def get_duration(self) -> float:
        """Track ki total duration (last clip end)"""
        if not self.clips:
            return 0.0
        return max(c.end_time for c in self.clips)

    def has_overlap(self, clip: Clip, exclude_id: Optional[str] = None) -> bool:
        """
        Check karo agar clip kisi existing clip se overlap kar raha hai.
        exclude_id: ye ID skip karo (khud ke move ke waqt useful)
        """
        for c in self.clips:
            if c.id == exclude_id:
                continue
            # Overlap detection
            if not (clip.end_time <= c.start_time or clip.start_time >= c.end_time):
                return True
        return False

    def to_dict(self) -> Dict:
        return {
            "id"         : self.id,
            "name"       : self.name,
            "track_type" : self.track_type.value,
            "height"     : self.height,
            "color"      : self.color,
            "order"      : self.order,
            "muted"      : self.muted,
            "solo"       : self.solo,
            "locked"     : self.locked,
            "visible"    : self.visible,
            "volume"     : self.volume,
            "clips"      : [c.to_dict() for c in self.clips],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Track":
        track = cls(
            id         = data.get("id", generate_short_id()),
            name       = data.get("name", "Track"),
            track_type = TrackType(data.get("track_type", "video")),
            height     = data.get("height", 60),
            color      = data.get("color", "#2D2D3E"),
            order      = data.get("order", 0),
            muted      = data.get("muted", False),
            solo       = data.get("solo", False),
            locked     = data.get("locked", False),
            visible    = data.get("visible", True),
            volume     = data.get("volume", 1.0),
        )
        for clip_data in data.get("clips", []):
            track.clips.append(Clip.from_dict(clip_data))
        track.clips.sort(key=lambda c: c.start_time)
        return track


# ============================================================
# COMMAND SYSTEM — Undo/Redo Support
# ============================================================

class TimelineCommand:
    """
    Base class for undoable commands.
    Har edit action ek command banata hai jo undo/redo ho sakta hai.
    """

    def __init__(self, description: str = "Command"):
        import time as _time_module   # Local import — variable shadowing avoid
        self.description = description
        self.timestamp   = _time_module.time()

    def execute(self, timeline: "Timeline") -> bool:
        """Command execute karo — override in subclass"""
        raise NotImplementedError

    def undo(self, timeline: "Timeline") -> bool:
        """Command undo karo — override in subclass"""
        raise NotImplementedError


class AddClipCommand(TimelineCommand):
    """Add clip command"""

    def __init__(self, track_id: str, clip: Clip):
        super().__init__(f"Add clip '{clip.name}'")
        self.track_id = track_id
        self.clip     = clip

    def execute(self, timeline: "Timeline") -> bool:
        track = timeline.get_track(self.track_id)
        if track:
            return track.add_clip(self.clip)
        return False

    def undo(self, timeline: "Timeline") -> bool:
        track = timeline.get_track(self.track_id)
        if track:
            return track.remove_clip(self.clip.id)
        return False


class RemoveClipCommand(TimelineCommand):
    """Remove clip command — clip data save karta hai undo ke liye"""

    def __init__(self, track_id: str, clip: Clip):
        super().__init__(f"Remove clip '{clip.name}'")
        self.track_id = track_id
        self.clip     = copy.deepcopy(clip)  # Undo ke liye backup

    def execute(self, timeline: "Timeline") -> bool:
        track = timeline.get_track(self.track_id)
        if track:
            return track.remove_clip(self.clip.id)
        return False

    def undo(self, timeline: "Timeline") -> bool:
        track = timeline.get_track(self.track_id)
        if track:
            return track.add_clip(self.clip)
        return False


class MoveClipCommand(TimelineCommand):
    """Move clip command — old aur new position track karta hai"""

    def __init__(self, track_id: str, clip_id: str,
                 old_time: float, new_time: float):
        super().__init__(f"Move clip")
        self.track_id = track_id
        self.clip_id  = clip_id
        self.old_time = old_time
        self.new_time = new_time

    def execute(self, timeline: "Timeline") -> bool:
        track = timeline.get_track(self.track_id)
        if track:
            clip = track.get_clip(self.clip_id)
            if clip:
                clip.start_time = self.new_time
                track.clips.sort(key=lambda c: c.start_time)
                return True
        return False

    def undo(self, timeline: "Timeline") -> bool:
        track = timeline.get_track(self.track_id)
        if track:
            clip = track.get_clip(self.clip_id)
            if clip:
                clip.start_time = self.old_time
                track.clips.sort(key=lambda c: c.start_time)
                return True
        return False


class UndoRedoManager:
    """
    ↩️ Undo/redo stack manager.
    Configurable history size — memory efficient.
    """

    def __init__(self, max_history: int = 100):
        self._undo_stack : List[TimelineCommand] = []
        self._redo_stack : List[TimelineCommand] = []
        self._max_history = max_history

    def execute(self, command: TimelineCommand, timeline: "Timeline") -> bool:
        """Command execute karo aur history mein add karo"""
        success = command.execute(timeline)
        if success:
            self._undo_stack.append(command)
            self._redo_stack.clear()  # Nayi action ke baad redo invalid

            # Limit history size
            if len(self._undo_stack) > self._max_history:
                self._undo_stack.pop(0)

            logger.debug(f"↩️  Executed: {command.description}")
        return success

    def undo(self, timeline: "Timeline") -> bool:
        """Last command undo karo"""
        if not self._undo_stack:
            logger.debug("Nothing to undo")
            return False

        command = self._undo_stack.pop()
        if command.undo(timeline):
            self._redo_stack.append(command)
            logger.debug(f"↶ Undid: {command.description}")
            return True
        return False

    def redo(self, timeline: "Timeline") -> bool:
        """Last undo redo karo"""
        if not self._redo_stack:
            logger.debug("Nothing to redo")
            return False

        command = self._redo_stack.pop()
        if command.execute(timeline):
            self._undo_stack.append(command)
            logger.debug(f"↷ Redid: {command.description}")
            return True
        return False

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def get_undo_history(self) -> List[str]:
        """Recent undo actions ki list"""
        return [c.description for c in reversed(self._undo_stack)]

    def clear(self):
        """Sab history clear karo"""
        self._undo_stack.clear()
        self._redo_stack.clear()


# ============================================================
# SNAP MANAGER — Snapping Logic
# ============================================================

class SnapManager:
    """
    🧲 Snap positions calculate karta hai.
    User clip drag kare toh nearby positions pe automatically stick ho.
    """

    def __init__(self,
                 snap_mode: SnapMode = SnapMode.ALL,
                 snap_threshold: float = 0.15,   # Seconds
                 fps: int = 30):
        self.snap_mode      = snap_mode
        self.snap_threshold = snap_threshold
        self.fps            = fps

    def get_snap_positions(self, timeline: "Timeline",
                           exclude_clip_id: Optional[str] = None) -> List[float]:
        """Sab snap positions collect karo current mode ke basis pe"""
        positions = set()

        if self.snap_mode == SnapMode.NONE:
            return []

        # Frame boundaries (agar zoomed in enough hai)
        if self.snap_mode in [SnapMode.FRAMES, SnapMode.ALL]:
            # Playhead ke aas paas ke frames add karo
            frame_duration = 1.0 / self.fps
            current = 0.0
            end     = timeline.get_duration() + 1.0
            while current <= end:
                positions.add(round(current, 4))
                current += frame_duration

        # Whole seconds
        if self.snap_mode in [SnapMode.SECONDS, SnapMode.ALL]:
            end = int(timeline.get_duration()) + 2
            for s in range(end):
                positions.add(float(s))

        # Markers
        if self.snap_mode in [SnapMode.MARKERS, SnapMode.ALL]:
            for marker in timeline.markers:
                positions.add(marker.time)

        # Other clip edges
        if self.snap_mode in [SnapMode.CLIPS, SnapMode.ALL]:
            for track in timeline.tracks:
                for clip in track.clips:
                    if clip.id != exclude_clip_id:
                        positions.add(clip.start_time)
                        positions.add(clip.end_time)

        # Playhead position
        positions.add(timeline.playhead_time)

        return sorted(positions)

    def snap(self, time: float, timeline: "Timeline",
             exclude_clip_id: Optional[str] = None) -> Tuple[float, bool]:
        """
        Given time ko nearest snap position pe snap karo.

        Returns:
            (snapped_time, was_snapped)
        """
        if self.snap_mode == SnapMode.NONE:
            return time, False

        positions = self.get_snap_positions(timeline, exclude_clip_id)
        if not positions:
            return time, False

        # Nearest position dhundo
        nearest      = min(positions, key=lambda p: abs(p - time))
        distance     = abs(nearest - time)

        if distance <= self.snap_threshold:
            return nearest, True

        return time, False


# ============================================================
# MAIN TIMELINE CLASS
# ============================================================

class Timeline:
    """
    ⏱️ Main Timeline Class

    Multi-track animation timeline. Sab clips, markers, playback
    control yahan se manage hote hain.

    Usage:
        timeline = Timeline(fps=30)
        video_track = timeline.add_track("Video", TrackType.VIDEO)
        clip = Clip(name="Intro", duration=5.0)
        timeline.add_clip(video_track.id, clip)
        timeline.play()
    """

    def __init__(self,
                 name: str = "Untitled Timeline",
                 fps: int = 30,
                 config: Optional[Dict] = None):
        """
        Args:
            name  : Timeline ka naam
            fps   : Frame rate (24, 30, 60)
            config: Optional config override
        """
        # Config setup
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # Timeline properties
        self.id          = generate_short_id()
        self.name        = name
        self.fps         = fps
        self.duration    = 60.0    # Total timeline length (grows automatically)
        self.created_at  = get_timestamp()
        self.modified_at = get_timestamp()

        # Content
        self.tracks  : List[Track]      = []
        self.markers : List[TimeMarker] = []

        # Playback state
        self.playback_state = PlaybackState.STOPPED
        self.playhead_time  = 0.0
        self.playback_speed = 1.0
        self.loop_enabled   = False
        self.loop_start     = 0.0
        self.loop_end       = 0.0

        # Selection
        self.selected_clip_ids : List[str] = []
        self.selected_track_id : Optional[str] = None

        # Editing modes
        self.ripple_mode = RippleMode.OFF

        # Sub-systems
        self.undo_redo = UndoRedoManager()
        self.snap      = SnapManager(fps=fps)

        # Event listeners
        self._change_listeners  : List[Callable] = []
        self._playback_listeners: List[Callable] = []

        # Statistics
        self._stats = {
            "clips_added"   : 0,
            "clips_removed" : 0,
            "clips_moved"   : 0,
        }

        logger.info(f"⏱️  Timeline created: '{name}' @ {fps}fps")

    # ── TRACK MANAGEMENT ──────────────────────────────────

    def add_track(self, name: str,
                  track_type: TrackType = TrackType.VIDEO,
                  order: Optional[int] = None) -> Track:
        """
        Naya track add karo.

        Args:
            name       : Track ka naam
            track_type : TrackType enum
            order      : Display order (None = auto)

        Returns:
            Created Track object
        """
        if order is None:
            order = len(self.tracks)

        track = Track(
            name       = name,
            track_type = track_type,
            order      = order,
        )
        self.tracks.append(track)
        self._sort_tracks()

        self._notify_change("track_added", {"track_id": track.id})
        logger.info(f"📊 Track added: '{name}' ({track_type.value})")
        return track

    def remove_track(self, track_id: str) -> bool:
        """Track remove karo"""
        for i, t in enumerate(self.tracks):
            if t.id == track_id:
                del self.tracks[i]
                self._notify_change("track_removed", {"track_id": track_id})
                logger.info(f"🗑️  Track removed: {t.name}")
                return True
        return False

    def get_track(self, track_id: str) -> Optional[Track]:
        """Track find karo by ID"""
        for t in self.tracks:
            if t.id == track_id:
                return t
        return None

    def get_tracks_by_type(self, track_type: TrackType) -> List[Track]:
        """Specific type ke sab tracks"""
        return [t for t in self.tracks if t.track_type == track_type]

    def _sort_tracks(self):
        """Order ke basis pe tracks sort karo"""
        self.tracks.sort(key=lambda t: t.order)

    # ── CLIP MANAGEMENT ───────────────────────────────────

    def add_clip(self, track_id: str, clip: Clip,
                 use_undo: bool = True) -> bool:
        """
        Clip add karo track pe.

        Args:
            track_id : Track ka ID
            clip     : Clip object
            use_undo : Undo/redo history mein add karna hai?
        """
        track = self.get_track(track_id)
        if not track:
            logger.error(f"Track not found: {track_id}")
            return False

        # Overlap check
        if track.has_overlap(clip):
            logger.warning(
                f"Clip '{clip.name}' overlaps with existing clips on '{track.name}'"
            )
            # Overlap allowed karte hain — user ki responsibility

        # Command pattern se add karo
        if use_undo:
            cmd = AddClipCommand(track_id, clip)
            success = self.undo_redo.execute(cmd, self)
        else:
            success = track.add_clip(clip)

        if success:
            self._stats["clips_added"] += 1
            self._update_duration()
            self._notify_change("clip_added", {
                "track_id": track_id,
                "clip_id" : clip.id,
            })
            logger.debug(f"➕ Clip added: '{clip.name}' @ {clip.start_time:.2f}s")

        return success

    def remove_clip(self, track_id: str, clip_id: str,
                    use_undo: bool = True) -> bool:
        """Clip remove karo"""
        track = self.get_track(track_id)
        if not track:
            return False

        clip = track.get_clip(clip_id)
        if not clip:
            return False

        if use_undo:
            cmd = RemoveClipCommand(track_id, clip)
            success = self.undo_redo.execute(cmd, self)
        else:
            success = track.remove_clip(clip_id)

        if success:
            self._stats["clips_removed"] += 1
            self._update_duration()
            self._notify_change("clip_removed", {
                "track_id": track_id,
                "clip_id" : clip_id,
            })
        return success

    def move_clip(self, track_id: str, clip_id: str,
                  new_time: float,
                  use_snap: bool = True,
                  use_undo: bool = True) -> bool:
        """
        Clip ko new time pe move karo.

        Args:
            track_id : Track ID
            clip_id  : Clip ID
            new_time : Naya start time
            use_snap : Snapping enabled?
            use_undo : Undo history mein add?
        """
        track = self.get_track(track_id)
        if not track:
            return False

        clip = track.get_clip(clip_id)
        if not clip or clip.locked:
            return False

        old_time = clip.start_time

        # Snapping apply karo
        if use_snap:
            new_time, snapped = self.snap.snap(new_time, self, exclude_clip_id=clip_id)
            if snapped:
                logger.debug(f"🧲 Snapped to {new_time:.3f}s")

        # Prevent negative time
        new_time = max(0.0, new_time)

        # Ripple mode handling
        if self.ripple_mode == RippleMode.TRACK:
            self._apply_ripple_to_track(track, clip, new_time - old_time)
        elif self.ripple_mode == RippleMode.ALL:
            self._apply_ripple_to_all(clip, new_time - old_time)

        # Command execute karo
        if use_undo:
            cmd = MoveClipCommand(track_id, clip_id, old_time, new_time)
            success = self.undo_redo.execute(cmd, self)
        else:
            clip.start_time = new_time
            track.clips.sort(key=lambda c: c.start_time)
            success = True

        if success:
            self._stats["clips_moved"] += 1
            self._update_duration()
            self._notify_change("clip_moved", {
                "track_id": track_id,
                "clip_id" : clip_id,
                "new_time": new_time,
            })

        return success

    def trim_clip(self, track_id: str, clip_id: str,
                  new_duration: float,
                  trim_from_start: bool = False) -> bool:
        """
        Clip ko trim karo — length change karo.

        Args:
            trim_from_start: True = start se trim, False = end se trim
        """
        track = self.get_track(track_id)
        if not track:
            return False

        clip = track.get_clip(clip_id)
        if not clip or clip.locked:
            return False

        new_duration = max(0.1, new_duration)  # Min 0.1s

        if trim_from_start:
            # Start se trim — clip aage move hoga
            diff              = clip.duration - new_duration
            clip.start_time  += diff
            clip.trim_start  += diff
            clip.duration     = new_duration
        else:
            # End se trim
            diff              = clip.duration - new_duration
            clip.trim_end    += diff
            clip.duration     = new_duration

        self._update_duration()
        self._notify_change("clip_trimmed", {
            "track_id": track_id,
            "clip_id" : clip_id,
        })
        logger.debug(f"✂️  Trimmed clip to {new_duration:.2f}s")
        return True

    def split_clip(self, track_id: str, clip_id: str,
                   split_time: float) -> Optional[str]:
        """
        Clip ko given time pe do parts mein split karo.

        Returns:
            New (second) clip ka ID, ya None if failed
        """
        track = self.get_track(track_id)
        if not track:
            return None

        clip = track.get_clip(clip_id)
        if not clip or clip.locked:
            return None

        # Split time clip ke andar hai?
        if not clip.contains_time(split_time):
            logger.warning(f"Split time {split_time} not within clip")
            return None

        # Offset within clip
        offset = split_time - clip.start_time

        # Naya clip banao (second half)
        new_clip                  = copy.deepcopy(clip)
        new_clip.id               = generate_short_id()
        new_clip.name             = f"{clip.name} (2)"
        new_clip.start_time       = split_time
        new_clip.duration         = clip.duration - offset
        new_clip.trim_start       = clip.trim_start + offset

        # Original clip ki duration adjust karo
        clip.duration = offset
        clip.trim_end = clip.source_duration - (clip.trim_start + offset)

        # Naya clip add karo
        track.add_clip(new_clip)

        self._notify_change("clip_split", {
            "track_id"     : track_id,
            "original_id"  : clip_id,
            "new_id"       : new_clip.id,
        })
        logger.info(f"✂️  Split clip at {split_time:.2f}s")
        return new_clip.id

    def duplicate_clip(self, track_id: str, clip_id: str,
                       offset: float = 0.0) -> Optional[str]:
        """
        Clip duplicate karo.

        Args:
            offset: Naya clip original se kitna aage rahe (0 = right after)

        Returns:
            Naye clip ka ID
        """
        track = self.get_track(track_id)
        if not track:
            return None

        clip = track.get_clip(clip_id)
        if not clip:
            return None

        # Copy banao
        new_clip = copy.deepcopy(clip)
        new_clip.id   = generate_short_id()
        new_clip.name = f"{clip.name} (copy)"

        # Position offset
        if offset == 0.0:
            # Right after original
            new_clip.start_time = clip.end_time
        else:
            new_clip.start_time = clip.start_time + offset

        track.add_clip(new_clip)
        self._update_duration()

        logger.debug(f"📋 Duplicated clip: {new_clip.name}")
        return new_clip.id

    def get_clip(self, clip_id: str) -> Optional[Tuple[str, Clip]]:
        """
        Sab tracks mein clip dhundo.

        Returns:
            (track_id, clip) tuple ya None
        """
        for track in self.tracks:
            clip = track.get_clip(clip_id)
            if clip:
                return (track.id, clip)
        return None

    def get_clips_at_time(self, time: float) -> Dict[str, List[Clip]]:
        """Given time pe active clips per track"""
        result = {}
        for track in self.tracks:
            active = track.get_clips_at_time(time)
            if active:
                result[track.id] = active
        return result

    # ── RIPPLE EDIT ───────────────────────────────────────

    def _apply_ripple_to_track(self, track: Track, moved_clip: Clip, delta: float):
        """Same track ke baaki clips ko shift karo"""
        for c in track.clips:
            if c.id != moved_clip.id and c.start_time > moved_clip.start_time:
                c.start_time += delta

    def _apply_ripple_to_all(self, moved_clip: Clip, delta: float):
        """Sab tracks ke clips ko shift karo"""
        for track in self.tracks:
            self._apply_ripple_to_track(track, moved_clip, delta)

    def set_ripple_mode(self, mode: RippleMode):
        """Ripple edit mode set karo"""
        self.ripple_mode = mode
        logger.info(f"🌊 Ripple mode: {mode.value}")

    # ── MARKERS ───────────────────────────────────────────

    def add_marker(self, time: float, label: str = "Marker",
                   color: str = "#00D4FF",
                   is_chapter: bool = False) -> TimeMarker:
        """Marker add karo timeline pe"""
        marker = TimeMarker(
            time       = time,
            label      = label,
            color      = color,
            is_chapter = is_chapter,
        )
        self.markers.append(marker)
        self.markers.sort(key=lambda m: m.time)

        self._notify_change("marker_added", {"marker_id": marker.id})
        logger.debug(f"📌 Marker added: '{label}' @ {time:.2f}s")
        return marker

    def remove_marker(self, marker_id: str) -> bool:
        """Marker remove karo"""
        for i, m in enumerate(self.markers):
            if m.id == marker_id:
                del self.markers[i]
                self._notify_change("marker_removed", {"marker_id": marker_id})
                return True
        return False

    def get_marker(self, marker_id: str) -> Optional[TimeMarker]:
        for m in self.markers:
            if m.id == marker_id:
                return m
        return None

    def get_markers_in_range(self, start: float, end: float) -> List[TimeMarker]:
        """Time range ke andar ke markers"""
        return [m for m in self.markers if start <= m.time <= end]

    def get_chapters(self) -> List[TimeMarker]:
        """YouTube chapter markers"""
        return [m for m in self.markers if m.is_chapter]

    # ── PLAYBACK CONTROL ──────────────────────────────────

    def play(self):
        """▶️ Playback start karo"""
        self.playback_state = PlaybackState.PLAYING
        self._notify_playback("play")
        logger.debug("▶️  Playback started")

    def pause(self):
        """⏸️ Playback pause karo"""
        self.playback_state = PlaybackState.PAUSED
        self._notify_playback("pause")
        logger.debug("⏸️  Playback paused")

    def stop(self):
        """⏹️ Playback stop karo aur beginning pe jao"""
        self.playback_state = PlaybackState.STOPPED
        self.playhead_time  = 0.0
        self._notify_playback("stop")
        logger.debug("⏹️  Playback stopped")

    def seek(self, time: float):
        """Playhead ko given time pe move karo"""
        self.playhead_time = clamp(time, 0.0, self.duration)
        self._notify_playback("seek")

    def step_forward(self, frames: int = 1):
        """Ek frame aage jao"""
        frame_duration = 1.0 / self.fps
        self.seek(self.playhead_time + (frame_duration * frames))

    def step_backward(self, frames: int = 1):
        """Ek frame peeche jao"""
        frame_duration = 1.0 / self.fps
        self.seek(self.playhead_time - (frame_duration * frames))

    def go_to_next_marker(self):
        """Next marker pe jao"""
        for m in self.markers:
            if m.time > self.playhead_time:
                self.seek(m.time)
                return

    def go_to_previous_marker(self):
        """Previous marker pe jao"""
        prev = None
        for m in self.markers:
            if m.time < self.playhead_time:
                prev = m
            else:
                break
        if prev:
            self.seek(prev.time)

    def set_loop(self, start: float, end: float):
        """Loop range set karo"""
        self.loop_start   = start
        self.loop_end     = end
        self.loop_enabled = True
        logger.info(f"🔁 Loop set: {start:.2f}s → {end:.2f}s")

    def disable_loop(self):
        self.loop_enabled = False

    # ── SELECTION ─────────────────────────────────────────

    def select_clip(self, clip_id: str, add_to_selection: bool = False):
        """Clip select karo"""
        if not add_to_selection:
            self.selected_clip_ids.clear()
        if clip_id not in self.selected_clip_ids:
            self.selected_clip_ids.append(clip_id)

    def deselect_clip(self, clip_id: str):
        if clip_id in self.selected_clip_ids:
            self.selected_clip_ids.remove(clip_id)

    def clear_selection(self):
        self.selected_clip_ids.clear()
        self.selected_track_id = None

    # ── UNDO/REDO ─────────────────────────────────────────

    def undo(self) -> bool:
        return self.undo_redo.undo(self)

    def redo(self) -> bool:
        return self.undo_redo.redo(self)

    def can_undo(self) -> bool:
        return self.undo_redo.can_undo()

    def can_redo(self) -> bool:
        return self.undo_redo.can_redo()

    # ── UTILITIES ─────────────────────────────────────────

    def get_duration(self) -> float:
        """Timeline ki actual duration (last clip end)"""
        max_end = 0.0
        for track in self.tracks:
            for clip in track.clips:
                max_end = max(max_end, clip.end_time)
        return max_end

    def _update_duration(self):
        """Duration auto-update — clips add hone par"""
        actual = self.get_duration()
        # Extra padding rakho scrolling ke liye
        self.duration    = max(60.0, actual + 10.0)
        self.modified_at = get_timestamp()

    def get_frame_at_time(self, time: float) -> int:
        """Time se frame number nikalo"""
        return int(time * self.fps)

    def get_time_at_frame(self, frame: int) -> float:
        """Frame number se time nikalo"""
        return frame / self.fps

    def get_timecode(self, time: Optional[float] = None) -> str:
        """
        HH:MM:SS:FF timecode return karo.
        None = current playhead time.
        """
        if time is None:
            time = self.playhead_time
        return seconds_to_timecode(time)

    # ── SERIALIZATION ─────────────────────────────────────

    def to_dict(self) -> Dict:
        """Timeline ko dict mein convert karo (JSON save ke liye)"""
        return {
            "id"           : self.id,
            "name"         : self.name,
            "fps"          : self.fps,
            "duration"     : self.duration,
            "created_at"   : self.created_at,
            "modified_at"  : self.modified_at,
            "playhead_time": self.playhead_time,
            "tracks"       : [t.to_dict() for t in self.tracks],
            "markers"      : [m.to_dict() for m in self.markers],
        }

    def save_to_file(self, filepath: str) -> bool:
        """JSON file mein save karo"""
        try:
            ensure_dir(os.path.dirname(filepath))
            return write_json(filepath, self.to_dict())
        except Exception as e:
            logger.error(f"Timeline save failed: {e}")
            return False

    @classmethod
    def load_from_file(cls, filepath: str) -> Optional["Timeline"]:
        """JSON file se timeline load karo"""
        try:
            data = read_json(filepath)
            if not data:
                return None

            timeline              = cls(
                name = data.get("name", "Loaded Timeline"),
                fps  = data.get("fps", 30),
            )
            timeline.id           = data.get("id", timeline.id)
            timeline.duration     = data.get("duration", 60.0)
            timeline.created_at   = data.get("created_at", get_timestamp())
            timeline.modified_at  = data.get("modified_at", get_timestamp())
            timeline.playhead_time= data.get("playhead_time", 0.0)

            # Tracks load karo
            for track_data in data.get("tracks", []):
                timeline.tracks.append(Track.from_dict(track_data))
            timeline._sort_tracks()

            # Markers load karo
            for marker_data in data.get("markers", []):
                timeline.markers.append(TimeMarker.from_dict(marker_data))
            timeline.markers.sort(key=lambda m: m.time)

            logger.info(f"⏱️  Timeline loaded: {timeline.name}")
            return timeline

        except Exception as e:
            logger.error(f"Timeline load failed: {e}")
            return None

    # ── LISTENERS ─────────────────────────────────────────

    def add_change_listener(self, callback: Callable):
        """Timeline change ke liye listener"""
        if callback not in self._change_listeners:
            self._change_listeners.append(callback)

    def add_playback_listener(self, callback: Callable):
        """Playback events ke liye listener"""
        if callback not in self._playback_listeners:
            self._playback_listeners.append(callback)

    def _notify_change(self, event_type: str, data: Dict):
        for cb in self._change_listeners:
            try:
                cb(event_type, data)
            except Exception as e:
                logger.debug(f"Change listener error: {e}")

    def _notify_playback(self, event_type: str):
        for cb in self._playback_listeners:
            try:
                cb(event_type, {"time": self.playhead_time})
            except Exception as e:
                logger.debug(f"Playback listener error: {e}")

    # ── STATISTICS ────────────────────────────────────────

    def get_stats(self) -> Dict:
        """Timeline statistics"""
        total_clips = sum(len(t.clips) for t in self.tracks)

        return {
            "name"          : self.name,
            "fps"           : self.fps,
            "duration"      : self.get_duration(),
            "duration_str"  : format_duration(self.get_duration()),
            "total_tracks"  : len(self.tracks),
            "total_clips"   : total_clips,
            "total_markers" : len(self.markers),
            "chapters"      : len(self.get_chapters()),
            "playhead_time" : self.playhead_time,
            "timecode"      : self.get_timecode(),
            "state"         : self.playback_state.value,
            "can_undo"      : self.can_undo(),
            "can_redo"      : self.can_redo(),
            **self._stats,
        }


# ============================================================
# TEST FUNCTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")
    print_banner(
        "⏱️  Timeline Editor Test",
        "Multi-track timeline with clips, markers, undo/redo"
    )

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))

    # ============================================================
    # Test 1: Create Timeline
    # ============================================================
    print_section("Test 1: Create Timeline")

    timeline = Timeline(name="My Animation", fps=30)
    stats = timeline.get_stats()

    print(f"  Name     : {stats['name']}")
    print(f"  FPS      : {stats['fps']}")
    print(f"  Duration : {stats['duration_str']}")
    print(f"  Tracks   : {stats['total_tracks']}")

    # ============================================================
    # Test 2: Add Tracks
    # ============================================================
    print_section("Test 2: Add Multi-type Tracks")

    tracks_to_add = [
        ("Main Video",    TrackType.VIDEO),
        ("Camera",        TrackType.CAMERA),
        ("Dialogue",      TrackType.AUDIO),
        ("Background Music", TrackType.AUDIO),
        ("SFX",           TrackType.AUDIO),
        ("Subtitles",     TrackType.SUBTITLE),
        ("Effects",       TrackType.EFFECT),
    ]

    created_tracks = {}
    for name, ttype in tracks_to_add:
        track = timeline.add_track(name, ttype)
        created_tracks[name] = track

    print(f"\n  Total tracks: {len(timeline.tracks)}")
    for track in timeline.tracks:
        icon = {"video": "🎬", "audio": "🎵", "subtitle": "📝",
                "effect": "✨", "camera": "📹"}.get(track.track_type.value, "▪️")
        print(f"    {icon} {track.name} ({track.track_type.value})")

    # ============================================================
    # Test 3: Add Clips
    # ============================================================
    print_section("Test 3: Add Clips to Tracks")

    # Video clips
    video_track = created_tracks["Main Video"]
    intro_clip = Clip(
        name       = "Intro Scene",
        clip_type  = ClipType.SCENE_3D,
        start_time = 0.0,
        duration   = 5.0,
        color      = "#4A90E2",
    )
    main_clip = Clip(
        name       = "Main Action",
        clip_type  = ClipType.SCENE_3D,
        start_time = 5.0,
        duration   = 15.0,
        color      = "#E24A90",
    )
    outro_clip = Clip(
        name       = "Outro",
        clip_type  = ClipType.SCENE_3D,
        start_time = 20.0,
        duration   = 3.0,
        color      = "#90E24A",
    )
    for c in [intro_clip, main_clip, outro_clip]:
        timeline.add_clip(video_track.id, c)

    # Audio clips
    dialogue_track = created_tracks["Dialogue"]
    for i in range(3):
        clip = Clip(
            name       = f"Dialogue Line {i+1}",
            clip_type  = ClipType.AUDIO,
            start_time = i * 5.0,
            duration   = 4.0,
            volume     = 0.9,
        )
        timeline.add_clip(dialogue_track.id, clip)

    music_track = created_tracks["Background Music"]
    music_clip = Clip(
        name       = "Background Track",
        clip_type  = ClipType.AUDIO,
        start_time = 0.0,
        duration   = 23.0,
        volume     = 0.4,
        fade_in    = 1.0,
        fade_out   = 2.0,
    )
    timeline.add_clip(music_track.id, music_clip)

    # Subtitle clips
    sub_track = created_tracks["Subtitles"]
    for i in range(3):
        clip = Clip(
            name         = f"Subtitle {i+1}",
            clip_type    = ClipType.TEXT,
            start_time   = i * 5.0,
            duration     = 4.0,
            text_content = f"Line {i+1} of dialogue text",
        )
        timeline.add_clip(sub_track.id, clip)

    stats = timeline.get_stats()
    print(f"\n  Total clips added: {stats['total_clips']}")
    print(f"  Timeline duration: {stats['duration_str']}")

    # ============================================================
    # Test 4: Add Markers
    # ============================================================
    print_section("Test 4: Add Time Markers")

    markers_data = [
        (0.0,  "Intro Start",   "#00FF00", True),
        (5.0,  "Scene Change",  "#FFFF00", False),
        (15.0, "Climax",        "#FF0000", True),
        (20.0, "Outro Start",   "#0000FF", True),
        (23.0, "The End",       "#FF00FF", False),
    ]

    for marker_time, label, color, is_chapter in markers_data:
        timeline.add_marker(marker_time, label, color, is_chapter)

    print(f"\n  Total markers: {len(timeline.markers)}")
    print(f"  YouTube chapters: {len(timeline.get_chapters())}")
    for m in timeline.markers:
        chapter_marker = " 📖" if m.is_chapter else ""
        print(f"    {m.time:5.1f}s → {m.label}{chapter_marker}")

    # ============================================================
    # Test 5: Playback Control
    # ============================================================
    print_section("Test 5: Playback Control")

    print("  Current state: STOPPED")
    print(f"  Playhead    : {timeline.get_timecode()}")

    timeline.play()
    print(f"  After play(): {timeline.playback_state.value}")

    timeline.seek(10.0)
    print(f"  Seek to 10s : {timeline.get_timecode()}")

    timeline.step_forward(30)  # 30 frames = 1 sec @ 30fps
    print(f"  Step +30frm : {timeline.get_timecode()}")

    timeline.pause()
    print(f"  After pause : {timeline.playback_state.value}")

    timeline.go_to_next_marker()
    print(f"  Next marker : {timeline.get_timecode()}")

    timeline.go_to_previous_marker()
    print(f"  Prev marker : {timeline.get_timecode()}")

    timeline.stop()
    print(f"  After stop  : {timeline.playback_state.value}")

    # ============================================================
    # Test 6: Undo/Redo System
    # ============================================================
    print_section("Test 6: Undo/Redo System")

    # Ek naya clip add karo
    test_clip = Clip(name="Test Clip", start_time=25.0, duration=2.0)
    timeline.add_clip(video_track.id, test_clip)

    initial_count = sum(len(t.clips) for t in timeline.tracks)
    print(f"  Clips after add : {initial_count}")

    # Undo
    timeline.undo()
    after_undo = sum(len(t.clips) for t in timeline.tracks)
    print(f"  After undo      : {after_undo}")

    # Redo
    timeline.redo()
    after_redo = sum(len(t.clips) for t in timeline.tracks)
    print(f"  After redo      : {after_redo}")

    # Undo history
    print(f"\n  Can undo: {timeline.can_undo()}")
    print(f"  Can redo: {timeline.can_redo()}")

    # ============================================================
    # Test 7: Snapping
    # ============================================================
    print_section("Test 7: Snap-to-Grid")

    # Different snap modes test karo
    positions_to_test = [0.03, 4.98, 5.02, 14.9, 20.05]

    print(f"  Snap mode: {timeline.snap.snap_mode.value}")
    print(f"  Snap threshold: {timeline.snap.snap_threshold}s\n")

    for pos in positions_to_test:
        snapped, was_snapped = timeline.snap.snap(pos, timeline)
        marker = "🧲" if was_snapped else "  "
        print(f"    {marker} {pos:.3f}s → {snapped:.3f}s")

    # ============================================================
    # Test 8: Clip Operations — Trim, Split, Duplicate
    # ============================================================
    print_section("Test 8: Advanced Clip Operations")

    # Trim
    print("  Original main_clip duration: 15.0s")
    timeline.trim_clip(video_track.id, main_clip.id, new_duration=10.0)
    print(f"  After trim to 10s: {main_clip.duration}s")

    # Split
    print("\n  Splitting main_clip at 12.5s...")
    new_id = timeline.split_clip(video_track.id, main_clip.id, split_time=12.5)
    if new_id:
        print(f"  ✅ Split successful: new clip ID = {new_id[:8]}...")

    # Duplicate
    print("\n  Duplicating intro clip...")
    dup_id = timeline.duplicate_clip(video_track.id, intro_clip.id)
    if dup_id:
        print(f"  ✅ Duplicate created: ID = {dup_id[:8]}...")

    stats = timeline.get_stats()
    print(f"\n  Total clips now: {stats['total_clips']}")

    # ============================================================
    # Test 9: Query Clips at Time
    # ============================================================
    print_section("Test 9: Query Active Clips at Time")

    query_times = [2.0, 7.0, 15.0, 22.0]

    for t in query_times:
        active = timeline.get_clips_at_time(t)
        print(f"\n  At t={t}s ({seconds_to_timecode(t)}):")
        if active:
            for track_id, clips in active.items():
                track = timeline.get_track(track_id)
                for clip in clips:
                    print(f"    ▶️  [{track.name}] {clip.name}")
        else:
            print(f"    (no active clips)")

    # ============================================================
    # Test 10: Save & Load Timeline
    # ============================================================
    print_section("Test 10: Save & Load Timeline")

    output_dir = os.path.join(base_dir, "temp", "timeline_tests")
    ensure_dir(output_dir)
    save_path = os.path.join(output_dir, "test_timeline.json")

    # Save
    success = timeline.save_to_file(save_path)
    if success:
        from src.utils import get_file_size, format_bytes
        size = format_bytes(get_file_size(save_path))
        print(f"  ✅ Saved: {os.path.basename(save_path)} ({size})")

        # Load
        loaded = Timeline.load_from_file(save_path)
        if loaded:
            loaded_stats = loaded.get_stats()
            print(f"\n  ✅ Loaded successfully:")
            print(f"     Name    : {loaded_stats['name']}")
            print(f"     FPS     : {loaded_stats['fps']}")
            print(f"     Duration: {loaded_stats['duration_str']}")
            print(f"     Tracks  : {loaded_stats['total_tracks']}")
            print(f"     Clips   : {loaded_stats['total_clips']}")
            print(f"     Markers : {loaded_stats['total_markers']}")

    # ============================================================
    # Test 11: Ripple Edit Mode
    # ============================================================
    print_section("Test 11: Ripple Edit Mode")

    # Fresh timeline banao ripple test ke liye
    ripple_tl = Timeline(name="Ripple Test", fps=30)
    ripple_track = ripple_tl.add_track("Video", TrackType.VIDEO)

    # 3 sequential clips add karo
    for i in range(3):
        c = Clip(name=f"Clip {i+1}", start_time=i*5.0, duration=5.0)
        ripple_tl.add_clip(ripple_track.id, c)

    print("  Original positions:")
    for c in ripple_track.clips:
        print(f"    {c.name}: {c.start_time}s → {c.end_time}s")

    # Ripple mode enable
    ripple_tl.set_ripple_mode(RippleMode.TRACK)

    # First clip ko 10s pe move karo — baaki bhi shift honge
    first_clip_id = ripple_track.clips[0].id
    ripple_tl.move_clip(ripple_track.id, first_clip_id, 10.0, use_snap=False)

    print("\n  After ripple move (first clip → 10s):")
    for c in ripple_track.clips:
        print(f"    {c.name}: {c.start_time}s → {c.end_time}s")

    # ============================================================
    # Test 12: Final Statistics
    # ============================================================
    print_section("Test 12: Final Statistics")

    stats = timeline.get_stats()
    print(f"  Timeline    : {stats['name']}")
    print(f"  Duration    : {stats['duration_str']}")
    print(f"  Tracks      : {stats['total_tracks']}")
    print(f"  Clips       : {stats['total_clips']}")
    print(f"  Markers     : {stats['total_markers']}")
    print(f"  Chapters    : {stats['chapters']}")
    print(f"\n  Editing:")
    print(f"    Clips added   : {stats['clips_added']}")
    print(f"    Clips removed : {stats['clips_removed']}")
    print(f"    Clips moved   : {stats['clips_moved']}")

    # ============================================================
    # Output Info
    # ============================================================
    print_section("Output Files")
    print(f"  📁 Timeline data saved in:")
    print(f"     {output_dir}")

    print_banner(
        "✅ Timeline Editor Ready!",
        f"{stats['total_tracks']} tracks | {stats['total_clips']} clips | "
        f"{stats['total_markers']} markers"
    )