"""
Template-driven reporting engine for SmartMIS.
Supports YAML report definitions, rule-based plain-English auto commentary,
enhanced landscape Excel workbooks with native charts and frozen panes,
and executive PDF documents with sign-off blocks and page numbers.
"""
import io
import json
import logging
import os
import smtplib
from datetime import date, datetime, timedelta
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple, Union

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import openpyxl
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
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
import yaml

try:
    import config
    from data import apply_filters, kpis
except ImportError:
    try:
        from smartmis import config
        from smartmis.data import apply_filters, kpis
    except ImportError:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import config
        from data import apply_filters, kpis

log = logging.getLogger("smartmis.reports")

# ==============================================================================
# 1. TEMPLATE DISCOVERY & LOADING
# ==============================================================================

def find_template_dirs() -> List[str]:
    """Return all valid template directory candidates."""
    candidates = [
        config.TEMPLATE_DIR,
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports", "templates"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"),
        os.path.join(os.getcwd(), "reports", "templates"),
        os.path.join(os.getcwd(), "smartmis", "reports", "templates"),
    ]
    return [c for c in candidates if os.path.exists(c)]


def list_templates() -> Dict[str, Dict[str, Any]]:
    """Scan and load all YAML report templates from template directories."""
    templates: Dict[str, Dict[str, Any]] = {}
    for tdir in find_template_dirs():
        for fname in os.listdir(tdir):
            if fname.endswith((".yaml", ".yml")):
                fpath = os.path.join(tdir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        tpl = yaml.safe_load(f)
                        if isinstance(tpl, dict) and "id" in tpl:
                            templates[tpl["id"]] = tpl
                except Exception as e:
                    log.warning("Could not parse template %s: %s", fpath, e)
    return templates


def get_template(template_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve template definition by ID."""
    all_tpls = list_templates()
    if template_id in all_tpls:
        return all_tpls[template_id]
    # Fallback to direct file check
    for tdir in find_template_dirs():
        direct = os.path.join(tdir, f"{template_id}.yaml")
        if os.path.exists(direct):
            with open(direct, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
    return None


# ==============================================================================
# 2. RULE-BASED AUTO COMMENTARY GENERATION
# ==============================================================================

def generate_commentary(
    df: pd.DataFrame,
    template: Dict[str, Any],
    end_date: Optional[date] = None,
) -> str:
    """
    Generate professional, plain-English executive commentary summarizing
    period-over-period rejection trends, primary defect drivers, critical machinery,
    shift dynamics, and downtime root causes.
    """
    if df.empty:
        return "No production records available for the evaluated period."

    end = end_date or df["date"].max()
    period_days = int(template.get("period_days", 7))
    dept = template.get("department", "All")
    target = float(template.get("target_rejection", config.REJECTION_TARGET))

    # Current window vs previous window
    cur_start = end - timedelta(days=period_days - 1)
    prev_end = cur_start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_days - 1)

    cur_df = apply_filters(df, dept, start=cur_start, end=end)
    prev_df = apply_filters(df, dept, start=prev_start, end=prev_end)

    if cur_df.empty:
        return f"No active manufacturing batches recorded between {cur_start} and {end}."

    # Volumes and rates
    cur_p, cur_r = float(cur_df["produced"].sum()), float(cur_df["rejected"].sum())
    prev_p, prev_r = float(prev_df["produced"].sum()), float(prev_df["rejected"].sum())

    cur_rate = (100.0 * cur_r / cur_p) if cur_p else 0.0
    prev_rate = (100.0 * prev_r / prev_p) if prev_p else 0.0
    delta_pts = cur_rate - prev_rate

    # 1. Headline Trend
    period_name = "week on week" if period_days <= 7 else "month on month"
    if abs(delta_pts) < 0.05:
        headline = f"Rejection rate held steady at {cur_rate:.2f}% {period_name} (target: {target:.1f}%)."
    elif delta_pts > 0:
        headline = (
            f"Rejection rose {delta_pts:.2f} pts {period_name} "
            f"(from {prev_rate:.2f}% to {cur_rate:.2f}%, {'exceeding' if cur_rate > target else 'within'} target of {target:.1f}%)."
        )
    else:
        headline = (
            f"Rejection improved by {abs(delta_pts):.2f} pts {period_name} "
            f"(declining from {prev_rate:.2f}% down to {cur_rate:.2f}%, {'below' if cur_rate <= target else 'approaching'} target limit of {target:.1f}%)."
        )

    # 2. Defect Breakdown & Root Cause
    rej_df = cur_df[cur_df["rejected"] > 0]
    defect_stmt = ""
    if not rej_df.empty:
        top_defect_series = rej_df.groupby("defect")["rejected"].sum().sort_values(ascending=False)
        top_defect = top_defect_series.index[0]
        top_cnt = int(top_defect_series.iloc[0])
        top_share = (100.0 * top_cnt / cur_r) if cur_r else 0.0
        defect_stmt = f"Main defect contributor: {top_defect} ({top_cnt:,} units, {top_share:.1f}% share of rejections)."

    # 3. Machine Focus
    mach_stmt = ""
    mach_rates = cur_df.groupby("machine").apply(lambda g: 100.0 * g["rejected"].sum() / max(1, g["produced"].sum()), include_groups=False).sort_values(ascending=False)
    if not mach_rates.empty:
        worst_mach = mach_rates.index[0]
        worst_mach_pct = float(mach_rates.iloc[0])
        mach_stmt = f"Machine {worst_mach} recorded peak rejection at {worst_mach_pct:.2f}%."

    # 4. Shift Dynamics
    shift_stmt = ""
    if "shift" in cur_df.columns:
        shift_rates = cur_df.groupby("shift").apply(lambda g: 100.0 * g["rejected"].sum() / max(1, g["produced"].sum()), include_groups=False).sort_values(ascending=False)
        if len(shift_rates) > 1:
            worst_shift = shift_rates.index[0]
            best_shift = shift_rates.index[-1]
            shift_stmt = f"Shift {worst_shift} recorded the highest rejection at {shift_rates.iloc[0]:.2f}%, compared to Shift {best_shift} at {shift_rates.iloc[-1]:.2f}%."

    # 5. Scrap vs Rework & Downtime
    scrap_stmt = ""
    if "scrap" in cur_df.columns and "rework" in cur_df.columns and cur_r > 0:
        tot_sc = int(cur_df["scrap"].sum())
        tot_rw = int(cur_df["rework"].sum())
        sc_pct = round(100.0 * tot_sc / cur_r, 1)
        rw_pct = round(100.0 * tot_rw / cur_r, 1)
        scrap_stmt = f"Scrap constituted {sc_pct}% of non-conformance (melt loss), while {rw_pct}% was salvaged via rework."

    dt_stmt = ""
    if "downtime_minutes" in cur_df.columns:
        tot_dt = int(cur_df["downtime_minutes"].sum())
        if tot_dt > 0:
            top_reason = "Operational"
            if "downtime_reason" in cur_df.columns:
                valid_reasons = cur_df[cur_df["downtime_reason"] != "None"]
                if not valid_reasons.empty:
                    top_reason = valid_reasons.groupby("downtime_reason")["downtime_minutes"].sum().sort_values(ascending=False).index[0]
            dt_stmt = f"Total reported downtime reached {tot_dt // 60}h {tot_dt % 60}m, led by {top_reason}."

    # Construct final paragraphs
    p1 = f"{headline} {defect_stmt} {mach_stmt}".strip()
    p2_parts = [s for s in [shift_stmt, scrap_stmt, dt_stmt] if s]
    p2 = " ".join(p2_parts)
    return f"{p1}\n\n{p2}" if p2 else p1


# ==============================================================================
# 3. TEMPLATE DATA PREPARATION
# ==============================================================================

def _rate_table(df: pd.DataFrame, group_cols: List[str]) -> pd.DataFrame:
    """Group by columns and compute aggregate production, rejection, and rates."""
    aggs: Dict[str, Any] = {"produced": ("produced", "sum"), "rejected": ("rejected", "sum")}
    if "scrap" in df.columns:
        aggs["scrap"] = ("scrap", "sum")
    if "rework" in df.columns:
        aggs["rework"] = ("rework", "sum")

    g = df.groupby(group_cols).agg(**aggs).reset_index()
    g["rejection_%"] = (100.0 * g["rejected"] / g["produced"].replace(0, np.nan)).fillna(0).round(2)
    return g


def prepare_template_report(
    df: pd.DataFrame,
    template: Dict[str, Any],
    end_date: Optional[date] = None,
) -> Tuple[Dict[str, pd.DataFrame], str, Dict[str, Any], str, Dict[str, Any]]:
    """
    Execute report template against the central dataset.
    Returns: (sections_dict, title_string, kpis_dict, commentary_text, template_meta)
    """
    end = end_date or df["date"].max()
    period_days = int(template.get("period_days", 7))
    start_dt = end - timedelta(days=period_days - 1)
    dept = template.get("department", "All")
    title = f"{template.get('title', 'Manufacturing Report')} ({start_dt:%d-%b-%Y} to {end:%d-%b-%Y})"

    filtered = apply_filters(df, dept, start=start_dt, end=end)

    # Compute high-level KPIs
    cur_kpis = kpis(filtered)
    if not filtered.empty:
        cur_kpis["Scrap"] = int(filtered["scrap"].sum()) if "scrap" in filtered.columns else cur_kpis["Rejected"]
        cur_kpis["Rework"] = int(filtered["rework"].sum()) if "rework" in filtered.columns else 0
        planned = int(filtered["planned_qty"].sum()) if "planned_qty" in filtered.columns else cur_kpis["Produced"]
        cur_kpis["Plan Adherence %"] = round(100.0 * cur_kpis["Produced"] / max(1, planned), 1)
        tot_dt = int(filtered["downtime_minutes"].sum()) if "downtime_minutes" in filtered.columns else 0
        cur_kpis["Total Downtime (hrs)"] = round(tot_dt / 60.0, 1)

    # Build sections
    sections: Dict[str, pd.DataFrame] = {}
    for sec in template.get("sections", []):
        sec_name = sec.get("name", sec.get("id"))
        sec_type = sec.get("type", "grouped")
        sort_by = sec.get("sort_by")
        ascending = sec.get("sort_ascending", True)

        if sec_type == "defect_pareto":
            rej_only = filtered[filtered["rejected"] > 0]
            if rej_only.empty:
                t = pd.DataFrame(columns=["defect", "rejected", "share_%", "cum_%"])
            else:
                d = rej_only.groupby("defect")["rejected"].sum().reset_index()
                tot_r = d["rejected"].sum()
                d["share_%"] = (100.0 * d["rejected"] / tot_r).round(2)
                d = d.sort_values("rejected", ascending=False).reset_index(drop=True)
                d["cum_%"] = (100.0 * d["rejected"].cumsum() / tot_r).round(1)
                t = d
        else:
            groupby = sec.get("groupby", ["date"])
            t = _rate_table(filtered, groupby)

        if sort_by and sort_by in t.columns:
            t = t.sort_values(sort_by, ascending=ascending).reset_index(drop=True)

        sections[sec_name] = t

    commentary = generate_commentary(df, template, end)
    return sections, title, cur_kpis, commentary, template


# ==============================================================================
# 4. ENHANCED EXCEL ENGINE (LANDSCAPE, NATIVE CHARTS, KPI BAND, FROZEN PANES)
# ==============================================================================

def to_excel_from_template(
    sections: Dict[str, pd.DataFrame],
    title: str,
    kpi_dict: Optional[Dict[str, Any]] = None,
    commentary: Optional[str] = None,
    template: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Generate professional executive Excel workbook with landscape print setup,
    frozen panes, styled KPI metrics band, conditional formatting, and native charts.
    """
    buf = io.BytesIO()
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    navy = PatternFill("solid", fgColor="1F3A5F")
    light_blue = PatternFill("solid", fgColor="F2F5FA")
    soft_red = PatternFill("solid", fgColor="F8CBAD")
    white_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    kpi_title_font = Font(name="Calibri", size=9, bold=True, color="FFFFFF")
    kpi_val_font = Font(name="Calibri", size=14, bold=True, color="1F3A5F")
    border_thin = Border(
        left=Side(style="thin", color="CCCCCC"),
        right=Side(style="thin", color="CCCCCC"),
        top=Side(style="thin", color="CCCCCC"),
        bottom=Side(style="thin", color="CCCCCC"),
    )

    target_rej = float(template.get("target_rejection", config.REJECTION_TARGET)) if template else config.REJECTION_TARGET

    for sheet_name, table in sections.items():
        ws = wb.create_sheet(title=sheet_name[:30])

        # Page setup: A4 Landscape, Fit to page wide
        ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0

        # Row 1: Company & Title
        ws["A1"] = f"{config.COMPANY} - {title}"
        ws["A1"].font = Font(name="Calibri", size=16, bold=True, color="1F3A5F")

        # Row 2: Subtitle
        ws["A2"] = f"Generated: {datetime.now().strftime('%d-%b-%Y %H:%M')} | Section: {sheet_name}"
        ws["A2"].font = Font(name="Calibri", size=10, italic=True, color="777777")

        # Row 3-4: Executive Commentary (if provided)
        if commentary:
            ws.merge_cells("A3:H4")
            comm_cell = ws["A3"]
            comm_cell.value = f"Executive Commentary: {commentary.replace(chr(10), ' ')}"
            comm_cell.font = Font(name="Calibri", size=9, italic=True, color="333333")
            comm_cell.fill = light_blue
            comm_cell.alignment = Alignment(wrap_text=True, vertical="center")

        # Row 6-7: Styled KPI Metrics Band
        start_row = 6
        if kpi_dict:
            kpi_cols = ["Produced", "Good", "Rejected", "Rejection %", "Scrap", "Rework", "Plan Adherence %"]
            col_idx = 1
            for k in kpi_cols:
                if k in kpi_dict:
                    val = kpi_dict[k]
                    # Title cell
                    tc = ws.cell(row=start_row, column=col_idx, value=k.upper())
                    tc.fill = navy
                    tc.font = kpi_title_font
                    tc.alignment = Alignment(horizontal="center", vertical="center")
                    # Value cell
                    vc = ws.cell(row=start_row + 1, column=col_idx)
                    vc.fill = light_blue
                    vc.font = kpi_val_font
                    vc.alignment = Alignment(horizontal="center", vertical="center")
                    vc.border = border_thin

                    if "%" in k:
                        vc.value = f"{val}%"
                    else:
                        vc.value = val
                        vc.number_format = "#,##0"
                    col_idx += 1
            start_row += 3
        else:
            start_row = 5

        # Data Table header
        table_header_row = start_row
        for col_i, col_name in enumerate(table.columns, start=1):
            cell = ws.cell(row=table_header_row, column=col_i, value=str(col_name).replace("_", " ").title())
            cell.fill = navy
            cell.font = white_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Data Rows
        for r_i, row in enumerate(table.itertuples(index=False), start=table_header_row + 1):
            is_even = (r_i % 2 == 0)
            for c_i, val in enumerate(row, start=1):
                c = ws.cell(row=r_i, column=c_i, value=val)
                c.border = border_thin
                if is_even:
                    c.fill = light_blue
                if isinstance(val, (int, np.integer)):
                    c.number_format = "#,##0"
                    c.alignment = Alignment(horizontal="right")
                elif isinstance(val, (float, np.floating)):
                    c.number_format = "0.00"
                    c.alignment = Alignment(horizontal="right")
                elif isinstance(val, (date, datetime)):
                    c.value = str(val)
                    c.alignment = Alignment(horizontal="center")

        # Auto column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = col[0].column_letter
            ws.column_dimensions[col_letter].width = max(12, min(max_len + 3, 35))

        # Conditional formatting for Rejection %
        if "rejection_%" in table.columns and len(table) > 0:
            ci = table.columns.get_loc("rejection_%") + 1
            col_ltr = ws.cell(row=table_header_row, column=ci).column_letter
            rule = CellIsRule(operator="greaterThan", formula=[str(target_rej)], fill=soft_red, font=Font(bold=True, color="9C0006"))
            ws.conditional_formatting.add(f"{col_ltr}{table_header_row + 1}:{col_ltr}{table_header_row + len(table)}", rule)

        # Native Chart embedding
        if len(table) > 0 and table.shape[1] >= 2:
            chart_col_ltr = ws.cell(row=1, column=len(table.columns) + 2).column_letter
            chart_target_cell = f"{chart_col_ltr}{table_header_row}"

            if "rejection_%" in table.columns:
                val_ci = table.columns.get_loc("rejection_%") + 1
                ch = LineChart() if len(table) > 10 else BarChart()
                ch.title = f"Rejection % - {sheet_name}"
                ch.style = 13
                ch.height, ch.width = 11, 18
                data_ref = Reference(ws, min_col=val_ci, min_row=table_header_row, max_row=table_header_row + len(table))
                cats_ref = Reference(ws, min_col=1, min_row=table_header_row + 1, max_row=table_header_row + len(table))
                ch.add_data(data_ref, titles_from_data=True)
                ch.set_categories(cats_ref)
                ws.add_chart(ch, chart_target_cell)
            elif "rejected" in table.columns:
                val_ci = table.columns.get_loc("rejected") + 1
                ch = BarChart()
                ch.title = f"Rejected Count - {sheet_name}"
                ch.height, ch.width = 11, 18
                data_ref = Reference(ws, min_col=val_ci, min_row=table_header_row, max_row=table_header_row + len(table))
                cats_ref = Reference(ws, min_col=1, min_row=table_header_row + 1, max_row=table_header_row + len(table))
                ch.add_data(data_ref, titles_from_data=True)
                ch.set_categories(cats_ref)
                ws.add_chart(ch, chart_target_cell)

        # Frozen panes: keeps headers and KPI band frozen while scrolling
        ws.freeze_panes = f"A{table_header_row + 1}"

    wb.save(buf)
    return buf.getvalue()


# Legacy compatible wrapper
def to_excel(sheets: Dict[str, pd.DataFrame], title: str) -> bytes:
    return to_excel_from_template(sheets, title)


# ==============================================================================
# 5. ENHANCED PDF ENGINE (COMMENTARY, KPI SUMMARY, CHARTS, SIGN-OFF BLOCKS)
# ==============================================================================

def _chart_to_image_flowable(table: pd.DataFrame, title: str, target: float = 4.0) -> Image:
    """Generate high-resolution PNG chart and return ReportLab Image flowable."""
    fig, ax = plt.subplots(figsize=(7.2, 2.3), dpi=140)
    x = table.iloc[:, 0].astype(str)

    if "rejection_%" in table.columns:
        if len(table) > 10:
            ax.plot(range(len(x)), table["rejection_%"], color="#E8420C", marker="o", markersize=3, lw=2, label="Rejection %")
        else:
            ax.bar(x, table["rejection_%"], color="#1F3A5F", width=0.55, label="Rejection %")
        ax.axhline(target, ls="--", color="#888888", lw=1.2, label=f"Target ({target}%)")
        ax.set_ylabel("Rejection %", fontsize=8)
        ax.legend(fontsize=7, loc="upper right")
    elif "share_%" in table.columns:
        ax.bar(x, table["rejected"], color="#E8420C", width=0.55)
        ax.set_ylabel("Rejected Qty", fontsize=8)
    else:
        y_col = table.columns[1]
        ax.bar(x, table[y_col], color="#1F3A5F", width=0.55)
        ax.set_ylabel(str(y_col).title(), fontsize=8)

    ax.set_title(title, fontsize=9, fontweight="bold", loc="left", color="#1F3A5F")
    ax.tick_params(labelsize=7)
    if len(x) > 10:
        step = max(1, len(x) // 8)
        ax.set_xticks(range(0, len(x), step))
        ax.set_xticklabels([x.iloc[i] for i in range(0, len(x), step)], rotation=25)
    else:
        plt.xticks(rotation=20)

    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140)
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=520, height=160)


def to_pdf_from_template(
    sections: Dict[str, pd.DataFrame],
    title: str,
    kpi_dict: Optional[Dict[str, Any]] = None,
    commentary: Optional[str] = None,
    template: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Generate professional executive PDF report featuring header cover block,
    KPI summary table, rule-based commentary box, section charts, formatted tables,
    and formal 'Prepared by / Reviewed by' sign-off blocks.
    """
    buf = io.BytesIO()
    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1F3A5F"),
        alignment=0,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#555555"),
    )
    comm_style = ParagraphStyle(
        "CommentaryText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#222222"),
    )
    h2_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#1F3A5F"),
        spaceBefore=10,
        spaceAfter=6,
    )

    story: List[Any] = []

    # 1. Header block
    story.append(Paragraph(f"<b>{config.COMPANY}</b>", subtitle_style))
    story.append(Spacer(1, 2))
    story.append(Paragraph(title, title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%d-%b-%Y %H:%M')} | SmartMIS Enterprise Intelligence", subtitle_style))
    story.append(Spacer(1, 10))

    # 2. Executive Commentary Box
    if commentary:
        comm_paras = [Paragraph(f"<b>Executive Commentary & Operational Insights:</b>", comm_style)]
        for p in commentary.split("\n\n"):
            comm_paras.append(Spacer(1, 3))
            comm_paras.append(Paragraph(p, comm_style))
        comm_box = Table([[comm_paras]], colWidths=[520])
        comm_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F2F5FA")),
            ("LINELEFT", (0, 0), (-1, -1), 4, colors.HexColor("#1F3A5F")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D7E5")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ]))
        story.append(comm_box)
        story.append(Spacer(1, 12))

    # 3. KPI Summary Table
    if kpi_dict:
        k_labels = ["Produced", "Good", "Rejected", "Rejection %", "Scrap", "Rework", "Adherence"]
        k_values = [
            f"{kpi_dict.get('Produced', 0):,}",
            f"{kpi_dict.get('Good', 0):,}",
            f"{kpi_dict.get('Rejected', 0):,}",
            f"{kpi_dict.get('Rejection %', 0):.2f}%",
            f"{kpi_dict.get('Scrap', 0):,}",
            f"{kpi_dict.get('Rework', 0):,}",
            f"{kpi_dict.get('Plan Adherence %', 100):.1f}%",
        ]
        kpi_table = Table([k_labels, k_values], colWidths=[74] * 7)
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F8FAFC")),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 1), (-1, 1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 14))

    # 4. Sections & Charts
    target_rej = float(template.get("target_rejection", config.REJECTION_TARGET)) if template else config.REJECTION_TARGET
    for name, tb in sections.items():
        if tb.empty:
            continue
        story.append(Paragraph(name, h2_style))
        # Embedded Chart
        story.append(_chart_to_image_flowable(tb, f"{name} Overview", target=target_rej))
        story.append(Spacer(1, 6))

        # Formatted Data Table (max 12 rows for PDF page economy)
        display_tb = tb.head(12)
        cols = [str(c).replace("_", " ").title() for c in display_tb.columns]
        data_rows = [cols] + [[f"{v:,}" if isinstance(v, (int, np.integer)) else f"{v:.2f}" if isinstance(v, (float, np.floating)) else str(v) for v in row] for row in display_tb.values]

        col_w = 520.0 / len(cols)
        data_table = Table(data_rows, colWidths=[col_w] * len(cols), repeatRows=1)
        data_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(data_table)
        story.append(Spacer(1, 14))

    # 5. Sign-off Block ("Prepared by" & "Reviewed by")
    signoff = template.get("signoff", {}) if template else {}
    prep_by = signoff.get("prepared_by", "MIS Engineer / Quality Assurance")
    rev_by = signoff.get("reviewed_by", "Plant Operations Head")

    sign_data = [
        ["PREPARED BY:", "REVIEWED & APPROVED BY:"],
        ["\n\n__________________________________", "\n\n__________________________________"],
        [f"Signature: ______________________", f"Signature: ______________________"],
        [f"Designation: {prep_by}", f"Designation: {rev_by}"],
        [f"Date: {date.today():%d-%b-%Y}", f"Date: {date.today():%d-%b-%Y}"],
    ]
    sign_table = Table(sign_data, colWidths=[260, 260])
    sign_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(KeepTogether([HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceAfter=8), sign_table]))

    # Footer Callback with page numbers
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#777777"))
        canvas.drawString(36, 22, f"SmartMIS Automated Manufacturing MIS | Confidential")
        canvas.drawRightString(A4[0] - 36, 22, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()


# Legacy compatible wrapper
def to_pdf(sheets: Dict[str, pd.DataFrame], title: str) -> bytes:
    return to_pdf_from_template(sheets, title)


# ==============================================================================
# 6. SMTP EMAIL DISPATCH (WITH DRY-RUN SIMULATION)
# ==============================================================================

def send_report_email(
    file_paths: List[str],
    recipients: Optional[str] = None,
    subject: Optional[str] = None,
    commentary: Optional[str] = None,
    dry_run: Optional[bool] = None,
) -> Tuple[bool, str]:
    """
    Deliver generated reports to management and quality leads via SMTP.
    Supports dry-run mode for demonstrations without live SMTP servers.
    """
    is_dry_run = dry_run if dry_run is not None else config.SMTP_DRY_RUN
    to_addrs = [r.strip() for r in (recipients or config.SMTP_TO).split(",") if r.strip()]
    if not to_addrs:
        to_addrs = ["management@smartmis.local"]

    sub = subject or f"[SmartMIS Alert] Manufacturing Performance Report - {date.today():%d-%b-%Y}"

    body_html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #222; line-height: 1.5;">
        <div style="background-color: #1F3A5F; padding: 16px 20px; color: #ffffff; border-radius: 6px;">
          <h2 style="margin: 0;">{config.COMPANY}</h2>
          <p style="margin: 4px 0 0; color: #F4B183;">Automated Manufacturing MIS &amp; Rejection Report</p>
        </div>
        <div style="padding: 16px 0;">
          <p>Dear Management Team,</p>
          <p>Please find attached the latest scheduled manufacturing performance and rejection reports for your review.</p>
          <div style="background: #F2F5FA; border-left: 4px solid #1F3A5F; padding: 12px 16px; margin: 16px 0; border-radius: 4px;">
            <h4 style="margin: 0 0 8px; color: #1F3A5F;">Automated Executive Commentary:</h4>
            <p style="margin: 0; font-size: 13px; color: #333;">{(commentary or 'No critical anomalies flagged for this period.').replace(chr(10), '<br>')}</p>
          </div>
          <p style="font-size: 12px; color: #777;">Attached files: {', '.join(os.path.basename(f) for f in file_paths)}</p>
        </div>
        <hr style="border: 0; border-top: 1px solid #eee;">
        <p style="font-size: 11px; color: #888;">Generated automatically by SmartMIS 2.0. Do not reply to this email.</p>
      </body>
    </html>
    """

    if is_dry_run or not config.SMTP_USER:
        msg = (
            f"[DRY-RUN SIMULATION] Email to {to_addrs} prepared successfully with "
            f"{len(file_paths)} attachments: {', '.join(os.path.basename(f) for f in file_paths)}."
        )
        log.info(msg)
        return True, msg

    try:
        msg = MIMEMultipart()
        msg["From"] = config.SMTP_FROM
        msg["To"] = ", ".join(to_addrs)
        msg["Subject"] = sub
        msg.attach(MIMEText(body_html, "html"))

        for path in file_paths:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(path))
                    part["Content-Disposition"] = f'attachment; filename="{os.path.basename(path)}"'
                    msg.attach(part)

        server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10)
        if config.SMTP_PORT == 587:
            server.starttls()
        server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True, f"Dispatched live email to {len(to_addrs)} recipients."
    except Exception as e:
        err = f"SMTP transmission failed: {e}"
        log.error(err)
        return False, err
