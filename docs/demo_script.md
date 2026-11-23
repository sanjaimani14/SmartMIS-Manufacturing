# SmartMIS Hackathon Pitch & 5-Minute Timed Demo Script
**Event**: Sakthi Hackathon 2.0 (Round 2)  
**Problem Statement**: PS-005: Automated Manufacturing MIS and Rejection Report Generator  
**Team**: firstones (SKH2-2026-00275)  
**Audience**: Industry Judges & Evaluation Panel (Foundry GM, Machine Shop Head, Quality VP, Head of MIS)

---

## ⏱️ Pitch Timeline Overview (Total: 5 Minutes)
| Minute | Section | Focus & Key Takeaway |
| :---: | :--- | :--- |
| **0:00 - 0:45** | **The Industrial Problem & Hook** | 15+ hours/week wasted in manual spreadsheet compilation, latency in detecting defect spikes. |
| **0:45 - 1:45** | **Live Data Ingestion & Central Hub** | Multi-source connectors (SQL/REST/Excel), fuzzy column mapping, incremental deduplication. |
| **1:45 - 2:45** | **Advanced Quality Engineering & SPC** | OEE, Cost of Poor Quality (₹ INR), SPC p-chart with Western Electric rules, anomaly detection. |
| **2:45 - 3:45** | **YAML Templates, Excel/PDF & Scheduler** | One-click corporate Excel & signed PDF generation, automated commentary, cron email engine. |
| **3:45 - 4:30** | **Live Defect Spike & Safe AI Query** | Injecting live furnace blow hole spike with real-time alerting + "Ask Your Data" NLP query. |
| **4:30 - 5:00** | **Business ROI, Power BI & Closing** | 99.4% time reduction, ₹4.89 Lakhs annual savings, Power BI star-schema readiness. |

---

## 🎬 Minute-by-Minute Speaking Script & UI Walkthrough

### ⏱️ [0:00 - 0:45] The Industrial Problem & Hook
> *"Respected judges and industry leaders: in automotive foundries and high-precision machine shops, quality data is the lifeblood of the plant. Yet today, senior quality and MIS engineers spend over 65 hours every month manually chasing shift log sheets, copying numbers between ERPs, and compiling Excel reports.*
>
> *By the time a weekly rejection report reaches the General Manager's desk on Monday morning, the castings have already moved to the customer—or worse, furnace scrap has compounded for six full shifts.*
>
> *We built **SmartMIS**—an enterprise-grade, turnkey manufacturing intelligence and automated report generation platform designed specifically for Sakthi's foundry and machining operations. It eliminates 99.4% of manual reporting overhead while bringing real-time statistical process control right to the plant head's fingertips."*

**Action**: Display `🏠 Home & Overview` page. Point out the live system status, architecture overview, and connected databases.

---

### ⏱️ [0:45 - 1:45] Live Data Ingestion & Heterogeneous Connectors
> *"The foundation of any robust MIS is painless data integration. Shopfloors never have clean, unified column headers.
>
> Let's navigate to **🔌 PMS Import & ETL**. SmartMIS provides three ingestion channels:*
> 1. *Direct upload of heterogeneous Excel and CSV files.*
> 2. *Live relational database queries via SQLAlchemy supporting SQLite, MySQL, and Microsoft SQL Server.*
> 3. *Real-time REST streaming from machine PLCs via our built-in FastAPI gateway.*
>
> *Notice our **Column Mapping Studio**: if an operator uploads a SAP PP export or an MES shift log with obscure header names, SmartMIS uses fuzzy Levenshtein matching to instantly map them to canonical fields (`produced`, `rejected`, `heat_no`, `downtime`). Presets are saved permanently.*
>
> *Best of all, our ingestion engine is **idempotently incremental**: uploading the same shift twice will never double-count production or skew quality metrics."*

**Action**: Click `🔌 PMS Import & ETL`. Select `FastAPI Mock PMS Server`, click `Fetch Live Stream`, and show the deduplication count in the Ingestion Log.

---

### ⏱️ [1:45 - 2:45] Advanced Quality Analytics, COPQ (₹) & SPC Studio
> *"Now, let's step into the analytics engine. Traditional MIS reports just show produced vs rejected counts. SmartMIS delivers tier-1 automotive manufacturing intelligence.*
>
> *On the **📊 Executive Dashboard**, we track true **OEE (Overall Equipment Effectiveness)** broken down into Availability, Performance, and Quality. We calculate automotive **PPM**, **First-Pass Yield**, and **Plan Adherence**.*
>
> *Under **💰 Cost of Poor Quality (COPQ)**, we translate technical defects directly into financial impact in Indian Rupees (₹). Using an editable per-part scrap and rework cost matrix, the plant head instantly sees our Top 5 financial cost drivers.*
>
> *Next, on **📈 Quality Control & SPC**, we plot dynamic **p-charts** with 3-sigma Upper and Lower Control Limits. The system continuously evaluates the **Western Electric / Wheeler Rules**: Rule 1 for points beyond 3-sigma, Rule 2 for process shifts of 7 points, and Rule 3 for tool-wear drift. Below it, our MAD rolling median anomaly detector flags process deviations into CRITICAL, WARNING, and INFO alerts."*

**Action**: Navigate to `📈 Quality Control & SPC`. Hover over the dynamic UCL/LCL control lines. Scroll to the Anomaly Alerts panel.

---

### ⏱️ [2:45 - 3:45] Declarative YAML Templates, Excel/PDF & Scheduler
> *"The core mandate of PS-005 is producing industry-approved, standardized reports for Foundry, Machine Shop, and Monthly Rejection.*
>
> *Under **📑 Formal Reports**, our reports are **100% template-driven** using declarative YAML files in `reports/templates/`. Adding an entirely new report format for a new customer or line takes zero Python code—just a simple YAML file.*
>
> *Look at the outputs:*
> 1. *Our **Excel export** is formatted in corporate A4 landscape, with frozen header panes, KPI cards, conditional formatting color scales, and native OpenPyXL charts.*
> 2. *Our **PDF export** features a formal corporate header, executive summary table, embedded Matplotlib defect charts, automated commentary, and official sign-off blocks for the GM and Quality Head.*
>
> *Notice the plain-English commentary: SmartMIS automatically synthesizes what happened—e.g. 'Rejection rose 1.2 pts week-on-week, driven primarily by Blow Holes on Furnace-2 during Shift B'.*
>
> *And under **⏱ Automation Scheduler**, managers can edit dynamic cron schedules right from the UI, with automatic failure retry and multi-attachment SMTP email dispatch."*

**Action**: Navigate to `📑 Formal Reports`. Generate `Weekly Foundry Report`. Click `Download Excel (.xlsx)` and open/preview the PDF with sign-off blocks.

---

### ⏱️ [3:45 - 4:30] Live Defect Spike Injection & "Ask Your Data" AI
> *"Let's test SmartMIS in a live crisis. Let's navigate to **⚡ Live Shopfloor Stream & Defect Spike**.*
>
> *Imagine a sudden monsoon humidity surge causes severe sand mold blowholes on Furnace-2 during Shift B. I will click **'Inject Defect Spike'**.*
>
> *Notice what happens instantly:
> - A high-priority **CRITICAL Alert Banner** flashes across the entire application with root-cause diagnostics and containment instructions.
> - The live rejection rate jumps from 2.6% to 4.9%.
> - The SPC p-Chart immediately flags a Rule 1 violation with red diamond markers!*
>
> *Now, what if the plant director walks in and asks an urgent question? On the **💬 Ask Your Data** tab, users can type natural English:*
> `'Top 3 defects in Foundry'` or `'Compare rejection between Shift A and Shift B'`.
>
> *SmartMIS parses the intent using Claude API or our offline parser, strictly executes **only whitelisted analytics primitives**, and displays the exact filters, raw table, and an interactive Plotly chart with zero SQL injection risk."*

**Action**: Click `⚡ Live Shopfloor Stream & Defect Spike`, click `Inject Defect Spike Now`. Show the banner and red SPC flag. Then switch to `💬 Ask Your Data` and execute a sample prompt.

---

### ⏱️ [4:30 - 5:00] Business Value, Power BI & Closing
> *"To conclude, what is the bottom-line ROI for Sakthi?
>
> Let's look at **⏱️ Time Saved & ROI Counter**:
> - Manual report preparation drops from 68 hours a month to under 25 minutes—a **99.4% reduction in engineering overhead**.
> - That recovers **over 815 senior engineering hours per year**, translating directly to **₹4.89 Lakhs saved annually**.
> - For corporate BI, our **📊 Power BI Integration** exports clean star-schema datasets with pre-written DAX measures for instant board-level executive dashboards.
>
> *SmartMIS is fully containerized with Docker, covered by 41 passing automated tests, and completely production-ready today. Thank you!"*

**Action**: Display `⏱️ Time Saved & ROI Counter` and `✅ Requirements Checklist` (showing 17/17 requirements satisfied).
