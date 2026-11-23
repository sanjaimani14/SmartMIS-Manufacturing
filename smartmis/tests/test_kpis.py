import os
import sys
import tempfile
from datetime import date, timedelta
import numpy as np
import pandas as pd
import pytest

# Ensure smartmis directory is on path
SMARTMIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SMARTMIS_DIR not in sys.path:
    sys.path.insert(0, SMARTMIS_DIR)

import data
import kpis


@pytest.fixture(scope="module")
def sample_df():
    return data.sample_pms(days=60, seed=55)


def test_compute_advanced_kpis(sample_df):
    """Verify calculation and invariants of all manufacturing KPIs including OEE."""
    res = kpis.compute_advanced_kpis(sample_df)

    # Core metrics
    assert "OEE %" in res
    assert "First-Pass Yield %" in res
    assert "Rejection %" in res
    assert "Scrap %" in res
    assert "Rework %" in res
    assert "PPM" in res
    assert "Downtime %" in res
    assert "Plan Adherence %" in res

    # Value ranges
    assert 0.0 <= res["OEE %"] <= 100.0
    assert 0.0 <= res["Availability %"] <= 100.0
    assert 0.0 <= res["Performance %"] <= 105.0
    assert 0.0 <= res["Quality %"] <= 100.0
    assert 0.0 <= res["First-Pass Yield %"] <= 100.0
    assert res["PPM"] >= 0
    assert res["Scrap"] + res["Rework"] == res["Rejected"]
    assert round(res["Scrap %"] + res["Rework %"], 1) == round(res["Rejection %"], 1)


def test_copq_calculation_and_top_drivers(sample_df, tmp_path):
    """Verify Cost of Poor Quality (COPQ) in INR and Top 5 cost drivers."""
    cost_file = str(tmp_path / "custom_copq.json")
    test_costs = {
        "Brake Drum": {"scrap": 1000.0, "rework": 300.0},
        "Hub Housing": {"scrap": 1500.0, "rework": 400.0},
    }
    kpis.save_copq_costs(test_costs, filepath=cost_file)
    loaded_costs = kpis.load_copq_costs(filepath=cost_file)
    assert "Brake Drum" in loaded_costs

    copq_res = kpis.compute_copq(sample_df, cost_table=loaded_costs)
    assert copq_res["total_copq"] > 0
    assert copq_res["total_copq"] == pytest.approx(copq_res["total_scrap_cost"] + copq_res["total_rework_cost"])

    # Top drivers
    assert not copq_res["top_products"].empty
    assert len(copq_res["top_products"]) <= 5
    assert not copq_res["top_defects"].empty
    assert len(copq_res["top_defects"]) <= 5


def test_spc_p_chart_limits_and_rules(sample_df):
    """Verify statistical process control limits and rule violation detection."""
    spc_df, alarms = kpis.compute_spc_p_chart(sample_df, group_col="date")

    assert not spc_df.empty
    assert "cl_pct" in spc_df.columns
    assert "ucl_pct" in spc_df.columns
    assert "lcl_pct" in spc_df.columns

    # Statistical limits invariants: LCL <= CL <= UCL
    assert (spc_df["ucl_pct"] >= spc_df["cl_pct"]).all()
    assert (spc_df["cl_pct"] >= spc_df["lcl_pct"]).all()
    assert (spc_df["lcl_pct"] >= 0.0).all()

    # Test Rule 1: Point beyond UCL
    outlier_df = sample_df.copy()
    # Inject massive defect spike on day 0
    day0 = outlier_df["date"].min()
    mask = outlier_df["date"] == day0
    outlier_df.loc[mask, "rejected"] = outlier_df.loc[mask, "produced"] - 2

    spc_out, alarms_out = kpis.compute_spc_p_chart(outlier_df, group_col="date")
    rule1_alarms = [a for a in alarms_out if "Rule 1" in a["rule"]]
    assert len(rule1_alarms) > 0


def test_anomaly_detection_z_score(sample_df):
    """Verify robust rolling median and MAD z-score anomaly detector."""
    daily, alerts = kpis.detect_anomalies(sample_df)

    assert not daily.empty
    assert "z_score" in daily.columns
    assert "severity" in daily.columns

    # Test spike anomaly injection
    spiked_df = sample_df.copy()
    target_dt = spiked_df["date"].max()
    spiked_df.loc[spiked_df["date"] == target_dt, "rejected"] = 120

    _, spiked_alerts = kpis.detect_anomalies(spiked_df)
    crit_alerts = [a for a in spiked_alerts if a["severity"] == "CRITICAL"]
    assert len(crit_alerts) > 0
    assert "Immediate containment" in crit_alerts[0]["action"]


def test_statsmodels_14_day_forecasting(sample_df):
    """Verify statsmodels Holt-Winters 14-day projection with 95% confidence bounds."""
    fc_map = kpis.forecast_production_and_rejection(sample_df, horizon_days=14)

    assert "rejection_%" in fc_map
    assert "produced" in fc_map

    rej_fc = fc_map["rejection_%"]
    future_rows = rej_fc.dropna(subset=["forecast"])
    assert len(future_rows) == 14

    # Confidence interval invariant: lower_95 <= forecast <= upper_95
    assert (future_rows["lower_95"] <= future_rows["forecast"] + 1e-4).all()
    assert (future_rows["forecast"] <= future_rows["upper_95"] + 1e-4).all()
    assert (future_rows["lower_95"] >= 0.0).all()


def test_multi_level_drill_down(sample_df):
    """Verify hierarchical cascading drill-down (Dept > Machine > Shift > Defect)."""
    # Level 1: Department
    d_res = kpis.drill_down_level(sample_df, level="department")
    assert len(d_res) == 2
    assert set(d_res["department"].unique()) == {"Foundry", "Machine Shop"}

    # Level 2: Machine in Foundry
    m_res = kpis.drill_down_level(sample_df, level="machine", filter_dept="Foundry")
    assert len(m_res) == 4

    # Level 3: Shift on Furnace-1
    s_res = kpis.drill_down_level(sample_df, level="shift", filter_dept="Foundry", filter_mach="Furnace-1")
    assert len(s_res) == 3

    # Level 4: Defect on Shift A
    def_res = kpis.drill_down_level(sample_df, level="defect", filter_dept="Foundry", filter_mach="Furnace-1", filter_shift="A")
    assert not def_res.empty
    assert "Blow Hole" in def_res["defect"].values or len(def_res) > 0
