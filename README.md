\# 🎬 3D Animation Studio



Free \& Open-Source 3D Animation Software for YouTube Content Creators



\## ✨ Features



\- 🎨 \*\*3D Rendering\*\* - OpenGL-based real-time rendering

\- 💡 \*\*13 Lighting Presets\*\* - Day, night, studio, dramatic

\- 📷 \*\*10 Camera Angles\*\* - Cinematic presets

\- ⚡ \*\*Physics Engine\*\* - Rigid body, collision detection

\- 👕 \*\*Cloth Simulation\*\* - Realistic fabric with 6 materials

\- 🔥 \*\*10 VFX Effects\*\* - Fire, smoke, rain, explosion

\- 🤖 \*\*AI Voice Generation\*\* - Multi-voice TTS (coming)

\- 👄 \*\*AI Lipsync\*\* - Automatic mouth animation (coming)

\- 🎞️ \*\*Timeline Editor\*\* - Full video editing (coming)

\- 📤 \*\*YouTube Integration\*\* - Direct upload (coming)



\## 🛠️ Tech Stack



\- \*\*Language\*\*: Python 3.11

\- \*\*GUI\*\*: PyQt5

\- \*\*3D Graphics\*\*: OpenGL, ModernGL

\- \*\*Physics\*\*: PyBullet

\- \*\*AI\*\*: Coqui TTS, Whisper

\- \*\*Video\*\*: FFmpeg



\## 📦 Installation



\### Prerequisites

\- Python 3.11+

\- FFmpeg

\- Git



\### Setup



```bash

\# Clone repository

git clone https://github.com/YOUR\_USERNAME/3d-animation-studio.git

cd 3d-animation-studio



\# Create virtual environment

py -3.11 -m venv venv

venv\\Scripts\\activate



\# Install dependencies

pip install -r requirements.txt



\# Install FFmpeg (Windows)

winget install Gyan.FFmpeg



\# Run the app

python main.py



📁 Project Structure

3d-animation-studio/

├── main.py                 # Entry point

├── config.json             # Configuration

├── src/

│   ├── utils/              # Helpers, logging, config

│   ├── core/               # Project \& asset management

│   ├── renderer/           # 3D rendering system

│   ├── physics/            # Physics \& VFX

│   ├── ai/                 # AI features (TTS, lipsync)

│   ├── audio/              # Audio system

│   ├── timeline/           # Timeline editor

│   ├── export/             # Video export

│   └── ui/                 # PyQt5 UI

└── assets/                 # 3D models, textures, audio



🚀 Progress

✅ 19 files complete (36% done)

🎯 33 files remaining

📊 25/55 features implemented

See PROJECT\_HANDOFF.md for detailed progress.



📝 License

MIT License - Free for personal and commercial use



🙏 Credits

Built with love using 100% free \& open-source libraries.



\*\*Save aur close\*\* (Ctrl+S, Ctrl+W).



\---



\## STEP 7: `PROJECT\_HANDOFF.md` Banao



Ye woh document hai jo naya AI padhega. Terminal me:



```bash

notepad PROJECT\_HANDOFF.md



\# 🎬 3D Animation Studio - Project Handoff Document



\## 🎯 PROJECT OVERVIEW



\*\*Project Name\*\*: 3D Animation Studio for YouTube Content Creators

\*\*Goal\*\*: Free open-source 3D animation software with AI features

\*\*Language\*\*: Python 3.11.9

\*\*License Model\*\*: 100% free, no paid tools/APIs

\*\*Rendering\*\*: Local (no cloud)

\*\*Target\*\*: 55 total features across 10 categories



\---



\## 💻 DEVELOPMENT ENVIRONMENT



\- \*\*OS\*\*: Windows 11

\- \*\*Python\*\*: 3.11.9 (in venv)

\- \*\*Editor\*\*: VS Code

\- \*\*GPU\*\*: Intel(R) Iris(R) Xe Graphics

\- \*\*OpenGL\*\*: 3.3.0

\- \*\*RAM\*\*: 7.72 GB

\- \*\*CPU\*\*: Intel i7 12-core



\### Setup Commands (already done):

```bash

py -3.11 -m venv venv

venv\\Scripts\\activate

pip install -r requirements.txt

winget install Gyan.FFmpeg



📦 INSTALLED DEPENDENCIES (Working)

Core: PyQt5, numpy, Pillow

3D Graphics: PyOpenGL, moderngl, moderngl-window, pyrr

3D Models: trimesh, pyglet

Physics: pybullet

Image: opencv-python, imageio, imageio-ffmpeg

Audio: librosa, soundfile, pydub, sounddevice

Video: ffmpeg-python

TTS (basic): pyttsx3, gTTS

Utilities: tqdm, colorama, psutil, requests, watchdog, jsonschema

Physics/Math: scipy



NOT YET installed (install when needed):



torch, torchvision, torchaudio (heavy, for advanced AI)

transformers, TTS (Coqui), openai-whisper

google-api-python-client



📁 PROJECT STRUCTURE

3d-animation-studio/

├── requirements.txt              ✅ DONE

├── config.json                   ✅ DONE

├── main.py                       ✅ DONE

├── PROJECT\_HANDOFF.md            (this file)

├── venv/                         (virtual environment)

├── logs/                         (auto-created)

├── projects/                     (user projects)

├── backups/                      (auto-backups)

├── temp/                         (temp files)

├── exports/                      (rendered videos)

├── cache/                        (caching)

├── assets/

│   ├── models/

│   ├── textures/

│   ├── audio/{music,sfx,ambient}/

│   ├── videos/

│   └── presets/{characters,scenes,animations,materials}/

└── src/

&#x20;   ├── \_\_init\_\_.py               ✅

&#x20;   ├── utils/                    ✅ COMPLETE

&#x20;   │   ├── \_\_init\_\_.py           ✅ (with all exports)

&#x20;   │   ├── helpers.py            ✅

&#x20;   │   ├── logger.py             ✅

&#x20;   │   ├── file\_manager.py       ✅

&#x20;   │   └── config\_manager.py     ✅

&#x20;   ├── core/                     ✅ MOSTLY COMPLETE

&#x20;   │   ├── \_\_init\_\_.py           ✅ (with all exports)

&#x20;   │   ├── project\_manager.py    ✅

&#x20;   │   ├── asset\_library.py      ✅

&#x20;   │   └── auto\_save.py          ✅

&#x20;   ├── renderer/                 🟡 PARTIALLY DONE (4/8)

&#x20;   │   ├── \_\_init\_\_.py           ✅ (empty, needs exports)

&#x20;   │   ├── render\_engine.py      ✅

&#x20;   │   ├── model\_loader.py       ✅

&#x20;   │   ├── lighting\_manager.py   ✅

&#x20;   │   ├── camera\_controller.py  ✅

&#x20;   │   ├── character\_system.py   ❌ TODO

&#x20;   │   ├── animation\_presets.py  ❌ TODO

&#x20;   │   ├── color\_grading.py      ❌ TODO

&#x20;   │   └── environment\_manager.py❌ TODO

&#x20;   ├── physics/                  ✅ COMPLETE

&#x20;   │   ├── \_\_init\_\_.py           ✅ (empty, needs exports)

&#x20;   │   ├── physics\_engine.py     ✅

&#x20;   │   ├── cloth\_simulation.py   ✅

&#x20;   │   └── vfx\_engine.py         ✅

&#x20;   ├── ai/                       ❌ NOT STARTED

&#x20;   │   ├── \_\_init\_\_.py           ✅ (empty)

&#x20;   │   ├── tts\_engine.py         ❌ TODO (NEXT)

&#x20;   │   ├── lipsync\_engine.py     ❌ TODO

&#x20;   │   ├── expression\_engine.py  ❌ TODO

&#x20;   │   └── subtitle\_generator.py ❌ TODO

&#x20;   ├── audio/                    ❌ NOT STARTED

&#x20;   │   ├── \_\_init\_\_.py           ✅ (empty)

&#x20;   │   ├── audio\_engine.py       ❌ TODO

&#x20;   │   ├── audio\_recorder.py     ❌ TODO

&#x20;   │   └── sound\_effects.py      ❌ TODO

&#x20;   ├── timeline/                 ❌ NOT STARTED

&#x20;   │   ├── \_\_init\_\_.py           ✅ (empty)

&#x20;   │   ├── timeline\_editor.py    ❌ TODO

&#x20;   │   ├── keyframe\_system.py    ❌ TODO

&#x20;   │   └── transitions.py        ❌ TODO

&#x20;   ├── ui/                       ❌ NOT STARTED

&#x20;   │   ├── \_\_init\_\_.py           ✅ (empty)

&#x20;   │   ├── main\_window.py        ❌ TODO

&#x20;   │   ├── viewport\_widget.py    ❌ TODO

&#x20;   │   ├── timeline\_widget.py    ❌ TODO

&#x20;   │   ├── scene\_hierarchy.py    ❌ TODO

&#x20;   │   ├── properties\_panel.py   ❌ TODO

&#x20;   │   ├── asset\_browser.py      ❌ TODO

&#x20;   │   ├── toolbar.py            ❌ TODO

&#x20;   │   ├── dialogs.py            ❌ TODO

&#x20;   │   ├── theme\_manager.py      ❌ TODO

&#x20;   │   └── shortcuts\_manager.py  ❌ TODO

&#x20;   └── export/                   ❌ NOT STARTED

&#x20;       ├── \_\_init\_\_.py           ✅ (empty)

&#x20;       ├── video\_exporter.py     ❌ TODO

&#x20;       ├── social\_media\_presets.py ❌ TODO

&#x20;       └── youtube\_uploader.py   ❌ TODO



✅ COMPLETED FILES - Detailed Info

1\. requirements.txt

All dependencies listed. Python 3.11 compatible versions.



2\. config.json

Full app configuration. Nested structure with sections:



app, paths, rendering, physics, lighting, environments

camera, audio, animation, vfx, color\_grading

export, ui, shortcuts, project\_defaults, youtube\_api

3\. main.py

Entry point with:



Path setup (adds project root + src to sys.path)

Directory auto-creation

Logging setup

Dependency checker

Qt Application with High DPI

Custom splash screen (dark blue theme, 700x400)

AnimationStudioApp class - initializes all subsystems

Placeholder window for when UI not built yet

Graceful cleanup on exit

4\. src/utils/helpers.py

Functions provided:



Path: get\_project\_root, ensure\_dir, safe\_join, sanitize\_filename, get\_file\_extension

File: read\_json, write\_json, copy\_file, delete\_file, delete\_directory, list\_files

Size: get\_file\_size, format\_bytes

Hash: generate\_uuid, generate\_short\_id, hash\_file, hash\_string

Math: clamp, lerp, map\_range, distance\_3d, distance\_2d, normalize\_angle

Angles: degrees\_to\_radians, radians\_to\_degrees

Color: rgb\_to\_hex, hex\_to\_rgb, rgb\_to\_normalized, normalized\_to\_rgb

Time: get\_timestamp, seconds\_to\_timecode, format\_duration, estimate\_time\_remaining

Validation: is\_supported\_model\_format, is\_supported\_image\_format, is\_supported\_audio\_format, is\_supported\_video\_format

System: get\_system\_info, get\_available\_ram\_mb, check\_gpu\_available

Timing: timeit decorator, Timer context manager

safe\_execute, calculate\_aspect\_ratio, resize\_maintain\_aspect

5\. src/utils/logger.py

Provides:



LoggerManager - Singleton class, centralized logging

ColoredFormatter - ANSI colors for console (dark theme friendly)

FileFormatter - Plain formatter for files

get\_logger(name) - Quick logger access

setup\_logging() - Initialize system

LogContext - Context manager for operations

print\_banner(title, subtitle), print\_section(name) - Pretty output

log\_exception, log\_performance

Features: File rotation (10MB), colored console, symbols (🔍ℹ️⚠️❌🔥), Windows ANSI support

6\. src/utils/file\_manager.py

Classes:



ProjectFileManager - Save/load .anim3d projects, backups (max 10), recent projects, atomic writes

TempFileManager - Auto-cleanup (24h old), create temp files/dirs

ProjectCompressor - ZIP compression/extraction

DiskSpaceMonitor - Disk usage tracking, low-space warnings

7\. src/utils/config\_manager.py

Classes:



ConfigManager - Singleton, dot notation access (config.get("rendering.fps"))

ConfigValidator - Type validation

Features: Auto-save, user preferences (separate file), observer pattern, env variable overrides, deep merge, reset to defaults, export/import

Global functions: get\_config(), init\_config()

8\. src/utils/\_\_init\_\_.py

Exports EVERYTHING from above modules for clean imports:

from src.utils import get\_logger, get\_config, ensure\_dir, ...



9\. src/core/project\_manager.py

Classes:



Command (base), SetValueCommand, AddObjectCommand, RemoveObjectCommand

UndoRedoManager - 100 command history, undo/redo stacks

Scene - Individual scene with objects, lights, cameras, audio, effects, timeline

Project - Multiple scenes, metadata, assets, export settings

ProjectManager - Main API for new/open/save/close projects, scene management, object CRUD

10\. src/core/asset\_library.py

Classes:



AssetCategory - Constants (MODEL, TEXTURE, AUDIO\_MUSIC, etc. — 10 categories)

Asset - Metadata (tags, favorites, usage tracking, description)

AssetLibrary - Auto-discovery scanning, search, filter, import (single/batch), stats

11\. src/core/auto\_save.py

Classes:



SaveState (constants), SaveEvent, SessionRecovery (crash recovery)

AutoSaveSystem - Background thread, configurable interval, pause/resume, listeners, dirty check callbacks

12\. src/core/\_\_init\_\_.py

Exports all Core classes cleanly.



13\. src/renderer/render\_engine.py

Classes:



RenderQuality - draft/medium/high/ultra with settings

Camera - View/projection matrices (perspective + orthographic)

DirectionalLight, AmbientLight

Mesh - vertex data, transform, material, OpenGL VAO/VBO/IBO

PrimitiveFactory - create\_cube(), create\_sphere(), create\_plane()

RenderStats - FPS, draw calls, triangles

RenderEngine - Main engine, framebuffer offscreen rendering, render\_to\_image(path)

Shaders: Vertex + fragment (with lighting), wireframe

Format: 8 floats per vertex \[x,y,z, nx,ny,nz, u,v]

KNOWN FIX: Fragment shader uses uv\_tint = vec3(v\_texcoord.x \* 0.001, ...) trick to prevent OpenGL from optimizing out texcoord attribute

KNOWN FIX: \_upload\_mesh() checks if attr in program before binding attributes

14\. src/renderer/model\_loader.py

Classes:



ModelInfo, BoundingBox

OBJParser - Native OBJ parser (fast, no dependencies)

TrimeshLoader - FBX/GLTF/DAE via trimesh

ModelLoader - Main API with caching (17ms → 1ms on cache hit), center/normalize options

15\. src/renderer/lighting\_manager.py

Classes:



LightType (enum), Light (base), DirectionalLight, PointLight, SpotLight, AmbientLight

LightingPresets - 13 presets: day\_outdoor, sunrise, sunset, night\_outdoor, night\_city, indoor\_warm, indoor\_cool, studio, dramatic, horror, forest, desert, snowy

TimeOfDay - Auto lighting from hour (dawn/morning/noon/dusk/night)

Season - Spring/summer/autumn/winter modifiers

LightingManager - Apply presets, transitions, apply\_to\_render\_engine()

16\. src/renderer/camera\_controller.py

Classes:



Easing - 12 easing functions (linear, ease\_in/out, cubic, sine, bounce, elastic)

CameraPresets - 10 presets: wide\_angle, close\_up, medium\_shot, over\_the\_shoulder, birds\_eye, low\_angle, dutch\_angle, worm\_eye, establishing\_shot, profile\_shot

CameraKeyframe, CameraAnimation - Keyframe-based animation

CameraShake - Earthquake/impact effects

CameraController - Main API: apply\_preset, transition\_to, track\_object, shake\_camera, manual controls (move/orbit/zoom/dolly)

17\. src/physics/physics\_engine.py

Classes:



BodyType (STATIC/DYNAMIC/KINEMATIC), ShapeType

PhysicsMaterial - Presets: wood, metal, rubber, ice, ground, bouncy

RigidBody, CollisionEvent, RaycastHit

PhysicsEngine - PyBullet wrapper: create\_box/sphere/cylinder/plane, apply\_force/impulse/torque, raycast, collision callbacks, gravity control

Simulation: 60 steps/second, DIRECT mode (no GUI)

18\. src/physics/cloth\_simulation.py

Classes:



ClothMaterial - 6 presets: cotton, silk, wool, leather, denim, chiffon

Particle, Constraint

ClothSimulation - Verlet integration, structural+shear+bend constraints, pinning (corners/top edge), wind, sphere collision

ClothManager - Multiple cloths

PERFORMANCE: 8x8-12x12 grids fast, 20x20 slow (\~6 FPS)

19\. src/physics/vfx\_engine.py

Classes:



EmitterShape (POINT/SPHERE/BOX/CONE/CIRCLE/LINE)

Particle, EmitterConfig, ParticleEmitter

VFXPresets - 10 effects: fire🔥, smoke💨, rain☔, snow❄️, sparkle✨, explosion💥, confetti🎉, fog🌫️, lightning⚡, blood\_splash🩸

VFXEngine - Manage multiple effects, create\_effect(name, position, intensity)

🎨 CONSISTENT CODE PATTERNS USED

Every module follows these patterns:



1\. Path Setup at Top

\# ===== PATH SETUP =====

import sys

import os

if \_\_name\_\_ == "\_\_main\_\_":

&#x20;   \_current\_dir = os.path.dirname(os.path.abspath(\_\_file\_\_))

&#x20;   \_project\_root = os.path.dirname(os.path.dirname(\_current\_dir))

&#x20;   if \_project\_root not in sys.path:

&#x20;       sys.path.insert(0, \_project\_root)

\# ======================



2\. Import Pattern

from src.utils import get\_logger, get\_config, ensure\_dir, ...

logger = get\_logger("ModuleName")





3\. Class Init Pattern

def \_\_init\_\_(self, config: Optional\[Dict] = None):

&#x20;   if config is None:

&#x20;       try:

&#x20;           self.config = get\_config().get\_all()

&#x20;       except Exception:

&#x20;           self.config = {}

&#x20;   else:

&#x20;       self.config = config



4\. Test Section at Bottom

if \_\_name\_\_ == "\_\_main\_\_":

&#x20;   from src.utils import setup\_logging, print\_banner, print\_section

&#x20;   setup\_logging(log\_level="DEBUG")

&#x20;   print\_banner("Module Test", "Description")

&#x20;   # ... tests ...

&#x20;   print\_banner("✅ All Tests Passed", "Module Working")



5\. Hindi Comments (Hinglish)

Comments in Hinglish for user's understanding: "Ye function X karta hai"



6\. Data Classes with Dataclass Decorator

@dataclass

class MyClass:

&#x20;   field: type = default



7\. Enum for Constants

class MyEnum(Enum):

&#x20;   VALUE = "value"



8\. Listener/Observer Pattern

self.\_listeners: List\[Callable] = \[]

def add\_listener(self, callback): ...

def \_notify\_listeners(self, event): ...



🚧 REMAINING FILES (33 files to build)

Priority Order:

AI Layer (5 files):



src/ai/tts\_engine.py - Multi-voice TTS (pyttsx3 + gTTS + Coqui)

src/ai/lipsync\_engine.py - Phoneme extraction, mouth shapes

src/ai/expression\_engine.py - Emotion → facial expression

src/ai/subtitle\_generator.py - Whisper for auto captions

src/ai/\_\_init\_\_.py - Exports

Audio Layer (4 files):



src/audio/audio\_engine.py - Playback, mixing

src/audio/audio\_recorder.py - Mic recording

src/audio/sound\_effects.py - SFX library, reverb, ambient sounds

src/audio/\_\_init\_\_.py

Timeline Layer (4 files):



src/timeline/timeline\_editor.py - Data model

src/timeline/keyframe\_system.py - Property keyframes

src/timeline/transitions.py - Fade/cut/dissolve

src/timeline/\_\_init\_\_.py

Export Layer (4 files):



src/export/video\_exporter.py - MP4/WebM via ffmpeg

src/export/social\_media\_presets.py - YouTube/Insta/TikTok formats

src/export/youtube\_uploader.py - Google API upload + metadata

src/export/\_\_init\_\_.py

UI Layer (11 files) - PyQt5 based:



src/ui/main\_window.py - QMainWindow with dockable panels

src/ui/viewport\_widget.py - 3D preview (QOpenGLWidget)

src/ui/timeline\_widget.py - Timeline UI

src/ui/scene\_hierarchy.py - Object list tree

src/ui/properties\_panel.py - Object properties editor

src/ui/asset\_browser.py - Asset library UI

src/ui/toolbar.py - Main toolbar

src/ui/dialogs.py - Import/export/settings dialogs

src/ui/theme\_manager.py - Dark theme, QSS stylesheets

src/ui/shortcuts\_manager.py - Keyboard shortcuts

src/ui/\_\_init\_\_.py

Renderer Extras (3 files):



src/renderer/character\_system.py - Character customization (clothing, colors)

src/renderer/animation\_presets.py - Walk/run/talk animations

src/renderer/color\_grading.py - Post-processing filters (vintage, dramatic, etc.)

Environment \& Extras (3 files):



src/renderer/environment\_manager.py - Forest/desert/city environments

src/renderer/storyboard.py - Storyboarding

src/core/batch\_renderer.py - Batch processing

🐛 KNOWN ISSUES / BUGS

Cloth simulation slow with 20x20 grid (\~6 FPS) — Use 8x8-12x12 for character clothing. Numba/Cython optimization possible later.



Qt::AA\_EnableHighDpiScaling warning in main.py — Cosmetic warning only. Fix: set attribute BEFORE creating QApplication (currently after).



VFX create\_effect() doesn't accept area\_size param — Test code had this, fixed by removing.



ensure\_dir needed in some test sections — Add to imports if missing.



RAM tight (0.75GB free during test) — User has 7.72GB total but often low free. Recommend closing other apps.



🎯 WHAT'S BEEN TESTED \& WORKING

Rendering Tests ✅:



Rendered 3D scene with cube+sphere+plane on green ground

OBJ file loaded and rendered (orange cube)

5 lighting presets compared visually (day\_outdoor, sunset, night, studio, dramatic)

7 camera angle presets rendered (wide, close-up, birds-eye, low-angle, etc.)

Physics Tests ✅:



Box, sphere, cylinder falling under gravity to ground

Collision events (739 total in test)

Raycasting (hit ground detected)

Force application (horizontal push worked)

Cloth Tests ✅:



Cotton sheet pinned at top, drooped under gravity

5 materials compared (silk floaty, wool stiff, chiffon most drape)

Flag with wind (X spread 0.96m, Y 3.08m, Z 2.01m)

Cloth draped over sphere obstacle

VFX Tests ✅:



Fire particles rising with color transition yellow→red→transparent

Explosion 300 particles → 0 auto-cleanup

Multiple effects simultaneously

Core Systems ✅:



Undo/redo working (position changes reverted correctly)

Save/load projects preserves all data

Auto-save fires on interval, recovery data created

Asset library scanning, favorites, tags all working



📊 CONFIG.JSON KEY SETTINGS

{

&#x20; "rendering": {

&#x20;   "default\_quality": "draft",

&#x20;   "default\_fps": 30,

&#x20;   "available\_fps": \[24, 30, 60]

&#x20; },

&#x20; "physics": {

&#x20;   "gravity": \[0, -9.81, 0],

&#x20;   "simulation\_steps": 60

&#x20; },

&#x20; "ui": {

&#x20;   "theme": "dark",

&#x20;   "accent\_color": "#00D4FF",

&#x20;   "auto\_save\_interval": 300

&#x20; }

}



🎨 UI DESIGN GUIDELINES (For Future UI Files)

Theme: Dark

Accent color: #00D4FF (cyan blue)

Background: #0F0F19 (very dark blue-gray)

Panel bg: #1A1A2E

Text: #FFFFFF primary, #8888AA secondary

Font: Segoe UI, 12pt

Style: Minimalist, professional (like Blender/DaVinci Resolve)

🚀 NEXT FILE TO BUILD

FILE 20: src/ai/tts\_engine.py



Requirements:



Support multiple TTS engines: pyttsx3 (offline, fast), gTTS (online, better quality), Coqui TTS (best quality, if installed)

Multi-voice: different voices per character

Multi-language: en, hi, es, fr, de, zh, ar, pt, ru, ja

Prosody control: speech rate, pitch, volume, pauses

Save to WAV file for use in timeline

Batch generation from script

Cache generated audio

Follow existing patterns:



PATH SETUP block at top

Import from src.utils

Test section at bottom with print\_banner/print\_section

Hinglish comments

Optional config parameter in init



🔗 IMPORTANT NOTES

All files must be self-testable - each has if \_\_name\_\_ == "\_\_main\_\_": section

Import from src.utils - never duplicate helper functions

Use existing patterns - don't invent new patterns

Test with existing files - new code must not break old tests

User speaks Hinglish - keep comments/messages friendly and mixed Hindi+English

User uses Windows CMD - use \\ in paths, python script.py commands

venv is activated - user always in (venv) prompt





END OF HANDOFF DOCUMENT



























































