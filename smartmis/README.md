# SmartMIS: Automated Manufacturing MIS & Rejection Report Generator
[![Sakthi Hackathon 2.0](https://img.shields.io/badge/Sakthi%20Hackathon%202.0-PS--005-orange.svg)](https://github.com/sanjaimani14/SmartMIS-Manufacturing)
[![CI Tests](https://img.shields.io/badge/CI%20Suite-41%2F41%20Passing-brightgreen.svg)](https://github.com/sanjaimani14/SmartMIS-Manufacturing)
[![Python Version](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![UI Framework](https://img.shields.io/badge/UI-Streamlit%20Multi--Page-FF4B4B.svg)](https://streamlit.io/)
[![Container](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE)

> **Event**: Sakthi Hackathon 2.0 (Round 2)  
> **Problem Statement**: PS-005 "Automated Manufacturing MIS and Rejection Report Generator"  
> **Theme**: Data Analytics, MIS and BI  
> **Team**: firstones (SKH2-2026-00275)

---

## 🚀 Quick Start
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the Streamlit Application
streamlit run app.py

# 3. (Optional) Run the Mock PMS REST API Server
python -m mock_pms.server
```

## 🧪 Running Pytest Suite
```bash
python -m pytest tests -v
```

---

## 👥 Enterprise User Accounts (RBAC)
- **Admin**: `admin` / `admin123` (Full plant-wide control, settings, COPQ pricing, audit log)
- **Manager**: `manager` / `manager123` (Foundry & Machine Shop operational visibility, reports, Power BI export)
- **Foundry Operator**: `op_foundry` / `foundry123` (Foundry department only)
- **Machining Operator**: `op_machining` / `machining123` (Machine Shop department only)

---

## 📚 Documentation & Deliverables
- 🏗️ [**Architecture Blueprint**](../docs/architecture.png)
- 🎬 [**5-Minute Hackathon Demo Script**](../docs/demo_script.md)
- 💡 [**25 Technical & Domain Judge Q&A**](../docs/judge_qa.md)
- 📘 [**Comprehensive Operations Manual**](../docs/user_guide.md)
- 📸 [**Screenshots Directory**](screenshots/)
- 📑 [**Generated Sample Reports**](sample_reports/)
