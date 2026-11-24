"""
SmartMIS Plotly Chart Theme - Industrial Analytics Visual Styling.
Uniform color palette, smooth gridlines, rounded bars, and high-contrast hover labels.
"""
from typing import Any, Dict, List, Optional
import plotly.graph_objects as go

# Industrial Color Palette matching design direction
INDUSTRIAL_PALETTE: List[str] = [
    "#2D7FF9",  # Electric Blue (Primary)
    "#FF6B1A",  # Safety Orange (Accent)
    "#00C2A8",  # Teal (Quality/FPY)
    "#FFB020",  # Amber (Warning/Downtime)
    "#FF4D4F",  # Alert Red (Rejection/Scrap)
    "#8B5CF6",  # Violet (Forecasting)
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
    "margin": dict(l=30, r=20, t=40, b=30),
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
) -> go.Figure:
    """
    Applies unified 'Smart Factory Control Room' styling to any Plotly figure.
    - Uniform color sequence
    - Soft clean gridlines and transparent background
    - High-contrast tooltip hover labels
    - Rounded bar aesthetic
    """
    if fig is None:
        return fig

    updates: Dict[str, Any] = {
        "paper_bgcolor": CHART_LAYOUT_DEFAULTS["paper_bgcolor"],
        "plot_bgcolor": CHART_LAYOUT_DEFAULTS["plot_bgcolor"],
        "font": CHART_LAYOUT_DEFAULTS["font"],
        "hoverlabel": CHART_LAYOUT_DEFAULTS["hoverlabel"],
        "showlegend": show_legend,
    }

    if title:
        updates["title"] = {
            "text": f"<b>{title}</b>",
            "font": {"size": 14, "color": "#0B1F3A", "family": "Plus Jakarta Sans, sans-serif"},
            "x": 0.02,
            "y": 0.96,
        }

    if height:
        updates["height"] = height

    fig.update_layout(**updates)

    # Style axes
    fig.update_xaxes(**CHART_LAYOUT_DEFAULTS["xaxis"])
    fig.update_yaxes(**CHART_LAYOUT_DEFAULTS["yaxis"])

    return fig
