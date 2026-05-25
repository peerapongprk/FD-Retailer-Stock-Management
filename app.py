"""
RetailIQ — Trusted Inventory Companion
Streamlit app · FD Retailer CRM & Predictive OOS
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar

# ── page config (must be first) ──────────────────────────────────────────────
st.set_page_config(
    page_title="RetailIQ",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from utils.styles import inject_css, kpi_card, section_header, rfm_badge, call_card, urgency_chip
from utils.charts import (revenue_trend_chart, rfm_donut, top_items_bar,
                           customer_revenue_bar, dept_pie, oos_urgency_bar)
from utils.data_engine import (clean_data, compute_kpis, monthly_trend, compute_rfm,
                                predict_oos, top5_calls_today, generate_visit_plan,
                                customer_monthly, customer_top_items, customer_dept_mix)
from database.persistence import (save_batch, load_combined_df, load_all_batches,
                                   delete_batch, rename_batch, check_date_overlap,
                                   get_users, add_user, delete_user,
                                   get_portfolio, add_to_portfolio, remove_from_portfolio)
from database.schema import MAKRO, RFM_COLOR, RFM_ADVICE, RFM

inject_css()

# ── session state defaults ────────────────────────────────────────────────────
_DEFAULTS = {
    "page": "home",
    "prev_page": "home",
    "df": None,
    "pending_upload": None,
    "selected_user_id": None,
    "selected_user": None,
    "detail_cust_id": None,
    "detail_cust_name": None,
    "my_page_sub": "overview",
    "rfm_df": None,
    "oos_df": None,
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── helpers ───────────────────────────────────────────────────────────────────

def go(page: str, **kwargs):
    st.session_state.prev_page = st.session_state.page
    st.session_state.page = page
    for k, v in kwargs.items():
        st.session_state[k] = v
    st.rerun()


def _reload_master():
    st.session_state.df = load_combined_df()
    st.session_state.rfm_df = None
    st.session_state.oos_df = None


def _get_df() -> pd.DataFrame:
    if st.session_state.df is None or st.session_state.df.empty:
        _reload_master()
    return st.session_state.df if st.session_state.df is not None else pd.DataFrame()


@st.cache_data(ttl=300)
def _cached_rfm(df_hash: int, _df: pd.DataFrame) -> pd.DataFrame:
    return compute_rfm(_df)


@st.cache_data(ttl=300)
def _cached_oos(df_hash: int, _df: pd.DataFrame) -> pd.DataFrame:
    return predict_oos(_df)


def _get_rfm(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    if st.session_state.rfm_df is None:
        st.session_state.rfm_df = compute_rfm(df)
    return st.session_state.rfm_df


def _get_oos(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    if st.session_state.oos_df is None:
        st.session_state.oos_df = predict_oos(df)
    return st.session_state.oos_df


def fmt_thb(v: float) -> str:
    if v >= 1_000_000:
        return f"฿{v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"฿{v/1_000:.1f}K"
    return f"฿{v:,.0f}"


# ── TOP NAV ───────────────────────────────────────────────────────────────────

def render_nav():
    users = get_users()
    user_options = ["— ทุกคน —"] + [u["name"] for u in users]

    c_logo, c_home, c_mypage, c_db, c_spacer, c_user = st.columns([1.2, 1, 1, 1, 3, 2])

    with c_logo:
        st.markdown("### 🏪 RetailIQ")

    page = st.session_state.page
    with c_home:
        if st.button("🏠 Home", use_container_width=True,
                     type="primary" if page == "home" else "secondary"):
            go("home")
    with c_mypage:
        if st.button("👤 My Page", use_container_width=True,
                     type="primary" if page == "my_page" else "secondary"):
            go("my_page")
    with c_db:
        if st.button("🗄️ Database", use_container_width=True,
                     type="primary" if page == "database" else "secondary"):
            go("database")

    with c_user:
        sel = st.selectbox("", user_options, label_visibility="collapsed",
                           key="nav_user_select")
        if sel == "— ทุกคน —":
            st.session_state.selected_user_id = None
            st.session_state.selected_user = None
        else:
            for u in users:
                if u["name"] == sel:
                    st.session_state.selected_user_id = u["id"]
                    st.session_state.selected_user = u["name"]

    st.divider()


# ── PAGE: HOME ────────────────────────────────────────────────────────────────

def page_home():
    df = _get_df()

    if df.empty:
        st.info("ยังไม่มีข้อมูล — ไปที่ 🗄️ Database เพื่ออัปโหลดไฟล์")
        st.stop()

    rfm_df = _get_rfm(df)
    oos_df = _get_oos(df)

    # ── KPIs ──
    st.markdown(section_header("ภาพรวม FD Retailer", "📊"), unsafe_allow_html=True)
    kpis = compute_kpis(df)
    cols = st.columns(6)
    cards = [
        ("ยอดขายรวม",      fmt_thb(kpis.get("revenue",0)),   "💰"),
        ("กำไรรวม",         fmt_thb(kpis.get("profit",0)),    "📈"),
        ("Margin",           f"{kpis.get('margin',0):.1f}%",  "🎯"),
        ("ลูกค้าทั้งหมด",   str(kpis.get("customers",0)),    "🏪"),
        ("Active (ล่าสุด)",  str(kpis.get("active",0)),       "✅"),
        ("SKU รวม",          str(kpis.get("items",0)),        "📦"),
    ]
    for col, (label, val, icon) in zip(cols, cards):
        with col:
            st.markdown(kpi_card(label, val, icon), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 1: Trend + RFM ──
    col_trend, col_rfm = st.columns([3, 2])
    with col_trend:
        st.markdown(section_header("ยอดขายรายเดือน", "📅"), unsafe_allow_html=True)
        with st.container():
            trend = monthly_trend(df)
            if not trend.empty:
                st.plotly_chart(revenue_trend_chart(trend),
                                use_container_width=True, config={"displayModeBar": False})

    with col_rfm:
        st.markdown(section_header("RFM Segment", "🎨"), unsafe_allow_html=True)
        if not rfm_df.empty:
            st.plotly_chart(rfm_donut(rfm_df),
                            use_container_width=True, config={"displayModeBar": False})
            # Segment summary
            for seg, grp in rfm_df.groupby("segment"):
                color = RFM_COLOR.get(seg, "#6b7280")
                advice = RFM_ADVICE.get(seg, "")
                st.markdown(
                    f'{rfm_badge(seg, color)} <span style="color:#94a3b8;font-size:0.78rem">'
                    f'({len(grp)} ร้าน) — {advice}</span>',
                    unsafe_allow_html=True
                )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 2: Top 5 Calls + OOS Alerts ──
    col_calls, col_oos = st.columns([2, 3])

    with col_calls:
        st.markdown(section_header("Top 5 Calls วันนี้", "📞"), unsafe_allow_html=True)
        calls = top5_calls_today(df, oos_df, rfm_df)
        if not calls.empty:
            for i, row in calls.iterrows():
                urg = row.get("urgency", "HIGH")
                st.markdown(
                    call_card(i, row[MAKRO.CUSTOMER], row["reason"], row["script"], urg),
                    unsafe_allow_html=True
                )
        else:
            st.info("ไม่มี Alert เร่งด่วนวันนี้ 🎉")

    with col_oos:
        st.markdown(section_header("OOS Prediction — ต้องเติมสต็อก", "⚠️"), unsafe_allow_html=True)
        if not oos_df.empty:
            urgent = oos_df[oos_df["urgency"].isin(["CRITICAL", "HIGH", "MEDIUM"])].head(15)
            if not urgent.empty:
                st.plotly_chart(oos_urgency_bar(urgent),
                                use_container_width=True, config={"displayModeBar": False})

                # Expandable table
                with st.expander("ดูรายละเอียด OOS ทั้งหมด"):
                    display = urgent[[MAKRO.CUSTOMER, MAKRO.ITEM, MAKRO.CLASS,
                                      "days_until_runout", "urgency", "avg_monthly_spend"]].copy()
                    display.columns = ["ลูกค้า", "สินค้า", "Class", "วันที่เหลือ", "ระดับ", "ยอดซื้อ/เดือน"]
                    display["ยอดซื้อ/เดือน"] = display["ยอดซื้อ/เดือน"].apply(fmt_thb)
                    st.dataframe(display, use_container_width=True, hide_index=True)
        else:
            st.success("ไม่พบสินค้าที่ใกล้หมดสต็อก")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── RFM Customer Table ──
    st.markdown(section_header("รายชื่อลูกค้า FD Retailer", "🏪"), unsafe_allow_html=True)

    seg_filter = st.multiselect(
        "Filter Segment",
        [RFM.CHAMPION, RFM.LOYAL, RFM.PROMISING, RFM.AT_RISK, RFM.CHURNING, RFM.NEW],
        default=[], label_visibility="collapsed",
        placeholder="แสดงทุก Segment"
    )

    show_rfm = rfm_df.copy() if not rfm_df.empty else pd.DataFrame()
    if seg_filter and not show_rfm.empty:
        show_rfm = show_rfm[show_rfm["segment"].isin(seg_filter)]

    if not show_rfm.empty:
        for _, row in show_rfm.iterrows():
            color = RFM_COLOR.get(row["segment"], "#6b7280")
            col_name, col_seg, col_rev, col_margin, col_btn = st.columns([3, 1.5, 1.5, 1.2, 1])
            with col_name:
                st.markdown(f"**{row[MAKRO.CUSTOMER]}**", unsafe_allow_html=True)
                st.caption(f"#{row[MAKRO.CUST_NUM]}")
            with col_seg:
                st.markdown(rfm_badge(row["segment"], color), unsafe_allow_html=True)
            with col_rev:
                st.markdown(fmt_thb(row["revenue"]))
            with col_margin:
                st.markdown(f"{row['margin_pct']:.1f}%")
            with col_btn:
                if st.button("ดูรายละเอียด", key=f"view_{row[MAKRO.CUST_NUM]}"):
                    go("customer_detail",
                       detail_cust_id=row[MAKRO.CUST_NUM],
                       detail_cust_name=row[MAKRO.CUSTOMER])
            st.divider()


# ── PAGE: CUSTOMER DETAIL ─────────────────────────────────────────────────────

def page_customer_detail():
    cust_id   = st.session_state.detail_cust_id
    cust_name = st.session_state.detail_cust_name
    df = _get_df()

    # Back button
    prev = st.session_state.prev_page
    if st.button(f"← กลับ", type="secondary"):
        go(prev)

    if df.empty or cust_id is None:
        st.warning("ไม่พบข้อมูลลูกค้า")
        st.stop()

    cust_df = df[df[MAKRO.CUST_NUM] == cust_id]
    if cust_df.empty:
        st.warning("ไม่พบข้อมูลลูกค้า")
        st.stop()

    rfm_df = _get_rfm(df)
    oos_df = _get_oos(df)

    # Header
    cust_info = cust_df.iloc[0]
    rfm_row = rfm_df[rfm_df[MAKRO.CUST_NUM] == cust_id]
    segment = rfm_row["segment"].values[0] if not rfm_row.empty else "—"
    color = RFM_COLOR.get(segment, "#6b7280")

    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f"## 🏪 {cust_name}")
        st.markdown(f'Type: **{cust_info[MAKRO.CUST_TYPE]}** &nbsp; {rfm_badge(segment, color)}',
                    unsafe_allow_html=True)
    with col_h2:
        if not rfm_row.empty:
            r = rfm_row.iloc[0]
            st.metric("ยอดขายรวม", fmt_thb(r["revenue"]))
            st.metric("Margin", f"{r['margin_pct']:.1f}%")

    st.divider()

    # ── KPI row ──
    if not rfm_row.empty:
        r = rfm_row.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(kpi_card("ยอดขายรวม", fmt_thb(r["revenue"]), "💰"), unsafe_allow_html=True)
        with c2: st.markdown(kpi_card("กำไร", fmt_thb(r["profit"]), "📈"), unsafe_allow_html=True)
        with c3: st.markdown(kpi_card("เดือนที่ซื้อ", f"{int(r['freq'])}/{df['_date'].nunique()}", "📅"), unsafe_allow_html=True)
        with c4: st.markdown(kpi_card("SKU ที่ซื้อ", str(int(r["items_count"])), "📦"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts row ──
    col_monthly, col_dept = st.columns([3, 2])
    with col_monthly:
        st.markdown(section_header("ยอดซื้อรายเดือน", "📊"), unsafe_allow_html=True)
        monthly = customer_monthly(df, cust_id)
        if not monthly.empty:
            st.plotly_chart(customer_revenue_bar(monthly),
                            use_container_width=True, config={"displayModeBar": False})

    with col_dept:
        st.markdown(section_header("สัดส่วนตาม Department", "🥧"), unsafe_allow_html=True)
        dept = customer_dept_mix(df, cust_id)
        if not dept.empty:
            st.plotly_chart(dept_pie(dept), use_container_width=True, config={"displayModeBar": False})

    st.markdown("<br>", unsafe_allow_html=True)

    # ── OOS for this customer ──
    cust_oos = oos_df[oos_df[MAKRO.CUST_NUM] == cust_id] if not oos_df.empty else pd.DataFrame()
    if not cust_oos.empty:
        st.markdown(section_header("⚠️ สินค้าที่ต้องสั่งเพิ่ม (OOS Prediction)", ""), unsafe_allow_html=True)
        for _, row in cust_oos.iterrows():
            d = int(row["days_until_runout"])
            chip = urgency_chip(row["urgency"], d)
            col_item, col_class, col_days, col_spend, col_script = st.columns([3, 1.5, 1, 1.2, 2])
            with col_item: st.markdown(f"**{row[MAKRO.ITEM]}**")
            with col_class: st.caption(row[MAKRO.CLASS])
            with col_days: st.markdown(chip, unsafe_allow_html=True)
            with col_spend: st.caption(fmt_thb(row["avg_monthly_spend"]))
            with col_script:
                if d <= 0:
                    txt = f"หมดแล้ว — สั่งด่วน!"
                else:
                    txt = f"ส่งใน {d} วัน ก่อนหมด"
                st.caption(f"💬 {txt}")
            st.divider()

    # ── Top items ──
    st.markdown(section_header("สินค้าที่ซื้อบ่อย", "🛒"), unsafe_allow_html=True)
    items = customer_top_items(df, cust_id)
    if not items.empty:
        st.plotly_chart(top_items_bar(items), use_container_width=True, config={"displayModeBar": False})
        with st.expander("ดูตารางรายสินค้า"):
            display = items.copy()
            display["Revenue"] = display["Revenue"].apply(fmt_thb)
            display["Profit"]  = display["Profit"].apply(fmt_thb)
            st.dataframe(display, use_container_width=True, hide_index=True)


# ── PAGE: MY PAGE ─────────────────────────────────────────────────────────────

def page_my_page():
    user_id   = st.session_state.selected_user_id
    user_name = st.session_state.selected_user

    if user_id is None:
        st.info("เลือก Salesperson จากเมนูด้านบนเพื่อดู My Page")
        st.stop()

    st.markdown(f"## 👤 {user_name}")
    portfolio_ids = get_portfolio(user_id)
    st.caption(f"Portfolio: {len(portfolio_ids)} ร้านค้า")

    # Sub-nav
    sub = st.session_state.my_page_sub
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("📊 Overview",   use_container_width=True,
                     type="primary" if sub == "overview" else "secondary"):
            st.session_state.my_page_sub = "overview"; st.rerun()
    with c2:
        if st.button("📅 Calendar",   use_container_width=True,
                     type="primary" if sub == "calendar" else "secondary"):
            st.session_state.my_page_sub = "calendar"; st.rerun()
    with c3:
        if st.button("🏪 Portfolio",  use_container_width=True,
                     type="primary" if sub == "portfolio" else "secondary"):
            st.session_state.my_page_sub = "portfolio"; st.rerun()

    st.divider()
    df = _get_df()

    # ── Sub: Overview ──
    if st.session_state.my_page_sub == "overview":
        if df.empty:
            st.info("ยังไม่มีข้อมูล")
            st.stop()

        port_df = df[df[MAKRO.CUST_NUM].isin(portfolio_ids)] if portfolio_ids else df
        if port_df.empty:
            st.info("ไม่มีข้อมูลสำหรับ Portfolio นี้")
            st.stop()

        kpis = compute_kpis(port_df)
        cols = st.columns(4)
        for col, (label, val, icon) in zip(cols, [
            ("ยอดขาย",   fmt_thb(kpis["revenue"]),         "💰"),
            ("กำไร",      fmt_thb(kpis["profit"]),          "📈"),
            ("ลูกค้า",    str(kpis["customers"]),           "🏪"),
            ("Margin",    f"{kpis['margin']:.1f}%",         "🎯"),
        ]):
            with col:
                st.markdown(kpi_card(label, val, icon), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        rfm_port  = compute_rfm(port_df)
        oos_port  = predict_oos(port_df)
        calls     = top5_calls_today(port_df, oos_port, rfm_port)

        col_calls, col_trend = st.columns([2, 3])
        with col_calls:
            st.markdown(section_header("Top 5 Calls ของคุณ", "📞"), unsafe_allow_html=True)
            if not calls.empty:
                for i, row in calls.iterrows():
                    st.markdown(
                        call_card(i, row[MAKRO.CUSTOMER], row["reason"], row["script"], row.get("urgency","HIGH")),
                        unsafe_allow_html=True
                    )
            else:
                st.success("ไม่มี Alert วันนี้ 🎉")

        with col_trend:
            st.markdown(section_header("ยอดขาย Portfolio รายเดือน", "📅"), unsafe_allow_html=True)
            trend = monthly_trend(port_df)
            if not trend.empty:
                st.plotly_chart(revenue_trend_chart(trend),
                                use_container_width=True, config={"displayModeBar": False})

    # ── Sub: Calendar ──
    elif st.session_state.my_page_sub == "calendar":
        st.markdown(section_header("Smart Replenishment Calendar", "📅"), unsafe_allow_html=True)

        if df.empty or not portfolio_ids:
            st.info("ยังไม่มีข้อมูลหรือ Portfolio ว่างเปล่า")
            st.stop()

        port_df  = df[df[MAKRO.CUST_NUM].isin(portfolio_ids)]
        oos_port = predict_oos(port_df)
        rfm_port = compute_rfm(port_df)

        # Calendar month selector
        today = datetime.now()
        col_m, col_y, _ = st.columns([1, 1, 4])
        with col_m:
            month = st.selectbox("เดือน", range(1, 13), index=today.month - 1,
                                 format_func=lambda m: ["ม.ค.","ก.พ.","มี.ค.","เม.ย.","พ.ค.","มิ.ย.",
                                                         "ก.ค.","ส.ค.","ก.ย.","ต.ค.","พ.ย.","ธ.ค."][m-1])
        with col_y:
            year = st.selectbox("ปี", [2025, 2026, 2027], index=1)

        # Build calendar data
        cal_events = {}  # date_str → list of events
        if not oos_port.empty:
            for _, row in oos_port.iterrows():
                rd = row["predicted_runout"]
                alert_date = (pd.Timestamp(rd) - pd.Timedelta(days=3)).strftime("%Y-%m-%d")
                if alert_date not in cal_events:
                    cal_events[alert_date] = []
                cal_events[alert_date].append({
                    "label": f"{row[MAKRO.CUSTOMER][:12]} / {row[MAKRO.ITEM][:15]}",
                    "urgency": row["urgency"],
                })

        # Render calendar
        month_cal = calendar.monthcalendar(year, month)
        day_names = ["จ.", "อ.", "พ.", "พฤ.", "ศ.", "ส.", "อา."]
        cols = st.columns(7)
        for i, dn in enumerate(day_names):
            cols[i].markdown(f"<div style='text-align:center;color:#6366f1;font-weight:600;font-size:0.8rem'>{dn}</div>",
                             unsafe_allow_html=True)

        for week in month_cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                with cols[i]:
                    if day == 0:
                        st.markdown("<div style='min-height:70px'></div>", unsafe_allow_html=True)
                        continue
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    is_today = (date_str == today.strftime("%Y-%m-%d"))
                    border = "border:1px solid #6366f1;" if is_today else "border:1px solid rgba(99,102,241,0.1);"
                    day_html = f"""<div style="background:rgba(15,23,42,0.6);border-radius:6px;
                        padding:5px;min-height:70px;{border}">
                        <div style="color:#94a3b8;font-size:0.7rem;margin-bottom:3px">
                            {'<b style="color:#6366f1">' if is_today else ''}{day}{'</b>' if is_today else ''}
                        </div>"""
                    if date_str in cal_events:
                        for ev in cal_events[date_str][:3]:
                            chip_color = {"CRITICAL":"rgba(239,68,68,0.3)", "HIGH":"rgba(245,158,11,0.3)"}.get(
                                ev["urgency"], "rgba(59,130,246,0.3)")
                            text_color = {"CRITICAL":"#fca5a5","HIGH":"#fcd34d"}.get(ev["urgency"],"#93c5fd")
                            day_html += (f'<div style="background:{chip_color};color:{text_color};'
                                         f'border-radius:4px;padding:2px 3px;font-size:0.6rem;'
                                         f'margin-bottom:2px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis">'
                                         f'{ev["label"]}</div>')
                    day_html += "</div>"
                    st.markdown(day_html, unsafe_allow_html=True)

        # Legend + OOS list
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            '<span style="background:rgba(239,68,68,0.3);color:#fca5a5;padding:3px 8px;border-radius:4px;font-size:0.8rem">🔴 Critical</span> &nbsp;'
            '<span style="background:rgba(245,158,11,0.3);color:#fcd34d;padding:3px 8px;border-radius:4px;font-size:0.8rem">🟡 High</span> &nbsp;'
            '<span style="background:rgba(59,130,246,0.3);color:#93c5fd;padding:3px 8px;border-radius:4px;font-size:0.8rem">🔵 Medium</span>'
            '<span style="color:#94a3b8;font-size:0.78rem"> — แสดงก่อนสต็อกหมด 3 วัน</span>',
            unsafe_allow_html=True
        )

        if not oos_port.empty:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(section_header("รายการ OOS ใน Portfolio", "⚠️"), unsafe_allow_html=True)
            display = oos_port[[MAKRO.CUSTOMER, MAKRO.ITEM, MAKRO.CLASS,
                                 "days_until_runout", "urgency", "avg_monthly_spend"]].copy()
            display.columns = ["ลูกค้า", "สินค้า", "Class", "วันที่เหลือ", "ระดับ", "ยอด/เดือน"]
            display["ยอด/เดือน"] = display["ยอด/เดือน"].apply(fmt_thb)
            st.dataframe(display, use_container_width=True, hide_index=True)

    # ── Sub: Portfolio ──
    elif st.session_state.my_page_sub == "portfolio":
        st.markdown(section_header("จัดการ Portfolio", "🏪"), unsafe_allow_html=True)

        if df.empty:
            st.info("ยังไม่มีข้อมูล")
            st.stop()

        rfm_all = _get_rfm(df)
        search  = st.text_input("🔍 ค้นหาร้านค้า", placeholder="ชื่อร้าน หรือ รหัสลูกค้า")

        show = rfm_all.copy()
        if search:
            mask = (show[MAKRO.CUSTOMER].str.contains(search, na=False) |
                    show[MAKRO.CUST_NUM].astype(str).str.contains(search, na=False))
            show = show[mask]

        for _, row in show.iterrows():
            cid   = row[MAKRO.CUST_NUM]
            color = RFM_COLOR.get(row["segment"], "#6b7280")
            in_port = str(cid) in [str(p) for p in portfolio_ids]

            ca, cb, cc, cd, ce = st.columns([3, 1.5, 1.5, 1.5, 1])
            with ca:
                st.markdown(f"**{row[MAKRO.CUSTOMER]}**")
                st.caption(f"#{cid}")
            with cb:
                st.markdown(rfm_badge(row["segment"], color), unsafe_allow_html=True)
            with cc:
                st.markdown(fmt_thb(row["revenue"]))
            with cd:
                if st.button("ดูรายละเอียด", key=f"port_view_{cid}"):
                    go("customer_detail", detail_cust_id=cid, detail_cust_name=row[MAKRO.CUSTOMER])
            with ce:
                if in_port:
                    if st.button("➖", key=f"rm_{cid}", help="ถอดออกจาก Portfolio"):
                        remove_from_portfolio(user_id, cid); st.rerun()
                else:
                    if st.button("➕", key=f"add_{cid}", help="เพิ่มเข้า Portfolio"):
                        add_to_portfolio(user_id, cid); st.rerun()
            st.divider()


# ── PAGE: DATABASE ────────────────────────────────────────────────────────────

def page_database():
    st.markdown("## 🗄️ Database Management")

    # ── Upload ──
    st.markdown(section_header("อัปโหลดข้อมูลใหม่", "📤"), unsafe_allow_html=True)
    col_file, col_label = st.columns([3, 2])
    with col_file:
        uploaded = st.file_uploader("เลือกไฟล์ Excel (.xlsx)", type=["xlsx"], label_visibility="collapsed")
    with col_label:
        batch_label = st.text_input("ชื่อ Batch", placeholder="เช่น May 2026")

    if uploaded and st.button("📥 โหลดข้อมูล"):
        with st.spinner("กำลังโหลดและ clean data..."):
            import pandas as pd
            raw = pd.read_excel(uploaded)
            cleaned = clean_data(raw)
            if cleaned.empty:
                st.error("ไม่พบข้อมูล FD Retailer ในไฟล์นี้")
            else:
                date_min = str(cleaned["_date"].min().date())
                date_max = str(cleaned["_date"].max().date())
                overlaps = check_date_overlap(date_min, date_max)
                label = batch_label or uploaded.name

                if overlaps:
                    st.warning(f"⚠️ พบข้อมูลช่วงวันที่ซ้ำกับ {len(overlaps)} batch เดิม")
                    for o in overlaps:
                        st.caption(f"  • {o['label']} ({o['date_min']} – {o['date_max']})")
                    st.session_state.pending_upload = {
                        "label": label, "filename": uploaded.name,
                        "df": cleaned, "overlaps": overlaps,
                        "date_min": date_min, "date_max": date_max,
                    }
                else:
                    save_batch(label, uploaded.name, cleaned)
                    _reload_master()
                    st.success(f"✅ บันทึก {len(cleaned):,} แถว ({date_min} – {date_max})")

    # Overlap confirmation
    if st.session_state.pending_upload:
        pend = st.session_state.pending_upload
        st.error("⚠️ ยืนยันการอัปโหลด — batch เดิมจะถูกลบ")
        ca, cb = st.columns(2)
        with ca:
            if st.button("✅ ยืนยัน — ลบเก่าแล้วบันทึกใหม่", type="primary"):
                for o in pend["overlaps"]:
                    delete_batch(o["id"])
                save_batch(pend["label"], pend["filename"], pend["df"])
                st.session_state.pending_upload = None
                _reload_master()
                st.success("บันทึกเรียบร้อย")
                st.rerun()
        with cb:
            if st.button("❌ ยกเลิก"):
                st.session_state.pending_upload = None; st.rerun()

    st.divider()

    # ── Batch list ──
    st.markdown(section_header("Batches ที่มีอยู่", "📦"), unsafe_allow_html=True)
    batches = load_all_batches()
    if not batches:
        st.info("ยังไม่มีข้อมูล")
    else:
        total_rows = sum(b.get("row_count", 0) for b in batches)
        st.caption(f"รวม {len(batches)} batch · {total_rows:,} แถว")
        for b in batches:
            ca, cb, cc, cd, ce = st.columns([3, 2, 1.5, 1, 1])
            with ca:
                new_label = st.text_input("", value=b["label"], key=f"lbl_{b['id']}",
                                          label_visibility="collapsed")
                if new_label != b["label"] and st.button("💾", key=f"save_{b['id']}"):
                    rename_batch(b["id"], new_label); st.rerun()
            with cb:
                st.caption(f"{b.get('date_min','')} – {b.get('date_max','')}")
            with cc:
                st.caption(f"{b.get('row_count',0):,} แถว")
            with cd:
                st.caption(b.get("created_at","")[:10])
            with ce:
                if st.button("🗑️", key=f"del_{b['id']}", help="ลบ batch นี้"):
                    delete_batch(b["id"]); _reload_master(); st.rerun()

    st.divider()

    # ── User management ──
    st.markdown(section_header("จัดการ Salesperson", "👥"), unsafe_allow_html=True)
    users = get_users()

    col_new, col_btn = st.columns([3, 1])
    with col_new:
        new_name = st.text_input("ชื่อ Salesperson ใหม่", label_visibility="collapsed",
                                 placeholder="ชื่อ Salesperson ใหม่")
    with col_btn:
        if st.button("➕ เพิ่ม") and new_name:
            add_user(new_name.strip()); st.rerun()

    for u in users:
        ca, cb = st.columns([4, 1])
        with ca: st.markdown(f"👤 **{u['name']}**")
        with cb:
            if st.button("🗑️", key=f"du_{u['id']}"):
                delete_user(u["id"]); st.rerun()

    st.divider()

    # ── DB Summary ──
    df = _get_df()
    if not df.empty:
        st.markdown(section_header("สรุปข้อมูลใน Master DB", "📊"), unsafe_allow_html=True)
        kpis = compute_kpis(df)
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("ลูกค้าทั้งหมด", kpis["customers"])
        with c2: st.metric("SKU", kpis["items"])
        with c3: st.metric("ยอดขายรวม", fmt_thb(kpis["revenue"]))
        with c4:
            months = df["_date"].nunique()
            st.metric("เดือนที่มีข้อมูล", months)


# ── ROUTER ────────────────────────────────────────────────────────────────────

render_nav()

page = st.session_state.page

if page == "home":
    page_home()
    st.stop()

if page == "customer_detail":
    page_customer_detail()
    st.stop()

if page == "my_page":
    page_my_page()
    st.stop()

if page == "database":
    page_database()
    st.stop()

# fallback
go("home")
