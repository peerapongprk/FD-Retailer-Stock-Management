"""RetailIQ V2 — Data Engine (gap-based restock logic)"""

import pandas as pd
import numpy as np
from datetime import datetime
from database.schema import MAKRO, FD_RETAILER_GROUP, RFM, DAY_TH


# ── clean ─────────────────────────────────────────────────────────────────────

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if MAKRO.CUST_GROUP in df.columns:
        df = df[df[MAKRO.CUST_GROUP] == FD_RETAILER_GROUP].copy()

    if MAKRO.DATE in df.columns:
        df[MAKRO.DATE] = pd.to_datetime(df[MAKRO.DATE], errors="coerce")
    else:
        def _parse_month(m):
            try:
                parts = str(m).replace(" ", "").split("/")
                return pd.Timestamp(year=int(parts[0]), month=int(parts[1]), day=1)
            except Exception:
                return pd.NaT
        df[MAKRO.DATE] = df[MAKRO.MONTH].apply(_parse_month)

    df["_date"] = df[MAKRO.DATE].dt.to_period("M").dt.to_timestamp()
    df = df.dropna(subset=[MAKRO.DATE])
    df[MAKRO.REVENUE] = pd.to_numeric(df[MAKRO.REVENUE], errors="coerce").fillna(0)
    df[MAKRO.PROFIT]  = pd.to_numeric(df[MAKRO.PROFIT],  errors="coerce").fillna(0)
    if MAKRO.QTY in df.columns:
        df[MAKRO.QTY] = pd.to_numeric(df[MAKRO.QTY], errors="coerce").fillna(0)
    df["_dow"]      = df[MAKRO.DATE].dt.dayofweek
    df["_dow_name"] = df["_dow"].map(dict(enumerate(DAY_TH)))
    return df.reset_index(drop=True)


# ── KPIs ──────────────────────────────────────────────────────────────────────

def compute_kpis(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    total_rev    = df[MAKRO.REVENUE].sum()
    total_profit = df[MAKRO.PROFIT].sum()
    margin       = (total_profit / total_rev * 100) if total_rev else 0
    customers    = df[MAKRO.CUST_NUM].nunique()
    items        = df[MAKRO.ITEM].nunique()
    latest_month = df["_date"].max()
    active = df[df["_date"] == latest_month][MAKRO.CUST_NUM].nunique()
    return dict(revenue=total_rev, profit=total_profit, margin=margin,
                customers=customers, active=active, items=items)


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby("_date")
              .agg(Revenue=(MAKRO.REVENUE,"sum"), Profit=(MAKRO.PROFIT,"sum"))
              .reset_index().rename(columns={"_date":"Date"})
              .sort_values("Date"))


# ── DOW Analysis ──────────────────────────────────────────────────────────────

def dow_overview(df: pd.DataFrame) -> pd.DataFrame:
    """ภาพรวม: ลูกค้านิยมสั่งวันไหนรวมทุกราย"""
    return (df.groupby("_dow")
              .agg(Revenue=(MAKRO.REVENUE,"sum"), Orders=(MAKRO.DATE,"nunique"),
                   Customers=(MAKRO.CUST_NUM,"nunique"))
              .reindex(range(7), fill_value=0).reset_index()
              .rename(columns={"_dow":"DowNum"})
              .assign(Day=lambda x: x["DowNum"].map(dict(enumerate(DAY_TH)))))


def dow_by_division(df: pd.DataFrame) -> pd.DataFrame:
    """แยกตาม Division"""
    return (df.groupby(["_dow", MAKRO.DIVISION])
              .agg(Revenue=(MAKRO.REVENUE,"sum"))
              .reset_index()
              .assign(Day=lambda x: x["_dow"].map(dict(enumerate(DAY_TH)))))


def dow_by_customer(df: pd.DataFrame, cust_id) -> pd.DataFrame:
    """รายลูกค้า: สั่งวันไหนบ่อย"""
    sub = df[df[MAKRO.CUST_NUM] == cust_id]
    return (sub.groupby("_dow")
               .agg(Revenue=(MAKRO.REVENUE,"sum"), Orders=(MAKRO.DATE,"nunique"))
               .reindex(range(7), fill_value=0).reset_index()
               .rename(columns={"_dow":"DowNum"})
               .assign(Day=lambda x: x["DowNum"].map(dict(enumerate(DAY_TH)))))


def _preferred_dow(df: pd.DataFrame, cust_id) -> int:
    """หา DOW ที่ลูกค้าสั่งบ่อยที่สุด (0=จันทร์)"""
    sub = df[df[MAKRO.CUST_NUM] == cust_id]
    if sub.empty:
        return 0
    return int(sub.groupby("_dow")["Date"].nunique().idxmax())


# ── Restock Prediction (gap-based) ───────────────────────────────────────────

def predict_restock(df: pd.DataFrame, horizon_days: int = 30) -> pd.DataFrame:
    """
    Gap-based restock prediction:
    1. คำนวณ avg gap จาก transaction dates จริง (ไม่ใช่ monthly)
    2. หา preferred DOW ของลูกค้าแต่ละราย
    3. call_date = วัน preferred DOW ที่ใกล้ที่สุดหลัง predicted_next - 1 วัน
    4. รวมเป็น 1 record ต่อลูกค้า พร้อม list items ที่ต้องสั่ง
    """
    if df.empty:
        return pd.DataFrame()

    ref_date = df[MAKRO.DATE].max()
    records = []

    for cust_id, cust_df in df.groupby(MAKRO.CUST_NUM):
        cust_name = cust_df[MAKRO.CUSTOMER].iloc[0]
        cust_type = cust_df[MAKRO.CUST_TYPE].iloc[0] if MAKRO.CUST_TYPE in cust_df.columns else ""

        # Preferred DOW
        dow_counts = cust_df.groupby("_dow")[MAKRO.DATE].nunique()
        preferred_dow = int(dow_counts.idxmax())

        items_due = []

        for item, item_df in cust_df.groupby(MAKRO.ITEM):
            dates = sorted(item_df[MAKRO.DATE].dt.normalize().unique())
            if len(dates) < 2:
                continue

            gaps = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
            # ใช้ median แทน mean เพื่อกันค่า outlier
            avg_gap = float(np.median(gaps))
            if avg_gap < 1:
                continue

            last_date    = pd.Timestamp(dates[-1])
            predicted_next = last_date + pd.Timedelta(days=avg_gap)

            # หา preferred DOW ที่ใกล้ที่สุด >= predicted_next
            days_to_dow = (preferred_dow - predicted_next.dayofweek) % 7
            order_day   = predicted_next + pd.Timedelta(days=days_to_dow)
            call_day    = order_day - pd.Timedelta(days=1)

            days_until_call = (call_day - ref_date).days

            if -3 <= days_until_call <= horizon_days:
                rev = item_df[MAKRO.REVENUE].sum()
                items_due.append({
                    "item":          item,
                    "class":         item_df[MAKRO.CLASS].iloc[0],
                    "avg_gap":       round(avg_gap, 1),
                    "last_purchase": last_date.date(),
                    "predicted_next":predicted_next.date(),
                    "call_day":      call_day.date(),
                    "days_until_call": days_until_call,
                    "avg_revenue":   rev / len(dates),
                })

        if not items_due:
            continue

        # เลือก call_day ที่เร็วที่สุดเป็นตัวแทนของลูกค้า
        items_due.sort(key=lambda x: x["days_until_call"])
        earliest = items_due[0]

        def _urgency(d):
            if d <= 0:  return "CRITICAL"
            if d <= 3:  return "HIGH"
            if d <= 7:  return "MEDIUM"
            return "OK"

        records.append({
            MAKRO.CUST_NUM:   cust_id,
            MAKRO.CUSTOMER:   cust_name,
            MAKRO.CUST_TYPE:  cust_type,
            "preferred_dow":  preferred_dow,
            "preferred_dow_name": DAY_TH[preferred_dow],
            "call_day":       earliest["call_day"],
            "days_until_call":earliest["days_until_call"],
            "urgency":        _urgency(earliest["days_until_call"]),
            "items_count":    len(items_due),
            "items_detail":   items_due,      # list สำหรับ drill-down
        })

    if not records:
        return pd.DataFrame()

    return (pd.DataFrame(records)
              .sort_values("days_until_call")
              .reset_index(drop=True))


def restock_items_for_customer(restock_df: pd.DataFrame, cust_id) -> list:
    """คืน items_detail ของลูกค้าคนนั้น"""
    row = restock_df[restock_df[MAKRO.CUST_NUM] == cust_id]
    if row.empty:
        return []
    return row.iloc[0]["items_detail"]


# ── Top Items (Pareto) ────────────────────────────────────────────────────────

def top_items_by_division(df: pd.DataFrame, division: str = "ALL", n_top: int = 10) -> pd.DataFrame:
    sub = df if division == "ALL" else df[df[MAKRO.DIVISION] == division]
    qty_agg = (MAKRO.QTY,"sum") if MAKRO.QTY in df.columns else (MAKRO.REVENUE,"count")
    return (sub.groupby([MAKRO.ITEM, MAKRO.DIVISION, MAKRO.CLASS, MAKRO.DEPT])
               .agg(Revenue=(MAKRO.REVENUE,"sum"), Profit=(MAKRO.PROFIT,"sum"),
                    Qty=qty_agg, Customers=(MAKRO.CUST_NUM,"nunique"),
                    Months=("_date","nunique"))
               .reset_index()
               .sort_values("Revenue", ascending=False)
               .head(n_top).reset_index(drop=True))


def pareto_items(df: pd.DataFrame, division: str = "ALL", threshold: float = 0.80) -> pd.DataFrame:
    sub = df if division == "ALL" else df[df[MAKRO.DIVISION] == division]
    item_rev = (sub.groupby([MAKRO.ITEM, MAKRO.DIVISION, MAKRO.CLASS, MAKRO.DEPT])
                   .agg(Revenue=(MAKRO.REVENUE,"sum"), Profit=(MAKRO.PROFIT,"sum"),
                        Customers=(MAKRO.CUST_NUM,"nunique"), Months=("_date","nunique"))
                   .reset_index()
                   .sort_values("Revenue", ascending=False))
    total = item_rev["Revenue"].sum()
    item_rev["CumRevenue"] = item_rev["Revenue"].cumsum()
    item_rev["CumPct"]     = item_rev["CumRevenue"] / total * 100
    item_rev["RevPct"]     = item_rev["Revenue"] / total * 100
    pareto = item_rev[item_rev["CumRevenue"] <= total * threshold].copy()
    if pareto.empty or pareto["CumRevenue"].max() < total * threshold:
        if len(pareto) < len(item_rev):
            pareto = pd.concat([pareto, item_rev.iloc[[len(pareto)]]], ignore_index=True)
    pareto = pareto.reset_index(drop=True)
    pareto.index = pareto.index + 1
    return pareto


# ── Item Detail ───────────────────────────────────────────────────────────────

def item_dow_pattern(df: pd.DataFrame, item_name: str) -> pd.DataFrame:
    sub = df[df[MAKRO.ITEM] == item_name]
    dow = (sub.groupby("_dow")
              .agg(Revenue=(MAKRO.REVENUE,"sum"), Orders=(MAKRO.DATE,"nunique"))
              .reindex(range(7), fill_value=0).reset_index()
              .rename(columns={"_dow":"DowNum"}))
    dow["Day"] = dow["DowNum"].map(dict(enumerate(DAY_TH)))
    return dow


def item_top_customers(df: pd.DataFrame, item_name: str, n: int = 10) -> pd.DataFrame:
    sub = df[df[MAKRO.ITEM] == item_name]
    qty_agg = (MAKRO.QTY,"sum") if MAKRO.QTY in df.columns else (MAKRO.REVENUE,"count")
    return (sub.groupby([MAKRO.CUST_NUM, MAKRO.CUSTOMER, MAKRO.CUST_TYPE])
               .agg(Revenue=(MAKRO.REVENUE,"sum"), Qty=qty_agg, Months=("_date","nunique"))
               .reset_index().sort_values("Revenue", ascending=False)
               .head(n).reset_index(drop=True))


def item_monthly_trend(df: pd.DataFrame, item_name: str) -> pd.DataFrame:
    sub = df[df[MAKRO.ITEM] == item_name]
    qty_agg = (MAKRO.QTY,"sum") if MAKRO.QTY in df.columns else (MAKRO.REVENUE,"count")
    return (sub.groupby("_date")
               .agg(Revenue=(MAKRO.REVENUE,"sum"), Qty=qty_agg)
               .reset_index().rename(columns={"_date":"Date"}).sort_values("Date"))


# ── RFM ──────────────────────────────────────────────────────────────────────

def compute_rfm(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    now = df["_date"].max()
    total_months = df["_date"].nunique()
    agg = df.groupby([MAKRO.CUST_NUM, MAKRO.CUSTOMER]).agg(
        last_date   = ("_date","max"),
        freq        = ("_date","nunique"),
        revenue     = (MAKRO.REVENUE,"sum"),
        profit      = (MAKRO.PROFIT,"sum"),
        items_count = (MAKRO.ITEM,"nunique"),
    ).reset_index()
    agg["recency_months"] = ((now - agg["last_date"]).dt.days / 30).round(1)
    agg["margin_pct"] = (agg["profit"] / agg["revenue"].replace(0, np.nan) * 100).fillna(0)

    def _safe_qcut(series, q, labels):
        try:
            return pd.qcut(series, q=q, labels=labels, duplicates="drop").astype(int)
        except ValueError:
            ranks = series.rank(method="first")
            n = len(ranks)
            return ((ranks / n * len(labels)).clip(0, len(labels)-1).astype(int) + 1).clip(1, len(labels))

    agg["r_score"] = _safe_qcut(agg["recency_months"], 3, [3,2,1])
    agg["f_score"] = pd.cut(agg["freq"], bins=[0,1,2,total_months],
                             labels=[1,2,3], include_lowest=True).astype(int)
    agg["m_score"] = _safe_qcut(agg["revenue"], 3, [1,2,3])

    def _seg(row):
        r,f,m = row["r_score"], row["f_score"], row["m_score"]
        if r==3 and f>=2 and m>=2: return RFM.CHAMPION
        if r>=2 and f>=2:          return RFM.LOYAL
        if r==3 and f==1:          return RFM.NEW
        if r==3 and m==1:          return RFM.PROMISING
        if r==2 and m<=2:          return RFM.AT_RISK
        return RFM.CHURNING

    agg["segment"] = agg.apply(_seg, axis=1)
    return agg.sort_values("revenue", ascending=False).reset_index(drop=True)


# ── Today's Calls (from restock) ─────────────────────────────────────────────

def top5_calls_today(df, restock_df=None, rfm_df=None) -> pd.DataFrame:
    calls = []

    if restock_df is not None and not restock_df.empty:
        urgent = restock_df[restock_df["urgency"].isin(["CRITICAL","HIGH","MEDIUM"])]
        for _, row in urgent.iterrows():
            d = row["days_until_call"]
            n_items = row["items_count"]
            items_preview = ", ".join(i["item"][:20] for i in row["items_detail"][:2])
            if n_items > 2:
                items_preview += f" +{n_items-2} อื่นๆ"
            if d <= 0:
                reason = f"⚠️ ควรโทรแล้ว ({abs(int(d))} วันที่แล้ว)"
                script = f"สวัสดีครับ {row[MAKRO.CUSTOMER]} — มีสินค้าที่น่าจะใกล้หมดแล้ว: {items_preview} สะดวกสั่งเพิ่มได้เลยครับ"
            else:
                reason = f"📦 Restock ใน {int(d)} วัน ({n_items} รายการ)"
                script = f"สวัสดีครับ {row[MAKRO.CUSTOMER]} — วัน{row['preferred_dow_name']}นี้/หน้าลูกค้ามักสั่ง: {items_preview} โทรเตรียมก่อน 1 วัน"
            calls.append({
                "priority":      1 if d <= 0 else (2 if d <= 3 else 3),
                MAKRO.CUST_NUM:  row[MAKRO.CUST_NUM],
                MAKRO.CUSTOMER:  row[MAKRO.CUSTOMER],
                "reason":        reason,
                "script":        script,
                "urgency":       row["urgency"],
                "call_day":      row["call_day"],
            })

    if rfm_df is not None and not rfm_df.empty:
        existing = {c[MAKRO.CUST_NUM] for c in calls}
        for _, row in rfm_df[rfm_df["segment"].isin([RFM.CHURNING, RFM.AT_RISK])].iterrows():
            if row[MAKRO.CUST_NUM] in existing:
                continue
            calls.append({
                "priority":      2,
                MAKRO.CUST_NUM:  row[MAKRO.CUST_NUM],
                MAKRO.CUSTOMER:  row[MAKRO.CUSTOMER],
                "reason":        f"📉 {row['segment']} — ยอดลดลงต่อเนื่อง",
                "script":        f"สวัสดีครับ {row[MAKRO.CUSTOMER]} — ช่วงนี้ยอดสั่งลดลง มีอะไรให้ช่วยดูแลมั้ยครับ?",
                "urgency":       "HIGH",
                "call_day":      None,
            })

    if not calls:
        return pd.DataFrame()
    return (pd.DataFrame(calls).sort_values("priority")
              .drop_duplicates(subset=[MAKRO.CUST_NUM]).head(5).reset_index(drop=True))


# ── Customer Detail ───────────────────────────────────────────────────────────

def customer_monthly(df, cust_id):
    sub = df[df[MAKRO.CUST_NUM] == cust_id]
    return (sub.groupby("_date")
               .agg(Revenue=(MAKRO.REVENUE,"sum"), Profit=(MAKRO.PROFIT,"sum"),
                    Items=(MAKRO.ITEM,"nunique"))
               .reset_index().rename(columns={"_date":"Date"}).sort_values("Date"))


def customer_top_items(df, cust_id, n=30):
    sub = df[df[MAKRO.CUST_NUM] == cust_id]
    return (sub.groupby([MAKRO.ITEM, MAKRO.CLASS, MAKRO.DEPT])
               .agg(Revenue=(MAKRO.REVENUE,"sum"), Profit=(MAKRO.PROFIT,"sum"),
                    Months=("_date","nunique"))
               .reset_index().sort_values("Revenue", ascending=False).head(n))


def customer_dept_mix(df, cust_id):
    sub = df[df[MAKRO.CUST_NUM] == cust_id]
    return (sub.groupby(MAKRO.DEPT).agg(Revenue=(MAKRO.REVENUE,"sum"))
               .reset_index().sort_values("Revenue", ascending=False))


def upsell_suggestions(df: pd.DataFrame, cust_id, n: int = 8) -> pd.DataFrame:
    cust_rows = df[df[MAKRO.CUST_NUM] == cust_id]
    if cust_rows.empty:
        return pd.DataFrame()
    cust_type = cust_rows[MAKRO.CUST_TYPE].iloc[0]
    my_items  = set(cust_rows[MAKRO.ITEM].unique())
    peer_df   = df[(df[MAKRO.CUST_TYPE] == cust_type) & (df[MAKRO.CUST_NUM] != cust_id)]
    if peer_df.empty:
        return pd.DataFrame()
    candidates = (peer_df.groupby([MAKRO.ITEM, MAKRO.CLASS, MAKRO.DEPT])
                         .agg(Revenue=(MAKRO.REVENUE,"sum"),
                              PeerCount=(MAKRO.CUST_NUM,"nunique"))
                         .reset_index()
                         .sort_values(["PeerCount","Revenue"], ascending=False))
    return candidates[~candidates[MAKRO.ITEM].isin(my_items)].head(n).reset_index(drop=True)


# ── backward compat alias ─────────────────────────────────────────────────────
def predict_oos(df, reference_date=None):
    """Alias เพื่อ backward compat — ใช้ predict_restock แทน"""
    return predict_restock(df)
