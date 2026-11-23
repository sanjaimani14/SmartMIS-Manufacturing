"""
Executive intelligence, Plant Head one-page digest PDF, Smart Insights,
and Power BI export engine for SmartMIS.
"""
import io
import logging
import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

try:
    import config
    from kpis import compute_advanced_kpis, compute_copq, load_copq_costs
except ImportError:
    from . import config
    from .kpis import compute_advanced_kpis, compute_copq, load_copq_costs

log = logging.getLogger("smartmis.executive")


# ==============================================================================
# 1. SMART INSIGHTS ENGINE (3 FINDINGS + 3 ACTIONS)
# ==============================================================================

def generate_smart_insights(df: pd.DataFrame) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Generate 3 data-driven findings and 3 concrete operational actions
    tailored to the active manufacturing dataset.
    """
    if df.empty:
        return (
            [{"title": "No Data", "text": "Insufficient production records to infer operational insights."}],
            [{"title": "Action", "text": "Ingest PMS data from CSV or simulator to generate insights."}]
        )

    tot_p = float(df["produced"].sum())
    tot_r = float(df["rejected"].sum())
    overall_rej = round(100.0 * tot_r / max(1.0, tot_p), 2)

    findings: List[Dict[str, str]] = []
    actions: List[Dict[str, str]] = []

    # 1. Finding & Action on Primary Defect
    rej_df = df[df["rejected"] > 0]
    if not rej_df.empty:
        top_def_s = rej_df.groupby("defect")["rejected"].sum().sort_values(ascending=False)
        top_def = top_def_s.index[0]
        top_def_cnt = int(top_def_s.iloc[0])
        top_def_share = round(100.0 * top_def_cnt / max(1.0, tot_r), 1)

        findings.append({
            "title": f"Dominant Quality Defect: {top_def}",
            "text": f"'{top_def}' is the single largest quality loss driver, contributing {top_def_cnt:,} rejected parts ({top_def_share}% of all plant non-conformance).",
            "category": "Quality",
            "badge": "CRITICAL" if top_def_share > 35 else "WARNING"
        })

        if "blow hole" in top_def.lower():
            actions.append({
                "title": "Melt Degassing & Sand Moisture Audit",
                "text": "Audit green sand return moisture levels (keep <3.6%) and inspect rotary nitrogen degassing cycle timing on active foundry melts.",
                "owner": "Foundry Metallurgist / QA Lead"
            })
        elif "tool mark" in top_def.lower() or "size" in top_def.lower():
            actions.append({
                "title": "Tool Wear & Offset Compensation",
                "text": "Inspect carbide insert edge wear, recalibrate tool wear offsets, and review spindle vibration runout on active CNC lines.",
                "owner": "Machining Maintenance Head"
            })
        else:
            actions.append({
                "title": "Standard Operating Procedure (SOP) Review",
                "text": f"Convene 8D problem-solving team to address root causes of {top_def} across tooling, setup, and temperature parameters.",
                "owner": "Quality Assurance Manager"
            })

    # 2. Finding & Action on Machine Performance & Degradation
    mach_rej = df.groupby(["department", "machine"]).apply(
        lambda g: 100.0 * g["rejected"].sum() / max(1.0, g["produced"].sum()),
        include_groups=False
    ).sort_values(ascending=False)

    if not mach_rej.empty:
        worst_dept, worst_mach = mach_rej.index[0]
        worst_pct = round(float(mach_rej.iloc[0]), 2)

        findings.append({
            "title": f"Equipment Bottleneck: {worst_mach}",
            "text": f"Machine '{worst_mach}' ({worst_dept}) exhibited the highest non-conformance rate at {worst_pct}%, operating {'significantly above' if worst_pct > config.REJECTION_TARGET else 'near'} the plant threshold ({config.REJECTION_TARGET}%).",
            "category": "Equipment",
            "badge": "CRITICAL" if worst_pct > config.REJECTION_TARGET * 1.3 else "WARNING"
        })

        actions.append({
            "title": f"Preventive Maintenance on {worst_mach}",
            "text": f"Perform scheduled mechanical and electrical inspection on {worst_mach}; replace worn fixtures and verify clamping pressure.",
            "owner": f"{worst_dept} Maintenance Supervisor"
        })

    # 3. Finding & Action on Shift or Scrap Financial Loss
    if "shift" in df.columns and len(df["shift"].unique()) > 1:
        sh_rates = df.groupby("shift").apply(
            lambda g: 100.0 * g["rejected"].sum() / max(1.0, g["produced"].sum()),
            include_groups=False
        ).sort_values(ascending=False)
        worst_shift = sh_rates.index[0]
        best_shift = sh_rates.index[-1]
        shift_delta = round(float(sh_rates.iloc[0] - sh_rates.iloc[-1]), 2)

        findings.append({
            "title": f"Shift Variance Gap ({worst_shift} vs {best_shift})",
            "text": f"Shift {worst_shift} experienced higher rejection ({sh_rates.iloc[0]:.2f}%) than Shift {best_shift} ({sh_rates.iloc[-1]:.2f}%), representing a {shift_delta} pts operational variance gap.",
            "category": "Operations",
            "badge": "WARNING"
        })

        actions.append({
            "title": f"Shift Handover & Standard Work Alignment",
            "text": f"Standardize operating parameters between Shift {worst_shift} and Shift {best_shift}; conduct refresher briefing on setup checks.",
            "owner": "Shop Floor Operations Lead"
        })
    else:
        copq_dict = compute_copq(df)
        tot_copq = copq_dict["total_copq"]
        findings.append({
            "title": f"Financial Scrap & Rework Loss: ₹{tot_copq:,.0f}",
            "text": f"Cost of Poor Quality reached ₹{tot_copq:,.0f}, with unrecoverable scrap accounting for {round(100.0*copq_dict['total_scrap_cost']/max(1.0, tot_copq), 1)}% of losses.",
            "category": "Finance",
            "badge": "WARNING"
        })
        actions.append({
            "title": "Scrap Reduction Target Initiative",
            "text": "Implement immediate scrap gate review before machining raw castings to avoid value-added machining loss on defective stock.",
            "owner": "Finance & Production Controller"
        })

    return findings[:3], actions[:3]


# ==============================================================================
# 2. ONE-PAGE EXECUTIVE SUMMARY PDF FOR PLANT HEAD
# ==============================================================================

def generate_executive_summary_pdf(
    df: pd.DataFrame,
    title: str = "EXECUTIVE MANUFACTURING MIS BRIEFING",
) -> bytes:
    """
    Generate a high-density, professional ONE-PAGE executive digest PDF
    specifically engineered for the Plant Head / General Manager.
    Strictly calibrated to fit cleanly onto a single A4 sheet.
    """
    buf = io.BytesIO()
    styles = getSampleStyleSheet()

    # Custom compact typography
    h1_style = ParagraphStyle(
        "ExecH1",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#1F3A5F"),
        alignment=0,
    )
    sub_style = ParagraphStyle(
        "ExecSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#555555"),
    )
    head2_style = ParagraphStyle(
        "ExecH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#1F3A5F"),
        spaceBefore=6,
        spaceAfter=3,
    )
    body_style = ParagraphStyle(
        "ExecBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#222222"),
    )
    bullet_style = ParagraphStyle(
        "ExecBullet",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#222222"),
        leftIndent=8,
    )

    story: List[Any] = []

    # Calculate metrics
    adv_kpis = compute_advanced_kpis(df)
    copq_info = compute_copq(df)
    findings, actions = generate_smart_insights(df)

    start_dt = df["date"].min() if not df.empty else date.today()
    end_dt = df["date"].max() if not df.empty else date.today()

    # 1. Header Banner
    story.append(Paragraph(f"<b>{config.COMPANY}</b> | PLANT OPERATIONS BRIEFING", sub_style))
    story.append(Paragraph(title, h1_style))
    story.append(Paragraph(f"Reporting Period: <b>{start_dt:%d %b %Y} to {end_dt:%d %b %Y}</b> | Generated: {datetime.now().strftime('%d-%b-%Y %H:%M')}", sub_style))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1F3A5F"), spaceAfter=6))

    # 2. Executive 4-Box Metric Grid
    kpi_grid_data = [
        ["TOTAL OUTPUT", "REJECTION RATE", "TOTAL COPQ LOSS", "PLANT OEE"],
        [
            f"{adv_kpis['Produced']:,} pcs",
            f"{adv_kpis['Rejection %']:.2f}%",
            f"₹{copq_info['total_copq']:,.0f}",
            f"{adv_kpis['OEE %']:.1f}%",
        ],
        [
            f"Good: {adv_kpis['Good']:,} pcs",
            f"Scrap: {adv_kpis['Scrap %']:.1f}% | Rework: {adv_kpis['Rework %']:.1f}%",
            f"Scrap: ₹{copq_info['total_scrap_cost']:,.0f}",
            f"A:{adv_kpis['Availability %']:.0f}% P:{adv_kpis['Performance %']:.0f}% Q:{adv_kpis['Quality %']:.0f}%",
        ],
    ]
    kpi_grid = Table(kpi_grid_data, colWidths=[130] * 4)
    kpi_grid.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7.5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F2F5FA")),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 12),
        ("TEXTCOLOR", (0, 1), (0, 1), colors.HexColor("#1F3A5F")),
        ("TEXTCOLOR", (1, 1), (1, 1), colors.HexColor("#D93025") if adv_kpis["Rejection %"] > config.REJECTION_TARGET else colors.HexColor("#2E9E5B")),
        ("TEXTCOLOR", (2, 1), (2, 1), colors.HexColor("#B06000")),
        ("TEXTCOLOR", (3, 1), (3, 1), colors.HexColor("#1F3A5F")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.white),
        ("FONTSIZE", (0, 2), (-1, 2), 6.5),
        ("TEXTCOLOR", (0, 2), (-1, 2), colors.HexColor("#555555")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(kpi_grid)
    story.append(Spacer(1, 6))

    # 3. Compact High-Impact Chart (Dual-Axis Production vs Rejection Trend)
    fig, ax1 = plt.subplots(figsize=(7.5, 1.8), dpi=140)
    daily = df.groupby("date").agg(p=("produced", "sum"), r=("rejected", "sum")).reset_index()
    daily["rate"] = (100.0 * daily["r"] / daily["p"]).round(2)
    daily = daily.sort_values("date").reset_index(drop=True)

    x = daily["date"].astype(str)
    ax1.bar(x, daily["p"], color="#CBD5E1", width=0.6, label="Production Volume")
    ax1.set_ylabel("Output (pcs)", fontsize=7, color="#555555")
    ax1.tick_params(labelsize=6)

    ax2 = ax1.twinx()
    ax2.plot(x, daily["rate"], color="#E8420C", lw=1.8, marker="o", markersize=2.5, label="Rejection %")
    ax2.axhline(config.REJECTION_TARGET, ls="--", color="#666666", lw=1, label=f"Target ({config.REJECTION_TARGET}%)")
    ax2.set_ylabel("Rejection %", fontsize=7, color="#E8420C")
    ax2.tick_params(labelsize=6)

    ax1.set_title("Plant Production Volume vs Rejection Rate Trajectory", fontsize=8, fontweight="bold", loc="left", color="#1F3A5F")
    if len(x) > 10:
        step = max(1, len(x) // 7)
        ax1.set_xticks(range(0, len(x), step))
        ax1.set_xticklabels([x.iloc[i] for i in range(0, len(x), step)], rotation=15)

    ax1.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)
    fig.tight_layout()

    chart_buf = io.BytesIO()
    fig.savefig(chart_buf, format="png", dpi=140)
    plt.close(fig)
    chart_buf.seek(0)
    story.append(Image(chart_buf, width=520, height=125))
    story.append(Spacer(1, 6))

    # 4. Smart Insights: Key Operational Findings & Prescriptive Actions
    story.append(Paragraph("<b>SMART OPERATIONAL INSIGHTS & ACTION REGISTER</b>", head2_style))

    insights_rows = []
    # Header
    insights_rows.append([
        Paragraph("<b>CORE FINDINGS & ROOT-CAUSE ALERTS</b>", body_style),
        Paragraph("<b>RECOMMENDED CONTAINMENT & CORRECTIVE ACTIONS</b>", body_style),
    ])

    # 3 paired rows
    for i in range(max(len(findings), len(actions))):
        f_p = Paragraph(f"<b>{i+1}. {findings[i]['title']}:</b> {findings[i]['text']}", bullet_style) if i < len(findings) else Paragraph("-", bullet_style)
        a_p = Paragraph(f"<b>{i+1}. {actions[i]['title']}:</b> {actions[i]['text']} <i>(Owner: {actions[i]['owner']})</i>", bullet_style) if i < len(actions) else Paragraph("-", bullet_style)
        insights_rows.append([f_p, a_p])

    insights_table = Table(insights_rows, colWidths=[260, 260])
    insights_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F5FA")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(insights_table)
    story.append(Spacer(1, 8))

    # 5. Sign-off Block (Single page strictly maintained)
    sign_data = [
        ["PREPARED BY (QA & MIS):", "REVIEWED & AUTHORIZED BY (PLANT HEAD):"],
        ["Signature: __________________________", "Signature: __________________________"],
        [f"Date: {date.today():%d-%b-%Y}", f"Date: {date.today():%d-%b-%Y}"],
    ]
    sign_table = Table(sign_data, colWidths=[260, 260])
    sign_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#444444")),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    story.append(KeepTogether([
        HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#CBD5E1"), spaceAfter=4),
        sign_table
    ]))

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=28,
        rightMargin=28,
        topMargin=26,
        bottomMargin=20,
    )
    doc.build(story)
    return buf.getvalue()


# ==============================================================================
# 3. POWER BI-READY DATASET EXPORT & INTEGRATION GUIDE
# ==============================================================================

def export_powerbi_dataset(
    df: pd.DataFrame,
    outdir: Optional[str] = None,
) -> Tuple[str, pd.DataFrame]:
    """
    Generate clean, denormalized dimensional star-schema export ready for
    instant consumption in Microsoft Power BI Desktop.
    """
    dest = outdir or config.REPORT_DIR
    os.makedirs(dest, exist_ok=True)
    out_file = os.path.join(dest, "powerbi_manufacturing_model.csv")

    pbi = df.copy()
    pbi["date"] = pd.to_datetime(pbi["date"])
    pbi["year"] = pbi["date"].dt.year
    pbi["month_name"] = pbi["date"].dt.strftime("%B")
    pbi["month_year"] = pbi["date"].dt.strftime("%b %Y")
    pbi["week_number"] = pbi["date"].dt.isocalendar().week.astype(int)
    pbi["day_name"] = pbi["date"].dt.strftime("%A")

    # Map costs
    costs = load_copq_costs()
    pbi["unit_scrap_cost_inr"] = pbi["product"].map(lambda p: costs.get(p, {}).get("scrap", 1000.0))
    pbi["unit_rework_cost_inr"] = pbi["product"].map(lambda p: costs.get(p, {}).get("rework", 300.0))

    if "scrap" not in pbi.columns:
        pbi["scrap"] = pbi["rejected"]
    if "rework" not in pbi.columns:
        pbi["rework"] = 0

    pbi["scrap_cost_inr"] = (pbi["scrap"] * pbi["unit_scrap_cost_inr"]).round(2)
    pbi["rework_cost_inr"] = (pbi["rework"] * pbi["unit_rework_cost_inr"]).round(2)
    pbi["total_copq_inr"] = (pbi["scrap_cost_inr"] + pbi["rework_cost_inr"]).round(2)

    pbi["rejection_rate"] = (pbi["rejected"] / pbi["produced"].replace(0, np.nan)).fillna(0).round(4)
    pbi["target_rejection_rate"] = config.REJECTION_TARGET / 100.0

    pbi.to_csv(out_file, index=False)
    return out_file, pbi


def get_powerbi_guide() -> str:
    """Return implementation guide matching Sakthi Hackathon Round 1 specifications."""
    return """
# Power BI Integration Guide - SmartMIS Manufacturing Analytics
*Sakthi Hackathon 2.0 | PS-005: Automated Manufacturing MIS and Rejection Report Generator*

### 1. Data Connection Steps
1. Launch **Power BI Desktop**.
2. Click **Get Data** ➔ **Text/CSV** and select `powerbi_manufacturing_model.csv`.
3. Click **Transform Data** (Power Query) to confirm column types:
   - `date` as Date
   - `produced`, `rejected`, `scrap`, `rework`, `planned_qty` as Whole Number
   - `scrap_cost_inr`, `total_copq_inr` as Fixed Decimal Number (Currency ₹)

### 2. Suggested DAX Key Measures
```dax
// Total Production Volume
Total Produced = SUM('pms_model'[produced])

// Total Defective Parts
Total Rejected = SUM('pms_model'[rejected])

// Rejection Percentage
Rejection % = DIVIDE([Total Rejected], [Total Produced], 0)

// Total Cost of Poor Quality (INR)
Total COPQ (INR) = SUM('pms_model'[total_copq_inr])

// Schedule Plan Adherence
Plan Adherence % = DIVIDE([Total Produced], SUM('pms_model'[planned_qty]), 1)

// Plant OEE (Overall Equipment Effectiveness)
Availability = DIVIDE(
    (COUNTROWS('pms_model') * 480) - SUM('pms_model'[downtime_minutes]),
    COUNTROWS('pms_model') * 480,
    1
)
Performance = DIVIDE([Total Produced], SUM('pms_model'[planned_qty]), 1)
Quality = DIVIDE(SUM('pms_model'[good]), [Total Produced], 1)
Plant OEE = [Availability] * [Performance] * [Quality]
```

### 3. Recommended Dashboard Page Layout
- **Page 1: Executive KPI Scorecard**: Cards for Produced, Rejection %, Total COPQ (₹), and OEE %.
- **Page 2: Quality & Defect Pareto**: Pareto combo bar/line chart (`defect` vs `Total Rejected` + Cumulative %).
- **Page 3: Root-Cause Decomposition Tree**: Decomposition Tree visual drilling from `Department` ➔ `Machine` ➔ `Shift` ➔ `Defect` ➔ `Heat Lot`.
"""
