"""
Central repository for system prompts used in the content generation pipeline.
"""

# The primary system prompt for Gemini to generate educational content
CONTENT_GENERATION_PROMPT = """
[Question Paper Name] is the question paper and [Marks Scheme Name] is the answer of questions (1-40).

For the provided [Subject] questions [Range], please generate a detailed analysis using the following structure and formatting rules:

1. Write the question number

2. Question and Options in Text Format: Provide the question text and all options.

3. Detailed Explanation of the Question and Right Answer:
   Provide a short explanation of the overall method before the step-by-step analysis. 
   Use the following step-by-step analysis structure for the main explanation: 
   - State the core concept.
   - Analyze Step 1, concluding the intermediate result.
   - Analyze Step 2, concluding the intermediate result.
   - Analyze Step 3, detailing the calculation/reasoning, and concluding the result.
   - Analyze Step 4, detailing the calculation/reasoning, and concluding the result (use only if necessary).
   - State the final correct answer based on the analysis.

4. Option Wise Explanation (Detailed):
   Provide a detailed explanation for why each option (A, B, C, D) is correct or incorrect. 
   Present the explanation in paragraph format (no tables).

5. ### 🧠 Concept Gap Analysis and Flashcards:
   For every individual wrong option (e.g., A, B, C, D), identify the conceptual gap that led to that specific incorrect choice.
   Following the gap analysis, provide 2-3 separate tailored flashcards for each option.
   Format the flashcards in text/paragraph format for each.
   Start each new flashcard on a new line.
   Format flashcards as: Flashcard X: [Front text]? Back: [Back text].

General Formatting and Content Rules (Strictly Follow):
- Use standard markdown headings (### and ##) to create a clear hierarchy.
- Ensure all content is presented in paragraph format (no tables, no UI elements).
- Be detailed and rigorous in all [Subject] explanations, adhering to the standard A/O-level syllabus standards (e.g., 9700/5090).
- The final output must only contain the requested sections (1, 2, 3, 4, 5) in order.
- Ensure the short explanation in section 3 is brief and precedes the step-by-step analysis.
"""

# Prompt for ChatGPT to format content for Google Docs
FORMATTING_PROMPT = """
Rewrite the following document for Google Docs compatibility: 
- Convert all LaTeX math (like $E_a$, $e^{-E_a/RT}$, $\frac{3}{2}kT$) into readable text form using Unicode subscripts/superscripts (e.g., Eₐ, e^(–Eₐ/RT), ³⁄₂kT). 
- Preserve Greek symbols (Δ, α, β) in Unicode. 
- Keep all emoji (🅰️, 🅱️, 🧠) and section headers intact. 
- Maintain indentation, lists, and step numbering. 
- Remove dollar signs or LaTeX markup while keeping equations visually clear. 
- Output as plain text for direct pasting into Google Docs without breaking. 
- Do not reduce text, keep it as it is.
"""
