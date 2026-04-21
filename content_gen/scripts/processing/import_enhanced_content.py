import re
import os
import json
import psycopg2
from pathlib import Path


def parse_processed_text(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by Question marker (e.g., "Question 1Question", "Question 2Question")
    # Note: There's a typo in the user's file "Question 1Question"
    blocks = re.split(r'Question\s+(\d+)\s*Question and Options', content)

    processed_results = []

    # blocks[0] is header, [1] is Q1 number, [2] is Q1 content, etc.
    for i in range(1, len(blocks), 2):
        q_num = int(blocks[i])
        block_content = blocks[i+1]

        # 1. Extract Detailed Explanation
        detailed_exp = ""
        exp_match = re.search(
            r'Detailed Explanation of the Question and Right Answer(.*?)(Option Wise Explanation|### 🧠 Concept Gap Analysis)', block_content, re.DOTALL)
        if exp_match:
            detailed_exp = exp_match.group(1).strip()

        # 2. Extract Option Wise Explanation
        option_exp = ""
        opt_match = re.search(
            r'Option Wise Explanation \(Detailed\)(.*?)(### 🧠 Concept Gap Analysis|--------------------------------------------------)', block_content, re.DOTALL)
        if opt_match:
            option_exp = opt_match.group(1).strip()

        # 3. Extract Flashcards
        flashcards = []
        # Find all Flashcard X: [Front]? Back: [Back].
        flash_matches = re.finditer(
            r'Flashcard\s+\d+:\s*(.*?)\?\s*Back:\s*(.*?)\.', block_content)
        for fm in flash_matches:
            flashcards.append({
                "front": fm.group(1).strip() + "?",
                "back": fm.group(2).strip()
            })

        processed_results.append({
            "question_number": q_num,
            "detailed_explanation": detailed_exp,
            "option_explanation": option_exp,  # Storing as single string for now
            "flashcards": flashcards
        })

    return processed_results


def import_to_db(results, paper_code="9701_w25_qp_11"):
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not set.")
        return

    # Default Chemistry Topic: 1. Atomic structure
    DEFAULT_TOPIC_ID = 'f648c2fa-a042-456c-92a1-cc0ecf7e30b3'
    DEFAULT_SUBTOPIC_ID = '1465d20e-0f30-44d8-aea0-02096c47cd5b'
    SUBJECT_ID = '426d220e-0020-4f6d-a523-72a8d389b5b0'

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        for q in results:
            q_num = q['question_number']
            q_id_str = f"{paper_code}/Q{q_num}"

            # --- 1. Update chemistry_questions ---
            cur.execute(
                "SELECT id FROM chemistry_questions WHERE question_identifier = %s",
                (q_id_str,)
            )
            row = cur.fetchone()
            if not row:
                print(f"  ⚠️  Question {q_id_str} not found in DB. Skipping.")
                continue

            db_q_id = row[0]

            # Update explanation and topic
            cur.execute(
                """
                UPDATE chemistry_questions 
                SET detailed_explanation = %s, 
                    topic_id = %s,
                    subtopic_id = %s,
                    is_verified = true
                WHERE id = %s
                """,
                (q['detailed_explanation'], DEFAULT_TOPIC_ID,
                 DEFAULT_SUBTOPIC_ID, db_q_id)
            )

            # --- 2. Insert Flashcards ---
            cur.execute(
                "DELETE FROM flashcards WHERE \"questionId\" = %s", (db_q_id,))

            for flash in q['flashcards']:
                import uuid
                card_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO flashcards (id, \"frontText\", \"backText\", \"topicId\", \"subtopicId\", \"subjectId\", \"questionId\", \"isActive\")
                    VALUES (%s, %s, %s, %s, %s, %s, %s, true)
                    """,
                    (card_id, flash['front'], flash['back'], DEFAULT_TOPIC_ID,
                     DEFAULT_SUBTOPIC_ID, SUBJECT_ID, db_q_id)
                )

            print(
                f"  ✅ Imported Q{q_num}: Explanation updated, {len(q['flashcards'])} flashcards added.")

        conn.commit()
        print("\n✨ Enhanced content import complete.")
        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Database error: {e}")


if __name__ == "__main__":
    processed_path = "content_gen/content_gen/data/outputs/9701_w25_qp_11_processed.txt"
    results = parse_processed_text(processed_path)
    print(f"📄 Parsed {len(results)} questions from text file.")
    import_to_db(results)
