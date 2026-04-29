from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from qc_viewer.config import STATIC_ROOT


router = APIRouter()


def serve_static_html(file_name: str, missing_detail: str) -> FileResponse:
    static_path = STATIC_ROOT / file_name
    if not static_path.exists():
        raise HTTPException(status_code=404, detail=missing_detail)
    return FileResponse(static_path)


@router.get("/")
async def serve_root():
    return serve_static_html("index.html", "index.html not found")


@router.get("/automate")
async def serve_hub():
    return serve_static_html("automate.html", "automate.html not found")


@router.get("/analytics")
async def serve_analytics():
    return serve_static_html("analytics.html", "analytics.html not found")


@router.get("/how-it-works")
async def serve_docs():
    return serve_static_html("how_it_works.html", "how_it_works.html not found")
