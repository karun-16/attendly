# Attendly extraction fix notes

- Preserved the Quick Calculator and attendance engine.
- Restored backward-compatible parser helpers used by the test suite.
- Fixed the scanned academic-calendar path: OCR text from later pages must not cause the whole PDF to be misclassified as a selectable-text PDF.
- The calendar summary now correctly extracts the instruction dates from the supplied MBU calendar: 2026-07-13 through 2026-11-06.
- Frontend extraction status now checks that Monday-Friday schedules were populated, instead of calling extraction successful just because subject names and dates exist.
- Tesseract still does not confidently reconstruct all weekday cells from the supplied timetable image; the UI should therefore remain in partial/verification mode for that timetable rather than pretending extraction succeeded.

Tests run locally: `PYTHONPATH=. pytest -q` — 28 passed.
