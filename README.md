# SmartMIS - Automated Manufacturing MIS & Rejection Report Generator
Sakthi Hackathon 2.0 | PS-005 | Team firstones (SKH2-2026-00275)

Automated Manufacturing MIS & Rejection Report Generator featuring a Streamlit dashboard, automated report generation (Excel & PDF), data quality validation, and scheduled reporting.

## Project Structure
- [`smartmis/`](smartmis/): Contains application source code, tests, and connectors.
  - [`app.py`](smartmis/app.py): Streamlit Executive Dashboard & PMS Integration Studio.
  - [`data.py`](smartmis/data.py): Simulator, SQLAlchemy/API connectors, column mapper, and incremental loader.
  - [`core.py`](smartmis/core.py): Facade module re-exporting data operations, report builders, and KPI engine.
  - [`mock_pms/server.py`](smartmis/mock_pms/server.py): FastAPI Mock PMS gateway for live production streaming.
  - [`tests/`](smartmis/tests/): Pytest test suite covering reporting and data integration.

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
python -m pytest tests
```
