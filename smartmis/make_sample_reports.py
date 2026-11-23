"""
Generate fresh, authentic sample reports into sample_reports/ directory.
"""
import os
import sys
from datetime import date

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import config
import data
import reports
import executive

def generate_all_samples():
    sample_dir = os.path.join(current_dir, "sample_reports")
    os.makedirs(sample_dir, exist_ok=True)

    print("Generating simulated PMS dataset...")
    df = data.sample_pms(days=35, seed=42)

    templates = [
        ("weekly_foundry", "weekly_foundry_2026-11-23"),
        ("weekly_machine_shop", "weekly_machine_shop_2026-11-23"),
        ("monthly_rejection", "monthly_rejection_2026-11-23"),
    ]

    for tmpl_id, base_name in templates:
        print(f"Loading template '{tmpl_id}'...")
        tmpl = reports.get_template(tmpl_id)
        if not tmpl:
            # direct fallback
            tmpl_path = os.path.join(current_dir, "reports", "templates", f"{tmpl_id}.yaml")
            import yaml
            with open(tmpl_path, "r", encoding="utf-8") as f_y:
                tmpl = yaml.safe_load(f_y)

        sections, title, cur_kpis, commentary, tmpl_meta = reports.prepare_template_report(df, tmpl)

        xlsx_path = os.path.join(sample_dir, f"{base_name}.xlsx")
        pdf_path = os.path.join(sample_dir, f"{base_name}.pdf")

        excel_bytes = reports.to_excel_from_template(sections, title, cur_kpis, commentary, tmpl_meta)
        with open(xlsx_path, "wb") as f_x:
            f_x.write(excel_bytes)
        print(f"Saved Excel: {xlsx_path} ({len(excel_bytes):,} bytes)")

        pdf_bytes = reports.to_pdf_from_template(sections, title, cur_kpis, commentary, tmpl_meta)
        with open(pdf_path, "wb") as f_p:
            f_p.write(pdf_bytes)
        print(f"Saved PDF: {pdf_path} ({len(pdf_bytes):,} bytes)")

    # Generate Executive Summary 1-Page PDF
    exec_pdf_path = os.path.join(sample_dir, "executive_summary_one_page_2026-11-23.pdf")
    exec_bytes = executive.generate_executive_summary_pdf(df)
    with open(exec_pdf_path, "wb") as f_e:
        f_e.write(exec_bytes)
    print(f"Saved Executive Summary PDF: {exec_pdf_path} ({len(exec_bytes):,} bytes)")
    print("ALL SAMPLE REPORTS GENERATED SUCCESSFULLY!")

if __name__ == "__main__":
    generate_all_samples()
