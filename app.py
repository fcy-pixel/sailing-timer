import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="風帆車計時系統", page_icon="⛵", layout="wide")

st.title("⛵ 風帆車行駛計時系統")
st.markdown("---")

# ── Session state init ──────────────────────────────────────────────────────
if "running" not in st.session_state:
    st.session_state.running = False
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "elapsed" not in st.session_state:
    st.session_state.elapsed = 0.0
if "laps" not in st.session_state:
    st.session_state.laps = []          # list of dicts
if "lap_start" not in st.session_state:
    st.session_state.lap_start = None   # elapsed at last lap mark

# ── Helper ──────────────────────────────────────────────────────────────────
def fmt(seconds: float) -> str:
    """Format seconds → HH:MM:SS.xx"""
    s = int(seconds)
    ms = int((seconds - s) * 100)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h:02d}:{m:02d}:{sec:02d}.{ms:02d}"
    return f"{m:02d}:{sec:02d}.{ms:02d}"

def current_elapsed() -> float:
    if st.session_state.running and st.session_state.start_time:
        return st.session_state.elapsed + (time.time() - st.session_state.start_time)
    return st.session_state.elapsed

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 行駛設定")
    car_name = st.text_input("風帆車名稱 / 編號", value="風帆車 #1")
    route = st.text_input("路線名稱", value="標準賽道 A")
    distance_km = st.number_input("路線距離 (公里)", min_value=0.0, value=1.0, step=0.1, format="%.2f")
    wind_speed = st.number_input("風速 (m/s)", min_value=0.0, value=5.0, step=0.5, format="%.1f")
    wind_dir = st.selectbox("風向", ["北", "東北", "東", "東南", "南", "西南", "西", "西北"])
    notes = st.text_area("備註", placeholder="天氣、場地狀況…")

# ── Main area ────────────────────────────────────────────────────────────────
col_timer, col_info = st.columns([2, 1])

with col_timer:
    st.subheader("⏱ 計時器")

    # big display
    elapsed_now = current_elapsed()
    timer_display = fmt(elapsed_now)

    st.markdown(
        f"<div style='font-size:4rem;font-weight:bold;font-family:monospace;"
        f"color:#1f77b4;text-align:center;padding:20px 0;'>{timer_display}</div>",
        unsafe_allow_html=True,
    )

    # lap time display
    if st.session_state.lap_start is not None:
        lap_elapsed = elapsed_now - st.session_state.lap_start
        st.markdown(
            f"<div style='font-size:1.5rem;color:#888;text-align:center;'>圈次時間: {fmt(lap_elapsed)}</div>",
            unsafe_allow_html=True,
        )

    # control buttons
    btn1, btn2, btn3 = st.columns(3)

    with btn1:
        if not st.session_state.running:
            if st.button("▶ 開始", use_container_width=True, type="primary"):
                st.session_state.running = True
                st.session_state.start_time = time.time()
                if st.session_state.lap_start is None:
                    st.session_state.lap_start = st.session_state.elapsed
                st.rerun()
        else:
            if st.button("⏸ 暫停", use_container_width=True):
                st.session_state.elapsed = current_elapsed()
                st.session_state.running = False
                st.session_state.start_time = None
                st.rerun()

    with btn2:
        lap_disabled = not st.session_state.running
        if st.button("🏁 記圈", use_container_width=True, disabled=lap_disabled):
            e = current_elapsed()
            lap_elapsed = e - (st.session_state.lap_start or 0)
            lap_num = len(st.session_state.laps) + 1
            avg_speed = (distance_km / (lap_elapsed / 3600)) if lap_elapsed > 0 else 0
            st.session_state.laps.append({
                "圈次": lap_num,
                "車輛": car_name,
                "路線": route,
                "圈次時間": fmt(lap_elapsed),
                "累計時間": fmt(e),
                "距離 (km)": distance_km,
                "平均速度 (km/h)": round(avg_speed, 2),
                "風速 (m/s)": wind_speed,
                "風向": wind_dir,
                "記錄時間": datetime.now().strftime("%H:%M:%S"),
                "備註": notes,
            })
            st.session_state.lap_start = e
            st.rerun()

    with btn3:
        if st.button("🔄 重置", use_container_width=True):
            st.session_state.running = False
            st.session_state.start_time = None
            st.session_state.elapsed = 0.0
            st.session_state.lap_start = None
            st.rerun()

    # auto-refresh while running
    if st.session_state.running:
        time.sleep(0.05)
        st.rerun()

with col_info:
    st.subheader("📊 即時資訊")
    elapsed_now = current_elapsed()

    if elapsed_now > 0 and distance_km > 0:
        speed_kmh = distance_km / (elapsed_now / 3600)
        st.metric("目前均速", f"{speed_kmh:.1f} km/h")
    else:
        st.metric("目前均速", "—")

    st.metric("風速", f"{wind_speed} m/s")
    st.metric("風向", wind_dir)
    st.metric("路線距離", f"{distance_km} km")
    st.metric("已記圈次", len(st.session_state.laps))

    # estimated finish if we have laps
    if st.session_state.laps:
        lap_times = []
        for lap in st.session_state.laps:
            t = lap["圈次時間"]
            parts = t.split(":")
            if len(parts) == 2:
                mins, secs = parts
                lap_times.append(int(mins) * 60 + float(secs))
            elif len(parts) == 3:
                h, m, s = parts
                lap_times.append(int(h) * 3600 + int(m) * 60 + float(s))
        avg_lap = sum(lap_times) / len(lap_times)
        st.metric("平均圈次時間", fmt(avg_lap))

# ── Lap records ──────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📋 圈次記錄")

if st.session_state.laps:
    df = pd.DataFrame(st.session_state.laps)

    # highlight best lap
    def highlight_best(s):
        if s.name != "圈次時間":
            return [""] * len(s)
        min_idx = s.tolist().index(min(s.tolist()))
        return ["background-color: #d4edda" if i == min_idx else "" for i in range(len(s))]

    st.dataframe(
        df.style.apply(highlight_best),
        use_container_width=True,
        hide_index=True,
    )

    col_dl, col_clear = st.columns([1, 5])
    with col_dl:
        csv = df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            "⬇ 下載 CSV",
            data=csv,
            file_name=f"sailing_timer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )
    with col_clear:
        if st.button("🗑 清除記錄"):
            st.session_state.laps = []
            st.rerun()

    # chart
    if len(st.session_state.laps) >= 2:
        st.subheader("📈 圈次時間趨勢")
        chart_df = pd.DataFrame({
            "圈次": [lap["圈次"] for lap in st.session_state.laps],
            "圈次时间(秒)": [],
        })
        sec_list = []
        for lap in st.session_state.laps:
            t = lap["圈次時間"]
            parts = t.split(":")
            if len(parts) == 2:
                sec_list.append(int(parts[0]) * 60 + float(parts[1]))
            elif len(parts) == 3:
                sec_list.append(int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2]))
        chart_df = pd.DataFrame({
            "圈次": [lap["圈次"] for lap in st.session_state.laps],
            "圈次時間 (秒)": sec_list,
            "平均速度 (km/h)": [lap["平均速度 (km/h)"] for lap in st.session_state.laps],
        }).set_index("圈次")
        tab_time, tab_speed = st.tabs(["圈次時間", "平均速度"])
        with tab_time:
            st.line_chart(chart_df[["圈次時間 (秒)"]])
        with tab_speed:
            st.line_chart(chart_df[["平均速度 (km/h)"]])
else:
    st.info("尚無圈次記錄。點擊「▶ 開始」計時，再按「🏁 記圈」記錄每圈成績。")

st.markdown("---")
st.caption("風帆車計時系統 © 2026 — 以 Streamlit 製作")
