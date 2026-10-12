# Project Architectural Rules & Guidelines

## 1. System & Hardware Awareness (AI Model Policy)
- **Host Specs**: Intel(R) Core(TM) i5-8500 CPU (6 cores @ 3.00GHz), 16GB Total RAM (~3.5–4.5GB free), **CPU-only (No NVIDIA GPU)**.
- **Model Standard**:
  - Primary Model: **`qwen2.5vl:3b`** (Quantized via Ollama CPU inference, RAM footprint ~2.2GB).
  - Alternative / Ultra-light Model: **`moondream:latest`** (1.7B params, ~1.2GB RAM footprint).
- **CPU Performance Safeguards**:
  - Resize all frames and crops to max 768px width before passing to the VLM.
  - Stage 1: Sample 8 representative sharp frames (filtered with Laplacian blur variance).
  - Celery concurrency capped at 2 worker processes to prevent CPU core exhaustion.

---

## 2. Backend Architecture (Django & DRF)
Every backend feature MUST be split into dedicated Django apps under `apps/`:
- `apps/jobs`: Job tracking, async task state machine, file upload session & progress tracking.
- `apps/profiling`: Stage 1 AI Road Profiling (video frames, voting, model config matrix).
- `apps/validation`: Stage 2 AI Detection Validator (bbox normalization, cropping, verdict engine).
- `apps/ai_engine`: Low-level Ollama/VLM client, prompt templates, retry & JSON parsers.

### Layered Separation of Concerns per App:
1. **`models.py`**:
   - Pure database schema definitions, choices, relationships, and table indexes.
   - No business logic or heavy computations in model methods.
2. **`serializers.py`**:
   - **Validation and serialization ONLY**.
   - Validate input formats, bounding box structures, and file extensions.
   - Do NOT execute business workflows or heavy DB mutations inside serializers.
3. **`services.py`**:
   - **All business logic and mutations live here**.
   - Functions that create/update models, trigger Celery tasks, interact with OpenCV, or call `ai_engine`.
4. **`selectors.py`**:
   - **Pure read/query operations**.
   - QuerySet builders, filtering, aggregations, and data fetching functions.
   - Must never perform database writes.
5. **`views.py`**:
   - HTTP controllers only.
   - Flow: Receive request ➔ Validate with Serializer ➔ Call Service (write) or Selector (read) ➔ Return DRF `Response`.
6. **`urls.py`**:
   - Clean, versioned endpoint definitions mapped to ViewSets/APIViews.

### API Standards:
- **Pagination**: Every list endpoint MUST use standard pagination (e.g. `CustomPageNumberPagination` with `page`, `page_size`, `total_count`, `total_pages`).
- **Searching & Ordering**: Implement `filterset_fields`, `search_fields`, and `ordering_fields` (via `django-filter` / DRF `SearchFilter`, `OrderingFilter`).
- **File Uploads with Percentage Progress**:
  - Implement tracked file uploads with client-side XHR `upload.onprogress` and backend upload sessions (`UploadSession` model or cache-backed progress) allowing live upload percentage feedback before Celery background processing.

---

## 3. Frontend Architecture
- **Design Philosophy (Minimalist & High Utility)**:
  - Clean, distraction-free aesthetic with high-contrast neutral surfaces (dark slate palette, subtle borders, modern Inter typography).
  - Semantic functional accents only (Emerald for Correct, Crimson for False, Amber for Needs Review, Indigo for Primary CTAs).
  - Zero bloated CSS frameworks. Single curated design tokens file (`tokens.css`) using CSS Custom Properties.

- **Strict Modular Separation**:
  - `templates/layouts/`: Base scaffolding with header, breadcrumb navigation, and modal outlets.
  - `templates/components/`: Reusable HTML partials (`_metric_card.html`, `_stepper.html`, `_badge.html`, `_table_controls.html`).
  - `templates/pages/`: Page-specific shells (`index.html`, `stage1.html`, `stage2.html`).
  - `static/css/`:
    - `tokens.css`: Core design system variables (colors, spacing, shadows, radius, typography).
    - `components.css`: Styles for reusable UI widgets.
    - `pages.css`: Layout and page-specific view rules.
  - `static/js/api/`: Decoupled API service modules (`client.js`, `uploadApi.js`, `jobsApi.js`, `profilingApi.js`, `validationApi.js`).
  - `static/js/components/`: Independent, reusable ES6 UI components:
    - `FileUploadZone.js`: Drag-and-drop zone with client-side XHR upload % progress and cancel hooks.
    - `ProgressBar.js`: Dynamic progress indicator for both byte uploads and processing steps.
    - `StatusBadge.js`: Semantic badge renderer for job and verdict states.
    - `DataTable.js`: Searchable, sortable, paginated data grid with filter chips.
    - `ImageZoomModal.js`: Accessible crop/overlay inspector with zoom, pan, and keyboard dismiss (`Escape`).
    - `Toast.js`: Non-intrusive notification drawer for feedback and errors.
  - `static/js/pages/`: Page controller scripts binding UI components to API services.

- **Room for Improvements & Extensibility**:
  - **Decoupled API Contract**: All frontend modules communicate strictly via `static/js/api/`, enabling future migration to React/Vue without backend modifications.
  - **Pluggable Filtering**: Table and selector components accept dynamic filter configurations (e.g. adding future defect categories or confidence thresholds without rewriting UI components).
  - **Design Token Scalability**: All styling is driven by `--theme-*` variables in `tokens.css`, making light/dark toggle or UI reskinning instantaneous.

---

## 4. Environment Variables & Centralized Configuration (.env)
Every critical operational parameter MUST be configurable via `.env` (with a documented `.env.example`):
- **Core / Django**: `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_URL` (defaults to SQLite, PostgreSQL in Docker).
- **Task Queue**: `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_WORKER_CONCURRENCY` (default: 2).
- **AI / VLM Engine**:
  - `AI_PROVIDER` (default: `ollama`, options: `ollama` for official submission, `gemini` for development & evaluation).
  - `GEMINI_API_KEY` (development API key for fast inference & benchmark labeling).
  - `GEMINI_MODEL` (default: `gemini-flash-latest`).
  - `OLLAMA_BASE_URL` (default: `http://localhost:11434` or `http://ollama:11434` in Docker).
  - `VLM_MODEL` (default: `qwen2.5vl:3b`).
  - `VLM_FALLBACK_MODEL` (default: `moondream:latest`).
  - `VLM_TIMEOUT_SECONDS` (default: `45`).
  - `VLM_MAX_IMAGE_WIDTH` (default: `768`).
  - `VLM_TEMPERATURE` (default: `0.1`).
- **Stage 1 Pipeline Parameters**:
  - `STAGE1_SAMPLE_FRAMES` (default: `8`)
  - `STAGE1_LAPLACIAN_BLUR_THRESHOLD` (default: `100.0`)
- **Stage 2 Pipeline Parameters**:
  - `STAGE2_BBOX_PADDING_RATIO` (default: `0.15`)
  - `STAGE2_CONCURRENT_DETECTIONS` (default: `2`)
- **File Upload Limits**: `MAX_UPLOAD_SIZE_MB` (default: `500`).
