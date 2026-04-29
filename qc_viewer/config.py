import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# Load environment variables from content_gen/.env
ENV_PATH = PROJECT_ROOT / "content_gen" / ".env"
load_dotenv(dotenv_path=ENV_PATH)

DATABASE_URL = os.getenv("DATABASE_URL")

TABLES = [
    "chemistry_questions",
    "biology_questions",
    "physics_questions",
    "igcse_biology_questions",
    "igcse_chemistry_questions",
    "igcse_physics_questions",
]

DRAFTS_ROOT = BASE_DIR / "drafts"
STATIC_ROOT = BASE_DIR / "static"
DOCS_ROOT = PROJECT_ROOT / "docs"
