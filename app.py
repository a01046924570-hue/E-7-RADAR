import streamlit as st
import yfinance as yf
import json
import os
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# 1. 데이터 관리
DB_FILE = "radar_data.json"
def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: pass
    return {"holdings": [], "watchlist": []}

def save_data(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

if 'db' not in st.session_state:
    st.session_state.db = load_data()

st.set_page_config(page_title="E-7 RADAR", layout="wide")
st_autorefresh(interval=15000, limit=None, key="refresh_v16_2")

# 2. 스타일링 설정
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #000000; }
    .label-text, [data-testid="stMetricLabel"] p { color: #FFFFFF !important; font-size: 1.1rem !important; font-weight: 600 !important; }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-weight: 900 !important; font-size: 2.5rem !important; }
    .stock-title { color: #FFFFFF !important; font-size: 1.8rem !important; font-weight: 800 !important; margin-bottom: 10px !important; display: block; }
    .total-card { background-color: #0a0a0a; padding: 30px; border-radius: 15px; border: 2px solid #333; text-align: center; margin-bottom: 40px; }
    hr { border-top: 2px solid #222; }
    </style>
""", unsafe_allow_html=True)

UP_COLOR, DOWN_COLOR = "#FF3131", "#1F51FF"

try: usd_krw = yf.Ticker("USDKRW=X").fast_info['last_price']
except: usd_krw = 1430.0

# 3. 사이드바 (등록 폼 최적화)
with st.sidebar:
    st.markdown("""
        <div style="margin-top: -60px; padding-bottom: 5px;">
            <h1 style='color: #000000; font-size: 2.1rem; font-weight: 950; letter-spacing: -1.5px; margin-bottom: 0; white-space: nowrap;'>E-7 RADAR</h1>
        </div>
    """, unsafe_allow_html=True)
    st.divider()
    
    st.header("🎮 관제 센터")
    view_mode = st.radio("모드 선택", ["내 보유 주식", "관심 종목 감시"])
    st.divider()
    
    with st.form("add_form", clear_on_submit=True):
        st.subheader(f"📍 {view_mode} 추가")
        t_code = st.text_input("종목코드 (예: TSLA, 005930.KS)").upper().strip()
        t_name = st.text_input("종목명")
        
        # 보유 주식 모드일 때만 평단가/수량 입력받기
        if view_mode == "내 보유 주식":
            t_price = st.number_input("평단가", min_value=0.0)
            t_qty = st.number_input("보유량", min_value=0.0)
        else:
            t_price, t_qty = 0.0, 0.0
            
        if st.form_submit_button("레이더 등록"):
            if t_code:
                key = "holdings" if view_mode == "내 보유 주식" else "watchlist"
                st.session_state.db[key].append({"ticker":t_code, "name":t_name or t_code, "price":t_price, "qty":t_qty})
                save_data(st.session_state.db)
                st.success(f"{t_code} 등록 완료!")
                st.rerun()
            else:
                st.error("코드를 입력하세요!")

# 4. 데이터 엔진
key = "holdings" if view_mode == "내 보유 주식" else "watchlist"
targets = st.session_state.db[key]
items_to_show = []

if not targets:
    st.warning(f"⚠️ {view_mode} 리스트가 비어있습니다. 왼쪽에서 종목을 추가해주세요.")
else:
    for idx, item in enumerate(targets):
        try:
            s = yf.Ticker(item['ticker'])
            hist = s.history(period="1mo")
            if hist.empty: continue
            
            curr, prev = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
            chg = ((curr - prev) / prev) * 100
            vol_pct = (hist['Volume'].iloc[-1] / hist['Volume'].iloc[-6:-1].mean() * 100)
            
            delta = hist['Close'].diff()
            rsi = 100 - (100 / (1 + (delta.clip(lower=0).tail(14).mean() / -delta.clip(upper=0).tail(14).mean())))
            
            # 수익률 계산 (보유 주식일 때만 의미 있음)
            is_kr = item['ticker'].endswith(('.KS', '.KQ'))
            avg_p = item['price'] / usd_krw if is_kr else item['price']
            p_rate = ((curr - avg_p) / avg_p * 100) if avg_p > 0 else 0.0
            p_val = (curr - avg_p) * item['qty']
            
            items_to_show.append({
                "item": item, "idx": idx, "curr": curr, "chg": chg, 
                "vol": vol_pct, "rsi": rsi, "hist": hist,
                "p_rate": p_rate, "p_val": p_val
            })
        except: continue

# 5. 상단 총 수익률 (보유 주식 모드 전용)
if view_mode == "내 보유 주식" and items_to_show:
    total_inv = sum((i['item']['price'] / usd_krw if i['item']['ticker'].endswith(('.KS', '.KQ')) else i['item']['price']) * i['item']['qty'] for i in items_to_show)
    total_prof = sum(i['p_val'] for i in items_to_show)
    if total_inv > 0:
        t_rate = (total_prof / total_inv) * 100
        st.markdown(f"""
            <div class="total-card">
                <p class="label-text">포트폴리오 총 수익률</p>
                <h1 style="color:{UP_COLOR if total_prof>=0 else DOWN_COLOR}; font-size:4.5rem; margin:10px 0; font-weight:900;">{t_rate:+.2f}%</h1>
                <p style="color:#FFFFFF; font-size:1.4rem; font-weight:bold;">총 손익: <span style="color:#00FF00;">${total_prof:,.2f}</span> | ₩{total_prof*usd_krw:,.0f}</p>
            </div>
        """, unsafe_allow_html=True)

# 6. 종목 리스트
for d in items_to_show:
    st.markdown(f'<span class="stock-title">🎯 {d["item"]["name"]} - {d["item"]["ticker"]}</span>', unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.metric("현재가", f"{d['curr']:,.2f}", f"{d['chg']:+.2f}%", delta_color="inverse")
    v_col = "#FF3131" if d['vol'] >= 150 else "#FFFF00" if d['vol'] >= 100 else "#FFFFFF"
    m2.markdown(f'<p class="label-text">수급 (5일 평균비)</p><p style="color:{v_col}; font-size:2.8rem; font-weight:900; margin:0;">{d["vol"]:.1f}%</p>', unsafe_allow_html=True)
    r_col = "#FF3131" if d['rsi'] > 70 else "#1F51FF" if d['rsi'] < 30 else "#FFA500"
    m3.markdown(f'<p class="label-text">심리지수 (RSI)</p><p style="color:{r_col}; font-size:2.8rem; font-weight:900; margin:0;">{d["rsi"]:.1f}</p>', unsafe_allow_html=True)

    c_left, c_right = st.columns([4, 1.5])
    with c_left:
        fig = go.Figure(go.Scatter(x=d['hist'].index, y=d['hist']['Close'], mode='lines', line=dict(color=UP_COLOR if d['chg']>=0 else DOWN_COLOR, width=3)))
        fig.update_layout(height=180, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='black', plot_bgcolor='black', xaxis_visible=False, yaxis_gridcolor='#222')
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    with c_right:
        if view_mode == "내 보유 주식":
            p_color = UP_COLOR if d['p_rate'] >= 0 else DOWN_COLOR
            st.markdown(f"""
                <p class="label-text">내 수익률</p>
                <p style="color:{p_color}; font-size:2.5rem; font-weight:900; margin:0;">{d['p_rate']:+.2f}%</p>
                <p style="color:#00FF00; font-size:1.2rem; font-weight:bold;">${d['p_val']:,.2f} / ₩{d['p_val']*usd_krw:,.0f}</p>
            """, unsafe_allow_html=True)
        
        with st.expander("⚙️ 관리"):
            if view_mode == "내 보유 주식":
                new_p = st.number_input("평단 수정", value=float(d['item']['price']), key=f"p_{d['idx']}")
                new_q = st.number_input("수량 수정", value=float(d['item']['qty']), key=f"q_{d['idx']}")
                if st.button("수정 완료", key=f"upd_{d['idx']}"):
                    targets[d['idx']]['price'], targets[d['idx']]['qty'] = new_p, new_q
                    save_data(st.session_state.db); st.rerun()
            if st.button("삭제", key=f"del_{d['idx']}", use_container_width=True):
                targets.pop(d['idx']); save_data(st.session_state.db); st.rerun()
    st.divider()