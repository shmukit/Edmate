import sys
from pathlib import Path
import os
import json

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from content_gen.scripts.pipeline.pipeline_orchestrator import PipelineOrchestrator
from content_gen.core.model_router import ModelRoutingEngine

def debug_extraction():
    pdf_path = Path("/Users/mukit_10ms/Documents/GitHub/Edmate/qc_viewer/drafts/draft_3a7a9e46/source.pdf")
    output_dir = Path("/Users/mukit_10ms/Documents/GitHub/Edmate/qc_viewer/drafts/debug_test")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    router = ModelRoutingEngine()
    router.config.extraction_engine = "pdf_extract_kit"
    orchestrator = PipelineOrchestrator(router=router)
    
    print(f"--- Starting Debug Extraction for {pdf_path.name} ---")
    try:
        extracted = orchestrator.extractor.extract_content(pdf_path, output_dir)
        print(f"--- SUCCESS: Extracted {len(extracted)} questions ---")
        for i, q in enumerate(extracted):
            print(f"Q{q.question_number}: {q.question_text[:50]}...")
            print(f"  Options: {q.options}")
            
        if not extracted:
            print("--- WARNING: No questions extracted! ---")
            
    except Exception as e:
        print(f"--- FAILURE: {str(e)} ---")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_extraction()
