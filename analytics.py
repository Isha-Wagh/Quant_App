# analytics.py

import pandas as pd
import numpy as np
from scipy.stats import linregress
from db_utils import get_engine

def resample_ticks_to_ohlc(df: pd.DataFrame, timeframe: str = "1min") -> pd.DataFrame:
    """
    Resample raw ticks of ONE symbol to OHLCV for a given timeframe. [file:1]
    """
    df = df.copy()
    df["ts"] = pd.to_datetime(df["ts"])
    df = df.set_index("ts").sort_index()

    # Price OHLC and volume sum
    ohlc = df["price"].resample(timeframe).ohlc()
    ohlc["volume"] = df["size"].resample(timeframe).sum()

    ohlc = ohlc.dropna()
    ohlc = ohlc.reset_index()  # columns: ts, open, high, low, close, volume
    return ohlc

def compute_pair_analytics(df1: pd.DataFrame, df2: pd.DataFrame, window: int = 50) -> pd.DataFrame:
    """
    Basic pair analytics: hedge ratio, spread, z-score, rolling correlation.
    Handles duplicate timestamps safely. [file:1][file:2]
    """
    df1 = df1.copy()
    df2 = df2.copy()
    df1["ts"] = pd.to_datetime(df1["ts"])
    df2["ts"] = pd.to_datetime(df2["ts"])

    # Remove duplicate timestamps within each symbol by taking the last tick
    df1 = df1.sort_values("ts").drop_duplicates(subset=["ts"], keep="last")
    df2 = df2.sort_values("ts").drop_duplicates(subset=["ts"], keep="last")

    # Put prices into a single DataFrame with ts index and inner join
    p1 = df1[["ts", "price"]].rename(columns={"price": "p1"}).set_index("ts")
    p2 = df2[["ts", "price"]].rename(columns={"price": "p2"}).set_index("ts")

    aligned = p1.join(p2, how="inner").dropna()  # only common timestamps

    if len(aligned) < window:
        window = max(5, len(aligned) // 3)  # shrink window if needed


    x = aligned["p2"].to_numpy()
    y = aligned["p1"].to_numpy()

    from scipy.stats import linregress
    slope, intercept, r_value, p_value, std_err = linregress(x, y)
    hedge_ratio = slope

    spread = aligned["p1"] - hedge_ratio * aligned["p2"]
    spread_mean = spread.rolling(window=window).mean()
    spread_std = spread.rolling(window=window).std()
    zscore = (spread - spread_mean) / spread_std
    corr = aligned["p1"].rolling(window=window).corr(aligned["p2"])

    out = pd.DataFrame(
        {
            "ts": aligned.index,
            "hedge_ratio": hedge_ratio,
            "spread": spread,
            "zscore": zscore,
            "correlation": corr,
        }
    )
    return out.dropna()


from statsmodels.tsa.stattools import adfuller

def adf_on_spread(spread_series):
    """Run ADF test on spread and return p-value + text result. [file:1]"""
    spread_series = spread_series.dropna()
    result = adfuller(spread_series)
    p_value = result[1]
    if p_value < 0.05:
        msg = "Spread likely stationary (p < 0.05)"
    else:
        msg = "Spread not clearly stationary (p ≥ 0.05)"
    return p_value, msg

