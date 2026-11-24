"""
SmartMIS UI Package - Premium Industrial Control Room Theme & Chart Styling.
"""
from .theme import (
    inject_theme,
    render_hero_header,
    render_sidebar_brand,
    render_sidebar_footer,
    kpi_card,
    render_stats_strip,
    render_progress_ring,
    render_roi_hero,
)
from .charts import (
    apply_chart_theme,
    INDUSTRIAL_PALETTE,
    create_gauge_chart,
    create_copq_treemap,
    create_process_heatmap,
)

__all__ = [
    "inject_theme",
    "render_hero_header",
    "render_sidebar_brand",
    "render_sidebar_footer",
    "kpi_card",
    "render_stats_strip",
    "render_progress_ring",
    "render_roi_hero",
    "apply_chart_theme",
    "INDUSTRIAL_PALETTE",
    "create_gauge_chart",
    "create_copq_treemap",
    "create_process_heatmap",
]
