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

from src.analytics.competitor import build_comparison_table, detect_switches, get_strengths_weaknesses  # noqa: E402
from src.analytics.pain_extractor import extract_feature_requests, extract_highlights, extract_pains  # noqa: E402
from src.analytics.patterns import get_ngrams, get_tfidf_keywords  # noqa: E402
from src.analytics.segments import SEGMENTS, get_segment_summary, segment_users  # noqa: E402
from src.apps import TRACKED_APPS, get_apps_by_niche  # noqa: E402
from src.models import AppConfig, AppNiche  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "reviews"
CSV_FILE = DATA_DIR / "all_reviews.csv"

# ── Local assets (base64-encoded so they work in Docker too) ──────────
_ASSETS_DIR = Path(__file__).resolve().parent / "assets"

def _load_b64(filename: str) -> str:
    """Return a data-URI string for an image in the assets folder."""
    fp = _ASSETS_DIR / filename
    if not fp.exists():
        return ""
    suffix = fp.suffix.lower()
    mime = {"gif": "image/gif", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(suffix.lstrip("."), "image/png")
    encoded = base64.b64encode(fp.read_bytes()).decode()
    return f"data:{mime};base64,{encoded}"

LOGO_URL = _load_b64("photo_2026-03-08 18.03.06.jpeg")
AUTH_GIF_URL = _load_b64("ScreenRecording_03-08-2026-18-31-16_1.gif")

NICHE_RU: dict[AppNiche, str] = {
    AppNiche.RELATIONSHIPS: "💑 Отношения и ментал",
    AppNiche.SMOKING: "🚭 Бросить курить",
    AppNiche.PLANT_SCANNER: "🌿 Сканер растений",
    AppNiche.CALORIE_TRACKER: "🍎 Трекер калорий",
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
.cm-block { border-left:3px solid var(--g-border); padding-left:10px; margin:3px 0; }
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

def _global_filters(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
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

    # Row 2: category + date popover
    r1, r2, _ = st.columns([1.3, 2.2, 6.5])
    with r1:
        sel_cats = st.multiselect("CATEGORY", options=all_categories, default=[], placeholder="All", key="f_cat")

    with r2:
        if "f_date_start" not in st.session_state:
            st.session_state.f_date_start = max_date - timedelta(days=180)
            st.session_state.f_date_end = max_date
            st.session_state.f_date_label = "6 mo"

        date_label = st.session_state.get("f_date_label", "6 mo")
        ds = st.session_state.f_date_start
        de = st.session_state.f_date_end

        st.markdown('<p style="font-size:.75rem;font-weight:600;color:var(--g-text-secondary);margin:0 0 4px 0;text-transform:uppercase;letter-spacing:.06em">DATE</p>', unsafe_allow_html=True)
        with st.popover(f"📅 {date_label} · {ds.strftime('%d.%m.%Y')} — {de.strftime('%d.%m.%Y')}"):
            date_range = st.date_input(
                "Date range",
                value=(st.session_state.f_date_start, st.session_state.f_date_end),
                min_value=min_date,
                max_value=max_date,
                key="f_date_picker",
                label_visibility="collapsed",
            )
            if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                if date_range[0] != st.session_state.f_date_start or date_range[1] != st.session_state.f_date_end:
                    st.session_state.f_date_start = date_range[0]
                    st.session_state.f_date_end = date_range[1]
                    st.session_state.f_date_label = "Custom"

            if st.button("3 months", key="dp_3m", use_container_width=True):
                st.session_state.f_date_start = max_date - timedelta(days=90)
                st.session_state.f_date_end = max_date
                st.session_state.f_date_label = "3 mo"
                st.rerun()
            if st.button("6 months", key="dp_6m", use_container_width=True):
                st.session_state.f_date_start = max_date - timedelta(days=180)
                st.session_state.f_date_end = max_date
                st.session_state.f_date_label = "6 mo"
                st.rerun()
            if st.button("1 year", key="dp_1y", use_container_width=True):
                st.session_state.f_date_start = max_date - timedelta(days=365)
                st.session_state.f_date_end = max_date
                st.session_state.f_date_label = "1 year"
                st.rerun()
            if st.button("All time", key="dp_all", use_container_width=True):
                st.session_state.f_date_start = min_date
                st.session_state.f_date_end = max_date
                st.session_state.f_date_label = "All time"
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
    if src_filter == "📄 Posts" and "source" in out.columns:
        out = out[out["source"] == "post"]
    elif src_filter == "💬 Comments" and "source" in out.columns:
        out = out[out["source"] == "comment"]
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
    return out, search_q

# ═══════════════════════════════════════════════════════════════════════════
#  PAGE 1: REVIEWS FEED
# ═══════════════════════════════════════════════════════════════════════════

def page_reviews(filtered: pd.DataFrame, search_q: str) -> None:
    if filtered.empty:
        st.info("Нет отзывов по выбранным фильтрам.")
        return

    has_src = "source" in filtered.columns
    if has_src:
        posts = filtered[filtered["source"] == "post"].copy()
        comments = filtered[filtered["source"] == "comment"].copy()
    else:
        posts = filtered.copy()
        comments = pd.DataFrame()

    comment_groups: dict[str, pd.DataFrame] = {}
    if not comments.empty:
        comments = comments.copy()
        comments["_base"] = comments["permalink"].fillna("").apply(_post_base)
        for base, grp in comments.groupby("_base"):
            comment_groups[base] = grp

    if not posts.empty:
        posts["_base"] = posts["permalink"].fillna("").apply(_post_base)
        posts["_n_comments"] = posts["_base"].map(lambda b: len(comment_groups.get(b, [])))
    else:
        posts = posts.copy()
        posts["_n_comments"] = 0

    st.markdown(
        f'<div style="font-size:.76rem;color:var(--g-text-secondary);margin:2px 0 6px 0">'
        f'📄 {len(posts)} постов · 💬 {len(comments)} комментариев · {len(filtered)} всего</div>',
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

    if not comments.empty and not posts.empty:
        post_bases = set(posts["_base"].tolist())
        orph = comments[~comments["_base"].isin(post_bases)]
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

    label = f"📄 {title[:90]}  ·  {app}  ·  {date_s}  ·  💬 {n_comm}"
    with st.expander(label, expanded=True):
        pills = _pill("tag-post", "📄 пост")
        if app:
            pills += " " + _pill_app(app)
        pills += " " + _pill_sent(sent)
        if niche:
            pills += " " + _pill_niche(niche)
        if primary_cat and primary_cat != "nan":
            pills += " " + _pill_cat(primary_cat.strip())

        st.markdown(f'<div class="rv-meta">{_user_link(author)} · {date_s} · {pills}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="rv-text">{_highlight(text[:1500], search_q)}</div>', unsafe_allow_html=True)
        if link:
            st.markdown(f'<div class="rv-link"><a href="{link}" target="_blank" class="ulink">🔗 Reddit</a></div>', unsafe_allow_html=True)

        if n_comm > 0:
            st.markdown(
                f'<div style="margin-top:6px;padding-top:5px;border-top:1px solid var(--g-border)">'
                f'<b style="color:var(--g-text-secondary);font-size:.76rem">💬 {n_comm} комментариев</b></div>',
                unsafe_allow_html=True,
            )
            for _, cr in post_comments.iterrows():
                _render_comment(cr, search_q)


def _render_comment(cr: pd.Series, search_q: str) -> None:
    c_author = cr.get("author", "?")
    c_text = str(cr.get("text", ""))[:600]
    c_sent = cr.get("sentiment_label", "")
    c_date = cr["date"].strftime("%d.%m.%Y") if pd.notna(cr.get("date")) else ""
    c_link = cr.get("permalink", "")
    c_app = cr.get("app_name", "")
    c_cat = str(cr.get("primary_category", ""))
    link_html = f' · <a href="{c_link}" target="_blank" class="ulink">🔗</a>' if c_link else ""
    cat_html = f' {_pill_cat(c_cat.strip())}' if c_cat and c_cat != "nan" else ""
    st.markdown(
        f'<div class="cm-block">'
        f'{_pill("tag-comm", "💬")} '
        f'{_user_link(c_author)} · '
        f'<span style="color:var(--g-text-secondary);font-size:.72rem">{c_date}</span> '
        f'{_pill_sent(c_sent)} {_pill_app(c_app)}{cat_html}{link_html}<br>'
        f'<span style="font-size:.82rem">{_highlight(c_text, search_q)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ═══════════════════════════════════════════════════════════════════════════
#  PAGE 2: ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════

def page_analytics(filtered: pd.DataFrame) -> None:
    if filtered.empty:
        st.info("No data for analytics.")
        return

    # Deduplicate for accurate counting: same permalink = same content
    deduped = filtered.drop_duplicates(subset="permalink") if "permalink" in filtered.columns else filtered

    total = len(deduped)
    texts = deduped["text"].fillna("").tolist()
    apps = deduped["app_name"].fillna("").tolist()

    n_pos = len(deduped[deduped["sentiment_label"] == "positive"]) if "sentiment_label" in deduped.columns else 0
    n_neg = len(deduped[deduped["sentiment_label"] == "negative"]) if "sentiment_label" in deduped.columns else 0
    n_neu = total - n_pos - n_neg
    n_apps = filtered["app_name"].nunique()  # apps from full set (not deduped)
    n_authors = deduped["author"].nunique() if "author" in deduped.columns else 0
    n_posts = len(deduped[deduped["source"] == "post"]) if "source" in deduped.columns else total
    n_comments = len(deduped[deduped["source"] == "comment"]) if "source" in deduped.columns else 0

    k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
    k1.metric("Total", total)
    k2.metric("📄 Posts", n_posts)
    k3.metric("💬 Comments", n_comments)
    k4.metric("😊 Positive", n_pos)
    k5.metric("😞 Negative", n_neg)
    k6.metric("📱 Apps", n_apps)
    k7.metric("👤 Authors", n_authors)

    st.markdown("---")

    # Sentiment by app (deduped, exclude General)
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

    # Stacked sentiment (deduped, exclude General)
    st.markdown("##### Sentiment Distribution")
    if "sentiment_label" in deduped.columns:
        _no_gen2 = deduped[~deduped["app_name"].isin(["General", "General / Общее"])]
        apps_bar = _no_gen2["app_name"].value_counts()
        apps_bar = apps_bar[apps_bar >= 2].head(15).index.tolist()
        if apps_bar:
            bar_data = _no_gen2[_no_gen2["app_name"].isin(apps_bar)]
            sent_counts = bar_data.groupby(["app_name", "sentiment_label"]).size().reset_index(name="count")
            fig = go.Figure()
            cm = {"positive": C_GREEN, "negative": C_RED, "neutral": C_YELLOW}
            lm = {"positive": "😊 Positive", "negative": "😞 Negative", "neutral": "😐 Neutral"}
            for sv in ["positive", "neutral", "negative"]:
                d = sent_counts[sent_counts["sentiment_label"] == sv]
                if not d.empty:
                    fig.add_trace(go.Bar(y=d["app_name"], x=d["count"], name=lm.get(sv, sv), marker_color=cm.get(sv, C_BLUE), orientation="h"))
            fig.update_layout(**PLOTLY_LAYOUT, height=max(len(apps_bar) * 30, 200), barmode="stack", yaxis=dict(autorange="reversed"), legend=dict(orientation="h", y=1.05, x=0))
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Praise vs Complaints
    c_l, c_r = st.columns(2)
    with c_l:
        st.markdown("##### 😊 What People Like")
        highlights = extract_highlights(texts, apps)
        if highlights:
            for h in highlights[:8]:
                st.markdown(
                    f'<div class="pain-card"><b style="color:{C_GREEN}">{_esc(h.text)}</b> — {h.count} mentions'
                    + "".join(f'<div class="pain-quote">{_esc(e[:200])}</div>' for e in h.examples[:2])
                    + (f'<div class="pain-apps">📱 {", ".join(h.apps[:5])}</div>' if h.apps else "")
                    + '</div>', unsafe_allow_html=True)
        else:
            st.info("No data")
    with c_r:
        st.markdown("##### 😤 Complaints")
        pains = extract_pains(texts, apps)
        if pains:
            for p in pains[:8]:
                st.markdown(
                    f'<div class="pain-card"><b style="color:{C_RED}">{_esc(p.text)}</b> — {p.count} mentions'
                    + "".join(f'<div class="pain-quote">{_esc(e[:200])}</div>' for e in p.examples[:2])
                    + (f'<div class="pain-apps">📱 {", ".join(p.apps[:5])}</div>' if p.apps else "")
                    + '</div>', unsafe_allow_html=True)
        else:
            st.info("No data")

    st.markdown("---")

    # Feature requests
    st.markdown("##### 💡 Feature Requests")
    freqs = extract_feature_requests(texts, apps)
    if freqs:
        cols_fr = st.columns(2)
        for i, f in enumerate(freqs[:10]):
            with cols_fr[i % 2]:
                st.markdown(
                    f'<div class="pain-card"><b style="color:{C_BLUE}">{_esc(f.text)}</b> — {f.count} mentions'
                    + "".join(f'<div class="pain-quote">{_esc(e[:150])}</div>' for e in f.examples[:2])
                    + '</div>', unsafe_allow_html=True)

    st.markdown("---")

    # Categories (deduped)
    st.markdown("##### 📂 Topics — Categories")
    if "primary_category" in deduped.columns:
        cat_counts = deduped["primary_category"].value_counts().head(12)
        if not cat_counts.empty:
            fig = go.Figure(go.Bar(
                x=cat_counts.values, y=cat_counts.index, orientation="h",
                marker_color=C_TEAL, text=cat_counts.values, textposition="outside",
            ))
            fig.update_layout(**PLOTLY_LAYOUT, height=max(len(cat_counts) * 28, 200), yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Demographics (deduped)
    st.markdown("##### 🚻 Demographics (heuristic)")
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

    # Strengths / weaknesses
    st.markdown("##### ⚔️ Strengths vs Weaknesses")
    sw = get_strengths_weaknesses(deduped)
    if sw:
        for app_name, data in sorted(sw.items()):
            if not data["strengths"] and not data["weaknesses"]:
                continue
            with st.expander(f"📱 {app_name}"):
                sc1, sc2 = st.columns(2)
                with sc1:
                    st.markdown("**✅ Pros:**")
                    for s in data["strengths"][:5]:
                        st.markdown(f"• {s}")
                with sc2:
                    st.markdown("**❌ Cons:**")
                    for w in data["weaknesses"][:5]:
                        st.markdown(f"• {w}")

    st.markdown("---")

    # Switches
    st.markdown("##### 🔄 App Switches")
    authors_list = deduped["author"].fillna("").tolist() if "author" in deduped.columns else None
    switches = detect_switches(texts, authors_list)
    if switches:
        sw_data = [{"From": s.from_app, "To": s.to_app, "Reason": s.reason[:100]} for s in switches[:15]]
        st.dataframe(pd.DataFrame(sw_data), hide_index=True, use_container_width=True)

    st.markdown("---")

    # Top subreddits
    st.markdown("##### 🏠 Subreddits")
    if "subreddit" in deduped.columns:
        top_subs = deduped["subreddit"].value_counts().head(10)
        if not top_subs.empty:
            fig = go.Figure(go.Bar(x=top_subs.values, y=top_subs.index, orientation="h", marker_color=C_TEAL))
            fig.update_layout(**PLOTLY_LAYOUT, height=max(len(top_subs) * 26, 150), yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

    # N-grams
    with st.expander("📊 Bigrams & TF-IDF"):
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
    filtered, search_q = _global_filters(df)

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
        page_reviews(filtered, search_q)
    with tab2:
        page_analytics(filtered)


if __name__ == "__main__":
    main()