from pathlib import Path
import os

BASE_DIR = Path("/Users/mukit_10ms/Documents/GitHub/Edmate/qc_viewer")
DRAFTS_DIR = BASE_DIR / "drafts"

draft_id = "83caef3c-b24d-415b-b7b6-64cee63949b7"
meta_path = DRAFTS_DIR / f"{draft_id}.json"

print(f"Checking path: {meta_path}")
print(f"Exists: {meta_path.exists()}")
print(f"Files in DRAFTS_DIR: {os.listdir(DRAFTS_DIR)}")
