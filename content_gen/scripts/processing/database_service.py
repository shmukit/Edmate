import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class DatabaseService:
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable is not set")

    def get_connection(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def inject_question(self, question_data: dict):
        """
        Injects a processed question into the standardized 'questions' table.
        
        Expected fields in question_data:
        - title (standardized HTML with base64 images)
        - type (USER-DEFINED, e.g., 'MULTIPLE_CHOICE')
        - subjectId
        - topicId
        - subtopicId (optional)
        - options (JSON array)
        - correctOptions (JSON array)
        - optionExplanations (JSON array)
        - detailedExplanation
        - difficultyLevel (USER-DEFINED)
        - source (USER-DEFINED)
        - year
        - session
        - variant
        - grade
        - examBoard
        - question_identifier
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Standardized injection into the 'questions' table
                # Note: We must ensure user-defined types match exactly.
                
                query = """
                INSERT INTO questions (
                    id, title, type, "subjectId", "topicId", "subtopicId", 
                    options, "correctOptions", "optionExplanations", 
                    "detailedExplanation", "difficultyLevel", source, 
                    year, session, variant, grade, "examBoard", 
                    question_identifier, "isActive", "createdAt", "updatedAt", "isValidated"
                ) VALUES (
                    uuid_generate_v4(), %s, %s::"QuestionType", %s, %s, %s, 
                    %s, %s, %s, 
                    %s, %s::"Difficulty", %s::"Source", 
                    %s, %s, %s, %s, %s, 
                    %s, true, NOW(), NOW(), false
                )
                """
                
                params = (
                    question_data.get('title'),
                    question_data.get('type', 'MCQ_SINGLE'), # Updated to match production enum
                    question_data.get('subjectId'),
                    question_data.get('topicId'),
                    question_data.get('subtopicId'),
                    question_data.get('options'),
                    question_data.get('correctOptions'),
                    question_data.get('optionExplanations'),
                    question_data.get('detailedExplanation'),
                    question_data.get('difficultyLevel', 'MEDIUM'),
                    question_data.get('source', 'PAST_PAPER'),
                    question_data.get('year'),
                    question_data.get('session'),
                    question_data.get('variant'),
                    question_data.get('grade'),
                    question_data.get('examBoard'),
                    question_data.get('question_identifier')
                )
                
                cur.execute(query, params)
                conn.commit()
                return True
        except Exception as e:
            print(f"Injection Error: {e}")
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_subject_topic_ids(self, subject_name: str, topic_name: str):
        """Helper to find IDs for migration cleanup"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM subjects WHERE name ILIKE %s", (subject_name,))
                subject = cur.fetchone()
                if not subject: return None, None
                
                cur.execute("SELECT id FROM topics WHERE name ILIKE %s AND \"subjectId\" = %s", (topic_name, subject['id']))
                topic = cur.fetchone()
                if not topic: return subject['id'], None
                
                return subject['id'], topic['id']
        finally:
            conn.close()
