# PROCESS_GUIDE: A/O-Level Content Generation

This guide defines the standard operating procedure for the Agent when processing batches of questions from `content_gen/inputs/`.

## Workflow Overview
1.  **Read Input**: The user will point to a file in `content_gen/inputs/` (e.g., `batch_001.txt`).
2.  **Process**: For each question in the file, apply the **Gemini Content Logic** followed immediately by the **ChatGPT Formatting Logic**.
3.  **Write Output**: Save the combined, formatted result to `content_gen/outputs/[filename]_processed.txt`.

---

## 1. Content Generation Logic (The "Gemini" Step)
For each question, generate the following sections. **Do not output loose text; strictly follow this structure.**

### Structure Per Question
1.  **Question Number**
2.  **Question and Options**: Full text of question and options.
3.  **Detailed Explanation**:
    *   **Core Concept**: State the biological/scientific principle.
    *   **Step-by-Step Analysis**: Break down the logic (Analyze Step 1, Step 2, etc.).
    *   **Final Correct Answer**: clearly stated.
4.  **Option Wise Explanation**: Paragraph explaining why each option is correct/incorrect.
5.  **Concept Gap Analysis & Flashcards**:
    *   Header: `### 🧠 Concept Gap Analysis and Flashcards`
    *   For each *wrong* option: Identify the gap.
    *   **Flashcards**: 2-3 tailored flashcards per option.
    *   Format: `Flashcard X: [Front]? Back: [Back].`

---

## 2. Formatting Logic (The "ChatGPT" Step)
Apply these formatting rules to the generated content *before* saving it.

*   **Google Docs Compatibility**:
    *   Subscripts/Superscripts: Use Unicode (e.g., `CO₂`, `H₂O`, `x²`, `Eₐ`). **Do not use LaTeX** (no `$E_a$`).
    *   Greek Symbols: Use Unicode (Δ, α, β).
    *   Emoji: Keep them (🅰️, 🅱️, 🧠).
    *   Equations: Make them visually clear using plain text/Unicode.
*   **Structure**:
    *   Keep Markdown headers (`##`, `###`).
    *   Keep indentation and lists.
    *   **No Markdown Code Blocks**: The output should be plain text/markdown suitable for copy-pasting, not wrapped in \`\`\`.

---

## Example Output Format
```text
Question 1

Question and Options in Text Format
[Question Text]

A [Option A]
B [Option B]
...

Detailed Explanation...
Core Concept: ...
Analyze Step 1: ...
Final Correct Answer: 🅱️

Option Wise Explanation
Option 🅰️ is incorrect because...

🧠 Concept Gap Analysis and Flashcards
Option 🅰️ Gap: ...
Flashcard 1: ... Back: ...
```
