import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.processing.content_generator import ContentGenerator
from scripts.prompts import JSON_GENERATION_PROMPT

def run_experiment():
    # 1. Load Extracted Data
    json_path = Path("content_gen/data/extracted/9701_m24_qp_12 (2)_extracted.json")
    if not json_path.exists():
        print(f"❌ Extracted JSON not found at {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    questions = data.get("questions", [])
    print(f"🧪 Starting Experiment for {len(questions)} questions...")

    # 2. Define Models to Test
    models_to_test = [
        {"alias": "mini", "model_id": "gpt-4o-mini"},
        {"alias": "standard", "model_id": "gpt-4o"}
    ]

    for model_cfg in models_to_test:
        alias = model_cfg["alias"]
        model_id = model_cfg["model_id"]
        
        print(f"\n🚀 Running experiment for Model: {model_id} ({alias})")
        
        gen = ContentGenerator(provider="openai", model_name=model_id)
        results = []

        output_file = Path(f"content_gen/data/outputs/experiment_9701_m24_{alias}.json")
        
        # Process 1-by-1 for 100% reliability
        for q in questions:
            q_num = q["question_number"]
            print(f"   Processing Q{q_num}...")
            
            prompt_context = f"Question Text: {q['question_text']}\nOptions: {json.dumps(q['options' ])}"
            full_prompt = JSON_GENERATION_PROMPT + "\n\n" + prompt_context
            
            # Get diagrams for this question
            images = q.get("stem_images", [])
            
            # Retry logic for Quality Control
            success = False
            attempts = 0
            while not success and attempts < 2:
                attempts += 1
                try:
                    # Tagging happens inside _call_llm which is decorated with @track
                    # Note: We should ideally pass tags dynamically. 
                    # For now, Opik logs model_name automatically via OpenAI instrumentation.
                    raw_resp = gen._call_llm(full_prompt, images=images)
                    parsed = json.loads(raw_resp)
                    
                    # QC Check: Ensure all keys exist
                    required_keys = ["detailed_explanation", "option_analysis", "flashcards"]
                    if all(parsed.get(k) for k in required_keys):
                        q_result = q.copy()
                        q_result["generated_content"] = parsed
                        results.append(q_result)
                        success = True
                    else:
                        print(f"      ⚠️ QC Failed (missing keys) for Q{q_num} on attempt {attempts}. Retrying...")
                except Exception as e:
                    print(f"      ❌ Error on attempt {attempts} for Q{q_num}: {e}")
                    if attempts == 2:
                        print(f"      ‼️ Giving up on Q{q_num}")

            # Save incrementally in case of crash
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)

        print(f"✅ Finished {alias} run. Results saved to {output_file}")

if __name__ == "__main__":
    run_experiment()
