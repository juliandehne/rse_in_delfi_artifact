"""
Step 5 — Label aggregation (intra-LLM + inter-LLM).

Adapted from the source study's
  analysis/label_aggregation/label_aggregation_intra_LLM.py   and
  analysis/label_aggregation/label_aggregation_inter_LLM.py
with all paths rewired to the artifact's ``data/`` layout (no MySQL, no repo-root cwd).

Intra-LLM (per model): load the 3 run CSVs, validate, compute inter-coder
reliability (ICR) across the 3 runs, majority-vote aggregate, save.

Inter-LLM (across models): load the 3 aggregated CSVs + human re-annotations,
compute ICR across the 3 LLMs, analyse label distributions, majority-vote
aggregate (ordinal ties resolved by the human label), validate against the 2017
reference study, and save the final aggregated dataframe.

Reads:  data/experiments/*.csv, data/inter_LLM/df_human_reannotation_results.csv,
        data/reference_paper/Evaluationen3.xlsx
Writes: data/intra_LLM/*, data/inter_LLM/* (overwrites the shipped precomputed copies)

Run standalone:
    python -m pipeline.step5_label_aggregation
"""

from __future__ import annotations

import warnings
from collections import Counter

import numpy as np
import pandas as pd
import krippendorff
from statsmodels.stats.inter_rater import aggregate_raters, fleiss_kappa

from pipeline import config

LABEL_COLUMNS = []
for _c in config.BINARY_COLS + config.ORDINAL_COLS:
    LABEL_COLUMNS += [_c, f"{_c}_erklärung"]
LABEL_VALUE_COLUMNS = config.BINARY_COLS + config.ORDINAL_COLS


# ══════════════════════════════════════════════════════════════════════════════
#  PART A — Intra-LLM aggregation (per model, across 3 runs)
# ══════════════════════════════════════════════════════════════════════════════

def _load_run_csvs(model_id: str) -> list[pd.DataFrame]:
    dfs = []
    for run in range(1, 4):
        pattern = f"df_full_experiment_{model_id}_{config.PROMPT_TEMPLATE_NAME}_run_{run}_*.csv"
        matches = sorted(config.EXPERIMENTS_DIR.glob(pattern))
        if not matches:
            raise FileNotFoundError(f"No run file matching {config.EXPERIMENTS_DIR / pattern}")
        df = pd.read_csv(matches[-1])  # most recent if several
        print(f"    run {run}: {matches[-1].name} ({len(df)} rows)")
        dfs.append(df)
    return dfs


def _merge_runs(dfs: list[pd.DataFrame]) -> pd.DataFrame:
    renamed = [
        df.rename(columns={col: f"{col}_run_{i}" for col in LABEL_COLUMNS})
        for i, df in enumerate(dfs, start=1)
    ]
    df1, df2, df3 = renamed
    return (
        df1
        .merge(df2[["id"] + [f"{c}_run_2" for c in LABEL_COLUMNS]], on="id", how="left")
        .merge(df3[["id"] + [f"{c}_run_3" for c in LABEL_COLUMNS]], on="id", how="left")
    )


def _icr_across_runs(df_merged: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in config.BINARY_COLS:
        arrs = [df_merged[f"{col}_run_{r}"].to_numpy() for r in range(1, 4)]
        # Krippendorff's alpha is undefined when the domain has a single value
        # (all runs agree on one label, common on tiny test subsets) — that is
        # perfect agreement, so report 1.0. Mirrors _icr_across_llms below.
        try:
            alpha = krippendorff.alpha(np.array(arrs), level_of_measurement="nominal")
        except ValueError:
            alpha = 1.0
        table, _ = aggregate_raters(np.column_stack(arrs))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            fk = fleiss_kappa(table)
        if np.isnan(fk):
            fk = 1.0
        rows.append({"label": col, "type": "binary",
                     "krippendorff_alpha": round(alpha, 2), "fleiss_kappa": round(fk, 2)})
    for col in config.ORDINAL_COLS:
        arrs = [df_merged[f"{col}_run_{r}"].to_numpy() for r in range(1, 4)]
        try:
            alpha = krippendorff.alpha(np.array(arrs), level_of_measurement="ordinal")
        except ValueError:
            alpha = 1.0
        rows.append({"label": col, "type": "ordinal",
                     "krippendorff_alpha": round(alpha, 2), "fleiss_kappa": None})
    df_icr = pd.DataFrame(rows)
    summary = pd.DataFrame([
        {"label": "Average (binary)", "type": "",
         "krippendorff_alpha": round(df_icr.loc[df_icr.type == "binary", "krippendorff_alpha"].mean(), 2),
         "fleiss_kappa": round(df_icr.loc[df_icr.type == "binary", "fleiss_kappa"].mean(), 3)},
        {"label": "Average (ordinal)", "type": "",
         "krippendorff_alpha": round(df_icr.loc[df_icr.type == "ordinal", "krippendorff_alpha"].mean(), 2),
         "fleiss_kappa": None},
        {"label": "Average (all labels)", "type": "",
         "krippendorff_alpha": round(df_icr["krippendorff_alpha"].mean(), 2), "fleiss_kappa": None},
    ])
    return pd.concat([df_icr, summary], ignore_index=True)


def _aggregate_runs(df_merged: pd.DataFrame) -> pd.DataFrame:
    df = df_merged.copy()
    for col in LABEL_VALUE_COLUMNS:
        run_cols = [f"{col}_run_{r}" for r in range(1, 4)]
        df[f"{col}_agg"] = df[run_cols].apply(
            lambda row: Counter(row.values).most_common(1)[0][0], axis=1)
    return df


def run_intra() -> None:
    config.INTRA_DIR.mkdir(parents=True, exist_ok=True)
    for short, model_id in config.MODELS.items():
        print(f"  [{short}] {model_id}")
        dfs = _load_run_csvs(model_id)
        df_merged = _merge_runs(dfs)
        df_icr = _icr_across_runs(df_merged)
        df_icr.to_csv(config.INTRA_DIR / f"icr_{model_id}_{config.PROMPT_TEMPLATE_NAME}.csv", index=False)
        df_agg = _aggregate_runs(df_merged)
        out = config.INTRA_DIR / f"df_full_experiment_{model_id}_{config.PROMPT_TEMPLATE_NAME}_aggregated.csv"
        df_agg.to_csv(out, index=False)
        print(f"    → {out.name}")


# ══════════════════════════════════════════════════════════════════════════════
#  PART B — Inter-LLM aggregation (across the 3 models + human fallback)
# ══════════════════════════════════════════════════════════════════════════════

def gwet_ac1_binary(arrs: list[np.ndarray]) -> float:
    """Gwet's AC1 for R raters on a binary (0/1) variable (robust to prevalence paradox)."""
    ratings = np.column_stack(arrs)
    n, R = ratings.shape
    Q = 2
    r_1 = ratings.sum(axis=1)
    r_0 = R - r_1
    P_a = ((r_1 * (r_1 - 1) + r_0 * (r_0 - 1)) / (R * (R - 1))).mean()
    pi_1 = r_1.sum() / (n * R)
    pi_0 = 1 - pi_1
    P_e = (1 / (Q - 1)) * (pi_0 * (1 - pi_0) + pi_1 * (1 - pi_1))
    return (P_a - P_e) / (1 - P_e)


def _load_aggregated() -> dict[str, pd.DataFrame]:
    out = {}
    for short, model_id in config.MODELS.items():
        out[short] = pd.read_csv(
            config.INTRA_DIR / f"df_full_experiment_{model_id}_{config.PROMPT_TEMPLATE_NAME}_aggregated.csv")
    ids = [list(df["id"]) for df in out.values()]
    assert all(x == ids[0] for x in ids), "ID mismatch between LLM dataframes — rows not aligned!"
    print(f"  ID check passed: 3 dfs share {len(ids[0])} IDs in the same order.")
    return out


def _icr_across_llms(dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    frames = list(dfs.values())
    for col in config.BINARY_COLS:
        arrs = [df[f"{col}_agg"].to_numpy() for df in frames]
        try:
            alpha = krippendorff.alpha(np.array(arrs), level_of_measurement="nominal")
        except ValueError:
            alpha = 1.0
        table, _ = aggregate_raters(np.column_stack(arrs))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            fk = fleiss_kappa(table)
        if np.isnan(fk):
            fk = 1.0
        rows.append({"label": col, "type": "binary", "krippendorff_alpha": round(alpha, 2),
                     "fleiss_kappa": round(fk, 2), "gwet_ac1": round(gwet_ac1_binary(arrs), 2)})
    for col in config.ORDINAL_COLS:
        arrs = [df[f"{col}_agg"].to_numpy() for df in frames]
        alpha = krippendorff.alpha(np.array(arrs), level_of_measurement="ordinal")
        rows.append({"label": col, "type": "ordinal", "krippendorff_alpha": round(alpha, 2),
                     "fleiss_kappa": None, "gwet_ac1": None})
    df_icr = pd.DataFrame(rows)
    bm, om = df_icr.type == "binary", df_icr.type == "ordinal"
    summary = pd.DataFrame([
        {"label": "Average (binary)", "type": "",
         "krippendorff_alpha": round(df_icr.loc[bm, "krippendorff_alpha"].mean(), 2),
         "fleiss_kappa": round(df_icr.loc[bm, "fleiss_kappa"].mean(), 3),
         "gwet_ac1": round(df_icr.loc[bm, "gwet_ac1"].mean(), 2)},
        {"label": "Average (ordinal)", "type": "",
         "krippendorff_alpha": round(df_icr.loc[om, "krippendorff_alpha"].mean(), 2),
         "fleiss_kappa": None, "gwet_ac1": None},
        {"label": "Average (all labels)", "type": "",
         "krippendorff_alpha": round(df_icr["krippendorff_alpha"].mean(), 2),
         "fleiss_kappa": None, "gwet_ac1": None},
    ])
    return pd.concat([df_icr, summary], ignore_index=True)


def _reshape_human(df_human: pd.DataFrame) -> pd.DataFrame:
    df = df_human.copy()
    df["paradigm"] = (df["label_column"].str.replace(r"^label_", "", regex=True)
                                        .str.replace(r"_agg$", "", regex=True))
    wide = df.pivot(index="paper_id", columns="paradigm",
                    values=["human_label", "human_justification", "timestamp"])
    wide.columns = [
        f"human_label_{p}" if m == "human_label"
        else f"human_label_{p}_erklärung" if m == "human_justification"
        else f"human_label_{p}_erklärung_timestamp"
        for m, p in wide.columns
    ]
    return wide.reset_index().rename(columns={"paper_id": "id"})


def _majority_vote(frames: list[pd.DataFrame], col: str) -> pd.Series:
    return pd.concat([f[col] for f in frames], axis=1).mode(axis=1)[0]


def _prefix(df: pd.DataFrame, name: str) -> pd.DataFrame:
    return df.rename(columns={c: f"{name}_{c}" for c in df.columns if c not in config.METADATA_COLS})


def _aggregate_final(dfs: dict[str, pd.DataFrame], df_human: pd.DataFrame) -> pd.DataFrame:
    frames = list(dfs.values())
    for col in config.METADATA_COLS:
        assert frames[0][col].equals(frames[1][col]) and frames[0][col].equals(frames[2][col]), \
            f"Metadata mismatch in column: {col}"

    pref = {name: _prefix(df, name) for name, df in dfs.items()}
    df_final = pref["mistral"].merge(
        pref["llama"][[c for c in pref["llama"].columns if c == "id" or c.startswith("llama_")]],
        on="id", how="left").merge(
        pref["gemma"][[c for c in pref["gemma"].columns if c == "id" or c.startswith("gemma_")]],
        on="id", how="left")
    df_final = df_final.merge(_reshape_human(df_human), on="id", how="left")

    for col in config.BINARY_COLS:
        df_final[f"{col}_final"] = _majority_vote(frames, f"{col}_agg").astype(int)

    for col in config.ORDINAL_COLS:
        agg = f"{col}_agg"
        a = [df[agg].to_numpy() for df in frames]
        disagree = (a[0] != a[1]) & (a[0] != a[2]) & (a[1] != a[2])
        vals = _majority_vote(frames, agg).astype(int)
        n = int(disagree.sum())
        if n > 0:
            vals[disagree] = df_final.loc[disagree, f"human_{col}"].values.astype(int)
        df_final[f"{col}_final"] = vals.astype(int)
        print(f"  {col}: {n} complete disagreement(s) → resolved with human label.")
    return df_final


def run_inter() -> None:
    config.INTER_DIR.mkdir(parents=True, exist_ok=True)
    dfs = _load_aggregated()
    df_human = pd.read_csv(config.HUMAN_REANNOTATION_CSV)

    df_icr = _icr_across_llms(dfs)
    df_icr.to_csv(config.INTER_DIR / "icr_mistral_llama_gemma_prompt_template_1.csv", index=False)
    print("  ICR (3 LLMs):")
    print(df_icr.to_string(index=False))

    df_final = _aggregate_final(dfs, df_human)
    df_final.to_csv(config.FINAL_CSV, index=False)
    print(f"\n  Final aggregated df → {config.FINAL_CSV.name}  shape={df_final.shape}")

    # External validation vs the 2017 reference study (binary labels).
    try:
        from pipeline.reference_validation import validate_against_reference
        validate_against_reference(df_final)
    except Exception as exc:  # reference validation is non-fatal for the core artifact
        print(f"  [warn] reference validation skipped: {exc}")


def main() -> None:
    print("=" * 60, "\n  Step 5a — Intra-LLM aggregation\n", "=" * 60)
    run_intra()
    print("\n", "=" * 60, "\n  Step 5b — Inter-LLM aggregation\n", "=" * 60)
    run_inter()
    print("\nStep 5 done.")


if __name__ == "__main__":
    main()
