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

# Try to import Opik for observability
try:
    import opik
    from opik import track
    from opik.integrations.openai import track_openai
except ImportError:
    opik = None
    track = lambda project_name=None: (lambda f: f)
    track_openai = lambda client, project_name=None: client

# Load prompts
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from scripts.prompts import CONTENT_GENERATION_PROMPT, FORMATTING_PROMPT, JSON_GENERATION_PROMPT
except ImportError:
    CONTENT_GENERATION_PROMPT = ""
    FORMATTING_PROMPT = ""
    JSON_GENERATION_PROMPT = ""

class ContentGenerator:
    """
    Automates Phase 2 (Content Generation) and Phase 3 (Formatting) 
    using flexible LLM providers.
    """
    
    def __init__(self, provider: str = "gemini", model_name: Optional[str] = None):
        """
        Initialize the generator with a specific provider.
        
        Args:
            provider: 'gemini', 'openai', or 'mock'
            model_name: Specific model ID (e.g., 'gemini-1.5-pro', 'gpt-4o')
        """
        self.provider = provider.lower()
        self.api_key = self._get_api_key()
        
        if self.provider == "gemini":
            if not genai:
                raise ImportError("google-generativeai not installed")
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(model_name or "gemini-1.5-flash")
            
        elif self.provider == "openai":
            if not OpenAI:
                raise ImportError("openai not installed")
            self.client = OpenAI(api_key=self.api_key)
            self.model_name = model_name or "gpt-4o"
            # Wrap OpenAI client with Opik for auto-tracking
            if opik:
                self.client = track_openai(self.client, project_name=os.getenv("OPIK_PROJECT_NAME", "Edmate"))
            
        elif self.provider == "mock":
            print("⚠️ Using Mock Generator (no API calls)")
            
    def _get_api_key(self) -> str:
        """Retrieve API key from environment variables"""
        if self.provider == "gemini":
            key = os.getenv("GEMINI_API_KEY")
        elif self.provider == "openai":
            key = os.getenv("OPENAI_API_KEY")
        else:
            return "mock"
            
        if not key and self.provider != "mock":
            raise ValueError(f"Missing API key for {self.provider}. Please set {self.provider.upper()}_API_KEY.")
        return key

    def _encode_image(self, image_path: str) -> str:
        """Helper to convert local image to base64 string"""
        import base64
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    @track(project_name=os.getenv("OPIK_PROJECT_NAME", "Edmate"))
    def generate_for_questions(self, questions: List[Dict], subject: str, batch_size: int = 5) -> List[Dict]:
        """
        Generate detailed analysis for a list of questions.
        
        Args:
            questions: List of extracted question dictionaries
            subject: The subject name
            
        Returns:
            Updated questions list with generated content
        """
        if not questions:
            return []
            
        print(f"🧠 Generating content for {len(questions)} questions using {self.provider}...")
        
        # In a real scenario, we might batch these to save tokens/time
        updated_questions = []
        
        for i in range(0, len(questions), batch_size):
            batch = questions[i:i+batch_size]
            batch_indices = [q['question_number'] for q in batch]
            print(f"   Processing batch: Questions {batch_indices}")
            
            # Prepare context for the LLM
            context = self._prepare_prompt_context(batch, subject)
            
            try:
                raw_response = self._call_llm(context)
                parsed_content = self._parse_response(raw_response, batch_indices)
                
                # Update batch with generated content
                for q in batch:
                    q_num = q['question_number']
                    if q_num in parsed_content:
                        q.update(parsed_content[q_num])
                    else:
                        print(f"   ⚠️ Warning: No content generated for Question {q_num}")
                
            except Exception as e:
                print(f"   ❌ Error generating content for batch {batch_indices}: {e}")
                # Keep original with placeholders on failure
            
            updated_questions.extend(batch)
            
        return updated_questions

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

    @track(name="llm_call", project_name=os.getenv("OPIK_PROJECT_NAME", "Edmate"))
    def _call_llm(self, prompt: str, images: Optional[List[str]] = None) -> str:
        """
        Executes the LLM call based on the provider.
        
        Args:
            prompt: Text prompt
            images: Optional list of base64 encoded images or image paths
        """
        if self.provider == "gemini":
            # Handle multimodal if images are provided
            if images:
                # Assuming images are paths for simplicity in this implementation
                content = [prompt]
                for img_path in images:
                    if os.path.exists(img_path):
                        img_data = genai.upload_file(img_path)
                        content.append(img_data)
                response = self.model.generate_content(content)
            else:
                response = self.model.generate_content(prompt)
            
            # Log metadata to Opik
            if opik:
                usage = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "completion_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count
                }
                metadata = {"usage": usage}
                if images:
                    metadata["images_count"] = len(images)
                    # Log base64 images if the user requested it earlier
                    metadata["images_base64"] = [self._encode_image(p) if os.path.exists(p) else p for p in images] 
                opik.log_metadata(metadata)
                
            return response.text
        elif self.provider == "openai":
            # For OpenAI, images are handled via messages structure
            if images:
                messages = [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt}
                    ]
                }]
                for img_path in images:
                    if os.path.exists(img_path):
                        b64_img = self._encode_image(img_path)
                        messages[0]["content"].append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
                        })
                    else:
                        # Fallback for URLs
                        messages[0]["content"].append({
                            "type": "image_url",
                            "image_url": {"url": img_path}
                        })
            else:
                messages = [{"role": "user", "content": prompt}]
                
            # Use JSON Mode for experiments if requested
            is_json = "JSON" in prompt
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_format={"type": "json_object"} if is_json else None
            )
            
            # OpenAI costs are tracked automatically by track_openai
            return response.choices[0].message.content
        elif self.provider == "mock":
            # Return a formatted string that the parser can understand
            mock_resp = ""
            for q_num in re.findall(r'--- Question (\d+) ---', prompt):
                mock_resp += f"\nQuestion {q_num}\n"
                mock_resp += "[DE_START]This is a mock explanation for " + q_num + ".[DE_END]\n"
                mock_resp += "[OE_START]This is a mock option analysis.[OE_END]\n"
                mock_resp += "[GA_START]Flashcard 1: Q? Back: A.[GA_END]\n"
            return mock_resp
        return ""

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

    def _inject_content(self, original_content: str, generated_data: List[Dict]) -> str:
        """Injects generated content into the placeholder structure"""
        sections = re.split(r'(Question\s+\d+Question and Options in Text Format)', original_content)
        header = sections[0]
        
        body_parts = []
        gen_map = {q['question_number']: q for q in generated_data}
        
        for i in range(1, len(sections), 2):
            q_intro = sections[i]
            q_body = sections[i+1]
            q_num_match = re.search(r'Question\s+(\d+)', q_intro)
            
            if q_num_match:
                q_num = int(q_num_match.group(1))
                if q_num in gen_map:
                    g = gen_map[q_num]
                    q_body = q_body.replace("[EXPLANATION_PLACEHOLDER]", g.get("explanation_generated", "[EXPLANATION_FAILED]"))
                    q_body = q_body.replace("[OPTION_EXPLANATION_PLACEHOLDER]", g.get("options_explanation_generated", "[EXPLANATION_FAILED]"))
                    q_body = q_body.replace("[FLASHCARDS_PLACEHOLDER]", g.get("flashcards_generated", "[GENERATION_FAILED]"))
            
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
