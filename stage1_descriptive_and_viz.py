import os
import math
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt


def safe_as_numeric(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def fmt_float(x, digits=6):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return ""
    try:
        return f"{float(x):.{digits}f}"
    except Exception:
        return str(x)


def build_desc_table(df, cols):
    table = []
    for c in cols:
        if c not in df.columns:
            continue
        s = pd.to_numeric(df[c], errors="coerce")
        table.append(
            {
                "variable": c,
                "mean": s.mean(),
                "std": s.std(ddof=1),
                "min": s.min(),
                "max": s.max(),
                "n": int(s.notna().sum()),
                "n_zero": int((s == 0).sum(skipna=True)),
                "n_negative": int((s < 0).sum(skipna=True)),
            }
        )
    out = pd.DataFrame(table)
    return out


def save_fig(path):
    plt.tight_layout()
    plt.savefig(path, dpi=200, bbox_inches="tight")
    plt.close()


def main():
    input_path = r"d:\investment\DMS\DMS001_enriched.csv"
    if not os.path.exists(input_path):
        raise FileNotFoundError(input_path)

    out_dir = r"d:\investment\DMS\stage1_output"
    fig_dir = os.path.join(out_dir, "figs")
    ensure_dir(fig_dir)

    df = pd.read_csv(input_path)

    required = [
        "high_or_low",
        "anxiety_score",
        "ces_total",
        "ces_per_1000_view",
        "interaction_rate",
        "collect_rate",
        "weighted_engagement_per_view",
        "deep_demand_ratio",
        "note_quote",
        "video_cpe_calc",
        "video_cpm_calc",
        "quote_video",
        "quote_post",
        "post_cpe_calc",
        "post_cpm_calc",
        "commercial_traffic_drop_pct",
        "is_commercial",
        "view",
    ]
    df = safe_as_numeric(df, [c for c in required if c not in ["high_or_low"]])

    df["high_or_low"] = df.get("high_or_low", "").astype(str)

    desc_cols = [
        "anxiety_score",
        "ces_total",
        "ces_per_1000_view",
        "interaction_rate",
        "collect_rate",
        "note_quote",
        "video_cpe_calc",
        "video_cpm_calc",
        "commercial_traffic_drop_pct",
    ]
    desc = build_desc_table(df, desc_cols)

    sns.set_theme(style="whitegrid", font="Arial")

    anxiety_order = [0, 1, 3, 5]
    if "anxiety_score" in df.columns:
        observed = sorted([x for x in df["anxiety_score"].dropna().unique().tolist() if float(x).is_integer()])
        observed = [int(x) for x in observed]
        anxiety_order = [x for x in anxiety_order if x in observed] + [x for x in observed if x not in anxiety_order]
        df["anxiety_score_cat"] = pd.Categorical(df["anxiety_score"].astype("Int64"), categories=anxiety_order, ordered=True)
    else:
        df["anxiety_score_cat"] = pd.Categorical([], categories=anxiety_order, ordered=True)

    g1 = (
        df.groupby(["high_or_low", "anxiety_score_cat"], dropna=False)[
            ["ces_per_1000_view", "collect_rate", "weighted_engagement_per_view"]
        ]
        .mean(numeric_only=True)
        .reset_index()
    )

    plt.figure(figsize=(14, 4))
    for i, y in enumerate(["ces_per_1000_view", "collect_rate", "weighted_engagement_per_view"], start=1):
        ax = plt.subplot(1, 3, i)
        sns.lineplot(
            data=g1,
            x="anxiety_score_cat",
            y=y,
            hue="high_or_low",
            marker="o",
            ax=ax,
        )
        ax.set_xlabel("anxiety_score")
        ax.set_ylabel(y)
        ax.legend(title="high_or_low")
    save_fig(os.path.join(fig_dir, "module1_anxiety_to_traffic_lines.png"))

    plt.figure(figsize=(12, 4))
    ax1 = plt.subplot(1, 2, 1)
    sns.boxplot(data=df, x="anxiety_score_cat", y="interaction_rate", ax=ax1)
    ax1.set_xlabel("anxiety_score")
    ax1.set_ylabel("interaction_rate")
    ax2 = plt.subplot(1, 2, 2)
    sns.boxplot(data=df, x="anxiety_score_cat", y="deep_demand_ratio", ax=ax2)
    ax2.set_xlabel("anxiety_score")
    ax2.set_ylabel("deep_demand_ratio")
    save_fig(os.path.join(fig_dir, "module1_anxiety_boxplots.png"))

    plt.figure(figsize=(15, 4))
    for i, y in enumerate(["note_quote", "video_cpe_calc", "video_cpm_calc"], start=1):
        ax = plt.subplot(1, 3, i)
        sns.regplot(
            data=df,
            x="anxiety_score",
            y=y,
            scatter_kws={"s": 18, "alpha": 0.5},
            line_kws={"color": "red"},
            ax=ax,
        )
        ax.set_xlabel("anxiety_score")
        ax.set_ylabel(y)
    save_fig(os.path.join(fig_dir, "module2_anxiety_to_monetization_scatter_reg.png"))

    g4 = df.groupby("high_or_low")[["note_quote", "ad_value_per_1000_view"]].mean(numeric_only=True).reset_index()
    g4m = g4.melt(id_vars=["high_or_low"], var_name="metric", value_name="value")
    plt.figure(figsize=(8, 4))
    ax = sns.barplot(data=g4m, x="high_or_low", y="value", hue="metric")
    ax.set_xlabel("high_or_low")
    ax.set_ylabel("mean value")
    save_fig(os.path.join(fig_dir, "module2_highlow_bar.png"))

    g5 = (
        df.groupby(["high_or_low", "is_commercial"])[["view", "ces_per_1000_view"]]
        .mean(numeric_only=True)
        .reset_index()
    )
    plt.figure(figsize=(12, 4))
    ax1 = plt.subplot(1, 2, 1)
    sns.barplot(data=g5, x="is_commercial", y="view", hue="high_or_low", ax=ax1)
    ax1.set_xlabel("is_commercial (0/1)")
    ax1.set_ylabel("mean view")
    ax2 = plt.subplot(1, 2, 2)
    sns.barplot(data=g5, x="is_commercial", y="ces_per_1000_view", hue="high_or_low", ax=ax2)
    ax2.set_xlabel("is_commercial (0/1)")
    ax2.set_ylabel("mean ces_per_1000_view")
    save_fig(os.path.join(fig_dir, "module3_commercial_vs_noncommercial.png"))

    g6 = df[["quote_video", "quote_post", "video_cpe_calc", "post_cpe_calc", "video_cpm_calc", "post_cpm_calc"]].mean(
        numeric_only=True
    )
    g6 = g6.reset_index()
    g6.columns = ["metric", "value"]
    plt.figure(figsize=(12, 4))
    ax = sns.barplot(data=g6, x="metric", y="value")
    ax.set_xlabel("")
    ax.set_ylabel("mean")
    plt.xticks(rotation=30, ha="right")
    save_fig(os.path.join(fig_dir, "module4_video_vs_post.png"))

    numeric_df = df.select_dtypes(include=["number"]).copy()
    corr = numeric_df.corr(numeric_only=True)
    plt.figure(figsize=(14, 12))
    ax = sns.heatmap(corr, cmap="RdBu_r", center=0, linewidths=0.3)
    ax.set_title("Correlation Heatmap (numeric variables)")
    save_fig(os.path.join(fig_dir, "module5_correlation_heatmap.png"))

    md_path = os.path.join(out_dir, "output_stage1.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# 第一阶段：描述性统计 + 可视化\n\n")
        f.write("## 1. 基础描述性统计（Table 1）\n\n")
        f.write("统计口径：mean / std / min / max，同时附带 n、0 值计数、负值计数用于排查异常。\n\n")
        f.write("| variable | mean | std | min | max | n | n_zero | n_negative |\n")
        f.write("|---|---:|---:|---:|---:|---:|---:|---:|\n")
        for _, row in desc.iterrows():
            f.write(
                "| "
                + str(row["variable"])
                + " | "
                + fmt_float(row["mean"])
                + " | "
                + fmt_float(row["std"])
                + " | "
                + fmt_float(row["min"])
                + " | "
                + fmt_float(row["max"])
                + " | "
                + str(int(row["n"]))
                + " | "
                + str(int(row["n_zero"]))
                + " | "
                + str(int(row["n_negative"]))
                + " |\n"
            )

        f.write("\n## 2. 分模块可视化\n\n")
        f.write("### 模块 1：焦虑情绪 → 流量效果\n\n")
        f.write("![module1_anxiety_to_traffic_lines](figs/module1_anxiety_to_traffic_lines.png)\n\n")
        f.write("![module1_anxiety_boxplots](figs/module1_anxiety_boxplots.png)\n\n")

        f.write("### 模块 2：焦虑情绪 → 商业变现\n\n")
        f.write("![module2_anxiety_to_monetization_scatter_reg](figs/module2_anxiety_to_monetization_scatter_reg.png)\n\n")
        f.write("![module2_highlow_bar](figs/module2_highlow_bar.png)\n\n")

        f.write("### 模块 3：商业笔记 VS 非商业笔记（流量折损）\n\n")
        f.write("![module3_commercial_vs_noncommercial](figs/module3_commercial_vs_noncommercial.png)\n\n")

        f.write("### 模块 4：视频 VS 图文 变现性价比\n\n")
        f.write("![module4_video_vs_post](figs/module4_video_vs_post.png)\n\n")

        f.write("### 模块 5：相关性热力图\n\n")
        f.write("![module5_correlation_heatmap](figs/module5_correlation_heatmap.png)\n")

    print(f"Saved markdown: {md_path}")


if __name__ == "__main__":
    main()

