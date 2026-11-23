# SmartMIS: Automated Manufacturing MIS & Rejection Report Generator
[![Sakthi Hackathon 2.0](https://img.shields.io/badge/Sakthi%20Hackathon%202.0-PS--005-orange.svg)](https://github.com/sanjaimani14/SmartMIS-Manufacturing)
[![CI Tests](https://img.shields.io/badge/CI%20Suite-41%2F41%20Passing-brightgreen.svg)](https://github.com/sanjaimani14/SmartMIS-Manufacturing)
[![Python Version](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![UI Framework](https://img.shields.io/badge/UI-Streamlit%20Multi--Page-FF4B4B.svg)](https://streamlit.io/)
[![Container](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Event**: Sakthi Hackathon 2.0 (Round 2)  
> **Problem Statement**: PS-005 "Automated Manufacturing MIS and Rejection Report Generator"  
> **Theme**: Data Analytics, MIS and BI  
> **Team**: firstones (SKH2-2026-00275)

---

## 🏭 Executive Overview & Industrial Context
In high-volume automotive foundries and precision machine shops, quality and production engineers spend over **65 hours every month** manually collecting paper shift logs, copy-pasting spreadsheet rows, computing rejection percentages, and formatting weekly reports. By the time leadership identifies a defect surge, hundreds of defective castings have already compounded scrap costs.

**SmartMIS** is an enterprise-grade, turnkey manufacturing intelligence and automated MIS platform built specifically for foundry and machining operations. It eliminates **99.4% of manual reporting overhead**, reduces report generation from hours to seconds, and brings real-time **Statistical Process Control (SPC)**, **Cost of Poor Quality (COPQ in ₹ INR)**, and **Safe Natural-Language AI Querying** directly to the plant head's desk.

---

## 📐 System Architecture
![SmartMIS Architecture](docs/architecture.png)

SmartMIS is structured across 5 production-grade operational tiers:
1. **Heterogeneous Ingestion & Connectivity**: CSV/Excel uploads with encoding auto-detection, SQLAlchemy connector for relational databases (SQLite, MySQL, MS SQL Server), and FastAPI Mock PMS REST streaming gateway (`/api/pms/today`).
2. **Incremental ETL & Persistence**: Composite natural-key deduplication (`date + dept + machine + shift + heat_no + product`) ensuring idempotent loading into SQLite `smartmis.db` with an immutable `action_audit_log`.
3. **Quality Analytics & Intelligence Core**:
   - **OEE Engine**: $\text{Availability} \times \text{Performance} \times \text{Quality}$
   - **Financial COPQ Matrix**: Real-time non-conformance costing in Indian Rupees (₹) with Top 5 loss drivers.
   - **Statistical Process Control**: Dynamic subgroup p-charts with 3-sigma limits ($\text{UCL}_i / \text{LCL}_i$) and Western Electric / Wheeler rules (Rules 1, 2, 3).
   - **MAD Anomaly Detection**: Median Absolute Deviation rolling median z-score alerts (`CRITICAL`, `WARNING`, `INFO`).
   - **14-Day Forecasting**: Statsmodels Holt-Winters Exponential Smoothing with 95% confidence bounds.
   - **Multi-Level Drill-Down**: $\text{Department} \rightarrow \text{Machine} \rightarrow \text{Shift} \rightarrow \text{Defect} \rightarrow \text{Heat Lot}$.
4. **AI & Executive Decision Layer**:
   - **"Ask Your Data"**: Natural language interface strictly sandboxed to whitelisted analytics primitives (`top_n`, `trend`, `compare`, `filter`, `kpi`) with dual Claude API and zero-configuration offline regex fallback.
   - **Smart Insights Engine**: Automated root-cause diagnostic identifying 3 Key Findings and 3 Prioritized Engineering Actions.
   - **One-Page Executive Summary PDF**: High-density GM briefing digest.
   - **Role-Based Access Control**: PBKDF2-salted SHA-256 authentication with departmental scoping (Foundry vs Machine Shop operators).
5. **Multi-Channel Presentation & Ecosystem Delivery**:
   - 16-module interactive Streamlit application with live shopfloor streaming and defect spike injection.
   - Declarative YAML report engine (`reports/templates/*.yaml`) generating corporate A4 Landscape Excel and signed PDF deliverables.
   - Automated Cron Scheduler with failure retry, report archive, and SMTP email delivery (with dry-run demo mode).
   - Microsoft Power BI ready star-schema dataset (`powerbi_manufacturing_model.csv`) with production-grade DAX measures.

---

## 🚀 Quick Start Guide

### 1. Local Python Setup
```bash
# Clone the repository
git clone https://github.com/sanjaimani14/SmartMIS-Manufacturing.git
cd SmartMIS-Manufacturing/smartmis

# Install dependencies
pip install -r requirements.txt

# Launch the Streamlit application
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

### 2. Live Mock PMS REST Server (Optional for Live Telemetry Demos)
In a separate terminal window:
```bash
cd smartmis
python -m mock_pms.server
```
Runs a FastAPI mock shopfloor gateway on `http://localhost:8001/api/pms/today`.

### 3. Production Docker Setup
```bash
# Start both SmartMIS app and Mock PMS server
docker compose up -d
```
Access the application at `http://localhost:8501`.

---

## 👥 Enterprise User Accounts (RBAC)

SmartMIS enforces departmental data scoping based on logged-in roles:

| Role | Username | Password | Operational Access Scope |
| :--- | :--- | :--- | :--- |
| **System Admin** | `admin` | `admin123` | Full plant-wide access; settings, COPQ pricing, schedules, user directory, audit log. |
| **Plant Manager** | `manager` | `manager123` | Enterprise visibility across Foundry & Machine Shop; report generation, analytics, Power BI export. |
| **Foundry Operator** | `op_foundry` | `foundry123` | Strictly scoped to Foundry records. Machine Shop data is isolated. |
| **Machining Operator** | `op_machining` | `machining123` | Strictly scoped to Machine Shop records. Foundry data is isolated. |

---

## ⏱️ Business Value & Quantifiable ROI

| Metric | Legacy Manual Workflow | SmartMIS Automated Platform | Impact / Value Delivered |
| :--- | :--- | :--- | :--- |
| **Weekly Foundry MIS** | 180 min / run | 0.5 min / run | **99.7% time reduction** |
| **Weekly Machine Shop MIS** | 150 min / run | 0.5 min / run | **99.7% time reduction** |
| **Monthly Rejection MIS** | 420 min / run | 1.0 min / run | **99.8% time reduction** |
| **Daily Shift Log Ingestion** | 45 min / shift (2,700 min/mo) | 0.2 min / shift (12 min/mo) | **99.6% time reduction** |
| **Ad-Hoc Defect Queries** | 60 min / query | 0.1 min / query ("Ask Data")| **99.8% time reduction** |
| **Monthly Engineering Effort** | **68.3 hours / month** | **0.4 hours / month** | **99.4% overall reduction** |
| **Annual Recovered Bandwidth** | — | **815+ Senior Engineering Hours** | Re-allocated to Kaizen & Lean |
| **Annual Financial Savings** | — | **₹4,89,000 / year** | Direct bandwidth cost recovery |
| **Environmental Sustainability**| Paper logbooks & prints | Zero-paper digital archive | **1,200+ paper sheets saved/yr** |

---

## ✅ Problem Statement Compliance Matrix (PS-005)

| Requirement ID | Problem Statement Mandate | SmartMIS Feature Implementation | Verified Code Module | Status |
| :---: | :--- | :--- | :--- | :---: |
| **REQ-01** | Connect & import PMS data | CSV/Excel upload, SQLAlchemy (MySQL/MSSQL/SQLite), FastAPI live stream | `smartmis/data.py` | ✅ Verified |
| **REQ-02** | Handle vendor formats & duplicates | Fuzzy column mapping studio + composite-key idempotent incremental loader | `smartmis/data.py` | ✅ Verified |
| **REQ-03** | Approved report formats | Declarative YAML template engine (`reports/templates/*.yaml`) | `smartmis/reports.py` | ✅ Verified |
| **REQ-04** | Excel & PDF deliverables | A4 Landscape Excel with native charts; PDF with cover, sign-off blocks | `smartmis/reports.py` | ✅ Verified |
| **REQ-05** | Plain-English commentary | Rule-based executive narrative synthesizing week-on-week shifts and culprits | `smartmis/reports.py` | ✅ Verified |
| **REQ-06** | Scheduled generation & email | Dynamic UI cron editor, retry logic, archive browser, SMTP email dispatch | `smartmis/scheduler.py` | ✅ Verified |
| **REQ-07** | Manufacturing KPIs & OEE | OEE = Availability × Performance × Quality, FPY %, PPM, Plan Adherence | `smartmis/kpis.py` | ✅ Verified |
| **REQ-08** | Cost of Poor Quality (COPQ) | Editable per-part scrap/rework matrix in ₹ INR + Top 5 financial cost drivers | `smartmis/kpis.py` | ✅ Verified |
| **REQ-09** | Statistical Process Control (SPC) | Dynamic 3σ p-chart with Western Electric rules (1, 2, 3) + MAD anomaly alerts | `smartmis/kpis.py` | ✅ Verified |
| **REQ-10** | Predictive forecasting | 14-day production & rejection forecast with 95% confidence intervals | `smartmis/kpis.py` | ✅ Verified |
| **REQ-11** | Root-cause drill-down | 5-level hierarchy: Department ➔ Machine ➔ Shift ➔ Defect ➔ Heat Lot | `smartmis/kpis.py` | ✅ Verified |
| **REQ-12** | "Ask Your Data" AI query | Safe whitelisted analytics primitives (`top_n`, `trend`, `compare`, `kpi`) | `smartmis/nlp_query.py` | ✅ Verified |
| **REQ-13** | Executive intelligence | Smart Insights (3 findings + 3 actions) & 1-page Plant Head digest PDF | `smartmis/executive.py` | ✅ Verified |
| **REQ-14** | Role-Based Access Control & Audit | Admin, Manager, Operator roles with departmental scoping + SQLite audit log | `smartmis/auth.py` | ✅ Verified |
| **REQ-15** | Power BI readiness | Star-schema dimensional export (`powerbi_manufacturing_model.csv`) + DAX | `smartmis/executive.py` | ✅ Verified |
| **REQ-16** | Quantifiable manual effort reduction| Time-saved ROI counter (99.4% reduction, ₹4.89 Lakhs saved per year) | `smartmis/demo.py` | ✅ Verified |
| **REQ-17** | Demo readiness & deployment | Live shopfloor streaming, defect spike injection studio, Docker container | `smartmis/demo.py` | ✅ Verified |

---

## 🧪 Comprehensive Automated Test Suite (41 Tests)

```bash
cd smartmis
python -m pytest tests -v
```

```text
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.1.1, pluggy-1.6.0
collected 41 items

tests/test_core.py::test_clean_derives_good PASSED                       [  2%]
tests/test_core.py::test_clean_missing_columns PASSED                    [  4%]
tests/test_core.py::test_filters PASSED                                  [  7%]
tests/test_core.py::test_weekly_and_monthly PASSED                       [  9%]
tests/test_core.py::test_quality_flags_bad_data PASSED                   [ 12%]
tests/test_core.py::test_exports PASSED                                  [ 14%]
tests/test_core.py::test_kpi_delta PASSED                                [ 17%]
tests/test_data.py::test_simulator_schema_and_integrity PASSED           [ 19%]
tests/test_data.py::test_simulator_seasonal_humidity_effect PASSED       [ 21%]
tests/test_data.py::test_simulator_machine_degradation PASSED            [ 24%]
tests/test_data.py::test_clean_backwards_compatibility PASSED            [ 26%]
tests/test_data.py::test_quality_issues_detection PASSED                 [ 29%]
tests/test_data.py::test_column_mapping_heuristics PASSED                [ 31%]
tests/test_data.py::test_preset_persistence PASSED                       [ 34%]
tests/test_data.py::test_incremental_load_idempotency PASSED             [ 36%]
tests/test_data.py::test_sql_connector PASSED                            [ 39%]
tests/test_data.py::test_fastapi_mock_pms_client PASSED                  [ 41%]
tests/test_demo.py::test_streaming_batch PASSED                          [ 43%]
tests/test_demo.py::test_inject_defect_spike PASSED                      [ 46%]
tests/test_demo.py::test_inject_tool_offset_spike PASSED                 [ 48%]
tests/test_demo.py::test_time_saved_roi_calculation PASSED               [ 51%]
tests/test_demo.py::test_requirement_checklist_mapping PASSED            [ 53%]
tests/test_enterprise.py::test_rbac_authentication_and_scoping PASSED    [ 56%]
tests/test_enterprise.py::test_audit_logging PASSED                      [ 58%]
tests/test_enterprise.py::test_nlp_whitelisted_queries PASSED            [ 60%]
tests/test_enterprise.py::test_smart_insights_generation PASSED          [ 63%]
tests/test_enterprise.py::test_executive_summary_one_page_pdf PASSED     [ 65%]
tests/test_enterprise.py::test_powerbi_dataset_export PASSED             [ 68%]
tests/test_kpis.py::test_compute_advanced_kpis PASSED                    [ 70%]
tests/test_kpis.py::test_copq_calculation_and_top_drivers PASSED         [ 73%]
tests/test_kpis.py::test_spc_p_chart_limits_and_rules PASSED             [ 75%]
tests/test_kpis.py::test_anomaly_detection_z_score PASSED                [ 78%]
tests/test_kpis.py::test_statsmodels_14_day_forecasting PASSED           [ 80%]
tests/test_kpis.py::test_multi_level_drill_down PASSED                   [ 82%]
tests/test_reports.py::test_yaml_template_loading PASSED                 [ 85%]
tests/test_reports.py::test_new_template_extensibility PASSED            [ 87%]
tests/test_reports.py::test_rule_based_auto_commentary PASSED            [ 90%]
tests/test_reports.py::test_excel_landscape_kpi_band_and_charts PASSED   [ 92%]
tests/test_reports.py::test_pdf_cover_kpi_table_and_signoff PASSED       [ 95%]
tests/test_reports.py::test_smtp_email_dispatch_dry_run PASSED           [ 97%]
tests/test_reports.py::test_scheduler_persistence_and_run PASSED         [100%]
======================= 41 passed, 1 warning in 37.17s ========================
```

---

## 📸 Automated Playwright Screenshots Gallery

| Screen | Description | View |
| :--- | :--- | :---: |
| **Executive Dashboard** | High-level OEE, FPY %, PPM, and Smart Insights card | [View Screenshot](screenshots/2_executive_dashboard.png) |
| **Live Defect Spike** | Shopfloor streaming & real-time defect spike alert | [View Screenshot](screenshots/3_live_defect_spike.png) |
| **Quality Control & SPC** | Dynamic 3-sigma p-Chart with Western Electric rules | [View Screenshot](screenshots/4_quality_control_spc.png) |
| **Cost of Poor Quality** | Editable scrap/rework matrix (₹) & Top 5 cost drivers | [View Screenshot](screenshots/5_cost_of_poor_quality.png) |
| **14-Day Forecasting** | Statsmodels Holt-Winters projection with 95% CI cone | [View Screenshot](screenshots/6_14day_forecasting.png) |
| **Root-Cause Drill-Down** | 5-level operational drill-down to heat number lot | [View Screenshot](screenshots/7_root_cause_drilldown.png) |
| **Formal MIS Reports** | YAML template generator for Excel (.xlsx) & PDF | [View Screenshot](screenshots/8_formal_mis_reports.png) |
| **Time-Saved ROI Counter** | Interactive ROI calculator (99.4% reduction, ₹4.89L saved) | [View Screenshot](screenshots/9_time_saved_roi.png) |
| **Requirement Matrix** | 17/17 PS-005 hackathon requirement traceability | [View Screenshot](screenshots/10_requirement_checklist.png) |
| **Ask Your Data (AI)** | Safe whitelisted NLP querying with dual-engine parser | [View Screenshot](screenshots/11_ask_your_data.png) |
| **Power BI Integration** | Star-schema export & production DAX formulas | [View Screenshot](screenshots/12_power_bi_integration.png) |

---

## 📑 Generated Sample Reports

All sample reports generated by the template engine are preserved in `sample_reports/`:
- **Weekly Foundry Report**: [`weekly_foundry_2026-11-23.xlsx`](sample_reports/weekly_foundry_2026-11-23.xlsx) | [`weekly_foundry_2026-11-23.pdf`](sample_reports/weekly_foundry_2026-11-23.pdf)
- **Weekly Machine Shop Report**: [`weekly_machine_shop_2026-11-23.xlsx`](sample_reports/weekly_machine_shop_2026-11-23.xlsx) | [`weekly_machine_shop_2026-11-23.pdf`](sample_reports/weekly_machine_shop_2026-11-23.pdf)
- **Monthly Rejection Report**: [`monthly_rejection_2026-11-23.xlsx`](sample_reports/monthly_rejection_2026-11-23.xlsx) | [`monthly_rejection_2026-11-23.pdf`](sample_reports/monthly_rejection_2026-11-23.pdf)
- **One-Page Executive Summary PDF**: [`executive_summary_one_page_2026-11-23.pdf`](sample_reports/executive_summary_one_page_2026-11-23.pdf)

---

## 📚 Technical Documentation & Presentation Assets
- 🎬 [**5-Minute Hackathon Demo Script**](docs/demo_script.md): Timed presentation guide for judges.
- 💡 [**25 Technical & Domain Judge Q&A**](docs/judge_qa.md): In-depth answers covering edge cases, SPC mathematics, and architecture.
- 📘 [**Comprehensive User & Operations Manual**](docs/user_guide.md): Complete instructions for operators, managers, and IT admins.
- 🏗️ [**System Architecture Diagram**](docs/architecture.png): High-resolution architectural blueprint.
