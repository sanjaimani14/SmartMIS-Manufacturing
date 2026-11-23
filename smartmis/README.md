# SmartMIS - Automated Manufacturing MIS & Rejection Report Generator
Sakthi Hackathon 2.0 | PS-005 | Team firstones (SKH2-2026-00275)

Automated Manufacturing MIS & Rejection Report Generator featuring an Executive Streamlit dashboard, template-driven Excel/PDF reports, rule-based automated plain-English commentary, scheduled generation with retry and email dispatch, and multi-source PMS integration.

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

## Phase 2 Capabilities: Template-Driven Reports & Automation

### 1. Template-Driven Report Architecture (`reports/templates/*.yaml`)
- **Declarative YAML Templates**: Standard approved reporting formats defined in YAML:
  - `weekly_foundry.yaml`: Weekly performance, melt batches, furnace rejection, scrap vs rework, and machine trends.
  - `weekly_machine_shop.yaml`: Weekly CNC/VMC output, dimensional non-conformances, component breakdown.
  - `monthly_rejection.yaml`: 30-day plant-wide rejection Pareto analysis, departmental comparison, and long-term trend.
- **Extensibility**: To add a new report format, create a new `.yaml` file in `reports/templates/`—no Python code changes required!

### 2. Enhanced Excel Workbooks (`.xlsx`)
- **Landscape Print Setup**: Configured for A4 Landscape with automatic fit-to-page-width.
- **Frozen Panes**: Header rows and KPI metrics bands stay frozen while scrolling through dense production data.
- **Styled KPI Band**: Executive KPI summary band at the top of each worksheet (Produced, Good, Rejected, Rejection %, Scrap, Rework, Adherence).
- **Conditional Formatting**: Dynamic soft red cell highlighting on non-conformance rates exceeding company targets.
- **Native OpenPyXL Charts**: Native bar and line charts embedded directly alongside data sections.

### 3. Executive PDF Deliverables (`.pdf`)
- **Branded Header & Cover Block**: Company branding, period date range, and document metadata.
- **Executive Commentary Callout**: Prominently features rule-based plain-English operational commentary.
- **KPI Summary Table**: Color-coded metric overview with production volumes, quality rates, and scrap shares.
- **Embedded Visualizations**: High-resolution Matplotlib charts embedded cleanly per section.
- **Sign-Off Block**: Formal 2-column "Prepared by" / "Reviewed and Approved by" signature block with designations and dates.
- **Dynamic Page Numbers**: "Page X" footer on all pages with enterprise confidentiality notice.

### 4. Rule-Based Plain-English Automated Commentary
- Evaluates period-over-period delta (`cur_rate - prev_rate`) and describes trend in natural language.
- Highlights primary defect contributors (defect name, piece count, share of non-conformance).
- Flags critical equipment anomalies (worst machine rejection rate).
- Analyzes shift dynamics (best vs worst shift non-conformance).
- Summarizes scrap vs rework split and downtime root causes.

### 5. Scheduler & Dispatch Control
- **Interactive Schedule Editor**: Edit weekly (day of week, hour) and monthly (day of month, hour) cron schedules directly from the Streamlit UI.
- **Audit History Log**: Tracks run timestamp, status (SUCCESS/FAILED), execution duration (seconds), file counts, and error diagnostics.
- **Retry Mechanism**: Automated retry on transient generation/delivery failures.
- **SMTP Email Delivery**: Dispatches generated `.xlsx` and `.pdf` attachments to management with HTML body and auto-commentary. Features **Dry-Run Simulation Mode** for seamless demonstrations.
- **Report Archive Page**: Library to browse, filter, inspect metadata, and re-download generated reports.

---

## Phase 1 Capabilities: Realistic Data & PMS Integration
- **Realistic Simulator**: Shifts A/B/C, heat numbers (`H24-101`), pattern IDs (`PAT-BD-01`), planned vs actual, scrap vs rework, downtime reasons, OEM customers, humidity surges elevating blow holes in Foundry, and gradual degradation of `CNC-02`.
- **Connectors**: CSV/Excel upload with encoding detection, SQL via SQLAlchemy (`PMS_DATABASE_URL`), and FastAPI Mock PMS Server (`mock_pms/server.py`).
- **Column Mapping Studio**: Fuzzy header matching with built-in presets (`SAP PP Export`, `MES Shopfloor Log`).
- **Idempotent Incremental Ingestion**: SQLite central database (`smartmis.db`) with composite key duplicate prevention and ingestion audit log.
