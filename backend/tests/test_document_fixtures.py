import io
import pytest
from PIL import Image, ImageDraw, ImageFont
import fitz  # PyMuPDF
from fastapi.testclient import TestClient

from backend.main import app
from backend.document_parser import (
    extract_document_text,
    parse_semester_documents,
    is_ocr_available,
)

client = TestClient(app)


def create_synthetic_digital_calendar_pdf() -> bytes:
    """Create in-memory digital PDF with selectable text."""
    doc = fitz.open()
    page = doc.new_page()
    text = (
        "ACADEMIC CALENDAR 2026-2027\n"
        "Commencement of Classes: 2026-08-10\n"
        "Independence Day Holiday: 2026-08-15\n"
        "Gandhi Jayanti Holiday: 2026-10-02\n"
        "Working Saturday (mimic Monday): 2026-10-10\n"
        "End Semester Examinations: 2026-12-05\n"
        "Last Working Day: 2026-12-04\n"
    )
    page.insert_text((50, 72), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_synthetic_digital_timetable_pdf() -> bytes:
    """Create in-memory digital timetable PDF with selectable text."""
    doc = fitz.open()
    page = doc.new_page()
    text = (
        "DEPARTMENT OF COMPUTER SCIENCE\n"
        "WEEKLY TIMETABLE\n"
        "Monday: Data Structures, Operating Systems, Computer Networks\n"
        "Tuesday: Database Management Systems Lab (2), Web Technology\n"
        "Wednesday: Operating Systems, Mathematics\n"
        "Thursday: Data Structures, Machine Learning\n"
        "Friday: Computer Networks, Algorithms\n"
    )
    page.insert_text((50, 72), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_synthetic_scanned_pdf() -> bytes:
    """Create in-memory scanned/image-only PDF without digital text."""
    # Generate image
    img = Image.new("RGB", (600, 300), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "SCANNED ACADEMIC SCHEDULE\nStart: 2026-08-10\nEnd: 2026-12-04", fill=(0, 0, 0))
    
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_bytes = img_byte_arr.getvalue()

    doc = fitz.open()
    page = doc.new_page(width=600, height=300)
    rect = fitz.Rect(0, 0, 600, 300)
    page.insert_image(rect, stream=img_bytes)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_synthetic_timetable_image() -> bytes:
    """Create in-memory PNG timetable image."""
    img = Image.new("RGB", (700, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((30, 30), "Monday: Algorithms, Distributed Systems\nTuesday: Networks Lab (2)", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_digital_pdf_pipeline_correctness():
    """Verify digital PDF text extraction extracts exact dates, subjects and multi-period labs."""
    cal_bytes = create_synthetic_digital_calendar_pdf()
    tt_bytes = create_synthetic_digital_timetable_pdf()

    result = parse_semester_documents(
        calendar_data=cal_bytes,
        calendar_filename="calendar.pdf",
        timetable_data=tt_bytes,
        timetable_filename="timetable.pdf",
    )

    # 1. Exact calendar extraction verification
    assert result["semester_start"] == "2026-08-10"
    assert result["last_working_day"] == "2026-12-04"
    assert "2026-08-15" in result["no_class_dates"]
    assert "2026-10-02" in result["no_class_dates"]
    assert len(result["special_classes"]) >= 1
    assert result["special_classes"][0]["date"] == "2026-10-10"

    # 2. Exact timetable extraction verification
    weekdays = result["weekdays"]
    assert len(weekdays["Monday"]) == 3
    monday_subs = [p["subject"] for p in weekdays["Monday"]]
    assert "Data Structures" in monday_subs
    assert "Operating Systems" in monday_subs
    assert "Computer Networks" in monday_subs

    # 3. Multi-period lab verification (DBMS Lab (2) -> periods == 2)
    tue_periods = weekdays["Tuesday"]
    dbms_lab = next(p for p in tue_periods if "Database Management Systems Lab" in p["subject"] or "DBMS Lab" in p["subject"])
    assert dbms_lab["periods"] == 2


def test_scanned_pdf_graceful_handling():
    """Verify scanned PDF without text stream handled gracefully with warning."""
    scanned_cal = create_synthetic_scanned_pdf()
    tt_bytes = create_synthetic_digital_timetable_pdf()

    result = parse_semester_documents(
        calendar_data=scanned_cal,
        calendar_filename="scanned_calendar.pdf",
        timetable_data=tt_bytes,
        timetable_filename="timetable.pdf",
    )

    # Ensure it returns structure without crashing
    assert "weekdays" in result
    assert "notes" in result
    if not is_ocr_available():
        # Expect note warning about scanned pages / Tesseract
        assert any("scanned" in note.lower() or "tesseract" in note.lower() for note in result["notes"])


def test_api_upload_endpoint_integration():
    """Verify POST /api/analyze with multi-part file uploads."""
    cal_bytes = create_synthetic_digital_calendar_pdf()
    tt_bytes = create_synthetic_digital_timetable_pdf()

    response = client.post(
        "/api/analyze",
        files={
            "calendar_file": ("academic_calendar.pdf", cal_bytes, "application/pdf"),
            "timetable_file": ("weekly_timetable.pdf", tt_bytes, "application/pdf"),
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["semester_start"] == "2026-08-10"
    assert data["last_working_day"] == "2026-12-04"
    assert data["processing_time_seconds"] >= 0
    assert "ocr_available" in data


def test_api_upload_oversized_file():
    """Verify 12MB limit rejects oversized files with HTTP 400."""
    huge_data = b"0" * (13 * 1024 * 1024)
    response = client.post(
        "/api/analyze",
        files={
            "calendar_file": ("huge.pdf", huge_data, "application/pdf"),
            "timetable_file": ("valid.pdf", b"%PDF-1.4...", "application/pdf"),
        },
    )
    assert response.status_code == 400
    assert "exceeds the maximum allowed size" in response.json()["detail"]


def test_api_upload_unsupported_mime():
    """Verify unsupported file types rejected."""
    bad_data = b"MZ\x90\x00\x03\x00\x00\x00"
    response = client.post(
        "/api/analyze",
        files={
            "calendar_file": ("script.sh", bad_data, "application/x-sh"),
            "timetable_file": ("valid.pdf", b"%PDF-1.4...", "application/pdf"),
        },
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]
