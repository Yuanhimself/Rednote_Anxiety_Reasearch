import os
import math
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from scipy import stats


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def safe_log(x):
    x = pd.to_numeric(x, errors="coerce")
    return np.where(x > 0, np.log(x), np.nan)


def safe_log1p(x):
    x = pd.to_numeric(x, errors="coerce")
    return np.where(x >= 0, np.log1p(x), np.nan)


def stars(p):
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.1:
        return "*"
    return ""


def fmt(x, digits=6):
    if x is None:
        return ""
    try:
        xf = float(x)
        if math.isnan(xf) or math.isinf(xf):
            return ""
        return f"{xf:.{digits}f}"
    except Exception:
        return str(x)

def winsorize_cols(df, cols, lower=0.01, upper=0.99):
    df = df.copy()
    for c in cols:
        if c not in df.columns:
            continue
        s = pd.to_numeric(df[c], errors="coerce")
        if s.notna().sum() == 0:
            continue
        q_low, q_high = s.quantile([lower, upper])
        df[c] = s.clip(q_low, q_high)
    return df


def build_design_matrix(d, numeric_cols, categorical_cols):
    parts = [pd.DataFrame({"const": np.ones(len(d), dtype="float64")}, index=d.index)]
    names = ["const"]

    if numeric_cols:
        xn = d[numeric_cols].astype("float64")
        parts.append(xn)
        names.extend(numeric_cols)

    for c in categorical_cols or []:
        dum = pd.get_dummies(d[c].astype(str), prefix=c, drop_first=True)
        if dum.shape[1] > 0:
            parts.append(dum.astype("float64"))
            names.extend(dum.columns.tolist())

    X = pd.concat(parts, axis=1)
    col_std = X.std(axis=0, ddof=0).to_numpy(dtype="float64")
    keep = np.asarray(X.columns == "const") | (col_std > 1e-12)
    X = X.loc[:, keep]
    names = [n for n, ok in zip(names, keep) if ok]
    return X.to_numpy(dtype="float64"), names


def fit_ols(df, y_col, x_numeric_cols, x_categorical_cols=None):
    x_categorical_cols = x_categorical_cols or []

    use_cols = [y_col] + x_numeric_cols + x_categorical_cols
    seen = set()
    use_cols = [c for c in use_cols if not (c in seen or seen.add(c))]
    d = df[use_cols].copy()

    d[y_col] = pd.to_numeric(d[y_col], errors="coerce")
    for c in x_numeric_cols:
        d[c] = pd.to_numeric(d[c], errors="coerce")

    d = d.dropna(subset=[y_col] + x_numeric_cols + x_categorical_cols)

    X, names = build_design_matrix(d, x_numeric_cols, x_categorical_cols)
    y = d[y_col].to_numpy(dtype="float64")

    keep = np.isfinite(y) & np.isfinite(X).all(axis=1)
    X = X[keep, :]
    y = y[keep]

    n = X.shape[0]
    k = X.shape[1]
    if n <= k:
        raise ValueError(f"Not enough observations (n={n}) for k={k}.")

    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta

    xtx = X.T @ X
    bread = np.linalg.pinv(xtx)
    df_resid = n - k
    xu = X * resid.reshape(-1, 1)
    meat = xu.T @ xu
    vcov = bread @ meat @ bread
    if df_resid > 0:
        vcov = vcov * (n / df_resid)
    se = np.sqrt(np.clip(np.diag(vcov), 0, np.inf))
    tval = np.divide(beta, se, out=np.full_like(beta, np.nan), where=se != 0)
    pval = 2 * (1 - stats.t.cdf(np.abs(tval), df=max(df_resid, 1)))
    tcrit = stats.t.ppf(0.975, df=max(df_resid, 1))
    ci_low = beta - tcrit * se
    ci_high = beta + tcrit * se

    y_mean = float(np.mean(y))
    sst = float(np.sum((y - y_mean) ** 2))
    ssr = float(np.sum(resid**2))
    r2 = np.nan if sst == 0 else 1 - ssr / sst

    out = pd.DataFrame(
        {
            "term": names,
            "coef": beta,
            "se": se,
            "t": tval,
            "p": pval,
            "ci_low_95": ci_low,
            "ci_high_95": ci_high,
        }
    )
    out["stars"] = out["p"].apply(stars)

    meta = {"n": n, "k": k, "df_resid": int(df_resid), "r2": r2}
    return out, meta, resid


def fit_ols_cluster(df, y_col, x_numeric_cols, cluster_col, x_categorical_cols=None):
    x_categorical_cols = x_categorical_cols or []

    use_cols = [y_col, cluster_col] + x_numeric_cols + x_categorical_cols
    seen = set()
    use_cols = [c for c in use_cols if not (c in seen or seen.add(c))]
    d = df[use_cols].copy()

    d[y_col] = pd.to_numeric(d[y_col], errors="coerce")
    for c in x_numeric_cols:
        d[c] = pd.to_numeric(d[c], errors="coerce")

    d = d.dropna(subset=[y_col] + x_numeric_cols + [cluster_col] + x_categorical_cols)

    X, names = build_design_matrix(d, x_numeric_cols, x_categorical_cols)
    y = d[y_col].to_numpy(dtype="float64")
    clusters = d[cluster_col].astype(str).to_numpy()

    keep = np.isfinite(y) & np.isfinite(X).all(axis=1)
    X = X[keep, :]
    y = y[keep]
    clusters = clusters[keep]

    n = X.shape[0]
    k = X.shape[1]
    if n <= k:
        raise ValueError(f"Not enough observations (n={n}) for k={k}.")

    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta

    xtx = X.T @ X
    bread = np.linalg.pinv(xtx)

    uniq = pd.unique(clusters)
    g = len(uniq)
    meat = np.zeros((k, k), dtype="float64")
    for key in uniq:
        idx = clusters == key
        Xg = X[idx, :]
        ug = resid[idx]
        xugu = Xg.T @ ug
        meat += np.outer(xugu, xugu)

    if g > 1:
        df_c = (g / (g - 1)) * ((n - 1) / (n - k))
    else:
        df_c = 1.0

    vcov = bread @ meat @ bread * df_c
    se = np.sqrt(np.clip(np.diag(vcov), 0, np.inf))
    df_t = max(g - 1, 1)
    tval = np.divide(beta, se, out=np.full_like(beta, np.nan), where=se != 0)
    pval = 2 * (1 - stats.t.cdf(np.abs(tval), df=df_t))
    tcrit = stats.t.ppf(0.975, df=df_t)
    ci_low = beta - tcrit * se
    ci_high = beta + tcrit * se

    y_mean = float(np.mean(y))
    sst = float(np.sum((y - y_mean) ** 2))
    ssr = float(np.sum(resid**2))
    r2 = np.nan if sst == 0 else 1 - ssr / sst

    out = pd.DataFrame(
        {
            "term": names,
            "coef": beta,
            "se": se,
            "t": tval,
            "p": pval,
            "ci_low_95": ci_low,
            "ci_high_95": ci_high,
        }
    )
    out["stars"] = out["p"].apply(stars)

    meta = {"n": n, "k": k, "df_resid": int(n - k), "clusters": g, "df_t": int(df_t), "r2": r2}
    return out, meta


def save_resid_hist(resid, out_path, title):
    plt.figure(figsize=(7, 4))
    sns.histplot(resid, bins=30, kde=True)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close()


def coef_plot(models, out_path, terms):
    rows = []
    for model_name, res in models.items():
        for t in terms:
            hit = res[res["term"] == t]
            if hit.empty:
                continue
            rows.append(
                {
                    "model": model_name,
                    "term": t,
                    "coef": float(hit["coef"].iloc[0]),
                    "ci_low": float(hit["ci_low_95"].iloc[0]),
                    "ci_high": float(hit["ci_high_95"].iloc[0]),
                }
            )
    p = pd.DataFrame(rows)
    if p.empty:
        return
    plt.figure(figsize=(12, max(4, 0.35 * len(p))))
    ax = plt.gca()
    y_pos = np.arange(len(p), dtype="float64")
    ax.hlines(y_pos, p["ci_low"], p["ci_high"], color="black", linewidth=1)
    ax.plot(p["coef"], y_pos, "o")
    ax.axvline(0, color="black", linewidth=1)
    ax.set_yticks(y_pos)
    ax.set_yticklabels((p["model"] + " | " + p["term"]).tolist())
    ax.set_xlabel("Coefficient (95% CI)")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close()


def main():
    input_path = r"d:\investment\DMS\DMS001_enriched.csv"
    if not os.path.exists(input_path):
        raise FileNotFoundError(input_path)

    out_dir = r"d:\investment\DMS\regression_output_ols"
    fig_dir = os.path.join(out_dir, "figs")
    ensure_dir(fig_dir)

    df = pd.read_csv(input_path)

    need = [
        "anxiety_score",
        "like",
        "collect",
        "comments",
        "share",
        "view",
        "note_quote",
        "is_commercial",
        "high_or_low",
    ]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    for c in ["anxiety_score", "like", "collect", "comments", "share", "view", "note_quote", "is_commercial"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["high_or_low"] = df["high_or_low"].astype(str)

    df_w = winsorize_cols(
        df,
        [
            "anxiety_score",
            "like",
            "collect",
            "comments",
            "share",
            "view",
            "note_quote",
        ],
        lower=0.01,
        upper=0.99,
    )

    df_w["anxiety_sq"] = df_w["anxiety_score"] ** 2

    df_w["ratio_collect"] = np.where(df_w["like"] > 0, df_w["collect"] / df_w["like"], np.nan)

    ces_total = df_w["like"] + df_w["collect"] + df_w["comments"] * 4 + df_w["share"] * 4
    df_w["ces_per_1000_view"] = np.where(df_w["view"] > 0, (ces_total / df_w["view"]) * 1000, 0.0)
    df_w["ln_ces_per_1000_view_plus1"] = safe_log1p(df_w["ces_per_1000_view"])

    df_w["ln_note_quote_plus1"] = safe_log1p(df_w["note_quote"])
    df_w["ln_view_plus1"] = safe_log1p(df_w["view"])

    sns.set_theme(style="whitegrid", font="Arial")

    models = {}
    metas = {}
    residuals = {}

    r1, m1, e1 = fit_ols(
        df_w,
        y_col="ratio_collect",
        x_numeric_cols=["anxiety_score", "anxiety_sq", "is_commercial"],
        x_categorical_cols=[],
    )
    models["Model1_CollectLikeRatio"] = r1
    metas["Model1_CollectLikeRatio"] = m1
    residuals["Model1_CollectLikeRatio"] = e1
    save_resid_hist(e1, os.path.join(fig_dir, "residuals_model1.png"), "Residuals: Model1 (winsorized 1%)")

    r2, m2, e2 = fit_ols(
        df_w,
        y_col="ln_ces_per_1000_view_plus1",
        x_numeric_cols=["anxiety_score", "anxiety_sq", "is_commercial"],
        x_categorical_cols=["high_or_low"],
    )
    models["Model2_lnCESper1000Plus1"] = r2
    metas["Model2_lnCESper1000Plus1"] = m2
    residuals["Model2_lnCESper1000Plus1"] = e2
    save_resid_hist(e2, os.path.join(fig_dir, "residuals_model2.png"), "Residuals: Model2 (winsorized 1%)")

    r3, m3, e3 = fit_ols(
        df_w,
        y_col="ln_note_quote_plus1",
        x_numeric_cols=["anxiety_score", "ln_view_plus1", "is_commercial"],
        x_categorical_cols=[],
    )
    models["Model3_lnNoteQuotePlus1"] = r3
    metas["Model3_lnNoteQuotePlus1"] = m3
    residuals["Model3_lnNoteQuotePlus1"] = e3
    save_resid_hist(e3, os.path.join(fig_dir, "residuals_model3.png"), "Residuals: Model3 (winsorized 1%)")

    coef_plot(
        models,
        os.path.join(fig_dir, "coef_key_terms.png"),
        ["anxiety_score", "anxiety_sq", "is_commercial", "high_or_low_low", "high_or_low_high", "ln_view_plus1"],
    )
    md_path = os.path.join(out_dir, "regression_results_ols.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# 回归结果（混合 OLS，多元线性回归，无博主固定效应）\n\n")
        f.write("数据来源：DMS001_enriched.csv\n\n")
        f.write("对数变换：ln(X+1)\n\n")
        f.write("标准误：怀特稳健标准误（White Robust / HC1）\n\n")
        f.write("![coef_key_terms](figs/coef_key_terms.png)\n\n")

        f.write("## 残差直方图\n\n")
        f.write("![resid_m1](figs/residuals_model1.png)\n\n")
        f.write("![resid_m2](figs/residuals_model2.png)\n\n")
        f.write("![resid_m3](figs/residuals_model3.png)\n\n")

        for name in ["Model1_CollectLikeRatio", "Model2_lnCESper1000Plus1", "Model3_lnNoteQuotePlus1"]:
            f.write(f"## {name}\n\n")
            meta = metas[name]
            f.write(f"- N = {meta['n']}, K = {meta['k']}, df_resid = {meta['df_resid']}, R2 = {fmt(meta['r2'], 6)}\n\n")
            f.write("| term | coef | se | t | p | 95% CI low | 95% CI high | |\n")
            f.write("|---|---:|---:|---:|---:|---:|---:|:--:|\n")
            rr = models[name].copy().sort_values("term")
            for _, row in rr.iterrows():
                f.write(
                    "| "
                    + str(row["term"])
                    + " | "
                    + fmt(row["coef"], 8)
                    + " | "
                    + fmt(row["se"], 8)
                    + " | "
                    + fmt(row["t"], 4)
                    + " | "
                    + fmt(row["p"], 6)
                    + " | "
                    + fmt(row["ci_low_95"], 8)
                    + " | "
                    + fmt(row["ci_high_95"], 8)
                    + " | "
                    + str(row["stars"])
                    + " |\n"
                )
            f.write("\n")

    print(f"Saved: {md_path}")

    if "koc_id" in df.columns:
        split_results = {}
        split_metas = {}
        for grp in ["low", "high"]:
            df_g = df_w[df["high_or_low"] == grp].copy()
            if df_g.empty:
                continue
            suffix = f"{grp}"

            r1g, m1g = fit_ols_cluster(
                df_g,
                y_col="ratio_collect",
                x_numeric_cols=["anxiety_score", "anxiety_sq", "is_commercial"],
                x_categorical_cols=None,
                cluster_col="koc_id",
            )
            split_results[f"Model1_CollectLikeRatio_{suffix}"] = r1g
            split_metas[f"Model1_CollectLikeRatio_{suffix}"] = m1g

            r2g, m2g = fit_ols_cluster(
                df_g,
                y_col="ln_ces_per_1000_view_plus1",
                x_numeric_cols=["anxiety_score", "anxiety_sq", "is_commercial"],
                x_categorical_cols=None,
                cluster_col="koc_id",
            )
            split_results[f"Model2_lnCESper1000Plus1_{suffix}"] = r2g
            split_metas[f"Model2_lnCESper1000Plus1_{suffix}"] = m2g

            r3g, m3g = fit_ols_cluster(
                df_g,
                y_col="ln_note_quote_plus1",
                x_numeric_cols=["anxiety_score", "ln_view_plus1", "is_commercial"],
                x_categorical_cols=None,
                cluster_col="koc_id",
            )
            split_results[f"Model3_lnNoteQuotePlus1_{suffix}"] = r3g
            split_metas[f"Model3_lnNoteQuotePlus1_{suffix}"] = m3g

        md_split = os.path.join(out_dir, "regression_results_ols_split_cluster.md")
        with open(md_split, "w", encoding="utf-8") as f:
            f.write("# 样本拆分 + 聚类稳健标准误（按 koc_id 聚类）\n\n")
            f.write("数据来源：DMS001_enriched.csv；样本按 high_or_low=low/high 拆分；对连续变量已做 1% 缩尾处理。\n\n")
            for name, res in split_results.items():
                meta = split_metas[name]
                f.write(f"## {name}\n\n")
                f.write(
                    f"- N = {meta['n']}, K = {meta['k']}, clusters = {meta['clusters']}, df_t = {meta['df_t']}, R2 = {fmt(meta['r2'], 6)}\n\n"
                )
                f.write("| term | coef | se(cluster) | t | p | 95% CI low | 95% CI high | |\n")
                f.write("|---|---:|---:|---:|---:|---:|---:|:--:|\n")
                rr = res.copy().sort_values("term")
                for _, row in rr.iterrows():
                    f.write(
                        "| "
                        + str(row["term"])
                        + " | "
                        + fmt(row["coef"], 8)
                        + " | "
                        + fmt(row["se"], 8)
                        + " | "
                        + fmt(row["t"], 4)
                        + " | "
                        + fmt(row["p"], 6)
                        + " | "
                        + fmt(row["ci_low_95"], 8)
                        + " | "
                        + fmt(row["ci_high_95"], 8)
                        + " | "
                        + str(row["stars"])
                        + " |\n"
                    )
                f.write("\n")

        print(f"Saved: {md_split}")



if __name__ == "__main__":
    main()

