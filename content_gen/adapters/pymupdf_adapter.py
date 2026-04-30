import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Optional, Callable
from content_gen.adapters.base_extraction import BaseExtractionAdapter
from content_gen.core.schemas import ProcessedQuestion


class PyMuPDFAdapter(BaseExtractionAdapter):
    """
    Lightweight, CPU-only PDF extractor.
    Optimized for text extraction without the overhead of vision models.
    """

    def extract_content(
        self, 
        source_path: Path, 
        output_dir: Path, 
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> List[ProcessedQuestion]:
        print(f"📄 Extracting text via PyMuPDF (Regex-Enabled): {source_path.name}")
        import re
        doc = fitz.open(str(source_path))
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n---PAGE_BREAK---\n"

        # Look for question markers like "1 \n Which row..." or "\n 1 \n"
        # Stricter pattern: Digit on a line, followed by a line starting with an Uppercase letter
        pattern = re.compile(r'\n(\d{1,2})\s*\n(?=[A-Z])')
        parts = pattern.split(full_text)
        
        # parts will be [header_text, "1", q1_text, "2", q2_text, ...]
        questions = []
        
        questions_dict = {}
        if len(parts) > 1:
            for i in range(1, len(parts), 2):
                q_num = int(parts[i])
                q_text = parts[i+1].strip()
                
                # Basic cleaning: remove page breaks and codes
                q_text = q_text.replace("---PAGE_BREAK---", "")
                q_text = re.sub(r'© UCLES.*', '', q_text)
                q_text = re.sub(r'9702/.*', '', q_text)
                
                # Split options if they exist (A, B, C, D)
                options = {}
                opt_pattern = re.compile(r'\n([A-D])\s*\n')
                opt_parts = opt_pattern.split(q_text)
                
                if len(opt_parts) > 1:
                    stem = opt_parts[0].strip()
                    for j in range(1, len(opt_parts), 2):
                        options[opt_parts[j]] = opt_parts[j+1].strip().split('\n')[0] # Get first line of option
                    q_text = stem

                # Store in dict for merging (basic merge: concat text)
                if q_num not in questions_dict:
                    questions_dict[q_num] = {
                        "text": q_text,
                        "options": options
                    }
                else:
                    questions_dict[q_num]["text"] += " " + q_text
                    # Simple merge for options if they were missing before
                    if not questions_dict[q_num]["options"] and options:
                        questions_dict[q_num]["options"] = options

            # Convert dict to ProcessedQuestion objects
            for q_num in sorted(questions_dict.keys()):
                data = questions_dict[q_num]
                questions.append(
                    ProcessedQuestion(
                        question_number=q_num,
                        question_text=data["text"][:2000],
                        options=data["options"],
                        subject="General",
                        metadata={"engine": "pymupdf_regex"}
                    )
                )
        else:
            # Fallback to single block if no numbers found
            questions = [
                ProcessedQuestion(
                    question_number=1,
                    question_text=full_text[:2000].replace("---PAGE_BREAK---", ""),
                    subject="General",
                    metadata={"engine": "pymupdf_fallback"}
                )
            ]
            
        doc.close()
        return questions

    def get_supported_formats(self) -> List[str]:
        return [".pdf"]
