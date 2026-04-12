import json
from pathlib import Path

def export_to_txt(json_path: Path, txt_path: Path):
    if not json_path.exists():
        print(f"❌ JSON not found: {json_path}")
        return

    print(f"📄 Exporting {json_path.name} to {txt_path.name}...")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    with open(txt_path, 'w', encoding='utf-8') as f:
        for q in questions:
            q_num = q["question_number"]
            content = q.get("generated_content", {})
            
            f.write(f"Question {q_num}Question and Options in Text Format\n\n")
            f.write(f"{q['question_text']}\n\n")
            
            opts = q["options"]
            opt_str = f"A. {opts.get('A')} B. {opts.get('B')} C. {opts.get('C')} D. {opts.get('D')}"
            f.write(f"{opt_str}\n\n")

            # Detailed Explanation
            f.write("Detailed Explanation of the Question and Right Answer\n\n")
            f.write("[DE_START]\n")
            f.write(f"Core Concept: {content.get('core_concept', '')}\n\n")
            f.write(f"{content.get('detailed_explanation', '')}\n")
            f.write("[DE_END]\n\n")

            # Option Wise
            f.write("Option Wise Explanation (Detailed)\n\n")
            f.write("[OE_START]\n")
            oe = content.get("option_analysis", {})
            for letter in ["A", "B", "C", "D"]:
                f.write(f"Option {letter}: {oe.get(letter, '')}\n")
            f.write("[OE_END]\n\n")

            # Flashcards
            f.write("### 🧠 Concept Gap Analysis and Flashcards\n\n")
            f.write("[GA_START]\n")
            flashcards = content.get("flashcards", [])
            for i, fc in enumerate(flashcards):
                f.write(f"Flashcard {i+1}: {fc.get('question')} Back: {fc.get('answer')}\n")
            f.write("[GA_END]\n\n")
            
            f.write("-" * 50 + "\n\n")

    print(f"✅ Export complete: {txt_path}")

if __name__ == "__main__":
    base_dir = Path("content_gen/data/outputs")
    
    # Export Mini
    export_to_txt(
        base_dir / "experiment_9701_m24_mini.json",
        base_dir / "9701_m24_qp_12_mini_REVIEW.txt"
    )
    
    # Export Standard
    export_to_txt(
        base_dir / "experiment_9701_m24_standard.json",
        base_dir / "9701_m24_qp_12_standard_REVIEW.txt"
    )
