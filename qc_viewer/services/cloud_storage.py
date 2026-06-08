"""
Pluggable file-storage adapter for draft assets (PDFs, images, etc.).

Default: local filesystem.  Set EDMATE_STORAGE_BACKEND=s3 to switch to the
(not-yet-implemented) S3 backend.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from qc_viewer.config import DRAFTS_ROOT


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class StorageBackend(ABC):
    """Async file-storage interface for per-draft assets."""

    @abstractmethod
    async def upload(self, user_id: str, draft_id: str, data: bytes, filename: str) -> str:
        """Persist *data* and return a reference key (e.g. path or URL)."""
        ...

    @abstractmethod
    async def download(self, user_id: str, draft_id: str, filename: str) -> bytes:
        """Return the raw bytes for the given file."""
        ...

    @abstractmethod
    async def delete_draft(self, user_id: str, draft_id: str) -> None:
        """Remove **all** stored files for a draft."""
        ...

    @abstractmethod
    async def list_files(self, user_id: str, draft_id: str) -> list[str]:
        """Return the filenames stored under the given draft."""
        ...


# ---------------------------------------------------------------------------
# Local-filesystem implementation
# ---------------------------------------------------------------------------

class LocalStorageBackend(StorageBackend):
    """Store draft assets on the local filesystem under ``DRAFTS_ROOT``.

    Directory layout::

        DRAFTS_ROOT / <user_id> / <draft_id> / <filename>

    For backward compatibility, ``user_id == "anonymous"`` omits the user
    directory::

        DRAFTS_ROOT / <draft_id> / <filename>

    All blocking I/O is offloaded to the default executor via
    ``asyncio.to_thread`` so the async interface never blocks the event loop.
    """

    def _draft_dir(self, user_id: str, draft_id: str) -> Path:
        """Return the directory that holds a draft's files."""
        if user_id == "anonymous":
            return DRAFTS_ROOT / draft_id
        return DRAFTS_ROOT / user_id / draft_id

    # -- synchronous helpers (run inside threads) ---------------------------

    def _upload_sync(self, user_id: str, draft_id: str, data: bytes, filename: str) -> str:
        dest_dir = self._draft_dir(user_id, draft_id)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / filename
        dest.write_bytes(data)
        return str(dest)

    def _download_sync(self, user_id: str, draft_id: str, filename: str) -> bytes:
        path = self._draft_dir(user_id, draft_id) / filename
        if not path.exists():
            raise FileNotFoundError(f"No such file: {path}")
        return path.read_bytes()

    def _delete_draft_sync(self, user_id: str, draft_id: str) -> None:
        draft_dir = self._draft_dir(user_id, draft_id)
        if draft_dir.is_dir():
            shutil.rmtree(draft_dir)

    def _list_files_sync(self, user_id: str, draft_id: str) -> list[str]:
        draft_dir = self._draft_dir(user_id, draft_id)
        if not draft_dir.is_dir():
            return []
        return [p.name for p in draft_dir.iterdir() if p.is_file()]

    # -- async interface ----------------------------------------------------

    async def upload(self, user_id: str, draft_id: str, data: bytes, filename: str) -> str:
        return await asyncio.to_thread(self._upload_sync, user_id, draft_id, data, filename)

    async def download(self, user_id: str, draft_id: str, filename: str) -> bytes:
        return await asyncio.to_thread(self._download_sync, user_id, draft_id, filename)

    async def delete_draft(self, user_id: str, draft_id: str) -> None:
        await asyncio.to_thread(self._delete_draft_sync, user_id, draft_id)

    async def list_files(self, user_id: str, draft_id: str) -> list[str]:
        return await asyncio.to_thread(self._list_files_sync, user_id, draft_id)


# ---------------------------------------------------------------------------
# S3 stub (future implementation)
# ---------------------------------------------------------------------------

class S3StorageBackend(StorageBackend):
    """Placeholder for an AWS-S3-backed storage backend."""

    async def upload(self, user_id: str, draft_id: str, data: bytes, filename: str) -> str:
        raise NotImplementedError("S3 storage not yet configured")

    async def download(self, user_id: str, draft_id: str, filename: str) -> bytes:
        raise NotImplementedError("S3 storage not yet configured")

    async def delete_draft(self, user_id: str, draft_id: str) -> None:
        raise NotImplementedError("S3 storage not yet configured")

    async def list_files(self, user_id: str, draft_id: str) -> list[str]:
        raise NotImplementedError("S3 storage not yet configured")


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_BACKENDS = {
    "local": LocalStorageBackend,
    "s3": S3StorageBackend,
}

_default_backend: Optional[StorageBackend] = None
_backend_lock = threading.Lock()


def _default_backend_from_env() -> StorageBackend:
    """Instantiate the backend selected by the ``EDMATE_STORAGE_BACKEND`` env var."""
    name = (os.environ.get("EDMATE_STORAGE_BACKEND") or "local").strip().lower()
    cls = _BACKENDS.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown storage backend {name!r}. "
            f"Supported: {', '.join(sorted(_BACKENDS))}"
        )
    return cls()


def get_storage_backend() -> StorageBackend:
    """Singleton storage backend (swap via ``set_storage_backend`` in tests)."""
    global _default_backend
    with _backend_lock:
        if _default_backend is None:
            _default_backend = _default_backend_from_env()
        return _default_backend


def set_storage_backend(backend: Optional[StorageBackend]) -> None:
    """Test hook: pass ``None`` to reset to env-based default on next get."""
    global _default_backend
    with _backend_lock:
        _default_backend = backend
