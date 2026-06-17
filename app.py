import streamlit as st
import pandas as pd
from pykrx import stock
import datetime

# 1. 페이지 설정 및 제목 (날짜 포함)
today_str = datetime.datetime.now().strftime("%Y-%m-%d")
st.set_page_config(layout="wide", page_title="홍환의 투자전문 AI Agent")
st.title(f"📈 홍환의 투자전문 AI Agent ({today_str})")
st.markdown(f"**진강님, 오늘도 성공적인 투자를 위해 에이전트가 분석을 준비합니다.**")

# 2. 데이터 수집 함수
@st.cache_data(ttl=86400)
def get_base_stocks():
    tickers = stock.get_market_ticker_list(market="ALL")
    data = []
    for ticker in tickers:
        try:
            mcap = stock.get_market_cap(ticker)
            if mcap >= 200000000000:
                name = stock.get_market_ticker_name(ticker)
                data.append({'Code': ticker, 'Name': name})
        except: continue
    return pd.DataFrame(data)

# 3. 전략 분석 로직
def run_strategy(strategy_num):
    df = get_base_stocks()
    results = []
    today = datetime.datetime.now().strftime("%Y%m%d")
    year_ago = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime("%Y%m%d")
    
    for _, row in df.iterrows():
        try:
            df_ohlcv = stock.get_market_ohlcv(year_ago, today, row['Code'])
            if df_ohlcv.empty: continue
            curr = df_ohlcv['종가'].iloc[-1]
            
            # 전략 1번 예시 로직 (나머지 전략은 번호별로 로직 추가)
            if strategy_num == 1 and curr <= df_ohlcv['종가'].min() * 1.2:
                results.append({'종목명': row['Name'], '현재가': curr})
        except: continue
    return pd.DataFrame(results)

# 4. 탭 구성
tab1, tab2, tab3 = st.tabs(["최신뉴스", "Study", "조건검색"])

with tab3:
    # 화면을 좌우로 분할 (왼쪽: 버튼, 오른쪽: 결과)
    left_col, right_col = st.columns([1, 3])
    
    with left_col:
        st.subheader("📊 전략 선택")
        strategies = {1: "1. 장기 바닥 횡보", 2: "2. RSI 과매도", 3: "3. 거래량 급증", 
                      4: "4. 가성비 우량주", 5: "5. 볼린저 상단", 6: "6. 엔벨로프 낙폭"}
        
        for num, name in strategies.items():
            if st.button(name):
                st.session_state.result = run_strategy(num)
        
        st.markdown("---")
        st.subheader("🚀 자동화")
        if st.button("전체 전략 자동 분석 시작"):
            st.session_state.result = pd.DataFrame({'알림': ['전체 분석 로직 실행 중...']})

    with right_col:
        st.subheader("🔍 분석 결과")
        if 'result' in st.session_state and not st.session_state.result.empty:
            st.dataframe(st.session_state.result, use_container_width=True)
        else:
            st.write("진강님, 전략을 선택하시면 결과가 여기에 표시됩니다.")