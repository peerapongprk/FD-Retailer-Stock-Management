"""RetailIQ — Chart builders (Plotly)."""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from database.schema import RFM_COLOR, RFM

_CHART_CONFIG = {"displayModeBar": False}
_BG = "rgba(0,0,0,0)"
_FONT = dict(family="Sarabun, sans-serif", color="#e2e8f0")

def _base_layout(**kwargs):
    base = dict(
        paper_bgcolor=_BG, plot_bgcolor=_BG,
        font=_FONT, margin=dict(l=10, r=10, t=30, b=10),
    )
    base.update(kwargs)
    return base


def revenue_trend_chart(trend_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=trend_df["Date"], y=trend_df["Revenue"],
        name="Revenue", marker_color="#3b82f6", opacity=0.85,
    ))
    fig.add_trace(go.Scatter(
        x=trend_df["Date"], y=trend_df["Profit"],
        name="Profit", mode="lines+markers",
        line=dict(color="#10b981", width=2),
        marker=dict(size=6),
    ))
    fig.update_layout(
        **_base_layout(legend=dict(orientation="h", y=1.1)),
        xaxis=dict(showgrid=False, tickformat="%b %Y"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)"),
        barmode="overlay",
    )
    return fig


def rfm_donut(rfm_df: pd.DataFrame) -> go.Figure:
    counts = rfm_df["segment"].value_counts()
    colors = [RFM_COLOR.get(s, "#6b7280") for s in counts.index]
    fig = go.Figure(go.Pie(
        labels=counts.index, values=counts.values,
        hole=0.55, marker_colors=colors,
        textinfo="label+percent",
        textfont=dict(size=11),
    ))
    fig.update_layout(**_base_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0)))
    return fig


def top_items_bar(items_df: pd.DataFrame) -> go.Figure:
    df = items_df.head(12).sort_values("Revenue")
    fig = go.Figure(go.Bar(
        y=df["Item"].str[:35], x=df["Revenue"],
        orientation="h",
        marker_color="#6366f1",
        text=df["Revenue"].apply(lambda v: f"฿{v:,.0f}"),
        textposition="outside",
    ))
    fig.update_layout(
        **_base_layout(margin=dict(l=10, r=60, t=10, b=10)),
        xaxis=dict(showgrid=False, visible=False),
        yaxis=dict(showgrid=False, tickfont=dict(size=10)),
        height=max(300, len(df) * 28),
    )
    return fig


def customer_revenue_bar(monthly_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=monthly_df["Date"], y=monthly_df["Revenue"],
        marker_color="#3b82f6", name="Revenue",
    ))
    fig.add_trace(go.Scatter(
        x=monthly_df["Date"], y=monthly_df["Profit"],
        mode="lines+markers", name="Profit",
        line=dict(color="#10b981", width=2),
    ))
    fig.update_layout(
        **_base_layout(legend=dict(orientation="h", y=1.1)),
        xaxis=dict(showgrid=False, tickformat="%b %Y"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)"),
    )
    return fig


def dept_pie(dept_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=dept_df["Department"], values=dept_df["Revenue"],
        hole=0.4, textinfo="label+percent",
        textfont=dict(size=10),
        marker=dict(colors=px.colors.qualitative.Set2),
    ))
    fig.update_layout(**_base_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0)))
    return fig


def oos_urgency_bar(oos_df: pd.DataFrame) -> go.Figure:
    df = oos_df.head(15).copy()
    color_map = {"CRITICAL": "#ef4444", "HIGH": "#f59e0b", "MEDIUM": "#3b82f6", "OK": "#10b981"}
    colors = df["urgency"].map(color_map).fillna("#6b7280")
    label = df["Customer Name"].str[:15] + " / " + df["Item"].str[:20]

    fig = go.Figure(go.Bar(
        x=df["days_until_runout"], y=label,
        orientation="h",
        marker_color=colors,
        text=df["days_until_runout"].apply(lambda d: f"{int(d)}d"),
        textposition="inside",
    ))
    fig.update_layout(
        **_base_layout(margin=dict(l=10, r=10, t=10, b=10)),
        xaxis=dict(title="วันที่เหลือ", showgrid=False),
        yaxis=dict(showgrid=False, tickfont=dict(size=10)),
        height=max(300, len(df) * 30),
    )
    return fig
