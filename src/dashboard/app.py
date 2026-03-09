# ruff: noqa: RUF001 SIM108 E501
"""
Reddit Review Analyzer — Compact Dashboard v3.

Two pages: Reviews (feed) + Analytics.
Grafana-style filters, no sidebar, compact layout.
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import base64
import html as html_mod
import io
import os
import re
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Reddit Scraper Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from src.analytics.patterns import get_ngrams, get_tfidf_keywords  # noqa: E402
from src.analytics.segments import SEGMENTS, get_segment_summary, segment_users  # noqa: E402
from src.apps import TRACKED_APPS, get_apps_by_niche  # noqa: E402
from src.models import AppConfig, AppNiche  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "reviews"
CSV_FILE = DATA_DIR / "all_reviews.csv"

# ── Assets: load from local file (dev) or fall back to GitHub raw URL ─
_ASSETS_DIR = Path(__file__).resolve().parent / "assets"
_GH_RAW = "https://raw.githubusercontent.com/Ksusha1128/reddit-scraper/main/src/dashboard/assets"

def _load_b64(filename: str) -> str:
    """Return a data-URI string for an image in the assets folder."""
    fp = _ASSETS_DIR / filename
    if not fp.exists():
        return ""
    suffix = fp.suffix.lower()
    mime = {"gif": "image/gif", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(suffix.lstrip("."), "image/png")
    encoded = base64.b64encode(fp.read_bytes()).decode()
    return f"data:{mime};base64,{encoded}"

def _asset_url(filename: str) -> str:
    """Return local base64 data-URI if the file exists, otherwise GitHub raw URL."""
    local = _load_b64(filename)
    if local:
        return local
    return f"{_GH_RAW}/{filename.replace(' ', '%20')}"

LOGO_URL = _asset_url("photo_2026-03-08 18.03.06.jpeg")
AUTH_GIF_URL = _asset_url("login_avatar.gif")

NICHE_RU: dict[AppNiche, str] = {
    AppNiche.RELATIONSHIPS: "AI Psychologist, Relationships",
    AppNiche.SMOKING: "Quit Smoking",
    AppNiche.PLANT_SCANNER: "Plant Scanner",
    AppNiche.CALORIE_TRACKER: "Calorie Tracker",
}
NICHE_FROM_RU: dict[str, AppNiche] = {v: k for k, v in NICHE_RU.items()}

PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#d8d9da", size=12, family="Inter, system-ui, sans-serif"),
    margin=dict(l=10, r=10, t=30, b=10),
)
C_GREEN = "#73bf69"
C_RED = "#f2495c"
C_YELLOW = "#ff9830"
C_BLUE = "#5794f2"
C_PURPLE = "#b877d9"
C_TEAL = "#36a2eb"

_CSS = """
<style>
:root {
    --g-bg-canvas: #111217;
    --g-bg-primary: #181b1f;
    --g-bg-secondary: #1e2028;
    --g-border: #2c3235;
    --g-border-hover: #464c54;
    --g-text-primary: #d8d9da;
    --g-text-secondary: #8e8e8e;
    --g-text-disabled: #6e6e6e;
    --g-blue: #5794f2;
    --g-green: #73bf69;
    --g-red: #f2495c;
    --g-orange: #ff9830;
    --g-purple: #b877d9;
}
.stApp, .main, [data-testid="stAppViewContainer"] {
    background-color: var(--g-bg-canvas) !important;
}
header[data-testid="stHeader"] {
    background-color: var(--g-bg-canvas) !important;
    border-bottom: 1px solid var(--g-border);
}
section[data-testid="stSidebar"] { display:none !important; }
[data-testid="stSidebarCollapsedControl"] { display:none !important; }
[data-testid="stSidebarNav"] { display:none !important; }
button[data-testid="stSidebarNavToggle"] { display:none !important; }
.css-1oe5cao { display:none !important; }
.block-container { padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; max-width: 100% !important; }
h1,h2,h3,h4,h5,h6 { color: var(--g-text-primary) !important; font-weight:500 !important; }
p, li, span, label, .stMarkdown, div[data-testid="stText"] { color: var(--g-text-primary); }
small, .stCaption, caption { color: var(--g-text-secondary) !important; }
div[data-baseweb="select"], div[data-baseweb="popover"] { background-color: var(--g-bg-secondary) !important; }
div[data-baseweb="select"] > div {
    background-color: var(--g-bg-secondary) !important;
    border-color: var(--g-border) !important;
    color: var(--g-text-primary) !important;
    min-height: 32px !important;
}
div[data-baseweb="select"] > div:hover { border-color: var(--g-border-hover) !important; }
ul[role="listbox"] { background-color: var(--g-bg-primary) !important; border: 1px solid var(--g-border) !important; }
li[role="option"] { color: var(--g-text-primary) !important; }
li[role="option"]:hover, li[role="option"][aria-selected="true"] { background-color: var(--g-bg-secondary) !important; }
span[data-baseweb="tag"] { background-color: #2c3235 !important; color: var(--g-text-primary) !important; }
div[data-testid="stWidgetLabel"] label {
    color: var(--g-text-secondary) !important; font-size: 0.72rem !important;
    text-transform: uppercase !important; letter-spacing: 0.5px !important; margin-bottom: 0 !important;
}
button[data-baseweb="tab"] {
    background-color: transparent !important; color: var(--g-text-secondary) !important;
    border: none !important; font-size: 0.82rem !important; padding: 6px 14px !important;
}
button[data-baseweb="tab"]:hover { color: var(--g-text-primary) !important; }
button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--g-text-primary) !important; border-bottom: 2px solid var(--g-blue) !important;
}
div[data-baseweb="tab-list"] { border-bottom: 1px solid var(--g-border) !important; gap: 0 !important; }
div[data-testid="stExpander"] {
    background-color: var(--g-bg-primary) !important; border: 1px solid var(--g-border) !important;
    border-radius: 4px !important; margin: 3px 0 !important;
}
div[data-testid="stExpander"] details { background-color: var(--g-bg-primary) !important; }
div[data-testid="stExpander"] details summary { background-color: var(--g-bg-primary) !important; }
div[data-testid="stExpander"] details summary p {
    font-weight: 500 !important; color: var(--g-text-primary) !important; font-size: 0.84rem !important;
}
button[kind="primary"], div.stDownloadButton > button {
    background-color: var(--g-blue) !important; color: #fff !important;
    border: none !important; border-radius: 4px !important; font-size: 0.8rem !important;
}
button[kind="secondary"], button:not([kind]) {
    background-color: var(--g-bg-secondary) !important;
    border: 1px solid var(--g-border) !important; color: var(--g-text-primary) !important;
}
input[type="text"], input[type="number"], textarea {
    background-color: var(--g-bg-secondary) !important;
    border: 1px solid var(--g-border) !important; color: var(--g-text-primary) !important;
}
input:focus, textarea:focus { border-color: var(--g-blue) !important; box-shadow: 0 0 0 1px var(--g-blue) !important; }
div[role="radiogroup"] label { color: var(--g-text-primary) !important; }
div[data-testid="stAlert"] {
    background-color: var(--g-bg-primary) !important;
    border: 1px solid var(--g-border) !important; color: var(--g-text-primary) !important;
}
div[data-testid="stMetric"] {
    background-color: var(--g-bg-primary) !important;
    border: 1px solid var(--g-border) !important; border-radius: 4px !important;
    padding: 8px 12px !important;
}
div[data-testid="stMetric"] label { font-size: 0.7rem !important; color: var(--g-text-secondary) !important; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 1.3rem !important; color: var(--g-text-primary) !important; }
.tag { display:inline-block; padding:1px 6px; margin:1px; border-radius:3px; font-size:.7rem; font-weight:500; white-space:nowrap; }
.tag-pos { background:#1a3a2a; color:#73bf69; border:1px solid #2f5a3a; }
.tag-neg { background:#3d1a1a; color:#f2495c; border:1px solid #5a2a2a; }
.tag-neu { background:#2d2a1a; color:#ff9830; border:1px solid #4a3a1a; }
.tag-post { background:#1a2535; color:#5794f2; border:1px solid #2a3a5a; }
.tag-comm { background:#2d1a35; color:#b877d9; border:1px solid #3a2a4a; }
.tag-sub { background:#1a2d2d; color:#36a2eb; border:1px solid #1b4a4a; }
.tag-app { background:#2d2a1a; color:#ff9830; border:1px solid #4a3a1a; }
.tag-niche { background:#2d1a2a; color:#b877d9; border:1px solid #3a2a4a; }
.tag-cat { background:#1a2a2d; color:#36a2eb; border:1px solid #1b3a4a; }
a.ulink { text-decoration:none; font-weight:500; color:var(--g-blue); font-size:.78rem; }
a.ulink:hover { text-decoration:underline; }
.rv-meta { font-size:.72rem; color:var(--g-text-secondary); margin:2px 0 4px 0; display:flex; align-items:center; gap:6px; flex-wrap:wrap; }
.rv-text { font-size:.84rem; color:var(--g-text-primary); line-height:1.55; margin:4px 0; }
.rv-link { font-size:.72rem; margin-top:4px; }
.cm-block { border-left:3px solid #4a4a5a; padding:8px 0 8px 14px; margin:4px 0 4px 8px; position:relative; }
.cm-block::before { content:''; position:absolute; left:-3px; top:0; bottom:0; width:3px; border-radius:2px; background:linear-gradient(180deg, #4a9eff22, #4a9eff08); }
.cm-author { font-weight:600; color:#58a6ff; font-size:.78rem; }
.cm-meta { font-size:.7rem; color:var(--g-text-secondary); margin-bottom:3px; display:flex; align-items:center; gap:5px; flex-wrap:wrap; }
.cm-text { font-size:.82rem; color:var(--g-text-primary); line-height:1.5; margin:2px 0; }
.cm-divider { border:none; border-top:1px solid var(--g-border); margin:8px 0 6px 0; }
.cm-header { color:var(--g-text-secondary); font-size:.76rem; font-weight:600; margin:6px 0 4px 0; padding-top:6px; border-top:1px solid var(--g-border); }
.stat-bar { display:flex; gap:0; margin:2px 0 6px 0; flex-wrap:wrap; align-items:center; padding:4px 0; border-bottom:1px solid var(--g-border); }
.stat-item { font-size:.76rem; color:var(--g-text-secondary); }
.stat-val { font-weight:600; margin-right:2px; font-family:monospace; }
.stat-sep { color:var(--g-border); margin:0 6px; font-size:.65rem; }
.pain-card { background:var(--g-bg-primary); border:1px solid var(--g-border); border-radius:4px; padding:8px 12px; margin:4px 0; }
.pain-quote {
    font-size:.8rem; color:var(--g-text-secondary); font-style:italic;
    border-left:3px solid var(--g-border); padding-left:8px; margin:4px 0; line-height:1.45;
}
.pain-apps { font-size:.72rem; color:var(--g-blue); margin-top:3px; }
mark { background-color: #3d3a1a; color: #ff9830; padding: 0 2px; border-radius: 2px; }
::-webkit-scrollbar { width:5px; height:5px; }
::-webkit-scrollbar-track { background:var(--g-bg-canvas); }
::-webkit-scrollbar-thumb { background:var(--g-border); border-radius:3px; }
[data-testid="stButton"] button[kind="secondary"] { min-height:0; padding:0.2rem 0.5rem; }
.filter-row-top [data-testid="column"] {
    min-width: 0 !important;
}
.filter-row-top div[data-baseweb="select"] > div,
.filter-row-top input {
    min-height: 30px !important;
}
.single-date-popover button[kind="secondary"] {
    white-space: nowrap !important;
}
.single-date-popover [data-testid="stPopover"] {
    width: 100%;
}
.appbar {
    display:flex;
    align-items:center;
    gap:12px;
    margin:0 0 8px 0;
    padding:0 0 10px 0;
    border-bottom:1px solid var(--g-border);
}
.appbar-logo {
    width:38px;
    height:38px;
    border-radius:10px;
    object-fit:cover;
    flex:0 0 auto;
}
.appbar-copy {
    display:flex;
    flex-direction:column;
    min-width:0;
}
.appbar-title {
    font-size:1rem;
    font-weight:700;
    line-height:1.1;
    color:var(--g-text-primary);
}
.appbar-subtitle {
    font-size:.68rem;
    letter-spacing:.08em;
    text-transform:uppercase;
    color:var(--g-text-secondary);
    margin-top:2px;
}
/* ── Login screen ─────────────────────────────────── */
.auth-card {
    max-width: 360px;
    margin: 28px auto 0;
    background: var(--g-bg-primary);
    border: 1px solid var(--g-border);
    border-radius: 16px;
    box-shadow: 0 4px 24px rgba(0,0,0,.4);
    padding: 28px 28px 22px;
    text-align: center;
}
.auth-avatar-wrap {
    width: 110px;
    height: 110px;
    border-radius: 50%;
    border: 3px solid var(--g-accent);
    margin: 0 auto 14px;
    box-shadow: 0 0 18px rgba(70,130,255,.3);
    overflow: hidden;
    position: relative;
}
.auth-avatar-wrap img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}
.auth-title {
    font-size: 1rem;
    font-weight: 700;
    color: var(--g-text-primary);
    margin-bottom: 2px;
}
.auth-subtitle {
    font-size: .72rem;
    color: var(--g-text-secondary);
    margin-bottom: 12px;
}
</style>
"""


def _get_auth_config() -> tuple[str | None, str | None]:
    username = os.getenv("APP_USERNAME", "parsernext")
    password = os.getenv("APP_PASSWORD", "parsernextteam")

    try:
        secrets_section = st.secrets.get("auth", {})
        username = secrets_section.get("username", username)
        password = secrets_section.get("password", password)
    except Exception:
        pass

    return username, password


def _check_auth() -> bool:
    expected_username, expected_password = _get_auth_config()
    if not expected_username or not expected_password:
        return True

    if st.session_state.get("auth_ok") is True:
        return True

    # ── Hide Streamlit chrome on login page ──
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown(
        """<style>
        header[data-testid="stHeader"],
        [data-testid="stSidebar"],
        [data-testid="stToolbar"],
        footer {display:none !important;}
        section[data-testid="stMain"] > div {padding-top:0 !important;}
        /* Compact inputs */
        .auth-inputs .stTextInput > div > div > input {
            background: var(--g-bg-base) !important;
            border: 1px solid var(--g-border) !important;
            color: var(--g-text-primary) !important;
            border-radius: 8px !important;
            padding: 8px 12px !important;
            font-size: .9rem !important;
        }
        .auth-inputs .stTextInput > label {
            color: var(--g-text-secondary) !important;
            font-size: .78rem !important;
            margin-bottom: 2px !important;
        }
        .auth-inputs .stTextInput {margin-bottom: 6px !important;}
        .auth-inputs .stButton > button {
            border-radius: 8px !important;
            font-size: .9rem !important;
            font-weight: 600 !important;
            padding: 8px 0 !important;
            margin-top: 4px !important;
        }
        </style>""",
        unsafe_allow_html=True,
    )

    # ── Single compact card at the top center ──
    col_l, col_c, col_r = st.columns([1.2, 1, 1.2])
    with col_c:
        st.markdown(
            f'''<div class="auth-card">
                <div class="auth-avatar-wrap"><img src="{AUTH_GIF_URL}" alt="" /></div>
                <div class="auth-title">Next · Reddit Parser</div>
            </div>''',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="auth-inputs">', unsafe_allow_html=True)
        username = st.text_input("Login", key="login_username", placeholder="login")
        password = st.text_input("Password", type="password", key="login_password", placeholder="password")
        submitted = st.button("Sign in", type="primary", use_container_width=True, key="login_submit")
        st.markdown('</div>', unsafe_allow_html=True)

    if submitted:
        if username == expected_username and password == expected_password:
            st.session_state.auth_ok = True
            st.rerun()
        else:
            with col_c:
                st.error("❌ Wrong login or password")

    return False

_REDDIT_FOOTER_RE = re.compile(
    r"\s*submitted by /u/\S+\s+to (?:r|u)/\S+\s*\[link\]\s*\[comments\]\s*$", re.IGNORECASE,
)

def _clean(text: str, title: str = "") -> str:
    t = str(text)
    t = _REDDIT_FOOTER_RE.sub("", t).rstrip()
    if title and t.startswith(title):
        t = t[len(title):].lstrip()
    if not t.strip() and title:
        t = title
    return t

@st.cache_data(ttl=3600)
def load_reviews() -> pd.DataFrame:
    if not CSV_FILE.exists():
        return pd.DataFrame()
    df = pd.read_csv(CSV_FILE, encoding="utf-8-sig")
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
    if "text" in df.columns and "source" in df.columns:
        mask = df["source"] == "post"
        if mask.any():
            titles = df.loc[mask, "title"].fillna("")
            texts = df.loc[mask, "text"].fillna("")
            df.loc[mask, "text"] = [_clean(t, tl) for t, tl in zip(texts, titles)]
    return df

def _infer_niche(text: str) -> str:
    """Infer niche from text content — every post MUST belong to a niche."""
    tl = str(text).lower()
    if any(w in tl for w in ("smoking", "nicotine", "cigarette", "vape", "quit smoking", "tobacco")):
        return NICHE_RU[AppNiche.SMOKING]
    if any(w in tl for w in ("plant", "garden", "leaf", "flower", "botanica", "tree", "mushroom", "succulent")):
        return NICHE_RU[AppNiche.PLANT_SCANNER]
    if any(w in tl for w in ("calorie", "nutrition", "macro", "diet", "food log", "weight loss", "fasting", "keto", "food track")):
        return NICHE_RU[AppNiche.CALORIE_TRACKER]
    # Default: relationships & mental health (largest niche)
    return NICHE_RU[AppNiche.RELATIONSHIPS]

# ── Normalize categories: all → Russian, no emoji ─────────────────────
_CAT_MAP: dict[str, str] = {
    # Old English categories
    "⭐ General Impression": "Пользовательский опыт",
    "📱 UI/UX & Design": "Интерфейс и дизайн",
    "🎯 Activities & Games": "Активность и вовлечённость",
    "🐛 Bugs & Technical Issues": "Баги и техпроблемы",
    "👫 Relationship Impact": "Пользовательский опыт",
    "💬 Communication": "Общение и коммуникация",
    "💰 Pricing & Subscription": "Цена и подписка",
    "📅 Planning & Calendar": "Намерение юзеров",
    "🔒 Privacy & Security": "Приватность и безопасность",
    "❤️ Intimacy": "Пользовательский опыт",
    "📝 Uncategorized": "Посты на тему",
    # Old Russian categories
    "⭐ Общее впечатление": "Пользовательский опыт",
    "⭐ UX / Интерфейс": "Интерфейс и дизайн",
    "❤️ Общее мнение": "Пользовательский опыт",
    "❤️ Близость / Интимность": "Пользовательский опыт",
    "🎯 Активности / Игры / Квизы": "Активность и вовлечённость",
    "🐛 Баги / Проблемы": "Баги и техпроблемы",
    "🐛 Баги / Технические проблемы": "Баги и техпроблемы",
    "👫 Влияние на отношения": "Пользовательский опыт",
    "� Общение / Коммуникация": "Общение и коммуникация",
    "💰 Цена / Подписка": "Цена и подписка",
    "📊 Функции": "Функции",
    "📋 Без категории": "Посты на тему",
    "� Без категории": "Посты на тему",
    # New enum values (direct pass-through)
    "Баги и техпроблемы": "Баги и техпроблемы",
    "Активность и вовлечённость": "Активность и вовлечённость",
    "Интерфейс и дизайн": "Интерфейс и дизайн",
    "Общение и коммуникация": "Общение и коммуникация",
    "Функции": "Функции",
    "Цена и подписка": "Цена и подписка",
    "Разработчики": "Разработчики",
    "Пользовательский опыт": "Пользовательский опыт",
    "Потребности": "Потребности",
    "Приватность и безопасность": "Приватность и безопасность",
    "Посты на тему": "Посты на тему",
    "Намерение юзеров": "Намерение юзеров",
    "Без категории": "Посты на тему",
}

# ── Strict text-based re-categorizer ──────────────────────────────────────
_STRICT_CAT_RULES: list[tuple[str, re.Pattern]] = [
    ("Баги и техпроблемы", re.compile(
        r"\b(?:bug(?:s|gy)?|crash(?:es|ed|ing)?|error|freeze[sd]?|lag(?:s|gy)?|glitch(?:es|y)?|"
        r"broken|not working|stopped working|doesn.t work|won.t (?:open|load|start)|"
        r"update broke|sync (?:issue|problem|error)|can.t (?:login|log in|sign in|connect)|"
        r"black screen|force close|data loss|battery drain)\b", re.I)),
    ("Цена и подписка", re.compile(
        r"\b(?:(?:too )?expensive|overpriced|subscription|paywall|premium|"
        r"free (?:version|tier|plan|trial)|(?:not )?worth (?:the )?(?:price|money|paying)|"
        r"(?:in-app |in app )?purchas|refund|billing|charged?|(?:cancel|renew)\w* (?:my |the )?(?:sub|plan|membership)|"
        r"rip\s*off|price (?:increase|hike|went up)|hidden (?:cost|fee)|trial (?:ended|expired))\b", re.I)),
    ("Интерфейс и дизайн", re.compile(
        r"\b(?:(?:the |this )?(?:ui|ux|interface|layout|design) (?:is|was|looks?|feels?|needs?)|"
        r"(?:ugly|beautiful|clean|cluttered|intuitive|confusing|sleek|modern|outdated) (?:ui|ux|interface|design|layout|app)|"
        r"dark mode|font size|navigation (?:is|sucks|confusing)|"
        r"button(?:s)? (?:too |are )?(?:small|big|hidden|confusing)|"
        r"(?:hard|easy|difficult|simple) to (?:use|navigate|find)|user.?friendly)\b", re.I)),
    ("Функции", re.compile(
        r"\b(?:(?:this |the )?(?:feature|function|option|tool) (?:is|was|should|needs?|doesn.t)|"
        r"(?:wish|want|need|hope) (?:it |they |the app )?(?:had|would|could|has|will) (?:add|support|include|have)|"
        r"(?:add|added|adding|support|include) (?:a |an )?(?:feature|option|function|mode)|"
        r"(?:can|could)(?:n.t|not) (?:do|find|use|access|export|import|customize|track)|"
        r"missing (?:feature|option|function|setting)|"
        r"should (?:add|have|support|include|allow))\b", re.I)),
    ("Приватность и безопасность", re.compile(
        r"\b(?:(?:data |user )?privacy|(?:data |personal )?(?:collect|harvest|sell|shar)(?:s|ing|ed)?|"
        r"(?:too many |unnecessary )?permission|account (?:hack|breach|stolen|compromised)|"
        r"(?:encrypt|secure|safety|two.?factor|2fa)|"
        r"(?:creepy|sketchy|suspicious|shady) (?:app|permission|practice))\b", re.I)),
    ("Пользовательский опыт", re.compile(
        r"\b(?:(?:this |the )?app (?:is|was|has been) (?:amazing|great|terrible|awful|incredible|life.?changing|helpful|useless|garbage|trash|worst|best)|"
        r"(?:love|hate|enjoy|recommend|regret|adore) (?:this |the )?app|"
        r"game.?changer|life.?saver|(?:highly |would |definitely )?recommend|"
        r"(?:saved|changed|ruined|improved|transformed) (?:my |our )|"
        r"(?:uninstall|delet)(?:ed|ing) (?:the |this )?app|"
        r"(?:switched|moving|moved) (?:to|from|away))\b", re.I)),
    ("Потребности", re.compile(
        r"\b(?:(?:looking|searching|need|want) (?:for )?(?:a |an )?(?:app|tool|alternative|replacement|something)|"
        r"(?:any(?:one)? |does anyone )?(?:know|recommend|suggest) (?:a |an )?(?:good |better )?(?:app|tool|alternative)|"
        r"(?:is there |are there )(?:a |any )?(?:app|tool|alternative)(?:s)?|"
        r"what (?:app|tool) (?:do you|should i|can i))\b", re.I)),
]

def _strict_categorize(text: str) -> str:
    """Categorize text strictly — only if pattern matches in app-relevant context."""
    text_s = str(text)
    for cat_name, pattern in _STRICT_CAT_RULES:
        if pattern.search(text_s):
            return cat_name
    return "Посты на тему"

def _normalize_categories(df: pd.DataFrame) -> pd.DataFrame:
    """Re-categorize all rows using strict text-based rules."""
    if "text" in df.columns:
        df["primary_category"] = df["text"].fillna("").apply(_strict_categorize)
    return df

def _add_niche(df: pd.DataFrame) -> pd.DataFrame:
    niche_map = {a.name: NICHE_RU[a.niche] for a in TRACKED_APPS}
    df = df.copy()
    # Merge "General / Общее" → "General"
    df["app_name"] = df["app_name"].replace({"General / Общее": "General", "General/ Общее": "General"})
    df["niche_ru"] = df["app_name"].map(niche_map)
    mask = df["niche_ru"].isna()
    if mask.any():
        df.loc[mask, "niche_ru"] = df.loc[mask, "text"].apply(_infer_niche)
    # Flag multi-app posts (same permalink assigned to multiple apps)
    if "permalink" in df.columns:
        apps_per_link = df.groupby("permalink")["app_name"].transform("nunique")
        df["_is_multi_app"] = apps_per_link > 1
    else:
        df["_is_multi_app"] = False
    # Normalize categories
    df = _normalize_categories(df)
    return df

def _post_base(url: str) -> str:
    m = re.search(r"(/r/\w+/comments/\w+)", str(url))
    return m.group(1) if m else str(url)

def _esc(t: str) -> str:
    return html_mod.escape(str(t))

def _highlight(text: str, q: str) -> str:
    if not q:
        return _esc(text)
    escaped = _esc(text)
    return re.compile(re.escape(_esc(q)), re.IGNORECASE).sub(lambda m: f"<mark>{m.group()}</mark>", escaped)

_SENT = {"positive": ("😊 positive", "tag-pos"), "negative": ("😞 negative", "tag-neg"), "neutral": ("😐 neutral", "tag-neu")}
def _pill(css: str, txt: str) -> str:
    return f'<span class="tag {css}">{txt}</span>'
def _pill_sent(label: str) -> str:
    t, c = _SENT.get(label, ("😐 ?", "tag-neu"))
    return _pill(c, t)
def _pill_app(name: str) -> str:
    return _pill("tag-app", f"#{name}")
def _pill_niche(niche: str) -> str:
    return _pill("tag-niche", niche)
def _pill_cat(cat: str) -> str:
    return _pill("tag-cat", cat)
def _user_link(author: str) -> str:
    if not author or author == "[deleted]":
        return '<span style="color:var(--g-text-disabled)">[deleted]</span>'
    return f'<a href="https://reddit.com/u/{author}" target="_blank" class="ulink">u/{author}</a>'
def _stat_val(value: str, label: str, color: str = "#d8d9da") -> str:
    return f'<span class="stat-item"><span class="stat-val" style="color:{color}">{value}</span> {label}</span>'
def _stat_line(items: list[str]) -> None:
    st.markdown('<div class="stat-bar">' + '<span class="stat-sep">·</span>'.join(items) + '</div>', unsafe_allow_html=True)

def _to_excel(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    export = df.copy()
    cols = [c for c in ["niche_ru", "app_name", "source", "author", "title", "text", "subreddit", "permalink", "date", "sentiment_label", "sentiment_score", "categories", "primary_category"] if c in export.columns]
    export = export[cols]
    rename = {"niche_ru": "Niche", "app_name": "App", "source": "Type", "author": "Author", "title": "Title", "text": "Text", "subreddit": "Subreddit", "permalink": "Link", "date": "Date", "sentiment_label": "Sentiment", "sentiment_score": "Score", "categories": "Categories", "primary_category": "Category"}
    export = export.rename(columns=rename)
    if "Date" in export.columns:
        export["Date"] = pd.to_datetime(export["Date"], errors="coerce").dt.tz_localize(None)
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        export.to_excel(w, sheet_name="Reviews", index=False)
    return buf.getvalue()

def _to_csv(df: pd.DataFrame) -> bytes:
    cols = [c for c in ["niche_ru", "app_name", "source", "author", "title", "text", "subreddit", "permalink", "date", "sentiment_label"] if c in df.columns]
    return df[cols].to_csv(index=False).encode("utf-8-sig")

# ═══════════════════════════════════════════════════════════════════════════
#  GLOBAL FILTERS — compact Grafana-style
# ═══════════════════════════════════════════════════════════════════════════

def _global_filters(df: pd.DataFrame) -> tuple[pd.DataFrame, str, str]:
    all_niches = sorted(df["niche_ru"].unique().tolist())
    all_apps = sorted(df["app_name"].unique().tolist())
    min_date = df["date"].min().date() if "date" in df.columns and not df["date"].isna().all() else datetime(2020, 1, 1).date()
    max_date = df["date"].max().date() if "date" in df.columns and not df["date"].isna().all() else datetime.now().date()
    all_categories: list[str] = []
    if "primary_category" in df.columns:
        all_categories = sorted(df["primary_category"].dropna().unique().tolist())

    # Row 1: niche, app, type, sentiment, search
    st.markdown('<div class="filter-row-top">', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns([1.35, 1.6, 0.72, 0.72, 1.35])
    with c1:
        sel_niches = st.multiselect("NICHE", options=all_niches, default=[], placeholder="All niches", key="f_niche")
    with c2:
        pool = sorted(df.loc[df["niche_ru"].isin(sel_niches), "app_name"].unique().tolist()) if sel_niches else all_apps
        sel_apps = st.multiselect("APP", options=pool, default=[], placeholder="All", key="f_app")
    with c3:
        src_filter = st.selectbox("TYPE", ["All", "📄 Posts", "💬 Comments"], key="f_src")
    with c4:
        sent_filter = st.selectbox("SENTIMENT", ["All", "😊 +", "😞 −", "😐 ~"], key="f_sent")
    with c5:
        search_q = st.text_input("🔍 SEARCH", value="", key="f_search", placeholder="Keyword…")
    st.markdown('</div>', unsafe_allow_html=True)

    # Row 2: category + date
    r1, r2, _ = st.columns([2.5, 2.2, 5.3])
    with r1:
        sel_cats = st.multiselect("CATEGORY", options=all_categories, default=[], placeholder="Все категории", key="f_cat")

    with r2:
        if "f_date_start" not in st.session_state:
            st.session_state.f_date_start = min_date
            st.session_state.f_date_end = max_date

        ds = st.session_state.f_date_start
        de = st.session_state.f_date_end

        st.markdown('<p style="font-size:.75rem;font-weight:600;color:var(--g-text-secondary);margin:0 0 4px 0;text-transform:uppercase;letter-spacing:.06em">DATE</p>', unsafe_allow_html=True)
        with st.popover(f"{ds.strftime('%d.%m.%Y')} — {de.strftime('%d.%m.%Y')}"):
            st.markdown("**From — To**")
            dc1, dc2 = st.columns(2)
            with dc1:
                d_start = st.date_input("from", value=ds, min_value=min_date, max_value=max_date, key="f_ds", label_visibility="collapsed")
            with dc2:
                d_end = st.date_input("to", value=de, min_value=min_date, max_value=max_date, key="f_de", label_visibility="collapsed")
            if d_start != ds or d_end != de:
                st.session_state.f_date_start = d_start
                st.session_state.f_date_end = d_end
                st.rerun()
            st.markdown("---")
            if st.button("3 months", key="dp_3m", use_container_width=True):
                st.session_state.f_date_start = max_date - timedelta(days=90)
                st.session_state.f_date_end = max_date
                st.rerun()
            if st.button("6 months", key="dp_6m", use_container_width=True):
                st.session_state.f_date_start = max_date - timedelta(days=180)
                st.session_state.f_date_end = max_date
                st.rerun()
            if st.button("1 year", key="dp_1y", use_container_width=True):
                st.session_state.f_date_start = max_date - timedelta(days=365)
                st.session_state.f_date_end = max_date
                st.rerun()
            if st.button("All time", key="dp_all", use_container_width=True):
                st.session_state.f_date_start = min_date
                st.session_state.f_date_end = max_date
                st.rerun()

    date_start = st.session_state.f_date_start
    date_end = st.session_state.f_date_end

    # Apply all filters
    out = df.copy()
    if sel_niches:
        out = out[out["niche_ru"].isin(sel_niches)]
    if sel_apps:
        out = out[out["app_name"].isin(sel_apps)]
    if sel_cats and "primary_category" in out.columns:
        out = out[out["primary_category"].isin(sel_cats)]
    sent_map = {"😊 +": "positive", "😞 −": "negative", "😐 ~": "neutral"}
    if sent_filter in sent_map and "sentiment_label" in out.columns:
        out = out[out["sentiment_label"] == sent_map[sent_filter]]
    # NOTE: source filter (Posts/Comments) is NOT applied here —
    # page_reviews handles it so comments always appear with their posts.
    if "date" in out.columns:
        out = out[out["date"] >= pd.Timestamp(date_start, tz="UTC")]
        out = out[out["date"] <= pd.Timestamp(date_end, tz="UTC") + pd.Timedelta(days=1)]
    if search_q and "text" in out.columns:
        mask = out["text"].fillna("").str.contains(search_q, case=False, na=False)
        if "title" in out.columns:
            mask = mask | out["title"].fillna("").str.contains(search_q, case=False, na=False)
        out = out[mask]
    if "date" in out.columns:
        out = out.sort_values("date", ascending=False, na_position="last")
    return out, search_q, src_filter

# ═══════════════════════════════════════════════════════════════════════════
#  PAGE 1: REVIEWS FEED
# ═══════════════════════════════════════════════════════════════════════════

def page_reviews(filtered: pd.DataFrame, search_q: str, full_df: pd.DataFrame | None = None, src_filter: str = "All") -> None:
    if filtered.empty:
        st.info("Нет отзывов по выбранным фильтрам.")
        return

    has_src = "source" in filtered.columns

    # ── Build comment groups from FULL df so comments always appear with posts ──
    _all = full_df if full_df is not None else filtered
    if has_src and "source" in _all.columns:
        all_comments = _all[_all["source"] == "comment"].copy()
    else:
        all_comments = pd.DataFrame()

    comment_groups: dict[str, pd.DataFrame] = {}
    if not all_comments.empty:
        all_comments["_base"] = all_comments["permalink"].fillna("").apply(_post_base)
        for base, grp in all_comments.groupby("_base"):
            comment_groups[base] = grp

    # ── Posts from filtered data ──
    if has_src:
        posts = filtered[filtered["source"] == "post"].copy()
    else:
        posts = filtered.copy()

    if not posts.empty:
        posts["_base"] = posts["permalink"].fillna("").apply(_post_base)
        posts["_n_comments"] = posts["_base"].map(lambda b: len(comment_groups.get(b, [])))
    else:
        posts = posts.copy()
        posts["_n_comments"] = 0

    # ── Apply TYPE filter on posts level ──
    if src_filter == "💬 Comments" and not posts.empty:
        # Show only posts that HAVE comments
        posts = posts[posts["_n_comments"] > 0]

    # Count comments that belong to displayed posts
    post_bases = set(posts["_base"].tolist()) if "_base" in posts.columns and not posts.empty else set()
    n_comments_shown = sum(len(comment_groups.get(b, [])) for b in post_bases)

    st.markdown(
        f'<div style="font-size:.76rem;color:var(--g-text-secondary);margin:2px 0 6px 0">'
        f'📄 {len(posts)} постов · 💬 {n_comments_shown} комментариев · {len(posts) + n_comments_shown} всего</div>',
        unsafe_allow_html=True,
    )

    page_size = 25
    total_items = len(posts)
    total_pages = max(1, (total_items - 1) // page_size + 1)
    if "rv_page" not in st.session_state:
        st.session_state.rv_page = 1
    if st.session_state.rv_page > total_pages:
        st.session_state.rv_page = total_pages
    page = st.session_state.rv_page

    sort_opts = ["Newest", "Oldest", "Comments ↓", "Negative", "Positive"]
    sort_map = {"Newest": ("date", False), "Oldest": ("date", True), "Comments ↓": ("_n_comments", False), "Negative": ("sentiment_score", True), "Positive": ("sentiment_score", False)}

    pc1, pc2, pc3, pc4, pc5 = st.columns([1.5, 0.3, 0.5, 0.3, 7.4])
    with pc1:
        sort_label = st.selectbox("sort", sort_opts, index=0, key="rv_sort", label_visibility="collapsed")
    with pc2:
        if st.button("◀", disabled=(page <= 1), key="rv_prev"):
            st.session_state.rv_page = page - 1
            st.rerun()
    with pc3:
        st.markdown(f'<div style="text-align:center;padding:5px 0;font-size:.76rem;color:var(--g-text-secondary)">{page}/{total_pages}</div>', unsafe_allow_html=True)
    with pc4:
        if st.button("▶", disabled=(page >= total_pages), key="rv_next"):
            st.session_state.rv_page = page + 1
            st.rerun()

    sort_col, sort_asc = sort_map[sort_label]
    if not posts.empty:
        posts = posts.sort_values(sort_col, ascending=sort_asc, na_position="last")

    start = (page - 1) * page_size
    page_posts = posts.iloc[start:start + page_size]

    for _, pr in page_posts.iterrows():
        _render_card(pr, comment_groups, search_q)

    if total_pages > 1:
        _, bp, bi, bn, _ = st.columns([5, 0.3, 0.5, 0.3, 3.9])
        with bp:
            if st.button("◀", disabled=(page <= 1), key="rv_prev_b"):
                st.session_state.rv_page = page - 1
                st.rerun()
        with bi:
            st.markdown(f'<div style="text-align:center;padding:5px 0;font-size:.76rem;color:var(--g-text-secondary)">{page}/{total_pages}</div>', unsafe_allow_html=True)
        with bn:
            if st.button("▶", disabled=(page >= total_pages), key="rv_next_b"):
                st.session_state.rv_page = page + 1
                st.rerun()

    if not all_comments.empty and not posts.empty:
        orph = all_comments[~all_comments["_base"].isin(post_bases)]
        if len(orph) > 0:
            with st.expander(f"💬 {len(orph)} комментариев без привязки к посту"):
                for _, row in orph.head(20).iterrows():
                    _render_comment(row, search_q)


def _render_card(pr: pd.Series, comment_groups: dict, search_q: str) -> None:
    title = str(pr.get("title", ""))[:140] or "(без заголовка)"
    author = pr.get("author", "?")
    sent = pr.get("sentiment_label", "")
    date_s = pr["date"].strftime("%d.%m.%Y") if pd.notna(pr.get("date")) else ""
    link = pr.get("permalink", "")
    app = pr.get("app_name", "")
    niche = pr.get("niche_ru", "")
    text = _clean(str(pr.get("text", "")), title)
    primary_cat = str(pr.get("primary_category", ""))

    base = _post_base(link) if link else ""
    post_comments = comment_groups.get(base, pd.DataFrame())
    n_comm = len(post_comments)

    comm_part = f"  ·  💬 {n_comm}" if n_comm > 0 else ""
    label = f"📄 {title[:90]}  ·  {app}  ·  {date_s}{comm_part}"
    with st.expander(label, expanded=True):
        pills = _pill("tag-post", "📄 пост")
        if app:
            pills += " " + _pill_app(app)
        pills += " " + _pill_sent(sent)
        if niche:
            pills += " " + _pill_niche(niche)
        if primary_cat and primary_cat != "nan":
            pills += " " + _pill_cat(primary_cat.strip())
        if n_comm > 0:
            pills += " " + _pill("tag-comm", f"💬 {n_comm}")

        st.markdown(f'<div class="rv-meta">{_user_link(author)} · {date_s} · {pills}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="rv-text">{_highlight(text[:1500], search_q)}</div>', unsafe_allow_html=True)
        if link:
            st.markdown(f'<div class="rv-link"><a href="{link}" target="_blank" class="ulink">🔗 Reddit</a></div>', unsafe_allow_html=True)

        # ── Comments inside card ──
        if n_comm > 0:
            parts = [f'<div class="cm-header">💬 {n_comm} комментариев</div>']
            for _, cr in post_comments.iterrows():
                parts.append(_render_comment_html(cr, search_q))
            st.markdown("\n".join(parts), unsafe_allow_html=True)


def _render_comment_html(cr: pd.Series, search_q: str) -> str:
    """Return one comment as HTML string (no st.markdown call)."""
    c_author = cr.get("author", "?")
    c_text = str(cr.get("text", ""))[:600]
    c_sent = cr.get("sentiment_label", "")
    c_date = cr["date"].strftime("%d.%m.%Y") if pd.notna(cr.get("date")) else ""
    c_link = cr.get("permalink", "")
    c_app = cr.get("app_name", "")
    c_cat = str(cr.get("primary_category", ""))
    link_html = f' · <a href="{c_link}" target="_blank" class="ulink">🔗</a>' if c_link else ""
    cat_html = f" {_pill_cat(c_cat.strip())}" if c_cat and c_cat != "nan" else ""
    return (
        f'<div class="cm-block">'
        f'<div class="cm-meta">'
        f'<span class="cm-author">u/{_esc(str(c_author))}</span> '
        f'{c_date} {_pill_sent(c_sent)} {_pill_app(c_app)}{cat_html}{link_html}'
        f'</div>'
        f'<div class="cm-text">{_highlight(c_text, search_q)}</div>'
        f'</div>'
    )


def _render_comment(cr: pd.Series, search_q: str) -> None:
    """Render a single comment via st.markdown (for orphan comments)."""
    st.markdown(_render_comment_html(cr, search_q), unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
#  PAGE 2: ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════

def _render_review_row(row: pd.Series, idx: int) -> str:
    """Render one review row as HTML with Reddit link, sentiment pill, app tag."""
    text = str(row.get("text", ""))[:300]
    author = row.get("author", "?")
    sent = row.get("sentiment_label", "")
    date_s = row["date"].strftime("%d.%m.%Y") if pd.notna(row.get("date")) else ""
    link = row.get("permalink", "")
    app = row.get("app_name", "")
    src = row.get("source", "post")
    icon = "💬" if src == "comment" else "📄"
    link_html = f' <a href="{link}" target="_blank" class="ulink">🔗 Reddit</a>' if link else ""
    return (
        f'<div class="cm-block">'
        f'<div class="cm-meta">{icon} <span class="cm-author">u/{_esc(str(author))}</span> '
        f'{date_s} {_pill_sent(sent)} {_pill_app(app)}{link_html}</div>'
        f'<div class="cm-text">{_esc(text)}</div>'
        f'</div>'
    )


def _analytics_expander_block(title: str, rows_df: pd.DataFrame, key_prefix: str, max_show: int = 10) -> None:
    """Render an expandable block with review rows + Reddit links."""
    n = len(rows_df)
    with st.expander(f"{title} — {n} posts", expanded=False):
        show = rows_df.head(max_show)
        parts = []
        for idx, (_, row) in enumerate(show.iterrows()):
            parts.append(_render_review_row(row, idx))
        if n > max_show:
            parts.append(f'<div style="color:var(--g-text-secondary);font-size:.8rem;padding:8px 0">...and {n - max_show} more</div>')
        st.markdown("\n".join(parts), unsafe_allow_html=True)


def page_analytics(filtered: pd.DataFrame) -> None:
    if filtered.empty:
        st.info("No data for analytics.")
        return

    # Deduplicate: same permalink+text+author = real duplicate, but keep different comments under same post
    dedup_cols = [c for c in ["permalink", "text", "author"] if c in filtered.columns]
    deduped = filtered.drop_duplicates(subset=dedup_cols) if dedup_cols else filtered

    # ── Split: about apps vs niche discussions ──
    _APP_SIGNAL = re.compile(
        r"\b(?:app|application|downloaded|installed|uninstalled|subscription|premium|"
        r"free version|interface|ui|ux|notification|feature|update|bug|crash|glitch|"
        r"tracking|tracker|log|sync|dark mode|widget|tutorial|onboarding)\b", re.I
    )
    # Build set of known app names for matching
    _known_apps_lower = set()
    _real_mask = ~deduped["app_name"].str.startswith("[", na=False)
    for a in deduped.loc[_real_mask, "app_name"].unique():
        _known_apps_lower.add(str(a).lower())
        # also add without special chars: "Lose It!" -> "lose it"
        _known_apps_lower.add(re.sub(r"[^a-z0-9 ]", "", str(a).lower()).strip())

    def _is_about_app(row):
        text_lower = str(row.get("text", "")).lower()
        # 1) text mentions a known app name
        for app_l in _known_apps_lower:
            if len(app_l) > 2 and app_l in text_lower:
                return True
        # 2) text mentions generic app-related words
        if _APP_SIGNAL.search(text_lower):
            return True
        return False

    deduped = deduped.copy()
    deduped["_about_app"] = deduped.apply(_is_about_app, axis=1)
    app_data = deduped[deduped["_about_app"]]     # posts/comments about apps
    niche_data = deduped[~deduped["_about_app"]]   # general niche discussions

    total = len(deduped)
    texts = deduped["text"].fillna("").tolist()
    apps = deduped["app_name"].fillna("").tolist()

    n_pos = len(deduped[deduped["sentiment_label"] == "positive"]) if "sentiment_label" in deduped.columns else 0
    n_neg = len(deduped[deduped["sentiment_label"] == "negative"]) if "sentiment_label" in deduped.columns else 0
    n_neu = total - n_pos - n_neg
    n_apps = filtered["app_name"].nunique()
    n_authors = deduped["author"].nunique() if "author" in deduped.columns else 0
    n_posts = len(deduped[deduped["source"] == "post"]) if "source" in deduped.columns else total
    n_comments = len(deduped[deduped["source"] == "comment"]) if "source" in deduped.columns else 0

    k1, k2, k3, k4, k5, k6, k7, k8 = st.columns(8)
    k1.metric("Total", total)
    k2.metric("About Apps", len(app_data))
    k3.metric("Niche Talk", len(niche_data))
    k4.metric("Posts", n_posts)
    k5.metric("Comments", n_comments)
    k6.metric("Positive", n_pos)
    k7.metric("Negative", n_neg)
    k8.metric("Apps", n_apps)

    st.markdown("---")

    # ── Sentiment by app ──
    st.markdown("##### Sentiment by App")
    if "sentiment_label" in deduped.columns:
        _no_gen = deduped[~deduped["app_name"].isin(["General", "General / Общее"])]
        app_sent = _no_gen.groupby("app_name").agg(sent=("sentiment_score", "mean"), cnt=("app_name", "size")).reset_index()
        app_sent = app_sent[app_sent["cnt"] >= 2].sort_values("sent")
        if len(app_sent) > 15:
            app_sent = pd.concat([app_sent.head(7), app_sent.tail(7)]).drop_duplicates()
        if not app_sent.empty:
            colors = [C_GREEN if v > 0.05 else (C_RED if v < -0.05 else C_YELLOW) for v in app_sent["sent"]]
            fig = go.Figure(go.Bar(
                x=app_sent["sent"].values, y=app_sent["app_name"].values,
                orientation="h", marker_color=colors,
                text=[f"{v:+.2f} ({c})" for v, c in zip(app_sent["sent"], app_sent["cnt"])],
                textposition="outside", textfont=dict(size=11, color="#8b949e"),
            ))
            fig.update_layout(**PLOTLY_LAYOUT, height=max(len(app_sent) * 28, 200), yaxis=dict(autorange="reversed"), xaxis_title="Avg sentiment")
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ── What People Like / Complaints ──
    st.markdown("##### What People Like / Complaints")

    # Use app_data (already filtered to posts about apps)

    # --- Positive: what people LIKE about apps, by theme ---
    # Keywords are PHRASES to avoid false positives
    _LIKE_CATEGORIES: dict[str, list[re.Pattern]] = {
        "Удобство и простота": [
            re.compile(r"\b(?:easy to use|user.friendly|simple to|intuitive|clean interface|smooth experience|well designed app)\b", re.I),
        ],
        "Функциональность": [
            re.compile(r"\b(?:great feature|useful feature|love the (?:feature|tracking|log)|accurate (?:track|data|count|scan)|good (?:tracking|logging|scanner))\b", re.I),
        ],
        "Мотивация и поддержка": [
            re.compile(r"\b(?:motivat(?:es|ed|ing)|streak|milestone|achievement|badge|reward|community|support(?:ive|ing))\b", re.I),
        ],
        "Результат и эффект": [
            re.compile(r"\b(?:helped me|saved my|changed my|life.?changer|game.?changer|works great|actually work|really help)\b", re.I),
        ],
        "Цена — доволен": [
            re.compile(r"\b(?:worth (?:the|every) (?:money|penny|cent|price)|good value|affordable|free (?:version|app) (?:is|works)|reasonable price)\b", re.I),
        ],
        "Дизайн и UI": [
            re.compile(r"\b(?:beautiful (?:app|design|ui|interface)|gorgeous|nice design|great ui|looks great|love the (?:design|look|aesthetic|theme))\b", re.I),
        ],
    }
    # --- Negative: complaints about apps, by theme ---
    _COMPLAINT_CATEGORIES: dict[str, list[re.Pattern]] = {
        "Цена и подписка": [
            re.compile(r"\b(?:(?:too )?expensive|overpriced|paywall|pay.?wall|not worth (?:the|it)|money grab|rip.?off|subscription (?:is|costs?|price)|premium (?:only|is)|(?:raised|increased) (?:the )?price|in.app purchase)\b", re.I),
        ],
        "Баги и техпроблемы": [
            re.compile(r"\b(?:crash(?:es|ed|ing)|bug(?:gy|s)?|glitch(?:y|es)?|freez(?:es|ing)|lag(?:gy|s|ging)?|(?:not|won't|doesn't) (?:load|open|work|sync|start|connect)|(?:update|latest version) broke|force close|black screen|error (?:message|code|when))\b", re.I),
        ],
        "Плохой UX / дизайн": [
            re.compile(r"\b(?:confusing (?:ui|interface|app|layout|design)|hard to (?:use|navigate|find)|bad (?:interface|design|ui|ux)|unintuitive|cluttered|too many (?:steps|clicks|taps)|(?:not|isn't) user.friendly|terrible (?:ui|ux|design|interface))\b", re.I),
        ],
        "Неточность данных": [
            re.compile(r"\b(?:inaccurate|(?:wrong|incorrect) (?:data|calories?|info|result|identification|plant)|not accurate|bad database|missing (?:food|items?|plants?)|misidentif|false positive)\b", re.I),
        ],
        "Приватность": [
            re.compile(r"\b(?:privacy (?:concern|issue|policy)|(?:data|user) (?:collection|harvesting|selling)|track(?:ing|s) (?:me|my|user)|suspicious permission|(?:steals?|sells?) (?:my |your )?data)\b", re.I),
        ],
        "Не хватает функций": [
            re.compile(r"\b(?:missing feature|(?:doesn't|doesn t|does not) (?:have|support)|wish (?:it|the app) had|would be (?:nice|great) (?:if|to)|(?:need|needs) (?:a |more )?(?:feature|option|support)|limited feature|basic feature missing)\b", re.I),
        ],
        "Навязчивость и реклама": [
            re.compile(r"\b(?:too many (?:notification|ad|pop.?up)|spam(?:my|ming)?|(?:annoying|constant|endless) (?:notification|ad|pop.?up)|full of ads|ad.?ridden|(?:push|forced) notification)\b", re.I),
        ],
    }

    c_l, c_r = st.columns(2)
    with c_l:
        st.markdown(f'<div style="font-size:1.05rem;font-weight:600;color:{C_GREEN};margin-bottom:8px">What People Like</div>', unsafe_allow_html=True)
        pos_rows = app_data[app_data["sentiment_label"] == "positive"] if "sentiment_label" in app_data.columns else pd.DataFrame()
        if not pos_rows.empty:
            for cat_name, patterns in _LIKE_CATEGORIES.items():
                matched_idx = []
                for df_idx, row in pos_rows.iterrows():
                    txt = str(row.get("text", ""))
                    if any(p.search(txt) for p in patterns):
                        matched_idx.append(df_idx)
                if matched_idx:
                    cat_df = pos_rows.loc[matched_idx].sort_values("sentiment_score", ascending=False)
                    _analytics_expander_block(f"{cat_name} — {len(cat_df)}", cat_df, f"pos_{cat_name}", max_show=8)
        else:
            st.info("No positive reviews")

    with c_r:
        st.markdown(f'<div style="font-size:1.05rem;font-weight:600;color:{C_RED};margin-bottom:8px">Complaints</div>', unsafe_allow_html=True)
        neg_rows = app_data[app_data["sentiment_label"] == "negative"] if "sentiment_label" in app_data.columns else pd.DataFrame()
        if not neg_rows.empty:
            for cat_name, patterns in _COMPLAINT_CATEGORIES.items():
                matched_idx = []
                for df_idx, row in neg_rows.iterrows():
                    txt = str(row.get("text", ""))
                    if any(p.search(txt) for p in patterns):
                        matched_idx.append(df_idx)
                if matched_idx:
                    cat_df = neg_rows.loc[matched_idx].sort_values("sentiment_score", ascending=True)
                    _analytics_expander_block(f"{cat_name} — {len(cat_df)}", cat_df, f"neg_{cat_name}", max_show=8)
        else:
            st.info("No negative reviews")

    st.markdown("---")

    # ── Feature Requests — strict: must mention an app and request a feature ──
    st.markdown("##### Feature Requests")
    # Build set of known app names for text matching
    _known_apps_set = set(app_data["app_name"].dropna().unique())
    _app_patterns = {app: re.compile(re.escape(app), re.I) for app in _known_apps_set if len(app) > 2}

    # Stricter feature patterns — must be about app features
    _strict_fr = [
        re.compile(r"\bi\s+wish\s+(?:the\s+app|this\s+app|it)\s+(?:had|could|would)\s+(.{10,80}?)(?:[.\n!?]|$)", re.I),
        re.compile(r"\bwould\s+(?:be\s+)?(?:nice|great|cool)\s+(?:if\s+(?:the\s+app|it|they)\s+)(.{10,80}?)(?:[.\n!?]|$)", re.I),
        re.compile(r"\b(?:they|the app|it|devs?)\s+should\s+(?:add|have|include|support|fix|improve)\s+(.{10,80}?)(?:[.\n!?]|$)", re.I),
        re.compile(r"\bplease\s+(?:add|fix|update|improve)\s+(.{10,80}?)(?:[.\n!?]|$)", re.I),
        re.compile(r"\bneed(?:s)?\s+(?:a|an|to\s+add|to\s+have|better)\s+(.{10,80}?)(?:[.\n!?]|$)", re.I),
        re.compile(r"\bmissing\s+(?:feature|option|setting|function|support)\b", re.I),
        re.compile(r"\blacking\s+(?:feature|option|support|function)\b", re.I),
    ]

    fr_indices: list[int] = []
    for df_idx, row in app_data.iterrows():
        text = str(row.get("text", ""))
        app = str(row.get("app_name", ""))
        # Text must mention the app name OR the row is already tagged to an app
        has_app_context = any(p.search(text) for p in _app_patterns.values()) or (app in _known_apps_set)
        if has_app_context:
            for pat in _strict_fr:
                if pat.search(text):
                    fr_indices.append(df_idx)
                    break
    if fr_indices:
        fr_df = app_data.loc[fr_indices]
        fr_apps = fr_df["app_name"].value_counts().head(10)
        cols_fr = st.columns(2)
        for i, (app_name, cnt) in enumerate(fr_apps.items()):
            with cols_fr[i % 2]:
                app_fr = fr_df[fr_df["app_name"] == app_name]
                _analytics_expander_block(f"{app_name} — {cnt} requests", app_fr, f"fr_{app_name}", max_show=6)
    else:
        st.info("No feature requests found")

    st.markdown("---")

    # ── Topics — Categories with sentiment breakdown ──
    st.markdown("##### Topics — Categories")
    if "primary_category" in app_data.columns:
        cat_sent = app_data.groupby(["primary_category", "sentiment_label"]).size().reset_index(name="count")
        cat_totals = app_data["primary_category"].value_counts().head(15)
        if not cat_totals.empty:
            cats_order = cat_totals.index.tolist()
            fig = go.Figure()
            cm = {"positive": C_GREEN, "negative": C_RED, "neutral": C_YELLOW}
            lm = {"positive": "Positive", "negative": "Negative", "neutral": "Neutral"}
            for sv in ["positive", "neutral", "negative"]:
                d = cat_sent[cat_sent["sentiment_label"] == sv]
                d = d[d["primary_category"].isin(cats_order)]
                if not d.empty:
                    fig.add_trace(go.Bar(
                        y=d["primary_category"], x=d["count"],
                        name=lm.get(sv, sv), marker_color=cm.get(sv, C_BLUE), orientation="h"
                    ))
            fig.update_layout(**PLOTLY_LAYOUT, height=max(len(cats_order) * 32, 200),
                            barmode="stack", yaxis=dict(categoryorder="array", categoryarray=cats_order[::-1]),
                            legend=dict(orientation="h", y=1.05, x=0))
            st.plotly_chart(fig, use_container_width=True)

            # Expandable reviews per category
            for cat in cats_order[:12]:
                cat_df = app_data[app_data["primary_category"] == cat]
                n_p = len(cat_df[cat_df["sentiment_label"] == "positive"]) if "sentiment_label" in cat_df.columns else 0
                n_n = len(cat_df[cat_df["sentiment_label"] == "negative"]) if "sentiment_label" in cat_df.columns else 0
                label = f"{cat} — {len(cat_df)} (pos {n_p} / neg {n_n})"
                _analytics_expander_block(label, cat_df, f"cat_{cat}", max_show=8)

    st.markdown("---")

    # ── Demographics ──
    st.markdown("##### Demographics (heuristic)")
    _male_re = re.compile(r"\b(?:my wife|my girlfriend|as a (?:man|guy|husband|dad|father|boyfriend|bf)|(?:i'm|im) a (?:guy|man|dude))\b", re.I)
    _female_re = re.compile(r"\b(?:my husband|my boyfriend|as a (?:woman|girl|wife|mom|mother|girlfriend|gf)|(?:i'm|im) a (?:girl|woman|lady))\b", re.I)
    male_n = int(deduped["text"].fillna("").str.contains(_male_re).sum())
    female_n = int(deduped["text"].fillna("").str.contains(_female_re).sum())
    unk_n = max(0, total - male_n - female_n)

    gc1, gc2 = st.columns(2)
    with gc1:
        fig = go.Figure(go.Pie(
            labels=["🙋‍♂️ М", "🙋‍♀️ Ж", "❓ N/A"], values=[male_n, female_n, unk_n],
            marker=dict(colors=[C_BLUE, C_PURPLE, "#464c54"]), textinfo="label+value+percent", hole=0.45,
        ))
        fig.update_layout(**PLOTLY_LAYOUT, height=230, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with gc2:
        _geo = {
            "🇺🇸 USA": re.compile(r"\b(?:usa|united states|america|california|new york|texas|florida|US\b)", re.I),
            "🇬🇧 UK": re.compile(r"\b(?:uk|united kingdom|london|england|british)\b", re.I),
            "🇨🇦 Canada": re.compile(r"\b(?:canada|canadian|toronto|vancouver)\b", re.I),
            "🇦🇺 Australia": re.compile(r"\b(?:australia|australian|sydney|melbourne)\b", re.I),
            "🇮🇳 India": re.compile(r"\b(?:india|indian|mumbai|delhi)\b", re.I),
        }
        geo_counts = {k: int(deduped["text"].fillna("").str.contains(v).sum()) for k, v in _geo.items()}
        geo_counts = {k: v for k, v in sorted(geo_counts.items(), key=lambda x: x[1], reverse=True) if v > 0}
        if geo_counts:
            fig = go.Figure(go.Bar(x=list(geo_counts.values()), y=list(geo_counts.keys()), orientation="h", marker_color=C_TEAL))
            fig.update_layout(**PLOTLY_LAYOUT, height=max(len(geo_counts) * 30, 150), yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
    st.caption("⚠️ Text-based heuristic.")

    st.markdown("---")

    # ── Strengths vs Weaknesses — per app with real reviews ──
    st.markdown("##### Strengths vs Weaknesses")
    _no_gen_sw = app_data[~app_data["app_name"].isin(["General", "General / Общее"])]
    app_counts_sw = _no_gen_sw["app_name"].value_counts()
    top_apps_sw = app_counts_sw[app_counts_sw >= 5].head(15).index.tolist()

    for app_name in top_apps_sw:
        app_df = _no_gen_sw[_no_gen_sw["app_name"] == app_name]
        n_total = len(app_df)
        pos_df = app_df[app_df["sentiment_label"] == "positive"] if "sentiment_label" in app_df.columns else pd.DataFrame()
        neg_df = app_df[app_df["sentiment_label"] == "negative"] if "sentiment_label" in app_df.columns else pd.DataFrame()
        n_p = len(pos_df)
        n_n = len(neg_df)
        with st.expander(f"{app_name} — {n_total} total (pos {n_p} / neg {n_n})", expanded=False):
            sc1, sc2 = st.columns(2)
            with sc1:
                st.markdown(f'<div style="color:{C_GREEN};font-weight:600;margin-bottom:4px">Strengths ({n_p})</div>', unsafe_allow_html=True)
                if not pos_df.empty:
                    parts = []
                    for _, row in pos_df.sort_values("sentiment_score", ascending=False).head(5).iterrows():
                        parts.append(_render_review_row(row, 0))
                    st.markdown("\n".join(parts), unsafe_allow_html=True)
                else:
                    st.info("No positive reviews")
            with sc2:
                st.markdown(f'<div style="color:{C_RED};font-weight:600;margin-bottom:4px">Weaknesses ({n_n})</div>', unsafe_allow_html=True)
                if not neg_df.empty:
                    parts = []
                    for _, row in neg_df.sort_values("sentiment_score", ascending=True).head(5).iterrows():
                        parts.append(_render_review_row(row, 0))
                    st.markdown("\n".join(parts), unsafe_allow_html=True)
                else:
                    st.info("No negative reviews")

    st.markdown("---")

    # ── App Switches — real app-to-app transitions ──
    st.markdown("##### App Switches")
    # Find posts where users mention switching FROM one app TO another
    known_apps = set(app_data["app_name"].dropna().unique()) if "app_name" in app_data.columns else set()
    known_apps = {a for a in known_apps if len(a) > 2 and not a.startswith("[")}
    _switch_re = re.compile(
        r"\b(?:switched?|moved?|migrated?|went|came|changed?)\s+"
        r"(?:from|over\s+from|away\s+from)\s+(.+?)\s+"
        r"(?:to|over\s+to)\s+(.+?)(?:\s|[.,!?;]|$)",
        re.I
    )
    _switch_re2 = re.compile(
        r"\b(?:left|quit|dropped|ditched|uninstalled?)\s+(.+?)\s+"
        r"(?:for|and\s+(?:now\s+)?(?:use|using|switched?\s+to))\s+(.+?)(?:\s|[.,!?;]|$)",
        re.I
    )

    switch_rows: list[dict] = []
    for _, row in app_data.iterrows():
        text = str(row.get("text", ""))
        link = row.get("permalink", "")
        for pat in [_switch_re, _switch_re2]:
            m = pat.search(text)
            if m:
                from_raw = m.group(1).strip().rstrip(".,!?;")[:60]
                to_raw = m.group(2).strip().rstrip(".,!?;")[:60]
                # At least one side must be a known app
                from_match = None
                to_match = None
                for app in known_apps:
                    if app.lower() in from_raw.lower():
                        from_match = app
                    if app.lower() in to_raw.lower():
                        to_match = app
                if from_match or to_match:
                    switch_rows.append({
                        "from": from_match or from_raw,
                        "to": to_match or to_raw,
                        "text": text[:200].replace("\n", " "),
                        "link": link,
                    })
                    break

    if switch_rows:
        sw_html_rows = []
        for s in switch_rows[:30]:
            link_html = f'<a href="{s["link"]}" target="_blank" class="ulink">Reddit</a>' if s["link"] else ""
            sw_html_rows.append(
                f'<tr style="border-bottom:1px solid #30363d">'
                f'<td style="padding:8px;color:{C_RED};font-weight:600;white-space:nowrap">{_esc(s["from"])}</td>'
                f'<td style="padding:8px;font-size:1.1rem;text-align:center">→</td>'
                f'<td style="padding:8px;color:{C_GREEN};font-weight:600;white-space:nowrap">{_esc(s["to"])}</td>'
                f'<td style="padding:8px;font-size:.82rem;color:#8b949e">{_esc(s["text"][:160])}</td>'
                f'<td style="padding:8px">{link_html}</td>'
                f'</tr>'
            )
        table_html = (
            '<table style="width:100%;border-collapse:collapse">'
            '<tr style="border-bottom:2px solid #30363d">'
            '<th style="text-align:left;padding:8px;color:#8b949e;font-size:.8rem">From</th>'
            '<th></th>'
            '<th style="text-align:left;padding:8px;color:#8b949e;font-size:.8rem">To</th>'
            '<th style="text-align:left;padding:8px;color:#8b949e;font-size:.8rem">Context</th>'
            '<th style="text-align:left;padding:8px;color:#8b949e;font-size:.8rem">Link</th>'
            '</tr>'
            + "\n".join(sw_html_rows)
            + '</table>'
        )
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.info("No app switches found")

    # ── N-grams ──
    with st.expander("Bigrams & TF-IDF"):
        ac1, ac2 = st.columns(2)
        with ac1:
            bigrams = get_ngrams(texts, n=2, top_k=12)
            if bigrams:
                bg_df = pd.DataFrame(bigrams, columns=["Bigram", "Count"])
                fig = go.Figure(go.Bar(x=bg_df["Count"], y=bg_df["Bigram"], orientation="h", marker_color=C_TEAL))
                fig.update_layout(**PLOTLY_LAYOUT, height=300, yaxis=dict(autorange="reversed"), title="Bigrams")
                st.plotly_chart(fig, use_container_width=True)
        with ac2:
            tfidf = get_tfidf_keywords(texts, top_k=12)
            if tfidf:
                tf_df = pd.DataFrame(tfidf, columns=["Word", "Weight"])
                fig = go.Figure(go.Bar(x=tf_df["Weight"], y=tf_df["Word"], orientation="h", marker_color=C_BLUE))
                fig.update_layout(**PLOTLY_LAYOUT, height=300, yaxis=dict(autorange="reversed"), title="TF-IDF")
                st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ── Niche Discussions — general talk NOT about specific apps ──
    if len(niche_data) > 0:
        st.markdown("##### Niche Discussions")
        st.caption(f"Posts and comments about the niche in general, not specifically about apps ({len(niche_data)} total)")
        # Group by sentiment
        for sent_label, sent_color, sent_title in [
            ("negative", C_RED, "Pain Points & Frustrations"),
            ("positive", C_GREEN, "Positive Experiences"),
            ("neutral", C_YELLOW, "General Discussions"),
        ]:
            sent_df = niche_data[niche_data["sentiment_label"] == sent_label] if "sentiment_label" in niche_data.columns else pd.DataFrame()
            if not sent_df.empty:
                _analytics_expander_block(f"{sent_title} — {len(sent_df)}", sent_df.head(50), f"niche_{sent_label}", max_show=10)

    st.markdown("---")
    ec1, ec2, _ = st.columns([1, 1, 6])
    with ec1:
        st.download_button("📥 Excel", data=_to_excel(filtered), file_name=f"reviews_{datetime.now():%Y%m%d}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_xlsx")
    with ec2:
        st.download_button("📄 CSV", data=_to_csv(filtered), file_name=f"reviews_{datetime.now():%Y%m%d}.csv", mime="text/csv", key="dl_csv")


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    if not _check_auth():
        return

    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown(
        f'''<div class="appbar">
            <img class="appbar-logo" src="{LOGO_URL}" alt="Next logo" />
            <div class="appbar-copy">
                <div class="appbar-title">Next Reddit Parser</div>
                <div class="appbar-subtitle">Review intelligence dashboard</div>
            </div>
        </div>''',
        unsafe_allow_html=True,
    )

    df = load_reviews()
    if df.empty:
        st.warning("No data. Run parser: `python -m src.cli scrape`")
        return

    df = _add_niche(df)
    filtered, search_q, src_filter = _global_filters(df)

    total = len(filtered)
    avg_s = filtered["sentiment_score"].mean() if "sentiment_score" in filtered.columns and total > 0 else 0
    n_apps = filtered["app_name"].nunique()
    sent_c = C_GREEN if avg_s > 0.05 else (C_RED if avg_s < -0.05 else C_YELLOW)
    _stat_line([
        _stat_val(str(total), "reviews", C_BLUE),
        _stat_val(f"{avg_s:+.2f}", "sentiment", sent_c),
        _stat_val(str(n_apps), "apps", C_PURPLE),
    ])

    tab1, tab2 = st.tabs(["📝 Reviews", "📊 Analytics"])
    with tab1:
        page_reviews(filtered, search_q, df, src_filter)
    with tab2:
        page_analytics(filtered)


if __name__ == "__main__":
    main()