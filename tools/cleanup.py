# ============================================================
# tools/cleanup.py
# Delete unused files and folders
# ============================================================

import os
import shutil
from pathlib import Path

_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)


# Files to delete
FILES_TO_DELETE = [
    # Old video generators
    "src/pipeline/video_generator_v2.py",
    "src/pipeline/video_generator_v3.py",
    "src/pipeline/video_generator_v5.py",
    
    # Test scripts (not needed anymore)
    "tools/test_tts_basic.py",
    "tools/test_current_tts.py",
    "tools/test_tts_proper.py",
    "tools/test_full_pipeline.py",
    "tools/deep_debug_audio.py",
    "tools/make_video_manual.py",
    "tools/test_hindi_voices.py",
    "tools/test_transliteration.py",
    "tools/test_native_hindi.py",
    "tools/fix_hindi_font.py",
    "tools/fix_tts_integration.py",
    "tools/check_menu.py",
    "tools/fix_shortcut.py",
    "tools/integrate_v2.py",
    "tools/integrate_v4.py",
    "tools/test_dicebear.py",
    "tools/download_characters.py",
    "tools/download_real_characters.py",
    
    # Root folder files
    "test_output.wav",
    "test_video.mp4",
    "temp_music.wav",
    "premium_characters_preview.png",
    "concat_list.txt",
    "extracted_test_audio.wav",
]

# Folders to delete
FOLDERS_TO_DELETE = [
    "manual_test",
    "manual_test_v2",
    "hindi_test",
    "hindi_fixed",
    "avatar_tests",
    "font_tests",
]

# Also cleanup temp folder contents (but keep folder)
CLEAN_FOLDERS = [
    "temp",
]


def delete_files():
    """Delete listed files"""
    print("\n" + "=" * 60)
    print("DELETING UNUSED FILES")
    print("=" * 60)
    
    deleted = 0
    not_found = 0
    
    for file_path in FILES_TO_DELETE:
        full_path = os.path.join(_project_root, file_path)
        
        if os.path.exists(full_path):
            try:
                # Get file size before deleting
                size = os.path.getsize(full_path)
                os.remove(full_path)
                print(f"  ✅ Deleted: {file_path} ({size:,} bytes)")
                deleted += 1
            except Exception as e:
                print(f"  ❌ Failed: {file_path} - {e}")
        else:
            not_found += 1
    
    print(f"\n  Summary: {deleted} deleted, {not_found} not found")


def delete_folders():
    """Delete listed folders"""
    print("\n" + "=" * 60)
    print("DELETING UNUSED FOLDERS")
    print("=" * 60)
    
    deleted = 0
    not_found = 0
    total_freed = 0
    
    for folder in FOLDERS_TO_DELETE:
        folder_path = os.path.join(_project_root, folder)
        
        if os.path.exists(folder_path):
            try:
                # Calculate size
                size = 0
                for dirpath, dirnames, filenames in os.walk(folder_path):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        size += os.path.getsize(fp)
                
                shutil.rmtree(folder_path)
                print(f"  ✅ Deleted: {folder}/ ({size/1024:.1f} KB)")
                deleted += 1
                total_freed += size
            except Exception as e:
                print(f"  ❌ Failed: {folder} - {e}")
        else:
            not_found += 1
    
    print(f"\n  Summary: {deleted} deleted, {not_found} not found")
    print(f"  Space freed: {total_freed/1024/1024:.2f} MB")


def clean_temp_folders():
    """Clean contents of temp folder"""
    print("\n" + "=" * 60)
    print("CLEANING TEMP FOLDERS")
    print("=" * 60)
    
    for folder in CLEAN_FOLDERS:
        folder_path = os.path.join(_project_root, folder)
        
        if os.path.exists(folder_path):
            print(f"\n  Cleaning: {folder}/")
            
            # Delete all contents
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                        print(f"    ✅ Deleted folder: {item}")
                    else:
                        os.remove(item_path)
                        print(f"    ✅ Deleted file: {item}")
                except Exception as e:
                    print(f"    ❌ Failed: {item} - {e}")


def clean_backups():
    """Delete old .backup files"""
    print("\n" + "=" * 60)
    print("CLEANING OLD BACKUP FILES")
    print("=" * 60)
    
    deleted = 0
    
    for root, dirs, files in os.walk(_project_root):
        # Skip venv, .git, etc
        dirs[:] = [d for d in dirs if d not in ['venv', '.git', '__pycache__', 'node_modules']]
        
        for file in files:
            if '.backup' in file or file.endswith('.backup'):
                file_path = os.path.join(root, file)
                try:
                    size = os.path.getsize(file_path)
                    os.remove(file_path)
                    rel_path = os.path.relpath(file_path, _project_root)
                    print(f"  ✅ Deleted: {rel_path}")
                    deleted += 1
                except Exception as e:
                    print(f"  ❌ Failed: {file} - {e}")
    
    print(f"\n  Total backup files deleted: {deleted}")


def show_disk_usage():
    """Show current disk usage"""
    print("\n" + "=" * 60)
    print("PROJECT SIZE")
    print("=" * 60)
    
    total = 0
    for root, dirs, files in os.walk(_project_root):
        # Skip venv
        dirs[:] = [d for d in dirs if d not in ['venv', '.git']]
        
        for file in files:
            try:
                total += os.path.getsize(os.path.join(root, file))
            except:
                pass
    
    print(f"\n  Total project size: {total/1024/1024:.2f} MB")
    print(f"  (excluding venv and .git)")


def main():
    print("\n" + "#" * 60)
    print("#    PROJECT CLEANUP")
    print("#" * 60)
    
    print("\nThis will delete:")
    print(f"  • {len(FILES_TO_DELETE)} unused files")
    print(f"  • {len(FOLDERS_TO_DELETE)} test folders")
    print(f"  • Contents of temp folders")
    print(f"  • Old backup files")
    print(f"\nAll KEEP files will be safe!")
    
    response = input("\nProceed with cleanup? (y/n): ").strip().lower()
    
    if response != 'y':
        print("Cancelled.")
        return
    
    # Do cleanup
    delete_files()
    delete_folders()
    clean_temp_folders()
    clean_backups()
    show_disk_usage()
    
    print("\n" + "=" * 60)
    print("✅ CLEANUP COMPLETE!")
    print("=" * 60)
    print("\nKept files:")
    print("  ✅ src/pipeline/quick_video.py")
    print("  ✅ src/pipeline/video_generator_v4.py")
    print("  ✅ src/pipeline/video_generator_v6.py")
    print("  ✅ src/pipeline/premium_character.py")
    print("  ✅ src/ai/voice_profiles.py")
    print("  ✅ src/audio/music_library.py")
    print("  ✅ tools/progress_tracker.py")


if __name__ == "__main__":
    main()