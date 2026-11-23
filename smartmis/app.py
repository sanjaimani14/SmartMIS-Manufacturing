import json, os, logging
from datetime import date, datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from apscheduler.schedulers.background import BackgroundScheduler
import config, core

logging.basicConfig(level=logging.INFO)
st.set_page_config("SmartMIS - Automated Manufacturing MIS", page_icon="🏭", layout="wide")

st.markdown("""<style>
.hdr{background:linear-gradient(90deg,#1F3A5F,#2B4C7E);padding:18px 24px;border-radius:10px;margin-bottom:14px}
.hdr h1{color:#fff;font-size:26px;margin:0}.hdr p{color:#F4B183;margin:2px 0 0;font-size:14px}
.card{background:#F2F5FA;border-radius:10px;padding:14px 16px;border-left:6px solid #1F3A5F;margin-bottom:10px}
.card.green{border-color:#2E9E5B}.card.amber{border-color:#F2A900}.card.red{border-color:#D93025}
.card .l{color:#555;font-size:13px;font-weight:600}.card .v{font-size:26px;font-weight:700;color:#1F3A5F}.card .d{font-size:12px;color:#555}
.comm-box{background:#F8FAFC;border:1px solid #CBD5E1;border-left:5px solid #1F3A5F;border-radius:8px;padding:14px 18px;margin-bottom:16px}
.comm-box h4{color:#1F3A5F;margin:0 0 6px 0;font-size:14px}
.comm-box p{color:#333;margin:0;font-size:13px;line-height:1.5}
.badge-crit{background:#FCE8E6;color:#C5221F;font-weight:bold;padding:3px 8px;border-radius:10px;font-size:11px}
.badge-warn{background:#FEF7E0;color:#B06000;font-weight:bold;padding:3px 8px;border-radius:10px;font-size:11px}
.badge-info{background:#E8F0FE;color:#1A73E8;font-weight:bold;padding:3px 8px;border-radius:10px;font-size:11px}
</style><div class="hdr"><h1>SmartMIS</h1><p>Automated Manufacturing MIS &amp; Advanced BI Analytics Platform | Sakthi Hackathon 2.0</p></div>""", unsafe_allow_html=True)

# ---- Central Database Initialization ---------------------------------------
core.init_central_db()

@st.cache_resource
def start_scheduler(_get_df):
    s = BackgroundScheduler()
    sched_cfg = core.load_schedule_config()
    s.add_job(lambda: core.run_scheduled_automation(_get_df()), "cron", id="Weekly Foundry + Machine Shop + Rejection", **sched_cfg.get("weekly", config.WEEKLY_CRON))
    s.add_job(lambda: core.run_scheduled_automation(_get_df()), "cron", id="Monthly Rejection Report", **sched_cfg.get("monthly", config.MONTHLY_CRON))
    s.start(); return s

# ---- PMS Integration & Ingestion Controller --------------------------------
st.sidebar.markdown("### 🔌 PMS Connectors & ETL")
src_choice = st.sidebar.selectbox(
    "Data Ingestion Source",
    ["🏭 Realistic Simulator", "📁 CSV / Excel Upload", "🗄️ SQL DB (SQLAlchemy)", "⚡ Live PMS Gateway (API)"]
)

if "ingestion_status" not in st.session_state:
    st.session_state["ingestion_status"] = None

# 1. Simulator Source
if src_choice == "🏭 Realistic Simulator":
    sim_col1, sim_col2 = st.sidebar.columns(2)
    sim_days = sim_col1.number_input("Days", min_value=14, max_value=180, value=90, step=15)
    degrade_on = sim_col2.checkbox("Degrade CNC-02", value=True)
    if st.sidebar.button("🔄 Generate & Sync to Central DB", use_container_width=True):
        sim_df = core.sample_pms(days=int(sim_days), degrade_machine="CNC-02" if degrade_on else "None")
        res = core.incremental_load(sim_df, source_type="Simulator", source_name=f"{sim_days}d_seed")
        st.session_state["ingestion_status"] = f"Ingested {res['inserted']} new records (skipped {res['skipped']} duplicates)."
        st.rerun()

# 2. File Upload & Column Mapping Studio
elif src_choice == "📁 CSV / Excel Upload":
    up_file = st.sidebar.file_uploader("Select PMS File", type=["csv", "xlsx", "xls"])
    if up_file:
        try:
            raw_up = core.read_uploaded_file(up_file, up_file.name)
            st.sidebar.caption(f"Loaded {len(raw_up):,} rows, {len(raw_up.columns)} columns")
            
            with st.sidebar.expander("🛠️ Column Mapping Studio", expanded=True):
                presets = core.load_mapping_presets()
                sel_preset = st.selectbox("Apply Preset", ["-- Auto Detect --"] + list(presets.keys()))
                
                if sel_preset == "-- Auto Detect --":
                    initial_map = core.auto_map_columns(list(raw_up.columns))
                else:
                    initial_map = presets.get(sel_preset, {})
                
                active_mapping = {}
                col_opts = ["(Skip / Default)"] + list(raw_up.columns)
                for req_col in ["date", "department", "machine", "product", "produced", "rejected", "defect", "shift", "planned_qty", "scrap", "rework"]:
                    default_idx = 0
                    guess = initial_map.get(req_col)
                    if guess and guess in raw_up.columns:
                        default_idx = col_opts.index(guess)
                    sel_col = st.selectbox(f"Target: {req_col}", col_opts, index=default_idx, key=f"map_{req_col}")
                    if sel_col != "(Skip / Default)":
                        active_mapping[req_col] = sel_col
                
                new_preset_name = st.text_input("Save as new preset", placeholder="e.g. My Line Export")
                if st.button("💾 Save Preset") and new_preset_name:
                    core.save_mapping_preset(new_preset_name, active_mapping)
                    st.success(f"Saved preset '{new_preset_name}'!")
            
            if st.sidebar.button("📥 Incremental Ingest", type="primary", use_container_width=True):
                mapped_df = core.apply_column_mapping(raw_up, active_mapping)
                issues = core.quality_issues(mapped_df)
                if issues[0][0] == "error":
                    st.sidebar.error(issues[0][1])
                else:
                    res = core.incremental_load(mapped_df, source_type="File Upload", source_name=up_file.name)
                    st.session_state["ingestion_status"] = f"Ingested {res['inserted']} new records from {up_file.name} (skipped {res['skipped']} duplicates)."
                    st.rerun()
        except Exception as ex:
            st.sidebar.error(f"Error reading file: {ex}")

# 3. SQL DB Connector
elif src_choice == "🗄️ SQL DB (SQLAlchemy)":
    sql_url = st.sidebar.text_input("SQLAlchemy Connection URI", value=config.PMS_DATABASE_URL)
    sql_tbl = st.sidebar.text_input("Table / Query", value="pms_production_records")
    
    col_t1, col_t2 = st.sidebar.columns(2)
    if col_t1.button("🔍 Test Conn", use_container_width=True):
        ok, msg = core.test_sql_connection(sql_url)
        if ok:
            st.sidebar.success(f"Connected! Tables: {', '.join(msg[:4])}")
        else:
            st.sidebar.error(f"Failed: {msg}")
            
    if col_t2.button("🌱 Seed Mock DB", use_container_width=True):
        db_file = core.seed_mock_sql_db()
        st.sidebar.success(f"Seeded '{db_file}' with 60d records!")
        
    if st.sidebar.button("📥 Fetch & Incremental Ingest", type="primary", use_container_width=True):
        try:
            sql_df = core.fetch_sql(sql_url, sql_tbl)
            res = core.incremental_load(sql_df, source_type="SQL DB", source_name=sql_url.split('/')[-1])
            st.session_state["ingestion_status"] = f"Ingested {res['inserted']} new records from SQL (skipped {res['skipped']} duplicates)."
            st.rerun()
        except Exception as ex:
            st.sidebar.error(f"SQL Fetch error: {ex}")

# 4. Live REST API Gateway
elif src_choice == "⚡ Live PMS Gateway (API)":
    api_url = st.sidebar.text_input("Gateway Endpoint", value=config.MOCK_PMS_URL)
    st.sidebar.caption("Run server: `python -m mock_pms.server` (Port 8001)")
    
    if st.sidebar.button("🔄 Sync Live PMS Records", type="primary", use_container_width=True):
        ok, res_data = core.fetch_api_pms(api_url)
        if ok and isinstance(res_data, pd.DataFrame):
            res = core.incremental_load(res_data, source_type="Mock PMS API", source_name=api_url)
            st.session_state["ingestion_status"] = f"Ingested {res['inserted']} records from API (skipped {res['skipped']} duplicates)."
            st.rerun()
        else:
            st.sidebar.error(f"Sync failed: {res_data}")

# Status banner
if st.session_state.get("ingestion_status"):
    st.sidebar.success(st.session_state["ingestion_status"])

# ---- Central Database Loading -----------------------------------------------
df = core.load_sqlite()
if df.empty:
    df = core.sample_pms()
    core.incremental_load(df, source_type="Initial Seed", source_name="simulator")
    df = core.load_sqlite()

issues = core.quality_issues(df)
sched = start_scheduler(lambda: df)

with st.sidebar.expander("📊 Central DB & Ingestion Audit Log", expanded=False):
    st.caption(f"Total Central Records: **{len(df):,}** | Range: **{df.date.min()}** to **{df.date.max()}**")
    logs = core.get_ingestion_log()
    if not logs.empty:
        st.dataframe(logs[["timestamp", "source_type", "records_inserted", "records_skipped"]].head(5), hide_index=True)
    if st.button("🧹 Reset Central DB", use_container_width=True):
        core.reset_central_db()
        sim_df = core.sample_pms()
        core.incremental_load(sim_df, source_type="Reset Seed", source_name="simulator")
        st.session_state["ingestion_status"] = "Central DB reset and re-seeded."
        st.rerun()

with st.sidebar.expander("Data Quality Health", expanded=any(l == "warning" for l, _ in issues)):
    for lvl, msg in issues:
        (st.success if lvl == "ok" else st.warning)(msg)

# ---- Filters ---------------------------------------------------------------
st.sidebar.header("Filter Criteria")
dept = st.sidebar.selectbox("Department", ["All", "Foundry", "Machine Shop"])
prods = st.sidebar.multiselect("Product", sorted(df["product"].unique()))
mach = st.sidebar.multiselect("Machine", sorted(df["machine"].unique()))
shift = st.sidebar.multiselect("Shift", sorted(df["shift"].unique()))
period = st.sidebar.radio("Report period", ["This week", "Last week", "This month", "Custom"])
custom = st.sidebar.date_input("Custom range", (df.date.min(), df.date.max())) if period == "Custom" else None
d0, d1 = core.period_bounds(df, period, custom)
f = core.apply_filters(df, dept, prods, d0, d1, shift, mach)

st.caption(f"Period: **{d0:%d %b %Y} to {d1:%d %b %Y}**  |  Department: **{dept}**  |  Rejection Target: **{config.REJECTION_TARGET}%**  |  Records filtered: **{len(f):,}**")

# Phase 3 Tabs Architecture
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📊 Executive Dashboard",
    "📈 SPC & Quality Control",
    "💰 Cost of Poor Quality (COPQ)",
    "🔮 14-Day Forecasting",
    "🔍 Root-Cause Drill-Down",
    "🗓 Weekly MIS Reports",
    "📉 Monthly Rejection Analysis",
    "⏱ Scheduler & Archive"
])

# ==============================================================================
# TAB 1: EXECUTIVE DASHBOARD
# ==============================================================================
with tab1:
    cur, dl = core.kpi_with_delta(df, dept, prods, d0, d1, shift, mach)
    adv_kpi = core.compute_advanced_kpis(f)
    
    # Primary KPI row
    col1, col2, col3, col4 = st.columns(4)
    for c, k in zip([col1, col2, col3, col4], ["Produced", "Good", "Rejected", "Rejection %"]):
        cls = core.status(float(cur[k])) if k == "Rejection %" else ""
        d = dl[k]
        arrow = "" if d is None else ("▲" if d > 0 else "▼" if d < 0 else "■")
        dtxt = "no previous data" if d is None else f"{arrow} {abs(d)}{' pts' if k == 'Rejection %' else '%'} vs previous period"
        c.markdown(f'<div class="card {cls}"><div class="l">{k}</div><div class="v">{cur[k]:,}</div><div class="d">{dtxt}</div></div>', unsafe_allow_html=True)
    
    # Secondary OEE & Manufacturing Intelligence Ribbon
    st.markdown("##### ⚙️ Manufacturing OEE & Quality Intelligence")
    o1, o2, o3, o4, o5, o6 = st.columns(6)
    o1.metric("OEE", f"{adv_kpi['OEE %']}%", f"A:{adv_kpi['Availability %']}% P:{adv_kpi['Performance %']}% Q:{adv_kpi['Quality %']}%")
    o2.metric("First-Pass Yield", f"{adv_kpi['First-Pass Yield %']}%", "Conforming at 1st pass")
    o3.metric("Scrap vs Rework", f"{adv_kpi['Scrap %']}% / {adv_kpi['Rework %']}%", f"{adv_kpi['Scrap']:,} sc / {adv_kpi['Rework']:,} rw")
    o4.metric("Quality PPM", f"{adv_kpi['PPM']:,}", "Parts per million defective")
    o5.metric("Downtime %", f"{adv_kpi['Downtime %']}%", f"{adv_kpi['Total Downtime (hrs)']} hrs total")
    o6.metric("Plan Adherence", f"{adv_kpi['Plan Adherence %']}%", f"Target adherence")
    
    st.write("")
    if f.empty:
        st.warning("No records found matching the active filter criteria.")
    else:
        # Chart Row 1: Production vs Rejection Trend & Pareto
        t = core._rate(f.groupby("date"))
        a, b = st.columns(2)
        combo = go.Figure([
            go.Bar(x=t.date, y=t.produced, name="Produced", marker_color="#1F3A5F"),
            go.Scatter(x=t.date, y=t["rejection_%"], name="Rejection %", yaxis="y2", line=dict(color="#E8420C", width=3))
        ])
        combo.add_hline(y=config.REJECTION_TARGET, yref="y2", line_dash="dash", line_color="gray", annotation_text=f"Target ({config.REJECTION_TARGET}%)")
        combo.update_layout(title="Daily Production Volume vs Rejection % Trend", yaxis2=dict(overlaying="y", side="right"), legend=dict(orientation="h", y=-.2), margin=dict(t=40, b=10))
        a.plotly_chart(combo, use_container_width=True)
        
        p = core.pareto(f)
        par = go.Figure([
            go.Bar(x=p.defect, y=p.rejected, name="Rejected", marker_color="#E8420C"),
            go.Scatter(x=p.defect, y=p["cum_%"], name="Cumulative %", yaxis="y2", line=dict(color="#1F3A5F", width=2))
        ])
        par.update_layout(title="Defect Pareto (80/20 Non-Conformance Analysis)", yaxis2=dict(overlaying="y", side="right", range=[0, 105]), legend=dict(orientation="h", y=-.2), margin=dict(t=40, b=10))
        b.plotly_chart(par, use_container_width=True)
        
        # Chart Row 2: Heatmap & Shift Distribution
        hm = f.groupby(["machine", "date"]).apply(lambda g: 100 * g.rejected.sum() / max(1, g.produced.sum()), include_groups=False).unstack()
        a.plotly_chart(
            px.imshow(hm, aspect="auto", color_continuous_scale=["#2E9E5B", "#F2A900", "#D93025"], title="Machine x Date Rejection Rate Heatmap (%)", labels=dict(color="%")).update_layout(margin=dict(t=40, b=10)),
            use_container_width=True
        )
        
        sh = core._rate(f.groupby("shift"))
        b.plotly_chart(
            px.bar(sh, x="shift", y="rejection_%", color="shift", title="Shift-wise Rejection % (Shift A / B / C)", color_discrete_sequence=["#1F3A5F", "#E8420C", "#7A8CA5"]).update_layout(margin=dict(t=40, b=10), showlegend=False),
            use_container_width=True
        )

# ==============================================================================
# TAB 2: SPC & QUALITY CONTROL
# ==============================================================================
with tab2:
    st.subheader("📈 Statistical Process Control (SPC p-Chart) & Anomaly Alerts")
    
    spc_df, spc_alarms = core.compute_spc_p_chart(f, group_col="date")
    anom_df, anom_alerts = core.detect_anomalies(f)
    
    col_spc1, col_spc2 = st.columns([3, 1])
    with col_spc2:
        st.markdown("##### 🚨 SPC Rules & Control Violations")
        crit_cnt = sum(1 for a in spc_alarms if a["severity"] == "CRITICAL")
        warn_cnt = sum(1 for a in spc_alarms if a["severity"] == "WARNING")
        st.metric("Out-of-Control Points", f"{len(spc_alarms)} points", f"{crit_cnt} beyond 3σ limits")
        for alarm in spc_alarms[:5]:
            badge = "badge-crit" if alarm["severity"] == "CRITICAL" else "badge-warn"
            st.markdown(f"<span class='{badge}'>{alarm['rule']}</span> **{alarm['label']}**: {alarm['value_pct']}% (Limit: {alarm['limit_pct']}%)", unsafe_allow_html=True)
            st.caption(alarm["message"])
            
    with col_spc1:
        if not spc_df.empty:
            fig_p = go.Figure()
            # Historical rate
            fig_p.add_trace(go.Scatter(x=spc_df["date"], y=spc_df["p_pct"], mode="lines+markers", name="Observed Rejection %", line=dict(color="#1F3A5F", width=2)))
            # Centerline
            fig_p.add_trace(go.Scatter(x=spc_df["date"], y=spc_df["cl_pct"], mode="lines", name="Centerline (p-bar)", line=dict(color="#2E9E5B", dash="dash", width=2)))
            # UCL
            fig_p.add_trace(go.Scatter(x=spc_df["date"], y=spc_df["ucl_pct"], mode="lines", name="Upper Control Limit (UCL = +3σ)", line=dict(color="#D93025", dash="dot", width=1.5)))
            # LCL
            fig_p.add_trace(go.Scatter(x=spc_df["date"], y=spc_df["lcl_pct"], mode="lines", name="Lower Control Limit (LCL = -3σ)", line=dict(color="#D93025", dash="dot", width=1.5)))
            
            # Highlight Out-of-control points
            ooc_points = spc_df[spc_df["out_of_control"]]
            if not ooc_points.empty:
                fig_p.add_trace(go.Scatter(
                    x=ooc_points["date"], y=ooc_points["p_pct"], mode="markers", name="Out-of-Control Alarm",
                    marker=dict(color="#E8420C", size=10, symbol="x-thin", line=dict(width=3, color="#D93025"))
                ))
            fig_p.update_layout(title="p-Chart for Non-Conformance Proportion with Dynamic 3-Sigma Limits", yaxis_title="Rejection %", margin=dict(t=40, b=10), legend=dict(orientation="h", y=-.2))
            st.plotly_chart(fig_p, use_container_width=True)
            
    # Anomaly Detection & Actionable Alerts Panel
    st.markdown("---")
    st.subheader("🔔 Real-Time Anomaly Detection Panel (Robust Z-Score)")
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
# TAB 3: COST OF POOR QUALITY (COPQ)
# ==============================================================================
with tab3:
    st.subheader("💰 Cost of Poor Quality (COPQ) & Financial Non-Conformance Loss")
    
    copq_costs = core.load_copq_costs()
    copq_data = core.compute_copq(f, cost_table=copq_costs)
    
    # Financial KPI row
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
    
    # Top 5 Drivers Visualizations
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
        
    # Editable Cost-Per-Part Table
    with st.expander("🛠️ Edit Cost-per-Part Parameters (Scrap & Rework in ₹ INR)", expanded=False):
        st.caption("Adjust part costs to recalculate plant financial COPQ impact in real time.")
        cost_rows = [{"Product": p, "Scrap Cost (₹)": v["scrap"], "Rework Cost (₹)": v["rework"]} for p, v in copq_costs.items()]
        cost_df = pd.DataFrame(cost_rows)
        edited_costs = st.data_editor(cost_df, use_container_width=True, hide_index=True)
        
        if st.button("💾 Save Updated Cost Matrix"):
            updated_dict = {row["Product"]: {"scrap": float(row["Scrap Cost (₹)"]), "rework": float(row["Rework Cost (₹)"])} for _, row in edited_costs.iterrows()}
            core.save_copq_costs(updated_dict)
            st.success("Successfully persisted updated part cost matrix to copq_costs.json!")
            st.rerun()

# ==============================================================================
# TAB 4: 14-DAY FORECASTING
# ==============================================================================
with tab4:
    st.subheader("🔮 Two-Week Manufacturing Projections (Statsmodels Exponential Smoothing)")
    
    with st.spinner("Generating statistical 14-day forecasts and 95% confidence bounds..."):
        fc_data = core.forecast_production_and_rejection(f, horizon_days=14)
        
    fc1, fc2 = st.columns(2)
    # Rejection % Forecast
    rej_fc = fc_data.get("rejection_%", pd.DataFrame())
    if not rej_fc.empty:
        fig_rf = go.Figure()
        # Historical
        hist_part = rej_fc.dropna(subset=["actual"])
        fig_rf.add_trace(go.Scatter(x=hist_part["date"], y=hist_part["actual"], name="Historical Rejection %", line=dict(color="#1F3A5F", width=2)))
        
        # Forecast
        fc_part = rej_fc.dropna(subset=["forecast"])
        fig_rf.add_trace(go.Scatter(x=fc_part["date"], y=fc_part["forecast"], name="14-Day Forecast", line=dict(color="#E8420C", dash="dash", width=2.5)))
        
        # Confidence Band
        fig_rf.add_trace(go.Scatter(x=fc_part["date"], y=fc_part["upper_95"], mode="lines", line=dict(width=0), showlegend=False))
        fig_rf.add_trace(go.Scatter(
            x=fc_part["date"], y=fc_part["lower_95"], mode="lines", fill="tonexty", fillcolor="rgba(232, 66, 12, 0.15)",
            line=dict(width=0), name="95% Confidence Band"
        ))
        fig_rf.add_hline(y=config.REJECTION_TARGET, line_dash="dot", line_color="gray", annotation_text=f"Target ({config.REJECTION_TARGET}%)")
        fig_rf.update_layout(title="Rejection % Trajectory (Historical vs 14-Day Forward Forecast)", yaxis_title="Rejection %", margin=dict(t=40, b=10), legend=dict(orientation="h", y=-.2))
        fc1.plotly_chart(fig_rf, use_container_width=True)
        
    # Production Volume Forecast
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
# TAB 5: ROOT-CAUSE DRILL-DOWN
# ==============================================================================
with tab5:
    st.subheader("🔍 Multi-Level Root-Cause Drill-Down Studio")
    st.caption("Investigate quality non-conformances along the full operational hierarchy:")
    st.markdown("**Department ➔ Machine ➔ Shift ➔ Defect ➔ Heat Number**")
    
    dd_c1, dd_c2, dd_c3, dd_c4, dd_c5 = st.columns(5)
    
    # 1. Department
    dd_dept = dd_c1.selectbox("1. Department", ["All", "Foundry", "Machine Shop"], key="dd_dept")
    
    # 2. Machine
    m_opts = sorted(df[df["department"] == dd_dept]["machine"].unique().tolist()) if dd_dept != "All" else sorted(df["machine"].unique().tolist())
    dd_mach = dd_c2.selectbox("2. Machine", ["All"] + m_opts, key="dd_mach")
    
    # 3. Shift
    dd_shift = dd_c3.selectbox("3. Shift", ["All", "A", "B", "C"], key="dd_shift")
    
    # 4. Defect
    def_sub = df.copy()
    if dd_dept != "All": def_sub = def_sub[def_sub["department"] == dd_dept]
    d_opts = sorted(def_sub[def_sub["defect"] != "None"]["defect"].unique().tolist())
    dd_def = dd_c4.selectbox("4. Defect", ["All"] + d_opts, key="dd_def")
    
    # 5. Heat Number
    heat_opts = sorted(df[(df["heat_no"] != "N/A") & (df["heat_no"].notna())]["heat_no"].unique().tolist())
    dd_heat = dd_c5.selectbox("5. Heat Lot", ["All"] + heat_opts, key="dd_heat")
    
    # Filter dataset for drill-down
    drill_subset = df.copy()
    if dd_dept != "All": drill_subset = drill_subset[drill_subset["department"] == dd_dept]
    if dd_mach != "All": drill_subset = drill_subset[drill_subset["machine"] == dd_mach]
    if dd_shift != "All": drill_subset = drill_subset[drill_subset["shift"] == dd_shift]
    if dd_def != "All": drill_subset = drill_subset[drill_subset["defect"] == dd_def]
    if dd_heat != "All": drill_subset = drill_subset[drill_subset["heat_no"] == dd_heat]
    
    st.markdown(f"**Filtered Breadcrumb:** `{dd_dept}` ➔ `{dd_mach}` ➔ `Shift: {dd_shift}` ➔ `Defect: {dd_def}` ➔ `Heat: {dd_heat}`")
    
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
        
        # Display breakdown
        st.dataframe(
            drill_subset[["date", "department", "machine", "product", "shift", "produced", "rejected", "scrap", "rework", "defect", "heat_no", "customer"]].head(25),
            hide_index=True,
            use_container_width=True
        )

# Helper function to render downloadable reports with commentary and KPI band
def show_template_report(template_id, key_prefix):
    tpl = core.get_template(template_id)
    if not tpl:
        st.error(f"Template '{template_id}' not found.")
        return
        
    sections, title, kpis_map, commentary, tpl_dict = core.prepare_template_report(df, tpl)
    
    st.subheader(title)
    
    # Display Plain-English Auto Commentary
    if commentary:
        st.markdown(f"""
        <div class="comm-box">
          <h4>💡 Automated Executive Commentary:</h4>
          <p>{commentary.replace(chr(10)+chr(10), '</p><p style="margin-top:8px;">')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Section Data Tables
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
    
    # Generate Enhanced Exports
    excel_bytes = core.to_excel_from_template(sections, title, kpi_dict=kpis_map, commentary=commentary, template=tpl_dict)
    pdf_bytes = core.to_pdf_from_template(sections, title, kpi_dict=kpis_map, commentary=commentary, template=tpl_dict)
    
    a, b = st.columns(2)
    a.download_button("⬇ Download Formatted Excel (.xlsx) [Landscape + Charts]", excel_bytes, f"{key_prefix}.xlsx", key=f"{key_prefix}_xl", use_container_width=True)
    b.download_button("⬇ Download Executive PDF (.pdf) [Cover + Sign-Off]", pdf_bytes, f"{key_prefix}.pdf", key=f"{key_prefix}_pdf", use_container_width=True)

# ==============================================================================
# TAB 6: WEEKLY MIS REPORTS
# ==============================================================================
with tab6:
    d = st.radio("Select Department", ["Foundry", "Machine Shop"], horizontal=True)
    t_id = "weekly_foundry" if d == "Foundry" else "weekly_machine_shop"
    show_template_report(t_id, f"weekly_{d.lower().replace(' ', '_')}")

# ==============================================================================
# TAB 7: MONTHLY REJECTION ANALYSIS
# ==============================================================================
with tab7:
    show_template_report("monthly_rejection", "monthly_rejection")

# ==============================================================================
# TAB 8: SCHEDULER & ARCHIVE
# ==============================================================================
with tab8:
    st.subheader("⏱️ Automated Report Schedulers & Document Archive")
    sub_sched, sub_arch = st.tabs(["⚙️ Scheduler & Dispatch Control", "📂 Report Archive & Library"])
    
    with sub_sched:
        st.markdown("##### Active Scheduled Jobs")
        st.dataframe(
            pd.DataFrame([
                {"Job ID": j.id, "Trigger": str(j.trigger), "Next Run Time": j.next_run_time.strftime("%a %d %b %Y %H:%M") if j.next_run_time else "Paused"}
                for j in sched.get_jobs()
            ]),
            hide_index=True,
            use_container_width=True
        )
        
        # Schedule Configuration Editor
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
            
            st.markdown("##### ✉️ Email Dispatch Configuration")
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
                st.success("Successfully saved schedule configuration and re-armed APScheduler triggers!")
                st.rerun()

        # Execution Action Buttons
        col_act1, col_act2, col_act3 = st.columns(3)
        if col_act1.button("▶ Trigger Run Now", type="primary", use_container_width=True):
            with st.spinner("Executing template engine and generating reports..."):
                gen_files, meta = core.run_scheduled_automation(df)
                st.success(f"Generated {len(gen_files)} files in '{config.REPORT_DIR}/' in {meta['duration_sec']}s! Email: {meta['email_delivery']}")
                st.rerun()
                
        if col_act2.button("✉️ Test SMTP Email Dispatch", use_container_width=True):
            archived = core.list_archived_reports()
            if archived.empty:
                st.warning("No generated reports found in archive to email. Click 'Trigger Run Now' first.")
            else:
                sample_paths = archived["Path"].head(2).tolist()
                ok_em, msg_em = core.send_report_email(sample_paths, commentary="Manual dispatch test triggered from UI.")
                if ok_em:
                    st.success(msg_em)
                else:
                    st.error(msg_em)
                    
        if col_act3.button("🔁 Retry Failed Deliverables", use_container_width=True):
            with st.spinner("Retrying report generation..."):
                gen_files, meta = core.run_scheduled_automation(df, max_retries=3)
                st.success(f"Retry execution completed: {meta['status']} ({len(gen_files)} files generated).")
                st.rerun()

        # Detailed Audit Log History
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

    with sub_arch:
        st.subheader("📂 Report Archive & Document Library")
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
                    st.download_button(
                        label=f"⬇ Download {sel_filename}",
                        data=f_obj.read(),
                        file_name=sel_filename,
                        mime=mime_type,
                        type="primary"
                    )
