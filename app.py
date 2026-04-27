import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# 1. 페이지 설정
st.set_page_config(page_title="E-7 RADAR FINAL", layout="wide")
st_autorefresh(interval=30000, limit=None, key="refresh_v20")

# --- [정보 확인] ---
SHEET_ID = "1uoDbuvVTooPlTjSQBjybfNW3CkXCQYPdf4-bXFRkqrQ"
API_URL = "https://script.google.com/macros/s/AKfycbwBlV403lrsg_d3BQ81Y3qF6-_Jel_YdU1x8U8YrUHT9snFj_cvyn3HP0WmJz8aQfy4/exec"
EXCHANGE_RATE = 1470 

def load_data():
    try: return pd.read_csv(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv")
    except: return pd.DataFrame(columns=["user_id", "type", "ticker", "buy_price", "qty"])

def calculate_rsi(data, window=14):
    delta = data.diff()
    up = delta.clip(lower=0); down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=window-1, adjust=False).mean()
    ema_down = down.ewm(com=window-1, adjust=False).mean()
    rs = ema_up / (ema_down + 1e-10)
    return 100 - (100 / (1 + rs))

# 🎨 디자인 (CSS)
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

# 2. 사이드바 (모드 선택 및 필터링 핵심)
with st.sidebar:
    st.title("📡 E-7 RADAR")
    user_pw = st.text_input("🔑 접속 키 입력", type="password")
    if not user_pw: st.stop()
    
    st.divider()
    # 핵심: 화면에 보여줄 모드 선택
    display_mode = st.radio("모드 선택", ["내 보유 주식", "관심 종목 감시"])
    
    with st.expander("➕ 타겟 신규 등록", expanded=False):
        with st.form("add_form", clear_on_submit=True):
            m = st.radio("구분", ["보유주식", "관심종목"])
            t = st.text_input("티커").upper()
            p = st.number_input("평단가($)", min_value=0.0) if m == "보유주식" else 0.0
            q = st.number_input("보유량", min_value=0.0) if m == "보유주식" else 0.0
            if st.form_submit_button("레이더 등록"):
                requests.post(API_URL, json={"action":"add", "user_id":user_pw, "type":m, "ticker":t, "buy_price":p, "qty":q})
                st.rerun()

# 3. 데이터 로드 및 필터링
df = load_data()
user_df = df[df['user_id'].astype(str) == str(user_pw)]

# 필터링 로직: 선택한 모드와 데이터의 type 매칭
filter_type = "보유주식" if display_mode == "내 보유 주식" else "관심종목"
filtered_df = user_df[user_df['type'] == filter_type]

if not filtered_df.empty:
    total_buy, total_val = 0, 0
    stocks_to_show = []

    for idx, row in filtered_df.iterrows():
        try:
            s = yf.Ticker(str(row['ticker']))
            h = s.history(period="15d", interval="1d") 
            h_live = s.history(period="2d", interval="15m")
            if h.empty or h_live.empty: continue
            
            curr = h_live['Close'].iloc[-1]
            prev_close = h['Close'].iloc[-2]
            day_change = ((curr - prev_close) / prev_close * 100)
            
            avg_vol = h['Volume'].tail(5).mean()
            supply_val = (h['Volume'].iloc[-1] / avg_vol * 100) if avg_vol > 0 else 0
            psi_val = calculate_rsi(h['Close']).iloc[-1]
            
            if row['type'] == "보유주식":
                total_buy += (float(row['buy_price']) * float(row['qty']))
                total_val += (curr * float(row['qty']))
            
            stocks_to_show.append({'row': row, 'curr': curr, 'change': day_change, 'hist': h_live, 'idx': idx, 'supply': supply_val, 'psi': psi_val})
        except: continue

    # [보유 주식 모드일 때만 전광판 표시]
    if display_mode == "내 보유 주식" and total_buy > 0:
        t_rate = ((total_val - total_buy) / total_buy * 100)
        t_color = "#FF4B4B" if t_rate >= 0 else "#0066FF" 
        st.markdown(f'<div class="total-banner"><h1 style="color:{t_color}; font-size:4.5rem;">{t_rate:+.2f}%</h1><p style="color:white;">총 손익: <span style="color:{t_color};">${(total_val-total_buy):,.2f} | ₩{(total_val-total_buy)*EXCHANGE_RATE:,.0f}</span></p></div>', unsafe_allow_html=True)

    # [리스트 표시]
    for item in stocks_to_show:
        r, curr, day_change, hist, i, supply, psi = item['row'], item['curr'], item['change'], item['hist'], item['idx'], item['supply'], item['psi']
        s_color = "#00FF7F" if supply > 120 else ("#FFA500" if supply > 80 else "#888888")
        p_color = "#FF4B4B" if psi > 70 else ("#0066FF" if psi < 30 else "#FFFFFF")
        
        st.markdown('<div class="stock-card">', unsafe_allow_html=True)
        c_info, c_chart = st.columns([2.8, 2.2])
        
        with c_info:
            st.markdown(f"<h2 style='color:white; margin:0;'>🎯 {r['ticker']}</h2>", unsafe_allow_html=True)
            m1, m2, m3 = st.columns(3)
            
            if r['type'] == "보유주식":
                buy_p, qty = float(r['buy_price']), float(r['qty'])
                rate = ((curr - buy_p) / buy_p * 100) if buy_p > 0 else 0
                p_usd = (curr - buy_p) * qty
                profit_color = "#FF4B4B" if rate >= 0 else "#0066FF"
                m1.markdown(f"<p class='metric-label'>현재가 / 평단</p><p class='metric-val'>${curr:,.2f}</p><p class='sub-val'>Avg: ${buy_p:,.2f}</p>", unsafe_allow_html=True)
                m2.markdown(f"<p class='metric-label'>수급 / PSI</p><p class='metric-val' style='color:{s_color};'>{supply:.1f}%</p><p class='sub-val' style='color:{p_color};'>PSI: {psi:.1f}</p>", unsafe_allow_html=True)
                m3.markdown(f"<p class='metric-label'>내 수익률</p><p class='metric-val' style='color:{profit_color};'>{rate:+.2f}%</p><p class='sub-val'>${p_usd:,.2f} / ₩{p_usd*EXCHANGE_RATE:,.0f}</p>", unsafe_allow_html=True)
            else:
                change_color = "#FF4B4B" if day_change >= 0 else "#0066FF"
                m1.markdown(f"<p class='metric-label'>현재가</p><p class='metric-val'>${curr:,.2f}</p>", unsafe_allow_html=True)
                m2.markdown(f"<p class='metric-label'>수급 / PSI</p><p class='metric-val' style='color:{s_color};'>{supply:.1f}%</p><p class='sub-val' style='color:{p_color};'>PSI: {psi:.1f}</p>", unsafe_allow_html=True)
                m3.markdown(f"<p class='metric-label'>전일대비</p><p class='metric-val' style='color:{change_color};'>{day_change:+.2f}%</p>", unsafe_allow_html=True)
            
        with c_chart:
            fig = go.Figure(data=[go.Scatter(x=hist.index, y=hist['Close'], line=dict(color='#0066FF', width=3))])
            fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), height=110, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(visible=False), yaxis=dict(visible=False))
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"chart_{i}")
            
            manage_col1, manage_col2 = st.columns([3, 2])
            with manage_col2:
                with st.popover("⚙️ 수정/삭제", use_container_width=True):
                    st.write(f"**{r['ticker']} 관리**")
                    new_p = st.number_input("평단가 수정", value=float(r['buy_price']), key=f"p_{i}")
                    new_q = st.number_input("보유량 수정", value=float(r['qty']), key=f"q_{i}")
                    c1, c2 = st.columns(2)
                    if c1.button("업데이트", key=f"upd_{i}"):
                        requests.post(API_URL, json={"action": "delete", "user_id": user_pw, "ticker": r['ticker']})
                        requests.post(API_URL, json={"action": "add", "user_id": user_pw, "type": r['type'], "ticker": r['ticker'], "buy_price": new_p, "qty": new_q})
                        st.rerun()
                    if c2.button("완전 삭제", key=f"del_{i}"):
                        requests.post(API_URL, json={"action": "delete", "user_id": user_pw, "ticker": r['ticker']})
                        st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info(f"현재 등록된 {filter_type}이 없습니다.")
