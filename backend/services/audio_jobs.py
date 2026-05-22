"""
Background audio processing job manager.
Runs transcription and summarization off the request thread.
"""

import queue
import threading
import time
import uuid
from typing import Dict, Optional


class AudioJobManager:
    """Simple in-memory job manager for async audio processing."""

    def __init__(self, transcriber, summarizer):
        self.transcriber = transcriber
        self.summarizer = summarizer
        self.jobs: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self._queue: "queue.Queue[tuple]" = queue.Queue()
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def submit(self, audio_path: str, max_bullets: int = 5) -> str:
        job_id = str(uuid.uuid4())
        with self._lock:
            self.jobs[job_id] = {
                "status": "queued",
                "created_at": time.time(),
                "updated_at": time.time(),
                "audio_path": audio_path,
                "transcript": None,
                "summary": None,
                "error": None,
            }
        self._queue.put((job_id, audio_path, max_bullets))
        return job_id

    def get(self, job_id: str) -> Optional[Dict]:
        with self._lock:
            return self.jobs.get(job_id)

    def _run(self) -> None:
        while True:
            job_id, audio_path, max_bullets = self._queue.get()
            with self._lock:
                job = self.jobs.get(job_id)
            if not job:
                self._queue.task_done()
                continue

            with self._lock:
                job["status"] = "processing"
                job["updated_at"] = time.time()

            try:
                transcript = self.transcriber.transcribe_audio(
                    file_path=audio_path,
                    task="transcribe",
                    language="en",
                    include_timestamps=False,
                    verbose=False
                )
                summary = self.summarizer.summarize_meeting(
                    text=transcript,
                    max_summary_bullets=max_bullets,
                    verbose=False
                )

                with self._lock:
                    job["transcript"] = transcript
                    job["summary"] = summary
                    job["status"] = "completed"
                    job["updated_at"] = time.time()
            except Exception as exc:
                with self._lock:
                    job["status"] = "failed"
                    job["error"] = str(exc)
                    job["updated_at"] = time.time()
            finally:
                self._queue.task_done()
