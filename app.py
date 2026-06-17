import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import datetime
import requests
import re
import io
import warnings
warnings.filterwarnings('ignore')

# 페이지 기본 설정 (넓은 화면 모드)
st.set_page_config(layout="wide")

# RSI 계산 함수
def calculate_rsi(series, period=14):
    delta = series.diff()
    avg_gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    avg_loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# 타이틀 및 소개
st.title("🤖 홍환님의 AI 종합 투자 전문 에이전트 v2.0")
st.markdown("---")
st.sidebar.header("⚙️ 시스템 제어판")
st.sidebar.write("원하는 투자 전략 버튼을 누르면 시총 2천억 이상 기업 전 종목을 실시간 퀀트 분석합니다.")

# [💡 성능 고도화] 기본 주식 정보 수집 시 PER, ROE까지 초고속 동시 수집
@st.cache_data(ttl=3600)
def get_base_stocks():
    stocks = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    for sosok in [0, 1]: # 0: 코스피, 1: 코스닥
        market_name = 'KOSPI' if sosok == 0 else 'KOSDAQ'
        for page in range(1, 25): # 시총 상위권 집중 수집
            url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}"
            res = requests.get(url, headers=headers)
            html = res.content.decode('euc-kr', errors='ignore')
            
            page_codes = re.findall(r'href="/item/main\.naver\?code=(\d{6})"[^>]* class="tltle">([^<]+)</a>', html)
            if not page_codes: break
                
            dfs = pd.read_html(io.StringIO(html))
            df_table = dfs[1].dropna(subset=['종목명'])
            
            # 컬럼 매칭 (시가총액, PER, ROE)
            marcap_col = next((c for c in df_table.columns if '시가총액' in str(c)), None)
            per_col = next((c for c in df_table.columns if 'PER' in str(c)), None)
            roe_col = next((c for c in df_table.columns if 'ROE' in str(c)), None)
            
            for (code, name), (_, row) in zip(page_codes, df_table.iterrows()):
                marcap_val = row[marcap_col] if marcap_col else 0
                if pd.isna(marcap_val): continue
                
                if isinstance(marcap_val, str):
                    marcap_val = int(re.sub(r'[^0-9]', '', marcap_val))
                else:
                    marcap_val = int(marcap_val)
                
                # 네이버 단위 '억 원' 기준 2,000억 이상 조건
                if marcap_val >= 2000:
                    # PER, ROE 정제
                    try: per_float = float(row[per_col]) if per_col and not pd.isna(row[per_col]) else None
                    except: per_float = None
                    try: roe_float = float(row[roe_col]) if roe_col and not pd.isna(row[roe_col]) else None
                    except: roe_float = None
                    
                    stocks.append({
                        'Code': code, 'Name': name, 'Market': market_name,
                        'MarCap': marcap_val * 100000000, 'PER': per_float, 'ROE': roe_float
                    })
                else:
                    break
    return pd.DataFrame(stocks)

df_base = get_base_stocks()
st.sidebar.info(f"현재 실시간 분석 대상 종목: **{len(df_base)}개**")

# ----------------------------------------------------
# 🏢 대시보드 화면 배치 (3개 컬럼씩 2줄 격자 구조)
# ----------------------------------------------------
row1_col1, row1_col2, row1_col3 = st.columns(3)
row2_col1, row2_col2, row2_col3 = st.columns(3)

# --- [상단 1열] 찰리 멍거 바닥 횡보주 ---
with row1_col1:
    st.subheader("👴 1. 찰리멍거 바닥 횡보")
    st.caption("3개월~2년간 바닥권 밀집 장기 횡보 기업")
    if st.button("🔍 바닥 횡보주 검색"):
        results = []
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=365 * 2)
        p_bar = st.progress(0); s_text = st.empty()
        
        for i, (_, row) in enumerate(df_base.iterrows()):
            p_bar.progress(int((i + 1) / len(df_base) * 100))
            s_text.text(f"분석: {row['Name']}")
            try:
                df = fdr.DataReader(row['Code'], start_date, end_date)
                if len(df) < 250: continue
                current = int(df['Close'].iloc[-1])
                price_1y = df['Close'].tail(240)
                if current < price_1y.max() * 0.6 and current < price_1y.min() * 1.25:
                    price_recent = df['Close'].tail(90)
                    if ((price_recent.max() - price_recent.min()) / price_recent.min()) < 0.20:
                        ma5 = df['Close'].rolling(5).mean().iloc[-1]
                        ma10 = df['Close'].rolling(10).mean().iloc[-1]
                        ma20 = df['Close'].rolling(20).mean().iloc[-1]
                        if ((max([ma5, ma10, ma20]) - min([ma5, ma10, ma20])) / min([ma5, ma10, ma20])) < 0.04:
                            results.append({"종목코드": row['Code'], "종목명": row['Name'], "시장": row['Market'], "현재가": current})
            except: continue
        s_text.success("✅ 완료!")
        st.dataframe(pd.DataFrame(results) if results else "조건에 맞는 종목이 없습니다.", use_container_width=True)

# --- [상단 2열] 일봉/주봉 RSI 과매도 ---
with row1_col2:
    st.subheader("📉 2. 일봉&주봉 RSI 과매도")
    st.caption("일봉 RSI 25 이하 & 주봉 RSI 30 이하 과매도")
    if st.button("🔍 RSI 과매도주 검색"):
        results = []
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=365 * 2)
        p_bar = st.progress(0); s_text = st.empty()
        
        for i, (_, row) in enumerate(df_base.iterrows()):
            p_bar.progress(int((i + 1) / len(df_base) * 100))
            s_text.text(f"분석: {row['Name']}")
            try:
                df_daily = fdr.DataReader(row['Code'], start_date, end_date)
                if len(df_daily) < 100: continue
                df_daily['RSI'] = calculate_rsi(df_daily['Close'], 14)
                rsi_d = df_daily['RSI'].iloc[-1]
                
                df_weekly = df_daily.resample('W').agg({'Close': 'last'})
                df_weekly['RSI_W'] = calculate_rsi(df_weekly['Close'], 14)
                rsi_w = df_weekly['RSI_W'].iloc[-1]
                
                if rsi_d <= 25 and rsi_w <= 30:
                    results.append({"종목코드": row['Code'], "종목명": row['Name'], "현재가": int(df_daily['Close'].iloc[-1]), "일봉RSI": round(rsi_d,1), "주봉RSI": round(rsi_w,1)})
            except: continue
        s_text.success("✅ 완료!")
        st.dataframe(pd.DataFrame(results) if results else "조건에 맞는 종목이 없습니다.", use_container_width=True)

# --- [상단 3열] 거래량 분출 정배열 초입 (신규 전략 1) ---
with row1_col3:
    st.subheader("🚀 3. 거래량 분출 정배열 초입")
    st.caption("이평선 정배열(5>20>60) 돌파 + 전일비 거래량 200% 폭발")
    if st.button("🔍 정배열 초입주 검색"):
        results = []
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=150)
        p_bar = st.progress(0); s_text = st.empty()
        
        for i, (_, row) in enumerate(df_base.iterrows()):
            p_bar.progress(int((i + 1) / len(df_base) * 100))
            s_text.text(f"분석: {row['Name']}")
            try:
                df = fdr.DataReader(row['Code'], start_date, end_date)
                if len(df) < 65: continue
                
                ma5 = df['Close'].rolling(5).mean().iloc[-1]
                ma20 = df['Close'].rolling(20).mean().iloc[-1]
                ma60 = df['Close'].rolling(60).mean().iloc[-1]
                
                vol_ma5 = df['Volume'].rolling(5).mean().iloc[-2] # 직전 5일 평균 거래량
                today_vol = df['Volume'].iloc[-1]
                current_price = df['Close'].iloc[-1]
                
                # 조건: 정배열 구조 형성 및 오늘 종가가 5일선 위에 안착 + 거래량 평소대비 2배 폭발 (세력 진입 추정)
                if ma5 > ma20 and ma20 > ma60 and current_price > ma5:
                    if today_vol > vol_ma5 * 2 and df['Change'].iloc[-1] > 0:
                        results.append({"종목코드": row['Code'], "종목명": row['Name'], "현재가": int(current_price), "당일등락률(%)": round(df['Change'].iloc[-1]*100, 2)})
            except: continue
        s_text.success("✅ 완료!")
        st.dataframe(pd.DataFrame(results) if results else "조건에 맞는 종목이 없습니다.", use_container_width=True)


# --- [하단 1열] 가성비 알짜 우량주 (신규 전략 2) ---
with row2_col1:
    st.subheader("💎 4. 가성비 알짜 우량주")
    st.caption("ROE 10% 이상 고성장 & PER 15배 이하 철저 저평가 알짜주")
    if st.button("🔍 가성비 우량주 추출"):
        # 미리 수집된 베이스 데이터에서 즉시 필터링하므로 루프 없이 초고속 가동!
        filtered = df_base[(df_base['ROE'] >= 10) & (df_base['PER'] > 0) & (df_base['PER'] <= 15)]
        filtered = filtered.sort_values(by='ROE', ascending=False) # 고ROE 순 정렬
        
        results = filtered[['Code', 'Name', 'Market', 'PER', 'ROE']].rename(
            columns={'Code': '종목코드', 'Name': '종목명', 'Market': '시장', 'PER': 'PER(배)', 'ROE': 'ROE(%)'}
        )
        st.success("✅ 즉시 추출 완료!")
        st.dataframe(results if not results.empty else "조건에 맞는 종목이 없습니다.", use_container_width=True)

# --- [하단 2열] 볼린저 밴드 상단 돌파 (신규 전략 3) ---
with row2_col2:
    st.subheader("💥 5. 볼린저 밴드 상단 돌파")
    st.caption("변동성 상단(20, 2) 강한 돌파 + 거래량 급증 대시세 신호")
    if st.button("🔍 볼린저 돌파주 검색"):
        results = []
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=100)
        p_bar = st.progress(0); s_text = st.empty()
        
        for i, (_, row) in enumerate(df_base.iterrows()):
            p_bar.progress(int((i + 1) / len(df_base) * 100))
            s_text.text(f"분석: {row['Name']}")
            try:
                df = fdr.DataReader(row['Code'], start_date, end_date)
                if len(df) < 25: continue
                
                ma20 = df['Close'].rolling(20).mean()
                std20 = df['Close'].rolling(20).std()
                upper_bb = ma20 + (std20 * 2)
                
                current_price = df['Close'].iloc[-1]
                prev_price = df['Close'].iloc[-2]
                
                # 오늘 상단밴드 돌파, 어제는 상단밴드 아래였던 종목 + 거래량 폭발
                if current_price > upper_bb.iloc[-1] and prev_price <= upper_bb.iloc[-2]:
                    vol_ma5 = df['Volume'].rolling(5).mean().iloc[-2]
                    if df['Volume'].iloc[-1] > vol_ma5 * 2.5:
                        results.append({"종목코드": row['Code'], "종목명": row['Name'], "현재가": int(current_price), "상단밴드가": round(upper_bb.iloc[-1])})
            except: continue
        s_text.success("✅ 완료!")
        st.dataframe(pd.DataFrame(results) if results else "조건에 맞는 종목이 없습니다.", use_container_width=True)

# --- [하단 3열] 엔벨로프 낙폭과대 타점 (신규 전략 4) ---
with row2_col3:
    st.subheader("🛡️ 6. 엔벨로프 낙폭과대 타점")
    st.caption("20일 이평선 대비 -15% 이하 이격 발생, 기계적 반등 유력 타점")
    if st.button("🔍 엔벨로프 타점 검색"):
        results = []
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=100)
        p_bar = st.progress(0); s_text = st.empty()
        
        for i, (_, row) in enumerate(df_base.iterrows()):
            p_bar.progress(int((i + 1) / len(df_base) * 100))
            s_text.text(f"분석: {row['Name']}")
            try:
                df = fdr.DataReader(row['Code'], start_date, end_date)
                if len(df) < 25: continue
                
                ma20 = df['Close'].rolling(20).mean().iloc[-1]
                envelope_lower = ma20 * (1 - 0.15) # 하단 지지선 (-15% 이격)
                current_price = df['Close'].iloc[-1]
                
                # 현재가가 엔벨로프 하단선보다 밑으로 떨어진 극단적 과매도주 포착
                if current_price <= envelope_lower:
                    disparity = (current_price / ma20) * 100
                    results.append({
                        "종목코드": row['Code'], "종목명": row['Name'], 
                        "현재가": int(current_price), "20일선": round(ma20), "이격률(%)": round(disparity, 1)
                    })
            except: continue
        s_text.success("✅ 완료!")
        st.dataframe(pd.DataFrame(results) if results else "조건에 맞는 종목이 없습니다.", use_container_width=True)