#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Virtualenv not found at .venv"
  exit 1
fi

echo "Running UI e2e regression tests..."
./.venv/bin/pytest -q tests/e2e/test_chip_picker_no_duplicates_e2e.py -m e2e
