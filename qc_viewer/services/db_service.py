from typing import Optional

from content_gen.db.session import connect_real_dict
from qc_viewer.config import DATABASE_URL


def get_db():
    if DATABASE_URL is None:
        print("DB connection error: DATABASE_URL is not set")
        return None
    try:
        return connect_real_dict(DATABASE_URL, connect_timeout=3)
    except Exception as e:
        print(f"DB connection error: {e}")
        return None
