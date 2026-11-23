# SmartMIS - Automated Manufacturing MIS & Rejection Report Generator
Sakthi Hackathon 2.0 | PS-005 | Team firstones (SKH2-2026-00275)

Automated Manufacturing MIS & Rejection Report Generator featuring an Executive Streamlit dashboard, template-driven Excel/PDF reports, automated plain-English commentary, scheduled generation with retry and email dispatch, and multi-source PMS integration.

## Project Structure
- [`smartmis/`](smartmis/): Application source code and test suite.
  - [`app.py`](smartmis/app.py): Executive Streamlit Dashboard, Schedule Controller & Archive.
  - [`data.py`](smartmis/data.py): Simulator, SQLAlchemy/API connectors, column mapper, incremental loader.
  - [`reports.py`](smartmis/reports.py): Template loader, plain-English auto-commentary, Excel/PDF engines, SMTP delivery.
  - [`scheduler.py`](smartmis/scheduler.py): Cron schedule management, execution with retry, run history, and report archive.
  - [`core.py`](smartmis/core.py): Facade module integrating data, reports, and scheduler.
  - [`mock_pms/server.py`](smartmis/mock_pms/server.py): FastAPI Mock PMS gateway for live production streaming.
  - [`reports/templates/`](smartmis/reports/templates/): Declarative YAML templates (`weekly_foundry.yaml`, `weekly_machine_shop.yaml`, `monthly_rejection.yaml`).
  - [`tests/`](smartmis/tests/): Automated pytest suite (`test_core.py`, `test_data.py`, `test_reports.py`).

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
