#!/usr/bin/env python3
"""
Text Normalizer for DB Import Pipeline
========================================
Converts raw PDF-extracted text (with LaTeX-style notation and Wingdings
characters) into frontend-ready HTML that the Edmate frontend can render.

Usage:
    from content_gen.scripts.processing.text_normalizer import normalize

    clean = normalize("CH_4(g) + 2H_2O(g) \\uf0ae CO_2(g) + 4H_2(g)")
    # → "<p>CH<sub>4</sub>(g) + 2H<sub>2</sub>O(g) → CO<sub>2</sub>(g) + 4H<sub>2</sub>(g)</p>"
"""

import re
from html import escape

# ─────────────────────────────────────────────────────────────
# Wingdings / Symbol font character map
# These are Private Use Area (PUA) Unicode chars that Word/PDF
# uses in place of proper Unicode when fonts are Symbol/Wingdings
# ─────────────────────────────────────────────────────────────
WINGDINGS_MAP = {
    "\uf0ae": "→",       # Rightwards arrow
    "\uf0ac": "←",       # Leftwards arrow
    "\uf0dc": "⇌",       # Equilibrium arrows (reversible reaction)
    "\uf0ab": "↔",       # Left-right arrow
    "\uf0b4": "×",       # Multiplication sign
    "\uf0b8": "÷",       # Division sign
    "\uf0b1": "±",       # Plus-minus
    "\uf0b3": "≥",       # Greater-than-or-equal
    "\uf0a3": "≤",       # Less-than-or-equal
    "\uf0b9": "·",       # Middle dot / centred dot
    "\uf070": "π",       # Pi
    "\uf06d": "μ",       # Mu (micro)
    "\uf061": "α",       # Alpha
    "\uf062": "β",       # Beta
    "\uf067": "γ",       # Gamma
    "\uf064": "δ",       # Delta (lowercase)
    "\uf044": "Δ",       # Delta (uppercase)
    "\uf071": "θ",       # Theta
    "\uf06c": "λ",       # Lambda
    "\uf073": "σ",       # Sigma (lowercase)
    "\uf053": "Σ",       # Sigma (uppercase)
    "\uf077": "ω",       # Omega (lowercase)
    "\uf0a5": "∞",       # Infinity
    "\uf0b0": "°",       # Degree sign
    "\uf0a7": "•",       # Bullet
    "\uf0d7": "×",       # Heavy multiplication (alternative)
    "\uf020": " ",       # Space
}

# ─────────────────────────────────────────────────────────────
# Superscript digit / sign Unicode map  (for plain-text output)
# ─────────────────────────────────────────────────────────────
SUPERSCRIPT_UNICODE = {
    "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
    "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
    "+": "⁺", "-": "⁻", "–": "⁻", "n": "ⁿ",
}

SUBSCRIPT_UNICODE = {
    "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄",
    "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉",
    "+": "₊", "-": "₋",
}


# ─────────────────────────────────────────────────────────────
# Core normalizer
# ─────────────────────────────────────────────────────────────

def _replace_wingdings(text: str) -> str:
    """Replace Wingdings / Symbol PUA characters with proper Unicode."""
    for char, replacement in WINGDINGS_MAP.items():
        text = text.replace(char, replacement)
    return text


def _apply_sub_sup_html(text: str) -> str:
    """
    Convert LaTeX-style sub/superscript notation to HTML tags.

    Rules:
        _2      → <sub>2</sub>
        _2O     → <sub>2</sub>O     (only digits/signs as subscript, letters follow)
        ^2+     → <sup>2+</sup>
        ^{2+}   → <sup>2+</sup>     (braces optional)
        _n      → single char subscripts; longer tokens need braces or are digit-only
        ^27_13  → <sup>27</sup><sub>13</sub>

    Strategy:
        Process ^ before _ since they can be chained.
        Use a state-machine regex to identify token boundaries.
    """

    # ── Electron configuration notation: 1s^22s^22p^6 ──────────────────
    # These look like: <digit><orbital_letter(s/p/d/f)>^<exponent><next_token>
    # Problem: naive greedy regex captures "^22s" as the exponent.
    # Fix: first insert a space boundary between the exponent digit(s) and the
    # next shell number+orbital combination, so "^22s" → "^2 2s".
    #
    # Pattern: a caret, some digits, then immediately a digit followed by s/p/d/f
    # We insert a space: ^2 → <sup>2</sup>, and "2s" stays as-is.
    text = re.sub(r'\^([0-9]+)(?=\d[spdf])',
                  lambda m: f'<sup>{m.group(1)}</sup>', text)

    # Remaining unbraced superscripts: ^<digits+signs>  e.g. ^2+  ^–1  ^27
    # (Do NOT capture trailing letters to avoid eating orbital symbols)
    text = re.sub(r'\^([0-9–\+\-]+)',
                  lambda m: f'<sup>{m.group(1)}</sup>', text)

    # Pure single-letter superscript (e.g. ^n) only when not followed by a digit
    text = re.sub(r'\^([a-zA-Z])(?!\d)',
                  lambda m: f'<sup>{m.group(1)}</sup>', text)

    # Subscript: _ followed by digits only (e.g. CH_4, H_2O → CH<sub>4</sub>)
    text = re.sub(r'_([0-9]+)', lambda m: f'<sub>{m.group(1)}</sub>', text)

    return text


def _wrap_html(text: str) -> str:
    """Wrap content in a <p> tag if not already wrapped in HTML."""
    stripped = text.strip()
    if stripped.startswith("<") and stripped.endswith(">"):
        return stripped  # already HTML
    return f"<p>{stripped}</p>"


def normalize(text: str, wrap_html: bool = True) -> str:
    """
    Normalize raw PDF-extracted text to frontend-ready HTML.

    Steps:
        1. Replace Wingdings / Symbol PUA characters
        2. Convert ^/_ LaTeX-style notation to HTML <sup>/<sub>
        3. Wrap in <p> tag

    Args:
        text:       Raw extracted text string.
        wrap_html:  If True (default), wrap result in <p>...</p>.

    Returns:
        HTML string safe for frontend rendering.
    """
    if not text:
        return ""

    result = text
    result = _replace_wingdings(result)
    result = _apply_sub_sup_html(result)

    if wrap_html:
        result = _wrap_html(result)

    return result


def normalize_options(options: dict | list) -> list:
    """
    Normalize a dict {A:..., B:..., C:..., D:...} or list of option strings.
    Returns a list of HTML strings [A, B, C, D].
    """
    if isinstance(options, dict):
        items = [options.get(k, "") for k in ("A", "B", "C", "D")]
    else:
        items = list(options)

    return [normalize(opt, wrap_html=False) for opt in items]


# ─────────────────────────────────────────────────────────────
# Batch DB fixer — run against already-imported rows
# ─────────────────────────────────────────────────────────────

def fix_existing_rows(
    connection_string: str,
    table: str,
    paper_code_pattern: str = "%",
    dry_run: bool = True,
):
    """
    Re-normalise `title` and `options` for rows that were imported with raw
    LaTeX notation.

    Args:
        connection_string:  PostgreSQL URL.
        table:              Target table name, e.g. 'chemistry_questions'.
        paper_code_pattern: SQL LIKE pattern to filter rows, e.g. '9701_w25%'.
        dry_run:            If True, print diffs but do NOT commit to DB.
    """
    import psycopg2
    conn = psycopg2.connect(connection_string)
    cur = conn.cursor()

    cur.execute(
        f"SELECT id, question_identifier, title, options FROM {table} "
        f"WHERE question_identifier LIKE %s;",
        (paper_code_pattern,),
    )
    rows = cur.fetchall()
    print(
        f"🔍 Found {len(rows)} rows matching '{paper_code_pattern}' in '{table}'")

    updated = 0
    for row_id, q_id, raw_title, raw_options in rows:
        new_title = normalize(raw_title)
        new_options = [normalize(o, wrap_html=False)
                       for o in (raw_options or [])]

        changed = (new_title != raw_title) or (
            new_options != list(raw_options or []))
        if not changed:
            continue

        if dry_run:
            print(f"\n⚡ {q_id}")
            print(f"  BEFORE title: {repr(raw_title[:100])}")
            print(f"  AFTER  title: {repr(new_title[:100])}")
            if list(raw_options or []) != new_options:
                print(f"  BEFORE opts: {raw_options}")
                print(f"  AFTER  opts: {new_options}")
        else:
            cur.execute(
                f"UPDATE {table} SET title = %s, options = %s, updated_at = NOW() WHERE id = %s;",
                (new_title, new_options, row_id),
            )
            updated += 1

    if dry_run:
        print("\n🚫 Dry run — no changes written. Run with dry_run=False to apply.")
        conn.rollback()
    else:
        conn.commit()
        print(f"✅ Updated {updated} rows in '{table}'.")

    cur.close()
    conn.close()


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description="Fix LaTeX/Wingdings in imported DB rows")
    parser.add_argument("--table", required=True,
                        help="e.g. chemistry_questions")
    parser.add_argument("--paper-code", default="%",
                        help="SQL LIKE filter on question_identifier, e.g. '9701_w25%%'")
    parser.add_argument("--apply", action="store_true",
                        help="Actually write changes (default is dry-run)")
    parser.add_argument("--db-url", default=None)
    args = parser.parse_args()

    db_url = args.db_url or os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ Set --db-url or DATABASE_URL env var.")
        raise SystemExit(1)

    fix_existing_rows(
        connection_string=db_url,
        table=args.table,
        paper_code_pattern=args.paper_code,
        dry_run=not args.apply,
    )
