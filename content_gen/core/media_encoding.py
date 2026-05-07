"""Shared binary → data URI helpers (PNG)."""

from __future__ import annotations

import base64
from pathlib import Path


def png_bytes_to_data_uri(png_bytes: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png_bytes).decode("utf-8")


def png_file_to_data_uri(path: Path) -> str:
    with open(path, "rb") as f:
        return png_bytes_to_data_uri(f.read())
