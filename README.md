# Quant Trading Analytics Dashboard

## 1. Project Overview

This project is an end‑to‑end analytical app for pair trading on Binance futures. It ingests tick data captured from the provided HTML WebSocket collector, stores it locally in SQLite, computes key quantitative analytics (hedge ratio, spread, z‑score, ADF, rolling correlation), and visualizes them in an interactive Streamlit dashboard. 

The goal is to demonstrate the full workflow a quantitative developer would build for a simple statistical‑arbitrage helper tool:

> Live data → Storage → Sampling → Analytics → Visualization → Alerts & Export. 

---

## 2. Architecture and Design

The system is modular: ingestion, storage, analytics, and visualization are separated so that each layer can be extended independently. 

### 2.1 Components

1. **Data Source – Binance WebSocket (HTML tool)**  
   - Uses the provided `binance_browser_collector_save_test-*.html`, which connects to `wss://fstream.binance.com` and streams tick data (trades) for chosen symbols such as `btcusdt` and `ethusdt`.  
   - The script normalizes each tick into `{symbol, ts, price, size}` and allows saving the buffered data as NDJSON. 

2. **Ingestion – `data_ingest.py`**  
   - Reads `data/ticks_sample.ndjson` using `pandas.read_json(..., lines=True)`.  
   - Validates/renames columns to `symbol`, `ts`, `price`, `size`; converts `ts` to pandas datetime and `price/size` to numeric.  
   - Writes all rows into SQLite database `data/ticks.db` table `ticks` via SQLAlchemy. 

3. **Storage – SQLite (`ticks` table)**  
   - Schema:  
     - `symbol TEXT`  
     - `ts TIMESTAMP`  
     - `price REAL`  
     - `size REAL`  
   - `db_utils.py` exposes:  
     - `get_engine()` – create SQLAlchemy engine.  
     - `load_ticks(symbol, limit)` – fetch recent ticks for one symbol.  
     - `load_pair_ticks(symbol1, symbol2, limit)` – fetch recent ticks for two symbols and split into two DataFrames. 

4. **Analytics – `analytics.py`**

   **Resampling / Sampling**  
   - `resample_ticks_to_ohlc(df, timeframe)` converts per‑symbol tick data to OHLCV bars at timeframes `1s`, `1min`, `5min` using pandas `resample`.  
   - Output columns: `ts`, `open`, `high`, `low`, `close`, `volume`.

   **Pair Analytics**  
   - `compute_pair_analytics(df1, df2, window)`:
     - Aligns symbol‑1 and symbol‑2 price series on common timestamps, handling duplicate timestamps by keeping the last tick per time.  
     - Runs an OLS regression \( price_1 = \beta \cdot price_2 + \alpha \) using `scipy.stats.linregress`; slope \(\beta\) is the **hedge ratio**.  
     - Computes **spread**: `spread = price1 − β × price2`.  
     - Computes rolling mean and standard deviation of spread and the **z‑score** `(spread − mean) / std`.  
     - Computes a **rolling correlation** between the two price series.  
     - Returns a DataFrame with `ts`, `hedge_ratio`, `spread`, `zscore`, `correlation`. 

   **ADF Test**  
   - `adf_on_spread(spread_series)` runs the Augmented Dickey–Fuller test (`statsmodels.tsa.stattools.adfuller`) on the spread and returns:
     - `p_value`: test p‑value.  
     - `msg`: interpretation string (“Spread likely stationary (p < 0.05)” or “Spread not clearly stationary (p ≥ 0.05)”). 

5. **Frontend – `app.py` (Streamlit + Plotly)**  

   **Sidebar Controls**  
   - `Symbol 1` and `Symbol 2` (e.g., `BTCUSDT`, `ETHUSDT`).  
   - `Timeframe`: `1s`, `1min`, `5min` (resampling).  
   - `Rolling window`: window length for z‑score and rolling correlation.  
   - `Ticks to load`: number of recent ticks to pull from SQLite.  
   - Optional **OHLC CSV uploader** for running the same analytics on user‑provided bar data. 

   **Main Dashboard**  
   - **Price chart** (row 1): resampled close prices for both symbols, using Plotly (zoom, pan, hover tooltips).  
   - **Spread & z‑score chart** (row 2):  
     - Orange line: spread.  
     - Red line: z‑score of spread.  
     - Green dashed bands: z = +2 and z = −2.  
   - **Rolling correlation chart** (row 3): blue line showing rolling correlation between the two legs.  
   - **Summary statistics**:  
     - Last price for each symbol.
     - Last price for each symbol.  
     - Mean and standard deviation of spread.  
     - Maximum and minimum observed z‑score over the loaded window.  
   - **Latest metrics** (as Streamlit metrics):  
     - Latest hedge ratio.  
     - Latest z‑score.  
     - Latest spread.  
     - Latest rolling correlation.  
   - **Alerts**:  
     - If z‑score > 2 → potential short opportunity.  
     - If z‑score < −2 → potential long opportunity.  
     - If |z‑score| is small → mean reversion likely complete.  
   - **ADF result**: p‑value and text message shown once analytics are available.  
   - **CSV export**: button to download the analytics DataFrame as CSV. 

---

## 3. Setup and Installation

**From the project root (`quant_app/`)**:

    python -m venv venv
    source venv/bin/activate # Windows: venv\Scripts\activate

    pip install -r requirements.txt


`requirements.txt` contains:

- `streamlit`  
- `pandas`  
- `sqlalchemy`  
- `scipy`  
- `plotly`  
- `statsmodels`  



---

## 4. Data Collection and Ingestion

### 4.1 Collect tick data with the HTML tool

1. Open `binance_browser_collector_save_test-*.html` in a browser.   
2. In “Symbols comma-separated”, enter:

   `btcusdt,ethusdt`

3. Click **Start** and let it buffer ticks for a few minutes.  
4. Click **Download NDJSON** and save the file as:

   `data/ticks_sample.ndjson`

You now have a local NDJSON file containing `{symbol, ts, price, size}` tick records. 

### 4.2 Ingest NDJSON into SQLite

python data_ingest.py


This will:

- Create `data/ticks.db` if it does not exist.  
- Insert all rows from `ticks_sample.ndjson` into the `ticks` table. 

You can verify ingestion with:

python check_db.py

which prints table names and counts per symbol.

---

## 5. Running the Dashboard

**From the project root with the virtual environment activated**:

    streamlit run app.py

Then open the local URL (usually `http://localhost:8501`) in your browser.

### 5.1 Basic usage

1. Choose **Symbol 1** and **Symbol 2** (e.g., `BTCUSDT` and `ETHUSDT`).  
2. Choose **Timeframe** (`1s`, `1min`, or `5min`).  
3. Choose **Rolling window** (e.g., 50) and **Ticks to load** (e.g., 5000).  
4. Click **“Refresh Data”** in the sidebar.  

The dashboard will display:

- Price chart, spread & z‑score chart, rolling correlation chart.  
- Summary statistics and latest metrics.  
- Alerts based on the latest z‑score.  
- ADF p‑value and stationarity message.  
- A button to download the analytics CSV. 

---

## 6. OHLC CSV Upload

The app also supports running the same analytics on uploaded OHLC data. 

- In the sidebar, use the **“Upload OHLC CSV (optional)”** widget.  
- Expected CSV format for this demo:

    ts,p1,p2
    2025-01-01T10:00:00Z,price_for_symbol1,price_for_symbol2


- `ts` is a timestamp parsable by pandas, `p1` and `p2` are prices for Symbol 1 and Symbol 2.  
- When a file is uploaded, clicking **“Refresh Data”** uses this CSV instead of SQLite ticks, but the rest of the analytics and visualization remain identical. 

This satisfies the requirement to support OHLC upload while still working without any dummy upload. 

---

## 7. Methodology and Analytics Explanation

### 7.1 Sampling and Resampling

- Raw trades are high‑frequency ticks; for visualization and pair analytics they are resampled to OHLCV bars at user‑selectable timeframes (1 second, 1 minute, 5 minutes).  
- Resampling reduces noise and aligns the two symbols on a common time grid. 

### 7.2 Hedge Ratio and Spread

- For a chosen pair (Symbol 1, Symbol 2), close prices are aligned and an OLS regression

  \( price_1 = \beta \cdot price_2 + \alpha \)

  is estimated; \(\beta\) is used as the **hedge ratio**.   
- The **spread** is defined as:

  `spread = price1 − β × price2`.

  A stationary spread suggests a mean‑reverting relationship between the two legs.

### 7.3 Z‑Score and Alerts

- Over a rolling window, the spread’s mean and standard deviation are computed.  
- The **z‑score** is `(spread − rolling_mean) / rolling_std`.  
- Alerts are shown when z‑score crosses ±2 (potential entry) or comes back near 0 (mean reversion / potential exit). This follows a simple mean‑reversion heuristic. 

### 7.4 Rolling Correlation

- Rolling Pearson
correlation is computed between the two price series over the same rolling window.  
- This helps understand whether the relationship between the two legs is stable over time and whether deviations in spread are meaningful. 

### 7.5 ADF Test on Spread

- The Augmented Dickey–Fuller (ADF) test checks whether the spread series is likely stationary.  
- Null hypothesis: the spread has a unit root (non‑stationary); alternative: spread is stationary.  
- If the p‑value is below 0.05, the app displays that the spread is likely stationary; otherwise it indicates that stationarity is not clearly supported by the data. 

---

## 8. Design Choices and Possible Extensions

- **SQLite for storage**: simple, file‑based, and sufficient for local prototyping; can be upgraded to Postgres/TimescaleDB for production.  
- **Streamlit + Plotly**: very fast to build interactive dashboards with zoom/pan/hover and sidebar controls.  
- **Pandas‑based analytics**: easy to read and reason about; can be swapped out for more scalable engines (Dask/Ray) if needed. 

Possible future extensions (not implemented, but accounted for in modular design):

- Dynamic hedge estimation via Kalman filter.  
- Robust regression (Huber, Theil–Sen) as alternative regression types.  
- Mini mean‑reversion backtest (z > 2 entry, z → 0 exit).  
- Liquidity filters and cross‑correlation heatmaps. 

---

## 9. How to Reproduce and Run

1. Collect NDJSON from the HTML WebSocket tool for symbols such as BTCUSDT and ETHUSDT.   
2. Place it at `data/ticks_sample.ndjson`.  
3. Run `python data_ingest.py` once to populate `data/ticks.db`. [file:1]  
4. Start the dashboard with `streamlit run app.py`.  
5. In the UI, choose symbols, timeframe, rolling window, and click **Refresh Data**.  
6. Optionally upload an OHLC CSV and rerun analytics on that dataset. 

---

## 10. ChatGPT / LLM Usage Transparency

In line with the assignment instructions, a language model (ChatGPT) was used as a coding and design assistant for this project. 

Specifically:

- Helped think through the high‑level architecture and how to separate ingestion, storage, analytics, and frontend.  
- Assisted with boilerplate examples for pandas/SQLAlchemy/Streamlit usage and with debugging some alignment issues in the analytics code.  
- Helped draft and refine this README and the textual explanation of analytics.  

All code and logic were reviewed, adapted, and integrated manually to ensure they match the assignment requirements and work correctly with the provided Binance HTML collector and the local environment.

