"""
===========================================================
 Crypto Adoption vs. Currency Collapse — Day 3 DB Loader
===========================================================
Creates PostgreSQL database + tables, loads all CSVs.

Run:
  python day3_db_loader.py
===========================================================
"""

import pandas as pd
from sqlalchemy import create_engine, text

# ── Config ────────────────────────────────────────────────
DB_USER     = "postgres"
DB_PASSWORD = "Boston@24"  # ← replace with your password
DB_HOST     = "localhost"
DB_PORT     = "5433"
DB_NAME     = "crypto_collapse"

# ── Connect ───────────────────────────────────────────────

def get_engine(db=DB_NAME):
    from sqlalchemy.engine import URL
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=db,
    )
    return create_engine(url)

def create_database():
    """Create the database if it doesn't exist."""
    engine = get_engine(db="postgres")
    with engine.connect() as conn:
        conn.execute(text("COMMIT"))
        result = conn.execute(text(
            f"SELECT 1 FROM pg_database WHERE datname='{DB_NAME}'"
        ))
        if not result.fetchone():
            conn.execute(text(f"CREATE DATABASE {DB_NAME}"))
            print(f"  ✓ Database '{DB_NAME}' created")
        else:
            print(f"  ✓ Database '{DB_NAME}' already exists")

# ── Load tables ───────────────────────────────────────────

def load_tables():
    engine = get_engine()

    tables = {
        "unified_country":  "data/unified_country_dataset.csv",
        "imf_inflation":    "data/raw/imf_inflation.csv",
        "worldbank_fx_gdp": "data/raw/worldbank_fx_gdp.csv",
        "google_trends":    "data/raw/google_trends.csv",
        "chainalysis":      "data/raw/chainalysis_manual.csv",
        "btc_price":        "data/raw/coinmetrics_onchain.csv",
    }

    for table_name, filepath in tables.items():
        try:
            df = pd.read_csv(filepath)
            df.to_sql(table_name, engine, if_exists="replace", index=False)
            print(f"  ✓ {table_name:<25} {len(df):>6} rows loaded")
        except Exception as e:
            print(f"  ✗ {table_name}: {e}")

# ── Verify ────────────────────────────────────────────────

def verify():
    engine = get_engine()
    with engine.connect() as conn:
        print("\n  Verification:")
        result = conn.execute(text("""
            SELECT table_name, 
                   (SELECT COUNT(*) FROM information_schema.columns 
                    WHERE table_name = t.table_name) as cols
            FROM information_schema.tables t
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        for row in result:
            print(f"    ✓ {row[0]:<25} {row[1]} columns")

# ── Main ──────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print(" Crypto Collapse — Day 3: Loading PostgreSQL")
    print("=" * 55)

    print("\n[1] Creating database...")
    create_database()

    print("\n[2] Loading tables...")
    load_tables()

    print("\n[3] Verifying...")
    verify()

    print("\nDay 3 complete!")
    print("Database 'crypto_collapse' is ready for analysis.\n")