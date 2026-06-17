import FinanceDataReader as fdr
import pandas as pd
from tqdm import tqdm
import datetime
import warnings
warnings.filterwarnings('ignore') # 불필요한 경고창 끄기

def calculate_rsi(series, period=14):
    """HTS와 동일한 방식(웰레스 와일더 방식)으로 RSI를 계산합니다."""
    delta = series.diff()
    avg_gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    avg_loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def main():
    print("==================================================")
    print("🚀 [시총 2천억 이상 + 일봉/주봉 RSI 과매도] 에이전트 가동")
    print("==================================================")

    # 1. KRX 전체 종목 목록 가져오기
    print("🔍 1. 한국거래소(KRX) 상장 종목 수집 및 시가총액 필터링 중...")
    df_krx = fdr.StockListing('KRX')
    
    # 코스피, 코스닥 시장만 지정
    df_krx = df_krx[df_krx['Market'].isin(['KOSPI', 'KOSDAQ'])]
    
    # ⭐ [KeyError 방어 조치] 시가총액 컬럼 이름 유연하게 찾기
    marcap_col = None
    for col in ['MarCap', 'marcap', 'MarketCap', '시가총액']:
        if col in df_krx.columns:
            marcap_col = col
            break
            
    # 만약 시가총액 컬럼이 직접 안 보인다면, [종가(Close) * 상장주식수(Stocks)]로 직접 계산해서 만듭니다.
    if marcap_col:
        df_krx = df_krx[df_krx[marcap_col] >= 200000000000]
    elif 'Close' in df_krx.columns and 'Stocks' in df_krx.columns:
        df_krx['Calculated_MarCap'] = df_krx['Close'] * df_krx['Stocks']
        df_krx = df_krx[df_krx['Calculated_MarCap'] >= 200000000000]
        marcap_col = 'Calculated_MarCap'
    else:
        print("⚠️ 시가총액 정보를 확인할 수 없어 안전을 위해 전체 종목을 대상으로 검사합니다.")
    
    target_stocks = []
    
    # 주봉 14개 이상을 안정적으로 계산하기 위해 2년치 데이터 수집
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=365 * 2)

    print(f"📊 2. 조건 필터링된 {len(df_krx)}개 종목의 차트 분석을 시작합니다.")
    print("--------------------------------------------------")

    # 2. 필터링된 종목만 돌면서 차트 분석하기
    for index, row in tqdm(df_krx.iterrows(), total=len(df_krx), desc="차트 및 지표 분석 중"):
        code = row['Code']
        name = row['Name']
        market = row['Market']
        
        # 시가총액 표시용 억 단위 변환
        if marcap_col:
            marcap_gwon = round(row[marcap_col] / 100000000, 1)
        else:
            marcap_gwon = "확인불가"
        
        try:
            # 해당 종목의 일봉 데이터 가져오기
            df_daily = fdr.DataReader(code, start_date, end_date)
            if len(df_daily) < 100: # 데이터가 너무 적은 신규 상장주 제외
                continue
                
            current_price = int(df_daily['Close'].iloc[-1])
            
            # --- A. 일봉 RSI 계산 ---
            df_daily['RSI_Daily'] = calculate_rsi(df_daily['Close'], period=14)
            rsi_daily_now = df_daily['RSI_Daily'].iloc[-1]
            
            # --- B. 주봉 데이터 생성 및 주봉 RSI 계산 ---
            df_weekly = df_daily.resample('W').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            })
            df_weekly['RSI_Weekly'] = calculate_rsi(df_weekly['Close'], period=14)
            rsi_weekly_now = df_weekly['RSI_Weekly'].iloc[-1]

            # --- C. 💎 조건 검사 💎 ---
            # 일봉 RSI 25 이하 그리고 주봉 RSI 30 이하
            if rsi_daily_now <= 25 and rsi_weekly_now <= 30:
                target_stocks.append({
                    "종목코드": code,
                    "종목명": name,
                    "시장": market,
                    "시가총액(억)": marcap_gwon,
                    "현재가": current_price,
                    "일봉 RSI": round(rsi_daily_now, 2),
                    "주봉 RSI": round(rsi_weekly_now, 2)
                })
                
        except Exception as e:
            continue

    # 3. 분석 결과 저장 및 출력
    if target_stocks:
        result_df = pd.DataFrame(target_stocks)
        result_df = result_df.sort_values(by="일봉 RSI", ascending=True)
        
        today_str = datetime.date.today().strftime("%Y%m%d")
        file_name = f"RSI_과매도_종목추출_{today_str}.xlsx"
        
        result_df.to_excel(file_name, index=False)
        print("\n==================================================")
        print(f"🎯 조건에 부합하는 역발상 투자 종목 {len(result_df)}개를 발굴했습니다!")
        print(f"📁 파일 저장 완료: {file_name}")
        print("==================================================")
    else:
        print("\n😭 현재 시장에서 시총 2천억 이상 중 일봉 RSI 25 이하 & 주봉 RSI 30 이하인 종목이 없습니다.")

if __name__ == "__main__":
    main()