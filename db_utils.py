# db_utils.py

import os
import pandas as pd
from sqlalchemy import create_engine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_FILE = os.path.join(DATA_DIR, "ticks.db")

def get_engine():
    """Create and return a SQLAlchemy engine for the SQLite DB."""
    conn_str = f"sqlite:///{DB_FILE}"
    engine = create_engine(conn_str, echo=False)
    return engine

def load_ticks(symbol: str, limit: int = 5000) -> pd.DataFrame:
    """
    Load recent tick data for a given symbol from the 'ticks' table. [file:1]
    """
    engine = get_engine()
    query = f"""
        SELECT symbol, ts, price, size
        FROM ticks
        WHERE symbol = :symbol
        ORDER BY ts DESC
        LIMIT :limit
    """
    df = pd.read_sql(query, con=engine, params={"symbol": symbol, "limit": limit})
    # Order back in ascending time for plotting
    df = df.sort_values("ts")
    return df

# Add this function to the END of your existing db_utils.py

def load_pair_ticks(symbol1: str, symbol2: str, limit: int = 5000) -> tuple:
    """
    Load ticks for TWO symbols and return as two DataFrames.
    """
    engine = get_engine()
    query = """
        SELECT symbol, ts, price, size
        FROM ticks
        WHERE symbol IN (:sym1, :sym2)
        ORDER BY ts DESC
        LIMIT :limit
    """
    df = pd.read_sql(query, con=engine, params={"sym1": symbol1, "sym2": symbol2, "limit": limit})
    df1 = df[df["symbol"] == symbol1].sort_values("ts").reset_index(drop=True)
    df2 = df[df["symbol"] == symbol2].sort_values("ts").reset_index(drop=True)
    return df1, df2
