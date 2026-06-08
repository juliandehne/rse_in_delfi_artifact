# rse_in_delfi_artifact

A **dataset publication** for the DELFI 2026 paper *"Research Software Engineering
in the Learning Technologies: a replication study of research paradigms in the
DELFI community"* (Dehne, Lochner, Wiepke).

The published artifact is the **set of datasets** in [`data/`](data/) — the LLM
annotation runs, the within- and cross-model aggregated labels, the human
re-annotations, the reference-study evaluation, and the derived figures and tables.
The [`pipeline/`](pipeline/) code is the software that *produces* those datasets;
it is shipped so the datasets are transparent and regenerable, but the datasets are
the primary contribution.

## What is published

- ✅ **All intermediate datasets** — every product of every step, including the
  outputs of the steps that need the paper PDFs or an LLM API, is shipped in
  [`data/`](data/). So every published number and figure is reproducible from the
  shipped data alone.
- ✅ **All figures and tables** (paradigm-distribution chart, label-trend plots,
  ICR tables, bias tables) — shipped and regenerable.
- ✅ The **pipeline** (six steps) and a management script that regenerates the
  datasets and figures.
- ❌ **No paper full texts.** The analyzed DELFI papers are copyrighted; their texts
  are never shipped (see `data/README.md` and the `--assert-no-fulltext` guard).

## Quickstart — regenerate the datasets and figures from shipped data

```bash
python -m pip install -r requirements.txt
python run_pipeline.py
```

This regenerates the aggregated datasets, the ICR tables, the figures and the bias
tables from the shipped intermediate data. No paper PDFs and no API key are needed.

## The steps

The pipeline runs as a chain; each step's output is a published dataset. Two source
inputs are not redistributable (the copyrighted paper PDFs) or are gated behind a
paid service (the LLM API), so the steps that consume them are **optional** — their
outputs are already shipped as datasets:

| # | Step | Output dataset | Optional input to *regenerate from scratch* |
|---|------|----------------|---------------------------------------------|
| 1 | Preprocessing (PDF → text) | paper texts (not shipped; copyrighted) | the paper PDF folder |
| 2 | LLM experiments | `data/experiments/*.csv` | a SAIA/KISSKI API key |
| 3 | Descriptive analysis | `data/descriptive/figures/*.png` | — |
| 4 | Human re-annotation | `data/inter_LLM/df_human_reannotation_results.csv` | the paper PDF folder (interactive) |
| 5 | Label aggregation (intra + inter, ICR) | `data/intra_LLM/*`, `data/inter_LLM/*` | — |
| 6 | Secondary analysis (biases) | `data/secondary_analysis/*` | — |

By default `run_pipeline.py` runs steps 3, 5 and 6 (which need only the shipped
data). Steps 1, 2 and 4 are optional because their outputs are already published;
enable them only if you want to rebuild those datasets from the original sources.

## Regenerating the optional steps from scratch

Both optional inputs are supplied the same way — as command-line parameters
(environment variables also work for the API key, if you prefer):

```bash
# Rebuild the paper-text-dependent datasets (steps 1 and 4) — needs the PDFs:
python run_pipeline.py --paper-folder ./papers --run-preprocessing --run-human-annotation

# Rebuild the LLM annotation datasets (step 2) — needs a SAIA key:
python run_pipeline.py --run-experiments \
    --saia-api-key YOUR_KEY --saia-api-endpoint https://chat-ai.academiccloud.de/v1
# (equivalently: export SAIA_API_KEY / SAIA_API_ENDPOINT and omit the flags)
```

## Testing the full chain on a small subset

If you have the paper PDFs and a SAIA key, you can smoke-test the two resource-gated
steps (preprocessing + experiments) on just **5 papers** without touching the
shipped datasets — everything goes into the `data/_test/` sandbox:

```bash
pip install pymupdf openai          # optional deps needed by steps 1 & 2
python run_pipeline.py --test-configuration \
    --paper-folder ./papers --saia-api-key YOUR_KEY \
    --saia-api-endpoint https://chat-ai.academiccloud.de/v1
```

Or just fill in the three variables at the top of
[`run_test_configuration.sh`](run_test_configuration.sh) and run `bash run_test_configuration.sh`.
By default it uses the first model only (5 API calls); pass `--models <id>` to choose another.

See [`PROGRESS.md`](PROGRESS.md) for the build plan and source mapping,
[`data/README.md`](data/README.md) for the data dictionary, and
[`artifact-paper/`](artifact-paper/) for the LNI-formatted artifact description.
