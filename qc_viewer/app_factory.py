import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from qc_viewer.config import DOCS_ROOT, STATIC_ROOT
from qc_viewer.router_v1 import router as api_v1_router
from qc_viewer.routers.automation import router as automation_router
from qc_viewer.routers.questions import router as questions_router
from qc_viewer.routers.static_pages import router as static_pages_router


def create_app() -> FastAPI:
    app = FastAPI(title="Edmate Lab_QA Service")

    app.include_router(api_v1_router)
    app.include_router(static_pages_router)
    app.include_router(questions_router)
    app.include_router(automation_router)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if DOCS_ROOT.exists():
        app.mount("/docs", StaticFiles(directory=str(DOCS_ROOT)), name="docs")

    app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
    return app
