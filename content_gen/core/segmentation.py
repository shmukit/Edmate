import re
from typing import List, Dict

class TextSegmentationUtility:
    """
    Utility to segment exam text into sections and individual questions.
    Specifically tuned for Bangladeshi exam formats.
    """
    
    SECTION_PATTERN = r'(?i)Section\s+([A-Z]):\s*(.*?)(?=\nSection\s+[A-Z]:|\nTHE END| \.\.\.|$)'
    QUESTION_PATTERN = r'(?m)^(\d+)\.\s*(.*?)(?=\n\d+\.\s*|\nSection|\nTHE END|$)'
    OPTION_PATTERN = r'([A-D])\.\s*(.*?)(?=\s+[A-D]\.|$)'

    @classmethod
    def segment_exam(cls, full_text: str) -> List[Dict]:
        """
        Segments the full text into a list of questions with metadata.
        """
        sections = re.findall(cls.SECTION_PATTERN, full_text, re.DOTALL)
        all_questions = []
        
        for section_letter, section_content in sections:
            section_type = cls._infer_section_type(section_content)
            
            # Find questions in this section
            questions = re.findall(cls.QUESTION_PATTERN, section_content, re.DOTALL)
            
            for q_num, q_body in questions:
                # Extract options if it's an MCQ section or if options are present
                options = {}
                if section_type == "MCQ" or "A." in q_body:
                    opt_matches = re.findall(cls.OPTION_PATTERN, q_body)
                    for letter, text in opt_matches:
                        options[letter] = text.strip()
                    
                    # Clean question text (remove options from it)
                    q_text = re.split(cls.OPTION_PATTERN, q_body)[0].strip()
                else:
                    q_text = q_body.strip()
                
                all_questions.append({
                    "section": section_letter,
                    "question_number": int(q_num),
                    "question_text": q_text,
                    "options": options,
                    "type": section_type
                })
        
        # Fallback: if no sections were found, try to find questions in the whole text
        if not all_questions:
            questions = re.findall(cls.QUESTION_PATTERN, full_text, re.DOTALL)
            for q_num, q_body in questions:
                all_questions.append({
                    "section": "Unknown",
                    "question_number": int(q_num),
                    "question_text": q_body.strip(),
                    "options": {},
                    "type": "General"
                })

        return all_questions

    @staticmethod
    def _infer_section_type(content: str) -> str:
        content_lower = content.lower()
        if "multiple choice" in content_lower or "choose the correct" in content_lower:
            return "MCQ"
        if "fill in the blank" in content_lower:
            return "FillInTheBlank"
        if "short question" in content_lower:
            return "ShortQuestion"
        if "broad word problem" in content_lower or "broad question" in content_lower:
            return "BroadQuestion"
        return "General"
