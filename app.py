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

# RSI 계산 함수
def calculate_rsi(series, period=14):
    delta = series.diff()
    avg_gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    avg_loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# 1. 기본 종목 데이터 수집
@st.cache_data(ttl=43200)
def get_base_stocks():
    stocks = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    for sosok in [0, 1]:
        market = 'KOSPI' if sosok == 0 else 'KOSDAQ'
        for page in range(1, 4):
            url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}"
            res = requests.get(url, headers=headers)
            html = res.content.decode('euc-kr', errors='ignore')
            codes = re.findall(r'href="/item/main\.naver\?code=(\d{6})"[^>]* class="tltle">([^<]+)</a>', html)
            stocks.extend([{'Code': c, 'Name': n, 'Market': market} for c, n in codes])
    return pd.DataFrame(stocks)

# 2. 개별 전략 분석 로직
def run_strategy(df, strategy_num):
    results = []
    end = datetime.date.today()
    for _, row in df.iterrows():
        try:
            d = fdr.DataReader(row['Code'], end - datetime.timedelta(days=200))
            if len(d) < 60: continue
            curr = d['Close'].iloc[-1]
            ma20 = d['Close'].rolling(20).mean().iloc[-1]
            
            if strategy_num == 1: # 찰리멍거
                if curr < d['Close'].tail(120).max() * 0.7: results.append({"종목명": row['Name'], "현재가": int(curr)})
            elif strategy_num == 2: # RSI
                rsi = calculate_rsi(d['Close'])
                if rsi.iloc[-1] <= 25: results.append({"종목명": row['Name'], "RSI": round(rsi.iloc[-1],1)})
            elif strategy_num == 3: # 거래량
                if d['Volume'].iloc[-1] > d['Volume'].rolling(20).mean().iloc[-1] * 3: results.append({"종목명": row['Name'], "현재가": int(curr)})
            elif strategy_num == 4: # 가성비 우량주(샘플)
                results.append({"종목명": row['Name'], "상태": "분석 준비 완료"})
            elif strategy_num == 5: # 볼린저
                std = d['Close'].rolling(20).std().iloc[-1]
                if curr > (ma20 + std * 2): results.append({"종목명": row['Name'], "현재가": int(curr)})
            elif strategy_num == 6: # 엔벨로프
                if curr <= ma20 * 0.85: results.append({"종목명": row['Name'], "현재가": int(curr)})
        except: continue
    return pd.DataFrame(results)

# --- 화면 출력 (UI 복구) ---
st.title("🤖 홍환의 투자전문 AI Agent")
df_base = get_base_stocks()

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🔍 1. 찰리멍거 바닥 횡보"):
        with st.spinner('분석 중...'): st.dataframe(run_strategy(df_base, 1))
with col2:
    if st.button("🔍 2. 일봉 RSI 과매도"):
        with st.spinner('분석 중...'): st.dataframe(run_strategy(df_base, 2))
with col3:
    if st.button("🔍 3. 거래량 급증 정배열"):
        with st.spinner('분석 중...'): st.dataframe(run_strategy(df_base, 3))

col4, col5, col6 = st.columns(3)
with col4:
    if st.button("🔍 4. 가성비 알짜 우량주"):
        with st.spinner('분석 중...'): st.dataframe(run_strategy(df_base, 4))
with col5:
    if st.button("🔍 5. 볼린저 밴드 상단"):
        with st.spinner('분석 중...'): st.dataframe(run_strategy(df_base, 5))
with col6:
    if st.button("🔍 6. 엔벨로프 낙폭과대"):
        with st.spinner('분석 중...'): st.dataframe(run_strategy(df_base, 6))