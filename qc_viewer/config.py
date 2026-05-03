import os
import re
from functools import lru_cache
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# Load environment variables from content_gen/.env
ENV_PATH = PROJECT_ROOT / "content_gen" / ".env"
load_dotenv(dotenv_path=ENV_PATH)

DATABASE_URL = os.getenv("DATABASE_URL")

_LEGACY_TABLES: List[str] = [
    "chemistry_questions",
    "biology_questions",
    "physics_questions",
    "igcse_biology_questions",
    "igcse_chemistry_questions",
    "igcse_physics_questions",
]

_TABLE_ID_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


@lru_cache(maxsize=1)
def get_allowed_table_ids() -> Tuple[str, ...]:
    """Table names allowed in /api/questions routes — from edmate_config or legacy defaults."""
    try:
        import yaml

        for name in ("edmate_config.yaml", "edmate_config.yml", "edmate_config.json"):
            p = PROJECT_ROOT / name
            if not p.exists():
                continue
            if p.suffix == ".json":
                import json

                with open(p, encoding="utf-8") as f:
                    data = json.load(f)
            else:
                with open(p, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
            ws = data.get("workspace") or {}
            raw = ws.get("target_tables") or []
            ids: List[str] = []
            for row in raw:
                if isinstance(row, dict) and row.get("id"):
                    tid = str(row["id"])
                    if _TABLE_ID_RE.match(tid):
                        ids.append(tid)
            if ids:
                return tuple(ids)
            break
    except Exception:
        pass
    return tuple(_LEGACY_TABLES)


def get_workspace_defaults() -> tuple[str, str]:
    """(default_curriculum, default_subject) from edmate_config workspace."""
    try:
        import yaml

        for name in ("edmate_config.yaml", "edmate_config.yml", "edmate_config.json"):
            p = PROJECT_ROOT / name
            if not p.exists():
                continue
            if p.suffix == ".json":
                import json

                with open(p, encoding="utf-8") as f:
                    data = json.load(f)
            else:
                with open(p, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
            ws = data.get("workspace") or {}
            dc = str(ws.get("default_curriculum") or "General").strip() or "General"
            ds = str(ws.get("default_subject") or "General").strip() or "General"
            return dc, ds
    except Exception:
        pass
    return "General", "General"


# Backward compatibility: mutable list view for callers expecting a list
TABLES = list(_LEGACY_TABLES)

DRAFTS_ROOT = BASE_DIR / "drafts"
STATIC_ROOT = BASE_DIR / "static"
DOCS_ROOT = PROJECT_ROOT / "docs"
