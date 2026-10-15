# Attendly — Production-Ready Attendance Planner

A privacy-focused, zero-cloud-dependency attendance calculator and semester planner for college students.

Attendly is designed to run anywhere — locally or in Docker containers — **without requiring OpenAI, Gemini, Ollama, API keys, or paid generative AI quotas**.

---

## 1. Features

- **Quick Calculator**:
  - Calculates present percentage, required future classes, and safe skip capacity.
  - Supports standard targets (75%, 80%, 85%, 90%) and custom decimal targets (e.g., 78.5%).
  - Mathematically sound ceiling logic: $\max(0, \lceil R \times (T + N) - P \rceil)$.
  - Handles boundary conditions (0 classes conducted so far, unachievable targets, exact percentages).

- **Semester Planner**:
  - Upload digital or scanned academic calendars and weekly timetables (PDF, PNG, JPG, WEBP).
  - Deterministic text extraction via **PyMuPDF** with **Tesseract OCR** fallback.
  - Interactive Review Screen:
    - View and customize projection start date and semester last working day.
    - Weekly schedule tabbed editor with multi-period lab support (e.g. 2+ periods).
    - Holiday and exam suspension tag cloud with date-wise exclusions.
    - Subject-wise present and total class tracking.
    - **Manual Entry Fallback**: Students can plan their semester immediately even without uploading any documents.
  - Day-by-day date simulation across the academic calendar.

---

## 2. Technology Stack

- **Frontend**: HTML5, CSS3, Vanilla JavaScript (zero framework bloat).
- **Backend**: Python 3.11+, FastAPI, Uvicorn.
- **PDF & Document Extraction**: PyMuPDF (`fitz`), Pillow.
- **OCR Engine**: Tesseract OCR (`pytesseract`).
- **Mathematical Engine**: Pure deterministic Python math & calendar simulation.
- **Containerization**: Docker (multi-platform `python:3.11-slim` with system Tesseract).

---

## 3. Local Development (Windows / macOS / Linux)

### Prerequisites
- Python 3.11+
- (Optional for scanned image OCR) Tesseract OCR installed on your system. If Tesseract is not installed locally, digital PDFs and manual entry continue to work seamlessly.

### Setup Instructions

1. **Clone or navigate to the repository**:
   ```bash
   cd attendance-planner
   ```

2. **Create and activate a virtual environment**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**:
   ```powershell
   pip install -r backend/requirements.txt
   ```

4. **Verify configuration**:
   Copy `.env.example` to `.env` if custom host/port settings are desired:
   ```powershell
   cp backend/.env.example backend/.env
   ```
   *(Notice: No AI API keys or secrets are required!)*

5. **Run the development server**:
   ```powershell
   python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
   ```

6. Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your web browser.

---

## 4. Running with Docker

Attendly includes a production-grade Dockerfile that automatically bundles `tesseract-ocr` and English training data:

### Build the Docker Image
```bash
docker build -t attendly:latest .
```

### Run the Container
```bash
docker run -d --name attendly -p 8000:8000 attendly:latest
```

Open [http://localhost:8000](http://localhost:8000) to use the application.

### Container Health Check
The Docker container exposes a self-monitoring health check:
```bash
docker inspect --format='{{json .State.Health.Status}}' attendly
```

---

## 5. Running Automated Tests

Attendly comes with an extensive pytest test suite covering attendance mathematics, date-wise scheduling, deterministic document parsing, and FastAPI endpoints:

```bash
python -m pytest backend/tests/ -v
```

All 16 test suites pass with sub-second execution.

---

## 6. Cloud Deployment Instructions

Attendly can be deployed directly to any container-compatible hosting platform (such as Render, Fly.io, Railway, Google Cloud Run, AWS App Runner, or a VPS).

### Deploying to Render / Railway / Cloud Run
1. Connect this repository to your container host.
2. Ensure the host builds using the provided `Dockerfile`.
3. Set the container port to `8000`.
4. The deployment will automatically include Tesseract OCR, PyMuPDF, and all dependencies with no cloud AI API keys required.
5. Benchmark recommendation: Allocate at least 512MB RAM (1GB recommended for intensive multi-page OCR concurrency).

---

## 7. Performance & Reliability Notes

- **Manual Calculations**: Instantaneous (< 5ms).
- **Digital PDF Parsing**: Typically 50–200ms using PyMuPDF direct text stream extraction.
- **Scanned Image OCR**: 1.5–4.5s per page on modern dual-core CPU with Tesseract OCR.
- **Bounded Concurrency**: Document parsing and OCR are executed in a dedicated `ThreadPoolExecutor` with bounded worker capacity (3 concurrent jobs) to guarantee that CPU-intensive operations never block the async FastAPI event loop.
