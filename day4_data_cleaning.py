"""
===========================================================
 Crypto Adoption vs. Currency Collapse — Day 4 Cleaning
===========================================================
Fixes:
  1. Venezuela FX nulls — interpolate from inflation proxy
  2. Iran FX zeros — replace with NaN, interpolate
  3. Chainalysis gaps — forward/back fill within country
  4. Outlier flagging — Venezuela hyperinflation kept but flagged
  5. Final clean table saved → data/clean_analysis_dataset.csv

Run:
  python day4_data_cleaning.py
===========================================================
"""

import pandas as pd
import numpy as np

# ── Load ───────────────────────────────────────────────────

df = pd.read_csv("data/unified_country_dataset.csv")
print("=" * 55)
print(" Crypto Collapse — Day 4: Data Cleaning")
print("=" * 55)
print(f"\n  Input: {df.shape[0]} rows × {df.shape[1]} columns")

# ── 1. Fix Iran FX zeros ───────────────────────────────────

print("\n[1] Fixing Iran FX zeros...")
# Iran's 0.0 values are data artifacts, not real — replace with NaN
iran_mask = (df["iso3"] == "IRN") & (df["fx_depreciation_pct"] == 0.0)
df.loc[iran_mask, "fx_depreciation_pct"] = np.nan
df.loc[df["iso3"] == "IRN", "fx_lcu_per_usd"] = np.nan
print(f"  ✓ Replaced {iran_mask.sum()} Iran FX zeros with NaN")

# ── 2. Fix Venezuela FX nulls ─────────────────────────────

print("\n[2] Fixing Venezuela FX nulls...")
# Venezuela stopped reporting official FX to World Bank
# We estimate depreciation from inflation as a proxy
# (high inflation → currency depreciation, rough but valid for analysis)
ven_mask = df["iso3"] == "VEN"
df.loc[ven_mask, "fx_depreciation_pct"] = (
    df.loc[ven_mask, "inflation_pct"]
    .apply(lambda x: min(x * 0.85, 99.9) if pd.notna(x) else np.nan)
)
print(f"  ✓ Venezuela FX estimated from inflation proxy")
print(f"    (methodology note: inflation × 0.85 coefficient)")

# ── 3. Interpolate remaining FX nulls ─────────────────────

print("\n[3] Interpolating remaining FX nulls...")
before = df["fx_depreciation_pct"].isnull().sum()
df["fx_depreciation_pct"] = (
    df.groupby("iso3")["fx_depreciation_pct"]
    .transform(lambda x: x.interpolate(method="linear", limit_direction="both"))
)
after = df["fx_depreciation_pct"].isnull().sum()
print(f"  ✓ Nulls reduced: {before} → {after}")

# ── 4. Fill Chainalysis gaps ───────────────────────────────

print("\n[4] Filling Chainalysis gaps...")
before = df["chainalysis_rank"].isnull().sum()
# Forward fill then back fill within each country
df["chainalysis_rank"] = (
    df.groupby("iso3")["chainalysis_rank"]
    .transform(lambda x: x.ffill().bfill())
)
df["chainalysis_score"] = (
    df.groupby("iso3")["chainalysis_score"]
    .transform(lambda x: x.ffill().bfill())
)
after = df["chainalysis_rank"].isnull().sum()
print(f"  ✓ Chainalysis nulls reduced: {before} → {after}")
print(f"  ℹ  Iran remains null (not in Chainalysis index)")

# ── 5. Add outlier flag ────────────────────────────────────

print("\n[5] Adding outlier flags...")
df["is_hyperinflation"] = df["inflation_pct"] > 1000
df["is_fx_crisis"]      = df["fx_depreciation_pct"] > 100
flagged = df[df["is_hyperinflation"] | df["is_fx_crisis"]][
    ["country", "year", "inflation_pct", "fx_depreciation_pct"]
]
print(f"  ✓ Flagged {len(flagged)} crisis rows:")
print(flagged.to_string(index=False))

# ── 6. Add crypto stress index ────────────────────────────

print("\n[6] Building crypto stress index...")
# Normalize trends (0-1 scale per country)
for col in ["trends_bitcoin", "trends_USDT", "trends_crypto"]:
    df[f"{col}_norm"] = (
        df.groupby("iso3")[col]
        .transform(lambda x: (x - x.min()) / (x.max() - x.min() + 1e-9))
    )

# Composite crypto demand score
df["crypto_demand_score"] = (
    df["trends_bitcoin_norm"] * 0.4 +
    df["trends_USDT_norm"]    * 0.4 +
    df["trends_crypto_norm"]  * 0.2
)
print(f"  ✓ crypto_demand_score created (0-1 scale)")

# ── 7. Add currency stress index ──────────────────────────

print("\n[7] Building currency stress index...")
# Normalize inflation and FX depreciation
df["inflation_norm"] = (
    df.groupby("iso3")["inflation_pct"]
    .transform(lambda x: (x - x.min()) / (x.max() - x.min() + 1e-9))
)
df["fx_norm"] = (
    df.groupby("iso3")["fx_depreciation_pct"]
    .transform(lambda x: (x - x.min()) / (x.max() - x.min() + 1e-9))
)

df["currency_stress_score"] = (
    df["inflation_norm"] * 0.5 +
    df["fx_norm"]        * 0.5
)
print(f"  ✓ currency_stress_score created (0-1 scale)")

# ── 8. Save clean dataset ─────────────────────────────────

output_path = "data/clean_analysis_dataset.csv"
df.to_csv(output_path, index=False)

print(f"\n{'='*55}")
print(f"  ✓ Clean dataset: {df.shape[0]} rows × {df.shape[1]} columns")
print(f"  ✓ Saved → {output_path}")
print(f"{'='*55}")

# ── 9. Final null check ───────────────────────────────────

print("\n  Final null counts:")
key_cols = ["inflation_pct", "fx_depreciation_pct",
            "chainalysis_rank", "crypto_demand_score",
            "currency_stress_score"]
for col in key_cols:
    n = df[col].isnull().sum()
    flag = " ⚠️" if n > 0 else " ✓"
    print(f"    {col:<30} {n} nulls{flag}")

print("\nDay 4 complete!")
print("Ready for Day 5 — correlation & lag analysis!\n")