"""RetailIQ V2 — Chart builders (light theme)."""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from database.schema import RFM_COLOR, DAY_TH

_CFG = {"displayModeBar": False}

# Light theme palette
_C_BLUE   = "#1a6faf"
_C_TEAL   = "#0f7b55"
_C_AMBER  = "#c07a00"
_C_RED    = "#c0392b"
_C_PURPLE = "#7c4dbd"
_C_GRAY   = "#6b7280"
_GRID     = "#e5e7eb"
_BG       = "white"
_FONT     = dict(family="Sarabun, sans-serif", color="#1f2937", size=12)

def _base(h=None, **kw):
    d = dict(paper_bgcolor=_BG, plot_bgcolor=_BG, font=_FONT,
             margin=dict(l=8, r=8, t=28, b=8))
    if h: d["height"] = h
    d.update(kw)
    return d


def revenue_trend_chart(trend_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=trend_df["Date"], y=trend_df["Revenue"],
                         name="ยอดขาย", marker_color=_C_BLUE, opacity=0.85))
    fig.add_trace(go.Scatter(x=trend_df["Date"], y=trend_df["Profit"],
                             name="กำไร", mode="lines+markers",
                             line=dict(color=_C_TEAL, width=2), marker=dict(size=6)))
    fig.update_layout(**_base(legend=dict(orientation="h", y=1.12, x=0)),
                      xaxis=dict(showgrid=False, tickformat="%b %Y"),
                      yaxis=dict(showgrid=True, gridcolor=_GRID, zeroline=False))
    return fig


def rfm_donut(rfm_df: pd.DataFrame) -> go.Figure:
    counts = rfm_df["segment"].value_counts()
    colors = [RFM_COLOR.get(s, _C_GRAY) for s in counts.index]
    fig = go.Figure(go.Pie(labels=counts.index, values=counts.values,
                            hole=0.55, marker_colors=colors,
                            textinfo="label+percent", textfont=dict(size=11)))
    fig.update_layout(**_base(showlegend=False, margin=dict(l=0,r=0,t=8,b=0)))
    return fig


def top_items_bar(items_df: pd.DataFrame, title: str = "") -> go.Figure:
    df = items_df.head(10).sort_values("Revenue")
    colors = [_C_BLUE] * len(df)
    fig = go.Figure(go.Bar(
        y=df["Item"].str[:40], x=df["Revenue"],
        orientation="h", marker_color=colors,
        text=df["Revenue"].apply(lambda v: f"฿{v/1000:.1f}K"),
        textposition="outside", textfont=dict(size=11),
    ))
    fig.update_layout(**_base(h=max(280, len(df)*34),
                               margin=dict(l=8, r=70, t=28, b=8),
                               title=dict(text=title, font=dict(size=13), x=0)),
                      xaxis=dict(showgrid=False, visible=False),
                      yaxis=dict(showgrid=False, tickfont=dict(size=11)))
    return fig


def pareto_chart(pareto_df: pd.DataFrame) -> go.Figure:
    df = pareto_df.copy().reset_index(drop=True).head(50)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=list(range(1, len(df)+1)), y=df["Revenue"],
        marker_color=_C_BLUE, opacity=0.8, name="Revenue",
        text=df["Revenue"].apply(lambda v: f"฿{v/1000:.0f}K"),
        textposition="outside", textfont=dict(size=9),
    ))
    fig.add_trace(go.Scatter(
        x=list(range(1, len(df)+1)), y=df["CumPct"],
        yaxis="y2", mode="lines+markers",
        line=dict(color=_C_AMBER, width=2), marker=dict(size=4),
        name="Cumulative %",
    ))
    fig.add_hline(y=80, yref="y2", line_dash="dot",
                  line_color=_C_RED, line_width=1,
                  annotation_text="80%", annotation_position="top right",
                  annotation_font=dict(size=10, color=_C_RED))
    fig.update_layout(
        **_base(h=300, legend=dict(orientation="h", y=1.12, x=0)),
        xaxis=dict(showgrid=False, title="Rank"),
        yaxis=dict(showgrid=True, gridcolor=_GRID, zeroline=False, title="Revenue (฿)"),
        yaxis2=dict(overlaying="y", side="right", range=[0,105],
                    ticksuffix="%", showgrid=False, zeroline=False),
        bargap=0.1,
    )
    return fig


def dow_bar(dow_df: pd.DataFrame, title: str = "") -> go.Figure:
    """Bar chart by day of week."""
    fig = go.Figure(go.Bar(
        x=dow_df["Day"], y=dow_df["Revenue"],
        marker_color=[_C_BLUE if i < 5 else _C_TEAL for i in range(len(dow_df))],
        text=dow_df["Revenue"].apply(lambda v: f"฿{v/1000:.1f}K"),
        textposition="outside", textfont=dict(size=11),
    ))
    base = _base(h=240, margin=dict(l=8,r=8,t=32,b=8))
    if title: base["title"] = dict(text=title, font=dict(size=13), x=0)
    fig.update_layout(**base,
                      xaxis=dict(showgrid=False),
                      yaxis=dict(showgrid=True, gridcolor=_GRID, visible=False))
    return fig


def item_trend_chart(trend_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=trend_df["Date"], y=trend_df["Revenue"],
                         marker_color=_C_BLUE, name="Revenue"))
    fig.update_layout(**_base(h=180, margin=dict(l=8,r=8,t=16,b=8)),
                      xaxis=dict(showgrid=False, tickformat="%b %y"),
                      yaxis=dict(showgrid=True, gridcolor=_GRID, zeroline=False))
    return fig


def customer_revenue_bar(monthly_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly_df["Date"], y=monthly_df["Revenue"],
                         marker_color=_C_BLUE, name="ยอดขาย"))
    fig.add_trace(go.Scatter(x=monthly_df["Date"], y=monthly_df["Profit"],
                             mode="lines+markers", name="กำไร",
                             line=dict(color=_C_TEAL, width=2)))
    fig.update_layout(**_base(legend=dict(orientation="h", y=1.12, x=0)),
                      xaxis=dict(showgrid=False, tickformat="%b %Y"),
                      yaxis=dict(showgrid=True, gridcolor=_GRID, zeroline=False))
    return fig


def dept_pie(dept_df: pd.DataFrame) -> go.Figure:
    COLORS = [_C_BLUE, _C_TEAL, _C_AMBER, _C_PURPLE, _C_RED,
              "#0891b2","#7c3aed","#db2777","#ea580c","#65a30d"]
    fig = go.Figure(go.Pie(
        labels=dept_df["Department"], values=dept_df["Revenue"],
        hole=0.4, textinfo="label+percent", textfont=dict(size=10),
        marker=dict(colors=COLORS[:len(dept_df)]),
    ))
    fig.update_layout(**_base(showlegend=False, margin=dict(l=0,r=0,t=8,b=0)))
    return fig


def oos_urgency_bar(oos_df: pd.DataFrame) -> go.Figure:
    df = oos_df.head(15).copy()
    cmap = {"CRITICAL":_C_RED,"HIGH":_C_AMBER,"MEDIUM":_C_BLUE,"OK":_C_TEAL}
    colors = df["urgency"].map(cmap).fillna(_C_GRAY)
    label = df["Customer Name"].str[:14] + " · " + df["Item"].str[:18]
    fig = go.Figure(go.Bar(
        x=df["days_until_runout"], y=label, orientation="h",
        marker_color=colors,
        text=df["days_until_runout"].apply(lambda d: f"{int(d)}d"),
        textposition="inside",
    ))
    fig.update_layout(**_base(h=max(280, len(df)*30), margin=dict(l=8,r=8,t=16,b=8)),
                      xaxis=dict(title="วันที่เหลือ", showgrid=False),
                      yaxis=dict(showgrid=False, tickfont=dict(size=10)))
    return fig


def dow_heatmap(dow_div_df: pd.DataFrame) -> go.Figure:
    """Grouped bar by DOW and Division."""
    colors = {"DRY FOOD": _C_BLUE, "FRESH FOOD": _C_TEAL, "NON FOOD": _C_AMBER}
    fig = go.Figure()
    for div in ["DRY FOOD","FRESH FOOD","NON FOOD"]:
        sub = dow_div_df[dow_div_df.get("Division", dow_div_df.columns[1]) == div] if "Division" in dow_div_df.columns else pd.DataFrame()
        if sub.empty: continue
        sub = sub.set_index("_dow").reindex(range(7)).fillna(0).reset_index()
        sub["Day"] = sub["_dow"].map(dict(enumerate(DAY_TH)))
        fig.add_trace(go.Bar(x=sub["Day"], y=sub["Revenue"],
                             name=div, marker_color=colors.get(div,"#888")))
    fig.update_layout(**_base(h=280, legend=dict(orientation="h",y=1.1,x=0)),
                      barmode="group",
                      xaxis=dict(showgrid=False),
                      yaxis=dict(showgrid=True, gridcolor=_GRID))
    return fig


def restock_timeline_chart(restock_df: pd.DataFrame) -> go.Figure:
    """Bar chart: customers by days_until_call."""
    df = restock_df.copy()
    cmap = {"CRITICAL":_C_RED,"HIGH":_C_AMBER,"MEDIUM":_C_BLUE,"OK":_C_TEAL}
    # Group by days_until_call
    grp = (df.groupby(["days_until_call","urgency"])
             .size().reset_index(name="count")
             .sort_values("days_until_call"))
    fig = go.Figure()
    for urg in ["CRITICAL","HIGH","MEDIUM","OK"]:
        sub = grp[grp["urgency"]==urg]
        if sub.empty: continue
        fig.add_trace(go.Bar(x=sub["days_until_call"], y=sub["count"],
                             name=urg, marker_color=cmap.get(urg,"#888")))
    fig.update_layout(**_base(h=220, legend=dict(orientation="h",y=1.1,x=0)),
                      barmode="stack",
                      xaxis=dict(title="วันนับจากวันนี้", showgrid=False),
                      yaxis=dict(title="จำนวนลูกค้า", showgrid=True, gridcolor=_GRID))
    return fig
