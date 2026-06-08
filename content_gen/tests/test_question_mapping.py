from content_gen.core.question_mapping import processed_question_to_edmate_question
from content_gen.core.schemas import ProcessedQuestion


def test_processed_to_edmate_basic():
    q = ProcessedQuestion(
        question_number=1,
        question_text="What is 2+2?",
        options={"A": "3", "B": "4", "C": "5", "D": "6"},
        correct_options=["B"],
        subject="Math",
        explanation_body="It is four.",
        option_wise_explanation="Option B is correct.",
    )
    out = processed_question_to_edmate_question(q, curriculum="IGCSE", topic="Arithmetic")
    assert out.metadata.subject == "Math"
    assert out.metadata.curriculum == "IGCSE"
    assert out.question_text == "What is 2+2?"
    labels = {o.id: o.text for o in (out.options or [])}
    assert labels["B"] == "4"
    assert any(o.is_correct for o in (out.options or []) if o.id == "B")
