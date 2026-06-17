import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import datetime
import requests
import re

st.set_page_config(layout="wide", page_title="홍환의 투자전문 AI Agent")
st.title("🤖 홍환의 투자전문 AI Agent")
st.markdown(f"**기준일자: {datetime.date.today().strftime('%Y년 %m월 %d일')}**")
st.markdown("---")

# 1. 전 종목 수집 (캐싱)
@st.cache_data(ttl=43200)
def get_base_stocks():
    stocks = []
    for sosok in [0, 1]:
        for page in range(1, 25):
            url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            codes = re.findall(r'/item/main\.naver\?code=(\d{6})', res.text)
            names = re.findall(r'class="tltle">([^<]+)</a>', res.text)
            for c, n in zip(codes, names):
                stocks.append({'Code': c, 'Name': n})
    return pd.DataFrame(stocks).drop_duplicates()

# 2. 분석 핵심 로직
def run_strategy(df, strategy_num):
    results = []
    total = len(df)
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    end = datetime.date.today()
    for i, (_, row) in enumerate(df.iterrows()):
        if i % 25 == 0: 
            progress_bar.progress((i + 1) / total)
            status_text.text(f"📊 분석 진행중: {i+1} / {total} ({row['Name']})")
        
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
    status_text.text(f"✅ 분석 완료! 총 {len(results)}개 종목 발견.")
    return pd.DataFrame(results)

# 3. 레이아웃: [조건 검색] 버튼 배치
left_col, right_col = st.columns([1, 4])
df_base = get_base_stocks()

with left_col:
    st.subheader("🔍 조건 검색")
    # 전략 리스트
    conditions = {1: "1. 바닥 횡보 (찰리멍거)", 2: "2. RSI 과매도", 3: "3. 거래량 급증", 
                  4: "4. 가성비 우량주", 5: "5. 볼린저 밴드 상단", 6: "6. 엔벨로프 낙폭과대"}
    
    for num, name in conditions.items():
        if st.button(name, key=f"btn_{num}"):
            st.session_state.choice = num

with right_col:
    st.subheader("📊 분석 결과 시트")
    if 'choice' in st.session_state:
        num = st.session_state.choice
        # 맨 아래줄: 선택한 전략의 상세 조건 설명
        st.markdown(f"**현재 검색 조건:** `{conditions[num]}`")
        
        if num == 4:
            st.info("전략 4번은 업데이트 대기 중입니다.")
        else:
            st.dataframe(run_strategy(df_base, num), use_container_width=True)
    else:
        st.info("왼쪽에서 검색할 조건을 선택해주세요.")