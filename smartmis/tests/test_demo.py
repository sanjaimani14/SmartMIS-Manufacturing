"""
Automated unit tests for SmartMIS Demo Readiness, Streaming, ROI, and Requirement Mapping.
"""
from datetime import date
import pandas as pd
import pytest

import demo
from data import sample_pms, CANONICAL_COLUMNS


@pytest.fixture
def sample_df():
    return sample_pms(days=30, seed=42)


def test_streaming_batch():
    """Verify live streaming batch produces valid canonical schema records."""
    batch = demo.generate_streaming_batch(base_date=date.today(), n_records=8, random_seed=123)
    assert len(batch) == 8
    for col in CANONICAL_COLUMNS:
        assert col in batch.columns
    assert (batch["produced"] >= 0).all()
    assert (batch["rejected"] >= 0).all()
    assert (batch["good"] == batch["produced"] - batch["rejected"]).all()


def test_inject_defect_spike(sample_df):
    """Verify defect spike injection increases rejection rate and returns critical alert."""
    initial_len = len(sample_df)
    initial_rej_pct = (sample_df["rejected"].sum() / sample_df["produced"].sum()) * 100

    updated_df, alert_meta = demo.inject_defect_spike(
        sample_df, spike_type="blowhole_furnace2", n_records=10
    )

    assert len(updated_df) == initial_len + 10
    assert alert_meta["severity"] == "CRITICAL"
    assert alert_meta["machine"] == "Furnace-2"
    assert alert_meta["defect"] == "Blow Hole"
    assert alert_meta["batch_rejection_pct"] > 25.0
    assert alert_meta["post_rejection_pct"] > alert_meta["pre_rejection_pct"]
    assert "recommended_action" in alert_meta


def test_inject_tool_offset_spike(sample_df):
    """Verify tool offset spike on CNC-02 Machine Shop."""
    updated_df, alert_meta = demo.inject_defect_spike(
        sample_df, spike_type="tool_offset_cnc2", n_records=8
    )
    assert alert_meta["department"] == "Machine Shop"
    assert alert_meta["machine"] == "CNC-02"
    assert alert_meta["defect"] == "Tool Offset / Dimension Deviation"


def test_time_saved_roi_calculation():
    """Verify engineering time saved and financial ROI calculation."""
    roi = demo.compute_time_saved_roi()

    assert roi["hourly_rate_inr"] == 600.0
    assert roi["total_manual_hours_monthly"] > 50.0
    assert roi["total_auto_hours_monthly"] < 2.0
    assert roi["overall_efficiency_pct"] > 98.0
    assert roi["annual_hours_saved"] > 600.0
    assert roi["annual_savings_inr"] > 300_000.0
    assert len(roi["breakdown"]) >= 5


def test_requirement_checklist_mapping():
    """Verify all 17 hackathon requirements are mapped with verification tests."""
    checklist = demo.get_requirement_checklist()
    assert len(checklist) >= 17

    req_ids = [r["req_id"] for r in checklist]
    assert "REQ-01" in req_ids
    assert "REQ-07" in req_ids
    assert "REQ-16" in req_ids

    for req in checklist:
        assert req["status"].startswith("✅")
        assert len(req["feature_implemented"]) > 10
        assert len(req["verification"]) > 5
