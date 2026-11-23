import os
import sys
import tempfile
import pandas as pd
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient

# Ensure smartmis directory is on path
SMARTMIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SMARTMIS_DIR not in sys.path:
    sys.path.insert(0, SMARTMIS_DIR)

import data
from mock_pms.server import app as fastapi_app


@pytest.fixture
def sim_df():
    return data.sample_pms(days=60, seed=42, degrade_machine="CNC-02")


def test_simulator_schema_and_integrity(sim_df):
    """Verify realistic simulator outputs all legacy and advanced columns with valid invariants."""
    required = [
        "date", "department", "machine", "product", "shift",
        "planned_qty", "produced", "rejected", "scrap", "rework", "good",
        "defect", "defect_category", "customer", "heat_no", "pattern_id",
        "downtime_minutes", "downtime_reason", "humidity", "temperature"
    ]
    for col in required:
        assert col in sim_df.columns, f"Missing expected column: {col}"

    # Invariants
    assert (sim_df["good"] == sim_df["produced"] - sim_df["rejected"]).all()
    assert (sim_df["scrap"] + sim_df["rework"] == sim_df["rejected"]).all()
    assert set(sim_df["shift"].unique()).issubset({"A", "B", "C"})
    assert set(sim_df["department"].unique()) == {"Foundry", "Machine Shop"}

    # Foundry heat numbers
    foundry_heats = sim_df[sim_df["department"] == "Foundry"]["heat_no"]
    assert (foundry_heats.str.startswith("H")).all()


def test_simulator_seasonal_humidity_effect(sim_df):
    """Verify that high humidity significantly elevates Blow Hole porosity in Foundry."""
    foundry = sim_df[(sim_df["department"] == "Foundry") & (sim_df["rejected"] > 0)]
    high_hum = foundry[foundry["humidity"] >= 70.0]
    norm_hum = foundry[foundry["humidity"] < 70.0]

    assert len(high_hum) > 0 and len(norm_hum) > 0
    high_hum_blow_hole_rate = (high_hum["defect"] == "Blow Hole").mean()
    norm_hum_blow_hole_rate = (norm_hum["defect"] == "Blow Hole").mean()

    # Blow holes should be noticeably higher during humid conditions
    assert high_hum_blow_hole_rate > norm_hum_blow_hole_rate


def test_simulator_machine_degradation(sim_df):
    """Verify that CNC-02 degrades over time, displaying higher rejection rates."""
    cnc = sim_df[sim_df["machine"] == "CNC-02"].sort_values("date")
    half = len(cnc) // 2
    first_half_rate = cnc.iloc[:half]["rejected"].sum() / cnc.iloc[:half]["produced"].sum()
    second_half_rate = cnc.iloc[half:]["rejected"].sum() / cnc.iloc[half:]["produced"].sum()

    assert second_half_rate > first_half_rate, f"Expected degradation: {second_half_rate:.3f} > {first_half_rate:.3f}"


def test_clean_backwards_compatibility():
    """Verify clean() handles a bare-bones legacy 7-column PMS dataframe."""
    legacy = pd.DataFrame({
        "date": ["2026-03-01", "2026-03-02"],
        "department": ["Foundry", "Machine Shop"],
        "machine": ["Furnace-1", "CNC-01"],
        "product": ["Brake Drum", "Hub Housing"],
        "produced": [150, 200],
        "rejected": [6, 4],
        "defect": ["Blow Hole", "Tool Mark"]
    })
    cleaned = data.clean(legacy)
    assert "good" in cleaned.columns
    assert "shift" in cleaned.columns
    assert "planned_qty" in cleaned.columns
    assert "scrap" in cleaned.columns
    assert "rework" in cleaned.columns
    assert cleaned["good"].tolist() == [144, 196]


def test_quality_issues_detection():
    """Verify quality_issues identifies missing columns, negative numbers, and anomalies."""
    bad_df = pd.DataFrame({
        "date": ["2026-01-01"],
        "department": ["Foundry"],
        "machine": ["F1"],
        "product": ["A"],
        "produced": [50],
        "rejected": [60],  # rejected > produced
        "defect": ["Blow Hole"]
    })
    issues = data.quality_issues(bad_df)
    messages = " ".join(msg for _, msg in issues)
    assert "rejected > produced" in messages


def test_column_mapping_heuristics():
    """Verify auto_map_columns and apply_column_mapping on foreign ERP exports."""
    foreign_cols = [
        "Txn_Date", "Cost_Center", "Asset_ID", "Part_Name",
        "Actual_Qty", "Total_Rejected", "Failure_Mode", "Work_Shift"
    ]
    mapping = data.auto_map_columns(foreign_cols)
    assert mapping.get("date") == "Txn_Date"
    assert mapping.get("department") == "Cost_Center"
    assert mapping.get("machine") == "Asset_ID"
    assert mapping.get("product") == "Part_Name"
    assert mapping.get("produced") == "Actual_Qty"
    assert mapping.get("rejected") == "Total_Rejected"
    assert mapping.get("defect") == "Failure_Mode"
    assert mapping.get("shift") == "Work_Shift"

    foreign_df = pd.DataFrame({
        "Txn_Date": ["2026-04-01"],
        "Cost_Center": ["Foundry"],
        "Asset_ID": ["Furnace-1"],
        "Part_Name": ["Brake Drum"],
        "Actual_Qty": [120],
        "Total_Rejected": [3],
        "Failure_Mode": ["Cold Shut"],
        "Work_Shift": ["B"]
    })
    mapped = data.apply_column_mapping(foreign_df, mapping)
    cleaned = data.clean(mapped)
    assert "produced" in cleaned.columns
    assert cleaned["produced"].iloc[0] == 120


def test_preset_persistence(tmp_path):
    """Verify saving and loading custom column mapping presets."""
    preset_file = str(tmp_path / "test_presets.json")
    custom_map = {"date": "MyDateCol", "produced": "MyProdCol"}
    data.save_mapping_preset("CustomLineAlpha", custom_map, filepath=preset_file)

    loaded = data.load_mapping_presets(filepath=preset_file)
    assert "CustomLineAlpha" in loaded
    assert loaded["CustomLineAlpha"] == custom_map


def test_incremental_load_idempotency(tmp_path):
    """Verify incremental load only adds new records and ignores existing ones."""
    test_db = str(tmp_path / "test_central.db")
    df = data.sample_pms(days=10, seed=99)

    # First load: all records inserted
    res1 = data.incremental_load(df, source_type="Test Batch", source_name="run1", db_path=test_db)
    assert res1["inserted"] == len(df)
    assert res1["skipped"] == 0

    # Second load with identical data: 0 inserted, all skipped
    res2 = data.incremental_load(df, source_type="Test Batch", source_name="run2", db_path=test_db)
    assert res2["inserted"] == 0
    assert res2["skipped"] == len(df)

    # Verify central table count
    loaded_df = data.load_sqlite(test_db)
    assert len(loaded_df) == len(df)

    # Ingestion log has both audit entries
    log_df = data.get_ingestion_log(test_db)
    assert len(log_df) == 2


def test_sql_connector(tmp_path):
    """Verify seeding and fetching from an external SQL database via SQLAlchemy."""
    mock_db = str(tmp_path / "test_external.db")
    data.seed_mock_sql_db(mock_db)

    uri = f"sqlite:///{mock_db}"
    ok, tables = data.test_sql_connection(uri)
    assert ok is True
    assert "pms_production_records" in tables

    fetched = data.fetch_sql(uri, "pms_production_records")
    assert len(fetched) > 0
    assert "produced" in fetched.columns


def test_fastapi_mock_pms_client():
    """Verify FastAPI mock PMS endpoints using TestClient."""
    client = TestClient(fastapi_app)

    # Health check
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "online"

    # Fetch records
    resp = client.get("/api/pms/records?limit=50")
    assert resp.status_code == 200
    data_json = resp.json()
    assert "records" in data_json
    assert len(data_json["records"]) == 50

    # Fetch machine telemetry
    resp = client.get("/api/pms/machines")
    assert resp.status_code == 200
    assert len(resp.json()["machines"]) == 8

    # Create new record
    new_rec = {
        "date": "2026-05-01",
        "department": "Foundry",
        "machine": "Furnace-1",
        "product": "Brake Drum",
        "shift": "A",
        "planned_qty": 200,
        "produced": 190,
        "rejected": 5,
        "defect": "Blow Hole",
        "customer": "Brembo",
    }
    resp = client.post("/api/pms/record", json=new_rec)
    assert resp.status_code == 201

    # Simulate shift
    resp = client.post("/api/pms/simulate-shift")
    assert resp.status_code == 200
    assert resp.json()["added_records"] == 8
