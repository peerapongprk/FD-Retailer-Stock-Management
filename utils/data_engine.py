"""RetailIQ V2 — Data Engine"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from database.schema import MAKRO, FD_RETAILER_GROUP, RFM, DAY_TH


# ── clean ─────────────────────────────────────────────────────────────────────

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if MAKRO.CUST_GROUP in df.columns:
        df = df[df[MAKRO.CUST_GROUP] == FD_RETAILER_GROUP].copy()
    # Parse Date column (daily)
    df[MAKRO.DATE] = pd.to_datetime(df[MAKRO.DATE], errors="coerce")
    # Also keep month-level _date for trend
    df["_date"] = df[MAKRO.DATE].dt.to_period("M").dt.to_timestamp()
    df = df.dropna(subset=[MAKRO.DATE])
    df[MAKRO.REVENUE] = pd.to_numeric(df[MAKRO.REVENUE], errors="coerce").fillna(0)
    df[MAKRO.PROFIT]  = pd.to_numeric(df[MAKRO.PROFIT],  errors="coerce").fillna(0)
    if MAKRO.QTY in df.columns:
        df[MAKRO.QTY] = pd.to_numeric(df[MAKRO.QTY], errors="coerce").fillna(0)
    df["_dow"] = df[MAKRO.DATE].dt.dayofweek   # 0=Mon … 6=Sun
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


# ── Top Items (Pareto) ────────────────────────────────────────────────────────

def top_items_by_division(df: pd.DataFrame, division: str = "ALL", n_top: int = 10) -> pd.DataFrame:
    """Top n items by revenue for a division (or ALL)."""
    sub = df if division == "ALL" else df[df[MAKRO.DIVISION] == division]
    return (sub.groupby([MAKRO.ITEM, MAKRO.DIVISION, MAKRO.CLASS, MAKRO.DEPT])
               .agg(Revenue=(MAKRO.REVENUE,"sum"), Profit=(MAKRO.PROFIT,"sum"),
                    Qty=(MAKRO.QTY,"sum") if MAKRO.QTY in df.columns else (MAKRO.REVENUE,"count"),
                    Customers=(MAKRO.CUST_NUM,"nunique"), Months=("_date","nunique"))
               .reset_index()
               .sort_values("Revenue", ascending=False)
               .head(n_top)
               .reset_index(drop=True))


def pareto_items(df: pd.DataFrame, division: str = "ALL", threshold: float = 0.80) -> pd.DataFrame:
    """Return items that cumulatively make up `threshold` of total revenue."""
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
    # Keep items up to threshold
    pareto = item_rev[item_rev["CumRevenue"] <= total * threshold].copy()
    if pareto.empty or pareto["CumRevenue"].max() < total * threshold:
        # include one more row to cross threshold
        next_idx = len(pareto)
        if next_idx < len(item_rev):
            pareto = pd.concat([pareto, item_rev.iloc[[next_idx]]], ignore_index=True)
    pareto = pareto.reset_index(drop=True)
    pareto.index = pareto.index + 1  # rank from 1
    return pareto


# ── Item Detail ───────────────────────────────────────────────────────────────

def item_dow_pattern(df: pd.DataFrame, item_name: str) -> pd.DataFrame:
    """Revenue by day-of-week for a specific item."""
    sub = df[df[MAKRO.ITEM] == item_name]
    dow = (sub.groupby("_dow")
              .agg(Revenue=(MAKRO.REVENUE,"sum"), Orders=(MAKRO.DATE,"nunique"))
              .reindex(range(7), fill_value=0)
              .reset_index()
              .rename(columns={"_dow":"DowNum"}))
    dow["Day"] = dow["DowNum"].map(dict(enumerate(DAY_TH)))
    return dow


def item_top_customers(df: pd.DataFrame, item_name: str, n: int = 10) -> pd.DataFrame:
    """Top n customers by revenue for a specific item."""
    sub = df[df[MAKRO.ITEM] == item_name]
    return (sub.groupby([MAKRO.CUST_NUM, MAKRO.CUSTOMER, MAKRO.CUST_TYPE])
               .agg(Revenue=(MAKRO.REVENUE,"sum"), Qty=(MAKRO.QTY,"sum") if MAKRO.QTY in df.columns else (MAKRO.REVENUE,"count"),
                    Months=("_date","nunique"))
               .reset_index()
               .sort_values("Revenue", ascending=False)
               .head(n)
               .reset_index(drop=True))


def item_monthly_trend(df: pd.DataFrame, item_name: str) -> pd.DataFrame:
    sub = df[df[MAKRO.ITEM] == item_name]
    return (sub.groupby("_date")
               .agg(Revenue=(MAKRO.REVENUE,"sum"), Qty=(MAKRO.QTY,"sum") if MAKRO.QTY in df.columns else (MAKRO.REVENUE,"count"))
               .reset_index().rename(columns={"_date":"Date"})
               .sort_values("Date"))


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
    agg["f_score"] = pd.cut(agg["freq"], bins=[0,1,2,total_months], labels=[1,2,3], include_lowest=True).astype(int)
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


# ── OOS Prediction ────────────────────────────────────────────────────────────

def predict_oos(df: pd.DataFrame, reference_date: datetime = None) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    if reference_date is None:
        reference_date = df[MAKRO.DATE].max().to_pydatetime()
    ref_ts = pd.Timestamp(reference_date)

    monthly = (df.groupby([MAKRO.CUST_NUM, MAKRO.CUSTOMER, MAKRO.ITEM,
                            MAKRO.CLASS, MAKRO.DEPT, "_date"])[MAKRO.REVENUE]
                 .sum().reset_index())
    item_counts = monthly.groupby([MAKRO.CUST_NUM, MAKRO.ITEM])["_date"].nunique()
    multi = item_counts[item_counts >= 2].reset_index()
    monthly = monthly.merge(multi[[MAKRO.CUST_NUM, MAKRO.ITEM]], on=[MAKRO.CUST_NUM, MAKRO.ITEM])
    if monthly.empty:
        return pd.DataFrame()

    agg = monthly.groupby([MAKRO.CUST_NUM, MAKRO.CUSTOMER, MAKRO.ITEM,
                            MAKRO.CLASS, MAKRO.DEPT]).agg(
        avg_monthly_spend = (MAKRO.REVENUE,"mean"),
        months_bought     = ("_date","nunique"),
        last_purchase     = ("_date","max"),
    ).reset_index()

    total_months = df["_date"].nunique()
    agg["frequency_ratio"] = agg["months_bought"] / total_months
    agg["cycle_days"] = (30 / agg["frequency_ratio"].clip(lower=0.1)).clip(upper=90).round(0).astype(int)
    agg["last_purchase_eom"] = agg["last_purchase"] + pd.offsets.MonthEnd(0)
    agg["predicted_runout"]  = agg["last_purchase_eom"] + pd.to_timedelta(agg["cycle_days"], unit="D")
    agg["days_until_runout"] = (agg["predicted_runout"] - ref_ts).dt.days

    def _urgency(d):
        if d <= 3:  return "CRITICAL"
        if d <= 7:  return "HIGH"
        if d <= 14: return "MEDIUM"
        return "OK"

    agg["urgency"] = agg["days_until_runout"].apply(_urgency)
    result = agg[agg["days_until_runout"] <= 30].copy()
    return result.sort_values("days_until_runout").reset_index(drop=True)


# ── Today's Calls ─────────────────────────────────────────────────────────────

def top5_calls_today(df, oos_df=None, rfm_df=None) -> pd.DataFrame:
    calls = []
    if oos_df is not None and not oos_df.empty:
        for _, row in oos_df[oos_df["urgency"].isin(["CRITICAL","HIGH"])].iterrows():
            d = row["days_until_runout"]
            calls.append({
                "priority": 1 if d <= 3 else 2,
                MAKRO.CUST_NUM:  row[MAKRO.CUST_NUM],
                MAKRO.CUSTOMER:  row[MAKRO.CUSTOMER],
                "reason":  f"⚠️ OOS ใน {max(0,int(d))} วัน — {row[MAKRO.ITEM]}",
                "script":  f"สวัสดีครับ คาดว่า {row[MAKRO.ITEM]} จะหมดในอีก {max(0,int(d))} วัน สะดวกสั่งเพิ่มมั้ยครับ?",
                "urgency": row["urgency"],
            })
    if rfm_df is not None and not rfm_df.empty:
        for _, row in rfm_df[rfm_df["segment"].isin([RFM.CHURNING, RFM.AT_RISK])].iterrows():
            calls.append({
                "priority": 2 if row["segment"] == RFM.AT_RISK else 1,
                MAKRO.CUST_NUM:  row[MAKRO.CUST_NUM],
                MAKRO.CUSTOMER:  row[MAKRO.CUSTOMER],
                "reason":  f"📉 {row['segment']} — ยอดลดลงต่อเนื่อง",
                "script":  f"สวัสดีครับ {row[MAKRO.CUSTOMER]} — ช่วงนี้ยอดสั่งลดลง มีอะไรให้ช่วยดูแลมั้ยครับ?",
                "urgency": "HIGH",
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


def customer_top_items(df, cust_id, n=15):
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
    """Items bought by same-type customers but NOT by this customer."""
    cust_type = df[df[MAKRO.CUST_NUM] == cust_id][MAKRO.CUST_TYPE].iloc[0] if not df[df[MAKRO.CUST_NUM] == cust_id].empty else None
    if cust_type is None:
        return pd.DataFrame()
    my_items = set(df[df[MAKRO.CUST_NUM] == cust_id][MAKRO.ITEM].unique())
    peer_df  = df[(df[MAKRO.CUST_TYPE] == cust_type) & (df[MAKRO.CUST_NUM] != cust_id)]
    candidates = (peer_df.groupby([MAKRO.ITEM, MAKRO.CLASS, MAKRO.DEPT])
                         .agg(Revenue=(MAKRO.REVENUE,"sum"), PeerCount=(MAKRO.CUST_NUM,"nunique"))
                         .reset_index()
                         .sort_values(["PeerCount","Revenue"], ascending=False))
    return candidates[~candidates[MAKRO.ITEM].isin(my_items)].head(n).reset_index(drop=True)
