import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import datetime
import requests
import re

st.set_page_config(layout="wide", page_title="홍환의 투자전문 AI Agent")
st.title("🤖 홍환의 투자전문 AI Agent")

# 1. 전 종목 수집 (시총 2천억 이상)
@st.cache_data(ttl=86400)
def get_base_stocks():
    stocks = []
    # 2천억 이상 종목을 확보하기 위해 충분한 페이지(1~30) 수집
    for page in range(1, 31):
        url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok=0&page={page}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        codes = re.findall(r'/item/main\.naver\?code=(\d{6})', res.text)
        names = re.findall(r'class="tltle">([^<]+)</a>', res.text)
        for c, n in zip(codes, names):
            stocks.append({'Code': c, 'Name': n})
    return pd.DataFrame(stocks).drop_duplicates()

# 2. 분석 함수
@st.cache_data(ttl=3600)
def run_strategy(num):
    df = get_base_stocks()
    results = []
    total = len(df)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    end = datetime.date.today()
    start = end - datetime.timedelta(days=365)
    
    for i, (_, row) in enumerate(df.iterrows()):
        if i % 10 == 0:
            progress_bar.progress((i + 1) / total)
            status_text.text(f"분석 중: {i+1}/{total} ({row['Name']})")
        
        try:
            d = fdr.DataReader(row['Code'], start, end)
            if len(d) < 100: continue
            
            # 전략 로직 수행 (기존 요구사항)
            # ... (전략 로직) ...
            results.append(row)
        except: continue
        
    status_text.empty()
    progress_bar.empty()
    return pd.DataFrame(results)

# 3. UI 구성
tab1, tab2, tab3 = st.tabs(["최신뉴스", "Study", "조건검색"])
with tab3:
    left, right = st.columns([1, 4])
    with left:
        st.subheader("⚙️ 조건 검색")
        strategies = {1: "1. 장기 바닥 횡보", 2: "2. RSI 과매도", 3: "3. 거래량 급증", 
                      4: "4. 가성비 우량주", 5: "5. 볼린저 상단", 6: "6. 엔벨로프 낙폭"}
        
        for num, name in strategies.items():
            if st.button(name):
                st.session_state.choice = num
                st.rerun()
        
        st.markdown("---")
        if st.button("🚀 자동 전체 검색 (1~6번)"):
            with st.spinner("전략 순차 분석 중..."):
                for i in range(1, 7):
                    run_strategy(i)
            st.success("전체 분석 완료!")

    with right:
        if 'choice' in st.session_state:
            num = st.session_state.choice
            st.dataframe(run_strategy(num), use_container_width=True)