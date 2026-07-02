# ============================================================
# tools/progress_tracker.py
# 3D Animation Studio - Auto Progress Tracker
# 100% Error-Free Progress Tracking System
# ============================================================

# ===== PATH SETUP =====
import sys
import os

_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
# ======================

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_NAME = "3D Animation Studio"
GITHUB_URL   = "https://github.com/happyreehal/3d-animation-studio"
OWNER        = "happyreehal"
TOTAL_DAYS   = 34
DAILY_HOURS  = 10
LANGUAGE     = "Hinglish (Hindi + English)"


# ============================================================
# COMPLETE PROJECT PLAN (Pre-defined)
# ============================================================

PROJECT_PLAN = {
    1: {
        "week": 1, "month": 1,
        "phase": "Audio System",
        "tasks": [
            "Install pyttsx3, gTTS, Coqui TTS",
            "Enable real TTS in tts_engine.py",
            "Setup multiple voice profiles",
            "Test voice generation for 6 characters"
        ]
    },
    2: {
        "week": 1, "month": 1,
        "phase": "Audio System",
        "tasks": [
            "Voice caching system",
            "Emotion-based voice modulation",
            "Voice speed/pitch control",
            "Save voices to cache folder"
        ]
    },
    3: {
        "week": 1, "month": 1,
        "phase": "Audio System",
        "tasks": [
            "FFmpeg audio pipeline setup",
            "Multi-track audio merging",
            "Volume normalization",
            "Fade in/out effects"
        ]
    },
    4: {
        "week": 1, "month": 1,
        "phase": "Audio System",
        "tasks": [
            "Audio-video synchronization",
            "Test perfect sync",
            "Fix timing issues",
            "Documentation"
        ]
    },
    5: {
        "week": 1, "month": 1,
        "phase": "Music & SFX",
        "tasks": [
            "Free music library integration",
            "Local music folder setup",
            "Music library organization",
            "Test music playback"
        ]
    },
    6: {
        "week": 1, "month": 1,
        "phase": "Music & SFX",
        "tasks": [
            "SFX library integration",
            "Auto music selection based on emotion",
            "Background music ducking",
            "Complete audio experience test"
        ]
    },
    7: {
        "week": 1, "month": 1,
        "phase": "Week 1 Review",
        "tasks": [
            "Bug fixes",
            "Test with sample scripts",
            "Git commit + GitHub push",
            "Create demo video"
        ]
    },
    8:  {"week": 2, "month": 1, "phase": "Lipsync", "tasks": ["Install openai-whisper", "Install librosa", "Phoneme extraction", "Timing detection"]},
    9:  {"week": 2, "month": 1, "phase": "Lipsync", "tasks": ["Viseme mapping", "Test lipsync data", "Frame-perfect timing", "Data structure"]},
    10: {"week": 2, "month": 1, "phase": "Expressions", "tasks": ["15 emotions mapping", "Eye movements", "Eyebrow expressions", "Auto-blend"]},
    11: {"week": 2, "month": 1, "phase": "Expressions", "tasks": ["Facial rig system", "Mouth morphing", "Real-time preview", "Smooth animations"]},
    12: {"week": 2, "month": 1, "phase": "Facial Animation", "tasks": ["Advanced features", "Micro-expressions", "Transitions", "Integration"]},
    13: {"week": 2, "month": 1, "phase": "Facial Animation", "tasks": ["Optimization", "Bug fixes", "Documentation", "Sample scenes"]},
    14: {"week": 2, "month": 1, "phase": "Week 2 Review", "tasks": ["Complete testing", "Expression testing", "GitHub push v0.2", "Update reports"]},
    15: {"week": 3, "month": 1, "phase": "Character Models", "tasks": ["Download 3D characters", "Mixamo integration", "Library setup", "Model optimization"]},
    16: {"week": 3, "month": 1, "phase": "Character Models", "tasks": ["Loading system", "Format support", "Preview widget", "Test 10+ characters"]},
    17: {"week": 3, "month": 1, "phase": "Character Rigging", "tasks": ["Bone rigging", "Skeleton system", "Skinning", "Test movement"]},
    18: {"week": 3, "month": 1, "phase": "Character Rigging", "tasks": ["IK/FK controls", "Joint constraints", "Weight painting", "Complex poses"]},
    19: {"week": 3, "month": 1, "phase": "Character Custom", "tasks": ["Enhance character_system.py", "Clothing textures", "Hair variations", "Skin tones"]},
    20: {"week": 3, "month": 1, "phase": "Character Custom", "tasks": ["Preview enhancements", "Save/load", "Library expansion", "UI improvements"]},
    21: {"week": 3, "month": 1, "phase": "Week 3 Review", "tasks": ["Test all characters", "Documentation", "GitHub push v0.3", "Screenshots"]},
    22: {"week": 4, "month": 1, "phase": "3D Renderer", "tasks": ["Upgrade render_engine.py", "Character rendering", "Viewport rendering", "Multi-object"]},
    23: {"week": 4, "month": 1, "phase": "3D Renderer", "tasks": ["Camera integration", "Multi-light", "Shadow rendering", "Test 3D scene"]},
    24: {"week": 4, "month": 1, "phase": "3D Renderer", "tasks": ["Performance opt", "GPU utilization", "Frame buffer", "Pipeline"]},
    25: {"week": 4, "month": 1, "phase": "Shaders", "tasks": ["PBR shaders", "Material upgrade", "Normal maps", "Roughness maps"]},
    26: {"week": 4, "month": 1, "phase": "Shaders", "tasks": ["Soft shadows", "AO", "Reflections", "Realistic materials"]},
    27: {"week": 4, "month": 1, "phase": "Environments", "tasks": ["Enhance environments", "Real 3D envs", "HDR skyboxes", "Terrain"]},
    28: {"week": 4, "month": 1, "phase": "Environments", "tasks": ["Props physics", "Env lighting", "Weather effects", "Beautiful envs"]},
    29: {"week": 5, "month": 2, "phase": "Animation Import", "tasks": ["Install pyfbx", "Mixamo import", "FBX/BVH support", "Animation library"]},
    30: {"week": 5, "month": 2, "phase": "Animation Import", "tasks": ["Test 100+ animations", "Categorization", "Library UI", "Performance"]},
    31: {"week": 5, "month": 2, "phase": "Skeletal Anim", "tasks": ["Real playback", "Blending", "Speed control", "Parallel animations"]},
    32: {"week": 5, "month": 2, "phase": "Skeletal Anim", "tasks": ["Advanced blending", "Loop control", "Reverse playback", "Testing"]},
    33: {"week": 5, "month": 2, "phase": "Motion System", "tasks": ["Walk cycles", "Idle animations", "Custom gestures", "Auto-transitions"]},
    34: {"week": 5, "month": 2, "phase": "Final Integration", "tasks": ["Complete integration", "Final testing", "Documentation", "LAUNCH!"]},
}


# ============================================================
# PROGRESS TRACKER CLASS
# ============================================================

class ProgressTracker:
    """Auto Progress Tracking System - 100% Error-Free"""

    def __init__(self):
        try:
            self.project_root = Path(__file__).parent.parent
            self.docs_folder  = self.project_root / "docs"
            self.logs_folder  = self.docs_folder / "daily_logs"

            self.docs_folder.mkdir(exist_ok=True, parents=True)
            self.logs_folder.mkdir(exist_ok=True, parents=True)

            self.state_file = self.docs_folder / "state.json"
            self.state = self._load_state()

            print(f"✅ ProgressTracker initialized")
            print(f"   Project: {PROJECT_NAME}")
            print(f"   Current Day: {self.state['current_day']}/{TOTAL_DAYS}")

        except Exception as e:
            print(f"❌ Tracker init error: {e}")
            raise

    # ==========================================
    # STATE MANAGEMENT
    # ==========================================

    def _load_state(self) -> Dict:
        """Load state ya naya banao"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️  State load error: {e}")

        new_state = {
            "project_name":     PROJECT_NAME,
            "owner":            OWNER,
            "github_url":       GITHUB_URL,
            "start_date":       datetime.now().isoformat(),
            "last_updated":     datetime.now().isoformat(),
            "current_day":      1,
            "current_week":     1,
            "current_month":    1,
            "current_phase":    "Setup",
            "current_task":     "Getting started",
            "total_hours":      0.0,
            "today_hours":      0.0,
            "days_worked":      0,
            "overall_progress": 0,
            "completed_tasks":  [],
            "today_activities": [],
            "today_files":      [],
            "session_count":    1,
            "last_ai_summary":  "Project just started",
        }
        self._save_state_dict(new_state)
        return new_state

    def _save_state(self):
        self._save_state_dict(self.state)

    def _save_state_dict(self, state_dict: Dict):
        try:
            state_dict["last_updated"] = datetime.now().isoformat()
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state_dict, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"❌ Save error: {e}")

    # ==========================================
    # DAY MANAGEMENT
    # ==========================================

    def start_day(self):
        """Aaj ka din start karo"""
        try:
            day = self.state['current_day']

            plan = PROJECT_PLAN.get(day, {
                "week":  ((day - 1) // 7) + 1,
                "month": ((day - 1) // 30) + 1,
                "phase": "Ongoing Development",
                "tasks": ["Continue development"]
            })

            self.state['current_week']     = plan['week']
            self.state['current_month']    = plan['month']
            self.state['current_phase']    = plan['phase']
            self.state['today_hours']      = 0.0
            self.state['today_activities'] = []
            self.state['today_files']      = []

            today_log = self.logs_folder / f"day_{day:02d}.md"

            content = "# Day " + str(day) + " - " + plan['phase'] + "\n\n"
            content += "**Date:** " + datetime.now().strftime('%Y-%m-%d') + "\n"
            content += "**Start Time:** " + datetime.now().strftime('%H:%M:%S') + "\n"
            content += "**Week:** " + str(plan['week']) + "/12\n"
            content += "**Month:** " + str(plan['month']) + "/3\n"
            content += "**Phase:** " + plan['phase'] + "\n\n"
            content += "---\n\n"
            content += "## TODAY'S PLANNED TASKS\n\n"

            for i, task in enumerate(plan['tasks'], 1):
                content += str(i) + ". [ ] " + task + "\n"

            content += "\n---\n\n## WORK LOG\n\n"
            content += "*Activities will be logged here...*\n\n---\n\n"

            today_log.write_text(content, encoding='utf-8')

            self._save_state()
            self._update_all_reports()

            print("\n" + "=" * 60)
            print("DAY " + str(day) + " STARTED!")
            print("=" * 60)
            print("Date: " + datetime.now().strftime('%Y-%m-%d'))
            print("Phase: " + plan['phase'])
            print("Planned Tasks: " + str(len(plan['tasks'])))
            print("\nTasks:")
            for i, task in enumerate(plan['tasks'], 1):
                print("  " + str(i) + ". " + task)
            print("\nLet's do this bhai! 10 hrs of coding ahead.")
            print("=" * 60 + "\n")

        except Exception as e:
            print(f"❌ Start day error: {e}")

    def log_activity(
        self,
        activity: str,
        hours: float = 0.0,
        files: Optional[List[str]] = None,
    ):
        """Activity log karo"""
        try:
            day = self.state['current_day']
            today_log = self.logs_folder / f"day_{day:02d}.md"

            self.state['today_hours'] += hours
            self.state['total_hours'] += hours
            self.state['today_activities'].append({
                "time":     datetime.now().strftime('%H:%M'),
                "activity": activity,
                "hours":    hours,
            })

            if files:
                for f in files:
                    if f not in self.state['today_files']:
                        self.state['today_files'].append(f)

            entry = "\n### " + datetime.now().strftime('%H:%M:%S') + " - " + activity + "\n\n"
            entry += "**Duration:** " + str(hours) + " hours\n"

            if files:
                entry += "**Files Modified:**\n"
                for f in files:
                    entry += "- `" + f + "`\n"

            entry += "\n---\n"

            with open(today_log, 'a', encoding='utf-8') as f:
                f.write(entry)

            self._save_state()
            self._update_all_reports()

            print(f"✅ Logged: {activity} ({hours}h)")

        except Exception as e:
            print(f"❌ Log activity error: {e}")

    def complete_task(self, task_name: str):
        """Task complete karo"""
        try:
            self.state['completed_tasks'].append({
                "task":  task_name,
                "day":   self.state['current_day'],
                "date":  datetime.now().strftime('%Y-%m-%d %H:%M'),
                "phase": self.state['current_phase'],
            })

            total_tasks = TOTAL_DAYS * 4
            completed = len(self.state['completed_tasks'])
            self.state['overall_progress'] = min(100, int((completed / total_tasks) * 100))

            day = self.state['current_day']
            today_log = self.logs_folder / f"day_{day:02d}.md"

            if today_log.exists():
                content = today_log.read_text(encoding='utf-8')
                content = content.replace("[ ] " + task_name, "[x] " + task_name)
                today_log.write_text(content, encoding='utf-8')

            self._save_state()
            self._update_all_reports()

            print(f"✅ COMPLETED: {task_name}")
            print(f"   Progress: {self.state['overall_progress']}%")

        except Exception as e:
            print(f"❌ Complete task error: {e}")

    def set_current_task(self, task: str):
        """Current task set karo"""
        try:
            self.state['current_task'] = task
            self._save_state()
            self._update_all_reports()
            print(f"📌 Task: {task}")
        except Exception as e:
            print(f"❌ Set task error: {e}")

    def end_day(self, summary: str = ""):
        """Din end karo"""
        try:
            day = self.state['current_day']
            today_log = self.logs_folder / f"day_{day:02d}.md"

            end_content = "\n\n## END OF DAY SUMMARY\n\n"
            end_content += "**End Time:** " + datetime.now().strftime('%H:%M:%S') + "\n"
            end_content += "**Total Hours Today:** " + str(self.state['today_hours']) + " hours\n"
            end_content += "**Activities:** " + str(len(self.state['today_activities'])) + "\n"
            end_content += "**Files Modified:** " + str(len(self.state['today_files'])) + "\n\n"
            end_content += "### Summary:\n"
            end_content += (summary if summary else "Day completed successfully.") + "\n\n"
            end_content += "### Files Modified Today:\n"

            for f in self.state['today_files']:
                end_content += "- `" + f + "`\n"

            end_content += "\n### Session Stats:\n"
            end_content += "- Total Project Hours: " + str(self.state['total_hours']) + "\n"
            end_content += "- Days Completed: " + str(self.state['days_worked']) + "\n"
            end_content += "- Overall Progress: " + str(self.state['overall_progress']) + "%\n\n"
            end_content += "### Git Log:\n"
            end_content += "```\n" + self._get_git_status() + "\n```\n\n"
            end_content += "---\n\n"
            end_content += "**Day " + str(day) + " Complete!**\n"

            with open(today_log, 'a', encoding='utf-8') as f:
                f.write(end_content)

            self.state['days_worked']  += 1
            self.state['current_day']  += 1

            self._save_state()
            self._update_all_reports()

            print("\n" + "=" * 60)
            print("DAY " + str(day) + " COMPLETED!")
            print("=" * 60)
            print("Hours Today: " + str(self.state['today_hours']))
            print("Progress: " + str(self.state['overall_progress']) + "%")
            print("Tasks Done: " + str(len(self.state['completed_tasks'])))
            print("\nGreat work bhai! See you tomorrow.")
            print("=" * 60 + "\n")

        except Exception as e:
            print(f"❌ End day error: {e}")

    # ==========================================
    # AUTO REPORT GENERATION
    # ==========================================

    def _update_all_reports(self):
        """Sab reports update karo"""
        try:
            self._update_progress_report()
            self._update_current_status()
            self._update_ai_context()
            self._update_next_steps()
        except Exception as e:
            print(f"❌ Report update error: {e}")

    def _update_progress_report(self):
        """PROGRESS_REPORT.md"""
        try:
            progress_bar = self._progress_bar(self.state['overall_progress'])

            content = "# 3D Animation Studio - Progress Report\n\n"
            content += "**Project:** " + PROJECT_NAME + "\n"
            content += "**Owner:** " + OWNER + "\n"
            content += "**GitHub:** " + GITHUB_URL + "\n"
            content += "**Started:** " + self.state['start_date'][:10] + "\n"
            content += "**Last Updated:** " + self.state['last_updated'][:19] + "\n\n"
            content += "---\n\n"
            content += "## CURRENT STATUS\n\n"
            content += "**Overall Progress:** " + progress_bar + " " + str(self.state['overall_progress']) + "%\n\n"
            content += "```\n"
            content += "Day:    " + str(self.state['current_day']) + "/" + str(TOTAL_DAYS) + "\n"
            content += "Week:   " + str(self.state['current_week']) + "/12\n"
            content += "Month:  " + str(self.state['current_month']) + "/3\n"
            content += "Phase:  " + self.state['current_phase'] + "\n"
            content += "```\n\n"
            content += "**Current Task:** `" + self.state['current_task'] + "`\n\n"
            content += "---\n\n"
            content += "## TIME TRACKING\n\n"
            content += "| Metric | Value |\n"
            content += "|--------|-------|\n"
            content += "| Total Hours | " + str(self.state['total_hours']) + " hrs |\n"
            content += "| Today's Hours | " + str(self.state['today_hours']) + " hrs |\n"
            content += "| Days Completed | " + str(self.state['days_worked']) + " |\n"
            content += "| Days Remaining | " + str(TOTAL_DAYS - self.state['days_worked']) + " |\n"

            avg = self.state['total_hours'] / max(1, self.state['days_worked'])
            content += "| Average Hours/Day | " + f"{avg:.1f}" + " |\n\n"

            content += "---\n\n"
            content += "## COMPLETED TASKS (" + str(len(self.state['completed_tasks'])) + ")\n\n"

            recent_tasks = self.state['completed_tasks'][-20:]
            for task in reversed(recent_tasks):
                content += "- [x] **" + task['task'] + "** (Day " + str(task['day']) + ", " + task['phase'] + ")\n"

            content += "\n---\n\n## TODAY'S ACTIVITIES\n\n"
            for act in self.state['today_activities']:
                content += "- **" + act['time'] + "** - " + act['activity'] + " (" + str(act['hours']) + "h)\n"

            content += "\n---\n\n## FILES MODIFIED TODAY\n\n"
            for f in self.state['today_files']:
                content += "- `" + f + "`\n"

            content += "\n---\n\n## NEXT STEPS\n\n"
            content += "See: [NEXT_STEPS.md](./NEXT_STEPS.md)\n\n"
            content += "---\n\n## FOR AI TOOLS\n\n"
            content += "If switching AI, first read: [AI_CONTEXT.md](./AI_CONTEXT.md)\n\n"
            content += "---\n\n**Auto-generated by progress_tracker.py**\n"

            report_file = self.docs_folder / "PROGRESS_REPORT.md"
            report_file.write_text(content, encoding='utf-8')

        except Exception as e:
            print(f"❌ Progress report error: {e}")

    def _update_current_status(self):
        """CURRENT_STATUS.md"""
        try:
            content = "# Current Status - Live Snapshot\n\n"
            content += "**Timestamp:** " + datetime.now().isoformat() + "\n\n"
            content += "---\n\n## RIGHT NOW\n\n"
            content += "```\n"
            content += "Working On: " + self.state['current_task'] + "\n"
            content += "Phase:      " + self.state['current_phase'] + "\n"
            content += "Day:        " + str(self.state['current_day']) + "/" + str(TOTAL_DAYS) + "\n"
            content += "Progress:   " + str(self.state['overall_progress']) + "%\n"
            content += "```\n\n"
            content += "---\n\n## TODAY\n\n"
            content += "- **Hours So Far:** " + str(self.state['today_hours']) + " / " + str(DAILY_HOURS) + "\n"
            content += "- **Activities:** " + str(len(self.state['today_activities'])) + "\n"
            content += "- **Files Modified:** " + str(len(self.state['today_files'])) + "\n\n"
            content += "---\n\n## OVERALL\n\n"
            content += "- **Total Hours:** " + str(self.state['total_hours']) + "\n"
            content += "- **Days Worked:** " + str(self.state['days_worked']) + "\n"
            content += "- **Tasks Done:** " + str(len(self.state['completed_tasks'])) + "\n\n"
            content += "---\n\n**Last Update:** " + self.state['last_updated'] + "\n"

            status_file = self.docs_folder / "CURRENT_STATUS.md"
            status_file.write_text(content, encoding='utf-8')

        except Exception as e:
            print(f"❌ Current status error: {e}")

    def _update_ai_context(self):
        """AI_CONTEXT.md - Most important for AI switching"""
        try:
            recent_completed = self.state['completed_tasks'][-10:]
            recent_activities = self.state['today_activities'][-5:]
            next_day = self.state['current_day']
            next_plan = PROJECT_PLAN.get(next_day, {})

            content = "# AI Context Handoff Document\n\n"
            content += "**Last Updated:** " + datetime.now().isoformat() + "\n"
            content += "**Session:** #" + str(self.state['session_count']) + "\n\n"
            content += "---\n\n"
            content += "## IMPORTANT - READ THIS FIRST!\n\n"
            content += "If you are a new AI tool taking over this project, read these files in order:\n\n"
            content += "1. **THIS FILE** (AI_CONTEXT.md)\n"
            content += "2. `PROJECT_HANDOFF.md` (in project root)\n"
            content += "3. `docs/PROGRESS_REPORT.md`\n"
            content += "4. `docs/CURRENT_STATUS.md`\n"
            content += "5. `docs/daily_logs/day_" + f"{self.state['current_day']:02d}" + ".md`\n\n"
            content += "---\n\n"
            content += "## QUICK CONTEXT\n\n"
            content += "```\n"
            content += "Project:  " + PROJECT_NAME + "\n"
            content += "Owner:    " + OWNER + "\n"
            content += "GitHub:   " + GITHUB_URL + "\n"
            content += "Language: Python 3.11.9\n"
            content += "OS:       Windows 11\n"
            content += "Style:    " + LANGUAGE + "\n"
            content += "```\n\n"
            content += "---\n\n"
            content += "## EXACTLY WHERE WE ARE\n\n"
            content += "```\n"
            content += "Current Day:    " + str(self.state['current_day']) + "/" + str(TOTAL_DAYS) + "\n"
            content += "Current Week:   " + str(self.state['current_week']) + "/12\n"
            content += "Current Month:  " + str(self.state['current_month']) + "/3\n"
            content += "Current Phase:  " + self.state['current_phase'] + "\n"
            content += "Progress:       " + str(self.state['overall_progress']) + "%\n"
            content += "Total Hours:    " + str(self.state['total_hours']) + "\n"
            content += "```\n\n"
            content += "---\n\n"
            content += "## WORKING ON RIGHT NOW\n\n"
            content += "**Task:** " + self.state['current_task'] + "\n\n"
            content += "**Latest Activities:**\n"

            for act in recent_activities:
                content += "- " + act['time'] + ": " + act['activity'] + "\n"

            content += "\n---\n\n## RECENTLY COMPLETED\n\n"
            for task in reversed(recent_completed):
                content += "- [x] " + task['task'] + " (Day " + str(task['day']) + ")\n"

            content += "\n---\n\n"
            content += "## NEXT PLANNED TASKS\n\n"
            content += "**Day " + str(next_day) + ":** " + next_plan.get('phase', 'TBD') + "\n\n"

            for task in next_plan.get('tasks', []):
                content += "- " + task + "\n"

            content += "\n---\n\n## COMMUNICATION STYLE\n\n"
            content += "- **Language:** Hinglish (Hindi + English)\n"
            content += "- **Tone:** Friendly, direct\n"
            content += "- **Address user as:** 'bhai', 'yaar'\n"
            content += "- **Provide:** COMPLETE code, no placeholders\n"
            content += "- **Explain:** Simple terms\n"
            content += "- **Comments:** In Hinglish\n\n"
            content += "---\n\n## KEY PROJECT FILES\n\n"
            content += "```\n"
            content += "main.py                          (App entry)\n"
            content += "PROJECT_HANDOFF.md               (Master docs)\n"
            content += "src/pipeline/\n"
            content += "  script_parser.py               (Script parsing)\n"
            content += "  scene_builder.py               (Scene creation)\n"
            content += "  automation_engine.py           (Orchestrator)\n"
            content += "  video_generator.py             (Video creation)\n"
            content += "src/ai/\n"
            content += "  tts_engine.py                  (TTS)\n"
            content += "  lipsync_engine.py              (Lipsync)\n"
            content += "src/audio/\n"
            content += "  audio_engine.py                (Audio playback)\n"
            content += "src/renderer/                    (3D rendering)\n"
            content += "src/physics/                     (Physics)\n"
            content += "src/ui/                          (User Interface)\n"
            content += "docs/                            (Progress tracking)\n"
            content += "```\n\n"
            content += "---\n\n"
            content += "## IMMEDIATE NEXT ACTION\n\n"
            content += "**If starting new AI session, tell them:**\n\n"
            content += "```\n"
            content += "Bhai, mera project 3D Animation Studio pe kaam kar raha hun.\n"
            content += "GitHub: " + GITHUB_URL + "\n\n"
            content += "Currently Day " + str(self.state['current_day']) + "/" + str(TOTAL_DAYS) + " pe hun.\n"
            content += "Phase: " + self.state['current_phase'] + "\n"
            content += "Current task: " + self.state['current_task'] + "\n\n"
            content += "docs/AI_CONTEXT.md padho complete context ke liye.\n"
            content += "Continue from where we left off.\n"
            content += "```\n\n"
            content += "---\n\n## LAST SESSION SUMMARY\n\n"
            content += self.state.get('last_ai_summary', 'No previous session summary') + "\n\n"
            content += "---\n\n"
            content += "**Auto-generated by progress_tracker.py - Trust this document!**\n"

            ai_file = self.docs_folder / "AI_CONTEXT.md"
            ai_file.write_text(content, encoding='utf-8')

        except Exception as e:
            print(f"❌ AI context error: {e}")

    def _update_next_steps(self):
        """NEXT_STEPS.md"""
        try:
            current = self.state['current_day']

            content = "# Next Steps\n\n"
            content += "**Generated:** " + datetime.now().isoformat() + "\n\n"
            content += "---\n\n## IMMEDIATE (Today/Tomorrow)\n\n"
            content += "### Currently Working On:\n"
            content += "`" + self.state['current_task'] + "`\n\n"
            content += "### Remaining Today:\n"

            today_plan = PROJECT_PLAN.get(current, {})
            completed_today = [t['task'] for t in self.state['completed_tasks'] if t['day'] == current]

            for task in today_plan.get('tasks', []):
                if task not in completed_today:
                    content += "- [ ] " + task + "\n"

            next_day = current + 1
            next_plan = PROJECT_PLAN.get(next_day, {})

            content += "\n---\n\n## TOMORROW (Day " + str(next_day) + ")\n\n"
            content += "**Phase:** " + next_plan.get('phase', 'TBD') + "\n\n"
            content += "**Planned Tasks:**\n"

            for task in next_plan.get('tasks', []):
                content += "- [ ] " + task + "\n"

            content += "\n---\n\n## THIS WEEK (Week " + str(self.state['current_week']) + ")\n\n"
            content += "**Focus:** " + today_plan.get('phase', 'Development') + "\n\n"

            days_remaining = 7 - ((current - 1) % 7)
            content += "**Days Remaining This Week:** " + str(days_remaining) + "\n\n"
            content += "---\n\n## THIS MONTH (Month " + str(self.state['current_month']) + ")\n\n"

            if self.state['current_month'] == 1:
                content += "### Month 1: Core Foundation\n"
                content += "- Week 1: Audio System\n"
                content += "- Week 2: Lipsync + Expressions\n"
                content += "- Week 3: 3D Character System\n"
                content += "- Week 4: OpenGL 3D Rendering\n"
            elif self.state['current_month'] == 2:
                content += "### Month 2: Advanced Features\n"
                content += "- Week 5: Animation System\n"
                content += "- Week 6: Physics + VFX\n"
                content += "- Week 7: Camera + Lighting\n"
                content += "- Week 8: Environments + Props\n"
            else:
                content += "### Month 3: Polish + Launch\n"
                content += "- Week 9: UI Improvements\n"
                content += "- Week 10: Testing + Bug Fixes\n"
                content += "- Week 11: Documentation\n"
                content += "- Week 12: LAUNCH!\n"

            content += "\n---\n\n## FINAL GOAL\n\n"

            try:
                start = datetime.fromisoformat(self.state['start_date'])
                target = start + timedelta(days=TOTAL_DAYS)
                content += "**Launch Date Target:** " + target.strftime('%Y-%m-%d') + "\n\n"
            except Exception:
                content += "**Launch Date Target:** ~34 days from start\n\n"

            content += "**Days Remaining:** " + str(TOTAL_DAYS - self.state['days_worked']) + "\n\n"
            content += "---\n\n**Auto-generated by progress_tracker.py**\n"

            next_file = self.docs_folder / "NEXT_STEPS.md"
            next_file.write_text(content, encoding='utf-8')

        except Exception as e:
            print(f"❌ Next steps error: {e}")

    # ==========================================
    # UTILITIES
    # ==========================================

    def _progress_bar(self, percent: int, width: int = 20) -> str:
        """Visual progress bar"""
        filled = int(width * percent / 100)
        return "#" * filled + "-" * (width - filled)

    def _get_git_status(self) -> str:
        """Git status"""
        try:
            result = subprocess.run(
                ['git', 'log', '--oneline', '-5'],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=5
            )
            return result.stdout if result.stdout else "No commits yet"
        except Exception:
            return "Git not available"

    def show_status(self):
        """Current status print"""
        try:
            print("\n" + "=" * 60)
            print("3D ANIMATION STUDIO - STATUS")
            print("=" * 60)
            print("Day:         " + str(self.state['current_day']) + "/" + str(TOTAL_DAYS))
            print("Week:        " + str(self.state['current_week']) + "/12")
            print("Month:       " + str(self.state['current_month']) + "/3")
            print("Phase:       " + self.state['current_phase'])
            print("Progress:    " + str(self.state['overall_progress']) + "%")
            print("Total Hours: " + str(self.state['total_hours']))
            print("Today Hours: " + str(self.state['today_hours']))
            print("Tasks Done:  " + str(len(self.state['completed_tasks'])))
            print("Files Today: " + str(len(self.state['today_files'])))
            print("Current:     " + self.state['current_task'])
            print("=" * 60 + "\n")
        except Exception as e:
            print(f"❌ Status error: {e}")

    def update_ai_summary(self, summary: str):
        """AI session summary update"""
        try:
            self.state['last_ai_summary'] = summary
            self.state['session_count'] += 1
            self._save_state()
            self._update_ai_context()
            print(f"✅ AI summary updated")
        except Exception as e:
            print(f"❌ AI summary error: {e}")


# ============================================================
# COMMAND LINE INTERFACE
# ============================================================

def print_help():
    """Help message"""
    print("""
=========================================================
     3D ANIMATION STUDIO - PROGRESS TRACKER
=========================================================

COMMANDS:

Day Management:
  start                    Start today's work
  end [summary]            End today's work
  status                   Show current status

Activity Logging:
  log "activity" [hours]   Log an activity
  task "task_name"         Set current task
  complete "task_name"     Mark task complete

AI Context:
  ai_summary "text"        Update AI handoff summary

Reports:
  reports                  Regenerate all reports
  help                     Show this help

=========================================================

EXAMPLES:

  python tools/progress_tracker.py start
  python tools/progress_tracker.py log "Fixed TTS" 2
  python tools/progress_tracker.py complete "TTS setup"
  python tools/progress_tracker.py end "Day went well"
  python tools/progress_tracker.py status

=========================================================
    """)


def main():
    """CLI entry point"""
    try:
        if len(sys.argv) < 2:
            print_help()
            return

        command = sys.argv[1].lower()
        tracker = ProgressTracker()

        if command == "start":
            tracker.start_day()

        elif command == "end":
            summary = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
            tracker.end_day(summary)

        elif command == "log":
            if len(sys.argv) < 3:
                print("❌ Usage: log \"activity\" [hours]")
                return
            activity = sys.argv[2]
            hours = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
            tracker.log_activity(activity, hours)

        elif command == "task":
            if len(sys.argv) < 3:
                print("❌ Usage: task \"task_name\"")
                return
            tracker.set_current_task(sys.argv[2])

        elif command == "complete":
            if len(sys.argv) < 3:
                print("❌ Usage: complete \"task_name\"")
                return
            tracker.complete_task(sys.argv[2])

        elif command == "status":
            tracker.show_status()

        elif command == "reports":
            tracker._update_all_reports()
            print("✅ All reports regenerated")

        elif command == "ai_summary":
            if len(sys.argv) < 3:
                print("❌ Usage: ai_summary \"summary text\"")
                return
            tracker.update_ai_summary(" ".join(sys.argv[2:]))

        elif command == "help":
            print_help()

        else:
            print(f"❌ Unknown command: {command}")
            print_help()

    except KeyboardInterrupt:
        print("\n⚠️  Cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()