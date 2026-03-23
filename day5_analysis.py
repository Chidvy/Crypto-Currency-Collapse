import pandas as pd
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings("ignore")

df = pd.read_csv("data/clean_analysis_dataset.csv")
df_trends = pd.read_csv("data/raw/google_trends.csv")

print("=" * 55)
print(" Crypto Collapse — Day 5: Analysis")
print("=" * 55)

df_clean = df[df["iso3"] != "IRN"].copy()

print("\n[1] CORRELATION ANALYSIS")
print("-" * 40)
pairs = [
    ("inflation_pct",         "crypto_demand_score",  "Inflation vs Crypto Demand"),
    ("fx_depreciation_pct",   "crypto_demand_score",  "FX Depreciation vs Crypto Demand"),
    ("currency_stress_score", "crypto_demand_score",  "Currency Stress vs Crypto Demand"),
]
for x_col, y_col, label in pairs:
    sub = df_clean[[x_col, y_col]].dropna()
    if len(sub) < 3:
        continue
    r, p = stats.pearsonr(sub[x_col], sub[y_col])
    sig = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""
    print(f"  {label}")
    print(f"    r = {r:+.3f}  p = {p:.3f}  n = {len(sub)}  {sig}")

print("\n[2] PER-COUNTRY CORRELATION (Inflation vs Crypto Demand)")
print("-" * 40)
for country, grp in df_clean.groupby("country"):
    sub = grp[["inflation_pct", "crypto_demand_score"]].dropna()
    if len(sub) < 3:
        print(f"  {country:<15} insufficient data")
        continue
    r, p = stats.pearsonr(sub["inflation_pct"], sub["crypto_demand_score"])
    direction = "↑ crypto rises with inflation" if r > 0 else "↓ crypto falls with inflation"
    print(f"  {country:<15} r={r:+.3f}  p={p:.3f}  {direction}")

print("\n[3] LAG ANALYSIS — Does crypto search LEAD inflation?")
print("-" * 40)

df_trends["date"] = pd.to_datetime(df_trends["date"])
df_trends["year_month"] = df_trends["date"].dt.to_period("M")
df_clean["date"] = pd.to_datetime(df_clean["year"].astype(str) + "-06-01")

lag_results = []

countries_to_test = ["Argentina", "Turkey", "Nigeria", "Egypt",
                     "Venezuela", "United States", "India"]

for country in countries_to_test:
    match = df_clean[df_clean["country"] == country]
    if match.empty:
        continue
    iso3 = match["iso3"].iloc[0]

    trends_country = (
        df_trends[df_trends["iso3"] == iso3]
        .groupby("year_month")["search_index"]
        .mean()
        .reset_index()
    )
    trends_country["date"] = trends_country["year_month"].dt.to_timestamp()
    trends_country = trends_country.sort_values("date").reset_index(drop=True)

    if trends_country.empty or trends_country["date"].isna().all():
        print(f"  {country:<15} no trends data (rate limited)")
        continue

    inf_annual = df_clean[df_clean["country"] == country][["date", "inflation_pct"]].copy()
    inf_annual = inf_annual.sort_values("date")

    date_range = pd.date_range(
        start=trends_country["date"].min(),
        end=trends_country["date"].max(),
        freq="MS"
    )
    inf_monthly = pd.DataFrame({"date": date_range})
    inf_monthly = inf_monthly.merge(inf_annual, on="date", how="left")
    inf_monthly["inflation_pct"] = inf_monthly["inflation_pct"].interpolate(
        method="linear", limit_direction="both"
    )

    merged = trends_country.merge(inf_monthly, on="date", how="inner")
    if len(merged) < 12:
        print(f"  {country:<15} insufficient monthly data")
        continue

    def normalize(x):
        return (x - x.mean()) / (x.std() + 1e-9)

    trends_norm = normalize(merged["search_index"].values)
    inflat_norm = normalize(merged["inflation_pct"].values)

    max_lag = min(6, len(trends_norm) // 3)
    best_r, best_lag = -999, 0

    for lag in range(-max_lag, max_lag + 1):
        if lag > 0:
            r, _ = stats.pearsonr(trends_norm[:-lag], inflat_norm[lag:])
        elif lag < 0:
            r, _ = stats.pearsonr(trends_norm[-lag:], inflat_norm[:lag])
        else:
            r, _ = stats.pearsonr(trends_norm, inflat_norm)
        if r > best_r:
            best_r = r
            best_lag = lag

    direction = (
        f"crypto LEADS inflation by {best_lag} months" if best_lag > 0
        else f"crypto LAGS inflation by {abs(best_lag)} months" if best_lag < 0
        else "simultaneous"
    )
    lag_results.append((country, best_lag, best_r))
    print(f"  {country:<15} lag={best_lag:+d} months  r={best_r:+.3f}  → {direction}")

print("\n[4] HEADLINE FINDING")
print("-" * 40)
leads = [(c, l, r) for c, l, r in lag_results if l > 0]
if leads:
    avg_lag = np.mean([l for _, l, _ in leads])
    avg_r   = np.mean([r for _, _, r in leads])
    print(f"""
  ✓ In {len(leads)} of {len(lag_results)} countries:
    Crypto search LEADS official inflation data

  Average lead time  : {avg_lag:.1f} months ({avg_lag*30:.0f} days)
  Average correlation: {avg_r:.3f}
  Countries          : {', '.join([c for c, _, _ in leads])}

  PORTFOLIO HEADLINE:
  "Crypto search volume leads official currency
   stress by ~{avg_lag*30:.0f} days across {len(leads)} countries
   with {avg_r*100:.0f}% average correlation"
    """)

results_df = pd.DataFrame(lag_results, columns=["country", "lag_months", "correlation"])
results_df.to_csv("data/lag_analysis_results.csv", index=False)
print(f"  ✓ Saved → data/lag_analysis_results.csv")
print("\nDay 5 complete!\n")