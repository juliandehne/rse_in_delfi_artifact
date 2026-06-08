re# data/ — intermediate products

All inputs and intermediate products needed to reproduce the analysis **without**
the paper PDFs or an LLM API token. **No copyrighted paper full text is stored here**
(no `abstract` / `text` / `references` columns — see `pipeline/fulltext_guard.py`).

## Layout

| Path | Role | Produced by |
|------|------|-------------|
| `experiments/` | Raw LLM annotation runs — 3 models × 3 runs (prompt template 1). Metadata + label values + `_erklärung` (LLM justification). **Input** to step 5. | step 2 (shipped) |
| `intra_LLM/` | Per-model majority-vote aggregation across the 3 runs + intra-model ICR (Krippendorff α, Fleiss κ). | step 5 (regenerated) |
| `inter_LLM/df_human_reannotation_results.csv` | **Human** re-annotation of the 29 papers where all 3 LLMs disagreed. **Input** to step 5 inter. | step 4 (human, shipped) |
| `inter_LLM/df_papers_subset_for_human_reannotation.csv` | The disagreement subset given to the human annotator (context). | step 4 (shipped) |
| `inter_LLM/df_llm_experiments_final_aggregated_results_prompt_template_1.csv` | **Final** aggregated labels (3 LLMs majority + human fallback). The central artifact. | step 5 (regenerated) |
| `inter_LLM/icr_*`, `inter_LLM/llm_label_distribution_*` | Cross-LLM ICR, label-distribution analysis, and ICR vs the 2017 reference study. | step 5 (regenerated) |
| `reference_paper/Evaluationen3.xlsx` | The 2014–2016 reference study's **human** evaluation (binary + ordinal labels, no full text). Used for external validation and the descriptive figures. | reference study (shipped) |
| `prompt_templates/prompt_template_1.md` | The annotation prompt (system + user). Used by steps 2 and 4. | shipped |
| `descriptive/figures/` | Paradigm-distribution bubble chart + label-trend line plots. | step 3 (regenerated) |
| `secondary_analysis/` | Combined paradigm labels for the bias analysis. | step 6 (regenerated) |
| `preprocessed/` | **(gitignored, not shipped)** Full paper texts written by step 1 if a reviewer supplies the paper folder. | step 1 |

## Label schema

Binary (0/1): `label_forschungssoftware`, `label_software_evaluation`, `label_lehr_lern_setting`.
Ordinal (−1/0/+1): `label_prozess_paradigma`, `label_lernende_paradigma`,
`label_design_paradigma`, `label_bildungstechnologie_paradigma`.

Per-model columns are prefixed (`mistral_`, `llama_`, `gemma_`); per-run suffix `_run_{1,2,3}`;
within-model aggregate suffix `_agg`; final cross-model label suffix `_final`;
LLM justifications carry the `_erklärung` suffix.
