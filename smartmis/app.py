import json, os, logging
import pandas as pd, plotly.express as px, plotly.graph_objects as go, streamlit as st
from apscheduler.schedulers.background import BackgroundScheduler
import config, core

logging.basicConfig(level=logging.INFO)
st.set_page_config("SmartMIS", page_icon="🏭", layout="wide")
st.markdown("""<style>
.hdr{background:linear-gradient(90deg,#1F3A5F,#2B4C7E);padding:18px 24px;border-radius:10px;margin-bottom:14px}
.hdr h1{color:#fff;font-size:26px;margin:0}.hdr p{color:#F4B183;margin:2px 0 0;font-size:14px}
.card{background:#F2F5FA;border-radius:10px;padding:14px 16px;border-left:6px solid #1F3A5F}
.card.green{border-color:#2E9E5B}.card.amber{border-color:#F2A900}.card.red{border-color:#D93025}
.card .l{color:#555;font-size:13px}.card .v{font-size:28px;font-weight:700;color:#1F3A5F}.card .d{font-size:12px;color:#555}
</style><div class="hdr"><h1>SmartMIS</h1><p>Automated Manufacturing MIS &amp; Rejection Report Generator</p></div>""", unsafe_allow_html=True)

@st.cache_resource
def start_scheduler(_get_df):
    s = BackgroundScheduler()
    s.add_job(lambda: core.run_scheduled(_get_df()), "cron", id="Weekly Foundry + Machine Shop + Rejection", **config.WEEKLY_CRON)
    s.add_job(lambda: core.run_scheduled(_get_df()), "cron", id="Monthly Rejection Report", **config.MONTHLY_CRON)
    s.start(); return s

# ---- import + data quality -------------------------------------------------
up = st.sidebar.file_uploader("Import PMS data (CSV/Excel)", type=["csv", "xlsx"])
if up:
    raw = pd.read_csv(up) if up.name.endswith(".csv") else pd.read_excel(up)
    issues = core.quality_issues(raw)
    if issues[0][0] == "error": st.sidebar.error(issues[0][1]); st.stop()
    df = core.clean(raw)
else:
    df = core.sample_pms(); issues = core.quality_issues(df); st.sidebar.info("Using built-in sample PMS data")
core.save_sqlite(df); df = core.load_sqlite()          # central database step
sched = start_scheduler(lambda: df)
with st.sidebar.expander("Data quality", expanded=any(l == "warning" for l, _ in issues)):
    for lvl, msg in issues: (st.success if lvl == "ok" else st.warning)(msg)

# ---- filters ---------------------------------------------------------------
st.sidebar.header("Filters")
dept = st.sidebar.selectbox("Department", ["All", "Foundry", "Machine Shop"])
prods = st.sidebar.multiselect("Product", sorted(df["product"].unique()))
mach = st.sidebar.multiselect("Machine", sorted(df["machine"].unique()))
shift = st.sidebar.multiselect("Shift", sorted(df["shift"].unique()))
period = st.sidebar.radio("Report period", ["This week", "Last week", "This month", "Custom"])
custom = st.sidebar.date_input("Custom range", (df.date.min(), df.date.max())) if period == "Custom" else None
d0, d1 = core.period_bounds(df, period, custom)
f = core.apply_filters(df, dept, prods, d0, d1, shift, mach)
st.caption(f"Period: **{d0:%d %b %Y} to {d1:%d %b %Y}**  |  Department: **{dept}**  |  Rejection target: **{config.REJECTION_TARGET}%**")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🗓 Weekly MIS", "📉 Monthly Rejection", "⏱ Scheduler"])

with tab1:
    cur, dl = core.kpi_with_delta(df, dept, prods, d0, d1, shift, mach)
    for c, k in zip(st.columns(4), ["Produced", "Good", "Rejected", "Rejection %"]):
        cls = core.status(float(cur[k])) if k == "Rejection %" else ""
        d = dl[k]; arrow = "" if d is None else ("▲" if d > 0 else "▼" if d < 0 else "■")
        dtxt = "no previous data" if d is None else f"{arrow} {abs(d)}{' pts' if k == 'Rejection %' else '%'} vs previous period"
        c.markdown(f'<div class="card {cls}"><div class="l">{k}</div><div class="v">{cur[k]:,}</div><div class="d">{dtxt}</div></div>', unsafe_allow_html=True)
    st.write("")
    t = core._rate(f.groupby("date")); a, b = st.columns(2)
    combo = go.Figure([go.Bar(x=t.date, y=t.produced, name="Produced", marker_color="#1F3A5F"),
                       go.Scatter(x=t.date, y=t["rejection_%"], name="Rejection %", yaxis="y2", line=dict(color="#E8420C", width=3))])
    combo.update_layout(title="Production vs rejection %", yaxis2=dict(overlaying="y", side="right"), legend=dict(orientation="h", y=-.2), margin=dict(t=40, b=10))
    a.plotly_chart(combo, use_container_width=True)
    p = core.pareto(f)
    par = go.Figure([go.Bar(x=p.defect, y=p.rejected, name="Rejected", marker_color="#E8420C"),
                     go.Scatter(x=p.defect, y=p["cum_%"], name="Cumulative %", yaxis="y2", line=dict(color="#1F3A5F"))])
    par.update_layout(title="Defect Pareto", yaxis2=dict(overlaying="y", side="right", range=[0, 105]), legend=dict(orientation="h", y=-.2), margin=dict(t=40, b=10))
    b.plotly_chart(par, use_container_width=True)
    hm = f.groupby(["machine", "date"]).apply(lambda g: 100 * g.rejected.sum() / g.produced.sum(), include_groups=False).unstack()
    a.plotly_chart(px.imshow(hm, aspect="auto", color_continuous_scale=["#2E9E5B", "#F2A900", "#D93025"], title="Rejection % heatmap (machine x date)", labels=dict(color="%")).update_layout(margin=dict(t=40, b=10)), use_container_width=True)
    sh = core._rate(f.groupby("shift"))
    b.plotly_chart(px.bar(sh, x="shift", y="rejection_%", color="shift", title="Shift-wise rejection %", color_discrete_sequence=["#1F3A5F", "#E8420C", "#7A8CA5"]).update_layout(margin=dict(t=40, b=10), showlegend=False), use_container_width=True)

def show(sheets, title, key):
    st.subheader(title)
    for n, tb in sheets.items():
        st.caption(n); st.dataframe(tb.style.map(lambda v: "background:#F8CBAD" if isinstance(v, float) and v > config.REJECTION_TARGET else "", subset=[c for c in tb.columns if c == "rejection_%"]), use_container_width=True, hide_index=True)
    a, b = st.columns(2)
    a.download_button("⬇ Download Excel", core.to_excel(sheets, title), f"{key}.xlsx", key=key + "x")
    b.download_button("⬇ Download PDF", core.to_pdf(sheets, title), f"{key}.pdf", key=key + "p")
with tab2:
    d = st.radio("Report", ["Foundry", "Machine Shop"], horizontal=True)
    show(*core.weekly_report(df, d), key="weekly_" + d.lower().replace(" ", "_"))
with tab3: show(*core.monthly_rejection_report(df), key="monthly_rejection")
with tab4:
    st.subheader("Scheduled jobs")
    st.dataframe(pd.DataFrame([{"Job": j.id, "Next run": j.next_run_time.strftime("%a %d %b %Y %H:%M") if j.next_run_time else "-"} for j in sched.get_jobs()]), hide_index=True, use_container_width=True)
    if st.button("▶ Run now", type="primary"): st.success(f"Generated {len(core.run_scheduled(df))} files in '{config.REPORT_DIR}/'")
    hist = f"{config.REPORT_DIR}/history.json"
    if os.path.exists(hist): st.caption("Run history"); st.dataframe(pd.DataFrame(json.load(open(hist))[::-1]), hide_index=True)
