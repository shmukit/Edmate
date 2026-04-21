import os
import json
import io
import uuid
import fitz
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from PIL import Image
import base64
from google import genai
from google.genai import types
from openai import OpenAI

# Import local utilities
from .modality_registry import get_modalities, MODALITIES
from .image_utils import ImageHandler

# Import Opik for telemetry
try:
    import opik
    from opik import opik_context
except ImportError:
    opik = None
    opik_context = None

class AutomationEngine:
    """
    Modular engine for automated content generation.
    Supports dynamic modalities, providers, and input formats.
    """
    
    def __init__(self, provider: str = "gemini", model_id: Optional[str] = None):
        self.provider = provider.lower()
        self.api_key = os.getenv("GEMINI_API_KEY") if "gemini" in self.provider else os.getenv("OPENAI_API_KEY")
        self.creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        if "gemini" in self.provider:
            self._init_gemini(model_id or "gemini-2.5-flash")
        elif "openai" in self.provider:
            self._init_openai(model_id or "gpt-4o")
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def _init_gemini(self, model_id: str):
        if self.creds_path and os.path.exists(self.creds_path):
            self.client = genai.Client(vertexai=True, project="mcq-master-490011", location="asia-south1")
        elif os.getenv("GEMINI_API_KEY"):
            self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        else:
            raise ValueError("Missing Gemini credentials")
        self.model_id = model_id

    def _init_openai(self, model_id: str):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model_id = model_id

    def _build_dynamic_prompt(self, modalities: List[str], lang: str = "English", curriculum: str = "Cambridge O/Level") -> str:
        selected = get_modalities(modalities)
        
        prompt = f"""
        You are an advanced OCR and educational expert specializing in {curriculum}.
        Analyze the provided context (image or text) and extract ALL multiple-choice questions.
        
        IMPORTANT: If a question or its OPTIONS include a diagram, chart, or image, identify its location on the page.
        Provide diagrams' bounding boxes in normalized coordinates [ymin, xmin, ymax, xmax] (0-1000).
        
        CRITICAL CROP RULES:
        1. CRITICAL: Use the TIGHTEST POSSIBLE bounding box for the diagram ONLY. 
        2. EXCLUDE any text above/below the diagram (like question text or page numbers).
        3. If a diagram is inside Option A, B, C, or D, provide it in the 'option_X_diagram_coords' field.
        
        For each question, perform the following analysis:
        """
        
        for i, mod in enumerate(selected):
            prompt += f"\n{i+1}. {mod.name}: {mod.prompt_chunk}"
            
        prompt += """
        
        Return the data in a valid JSON list following the provided schema.
        If a question has a diagram, indicate its position with [DIAGRAM] in the text and provide 'diagram_coords'. 
        If no diagram is present, 'diagram_coords' must be null.
        """
        return prompt

    def _build_dynamic_schema(self, modality_ids: List[str]) -> types.Schema:
        """Builds a dynamic Google GenAI response schema"""
        selected = get_modalities(modality_ids)
        
        base_properties = {
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
            "diagram_coords": types.Schema(
                type="ARRAY",
                items=types.Schema(type="INTEGER"),
                description="Main question diagram [ymin, xmin, ymax, xmax]"
            ),
            "option_A_diagram_coords": types.Schema(type="ARRAY", items=types.Schema(type="INTEGER")),
            "option_B_diagram_coords": types.Schema(type="ARRAY", items=types.Schema(type="INTEGER")),
            "option_C_diagram_coords": types.Schema(type="ARRAY", items=types.Schema(type="INTEGER")),
            "option_D_diagram_coords": types.Schema(type="ARRAY", items=types.Schema(type="INTEGER"))
        }
        
        # Add generated content properties
        gc_properties = {}
        for mod in selected:
            gc_properties.update(mod.schema_fragment)
            
        if gc_properties:
            base_properties["generated_content"] = types.Schema(
                type="OBJECT",
                properties=gc_properties
            )
            
        return types.Schema(
            type="ARRAY",
            items=types.Schema(
                type="OBJECT",
                properties=base_properties
            )
        )

    @opik.track(project_name="Edmate") if opik else lambda x: x
    def process_pdf(self, pdf_path: str, config: Dict[str, Any], progress_callback: Optional[Callable[[float], None]] = None) -> List[Dict]:
        """Processes a PDF using the specified modular configuration"""
        modalities = config.get("modalities", ["core_concept", "detailed_explanation", "option_analysis", "flashcards"])
        lang = config.get("language", "English")
        curriculum = config.get("curriculum", "Cambridge O/Level")
        
        doc = fitz.open(pdf_path)
        all_questions = []
        total_pages = len(doc)
        
        prompt = self._build_dynamic_prompt(modalities, lang, curriculum)
        schema = self._build_dynamic_schema(modalities)
        
        for i, page in enumerate(doc):
            print(f"  Processing page {i+1}/{total_pages}...")
            # Use high-res for extraction, but we'll also use this for cropping
            zoom = 2
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            img_bytes = pix.tobytes("png")
            
            questions = self._call_llm(img_bytes, prompt, schema)
            
            # Post-process diagrams
            if questions:
                self._extract_diagrams(img_bytes, questions)
                
            for q in questions:
                q['page'] = i + 1
            all_questions.extend(questions)
            
            # Report progress
            if progress_callback:
                progress_callback(((i + 1) / total_pages) * 100)
            
        doc.close()
        return all_questions

    def _extract_diagrams(self, img_bytes: bytes, questions: List[Dict]):
        """Crops diagrams from the page image based on LLM-provided coordinates"""
        try:
            img = Image.open(io.BytesIO(img_bytes))
            width, height = img.size
            
            for q in questions:
                # Find all coordinator fields (main and options)
                coord_fields = [f for f in q.keys() if f.endswith("_coords") and q[f]]
                
                for field in coord_fields:
                    coords = q.get(field)
                    if not coords or len(coords) != 4: continue
                    
                    # Normalize: [ymin, xmin, ymax, xmax] (0-1000)
                    ymin, xmin, ymax, xmax = coords
                    # Convert to pixel coordinates
                    left = (xmin / 1000) * width
                    top = (ymin / 1000) * height
                    right = (xmax / 1000) * width
                    bottom = (ymax / 1000) * height
                    
                    # Sanity check for crop area
                    if right > left and bottom > top:
                        # Tighter crop for clearer extraction
                        padding = 2
                        left = max(0, left - padding)
                        top = max(0, top - padding)
                        right = min(width, right + padding)
                        bottom = min(height, bottom + padding)
                        
                        cropped_img = img.crop((left, top, right, bottom))
                        
                        # Convert to base64
                        buffered = io.BytesIO()
                        cropped_img.save(buffered, format="PNG")
                        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                        
                        # Store in the appropriate base64 field
                        target_field = field.replace("_coords", "_base64")
                        q[target_field] = f"data:image/png;base64,{img_str}"
        except Exception as e:
            print(f"  Diagram extraction failed: {e}")

    def _call_llm(self, img_bytes: bytes, prompt: str, schema: Any) -> List[Dict]:
        """Dispatches the call to the appropriate provider"""
        if "gemini" in self.provider:
            return self._call_gemini(img_bytes, prompt, schema)
        elif "openai" in self.provider:
            return self._call_openai(img_bytes, prompt) # OpenAI uses text-based guidance for schema
        return []

    def _call_gemini(self, img_bytes: bytes, prompt: str, schema: Any) -> List[Dict]:
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=[
                types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema
            )
        )
        
        if opik and opik_context and response.usage_metadata:
            opik_context.update_current_span(
                usage={
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "completion_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count,
                }
            )
            
        return json.loads(response.text)

    def _call_openai(self, img_bytes: bytes, prompt: str) -> List[Dict]:
        # Implementation for OpenAI (Vision + JSON Mode)
        # Note: OpenAI handles schema differently, often via system message or function calling
        # For simplicity in this v2 architecture, we use JSON response format
        base64_img = base64.b64encode(img_bytes).decode('utf-8')
        
        response = self.client.chat.completions.create(
            model=self.model_id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt + "\nReturn a JSON array of questions."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_img}"}}
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )
        # OpenAI cost/tokens are tracked by track_openai wrapper if active
        data = json.loads(response.choices[0].message.content)
        # Extract the list if wrapped in an object like {"questions": [...]}
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list): return v
        return data if isinstance(data, list) else []
