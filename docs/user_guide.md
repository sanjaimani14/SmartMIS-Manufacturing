# SmartMIS: Comprehensive User & Operations Manual
**Sakthi Hackathon 2.0 | PS-005: Automated Manufacturing MIS and Rejection Report Generator**  
**Product Version**: 2.5.0-Enterprise | **Team**: firstones (SKH2-2026-00275)

---

## 📖 Table of Contents
1. [Overview & Key Concepts](#1-overview--key-concepts)
2. [Installation & Quick Start](#2-installation--quick-start)
3. [User Roles & Authentication (RBAC)](#3-user-roles--authentication-rbac)
4. [Shopfloor Data Ingestion & ETL](#4-shopfloor-data-ingestion--etl)
5. [Executive Dashboard & Operational KPIs](#5-executive-dashboard--operational-kpis)
6. [Statistical Process Control (SPC) & Anomaly Alerts](#6-statistical-process-control-spc--anomaly-alerts)
7. [Cost of Poor Quality (COPQ in ₹ INR)](#7-cost-of-poor-quality-copq-in--inr)
8. [Two-Week Statistical Forecasting](#8-two-week-statistical-forecasting)
9. [Hierarchical Root-Cause Drill-Down](#9-hierarchical-root-cause-drill-down)
10. [Template-Driven Report Generation & Archive](#10-template-driven-report-generation--archive)
11. [Automation Scheduler & SMTP Email Delivery](#11-automation-scheduler--smtp-email-delivery)
12. [Live Shopfloor Streaming & Defect Spike Injection](#12-live-shopfloor-streaming--defect-spike-injection)
13. ["Ask Your Data" AI Natural Language Querying](#13-ask-your-data-ai-natural-language-querying)
14. [Power BI Ecosystem Integration & DAX Guide](#14-power-bi-ecosystem-integration--dax-guide)
15. [Enterprise Settings & Security Audit Trail](#15-enterprise-settings--security-audit-trail)

---

## 1. Overview & Key Concepts
**SmartMIS** is an automated manufacturing management information system designed to bridge the operational gap between shopfloor production logging (Foundry and Machine Shop) and executive business intelligence.

Traditional reporting workflows rely on engineers manually aggregating shift logbooks into Excel, formatting tables, computing rejection percentages, and writing commentary. SmartMIS automates this entire lifecycle:
- Ingests data from CSV/Excel, SQL databases, or live PLC REST streams.
- Dynamically normalizes vendor columns with fuzzy mapping.
- Computes advanced manufacturing metrics: **OEE**, **PPM**, **First-Pass Yield**, and **Cost of Poor Quality (₹ INR)**.
- Monitors quality stability using **Statistical Process Control (SPC p-charts)** and Wheeler rules.
- Automatically generates boardroom-ready **A4 Landscape Excel workbooks** and **signed PDF deliverables** via declarative YAML templates.
- Provides a conversational **"Ask Your Data"** interface strictly sandboxed to whitelisted analytics.

---

## 2. Installation & Quick Start

### Local Python Environment
```bash
# Clone and enter directory
cd smartmis

# Install dependencies
pip install -r requirements.txt

# Run the Streamlit Application
streamlit run app.py
```
Access the application in your browser at `http://localhost:8501`.

### Live Mock PMS Server (Optional for Live Telemetry Demos)
In a separate terminal window:
```bash
cd smartmis
python -m mock_pms.server
```
Runs a FastAPI mock shopfloor gateway on `http://localhost:8001/api/pms/today`.

### Production Docker Deployment
```bash
# Launch both SmartMIS and Mock PMS services
docker compose up -d
```

---

## 3. User Roles & Authentication (RBAC)

SmartMIS enforces strict Role-Based Access Control using salted PBKDF2-HMAC-SHA256 credentials:

| Role | Default Username | Default Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **System Admin** | `admin` | `admin123` | Unrestricted plant-wide access; settings, pricing, user directory, audit log. |
| **Plant Manager** | `manager` | `manager123` | Full operational visibility across Foundry and Machine Shop; report generation, analytics, Power BI export. |
| **Foundry Operator** | `op_foundry` | `foundry123` | Strictly scoped to Foundry records. Machine Shop data is isolated. |
| **Machining Operator** | `op_machining` | `machining123` | Strictly scoped to Machine Shop records. Foundry data is isolated. |

To switch accounts, expand **👤 Logged in as: [User]** in the sidebar and click **Log out**.

---

## 4. Shopfloor Data Ingestion & ETL

Navigate to **🔌 PMS Import & ETL**:

### A. CSV / Excel Upload
1. Select the **📂 CSV / Excel Ingestion** tab.
2. Drag and drop your shopfloor production log (`.csv`, `.xlsx`, or `.xls`).
3. If headers match standard names, click **Direct Load**.
4. If your file uses proprietary column headers, open the **Column Mapping Studio**:
   - SmartMIS auto-maps fields with >80% fuzzy similarity.
   - Adjust any dropdowns (`date`, `department`, `produced`, `rejected`, etc.).
   - Click **💾 Save Mapping Preset** for instant reuse on future uploads.
5. Click **⚡ Ingest File into Central Database**.

### B. Relational SQL Database Connection
1. Select the **🗄️ Relational Database (SQL)** tab.
2. Enter your SQLAlchemy connection string (or accept the environment default `PMS_DATABASE_URL`).
3. Click **🔌 Test Connection** to verify database accessibility.
4. Select table or view, specify row limits, and click **📥 Fetch SQL Records**.

### C. Live Mock PMS REST Streaming
1. Select the **📡 Live Mock PMS Server** tab.
2. Verify the endpoint URL (`http://localhost:8001/api/pms/today`).
3. Click **🔄 Fetch Live Daily Stream**.
4. The system incrementally ingests today's batch without duplicating records.

---

## 5. Executive Dashboard & Operational KPIs

Navigate to **📊 Executive Dashboard**:
- **OEE (Overall Equipment Effectiveness)**: Availability % $\times$ Performance % $\times$ Quality %.
- **Rejection Rate %**: Metric card with dynamic color coding (Green $< 2.5\%$, Amber $2.5\% - 3.75\%$, Red $> 3.75\%$).
- **First-Pass Yield (FPY %)**: Conforming parts produced without requiring rework.
- **Defect PPM**: Automotive standard Parts Per Million ($\frac{\text{rejected}}{\text{produced}} \times 1,000,000$).
- **Smart Insights Card**: Automatically synthesizes **3 Key Findings** and **3 Prioritized Engineering Actions**.

---

## 6. Statistical Process Control (SPC) & Anomaly Alerts

Navigate to **📈 Quality Control & SPC**:
- **Dynamic 3-Sigma Control Limits**: The p-Chart calculates daily varying $\text{UCL}_i$ and $\text{LCL}_i$ accounting for daily production volume swings.
- **Western Electric / Wheeler Quality Rules**:
  - *Rule 1*: Point outside 3-sigma control limits. Highlighted with red diamond markers.
  - *Rule 2*: Run of 7 consecutive points on one side of the historical mean $\bar{p}$.
  - *Rule 3*: Trend of 6 consecutive points steadily increasing or decreasing (tool wear indicator).
- **MAD Anomaly Alerts**: Rolling median anomaly detector flags statistical deviations into `CRITICAL`, `WARNING`, and `INFO` tiers with immediate engineering containment instructions.

---

## 7. Cost of Poor Quality (COPQ in ₹ INR)

Navigate to **💰 Cost of Poor Quality (COPQ)**:
- Quantifies total rupee losses divided into unrecoverable scrap and rectification rework.
- **Editable Cost Matrix**: Adjust scrap and rework unit costs per component (e.g. Brake Drum, Hub Housing, Pump Casing) and click **💾 Save Cost Matrix**.
- **Top 5 Financial Drivers**:
  - Top 5 Products by COPQ.
  - Top 5 Defects by Financial Loss.
  - Top 5 Machines Generating Scrap.

---

## 8. Two-Week Statistical Forecasting

Navigate to **🔮 14-Day Forecasting**:
- Employs **Statsmodels Holt-Winters Exponential Smoothing** with damped additive trend modeling.
- Generates 14-day forward projections for daily production output and rejection trajectory.
- Displays **95% Confidence Interval cones** enabling proactive capacity and quality planning.

---

## 9. Hierarchical Root-Cause Drill-Down

Navigate to **🔍 Root-Cause Drill-Down**:
- Interactive 5-level operational drill-down hierarchy:
  $$\text{Department} \longrightarrow \text{Machine} \longrightarrow \text{Shift} \longrightarrow \text{Defect Category} \longrightarrow \text{Heat Lot}$$
- Selecting any node dynamically recalculates metrics and reveals the underlying batch records for precise metallurgical tracebacks.

---

## 10. Template-Driven Report Generation & Archive

Navigate to **📑 Formal Reports**:
1. Select an approved template:
   - `Weekly Foundry Report`
   - `Weekly Machine Shop Report`
   - `Monthly Rejection Report`
2. Review the automated plain-English commentary synthesized for the active period.
3. Click **⬇ Download Excel (.xlsx)** for an A4 Landscape spreadsheet with frozen panes, KPI summary, and native charts.
4. Click **⬇ Download PDF Report** for a boardroom-ready deliverable with sign-off blocks.
5. Click **📄 Executive Summary (1-Page PDF)** for a dense, single-page GM digest.

All generated reports are automatically preserved in the **📂 Report Archive** with timestamped records and SHA-256 integrity hashes.

---

## 11. Automation Scheduler & SMTP Email Delivery

Navigate to **⏱ Automation Scheduler**:
- Configure dynamic cron frequencies for Weekly and Monthly report runs directly from the UI.
- Trigger manual execution with retry logic (`Run Automation Now`).
- Monitor execution audit history (Status, Duration, Files Generated).
- Deliver multi-attachment reports via SMTP with support for a safe `dry_run` demonstration mode.

---

## 12. Live Shopfloor Streaming & Defect Spike Injection

Navigate to **⚡ Live Shopfloor Stream & Defect Spike**:
- **Simulate Production Batch**: Click **▶ Simulate Next Production Batch (5 records)** to simulate incoming shift lots.
- **Defect Spike Injection**:
  - Select *🚨 Sudden Blow Hole Porosity (Furnace-2, Shift B)* or *⚠️ Tool Offset Drift (CNC-02, Shift C)*.
  - Click **⚡ Inject Defect Spike Now**.
  - A real-time **CRITICAL Alert Banner** flashes across the entire application, the rejection rate spikes, and the SPC p-chart highlights Rule 1 violations in red.
- **Reset State**: Click **↺ Reset to Baseline** to restore normal operational data.

---

## 13. "Ask Your Data" AI Natural Language Querying

Navigate to **💬 Ask Your Data**:
- Type natural questions into the query bar:
  - *"Top 3 defects in Foundry"*
  - *"Monthly rejection trend"*
  - *"Compare rejection between Shift A and Shift B"*
  - *"What was the total scrap for Brake Drum?"*
- Powered by the Anthropic Claude API (when `ANTHROPIC_API_KEY` is configured) or the intelligent offline regex intent parser.
- Strictly executes only whitelisted functions (`top_n`, `trend`, `compare`, `filter`, `kpi`) with zero arbitrary code execution.
- Displays the transparent filters applied, the generated data table, and interactive Plotly figures.

---

## 14. Power BI Ecosystem Integration & DAX Guide

Navigate to **📊 Power BI Integration**:
- Click **⬇ Download `powerbi_manufacturing_model.csv`** to generate a clean star-schema dimensional dataset with calendar dates, weeks, and months.
- Follow the integrated DAX Measure Guide to paste production formulas for Plant OEE, Rejection %, and Plan Adherence into Power BI Desktop.

---

## 15. Enterprise Settings & Security Audit Trail

Navigate to **⚙️ Enterprise Settings** (Admin Access Only):
- **Plant Targets & Branding**: Configure plant company name and rejection target thresholds.
- **User Directory**: View registered enterprise accounts and role allocations.
- **Security Audit Trail**: Inspect the immutable `action_audit_log` detailing all user actions, report exports, and system settings modifications.
