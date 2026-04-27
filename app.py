import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from streamlit_autorefresh import st_autorefresh

# 1. 기본 설정
st.set_page_config(page_title="E-7 RADAR V20", layout="wide")
st_autorefresh(interval=30000, limit=None, key="refresh_v20")

# --- [여기를 본인의 정보로 갈아 끼우세요] ---
SHEET_ID = "1uoDbuvVTooPlTjSQBjybfNW3CkXCQYPdf4-bXFRkqrQ"
# 방금 스크린샷에서 본 '웹 앱 URL'을 아래 큰따옴표 안에 붙여넣으세요!
API_URL = "https://script.google.com/macros/s/AKfycbygyuZvtEiVQ31VZcqB4T5rXsc6-O9TsDq7BpQwl3OLsgd9hkHNOuKRhmPmM1ptKEuJ/exec"
# ------------------------------------------

CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

def load_data():
    try:
        # 구글 시트 데이터를 실시간으로 읽어옴
        return pd.read_csv(CSV_URL)
    except:
        return pd.DataFrame(columns=["user_id", "type", "ticker", "buy_price", "qty"])

# 디자인 설정
st.markdown("<style>[data-testid='stAppViewContainer'] { background-color: #000000; }</style>", unsafe_allow_html=True)

# 사이드바 (등록 기능)
with st.sidebar:
    st.title("📡 E-7 RADAR")
    user_pw = st.text_input("🔑 접속 키 입력", type="password")
    if not user_pw: st.stop()
    
    st.success(f"{user_pw}님 접속 중")
    st.divider()
    
    st.subheader("➕ 종목 추가")
    with st.form("add_form", clear_on_submit=True):
        t_type = st.radio("구분", ["보유주식", "관심종목"])
        t_ticker = st.text_input("티커 (예: TSLA, 005930.KS)").upper()
        t_price = st.number_input("평단", min_value=0.0)
        t_qty = st.number_input("수량", min_value=0.0)
        
        if st.form_submit_button("레이더 등록"):
            if t_ticker:
                # 구글 앱스 스크립트(API)로 데이터 전송
                payload = {
                    "user_id": str(user_pw),
                    "type": str(t_type),
                    "ticker": str(t_ticker),
                    "buy_price": float(t_price),
                    "qty": float(t_qty)
                }
                try:
                    response = requests.post(API_URL, json=payload)
                    if response.status_code == 200:
                        st.success("등록 완료! (약 5~10초 뒤 반영)")
                        st.rerun()
                except:
                    st.error("전송 실패. API 주소를 확인하세요.")

# 메인 화면 (관제탑 출력)
df = load_data()
# user_id 컬럼이 있는지 확인 후 필터링
if not df.empty and 'user_id' in df.columns:
    user_df = df[df['user_id'].astype(str) == str(user_pw)]
    
    st.markdown("<h2 style='color:white;'>📊 실시간 관제탑</h2>", unsafe_allow_html=True)
    
    if user_df.empty:
        st.info("등록된 종목이 없습니다. 왼쪽에서 등록해 보세요!")
    else:
        for _, row in user_df.iterrows():
            try:
                stock = yf.Ticker(str(row['ticker']))
                curr = stock.history(period="1d")['Close'].iloc[-1]
                
                col1, col2, col3 = st.columns([1, 1, 1])
                if row['type'] == "보유주식":
                    price = float(row['buy_price'])
                    rate = ((curr - price) / price * 100) if price > 0 else 0
                    col1.metric(row['ticker'], f"{curr:,.2f}", f"{rate:+.2f}%")
                    col2.write(f"평단: {price:,.2f}")
                    col3.write(f"수량: {row['qty']}")
                else:
                    col1.metric(row['ticker'], f"{curr:,.2f}", "관심종목")
                st.divider()
            except:
                continue
else:
    st.warning("시트에 데이터가 없거나 형식이 잘못되었습니다. 1행 제목을 확인하세요!")
