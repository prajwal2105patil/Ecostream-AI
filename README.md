# EcoStream AI — Smart Waste Management Platform

> Software-only, AI-driven waste management for Indian cities. No hardware required.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- (Optional) NVIDIA GPU for faster YOLO training

### 1. Clone & Configure
```bash
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD, SECRET_KEY, OPENAI_API_KEY (or use Ollama)
```

### 2. Start All Services
```bash
docker-compose up -d
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| ChromaDB | http://localhost:8001 |

### 3. Run Migrations & Seed
```bash
docker-compose exec backend alembic upgrade head
```
Waste categories are auto-seeded on first startup.

### 4. Build Knowledge Base (RAG)
```bash
docker-compose exec backend python /app/ml-models/rag/build_vectorstore.py
```

### 5. Train YOLO (Optional)
```bash
# Prepare dataset first
python ml-models/yolo/data_prep.py --coco_json data/raw/annotations/instances.json \
    --images_dir data/raw/images

# Train
python ml-models/yolo/train.py

# Copy weights
cp runs/segment/ecostream_waste/weights/best.pt ml-models/yolo/weights/best.pt
```

---

## Development Setup (No Docker)

```bash
# Backend
cd backend
python -m venv venv && source venv/Scripts/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env && alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev   # → http://localhost:5173
```

---

## Architecture

```
User Browser
    ↓
React Frontend (Vite + Tailwind + Recharts + Leaflet)
    ↓  REST + SSE
FastAPI Backend
    ├── /api/auth      — JWT auth
    ├── /api/scans     — Upload + poll pipeline
    ├── /api/rag       — SSE streaming LLM advice
    ├── /api/heatmap   — KDE heatmap data
    ├── /api/analytics — Trends, hotspots, categories
    └── /api/routes    — Truck route optimization
         ↓
    ┌────────────────────────────┐
    │  scan_service (pipeline)   │
    │  1. Save image             │
    │  2. YOLO inference         │
    │  3. Urgency scoring        │
    │  4. RAG lookup (ChromaDB)  │
    │  5. Persist to PostgreSQL  │
    └────────────────────────────┘
         ↓
    PostgreSQL (scans, users, locations, routes)
    ChromaDB  (Indian municipal waste laws)
```

---

## Team

| Member | Role | Focus |
|---|---|---|
| M1 | AI/Vision Lead | YOLOv11-seg, dataset, GANs |
| M2 | LLM/NLP Lead | RAG, ChromaDB, prompt engineering |
| M3 | Backend Architect | FastAPI, PostgreSQL, Docker |
| M4 | Frontend Developer | React, Leaflet, Recharts |
| M5 | Research & Analytics | KDE heatmap, ML hotspot predictor, IEEE paper |

---

## Key Files

- [backend/app/services/scan_service.py](backend/app/services/scan_service.py) — Core pipeline orchestrator
- [ml-models/yolo/inference.py](ml-models/yolo/inference.py) — YOLO waste detection
- [ml-models/rag/rag_chain.py](ml-models/rag/rag_chain.py) — LangChain RAG chain
- [ml-models/analytics/kde_generator.py](ml-models/analytics/kde_generator.py) — Gaussian KDE heatmap
- [frontend/src/pages/ScanChat.jsx](frontend/src/pages/ScanChat.jsx) — Main citizen interface
- [frontend/src/pages/Dashboard.jsx](frontend/src/pages/Dashboard.jsx) — Government dashboard
