# SmartMIS - Automated Manufacturing MIS & Rejection Report Generator
Sakthi Hackathon 2.0 | PS-005 | Team firstones (SKH2-2026-00275)

Automated Manufacturing MIS & Advanced BI Analytics Platform featuring an Executive Streamlit dashboard, OEE & quality intelligence, Cost of Poor Quality (₹ INR), SPC p-charts, anomaly alerts, 14-day statistical forecasting, multi-level root-cause drill-downs, template-driven Excel/PDF reports, and scheduled automation.

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

## Phase 3 Capabilities: Advanced Manufacturing Analytics

### 1. Advanced Manufacturing KPIs & OEE Engine
- **OEE (Overall Equipment Effectiveness)**: Computed as $\text{Availability} \times \text{Performance} \times \text{Quality}$.
  - **Availability %**: Ratio of operating time vs planned operating minutes (accounting for recorded machine downtime).
  - **Performance %**: Actual production vs planned schedule output during operating windows.
  - **Quality %**: First-pass conforming castings and components vs total manufactured.
- **First-Pass Yield (FPY %)**: Conforming parts produced without requiring rework or scrap.
- **Defect PPM (Parts Per Million)**: Standard automotive industry quality benchmark: $\frac{\text{rejected}}{\text{produced}} \times 1,000,000$.
- **Plan Adherence & Downtime %**: Quantifies production output vs planned target, and lost capacity percentage.

### 2. Cost of Poor Quality (COPQ in ₹ INR)
- **Financial Non-Conformance Impact**: Calculates financial loss in Indian Rupees (₹) for unrecoverable scrap and rectification rework.
- **Editable Cost Matrix**: Interactive in-app cost editor to adjust per-part scrap and rework valuations (persisted to `copq_costs.json`).
- **Top 5 Financial Loss Drivers**:
  - Top 5 products by COPQ with scrap vs rework cost breakdown.
  - Top 5 defects by financial loss.
  - Top 5 machines by financial loss.

### 3. Statistical Process Control (SPC) p-Chart
- **Dynamic 3-Sigma Limits**: Evaluates daily non-conformance proportion against subgroup-varying limits:
  $$\text{UCL}_i = \bar{p} + 3\sqrt{\frac{\bar{p}(1-\bar{p})}{n_i}}, \quad \text{LCL}_i = \max\left(0, \bar{p} - 3\sqrt{\frac{\bar{p}(1-\bar{p})}{n_i}}\right)$$
- **Western Electric / Wheeler Quality Rules**:
  - **Rule 1**: Points beyond 3-sigma control limits (Special Cause variation).
  - **Rule 2**: Run of 7 consecutive points on one side of the centerline (Process shift / bias).
  - **Rule 3**: Trend of 6 consecutive points steadily increasing or decreasing (Equipment wear / degradation).

### 4. Robust Anomaly Detection & Live Alerts Panel
- **Rolling Median & MAD Z-Scores**: Uses Median Absolute Deviation ($0.6745 \times \frac{x - \text{median}}{\text{MAD}}$) to detect non-Gaussian anomalies resistant to extreme outliers.
- **Actionable Severity Tiers**: Categorizes anomalies into `CRITICAL`, `WARNING`, and `INFO`.
- **Root-Cause Prescriptions**: Provides immediate containment instructions (e.g. sand degassing, tool offset calibration).

### 5. Two-Week Statistical Forecasting (Statsmodels)
- **Holt-Winters Exponential Smoothing**: 14-day forward projections with damped additive trends.
- **95% Confidence Intervals**: Dynamically calculated confidence cones for both daily production volume and rejection rate trajectory.

### 6. Multi-Level Root-Cause Drill-Down Studio
- **Cascading Operational Hierarchy**:
  $$\text{Department} \longrightarrow \text{Machine} \longrightarrow \text{Shift} \longrightarrow \text{Defect} \longrightarrow \text{Heat Lot}$$
- Dynamic filtering, instant KPI recalculation, and raw batch inspection.

---

## Phase 2 Capabilities: Template-Driven Reports & Automation
- **Declarative YAML Templates (`reports/templates/*.yaml`)**: `weekly_foundry.yaml`, `weekly_machine_shop.yaml`, and `monthly_rejection.yaml`. New format = new YAML file only.
- **Enhanced Excel Engine**: A4 Landscape print setup, frozen panes, KPI summary band, conditional formatting, and native OpenPyXL charts.
- **Executive PDF Deliverables**: Header cover block, KPI table, embedded Matplotlib charts, commentary callout, and official sign-off blocks.
- **Automated Plain-English Commentary**: Rule-based executive narrative generated per report period.
- **Dynamic Scheduler & Archive**: UI-based weekly/monthly schedule editor, execution with retry, audit history, and report library.
- **SMTP Email Delivery**: Multi-attachment report dispatch with dry-run demo mode.

---

## Phase 1 Capabilities: Realistic Data & PMS Integration
- **Realistic Simulator**: Shifts A/B/C, heat numbers (`H24-101`), pattern IDs (`PAT-BD-01`), planned vs actual, scrap vs rework, downtime reasons, OEM customers, humidity surges elevating blow holes in Foundry, and gradual degradation of `CNC-02`.
- **Connectors**: CSV/Excel upload with encoding detection, SQL via SQLAlchemy (`PMS_DATABASE_URL`), and FastAPI Mock PMS Server (`mock_pms/server.py`).
- **Column Mapping Studio**: Fuzzy header matching with built-in presets (`SAP PP Export`, `MES Shopfloor Log`).
- **Idempotent Incremental Ingestion**: SQLite central database (`smartmis.db`) with composite key duplicate prevention and ingestion audit log.
