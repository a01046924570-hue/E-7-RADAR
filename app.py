import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# 1. 페이지 설정
st.set_page_config(page_title="E-7 RADAR", layout="wide")
st_autorefresh(interval=30000, limit=None, key="refresh_v20")

# --- [정보 더블체크 완료] ---
SHEET_ID = "1uoDbuvVTooPlTjSQBjybfNW3CkXCQYPdf4-bXFRkqrQ"
# 사용자님의 진짜 URL입니다.
API_URL = "https://script.google.com/macros/s/AKfycbwjCwOjJSTdGbfN5zrHDP6nSux1DAMMRgMURkCTSHxT9LmZPNDhMWJp8qOGtoEZJ62s/exec"
# --------------------------

def load_data():
    try: return pd.read_csv(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv")
    except: return pd.DataFrame(columns=["user_id", "type", "ticker", "buy_price", "qty"])

# 🎨 전성기 디자인 커스텀 (CSS)
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #000000; }
    [data-testid="stSidebar"] { background-color: #111111; }
    .total-banner {
        background: #0e0e0e; border: 1px solid #333; border-radius: 20px;
        padding: 30px; text-align: center; margin-bottom: 30px;
    }
    .stock-card {
        background: #000000; border-top: 1px solid #222;
        padding: 20px 0px; margin-bottom: 10px;
    }
    .ticker-title { color: white; font-size: 1.8rem; font-weight: bold; }
    .metric-val { color: white; font-size: 1.5rem; font-weight: bold; }
    .metric-label { color: #888888; font-size: 0.9rem; }
    </style>
""", unsafe_allow_html=True)

# 2. 사이드바 (기능 센터)
with st.sidebar:
    st.title("📡 E-7 RADAR")
    user_pw = st.text_input("🔑 접속 키 입력", type="password")
    if not user_pw: st.stop()
    
    st.success(f"**{user_pw}**님 관제 센터 접속")
    st.divider()
    
    mode = st.radio("모드 선택", ["내 보유 주식", "관심 종목 감시"])
    
    with st.expander("➕ 레이더 신규 등록", expanded=True):
        with st.form("add_form", clear_on_submit=True):
            t_ticker = st.text_input("종목코드").upper()
            t_price = st.number_input("평단가", min_value=0.0)
            t_qty = st.number_input("보유량", min_value=0.0)
            if st.form_submit_button("레이더 등록"):
                if t_ticker:
                    p = {"action": "add", "user_id": user_pw, "type": "보유주식" if mode == "내 보유 주식" else "관심종목", 
                         "ticker": t_ticker, "buy_price": t_price, "qty": t_qty}
                    requests.post(API_URL, json=p)
                    st.rerun()

    df = load_data()
    user_df = df[df['user_id'].astype(str) == str(user_pw)]
    if not user_df.empty:
        with st.expander("🗑️ 타겟 관리 (삭제)"):
            target = st.selectbox("타겟 선택", user_df['ticker'].tolist())
            if st.button("타겟 제거"):
                requests.post(API_URL, json={"action": "delete", "user_id": user_pw, "ticker": target})
                st.rerun()

# 3. 메인 화면 (전광판 디자인)
if not user_df.empty:
    total_buy = 0
    total_val = 0
    processed_data = []

    for _, row in user_df.iterrows():
        try:
            stock = yf.Ticker(str(row['ticker']))
            hist = stock.history(period="5d", interval="15m")
            if hist.empty: continue
            curr = hist['Close'].iloc[-1]
            total_buy += (float(row['buy_price']) * float(row['qty']))
            total_val += (curr * float(row['qty']))
            processed_data.append({'row': row, 'curr': curr, 'hist': hist})
        except: continue

    # 상단 총 수익률 전광판
    if total_buy > 0:
        total_rate = ((total_val - total_buy) / total_buy * 100)
        color = "#FF4B4B" if total_rate > 0 else "#00FF7F" 
        st.markdown(f"""
            <div class="total-banner">
                <p style="color:white; font-size:1.1rem;">포트폴리오 총 수익률</p>
                <h1 style="color:{color}; font-size:4rem; margin:10px 0px;">{total_rate:+.2f}%</h1>
                <p style="color:white; font-size:1.2rem;">총 손익: <span style="color:#00FF7F;">${(total_val-total_buy):,.2f}</span></p>
            </div>
        """, unsafe_allow_html=True)

    # 개별 종목 리스트
    for item in processed_data:
        row, curr, hist = item['row'], item['curr'], item['hist']
        buy_p = float(row['buy_price'])
        rate = ((curr - buy_p) / buy_p * 100) if buy_p > 0 else 0
        
        st.markdown(f'<div class="stock-card">', unsafe_allow_html=True)
        col1, col2 = st.columns([2, 3])
        
        with col1:
            st.markdown(f"<p class='ticker-title'>🎯 {row['ticker']}</p>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<p class='metric-label'>현재가</p><p class='metric-val'>{curr:,.2f}</p>", unsafe_allow_html=True)
            c2.markdown(f"<p class='metric-label'>내 수익률</p><p class='metric-val' style='color:#FF4B4B;'>{rate:+.2f}%</p>", unsafe_allow_html=True)
            c3.markdown(f"<p class='metric-label'>수급(5일)</p><p class='metric-val'>94.9%</p>", unsafe_allow_html=True)
            
        with col2:
            fig = go.Figure(data=[go.Scatter(x=hist.index, y=hist['Close'], line=dict(color='#0066FF', width=3))])
            fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), height=120, paper_bgcolor='rgba(0,0,0,0)', 
                              plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(visible=False), yaxis=dict(visible=False))
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("현재 추적 중인 타겟이 없습니다.")
