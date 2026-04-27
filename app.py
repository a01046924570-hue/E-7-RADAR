import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# 1. 설정
st.set_page_config(page_title="E-7 RADAR FINAL", layout="wide")
st_autorefresh(interval=30000, limit=None, key="refresh_v20")

# --- [정보 확인] ---
SHEET_ID = "1uoDbuvVTooPlTjSQBjybfNW3CkXCQYPdf4-bXFRkqrQ"
# 사용자님이 주신 진짜 주소로 고정했습니다!
API_URL = "https://script.google.com/macros/s/AKfycbwjCwOjJSTdGbfN5zrHDP6nSux1DAMMRgMURkCTSHxT9LmZPNDhMWJp8qOGtoEZJ62s/exec"
# ------------------

CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

def load_data():
    try:
        # 캐시 방지를 위해 랜덤 파라미터 추가하여 읽기
        return pd.read_csv(f"{CSV_URL}&t={pd.Timestamp.now().timestamp()}")
    except:
        return pd.DataFrame(columns=["user_id", "type", "ticker", "buy_price", "qty"])

# 예전 전성기 느낌! 깔끔한 블랙 테마 스타일
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #000000; }
    [data-testid="stSidebar"] { background-color: #0e0e0e; }
    .stMetric { background-color: #111111; border: 1px solid #222; padding: 10px; border-radius: 10px; }
    hr { margin: 15px 0px; border-bottom: 1px solid #222; }
    h3 { margin-bottom: 0px !important; }
    </style>
""", unsafe_allow_html=True)

# 2. 사이드바 (등록/삭제 기능)
with st.sidebar:
    st.title("📡 E-7 RADAR")
    user_pw = st.text_input("🔑 접속 키 입력", type="password")
    
    if not user_pw:
        st.info("키를 입력하여 시스템을 가동하십시오.")
        st.stop()
    
    st.success(f"**{user_pw}**님 접속 중")
    st.divider()
    
    # [기능 1] 종목 추가
    with st.expander("➕ 종목 추가", expanded=False):
        with st.form("add_form", clear_on_submit=True):
            t_type = st.radio("구분", ["보유주식", "관심종목"])
            t_ticker = st.text_input("티커 (예: TSLA)").upper()
            t_price = st.number_input("평단", min_value=0.0)
            t_qty = st.number_input("수량", min_value=0.0)
            if st.form_submit_button("레이더 등록"):
                if t_ticker:
                    payload = {"action": "add", "user_id": user_pw, "type": t_type, "ticker": t_ticker, "buy_price": t_price, "qty": t_qty}
                    requests.post(API_URL, json=payload)
                    st.success("등록 요청 완료!")
                    st.rerun()

    # [기능 2] 종목 삭제
    df = load_data()
    user_df = df[df['user_id'].astype(str) == str(user_pw)]
    if not user_df.empty:
        with st.expander("🗑️ 종목 삭제"):
            target = st.selectbox("삭제할 종목 선택", user_df['ticker'].tolist())
            if st.button("선택 종목 삭제"):
                payload = {"action": "delete", "user_id": user_pw, "ticker": target}
                requests.post(API_URL, json=payload)
                st.warning(f"{target} 삭제 요청 완료!")
                st.rerun()

# 3. 메인 화면 (가로형 디자인 복구)
st.markdown("<h2 style='color:white;'>📊 실시간 관제탑</h2>", unsafe_allow_html=True)
st.divider()

if not user_df.empty:
    for _, row in user_df.iterrows():
        try:
            # 주가 데이터 로드 (5일치 15분 단위)
            stock = yf.Ticker(str(row['ticker']))
            hist = stock.history(period="2d", interval="15m")
            if hist.empty: continue
            
            curr = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[0]
            
            with st.container():
                # 가로로 5컬럼 배치 (종목명, 현재가, 정보1, 정보2, 차트)
                col1, col2, col3, col4, col5 = st.columns([1.2, 1.5, 1.5, 1.5, 2.5])
                
                if row['type'] == "보유주식":
                    buy_p = float(row['buy_price'])
                    rate = ((curr - buy_p) / buy_p * 100) if buy_p > 0 else 0
                    color = "#FF4B4B" if rate < 0 else "#00FF7F"
                    
                    col1.markdown(f"<h3 style='color:white;'>{row['ticker']}</h3><p style='color:{color}; font-size:12px;'>{row['type']}</p>", unsafe_allow_html=True)
                    col2.metric("현재가", f"${curr:,.2f}", f"{rate:+.2f}%")
                    col3.metric("평단/수량", f"${buy_p:,.2f}", f"{row['qty']:,}주")
                    col4.metric("평가금액", f"${(curr * float(row['qty'])):,.2f}")
                    
                    # 미니 차트
                    fig = go.Figure(data=[go.Scatter(x=hist.index, y=hist['Close'], line=dict(color=color, width=2), fill='tozeroy')])
                    fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), height=70, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                      xaxis=dict(visible=False), yaxis=dict(visible=False))
                    col5.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                
                else: # 관심종목
                    col1.markdown(f"<h3 style='color:white;'>{row['ticker']}</h3><p style='color:#888888; font-size:12px;'>관심종목</p>", unsafe_allow_html=True)
                    col2.metric("현재가", f"${curr:,.2f}", f"{curr-prev_close:+.2f}")
                    col3.write("")
                    col4.write("")
                    # 미니 차트 (무채색)
                    fig = go.Figure(data=[go.Scatter(x=hist.index, y=hist['Close'], line=dict(color='#888888', width=2))])
                    fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), height=70, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                      xaxis=dict(visible=False), yaxis=dict(visible=False))
                    col5.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                
                st.markdown("<hr>", unsafe_allow_html=True)
        except:
            continue
else:
    st.info("사이드바에서 종목을 추가하면 실시간 추적이 시작됩니다.")
