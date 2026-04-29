#!/usr/bin/env python3
"""
Generate and Sync Script
========================
1. Fetches questions from production DB that lack explanations.
2. Calls ContentGenerator (LLM) to generate explanations and flashcards.
3. Normalizes the output to HTML.
4. Syncs the content back to the production DB.
"""

from content_gen.scripts.processing.text_normalizer import normalize, normalize_options
from content_gen.scripts.processing.content_generator import ContentGenerator
from content_gen.scripts.processing.import_to_db import DatabaseImporter, TABLE_MAP, SUBJECT_IDS, FALLBACK_TOPIC_ID, FALLBACK_SUBTOPIC_ID
import os
import re
import sys
import json
import uuid
from pathlib import Path
from typing import Any, List, Dict, Optional, cast
from datetime import datetime, timezone
from content_gen.core.schemas import ProcessedQuestion

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def parse_option_explanations(text: str) -> List[str]:
    """
    Parses a block of text containing option explanations into a list of 4 strings.
    """
    explanations = ["", "", "", ""]

    # More flexible regex to find A, B, C, D sections
    # Matches "Option A:", "**Option A**", "Option A is...", or just "A:" at line start
    for i, letter in enumerate(["A", "B", "C", "D"]):
        pattern = rf"(?is)(?:Option\s+{letter}|[#\*]*{letter}[#\*]*[:\.\s])\s*(.*?)(?=\s*\n\s*(?:Option\s+[B-D]|[#\*]*[B-D][#\*]*[:\.\s])|$)"
        match = re.search(pattern, text)
        if match:
            # Clean up: remove "is correct", "is incorrect" prefix if present
            content = re.sub(r"^(is|is correctly|is incorrectly|is correct|is incorrect)\s*(because|as|since|identifies)?\s*",
                             "", match.group(1).strip(), flags=re.IGNORECASE)
            explanations[i] = normalize(content.strip(), wrap_html=False)

    # If all are empty, try splitting by "Option [A-D]" without line start constraint
    if not any(explanations):
        for i, letter in enumerate(["A", "B", "C", "D"]):
            pattern = rf"(?is)Option\s+{letter}.*?[:\-]\s*(.*?)(?=\s*Option\s+[B-D]|$)"
            match = re.search(pattern, text)
            if match:
                explanations[i] = normalize(
                    match.group(1).strip(), wrap_html=False)

    return explanations


def parse_flashcards(text: str) -> List[Dict]:
    """
    Parses a block of text containing flashcards.
    """
    flashcards = []
    # Pattern: Flashcard X: Front text? Back: Back text
    pattern = r"(?i)Flashcard\s*\d*[:\s]*(.*?)\?\s*Back[:\s]*(.*?)(?=\nFlashcard|$)"
    matches = re.findall(pattern, text, re.DOTALL)

    for front, back in matches:
        # Final cleanup of the back text to remove any "Flashcard X" residues
        back_clean = re.split(r"(?i)\nFlashcard", back)[0].strip()
        flashcards.append({
            "front_text": normalize(front.strip() + "?", wrap_html=False),
            "back_text": normalize(back_clean, wrap_html=False)
        })

    return flashcards


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Generate AI content and sync to production DB")
    parser.add_argument("--paper-code", required=True,
                        help="Paper code, e.g. 9701_w25_qp_11")
    parser.add_argument("--subject", required=True,
                        choices=["Biology", "Chemistry", "Physics"], help="Subject")
    parser.add_argument("--grade", default="A-Level",
                        choices=["A-Level", "IGCSE"], help="Grade")
    parser.add_argument("--provider", default="gemini",
                        choices=["gemini", "openai", "mock"], help="LLM provider")
    parser.add_argument("--batch-size", type=int, default=1,
                        help="Number of questions per AI call")
    parser.add_argument("--limit", type=int, default=100,
                        help="Limit number of questions to process")
    parser.add_argument("--dry-run", action="store_true",
                        help="Don't write to DB")
    parser.add_argument("--db-url", help="Database URL")

    args = parser.parse_args()

    db_url = args.db_url or os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ Error: Set DATABASE_URL env var or use --db-url")
        sys.exit(1)

    table = TABLE_MAP.get((args.subject, args.grade))
    if not table:
        print(f"❌ Error: No table mapping for {args.subject} {args.grade}")
        sys.exit(1)

    subject_id = SUBJECT_IDS.get(args.subject)
    if subject_id is None:
        print(f"❌ Error: No subject ID mapping for {args.subject}")
        sys.exit(1)

    print(
        f"🚀 Starting Sync for {args.paper_code} ({args.subject} {args.grade})")

    with DatabaseImporter(db_url) as importer:
        # 1. Fetch questions lacking content
        questions = importer.fetch_questions_for_generation(
            table, args.paper_code)

        if not questions:
            print("✅ All questions already have content. Nothing to do!")
            return

        print(
            f"📊 Found {len(questions)} questions lacking content. Processing up to {args.limit}...")
        questions = questions[:args.limit]

        # 2. Generate content
        gen = ContentGenerator()
        generated_results = cast(List[Dict[str, Any]], gen.generate_for_questions(
            cast(List[ProcessedQuestion], questions), args.subject, batch_size=args.batch_size))

        # 3. Process and Sync
        for q in generated_results:
            q_id = q["id"]
            q_num = q["question_number"]
            print(f"Syncing Q{q_num} (ID: {q_id})...")

            # Extract and normalize
            summary_exp = normalize(
                q.get("explanation_generated", ""), wrap_html=True)
            print(f"  Summary size: {len(summary_exp)} chars")
            if summary_exp == "<p>[PARSING_FAILED]</p>":
                print(f"  ❌ Parsing failed for Q{q_num}!")
                continue

            detailed_exp = summary_exp

            # Parse option explanations
            oe_raw = q.get("options_explanation_generated", "")
            print(f"  Option explanations size: {len(oe_raw)} chars")
            option_exps = parse_option_explanations(oe_raw)
            print(f"  Parsed {sum(1 for e in option_exps if e)} / 4 options")

            # Parse correct answer from the explanation block
            # Looking for "Final Correct Answer: A" or "Correct Answer is B" or just a letter in a specific context
            correct_match = re.search(
                r"(?i)(?:Final\s+)?Correct\s+Answer[:\s]+(?:is\s+)?([A-D])", q.get("explanation_generated", ""))
            if not correct_match:
                # Fallback: look for the letter at the end of the explanation
                correct_match = re.search(
                    r"(?i)option\s+([A-D])\s*\.?$", q.get("explanation_generated", "").strip())

            # Store correct option as letter(s) to match DB importer contract
            correct_options = [correct_match.group(
                1).upper()] if correct_match else []
            print(f"  Correct option letters: {correct_options}")

            if not args.dry_run:
                # Update question
                importer.update_question_content(
                    table=table,
                    question_id=q_id,
                    correct_options=correct_options,
                    option_explanations=option_exps,
                    summary_explanation=summary_exp,
                    detailed_explanation=detailed_exp,
                )

                # Insert flashcards
                fc_raw = q.get("flashcards_generated", "")
                flashcards = parse_flashcards(fc_raw)

                # To insert flashcards, we need topic/subtopic.
                # Let's fetch them from the question row first.
                importer.cur.execute(
                    f"SELECT topic_id, subtopic_id FROM {table} WHERE id = %s", (q_id,))
                topic_row = importer.cur.fetchone()
                if topic_row is None:
                    t_id, st_id = None, None
                else:
                    t_id, st_id = topic_row

                if flashcards:
                    importer.insert_flashcards(
                        subject_id=subject_id,
                        topic_id=t_id or FALLBACK_TOPIC_ID,
                        subtopic_id=st_id or FALLBACK_SUBTOPIC_ID,
                        flashcards=flashcards
                    )
            else:
                print(f"  [DRY RUN] Would update Q{q_num}")
                print(f"            Correct: {correct_options}")
                print(f"            Explanations: {len(option_exps)} options")

    print("\n🏁 Sync complete!")


if __name__ == "__main__":
    main()
