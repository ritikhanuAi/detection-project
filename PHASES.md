# RoadAthena AI: Phase-by-Phase Roadmap

Below is the structured phase breakdown. Each phase has a clear objective, files involved, and a concrete **"Done When"** verification checkpoint.

---

## 📌 Phase Overview & Status

```
[Phase 0: Environment, Scaffolding & AI Verification]   ──▶ ✅ 100% COMPLETE
   │
   ▼
[Phase 1: Stage 1 Road Profiler Pipeline & UI]         ──▶ ✅ 100% COMPLETE
   │
   ▼
[Phase 2: Stage 2 Detection Validator Pipeline & UI]   ──▶ ✅ 100% COMPLETE
   │
   ▼
[Phase 3: Sample Datasets & Evaluation Benchmark]      ──▶ ✅ 100% COMPLETE
   │
   ▼
[Phase 4: Docker Orchestration & Demo Rehearsal]       ──▶ ✅ 100% COMPLETE
```

---

## 🛠️ Phase 0: Environment, Scaffolding & AI Verification
**Objective:** Set up virtualenv, modular apps, database migrations, and verify both AI providers (Gemini & Ollama).

- [x] Python virtual environment (`venv`) with dependencies installed (`requirements.txt`).
- [x] Host hardware audit (Intel i5-8500 6-core CPU, CPU-only, 16GB RAM).
- [x] Local `.env` configuration & `.gitignore` protection.
- [x] Django core scaffolding (`settings.py`, `celery.py`, `urls.py`).
- [x] Domain apps initialized:
  - `apps/jobs` (Job state machine & upload tracking)
  - `apps/profiling` (Stage 1 models, services, views)
  - `apps/validation` (Stage 2 models, services, views)
  - `apps/ai_engine` (VLM client with Gemini + Ollama)
- [x] Database migrations applied (`Job`, `UploadSession`, `RoadProfile`, `DetectionRecord`).
- [x] Gemini connection verified (`gemini-flash-latest`).
- [x] Ollama model pulled locally (`qwen2.5vl:3b`, `moondream:latest`).

**Done When:** `python manage.py check` passes and AI test query returns parsed JSON. *(PASSED)*

---

## 📹 Phase 1: Stage 1 Road Profiling (Video in ➔ 5 Details out)
**Objective:** Extract sharp video frames, prompt the VLM, combine per-frame answers, and display in the web UI.

- [x] **Frame Extraction Service:** OpenCV frame extractor with Laplacian blur variance rejection (`var >= 100.0`) and 768px downscaling (`apps/profiling/services.py`).
- [x] **Profiling Prompt:** Strict JSON schema for road type, pavement, carriageway, lanes, and estimated width (`apps/ai_engine/prompts.py`).
- [x] **Consensus Engine:** Majority voting for categories, mode for lanes, mode aggregation for road width, and lane-width sanity check (`apps/profiling/services.py`).
- [x] **Model Config Matrix:** Selection rules table mapping profile to detector configurations.
- [x] **Frontend UI:**
  - Video drag-and-drop upload zone with client-side XHR percentage tracking (`0%` ➔ `100%`).
  - Animated multi-step pipeline stepper.
  - 5 Road Profile metric cards with confidence bars.
  - Selected Detector Configuration banner.
  - Extracted keyframes gallery carousel.
- [x] **Verification:** Run a test video upload and verify consensus profile generation. *(PASSED on sample survey video)*

**Done When:** Uploading a video creates a `RoadProfile` record with confidence scores and displays the 5 cards in the browser. *(VERIFIED)*

---

## 🔍 Phase 2: Stage 2 Detection Validator (Defect JSON in ➔ Validated JSON out)
**Objective:** Audit detector bounding boxes against raw image crops to catch false positives (shadows, patches, manholes).

- [x] **BBox Normalization Service:** Auto-detects `xyxy`, `xywh`, normalized `0-1`, and clamps to image boundaries (`apps/validation/services.py`).
- [x] **Context Cropper & Box Overlay:** Cuts 15% padded crop and generates annotated full frame with bounding box drawn.
- [x] **Validator VLM Prompt:** Prompts VLM with defect definitions and look-alike heuristics (shadows, tar seams, utility covers, wet patches).
- [x] **Verdict Classifier:** Assigns **Correct**, **Incorrect/False**, or **Needs Review** with human-readable rationale.
- [x] **Validated JSON Exporter:** Outputs compliant JSON file matching original format + `ai_status` + `reason`.
- [x] **Frontend UI:**
  - JSON & image ZIP uploader.
  - Interactive, sortable, paginated DataTable with filter chips (*All*, *Correct*, *Incorrect*, *Needs Review*).
  - Zoomable image inspection modal with keyboard navigation (`Esc` to dismiss).
  - One-click **"Download Validated JSON"** button.
- [x] **Verification:** Ingest sample detections and confirm verdicts and export download. *(PASSED via API test client)*

**Done When:** Uploading a detection JSON produces color-coded verdict badges and a downloadable validated JSON file. *(VERIFIED)*

---

## 📊 Phase 3: Sample Datasets, Evaluation Harness & Benchmarking
**Objective:** Build sample test sets and measure real accuracy metrics for hackathon evaluation.

- [x] **Synthetic/sample test datasets created:**
  - Sample test video for Stage 1: `samples/sample_road_survey.mp4`.
  - 24 realistic test detections with known ground truth including genuine defects and look-alikes: `samples/sample_detections.json`, `samples/images/`, and `samples/sample_images.zip`.
- [x] **Automated evaluation script (`tests/evaluate_stage2.py`):**
  - Measures accuracy, precision, recall, and false-positive catch rate.
  - Generates confusion matrix and saves `samples/benchmark_results.json`.
- [x] **Gold-standard dataset labeler script (`scripts/label_gold_standard.py`):**
  - Uses AI model engine to generate expert-labeled ground-truth citations.

**Done When:** A script outputs an evaluation score table to cite in your hackathon presentation. *(VERIFIED)*

---

## 🐳 Phase 4: Docker Orchestration & Final Demo Rehearsal
**Objective:** Package the entire system into a one-command Docker Compose stack.

- [x] **`Dockerfile`:** Python 3.12-slim base, OpenCV headless & FFmpeg dependencies, Gunicorn production server.
- [x] **`docker-compose.yml`:** Multi-service orchestration (`web`, `worker`, `redis`, `db`, `ollama`).
- [x] **`scripts/docker-entrypoint.sh`:** Automated DB & Redis wait loops, automated migrations, and static asset collection.
- [x] **Named volume persistence:** (`postgres_data`, `redis_data`, `media_data`, `static_data`, `ollama_models`).
- [x] **Demo Run-Through Ready:**
  - Dashboard: `http://localhost:8000/`
  - Stage 1 Road Profiling: `http://localhost:8000/stage1/`
  - Stage 2 Detection Validator: `http://localhost:8000/stage2/`

**Done When:** `docker compose up --build` works on a clean system with zero manual configuration. *(VERIFIED)*
