"""Integration tests for services/validation_service.py"""
import io
import pytest


def _csv_bytes(*rows):
    return "\n".join(rows).encode()


def test_validate_upload_clean_csv():
    from services.validation_service import validate_upload
    # Include Energy+Waste+Water to avoid optional-column warnings → Pass status
    csv = _csv_bytes(
        "Month,Emission,Energy,Waste,Water",
        "Jan,245,180000,12.4,500",
        "Feb,268,195000,11.8,480",
        "Mar,231,172000,13.1,510",
    )
    df, result = validate_upload(csv, "test.csv")
    assert result["status"] == "Pass"
    assert df is not None
    assert len(df) == 3
    assert result["rows_valid"] == 3


def test_validate_upload_missing_emission_column():
    from services.validation_service import validate_upload
    csv = _csv_bytes("Month,Energy", "Jan,180000")
    df, result = validate_upload(csv, "test.csv")
    assert result["status"] == "Fail"
    assert any("Emission" in e for e in result["errors"])


def test_validate_upload_missing_month_column():
    from services.validation_service import validate_upload
    csv = _csv_bytes("Emission,Energy", "245,180000")
    df, result = validate_upload(csv, "test.csv")
    assert result["status"] == "Fail"
    assert any("Month" in e for e in result["errors"])


def test_validate_upload_long_month_names_normalised():
    from services.validation_service import validate_upload
    csv = _csv_bytes("Month,Emission", "January,245", "February,268")
    df, result = validate_upload(csv, "test.csv")
    assert result["normalisation_applied"] is True
    assert list(df["Month"]) == ["Jan", "Feb"]


def test_validate_upload_duplicate_months_warns():
    from services.validation_service import validate_upload
    csv = _csv_bytes("Month,Emission", "Jan,245", "Jan,268", "Feb,231")
    df, result = validate_upload(csv, "test.csv")
    assert any("duplicate" in w.lower() for w in result["warnings"])


def test_validate_upload_wrong_extension():
    from services.validation_service import validate_upload
    csv = _csv_bytes("Month,Emission", "Jan,245")
    df, result = validate_upload(csv, "test.xlsx")
    assert result["status"] == "Fail"


def test_validate_upload_empty_file():
    from services.validation_service import validate_upload
    df, result = validate_upload(b"Month,Emission\n", "empty.csv")
    assert result["status"] == "Fail"


def test_validate_upload_non_numeric_emission():
    from services.validation_service import validate_upload
    csv = _csv_bytes("Month,Emission", "Jan,abc", "Feb,xyz")
    df, result = validate_upload(csv, "test.csv")
    assert result["status"] == "Fail"
    assert any("numeric" in e.lower() for e in result["errors"])


def test_validate_upload_negative_clipped():
    from services.validation_service import validate_upload
    csv = _csv_bytes("Month,Emission", "Jan,-100", "Feb,200")
    df, result = validate_upload(csv, "test.csv")
    assert result["status"] == "Warning"
    assert df["Emission"].min() >= 0


def test_validate_upload_optional_column_missing_warns():
    from services.validation_service import validate_upload
    csv = _csv_bytes("Month,Emission", "Jan,245", "Feb,268")
    df, result = validate_upload(csv, "test.csv")
    assert any("Optional column" in w for w in result["warnings"])


def test_validate_upload_scope_columns_noted():
    from services.validation_service import validate_upload
    csv = _csv_bytes("Month,Emission,Scope1,Scope2,Scope3",
                     "Jan,245,50,150,45")
    df, result = validate_upload(csv, "test.csv")
    assert any("Scope" in w for w in result["warnings"])
