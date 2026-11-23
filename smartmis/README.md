# SmartMIS - Automated Manufacturing MIS & Rejection Report Generator
Sakthi Hackathon 2.0 | PS-005 | Team firstones (SKH2-2026-00275)

Automated Manufacturing MIS & Rejection Report Generator with Streamlit dashboard, SQLite central database, automated report generation (Excel & PDF), APScheduler, and multi-source PMS ETL integration.

## Quick Start
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the Streamlit Application
streamlit run app.py

# 3. (Optional) Run the Mock PMS REST API Server
python -m mock_pms.server
```

## Running Tests
```bash
pip install pytest
python -m pytest tests
```

---

## Phase 1 Capabilities: Realistic Data & PMS Integration

### 1. Realistic Manufacturing Simulator
- **Shifts**: Diurnal Shift schedules A, B, and C with realistic fatigue factors.
- **Traceability**: Foundry heat batch numbers (`H24-101`) and tooling pattern codes (`PAT-BD-01`).
- **Production Efficiency**: Planned vs Actual quantities (`planned_qty`, `produced`, plan adherence %).
- **Downtime Tracking**: Breakdown minutes and root causes (`Tool Change`, `Electrical Breakdown`, `Mechanical Jam`, etc.).
- **Non-Conformance Hierarchy**: Distinction between unrecoverable **Scrap** (melt-loss) and rectifiable **Rework**.
- **OEM Customers**: Product allocation to OEMs (`Brembo`, `Mahindra`, `Tata Motors`, `BOSCH`, `TVS Motor`, `Dana`).
- **Seasonal Environmental Effects**: Monsoonal humidity surges (>70% RH) realistically elevate green sand **Blow Hole** porosity in the Foundry.
- **Equipment Degradation**: Tool wear and runout drift modeled on machine `CNC-02` (accelerating rejection rate and tool marks over time).
- **100% Backwards Compatible**: Retains all original core columns (`date`, `department`, `machine`, `product`, `produced`, `rejected`, `defect`, `shift`, `good`).

### 2. Multi-Source Connectors
- **CSV & Excel Upload**: Auto-detects encodings, formats, and handles legacy or custom spreadsheets.
- **SQL via SQLAlchemy**: Direct querying of external databases (SQLite, MySQL, SQL Server, PostgreSQL) via `PMS_DATABASE_URL`.
- **FastAPI Mock PMS Server (`mock_pms/server.py`)**:
  - Live plant management gateway streaming batch records, telemetry, and machine status.
  - Interactive OpenAPI Swagger documentation at `http://127.0.0.1:8001/docs`.
  - Endpoint `POST /api/pms/simulate-shift` to push live production batches in real time.

### 3. Column Mapping Studio
- **Fuzzy Auto-Detection**: Matches foreign ERP/MES column headers (`Posting_Date` -> `date`, `Actual_Qty` -> `produced`, etc.).
- **Preset Management**: Built-in presets for `SAP PP Export`, `MES Shopfloor Log`, and user-saved custom mapping presets.
- **Interactive Mapping UI**: Allows mapping and previewing custom files directly inside Streamlit before ingestion.

### 4. Idempotent Incremental Ingestion & Central Database
- **Central SQLite Database** (`smartmis.db`): Stores unified production data in `pms_data`.
- **Duplicate Prevention**: Ingests only new, unrecorded records based on composite signatures (`date`, `department`, `machine`, `product`, `shift`, `heat_no`).
- **Audit Ingestion Log**: Tracks load timestamp, source type, records read, inserted, and skipped duplicates.
