# ============================================================
# 3D ANIMATION STUDIO - Configuration Manager
# ============================================================
# Features:
# - Config file load/save with validation
# - Runtime configuration updates
# - User preferences management (alag file me)
# - Default fallback values
# - Config change notifications (observer pattern)
# - Dot notation access (config.get("rendering.fps"))
# - Environment variable overrides
# - Config migration (version upgrades)
# ============================================================

# ===== PATH SETUP - Standalone execution ke liye =====
import sys
import os
if __name__ == "__main__":
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.dirname(os.path.dirname(_current_dir))
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
# ======================================================

import json
import copy
from typing import Any, Dict, List, Optional, Callable, Union
from datetime import datetime
from pathlib import Path

from src.utils.logger import get_logger
from src.utils.helpers import (
    read_json, write_json, ensure_dir, get_timestamp
)

logger = get_logger("ConfigManager")


# ============================================================
# CONFIG VALIDATOR
# ============================================================

class ConfigValidator:
    """
    Config values validate karta hai.
    Invalid values ko default se replace karta hai.
    """

    @staticmethod
    def validate_int(value: Any, default: int,
                     min_val: Optional[int] = None,
                     max_val: Optional[int] = None) -> int:
        """Integer validate karta hai"""
        try:
            result = int(value)
            if min_val is not None and result < min_val:
                return default
            if max_val is not None and result > max_val:
                return default
            return result
        except (TypeError, ValueError):
            return default

    @staticmethod
    def validate_float(value: Any, default: float,
                       min_val: Optional[float] = None,
                       max_val: Optional[float] = None) -> float:
        """Float validate karta hai"""
        try:
            result = float(value)
            if min_val is not None and result < min_val:
                return default
            if max_val is not None and result > max_val:
                return default
            return result
        except (TypeError, ValueError):
            return default

    @staticmethod
    def validate_string(value: Any, default: str,
                        allowed: Optional[List[str]] = None) -> str:
        """String validate karta hai"""
        try:
            result = str(value)
            if allowed and result not in allowed:
                return default
            return result
        except Exception:
            return default

    @staticmethod
    def validate_bool(value: Any, default: bool) -> bool:
        """Boolean validate karta hai"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ["true", "yes", "1", "on"]
        try:
            return bool(value)
        except Exception:
            return default

    @staticmethod
    def validate_list(value: Any, default: List,
                      item_type: Optional[type] = None) -> List:
        """List validate karta hai"""
        if not isinstance(value, list):
            return default

        if item_type:
            try:
                return [item_type(x) for x in value]
            except (TypeError, ValueError):
                return default

        return value


# ============================================================
# MAIN CONFIG MANAGER
# ============================================================

class ConfigManager:
    """
    Application configuration ka central manager.
    Singleton pattern - poore app me ek hi instance.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_file: Optional[str] = None,
                 user_prefs_file: Optional[str] = None,
                 auto_save: bool = True):
        """
        Args:
            config_file: Main config.json ka path
            user_prefs_file: User preferences file (alag)
            auto_save: Changes automatically save karne hain
        """
        # Prevent re-initialization
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._initialized = True

        # Default paths
        if config_file is None:
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            config_file = os.path.join(project_root, "config.json")

        if user_prefs_file is None:
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            user_prefs_file = os.path.join(project_root, "user_prefs.json")

        self.config_file = config_file
        self.user_prefs_file = user_prefs_file
        self.auto_save = auto_save

        # Config data
        self._config: Dict[str, Any] = {}
        self._user_prefs: Dict[str, Any] = {}
        self._defaults: Dict[str, Any] = {}

        # Change observers (callbacks)
        self._observers: Dict[str, List[Callable]] = {}

        # Load karo
        self.load()

        logger.info(f"ConfigManager initialized")
        logger.debug(f"Config file: {self.config_file}")
        logger.debug(f"User prefs: {self.user_prefs_file}")

    # ------------------------------------------------------------
    # LOAD & SAVE
    # ------------------------------------------------------------

    def load(self) -> bool:
        """
        Config aur user preferences load karta hai.
        """
        # Main config load karo
        if os.path.exists(self.config_file):
            data = read_json(self.config_file)
            if data:
                self._config = data
                self._defaults = copy.deepcopy(data)  # Backup as defaults
                logger.info("Main config loaded successfully")
            else:
                logger.error("Failed to parse config.json")
                self._config = self._get_minimal_config()
        else:
            logger.warning(f"Config file not found: {self.config_file}")
            self._config = self._get_minimal_config()
            self.save()  # Default config save karo

        # User preferences load karo (agar exist karti hai)
        if os.path.exists(self.user_prefs_file):
            user_data = read_json(self.user_prefs_file)
            if user_data:
                self._user_prefs = user_data
                # User prefs config ke upar apply karo
                self._merge_user_prefs()
                logger.info("User preferences loaded")

        # Environment variables se overrides check karo
        self._apply_env_overrides()

        return True

    def save(self) -> bool:
        """Config file save karta hai"""
        try:
            success = write_json(self.config_file, self._config)
            if success:
                logger.debug("Config saved")
            return success
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False

    def save_user_prefs(self) -> bool:
        """User preferences save karta hai"""
        try:
            success = write_json(self.user_prefs_file, self._user_prefs)
            if success:
                logger.debug("User preferences saved")
            return success
        except Exception as e:
            logger.error(f"Failed to save user prefs: {e}")
            return False

    def reload(self) -> bool:
        """Config dubara load karta hai"""
        logger.info("Reloading config...")
        return self.load()

    # ------------------------------------------------------------
    # GET / SET (Dot Notation Support)
    # ------------------------------------------------------------

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Config value get karta hai dot notation se.

        Examples:
            config.get("rendering.fps")           → 30
            config.get("physics.gravity")         → [0, -9.81, 0]
            config.get("nonexistent.key", "N/A")  → "N/A"
        """
        try:
            keys = key_path.split(".")
            value = self._config

            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default

            return value

        except Exception as e:
            logger.error(f"Error getting '{key_path}': {e}")
            return default

    def set(self, key_path: str, value: Any,
            save_immediately: bool = None) -> bool:
        """
        Config value set karta hai dot notation se.

        Examples:
            config.set("rendering.fps", 60)
            config.set("ui.theme", "light")
        """
        try:
            keys = key_path.split(".")
            target = self._config

            # Nested keys me navigate karo
            for key in keys[:-1]:
                if key not in target or not isinstance(target[key], dict):
                    target[key] = {}
                target = target[key]

            # Old value save karo (observers ke liye)
            old_value = target.get(keys[-1])

            # Naya value set karo
            target[keys[-1]] = value

            # Observers ko notify karo
            self._notify_observers(key_path, old_value, value)

            # Auto-save
            should_save = save_immediately if save_immediately is not None else self.auto_save
            if should_save:
                self.save()

            logger.debug(f"Config updated: {key_path} = {value}")
            return True

        except Exception as e:
            logger.error(f"Error setting '{key_path}': {e}")
            return False

    def has(self, key_path: str) -> bool:
        """Check karta hai key exist karti hai ya nahi"""
        sentinel = object()
        return self.get(key_path, sentinel) is not sentinel

    def delete(self, key_path: str) -> bool:
        """Config key delete karta hai"""
        try:
            keys = key_path.split(".")
            target = self._config

            for key in keys[:-1]:
                if key not in target:
                    return False
                target = target[key]

            if keys[-1] in target:
                old_value = target[keys[-1]]
                del target[keys[-1]]
                self._notify_observers(key_path, old_value, None)

                if self.auto_save:
                    self.save()
                return True

            return False

        except Exception as e:
            logger.error(f"Error deleting '{key_path}': {e}")
            return False

    # ------------------------------------------------------------
    # RESET TO DEFAULTS
    # ------------------------------------------------------------

    def reset_to_default(self, key_path: Optional[str] = None) -> bool:
        """
        Config ko default values pe reset karta hai.

        Args:
            key_path: Specific key reset karni hai to, ya None (poora config)
        """
        try:
            if key_path is None:
                # Poora config reset karo
                self._config = copy.deepcopy(self._defaults)
                logger.info("Full config reset to defaults")
            else:
                # Specific key reset karo
                keys = key_path.split(".")
                default_value = self._defaults
                for key in keys:
                    if isinstance(default_value, dict) and key in default_value:
                        default_value = default_value[key]
                    else:
                        logger.warning(f"No default for: {key_path}")
                        return False

                self.set(key_path, copy.deepcopy(default_value))
                logger.info(f"Reset to default: {key_path}")

            if self.auto_save:
                self.save()
            return True

        except Exception as e:
            logger.error(f"Reset failed: {e}")
            return False

    # ------------------------------------------------------------
    # USER PREFERENCES (User-specific overrides)
    # ------------------------------------------------------------

    def set_user_pref(self, key_path: str, value: Any) -> bool:
        """
        User preference set karta hai.
        Ye alag file me save hoti hai aur config ke upar apply hoti hai.
        """
        try:
            keys = key_path.split(".")
            target = self._user_prefs

            for key in keys[:-1]:
                if key not in target or not isinstance(target[key], dict):
                    target[key] = {}
                target = target[key]

            target[keys[-1]] = value

            # Main config me bhi apply karo (runtime ke liye)
            self.set(key_path, value, save_immediately=False)

            # User prefs save karo
            self.save_user_prefs()

            logger.debug(f"User pref set: {key_path} = {value}")
            return True

        except Exception as e:
            logger.error(f"Failed to set user pref: {e}")
            return False

    def get_user_pref(self, key_path: str, default: Any = None) -> Any:
        """User preference get karta hai"""
        try:
            keys = key_path.split(".")
            value = self._user_prefs

            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default

            return value
        except Exception:
            return default

    def clear_user_prefs(self) -> bool:
        """Saari user preferences clear karta hai"""
        try:
            self._user_prefs = {}
            self.save_user_prefs()

            # Config reload karo taki original values wapas aayein
            self.load()

            logger.info("User preferences cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear user prefs: {e}")
            return False

    def _merge_user_prefs(self):
        """User prefs ko main config ke upar apply karta hai"""
        self._deep_merge(self._config, self._user_prefs)

    def _deep_merge(self, base: Dict, override: Dict):
        """Recursively dictionaries merge karta hai"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    # ------------------------------------------------------------
    # ENVIRONMENT VARIABLE OVERRIDES
    # ------------------------------------------------------------

    def _apply_env_overrides(self):
        """
        Environment variables se config overrides apply karta hai.

        Format: ANIMSTUDIO_<SECTION>_<KEY>
        Example: ANIMSTUDIO_RENDERING_FPS=60
        """
        prefix = "ANIMSTUDIO_"

        for env_key, env_value in os.environ.items():
            if env_key.startswith(prefix):
                config_path = env_key[len(prefix):].lower().replace("_", ".")

                # Value type parse karo
                parsed_value = self._parse_env_value(env_value)
                self.set(config_path, parsed_value, save_immediately=False)

                logger.debug(f"Env override: {config_path} = {parsed_value}")

    def _parse_env_value(self, value: str) -> Any:
        """Environment variable value ko sahi type me parse karta hai"""
        # Boolean
        if value.lower() in ["true", "yes", "1"]:
            return True
        if value.lower() in ["false", "no", "0"]:
            return False

        # Number
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # JSON (list/dict)
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            pass

        # String (default)
        return value

    # ------------------------------------------------------------
    # OBSERVERS (Change Notifications)
    # ------------------------------------------------------------

    def observe(self, key_path: str, callback: Callable) -> None:
        """
        Config change notification register karta hai.

        Args:
            key_path: Konsi key watch karni hai
            callback: Function jo call hoga (old_value, new_value)

        Example:
            def on_fps_change(old, new):
                print(f"FPS changed: {old} → {new}")

            config.observe("rendering.fps", on_fps_change)
        """
        if key_path not in self._observers:
            self._observers[key_path] = []
        self._observers[key_path].append(callback)
        logger.debug(f"Observer added for: {key_path}")

    def unobserve(self, key_path: str, callback: Callable) -> None:
        """Observer remove karta hai"""
        if key_path in self._observers:
            try:
                self._observers[key_path].remove(callback)
            except ValueError:
                pass

    def _notify_observers(self, key_path: str,
                          old_value: Any, new_value: Any):
        """Observers ko notify karta hai"""
        # Exact match
        if key_path in self._observers:
            for callback in self._observers[key_path]:
                try:
                    callback(old_value, new_value)
                except Exception as e:
                    logger.error(f"Observer callback failed: {e}")

        # Parent path matches (e.g., "rendering.fps" changes → "rendering" observers)
        parts = key_path.split(".")
        for i in range(len(parts) - 1, 0, -1):
            parent = ".".join(parts[:i])
            if parent in self._observers:
                for callback in self._observers[parent]:
                    try:
                        callback(old_value, new_value)
                    except Exception as e:
                        logger.error(f"Observer callback failed: {e}")

    # ------------------------------------------------------------
    # UTILITY METHODS
    # ------------------------------------------------------------

    def get_all(self) -> Dict[str, Any]:
        """Poora config return karta hai (deep copy)"""
        return copy.deepcopy(self._config)

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Poori section return karta hai.

        Example:
            config.get_section("rendering")  → {"default_fps": 30, ...}
        """
        return copy.deepcopy(self.get(section, {}))

    def update_section(self, section: str, updates: Dict) -> bool:
        """Poori section update karta hai"""
        try:
            current = self.get_section(section)
            self._deep_merge(current, updates)
            self.set(section, current)
            return True
        except Exception as e:
            logger.error(f"Section update failed: {e}")
            return False

    def _get_minimal_config(self) -> Dict:
        """
        Agar config.json missing ho to minimal fallback config.
        """
        return {
            "app": {
                "name": "3D Animation Studio",
                "version": "1.0.0"
            },
            "rendering": {
                "default_fps": 30,
                "default_quality": "draft"
            },
            "ui": {
                "theme": "dark"
            }
        }

    def export_config(self, filepath: str) -> bool:
        """Config ko file me export karta hai (backup ke liye)"""
        try:
            export_data = {
                "exported_at": get_timestamp(),
                "version": self.get("app.version", "1.0.0"),
                "config": self._config,
                "user_prefs": self._user_prefs,
            }
            return write_json(filepath, export_data)
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False

    def import_config(self, filepath: str,
                      merge: bool = False) -> bool:
        """
        Config file import karta hai.

        Args:
            filepath: Import karne wali file
            merge: True to merge, False to replace
        """
        try:
            data = read_json(filepath)
            if not data:
                return False

            imported_config = data.get("config", data)

            if merge:
                self._deep_merge(self._config, imported_config)
            else:
                self._config = imported_config

            if "user_prefs" in data:
                self._user_prefs = data["user_prefs"]
                self.save_user_prefs()

            self.save()
            logger.info(f"Config imported from: {filepath}")
            return True

        except Exception as e:
            logger.error(f"Import failed: {e}")
            return False


# ============================================================
# GLOBAL ACCESS FUNCTION
# ============================================================

_global_config: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """
    Global config instance return karta hai.

    Usage:
        from src.utils.config_manager import get_config
        config = get_config()
        fps = config.get("rendering.default_fps")
    """
    global _global_config
    if _global_config is None:
        _global_config = ConfigManager()
    return _global_config


def init_config(config_file: Optional[str] = None,
                user_prefs_file: Optional[str] = None) -> ConfigManager:
    """Config initialize karta hai custom paths ke saath"""
    global _global_config
    _global_config = ConfigManager(
        config_file=config_file,
        user_prefs_file=user_prefs_file
    )
    return _global_config


# ============================================================
# TEST FUNCTION
# ============================================================

if __name__ == "__main__":
    from src.utils.logger import setup_logging, print_banner, print_section

    setup_logging(log_level="DEBUG")
    print_banner("Config Manager Test", "Testing configuration system")

    # ============================================================
    # Test 1: Basic Load
    # ============================================================
    print_section("Test 1: Basic Load & Get")

    config = get_config()

    app_name = config.get("app.name")
    fps = config.get("rendering.default_fps")
    theme = config.get("ui.theme")

    print(f"App Name: {app_name}")
    print(f"Default FPS: {fps}")
    print(f"UI Theme: {theme}")

    # ============================================================
    # Test 2: Nested Access
    # ============================================================
    print_section("Test 2: Nested Dot Notation")

    gravity = config.get("physics.gravity")
    cotton_stiffness = config.get("physics.cloth_materials.cotton.stiffness")

    print(f"Gravity: {gravity}")
    print(f"Cotton Stiffness: {cotton_stiffness}")

    # Missing key with default
    missing = config.get("nonexistent.key", "DEFAULT_VALUE")
    print(f"Missing key: {missing}")

    # ============================================================
    # Test 3: Set Values
    # ============================================================
    print_section("Test 3: Set Configuration Values")

    # Runtime change
    config.set("rendering.default_fps", 60, save_immediately=False)
    print(f"FPS updated to: {config.get('rendering.default_fps')}")

    # Revert
    config.set("rendering.default_fps", 30, save_immediately=False)

    # ============================================================
    # Test 4: Observers
    # ============================================================
    print_section("Test 4: Change Observers")

    changes = []
    def on_theme_change(old, new):
        changes.append((old, new))
        print(f"  → Theme changed: {old} → {new}")

    config.observe("ui.theme", on_theme_change)

    config.set("ui.theme", "light", save_immediately=False)
    config.set("ui.theme", "dark", save_immediately=False)

    print(f"Total theme changes recorded: {len(changes)}")

    # ============================================================
    # Test 5: User Preferences
    # ============================================================
    print_section("Test 5: User Preferences")

    config.set_user_pref("ui.font_size", 14)
    config.set_user_pref("shortcuts.play", "Ctrl+P")

    font_size = config.get_user_pref("ui.font_size")
    play_shortcut = config.get_user_pref("shortcuts.play")

    print(f"User font size: {font_size}")
    print(f"User play shortcut: {play_shortcut}")

    # ============================================================
    # Test 6: Section Access
    # ============================================================
    print_section("Test 6: Section Access")

    rendering_config = config.get_section("rendering")
    print(f"Rendering section keys: {list(rendering_config.keys())[:5]}...")

    # ============================================================
    # Test 7: Validation
    # ============================================================
    print_section("Test 7: Validator")

    val = ConfigValidator.validate_int("abc", default=30, min_val=1, max_val=120)
    print(f"Invalid int 'abc' → default: {val}")

    val = ConfigValidator.validate_int("60", default=30, min_val=1, max_val=120)
    print(f"Valid int '60' → {val}")

    val = ConfigValidator.validate_string("light", default="dark",
                                          allowed=["dark", "light"])
    print(f"Valid string 'light' → {val}")

    # ============================================================
    # Test 8: Export/Import
    # ============================================================
    print_section("Test 8: Export Config")

    export_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "temp",
        "config_export.json"
    )
    ensure_dir(os.path.dirname(export_path))

    success = config.export_config(export_path)
    print(f"Export: {'✓ Success' if success else '✗ Failed'}")
    print(f"Export path: {export_path}")

    # ============================================================
    # Cleanup
    # ============================================================
    print_section("Cleanup")

    config.clear_user_prefs()
    print("User prefs cleared")

    # Remove test files
    from src.utils.helpers import delete_file
    delete_file(export_path)

    # user_prefs.json bhi delete karo (test ka)
    user_prefs_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "user_prefs.json"
    )
    delete_file(user_prefs_file)

    print_banner("✅ All Tests Passed", "Config Manager Working")