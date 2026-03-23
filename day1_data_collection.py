"""
===========================================================
 Crypto Adoption vs. Currency Collapse — Day 1 Data Collection
===========================================================
Sources:
  - IMF World Economic Outlook (inflation by country)
  - World Bank (currency depreciation, GDP per capita)
  - CoinMetrics Community API (on-chain BTC/USDT volumes)
  - pytrends — Google Trends search volume
  - Chainalysis index: manual entry (PDF, no public API)

Output:
  - data/raw/imf_inflation.csv
  - data/raw/worldbank_fx_gdp.csv
  - data/raw/coinmetrics_onchain.csv
  - data/raw/google_trends.csv
  - data/raw/chainalysis_manual.csv
  - data/unified_country_dataset.csv   ← master file for Phase 2

Run:
  pip install requests pandas pytrends wbgapi tqdm
  python day1_data_collection.py
===========================================================
"""

import os
import time
import requests
import pandas as pd
from datetime import datetime
from pytrends.request import TrendReq
import wbgapi as wb
from tqdm import tqdm

# ── Config ─────────────────────────────────────────────────────────────────────

FOCUS_COUNTRIES = {
    "ARG": {"name": "Argentina", "iso2": "AR"},
    "TUR": {"name": "Turkey",    "iso2": "TR"},
    "IRN": {"name": "Iran",      "iso2": "IR"},
    "EGY": {"name": "Egypt",     "iso2": "EG"},
    "VEN": {"name": "Venezuela", "iso2": "VE"},
    "NGA": {"name": "Nigeria",   "iso2": "NG"},
    "USA": {"name": "United States", "iso2": "US"},
    "IND": {"name": "India",     "iso2": "IN"},
}

START_YEAR   = 2019
END_YEAR     = 2024
TRENDS_START = "2019-01-01"
TRENDS_END   = "2024-12-31"

os.makedirs("data/raw", exist_ok=True)

# ── 1. IMF — Inflation (CPI % change) ─────────────────────────────────────────

def fetch_imf_inflation():
    print("\n[1/4] Fetching IMF inflation data...")
    base = "https://www.imf.org/external/datamapper/api/v1/PCPIPCH"
    iso3_list = list(FOCUS_COUNTRIES.keys())
    rows = []

    for iso3 in tqdm(iso3_list):
        url = f"{base}/{iso3}"
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            data = r.json()
            values = data.get("values", {}).get("PCPIPCH", {}).get(iso3, {})
            for year, val in values.items():
                if START_YEAR <= int(year) <= END_YEAR:
                    rows.append({
                        "iso3": iso3,
                        "country": FOCUS_COUNTRIES[iso3]["name"],
                        "year": int(year),
                        "inflation_pct": val,
                    })
        except Exception as e:
            print(f"  ✗ IMF error for {iso3}: {e}")
        time.sleep(0.5)

    df = pd.DataFrame(rows)
    df.to_csv("data/raw/imf_inflation.csv", index=False)
    print(f"  ✓ Saved {len(df)} rows → data/raw/imf_inflation.csv")
    return df


# ── 2. World Bank — Currency Depreciation + GDP per capita ────────────────────

def fetch_worldbank():
    print("\n[2/4] Fetching World Bank FX + GDP data...")
    indicators = {
        "PA.NUS.FCRF":    "fx_lcu_per_usd",
        "NY.GDP.PCAP.CD": "gdp_per_capita_usd",
    }
    iso3_list = list(FOCUS_COUNTRIES.keys())
    years     = range(START_YEAR, END_YEAR + 1)
    frames    = []

    for ind_code, col_name in indicators.items():
        try:
            raw = wb.data.DataFrame(
                ind_code,
                economy=iso3_list,
                time=years,
                labels=False,
            )
            raw = raw.reset_index()
            raw = raw.melt(id_vars=["economy"], var_name="year", value_name=col_name)
            raw["year"] = raw["year"].astype(str).str.extract(r"(\d{4})").astype(int)
            raw.rename(columns={"economy": "iso3"}, inplace=True)
            frames.append(raw.set_index(["iso3", "year"]))
        except Exception as e:
            print(f"  ✗ World Bank error ({ind_code}): {e}")

    if frames:
        df = pd.concat(frames, axis=1).reset_index()
        df["country"] = df["iso3"].map({k: v["name"] for k, v in FOCUS_COUNTRIES.items()})
        df = df.sort_values(["iso3", "year"])
        df["fx_depreciation_pct"] = (
            df.groupby("iso3")["fx_lcu_per_usd"]
            .pct_change() * 100
        )
        df.to_csv("data/raw/worldbank_fx_gdp.csv", index=False)
        print(f"  ✓ Saved {len(df)} rows → data/raw/worldbank_fx_gdp.csv")
    else:
        df = pd.DataFrame()
        print("  ✗ No World Bank data retrieved.")

    return df


# ── 3. CoinMetrics Community API — On-chain BTC volume ────────────────────────

def fetch_coinmetrics():
    print("\n[3/4] Fetching BTC + ETH price & volume via yfinance...")
    import yfinance as yf
    rows = []
    tickers = {"BTC-USD": "btc", "ETH-USD": "eth"}

    for ticker, asset in tickers.items():
        try:
            df = yf.download(ticker, start=f"{START_YEAR}-01-01",
                             end=f"{END_YEAR}-12-31", auto_adjust=True, progress=False)
            df = df.reset_index()
            df["asset"]        = asset
            df["date"]         = df["Date"].dt.date
            df["tx_volume_usd"] = df["Volume"] * df["Close"]
            df["price_usd"]    = df["Close"]
            df = df[["asset", "date", "price_usd", "tx_volume_usd"]]
            rows.append(df)
            print(f"  ✓ {asset.upper()}: {len(df)} rows")
        except Exception as e:
            print(f"  ✗ yfinance error ({ticker}): {e}")

    if rows:
        df_all = pd.concat(rows, ignore_index=True)
        df_all.to_csv("data/raw/coinmetrics_onchain.csv", index=False)
        print(f"  ✓ Saved → data/raw/coinmetrics_onchain.csv")
    else:
        df_all = pd.DataFrame()

    return df_all
    print("\n[3/4] Fetching CoinMetrics on-chain volume (BTC)...")
    url = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
    params = {
        "assets":     "btc,usdt",
        "metrics":    "TxTfrValAdjUSD,TxCnt",
        "frequency":  "1d",
        "start_time": f"{START_YEAR}-01-01",
        "end_time":   f"{END_YEAR}-12-31",
        "page_size":  10000,
    }
    rows = []

    try:
        while True:
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            rows.extend(data.get("data", []))
            next_page = data.get("next_page_token")
            if not next_page:
                break
            params["next_page_token"] = next_page
            time.sleep(0.3)

        df = pd.DataFrame(rows)
        if not df.empty:
            df["date"] = pd.to_datetime(df["time"]).dt.date
            df = df[["asset", "date", "TxTfrValAdjUSD", "TxCnt"]]
            df.columns = ["asset", "date", "tx_volume_usd", "tx_count"]
            df.to_csv("data/raw/coinmetrics_onchain.csv", index=False)
            print(f"  ✓ Saved {len(df)} rows → data/raw/coinmetrics_onchain.csv")
    except Exception as e:
        print(f"  ✗ CoinMetrics error: {e}")
        df = pd.DataFrame()

    return df


# ── 4. Google Trends — Search volume by country ───────────────────────────────

def fetch_google_trends():
    print("\n[4/4] Fetching Google Trends data...")
    pytrends = TrendReq(hl="en-US", tz=0, timeout=(10, 25))
    keywords  = ["bitcoin", "USDT", "crypto", "dollar"]
    all_rows  = []

    for iso3, meta in tqdm(FOCUS_COUNTRIES.items()):
        geo = meta["iso2"]
        for kw in keywords:
            try:
                pytrends.build_payload(
                    [kw],
                    cat=0,
                    timeframe=f"{TRENDS_START} {TRENDS_END}",
                    geo=geo,
                    gprop="",
                )
                df_trend = pytrends.interest_over_time()
                if df_trend.empty:
                    continue
                df_trend = df_trend.reset_index()[["date", kw]]
                df_trend.columns = ["date", "search_index"]
                df_trend["keyword"] = kw
                df_trend["iso3"]    = iso3
                df_trend["country"] = meta["name"]
                all_rows.append(df_trend)
                time.sleep(2)
            except Exception as e:
                print(f"  ✗ Trends error ({iso3}, {kw}): {e}")
                time.sleep(5)

    if all_rows:
        df = pd.concat(all_rows, ignore_index=True)
        df.to_csv("data/raw/google_trends.csv", index=False)
        print(f"  ✓ Saved {len(df)} rows → data/raw/google_trends.csv")
    else:
        df = pd.DataFrame()

    return df


# ── 5. Chainalysis Index — Manual Entry ───────────────────────────────────────

def build_chainalysis_manual():
    print("\n[5/5] Building Chainalysis manual dataset...")

    CHAINALYSIS_DATA = [
    ("ARG", 2023, 15, 0.29),
    ("ARG", 2024, 15, 0.29),
    ("TUR", 2023, 11, 0.34),
    ("TUR", 2024, 11, 0.34),
    ("EGY", 2023, 44, 0.18),
    ("EGY", 2024, 44, 0.18),
    ("VEN", 2023, 13, 0.31),
    ("VEN", 2024, 13, 0.31),
    ("NGA", 2023,  2, 0.61),
    ("NGA", 2024,  2, 0.61),
    ("USA", 2023,  4, 0.55),
    ("USA", 2024,  4, 0.55),
    ("IND", 2023,  1, 0.68),
    ("IND", 2024,  1, 0.68),
]
    df = pd.DataFrame(
        CHAINALYSIS_DATA,
        columns=["iso3", "year", "chainalysis_rank", "chainalysis_score"],
    )
    df["country"] = df["iso3"].map({k: v["name"] for k, v in FOCUS_COUNTRIES.items()})
    df.to_csv("data/raw/chainalysis_manual.csv", index=False)
    print(f"  ✓ Saved {len(df)} rows → data/raw/chainalysis_manual.csv")
    print("  ⚠  Remember: verify/update these numbers from the Chainalysis PDF!")
    return df


# ── 6. Merge into unified dataset ─────────────────────────────────────────────

def build_unified(df_imf, df_wb, df_trends, df_chainalysis):
    print("\n[Merge] Building unified country dataset...")

    if not df_trends.empty:
        df_trends["year"] = pd.to_datetime(df_trends["date"]).dt.year
        trends_annual = (
            df_trends
            .groupby(["iso3", "year", "keyword"])["search_index"]
            .mean()
            .unstack("keyword")
            .reset_index()
        )
        trends_annual.columns = (
            ["iso3", "year"]
            + [f"trends_{c}" for c in trends_annual.columns[2:]]
        )
    else:
        trends_annual = pd.DataFrame(columns=["iso3", "year"])

    base = df_imf.copy()
    if not df_wb.empty:
        wb_cols = ["iso3", "year", "fx_lcu_per_usd", "gdp_per_capita_usd", "fx_depreciation_pct"]
        base = base.merge(df_wb[wb_cols], on=["iso3", "year"], how="left")

    if not trends_annual.empty:
        base = base.merge(trends_annual, on=["iso3", "year"], how="left")

    if not df_chainalysis.empty:
        base = base.merge(
            df_chainalysis[["iso3", "year", "chainalysis_rank", "chainalysis_score"]],
            on=["iso3", "year"],
            how="left",
        )

    base = base.sort_values(["iso3", "year"]).reset_index(drop=True)
    base.to_csv("data/unified_country_dataset.csv", index=False)

    print(f"\n{'='*55}")
    print(f"  ✓ Unified dataset: {len(base)} rows × {len(base.columns)} columns")
    print(f"  ✓ Saved → data/unified_country_dataset.csv")
    print(f"{'='*55}")
    print(f"\n  Columns: {list(base.columns)}\n")
    return base


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print(" Crypto Adoption vs. Currency Collapse — Day 1")
    print(f" Run at: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 55)

    df_imf         = fetch_imf_inflation()
    df_wb          = fetch_worldbank()
    df_coinmetrics = fetch_coinmetrics()
    df_trends      = fetch_google_trends()
    df_chainalysis = build_chainalysis_manual()

    df_unified = build_unified(df_imf, df_wb, df_trends, df_chainalysis)

    print("\nDay 1 complete. Files in data/")
    print("  data/raw/                 ← individual source CSVs")
    print("  data/unified_country_dataset.csv  ← master table for Phase 2")
    print("\nNext: Day 2 — validate completeness, check nulls,")
    print("      then load into PostgreSQL schema on Day 3.\n")