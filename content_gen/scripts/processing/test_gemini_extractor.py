import os
from pathlib import Path
from dotenv import load_dotenv
from content_gen.scripts.processing.gemini_extractor import GeminiExtractor

# Load environment
env_path = Path("content_gen/.env")
load_dotenv(dotenv_path=env_path)

def test_extractor():
    # We need a sample PDF. Let's see if any exist.
    pdf_dir = Path("content_gen/data/inputs")
    pdfs = list(pdf_dir.glob("*.pdf"))
    
    if not pdfs:
        print("❌ No PDFs found in content_gen/data/pdfs for testing.")
        return

    test_pdf = str(pdfs[0])
    print(f"Testing GeminiExtractor with: {test_pdf}")
    
    try:
        extractor = GeminiExtractor()
        # Only process first page for testing to save tokens
        images = extractor.pdf_to_images(test_pdf)
        if images:
            results = extractor.extract_questions_from_page(images[0], 1)
            print("Successfully extracted questions from page 1:")
            import json
            print(json.dumps(results, indent=2))
        else:
            print("❌ No images generated from PDF.")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_extractor()
