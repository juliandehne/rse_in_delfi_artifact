# data/ — datasets and codebook

This is the **codebook / data dictionary** for the published datasets. No copyrighted
paper full text is stored here (no `abstract` / `text` / `references` columns — see
`pipeline/fulltext_guard.py`). Format: open **UTF-8 CSV** (comma-separated, header row,
`.` decimal), plus one `.xlsx` (the 2017 reference study) and one `.md` (the prompt).

## Provenance (how the data were produced)

- **Population.** Papers from the DELFI/DeLFI conference proceedings (the German
  learning-technologies community), volumes **2003–2025**; `n = 798` papers of
  ≥ 3 pages (very short 1–2 page papers were excluded, as in the 2017 reference study).
- **Instrument.** A single annotation prompt operationalising the codebook,
  `prompt_templates/prompt_template_1.md` (system + user prompt). It fixes, per label,
  the textual evidence an annotator must find.
- **Annotators (machine).** Three open-weight LLMs via the KISSKI SAIA API:
  `mistral-large-3-675b-instruct-2512`, `llama-3.1-sauerkrautlm-70b-instruct`,
  `gemma-3-27b-it`; **temperature 0, top_p 1.0, seed 42**, **3 runs** per model
  (run dates 2026-03-10…19). (Live re-runs use `llama-3.3-70b-instruct`, as the 3.1
  model was deprecated by the provider; the shipped labels use the 3.1 ID above.)
- **Annotator (human).** One human resolved the 29 papers where all three models
  disagreed on an ordinal label (2026-03-26).
- **Reference labels.** Human codings from the 2017 reference study (`reference_paper/`).

## Generation method (the labels are partially synthetic)

The labels are **LLM-generated** (i.e. partially synthetic data). To regenerate:
run step 2 (`pipeline/step2_experiments.py`) with the shipped prompt and the model
IDs / parameters / seed above, then aggregate with step 5 (majority vote across the
3 runs, then across the 3 models; ordinal ties broken by the human label).
**Validation:** cross-model inter-coder reliability (Krippendorff's α, reported in
`inter_LLM/icr_*`) and external validation against the 2017 human reference study
(`inter_LLM/icr_replication_*_reference_study.csv`).

## The label set (core variables)

| Label (base name) | Meaning | Type | Allowed values |
|---|---|---|---|
| `label_forschungssoftware` | research software is present | binary | `0`, `1` |
| `label_software_evaluation` | a software evaluation was conducted | binary | `0`, `1` |
| `label_lehr_lern_setting` | a teaching–learning setting is present | binary | `0`, `1` |
| `label_prozess_paradigma` | process paradigm | ordinal | `-1`, `0`, `+1` |
| `label_lernende_paradigma` | outcome / learner paradigm | ordinal | `-1`, `0`, `+1` |
| `label_design_paradigma` | design paradigm | ordinal | `-1`, `0`, `+1` |
| `label_bildungstechnologie_paradigma` | acceptance / educational-technology paradigm | ordinal | `-1`, `0`, `+1` |

Every label has a companion free-text **`…_erklärung`** column (string): the
annotator's justification. Ordinal `0` = paradigm not (clearly) pursued; `+1` /
`-1` = the two opposing directions.

### Column-name grammar (lets you read any of the 185 columns)

```
[<model>_] <label> [_erklärung] [_run_<r>] [_agg | _final] [_timestamp]
```
- `<model>` prefix ∈ `mistral_`, `llama_`, `gemma_`, `human_` (cross-model files only)
- `_run_<r>`  r ∈ {1,2,3}: the value from run r
- `_agg`      within-model majority vote across the 3 runs
- `_final`    cross-model majority vote (ordinal ties → human label)
- `_erklärung`        free-text justification; `_erklärung_timestamp` = ISO-8601 time of a human justification

**Missing-value coding:** empty cell = missing (`NA`). Metadata fields are `NA` when
the proceedings provided no value (e.g. `doi`/`issn` for older volumes). For the
`*_combined` secondary-analysis labels, empty = NaN = "no direction" (all three
models abstained with `0`).

## Bibliographic metadata columns (shared by most tables)

`id` (int, stable paper key) · `title` (str) · `authors` (str) · `year` (int,
2003–2025) · `start_page`, `end_page` (int, may be `NA`) · `subject` (str) ·
`filename` (str, e.g. `51.pdf`) · `editors` (str) · `doi`, `isbn`, `issn` (str, may
be `NA`) · `proceeding_title`, `series_title`, `publisher`, `publication_place`,
`conference_date`, `conference_location`, `session_title` (str) · `publication_type`
(categorical: `Text/Conference Paper`, `…Poster`, `…Demo`, `…Abstract`,
`Complete Volume`) · `language` (`de`/`en`) · `peer_review_status` (`full`).

## File-by-file schema

| File (under `data/`) | Rows×Cols | Columns |
|---|---|---|
| `experiments/df_full_experiment_<model>_prompt_template_1_run_<r>_<date>.csv` (9 files) | 798×36 | 22 metadata + 7 labels + 7 `_erklärung`. One file per (model, run); raw LLM output. |
| `intra_LLM/df_full_experiment_<model>_prompt_template_1_aggregated.csv` (3) | 798×… | 22 metadata + per label: `_run_1/2/3` (+ `_erklärung_run_*`) + `_agg` (majority across runs). |
| `intra_LLM/icr_<model>_prompt_template_1.csv` (3) | 10×4 | `label`, `type` (binary/ordinal), `krippendorff_alpha`, `fleiss_kappa` — across the 3 runs. |
| `inter_LLM/df_llm_experiments_final_aggregated_results_prompt_template_1.csv` | 798×185 | 22 metadata + `<model>_<label>_run_<r>` / `_erklärung_run_<r>` / `_agg` for the 3 models + `human_label_<paradigm>` (+ `_erklärung`, `_erklärung_timestamp`) for the disagreement paradigms + `<label>_final` for all 7 labels. **The central dataset.** |
| `inter_LLM/df_human_reannotation_results.csv` | 32×11 | `paper_id`, `title`, `year`, `filename`, `label_column` (which ordinal label), `mistral_label`/`llama_label`/`gemma_label` (the 3 disagreeing values), `human_label` (`-1/0/1`), `human_justification` (str), `timestamp` (ISO-8601). |
| `inter_LLM/df_papers_subset_for_human_reannotation.csv` | 29×… | metadata + per-model `_agg` ordinal labels for the 29 disagreement papers (the annotation worklist). |
| `inter_LLM/icr_mistral_llama_gemma_prompt_template_1.csv` | 10×5 | `label`, `type`, `krippendorff_alpha`, `fleiss_kappa`, `gwet_ac1` — cross-model. |
| `inter_LLM/icr_replication_prompt_template_1_reference_study.csv` | 4×5 | same schema — final labels vs the 2017 reference study (binary). |
| `inter_LLM/llm_label_distribution_analysis_ordinal_labels.csv` | 15×9 | `label`, `llm`, `mean`, `n_neg1`, `pct_neg1`, `n_0`, `pct_0`, `n_pos1`, `pct_pos1`. |
| `reference_paper/Evaluationen3.xlsx` | 83×17 | 2017 human study: `DelFI Band` (year), `Beitragstitelseite` (page), `Evaluation durchgeführt`/`Einzelne Software`/`Lehr-Lernsetting` (binary 0/1), `Fokus Medialität`/`Akzeptanz`/`Normalität der Nutzung`/`Innovation`/`Empirischer Lernerfolg` (ordinal −1/0/1), `Softwareklasse` (str), `X-/Y-Koordinate` (derived paradigm coordinates), plus free-text note columns. |
| `prompt_templates/prompt_template_1.md` | — | the annotation instrument (system + user prompt with `{row[...]}` placeholders). |
| `descriptive/figures/*.png` | — | regenerated figures (paradigm-distribution bubble chart; binary/ordinal label trends). |
| `secondary_analysis/df_paradigms_combined.csv` | 798×7 | `title`, `year`, `publication_type`, `label_<paradigm>_combined` ×4 (values `-1`, `+1`, or empty=NaN when all models abstained). |
| `secondary_analysis/paradigm_year_trends.csv` | 23×5 | `year` + mean of each `label_<paradigm>_combined` per year. |

## Machine-readable metadata & license

Repository-level machine-readable metadata: `../CITATION.cff` (Citation File
Format). License: data under **CC-BY-4.0** (`../LICENSE-data`), code under MIT
(`../LICENSE`). No personal or human-subject data are released; the only human
content is the annotators' short justifications.
