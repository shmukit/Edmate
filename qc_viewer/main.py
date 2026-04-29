import uvicorn
from qc_viewer.app_factory import create_app


def build_qc_payload(core_concept: str, explanation_text: str) -> dict[str, str]:
    """Backward-compatible payload shape used by frontend contract tests."""
    return {
        "core_concept": core_concept,
        "detailed_explanation": explanation_text,
    }


app = create_app()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
