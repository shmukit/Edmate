"""
Regression Test: LLM Output Parsing Stability
This script verifies that the ContentGenerator's regex patterns remain robust 
against various markdown formatting styles produced by different Gemini versions.
"""

import re
from typing import Dict, List

def validate_extraction(explanation: str, options_exp: str, flashcards_raw: str):
    # Regex patterns mirrored from ContentGenerator for stability testing
    option_letters = re.findall(r'(?:Option|Label|Choice)?[\s\*]*([A-D])[\s\*]*[:\-\)]', options_exp, flags=re.IGNORECASE)
    
    report = {
        "has_explanation": bool(explanation.strip()),
        "has_final_answer": bool(re.search(r'Final Correct Answer[\s\*]*:[\s\*]*[A-D]', explanation, flags=re.IGNORECASE)),
        "has_option_analysis": len(set([m.upper() for m in option_letters])) >= 3,
    }
    return report

def parse_flashcards(gap_body: str):
    # Regex mirrored from ContentGenerator
    pattern = re.compile(
        r'(?:Flashcard|Card)[\s\*]*\d*[\s\*]*[:\-\)]?[\s\*]*(?:Front|Question)?[\s\*]*[:\-\)]?\s*(.*?)\s*(?:Back|Answer)[\s\*]*[:\-\)]\s*(.*?)(?=(?:Flashcard|Card)|$)',
        re.IGNORECASE | re.DOTALL
    )
    flashcards = []
    for match in pattern.finditer(gap_body):
        front = re.sub(r'\s+', ' ', match.group(1)).strip(" -*\n\t")
        back = re.sub(r'\s+', ' ', match.group(2)).strip(" -*\n\t")
        if front and back:
            flashcards.append((front, back))
    return flashcards

def test_parsing_stability():
    print("🧪 Running Extraction Parsing Stability Tests...")
    
    # Test Case 1: The problematic bolded format from Gemini 2.5 Flash
    exp1 = "\nStep 1: Analysis...\n**Final Correct Answer**: **B**\n"
    opt1 = "**Option A**: Wrong\n**Option B**: Right\n**Option C**: Maybe\n**Option D**: No"
    res1 = validate_extraction(exp1, opt1, "")
    assert res1["has_final_answer"], "Failed to parse bolded Final Answer"
    assert res1["has_option_analysis"], "Failed to parse bolded Options"
    print("  ✅ Bolded Formatting: PASSED")

    # Test Case 2: Mixed separator formatting
    exp2 = "Final Correct Answer *:* C"
    opt2 = "A) ... B) ... C) ..."
    res2 = validate_extraction(exp2, opt2, "")
    assert res2["has_final_answer"], "Failed to parse mixed separator Final Answer"
    assert res2["has_option_analysis"], "Failed to parse parentheses options"
    print("  ✅ Mixed Separators: PASSED")

    # Test Case 3: Flashcard formatting
    fc1 = """
    **Flashcard 1**:
    * **Front**: What is 1+1?
    * **Back**: 2
    """
    fcs = parse_flashcards(fc1)
    assert len(fcs) == 1, f"Expected 1 flashcard, got {len(fcs)}"
    assert fcs[0][0] == "What is 1+1?", f"Parsed front incorrectly: {fcs[0][0]}"
    print("  ✅ Flashcard Formatting: PASSED")

    print("\n🎉 All parsing stability tests passed!")

if __name__ == "__main__":
    test_parsing_stability()
