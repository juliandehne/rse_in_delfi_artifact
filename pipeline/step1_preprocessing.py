"""
Step 1 — Preprocessing (PDF → text).  SKIPPED BY DEFAULT.

Extracts main content + references from the DELFI paper PDFs using the source
study's regex/PyMuPDF extractor (``pdf_text_extraction.py``, copied verbatim).

This step needs the **paper PDF folder**, which artifact-track reviewers do NOT
have (the analyzed papers are copyrighted). It is therefore skipped by default and
only runs when ``--paper-folder`` is supplied.

Its output (``data/preprocessed/delfi_paper_texts.csv``) contains paper FULL TEXT
and is written into the ``.gitignore``'d ``data/preprocessed/`` directory — it must
never be committed. Downstream, step 2 consumes this file in place of the original
study's MySQL ``paper`` table.

Run standalone:
    python -m pipeline.step1_preprocessing --paper-folder /path/to/papers
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from pipeline import config
from pipeline.pdf_text_extraction import (
    extract_text_from_pdf,
    extract_main_content,
    extract_references,
    get_page_count,
)

# The reference study excluded very short papers (1-2 pages) from classification.
MIN_PAGES = 3


def run(paper_folder: Path, output_csv: Path | None = None, min_pages: int = MIN_PAGES) -> Path:
    paper_folder = Path(paper_folder)
    if not paper_folder.is_dir():
        raise FileNotFoundError(f"--paper-folder not found: {paper_folder}")

    output_csv = output_csv or (config.PREPROCESSED_DIR / "delfi_paper_texts.csv")
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    pdfs = sorted(paper_folder.rglob("*.pdf"))
    print(f"  Found {len(pdfs)} PDF(s) under {paper_folder}")
    for pdf in pdfs:
        try:
            if get_page_count(pdf) < min_pages:
                continue
            raw = extract_text_from_pdf(pdf, min_pages=min_pages)
            if raw is None:
                continue
            rows.append({
                "filename": pdf.name,
                "text": extract_main_content(raw),
                "references": extract_references(raw),
            })
        except Exception as exc:
            print(f"  [warn] failed on {pdf.name}: {exc}")

    df = pd.DataFrame(rows)
    df.to_csv(output_csv, index=False)
    print(f"  Wrote {len(df)} paper texts → {output_csv}")
    print("  NOTE: this file contains full texts and is gitignored — do not commit it.")
    print("  To attach bibliographic metadata, join this on 'filename' with your")
    print("  proceedings metadata (see the source repo's preprocessing/data_preparation.ipynb).")
    return output_csv


def main() -> None:
    ap = argparse.ArgumentParser(description="Step 1: extract text from DELFI paper PDFs.")
    ap.add_argument("--paper-folder", required=True, type=Path,
                    help="Folder containing the DELFI paper PDFs (reviewers usually lack this).")
    ap.add_argument("--output", type=Path, default=None,
                    help="Output CSV (default: data/preprocessed/delfi_paper_texts.csv).")
    ap.add_argument("--min-pages", type=int, default=MIN_PAGES)
    args = ap.parse_args()
    run(args.paper_folder, args.output, args.min_pages)


if __name__ == "__main__":
    main()
