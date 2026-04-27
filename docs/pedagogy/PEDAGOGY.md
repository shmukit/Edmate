# 🧠 Edmate Pedagogy & Learning Science Framework

> **Transparency Report**: This document outlines the pedagogical theories, learning science principles, and academic research that govern how Edmate generates content.

Edmate is not just an AI wrapper; it is a **Content Infrastructure Factory** designed to encode proven learning science into structured data. We follow a hierarchical evidence model to ensure every content item is grounded in rigorous cognitive science.

---

## 🏛️ The 7 Pillars of Edmate Pedagogy

### 1. Retrieval Practice (The Testing Effect)
**The Principle**: Actively recalling information from memory strengthens neural pathways and makes knowledge more durable than passive re-reading.

*   **Seminal Paper**: [Roediger & Karpicke (2006)](https://journals.sagepub.com/doi/abs/10.1111/j.1467-9280.2006.01693.x) - *The Testing Effect: Taking Memory Tests Improves Long-Term Retention.*
*   **Meta-analysis**: [Dunlosky et al. (2013)](https://journals.sagepub.com/doi/abs/10.1177/1529100612453266) - *Improving Students' Learning With Effective Learning Techniques.*
*   **Applied Translation**: [Agarwal et al. (2012)](https://psycnet.apa.org/record/2012-07332-005) - *Classroom-based evidence for retrieval practice.*

---

### 2. Spaced Repetition (Distributed Practice)
**The Principle**: Information is better retained when review sessions are spaced out over time.

*   **Seminal Paper**: [Cepeda et al. (2006)](https://pubmed.ncbi.nlm.nih.gov/16784440/) - *Distributed practice in verbal recall tasks: A review and quantitative synthesis.*
*   **Meta-analysis**: [Cepeda et al. (2008)](https://journals.sagepub.com/doi/abs/10.1111/j.1467-9280.2008.02209.x) - *Spacing effects in learning: A temporal ridgeline of optimal retention.*
*   **Applied Translation**: Spaced repetition metadata (SM-2/Anki) integrated into all Edmate flashcard outputs.

---

### 3. Interleaving
**The Principle**: Mixing different topics or problem types improves the ability to discriminate between concepts and choose the right strategy.

*   **Seminal Paper**: [Kornell & Bjork (2008)](https://journals.sagepub.com/doi/abs/10.1111/j.1467-9280.2008.02127.x) - *Learning Concepts and Categories: Is Spacing the "Enemy" of Induction?*
*   **Meta-analysis**: [Brunmair & Richter (2019)](https://journals.sagepub.com/doi/abs/10.1037/edu0000320) - *The Interleaving Effect: A Meta-analytic Review.*
*   **Applied Translation**: `concept_links` and `interleaving_tags` in schema allow platforms to build mixed-topic quiz sets.

---

### 4. Bloom's Taxonomy (Revised)
**The Principle**: Educational objectives vary in cognitive complexity, from basic recall to complex creation.

*   **Original Framework**: [Bloom et al. (1956)](https://www.google.com/search?q=Bloom+Taxonomy+1956) - *Taxonomy of Educational Objectives.*
*   **Revised Framework**: [Anderson & Krathwohl (2001)](https://www.google.com/search?q=Anderson+Krathwohl+2001+Bloom+Revision) - *A Taxonomy for Learning, Teaching, and Assessing.*
*   **Applied Translation**: Every Edmate question is tagged with a validated level from the **Revised Bloom's Taxonomy**.

---

### 5. Elaborative Interrogation
**The Principle**: Asking "why" and "how" questions connects new information to existing knowledge.

*   **Seminal Paper**: [Pressley et al. (1987)](https://onlinelibrary.wiley.com/doi/abs/10.1002/acp.2350010104) - *Elaborative interrogation: Facilitating the recall of factual information.*
*   **Evidence Strength**: Validated as high-utility by [Dunlosky (2013)](https://journals.sagepub.com/doi/abs/10.1177/1529100612453266).
*   **Applied Translation**: Edmate provides an explanation for **every** distractor, identifying the specific "Concept Gap."

---

### 6. Cognitive Load Theory (CLT)
**The Principle**: Working memory is limited; instruction must manage "extraneous" load to focus on "germane" learning processes.

*   **Seminal Paper**: [Sweller (1988)](https://onlinelibrary.wiley.com/doi/abs/10.1207/s15516709cog1202_4) - *Cognitive load during problem solving: Effects on learning.*
*   **Modern Expansion**: [Sweller, Ayres & Kalyuga (2011)](https://www.springer.com/gp/book/9781441981257) - *Cognitive Load Theory (Applied).*
*   **Multimedia Learning**: [Mayer (2002)](https://www.sciencedirect.com/science/article/pii/S095947520100010X) - *Multimedia Learning.*
*   **Applied Translation**: Layered Explanations (Core, Detailed, Scaffold) manage cognitive load during review.

---

### 7. Formative vs. Summative Assessment
**The Principle**: Assessment as a tool for learning feedback (formative) vs. evaluation of learning (summative).

*   **Seminal Paper**: [Black & Wiliam (1998)](https://www.tandfonline.com/doi/abs/10.1080/0969594980050103) - *Assessment and Classroom Learning.*
*   **Applied Translation**: The `assessment_role` tag directs platforms to surface content in appropriate feedback contexts.

---

## 🛡️ High-Integrity Assessments (HIA): AI Resilience

In the era of Generative AI, Edmate introduces the **HIA Framework** to ensure assessment integrity. This is grounded in **Authentic Assessment** theory.

*   **Theoretical Origin**: [Wiggins (1990)](https://www.google.com/search?q=Wiggins+Authentic+Assessment+1990) - *The Case for Authentic Assessment.*
*   **Modern Context**: [Lodge et al. (2023)](https://www.nature.com/articles/s41539-023-00162-w) - *Assessment in the age of generative artificial intelligence.*
*   **Applied Translation**: AI Critique, Isomorphic Variants, and Viva (Oral) Probes.

---

## 🔗 Vetted Research & Sources

We rely on these organizations and researchers to ground our work:

*   **[Bjork Learning & Forgetting Lab (UCLA)](https://bjorklab.psych.ucla.edu/)**: Foundational research on "Desirable Difficulties."
*   **[The Learning Scientists](https://www.learningscientists.org/)**: A team of cognitive psychological researchers bridging the lab and classroom.
*   **[Make It Stick](https://www.retrievalpractice.org/make-it-stick)**: The seminal applied synthesis by Brown, Roediger, & McDaniel.
*   **[RetrievalPractice.org](https://www.retrievalpractice.org/)**: Dr. Pooja Agarwal’s hub for retrieval-based learning.
*   **[Deans for Impact](https://deansforimpact.org/resources/the-science-of-learning/)**: Authors of the "Science of Learning" practitioner guide.

---

## 🛠️ How to Audit Edmate's Pedagogy
Every JSON output from Edmate contains a `learning_science_applied` block. This acts as a **Nutrition Label** for pedagogy:

```json
{
  "learning_science_applied": {
    "profile": "exam_prep",
    "techniques": [
      {
        "name": "Bloom's Taxonomy",
        "level": "Apply",
        "description": "Question requires applying laws of physics to a new scenario."
      }
    ]
  }
}
```

---
*Edmate is committed to open, transparent, and science-backed education for all.*
