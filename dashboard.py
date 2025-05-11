import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta

# Finnhub API key
FINNHUB_API_KEY = 'd0gamdpr01qhao4sg1n0d0gamdpr01qhao4sg1ng'

st.title('Market Dashboard: Movers, IPOs, and Unicorns')

# --- 1. User-Selectable Market/Exchange ---
market_options = ['Nasdaq', 'NYSE', 'AMEX', 'All']
selected_market = st.selectbox('Select Market/Exchange for Stock Search', market_options)

stock_type = st.radio('What kind of stocks are you looking for?', [
    'Biggest 30-day winners',
    'Biggest 30-day losers',
    'All (sortable table)'
])

@st.cache_data(show_spinner=True)
def get_exchange_tickers(selected_market):
    tickers = []
    if selected_market in ['Nasdaq', 'All']:
        nasdaq_url = 'ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt'
        df_nasdaq = pd.read_csv(nasdaq_url, sep='|')
        tickers += df_nasdaq['Symbol'].dropna().tolist()
    if selected_market in ['NYSE', 'AMEX', 'All']:
        other_url = 'ftp://ftp.nasdaqtrader.com/SymbolDirectory/otherlisted.txt'
        df_other = pd.read_csv(other_url, sep='|')
        if selected_market == 'NYSE' or selected_market == 'All':
            tickers += df_other[df_other['Exchange'] == 'N']['ACT Symbol'].dropna().tolist()
        if selected_market == 'AMEX' or selected_market == 'All':
            tickers += df_other[df_other['Exchange'] == 'A']['ACT Symbol'].dropna().tolist()
    tickers = [t for t in tickers if isinstance(t, str) and t.isalpha() and t != 'Symbol']
    return tickers

tickers = get_exchange_tickers(selected_market)
st.write(f"Found {len(tickers)} tickers for {selected_market}.")

max_tickers = st.slider('Number of tickers to analyze (for speed)', 50, 500, 200)
tickers = tickers[:max_tickers]

@st.cache_data(show_spinner=True)
def get_30d_performance(tickers):
    end = datetime.now()
    start = end - timedelta(days=35)
    data = yf.download(tickers, start=start.strftime('%Y-%m-%d'), end=end.strftime('%Y-%m-%d'), group_by='ticker', progress=False, threads=True)
    perf = []
    for t in tickers:
        try:
            close = data[t]['Close'].dropna()
            if len(close) < 2:
                perf.append({'Ticker': t, '30d % Change': np.nan})
                continue
            pct = (close.iloc[-1] - close.iloc[0]) / close.iloc[0] * 100
            perf.append({'Ticker': t, '30d % Change': pct})
        except Exception:
            perf.append({'Ticker': t, '30d % Change': np.nan})
    df_perf = pd.DataFrame(perf).sort_values('30d % Change', ascending=False, na_position='last')
    return df_perf

df_perf = get_30d_performance(tickers)

# --- Show table based on user choice ---
if stock_type == 'Biggest 30-day winners':
    st.subheader('Biggest 30-day Winners')
    st.dataframe(df_perf.head(10).reset_index(drop=True), height=400)
elif stock_type == 'Biggest 30-day losers':
    st.subheader('Biggest 30-day Losers')
    st.dataframe(df_perf.tail(10).sort_values('30d % Change').reset_index(drop=True), height=400)
else:
    st.subheader('All Analyzed Stocks (Sortable)')
    page_size = 25
    num_pages = (len(df_perf) - 1) // page_size + 1
    page = st.number_input('Page', min_value=1, max_value=num_pages, value=1, step=1)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    st.dataframe(df_perf.iloc[start_idx:end_idx].reset_index(drop=True), height=400)

# --- 2. User-Selectable Country for IPOs ---
st.header('Upcoming IPOs (Next 7 Days)')
# Get all IPOs for the next 7 days
now = datetime.now()
from_date = now.strftime('%Y-%m-%d')
to_date = (now + timedelta(days=7)).strftime('%Y-%m-%d')
ipo_url = f'https://finnhub.io/api/v1/calendar/ipo?from={from_date}&to={to_date}&token={FINNHUB_API_KEY}'
try:
    ipo_resp = requests.get(ipo_url)
    ipo_data = ipo_resp.json().get('ipoCalendar', [])
    df_ipo = pd.DataFrame(ipo_data)
    if not df_ipo.empty:
        countries = ['All'] + sorted(df_ipo['country'].dropna().unique().tolist()) if 'country' in df_ipo.columns else ['All']
        selected_country = st.selectbox('Filter IPOs by Country', countries)
        if selected_country != 'All' and 'country' in df_ipo.columns:
            df_ipo = df_ipo[df_ipo['country'] == selected_country]
        st.dataframe(df_ipo[['name', 'symbol', 'exchange', 'date', 'numberOfShares', 'price'] + (['country'] if 'country' in df_ipo.columns else [])], height=400)
    else:
        st.info('No IPOs found for the coming week.')
except Exception as e:
    st.error(f'Error fetching IPO data: {e}')

st.caption('Data sources: Nasdaq, NYSE, AMEX, yfinance, Finnhub, CB Insights/Wikipedia (unicorns)') 