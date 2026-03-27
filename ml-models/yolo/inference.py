"""
YOLO Inference Module — EcoStream AI
Member 1 (AI/Vision Lead) owns this file.

Loads YOLOv11-seg and runs instance segmentation on waste images.
Auto-detects trained weights (best.pt); falls back to mock inference during dev.

Usage (from scan_service.py):
    from ml_models.yolo.inference import run_inference, mock_inference, has_real_model
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import numpy as np

try:
    from ultralytics import YOLO
    import cv2
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False

# ── Paths ──────────────────────────────────────────────────────────────────
_THIS_DIR   = Path(__file__).resolve().parent
WEIGHTS_DIR = _THIS_DIR / "weights"
BEST_PT     = WEIGHTS_DIR / "best.pt"

# 20 Indian waste classes (must match dataset.yaml order)
CLASS_NAMES = [
    "plastic_pet_bottle", "plastic_bag",        "plastic_wrapper",
    "glass_bottle",       "glass_broken",       "paper_newspaper",
    "paper_cardboard",    "metal_can",           "metal_scrap",
    "organic_food_waste", "organic_leaves",      "e_waste_phone",
    "e_waste_battery",    "textile_cloth",       "rubber_tire",
    "construction_debris","medical_waste_mask",  "thermocol",
    "tetra_pak",          "mixed_waste",
]

# BGR colours for segmentation mask overlays
CLASS_COLORS = [
    (255,  87,  34), ( 33, 150, 243), ( 76, 175,  80), (156,  39, 176),
    (255, 193,   7), (  0, 188, 212), (233,  30,  99), (121,  85,  72),
    ( 96, 125, 139), (139, 195,  74), (  0, 150, 136), ( 63,  81, 181),
    (255, 152,   0), (103,  58, 183), (244,  67,  54), (158, 158, 158),
    (205, 220,  57), (  0, 188, 212), (255,  87,  34), (189, 189, 189),
]


@dataclass
class DetectionResult:
    class_id:   int
    class_name: str
    confidence: float
    mask_area:  float = 0.0
    bbox:       list  = field(default_factory=list)


_model_cache: Optional[object] = None


def has_real_model() -> bool:
    """True if trained best.pt weights are available."""
    return BEST_PT.exists() and BEST_PT.stat().st_size > 100_000  # >100 KB means real weights


def load_model(model_path: str | None = None) -> object:
    """Load YOLO model, caching after first load. Uses best.pt by default."""
    global _model_cache
    if _model_cache is not None:
        return _model_cache

    if not ULTRALYTICS_AVAILABLE:
        raise RuntimeError("ultralytics not installed. Run: pip install ultralytics")

    path = Path(model_path) if model_path else BEST_PT
    if not path.exists():
        raise FileNotFoundError(
            f"YOLO weights not found at {path}. "
            "Train first: python ml-models/yolo/train.py"
        )

    print(f"[YOLO] Loading model from {path} ...")
    _model_cache = YOLO(str(path))
    return _model_cache


def run_inference(
    image_path: str,
    model_path: str | None = None,
    conf: float = 0.25,
    iou: float = 0.45,
    annotated_output_path: str | None = None,
) -> tuple[list[DetectionResult], int]:
    """
    Run YOLO instance segmentation on an image.

    Args:
        image_path: Path to input image.
        model_path: Path to .pt weights (default: ml-models/yolo/weights/best.pt).
        conf: Confidence threshold.
        iou: NMS IoU threshold.
        annotated_output_path: If given, saves annotated image with coloured masks.

    Returns:
        (list[DetectionResult], inference_ms)
    """
    model = load_model(model_path)

    t0 = time.perf_counter()
    results = model.predict(
        source=image_path,
        conf=conf,
        iou=iou,
        task="segment",
        verbose=False,
        save=False,
    )
    inference_ms = int((time.perf_counter() - t0) * 1000)

    if not results:
        return [], inference_ms

    result = results[0]

    # ── Annotated image with coloured mask overlays ────────────────────────
    if annotated_output_path and ULTRALYTICS_AVAILABLE:
        img = cv2.imread(image_path)
        if img is not None:
            overlay = img.copy()
            if result.masks is not None:
                for i, mask in enumerate(result.masks.data.cpu().numpy()):
                    cls_id = int(result.boxes.cls[i].item())
                    color  = CLASS_COLORS[cls_id % len(CLASS_COLORS)]
                    h, w   = img.shape[:2]
                    mask_r = cv2.resize(mask, (w, h))
                    binary = (mask_r > 0.5).astype(np.uint8)
                    overlay[binary == 1] = color
            cv2.addWeighted(overlay, 0.4, img, 0.6, 0, img)
            if result.boxes is not None:
                for box in result.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    cls_id  = int(box.cls[0].item())
                    conf_v  = float(box.conf[0].item())
                    name    = CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else str(cls_id)
                    color   = CLASS_COLORS[cls_id % len(CLASS_COLORS)]
                    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(img, f"{name} {conf_v:.2f}", (x1, y1 - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)
            cv2.imwrite(annotated_output_path, img)

    # ── Parse detections ───────────────────────────────────────────────────
    detections: list[DetectionResult] = []
    if result.boxes is not None:
        masks_data = result.masks.data.cpu().numpy() if result.masks is not None else None
        for i, box in enumerate(result.boxes):
            cls_id   = int(box.cls[0].item())
            conf_v   = float(box.conf[0].item())
            name     = CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else f"class_{cls_id}"
            mask_area = 0.0
            if masks_data is not None and i < len(masks_data):
                mask_area = float(np.sum(masks_data[i] > 0.5))
            detections.append(DetectionResult(
                class_id=cls_id,
                class_name=name,
                confidence=conf_v,
                mask_area=mask_area,
                bbox=box.xyxy[0].tolist(),
            ))

    return detections, inference_ms


def mock_inference(image_path: str) -> tuple[list[DetectionResult], int]:
    """
    Returns realistic mock detections for development (no trained weights needed).
    Simulates what a real model would return for a mixed-waste image.
    """
    import random
    candidates = [
        (0,  "plastic_pet_bottle",  0.91),
        (1,  "plastic_bag",         0.82),
        (6,  "paper_cardboard",     0.78),
        (7,  "metal_can",           0.74),
        (9,  "organic_food_waste",  0.69),
        (19, "mixed_waste",         0.65),
        (12, "e_waste_battery",     0.88),
        (3,  "glass_bottle",        0.76),
    ]
    chosen = random.sample(candidates, k=random.randint(1, 3))
    detections = [
        DetectionResult(
            class_id=c, class_name=n, confidence=conf,
            mask_area=round(random.uniform(3000, 12000), 1),
            bbox=[50.0, 50.0, 250.0, 300.0],
        )
        for c, n, conf in chosen
    ]
    return detections, 95  # ~95 ms mock latency
