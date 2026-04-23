# DMS Xiaohongshu Panel Data Pipeline & Regression Analysis

[中文](README.md) | [English](README.en.md)

## What’s in this folder

This folder contains an end-to-end pipeline for:

- Cleaning the raw CSV
- Parsing quote information from the multi-line `quote` field
- Building derived metrics (CES, rates, monetization metrics)
- Producing descriptive statistics & plots
- Running pooled OLS regressions (no creator fixed effects), plus robustness checks

## Data files

- `DMS001_raw.csv`: raw input
- `DMS001_processed.csv`: cleaned + quote parsing + quote broadcast per creator
- `DMS001_enriched.csv`: processed data with derived metrics (CES / rates / value metrics, etc.)

## Scripts & outputs (recommended order)

### 1) Cleaning & quote parsing

- Script: `process_data.py`
- Input: `DMS001_raw.csv`
- Output: `DMS001_processed.csv`
- Key steps:
  - Remove comma separators in numbers (e.g., `4,336 -> 4336`)
  - Convert `w` unit (e.g., `2.3w -> 23000`)
  - Extract `quote_video, video_cpe, video_cpm, quote_post, post_cpe, post_cpm` from the multi-line `quote`
  - Broadcast each creator’s quote fields to all rows of that `koc_id`
  - Cast columns from `follower_count` to `is_commercial` to integers

Run:

```bash
python d:\investment\DMS\process_data.py
```

### 2) Derived metrics (CES / rates / monetization metrics)

- Script: `process_metrics.py`
- Input: `DMS001_processed.csv`
- Output: `DMS001_enriched.csv`

Run:

```bash
python d:\investment\DMS\process_metrics.py
```

### 3) Descriptive stats & visualization (Stage 1)

- Script: `stage1_descriptive_and_viz.py`
- Input: `DMS001_enriched.csv`
- Output folder: `stage1_output/`
  - Report: `stage1_output/output_stage1.md`
  - Figures: `stage1_output/figs/*.png`

Run:

```bash
python d:\investment\DMS\stage1_descriptive_and_viz.py
```

### 4) Regression outputs

Two pooled-OLS (no creator fixed effects) versions are kept separately:

#### 4.1 Original (no winsorization, no split, no clustered SE)

- Folder: `regression_output_ols_original/`
- Script: `regression_output_ols_original/run_regressions_original.py`
- Outputs:
  - `regression_output_ols_original/regression_results_original.md`
  - `regression_output_ols_original/figs/*.png`

Run:

```bash
python d:\investment\DMS\regression_output_ols_original\run_regressions_original.py
```

#### 4.2 Robustness (1% winsorization + split + clustered SE)

- Folder: `regression_output_ols_robustness/`
- Script: `regression_output_ols_robustness/run_regressions_robustness.py`
- Outputs:
  - `regression_output_ols_robustness/regression_results_robustness.md` (1% winsorization + White Robust/HC1)
  - `regression_output_ols_robustness/regression_results_split_cluster.md` (split by low/high + cluster-robust by koc_id)
  - `regression_output_ols_robustness/figs/*.png`

Run:

```bash
python d:\investment\DMS\regression_output_ols_robustness\run_regressions_robustness.py
```

#### 4.3 Other historical outputs

- `regression_output/`: historical fixed-effect output
- `regression_output_ols/`: intermediate iterations
- `run_regressions.py`: the working/iteration script (use the original/robustness folders as the canonical versions)

## Dependencies

Main dependencies:

- pandas
- numpy
- scipy
- matplotlib
- seaborn

