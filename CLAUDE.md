# CLAUDE.md — EcoStream AI

## PROJECT OVERVIEW

**EcoStream AI** is a **software-only** smart waste management web platform (no mobile apps, no hardware bins, no React Native).  
It solves the real Indian urban waste problem: **clustered/mixed waste** through three tightly coupled engines:

1. **Vision Engine** – YOLOv11-seg (instance segmentation only)
2. **RAG/LLM Engine** – LangChain + ChromaDB (never hallucinates)
3. **Analytics Engine** – KDE heatmap + predictive routing (WUI formula locked)

**Two UIs**:

- **Citizen Portal** (upload + chat)
- **Government Dashboard** (heatmap + optimized routes)

**Uniqueness (what makes this IEEE-publishable)**: First software-only system that uses instance segmentation + RAG to handle real-world Indian clustered waste and delivers measurable route optimization without any IoT sensors. All metrics in the paper **must** come from the running system.

**Core Constraint**: No feature outside the three engines until all three are production-ready and tested.

## TEAM MAP (Paired Ownership – Redundancy Model)

| Member | Name | Role | Owns |
|--------|------|------|------|
| M1a | Prajwal Patil | AI/Vision Lead (YOLO + RAG) | `ml-models/yolo/`, `ml-models/rag/`, `backend/app/services/rag_service.py`, `data/knowledge_base/` |
| M1b | Mahantesh | AI/Vision Lead (GAN) | `ml-models/gan/` |
| M3  | Prakash | Backend Architect | `backend/app/` (models, routers, scan_service, alembic, Docker) |
| M4  | TBD | Frontend Developer | `frontend/src/` |
| M5  | TBD | Research & Analytics | `ml-models/analytics/`, `backend/app/services/{heatmap,analytics,route}_service.py`, IEEE paper |

### Redundancy Pairs
- M1a backs up M1b (both understand the full Vision pipeline end-to-end)
- M3 backs up M1a on scan_service.py integration
- M5 owns all paper metrics — must have access to all three engine outputs

### GAN Reproducibility Note
`data/gan_seeds/` and `ml-models/gan/weights/*.pt` are gitignored (large binaries).
To regenerate on a new machine:
```bash
python ml-models/gan/download_seeds.py   # ~5 min
python ml-models/gan/train_gan.py        # ~25 min CPU
python ml-models/gan/generate.py         # ~1 min
```

