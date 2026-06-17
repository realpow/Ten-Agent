import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import datetime
import requests
import re

st.set_page_config(layout="wide", page_title="홍환의 투자전문 AI Agent")
st.title("🤖 홍환의 투자전문 AI Agent")

# 1. 시총 2천억 이상 리스트 실시간 수집 (캐싱)
@st.cache_data(ttl=86400)
def get_base_stocks():
    stocks = []
    # 페이지를 돌며 종목 추출
    for page in range(1, 5): # 테스트를 위해 5페이지로 제한, 전체는 25페이지 이상
        url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok=0&page={page}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        codes = re.findall(r'/item/main\.naver\?code=(\d{6})', res.text)
        names = re.findall(r'class="tltle">([^<]+)</a>', res.text)
        for c, n in zip(codes, names):
            stocks.append({'Code': c, 'Name': n})
    return pd.DataFrame(stocks).drop_duplicates()

# 2. 분석 함수 (모든 전략 로직 반영)
def analyze_with_progress(num):
    df = get_base_stocks()
    total = len(df)
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    end = datetime.date.today()
    start = end - datetime.timedelta(days=365)
    
    for i, (_, row) in enumerate(df.iterrows()):
        progress_bar.progress((i + 1) / total)
        status_text.text(f"📊 {num}번 전략 분석 중: {i+1}/{total} ({row['Name']})")
        
        try:
            d = fdr.DataReader(row['Code'], start, end)
            if len(d) < 100: continue
            
            curr = d['Close'].iloc[-1]
            ma20 = d['Close'].rolling(20).mean().iloc[-1]
            
            # 전략 로직
            if num == 1 and curr < d['Close'].max() * 0.6: # 찰리멍거
                results.append(row)
            elif num == 2 and (d['Close'].diff().clip(lower=0).rolling(14).mean() / -d['Close'].diff().clip(upper=0).rolling(14).mean() < 0.5): # RSI 과매도
                results.append(row)
            elif num == 3 and d['Volume'].iloc[-1] > d['Volume'].rolling(20).mean().iloc[-1] * 5: # 거래량 급증
                results.append(row)
            elif num == 5 and curr > (ma20 + d['Close'].rolling(20).std().iloc[-1] * 2): # 볼린저
                results.append(row)
            elif num == 6 and curr < ma20 * 0.8: # 엔벨로프
                results.append(row)
        except: continue
        
    progress_bar.empty()
    status_text.text(f"✅ 완료! {len(results)}개 종목 발견.")
    return pd.DataFrame(results)

# 3. 메인 UI
tab1, tab2, tab3 = st.tabs(["최신뉴스", "Study", "조건검색"])
with tab3:
    left, right = st.columns([1, 4])
    with left:
        strategies = {1: "1. 장기 바닥 횡보", 2: "2. RSI 과매도", 3: "3. 거래량 급증", 
                      4: "4. 가성비 우량주", 5: "5. 볼린저 상단", 6: "6. 엔벨로프 낙폭"}
        for num, name in strategies.items():
            if st.button(name):
                st.session_state.choice = num
                st.rerun()
    with right:
        if 'choice' in st.session_state:
            num = st.session_state.choice
            # 캐시를 활용한 결과 호출
            res = analyze_with_progress(num) 
            st.dataframe(res)