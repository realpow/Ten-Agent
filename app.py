import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import datetime
import requests
import re

st.set_page_config(layout="wide", page_title="홍환의 투자전문 AI Agent")

# 1. 타이틀 및 날짜 표시
st.title("🤖 홍환의 투자전문 AI Agent")
today = datetime.date.today().strftime("%Y년 %m월 %d일")
st.markdown(f"**기준일자: {today}**")
st.markdown("---")

# 2. 전 종목 수집 (캐싱 적용)
@st.cache_data(ttl=43200)
def get_base_stocks():
    stocks = []
    # 페이지 범위 1~25 (전 종목)
    for sosok in [0, 1]:
        for page in range(1, 25):
            url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            codes = re.findall(r'/item/main\.naver\?code=(\d{6})', res.text)
            names = re.findall(r'class="tltle">([^<]+)</a>', res.text)
            for c, n in zip(codes, names):
                stocks.append({'Code': c, 'Name': n})
    return pd.DataFrame(stocks).drop_duplicates()

# 3. 전략별 독립 캐싱 분석 함수 (버튼 연타 방지)
@st.cache_data(ttl=43200)
def run_strategy_cached(strategy_num):
    df = get_base_stocks()
    results = []
    total = len(df)
    
    # 분석 상태 표시창
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    end = datetime.date.today()
    for i, (_, row) in enumerate(df.iterrows()):
        if i % 20 == 0:
            progress_bar.progress((i + 1) / total)
            status_text.text(f"📊 전략 {strategy_num} 분석 중: {i+1} / {total}개 종목")
        
        try:
            d = fdr.DataReader(row['Code'], end - datetime.timedelta(days=150))
            if len(d) < 60: continue
            curr = d['Close'].iloc[-1]
            ma20 = d['Close'].rolling(20).mean().iloc[-1]
            
            if strategy_num == 1 and curr < d['Close'].max() * 0.6: 
                results.append({"종목명": row['Name'], "현재가": int(curr)})
            elif strategy_num == 2:
                delta = d['Close'].diff()
                rsi = 100 - (100 / (1 + (delta.clip(lower=0).rolling(14).mean() / (-delta.clip(upper=0)).rolling(14).mean())))
                if rsi.iloc[-1] <= 25: results.append({"종목명": row['Name'], "RSI": round(rsi.iloc[-1],1)})
            elif strategy_num == 3 and d['Volume'].iloc[-1] > d['Volume'].rolling(20).mean().iloc[-1] * 3:
                results.append({"종목명": row['Name'], "현재가": int(curr)})
            elif strategy_num == 5 and curr > (ma20 + d['Close'].rolling(20).std().iloc[-1] * 2):
                results.append({"종목명": row['Name'], "현재가": int(curr)})
            elif strategy_num == 6 and curr <= ma20 * 0.85:
                results.append({"종목명": row['Name'], "현재가": int(curr)})
        except: continue
    
    progress_bar.empty()
    status_text.text(f"✅ 전략 {strategy_num} 분석 완료! 총 {len(results)}개 발견.")
    return pd.DataFrame(results)

# 4. 레이아웃 (왼쪽 버튼, 오른쪽 결과)
left_col, right_col = st.columns([1, 4])

with left_col:
    st.subheader("⚙️ 조건 검색")
    strategies = {1: "👴 1. 바닥 횡보", 2: "📉 2. RSI 과매도", 3: "🚀 3. 거래량 급증", 
                  4: "💎 4. 가성비 우량주", 5: "💥 5. 볼린저 돌파", 6: "🛡️ 6. 엔벨로프 타점"}
    
    for num, name in strategies.items():
        if st.button(name, key=f"btn_{num}"):
            st.session_state.choice = num

with right_col:
    st.subheader("📊 분석 결과 시트")
    if 'choice' in st.session_state:
        num = st.session_state.choice
        if num == 4:
            st.info("전략 4번은 현재 재무 데이터 업데이트 대기 중입니다.")
        else:
            result_df = run_strategy_cached(num)
            st.dataframe(result_df, use_container_width=True)
    else:
        st.info("왼쪽에서 분석할 조건을 선택해주세요.")