import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from db_utils import load_pair_ticks
from analytics import resample_ticks_to_ohlc, compute_pair_analytics, adf_on_spread

st.set_page_config(page_title="Quant Trading Dashboard", layout="wide")
st.title("🧮 Quant Trading Dashboard")
st.markdown("**Live tick analytics with resampling, hedge ratios, spreads, and z-scores**")

# Sidebar controls
st.sidebar.header("📊 Controls")
symbol1 = st.sidebar.selectbox("Symbol 1", ["BTCUSDT", "ETHUSDT"], index=0)
symbol2 = st.sidebar.selectbox("Symbol 2", ["BTCUSDT", "ETHUSDT"], index=1)

timeframe = st.sidebar.selectbox("Timeframe", ["1s", "1min", "5min"], index=1)
window = st.sidebar.slider("Rolling window", 20, 200, 50, 10)
limit = st.sidebar.slider("Ticks to load", 1000, 20000, 5000, 1000)

st.sidebar.markdown("---")
uploaded = st.sidebar.file_uploader("Upload OHLC CSV (optional)", type=["csv"])
use_uploaded = uploaded is not None

# run_adf = st.sidebar.button("Run ADF on spread")

# Main logic
if st.sidebar.button("🔄 Refresh Data"):

    # 1) Load data: either from uploaded CSV or from DB
    if use_uploaded:
        ohlc_df = pd.read_csv(uploaded)
        # Expect columns: ts, p1, p2 (document this in README)
        ohlc_df["ts"] = pd.to_datetime(ohlc_df["ts"])
        df1 = ohlc_df[["ts", "p1"]].rename(columns={"p1": "price"})
        df1["symbol"] = symbol1
        df2 = ohlc_df[["ts", "p2"]].rename(columns={"p2": "price"})
        df2["symbol"] = symbol2
    else:
        df1, df2 = load_pair_ticks(symbol1, symbol2, limit)

    if df1.empty or df2.empty:
        st.warning("No data found. Run `python data_ingest.py` with fresh NDJSON first!")
    else:
        # 2) Resample to OHLC for price chart
        ohlc1 = resample_ticks_to_ohlc(df1, timeframe)
        ohlc2 = resample_ticks_to_ohlc(df2, timeframe)

         # 3) Pair analytics (hedge ratio, spread, zscore, correlation)
        analytics = compute_pair_analytics(df1, df2, window)

        if analytics.empty:
            st.warning("Not enough overlapping data points to compute analytics for this window/timeframe.")
            st.stop()

        # 4) Charts: prices + spread/zscore + correlation
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=(
                f"Prices: {symbol1} vs {symbol2}",
                "Spread & Z-Score",
                "Rolling Correlation"
            ),
            vertical_spacing=0.08
        )

        # Prices
        fig.add_trace(
            go.Scatter(
                x=ohlc1["ts"], y=ohlc1["close"],
                name=f"{symbol1} Close"
            ),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=ohlc2["ts"], y=ohlc2["close"],
                name=f"{symbol2} Close"
            ),
            row=1, col=1
        )

        # Spread & Z-score
        fig.add_trace(
            go.Scatter(
                x=analytics["ts"], y=analytics["spread"],
                name="Spread", line=dict(color="orange")
            ),
            row=2, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=analytics["ts"], y=analytics["zscore"],
                name="Z-Score", line=dict(color="red")
            ),
            row=2, col=1
        )

        # Z-score bands
        fig.add_trace(
            go.Scatter(
                x=analytics["ts"],
                y=pd.Series(2, index=analytics["ts"]),
                name="Z=2", line=dict(color="green", dash="dash")
            ),
            row=2, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=analytics["ts"],
                y=pd.Series(-2, index=analytics["ts"]),
                name="Z=-2", line=dict(color="green", dash="dash")
            ),
            row=2, col=1
        )

        # Rolling correlation
        fig.add_trace(
            go.Scatter(
                x=analytics["ts"],
                y=analytics["correlation"],
                name="Correlation",
                line=dict(color="blue")
            ),
            row=3, col=1
        )

        fig.update_layout(height=800, showlegend=True, title_text="Pair Trading Analytics")
        st.plotly_chart(fig, use_container_width=True)

        # 5) Summary statistics
        st.subheader("Summary statistics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Last price 1", f"{df1['price'].iloc[-1]:.2f}")
            st.metric("Last price 2", f"{df2['price'].iloc[-1]:.2f}")
        with col2:
            st.metric("Spread mean", f"{analytics['spread'].mean():.2f}")
            st.metric("Spread std", f"{analytics['spread'].std():.2f}")
        with col3:
            st.metric("Max z-score", f"{analytics['zscore'].max():.2f}")
            st.metric("Min z-score", f"{analytics['zscore'].min():.2f}")

        # 6) Key metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Latest Hedge Ratio", f"{analytics['hedge_ratio'].iloc[-1]:.4f}")
        with col2:
            st.metric("Latest Z-Score", f"{analytics['zscore'].iloc[-1]:.3f}")
        with col3:
            st.metric("Latest Spread", f"{analytics['spread'].iloc[-1]:.2f}")
        with col4:
            st.metric("Correlation", f"{analytics['correlation'].iloc[-1]:.3f}")

        # 7) Alerts
        latest_z = analytics["zscore"].iloc[-1]
        if latest_z > 2:
            st.error("🚨 Z-Score > 2: Potential SHORT opportunity!")
        elif latest_z < -2:
            st.error("🚨 Z-Score < -2: Potential LONG opportunity!")
        elif abs(latest_z) < 0.5:
            st.success("✅ Z-Score near 0: Mean reversion complete")

        
        # 8) ADF test (always shown when data available)
        p_val, msg = adf_on_spread(analytics["spread"])
        st.info(f"ADF p-value: {p_val:.4f} – {msg}")


        # 9) Download analytics
        csv = analytics.to_csv(index=False)
        st.download_button("📥 Download Analytics CSV", csv, f"{symbol1}_{symbol2}_analytics.csv")
