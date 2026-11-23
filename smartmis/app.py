import json, os, logging
from datetime import date, timedelta
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
.stat-pill{display:inline-block;padding:3px 8px;border-radius:12px;font-size:11px;font-weight:bold;margin-right:4px}
.pill-green{background:#E6F4EA;color:#137333}
.pill-amber{background:#FEF7E0;color:#B06000}
.pill-red{background:#FCE8E6;color:#C5221F}
</style><div class="hdr"><h1>SmartMIS</h1><p>Automated Manufacturing MIS &amp; Rejection Report Generator | Sakthi Hackathon 2.0</p></div>""", unsafe_allow_html=True)

# ---- Central Database Initialization ---------------------------------------
core.init_central_db()

@st.cache_resource
def start_scheduler(_get_df):
    s = BackgroundScheduler()
    s.add_job(lambda: core.run_scheduled(_get_df()), "cron", id="Weekly Foundry + Machine Shop + Rejection", **config.WEEKLY_CRON)
    s.add_job(lambda: core.run_scheduled(_get_df()), "cron", id="Monthly Rejection Report", **config.MONTHLY_CRON)
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
    # First-time initialization fallback
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

tab1, tab2, tab3, tab4 = st.tabs(["📊 Executive Dashboard", "🗓 Weekly MIS Reports", "📉 Monthly Rejection Analysis", "⏱ Scheduler & Automation"])

# ==============================================================================
# TAB 1: EXECUTIVE DASHBOARD
# ==============================================================================
with tab1:
    cur, dl = core.kpi_with_delta(df, dept, prods, d0, d1, shift, mach)
    
    # Primary KPI row
    col1, col2, col3, col4 = st.columns(4)
    for c, k in zip([col1, col2, col3, col4], ["Produced", "Good", "Rejected", "Rejection %"]):
        cls = core.status(float(cur[k])) if k == "Rejection %" else ""
        d = dl[k]
        arrow = "" if d is None else ("▲" if d > 0 else "▼" if d < 0 else "■")
        dtxt = "no previous data" if d is None else f"{arrow} {abs(d)}{' pts' if k == 'Rejection %' else '%'} vs previous period"
        c.markdown(f'<div class="card {cls}"><div class="l">{k}</div><div class="v">{cur[k]:,}</div><div class="d">{dtxt}</div></div>', unsafe_allow_html=True)
    
    # Secondary Manufacturing & Operational KPIs
    if not f.empty:
        c_scrap = int(f["scrap"].sum()) if "scrap" in f.columns else int(cur["Rejected"])
        c_rework = int(f["rework"].sum()) if "rework" in f.columns else 0
        c_planned = int(f["planned_qty"].sum()) if "planned_qty" in f.columns else int(cur["Produced"])
        adherence = round(100.0 * cur["Produced"] / c_planned, 1) if c_planned else 100.0
        total_dt = int(f["downtime_minutes"].sum()) if "downtime_minutes" in f.columns else 0
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Scrap vs Rework", f"{c_scrap:,} sc / {c_rework:,} rw", f"{round(100*c_scrap/(cur['Produced'] or 1), 2)}% Scrap Rate")
        m2.metric("Plan Adherence", f"{adherence}%", f"Plan: {c_planned:,}")
        m3.metric("Total Downtime", f"{total_dt // 60}h {total_dt % 60}m", f"{round(total_dt / (len(f) or 1), 1)} min/batch")
        m4.metric("Active Tooling / Heats", f"{f['heat_no'].nunique() if 'heat_no' in f.columns else '-'} Heats", f"{f['customer'].nunique() if 'customer' in f.columns else '-'} Customers")
    
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
        
        # Chart Row 3: Equipment Degradation & Downtime Reasons
        c1, c2 = st.columns(2)
        if "downtime_reason" in f.columns:
            dt_df = f[f["downtime_reason"] != "None"].groupby("downtime_reason")["downtime_minutes"].sum().reset_index().sort_values("downtime_minutes", ascending=False)
            if not dt_df.empty:
                c1.plotly_chart(
                    px.pie(dt_df, names="downtime_reason", values="downtime_minutes", title="Downtime Root Cause Breakdown (Minutes)", hole=0.4, color_discrete_sequence=px.colors.qualitative.Prism).update_layout(margin=dict(t=40, b=10)),
                    use_container_width=True
                )
        
        # Degradation tracking (highlights CNC-02 tool wear drift)
        mach_trend = f.groupby(["date", "machine"]).apply(lambda g: 100 * g.rejected.sum() / max(1, g.produced.sum()), include_groups=False).reset_index(name="rejection_%")
        fig_mach = px.line(mach_trend, x="date", y="rejection_%", color="machine", title="Machine-wise Wear & Degradation Trend Over Time")
        fig_mach.update_layout(margin=dict(t=40, b=10))
        c2.plotly_chart(fig_mach, use_container_width=True)

# Helper function to render downloadable reports
def show(sheets, title, key):
    st.subheader(title)
    for n, tb in sheets.items():
        st.caption(f"**{n}**")
        st.dataframe(
            tb.style.map(
                lambda v: "background:#F8CBAD;font-weight:bold" if isinstance(v, float) and v > config.REJECTION_TARGET else "",
                subset=[c for c in tb.columns if c == "rejection_%"]
            ),
            use_container_width=True,
            hide_index=True
        )
    a, b = st.columns(2)
    a.download_button("⬇ Download Formatted Excel (.xlsx)", core.to_excel(sheets, title), f"{key}.xlsx", key=key + "x", use_container_width=True)
    b.download_button("⬇ Download Formatted PDF (.pdf)", core.to_pdf(sheets, title), f"{key}.pdf", key=key + "p", use_container_width=True)

# ==============================================================================
# TAB 2: WEEKLY MIS REPORTS
# ==============================================================================
with tab2:
    d = st.radio("Select Department", ["Foundry", "Machine Shop"], horizontal=True)
    show(*core.weekly_report(df, d), key="weekly_" + d.lower().replace(" ", "_"))

# ==============================================================================
# TAB 3: MONTHLY REJECTION ANALYSIS
# ==============================================================================
with tab3:
    show(*core.monthly_rejection_report(df), key="monthly_rejection")

# ==============================================================================
# TAB 4: SCHEDULER & AUTOMATION
# ==============================================================================
with tab4:
    st.subheader("Automated Report Schedulers (APScheduler Engine)")
    st.dataframe(
        pd.DataFrame([
            {"Job ID": j.id, "Trigger": str(j.trigger), "Next Run Time": j.next_run_time.strftime("%a %d %b %Y %H:%M") if j.next_run_time else "Paused"}
            for j in sched.get_jobs()
        ]),
        hide_index=True,
        use_container_width=True
    )
    
    col_run1, col_run2 = st.columns([1, 3])
    if col_run1.button("▶ Trigger Run Now", type="primary", use_container_width=True):
        generated = core.run_scheduled(df)
        col_run2.success(f"Generated {len(generated)} report files into '{config.REPORT_DIR}/'")
    
    hist = f"{config.REPORT_DIR}/history.json"
    if os.path.exists(hist):
        st.markdown("---")
        st.subheader("Report Dispatch History")
        st.dataframe(pd.DataFrame(json.load(open(hist))[::-1]), hide_index=True, use_container_width=True)
