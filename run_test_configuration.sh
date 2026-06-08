#!/usr/bin/env bash
#
# run_test_configuration.sh
#
# Smoke-test the two resource-gated pipeline steps (1 preprocessing + 2 experiments)
# on a small subset of papers, WITHOUT touching the shipped datasets (everything is
# written to the data/_test/ sandbox).
#
# Fill in the three variables below, then run:   bash run_test_configuration.sh
#
# Prerequisites (steps 1 & 2 need the optional deps):
#   pip install -r requirements.txt pymupdf openai
#
set -euo pipefail

# ── FILL ME IN ────────────────────────────────────────────────────────────────
PAPER_FOLDER=""        # path to the folder containing the DELFI paper PDFs
SAIA_API_KEY=""        # your KISSKI SAIA API key
SAIA_API_ENDPOINT="https://chat-ai.academiccloud.de/v1"   # SAIA endpoint (override if different)

# Optional: which model to test with (default: the first model in config.MODELS).
# e.g. MODEL="mistral-large-3-675b-instruct-2512"
MODEL=""
# ──────────────────────────────────────────────────────────────────────────────

if [[ -z "$PAPER_FOLDER" || -z "$SAIA_API_KEY" ]]; then
  echo "ERROR: please set PAPER_FOLDER and SAIA_API_KEY at the top of this script." >&2
  exit 1
fi

# Use the interpreter from an active venv if present, else system python.
PY="${PYTHON:-python}"

ARGS=(run_pipeline.py --test-configuration
      --paper-folder "$PAPER_FOLDER"
      --saia-api-key "$SAIA_API_KEY"
      --saia-api-endpoint "$SAIA_API_ENDPOINT")

if [[ -n "$MODEL" ]]; then
  ARGS+=(--models "$MODEL")
fi

echo "Running test configuration (5 papers, sandbox = data/_test/) ..."
"$PY" "${ARGS[@]}"
