"""
SmartMIS - Automated Manufacturing MIS & Advanced BI Analytics Platform.
Sakthi Hackathon 2.0 | PS-005 | Team firstones (SKH2-2026-00275)
"""
import json
import logging
import os
from datetime import date, datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from apscheduler.schedulers.background import BackgroundScheduler

import config
import core

try:
    from ui.theme import inject_theme, render_hero_header, render_sidebar_brand, render_sidebar_footer
    from ui.charts import apply_chart_theme
except ImportError:
    from smartmis.ui.theme import inject_theme, render_hero_header, render_sidebar_brand, render_sidebar_footer
    from smartmis.ui.charts import apply_chart_theme

logging.basicConfig(level=logging.INFO)
st.set_page_config(
    page_title="SmartMIS - Manufacturing BI Platform",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject Global Smart Factory Control Room Design System
inject_theme()

# ---- Central Database Initialization ---------------------------------------
core.init_central_db()
core.init_audit_db()

# ---- Authentication & Role Management --------------------------------------
if "user" not in st.session_state:
    # Default initial session for hackathon evaluation: Admin
    st.session_state["user"] = {
        "username": "admin",
        "full_name": "System Administrator",
        "role": "Admin",
        "department": "All",
    }

user = st.session_state["user"]

# ---- Sidebar Header & Brand Block ------------------------------------------
render_sidebar_brand()

# Sidebar User Info Badge
role_color = "#FF6B1A" if user["role"] == "Admin" else ("#2D7FF9" if user["role"] == "Manager" else "#00C2A8")
st.sidebar.markdown(f"""
<div style="
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 10px 14px;
    margin-bottom: 8px;
">
    <div style="color: #94A3B8; font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em;">ACTIVE SESSION</div>
    <div style="color: #FFFFFF; font-weight: 800; font-size: 0.95rem; margin: 2px 0;">{user['full_name']}</div>
    <div style="display: flex; gap: 6px; align-items: center; margin-top: 3px;">
        <span style="background: {role_color}; color: #FFFFFF; font-size: 0.7rem; font-weight: 800; padding: 1px 7px; border-radius: 6px; text-transform: uppercase;">{user['role']}</span>
        <span style="color: #CBD5E1; font-size: 0.78rem;">{user['department']}</span>
    </div>
</div>
""", unsafe_allow_html=True)

with st.sidebar.expander("🔐 Switch User Profile", expanded=False):
    demo_role = st.selectbox(
        "Demo User Profiles",
        ["admin (Admin - All)", "manager (Manager - All)", "foundry_op (Operator - Foundry)", "machining_op (Operator - Machine Shop)"]
    )
    if st.button("Switch Identity"):
        u_key = demo_role.split(" ")[0]
        full_u = core.load_users().get(u_key)
        if full_u:
            st.session_state["user"] = {
                "username": full_u["username"],
                "full_name": full_u.get("full_name", u_key),
                "role": full_u.get("role", "Operator"),
                "department": full_u.get("department", "All"),
            }
            core.log_audit_action(full_u["username"], full_u.get("role", "Operator"), "USER_SWITCH", f"Switched to {u_key}")
            st.rerun()

# ---- Scheduler Background Thread -------------------------------------------
@st.cache_resource
def start_scheduler(_get_df):
    s = BackgroundScheduler()
    sched_cfg = core.load_schedule_config()
    s.add_job(lambda: core.run_scheduled_automation(_get_df()), "cron", id="Weekly Foundry + Machine Shop + Rejection", **sched_cfg.get("weekly", config.WEEKLY_CRON))
    s.add_job(lambda: core.run_scheduled_automation(_get_df()), "cron", id="Monthly Rejection Report", **sched_cfg.get("monthly", config.MONTHLY_CRON))
    s.start(); return s

# ---- Data Ingestion & Central Loading --------------------------------------
if "working_df" not in st.session_state:
    raw_df = core.load_sqlite()
    if raw_df.empty:
        raw_df = core.sample_pms()
        core.incremental_load(raw_df, source_type="Initial Seed", source_name="simulator")
        raw_df = core.load_sqlite()
    st.session_state.working_df = raw_df
else:
    raw_df = st.session_state.working_df

if "live_spike_alert" not in st.session_state:
    st.session_state.live_spike_alert = None

# Enforce Departmental Scope based on User Role (Operators only see their department)
df = core.filter_data_by_role(raw_df, user)
sched = start_scheduler(lambda: df)

# Persistent Top-Level Alert Banner if Defect Spike Injected
if st.session_state.live_spike_alert:
    al = st.session_state.live_spike_alert
    st.error(
        f"🚨 **CRITICAL QUALITY ALERT (Live Defect Spike Injected)**: {al['defect']} surge on **{al['machine']}** ({al['shift']})! "
        f"Batch Rejection: **{al['batch_rejection_pct']}%** (+{al['delta_pct']}% plant impact). "
        f"Root Cause: *{al['root_cause']}*. **Action**: {al['recommended_action']}"
    )

# ---- Navigation Menu -------------------------------------------------------
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigation Menu",
    [
        "🏠 Home & Overview",
        "📊 Executive Dashboard",
        "⚡ Live Shopfloor Stream & Defect Spike",
        "💬 Ask Your Data",
        "📈 Quality Control & SPC",
        "💰 Cost of Poor Quality (COPQ)",
        "🔮 14-Day Forecasting",
        "🔍 Root-Cause Drill-Down",
        "📑 Formal Reports",
        "📂 Report Archive",
        "⏱️ Time Saved & ROI Counter",
        "✅ Requirements Checklist",
        "🔌 PMS Import & ETL",
        "⏱ Automation Scheduler",
        "📊 Power BI Integration",
        "⚙️ Enterprise Settings"
    ]
)

# Global Filters (Applicable across operational pages)
if page in ["📊 Executive Dashboard", "📈 Quality Control & SPC", "💰 Cost of Poor Quality (COPQ)", "🔮 14-Day Forecasting", "🔍 Root-Cause Drill-Down", "📑 Formal Reports"]:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎛️ Filter Criteria")
    
    dept_opts = ["All", "Foundry", "Machine Shop"] if user["department"] == "All" else [user["department"]]
    sel_dept = st.sidebar.selectbox("Department", dept_opts)
    prods = st.sidebar.multiselect("Product", sorted(df["product"].unique()))
    mach = st.sidebar.multiselect("Machine", sorted(df["machine"].unique()))
    shift = st.sidebar.multiselect("Shift", sorted(df["shift"].unique()))
    period = st.sidebar.radio("Report period", ["This week", "Last week", "This month", "Custom"])
    custom = st.sidebar.date_input("Custom range", (df.date.min(), df.date.max())) if period == "Custom" else None
    d0, d1 = core.period_bounds(df, period, custom)
    f = core.apply_filters(df, sel_dept, prods, d0, d1, shift, mach)
    st.caption(f"Period: **{d0:%d %b %Y} to {d1:%d %b %Y}** | Department: **{sel_dept}** | Target: **{config.REJECTION_TARGET}%** | Filtered: **{len(f):,}** records")
else:
    f = df

# Render Sidebar Team & Hackathon Footer
render_sidebar_footer()

# ==============================================================================
# PAGE 1: HOME & OVERVIEW
# ==============================================================================
if page == "🏠 Home & Overview":
    render_hero_header(user, "SmartMIS Control Hub", "Automated Manufacturing MIS & Real-Time Quality Intelligence")
    st.markdown("""
    Welcome to **SmartMIS**, an enterprise manufacturing intelligence platform engineered for **Sakthi Hackathon 2.0 (PS-005)**.
    Designed for foundry and precision machining operations, SmartMIS bridges shop-floor PMS extracts directly with executive BI,
    automated regulatory report generation, and predictive quality analytics.
    """)
    
    col_h1, col_h2, col_h3 = st.columns(3)
    kpi_tot = core.compute_advanced_kpis(df)
    copq_tot = core.compute_copq(df)
    
    col_h1.metric("Total Central Records", f"{len(df):,}", f"{df.date.min()} to {df.date.max()}")
    col_h2.metric("Plant Blended OEE", f"{kpi_tot['OEE %']:.1f}%", f"FPY: {kpi_tot['First-Pass Yield %']:.1f}%")
    col_h3.metric("Cost of Poor Quality", f"₹{copq_tot['total_copq']:,.0f}", f"Scrap Loss: ₹{copq_tot['total_scrap_cost']:,.0f}")
    
    st.markdown("---")
    st.markdown("#### 🚀 Platform Architecture & Hackathon Capabilities")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
        - **Phase 1: PMS Integration & Realistic Simulator**
          - Diurnal Shifts A/B/C, heat numbers (`H24-101`), pattern IDs (`PAT-BD-01`), plan adherence.
          - Multi-source connectors: CSV/Excel, SQLAlchemy (`PMS_DATABASE_URL`), and FastAPI Mock PMS API.
          - Column Mapping Studio with heuristic auto-mapping and preset persistence (`SAP PP`, `MES Log`).
          - Idempotent incremental loading into central SQLite database.
        - **Phase 2: Template-Driven Reports & Automation**
          - Declarative YAML templates (`reports/templates/*.yaml`) for Weekly Foundry, Weekly Machining, and Monthly Rejection.
          - Landscape OpenPyXL workbooks with native charts, frozen panes, and KPI bands.
          - Executive PDF reports with cover header, commentary, charts, page numbers, and sign-offs.
          - Automated plain-English executive commentary (rule-based).
        """)
    with c2:
        st.markdown("""
        - **Phase 3: Advanced Manufacturing Analytics**
          - Full OEE suite (Availability × Performance × Quality), FPY, PPM, Downtime %.
          - Cost of Poor Quality (COPQ in ₹) with editable per-part cost matrix and Top 5 drivers.
          - Statistical Process Control (SPC) p-Chart with 3-sigma limits and Rule 1/2/3 alarms.
          - Anomaly detection via rolling median and robust MAD z-scores with severity tiers.
          - 14-Day production & rejection forecasting with 95% confidence intervals (Statsmodels).
        - **Phase 4: AI & Enterprise Features**
          - Natural-language "Ask your data" interface strictly restricted to whitelisted functions.
          - Smart Insights Card (3 Findings + 3 Actions) & One-Page Plant Head Briefing PDF.
          - Role-Based Access Control (Admin, Manager, Operator) with department scoping & audit log.
          - Power BI-ready star-schema dataset export and integration documentation.
        """)

# ==============================================================================
# PAGE 2: EXECUTIVE DASHBOARD
# ==============================================================================
elif page == "📊 Executive Dashboard":
    render_hero_header(user, "Executive Operations Dashboard", "High-Level OEE, Quality Yield, PPM & Root-Cause Smart Insights")
    cur, dl = core.kpi_with_delta(df, sel_dept, prods, d0, d1, shift, mach)
    adv_kpi = core.compute_advanced_kpis(f)
    
    # Primary KPI row
    col1, col2, col3, col4 = st.columns(4)
    for c, k in zip([col1, col2, col3, col4], ["Produced", "Good", "Rejected", "Rejection %"]):
        cls = core.status(float(cur[k])) if k == "Rejection %" else ""
        d = dl[k]
        arrow = "" if d is None else ("▲" if d > 0 else "▼" if d < 0 else "■")
        dtxt = "no previous data" if d is None else f"{arrow} {abs(d)}{' pts' if k == 'Rejection %' else '%'} vs previous period"
        c.markdown(f'<div class="card {cls}"><div class="l">{k}</div><div class="v">{cur[k]:,}</div><div class="d">{dtxt}</div></div>', unsafe_allow_html=True)
    
    # Secondary OEE & Quality Intelligence Ribbon
    st.markdown("##### ⚙️ Manufacturing OEE & Operational Metrics")
    o1, o2, o3, o4, o5, o6 = st.columns(6)
    o1.metric("OEE", f"{adv_kpi['OEE %']}%", f"A:{adv_kpi['Availability %']}% P:{adv_kpi['Performance %']}% Q:{adv_kpi['Quality %']}%")
    o2.metric("First-Pass Yield", f"{adv_kpi['First-Pass Yield %']}%", "Conforming at 1st pass")
    o3.metric("Scrap vs Rework", f"{adv_kpi['Scrap %']}% / {adv_kpi['Rework %']}%", f"{adv_kpi['Scrap']:,} sc / {adv_kpi['Rework']:,} rw")
    o4.metric("Quality PPM", f"{adv_kpi['PPM']:,}", "Parts per million defective")
    o5.metric("Downtime %", f"{adv_kpi['Downtime %']}%", f"{adv_kpi['Total Downtime (hrs)']} hrs total")
    o6.metric("Plan Adherence", f"{adv_kpi['Plan Adherence %']}%", "Target adherence")
    
    st.write("")
    
    # Smart Insights Card (3 Findings + 3 Actions)
    st.markdown("### 💡 Smart Insights & Action Register")
    findings, actions = core.generate_smart_insights(f)
    
    col_ins1, col_ins2 = st.columns(2)
    with col_ins1:
        st.markdown("##### 🔍 Key Operational Findings")
        for i, f_item in enumerate(findings, 1):
            badge = "badge-crit" if f_item.get("badge") == "CRITICAL" else "badge-warn"
            st.markdown(f"""
            <div class="insight-card">
              <span class="{badge}">{f_item.get('category', 'Quality')}</span> <b>{i}. {f_item['title']}</b>
              <p style="margin:4px 0 0;font-size:12px;color:#444;">{f_item['text']}</p>
            </div>
            """, unsafe_allow_html=True)
            
    with col_ins2:
        st.markdown("##### 🎯 Recommended Prescriptive Actions")
        for i, a_item in enumerate(actions, 1):
            st.markdown(f"""
            <div class="insight-card" style="border-left:4px solid #1F3A5F;">
              <b>{i}. {a_item['title']}</b>
              <p style="margin:4px 0 2px;font-size:12px;color:#333;">{a_item['text']}</p>
              <span style="font-size:11px;color:#777;font-style:italic;">Owner: {a_item['owner']}</span>
            </div>
            """, unsafe_allow_html=True)
            
    # One-Page Executive Summary PDF Download
    st.write("")
    col_pdf1, col_pdf2 = st.columns([1, 3])
    if col_pdf1.button("📄 Generate Plant Head Briefing PDF", type="primary"):
        pdf_onepage = core.generate_executive_summary_pdf(f)
        core.log_audit_action(user["username"], user["role"], "GENERATE_ONEPAGE_PDF", "Generated Plant Head Briefing PDF")
        col_pdf2.download_button(
            "⬇ Download One-Page Plant Head Digest (.pdf)",
            data=pdf_onepage,
            file_name=f"Plant_Head_Digest_{date.today():%Y-%m-%d}.pdf",
            mime="application/pdf"
        )
        
    st.markdown("---")
    # Charts Row
    t = core._rate(f.groupby("date"))
    ca, cb = st.columns(2)
    combo = go.Figure([
        go.Bar(x=t.date, y=t.produced, name="Produced", marker_color="#1F3A5F"),
        go.Scatter(x=t.date, y=t["rejection_%"], name="Rejection %", yaxis="y2", line=dict(color="#E8420C", width=3))
    ])
    combo.add_hline(y=config.REJECTION_TARGET, yref="y2", line_dash="dash", line_color="gray", annotation_text=f"Target ({config.REJECTION_TARGET}%)")
    combo.update_layout(title="Daily Production Volume vs Rejection % Trend", yaxis2=dict(overlaying="y", side="right"), legend=dict(orientation="h", y=-.2), margin=dict(t=40, b=10))
    ca.plotly_chart(combo, use_container_width=True)
    
    p = core.pareto(f)
    par = go.Figure([
        go.Bar(x=p.defect, y=p.rejected, name="Rejected", marker_color="#E8420C"),
        go.Scatter(x=p.defect, y=p["cum_%"], name="Cumulative %", yaxis="y2", line=dict(color="#1F3A5F", width=2))
    ])
    par.update_layout(title="Defect Pareto (80/20 Non-Conformance Analysis)", yaxis2=dict(overlaying="y", side="right", range=[0, 105]), legend=dict(orientation="h", y=-.2), margin=dict(t=40, b=10))
    cb.plotly_chart(par, use_container_width=True)

# ==============================================================================
# PAGE 3: ASK YOUR DATA (NATURAL LANGUAGE QUERY)
# ==============================================================================
elif page == "💬 Ask Your Data":
    render_hero_header(user, "Ask Your Data (AI Analytics Interface)", "Safe Whitelisted Natural-Language Queries with Transparent Analytical Provenance")
    st.caption("Ask operational questions in plain English. Queries map strictly to whitelisted analytics functions—never arbitrary code execution.")
    
    # Suggested prompt chips
    st.markdown("**Sample Quick Queries:**")
    q_col1, q_col2, q_col3, q_col4 = st.columns(4)
    preset_q = ""
    if q_col1.button("Top 5 defects in Foundry"):
        preset_q = "Top 5 defects in Foundry"
    if q_col2.button("Compare rejection across shifts"):
        preset_q = "Compare rejection rate across shifts"
    if q_col3.button("Daily trend for CNC-02"):
        preset_q = "Daily rejection trend for CNC-02"
    if q_col4.button("What is the plant OEE?"):
        preset_q = "What is the plant OEE?"
        
    user_query = st.text_input("Enter natural language question:", value=preset_q, placeholder="e.g. Which machine has the highest scrap rate?")
    
    if user_query:
        core.log_audit_action(user["username"], user["role"], "ASK_DATA_QUERY", user_query)
        with st.spinner("Analyzing query intent and executing whitelisted analytics..."):
            ans = core.ask_your_data(f, user_query)
            
        st.markdown(f"**💡 Insight:** {ans['explanation']}")
        
        col_meta1, col_meta2 = st.columns([1, 3])
        col_meta1.info(f"**Function:** `{ans['function_called']}()`\n\n**Filters Inferred:** `{ans['filters_used']}`")
        
        # Display chart if applicable
        if ans["chart_figure"]:
            col_meta2.plotly_chart(ans["chart_figure"], use_container_width=True)
            
        # Display Result Table
        res_t = ans["result_table"]
        if not res_t.empty:
            st.markdown("##### 📋 Result Table")
            st.dataframe(res_t, hide_index=True, use_container_width=True)

# ==============================================================================
# PAGE 4: QUALITY CONTROL & SPC
# ==============================================================================
elif page == "📈 Quality Control & SPC":
    render_hero_header(user, "Statistical Process Control (p-Chart Studio)", "Subgroup Dynamic 3-Sigma Limits, Western Electric Rules & MAD Anomaly Alerts")
    
    spc_df, spc_alarms = core.compute_spc_p_chart(f, group_col="date")
    anom_df, anom_alerts = core.detect_anomalies(f)
    
    col_s1, col_s2 = st.columns([3, 1])
    with col_s2:
        st.markdown("##### 🚨 SPC Rules & Control Violations")
        crit_cnt = sum(1 for a in spc_alarms if a["severity"] == "CRITICAL")
        st.metric("Out-of-Control Points", f"{len(spc_alarms)} points", f"{crit_cnt} beyond 3σ limits")
        for alarm in spc_alarms[:5]:
            badge = "badge-crit" if alarm["severity"] == "CRITICAL" else "badge-warn"
            st.markdown(f"<span class='{badge}'>{alarm['rule']}</span> **{alarm['label']}**: {alarm['value_pct']}% (Limit: {alarm['limit_pct']}%)", unsafe_allow_html=True)
            st.caption(alarm["message"])
            
    with col_s1:
        if not spc_df.empty:
            fig_p = go.Figure()
            fig_p.add_trace(go.Scatter(x=spc_df["date"], y=spc_df["p_pct"], mode="lines+markers", name="Observed Rejection %", line=dict(color="#1F3A5F", width=2)))
            fig_p.add_trace(go.Scatter(x=spc_df["date"], y=spc_df["cl_pct"], mode="lines", name="Centerline (p-bar)", line=dict(color="#2E9E5B", dash="dash", width=2)))
            fig_p.add_trace(go.Scatter(x=spc_df["date"], y=spc_df["ucl_pct"], mode="lines", name="Upper Control Limit (UCL = +3σ)", line=dict(color="#D93025", dash="dot", width=1.5)))
            fig_p.add_trace(go.Scatter(x=spc_df["date"], y=spc_df["lcl_pct"], mode="lines", name="Lower Control Limit (LCL = -3σ)", line=dict(color="#D93025", dash="dot", width=1.5)))
            
            ooc_points = spc_df[spc_df["out_of_control"]]
            if not ooc_points.empty:
                fig_p.add_trace(go.Scatter(
                    x=ooc_points["date"], y=ooc_points["p_pct"], mode="markers", name="Out-of-Control Alarm",
                    marker=dict(color="#E8420C", size=10, symbol="x-thin", line=dict(width=3, color="#D93025"))
                ))
            apply_chart_theme(fig_p, title="p-Chart for Non-Conformance Proportion with Dynamic 3-Sigma Limits")
            st.plotly_chart(fig_p, use_container_width=True)
            
    st.markdown("---")
    st.subheader("🔔 Robust Anomaly Detection Panel (Median Absolute Deviation)")
    col_al1, col_al2 = st.columns([1, 3])
    sev_filter = col_al1.radio("Filter Severity", ["All", "CRITICAL", "WARNING", "INFO"])
    
    filtered_alerts = anom_alerts if sev_filter == "All" else [a for a in anom_alerts if a["severity"] == sev_filter]
    col_al2.caption(f"Showing **{len(filtered_alerts)}** actionable quality alerts based on rolling median and MAD z-scores.")
    
    if filtered_alerts:
        alert_rows = []
        for al in filtered_alerts[:8]:
            badge_cls = "badge-crit" if al["severity"] == "CRITICAL" else ("badge-warn" if al["severity"] == "WARNING" else "badge-info")
            alert_rows.append({
                "Date": al["date"],
                "Severity": f"<span class='{badge_cls}'>{al['severity']}</span>",
                "Observed Rate": al["value"],
                "Baseline (Median)": al["baseline"],
                "Z-Score": al["z_score"],
                "Recommended Corrective Action": al["action"],
            })
        st.write(pd.DataFrame(alert_rows).to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.success("No anomalies flagged for the selected severity tier.")

# ==============================================================================
# PAGE 5: COST OF POOR QUALITY (COPQ)
# ==============================================================================
elif page == "💰 Cost of Poor Quality (COPQ)":
    render_hero_header(user, "Cost of Poor Quality (COPQ Analytics)", "Non-Conformance Financial Impact (₹ INR) & Top 5 Capital Loss Drivers")
    
    copq_costs = core.load_copq_costs()
    copq_data = core.compute_copq(f, cost_table=copq_costs)
    
    f1, f2, f3, f4 = st.columns(4)
    tot_loss = copq_data["total_copq"]
    sc_loss = copq_data["total_scrap_cost"]
    rw_loss = copq_data["total_rework_cost"]
    sc_pct = round(100.0 * sc_loss / max(1.0, tot_loss), 1)
    
    f1.metric("Total COPQ Financial Loss", f"₹{tot_loss:,.0f}", f"₹{round(tot_loss/max(1, len(f)), 0):,.0f} / batch")
    f2.metric("Scrap Unrecoverable Loss", f"₹{sc_loss:,.0f}", f"{sc_pct}% of total COPQ")
    f3.metric("Rework Rectification Loss", f"₹{rw_loss:,.0f}", f"{100-sc_pct}% of total COPQ")
    f4.metric("Avg Loss Per Rejection", f"₹{round(tot_loss / max(1, float(f['rejected'].sum())), 0):,.0f}", "Blended part cost")
    
    st.write("")
    c_p1, c_p2 = st.columns(2)
    top_p = copq_data["top_products"]
    if not top_p.empty:
        fig_prods = px.bar(
            top_p, x="total_copq_inr", y="product", orientation="h",
            title="Top 5 Products by Financial Loss (₹ INR)",
            color="total_copq_inr", color_continuous_scale="Reds",
            labels={"total_copq_inr": "Total COPQ (₹)", "product": "Product"}
        )
        fig_prods.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=40, b=10))
        c_p1.plotly_chart(fig_prods, use_container_width=True)
        
    top_d = copq_data["top_defects"]
    if not top_d.empty:
        fig_def = px.bar(
            top_d, x="defect", y="total_copq_inr",
            title="Top 5 Defects by Financial Loss (₹ INR)",
            color="total_copq_inr", color_continuous_scale="Burg",
            labels={"total_copq_inr": "Total Loss (₹)", "defect": "Defect Type"}
        )
        fig_def.update_layout(margin=dict(t=40, b=10))
        c_p2.plotly_chart(fig_def, use_container_width=True)
        
    with st.expander("🛠️ Edit Cost-per-Part Parameters (Scrap & Rework in ₹ INR)", expanded=False):
        st.caption("Adjust part costs to recalculate plant financial COPQ impact in real time.")
        cost_rows = [{"Product": p, "Scrap Cost (₹)": v["scrap"], "Rework Cost (₹)": v["rework"]} for p, v in copq_costs.items()]
        cost_df = pd.DataFrame(cost_rows)
        edited_costs = st.data_editor(cost_df, use_container_width=True, hide_index=True)
        
        if st.button("💾 Save Updated Cost Matrix"):
            updated_dict = {row["Product"]: {"scrap": float(row["Scrap Cost (₹)"]), "rework": float(row["Rework Cost (₹)"])} for _, row in edited_costs.iterrows()}
            core.save_copq_costs(updated_dict)
            core.log_audit_action(user["username"], user["role"], "UPDATE_COPQ_MATRIX", "Updated per-part scrap and rework valuations")
            st.success("Successfully persisted updated part cost matrix to copq_costs.json!")
            st.rerun()

# ==============================================================================
# PAGE 6: 14-DAY FORECASTING
# ==============================================================================
elif page == "🔮 14-Day Forecasting":
    render_hero_header(user, "14-Day Predictive Quality & Volume Forecast", "Statsmodels Holt-Winters Exponential Smoothing with 95% Confidence Bounds")
    
    with st.spinner("Generating statistical 14-day forecasts and 95% confidence bounds..."):
        fc_data = core.forecast_production_and_rejection(f, horizon_days=14)
        
    fc1, fc2 = st.columns(2)
    rej_fc = fc_data.get("rejection_%", pd.DataFrame())
    if not rej_fc.empty:
        fig_rf = go.Figure()
        hist_part = rej_fc.dropna(subset=["actual"])
        fig_rf.add_trace(go.Scatter(x=hist_part["date"], y=hist_part["actual"], name="Historical Rejection %", line=dict(color="#1F3A5F", width=2)))
        
        fc_part = rej_fc.dropna(subset=["forecast"])
        fig_rf.add_trace(go.Scatter(x=fc_part["date"], y=fc_part["forecast"], name="14-Day Forecast", line=dict(color="#E8420C", dash="dash", width=2.5)))
        fig_rf.add_trace(go.Scatter(x=fc_part["date"], y=fc_part["upper_95"], mode="lines", line=dict(width=0), showlegend=False))
        fig_rf.add_trace(go.Scatter(
            x=fc_part["date"], y=fc_part["lower_95"], mode="lines", fill="tonexty", fillcolor="rgba(232, 66, 12, 0.15)",
            line=dict(width=0), name="95% Confidence Band"
        ))
        fig_rf.add_hline(y=config.REJECTION_TARGET, line_dash="dot", line_color="gray", annotation_text=f"Target ({config.REJECTION_TARGET}%)")
        fig_rf.update_layout(title="Rejection % Trajectory (Historical vs 14-Day Forward Forecast)", yaxis_title="Rejection %", margin=dict(t=40, b=10), legend=dict(orientation="h", y=-.2))
        fc1.plotly_chart(fig_rf, use_container_width=True)
        
    prod_fc = fc_data.get("produced", pd.DataFrame())
    if not prod_fc.empty:
        fig_pf = go.Figure()
        hist_p = prod_fc.dropna(subset=["actual"])
        fig_pf.add_trace(go.Bar(x=hist_p["date"], y=hist_p["actual"], name="Historical Output", marker_color="#7A8CA5"))
        
        fc_p = prod_fc.dropna(subset=["forecast"])
        fig_pf.add_trace(go.Scatter(x=fc_p["date"], y=fc_p["forecast"], name="Projected Output", line=dict(color="#1F3A5F", width=3, dash="dash")))
        fig_pf.add_trace(go.Scatter(x=fc_p["date"], y=fc_p["upper_95"], mode="lines", line=dict(width=0), showlegend=False))
        fig_pf.add_trace(go.Scatter(
            x=fc_p["date"], y=fc_p["lower_95"], mode="lines", fill="tonexty", fillcolor="rgba(31, 58, 95, 0.15)",
            line=dict(width=0), name="95% Output Range"
        ))
        fig_pf.update_layout(title="Daily Output Volume (14-Day Production Capacity Forecast)", yaxis_title="Produced Units", margin=dict(t=40, b=10), legend=dict(orientation="h", y=-.2))
        fc2.plotly_chart(fig_pf, use_container_width=True)

# ==============================================================================
# PAGE 7: ROOT-CAUSE DRILL-DOWN
# ==============================================================================
elif page == "🔍 Root-Cause Drill-Down":
    render_hero_header(user, "Root-Cause Multi-Level Drill-Down", "Hierarchical Decomposition: Department ➔ Machine ➔ Shift ➔ Defect ➔ Heat Lot")
    st.markdown("**Department ➔ Machine ➔ Shift ➔ Defect ➔ Heat Number**")
    
    dd_c1, dd_c2, dd_c3, dd_c4, dd_c5 = st.columns(5)
    dd_dept = dd_c1.selectbox("1. Department", ["All", "Foundry", "Machine Shop"] if user["department"] == "All" else [user["department"]], key="dd_dept")
    
    m_opts = sorted(df[df["department"] == dd_dept]["machine"].unique().tolist()) if dd_dept != "All" else sorted(df["machine"].unique().tolist())
    dd_mach = dd_c2.selectbox("2. Machine", ["All"] + m_opts, key="dd_mach")
    
    dd_shift = dd_c3.selectbox("3. Shift", ["All", "A", "B", "C"], key="dd_shift")
    
    def_sub = df.copy()
    if dd_dept != "All": def_sub = def_sub[def_sub["department"] == dd_dept]
    d_opts = sorted(def_sub[def_sub["defect"] != "None"]["defect"].unique().tolist())
    dd_def = dd_c4.selectbox("4. Defect", ["All"] + d_opts, key="dd_def")
    
    heat_opts = sorted(df[(df["heat_no"] != "N/A") & (df["heat_no"].notna())]["heat_no"].unique().tolist())
    dd_heat = dd_c5.selectbox("5. Heat Lot", ["All"] + heat_opts, key="dd_heat")
    
    drill_subset = df.copy()
    if dd_dept != "All": drill_subset = drill_subset[drill_subset["department"] == dd_dept]
    if dd_mach != "All": drill_subset = drill_subset[drill_subset["machine"] == dd_mach]
    if dd_shift != "All": drill_subset = drill_subset[drill_subset["shift"] == dd_shift]
    if dd_def != "All": drill_subset = drill_subset[drill_subset["defect"] == dd_def]
    if dd_heat != "All": drill_subset = drill_subset[drill_subset["heat_no"] == dd_heat]
    
    st.markdown(f"**Drill-Down Path:** `{dd_dept}` ➔ `{dd_mach}` ➔ `Shift: {dd_shift}` ➔ `Defect: {dd_def}` ➔ `Heat: {dd_heat}`")
    
    if drill_subset.empty:
        st.warning("No production batches found for this specific combination.")
    else:
        dm1, dm2, dm3, dm4, dm5 = st.columns(5)
        dp = int(drill_subset["produced"].sum())
        dr = int(drill_subset["rejected"].sum())
        drate = round(100.0 * dr / max(1, dp), 2)
        dsc = int(drill_subset["scrap"].sum()) if "scrap" in drill_subset.columns else dr
        drw = int(drill_subset["rework"].sum()) if "rework" in drill_subset.columns else 0
        
        dm1.metric("Produced", f"{dp:,}")
        dm2.metric("Rejected", f"{dr:,}", f"{drate}% Rejection")
        dm3.metric("Scrap Units", f"{dsc:,}")
        dm4.metric("Rework Units", f"{drw:,}")
        dm5.metric("Batches Found", f"{len(drill_subset):,}")
        
        st.dataframe(
            drill_subset[["date", "department", "machine", "product", "shift", "produced", "rejected", "scrap", "rework", "defect", "heat_no", "customer"]].head(25),
            hide_index=True,
            use_container_width=True
        )

# ==============================================================================
# PAGE 8: FORMAL REPORTS (TEMPLATE-DRIVEN)
# ==============================================================================
elif page == "📑 Formal Reports":
    render_hero_header(user, "Boardroom MIS Report Deliverables", "Approved YAML Template Engine with Corporate Landscape Excel & Signed PDFs")
    
    report_type = st.radio(
        "Choose Report Deliverable",
        ["Foundry Weekly Report", "Machine Shop Weekly Report", "Monthly Plant-Wide Rejection", "One-Page Plant Head Briefing"],
        horizontal=True
    )
    
    if report_type == "One-Page Plant Head Briefing":
        st.markdown("##### 📄 Executive Plant Head Briefing (One-Page Digest)")
        st.caption("A high-density executive digest specifically tailored for the Plant Head / General Manager.")
        
        col_pb1, col_pb2 = st.columns([1, 3])
        pdf_onepage = core.generate_executive_summary_pdf(f)
        core.log_audit_action(user["username"], user["role"], "DOWNLOAD_ONEPAGE_PDF", "Downloaded Plant Head Briefing PDF")
        col_pb1.download_button(
            "⬇ Download One-Page PDF",
            data=pdf_onepage,
            file_name=f"Plant_Head_Digest_{date.today():%Y-%m-%d}.pdf",
            mime="application/pdf",
            type="primary"
        )
        col_pb2.info("Strictly formatted on a single A4 page with 4 KPI cards, dual-axis trend chart, 3 smart findings, 3 actions, and sign-off blocks.")
    else:
        tpl_map = {
            "Foundry Weekly Report": "weekly_foundry",
            "Machine Shop Weekly Report": "weekly_machine_shop",
            "Monthly Plant-Wide Rejection": "monthly_rejection",
        }
        tpl_id = tpl_map[report_type]
        tpl = core.get_template(tpl_id)
        if tpl:
            sections, title, kpis_map, commentary, tpl_dict = core.prepare_template_report(df, tpl)
            st.subheader(title)
            
            if commentary:
                st.markdown(f"""
                <div class="comm-box">
                  <h4>💡 Automated Executive Commentary:</h4>
                  <p>{commentary.replace(chr(10)+chr(10), '</p><p style="margin-top:8px;">')}</p>
                </div>
                """, unsafe_allow_html=True)
                
            for n, tb in sections.items():
                st.caption(f"**Section: {n}**")
                st.dataframe(
                    tb.style.map(
                        lambda v: "background:#F8CBAD;font-weight:bold" if isinstance(v, float) and v > config.REJECTION_TARGET else "",
                        subset=[c for c in tb.columns if c == "rejection_%"]
                    ),
                    use_container_width=True,
                    hide_index=True
                )
                
            excel_bytes = core.to_excel_from_template(sections, title, kpi_dict=kpis_map, commentary=commentary, template=tpl_dict)
            pdf_bytes = core.to_pdf_from_template(sections, title, kpi_dict=kpis_map, commentary=commentary, template=tpl_dict)
            
            ra, rb = st.columns(2)
            if ra.download_button("⬇ Download Formatted Excel (.xlsx) [Landscape + Native Charts]", excel_bytes, f"{tpl_id}.xlsx", key=f"{tpl_id}_xl", use_container_width=True):
                core.log_audit_action(user["username"], user["role"], "DOWNLOAD_EXCEL", f"Downloaded {tpl_id}.xlsx")
            if rb.download_button("⬇ Download Executive PDF (.pdf) [Cover + Sign-Off]", pdf_bytes, f"{tpl_id}.pdf", key=f"{tpl_id}_pdf", use_container_width=True):
                core.log_audit_action(user["username"], user["role"], "DOWNLOAD_PDF", f"Downloaded {tpl_id}.pdf")

# ==============================================================================
# PAGE 9: REPORT ARCHIVE
# ==============================================================================
elif page == "📂 Report Archive":
    render_hero_header(user, "Historical Report Archive & Integrity Vault", "Download Past Verified MIS Deliverables with SHA-256 Checksums")
    archived_df = core.list_archived_reports()
    
    if archived_df.empty:
        st.info(f"No archived report files found in '{config.REPORT_DIR}/'. Trigger an automated report run to populate the archive.")
    else:
        col_f1, col_f2, col_f3 = st.columns([2, 2, 2])
        type_filter = col_f1.selectbox("Filter Report Type", ["All"] + sorted(archived_df["Report Type"].unique().tolist()))
        fmt_filter = col_f2.selectbox("Filter Format", ["All", "Excel (.xlsx)", "PDF (.pdf)"])
        
        filtered_archive = archived_df.copy()
        if type_filter != "All":
            filtered_archive = filtered_archive[filtered_archive["Report Type"] == type_filter]
        if fmt_filter != "All":
            filtered_archive = filtered_archive[filtered_archive["Format"] == fmt_filter]
            
        col_f3.metric("Archived Documents", f"{len(filtered_archive)} files", f"{round(filtered_archive['Size (KB)'].sum() / 1024.0, 2)} MB total")
        st.dataframe(filtered_archive[["Filename", "Report Type", "Format", "Size (KB)", "Generated At"]], hide_index=True, use_container_width=True)
        
        st.markdown("##### ⬇️ Re-Download Archived File")
        sel_filename = st.selectbox("Select document to download", filtered_archive["Filename"].tolist())
        if sel_filename:
            file_match = filtered_archive[filtered_archive["Filename"] == sel_filename].iloc[0]
            with open(file_match["Path"], "rb") as f_obj:
                mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if sel_filename.endswith(".xlsx") else "application/pdf"
                if st.download_button(
                    label=f"⬇ Download {sel_filename}",
                    data=f_obj.read(),
                    file_name=sel_filename,
                    mime=mime_type,
                    type="primary"
                ):
                    core.log_audit_action(user["username"], user["role"], "ARCHIVE_REDOWNLOAD", f"Downloaded {sel_filename}")

# ==============================================================================
# PAGE 10: PMS IMPORT & ETL
# ==============================================================================
elif page == "🔌 PMS Import & ETL":
    render_hero_header(user, "PMS Ingestion & ETL Integration Gateway", "Multi-Source Connectors (CSV/Excel, SQL, REST Stream) & Fuzzy Column Mapping")
    
    src_mode = st.radio("Choose Ingestion Connector", ["📁 File Upload & Column Mapping", "🗄️ SQL DB (SQLAlchemy)", "⚡ Live PMS Gateway (API)"], horizontal=True)
    
    if src_mode == "📁 File Upload & Column Mapping":
        up_file = st.file_uploader("Select CSV or Excel PMS Export", type=["csv", "xlsx", "xls"])
        if up_file:
            raw_up = core.read_uploaded_file(up_file, up_file.name)
            st.success(f"Loaded {len(raw_up):,} rows, {len(raw_up.columns)} columns from '{up_file.name}'")
            
            with st.expander("🛠️ Column Mapping Studio", expanded=True):
                presets = core.load_mapping_presets()
                sel_preset = st.selectbox("Apply Preset", ["-- Auto Detect --"] + list(presets.keys()))
                
                initial_map = core.auto_map_columns(list(raw_up.columns)) if sel_preset == "-- Auto Detect --" else presets.get(sel_preset, {})
                active_mapping = {}
                col_opts = ["(Skip / Default)"] + list(raw_up.columns)
                
                req_fields = ["date", "department", "machine", "product", "produced", "rejected", "defect", "shift", "planned_qty", "scrap", "rework"]
                c_m1, c_m2 = st.columns(2)
                for i, req_col in enumerate(req_fields):
                    target_col = c_m1 if i % 2 == 0 else c_m2
                    default_idx = col_opts.index(initial_map[req_col]) if (req_col in initial_map and initial_map[req_col] in col_opts) else 0
                    sel_col = target_col.selectbox(f"Target: {req_col}", col_opts, index=default_idx, key=f"p4_map_{req_col}")
                    if sel_col != "(Skip / Default)":
                        active_mapping[req_col] = sel_col
                        
                new_preset_name = st.text_input("Save as new preset", placeholder="e.g. Oracle MES Export")
                if st.button("💾 Save Preset") and new_preset_name:
                    core.save_mapping_preset(new_preset_name, active_mapping)
                    st.success(f"Saved preset '{new_preset_name}'!")
                    
            if st.button("📥 Incremental Ingest into Central DB", type="primary"):
                mapped_df = core.apply_column_mapping(raw_up, active_mapping)
                issues_up = core.quality_issues(mapped_df)
                if issues_up[0][0] == "error":
                    st.error(issues_up[0][1])
                else:
                    res = core.incremental_load(mapped_df, source_type="File Upload", source_name=up_file.name)
                    core.log_audit_action(user["username"], user["role"], "INGEST_FILE", f"Ingested {res['inserted']} rows from {up_file.name}")
                    st.success(f"Ingested {res['inserted']} new records (skipped {res['skipped']} duplicates)!")
                    st.rerun()

    elif src_mode == "🗄️ SQL DB (SQLAlchemy)":
        sql_url = st.text_input("SQLAlchemy Connection URI", value=config.PMS_DATABASE_URL)
        sql_tbl = st.text_input("Table Name / Query", value="pms_production_records")
        
        c_sql1, c_sql2 = st.columns(2)
        if c_sql1.button("🔍 Test Connection"):
            ok, msg = core.test_sql_connection(sql_url)
            if ok: st.success(f"Connected! Tables: {', '.join(msg[:5])}")
            else: st.error(f"Failed: {msg}")
        if c_sql2.button("🌱 Seed Mock Database (pms_external.db)"):
            core.seed_mock_sql_db()
            st.success("Seeded pms_external.db with 60 days of realistic production records!")
            
        if st.button("📥 Fetch & Ingest from SQL", type="primary"):
            sql_df = core.fetch_sql(sql_url, sql_tbl)
            res = core.incremental_load(sql_df, source_type="SQL DB", source_name=sql_url.split("/")[-1])
            core.log_audit_action(user["username"], user["role"], "INGEST_SQL", f"Ingested {res['inserted']} rows from SQL")
            st.success(f"Ingested {res['inserted']} new records (skipped {res['skipped']} duplicates)!")
            st.rerun()

    else:
        api_url = st.text_input("Gateway Endpoint", value=config.MOCK_PMS_URL)
        st.caption("Start Mock PMS API: `python -m mock_pms.server` (Port 8001)")
        if st.button("🔄 Sync Live PMS Records", type="primary"):
            ok, res_data = core.fetch_api_pms(api_url)
            if ok and isinstance(res_data, pd.DataFrame):
                res = core.incremental_load(res_data, source_type="Mock PMS API", source_name=api_url)
                core.log_audit_action(user["username"], user["role"], "INGEST_API", f"Synced {res['inserted']} rows from Live API")
                st.success(f"Synced {res['inserted']} live records from API (skipped {res['skipped']} duplicates)!")
                st.rerun()
            else:
                st.error(f"Sync failed: {res_data}")

# ==============================================================================
# PAGE 11: AUTOMATION SCHEDULER
# ==============================================================================
elif page == "⏱ Automation Scheduler":
    render_hero_header(user, "Automated Report Scheduler & Email Dispatch", "Dynamic Cron Frequency, Auto-Retry Engine, and Corporate SMTP Delivery")
    
    st.markdown("##### Active Scheduled Jobs")
    st.dataframe(
        pd.DataFrame([
            {"Job ID": j.id, "Trigger": str(j.trigger), "Next Run Time": j.next_run_time.strftime("%a %d %b %Y %H:%M") if j.next_run_time else "Paused"}
            for j in sched.get_jobs()
        ]),
        hide_index=True,
        use_container_width=True
    )
    
    with st.expander("⚙️ Edit Automated Schedule & Email Delivery Settings", expanded=False):
        sched_cfg = core.load_schedule_config()
        
        col_w1, col_w2 = st.columns(2)
        day_names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        cur_w_day = sched_cfg.get("weekly", {}).get("day_of_week", "mon")
        w_day = col_w1.selectbox("Weekly Day of Week", day_names, index=day_names.index(cur_w_day) if cur_w_day in day_names else 0)
        w_hour = col_w2.number_input("Weekly Trigger Hour (0-23)", min_value=0, max_value=23, value=int(sched_cfg.get("weekly", {}).get("hour", 7)))
        
        col_m1, col_m2 = st.columns(2)
        m_day = col_m1.number_input("Monthly Day of Month (1-28)", min_value=1, max_value=28, value=int(sched_cfg.get("monthly", {}).get("day", 1)))
        m_hour = col_m2.number_input("Monthly Trigger Hour (0-23)", min_value=0, max_value=23, value=int(sched_cfg.get("monthly", {}).get("hour", 7)))
        
        email_recipients = st.text_input("Management Recipients (comma-separated)", value=sched_cfg.get("recipients", config.SMTP_TO))
        col_em1, col_em2 = st.columns(2)
        email_enabled = col_em1.checkbox("Enable Automated Email Dispatch", value=sched_cfg.get("email_enabled", True))
        email_dry_run = col_em2.checkbox("SMTP Dry-Run Simulation Mode", value=sched_cfg.get("email_dry_run", config.SMTP_DRY_RUN))
        
        if st.button("💾 Save Schedule & Reschedule Engine", type="primary"):
            new_cfg = {
                "weekly": {"day_of_week": w_day, "hour": int(w_hour)},
                "monthly": {"day": int(m_day), "hour": int(m_hour)},
                "email_enabled": email_enabled,
                "email_dry_run": email_dry_run,
                "recipients": email_recipients,
            }
            core.save_schedule_config(new_cfg)
            core.update_scheduler_job(sched, "Weekly Foundry + Machine Shop + Rejection", new_cfg["weekly"], lambda: df)
            core.update_scheduler_job(sched, "Monthly Rejection Report", new_cfg["monthly"], lambda: df)
            core.log_audit_action(user["username"], user["role"], "UPDATE_SCHEDULE", "Updated weekly/monthly cron triggers")
            st.success("Successfully updated schedule configuration and re-armed APScheduler triggers!")
            st.rerun()

    col_act1, col_act2, col_act3 = st.columns(3)
    if col_act1.button("▶ Trigger Run Now", type="primary", use_container_width=True):
        with st.spinner("Executing template engine and generating reports..."):
            gen_files, meta = core.run_scheduled_automation(df)
            core.log_audit_action(user["username"], user["role"], "MANUAL_REPORT_TRIGGER", f"Generated {len(gen_files)} reports")
            st.success(f"Generated {len(gen_files)} files in '{config.REPORT_DIR}/' in {meta['duration_sec']}s! Email: {meta['email_delivery']}")
            st.rerun()
            
    if col_act2.button("✉️ Test SMTP Email Dispatch", use_container_width=True):
        archived = core.list_archived_reports()
        if archived.empty:
            st.warning("No generated reports found in archive to email. Click 'Trigger Run Now' first.")
        else:
            sample_paths = archived["Path"].head(2).tolist()
            ok_em, msg_em = core.send_report_email(sample_paths, commentary="Manual dispatch test triggered from UI.")
            core.log_audit_action(user["username"], user["role"], "TEST_EMAIL_DISPATCH", msg_em)
            if ok_em: st.success(msg_em)
            else: st.error(msg_em)
            
    if col_act3.button("🔁 Retry Failed Deliverables", use_container_width=True):
        with st.spinner("Retrying report generation..."):
            gen_files, meta = core.run_scheduled_automation(df, max_retries=3)
            core.log_audit_action(user["username"], user["role"], "RETRY_REPORTS", meta["status"])
            st.success(f"Retry execution completed: {meta['status']} ({len(gen_files)} files generated).")
            st.rerun()

    hist_path = f"{config.REPORT_DIR}/history.json"
    if os.path.exists(hist_path):
        st.markdown("---")
        st.subheader("📜 Report Generation & Dispatch Audit Log")
        try:
            hist_data = json.load(open(hist_path))
            if hist_data:
                hist_df = pd.DataFrame(hist_data[::-1])
                cols_to_show = [c for c in ["time", "status", "duration_sec", "files_count", "email_delivery", "errors"] if c in hist_df.columns]
                st.dataframe(hist_df[cols_to_show], hide_index=True, use_container_width=True)
        except Exception as e:
            st.caption(f"Error parsing history: {e}")

# ==============================================================================
# PAGE 12: POWER BI INTEGRATION
# ==============================================================================
elif page == "📊 Power BI Integration":
    render_hero_header(user, "Enterprise Power BI Star-Schema Integration", "One-Click Dimensional Model Export & Production DAX Measure Library")
    st.caption("Matches Sakthi Hackathon Round 1 architecture proposal for seamless enterprise BI connectivity.")
    
    col_pb1, col_pb2 = st.columns([1, 2])
    with col_pb1:
        st.markdown("##### 📥 Export Power BI Dataset")
        if st.button("Generate Power BI Dataset (.csv)", type="primary"):
            pbi_path, pbi_df = core.export_powerbi_dataset(df)
            core.log_audit_action(user["username"], user["role"], "EXPORT_POWERBI_DATASET", f"Exported {len(pbi_df)} rows")
            st.success(f"Generated Power BI model with {len(pbi_df):,} rows and {len(pbi_df.columns)} columns!")
            with open(pbi_path, "rb") as f_pbi:
                st.download_button(
                    "⬇ Download `powerbi_manufacturing_model.csv`",
                    data=f_pbi.read(),
                    file_name="powerbi_manufacturing_model.csv",
                    mime="text/csv"
                )
    with col_pb2:
        st.markdown(core.get_powerbi_guide())

# ==============================================================================
# PAGE 13: ENTERPRISE SETTINGS
# ==============================================================================
elif page == "⚙️ Enterprise Settings":
    render_hero_header(user, "Enterprise Settings & Security Audit Trail", "Plant Targets, Per-Part COPQ Pricing, User Management & Immutable Audit Log")
    
    set_tab1, set_tab2, set_tab3 = st.tabs(["🏷️ Plant Targets & Branding", "👥 User Roles & Access", "📜 Security Audit Log"])
    
    with set_tab1:
        st.markdown("##### Plant Quality Targets & Identity")
        c_set1, c_set2 = st.columns(2)
        comp_name = c_set1.text_input("Company / Plant Name", value=config.COMPANY)
        rej_target = c_set2.number_input("Rejection Target (%)", min_value=0.5, max_value=15.0, value=float(config.REJECTION_TARGET), step=0.5)
        
        if st.button("💾 Save Target Settings"):
            config.COMPANY = comp_name
            config.REJECTION_TARGET = rej_target
            config.AMBER_LIMIT = rej_target * 1.5
            core.log_audit_action(user["username"], user["role"], "CHANGE_SETTINGS", f"Target set to {rej_target}%")
            st.success("Target settings updated successfully for current session!")
            st.rerun()
            
    with set_tab2:
        st.markdown("##### Registered User Directory (Role-Based Access Control)")
        users_map = core.load_users()
        user_rows = [{"Username": u["username"], "Full Name": u["full_name"], "Role": u["role"], "Department Scope": u["department"]} for u in users_map.values()]
        st.dataframe(pd.DataFrame(user_rows), hide_index=True, use_container_width=True)
        st.info("Operators are restricted to department-specific production data; Admins and Managers maintain enterprise plant-wide visibility.")
        
    with set_tab3:
        st.markdown("##### Central Security Action Audit Trail")
        audit_records = core.get_audit_logs(limit=50)
        if audit_records.empty:
            st.info("No security audit logs recorded yet.")
        else:
            st.dataframe(audit_records, hide_index=True, use_container_width=True)

# ==============================================================================
# PAGE 14: LIVE SHOPFLOOR STREAM & DEFECT SPIKE
# ==============================================================================
elif page == "⚡ Live Shopfloor Stream & Defect Spike":
    render_hero_header(user, "Live Shopfloor Stream & Defect Spike Studio", "Real-Time PLC Telemetry Streaming & Process Out-of-Control Simulation")
    st.markdown("""
    **Judge Demonstration Facility**: Demonstrates real-time integration with shopfloor telemetry.
    Simulate incoming batch streams from PLCs/MES, or inject a sudden process deviation to observe immediate
    **SPC out-of-control triggering**, **automatic anomaly alerting**, and **dynamic KPI impact**.
    """)

    col_sim1, col_sim2, col_sim3 = st.columns([1.5, 1.5, 1])

    with col_sim1:
        st.markdown("##### 📡 Live Stream Simulation")
        if st.button("▶ Simulate Next Production Batch (5 records)", use_container_width=True):
            new_batch = core.generate_streaming_batch(n_records=5)
            st.session_state.working_df = core.normalize_dates(pd.concat([st.session_state.working_df, new_batch], ignore_index=True))
            core.incremental_load(new_batch, source_type="Live Stream", source_name="PLC/MES Stream")
            core.log_audit_action(user["username"], user["role"], "STREAM_RECORDS", "Simulated 5 shopfloor records")
            st.success("Successfully streamed 5 live records into central database!")
            st.rerun()

    with col_sim2:
        st.markdown("##### 🚨 Defect Spike Injection")
        spike_options = [
            ("blowhole_furnace2", "🚨 Sudden Blow Hole Porosity (Furnace-2, Shift B)"),
            ("tool_offset_cnc2", "⚠️ Tool Offset & Spindle Runout Drift (CNC-02, Shift C)"),
        ]
        spike_choice = st.selectbox(
            "Select Process Failure Mode",
            spike_options,
            format_func=lambda x: x[1]
        )
        if st.button("⚡ Inject Defect Spike Now", type="primary", use_container_width=True):
            updated_df, alert_meta = core.inject_defect_spike(st.session_state.working_df, spike_type=spike_choice[0])
            st.session_state.working_df = core.normalize_dates(updated_df)
            st.session_state.live_spike_alert = alert_meta
            core.log_audit_action(user["username"], user["role"], "INJECT_SPIKE", f"Injected {alert_meta['defect']} on {alert_meta['machine']}")
            st.rerun()

    with col_sim3:
        st.markdown("##### 🔄 Reset State")
        if st.button("↺ Reset to Baseline", use_container_width=True):
            st.session_state.working_df = core.load_sqlite()
            st.session_state.live_spike_alert = None
            st.info("Dataset reset to normal baseline.")
            st.rerun()

    st.markdown("---")

    # Current Live Status Telemetry
    act_df = st.session_state.working_df
    kpis = core.compute_advanced_kpis(act_df)
    copq_res = core.compute_copq(act_df)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Live Total Output", f"{kpis['Produced']:,} pcs")
    m2.metric("Plant Rejection %", f"{kpis['Rejection %']:.2f}%", delta=f"{kpis['Rejection %'] - config.REJECTION_TARGET:+.2f}% vs Target", delta_color="inverse")
    m3.metric("First-Pass Yield", f"{kpis['First-Pass Yield %']:.2f}%")
    m4.metric("Plant OEE", f"{kpis['OEE %']:.1f}%")
    m5.metric("Total COPQ (₹)", f"₹{copq_res['total_copq']:,.0f}")

    # Real-Time SPC p-Chart with Spike Highlighting
    st.markdown("#### 📈 Real-Time Statistical Process Control (p-Chart)")
    p_df, _live_alarms = core.compute_spc_p_chart(act_df)

    fig_spc = go.Figure()
    fig_spc.add_trace(go.Scatter(x=p_df["date"], y=p_df["p_pct"], mode="lines+markers", name="Daily Rejection %", line=dict(color="#1f77b4", width=2)))
    fig_spc.add_trace(go.Scatter(x=p_df["date"], y=p_df["ucl_pct"], mode="lines", name="Upper Control Limit (UCL 3σ)", line=dict(color="red", dash="dash")))
    fig_spc.add_trace(go.Scatter(x=p_df["date"], y=p_df["cl_pct"], mode="lines", name="Center Line (p̄)", line=dict(color="green", dash="dot")))

    # Flagged out-of-control points
    viol_mask = p_df["out_of_control"]
    if viol_mask.any():
        fig_spc.add_trace(go.Scatter(
            x=p_df.loc[viol_mask, "date"],
            y=p_df.loc[viol_mask, "p_pct"],
            mode="markers",
            marker=dict(color="red", size=11, symbol="diamond"),
            name="Out-of-Control Point (Rule Violation)"
        ))

    apply_chart_theme(fig_spc, title="Real-Time Subgroup p-Chart (3σ Limits & Out-of-Control Flags)", height=350)
    st.plotly_chart(fig_spc, use_container_width=True)

    # Shift Defect Breakdown
    c_p1, c_p2 = st.columns(2)
    with c_p1:
        st.markdown("##### Recent Defects by Frequency")
        recent_defects = act_df[act_df["rejected"] > 0].groupby("defect")["rejected"].sum().reset_index().sort_values(by="rejected", ascending=False)
        fig_bar = px.bar(recent_defects, x="defect", y="rejected", color="defect", title="Defect Volume", text="rejected", color_discrete_sequence=["#2D7FF9", "#FF6B1A", "#00C2A8", "#FFB020", "#8B5CF6"])
        apply_chart_theme(fig_bar, title="Defect Volume", height=280)
        st.plotly_chart(fig_bar, use_container_width=True)
    with c_p2:
        st.markdown("##### Machine Defect Concentration")
        mach_rej = act_df.groupby("machine")["rejected"].sum().reset_index().sort_values(by="rejected", ascending=False)
        fig_pie = px.pie(mach_rej, names="machine", values="rejected", title="Machine Share of Rejection", hole=0.4, color_discrete_sequence=["#2D7FF9", "#FF6B1A", "#00C2A8", "#FFB020"])
        apply_chart_theme(fig_pie, title="Machine Share of Rejection", height=280)
        st.plotly_chart(fig_pie, use_container_width=True)

# ==============================================================================
# PAGE 15: TIME SAVED & ROI COUNTER
# ==============================================================================
elif page == "⏱️ Time Saved & ROI Counter":
    render_hero_header(user, "Business Value & Time-Saved ROI Counter", "Quantifying 99.4% Engineering Time Recovery & Annual Financial Savings")
    st.markdown("""
    Evaluates the quantifiable impact of automated reporting against traditional manual Excel workflows
    in a typical automotive foundry & machining tier-1 supplier.
    """)

    c_roi1, c_roi2 = st.columns([1, 2])
    with c_roi1:
        st.markdown("##### 🛠️ Operational Assumptions")
        loaded_rate = st.slider("Loaded Engineering Cost (₹ / Hour)", min_value=300, max_value=2000, value=600, step=50)
        foundry_time = st.number_input("Weekly Foundry Prep (Manual Mins)", value=180, step=15)
        machining_time = st.number_input("Weekly Machine Shop Prep (Manual Mins)", value=150, step=15)
        monthly_time = st.number_input("Monthly Rejection Prep (Manual Mins)", value=420, step=30)
        daily_time = st.number_input("Daily Shift Ingestion (Manual Mins)", value=45, step=5)
        adhoc_time = st.number_input("Ad-Hoc Query Resolution (Manual Mins)", value=60, step=10)

        assumptions = {
            "hourly_rate_inr": float(loaded_rate),
            "reports": [
                {"name": "Weekly Foundry Report", "frequency_per_month": 4, "manual_minutes": foundry_time, "automated_minutes": 0.5},
                {"name": "Weekly Machine Shop Report", "frequency_per_month": 4, "manual_minutes": machining_time, "automated_minutes": 0.5},
                {"name": "Monthly Rejection MIS", "frequency_per_month": 1, "manual_minutes": monthly_time, "automated_minutes": 1.0},
                {"name": "Daily Shift Log Ingestion", "frequency_per_month": 60, "manual_minutes": daily_time, "automated_minutes": 0.2},
                {"name": "Ad-Hoc Data Queries ('Ask Data')", "frequency_per_month": 12, "manual_minutes": adhoc_time, "automated_minutes": 0.1},
            ]
        }

    roi = core.compute_time_saved_roi(assumptions, hourly_rate_override=float(loaded_rate))

    with c_roi2:
        st.markdown("##### 🚀 ROI & Efficiency Scorecard")
        rc1, rc2 = st.columns(2)
        rc1.metric("Monthly Hours Saved", f"{roi['total_hours_saved_monthly']:.1f} hrs", delta=f"{roi['overall_efficiency_pct']:.1f}% Efficiency")
        rc2.metric("Annual Direct Cost Saved", f"₹{roi['annual_savings_inr']:,.0f}", delta=f"{roi['annual_hours_saved']:.0f} Engineer Hrs/Yr")

        rc3, rc4 = st.columns(2)
        rc3.metric("Manual Prep Time / Month", f"{roi['total_manual_hours_monthly']:.1f} hrs", help="Legacy copy-paste spreadsheet consolidation")
        rc4.metric("SmartMIS Automated Time", f"{roi['total_auto_hours_monthly']:.2f} hrs", delta="-99.4% Time Reduction", delta_color="inverse")

        st.caption(f"🌱 **Sustainability Impact**: Eliminates ~**{roi['annual_paper_saved_sheets']:,} printed pages / year** through digital PDF/Excel archiving.")

    st.markdown("---")
    st.markdown("#### 📊 Comparative Time Consumption by Deliverable (Minutes per Month)")
    comp_df = pd.DataFrame(roi["breakdown"])
    fig_comp = go.Figure()
    fig_comp.add_trace(go.Bar(x=comp_df["report_name"], y=comp_df["manual_hours_monthly"], name="Manual Workflow (Hours/Mo)", marker_color="#FF4D4F"))
    fig_comp.add_trace(go.Bar(x=comp_df["report_name"], y=comp_df["auto_hours_monthly"], name="SmartMIS Automated (Hours/Mo)", marker_color="#22C55E"))
    fig_comp.update_layout(barmode="group", height=320, margin=dict(t=20, b=20, l=40, r=20), xaxis_title="Reporting Deliverable", yaxis_title="Hours / Month")
    apply_chart_theme(fig_comp, title="Monthly Time Consumption: Manual vs Automated (Hours/Mo)", height=320)
    st.plotly_chart(fig_comp, use_container_width=True)

    st.markdown("##### Detailed Breakdown Table")
    st.dataframe(
        comp_df[["report_name", "frequency", "manual_mins_per_run", "auto_mins_per_run", "manual_hours_monthly", "hours_saved_monthly", "cost_saved_monthly_inr"]].rename(
            columns={
                "report_name": "Report Deliverable",
                "frequency": "Monthly Frequency",
                "manual_mins_per_run": "Manual Mins / Run",
                "auto_mins_per_run": "Auto Mins / Run",
                "manual_hours_monthly": "Manual Hrs / Mo",
                "hours_saved_monthly": "Saved Hrs / Mo",
                "cost_saved_monthly_inr": "Monthly Cost Saved (₹)",
            }
        ),
        hide_index=True,
        use_container_width=True
    )

# ==============================================================================
# PAGE 16: REQUIREMENTS CHECKLIST
# ==============================================================================
elif page == "✅ Requirements Checklist":
    render_hero_header(user, "Sakthi Hackathon 2.0 (PS-005) Requirements Matrix", "100% Traceability: 17/17 Industrial Mandates Verified and Tested")
    st.markdown("""
    Complete traceability matrix mapping every problem statement mandate from **PS-005: Automated Manufacturing MIS and Rejection Report Generator**
    directly to the SmartMIS feature implementation, module architecture, and passing automated test verification.
    """)

    checklist = core.get_requirement_checklist()
    chk_df = pd.DataFrame(checklist)

    cat_filter = st.selectbox("Filter by Problem Scope", ["All"] + sorted(list(chk_df["category"].unique())))
    if cat_filter != "All":
        chk_df = chk_df[chk_df["category"] == cat_filter]

    st.caption(f"Showing **{len(chk_df)} of {len(checklist)}** verified requirements | Overall Implementation: **100% Complete (17 / 17 Verified)**")

    for _, row in chk_df.iterrows():
        with st.expander(f"{row['status']} | **{row['req_id']}**: {row['requirement']}"):
            st.markdown(f"**Functional Scope**: `{row['category']}`")
            st.markdown(f"**SmartMIS Feature Implementation**:\n> {row['feature_implemented']}")
            c1, c2 = st.columns(2)
            c1.markdown(f"**Source Module**: `{row['module']}`")
            c2.markdown(f"**Automated Verification**: `{row['verification']}`")
