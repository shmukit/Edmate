"""
Pluggable job storage for /api/v1 async extract jobs.

Default: in-memory (dev). Set EDMATE_JOB_STORE_DB to a filesystem path for a
SQLite-backed store (survives process restarts; use Redis/Postgres for multi-worker).
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class JobRepository(ABC):
    @abstractmethod
    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def put(self, job_id: str, payload: Dict[str, Any]) -> None:
        ...

    @abstractmethod
    def merge(self, job_id: str, updates: Dict[str, Any]) -> None:
        """Shallow merge updates into the existing job record."""
        ...


class InMemoryJobRepository(JobRepository):
    def __init__(self) -> None:
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._jobs.get(job_id)
            return None if row is None else dict(row)

    def put(self, job_id: str, payload: Dict[str, Any]) -> None:
        with self._lock:
            self._jobs[job_id] = dict(payload)

    def merge(self, job_id: str, updates: Dict[str, Any]) -> None:
        with self._lock:
            if job_id not in self._jobs:
                self._jobs[job_id] = {}
            self._jobs[job_id].update(updates)


class SqliteJobRepository(JobRepository):
    def __init__(self, db_path: str) -> None:
        self._path = db_path
        self._lock = threading.Lock()
        parent = os.path.dirname(os.path.abspath(db_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, check_same_thread=False)

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            with self._connect() as conn:
                cur = conn.execute("SELECT payload FROM jobs WHERE id = ?", (job_id,))
                row = cur.fetchone()
                if not row:
                    return None
                return json.loads(row[0])

    def put(self, job_id: str, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, default=str)
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO jobs(id, payload) VALUES(?, ?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                    (job_id, body),
                )
                conn.commit()

    def merge(self, job_id: str, updates: Dict[str, Any]) -> None:
        current = self.get(job_id) or {}
        current.update(updates)
        self.put(job_id, current)


def _default_repo_from_env() -> JobRepository:
    path = (os.environ.get("EDMATE_JOB_STORE_DB") or "").strip()
    if path:
        return SqliteJobRepository(path)
    return InMemoryJobRepository()


_default_repo: Optional[JobRepository] = None
_repo_lock = threading.Lock()


def get_job_repository() -> JobRepository:
    """Singleton repository (swap via set_job_repository in tests)."""
    global _default_repo
    with _repo_lock:
        if _default_repo is None:
            _default_repo = _default_repo_from_env()
        return _default_repo


def set_job_repository(repo: Optional[JobRepository]) -> None:
    """Test hook: pass None to reset to env-based default on next get."""
    global _default_repo
    with _repo_lock:
        _default_repo = repo
