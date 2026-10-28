"""ui.py — presentation layer for the UAE FLSC compliance console.

Everything visual lives here: the injected global stylesheet, the hero
banner, status badges / count pills, chapter headers, the classification
strip, the status-distribution bar, the legend and the footer. app.py stays
in charge of *what* is shown; this module decides *how it looks*.

All builders return HTML strings (render with st.markdown(..., unsafe_allow_html=True))
except inject_css / render_hero / render_sidebar_brand which render directly.
"""
from __future__ import annotations

import base64
import html as _html
from pathlib import Path

import streamlit as st

_ASSETS = Path(__file__).parent / "assets"

# status -> (label, foreground, background, border)
STATUS_META: dict[str, tuple[str, str, str, str]] = {
    "required":     ("Required",     "#B91C1C", "#FEF2F2", "#FECACA"),
    "recommended":  ("Recommended",  "#1D4ED8", "#EFF6FF", "#BFDBFE"),
    "conditional":  ("Conditional",  "#B45309", "#FFFBEB", "#FDE68A"),
    "not_required": ("Not required", "#64748B", "#F8FAFC", "#E2E8F0"),
    # Audit UX-03: a missing input, never a pass and never a required system.
    "not_evaluated": ("Not evaluated", "#6D28D9", "#F5F3FF", "#DDD6FE"),
}

STATUS_ORDER = ["required", "not_evaluated", "recommended", "conditional", "not_required"]


def esc(text: str) -> str:
    return _html.escape(str(text or ""))


# ---------------------------------------------------------------------------
# Global stylesheet
# ---------------------------------------------------------------------------

_GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&family=Noto+Kufi+Arabic:wght@500;700&display=swap');

:root {
  --flsc-navy:    #101F38;
  --flsc-navy-2:  #1B3153;
  --flsc-red:     #C8102E;
  --flsc-amber:   #F0A43B;
  --flsc-ink:     #1B2532;
  --flsc-muted:   #475569;   /* audit UX-24: 4.5:1 or better on the page background */
  --flsc-border:  #E2E8F0;
  --flsc-card:    #FFFFFF;
  --flsc-radius:  14px;
  --flsc-shadow:  0 1px 2px rgba(15,23,42,.05), 0 2px 8px rgba(15,23,42,.06);
}

/* ---------- chrome ---------- */
.stAppDeployButton { display: none; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMainBlockContainer"] { padding-top: 1.6rem; max-width: 1280px; }
[data-testid="stMainBlockContainer"] hr { margin: 1.4rem 0; border-color: var(--flsc-border); }

/* anchor jumps shouldn't hide the target under the fixed header */
a[name], .flsc-chapter { scroll-margin-top: 4rem; }

/* ---------- hero ---------- */
.flsc-hero {
  position: relative; border-radius: 18px; overflow: hidden;
  padding: 2.1rem 2.3rem 1.7rem; margin-bottom: 1.1rem;
  color: #F4F7FB; background-color: var(--flsc-navy);
  background-size: cover; background-position: center 62%;
  box-shadow: 0 8px 28px rgba(10,20,40,.28);
}
.flsc-hero__eyebrow {
  font-size: .72rem; font-weight: 700; letter-spacing: .16em;
  text-transform: uppercase; color: #FCD9A8; margin-bottom: .5rem;
}
.flsc-hero__title {
  font-size: 2.05rem; line-height: 1.15; font-weight: 800;
  margin: 0 0 .25rem; color: #FFFFFF; letter-spacing: -.01em;
}
.flsc-hero__ar {
  font-family: 'Noto Kufi Arabic', Inter, sans-serif;
  font-size: 1.02rem; font-weight: 500; color: #C8D6EA; margin-bottom: 1rem;
}
.flsc-hero__chips { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 1.1rem; }
.flsc-hero__chip {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: .74rem; font-weight: 600; padding: 4px 12px;
  border-radius: 999px; border: 1px solid rgba(255,255,255,.28);
  background: rgba(255,255,255,.10); backdrop-filter: blur(3px);
  color: #EDF2F9; white-space: nowrap;
}
.flsc-hero__foot {
  display: flex; flex-wrap: wrap; justify-content: space-between;
  align-items: center; gap: 10px;
  border-top: 1px solid rgba(255,255,255,.16); padding-top: .8rem;
  font-size: .8rem; color: #B9C7DB;
}
.flsc-hero__foot a { color: #9EC5FF; text-decoration: none; font-weight: 600; }
.flsc-hero__foot a:hover { text-decoration: underline; }
.flsc-hero__foot svg { vertical-align: -4px; margin-right: 4px; }

/* ---------- sidebar brand ---------- */
.flsc-side-brand {
  display: flex; align-items: center; gap: 12px;
  padding: 4px 2px 14px; margin-bottom: 6px;
  border-bottom: 1px solid rgba(255,255,255,.14);
}
.flsc-side-brand__logo {
  width: 42px; height: 42px; border-radius: 12px; flex: 0 0 42px;
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; background: linear-gradient(135deg, #C8102E, #8F1D2C);
  box-shadow: 0 3px 10px rgba(200,16,46,.4);
}
.flsc-side-brand__name { font-weight: 700; font-size: .95rem; color: #F4F7FB; line-height: 1.25; }
.flsc-side-brand__sub  { font-size: .72rem; color: #93A6C4; letter-spacing: .04em; }

/* sidebar polish */
[data-testid="stSidebar"] [data-testid="stExpander"] details {
  border-radius: 12px; border-color: #2C456B;
}
[data-testid="stSidebar"] hr { border-color: #2C456B; margin: .7rem 0; }
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { letter-spacing: -.01em; }

/* ---------- metric cards ---------- */
[data-testid="stMetric"] {
  background: var(--flsc-card); border: 1px solid var(--flsc-border);
  border-radius: var(--flsc-radius); padding: 14px 16px 10px;
  box-shadow: var(--flsc-shadow); position: relative; overflow: hidden;
}
[data-testid="stMetric"]::before {
  content: ""; position: absolute; inset: 0 0 auto 0; height: 3px;
  background: linear-gradient(90deg, var(--flsc-red), var(--flsc-amber));
}
[data-testid="stMetricLabel"] p {
  text-transform: uppercase; letter-spacing: .07em;
  font-size: .7rem !important; font-weight: 700; color: var(--flsc-muted);
}
[data-testid="stMetricValue"] {
  font-weight: 700; letter-spacing: -.01em; font-size: 1.6rem !important;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* block subheaders shouldn't compete with the chapter headers */
[data-testid="stMainBlockContainer"] h3 {
  font-size: 1.12rem; font-weight: 700; color: var(--flsc-navy-2);
  padding-bottom: .15rem;
}

/* ---------- requirement cards ---------- */
[data-testid="stVerticalBlockBorderWrapper"]:has(.flsc-mark) {
  background: var(--flsc-card);
  border: 1px solid var(--flsc-border) !important;
  border-left-width: 4px !important;
  border-radius: var(--flsc-radius);
  box-shadow: var(--flsc-shadow);
}
[data-testid="stVerticalBlockBorderWrapper"]:has(.flsc-mark--required)     { border-left-color: #DC2626 !important; }
[data-testid="stVerticalBlockBorderWrapper"]:has(.flsc-mark--recommended)  { border-left-color: #2563EB !important; }
[data-testid="stVerticalBlockBorderWrapper"]:has(.flsc-mark--conditional)  { border-left-color: #F59E0B !important; }
[data-testid="stVerticalBlockBorderWrapper"]:has(.flsc-mark--not_required) { border-left-color: #CBD5E1 !important; }
.flsc-mark { display: none; }

.flsc-req-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.flsc-req-title { font-weight: 700; font-size: 1.0rem; color: var(--flsc-ink); }

/* ---------- badges & pills ---------- */
.flsc-badge {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: .66rem; font-weight: 700; letter-spacing: .09em;
  text-transform: uppercase; padding: 3px 10px; border-radius: 999px;
  border: 1px solid; white-space: nowrap;
}
.flsc-badge::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: currentColor; }

.flsc-pill {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: .68rem; font-weight: 700; padding: 1px 8px;
  border-radius: 999px; border: 1px solid; white-space: nowrap;
}

/* ---------- legend ---------- */
.flsc-legend {
  display: flex; flex-wrap: wrap; gap: 8px 18px; align-items: center;
  background: var(--flsc-card); border: 1px solid var(--flsc-border);
  border-radius: var(--flsc-radius); padding: 10px 16px; margin: .3rem 0 .8rem;
  box-shadow: var(--flsc-shadow);
}
.flsc-legend__item { display: inline-flex; align-items: center; gap: 8px; font-size: .84rem; color: var(--flsc-muted); }

/* ---------- classification strip ---------- */
.flsc-class {
  display: flex; flex-wrap: wrap; gap: 14px; align-items: stretch;
  margin: .2rem 0 .9rem;
}
.flsc-class__hero {
  flex: 0 0 auto; min-width: 190px;
  background: linear-gradient(150deg, var(--flsc-navy), var(--flsc-navy-2));
  color: #fff; border-radius: var(--flsc-radius); padding: 14px 18px;
  box-shadow: var(--flsc-shadow);
}
.flsc-class__hero small { display:block; font-size: .68rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: #FCD9A8; margin-bottom: 2px; }
.flsc-class__hero strong { font-size: 1.35rem; font-weight: 800; letter-spacing: -.01em; }
.flsc-class__hero em { display:block; font-style: normal; font-size: .74rem; color: #B9C7DB; margin-top: 2px; }
.flsc-class__branches {
  flex: 1 1 320px; display: flex; flex-wrap: wrap; gap: 7px; align-content: flex-start;
  background: var(--flsc-card); border: 1px solid var(--flsc-border);
  border-radius: var(--flsc-radius); padding: 12px 14px; box-shadow: var(--flsc-shadow);
}
.flsc-branch {
  display: inline-flex; align-items: center; gap: 7px;
  font-size: .72rem; padding: 4px 10px; border-radius: 8px;
  border: 1px solid var(--flsc-border); background: #F8FAFC; color: var(--flsc-ink);
}
.flsc-branch b {
  font-size: .66rem; font-weight: 800; letter-spacing: .06em;
  color: var(--flsc-navy-2);
}
.flsc-branch code {
  font-family: 'IBM Plex Mono', monospace; font-size: .68rem;
  color: #475569; background: none; padding: 0;
}
.flsc-branch--none code { color: #475569; font-style: italic; }

/* ---------- status distribution bar ---------- */
.flsc-statusbar { margin: .1rem 0 .4rem; }
.flsc-statusbar__track {
  display: flex; height: 12px; border-radius: 999px; overflow: hidden;
  border: 1px solid var(--flsc-border); background: #EEF2F7;
}
.flsc-statusbar__seg { height: 100%; }
.flsc-statusbar__legend { display: flex; flex-wrap: wrap; gap: 6px 16px; margin-top: 7px; font-size: .82rem; color: var(--flsc-muted); }
.flsc-statusbar__legend b { color: var(--flsc-ink); }

/* ---------- chapter headers ---------- */
.flsc-chapter {
  display: flex; align-items: center; gap: 13px;
  margin: 1.9rem 0 .5rem; padding-bottom: .55rem;
  border-bottom: 2px solid var(--flsc-border);
}
.flsc-chapter__code {
  flex: 0 0 auto; min-width: 46px; height: 40px; padding: 0 10px;
  display: inline-flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: .92rem; letter-spacing: .03em; color: #fff;
  background: linear-gradient(140deg, var(--flsc-navy), var(--flsc-navy-2));
  border-radius: 11px; box-shadow: var(--flsc-shadow);
}
.flsc-chapter--parking .flsc-chapter__code { background: linear-gradient(140deg, #7C2D12, #B45309); }
.flsc-chapter__title { font-size: 1.32rem; font-weight: 750; color: var(--flsc-ink); line-height: 1.2; letter-spacing: -.01em; }
.flsc-chapter__ar {
  font-family: 'Noto Kufi Arabic', Inter, sans-serif;
  font-size: .84rem; color: var(--flsc-muted); margin-top: 1px;
}

/* ---------- table of contents ---------- */
[data-testid="stColumn"]:has(.flsc-toc) > div {
  position: sticky; top: 3.4rem;
  max-height: calc(100vh - 4.6rem); overflow-y: auto;
  padding: 2px 4px 2px 2px;
}
.flsc-toc {
  background: var(--flsc-card); border: 1px solid var(--flsc-border);
  border-radius: var(--flsc-radius); padding: 14px 14px 10px;
  box-shadow: var(--flsc-shadow);
}
.flsc-toc__head {
  font-size: .72rem; font-weight: 800; letter-spacing: .1em;
  text-transform: uppercase; color: var(--flsc-muted); margin-bottom: 8px;
}
.flsc-toc a.flsc-toc__row {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  padding: 6px 8px; border-radius: 8px; text-decoration: none;
  color: var(--flsc-ink); font-size: .82rem; font-weight: 600;
}
.flsc-toc a.flsc-toc__row:hover { background: #F1F5F9; }
.flsc-toc__counts { display: inline-flex; gap: 4px; flex-wrap: wrap; justify-content: flex-end; }

/* ---------- buttons / inputs ---------- */
.stButton > button, .stDownloadButton > button, .stLinkButton > a { font-weight: 600; }
.stDownloadButton > button { box-shadow: var(--flsc-shadow); }

/* ---------- captions + sidebar info (audit UX-24 contrast) ---------- */
[data-testid="stMainBlockContainer"] [data-testid="stCaptionContainer"] { color: #475569; }
[data-testid="stSidebar"] [data-testid="stAlertContainer"] {
  background: #F1F5F9 !important; color: #0F172A !important;
}
[data-testid="stSidebar"] [data-testid="stAlertContainer"] p { color: #0F172A !important; }

/* ---------- compact requirement table (audit UX-13) ---------- */
.flsc-rtable { width: 100%; border-collapse: collapse; margin: .2rem 0 .9rem; font-size: .86rem;
  background: var(--flsc-card); border: 1px solid var(--flsc-border); }
.flsc-rtable th { text-align: left; font-size: .72rem; letter-spacing: .06em; text-transform: uppercase;
  color: #FFFFFF; background: var(--flsc-navy-2); padding: 6px 8px; }
.flsc-rtable td { vertical-align: top; padding: 6px 8px; border-top: 1px solid var(--flsc-border);
  color: var(--flsc-ink); overflow-wrap: anywhere; }
.flsc-rtable td.flsc-rtable__sys { font-weight: 650; width: 28%; }
.flsc-rtable td.flsc-rtable__st { width: 1%; white-space: nowrap; }
.flsc-rtable td.flsc-rtable__cite { width: 20%; color: var(--flsc-muted); font-size: .78rem; }
.flsc-rtable tr:nth-child(even) td { background: #F8FAFC; }
.flsc-rtable small { color: var(--flsc-muted); }

/* ---------- small screens (audit UX-18) ---------- */
@media (max-width: 640px) {
  .flsc-hero { padding: 1rem 1.1rem .8rem; border-radius: 12px; }
  .flsc-hero .flsc-hero__title { font-size: 1.35rem !important; line-height: 1.2; }
  .flsc-hero__ar { font-size: .85rem; margin-bottom: .4rem; }
  .flsc-hero__chips, .flsc-hero__foot { display: none; }
  .flsc-chapter__title { font-size: 1.08rem; }
  .flsc-rtable td.flsc-rtable__cite { display: none; }
}
.flsc-hero__title, .flsc-chapter__title { overflow-wrap: normal; word-break: normal; hyphens: none; }

/* ---------- footer ---------- */
.flsc-footer {
  margin-top: 1.6rem; border-radius: var(--flsc-radius);
  background: linear-gradient(150deg, var(--flsc-navy), var(--flsc-navy-2));
  color: #C8D6EA; padding: 18px 22px; font-size: .82rem; line-height: 1.55;
  box-shadow: var(--flsc-shadow);
}
.flsc-footer strong { color: #fff; }
.flsc-footer a { color: #9EC5FF; }
.flsc-footer__meta {
  margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,.14);
  display: flex; flex-wrap: wrap; gap: 8px 20px; font-size: .74rem; color: #93A6C4;
}
</style>
"""

_PRINT_CSS = """
<style>
  [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
  [data-testid="collapsedControl"] { display: none !important; }
  [data-testid="stMainBlockContainer"] { max-width: 950px; padding-top: 1rem; }
  .flsc-hero { padding: 1.2rem 1.5rem 1rem; box-shadow: none; }
  @media print {
    [data-testid="stExpander"] { page-break-inside: avoid; }
    .stDownloadButton, .stButton, [data-testid="stCheckbox"], [data-testid="stToggle"],
    [data-testid="stMultiSelect"], [data-testid="stTextInput"], [data-testid="stRadio"],
    [data-testid="stHeader"] { display: none !important; }
    .flsc-hero, .flsc-footer, .flsc-badge, .flsc-pill, .flsc-chapter__code, .flsc-rtable th {
      -webkit-print-color-adjust: exact; print-color-adjust: exact;
    }
  }
</style>
"""


def inject_css(print_mode: bool = False) -> None:
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)
    if print_mode:
        st.markdown(_PRINT_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Hero banner
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def _hero_background_css() -> str:
    """Data-URI background for the hero (navy gradient overlay on hero.jpg)."""
    hero = _ASSETS / "hero.jpg"
    overlay = "linear-gradient(100deg, rgba(11,22,42,.94) 0%, rgba(13,28,52,.82) 45%, rgba(16,31,56,.62) 100%)"
    if not hero.exists():
        return f"background-image: {overlay};"
    b64 = base64.b64encode(hero.read_bytes()).decode("ascii")
    return f"background-image: {overlay}, url(data:image/jpeg;base64,{b64});"

_LINKEDIN_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="15" height="15" fill="#9EC5FF">'
    '<path d="M20.45 20.45h-3.55v-5.57c0-1.33-.02-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.95v5.66H9.36V9h3.41v1.56h.05c.48-.9 1.65-1.85 3.4-1.85 3.64 0 4.31 2.4 4.31 5.51v6.23zM5.34 7.43a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12zM7.12 20.45H3.56V9h3.56v11.45zM22.22 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.22.79 24 1.77 24h20.45c.98 0 1.78-.78 1.78-1.73V1.73C24 .77 23.2 0 22.22 0z"/></svg>'
)

_HERO_CHIPS = [
    "📘 CDGH-OP-25 · September 2018",
    "🏗️ Chapters 2–11 + Accessibility + EAP",
    "🧮 Occupant load & fire-service access",
    "📄 Word · PDF · Excel exports",
]


def render_hero(print_mode: bool = False) -> None:
    chips = "".join(f'<span class="flsc-hero__chip">{c}</span>' for c in _HERO_CHIPS)
    bg = "" if print_mode else _hero_background_css()
    st.markdown(
        f"""
        <div class="flsc-hero" style="{bg}">
          <div class="flsc-hero__eyebrow">UAE Fire &amp; Life Safety Code of Practice</div>
          <h1 class="flsc-hero__title">Fire &amp; Life Safety Requirements</h1>
          <div class="flsc-hero__ar">أداة التحقق من متطلبات كود الإمارات للوقاية من الحريق وحماية الأرواح ٢٠١٨</div>
          <div class="flsc-hero__chips">{chips}</div>
          <div class="flsc-hero__foot">
            <span>⚖️ Design aid only — not a substitute for UAE Civil Defence review or a registered Fire Protection Engineer.</span>
            <span>Created by <strong style="color:#fff">Hussein Ragab</strong> ·
              <a href="https://www.linkedin.com/in/husseinragab" target="_blank">{_LINKEDIN_SVG} LinkedIn</a>
            </span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_brand() -> None:
    st.markdown(
        """
        <div class="flsc-side-brand">
          <div class="flsc-side-brand__logo">🧯</div>
          <div>
            <div class="flsc-side-brand__name">UAE FLSC 2018</div>
            <div class="flsc-side-brand__sub">COMPLIANCE CONSOLE</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Badges, pills, markers
# ---------------------------------------------------------------------------

def _meta_for(status: str):
    """Badge colours of a status; an unknown status (for example a later
    'not_evaluated') is shown in grey with its own name, never as 'Required'."""
    if status in STATUS_META:
        return STATUS_META[status]
    return (str(status).replace("_", " ").capitalize(), "#334155", "#F1F5F9", "#CBD5E1")


def status_badge(status: str) -> str:
    label, fg, bg, border = _meta_for(status)
    return (
        f'<span class="flsc-badge" '
        f'style="color:{fg};background:{bg};border-color:{border};">{label}</span>'
    )


def status_marker(status: str) -> str:
    """Hidden marker consumed by the :has() card-accent CSS."""
    return f'<span class="flsc-mark flsc-mark--{status}"></span>'


def count_pill(status: str, count: int) -> str:
    _, fg, bg, border = _meta_for(status)
    return (
        f'<span class="flsc-pill" '
        f'style="color:{fg};background:{bg};border-color:{border};">{count}</span>'
    )


def requirement_head(status: str, system: str) -> str:
    return (
        status_marker(status)
        + f'<div class="flsc-req-head">{status_badge(status)}'
        + f'<span class="flsc-req-title">{esc(system)}</span></div>'
    )


def legend_html() -> str:
    notes = {
        "required": "code “shall”",
        "recommended": "code “should”",
        "conditional": "subject to project context",
        "not_required": "exemption captured for traceability",
        "not_evaluated": "input missing; never taken as a pass",
    }
    items = "".join(
        f'<span class="flsc-legend__item">{status_badge(s)} {notes[s]}</span>'
        for s in STATUS_ORDER
    )
    return f'<div class="flsc-legend">{items}</div>'


# ---------------------------------------------------------------------------
# Classification strip + status distribution
# ---------------------------------------------------------------------------

def classification_html(height_class: str, category: str,
                        branches: list) -> str:
    """branches: (chapter code, readable table / row label, rule id or None). The
    printed table / row is shown; the rule id only as a hover title (audit UX-14).
    A chapter with no matched row reads 'general rules', not an empty chip."""
    chips = []
    for entry in branches:
        code, label = entry[0], entry[1]
        rule = entry[2] if len(entry) > 2 else None
        cls = "flsc-branch" + ("" if label else " flsc-branch--none")
        title = f' title="rule {esc(rule)}"' if rule else ""
        chips.append(
            f'<span class="{cls}"{title}><b>{esc(code)}</b>'
            f'<code>{esc(label) if label else "general rules"}</code></span>'
        )
    return (
        '<div class="flsc-class">'
        '<div class="flsc-class__hero">'
        '<small>Height class</small>'
        f'<strong>{esc(height_class.replace("_", " ").title())}</strong>'
        f'<em>Category {esc(category.replace("_", " "))}</em>'
        '</div>'
        f'<div class="flsc-class__branches">{"".join(chips)}</div>'
        '</div>'
    )


def requirements_table_html(items, show_rule_ids: bool = False) -> str:
    """Compact table view of one block of requirements (audit UX-13): system,
    status, spec and citation in one wrapping row each."""
    head = ("<tr><th>System</th><th>Status</th><th>Specification / detail</th>"
            "<th>Code ref</th></tr>")
    rows = []
    for r in items:
        spec = esc(r.spec or "")
        det = esc(r.detail or "")
        body = spec + (("<br><small>" + det + "</small>") if det else "")
        cite = " · ".join(esc(x) for x in (r.code_ref, r.page_ref) if x)
        if show_rule_ids and getattr(r, "source_rule", None):
            cite += f"<br><small>rule {esc(r.source_rule)}</small>"
        rows.append(
            f'<tr><td class="flsc-rtable__sys">{esc(r.system)}</td>'
            f'<td class="flsc-rtable__st">{status_badge(r.status)}</td>'
            f'<td>{body or "-"}</td><td class="flsc-rtable__cite">{cite or "-"}</td></tr>')
    return f'<table class="flsc-rtable">{head}{"".join(rows)}</table>'


def status_summary_html(counts: dict[str, int]) -> str:
    total = sum(counts.get(s, 0) for s in STATUS_ORDER) or 1
    segs, legend = [], []
    seg_colors = {"required": "#DC2626", "recommended": "#2563EB",
                  "conditional": "#F59E0B", "not_required": "#CBD5E1", "not_evaluated": "#7C3AED"}
    for s in STATUS_ORDER:
        n = counts.get(s, 0)
        label = STATUS_META[s][0]
        if n:
            segs.append(
                f'<span class="flsc-statusbar__seg" '
                f'style="flex:{n};background:{seg_colors[s]};" title="{label}: {n}"></span>'
            )
        legend.append(f'<span><b>{n}</b> {label.lower()}</span>')
    return (
        '<div class="flsc-statusbar">'
        f'<div class="flsc-statusbar__track">{"".join(segs)}</div>'
        f'<div class="flsc-statusbar__legend">{"".join(legend)}'
        f'<span style="margin-left:auto"><b>{total}</b> total line items</span></div>'
        '</div>'
    )


# ---------------------------------------------------------------------------
# Chapter headers & TOC
# ---------------------------------------------------------------------------

def chapter_header(code: str, title: str, arabic: str | None = None,
                   anchor: str | None = None, parking: bool = False) -> str:
    ar = f'<div class="flsc-chapter__ar">{esc(arabic)}</div>' if arabic else ""
    aid = f' id="{esc(anchor)}"' if anchor else ""
    cls = "flsc-chapter flsc-chapter--parking" if parking else "flsc-chapter"
    return (
        f'<div class="{cls}"{aid}>'
        f'<span class="flsc-chapter__code">{esc(code)}</span>'
        f'<div><div class="flsc-chapter__title">{esc(title)}</div>{ar}</div>'
        '</div>'
    )


def toc_html(rows: list[tuple[str, str, str, dict[str, int] | None]]) -> str:
    """rows: (anchor, code, short_title, counts-or-None)."""
    out = ['<div class="flsc-toc"><div class="flsc-toc__head">Report contents</div>']
    for anchor, code, short, counts in rows:
        pills = ""
        if counts:
            pills = "".join(count_pill(s, counts[s]) for s in STATUS_ORDER if counts.get(s))
        out.append(
            f'<a class="flsc-toc__row" href="#{esc(anchor)}">'
            f'<span>{esc(code)} · {esc(short)}</span>'
            f'<span class="flsc-toc__counts">{pills}</span></a>'
        )
    out.append('</div>')
    return "".join(out)


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

def footer_html(disclaimer: str) -> str:
    return (
        '<div class="flsc-footer">'
        f'<strong>⚖️ Disclaimer.</strong> {esc(disclaimer)}'
        '<div class="flsc-footer__meta">'
        '<span>UAE FLSC 2018 · CDGH-OP-25 · September 2018</span>'
        '<span>Chapters loaded: FSA · MOE · FE · ES · EL · EVC · FA · FP · SC · LPG · ACC · EAP</span>'
        '<span>Created by Hussein Ragab · <a href="https://www.linkedin.com/in/husseinragab" target="_blank">LinkedIn</a></span>'
        '</div></div>'
    )
