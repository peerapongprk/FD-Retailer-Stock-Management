"""RetailIQ V2 — Trusted Inventory Companion"""

import streamlit as st
import pandas as pd
from datetime import datetime
import calendar

st.set_page_config(page_title="RetailIQ", page_icon="🏪",
                   layout="wide", initial_sidebar_state="collapsed")

from utils.styles  import inject_css, kpi_card, section_header, div_badge, urgency_badge, call_card
from utils.charts  import (revenue_trend_chart, rfm_donut, top_items_bar, pareto_chart,
                            dow_bar, dow_heatmap, item_trend_chart,
                            customer_revenue_bar, dept_pie, restock_timeline_chart)
from utils.data_engine import (clean_data, compute_kpis, monthly_trend, compute_rfm,
                                top_items_by_division, pareto_items,
                                item_dow_pattern, item_top_customers, item_monthly_trend,
                                dow_overview, dow_by_division, dow_by_customer,
                                predict_restock, restock_items_for_customer,
                                top5_calls_today,
                                customer_monthly, customer_top_items, customer_dept_mix,
                                upsell_suggestions)
from database.persistence import (save_batch, load_combined_df, load_all_batches,
                                   delete_batch, rename_batch, check_date_overlap,
                                   get_users, add_user, delete_user)
from database.schema import MAKRO, RFM_COLOR, RFM_ADVICE, DAY_TH

inject_css()

# ── Breadcrumb ────────────────────────────────────────────────────────────────

_BREADCRUMB_LABELS = {
    "home": "🏠 Overview",
    "calendar": "📅 Calendar",
    "database": "🗄️ Database",
    "item_detail": "📦 สินค้า",
    "customer_detail": "🏪 ลูกค้า",
}

def render_breadcrumb(extra: str = ""):
    """แสดง breadcrumb trail ด้านบนหน้า"""
    page  = st.session_state.page
    prev  = st.session_state.prev_page
    parts = []
    # Always show home as root
    parts.append(("home", "🏠 Overview"))
    if prev != "home" and prev != page:
        parts.append((prev, _BREADCRUMB_LABELS.get(prev, prev)))
    if page != "home":
        label = _BREADCRUMB_LABELS.get(page, page)
        if extra:
            label = f"{label}: {extra}"
        parts.append((page, label))

    crumbs_html = ""
    for i, (pg, lbl) in enumerate(parts):
        is_last = (i == len(parts) - 1)
        if is_last:
            crumbs_html += f'<span style="color:#1e293b;font-weight:600;font-size:0.82rem">{lbl}</span>'
        else:
            crumbs_html += (
                f'<span style="color:#1a6faf;font-size:0.82rem;cursor:pointer" '
                f'onclick="void(0)">{lbl}</span>'
                f'<span style="color:#94a3b8;margin:0 6px;font-size:0.8rem">›</span>'
            )
    st.markdown(
        f'<div style="padding:4px 0 10px;display:flex;align-items:center">{crumbs_html}</div>',
        unsafe_allow_html=True)


# ── session defaults ──────────────────────────────────────────────────────────
for k, v in {
    "page": "home", "prev_page": "home",
    "df": None, "pending_upload": None,
    "rfm_df": None, "restock_df": None,
    "detail_cust_id": None, "detail_cust_name": None,
    "detail_item": None,
    "home_sub": "overview",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── helpers ───────────────────────────────────────────────────────────────────

def go(page, **kw):
    st.session_state.prev_page = st.session_state.page
    st.session_state.page = page
    for k, v in kw.items():
        st.session_state[k] = v
    st.rerun()

def _reload():
    st.session_state.df = load_combined_df()
    st.session_state.rfm_df = None
    st.session_state.restock_df = None

def _df():
    if st.session_state.df is None or (hasattr(st.session_state.df,"empty") and st.session_state.df.empty):
        _reload()
    return st.session_state.df if st.session_state.df is not None else pd.DataFrame()

def _rfm(df):
    if df.empty: return pd.DataFrame()
    if st.session_state.rfm_df is None:
        st.session_state.rfm_df = compute_rfm(df)
    return st.session_state.rfm_df

def _restock(df):
    if df.empty: return pd.DataFrame()
    if st.session_state.restock_df is None:
        st.session_state.restock_df = predict_restock(df)
    return st.session_state.restock_df

def fmt(v):
    if v >= 1_000_000: return f"฿{v/1_000_000:.1f}M"
    if v >= 1_000:     return f"฿{v/1_000:.1f}K"
    return f"฿{v:,.0f}"

def scrollable_df(df: pd.DataFrame, height: int = 400, key: str = "tbl"):
    """แสดง dataframe ในกล่อง scroll ได้ พร้อม sort"""
    st.dataframe(df, use_container_width=True, height=height,
                 hide_index=True, key=key)


# ── NAV ───────────────────────────────────────────────────────────────────────

def render_nav():
    c_logo, c1, c2, c3, _ = st.columns([1.5, 1, 1, 1, 4])
    with c_logo:
        st.markdown("### 🏪 RetailIQ")
    pg = st.session_state.page
    with c1:
        if st.button("🏠 Overview", use_container_width=True,
                     type="primary" if pg=="home" else "secondary"): go("home")
    with c2:
        if st.button("📅 Calendar", use_container_width=True,
                     type="primary" if pg=="calendar" else "secondary"): go("calendar")
    with c3:
        if st.button("🗄️ Database", use_container_width=True,
                     type="primary" if pg=="database" else "secondary"): go("database")
    st.divider()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: HOME
# ═══════════════════════════════════════════════════════════════════════════════

def page_home():
    df = _df()
    if df.empty:
        st.info("ยังไม่มีข้อมูล — ไปที่ 🗄️ Database เพื่ออัปโหลดไฟล์")
        st.stop()

    rfm_df     = _rfm(df)
    restock_df = _restock(df)

    # Sub-nav
    sub = st.session_state.home_sub
    tabs = [("📊 ภาพรวม","overview"), ("📦 สินค้าขายดี","top_items"),
            ("📅 เทรนด์วัน","dow_trend"), ("🔔 Alerts","alerts")]
    cols = st.columns(len(tabs))
    for col, (label, key) in zip(cols, tabs):
        with col:
            if st.button(label, use_container_width=True,
                         type="primary" if sub==key else "secondary"):
                st.session_state.home_sub = key; st.rerun()
    st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)

    if sub == "overview":   _render_overview(df, rfm_df, restock_df)
    elif sub == "top_items": _render_top_items(df)
    elif sub == "dow_trend": _render_dow_trend(df)
    elif sub == "alerts":    _render_alerts(df, rfm_df, restock_df)


# ── Overview ──────────────────────────────────────────────────────────────────

def _render_overview(df, rfm_df, restock_df):
    kpis = compute_kpis(df)
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
        st.markdown(section_header("ยอดขายรายเดือน","📅"), unsafe_allow_html=True)
        trend = monthly_trend(df)
        if not trend.empty:
            st.plotly_chart(revenue_trend_chart(trend),
                            use_container_width=True, config={"displayModeBar":False})
    with col_rfm:
        st.markdown(section_header("RFM Segment","🎨"), unsafe_allow_html=True)
        if not rfm_df.empty:
            st.plotly_chart(rfm_donut(rfm_df),
                            use_container_width=True, config={"displayModeBar":False})
            for seg, grp in rfm_df.groupby("segment"):
                color = RFM_COLOR.get(seg, "#6b7280")
                advice = RFM_ADVICE.get(seg, "")
                st.markdown(
                    f'<span style="background:{color}18;color:{color};border:1px solid {color}44;'
                    f'border-radius:20px;padding:1px 10px;font-size:0.72rem;font-weight:600">{seg}</span>'
                    f' <span style="font-size:0.76rem;color:#64748b">({len(grp)} ร้าน) — {advice}</span>',
                    unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    calls = top5_calls_today(df, restock_df, rfm_df)
    if not calls.empty:
        st.markdown(section_header("Today's Top 5 Calls","📞"), unsafe_allow_html=True)
        for i, row in calls.iterrows():
            st.markdown(call_card(i+1, row[MAKRO.CUSTOMER], row["reason"],
                                  row["script"], row.get("urgency","HIGH")),
                        unsafe_allow_html=True)


# ── Top Items ─────────────────────────────────────────────────────────────────

def _render_top_items(df):
    st.markdown(section_header("สินค้าขายดี 10 อันดับแรก แยก Division","📦"),
                unsafe_allow_html=True)
    divs = ["DRY FOOD","FRESH FOOD","NON FOOD"]
    div_icons = {"DRY FOOD":"🥫","FRESH FOOD":"🥬","NON FOOD":"🧴"}

    for div in divs:
        top = top_items_by_division(df, division=div, n_top=10)
        if top.empty: continue

        st.markdown("<br>", unsafe_allow_html=True)
        col_hdr, col_btn = st.columns([5, 1])
        with col_hdr:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;padding:4px 0">'
                f'<span style="font-size:1.2rem">{div_icons.get(div,"")}</span>'
                f'<span style="font-size:0.95rem;font-weight:600;color:#1e293b">{div}</span>'
                f'</div>', unsafe_allow_html=True)
        with col_btn:
            pk = f"pareto_{div}"
            showing = st.session_state.get(pk, False)
            if st.button("▲ ซ่อน" if showing else "📊 Pareto 80%",
                         key=f"btn_{pk}", use_container_width=True):
                st.session_state[pk] = not showing; st.rerun()

        # Top 10 table in scrollable box (10 rows visible)
        disp = top[[MAKRO.ITEM, MAKRO.CLASS, "Revenue","Profit","Customers","Months"]].copy()
        disp.index = range(1, len(disp)+1)
        disp.columns = ["สินค้า","Class","ยอดขาย (฿)","กำไร (฿)","ร้าน","เดือน"]
        disp["ยอดขาย (฿)"] = disp["ยอดขาย (฿)"].apply(lambda v: f"{v:,.0f}")
        disp["กำไร (฿)"]   = disp["กำไร (฿)"].apply(lambda v: f"{v:,.0f}")

        st.dataframe(disp, use_container_width=True, height=390, hide_index=False)
        # Drill-down buttons below table
        btn_cols = st.columns(min(5, len(top)))
        for idx, row in top.iterrows():
            with btn_cols[idx % len(btn_cols)]:
                short = row[MAKRO.ITEM][:18] + ("…" if len(row[MAKRO.ITEM])>18 else "")
                if st.button(f"🔍 {short}", key=f"item_{div}_{idx}", use_container_width=True):
                    go("item_detail", detail_item=row[MAKRO.ITEM])

        # Pareto panel
        if st.session_state.get(pk, False):
            with st.container():
                st.markdown(
                    f'<div style="background:#eff6ff;border:1px solid #bfdbfe;'
                    f'border-radius:10px;padding:14px;margin-bottom:10px">'
                    f'<span style="font-size:0.85rem;font-weight:600;color:#1e40af">'
                    f'📊 Pareto — {div}</span></div>', unsafe_allow_html=True)

                pareto_df = pareto_items(df, division=div)
                total_items_div = df[df[MAKRO.DIVISION]==div][MAKRO.ITEM].nunique()
                pct_items = len(pareto_df)/total_items_div*100 if total_items_div else 0

                ca,cb,cc = st.columns(3)
                with ca: st.metric("SKU ใน 80%", f"{len(pareto_df):,} รายการ")
                with cb: st.metric("% ของ SKU ทั้งหมด", f"{pct_items:.1f}%")
                with cc: st.metric("SKU ทั้งหมด", f"{total_items_div:,} รายการ")

                st.plotly_chart(pareto_chart(pareto_df.reset_index()),
                                use_container_width=True, config={"displayModeBar":False})

                # Pareto table scrollable 20 rows
                p_disp = pareto_df.reset_index()[[
                    "index", MAKRO.ITEM, MAKRO.CLASS, "Revenue","CumPct","Customers"]].copy()
                p_disp.columns = ["Rank","สินค้า","Class","ยอดขาย (฿)","Cum%","ร้าน"]
                p_disp["ยอดขาย (฿)"] = p_disp["ยอดขาย (฿)"].apply(lambda v: f"{v:,.0f}")
                p_disp["Cum%"] = p_disp["Cum%"].apply(lambda v: f"{v:.1f}%")

                st.dataframe(p_disp, use_container_width=True, height=680, hide_index=True)
                st.caption("👆 กดหัวตารางเพื่อ sort | กดปุ่มด้านล่างเพื่อดูรายละเอียดสินค้า")
                btn_cols2 = st.columns(5)
                for idx2, prow in pareto_df.reset_index().head(20).iterrows():
                    with btn_cols2[idx2 % 5]:
                        short = prow[MAKRO.ITEM][:15] + ("…" if len(prow[MAKRO.ITEM])>15 else "")
                        if st.button(f"🔍 {short}", key=f"pi_{div}_{idx2}", use_container_width=True):
                            go("item_detail", detail_item=prow[MAKRO.ITEM])


# ── DOW Trend ─────────────────────────────────────────────────────────────────

def _render_dow_trend(df):
    st.markdown(section_header("เทรนด์วันที่ลูกค้าสั่งซื้อ","📅"), unsafe_allow_html=True)

    # Level selector
    level = st.radio("ระดับการดู", ["ภาพรวมทั้งหมด","แยกตาม Division","รายลูกค้า"],
                     horizontal=True)

    if level == "ภาพรวมทั้งหมด":
        dow = dow_overview(df)
        best = dow.loc[dow["Revenue"].idxmax(),"Day"]
        col_chart, col_info = st.columns([3,1])
        with col_chart:
            st.plotly_chart(dow_bar(dow, title="ยอดขายรวม แยกตามวัน"),
                            use_container_width=True, config={"displayModeBar":False})
        with col_info:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.metric("วันขายดีสุด", best)
            st.metric("ลูกค้า unique", f"{dow['Customers'].sum():,.0f}")
            # Top 3 days
            top3 = dow.nlargest(3,"Revenue")[["Day","Revenue"]]
            st.markdown("**Top 3 วัน**")
            for _, r in top3.iterrows():
                st.markdown(f'- **{r["Day"]}**: {fmt(r["Revenue"])}')

        # Summary table
        with st.expander("ดูตารางข้อมูลวัน"):
            disp = dow[["Day","Revenue","Orders","Customers"]].copy()
            disp.columns = ["วัน","ยอดขาย (฿)","จำนวนวัน","ลูกค้า"]
            disp["ยอดขาย (฿)"] = disp["ยอดขาย (฿)"].apply(lambda v: f"{v:,.0f}")
            st.dataframe(disp, use_container_width=True, height=310, hide_index=True)

    elif level == "แยกตาม Division":
        dow_div = dow_by_division(df)
        import plotly.graph_objects as _go
        colors = {"DRY FOOD":"#1a6faf","FRESH FOOD":"#0f7b55","NON FOOD":"#c07a00"}
        fig = _go.Figure()
        for div in ["DRY FOOD","FRESH FOOD","NON FOOD"]:
            sub = dow_div[dow_div[MAKRO.DIVISION]==div]
            if sub.empty: continue
            # Reindex to full week order
            sub = sub.set_index("_dow").reindex(range(7)).fillna(0).reset_index()
            sub["Day"] = sub["_dow"].map(dict(enumerate(DAY_TH)))
            fig.add_trace(_go.Bar(x=sub["Day"], y=sub["Revenue"],
                                  name=div, marker_color=colors.get(div,"#888")))
        fig.update_layout(barmode="group", height=300,
                          paper_bgcolor="white", plot_bgcolor="white",
                          font=dict(family="Sarabun, sans-serif", size=12),
                          margin=dict(l=8,r=8,t=16,b=8),
                          legend=dict(orientation="h",y=1.1,x=0),
                          xaxis=dict(showgrid=False),
                          yaxis=dict(showgrid=True, gridcolor="#e5e7eb"))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    else:  # รายลูกค้า
        cust_list = df[[MAKRO.CUST_NUM, MAKRO.CUSTOMER]].drop_duplicates()
        cust_opts = {row[MAKRO.CUSTOMER]: row[MAKRO.CUST_NUM]
                     for _, row in cust_list.sort_values(MAKRO.CUSTOMER).iterrows()}
        sel_name = st.selectbox("เลือกลูกค้า", list(cust_opts.keys()),
                                label_visibility="collapsed")
        sel_id = cust_opts[sel_name]

        dow_c = dow_by_customer(df, sel_id)
        best_dow = dow_c.loc[dow_c["Revenue"].idxmax(),"Day"]

        col_chart, col_info = st.columns([3,1])
        with col_chart:
            st.plotly_chart(dow_bar(dow_c, title=f"วันสั่งของ {sel_name}"),
                            use_container_width=True, config={"displayModeBar":False})
        with col_info:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.metric("วันที่สั่งบ่อยสุด", best_dow)
            restock_df = _restock(df)
            cust_restock = restock_df[restock_df[MAKRO.CUST_NUM]==sel_id]
            if not cust_restock.empty:
                r = cust_restock.iloc[0]
                st.metric("วันที่ควรโทร", str(r["call_day"]))
                st.metric("Items ที่ต้อง Restock", r["items_count"])
        if st.button("ดูรายละเอียดลูกค้า →"):
            go("customer_detail", detail_cust_id=sel_id, detail_cust_name=sel_name)


# ── Alerts ────────────────────────────────────────────────────────────────────

def _render_alerts(df, rfm_df, restock_df):
    st.markdown(section_header("Today's Top 5 Calls","📞"), unsafe_allow_html=True)
    calls = top5_calls_today(df, restock_df, rfm_df)
    if not calls.empty:
        for i, row in calls.iterrows():
            col_card, col_btn = st.columns([5,1])
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
    st.markdown(section_header("Restock Schedule — รายการทั้งหมด","📦"), unsafe_allow_html=True)

    if not restock_df.empty:
        # Timeline chart
        st.plotly_chart(restock_timeline_chart(restock_df),
                        use_container_width=True, config={"displayModeBar":False})

        # Scrollable table
        disp = restock_df[[MAKRO.CUSTOMER, "preferred_dow_name", "call_day",
                            "days_until_call", "urgency", "items_count"]].copy()
        disp.columns = ["ลูกค้า","วันที่มักสั่ง","วันที่ควรโทร","วันนับจากนี้","ระดับ","จำนวน Items"]
        st.dataframe(disp, use_container_width=True, height=680, hide_index=True)

        # Drill-down
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(section_header("ดูรายละเอียด Items ที่ต้อง Restock","🔍"), unsafe_allow_html=True)
        cust_opts = {row[MAKRO.CUSTOMER]: row[MAKRO.CUST_NUM]
                     for _, row in restock_df.iterrows()}
        sel = st.selectbox("เลือกลูกค้า", list(cust_opts.keys()),
                           label_visibility="collapsed")
        items = restock_items_for_customer(restock_df, cust_opts[sel])
        if items:
            items_df = pd.DataFrame(items)[[
                "item","class","avg_gap","last_purchase","predicted_next","call_day","days_until_call"]]
            items_df.columns = ["สินค้า","Class","Cycle (วัน)","สั่งล่าสุด","คาดสั่งครั้งถัดไป","ควรโทรวัน","วันนับจากนี้"]
            st.dataframe(items_df, use_container_width=True, height=680, hide_index=True)
            if st.button(f"ดูหน้าลูกค้า {sel} →"):
                go("customer_detail", detail_cust_id=cust_opts[sel], detail_cust_name=sel)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: ITEM DETAIL
# ═══════════════════════════════════════════════════════════════════════════════

def page_item_detail():
    item_name = st.session_state.detail_item
    df = _df()
    col_back, _ = st.columns([1,8])
    with col_back:
        if st.button("← กลับ", type="secondary"): go(st.session_state.prev_page)
    render_breadcrumb(extra=item_name or "")
    if df.empty or not item_name:
        st.warning("ไม่พบข้อมูลสินค้า"); st.stop()

    item_df = df[df[MAKRO.ITEM]==item_name]
    if item_df.empty:
        st.warning("ไม่พบสินค้านี้"); st.stop()

    info = item_df.iloc[0]
    total_rev    = item_df[MAKRO.REVENUE].sum()
    total_profit = item_df[MAKRO.PROFIT].sum()
    margin = total_profit/total_rev*100 if total_rev else 0

    st.markdown(f"## 📦 {item_name}")
    st.markdown(
        f'<span style="color:#64748b;font-size:0.85rem">'
        f'{div_badge(info[MAKRO.DIVISION])} &nbsp; {info[MAKRO.DEPT]} › {info[MAKRO.CLASS]}</span>',
        unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(kpi_card("ยอดขายรวม", fmt(total_rev), "💰"), unsafe_allow_html=True)
    with c2: st.markdown(kpi_card("กำไรรวม", fmt(total_profit), "📈"), unsafe_allow_html=True)
    with c3: st.markdown(kpi_card("Margin", f"{margin:.1f}%", "🎯"), unsafe_allow_html=True)
    with c4: st.markdown(kpi_card("ร้านที่ซื้อ", str(item_df[MAKRO.CUST_NUM].nunique()), "🏪"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_dow, col_trend = st.columns([2,3])
    with col_dow:
        st.markdown(section_header("วันที่มักสั่ง","📅"), unsafe_allow_html=True)
        dow = item_dow_pattern(df, item_name)
        if not dow.empty and dow["Revenue"].sum() > 0:
            st.plotly_chart(dow_bar(dow), use_container_width=True, config={"displayModeBar":False})
            best = dow.loc[dow["Revenue"].idxmax(),"Day"]
            st.caption(f"📌 วันยอดขายสูงสุด: **{best}**")
        else:
            st.info("ไม่มีข้อมูลรายวัน")
    with col_trend:
        st.markdown(section_header("ยอดขายรายเดือน","📊"), unsafe_allow_html=True)
        t = item_monthly_trend(df, item_name)
        if not t.empty:
            st.plotly_chart(item_trend_chart(t), use_container_width=True, config={"displayModeBar":False})
            if len(t) >= 2:
                fh = t["Revenue"].iloc[:len(t)//2].mean()
                sh = t["Revenue"].iloc[len(t)//2:].mean()
                arrow = "📈 กำลังเติบโต" if sh>fh*1.05 else ("📉 มีแนวโน้มลดลง" if sh<fh*0.95 else "➡️ ทรงตัว")
                st.caption(f"เทรนด์: {arrow}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(section_header("10 ร้านที่ซื้อมากที่สุด","🏪"), unsafe_allow_html=True)
    top_custs = item_top_customers(df, item_name)
    if not top_custs.empty:
        disp = top_custs[[MAKRO.CUSTOMER, MAKRO.CUST_TYPE, "Revenue","Months"]].copy()
        disp.index = range(1, len(disp)+1)
        disp.columns = ["ลูกค้า","ประเภท","ยอดขาย (฿)","เดือน"]
        disp["ยอดขาย (฿)"] = disp["ยอดขาย (฿)"].apply(lambda v: f"{v:,.0f}")

        st.dataframe(disp, use_container_width=True, height=390, hide_index=False)
        st.caption("👆 กดหัวตารางเพื่อ sort")
        btn_cols3 = st.columns(min(5, len(top_custs)))
        for idx, row in top_custs.iterrows():
            with btn_cols3[idx % len(btn_cols3)]:
                short = row[MAKRO.CUSTOMER][:16] + ("…" if len(row[MAKRO.CUSTOMER])>16 else "")
                if st.button(f"🏪 {short}", key=f"ic_{idx}", use_container_width=True):
                    go("customer_detail",
                       detail_cust_id=row[MAKRO.CUST_NUM],
                       detail_cust_name=row[MAKRO.CUSTOMER])


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: CALENDAR
# ═══════════════════════════════════════════════════════════════════════════════

def page_calendar():
    df = _df()
    if df.empty:
        st.info("ยังไม่มีข้อมูล"); st.stop()

    restock_df = _restock(df)
    rfm_df     = _rfm(df)
    st.markdown(section_header("Restock Calendar","📅"), unsafe_allow_html=True)

    today = datetime.now()
    col_m, col_y, _ = st.columns([1.2,1,5])
    with col_m:
        month = st.selectbox("เดือน", range(1,13), index=today.month-1,
                             format_func=lambda m: ["ม.ค.","ก.พ.","มี.ค.","เม.ย.","พ.ค.",
                                                    "มิ.ย.","ก.ค.","ส.ค.","ก.ย.","ต.ค.","พ.ย.","ธ.ค."][m-1])
    with col_y:
        year = st.selectbox("ปี", [2025,2026,2027], index=1)

    # Build events from restock_df (1 record per customer)
    events: dict = {}
    if not restock_df.empty:
        for _, row in restock_df.iterrows():
            call_d = str(row["call_day"])
            if call_d not in events:
                events[call_d] = []
            events[call_d].append({
                "cust_id":    row[MAKRO.CUST_NUM],
                "cust_name":  row[MAKRO.CUSTOMER],
                "items_count":row["items_count"],
                "urgency":    row["urgency"],
                "items_detail": row["items_detail"],
            })

    # Calendar render
    day_names = ["จ","อ","พ","พฤ","ศ","ส","อา"]
    hdr_cols = st.columns(7)
    for i, dn in enumerate(day_names):
        hdr_cols[i].markdown(
            f'<div style="text-align:center;font-size:0.78rem;font-weight:600;'
            f'color:#1a6faf;padding:4px 0;border-bottom:2px solid #bfdbfe">{dn}</div>',
            unsafe_allow_html=True)

    for week in calendar.monthcalendar(year, month):
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    st.markdown('<div style="min-height:72px"></div>', unsafe_allow_html=True)
                    continue
                date_str = f"{year}-{month:02d}-{day:02d}"
                is_today = (date_str == today.strftime("%Y-%m-%d"))
                day_evs  = events.get(date_str, [])
                cnt      = len(day_evs)
                border = "border:2px solid #1a6faf;" if is_today else "border:1px solid #e2e8f0;"
                bg     = "#eff6ff" if is_today else "#ffffff"
                html   = (f'<div style="background:{bg};{border}border-radius:8px;'
                          f'padding:5px 6px;min-height:72px">')
                dc = "#1a6faf" if is_today else "#374151"
                html += f'<div style="font-size:0.72rem;font-weight:{"600" if is_today else "400"};color:{dc}">{day}</div>'
                for ev in day_evs[:2]:
                    urg = ev["urgency"]
                    bg2 = {"CRITICAL":"#fee2e2","HIGH":"#fef3c7","MEDIUM":"#dbeafe"}.get(urg,"#f1f5f9")
                    c2  = {"CRITICAL":"#991b1b","HIGH":"#92400e","MEDIUM":"#1e40af"}.get(urg,"#475569")
                    html += (f'<div style="background:{bg2};color:{c2};border-radius:3px;'
                             f'padding:1px 4px;font-size:0.58rem;margin-top:2px;'
                             f'overflow:hidden;white-space:nowrap;text-overflow:ellipsis">'
                             f'{ev["cust_name"][:10]} ({ev["items_count"]})</div>')
                if cnt > 2:
                    html += f'<div style="font-size:0.58rem;color:#94a3b8;margin-top:1px">+{cnt-2} อื่นๆ</div>'
                html += "</div>"
                st.markdown(html, unsafe_allow_html=True)

    # Day detail
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(section_header("เลือกวันเพื่อดูรายละเอียด","🔍"), unsafe_allow_html=True)
    days_with_events = sorted([d for d in events if d.startswith(f"{year}-{month:02d}")])
    if not days_with_events:
        st.info("ไม่มี Restock Alert ในเดือนนี้")
    else:
        sel_day = st.selectbox("เลือกวันที่", days_with_events,
                               format_func=lambda d: f"{d} ({len(events[d])} ลูกค้า)")
        if sel_day:
            day_events = events[sel_day]
            st.markdown(f"**{sel_day} — {len(day_events)} ลูกค้าที่ควรโทร**")
            for ei, ev in enumerate(day_events):
                col_urg, col_cust, col_items, col_btn = st.columns([1.5,2.5,3.5,1.2])
                with col_urg:
                    st.markdown(urgency_badge(ev["urgency"]), unsafe_allow_html=True)
                with col_cust:
                    st.markdown(f'<div style="font-size:0.85rem;font-weight:500;padding:4px 0">{ev["cust_name"]}</div>',
                                unsafe_allow_html=True)
                with col_items:
                    preview = ", ".join(i["item"][:18] for i in ev["items_detail"][:2])
                    if ev["items_count"] > 2:
                        preview += f" +{ev['items_count']-2} อื่นๆ"
                    st.markdown(f'<div style="font-size:0.78rem;color:#475569;padding:4px 0">{preview}</div>',
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
    col_back, _ = st.columns([1,8])
    with col_back:
        if st.button("← กลับ", type="secondary"): go(st.session_state.prev_page)
    render_breadcrumb(extra=cust_name or "")
    if df.empty or cust_id is None:
        st.warning("ไม่พบข้อมูล"); st.stop()

    cust_df = df[df[MAKRO.CUST_NUM]==cust_id]
    if cust_df.empty:
        st.warning("ไม่พบข้อมูลลูกค้า"); st.stop()

    rfm_df     = _rfm(df)
    restock_df = _restock(df)
    info       = cust_df.iloc[0]
    rfm_row    = rfm_df[rfm_df[MAKRO.CUST_NUM]==cust_id]
    segment    = rfm_row["segment"].values[0] if not rfm_row.empty else "—"
    seg_color  = {"Champion":"#0f7b55","Loyal":"#1a6faf","At Risk":"#c07a00",
                  "Churning":"#c0392b","New":"#5a6a7a","Promising":"#7c4dbd"}.get(segment,"#6b7280")

    st.markdown(f"## 🏪 {cust_name}")
    st.markdown(
        f'<span style="color:#64748b;font-size:0.85rem">{info[MAKRO.CUST_TYPE]}</span> &nbsp;'
        f'<span style="background:{seg_color}18;color:{seg_color};border:1px solid {seg_color}44;'
        f'border-radius:20px;padding:2px 12px;font-size:0.75rem;font-weight:600">{segment}</span>',
        unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if not rfm_row.empty:
        r = rfm_row.iloc[0]
        c1,c2,c3,c4 = st.columns(4)
        with c1: st.markdown(kpi_card("ยอดขายรวม", fmt(r["revenue"]), "💰"), unsafe_allow_html=True)
        with c2: st.markdown(kpi_card("กำไร", fmt(r["profit"]), "📈"), unsafe_allow_html=True)
        with c3: st.markdown(kpi_card("เดือน Active", f"{int(r['freq'])}/{df['_date'].nunique()}", "📅"), unsafe_allow_html=True)
        with c4: st.markdown(kpi_card("SKU ที่ซื้อ", str(int(r["items_count"])), "📦"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
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
            st.plotly_chart(dept_pie(dept), use_container_width=True, config={"displayModeBar":False})

    # DOW pattern for this customer
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(section_header("วันที่มักสั่ง (DOW Pattern)","📅"), unsafe_allow_html=True)
    dow_c = dow_by_customer(df, cust_id)
    best_dow = dow_c.loc[dow_c["Revenue"].idxmax(),"Day"]
    col_dow, col_restock_info = st.columns([3,1])
    with col_dow:
        st.plotly_chart(dow_bar(dow_c), use_container_width=True, config={"displayModeBar":False})
    with col_restock_info:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.metric("วันที่สั่งบ่อยสุด", best_dow)
        cust_rs = restock_df[restock_df[MAKRO.CUST_NUM]==cust_id]
        if not cust_rs.empty:
            r = cust_rs.iloc[0]
            st.metric("วันควรโทร", str(r["call_day"]))
            st.metric("Items ต้อง Restock", r["items_count"])

    st.markdown("<br>", unsafe_allow_html=True)
    tab_restock, tab_upsell, tab_history = st.tabs(["🔄 Restock","✨ Upsell","📋 ประวัติซื้อ"])

    with tab_restock:
        items = restock_items_for_customer(restock_df, cust_id)
        if items:
            items_df = pd.DataFrame(items)[[
                "item","class","avg_gap","last_purchase","predicted_next","call_day","days_until_call"]]
            items_df.columns = ["สินค้า","Class","Cycle (วัน)","สั่งล่าสุด","คาดสั่งครั้งถัดไป","ควรโทรวัน","วันนับจากนี้"]
            st.caption(f"วันที่ควรโทรทั้งหมด อิงจาก avg gap จาก transaction จริง + preferred DOW ({best_dow})")
            st.dataframe(items_df, use_container_width=True, height=680, hide_index=True)
        else:
            st.success("ไม่มี Restock Alert สำหรับลูกค้านี้ 🎉")

    with tab_upsell:
        upsell = upsell_suggestions(df, cust_id)
        if not upsell.empty:
            st.caption(f"สินค้าที่ลูกค้าประเภทเดียวกันซื้อ แต่ {cust_name} ยังไม่เคยสั่ง")
            disp = upsell[[MAKRO.ITEM, MAKRO.CLASS, "PeerCount","Revenue"]].copy()
            disp.columns = ["สินค้า","Class","ร้านที่ซื้อ","ยอดขายรวม (฿)"]
            disp["ยอดขายรวม (฿)"] = disp["ยอดขายรวม (฿)"].apply(lambda v: f"{v:,.0f}")
            st.dataframe(disp, use_container_width=True, height=320, hide_index=True)
        else:
            st.info("ไม่มีข้อมูล Upsell")

    with tab_history:
        items_hist = customer_top_items(df, cust_id)
        if not items_hist.empty:
            disp = items_hist[[MAKRO.ITEM, MAKRO.CLASS, MAKRO.DEPT, "Revenue","Months"]].copy()
            disp.columns = ["สินค้า","Class","Dept","ยอดขาย (฿)","เดือน"]
            disp["ยอดขาย (฿)"] = disp["ยอดขาย (฿)"].apply(lambda v: f"{v:,.0f}")
            st.dataframe(disp, use_container_width=True, height=680, hide_index=True)
            st.caption("👆 กดหัวตารางเพื่อ sort")
            btn_cols4 = st.columns(5)
            for idx, row in items_hist.head(20).iterrows():
                with btn_cols4[idx % 5]:
                    short = row[MAKRO.ITEM][:15] + ("…" if len(row[MAKRO.ITEM])>15 else "")
                    if st.button(f"📦 {short}", key=f"hist_{idx}", use_container_width=True):
                        go("item_detail", detail_item=row[MAKRO.ITEM])


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

def page_database():
    st.markdown("## 🗄️ Database Management")
    st.markdown(section_header("อัปโหลดข้อมูลใหม่","📤"), unsafe_allow_html=True)
    col_f, col_l = st.columns([3,2])
    with col_f:
        uploaded = st.file_uploader("ไฟล์ Excel", type=["xlsx"], label_visibility="collapsed")
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

    if st.session_state.get("pending_upload"):
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
        new_name = st.text_input("", placeholder="ชื่อ Salesperson ใหม่", label_visibility="collapsed")
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
