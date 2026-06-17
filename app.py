import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import datetime
import requests
import re

st.set_page_config(layout="wide", page_title="홍환의 투자전문 AI Agent")
st.title("🤖 홍환의 투자전문 AI Agent")
st.markdown(f"**기준일자: {datetime.date.today().strftime('%Y년 %m월 %d일')}**")

# [핵심] 시총 2천억 이상 리스트 수집
@st.cache_data(ttl=86400)
def get_base_stocks():
    stocks = []
    # 시총 상위 2000억 이상 종목을 가져오기 위한 페이지 범위 설정 (필요시 조정)
    for page in range(1, 15): 
        url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok=0&page={page}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        codes = re.findall(r'/item/main\.naver\?code=(\d{6})', res.text)
        names = re.findall(r'class="tltle">([^<]+)</a>', res.text)
        for c, n in zip(codes, names):
            stocks.append({'Code': c, 'Name': n, 'Market': 'KOSPI'})
    return pd.DataFrame(stocks)

# 6가지 전략 통합 분석 함수
@st.cache_data(ttl=3600)
def analyze_strategy(num):
    df = get_base_stocks()
    results = []
    end = datetime.date.today()
    start = end - datetime.timedelta(days=365)
    
    # 50개 종목만 샘플로 테스트 (속도를 위해 제한)
    for _, row in df.head(50).iterrows():
        try:
            data = fdr.DataReader(row['Code'], start, end)
            if len(data) < 100: continue
            
            curr = data['Close'].iloc[-1]
            ma20 = data['Close'].rolling(20).mean().iloc[-1]
            
            # 전략별 필터링
            if num == 1: # 찰리멍거 바닥 횡보
                if curr < data['Close'].max() * 0.6 and (data['Close'].max() - data['Close'].min()) / data['Close'].min() < 0.2:
                    results.append(row)
            elif num == 2: # RSI 과매도
                delta = data['Close'].diff()
                rsi = 100 - (100 / (1 + (delta.clip(lower=0).rolling(14).mean() / (-delta.clip(upper=0)).rolling(14).mean())))
                if rsi.iloc[-1] < 25: results.append(row)
            elif num == 3: # 거래량 급증
                if data['Volume'].iloc[-1] > data['Volume'].rolling(20).mean().iloc[-1] * 10:
                    results.append(row)
            elif num == 5: # 볼린저 밴드 상단
                upper = data['Close'].rolling(20).mean() + (data['Close'].rolling(20).std() * 2)
                if curr > upper.iloc[-1]: results.append(row)
            elif num == 6: # 엔벨로프
                if curr < ma20 * 0.8: results.append(row)
        except: continue
    return pd.DataFrame(results)

# UI 구성
tab1, tab2, tab3 = st.tabs(["최신뉴스", "Study", "조건검색"])
with tab3:
    left, right = st.columns([1, 4])
    with left:
        strategies = {1: "1. 찰리멍거 횡보", 2: "2. RSI 과매도", 3: "3. 거래량 급증", 4: "4. 가성비 우량주", 5: "5. 볼린저 상단", 6: "6. 엔벨로프 낙폭"}
        for num, name in strategies.items():
            if st.button(name): st.session_state.choice = num
        if st.button("🚀 자동 전체 검색"):
            for i in range(1, 7): analyze_strategy(i)
            st.success("완료!")
    with right:
        if 'choice' in st.session_state:
            res = analyze_strategy(st.session_state.choice)
            st.dataframe(res)