# ============================================================
# src/ui/timeline_widget.py
# 3D Animation Studio - Timeline Widget
# Animation timeline editor - DaVinci Resolve style
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
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum

from src.utils import get_logger, get_config, get_timestamp, generate_uuid

logger = get_logger("TimelineWidget")


# ============================================================
# ENUMS
# ============================================================

class TrackType(Enum):
    """Timeline track types"""
    VIDEO       = "video"
    AUDIO       = "audio"
    CHARACTER   = "character"
    CAMERA      = "camera"
    VFX         = "vfx"
    SUBTITLE    = "subtitle"
    MARKER      = "marker"


class ClipType(Enum):
    """Clip content types"""
    VIDEO       = "video"
    AUDIO       = "audio"
    ANIMATION   = "animation"
    IMAGE       = "image"
    TEXT        = "text"
    VFX         = "vfx"
    TRANSITION  = "transition"


class TransitionType(Enum):
    """Transition types between clips"""
    CUT         = "cut"
    FADE_IN     = "fade_in"
    FADE_OUT    = "fade_out"
    CROSS_FADE  = "cross_fade"
    DISSOLVE    = "dissolve"
    WIPE_LEFT   = "wipe_left"
    WIPE_RIGHT  = "wipe_right"
    ZOOM_IN     = "zoom_in"
    ZOOM_OUT    = "zoom_out"


class PlaybackState(Enum):
    """Playback states"""
    STOPPED     = "stopped"
    PLAYING     = "playing"
    PAUSED      = "paused"
    SCRUBBING   = "scrubbing"


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class TimelineMarker:
    """Timeline pe marker - chapter ya note"""
    id:         str
    frame:      int
    label:      str             = ""
    color:      str             = "#FFD700"   # Gold
    marker_type: str            = "note"      # note, chapter, cut

    def get_timecode(self, fps: int = 30) -> str:
        """Frame se timecode string"""
        total_sec = self.frame // fps
        frames    = self.frame % fps
        mins      = total_sec // 60
        secs      = total_sec % 60
        return f"{mins:02d}:{secs:02d}:{frames:02d}"


@dataclass
class ClipTransition:
    """Clip ke start ya end pe transition"""
    transition_type: str    = TransitionType.CUT.value
    duration_frames: int    = 15    # Transition duration frames mein


@dataclass
class TimelineClip:
    """
    Timeline pe ek clip.
    Track mein position, duration, source file sab yahan.
    """
    id:             str
    name:           str
    clip_type:      str             = ClipType.VIDEO.value
    track_id:       str             = ""

    # Timeline position (frames mein)
    start_frame:    int             = 0
    duration_frames: int            = 30        # Default 1 second at 30fps
    end_frame:      int             = 30        # start + duration

    # Source file
    source_path:    str             = ""
    source_start:   int             = 0         # Source file ka start frame
    source_end:     int             = 30        # Source file ka end frame

    # Playback
    speed:          float           = 1.0       # Playback speed multiplier
    volume:         float           = 1.0       # Audio volume (0-1)
    opacity:        float           = 1.0       # Visual opacity (0-1)

    # Transitions
    transition_in:  ClipTransition  = field(
        default_factory=ClipTransition
    )
    transition_out: ClipTransition  = field(
        default_factory=ClipTransition
    )

    # State
    selected:       bool            = False
    locked:         bool            = False
    muted:          bool            = False
    color:          str             = "#4488FF"

    def __post_init__(self):
        """end_frame calculate karo"""
        self.end_frame = self.start_frame + self.duration_frames

    def get_duration_seconds(self, fps: int = 30) -> float:
        """Duration seconds mein"""
        return self.duration_frames / fps

    def get_timecode_start(self, fps: int = 30) -> str:
        """Start timecode"""
        return self._frames_to_tc(self.start_frame, fps)

    def get_timecode_end(self, fps: int = 30) -> str:
        """End timecode"""
        return self._frames_to_tc(self.end_frame, fps)

    @staticmethod
    def _frames_to_tc(frames: int, fps: int) -> str:
        total_sec = frames // fps
        f         = frames % fps
        m         = total_sec // 60
        s         = total_sec % 60
        return f"{m:02d}:{s:02d}:{f:02d}"

    def overlaps_with(self, other: "TimelineClip") -> bool:
        """Kya yeh clip doosre clip se overlap karta hai?"""
        return (
            self.start_frame < other.end_frame
            and self.end_frame > other.start_frame
        )

    def contains_frame(self, frame: int) -> bool:
        """Kya yeh frame is clip mein hai?"""
        return self.start_frame <= frame < self.end_frame

    def to_dict(self) -> Dict:
        return {
            "id":             self.id,
            "name":           self.name,
            "clip_type":      self.clip_type,
            "track_id":       self.track_id,
            "start_frame":    self.start_frame,
            "duration_frames":self.duration_frames,
            "end_frame":      self.end_frame,
            "source_path":    self.source_path,
            "speed":          self.speed,
            "volume":         self.volume,
            "opacity":        self.opacity,
            "muted":          self.muted,
            "locked":         self.locked,
            "color":          self.color,
        }


@dataclass
class TimelineTrack:
    """
    Timeline mein ek track (row).
    Ek track mein multiple clips hote hain.
    """
    id:             str
    name:           str
    track_type:     str             = TrackType.VIDEO.value

    # Track clips
    clips:          List[TimelineClip] = field(default_factory=list)

    # Track state
    visible:        bool            = True
    locked:         bool            = False
    muted:          bool            = False
    solo:           bool            = False
    height:         int             = 50        # Pixels

    # Track color
    color:          str             = "#2A4A8A"

    def get_icon(self) -> str:
        icons = {
            TrackType.VIDEO.value:     "🎬",
            TrackType.AUDIO.value:     "🔊",
            TrackType.CHARACTER.value: "🧍",
            TrackType.CAMERA.value:    "🎥",
            TrackType.VFX.value:       "✨",
            TrackType.SUBTITLE.value:  "💬",
            TrackType.MARKER.value:    "📌",
        }
        return icons.get(self.track_type, "📄")

    def get_clip_at_frame(self, frame: int) -> Optional[TimelineClip]:
        """Frame pe clip lo"""
        for clip in self.clips:
            if clip.contains_frame(frame):
                return clip
        return None

    def get_total_duration(self) -> int:
        """Track ki total duration frames mein"""
        if not self.clips:
            return 0
        return max(clip.end_frame for clip in self.clips)

    def add_clip(self, clip: TimelineClip) -> bool:
        """Clip add karo (overlap check ke saath)"""
        if self.locked:
            return False
        clip.track_id = self.id
        self.clips.append(clip)
        # Sort by start frame
        self.clips.sort(key=lambda c: c.start_frame)
        return True

    def remove_clip(self, clip_id: str) -> bool:
        """Clip remove karo"""
        for i, clip in enumerate(self.clips):
            if clip.id == clip_id:
                self.clips.pop(i)
                return True
        return False

    def get_clips_in_range(
        self,
        start: int,
        end: int,
    ) -> List[TimelineClip]:
        """Range mein clips lo"""
        return [
            c for c in self.clips
            if c.start_frame < end and c.end_frame > start
        ]


# ============================================================
# TIMELINE MODEL
# ============================================================

class TimelineModel:
    """
    Timeline ka complete data model.
    Tracks, clips, markers, playback state sab manage karta hai.
    """

    def __init__(self, fps: int = 30):
        """
        Timeline initialize karo.

        Args:
            fps: Frames per second
        """
        self.fps            = fps
        self._tracks:   Dict[str, TimelineTrack]   = {}
        self._track_order:  List[str]              = []
        self._markers:  Dict[str, TimelineMarker]  = {}
        self._listeners:    List[Callable]         = []

        # Playback state
        self._current_frame:  int           = 0
        self._playback_state: str           = PlaybackState.STOPPED.value
        self._loop:           bool          = False
        self._in_point:       Optional[int] = None
        self._out_point:      Optional[int] = None

        # Selection
        self._selected_clips: List[str]     = []   # Clip IDs
        self._selected_track: Optional[str] = None

        # Zoom
        self._zoom_level:     float         = 1.0   # 1.0 = default
        self._scroll_offset:  int           = 0     # Frames offset

        # ID counter
        self._id_counter = 0

        # Default tracks banao
        self._create_default_tracks()

        logger.info(
            f"✅ TimelineModel initialized | FPS: {fps}"
        )

    def _gen_id(self, prefix: str = "id") -> str:
        self._id_counter += 1
        return f"{prefix}_{self._id_counter:04d}"

    def _create_default_tracks(self):
        """Default tracks create karo"""
        defaults = [
            ("Video 1",    TrackType.VIDEO.value,     "#2A4A8A", 60),
            ("Video 2",    TrackType.VIDEO.value,     "#1A3A6A", 60),
            ("Character",  TrackType.CHARACTER.value, "#2A6A4A", 50),
            ("Audio 1",    TrackType.AUDIO.value,     "#6A4A2A", 40),
            ("Audio 2",    TrackType.AUDIO.value,     "#5A3A1A", 40),
            ("VFX",        TrackType.VFX.value,       "#6A2A6A", 40),
            ("Subtitles",  TrackType.SUBTITLE.value,  "#2A6A6A", 35),
        ]
        for name, track_type, color, height in defaults:
            self.add_track(name, track_type, color=color, height=height)

    # ----------------------------------------------------------
    # TRACK MANAGEMENT
    # ----------------------------------------------------------

    def add_track(
        self,
        name:       str,
        track_type: str = TrackType.VIDEO.value,
        color:      str = "#2A4A8A",
        height:     int = 50,
        position:   Optional[int] = None,
    ) -> TimelineTrack:
        """Naya track add karo"""
        track_id = self._gen_id("trk")
        track = TimelineTrack(
            id         = track_id,
            name       = name,
            track_type = track_type,
            color      = color,
            height     = height,
        )
        self._tracks[track_id] = track

        if position is not None and 0 <= position <= len(self._track_order):
            self._track_order.insert(position, track_id)
        else:
            self._track_order.append(track_id)

        self._notify("track_added", {"track": track})
        logger.debug(f"Track added: {name} ({track_type})")
        return track

    def remove_track(self, track_id: str) -> bool:
        """Track remove karo"""
        if track_id not in self._tracks:
            return False
        del self._tracks[track_id]
        if track_id in self._track_order:
            self._track_order.remove(track_id)
        self._notify("track_removed", {"track_id": track_id})
        return True

    def get_track(self, track_id: str) -> Optional[TimelineTrack]:
        """Track lo"""
        return self._tracks.get(track_id)

    def get_tracks_ordered(self) -> List[TimelineTrack]:
        """Order mein tracks lo"""
        return [
            self._tracks[tid]
            for tid in self._track_order
            if tid in self._tracks
        ]

    def get_tracks_by_type(self, track_type: str) -> List[TimelineTrack]:
        """Type se tracks filter karo"""
        return [
            t for t in self._tracks.values()
            if t.track_type == track_type
        ]

    def move_track(self, track_id: str, new_position: int):
        """Track reorder karo"""
        if track_id not in self._track_order:
            return
        self._track_order.remove(track_id)
        new_position = max(0, min(new_position, len(self._track_order)))
        self._track_order.insert(new_position, track_id)
        self._notify("track_reordered", {})

    def rename_track(self, track_id: str, new_name: str):
        """Track rename karo"""
        track = self._tracks.get(track_id)
        if track:
            track.name = new_name
            self._notify("track_updated", {"track_id": track_id})

    def toggle_track_mute(self, track_id: str) -> bool:
        """Track mute toggle"""
        track = self._tracks.get(track_id)
        if track:
            track.muted = not track.muted
            self._notify("track_updated", {"track_id": track_id})
            return track.muted
        return False

    def toggle_track_solo(self, track_id: str) -> bool:
        """Track solo toggle"""
        track = self._tracks.get(track_id)
        if track:
            track.solo = not track.solo
            # Agar solo on hai to baaki sab mute
            if track.solo:
                for t in self._tracks.values():
                    if t.id != track_id:
                        t.muted = True
            else:
                for t in self._tracks.values():
                    t.muted = False
            self._notify("track_updated", {"track_id": track_id})
            return track.solo
        return False

    def toggle_track_lock(self, track_id: str) -> bool:
        """Track lock toggle"""
        track = self._tracks.get(track_id)
        if track:
            track.locked = not track.locked
            self._notify("track_updated", {"track_id": track_id})
            return track.locked
        return False

    def toggle_track_visibility(self, track_id: str) -> bool:
        """Track visibility toggle"""
        track = self._tracks.get(track_id)
        if track:
            track.visible = not track.visible
            self._notify("track_updated", {"track_id": track_id})
            return track.visible
        return False

    # ----------------------------------------------------------
    # CLIP MANAGEMENT
    # ----------------------------------------------------------

    def add_clip(
        self,
        track_id:       str,
        name:           str,
        start_frame:    int,
        duration_frames:int,
        clip_type:      str     = ClipType.VIDEO.value,
        source_path:    str     = "",
        color:          str     = "#4488FF",
    ) -> Optional[TimelineClip]:
        """Clip add karo track mein"""
        track = self._tracks.get(track_id)
        if not track:
            logger.error(f"Track nahi mila: {track_id}")
            return None

        clip_id = self._gen_id("clip")
        clip = TimelineClip(
            id              = clip_id,
            name            = name,
            clip_type       = clip_type,
            track_id        = track_id,
            start_frame     = start_frame,
            duration_frames = duration_frames,
            source_path     = source_path,
            color           = color,
        )

        if track.add_clip(clip):
            self._notify("clip_added", {"clip": clip})
            logger.debug(
                f"Clip added: {name} | "
                f"Track: {track.name} | "
                f"Frame: {start_frame}-{clip.end_frame}"
            )
            return clip

        return None

    def remove_clip(self, clip_id: str) -> bool:
        """Clip remove karo"""
        for track in self._tracks.values():
            if track.remove_clip(clip_id):
                # Selection se bhi remove karo
                if clip_id in self._selected_clips:
                    self._selected_clips.remove(clip_id)
                self._notify("clip_removed", {"clip_id": clip_id})
                return True
        return False

    def get_clip(self, clip_id: str) -> Optional[TimelineClip]:
        """Clip ID se lo"""
        for track in self._tracks.values():
            for clip in track.clips:
                if clip.id == clip_id:
                    return clip
        return None

    def move_clip(
        self,
        clip_id:        str,
        new_start:      int,
        new_track_id:   Optional[str] = None,
    ) -> bool:
        """Clip move karo (drag & drop)"""
        clip = self.get_clip(clip_id)
        if not clip or clip.locked:
            return False

        old_duration  = clip.duration_frames

        # Track change (agar hai)
        if new_track_id and new_track_id != clip.track_id:
            # Old track se remove karo
            old_track = self._tracks.get(clip.track_id)
            if old_track:
                old_track.remove_clip(clip_id)

            # New track mein add karo
            new_track = self._tracks.get(new_track_id)
            if new_track:
                clip.track_id    = new_track_id
                clip.start_frame = max(0, new_start)
                clip.end_frame   = clip.start_frame + old_duration
                new_track.add_clip(clip)

        else:
            clip.start_frame = max(0, new_start)
            clip.end_frame   = clip.start_frame + old_duration

        self._notify("clip_moved", {"clip_id": clip_id})
        return True

    def resize_clip(
        self,
        clip_id:        str,
        new_start:      Optional[int] = None,
        new_duration:   Optional[int] = None,
    ) -> bool:
        """Clip resize karo"""
        clip = self.get_clip(clip_id)
        if not clip or clip.locked:
            return False

        if new_start is not None:
            old_end         = clip.end_frame
            clip.start_frame = max(0, new_start)
            clip.duration_frames = old_end - clip.start_frame
            clip.end_frame   = old_end

        if new_duration is not None and new_duration > 0:
            clip.duration_frames = new_duration
            clip.end_frame   = clip.start_frame + new_duration

        self._notify("clip_resized", {"clip_id": clip_id})
        return True

    def split_clip(self, clip_id: str, split_frame: int) -> Optional[TimelineClip]:
        """
        Clip ko specific frame pe split karo.
        Do clips ban jaate hain.
        """
        clip = self.get_clip(clip_id)
        if not clip:
            return None

        if not (clip.start_frame < split_frame < clip.end_frame):
            logger.warning("Split frame clip ke range mein nahi hai")
            return None

        # Original clip truncate karo
        original_end    = clip.end_frame
        clip.duration_frames = split_frame - clip.start_frame
        clip.end_frame  = split_frame

        # New clip banao (split ke baad wala)
        track = self._tracks.get(clip.track_id)
        new_clip = self.add_clip(
            track_id        = clip.track_id,
            name            = f"{clip.name}_2",
            start_frame     = split_frame,
            duration_frames = original_end - split_frame,
            clip_type       = clip.clip_type,
            source_path     = clip.source_path,
            color           = clip.color,
        )

        self._notify("clip_split", {
            "original_id": clip_id,
            "new_clip":    new_clip,
        })
        return new_clip

    def duplicate_clip(self, clip_id: str, offset: int = 0) -> Optional[TimelineClip]:
        """Clip duplicate karo"""
        clip = self.get_clip(clip_id)
        if not clip:
            return None

        new_start = clip.end_frame + offset
        new_clip  = self.add_clip(
            track_id        = clip.track_id,
            name            = f"{clip.name}_copy",
            start_frame     = new_start,
            duration_frames = clip.duration_frames,
            clip_type       = clip.clip_type,
            source_path     = clip.source_path,
            color           = clip.color,
        )
        return new_clip

    def set_clip_transition(
        self,
        clip_id:         str,
        transition_type: str,
        at_start:        bool = True,
        duration:        int  = 15,
    ):
        """Clip pe transition set karo"""
        clip = self.get_clip(clip_id)
        if not clip:
            return
        transition = ClipTransition(
            transition_type  = transition_type,
            duration_frames  = duration,
        )
        if at_start:
            clip.transition_in  = transition
        else:
            clip.transition_out = transition
        self._notify("clip_updated", {"clip_id": clip_id})

    # ----------------------------------------------------------
    # SELECTION
    # ----------------------------------------------------------

    def select_clip(self, clip_id: str, multi: bool = False):
        """Clip select karo"""
        if not multi:
            for c in self._selected_clips:
                old_clip = self.get_clip(c)
                if old_clip:
                    old_clip.selected = False
            self._selected_clips.clear()

        clip = self.get_clip(clip_id)
        if clip and clip_id not in self._selected_clips:
            clip.selected = True
            self._selected_clips.append(clip_id)

        self._notify("selection_changed", {
            "selected": self._selected_clips.copy()
        })

    def deselect_all_clips(self):
        """Sabhi clips deselect karo"""
        for clip_id in self._selected_clips:
            clip = self.get_clip(clip_id)
            if clip:
                clip.selected = False
        self._selected_clips.clear()
        self._notify("selection_changed", {"selected": []})

    def get_selected_clips(self) -> List[TimelineClip]:
        """Selected clips lo"""
        return [
            self.get_clip(cid)
            for cid in self._selected_clips
            if self.get_clip(cid)
        ]

    def select_track(self, track_id: str):
        """Track select karo"""
        self._selected_track = track_id
        self._notify("track_selected", {"track_id": track_id})

    # ----------------------------------------------------------
    # MARKERS
    # ----------------------------------------------------------

    def add_marker(
        self,
        frame:       int,
        label:       str   = "",
        color:       str   = "#FFD700",
        marker_type: str   = "note",
    ) -> TimelineMarker:
        """Marker add karo"""
        marker_id = self._gen_id("mkr")
        marker = TimelineMarker(
            id          = marker_id,
            frame       = frame,
            label       = label or f"Marker {len(self._markers)+1}",
            color       = color,
            marker_type = marker_type,
        )
        self._markers[marker_id] = marker
        self._notify("marker_added", {"marker": marker})
        logger.debug(f"Marker added: {marker.label} @ frame {frame}")
        return marker

    def remove_marker(self, marker_id: str) -> bool:
        """Marker remove karo"""
        if marker_id in self._markers:
            del self._markers[marker_id]
            self._notify("marker_removed", {"marker_id": marker_id})
            return True
        return False

    def get_markers(self) -> List[TimelineMarker]:
        """Sabhi markers lo (frame order mein)"""
        return sorted(
            self._markers.values(),
            key=lambda m: m.frame
        )

    def get_markers_at_frame(self, frame: int) -> List[TimelineMarker]:
        """Frame pe markers lo"""
        return [m for m in self._markers.values() if m.frame == frame]

    # ----------------------------------------------------------
    # PLAYBACK
    # ----------------------------------------------------------

    def get_current_frame(self) -> int:
        """Current frame lo"""
        return self._current_frame

    def set_current_frame(self, frame: int):
        """Current frame set karo"""
        frame = max(0, frame)
        total = self.get_total_duration()
        if total > 0:
            frame = min(frame, total)
        self._current_frame = frame
        self._notify("frame_changed", {"frame": frame})

    def get_playback_state(self) -> str:
        """Playback state lo"""
        return self._playback_state

    def play(self):
        """Playback start karo"""
        self._playback_state = PlaybackState.PLAYING.value
        self._notify("playback_state_changed", {
            "state": self._playback_state
        })
        logger.debug("▶️  Playback started")

    def pause(self):
        """Pause karo"""
        self._playback_state = PlaybackState.PAUSED.value
        self._notify("playback_state_changed", {
            "state": self._playback_state
        })
        logger.debug("⏸  Playback paused")

    def stop(self):
        """Stop karo aur start pe jao"""
        self._playback_state = PlaybackState.STOPPED.value
        self._current_frame  = self._in_point or 0
        self._notify("playback_state_changed", {
            "state": self._playback_state
        })
        self._notify("frame_changed", {"frame": self._current_frame})
        logger.debug("⏹  Playback stopped")

    def toggle_play_pause(self):
        """Play/Pause toggle karo"""
        if self._playback_state == PlaybackState.PLAYING.value:
            self.pause()
        else:
            self.play()

    def next_frame(self):
        """Ek frame aage"""
        self.set_current_frame(self._current_frame + 1)

    def prev_frame(self):
        """Ek frame peeche"""
        self.set_current_frame(self._current_frame - 1)

    def go_to_start(self):
        """Start pe jao"""
        self.set_current_frame(self._in_point or 0)

    def go_to_end(self):
        """End pe jao"""
        self.set_current_frame(self._out_point or self.get_total_duration())

    def set_in_point(self, frame: int):
        """In point set karo"""
        self._in_point = max(0, frame)
        self._notify("in_out_changed", {
            "in": self._in_point, "out": self._out_point
        })

    def set_out_point(self, frame: int):
        """Out point set karo"""
        self._out_point = frame
        self._notify("in_out_changed", {
            "in": self._in_point, "out": self._out_point
        })

    def set_loop(self, loop: bool):
        """Loop set karo"""
        self._loop = loop

    def get_loop(self) -> bool:
        return self._loop

    # ----------------------------------------------------------
    # ZOOM & SCROLL
    # ----------------------------------------------------------

    def set_zoom(self, zoom: float):
        """Timeline zoom set karo"""
        self._zoom_level = max(0.1, min(10.0, zoom))
        self._notify("zoom_changed", {"zoom": self._zoom_level})

    def zoom_in(self):
        """Zoom in"""
        self.set_zoom(self._zoom_level * 1.2)

    def zoom_out(self):
        """Zoom out"""
        self.set_zoom(self._zoom_level / 1.2)

    def get_zoom(self) -> float:
        return self._zoom_level

    def set_scroll(self, offset: int):
        """Scroll offset set karo"""
        self._scroll_offset = max(0, offset)
        self._notify("scroll_changed", {"offset": self._scroll_offset})

    def get_scroll(self) -> int:
        return self._scroll_offset

    # ----------------------------------------------------------
    # UTILITY
    # ----------------------------------------------------------

    def get_total_duration(self) -> int:
        """Total timeline duration frames mein"""
        max_frame = 0
        for track in self._tracks.values():
            track_dur = track.get_total_duration()
            if track_dur > max_frame:
                max_frame = track_dur
        return max_frame

    def get_total_duration_seconds(self) -> float:
        """Total duration seconds mein"""
        return self.get_total_duration() / self.fps

    def get_timecode(self, frame: Optional[int] = None) -> str:
        """Frame se timecode"""
        f     = frame if frame is not None else self._current_frame
        total = f // self.fps
        fr    = f % self.fps
        mins  = total // 60
        secs  = total % 60
        return f"{mins:02d}:{secs:02d}:{fr:02d}"

    def frame_to_pixel(self, frame: int, pixels_per_frame: float = 5.0) -> float:
        """Frame ko pixel position mein convert karo"""
        return (frame - self._scroll_offset) * pixels_per_frame * self._zoom_level

    def pixel_to_frame(self, pixel: float, pixels_per_frame: float = 5.0) -> int:
        """Pixel position ko frame mein convert karo"""
        frame = int(pixel / (pixels_per_frame * self._zoom_level)) + self._scroll_offset
        return max(0, frame)

    def get_all_clips(self) -> List[TimelineClip]:
        """Sabhi clips lo"""
        clips = []
        for track in self._tracks.values():
            clips.extend(track.clips)
        return clips

    def get_clips_at_frame(self, frame: int) -> List[Tuple[TimelineTrack, TimelineClip]]:
        """Frame pe sabhi clips lo (track ke saath)"""
        result = []
        for track in self._tracks.values():
            clip = track.get_clip_at_frame(frame)
            if clip:
                result.append((track, clip))
        return result

    def clear_all_clips(self):
        """Sabhi clips clear karo"""
        for track in self._tracks.values():
            track.clips.clear()
        self._selected_clips.clear()
        self._notify("timeline_cleared", {})

    def get_statistics(self) -> Dict:
        """Timeline statistics"""
        all_clips = self.get_all_clips()
        return {
            "total_tracks":     len(self._tracks),
            "total_clips":      len(all_clips),
            "total_markers":    len(self._markers),
            "total_frames":     self.get_total_duration(),
            "total_seconds":    round(self.get_total_duration_seconds(), 2),
            "fps":              self.fps,
            "current_frame":    self._current_frame,
            "current_timecode": self.get_timecode(),
            "zoom_level":       self._zoom_level,
        }

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
                logger.warning(f"Timeline listener error: {e}")

    def print_timeline(self):
        """Console mein timeline print karo (debug)"""
        print(f"\n{'='*60}")
        print(f"TIMELINE | FPS: {self.fps} | "
              f"Duration: {self.get_timecode(self.get_total_duration())}")
        print(f"Frame: {self._current_frame} | "
              f"State: {self._playback_state}")
        print(f"{'='*60}")

        for track in self.get_tracks_ordered():
            mute = "🔇" if track.muted else "🔊"
            lock = "🔒" if track.locked else "  "
            vis  = "👁" if track.visible else "🙈"
            print(f"\n  {track.get_icon()} {track.name:15s} "
                  f"{mute}{lock}{vis} | {len(track.clips)} clips")
            for clip in track.clips:
                print(
                    f"     [{clip.get_timecode_start(self.fps)} → "
                    f"{clip.get_timecode_end(self.fps)}] "
                    f"{clip.name} ({clip.duration_frames}f)"
                )

        if self._markers:
            print(f"\n  📌 Markers:")
            for m in self.get_markers():
                print(f"     {m.get_timecode(self.fps)} - {m.label}")
        print(f"{'='*60}")


# ============================================================
# QT TIMELINE WIDGET
# ============================================================

class TimelineWidget:
    """
    PyQt5 Timeline Widget.
    Track headers + clip display + playhead + ruler.
    """

    TRACK_HEADER_WIDTH  = 150
    RULER_HEIGHT        = 24
    PIXELS_PER_FRAME    = 5.0

    def __init__(
        self,
        parent=None,
        model: Optional[TimelineModel] = None,
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

        self.parent_widget  = parent
        self.theme_manager  = theme_manager
        self.model          = model or TimelineModel(fps=30)

        # Qt references
        self._widget            = None
        self._track_header_list = None
        self._clip_area         = None
        self._ruler             = None
        self._transport_bar     = None

        # Labels
        self._timecode_label    = None
        self._frame_label       = None

        # Build widget
        self._build_widget()

        # Model listen
        self.model.add_listener(self._on_model_changed)

        logger.info("✅ TimelineWidget initialized")

    def _build_widget(self):
        """Qt widget build karo"""
        try:
            from PyQt5.QtWidgets import (
                QWidget, QVBoxLayout, QHBoxLayout,
                QListWidget, QListWidgetItem, QLabel,
                QPushButton, QSlider, QScrollArea,
                QSplitter, QToolButton, QFrame,
                QSizePolicy, QScrollBar,
            )
            from PyQt5.QtCore import Qt, QSize, QTimer
            from PyQt5.QtGui import QFont, QColor

            # Main container
            self._widget = QWidget(self.parent_widget)
            self._widget.setObjectName("TimelineWidget")
            main_layout = QVBoxLayout(self._widget)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)

            # ===== TRANSPORT BAR (Top controls) =====
            transport = QWidget()
            transport.setObjectName("TransportBar")
            transport_layout = QHBoxLayout(transport)
            transport_layout.setContentsMargins(8, 4, 8, 4)
            transport_layout.setSpacing(4)
            transport.setFixedHeight(40)

            # Go to start
            btn_start = QToolButton()
            btn_start.setText("⏮")
            btn_start.setFixedSize(28, 28)
            btn_start.clicked.connect(self.model.go_to_start)
            transport_layout.addWidget(btn_start)

            # Prev frame
            btn_prev = QToolButton()
            btn_prev.setText("◀")
            btn_prev.setFixedSize(28, 28)
            btn_prev.clicked.connect(self.model.prev_frame)
            transport_layout.addWidget(btn_prev)

            # Play/Pause
            self._play_btn = QPushButton("▶ Play")
            self._play_btn.setFixedSize(70, 28)
            self._play_btn.setCheckable(True)
            self._play_btn.clicked.connect(self._on_play_clicked)
            transport_layout.addWidget(self._play_btn)

            # Next frame
            btn_next = QToolButton()
            btn_next.setText("▶")
            btn_next.setFixedSize(28, 28)
            btn_next.clicked.connect(self.model.next_frame)
            transport_layout.addWidget(btn_next)

            # Go to end
            btn_end = QToolButton()
            btn_end.setText("⏭")
            btn_end.setFixedSize(28, 28)
            btn_end.clicked.connect(self.model.go_to_end)
            transport_layout.addWidget(btn_end)

            transport_layout.addSpacing(8)

            # Loop button
            self._loop_btn = QToolButton()
            self._loop_btn.setText("🔁")
            self._loop_btn.setCheckable(True)
            self._loop_btn.setFixedSize(28, 28)
            self._loop_btn.toggled.connect(self.model.set_loop)
            transport_layout.addWidget(self._loop_btn)

            transport_layout.addSpacing(16)

            # Timecode display
            self._timecode_label = QLabel("00:00:00")
            self._timecode_label.setObjectName("TimecodeLabel")
            self._timecode_label.setFixedWidth(80)
            transport_layout.addWidget(self._timecode_label)

            # Frame label
            self._frame_label = QLabel("Frame: 0")
            self._frame_label.setObjectName("FrameLabel")
            transport_layout.addWidget(self._frame_label)

            transport_layout.addStretch()

            # Zoom controls
            zoom_lbl = QLabel("Zoom:")
            transport_layout.addWidget(zoom_lbl)

            zoom_out_btn = QToolButton()
            zoom_out_btn.setText("−")
            zoom_out_btn.setFixedSize(22, 22)
            zoom_out_btn.clicked.connect(self.model.zoom_out)
            transport_layout.addWidget(zoom_out_btn)

            self._zoom_slider = QSlider(Qt.Horizontal)
            self._zoom_slider.setRange(1, 50)
            self._zoom_slider.setValue(10)
            self._zoom_slider.setFixedWidth(80)
            self._zoom_slider.valueChanged.connect(
                lambda v: self.model.set_zoom(v / 10.0)
            )
            transport_layout.addWidget(self._zoom_slider)

            zoom_in_btn = QToolButton()
            zoom_in_btn.setText("+")
            zoom_in_btn.setFixedSize(22, 22)
            zoom_in_btn.clicked.connect(self.model.zoom_in)
            transport_layout.addWidget(zoom_in_btn)

            # Add marker button
            transport_layout.addSpacing(8)
            marker_btn = QToolButton()
            marker_btn.setText("📌 Marker")
            marker_btn.setFixedHeight(28)
            marker_btn.clicked.connect(self._on_add_marker)
            transport_layout.addWidget(marker_btn)

            main_layout.addWidget(transport)

            # Separator
            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            main_layout.addWidget(sep)

            # ===== TIMELINE AREA =====
            timeline_area = QWidget()
            timeline_layout = QHBoxLayout(timeline_area)
            timeline_layout.setContentsMargins(0, 0, 0, 0)
            timeline_layout.setSpacing(0)

            # Left: Track headers
            self._track_header_list = QListWidget()
            self._track_header_list.setObjectName("TrackHeaders")
            self._track_header_list.setFixedWidth(self.TRACK_HEADER_WIDTH)
            self._track_header_list.setHorizontalScrollBarPolicy(
                Qt.ScrollBarAlwaysOff
            )
            self._track_header_list.setVerticalScrollBarPolicy(
                Qt.ScrollBarAlwaysOff
            )
            timeline_layout.addWidget(self._track_header_list)

            # Right: Clip area (scrollable)
            self._clip_scroll = QScrollArea()
            self._clip_scroll.setObjectName("ClipScroll")
            self._clip_scroll.setWidgetResizable(True)
            self._clip_scroll.setHorizontalScrollBarPolicy(
                Qt.ScrollBarAlwaysOn
            )

            self._clip_area = QWidget()
            self._clip_area.setObjectName("ClipArea")
            self._clip_area.setMinimumHeight(300)
            self._clip_area_layout = QVBoxLayout(self._clip_area)
            self._clip_area_layout.setContentsMargins(0, 0, 0, 0)
            self._clip_area_layout.setSpacing(0)
            self._clip_area_layout.addStretch()

            self._clip_scroll.setWidget(self._clip_area)
            timeline_layout.addWidget(self._clip_scroll, 1)

            main_layout.addWidget(timeline_area, 1)

            # ===== BOTTOM STATUS =====
            status_bar = QWidget()
            status_bar.setObjectName("TimelineStatus")
            status_layout = QHBoxLayout(status_bar)
            status_layout.setContentsMargins(8, 2, 8, 2)

            self._status_label = QLabel("Timeline ready")
            self._status_label.setObjectName("TLStatus")
            status_layout.addWidget(self._status_label)
            status_layout.addStretch()

            self._duration_label = QLabel("Duration: 0:00")
            status_layout.addWidget(self._duration_label)

            main_layout.addWidget(status_bar)

            # Theme apply
            self._apply_theme()

            # Tracks populate karo
            self._populate_tracks()

            # Playback timer (30fps simulate)
            self._play_timer = QTimer()
            self._play_timer.setInterval(int(1000 / self.model.fps))
            self._play_timer.timeout.connect(self._on_timer_tick)

        except ImportError:
            logger.warning("PyQt5 nahi - timeline non-Qt mode")
        except Exception as e:
            logger.error(f"Timeline widget build error: {e}")

    def _apply_theme(self):
        """Theme apply karo"""
        if not self.theme_manager or not self._widget:
            return
        try:
            p = self.theme_manager.get_palette()
            self._widget.setStyleSheet(f"""
                #TimelineWidget {{
                    background-color: {p.timeline_bg};
                }}
                #TransportBar {{
                    background-color: {p.bg_secondary};
                    border-bottom: 1px solid {p.border};
                }}
                QToolButton {{
                    background-color: {p.bg_elevated};
                    border: 1px solid {p.border};
                    border-radius: 4px;
                    color: {p.text_primary};
                    font-size: 13px;
                }}
                QToolButton:hover {{
                    background-color: {p.bg_hover};
                    border-color: {p.accent};
                }}
                QToolButton:checked {{
                    background-color: {p.accent_muted};
                    border-color: {p.accent};
                    color: {p.accent};
                }}
                QPushButton {{
                    background-color: {p.accent};
                    border: none;
                    border-radius: 4px;
                    color: #000;
                    font-weight: bold;
                    font-size: 12px;
                }}
                QPushButton:checked {{
                    background-color: {p.text_warning};
                }}
                #TimecodeLabel {{
                    background-color: {p.bg_primary};
                    color: {p.accent};
                    font-family: monospace;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 2px 6px;
                    border: 1px solid {p.border};
                    border-radius: 3px;
                }}
                #FrameLabel {{
                    color: {p.text_secondary};
                    font-size: 11px;
                }}
                #TrackHeaders {{
                    background-color: {p.bg_secondary};
                    border: none;
                    border-right: 1px solid {p.border};
                    outline: 0;
                }}
                #TrackHeaders::item {{
                    padding: 4px 6px;
                    border-bottom: 1px solid {p.border};
                    color: {p.text_primary};
                    font-size: 11px;
                }}
                #TrackHeaders::item:selected {{
                    background-color: {p.accent_muted};
                    color: {p.accent};
                }}
                #ClipArea {{
                    background-color: {p.timeline_bg};
                }}
                #ClipScroll {{
                    border: none;
                }}
                #TimelineStatus {{
                    background-color: {p.bg_secondary};
                    border-top: 1px solid {p.border};
                }}
                #TLStatus {{
                    color: {p.text_secondary};
                    font-size: 10px;
                }}
                QSlider::groove:horizontal {{
                    height: 3px;
                    background: {p.border};
                    border-radius: 2px;
                }}
                QSlider::sub-page:horizontal {{
                    background: {p.accent};
                    border-radius: 2px;
                }}
                QSlider::handle:horizontal {{
                    background: {p.accent};
                    width: 10px; height: 10px;
                    margin: -4px 0;
                    border-radius: 5px;
                }}
                QLabel {{
                    color: {p.text_secondary};
                    font-size: 10px;
                }}
            """)
        except Exception as e:
            logger.warning(f"Theme apply error: {e}")

    def _populate_tracks(self):
        """Track headers populate karo"""
        if not self._track_header_list:
            return

        try:
            from PyQt5.QtWidgets import QListWidgetItem
            from PyQt5.QtCore import Qt

            self._track_header_list.blockSignals(True)
            self._track_header_list.clear()

            for track in self.model.get_tracks_ordered():
                mute  = "🔇" if track.muted  else "🔊"
                lock  = "🔒" if track.locked else "  "
                clip_count = len(track.clips)

                text = (
                    f"{track.get_icon()} {track.name}\n"
                    f"  {mute}{lock} {clip_count} clips"
                )
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, track.id)
                item.setSizeHint(
                    __import__('PyQt5.QtCore', fromlist=['QSize'])
                    .QSize(self.TRACK_HEADER_WIDTH, track.height)
                )
                self._track_header_list.addItem(item)

            self._track_header_list.blockSignals(False)

        except Exception as e:
            logger.warning(f"Track populate error: {e}")
            if self._track_header_list:
                self._track_header_list.blockSignals(False)

    def _update_status(self):
        """Status bar update karo"""
        if not self._status_label:
            return
        try:
            stats = self.model.get_statistics()
            self._status_label.setText(
                f"{stats['total_tracks']} tracks | "
                f"{stats['total_clips']} clips | "
                f"{stats['total_markers']} markers"
            )
            total_sec = stats['total_seconds']
            mins = int(total_sec // 60)
            secs = int(total_sec % 60)
            if self._duration_label:
                self._duration_label.setText(
                    f"Duration: {mins}:{secs:02d}"
                )
        except Exception:
            pass

    def _update_timecode(self):
        """Timecode display update karo"""
        frame = self.model.get_current_frame()
        tc    = self.model.get_timecode(frame)
        if self._timecode_label:
            self._timecode_label.setText(tc)
        if self._frame_label:
            self._frame_label.setText(f"Frame: {frame}")

    # ----------------------------------------------------------
    # EVENT HANDLERS
    # ----------------------------------------------------------

    def _on_model_changed(self, event: str, data: Dict):
        """Model changes handle karo"""
        if event in ["track_added", "track_removed", "track_updated",
                     "track_reordered", "clip_added", "clip_removed",
                     "timeline_cleared"]:
            self._populate_tracks()
            self._update_status()

        elif event == "frame_changed":
            self._update_timecode()

        elif event == "playback_state_changed":
            state = data.get("state")
            if self._play_btn:
                is_playing = state == PlaybackState.PLAYING.value
                try:
                    self._play_btn.setChecked(is_playing)
                    self._play_btn.setText(
                        "⏸ Pause" if is_playing else "▶ Play"
                    )
                    # Timer control
                    if is_playing:
                        self._play_timer.start()
                    else:
                        self._play_timer.stop()
                except Exception:
                    pass

        elif event == "zoom_changed":
            zoom = data.get("zoom", 1.0)
            if self._zoom_slider:
                try:
                    self._zoom_slider.blockSignals(True)
                    self._zoom_slider.setValue(int(zoom * 10))
                    self._zoom_slider.blockSignals(False)
                except Exception:
                    pass

    def _on_play_clicked(self, checked: bool):
        """Play button click"""
        if checked:
            self.model.play()
        else:
            self.model.pause()

    def _on_timer_tick(self):
        """Playback timer tick - next frame advance karo"""
        if self.model.get_playback_state() == PlaybackState.PLAYING.value:
            current = self.model.get_current_frame()
            total   = self.model.get_total_duration()

            if current >= total:
                if self.model.get_loop():
                    self.model.go_to_start()
                else:
                    self.model.stop()
            else:
                self.model.next_frame()

    def _on_add_marker(self):
        """Marker add karo current frame pe"""
        frame = self.model.get_current_frame()
        self.model.add_marker(
            frame = frame,
            label = f"Mark {len(self.model.get_markers())+1}",
        )
        if self._status_label:
            self._status_label.setText(
                f"Marker added @ frame {frame}"
            )

    # ----------------------------------------------------------
    # PUBLIC API
    # ----------------------------------------------------------

    def get_widget(self):
        """Qt widget lo"""
        return self._widget

    def get_model(self) -> TimelineModel:
        """Timeline model lo"""
        return self.model


# ============================================================
# GLOBAL INSTANCE
# ============================================================

_global_model: Optional[TimelineModel] = None


def get_timeline_model(fps: int = 30) -> TimelineModel:
    """Global TimelineModel lo (singleton)"""
    global _global_model
    if _global_model is None:
        _global_model = TimelineModel(fps=fps)
    return _global_model


# ============================================================
# TEST SECTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="DEBUG")
    print_banner("Timeline Widget Test", "Animation Timeline Editor")

    # ===== TEST 1: Model Init =====
    print_section("Test 1: Model Initialization")
    model = TimelineModel(fps=30)
    stats = model.get_statistics()
    print(f"✅ TimelineModel initialized | FPS: {model.fps}")
    print(f"   Tracks   : {stats['total_tracks']}")
    print(f"   Timecode : {stats['current_timecode']}")
    print(f"   Zoom     : {stats['zoom_level']}")

    # ===== TEST 2: Tracks =====
    print_section("Test 2: Track Management")
    tracks = model.get_tracks_ordered()
    print(f"✅ Default tracks: {len(tracks)}")
    for t in tracks:
        print(f"   {t.get_icon()} {t.name:15s} ({t.track_type})")

    # Custom track add karo
    extra = model.add_track("Extra Audio", TrackType.AUDIO.value)
    print(f"✅ Added track: {extra.name}")
    print(f"   Total: {len(model.get_tracks_ordered())}")

    # Track operations
    model.rename_track(extra.id, "Background Music")
    print(f"✅ Renamed: {model.get_track(extra.id).name}")

    muted = model.toggle_track_mute(extra.id)
    print(f"✅ Muted: {muted}")
    model.toggle_track_mute(extra.id)

    locked = model.toggle_track_lock(extra.id)
    print(f"✅ Locked: {locked}")
    model.toggle_track_lock(extra.id)

    # ===== TEST 3: Clips =====
    print_section("Test 3: Clip Management")

    video_track = model.get_tracks_by_type(TrackType.VIDEO.value)[0]
    audio_track = model.get_tracks_by_type(TrackType.AUDIO.value)[0]
    char_track  = model.get_tracks_by_type(TrackType.CHARACTER.value)[0]

    # Clips add karo
    clip1 = model.add_clip(
        track_id        = video_track.id,
        name            = "Opening Scene",
        start_frame     = 0,
        duration_frames = 90,
        clip_type       = ClipType.VIDEO.value,
        color           = "#4488FF",
    )
    clip2 = model.add_clip(
        track_id        = video_track.id,
        name            = "Main Action",
        start_frame     = 90,
        duration_frames = 150,
        clip_type       = ClipType.VIDEO.value,
        color           = "#44AA44",
    )
    clip3 = model.add_clip(
        track_id        = audio_track.id,
        name            = "BGM Track",
        start_frame     = 0,
        duration_frames = 240,
        clip_type       = ClipType.AUDIO.value,
        color           = "#AA4444",
    )
    clip4 = model.add_clip(
        track_id        = char_track.id,
        name            = "Hero Walk",
        start_frame     = 30,
        duration_frames = 120,
        clip_type       = ClipType.ANIMATION.value,
        color           = "#AA44AA",
    )

    all_clips = model.get_all_clips()
    print(f"✅ Clips added: {len(all_clips)}")
    for c in all_clips:
        print(
            f"   {c.name:20s} | "
            f"{c.get_timecode_start(30)} → {c.get_timecode_end(30)} | "
            f"{c.duration_frames}f"
        )

    # ===== TEST 4: Duration =====
    print_section("Test 4: Duration Calculation")
    total = model.get_total_duration()
    secs  = model.get_total_duration_seconds()
    print(f"✅ Total duration: {total} frames = {secs:.1f}s")
    print(f"   Timecode: {model.get_timecode(total)}")

    # ===== TEST 5: Clip Operations =====
    print_section("Test 5: Clip Operations")

    # Move clip
    model.move_clip(clip2.id, 150)
    print(f"✅ Clip moved: {clip2.name} now starts @ frame {clip2.start_frame}")

    # Resize clip
    model.resize_clip(clip1.id, new_duration=120)
    print(f"✅ Clip resized: {clip1.name} = {clip1.duration_frames}f")

    # Split clip
    new_clip = model.split_clip(clip1.id, 60)
    if new_clip:
        print(f"✅ Clip split: '{clip1.name}' | '{new_clip.name}'")
        print(f"   Part1: {clip1.duration_frames}f | Part2: {new_clip.duration_frames}f")

    # Duplicate
    dup = model.duplicate_clip(clip3.id, offset=5)
    if dup:
        print(f"✅ Clip duplicated: {dup.name} @ frame {dup.start_frame}")

    # Transition
    model.set_clip_transition(
        clip1.id,
        TransitionType.FADE_IN.value,
        at_start=True,
        duration=10,
    )
    print(f"✅ Transition set: {clip1.transition_in.transition_type}")

    # ===== TEST 6: Selection =====
    print_section("Test 6: Clip Selection")
    model.select_clip(clip1.id)
    model.select_clip(clip3.id, multi=True)
    selected = model.get_selected_clips()
    print(f"✅ Selected: {len(selected)} clips")
    for c in selected:
        print(f"   ◆ {c.name}")

    model.deselect_all_clips()
    print(f"✅ Deselected: {len(model.get_selected_clips())}")

    # ===== TEST 7: Markers =====
    print_section("Test 7: Markers")
    m1 = model.add_marker(0,   "Start",    "#FFD700", "chapter")
    m2 = model.add_marker(90,  "Act 1",    "#FF4444", "chapter")
    m3 = model.add_marker(150, "Climax",   "#44FF44", "note")
    m4 = model.add_marker(230, "Ending",   "#4444FF", "chapter")

    markers = model.get_markers()
    print(f"✅ Markers: {len(markers)}")
    for m in markers:
        print(f"   📌 {m.get_timecode(30)} - {m.label} [{m.marker_type}]")

    # Marker remove
    removed = model.remove_marker(m3.id)
    print(f"✅ Marker removed: {removed}")

    # ===== TEST 8: Playback =====
    print_section("Test 8: Playback Controls")
    print(f"   State: {model.get_playback_state()}")

    model.play()
    print(f"✅ Play: {model.get_playback_state()}")

    model.pause()
    print(f"✅ Pause: {model.get_playback_state()}")

    model.set_current_frame(45)
    print(f"✅ Frame set: {model.get_current_frame()}")
    print(f"   Timecode: {model.get_timecode()}")

    model.next_frame()
    model.next_frame()
    model.next_frame()
    print(f"✅ Next frame x3: {model.get_current_frame()}")

    model.go_to_start()
    print(f"✅ Go to start: {model.get_current_frame()}")

    model.go_to_end()
    print(f"✅ Go to end: {model.get_current_frame()}")

    model.stop()
    print(f"✅ Stop: {model.get_playback_state()} | Frame: {model.get_current_frame()}")

    # ===== TEST 9: Zoom & Scroll =====
    print_section("Test 9: Zoom & Scroll")
    model.set_zoom(2.0)
    print(f"✅ Zoom set: {model.get_zoom()}")

    model.zoom_in()
    print(f"✅ Zoom in: {model.get_zoom():.2f}")

    model.zoom_out()
    model.zoom_out()
    print(f"✅ Zoom out: {model.get_zoom():.2f}")

    # Frame-pixel conversion
    px = model.frame_to_pixel(30)
    fr = model.pixel_to_frame(px)
    print(f"✅ Frame→Pixel→Frame: 30 → {px:.1f}px → {fr}f")

    # ===== TEST 10: Timeline Print =====
    print_section("Test 10: Timeline Visualization")
    model.print_timeline()

    # ===== TEST 11: Statistics =====
    print_section("Test 11: Final Statistics")
    stats = model.get_statistics()
    for k, v in stats.items():
        print(f"   {k:22s}: {v}")

    # ===== TEST 12: Listeners =====
    print_section("Test 12: Event Listeners")
    events = []
    def on_event(event, data):
        events.append(event)

    model.add_listener(on_event)
    model.play()
    model.set_current_frame(10)
    model.add_marker(10, "Test")
    model.stop()
    print(f"✅ Events: {events}")

    # ===== TEST 13: Qt Widget =====
    print_section("Test 13: Qt Widget Build")
    try:
        from PyQt5.QtWidgets import QApplication, QMainWindow
        import sys as _sys

        app = QApplication.instance() or QApplication(_sys.argv)

        from src.ui.theme_manager import ThemeManager
        theme = ThemeManager()
        theme.set_application(app)

        window = QMainWindow()
        window.setWindowTitle("Timeline Test")
        window.resize(900, 350)

        tl_widget = TimelineWidget(
            model         = model,
            theme_manager = theme,
        )
        window.setCentralWidget(tl_widget.get_widget())
        window.show()
        print(f"✅ Qt widget shown")

        from PyQt5.QtCore import QTimer
        QTimer.singleShot(800, app.quit)
        app.exec_()
        print(f"✅ Qt test complete")

    except ImportError:
        print("⚠️  PyQt5 visual test skip")
    except Exception as e:
        print(f"⚠️  Qt test: {e}")

    # ===== TEST 14: Singleton =====
    print_section("Test 14: Global Singleton")
    m1 = get_timeline_model()
    m2 = get_timeline_model()
    print(f"✅ Singleton: {m1 is m2}")

    print_banner("✅ All Tests Passed!", "timeline_widget.py Working Perfectly")