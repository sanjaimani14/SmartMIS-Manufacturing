# SmartMIS - Automated Manufacturing MIS & Rejection Report Generator
Sakthi Hackathon 2.0 | PS-005 | Team firstones (SKH2-2026-00275)

## Run
    pip install -r requirements.txt
    streamlit run app.py
## Test
    pip install pytest && python -m pytest tests

## Features
- PMS import (CSV/Excel) with data-quality checks; central SQLite database
- Filters: department, product, machine, shift, period
- Dashboard: colour-coded KPIs with period-over-period change, production vs rejection, defect Pareto, machine heatmap, shift comparison
- Reports: Weekly Foundry, Weekly Machine Shop, Monthly Rejection as formatted Excel (conditional formatting + charts) and PDF (charts, page numbers)
- Scheduler (APScheduler): weekly Mon 07:00, monthly 1st 07:00, Run-now, run history
- Settings in config.py (rejection target, schedule, folders)

## Data format
date, department, machine, product, produced, rejected, defect, shift (optional) - see sample_pms_data.csv
