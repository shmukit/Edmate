from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from qc_viewer.config import DATABASE_URL


def get_db():
    try:
        return psycopg2.connect(
            DATABASE_URL,
            cursor_factory=RealDictCursor,
            connect_timeout=3,
        )
    except Exception as e:
        print(f"DB connection error: {e}")
        return None
