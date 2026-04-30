"""
PedagogyEngine: Translates learning science profiles into structured system prompts.

Instead of a generic "you are an AI" prompt, this compiler assembles a rich pedagogical
constitution based on the selected profile. This is how PEDAGOGY.md becomes real in output.
"""

from typing import Optional


# Bloom's Taxonomy verb maps by cognitive level
BLOOMS_VERBS = {
    "remember":    ["identify", "recall", "list", "name", "define"],
    "understand":  ["explain", "describe", "classify", "summarize", "paraphrase"],
    "apply":       ["calculate", "solve", "use", "demonstrate", "apply"],
    "analyze":     ["compare", "distinguish", "examine", "differentiate", "break down"],
    "evaluate":    ["judge", "justify", "critique", "defend", "assess"],
    "create":      ["design", "formulate", "construct", "propose", "develop"],
}

# Bloom's target levels per profile
PROFILE_BLOOM_MAP = {
    "default":        ["remember", "understand", "apply"],
    "exam_prep":      ["apply", "analyze", "evaluate"],
    "beginner":       ["remember", "understand"],
    "flashcard_only": ["remember", "understand"],
    "hia_high":       ["analyze", "evaluate", "create"],
}

# Retrieval practice framing per profile
RETRIEVAL_FRAMING = {
    "default": "Questions should promote active recall by testing core concepts directly.",
    "exam_prep": (
        "Questions must simulate high-stakes exam conditions: ambiguous distractors, "
        "multi-step reasoning, and transfer tasks that prevent surface-level pattern matching."
    ),
    "beginner": (
        "Questions should scaffold knowledge retrieval progressively — start with recognition, "
        "then move toward recall. Use clear, unambiguous language."
    ),
    "flashcard_only": (
        "Generate atomic, single-concept flashcards optimized for spaced repetition. "
        "Each front/back pair should test exactly one fact."
    ),
    "hia_high": (
        "Questions must be designed to be AI-resilient: require original reasoning, "
        "real-world application, or metacognitive reflection that cannot be answered "
        "by pattern-matching alone."
    ),
}

# Cognitive load guidance per profile
COGNITIVE_LOAD_NOTES = {
    "default": "Keep explanations clear. Avoid unnecessary jargon.",
    "exam_prep": (
        "Explanations should be dense and precise. Assume the learner has foundational knowledge. "
        "Focus on why wrong answers are wrong (option analysis)."
    ),
    "beginner": (
        "Apply the Split-Attention Principle: keep explanations adjacent to relevant information. "
        "Avoid multiple interleaved concepts in a single question."
    ),
    "flashcard_only": "Keep each flashcard minimal. One concept per card.",
    "hia_high": (
        "Apply Desirable Difficulties: make the question slightly harder than comfortable recall. "
        "The friction is intentional and pedagogically valuable."
    ),
}

# HIA mode instructions
HIA_INSTRUCTIONS = {
    "Low": "",
    "Medium": (
        "\n\nHIA GUIDANCE: At least 20% of generated items should require multi-step reasoning "
        "that resists single-attempt AI generation."
    ),
    "High": (
        "\n\nHIA GUIDANCE: Generate questions that require authentic reasoning. "
        "For each question, include a 'resilience_note' field explaining why this question "
        "is difficult for AI to answer correctly without deep understanding."
    ),
    "Very High": (
        "\n\nHIA GUIDANCE: ALL questions must be High-Integrity Assessments. Prefer types: "
        "AI Critique (plant deliberate errors for students to find), "
        "Isomorphic Variants (same concept, different numerical/contextual parameters), "
        "or Viva Probes (multi-stage oral defense questions). "
        "Include 'hia_details' in the output schema."
    ),
}


class PedagogyEngine:
    """
    Compiles a structured pedagogical system prompt from a selected profile.
    The output prompt is injected as the system message to every LLM generation call.
    """

    def __init__(self, ls_profile: str = "default", hia_mode: str = "Low", curriculum: str = "Cambridge O/Level"):
        self.ls_profile = ls_profile if ls_profile in PROFILE_BLOOM_MAP else "default"
        self.hia_mode = hia_mode if hia_mode in HIA_INSTRUCTIONS else "Low"
        self.curriculum = curriculum

    def compile_system_prompt(self) -> str:
        """Assembles the full pedagogical system prompt for this profile."""
        bloom_levels = PROFILE_BLOOM_MAP[self.ls_profile]
        bloom_verbs = []
        for level in bloom_levels:
            bloom_verbs.extend(BLOOMS_VERBS.get(level, []))

        retrieval = RETRIEVAL_FRAMING[self.ls_profile]
        cog_load = COGNITIVE_LOAD_NOTES[self.ls_profile]
        hia = HIA_INSTRUCTIONS[self.hia_mode]

        prompt = f"""You are an expert assessment content designer for {self.curriculum}.
Your outputs are grounded in evidence-based learning science. You do not generate generic questions.
Every item you generate must reflect the following pedagogical framework:

## 1. Cognitive Complexity (Bloom's Revised Taxonomy — Anderson & Krathwohl, 2001)
Target cognitive levels: {', '.join(level.capitalize() for level in bloom_levels)}.
Use action verbs such as: {', '.join(bloom_verbs[:8])}.
Do NOT produce questions that only test surface memorisation unless the profile explicitly targets "Remember".

## 2. Retrieval Practice (Roediger & Karpicke, 2006; Agarwal, 2012)
{retrieval}

## 3. Cognitive Load Management (Sweller, 1988; Mayer, 2002)
{cog_load}

## 4. Learning Science Profile Active: [{self.ls_profile.upper()}]
Every generated item should include a 'learning_science_applied' field listing:
- bloom_level: The target Bloom's level of this question.
- technique: The primary learning science technique applied (e.g., "Retrieval Practice", "Interleaving").
- resilience_profile: One of "Standard", "Enhanced", "High-Integrity".
{hia}

## 5. Output Consistency
- **Core Concept**: Provide a high-level summary of the underlying concept. Constraints: Max 4-6 lines of clear, concise text. Do not repeat the entire detailed explanation here.
"""
        return prompt.strip()

    def get_profile_summary(self) -> dict:
        """Returns a machine-readable summary of the active pedagogical profile."""
        return {
            "ls_profile": self.ls_profile,
            "hia_mode": self.hia_mode,
            "curriculum": self.curriculum,
            "target_bloom_levels": PROFILE_BLOOM_MAP[self.ls_profile],
        }
