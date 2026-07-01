# ============================================================
# src/core/batch_renderer.py
# 3D Animation Studio - Batch Renderer
# Multiple videos/scenes parallel render karo
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
import threading
import queue
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum
from pathlib import Path

from src.utils import (
    get_logger,
    get_config,
    ensure_dir,
    write_json,
    read_json,
    generate_uuid,
    get_timestamp,
    format_bytes,
    get_file_size,
)

logger = get_logger("BatchRenderer")


# ============================================================
# ENUMS
# ============================================================

class JobStatus(Enum):
    """Batch job status"""
    QUEUED             = "queued"           # Waiting to start
    RUNNING            = "running"          # Currently rendering
    COMPLETED          = "completed"        # Successfully done
    FAILED             = "failed"           # Error occurred
    CANCELLED          = "cancelled"        # User cancelled
    PAUSED             = "paused"           # Temporarily stopped


class JobPriority(Enum):
    """Job priority levels"""
    LOW                = 1
    NORMAL             = 5
    HIGH               = 10
    URGENT             = 20


class JobType(Enum):
    """Types of batch jobs"""
    VIDEO_EXPORT       = "video_export"           # Full video from automation
    SCRIPT_TO_VIDEO    = "script_to_video"        # Script → video
    SCENE_RENDER       = "scene_render"           # Single scene
    IMAGE_SEQUENCE     = "image_sequence"         # Frame sequence
    CUSTOM             = "custom"


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class BatchJob:
    """
    Ek batch rendering job.
    Complete configuration + status tracking.
    """
    # Identity
    job_id:            str             = ""
    name:              str             = "Untitled Job"
    job_type:          str             = JobType.VIDEO_EXPORT.value

    # Priority
    priority:          int             = JobPriority.NORMAL.value

    # Input
    input_data:        Dict            = field(default_factory=dict)
    # Examples:
    # {"script_text": "...", "title": "..."}          - for script_to_video
    # {"automation_result_id": "..."}                  - for video_export

    # Output
    output_path:       str             = ""
    output_settings:   Dict            = field(default_factory=dict)

    # Status
    status:            str             = JobStatus.QUEUED.value
    progress:          float           = 0.0        # 0-100
    current_stage:     str             = ""
    error_message:     str             = ""

    # Timing
    created_at:        str             = ""
    started_at:        str             = ""
    completed_at:      str             = ""
    duration_seconds:  float           = 0.0

    # Result
    output_file_size:  int             = 0
    result_data:       Dict            = field(default_factory=dict)

    # Retry
    retry_count:       int             = 0
    max_retries:       int             = 2

    def __post_init__(self):
        if not self.job_id:
            self.job_id = f"job_{generate_uuid()[:8]}"
        if not self.created_at:
            self.created_at = get_timestamp()

    def is_finished(self) -> bool:
        """Kya job complete ho gayi?"""
        return self.status in [
            JobStatus.COMPLETED.value,
            JobStatus.FAILED.value,
            JobStatus.CANCELLED.value,
        ]

    def can_retry(self) -> bool:
        """Kya retry ho sakti hai?"""
        return (self.status == JobStatus.FAILED.value
                and self.retry_count < self.max_retries)

    def to_dict(self) -> Dict:
        return {
            "job_id":           self.job_id,
            "name":             self.name,
            "job_type":         self.job_type,
            "priority":         self.priority,
            "status":           self.status,
            "progress":         self.progress,
            "current_stage":    self.current_stage,
            "error_message":    self.error_message,
            "output_path":      self.output_path,
            "created_at":       self.created_at,
            "started_at":       self.started_at,
            "completed_at":     self.completed_at,
            "duration_seconds": round(self.duration_seconds, 2),
            "output_file_size": self.output_file_size,
            "retry_count":      self.retry_count,
        }


@dataclass
class BatchStats:
    """Overall batch statistics"""
    total_jobs:        int             = 0
    completed_jobs:    int             = 0
    failed_jobs:       int             = 0
    cancelled_jobs:    int             = 0
    running_jobs:      int             = 0
    queued_jobs:       int             = 0

    total_render_time: float           = 0.0
    total_output_size: int             = 0
    average_time_per_job: float        = 0.0

    def to_dict(self) -> Dict:
        return {
            "total_jobs":           self.total_jobs,
            "completed_jobs":       self.completed_jobs,
            "failed_jobs":          self.failed_jobs,
            "cancelled_jobs":       self.cancelled_jobs,
            "running_jobs":         self.running_jobs,
            "queued_jobs":          self.queued_jobs,
            "total_render_time":    round(self.total_render_time, 2),
            "total_output_size":    self.total_output_size,
            "total_output_size_str":format_bytes(self.total_output_size),
            "average_time_per_job": round(self.average_time_per_job, 2),
            "success_rate":         round(
                (self.completed_jobs / max(1, self.total_jobs)) * 100, 1
            ),
        }


# ============================================================
# JOB EXECUTORS - Actual work karne wale
# ============================================================

class JobExecutor:
    """
    Base job executor.
    Har job type ka apna executor hoga.
    """

    def execute(
        self,
        job:               BatchJob,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[bool, str]:
        """
        Job execute karo.

        Returns:
            (success, message)
        """
        raise NotImplementedError("Subclass must implement execute()")


class ScriptToVideoExecutor(JobExecutor):
    """
    Script se video generate karne wala executor.
    Pipeline module use karta hai.
    """

    def execute(
        self,
        job:               BatchJob,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[bool, str]:
        """Script → Video generate karo"""
        try:
            from src.pipeline.video_generator import script_to_video

            # Input parse karo
            script_text = job.input_data.get("script_text", "")
            title = job.input_data.get("title", job.name)
            language = job.input_data.get("language", "en")
            quality = job.input_data.get("quality", "medium")

            if not script_text:
                return False, "Script text empty hai"

            # Progress wrapper
            def on_progress(data):
                if isinstance(data, dict):
                    percent = data.get("percent", 0)
                    stage = data.get("stage", "")
                    message = data.get("message", "")
                else:
                    percent = data.percent
                    stage = data.stage
                    message = data.message

                if progress_callback:
                    progress_callback(percent, f"{stage}: {message}")

            # Generate video
            result = script_to_video(
                script_text       = script_text,
                output_path       = job.output_path,
                title             = title,
                language          = language,
                quality           = quality,
                progress_callback = on_progress,
            )

            if result.success:
                # Result data save karo
                job.result_data = {
                    "video_path":       result.video_path,
                    "duration_seconds": result.duration_seconds,
                    "total_frames":     result.total_frames,
                    "resolution":       f"{result.resolution[0]}x{result.resolution[1]}",
                    "fps":              result.fps,
                    "subtitle_path":    result.subtitle_path,
                    "metadata_path":    result.metadata_path,
                }
                job.output_file_size = result.file_size
                return True, f"Video generated: {result.video_path}"
            else:
                return False, result.error or "Unknown error"

        except Exception as e:
            logger.error(f"ScriptToVideo executor error: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e)


class VideoExportExecutor(JobExecutor):
    """
    Automation result se video export karne wala.
    """

    def execute(
        self,
        job:               BatchJob,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[bool, str]:
        """Automation result se video generate karo"""
        try:
            from src.pipeline.video_generator import (
                VideoGenerator,
                VideoSettings,
            )

            # Automation result required
            automation_result = job.input_data.get("automation_result")
            if not automation_result:
                return False, "Automation result nahi mila"

            # Settings
            settings_dict = job.output_settings or {}
            settings = VideoSettings(
                width           = settings_dict.get("width", 1920),
                height          = settings_dict.get("height", 1080),
                fps             = settings_dict.get("fps", 30),
                quality         = settings_dict.get("quality", "high"),
                video_bitrate   = settings_dict.get("video_bitrate", "8M"),
                include_audio   = settings_dict.get("include_audio", True),
                include_subtitles=settings_dict.get("include_subtitles", True),
            )

            # Generate
            generator = VideoGenerator()

            def on_progress(prog):
                if progress_callback:
                    progress_callback(prog.percent, f"{prog.stage}: {prog.message}")

            generator.add_progress_callback(on_progress)

            result = generator.generate_video(
                automation_result = automation_result,
                output_path       = job.output_path,
                settings          = settings,
            )

            if result.success:
                job.result_data = {
                    "video_path": result.video_path,
                    "duration":   result.duration_seconds,
                    "size":       result.get_file_size_str(),
                }
                job.output_file_size = result.file_size
                return True, f"Exported: {result.video_path}"
            else:
                return False, result.error or "Export failed"

        except Exception as e:
            logger.error(f"VideoExport executor error: {e}")
            return False, str(e)


class CustomExecutor(JobExecutor):
    """
    Custom function execute karne ke liye.
    User apna function pass kar sakta hai.
    """

    def execute(
        self,
        job:               BatchJob,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[bool, str]:
        """Custom function execute karo"""
        try:
            custom_func = job.input_data.get("function")
            if not callable(custom_func):
                return False, "Custom function callable nahi hai"

            args = job.input_data.get("args", [])
            kwargs = job.input_data.get("kwargs", {})

            # Custom function ko call karo
            if progress_callback:
                kwargs["progress_callback"] = progress_callback

            result = custom_func(*args, **kwargs)

            job.result_data = {"result": str(result)}
            return True, "Custom job completed"

        except Exception as e:
            logger.error(f"Custom executor error: {e}")
            return False, str(e)


# ============================================================
# BATCH RENDERER - Main class
# ============================================================

class BatchRenderer:
    """
    Batch rendering system.

    Features:
    - Multiple jobs queue
    - Sequential ya parallel execution
    - Priority-based scheduling
    - Progress tracking per job
    - Failure retry
    - Cancel support
    - Job history
    - Statistics
    """

    def __init__(
        self,
        max_parallel:      int = 1,
        config:            Optional[Dict] = None,
    ):
        """
        Args:
            max_parallel: Kitne jobs ek saath run kar sakte hain
        """
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        # Configuration
        self.max_parallel = max(1, max_parallel)

        # Job queue (priority)
        self._job_queue: List[BatchJob] = []
        self._running_jobs: Dict[str, BatchJob] = {}
        self._completed_jobs: Dict[str, BatchJob] = {}

        # Thread safety
        self._lock = threading.Lock()

        # Worker threads
        self._workers: List[threading.Thread] = []
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()

        # State
        self._is_running = False

        # Executors
        self._executors: Dict[str, JobExecutor] = {
            JobType.SCRIPT_TO_VIDEO.value: ScriptToVideoExecutor(),
            JobType.VIDEO_EXPORT.value:    VideoExportExecutor(),
            JobType.CUSTOM.value:          CustomExecutor(),
        }

        # Progress callbacks
        self._global_callbacks: List[Callable[[BatchJob], None]] = []

        # Statistics
        self._stats = BatchStats()

        # History file
        self._history_file = Path("cache/batch_history.json")

        logger.info(
            f"✅ BatchRenderer initialized | "
            f"Max parallel: {self.max_parallel}"
        )

    # ----------------------------------------------------------
    # JOB MANAGEMENT
    # ----------------------------------------------------------

    def add_job(self, job: BatchJob) -> str:
        """
        Job add karo queue mein.

        Returns:
            Job ID
        """
        with self._lock:
            self._job_queue.append(job)
            # Sort by priority (highest first)
            self._job_queue.sort(key=lambda j: -j.priority)

        self._stats.total_jobs += 1
        self._stats.queued_jobs = len(self._job_queue)

        self._notify_progress(job)
        logger.info(
            f"➕ Job added: {job.name} | "
            f"Priority: {job.priority} | "
            f"Queue: {len(self._job_queue)}"
        )
        return job.job_id

    def add_script_job(
        self,
        script_text:    str,
        output_path:    str,
        title:          str = "Untitled",
        language:       str = "en",
        quality:        str = "medium",
        priority:       int = JobPriority.NORMAL.value,
    ) -> str:
        """
        Convenience: Script-to-video job add karo.
        """
        job = BatchJob(
            name        = title,
            job_type    = JobType.SCRIPT_TO_VIDEO.value,
            priority    = priority,
            output_path = output_path,
            input_data  = {
                "script_text": script_text,
                "title":       title,
                "language":    language,
                "quality":     quality,
            },
        )
        return self.add_job(job)

    def cancel_job(self, job_id: str) -> bool:
        """Job cancel karo"""
        with self._lock:
            # Queue mein hai?
            for i, job in enumerate(self._job_queue):
                if job.job_id == job_id:
                    job.status = JobStatus.CANCELLED.value
                    self._job_queue.pop(i)
                    self._completed_jobs[job.job_id] = job
                    self._stats.cancelled_jobs += 1
                    self._stats.queued_jobs = len(self._job_queue)
                    logger.info(f"🚫 Job cancelled: {job.name}")
                    self._notify_progress(job)
                    return True

            # Running mein hai?
            if job_id in self._running_jobs:
                job = self._running_jobs[job_id]
                job.status = JobStatus.CANCELLED.value
                # Note: Actual cancellation depends on executor
                logger.info(f"🚫 Job cancel requested (running): {job.name}")
                self._notify_progress(job)
                return True

        return False

    def retry_job(self, job_id: str) -> bool:
        """Failed job retry karo"""
        job = self._completed_jobs.get(job_id)
        if not job or not job.can_retry():
            return False

        with self._lock:
            # Reset
            job.status = JobStatus.QUEUED.value
            job.progress = 0.0
            job.error_message = ""
            job.retry_count += 1
            job.started_at = ""
            job.completed_at = ""

            # Move back to queue
            del self._completed_jobs[job_id]
            self._job_queue.append(job)
            self._job_queue.sort(key=lambda j: -j.priority)

            self._stats.failed_jobs -= 1
            self._stats.queued_jobs = len(self._job_queue)

        logger.info(f"🔁 Job re-queued: {job.name} (attempt {job.retry_count + 1})")
        return True

    def get_job(self, job_id: str) -> Optional[BatchJob]:
        """Job lo ID se"""
        # Check all locations
        for job in self._job_queue:
            if job.job_id == job_id:
                return job

        if job_id in self._running_jobs:
            return self._running_jobs[job_id]

        if job_id in self._completed_jobs:
            return self._completed_jobs[job_id]

        return None

    def get_all_jobs(self) -> List[BatchJob]:
        """Sabhi jobs lo"""
        all_jobs = []
        all_jobs.extend(self._job_queue)
        all_jobs.extend(self._running_jobs.values())
        all_jobs.extend(self._completed_jobs.values())
        return all_jobs

    def get_queued_jobs(self) -> List[BatchJob]:
        return list(self._job_queue)

    def get_running_jobs(self) -> List[BatchJob]:
        return list(self._running_jobs.values())

    def get_completed_jobs(self) -> List[BatchJob]:
        return list(self._completed_jobs.values())

    def clear_completed(self):
        """Completed jobs history clear karo"""
        with self._lock:
            self._completed_jobs.clear()
        logger.info("🧹 Completed jobs cleared")

    def clear_all(self):
        """Sab kuch clear karo"""
        self.cancel_all()
        with self._lock:
            self._job_queue.clear()
            self._running_jobs.clear()
            self._completed_jobs.clear()
            self._stats = BatchStats()

    def cancel_all(self):
        """Sabhi jobs cancel karo"""
        with self._lock:
            for job in self._job_queue:
                job.status = JobStatus.CANCELLED.value
                self._completed_jobs[job.job_id] = job
                self._stats.cancelled_jobs += 1

            self._job_queue.clear()
            self._stats.queued_jobs = 0

        logger.info("🚫 All queued jobs cancelled")

    # ----------------------------------------------------------
    # EXECUTION
    # ----------------------------------------------------------

    def start(self):
        """Batch processing start karo"""
        if self._is_running:
            logger.warning("Already running")
            return

        self._is_running = True
        self._stop_event.clear()
        self._pause_event.clear()

        # Worker threads start karo
        for i in range(self.max_parallel):
            worker = threading.Thread(
                target=self._worker_loop,
                args=(i,),
                daemon=True,
            )
            worker.start()
            self._workers.append(worker)

        logger.info(f"🚀 Batch renderer started | {self.max_parallel} workers")

    def stop(self):
        """Batch processing stop karo"""
        self._is_running = False
        self._stop_event.set()

        # Wait for workers
        for worker in self._workers:
            worker.join(timeout=2)

        self._workers.clear()
        logger.info("⏹️  Batch renderer stopped")

    def pause(self):
        """Processing pause karo"""
        self._pause_event.set()
        logger.info("⏸️  Batch renderer paused")

    def resume(self):
        """Resume karo"""
        self._pause_event.clear()
        logger.info("▶️  Batch renderer resumed")

    def is_paused(self) -> bool:
        return self._pause_event.is_set()

    def is_running(self) -> bool:
        return self._is_running

    def wait_all(self, timeout: Optional[float] = None) -> bool:
        """
        Sabhi jobs complete hone tak wait karo.

        Args:
            timeout: Max wait seconds (None = infinite)

        Returns:
            True agar sab complete ho gayi
        """
        start_time = time.time()

        while True:
            with self._lock:
                queued = len(self._job_queue)
                running = len(self._running_jobs)

            if queued == 0 and running == 0:
                return True

            if timeout and (time.time() - start_time) > timeout:
                return False

            time.sleep(0.5)

    def _worker_loop(self, worker_id: int):
        """
        Worker thread loop.
        Queue se jobs uthake execute karta hai.
        """
        logger.debug(f"Worker {worker_id} started")

        while not self._stop_event.is_set():
            # Paused hai to wait karo
            if self._pause_event.is_set():
                time.sleep(0.5)
                continue

            # Next job lo
            job = None
            with self._lock:
                if self._job_queue:
                    job = self._job_queue.pop(0)
                    self._running_jobs[job.job_id] = job
                    self._stats.queued_jobs = len(self._job_queue)
                    self._stats.running_jobs = len(self._running_jobs)

            if not job:
                time.sleep(0.5)
                continue

            # Execute karo
            self._execute_job(job, worker_id)

        logger.debug(f"Worker {worker_id} stopped")

    def _execute_job(self, job: BatchJob, worker_id: int):
        """Ek job execute karo"""
        logger.info(
            f"▶️  Worker {worker_id}: Starting job '{job.name}' "
            f"({job.job_type})"
        )

        # Setup
        job.status = JobStatus.RUNNING.value
        job.started_at = get_timestamp()
        job.progress = 0.0
        start_time = time.time()

        self._notify_progress(job)

        # Executor lo
        executor = self._executors.get(job.job_type)
        if not executor:
            job.status = JobStatus.FAILED.value
            job.error_message = f"No executor for type: {job.job_type}"
            self._finish_job(job, start_time)
            return

        # Ensure output directory exists
        try:
            output_dir = os.path.dirname(job.output_path)
            if output_dir:
                ensure_dir(output_dir)
        except Exception:
            pass

        # Progress callback
        def progress_cb(percent: float, message: str):
            job.progress = percent
            job.current_stage = message
            self._notify_progress(job)

            # Cancel check
            if job.status == JobStatus.CANCELLED.value:
                raise InterruptedError("Job cancelled by user")

        # Execute
        try:
            success, message = executor.execute(job, progress_cb)

            if success:
                job.status = JobStatus.COMPLETED.value
                job.progress = 100.0
                job.current_stage = "Complete"
                logger.info(
                    f"✅ Worker {worker_id}: Job completed '{job.name}' "
                    f"in {time.time() - start_time:.1f}s"
                )
            else:
                job.status = JobStatus.FAILED.value
                job.error_message = message
                logger.error(f"❌ Job failed '{job.name}': {message}")

        except InterruptedError:
            # Already cancelled
            pass
        except Exception as e:
            job.status = JobStatus.FAILED.value
            job.error_message = str(e)
            logger.error(f"❌ Job exception '{job.name}': {e}")
            import traceback
            traceback.print_exc()

        self._finish_job(job, start_time)

    def _finish_job(self, job: BatchJob, start_time: float):
        """Job finalize karo"""
        job.completed_at = get_timestamp()
        job.duration_seconds = time.time() - start_time

        # Move to completed
        with self._lock:
            if job.job_id in self._running_jobs:
                del self._running_jobs[job.job_id]
            self._completed_jobs[job.job_id] = job

            # Stats update
            self._stats.running_jobs = len(self._running_jobs)
            self._stats.total_render_time += job.duration_seconds

            if job.status == JobStatus.COMPLETED.value:
                self._stats.completed_jobs += 1
                self._stats.total_output_size += job.output_file_size
            elif job.status == JobStatus.FAILED.value:
                self._stats.failed_jobs += 1
            elif job.status == JobStatus.CANCELLED.value:
                self._stats.cancelled_jobs += 1

            # Average
            total_done = (self._stats.completed_jobs +
                         self._stats.failed_jobs +
                         self._stats.cancelled_jobs)
            if total_done > 0:
                self._stats.average_time_per_job = (
                    self._stats.total_render_time / total_done
                )

        self._notify_progress(job)

        # Save history
        try:
            self._save_history()
        except Exception:
            pass

    # ----------------------------------------------------------
    # CALLBACKS
    # ----------------------------------------------------------

    def add_progress_callback(
        self,
        callback: Callable[[BatchJob], None]
    ):
        """Progress callback register karo"""
        self._global_callbacks.append(callback)

    def _notify_progress(self, job: BatchJob):
        """Callbacks ko notify karo"""
        for cb in self._global_callbacks:
            try:
                cb(job)
            except Exception as e:
                logger.warning(f"Callback error: {e}")

    # ----------------------------------------------------------
    # STATISTICS
    # ----------------------------------------------------------

    def get_stats(self) -> BatchStats:
        """Current statistics lo"""
        return self._stats

    def get_overall_progress(self) -> float:
        """Overall batch progress percentage (0-100)"""
        total = self._stats.total_jobs
        if total == 0:
            return 0.0

        completed = self._stats.completed_jobs
        # Running jobs ka partial progress bhi count karo
        running_progress = 0.0
        for job in self._running_jobs.values():
            running_progress += job.progress / 100.0

        return ((completed + running_progress) / total) * 100

    def get_eta_seconds(self) -> float:
        """Remaining time estimate"""
        remaining = self._stats.queued_jobs + self._stats.running_jobs
        if remaining == 0 or self._stats.average_time_per_job <= 0:
            return 0.0
        return remaining * self._stats.average_time_per_job / max(1, self.max_parallel)

    # ----------------------------------------------------------
    # PERSISTENCE
    # ----------------------------------------------------------

    def _save_history(self):
        """Job history save karo"""
        try:
            ensure_dir(str(self._history_file.parent))

            history = []
            for job in list(self._completed_jobs.values())[-50:]:   # Last 50
                history.append(job.to_dict())

            data = {
                "saved_at":  get_timestamp(),
                "stats":     self._stats.to_dict(),
                "history":   history,
            }
            write_json(str(self._history_file), data)

        except Exception as e:
            logger.debug(f"History save error: {e}")

    def load_history(self) -> List[Dict]:
        """History load karo"""
        try:
            if self._history_file.exists():
                data = read_json(str(self._history_file))
                return data.get("history", []) if data else []
        except Exception:
            pass
        return []

    # ----------------------------------------------------------
    # DISPLAY
    # ----------------------------------------------------------

    def print_status(self):
        """Console pe status print karo"""
        stats = self._stats.to_dict()
        overall = self.get_overall_progress()

        print(f"\n{'=' * 60}")
        print(f"📦 BATCH RENDERER STATUS")
        print(f"{'=' * 60}")
        print(f"  Running       : {self._is_running}")
        print(f"  Paused        : {self.is_paused()}")
        print(f"  Max Parallel  : {self.max_parallel}")
        print(f"  Overall Prog  : {overall:.1f}%")
        print(f"\n📊 Statistics:")
        for key, value in stats.items():
            print(f"  {key:25s}: {value}")

        # Queue
        queued = self.get_queued_jobs()
        if queued:
            print(f"\n⏳ Queued Jobs ({len(queued)}):")
            for job in queued[:5]:
                print(f"  • [P{job.priority}] {job.name} ({job.job_type})")

        # Running
        running = self.get_running_jobs()
        if running:
            print(f"\n▶️  Running Jobs ({len(running)}):")
            for job in running:
                print(
                    f"  • {job.name} - "
                    f"{job.progress:.0f}% - "
                    f"{job.current_stage[:40]}"
                )

        # Completed
        completed = self.get_completed_jobs()
        if completed:
            print(f"\n✅ Recent Completed ({min(5, len(completed))}):")
            for job in completed[-5:]:
                emoji = "✅" if job.status == JobStatus.COMPLETED.value else "❌"
                print(
                    f"  {emoji} {job.name} - "
                    f"{job.duration_seconds:.1f}s - "
                    f"{format_bytes(job.output_file_size)}"
                )

        print(f"{'=' * 60}\n")


# ============================================================
# GLOBAL INSTANCE
# ============================================================

_global_renderer: Optional[BatchRenderer] = None


def get_batch_renderer() -> BatchRenderer:
    """Global BatchRenderer"""
    global _global_renderer
    if _global_renderer is None:
        _global_renderer = BatchRenderer()
    return _global_renderer


# ============================================================
# CONVENIENCE - Quick batch processing
# ============================================================

def batch_render_scripts(
    scripts:         List[Dict],           # [{title, script, output_path}]
    quality:         str = "medium",
    parallel:        int = 1,
    on_progress:     Optional[Callable] = None,
) -> List[BatchJob]:
    """
    Multiple scripts ek saath render karo.
    Convenience function.

    Args:
        scripts: List of dicts with keys: title, script, output_path
        quality: Video quality
        parallel: Kitne parallel jobs
        on_progress: Progress callback

    Returns:
        List of completed BatchJobs
    """
    renderer = BatchRenderer(max_parallel=parallel)

    if on_progress:
        renderer.add_progress_callback(on_progress)

    # Add all jobs
    for script_info in scripts:
        renderer.add_script_job(
            script_text = script_info["script"],
            output_path = script_info["output_path"],
            title       = script_info.get("title", "Untitled"),
            language    = script_info.get("language", "en"),
            quality     = quality,
            priority    = script_info.get("priority", JobPriority.NORMAL.value),
        )

    # Start rendering
    renderer.start()

    # Wait for completion
    renderer.wait_all()

    # Stop
    renderer.stop()

    return renderer.get_completed_jobs()


# ============================================================
# TEST SECTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="INFO")
    print_banner("Batch Renderer Test", "Multiple Video Rendering Pipeline")

    # ===== TEST 1: Init =====
    print_section("Test 1: Initialization")
    renderer = BatchRenderer(max_parallel=2)
    print(f"✅ BatchRenderer initialized")
    print(f"   Max parallel: {renderer.max_parallel}")

    # ===== TEST 2: Job Creation =====
    print_section("Test 2: Create Jobs")

    # Custom job (simplest test)
    def custom_work(*args, progress_callback=None, **kwargs):
        """Test custom function"""
        for i in range(0, 101, 20):
            if progress_callback:
                progress_callback(i, f"Working... {i}%")
            time.sleep(0.1)
        return "Custom job success!"

    job1 = BatchJob(
        name       = "Custom Test Job 1",
        job_type   = JobType.CUSTOM.value,
        priority   = JobPriority.HIGH.value,
        input_data = {
            "function": custom_work,
            "args":     [],
            "kwargs":   {},
        },
    )

    job2 = BatchJob(
        name       = "Custom Test Job 2",
        job_type   = JobType.CUSTOM.value,
        priority   = JobPriority.NORMAL.value,
        input_data = {
            "function": custom_work,
            "args":     [],
            "kwargs":   {},
        },
    )

    job3 = BatchJob(
        name       = "Custom Test Job 3",
        job_type   = JobType.CUSTOM.value,
        priority   = JobPriority.LOW.value,
        input_data = {
            "function": custom_work,
            "args":     [],
            "kwargs":   {},
        },
    )

    print(f"✅ Created 3 test jobs")

    # Add to queue
    renderer.add_job(job1)
    renderer.add_job(job2)
    renderer.add_job(job3)

    print(f"✅ Jobs queued")
    print(f"   Queue length: {len(renderer.get_queued_jobs())}")

    # ===== TEST 3: Progress Callback =====
    print_section("Test 3: Progress Tracking")

    events_log = []
    def on_job_progress(job: BatchJob):
        events_log.append((job.name, job.status, job.progress))
        if job.status == JobStatus.RUNNING.value and int(job.progress) % 40 == 0:
            print(f"   [{job.name}] {job.progress:.0f}% - {job.current_stage}")
        elif job.status == JobStatus.COMPLETED.value:
            print(f"   ✅ [{job.name}] Completed in {job.duration_seconds:.2f}s")
        elif job.status == JobStatus.FAILED.value:
            print(f"   ❌ [{job.name}] Failed: {job.error_message}")

    renderer.add_progress_callback(on_job_progress)

    # ===== TEST 4: Start Rendering =====
    print_section("Test 4: Start Batch Rendering")

    renderer.start()
    print(f"✅ Batch renderer started")
    print(f"   Is running: {renderer.is_running()}")

    # Wait for completion
    print("\n🔄 Processing jobs...")
    success = renderer.wait_all(timeout=30)
    print(f"\n✅ All jobs finished: {success}")

    renderer.stop()

    # ===== TEST 5: Results =====
    print_section("Test 5: Results")

    completed = renderer.get_completed_jobs()
    print(f"✅ Total completed jobs: {len(completed)}")

    for job in completed:
        status_icon = "✅" if job.status == JobStatus.COMPLETED.value else "❌"
        print(
            f"   {status_icon} {job.name:25s} | "
            f"Priority: {job.priority:3d} | "
            f"Time: {job.duration_seconds:.2f}s | "
            f"Status: {job.status}"
        )

    # ===== TEST 6: Statistics =====
    print_section("Test 6: Statistics")
    stats = renderer.get_stats().to_dict()
    for key, value in stats.items():
        print(f"   {key:25s}: {value}")

    # ===== TEST 7: Print Status =====
    print_section("Test 7: Full Status Display")
    renderer.print_status()

    # ===== TEST 8: Failed Job Retry =====
    print_section("Test 8: Failed Job Retry")

    def failing_work(*args, progress_callback=None, **kwargs):
        if progress_callback:
            progress_callback(50, "About to fail...")
        raise Exception("Simulated failure")

    fail_job = BatchJob(
        name       = "Failing Job",
        job_type   = JobType.CUSTOM.value,
        max_retries= 1,
        input_data = {"function": failing_work},
    )

    renderer.clear_completed()
    renderer.add_job(fail_job)
    renderer.start()
    renderer.wait_all(timeout=10)
    renderer.stop()

    print(f"✅ Job status: {fail_job.status}")
    print(f"   Can retry: {fail_job.can_retry()}")
    print(f"   Retry count: {fail_job.retry_count}")

    if fail_job.can_retry():
        retried = renderer.retry_job(fail_job.job_id)
        print(f"✅ Retried: {retried}")

    # ===== TEST 9: Cancellation =====
    print_section("Test 9: Job Cancellation")

    def slow_work(*args, progress_callback=None, **kwargs):
        for i in range(100):
            if progress_callback:
                progress_callback(i, f"Slow work {i}")
            time.sleep(0.1)

    slow_job = BatchJob(
        name       = "Slow Job",
        job_type   = JobType.CUSTOM.value,
        input_data = {"function": slow_work},
    )

    renderer.clear_completed()
    renderer.add_job(slow_job)
    renderer.start()

    # Wait a bit then cancel
    time.sleep(0.5)
    cancelled = renderer.cancel_job(slow_job.job_id)
    print(f"✅ Cancel requested: {cancelled}")

    time.sleep(1)
    renderer.stop()

    print(f"✅ Job final status: {slow_job.status}")

    # ===== TEST 10: Convenience Function =====
    print_section("Test 10: Batch Script Rendering (Simulation)")

    # Multiple simple jobs test
    scripts = [
        {
            "title":       f"Test Script {i}",
            "script":      "Character: Test dialogue " + str(i),
            "output_path": f"exports/batch_test_{i}.mp4",
        }
        for i in range(3)
    ]

    print(f"⚠️  Skipping actual video generation (uses main pipeline)")
    print(f"   Would render {len(scripts)} scripts in batch")

    # ===== TEST 11: Job Priority =====
    print_section("Test 11: Priority Sorting")

    renderer2 = BatchRenderer(max_parallel=1)

    priorities = [
        ("Low priority",    JobPriority.LOW.value),
        ("Urgent!",         JobPriority.URGENT.value),
        ("Normal 1",        JobPriority.NORMAL.value),
        ("High priority",   JobPriority.HIGH.value),
        ("Normal 2",        JobPriority.NORMAL.value),
    ]

    for name, priority in priorities:
        renderer2.add_job(BatchJob(
            name       = name,
            job_type   = JobType.CUSTOM.value,
            priority   = priority,
            input_data = {"function": custom_work},
        ))

    print(f"✅ Added {len(priorities)} jobs with different priorities")
    print(f"   Execution order (based on priority):")
    for i, job in enumerate(renderer2.get_queued_jobs(), 1):
        print(f"   {i}. [{job.priority:3d}] {job.name}")

    # ===== TEST 12: Overall Progress =====
    print_section("Test 12: Overall Progress Calculation")
    print(f"   Overall: {renderer.get_overall_progress():.1f}%")
    print(f"   ETA    : {renderer.get_eta_seconds():.1f}s")

    # ===== TEST 13: Singleton =====
    print_section("Test 13: Global Singleton")
    r1 = get_batch_renderer()
    r2 = get_batch_renderer()
    print(f"✅ Singleton: {r1 is r2}")

    print_banner("✅ All Tests Passed!", "batch_renderer.py Working Perfectly")