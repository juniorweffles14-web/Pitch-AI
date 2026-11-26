import streamlit as st
from groq import Groq
import json
import os
import re
import base64
import io
import html
import inspect
import secrets
import smtplib
import time
from PIL import Image
from datetime import datetime, date
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
import plotly.graph_objects as go
import bcrypt
try:
    import cv2
except ImportError:  # app still works (without video frames) if OpenCV is missing
    cv2 = None
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid
from email.mime.multipart import MIMEMultipart

APP_DIR = os.path.dirname(os.path.abspath(__file__))


def _find_asset(*names):
    for n in names:
        p = os.path.join(APP_DIR, n)
        if os.path.exists(p):
            return p
    return None


def _secret(name, default=""):
    """Read from st.secrets or env vars without crashing when no secrets.toml exists."""
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.environ.get(name, default)


def _esc(s):
    return html.escape(str(s))


# Streamlit renamed use_container_width -> width="stretch". Pick whichever this install supports.
def _stretch_kwargs(fn):
    try:
        if "width" in inspect.signature(fn).parameters:
            return {"width": "stretch"}
    except (TypeError, ValueError):
        pass
    return {"use_container_width": True}


BTN_STRETCH = _stretch_kwargs(st.button)
CHART_STRETCH = _stretch_kwargs(st.plotly_chart)


# Favicon: your "Untitled design" logo (favicon.png is a transparent, cropped copy of it).
_fav_path = _find_asset("favicon.png", "Untitled_design.jpg", "Untitled design.jpg", "Untitled_design.png", "Untitled design.png")
try:
    PAGE_ICON = Image.open(_fav_path) if _fav_path else "⚽"
except Exception:
    PAGE_ICON = "⚽"

st.set_page_config(page_title="Pitch AI", page_icon=PAGE_ICON, layout="wide", initial_sidebar_state="collapsed")

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

# Fluid layout: fills the screen on phones and tablets; on big desktop monitors the content is
# kept to a readable width in the middle while the background still covers the whole screen.
RESPONSIVE_CSS = """
<style>
.block-container{ width:100%; max-width:100% !important;
  padding-left:clamp(.8rem,4vw,2.5rem) !important; padding-right:clamp(.8rem,4vw,2.5rem) !important; }
@media (min-width:1100px){ .block-container{ max-width:1100px !important; margin-left:auto !important; margin-right:auto !important; } }
img, video{ max-width:100%; }
</style>
"""
st.markdown(RESPONSIVE_CSS, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# PASSWORD RESET — emailed verification code
# ══════════════════════════════════════════════════════════════════════════
RESET_CODE_TTL_SECONDS = 600  # 10 minutes
RESET_MAX_ATTEMPTS = 5
MIN_PASSWORD_LEN = 8

# Set these in .streamlit/secrets.toml (or as environment variables):
#   SENDER_EMAIL = "you@gmail.com"
#   SENDER_PASSWORD = "your-new-gmail-app-password"
SENDER_EMAIL = str(_secret("SENDER_EMAIL")).strip()
SENDER_PASSWORD = str(_secret("SENDER_PASSWORD")).replace(" ", "")


def send_reset_code(receiver_email, code):
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        st.error("Email sending isn't configured. Set SENDER_EMAIL and SENDER_PASSWORD in your secrets.")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Your Pitch AI reset code"
        msg["From"] = formataddr(("Pitch AI", SENDER_EMAIL))
        msg["To"] = receiver_email
        msg["Reply-To"] = SENDER_EMAIL
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain=SENDER_EMAIL.split("@")[-1] or "pitchai.app")

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #0a0e17; padding: 30px;">
            <div style="max-width: 480px; margin: auto; background: #111a2b; border-radius: 16px; padding: 32px;">
                <h2 style="color: #22d3ee;">⚽ Pitch AI</h2>
                <p style="color: #f2f5fa;">Hi there! You requested a password reset.</p>
                <p style="color: #f2f5fa;">Your reset code is:</p>
                <div style="text-align: center; margin: 24px 0;">
                    <span style="font-size: 2.5rem; font-weight: 800; letter-spacing: 8px; color: #22d3ee;">
                        {code}
                    </span>
                </div>
                <p style="color: #8b98ad; font-size: 0.85rem;">This code expires in {RESET_CODE_TTL_SECONDS // 60} minutes. If you did not request this, ignore this email.</p>
                <hr style="border: none; border-top: 1px solid #1c2740; margin: 24px 0;">
                <p style="color: #8b98ad; font-size: 0.75rem;">Pitch AI — Your Personal AI Football Coach</p>
            </div>
        </body>
        </html>
        """

        plain_body = (
            f"Your Pitch AI reset code is: {code}\n\n"
            f"It expires in {RESET_CODE_TTL_SECONDS // 60} minutes. If you did not request this, ignore this email."
        )
        msg.attach(MIMEText(plain_body, "plain", "utf-8"))  # plain-text part helps avoid spam filters
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            refused = server.sendmail(SENDER_EMAIL, receiver_email, msg.as_string())

        if refused:  # sendmail returns the recipients the server refused
            print(f"[reset email] recipient refused: {list(refused)}")
            st.error("The mail server refused that email address. Check the address on the account.")
            return False
        print(f"[reset email] handed to Gmail for {_mask_email(receiver_email)}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("[reset email] Gmail rejected SENDER_EMAIL / SENDER_PASSWORD")
        st.error("Gmail rejected the login. Check that SENDER_EMAIL and SENDER_PASSWORD "
                 "(a Gmail app password) are correct in your secrets.")
        return False
    except Exception as e:
        print(f"[reset email] {type(e).__name__}: {e}")
        st.error(f"Couldn't send the reset email ({type(e).__name__}). Please try again later.")
        return False


RESET_STATE_KEYS = ("reset_code_sent", "reset_code", "reset_code_username", "reset_code_expiry", "reset_attempts")


def _clear_reset_state():
    for k in RESET_STATE_KEYS:
        st.session_state.pop(k, None)


@st.cache_resource
def _reset_request_log():
    return {}  # shared across sessions for the life of the server process


def _reset_rate_allowed(username, max_per_hour=3):
    """True if fewer than max_per_hour reset emails were sent to this account in the last hour."""
    now = time.time()
    log = _reset_request_log()
    log[username] = [x for x in log.get(username, []) if now - x < 3600]
    return len(log[username]) < max_per_hour


def _reset_rate_record(username):
    _reset_request_log().setdefault(username, []).append(time.time())


def _find_account(usernames, text):
    """Match what the person typed to an account: username (any case) or email address."""
    text = text.strip()
    if text in usernames:
        return text
    if text.lower() in usernames:
        return text.lower()
    for key, data in usernames.items():
        if str((data or {}).get("email", "")).strip().lower() == text.lower() and text:
            return key
    return None


def _mask_email(email):
    name, _, domain = email.partition("@")
    return (name[:1] + "*" * max(len(name) - 1, 2) + "@" + domain) if domain else email


def _password_problem(pw):
    if len(pw) < MIN_PASSWORD_LEN:
        return f"Password must be at least {MIN_PASSWORD_LEN} characters."
    if not (re.search(r"[A-Za-z]", pw) and re.search(r"\d", pw)):
        return "Password must include at least one letter and one number."
    return None


@st.cache_data(show_spinner=False)
def _plain_data_uri(path, mtime):
    """Image file -> data URI (mtime is only here so the cache refreshes when the file changes)."""
    mime = "image/png" if path.lower().endswith(".png") else "image/jpeg"
    with open(path, "rb") as f:
        return f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"


@st.cache_data(show_spinner=False)
def _hero_bg_uri(path, mtime):
    """The landing photo as a small JPEG data URI (the PNG is ~1 MB) for use as a full-screen background."""
    try:
        im = Image.open(path).convert("RGB")
        im.thumbnail((1000, 1400))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=80, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return _plain_data_uri(path, mtime)


@st.cache_data(show_spinner=False)
def _logo_data_uri(path, mtime):
    """logo.png with its empty transparent margin trimmed off, as a data URI ('' if it can't be read)."""
    try:
        im = Image.open(path).convert("RGBA")
        bbox = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
        if bbox:
            im = im.crop(bbox)
        buf = io.BytesIO()
        im.save(buf, "PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


def logo_html(height=64, center=False):
    """The Pitch AI logo (logo.png next to this file); falls back to a text logo if it's missing."""
    p = _find_asset("logo.png", "logo.jpg", "logo.jpeg")
    uri = _logo_data_uri(p, os.path.getmtime(p)) if p else ""
    if uri:
        margin = "margin:0 auto;" if center else ""
        return f'<img src="{uri}" alt="Pitch AI" style="height:{height}px;width:auto;display:block;{margin}">'
    return '<div class="pitch-logo">⚽ PITCH <span>AI</span></div>'


def _set_auth_view(view):
    st.session_state.auth_view = view


AUTH_SUBTITLES = {
    "login": "Welcome back. Log in to continue.",
    "signup": "Create your account to get started.",
    "reset": "Reset your password with a code sent to your email.",
}

AUTH_CSS = """
<style>
.block-container{ max-width:560px !important; margin-left:auto !important; margin-right:auto !important; }
.st-key-auth_back button{ background:transparent !important; color:#8b98ad !important;
  border:1px solid rgba(34,211,238,.25) !important; }
/* Log in / Register / Send code / Reset buttons: light blue with dark blue text; inverted on hover */
.stApp div[data-testid="stFormSubmitButton"] button,
.stApp .st-key-send_code_btn button, .stApp .st-key-reset_final_btn button{
  width:100%; min-height:3rem; border-radius:12px !important; font-weight:800 !important;
  background:#8fdcff !important; color:#06224a !important; border:2px solid #8fdcff !important;
  transition:background .15s, color .15s; }
.stApp div[data-testid="stFormSubmitButton"] button *,
.stApp .st-key-send_code_btn button *, .stApp .st-key-reset_final_btn button *{
  color:#06224a !important; font-weight:800 !important; }
.stApp div[data-testid="stFormSubmitButton"] button:hover,
.stApp .st-key-send_code_btn button:hover, .stApp .st-key-reset_final_btn button:hover{
  background:#06224a !important; color:#8fdcff !important; border-color:#8fdcff !important; }
.stApp div[data-testid="stFormSubmitButton"] button:hover *,
.stApp .st-key-send_code_btn button:hover *, .stApp .st-key-reset_final_btn button:hover *{
  color:#8fdcff !important; }
div[data-testid="stVerticalBlockBorderWrapper"]{ background:rgba(8,16,30,.82); border-radius:16px; backdrop-filter:blur(6px); }
</style>
"""

WELCOME_CSS = """
<style>
.block-container{ padding-top:1rem !important; padding-bottom:1rem !important; max-width:100% !important; }
.welcome-spacer{ height:calc(100vh - 18rem); height:calc(100dvh - 18rem); min-height:14rem; }
.st-key-welcome_start, .st-key-welcome_login{ align-self:center; width:min(86%,420px) !important; }
.st-key-welcome_start button, .st-key-welcome_login button{
  width:100%; height:3.3rem; border-radius:999px !important; font-weight:800 !important; letter-spacing:.08em; }
.st-key-welcome_start button{ background:#00e5ff !important; color:#03121c !important; border:none !important; }
.st-key-welcome_start button p{ color:#03121c !important; font-weight:800; letter-spacing:.08em; }
.st-key-welcome_login button{ background:rgba(3,14,26,.6) !important; color:#f2f5fa !important;
  border:1.5px solid #22d3ee !important; }
.st-key-welcome_login button p{ color:#f2f5fa !important; font-weight:800; letter-spacing:.08em; }
</style>
"""


def _hero_background_css(uri, dim):
    """Full-screen photo behind the page. dim 0 = as-is, higher = darker (for forms). The side fades
    blend the portrait photo into the page colour on wide screens."""
    return f"""
<style>
header[data-testid="stHeader"]{{ background:transparent !important; }}
.stApp{{
  background:
    linear-gradient(to right,#000d1a 0%,rgba(0,13,26,0) 22%,rgba(0,13,26,0) 78%,#000d1a 100%),
    linear-gradient(rgba(0,13,26,{dim}),rgba(0,13,26,{dim})),
    url("{uri}") center top / auto 100% no-repeat,
    #000d1a !important;
  background-attachment:fixed !important;
}}
</style>"""


def apply_auth_background():
    """Same photo as the welcome screen, dimmed, behind the log-in / sign-up / reset forms."""
    hero = _find_asset("landing_hero.png", "landing_hero.jpg")
    if hero:
        st.markdown(_hero_background_css(_hero_bg_uri(hero, os.path.getmtime(hero)), 0.8), unsafe_allow_html=True)
    else:
        st.markdown("<style>.stApp{ background:linear-gradient(180deg,#000d1a 0%,#021724 100%) fixed !important; }</style>",
                    unsafe_allow_html=True)


def render_welcome():
    """First screen: full-screen photo with GET STARTED -> sign-up and LOG IN -> log-in on top of it."""
    st.markdown(WELCOME_CSS, unsafe_allow_html=True)
    hero = _find_asset("landing_hero.png", "landing_hero.jpg")
    if hero:
        st.markdown(_hero_background_css(_hero_bg_uri(hero, os.path.getmtime(hero)), 0), unsafe_allow_html=True)
        st.markdown('<div class="welcome-spacer"></div>', unsafe_allow_html=True)
    else:
        st.markdown("<style>.stApp{ background:linear-gradient(180deg,#000d1a 0%,#021724 100%) fixed !important; }</style>"
                    + logo_html(120, center=True)
                    + '<div class="auth-sub">Analyze. Train. Improve.<br>Your Personal AI Soccer Coach.</div>',
                    unsafe_allow_html=True)
    st.button("GET STARTED", key="welcome_start", on_click=_set_auth_view, args=("signup",))
    st.button("LOG IN", key="welcome_login", on_click=_set_auth_view, args=("login",))


# ══════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════
CONFIG_PATH = os.path.join(APP_DIR, "config.yaml")

if not os.path.exists(CONFIG_PATH):
    st.error(
        "`config.yaml` not found. Create one for streamlit-authenticator, e.g.:\n\n"
        "```yaml\ncredentials:\n  usernames: {}\ncookie:\n  name: pitch_ai_cookie\n"
        "  key: change_this_random_string\n  expiry_days: 30\n```"
    )
    st.stop()

with open(CONFIG_PATH, "r") as f:
    config = yaml.load(f, Loader=SafeLoader)


def save_config():
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


authenticator = stauth.Authenticate(
    config["credentials"], config["cookie"]["name"], config["cookie"]["key"], config["cookie"]["expiry_days"]
)

if st.session_state.get("authentication_status") is not True:
    auth_view = st.session_state.get("auth_view", "welcome")

    if auth_view not in AUTH_SUBTITLES:  # "welcome" (the first screen)
        # Returning users with a valid "remember me" cookie skip the welcome screen.
        try:
            authenticator.login(location="unrendered")
        except Exception:
            pass  # older streamlit-authenticator versions: the cookie is checked by the Log in form instead
        if st.session_state.get("authentication_status") is True:
            st.rerun()
        render_welcome()
        st.stop()

    st.markdown(AUTH_CSS, unsafe_allow_html=True)
    apply_auth_background()
    st.button("← Back", key="auth_back", on_click=_set_auth_view, args=("login" if auth_view == "reset" else "welcome",))
    st.markdown(logo_html(110, center=True), unsafe_allow_html=True)
    st.markdown(f'<div class="auth-sub">{AUTH_SUBTITLES[auth_view]}</div>', unsafe_allow_html=True)

    with st.container(border=True):
        if auth_view == "login":
            try:
                authenticator.login()
            except Exception as e:
                st.error(e)
            if st.session_state.get("authentication_status") is False:
                st.error("Username or password is incorrect.")
            elif st.session_state.get("authentication_status") is None:
                st.caption("Enter your credentials to continue.")
            st.button("Forgot password?", key="to_reset", on_click=_set_auth_view, args=("reset",))
            st.button("New here? Create an account", key="to_signup", on_click=_set_auth_view, args=("signup",))
        elif auth_view == "signup":
            try:
                result = authenticator.register_user()
                if result:
                    email, username, name = result
                    if email:
                        st.success("Account created! Tap “Log in” below to sign in.")
                        save_config()
            except Exception as e:
                st.error(e)
            st.button("Already have an account? Log in", key="to_login", on_click=_set_auth_view, args=("login",))
        else:  # reset
            st.subheader("🔐 Reset Password")
            st.write("Enter your username or email and we'll send a reset code to your registered email.")

            reset_username = st.text_input("Username or email", key="reset_username_input").strip()

            if st.button("Send Reset Code 📧", key="send_code_btn"):
                if not reset_username:
                    st.error("Please enter your username or email.")
                else:
                    usernames = config["credentials"]["usernames"]
                    account_key = _find_account(usernames, reset_username)
                    user_data = usernames.get(account_key) if account_key else None
                    user_email = (user_data or {}).get("email", "")

                    _clear_reset_state()
                    if not user_data:
                        print(f"[reset email] no account matches {reset_username[:3]}...")
                        st.error("We couldn't find an account with that username or email. "
                                 "Check the spelling, or create a new account.")
                    elif not user_email:
                        st.error("That account has no email address on file, so a code can't be sent.")
                    elif not _reset_rate_allowed(account_key):
                        st.error("Too many reset emails were sent for this account. Please wait an hour and try again.")
                    else:
                        code = str(secrets.randbelow(900000) + 100000)
                        if send_reset_code(user_email, code):  # shows its own error if sending fails
                            _reset_rate_record(account_key)
                            st.session_state.reset_code = code
                            st.session_state.reset_code_username = account_key
                            st.session_state.reset_code_expiry = time.time() + RESET_CODE_TTL_SECONDS
                            st.session_state.reset_code_sent = True
                            st.session_state.reset_attempts = 0
                            st.success(f"A reset code was sent to {_mask_email(user_email)}. "
                                       "It can take a minute, so check your spam folder too.")

            if st.session_state.get("reset_code_sent"):
                st.divider()

                entered_code = st.text_input("Enter the 6 digit code from your email", key="entered_code")
                new_password = st.text_input("New Password", type="password", key="new_password")
                confirm_password = st.text_input("Confirm New Password", type="password", key="confirm_password")

                if st.button("Reset Password ✅", key="reset_final_btn"):
                    stored_code = st.session_state.get("reset_code")
                    stored_user = st.session_state.get("reset_code_username")
                    expiry = st.session_state.get("reset_code_expiry", 0) or 0

                    if not entered_code or not new_password or not confirm_password:
                        st.error("Please fill in all fields.")

                    elif st.session_state.get("reset_attempts", 0) >= RESET_MAX_ATTEMPTS:
                        st.error("Too many incorrect attempts. Please request a new code.")
                        _clear_reset_state()

                    elif not stored_code or not stored_user or time.time() > expiry:
                        st.error("That code is invalid or has expired. Please request a new one.")
                        _clear_reset_state()

                    elif not secrets.compare_digest(entered_code.strip(), stored_code):
                        st.session_state.reset_attempts = st.session_state.get("reset_attempts", 0) + 1
                        st.error("Incorrect code. Please try again.")

                    elif new_password != confirm_password:
                        st.error("Passwords do not match.")

                    elif _password_problem(new_password):
                        st.error(_password_problem(new_password))

                    else:
                        hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
                        config["credentials"]["usernames"][stored_user]["password"] = hashed
                        save_config()
                        st.success("✅ Password reset successfully! Please login with your new password.")
                        _clear_reset_state()
    st.stop()

# Signed in. After a log-out the user starts from the welcome screen again.
st.session_state.auth_view = "welcome"

# Sanitize the username before it is used in file paths.
CURRENT_USER = re.sub(r"[^A-Za-z0-9_.-]", "_", str(st.session_state.get("username", "player"))) or "player"

# ══════════════════════════════════════════════════════════════════════════
# API CLIENT — key loaded from secrets/env, never hardcoded
# ══════════════════════════════════════════════════════════════════════════
GROQ_API_KEY = _secret("GROQ_API_KEY")
if not GROQ_API_KEY:
    st.error(
        "No Groq API key found. Add `GROQ_API_KEY = \"your-key\"` to "
        "`.streamlit/secrets.toml`, or set it as an environment variable."
    )
    st.stop()
client = Groq(api_key=GROQ_API_KEY)
MODEL = _secret("TEXT_MODEL", "openai/gpt-oss-120b")
# Multimodal model used when match frames are attached (max 3 images per request).
# Groq retired Llama 4 Scout on 2026-07-17; qwen/qwen3.6-27b is the vision replacement it lists (a Preview model,
# so it can change). Override with VISION_MODEL in your secrets if Groq's model list changes.
VISION_MODEL = _secret("VISION_MODEL", "qwen/qwen3.6-27b")

# ══════════════════════════════════════════════════════════════════════════
# STORAGE — per-user JSON files + uploaded video files on disk
# ══════════════════════════════════════════════════════════════════════════
DATA_DIR = os.path.join(APP_DIR, "pitch_ai_data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads", CURRENT_USER)
os.makedirs(UPLOAD_DIR, exist_ok=True)

SESSIONS_FILE = os.path.join(DATA_DIR, f"sessions_{CURRENT_USER}.json")
PROFILE_FILE = os.path.join(DATA_DIR, f"profile_{CURRENT_USER}.json")
TRAINING_LOG_FILE = os.path.join(DATA_DIR, f"training_log_{CURRENT_USER}.json")


def load_json(path, default):
    """Read JSON; return `default` if the file is missing, empty, or corrupted."""
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            try:  # keep the unreadable file instead of silently overwriting it on the next save
                os.replace(path, path + ".corrupt")
            except OSError:
                pass
            return default
        except OSError:
            return default
    return default


def save_json(path, data):
    """Atomic write so a crash mid-save can't leave a half-written file."""
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def load_sessions():
    data = load_json(SESSIONS_FILE, [])
    return data if isinstance(data, list) else []


def save_session(session):
    sessions = load_sessions()
    sessions.append(session)
    save_json(SESSIONS_FILE, sessions)


POSITIONS = ["Goalkeeper", "Defender", "Midfielder", "Winger", "Striker"]
DEFAULT_PROFILE = {"name": "", "position": "Midfielder", "jersey_number": 10, "completed_drills": []}


def _position_index(pos):
    return POSITIONS.index(pos) if pos in POSITIONS else POSITIONS.index("Midfielder")


def load_profile():
    data = load_json(PROFILE_FILE, {})
    if not isinstance(data, dict):
        data = {}
    return {**DEFAULT_PROFILE, **data}


def save_profile(p):
    save_json(PROFILE_FILE, p)


def load_training_log():
    data = load_json(TRAINING_LOG_FILE, [])
    return data if isinstance(data, list) else []


def log_training_complete():
    log = load_training_log()
    log.append({"date": datetime.now().strftime("%d %b %Y, %H:%M")})
    save_json(TRAINING_LOG_FILE, log)


try:
    with open(os.path.join(APP_DIR, "drills.json"), "r") as f:
        drills = json.load(f)["drills"]
except (OSError, json.JSONDecodeError, KeyError) as e:
    st.error(f"Couldn't load `drills.json` (expecting a top-level \"drills\" list): {e}")
    st.stop()

RADAR_ORDER = ["passing", "shooting", "dribbling", "fitness", "ball_control", "defending", "vision", "off_ball_movement"]
RADAR_LABELS = {
    "passing": "Passing", "shooting": "Shooting", "dribbling": "Dribbling", "fitness": "Fitness",
    "ball_control": "Ball Control", "defending": "Defending", "vision": "Vision",
    "off_ball_movement": "Off-Ball Movement",
}


def goto(target):
    """Switch page and keep the bottom nav pills in sync with it."""
    st.session_state.page = target
    st.session_state.sub = None
    st.session_state._nav_override = target
    st.rerun()


def header():
    c1, c2 = st.columns([5, 1])
    with c1:
        st.markdown(logo_html(56), unsafe_allow_html=True)
    with c2:
        if st.button("👤", key="avatar_btn", help="Profile"):
            goto("Profile")


def page_title(title, subtitle):
    st.markdown(f'<div class="page-title">{_esc(title)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-sub">{_esc(subtitle)}</div>', unsafe_allow_html=True)


def score_color(v, max_v=100):
    pct = v / max_v
    if pct >= 0.7:
        return "var(--green)"
    if pct >= 0.4:
        return "var(--amber)"
    return "var(--red)"


def chip(label, value, color="var(--cyan)", bar_pct=None):
    bar = f'<div class="bar-track"><div class="bar-fill" style="width:{bar_pct}%;background:{color}"></div></div>' if bar_pct is not None else ""
    return f'<div class="chip"><div class="label">{_esc(label)}</div><div class="value" style="color:{color}">{_esc(value)}</div>{bar}</div>'


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


# ══════════════════════════════════════════════════════════════════════════
# VIDEO — sample a few still frames so the coach can "see" the match
# ══════════════════════════════════════════════════════════════════════════
MAX_VIDEO_FRAMES = 3  # keep well under the vision model's per-request image limit


def extract_video_frames(video_path, num_frames=MAX_VIDEO_FRAMES, max_dim=768):
    """Grab a handful of evenly-spaced still frames from a video file, as base64 JPEG data URIs.
    This is a lightweight sample of stills, NOT frame-by-frame tracking — it can't count exact
    passes, tackles, or touches, but gives the coach a visual sense of the match."""
    frames = []
    if cv2 is None:
        return frames
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


def parse_json_reply(raw):
    """Pull the JSON object out of a model reply, tolerating <think> blocks, fences, and preamble."""
    if not raw:
        return None
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.S)
    m = re.search(r"\{.*\}", raw, flags=re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except (json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _num(v, lo, hi, default, as_int=False):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    x = max(lo, min(hi, x))
    return int(round(x)) if as_int else round(x, 1)


def _str_list(v, limit=8):
    if isinstance(v, str):
        v = [v]
    if not isinstance(v, list):
        return []
    return [str(x) for x in v if x][:limit]


def normalize_report(rep):
    """Coerce an AI (or older saved) report into the exact shape the UI expects, so a malformed
    reply can never crash a page."""
    rep = rep if isinstance(rep, dict) else {}
    raw_radar = rep.get("radar") if isinstance(rep.get("radar"), dict) else {}
    radar = {k: _num(raw_radar.get(k), 0, 100, 0, as_int=True) for k in RADAR_ORDER}

    weakest = rep.get("weakest_area")
    strongest = rep.get("strongest_area")
    if weakest not in RADAR_ORDER:
        weakest = min(RADAR_ORDER, key=lambda k: radar[k])
    if strongest not in RADAR_ORDER:
        strongest = max(RADAR_ORDER, key=lambda k: radar[k])

    da = rep.get("decision_analysis") if isinstance(rep.get("decision_analysis"), dict) else {}
    good = _num(da.get("good_pct"), 0, 100, 0)
    avg = _num(da.get("average_pct"), 0, 100, 0)
    poor = _num(da.get("poor_pct"), 0, 100, 0)
    total = good + avg + poor
    if total <= 0:
        good, avg, poor = 34, 33, 33
    else:
        good, avg, poor = (round(x * 100 / total, 1) for x in (good, avg, poor))

    return {
        "overall_rating": _num(rep.get("overall_rating"), 0, 10, 0.0),
        "performance_score": _num(rep.get("performance_score"), 0, 100, 0, as_int=True),
        "radar": radar,
        "decision_analysis": {"good_pct": good, "average_pct": avg, "poor_pct": poor},
        "findings": _str_list(rep.get("findings")),
        "strengths": str(rep.get("strengths", "")),
        "improvement": str(rep.get("improvement", "")),
        "tactical_insight": str(rep.get("tactical_insight", "")),
        "key_moment": str(rep.get("key_moment", "")),
        "key_takeaway": str(rep.get("key_takeaway", "")),
        "recommended_drills": _str_list(rep.get("recommended_drills")),
        "weakest_area": weakest,
        "strongest_area": strongest,
        "message": str(rep.get("message", "")),
    }


def run_analysis(player_ctx, stats_ctx, drills_text, frames=None):
    """Returns (normalized_report, None) on success, or (None, error_or_raw_text) on failure."""
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

    attempts = []
    if frames:
        content = [{"type": "text", "text": prompt}]
        for uri in frames[:MAX_VIDEO_FRAMES]:
            content.append({"type": "image_url", "image_url": {"url": uri}})
        attempts.append((VISION_MODEL, [{"role": "user", "content": content}]))
    # Text-only fallback (also the normal path when no video was attached).
    attempts.append((MODEL, [{"role": "user", "content": prompt}]))

    last_error = "Unknown error"
    for model, messages in attempts:
        try:
            response = client.chat.completions.create(model=model, messages=messages)
            raw = (response.choices[0].message.content or "").strip()
        except Exception as e:
            last_error = f"{model}: {e}"
            continue
        parsed = parse_json_reply(raw)
        if parsed is not None:
            return normalize_report(parsed), None
        last_error = raw or "Empty response from the model."
    return None, last_error


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
if "sub" not in st.session_state:
    st.session_state.sub = None  # which sub-page of the current page is open (None = the page's menu)

header()

# If a button moved us to another page, update the pills BEFORE they are drawn
# (a widget's state can't be changed after it has been created in the same run).
if "_nav_override" in st.session_state:
    _target = st.session_state.pop("_nav_override")
    st.session_state.nav_pills = _target if _target in NAV_PAGES else None
    st.session_state.last_pill = st.session_state.nav_pills

with st.bottom:
    clicked = st.pills("Select Page:", NAV_PAGES, label_visibility="collapsed", key="nav_pills")
if clicked != st.session_state.last_pill:
    st.session_state.last_pill = clicked
    if clicked:
        st.session_state.page = clicked
        st.session_state.sub = None

page = st.session_state.page
sessions = load_sessions()
profile = load_profile()


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


# ══════════════════════════════════════════════════════════════════════════
# BUTTON-MENU NAVIGATION
# Every page is a short menu of buttons; each button opens a sub-page with one
# small piece of content, so nothing needs scrolling.
# ══════════════════════════════════════════════════════════════════════════
ss = st.session_state

MENU_CSS = """
<style>
.block-container{ padding-top:.8rem !important; padding-bottom:6rem !important; }
.page-sub{ margin-bottom:.7rem !important; }
div[class*="st-key-hub_"] button{
  width:100%; min-height:3.2rem; justify-content:flex-start !important; text-align:left;
  border-radius:14px !important; background:linear-gradient(135deg,#111b30,#0d1524) !important;
  color:#f2f5fa !important; border:1px solid var(--card-border) !important; font-weight:700 !important; }
div[class*="st-key-hub_"] button:hover{ border-color:#22d3ee !important; }
div[class*="st-key-hub_"] button p{ text-align:left; width:100%; }
.st-key-sub_back button{ background:transparent !important; color:#8b98ad !important;
  border:1px solid rgba(34,211,238,.25) !important; min-height:2.1rem; padding:.1rem .9rem; }
.st-key-primary_cta button{ width:100%; min-height:3.2rem; border-radius:999px !important; border:none !important;
  background:#00e5ff !important; color:#03121c !important; font-weight:800 !important; letter-spacing:.04em; }
.st-key-primary_cta button p{ color:#03121c !important; font-weight:800; }
/* keep the header row and the Prev/Next rows on ONE line, even on a phone */
div[data-testid="stHorizontalBlock"]:has(.st-key-avatar_btn),
div[data-testid="stHorizontalBlock"]:has([class*="st-key-pgbtn_"]){ flex-wrap:nowrap !important; }
div[data-testid="stHorizontalBlock"]:has(.st-key-avatar_btn) > div,
div[data-testid="stHorizontalBlock"]:has([class*="st-key-pgbtn_"]) > div{ min-width:0 !important; }
</style>
"""
st.markdown(MENU_CSS, unsafe_allow_html=True)

# New account in this browser session -> forget the previous user's half-filled forms and chat.
if ss.get("_last_user") != CURRENT_USER:
    for _k in list(ss.keys()):
        if _k.startswith(("an_", "df_", "pg_")) or _k in (
            "chat_history", "current_plan", "diet_result", "diet_plan", "viewing_session", "drill_filter",
        ):
            del ss[_k]
    ss._last_user = CURRENT_USER
    ss.sub = None

# Streamlit forgets a widget's value when its page isn't drawn. These forms span several
# sub-pages, so re-assign their values on every run to keep them.
ANALYZE_NUM_DEFAULTS = {
    "an_goals": 0, "an_assists": 0, "an_shots": 0, "an_keypasses": 0,
    "an_drib_att": 0, "an_drib_succ": 0, "an_tackles": 0, "an_duels": 0, "an_possession": 0,
    "an_fouls_won": 0, "an_fouls_comm": 0, "an_distance": 0.0, "an_sprints": 0,
    "an_offsides": 0, "an_yellow": 0, "an_red": 0,
}
ANALYZE_KEYS = ["an_jersey", "an_jersey_color", "an_name", "an_opponent", "an_position",
                "an_date", "an_weakness", "an_notes"] + list(ANALYZE_NUM_DEFAULTS)
DIET_KEYS = ["df_sex", "df_age", "df_height", "df_weight", "df_style", "df_goal", "df_restr"]
for _k in ANALYZE_KEYS + DIET_KEYS + ["drill_filter"]:
    if _k in ss:
        ss[_k] = ss[_k]


def init_analyze_state():
    ss.setdefault("an_jersey", str(profile.get("jersey_number", "")))
    ss.setdefault("an_jersey_color", "#e11d48")
    ss.setdefault("an_name", profile.get("name", ""))
    ss.setdefault("an_opponent", "")
    ss.setdefault("an_position", POSITIONS[_position_index(profile.get("position"))])
    ss.setdefault("an_date", date.today())
    ss.setdefault("an_weakness", "")
    ss.setdefault("an_notes", "")
    for k, v in ANALYZE_NUM_DEFAULTS.items():
        ss.setdefault(k, v)


def reset_analyze_state():
    for k in ANALYZE_KEYS + ["an_video"]:
        ss.pop(k, None)
    ss.an_up_n = ss.get("an_up_n", 0) + 1  # gives the video uploader a fresh, empty state


def open_sub(name):
    ss.sub = name


def close_sub():
    ss.sub = None


def _open_match(i):
    ss.viewing_session = i
    ss.sub = None


def _close_match():
    ss.viewing_session = None
    ss.sub = None


def hub_btn(key, label, sub=None):
    """A menu button that opens a sub-page."""
    st.button(label, key=f"hub_{key}", on_click=open_sub, args=(sub or key,))


def hub_go(key, label, target):
    """A menu button that jumps to another main page."""
    if st.button(label, key=f"hub_{key}"):
        goto(target)


def sub_header(title, subtitle="", back=close_sub):
    st.button("← Back", key="sub_back", on_click=back)
    page_title(title, subtitle)


def _pg_step(key, delta):
    ss[f"pg_{key}"] = max(0, ss.get(f"pg_{key}", 0) + delta)


def paginate(items, per_page, key):
    key = re.sub(r"\W", "_", key)
    pages = max(1, -(-len(items) // per_page))
    cur = min(ss.get(f"pg_{key}", 0), pages - 1)
    ss[f"pg_{key}"] = cur
    return items[cur * per_page:(cur + 1) * per_page], cur, pages


def pager(key, cur, pages):
    if pages <= 1:
        return
    key = re.sub(r"\W", "_", key)
    c1, c2, c3 = st.columns(3)
    c1.button("◀ Prev", key=f"pgbtn_prev_{key}", on_click=_pg_step, args=(key, -1), disabled=cur == 0)
    c2.markdown(f"<div style='text-align:center;padding-top:.55rem;color:var(--muted)'>{cur + 1} / {pages}</div>",
                unsafe_allow_html=True)
    c3.button("Next ▶", key=f"pgbtn_next_{key}", on_click=_pg_step, args=(key, 1), disabled=cur >= pages - 1)


# ══════════════════════════════════════════════════════════════════════════
# HOME
# ══════════════════════════════════════════════════════════════════════════
if page == "Home":
    sub = ss.sub
    display_name = profile.get("name") or CURRENT_USER
    has_data = bool(sessions)
    if has_data:
        latest = sessions[-1]
        report = normalize_report(latest.get("ai_report"))
        radar = report["radar"]
        weakest_k, strongest_k = report["weakest_area"], report["strongest_area"]

    if sub is None:
        page_title(f"Welcome back, {display_name}", "Every clip makes you better.")
        if has_data:
            st.markdown(
                '<div class="chip-grid">'
                + chip("Overall Rating", f"{report['overall_rating']:.1f}/10", score_color(report["overall_rating"], 10), report["overall_rating"] * 10)
                + chip("Weakest Area", RADAR_LABELS.get(weakest_k, weakest_k), "var(--amber)", radar.get(weakest_k, 0))
                + chip("Strongest Area", RADAR_LABELS.get(strongest_k, strongest_k), "var(--green)", radar.get(strongest_k, 0))
                + "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.caption("Analyze your game in under 60 seconds. Upload a clip to get started.")
        hub_go("upload", "🎥  Upload match clip", "Analyze")
        hub_btn("latest", "📹  Latest analysis")
        hub_btn("overview", "📊  Performance overview")
        hub_btn("training", "📋  Recommended training")
        hub_btn("tracker", "📈  Improvement tracker")

    elif sub == "latest":
        if has_data:
            sub_header("📹 Latest analysis", f"{latest.get('opponent') or 'Match'} · {latest.get('date', '')}")
            st.markdown(f"<span class='badge badge-cyan'>{report['performance_score']}/100 PERFORMANCE</span>", unsafe_allow_html=True)
            for finding in report["findings"]:
                st.write(f"• {finding}")
            if st.button("View Full Analysis →", key="hub_home_full"):
                ss.viewing_session = len(sessions) - 1
                goto("History")
        else:
            sub_header("📹 Latest analysis", "Your first match report will appear here.")
            st.markdown(
                '<div class="thumb"><div class="play">▶</div><span class="dur">??:??</span></div>'
                '<div class="match-row"><div><div class="match-name">Match vs ???</div><div class="muted">Date ?? · Full Match</div></div>'
                '<div class="perf-box"><b>??</b><span class="muted">/100</span><small>PERFORMANCE</small></div></div>'
                '<div class="find-h">AI FINDINGS</div>'
                '<div class="find"><span class="dot g">✓</span>Your strengths will show up here</div>'
                '<div class="find"><span class="dot r">!</span>Your biggest weakness, spotted by AI</div>',
                unsafe_allow_html=True,
            )
            hub_go("analyze_first", "Analyze a match →", "Analyze")

    elif sub == "overview":
        sub_header("📊 Performance overview", "How your skills add up.")
        if has_data:
            st.plotly_chart(radar_chart(radar, height=340), config={"displayModeBar": False}, **CHART_STRETCH)
        else:
            st.plotly_chart(placeholder_radar(), config={"displayModeBar": False}, **CHART_STRETCH)
            st.caption("Your radar fills in after your first analysis.")

    elif sub == "training":
        sub_header("📋 Recommended training", "Drills picked for you.")
        if has_data:
            for d in report["recommended_drills"]:
                st.write(f"• {d}")
        else:
            preferred = ["First Touch Control", "Cone Dribbling Course", "Weak Foot Passing Wall"]
            starter = [d for n in preferred for d in drills if d.get("name") == n]
            for d in drills:
                if len(starter) >= 3:
                    break
                if d.get("difficulty") == "beginner" and d not in starter:
                    starter.append(d)
            st.caption("Starter drills — personalized after your first match.")
            for d in starter[:3]:
                st.write(f"• **{d.get('name', 'Drill')}** · {d.get('duration_minutes', '?')} min")
        hub_go("start_training", "Start Training →", "Training")

    elif sub == "tracker":
        sub_header("📈 Improvement tracker", "Your first match vs your latest.")
        if has_data and len(sessions) >= 2:
            first_radar = normalize_report(sessions[0].get("ai_report"))["radar"]
            rows = ""
            for k in RADAR_ORDER:
                before, after = first_radar.get(k, 0), radar.get(k, 0)
                change = after - before
                c = "var(--green)" if change >= 0 else "var(--red)"
                rows += (
                    f'<div class="stat-row"><span>{RADAR_LABELS[k]}</span>'
                    f'<span>{before} → {after} &nbsp;'
                    f'<span style="color:{c}">({"+" if change >= 0 else ""}{change})</span></span></div>'
                )
            st.markdown(rows, unsafe_allow_html=True)
        else:
            st.info("Analyze at least two matches to see how you're improving.")
            hub_go("analyze_more", "Analyze a match →", "Analyze")

# ══════════════════════════════════════════════════════════════════════════
# ANALYZE
# ══════════════════════════════════════════════════════════════════════════
elif page == "Analyze":
    init_analyze_state()
    sub = ss.sub
    vid = ss.get("an_video")

    if sub is None:
        page_title("Analyze Match", "Fill in what you can, then tap Analyze.")
        hub_btn("video", f"🎥  Match video{'   ✅' if vid else ''}")
        hub_btn("details", "📝  Match details")
        hub_btn("attack", "⚽  Attacking stats")
        hub_btn("defend", "🛡️  Defending stats")
        hub_btn("physical", "🏃  Physical & discipline")
        analyse_clicked = st.button("Analyze Match ⚽", key="primary_cta")

        if analyse_clicked:
            weakness = ss.an_weakness.strip()
            if not weakness and not vid:
                st.warning("Add a match video, or tell your coach your biggest weakness in Match details.")
            elif ss.an_drib_succ > ss.an_drib_att:
                st.warning("Successful dribbles can't be higher than dribbles attempted (Attacking stats).")
            else:
                video_filename = None
                frames = []
                if vid:
                    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", os.path.basename(vid["name"]))
                    video_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe_name}"
                    video_path = os.path.join(UPLOAD_DIR, video_filename)
                    with open(video_path, "wb") as f:
                        f.write(vid["bytes"])
                    with st.spinner("Sampling frames from your video..."):
                        frames = extract_video_frames(video_path)
                    if not frames:
                        st.warning("Couldn't read frames from that video — continuing with the stats provided.")

                name, opponent, position = ss.an_name, ss.an_opponent, ss.an_position
                goals, assists, notes = ss.an_goals, ss.an_assists, ss.an_notes
                with st.spinner("Your coach is analysing your match..."):
                    weakness_key = weakness or "unspecified — infer from the match video"
                    matching_drills = []
                    for d in drills:
                        for tag in d.get("tags", []):
                            if any(w in weakness_key.lower() for w in tag.split("_")):
                                matching_drills.append(f"{d['name']} — {d['description']}")
                                break
                    drills_text = "\n".join(matching_drills) if matching_drills else "\n".join(f"{d['name']} — {d['description']}" for d in drills)

                    player_ctx = f"Player: {name}\nPosition: {position}\nOpponent: {opponent or 'N/A'}"
                    stats_ctx = f"""Match stats:
- Goals: {goals}, Assists: {assists}
- Shots on target: {ss.an_shots}, Key passes: {ss.an_keypasses}, Tackles won: {ss.an_tackles}
- Dribbles: {ss.an_drib_succ}/{ss.an_drib_att} successful, Duels won: {ss.an_duels}
- Possession won: {ss.an_possession}, Distance: {ss.an_distance} km, Sprints: {ss.an_sprints}
- Fouls won: {ss.an_fouls_won}, Fouls committed: {ss.an_fouls_comm}, Offsides: {ss.an_offsides}
- Cards: {ss.an_yellow} yellow, {ss.an_red} red
- Self-reported weakness: {weakness or 'Not provided'}
- Match notes: {notes or 'None provided'}"""

                    report, raw_fallback = run_analysis(player_ctx, stats_ctx, drills_text, frames=frames)

                if report is None:
                    st.error("Your coach couldn't produce a readable report this time. Please try again.")
                    with st.expander("Details"):
                        st.write(raw_fallback)
                else:
                    dribble_pct = round(100 * ss.an_drib_succ / ss.an_drib_att) if ss.an_drib_att else None
                    save_session({
                        "date": ss.an_date.strftime("%d %b %Y"),
                        "name": name, "position": position, "opponent": opponent,
                        "video_filename": video_filename,
                        "analyzed_from_video": bool(frames),
                        "goals": goals, "assists": assists,
                        "shots_on_target": ss.an_shots, "key_passes": ss.an_keypasses, "tackles_won": ss.an_tackles,
                        "dribbles_attempted": ss.an_drib_att, "dribbles_successful": ss.an_drib_succ,
                        "dribble_pct": dribble_pct,
                        "duels_won": ss.an_duels, "possession_won": ss.an_possession, "distance_km": ss.an_distance,
                        "sprints": ss.an_sprints, "fouls_won": ss.an_fouls_won, "fouls_committed": ss.an_fouls_comm,
                        "offsides": ss.an_offsides, "yellow_cards": ss.an_yellow, "red_cards": ss.an_red,
                        "weakness": weakness, "notes": notes,
                        "ai_report": report,
                    })
                    profile["name"], profile["position"] = name, position
                    if ss.an_jersey:
                        profile["jersey_number"] = ss.an_jersey
                    save_profile(profile)
                    reset_analyze_state()
                    ss.viewing_session = len(load_sessions()) - 1
                    goto("History")

    elif sub == "video":
        sub_header("🎥 Match video", "Optional — your coach can analyze straight from the clip.")
        up_n = ss.get("an_up_n", 0)
        f = st.file_uploader("Choose a video (MP4 or MOV)", type=["mp4", "mov"], key=f"an_uploader_{up_n}")
        if f is not None and (not vid or vid["name"] != f.name or len(vid["bytes"]) != f.size):
            ss.an_video = {"name": f.name, "bytes": f.getvalue()}
            vid = ss.an_video
        if vid:
            st.success(f"Attached: {vid['name']} ({len(vid['bytes']) / 1e6:.0f} MB)")

            def _remove_video():
                ss.pop("an_video", None)
                ss.an_up_n = ss.get("an_up_n", 0) + 1

            st.button("Remove video", key="an_remove_video", on_click=_remove_video)
        st.text_input("Jersey number", key="an_jersey")
        st.color_picker("Jersey color", key="an_jersey_color")
        st.caption("Your coach samples a few still frames, so it's a best-effort read of intensity and play style.")

    elif sub == "details":
        sub_header("📝 Match details")
        st.text_input("Your name", key="an_name")
        st.text_input("Opponent", key="an_opponent", placeholder="e.g. Galaxy FC")
        st.selectbox("Your position", POSITIONS, key="an_position")
        st.date_input("Match date", key="an_date")
        st.text_input("Biggest weakness today?", key="an_weakness")
        if vid:
            st.caption("Optional — you've attached a video.")
        st.text_area("Other match notes", key="an_notes", height=70,
                     placeholder="e.g. I kept losing the ball under pressure in midfield")

    elif sub == "attack":
        sub_header("⚽ Attacking stats")
        st.number_input("Goals scored", 0, 10, key="an_goals")
        st.number_input("Assists", 0, 10, key="an_assists")
        st.number_input("Shots on target", 0, 30, key="an_shots")
        st.number_input("Key passes", 0, 30, key="an_keypasses")
        st.number_input("Dribbles attempted", 0, 30, key="an_drib_att")
        st.number_input("Dribbles successful", 0, 30, key="an_drib_succ")

    elif sub == "defend":
        sub_header("🛡️ Defending stats")
        st.number_input("Tackles won", 0, 20, key="an_tackles")
        st.number_input("Duels won", 0, 30, key="an_duels")
        st.number_input("Possession won", 0, 30, key="an_possession")
        st.number_input("Fouls won", 0, 20, key="an_fouls_won")
        st.number_input("Fouls committed", 0, 20, key="an_fouls_comm")

    elif sub == "physical":
        sub_header("🏃 Physical & discipline")
        st.number_input("Distance covered (km)", 0.0, 20.0, step=0.1, key="an_distance")
        st.number_input("Sprints", 0, 60, key="an_sprints")
        st.number_input("Offsides", 0, 10, key="an_offsides")
        st.number_input("Yellow cards", 0, 2, key="an_yellow")
        st.number_input("Red cards", 0, 1, key="an_red")

# ══════════════════════════════════════════════════════════════════════════
# DRILLS
# ══════════════════════════════════════════════════════════════════════════
elif page == "Drills":
    sub = ss.sub
    completed = set(profile.get("completed_drills", []))
    diff_badge = {"easy": "badge-green", "beginner": "badge-green", "medium": "badge-amber",
                  "intermediate": "badge-amber", "hard": "badge-red", "advanced": "badge-red"}

    if sub is None:
        page_title("🏃 Drill Library", "Tap a drill to see how it works.")
        all_tags = sorted({t for d in drills for t in d.get("tags", [])})
        selected_tag = st.selectbox("Filter by skill", ["All"] + all_tags, key="drill_filter")
        shown = [d for d in drills if selected_tag == "All" or selected_tag in d.get("tags", [])]
        chunk, cur, pages = paginate(shown, 4, f"drills_{selected_tag}")
        if not shown:
            st.caption("No drills for that skill yet.")
        for d in chunk:
            done = d.get("name") in completed
            label = f"{'✅ ' if done else ''}{d.get('name', 'Drill')}  ·  {d.get('duration_minutes', '?')} min"
            st.button(label, key=f"hub_drill_{d.get('name')}", on_click=open_sub, args=(f"drill:{d.get('name')}",))
        pager(f"drills_{selected_tag}", cur, pages)

    elif sub.startswith("drill:"):
        d = next((x for x in drills if x.get("name") == sub[6:]), None)
        if d is None:
            close_sub()
            st.rerun()
        done = d["name"] in completed
        sub_header(f"{'✅ ' if done else ''}{d['name']}")
        b = diff_badge.get(str(d.get("difficulty", "")).lower(), "badge-cyan")
        st.markdown(
            f"<span class='badge {b}'>{_esc(d.get('difficulty', ''))}</span> "
            f"<span class='badge badge-cyan'>⏱ {_esc(d.get('duration_minutes', '?'))} min</span> "
            f"<span class='badge badge-cyan'>👥 {_esc(d.get('players_needed', '?'))}</span>",
            unsafe_allow_html=True,
        )
        st.write(f"**Description:** {d.get('description', '')}")
        st.write(f"**Setup:** {d.get('setup', '')}")
        st.write(f"**Reps:** {d.get('reps', '')}")
        st.write(f"**Objective:** {d.get('objective', '')}")
        if st.button("Mark Complete" if not done else "Mark Incomplete", key="primary_cta"):
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
    sub = ss.sub
    training_log = load_training_log()
    completed_drills = set(profile.get("completed_drills", []))

    if sub is None:
        page_title("📅 Training", "Train smarter. Improve faster.")
        st.markdown(f"**Trainings completed:** {len(training_log)} &nbsp;·&nbsp; **Drills mastered:** {len(completed_drills)}/{len(drills)}")
        st.progress(min(len(completed_drills) / max(len(drills), 1), 1.0))
        hub_btn("plan", "📋  Build today's plan")
        if ss.get("current_plan"):
            hub_btn("viewplan", "📄  View today's plan")
        hub_go("drills", "🏃  Browse drills", "Drills")

    elif sub == "plan":
        sub_header("📋 Build today's plan", "Your coach builds a session around your weakness.")
        if not sessions:
            st.info("Analyze a match first so your coach can build a plan focused on your weaknesses.")
        else:
            last = sessions[-1]
            st.markdown(f"<span class='badge badge-amber'>Last weakness</span> {_esc(last.get('weakness') or 'Not specified — analyzed from video')}", unsafe_allow_html=True)
            focus = st.selectbox("Focus for today",
                                 ["My biggest weakness", "Passing", "Dribbling", "Finishing", "Defending", "Fitness"])
            duration = st.selectbox("Session duration", ["30 minutes", "45 minutes", "60 minutes", "90 minutes"])
            if st.button("Generate Training Plan 📋", key="primary_cta"):
                with st.spinner("Building your session plan..."):
                    drills_list = "\n".join(f"{d['name']} ({d['duration_minutes']} mins) — {d['description']}" for d in drills)
                    prompt = f"""You are an elite football coach building a training session plan.
Player's last match weakness: {last.get('weakness') or 'not specified'}
Today's focus: {focus}
Session duration: {duration}

Available drills:
{drills_list}

Build a complete training session plan with:
1. Warm up (5 mins)
2. Main drills from the list that fit the focus and duration
3. Cool down (5 mins)
4. One key coaching point

Keep the whole plan under 250 words. Format clearly using markdown."""
                    plan_ok = False
                    try:
                        response = client.chat.completions.create(model=MODEL, messages=[{"role": "user", "content": prompt}])
                        ss.current_plan = response.choices[0].message.content
                        ss.sub = "viewplan"
                        plan_ok = True
                    except Exception as e:
                        st.error(f"Couldn't build the plan right now: {e}")
                if plan_ok:
                    st.rerun()

    elif sub == "viewplan":
        sub_header("📄 Today's plan")
        if ss.get("current_plan"):
            st.markdown(ss.current_plan)
            if st.button("Mark Today's Training Complete ✅", key="primary_cta"):
                log_training_complete()
                ss.sub = None
                st.toast("Logged! Great work today.")
                st.rerun()
        else:
            st.info("No plan yet — build one first.")

# ══════════════════════════════════════════════════════════════════════════
# PROGRESS
# ══════════════════════════════════════════════════════════════════════════
elif page == "Progress":
    sub = ss.sub
    if sub is None:
        page_title("📈 Progress", "Track your improvement. See results.")
        if not sessions:
            st.info("Analyze at least one match to start tracking progress.")
            hub_go("analyze_first", "🎥  Analyze a match", "Analyze")
        else:
            hub_btn("numbers", "📊  My numbers")
            hub_btn("compare", "📈  Compare two matches")

    elif sub == "numbers":
        sub_header("📊 My numbers")
        training_log = load_training_log()
        ratings = [normalize_report(s.get("ai_report"))["overall_rating"] for s in sessions]
        st.markdown(
            '<div class="chip-grid">'
            + chip("Matches Analyzed", len(sessions), "var(--cyan)")
            + chip("Trainings Completed", len(training_log), "var(--green)")
            + chip("First → Latest Rating", f"{ratings[0]:.1f} → {ratings[-1]:.1f}",
                   "var(--green)" if ratings[-1] >= ratings[0] else "var(--red)")
            + "</div>",
            unsafe_allow_html=True,
        )

    elif sub == "compare":
        sub_header("📈 Compare two matches")
        if len(sessions) < 2:
            st.info("Analyze a second match to unlock the comparison chart.")
        else:
            labels = [f"{s.get('opponent') or 'Match'} · {s.get('date', '')}" for s in sessions]
            idx_a, idx_b = st.select_slider(
                "Compare", options=list(range(len(sessions))),
                value=(0, len(sessions) - 1), format_func=lambda i: labels[i],
            )
            fig = compare_line_chart(normalize_report(sessions[idx_a].get("ai_report"))["radar"],
                                      normalize_report(sessions[idx_b].get("ai_report"))["radar"],
                                      labels[idx_a], labels[idx_b])
            fig.update_layout(height=300)
            st.plotly_chart(fig, config={"displayModeBar": False}, **CHART_STRETCH)

# ══════════════════════════════════════════════════════════════════════════
# DIET
# ══════════════════════════════════════════════════════════════════════════
elif page == "Diet":
    PLAYSTYLE_MULTIPLIER = {
        "Box-to-Box": 1.75, "Wing-Back": 1.75, "False Nine": 1.65, "Playmaker": 1.6,
        "Target Man": 1.6, "Sweeper": 1.55, "Ball-Winner": 1.7,
    }
    ss.setdefault("df_sex", "Male")
    ss.setdefault("df_age", 20)
    ss.setdefault("df_height", 175)
    ss.setdefault("df_weight", 70)
    ss.setdefault("df_style", list(PLAYSTYLE_MULTIPLIER)[0])
    ss.setdefault("df_goal", "Maintain")
    ss.setdefault("df_restr", "")
    sub = ss.sub

    if sub is None:
        page_title("🥗 Diet", "Fuel your body. Maximize your performance.")
        hub_btn("body", "🧍  Body stats")
        hub_btn("goal", "🎯  Goal & play-style")
        calc = st.button("Calculate My Diet Plan 🧮", key="primary_cta")
        if ss.get("diet_result"):
            hub_btn("result", "📊  My daily targets")
            hub_btn("meal", "🍽️  Sample meal plan")

        if calc:
            ss.pop("diet_plan", None)
            sex, age, height_cm, weight_kg = ss.df_sex, ss.df_age, ss.df_height, ss.df_weight
            goal = ss.df_goal if (ss.df_goal != "Cut weight" or age >= 18) else "Maintain"
            bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + (5 if sex == "Male" else -161)
            tdee = bmr * PLAYSTYLE_MULTIPLIER[ss.df_style]
            if goal == "Build muscle":
                tdee += 300
            elif goal == "Cut weight":
                tdee -= 300
            tdee = max(tdee, 1500 if sex == "Male" else 1200)  # never recommend a crash-diet calorie level
            protein_g = round(weight_kg * 2.0)
            fat_g = round((tdee * 0.27) / 9)
            carbs_g = round(max(tdee - (protein_g * 4) - (fat_g * 9), 0) / 4)
            ss.diet_result = dict(
                calories=round(tdee), protein=protein_g, carbs=carbs_g, fat=fat_g,
                fiber=round(tdee / 1000 * 14), water=round(weight_kg * 0.033 + 0.6, 1),
                restrictions=ss.df_restr,
            )
            ss.sub = "result"
            st.rerun()

    elif sub == "body":
        sub_header("🧍 Body stats")
        st.selectbox("Sex", ["Male", "Female"], key="df_sex")
        st.number_input("Age", 10, 60, key="df_age")
        st.number_input("Height (cm)", 120, 220, key="df_height")
        st.number_input("Weight (kg)", 30, 150, key="df_weight")

    elif sub == "goal":
        sub_header("🎯 Goal & play-style")
        goal_options = ["Maintain", "Build muscle"] + (["Cut weight"] if ss.df_age >= 18 else [])
        if ss.df_goal not in goal_options:
            ss.df_goal = "Maintain"
        st.selectbox("Play-style", list(PLAYSTYLE_MULTIPLIER.keys()), key="df_style")
        st.selectbox("Goal", goal_options, key="df_goal")
        if ss.df_age < 18:
            st.caption("Weight-cut targets aren't offered under 18. Growing athletes should check with a doctor or dietitian.")
        st.text_input("Dietary restrictions (optional)", key="df_restr", placeholder="e.g. No dairy, no shellfish")

    elif sub == "result":
        sub_header("📊 My daily targets")
        dr = ss.get("diet_result")
        if not dr:
            st.info("Tap Calculate on the Diet menu first.")
        else:
            st.markdown(
                '<div class="chip-grid">'
                + chip("Calories", f"{dr['calories']} kcal", "var(--red)")
                + chip("Protein", f"{dr['protein']} g", "var(--amber)")
                + chip("Carbs", f"{dr['carbs']} g", "var(--cyan)")
                + chip("Fats", f"{dr['fat']} g", "var(--purple)")
                + chip("Fiber", f"{dr['fiber']} g", "var(--green)")
                + chip("Water", f"{dr['water']} L", "var(--blue)")
                + "</div>",
                unsafe_allow_html=True,
            )
            hub_btn("meal_from_result", "🍽️  Sample meal plan", sub="meal")

    elif sub == "meal":
        sub_header("🍽️ Sample meal plan")
        dr = ss.get("diet_result")
        if not dr:
            st.info("Tap Calculate on the Diet menu first.")
        else:
            if ss.get("diet_plan"):
                st.markdown(ss.diet_plan)
            elif st.button("Generate Sample Meal Plan", key="primary_cta"):
                prompt = f"""You are a sports nutritionist for a competitive football player.
Daily targets: {dr['calories']} kcal, {dr['protein']}g protein, {dr['carbs']}g carbs, {dr['fat']}g fat, {dr['fiber']}g fiber.
Dietary restrictions: {dr['restrictions'] or 'none'}.
Suggest a simple one-day meal plan (breakfast, lunch, dinner, 1 snack) that roughly hits these targets. Keep it practical and under 220 words, using markdown."""
                meal_ok = False
                with st.spinner("Building your meal plan..."):
                    try:
                        response = client.chat.completions.create(model=MODEL, messages=[{"role": "user", "content": prompt}])
                        ss.diet_plan = response.choices[0].message.content
                        meal_ok = True
                    except Exception as e:
                        st.error(f"Couldn't build the meal plan right now: {e}")
                if meal_ok:
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════
# PROFILE
# ══════════════════════════════════════════════════════════════════════════
elif page == "Profile":
    sub = ss.sub
    if sub is None:
        page_title("Profile", "Your journey. Your stats. Your growth.")
        hub_btn("edit", "✏️  Edit profile")
        hub_btn("stats", "📊  My stats")
        hub_btn("storage", "💾  Videos & storage")
        hub_go("history", "📋  Match history", "History")
        try:
            authenticator.logout("Log out", "main", key="logout_btn")
        except TypeError:  # older streamlit-authenticator versions have no `key` argument
            authenticator.logout("Log out", "main")

    elif sub == "edit":
        sub_header("✏️ Edit profile")
        name = st.text_input("Name", value=profile.get("name", ""))
        jersey_number = st.text_input("Jersey number", value=str(profile.get("jersey_number", "")))
        position = st.selectbox("Position", POSITIONS, index=_position_index(profile.get("position")))
        if st.button("Save Profile", key="primary_cta"):
            profile.update({"name": name, "jersey_number": jersey_number, "position": position})
            save_profile(profile)
            ss.sub = None
            st.toast("Profile saved!")
            st.rerun()

    elif sub == "stats":
        sub_header("📊 My stats")
        training_log = load_training_log()
        ratings = [normalize_report(s.get("ai_report"))["overall_rating"] for s in sessions]
        goals_total = sum(s.get("goals", 0) for s in sessions)
        assists_total = sum(s.get("assists", 0) for s in sessions)
        st.markdown(
            '<div class="chip-grid">'
            + chip("Matches Uploaded", len(sessions), "var(--cyan)")
            + chip("Trainings Completed", len(training_log), "var(--green)")
            + chip("Best Performance", f"{max(ratings):.1f}" if ratings else "—", "var(--amber)")
            + "</div>"
            + '<div class="chip-grid">'
            + chip("Goals Scored", goals_total, "var(--cyan)")
            + chip("Assists", assists_total, "var(--cyan)")
            + chip("Average Rating", f"{(sum(ratings) / len(ratings)):.1f}" if ratings else "—", "var(--purple)")
            + "</div>",
            unsafe_allow_html=True,
        )
        if sessions:
            all_radars = [normalize_report(s.get("ai_report"))["radar"] for s in sessions]
            avg_radar = {k: round(sum(r.get(k, 0) for r in all_radars) / len(all_radars)) for k in RADAR_ORDER}
            buckets = {
                "Attacking": ["shooting", "off_ball_movement"], "Defending": ["defending"], "Fitness": ["fitness"],
                "Technical": ["dribbling", "ball_control"], "Tactical": ["passing", "vision"],
            }
            st.markdown("**All-time average**")
            for label, keys in buckets.items():
                val = round(sum(avg_radar[k] for k in keys) / len(keys))
                st.markdown(
                    f"<div style='margin-bottom:.4rem'><div class='stat-row'><span>{label}</span><span>{val}%</span></div>"
                    f"<div class='bar-track'><div class='bar-fill' style='width:{val}%;background:{score_color(val)}'></div></div></div>",
                    unsafe_allow_html=True,
                )

    elif sub == "storage":
        sub_header("💾 Videos & storage")
        files = os.listdir(UPLOAD_DIR) if os.path.isdir(UPLOAD_DIR) else []
        total_bytes = sum(os.path.getsize(os.path.join(UPLOAD_DIR, f)) for f in files)
        gb_used = total_bytes / (1024 ** 3)
        st.markdown(f"**{gb_used:.2f} GB** used across {len(files)} files")
        st.progress(min(gb_used / 10, 1.0))
        st.markdown("**Recent uploads**")
        video_sessions = [s for s in sessions if s.get("video_filename")]
        if not video_sessions:
            st.caption("No videos uploaded yet.")
        for s in reversed(video_sessions[-4:]):
            r = normalize_report(s.get("ai_report"))
            color = score_color(r["performance_score"])
            st.markdown(
                f"<div class='stat-row'><span>{_esc(s.get('opponent') or 'Match')} · {_esc(s.get('date', ''))}</span>"
                f"<span style='color:{color}'>{r['performance_score']}/100</span></div>",
                unsafe_allow_html=True,
            )

# ══════════════════════════════════════════════════════════════════════════
# HISTORY
# ══════════════════════════════════════════════════════════════════════════
elif page == "History":
    sub = ss.sub
    vs = ss.viewing_session
    if vs is not None and (not isinstance(vs, int) or not (0 <= vs < len(sessions))):
        ss.viewing_session = None
        vs = None

    if vs is None:
        page_title("📋 Match History", "Every match logged. Tap one to open it.")
        if not sessions:
            st.info("No sessions saved yet. Analyze a match first!")
            hub_go("analyze_first", "🎥  Analyze a match", "Analyze")
        else:
            newest_first = list(reversed(list(enumerate(sessions))))
            chunk, cur, pages = paginate(newest_first, 4, "history")
            for i, s in chunk:
                r = normalize_report(s.get("ai_report"))
                label = f"{s.get('opponent') or 'Match'}  ·  {s.get('date', '')}  ·  {r['performance_score']}/100"
                st.button(label, key=f"hub_match_{i}", on_click=_open_match, args=(i,))
            pager("history", cur, pages)
    else:
        s = sessions[vs]
        r = normalize_report(s.get("ai_report"))
        title = s.get("opponent") or "Match"
        if sub is None:
            sub_header(title, f"{s.get('date', '')} · {s.get('position', '')}", back=_close_match)
            if s.get("analyzed_from_video"):
                st.markdown("<span class='badge badge-cyan'>📹 Analyzed from video</span>", unsafe_allow_html=True)
            rcolor = score_color(r["overall_rating"], 10)
            st.markdown(
                f"<div style='text-align:center'><div style='color:var(--muted)'>OVERALL RATING</div>"
                f"<div style='font-family:Sora,sans-serif;font-weight:800;font-size:2.4rem;color:{rcolor}'>{r['overall_rating']:.1f}</div></div>",
                unsafe_allow_html=True,
            )
            hub_btn("findings", "🧠  AI findings")
            hub_btn("mstats", "📈  Match stats")
            hub_btn("breakdown", "📊  Detailed breakdown")
            hub_btn("mdrills", "📋  Recommended drills")
            vid_path = os.path.join(UPLOAD_DIR, s["video_filename"]) if s.get("video_filename") else None
            if vid_path and os.path.exists(vid_path):
                hub_btn("video", "🎥  Watch video")

        elif sub == "findings":
            sub_header("🧠 AI findings", title)
            st.write(f"**Strengths:** {r['strengths']}")
            st.write(f"**Improvement:** {r['improvement']}")
            st.write(f"**Tactical Insight:** {r['tactical_insight']}")
            st.write(f"**Key Moment:** {r['key_moment']}")
            st.markdown(f"<div class='quote-box'>⭐ {_esc(r['key_takeaway'])}</div>", unsafe_allow_html=True)

        elif sub == "mstats":
            sub_header("📈 Match stats", title)
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
            rows = "".join(f"<div class='stat-row'><span>{k}</span><span>{'—' if v is None else v}</span></div>" for k, v in stat_pairs)
            st.markdown(rows, unsafe_allow_html=True)

        elif sub == "breakdown":
            sub_header("📊 Detailed breakdown", title)
            st.plotly_chart(radar_chart(r["radar"], height=300), config={"displayModeBar": False}, **CHART_STRETCH)
            da = r["decision_analysis"]
            for label, pct, color in [("Good Decisions", da["good_pct"], "var(--green)"),
                                       ("Average Decisions", da["average_pct"], "var(--amber)"),
                                       ("Poor Decisions", da["poor_pct"], "var(--red)")]:
                st.markdown(
                    f"<div class='stat-row'><span>{label}</span><span>{pct}%</span></div>"
                    f"<div class='bar-track'><div class='bar-fill' style='width:{pct}%;background:{color}'></div></div>",
                    unsafe_allow_html=True,
                )

        elif sub == "mdrills":
            sub_header("📋 Recommended drills", title)
            for d in r.get("recommended_drills", []):
                st.write(f"• {d}")
            st.markdown(f"<div class='quote-box'>🗣️ {_esc(r['message'])}</div>", unsafe_allow_html=True)

        elif sub == "video":
            sub_header("🎥 Match video", title)
            vid_path = os.path.join(UPLOAD_DIR, s.get("video_filename") or "")
            if s.get("video_filename") and os.path.exists(vid_path):
                st.video(vid_path)
            else:
                st.info("This video is no longer stored.")

# ══════════════════════════════════════════════════════════════════════════
# CHAT
# ══════════════════════════════════════════════════════════════════════════
elif page == "Chat":
    sub = ss.sub
    if "chat_history" not in ss:
        ss.chat_history = []

    if sub == "earlier":
        sub_header("🕑 Earlier messages")
        pairs = list(reversed(ss.chat_history[:-2]))
        chunk, cur, pages = paginate(pairs, 4, "chat")
        for message in chunk:
            avatar = "🧑" if message["role"] == "user" else "⚽"
            st.chat_message(message["role"], avatar=avatar).write(message["content"])
        pager("chat", cur, pages)
    else:
        page_title("💬 Chat With Your Coach", "Tactics, advice, motivation — ask anything.")
        user_input = st.chat_input("Ask your coach something...")
        if user_input:
            ss.chat_history.append({"role": "user", "content": user_input})
            messages = [{"role": "system", "content": "You are an elite UEFA Pro License football coach. Answer all questions with specific, practical football advice. Be direct, motivating and knowledgeable. Keep answers under about 120 words unless the player asks for more detail."}]
            messages.extend(ss.chat_history[-20:])  # keep requests a sane size
            with st.spinner("Coach is thinking..."):
                try:
                    response = client.chat.completions.create(model=MODEL, messages=messages)
                    coach_reply = response.choices[0].message.content or ""
                except Exception as e:
                    coach_reply = ""
                    st.error(f"Your coach couldn't reply right now: {e}")
            if coach_reply:
                ss.chat_history.append({"role": "assistant", "content": coach_reply})
            else:
                ss.chat_history.pop()  # drop the unanswered question so history stays alternating

        for message in ss.chat_history[-2:]:
            avatar = "🧑" if message["role"] == "user" else "⚽"
            st.chat_message(message["role"], avatar=avatar).write(message["content"])
        if len(ss.chat_history) > 2:
            hub_btn("earlier", "🕑  Earlier messages")
