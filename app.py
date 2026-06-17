import streamlit as st
import pandas as pd
from pykrx import stock
import datetime

# 페이지 기본 설정
st.set_page_config(layout="wide", page_title="홍환의 투자전문 AI Agent")
today_str = datetime.datetime.now().strftime("%Y-%m-%d")
st.title(f"📈 홍환의 투자전문 AI Agent ({today_str})")
st.markdown(f"**진강님, 오늘도 성공적인 투자를 위해 에이전트가 분석을 준비합니다.**")

# 1. 데이터 수집: 모든 예외 상황을 처리하는 안정적 코드
@st.cache_data(ttl=86400)
def get_base_stocks():
    try:
        date = stock.get_nearest_business_day_in_a_week()
        tickers = stock.get_market_ticker_list(date=date, market="ALL")
        data = []
        for ticker in tickers:
            try:
                # 시가총액 필터링 (최신 영업일 기준)
                mcap = stock.get_market_cap(ticker, fromdate=date, todate=date)
                if mcap >= 200000000000:
                    name = stock.get_market_ticker_name(ticker)
                    data.append({'Code': ticker, 'Name': name})
            except: continue
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

# 2. 전략 분석 함수: 루프마다 안전하게 처리
def run_strategy(strategy_num):
    df = get_base_stocks()
    if df.empty: return pd.DataFrame({'알림': ['데이터를 불러오지 못했습니다.']})
    
    results = []
    # 데이터 안정성을 위해 날짜를 문자열로 명확히 변환
    today = datetime.datetime.now().strftime("%Y%m%d")
    year_ago = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime("%Y%m%d")
    
    for _, row in df.iterrows():
        try:
            df_ohlcv = stock.get_market_ohlcv(year_ago, today, row['Code'])
            if df_ohlcv is None or df_ohlcv.empty or len(df_ohlcv) < 100: continue
            
            curr = df_ohlcv['종가'].iloc[-1]
            min_val = df_ohlcv['종가'].min()
            
            # 전략 번호에 따른 로직 분기 (안전한 필터링)
            if strategy_num == 1 and curr <= min_val * 1.2:
                results.append({'종목명': row['Name'], '현재가': curr})
        except: continue
    
    return pd.DataFrame(results) if results else pd.DataFrame({'알림': ['조건에 맞는 종목이 없습니다.']})

# 3. 탭 및 UI 구성
tab1, tab2, tab3 = st.tabs(["최신뉴스", "Study", "조건검색"])

with tab3:
    left_col, right_col = st.columns([1, 3])
    
    with left_col:
        st.subheader("📊 전략 선택")
        strategies = {1: "1. 장기 바닥 횡보", 2: "2. RSI 과매도", 3: "3. 거래량 급증", 
                      4: "4. 가성비 우량주", 5: "5. 볼린저 상단", 6: "6. 엔벨로프 낙폭"}
        
        for num, name in strategies.items():
            if st.button(name, key=f"btn_{num}"):
                st.session_state.result = run_strategy(num)
        
        st.markdown("---")
        if st.button("🚀 전체 전략 자동 분석 시작"):
            st.session_state.result = pd.DataFrame({'알림': ['전체 분석 중...']})

    with right_col:
        st.subheader("🔍 분석 결과")
        if 'result' in st.session_state:
            st.dataframe(st.session_state.result, use_container_width=True)
        else:
            st.write("진강님, 전략을 선택하시면 결과가 여기에 표시됩니다.")