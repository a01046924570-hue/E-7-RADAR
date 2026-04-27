import streamlit as st
import yfinance as yf
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go

# 1. 페이지 기본 설정
st.set_page_config(page_title="E-7 RADAR Multi", layout="wide")
st_autorefresh(interval=60000, limit=None, key="refresh")

# --- [여기에 구글 시트 주소를 붙여넣으세요] ---
url = "https://docs.google.com/spreadsheets/d/1uoDbuvVTooPlTjSQBjybfNW3CkXCQYPdf4-bXFRkqrQ/edit?usp=sharing"
# ------------------------------------------

# 2. 구글 시트 연결 설정
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # 구글 시트에서 데이터를 읽어옵니다
        return conn.read(spreadsheet=url, ttl=0)
    except:
        # 시트가 비어있을 경우 기본 틀을 만듭니다
        return pd.DataFrame(columns=["user_id", "type", "ticker", "name", "price", "qty"])

# 3. 사이드바 로그인 및 메뉴
with st.sidebar:
    st.title("📡 E-7 RADAR")
    user_pw = st.text_input("🔑 개인 접속 키 입력", type="password")
    
    if not user_pw:
        st.info("접속 키를 입력해야 데이터가 보입니다.")
        st.stop()

    st.success(f"접속 중: {user_pw}")
    menu = st.radio("메뉴 선택", ["실시간 관제탑", "종목 관리(추가/삭제)"])

# 데이터 불러오기
df = load_data()
# 로그인한 사용자의 데이터만 필터링
user_df = df[df['user_id'] == user_pw].copy()

# 4. 메뉴별 화면 구성
if menu == "실시간 관제탑":
    st.subheader(f"📊 {user_pw}님의 실시간 레이더")
    
    if user_df.empty:
        st.warning("등록된 종목이 없습니다. '종목 관리' 메뉴에서 추가하세요!")
    else:
        # 실시간 가격 업데이트 로직 (요약 버전)
        for index, row in user_df.iterrows():
            with st.container():
                stock = yf.Ticker(row['ticker'])
                curr_price = stock.history(period="1d")['Close'].iloc[-1]
                
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.write(f"**{row['ticker']}**")
                with col2:
                    st.metric("현재가", f"{curr_price:,.2f}")
                with col3:
                    st.write(f"수량: {row['qty']}")
                st.divider()

elif menu == "종목 관리(추가/삭제)":
    st.subheader("🛠 종목 추가 및 삭제")
    
    # 종목 추가 폼
    with st.form("add_stock"):
        t_input = st.text_input("티커 입력 (예: TSLA, 005930.KS)")
        q_input = st.number_input("보유 수량", min_value=0.0, step=0.1)
        add_btn = st.form_submit_button("레이더 등록")
        
        if add_btn and t_input:
            new_row = pd.DataFrame([{
                "user_id": user_pw,
                "type": "holdings",
                "ticker": t_input.upper(),
                "name": t_input,
                "price": 0,
                "qty": q_input
            }])
            # 기존 데이터에 합치고 구글 시트 업데이트
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(spreadsheet=url, data=updated_df)
            st.success("구글 시트에 저장되었습니다!")
            st.rerun()

    # 종목 삭제 기능
    if not user_df.empty:
        st.divider()
        st.write("🗑 종목 삭제")
        target_del = st.selectbox("삭제할 종목 선택", user_df['ticker'].tolist())
        if st.button("선택 종목 삭제"):
            # 해당 유저의 해당 티커만 제외하고 나머지 저장
            final_df = df[~((df['user_id'] == user_pw) & (df['ticker'] == target_del))]
            conn.update(spreadsheet=url, data=final_df)
            st.error(f"{target_del} 삭제 완료!")
            st.rerun()
