"""RetailIQ V2 — Trusted Inventory Companion (Light Theme)"""

import streamlit as st
import pandas as pd
from datetime import datetime
import calendar

st.set_page_config(page_title="RetailIQ", page_icon="🏪",
                   layout="wide", initial_sidebar_state="collapsed")

from utils.styles  import inject_css, kpi_card, section_header, div_badge, urgency_badge, call_card
from utils.charts  import (revenue_trend_chart, rfm_donut, top_items_bar, pareto_chart,
                            dow_bar, item_trend_chart, customer_revenue_bar, dept_pie, oos_urgency_bar)
from utils.data_engine import (clean_data, compute_kpis, monthly_trend, compute_rfm,
                                top_items_by_division, pareto_items,
                                item_dow_pattern, item_top_customers, item_monthly_trend,
                                predict_oos, top5_calls_today,
                                customer_monthly, customer_top_items, customer_dept_mix,
                                upsell_suggestions)
from database.persistence import (save_batch, load_combined_df, load_all_batches,
                                   delete_batch, rename_batch, check_date_overlap,
                                   get_users, add_user, delete_user)
from database.schema import MAKRO, RFM_COLOR, RFM_ADVICE

inject_css()

# ── session defaults ──────────────────────────────────────────────────────────
for k, v in {
    "page": "home", "prev_page": "home",
    "df": None, "pending_upload": None,
    "rfm_df": None, "oos_df": None,
    "detail_cust_id": None, "detail_cust_name": None,
    "detail_item": None,
    "home_sub": "overview",   # overview | top_items | alerts
    "top_items_div": "ทั้งหมด",
    "show_pareto_div": None,
}.items():
    if k not in st.session_state: st.session_state[k] = v


# ── helpers ───────────────────────────────────────────────────────────────────

def go(page, **kw):
    st.session_state.prev_page = st.session_state.page
    st.session_state.page = page
    for k, v in kw.items(): st.session_state[k] = v
    st.rerun()

def _reload():
    st.session_state.df = load_combined_df()
    st.session_state.rfm_df = None
    st.session_state.oos_df = None

def _df():
    if st.session_state.df is None or (hasattr(st.session_state.df,"empty") and st.session_state.df.empty):
        _reload()
    return st.session_state.df if st.session_state.df is not None else pd.DataFrame()

def _rfm(df):
    if df.empty: return pd.DataFrame()
    if st.session_state.rfm_df is None:
        st.session_state.rfm_df = compute_rfm(df)
    return st.session_state.rfm_df

def _oos(df):
    if df.empty: return pd.DataFrame()
    if st.session_state.oos_df is None:
        st.session_state.oos_df = predict_oos(df)
    return st.session_state.oos_df

def fmt(v):
    if v >= 1_000_000: return f"฿{v/1_000_000:.1f}M"
    if v >= 1_000:     return f"฿{v/1_000:.1f}K"
    return f"฿{v:,.0f}"


# ── NAV ───────────────────────────────────────────────────────────────────────

def render_nav():
    c_logo, c1, c2, c3, _ = st.columns([1.5, 1, 1, 1, 4])
    with c_logo:
        st.markdown("### 🏪 RetailIQ")
    pg = st.session_state.page
    with c1:
        if st.button("🏠 Overview", use_container_width=True,
                     type="primary" if pg == "home" else "secondary"): go("home")
    with c2:
        if st.button("📅 Calendar", use_container_width=True,
                     type="primary" if pg == "calendar" else "secondary"): go("calendar")
    with c3:
        if st.button("🗄️ Database", use_container_width=True,
                     type="primary" if pg == "database" else "secondary"): go("database")
    st.divider()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: HOME
# ═══════════════════════════════════════════════════════════════════════════════

def page_home():
    df = _df()
    if df.empty:
        st.info("ยังไม่มีข้อมูล — ไปที่ 🗄️ Database เพื่ออัปโหลดไฟล์")
        st.stop()

    rfm_df = _rfm(df)
    oos_df = _oos(df)

    # Sub-nav
    sub = st.session_state.home_sub
    ca, cb, cc, _ = st.columns([1,1,1,5])
    with ca:
        if st.button("📊 ภาพรวม", use_container_width=True,
                     type="primary" if sub=="overview" else "secondary"):
            st.session_state.home_sub = "overview"; st.rerun()
    with cb:
        if st.button("📦 สินค้าขายดี", use_container_width=True,
                     type="primary" if sub=="top_items" else "secondary"):
            st.session_state.home_sub = "top_items"; st.rerun()
    with cc:
        if st.button("🔔 Alerts", use_container_width=True,
                     type="primary" if sub=="alerts" else "secondary"):
            st.session_state.home_sub = "alerts"; st.rerun()
    st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)

    # ── Sub: Overview ──────────────────────────────────────────────────────────
    if sub == "overview":
        kpis = compute_kpis(df)

        # KPI row
        cols = st.columns(6)
        for col, (lbl, val, icon) in zip(cols, [
            ("ยอดขายรวม",   fmt(kpis.get("revenue",0)), "💰"),
            ("กำไรรวม",     fmt(kpis.get("profit",0)),  "📈"),
            ("Margin",       f"{kpis.get('margin',0):.1f}%", "🎯"),
            ("ลูกค้าทั้งหมด", str(kpis.get("customers",0)), "🏪"),
            ("Active เดือนล่าสุด", str(kpis.get("active",0)), "✅"),
            ("SKU รวม",      str(kpis.get("items",0)),   "📦"),
        ]):
            with col: st.markdown(kpi_card(lbl, val, icon), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        col_trend, col_rfm = st.columns([3, 2])
        with col_trend:
            st.markdown(section_header("ยอดขายรายเดือน", "📅"), unsafe_allow_html=True)
            trend = monthly_trend(df)
            if not trend.empty:
                st.plotly_chart(revenue_trend_chart(trend),
                                use_container_width=True, config={"displayModeBar": False})

        with col_rfm:
            st.markdown(section_header("RFM Segment", "🎨"), unsafe_allow_html=True)
            if not rfm_df.empty:
                st.plotly_chart(rfm_donut(rfm_df),
                                use_container_width=True, config={"displayModeBar": False})
                for seg, grp in rfm_df.groupby("segment"):
                    color = RFM_COLOR.get(seg, "#6b7280")
                    advice = RFM_ADVICE.get(seg, "")
                    st.markdown(
                        f'<span style="display:inline-block;background:{color}18;color:{color};'
                        f'border:1px solid {color}44;border-radius:20px;padding:1px 10px;'
                        f'font-size:0.72rem;font-weight:600">{seg}</span>'
                        f' <span style="font-size:0.76rem;color:#64748b">({len(grp)} ร้าน) — {advice}</span>',
                        unsafe_allow_html=True)

        # Today's alerts preview
        st.markdown("<br>", unsafe_allow_html=True)
        calls = top5_calls_today(df, oos_df, rfm_df)
        if not calls.empty:
            st.markdown(section_header("Today's Alerts (Preview)", "📞"), unsafe_allow_html=True)
            for i, row in calls.iterrows():
                st.markdown(call_card(i+1, row[MAKRO.CUSTOMER], row["reason"],
                                      row["script"], row.get("urgency","HIGH")),
                            unsafe_allow_html=True)

    # ── Sub: Top Items ─────────────────────────────────────────────────────────
    elif sub == "top_items":
        _render_top_items(df)

    # ── Sub: Alerts ────────────────────────────────────────────────────────────
    elif sub == "alerts":
        _render_alerts(df, rfm_df, oos_df)


# ── Top Items section ─────────────────────────────────────────────────────────

def _render_top_items(df: pd.DataFrame):
    st.markdown(section_header("สินค้าขายดี 10 อันดับแรก แยก Division", "📦"),
                unsafe_allow_html=True)
    st.caption("กดปุ่ม 'ดู Pareto' เพื่อดู 20% ของสินค้าที่สร้าง 80% ของยอดขาย")

    divs = ["DRY FOOD", "FRESH FOOD", "NON FOOD"]
    div_icons = {"DRY FOOD": "🥫", "FRESH FOOD": "🥬", "NON FOOD": "🧴"}

    for div in divs:
        top = top_items_by_division(df, division=div, n_top=10)
        if top.empty:
            continue

        st.markdown(f"<br>", unsafe_allow_html=True)
        col_hdr, col_btn = st.columns([5, 1])
        with col_hdr:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;padding:4px 0">'
                f'<span style="font-size:1.2rem">{div_icons.get(div,"")}</span>'
                f'<span style="font-size:0.95rem;font-weight:600;color:#1e293b">{div}</span>'
                f'</div>',
                unsafe_allow_html=True)
        with col_btn:
            pareto_key = f"pareto_{div}"
            showing = st.session_state.get(pareto_key, False)
            label = "▲ ซ่อน Pareto" if showing else "📊 ดู Pareto 80%"
            if st.button(label, key=f"btn_{pareto_key}", use_container_width=True):
                st.session_state[pareto_key] = not showing
                st.rerun()

        # Top 10 table
        for idx, row in top.iterrows():
            col_rank, col_name, col_div, col_rev, col_cust, col_btn2 = st.columns([0.4, 4, 1, 1.5, 1, 1.2])
            with col_rank:
                st.markdown(f'<div style="color:#94a3b8;font-size:0.8rem;padding-top:8px">#{idx+1}</div>',
                            unsafe_allow_html=True)
            with col_name:
                st.markdown(f'<div style="padding:6px 0;font-size:0.85rem;color:#1e293b;font-weight:500">{row[MAKRO.ITEM]}</div>',
                            unsafe_allow_html=True)
            with col_div:
                st.markdown(f'<div style="padding:6px 0">{div_badge(row[MAKRO.DIVISION])}</div>',
                            unsafe_allow_html=True)
            with col_rev:
                st.markdown(f'<div style="padding:6px 0;font-size:0.85rem;color:#1a6faf;font-weight:600">{fmt(row["Revenue"])}</div>',
                            unsafe_allow_html=True)
            with col_cust:
                st.markdown(f'<div style="padding:6px 0;font-size:0.8rem;color:#64748b">{int(row["Customers"])} ร้าน</div>',
                            unsafe_allow_html=True)
            with col_btn2:
                if st.button("ดูรายละเอียด", key=f"item_{div}_{idx}"):
                    go("item_detail", detail_item=row[MAKRO.ITEM])
            st.divider()

        # Pareto section (toggle)
        if st.session_state.get(pareto_key, False):
            st.markdown(
                f'<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:14px;margin-bottom:10px">'
                f'<div style="font-size:0.85rem;font-weight:600;color:#1e40af;margin-bottom:8px">'
                f'📊 Pareto Analysis — {div} (สินค้าที่สร้าง 80% ของยอดขาย)</div>',
                unsafe_allow_html=True)

            pareto_df = pareto_items(df, division=div)
            total_items_div = df[df[MAKRO.DIVISION]==div][MAKRO.ITEM].nunique()
            pct_items = len(pareto_df) / total_items_div * 100 if total_items_div else 0

            ca, cb, cc = st.columns(3)
            with ca: st.metric("จำนวน SKU ใน 80%", f"{len(pareto_df):,} รายการ")
            with cb: st.metric("% ของ SKU ทั้งหมด", f"{pct_items:.1f}%")
            with cc: st.metric("SKU ทั้งหมดใน Division", f"{total_items_div:,} รายการ")

            st.plotly_chart(pareto_chart(pareto_df.reset_index()),
                            use_container_width=True, config={"displayModeBar": False})

            # Pareto table (top 20 rows shown, with item detail drill-down)
            st.markdown("**รายการสินค้าใน Pareto (Top 20 แสดง)**")
            show_p = pareto_df.head(20).reset_index()
            for _, prow in show_p.iterrows():
                pc1, pc2, pc3, pc4, pc5, pc6 = st.columns([0.5, 4, 1.2, 1.5, 1.2, 1.2])
                with pc1:
                    st.markdown(f'<div style="color:#94a3b8;font-size:0.75rem;padding-top:6px">#{int(prow["index"])}</div>',
                                unsafe_allow_html=True)
                with pc2:
                    st.markdown(f'<div style="font-size:0.82rem;padding:4px 0;color:#1e293b">{prow[MAKRO.ITEM]}</div>',
                                unsafe_allow_html=True)
                with pc3:
                    st.markdown(f'<div style="font-size:0.78rem;color:#64748b;padding:4px 0">{prow[MAKRO.CLASS]}</div>',
                                unsafe_allow_html=True)
                with pc4:
                    st.markdown(f'<div style="font-size:0.82rem;color:#1a6faf;font-weight:600;padding:4px 0">{fmt(prow["Revenue"])}</div>',
                                unsafe_allow_html=True)
                with pc5:
                    st.markdown(f'<div style="font-size:0.78rem;color:#64748b;padding:4px 0">{prow["CumPct"]:.1f}% cum.</div>',
                                unsafe_allow_html=True)
                with pc6:
                    if st.button("ดูรายละเอียด", key=f"pareto_item_{div}_{_}"):
                        go("item_detail", detail_item=prow[MAKRO.ITEM])
            st.markdown("</div>", unsafe_allow_html=True)


# ── Alerts section ────────────────────────────────────────────────────────────

def _render_alerts(df, rfm_df, oos_df):
    st.markdown(section_header("Today's Alerts — ลูกค้าที่ควรโทรวันนี้", "🔔"),
                unsafe_allow_html=True)

    calls = top5_calls_today(df, oos_df, rfm_df)
    if not calls.empty:
        for i, row in calls.iterrows():
            col_card, col_btn = st.columns([5, 1])
            with col_card:
                st.markdown(call_card(i+1, row[MAKRO.CUSTOMER], row["reason"],
                                      row["script"], row.get("urgency","HIGH")),
                            unsafe_allow_html=True)
            with col_btn:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("ดูลูกค้า", key=f"call_cust_{i}"):
                    go("customer_detail",
                       detail_cust_id=row[MAKRO.CUST_NUM],
                       detail_cust_name=row[MAKRO.CUSTOMER])
    else:
        st.success("ไม่มี Alert เร่งด่วนวันนี้ 🎉")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(section_header("OOS Predictions — รายการทั้งหมด", "⚠️"),
                unsafe_allow_html=True)

    if not oos_df.empty:
        urgent = oos_df[oos_df["urgency"].isin(["CRITICAL","HIGH","MEDIUM"])].head(20)
        if not urgent.empty:
            st.plotly_chart(oos_urgency_bar(urgent),
                            use_container_width=True, config={"displayModeBar": False})
            with st.expander("ดูตาราง OOS ทั้งหมด"):
                disp = urgent[[MAKRO.CUSTOMER, MAKRO.ITEM, MAKRO.CLASS,
                               "days_until_runout", "urgency", "avg_monthly_spend"]].copy()
                disp.columns = ["ลูกค้า","สินค้า","Class","วันที่เหลือ","ระดับ","ยอด/เดือน"]
                disp["ยอด/เดือน"] = disp["ยอด/เดือน"].apply(fmt)
                st.dataframe(disp, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: ITEM DETAIL
# ═══════════════════════════════════════════════════════════════════════════════

def page_item_detail():
    item_name = st.session_state.detail_item
    df = _df()

    if st.button("← กลับ", type="secondary"):
        go(st.session_state.prev_page)

    if df.empty or not item_name:
        st.warning("ไม่พบข้อมูลสินค้า")
        st.stop()

    item_df = df[df[MAKRO.ITEM] == item_name]
    if item_df.empty:
        st.warning("ไม่พบสินค้านี้ในฐานข้อมูล")
        st.stop()

    info = item_df.iloc[0]
    total_rev = item_df[MAKRO.REVENUE].sum()
    total_profit = item_df[MAKRO.PROFIT].sum()
    margin = total_profit / total_rev * 100 if total_rev else 0

    # Header
    st.markdown(f"## 📦 {item_name}")
    st.markdown(
        f'<span style="color:#64748b;font-size:0.85rem">'
        f'{div_badge(info[MAKRO.DIVISION])} &nbsp; '
        f'{info[MAKRO.DEPT]} › {info[MAKRO.CLASS]}</span>',
        unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(kpi_card("ยอดขายรวม", fmt(total_rev), "💰"), unsafe_allow_html=True)
    with col2: st.markdown(kpi_card("กำไรรวม", fmt(total_profit), "📈"), unsafe_allow_html=True)
    with col3: st.markdown(kpi_card("Margin", f"{margin:.1f}%", "🎯"), unsafe_allow_html=True)
    with col4:
        n_custs = item_df[MAKRO.CUST_NUM].nunique()
        st.markdown(kpi_card("ร้านที่ซื้อ", str(n_custs), "🏪"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Row 1: DOW pattern + Monthly trend
    col_dow, col_trend = st.columns([2, 3])

    with col_dow:
        st.markdown(section_header("วันที่ลูกค้ามักสั่งซื้อ", "📅"), unsafe_allow_html=True)
        dow = item_dow_pattern(df, item_name)
        if not dow.empty and dow["Revenue"].sum() > 0:
            st.plotly_chart(dow_bar(dow), use_container_width=True, config={"displayModeBar": False})
            best_dow = dow.loc[dow["Revenue"].idxmax(), "Day"]
            st.caption(f"📌 วันที่ยอดขายสูงสุด: **{best_dow}**")
        else:
            st.info("ไม่มีข้อมูลรายวัน")

    with col_trend:
        st.markdown(section_header("ยอดขายรายเดือน", "📊"), unsafe_allow_html=True)
        t = item_monthly_trend(df, item_name)
        if not t.empty:
            st.plotly_chart(item_trend_chart(t),
                            use_container_width=True, config={"displayModeBar": False})
            # Trend direction
            if len(t) >= 2:
                first_h = t["Revenue"].iloc[:len(t)//2].mean()
                second_h = t["Revenue"].iloc[len(t)//2:].mean()
                if second_h > first_h * 1.05:
                    st.caption("📈 เทรนด์: ยอดขายกำลังเติบโต")
                elif second_h < first_h * 0.95:
                    st.caption("📉 เทรนด์: ยอดขายมีแนวโน้มลดลง")
                else:
                    st.caption("➡️ เทรนด์: ยอดขายทรงตัว")

    st.markdown("<br>", unsafe_allow_html=True)

    # Row 2: Top 10 customers
    st.markdown(section_header("10 ร้านที่ซื้อสินค้านี้มากที่สุด", "🏪"), unsafe_allow_html=True)
    top_custs = item_top_customers(df, item_name, n=10)

    if not top_custs.empty:
        max_rev = top_custs["Revenue"].max()
        for idx, row in top_custs.iterrows():
            pct = row["Revenue"] / max_rev * 100
            col_rank, col_name, col_type, col_rev, col_bar, col_btn = st.columns([0.4, 3, 2, 1.5, 2, 1.2])
            with col_rank:
                st.markdown(f'<div style="color:#94a3b8;font-size:0.8rem;padding-top:8px">#{idx+1}</div>',
                            unsafe_allow_html=True)
            with col_name:
                st.markdown(f'<div style="padding:6px 0;font-size:0.85rem;font-weight:500;color:#1e293b">{row[MAKRO.CUSTOMER]}</div>',
                            unsafe_allow_html=True)
            with col_type:
                st.markdown(f'<div style="padding:6px 0;font-size:0.75rem;color:#64748b">{row[MAKRO.CUST_TYPE]}</div>',
                            unsafe_allow_html=True)
            with col_rev:
                st.markdown(f'<div style="padding:6px 0;font-size:0.85rem;color:#1a6faf;font-weight:600">{fmt(row["Revenue"])}</div>',
                            unsafe_allow_html=True)
            with col_bar:
                bar_html = (f'<div style="margin-top:10px;background:#e2e8f0;border-radius:4px;height:8px">'
                            f'<div style="width:{pct:.0f}%;background:#1a6faf;height:8px;border-radius:4px"></div></div>')
                st.markdown(bar_html, unsafe_allow_html=True)
            with col_btn:
                if st.button("ดูลูกค้า", key=f"ic_{idx}"):
                    go("customer_detail",
                       detail_cust_id=row[MAKRO.CUST_NUM],
                       detail_cust_name=row[MAKRO.CUSTOMER])
            st.divider()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: CALENDAR
# ═══════════════════════════════════════════════════════════════════════════════

def page_calendar():
    df = _df()
    if df.empty:
        st.info("ยังไม่มีข้อมูล")
        st.stop()

    oos_df = _oos(df)
    rfm_df = _rfm(df)

    st.markdown(section_header("Restock Calendar — วางแผนการโทรหาลูกค้า", "📅"),
                unsafe_allow_html=True)

    today = datetime.now()
    col_m, col_y, _ = st.columns([1.2, 1, 5])
    with col_m:
        month = st.selectbox("เดือน", range(1,13), index=today.month-1,
                             format_func=lambda m: ["ม.ค.","ก.พ.","มี.ค.","เม.ย.","พ.ค.",
                                                    "มิ.ย.","ก.ค.","ส.ค.","ก.ย.","ต.ค.","พ.ย.","ธ.ค."][m-1])
    with col_y:
        year = st.selectbox("ปี", [2025,2026,2027], index=1)

    # Build events dict: date_str → list of {cust, item, urgency}
    events: dict = {}
    if not oos_df.empty:
        for _, row in oos_df.iterrows():
            rd = row["predicted_runout"]
            alert_date = (pd.Timestamp(rd) - pd.Timedelta(days=3)).strftime("%Y-%m-%d")
            if alert_date not in events:
                events[alert_date] = []
            events[alert_date].append({
                "cust_id":   row[MAKRO.CUST_NUM],
                "cust_name": row[MAKRO.CUSTOMER],
                "item":      row[MAKRO.ITEM],
                "urgency":   row["urgency"],
            })

    # Summary count per day
    event_counts = {d: len(v) for d, v in events.items()}

    # Render calendar
    day_names = ["จ","อ","พ","พฤ","ศ","ส","อา"]
    cols = st.columns(7)
    for i, dn in enumerate(day_names):
        cols[i].markdown(
            f'<div style="text-align:center;font-size:0.78rem;font-weight:600;'
            f'color:#1a6faf;padding:4px 0;border-bottom:2px solid #bfdbfe">{dn}</div>',
            unsafe_allow_html=True)

    month_cal = calendar.monthcalendar(year, month)
    for week in month_cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    st.markdown('<div style="min-height:72px"></div>', unsafe_allow_html=True)
                    continue
                date_str = f"{year}-{month:02d}-{day:02d}"
                is_today = (date_str == today.strftime("%Y-%m-%d"))
                cnt = event_counts.get(date_str, 0)
                day_evs = events.get(date_str, [])

                border = "border:2px solid #1a6faf;" if is_today else "border:1px solid #e2e8f0;"
                bg = "#eff6ff" if is_today else "#ffffff"
                html = (f'<div style="background:{bg};{border}border-radius:8px;'
                        f'padding:5px 6px;min-height:72px;cursor:pointer">')
                day_color = "#1a6faf" if is_today else "#374151"
                html += f'<div style="font-size:0.72rem;font-weight:{"600" if is_today else "400"};color:{day_color}">{day}</div>'

                if cnt > 0:
                    # Show up to 2 chips
                    for ev in day_evs[:2]:
                        urg = ev["urgency"]
                        chip_bg = {"CRITICAL":"#fee2e2","HIGH":"#fef3c7","MEDIUM":"#dbeafe"}.get(urg,"#f1f5f9")
                        chip_c  = {"CRITICAL":"#991b1b","HIGH":"#92400e","MEDIUM":"#1e40af"}.get(urg,"#475569")
                        short_name = ev["cust_name"][:10]
                        html += (f'<div style="background:{chip_bg};color:{chip_c};'
                                 f'border-radius:3px;padding:1px 4px;font-size:0.58rem;'
                                 f'margin-top:2px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis">'
                                 f'{short_name}</div>')
                    if cnt > 2:
                        html += f'<div style="font-size:0.58rem;color:#94a3b8;margin-top:1px">+{cnt-2} อื่นๆ</div>'
                html += "</div>"
                st.markdown(html, unsafe_allow_html=True)

    # Day detail selector
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(section_header("เลือกวันเพื่อดูรายละเอียด", "🔍"), unsafe_allow_html=True)

    days_with_events = sorted([d for d in events if d.startswith(f"{year}-{month:02d}")])
    if not days_with_events:
        st.info("ไม่มี Alert ในเดือนนี้")
    else:
        sel_day = st.selectbox(
            "เลือกวันที่มี Alert",
            days_with_events,
            format_func=lambda d: f"{d} ({len(events[d])} รายการ)")

        if sel_day:
            day_events = events[sel_day]
            st.markdown(f"**{sel_day} — {len(day_events)} รายการที่ต้องติดตาม**")
            for ei, ev in enumerate(day_events):
                col_urg, col_cust, col_item, col_btn = st.columns([1.5, 2.5, 3.5, 1.2])
                with col_urg:
                    st.markdown(urgency_badge(ev["urgency"]), unsafe_allow_html=True)
                with col_cust:
                    st.markdown(f'<div style="font-size:0.85rem;font-weight:500;padding:4px 0">{ev["cust_name"]}</div>',
                                unsafe_allow_html=True)
                with col_item:
                    st.markdown(f'<div style="font-size:0.8rem;color:#475569;padding:4px 0">{ev["item"]}</div>',
                                unsafe_allow_html=True)
                with col_btn:
                    if st.button("ดูลูกค้า", key=f"cal_{sel_day}_{ei}_{ev['cust_id']}"):
                        go("customer_detail",
                           detail_cust_id=ev["cust_id"],
                           detail_cust_name=ev["cust_name"])
                st.divider()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: CUSTOMER DETAIL
# ═══════════════════════════════════════════════════════════════════════════════

def page_customer_detail():
    cust_id   = st.session_state.detail_cust_id
    cust_name = st.session_state.detail_cust_name
    df = _df()

    if st.button("← กลับ", type="secondary"):
        go(st.session_state.prev_page)

    if df.empty or cust_id is None:
        st.warning("ไม่พบข้อมูล")
        st.stop()

    cust_df = df[df[MAKRO.CUST_NUM] == cust_id]
    if cust_df.empty:
        st.warning("ไม่พบข้อมูลลูกค้า")
        st.stop()

    rfm_df = _rfm(df)
    oos_df = _oos(df)
    info   = cust_df.iloc[0]
    rfm_row = rfm_df[rfm_df[MAKRO.CUST_NUM] == cust_id]
    segment = rfm_row["segment"].values[0] if not rfm_row.empty else "—"
    seg_color = {"Champion":"#0f7b55","Loyal":"#1a6faf","At Risk":"#c07a00",
                 "Churning":"#c0392b","New":"#5a6a7a","Promising":"#7c4dbd"}.get(segment,"#6b7280")

    # Header
    st.markdown(f"## 🏪 {cust_name}")
    st.markdown(
        f'<span style="color:#64748b;font-size:0.85rem">{info[MAKRO.CUST_TYPE]}</span> &nbsp;'
        f'<span style="background:{seg_color}18;color:{seg_color};border:1px solid {seg_color}44;'
        f'border-radius:20px;padding:2px 12px;font-size:0.75rem;font-weight:600">{segment}</span>',
        unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # KPIs
    if not rfm_row.empty:
        r = rfm_row.iloc[0]
        c1,c2,c3,c4 = st.columns(4)
        with c1: st.markdown(kpi_card("ยอดขายรวม", fmt(r["revenue"]), "💰"), unsafe_allow_html=True)
        with c2: st.markdown(kpi_card("กำไร", fmt(r["profit"]), "📈"), unsafe_allow_html=True)
        with c3: st.markdown(kpi_card("เดือน Active", f"{int(r['freq'])}/{df['_date'].nunique()}", "📅"), unsafe_allow_html=True)
        with c4: st.markdown(kpi_card("SKU ที่ซื้อ", str(int(r["items_count"])), "📦"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Charts
    col_monthly, col_dept = st.columns([3,2])
    with col_monthly:
        st.markdown(section_header("ยอดซื้อรายเดือน","📊"), unsafe_allow_html=True)
        monthly = customer_monthly(df, cust_id)
        if not monthly.empty:
            st.plotly_chart(customer_revenue_bar(monthly),
                            use_container_width=True, config={"displayModeBar":False})
    with col_dept:
        st.markdown(section_header("สัดส่วน Department","🥧"), unsafe_allow_html=True)
        dept = customer_dept_mix(df, cust_id)
        if not dept.empty:
            st.plotly_chart(dept_pie(dept),
                            use_container_width=True, config={"displayModeBar":False})

    st.markdown("<br>", unsafe_allow_html=True)

    # Restock + Upsell tabs
    tab_restock, tab_upsell, tab_history = st.tabs(["🔄 Restock", "✨ Upsell", "📋 ประวัติการซื้อ"])

    with tab_restock:
        cust_oos = oos_df[oos_df[MAKRO.CUST_NUM] == cust_id] if not oos_df.empty else pd.DataFrame()
        if not cust_oos.empty:
            for _, row in cust_oos.iterrows():
                d = int(row["days_until_runout"])
                col_badge, col_item, col_info, col_action = st.columns([1.2, 3.5, 2, 2])
                with col_badge:
                    st.markdown(urgency_badge(row["urgency"]), unsafe_allow_html=True)
                with col_item:
                    st.markdown(f'<div style="font-size:0.85rem;font-weight:500;padding:4px 0">{row[MAKRO.ITEM]}</div>', unsafe_allow_html=True)
                    st.caption(row[MAKRO.CLASS])
                with col_info:
                    st.markdown(f'<div style="font-size:0.8rem;color:#475569;padding:4px 0">ยอด/เดือน: {fmt(row["avg_monthly_spend"])}</div>', unsafe_allow_html=True)
                    st.caption(f"คาดหมดใน {max(0,d)} วัน")
                with col_action:
                    script = (f"หมดแล้ว สั่งด่วน!" if d <= 0
                              else f"ส่งเพิ่มก่อนหมด {d} วัน")
                    st.caption(f"💬 {script}")
                st.divider()
        else:
            st.success("ไม่มีสินค้าที่ใกล้หมดสต็อก 🎉")

    with tab_upsell:
        upsell = upsell_suggestions(df, cust_id)
        if not upsell.empty:
            st.caption(f"สินค้าที่ลูกค้าประเภทเดียวกันซื้อ แต่ {cust_name} ยังไม่เคยสั่ง")
            for _, row in upsell.iterrows():
                col_item, col_class, col_peers, col_rev = st.columns([3.5, 2, 1.5, 1.5])
                with col_item:
                    st.markdown(f'<div style="font-size:0.85rem;font-weight:500;padding:4px 0">{row[MAKRO.ITEM]}</div>', unsafe_allow_html=True)
                with col_class:
                    st.caption(row[MAKRO.CLASS])
                with col_peers:
                    st.markdown(f'<div style="font-size:0.8rem;color:#0f7b55;padding:4px 0">{int(row["PeerCount"])} ร้านซื้อ</div>', unsafe_allow_html=True)
                with col_rev:
                    st.markdown(f'<div style="font-size:0.8rem;color:#1a6faf;padding:4px 0">{fmt(row["Revenue"])}</div>', unsafe_allow_html=True)
                st.divider()
        else:
            st.info("ไม่มีข้อมูล Upsell สำหรับลูกค้านี้")

    with tab_history:
        items = customer_top_items(df, cust_id, n=30)
        if not items.empty:
            for _, row in items.iterrows():
                col_item, col_class, col_rev, col_mo, col_btn = st.columns([3.5, 2, 1.5, 1, 1.2])
                with col_item:
                    st.markdown(f'<div style="font-size:0.83rem;font-weight:500;padding:3px 0">{row[MAKRO.ITEM]}</div>', unsafe_allow_html=True)
                with col_class:
                    st.caption(row[MAKRO.CLASS])
                with col_rev:
                    st.markdown(f'<div style="font-size:0.83rem;color:#1a6faf;padding:3px 0">{fmt(row["Revenue"])}</div>', unsafe_allow_html=True)
                with col_mo:
                    st.caption(f"{int(row['Months'])} เดือน")
                with col_btn:
                    if st.button("ดูสินค้า", key=f"hist_{_}"):
                        go("item_detail", detail_item=row[MAKRO.ITEM])
                st.divider()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

def page_database():
    st.markdown("## 🗄️ Database Management")

    st.markdown(section_header("อัปโหลดข้อมูลใหม่","📤"), unsafe_allow_html=True)
    col_f, col_l = st.columns([3,2])
    with col_f:
        uploaded = st.file_uploader("เลือกไฟล์ Excel (.xlsx)",
                                     type=["xlsx"], label_visibility="collapsed")
    with col_l:
        batch_label = st.text_input("ชื่อ Batch", placeholder="เช่น May 2026")

    if uploaded and st.button("📥 โหลดข้อมูล"):
        with st.spinner("กำลัง clean data..."):
            raw     = pd.read_excel(uploaded)
            cleaned = clean_data(raw)
            if cleaned.empty:
                st.error("ไม่พบข้อมูล FD RETAILER ในไฟล์นี้")
            else:
                date_min = str(cleaned[MAKRO.DATE].min().date())
                date_max = str(cleaned[MAKRO.DATE].max().date())
                overlaps = check_date_overlap(date_min, date_max)
                label    = batch_label or uploaded.name
                if overlaps:
                    st.warning(f"⚠️ ช่วงวันที่ซ้ำกับ {len(overlaps)} batch เดิม")
                    for o in overlaps: st.caption(f"• {o['label']} ({o['date_min']}–{o['date_max']})")
                    st.session_state.pending_upload = dict(
                        label=label, filename=uploaded.name, df=cleaned,
                        overlaps=overlaps, date_min=date_min, date_max=date_max)
                else:
                    save_batch(label, uploaded.name, cleaned)
                    _reload()
                    st.success(f"✅ บันทึก {len(cleaned):,} แถว ({date_min}–{date_max})")

    if st.session_state.pending_upload:
        pend = st.session_state.pending_upload
        st.error("⚠️ ยืนยันการ Replace batch เดิม?")
        ca, cb = st.columns(2)
        with ca:
            if st.button("✅ ยืนยัน", type="primary"):
                for o in pend["overlaps"]: delete_batch(o["id"])
                save_batch(pend["label"], pend["filename"], pend["df"])
                st.session_state.pending_upload = None
                _reload(); st.success("บันทึกเรียบร้อย"); st.rerun()
        with cb:
            if st.button("❌ ยกเลิก"):
                st.session_state.pending_upload = None; st.rerun()

    st.divider()
    st.markdown(section_header("Batches ที่มีอยู่","📦"), unsafe_allow_html=True)
    batches = load_all_batches()
    if not batches:
        st.info("ยังไม่มีข้อมูล")
    else:
        for b in batches:
            ca,cb,cc,cd,ce = st.columns([3,2,1.5,1,1])
            with ca:
                new_lbl = st.text_input("", value=b["label"], key=f"lbl_{b['id']}",
                                         label_visibility="collapsed")
                if new_lbl != b["label"] and st.button("💾", key=f"sv_{b['id']}"):
                    rename_batch(b["id"], new_lbl); st.rerun()
            with cb: st.caption(f"{b.get('date_min','')} – {b.get('date_max','')}")
            with cc: st.caption(f"{b.get('row_count',0):,} แถว")
            with cd: st.caption(b.get("created_at","")[:10])
            with ce:
                if st.button("🗑️", key=f"del_{b['id']}"): delete_batch(b["id"]); _reload(); st.rerun()

    st.divider()
    st.markdown(section_header("จัดการ Salesperson","👥"), unsafe_allow_html=True)
    users = get_users()
    col_n, col_b = st.columns([3,1])
    with col_n:
        new_name = st.text_input("", placeholder="ชื่อ Salesperson ใหม่",
                                  label_visibility="collapsed")
    with col_b:
        if st.button("➕ เพิ่ม") and new_name:
            add_user(new_name.strip()); st.rerun()
    for u in users:
        ca,cb = st.columns([4,1])
        with ca: st.markdown(f"👤 **{u['name']}**")
        with cb:
            if st.button("🗑️", key=f"du_{u['id']}"): delete_user(u["id"]); st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

render_nav()
pg = st.session_state.page

if pg == "home":            page_home();            st.stop()
if pg == "item_detail":     page_item_detail();     st.stop()
if pg == "calendar":        page_calendar();        st.stop()
if pg == "customer_detail": page_customer_detail(); st.stop()
if pg == "database":        page_database();        st.stop()

go("home")
