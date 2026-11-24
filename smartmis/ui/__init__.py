"""
SmartMIS UI Package - Premium Industrial Control Room Theme & Chart Styling.
"""
from .theme import inject_theme, render_hero_header, render_sidebar_brand, render_sidebar_footer
from .charts import apply_chart_theme, INDUSTRIAL_PALETTE

__all__ = [
    "inject_theme",
    "render_hero_header",
    "render_sidebar_brand",
    "render_sidebar_footer",
    "apply_chart_theme",
    "INDUSTRIAL_PALETTE",
]
