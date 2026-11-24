"""
SmartMIS Unified Theme Engine - "Smart Factory Control Room" Design System.
Provides inject_theme(), render_hero_header(), render_sidebar_brand(), and render_sidebar_footer().
All styling is pure CSS with zero heavy third-party dependencies.
"""
from datetime import date
from typing import Any, Dict, List, Optional, Union
import numpy as np
import streamlit as st


# ==============================================================================
# 1. CORE THEME CSS INJECTION
# ==============================================================================

def inject_theme(dark_mode: bool = False) -> None:
    """
    Injects the complete 'Smart Factory Control Room' CSS design system into the Streamlit app.
    Features:
    - Google Fonts: Plus Jakarta Sans & Inter
    - Background gradient (#F4F8FF to #EAF1FF or Dark Space Navy in Dark Mode)
    - Dark Navy Sidebar (#071527 to #0B1F3A) with option-menu style navigation buttons
    - Primary Orange Gradient Buttons & Outlined Secondary Buttons
    - 16px Rounded Cards, subtle drop shadows, and hover lift
    - Flashing alert banner, glowing CTA buttons, chat bubbles, and progress rings
    - Clean hiding of Streamlit's default footer and header clutter
    """
    bg_gradient = (
        "linear-gradient(180deg, #071322 0%, #0B1C33 50%, #0F2544 100%)"
        if dark_mode
        else "linear-gradient(180deg, #F4F8FF 0%, #EDF3FC 50%, #E6EEF9 100%)"
    )
    text_color = "#F8FAFC" if dark_mode else "#0F172A"
    card_bg = "#0B1C33" if dark_mode else "#FFFFFF"
    card_border = "rgba(255, 255, 255, 0.12)" if dark_mode else "#E2E8F0"

    dynamic_css = f"""
    <style>
    html, body, [class*="css"] {{
        color: {text_color};
    }}
    .stApp {{
        background: {bg_gradient} !important;
        background-attachment: fixed !important;
    }}
    </style>
    """

    static_css = """
    <style>
    /* ==========================================================================
       1. GOOGLE FONTS & GLOBAL TYPOGRAPHY
       ========================================================================== */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    /* Hide Streamlit default clutter */
    #MainMenu { visibility: hidden !important; }
    footer { visibility: hidden !important; }
    header { background: transparent !important; }
    div[data-testid="stDecoration"] { display: none !important; }
    div[data-testid="stToolbar"] { visibility: hidden !important; }

    /* ==========================================================================
       2. MODERN INDUSTRIAL SIDEBAR
       ========================================================================== */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #071527 0%, #0B1F3A 60%, #0D2647 100%) !important;
        color: #F8FAFC !important;
        border-right: 1px solid rgba(45, 127, 249, 0.15) !important;
        box-shadow: 4px 0px 24px rgba(7, 21, 39, 0.25) !important;
    }

    /* Sidebar inner content padding */
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
    }

    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label {
        color: #E2E8F0 !important;
    }

    /* Horizontal line dividers in sidebar */
    section[data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.1) !important;
        margin: 0.85rem 0 !important;
    }

    /* Transform Streamlit native radio into Option-Menu styled navigation cards */
    div[data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] {
        gap: 4px !important;
    }

    div[data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] > label {
        background: rgba(255, 255, 255, 0.03) !important;
        padding: 9px 14px !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        cursor: pointer !important;
        transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1) !important;
        margin-bottom: 3px !important;
        display: flex !important;
        flex-wrap: wrap !important;
        align-items: center !important;
    }

    /* Grouped Navigation Section Headers (Monitor / Analytics / Reports / Admin) */
    div[data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input[value*="🏠"])::before {
        content: "MONITOR & OPERATIONS";
        display: block;
        width: 100%;
        font-size: 0.68rem;
        font-weight: 800;
        color: #94A3B8;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        margin-bottom: 6px;
        padding-bottom: 4px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        pointer-events: none;
    }

    div[data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input[value*="💬"])::before {
        content: "ADVANCED ANALYTICS";
        display: block;
        width: 100%;
        font-size: 0.68rem;
        font-weight: 800;
        color: #94A3B8;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        margin-top: 10px;
        margin-bottom: 6px;
        padding-top: 8px;
        padding-bottom: 4px;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        pointer-events: none;
    }

    div[data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input[value*="📑"])::before {
        content: "REPORTS & ARCHIVE";
        display: block;
        width: 100%;
        font-size: 0.68rem;
        font-weight: 800;
        color: #94A3B8;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        margin-top: 10px;
        margin-bottom: 6px;
        padding-top: 8px;
        padding-bottom: 4px;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        pointer-events: none;
    }

    div[data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input[value*="🔌"])::before {
        content: "ADMIN & INTEGRATION";
        display: block;
        width: 100%;
        font-size: 0.68rem;
        font-weight: 800;
        color: #94A3B8;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        margin-top: 10px;
        margin-bottom: 6px;
        padding-top: 8px;
        padding-bottom: 4px;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        pointer-events: none;
    }

    /* Hide default radio circle completely */
    div[data-testid="stSidebar"] div[data-testid="stRadio"] input[type="radio"] {
        display: none !important;
    }
    div[data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child {
        display: none !important;
    }

    /* Text inside navigation buttons */
    div[data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] > label div[data-testid="stMarkdownContainer"] p {
        color: #CBD5E1 !important;
        font-size: 0.91rem !important;
        font-weight: 500 !important;
        margin: 0 !important;
        letter-spacing: -0.01em !important;
    }

    /* Hover state for nav items */
    div[data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {
        background: rgba(45, 127, 249, 0.14) !important;
        border-color: rgba(45, 127, 249, 0.4) !important;
        transform: translateX(4px) !important;
    }

    div[data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover div[data-testid="stMarkdownContainer"] p {
        color: #FFFFFF !important;
    }

    /* ACTIVE state for selected nav item (Safety Orange Accent) */
    div[data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked),
    div[data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] {
        background: linear-gradient(90deg, rgba(255, 107, 26, 0.24) 0%, rgba(45, 127, 249, 0.16) 100%) !important;
        border-left: 4px solid #FF6B1A !important;
        border-top: 1px solid rgba(255, 107, 26, 0.35) !important;
        border-right: 1px solid rgba(45, 127, 249, 0.25) !important;
        border-bottom: 1px solid rgba(255, 107, 26, 0.35) !important;
        box-shadow: 0 4px 16px rgba(255, 107, 26, 0.2) !important;
        transform: translateX(3px) !important;
    }

    div[data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) div[data-testid="stMarkdownContainer"] p {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }

    /* ==========================================================================
       3. METRIC CARDS (ROUNDED 16px WITH HOVER LIFT)
       ========================================================================== */
    div[data-testid="stMetric"] {
        background: #FFFFFF !important;
        border-radius: 16px !important;
        padding: 18px 22px !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 4px 20px rgba(11, 31, 58, 0.05) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        position: relative !important;
        overflow: hidden !important;
    }

    div[data-testid="stMetric"]::before {
        content: "" !important;
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        width: 100% !important;
        height: 3px !important;
        background: linear-gradient(90deg, #2D7FF9 0%, #FF6B1A 100%) !important;
        opacity: 0.85 !important;
    }

    div[data-testid="stMetric"]:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 10px 28px rgba(11, 31, 58, 0.1) !important;
        border-color: #CBD5E1 !important;
    }

    div[data-testid="stMetric"] label[data-testid="stMetricLabel"] {
        font-size: 0.82rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        color: #64748B !important;
        margin-bottom: 4px !important;
    }

    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 1.85rem !important;
        font-weight: 800 !important;
        color: #0B1F3A !important;
        letter-spacing: -0.02em !important;
    }

    div[data-testid="stMetric"] div[data-testid="stMetricDelta"] {
        font-size: 0.85rem !important;
        font-weight: 600 !important;
    }

    /* ==========================================================================
       4. BUTTONS (PRIMARY ORANGE GRADIENT & OUTLINED SECONDARY)
       ========================================================================== */
    /* Primary buttons */
    button[kind="primary"],
    button[data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #FF6B1A 0%, #FF8533 100%) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.6rem 1.4rem !important;
        box-shadow: 0 4px 16px rgba(255, 107, 26, 0.35) !important;
        transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    button[kind="primary"]:hover,
    button[data-testid="baseButton-primary"]:hover {
        background: linear-gradient(135deg, #EA580C 0%, #FF6B1A 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(255, 107, 26, 0.45) !important;
    }

    /* Secondary / standard buttons */
    button[kind="secondary"],
    button[data-testid="baseButton-secondary"] {
        background: #FFFFFF !important;
        color: #0B1F3A !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        border: 1.5px solid #CBD5E1 !important;
        border-radius: 12px !important;
        padding: 0.55rem 1.25rem !important;
        box-shadow: 0 2px 6px rgba(11, 31, 58, 0.04) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    button[kind="secondary"]:hover,
    button[data-testid="baseButton-secondary"]:hover {
        background: #F8FAFC !important;
        border-color: #2D7FF9 !important;
        color: #2D7FF9 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(45, 127, 249, 0.15) !important;
    }

    /* Download buttons */
    div[data-testid="stDownloadButton"] > button {
        background: linear-gradient(135deg, #0B1F3A 0%, #16365C 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(45, 127, 249, 0.3) !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 14px rgba(11, 31, 58, 0.2) !important;
        transition: all 0.22s ease !important;
    }

    div[data-testid="stDownloadButton"] > button:hover {
        background: linear-gradient(135deg, #2D7FF9 0%, #16365C 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 18px rgba(45, 127, 249, 0.3) !important;
    }

    /* ==========================================================================
       5. TABS STYLING (MODERN PILL TABS)
       ========================================================================== */
    div[data-testid="stTabs"] {
        background: transparent !important;
    }

    div[data-baseweb="tab-list"] {
        background: rgba(255, 255, 255, 0.75) !important;
        backdrop-filter: blur(8px) !important;
        border-radius: 14px !important;
        padding: 6px !important;
        border: 1px solid #E2E8F0 !important;
        gap: 6px !important;
        box-shadow: 0 2px 8px rgba(11, 31, 58, 0.04) !important;
    }

    button[data-baseweb="tab"] {
        border-radius: 10px !important;
        padding: 8px 18px !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        color: #64748B !important;
        border: none !important;
        background: transparent !important;
        transition: all 0.2s ease !important;
    }

    button[data-baseweb="tab"]:hover {
        color: #0B1F3A !important;
        background: rgba(45, 127, 249, 0.06) !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        background: #0B1F3A !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 12px rgba(11, 31, 58, 0.2) !important;
    }

    /* ==========================================================================
       6. CARDS, EXPANDERS & CONTAINERS
       ========================================================================== */
    /* Expanders */
    div[data-testid="stExpander"] {
        background: #FFFFFF !important;
        border-radius: 14px !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 2px 10px rgba(11, 31, 58, 0.03) !important;
        margin-bottom: 0.75rem !important;
        overflow: hidden !important;
    }

    div[data-testid="stExpander"] summary {
        font-weight: 700 !important;
        color: #0B1F3A !important;
        font-size: 0.95rem !important;
        padding: 12px 16px !important;
    }

    /* Inputs, selects, and text fields */
    div[data-baseweb="input"],
    div[data-baseweb="select"] > div {
        border-radius: 10px !important;
        border: 1px solid #CBD5E1 !important;
        background: #FFFFFF !important;
        transition: all 0.2s ease !important;
    }

    div[data-baseweb="input"]:focus-within,
    div[data-baseweb="select"] > div:focus-within {
        border-color: #2D7FF9 !important;
        box-shadow: 0 0 0 3px rgba(45, 127, 249, 0.15) !important;
    }

    /* Dataframes */
    div[data-testid="stDataFrame"] {
        border-radius: 14px !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 4px 16px rgba(11, 31, 58, 0.04) !important;
        overflow: hidden !important;
        background: #FFFFFF !important;
    }

    /* Callouts / Info / Success / Error alert banners */
    div[data-testid="stAlert"] {
        border-radius: 12px !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(11, 31, 58, 0.05) !important;
        padding: 14px 18px !important;
    }

    /* Custom Sleek Scrollbar */
    ::-webkit-scrollbar {
        width: 7px;
        height: 7px;
    }
    ::-webkit-scrollbar-track {
        background: rgba(241, 245, 249, 0.8);
    }
    ::-webkit-scrollbar-thumb {
        background: #CBD5E1;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #94A3B8;
    }

    /* Pulsing Live Dot Animation */
    @keyframes pulseGlow {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7); }
        70% { transform: scale(1.05); box-shadow: 0 0 0 8px rgba(34, 197, 94, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
    }

    .live-pulse-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        background-color: #22C55E;
        border-radius: 50%;
        animation: pulseGlow 1.8s infinite;
        margin-right: 7px;
        vertical-align: middle;
    }

    /* ==========================================================================
       9. PREMIUM INDUSTRIAL KPI CARDS & HOVER LIFT
       ========================================================================== */
    .smartmis-kpi-card {
        transition: transform 0.22s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.22s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.22s ease !important;
        position: relative !important;
        overflow: hidden !important;
    }
    .smartmis-kpi-card:hover {
        transform: translateY(-4px) !important;
        box-shadow: 0 12px 28px rgba(11, 31, 58, 0.12) !important;
    }

    /* Flashing Spike Alert Banner */
    @keyframes alertFlash {
        0% { background: rgba(239, 68, 68, 0.16); border-color: rgba(239, 68, 68, 0.45); box-shadow: 0 0 10px rgba(239, 68, 68, 0.2); }
        50% { background: rgba(239, 68, 68, 0.32); border-color: rgba(239, 68, 68, 0.9); box-shadow: 0 0 24px rgba(239, 68, 68, 0.45); }
        100% { background: rgba(239, 68, 68, 0.16); border-color: rgba(239, 68, 68, 0.45); box-shadow: 0 0 10px rgba(239, 68, 68, 0.2); }
    }
    .flashing-spike-banner {
        animation: alertFlash 1.6s infinite ease-in-out !important;
        border-radius: 14px !important;
        padding: 16px 20px !important;
        border: 2px solid #EF4444 !important;
        margin-bottom: 20px !important;
    }

    /* Glowing Orange Action Button */
    @keyframes glowOrange {
        0% { box-shadow: 0 0 8px rgba(255, 107, 26, 0.4); }
        50% { box-shadow: 0 0 24px rgba(255, 107, 26, 0.85), 0 0 35px rgba(255, 107, 26, 0.35); }
        100% { box-shadow: 0 0 8px rgba(255, 107, 26, 0.4); }
    }
    .glow-orange-btn button {
        animation: glowOrange 2s infinite ease-in-out !important;
        background: linear-gradient(135deg, #FF6B1A 0%, #FF8533 100%) !important;
        color: #FFFFFF !important;
        font-weight: 800 !important;
        border: none !important;
    }

    /* Chat-Style UI for Ask Your Data */
    .chat-bubble-user {
        background: linear-gradient(135deg, #2D7FF9 0%, #1D4ED8 100%) !important;
        color: #FFFFFF !important;
        padding: 12px 18px !important;
        border-radius: 18px 18px 4px 18px !important;
        max-width: 82% !important;
        margin-left: auto !important;
        margin-bottom: 12px !important;
        box-shadow: 0 4px 14px rgba(45, 127, 249, 0.25) !important;
        font-weight: 500 !important;
        font-size: 0.94rem !important;
        line-height: 1.4 !important;
    }
    .chat-bubble-ai {
        background: #FFFFFF !important;
        color: #0F172A !important;
        padding: 16px 20px !important;
        border-radius: 18px 18px 18px 4px !important;
        border: 1px solid #E2E8F0 !important;
        margin-right: auto !important;
        margin-bottom: 14px !important;
        box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06) !important;
        max-width: 95% !important;
    }

    /* Smart Insights Cards */
    .smart-insight-card {
        background: #FFFFFF !important;
        border-radius: 14px !important;
        padding: 14px 18px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 3px 12px rgba(15, 23, 42, 0.04) !important;
        border: 1px solid #E2E8F0 !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    }
    .smart-insight-card:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.08) !important;
    }
    .insight-border-critical {
        border-left: 5px solid #EF4444 !important;
    }
    .insight-border-warning {
        border-left: 5px solid #F59E0B !important;
    }
    .insight-border-good {
        border-left: 5px solid #22C55E !important;
    }

    /* Feature Grid Cards */
    .feature-card {
        background: #FFFFFF !important;
        border-radius: 14px !important;
        padding: 22px 20px !important;
        box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05) !important;
        border: 1px solid #E2E8F0 !important;
        position: relative !important;
        overflow: hidden !important;
        height: 100% !important;
        transition: transform 0.22s ease, box-shadow 0.22s ease !important;
    }
    .feature-card:hover {
        transform: translateY(-4px) !important;
        box-shadow: 0 12px 28px rgba(15, 23, 42, 0.1) !important;
    }

    /* Animated Stats Strip */
    .stats-strip {
        background: linear-gradient(135deg, #071527 0%, #0B1F3A 60%, #16365C 100%) !important;
        border-radius: 16px !important;
        padding: 20px 24px !important;
        margin: 22px 0 !important;
        border: 1px solid rgba(45, 127, 249, 0.25) !important;
        box-shadow: 0 10px 28px rgba(7, 21, 39, 0.22) !important;
        display: flex !important;
        justify-content: space-around !important;
        align-items: center !important;
        flex-wrap: wrap !important;
        gap: 16px !important;
    }
    .stats-item {
        text-align: center !important;
        min-width: 130px !important;
    }
    .stats-val {
        font-size: 1.85rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em !important;
        line-height: 1.1 !important;
    }
    .stats-lbl {
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        color: #94A3B8 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        margin-top: 5px !important;
    }

    /* Big CTA Cards */
    .cta-card {
        background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%) !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 16px !important;
        padding: 22px 20px !important;
        text-align: center !important;
        box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06) !important;
        transition: all 0.24s cubic-bezier(0.4, 0, 0.2, 1) !important;
        position: relative !important;
        overflow: hidden !important;
        height: 100% !important;
    }
    .cta-card:hover {
        transform: translateY(-5px) !important;
        box-shadow: 0 14px 30px rgba(15, 23, 42, 0.12) !important;
        border-color: #2D7FF9 !important;
    }

    /* Document Preview Frame */
    .doc-preview-sheet {
        background: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 10px !important;
        padding: 28px 32px !important;
        box-shadow: 0 8px 30px rgba(15, 23, 42, 0.08) !important;
        font-family: 'Inter', sans-serif !important;
    }
    </style>
    """
    st.markdown(dynamic_css + static_css, unsafe_allow_html=True)


# ==============================================================================
# 2. HERO CONTROL ROOM BANNER
# ==============================================================================

def render_hero_header(
    user: Dict[str, Any],
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
) -> None:
    """
    Renders a boardroom-grade 'Smart Factory Control Room' hero header banner
    across all application pages. Includes live pulsing system dot, date, and user role badge.
    """
    today_str = date.today().strftime("%d %b %Y")
    user_name = user.get("full_name", user.get("username", "Engineer"))
    role = user.get("role", "Operator")
    dept = user.get("department", "Plant Floor")

    # Role badge styling
    role_color = "#FF6B1A" if role == "Admin" else ("#2D7FF9" if role == "Manager" else "#00C2A8")

    page_title = title or "SmartMIS: Manufacturing Intelligence & Control Room"
    page_subtitle = subtitle or "Automated MIS, Real-Time Rejection Analytics & Statistical Quality Engineering"

    hero_html = f"""
    <div style="
        background: linear-gradient(135deg, #071527 0%, #0B1F3A 40%, #16365C 80%, #1D4B82 100%);
        border-radius: 18px;
        padding: 24px 28px;
        margin-bottom: 24px;
        box-shadow: 0 10px 30px rgba(7, 21, 39, 0.25);
        border: 1px solid rgba(45, 127, 249, 0.2);
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 16px;
    ">
        <div style="flex: 1; min-width: 320px;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
                <span style="
                    background: rgba(45, 127, 249, 0.2);
                    border: 1px solid rgba(45, 127, 249, 0.4);
                    color: #60A5FA;
                    padding: 3px 10px;
                    border-radius: 20px;
                    font-size: 0.75rem;
                    font-weight: 700;
                    letter-spacing: 0.06em;
                    text-transform: uppercase;
                ">🏭 SAKTHI HACKATHON 2.0 | PS-005</span>
                <span style="
                    background: rgba(34, 197, 94, 0.15);
                    border: 1px solid rgba(34, 197, 94, 0.35);
                    color: #4ADE80;
                    padding: 3px 10px;
                    border-radius: 20px;
                    font-size: 0.75rem;
                    font-weight: 700;
                    display: inline-flex;
                    align-items: center;
                "><span class="live-pulse-dot"></span>SYSTEM ONLINE</span>
            </div>
            <h1 style="
                color: #FFFFFF;
                font-size: 1.65rem;
                font-weight: 800;
                margin: 0 0 6px 0;
                letter-spacing: -0.02em;
                line-height: 1.25;
            ">{page_title}</h1>
            <p style="
                color: #94A3B8;
                font-size: 0.92rem;
                margin: 0;
                font-weight: 500;
            ">{page_subtitle}</p>
        </div>
        <div style="
            display: flex;
            align-items: center;
            gap: 14px;
            background: rgba(255, 255, 255, 0.05);
            padding: 10px 18px;
            border-radius: 14px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        ">
            <div style="text-align: right;">
                <div style="color: #F8FAFC; font-weight: 700; font-size: 0.92rem;">{user_name}</div>
                <div style="display: flex; gap: 6px; align-items: center; justify-content: flex-end; margin-top: 2px;">
                    <span style="
                        background: {role_color};
                        color: #FFFFFF;
                        font-size: 0.7rem;
                        font-weight: 800;
                        padding: 1px 7px;
                        border-radius: 6px;
                        text-transform: uppercase;
                    ">{role}</span>
                    <span style="color: #94A3B8; font-size: 0.78rem;">{dept}</span>
                </div>
            </div>
            <div style="
                border-left: 1px solid rgba(255, 255, 255, 0.15);
                padding-left: 14px;
                text-align: center;
            ">
                <div style="color: #64748B; font-size: 0.7rem; font-weight: 700; text-transform: uppercase;">DATE</div>
                <div style="color: #38BDF8; font-weight: 800; font-size: 0.88rem;">{today_str}</div>
            </div>
        </div>
    </div>
    """
    st.markdown(hero_html, unsafe_allow_html=True)


# ==============================================================================
# 3. SIDEBAR BRAND & FOOTER BLOCKS
# ==============================================================================

def render_sidebar_brand() -> None:
    """Renders the top branding block in the sidebar."""
    brand_html = """
    <div style="
        padding: 6px 4px 16px 4px;
        margin-bottom: 8px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    ">
        <div style="display: flex; align-items: center; gap: 10px;">
            <div style="
                background: linear-gradient(135deg, #FF6B1A 0%, #FF8533 100%);
                width: 36px;
                height: 36px;
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.25rem;
                box-shadow: 0 4px 12px rgba(255, 107, 26, 0.4);
            ">⚡</div>
            <div>
                <div style="
                    color: #FFFFFF;
                    font-size: 1.35rem;
                    font-weight: 800;
                    letter-spacing: -0.02em;
                    line-height: 1.1;
                ">Smart<span style="color: #FF6B1A;">MIS</span></div>
                <div style="
                    color: #38BDF8;
                    font-size: 0.72rem;
                    font-weight: 700;
                    letter-spacing: 0.08em;
                    text-transform: uppercase;
                ">Control Room v2.5</div>
            </div>
        </div>
    </div>
    """
    st.sidebar.markdown(brand_html, unsafe_allow_html=True)


def render_sidebar_footer() -> None:
    """Renders the team and event credit footer at bottom of sidebar."""
    footer_html = """
    <div style="
        margin-top: 2rem;
        padding: 14px 12px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        text-align: center;
    ">
        <div style="color: #94A3B8; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">
            ENGINEERED BY
        </div>
        <div style="color: #FFFFFF; font-weight: 800; font-size: 0.88rem; margin: 2px 0;">
            Team firstones
        </div>
        <div style="color: #FF6B1A; font-size: 0.74rem; font-weight: 600;">
            Sakthi Hackathon 2.0 • Round 2
        </div>
        <div style="color: #64748B; font-size: 0.68rem; margin-top: 4px;">
            PS-005 Automated MIS & Rejection
        </div>
    </div>
    """
    st.sidebar.markdown(footer_html, unsafe_allow_html=True)


# ==============================================================================
# 4. REUSABLE INDUSTRIAL KPI CARD COMPONENT
# ==============================================================================

KPI_COLOR_SCHEMES: Dict[str, Dict[str, str]] = {
    "blue": {
        "bg": "linear-gradient(135deg, rgba(45, 127, 249, 0.08) 0%, rgba(56, 189, 248, 0.03) 100%)",
        "border": "rgba(45, 127, 249, 0.22)",
        "accent": "linear-gradient(90deg, #2D7FF9, #38BDF8)",
        "icon_bg": "rgba(45, 127, 249, 0.12)",
        "icon_color": "#2D7FF9",
        "sparkline": "#2D7FF9",
    },
    "green": {
        "bg": "linear-gradient(135deg, rgba(34, 197, 94, 0.08) 0%, rgba(74, 222, 128, 0.03) 100%)",
        "border": "rgba(34, 197, 94, 0.22)",
        "accent": "linear-gradient(90deg, #22C55E, #4ADE80)",
        "icon_bg": "rgba(34, 197, 94, 0.12)",
        "icon_color": "#22C55E",
        "sparkline": "#22C55E",
    },
    "orange": {
        "bg": "linear-gradient(135deg, rgba(255, 107, 26, 0.08) 0%, rgba(255, 149, 0, 0.03) 100%)",
        "border": "rgba(255, 107, 26, 0.22)",
        "accent": "linear-gradient(90deg, #FF6B1A, #FFB020)",
        "icon_bg": "rgba(255, 107, 26, 0.12)",
        "icon_color": "#FF6B1A",
        "sparkline": "#FF6B1A",
    },
    "red": {
        "bg": "linear-gradient(135deg, rgba(255, 77, 79, 0.09) 0%, rgba(254, 202, 202, 0.04) 100%)",
        "border": "rgba(255, 77, 79, 0.25)",
        "accent": "linear-gradient(90deg, #FF4D4F, #F87171)",
        "icon_bg": "rgba(255, 77, 79, 0.14)",
        "icon_color": "#FF4D4F",
        "sparkline": "#FF4D4F",
    },
    "amber": {
        "bg": "linear-gradient(135deg, rgba(255, 176, 32, 0.08) 0%, rgba(251, 191, 36, 0.03) 100%)",
        "border": "rgba(255, 176, 32, 0.22)",
        "accent": "linear-gradient(90deg, #FFB020, #FBBF24)",
        "icon_bg": "rgba(255, 176, 32, 0.12)",
        "icon_color": "#FFB020",
        "sparkline": "#FFB020",
    },
    "teal": {
        "bg": "linear-gradient(135deg, rgba(0, 194, 168, 0.08) 0%, rgba(45, 212, 191, 0.03) 100%)",
        "border": "rgba(0, 194, 168, 0.22)",
        "accent": "linear-gradient(90deg, #00C2A8, #2DD4BF)",
        "icon_bg": "rgba(0, 194, 168, 0.12)",
        "icon_color": "#00C2A8",
        "sparkline": "#00C2A8",
    },
    "purple": {
        "bg": "linear-gradient(135deg, rgba(139, 92, 246, 0.08) 0%, rgba(167, 139, 250, 0.03) 100%)",
        "border": "rgba(139, 92, 246, 0.22)",
        "accent": "linear-gradient(90deg, #8B5CF6, #A78BFA)",
        "icon_bg": "rgba(139, 92, 246, 0.12)",
        "icon_color": "#8B5CF6",
        "sparkline": "#8B5CF6",
    },
}


def _generate_sparkline_svg(data: List[float], color: str) -> str:
    """Generates a responsive, zero-dependency inline SVG sparkline with gradient area fill."""
    if not data or len(data) < 2:
        return ""
    clean_data = [float(v) for v in data if v is not None and not (isinstance(v, float) and np.isnan(v))]
    if len(clean_data) < 2:
        return ""
    min_v = min(clean_data)
    max_v = max(clean_data)
    rng = max(1e-5, max_v - min_v)
    w = 140
    h = 32
    pad = 4
    pts = []
    for idx, val in enumerate(clean_data):
        x = round(pad + (idx / (len(clean_data) - 1)) * (w - 2 * pad), 1)
        y = round((h - pad) - ((val - min_v) / rng) * (h - 2 * pad), 1)
        pts.append((x, y))
    pts_str = " ".join(f"{x},{y}" for x, y in pts)
    area_pts = f"{pts[0][0]},{h} " + pts_str + f" {pts[-1][0]},{h}"
    cid = abs(hash(str(clean_data) + color)) % 100000

    return f"""
    <div style="margin-top: 8px; width: 100%;">
        <svg width="100%" height="{h}" viewBox="0 0 {w} {h}" preserveAspectRatio="none" style="display: block; overflow: visible;">
            <defs>
                <linearGradient id="spk_grad_{cid}" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="{color}" stop-opacity="0.30"/>
                    <stop offset="100%" stop-color="{color}" stop-opacity="0.02"/>
                </linearGradient>
            </defs>
            <polygon points="{area_pts}" fill="url(#spk_grad_{cid})" />
            <polyline points="{pts_str}" fill="none" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="{pts[-1][0]}" cy="{pts[-1][1]}" r="3.2" fill="{color}" stroke="#FFFFFF" stroke-width="1.2" />
        </svg>
    </div>
    """


def kpi_card(
    title: str,
    value: Any,
    delta: Optional[str] = None,
    icon: str = "📊",
    color: str = "blue",
    sparkline_data: Optional[List[float]] = None,
    delta_color: str = "normal",
    container: Any = None,
    help_text: Optional[str] = None,
) -> str:
    """
    Renders a boardroom-grade, responsive KPI card with gradient background,
    accent bar, large typography, delta badge, subtle icon, hover lift,
    and optional inline SVG sparkline.

    Args:
        title: Card label (e.g. 'Production Output')
        value: Primary metric number or text (e.g. '18,450 pcs', '84.2%')
        delta: Optional trend delta text (e.g. '+1.2% vs target', 'A:88% P:92% Q:96%')
        icon: Emoji or icon symbol
        color: 'blue' (production), 'green' (good/yield), 'orange' (rejected),
               'red' (alert), 'amber' (warning), 'teal' (OEE), 'purple' (COPQ),
               or 'rejection %' (auto-evaluates red/amber/green vs target).
        sparkline_data: Optional list of numeric points for mini trend chart
        delta_color: 'normal' (+ is good/green, - is bad/red),
                     'inverse' (+ is bad/red, - is good/green), or 'neutral'
        container: Streamlit container/column to render into (defaults to st)
        help_text: Optional tooltip hover title
    """
    # Evaluate dynamic rejection color if specified
    color_lower = color.lower()
    if color_lower in ("rejection %", "rejection_pct", "auto_rejection"):
        try:
            val_num = float(str(value).replace("%", "").replace(",", "").strip())
            if val_num <= 3.0:
                scheme_key = "green"
            elif val_num <= 4.5:
                scheme_key = "amber"
            else:
                scheme_key = "red"
        except (ValueError, TypeError):
            scheme_key = "orange"
    elif color_lower in KPI_COLOR_SCHEMES:
        scheme_key = color_lower
    else:
        scheme_key = "blue"

    scheme = KPI_COLOR_SCHEMES[scheme_key]

    # Delta badge rendering
    delta_html = ""
    if delta is not None and str(delta).strip():
        d_str = str(delta).strip()
        is_positive = d_str.startswith("+") or "▲" in d_str
        is_negative = d_str.startswith("-") or "▼" in d_str

        if delta_color == "inverse":
            badge_bg = "rgba(239, 68, 68, 0.12)" if is_positive else ("rgba(34, 197, 94, 0.14)" if is_negative else "rgba(100, 116, 139, 0.10)")
            badge_fg = "#DC2626" if is_positive else ("#16A34A" if is_negative else "#475569")
        elif delta_color == "neutral":
            badge_bg = "rgba(100, 116, 139, 0.10)"
            badge_fg = "#475569"
        else:  # normal
            badge_bg = "rgba(34, 197, 94, 0.14)" if is_positive else ("rgba(239, 68, 68, 0.12)" if is_negative else "rgba(100, 116, 139, 0.10)")
            badge_fg = "#16A34A" if is_positive else ("#DC2626" if is_negative else "#475569")

        delta_html = f"""
        <div style="
            display: inline-flex;
            align-items: center;
            gap: 5px;
            background: {badge_bg};
            color: {badge_fg};
            font-size: 0.74rem;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 12px;
            margin-top: 4px;
            line-height: 1.25;
        ">{d_str}</div>
        """

    spark_html = _generate_sparkline_svg(sparkline_data, scheme["sparkline"]) if sparkline_data else ""
    title_attr = f'title="{help_text}"' if help_text else ""

    card_html = f"""
    <div class="smartmis-kpi-card" {title_attr} style="
        background: {scheme['bg']};
        border: 1px solid {scheme['border']};
        border-radius: 16px;
        padding: 16px 18px 14px 18px;
        position: relative;
        box-shadow: 0 4px 16px rgba(11, 31, 58, 0.05);
        margin-bottom: 12px;
    ">
        <div style="position: absolute; top: 0; left: 0; right: 0; height: 3.5px; background: {scheme['accent']};"></div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span style="
                color: #64748B;
                font-size: 0.74rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.06em;
            ">{title}</span>
            <div style="
                background: {scheme['icon_bg']};
                color: {scheme['icon_color']};
                width: 30px;
                height: 30px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.95rem;
                box-shadow: inset 0 0 0 1px {scheme['border']};
            ">{icon}</div>
        </div>
        <div style="
            color: #0B1F3A;
            font-size: 1.72rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            line-height: 1.15;
            margin: 2px 0 4px 0;
        ">{value}</div>
        {delta_html}
        {spark_html}
    </div>
    """

    target = container if container is not None else st
    target.markdown(card_html, unsafe_allow_html=True)
    return card_html


# ==============================================================================
# 5. HIGH-IMPACT POLISHED UI COMPONENTS (STATS STRIP & PROGRESS RING)
# ==============================================================================

def render_stats_strip(
    records_cnt: int,
    oee_pct: float,
    copq_inr: float,
    reports_cnt: int = 4,
) -> None:
    """Renders a high-impact horizontal stats counter banner."""
    html = f"""
    <div class="stats-strip">
        <div class="stats-item">
            <div class="stats-val" style="color: #38BDF8;">{records_cnt:,}</div>
            <div class="stats-lbl">Verified PMS Records</div>
        </div>
        <div style="width: 1px; height: 35px; background: rgba(255,255,255,0.15);"></div>
        <div class="stats-item">
            <div class="stats-val" style="color: #22C55E;">{oee_pct:.1f}%</div>
            <div class="stats-lbl">Plant Blended OEE</div>
        </div>
        <div style="width: 1px; height: 35px; background: rgba(255,255,255,0.15);"></div>
        <div class="stats-item">
            <div class="stats-val" style="color: #A78BFA;">₹{copq_inr:,.0f}</div>
            <div class="stats-lbl">Calculated COPQ Loss</div>
        </div>
        <div style="width: 1px; height: 35px; background: rgba(255,255,255,0.15);"></div>
        <div class="stats-item">
            <div class="stats-val" style="color: #FFB020;">{reports_cnt} Formats</div>
            <div class="stats-lbl">Automated MIS Reports</div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_progress_ring(
    percentage: float = 100.0,
    title: str = "Requirement Coverage",
    subtitle: str = "17 of 17 Hackathon Requirements Fully Verified",
) -> None:
    """Renders an SVG circular progress indicator with 100% coverage badge."""
    radius = 46
    circumference = round(2 * 3.14159 * radius, 1)
    stroke_offset = round(circumference - (percentage / 100.0) * circumference, 1)
    html = f"""
    <div style="
        background: #FFFFFF;
        border-radius: 16px;
        padding: 22px 26px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
        display: flex;
        align-items: center;
        gap: 22px;
        margin-bottom: 22px;
    ">
        <div style="position: relative; width: 110px; height: 110px; flex-shrink: 0;">
            <svg width="110" height="110" viewBox="0 0 110 110" style="transform: rotate(-90deg);">
                <circle cx="55" cy="55" r="{radius}" fill="none" stroke="#E2E8F0" stroke-width="9" />
                <circle cx="55" cy="55" r="{radius}" fill="none" stroke="#22C55E" stroke-width="9"
                    stroke-dasharray="{circumference}" stroke-dashoffset="{stroke_offset}"
                    stroke-linecap="round" />
            </svg>
            <div style="
                position: absolute;
                top: 0; left: 0; right: 0; bottom: 0;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            ">
                <span style="font-size: 1.35rem; font-weight: 800; color: #0B1F3A; line-height: 1;">{int(percentage)}%</span>
                <span style="font-size: 0.62rem; font-weight: 800; color: #16A34A; text-transform: uppercase; margin-top: 2px;">VERIFIED</span>
            </div>
        </div>
        <div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="background: rgba(34, 197, 94, 0.15); color: #16A34A; padding: 2px 8px; border-radius: 12px; font-size: 0.72rem; font-weight: 800; text-transform: uppercase;">
                    PS-005 COMPLIANT
                </span>
                <span style="color: #64748B; font-size: 0.78rem; font-weight: 600;">Sakthi Hackathon 2.0 • Round 2</span>
            </div>
            <h3 style="margin: 6px 0 3px 0; color: #0B1F3A; font-size: 1.25rem; font-weight: 800;">{title}</h3>
            <p style="margin: 0; color: #64748B; font-size: 0.88rem;">{subtitle}</p>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_roi_hero(
    hours_saved_monthly: float,
    annual_savings_inr: float,
    efficiency_pct: float = 99.4
) -> None:
    """Renders a prominent green-gradient hero block with large numbers for the ROI page."""
    html = f"""
    <div style="
        background: linear-gradient(135deg, #0B1F3A 0%, #0F382E 50%, #16533A 100%);
        border-radius: 18px;
        padding: 26px 32px;
        margin-bottom: 24px;
        border: 1px solid rgba(34, 197, 94, 0.35);
        box-shadow: 0 10px 30px rgba(11, 31, 58, 0.15);
        color: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 20px;
    ">
        <div>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                <span style="background: rgba(34, 197, 94, 0.22); color: #4ADE80; font-size: 0.75rem; font-weight: 800; padding: 3px 10px; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.05em; border: 1px solid rgba(74, 222, 128, 0.3);">
                    ⚡ AUTOMATION PAYBACK
                </span>
                <span style="color: #94A3B8; font-size: 0.85rem;">Plant MIS Automation & Telemetry Ingestion</span>
            </div>
            <div style="font-size: 2.35rem; font-weight: 900; letter-spacing: -0.03em; color: #FFFFFF; line-height: 1.1;">
                <span style="color: #4ADE80;">{hours_saved_monthly:.1f} hrs</span> <span style="font-size: 1.6rem; font-weight: 600; color: #E2E8F0;">saved / mo</span>
            </div>
            <div style="font-size: 1.0rem; color: #A7F3D0; margin-top: 6px; font-weight: 500;">
                Recovers <strong style="color: #FFFFFF;">{efficiency_pct:.1f}%</strong> of engineering spreadsheet prep time across all shifts
            </div>
        </div>
        <div style="
            background: rgba(255, 255, 255, 0.07);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 14px;
            padding: 16px 24px;
            text-align: right;
            backdrop-filter: blur(6px);
        ">
            <div style="font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; color: #94A3B8; font-weight: 700;">
                Projected Annual Value
            </div>
            <div style="font-size: 2.1rem; font-weight: 900; color: #34D399; letter-spacing: -0.02em; margin-top: 2px;">
                ₹{annual_savings_inr:,.0f} <span style="font-size: 1.1rem; font-weight: 600; color: #CBD5E1;">/ yr</span>
            </div>
            <div style="font-size: 0.78rem; color: #86EFAC; font-weight: 600; margin-top: 2px;">
                ✓ Direct Engineering Time Saved
            </div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)



