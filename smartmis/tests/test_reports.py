import io
import json
import os
import sys
import tempfile
from datetime import date, timedelta
import openpyxl
import pandas as pd
import pytest

# Ensure smartmis directory is on path
SMARTMIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SMARTMIS_DIR not in sys.path:
    sys.path.insert(0, SMARTMIS_DIR)

import data
import reports
import scheduler


@pytest.fixture(scope="module")
def sample_df():
    return data.sample_pms(days=45, seed=77)


def test_yaml_template_loading():
    """Verify all 3 approved YAML report templates are discovered and valid."""
    templates = reports.list_templates()
    assert "weekly_foundry" in templates
    assert "weekly_machine_shop" in templates
    assert "monthly_rejection" in templates

    wf = templates["weekly_foundry"]
    assert wf["department"] == "Foundry"
    assert "sections" in wf and len(wf["sections"]) >= 3
    assert "signoff" in wf and "prepared_by" in wf["signoff"]


def test_new_template_extensibility(tmp_path, sample_df):
    """Verify that adding a new YAML file instantly enables a new report without code changes."""
    custom_yaml = """
id: quarterly_executive
title: Quarterly Executive Rejection Summary
department: All
period_type: quarterly
period_days: 90
target_rejection: 3.5
signoff:
  prepared_by: Lead QA Engineer
  reviewed_by: Plant GM
sections:
  - id: by_department
    name: Department Breakdown
    groupby: [department]
    metrics: [produced, rejected, rejection_%]
"""
    tpl_file = tmp_path / "quarterly_executive.yaml"
    tpl_file.write_text(custom_yaml, encoding="utf-8")

    import yaml
    custom_tpl = yaml.safe_load(tpl_file.read_text(encoding="utf-8"))
    sections, title, kpis_map, commentary, _ = reports.prepare_template_report(sample_df, custom_tpl)

    assert "Department Breakdown" in sections
    assert "Quarterly Executive Rejection Summary" in title
    assert len(commentary) > 20


def test_rule_based_auto_commentary(sample_df):
    """Verify auto-commentary contains specific plain-English operational metrics."""
    tpl = reports.get_template("weekly_foundry")
    assert tpl is not None
    commentary = reports.generate_commentary(sample_df, tpl)

    assert isinstance(commentary, str)
    assert len(commentary) > 50
    # Must mention rejection trend, defects, and machinery
    assert any(word in commentary.lower() for word in ["rejection", "rose", "improved", "steady"])
    assert any(word in commentary.lower() for word in ["defect", "blow hole", "shrinkage", "sand inclusion"])
    assert "machine" in commentary.lower()


def test_excel_landscape_kpi_band_and_charts(sample_df):
    """Verify generated Excel workbook has A4 landscape print setup, frozen panes, and charts."""
    tpl = reports.get_template("weekly_machine_shop")
    sections, title, kpis_map, commentary, tpl_dict = reports.prepare_template_report(sample_df, tpl)

    excel_bytes = reports.to_excel_from_template(sections, title, kpi_dict=kpis_map, commentary=commentary, template=tpl_dict)
    assert excel_bytes[:2] == b"PK"

    # Inspect openpyxl workbook
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    assert len(wb.sheetnames) >= 3

    sheet = wb["Daily Trend"]
    # Check landscape print orientation
    assert sheet.page_setup.orientation == sheet.ORIENTATION_LANDSCAPE
    # Check frozen panes
    assert sheet.freeze_panes is not None
    # Check KPI band exists in cells
    assert sheet["A6"].value == "PRODUCED" or "PRODUCED" in str(sheet["A6"].value)


def test_pdf_cover_kpi_table_and_signoff(sample_df):
    """Verify generated PDF contains header cover, KPI summary, and sign-off blocks."""
    tpl = reports.get_template("monthly_rejection")
    sections, title, kpis_map, commentary, tpl_dict = reports.prepare_template_report(sample_df, tpl)

    pdf_bytes = reports.to_pdf_from_template(sections, title, kpi_dict=kpis_map, commentary=commentary, template=tpl_dict)
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 20000  # Substantial PDF with embedded charts and tables


def test_smtp_email_dispatch_dry_run(tmp_path):
    """Verify SMTP email composition and dry-run delivery simulation."""
    dummy_file = tmp_path / "test_report.xlsx"
    dummy_file.write_bytes(b"dummy_content")

    ok, msg = reports.send_report_email(
        [str(dummy_file)],
        recipients="manager@smartmis.local",
        subject="Test Dispatch",
        commentary="Sample commentary",
        dry_run=True,
    )
    assert ok is True
    assert "[DRY-RUN SIMULATION]" in msg
    assert "test_report.xlsx" in msg


def test_scheduler_persistence_and_run(sample_df, tmp_path):
    """Verify schedule configuration persistence, execution with timing, and archive listing."""
    outdir = str(tmp_path / "out_reports")
    gen_files, meta = scheduler.run_scheduled_automation(sample_df, outdir=outdir, send_email=True)

    assert len(gen_files) >= 6  # 3 templates x 2 formats (.xlsx + .pdf)
    assert meta["status"] in ("SUCCESS", "PARTIAL_SUCCESS")
    assert meta["duration_sec"] > 0
    assert "history.json" in os.listdir(outdir)

    # Test report archive browser
    archived = scheduler.list_archived_reports(outdir)
    assert len(archived) == len(gen_files)
    assert "Weekly Foundry" in archived["Report Type"].values
    assert "Format" in archived.columns
