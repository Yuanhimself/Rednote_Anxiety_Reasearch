# DMS 小红书笔记面板数据处理与回归分析

[中文](README.md) | [English](README.en.md)

## 项目内容

本目录包含一套从原始 CSV 清洗、报价信息解析、衍生指标构建，到描述性统计/可视化与回归分析（含稳健性检验）的脚本与输出文件。

## 数据文件

- `DMS001_raw.csv`：原始数据
- `DMS001_processed.csv`：清洗后 + 报价字段解析 + 按博主补齐报价
- `DMS001_enriched.csv`：在 processed 基础上新增 CES、率类指标、商业价值等二级变量

## 脚本与产出（按推荐执行顺序）

### 1) 清洗与报价解析

- 脚本：`process_data.py`
- 输入：`DMS001_raw.csv`
- 输出：`DMS001_processed.csv`
- 主要处理：
  - 数字去逗号（如 `4,336 -> 4336`）
  - `w` 单位换算（如 `2.3w -> 23000`）
  - 从 `quote` 多行文本中提取 `quote_video, video_cpe, video_cpm, quote_post, post_cpe, post_cpm`
  - 将同一 `koc_id` 的报价补齐到该博主所有行
  - `follower_count` 到 `is_commercial` 列输出为整数

运行：

```bash
python d:\investment\DMS\process_data.py
```

### 2) 二级指标构建（CES/率类/商业价值）

- 脚本：`process_metrics.py`
- 输入：`DMS001_processed.csv`
- 输出：`DMS001_enriched.csv`

运行：

```bash
python d:\investment\DMS\process_metrics.py
```

### 3) 描述性统计与可视化（阶段 1）

- 脚本：`stage1_descriptive_and_viz.py`
- 输入：`DMS001_enriched.csv`
- 输出目录：`stage1_output/`
  - 报告：`stage1_output/output_stage1.md`
  - 图片：`stage1_output/figs/*.png`

运行：

```bash
python d:\investment\DMS\stage1_descriptive_and_viz.py
```

### 4) 回归分析输出

本项目保留两套“混合 OLS（不含博主固定效应）”脚本与输出，便于区分“原版”与“稳健性检验版”。

#### 4.1 原版（无缩尾、无拆分、无聚类）

- 目录：`regression_output_ols_original/`
- 脚本：`regression_output_ols_original/run_regressions_original.py`
- 输出：
  - `regression_output_ols_original/regression_results_original.md`
  - `regression_output_ols_original/figs/*.png`

运行：

```bash
python d:\investment\DMS\regression_output_ols_original\run_regressions_original.py
```

#### 4.2 稳健性检验版（1% 缩尾 + 拆分 + 聚类）

- 目录：`regression_output_ols_robustness/`
- 脚本：`regression_output_ols_robustness/run_regressions_robustness.py`
- 输出：
  - `regression_output_ols_robustness/regression_results_robustness.md`（1% 缩尾 + White Robust/HC1）
  - `regression_output_ols_robustness/regression_results_split_cluster.md`（low/high 拆分 + koc_id 聚类稳健）
  - `regression_output_ols_robustness/figs/*.png`

运行：

```bash
python d:\investment\DMS\regression_output_ols_robustness\run_regressions_robustness.py
```

#### 4.3 其它回归输出（历史版本）

- `regression_output/`：固定效应版本的历史输出（如需可参考）
- `regression_output_ols/`：迭代过程中的输出目录（如需可参考）
- `run_regressions.py`：迭代用脚本（建议以 original/robustness 两套为准）

## 依赖环境

脚本主要依赖：

- pandas
- numpy
- scipy
- matplotlib
- seaborn

如在本机环境中缺少依赖，请先安装对应包后再运行。

