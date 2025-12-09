# data_ingest.py

import os
import pandas as pd
from sqlalchemy import create_engine

# 1. Paths (change if your structure is different)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# NDJSON input file
NDJSON_FILE = os.path.join(DATA_DIR, "ticks_sample.ndjson")

# SQLite database file
DB_FILE = os.path.join(DATA_DIR, "ticks.db")

def load_ndjson_to_dataframe():
    """
    Read the NDJSON tick file into a pandas DataFrame.
    Each line is a JSON object with fields: symbol, ts, price, size. [file:2]
    """
    if not os.path.exists(NDJSON_FILE):
        raise FileNotFoundError(f"NDJSON file not found: {NDJSON_FILE}")

    # lines=True tells pandas that each line is a separate JSON object (NDJSON format).
    df = pd.read_json(NDJSON_FILE, lines=True)

    # Make sure expected columns exist; if names differ, print df.head() once and adjust.
    # For the provided HTML, we expect: symbol (s), ts, price (p), size (q) after normalize. [file:2]
    # But since the HTML already writes normalized keys, we assume: symbol, ts, price, size. [file:2]

    # Rename columns if needed (uncomment and adjust if your columns differ)
    # df = df.rename(columns={"s": "symbol", "E": "ts", "p": "price", "q": "size"})

    # Convert timestamp column to pandas datetime, if it's a string.
    # If ts is already ISO string like "2025-12-06T08:00:00Z", this works. [file:2]
    df["ts"] = pd.to_datetime(df["ts"])

    # Ensure correct dtypes for numeric columns
    df["price"] = pd.to_numeric(df["price"])
    df["size"] = pd.to_numeric(df["size"])

    return df


def create_db_engine():
    """
    Create a SQLAlchemy engine for SQLite.
    SQLite connection string uses 'sqlite:///' + path. [file:1]
    """
    conn_str = f"sqlite:///{DB_FILE}"
    engine = create_engine(conn_str, echo=False)  # echo=True prints SQL for debugging
    return engine


def save_ticks_to_sqlite(df):
    """
    Save the ticks DataFrame into a SQLite table named 'ticks'.
    If the table exists, append new rows. [file:1]
    """
    engine = create_db_engine()

    # to_sql will create the table automatically if it doesn't exist.
    # index=False: we don't want the DataFrame index as a column.
    df.to_sql("ticks", con=engine, if_exists="append", index=False)

    print(f"Saved {len(df)} rows into table 'ticks' in {DB_FILE}")


def main():
    print("Loading NDJSON into DataFrame...")
    df = load_ndjson_to_dataframe()
    print(df.head())
    print(f"Total rows loaded: {len(df)}")

    print("Saving DataFrame to SQLite...")
    save_ticks_to_sqlite(df)
    print("Done.")


if __name__ == "__main__":
    main()
