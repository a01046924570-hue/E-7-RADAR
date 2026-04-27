import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from streamlit_autorefresh import st_autorefresh

# 1. 페이지 설정
st.set_page_config(page_title="E-7 RADAR FINAL", layout="wide")
st_autorefresh(interval=30000, limit=None, key="refresh_v20")

# --- [정보 수정] ---
SHEET_ID = "1uoDbuvVTooPlTjSQBjybfNW3CkXCQYPdf4-bXFRkqrQ"
API_URL = "https://script.google.com/macros/s/AKfybygyuZvtEiVQ31VZcqB4T5rXsc6-O9TsDq7BpQwl3OLsgd9hkHNOuKRhmPmM1ptKEuJ/exec"
# ------------------

CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

def load_data():
    try:
        # 데이터 읽어올 때 캐시 방지를 위해 랜덤 파라미터 추가 (선택사항)
        return pd.read_csv(CSV_URL)
    except:
        return pd.DataFrame(columns=["user_id", "type", "ticker", "buy_price", "qty"])

# 블랙 테마 스타일 (우리가 맞춘 그 감성)
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #000000; }
    [data-testid="stSidebar"] { background-color: #111111; }
    .stock-card {
        background-color: #1e1e1e;
        padding: 20px;
        border-radius: 15px;
        border-left: 5px solid #4CAF50;
        margin-bottom: 15px;
    }
    .metric-label { color: #888888; font-size: 0.9rem; }
    .metric-value { color: white; font-size: 1.5rem; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# 2. 사이드바
with st.sidebar:
    st.title("📡 E-7 RADAR")
    user_pw = st.text_input("🔑 접속 키 입력", type="password")
    
    if not user_pw:
        st.info("키를 입력하면 레이더가 가동됩니다.")
        st.stop()
    
    st.success(f"**{user_pw}**님 관제 시스템 접속")
    st.divider()
    
    st.subheader("➕ 종목 추가")
    with st.form("add_form", clear_on_submit=True):
        t_type = st.radio("구분", ["보유주식", "관심종목"])
        t_ticker = st.text_input("티커 (예: TSLA, AAPL)").upper()
        t_price = st.number_input("매수 평단", min_value=0.0, step=0.01)
        t_qty = st.number_input("보유 수량", min_value=0.0, step=0.01)
        
        if st.form_submit_button("레이더 등록"):
            if t_ticker:
                payload = {"user_id": str(user_pw), "type": str(t_type), "ticker": str(t_ticker), "buy_price": float(t_price), "qty": float(t_qty)}
                try:
                    res = requests.post(API_URL, json=payload)
                    if res.status_code == 200:
                        st.success("등록 완료! (데이터 갱신 중...)")
                        st.rerun()
                except:
                    st.error("전송 에러")

# 3. 메인 화면
df = load_data()

st.markdown("<h1 style='color:white;'>📊 실시간 관제탑</h1>", unsafe_allow_html=True)
st.divider()

if not df.empty and 'user_id' in df.columns:
    user_df = df[df['user_id'].astype(str) == str(user_pw)]
    
    if user_df.empty:
        st.info("현재 추적 중인 종목이 없습니다.")
    else:
        for _, row in user_df.iterrows():
            try:
                stock = yf.Ticker(str(row['ticker']))
                # 최신가 가져오기 (속도를 위해 period="1d")
                curr_data = stock.history(period="1d")
                if curr_data.empty: continue
                curr = curr_data['Close'].iloc[-1]
                prev = curr_data['Open'].iloc[-1] # 전일자 대신 당일 시가 대비
                
                # 색상 결정
                if row['type'] == "보유주식":
                    price = float(row['buy_price'])
                    rate = ((curr - price) / price * 100) if price > 0 else 0
                    color = "#FF4B4B" if rate < 0 else "#4CAF50" # 마이너스 빨강, 플러스 초록
                    
                    # 카드 형태 레이아웃
                    with st.container():
                        st.markdown(f"""
                        <div class="stock-card" style="border-left-color: {color};">
                            <span style="color: {color}; font-weight: bold;">{row['type']}</span>
                            <h3 style="margin: 0; color: white;">{row['ticker']}</h3>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("현재가", f"${curr:,.2f}", f"{rate:+.2f}%")
                        c2.metric("매수평단", f"${price:,.2f}")
                        c3.metric("보유수량", f"{row['qty']:,}")
                        # 평가금액 (현재가 * 수량)
                        total_val = curr * float(row['qty'])
                        c4.metric("평가금액", f"${total_val:,.2f}")
                        st.markdown("<br>", unsafe_allow_html=True)
                
                else: # 관심종목
                    with st.container():
                        st.markdown(f"""
                        <div class="stock-card" style="border-left-color: #555555;">
                            <span style="color: #888888;">{row['type']}</span>
                            <h3 style="margin: 0; color: white;">{row['ticker']}</h3>
                        </div>
                        """, unsafe_allow_html=True)
                        c1, c2 = st.columns(2)
                        diff = curr - prev
                        c1.metric("현재가", f"${curr:,.2f}", f"{diff:+.2f}")
                        st.markdown("<br>", unsafe_allow_html=True)
                        
            except:
                st.error(f"{row['ticker']} 데이터를 불러올 수 없습니다.")
else:
    st.warning("데이터 로드 실패. 구글 시트의 제목줄을 확인하세요.")
