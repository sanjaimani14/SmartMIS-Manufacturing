"""Data layer for SmartMIS: realistic simulator, PMS connectors, column mapping, and incremental loading."""
import io
import json
import logging
import math
import os
import sqlite3
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import sqlalchemy as sa
from sqlalchemy import text

try:
    import config
except ImportError:
    from . import config

log = logging.getLogger("smartmis.data")

# Core domain definitions
PRODUCTS = {
    "Foundry": ["Brake Drum", "Hub Housing", "Pump Casing", "Flywheel"],
    "Machine Shop": ["Brake Drum", "Hub Housing", "Pump Casing", "Gear Blank"],
}

MACHINES = {
    "Foundry": ["Furnace-1", "Furnace-2", "Moulding-A", "Moulding-B"],
    "Machine Shop": ["CNC-01", "CNC-02", "VMC-01", "Lathe-01"],
}

DEFECTS = {
    "Foundry": ["Blow Hole", "Shrinkage", "Sand Inclusion", "Cold Shut"],
    "Machine Shop": ["Oversize", "Undersize", "Surface Finish", "Tool Mark"],
}

DEFECT_CATEGORIES = {
    "Blow Hole": "Gas Porosity",
    "Shrinkage": "Solidification Defect",
    "Sand Inclusion": "Moulding Defect",
    "Cold Shut": "Pouring Defect",
    "Oversize": "Dimensional Defect",
    "Undersize": "Dimensional Defect",
    "Surface Finish": "Tooling & Surface",
    "Tool Mark": "Tooling & Surface",
    "None": "None",
}

CUSTOMERS = ["Brembo", "Mahindra", "Tata Motors", "BOSCH", "TVS Motor", "Dana"]

PATTERN_MAP = {
    "Brake Drum": "PAT-BD-01",
    "Hub Housing": "PAT-HH-02",
    "Pump Casing": "PAT-PC-01",
    "Flywheel": "PAT-FW-03",
    "Gear Blank": "PAT-GB-01",
}

DOWNTIME_REASONS = [
    "Tool Change",
    "Electrical Breakdown",
    "Mechanical Jam",
    "Power Dip",
    "Preventive Maintenance",
    "Waiting for Material",
]

SHIFTS = ["A", "B", "C"]

CANONICAL_COLUMNS: Dict[str, List[str]] = {
    "date": ["date", "production_date", "prod_date", "txn_date", "posting_date", "work_date", "timestamp"],
    "department": ["department", "dept", "shop", "shop_floor", "cost_center", "unit", "line"],
    "machine": ["machine", "machine_name", "equipment", "asset", "station", "work_center", "mach_id"],
    "product": ["product", "part_name", "component", "item", "material", "part_number", "item_desc"],
    "produced": ["produced", "actual_qty", "qty_produced", "output", "production_qty", "good_and_rejected", "actual"],
    "rejected": ["rejected", "rej_qty", "total_rejected", "rejection_qty", "scrap_and_rework", "defect_qty", "non_conforming"],
    "defect": ["defect", "defect_type", "rejection_reason", "failure_mode", "defect_description", "reason"],
    "shift": ["shift", "shift_name", "shift_code", "work_shift"],
    "planned_qty": ["planned_qty", "plan_qty", "target_qty", "scheduled_qty", "budget_qty", "target"],
    "scrap": ["scrap", "scrap_qty", "unrecoverable_scrap", "melt_loss"],
    "rework": ["rework", "rework_qty", "rectification", "reworkable"],
    "customer": ["customer", "client", "oem", "account", "buyer"],
    "heat_no": ["heat_no", "heat_number", "melt_no", "batch_no", "lot_number", "charge_no"],
    "pattern_id": ["pattern_id", "pattern_no", "tooling_id", "die_no", "fixture_id"],
    "downtime_minutes": ["downtime_minutes", "downtime", "idle_time_mins", "lost_time_mins", "breakdown_min"],
    "downtime_reason": ["downtime_reason", "stoppage_reason", "delay_reason", "idle_reason", "stoppage_type"],
}

DEFAULT_PRESETS: Dict[str, Dict[str, str]] = {
    "Standard SmartMIS": {c: c for c in CANONICAL_COLUMNS},
    "SAP PP Export": {
        "posting_date": "date",
        "cost_center": "department",
        "work_center": "machine",
        "material": "product",
        "actual": "produced",
        "target": "planned_qty",
        "scrap_and_rework": "rejected",
        "failure_mode": "defect",
        "work_shift": "shift",
    },
    "MES Shopfloor Log": {
        "work_date": "date",
        "unit": "department",
        "mach_id": "machine",
        "part_name": "product",
        "qty_produced": "produced",
        "rej_qty": "rejected",
        "defect_description": "defect",
        "shift_code": "shift",
        "stoppage_type": "downtime_reason",
        "lost_time_mins": "downtime_minutes",
    },
}


# ==============================================================================
# 1. REALISTIC SIMULATOR
# ==============================================================================

def sample_pms(
    days: int = 90,
    seed: int = 42,
    degrade_machine: str = "CNC-02",
    end_date: Optional[date] = None,
) -> pd.DataFrame:
    """
    Realistic manufacturing PMS simulator for Foundry and Machine Shop operations.

    Features:
    - Full shift schedules: Shifts A, B, and C with realistic diurnal variation.
    - Heat numbers for Foundry melting batches and pattern tooling IDs.
    - Planned vs actual production quantities accounting for speed loss.
    - Downtime tracking (minutes + root cause reasons).
    - Granular rejection breakdown: Scrap (unrecoverable) vs Rework (rectifiable).
    - OEM Customer allocation (Brembo, Mahindra, Tata, BOSCH, etc.).
    - Defect hierarchy (defect and standardized defect_category).
    - Environmental seasonal effect: Humid days trigger heightened blow hole porosity in Foundry.
    - Wear degradation: Degrades target machine (default: CNC-02) showing increasing scrap & tool mark drift.
    - Preserves all legacy columns: date, department, machine, product, produced, rejected, defect, shift, good.
    """
    rng = np.random.default_rng(seed)
    end_dt = end_date or date.today()
    start_dt = end_dt - timedelta(days=days - 1)

    rows: List[Dict[str, Any]] = []

    for d in range(days):
        current_date = start_dt + timedelta(days=d)
        day_of_year = current_date.timetuple().tm_yday

        # Seasonal environmental simulation:
        # Humid wave in monsoon season (approx day 170 to 280) + cyclical local variance
        base_humidity = 52.0 + 26.0 * math.sin((day_of_year - 140) * 2 * math.pi / 365)
        humidity = round(float(np.clip(base_humidity + rng.normal(0, 7.5), 32.0, 95.0)), 1)
        temp_c = round(float(np.clip(33.0 - 0.15 * (humidity - 50) + rng.normal(0, 3), 20.0, 43.0)), 1)

        # Humidity effect: High humidity significantly increases blow hole defects in green sand foundry moulds
        is_high_humidity = humidity >= 70.0

        # One machine degradation factor: e.g. CNC-02 tool wear and spindle bearing runout
        degradation_progress = d / max(1, days - 1)
        # Degradation kicks in moderately then accelerates toward the end of the window
        degradation_factor = 1.0 + 3.2 * (degradation_progress ** 1.8)

        # Generate batch records per department, machine, and shift
        for dept in ["Foundry", "Machine Shop"]:
            # Daily melt batch for Foundry
            heat_no = f"H{current_date.strftime('%y%m')}-{d % 28 + 101:03d}" if dept == "Foundry" else "N/A"

            for mach in MACHINES[dept]:
                is_degrading = (mach == degrade_machine)

                for shift in SHIFTS:
                    # Select product and tooling pattern
                    product = rng.choice(PRODUCTS[dept])
                    pattern_id = PATTERN_MAP.get(product, "PAT-GEN-01")
                    customer = rng.choice(CUSTOMERS)

                    # Planned quantity based on shift capacity (8 hours standard target)
                    planned_qty = int(rng.integers(140, 220))

                    # Downtime simulation
                    has_downtime = rng.random() < (0.45 if is_degrading else 0.22)
                    if has_downtime:
                        if is_degrading and rng.random() < 0.65:
                            downtime_reason = rng.choice(["Tool Change", "Mechanical Jam"])
                            downtime_minutes = int(rng.integers(30, 95))
                        else:
                            downtime_reason = rng.choice(DOWNTIME_REASONS)
                            downtime_minutes = int(rng.integers(10, 65))
                    else:
                        downtime_reason = "None"
                        downtime_minutes = 0

                    # Production quantity loss from downtime + small operational variance
                    loss_factor = max(0.40, 1.0 - (downtime_minutes / 480.0))
                    efficiency = rng.uniform(0.88, 1.02)
                    produced = int(np.clip(planned_qty * loss_factor * efficiency, 30, planned_qty + 15))

                    # Base rejection rate
                    if dept == "Foundry":
                        base_rej_rate = rng.uniform(0.015, 0.055)
                        # Shift C (night shift) slight fatigue adjustment
                        if shift == "C":
                            base_rej_rate *= 1.15
                    else:
                        base_rej_rate = rng.uniform(0.012, 0.040)
                        if shift == "C":
                            base_rej_rate *= 1.10

                    # Apply machine degradation if applicable
                    if is_degrading:
                        base_rej_rate *= degradation_factor

                    # Compute total rejected count
                    rejected = int(np.clip(round(produced * base_rej_rate), 0, produced))

                    # Defect selection and scrap vs rework breakdown
                    if rejected > 0:
                        if dept == "Foundry":
                            # Foundry defects: High humidity boosts Blow Hole defects
                            if is_high_humidity:
                                defect_weights = [0.65, 0.15, 0.12, 0.08]  # Blow Hole heavily favored
                            else:
                                defect_weights = [0.25, 0.30, 0.25, 0.20]
                            defect = rng.choice(DEFECTS["Foundry"], p=defect_weights)
                            defect_cat = DEFECT_CATEGORIES[defect]

                            # Cast iron scrap is mostly non-rectifiable (melt-back scrap)
                            scrap_ratio = rng.uniform(0.70, 0.95)
                            scrap = int(round(rejected * scrap_ratio))
                            scrap = min(rejected, max(1, scrap))
                            rework = rejected - scrap
                        else:
                            # Machine Shop defects
                            if is_degrading:
                                # Tool wear produces heavy Tool Marks and Oversize/Undersize
                                defect_weights = [0.25, 0.25, 0.10, 0.40]  # Tool Mark favored
                            else:
                                defect_weights = [0.28, 0.28, 0.24, 0.20]
                            defect = rng.choice(DEFECTS["Machine Shop"], p=defect_weights)
                            defect_cat = DEFECT_CATEGORIES[defect]

                            # Machined parts can often be reworked (re-turned/ground/polished)
                            rework_ratio = rng.uniform(0.40, 0.70)
                            rework = int(round(rejected * rework_ratio))
                            rework = min(rejected, max(0, rework))
                            scrap = rejected - rework
                    else:
                        defect = "None"
                        defect_cat = "None"
                        scrap = 0
                        rework = 0

                    rows.append({
                        "date": current_date,
                        "department": dept,
                        "machine": mach,
                        "product": product,
                        "shift": shift,
                        "planned_qty": planned_qty,
                        "produced": produced,
                        "rejected": rejected,
                        "scrap": scrap,
                        "rework": rework,
                        "good": produced - rejected,
                        "defect": defect,
                        "defect_category": defect_cat,
                        "customer": customer,
                        "heat_no": heat_no,
                        "pattern_id": pattern_id,
                        "downtime_minutes": downtime_minutes,
                        "downtime_reason": downtime_reason,
                        "humidity": humidity,
                        "temperature": temp_c,
                    })

    df = pd.DataFrame(rows)
    return clean(df)


# ==============================================================================
# 2. ETL CLEANING & DATA QUALITY
# ==============================================================================

def clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize column names, validate types, and derive missing manufacturing fields.
    Guarantees compatibility with both legacy 7-column formats and full rich PMS datasets.
    """
    d = df.copy()
    d.columns = [str(c).strip().lower() for c in d.columns]

    need = {"date", "department", "machine", "product", "produced", "rejected", "defect"}
    missing = need - set(d.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    # Standardize date
    d["date"] = pd.to_datetime(d["date"]).dt.date

    # Drop invalid rows and duplicates
    d = d.dropna(subset=["produced"]).drop_duplicates()

    # Numeric safeguards
    d["produced"] = pd.to_numeric(d["produced"], errors="coerce").fillna(0).astype(int)
    d["rejected"] = pd.to_numeric(d["rejected"], errors="coerce").fillna(0).clip(lower=0).astype(int)

    # Derived good production
    d["good"] = (d["produced"] - d["rejected"]).clip(lower=0)

    # Optional fields with sensible defaults if missing
    if "shift" not in d.columns:
        d["shift"] = "A"
    else:
        d["shift"] = d["shift"].fillna("A").astype(str).str.strip().str.upper()

    if "planned_qty" not in d.columns:
        d["planned_qty"] = d["produced"]
    else:
        d["planned_qty"] = pd.to_numeric(d["planned_qty"], errors="coerce").fillna(d["produced"]).astype(int)

    if "scrap" not in d.columns or "rework" not in d.columns:
        d["scrap"] = d["rejected"]
        d["rework"] = 0
    else:
        d["scrap"] = pd.to_numeric(d["scrap"], errors="coerce").fillna(d["rejected"]).astype(int)
        d["rework"] = pd.to_numeric(d["rework"], errors="coerce").fillna(0).astype(int)

    if "customer" not in d.columns:
        d["customer"] = "General"
    else:
        d["customer"] = d["customer"].fillna("General").astype(str)

    if "defect_category" not in d.columns:
        d["defect_category"] = d["defect"].map(lambda x: DEFECT_CATEGORIES.get(str(x), "Other"))
    else:
        d["defect_category"] = d["defect_category"].fillna("Other").astype(str)

    if "heat_no" not in d.columns:
        d["heat_no"] = "N/A"
    else:
        d["heat_no"] = d["heat_no"].fillna("N/A").astype(str)

    if "pattern_id" not in d.columns:
        d["pattern_id"] = "N/A"
    else:
        d["pattern_id"] = d["pattern_id"].fillna("N/A").astype(str)

    if "downtime_minutes" not in d.columns:
        d["downtime_minutes"] = 0
    else:
        d["downtime_minutes"] = pd.to_numeric(d["downtime_minutes"], errors="coerce").fillna(0).astype(int)

    if "downtime_reason" not in d.columns:
        d["downtime_reason"] = "None"
    else:
        d["downtime_reason"] = d["downtime_reason"].fillna("None").astype(str)

    return d


def quality_issues(raw: pd.DataFrame) -> List[Tuple[str, str]]:
    """
    Comprehensive data-quality checks on a raw PMS extract.
    Returns ordered list of (level, message) tuples where level in ('ok', 'warning', 'error').
    """
    cols = {str(c).strip().lower() for c in raw.columns}
    need = {"date", "department", "machine", "product", "produced", "rejected", "defect"}
    missing = need - cols
    if missing:
        return [("error", f"Missing columns: {sorted(missing)}")]

    d = raw.copy()
    d.columns = [str(c).strip().lower() for c in d.columns]
    out: List[Tuple[str, str]] = []

    # Check nulls
    null_produced = int(d["produced"].isna().sum())
    if null_produced:
        out.append(("warning", f"{null_produced} rows with empty 'produced' will be dropped"))

    # Check negative quantities
    prod_num = pd.to_numeric(d["produced"], errors="coerce").fillna(0)
    rej_num = pd.to_numeric(d["rejected"], errors="coerce").fillna(0)
    if (prod_num < 0).sum() or (rej_num < 0).sum():
        out.append(("warning", "Negative quantities detected (rejected clipped to 0)"))

    # Check rejected > produced
    rej_over = int((rej_num > prod_num).sum())
    if rej_over:
        out.append(("warning", f"{rej_over} rows where rejected > produced"))

    # Check scrap + rework consistency
    if "scrap" in d.columns and "rework" in d.columns:
        sc = pd.to_numeric(d["scrap"], errors="coerce").fillna(0)
        rw = pd.to_numeric(d["rework"], errors="coerce").fillna(0)
        mismatch = int(((sc + rw) != rej_num).sum())
        if mismatch:
            out.append(("warning", f"{mismatch} rows where scrap + rework does not equal rejected"))

    # Check excessive downtime
    if "downtime_minutes" in d.columns:
        dt_num = pd.to_numeric(d["downtime_minutes"], errors="coerce").fillna(0)
        excess_dt = int((dt_num > 480).sum())
        if excess_dt:
            out.append(("warning", f"{excess_dt} rows with downtime exceeding shift capacity (>480m)"))

    # Check duplicates
    dup_count = int(d.duplicated().sum())
    if dup_count:
        out.append(("warning", f"{dup_count} duplicate rows detected and pruned"))

    return out or [("ok", f"All checks passed ({len(d):,} rows)")]


# ==============================================================================
# 3. COLUMN MAPPING & PRESETS
# ==============================================================================

def auto_map_columns(source_columns: List[str]) -> Dict[str, str]:
    """
    Intelligently infer canonical column mappings from arbitrary source headers using alias matching.
    Returns: Dict[target_canonical_name, matched_source_column]
    """
    normalized_sources = {s.strip().lower().replace(" ", "_").replace("-", "_"): s for s in source_columns}
    mapping: Dict[str, str] = {}

    for canonical, aliases in CANONICAL_COLUMNS.items():
        found = False
        # Exact alias match
        for alias in aliases:
            norm_alias = alias.lower().replace(" ", "_")
            if norm_alias in normalized_sources:
                mapping[canonical] = normalized_sources[norm_alias]
                found = True
                break
        if found:
            continue

        # Substring heuristic match
        for norm_src, orig_src in normalized_sources.items():
            if any(alias in norm_src for alias in aliases):
                mapping[canonical] = orig_src
                break

    return mapping


def apply_column_mapping(df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
    """
    Apply column mapping dictionary {canonical_field: source_column_name} to transform input dataframe.
    """
    reverse_map = {src_col: target_field for target_field, src_col in mapping.items() if src_col in df.columns}
    renamed = df.rename(columns=reverse_map)
    return renamed


def save_mapping_preset(
    preset_name: str,
    mapping: Dict[str, str],
    filepath: Optional[str] = None,
) -> None:
    """Save user column mapping preset to local storage."""
    path = filepath or config.COLUMN_MAPPINGS_FILE
    presets = load_mapping_presets(path)
    presets[preset_name] = mapping
    with open(path, "w", encoding="utf-8") as f:
        json.dump(presets, f, indent=2)


def load_mapping_presets(filepath: Optional[str] = None) -> Dict[str, Dict[str, str]]:
    """Load column mapping presets including built-in presets and user configurations."""
    path = filepath or config.COLUMN_MAPPINGS_FILE
    all_presets = dict(DEFAULT_PRESETS)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                user_presets = json.load(f)
                all_presets.update(user_presets)
        except Exception as e:
            log.warning("Could not read presets file %s: %s", path, e)
    return all_presets


# ==============================================================================
# 4. CONNECTORS (FILE, SQLALCHEMY, REST API)
# ==============================================================================

def read_uploaded_file(file_obj: Any, filename: str) -> pd.DataFrame:
    """Read CSV or Excel uploaded file object with encoding and format fallbacks."""
    name_lower = filename.lower()
    if name_lower.endswith(".csv"):
        try:
            return pd.read_csv(file_obj)
        except UnicodeDecodeError:
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
            return pd.read_csv(file_obj, encoding="latin1")
    elif name_lower.endswith((".xlsx", ".xls")):
        return pd.read_excel(file_obj)
    else:
        raise ValueError(f"Unsupported file format for {filename}. Expected .csv, .xlsx, or .xls")


def test_sql_connection(connection_url: str) -> Tuple[bool, Union[List[str], str]]:
    """Test connection to an external SQL database and list available tables."""
    try:
        engine = sa.create_engine(connection_url)
        with engine.connect() as conn:
            inspector = sa.inspect(engine)
            tables = inspector.get_table_names()
            return True, tables
    except Exception as e:
        return False, str(e)


def fetch_sql(
    connection_url: Optional[str] = None,
    table_or_query: str = "pms_production_records",
    since_date: Optional[Union[str, date]] = None,
) -> pd.DataFrame:
    """
    Fetch PMS records from external SQL database (SQLite, MySQL, SQL Server, PostgreSQL)
    via SQLAlchemy with parameterized query support.
    """
    url = connection_url or config.PMS_DATABASE_URL
    engine = sa.create_engine(url)

    is_select = table_or_query.strip().lower().startswith("select")
    if is_select:
        query = table_or_query
        params: Dict[str, Any] = {}
        if since_date and ":since" in query:
            params["since"] = str(since_date)
        with engine.connect() as conn:
            return pd.read_sql_query(text(query), conn, params=params)
    else:
        table_name = table_or_query
        if since_date:
            q = f"SELECT * FROM {table_name} WHERE date >= :since ORDER BY date ASC"
            with engine.connect() as conn:
                return pd.read_sql_query(text(q), conn, params={"since": str(since_date)})
        else:
            with engine.connect() as conn:
                return pd.read_sql_table(table_name, conn)


def seed_mock_sql_db(db_path: str = "pms_external.db") -> str:
    """
    Seed a standalone mock external SQL database file with realistic production records
    so judges and reviewers can test the SQL connector out-of-the-box without manual DB setup.
    """
    df = sample_pms(days=60, seed=101)
    engine = sa.create_engine(f"sqlite:///{db_path}")
    df.to_sql("pms_production_records", engine, if_exists="replace", index=False)
    return db_path


def fetch_api_pms(
    base_url: Optional[str] = None,
    since_date: Optional[Union[str, date]] = None,
    limit: int = 1000,
) -> Tuple[bool, Union[pd.DataFrame, str]]:
    """
    Fetch live production records from the FastAPI mock PMS server.
    Returns: (is_success, DataFrame or error_message)
    """
    import requests
    url = (base_url or config.MOCK_PMS_URL).rstrip("/")
    endpoint = f"{url}/api/pms/records"
    params: Dict[str, Any] = {"limit": limit}
    if since_date:
        params["since"] = str(since_date)

    try:
        resp = requests.get(endpoint, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and "records" in data:
                records = data["records"]
            elif isinstance(data, list):
                records = data
            else:
                records = []
            if not records:
                return True, pd.DataFrame()
            df = pd.DataFrame(records)
            return True, clean(df)
        else:
            return False, f"Server responded with status {resp.status_code}: {resp.text}"
    except Exception as e:
        return False, f"Failed to connect to Mock PMS at {url}: {e}"


# ==============================================================================
# 5. CENTRAL DATABASE & INCREMENTAL LOADING
# ==============================================================================

def init_central_db(db_path: Optional[str] = None) -> None:
    """Initialize central SQLite tables with indexing and ingestion tracking."""
    path = db_path or config.DB_PATH
    con = sqlite3.connect(path)
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ingestion_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        source_type TEXT NOT NULL,
        source_name TEXT,
        records_read INTEGER NOT NULL,
        records_inserted INTEGER NOT NULL,
        records_skipped INTEGER NOT NULL,
        status TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS pms_data (
        date TEXT NOT NULL,
        department TEXT NOT NULL,
        machine TEXT NOT NULL,
        product TEXT NOT NULL,
        shift TEXT NOT NULL,
        planned_qty INTEGER,
        produced INTEGER NOT NULL,
        rejected INTEGER NOT NULL,
        scrap INTEGER,
        rework INTEGER,
        good INTEGER,
        defect TEXT,
        defect_category TEXT,
        customer TEXT,
        heat_no TEXT,
        pattern_id TEXT,
        downtime_minutes INTEGER,
        downtime_reason TEXT,
        humidity REAL,
        temperature REAL,
        PRIMARY KEY (date, department, machine, product, shift, heat_no)
    )
    """)
    con.commit()
    con.close()


def save_sqlite(df: pd.DataFrame, path: Optional[str] = None) -> None:
    """Legacy full-table replacement into central database."""
    db_file = path or config.DB_PATH
    init_central_db(db_file)
    con = sqlite3.connect(db_file)
    clean_df = clean(df)
    clean_df.to_sql("pms_data", con, if_exists="replace", index=False)
    con.close()


def load_sqlite(path: Optional[str] = None) -> pd.DataFrame:
    """Read all records from central SQLite database, returning sorted DataFrame."""
    db_file = path or config.DB_PATH
    init_central_db(db_file)
    con = sqlite3.connect(db_file)
    try:
        df = pd.read_sql("SELECT * FROM pms_data ORDER BY date ASC", con)
    except Exception:
        con.close()
        return pd.DataFrame()
    con.close()

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def incremental_load(
    incoming_df: pd.DataFrame,
    source_type: str = "Upload",
    source_name: str = "",
    db_path: Optional[str] = None,
) -> Dict[str, int]:
    """
    Perform idempotent incremental load: only new, unrecorded entries are appended.
    Checks uniqueness via composite signature (date, department, machine, product, shift, heat_no).
    Logs the transaction in ingestion_log.
    """
    db_file = db_path or config.DB_PATH
    init_central_db(db_file)

    if incoming_df.empty:
        return {"read": 0, "inserted": 0, "skipped": 0}

    df = clean(incoming_df)
    total_read = len(df)

    con = sqlite3.connect(db_file)

    # Generate matching signature in memory
    def make_sig(row: pd.Series) -> str:
        return f"{row['date']}|{row['department']}|{row['machine']}|{row['product']}|{row['shift']}|{row.get('heat_no', 'N/A')}"

    # Fetch existing signatures
    existing_sigs = set()
    try:
        cur = con.cursor()
        cur.execute("SELECT date, department, machine, product, shift, COALESCE(heat_no, 'N/A') FROM pms_data")
        for row in cur.fetchall():
            existing_sigs.add(f"{row[0]}|{row[1]}|{row[2]}|{row[3]}|{row[4]}|{row[5]}")
    except Exception as e:
        log.warning("Could not read existing keys: %s", e)

    df["_sig"] = df.apply(make_sig, axis=1)
    new_mask = ~df["_sig"].isin(existing_sigs)
    new_records = df[new_mask].drop(columns=["_sig"])
    skipped_count = int((~new_mask).sum())
    inserted_count = len(new_records)

    # Append new records
    if inserted_count > 0:
        new_records.to_sql("pms_data", con, if_exists="append", index=False)

    # Log operation
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO ingestion_log (timestamp, source_type, source_name, records_read, records_inserted, records_skipped, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (now_str, source_type, source_name, total_read, inserted_count, skipped_count, "SUCCESS"),
    )
    con.commit()
    con.close()

    return {"read": total_read, "inserted": inserted_count, "skipped": skipped_count}


def get_ingestion_log(db_path: Optional[str] = None) -> pd.DataFrame:
    """Retrieve history of incremental data loads."""
    db_file = db_path or config.DB_PATH
    init_central_db(db_file)
    con = sqlite3.connect(db_file)
    log_df = pd.read_sql("SELECT * FROM ingestion_log ORDER BY id DESC LIMIT 25", con)
    con.close()
    return log_df


def reset_central_db(db_path: Optional[str] = None) -> None:
    """Wipe central database tables for fresh demonstration."""
    db_file = db_path or config.DB_PATH
    if os.path.exists(db_file):
        con = sqlite3.connect(db_file)
        cur = con.cursor()
        cur.execute("DROP TABLE IF EXISTS pms_data")
        cur.execute("DROP TABLE IF EXISTS ingestion_log")
        con.commit()
        con.close()
    init_central_db(db_file)
