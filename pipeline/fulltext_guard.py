"""
fulltext_guard.py

Asserts that the shipped ``data/`` directory contains **no copyrighted paper
full text**. The analyzed DELFI papers may not be redistributed, so the artifact
ships only labels, justifications and bibliographic metadata.

Two complementary checks per tabular file (CSV + XLSX) under ``data/``:

1. **Banned column names** — fails if a column called ``text``/``abstract``/
   ``references``/``main_content``/… is present (see config.FULLTEXT_COLUMNS).
   These are exactly the columns the original ``experiments.py`` drops
   "for legal reasons" before saving.
2. **Cell-length heuristic** — fails if any cell exceeds ``MAX_CELL_CHARS``.
   LLM/human justifications are at most a few hundred chars; a full paper body
   is tens of thousands. The threshold sits safely in between.

Run standalone:
    python -m pipeline.fulltext_guard
Returns a non-zero exit code (and raises) if a violation is found.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from pipeline import config

# A justification paragraph is well under this; a paper body is far above it.
MAX_CELL_CHARS = 5000


def _iter_tables(data_dir: Path):
    """Yield (path, DataFrame) for every CSV/XLSX under data_dir."""
    for path in sorted(data_dir.rglob("*")):
        if path.suffix.lower() == ".csv":
            yield path, pd.read_csv(path, low_memory=False)
        elif path.suffix.lower() in {".xlsx", ".xls"}:
            yield path, pd.read_excel(path)


def check_no_fulltext(data_dir: Path | None = None) -> list[str]:
    """
    Scan all tables under data_dir. Returns a list of human-readable violation
    strings (empty list == clean).
    """
    data_dir = data_dir or config.DATA
    violations: list[str] = []

    for path, df in _iter_tables(data_dir):
        rel = path.relative_to(data_dir.parent)

        # 1) banned column names (case-insensitive, exact match)
        for col in df.columns:
            if str(col).strip().lower() in config.FULLTEXT_COLUMNS:
                violations.append(f"{rel}: banned full-text column '{col}'")

        # 2) over-long cells (check every non-numeric column)
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                continue
            lengths = df[col].dropna().astype(str).str.len()
            if not lengths.empty and lengths.max() > MAX_CELL_CHARS:
                violations.append(
                    f"{rel}: column '{col}' has a {int(lengths.max())}-char cell "
                    f"(> {MAX_CELL_CHARS}); possible full text"
                )

    return violations


def assert_no_fulltext(data_dir: Path | None = None) -> None:
    """Raise AssertionError if any full text is found in data_dir."""
    violations = check_no_fulltext(data_dir)
    if violations:
        msg = "Full-text guard FAILED — data/ must not contain paper full texts:\n  - " + \
              "\n  - ".join(violations)
        raise AssertionError(msg)
    print("Full-text guard passed: no paper full texts found in data/.")


if __name__ == "__main__":
    try:
        assert_no_fulltext()
    except AssertionError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
