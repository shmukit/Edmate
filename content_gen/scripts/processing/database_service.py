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

    def inject_question(self, table_name: str, question_data: dict):
        """
        Injects a processed question into a subject-specific table.
        """
        if not table_name:
            raise ValueError("table_name is required for injection")
            
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # The 'questions' table uses camelCase quoted columns (Prisma style)
                # subject-specific tables use snake_case. 
                # We prioritize the 'questions' table as requested by the user.
                
                if table_name == "questions":
                    query = f"""
                    INSERT INTO {table_name} (
                        id, question_identifier, title, options, 
                        "correctOptions", "optionExplanations", 
                        "detailedExplanation", "topicId", "subtopicId",
                        "isActive", "isValidated", "createdAt", "updatedAt"
                    ) VALUES (
                        uuid_generate_v4(), %s, %s, %s, 
                        %s, %s, 
                        %s, %s, %s,
                        true, false, NOW(), NOW()
                    ) RETURNING id
                    """
                else:
                    # Subject-specific tables (snake_case)
                    query = f"""
                    INSERT INTO {table_name} (
                        id, question_identifier, title, options, 
                        correct_options, option_explanations, 
                        detailed_explanation, topic_id, subtopic_id,
                        other_contents, is_verified, "createdAt", "updatedAt"
                    ) VALUES (
                        uuid_generate_v4(), %s, %s, %s, 
                        %s, %s, 
                        %s, %s, %s,
                        %s, false, NOW(), NOW()
                    ) RETURNING id
                    """
                
                params = (
                    question_data.get('question_identifier'),
                    question_data.get('title'),
                    question_data.get('options'),
                    question_data.get('correct_options', [0]),
                    question_data.get('option_explanations', []),
                    question_data.get('detailed_explanation'),
                    question_data.get('topic_id'),
                    question_data.get('subtopic_id'),
                )
                
                if table_name != "questions":
                    params += (question_data.get('diagrams', []),)
                
                cur.execute(query, params)
                question_id = cur.fetchone()['id']
                
                # Inject Flashcards if present
                flashcards = question_data.get('flashcards', [])
                if flashcards:
                    for fc in flashcards:
                        cur.execute("""
                            INSERT INTO flashcards (
                                id, question, answer, "topicId", "subtopicId", "createdAt", "updatedAt"
                            ) VALUES (
                                uuid_generate_v4(), %s, %s, %s, %s, NOW(), NOW()
                            )
                        """, (
                            fc.get('question'), 
                            fc.get('answer'), 
                            question_data.get('topic_id'),
                            question_data.get('subtopic_id')
                        ))
                
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
