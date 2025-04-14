import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# Set page config (this must be first!)
st.set_page_config(page_title="Crypto Market Dashboard", layout="wide")

# Refresh every 15 minutes (900000 ms)
st_autorefresh(interval=900000, key="refresh")

# Your Polygon.io API key
API_KEY = "Z9nJVv8cOxoaJZI55yR5ZzLQsmZaBgyn"  # 🔁 Replace this with your key

st.title("📊 Real-Time Crypto Market Dashboard")

# Sidebar
st.sidebar.header("Settings")
crypto_symbol = st.sidebar.selectbox(
    "Choose Crypto Pair (Symbol)",
    ["X:BTCUSD", "X:ETHUSD", "X:MATICUSD", "X:DOGEUSD", "X:SOLUSD"]
)

interval = st.sidebar.selectbox("Chart Interval", ["minute", "hour", "day"])

from datetime import datetime, timedelta

to = datetime.today()
from_ = to - timedelta(days=1)
from_str = from_.strftime('%Y-%m-%d')
to_str = to.strftime('%Y-%m-%d')

# Get data from Polygon
def get_crypto_data(symbol, timespan):
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/{timespan}/{from_str}/{to_str}?apiKey={API_KEY}&limit=100"
    r = requests.get(url)
    print("Request URL:", url)
    print("Status Code:", r.status_code)
    print("Response Text:", r.text)

    data = r.json()

    if "results" not in data:
        return None

    df = pd.DataFrame(data["results"])
    df["t"] = pd.to_datetime(df["t"], unit="ms")
    df.rename(columns={"t": "time", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}, inplace=True)
    return df

# Fetch and display
data = get_crypto_data(crypto_symbol, interval)

if data is None:
    st.error("Failed to fetch data. Check symbol or API key.")
else:
    latest = data.iloc[-1]
    st.metric(label="Current Price", value=f"${latest['close']:.2f}")
    st.metric(label="24H Volume", value=f"{latest['volume']:.2f}")

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=data['time'],
        open=data['open'],
        high=data['high'],
        low=data['low'],
        close=data['close'],
        name='Price'
    ))

    fig.update_layout(title=f"{crypto_symbol.replace('X:', '')} Price Chart ({interval})", xaxis_title="Time", yaxis_title="Price (USD)", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
