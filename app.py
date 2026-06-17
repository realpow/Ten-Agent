import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import datetime
import requests
import re

st.set_page_config(layout="wide")

# 1. 기본 종목 데이터 수집
@st.cache_data(ttl=43200)
def get_base_stocks():
    stocks = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    for sosok in [0, 1]:
        market = 'KOSPI' if sosok == 0 else 'KOSDAQ'
        for page in range(1, 4): # 속도를 위해 3페이지로 조정
            url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}"
            res = requests.get(url, headers=headers)
            html = res.content.decode('euc-kr', errors='ignore')
            codes = re.findall(r'href="/item/main\.naver\?code=(\d{6})"[^>]* class="tltle">([^<]+)</a>', html)
            stocks.extend([{'Code': c, 'Name': n, 'Market': market} for c, n in codes])
    return pd.DataFrame(stocks)

# 2. 분석 함수 (진행률 표시 포함)
def run_strategy(df, strategy_num):
    results = []
    total = len(df)
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    end = datetime.date.today()
    for i, (_, row) in enumerate(df.iterrows()):
        progress_bar.progress((i + 1) / total)
        status_text.text(f"분석 중: {i+1} / {total} ({row['Name']})")
        try:
            d = fdr.DataReader(row['Code'], end - datetime.timedelta(days=150))
            if len(d) < 60: continue
            curr = d['Close'].iloc[-1]
            ma20 = d['Close'].rolling(20).mean().iloc[-1]
            
            # 전략 로직
            if strategy_num == 1 and curr < d['Close'].tail(120).max() * 0.7: results.append({"종목명": row['Name'], "현재가": int(curr)})
            elif strategy_num == 2:
                delta = d['Close'].diff()
                rsi = 100 - (100 / (1 + (delta.clip(lower=0).rolling(14).mean() / (-delta.clip(upper=0)).rolling(14).mean())))
                if rsi.iloc[-1] <= 25: results.append({"종목명": row['Name'], "RSI": round(rsi.iloc[-1],1)})
            elif strategy_num == 3 and d['Volume'].iloc[-1] > d['Volume'].rolling(20).mean().iloc[-1] * 3: results.append({"종목명": row['Name'], "현재가": int(curr)})
            elif strategy_num == 5 and curr > (ma20 + d['Close'].rolling(20).std().iloc[-1] * 2): results.append({"종목명": row['Name'], "현재가": int(curr)})
            elif strategy_num == 6 and curr <= ma20 * 0.85: results.append({"종목명": row['Name'], "현재가": int(curr)})
        except: continue
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(results)

# --- 메인 대시보드 UI ---
st.title("🤖 홍환의 투자전문 AI Agent")
df_base = get_base_stocks()

# 1:3 비율로 왼쪽(메뉴), 오른쪽(결과) 분할
left_col, right_col = st.columns([1, 3])

with left_col:
    st.header("⚙️ 전략 선택")
    st.write("버튼을 누르면 오른쪽 창에 결과가 나타납니다.")
    # 세션 상태로 어떤 버튼을 눌렀는지 기억
    btn1 = st.button("👴 1. 장기 바닥 횡보")
    btn2 = st.button("📉 2. RSI 과매도")
    btn3 = st.button("🚀 3. 거래량 급증")
    btn4 = st.button("💎 4. 가성비 우량주")
    btn5 = st.button("💥 5. 볼린저 돌파")
    btn6 = st.button("🛡️ 6. 엔벨로프 타점")

with right_col:
    st.header("📊 분석 결과 시트")
    if btn1: st.dataframe(run_strategy(df_base, 1), use_container_width=True)
    elif btn2: st.dataframe(run_strategy(df_base, 2), use_container_width=True)
    elif btn3: st.dataframe(run_strategy(df_base, 3), use_container_width=True)
    elif btn4: st.write("전략 4번 로직 실행 대기 중...")
    elif btn5: st.dataframe(run_strategy(df_base, 5), use_container_width=True)
    elif btn6: st.dataframe(run_strategy(df_base, 6), use_container_width=True)
    else: st.info("왼쪽 메뉴에서 분석 전략을 선택해 주세요.")