import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime
import time
import os

st.set_page_config(page_title="風帆車計時系統", page_icon="⛵", layout="wide")

st.title("⛵ 風帆車行駛計時系統")
st.markdown("---")

def _init(key, val):
    if key not in st.session_state:
        st.session_state[key] = val

_init("running", False)
_init("start_time", None)
_init("elapsed", 0.0)
_init("laps", [])
_init("lap_start", None)
_init("cam_mode", False)
_init("trigger_count", 0)


def fmt(seconds: float) -> str:
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


def do_start():
    st.session_state.running = True
    st.session_state.start_time = time.time()
    if st.session_state.lap_start is None:
        st.session_state.lap_start = st.session_state.elapsed


def do_lap(car_name, route, distance_km, wind_speed, wind_dir, notes):
    e = current_elapsed()
    lap_elapsed = e - (st.session_state.lap_start or 0)
    lap_num = len(st.session_state.laps) + 1
    avg_speed = (distance_km / (lap_elapsed / 3600)) if lap_elapsed > 0 else 0
    st.session_state.laps.append({
        "圈次": lap_num, "車輛": car_name, "路線": route,
        "圈次時間": fmt(lap_elapsed), "累計時間": fmt(e),
        "距離 (km)": distance_km, "平均速度 (km/h)": round(avg_speed, 2),
        "風速 (m/s)": wind_speed, "風向": wind_dir,
        "記錄時間": datetime.now().strftime("%H:%M:%S"), "備註": notes,
    })
    st.session_state.lap_start = e


def do_reset():
    st.session_state.running = False
    st.session_state.start_time = None
    st.session_state.elapsed = 0.0
    st.session_state.lap_start = None
    st.session_state.trigger_count = 0


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 設定")
    car_name    = st.text_input("風帆車名稱 / 編號", value="風帆車 #1")
    route       = st.text_input("路線名稱",          value="標準賽道 A")
    distance_km = st.number_input("路線距離 (km)",   min_value=0.0, value=1.0, step=0.1, format="%.2f")
    wind_speed  = st.number_input("風速 (m/s)",      min_value=0.0, value=5.0, step=0.5, format="%.1f")
    wind_dir    = st.selectbox("風向", ["北", "東北", "東", "東南", "南", "西南", "西", "西北"])
    notes       = st.text_area("備註", placeholder="天氣、場地狀況…")
    st.markdown("---")
    st.subheader("📷 相機偵測設定")
    cam_line_pos    = st.slider("感測線位置 (%)", 10, 90, 50)
    cam_sensitivity = st.slider("靈敏度",          5, 80, 25)
    cam_cooldown    = st.slider("冷卻時間 (秒)",   1, 10,  3)
    st.info("對準賽道終點線，偵測風帆車穿越感測線自動計時。")


# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_manual, tab_camera = st.tabs(["⏱ 手動計時", "📷 相機計時"])


# ════════════════════════════════════════════════════════════
# Tab 1 — Manual
# ════════════════════════════════════════════════════════════
with tab_manual:
    col_timer, col_info = st.columns([2, 1])
    with col_timer:
        st.subheader("⏱ 計時器")
        elapsed_now = current_elapsed()
        st.markdown(
            f"<div style='font-size:4rem;font-weight:bold;font-family:monospace;"
            f"color:#1f77b4;text-align:center;padding:20px 0;'>{fmt(elapsed_now)}</div>",
            unsafe_allow_html=True,
        )
        if st.session_state.lap_start is not None:
            lap_elapsed = elapsed_now - st.session_state.lap_start
            st.markdown(
                f"<div style='font-size:1.5rem;color:#888;text-align:center;'>圈次時間: {fmt(lap_elapsed)}</div>",
                unsafe_allow_html=True,
            )
        b1, b2, b3 = st.columns(3)
        with b1:
            if not st.session_state.running:
                if st.button("▶ 開始", use_container_width=True, type="primary", key="m_start"):
                    do_start(); st.rerun()
            else:
                if st.button("⏸ 暫停", use_container_width=True, key="m_pause"):
                    st.session_state.elapsed = current_elapsed()
                    st.session_state.running = False
                    st.session_state.start_time = None
                    st.rerun()
        with b2:
            if st.button("🏁 記圈", use_container_width=True,
                         disabled=not st.session_state.running, key="m_lap"):
                do_lap(car_name, route, distance_km, wind_speed, wind_dir, notes); st.rerun()
        with b3:
            if st.button("🔄 重置", use_container_width=True, key="m_reset"):
                do_reset(); st.rerun()
        if st.session_state.running:
            time.sleep(0.05); st.rerun()

    with col_info:
        st.subheader("📊 即時資訊")
        elapsed_now = current_elapsed()
        if elapsed_now > 0 and distance_km > 0:
            st.metric("目前均速", f"{distance_km / (elapsed_now / 3600):.1f} km/h")
        else:
            st.metric("目前均速", "—")
        st.metric("風速", f"{wind_speed} m/s")
        st.metric("風向", wind_dir)
        st.metric("路線距離", f"{distance_km} km")
        st.metric("已記圈次", len(st.session_state.laps))
        if st.session_state.laps:
            sec_list = []
            for lap in st.session_state.laps:
                t = lap["圈次時間"]; p = t.split(":")
                if len(p) == 2:   sec_list.append(int(p[0]) * 60 + float(p[1]))
                elif len(p) == 3: sec_list.append(int(p[0]) * 3600 + int(p[1]) * 60 + float(p[2]))
            st.metric("平均圈次時間", fmt(sum(sec_list) / len(sec_list)))


# ════════════════════════════════════════════════════════════
# Tab 2 — Camera
# ════════════════════════════════════════════════════════════
with tab_camera:
    st.subheader("📷 相機自動計時")
    st.markdown(
        "將相機<b>對準終點線</b>，點擊「🟢 啟用偵測」後，"
        "風帆車穿越<span style='color:#1ed760;font-weight:bold;'>綠色感測線</span>時會自動計時。",
        unsafe_allow_html=True,
    )
    col_cam, col_cam_info = st.columns([3, 1])

    with col_cam:
        component_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "camera_component")
        camera_component = components.declare_component("sailing_camera", path=component_dir)
        cam_event = camera_component(
            line_pos=cam_line_pos,
            sensitivity=cam_sensitivity,
            cooldown=cam_cooldown,
            key="cam",
            default=None,
        )
        if cam_event is not None:
            ev_type = cam_event.get("type")
            if ev_type == "armed":
                st.session_state.cam_mode = True
                st.session_state.trigger_count = 0
            elif ev_type == "disarmed":
                st.session_state.cam_mode = False
            elif ev_type == "motion":
                count = cam_event.get("count", 1)
                if st.session_state.cam_mode:
                    if not st.session_state.running:
                        do_start()
                        st.session_state.trigger_count = count
                        st.toast("🚀 偵測到動作 — 計時開始！", icon="⏱")
                    else:
                        do_lap(car_name, route, distance_km, wind_speed, wind_dir, notes)
                        st.session_state.trigger_count = count
                        st.toast(f"🏁 記錄第 {len(st.session_state.laps)} 圈！", icon="🏁")
                    st.rerun()
            elif ev_type == "manual_start":
                if not st.session_state.running:
                    do_start(); st.rerun()
            elif ev_type == "manual_stop":
                if st.session_state.running:
                    do_lap(car_name, route, distance_km, wind_speed, wind_dir, notes)
                    st.session_state.elapsed = current_elapsed()
                    st.session_state.running = False
                    st.session_state.start_time = None
                    st.rerun()

    with col_cam_info:
        st.subheader("📊 計時狀態")
        elapsed_now = current_elapsed()
        st.metric("狀態", "🟢 計時中" if st.session_state.running else "⏸ 停止")
        st.metric("目前時間", fmt(elapsed_now))
        st.metric("已記圈次", len(st.session_state.laps))
        st.metric("偵測觸發次數", st.session_state.trigger_count)
        if elapsed_now > 0 and distance_km > 0:
            st.metric("均速", f"{distance_km / (elapsed_now / 3600):.1f} km/h")
        st.markdown("---")
        st.markdown(
            f"<div style='font-size:2.8rem;font-weight:bold;font-family:monospace;"
            f"color:#1f77b4;text-align:center;'>{fmt(elapsed_now)}</div>",
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 重置", use_container_width=True, key="c_reset"):
                do_reset(); st.rerun()
        with c2:
            if st.button("⏹ 停止", use_container_width=True, key="c_stop",
                         disabled=not st.session_state.running):
                st.session_state.elapsed = current_elapsed()
                st.session_state.running = False
                st.session_state.start_time = None
                st.rerun()
        if st.session_state.running:
            time.sleep(0.1); st.rerun()

    st.markdown("""
**使用方式：**
1. 拖曳左側欄「感測線位置」，對準畫面中的終點線
2. 點擊相機畫面中的「🟢 啟用偵測」
3. 第一次穿越感測線 → **自動開始計時**
4. 再次穿越感測線 → **自動記圈**
5. 按右側「⏹ 停止」結束計時
    """)


# ── Shared lap records ────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📋 圈次記錄")

if st.session_state.laps:
    df = pd.DataFrame(st.session_state.laps)

    def highlight_best(s):
        if s.name != "圈次時間":
            return [""] * len(s)
        min_idx = s.tolist().index(min(s.tolist()))
        return ["background-color: #d4edda" if i == min_idx else "" for i in range(len(s))]

    st.dataframe(df.style.apply(highlight_best), use_container_width=True, hide_index=True)

    col_dl, col_clear = st.columns([1, 5])
    with col_dl:
        csv = df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            "⬇ 下載 CSV", data=csv,
            file_name=f"sailing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )
    with col_clear:
        if st.button("🗑 清除記錄"):
            st.session_state.laps = []; st.rerun()

    if len(st.session_state.laps) >= 2:
        st.subheader("📈 圈次時間趨勢")
        sec_list = []
        for lap in st.session_state.laps:
            t = lap["圈次時間"]; p = t.split(":")
            if len(p) == 2:   sec_list.append(int(p[0]) * 60 + float(p[1]))
            elif len(p) == 3: sec_list.append(int(p[0]) * 3600 + int(p[1]) * 60 + float(p[2]))
        chart_df = pd.DataFrame({
            "圈次": [l["圈次"] for l in st.session_state.laps],
            "圈次時間 (秒)": sec_list,
            "平均速度 (km/h)": [l["平均速度 (km/h)"] for l in st.session_state.laps],
        }).set_index("圈次")
        t_time, t_speed = st.tabs(["圈次時間", "平均速度"])
        with t_time:  st.line_chart(chart_df[["圈次時間 (秒)"]])
        with t_speed: st.line_chart(chart_df[["平均速度 (km/h)"]])
else:
    st.info("尚無圈次記錄。使用「手動計時」或「相機計時」開始記錄成績。")

st.markdown("---")
st.caption("風帆車計時系統 © 2026 — 以 Streamlit 製作")
