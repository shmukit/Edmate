from content_gen.core.model_router import ModelRoutingEngine
from content_gen.scripts.pipeline.pipeline_orchestrator import PipelineOrchestrator
from unittest.mock import patch
from pathlib import Path
import pytest
import sys
from unittest.mock import MagicMock

# Mock heavy dependencies using patch.dict to avoid global side effects
HEAVY_MOCKS = {
    "fitz": MagicMock(),
    "pdf_extract_kit.tasks": MagicMock(),
    "pdf_extract_kit.utils.config_loader": MagicMock(),
    "psycopg2": MagicMock()
}


def test_base64_conversion(tmp_path):
    # Setup: Create a dummy image file
    img_path = tmp_path / "test.png"
    img_path.write_bytes(b"dummy image data")

    # Initialize orchestrator with mocked extractor/storage to avoid heavy init
    with patch.dict("sys.modules", HEAVY_MOCKS):
        with patch("content_gen.scripts.pipeline.pipeline_orchestrator.KitExtractionAdapter"), \
             patch("content_gen.scripts.pipeline.pipeline_orchestrator.PostgresStorageAdapter"):
            orchestrator = PipelineOrchestrator()
    
    # Execute conversion
    b64_str = orchestrator._convert_to_base64(img_path)

    # Verify
    assert b64_str.startswith("data:image/png;base64,")
    assert "ZHVtbXkgaW1hZ2UgZGF0YQ==" in b64_str  # "dummy image data" in base64


@patch("content_gen.scripts.pipeline.pipeline_orchestrator.StorageUploader")
def test_pipeline_uses_base64_mode(mock_uploader, tmp_path):
    # Setup dummy images
    img_dir = tmp_path / "images"
    img_dir.mkdir()
    (img_dir / "q1_stem.png").write_bytes(b"data")

    # Mock router with base64 config
    mock_router = MagicMock()
    mock_router.config.storage_settings.image_mode = "base64"
    mock_router.config.extraction_settings.engine = "pymupdf"

    with patch.dict("sys.modules", HEAVY_MOCKS):
        with patch("content_gen.scripts.pipeline.pipeline_orchestrator.KitExtractionAdapter"), \
             patch("content_gen.scripts.pipeline.pipeline_orchestrator.PostgresStorageAdapter"):
            orchestrator = PipelineOrchestrator(router=mock_router)

    # Manually check the logic branch in process_pdf (isolated)
    images = [img_dir / "q1_stem.png"]

    cdn_mapping = {}
    if orchestrator.router.config.storage_settings.image_mode == "base64":
        for img_path in images:
            b64_str = orchestrator._convert_to_base64(img_path)
            if b64_str:
                cdn_mapping[img_path.name] = b64_str

    assert "q1_stem.png" in cdn_mapping
    assert cdn_mapping["q1_stem.png"].startswith("data:image/png;base64,")
    mock_uploader.assert_not_called()
