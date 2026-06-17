import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import datetime
import requests
import re
import io
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(layout="wide")

def calculate_rsi(series, period=14):
    delta = series.diff()
    avg_gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    avg_loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

st.title("🤖 홍환의 투자전문 AI Agent")
st.markdown("---")
st.sidebar.header("⚙️ 시스템 제어판")

@st.cache_data(ttl=43200)
def get_base_stocks(today_str):
    stocks = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    for sosok in [0, 1]:
        market_name = 'KOSPI' if sosok == 0 else 'KOSDAQ'
        for page in range(1, 10):
            url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}"
            res = requests.get(url, headers=headers)
            html = res.content.decode('euc-kr', errors='ignore')
            page_codes = re.findall(r'href="/item/main\.naver\?code=(\d{6})"[^>]* class="tltle">([^<]+)</a>', html)
            if not page_codes: break
            dfs = pd.read_html(io.StringIO(html))
            df_table = dfs[1].dropna(subset=['종목명'])
            marcap_col = next((c for c in df_table.columns if '시가총액' in str(c)), None)
            per_col = next((c for c in df_table.columns if 'PER' in str(c)), None)
            roe_col = next((c for c in df_table.columns if 'ROE' in str(c)), None)
            for (code, name), (_, row) in zip(page_codes, df_table.iterrows()):
                marcap_val = row[marcap_col] if marcap_col else 0
                if pd.isna(marcap_val): continue
                marcap_val = int(re.sub(r'[^0-9]', '', str(marcap_val)))
                if marcap_val >= 2000:
                    try: 
                        per_val = float(row[per_col]) if per_col and not pd.isna(row[per_col]) else None
                        roe_val = float(row[roe_col]) if roe_col and not pd.isna(row[roe_col]) else None
                    except: per_val, roe_val = None, None
                    stocks.append({'Code': code, 'Name': name, 'Market': market_name, 'PER': per_val, 'ROE': roe_val})
                else: break
    return pd.DataFrame(stocks)

today_str = datetime.date.today().strftime('%Y-%m-%d')
df_base = get_base_stocks(today_str)

@st.cache_data(ttl=43200)
def analyze_strategy_1(df):
    results = []
    for _, row in df.iterrows():
        try:
            stock_df = fdr.DataReader(row['Code'], datetime.datetime.now() - datetime.timedelta(days=500))
            if len(stock_df) < 250: continue
            current = int(stock_df['Close'].iloc[-1])
            if current < stock_df['Close'].tail(240).max() * 0.6:
                results.append({"종목코드": row['Code'], "종목명": row['Name'], "현재가": current})
        except: continue
    return pd.DataFrame(results)

@st.cache_data(ttl=43200)
def analyze_strategy_2(df):
    results = []
    for _, row in df.iterrows():
        try:
            df_d = fdr.DataReader(row['Code'], datetime.datetime.now() - datetime.timedelta(days=200))
            df_d['RSI'] = calculate_rsi(df_d['Close'])
            if df_d['RSI'].iloc[-1] <= 25:
                results.append({"종목코드": row['Code'], "종목명": row['Name'], "RSI": round(df_d['RSI'].iloc[-1],1)})
        except: continue
    return pd.DataFrame(results)

@st.cache_data(ttl=43200)
def analyze_strategy_3(df):
    results = []
    for _, row in df.iterrows():
        try:
            df_d = fdr.DataReader(row['Code'], datetime.datetime.now() - datetime.timedelta(days=100))
            if df_d['Volume'].iloc[-1] > df_d['Volume'].rolling(20).mean().iloc[-1] * 3:
                results.append({"종목코드": row['Code'], "종목명": row['Name'], "현재가": int(df_d['Close'].iloc[-1])})
        except: continue
    return pd.DataFrame(results)

@st.cache_data(ttl=43200)
def analyze_strategy_4(df):
    candidates = df[(df['ROE'] >= 10) & (df['PER'] > 0) & (df['PER'] <= 15)]
    return candidates

@st.cache_data(ttl=43200)
def analyze_strategy_5(df):
    results = []
    for _, row in df.iterrows():
        try:
            df_d = fdr.DataReader(row['Code'], datetime.datetime.now() - datetime.timedelta(days=100))
            ma20 = df_d['Close'].rolling(20).mean()
            if df_d['Close'].iloc[-1] > (ma20.iloc[-1] + df_d['Close'].rolling(20).std().iloc[-1] * 2):
                results.append({"종목코드": row['Code'], "종목명": row['Name']})
        except: continue
    return pd.DataFrame(results)

@st.cache_data(ttl=43200)
def analyze_strategy_6(df):
    results = []
    for _, row in df.iterrows():
        try:
            df_d = fdr.DataReader(row['Code'], datetime.datetime.now() - datetime.timedelta(days=100))
            if df_d['Close'].iloc[-1] <= df_d['Close'].rolling(20).mean().iloc[-1] * 0.85:
                results.append({"종목코드": row['Code'], "종목명": row['Name']})
        except: continue
    return pd.DataFrame(results)

cols = st.columns(3)
if cols[0].button("1. 바닥 횡보주"): st.dataframe(analyze_strategy_1(df_base))
if cols[1].button("2. RSI 과매도"): st.dataframe(analyze_strategy_2(df_base))
if cols[2].button("3. 거래량 급증"): st.dataframe(analyze_strategy_3(df_base))
cols2 = st.columns(3)
if cols2[0].button("4. 가성비 우량주"): st.dataframe(analyze_strategy_4(df_base))
if cols2[1].button("5. 볼린저 상단"): st.dataframe(analyze_strategy_5(df_base))
if cols2[2].button("6. 엔벨로프 과매도"): st.dataframe(analyze_strategy_6(df_base))