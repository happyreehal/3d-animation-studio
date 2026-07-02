import sys
import os
from pathlib import Path

_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)
sys.path.insert(0, _project_root)


def verify_characters():
    print("\n" + "=" * 60)
    print("CHARACTER IMAGES VERIFICATION")
    print("=" * 60)
    
    chars_dir = Path(_project_root) / "assets" / "characters"
    
    characters = ["hero", "heroine", "villain", "child", "old_man", "narrator"]
    
    all_good = True
    total_size = 0
    
    for char in characters:
        char_folder = chars_dir / char
        idle_file = char_folder / "idle.png"
        
        # Also check for .jpg or .jpeg
        alt_files = list(char_folder.glob("*.png")) + list(char_folder.glob("*.jpg")) + list(char_folder.glob("*.jpeg"))
        alt_files = [f for f in alt_files if f.name != "GENERATE_PROMPT.md"]
        
        print(f"\n📁 {char.upper()}/")
        
        if idle_file.exists():
            size = idle_file.stat().st_size
            total_size += size
            print(f"   ✅ idle.png ({size:,} bytes / {size/1024:.1f} KB)")
            
            # Check image
            try:
                from PIL import Image
                img = Image.open(idle_file)
                print(f"   📐 Size: {img.width}x{img.height}")
                print(f"   🎨 Mode: {img.mode}")
            except Exception as e:
                print(f"   ⚠️  Can't read image: {e}")
        elif alt_files:
            print(f"   ⚠️  idle.png NOT FOUND, but found:")
            for f in alt_files:
                print(f"      - {f.name} ({f.stat().st_size:,} bytes)")
            print(f"   💡 Rename to 'idle.png' or copy as 'idle.png'")
            all_good = False
        else:
            print(f"   ❌ NO IMAGES FOUND")
            all_good = False
    
    print("\n" + "=" * 60)
    if all_good:
        print("✅ ALL 6 CHARACTERS READY!")
        print(f"   Total size: {total_size/1024/1024:.2f} MB")
    else:
        print("⚠️  Some characters missing - see above")
    print("=" * 60)
    
    return all_good


def main():
    print("\n" + "#" * 60)
    print("#    VERIFY CHARACTER IMAGES")
    print("#" * 60)
    
    if verify_characters():
        print("\n🎉 Ready for V7! Character images all set!")
        print("\nNext step: Build V7 that uses these images")
    else:
        print("\n⚠️  Please save images as 'idle.png' in each folder")


if __name__ == "__main__":
    main()