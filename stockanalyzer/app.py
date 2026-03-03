import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
import datetime
import os

st.set_page_config(page_title="Stock Market Visualizer", layout="wide")

st.title("📈 Stock Market Visualizer")

# -----------------------------
# Sidebar Configuration
# -----------------------------

st.sidebar.header("Stock Settings")

ticker = st.sidebar.text_input("Enter Stock Ticker", "AAPL")
period = st.sidebar.selectbox("Select Time Period",
                               ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"])

interval = st.sidebar.selectbox("Select Interval",
                                 ["1d", "1wk", "1mo"])

show_ma = st.sidebar.checkbox("Show Moving Averages", True)
ma_short = st.sidebar.number_input("Short MA Window", 5)
ma_long = st.sidebar.number_input("Long MA Window", 20)

show_rsi = st.sidebar.checkbox("Show RSI", True)
show_bb = st.sidebar.checkbox("Show Bollinger Bands", True)

# -----------------------------
# Fetch Data
# -----------------------------

@st.cache_data
def load_data(ticker, period, interval):
    stock = yf.Ticker(ticker)
    df = stock.history(period=period, interval=interval)
    return df

df = load_data(ticker, period, interval)

if df.empty:
    st.error("Invalid ticker or no data available.")
    st.stop()

# -----------------------------
# Indicators
# -----------------------------

df['MA_Short'] = df['Close'].rolling(window=int(ma_short)).mean()
df['MA_Long'] = df['Close'].rolling(window=int(ma_long)).mean()

# RSI
delta = df['Close'].diff()
gain = delta.where(delta > 0, 0)
loss = -delta.where(delta < 0, 0)

avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()

rs = avg_gain / avg_loss
df['RSI'] = 100 - (100 / (1 + rs))

# Bollinger Bands
df['BB_Middle'] = df['Close'].rolling(20).mean()
df['BB_Upper'] = df['BB_Middle'] + 2 * df['Close'].rolling(20).std()
df['BB_Lower'] = df['BB_Middle'] - 2 * df['Close'].rolling(20).std()

# -----------------------------
# Candlestick Chart
# -----------------------------

fig = make_subplots(rows=2 if show_rsi else 1, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.05,
                    row_heights=[0.7, 0.3] if show_rsi else [1])

fig.add_trace(go.Candlestick(
    x=df.index,
    open=df['Open'],
    high=df['High'],
    low=df['Low'],
    close=df['Close'],
    name='Candlestick'
), row=1, col=1)

if show_ma:
    fig.add_trace(go.Scatter(x=df.index, y=df['MA_Short'],
                             name='Short MA'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA_Long'],
                             name='Long MA'), row=1, col=1)

if show_bb:
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'],
                             name='BB Upper'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'],
                             name='BB Lower'), row=1, col=1)

if show_rsi:
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'],
                             name='RSI'), row=2, col=1)

fig.update_layout(height=800, xaxis_rangeslider_visible=False)

st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Financial Ratios
# -----------------------------

st.subheader("📊 Financial Ratios")

stock = yf.Ticker(ticker)
info = stock.info

ratios = {
    "Market Cap": info.get("marketCap"),
    "PE Ratio": info.get("trailingPE"),
    "Forward PE": info.get("forwardPE"),
    "Price to Book": info.get("priceToBook"),
    "Dividend Yield": info.get("dividendYield")
}

st.json(ratios)

# -----------------------------
# Portfolio Upload
# -----------------------------

st.subheader("📁 Portfolio Tracking")

uploaded_file = st.file_uploader("Upload Portfolio CSV or Excel", type=["csv", "xlsx"])

if uploaded_file:
    if uploaded_file.name.endswith("csv"):
        portfolio = pd.read_csv(uploaded_file)
    else:
        portfolio = pd.read_excel(uploaded_file)

    st.write(portfolio)

    portfolio["Current Price"] = portfolio["Ticker"].apply(
        lambda x: yf.Ticker(x).history(period="1d")["Close"].iloc[-1]
    )

    portfolio["Value"] = portfolio["Shares"] * portfolio["Current Price"]

    st.write("Total Portfolio Value:", portfolio["Value"].sum())

# -----------------------------
# Correlation Heatmap
# -----------------------------

st.subheader("🔗 Correlation Analysis")

tickers_input = st.text_input("Enter multiple tickers (comma-separated)", "AAPL,MSFT,GOOGL")

tickers_list = [t.strip() for t in tickers_input.split(",")]

if st.button("Generate Correlation"):
    data = yf.download(tickers_list, period="1y")['Close']
    corr = data.corr()

    heatmap = px.imshow(corr, text_auto=True, aspect="auto")
    st.plotly_chart(heatmap, use_container_width=True)

# -----------------------------
# Export Options
# -----------------------------

st.subheader("💾 Export Chart")

if st.button("Export as HTML"):
    fig.write_html("chart.html")
    st.success("Chart exported as chart.html")

if st.button("Export as PNG"):
    fig.write_image("chart.png")
    st.success("Chart exported as chart.png")

# -----------------------------
# Save Configuration
# -----------------------------

st.subheader("⚙ Save Configuration")

config = {
    "ticker": ticker,
    "period": period,
    "interval": interval,
    "show_ma": show_ma,
    "show_rsi": show_rsi,
    "show_bb": show_bb
}

if st.button("Save Settings"):
    with open("saved_configs.json", "w") as f:
        json.dump(config, f)
    st.success("Configuration Saved!")
