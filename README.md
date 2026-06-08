# rse_in_delfi_artifact

Replication / artifact package for the DELFI 2026 paper
**"Research Software Engineering in the Learning Technologies: a replication study of
research paradigms in the DELFI community"** (Dehne, Lochner, Wiepke).

This package lets a reviewer **reproduce the analysis, figures and reliability metrics
from the shipped intermediate data**, without needing the original paper PDFs or an LLM
API token.

## What is and isn't included

- ✅ All **intermediate products** (LLM annotation runs, aggregated labels, human
  re-annotation results, the reference-study evaluation) live in [`data/`](data/).
- ✅ A **6-step pipeline** in [`pipeline/`](pipeline/) plus a management script
  [`run_pipeline.py`](run_pipeline.py).
- ❌ **No full paper texts.** The analyzed DELFI papers are copyrighted; their texts are
  never shipped (see `data/README.md` and the `--assert-no-fulltext` guard).
- ❌ **No database.** The original study used MySQL; this artifact is purely file-based.

## Quickstart

```bash
python -m pip install -r requirements.txt

# Runs steps 3, 5, 6 (the steps that work from shipped data).
# Steps 1 (preprocessing) and 2 (experiments) and 4 (human annotation) are
# SKIPPED BY DEFAULT because they need the paper PDFs / an API token.
python run_pipeline.py
```

Outputs (figures, ICR tables, regenerated aggregations) are written under `data/`.

## The steps

| # | Step | Default | Why it may be skipped |
|---|------|---------|-----------------------|
| 1 | Preprocessing (PDF → text) | **skipped** | needs the paper PDF folder |
| 2 | LLM experiments | **skipped** | needs a SAIA/KISSKI API token |
| 3 | Descriptive analysis (figures) | runs | works from `data/` |
| 4 | Human annotation | **skipped** | needs the paper PDF folder (interactive) |
| 5 | Label aggregation (intra+inter, ICR) | runs | works from `data/` |
| 6 | Secondary analysis (biases) | runs | works from `data/` |

### Re-enabling the skipped steps

```bash
# If you DO have the paper PDFs:
python run_pipeline.py --paper-folder /path/to/papers --run-preprocessing --run-human-annotation

# If you DO have a SAIA token (export SAIA_API_KEY):
python run_pipeline.py --run-experiments
```

See [`PROGRESS.md`](PROGRESS.md) for the full build plan and source mapping, and
[`artifact-paper/`](artifact-paper/) for the LNI-formatted artifact description.
