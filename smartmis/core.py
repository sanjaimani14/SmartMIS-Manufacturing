import io, json, os, logging, numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import config
from datetime import date, timedelta
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.formatting.rule import CellIsRule
from reportlab.platypus import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer

# Import and re-export data layer for 100% backwards-compatibility
from data import (
    PRODUCTS, MACHINES, DEFECTS, DEFECT_CATEGORIES, CUSTOMERS, PATTERN_MAP,
    DOWNTIME_REASONS, SHIFTS, CANONICAL_COLUMNS, DEFAULT_PRESETS,
    sample_pms, clean, quality_issues, auto_map_columns, apply_column_mapping,
    save_mapping_preset, load_mapping_presets, read_uploaded_file,
    test_sql_connection, fetch_sql, seed_mock_sql_db, fetch_api_pms,
    init_central_db, save_sqlite, load_sqlite, incremental_load,
    get_ingestion_log, reset_central_db
)

log = logging.getLogger('smartmis')

def apply_filters(df, dept=None, products=None, start=None, end=None, shift=None, machines=None):
    if dept and dept != "All": df = df[df.department == dept]
    if products: df = df[df["product"].isin(products)]
    if shift: df = df[df["shift"].isin(shift)]
    if machines: df = df[df.machine.isin(machines)]
    if start: df = df[df.date >= start]
    if end: df = df[df.date <= end]
    return df

def kpis(df):
    p, r = df.produced.sum(), df.rejected.sum()
    return {"Produced": int(p), "Good": int(p - r), "Rejected": int(r), "Rejection %": round(100 * r / p, 2) if p else 0}

def _rate(g): 
    g = g.agg(produced=("produced", "sum"), rejected=("rejected", "sum")).reset_index()
    g["rejection_%"] = (100 * g.rejected / g.produced).round(2); return g

def weekly_report(df, dept, end=None):
    end = end or df.date.max(); w = apply_filters(df, dept, None, end - timedelta(days=6), end)
    return {"Daily Trend": _rate(w.groupby("date")), "By Machine": _rate(w.groupby("machine")),
            "By Product": _rate(w.groupby("product"))}, f"Weekly {dept} Report ({end - timedelta(days=6)} to {end})"

def monthly_rejection_report(df, end=None):
    end = end or df.date.max(); m = apply_filters(df, None, None, end - timedelta(days=29), end)
    d = m[m.rejected > 0].groupby(["department", "defect"]).rejected.sum().reset_index().sort_values("rejected", ascending=False)
    d["share_%"] = (100 * d.rejected / d.rejected.sum()).round(2)
    return {"By Defect": d, "By Department": _rate(m.groupby("department")), "By Product": _rate(m.groupby("product")),
            "Daily Trend": _rate(m.groupby("date"))}, f"Monthly Rejection Report ({end - timedelta(days=29)} to {end})"

def period_bounds(df, choice, custom=None):
    end = df.date.max()
    if choice == "This week": return end - timedelta(days=6), end
    if choice == "Last week": return end - timedelta(days=13), end - timedelta(days=7)
    if choice == "This month": return end - timedelta(days=29), end
    return (custom[0], custom[1]) if custom and len(custom) == 2 else (df.date.min(), end)

def kpi_with_delta(df, dept, products, start, end, shift, machines):
    """KPIs for the window and % change vs the previous window of equal length."""
    cur = kpis(apply_filters(df, dept, products, start, end, shift, machines))
    span = (end - start).days + 1; ps, pe = start - timedelta(days=span), start - timedelta(days=1)
    prev = kpis(apply_filters(df, dept, products, ps, pe, shift, machines))
    delta = {k: (round(100 * (cur[k] - prev[k]) / prev[k], 1) if prev[k] else None) for k in cur}
    delta["Rejection %"] = round(float(cur["Rejection %"]) - float(prev["Rejection %"]), 2)
    return cur, delta

def status(rej):
    return "green" if rej <= config.REJECTION_TARGET else ("amber" if rej <= config.AMBER_LIMIT else "red")

def pareto(df):
    d = df[df.rejected > 0].groupby("defect").rejected.sum().sort_values(ascending=False).reset_index()
    d["cum_%"] = (100 * d.rejected.cumsum() / d.rejected.sum()).round(1); return d

def to_excel(sheets, title):
    buf = io.BytesIO(); navy = PatternFill("solid", fgColor="1F3A5F"); red = PatternFill("solid", bgColor="F8CBAD", fgColor="F8CBAD")
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for name, t in sheets.items():
            t.to_excel(xw, sheet_name=name, index=False, startrow=3); ws = xw.sheets[name]
            ws["A1"] = f"{config.COMPANY} - {title}"; ws["A1"].font = Font(size=14, bold=True, color="1F3A5F")
            ws["A2"] = f"Generated {date.today():%d-%b-%Y} by SmartMIS"; ws["A2"].font = Font(italic=True, color="777777")
            for c in ws[4]: c.fill, c.font, c.alignment = navy, Font(bold=True, color="FFFFFF"), Alignment(horizontal="center")
            for col in ws.columns: ws.column_dimensions[col[0].column_letter].width = 18
            ws.freeze_panes = "A5"
            for col in ws.iter_cols(min_row=5, max_row=4 + len(t)):
                for c in col:
                    if isinstance(c.value, float): c.number_format = "0.00"
                    elif isinstance(c.value, int): c.number_format = "#,##0"
            if "rejection_%" in t.columns and len(t):
                ci = t.columns.get_loc("rejection_%") + 1; L = ws.cell(4, ci).column_letter
                ws.conditional_formatting.add(f"{L}5:{L}{4 + len(t)}", CellIsRule(operator="greaterThan", formula=[str(config.REJECTION_TARGET)], fill=red))
                ch = BarChart(); ch.title = f"Rejection % - {name}"; ch.height, ch.width = 7.5, 15
                ch.add_data(Reference(ws, min_col=ci, min_row=4, max_row=4 + len(t)), titles_from_data=True)
                ch.set_categories(Reference(ws, min_col=1, min_row=5, max_row=4 + len(t))); ws.add_chart(ch, f"{ws.cell(1, len(t.columns) + 2).column_letter}4")
    return buf.getvalue()

def _chart_png(t, name):
    fig, ax = plt.subplots(figsize=(7, 2.4)); x = t.iloc[:, 0].astype(str)
    if "rejection_%" in t.columns:
        (ax.plot(x, t["rejection_%"], color="#E8420C") if len(t) > 12 else ax.bar(x, t["rejection_%"], color="#1F3A5F"))
        ax.axhline(config.REJECTION_TARGET, ls="--", color="grey", lw=.8); ax.set_ylabel("Rejection %", fontsize=8)
    else: ax.bar(x, t.iloc[:, 2] if t.shape[1] > 2 else t.iloc[:, 1], color="#1F3A5F")
    ax.set_title(name, fontsize=9, loc="left"); ax.tick_params(labelsize=7)
    if len(t) > 12: ax.set_xticks(range(0, len(t), max(1, len(t) // 8)))
    plt.xticks(rotation=30); [ax.spines[s].set_visible(False) for s in ("top", "right")]; fig.tight_layout()
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=130); plt.close(fig); b.seek(0); return b

def to_pdf(sheets, title):
    buf = io.BytesIO(); st = getSampleStyleSheet()
    def footer(c, d):
        c.setFont("Helvetica", 8); c.setFillColor(colors.grey)
        c.drawString(36, 22, "Generated by SmartMIS"); c.drawRightString(A4[0] - 36, 22, f"Page {d.page}")
    els = [Paragraph(f"{config.COMPANY}", st["Normal"]), Paragraph(title, st["Title"]), Paragraph(f"Generated {date.today():%d-%b-%Y}", st["Normal"]), Spacer(1, 10)]
    first = next(iter(sheets.values()))
    if "produced" in first.columns:
        p, r = first.produced.sum(), first.rejected.sum()
        kt = Table([["Produced", "Rejected", "Rejection %"], [f"{int(p):,}", f"{int(r):,}", f"{100 * r / p:.2f}" if p else "0"]], colWidths=[130] * 3)
        kt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8420C")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("FONTSIZE", (0, 1), (-1, 1), 14)])); els += [kt, Spacer(1, 12)]
    for name, t in sheets.items():
        els += [Paragraph(name, st["Heading2"]), Image(_chart_png(t, name), width=440, height=150)]
        tb = Table([list(t.columns)] + t.head(12).astype(str).values.tolist(), repeatRows=1)
        tb.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .25, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 8), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F5FA")])]))
        els += [tb, Spacer(1, 12)]
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=36, rightMargin=36).build(els, onFirstPage=footer, onLaterPages=footer); return buf.getvalue()

def run_scheduled(df, outdir=None):
    """Called by APScheduler / Run-now: writes weekly + monthly reports and logs history."""
    outdir = outdir or config.REPORT_DIR; os.makedirs(outdir, exist_ok=True); stamp = date.today().isoformat(); out = []
    jobs = [(weekly_report(df, "Foundry"), "weekly_foundry"), (weekly_report(df, "Machine Shop"), "weekly_machine_shop"), (monthly_rejection_report(df), "monthly_rejection")]
    for (sheets, title), name in jobs:
        for ext, fn in (("xlsx", to_excel), ("pdf", to_pdf)):
            p = f"{outdir}/{name}_{stamp}.{ext}"; open(p, "wb").write(fn(sheets, title)); out.append(p)
    hist = f"{outdir}/history.json"; h = json.load(open(hist)) if os.path.exists(hist) else []
    h.append({"time": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "files": len(out)}); json.dump(h[-20:], open(hist, "w"))
    log.info("Generated %d report files", len(out)); return out
