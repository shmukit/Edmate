import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import threading

from fastapi import HTTPException

from qc_viewer.config import DRAFTS_ROOT

METADATA_LOCK = threading.Lock()


def ensure_drafts_root() -> None:
    DRAFTS_ROOT.mkdir(parents=True, exist_ok=True)


def get_draft_dir(draft_id: str) -> Path:
    return DRAFTS_ROOT / draft_id


def get_draft_metadata_path(draft_id: str) -> Path:
    return get_draft_dir(draft_id) / "metadata.json"


def get_legacy_metadata_path(draft_id: str) -> Path:
    return DRAFTS_ROOT / f"{draft_id}.json"


def resolve_metadata_path(draft_id: str) -> Path:
    meta_path = get_draft_metadata_path(draft_id)
    if meta_path.exists():
        return meta_path
    legacy_path = get_legacy_metadata_path(draft_id)
    if legacy_path.exists():
        return legacy_path
    raise HTTPException(status_code=404, detail="Draft not found")


def read_json(path: Path) -> dict[str, Any]:
    with METADATA_LOCK:
        with open(path, "r") as f:
            return json.load(f)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    with METADATA_LOCK:
        with open(path, "w") as f:
            json.dump(payload, f)


def list_draft_metadata() -> list[dict[str, Any]]:
    drafts: list[dict[str, Any]] = []
    if not DRAFTS_ROOT.exists():
        return drafts

    for d in DRAFTS_ROOT.iterdir():
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


def delete_draft_data(draft_id: str) -> bool:
    draft_dir = get_draft_dir(draft_id)
    if draft_dir.is_dir():
        shutil.rmtree(draft_dir)
        return True

    legacy_json = get_legacy_metadata_path(draft_id)
    legacy_pdf = DRAFTS_ROOT / f"{draft_id}.pdf"
    if legacy_json.exists():
        legacy_json.unlink()
        if legacy_pdf.exists():
            legacy_pdf.unlink()
        return True
    return False


def load_metadata_if_exists(draft_id: str) -> Optional[dict[str, Any]]:
    try:
        return read_json(resolve_metadata_path(draft_id))
    except HTTPException:
        return None
