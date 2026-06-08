#!/usr/bin/env python3
"""
run_pipeline.py — management script for the rse_in_delfi_artifact pipeline.

Runs the six pipeline steps in dependency order. By default it runs only the
steps that work from the shipped ``data/``:

    step 3  descriptive analysis
    step 5  label aggregation (intra + inter)
    step 6  secondary analysis

The three steps that need resources artifact reviewers don't have are
**SKIPPED BY DEFAULT** and must be opted into explicitly:

    step 1  preprocessing      — needs --paper-folder (paper PDFs)
    step 2  experiments        — needs a SAIA API token (env SAIA_API_KEY/_ENDPOINT)
    step 4  human annotation   — needs --paper-folder (interactive)

Examples:
    python run_pipeline.py                                   # default: steps 3, 5, 6
    python run_pipeline.py --paper-folder ./papers --run-preprocessing --run-human-annotation
    python run_pipeline.py --run-experiments                 # if you exported a SAIA token
    python run_pipeline.py --only 5                          # run a single step

A no-full-text guard runs first (unless --no-guard) and aborts if any paper full
text is found under data/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipeline import config
from pipeline.fulltext_guard import assert_no_fulltext
# Steps 3, 5, 6 work from shipped data and have light deps — import eagerly.
from pipeline import step3_descriptive_analysis, step5_label_aggregation, step6_secondary_analysis
# Steps 1, 2, 4 pull in optional deps (pymupdf / openai); import them lazily so the
# default run (3, 5, 6) works without those packages installed.


def _banner(text: str) -> None:
    print("\n" + "#" * 72 + f"\n#  {text}\n" + "#" * 72)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Run the rse_in_delfi_artifact pipeline (steps 1 & 2 & 4 skipped by default).",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--paper-folder", type=Path, default=None,
                    help="Folder with the DELFI paper PDFs (needed for steps 1 and 4).")
    ap.add_argument("--run-preprocessing", action="store_true",
                    help="Enable step 1 (needs --paper-folder). Default: skipped.")
    ap.add_argument("--run-experiments", action="store_true",
                    help="Enable step 2 (needs a SAIA API token). Default: skipped.")
    ap.add_argument("--run-human-annotation", action="store_true",
                    help="Enable interactive step 4 (needs --paper-folder). Default: skipped.")
    ap.add_argument("--only", type=int, choices=[1, 2, 3, 4, 5, 6], default=None,
                    help="Run only this one step (overrides the default selection).")
    ap.add_argument("--models", nargs="+", default=None,
                    help="For step 2: model id(s) to annotate with (default: all in config.MODELS).")
    ap.add_argument("--no-guard", action="store_true",
                    help="Skip the no-full-text guard (not recommended).")
    args = ap.parse_args()

    # Decide which steps run.
    if args.only is not None:
        run1, run2, run3, run4, run5, run6 = (args.only == i for i in (1, 2, 3, 4, 5, 6))
    else:
        run1, run2 = args.run_preprocessing, args.run_experiments
        run4 = args.run_human_annotation
        run3 = run5 = run6 = True  # the shipped-data steps always run by default

    if run1 and args.paper_folder is None:
        ap.error("step 1 (preprocessing) needs --paper-folder (the paper PDFs).")
    if run4 and args.paper_folder is None:
        print("[note] step 4: no --paper-folder → running subset computation only "
              "(interactive annotation needs the paper PDFs).")

    if not args.no_guard:
        _banner("Full-text guard")
        assert_no_fulltext()

    if run1:
        _banner("Step 1 — Preprocessing (PDF → text)")
        from pipeline import step1_preprocessing
        step1_preprocessing.run(args.paper_folder)

    if run2:
        _banner("Step 2 — LLM experiments (SAIA API)")
        from pipeline import step2_experiments
        models = args.models or list(config.MODELS.values())
        for model in models:
            for run_id in ("run_1", "run_2", "run_3"):
                step2_experiments.run(model, run_id)

    # Step 5 is split so human annotation (step 4) can slot between intra and inter.
    if run5:
        _banner("Step 5a — Intra-LLM aggregation")
        step5_label_aggregation.run_intra()

    if run4:
        from pipeline import step4_human_annotation
        _banner("Step 4 — Human annotation")
        step4_human_annotation.run(args.paper_folder)  # None → subset computation only

    if run5:
        _banner("Step 5b — Inter-LLM aggregation")
        step5_label_aggregation.run_inter()

    if run3:
        _banner("Step 3 — Descriptive analysis (figures)")
        step3_descriptive_analysis.main()

    if run6:
        _banner("Step 6 — Secondary analysis (biases)")
        step6_secondary_analysis.main()

    # Re-assert the guarantee after any regeneration.
    if not args.no_guard:
        _banner("Full-text guard (post-run)")
        assert_no_fulltext()

    _banner("Pipeline complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
