import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import datetime
import requests
import re
import io
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(layout="wide")

def calculate_rsi(series, period=14):
    delta = series.diff()
    avg_gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    avg_loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

st.title("🤖 홍환님의 AI 종합 투자 전문 에이전트 v2.3 (캐싱 엔진)")
st.markdown("---")
st.sidebar.header("⚙️ 시스템 제어판")
st.sidebar.write("캐싱이 적용되어 오늘 이미 분석된 전략은 버튼 클릭 즉시(0.1초) 결과가 나타납니다.")

# [캐싱 0단계] 시총 2천억 이상 기본 종목 수집 (하루 단위 캐싱)
@st.cache_data(ttl=43200) # 12시간 캐시
def get_base_stocks(today_str):
    stocks = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    for sosok in [0, 1]:
        market_name = 'KOSPI' if sosok == 0 else 'KOSDAQ'
        for page in range(1, 25):
            url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}"
            res = requests.get(url, headers=headers)
            html = res.content.decode('euc-kr', errors='ignore')
            page_codes = re.findall(r'href="/item/main\.naver\?code=(\d{6})"[^>]* class="tltle">([^<]+)</a>', html)
            if not page_codes: break
            dfs = pd.read_html(io.StringIO(html))
            df_table = dfs[1].dropna(subset=['종목명'])
            
            marcap_col = next((c for c in df_table.columns if '시가총액' in str(c)), None)
            per_col = next((c for c in df_table.columns if 'PER' in str(c)), None)
            roe_col = next((c for c in df_table.columns if 'ROE' in str(c)), None)
            
            for (code, name), (_, row) in zip(page_codes, df_table.iterrows()):
                marcap_val = row[marcap_col] if marcap_col else 0
                if pd.isna(marcap_val): continue
                marcap_val = int(re.sub(r'[^0-9]', '', str(marcap_val)))
                if marcap_val >= 2000:
                    try: per_float = float(row[per_col]) if per_col and not pd.isna(row[per_col]) else None
                    except: per_float = None
                    try: roe_float = float(row[roe_col]) if roe_col and not pd.isna(row[roe_col]) else None
                    except: roe_float = None
                    stocks.append({'Code': code, 'Name': name, 'Market': market_name, 'MarCap': marcap_val * 100000000, 'PER': per_float, 'ROE': roe_float})
                else: break
    return pd.DataFrame(stocks)

today_str = datetime.date.today().strftime('%Y-%m-%d')
df_base = get_base_stocks(today_str)
st.sidebar.info(f"오늘의 분석 대상 종목: **{len(df_base)}개**")

# --- 🚀 [핵심 업그레이드] 6대 전략 연산 로직 전체 캐싱 처리 (오늘 날짜가 바뀌지 않으면 연산 생략) ---

@st.cache_data(ttl=43200)
def analyze_strategy_1(df, target_date):
    results = []
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=365 * 2)
    for _, row in df.iterrows():
        try:
            stock_df = fdr.DataReader(row['Code'], start_date, end_date)
            if len(stock_df) < 250: continue
            current = int(stock_df['Close'].iloc[-1])
            price_1y = stock_df['Close'].tail(240)
            if current < price_1y.max() * 0.6 and current < price_1y.min() * 1.25:
                price_recent = stock_df['Close'].tail(90)
                if ((price_recent.max() - price_recent.min()) / price_recent.min()) < 0.20:
                    ma5 = stock_df['Close'].rolling(5).mean().iloc[-1]
                    ma10 = stock_df['Close'].rolling(10).mean().iloc[-1]
                    ma20 = stock_df['Close'].rolling(20).mean().iloc[-1]
                    if ((max([ma5, ma10, ma20]) - min([ma5, ma10, ma20])) / min([ma5, ma10, ma20])) < 0.04:
                        results.append({"종목코드": row['Code'], "종목명": row['Name'], "시장": row['Market'], "현재가": current})
        except: continue
    return pd.DataFrame(results)

@st.cache_data(ttl=43200)
def analyze_strategy_2(df, target_date):
    results = []
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=365 * 2)
    for _, row in df.iterrows():
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
    return pd.DataFrame(results)

@st.cache_data(ttl=43200)
def analyze_strategy_3(df, target_date):
    results = []
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=150)
    for _, row in df.iterrows():
        try:
            stock_df = fdr.DataReader(row['Code'], start_date, end_date)
            if len(stock_df) < 65: continue
            ma5 = stock_df['Close'].rolling(5).mean().iloc[-1]
            ma20 = stock_df['Close'].rolling(20).mean().iloc[-1]
            ma60 = stock_df['Close'].rolling(60).mean().iloc[-1]
            vol_ma5 = stock_df['Volume'].rolling(5).mean().iloc[-2]
            today_vol = stock_df['Volume'].iloc[-1]
            current_price = stock_df['Close'].iloc[-1]
            if ma5 > ma20 and ma20 > ma60 and current_price > ma5:
                if today_vol > vol_ma5 * 2 and stock_df['Change'].iloc[-1] > 0:
                    results.append({"종목코드": row['Code'], "종목명": row['Name'], "현재가": int(current_price), "당일등락률(%)": round(stock_df['Change'].iloc[-1]*100, 2)})
        except: continue
    return pd.DataFrame(results)

@st.cache_data(ttl=43200)
def analyze_strategy_4(df, target_date):
    candidates = df[(df['ROE'] >= 10) & (df['PER'] > 0) & (df['PER'] <= 15)]
    if candidates.empty: return pd.DataFrame()
    advanced_results = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    for _, row in candidates.iterrows():
        code = row['Code']
        stock_info = {
            "종목코드": code, "종목명": row['Name'], "시장": row['Market'], "PER(배)": row['PER'], "ROE(%)": row['ROE'],
            "3년전 매출액": "-", "2년전 매출액": "-", "1년전 매출액": "-", "매출액 성장률(2년전)(%)": "-", "매출액 성장률(1년전)(%)": "-",
            "3년전 영업이익": "-", "2년전 영업이익": "-", "1년전 영업이익": "-", "영업이익 성장률(2년전)(%)": "-", "영업이익 성장률(1년전)(%)": "-"
        }
        try:
            url = f"https://finance.naver.com/item/main.naver?code={code}"
            res = requests.get(url, headers=headers)
            html = res.content.decode('euc-kr', errors='ignore')
            tables = pd.read_html(io.StringIO(html))
            df_fin = tables[3]
            df_fin.set_index(df_fin.columns[0], inplace=True)
            annual_cols = [c for c in df_fin.columns if c[0] == '최근 연간 실적' and '(E)' not in str(c[1])][:3]
            if len(annual_cols) == 3:
                rev_idx = [i for i in df_fin.index if '매출액' in str(i)][0]
                op_idx = [i for i in df_fin.index if '영업이익' in str(i)][0]
                def clean_num(v):
                    if pd.isna(v) or v == '-' or str(v).strip() == '': return None
                    return float(str(v).replace(',', ''))
                rev_3y = clean_num(df_fin.loc[rev_idx, annual_cols[0]])
                rev_2y = clean_num(df_fin.loc[rev_idx, annual_cols[1]])
                rev_1y = clean_num(df_fin.loc[rev_idx, annual_cols[2]])
                op_3y = clean_num(df_fin.loc[op_idx, annual_cols[0]])
                op_2y = clean_num(df_fin.loc[op_idx, annual_cols[1]])
                op_1y = clean_num(df_fin.loc[op_idx, annual_cols[2]])
                if rev_3y: stock_info["3년전 매출액"] = int(rev_3y)
                if rev_2y: stock_info["2년전 매출액"] = int(rev_2y)
                if rev_1y: stock_info["1년전 매출액"] = int(rev_1y)
                if op_3y: stock_info["3년전 영업이익"] = int(op_3y)
                if op_2y: stock_info["2년전 영업이익"] = int(op_2y)
                if op_1y: stock_info["1년전 영업이익"] = int(op_1y)
                if rev_3y and rev_2y and rev_3y != 0: stock_info["매출액 성장률(2년전)(%)"] = round(((rev_2y - rev_3y) / rev_3y) * 100, 2)
                if op_3y and op_2y and op_3y != 0: stock_info["영업이익 성장률(2년전)(%)"] = round(((op_2y - op_3y) / abs(op_3y)) * 100, 2)
                if rev_2y and rev_1y and rev_2y != 0: stock_info["매출액 성장률(1년전)(%)"] = round(((rev_1y - rev_2y) / rev_2y) * 100, 2)
                if op_2y and op_1y and op_2y != 0: stock_info["영업이익 성장률(1년전)(%)"] = round(((op_1y - op_2y) / abs(op_2y)) * 100, 2)
        except: pass
        advanced_results.append(stock_info)
    df_final = pd.DataFrame(advanced_results)
    if not df_final.empty:
        col_order = ["종목코드", "종목명", "시장", "PER(배)", "ROE(%)", "3년전 매출액", "2년전 매출액", "1년전 매출액", "매출액 성장률(2년전)(%)", "매출액 성장률(1년전)(%)", "3년전 영업이익", "2년전 영업이익", "1년전 영업이익", "영업이익 성장률(2년전)(%)", "영업이익 성장률(1년전)(%)"]
        df_final = df_final[col_order]
        df_final['sort_helper'] = pd.to_numeric(df_final['영업이익 성장률(1년전)(%)'], errors='coerce').fillna(-99999)
        df_final = df_final.sort_values(by='sort_helper', ascending=False).drop(columns=['sort_helper'])
    return df_final

@st.cache_data(ttl=43200)
def analyze_strategy_5(df, target_date):
    results = []
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=100)
    for _, row in df.iterrows():
        try:
            stock_df = fdr.DataReader(row['Code'], start_date, end_date)
            if len(stock_df) < 25: continue
            ma20 = stock_df['Close'].rolling(20).mean()
            std20 = stock_df['Close'].rolling(20).std()
            upper_bb = ma20 + (std20 * 2)
            current_price = stock_df['Close'].iloc[-1]
            prev_price = stock_df['Close'].iloc[-2]
            if current_price > upper_bb.iloc[-1] and prev_price <= upper_bb.iloc[-2]:
                vol_ma5 = stock_df['Volume'].rolling(5).mean().iloc[-2]
                if stock_df['Volume'].iloc[-1] > vol_ma5 * 2.5:
                    results.append({"종목코드": row['Code'], "종목명": row['Name'], "현재가": int(current_price), "상단밴드가": round(upper_bb.iloc[-1])})
        except: continue
    return pd.DataFrame(results)

@st.cache_data(ttl=43200)
def analyze_strategy_6(df, target_date):
    results = []
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=100)
    for _, row in df.iterrows():
        try:
            stock_df = fdr.DataReader(row['Code'], start_date, end_date)
            if len(stock_df) < 25: continue
            ma20 = stock_df['Close'].rolling(20).mean().iloc[-1]
            envelope_lower = ma20 * (1 - 0.15)
            current_price = stock_df['Close'].iloc[-1]
            if current_price <= envelope_lower:
                disparity = (current_price / ma20) * 100
                results.append({"종목코드": row['Code'], "종목명": row['Name'], "현재가": int(current_price), "20일선": round(ma20), "이격률(%)": round(disparity, 1)})
        except: continue
    return pd.DataFrame(results)

# --- 🏢 대시보드 레이아웃 구성 ---
row1_col1, row1_col2, row1_col3 = st.columns(3)
row2_col1, row2_col2, row2_col3 = st.columns(3)

with row1_col1:
    st.subheader("👴 1. 찰리멍거 바닥 횡보")
    if st.button("🔍 바닥 횡보주 검색"):
        res = analyze_strategy_1(df_base, today_str)
        st.dataframe(res if not res.empty else "조건에 맞는 종목이 없습니다.", use_container_width=True)

with row1_col2:
    st.subheader("📉 2. 일봉&주봉 RSI 과매도")
    if st.button("🔍 RSI 과매도주 검색"):
        res = analyze_strategy_2(df_base, today_str)
        st.dataframe(res if not res.empty else "조건에 맞는 종목이 없습니다.", use_container_width=True)

with row1_col3:
    st.subheader("🚀 3. 거래량 분출 정배열 초입")
    if st.button("🔍 정배열 초입주 검색"):
        res = analyze_strategy_3(df_base, today_str)
        st.dataframe(res if not res.empty else "조건에 맞는 종목이 없습니다.", use_container_width=True)

with row2_col1:
    st.subheader("💎 4. 가성비 알짜 우량주")
    if st.button("🔍 가성비 우량주 심층 분석"):
        res = analyze_strategy_4(df_base, today_str)
        st.dataframe(res if not res.empty else "조건에 맞는 종목이 없습니다.", use_container_width=True)

with row2_col2:
    st.subheader("💥 5. 볼린저 밴드 상단 돌파")
    if st.button("🔍 볼린저 돌파주 검색"):
        res = analyze_strategy_5(df_base, today_str)
        st.dataframe(res if not res.empty else "조건에 맞는 종목이 없습니다.", use_container_width=True)

with row2_col3:
    st.subheader("🛡️ 6. 엔벨로프 낙폭과대 타점")
    if st.button("🔍 엔벨로프 타점 검색"):
        res = analyze_strategy_6(df_base, today_str)
        st.dataframe(res if not res.empty else "조건에 맞는 종목이 없습니다.", use_container_width=True)