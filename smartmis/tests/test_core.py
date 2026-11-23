import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pandas as pd, pytest, core

@pytest.fixture(scope="module")
def df(): return core.sample_pms()

def test_clean_derives_good(df): assert (df.good == df.produced - df.rejected).all()
def test_clean_missing_columns():
    with pytest.raises(ValueError): core.clean(pd.DataFrame({"date": [1]}))
def test_filters(df):
    f = core.apply_filters(df, "Foundry", shift=["A"]); assert set(f.department) == {"Foundry"} and set(f["shift"]) == {"A"}
def test_weekly_and_monthly(df):
    s, t = core.weekly_report(df, "Foundry"); assert "Daily Trend" in s and "Foundry" in t
    s, _ = core.monthly_rejection_report(df); assert abs(s["By Defect"]["share_%"].sum() - 100) < 0.5
def test_quality_flags_bad_data():
    bad = pd.DataFrame({"date": ["2026-01-01"] * 2, "department": ["Foundry"] * 2, "machine": ["F1"] * 2, "product": ["A"] * 2, "produced": [10, 10], "rejected": [20, 20], "defect": ["x"] * 2})
    msgs = " ".join(m for _, m in core.quality_issues(bad)); assert "rejected > produced" in msgs and "duplicate" in msgs
def test_exports(df):
    s, t = core.weekly_report(df, "Machine Shop"); assert core.to_excel(s, t)[:2] == b"PK" and core.to_pdf(s, t)[:4] == b"%PDF"
def test_kpi_delta(df):
    e = df.date.max(); cur, d = core.kpi_with_delta(df, "All", None, e - pd.Timedelta(days=6), e, None, None); assert cur["Produced"] > 0 and "Produced" in d
