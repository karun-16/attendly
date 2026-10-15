import pytest
from backend.document_parser import (
    parse_academic_calendar,
    parse_weekly_timetable,
    validate_file_bytes,
)


def test_validate_file_bytes_valid_and_invalid():
    # Valid PDF signature
    pdf_bytes = b"%PDF-1.5 test content"
    assert validate_file_bytes(pdf_bytes, "doc.pdf") == "application/pdf"

    # Valid PNG signature
    png_bytes = b"\x89PNG\r\n\x1a\nfakeimage"
    assert validate_file_bytes(png_bytes, "img.png") == "image/png"

    # Empty file
    with pytest.raises(ValueError, match="is empty"):
        validate_file_bytes(b"", "empty.pdf")

    # Unsupported extension
    with pytest.raises(ValueError, match="Unsupported file format"):
        validate_file_bytes(b"hello", "file.exe")


def test_parse_academic_calendar_sample():
    sample_text = """
    ACADEMIC CALENDAR 2026-2027
    Commencement of Classes: 2026-08-10
    Independence Day Holiday: 2026-08-15
    Gandhi Jayanti Holiday: 2026-10-02
    Working Saturday (Monday schedule): 2026-10-10
    Last Working Day: 2026-12-04
    End Semester Examinations: 2026-12-10
    """
    res = parse_academic_calendar(sample_text)
    assert res["semester_start"] == "2026-08-10"
    assert res["last_working_day"] == "2026-12-04"
    assert "2026-08-15" in res["no_class_dates"]
    assert "2026-10-02" in res["no_class_dates"]
    assert len(res["special_working_days"]) >= 1
    assert res["special_working_days"][0]["date"] == "2026-10-10"


def test_parse_weekly_timetable_sample():
    sample_tt = """
    DEPARTMENT OF COMPUTER SCIENCE - TIMETABLE
    Monday: Data Structures, Operating Systems, Algorithms
    Tuesday: DBMS Lab (2), Computer Networks
    Wednesday: Operating Systems, Mathematics
    Thursday: Data Structures, DBMS
    Friday: Algorithms, Technical Communication
    """
    res = parse_weekly_timetable(sample_tt)
    weekdays = res["weekdays"]
    assert len(weekdays["Monday"]) == 3
    assert any(p["subject"] == "Data Structures" for p in weekdays["Monday"])
    
    # Check multi-period lab
    tue_periods = weekdays["Tuesday"]
    dbms_lab = next(p for p in tue_periods if "DBMS Lab" in p["subject"])
    assert dbms_lab["periods"] == 2

    assert "Operating Systems" in res["subjects"]
    assert "Algorithms" in res["subjects"]
