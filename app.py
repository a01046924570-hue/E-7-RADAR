import streamlit as st
import yfinance as yf
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go

# 1. 페이지 설정
st.set_page_config(page_title="E-7 RADAR V18", layout="wide")
st_autorefresh(interval=30000, limit=None, key="refresh_v18")

# --- [여기에 구글 시트 주소 붙여넣기] ---
url = "https://docs.google.com/spreadsheets/d/1uoDbuvVTooPlTjSQBjybfNW3CkXCQYPdf4-bXFRkqrQ/edit?usp=sharing"
# --------------------------------------

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        return conn.read(spreadsheet=url, ttl=0)
    except:
        return pd.DataFrame(columns=["user_id", "type", "ticker", "name", "buy_price", "qty"])

# 2. 스타일링
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #000000; }
    .label-text { color: #FFFFFF !important; font-weight: 600; }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 2rem !important; }
    </style>
""", unsafe_allow_html=True)

# 3. 사이드바 로그인
with st.sidebar:
    st.title("📡 E-7 RADAR")
    user_pw = st.text_input("🔑 접속 키 입력", type="password")
    if not user_pw:
        st.stop()
    st.success(f"{user_pw}님 접속 중")
    st.divider()
    
    # [종목 추가 양식] - 사이드바에서 바로 추가
    st.subheader("➕ 종목 추가")
    with st.form("add_form", clear_on_submit=True):
        t_type = st.radio("구분", ["보유주식", "관심종목"])
        t_ticker = st.text_input("티커 (예: TSLA, 005930.KS)")
        t_price = st.number_input("매수 평단 (관심종목은 0)", min_value=0.0)
        t_qty = st.number_input("보유 수량 (관심종목은 0)", min_value=0.0)
        if st.form_submit_button("레이더 등록"):
            df = load_data()
            new_data = pd.DataFrame([{
                "user_id": user_pw, "type": t_type, "ticker": t_ticker.upper(),
                "name": t_ticker, "buy_price": t_price, "qty": t_qty
            }])
            updated_df = pd.concat([df, new_data], ignore_index=True)
            conn.update(spreadsheet=url, data=updated_df)
            st.rerun()

# 4. 메인 화면 (관제탑)
df = load_data()
user_df = df[df['user_id'] == user_pw]

# [보유 주식 섹션]
st.markdown("<h2 style='color:white;'>📊 실시간 관제탑 (보유주식)</h2>", unsafe_allow_html=True)
holdings = user_df[user_df['type'] == "보유주식"]

if holdings.empty:
    st.info("등록된 보유 주식이 없습니다.")
else:
    for _, row in holdings.iterrows():
        stock = yf.Ticker(row['ticker'])
        curr = stock.history(period="1d")['Close'].iloc[-1]
        diff = curr - row['buy_price']
        rate = (diff / row['buy_price'] * 100) if row['buy_price'] > 0 else 0
        
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        col1.metric(row['ticker'], f"{curr:,.2f}", f"{rate:+.2f}%")
        col2.write(f"평단: {row['buy_price']:,.2f}")
        col3.write(f"수량: {row['qty']}")
        if col4.button(f"삭제", key=f"del_{row['ticker']}"):
            new_df = df.drop(_)
            conn.update(spreadsheet=url, data=new_df)
            st.rerun()
        st.divider()

# [관심 종목 섹션]
st.markdown("<h2 style='color:white;'>👀 관심 종목 감시</h2>", unsafe_allow_html=True)
watchlist = user_df[user_df['type'] == "관심종목"]

if watchlist.empty:
    st.info("등록된 관심 종목이 없습니다.")
else:
    cols = st.columns(3)
    for i, (_, row) in enumerate(watchlist.iterrows()):
        stock = yf.Ticker(row['ticker'])
        curr = stock.history(period="1d")['Close'].iloc[-1]
        with cols[i % 3]:
            st.metric(row['ticker'], f"{curr:,.2f}")
            if st.button(f"삭제", key=f"del_w_{row['ticker']}"):
                new_df = df.drop(_)
                conn.update(spreadsheet=url, data=new_df)
                st.rerun()
