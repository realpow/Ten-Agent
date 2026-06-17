import streamlit as st
import pandas as pd
from pykrx import stock
import datetime

st.set_page_config(layout="wide", page_title="진강의 투자전문 AI Agent")
st.title("🤖 진강의 투자전문 AI Agent")

# 1. 시총 2천억 이상 전 종목 수집 (캐싱)
@st.cache_data(ttl=86400)
def get_base_stocks():
    tickers = stock.get_market_ticker_list(market="ALL")
    stocks = []
    # 전체 종목 대상으로 필터링
    for ticker in tickers:
        name = stock.get_market_ticker_name(ticker)
        mcap = stock.get_market_cap(ticker)
        if mcap >= 200000000000: # 2천억 이상
            stocks.append({'Code': ticker, 'Name': name})
    return pd.DataFrame(stocks)

# 2. 분석 함수 (전체 종목 대상)
def run_full_analysis():
    df = get_base_stocks()
    results = []
    total = len(df)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 1년 전 날짜 설정
    today = datetime.datetime.now().strftime("%Y%m%d")
    one_year_ago = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime("%Y%m%d")
    
    for i, (_, row) in enumerate(df.iterrows()):
        progress_bar.progress((i + 1) / total)
        status_text.text(f"진강님, 전체 {total}개 종목 중 {i+1}번째 분석 중: {row['Name']}")
        
        try:
            # 1년치 종가 데이터 가져오기
            df_price = stock.get_market_ohlcv(one_year_ago, today, row['Code'])
            if len(df_price) < 200: continue
            
            curr = df_price['종가'].iloc[-1]
            min_price = df_price['종가'].min()
            
            # 찰리멍거식 바닥권 조건: 현재가가 1년 최저가 대비 20% 이내
            if curr <= min_price * 1.2:
                results.append({'종목명': row['Name'], '현재가': curr, '최저가': min_price})
        except:
            continue
            
    status_text.text(f"✅ 분석 완료! 총 {len(results)}개 종목 발견.")
    return pd.DataFrame(results)

# 3. UI 구성
st.subheader("조건 검색")
if st.button("🚀 전 종목 장기 바닥 횡보 분석 시작"):
    st.session_state.result_full = run_full_analysis()

if 'result_full' in st.session_state:
    st.dataframe(st.session_state.result_full, use_container_width=True)
else:
    st.write("버튼을 누르면 시총 2천억 이상 전 종목을 분석합니다.")