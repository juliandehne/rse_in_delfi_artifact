"""
Step 6 — Secondary analysis (paradigm biases).

Ported from the source study's analysis/secondary_analysis/biases.ipynb.
Loads the final aggregated labels, derives a per-paradigm "combined" label that
ignores abstentions (0 = paradigm not pursued), and reports how those combined
paradigm labels relate to publication metadata (year, publication type).

Reads:  data/inter_LLM/<final>.csv
Writes: data/secondary_analysis/df_paradigms_combined.csv
        data/secondary_analysis/paradigm_year_trends.csv

Run standalone:
    python -m pipeline.step6_secondary_analysis
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from pipeline import config

PARADIGMS = [
    "prozess_paradigma",
    "lernende_paradigma",
    "design_paradigma",
    "bildungstechnologie_paradigma",
]


def combine_paradigm_labels(df_final: pd.DataFrame) -> pd.DataFrame:
    """
    Combine the 3 per-LLM ``_agg`` ordinal votes into one directional label,
    ignoring 0s (abstentions):
      - all three 0      -> NaN  (paradigm not pursued by any model)
      - otherwise        -> +1 if the non-zero votes sum positive, else -1
    """
    keep = [c for c in df_final.columns
            if "_agg" in c or "_final" in c or c in ("year", "publication_type", "title")]
    df = df_final[keep]
    out = df[["title", "year", "publication_type"]].copy()

    for paradigm in PARADIGMS:
        cols = [f"{m}_label_{paradigm}_agg" for m in ("mistral", "llama", "gemma")]

        def combine(row):
            values = row[cols].tolist()
            if all(v == 0 for v in values):
                return np.nan
            non_zero = [v for v in values if v != 0]
            return 1 if sum(non_zero) > 0 else -1

        out[f"label_{paradigm}_combined"] = df.apply(combine, axis=1)
    return out


def paradigm_year_trends(df_combined: pd.DataFrame) -> pd.DataFrame:
    """Mean combined paradigm label per year (directional trend over time)."""
    combined_cols = [f"label_{p}_combined" for p in PARADIGMS]
    return (df_combined.groupby("year")[combined_cols]
            .mean().round(3).reset_index())


def main() -> None:
    config.SECONDARY_DIR.mkdir(parents=True, exist_ok=True)
    df_final = pd.read_csv(config.FINAL_CSV)
    print(f"  Loaded final df: {df_final.shape}")

    df_combined = combine_paradigm_labels(df_final)
    out1 = config.SECONDARY_DIR / "df_paradigms_combined.csv"
    df_combined.to_csv(out1, index=False)
    print(f"  Combined paradigm labels → {out1.name}")
    for p in PARADIGMS:
        col = f"label_{p}_combined"
        vc = df_combined[col].value_counts(dropna=False).to_dict()
        print(f"    {col}: {vc}")

    df_trends = paradigm_year_trends(df_combined)
    out2 = config.SECONDARY_DIR / "paradigm_year_trends.csv"
    df_trends.to_csv(out2, index=False)
    print(f"  Paradigm year trends → {out2.name}")
    print("Step 6 done.")


if __name__ == "__main__":
    main()
