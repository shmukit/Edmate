#!/usr/bin/env python3
"""
Database Import Script
Imports structured question data from the extraction pipeline into the
production `mukit_edmate_frontend` PostgreSQL database.

Targets the correct subject-specific tables:
  - A-Level:  biology_questions | chemistry_questions | physics_questions
  - IGCSE:    igcse_biology_questions | igcse_chemistry_questions | igcse_physics_questions
  - Shared:   flashcards
"""
import os
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import psycopg2
import re
from psycopg2.extras import execute_values
from .text_normalizer import normalize, normalize_options

# ──────────────────────────────────────────────
# Subject/grade → table mapping
# ──────────────────────────────────────────────
TABLE_MAP = {
    ("Biology",   "A-Level"): "biology_questions",
    ("Chemistry", "A-Level"): "chemistry_questions",
    ("Physics",   "A-Level"): "physics_questions",
    ("Biology",   "IGCSE"):   "igcse_biology_questions",
    ("Chemistry", "IGCSE"):   "igcse_chemistry_questions",
    ("Physics",   "IGCSE"):   "igcse_physics_questions",
}

# Known subject IDs from the production DB
SUBJECT_IDS = {
    "Biology":   "f9232f73-7e92-4f86-823f-7c510629b79c",
    "Chemistry": "426d220e-0020-4f6d-a523-72a8d389b5b0",
    "Physics":   "cd3e2279-3f0c-4737-9209-ddf4d2547854",
    "Mathematics": "3a90ec58-a85b-43a9-84d0-249452988545",
}

# Fallback topic/subtopic IDs used when they cannot be resolved
FALLBACK_TOPIC_ID = "unknown-topic"
FALLBACK_SUBTOPIC_ID = "unknown-subtopics"


def _parse_paper_code(paper_code: str) -> Dict[str, str]:
    """
    Parse a paper code like '9701_w25_qp_11' into metadata components.

    Returns dict with: year, session, variant, grade, exam_board
    """
    parts = paper_code.lower().split("_")
    meta = {
        "year": None,
        "session": None,
        "variant": None,
        "grade": None,
        "exam_board": "Cambridge",
    }

    # year: 2-digit suffix → 20xx
    for p in parts:
        if len(p) == 3 and p[0] in ("s", "w", "m"):
            session_map = {"s": "M/J", "w": "O/N", "m": "M/J"}
            meta["session"] = session_map.get(p[0], p[0].upper())
            meta["year"] = "20" + p[1:]
        elif len(p) == 2 and p.isdigit():
            meta["variant"] = p

    # Determine grade from subject code prefix
    code = parts[0] if parts else ""
    igcse_codes = {"0610", "0620", "0625", "0580", "4024"}  # IGCSE syllabi
    if code in igcse_codes:
        meta["grade"] = "IGCSE"
    else:
        meta["grade"] = "A-Level"

    return meta


class DatabaseImporter:
    def __init__(self, connection_string: str):
        """
        Initialise importer with a PostgreSQL connection string.
        Format: postgresql://user:password@host:5432/database
        """
        self.conn = psycopg2.connect(connection_string)
        self.cur = self.conn.cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.cur.close()
        self.conn.close()

    # ──────────────────────────────────────────
    # Topic resolution
    # ──────────────────────────────────────────

    def _resolve_topic_id(self, subject: str, topic_hint: Optional[str]) -> str:
        """Look up a topic ID by fuzzy name match, falling back to FALLBACK_TOPIC_ID."""
        if not topic_hint:
            return FALLBACK_TOPIC_ID

        subject_id = SUBJECT_IDS.get(subject)
        if not subject_id:
            return FALLBACK_TOPIC_ID

        self.cur.execute(
            'SELECT id FROM topics WHERE "subjectId" = %s AND lower(name) LIKE %s LIMIT 1;',
            (subject_id, f"%{topic_hint.lower()}%"),
        )
        row = self.cur.fetchone()
        return row[0] if row else FALLBACK_TOPIC_ID

    # ──────────────────────────────────────────
    # Main import entry point
    # ──────────────────────────────────────────

    def import_questions(
        self,
        json_path: str,
        paper_code: str,
        subject: str,
        grade: str = "A-Level",
        difficulty: str = "Medium",
        topic_id: Optional[str] = None,
        subtopic_id: Optional[str] = None,
        cdn_mapping: Optional[Dict[str, str]] = None,
    ) -> Dict:
        """
        Import questions from an extracted JSON file into the production DB.

        Args:
            json_path:    Path to the extracted JSON file.
            paper_code:   Paper code string, e.g. '9701_w25_qp_11'.
            subject:      Subject name: 'Biology' | 'Chemistry' | 'Physics'.
            grade:        'A-Level' | 'IGCSE'.
            difficulty:   Default difficulty level for all questions.
            topic_id:     Override topic UUID (looked up automatically if omitted).
            subtopic_id:  Optional subtopic UUID.
            cdn_mapping:  filename → CDN URL dict (from the upload step).

        Returns:
            Summary report dict.
        """
        with open(json_path) as f:
            data = json.load(f)

        # Resolve target table
        table = TABLE_MAP.get((subject, grade))
        if not table:
            raise ValueError(
                f"No table mapping for subject='{subject}', grade='{grade}'. "
                f"Valid combinations: {list(TABLE_MAP.keys())}"
            )

        # Parse paper metadata from code
        meta = _parse_paper_code(paper_code)
        effective_grade = meta.get("grade") or grade

        # Re-resolve table in case grade was inferred from paper code
        table = TABLE_MAP.get((subject, effective_grade), table)

        # Resolve subject ID
        subject_id = SUBJECT_IDS.get(subject)
        if not subject_id:
            raise ValueError(
                f"Unknown subject '{subject}'. Valid: {list(SUBJECT_IDS.keys())}")

        # Resolve topic
        resolved_topic_id = topic_id or FALLBACK_TOPIC_ID

        questions = data.get("questions", [])
        print(
            f"\n📥 Importing {len(questions)} questions from '{paper_code}' → table '{table}'")
        print(
            f"   Subject: {subject} | Grade: {effective_grade} | Year: {meta.get('year')} | Session: {meta.get('session')}")

        inserted = 0
        skipped = 0
        errors = []

        for q in questions:
            try:
                q_id = self._insert_question(
                    table=table,
                    question=q,
                    paper_code=paper_code,
                    subject_id=subject_id,
                    topic_id=resolved_topic_id,
                    subtopic_id=subtopic_id,
                    difficulty=difficulty,
                    meta=meta,
                    cdn_mapping=cdn_mapping or {},
                )
                inserted += 1
                print(f"  ✅ Q{q.get('question_number')}: inserted (id={q_id})")
            except psycopg2.errors.UniqueViolation:
                self.conn.rollback()
                skipped += 1
                print(
                    f"  ⚠️  Q{q.get('question_number')}: already exists, skipped")
            except Exception as e:
                self.conn.rollback()
                errors.append({"question_number": q.get(
                    "question_number"), "error": str(e)})
                print(f"  ❌ Q{q.get('question_number')}: {e}")

        report = {
            "table": table,
            "inserted": inserted,
            "skipped": skipped,
            "errors": errors,
        }
        print(
            f"\n✅ Done: {inserted} inserted, {skipped} skipped, {len(errors)} errors.")
        return report

    # ──────────────────────────────────────────
    # Row insertion helpers
    # ──────────────────────────────────────────

    def _insert_question(
        self,
        table: str,
        question: Dict,
        paper_code: str,
        subject_id: str,
        topic_id: str,
        subtopic_id: Optional[str],
        difficulty: str,
        meta: Dict,
        cdn_mapping: Dict[str, str],
    ) -> str:
        """Insert one question row and return its ID."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        q_id = str(uuid.uuid4())

        # Build the title / question text — normalize Wingdings + LaTeX → HTML
        q_text = normalize(question.get("question_text", "").strip())

        # Resolve options list [A, B, C, D] → normalized HTML strings
        raw_opts = question.get("options", {})
        options_list = normalize_options(raw_opts)

        # Build question_identifier: paper_code/Q<n>
        q_num = question.get("question_number")
        question_identifier = f"{paper_code}/Q{q_num}"

        # Build other_contents from CDN URLs of attached images
        cdn_urls = []
        for img in question.get("stem_images", []):
            url = cdn_mapping.get(Path(img).name)
            if url:
                cdn_urls.append(url)
        for opt_imgs in question.get("option_images", {}).values():
            for img in opt_imgs:
                url = cdn_mapping.get(Path(img).name)
                if url:
                    cdn_urls.append(url)
        other_contents = "\n".join(cdn_urls) if cdn_urls else None

        # Deduplicate by question_identifier — skip if already imported
        self.cur.execute(
            f"SELECT id FROM {table} WHERE question_identifier = %s LIMIT 1;",
            (question_identifier,),
        )
        existing = self.cur.fetchone()
        if existing:
            raise psycopg2.errors.UniqueViolation(
                f"question_identifier '{question_identifier}' already exists"
            )

        self.cur.execute(
            f"""
            INSERT INTO {table} (
                id, title, type, difficulty_level, source,
                subject_id, topic_id, subtopic_id,
                options, correct_options, option_explanations,
                other_contents, summary_explanation, detailed_explanation, quick_explanation,
                year, session, variant, question_identifier,
                grade, exam_board, institute_name,
                is_active, is_verified,
                created_at, updated_at
            )
            VALUES (%s,%s,%s,%s,%s, %s,%s,%s, %s,%s,%s, %s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s, %s,%s, %s,%s)
            RETURNING id;
            """,
            (
                q_id, q_text, "MCQ", difficulty, "PastPaper",
                subject_id, topic_id, subtopic_id,
                options_list, None, None,
                other_contents, None, None, None,
                meta.get("year"), meta.get("session"), meta.get(
                    "variant"), question_identifier,
                meta.get("grade"), meta.get("exam_board"), None,
                True, False,
                now, now,
            ),
        )
        self.conn.commit()
        return q_id

    # ──────────────────────────────────────────
    # Flashcard insertion
    # ──────────────────────────────────────────

    def insert_flashcards(
        self,
        subject_id: str,
        topic_id: str,
        subtopic_id: str,
        flashcards: List[Dict],
    ):
        """
        Insert flashcards into the shared `flashcards` table.

        Each flashcard dict should have: front_text, back_text
        """
        if not flashcards:
            return

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        values = [
            (
                str(uuid.uuid4()),
                subject_id,
                topic_id,
                subtopic_id,
                fc.get("front_text", ""),
                fc.get("back_text", ""),
                True,
                now,
            )
            for fc in flashcards
        ]

        execute_values(
            self.cur,
            """
            INSERT INTO flashcards (id, "subjectId", "topicId", "subtopicId", "frontText", "backText", "isActive", "createdAt")
            VALUES %s
            ON CONFLICT (id) DO NOTHING;
            """,
            values,
        )
        self.conn.commit()
        print(f"  ✅ Inserted {len(flashcards)} flashcards.")

    # ──────────────────────────────────────────
    # Content sync/update helpers
    # ──────────────────────────────────────────

    def fetch_questions_for_generation(self, table: str, paper_code: str) -> List[Dict]:
        """
        Fetch questions from a specific table and paper that lack AI explanations.
        """
        self.cur.execute(
            f"""
            SELECT id, question_identifier, title, options
            FROM {table}
            WHERE question_identifier LIKE %s
            AND (summary_explanation IS NULL OR detailed_explanation IS NULL);
            """,
            (f"{paper_code}/%",),
        )
        rows = self.cur.fetchall()

        results = []
        for r in rows:
            q_id, q_identifier, title, options = r

            # Extract question number from identifier (e.g. 9701_w25_qp_11/Q1 -> 1)
            q_num = 0
            match = re.search(r'/Q(\d+)$', q_identifier)
            if match:
                q_num = int(match.group(1))

            results.append({
                "id": q_id,
                "question_identifier": q_identifier,
                "question_text": title,
                "options": {
                    "A": options[0] if len(options) > 0 else "",
                    "B": options[1] if len(options) > 1 else "",
                    "C": options[2] if len(options) > 2 else "",
                    "D": options[3] if len(options) > 3 else "",
                },
                "question_number": q_num,
            })
        return results

    def update_question_content(
        self,
        table: str,
        question_id: str,
        correct_options: List[str],
        option_explanations: List[str],
        summary_explanation: str,
        detailed_explanation: str,
        quick_explanation: str = None,
    ):
        """
        Update a question row with AI-generated content.
        All text fields should be HTML-normalized before calling this.
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        self.cur.execute(
            f"""
            UPDATE {table}
            SET correct_options = %s,
                option_explanations = %s,
                summary_explanation = %s,
                detailed_explanation = %s,
                quick_explanation = %s,
                is_verified = true,
                updated_at = %s
            WHERE id = %s;
            """,
            (
                correct_options,
                option_explanations,
                summary_explanation,
                detailed_explanation,
                quick_explanation or summary_explanation[:200],
                now,
                question_id,
            ),
        )
        self.conn.commit()


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Import extracted questions into the production mukit_edmate_frontend DB"
    )
    parser.add_argument("json_path", help="Path to extracted JSON file")
    parser.add_argument(
        "--db-url", help="Database URL (falls back to DATABASE_URL env var)")
    parser.add_argument("--paper-code", required=True,
                        help="Paper code, e.g. 9701_w25_qp_11")
    parser.add_argument(
        "--subject", required=True,
        choices=["Biology", "Chemistry", "Physics", "Mathematics"],
        help="Subject name"
    )
    parser.add_argument(
        "--grade", default="A-Level",
        choices=["A-Level", "IGCSE"],
        help="Exam grade level (default: A-Level, auto-detected from paper code if possible)"
    )
    parser.add_argument(
        "--difficulty", default="Medium",
        choices=["Easy", "Medium", "Hard"],
    )
    parser.add_argument("--topic-id", default=None, help="Override topic UUID")
    parser.add_argument("--subtopic-id", default=None,
                        help="Override subtopic UUID")
    parser.add_argument("--cdn-mapping", default=None,
                        help="Path to CDN mapping JSON (optional)")

    args = parser.parse_args()

    db_url = args.db_url or os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ Error: Set --db-url or DATABASE_URL env var.")
        sys.exit(1)

    cdn_mapping: Dict[str, str] = {}
    if args.cdn_mapping:
        with open(args.cdn_mapping) as f:
            raw = json.load(f)
            cdn_mapping = raw.get("cdn_mapping", raw)

    with DatabaseImporter(db_url) as importer:
        report = importer.import_questions(
            json_path=args.json_path,
            paper_code=args.paper_code,
            subject=args.subject,
            grade=args.grade,
            difficulty=args.difficulty,
            topic_id=args.topic_id,
            subtopic_id=args.subtopic_id,
            cdn_mapping=cdn_mapping,
        )

    sys.exit(0 if len(report["errors"]) == 0 else 1)


if __name__ == "__main__":
    main()
