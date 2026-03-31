"""
vision/serve.py  --  EcoStream AI YOLO Microservice
====================================================
Standalone FastAPI server wrapping YOLOv11-seg inference.
The main backend calls this service via YOLO_SERVICE_URL=http://vision:8001

Endpoints
---------
POST /detect    multipart image  ->  JSON detections + polygon coords
GET  /health    liveness probe

Owned by: M1a Prajwal Patil (AI/Vision Lead)
"""

import io
import os
import tempfile
import time
from pathlib import Path

import numpy as np
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Config (override via env vars in docker-compose)
# ---------------------------------------------------------------------------
WEIGHTS_PATH   = Path(os.getenv("YOLO_WEIGHTS", "/app/weights/best.pt"))
CONF_THRESHOLD = float(os.getenv("YOLO_CONF", "0.25"))
IOU_THRESHOLD  = float(os.getenv("YOLO_IOU",  "0.45"))

# 20 Indian waste classes -- must match dataset.yaml order (LOCKED)
CLASS_NAMES = [
    "plastic_pet_bottle", "plastic_bag",        "plastic_wrapper",
    "glass_bottle",       "glass_broken",       "paper_newspaper",
    "paper_cardboard",    "metal_can",           "metal_scrap",
    "organic_food_waste", "organic_leaves",      "e_waste_phone",
    "e_waste_battery",    "textile_cloth",       "rubber_tire",
    "construction_debris","medical_waste_mask",  "thermocol",
    "tetra_pak",          "mixed_waste",
]

# BGR overlay colours (one per class, used when saving annotated images)
CLASS_COLORS = [
    (255,  87,  34), ( 33, 150, 243), ( 76, 175,  80), (156,  39, 176),
    (255, 193,   7), (  0, 188, 212), (233,  30,  99), (121,  85,  72),
    ( 96, 125, 139), (139, 195,  74), (  0, 150, 136), ( 63,  81, 181),
    (255, 152,   0), (103,  58, 183), (244,  67,  54), (158, 158, 158),
    (205, 220,  57), (  0, 188, 212), (255,  87,  34), (189, 189, 189),
]

# ---------------------------------------------------------------------------
# Optional imports (service works in mock mode if ultralytics is absent)
# ---------------------------------------------------------------------------
try:
    from ultralytics import YOLO
    import cv2
    _ULTRALYTICS = True
except ImportError:
    _ULTRALYTICS = False

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="EcoStream Vision Service", version="1.0.0")

_model = None
_model_ready = False


def _load_model():
    global _model, _model_ready
    if not _ULTRALYTICS:
        print("[vision] ultralytics not installed -- running in mock mode")
        return
    if not WEIGHTS_PATH.exists() or WEIGHTS_PATH.stat().st_size < 100_000:
        print(f"[vision] weights not found at {WEIGHTS_PATH} -- running in mock mode")
        return
    print(f"[vision] Loading YOLOv11-seg from {WEIGHTS_PATH} ...")
    _model = YOLO(str(WEIGHTS_PATH))
    _model_ready = True
    print("[vision] Model loaded OK")


@app.on_event("startup")
def startup():
    _load_model()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": _model_ready,
        "weights": str(WEIGHTS_PATH),
        "num_classes": len(CLASS_NAMES),
    }


# ---------------------------------------------------------------------------
# Predict
# ---------------------------------------------------------------------------
@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    """
    Accept a JPEG/PNG/WebP image and return YOLO instance-segmentation results.

    Response schema:
        {
          "detections": [
            {
              "class_id":   0,
              "class_name": "plastic_pet_bottle",
              "confidence": 0.91,
              "mask_area":  4230.0,
              "bbox":       [x1, y1, x2, y2],
              "polygon":    [[x1,y1], [x2,y2], ...]   -- normalised 0-1 coords
            }
          ],
          "inference_ms": 123,
          "model": "yolo11s-seg | mock"
        }
    """
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=415, detail="Only JPEG/PNG/WebP images accepted")

    raw = await file.read()

    if not _model_ready:
        return JSONResponse(_mock_response())

    return JSONResponse(_run_inference(raw))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _run_inference(raw: bytes) -> dict:
    """Write raw bytes to a temp file, run YOLO predict, parse results."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name

    try:
        t0 = time.perf_counter()
        results = _model.predict(
            source=tmp_path,
            conf=CONF_THRESHOLD,
            iou=IOU_THRESHOLD,
            task="segment",
            verbose=False,
            save=False,
        )
        ms = int((time.perf_counter() - t0) * 1000)
    finally:
        os.unlink(tmp_path)

    if not results:
        return {"detections": [], "inference_ms": ms, "model": "yolo11s-seg"}

    result = results[0]
    detections = []

    if result.boxes is not None:
        masks_data = result.masks.data.cpu().numpy() if result.masks is not None else None
        for i, box in enumerate(result.boxes):
            cls_id = int(box.cls[0].item())
            conf_v = round(float(box.conf[0].item()), 4)
            name   = CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else f"class_{cls_id}"
            area    = 0.0
            polygon = []
            if masks_data is not None and i < len(masks_data):
                mask_bin = (masks_data[i] > 0.5).astype(np.uint8)
                area = float(np.sum(mask_bin))
                # Extract largest contour and normalise coords to [0,1]
                contours, _ = cv2.findContours(
                    mask_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                if contours:
                    h, w = mask_bin.shape
                    pts = contours[0].squeeze()
                    if pts.ndim == 2:
                        polygon = [
                            [round(p[0] / w, 4), round(p[1] / h, 4)]
                            for p in pts.tolist()
                        ]
            detections.append({
                "class_id":   cls_id,
                "class_name": name,
                "confidence": conf_v,
                "mask_area":  round(area, 1),
                "bbox":       [round(v, 1) for v in box.xyxy[0].tolist()],
                "polygon":    polygon,
            })

    return {"detections": detections, "inference_ms": ms, "model": "yolo11s-seg"}


def _mock_response() -> dict:
    """Deterministic mock -- used when weights are absent (dev/CI)."""
    import random
    candidates = [
        (0,  "plastic_pet_bottle",  0.91),
        (1,  "plastic_bag",         0.82),
        (6,  "paper_cardboard",     0.78),
        (7,  "metal_can",           0.74),
        (19, "mixed_waste",         0.65),
        (12, "e_waste_battery",     0.88),
        (3,  "glass_bottle",        0.76),
    ]
    chosen = random.sample(candidates, k=random.randint(1, 3))
    return {
        "detections": [
            {
                "class_id":   cid,
                "class_name": name,
                "confidence": conf,
                "mask_area":  round(random.uniform(3000, 12000), 1),
                "bbox":       [50.0, 50.0, 250.0, 300.0],
                "polygon":    [],
            }
            for cid, name, conf in chosen
        ],
        "inference_ms": 95,
        "model": "mock",
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
