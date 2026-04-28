import requests
import time
import os

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
PDF_PATH = "content_gen/data/inputs/9701_s24_qp_11 (1).pdf"  # Using a real test PDF
OPENAI_KEY = os.getenv("OPENAI_API_KEY") 
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

def process_document():
    # 1. Start the extraction
    print(f"🚀 Starting extraction for {PDF_PATH}...")
    
    headers = {}
    if GEMINI_KEY:
        headers["X-Gemini-Key"] = GEMINI_KEY
    elif OPENAI_KEY:
        headers["X-OpenAI-Key"] = OPENAI_KEY
        
    with open(PDF_PATH, "rb") as f:
        response = requests.post(
            f"{API_BASE_URL}/extract",
            files={"file": f},
            data={"curriculum": "Cambridge O/Level", "subject": "Biology"},
            headers=headers
        )
    
    if response.status_code != 200:
        print(f"❌ Error: {response.text}")
        return

    job_id = response.json()["job_id"]
    print(f"✅ Job created: {job_id}. Waiting for processing...")

    # 2. Poll for status
    while True:
        status_res = requests.get(f"{API_BASE_URL}/jobs/{job_id}")
        data = status_res.json()
        
        status = data.get("status")
        print(f"⏳ Current Status: {status}")
        
        if status == "COMPLETED":
            print("\n🎉 SUCCESS! Extracted Questions:")
            for i, q in enumerate(data.get("questions", [])):
                print(f"\n{i+1}. {q['question_text']}")
                print(f"   Core Concept: {q['explanations']['core_concept']}")
            break
        elif status == "FAILED":
            print(f"❌ Processing failed: {data.get('error')}")
            break
            
        time.sleep(5)

if __name__ == "__main__":
    # Create a dummy PDF if none exists for testing
    if not os.path.exists(PDF_PATH):
        print(f"Creating dummy {PDF_PATH} for testing...")
        with open(PDF_PATH, "w") as f:
            f.write("%PDF-1.4 dummy content")
            
    process_document()
