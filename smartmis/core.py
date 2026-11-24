"""
Facade and integration module for SmartMIS.
Maintains 100% backwards-compatibility while delegating to specialized modules:
data.py, reports.py, and scheduler.py.
"""
import io
import json
import logging
import os
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

import config

# Import and re-export data layer
from data import (
    PRODUCTS, MACHINES, DEFECTS, DEFECT_CATEGORIES, CUSTOMERS, PATTERN_MAP,
    DOWNTIME_REASONS, SHIFTS, CANONICAL_COLUMNS, DEFAULT_PRESETS,
    sample_pms, clean, quality_issues, auto_map_columns, apply_column_mapping,
    save_mapping_preset, load_mapping_presets, read_uploaded_file,
    test_sql_connection, fetch_sql, seed_mock_sql_db, fetch_api_pms,
    init_central_db, save_sqlite, load_sqlite, incremental_load,
    get_ingestion_log, reset_central_db
)

# Import and re-export reporting layer
from reports import (
    find_template_dirs, list_templates, get_template, generate_commentary,
    prepare_template_report, to_excel_from_template, to_pdf_from_template,
    to_excel, to_pdf, send_report_email
)

# Import and re-export scheduler layer
from scheduler import (
    load_schedule_config, save_schedule_config, update_scheduler_job,
    run_scheduled_automation, list_archived_reports
)

# Import and re-export advanced analytics & KPIs
from kpis import (
    compute_advanced_kpis, DEFAULT_PART_COSTS, load_copq_costs,
    save_copq_costs, compute_copq, compute_spc_p_chart,
    detect_anomalies, forecast_production_and_rejection, drill_down_level
)

# Import and re-export enterprise authentication & audit log
from auth import (
    authenticate_user, filter_data_by_role, log_audit_action,
    get_audit_logs, load_users, save_users, DEFAULT_USERS, init_audit_db
)

# Import and re-export natural language query engine
from nlp_query import (
    ask_your_data, parse_query_rule_based, execute_whitelisted_query,
    WHITELISTED_FUNCTIONS
)

# Import and re-export executive briefing and Power BI integration
from executive import (
    generate_smart_insights, generate_executive_summary_pdf,
    export_powerbi_dataset, get_powerbi_guide
)

# Import and re-export demo simulation, ROI, and requirement mapping
from demo import (
    generate_streaming_batch, inject_defect_spike, normalize_dates,
    compute_time_saved_roi, get_requirement_checklist,
    DEFAULT_ROI_ASSUMPTIONS
)

log = logging.getLogger('smartmis')


def apply_filters(
    df: pd.DataFrame,
    dept: Optional[str] = None,
    products: Optional[List[str]] = None,
    start: Optional[date] = None,
    end: Optional[date] = None,
    shift: Optional[List[str]] = None,
    machines: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Filter production dataframe across multiple operational dimensions."""
    if dept and dept != "All":
        df = df[df["department"] == dept]
    if products:
        df = df[df["product"].isin(products)]
    if shift:
        df = df[df["shift"].isin(shift)]
    if machines:
        df = df[df["machine"].isin(machines)]
    if start:
        df = df[pd.to_datetime(df["date"]) >= pd.to_datetime(start)]
    if end:
        df = df[pd.to_datetime(df["date"]) <= pd.to_datetime(end)]
    return df


def kpis(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute basic production volume and rejection rate KPIs."""
    if df.empty:
        return {"Produced": 0, "Good": 0, "Rejected": 0, "Rejection %": 0.0}
    p, r = float(df["produced"].sum()), float(df["rejected"].sum())
    return {
        "Produced": int(p),
        "Good": int(p - r),
        "Rejected": int(r),
        "Rejection %": round(100.0 * r / p, 2) if p else 0.0,
    }


def _rate(g: Any) -> pd.DataFrame:
    """Aggregate group object to calculate produced, rejected, and rate."""
    res = g.agg(produced=("produced", "sum"), rejected=("rejected", "sum")).reset_index()
    res["rejection_%"] = (100.0 * res["rejected"] / res["produced"].replace(0, np.nan)).fillna(0).round(2)
    return res


def weekly_report(df: pd.DataFrame, dept: str, end: Optional[date] = None) -> Tuple[Dict[str, pd.DataFrame], str]:
    """Generate weekly performance and rejection report for Foundry or Machine Shop."""
    tpl_id = "weekly_foundry" if dept == "Foundry" else "weekly_machine_shop"
    tpl = get_template(tpl_id)
    if tpl:
        sections, title, _, _, _ = prepare_template_report(df, tpl, end_date=end)
        return sections, title

    # Fallback calculation
    end = end or df["date"].max()
    w = apply_filters(df, dept, start=end - timedelta(days=6), end=end)
    return {
        "Daily Trend": _rate(w.groupby("date")),
        "By Machine": _rate(w.groupby("machine")),
        "By Product": _rate(w.groupby("product")),
    }, f"Weekly {dept} Report ({end - timedelta(days=6)} to {end})"


def monthly_rejection_report(df: pd.DataFrame, end: Optional[date] = None) -> Tuple[Dict[str, pd.DataFrame], str]:
    """Generate plant-wide monthly rejection analysis report."""
    tpl = get_template("monthly_rejection")
    if tpl:
        sections, title, _, _, _ = prepare_template_report(df, tpl, end_date=end)
        return sections, title

    # Fallback calculation
    end = end or df["date"].max()
    m = apply_filters(df, None, start=end - timedelta(days=29), end=end)
    d = (
        m[m["rejected"] > 0]
        .groupby(["department", "defect"])["rejected"]
        .sum()
        .reset_index()
        .sort_values("rejected", ascending=False)
    )
    d["share_%"] = (100.0 * d["rejected"] / d["rejected"].sum()).round(2)
    return {
        "By Defect": d,
        "By Department": _rate(m.groupby("department")),
        "By Product": _rate(m.groupby("product")),
        "Daily Trend": _rate(m.groupby("date")),
    }, f"Monthly Rejection Report ({end - timedelta(days=29)} to {end})"


def period_bounds(df: pd.DataFrame, choice: str, custom: Optional[Tuple[date, date]] = None) -> Tuple[date, date]:
    """Compute date boundaries for UI period radio selections."""
    end = df["date"].max()
    if choice == "This week":
        return end - timedelta(days=6), end
    if choice == "Last week":
        return end - timedelta(days=13), end - timedelta(days=7)
    if choice == "This month":
        return end - timedelta(days=29), end
    return (custom[0], custom[1]) if custom and len(custom) == 2 else (df["date"].min(), end)


def kpi_with_delta(
    df: pd.DataFrame,
    dept: Optional[str],
    products: Optional[List[str]],
    start: date,
    end: date,
    shift: Optional[List[str]],
    machines: Optional[List[str]],
) -> Tuple[Dict[str, Any], Dict[str, Optional[float]]]:
    """Calculate current window KPIs and delta percentage against prior window."""
    cur = kpis(apply_filters(df, dept, products, start, end, shift, machines))
    span = (end - start).days + 1
    ps, pe = start - timedelta(days=span), start - timedelta(days=1)
    prev = kpis(apply_filters(df, dept, products, ps, pe, shift, machines))

    delta: Dict[str, Optional[float]] = {}
    for k in cur:
        if prev[k]:
            delta[k] = round(100.0 * (cur[k] - prev[k]) / prev[k], 1)
        else:
            delta[k] = None
    delta["Rejection %"] = round(float(cur["Rejection %"]) - float(prev["Rejection %"]), 2)
    return cur, delta


def status(rej: float) -> str:
    """Return color status tag based on company thresholds."""
    if rej <= config.REJECTION_TARGET:
        return "green"
    elif rej <= config.AMBER_LIMIT:
        return "amber"
    return "red"


def pareto(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate defect Pareto breakdown with cumulative share percentage."""
    rej_only = df[df["rejected"] > 0]
    if rej_only.empty:
        return pd.DataFrame(columns=["defect", "rejected", "cum_%"])
    d = rej_only.groupby("defect")["rejected"].sum().sort_values(ascending=False).reset_index()
    tot = d["rejected"].sum()
    d["cum_%"] = (100.0 * d["rejected"].cumsum() / tot).round(1)
    return d


def run_scheduled(df: pd.DataFrame, outdir: Optional[str] = None) -> List[str]:
    """Execute automated reporting run and return list of generated file paths."""
    files, _ = run_scheduled_automation(df, outdir=outdir)
    return files
