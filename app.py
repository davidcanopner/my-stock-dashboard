import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(layout="wide")

st.title("🎯 주식/ETF 멀티 지표 대시보드")
st.write("RSI, 볼린저 밴드, MACD, 이동평균선을 종합하여 매매 타이밍을 분석합니다.")

# 1. 관심 종목 설정
watch_list = {
    "KODEX 200": "069500.KS",
    "TIGER 미국S&P500": "360750.KS",
    "SCHD(미국배당성장)": "SCHD",
    "애플(Apple)": "AAPL"
}

results = []

for name, ticker in watch_list.items():
    # 이동평균선(120일) 계산을 위해 기간을 150일로 넉넉히 설정
    df = yf.download(ticker, period="150d", interval="1d", progress=False)
    
    if df.empty or len(df) < 120:
        continue

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 2. 지표 계산
    # RSI
    df['RSI'] = ta.rsi(df['Close'], length=14)
    
    # 볼린저 밴드
    bbands = ta.bbands(df['Close'], length=20, std=2)
    df = pd.concat([df, bbands], axis=1)
    
    # MACD
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    df = pd.concat([df, macd], axis=1)

    # 이동평균선 (5, 20, 60, 120)
    df['MA5'] = ta.sma(df['Close'], length=5)
    df['MA20'] = ta.sma(df['Close'], length=20)
    df['MA60'] = ta.sma(df['Close'], length=60)
    df['MA120'] = ta.sma(df['Close'], length=120)
    
    last_row = df.iloc[-1]

    try:
        current_price = float(last_row['Close'].item()) if hasattr(last_row['Close'], 'item') else float(last_row['Close'])
        rsi_val = float(last_row['RSI'].item()) if hasattr(last_row['RSI'], 'item') else float(last_row['RSI'])
        upper_bb = float(df.filter(like='BBU_20_2.0').iloc[-1].values[0])
        lower_bb = float(df.filter(like='BBL_20_2.0').iloc[-1].values[0])
        macd_val = float(df.filter(like='MACD_12_26_9').iloc[-1].values[0])
        macd_sig = float(df.filter(like='MACDs_12_26_9').iloc[-1].values[0])

        # MA 값 추출
        ma5 = float(last_row['MA5'])
        ma20 = float(last_row['MA20'])
        ma60 = float(last_row['MA60'])
        ma120 = float(last_row['MA120'])

        # 3. 신호 판단 로직
        # RSI
        if rsi_val >= 70: rsi_status = "🔴 과매수"
        elif rsi_val <= 30: rsi_status = "🔵 과매도"
        else: rsi_status = "⚪ 관망"

        # BB
        if current_price >= upper_bb: bb_signal = "🚩 매도 (상단)"
        elif current_price <= lower_bb: bb_signal = "🚀 매수 (하단)"
        else: bb_signal = "⏳ 관망"
        
        # MACD
        macd_signal = "📈 매수 (상향)" if macd_val > macd_sig else "📉 매도 (하향)"

        # 이동평균선 (MA) 신호
        # 단기(5, 20)가 장기(60, 120)보다 위에 있으면 정배열/골든크로스 방향
        if ma5 > ma60 and ma20 > ma120:
            ma_signal = "💎 매수 (골든크로스)"
        elif ma5 < ma60 and ma20 < ma120:
            ma_signal = "⚠️ 매도 (데드크로스)"
        else:
            ma_signal = "🧱 관망 (혼조세)"

        results.append({
            "종목명": name,
            "현재가": f"{current_price:,.0f}" if ".KS" in ticker else f"{current_price:,.2f}",
            "RSI 상태": rsi_status,
            "BB 신호": bb_signal,
            "MACD 신호": macd_signal,
            "MA 추세": ma_signal
        })
    except:
        continue

# 4. 테이블 표시
if results:
    df_display = pd.DataFrame(results)

    def style_signals(val):
        if any(x in str(val) for x in ["매도", "🔴", "하향", "데드"]): 
            return 'color: #e74c3c; font-weight: bold'
        if any(x in str(val) for x in ["매수", "🔵", "상향", "골든"]): 
            return 'color: #3498db; font-weight: bold'
        return 'color: #95a5a6'

    st.dataframe(
        df_display.style.map(style_signals), 
        use_container_width=True,
        hide_index=True
    )
else:
    st.warning("데이터 계산 중...")

# 5. 하단 설명 문구 (총 4줄)
st.markdown("---")
st.write("📊 **RSI:** 70 이상은 과열(매도), 30 이하는 침체(매수)를 의미합니다.")
st.write("📈 **볼린저 밴드:** 가격이 상단에 닿으면 매도, 하단에 닿으면 매수를 검토합니다.")
st.write("🔄 **MACD:** MACD선이 시그널선을 위로 뚫으면 매수, 아래로 뚫으면 매도 신호입니다.")
st.write("📍 **이동평균선 (MA):** 단기선이 장기선을 상향 돌파(골든크로스)하면 매수, 하향 돌파(데드크로스)하면 매도 신호입니다.")