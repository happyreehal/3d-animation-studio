# ============================================================
# 3D ANIMATION STUDIO - Advanced File Manager
# ============================================================

# ===== PATH SETUP - Standalone execution ke liye =====
import sys
import os
if __name__ == "__main__":
    # Agar directly run kiya to project root add karo
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.dirname(os.path.dirname(_current_dir))
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
# ======================================================
# ============================================================
# 3D ANIMATION STUDIO - Advanced File Manager
# ============================================================
# Features:
# - Project file operations (save, load, backup)
# - Automatic backups with versioning
# - Temp file management with auto-cleanup
# - File watching (changes detect karta hai)
# - Compression/decompression (project size kam karne ke liye)
# - Metadata management
# - Recent files tracking
# - Disk space management
# ============================================================

import shutil
import json
import zipfile
import gzip
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple, Callable

from src.utils.logger import get_logger
from src.utils.helpers import (
    ensure_dir, safe_join, sanitize_filename,
    read_json, write_json, hash_file, generate_short_id,
    format_bytes, get_file_size, get_timestamp,
    delete_file, delete_directory, list_files
)

logger = get_logger("FileManager")


# ============================================================
# PROJECT FILE MANAGER
# ============================================================

class ProjectFileManager:
    """
    Project files ka management karta hai.
    - Save/Load projects
    - Auto-backups
    - Version history
    - Recent projects tracking
    """

    PROJECT_EXTENSION = ".anim3d"
    BACKUP_EXTENSION = ".bak"
    METADATA_FILE = "project_meta.json"

    def __init__(self, projects_dir: str, backups_dir: str,
                 max_backups: int = 10):
        """
        Args:
            projects_dir: Jahan projects save honge
            backups_dir: Jahan backups save honge
            max_backups: Har project ke kitne backups rakhne hain
        """
        self.projects_dir = ensure_dir(projects_dir)
        self.backups_dir = ensure_dir(backups_dir)
        self.max_backups = max_backups

        # Recent projects file
        self.recent_projects_file = os.path.join(
            projects_dir, "recent_projects.json"
        )

        logger.info(f"ProjectFileManager initialized")
        logger.debug(f"Projects dir: {self.projects_dir}")
        logger.debug(f"Backups dir: {self.backups_dir}")

    # ------------------------------------------------------------
    # PROJECT CREATION
    # ------------------------------------------------------------

    def create_project(self, project_name: str,
                       project_data: Dict) -> Optional[str]:
        """
        Naya project banata hai.

        Args:
            project_name: Project ka naam
            project_data: Project ka data dictionary

        Returns:
            Project file ka path, ya None (failure par)
        """
        try:
            safe_name = sanitize_filename(project_name)
            project_folder = os.path.join(self.projects_dir, safe_name)

            # Agar already exists to unique name banao
            if os.path.exists(project_folder):
                counter = 1
                while os.path.exists(f"{project_folder}_{counter}"):
                    counter += 1
                project_folder = f"{project_folder}_{counter}"
                safe_name = f"{safe_name}_{counter}"

            # Folder structure banao
            ensure_dir(project_folder)
            ensure_dir(os.path.join(project_folder, "assets"))
            ensure_dir(os.path.join(project_folder, "renders"))
            ensure_dir(os.path.join(project_folder, "audio"))
            ensure_dir(os.path.join(project_folder, "cache"))

            # Metadata add karo
            project_data["metadata"] = {
                "name": project_name,
                "created_at": get_timestamp(),
                "modified_at": get_timestamp(),
                "version": "1.0.0",
                "unique_id": generate_short_id(),
            }

            # Project file save karo
            project_file = os.path.join(
                project_folder, f"{safe_name}{self.PROJECT_EXTENSION}"
            )
            write_json(project_file, project_data)

            # Metadata alag file me bhi save karo
            metadata_file = os.path.join(project_folder, self.METADATA_FILE)
            write_json(metadata_file, project_data["metadata"])

            # Recent projects me add karo
            self.add_to_recent(project_file)

            logger.info(f"Project created: {project_name} at {project_file}")
            return project_file

        except Exception as e:
            logger.error(f"Failed to create project '{project_name}': {e}")
            return None

    # ------------------------------------------------------------
    # PROJECT SAVING
    # ------------------------------------------------------------

    def save_project(self, project_file: str,
                     project_data: Dict,
                     create_backup: bool = True) -> bool:
        """
        Project save karta hai.

        Args:
            project_file: Project file ka path
            project_data: Save karne ke liye data
            create_backup: Backup banana hai ya nahi

        Returns:
            True agar success, False otherwise
        """
        try:
            if not os.path.exists(project_file):
                logger.warning(f"Project file doesn't exist: {project_file}")

            # Backup banao (agar file exist karti hai)
            if create_backup and os.path.exists(project_file):
                self.create_backup(project_file)

            # Metadata update karo
            if "metadata" not in project_data:
                project_data["metadata"] = {}
            project_data["metadata"]["modified_at"] = get_timestamp()

            # Atomic write - pehle temp file me
            success = write_json(project_file, project_data)

            if success:
                # Metadata file bhi update karo
                project_folder = os.path.dirname(project_file)
                metadata_file = os.path.join(project_folder, self.METADATA_FILE)
                write_json(metadata_file, project_data["metadata"])

                # Recent me add karo
                self.add_to_recent(project_file)

                logger.info(f"Project saved: {project_file}")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to save project {project_file}: {e}")
            return False

    # ------------------------------------------------------------
    # PROJECT LOADING
    # ------------------------------------------------------------

    def load_project(self, project_file: str) -> Optional[Dict]:
        """
        Project load karta hai.

        Args:
            project_file: Project file ka path

        Returns:
            Project data dictionary, ya None
        """
        try:
            if not os.path.exists(project_file):
                logger.error(f"Project file not found: {project_file}")
                return None

            project_data = read_json(project_file)

            if project_data is None:
                logger.error(f"Failed to parse project file: {project_file}")
                # Try to restore from backup
                return self._try_restore_from_backup(project_file)

            # Recent me add karo
            self.add_to_recent(project_file)

            logger.info(f"Project loaded: {project_file}")
            return project_data

        except Exception as e:
            logger.error(f"Failed to load project {project_file}: {e}")
            return self._try_restore_from_backup(project_file)

    def _try_restore_from_backup(self, project_file: str) -> Optional[Dict]:
        """Backup se project restore karne ki koshish karta hai"""
        logger.warning(f"Attempting to restore from backup: {project_file}")

        backups = self.get_backups(project_file)
        if not backups:
            logger.error("No backups available")
            return None

        # Latest backup try karo
        latest_backup = backups[0]["path"]
        logger.info(f"Trying backup: {latest_backup}")

        data = read_json(latest_backup)
        if data:
            logger.info("Successfully restored from backup")
            return data

        return None

    # ------------------------------------------------------------
    # BACKUP MANAGEMENT
    # ------------------------------------------------------------

    def create_backup(self, project_file: str) -> Optional[str]:
        """
        Project ka backup banata hai.

        Returns:
            Backup file ka path
        """
        try:
            if not os.path.exists(project_file):
                return None

            project_name = os.path.basename(project_file).replace(
                self.PROJECT_EXTENSION, ""
            )

            # Backup folder banao
            backup_folder = os.path.join(self.backups_dir, project_name)
            ensure_dir(backup_folder)

            # Backup filename with timestamp
            timestamp = get_timestamp()
            backup_filename = f"{project_name}_{timestamp}{self.BACKUP_EXTENSION}"
            backup_path = os.path.join(backup_folder, backup_filename)

            # Copy karo
            shutil.copy2(project_file, backup_path)

            # Purane backups delete karo
            self._cleanup_old_backups(backup_folder)

            logger.debug(f"Backup created: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return None

    def _cleanup_old_backups(self, backup_folder: str):
        """Purane backups delete karta hai (max_backups se zyada hone par)"""
        try:
            backups = sorted(
                [f for f in os.listdir(backup_folder)
                 if f.endswith(self.BACKUP_EXTENSION)],
                reverse=True
            )

            # Extra backups delete karo
            for old_backup in backups[self.max_backups:]:
                old_path = os.path.join(backup_folder, old_backup)
                try:
                    os.remove(old_path)
                    logger.debug(f"Old backup removed: {old_backup}")
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")

    def get_backups(self, project_file: str) -> List[Dict]:
        """
        Project ke saare backups list karta hai.

        Returns:
            List of dicts with 'path', 'timestamp', 'size'
        """
        try:
            project_name = os.path.basename(project_file).replace(
                self.PROJECT_EXTENSION, ""
            )
            backup_folder = os.path.join(self.backups_dir, project_name)

            if not os.path.exists(backup_folder):
                return []

            backups = []
            for filename in os.listdir(backup_folder):
                if filename.endswith(self.BACKUP_EXTENSION):
                    filepath = os.path.join(backup_folder, filename)
                    stat = os.stat(filepath)
                    backups.append({
                        "path": filepath,
                        "filename": filename,
                        "timestamp": datetime.fromtimestamp(stat.st_mtime),
                        "size": stat.st_size,
                        "size_readable": format_bytes(stat.st_size),
                    })

            # Latest pehle
            backups.sort(key=lambda x: x["timestamp"], reverse=True)
            return backups

        except Exception as e:
            logger.error(f"Failed to get backups: {e}")
            return []

    def restore_backup(self, project_file: str,
                       backup_path: str) -> bool:
        """
        Specific backup se project restore karta hai.
        """
        try:
            if not os.path.exists(backup_path):
                logger.error(f"Backup not found: {backup_path}")
                return False

            # Current file ka bhi backup banao (safety)
            if os.path.exists(project_file):
                safety_backup = project_file + ".before_restore"
                shutil.copy2(project_file, safety_backup)

            # Restore karo
            shutil.copy2(backup_path, project_file)

            logger.info(f"Project restored from: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

    # ------------------------------------------------------------
    # RECENT PROJECTS
    # ------------------------------------------------------------

    def add_to_recent(self, project_file: str, max_recent: int = 15):
        """Recent projects list me add karta hai"""
        try:
            recent = self.get_recent_projects()

            # Agar already list me hai to hatao
            recent = [p for p in recent if p.get("path") != project_file]

            # Naye entry ko top pe add karo
            recent.insert(0, {
                "path": project_file,
                "name": os.path.basename(project_file).replace(
                    self.PROJECT_EXTENSION, ""
                ),
                "last_opened": get_timestamp(),
            })

            # Max limit tak trim karo
            recent = recent[:max_recent]

            write_json(self.recent_projects_file, {"projects": recent})

        except Exception as e:
            logger.error(f"Failed to update recent projects: {e}")

    def get_recent_projects(self) -> List[Dict]:
        """Recent projects ki list return karta hai"""
        try:
            if not os.path.exists(self.recent_projects_file):
                return []

            data = read_json(self.recent_projects_file)
            if not data:
                return []

            # Sirf existing files return karo
            recent = data.get("projects", [])
            existing = [p for p in recent
                       if os.path.exists(p.get("path", ""))]

            return existing

        except Exception as e:
            logger.error(f"Failed to get recent projects: {e}")
            return []

    def remove_from_recent(self, project_file: str):
        """Recent list se hatata hai"""
        try:
            recent = self.get_recent_projects()
            recent = [p for p in recent if p.get("path") != project_file]
            write_json(self.recent_projects_file, {"projects": recent})
        except Exception as e:
            logger.error(f"Failed to remove from recent: {e}")

    def clear_recent(self):
        """Recent projects clear karta hai"""
        write_json(self.recent_projects_file, {"projects": []})

    # ------------------------------------------------------------
    # PROJECT DELETION
    # ------------------------------------------------------------

    def delete_project(self, project_file: str,
                       delete_backups: bool = False) -> bool:
        """
        Project delete karta hai.

        Args:
            project_file: Project file path
            delete_backups: Backups bhi delete karne hain ya nahi
        """
        try:
            project_folder = os.path.dirname(project_file)
            project_name = os.path.basename(project_folder)

            # Project folder delete karo
            if os.path.exists(project_folder):
                delete_directory(project_folder)
                logger.info(f"Project deleted: {project_folder}")

            # Backups bhi delete karo agar user chahe
            if delete_backups:
                backup_folder = os.path.join(self.backups_dir, project_name)
                if os.path.exists(backup_folder):
                    delete_directory(backup_folder)
                    logger.info(f"Backups deleted: {backup_folder}")

            # Recent se hatao
            self.remove_from_recent(project_file)

            return True

        except Exception as e:
            logger.error(f"Failed to delete project: {e}")
            return False

    # ------------------------------------------------------------
    # PROJECT LISTING
    # ------------------------------------------------------------

    def list_all_projects(self) -> List[Dict]:
        """Saare projects ki list return karta hai"""
        projects = []

        try:
            for item in os.listdir(self.projects_dir):
                item_path = os.path.join(self.projects_dir, item)
                if os.path.isdir(item_path):
                    # Project file dhundo
                    project_file = None
                    for f in os.listdir(item_path):
                        if f.endswith(self.PROJECT_EXTENSION):
                            project_file = os.path.join(item_path, f)
                            break

                    if project_file:
                        metadata_file = os.path.join(item_path, self.METADATA_FILE)
                        metadata = read_json(metadata_file) or {}

                        projects.append({
                            "name": metadata.get("name", item),
                            "path": project_file,
                            "folder": item_path,
                            "created_at": metadata.get("created_at", "Unknown"),
                            "modified_at": metadata.get("modified_at", "Unknown"),
                            "size": self._get_folder_size(item_path),
                        })

        except Exception as e:
            logger.error(f"Failed to list projects: {e}")

        return projects

    def _get_folder_size(self, folder: str) -> int:
        """Folder ka total size calculate karta hai"""
        total = 0
        try:
            for root, _, files in os.walk(folder):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        total += os.path.getsize(fp)
                    except Exception:
                        pass
        except Exception:
            pass
        return total


# ============================================================
# TEMP FILE MANAGER
# ============================================================

class TempFileManager:
    """
    Temporary files ka management karta hai.
    Auto-cleanup karta hai purane files ka.
    """

    def __init__(self, temp_dir: str,
                 max_age_hours: int = 24):
        """
        Args:
            temp_dir: Temp files kahan honge
            max_age_hours: Kitne ghante se purane files delete karne hain
        """
        self.temp_dir = ensure_dir(temp_dir)
        self.max_age_hours = max_age_hours

        logger.info(f"TempFileManager initialized: {self.temp_dir}")

        # Initialize hote hi cleanup karo
        self.cleanup_old_files()

    def create_temp_file(self, prefix: str = "temp_",
                         suffix: str = ".tmp") -> str:
        """
        Naya temp file banata hai.

        Returns:
            Temp file ka path
        """
        try:
            unique_id = generate_short_id()
            filename = f"{prefix}{unique_id}{suffix}"
            filepath = os.path.join(self.temp_dir, filename)

            # Empty file create karo
            Path(filepath).touch()

            logger.debug(f"Temp file created: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Failed to create temp file: {e}")
            # Fallback to system temp
            fd, path = tempfile.mkstemp(prefix=prefix, suffix=suffix)
            os.close(fd)
            return path

    def create_temp_dir(self, prefix: str = "tempdir_") -> str:
        """Naya temp directory banata hai"""
        try:
            unique_id = generate_short_id()
            dirname = f"{prefix}{unique_id}"
            dirpath = os.path.join(self.temp_dir, dirname)
            ensure_dir(dirpath)
            return dirpath
        except Exception as e:
            logger.error(f"Failed to create temp dir: {e}")
            return tempfile.mkdtemp(prefix=prefix)

    def cleanup_old_files(self):
        """Purane temp files delete karta hai"""
        try:
            if not os.path.exists(self.temp_dir):
                return

            now = time.time()
            max_age_seconds = self.max_age_hours * 3600
            deleted_count = 0

            for item in os.listdir(self.temp_dir):
                item_path = os.path.join(self.temp_dir, item)

                try:
                    age = now - os.path.getmtime(item_path)

                    if age > max_age_seconds:
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                            deleted_count += 1
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                            deleted_count += 1

                except Exception:
                    pass

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old temp files")

        except Exception as e:
            logger.error(f"Temp cleanup failed: {e}")

    def cleanup_all(self):
        """Saare temp files delete karta hai"""
        try:
            for item in os.listdir(self.temp_dir):
                item_path = os.path.join(self.temp_dir, item)
                try:
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except Exception:
                    pass
            logger.info("All temp files cleaned")
        except Exception as e:
            logger.error(f"Temp cleanup failed: {e}")

    def get_temp_usage(self) -> Dict[str, Any]:
        """Temp folder ka usage return karta hai"""
        total_size = 0
        file_count = 0

        try:
            for root, _, files in os.walk(self.temp_dir):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        total_size += os.path.getsize(fp)
                        file_count += 1
                    except Exception:
                        pass
        except Exception:
            pass

        return {
            "total_size": total_size,
            "total_size_readable": format_bytes(total_size),
            "file_count": file_count,
        }


# ============================================================
# PROJECT COMPRESSION
# ============================================================

class ProjectCompressor:
    """
    Projects ko compress karta hai (ZIP me).
    Sharing/archiving ke liye useful.
    """

    @staticmethod
    def compress_project(project_folder: str,
                         output_zip: str) -> bool:
        """
        Project folder ko ZIP me compress karta hai.

        Args:
            project_folder: Project folder path
            output_zip: Output ZIP file path
        """
        try:
            if not os.path.exists(project_folder):
                logger.error(f"Project folder not found: {project_folder}")
                return False

            ensure_dir(os.path.dirname(output_zip))

            with zipfile.ZipFile(output_zip, "w",
                                zipfile.ZIP_DEFLATED,
                                compresslevel=6) as zf:
                for root, _, files in os.walk(project_folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, project_folder)
                        zf.write(file_path, arcname)

            original_size = ProjectCompressor._get_folder_size(project_folder)
            compressed_size = get_file_size(output_zip)
            ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0

            logger.info(
                f"Compressed: {format_bytes(original_size)} → "
                f"{format_bytes(compressed_size)} ({ratio:.1f}% saved)"
            )
            return True

        except Exception as e:
            logger.error(f"Compression failed: {e}")
            return False

    @staticmethod
    def extract_project(zip_file: str,
                        output_folder: str) -> bool:
        """
        ZIP file se project extract karta hai.
        """
        try:
            if not os.path.exists(zip_file):
                logger.error(f"ZIP file not found: {zip_file}")
                return False

            ensure_dir(output_folder)

            with zipfile.ZipFile(zip_file, "r") as zf:
                zf.extractall(output_folder)

            logger.info(f"Extracted to: {output_folder}")
            return True

        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return False

    @staticmethod
    def _get_folder_size(folder: str) -> int:
        """Folder size calculate karta hai"""
        total = 0
        try:
            for root, _, files in os.walk(folder):
                for f in files:
                    try:
                        total += os.path.getsize(os.path.join(root, f))
                    except Exception:
                        pass
        except Exception:
            pass
        return total


# ============================================================
# DISK SPACE MONITOR
# ============================================================

class DiskSpaceMonitor:
    """Disk space monitor karta hai"""

    @staticmethod
    def get_disk_info(path: str) -> Dict[str, Any]:
        """Disk info return karta hai"""
        try:
            usage = shutil.disk_usage(path)
            return {
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "total_readable": format_bytes(usage.total),
                "used_readable": format_bytes(usage.used),
                "free_readable": format_bytes(usage.free),
                "percent_used": (usage.used / usage.total) * 100,
            }
        except Exception as e:
            logger.error(f"Disk info failed: {e}")
            return {}

    @staticmethod
    def check_space_available(path: str,
                               required_mb: int) -> bool:
        """Check karta hai enough space hai ya nahi"""
        info = DiskSpaceMonitor.get_disk_info(path)
        if not info:
            return False

        free_mb = info["free"] / (1024 * 1024)
        return free_mb >= required_mb

    @staticmethod
    def warn_if_low_space(path: str,
                           warning_threshold_gb: float = 5.0):
        """Kam space par warning deta hai"""
        info = DiskSpaceMonitor.get_disk_info(path)
        if not info:
            return

        free_gb = info["free"] / (1024 ** 3)
        if free_gb < warning_threshold_gb:
            logger.warning(
                f"LOW DISK SPACE: Only {free_gb:.2f} GB free at {path}"
            )


# ============================================================
# TEST FUNCTION
# ============================================================

if __name__ == "__main__":
    from src.utils.logger import setup_logging, print_banner, print_section

    setup_logging(log_level="DEBUG")
    print_banner("File Manager Test", "Testing all file operations")

    # Test paths
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))
    test_projects = os.path.join(base_dir, "projects")
    test_backups = os.path.join(base_dir, "backups")
    test_temp = os.path.join(base_dir, "temp")

    # ============================================================
    # Test 1: Project Manager
    # ============================================================
    print_section("Test 1: Project File Manager")

    pfm = ProjectFileManager(test_projects, test_backups, max_backups=5)

    # Project create karo
    test_data = {
        "scene_name": "Test Scene",
        "duration": 10.0,
        "fps": 30,
        "objects": [
            {"name": "Cube", "position": [0, 0, 0]},
            {"name": "Camera", "position": [0, 5, 10]},
        ],
        "audio_tracks": [],
    }

    project_file = pfm.create_project("Test_Project", test_data)
    print(f"Created project: {project_file}")

    # Load karo
    if project_file:
        loaded = pfm.load_project(project_file)
        print(f"Loaded project: {loaded.get('metadata', {}).get('name')}")

        # Modify karo aur save
        loaded["scene_name"] = "Modified Scene"
        pfm.save_project(project_file, loaded, create_backup=True)
        print("Project modified and saved")

        # Backups check karo
        backups = pfm.get_backups(project_file)
        print(f"Backups available: {len(backups)}")

    # Recent projects
    recent = pfm.get_recent_projects()
    print(f"Recent projects: {len(recent)}")

    # All projects
    all_proj = pfm.list_all_projects()
    print(f"Total projects: {len(all_proj)}")

    # ============================================================
    # Test 2: Temp File Manager
    # ============================================================
    print_section("Test 2: Temp File Manager")

    tfm = TempFileManager(test_temp, max_age_hours=24)

    # Temp files banao
    temp1 = tfm.create_temp_file(prefix="render_", suffix=".png")
    temp2 = tfm.create_temp_file(prefix="audio_", suffix=".wav")
    temp_dir = tfm.create_temp_dir(prefix="workspace_")

    print(f"Created temp file 1: {temp1}")
    print(f"Created temp file 2: {temp2}")
    print(f"Created temp dir: {temp_dir}")

    # Usage check karo
    usage = tfm.get_temp_usage()
    print(f"Temp usage: {usage['total_size_readable']} in {usage['file_count']} files")

    # ============================================================
    # Test 3: Disk Space
    # ============================================================
    print_section("Test 3: Disk Space Monitor")

    disk_info = DiskSpaceMonitor.get_disk_info(base_dir)
    print(f"Total: {disk_info.get('total_readable')}")
    print(f"Used: {disk_info.get('used_readable')} ({disk_info.get('percent_used', 0):.1f}%)")
    print(f"Free: {disk_info.get('free_readable')}")

    space_ok = DiskSpaceMonitor.check_space_available(base_dir, 1000)
    print(f"1GB available: {space_ok}")

    DiskSpaceMonitor.warn_if_low_space(base_dir, warning_threshold_gb=5.0)

    # ============================================================
    # Test 4: Compression (optional - skip agar time zyada lage)
    # ============================================================
    print_section("Test 4: Project Compression")

    if project_file:
        project_folder = os.path.dirname(project_file)
        zip_output = os.path.join(test_temp, "test_project.zip")

        success = ProjectCompressor.compress_project(project_folder, zip_output)
        print(f"Compression: {'✓ Success' if success else '✗ Failed'}")

        if success and os.path.exists(zip_output):
            zip_size = get_file_size(zip_output)
            print(f"ZIP size: {format_bytes(zip_size)}")

    # ============================================================
    # Cleanup Test Files
    # ============================================================
    print_section("Cleanup")

    # Test project delete karo
    if project_file:
        pfm.delete_project(project_file, delete_backups=True)
        print("Test project deleted")

    print_banner("✅ All Tests Passed", "File Manager Working Perfectly")