import os
import sys
import tempfile
import pandas as pd
import pytest

# Ensure smartmis directory is on path
SMARTMIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SMARTMIS_DIR not in sys.path:
    sys.path.insert(0, SMARTMIS_DIR)

import auth
import data
import executive
import nlp_query


@pytest.fixture(scope="module")
def sample_df():
    return data.sample_pms(days=45, seed=88)


def test_rbac_authentication_and_scoping(sample_df):
    """Verify role-based authentication and strict departmental scoping for operators."""
    # 1. Successful authentication
    admin = auth.authenticate_user("admin", "admin123")
    assert admin is not None
    assert admin["role"] == "Admin"
    assert admin["department"] == "All"

    foundry_op = auth.authenticate_user("foundry_op", "foundry123")
    assert foundry_op is not None
    assert foundry_op["role"] == "Operator"
    assert foundry_op["department"] == "Foundry"

    # 2. Failed authentication
    bad_login = auth.authenticate_user("admin", "wrong_password")
    assert bad_login is None

    # 3. Departmental Scoping
    admin_view = auth.filter_data_by_role(sample_df, admin)
    assert set(admin_view["department"].unique()) == {"Foundry", "Machine Shop"}

    foundry_view = auth.filter_data_by_role(sample_df, foundry_op)
    assert set(foundry_view["department"].unique()) == {"Foundry"}


def test_audit_logging(tmp_path):
    """Verify enterprise action audit trail recording and retrieval."""
    test_db = str(tmp_path / "test_audit.db")
    auth.init_audit_db(test_db)

    auth.log_audit_action("admin", "Admin", "TEST_ACTION", "Details 123", db_path=test_db)
    logs = auth.get_audit_logs(limit=10, db_path=test_db)

    assert not logs.empty
    assert len(logs) == 1
    assert logs["action"].iloc[0] == "TEST_ACTION"
    assert logs["username"].iloc[0] == "admin"


def test_nlp_whitelisted_queries(sample_df):
    """Verify natural-language queries execute only whitelisted operations without arbitrary code execution."""
    # 1. Top N query
    top_res = nlp_query.ask_your_data(sample_df, "Top 3 defects in Foundry")
    assert top_res["function_called"] == "top_n"
    assert len(top_res["result_table"]) <= 3
    assert top_res["chart_type"] == "bar"

    # 2. Compare query
    cmp_res = nlp_query.ask_your_data(sample_df, "Compare rejection across shifts")
    assert cmp_res["function_called"] == "compare"
    assert "rejection_%" in cmp_res["result_table"].columns

    # 3. Trend query
    tr_res = nlp_query.ask_your_data(sample_df, "Daily production volume trend")
    assert tr_res["function_called"] == "trend"
    assert tr_res["chart_type"] == "line"

    # 4. KPI query
    kpi_res = nlp_query.ask_your_data(sample_df, "What is the plant OEE?")
    assert kpi_res["function_called"] == "kpi"
    assert not kpi_res["result_table"].empty

    # 5. Security: Arbitrary code injection attempt is strictly defused
    malicious = nlp_query.ask_your_data(sample_df, "import os; os.system('rm -rf /')")
    assert malicious["function_called"] in nlp_query.WHITELISTED_FUNCTIONS


def test_smart_insights_generation(sample_df):
    """Verify Smart Insights generates 3 findings and 3 prescriptive actions."""
    findings, actions = executive.generate_smart_insights(sample_df)

    assert len(findings) == 3
    assert len(actions) == 3

    for f in findings:
        assert "title" in f and "text" in f
        assert len(f["title"]) > 3
    for a in actions:
        assert "title" in a and "text" in a and "owner" in a
        assert len(a["owner"]) > 3


def test_executive_summary_one_page_pdf(sample_df):
    """Verify single-page Executive Summary PDF generation for Plant Head."""
    pdf_bytes = executive.generate_executive_summary_pdf(sample_df)
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 15000


def test_powerbi_dataset_export(sample_df, tmp_path):
    """Verify Power BI dimensional model CSV export and DAX guide."""
    out_dir = str(tmp_path / "pbi_out")
    fpath, pbi_df = executive.export_powerbi_dataset(sample_df, outdir=out_dir)

    assert os.path.exists(fpath)
    assert "year" in pbi_df.columns
    assert "month_name" in pbi_df.columns
    assert "week_number" in pbi_df.columns
    assert "scrap_cost_inr" in pbi_df.columns
    assert "total_copq_inr" in pbi_df.columns
    assert "rejection_rate" in pbi_df.columns

    guide = executive.get_powerbi_guide()
    assert "Total COPQ (INR)" in guide
    assert "Plant OEE" in guide
