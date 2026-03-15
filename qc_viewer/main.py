import os
import uvicorn
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Edmate QC Viewer")

# Allow CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# Tables mapping
TABLES = ["chemistry_questions", "igcse_biology_questions", "biology_questions", "physics_questions"]

@app.get("/api/papers")
async def get_papers():
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    papers = []
    try:
        with conn.cursor() as cur:
            for table in TABLES:
                # Check if table exists
                cur.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')")
                if not cur.fetchone()['exists']:
                    continue
                
                cur.execute(f"SELECT DISTINCT paper_code FROM {table} WHERE paper_code IS NOT NULL")
                rows = cur.fetchall()
                for row in rows:
                    papers.append({"code": row['paper_code'], "table": table})
    finally:
        conn.close()
    
    return sorted(papers, key=lambda x: x['code'])

@app.get("/api/questions")
async def get_questions(table: str, paper_code: str):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT id, question_identifier, 
                       split_part(question_identifier, '/Q', 2) as question_number, 
                       title, options, 
                       correct_options, option_explanations, summary_explanation, 
                       detailed_explanation, is_verified, diagrams
                FROM {table}
                WHERE paper_code = %s
                ORDER BY length(split_part(question_identifier, '/Q', 2)), question_identifier
            """, (paper_code,))
            questions = cur.fetchall()
            return questions
    finally:
        conn.close()

@app.get("/api/flashcards")
async def get_flashcards(question_id: str):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, front_text, back_text, topic_id, subtopic_id
                FROM flashcards
                WHERE id::text IN (
                    -- This is a bit tricky if we don't have a direct mapping table yet
                    -- Assuming for now we filter by question context or if they are linked
                    -- In reality, we'll need a way to link them. 
                    -- Based on my insert_flashcards, they aren't explicitly linked to a question ID in the schema I saw.
                    -- Let's check the schema again or use a placeholder logic.
                    SELECT id::text FROM flashcards LIMIT 0 -- Placeholder
                )
            """)
            # Actually, let's use a simpler query for now since I don't see a question_id in flashcards table
            # In generate_and_sync.py, I insert them with topic_id and subtopic_id.
            # Let's fetch by topic/subtopic for now if provided?
            return []
    finally:
        conn.close()

@app.get("/api/stats")
async def get_stats():
    conn = get_db_connection()
    if not conn:
        return {"error": "DB connection failed"}
    try:
        with conn.cursor() as cur:
            stats = {}
            for table in TABLES:
                cur.execute(f"SELECT count(*) FROM {table}")
                stats[table] = cur.fetchone()['count']
            return stats
    finally:
        conn.close()

# Serve static files
app.mount("/", StaticFiles(directory="qc_viewer/static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
