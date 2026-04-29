import fitz
import base64
import json
import io
from pathlib import Path
from typing import List, Dict, Optional, Callable
from PIL import Image
from content_gen.adapters.base_extraction import BaseExtractionAdapter
from content_gen.core.schemas import ProcessedQuestion
from content_gen.core.model_router import ModelRoutingEngine

EXTRACTION_SYSTEM_PROMPT = """
You are an expert at extracting structured educational content from exam paper images.
Your goal is to identify each question and its options with 100% accuracy.

### CRITICAL RULES:
1. **Identification**: Every question typically starts with a number. Capture the full text of the question (the "stem").
2. **Options**: MCQs always have options (usually A, B, C, D). If you see options, extract them into the "options" object.
3. **Spatial Intelligence**: If a diagram, graph, or table is placed near a question, it belongs to that question. Provide its coordinates.
4. **No Refusals**: Even if the text is blurry, use your domain knowledge (O/A-Level) to reconstruct the most likely intended text.

For each question found, return a JSON object with:
- question_number: (int)
- question_text: (str) include the stem and any text before options.
- options: (dict) mapping A, B, C, D to their text.
- correct_answer: (str) optional, if identifiable (e.g. "A").
- diagram_coords: [ymin, xmin, ymax, xmax] (list of 4 ints, 0-1000) for relevant visuals.

Return a JSON array of these objects under a "questions" key.
"""

class VisionExtractionAdapter(BaseExtractionAdapter):
    """
    High-fidelity extraction adapter using Multimodal LLMs (Vision).
    Restores the spatial intelligence of the legacy system while maintaining modularity.
    """

    def __init__(self, router: ModelRoutingEngine):
        self.router = router

    def extract_content(
        self, 
        source_path: Path, 
        output_dir: Path, 
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> List[ProcessedQuestion]:
        print(f"👁️  Extracting via Vision LLM: {source_path.name}")
        
        if progress_callback:
            progress_callback(20, "Initializing Vision AI context...")
        
        doc = fitz.open(str(source_path))
        all_questions = []
        
        # Create image output directory
        images_dir = output_dir / "images" / source_path.stem
        images_dir.mkdir(parents=True, exist_ok=True)

        for i, page in enumerate(doc):
            print(f"  Processing page {i+1}/{len(doc)}...")
            
            if progress_callback:
                prog = 20 + int(((i + 1) / len(doc)) * 30)
                progress_callback(prog, f"Extracting content from page {i+1} via Vision AI...")
            
            # 1. Convert page to high-res image for LLM
            zoom = 2
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            img_bytes = pix.tobytes("png")
            
            # Base64 encode for litellm/router
            base64_img = f"data:image/png;base64,{base64.b64encode(img_bytes).decode('utf-8')}"
            
            # 2. Call Vision LLM via Router
            try:
                response_text = self.router.generate_content(
                    prompt="Extract all questions from this page image as structured JSON.",
                    task_type="extraction",
                    system_prompt=EXTRACTION_SYSTEM_PROMPT,
                    images=[base64_img],
                    json_mode=True
                )
                
                page_data = json.loads(response_text)
                if isinstance(page_data, dict):
                    # Handle if LLM wraps in a "questions" key
                    page_questions = page_data.get("questions", []) if "questions" in page_data else [page_data]
                else:
                    page_questions = page_data

                # 3. Process each extracted question (diagram cropping)
                for q_data in page_questions:
                    q_num = q_data.get("question_number", 0)
                    if q_num == 0: continue # Skip if no question number detected
                    
                    diagram_path = None
                    coords = q_data.get("diagram_coords")
                    
                    if coords and len(coords) == 4:
                        diagram_path = self._crop_diagram(img_bytes, coords, q_num, i+1, images_dir)

                    # Map to ProcessedQuestion
                    question = ProcessedQuestion(
                        question_number=q_num,
                        question_text=q_data.get("question_text", ""),
                        options=q_data.get("options", {}),
                        correct_options=[q_data.get("correct_answer")] if q_data.get("correct_answer") else [],
                        subject="General", # Default, generator will refine
                        metadata={
                            "page": i + 1,
                            "stem_images": [str(diagram_path)] if diagram_path else [],
                            "engine": "vision_multimodal"
                        }
                    )
                    all_questions.append(question)
                    
            except Exception as e:
                print(f"  ❌ Error processing page {i+1}: {e}")

        doc.close()
        return all_questions

    def _crop_diagram(self, img_bytes: bytes, coords: List[int], q_num: int, page_num: int, output_dir: Path) -> Optional[Path]:
        """Crops a diagram from the page image based on LLM-provided 0-1000 coordinates."""
        try:
            img = Image.open(io.BytesIO(img_bytes))
            width, height = img.size

            # Normalize: [ymin, xmin, ymax, xmax] (0-1000)
            ymin, xmin, ymax, xmax = coords
            
            # Convert to pixel coordinates
            left = (xmin / 1000) * width
            top = (ymin / 1000) * height
            right = (xmax / 1000) * width
            bottom = (ymax / 1000) * height

            if right > left and bottom > top:
                # Add slight padding
                padding = 5
                left = max(0, left - padding)
                top = max(0, top - padding)
                right = min(width, right + padding)
                bottom = min(height, bottom + padding)

                cropped_img = img.crop((left, top, right, bottom))
                
                filename = f"q{q_num}_p{page_num}_diagram.png"
                filepath = output_dir / filename
                cropped_img.save(filepath)
                return filepath
        except Exception as e:
            print(f"    ⚠️ Diagram cropping failed: {e}")
        return None

    def get_supported_formats(self) -> List[str]:
        return [".pdf"]
