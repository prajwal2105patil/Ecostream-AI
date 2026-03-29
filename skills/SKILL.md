---
name: ecostream_autoresearcher
description: Autonomous machine learning experimentation and architecture search for YOLO and RAG models under strict time-bounded constraints.
---

# EcoStream AI Autoresearcher

## Goal

Autonomously discover, implement, and benchmark architectural changes, optimizers, loss functions, retrieval strategies, and prompt templates for the **EcoStream AI** machine learning models. The agent's primary directive is to maximize the target metric within a rigid, unchangeable **5-minute training budget** per experiment.

## Pipelines

### YOLO Vision Engine

| File | Path | Role |
|------|------|------|
| `prepare.py` | `ml-models/yolo/prepare.py` | Downloads TACO dataset, converts COCO→YOLO format, writes `dataset.yaml`. **READ ONLY.** |
| `train.py` | `ml-models/yolo/train.py` | Self-contained ultralytics training with all config inlined. **THE ONLY FILE YOU EDIT.** |

**Target metric**: `map50_seg` (mAP@50 for segmentation masks)

**Experiment knobs** (top of train.py):
- `MODEL_VARIANT`: yolo11n-seg / yolo11s-seg / yolo11m-seg
- `IMGSZ`: 320 / 416 / 512 / 640
- `BATCH_SIZE`: 2 / 4 / 8
- `OPTIMIZER`: AdamW / SGD / Adam / RMSProp
- `LR0`, `LRF`, `MOMENTUM`, `WEIGHT_DECAY`, `WARMUP_EPOCHS`
- `PATIENCE`: early stopping epochs
- `FREEZE_LAYERS`: 0 (none) to 10+ (freeze backbone for transfer learning)
- Augmentation: `HSV_H/S/V`, `DEGREES`, `TRANSLATE`, `SCALE`, `FLIPLR`, `MOSAIC`, `MIXUP`, `COPY_PASTE`

**Run**: `python ml-models/yolo/train.py`

---

### RAG Retrieval Pipeline

| File | Path | Role |
|------|------|------|
| `prepare.py` | `ml-models/rag/prepare.py` | Builds ChromaDB vectorstore + verifies test queries. **READ ONLY.** |
| `train.py` | `ml-models/rag/train.py` | Evaluation harness: rebuilds experiment vectorstore, runs 18 test queries, measures quality. **THE ONLY FILE YOU EDIT.** |

**Target metric**: `composite_score` (weighted blend of retrieval + answer quality)

**Experiment knobs** (top of train.py):
- `CHUNK_SIZE`: 200 / 300 / 500 / 800 / 1000
- `CHUNK_OVERLAP`: 0 / 25 / 50 / 100 / 150
- `EMBEDDING_MODEL`: all-MiniLM-L6-v2 / all-mpnet-base-v2 / paraphrase-MiniLM-L6-v2
- `RETRIEVAL_K`: 2 / 3 / 4 / 6 / 8
- `SIMILARITY_THRESHOLD`: 0.10 – 0.30
- `USE_MMR` / `MMR_LAMBDA`: diversity vs relevance tradeoff
- `PROMPT_TEMPLATE`: full prompt text (rewrite freely)

**Run**: `python ml-models/rag/train.py`

---

## Allowed Tools

- **Read File**: Allowed to read `prepare.py` for dataset context. **Strictly forbidden from modifying it.**
- **Edit File**: Allowed **ONLY** to edit `train.py`. All iterations must be self-contained within this single file.
- **Run Terminal Command**: Allowed to execute `python ml-models/yolo/train.py` or `python ml-models/rag/train.py`.

## Agent Protocol

1. **Read** `prepare.py` to understand the data pipeline and available dataset.
2. **Read** the current `train.py` to understand the baseline configuration.
3. **Formulate a hypothesis** — one specific change with expected impact.
4. **Edit** `train.py` — modify only the experiment knobs section.
5. **Run** `python train.py` and wait for completion (max 5 minutes).
6. **Parse** the final JSON line from stdout.
7. **Log** the results and compare against the previous best.
8. **Repeat** from step 3 with a new hypothesis informed by results.

## JSON Metrics Contract

The agent parses the **last non-empty line** of stdout as JSON. If parsing fails, the experiment is marked as "crashed."

### YOLO Output Schema

```json
{
  "experiment": "yolo",
  "wall_clock_sec": 298.1,
  "epochs_completed": 12,
  "map50_seg": 0.482,
  "map50_95_seg": 0.231,
  "map50_box": 0.513,
  "precision_seg": 0.61,
  "recall_seg": 0.43,
  "val_loss_seg": 1.82,
  "val_loss_box": 1.24,
  "val_loss_cls": 2.11,
  "model_variant": "yolo11n-seg.pt",
  "imgsz": 416,
  "batch_size": 4,
  "optimizer": "AdamW",
  "lr0": 0.001,
  "freeze_layers": 0
}
```

### RAG Output Schema

```json
{
  "experiment": "rag",
  "wall_clock_sec": 142.3,
  "queries_evaluated": 18,
  "source_hit_rate": 0.85,
  "keyword_precision": 0.72,
  "keyword_recall": 0.68,
  "avg_relevance_score": 0.34,
  "hallucination_guard_accuracy": 1.0,
  "avg_answer_length": 145,
  "composite_score": 0.76,
  "chunk_size": 500,
  "chunk_overlap": 50,
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "retrieval_k": 4,
  "similarity_threshold": 0.20,
  "use_mmr": false
}
```

## Rules

1. **5-minute budget is sacred.** Never modify `WALL_CLOCK_BUDGET_SEC`.
2. **One hypothesis per run.** Change one or two related knobs at a time for clean A/B comparison.
3. **Never touch prepare.py.** Data pipeline is frozen.
4. **Never touch fixed constants.** `PROJECT_ROOT`, `DATASET_YAML`, `NC`, paths are locked.
5. **Log every experiment.** The JSON line is your lab notebook — never discard results.
6. **Fail fast.** If a configuration crashes, revert to the last working state before trying a new hypothesis.
