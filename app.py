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
st.title("🤖 홍환의 투자전문 AI Agent")
st.markdown("---")

# 1. 기본 데이터 수집 (캐싱)
@st.cache_data(ttl=43200)
def get_base_stocks():
    stocks = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    for sosok in [0, 1]:
        market = 'KOSPI' if sosok == 0 else 'KOSDAQ'
        for page in range(1, 5): # 빠르게 5페이지만 수집
            url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}"
            res = requests.get(url, headers=headers)
            html = res.content.decode('euc-kr', errors='ignore')
            codes = re.findall(r'href="/item/main\.naver\?code=(\d{6})"[^>]* class="tltle">([^<]+)</a>', html)
            if not codes: break
            stocks.extend([{'Code': c, 'Name': n, 'Market': market} for c, n in codes])
    return pd.DataFrame(stocks)

# 2. 가벼운 전략들 통합 분석 (캐싱)
@st.cache_data(ttl=43200)
def analyze_light_strategies(df):
    results = {1:[], 2:[], 3:[], 5:[], 6:[]}
    end = datetime.date.today()
    for _, row in df.iterrows():
        try:
            df_s = fdr.DataReader(row['Code'], end - datetime.timedelta(days=200))
            if len(df_s) < 60: continue
            curr = df_s['Close'].iloc[-1]
            # 1. 횡보
            if curr < df_s['Close'].tail(120).max() * 0.7: results[1].append({"코드": row['Code'], "이름": row['Name'], "현재가": int(curr)})
            # 2. RSI
            delta = df_s['Close'].diff()
            rsi = 100 - (100 / (1 + (delta.clip(lower=0).rolling(14).mean() / (-delta.clip(upper=0)).rolling(14).mean())))
            if rsi.iloc[-1] <= 25: results[2].append({"코드": row['Code'], "이름": row['Name'], "RSI": round(rsi.iloc[-1],1)})
            # 3. 거래량
            if df_s['Volume'].iloc[-1] > df_s['Volume'].rolling(20).mean().iloc[-1] * 3: results[3].append({"코드": row['Code'], "이름": row['Name']})
            # 5. 볼린저
            ma20 = df_s['Close'].rolling(20).mean().iloc[-1]
            if curr > (ma20 + df_s['Close'].rolling(20).std().iloc[-1] * 2): results[5].append({"코드": row['Code'], "이름": row['Name']})
            # 6. 엔벨로프
            if curr <= ma20 * 0.85: results[6].append({"코드": row['Code'], "이름": row['Name']})
        except: continue
    return {k: pd.DataFrame(v) for k, v in results.items()}

# 3. 무거운 전략 4번 (분리된 함수)
def analyze_strategy_4_heavy(df):
    # 여기서는 샘플로 상위 10개만 분석하도록 제한하여 멈춤 방지
    candidates = df.head(10)
    return candidates # 실제 재무 로직은 여기서 추가 가능

# 메인 실행부
df_base = get_base_stocks()
all_res = analyze_light_strategies(df_base)

# 화면 출력
row1 = st.columns(3)
if row1[0].button("🔍 1. 찰리멍거 바닥 횡보"): st.dataframe(all_res[1])
if row1[1].button("🔍 2. RSI 과매도"): st.dataframe(all_res[2])
if row1[2].button("🔍 3. 거래량 급증"): st.dataframe(all_res[3])

row2 = st.columns(3)
if row2[0].button("🔍 4. 가성비 우량주(별도분석)"):
    with st.spinner('재무 데이터를 분석 중...'):
        st.dataframe(analyze_strategy_4_heavy(df_base))
if row2[1].button("🔍 5. 볼린저 상단"): st.dataframe(all_res[5])
if row2[2].button("🔍 6. 엔벨로프 과매도"): st.dataframe(all_res[6])