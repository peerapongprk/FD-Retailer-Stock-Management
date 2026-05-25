"""
RetailIQ — Data Engine
Analytics, RFM segmentation, and Predictive OOS algorithm.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from database.schema import MAKRO, FD_RETAILER_GROUP, RFM

# ── helpers ──────────────────────────────────────────────────────────────────

def _parse_month(month_str: str) -> pd.Timestamp:
    """Convert 'YYYY / MM' → Timestamp (first day of month)."""
    try:
        parts = str(month_str).replace(" ", "").split("/")
        return pd.Timestamp(year=int(parts[0]), month=int(parts[1]), day=1)
    except Exception:
        return pd.NaT


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize raw Makro export; filter to FD Retailer only."""
    df = df.copy()
    # Filter FD Retailer
    if MAKRO.CUST_GROUP in df.columns:
        df = df[df[MAKRO.CUST_GROUP] == FD_RETAILER_GROUP].copy()
    # Parse month → date
    df["_date"] = df[MAKRO.MONTH].apply(_parse_month)
    df = df.dropna(subset=["_date"])
    df[MAKRO.REVENUE] = pd.to_numeric(df[MAKRO.REVENUE], errors="coerce").fillna(0)
    df[MAKRO.PROFIT]  = pd.to_numeric(df[MAKRO.PROFIT],  errors="coerce").fillna(0)
    return df.reset_index(drop=True)


# ── KPIs ─────────────────────────────────────────────────────────────────────

def compute_kpis(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    total_rev    = df[MAKRO.REVENUE].sum()
    total_profit = df[MAKRO.PROFIT].sum()
    margin       = (total_profit / total_rev * 100) if total_rev else 0
    customers    = df[MAKRO.CUST_NUM].nunique()
    items        = df[MAKRO.ITEM].nunique()
    # Active = bought in latest month
    latest_month = df["_date"].max()
    active = df[df["_date"] == latest_month][MAKRO.CUST_NUM].nunique()
    return {
        "revenue":   total_rev,
        "profit":    total_profit,
        "margin":    margin,
        "customers": customers,
        "active":    active,
        "items":     items,
    }


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("_date")
        .agg(Revenue=(MAKRO.REVENUE, "sum"), Profit=(MAKRO.PROFIT, "sum"))
        .reset_index()
        .rename(columns={"_date": "Date"})
        .sort_values("Date")
    )


# ── RFM ──────────────────────────────────────────────────────────────────────

def compute_rfm(df: pd.DataFrame) -> pd.DataFrame:
    """
    Monthly-granularity RFM.
    R = months since last purchase (lower = better)
    F = number of distinct months active
    M = total revenue
    Returns DataFrame with RFM scores + Segment per customer.
    """
    if df.empty:
        return pd.DataFrame()

    now = df["_date"].max()
    total_months = df["_date"].nunique()

    agg = df.groupby([MAKRO.CUST_NUM, MAKRO.CUSTOMER]).agg(
        last_date   = ("_date", "max"),
        freq        = ("_date", "nunique"),        # months active
        revenue     = (MAKRO.REVENUE, "sum"),
        profit      = (MAKRO.PROFIT, "sum"),
        items_count = (MAKRO.ITEM, "nunique"),
    ).reset_index()

    agg["recency_months"] = ((now - agg["last_date"]).dt.days / 30).round(1)
    agg["margin_pct"] = (agg["profit"] / agg["revenue"].replace(0, np.nan) * 100).fillna(0)

    # Score 1–3 per dimension (robust to few unique values)
    def _safe_qcut(series, q, labels):
        try:
            return pd.qcut(series, q=q, labels=labels, duplicates="drop").astype(int)
        except ValueError:
            # Fallback: rank-based scoring
            ranks = series.rank(method="first")
            n = len(ranks)
            return ((ranks / n * len(labels)).clip(0, len(labels)-1).astype(int) + 1).clip(1, len(labels))

    agg["r_score"] = _safe_qcut(agg["recency_months"], q=3, labels=[3, 2, 1])
    agg["f_score"] = pd.cut(agg["freq"], bins=[0, 1, 2, total_months], labels=[1, 2, 3],
                            include_lowest=True).astype(int)
    agg["m_score"] = _safe_qcut(agg["revenue"], q=3, labels=[1, 2, 3])

    def _segment(row):
        r, f, m = row["r_score"], row["f_score"], row["m_score"]
        if r == 3 and f >= 2 and m >= 2:  return RFM.CHAMPION
        if r >= 2 and f >= 2:             return RFM.LOYAL
        if r == 3 and f == 1:             return RFM.NEW
        if r == 3 and m == 1:             return RFM.PROMISING
        if r == 2 and m <= 2:             return RFM.AT_RISK
        return RFM.CHURNING

    agg["segment"] = agg.apply(_segment, axis=1)
    return agg.sort_values("revenue", ascending=False).reset_index(drop=True)


# ── Customer Detail ───────────────────────────────────────────────────────────

def customer_monthly(df: pd.DataFrame, cust_id) -> pd.DataFrame:
    sub = df[df[MAKRO.CUST_NUM] == cust_id]
    return (
        sub.groupby("_date")
        .agg(Revenue=(MAKRO.REVENUE, "sum"), Profit=(MAKRO.PROFIT, "sum"),
             Items=(MAKRO.ITEM, "nunique"))
        .reset_index().rename(columns={"_date": "Date"})
        .sort_values("Date")
    )


def customer_top_items(df: pd.DataFrame, cust_id, n: int = 15) -> pd.DataFrame:
    sub = df[df[MAKRO.CUST_NUM] == cust_id]
    return (
        sub.groupby([MAKRO.ITEM, MAKRO.CLASS, MAKRO.DEPT])
        .agg(Revenue=(MAKRO.REVENUE, "sum"), Profit=(MAKRO.PROFIT, "sum"),
             Months=(MAKRO.MONTH, "nunique"))
        .reset_index()
        .sort_values("Revenue", ascending=False)
        .head(n)
    )


def customer_dept_mix(df: pd.DataFrame, cust_id) -> pd.DataFrame:
    sub = df[df[MAKRO.CUST_NUM] == cust_id]
    return (
        sub.groupby(MAKRO.DEPT)
        .agg(Revenue=(MAKRO.REVENUE, "sum"))
        .reset_index()
        .sort_values("Revenue", ascending=False)
    )


# ── Predictive OOS ────────────────────────────────────────────────────────────

def predict_oos(df: pd.DataFrame, reference_date: datetime = None) -> pd.DataFrame:
    """
    Predictive Out-of-Stock algorithm.

    Logic:
    1. For each customer-item pair, compute avg monthly spend
    2. Estimate consumption cycle = days per reorder (based on purchase frequency)
    3. From last purchase date, project next run-out date
    4. Flag items where predicted run-out is within next 14 days

    Returns DataFrame: cust_id, cust_name, item, class, dept,
                       avg_monthly_spend, last_purchase_month,
                       cycle_days, predicted_runout_date, urgency (HIGH/MED/LOW)
    """
    if df.empty:
        return pd.DataFrame()

    if reference_date is None:
        # Latest month in data + simulate "today" = end of that month
        latest = df["_date"].max()
        reference_date = (latest + pd.offsets.MonthEnd(0)).to_pydatetime()

    ref_ts = pd.Timestamp(reference_date)

    # Monthly spend per customer-item
    monthly = (
        df.groupby([MAKRO.CUST_NUM, MAKRO.CUSTOMER, MAKRO.ITEM, MAKRO.CLASS, MAKRO.DEPT, "_date"])
        [MAKRO.REVENUE].sum().reset_index()
    )

    # Only items bought in ≥ 2 months (enough history for cycle)
    item_counts = monthly.groupby([MAKRO.CUST_NUM, MAKRO.ITEM])["_date"].nunique()
    multi_month = item_counts[item_counts >= 2].reset_index()
    monthly = monthly.merge(multi_month[[MAKRO.CUST_NUM, MAKRO.ITEM]], on=[MAKRO.CUST_NUM, MAKRO.ITEM])

    if monthly.empty:
        return pd.DataFrame()

    agg = monthly.groupby([MAKRO.CUST_NUM, MAKRO.CUSTOMER, MAKRO.ITEM, MAKRO.CLASS, MAKRO.DEPT]).agg(
        avg_monthly_spend = (MAKRO.REVENUE, "mean"),
        months_bought     = ("_date", "nunique"),
        last_purchase     = ("_date", "max"),
    ).reset_index()

    # Consumption cycle: assume item lasts ~30 days × (1 / frequency_ratio)
    # frequency_ratio = months_bought / total_months_in_data
    total_months = df["_date"].nunique()
    agg["frequency_ratio"] = agg["months_bought"] / total_months
    agg["cycle_days"] = (30 / agg["frequency_ratio"].clip(lower=0.1)).clip(upper=90).round(0).astype(int)

    # Predicted run-out = last purchase end-of-month + cycle_days
    agg["last_purchase_eom"] = agg["last_purchase"] + pd.offsets.MonthEnd(0)
    agg["predicted_runout"]  = agg["last_purchase_eom"] + pd.to_timedelta(agg["cycle_days"], unit="D")

    # Days until run-out from reference date
    agg["days_until_runout"] = (agg["predicted_runout"] - ref_ts).dt.days

    # Urgency bands
    def _urgency(d):
        if d <= 3:   return "CRITICAL"
        if d <= 7:   return "HIGH"
        if d <= 14:  return "MEDIUM"
        return "OK"

    agg["urgency"] = agg["days_until_runout"].apply(_urgency)

    # Keep only actionable items (run-out within 30 days, or already overdue)
    result = agg[agg["days_until_runout"] <= 30].copy()
    result = result.sort_values(["days_until_runout"], ascending=True)

    return result[[
        MAKRO.CUST_NUM, MAKRO.CUSTOMER, MAKRO.ITEM, MAKRO.CLASS, MAKRO.DEPT,
        "avg_monthly_spend", "months_bought", "last_purchase",
        "cycle_days", "predicted_runout", "days_until_runout", "urgency"
    ]].reset_index(drop=True)


def top5_calls_today(df: pd.DataFrame, oos_df: pd.DataFrame = None,
                     rfm_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    Generate 'Today's Top 5 Calls' by combining:
    - CRITICAL/HIGH urgency OOS customers
    - Churning/At-Risk customers (RFM)
    Returns ranked list with reason + talking script.
    """
    calls = []

    if oos_df is not None and not oos_df.empty:
        critical = oos_df[oos_df["urgency"].isin(["CRITICAL", "HIGH"])].copy()
        for _, row in critical.iterrows():
            days = row["days_until_runout"]
            if days <= 0:
                script = f"สวัสดีครับ ตอนนี้ {row[MAKRO.ITEM]} น่าจะหมดสต็อกแล้ว — รีบสั่งเลยดีมั้ยครับ?"
            else:
                script = (f"สวัสดีครับ {row[MAKRO.CUSTOMER]} — "
                          f"คาดว่า {row[MAKRO.ITEM]} จะหมดในอีก {int(days)} วัน "
                          f"สะดวกสั่งเพิ่มเพื่อป้องกัน OOS ช่วงสุดสัปดาห์มั้ยครับ?")
            calls.append({
                "priority": 1 if days <= 3 else 2,
                MAKRO.CUST_NUM:  row[MAKRO.CUST_NUM],
                MAKRO.CUSTOMER:  row[MAKRO.CUSTOMER],
                "reason":  f"⚠️ OOS ใน {max(0,int(days))} วัน — {row[MAKRO.ITEM]}",
                "script":  script,
                "urgency": row["urgency"],
            })

    if rfm_df is not None and not rfm_df.empty:
        at_risk = rfm_df[rfm_df["segment"].isin([RFM.CHURNING, RFM.AT_RISK])].copy()
        for _, row in at_risk.iterrows():
            calls.append({
                "priority": 2 if row["segment"] == RFM.AT_RISK else 1,
                MAKRO.CUST_NUM:  row[MAKRO.CUST_NUM],
                MAKRO.CUSTOMER:  row[MAKRO.CUSTOMER],
                "reason":  f"📉 {row['segment']} — ยอดลดลงต่อเนื่อง",
                "script":  (f"สวัสดีครับ {row[MAKRO.CUSTOMER]} — "
                            f"สังเกตว่าช่วงนี้ยอดสั่งลดลง มีอะไรให้ช่วยดูแลมั้ยครับ?"),
                "urgency": "HIGH",
            })

    if not calls:
        return pd.DataFrame()

    result = (
        pd.DataFrame(calls)
        .sort_values("priority")
        .drop_duplicates(subset=[MAKRO.CUST_NUM])
        .head(5)
        .reset_index(drop=True)
    )
    result.index = result.index + 1
    return result


# ── Portfolio / Visit Plan ────────────────────────────────────────────────────

def generate_visit_plan(oos_df: pd.DataFrame, rfm_df: pd.DataFrame,
                        portfolio_ids: list, horizon_days: int = 14) -> pd.DataFrame:
    """
    Generate a visit/call plan for a sales rep's portfolio.
    Combines OOS urgency + RFM risk into a prioritized weekly schedule.
    """
    if not portfolio_ids:
        return pd.DataFrame()

    rows = []

    if oos_df is not None and not oos_df.empty:
        sub = oos_df[oos_df[MAKRO.CUST_NUM].isin(portfolio_ids)].copy()
        for _, row in sub.iterrows():
            d = int(row["days_until_runout"])
            rows.append({
                MAKRO.CUST_NUM:  row[MAKRO.CUST_NUM],
                MAKRO.CUSTOMER:  row[MAKRO.CUSTOMER],
                "visit_date":    (datetime.now() + timedelta(days=max(0, d - 3))).strftime("%Y-%m-%d"),
                "reason":        f"OOS Alert: {row[MAKRO.ITEM]}",
                "urgency":       row["urgency"],
            })

    if rfm_df is not None and not rfm_df.empty:
        sub = rfm_df[
            (rfm_df[MAKRO.CUST_NUM].isin(portfolio_ids)) &
            (rfm_df["segment"].isin([RFM.AT_RISK, RFM.CHURNING]))
        ]
        for _, row in sub.iterrows():
            rows.append({
                MAKRO.CUST_NUM:  row[MAKRO.CUST_NUM],
                MAKRO.CUSTOMER:  row[MAKRO.CUSTOMER],
                "visit_date":    datetime.now().strftime("%Y-%m-%d"),
                "reason":        f"RFM Alert: {row['segment']}",
                "urgency":       "HIGH" if row["segment"] == RFM.CHURNING else "MEDIUM",
            })

    if not rows:
        return pd.DataFrame()

    return (
        pd.DataFrame(rows)
        .sort_values("urgency", key=lambda s: s.map({"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "OK": 3}))
        .drop_duplicates(subset=[MAKRO.CUST_NUM])
        .reset_index(drop=True)
    )
