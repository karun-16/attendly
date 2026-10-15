import os
import pytest
from unittest.mock import patch
from PIL import Image
from backend.document_parser import (
    is_ocr_available,
    get_tesseract_command,
    run_ocr_on_image,
    parse_weekly_timetable,
    extract_document_text,
)


def test_tesseract_cmd_env_resolution(tmp_path):
    """Verify explicit TESSERACT_CMD env variable overrides default paths."""
    fake_tesseract = tmp_path / "mock_tesseract.exe"
    fake_tesseract.write_text("mock binary")

    with patch.dict(os.environ, {"TESSERACT_CMD": str(fake_tesseract)}):
        resolved = get_tesseract_command()
        assert resolved == str(fake_tesseract)


def test_ocr_missing_graceful_handling():
    """Verify that when Tesseract is not available, OCR returns empty string without crashing."""
    with patch("backend.document_parser.is_ocr_available", return_value=False):
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        result = run_ocr_on_image(img)
        assert result == ""


def test_ocr_runtime_exception_handling():
    """Verify that if pytesseract raises an exception during execution, it is caught gracefully."""
    with patch("backend.document_parser.is_ocr_available", return_value=True):
        with patch("pytesseract.image_to_string", side_effect=RuntimeError("Tesseract failed to open file")):
            img = Image.new("RGB", (100, 100), color=(255, 255, 255))
            result = run_ocr_on_image(img)
            assert result == ""


def test_ambiguous_timetable_parsing():
    """Verify that ambiguous timetable with headers or noise produces clean subjects and review notes."""
    ambiguous_text = """
    TIMETABLE BATCH 2026
    Time: 09:00 - 10:00 | 10:00 - 11:00 | Break | 11:30 - 01:00
    Monday: Theory Class, Web Architecture, Lunch, Machine Learning Lab (2)
    Tuesday: Room 101, Discrete Structures, Free Slot
    """
    res = parse_weekly_timetable(ambiguous_text)
    monday_subs = [p["subject"] for p in res["weekdays"]["Monday"]]
    assert "Web Architecture" in monday_subs
    assert "Machine Learning Lab" in monday_subs

    # Lab period verification
    ml_lab = next(p for p in res["weekdays"]["Monday"] if "Machine Learning Lab" in p["subject"])
    assert ml_lab["periods"] == 2

    # Verify noise words like Lunch, Break, Room 101 were ignored
    assert "Lunch" not in res["subjects"]
    assert "Break" not in res["subjects"]
