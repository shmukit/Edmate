"""Centralized psycopg2 connection factory (RealDictCursor, timeouts)."""

from __future__ import annotations

from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor


def connect_real_dict(dsn: str, *, connect_timeout: int = 30, **kwargs: Any):
    """
    Open a PostgreSQL connection with dict-like rows.

    Extra kwargs are forwarded to psycopg2.connect (e.g. application_name).
    """
    return psycopg2.connect(
        dsn,
        cursor_factory=RealDictCursor,
        connect_timeout=connect_timeout,
        **kwargs,
    )
