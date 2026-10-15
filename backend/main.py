from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import os
import time
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.attendance_engine import (
    QuickCalculatorInput,
    QuickCalculatorResult,
    SemesterPlanRequest,
    SemesterPlanResponse,
    calculate_quick_attendance,
    calculate_semester_projections,
)
from backend.document_parser import (
    MAX_FILE_BYTES,
    is_ocr_available,
    parse_semester_documents,
    validate_file_bytes,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("attendly")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND = os.path.join(ROOT, "frontend")

app = FastAPI(
    title="Attendly — Attendance Planner API",
    description="Deterministic student attendance planner and calendar scheduler without cloud AI dependencies.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Thread pool with bounded concurrency for CPU-bound OCR and document parsing
PARSER_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=3,
    thread_name_prefix="attendly_parser_",
)


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Health check endpoint exposing runtime capabilities."""
    return {
        "status": "ok",
        "service": "attendly",
        "version": "2.0.0",
        "ocr_available": is_ocr_available(),
        "ai_dependency": False,
        "mode": "deterministic",
    }


@app.post("/api/calculate-quick", response_model=QuickCalculatorResult)
def quick_calculate(payload: QuickCalculatorInput) -> QuickCalculatorResult:
    """Validate and compute attendance projection for the Quick Calculator."""
    try:
        return calculate_quick_attendance(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/api/analyze")
async def analyze_documents(
    calendar_file: UploadFile = File(...),
    timetable_file: UploadFile = File(...),
) -> dict[str, Any]:
    """Parse academic calendar and weekly timetable files asynchronously.

    Runs extraction in a bounded thread pool to keep the FastAPI event loop responsive.
    No cloud LLM API is invoked.
    """
    start_time = time.perf_counter()

    # Read uploaded bytes with size validation
    cal_name = calendar_file.filename or "calendar"
    tt_name = timetable_file.filename or "timetable"

    cal_bytes = await calendar_file.read()
    tt_bytes = await timetable_file.read()

    try:
        validate_file_bytes(cal_bytes, cal_name)
        validate_file_bytes(tt_bytes, tt_name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # Run deterministic parsing off the event loop
    loop = asyncio.get_running_loop()
    try:
        extracted = await loop.run_in_executor(
            PARSER_EXECUTOR,
            parse_semester_documents,
            cal_bytes,
            cal_name,
            tt_bytes,
            tt_name,
        )
    except Exception as exc:
        logger.exception("Error during document parsing")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse documents: {exc}",
        ) from exc

    elapsed_sec = round(time.perf_counter() - start_time, 2)
    logger.info("Processed '%s' and '%s' in %.2fs", cal_name, tt_name, elapsed_sec)

    extracted["processing_time_seconds"] = elapsed_sec
    extracted["ocr_available"] = is_ocr_available()
    return extracted


@app.post("/api/project", response_model=SemesterPlanResponse)
def project_attendance(payload: SemesterPlanRequest) -> SemesterPlanResponse:
    """Calculate date-wise projections for all subjects across the semester."""
    try:
        return calculate_semester_projections(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/")
def homepage() -> FileResponse:
    return FileResponse(os.path.join(FRONTEND, "index.html"))


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
