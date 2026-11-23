# SmartMIS - Automated Manufacturing MIS & Rejection Report Generator
Sakthi Hackathon 2.0 | PS-005 | Team firstones (SKH2-2026-00275)

Automated Manufacturing MIS, AI-Powered Enterprise BI Platform featuring an Executive Streamlit dashboard, "Ask Your Data" Natural Language Interface, Smart Insights, One-Page Plant Head Digest PDF, Role-Based Access Control (RBAC), Action Audit Logging, Power BI star-schema export, OEE & quality intelligence, Cost of Poor Quality (₹ INR), SPC p-charts, anomaly alerts, 14-day statistical forecasting, multi-level root-cause drill-downs, template-driven Excel/PDF reports, and scheduled automation.

## Quick Start
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the Streamlit Application
streamlit run app.py

# 3. (Optional) Run the Mock PMS REST API Server
python -m mock_pms.server
```

### Default Login Credentials
- **System Admin**: `admin` / `admin123` (Full system configuration, COPQ pricing, schedules, audit log)
- **Plant Manager**: `manager` / `manager123` (Full visibility across Foundry and Machine Shop)
- **Foundry Operator**: `op_foundry` / `foundry123` (Strictly scoped to Foundry records)
- **Machining Operator**: `op_machining` / `machining123` (Strictly scoped to Machine Shop records)

## Running Tests
```bash
pip install pytest
python -m pytest tests -v
```

---

## Phase 4 Capabilities: AI & Enterprise Features

### 1. "Ask Your Data" Natural Language Query Interface
- **Safe Natural Language Querying**: Translates user manufacturing queries (e.g. *"Top 3 defects in Foundry"*, *"Monthly rejection trend"*, *"Compare rejection between Shift A and Shift B"*) directly into structured analytics.
- **Strict Execution Whitelist**: Only permits execution of verified analytics functions: `top_n`, `trend`, `compare`, `filter`, and `kpi`. **Zero arbitrary code execution or SQL injection risk**.
- **Offline + AI Dual-Engine**: Utilizes the Anthropic Claude API when `ANTHROPIC_API_KEY` is present, with automatic, zero-configuration offline fallback to an intelligent rule-based intent parser.
- **Transparent Output**: Displays query execution provenance, the exact dataset filters applied, the generated data table, and interactive Plotly visualization.

### 2. Smart Insights Engine
- **Automated Root-Cause Diagnostic**: Evaluates live operational data and instantly generates:
  - **3 Key Quantitative Findings**: Identifies top loss drivers, machine degradation patterns, and quality anomalies.
  - **3 Prioritized Corrective Actions**: Formulates actionable engineering interventions (e.g. vent cleaning, tool offset compensation, moisture control).

### 3. One-Page Executive Summary PDF (Plant Head Digest)
- **High-Density Single-Page Brief**: Specially formatted A4 report engineered for plant general managers and directors.
- **Compact Multi-Component Layout**:
  - Executive header with target vs actual rejection benchmarks.
  - 4-metric KPI scorecard (Production, Rejection %, FPY %, Total COPQ ₹).
  - Departmental breakdown matrix (Foundry vs Machine Shop).
  - Embedded Top Defect Pareto chart.
  - Automated executive commentary summarizing critical shifts and machines.
  - Formal sign-off block for General Manager & Quality Head.

### 4. Enterprise RBAC & Action Audit Logging
- **Role-Based Access Control**:
  - **Admin**: Complete system control, target setting, schedule frequency, and audit inspection.
  - **Manager**: Cross-departmental operational analytics, report generation, and data export.
  - **Operator**: Hard-filtered departmental view ensuring shop floor personnel view only their allocated department.
- **Salted SHA-256 Hashing**: PBKDF2 cryptography for secure credential storage.
- **Action Audit Trail**: Every critical action (login, report generation, file export, data load, settings change) is immutably logged to SQLite `action_audit_log` with timestamp, user ID, role, action type, and details.

### 5. Multi-Page Layout & Enterprise Settings Studio
- **Unified Navigation Sidebar**:
  1. Home (System Overview & Architecture)
  2. Executive Dashboard (KPIs & Smart Insights)
  3. Ask Your Data (Natural Language Query)
  4. Quality Control & SPC (p-Charts & Wheeler Rules)
  5. Cost of Poor Quality (COPQ & Top 5 Drivers)
  6. 14-Day Forecasting (Statsmodels Holt-Winters)
  7. Multi-Level Drill-Down (Root-Cause Hierarchy)
  8. Formal MIS Reports (Excel & PDF from YAML Templates)
  9. Executive Summary (1-Page Plant Head Digest)
  10. Report Archive (Browse & Download Generated Deliverables)
  11. PMS Data Import & Mapping (CSV/Excel, SQL, Mock API)
  12. Automation Scheduler (Dynamic Cron & Email Dispatch)
  13. Power BI Integration (Dataset Export & DAX Guide)
  14. Enterprise Settings & Audit Log (Admin Only)
- **Enterprise Settings Studio**: In-app management of plant quality targets, per-part COPQ pricing, scheduled delivery, email SMTP parameters, and company branding.

### 6. Power BI Integration Ready-Dataset & Guide
- **Dimensional Star-Schema Export**: One-click generation of `powerbi_manufacturing_model.csv` with calendar dimensions (`year`, `month`, `week`, `day`) and calculated financial measures.
- **Pre-Built DAX Measures**: Ready-to-paste production-grade DAX formulas for Plant OEE, COPQ (₹), First-Pass Yield, and Plan Adherence.
- **Dashboard Blueprint**: Visual recommendations matching Sakthi Hackathon Round 1 presentation guidelines.

---

## Phase 3 Capabilities: Advanced Manufacturing Analytics
- **OEE (Overall Equipment Effectiveness)**: Availability × Performance × Quality.
- **First-Pass Yield (FPY %)**, Scrap %, Rework %, PPM, and Plan Adherence %.
- **Cost of Poor Quality (COPQ in ₹ INR)**: Editable per-part cost matrix and Top 5 financial cost drivers.
- **Statistical Process Control (SPC) p-Chart**: Dynamic 3-sigma control limits (UCL/LCL) and Western Electric / Wheeler rules.
- **Robust Anomaly Detection**: Rolling median and MAD z-scores with severity tiers (CRITICAL, WARNING, INFO).
- **Two-Week Statistical Forecasting**: 14-day production & rejection forecasting with 95% confidence intervals using `statsmodels`.
- **Multi-Level Root-Cause Drill-Down**: Department ➔ Machine ➔ Shift ➔ Defect ➔ Heat Number.

---

## Phase 2 Capabilities: Template-Driven Reports & Automation
- **Declarative YAML Templates (`reports/templates/*.yaml`)**: `weekly_foundry.yaml`, `weekly_machine_shop.yaml`, and `monthly_rejection.yaml`.
- **Enhanced Excel Engine**: A4 Landscape print setup, frozen panes, KPI summary band, conditional formatting, and native charts.
- **Executive PDF Deliverables**: Header cover block, KPI table, embedded Matplotlib charts, commentary, and official sign-off blocks.
- **Automated Plain-English Commentary**: Rule-based executive narrative generated per report period.
- **Dynamic Scheduler & Archive**: UI-based weekly/monthly schedule editor, execution with retry, audit history, and report library.
- **SMTP Email Delivery**: Multi-attachment report dispatch with dry-run demo mode.

---

## Phase 1 Capabilities: Realistic Data & PMS Integration
- **Realistic Simulator**: Shifts A/B/C, heat numbers (`H24-101`), pattern IDs (`PAT-BD-01`), planned vs actual, scrap vs rework, downtime reasons, OEM customers, humidity surges elevating blow holes in Foundry, and gradual degradation of `CNC-02`.
- **Connectors**: CSV/Excel upload with encoding detection, SQL via SQLAlchemy (`PMS_DATABASE_URL`), and FastAPI Mock PMS Server (`mock_pms/server.py`).
- **Column Mapping Studio**: Fuzzy header matching with built-in presets (`SAP PP Export`, `MES Shopfloor Log`).
- **Idempotent Incremental Ingestion**: SQLite central database (`smartmis.db`) with composite key duplicate prevention and ingestion audit log.
