# SmartMIS - Automated Manufacturing MIS & Rejection Report Generator
Sakthi Hackathon 2.0 | PS-005 | Team firstones (SKH2-2026-00275)

Automated Manufacturing MIS, AI-Powered Enterprise BI Platform featuring an Executive Streamlit dashboard, "Ask Your Data" Natural Language Interface, Smart Insights, One-Page Plant Head Digest PDF, Role-Based Access Control (RBAC), Action Audit Logging, Power BI star-schema export, OEE & quality intelligence, Cost of Poor Quality (₹ INR), SPC p-charts, anomaly alerts, 14-day statistical forecasting, multi-level root-cause drill-downs, template-driven Excel/PDF reports, and scheduled automation.

## Project Structure
- [`smartmis/`](smartmis/): Application source code and test suite.
  - [`app.py`](smartmis/app.py): Enterprise Streamlit multi-page dashboard & analytics portal.
  - [`auth.py`](smartmis/auth.py): Role-Based Access Control (Admin/Manager/Operator), department scoping, and audit logger.
  - [`nlp_query.py`](smartmis/nlp_query.py): "Ask your data" natural language query engine with whitelisted executors (`top_n`, `trend`, `compare`, `filter`, `kpi`).
  - [`executive.py`](smartmis/executive.py): Smart Insights engine (3 findings + 3 actions), One-Page Executive PDF generator, Power BI export & DAX guide.
  - [`kpis.py`](smartmis/kpis.py): OEE, COPQ (₹), SPC p-charts, anomaly detector, statsmodels 14-day forecast, drill-down engine.
  - [`data.py`](smartmis/data.py): Simulator, SQLAlchemy/API connectors, column mapper, incremental loader.
  - [`reports.py`](smartmis/reports.py): Template loader, plain-English auto-commentary, Excel/PDF engines, SMTP delivery.
  - [`scheduler.py`](smartmis/scheduler.py): Cron schedule management, execution with retry, run history, and report archive.
  - [`core.py`](smartmis/core.py): Central facade re-exporting modules with 100% backwards-compatibility.
  - [`mock_pms/server.py`](smartmis/mock_pms/server.py): FastAPI Mock PMS gateway for live production streaming.
  - [`reports/templates/`](smartmis/reports/templates/): Declarative YAML templates (`weekly_foundry.yaml`, `weekly_machine_shop.yaml`, `monthly_rejection.yaml`).
  - [`tests/`](smartmis/tests/): Automated pytest suite covering core, data, reports, KPIs, and enterprise features (36 passing tests).

## Quick Start
```bash
cd smartmis
pip install -r requirements.txt
streamlit run app.py
```

### Default Login Accounts
- **Admin**: `admin` / `admin123` (Full system access, all departments, settings, user management)
- **Manager**: `manager` / `manager123` (Plant-wide visibility, all reports, analytics, export)
- **Foundry Operator**: `op_foundry` / `foundry123` (Foundry department only)
- **Machining Operator**: `op_machining` / `machining123` (Machine Shop department only)

### Live Mock PMS Server (Optional)
```bash
cd smartmis
python -m mock_pms.server
```

## Running Tests
```bash
cd smartmis
pip install pytest
python -m pytest tests
```
