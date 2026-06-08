#!/usr/bin/env bash
#
# run_test_configuration.sh
#
# Smoke-test the resource-gated pipeline on a small subset of papers, WITHOUT
# touching the shipped datasets (everything goes to a throwaway tmp/ folder).
# It mirrors the real configuration: the 3 study models, 3 runs each, followed by
# intra-model majority voting (~3 models x 3 runs x 5 papers = 45 API calls).
#
# Study models used for live runs (the Llama model was upgraded from
# llama-3.1-sauerkrautlm-70b-instruct to llama-3.3-70b-instruct after the provider
# deprecated the former; see pub_rse_methodology/ieee.qmd):
#   mistral-large-3-675b-instruct-2512, llama-3.3-70b-instruct, gemma-3-27b-it
#
# Fill in the variables below, then run:   bash run_test_configuration.sh
#
# Prerequisites (steps 1 & 2 need the optional deps):
#   pip install -r requirements.txt pymupdf openai
#
set -euo pipefail

# ── FILL ME IN ────────────────────────────────────────────────────────────────
PAPER_FOLDER=""        # path to the folder containing the DELFI paper PDFs
SAIA_API_KEY=""        # your KISSKI SAIA API key
SAIA_API_ENDPOINT="https://chat-ai.academiccloud.de/v1"   # SAIA endpoint (override if different)

# Optional: restrict to ONE model (default: all 3 study models, 3 runs each).
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

echo "Running test configuration (5 papers x 3 models x 3 runs, output = tmp/test_run/) ..."
"$PY" "${ARGS[@]}"
