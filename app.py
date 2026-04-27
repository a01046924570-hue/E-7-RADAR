import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from streamlit_autorefresh import st_autorefresh

# 1. 페이지 설정 및 자동 새로고침 (30초마다)
st.set_page_config(page_title="E-7 RADAR V20", layout="wide")
st_autorefresh(interval=30000, limit=None, key="refresh_v20")

# --- [이 부분을 본인의 정보로 정확히 수정하세요] ---
SHEET_ID = "1uoDbuvVTooPlTjSQBjybfNW3CkXCQYPdf4-bXFRkqrQ"

# 구글 앱스 스크립트 '새 배포' 후 받은 웹 앱 URL을 여기에 붙여넣으세요.
# 반드시 끝에 /exec 가 포함되어 있어야 합니다.
API_URL = "https://script.google.com/macros/s/AKfycbwjCwOjJSTdGbfN5zrHDP6nSux1DAMMRgMURkCTSHxT9LmZPNDhMWJp8qOGtoEZJ62s/exec"
# ------------------------------------------

# 구글 시트를 CSV 형식으로 읽어오는 주소
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

def load_data():
    try:
        # 실시간으로 구글 시트 데이터 가져오기
        return pd.read_csv(CSV_URL)
    except:
        # 에러 발생 시 빈 데이터프레임 반환
        return pd.DataFrame(columns=["user_id", "type", "ticker", "buy_price", "qty"])

# 블랙 테마 스타일링
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #000000; }
    .stMetric { background-color: #1e1e1e; padding: 15px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# 2. 사이드바 (로그인 및 종목 추가)
with st.sidebar:
    st.title("📡 E-7 RADAR")
    user_pw = st.text_input("🔑 접속 키 입력", type="password")
    
    if not user_pw:
        st.warning("접속 키를 입력해주세요.")
        st.stop()
    
    st.success(f"{user_pw}님 접속 중")
    st.divider()
    
    st.subheader("➕ 종목 추가")
    with st.form("add_form", clear_on_submit=True):
        t_type = st.radio("구분", ["보유주식", "관심종목"])
        t_ticker = st.text_input("티커 (예: TSLA, 005930.KS)").upper()
        t_price = st.number_input("매수 평단", min_value=0.0)
        t_qty = st.number_input("보유 수량", min_value=0.0)
        
        if st.form_submit_button("레이더 등록"):
            if t_ticker:
                # 구글 앱스 스크립트로 보낼 데이터 꾸러미
                payload = {
                    "user_id": str(user_pw),
                    "type": str(t_type),
                    "ticker": str(t_ticker),
                    "buy_price": float(t_price),
                    "qty": float(t_qty)
                }
                try:
                    # 다리(API)를 통해 구글 시트에 데이터 전송
                    response = requests.post(API_URL, json=payload)
                    if response.status_code == 200:
                        st.success("등록 완료! (데이터 반영까지 최대 10초)")
                        st.rerun()
                    else:
                        st.error(f"전송 실패: {response.status_code}")
                except Exception as e:
                    st.error(f"연결 오류: {e}")

# 3. 메인 화면 (실시간 관제탑)
df = load_data()

# 데이터가 있고 user_id 컬럼이 정상일 때만 출력
if not df.empty and 'user_id' in df.columns:
    # 현재 로그인한 키(user_pw)에 해당하는 데이터만 필터링
    user_df = df[df['user_id'].astype(str) == str(user_pw)]
    
    st.markdown("<h2 style='color:white;'>📊 실시간 관제탑</h2>", unsafe_allow_html=True)
    
    if user_df.empty:
        st.info("등록된 종목이 없습니다. 사이드바에서 종목을 추가해보세요!")
    else:
        # 보유 주식과 관심 종목을 리스트로 출력
        for _, row in user_df.iterrows():
            try:
                # 야후 파이낸스 실시간 가격 조회
                stock = yf.Ticker(str(row['ticker']))
                curr_data = stock.history(period="1d")
                if curr_data.empty:
                    continue
                curr = curr_data['Close'].iloc[-1]
                
                col1, col2, col3 = st.columns([1, 1, 1])
                
                if row['type'] == "보유주식":
                    buy_p = float(row['buy_price'])
                    # 수익률 계산
                    rate = ((curr - buy_p) / buy_p * 100) if buy_p > 0 else 0
                    col1.metric(row['ticker'], f"{curr:,.2f}", f"{rate:+.2f}%")
                    col2.write(f"**평단:** {buy_p:,.2f}")
                    col3.write(f"**수량:** {row['qty']}")
                else:
                    # 관심 종목은 수익률 없이 현재가만 표시
                    col1.metric(row['ticker'], f"{curr:,.2f}", "관심종목")
                    col2.write("-")
                    col3.write("-")
                st.divider()
            except Exception as e:
                st.error(f"{row['ticker']} 로딩 에러")
else:
    st.warning("구글 시트에 접근할 수 없거나 데이터 형식이 비어있습니다.")
    st.info("시트 1행에 user_id, type, ticker, buy_price, qty 제목이 있는지 확인하세요.")
