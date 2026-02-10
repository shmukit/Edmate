#!/usr/bin/env python3
"""
Database Import Script
Imports structured question data and diagrams into PostgreSQL/Supabase
Links CDN URLs to database records
"""
import os
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import execute_values

class DatabaseImporter:
    def __init__(self, connection_string: str):
        """
        Initialize database importer
        
        Args:
            connection_string: PostgreSQL connection string
                Format: postgresql://user:pass@host:5432/database
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
    
    def import_questions(
        self,
        json_path: str,
        cdn_mapping: Dict[str, str],
        paper_code: str,
        subject: str,
        difficulty: Optional[str] = None,
        topics: Optional[List[str]] = None
    ) -> Dict:
        """
        Import questions and diagrams from extracted JSON
        
        Args:
            json_path: Path to extracted JSON file
            cdn_mapping: Filename → CDN URL mapping
            paper_code: Paper code (e.g., "9701_s25_qp_13")
            subject: Subject name ("Biology", "Chemistry", "Physics")
            difficulty: Optional difficulty level
            topics: Optional list of topic tags
            
        Returns:
            Report with counts and errors
        """
        with open(json_path) as f:
            data = json.load(f)
        
        questions_inserted = 0
        diagrams_inserted = 0
        errors = []
        
        print(f"📥 Importing {len(data['questions'])} questions from {paper_code}...")
        
        for question in data["questions"]:
            try:
                # Insert question
                question_id = self._insert_question(
                    question_number=question["question_number"],
                    paper_code=paper_code,
                    subject=subject,
                    difficulty=difficulty,
                    topics=topics
                )
                questions_inserted += 1
                
                # Insert stem diagrams
                for img_filename in question.get("stem_images", []):
                    cdn_url = cdn_mapping.get(Path(img_filename).name)
                    if cdn_url:
                        self._insert_diagram(
                            question_id=question_id,
                            cdn_url=cdn_url,
                            diagram_type="stem",
                            page_number=question.get("page")
                        )
                        diagrams_inserted += 1
                
                # Insert option diagrams
                for option, img_list in question.get("option_images", {}).items():
                    for img_filename in img_list:
                        cdn_url = cdn_mapping.get(Path(img_filename).name)
                        if cdn_url:
                            self._insert_diagram(
                                question_id=question_id,
                                cdn_url=cdn_url,
                                diagram_type=f"option_{option}",
                                page_number=question.get("page")
                            )
                            diagrams_inserted += 1
                
                print(f"  ✅ Question {question['question_number']}: {len(question.get('stem_images', []))} stem + {sum(len(v) for v in question.get('option_images', {}).values())} option images")
                
            except Exception as e:
                errors.append({
                    "question_number": question.get("question_number"),
                    "error": str(e)
                })
                print(f"  ❌ Question {question.get('question_number')}: {e}")
        
        report = {
            "questions_inserted": questions_inserted,
            "diagrams_inserted": diagrams_inserted,
            "errors": errors
        }
        
        print(f"\n✅ Import complete: {questions_inserted} questions, {diagrams_inserted} diagrams")
        
        return report
    
    def _insert_question(
        self,
        question_number: int,
        paper_code: str,
        subject: str,
        difficulty: Optional[str] = None,
        topics: Optional[List[str]] = None
    ) -> str:
        """Insert question and return question_id"""
        self.cur.execute("""
            INSERT INTO questions (
                question_number, 
                paper_code, 
                subject, 
                difficulty, 
                topics
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (question_number, paper_code, subject, difficulty, topics or []))
        
        return self.cur.fetchone()[0]
    
    def _insert_diagram(
        self,
        question_id: str,
        cdn_url: str,
        diagram_type: str,
        page_number: Optional[int] = None
    ):
        """Insert diagram record"""
        self.cur.execute("""
            INSERT INTO diagrams (
                question_id, 
                cdn_url, 
                diagram_type, 
                page_number
            )
            VALUES (%s, %s, %s, %s)
        """, (question_id, cdn_url, diagram_type, page_number))
    
    def insert_flashcards(
        self,
        question_id: str,
        flashcards: List[Dict]
    ):
        """
        Insert flashcards for a question
        
        Args:
            question_id: Question UUID
            flashcards: List of {option_letter, front_text, back_text, concept_gap}
        """
        if not flashcards:
            return
        
        values = [
            (
                question_id,
                fc["option_letter"],
                fc["front_text"],
                fc["back_text"],
                fc.get("concept_gap")
            )
            for fc in flashcards
        ]
        
        execute_values(
            self.cur,
            """
            INSERT INTO flashcards (
                question_id, 
                option_letter, 
                front_text, 
                back_text, 
                concept_gap
            )
            VALUES %s
            """,
            values
        )
    
    def insert_concept_gaps(
        self,
        question_id: str,
        concept_gaps: List[Dict]
    ):
        """
        Insert concept gaps for a question
        
        Args:
            question_id: Question UUID
            concept_gaps: List of {option_letter, gap_description}
        """
        if not concept_gaps:
            return
        
        values = [
            (question_id, cg["option_letter"], cg["gap_description"])
            for cg in concept_gaps
        ]
        
        execute_values(
            self.cur,
            """
            INSERT INTO concept_gaps (
                question_id, 
                option_letter, 
                gap_description
            )
            VALUES %s
            """,
            values
        )


def create_schema(connection_string: str):
    """Create database schema if it doesn't exist"""
    conn = psycopg2.connect(connection_string)
    cur = conn.cursor()
    
    # Create questions table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            question_number INT NOT NULL,
            paper_code TEXT NOT NULL,
            subject TEXT NOT NULL,
            question_text TEXT,
            options JSONB,
            correct_answer TEXT,
            explanation TEXT,
            core_concept TEXT,
            difficulty TEXT,
            topics TEXT[],
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_questions_paper ON questions(paper_code);
        CREATE INDEX IF NOT EXISTS idx_questions_subject ON questions(subject);
    """)
    
    # Create diagrams table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS diagrams (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            question_id UUID REFERENCES questions(id) ON DELETE CASCADE,
            cdn_url TEXT NOT NULL,
            diagram_type TEXT,
            page_number INT,
            alt_text TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_diagrams_question ON diagrams(question_id);
    """)
    
    # Create flashcards table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS flashcards (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            question_id UUID REFERENCES questions(id) ON DELETE CASCADE,
            option_letter TEXT,
            front_text TEXT NOT NULL,
            back_text TEXT NOT NULL,
            concept_gap TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_flashcards_question ON flashcards(question_id);
    """)
    
    # Create concept_gaps table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS concept_gaps (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            question_id UUID REFERENCES questions(id) ON DELETE CASCADE,
            option_letter TEXT,
            gap_description TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_concept_gaps_question ON concept_gaps(question_id);
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    
    print("✅ Database schema created successfully")


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Import questions to database")
    parser.add_argument("json_path", help="Path to extracted JSON file")
    parser.add_argument("--cdn-mapping", required=True, help="Path to CDN mapping JSON")
    parser.add_argument("--db-url", help="Database connection string (or use DATABASE_URL env var)")
    parser.add_argument("--paper-code", required=True, help="Paper code (e.g., 9701_s25_qp_13)")
    parser.add_argument("--subject", required=True, choices=["Biology", "Chemistry", "Physics"])
    parser.add_argument("--difficulty", choices=["Easy", "Medium", "Hard"])
    parser.add_argument("--topics", nargs="+", help="Topic tags")
    parser.add_argument("--create-schema", action="store_true", help="Create schema before import")
    
    args = parser.parse_args()
    
    # Get database URL
    db_url = args.db_url or os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ Error: Database URL required (--db-url or DATABASE_URL env var)")
        sys.exit(1)
    
    # Create schema if requested
    if args.create_schema:
        create_schema(db_url)
    
    # Load CDN mapping
    with open(args.cdn_mapping) as f:
        cdn_data = json.load(f)
        cdn_mapping = cdn_data.get("cdn_mapping", cdn_data)
    
    # Import
    with DatabaseImporter(db_url) as importer:
        report = importer.import_questions(
            json_path=args.json_path,
            cdn_mapping=cdn_mapping,
            paper_code=args.paper_code,
            subject=args.subject,
            difficulty=args.difficulty,
            topics=args.topics
        )
    
    # Exit with error code if any imports failed
    sys.exit(0 if len(report["errors"]) == 0 else 1)


if __name__ == "__main__":
    main()
