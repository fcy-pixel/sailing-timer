import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime
import time
import os

st.set_page_config(page_title="風帆車計時系統", page_icon="⛵", layout="wide")
st.title("⛵ 風帆車行駛計時系統")
st.markdown("---")

# ── Shared race state — stored in memory, shared across ALL sessions ──────────
# st.cache_resource lives in the same Python process for every connected device.
# Two phones on the same Streamlit Cloud URL share this dict automatically.
@st.cache_resource
def _race_store() -> dict:
    return {}

def read_race(code: str = "DEFAULT") -> dict:
    return _race_store().get(
        code, {"status": "idle", "start_time": None, "last_elapsed": None}
    )

def write_race(data: dict, code: str = "DEFAULT"):
    _race_store()[code] = data

# ── Session state ─────────────────────────────────────────────────────────────
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

# ── Helpers ───────────────────────────────────────────────────────────────────
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
    _save_lap(e, car_name, route, distance_km, wind_speed, wind_dir, notes)
    st.session_state.lap_start = e

def do_lap_direct(elapsed, car_name, route, distance_km, wind_speed, wind_dir, notes):
    _save_lap(elapsed, car_name, route, distance_km, wind_speed, wind_dir, notes)

def _save_lap(elapsed, car_name, route, distance_km, wind_speed, wind_dir, notes):
    lap_num = len(st.session_state.laps) + 1
    avg_speed = (distance_km / (elapsed / 3600)) if elapsed > 0 else 0
    st.session_state.laps.append({
        "圈次": lap_num, "車輛": car_name, "路線": route,
        "行駛時間": fmt(elapsed),
        "距離 (km)": distance_km, "平均速度 (km/h)": round(avg_speed, 2),
        "風速 (m/s)": wind_speed, "風向": wind_dir,
        "記錄時間": datetime.now().strftime("%H:%M:%S"), "備註": notes,
    })

def do_reset(code: str = "DEFAULT"):
    st.session_state.running = False
    st.session_state.start_time = None
    st.session_state.elapsed = 0.0
    st.session_state.lap_start = None
    st.session_state.trigger_count = 0
    write_race({"status": "idle", "start_time": None, "last_elapsed": None}, code)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 設定")

    # ── Room code (must match on both phones) ─────────────────────────────────
    room_code_raw = st.text_input(
        "🔑 房間碼（兩機需一致）",
        value="A",
        max_chars=8,
        help="起點和終點手機輸入相同房間碼，才能互相配對計時。",
    )
    room_code = "".join(c for c in room_code_raw.upper().strip() if c.isalnum()) or "A"
    st.markdown("---")

    car_name    = st.text_input("風帆車名稱 / 編號", value="風帆車 #1")
    route       = st.text_input("路線名稱",          value="直線賽道")
    distance_km = st.number_input("路線距離 (km)",   min_value=0.0, value=0.1, step=0.01, format="%.3f")
    wind_speed  = st.number_input("風速 (m/s)",      min_value=0.0, value=5.0, step=0.5,  format="%.1f")
    wind_dir    = st.selectbox("風向", ["北", "東北", "東", "東南", "南", "西南", "西", "西北"])
    notes       = st.text_area("備註", placeholder="天氣、場地狀況…")
    st.markdown("---")
    st.subheader("📷 相機偵測設定")
    cam_line_pos    = st.slider("感測線位置 (%)", 10, 90, 50)
    cam_sensitivity = st.slider("靈敏度",          5, 80, 25)
    cam_cooldown    = st.slider("冷卻時間 (秒)",   1, 10,  2)
    st.markdown("---")
    st.info(
        f"兩部手機連接同一 WiFi，開啟同一網址。\n"
        f"目前房間碼：**{room_code}**\n"
        f"兩機輸入相同碼即完成配對。"
    )

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_manual, tab_camera = st.tabs(["⏱ 手動計時", "📷 雙機相機計時"])

# ═════════════════════════════════════════════════════════════════════════════
# Tab 1 - Manual
# ═════════════════════════════════════════════════════════════════════════════
with tab_manual:
    col_timer, col_info = st.columns([2, 1])
    with col_timer:
        st.subheader("⏱ 計時器")
        elapsed_now = current_elapsed()
        st.markdown(
            f"<div style=\'font-size:4rem;font-weight:bold;font-family:monospace;"
            f"color:#1f77b4;text-align:center;padding:20px 0;\'>{fmt(elapsed_now)}</div>",
            unsafe_allow_html=True,
        )
        if st.session_state.lap_start is not None:
            lap_e = elapsed_now - st.session_state.lap_start
            st.markdown(
                f"<div style=\'font-size:1.5rem;color:#888;text-align:center;\'>圈次時間: {fmt(lap_e)}</div>",
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
                do_reset(room_code); st.rerun()
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

# ═════════════════════════════════════════════════════════════════════════════
# Tab 2 - Dual Camera
# ═════════════════════════════════════════════════════════════════════════════
with tab_camera:
    st.subheader(f"📷 雙機相機計時　🔑 {room_code}")

    # ── Race status bar ───────────────────────────────────────────────────────
    race = read_race(room_code)
    status_map = {
        "idle":     ("⏸", "待命中",       "#888"),
        "ready":    ("✅", "起點已就緒",    "#2ecc71"),
        "running":  ("🏃", "計時中",        "#1f77b4"),
        "finished": ("🏁", "比賽完成",      "#e67e22"),
    }
    icon, label, color = status_map.get(race["status"], ("⏸", "待命中", "#888"))
    _le = race.get("last_elapsed")
    last_t = f"　　最後成績：{fmt(_le)}" if _le else ""
    st.markdown(
        f"<div style=\'background:#1e2130;border-radius:8px;padding:8px 16px;"
        f"font-size:1.1rem;font-weight:bold;color:{color};border:1px solid {color};\'>"
        f"{icon} 比賽狀態：{label}{last_t}</div>",
        unsafe_allow_html=True,
    )
    st.markdown("")

    # ── Device role selector ──────────────────────────────────────────────────
    col_role, col_reset = st.columns([3, 1])
    with col_role:
        dev_mode = st.radio(
            "📱 本機角色",
            ["🟢 起點（開始計時）", "🏁 終點（停止計時）"],
            horizontal=True,
            key="dev_mode_radio",
        )
    with col_reset:
        st.write("")
        if st.button("🔄 重置比賽", use_container_width=True, key="race_reset"):
            do_reset(room_code); st.rerun()

    is_start = "起點" in dev_mode
    st.markdown("---")

    # ── Camera component ──────────────────────────────────────────────────────
    col_cam, col_cam_info = st.columns([3, 1])

    with col_cam:
        component_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "camera_component")
        camera_component = components.declare_component("sailing_camera", path=component_dir)
        cam_event = camera_component(
            mode="start" if is_start else "finish",
            line_pos=cam_line_pos,
            sensitivity=cam_sensitivity,
            cooldown=cam_cooldown,
            key="cam",
            default=None,
            height=560,
        )

        if cam_event is not None:
            ev_type = cam_event.get("type")
            race = read_race(room_code)

            if is_start:
                # ── 起點裝置 ──────────────────────────────────────────────────
                if ev_type == "armed":
                    st.session_state.cam_mode = True
                    write_race({"status": "ready", "start_time": None, "last_elapsed": race.get("last_elapsed")}, room_code)
                    st.rerun()
                elif ev_type == "disarmed":
                    st.session_state.cam_mode = False
                elif ev_type in ("motion", "manual_trigger") and st.session_state.cam_mode:
                    if race["status"] in ("ready", "idle", "finished"):
                        start_t = time.time()
                        write_race({"status": "running", "start_time": start_t,
                                    "last_elapsed": race.get("last_elapsed")}, room_code)
                        st.session_state.running = True
                        st.session_state.start_time = start_t
                        st.session_state.elapsed = 0.0
                        st.session_state.lap_start = 0.0
                        st.session_state.trigger_count += 1
                        st.toast("🚀 起點通過！計時開始！", icon="🏃")
                        st.rerun()
                elif ev_type == "manual_trigger" and not st.session_state.cam_mode:
                    start_t = time.time()
                    write_race({"status": "running", "start_time": start_t,
                                "last_elapsed": race.get("last_elapsed")}, room_code)
                    st.session_state.running = True
                    st.session_state.start_time = start_t
                    st.session_state.elapsed = 0.0
                    st.session_state.lap_start = 0.0
                    st.rerun()

            else:
                # ── 終點裝置 ──────────────────────────────────────────────────
                if ev_type == "armed":
                    st.session_state.cam_mode = True
                elif ev_type == "disarmed":
                    st.session_state.cam_mode = False
                elif ev_type in ("motion", "manual_trigger") and st.session_state.cam_mode:
                    if race["status"] == "running" and race["start_time"]:
                        elapsed = time.time() - race["start_time"]
                        do_lap_direct(elapsed, car_name, route, distance_km, wind_speed, wind_dir, notes)
                        write_race({"status": "finished", "start_time": race["start_time"],
                                    "last_elapsed": elapsed}, room_code)
                        st.session_state.trigger_count += 1
                        st.toast(f"🏁 終點通過！成績: {fmt(elapsed)}", icon="🎉")
                        st.rerun()
                    else:
                        st.warning("尚未偵測到起點觸發，請確認起點手機已就緒。")
                elif ev_type == "manual_trigger" and not st.session_state.cam_mode:
                    if race["status"] == "running" and race["start_time"]:
                        elapsed = time.time() - race["start_time"]
                        do_lap_direct(elapsed, car_name, route, distance_km, wind_speed, wind_dir, notes)
                        write_race({"status": "finished", "start_time": race["start_time"],
                                    "last_elapsed": elapsed}, room_code)
                        st.rerun()

    # ── Info panel ────────────────────────────────────────────────────────────
    with col_cam_info:
        race = read_race(room_code)
        st.subheader("📊 計時狀態")

        if is_start:
            st.success("🟢 起點裝置")
            if st.session_state.running:
                en = current_elapsed()
                st.metric("計時中", fmt(en))
                st.metric("觸發次數", st.session_state.trigger_count)
                display_t = fmt(en)
            else:
                st.metric("狀態", "⏸ 待命")
                display_t = "00:00.00"
        else:
            st.warning("🏁 終點裝置")
            if race["status"] == "running" and race["start_time"]:
                live = time.time() - race["start_time"]
                st.metric("計時中", fmt(live))
                display_t = fmt(live)
            elif race["status"] == "finished" and race.get("last_elapsed"):
                st.metric("成績", fmt(race["last_elapsed"]))
                st.metric("觸發次數", st.session_state.trigger_count)
                display_t = fmt(race["last_elapsed"])
            elif race["status"] == "ready":
                st.metric("狀態", "✅ 等待起點…")
                display_t = "00:00.00"
            else:
                st.metric("狀態", "⏸ 待命")
                display_t = "00:00.00"

        st.markdown("---")
        st.markdown(
            f"<div style=\'font-size:2.5rem;font-weight:bold;font-family:monospace;"
            f"color:#1f77b4;text-align:center;\'>{display_t}</div>",
            unsafe_allow_html=True,
        )

        st.markdown("---")
        if is_start:
            st.caption("**起點操作：**\n1. 按「啟用偵測」\n2. 風帆車通過起點 → 自動計時")
        else:
            st.caption("**終點操作：**\n1. 確認起點手機已就緒\n2. 按「啟用偵測」\n3. 風帆車通過終點 → 記錄成績")

        if is_start and st.session_state.running:
            time.sleep(0.1); st.rerun()
        if not is_start and st.session_state.cam_mode and race["status"] == "running":
            time.sleep(0.2); st.rerun()

    st.markdown('''
---
**使用說明（兩部手機）：**
| 步驟 | 起點手機 | 終點手機 |
|------|----------|----------|
| 1 | 連到同一 WiFi，開啟同一網址 | 連到同一 WiFi，開啟同一網址 |
| 2 | 左側欄輸入相同**房間碼** | 左側欄輸入相同**房間碼** |
| 3 | 選「🟢 起點」 | 選「🏁 終點」 |
| 4 | 對準起點線，按「啟用偵測」 | 對準終點線，按「啟用偵測」 |
| 5 | 風帆車通過 → **自動開始計時** | 等待… |
| 6 | 顯示計時中 | 風帆車通過 → **自動記錄成績** |
    ''')

# ── Shared lap records ────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📋 成績記錄")

if st.session_state.laps:
    df = pd.DataFrame(st.session_state.laps)
    st.dataframe(df, use_container_width=True, hide_index=True)

    col_dl, col_clear = st.columns([1, 5])
    with col_dl:
        csv = df.to_csv(index=False, encoding="utf-8-sig")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            "⬇ 下載 CSV", data=csv,
            file_name=f"sailing_{ts}.csv",
            mime="text/csv",
        )
    with col_clear:
        if st.button("🗑 清除記錄"):
            st.session_state.laps = []; st.rerun()

    if len(st.session_state.laps) >= 2:
        st.subheader("📈 成績趨勢")
        sec_list = []
        for lap in st.session_state.laps:
            t = lap["行駛時間"]; p = t.split(":")
            if len(p) == 2:   sec_list.append(int(p[0])*60 + float(p[1]))
            elif len(p) == 3: sec_list.append(int(p[0])*3600 + int(p[1])*60 + float(p[2]))
        chart_df = pd.DataFrame({
            "次數": [l["圈次"] for l in st.session_state.laps],
            "行駛時間 (秒)": sec_list,
            "平均速度 (km/h)": [l["平均速度 (km/h)"] for l in st.session_state.laps],
        }).set_index("次數")
        t1, t2 = st.tabs(["行駛時間", "平均速度"])
        with t1: st.line_chart(chart_df[["行駛時間 (秒)"]])
        with t2: st.line_chart(chart_df[["平均速度 (km/h)"]])
else:
    st.info("尚無成績記錄。")

st.markdown("---")
st.caption("風帆車計時系統 © 2026 — 以 Streamlit 製作")
