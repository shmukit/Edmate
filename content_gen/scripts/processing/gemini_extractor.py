import os
import json
import base64
import fitz
from pathlib import Path
from typing import List, Dict, Optional
from google import genai
from google.genai import types
from PIL import Image
import io

# Import local utilities
from .image_utils import ImageHandler
from .database_service import DatabaseService

# Import Opik for telemetry
try:
    import opik
    from opik import opik_context
except ImportError:
    opik = None
    opik_context = None

class GeminiExtractor:
    def __init__(self, model_id: str = "gemini-2.5-flash"):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        # Initialize GenAI Client
        if self.creds_path and os.path.exists(self.creds_path):
            # Use Vertex AI (GCP)
            self.client = genai.Client(
                vertexai=True,
                project="mcq-master-490011",
                location="asia-south1"
            )
        elif self.api_key:
            # Fallback to API Key (Google AI Studio)
            self.client = genai.Client(api_key=self.api_key)
        else:
            raise ValueError("Missing Gemini credentials (GEMINI_API_KEY or GOOGLE_APPLICATION_CREDENTIALS)")
            
        self.model_id = model_id

    def pdf_to_images(self, pdf_path: str, dpi: int = 200) -> List[Image.Image]:
        """Convert PDF pages to PIL images for Gemini"""
        doc = fitz.open(pdf_path)
        images = []
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
            img_data = pix.tobytes("png")
            images.append(Image.open(io.BytesIO(img_data)))
        doc.close()
        return images

    @opik.track(project_name="Edmate") if opik else lambda x: x
    def extract_questions_from_page(self, page_image: Image.Image, page_num: int) -> List[Dict]:
        """Send a single page image to Gemini and extract structured questions with analysis"""
        
        # Convert PIL to bytes for Gemini
        img_byte_arr = io.BytesIO()
        page_image.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()
        
        prompt = """
        You are an advanced OCR and educational expert.
        Analyze the provided image of an exam paper and extract ALL multiple-choice questions.
        
        For each question, perform a full educational analysis:
        1. Core Concept: Summarize the main principle.
        2. Detailed Explanation: Provide step-by-step logic leading to the answer. 
           CRITICAL: End this section with "**Final Correct Answer: [LETTER]**".
3. Option Analysis: Explain why each option (A, B, C, D) is correct or incorrect.
        4. Flashcards: Generate 2-3 conceptual flashcards.
        
        Return the data in a valid JSON list following the provided schema.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[
                    types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=types.Schema(
                        type="ARRAY",
                        items=types.Schema(
                            type="OBJECT",
                            properties={
                                "question_number": types.Schema(type="INTEGER"),
                                "text": types.Schema(type="STRING"),
                                "options": types.Schema(
                                    type="OBJECT",
                                    properties={
                                        "A": types.Schema(type="STRING"),
                                        "B": types.Schema(type="STRING"),
                                        "C": types.Schema(type="STRING"),
                                        "D": types.Schema(type="STRING"),
                                    }
                                ),
                                "generated_content": types.Schema(
                                    type="OBJECT",
                                    properties={
                                        "core_concept": types.Schema(type="STRING"),
                                        "detailed_explanation": types.Schema(type="STRING"),
                                        "option_analysis": types.Schema(
                                            type="OBJECT",
                                            properties={
                                                "A": types.Schema(type="STRING"),
                                                "B": types.Schema(type="STRING"),
                                                "C": types.Schema(type="STRING"),
                                                "D": types.Schema(type="STRING"),
                                            }
                                        ),
                                        "flashcards": types.Schema(
                                            type="ARRAY",
                                            items=types.Schema(
                                                type="OBJECT",
                                                properties={
                                                    "question": types.Schema(type="STRING"),
                                                    "answer": types.Schema(type="STRING"),
                                                }
                                            )
                                        )
                                    }
                                )
                            }
                        )
                    )
                )
            )
            
            # Log usage metadata for Opik if available
            if opik and opik_context and response.usage_metadata:
                opik_context.update_current_span(
                    usage={
                        "prompt_tokens": response.usage_metadata.prompt_token_count,
                        "completion_tokens": response.usage_metadata.candidates_token_count,
                        "total_tokens": response.usage_metadata.total_token_count,
                    }
                )

            return json.loads(response.text)
        except Exception as e:
            print(f"Error parsing Gemini response for page {page_num}: {e}")
            return []

    @opik.track(project_name="Edmate") if opik else lambda x: x
    def process_pdf(self, pdf_path: str) -> Dict:
        """Full pipeline: PDF -> Images -> Gemini -> Structured JSON with Analysis"""
        print(f"🚀 Processing PDF: {pdf_path}")
        images = self.pdf_to_images(pdf_path)
        all_questions = []
        
        for i, img in enumerate(images):
            print(f"  Processing page {i+1}...")
            questions = self.extract_questions_from_page(img, i+1)
            for q in questions:
                q['page'] = i + 1
            all_questions.extend(questions)
            
        return {
            "source": pdf_path,
            "papers_code": Path(pdf_path).stem,
            "questions": all_questions
        }
