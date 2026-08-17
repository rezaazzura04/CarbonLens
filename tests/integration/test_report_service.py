"""Integration tests for services/report_service.py"""
import pytest


@pytest.fixture
def org():
    return {
        "org_id": "test-org-001", "company_name": "PT Test Energi",
        "sector": "Manufacturing", "area_m2": 5000.0,
        "province": "Jawa Timur", "reporting_period": "2024",
        "renew_pct": 20.0, "recycle_pct": 15.0, "certifications": [],
    }


@pytest.fixture
def state():
    """Minimal ComputedState for testing report_service without full orchestration."""
    return {
        "state_id": "abc-123",
        "org_id":   "test-org-001",
        "period":   "2024",
        "version":  1,
        "previous_version_id": None,
        "input_hash": "deadbeef",
        "status": "Provisional",
        "carbon": {
            "scope1_kg": 50000.0, "scope2_kg": 100000.0,
            "scope3_kg": 25000.0, "total_kg": 175000.0,
            "intens_m2": 35.0, "scope_source": "carbon_accounting",
            "province": "Jawa Timur", "pln_ef_used": 0.781,
            "scope3_breakdown": {}, "screened_excluded": [],
            "benchmark": 120.0, "gap": {"gap_pct": -70.8, "above_benchmark": False},
            "computed_at": "2024-01-01T00:00:00",
        },
        "esg": {
            "org_id": "test-org-001", "score": 72.5, "grade": "B",
            "label": "Satisfactory", "env": 80.0, "social": 65.0, "gov": 70.0,
            "confidence_score": 100.0, "is_provisional": False,
            "n_disclosed": 8, "n_total_indicators": 8,
            "disclosure_summary": "8 of 8 disclosed",
            "methodology_version": "V8-Phase4",
            "methodology_disclaimer": "Substantive score.",
            "computed_at": "2024-01-01T00:00:00",
        },
        "data_quality": {
            "completeness_score": 85.0, "consistency_score": 100.0,
            "validation_status": "Pass", "validation_score": 100.0,
            "confidence_score": 92.5, "is_provisional": False,
            "env_completeness": 90.0, "sg_completeness": 100.0,
            "sg_disclosed": 8, "sg_total": 8,
            "flagged_fields": [], "summary": "Confidence 93%",
        },
        "confidence": {
            "esg_confidence": 100.0, "esg_is_provisional": False,
            "dq_confidence": 92.5, "dq_is_provisional": False,
            "interpretation": "Substantive.",
        },
        "computed_at": "2024-01-01T00:00:00",
        "computation_time_ms": 150,
    }


def test_build_report_context_schema(state, org, monkeypatch):
    from services.report_service import build_report_context
    # Patch session reads to avoid Streamlit dependency
    monkeypatch.setattr(
        "repository.session_repo.get", lambda k, **kw: None, raising=False
    )
    monkeypatch.setattr(
        "repository.session_repo.get_uploaded_df", lambda: None, raising=False
    )
    ctx = build_report_context(state, org)
    for key in ["company","esg_score","esg_grade","scope1_tco2e","scope2_tco2e",
                "scope3_tco2e","total_tco2e","intensity_kg_m2","dq_confidence",
                "generated_at","platform_version"]:
        assert key in ctx, f"Missing: {key}"


def test_build_report_context_totals(state, org, monkeypatch):
    from services.report_service import build_report_context
    monkeypatch.setattr("repository.session_repo.get", lambda k, **kw: None, raising=False)
    monkeypatch.setattr("repository.session_repo.get_uploaded_df", lambda: None, raising=False)
    ctx = build_report_context(state, org)
    expected = round(ctx["scope1_tco2e"] + ctx["scope2_tco2e"] + ctx["scope3_tco2e"], 2)
    assert abs(ctx["total_tco2e"] - expected) < 0.01


def test_build_snapshot_schema(state, org):
    from services.report_service import build_snapshot
    snap = build_snapshot(state, org)
    for key in ["snapshot_ts","state_id","esg_score","total_tco2e",
                "is_provisional","dq_confidence","platform_version"]:
        assert key in snap, f"Missing: {key}"


def test_build_csv_output(state, org, monkeypatch):
    from services.report_service import build_report_context, build_csv
    monkeypatch.setattr("repository.session_repo.get", lambda k, **kw: None, raising=False)
    monkeypatch.setattr("repository.session_repo.get_uploaded_df", lambda: None, raising=False)
    ctx = build_report_context(state, org)
    csv = build_csv(ctx)
    assert isinstance(csv, str)
    assert "ESG" in csv
    assert "CARBON" in csv
    assert "PT Test Energi" in csv


def test_build_json_output(state, org, monkeypatch):
    import json
    from services.report_service import build_report_context, build_json
    monkeypatch.setattr("repository.session_repo.get", lambda k, **kw: None, raising=False)
    monkeypatch.setattr("repository.session_repo.get_uploaded_df", lambda: None, raising=False)
    ctx = build_report_context(state, org)
    jstr = build_json(ctx)
    parsed = json.loads(jstr)
    assert "esg_score" in parsed
    assert "company" in parsed


def test_build_excel_output(state, org, monkeypatch):
    from services.report_service import build_report_context, build_excel
    monkeypatch.setattr("repository.session_repo.get", lambda k, **kw: None, raising=False)
    monkeypatch.setattr("repository.session_repo.get_uploaded_df", lambda: None, raising=False)
    ctx = build_report_context(state, org)
    excel_bytes = build_excel(ctx)
    assert isinstance(excel_bytes, bytes)
    # Excel files start with PK (zip signature)
    assert excel_bytes[:2] == b"PK"
