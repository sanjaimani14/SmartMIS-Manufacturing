"""
Secure Natural Language Interface ('Ask your data') for SmartMIS.
Maps natural-language user queries strictly to whitelisted analytics functions:
[top_n, trend, compare, filter, kpi]. Never arbitrary code execution.
Uses Anthropic API when ANTHROPIC_API_KEY is present; otherwise robust rule-based intent parser.
"""
import json
import logging
import os
import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests

try:
    import config
    from data import PRODUCTS, MACHINES, DEFECTS, SHIFTS
    from kpis import compute_advanced_kpis
except ImportError:
    from . import config
    from .data import PRODUCTS, MACHINES, DEFECTS, SHIFTS
    from .kpis import compute_advanced_kpis

log = logging.getLogger("smartmis.nlp_query")

# Whitelist of permissible analytics actions
WHITELISTED_FUNCTIONS = ["top_n", "trend", "compare", "filter", "kpi"]


# ==============================================================================
# 1. WHITELISTED ANALYTICS EXECUTORS
# ==============================================================================

def execute_whitelisted_query(
    df: pd.DataFrame,
    fn_name: str,
    args: Dict[str, Any],
) -> Tuple[pd.DataFrame, str, Optional[go.Figure], str]:
    """
    Execute strictly whitelisted function on the dataframe.
    Returns: (result_df, chart_type, plotly_figure, explanation_text)
    """
    if fn_name not in WHITELISTED_FUNCTIONS:
        raise ValueError(f"Forbidden function execution: '{fn_name}' is not in whitelisted operations.")

    # Apply pre-filters
    filtered = df.copy()
    filters_applied = args.get("filters", {})
    if filters_applied:
        for col, val in filters_applied.items():
            if col in filtered.columns and val and val != "All":
                if isinstance(val, list):
                    filtered = filtered[filtered[col].isin(val)]
                else:
                    filtered = filtered[filtered[col] == val]

    if filtered.empty:
        return pd.DataFrame(), "none", None, "No production records matched the given criteria."

    # 1. KPI Function
    if fn_name == "kpi":
        kpi_res = compute_advanced_kpis(filtered)
        metric = args.get("metric")
        if metric and metric in kpi_res:
            res_df = pd.DataFrame([{"Metric": metric, "Value": kpi_res[metric]}])
            exp = f"Calculated {metric}: **{kpi_res[metric]}** across {len(filtered):,} records."
        else:
            rows = [{"KPI": k, "Value": f"{v:,}" if isinstance(v, int) else f"{v}%" if "%" in k else str(v)} for k, v in kpi_res.items()]
            res_df = pd.DataFrame(rows)
            exp = f"Calculated operational KPIs for {len(filtered):,} matching manufacturing records."

        return res_df, "table", None, exp

    # 2. TOP_N Function
    elif fn_name == "top_n":
        dim = args.get("dimension", "defect")
        metric = args.get("metric", "rejected")
        n = int(args.get("n", 5))

        if dim not in filtered.columns:
            dim = "defect"
        if metric not in filtered.columns:
            metric = "rejected"

        # Exclude 'None' defect
        sub = filtered[filtered[dim] != "None"] if dim == "defect" else filtered
        grouped = sub.groupby(dim)[metric].sum().reset_index().sort_values(metric, ascending=False).head(n)
        tot = sub[metric].sum()
        grouped["share_%"] = (100.0 * grouped[metric] / max(1.0, tot)).round(1)

        fig = px.bar(
            grouped, x=dim, y=metric, color=metric,
            title=f"Top {n} {dim.title()}s by {metric.replace('_', ' ').title()}",
            color_continuous_scale="Reds" if metric == "rejected" else "Blues"
        )
        fig.update_layout(margin=dict(t=40, b=10))
        exp = f"Identified Top {len(grouped)} {dim}s ranked by total {metric}."
        return grouped, "bar", fig, exp

    # 3. TREND Function
    elif fn_name == "trend":
        metric = args.get("metric", "rejection_%")
        dim = args.get("dimension", "date")

        daily = filtered.groupby(dim).agg(
            produced=("produced", "sum"),
            rejected=("rejected", "sum"),
        ).reset_index()
        daily["rejection_%"] = (100.0 * daily["rejected"] / daily["produced"]).round(2)
        daily = daily.sort_values(dim).reset_index(drop=True)

        target_col = metric if metric in daily.columns else "rejection_%"
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=daily[dim], y=daily[target_col], mode="lines+markers", name=target_col.title(), line=dict(color="#1F3A5F", width=2.5)))
        if target_col == "rejection_%":
            fig.add_hline(y=config.REJECTION_TARGET, line_dash="dash", line_color="gray", annotation_text=f"Target ({config.REJECTION_TARGET}%)")
        fig.update_layout(title=f"Trend for {target_col.replace('_', ' ').title()} over {dim.title()}", margin=dict(t=40, b=10))

        exp = f"Computed time-series trend of {target_col} across {len(daily)} intervals."
        return daily, "line", fig, exp

    # 4. COMPARE Function
    elif fn_name == "compare":
        dim = args.get("dimension", "department")
        metric = args.get("metric", "rejection_%")

        if dim not in filtered.columns:
            dim = "department"

        grouped = filtered.groupby(dim).agg(
            produced=("produced", "sum"),
            rejected=("rejected", "sum"),
            scrap=("scrap", "sum") if "scrap" in filtered.columns else ("rejected", "sum"),
            rework=("rework", "sum") if "rework" in filtered.columns else ("rejected", lambda x: 0),
        ).reset_index()
        grouped["rejection_%"] = (100.0 * grouped["rejected"] / grouped["produced"]).round(2)
        grouped = grouped.sort_values(metric if metric in grouped.columns else "rejection_%", ascending=False).reset_index(drop=True)

        target_col = metric if metric in grouped.columns else "rejection_%"
        fig = px.bar(grouped, x=dim, y=target_col, color=dim, title=f"Comparison across {dim.title()} by {target_col}")
        fig.update_layout(margin=dict(t=40, b=10), showlegend=False)

        exp = f"Compared {target_col} performance across {len(grouped)} distinct {dim}s."
        return grouped, "bar", fig, exp

    # 5. FILTER Function
    else:
        disp_cols = [c for c in ["date", "department", "machine", "product", "shift", "produced", "rejected", "scrap", "rework", "defect", "heat_no"] if c in filtered.columns]
        sample_res = filtered[disp_cols].head(50).reset_index(drop=True)
        exp = f"Filtered {len(filtered):,} records matching specified parameters. Showing first 50 rows."
        return sample_res, "table", None, exp


# ==============================================================================
# 2. INTENT CLASSIFICATION & PARSER (AI + RULE-BASED FALLBACK)
# ==============================================================================

def parse_query_rule_based(query: str) -> Tuple[str, Dict[str, Any]]:
    """
    Offline deterministic rule-based natural language intent parser.
    Extracts analytics function, dimensions, metrics, and entity filters.
    """
    q = query.lower().strip()

    filters: Dict[str, Any] = {}

    # Department detection
    if "foundry" in q:
        filters["department"] = "Foundry"
    elif "machine shop" in q or "machining" in q:
        filters["department"] = "Machine Shop"

    # Machine detection
    for dept_m in MACHINES.values():
        for m in dept_m:
            if m.lower() in q:
                filters["machine"] = m
                break

    # Shift detection
    if "shift a" in q:
        filters["shift"] = "A"
    elif "shift b" in q:
        filters["shift"] = "B"
    elif "shift c" in q:
        filters["shift"] = "C"

    # Product detection
    for prods in PRODUCTS.values():
        for p in prods:
            if p.lower() in q:
                filters["product"] = p
                break

    # Defect detection
    for defs in DEFECTS.values():
        for d in defs:
            if d.lower() in q:
                filters["defect"] = d
                break

    # Extract limit N if specified (e.g. "top 3", "top 5")
    n_match = re.search(r"top\s*(\d+)", q)
    n = int(n_match.group(1)) if n_match else 5

    # Intent Classification
    if any(k in q for k in ["top", "highest", "most", "worst", "lowest"]):
        fn = "top_n"
        dim = "defect"
        if "machine" in q:
            dim = "machine"
        elif "product" in q or "part" in q:
            dim = "product"
        elif "customer" in q:
            dim = "customer"

        metric = "rejected"
        if "scrap" in q:
            metric = "scrap"
        elif "produced" in q or "volume" in q or "production" in q:
            metric = "produced"
        elif "cost" in q or "loss" in q:
            metric = "total_copq_inr"

        return fn, {"dimension": dim, "metric": metric, "n": n, "filters": filters}

    elif any(k in q for k in ["trend", "history", "daily", "over time", "trajectory"]):
        fn = "trend"
        metric = "produced" if ("volume" in q or "production" in q) else "rejection_%"
        return fn, {"metric": metric, "dimension": "date", "filters": filters}

    elif any(k in q for k in ["compare", "versus", "vs", "difference", "between"]):
        fn = "compare"
        dim = "department"
        if "shift" in q:
            dim = "shift"
        elif "machine" in q:
            dim = "machine"
        elif "product" in q:
            dim = "product"
        metric = "produced" if ("volume" in q or "production" in q) else "rejection_%"
        return fn, {"dimension": dim, "metric": metric, "filters": filters}

    elif any(k in q for k in ["kpi", "oee", "ppm", "yield", "rate", "fpy", "summary", "how many"]):
        fn = "kpi"
        metric = None
        if "oee" in q:
            metric = "OEE %"
        elif "ppm" in q:
            metric = "PPM"
        elif "yield" in q or "fpy" in q:
            metric = "First-Pass Yield %"
        elif "rejection" in q:
            metric = "Rejection %"
        elif "scrap" in q:
            metric = "Scrap"
        elif "rework" in q:
            metric = "Rework"
        return fn, {"metric": metric, "filters": filters}

    else:
        return "filter", {"filters": filters}


def ask_your_data(
    df: pd.DataFrame,
    query: str,
) -> Dict[str, Any]:
    """
    Main entry point for 'Ask your data'.
    Parses natural language prompt using Anthropic API (if key configured)
    or robust rule-based parser, strictly validating against whitelisted operations.
    """
    api_key = config.ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY")
    fn_name, args = None, None

    # 1. Optional Anthropic API Attempt
    if api_key:
        try:
            prompt = f"""
You are a manufacturing BI data agent. Map the user query to one of these whitelisted functions:
- top_n (arguments: dimension, metric, n, filters)
- trend (arguments: metric, dimension, filters)
- compare (arguments: dimension, metric, filters)
- filter (arguments: filters)
- kpi (arguments: metric, filters)

Valid dimensions: [department, machine, product, shift, defect, customer]
Valid metrics: [produced, rejected, rejection_%, scrap, rework, OEE %, PPM]
Valid filter keys: [department, machine, product, shift, defect]

User Query: "{query}"

Output ONLY a raw JSON dictionary without code fences or formatting:
{{"function": "top_n|trend|compare|filter|kpi", "arguments": {{...}}}}
"""
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 200,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                raw_text = data["content"][0]["text"].strip()
                parsed = json.loads(raw_text)
                if parsed.get("function") in WHITELISTED_FUNCTIONS:
                    fn_name = parsed["function"]
                    args = parsed.get("arguments", {})
        except Exception as e:
            log.warning("Anthropic API query failed (%s); falling back to rule-based parser.", e)

    # 2. Rule-Based Fallback
    if not fn_name or fn_name not in WHITELISTED_FUNCTIONS:
        fn_name, args = parse_query_rule_based(query)

    # Execute whitelisted plan
    res_df, chart_type, fig, explanation = execute_whitelisted_query(df, fn_name, args)

    return {
        "query": query,
        "function_called": fn_name,
        "filters_used": args.get("filters", {}),
        "arguments": args,
        "explanation": explanation,
        "result_table": res_df,
        "chart_type": chart_type,
        "chart_figure": fig,
    }
