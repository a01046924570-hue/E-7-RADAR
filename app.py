import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import requests

# 1. 페이지 설정
st.set_page_config(page_title="E-7 RADAR FINAL", layout="wide")
st_autorefresh(interval=30000, limit=None, key="refresh_final")

# --- [수정 필수] ---
# 구글 시트 ID (주소창의 /d/ 와 /edit 사이의 문자열)
SHEET_ID = "1uoDbuvVTooPlTjSQBjybfNW3CkXCQYPdf4-bXFRkqrQ"
# 구글 시트가 '링크가 있는 모든 사용자-편집자'로 되어 있어야 합니다.
# ------------------

# 구글 시트를 CSV 형태로 읽어오는 주소
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

def load_data():
    try:
        # 구글 시트에서 직접 CSV를 읽어옵니다.
        return pd.read_csv(CSV_URL)
    except:
        return pd.DataFrame(columns=["user_id", "type", "ticker", "buy_price", "qty"])

# 2. 스타일링 (기존 검정 테마 유지)
st.markdown("<style>[data-testid='stAppViewContainer'] { background-color: #000000; }</style>", unsafe_allow_html=True)

# 3. 사이드바 로그인 및 추가
with st.sidebar:
    st.title("📡 E-7 RADAR")
    user_pw = st.text_input("🔑 접속 키 입력", type="password")
    if not user_pw: st.stop()
    st.success(f"{user_pw}님 접속 중")
    
    st.subheader("➕ 종목 추가")
    # 구글 시트에 직접 쓰기는 웹 앱 환경에서 Google API 설정이 복잡하므로, 
    # 사용자님께 '구글 시트 바로가기' 링크를 드려 직접 수정하게 하는게 가장 안전합니다.
    st.markdown(f"[🔗 내 구글 시트 열기](https://docs.google.com/spreadsheets/d/{SHEET_ID})")
    st.info("위 링크를 눌러 시트에 데이터를 직접 적으면 앱에 실시간 반영됩니다!")

# 4. 메인 화면 출력
df = load_data()
if not df.empty:
    user_df = df[df['user_id'].astype(str) == str(user_pw)]
    
    st.markdown("<h2 style='color:white;'>📊 실시간 관제탑</h2>", unsafe_allow_html=True)
    
    # 보유주식/관심종목 구분 출력
    for t_type in ["보유주식", "관심종목"]:
        st.subheader(f"📍 {t_type}")
        sub_df = user_df[user_df['type'] == t_type]
        
        if sub_df.empty:
            st.write("데이터가 없습니다.")
            continue
            
        for _, row in sub_df.iterrows():
            try:
                stock = yf.Ticker(str(row['ticker']))
                curr = stock.history(period="1d")['Close'].iloc[-1]
                
                col1, col2, col3 = st.columns([1, 1, 1])
                if t_type == "보유주식":
                    price = float(row['buy_price'])
                    rate = ((curr - price) / price * 100) if price > 0 else 0
                    col1.metric(row['ticker'], f"{curr:,.2f}", f"{rate:+.2f}%")
                    col2.write(f"평단: {price:,.2f}")
                    col3.write(f"수량: {row['qty']}")
                else:
                    col1.metric(row['ticker'], f"{curr:,.2f}")
                st.divider()
            except:
                st.error(f"{row['ticker']} 로딩 실패")
