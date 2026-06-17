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
st.title("🤖 홍환님의 AI 종합 투자 에이전트")
st.markdown("---")
st.sidebar.header("⚙️ 검색 설정")
st.sidebar.write("두 가지 퀀트 엔진 중 원하는 전략의 버튼을 누르면 전 종목을 실시간 분석합니다.")

# [💡 우회 패치] 클라우드 서버 차단을 막기 위해 네이버 금융을 통해 시총 2천억 이상 안정적 수집
@st.cache_data(ttl=3600) # 1시간 동안 데이터 캐싱
def get_base_stocks():
    stocks = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    for sosok in [0, 1]: # 0: 코스피, 1: 코스닥
        market_name = 'KOSPI' if sosok == 0 else 'KOSDAQ'
        for page in range(1, 25): # 상위 페이지 집중 탐색
            url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}"
            res = requests.get(url, headers=headers)
            html = res.content.decode('euc-kr', errors='ignore')
            
            # 6자리 종목코드와 종목명 추출
            page_codes = re.findall(r'href="/item/main\.naver\?code=(\d{6})"[^>]* class="tltle">([^<]+)</a>', html)
            if not page_codes:
                break
                
            # 테이블 파싱
            dfs = pd.read_html(io.StringIO(html))
            df_table = dfs[1].dropna(subset=['종목명'])
            
            # 시가총액 컬럼 매칭
            marcap_col = None
            for c in df_table.columns:
                if '시가총액' in str(c):
                    marcap_col = c
                    break
            
            # 코드와 데이터 결합 및 2천억 필터링
            for (code, name), (_, row) in zip(page_codes, df_table.iterrows()):
                marcap_val = row[marcap_col] if marcap_col else 0
                if pd.isna(marcap_val): continue
                
                if isinstance(marcap_val, str):
                    marcap_val = int(re.sub(r'[^0-9]', '', marcap_val))
                elif isinstance(marcap_val, (int, float)):
                    marcap_val = int(marcap_val)
                
                # 네이버 시가총액 단위는 '억 원'이므로 2000(억) 이상만 필터링
                if marcap_val >= 2000:
                    stocks.append({
                        'Code': code,
                        'Name': name,
                        'Market': market_name,
                        'MarCap': marcap_val * 100000000 # 원 단위 환산
                    })
                else:
                    break # 시총 순 정렬이므로 2천억 미만이 나오면 해당 시장 종료
                    
    return pd.DataFrame(stocks), 'MarCap'

df_base, marcap_column = get_base_stocks()
st.sidebar.info(f"현재 분석 대상 종목 (시총 2천억 이상): **{len(df_base)}개**")

# 화면을 반으로 쪼개서 버튼 배치하기
col1, col2 = st.columns(2)

# ----------------------------------------------------
# 👴 버튼 1: 찰리 멍거 바닥 횡보주 검색 엔진
# ----------------------------------------------------
with col1:
    st.subheader("👴 1. 찰리 멍거 스타일 바닥 횡보주")
    st.caption("최소 3개월~2년간 바닥권에서 에너지를 모으며 장기 횡보하는 종목")
    
    if st.button("🔍 바닥 횡보주 검색 시작"):
        munger_stocks = []
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=365 * 2)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, (index, row) in enumerate(df_base.iterrows()):
            pct = int((i + 1) / len(df_base) * 100)
            progress_bar.progress(pct)
            status_text.text(f"분석 중: {row['Name']} ({i+1}/{len(df_base)})")
            
            try:
                df = fdr.DataReader(row['Code'], start_date, end_date)
                if len(df) < 250: continue
                    
                current_price = int(df['Close'].iloc[-1])
                ma5 = df['Close'].rolling(5).mean().iloc[-1]
                ma10 = df['Close'].rolling(10).mean().iloc[-1]
                ma20 = df['Close'].rolling(20).mean().iloc[-1]
                
                # 조건 A (바닥권)
                price_1y = df['Close'].tail(240)
                max_1y = price_1y.max()
                min_1y = price_1y.min()
                is_bottom = (current_price < max_1y * 0.6) and (current_price < min_1y * 1.25)
                
                # 조건 B (횡보)
                price_recent = df['Close'].tail(90)
                is_sideways = ((price_recent.max() - price_recent.min()) / price_recent.min()) < 0.20
                
                # 조건 C (이평선 밀집)
                ma_list = [ma5, ma10, ma20]
                is_ma_converged = ((max(ma_list) - min(ma_list)) / min(ma_list)) < 0.04
                
                if is_bottom and is_sideways and is_ma_converged:
                    munger_stocks.append({
                        "종목코드": row['Code'], "종목명": row['Name'], "시장": row['Market'],
                        "현재가": current_price, "5일선": round(ma5), "10일선": round(ma10), "20일선": round(ma20)
                    })
            except: continue
            
        status_text.success("✅ 검색 완료!")
        if munger_stocks:
            st.dataframe(pd.DataFrame(munger_stocks), use_container_width=True)
        else:
            st.warning("😭 조건에 맞는 바닥 횡보 종목이 현재 없습니다.")

# ----------------------------------------------------
# 📉 버튼 2: 일봉/주봉 RSI 과매도 검색 엔진
# ----------------------------------------------------
with col2:
    st.subheader("📉 2. 일봉 & 주봉 RSI 동시 과매도")
    st.caption("일봉 RSI 25 이하 이면서 주봉 RSI 30 이하인 낙폭 과대 보물주")
    
    if st.button("🔍 RSI 과매도주 검색 시작"):
        rsi_stocks = []
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=365 * 2)
        
        progress_bar2 = st.progress(0)
        status_text2 = st.empty()
        
        for i, (index, row) in enumerate(df_base.iterrows()):
            pct = int((i + 1) / len(df_base) * 100)
            progress_bar2.progress(pct)
            status_text2.text(f"분석 중: {row['Name']} ({i+1}/{len(df_base)})")
            
            try:
                df_daily = fdr.DataReader(row['Code'], start_date, end_date)
                if len(df_daily) < 100: continue
                    
                current_price = int(df_daily['Close'].iloc[-1])
                
                # 일봉 RSI
                df_daily['RSI_Daily'] = calculate_rsi(df_daily['Close'], period=14)
                rsi_daily_now = df_daily['RSI_Daily'].iloc[-1]
                
                # 주봉 RSI 변환
                df_weekly = df_daily.resample('W').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'})
                df_weekly['RSI_Weekly'] = calculate_rsi(df_weekly['Close'], period=14)
                rsi_weekly_now = df_weekly['RSI_Weekly'].iloc[-1]
                
                if rsi_daily_now <= 25 and rsi_weekly_now <= 30:
                    rsi_stocks.append({
                        "종목코드": row['Code'], "종목명": row['Name'], "시장": row['Market'],
                        "현재가": current_price, "일봉 RSI": round(rsi_daily_now, 2), "주봉 RSI": round(rsi_weekly_now, 2)
                    })
            except: continue
            
        status_text2.success("✅ 검색 완료!")
        if rsi_stocks:
            st.dataframe(pd.DataFrame(rsi_stocks), use_container_width=True)
        else:
            st.warning("😭 조건에 맞는 RSI 과매도 종목이 현재 없습니다.")