import sys
import os
from pathlib import Path

_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)


def create_folders_and_guide():
    print("\n" + "=" * 60)
    print("AI CHARACTER SETUP GUIDE")
    print("=" * 60)
    
    chars_dir = Path(_project_root) / "assets" / "characters"
    chars_dir.mkdir(parents=True, exist_ok=True)
    
    characters = {
        "hero": {
            "name": "HERO",
            "prompt": "3D cartoon character full body, young Indian male, confident pose, modern clothes, white background, Pixar style, standing straight, smiling, brown hair, casual jacket, jeans, professional 3D render, studio lighting, high quality"
        },
        "heroine": {
            "name": "HEROINE",
            "prompt": "3D cartoon character full body, young Indian female, friendly pose, modern clothes, white background, Pixar style, standing straight, smiling, long hair, casual top, jeans, professional 3D render, studio lighting, high quality"
        },
        "villain": {
            "name": "VILLAIN",
            "prompt": "3D cartoon character full body, adult male villain, menacing pose, dark clothes, white background, Pixar style, arms crossed, serious expression, black hair, dark jacket, dark pants, professional 3D render, high quality"
        },
        "child": {
            "name": "CHILD",
            "prompt": "3D cartoon character full body, small child aged 8, happy pose, colorful clothes, white background, Pixar style, big smile, messy hair, t-shirt, shorts, professional 3D render, cute, high quality"
        },
        "old_man": {
            "name": "OLD_MAN",
            "prompt": "3D cartoon character full body, elderly wise man, calm pose, traditional clothes, white background, Pixar style, gentle smile, white hair, beard, glasses, formal wear, professional 3D render, high quality"
        },
        "narrator": {
            "name": "NARRATOR",
            "prompt": "3D cartoon character full body, mature male storyteller, calm pose, casual clothes, white background, Pixar style, thoughtful expression, brown hair, sweater, jeans, professional 3D render, high quality"
        },
    }
    
    for folder_name, info in characters.items():
        char_folder = chars_dir / folder_name
        char_folder.mkdir(exist_ok=True)
        
        readme = char_folder / "GENERATE_PROMPT.md"
        content = f"""# {info['name']} - AI Character Generation

## Instructions:

1. Go to: https://www.bing.com/images/create
2. Sign in with Microsoft account (free)
3. Copy the prompt below
4. Click Create
5. Wait 30 seconds
6. Download the best image
7. Save it as: idle.png in this folder

## Copy This Prompt:

{info['prompt']}

## Save Location:

Save the downloaded image as:
{char_folder / 'idle.png'}

## Recommended Files (Optional):

Create these poses for full animation:
- idle.png - Standing pose (REQUIRED)
- happy.png - Happy expression
- angry.png - Angry expression
- sad.png - Sad expression
- surprised.png - Surprised expression

## Tips:

- Use PNG format
- Size: 512x768 or higher
- Full body visible
- White or simple background
"""
        readme.write_text(content, encoding='utf-8')
        
        print(f"✅ Created: {folder_name}/")
        print(f"   Prompt file added")
    
    main_readme = chars_dir / "README.md"
    main_content = """# Character Assets

## AI-Generated Characters Setup

### Quick Start:

1. Open Bing Image Creator (FREE):
   https://www.bing.com/images/create

2. For each character folder, open its GENERATE_PROMPT.md

3. Copy the prompt and paste in Bing

4. Generate (30 seconds)

5. Download best image

6. Save as idle.png in the character folder

### Character Folders:

- hero/ - Main hero character
- heroine/ - Female lead
- villain/ - Antagonist
- child/ - Young child
- old_man/ - Elder character
- narrator/ - Storyteller

### Free AI Sources:

- Bing Image Creator: https://www.bing.com/images/create
- Leonardo.AI: https://leonardo.ai/
- Playground AI: https://playgroundai.com/
- Stable Diffusion: https://stablediffusionweb.com/

### Image Requirements:

- Format: PNG
- Size: 512x768 or higher
- Full body: Head to toe visible
- Style: Consistent (all same style)
"""
    main_readme.write_text(main_content, encoding='utf-8')
    
    print("\n" + "=" * 60)
    print("SETUP COMPLETE!")
    print("=" * 60)
    print(f"\nFolder: {chars_dir.absolute()}")
    print("\nNext Steps:")
    print("1. Open the folder (opening now...)")
    print("2. Read README.md")
    print("3. For each character, open GENERATE_PROMPT.md")
    print("4. Use Bing Image Creator (FREE)")
    print("5. Save images as idle.png")
    
    try:
        os.startfile(str(chars_dir.absolute()))
        print("\nFolder opened!")
    except:
        pass


if __name__ == "__main__":
    print("\n" + "#" * 60)
    print("#    AI CHARACTER SETUP")
    print("#" * 60)
    
    create_folders_and_guide()
    
    print("\n" + "=" * 60)
    print("Ready to generate characters!")
    print("=" * 60)