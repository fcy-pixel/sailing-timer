import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime
import time
import os

st.set_page_config(page_title="風帆車計時系統", page_icon="⛵", layout="centered")

# ── Shared race state ─────────────────────────────────────────────────────────
@st.cache_resource
def _race_store() -> dict:
    return {}

def read_race(code: str = "A") -> dict:
    return _race_store().get(
        code, {"status": "idle", "start_time": None, "last_elapsed": None}
    )

def write_race(data: dict, code: str = "A"):
    _race_store()[code] = data

@st.cache_resource
def _conn_store() -> dict:
    return {}  # {room: {"start": timestamp, "finish": timestamp}}

def update_presence(room_code: str, role: str):
    s = _conn_store()
    if room_code not in s:
        s[room_code] = {}
    s[room_code][role] = time.time()

def get_pairing(room_code: str):
    """Return (start_online, finish_online) based on last-seen timestamps."""
    conn = _conn_store().get(room_code, {})
    now = time.time()
    timeout = 15  # seconds without heartbeat → considered offline
    return (now - conn.get("start", 0)) < timeout, (now - conn.get("finish", 0)) < timeout

def _init(key, val):
    if key not in st.session_state:
        st.session_state[key] = val

_init("laps", [])
_init("trigger_count", 0)
_init("last_dev_mode", None)
_init("cam_mode", False)

def fmt(seconds: float) -> str:
    s = int(seconds)
    ms = int((seconds - s) * 100)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h:02d}:{m:02d}:{sec:02d}.{ms:02d}"
    return f"{m:02d}:{sec:02d}.{ms:02d}"

def _save_lap(elapsed, car_name, route, distance_km):
    lap_num = len(st.session_state.laps) + 1
    avg_speed = (distance_km / (elapsed / 3600)) if elapsed > 0 else 0
    st.session_state.laps.append({
        "次數": lap_num,
        "車輛": car_name,
        "路線": route,
        "時間": fmt(elapsed),
        "距離 (km)": distance_km,
        "均速 (km/h)": round(avg_speed, 2),
        "記錄時間": datetime.now().strftime("%H:%M:%S"),
    })

def do_reset(code):
    st.session_state.trigger_count = 0
    st.session_state.cam_mode = False
    write_race({"status": "idle", "start_time": None, "last_elapsed": None}, code)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 設定")
    room_code_raw = st.text_input("🔑 房間碼（兩機須一致）", value="A", max_chars=8)
    room_code = "".join(c for c in room_code_raw.upper().strip() if c.isalnum()) or "A"
    st.markdown("---")
    car_name    = st.text_input("車輛名稱", value="風帆車 #1")
    route       = st.text_input("路線名稱", value="直線賽道")
    distance_km = st.number_input("距離 (km)", min_value=0.0, value=0.1, step=0.01, format="%.3f")
    st.markdown("---")
    st.subheader("📷 偵測設定")
    cam_line_pos    = st.slider("感測線位置 ↔ (%)", 10, 90, 50)
    cam_sensitivity = st.slider("靈敏度", 5, 80, 25)
    cam_cooldown    = st.slider("冷卻時間 (秒)", 1, 10, 2)
    st.markdown("---")
    st.caption(f"房間碼：**{room_code}**　兩機輸入相同碼即配對")

# ── Main page ─────────────────────────────────────────────────────────────────
# ── Role selector ─────────────────────────────────────────────────────────────
race = read_race(room_code)
st.markdown(
    "<h1 style='text-align:center;font-size:2rem;margin-bottom:0;'>⛵ 風帆車計時系統</h1>"
    "<div style='text-align:center;color:#f39c12;font-size:1.1rem;font-weight:bold;"
    "letter-spacing:2px;margin-bottom:12px;'>Empowered by Fung Sir</div>",
    unsafe_allow_html=True,
)
status_map = {
    "idle":     ("⏸", "待命中",    "#888"),
    "ready":    ("✅", "起點就緒",  "#2ecc71"),
    "running":  ("🏃", "計時中",    "#1f77b4"),
    "finished": ("🏁", "完成",      "#e67e22"),
}
icon, label, color = status_map.get(race["status"], ("⏸", "待命中", "#888"))
_le = race.get("last_elapsed")
last_t = f"　成績：**{fmt(_le)}**" if _le else ""
st.markdown(
    f"<div style=\'background:#1e2130;border-radius:10px;padding:10px 18px;"
    f"font-size:1.2rem;font-weight:bold;color:{color};border:2px solid {color};\'>"
    f"{icon} {label}{last_t}</div>",
    unsafe_allow_html=True,
)
st.write("")

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
    if st.button("🔄 重置", use_container_width=True, key="race_reset"):
        do_reset(room_code); st.rerun()

is_start = "起點" in dev_mode

if st.session_state.last_dev_mode != dev_mode:
    st.session_state.cam_mode = False
    st.session_state.last_dev_mode = dev_mode

# Update this device's presence and show pairing status
update_presence(room_code, "start" if is_start else "finish")
start_on, finish_on = get_pairing(room_code)

if start_on and finish_on:
    pair_bg, pair_border, pair_icon, pair_text = "#0d2b0d", "#2ecc71", "✅", "兩機配對成功"
elif start_on or finish_on:
    pair_bg, pair_border, pair_icon, pair_text = "#2b1d00", "#f39c12", "⏳", "等待另一部手機加入…"
else:
    pair_bg, pair_border, pair_icon, pair_text = "#1e1e1e", "#888", "📵", "未配對"

role_tag = "🟢 起點" if start_on else "<span style='color:#555'>🟢 起點</span>"
finish_tag = "🏁 終點" if finish_on else "<span style='color:#555'>🏁 終點</span>"
st.markdown(
    f"<div style='background:{pair_bg};border:2px solid {pair_border};border-radius:10px;"
    f"padding:8px 16px;font-size:1rem;color:{pair_border};font-weight:bold;'"
    f">{pair_icon} {pair_text}"
    f"<span style='float:right;font-size:0.85rem;font-weight:normal;color:#aaa;'>"
    f"房間 {room_code}：{role_tag} &nbsp;|&nbsp; {finish_tag}</span></div>",
    unsafe_allow_html=True,
)
st.write("")

st.markdown("---")

# ── Status display ────────────────────────────────────────────────────────────
race = read_race(room_code)
if is_start:
    if race["status"] == "running" and race["start_time"]:
        elapsed_live = time.time() - race["start_time"]
        st.markdown(
            f"<div style=\'text-align:center;font-size:4rem;font-weight:bold;"
            f"font-family:monospace;color:#1f77b4;\'>{fmt(elapsed_live)}</div>",
            unsafe_allow_html=True,
        )
    elif race["status"] == "finished" and race.get("last_elapsed"):
        _fle = race["last_elapsed"]
        st.markdown(
            f"<div style=\'text-align:center;font-size:4rem;font-weight:bold;"
            f"font-family:monospace;color:#e67e22;\'>{fmt(_fle)}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style=\'text-align:center;font-size:2rem;color:#888;\'>📷 相機偵測起點中…</div>",
            unsafe_allow_html=True,
        )
else:
    if race["status"] == "running" and race["start_time"]:
        elapsed_live = time.time() - race["start_time"]
        st.markdown(
            f"<div style=\'text-align:center;font-size:4rem;font-weight:bold;"
            f"font-family:monospace;color:#1f77b4;\'>{fmt(elapsed_live)}</div>",
            unsafe_allow_html=True,
        )
    elif race["status"] == "finished" and race.get("last_elapsed"):
        _fle = race["last_elapsed"]
        st.markdown(
            f"<div style=\'text-align:center;font-size:4rem;font-weight:bold;"
            f"font-family:monospace;color:#e67e22;\'>{fmt(_fle)}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style=\'text-align:center;font-size:2rem;color:#888;\'>⏳ 等待起點手機觸發…</div>",
            unsafe_allow_html=True,
        )

st.write("")

# ── Camera component ──────────────────────────────────────────────────────────
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
        if ev_type == "armed":
            st.session_state.cam_mode = True
            write_race({"status": "ready", "start_time": None,
                        "last_elapsed": race.get("last_elapsed")}, room_code)
            st.rerun()
        elif ev_type == "disarmed":
            st.session_state.cam_mode = False
            write_race({"status": "idle", "start_time": None,
                        "last_elapsed": race.get("last_elapsed")}, room_code)
        elif ev_type == "motion" and st.session_state.cam_mode:
            if race["status"] in ("ready", "idle", "finished"):
                start_t = time.time()
                write_race({"status": "running", "start_time": start_t,
                            "last_elapsed": race.get("last_elapsed")}, room_code)
                st.session_state.trigger_count += 1
                st.session_state.cam_mode = False  # auto-disarm
                st.toast("🚀 起點通過！計時開始！", icon="🏃")
                st.rerun()
    else:
        if ev_type == "armed":
            st.session_state.cam_mode = True
        elif ev_type == "disarmed":
            st.session_state.cam_mode = False
        elif ev_type == "motion":  # trust JS armed state — no cam_mode guard needed
            # Accept motion if running, OR if start_time exists but status update lagged
            if race["start_time"] and race["status"] in ("running", "ready"):
                elapsed = time.time() - race["start_time"]
                elapsed = time.time() - race["start_time"]
                _save_lap(elapsed, car_name, route, distance_km)
                write_race({"status": "finished", "start_time": race["start_time"],
                            "last_elapsed": elapsed}, room_code)
                st.session_state.trigger_count += 1
                st.session_state.cam_mode = False  # auto-disarm
                st.toast(f"🏁 終點！成績: {fmt(elapsed)}", icon="🎉")
                st.rerun()

# Auto-refresh while timing; slow refresh to keep pairing status live when idle
race = read_race(room_code)
if race["status"] == "running":
    time.sleep(0.15); st.rerun()
elif not (start_on and finish_on):
    time.sleep(2); st.rerun()

# ── Results table ─────────────────────────────────────────────────────────────
if st.session_state.laps:
    st.markdown("---")
    st.subheader("📋 成績記錄")
    df = pd.DataFrame(st.session_state.laps)
    st.dataframe(df, use_container_width=True, hide_index=True)
    col_dl, col_clear = st.columns([1, 4])
    with col_dl:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button("⬇ 下載 CSV",
            data=df.to_csv(index=False, encoding="utf-8-sig"),
            file_name=f"sailing_{ts}.csv", mime="text/csv")
    with col_clear:
        if st.button("🗑 清除記錄"):
            st.session_state.laps = []; st.rerun()
