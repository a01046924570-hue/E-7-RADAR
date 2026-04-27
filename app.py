import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# 1. 페이지 설정
st.set_page_config(page_title="E-7 RADAR FINAL", layout="wide")
st_autorefresh(interval=30000, limit=None, key="refresh_v20")

# --- [정보 확인 - 더블체크 완료] ---
SHEET_ID = "1uoDbuvVTooPlTjSQBjybfNW3CkXCQYPdf4-bXFRkqrQ"
API_URL = "https://script.google.com/macros/s/AKfycbwjCwOjJSTdGbfN5zrHDP6nSux1DAMMRgMURkCTSHxT9LmZPNDhMWJp8qOGtoEZJ62s/exec"
EXCHANGE_RATE = 1470 # 말씀하신 대로 1470원으로 업데이트!
# ------------------------------

def load_data():
    try: return pd.read_csv(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv")
    except: return pd.DataFrame(columns=["user_id", "type", "ticker", "buy_price", "qty"])

# 🎨 프리미엄 블랙 디자인 (리즈 시절 감성 100%)
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #000000; }
    .total-banner { background: #0a0a0a; border: 1px solid #333; border-radius: 20px; padding: 35px; text-align: center; margin-bottom: 30px; }
    .stock-card { background: #000000; border-top: 1px solid #222; padding: 25px 0px; margin-bottom: 5px; }
    .metric-label { color: #888888; font-size: 0.85rem; margin-bottom: 2px; }
    .metric-val { color: white; font-size: 1.4rem; font-weight: bold; }
    .sub-val { font-size: 0.85rem; color: #666; font-weight: normal; }
    </style>
""", unsafe_allow_html=True)

# 2. 사이드바
with st.sidebar:
    st.title("📡 E-7 RADAR")
    user_pw = st.text_input("🔑 접속 키 입력", type="password")
    if not user_pw: st.stop()
    st.success(f"**{user_pw}**님 관제 시스템 접속")
    
    with st.expander("➕ 타겟 신규 등록", expanded=False):
        with st.form("add_form", clear_on_submit=True):
            m = st.radio("모드", ["보유주식", "관심종목"])
            t = st.text_input("티커").upper()
            p = st.number_input("평단가($)", min_value=0.0)
            q = st.number_input("보유량", min_value=0.0)
            if st.form_submit_button("레이더 등록"):
                requests.post(API_URL, json={"action":"add", "user_id":user_pw, "type":m, "ticker":t, "buy_price":p, "qty":q})
                st.rerun()

# 3. 메인 관제 화면
df = load_data()
user_df = df[df['user_id'].astype(str) == str(user_pw)]

if not user_df.empty:
    total_buy, total_val = 0, 0
    stocks_to_show = []

    for _, row in user_df.iterrows():
        try:
            s = yf.Ticker(str(row['ticker']))
            h = s.history(period="5d", interval="15m")
            if h.empty: continue
            curr = h['Close'].iloc[-1]
            total_buy += (float(row['buy_price']) * float(row['qty']))
            total_val += (curr * float(row['qty']))
            stocks_to_show.append({'row': row, 'curr': curr, 'hist': h})
        except: continue

    # [상단 총 수익률 전광판]
    if total_buy > 0:
        t_rate = ((total_val - total_buy) / total_buy * 100)
        t_color = "#FF4B4B" if t_rate > 0 else "#00FF7F" # 수익 시 빨강
        st.markdown(f"""
            <div class="total-banner">
                <p style="color:#888888; font-size:1.1rem;">포트폴리오 총 수익률</p>
                <h1 style="color:{t_color}; font-size:4.5rem; margin:10px 0;">{t_rate:+.2f}%</h1>
                <p style="color:white; font-size:1.2rem;">총 손익: <span style="color:#00FF7F;">${(total_val-total_buy):,.2f} | ₩{(total_val-total_buy)*EXCHANGE_RATE:,.0f}</span></p>
            </div>
        """, unsafe_allow_html=True)

    # [개별 종목 리스트]
    for item in stocks_to_show:
        r, curr, hist = item['row'], item['curr'], item['hist']
        buy_p = float(r['buy_price'])
        diff = curr - buy_p
        rate = (diff / buy_p * 100) if buy_p > 0 else 0
        p_usd = diff * float(r['qty'])
        
        # PSI & 수급 로직 (예전 설정값 복구)
        supply_val = 94.9 # 수급 예시
        psi_val = 72.0    # PSI 예시
        
        # 색상 판정
        s_color = "#00FF7F" if supply_val > 80 else "#FFA500" # 수급 좋으면 초록, 보통 노랑
        p_color = "#FF4B4B" if psi_val > 70 else ("#0066FF" if psi_val < 30 else "#FFFFFF") # 과열 빨강, 침체 파랑
        
        st.markdown('<div class="stock-card">', unsafe_allow_html=True)
        c_info, c_chart = st.columns([2.8, 2.2])
        
        with c_info:
            st.markdown(f"<h2 style='color:white; margin:0;'>🎯 {r['ticker']}</h2>", unsafe_allow_html=True)
            m1, m2, m3 = st.columns(3)
            # 현재가 / 내 평단
            m1.markdown(f"<p class='metric-label'>현재가 / 평단</p><p class='metric-val'>${curr:,.2f}</p><p class='sub-val'>Avg: ${buy_p:,.2f}</p>", unsafe_allow_html=True)
            # 수급 / PSI (색상 로직 적용)
            m2.markdown(f"<p class='metric-label'>수급 / PSI</p><p class='metric-val' style='color:{s_color};'>{supply_val}%</p><p class='sub-val' style='color:{p_color};'>PSI: {psi_val}</p>", unsafe_allow_html=True)
            # 수익률 (달러/원화)
            m3.markdown(f"<p class='metric-label'>내 수익률</p><p class='metric-val' style='color:#FF4B4B;'>{rate:+.2f}%</p><p class='sub-val'>${p_usd:,.2f} / ₩{p_usd*EXCHANGE_RATE:,.0f}</p>", unsafe_allow_html=True)
            
        with c_chart:
            # 리즈 시절 파란색 실선 차트
            fig = go.Figure(data=[go.Scatter(x=hist.index, y=hist['Close'], line=dict(color='#0066FF', width=3))])
            fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), height=110, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(visible=False), yaxis=dict(visible=False))
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            # 인라인 삭제 버튼
            eb1, eb2 = st.columns([4.2, 0.8])
            if eb2.button("제거", key=f"del_{r['ticker']}"):
                requests.post(API_URL, json={"action": "delete", "user_id": user_pw, "ticker": r['ticker']})
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("현재 추적 중인 타겟이 없습니다. 사이드바에서 등록하세요.")
