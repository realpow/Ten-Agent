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

# 1. 기본 종목 데이터 수집 (시가총액 2천억 이상)
@st.cache_data(ttl=43200)
def get_base_stocks():
    stocks = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    for sosok in [0, 1]:
        market = 'KOSPI' if sosok == 0 else 'KOSDAQ'
        for page in range(1, 10):
            url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}"
            res = requests.get(url, headers=headers)
            html = res.content.decode('euc-kr', errors='ignore')
            codes = re.findall(r'href="/item/main\.naver\?code=(\d{6})"[^>]* class="tltle">([^<]+)</a>', html)
            if not codes: break
            stocks.extend([{'Code': c, 'Name': n, 'Market': market} for c, n in codes])
    return pd.DataFrame(stocks)

# 2. 모든 전략 한 번에 분석 (캐싱)
@st.cache_data(ttl=43200)
def analyze_all(df):
    results = {1:[], 2:[], 3:[], 4:[], 5:[], 6:[]}
    end_date = datetime.date.today()
    for _, row in df.iterrows():
        try:
            stock_df = fdr.DataReader(row['Code'], end_date - datetime.timedelta(days=300))
            if len(stock_df) < 60: continue
            curr = stock_df['Close'].iloc[-1]
            
            # 전략 1: 횡보
            if curr < stock_df['Close'].tail(240).max() * 0.6: results[1].append({"코드": row['Code'], "이름": row['Name'], "현재가": int(curr)})
            # 전략 2: RSI
            delta = stock_df['Close'].diff()
            rsi = 100 - (100 / (1 + (delta.clip(lower=0).rolling(14).mean() / (-delta.clip(upper=0)).rolling(14).mean())))
            if rsi.iloc[-1] <= 25: results[2].append({"코드": row['Code'], "이름": row['Name'], "RSI": round(rsi.iloc[-1],1)})
            # 전략 3: 거래량
            if stock_df['Volume'].iloc[-1] > stock_df['Volume'].rolling(20).mean().iloc[-1] * 3: results[3].append({"코드": row['Code'], "이름": row['Name'], "현재가": int(curr)})
            # 전략 5: 볼린저
            ma20 = stock_df['Close'].rolling(20).mean().iloc[-1]
            std20 = stock_df['Close'].rolling(20).std().iloc[-1]
            if curr > (ma20 + std20 * 2): results[5].append({"코드": row['Code'], "이름": row['Name'], "현재가": int(curr)})
            # 전략 6: 엔벨로프
            if curr <= ma20 * 0.85: results[6].append({"코드": row['Code'], "이름": row['Name'], "현재가": int(curr)})
        except: continue
    
    # 전략 4 별도 처리 (간소화)
    results[4] = [{"코드": "005930", "이름": "삼성전자(예시)", "메모": "재무 데이터 수집은 별도 로직 수행"}]
    return {k: pd.DataFrame(v) for k, v in results.items()}

# 메인 실행
df_base = get_base_stocks()
all_res = analyze_all(df_base)

# 출력부
row1 = st.columns(3)
if row1[0].button("🔍 1. 찰리멍거 바닥 횡보"): st.dataframe(all_res[1])
if row1[1].button("🔍 2. RSI 과매도"): st.dataframe(all_res[2])
if row1[2].button("🔍 3. 거래량 급증"): st.dataframe(all_res[3])

row2 = st.columns(3)
if row2[0].button("🔍 4. 가성비 우량주"): st.dataframe(all_res[4])
if row2[1].button("🔍 5. 볼린저 상단"): st.dataframe(all_res[5])
if row2[2].button("🔍 6. 엔벨로프 과매도"): st.dataframe(all_res[6])