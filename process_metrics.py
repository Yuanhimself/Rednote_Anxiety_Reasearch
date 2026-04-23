import os
import pandas as pd
import numpy as np


def safe_div(numerator, denominator):
    numerator = np.asarray(numerator, dtype="float64")
    denominator = np.asarray(denominator, dtype="float64")
    out = np.zeros_like(numerator, dtype="float64")
    np.divide(numerator, denominator, out=out, where=denominator != 0)
    return out


def main():
    input_path = r"d:\investment\DMS\DMS001_processed.csv"
    if not os.path.exists(input_path):
        raise FileNotFoundError(input_path)

    df = pd.read_csv(input_path)

    required_cols = [
        "koc_id",
        "view",
        "like",
        "collect",
        "comments",
        "share",
        "is_commercial",
        "quote_video",
        "quote_post",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    for col in ["view", "like", "collect", "comments", "share", "is_commercial"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype("int64")

    for col in ["quote_video", "quote_post"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).astype("float64")

    total_engagement = df["like"] + df["collect"] + df["comments"] + df["share"]
    ces_total = df["like"] + df["collect"] + df["comments"] * 4 + df["share"] * 4

    df["ces_total"] = ces_total.astype("int64")
    df["ces_per_1000_view"] = (safe_div(ces_total, df["view"]) * 1000).round(6)
    df["weighted_engagement_per_view"] = safe_div(ces_total, df["view"]).round(8)
    df["high_weight_engagement_ratio"] = safe_div(df["comments"] + df["share"], total_engagement).round(8)

    df["like_rate"] = safe_div(df["like"], df["view"]).round(8)
    df["collect_rate"] = safe_div(df["collect"], df["view"]).round(8)
    df["comment_rate"] = safe_div(df["comments"], df["view"]).round(8)
    df["share_rate"] = safe_div(df["share"], df["view"]).round(8)
    df["interaction_rate"] = safe_div(total_engagement, df["view"]).round(8)
    df["deep_demand_ratio"] = safe_div(df["collect"] + df["comments"], total_engagement).round(8)

    note_quote = np.where(df["quote_video"] != 0.0, df["quote_video"], df["quote_post"])
    df["note_quote"] = note_quote.round(2)
    df["ces_unit_price"] = safe_div(note_quote, ces_total).round(8)
    df["ad_value_per_1000_view"] = (safe_div(note_quote, df["view"]) * 1000).round(6)

    avg_view_by_koc = df.groupby("koc_id")["view"].transform("mean")
    avg_engagement_by_koc = total_engagement.groupby(df["koc_id"]).transform("mean").astype("float64")

    df["video_cpe_calc"] = safe_div(df["quote_video"], avg_engagement_by_koc).round(8)
    df["video_cpm_calc"] = (safe_div(df["quote_video"], avg_view_by_koc) * 1000).round(6)
    df["post_cpe_calc"] = safe_div(df["quote_post"], avg_engagement_by_koc).round(8)
    df["post_cpm_calc"] = (safe_div(df["quote_post"], avg_view_by_koc) * 1000).round(6)

    noncommercial_mean_map = df[df["is_commercial"] == 0].groupby("koc_id")["view"].mean()
    commercial_mean_map = df[df["is_commercial"] == 1].groupby("koc_id")["view"].mean()
    noncommercial_mean = df["koc_id"].map(noncommercial_mean_map).fillna(0.0).to_numpy(dtype="float64")
    commercial_mean = df["koc_id"].map(commercial_mean_map).fillna(0.0).to_numpy(dtype="float64")
    df["commercial_traffic_drop_pct"] = (safe_div(noncommercial_mean - commercial_mean, noncommercial_mean) * 100).round(4)

    output_path = r"d:\investment\DMS\DMS001_enriched.csv"
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()

