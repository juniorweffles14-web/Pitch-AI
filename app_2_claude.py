import streamlit as st
from groq import Groq
import json
import os
import base64
import html
from PIL import Image
from datetime import datetime, date
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
import plotly.graph_objects as go
import bcrypt
import smtplib
import secrets
import time
import cv2
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

APP_DIR = os.path.dirname(os.path.abspath(__file__))


def _find_asset(*names):
    for n in names:
        p = os.path.join(APP_DIR, n)
        if os.path.exists(p):
            return p
    return None


# Favicon: your "Untitled design" logo (favicon.png is a transparent, cropped copy of it).
_fav_path = _find_asset("favicon.png", "Untitled_design.jpg", "Untitled design.jpg", "Untitled_design.png", "Untitled design.png")
try:
    PAGE_ICON = Image.open(_fav_path) if _fav_path else "⚽"
except Exception:
    PAGE_ICON = "⚽"

st.set_page_config(page_title="Pitch AI", page_icon=PAGE_ICON, layout="centered")

# ══════════════════════════════════════════════════════════════════════════
# THEME — injected first so the login/signup page is styled too
# ══════════════════════════════════════════════════════════════════════════
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@600;700;800&family=Inter:wght@400;500;600;700&display=swap');
:root{
  --bg:#0a0e17; --card:#111a2b; --card-border:rgba(0,217,255,0.14);
  --cyan:#22d3ee; --blue:#3b82f6; --text:#f2f5fa; --muted:#8b98ad;
  --green:#22c55e; --amber:#f5a623; --red:#ef4444; --purple:#a855f7;
}
html, body, [class*="css"]{ font-family:'Inter', sans-serif; }
h1,h2,h3,h4{ font-family:'Sora', sans-serif; }
.stApp{ background: radial-gradient(circle at 20% 0%, #0f1830 0%, var(--bg) 55%) fixed; color: var(--text); }
#MainMenu, footer{visibility:hidden;}
div[data-testid="stDecoration"]{display:none;}

.pitch-header{ display:flex; align-items:center; justify-content:space-between; padding:.25rem 0 1rem 0;
  border-bottom:1px solid var(--card-border); margin-bottom:1.2rem;}
.pitch-logo{ font-family:'Sora',sans-serif; font-weight:800; font-size:1.5rem;}
.pitch-logo span{ color:var(--cyan); }
.page-title{ font-family:'Sora',sans-serif; font-weight:800; font-size:1.9rem; margin:0 0 .1rem 0;}
.page-sub{ color:var(--muted); margin-bottom:1.1rem; font-size:.93rem;}

div[data-testid="stVerticalBlockBorderWrapper"]{
  background:var(--card) !important; border:1px solid var(--card-border) !important; border-radius:16px !important;
}
div[data-testid="stExpander"]{ background:var(--card); border:1px solid var(--card-border) !important; border-radius:14px !important; }
div[data-testid="stChatMessage"]{ background:var(--card); border:1px solid var(--card-border); border-radius:14px; }

.chip-grid{ display:flex; gap:.6rem; flex-wrap:wrap; margin-bottom:.6rem;}
.chip{ flex:1; min-width:130px; background:var(--card); border:1px solid var(--card-border); border-radius:14px; padding:.85rem 1rem;}
.chip .label{ color:var(--muted); font-size:.68rem; text-transform:uppercase; letter-spacing:.5px;}
.chip .value{ font-family:'Sora',sans-serif; font-weight:800; font-size:1.55rem; margin-top:.15rem;}
.bar-track{ background:#1c2740; border-radius:6px; height:7px; margin-top:.5rem; overflow:hidden;}
.bar-fill{ height:100%; border-radius:6px; }

.badge{ display:inline-block; padding:.18rem .6rem; border-radius:999px; font-size:.72rem; font-weight:600;}
.badge-green{ background:rgba(34,197,94,.15); color:var(--green);}
.badge-amber{ background:rgba(245,166,35,.15); color:var(--amber);}
.badge-red{ background:rgba(239,68,68,.15); color:var(--red);}
.badge-cyan{ background:rgba(34,211,238,.15); color:var(--cyan);}
.badge-purple{ background:rgba(168,85,247,.15); color:var(--purple);}

.quote-box{ border-left:3px solid var(--cyan); background:rgba(34,211,238,.06); padding:.9rem 1rem; border-radius:8px; font-style:italic;}
.stat-row{ display:flex; justify-content:space-between; padding:.35rem 0; border-bottom:1px solid var(--card-border); font-size:.92rem;}
.stat-row:last-child{ border-bottom:none; }

div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea,
div[data-testid="stNumberInput"] input, div[data-baseweb="select"] > div{
  background:#0d1420 !important; border:1px solid var(--card-border) !important; color:var(--text) !important; border-radius:10px !important;
}
div[data-testid="stButton"] button{
  background:linear-gradient(135deg,var(--cyan),var(--blue)); color:#04101c; font-weight:700; border:none; border-radius:10px;
}
div[data-testid="stButton"] button:hover{ filter:brightness(1.08); color:#04101c;}
div[data-testid="stFileUploader"]{ background:var(--card); border:1px dashed var(--card-border); border-radius:14px; padding:.5rem;}
div[data-testid="stBottom"]{ background:#0d1420 !important; border-top:1px solid var(--card-border); }

/* ── login / signup page ─────────────────────────────────────────── */
.auth-logo{ text-align:center; font-family:'Sora',sans-serif; font-weight:800; font-size:2.1rem; margin-top:1.5rem;}
.auth-logo span{ color:var(--cyan); }
.auth-sub{ text-align:center; color:var(--muted); margin-bottom:1.6rem; font-size:.95rem;}
div[data-baseweb="tab-list"]{
  background:var(--card); border:1px solid var(--card-border); border-radius:12px; padding:.3rem; gap:.3rem;
}
button[data-baseweb="tab"]{ color:var(--muted); font-weight:600; border-radius:8px; }
button[data-baseweb="tab"][aria-selected="true"]{
  background:linear-gradient(135deg,var(--cyan),var(--blue)); color:#04101c !important;
}
div[data-baseweb="tab-highlight"]{ display:none; }
div[data-baseweb="tab-border"]{ display:none; }
/* ── home screen (no matches analyzed yet) ───────────────────────── */
.hero-marker{ display:none; }
div[data-testid="stVerticalBlockBorderWrapper"]:has(.hero-marker){
  position:relative; overflow:hidden;
  border:1px solid rgba(34,211,238,.55) !important;
  background:linear-gradient(120deg,#0a1220 0%,#0a0e17 100%) !important;
  box-shadow:0 0 28px rgba(34,211,238,.16), inset 0 0 40px rgba(34,211,238,.05);
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.hero-marker) div[data-testid="stElementContainer"]:not(:has(.hero-marker)),
div[data-testid="stVerticalBlockBorderWrapper"]:has(.hero-marker) div[data-testid="element-container"]:not(:has(.hero-marker)){
  position:relative; z-index:1;
}
.hero-art{ position:absolute; top:0; right:0; bottom:0; width:62%; z-index:0; pointer-events:none;
  background-size:cover; background-position:center 30%; opacity:.95;
  -webkit-mask-image:linear-gradient(to right,transparent 0%,#000 55%); mask-image:linear-gradient(to right,transparent 0%,#000 55%); }
.hero-checks{ position:absolute; right:16px; bottom:14px; z-index:2; font-size:.62rem; letter-spacing:.4px; line-height:1.9; color:#dfe8f5; }
.hero-checks span{ color:var(--cyan); margin-right:.4rem; }
.hero-icon{ width:46px; height:46px; border:1px solid rgba(34,211,238,.6); border-radius:12px; display:flex; align-items:center; justify-content:center;
  font-size:1.3rem; background:rgba(34,211,238,.08); margin-bottom:.8rem; }
.hero-title{ font-family:'Sora',sans-serif; font-weight:800; font-size:2rem; line-height:1.05; letter-spacing:.5px; }
.hero-sub{ color:#cfd8e6; margin:.6rem 0 .4rem; font-size:.95rem; max-width:230px; }
@media (max-width:640px){ .hero-art{ width:100%; opacity:.3; } .hero-checks{ display:none; } }

.stat-grid{ display:grid; grid-template-columns:repeat(4,1fr); gap:.6rem; margin:.9rem 0; }
@media (max-width:640px){ .stat-grid{ grid-template-columns:repeat(2,1fr); } }
.sc{ background:var(--card); border:1px solid var(--card-border); border-radius:14px; padding:.8rem .85rem; min-height:132px; }
.sc-h{ display:flex; justify-content:space-between; color:#cfd8e6; font-size:.62rem; text-transform:uppercase; letter-spacing:.4px; }
.sc-h i{ font-style:normal; color:var(--cyan); font-size:.9rem; }
.sc-big{ font-family:'Sora',sans-serif; font-weight:800; font-size:1.6rem; margin-top:.35rem; line-height:1.1; }
.sc-big small{ font-size:.85rem; color:var(--muted); font-weight:600; margin-left:.15rem; }
.sc-name{ font-family:'Sora',sans-serif; font-weight:800; font-size:1rem; line-height:1.2; margin-top:.35rem; }
.sc-note{ color:var(--muted); font-size:.72rem; margin-top:.35rem; }
.gauge{ position:relative; height:6px; border-radius:4px; margin-top:.7rem; background:linear-gradient(90deg,#ef4444,#f59e0b,#eab308,#84cc16,#22c55e); }
.gauge b{ position:absolute; top:50%; left:50%; width:9px; height:9px; border-radius:50%; background:#fff; transform:translate(-50%,-50%); }
.gauge-scale{ display:flex; justify-content:space-between; color:var(--muted); font-size:.6rem; margin-top:.3rem; }
.ring{ width:54px; height:54px; border:3px solid var(--cyan); border-radius:50%; display:flex; align-items:center; justify-content:center;
  font-family:'Sora',sans-serif; font-weight:800; font-size:.85rem; margin:.5rem 0 0 auto; box-shadow:0 0 12px rgba(34,211,238,.35); }

.sec-h{ font-family:'Sora',sans-serif; font-weight:700; font-size:.82rem; letter-spacing:.6px; text-transform:uppercase; margin-bottom:.7rem; }
.sec-sub{ color:var(--muted); font-size:.75rem; margin:-.5rem 0 .7rem 0; }
.thumb{ position:relative; height:120px; border-radius:10px; overflow:hidden;
  background:linear-gradient(180deg,rgba(6,12,22,.15),rgba(6,12,22,.7)), repeating-linear-gradient(90deg,#14532d 0 34px,#166534 34px 68px); }
.thumb .play{ position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); width:42px; height:42px; border-radius:50%;
  background:rgba(10,14,23,.75); border:2px solid #fff; display:flex; align-items:center; justify-content:center; color:#fff; font-size:.9rem; }
.thumb .dur{ position:absolute; left:8px; bottom:6px; font-size:.68rem; background:rgba(0,0,0,.65); padding:.05rem .4rem; border-radius:4px; }
.match-row{ display:flex; justify-content:space-between; align-items:flex-end; gap:.6rem; margin:.7rem 0 .5rem; }
.match-name{ font-weight:700; font-size:.95rem; }
.muted{ color:var(--muted); font-size:.72rem; }
.perf-box{ border:1px solid var(--card-border); border-radius:10px; padding:.35rem .6rem; text-align:center; min-width:88px; }
.perf-box b{ font-family:'Sora',sans-serif; font-size:1.15rem; }
.perf-box small{ color:var(--muted); font-size:.58rem; display:block; letter-spacing:.4px; }
.find-h{ color:var(--cyan); font-size:.66rem; letter-spacing:.6px; font-weight:600; margin-top:.3rem; }
.find{ display:flex; gap:.5rem; align-items:center; font-size:.8rem; margin:.3rem 0; color:#dbe3ef; }
.dot{ width:14px; height:14px; border-radius:50%; border:1.5px solid; display:inline-flex; align-items:center; justify-content:center; font-size:.55rem; flex:none; }
.dot.g{ color:var(--green); } .dot.a{ color:var(--amber); } .dot.r{ color:var(--red); }
.legend{ display:flex; justify-content:space-between; font-size:.62rem; color:var(--muted); border-top:1px solid var(--card-border); padding-top:.5rem; }
.legend i{ display:inline-block; width:14px; height:3px; border-radius:2px; margin-right:.35rem; vertical-align:middle; }
.tr-row{ display:flex; align-items:center; gap:.6rem; padding:.55rem .6rem; border:1px solid var(--card-border); border-radius:10px; margin-bottom:.45rem; background:#0d1526; }
.tr-ico{ width:30px; height:30px; border-radius:8px; border:1px solid rgba(34,211,238,.4); display:flex; align-items:center; justify-content:center; flex:none; }
.tr-name{ flex:1; font-size:.82rem; font-weight:600; }
.tr-min{ color:var(--muted); font-size:.7rem; }
.imp-head, .imp-row{ display:grid; grid-template-columns:1.5fr 34px 1fr 34px 48px; gap:.4rem; align-items:center; font-size:.72rem; }
.imp-head{ color:var(--muted); font-size:.58rem; letter-spacing:.4px; margin-bottom:.4rem; }
.imp-row{ padding:.45rem 0; border-bottom:1px solid var(--card-border); }
.imp-row:last-child{ border-bottom:none; }
.imp-bar{ height:5px; border-radius:3px; background:#1c2740; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# PASSWORD RESET — emailed verification code
# ══════════════════════════════════════════════════════════════════════════
RESET_CODE_TTL_SECONDS = 600  # 10 minutes


# ─── Email Config ───
SENDER_EMAIL = "pitch.ai.coach@gmail.com"  # Change this
SENDER_PASSWORD = "pnus wwvq vvbx ywko"  # Change this

def send_reset_code(receiver_email, code):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Your Pitch AI reset code"  # Change to Soccer AI Coach for boy
        msg["From"] = SENDER_EMAIL
        msg["To"] = receiver_email

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #FFF8F9; padding: 30px;">
            <div style="max-width: 480px; margin: auto; background: white; border-radius: 16px; padding: 32px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
                <h2 style="color: #D6336C;">Pitch Ai </h2>
                <p style="color: #333;">Hi there! You requested a password reset.</p>
                <p style="color: #333;">Your reset code is:</p>
                <div style="text-align: center; margin: 24px 0;">
                    <span style="font-size: 2.5rem; font-weight: 800; letter-spacing: 8px; color: #D6336C;">
                        {code}
                    </span>
                </div>
                <p style="color: #888; font-size: 0.85rem;">This code expires in 10 minutes. If you did not request this, ignore this email.</p>
                <hr style="border: none; border-top: 1px solid #F0E0E4; margin: 24px 0;">
                <p style="color: #bbb; font-size: 0.75rem;">Fitz — Your Personal AI Stylist</p>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, receiver_email, msg.as_string())

        return True

    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False


def _clear_reset_state():
    for k in ("reset_stage", "reset_username", "reset_email", "reset_code", "reset_code_expires"):
        st.session_state.pop(k, None)


# ══════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════
if not os.path.exists("config.yaml"):
    st.error(
        "`config.yaml` not found. Create one for streamlit-authenticator, e.g.:\n\n"
        "```yaml\ncredentials:\n  usernames: {}\ncookie:\n  name: pitch_ai_cookie\n"
        "  key: change_this_random_string\n  expiry_days: 30\n```"
    )
    st.stop()

with open("config.yaml", "r") as f:
    config = yaml.load(f, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config["credentials"], config["cookie"]["name"], config["cookie"]["key"], config["cookie"]["expiry_days"]
)

if st.session_state.get("authentication_status") is not True:
    st.markdown('<div class="auth-logo">⚽ PITCH <span>AI</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-sub">Your personal AI football coach. Login or create an account to continue.</div>', unsafe_allow_html=True)

    with st.container(border=True):
        tab1, tab2, tab3 = st.tabs(["Login", "Sign Up", "Reset Password"])
        with tab1:
            try:
                authenticator.login()
            except Exception as e:
                st.error(e)
            if st.session_state.get("authentication_status") is False:
                st.error("Username or password is incorrect.")
            elif st.session_state.get("authentication_status") is None:
                st.caption("Enter your credentials to continue.")
        with tab2:
            try:
                result = authenticator.register_user()
                if result:
                    email, username, name = result
                    if email:
                        st.success("Account created! Head to the Login tab to sign in.")
                        with open("config.yaml", "w") as f:
                            yaml.dump(config, f, default_flow_style=False)
            except Exception as e:
                st.error(e)
        with tab3:
            st.subheader("🔐 Reset Password")

            st.write("Enter your username and we'll send a reset code to your registered email.")

            reset_username = st.text_input("Username", key="reset_username")

            if st.button("Send Reset Code 📧", key="send_code_btn"):
                if not reset_username:
                    st.error("Please enter your username.")
                elif reset_username not in config["credentials"]["usernames"]:
                    st.error("Username not found.")
                else:
                    user_data = config["credentials"]["usernames"][reset_username]
                    user_email = user_data.get("email", "")

                    if not user_email:
                        st.error("No email found for this account. Please contact support.")
                    else:
                        code = str(random.randint(100000, 999999))
                        st.session_state.reset_code = code
                        st.session_state.reset_code_username = reset_username
                        st.session_state.reset_code_expiry = datetime.now().timestamp() + 600  # 10 mins

                        if send_reset_code(user_email, code):
                            masked_email = user_email[:3] + "***@" + user_email.split("@")[1]
                            st.success(f"Reset code sent to {masked_email}!")
                            st.session_state.reset_code_sent = True

            if st.session_state.get("reset_code_sent"):

                st.divider()

                entered_code = st.text_input("Enter the 6 digit code from your email", key="entered_code")
                new_password = st.text_input("New Password", type="password", key="new_password")
                confirm_password = st.text_input("Confirm New Password", type="password", key="confirm_password")

                if st.button("Reset Password ✅", key="reset_final_btn"):
                    if not entered_code or not new_password or not confirm_password:
                        st.error("Please fill in all fields.")

                    elif datetime.now().timestamp() > st.session_state.get("reset_code_expiry", 0):
                        st.error("Reset code has expired. Please request a new one.")
                        st.session_state.reset_code_sent = False

                    elif entered_code != st.session_state.get("reset_code"):
                        st.error("Incorrect code. Please try again.")

                    elif new_password != confirm_password:
                        st.error("Passwords do not match.")

                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 characters.")

                    else:
                        import bcrypt
                        hashed = bcrypt.hashpw(
                            new_password.encode(),
                            bcrypt.gensalt()
                        ).decode()

                        config["credentials"]["usernames"][
                            st.session_state.reset_code_username
                        ]["password"] = hashed

                        with open("config.yaml", "w") as f:
                            yaml.dump(config, f, default_flow_style=False)

                        st.success("✅ Password reset successfully! Please login with your new password.")

                        # Clear session state
                        st.session_state.reset_code_sent = False
                        st.session_state.reset_code = None
                        st.session_state.reset_code_username = None
                        st.session_state.reset_code_expiry = None
    st.stop()

CURRENT_USER = st.session_state.get("username", "player")

# ══════════════════════════════════════════════════════════════════════════
# API CLIENT — key loaded from secrets/env, never hardcoded
# ══════════════════════════════════════════════════════════════════════════
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
if not GROQ_API_KEY:
    st.error(
        "No Groq API key found. Add `GROQ_API_KEY = \"your-key\"` to "
        "`.streamlit/secrets.toml`, or set it as an environment variable."
    )
    st.stop()
client = Groq(api_key=GROQ_API_KEY)
MODEL = "openai/gpt-oss-120b"
VISION_MODEL = "qwen/qwen3.8-27b"  # multimodal — used when match frames are attached

# ══════════════════════════════════════════════════════════════════════════
# STORAGE — per-user JSON files + uploaded video files on disk
# ══════════════════════════════════════════════════════════════════════════
DATA_DIR = "pitch_ai_data"
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads", CURRENT_USER)
os.makedirs(UPLOAD_DIR, exist_ok=True)

SESSIONS_FILE = os.path.join(DATA_DIR, f"sessions_{CURRENT_USER}.json")
PROFILE_FILE = os.path.join(DATA_DIR, f"profile_{CURRENT_USER}.json")
TRAINING_LOG_FILE = os.path.join(DATA_DIR, f"training_log_{CURRENT_USER}.json")


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_sessions():
    return load_json(SESSIONS_FILE, [])


def save_session(session):
    sessions = load_sessions()
    sessions.append(session)
    save_json(SESSIONS_FILE, sessions)


def load_profile():
    return load_json(PROFILE_FILE, {"name": "", "position": "Midfielder", "jersey_number": 10, "completed_drills": []})


def save_profile(p):
    save_json(PROFILE_FILE, p)


def load_training_log():
    return load_json(TRAINING_LOG_FILE, [])


def log_training_complete():
    log = load_training_log()
    log.append({"date": datetime.now().strftime("%d %b %Y, %H:%M")})
    save_json(TRAINING_LOG_FILE, log)


with open("drills.json", "r") as f:
    drills = json.load(f)["drills"]

RADAR_ORDER = ["passing", "shooting", "dribbling", "fitness", "ball_control", "defending", "vision", "off_ball_movement"]
RADAR_LABELS = {
    "passing": "Passing", "shooting": "Shooting", "dribbling": "Dribbling", "fitness": "Fitness",
    "ball_control": "Ball Control", "defending": "Defending", "vision": "Vision",
    "off_ball_movement": "Off-Ball Movement",
}

def header():
    c1, c2 = st.columns([5, 1])
    with c1:
        st.markdown('<div class="pitch-logo">⚽ PITCH <span>AI</span></div>', unsafe_allow_html=True)
    with c2:
        if st.button("👤", key="avatar_btn", help="Profile"):
            goto("Profile")


def page_title(title, subtitle):
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-sub">{subtitle}</div>', unsafe_allow_html=True)


def score_color(v, max_v=100):
    pct = v / max_v
    if pct >= 0.7:
        return "var(--green)"
    if pct >= 0.4:
        return "var(--amber)"
    return "var(--red)"


def chip(label, value, color="var(--cyan)", bar_pct=None):
    bar = f'<div class="bar-track"><div class="bar-fill" style="width:{bar_pct}%;background:{color}"></div></div>' if bar_pct is not None else ""
    return f'<div class="chip"><div class="label">{label}</div><div class="value" style="color:{color}">{value}</div>{bar}</div>'


def radar_chart(radar, title="Performance Overview", height=380):
    cats = [RADAR_LABELS[k] for k in RADAR_ORDER] + [RADAR_LABELS[RADAR_ORDER[0]]]
    vals = [radar.get(k, 0) for k in RADAR_ORDER] + [radar.get(RADAR_ORDER[0], 0)]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals, theta=cats, fill="toself", name=title,
        line=dict(color="#22d3ee", width=2), fillcolor="rgba(34,211,238,0.25)",
        marker=dict(color="#22d3ee", size=6),
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="#1c2740", tickfont=dict(color="#8b98ad", size=9)),
            angularaxis=dict(gridcolor="#1c2740", tickfont=dict(color="#f2f5fa", size=11)),
        ),
        showlegend=False, height=height, margin=dict(l=40, r=40, t=30, b=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#f2f5fa"),
    )
    return fig


def compare_line_chart(radar_a, radar_b, label_a, label_b):
    cats = [RADAR_LABELS[k] for k in RADAR_ORDER]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cats, y=[radar_a.get(k, 0) for k in RADAR_ORDER], mode="lines+markers+text",
                              name=label_a, line=dict(color="#22d3ee", width=3),
                              text=[radar_a.get(k, 0) for k in RADAR_ORDER], textposition="top center",
                              textfont=dict(color="#22d3ee")))
    fig.add_trace(go.Scatter(x=cats, y=[radar_b.get(k, 0) for k in RADAR_ORDER], mode="lines+markers+text",
                              name=label_b, line=dict(color="#22c55e", width=3), fill="tonexty",
                              fillcolor="rgba(34,197,94,0.12)",
                              text=[radar_b.get(k, 0) for k in RADAR_ORDER], textposition="bottom center",
                              textfont=dict(color="#22c55e")))
    fig.update_layout(
        height=380, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f2f5fa"), yaxis=dict(range=[0, 100], gridcolor="#1c2740"),
        xaxis=dict(gridcolor="#1c2740"), legend=dict(orientation="h", y=1.15),
    )
    return fig


def goto(target):
    st.session_state.page = target
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════
# VIDEO — sample a few still frames so the coach can "see" the match
# ══════════════════════════════════════════════════════════════════════════
MAX_VIDEO_FRAMES = 3  # VISION_MODEL accepts at most 3 images per request


def extract_video_frames(video_path, num_frames=MAX_VIDEO_FRAMES, max_dim=768):
    """Grab a handful of evenly-spaced still frames from a video file, as base64 JPEG data URIs.
    This is a lightweight sample of stills, NOT frame-by-frame tracking — it can't count exact
    passes, tackles, or touches, but gives the coach a visual sense of the match."""
    frames = []
    cap = cv2.VideoCapture(video_path)
    try:
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total <= 0:
            return frames
        fractions = [0.15, 0.5, 0.85][:num_frames]
        for frac in fractions:
            idx = min(max(int(total * frac), 0), total - 1)
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok:
                continue
            h, w = frame.shape[:2]
            scale = max_dim / max(h, w)
            if scale < 1:
                frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
            ok2, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            if ok2:
                b64 = base64.b64encode(buf.tobytes()).decode()
                frames.append(f"data:image/jpeg;base64,{b64}")
    except Exception:
        return frames
    finally:
        cap.release()
    return frames


# ══════════════════════════════════════════════════════════════════════════
# AI ANALYSIS SCHEMA
# ══════════════════════════════════════════════════════════════════════════
ANALYSIS_SCHEMA = """Respond with ONLY valid JSON, no markdown fences, no commentary, matching this exact schema:
{
  "overall_rating": <number 0-10, one decimal>,
  "performance_score": <integer 0-100>,
  "radar": {"passing": <0-100>, "shooting": <0-100>, "dribbling": <0-100>, "fitness": <0-100>,
            "ball_control": <0-100>, "defending": <0-100>, "vision": <0-100>, "off_ball_movement": <0-100>},
  "decision_analysis": {"good_pct": <0-100>, "average_pct": <0-100>, "poor_pct": <0-100>},
  "findings": ["<short finding>", "<short finding>", "<short finding>", "<short finding>"],
  "strengths": "<1-2 sentences>",
  "improvement": "<1-2 sentences>",
  "tactical_insight": "<1-2 sentences>",
  "key_moment": "<one plausible standout moment based on the stats given>",
  "key_takeaway": "<1 sentence coaching takeaway>",
  "recommended_drills": ["<drill name — 1 line reason>", "<drill name — 1 line reason>"],
  "weakest_area": "<one of: passing, shooting, dribbling, fitness, ball_control, defending, vision, off_ball_movement>",
  "strongest_area": "<one of: passing, shooting, dribbling, fitness, ball_control, defending, vision, off_ball_movement>",
  "message": "<one motivational sentence in the coach's voice>"
}
good_pct + average_pct + poor_pct must sum to 100."""


def run_analysis(player_ctx, stats_ctx, drills_text, frames=None):
    frame_note = ""
    if frames:
        frame_note = f"""
You are also given {len(frames)} still frames sampled evenly across the player's uploaded match video.
These are a handful of stills, not full video tracking — you cannot count exact passes, tackles, or
touches from them. Use them only for a qualitative read (intensity, formation, pitch/weather conditions,
apparent skill level, jersey colors). Where a numeric stat below is 0 or missing, treat it as unreported
rather than a true zero, and give your best realistic estimate based on the player's position and what
the frames suggest about the match — and say in tactical_insight that some figures are estimated from
limited video sampling, not measured."""

    prompt = f"""You are an elite UEFA Pro License football coach analysing a player's match.
{player_ctx}
{stats_ctx}
{frame_note}

Available drills to choose from for recommended_drills:
{drills_text}

Base your radar scores, findings, strengths/weaknesses and ratings on the stats, notes, and any video
frames provided — be specific and realistic, not generic.
{ANALYSIS_SCHEMA}"""

    if frames:
        content = [{"type": "text", "text": prompt}]
        for uri in frames[:MAX_VIDEO_FRAMES]:
            content.append({"type": "image_url", "image_url": {"url": uri}})
        messages = [{"role": "user", "content": content}]
        model = VISION_MODEL
    else:
        messages = [{"role": "user", "content": prompt}]
        model = MODEL

    response = client.chat.completions.create(model=model, messages=messages)
    raw = response.choices[0].message.content.strip().strip("`")
    if raw.lower().startswith("json"):
        raw = raw[4:]
    try:
        return json.loads(raw), None
    except (json.JSONDecodeError, ValueError):
        return None, raw


# ══════════════════════════════════════════════════════════════════════════
# NAV
# ══════════════════════════════════════════════════════════════════════════
NAV_PAGES = ["Home", "Analyze", "Drills", "Training", "Progress", "Diet", "Chat"]
if "page" not in st.session_state:
    st.session_state.page = "Home"
if "last_pill" not in st.session_state:
    st.session_state.last_pill = None
if "viewing_session" not in st.session_state:
    st.session_state.viewing_session = None

header()

with st.bottom:
    clicked = st.pills("Select Page:", NAV_PAGES, label_visibility="collapsed", key="nav_pills")
if clicked != st.session_state.last_pill:
    st.session_state.last_pill = clicked
    if clicked:
        st.session_state.page = clicked

page = st.session_state.page
sessions = load_sessions()
profile = load_profile()

def _esc(s):
    return html.escape(str(s))


@st.cache_data(show_spinner=False)
def asset_data_uri(name):
    p = os.path.join(APP_DIR, name)
    if not os.path.exists(p):
        return ""
    with open(p, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    mime = "image/png" if name.lower().endswith(".png") else "image/jpeg"
    return f"data:{mime};base64,{b64}"


def placeholder_radar(height=300):
    cats = [RADAR_LABELS[k] for k in RADAR_ORDER] + [RADAR_LABELS[RADAR_ORDER[0]]]
    fig = go.Figure(go.Scatterpolar(
        r=[50] * len(cats), theta=cats, fill="toself", hoverinfo="skip",
        line=dict(color="#22d3ee", width=2, dash="dot"), fillcolor="rgba(34,211,238,0.10)",
        marker=dict(color="#22d3ee", size=5),
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, ticks="", gridcolor="#1c2740"),
            angularaxis=dict(gridcolor="#1c2740", tickfont=dict(color="#f2f5fa", size=10)),
        ),
        showlegend=False, height=height, margin=dict(l=45, r=45, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#f2f5fa"),
    )
    fig.add_annotation(x=0.5, y=0.5, xref="paper", yref="paper", text="?", showarrow=False,
                       font=dict(size=38, color="#22d3ee", family="Sora"))
    return fig


def render_empty_home():
    """Dashboard shown before the player has analyzed any match (placeholder '?' values)."""
    # ── hero: upload match clip ──
    hero_uri = asset_data_uri("hero_player.jpg")
    art = f'<div class="hero-art" style="background-image:url({hero_uri})"></div>' if hero_uri else ""
    with st.container(border=True):
        st.markdown(
            '<div class="hero-marker"></div>' + art
            + '<div class="hero-checks"><div><span>✔</span>AI ANALYSIS</div>'
            '<div><span>✔</span>PERSONALIZED FEEDBACK</div><div><span>✔</span>TRAINING RECOMMENDATIONS</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="hero-icon">🎥</div><div class="hero-title">UPLOAD<br>MATCH CLIP</div>'
            '<div class="hero-sub">Analyze your game in under 60 seconds.</div>',
            unsafe_allow_html=True,
        )
        if st.button("Upload Video ⬆️", key="hero_upload"):
            goto("Analyze")

    # ── four summary cards ──
    st.markdown(
        '<div class="stat-grid">'
        '<div class="sc"><div class="sc-h"><span>Overall Rating</span><i>↗</i></div>'
        '<div class="sc-big">?<small>/10</small></div>'
        '<div class="gauge"><b></b></div><div class="gauge-scale"><span>?</span><span>?</span><span>?</span></div></div>'
        '<div class="sc"><div class="sc-h"><span>Weakest Area</span><i>◎</i></div>'
        '<div class="sc-name" style="color:var(--amber)">Unknown</div>'
        '<div class="sc-big" style="font-size:1.2rem">?<small>/10</small></div>'
        '<div class="gauge"><b></b></div></div>'
        '<div class="sc"><div class="sc-h"><span>Strongest Area</span><i>★</i></div>'
        '<div class="sc-name" style="color:var(--green)">Unknown</div>'
        '<div class="sc-big" style="font-size:1.2rem">?<small>/10</small></div>'
        '<div class="gauge"><b></b></div></div>'
        '<div class="sc"><div class="sc-h"><span>Focus This Week</span><i>△</i></div>'
        '<div class="sc-name" style="color:var(--cyan)">To be set</div>'
        '<div class="sc-note">Upload a clip to get your focus area.</div>'
        '<div class="ring">?%</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── latest analysis + performance overview ──
    col_a, col_b = st.columns(2)
    with col_a:
        with st.container(border=True):
            st.markdown(
                '<div class="sec-h">Latest Analysis</div>'
                '<div class="thumb"><div class="play">▶</div><span class="dur">??:??</span></div>'
                '<div class="match-row"><div><div class="match-name">Match vs ???</div><div class="muted">Date ?? · Full Match</div></div>'
                '<div class="perf-box"><b>??</b><span class="muted">/100</span><small>PERFORMANCE</small></div></div>'
                '<div class="find-h">AI FINDINGS</div>'
                '<div class="find"><span class="dot g">✓</span>Your strengths will show up here</div>'
                '<div class="find"><span class="dot a">!</span>Lost possession ? times</div>'
                '<div class="find"><span class="dot r">!</span>Your biggest weakness, spotted by AI</div>'
                '<div class="find"><span class="dot a">!</span>Tactical insights from your clip</div>',
                unsafe_allow_html=True,
            )
            if st.button("Analyze a match →", key="empty_analyze", use_container_width=True):
                goto("Analyze")
    with col_b:
        with st.container(border=True):
            st.markdown('<div class="sec-h">Performance Overview</div>', unsafe_allow_html=True)
            st.plotly_chart(placeholder_radar(), use_container_width=True, config={"displayModeBar": False})
            st.markdown(
                '<div class="legend">'
                '<span><i style="background:var(--red)"></i>?-? Needs Work</span>'
                '<span><i style="background:var(--amber)"></i>?-? Average</span>'
                '<span><i style="background:var(--green)"></i>?-? Strong</span></div>',
                unsafe_allow_html=True,
            )

    # ── recommended training + improvement tracker ──
    preferred = ["First Touch Control", "Cone Dribbling Course", "Weak Foot Passing Wall"]
    starter = [d for n in preferred for d in drills if d["name"] == n]
    for d in drills:
        if len(starter) >= 3:
            break
        if d["difficulty"] == "beginner" and d not in starter:
            starter.append(d)
    level = {"beginner": ("Easy", "badge-green"), "intermediate": ("Medium", "badge-amber")}
    icons = ["🎯", "⚽", "👟"]

    col_c, col_d = st.columns(2)
    with col_c:
        with st.container(border=True):
            rows = ""
            for ico, d in zip(icons, starter[:3]):
                lvl, cls = level.get(d["difficulty"], ("Hard", "badge-red"))
                rows += (
                    f'<div class="tr-row"><div class="tr-ico">{ico}</div><div class="tr-name">{_esc(d["name"])}</div>'
                    f'<div class="tr-min">{d["duration_minutes"]} min</div><span class="badge {cls}">{lvl}</span></div>'
                )
            st.markdown(
                '<div class="sec-h">Recommended Training</div>'
                '<div class="sec-sub">Starter drills — personalized after your first match</div>' + rows,
                unsafe_allow_html=True,
            )
            if st.button("Start Training →", key="empty_training", use_container_width=True):
                goto("Training")
    with col_d:
        with st.container(border=True):
            rows = ""
            for k in ["passing", "vision", "shooting", "ball_control", "defending", "fitness"]:
                rows += (
                    f'<div class="imp-row"><span>{RADAR_LABELS[k]}</span><span>?%</span><div class="imp-bar"></div>'
                    f'<span>?%</span><span style="color:var(--green)">↑ ?%</span></div>'
                )
            st.markdown(
                '<div class="sec-h">Improvement Tracker</div>'
                '<div class="imp-head"><span>ATTRIBUTE</span><span>BEFORE</span><span></span><span>AFTER</span><span>CHANGE</span></div>' + rows,
                unsafe_allow_html=True,
            )
            if st.button("View all progress →", key="empty_progress", use_container_width=True):
                goto("Progress")


# ══════════════════════════════════════════════════════════════════════════
# HOME
# ══════════════════════════════════════════════════════════════════════════
if page == "Home":
    display_name = profile.get("name") or CURRENT_USER
    page_title(f"Welcome back, {display_name}", "Every clip makes you better.")

    if not sessions:
        render_empty_home()
    else:
        with st.container(border=True):
            st.markdown("**🎥 Upload Match Clip**")
            st.caption("Analyze your game and get a full coaching breakdown.")
            if st.button("Upload Video ⬆️"):
                goto("Analyze")

        latest = sessions[-1]
        report = latest["ai_report"]
        radar = report["radar"]
        weakest_k, strongest_k = report["weakest_area"], report["strongest_area"]

        st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div class="chip-grid">'
            + chip("Overall Rating", f"{report['overall_rating']:.1f}/10", score_color(report["overall_rating"], 10), report["overall_rating"] * 10)
            + chip("Weakest Area", RADAR_LABELS.get(weakest_k, weakest_k), "var(--amber)", radar.get(weakest_k, 0))
            + chip("Strongest Area", RADAR_LABELS.get(strongest_k, strongest_k), "var(--green)", radar.get(strongest_k, 0))
            + "</div>",
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.markdown(f"**📹 Latest Analysis** — {latest.get('opponent', 'Match')} · {latest['date']}")
            st.markdown(f"<span class='badge badge-cyan'>{report['performance_score']}/100 PERFORMANCE</span>", unsafe_allow_html=True)
            for finding in report.get("findings", []):
                st.write(f"• {finding}")
            if st.button("View Full Analysis →", key="home_view_full"):
                st.session_state.viewing_session = len(sessions) - 1
                goto("History")

        with st.container(border=True):
            st.markdown("**📊 Performance Overview**")
            st.plotly_chart(radar_chart(radar), use_container_width=True, config={"displayModeBar": False})

        with st.container(border=True):
            st.markdown("**📋 Recommended Training**")
            for d in report.get("recommended_drills", []):
                st.write(f"• {d}")
            if st.button("Start Training →"):
                goto("Training")

        if len(sessions) >= 2:
            first_radar = sessions[0]["ai_report"]["radar"]
            with st.container(border=True):
                st.markdown("**📈 Improvement Tracker**")
                rows = ""
                for k in RADAR_ORDER:
                    before, after = first_radar.get(k, 0), radar.get(k, 0)
                    change = after - before
                    c = "var(--green)" if change >= 0 else "var(--red)"
                    rows += (
                        f'<div class="stat-row"><span>{RADAR_LABELS[k]}</span>'
                        f'<span>{before} → {after} &nbsp;'
                        f'<span style="color:{c}">({"+" if change>=0 else ""}{change})</span></span></div>'
                    )
                st.markdown(rows, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# ANALYZE
# ══════════════════════════════════════════════════════════════════════════
elif page == "Analyze":
    page_title("Analyze Match", "Upload your match footage and stats to get AI insights.")

    with st.container(border=True):
        st.markdown("**⬆️ Upload Match Footage**")
        video_file = st.file_uploader("Drag & drop your video here (MP4, MOV)", type=["mp4", "mov"])
        st.caption(
            "Upload a clip and your coach can analyze straight from the video — no stats required. "
            "It samples a few still frames (not full video tracking), so it's a best-effort read of "
            "intensity, formation, and play style. For the sharpest report, add whatever stats you can below too."
        )
        c1, c2 = st.columns(2)
        jersey_number = c1.text_input("Jersey number", value=str(profile.get("jersey_number", "")))
        jersey_color = c2.color_picker("Jersey color", value="#e11d48")

    with st.container(border=True):
        st.markdown("**📝 Match Details**")
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Your name", value=profile.get("name", ""))
            opponent = st.text_input("Opponent", placeholder="e.g. Galaxy FC")
            goals = st.number_input("Goals scored", min_value=0, max_value=10, value=0)
        with c2:
            position = st.selectbox(
                "Your position", ["Goalkeeper", "Defender", "Midfielder", "Winger", "Striker"],
                index=["Goalkeeper", "Defender", "Midfielder", "Winger", "Striker"].index(profile.get("position", "Midfielder")),
            )
            match_date = st.date_input("Match date", value=date.today())
            assists = st.number_input("Assists", min_value=0, max_value=10, value=0)

        weakness = st.text_input(
            "What do you think your biggest weakness was today?"
            + ("" if video_file is None else " (optional — you've uploaded a video)")
        )
        notes = st.text_area("Any other match notes?", placeholder="e.g. I kept losing the ball under pressure in midfield")

        st.markdown("**📊 Match Stats**")
        a1, a2, a3 = st.columns(3)
        shots_on_target = a1.number_input("Shots on target", 0, 30, 0)
        key_passes = a1.number_input("Key passes", 0, 30, 0)
        tackles_won = a1.number_input("Tackles won", 0, 20, 0)
        dribbles_attempted = a2.number_input("Dribbles attempted", 0, 30, 0)
        dribbles_successful = a2.number_input("Dribbles successful", 0, 30, 0)
        duels_won = a2.number_input("Duels won", 0, 30, 0)
        possession_won = a3.number_input("Possession won", 0, 30, 0)
        distance_km = a3.number_input("Distance covered (km)", 0.0, 20.0, 0.0, step=0.1)
        sprints = a3.number_input("Sprints", 0, 60, 0)
        b1, b2, b3 = st.columns(3)
        fouls_won = b1.number_input("Fouls won", 0, 20, 0)
        fouls_committed = b2.number_input("Fouls committed", 0, 20, 0)
        offsides = b3.number_input("Offsides", 0, 10, 0)
        c1b, c2b = st.columns(2)
        yellow_cards = c1b.number_input("Yellow cards", 0, 2, 0)
        red_cards = c2b.number_input("Red cards", 0, 1, 0)

        analyse_clicked = st.button("Analyze Match ⚽")

    # ── past uploads + storage manager ──
    video_sessions = [s for s in sessions if s.get("video_filename")]
    colA, colB = st.columns(2)
    with colA:
        with st.container(border=True):
            st.markdown("**📁 Past Uploads**")
            if not video_sessions:
                st.caption("No videos uploaded yet.")
            for s in reversed(video_sessions[-5:]):
                r = s["ai_report"]
                color = score_color(r["performance_score"])
                st.markdown(
                    f"<div class='stat-row'><span>{s.get('opponent','Match')} · {s['date']}</span>"
                    f"<span style='color:{color}'>{r['performance_score']}/100</span></div>",
                    unsafe_allow_html=True,
                )
    with colB:
        with st.container(border=True):
            st.markdown("**💾 Storage Manager**")
            total_bytes = sum(
                os.path.getsize(os.path.join(UPLOAD_DIR, f)) for f in os.listdir(UPLOAD_DIR)
            ) if os.path.isdir(UPLOAD_DIR) else 0
            gb_used = total_bytes / (1024 ** 3)
            st.markdown(f"**{gb_used:.2f} GB** used across {len(os.listdir(UPLOAD_DIR)) if os.path.isdir(UPLOAD_DIR) else 0} files")
            st.progress(min(gb_used / 10, 1.0))

    if analyse_clicked:
        if not weakness and video_file is None:
            st.warning("Tell your coach what your biggest weakness was, or upload a match video!")
        else:
            video_filename = None
            frames = []
            if video_file is not None:
                video_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{video_file.name}"
                video_path = os.path.join(UPLOAD_DIR, video_filename)
                with open(video_path, "wb") as f:
                    f.write(video_file.getbuffer())

                with st.spinner("Sampling frames from your video..."):
                    frames = extract_video_frames(video_path)
                if not frames:
                    st.warning("Couldn't read frames from that video — continuing with the stats provided.")

            with st.spinner("Your coach is analysing your match..."):
                weakness_key = weakness or "unspecified — infer from the match video"
                matching_drills = []
                for d in drills:
                    for tag in d["tags"]:
                        if any(w in weakness_key.lower() for w in tag.split("_")):
                            matching_drills.append(f"{d['name']} — {d['description']}")
                            break
                drills_text = "\n".join(matching_drills) if matching_drills else "\n".join(f"{d['name']} — {d['description']}" for d in drills)

                player_ctx = f"Player: {name}\nPosition: {position}\nOpponent: {opponent or 'N/A'}"
                stats_ctx = f"""Match stats:
- Goals: {goals}, Assists: {assists}
- Shots on target: {shots_on_target}, Key passes: {key_passes}, Tackles won: {tackles_won}
- Dribbles: {dribbles_successful}/{dribbles_attempted} successful, Duels won: {duels_won}
- Possession won: {possession_won}, Distance: {distance_km} km, Sprints: {sprints}
- Fouls won: {fouls_won}, Fouls committed: {fouls_committed}, Offsides: {offsides}
- Cards: {yellow_cards} yellow, {red_cards} red
- Self-reported weakness: {weakness or 'Not provided'}
- Match notes: {notes or 'None provided'}"""

                report, raw_fallback = run_analysis(player_ctx, stats_ctx, drills_text, frames=frames)

            if report is None:
                st.error("Couldn't parse the coach's report — showing raw output instead.")
                st.write(raw_fallback)
            else:
                dribble_pct = round(100 * dribbles_successful / dribbles_attempted) if dribbles_attempted else None

                save_session({
                    "date": match_date.strftime("%d %b %Y"),
                    "name": name, "position": position, "opponent": opponent,
                    "video_filename": video_filename,
                    "analyzed_from_video": bool(frames),
                    "goals": goals, "assists": assists,
                    "shots_on_target": shots_on_target, "key_passes": key_passes, "tackles_won": tackles_won,
                    "dribbles_attempted": dribbles_attempted, "dribbles_successful": dribbles_successful,
                    "dribble_pct": dribble_pct,
                    "duels_won": duels_won, "possession_won": possession_won, "distance_km": distance_km,
                    "sprints": sprints, "fouls_won": fouls_won, "fouls_committed": fouls_committed,
                    "offsides": offsides, "yellow_cards": yellow_cards, "red_cards": red_cards,
                    "weakness": weakness, "notes": notes,
                    "ai_report": report,
                })
                profile["name"], profile["position"] = name, position
                if jersey_number:
                    profile["jersey_number"] = jersey_number
                save_profile(profile)

                st.success("✅ Match analyzed and saved!")
                st.session_state.viewing_session = len(load_sessions()) - 1
                goto("History")

# ══════════════════════════════════════════════════════════════════════════
# DRILLS
# ══════════════════════════════════════════════════════════════════════════
elif page == "Drills":
    page_title("🏃 Drill Library", "Build your training toolkit, one drill at a time.")

    all_tags = sorted({t for d in drills for t in d["tags"]})
    selected_tag = st.selectbox("Filter by skill", ["All"] + all_tags)

    completed = set(profile.get("completed_drills", []))
    diff_badge = {"Easy": "badge-green", "Medium": "badge-amber", "Hard": "badge-red"}

    for d in drills:
        if selected_tag != "All" and selected_tag not in d["tags"]:
            continue
        with st.container(border=True):
            b = diff_badge.get(d["difficulty"], "badge-cyan")
            done = d["name"] in completed
            st.markdown(
                f"**{'✅ ' if done else ''}{d['name']}** &nbsp; "
                f"<span class='badge {b}'>{d['difficulty']}</span> "
                f"<span class='badge badge-cyan'>⏱ {d['duration_minutes']} min</span> "
                f"<span class='badge badge-cyan'>👥 {d['players_needed']}</span>",
                unsafe_allow_html=True,
            )
            with st.expander("Details"):
                st.write(f"**Description:** {d['description']}")
                st.write(f"**Setup:** {d['setup']}")
                st.write(f"**Reps:** {d['reps']}")
                st.write(f"**Objective:** {d['objective']}")
                if st.button("Mark Complete" if not done else "Mark Incomplete", key=f"drill_{d['name']}"):
                    if done:
                        completed.discard(d["name"])
                    else:
                        completed.add(d["name"])
                    profile["completed_drills"] = list(completed)
                    save_profile(profile)
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════
# TRAINING
# ══════════════════════════════════════════════════════════════════════════
elif page == "Training":
    page_title("📅 Training", "Train smarter. Improve faster.")

    training_log = load_training_log()
    completed_drills = set(profile.get("completed_drills", []))

    with st.container(border=True):
        st.markdown(f"**Trainings completed:** {len(training_log)} &nbsp;·&nbsp; **Drills mastered:** {len(completed_drills)}/{len(drills)}")
        st.progress(min(len(completed_drills) / max(len(drills), 1), 1.0))

    if not sessions:
        st.info("Analyze a match first so your coach can build a plan focused on your weaknesses.")
    else:
        last = sessions[-1]
        with st.container(border=True):
            st.markdown(f"<span class='badge badge-amber'>Last weakness</span> {last['weakness'] or 'Not specified — analyzed from video'}", unsafe_allow_html=True)
            focus = st.selectbox("What do you want to focus on today?",
                                  ["My biggest weakness", "Passing", "Dribbling", "Finishing", "Defending", "Fitness"])
            duration = st.selectbox("Session duration", ["30 minutes", "45 minutes", "60 minutes", "90 minutes"])
            generate = st.button("Generate Training Plan 📋")

        if generate:
            with st.spinner("Building your session plan..."):
                drills_list = "\n".join(f"{d['name']} ({d['duration_minutes']} mins) — {d['description']}" for d in drills)
                prompt = f"""You are an elite football coach building a training session plan.
Player's last match weakness: {last['weakness']}
Today's focus: {focus}
Session duration: {duration}

Available drills:
{drills_list}

Build a complete training session plan with:
1. Warm up (5 mins)
2. Main drills from the list that fit the focus and duration
3. Cool down (5 mins)
4. One key coaching point

Format clearly using markdown headers."""
                response = client.chat.completions.create(model=MODEL, messages=[{"role": "user", "content": prompt}])
            st.session_state.current_plan = response.choices[0].message.content

        if st.session_state.get("current_plan"):
            with st.container(border=True):
                st.markdown(st.session_state.current_plan)
                if st.button("Mark Today's Training Complete ✅"):
                    log_training_complete()
                    st.success("Logged! Great work today.")
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════
# PROGRESS
# ══════════════════════════════════════════════════════════════════════════
elif page == "Progress":
    page_title("📈 Progress", "Track your improvement. See results.")

    if len(sessions) < 1:
        st.info("Analyze at least one match to start tracking progress.")
    else:
        training_log = load_training_log()
        ratings = [s["ai_report"]["overall_rating"] for s in sessions]
        st.markdown(
            '<div class="chip-grid">'
            + chip("Matches Analyzed", len(sessions), "var(--cyan)")
            + chip("Trainings Completed", len(training_log), "var(--green)")
            + chip("First → Latest Rating", f"{ratings[0]:.1f} → {ratings[-1]:.1f}",
                   "var(--green)" if ratings[-1] >= ratings[0] else "var(--red)")
            + "</div>",
            unsafe_allow_html=True,
        )

        if len(sessions) >= 2:
            with st.container(border=True):
                st.markdown("**📊 Week's Progress**")
                labels = [f"{s.get('opponent','Match')} · {s['date']}" for s in sessions]
                idx_a, idx_b = st.select_slider(
                    "Compare two matches", options=list(range(len(sessions))),
                    value=(0, len(sessions) - 1), format_func=lambda i: labels[i],
                )
                fig = compare_line_chart(sessions[idx_a]["ai_report"]["radar"], sessions[idx_b]["ai_report"]["radar"],
                                          labels[idx_a], labels[idx_b])
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.caption("Analyze a second match to unlock the comparison chart.")

# ══════════════════════════════════════════════════════════════════════════
# DIET
# ══════════════════════════════════════════════════════════════════════════
elif page == "Diet":
    page_title("🥗 Diet", "Fuel your body. Maximize your performance.")

    PLAYSTYLE_MULTIPLIER = {
        "Box-to-Box": 1.75, "Wing-Back": 1.75, "False Nine": 1.65, "Playmaker": 1.6,
        "Target Man": 1.6, "Sweeper": 1.55, "Ball-Winner": 1.7,
    }

    with st.container(border=True):
        st.markdown("**🧮 Diet Calculator**")
        c1, c2 = st.columns(2)
        with c1:
            sex = st.selectbox("Sex", ["Male", "Female"])
            age = st.number_input("Age", 10, 60, 20)
            height_cm = st.number_input("Height (cm)", 120, 220, 175)
        with c2:
            weight_kg = st.number_input("Weight (kg)", 30, 150, 70)
            playstyle = st.selectbox("Play-style", list(PLAYSTYLE_MULTIPLIER.keys()))
            goal = st.selectbox("Goal", ["Maintain", "Build muscle", "Cut weight"])
        restrictions = st.text_input("Dietary restrictions (optional)", placeholder="e.g. No dairy, no shellfish")
        calc = st.button("Calculate My Diet Plan 🧮")

    if calc:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + (5 if sex == "Male" else -161)
        tdee = bmr * PLAYSTYLE_MULTIPLIER[playstyle]
        if goal == "Build muscle":
            tdee += 300
        elif goal == "Cut weight":
            tdee -= 300

        protein_g = round(weight_kg * 2.0)
        fat_g = round((tdee * 0.27) / 9)
        remaining_cal = tdee - (protein_g * 4) - (fat_g * 9)
        carbs_g = round(max(remaining_cal, 0) / 4)
        fiber_g = round(tdee / 1000 * 14)
        water_l = round(weight_kg * 0.033 + 0.6, 1)

        st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div class="chip-grid">'
            + chip("Calories", f"{round(tdee)} kcal", "var(--red)")
            + chip("Protein", f"{protein_g} g", "var(--amber)")
            + chip("Carbs", f"{carbs_g} g", "var(--cyan)")
            + chip("Fats", f"{fat_g} g", "var(--purple)")
            + chip("Fiber", f"{fiber_g} g", "var(--green)")
            + chip("Water", f"{water_l} L", "var(--blue)")
            + "</div>",
            unsafe_allow_html=True,
        )
        st.session_state.diet_result = dict(
            calories=round(tdee), protein=protein_g, carbs=carbs_g, fat=fat_g,
            fiber=fiber_g, water=water_l, restrictions=restrictions,
        )

    if st.session_state.get("diet_result"):
        with st.container(border=True):
            st.markdown("**🍽️ Sample Meal Plan**")
            if st.button("Generate Sample Meal Plan"):
                dr = st.session_state.diet_result
                prompt = f"""You are a sports nutritionist for a competitive football player.
Daily targets: {dr['calories']} kcal, {dr['protein']}g protein, {dr['carbs']}g carbs, {dr['fat']}g fat, {dr['fiber']}g fiber.
Dietary restrictions: {dr['restrictions'] or 'none'}.
Suggest a simple one-day meal plan (breakfast, lunch, dinner, 1 snack) that roughly hits these targets. Keep it practical and concise, using markdown."""
                with st.spinner("Building your meal plan..."):
                    response = client.chat.completions.create(model=MODEL, messages=[{"role": "user", "content": prompt}])
                st.markdown(response.choices[0].message.content)

# ══════════════════════════════════════════════════════════════════════════
# PROFILE
# ══════════════════════════════════════════════════════════════════════════
elif page == "Profile":
    page_title("Profile", "Your journey. Your stats. Your growth.")

    with st.container(border=True):
        c1, c2 = st.columns(2)
        name = c1.text_input("Name", value=profile.get("name", ""))
        jersey_number = c2.text_input("Jersey number", value=str(profile.get("jersey_number", "")))
        position = st.selectbox(
            "Position", ["Goalkeeper", "Defender", "Midfielder", "Winger", "Striker"],
            index=["Goalkeeper", "Defender", "Midfielder", "Winger", "Striker"].index(profile.get("position", "Midfielder")),
        )
        if st.button("Save Profile"):
            profile.update({"name": name, "jersey_number": jersey_number, "position": position})
            save_profile(profile)
            st.success("Saved!")

    training_log = load_training_log()
    ratings = [s["ai_report"]["overall_rating"] for s in sessions]
    goals_total = sum(s.get("goals", 0) for s in sessions)
    assists_total = sum(s.get("assists", 0) for s in sessions)

    st.markdown(
        '<div class="chip-grid">'
        + chip("Matches Uploaded", len(sessions), "var(--cyan)")
        + chip("Trainings Completed", len(training_log), "var(--green)")
        + chip("Best Performance", f"{max(ratings):.1f}" if ratings else "—", "var(--amber)")
        + "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="chip-grid">'
        + chip("Goals Scored", goals_total, "var(--cyan)")
        + chip("Assists", assists_total, "var(--cyan)")
        + chip("Average Rating", f"{(sum(ratings)/len(ratings)):.1f}" if ratings else "—", "var(--purple)")
        + "</div>",
        unsafe_allow_html=True,
    )

    if sessions:
        avg_radar = {k: round(sum(s["ai_report"]["radar"].get(k, 0) for s in sessions) / len(sessions)) for k in RADAR_ORDER}
        buckets = {
            "Attacking": ["shooting", "off_ball_movement"],
            "Defending": ["defending"],
            "Fitness": ["fitness"],
            "Technical": ["dribbling", "ball_control"],
            "Tactical": ["passing", "vision"],
        }
        with st.container(border=True):
            st.markdown("**📊 Performance Overview (all-time average)**")
            for label, keys in buckets.items():
                val = round(sum(avg_radar[k] for k in keys) / len(keys))
                st.markdown(
                    f"<div style='margin-bottom:.5rem'><div class='stat-row'><span>{label}</span><span>{val}%</span></div>"
                    f"<div class='bar-track'><div class='bar-fill' style='width:{val}%;background:{score_color(val)}'></div></div></div>",
                    unsafe_allow_html=True,
                )

# ══════════════════════════════════════════════════════════════════════════
# HISTORY / FULL ANALYSIS + DETAILED BREAKDOWN
# ══════════════════════════════════════════════════════════════════════════
elif page == "History":
    if st.session_state.viewing_session is None:
        page_title("📋 Match History", "Every match logged. Every trend tracked.")
        if not sessions:
            st.info("No sessions saved yet. Analyze a match first!")
        else:
            for i, s in reversed(list(enumerate(sessions))):
                r = s["ai_report"]
                with st.container(border=True):
                    st.markdown(
                        f"**{s.get('opponent','Match')}** &nbsp; "
                        f"<span class='badge badge-cyan'>{s['date']}</span> &nbsp; "
                        f"<span class='badge {'badge-green' if r['performance_score']>=70 else 'badge-amber' if r['performance_score']>=40 else 'badge-red'}'>{r['performance_score']}/100</span>",
                        unsafe_allow_html=True,
                    )
                    if st.button("View Full Analysis →", key=f"hist_{i}"):
                        st.session_state.viewing_session = i
                        st.rerun()
    else:
        i = st.session_state.viewing_session
        s = sessions[i]
        r = s["ai_report"]
        if st.button("← Back to Match History"):
            st.session_state.viewing_session = None
            st.rerun()

        page_title(f"{s.get('opponent','Match')}", f"{s['date']} · {s['position']}")
        if s.get("analyzed_from_video"):
            st.markdown("<span class='badge badge-cyan'>📹 Analyzed from video</span>", unsafe_allow_html=True)

        if s.get("video_filename"):
            vid_path = os.path.join(UPLOAD_DIR, s["video_filename"])
            if os.path.exists(vid_path):
                st.video(vid_path)

        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                st.markdown("**🧠 AI Findings**")
                st.write(f"**Strengths:** {r['strengths']}")
                st.write(f"**Improvement:** {r['improvement']}")
                st.write(f"**Tactical Insight:** {r['tactical_insight']}")
                st.write(f"**Key Moment:** {r['key_moment']}")
                st.markdown(f"<div class='quote-box'>⭐ {r['key_takeaway']}</div>", unsafe_allow_html=True)
        with col2:
            with st.container(border=True):
                st.markdown("**📈 Match Stats**")
                stat_pairs = [
                    ("Goals", s.get("goals")), ("Assists", s.get("assists")),
                    ("Shots on Target", s.get("shots_on_target")),
                    ("Dribble Success", f"{s.get('dribble_pct')}%" if s.get("dribble_pct") is not None else "—"),
                    ("Key Passes", s.get("key_passes")),
                    ("Tackles Won", s.get("tackles_won")), ("Duels Won", s.get("duels_won")),
                    ("Possession Won", s.get("possession_won")), ("Distance", f"{s.get('distance_km')} km"),
                    ("Sprints", s.get("sprints")), ("Yellow Cards", s.get("yellow_cards")),
                    ("Red Cards", s.get("red_cards")),
                ]
                rows = "".join(f"<div class='stat-row'><span>{k}</span><span>{v}</span></div>" for k, v in stat_pairs)
                st.markdown(rows, unsafe_allow_html=True)

        with st.container(border=True):
            rcolor = score_color(r["overall_rating"], 10)
            st.markdown(
                f"<div style='text-align:center'><div style='color:var(--muted)'>OVERALL RATING</div>"
                f"<div style='font-family:Sora,sans-serif;font-weight:800;font-size:2.6rem;color:{rcolor}'>{r['overall_rating']:.1f}</div></div>",
                unsafe_allow_html=True,
            )

        with st.container(border=True):
            st.markdown("**📊 Detailed Breakdown**")
            st.plotly_chart(radar_chart(r["radar"]), use_container_width=True, config={"displayModeBar": False})

            da = r["decision_analysis"]
            st.markdown("**⚖️ Decision Analysis**")
            for label, pct, color in [("Good Decisions", da["good_pct"], "var(--green)"),
                                       ("Average Decisions", da["average_pct"], "var(--amber)"),
                                       ("Poor Decisions", da["poor_pct"], "var(--red)")]:
                st.markdown(
                    f"<div class='stat-row'><span>{label}</span><span>{pct}%</span></div>"
                    f"<div class='bar-track'><div class='bar-fill' style='width:{pct}%;background:{color}'></div></div>",
                    unsafe_allow_html=True,
                )

        with st.container(border=True):
            st.markdown("**📋 Recommended Drills**")
            for d in r.get("recommended_drills", []):
                st.write(f"• {d}")
            st.markdown(f"<div class='quote-box'>🗣️ {r['message']}</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# CHAT
# ══════════════════════════════════════════════════════════════════════════
elif page == "Chat":
    page_title("💬 Chat With Your Coach", "Tactics, advice, motivation — ask anything.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for message in st.session_state.chat_history:
        avatar = "🧑" if message["role"] == "user" else "⚽"
        st.chat_message(message["role"], avatar=avatar).write(message["content"])

    user_input = st.chat_input("Ask your coach something...")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.chat_message("user", avatar="🧑").write(user_input)

        messages = [{"role": "system", "content": "You are an elite UEFA Pro License football coach. Answer all questions with specific, practical football advice. Be direct, motivating and knowledgeable."}]
        messages.extend(st.session_state.chat_history)

        with st.spinner("Coach is thinking..."):
            response = client.chat.completions.create(model=MODEL, messages=messages)
            coach_reply = response.choices[0].message.content

        st.session_state.chat_history.append({"role": "assistant", "content": coach_reply})
        st.chat_message("assistant", avatar="⚽").write(coach_reply)
