#!/usr/bin/env bash
# Clone PDF-Extract-Kit into the path expected by Edmate (gitignored by default).
# For a pinned fork with your customizations, set PDF_EXTRACT_KIT_REPO and PDF_EXTRACT_KIT_REF.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KIT_DIR="${ROOT}/content_gen/tools/PDF-Extract-Kit"
REPO="${PDF_EXTRACT_KIT_REPO:-https://github.com/opendatalab/PDF-Extract-Kit.git}"
REF="${PDF_EXTRACT_KIT_REF:-main}"

if [[ -d "${KIT_DIR}/.git" ]]; then
  echo "PDF-Extract-Kit already present at ${KIT_DIR}"
  echo "To update: cd ${KIT_DIR} && git fetch && git checkout ${REF} && git pull"
  exit 0
fi

if [[ -d "${KIT_DIR}" ]]; then
  echo "Directory exists but is not a git repo: ${KIT_DIR}"
  echo "Remove it manually, then re-run this script."
  exit 1
fi

mkdir -p "$(dirname "${KIT_DIR}")"
git clone --depth 1 --branch "${REF}" "${REPO}" "${KIT_DIR}" || {
  echo "Clone failed (branch ${REF} may not exist). Trying default clone + checkout..."
  git clone "${REPO}" "${KIT_DIR}"
  git -C "${KIT_DIR}" checkout "${REF}"
}

echo "Installed PDF-Extract-Kit at ${KIT_DIR}"
echo "Install Python deps from the kit (CPU): pip install -r ${KIT_DIR}/requirements-cpu.txt"
echo "Download layout weights per upstream PDF-Extract-Kit docs (models/ directory)."
