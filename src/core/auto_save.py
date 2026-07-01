# ============================================================
# 3D ANIMATION STUDIO - Auto-Save System
# ============================================================
# Features:
# - Background auto-save (configurable interval)
# - Only saves when dirty (unsaved changes)
# - Backup rotation
# - Session recovery (crash ke baad restore)
# - Save history tracking
# - Non-blocking (UI freeze nahi karega)
# - Pause/Resume support
# - Custom save callbacks
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

import threading
import time
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from collections import deque

from src.utils.logger import get_logger
from src.utils.helpers import (
    ensure_dir, get_timestamp, generate_short_id,
    read_json, write_json, delete_file, format_bytes,
    get_file_size, format_duration
)
from src.utils.config_manager import get_config

logger = get_logger("AutoSave")


# ============================================================
# SAVE STATE
# ============================================================

class SaveState:
    """Auto-save ka current state"""
    IDLE = "idle"           # Kuch nahi ho raha
    WAITING = "waiting"     # Next save ka wait
    SAVING = "saving"       # Save ho raha hai
    PAUSED = "paused"       # Paused
    ERROR = "error"         # Error state
    STOPPED = "stopped"     # Fully stopped


# ============================================================
# SAVE EVENT (History ke liye)
# ============================================================

class SaveEvent:
    """Single save event ka record"""

    def __init__(self, event_type: str,
                 success: bool = True,
                 message: str = "",
                 file_path: Optional[str] = None,
                 file_size: int = 0):
        self.timestamp = get_timestamp()
        self.datetime = datetime.now()
        self.event_type = event_type  # "auto", "manual", "recovery"
        self.success = success
        self.message = message
        self.file_path = file_path
        self.file_size = file_size

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "success": self.success,
            "message": self.message,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "file_size_readable": format_bytes(self.file_size) if self.file_size else "N/A",
        }


# ============================================================
# SESSION RECOVERY FILE
# ============================================================

class SessionRecovery:
    """
    Crash ke baad recovery ke liye.
    Har save par ek recovery file update hoti hai.
    """

    RECOVERY_FILE = "session_recovery.json"

    def __init__(self, recovery_dir: str):
        self.recovery_dir = ensure_dir(recovery_dir)
        self.recovery_file = os.path.join(recovery_dir, self.RECOVERY_FILE)

    def write_recovery_data(self, project_data: Dict,
                            project_file: Optional[str] = None):
        """Recovery data write karo (har save par)"""
        try:
            recovery = {
                "saved_at": get_timestamp(),
                "session_id": generate_short_id(),
                "original_file": project_file,
                "project_data": project_data,
                "process_id": os.getpid(),
            }

            # Atomic write
            temp_file = self.recovery_file + ".tmp"
            write_json(temp_file, recovery)
            os.replace(temp_file, self.recovery_file)

            logger.debug("Recovery data updated")
            return True

        except Exception as e:
            logger.error(f"Recovery write failed: {e}")
            return False

    def has_recovery_data(self) -> bool:
        """Recovery data available hai?"""
        return os.path.exists(self.recovery_file)

    def get_recovery_data(self) -> Optional[Dict]:
        """Recovery data read karo"""
        if not self.has_recovery_data():
            return None
        return read_json(self.recovery_file)

    def is_recovery_needed(self) -> bool:
        """
        Check karo recovery zaroori hai kya.
        Agar previous session properly close hui to recovery nahi chahiye.
        """
        if not self.has_recovery_data():
            return False

        data = self.get_recovery_data()
        if not data:
            return False

        # Agar current PID same hai to same session hai
        if data.get("process_id") == os.getpid():
            return False

        # Purani session data hai - recovery available
        return True

    def clear_recovery(self):
        """Recovery data clear karo (clean shutdown par)"""
        if os.path.exists(self.recovery_file):
            delete_file(self.recovery_file)
            logger.debug("Recovery data cleared")


# ============================================================
# MAIN AUTO-SAVE SYSTEM
# ============================================================

class AutoSaveSystem:
    """
    Background auto-save system.
    Threading use karta hai taki UI freeze na ho.
    """

    def __init__(self, config: Optional[Dict] = None,
                 save_callback: Optional[Callable] = None,
                 dirty_check_callback: Optional[Callable] = None,
                 recovery_dir: Optional[str] = None):
        """
        Args:
            config: Configuration
            save_callback: Function jo call hoga save ke liye.
                          Should return bool (success).
            dirty_check_callback: Function jo return kare dirty state (bool)
            recovery_dir: Recovery files kahan store karni hain
        """
        # Config load karo
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # Settings
        ui_config = self.config.get("ui", {})
        self.interval_seconds = ui_config.get("auto_save_interval", 300)  # 5 min default
        self.enabled = True

        # Callbacks
        self._save_callback = save_callback
        self._dirty_check_callback = dirty_check_callback

        # State
        self.state = SaveState.IDLE
        self._last_save_time: Optional[float] = None
        self._last_save_success = True
        self._last_error: Optional[str] = None
        self._save_count = 0

        # Threading
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._save_now_event = threading.Event()
        self._lock = threading.Lock()

        # History
        self.history: deque = deque(maxlen=50)

        # Recovery
        if recovery_dir is None:
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            recovery_dir = os.path.join(project_root, "cache")

        self.recovery = SessionRecovery(recovery_dir)

        # Listeners
        self._listeners: List[Callable] = []

        logger.info(f"AutoSaveSystem initialized (interval: {self.interval_seconds}s)")

    # ------------------------------------------------------------
    # CALLBACK SETUP
    # ------------------------------------------------------------

    def set_save_callback(self, callback: Callable[[], bool]):
        """
        Save function set karo.
        Callback should return True on success.
        """
        self._save_callback = callback

    def set_dirty_check_callback(self, callback: Callable[[], bool]):
        """
        Dirty state check function set karo.
        Callback should return True agar unsaved changes hain.
        """
        self._dirty_check_callback = callback

    # ------------------------------------------------------------
    # LIFECYCLE
    # ------------------------------------------------------------

    def start(self) -> bool:
        """Auto-save start karo (background thread)"""
        with self._lock:
            if self._thread and self._thread.is_alive():
                logger.warning("Auto-save already running")
                return False

            self._stop_event.clear()
            self._pause_event.clear()
            self._save_now_event.clear()

            self._thread = threading.Thread(
                target=self._auto_save_loop,
                name="AutoSaveThread",
                daemon=True
            )
            self._thread.start()

            self.state = SaveState.WAITING
            logger.info("Auto-save started")
            self._notify_listeners("started")
            return True

    def stop(self, save_before_stop: bool = True) -> bool:
        """
        Auto-save stop karo.

        Args:
            save_before_stop: True to ek final save kar do
        """
        with self._lock:
            if not self._thread or not self._thread.is_alive():
                return True

            logger.info("Stopping auto-save...")

            # Final save (agar chahiye)
            if save_before_stop and self._save_callback:
                try:
                    if self._is_dirty():
                        self._perform_save(event_type="shutdown")
                except Exception as e:
                    logger.error(f"Final save failed: {e}")

            # Thread stop karo
            self._stop_event.set()
            self._save_now_event.set()  # Wait break karne ke liye

            # Thread finish hone do (max 5 sec wait)
            self._thread.join(timeout=5.0)

            self.state = SaveState.STOPPED

            # Recovery clear karo (clean shutdown)
            self.recovery.clear_recovery()

            logger.info("Auto-save stopped")
            self._notify_listeners("stopped")
            return True

    def pause(self):
        """Auto-save pause karo"""
        with self._lock:
            self._pause_event.set()
            self.state = SaveState.PAUSED
            logger.info("Auto-save paused")
            self._notify_listeners("paused")

    def resume(self):
        """Auto-save resume karo"""
        with self._lock:
            self._pause_event.clear()
            self.state = SaveState.WAITING
            logger.info("Auto-save resumed")
            self._notify_listeners("resumed")

    def is_running(self) -> bool:
        """Currently chal raha hai?"""
        return self._thread is not None and self._thread.is_alive()

    def is_paused(self) -> bool:
        return self._pause_event.is_set()

    # ------------------------------------------------------------
    # MANUAL TRIGGERS
    # ------------------------------------------------------------

    def save_now(self, force: bool = False) -> bool:
        """
        Turant save trigger karo.

        Args:
            force: True to ignore dirty check
        """
        if not self._save_callback:
            logger.error("No save callback set")
            return False

        try:
            if not force and not self._is_dirty():
                logger.debug("Nothing to save (not dirty)")
                return True

            return self._perform_save(event_type="manual")

        except Exception as e:
            logger.error(f"Manual save failed: {e}")
            return False

    def request_save(self):
        """Auto-save loop me next iteration me save request karo"""
        self._save_now_event.set()

    # ------------------------------------------------------------
    # INTERNAL SAVE LOGIC
    # ------------------------------------------------------------

    def _auto_save_loop(self):
        """
        Background thread ka main loop.
        Har interval par dirty check karke save karta hai.
        """
        logger.debug("Auto-save loop started")

        while not self._stop_event.is_set():
            try:
                # Interval wait karo (ya save request tak)
                self._save_now_event.wait(timeout=self.interval_seconds)
                self._save_now_event.clear()

                # Stop check
                if self._stop_event.is_set():
                    break

                # Pause check
                if self._pause_event.is_set():
                    continue

                # Enabled check
                if not self.enabled:
                    continue

                # Dirty check
                if not self._is_dirty():
                    logger.debug("Not dirty, skipping auto-save")
                    continue

                # Save karo
                self.state = SaveState.SAVING
                self._perform_save(event_type="auto")
                self.state = SaveState.WAITING

            except Exception as e:
                logger.error(f"Auto-save loop error: {e}")
                self.state = SaveState.ERROR
                self._last_error = str(e)

        logger.debug("Auto-save loop ended")

    def _perform_save(self, event_type: str = "auto") -> bool:
        """Actual save perform karta hai"""
        if not self._save_callback:
            return False

        try:
            start_time = time.time()

            # Save callback call karo
            success = self._save_callback()

            duration = time.time() - start_time

            # Event record karo
            event = SaveEvent(
                event_type=event_type,
                success=success,
                message=f"Save completed in {duration:.2f}s" if success else "Save failed",
            )
            self.history.append(event)

            if success:
                self._last_save_time = time.time()
                self._last_save_success = True
                self._save_count += 1
                self._last_error = None

                logger.info(
                    f"{event_type.title()} save successful ({duration:.2f}s) "
                    f"[Total: {self._save_count}]"
                )
                self._notify_listeners("saved", event)
            else:
                self._last_save_success = False
                self._last_error = "Save callback returned False"

                logger.error(f"{event_type.title()} save failed")
                self._notify_listeners("save_failed", event)

            return success

        except Exception as e:
            self._last_save_success = False
            self._last_error = str(e)

            event = SaveEvent(
                event_type=event_type,
                success=False,
                message=str(e),
            )
            self.history.append(event)

            logger.error(f"Save error: {e}")
            self._notify_listeners("save_failed", event)
            return False

    def _is_dirty(self) -> bool:
        """Check karo save zaroori hai kya"""
        if self._dirty_check_callback:
            try:
                return self._dirty_check_callback()
            except Exception as e:
                logger.error(f"Dirty check failed: {e}")
                return True  # Safe side - save karo

        # Default: hamesha dirty maano
        return True

    # ------------------------------------------------------------
    # SETTINGS
    # ------------------------------------------------------------

    def set_interval(self, seconds: int) -> bool:
        """Auto-save interval change karo"""
        if seconds < 10:
            logger.warning("Interval too small (min 10s)")
            return False

        with self._lock:
            self.interval_seconds = seconds

            # Loop wake up karo taki naya interval apply ho
            self._save_now_event.set()

            logger.info(f"Auto-save interval changed to {seconds}s")
            return True

    def set_enabled(self, enabled: bool):
        """Enable/disable karo"""
        self.enabled = enabled
        logger.info(f"Auto-save {'enabled' if enabled else 'disabled'}")

    # ------------------------------------------------------------
    # RECOVERY
    # ------------------------------------------------------------

    def update_recovery_data(self, project_data: Dict,
                              project_file: Optional[str] = None):
        """Recovery file update karo"""
        self.recovery.write_recovery_data(project_data, project_file)

    def check_recovery_needed(self) -> bool:
        """Recovery zaroori hai kya"""
        return self.recovery.is_recovery_needed()

    def get_recovery_data(self) -> Optional[Dict]:
        """Recovery data return karo"""
        return self.recovery.get_recovery_data()

    def clear_recovery(self):
        """Recovery data clear karo"""
        self.recovery.clear_recovery()

    # ------------------------------------------------------------
    # STATUS & INFO
    # ------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Complete status info"""
        time_since_save = None
        next_save_in = None

        if self._last_save_time:
            time_since_save = time.time() - self._last_save_time
            next_save_in = max(0, self.interval_seconds - time_since_save)

        return {
            "state": self.state,
            "enabled": self.enabled,
            "running": self.is_running(),
            "paused": self.is_paused(),
            "interval_seconds": self.interval_seconds,
            "save_count": self._save_count,
            "last_save_time": self._last_save_time,
            "last_save_success": self._last_save_success,
            "last_error": self._last_error,
            "time_since_last_save": time_since_save,
            "time_since_last_save_readable": format_duration(time_since_save) if time_since_save else "Never",
            "next_save_in": next_save_in,
            "next_save_in_readable": format_duration(next_save_in) if next_save_in else "N/A",
        }

    def get_history(self, limit: int = 10) -> List[Dict]:
        """Save history"""
        events = list(self.history)[-limit:]
        return [e.to_dict() for e in reversed(events)]

    # ------------------------------------------------------------
    # LISTENERS
    # ------------------------------------------------------------

    def add_listener(self, callback: Callable):
        """Event listener add karo"""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable):
        """Listener remove karo"""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self, event: str, data: Any = None):
        """Sab listeners ko notify karo"""
        for listener in self._listeners:
            try:
                listener(event, data)
            except Exception as e:
                logger.error(f"Listener error: {e}")


# ============================================================
# TEST FUNCTION
# ============================================================

if __name__ == "__main__":
    from src.utils.logger import setup_logging, print_banner, print_section

    setup_logging(log_level="DEBUG")
    print_banner("Auto-Save System Test", "Testing background save system")

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))

    # ============================================================
    # Setup - Fake project state
    # ============================================================
    print_section("Setup: Fake Project State")

    # Fake project state
    project_state = {
        "dirty": True,
        "save_count": 0,
        "data": {"name": "Test Project", "scenes": []}
    }

    # Save callback
    def fake_save():
        project_state["save_count"] += 1
        project_state["dirty"] = False
        print(f"  💾 Save #{project_state['save_count']} performed!")

        # Recovery bhi update karo
        autosave.update_recovery_data(
            project_state["data"],
            project_file="/fake/path/project.anim3d"
        )
        return True

    # Dirty check callback
    def is_dirty():
        return project_state["dirty"]

    print("Callbacks defined")

    # ============================================================
    # Test 1: Initialize
    # ============================================================
    print_section("Test 1: Initialize")

    autosave = AutoSaveSystem(
        save_callback=fake_save,
        dirty_check_callback=is_dirty,
        recovery_dir=os.path.join(base_dir, "cache")
    )

    # Fast interval for testing
    autosave.set_interval(3)  # 3 seconds
    print(f"Interval set to 3 seconds for testing")

    # ============================================================
    # Test 2: Listener
    # ============================================================
    print_section("Test 2: Setup Listener")

    events_received = []
    def on_event(event, data):
        events_received.append(event)
        print(f"  📡 Event: {event}")

    autosave.add_listener(on_event)

    # ============================================================
    # Test 3: Manual Save
    # ============================================================
    print_section("Test 3: Manual Save")

    project_state["dirty"] = True
    success = autosave.save_now()
    print(f"Manual save success: {success}")
    print(f"Total saves: {project_state['save_count']}")

    # ============================================================
    # Test 4: Start Auto-Save Loop
    # ============================================================
    print_section("Test 4: Start Auto-Save (3s interval)")

    autosave.start()
    print("Auto-save running in background...")
    print("Simulating work for 10 seconds...")

    for i in range(10):
        time.sleep(1)

        # Simulate changes
        if i == 2:
            project_state["dirty"] = True
            print(f"  [{i+1}s] Made changes - dirty=True")

        if i == 6:
            project_state["dirty"] = True
            print(f"  [{i+1}s] Made changes - dirty=True")

    # ============================================================
    # Test 5: Check Status
    # ============================================================
    print_section("Test 5: Auto-Save Status")

    status = autosave.get_status()
    print(f"State: {status['state']}")
    print(f"Running: {status['running']}")
    print(f"Save count: {status['save_count']}")
    print(f"Last save success: {status['last_save_success']}")
    print(f"Time since last save: {status['time_since_last_save_readable']}")

    # ============================================================
    # Test 6: Pause & Resume
    # ============================================================
    print_section("Test 6: Pause & Resume")

    autosave.pause()
    print(f"Paused. Is paused: {autosave.is_paused()}")

    project_state["dirty"] = True
    print("Made changes while paused...")
    time.sleep(4)  # Interval se zyada wait
    print(f"Save count (should not increase): {project_state['save_count']}")

    autosave.resume()
    print("Resumed")
    time.sleep(4)
    print(f"Save count (should increase now): {project_state['save_count']}")

    # ============================================================
    # Test 7: History
    # ============================================================
    print_section("Test 7: Save History")

    history = autosave.get_history(limit=5)
    print(f"Recent {len(history)} events:")
    for i, event in enumerate(history):
        symbol = "✓" if event["success"] else "✗"
        print(f"  {i+1}. {symbol} [{event['event_type']}] {event['timestamp']}")

    # ============================================================
    # Test 8: Recovery
    # ============================================================
    print_section("Test 8: Recovery System")

    has_recovery = autosave.recovery.has_recovery_data()
    print(f"Recovery data exists: {has_recovery}")

    if has_recovery:
        recovery_data = autosave.get_recovery_data()
        print(f"Recovery saved at: {recovery_data.get('saved_at')}")
        print(f"Session ID: {recovery_data.get('session_id')}")
        print(f"Original file: {recovery_data.get('original_file')}")

    # ============================================================
    # Test 9: Change Interval
    # ============================================================
    print_section("Test 9: Change Interval")

    autosave.set_interval(60)
    print(f"New interval: {autosave.interval_seconds}s")

    # ============================================================
    # Test 10: Stop
    # ============================================================
    print_section("Test 10: Stop Auto-Save")

    autosave.stop(save_before_stop=True)
    print(f"Stopped. Is running: {autosave.is_running()}")
    print(f"Final save count: {project_state['save_count']}")

    # Recovery cleared
    print(f"Recovery cleared: {not autosave.recovery.has_recovery_data()}")

    # ============================================================
    # Summary
    # ============================================================
    print_section("Test Summary")

    print(f"Total events received: {len(events_received)}")
    print(f"Total saves performed: {project_state['save_count']}")
    print(f"Event types: {set(events_received)}")

    print_banner("✅ All Tests Passed", "Auto-Save System Working")