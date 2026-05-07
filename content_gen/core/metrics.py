import importlib
import json
import os
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime


class MetricsTrackerBase(ABC):
    """LLM usage / cost tracking (file, memory, or Redis)."""

    @property
    @abstractmethod
    def metrics(self) -> Dict[str, Any]:
        """Aggregate counters (mutable dict for file/memory; snapshot for redis)."""
        ...

    @abstractmethod
    def log_usage(self, response_obj: Any) -> None:
        ...

    @abstractmethod
    def get_current_cost(self) -> float:
        ...

    def reset_if_new_day(self) -> None:
        """Placeholder for daily reset logic if needed."""
        pass


class FileMetricsTracker(MetricsTrackerBase):
    """Persists aggregate metrics to a JSON file (default; single-process friendly)."""

    def __init__(self, storage_path: str = "content_gen/data/session_metrics.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._metrics = self._load_metrics()

    @property
    def metrics(self) -> Dict[str, Any]:
        return self._metrics

    def _load_metrics(self) -> Dict[str, Any]:
        if not self.storage_path.exists():
            return {"total_cost": 0.0, "total_tokens": 0, "last_updated": None, "calls": 0}
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"total_cost": 0.0, "total_tokens": 0, "last_updated": None, "calls": 0}

    def log_usage(self, response_obj: Any) -> None:
        usage = getattr(response_obj, "usage", {})
        try:
            from litellm import completion_cost

            actual_cost = completion_cost(completion_response=response_obj)
        except Exception:
            actual_cost = 0.0

        with self._lock:
            self._metrics["total_cost"] += actual_cost
            self._metrics["total_tokens"] += usage.get("total_tokens", 0)
            self._metrics["calls"] = int(self._metrics.get("calls", 0)) + 1
            self._metrics["last_updated"] = datetime.now().isoformat()
            self._save_metrics_unlocked()

    def _save_metrics_unlocked(self) -> None:
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(self._metrics, f, indent=2)

    def get_current_cost(self) -> float:
        with self._lock:
            return float(self._metrics.get("total_cost", 0.0))


class MemoryMetricsTracker(MetricsTrackerBase):
    """In-process metrics only (safe default under multi-worker: no shared file corruption)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._metrics: Dict[str, Any] = {
            "total_cost": 0.0,
            "total_tokens": 0,
            "last_updated": None,
            "calls": 0,
        }

    @property
    def metrics(self) -> Dict[str, Any]:
        return self._metrics

    def log_usage(self, response_obj: Any) -> None:
        usage = getattr(response_obj, "usage", {})
        try:
            from litellm import completion_cost

            actual_cost = completion_cost(completion_response=response_obj)
        except Exception:
            actual_cost = 0.0

        with self._lock:
            self._metrics["total_cost"] += actual_cost
            self._metrics["total_tokens"] += usage.get("total_tokens", 0)
            self._metrics["calls"] = int(self._metrics.get("calls", 0)) + 1
            self._metrics["last_updated"] = datetime.now().isoformat()

    def get_current_cost(self) -> float:
        with self._lock:
            return float(self._metrics.get("total_cost", 0.0))


class RedisMetricsTracker(MetricsTrackerBase):
    """Optional Redis-backed aggregates (hash: atomic HINCRBY*)."""

    def __init__(self, url: str, key: str = "edmate:metrics:session"):
        try:
            redis_mod = importlib.import_module("redis")
        except ImportError as e:
            raise RuntimeError("redis package required for Redis metrics backend") from e
        self._r = redis_mod.from_url(url, decode_responses=True)
        self._key = key

    @property
    def metrics(self) -> Dict[str, Any]:
        raw = self._r.hgetall(self._key)
        if not raw:
            return {"total_cost": 0.0, "total_tokens": 0, "last_updated": None, "calls": 0}
        return {
            "total_cost": float(raw.get("total_cost") or 0.0),
            "total_tokens": int(raw.get("total_tokens") or 0),
            "last_updated": raw.get("last_updated"),
            "calls": int(raw.get("calls") or 0),
        }

    def log_usage(self, response_obj: Any) -> None:
        usage = getattr(response_obj, "usage", {})
        try:
            from litellm import completion_cost

            actual_cost = completion_cost(completion_response=response_obj)
        except Exception:
            actual_cost = 0.0

        tokens = int(usage.get("total_tokens", 0) or 0)
        pipe = self._r.pipeline()
        pipe.hincrbyfloat(self._key, "total_cost", float(actual_cost))
        pipe.hincrby(self._key, "total_tokens", tokens)
        pipe.hincrby(self._key, "calls", 1)
        pipe.hset(self._key, "last_updated", datetime.now().isoformat())
        pipe.execute()

    def get_current_cost(self) -> float:
        v = self._r.hget(self._key, "total_cost")
        return float(v or 0.0)


def create_metrics_tracker(
    storage_path: Optional[str] = None,
) -> MetricsTrackerBase:
    """
    Factory: EDMATE_METRICS_BACKEND=file|memory|redis (default: file).

    - ``memory``: no disk; per-process (recommended for multi-worker until Redis is used).
    - ``file``: legacy JSON file (single-worker or dev).
    - ``redis``: requires EDMATE_METRICS_REDIS_URL and ``redis`` package.
    """
    mode = (os.environ.get("EDMATE_METRICS_BACKEND") or "file").strip().lower()
    if mode == "memory":
        return MemoryMetricsTracker()
    if mode == "redis":
        url = (os.environ.get("EDMATE_METRICS_REDIS_URL") or "").strip()
        if not url:
            return MemoryMetricsTracker()
        return RedisMetricsTracker(url)
    path = storage_path or os.environ.get("EDMATE_METRICS_FILE") or "content_gen/data/session_metrics.json"
    return FileMetricsTracker(path)


# Backward-compatible name used by ModelRoutingEngine and tests.
MetricsTracker = FileMetricsTracker
