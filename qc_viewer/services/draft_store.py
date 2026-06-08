import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional
import threading

from qc_viewer.config import DRAFTS_ROOT

METADATA_LOCK = threading.Lock()

# Sentinel for anonymous / self-hosted users (no user-scoping)
ANONYMOUS_USER = "anonymous"


class DraftNotFound(Exception):
    """No metadata file exists for this draft_id (neither dir/metadata.json nor legacy flat .json)."""

    def __init__(self, draft_id: str):
        self.draft_id = draft_id
        super().__init__(f"Draft not found: {draft_id}")


def ensure_drafts_root() -> None:
    DRAFTS_ROOT.mkdir(parents=True, exist_ok=True)


def _user_drafts_root(user_id: Optional[str] = None) -> Path:
    """
    Return the base directory for a user's drafts.

    Anonymous / None users use the flat DRAFTS_ROOT (backward compatible).
    Authenticated users get a scoped sub-directory: DRAFTS_ROOT / user_id.
    """
    if not user_id or user_id == ANONYMOUS_USER:
        return DRAFTS_ROOT
    scoped = DRAFTS_ROOT / user_id
    scoped.mkdir(parents=True, exist_ok=True)
    return scoped


def get_draft_dir(draft_id: str, user_id: Optional[str] = None) -> Path:
    return _user_drafts_root(user_id) / draft_id


def get_draft_metadata_path(draft_id: str, user_id: Optional[str] = None) -> Path:
    return get_draft_dir(draft_id, user_id) / "metadata.json"


def get_legacy_metadata_path(draft_id: str) -> Path:
    return DRAFTS_ROOT / f"{draft_id}.json"


def resolve_metadata_path(draft_id: str, user_id: Optional[str] = None) -> Path:
    """
    Resolve the metadata.json path for a draft.

    Search order:
      1. User-scoped directory: DRAFTS_ROOT / user_id / draft_id / metadata.json
      2. Flat directory (anonymous/legacy): DRAFTS_ROOT / draft_id / metadata.json
      3. Legacy flat JSON: DRAFTS_ROOT / draft_id.json
    """
    # Try user-scoped path first (if a real user_id is provided)
    if user_id and user_id != ANONYMOUS_USER:
        scoped_path = _user_drafts_root(user_id) / draft_id / "metadata.json"
        if scoped_path.exists():
            return scoped_path

    # Fall back to flat directory (anonymous / legacy)
    flat_path = DRAFTS_ROOT / draft_id / "metadata.json"
    if flat_path.exists():
        return flat_path

    # Fall back to legacy flat JSON
    legacy_path = get_legacy_metadata_path(draft_id)
    if legacy_path.exists():
        return legacy_path

    raise DraftNotFound(draft_id)


def read_json(path: Path) -> dict[str, Any]:
    with METADATA_LOCK:
        with open(path, "r") as f:
            return json.load(f)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    with METADATA_LOCK:
        with open(path, "w") as f:
            json.dump(payload, f)


def read_modify_write_json(path: Path, mutator: Callable[[dict[str, Any]], None]) -> None:
    """
    Read JSON, apply mutator in-place, then atomically replace the file.
    Holds METADATA_LOCK for the whole operation so callers never read a torn write.
    """
    with METADATA_LOCK:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
        else:
            data = {}
        mutator(data)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, path)


def _scan_directory_for_drafts(root: Path) -> list[dict[str, Any]]:
    """Scan a single directory for draft metadata (directories with metadata.json + legacy flat .json)."""
    drafts: list[dict[str, Any]] = []
    if not root.exists():
        return drafts

    for d in root.iterdir():
        if d.is_dir() and (d / "metadata.json").exists():
            try:
                drafts.append(read_json(d / "metadata.json"))
            except Exception:
                continue
        elif d.suffix == ".json" and d.name != "metadata.json":
            try:
                data = read_json(d)
                if "id" in data:
                    drafts.append(data)
            except Exception:
                continue
    return drafts


def list_draft_metadata(user_id: Optional[str] = None) -> list[dict[str, Any]]:
    """
    List all draft metadata for a given user.

    - Anonymous / None: scans DRAFTS_ROOT (flat layout, backward compatible).
    - Authenticated user: scans DRAFTS_ROOT / user_id only.
    """
    root = _user_drafts_root(user_id)
    return _scan_directory_for_drafts(root)


def sort_key_from_timestamp(payload: dict[str, Any]) -> float:
    ts = payload.get("timestamp") or payload.get("created_at") or ""
    if not ts:
        return 0.0
    try:
        return float(ts)
    except (ValueError, TypeError):
        try:
            return datetime.fromisoformat(ts).timestamp()
        except Exception:
            return 0.0


def delete_draft_data(draft_id: str, user_id: Optional[str] = None) -> bool:
    """Delete all data for a draft. Checks user-scoped dir first, then flat/legacy layout."""
    draft_dir = get_draft_dir(draft_id, user_id)
    if draft_dir.is_dir():
        shutil.rmtree(draft_dir)
        return True

    # Also check the flat layout (anonymous / legacy)
    if user_id and user_id != ANONYMOUS_USER:
        flat_dir = DRAFTS_ROOT / draft_id
        if flat_dir.is_dir():
            shutil.rmtree(flat_dir)
            return True

    legacy_json = get_legacy_metadata_path(draft_id)
    legacy_pdf = DRAFTS_ROOT / f"{draft_id}.pdf"
    if legacy_json.exists():
        legacy_json.unlink()
        if legacy_pdf.exists():
            legacy_pdf.unlink()
        return True
    return False


def load_metadata_if_exists(draft_id: str, user_id: Optional[str] = None) -> Optional[dict[str, Any]]:
    try:
        return read_json(resolve_metadata_path(draft_id, user_id))
    except DraftNotFound:
        return None


def is_draft_owned_by(draft_id: str, user_id: str) -> bool:
    """
    Check if a draft belongs to a user.

    Returns True if:
      - Draft exists in the user's scoped directory, OR
      - Draft metadata has matching owner_id, OR
      - user_id is anonymous (anonymous can access flat-layout drafts)
    """
    if not user_id or user_id == ANONYMOUS_USER:
        # Anonymous users can access any draft in the flat layout
        return True

    # Check user-scoped directory
    scoped_path = _user_drafts_root(user_id) / draft_id / "metadata.json"
    if scoped_path.exists():
        return True

    # Check owner_id in flat-layout metadata
    flat_path = DRAFTS_ROOT / draft_id / "metadata.json"
    if flat_path.exists():
        try:
            meta = read_json(flat_path)
            return meta.get("owner_id") == user_id
        except Exception:
            return False

    return False
