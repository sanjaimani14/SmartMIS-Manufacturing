"""
Advanced Manufacturing Analytics Engine for SmartMIS.
Includes:
- OEE (Availability x Performance x Quality), FPY, Rejection %, Scrap %, Rework %, PPM, Downtime %, Adherence
- Cost of Poor Quality (COPQ) in INR (₹) with Top 5 cost drivers
- Statistical Process Control (SPC) p-chart with UCL/LCL and Western Electric / Wheeler rules
- Robust Anomaly Detection (rolling median + MAD z-score) with severity tiers
- 14-Day Production & Rejection Forecasting with 95% confidence intervals (statsmodels)
- Multi-level cascading drill-down (Department > Machine > Shift > Defect > Heat Number)
"""
import json
import logging
import math
import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
from statsmodels.tsa.holtwinters import ExponentialSmoothing

try:
    import config
except ImportError:
    from . import config

log = logging.getLogger("smartmis.kpis")

DEFAULT_PART_COSTS: Dict[str, Dict[str, float]] = {
    "Brake Drum": {"scrap": 850.0, "rework": 250.0},
    "Hub Housing": {"scrap": 1200.0, "rework": 350.0},
    "Pump Casing": {"scrap": 1450.0, "rework": 400.0},
    "Flywheel": {"scrap": 1800.0, "rework": 500.0},
    "Gear Blank": {"scrap": 950.0, "rework": 280.0},
}


# ==============================================================================
# 1. ADVANCED MANUFACTURING KPIS & OEE
# ==============================================================================

def compute_advanced_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate full manufacturing intelligence suite:
    - OEE (Availability x Performance x Quality)
    - First-Pass Yield (FPY %)
    - Rejection %, Scrap %, Rework %
    - PPM (Parts Per Million Defective)
    - Downtime %
    - Plan Adherence %
    """
    if df.empty:
        return {
            "Produced": 0,
            "Good": 0,
            "Rejected": 0,
            "Rejection %": 0.0,
            "Scrap": 0,
            "Scrap %": 0.0,
            "Rework": 0,
            "Rework %": 0.0,
            "PPM": 0,
            "First-Pass Yield %": 100.0,
            "Plan Adherence %": 100.0,
            "Total Downtime (hrs)": 0.0,
            "Downtime %": 0.0,
            "Availability %": 100.0,
            "Performance %": 100.0,
            "Quality %": 100.0,
            "OEE %": 100.0,
        }

    produced = float(df["produced"].sum())
    rejected = float(df["rejected"].sum())
    good = float(df["good"].sum()) if "good" in df.columns else (produced - rejected)

    scrap = float(df["scrap"].sum()) if "scrap" in df.columns else rejected
    rework = float(df["rework"].sum()) if "rework" in df.columns else 0.0
    planned = float(df["planned_qty"].sum()) if "planned_qty" in df.columns else produced

    # Shift-based time modeling (standard 480 operating minutes per shift batch)
    batches_count = len(df)
    planned_operating_minutes = batches_count * 480.0
    downtime_minutes = float(df["downtime_minutes"].sum()) if "downtime_minutes" in df.columns else 0.0

    # Rates
    rej_pct = round(100.0 * rejected / produced, 2) if produced else 0.0
    scrap_pct = round(100.0 * scrap / produced, 2) if produced else 0.0
    rework_pct = round(100.0 * rework / produced, 2) if produced else 0.0
    ppm = round((rejected / produced) * 1_000_000.0, 0) if produced else 0.0

    # First-Pass Yield: items that passed inspection on the very first pass without defect
    fpy_pct = round(100.0 * (produced - rejected) / produced, 2) if produced else 100.0

    # Schedule / Plan Adherence
    adherence_pct = round(100.0 * produced / planned, 2) if planned else 100.0

    # Downtime metrics
    downtime_pct = round(100.0 * downtime_minutes / max(1.0, planned_operating_minutes), 2)
    downtime_hrs = round(downtime_minutes / 60.0, 1)

    # OEE Components
    # 1. Availability = Operating Time / Planned Time
    operating_minutes = max(0.0, planned_operating_minutes - downtime_minutes)
    availability = min(1.0, max(0.0, operating_minutes / planned_operating_minutes)) if planned_operating_minutes else 1.0

    # 2. Performance = Actual Production / Target Production during operating time
    # Target scaled by operating time ratio
    target_for_operating_time = max(1.0, planned * (operating_minutes / planned_operating_minutes))
    performance = min(1.05, max(0.0, produced / target_for_operating_time)) if target_for_operating_time else 1.0

    # 3. Quality = Good Units / Total Produced
    quality = min(1.0, max(0.0, good / produced)) if produced else 1.0

    # Overall Equipment Effectiveness
    oee = availability * performance * quality * 100.0

    return {
        "Produced": int(produced),
        "Good": int(good),
        "Rejected": int(rejected),
        "Rejection %": rej_pct,
        "Scrap": int(scrap),
        "Scrap %": scrap_pct,
        "Rework": int(rework),
        "Rework %": rework_pct,
        "PPM": int(ppm),
        "First-Pass Yield %": fpy_pct,
        "Plan Adherence %": adherence_pct,
        "Total Downtime (hrs)": downtime_hrs,
        "Downtime %": downtime_pct,
        "Availability %": round(availability * 100.0, 1),
        "Performance %": round(performance * 100.0, 1),
        "Quality %": round(quality * 100.0, 1),
        "OEE %": round(oee, 1),
    }


# ==============================================================================
# 2. COST OF POOR QUALITY (COPQ) ENGINE
# ==============================================================================

def load_copq_costs(filepath: Optional[str] = None) -> Dict[str, Dict[str, float]]:
    """Load per-part scrap and rework cost matrix in INR (₹)."""
    path = filepath or config.COPQ_CONFIG_FILE
    costs = dict(DEFAULT_PART_COSTS)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                user_costs = json.load(f)
                costs.update(user_costs)
        except Exception as e:
            log.warning("Could not read COPQ file %s: %s", path, e)
    return costs


def save_copq_costs(costs: Dict[str, Dict[str, float]], filepath: Optional[str] = None) -> None:
    """Save updated COPQ cost matrix to persistent storage."""
    path = filepath or config.COPQ_CONFIG_FILE
    with open(path, "w", encoding="utf-8") as f:
        json.dump(costs, f, indent=2)


def compute_copq(
    df: pd.DataFrame,
    cost_table: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    """
    Calculate financial impact of scrap and rework in Indian Rupees (₹).
    Identifies Top 5 cost drivers across Products, Defects, and Machines.
    """
    if df.empty:
        return {
            "total_copq": 0.0,
            "total_scrap_cost": 0.0,
            "total_rework_cost": 0.0,
            "top_products": pd.DataFrame(),
            "top_defects": pd.DataFrame(),
            "top_machines": pd.DataFrame(),
        }

    costs = cost_table or load_copq_costs()

    d = df.copy()
    if "scrap" not in d.columns:
        d["scrap"] = d["rejected"]
    if "rework" not in d.columns:
        d["rework"] = 0

    # Map unit costs
    d["unit_scrap_cost"] = d["product"].map(lambda p: costs.get(p, {}).get("scrap", 1000.0))
    d["unit_rework_cost"] = d["product"].map(lambda p: costs.get(p, {}).get("rework", 300.0))

    d["scrap_cost_inr"] = d["scrap"] * d["unit_scrap_cost"]
    d["rework_cost_inr"] = d["rework"] * d["unit_rework_cost"]
    d["total_copq_inr"] = d["scrap_cost_inr"] + d["rework_cost_inr"]

    tot_copq = float(d["total_copq_inr"].sum())
    tot_scrap_cost = float(d["scrap_cost_inr"].sum())
    tot_rework_cost = float(d["rework_cost_inr"].sum())

    # 1. Top 5 Products by COPQ
    top_prods = (
        d.groupby("product")
        .agg(
            scrap_units=("scrap", "sum"),
            rework_units=("rework", "sum"),
            scrap_cost_inr=("scrap_cost_inr", "sum"),
            rework_cost_inr=("rework_cost_inr", "sum"),
            total_copq_inr=("total_copq_inr", "sum"),
        )
        .reset_index()
    )
    top_prods["share_%"] = (100.0 * top_prods["total_copq_inr"] / max(1.0, tot_copq)).round(1)
    top_prods = top_prods.sort_values("total_copq_inr", ascending=False).head(5).reset_index(drop=True)

    # 2. Top 5 Defects by Financial Loss
    rej_only = d[d["rejected"] > 0]
    if not rej_only.empty:
        top_defects = (
            rej_only.groupby("defect")
            .agg(
                rejected_units=("rejected", "sum"),
                total_copq_inr=("total_copq_inr", "sum"),
            )
            .reset_index()
        )
        top_defects["share_%"] = (100.0 * top_defects["total_copq_inr"] / max(1.0, tot_copq)).round(1)
        top_defects = top_defects.sort_values("total_copq_inr", ascending=False).head(5).reset_index(drop=True)
    else:
        top_defects = pd.DataFrame()

    # 3. Top 5 Machines by Financial Loss
    top_mach = (
        d.groupby("machine")
        .agg(
            department=("department", "first"),
            rejected_units=("rejected", "sum"),
            total_copq_inr=("total_copq_inr", "sum"),
        )
        .reset_index()
    )
    top_mach["share_%"] = (100.0 * top_mach["total_copq_inr"] / max(1.0, tot_copq)).round(1)
    top_mach = top_mach.sort_values("total_copq_inr", ascending=False).head(5).reset_index(drop=True)

    return {
        "total_copq": tot_copq,
        "total_scrap_cost": tot_scrap_cost,
        "total_rework_cost": tot_rework_cost,
        "top_products": top_prods,
        "top_defects": top_defects,
        "top_machines": top_mach,
    }


# ==============================================================================
# 3. STATISTICAL PROCESS CONTROL (SPC) p-CHART
# ==============================================================================

def compute_spc_p_chart(
    df: pd.DataFrame,
    group_col: str = "date",
    target_p: Optional[float] = None,
) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """
    Generate Statistical Process Control p-chart for non-conformance rate.
    Computes variable Upper/Lower Control Limits based on subgroup sample size n_i:
        UCL_i = p_bar + 3 * sqrt(p_bar * (1 - p_bar) / n_i)
        LCL_i = max(0, p_bar - 3 * sqrt(p_bar * (1 - p_bar) / n_i))
    Detects Rule 1 (beyond 3-sigma limits), Rule 2 (7 consecutive points on one side),
    and Rule 3 (6 consecutive points trending up/down).
    """
    if df.empty:
        return pd.DataFrame(), []

    grouped = (
        df.groupby(group_col)
        .agg(
            produced=("produced", "sum"),
            rejected=("rejected", "sum"),
        )
        .reset_index()
    )
    grouped = grouped[grouped["produced"] > 0].reset_index(drop=True)

    if grouped.empty:
        return pd.DataFrame(), []

    tot_p = float(grouped["produced"].sum())
    tot_r = float(grouped["rejected"].sum())
    p_bar = (tot_r / tot_p) if tot_p else 0.0

    p_vals = grouped["rejected"] / grouped["produced"]
    grouped["p"] = p_vals
    grouped["p_pct"] = (p_vals * 100.0).round(2)
    grouped["cl_pct"] = round(p_bar * 100.0, 2)

    # Compute 3-sigma limits per subgroup
    sigmas = np.sqrt(p_bar * (1.0 - p_bar) / grouped["produced"].replace(0, np.nan)).fillna(0)
    ucl = np.clip(p_bar + 3.0 * sigmas, 0.0, 1.0)
    lcl = np.clip(p_bar - 3.0 * sigmas, 0.0, 1.0)

    grouped["ucl_pct"] = (ucl * 100.0).round(2)
    grouped["lcl_pct"] = (lcl * 100.0).round(2)

    # Alarm and Out-of-Control Rules
    alarms: List[Dict[str, Any]] = []
    is_ooc = [False] * len(grouped)
    reasons = [""] * len(grouped)

    # Rule 1: Point beyond control limits
    for i in range(len(grouped)):
        val = p_vals.iloc[i]
        limit_high = ucl.iloc[i]
        limit_low = lcl.iloc[i]
        grp_val = grouped[group_col].iloc[i]

        if val > limit_high:
            is_ooc[i] = True
            reasons[i] = "Point Exceeds Upper Control Limit (UCL)"
            alarms.append({
                "index": i,
                "label": str(grp_val),
                "rule": "Rule 1: Beyond 3-Sigma Limit",
                "value_pct": round(val * 100.0, 2),
                "limit_pct": round(limit_high * 100.0, 2),
                "severity": "CRITICAL",
                "message": f"Sample on {grp_val} at {val*100:.2f}% exceeds UCL ({limit_high*100:.2f}%). Special cause variation detected.",
            })
        elif val < limit_low and limit_low > 0:
            is_ooc[i] = True
            reasons[i] = "Point Below Lower Control Limit (LCL)"
            alarms.append({
                "index": i,
                "label": str(grp_val),
                "rule": "Rule 1: Beyond 3-Sigma Limit",
                "value_pct": round(val * 100.0, 2),
                "limit_pct": round(limit_low * 100.0, 2),
                "severity": "INFO",
                "message": f"Sample on {grp_val} at {val*100:.2f}% dropped below LCL. Quality breakthrough / process shift.",
            })

    # Rule 2: Run of 7 points on one side of centerline
    for i in range(6, len(grouped)):
        window = p_vals.iloc[i - 6 : i + 1]
        grp_val = grouped[group_col].iloc[i]
        if (window > p_bar).all():
            is_ooc[i] = True
            reasons[i] = (reasons[i] + " | " if reasons[i] else "") + "Run of 7 Above Centerline"
            alarms.append({
                "index": i,
                "label": str(grp_val),
                "rule": "Rule 2: Run of 7",
                "value_pct": round(window.iloc[-1] * 100.0, 2),
                "limit_pct": round(p_bar * 100.0, 2),
                "severity": "WARNING",
                "message": f"Run of 7 consecutive points above average on {grp_val}. Process mean shift indicated.",
            })
        elif (window < p_bar).all():
            is_ooc[i] = True
            reasons[i] = (reasons[i] + " | " if reasons[i] else "") + "Run of 7 Below Centerline"

    # Rule 3: Trend of 6 consecutive increasing or decreasing points
    for i in range(5, len(grouped)):
        window = p_vals.iloc[i - 5 : i + 1].values
        grp_val = grouped[group_col].iloc[i]
        diffs = np.diff(window)
        if (diffs > 0).all():
            is_ooc[i] = True
            reasons[i] = (reasons[i] + " | " if reasons[i] else "") + "Trend of 6 Steadily Increasing"
            alarms.append({
                "index": i,
                "label": str(grp_val),
                "rule": "Rule 3: Trend of 6",
                "value_pct": round(window[-1] * 100.0, 2),
                "limit_pct": round(p_bar * 100.0, 2),
                "severity": "WARNING",
                "message": f"Steady upward drift over 6 consecutive intervals detected up to {grp_val}. Tool wear or degradation suspected.",
            })

    grouped["out_of_control"] = is_ooc
    grouped["violation_notes"] = reasons
    return grouped, alarms


# ==============================================================================
# 4. ROBUST ANOMALY DETECTION ENGINE
# ==============================================================================

def detect_anomalies(
    df: pd.DataFrame,
    window: int = 7,
    threshold: float = 2.5,
) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """
    Robust time-series anomaly detection based on rolling median and
    Median Absolute Deviation (MAD) z-scores.
    Categorizes alarms into CRITICAL, WARNING, and INFO tiers.
    """
    if df.empty:
        return pd.DataFrame(), []

    daily = (
        df.groupby("date")
        .agg(
            produced=("produced", "sum"),
            rejected=("rejected", "sum"),
        )
        .reset_index()
    )
    daily["rejection_%"] = (100.0 * daily["rejected"] / daily["produced"]).round(2)
    daily = daily.sort_values("date").reset_index(drop=True)

    # Rolling median and MAD
    series = daily["rejection_%"]
    rolling_med = series.rolling(window=window, min_periods=3, center=False).median()
    rolling_mad = series.rolling(window=window, min_periods=3, center=False).apply(
        lambda w: np.median(np.abs(w - np.median(w))) if len(w) > 0 else 0.01,
        raw=True,
    ).fillna(0.1).replace(0, 0.1)

    # Robust Z-score: 0.6745 * (x - median) / MAD
    z_scores = 0.6745 * (series - rolling_med) / rolling_mad
    daily["median_%"] = rolling_med.round(2)
    daily["z_score"] = z_scores.round(2)

    alerts: List[Dict[str, Any]] = []
    severities = []

    for i in range(len(daily)):
        row = daily.iloc[i]
        dt = row["date"]
        val = row["rejection_%"]
        z = row["z_score"]
        med = row["median_%"]

        if z >= 3.0 or val >= config.AMBER_LIMIT:
            sev = "CRITICAL"
            alerts.append({
                "date": str(dt),
                "metric": "Rejection Rate (%)",
                "value": f"{val:.2f}%",
                "baseline": f"{med:.2f}%",
                "z_score": f"{z:.1f}σ",
                "severity": sev,
                "action": "Immediate containment: Halt suspect line, inspect mould sand porosity and tooling offsets.",
            })
        elif z >= 2.0:
            sev = "WARNING"
            alerts.append({
                "date": str(dt),
                "metric": "Rejection Rate (%)",
                "value": f"{val:.2f}%",
                "baseline": f"{med:.2f}%",
                "z_score": f"{z:.1f}σ",
                "severity": sev,
                "action": "Investigate shift variances and check raw material charge quality.",
            })
        elif z <= -2.0:
            sev = "INFO"
            alerts.append({
                "date": str(dt),
                "metric": "Quality Gain (%)",
                "value": f"{val:.2f}%",
                "baseline": f"{med:.2f}%",
                "z_score": f"{z:.1f}σ",
                "severity": sev,
                "action": "Benchmark operating parameters: Validate optimal shift settings for standard work.",
            })
        else:
            sev = "NORMAL"

        severities.append(sev)

    daily["severity"] = severities
    return daily, alerts


# ==============================================================================
# 5. TWO-WEEK FORECASTING WITH CONFIDENCE BANDS (STATSMODELS)
# ==============================================================================

def forecast_production_and_rejection(
    df: pd.DataFrame,
    horizon_days: int = 14,
) -> Dict[str, pd.DataFrame]:
    """
    Generate 14-day forward projections for Production Volume and Rejection Rate (%)
    using statsmodels Holt-Winters Exponential Smoothing with 95% confidence intervals.
    """
    if df.empty:
        return {"production": pd.DataFrame(), "rejection": pd.DataFrame()}

    daily = (
        df.groupby("date")
        .agg(
            produced=("produced", "sum"),
            rejected=("rejected", "sum"),
        )
        .reset_index()
    )
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values("date").reset_index(drop=True)
    daily["rejection_%"] = (100.0 * daily["rejected"] / daily["produced"]).round(2)

    last_dt = daily["date"].max()
    future_dates = [last_dt + timedelta(days=i) for i in range(1, horizon_days + 1)]

    results: Dict[str, pd.DataFrame] = {}

    for col in ["produced", "rejection_%"]:
        y = daily[col].values
        n = len(y)

        if n >= 14:
            try:
                # Fit damped additive Holt-Winters model
                fit_kwargs = {"damping_trend": 0.92}
                try:
                    model = ExponentialSmoothing(
                        y,
                        trend="add",
                        damped_trend=True,
                        seasonal=None,
                        initialization_method="estimated",
                    ).fit(**fit_kwargs)
                except TypeError:
                    model = ExponentialSmoothing(
                        y,
                        trend="add",
                        damped_trend=True,
                        seasonal=None,
                        initialization_method="estimated",
                    ).fit(damping_slope=0.92)
                preds = model.forecast(horizon_days)

                # Standard error estimation from residual variance
                residuals = y - model.fittedvalues
                sigma = float(np.std(residuals)) if len(residuals) > 0 else 1.0

                # Growing 95% confidence cone over horizon: sigma * 1.96 * sqrt(step)
                steps = np.arange(1, horizon_days + 1)
                margin = 1.96 * sigma * np.sqrt(1.0 + 0.08 * steps)

                lower = np.clip(preds - margin, 0.0 if col == "rejection_%" else 100.0, None)
                upper = np.clip(preds + margin, 0.0, 100.0 if col == "rejection_%" else None)

            except Exception as e:
                log.warning("Statsmodels fit failed for %s: %s; using linear projection", col, e)
                # Robust fallback to linear regression
                x = np.arange(n)
                slope, intercept, _, _, _ = stats.linregress(x, y)
                fx = np.arange(n, n + horizon_days)
                preds = intercept + slope * fx
                sigma = float(np.std(y))
                lower = np.clip(preds - 1.96 * sigma, 0.0, None)
                upper = np.clip(preds + 1.96 * sigma, 0.0, None)
        else:
            # Baseline mean projection
            mean_val = float(np.mean(y)) if n else 0.0
            sigma = float(np.std(y)) if n > 1 else 0.5
            preds = np.full(horizon_days, mean_val)
            lower = np.clip(preds - 1.96 * sigma, 0.0, None)
            upper = np.clip(preds + 1.96 * sigma, 0.0, None)

        f_df = pd.DataFrame({
            "date": future_dates,
            "forecast": preds.round(2 if col == "rejection_%" else 0),
            "lower_95": lower.round(2 if col == "rejection_%" else 0),
            "upper_95": upper.round(2 if col == "rejection_%" else 0),
        })

        # Combine historical with forecast
        hist_df = pd.DataFrame({
            "date": daily["date"],
            "actual": daily[col].round(2 if col == "rejection_%" else 0),
        })

        results[col] = pd.merge(hist_df, f_df, on="date", how="outer").sort_values("date").reset_index(drop=True)

    return results


# ==============================================================================
# 6. MULTI-LEVEL DRILL-DOWN ENGINE
# ==============================================================================

def drill_down_level(
    df: pd.DataFrame,
    level: str = "department",
    filter_dept: Optional[str] = None,
    filter_mach: Optional[str] = None,
    filter_shift: Optional[str] = None,
    filter_defect: Optional[str] = None,
) -> pd.DataFrame:
    """
    Hierarchical multi-level slice-and-dice:
    Department -> Machine -> Shift -> Defect -> Heat Number
    """
    filtered = df.copy()
    if filter_dept and filter_dept != "All":
        filtered = filtered[filtered["department"] == filter_dept]
    if filter_mach and filter_mach != "All":
        filtered = filtered[filtered["machine"] == filter_mach]
    if filter_shift and filter_shift != "All":
        filtered = filtered[filtered["shift"] == filter_shift]
    if filter_defect and filter_defect != "All":
        filtered = filtered[filtered["defect"] == filter_defect]

    if filtered.empty:
        return pd.DataFrame()

    group_col = {
        "department": "department",
        "machine": "machine",
        "shift": "shift",
        "defect": "defect",
        "heat_no": "heat_no",
    }.get(level, "department")

    # If drilling down to defect, filter out non-defective records
    if group_col == "defect":
        filtered = filtered[filtered["rejected"] > 0]
        if filtered.empty:
            return pd.DataFrame()

    res = (
        filtered.groupby(group_col)
        .agg(
            produced=("produced", "sum"),
            rejected=("rejected", "sum"),
            scrap=("scrap", "sum") if "scrap" in filtered.columns else ("rejected", "sum"),
            rework=("rework", "sum") if "rework" in filtered.columns else ("rejected", lambda x: 0),
            downtime_minutes=("downtime_minutes", "sum") if "downtime_minutes" in filtered.columns else ("produced", lambda x: 0),
        )
        .reset_index()
    )
    res["rejection_%"] = (100.0 * res["rejected"] / res["produced"].replace(0, np.nan)).fillna(0).round(2)
    res = res.sort_values("rejected", ascending=False).reset_index(drop=True)
    return res
