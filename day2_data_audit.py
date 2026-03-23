"""
===========================================================
 Crypto Adoption vs. Currency Collapse — Day 2 Data Audit
===========================================================
Checks the unified dataset for:
  - Null/missing values
  - Country coverage gaps
  - Year range completeness
  - Outliers in key numeric columns
  - Venezuela & Iran special checks

Run:
  python day2_data_audit.py
===========================================================
"""

import pandas as pd
import numpy as np

# ── Load ───────────────────────────────────────────────────────────────────────

df = pd.read_csv("data/unified_country_dataset.csv")

print("=" * 55)
print(" Crypto Adoption vs. Currency Collapse — Day 2 Audit")
print("=" * 55)

# ── 1. Basic shape ─────────────────────────────────────────────────────────────

print(f"\n[1] Dataset shape: {df.shape[0]} rows × {df.shape[1]} columns")
print(f"    Countries : {sorted(df['country'].unique())}")
print(f"    Years     : {sorted(df['year'].unique())}")

# ── 2. Null counts ─────────────────────────────────────────────────────────────

print("\n[2] Null counts per column:")
nulls = df.isnull().sum()
for col, count in nulls.items():
    pct = count / len(df) * 100
    flag = " ⚠️ " if pct > 30 else ""
    print(f"    {col:<35} {count:>3} nulls ({pct:.0f}%){flag}")

# ── 3. Coverage per country ────────────────────────────────────────────────────

print("\n[3] Row coverage per country:")
for country, grp in df.groupby("country"):
    years = sorted(grp["year"].tolist())
    nulls_inf = grp["inflation_pct"].isnull().sum()
    nulls_fx  = grp["fx_depreciation_pct"].isnull().sum()
    print(f"    {country:<15} years={years}  "
          f"inflation_nulls={nulls_inf}  fx_nulls={nulls_fx}")

# ── 4. Venezuela & Iran special check ─────────────────────────────────────────

print("\n[4] Venezuela & Iran spot check:")
for iso3, name in [("VEN", "Venezuela"), ("IRN", "Iran")]:
    sub = df[df["iso3"] == iso3]
    if sub.empty:
        print(f"    ⚠️  {name} — NO ROWS FOUND. May need manual data.")
    else:
        print(f"    {name}:")
        print(sub[["year", "inflation_pct", "fx_depreciation_pct",
                   "chainalysis_rank"]].to_string(index=False))

# ── 5. Outlier check ───────────────────────────────────────────────────────────

print("\n[5] Outlier check (values beyond 3 std devs):")
numeric_cols = ["inflation_pct", "fx_depreciation_pct",
                "gdp_per_capita_usd", "trends_bitcoin"]
for col in numeric_cols:
    if col not in df.columns:
        continue
    mean = df[col].mean()
    std  = df[col].std()
    outliers = df[np.abs(df[col] - mean) > 3 * std]
    if not outliers.empty:
        print(f"    ⚠️  {col}: {len(outliers)} outlier(s)")
        print(outliers[["country", "year", col]].to_string(index=False))
    else:
        print(f"    ✓  {col}: no outliers")

# ── 6. Summary & recommendations ──────────────────────────────────────────────

print("\n[6] Summary:")
total_nulls = df.isnull().sum().sum()
print(f"    Total nulls in dataset : {total_nulls}")
print(f"    Rows with any null     : {df.isnull().any(axis=1).sum()}")
print(f"    Complete rows          : {df.dropna().shape[0]}")

print("\n[7] Recommendations:")
if df[df["iso3"] == "IRN"].empty:
    print("    ⚠️  Iran missing — expected, drop or flag in analysis")
if df[df["iso3"] == "VEN"]["fx_depreciation_pct"].isnull().all():
    print("    ⚠️  Venezuela FX nulls — consider DolarToday historical data")
if df["chainalysis_rank"].isnull().sum() > 0:
    print("    ⚠️  Chainalysis gaps — verify PDF and update manual entries")

print("\nDay 2 audit complete!")
print("Review the ⚠️  flags above before moving to Day 3.\n")
