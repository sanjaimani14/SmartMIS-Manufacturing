"""
SmartMIS Plotly Chart Theme - Industrial Analytics Visual Styling.
Uniform color palette, smooth gridlines, rounded bars, and high-contrast hover labels.
Includes specialized visual generators: Gauge Charts, COPQ Treemap, and Process Heatmap.
"""
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Industrial Color Palette matching design direction
INDUSTRIAL_PALETTE: List[str] = [
    "#2D7FF9",  # Electric Blue (Primary)
    "#FF6B1A",  # Safety Orange (Accent)
    "#00C2A8",  # Teal (Quality/FPY)
    "#FFB020",  # Amber (Warning/Downtime)
    "#FF4D4F",  # Alert Red (Rejection/Scrap)
    "#8B5CF6",  # Violet (Forecasting/COPQ)
    "#0B1F3A",  # Deep Navy (Contrast)
    "#38BDF8",  # Sky Blue
]

CHART_LAYOUT_DEFAULTS: Dict[str, Any] = {
    "font": {
        "family": "Plus Jakarta Sans, Inter, -apple-system, sans-serif",
        "color": "#334155",
        "size": 12,
    },
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "margin": dict(l=35, r=25, t=45, b=35),
    "hoverlabel": {
        "bgcolor": "#0B1F3A",
        "font_size": 12,
        "font_family": "Plus Jakarta Sans, Inter, sans-serif",
        "font_color": "#FFFFFF",
        "bordercolor": "#2D7FF9",
    },
    "xaxis": {
        "gridcolor": "#E2E8F0",
        "linecolor": "#CBD5E1",
        "zerolinecolor": "#CBD5E1",
        "showline": True,
        "ticks": "outside",
        "tickfont": {"color": "#64748B", "size": 11},
        "title_font": {"color": "#334155", "size": 12},
    },
    "yaxis": {
        "gridcolor": "#E2E8F0",
        "linecolor": "#CBD5E1",
        "zerolinecolor": "#CBD5E1",
        "showline": True,
        "ticks": "outside",
        "tickfont": {"color": "#64748B", "size": 11},
        "title_font": {"color": "#334155", "size": 12},
    },
    "legend": {
        "orientation": "h",
        "yanchor": "top",
        "y": -0.20,
        "xanchor": "center",
        "x": 0.5,
        "bgcolor": "rgba(255, 255, 255, 0.85)",
        "bordercolor": "#E2E8F0",
        "borderwidth": 1,
        "font": {"color": "#334155", "size": 11},
    },
}


def apply_chart_theme(
    fig: go.Figure,
    title: Optional[str] = None,
    height: Optional[int] = None,
    show_legend: bool = True,
    hovermode: Optional[str] = None,
    legend_bottom: bool = True,
    dark_mode: Optional[bool] = None,
) -> go.Figure:
    """
    Applies unified 'Smart Factory Control Room' styling to any Plotly figure.
    - Unified industrial color sequence
    - Soft clean gridlines and transparent background
    - Smooth continuous curves for lines
    - Rounded aesthetics for bar charts
    - Donut styling for pie charts
    - Bottom horizontal legend and high-contrast tooltip hover labels
    """
    if fig is None:
        return fig

    if dark_mode is None:
        try:
            dark_mode = st.session_state.get("dark_mode", False) if hasattr(st, "session_state") else False
        except Exception:
            dark_mode = False

    font_color = "#E6EEF9" if dark_mode else "#334155"
    grid_color = "rgba(255, 255, 255, 0.10)" if dark_mode else "#E2E8F0"
    line_color = "rgba(255, 255, 255, 0.20)" if dark_mode else "#CBD5E1"
    tick_color = "#9FB3CC" if dark_mode else "#64748B"
    title_color = "#FFFFFF" if dark_mode else "#0B1F3A"
    legend_bg = "rgba(14, 34, 64, 0.85)" if dark_mode else "rgba(255, 255, 255, 0.85)"
    legend_border = "rgba(255, 255, 255, 0.15)" if dark_mode else "#E2E8F0"

    updates: Dict[str, Any] = {
        "paper_bgcolor": CHART_LAYOUT_DEFAULTS["paper_bgcolor"],
        "plot_bgcolor": CHART_LAYOUT_DEFAULTS["plot_bgcolor"],
        "colorway": INDUSTRIAL_PALETTE,
        "font": {
            "family": "Plus Jakarta Sans, Inter, -apple-system, sans-serif",
            "color": font_color,
            "size": 12,
        },
        "hoverlabel": CHART_LAYOUT_DEFAULTS["hoverlabel"],
        "showlegend": show_legend,
    }

    if legend_bottom and show_legend:
        updates["legend"] = {
            "orientation": "h",
            "yanchor": "top",
            "y": -0.20,
            "xanchor": "center",
            "x": 0.5,
            "bgcolor": legend_bg,
            "bordercolor": legend_border,
            "borderwidth": 1,
            "font": {"color": font_color, "size": 11},
        }

    if hovermode:
        updates["hovermode"] = hovermode

    if title:
        updates["title"] = {
            "text": f"<b>{title}</b>",
            "font": {"size": 14, "color": title_color, "family": "Plus Jakarta Sans, sans-serif"},
            "x": 0.02,
            "y": 0.96,
        }

    if height:
        updates["height"] = height

    # Trace-level enhancements
    for trace in fig.data:
        t_type = getattr(trace, "type", "")
        # Smooth line interpolation for non-dashed line traces
        if t_type == "scatter":
            mode = getattr(trace, "mode", "") or ""
            if "lines" in mode:
                line_obj = getattr(trace, "line", None)
                dash = getattr(line_obj, "dash", None) if line_obj else None
                # Keep dash straight, make regular lines smooth spline
                if not dash and line_obj is not None:
                    try:
                        trace.line.shape = "spline"
                        if getattr(trace.line, "width", None) is None or trace.line.width < 2:
                            trace.line.width = 2.5
                    except Exception:
                        pass
        elif t_type == "bar":
            updates["bargap"] = 0.24
            updates["bargroupgap"] = 0.08
        elif t_type == "pie":
            if not getattr(trace, "hole", None):
                trace.hole = 0.48

    fig.update_layout(**updates)

    # Style axes
    fig.update_xaxes(
        gridcolor=grid_color,
        linecolor=line_color,
        zerolinecolor=line_color,
        showline=True,
        ticks="outside",
        tickfont={"color": tick_color, "size": 11},
        title_font={"color": font_color, "size": 12},
    )
    fig.update_yaxes(
        gridcolor=grid_color,
        linecolor=line_color,
        zerolinecolor=line_color,
        showline=True,
        ticks="outside",
        tickfont={"color": tick_color, "size": 11},
        title_font={"color": font_color, "size": 12},
    )

    # If secondary y-axis exists (e.g. Pareto or 2-axis charts), style it
    try:
        fig.update_layout(
            yaxis2=dict(
                gridcolor=grid_color,
                linecolor=line_color,
                tickfont=dict(color=tick_color, size=11),
                title_font=dict(color=font_color, size=12),
            )
        )
    except Exception:
        pass

    return fig


# ==============================================================================
# 2. RICH VISUAL GENERATORS (GAUGES, TREEMAP, HEATMAP)
# ==============================================================================

def create_gauge_chart(
    value: float,
    title: str,
    min_val: float = 0.0,
    max_val: float = 100.0,
    target: Optional[float] = None,
    gauge_type: str = "oee",
    height: int = 240,
    dark_mode: Optional[bool] = None,
) -> go.Figure:
    """
    Renders an industrial radial dial gauge with red/amber/green process performance zones.
    - gauge_type='oee': higher is better (red <60%, amber 60-75%, blue 75-85%, green 85-100%)
    - gauge_type='rejection': lower is better (green <=3%, amber 3-5%, red >5%)
    """
    if dark_mode is None:
        try:
            dark_mode = st.session_state.get("dark_mode", False) if hasattr(st, "session_state") else False
        except Exception:
            dark_mode = False

    number_color = "#FFFFFF" if dark_mode else "#0B1F3A"
    title_color = "#E6EEF9" if dark_mode else "#64748B"
    tick_color = "#9FB3CC" if dark_mode else "#64748B"
    gauge_bg = "rgba(255, 255, 255, 0.06)" if dark_mode else "#FFFFFF"
    gauge_border = "rgba(255, 255, 255, 0.15)" if dark_mode else "#E2E8F0"
    threshold_color = "#FFFFFF" if dark_mode else "#0B1F3A"

    fig = go.Figure()

    if gauge_type == "oee":
        steps = [
            dict(range=[0, 60], color="rgba(255, 77, 79, 0.22)"),
            dict(range=[60, 75], color="rgba(255, 176, 32, 0.22)"),
            dict(range=[75, 85], color="rgba(45, 127, 249, 0.20)"),
            dict(range=[85, 100], color="rgba(34, 197, 94, 0.25)"),
        ]
        bar_color = "#00C2A8"
        val_suffix = "%"
        threshold_val = target if target is not None else 85.0
    else:  # rejection
        actual_max = max(max_val, float(value) + 2.0)
        steps = [
            dict(range=[0, 3.0], color="rgba(34, 197, 94, 0.25)"),
            dict(range=[3.0, 5.0], color="rgba(255, 176, 32, 0.25)"),
            dict(range=[5.0, actual_max], color="rgba(255, 77, 79, 0.25)"),
        ]
        bar_color = "#FF4D4F" if value > 5.0 else ("#FFB020" if value > 3.0 else "#22C55E")
        val_suffix = "%"
        threshold_val = target if target is not None else 3.0
        max_val = actual_max

    indicator_args: Dict[str, Any] = {
        "mode": "gauge+number" if target is None else "gauge+number+delta",
        "value": round(float(value), 2),
        "number": {"suffix": val_suffix, "font": {"family": "Plus Jakarta Sans, sans-serif", "size": 30, "color": number_color}},
        "title": {"text": f"<b>{title}</b>", "font": {"family": "Plus Jakarta Sans, sans-serif", "size": 13, "color": title_color}},
        "gauge": {
            "axis": {"range": [min_val, max_val], "tickwidth": 1, "tickcolor": tick_color, "tickfont": {"size": 10, "color": tick_color}},
            "bar": {"color": bar_color, "thickness": 0.32},
            "bgcolor": gauge_bg,
            "borderwidth": 1,
            "bordercolor": gauge_border,
            "steps": steps,
            "threshold": {
                "line": {"color": threshold_color, "width": 3},
                "thickness": 0.8,
                "value": threshold_val,
            },
        },
    }

    if target is not None:
        indicator_args["delta"] = {
            "reference": target,
            "suffix": "% vs Target",
            "increasing": {"color": "#22C55E" if gauge_type == "oee" else "#FF4D4F"},
            "decreasing": {"color": "#FF4D4F" if gauge_type == "oee" else "#22C55E"},
            "font": {"size": 11},
        }

    fig.add_trace(go.Indicator(**indicator_args))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=25, r=25, t=40, b=15),
        height=height,
    )
    return fig


def create_copq_treemap(
    df: pd.DataFrame,
    cost_table: Optional[Dict[str, Dict[str, float]]] = None,
    title: str = "Cost of Poor Quality Loss Treemap (Dept ➔ Machine ➔ Defect)",
    height: int = 380,
) -> go.Figure:
    """
    Renders an interactive hierarchical Treemap showing COPQ financial distribution
    nested from Department -> Machine -> Defect.
    """
    if df.empty or "rejected" not in df.columns:
        fig = go.Figure()
        return apply_chart_theme(fig, title=title, height=height)

    costs = cost_table or {}
    d = df.copy()

    # Calculate financial loss per record
    scrap = d["scrap"] if "scrap" in d.columns else d["rejected"] * 0.85
    rework = d["rework"] if "rework" in d.columns else d["rejected"] * 0.15

    d["unit_scrap"] = d["product"].map(lambda p: costs.get(p, {}).get("scrap", 1000.0))
    d["unit_rework"] = d["product"].map(lambda p: costs.get(p, {}).get("rework", 300.0))
    d["total_copq_inr"] = (scrap * d["unit_scrap"] + rework * d["unit_rework"]).round(0)

    # Filter to defect records
    rej_d = d[d["rejected"] > 0]
    if rej_d.empty:
        fig = go.Figure()
        return apply_chart_theme(fig, title=title, height=height)

    # Group by hierarchy
    grouped = (
        rej_d.groupby(["department", "machine", "defect"])
        .agg(
            total_copq_inr=("total_copq_inr", "sum"),
            rejected_units=("rejected", "sum"),
        )
        .reset_index()
    )
    grouped = grouped[grouped["total_copq_inr"] > 0]

    fig = px.treemap(
        grouped,
        path=["department", "machine", "defect"],
        values="total_copq_inr",
        color="total_copq_inr",
        color_continuous_scale="Purples",
        title=title,
    )

    fig.update_traces(
        textinfo="label+value+percent parent",
        hovertemplate="<b>%{label}</b><br>Financial Loss: ₹%{value:,.0f}<br>Share of Parent: %{percentParent:.1%}<extra></extra>",
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=15, r=15, t=45, b=15),
        coloraxis_colorbar=dict(
            title="Loss (₹)",
            thickness=12,
            len=0.7,
            tickfont=dict(size=10, color="#64748B"),
        ),
    )

    return apply_chart_theme(fig, title=title, height=height, show_legend=False)


def create_process_heatmap(
    df: pd.DataFrame,
    x_col: str = "machine",
    y_col: str = "defect",
    val_col: str = "rejected",
    title: str = "Shopfloor Non-Conformance Heatmap (Defect by Machine)",
    height: int = 340,
) -> go.Figure:
    """
    Renders a vibrant quality intensity matrix / heatmap of defect occurrences across machines.
    """
    if df.empty or val_col not in df.columns:
        fig = go.Figure()
        return apply_chart_theme(fig, title=title, height=height)

    rej_df = df[df[val_col] > 0]
    if rej_df.empty:
        fig = go.Figure()
        return apply_chart_theme(fig, title=title, height=height)

    pivot = rej_df.pivot_table(index=y_col, columns=x_col, values=val_col, aggfunc="sum", fill_value=0)

    # Vibrant industrial colorscale (Clean white -> Slate Blue -> Amber -> Alert Red)
    colorscale = [
        [0.0, "#F8FAFC"],
        [0.15, "#DBEAFE"],
        [0.45, "#FCD34D"],
        [0.75, "#FB923C"],
        [1.0, "#DC2626"],
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale=colorscale,
            text=pivot.values,
            texttemplate="%{text}",
            textfont=dict(size=11, color="#0B1F3A", family="Plus Jakarta Sans, sans-serif"),
            hoverongaps=False,
            hovertemplate="<b>Machine: %{x}</b><br>Defect: %{y}<br>Non-Conformances: <b>%{z:,} units</b><extra></extra>",
            colorbar=dict(
                title="Units",
                thickness=12,
                len=0.8,
                tickfont=dict(size=10, color="#64748B"),
            ),
        )
    )

    fig.update_layout(
        xaxis=dict(title="Production Equipment / Machine", tickangle=-30),
        yaxis=dict(title="Defect Classification"),
        margin=dict(l=30, r=20, t=50, b=45),
    )

    return apply_chart_theme(fig, title=title, height=height, show_legend=False)

