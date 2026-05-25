"""RetailIQ V2 — Light theme styles."""

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Sarabun', sans-serif !important; }

/* Layout */
.main .block-container { padding-top: 0.75rem !important; max-width: 1280px; background: #f8fafc; }
header[data-testid="stHeader"] { background: #ffffff; border-bottom: 1px solid #e2e8f0; }

/* KPI cards — light */
.kpi-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px 18px;
  text-align: center;
}
.kpi-icon  { font-size: 1.4rem; margin-bottom: 2px; }
.kpi-value { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 2px 0; }
.kpi-label { font-size: 0.75rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }

/* Section header */
.section-header { display:flex; align-items:center; gap:8px; padding: 8px 0 6px;
  border-bottom: 2px solid #e2e8f0; margin-bottom: 10px; }
.section-title { font-size: 0.95rem; font-weight: 600; color: #1e293b; margin: 0; }

/* Chart card */
.chart-card { background: #ffffff; border: 1px solid #e2e8f0;
  border-radius: 12px; padding: 14px; margin-bottom: 10px; }

/* Alert call card */
.call-card { background:#ffffff; border-left:3px solid #c07a00;
  border-radius:0 8px 8px 0; padding:10px 14px; margin-bottom:8px;
  border-top:1px solid #e2e8f0; border-right:1px solid #e2e8f0; border-bottom:1px solid #e2e8f0; }
.call-card.critical { border-left-color: #c0392b; }
.call-card.medium   { border-left-color: #1a6faf; }
.call-script { font-size:0.8rem; color:#475569; background:#f8fafc;
  border-radius:6px; padding:7px 10px; margin-top:5px; font-style:italic; }

/* Item rows */
.item-row { display:flex; align-items:center; padding:8px 12px;
  border-radius:8px; background:#ffffff; border:1px solid #e2e8f0; margin-bottom:5px; }
.item-rank { font-size:0.7rem; color:#94a3b8; width:24px; flex-shrink:0; }
.item-name { flex:1; font-size:0.85rem; color:#1e293b; font-weight:500; }
.item-rev  { font-size:0.85rem; color:#1a6faf; font-weight:600; }
.item-pct  { font-size:0.75rem; color:#64748b; margin-left:8px; }

/* Badges */
.div-badge { display:inline-block; padding:2px 10px; border-radius:20px;
  font-size:0.72rem; font-weight:600; letter-spacing:0.03em; }
.div-dry  { background:#dbeafe; color:#1e40af; }
.div-fresh{ background:#dcfce7; color:#166534; }
.div-non  { background:#fef9c3; color:#854d0e; }

.urgency-badge { display:inline-block; padding:2px 8px; border-radius:12px;
  font-size:0.72rem; font-weight:600; }
.urg-critical { background:#fee2e2; color:#991b1b; }
.urg-high     { background:#fef3c7; color:#92400e; }
.urg-medium   { background:#dbeafe; color:#1e40af; }

/* Nav active */
div[data-testid="stHorizontalBlock"] button[kind="primary"] {
  background: #1a6faf !important; color: white !important; }

/* Streamlit overrides */
.stDataFrame { border-radius:8px; overflow:hidden; }
div[data-testid="stSelectbox"] label,
div[data-testid="stMultiSelect"] label { color:#475569 !important; font-size:0.85rem !important; }
h1,h2,h3 { color:#1e293b !important; }
</style>
"""

def inject_css():
    import streamlit as st
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def kpi_card(label, value, icon, sub=""):
    sub_html = f'<div class="kpi-label" style="color:#94a3b8;margin-top:2px">{sub}</div>' if sub else ""
    return f'<div class="kpi-card"><div class="kpi-icon">{icon}</div><div class="kpi-value">{value}</div><div class="kpi-label">{label}</div>{sub_html}</div>'


def section_header(title, icon=""):
    return f'<div class="section-header"><span style="font-size:1.1rem">{icon}</span><p class="section-title">{title}</p></div>'


def div_badge(division):
    cls = {"DRY FOOD":"div-dry","FRESH FOOD":"div-fresh","NON FOOD":"div-non"}.get(division,"div-dry")
    short = {"DRY FOOD":"DRY","FRESH FOOD":"FRESH","NON FOOD":"NON-FOOD"}.get(division, division)
    return f'<span class="div-badge {cls}">{short}</span>'


def urgency_badge(urgency):
    cls = {"CRITICAL":"urg-critical","HIGH":"urg-high","MEDIUM":"urg-medium"}.get(urgency,"urg-medium")
    label = {"CRITICAL":"🔴 วิกฤต","HIGH":"🟡 เร่งด่วน","MEDIUM":"🔵 ติดตาม"}.get(urgency, urgency)
    return f'<span class="urgency-badge {cls}">{label}</span>'


def call_card(rank, customer, reason, script, urgency):
    cls = "critical" if urgency=="CRITICAL" else ("medium" if urgency=="MEDIUM" else "")
    return f"""<div class="call-card {cls}">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <span style="font-weight:600;color:#1e293b;font-size:0.9rem">#{rank} {customer}</span>
    <span style="font-size:0.76rem;color:#64748b">{reason}</span>
  </div>
  <div class="call-script">💬 {script}</div>
</div>"""
