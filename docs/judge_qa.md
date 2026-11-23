# SmartMIS Technical & Domain Judge Q&A Guide
**Sakthi Hackathon 2.0 | PS-005: Automated Manufacturing MIS and Rejection Report Generator**  
**Team**: firstones (SKH2-2026-00275)

This document prepares the presentation team for the 25 most rigorous, probing questions expected from industry panel judges across Foundry, Machine Shop, Quality Assurance, IT/MIS, and Plant Operations.

---

### Section 1: Data Integration, Shopfloor Ingestion & Edge Connectivity

#### Q1: "How does SmartMIS handle real-time PMS data when shopfloor connectivity drops or is intermittent?"
> **Answer**: SmartMIS implements an **idempotent incremental buffer pattern**. When edge connectivity is interrupted, shopfloor PLCs or local edge nodes buffer records locally. Once restored, batch uploads or API streams are transmitted with composite natural keys (`date + department + machine + shift + heat_no + product`). The ingestion engine uses SQL `INSERT OR IGNORE` logic with an active hash index. If 500 records are re-sent, SmartMIS commits only the unrecorded deltas, records an entry in `ingestion_log`, and completely avoids duplicate counts or skewed KPIs.

#### Q2: "In real factories, machine operators frequently rename spreadsheet headers. How does your column-mapping studio handle this?"
> **Answer**: In `smartmis/data.py`, we implement a **fuzzy Levenshtein distance matching heuristic** across canonical field synonyms. For example, headers like `Rej_Count`, `Total_Scrap`, `Defect_Qty`, or `Non_Conforming` are automatically scored against `CANONICAL_COLUMNS["rejected"]`. If confidence exceeds 80%, SmartMIS auto-maps them. Operators can manually adjust mappings via the UI and save them as named presets (e.g. *'DISA Moulding Line Log'* or *'SAP PP Daily Dump'*), which persist into `column_mapping_presets.json` for one-click re-use.

#### Q3: "What relational databases can SmartMIS connect to, and how are database credentials managed?"
> **Answer**: SmartMIS uses **SQLAlchemy** as an abstraction layer. By setting the standard environment variable `PMS_DATABASE_URL`, SmartMIS connects out-of-the-box to **SQLite**, **PostgreSQL**, **MySQL/MariaDB**, or **Microsoft SQL Server** (via `pyodbc` or `pymssql`). Credentials are strictly injected at runtime from `.env` or system environment variables—never committed to source control.

#### Q4: "How do you handle character encoding issues (like UTF-8 vs Windows-1252/cp1252) often found in older CNC export files?"
> **Answer**: In `read_uploaded_file()` within `smartmis/data.py`, SmartMIS employs a **fallback decoding strategy**: it first attempts standard `utf-8-sig` (handling Excel UTF-8 BOM headers), and if a `UnicodeDecodeError` is caught, it falls back to `latin-1` / `cp1252`. For Excel workbooks, both modern `.xlsx` (OpenPyXL) and legacy `.xls` formats are handled seamlessly.

---

### Section 2: Quality Engineering, SPC & Statistical Methodology

#### Q5: "How does your SPC p-chart handle varying daily subgroup sizes ($n_i$)?"
> **Answer**: In manufacturing plants, daily production volume is never constant. A naive fixed UCL/LCL control limit is statistically invalid. SmartMIS computes **dynamic binomial control limits per individual subgroup $i$**:
> $$\text{UCL}_i = \bar{p} + 3\sqrt{\frac{\bar{p}(1-\bar{p})}{n_i}}, \quad \text{LCL}_i = \max\left(0, \bar{p} - 3\sqrt{\frac{\bar{p}(1-\bar{p})}{n_i}}\right)$$
> where $\bar{p} = \frac{\sum \text{rejected}_i}{\sum \text{produced}_i}$. On high-volume production days, the control band narrows; on low-volume runs, it widens legitimately, preventing false-positive special cause alarms.

#### Q6: "Which Western Electric / Wheeler out-of-control rules are implemented?"
> **Answer**: In `smartmis/kpis.py`, the SPC engine checks three standard quality engineering rules:
> 1. **Rule 1 (Special Cause Spike)**: Any single day where non-conformance exceeds $\text{UCL}_i$ or falls below $\text{LCL}_i$.
> 2. **Rule 2 (Process Shift / Bias)**: A run of 7 consecutive points on one side of the historical centerline ($\bar{p}$).
> 3. **Rule 3 (Wear / Drift Trend)**: A sequence of 6 consecutive points steadily increasing or steadily decreasing (critical for detecting furnace refractory lining erosion or CNC tool wear).

#### Q7: "Why did you use Median Absolute Deviation (MAD) for anomaly detection instead of standard standard deviation ($z$-score)?"
> **Answer**: In industrial rejection datasets, extreme defect outbreaks (such as a 30% blowhole surge) dramatically distort the empirical mean ($\mu$) and standard deviation ($\sigma$). This leads to the **masking effect**, where subsequent anomalies go undetected. SmartMIS uses the robust non-parametric MAD metric:
> $$\text{MAD} = \text{median}(|x_i - \tilde{x}|), \quad z_{\text{robust}} = \frac{0.6745 \cdot (x_i - \tilde{x})}{\text{MAD}}$$
> This ensures outlier resistance up to a 50% breakdown point, classifying deviations into CRITICAL ($z > 3.0$), WARNING ($2.0 \le z \le 3.0$), and INFO tiers.

#### Q8: "How does SmartMIS forecast production and rejection rates, and how do you prevent negative rejection forecasts?"
> **Answer**: SmartMIS utilizes **Statsmodels Holt-Winters Exponential Smoothing** (`ExponentialSmoothing`) with additive damped trend modeling (`damping_trend=0.85`). For daily rejection rates, we project forward 14 days and generate 95% confidence intervals based on residual variance, strictly clipping negative lower bounds at $0.0\%$ to ensure physically meaningful forecasts.

---

### Section 3: Financial Analytics & Cost of Poor Quality (COPQ)

#### Q9: "How is Cost of Poor Quality (COPQ in ₹ INR) calculated, and can the plant finance team adjust unit costs?"
> **Answer**: COPQ is calculated by separating non-conforming items into **Scrap** (unrecoverable loss) and **Rework** (rectification labor/tooling loss):
> $$\text{COPQ} = \sum_{\text{parts}} \left( \text{Scrap Qty} \times \text{Cost}_{\text{scrap}} + \text{Rework Qty} \times \text{Cost}_{\text{rework}} \right)$$
> Unit costs are managed through an editable interactive table in the UI (`smartmis/copq_costs.json`). For instance, a Brake Drum is configured at ₹450 scrap and ₹95 rework. Finance or plant controllers can update unit costs at any time without engineering assistance.

#### Q10: "Can SmartMIS identify the Top 5 financial cost drivers instead of just part counts?"
> **Answer**: Yes. Volume Pareto and Financial Pareto are often very different. In `compute_copq()` (`smartmis/kpis.py`), SmartMIS calculates three Top 5 financial breakdowns: Top 5 products by COPQ, Top 5 defects by rupee loss, and Top 5 machines generating the highest financial loss. This allows plant leadership to prioritize capital expenditure where rupee leakage is highest.

---

### Section 4: Report Automation, Templates & Deliverables

#### Q11: "Why did you choose declarative YAML templates for reports instead of hardcoding layouts in Python?"
> **Answer**: Automotive tier-1 suppliers serve multiple OEMs (e.g. Tata, Mahindra, Brembo), each requiring distinct weekly and monthly report headers, specific KPI bands, and customized defect groupings. Hardcoding layouts into Python code introduces regression risks. With our YAML engine (`reports/templates/*.yaml`), adding an approved format requires only defining a new YAML file specifying sections, columns, KPIs, and chart types. SmartMIS dynamically discovers and renders it with zero code changes.

#### Q12: "How are the Excel files formatted? Are they just raw data dumps?"
> **Answer**: No. SmartMIS uses **OpenPyXL** to engineer boardroom-ready spreadsheets:
> - Configured in **A4 Landscape** with active print area boundaries and fit-to-page scaling.
> - Sticky frozen panes ensuring headers remain visible during navigation.
> - High-density executive KPI summary band across rows 4–6.
> - Two-color conditional formatting (Green to Red gradient) highlighting high-rejection cells.
> - Native embedded OpenPyXL bar charts linked directly to sheet data formulas.

#### Q13: "What safety features exist in the automated email delivery system to prevent accidental emails during demos?"
> **Answer**: In `smartmis/reports.py`, `send_report_email()` features an explicit `dry_run` flag. When running in development, testing, or hackathon demo mode, emails are simulated with full MIME multi-attachment assembly, logged to the application console and audit trail, but bypassed over the network. Real dispatch activates seamlessly when standard SMTP credentials are provided.

---

### Section 5: AI Natural Language Querying & Security Sandboxing

#### Q14: "How do you prevent SQL injection or arbitrary code execution in the 'Ask Your Data' tab?"
> **Answer**: SmartMIS implements a **strict whitelist execution architecture** (`smartmis/nlp_query.py`). Under no circumstances is LLM output passed to `eval()`, `exec()`, or raw SQL `execute()`. The query parser (Claude API or offline regex) maps the prompt strictly to a JSON payload matching one of 5 whitelisted operational primitives:
> - `top_n`: Top $N$ products/defects by count or scrap
> - `trend`: Daily/weekly chronological resampled metric
> - `compare`: Category A vs Category B (e.g. Shift A vs Shift B)
> - `filter`: Scoped dimensional query
> - `kpi`: Direct mathematical metric retrieval
> Any payload specifying unknown functions or arbitrary syntax is rejected with a validation error.

#### Q15: "What happens if there is no internet connection or no Anthropic API key?"
> **Answer**: SmartMIS includes an intelligent, rule-based offline natural language parser built with regex patterns and semantic keyword extractors. It recognizes queries like *"Top 3 defects in Foundry"*, *"Monthly rejection trend"*, and *"Compare Shift A and Shift B"* with zero external dependencies and sub-millisecond execution latency.

---

### Section 6: Security, Role-Based Access Control & Auditing

#### Q16: "How does Role-Based Access Control (RBAC) restrict shopfloor operators?"
> **Answer**: In `smartmis/auth.py`, SmartMIS provides three standard enterprise roles:
> 1. **Admin**: Complete system visibility, quality target editing, COPQ cost modification, schedule frequency, and audit inspection.
> 2. **Manager**: Cross-departmental operational visibility, report generation, analytics, and Power BI export.
> 3. **Operator**: Hard-filtered departmental view. A Foundry Operator can only query, view, and inspect Foundry records; Machine Shop records are stripped at the data layer before rendering.

#### Q17: "How are passwords stored and verified?"
> **Answer**: Passwords are never stored in plaintext. SmartMIS utilizes salted **PBKDF2-HMAC-SHA256** with 100,000 hashing rounds and cryptographically secure 16-byte random salts generated via Python's `secrets` module, preventing rainbow table attacks.

#### Q18: "What information is captured in your security audit trail?"
> **Answer**: The SQLite `action_audit_log` table immutably logs every significant action: timestamp, username, user role, action type (e.g. `LOGIN`, `GENERATE_REPORT`, `DOWNLOAD_REPORT`, `DATA_INGESTION`, `CHANGE_SETTINGS`), and a detailed summary of the action.

---

### Section 7: Industrial Deployment, Power BI & Business ROI

#### Q19: "How does SmartMIS integrate with enterprise Microsoft Power BI deployments?"
> **Answer**: Under `smartmis/executive.py`, SmartMIS provides a one-click star-schema export: `powerbi_manufacturing_model.csv`. This dataset includes pre-joined calendar dimensions (`year`, `month_name`, `week_number`, `day_name`) and calculated non-conformance metrics. Furthermore, the UI provides copy-paste production **DAX measures** for Plant OEE, Rejection %, Total COPQ (₹), and Plan Adherence matching Sakthi's Round 1 proposal.

#### Q20: "Can SmartMIS run on an on-premise industrial server inside our factory firewall?"
> **Answer**: Yes. SmartMIS includes a production `Dockerfile` and `docker-compose.yml`. It has zero cloud dependencies, requires no external SaaS subscriptions, and can be deployed on a local Linux or Windows edge server with a single command: `docker compose up -d`.

#### Q21: "What is the measured reduction in reporting time?"
> **Answer**: Based on standard tier-1 automotive manufacturing benchmarks:
> - Weekly Foundry Report: 180 min manual $\rightarrow$ 30 sec automated
> - Weekly Machine Shop Report: 150 min manual $\rightarrow$ 30 sec automated
> - Monthly Rejection MIS: 420 min manual $\rightarrow$ 60 sec automated
> - Daily Shift Ingestion: 45 min/shift $\times$ 60 shifts = 2,700 min $\rightarrow$ 12 min automated
> Total manual reporting overhead drops from **68.3 hours/month to 0.4 hours/month**—an overall **99.4% reduction in engineering effort**, saving **over 815 engineer hours annually**.

#### Q22: "What is the annual financial saving for Sakthi?"
> **Answer**: Assuming a loaded cost of ₹600/hour for senior quality and MIS engineers, saving 815 hours per year yields direct annual payroll bandwidth recovery of **₹4,89,000 per plant line**, in addition to preventing scrap compounding through real-time defect spike alerts.

#### Q23: "How does the system simulate realistic seasonal effects like monsoon humidity?"
> **Answer**: In `smartmis/data.py`, our simulator incorporates a sinusoidal seasonal model simulating diurnal temperature and monsoon humidity surges (relative humidity reaching 75%–90%). When humidity spikes, green sand mold moisture increases, triggering a mathematically modelled surge in Foundry blow hole gas porosity, reflecting real-world casting metallurgy.

#### Q24: "How does the machine degradation model work?"
> **Answer**: The simulator progressively degrades machine `CNC-02` across the operational period. As tool tip wear and spindle bearing runout accumulate, dimensional defects (*Tool Marks*, *Oversize*, and *Undersize*) gradually escalate over 30 days, providing authentic data for our Wheeler Rule 3 trend detector.

#### Q25: "How thorough is your automated test suite?"
> **Answer**: The project includes 41 automated pytest test cases covering schema integrity, seasonal humidity simulation, machine degradation, column mapping heuristics, incremental load idempotency, SQL connectors, FastAPI client, YAML template validation, Excel/PDF generation, SMTP dry-run, scheduler persistence, advanced KPIs & OEE, COPQ calculations, SPC p-chart limits, Wheeler rules, MAD anomaly z-scores, Statsmodels 14-day forecasts, multi-level drill-down, RBAC scoping, audit logging, whitelisted NLP queries, 1-page PDF generation, Power BI export, streaming batch generation, defect spike injection, and ROI calculations.
