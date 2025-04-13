import os
import requests
import streamlit as st
from dotenv import load_dotenv
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# First command
st.set_page_config(page_title="📉 Stock Visualizer", layout="wide")

# Auto-refresh every 15 minutes
st_autorefresh(interval=15 * 60 * 1000, key="stock-refresh")

# Load Alpha Vantage key
load_dotenv()
alpha_key = os.getenv("stockapi_key")

# Sidebar settings
st.sidebar.title("Settings")
symbol = st.sidebar.text_input("Stock Symbol", "RELIANCE.BSE")  # e.g., "AAPL" or "RELIANCE.BSE"
interval = st.sidebar.selectbox("Interval", ["1min", "5min", "15min", "60min", "daily"], index=3)
refresh = st.sidebar.button("🔄 Manual Refresh")

st.title(f"Live Market Chart: {symbol}")

# Alpha Vantage URL
if interval == "daily":
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={symbol}&apikey={alpha_key}"
    key_name = "Time Series (Daily)"
else:
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval={interval}&apikey={alpha_key}"
    key_name = f"Time Series ({interval})"

res = requests.get(url).json()

if key_name in res:
    ts_data = res[key_name]
    df = pd.DataFrame.from_dict(ts_data, orient="index").rename(columns={
        "1. open": "open",
        "2. high": "high",
        "3. low": "low",
        "4. close": "close",
        "5. volume": "volume"
    })
    df = df.astype(float)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    # Display latest stats
    latest_price = df["close"].iloc[-1]
    prev_price = df["close"].iloc[-2]
    pct_change = ((latest_price - prev_price) / prev_price) * 100

    st.metric(label="📈 Latest Price", value=f"{latest_price:.2f}", delta=f"{pct_change:.2f}%")

    # Candlestick chart
    fig = go.Figure(data=[
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Price"
        )
    ])
    fig.update_layout(title=f"📉 {symbol.upper()} Price Chart", xaxis_title="Time", yaxis_title="Price",
                      xaxis_rangeslider_visible=False, template="plotly_dark", height=500)
    st.plotly_chart(fig, use_container_width=True)

    # Volume bar chart
    vol_fig = go.Figure()
    vol_fig.add_trace(go.Bar(x=df.index, y=df["volume"], marker_color='lightblue', name="Volume"))
    vol_fig.update_layout(title="🔊 Volume Traded", xaxis_title="Time", yaxis_title="Volume", height=300)
    st.plotly_chart(vol_fig, use_container_width=True)

    with st.expander("🧾 Raw Data Table"):
        st.dataframe(df.tail(20).reset_index().rename(columns={"index": "Time"}))
else:
    st.warning("Failed to fetch data. Check your API key, symbol, or interval.")
