import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go

# 0. 전역 변수 초기화 (에러 방지 핵심)
target_stock = None
target_period = "3개월"
p_map = {"1주": 5, "2주": 10, "1개월": 20, "3개월": 60, "6개월": 120, "1년": 252, "3년": 756, "5년": 1260, "10년": 2520}

st.set_page_config(layout="wide")

st.title("🎯 Stock/ETF Index Dashboard")
st.write("RSI, 볼린저 밴드, MACD, 이동평균선을 종합하여 매매 타이밍을 분석합니다.")

# 1. 티커 리스트
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

# 2. 데이터 로딩 및 분석
for name, ticker in watch_list.items():
    try:
        df = yf.download(ticker, period="10y", interval="1d", progress=False)
        if df.empty or len(df) < 30: continue
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(col).strip() for col in df.columns]

        df['RSI'] = ta.rsi(df['Close'], length=14)
        bb = ta.bbands(df['Close'], length=20, std=2)
        if bb is not None: df = pd.concat([df, bb], axis=1)
        macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
        if macd is not None: df = pd.concat([df, macd], axis=1)
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        df['MA120'] = ta.sma(df['Close'], length=120)
        
        data_dict[name] = df
        last_row = df.iloc[-1]

        cur_price = float(last_row['Close'])
        rsi_v = float(last_row['RSI'])
        up_bb = float(df.filter(like='BBU_20_2.0').iloc[-1].values[0])
        lo_bb = float(df.filter(like='BBL_20_2.0').iloc[-1].values[0])
        m_val = float(df.filter(like='MACD_12_26_9').iloc[-1].values[0])
        m_sig = float(df.filter(like='MACDs_12_26_9').iloc[-1].values[0])
        m5, m20, m60, m120 = last_row['MA5'], last_row['MA20'], last_row['MA60'], last_row['MA120']

        rsi_s = f"🔴 과매수 ({rsi_v:.1f})" if rsi_v >= 70 else f"🔵 과매도 ({rsi_v:.1f})" if rsi_v <= 30 else f"⚪ 관망 ({rsi_v:.1f})"
        bb_s = "🚩 매도 (상단)" if cur_price >= up_bb else "🚀 매수 (하단)" if cur_price <= lo_bb else "⏳ 관망"
        macd_s = "📈 매수 (상향)" if m_val > m_sig else "📉 매도 (하향)"
        ma_s = "💎 매수 (골든)" if m5 > m60 and m20 > m120 else "⚠️ 매도 (데드)" if m5 < m60 and m20 < m120 else "🧱 관망"

        results.append({"종목명": name, "현재가": f"{cur_price:,.0f}" if ".KS" in ticker else f"{cur_price:,.2f}", "RSI 상태": rsi_s, "BB 신호": bb_s, "MACD 신호": macd_s, "MA 추세": ma_s})
    except: continue

# 3. 상단 테이블 출력
if results:
    st.dataframe(pd.DataFrame(results).style.map(lambda v: 'color: #e74c3c; font-weight: bold' if any(x in str(v) for x in ["매도", "🔴", "하향", "데드"]) 
                                                 else 'color: #3498db; font-weight: bold' if any(x in str(v) for x in ["매수", "🔵", "상향", "골든"]) 
                                                 else 'color: #95a5a6'), use_container_width=True, hide_index=True)

# 4. 하단 레이아웃 및 차트 (에러 방지를 위한 선제적 변수 할당)
if len(data_dict) > 0:
    st.markdown("---")
    col_guide, col_set = st.columns([1, 1.5])
    
    with col_guide:
        st.subheader("📝 Indicator Guide")
        st.write("📊 **RSI:** 70↑ **'매도신호'**, 30↓ **'매수신호'**")
        st.write("📈 **BB:** 상단 터치 시 **'매도신호'**, 하단 터치 시 **'매수신호'**")
        st.write("🔄 **MACD:** 상향 교차 시 **'매수신호'**, 하향 교차 시 **'매도신호'**")
        st.write("📍 **MA:** 골든크로스 시 **'매수신호'**, 데드크로스 시 **'매도신호'**")

    with col_set:
        st.subheader("⚙️ Chart Settings")
        sc1, sc2 = st.columns(2)
        with sc1:
            # selectbox 결과를 즉시 변수에 담음
            target_stock = st.selectbox("종목 선택", options=list(data_dict.keys()), key="s_stock")
        with sc2:
            target_period = st.selectbox("기간 선택", options=list(p_map.keys()), index=3, key="s_period")

    # 변수가 존재하고 데이터가 있을 때만 차트 실행
    if target_stock and target_stock in data_dict:
        pdf = data_dict[target_stock].tail(p_map[target_period])
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=pdf.index, open=pdf['Open'], high=pdf['High'], low=pdf['Low'], close=pdf['Close'], name='Price'))
        fig.add_trace(go.Scatter(x=pdf.index, y=pdf['MA20'], line=dict(color='orange', width=1.5), name='MA20'))
        fig.update_layout(title=f"📊 {target_stock} ({target_period})", xaxis_rangeslider_visible=False, height=450, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("데이터 로딩 중 에러가 발생했거나 데이터를 불러오는 중입니다.")
