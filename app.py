import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go

st.set_page_config(layout="wide")

# 1) 대제목
st.title("🎯 Stock/ETF Index Dashboard")
st.write("RSI, 볼린저 밴드, MACD, 이동평균선을 종합하여 매매 타이밍을 분석합니다.")

# 종목 설정 (yfinance 전용 티커 사용)
watch_list = {
    "KODEX 200": "069500.KS",
    "TIGER 미국S&P500": "360750.KS",
    "SCHD(미국배당성장)": "SCHD",
    "KODEX방산TOP10": "444500.KS",
    "ACE미국빅테크TOP7 PLUS": "465580.KS",
    "WON미국우주항공방산": "440910.KS",
    "HANARO 유럽방산": "466920.KS"
}

results = []
data_dict = {}

for name, ticker in watch_list.items():
    # 데이터 불러오기
    df = yf.download(ticker, period="max", interval="1d", progress=False)
    
    if df.empty or len(df) < 120: continue

    # 🚨 [중요] MultiIndex 컬럼 해결: 'Close' 열을 확실하게 찾기 위함
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # 간혹 컬럼명에 공백이 들어가는 경우 방지
    df.columns = [str(col).strip() for col in df.columns]

    try:
        # 지표 계산
        df['RSI'] = ta.rsi(df['Close'], length=14)
        bbands = ta.bbands(df['Close'], length=20, std=2)
        df = pd.concat([df, bbands], axis=1)
        macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
        df = pd.concat([df, macd], axis=1)
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        df['MA120'] = ta.sma(df['Close'], length=120)
        
        data_dict[name] = df
        last_row = df.iloc[-1]

        current_price = float(last_row['Close'])
        rsi_val = float(last_row['RSI'])
        upper_bb = float(df.filter(like='BBU_20_2.0').iloc[-1].values[0])
        lower_bb = float(df.filter(like='BBL_20_2.0').iloc[-1].values[0])
        macd_val = float(df.filter(like='MACD_12_26_9').iloc[-1].values[0])
        macd_sig = float(df.filter(like='MACDs_12_26_9').iloc[-1].values[0])
        ma5, ma20, ma60, ma120 = last_row['MA5'], last_row['MA20'], last_row['MA60'], last_row['MA120']

        # RSI 상태값 표시
        if rsi_val >= 70: rsi_status = f"🔴 과매수 ({rsi_val:.2f})"
        elif rsi_val <= 30: rsi_status = f"🔵 과매도 ({rsi_val:.2f})"
        else: rsi_status = f"⚪ 관망 ({rsi_val:.2f})"

        bb_signal = "🚩 매도 (상단)" if current_price >= upper_bb else "🚀 매수 (하단)" if current_price <= lower_bb else "⏳ 관망"
        macd_signal = "📈 매수 (상향)" if macd_val > macd_sig else "📉 매도 (하향)"
        ma_signal = "💎 매수 (골든)" if ma5 > ma60 and ma20 > ma120 else "⚠️ 매도 (데드)" if ma5 < ma60 and ma20 < ma120 else "🧱 관망"

        results.append({
            "종목명": name,
            "현재가": f"{current_price:,.0f}" if ".KS" in ticker else f"{current_price:,.2f}",
            "RSI 상태": rsi_status,
            "BB 신호": bb_signal,
            "MACD 신호": macd_signal,
            "MA 추세": ma_signal
        })
    except Exception as e:
        # 특정 종목에서 에러 발생 시 건너뛰기
        continue

# --- 테이블 표시 ---
if results:
    df_display = pd.DataFrame(results)
    def style_signals(val):
        if any(x in str(val) for x in ["매도", "🔴", "하향", "데드"]): return 'color: #e74c3c; font-weight: bold'
        if any(x in str(val) for x in ["매수", "🔵", "상향", "골든"]): return 'color: #3498db; font-weight: bold'
        return 'color: #95a5a6'
    st.dataframe(df_display.style.map(style_signals), use_container_width=True, hide_index=True)

# --- 설명과 차트 컨트롤러 (테이블 바로 밑) ---
st.markdown("---")
col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("📝 Indicator Guide")
    st.write("📊 **RSI:** 70↑ **'매도신호'**, 30↓ **'매수신호'**")
    st.write("📈 **BB:** 상단 터치 시 **'매도신호'**, 하단 터치 시 **'매수신호'**")
    st.write("🔄 **MACD:** 상향 교차 시 **'매수신호'**, 하향 교차 시 **'매도신호'**")
    st.write("📍 **MA:** 골든크로스 시 **'매수신호'**, 데드크로스 시 **'매도신호'**")

with col2:
    st.subheader("⚙️ Chart Settings")
    sub_col1, sub_col2 = st.columns(2)
    with sub_col1:
        selected_stock = st.selectbox("종목 선택", list(data_dict.keys()))
    with sub_col2:
        period_options = {"1주": 5, "2주": 10, "1개월": 20, "3개월": 60, "6개월": 120, "1년": 252, "3년": 756, "5년": 1260, "10년": 2520}
        selected_period = st.selectbox("기간 선택", list(period_options.keys()), index=3)

# --- 하단 차트 ---
if selected_stock:
    chart_df = data_dict[selected_stock]
    plot_df = chart_df.tail(period_options[selected_period])
    
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=plot_df.index, open=plot_df['Open'], high=plot_df['High'], low=plot_df['Low'], close=plot_df['Close'], name='Price'))
    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MA20'], line=dict(color='orange', width=1.5), name='MA20'))
    fig.update_layout(
        title=f"📊 {selected_stock} ({selected_period})",
        xaxis_rangeslider_visible=False,
        height=450,
        margin=dict(l=10, r=10, t=40, b=10)
    )
    st.plotly_chart(fig, use_container_width=True)
