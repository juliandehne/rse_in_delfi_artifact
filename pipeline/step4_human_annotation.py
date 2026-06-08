"""
Step 4 — Human re-annotation of complete-disagreement cases.  SKIPPED BY DEFAULT.

For ordinal labels where all 3 LLMs assigned different values (-1, 0, +1), a human
annotator sets the final label after reading the paper and the LLM justifications.

Ported from the source notebook
``analysis/label_aggregation/human_reannotation/human_reannotation.ipynb``.
The interactive ipywidgets UI is replaced by a **console** loop so it can run inside
the pipeline. Two parts:

  * SUBSET (always runs, no papers needed): recompute which papers/labels are in
    complete disagreement from the step-5a intra-LLM aggregates, and (re)write
    ``data/inter_LLM/df_papers_subset_for_human_reannotation.csv``.
  * ANNOTATE (only with ``--paper-folder``): show each paper's text + the 3 LLM
    justifications, prompt for a human label in {-1, 0, +1} and a short justification,
    and append to ``data/inter_LLM/df_human_reannotation_results.csv`` after each entry.

Reviewers without the paper PDFs keep this skipped: the shipped
``df_human_reannotation_results.csv`` is the authoritative human output.

Run standalone:
    python -m pipeline.step4_human_annotation                       # subset only
    python -m pipeline.step4_human_annotation --paper-folder PATH    # + interactive annotation
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline import config

ORDINAL_AGG_COLS = [f"{c}_agg" for c in config.ORDINAL_COLS]
SUBSET_CSV = config.INTER_DIR / "df_papers_subset_for_human_reannotation.csv"
RESULTS_CSV = config.HUMAN_REANNOTATION_CSV
RESULTS_COLUMNS = ["paper_id", "title", "year", "filename", "label_column",
                   "mistral_label", "llama_label", "gemma_label",
                   "human_label", "human_justification", "timestamp"]


def _load_aggregates() -> dict[str, pd.DataFrame]:
    dfs = {}
    for short, model_id in config.MODELS.items():
        dfs[short] = pd.read_csv(
            config.INTRA_DIR / f"df_full_experiment_{model_id}_{config.PROMPT_TEMPLATE_NAME}_aggregated.csv")
    ids = [list(df["id"]) for df in dfs.values()]
    assert all(x == ids[0] for x in ids), "ID mismatch between LLM dataframes — rows not aligned!"
    print(f"  ID check passed: 3 dfs share {len(ids[0])} IDs in the same order.")
    return dfs


def find_disagreements(dfs: dict[str, pd.DataFrame]) -> list[dict]:
    """Papers where all 3 LLMs disagree (values == {-1, 0, 1}) on an ordinal label."""
    m, l, g = (dfs["mistral"], dfs["llama"], dfs["gemma"])
    paper_labels: dict[int, list[str]] = defaultdict(list)
    for col in ORDINAL_AGG_COLS:
        am, al, ag = m[col].to_numpy(), l[col].to_numpy(), g[col].to_numpy()
        mask = (am != al) & (am != ag) & (al != ag)
        for idx in np.where(mask)[0]:
            paper_labels[int(idx)].append(col)
    tasks = [{"paper_index": i, "labels": cols} for i, cols in sorted(paper_labels.items())]
    total = sum(len(t["labels"]) for t in tasks)
    print(f"  Papers to annotate: {len(tasks)} | total label annotations: {total}")
    return tasks


def build_subset(dfs: dict[str, pd.DataFrame], tasks: list[dict]) -> pd.DataFrame:
    """Recreate the disagreement-subset dataframe (metadata + per-LLM labels)."""
    idx = [t["paper_index"] for t in tasks]
    base = dfs["mistral"].loc[idx, [c for c in config.METADATA_COLS]].copy()
    for short, df in dfs.items():
        for col in ORDINAL_AGG_COLS:
            base[f"{short}_{col}"] = df.loc[idx, col].values
    base.to_csv(SUBSET_CSV, index=False)
    print(f"  Wrote disagreement subset ({len(base)} papers) → {SUBSET_CSV.name}")
    return base


def _read_pdf_text(pdf_index: dict[str, Path], filename: str) -> str:
    path = pdf_index.get(filename)
    if path is None:
        return f"[PDF '{filename}' not found in paper folder]"
    try:
        from pipeline.pdf_text_extraction import extract_text_from_pdf, extract_main_content
        return extract_main_content(extract_text_from_pdf(path)) or "[empty extraction]"
    except Exception as exc:
        return f"[extraction failed: {exc}]"


def annotate_console(dfs, tasks, paper_folder: Path) -> None:
    """Console re-annotation loop (replaces the notebook's ipywidgets UI)."""
    from datetime import datetime, timezone

    pdf_index = {p.name: p for p in Path(paper_folder).rglob("*.pdf")}
    done = set()
    if RESULTS_CSV.exists():
        prev = pd.read_csv(RESULTS_CSV)
        done = set(zip(prev["paper_id"], prev["label_column"]))

    m, l, g = dfs["mistral"], dfs["llama"], dfs["gemma"]
    for t in tasks:
        i = t["paper_index"]
        pid = int(m.loc[i, "id"])
        fname = str(m.loc[i, "filename"])
        for col in t["labels"]:
            if (pid, col) in done:
                continue
            base = col.replace("_agg", "")
            print("\n" + "=" * 70)
            print(f"Paper id={pid} | {m.loc[i, 'title']} ({m.loc[i, 'year']}) | {fname}")
            print(f"Label: {col}")
            print(f"  mistral={m.loc[i, col]} | llama={l.loc[i, col]} | gemma={g.loc[i, col]}")
            for short, df in dfs.items():
                ex = df.loc[i].get(f"{base}_erklärung_run_1", "")
                print(f"  [{short} justification] {str(ex)[:500]}")
            print("-" * 70)
            print(_read_pdf_text(pdf_index, fname)[:4000])
            print("-" * 70)
            while True:
                val = input("Your label (-1 / 0 / 1, or 's' to skip): ").strip()
                if val == "s":
                    break
                if val in {"-1", "0", "1"}:
                    just = input("Short justification: ").strip()
                    pd.DataFrame([{
                        "paper_id": pid, "title": m.loc[i, "title"], "year": m.loc[i, "year"],
                        "filename": fname, "label_column": col,
                        "mistral_label": m.loc[i, col], "llama_label": l.loc[i, col],
                        "gemma_label": g.loc[i, col], "human_label": int(val),
                        "human_justification": just,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }], columns=RESULTS_COLUMNS).to_csv(
                        RESULTS_CSV, mode="a", header=not RESULTS_CSV.exists(), index=False)
                    print("  saved.")
                    break
                print("  please enter -1, 0, 1 or s")


def run(paper_folder: Path | None = None) -> None:
    dfs = _load_aggregates()
    tasks = find_disagreements(dfs)
    build_subset(dfs, tasks)
    if paper_folder is None:
        print("  No --paper-folder supplied: interactive annotation skipped.")
        print(f"  Using the shipped human results: {RESULTS_CSV.name}")
        return
    annotate_console(dfs, tasks, paper_folder)


def main() -> None:
    ap = argparse.ArgumentParser(description="Step 4: human re-annotation of LLM disagreements.")
    ap.add_argument("--paper-folder", type=Path, default=None,
                    help="Folder with the DELFI paper PDFs (required for interactive annotation).")
    args = ap.parse_args()
    run(args.paper_folder)


if __name__ == "__main__":
    main()
