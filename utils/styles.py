"""RetailIQ — Styles & HTML component helpers."""

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Sarabun', sans-serif !important;
}

/* ── Layout ── */
.main .block-container { padding-top: 1rem !important; max-width: 1200px; }
header[data-testid="stHeader"] { background: rgba(15,23,42,0.95); }

/* ── KPI Cards ── */
.kpi-card {
    background: linear-gradient(135deg, rgba(30,41,59,0.9), rgba(15,23,42,0.95));
    border: 1px solid rgba(99,102,241,0.2);
    border-radius: 12px;
    padding: 18px 20px;
    text-align: center;
    backdrop-filter: blur(8px);
    transition: border-color 0.2s;
}
.kpi-card:hover { border-color: rgba(99,102,241,0.5); }
.kpi-icon { font-size: 1.6rem; margin-bottom: 4px; }
.kpi-value { font-size: 1.55rem; font-weight: 700; color: #e2e8f0; margin: 2px 0; }
.kpi-label { font-size: 0.78rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }

/* ── Section Headers ── */
.section-header {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 0 6px;
    border-bottom: 1px solid rgba(99,102,241,0.2);
    margin-bottom: 12px;
}
.section-title { font-size: 1.05rem; font-weight: 600; color: #c7d2fe; margin: 0; }

/* ── Chart Card ── */
.chart-card {
    background: rgba(15,23,42,0.6);
    border: 1px solid rgba(99,102,241,0.15);
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
}

/* ── RFM Badge ── */
.rfm-badge {
    display: inline-block; padding: 2px 10px;
    border-radius: 20px; font-size: 0.75rem; font-weight: 600;
    letter-spacing: 0.03em;
}

/* ── Call Card ── */
.call-card {
    background: rgba(30,41,59,0.8);
    border-left: 3px solid #f59e0b;
    border-radius: 8px;
    padding: 12px 14px;
    margin-bottom: 8px;
}
.call-card.critical { border-left-color: #ef4444; }
.call-card.medium   { border-left-color: #3b82f6; }
.call-script {
    font-size: 0.82rem; color: #94a3b8;
    background: rgba(0,0,0,0.2); border-radius: 6px;
    padding: 8px 10px; margin-top: 6px;
    font-style: italic;
}

/* ── OOS Alert ── */
.oos-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 8px 12px; border-radius: 8px;
    background: rgba(30,41,59,0.5);
    margin-bottom: 6px; font-size: 0.85rem;
}
.urgency-critical { color: #ef4444; font-weight: 700; }
.urgency-high     { color: #f59e0b; font-weight: 600; }
.urgency-medium   { color: #3b82f6; }

/* ── Calendar ── */
.calendar-grid {
    display: grid; grid-template-columns: repeat(7, 1fr);
    gap: 4px; margin-top: 8px;
}
.cal-day {
    background: rgba(30,41,59,0.5); border-radius: 6px;
    padding: 6px 4px; min-height: 64px; font-size: 0.75rem;
}
.cal-day-num { color: #94a3b8; font-size: 0.7rem; margin-bottom: 3px; }
.cal-chip {
    padding: 2px 4px; border-radius: 4px;
    font-size: 0.65rem; margin-bottom: 2px;
    display: block; text-overflow: ellipsis;
    overflow: hidden; white-space: nowrap;
}
.cal-chip-critical { background: rgba(239,68,68,0.25); color: #fca5a5; }
.cal-chip-high     { background: rgba(245,158,11,0.25); color: #fcd34d; }
.cal-chip-medium   { background: rgba(59,130,246,0.25); color: #93c5fd; }

/* ── Nav ── */
.nav-btn button {
    background: transparent !important;
    border: 1px solid rgba(99,102,241,0.3) !important;
    border-radius: 8px !important; color: #94a3b8 !important;
    font-family: 'Sarabun', sans-serif !important;
}
.nav-btn-active button {
    background: rgba(99,102,241,0.2) !important;
    border-color: #6366f1 !important; color: #c7d2fe !important;
}

/* ── Streamlit overrides ── */
div[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }
.stSelectbox label, .stMultiSelect label { color: #94a3b8 !important; font-size: 0.85rem !important; }
</style>
"""


def inject_css():
    import streamlit as st
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def kpi_card(label: str, value: str, icon: str, sub: str = "") -> str:
    sub_html = f'<div class="kpi-label" style="color:#64748b;margin-top:2px">{sub}</div>' if sub else ""
    return f"""
<div class="kpi-card">
  <div class="kpi-icon">{icon}</div>
  <div class="kpi-value">{value}</div>
  <div class="kpi-label">{label}</div>
  {sub_html}
</div>"""


def section_header(title: str, icon: str = "") -> str:
    return f"""
<div class="section-header">
  <span style="font-size:1.2rem">{icon}</span>
  <p class="section-title">{title}</p>
</div>"""


def rfm_badge(segment: str, color: str) -> str:
    return f'<span class="rfm-badge" style="background:{color}22;color:{color};border:1px solid {color}55">{segment}</span>'


def call_card(rank: int, customer: str, reason: str, script: str, urgency: str) -> str:
    cls = "critical" if urgency == "CRITICAL" else ("medium" if urgency == "MEDIUM" else "")
    return f"""
<div class="call-card {cls}">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <span style="font-weight:600;color:#e2e8f0">#{rank} {customer}</span>
    <span style="font-size:0.78rem;color:#94a3b8">{reason}</span>
  </div>
  <div class="call-script">💬 {script}</div>
</div>"""


def urgency_chip(urgency: str, days: int) -> str:
    cls_map = {"CRITICAL": "urgency-critical", "HIGH": "urgency-high", "MEDIUM": "urgency-medium"}
    label_map = {"CRITICAL": f"🔴 {days}d", "HIGH": f"🟡 {days}d", "MEDIUM": f"🔵 {days}d", "OK": "✅ OK"}
    cls = cls_map.get(urgency, "")
    label = label_map.get(urgency, f"{days}d")
    return f'<span class="{cls}">{label}</span>'
