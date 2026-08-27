import streamlit as st
import pandas as pd
import json
import urllib.request
import time

st.set_page_config(page_title="Real-time Crypto Futures Simulator", layout="wide")

# 1. 업비트 API로 실시간 코인 시세 조회
def get_upbit_price(ticker="KRW-BTC"):
    try:
        url = f"https://api.upbit.com/v1/ticker?markets={ticker}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return float(data[0]['trade_price'])
    except Exception:
        return None

# 2. 세션 상태 초기화
if "cash" not in st.session_state:
    st.session_state.cash = 10_000_000  # 시드머니 1,000만 원
if "position_type" not in st.session_state:
    st.session_state.position_type = None  # None, 'LONG', 'SHORT'
if "position_size" not in st.session_state:
    st.session_state.position_size = 0  # 포지션 가치 (원화)
if "entry_price" not in st.session_state:
    st.session_state.entry_price = 0  # 진입가
if "margin" not in st.session_state:
    st.session_state.margin = 0  # 투입 증거금
if "leverage" not in st.session_state:
    st.session_state.leverage = 1
if "price_history" not in st.session_state:
    st.session_state.price_history = []
if "running" not in st.session_state:
    st.session_state.running = False

# 3. 사이드바 - 코인 선택 및 설정
st.sidebar.title("⚙️ 선물 거래소 설정")

coin_map = {
    "비트코인 (BTC)": "KRW-BTC",
    "이더리움 (ETH)": "KRW-ETH",
    "리플 (XRP)": "KRW-XRP",
    "솔라나 (SOL)": "KRW-SOL",
    "도지코인 (DOGE)": "KRW-DOGE"
}
selected_coin_name = st.sidebar.selectbox("거래할 코인 선택", list(coin_map.keys()))
ticker = coin_map[selected_coin_name]

st.session_state.leverage = st.sidebar.select_slider(
    "레버리지 설정", options=[1, 2, 5, 10, 20, 50, 100], value=st.session_state.leverage
)

col_start, col_reset = st.sidebar.columns(2)
if col_start.button("▶ 시세 동기화 시작/중지"):
    st.session_state.running = not st.session_state.running

if col_reset.button("🔄 시드머니 리셋"):
    st.session_state.cash = 10_000_000
    st.session_state.position_type = None
    st.session_state.position_size = 0
    st.session_state.entry_price = 0
    st.session_state.margin = 0
    st.session_state.price_history = []
    st.session_state.running = False
    st.rerun()

# 4. 실시간 현재가 획득
curr_price = get_upbit_price(ticker)

if curr_price is None:
    st.error("업비트 시세를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.")
    st.stop()

if not st.session_state.price_history or st.session_state.price_history[-1] != curr_price:
    st.session_state.price_history.append(curr_price)
    if len(st.session_state.price_history) > 50:
        st.session_state.price_history.pop(0)

# 5. 미실현 손익(PnL) 및 수익률 계산
pnl = 0
pnl_pct = 0.0

if st.session_state.position_type == "LONG":
    price_diff_pct = (curr_price - st.session_state.entry_price) / st.session_state.entry_price
    pnl_pct = price_diff_pct * 100 * st.session_state.leverage
    pnl = st.session_state.margin * (pnl_pct / 100)
elif st.session_state.position_type == "SHORT":
    price_diff_pct = (st.session_state.entry_price - curr_price) / st.session_state.entry_price
    pnl_pct = price_diff_pct * 100 * st.session_state.leverage
    pnl = st.session_state.margin * (pnl_pct / 100)

total_asset = st.session_state.cash + st.session_state.margin + pnl

# 6. 대시보드 출력
st.title(f"🚀 업비트 실시간 선물 시뮬레이터 ({selected_coin_name})")

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("실시간 현재가", f"{curr_price:,.0f} 원")
m2.metric("총 자산", f"{int(total_asset):,} 원")
m3.metric("주문 가능 잔고", f"{int(st.session_state.cash):,} 원")
m4.metric("현재 포지션", f"{st.session_state.position_type} ({st.session_state.leverage}x)" if st.session_state.position_type else "무포지션")
m5.metric("수익률 (PnL)", f"{pnl_pct:+.2f}% ({int(pnl):+}원)" if st.session_state.position_type else "0.00%", delta_color="normal")

st.divider()

# 차트
st.line_chart(pd.DataFrame({"실시간 시세": st.session_state.price_history}), height=300)

# 7. 주문 컨트롤러
c1, c2, c3 = st.columns(3)

with c1:
    if st.button("🟢 롱(Long) 풀매수", use_container_width=True, disabled=st.session_state.position_type is not None):
        if st.session_state.cash > 0:
            st.session_state.margin = st.session_state.cash
            st.session_state.position_size = st.session_state.cash * st.session_state.leverage
            st.session_state.entry_price = curr_price
            st.session_state.position_type = "LONG"
            st.session_state.cash = 0
            st.rerun()

with c2:
    if st.button("🔴 숏(Short) 풀매수", use_container_width=True, disabled=st.session_state.position_type is not None):
        if st.session_state.cash > 0:
            st.session_state.margin = st.session_state.cash
            st.session_state.position_size = st.session_state.cash * st.session_state.leverage
            st.session_state.entry_price = curr_price
            st.session_state.position_type = "SHORT"
            st.session_state.cash = 0
            st.rerun()

with c3:
    if st.button("⚡ 포지션 전량 청산", use_container_width=True, disabled=st.session_state.position_type is None):
        st.session_state.cash += st.session_state.margin + pnl
        st.session_state.position_type = None
        st.session_state.margin = 0
        st.session_state.position_size = 0
        st.session_state.entry_price = 0
        st.rerun()

# 8. 청산 조건 체크 및 실시간 갱신 루프
if st.session_state.position_type and pnl_pct <= -100:
    st.error("💥 손실률 -100% 도달! 강제 청산(청산빔) 당했습니다!")
    st.session_state.position_type = None
    st.session_state.margin = 0
    st.session_state.position_size = 0
    st.session_state.entry_price = 0
    st.session_state.running = False
    st.rerun()

if st.session_state.running:
    time.sleep(1)  # 1초마다 업비트 실시간 시세 갱신
    st.rerun()
