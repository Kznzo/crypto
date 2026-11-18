"""File d'attente des tâches longues (téléchargements, transcription, exports)."""
from __future__ import annotations

import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Callable


class Cancelled(Exception):
    pass


class Job:
    def __init__(self, project_id: str | None, kind: str, label: str):
        self.id = uuid.uuid4().hex[:10]
        self.project_id = project_id
        self.kind = kind
        self.label = label
        self.status = "attente"
        self.progress = 0.0
        self.message = "En attente…"
        self.error: str | None = None
        self.created = time.time()
        self.finished: float | None = None
        self.cancel_requested = False

    def set(self, progress: float | None = None, message: str | None = None) -> None:
        if self.cancel_requested:
            raise Cancelled()
        if progress is not None:
            self.progress = max(0.0, min(1.0, float(progress)))
        if message is not None:
            self.message = message

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "kind": self.kind,
            "label": self.label,
            "status": self.status,
            "progress": round(self.progress, 4),
            "message": self.message,
            "error": self.error,
            "created": self.created,
            "finished": self.finished,
        }


class JobManager:
    """Deux files : « réseau » (téléchargements) et « calcul » (IA + encodage vidéo, une à la fois)."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._pools = {
            "reseau": ThreadPoolExecutor(max_workers=2, thread_name_prefix="reseau"),
            "calcul": ThreadPoolExecutor(max_workers=1, thread_name_prefix="calcul"),
        }

    def submit(
        self,
        project_id: str | None,
        kind: str,
        label: str,
        fn: Callable[[Job], None],
        queue: str = "calcul",
        on_error: Callable[[Job, str], None] | None = None,
    ) -> Job:
        job = Job(project_id, kind, label)
        with self._lock:
            self._jobs[job.id] = job
            self._prune()

        def runner() -> None:
            if job.cancel_requested:
                job.status = "annule"
                job.message = "Annulé"
                job.finished = time.time()
                if on_error:
                    on_error(job, "Annulé")
                return
            job.status = "en_cours"
            job.message = "Démarrage…"
            try:
                fn(job)
                job.status = "fini"
                job.progress = 1.0
                if job.message in ("Démarrage…", "En attente…"):
                    job.message = "Terminé"
            except Cancelled:
                job.status = "annule"
                job.message = "Annulé"
                if on_error:
                    on_error(job, "Annulé")
            except Exception as exc:  # noqa: BLE001 - on veut tout remonter à l'interface
                msg = str(exc) or exc.__class__.__name__
                if msg == "Annulé":
                    job.status = "annule"
                    job.message = "Annulé"
                else:
                    job.status = "erreur"
                    job.error = msg
                    job.message = "Erreur"
                    traceback.print_exc()
                if on_error:
                    on_error(job, msg)
            finally:
                job.finished = time.time()

        self._pools[queue].submit(runner)
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job or job.status in ("fini", "erreur", "annule"):
            return False
        job.cancel_requested = True
        return True

    def list(self, project_id: str | None = None) -> list[dict]:
        with self._lock:
            jobs = list(self._jobs.values())
        if project_id:
            jobs = [j for j in jobs if j.project_id == project_id]
        jobs.sort(key=lambda j: j.created)
        return [j.to_dict() for j in jobs]

    def active_for(self, project_id: str, kind: str | None = None) -> list[Job]:
        return [
            j for j in self._jobs.values()
            if j.project_id == project_id and j.status in ("attente", "en_cours") and (kind is None or j.kind == kind)
        ]

    def _prune(self) -> None:
        if len(self._jobs) < 300:
            return
        done = sorted(
            (j for j in self._jobs.values() if j.status in ("fini", "erreur", "annule")),
            key=lambda j: j.created,
        )
        for j in done[:100]:
            self._jobs.pop(j.id, None)


manager = JobManager()
