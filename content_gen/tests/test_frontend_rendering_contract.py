from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_editor_uses_sized_image_wrapper_classes():
    content = _read("qc_viewer/static/js/controllers/editor.js")
    assert "image-wrapper-small" in content
    assert "image-wrapper-main" in content


def test_marked_breaks_enabled_in_automate_page():
    html = _read("qc_viewer/static/automate.html")
    assert "marked.setOptions({ gfm: true, breaks: true })" in html


def test_review_css_does_not_hide_bold_text():
    css = _read("qc_viewer/static/css/modules/review.css")
    assert "color: var(--text-main);" in css


def test_qc_payload_maps_core_and_detailed_separately():
    backend = _read("qc_viewer/main.py")
    assert '"core_concept": core_concept' in backend
    assert '"detailed_explanation": explanation_text' in backend
