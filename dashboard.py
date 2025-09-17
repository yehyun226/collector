import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import glob, os, re

# === 데이터 불러오기 함수 ===
def load_txt(file_path):
    rows = []
    with open(file_path, encoding="utf-8") as f:
        block = {}
        for line in f:
            line = line.strip()
            if line.startswith("["):  # 시간 + 종목
                block["timestamp"] = re.search(r"\[(.*?)\]", line).group(1)
                block["symbol"] = line.split("종목:")[-1].strip()
            elif line.startswith("주가:"):
                parts = line.replace(" ", "").split("/")
                def safe_int(x): 
                    try: return int(x.split(":")[1])
                    except: return None
                def safe_float(x): 
                    try: return float(x.split(":")[1])
                    except: return None

                block["price"] = safe_int(parts[0])
                block["volume"] = safe_int(parts[1])
                block["cumulative_volume"] = safe_int(parts[2])
                block["strength"] = safe_float(parts[3]) if len(parts) > 3 else None

            elif line.startswith("매수상위:"):
                nums = re.findall(r"([가-힣A-Za-z]+)\s(\d+)", line)
                for i, (broker, val) in enumerate(nums, 1):
                    block[f"buy_{i}_broker"] = broker
                    block[f"buy_{i}_value"] = int(val)
                block["buy_sum"] = sum(int(v) for _, v in nums)

            elif line.startswith("매도상위:"):
                nums = re.findall(r"([가-힣A-Za-z]+)\s(\d+)", line)
                for i, (broker, val) in enumerate(nums, 1):
                    block[f"sell_{i}_broker"] = broker
                    block[f"sell_{i}_value"] = int(val)
                block["sell_sum"] = sum(int(v) for _, v in nums)
                rows.append(block)
                block = {}
    return pd.DataFrame(rows)

# === 경로 설정 ===
BASE_PATH = "data"
date_folders = sorted([f for f in os.listdir(BASE_PATH) if os.path.isdir(os.path.join(BASE_PATH, f))])

# === 사이드바 ===
st.sidebar.header("옵션 선택")
date_selected = st.sidebar.selectbox("날짜 선택", date_folders)

date_folder = os.path.join(BASE_PATH, date_selected)
files = glob.glob(os.path.join(date_folder, "*.txt"))
symbols = [os.path.splitext(os.path.basename(f))[0] for f in files]
symbol = st.sidebar.selectbox("종목 선택", symbols)

# === 데이터 로딩 ===
file_path = os.path.join(date_folder, f"{symbol}.txt")
df = load_txt(file_path)
df["timestamp"] = pd.to_datetime(df["timestamp"], format="%H:%M:%S")
df["net_flow"] = df["buy_sum"] - df["sell_sum"]

# === 통합 차트 ===
fig_all = go.Figure()
fig_all.add_trace(go.Scatter(x=df["timestamp"], y=df["price"], name="주가", mode="lines", yaxis="y1"))

# 옵션 토글
show_strength = st.sidebar.checkbox("체결강도", value=True)
show_volume   = st.sidebar.checkbox("거래량", value=True)
show_netflow  = st.sidebar.checkbox("순매수(매수-매도)", value=True)

if show_strength:
    fig_all.add_trace(go.Scatter(
        x=df["timestamp"], y=df["strength"], name="체결강도",
        mode="lines", yaxis="y2", line=dict(color="red")
    ))
if show_volume:
    fig_all.add_trace(go.Bar(
        x=df["timestamp"], y=df["volume"], name="거래량",
        yaxis="y3", marker_color="gray", opacity=0.5
    ))
if show_netflow:
    fig_all.add_trace(go.Scatter(
        x=df["timestamp"], y=df["net_flow"], name="순매수",
        mode="lines", yaxis="y4", line=dict(color="green")
    ))

fig_all.update_layout(
    title=f"{date_selected} {symbol} 통합 차트",
    xaxis=dict(title="시간"),
    yaxis=dict(title="주가", side="left"),
    yaxis2=dict(title="체결강도", overlaying="y", side="right", range=[0,200]),
    yaxis3=dict(title="거래량", overlaying="y", side="right"),
    yaxis4=dict(title="순매수", overlaying="y", side="right"),
    barmode="overlay",
    legend=dict(orientation="h", y=-0.3)
)
st.plotly_chart(fig_all, use_container_width=True)

# === 개별 차트 ===
st.subheader("개별 차트")

# 거래량 (막대)
fig_vol = px.bar(df, x="timestamp", y="volume", title="거래량", labels={"volume":"거래량"})
st.plotly_chart(fig_vol, use_container_width=True)

# 체결강도 (라인)
fig_strength = px.line(df, x="timestamp", y="strength", title="체결강도 (0~100)", color_discrete_sequence=["red"])
fig_strength.update_yaxes(range=[0,200])
st.plotly_chart(fig_strength, use_container_width=True)

# 매수총합
fig_buy_sum = px.line(df, x="timestamp", y="buy_sum", title="매수 총합", color_discrete_sequence=["blue"])
st.plotly_chart(fig_buy_sum, use_container_width=True)

# 매도총합
fig_sell_sum = px.line(df, x="timestamp", y="sell_sum", title="매도 총합", color_discrete_sequence=["orange"])
st.plotly_chart(fig_sell_sum, use_container_width=True)

# 순매수
fig_net = px.line(df, x="timestamp", y="net_flow", title="순매수 (매수 총합 - 매도 총합)", color_discrete_sequence=["green"])
st.plotly_chart(fig_net, use_container_width=True)

# 매수 Top5
fig_buy = go.Figure()
for i in range(1,6):
    if f"buy_{i}_value" in df:
        fig_buy.add_trace(go.Bar(x=df["timestamp"], y=df[f"buy_{i}_value"], name=df[f"buy_{i}_broker"].iloc[-1]))
fig_buy.update_layout(title="매수 Top5", barmode="stack")
st.plotly_chart(fig_buy, use_container_width=True)

# 매도 Top5
fig_sell = go.Figure()
for i in range(1,6):
    if f"sell_{i}_value" in df:
        fig_sell.add_trace(go.Bar(x=df["timestamp"], y=df[f"sell_{i}_value"], name=df[f"sell_{i}_broker"].iloc[-1]))
fig_sell.update_layout(title="매도 Top5", barmode="stack")
st.plotly_chart(fig_sell, use_container_width=True)
