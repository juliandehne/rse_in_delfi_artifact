"""
Step 2 — LLM annotation experiments.  SKIPPED BY DEFAULT.

Adapted from the source study's experiments/experiments/experiments.py. Two changes
for the artifact:
  * papers are read from the step-1 CSV (``data/preprocessed/delfi_paper_texts.csv``)
    instead of the original MySQL ``paper`` table (the DB is excluded from this artifact);
  * full-text columns (``abstract``, ``text``, ``references``) are dropped before
    saving — exactly as the original did "for legal reasons".

This step needs a **KISSKI SAIA API token** (env ``SAIA_API_KEY`` / ``SAIA_API_ENDPOINT``)
and the ``openai`` client, which artifact-track reviewers do NOT have. It is therefore
skipped by default. The shipped ``data/experiments/*.csv`` are the outputs of this step.

Run standalone (needs token + step-1 output):
    SAIA_API_KEY=... SAIA_API_ENDPOINT=... \
    python -m pipeline.step2_experiments --model mistral-large-3-675b-instruct-2512 --run run_1
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import random
from collections import deque
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from pipeline import config

# Fields substituted into the user prompt (mirrors the source study).
PROMPT_FIELDS = ["title", "authors", "year", "abstract", "text", "references"]
DROP_BEFORE_SAVE = ["abstract", "text", "references"]  # never persist full texts


class RateLimiter:
    """Sliding-window limiter for the KISSKI SAIA API (10 req/min, 200 req/hour)."""

    def __init__(self, max_per_minute=10, max_per_hour=200):
        self.max_per_minute = max_per_minute
        self.max_per_hour = max_per_hour
        self._ts: deque = deque()

    def wait_if_needed(self):
        while True:
            now = time.time()
            while self._ts and self._ts[0] < now - 3600:
                self._ts.popleft()
            if len(self._ts) >= self.max_per_hour:
                time.sleep((self._ts[0] + 3600) - now + 1.0)
                continue
            recent = [t for t in self._ts if t >= now - 60]
            if len(recent) >= self.max_per_minute:
                time.sleep((min(recent) + 60) - now + 0.5)
                continue
            break

    def record(self):
        self._ts.append(time.time())


def load_prompt_template(path: Path) -> tuple[str, str]:
    content = Path(path).read_text(encoding="utf-8")
    sys_m = re.search(r"#### 1\) System prompt\s*\n(.*?)(?=#### 2\))", content, re.DOTALL)
    usr_m = re.search(r"#### 2\) User prompt\s*\n(.*?)$", content, re.DOTALL)
    if not sys_m or not usr_m:
        raise ValueError(f"Could not parse system/user prompt sections from {path}")
    return sys_m.group(1).strip(), usr_m.group(1).strip()


def fill_user_prompt(template: str, row: pd.Series) -> str:
    result = template
    for field in PROMPT_FIELDS:
        result = result.replace(f"{{row['{field}']}}", str(row.get(field, "")))
    return result


def extract_json_from_response(raw: str) -> dict:
    cleaned = raw.strip()
    decoder = json.JSONDecoder()
    i = cleaned.find("{")
    if i != -1:
        try:
            obj, _ = decoder.raw_decode(cleaned, i)
            return obj
        except json.JSONDecodeError:
            pass
    block = re.search(r"```(?:json)?\s*\n([\s\S]*?)\n\s*```", cleaned)
    if block:
        return decoder.decode(block.group(1).strip())
    raise json.JSONDecodeError("No valid JSON object found", cleaned, 0)


class ModelUnavailableError(RuntimeError):
    """Raised when the requested model is not reachable on the SAIA endpoint."""


def assert_model_available(client, model: str) -> None:
    """Verify ``model`` is reachable before annotating.

    Queries the SAIA ``GET /models`` endpoint (the OpenAI/OpenAPI standard, exposed
    via ``client.models.list()``) and checks that ``model`` is in the returned list.
    Models get deprecated/removed by the provider, so a run can otherwise fail only
    after the first slow per-paper request — this fails fast with a clear message
    listing what *is* available.
    """
    try:
        available = [m.id for m in client.models.list().data]
    except Exception as exc:  # network/auth/endpoint errors — surface them clearly
        raise ModelUnavailableError(
            f"Could not query the SAIA /models endpoint to verify '{model}'. "
            f"Check SAIA_API_ENDPOINT / SAIA_API_KEY and connectivity. Underlying "
            f"error: {type(exc).__name__}: {exc}") from exc
    if model not in available:
        listed = ", ".join(sorted(available)) or "(none returned)"
        raise ModelUnavailableError(
            f"Model '{model}' is not reachable on the SAIA endpoint (likely deprecated "
            f"or renamed by the provider). Available models: {listed}. Update the model "
            f"id in pipeline/config.py (LIVE_MODELS) or pass a reachable --model.")


def classify_paper(client, row, model, system_prompt, user_prompt_template, rate_limiter,
                   temperature=0, seed=42, top_p=1.0):
    from openai import APITimeoutError, RateLimitError  # local import: optional dep
    user_prompt = fill_user_prompt(user_prompt_template, row)
    MAX_RETRIES, BASE_DELAY, response = 5, 1.0, None
    for attempt in range(MAX_RETRIES):
        rate_limiter.wait_if_needed()
        try:
            rate_limiter.record()
            response = client.chat.completions.create(
                model=model, temperature=temperature, top_p=top_p, seed=seed,
                messages=[{"role": "system", "content": system_prompt},
                          {"role": "user", "content": user_prompt}])
            break
        except APITimeoutError:
            return {"llm_error": "APITimeoutError", "llm_raw_response": None}
        except RateLimitError as e:
            if attempt == MAX_RETRIES - 1:
                return {"llm_error": f"RateLimitError: {e}", "llm_raw_response": None}
            time.sleep(BASE_DELAY * (2 ** attempt) * (1 + 0.25 * random.random()))
    raw = response.choices[0].message.content
    try:
        result = extract_json_from_response(raw)
        return result if isinstance(result, dict) else {"llm_error": "non-dict JSON", "llm_raw_response": raw}
    except json.JSONDecodeError as e:
        return {"llm_error": f"JSON parse error: {e}", "llm_raw_response": raw}


def run(model: str, run_id: str, prompt_template: Path | None = None,
        papers_csv: Path | None = None, test: bool = False,
        api_key: str | None = None, base_url: str | None = None,
        output_dir: Path | None = None) -> Path:
    # Credentials may be passed directly (CLI flags) or via the environment.
    api_key = api_key or os.getenv("SAIA_API_KEY")
    base_url = base_url or os.getenv("SAIA_API_ENDPOINT")
    if not api_key or not base_url:
        raise EnvironmentError(
            "Step 2 needs a SAIA API token. Provide it either as parameters "
            "(--saia-api-key / --saia-api-endpoint) or as environment variables "
            "(SAIA_API_KEY / SAIA_API_ENDPOINT). Reviewers without a token keep this "
            "step skipped — the shipped data/experiments/*.csv are this step's outputs.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError("Step 2 needs the 'openai' package (uncomment it in requirements.txt).") from exc

    papers_csv = papers_csv or (config.PREPROCESSED_DIR / "delfi_paper_texts.csv")
    if not Path(papers_csv).exists():
        raise FileNotFoundError(
            f"Paper input not found: {papers_csv}. Run step 1 (preprocessing) first with --paper-folder.")
    df = pd.read_csv(papers_csv)
    if "id" not in df.columns:
        df = df.reset_index().rename(columns={"index": "id"})
    if test:
        df = df.head(5)

    prompt_template = prompt_template or config.PROMPT_TEMPLATE
    system_prompt, user_prompt_template = load_prompt_template(prompt_template)
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=300.0)
    rl = RateLimiter()

    # Fail fast if the provider has deprecated/removed this model, instead of
    # discovering it mid-run after the first per-paper request.
    assert_model_available(client, model)

    print("classifying papers with model: ", model)
    rows = []
    for _, row in df.iterrows():
        res = classify_paper(client, row, model, system_prompt, user_prompt_template, rl)
        res["id"] = row["id"]
        rows.append(res)

    results = pd.DataFrame(rows)
    annotated = df.merge(results, on="id", how="left")
    annotated = annotated.drop(columns=[c for c in DROP_BEFORE_SAVE if c in annotated.columns])

    today = date.today().strftime("%Y-%m-%d")
    out_dir = output_dir or config.EXPERIMENTS_DIR
    out = Path(out_dir) / f"df_full_experiment_{model}_{config.PROMPT_TEMPLATE_NAME}_{run_id}_{today}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    annotated.to_csv(out, index=False)
    print(f"  Saved {len(annotated)} rows → {out} (full-text columns dropped)")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Step 2: LLM annotation via KISSKI SAIA API (needs token).")
    ap.add_argument("--model", required=True)
    ap.add_argument("--run", default="run_1")
    ap.add_argument("--prompt-template", type=Path, default=None)
    ap.add_argument("--papers-csv", type=Path, default=None)
    ap.add_argument("--saia-api-key", default=None,
                    help="SAIA API key (falls back to env SAIA_API_KEY).")
    ap.add_argument("--saia-api-endpoint", default=None,
                    help="SAIA API endpoint URL (falls back to env SAIA_API_ENDPOINT).")
    ap.add_argument("--test", action="store_true", help="Annotate only the first 5 papers.")
    args = ap.parse_args()
    run(args.model, args.run, args.prompt_template, args.papers_csv, args.test,
        api_key=args.saia_api_key, base_url=args.saia_api_endpoint)


if __name__ == "__main__":
    main()
