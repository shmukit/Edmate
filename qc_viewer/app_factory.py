import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from qc_viewer.config import DOCS_ROOT, STATIC_ROOT
from qc_viewer.middleware.security import EdmateApiSecurityMiddleware
from qc_viewer.router_v1 import router as api_v1_router
from qc_viewer.routers.automation import router as automation_router
from qc_viewer.routers.questions import router as questions_router
from qc_viewer.routers.static_pages import router as static_pages_router


def create_app() -> FastAPI:
    app = FastAPI(title="Edmate Lab_QA Service")

    # ── CORS must be registered before routers ──────────────────────────────
    # FastAPI/Starlette middleware wraps the app at add_middleware() time.
    # If routers are added first, preflight OPTIONS requests are handled by
    # the router (returning 405) before CORS headers can be set, which causes
    # browsers to report a CORS error even though the actual route exists.
    #
    # allow_origin_regex=r".*" reflects the exact requesting origin instead of
    # returning a literal "*".  Browsers reject "*" when non-safelisted request
    # headers (X-API-Key, X-Gemini-Key …) are present in the preflight.
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=[
            "*",
            "X-API-Key",
            "X-LLM-Provider",
            "X-Model-ID",
            "X-Gemini-Key",
            "X-OpenAI-Key",
            "Content-Type",
            "Authorization",
        ],
    )

    app.add_middleware(EdmateApiSecurityMiddleware)

    app.include_router(api_v1_router)
    app.include_router(static_pages_router)
    app.include_router(questions_router)
    app.include_router(automation_router)

    if DOCS_ROOT.exists():
        app.mount("/docs", StaticFiles(directory=str(DOCS_ROOT)), name="docs")

    app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
    return app
