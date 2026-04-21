import os
import re
import json
import time
from typing import List, Dict, Optional
from pathlib import Path

# Try to import LLM libraries
try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    def load_dotenv(): pass

from ...core.schemas import ProcessedQuestion, Flashcard
from ...core.model_router import ModelRoutingEngine

# Load prompts
try:
    from scripts.prompts import CONTENT_GENERATION_PROMPT
except ImportError:
    CONTENT_GENERATION_PROMPT = ""

class ContentGenerator:
    """
    Automates Phase 2 (Content Generation) and Phase 3 (Formatting) 
    using the modular ModelRoutingEngine.
    """
    
    def __init__(self, router: Optional[ModelRoutingEngine] = None):
        """
        Initialize the generator with a modular router.
        """
        self.router = router or ModelRoutingEngine()

    def _encode_image(self, image_path: str) -> str:
        """Helper to convert local image to base64 string"""
        import base64
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def generate_for_questions(self, questions: List[Dict], subject: str, batch_size: int = 5) -> List[ProcessedQuestion]:
        """
        Generate detailed analysis for a list of questions using the modular router.
        """
        if not questions:
            return []
            
        print(f"🧠 Generating content for {len(questions)} questions using Modular Router...")
        
        processed_results = []
        
        for i in range(0, len(questions), batch_size):
            batch = questions[i:i+batch_size]
            batch_indices = [q['question_number'] for q in batch]
            print(f"   Processing batch: Questions {batch_indices}")
            
            context = self._prepare_prompt_context(batch, subject)
            
            try:
                # Use the modular router instead of private _call_llm
                raw_response = self.router.generate_content(
                    prompt=context, 
                    task_type="generation",
                    system_prompt="You are an expert AI educational content generator. Provide deep explanations and flashcards."
                )
                
                parsed_content = self._parse_response(raw_response, batch_indices)
                
                for q in batch:
                    q_num = q['question_number']
                    content = parsed_content.get(q_num, {})
                    
                    # Convert to standardized ProcessedQuestion
                    processed_q = ProcessedQuestion(
                        question_number=q_num,
                        question_text=q.get('question_text', ''),
                        options=q.get('options', {}),
                        subject=subject,
                        explanation_body=content.get("explanation_generated"),
                        option_wise_explanation=content.get("options_explanation_generated"),
                        flashcards=[Flashcard(front_text=f.split(":")[0], back_text=f.split(":")[1]) 
                                   for f in content.get("flashcards_generated", "").split("\n") if ":" in f]
                    )
                    processed_results.append(processed_q)
                
            except Exception as e:
                print(f"   ❌ Error generating content for batch {batch_indices}: {e}")
            
        return processed_results

    def _prepare_prompt_context(self, batch: List[Dict], subject: str) -> str:
        """Formats the extraction data into the prompt format defined in prompts.py"""
        q_range = f"{min(q['question_number'] for q in batch)}-{max(q['question_number'] for q in batch)}"
        
        # Construct the core prompt
        prompt = CONTENT_GENERATION_PROMPT.replace("[Subject]", subject).replace("[Range]", q_range)
        
        # Append the extracted question data
        data_block = "\n\nEXTRACTED DATA:\n"
        for q in batch:
            data_block += f"\n--- Question {q['question_number']} ---\n"
            data_block += f"Text: {q.get('question_text', '')}\n"
            opts = q.get('options', {})
            data_block += f"Options: A: {opts.get('A', '')}, B: {opts.get('B', '')}, C: {opts.get('C', '')}, D: {opts.get('D', '')}\n"
            
        return prompt + data_block


    def _parse_response(self, response: str, batch_indices: List[int]) -> Dict[int, Dict]:
        """
        Parses the LLM output back into a structured dictionary using strict markers.
        """
        results = {}
        
        # Log response (keep all for debugging)
        log_dir = Path("content_gen/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        with open(log_dir / "all_llm_responses.log", "a", encoding="utf-8") as f:
            f.write(f"\n\n{'='*50}\nBatch: {batch_indices}\n{'='*50}\n")
            f.write(response)
        
        with open(log_dir / "llm_response_last.txt", "w", encoding="utf-8") as f:
            f.write(response)

        # More robust splitting: handles ### Question 1, --- Question 1 ---, **Question 1**, etc.
        # It also looks for "Question 1" even if it's the very first text in the response.
        header_pattern = r'(?i)(?:^|\n)(?:[#\-\*]+)?\s*Question\s*[:\s]*(\d+)\s*(?:[#\-\*]+)?'
        sections = re.split(header_pattern, response)
        
        # Fallback: if we only have 1 question and we couldn't find a clear header, 
        # assume the whole response (or from the first marker) belongs to the first question.
        if len(sections) < 3 and len(batch_indices) == 1:
            results[batch_indices[0]] = self._parse_single_content(response)
            return results

        for i in range(1, len(sections), 2):
            try:
                q_num = int(sections[i])
                content = sections[i+1]
                results[q_num] = self._parse_single_content(content)
            except (ValueError, IndexError):
                continue
                
        return results

    def _parse_single_content(self, content: str) -> Dict:
        """Helper to parse markers from a single question block."""
        # 1. Detailed Explanation
        de_match = re.search(r'(?is)\[DE_START\]\s*(.*?)\s*\[DE_END\]', content)
        explanation_body = de_match.group(1).strip() if de_match else ""
        
        # 2. Option Wise Explanation
        oe_match = re.search(r'(?is)\[OE_START\]\s*(.*?)\s*\[OE_END\]', content)
        options_body = oe_match.group(1).strip() if oe_match else ""
        
        # 3. Gap Analysis
        ga_match = re.search(r'(?is)\[GA_START\]\s*(.*?)\s*\[GA_END\]', content)
        gap_body = ga_match.group(1).strip() if ga_match else ""
        
        # Robust fallback for uncooperative LLMs or misplaced markers
        if not explanation_body:
            # Look for content between Question header and first marker or section title
            parts = re.split(r'(?is)\[[A-Z_]+_START\]|Explanation|Analysis', content)
            if len(parts) > 1 and len(parts[0].strip()) > 50:
                explanation_body = parts[0].strip()

        if not options_body and "Option" in content:
            parts = re.split(r'(?is)\[OE_START\]|Option Wise', content)
            if len(parts) > 1:
                options_body = re.split(r'(?is)\[[A-Z_]+_START\]|Concept Gap|###|---', parts[1])[0].strip()

        if not gap_body and ("Gap" in content or "Flashcards" in content):
            parts = re.split(r'(?is)\[GA_START\]|Concept Gap|Flashcards', content)
            if len(parts) > 1:
                gap_body = re.split(r'(?is)###|---', parts[1])[0].strip()

        # Final desperation fallback
        if not explanation_body and len(content.strip()) > 100:
            explanation_body = content.strip()

        return {
            "explanation_generated": explanation_body or "[PARSING_FAILED]",
            "options_explanation_generated": options_body,
            "flashcards_generated": gap_body
        }

    def process_and_update_file(self, file_path: Path, subject: str):
        """
        Reads a processed text file with placeholders, 
        calls LLM, and replaces placeholders with real content.
        """
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if "[EXPLANATION_PLACEHOLDER]" not in content:
            print(f"ℹ️ No placeholders found in {file_path.name}. Skipping.")
            return

        # Extract question data from the file itself for the LLM
        questions_data = self._parse_placeholders_file(content)
        
        if not questions_data:
            print(f"❌ Could not parse question data from {file_path.name}")
            return

        # Generate content
        generated_data = self.generate_for_questions(questions_data, subject)
        
        # Reconstruct the file content
        new_content = self._inject_content(content, generated_data)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ Successfully updated {file_path.name} with LLM content.")

    def _parse_placeholders_file(self, content: str) -> List[Dict]:
        """Parses the text file structure created by pdf_extract_kit_wrapper.py"""
        questions = []
        sections = re.split(r'Question\s+(\d+)Question and Options in Text Format', content)
        
        for i in range(1, len(sections), 2):
            q_num = int(sections[i])
            body = sections[i+1].split("Detailed Explanation")[0].strip()
            
            lines = [l for l in body.split('\n') if l.strip()]
            if not lines: continue
            
            q_text = lines[0]
            opt_line = lines[-1] if len(lines) > 1 else ""
            
            opts = {"A": "", "B": "", "C": "", "D": ""}
            opt_matches = re.findall(r'([A-D])\.\s*(.*?)(?=\s+[A-D]\.|$)', opt_line)
            for letter, val in opt_matches:
                opts[letter] = val.strip()
                
            questions.append({
                "question_number": q_num,
                "question_text": q_text,
                "options": opts
            })
            
        return questions

    def _inject_content(self, original_content: str, generated_data: List[ProcessedQuestion]) -> str:
        """Injects generated data back into the placeholder structure"""
        sections = re.split(r'(Question\s+\d+Question and Options in Text Format)', original_content)
        header = sections[0]
        
        body_parts = []
        gen_map = {q.question_number: q for q in generated_data}
        
        for i in range(1, len(sections), 2):
            q_intro = sections[i]
            q_body = sections[i+1]
            q_num_match = re.search(r'Question\s+(\d+)', q_intro)
            
            if q_num_match:
                q_num = int(q_num_match.group(1))
                if q_num in gen_map:
                    g = gen_map[q_num]
                    q_body = q_body.replace("[EXPLANATION_PLACEHOLDER]", g.explanation_body or "[EXPLANATION_FAILED]")
                    q_body = q_body.replace("[OPTION_EXPLANATION_PLACEHOLDER]", g.option_wise_explanation or "[EXPLANATION_FAILED]")
                    q_body = q_body.replace("[FLASHCARDS_PLACEHOLDER]", "\n".join([f"{f.front_text}: {f.back_text}" for f in g.flashcards]) or "[GENERATION_FAILED]")
            
            body_parts.append(q_intro + q_body)
            
        return header + "".join(body_parts)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="Path to processed text file")
    parser.add_argument("--subject", default="Chemistry")
    parser.add_argument("--provider", default="mock")
    args = parser.parse_args()
    
    gen = ContentGenerator(provider=args.provider)
    gen.process_and_update_file(Path(args.file), args.subject)
