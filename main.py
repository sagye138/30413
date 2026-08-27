import streamlit as st
import pandas as pd
import json
import urllib.request
import time
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 페이지 설정 및 다크모드 커스텀 CSS
st.set_page_config(page_title="Crypto Futures Terminal", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* 전체 배경 */
    .stApp { background-color: #0b0e11; color: #ffffff !important; font-family: sans-serif; }
    section[data-testid="stSidebar"] { background-color: #181a20; border-right: 1px solid #2b313a; }
    
    /* 레이아웃 카드 */
    .header-card { background-color: #181a20; border-radius: 8px; padding: 12px 20px; border: 1px solid #2b313a; margin-bottom: 12px; }
    .trade-box { background-color: #181a20; border: 1px solid #2b313a; border-radius: 8px; padding: 16px; margin-bottom: 10px; }
    
    /* 텍스트 컬러 */
    .green-text { color: #0ecb81 !important; }
    .red-text { color: #f6465d !important; }
    .gray-text { color: #848e9c !important; }
    
    /* 입력창 기본 스타일 */
    div[data-baseweb="input"] {
        background-color: #1e2329 !important;
        border: 1px solid #474d57 !important;
        border-radius: 4px !important;
    }
    input {
        background-color: #1e2329 !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    /* 코인 선택창 (Selectbox) 전체 요소 CSS 강제 고정 */
    div[data-baseweb="select"], 
    div[data-baseweb="select"] *,
    div[data-baseweb="popover"],
    div[data-baseweb="popover"] *,
    ul[role="listbox"],
    ul[role="listbox"] li,
    div[role="option"] {
        background-color: #1e2329 !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }
    
    /* 선택목록 마우스 호버 시 처리 */
    ul[role="listbox"] li:hover,
    div[role="option"]:hover,
    li[aria-selected="true"] {
        background-color: #2b313a !important;
        color: #0ecb81 !important;
        -webkit-text-fill-color: #0ecb81 !important;
    }
    
    /* 라벨 및 텍스트 흰색 설정 */
    label, p, span, div {
        color: #ffffff !important;
    }
    .gray-text { color: #848e9c !important; }

    /* 버튼 스타일 */
    div.stButton > button {
        background-color: #2b313a !important;
        color: #ffffff !important;
        border: 1px solid #474d57 !important;
        border-radius: 4px;
        font-weight: 600;
        height: 42px;
    }
    div.stButton > button:hover {
        background-color: #363c4e !important;
        border-color: #848e9c !important;
    }

    /* 롱/숏 전용 버튼 */
    .btn-long button { background-color: #0ecb81 !important; color: #ffffff !important; border: none !important; }
    .btn-long button:hover { background-color: #0ba368 !important; }
    .btn-short button { background-color: #f6465d !important; color: #ffffff !important; border: none !important; }
    .btn-short button:hover { background-color: #d6384c !important; }
</style>
""", unsafe_allow_html=True)

# 2. 업비트 API 정보 수집
def get_upbit_detail(ticker="KRW-BTC"):
    try:
        url = f"https://api.upbit.com/v1/ticker?markets={ticker}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())[0]
            return {
                "price": float(data['trade_price']),
                "high": float(data['high_price']),
                "low": float(data['low_price']),
                "change_rate": float(data['signed_change_rate']) * 100,
                "volume": float(data['acc_trade_price_24h']),
                "trade_volume": float(data['acc_trade_volume_24h'])
            }
    except Exception:
        return None

# 3. 세션 상태 초기화
if "cash" not in st.session_state: st.session_state.cash = 10_000_000
if "position_type" not in st.session_state: st.session_state.position_type = None
if "position_size" not in st.session_state: st.session_state.position_size = 0
if "entry_price" not in st.session_state: st.session_state.entry_price = 0
if "margin" not in st.session_state: st.session_state.margin = 0
if "leverage" not in st.session_state: st.session_state.leverage = 10
if "ohlc_data" not in st.session_state: st.session_state.ohlc_data = []
if "running" not in st.session_state: st.session_state.running = True
if "tp_pct" not in st.session_state: st.session_state.tp_pct = 0.0
if "sl_pct" not in st.session_state: st.session_state.sl_pct = 0.0
if "trade_logs" not in st.session_state: st.session_state.trade_logs = []
if "input_margin" not in st.session_state: st.session_state.input_margin = int(st.session_state.cash)
if "current_ticker" not in st.session_state: st.session_state.current_ticker = "KRW-BTC"

# 4. 사이드바 - 설정 및 요청 코인 6종 정의
st.sidebar.markdown("### TERMINAL SETTINGS")

coin_map = {
    "BTC/KRW (비트코인)": "KRW-BTC",
    "LTC/KRW (라이트코인)": "KRW-LTC",
    "ETH/KRW (이더리움)": "KRW-ETH",
    "TRX/KRW (트론)": "KRW-TRX",
    "USDT/KRW (테더)": "KRW-USDT",
    "BNB/KRW (바이낸스코인)": "KRW-BNB"
}

selected_coin_label = st.sidebar.selectbox("Market Ticker", list(coin_map.keys()))
ticker = coin_map[selected_coin_label]

# 코인 종류 변경 시 이전 코인 차트 데이터 초기화
if st.session_state.current_ticker != ticker:
    st.session_state.current_ticker = ticker
    st.session_state.ohlc_data = []

st.session_state.leverage = st.sidebar.select_slider(
    "Leverage (레버리지)", options=[1, 2, 5, 10, 20, 50, 75, 100, 125], value=st.session_state.leverage
)

st.sidebar.markdown("---")
st.sidebar.markdown("### CHART INDICATORS")
show_ma5 = st.sidebar.checkbox("이동평균선 MA 5", value=True)
show_ma20 = st.sidebar.checkbox("이동평균선 MA 20", value=True)
show_ma60 = st.sidebar.checkbox("이동평균선 MA 60", value=False)
show_rsi = st.sidebar.checkbox("RSI 보조지표 (14)", value=True)

st.sidebar.markdown("---")
col_s1, col_s2 = st.sidebar.columns(2)
if col_s1.button("Stream On/Off", use_container_width=True):
    st.session_state.running = not st.session_state.running

if col_s2.button("Reset", use_container_width=True):
    st.session_state.cash = 10_000_000
    st.session_state.input_margin = 10_000_000
    st.session_state.position_type = None
    st.session_state.position_size = 0
    st.session_state.entry_price = 0
    st.session_state.margin = 0
    st.session_state.ohlc_data = []
    st.session_state.trade_logs = []
    st.rerun()

# 5. 시세 처리 및 차트 데이터 갱신
market_data = get_upbit_detail(ticker)
if market_data is None:
    st.error("시세 데이터를 불러오는데 실패했습니다.")
    st.stop()

curr_price = market_data['price']
now_str = datetime.now().strftime("%H:%M:%S")

if not st.session_state.ohlc_data:
    init_vol = curr_price * 0.05
    st.session_state.ohlc_data.append({
        "time": now_str, "open": curr_price, "high": curr_price,
        "low": curr_price, "close": curr_price, "vol": init_vol
    })
else:
    last_candle = st.session_state.ohlc_data[-1]
    new_open = last_candle["close"]
    new_high = max(new_open, curr_price)
    new_low = min(new_open, curr_price)
    vol = abs(curr_price - new_open) * 10 + 100000
    
    st.session_state.ohlc_data.append({
        "time": now_str, "open": new_open, "high": new_high,
        "low": new_low, "close": curr_price, "vol": vol
    })
    if len(st.session_state.ohlc_data) > 60:
        st.session_state.ohlc_data.pop(0)

df = pd.DataFrame(st.session_state.ohlc_data)

# 지표 계산
df["MA5"] = df["close"].rolling(window=5).mean()
df["MA20"] = df["close"].rolling(window=20).mean()
df["MA60"] = df["close"].rolling(window=60).mean()

delta = df["close"].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
df["RSI"] = 100 - (100 / (1 + rs))

# 6. PnL 계산
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

# 7. 상단 헤더
change_class = "green-text" if market_data['change_rate'] >= 0 else "red-text"
st.markdown(f"""
<div class="header-card">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <span style="font-size: 20px; font-weight: bold; color: #ffffff;">{selected_coin_label.split()[0]} PERPETUAL</span>
            <span style="background-color: #2b313a; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin-left: 8px; color: #f0b90b;">{st.session_state.leverage}x</span>
        </div>
        <div>
            <span class="gray-text">24h High:</span> <span style="margin-right: 12px; color: #ffffff;">{market_data['high']:,.0f}</span>
            <span class="gray-text">24h Low:</span> <span style="margin-right: 12px; color: #ffffff;">{market_data['low']:,.0f}</span>
            <span class="gray-text">24h Vol:</span> <span style="color: #ffffff;">{market_data['volume']/1e8:,.1f} 억</span>
        </div>
    </div>
    <div style="display: flex; gap: 20px; margin-top: 6px; align-items: baseline;">
        <span style="font-size: 26px; font-weight: bold;" class="{change_class}">{curr_price:,.0f} KRW</span>
        <span class="{change_class}" style="font-weight: bold;">{market_data['change_rate']:+.2f}%</span>
    </div>
</div>
""", unsafe_allow_html=True)

# 8. 메인 레이아웃 분할
col_left, col_right = st.columns([7, 5])

with col_left:
    rows = 3 if show_rsi else 2
    row_heights = [0.6, 0.2, 0.2] if show_rsi else [0.7, 0.3]
    
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=row_heights)
    
    # 캔들스틱
    fig.add_trace(go.Candlestick(
        x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color='#0ecb81', decreasing_line_color='#f6465d', name="OHLC"
    ), row=1, col=1)
    
    # 이동평균선
    if show_ma5:
        fig.add_trace(go.Scatter(x=df['time'], y=df['MA5'], mode='lines', line=dict(color='#f0b90b', width=1.2), name="MA5"), row=1, col=1)
    if show_ma20:
        fig.add_trace(go.Scatter(x=df['time'], y=df['MA20'], mode='lines', line=dict(color='#e024c3', width=1.2), name="MA20"), row=1, col=1)
    if show_ma60:
        fig.add_trace(go.Scatter(x=df['time'], y=df['MA60'], mode='lines', line=dict(color='#00bfff', width=1.2), name="MA60"), row=1, col=1)
        
    # 차트 내 진입 평단가 선 표시 (포지션 보유 시)
    if st.session_state.position_type and st.session_state.entry_price > 0:
        line_color = "#0ecb81" if st.session_state.position_type == "LONG" else "#f6465d"
        fig.add_hline(
            y=st.session_state.entry_price, 
            line_dash="dash", 
            line_color=line_color, 
            line_width=1.5,
            annotation_text=f"ENTRY ({st.session_state.position_type}): {st.session_state.entry_price:,.0f}",
            annotation_position="top right",
            annotation_font_color=line_color,
            row=1, col=1
        )

    # 거래량
    colors = ['#0ecb81' if c >= o else '#f6465d' for c, o in zip(df['close'], df['open'])]
    fig.add_trace(go.Bar(x=df['time'], y=df['vol'], marker_color=colors, name="Volume"), row=2, col=1)
    
    # RSI
    if show_rsi:
        fig.add_trace(go.Scatter(x=df['time'], y=df['RSI'], line=dict(color='#f0b90b', width=1), name="RSI(14)"), row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#f6465d", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#0ecb81", row=3, col=1)

    fig.update_layout(
        template="plotly_dark", paper_bgcolor='#181a20', plot_bgcolor='#181a20',
        margin=dict(l=10, r=10, t=10, b=10), height=380, showlegend=False,
        xaxis_rangeslider_visible=False
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- 주문 패널 ---
    st.markdown('<div class="trade-box">', unsafe_allow_html=True)
    st.markdown("##### ORDER PANEL")
    
    # 비율 버튼
    b1, b2, b3, b4 = st.columns(4)
    if b1.button("25%"):
        st.session_state.input_margin = int(st.session_state.cash * 0.25)
        st.rerun()
    if b2.button("50%"):
        st.session_state.input_margin = int(st.session_state.cash * 0.50)
        st.rerun()
    if b3.button("75%"):
        st.session_state.input_margin = int(st.session_state.cash * 0.75)
        st.rerun()
    if b4.button("100% Max"):
        st.session_state.input_margin = int(st.session_state.cash)
        st.rerun()

    o_col1, o_col2 = st.columns(2)
    with o_col1:
        formatted_val = f"{int(st.session_state.input_margin):,}"
        user_input_str = st.text_input("증거금 직접 입력 (KRW)", value=formatted_val)
        
        try:
            clean_val = int("".join(filter(str.isdigit, user_input_str)))
            st.session_state.input_margin = min(clean_val, int(st.session_state.cash))
        except ValueError:
            st.session_state.input_margin = 0
            
    with o_col2:
        coin_qty = (st.session_state.input_margin * st.session_state.leverage) / curr_price if curr_price > 0 else 0
        st.write(" ")
        st.write(f"주문 수량: **{coin_qty:,.4f} 코인**")

    tp_col, sl_col = st.columns(2)
    with tp_col: 
        st.session_state.tp_pct = st.number_input("목표 익절 (TP %)", value=float(st.session_state.tp_pct), step=5.0, format="%.1f")
    with sl_col: 
        st.session_state.sl_pct = st.number_input("최대 손절 (SL %)", value=float(st.session_state.sl_pct), step=5.0, format="%.1f")

    btn1, btn2 = st.columns(2)
    with btn1:
        st.markdown('<div class="btn-long">', unsafe_allow_html=True)
        if st.button("OPEN LONG (롱 진입)", use_container_width=True, disabled=st.session_state.position_type is not None):
            if st.session_state.input_margin > 0:
                st.session_state.margin = st.session_state.input_margin
                st.session_state.cash -= st.session_state.input_margin
                st.session_state.position_size = st.session_state.input_margin * st.session_state.leverage
                st.session_state.entry_price = curr_price
                st.session_state.position_type = "LONG"
                st.session_state.trade_logs.insert(0, f"[{now_str}] OPEN LONG @ {curr_price:,.0f} KRW")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with btn2:
        st.markdown('<div class="btn-short">', unsafe_allow_html=True)
        if st.button("OPEN SHORT (숏 진입)", use_container_width=True, disabled=st.session_state.position_type is not None):
            if st.session_state.input_margin > 0:
                st.session_state.margin = st.session_state.input_margin
                st.session_state.cash -= st.session_state.input_margin
                st.session_state.position_size = st.session_state.input_margin * st.session_state.leverage
                st.session_state.entry_price = curr_price
                st.session_state.position_type = "SHORT"
                st.session_state.trade_logs.insert(0, f"[{now_str}] OPEN SHORT @ {curr_price:,.0f} KRW")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)
    with m1:
        if st.button("50% 반익/반손", use_container_width=True, disabled=st.session_state.position_type is None):
            st.session_state.cash += (st.session_state.margin / 2) + (pnl / 2)
            st.session_state.margin /= 2
            st.session_state.position_size /= 2
            st.session_state.trade_logs.insert(0, f"[{now_str}] PARTIAL CLOSE 50%")
            st.rerun()
    with m2:
        if st.button("전량 청산", use_container_width=True, disabled=st.session_state.position_type is None):
            st.session_state.cash += st.session_state.margin + pnl
            st.session_state.trade_logs.insert(0, f"[{now_str}] CLOSE POSITION | PnL: {int(pnl):+} KRW")
            st.session_state.position_type = None
            st.session_state.margin = 0
            st.session_state.entry_price = 0
            st.rerun()
    with m3:
        if st.button("스위칭 (REVERSE)", use_container_width=True, disabled=st.session_state.position_type is None):
            st.session_state.cash += st.session_state.margin + pnl
            new_type = "SHORT" if st.session_state.position_type == "LONG" else "LONG"
            new_m = min(st.session_state.margin, st.session_state.cash)
            st.session_state.cash -= new_m
            st.session_state.margin = new_m
            st.session_state.entry_price = curr_price
            st.session_state.position_type = new_type
            st.session_state.trade_logs.insert(0, f"[{now_str}] REVERSE TO {new_type}")
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

with col_right:
    st.markdown('<div class="trade-box">', unsafe_allow_html=True)
    st.markdown("##### ACCOUNT & POSITION SUMMARY")
    st.markdown(f"**Total Wallet Balance:** `{int(total_asset):,} KRW`")
    st.markdown(f"**Available Balance:** `{int(st.session_state.cash):,} KRW`")
    st.markdown(f"**Margin In Use:** `{int(st.session_state.margin):,} KRW`")
    st.markdown("---")
    
    if st.session_state.position_type:
        pos_color = "green-text" if st.session_state.position_type == "LONG" else "red-text"
        st.markdown(f"### <span class='{pos_color}'>{st.session_state.position_type}</span> <span style='font-size:16px;'>{st.session_state.leverage}x</span>", unsafe_allow_html=True)
        
        liq = st.session_state.entry_price * (1 - (1/st.session_state.leverage)) if st.session_state.position_type == "LONG" else st.session_state.entry_price * (1 + (1/st.session_state.leverage))
        holding_qty = st.session_state.position_size / st.session_state.entry_price if st.session_state.entry_price > 0 else 0
        
        c_p1, c_p2 = st.columns(2)
        c_p1.metric("평단가 (Avg Entry)", f"{st.session_state.entry_price:,.0f} KRW")
        c_p2.metric("청산가 (Liq Price)", f"{liq:,.0f} KRW")
        
        c_p3, c_p4 = st.columns(2)
        c_p3.metric("보유 수량", f"{holding_qty:,.4f}")
        c_p4.metric("포지션 규모", f"{int(st.session_state.position_size):,} KRW")
        
        st.metric("미실현 손익 (PnL)", f"{int(pnl):+} KRW", delta=f"{pnl_pct:+.2f}%", delta_color="normal")
    else:
        st.info("보유 중인 포지션이 없습니다.")
    st.markdown('</div>', unsafe_allow_html=True)

    # 호가창
    st.markdown('<div class="trade-box">', unsafe_allow_html=True)
    st.markdown("##### REAL-TIME ORDERBOOK (호가창)")
    for i in range(3, 0, -1):
        ask_p = curr_price + (i * (curr_price * 0.001))
        ask_vol = int(ask_p * 0.002)
        st.caption(f"매도호가 {ask_p:,.0f} KRW | 잔량: {ask_vol:,} Qty")
    st.markdown(f"**현재가 {curr_price:,.0f} KRW**")
    for i in range(1, 4):
        bid_p = curr_price - (i * (curr_price * 0.001))
        bid_vol = int(bid_p * 0.0025)
        st.caption(f"매수호가 {bid_p:,.0f} KRW | 잔량: {bid_vol:,} Qty")
    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("Execution Logs", expanded=True):
        for log in st.session_state.trade_logs[:8]:
            st.caption(log)

# 9. 자동 청산 및 루프
if st.session_state.position_type:
    if pnl_pct <= -100:
        st.error("[LIQUIDATED] 강제 청산되었습니다!")
        st.session_state.position_type = None
        st.session_state.margin = 0
        st.rerun()
    elif st.session_state.tp_pct > 0 and pnl_pct >= st.session_state.tp_pct:
        st.success("[AUTO TP] 목표 익절 달성!")
        st.session_state.cash += st.session_state.margin + pnl
        st.session_state.position_type = None
        st.session_state.margin = 0
        st.rerun()
    elif st.session_state.sl_pct > 0 and pnl_pct <= -st.session_state.sl_pct:
        st.warning("[AUTO SL] 손절 한도 도달!")
        st.session_state.cash += st.session_state.margin + pnl
        st.session_state.position_type = None
        st.session_state.margin = 0
        st.rerun()

if st.session_state.running:
    time.sleep(1)
    st.rerun()
