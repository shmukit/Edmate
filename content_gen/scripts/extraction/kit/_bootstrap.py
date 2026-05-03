"""
PDF-Extract-Kit path bootstrap — must run before importing pdf_extract_kit.
"""
from __future__ import annotations

import sys
from pathlib import Path

# content_gen/scripts/extraction/kit -> content_gen
CONTENT_GEN_ROOT = Path(__file__).resolve().parent.parent.parent.parent

KIT_PATH = CONTENT_GEN_ROOT / "tools" / "PDF-Extract-Kit"
if str(KIT_PATH) not in sys.path:
    sys.path.insert(0, str(KIT_PATH))

try:
    import pdf_extract_kit.tasks  # noqa: F401 — trigger registration
    from pdf_extract_kit.utils.config_loader import initialize_tasks_and_models

    HAS_KIT = True
except (ImportError, ModuleNotFoundError):
    HAS_KIT = False
    initialize_tasks_and_models = None  # type: ignore[assignment]
    print(
        "⚠️ PDF-Extract-Kit not found. Extraction features using this engine will be disabled."
    )

__all__ = ["CONTENT_GEN_ROOT", "KIT_PATH", "HAS_KIT", "initialize_tasks_and_models"]
