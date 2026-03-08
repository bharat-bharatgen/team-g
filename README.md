# InsureCopilot

AI-powered insurance underwriting platform. Automates document analysis pipelines — MER, Pathology, Face Match, Risk Assessment, Location Check, and Test Verification — using LLMs and computer vision.

## Architecture

```
team-g/
├── backend/        # FastAPI app + async worker
├── frontend/       # React + Vite + TypeScript SPA
└── docker-compose.yml
```

**Services (Docker Compose):**
| Service | Container | Port |
|---------|-----------|------|
| MongoDB 7.0 | `insure-copilot-DB` | 27017 |
| FastAPI backend | `insure-copilot-BE` | 48000 |
| Async worker | `insure-copilot-WORKER` | — |
| Nginx + React frontend | `insure-copilot-FE` | 43000 |

**External dependencies (not in compose):**
- **LiteLLM** at `bharat-litellm:8005` — LLM proxy (serves `qwen3.5-27b`, `gpt-oss-120b`)
- **MinIO** at `minio.bharatgen.dev` — S3-compatible object storage
- Docker network `bharat-network` must exist externally

---

## Prerequisites

- Docker and Docker Compose
- Access to the `bharat-network` external Docker network
- A `.env` file at the project root (see below)

---

## Setup

### 1. Create the external Docker network (once)

```bash
docker network create bharat-network
```

### 2. Configure environment

Copy the example and fill in secrets:

```bash
cp .env.example .env   # or create .env manually
```

Required `.env` keys:

```env
# MongoDB
MONGODB_URL=mongodb://insure-copilot-DB:27017
MONGODB_DB_NAME=insurance_copilot

# MinIO / S3
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
S3_BUCKET_NAME=team-g-bucket
S3_ENDPOINT_URL=https://minio.bharatgen.dev

# LLM proxy
LLM_API_BASE_URL=http://bharat-litellm:8005/v1
LLM_API_KEY=...

# JWT
JWT_SECRET_KEY=...

# Google Maps (for location check)
GOOGLE_MAPS_API_KEY=...

# CORS (comma-separated)
CORS_ORIGINS=http://localhost:43000,http://localhost:5173

# Optional: OpenRouter fallback
USE_OPENROUTER=0
OPENROUTER_API_KEY=...
```

---

## Building

Build all images:

```bash
docker compose build
```

Build a single service:

```bash
docker compose build backend
docker compose build frontend
```

---

## Deployment

### Start all services

```bash
docker compose up -d
```

### Check status

```bash
docker compose ps
docker compose logs -f backend
```

### Endpoints after startup

| Service | URL |
|---------|-----|
| Frontend | http://localhost:43000 |
| Backend API | http://localhost:48000 |
| API docs (Swagger) | http://localhost:48000/docs |
| Health check | http://localhost:48000/health |

### Stop services

```bash
docker compose down
```

To also remove the MongoDB volume:

```bash
docker compose down -v
```

---

## Development (local, without Docker)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run API server
uvicorn app.main:app --reload --port 48000

# Run worker (separate terminal)
python -m app.worker
```

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
npm run build      # production build → dist/
npm run preview    # preview production build
```

Set `VITE_API_BASE_URL=http://localhost:48000/api/v1` in `frontend/.env` for local dev.

---

## AI Models Used

| Model | Purpose |
|-------|---------|
| `qwen3.5-27b` | MER extraction, OCR, test verification, location check |
| `gpt-oss-120b` | Pathology extraction, lab address check, risk analysis |
| InsightFace `buffalo_sc` (MobileFaceNet) | Face matching (v2, default) |
| YuNet + SFace (OpenCV) | Face matching (v1, legacy) |

Switch face-match algorithm via `FACE_MATCH_ALGORITHM=v1` or `v2` in `.env`.

---

## Ignored / Legacy Files

`backend/docker-compose.yml` and `backend/docker-compose.prod.yml` are **superseded** by the top-level `docker-compose.yml` and should not be used. They predate the current setup — they use port 8000 (not 48000), have no worker service, and don't connect to `bharat-network`. They are kept for reference but can be deleted.

---

## Production Notes

- Backend and worker share the same Docker image; worker runs `python -m app.worker`
- Both backend and worker connect to the `bharat-network` to reach LiteLLM
- InsightFace model (`buffalo_sc`) is downloaded on first run and cached in the container
- MongoDB data is persisted in the `mongodb_data` Docker volume
- Frontend is served by Nginx on port 43000; `/api` requests are proxied to the backend
