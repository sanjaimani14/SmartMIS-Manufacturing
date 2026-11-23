# SmartMIS - Automated Manufacturing MIS & Rejection Report Generator
Sakthi Hackathon 2.0 | PS-005 | Team firstones (SKH2-2026-00275)

Automated Manufacturing MIS & Advanced BI Analytics Platform featuring an Executive Streamlit dashboard, OEE & quality intelligence, Cost of Poor Quality (₹ INR), SPC p-charts, anomaly alerts, 14-day statistical forecasting, multi-level root-cause drill-downs, template-driven Excel/PDF reports, and scheduled automation.

## Project Structure
- [`smartmis/`](smartmis/): Application source code and test suite.
  - [`app.py`](smartmis/app.py): Executive Streamlit Dashboard, Analytics Suite & Archive.
  - [`kpis.py`](smartmis/kpis.py): OEE, COPQ (₹), SPC p-charts, anomaly detector, statsmodels 14-day forecast, drill-down engine.
  - [`data.py`](smartmis/data.py): Simulator, SQLAlchemy/API connectors, column mapper, incremental loader.
  - [`reports.py`](smartmis/reports.py): Template loader, plain-English auto-commentary, Excel/PDF engines, SMTP delivery.
  - [`scheduler.py`](smartmis/scheduler.py): Cron schedule management, execution with retry, run history, and report archive.
  - [`core.py`](smartmis/core.py): Facade module integrating data, KPIs, reports, and scheduler.
  - [`mock_pms/server.py`](smartmis/mock_pms/server.py): FastAPI Mock PMS gateway for live production streaming.
  - [`reports/templates/`](smartmis/reports/templates/): Declarative YAML templates (`weekly_foundry.yaml`, `weekly_machine_shop.yaml`, `monthly_rejection.yaml`).
  - [`tests/`](smartmis/tests/): Automated pytest suite (`test_core.py`, `test_data.py`, `test_reports.py`, `test_kpis.py`).

## Quick Start
```bash
cd smartmis
pip install -r requirements.txt
streamlit run app.py
```

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
