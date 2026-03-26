"""
YOLO Inference Module
Member 1 (AI/Vision Lead) owns this file.

Loads a YOLOv11-seg model and runs instance segmentation on a given image.
Returns structured DetectionResult objects with class info and mask area.
"""

import os
import time
from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np

# Lazy import to avoid crashing when ultralytics isn't installed
try:
    from ultralytics import YOLO
    import cv2
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False

# 20 Indian waste classes (matches dataset.yaml)
CLASS_NAMES = [
    "plastic_pet_bottle",
    "plastic_bag",
    "plastic_wrapper",
    "glass_bottle",
    "glass_broken",
    "paper_newspaper",
    "paper_cardboard",
    "metal_can",
    "metal_scrap",
    "organic_food_waste",
    "organic_leaves",
    "e_waste_phone",
    "e_waste_battery",
    "textile_cloth",
    "rubber_tire",
    "construction_debris",
    "medical_waste_mask",
    "thermocol",
    "tetra_pak",
    "mixed_waste",
]

# Colours for mask overlays (BGR)
CLASS_COLORS = [
    (255, 87, 34), (33, 150, 243), (76, 175, 80), (156, 39, 176),
    (255, 193, 7), (0, 188, 212), (233, 30, 99), (121, 85, 72),
    (96, 125, 139), (139, 195, 74), (0, 150, 136), (63, 81, 181),
    (255, 152, 0), (103, 58, 183), (244, 67, 54), (158, 158, 158),
    (205, 220, 57), (0, 188, 212), (255, 87, 34), (189, 189, 189),
]


@dataclass
class DetectionResult:
    class_id: int
    class_name: str
    confidence: float
    mask_area: float = 0.0
    bbox: List[float] = field(default_factory=list)


_model_cache: Optional[object] = None


def load_model(model_path: str):
    global _model_cache
    if _model_cache is None:
        if not ULTRALYTICS_AVAILABLE:
            raise RuntimeError("ultralytics not installed. Run: pip install ultralytics")
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"YOLO weights not found at {model_path}. "
                "Train the model first with ml-models/yolo/train.py"
            )
        _model_cache = YOLO(model_path)
    return _model_cache


def run_inference(
    image_path: str,
    model_path: str,
    conf: float = 0.25,
    iou: float = 0.45,
    annotated_output_path: Optional[str] = None,
) -> tuple[List[DetectionResult], int]:
    """
    Run YOLO instance segmentation on image_path.
    Returns (list of DetectionResult, inference_ms).
    Saves annotated image if annotated_output_path is provided.
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

    detections: List[DetectionResult] = []

    if not results or len(results) == 0:
        return detections, inference_ms

    result = results[0]

    # Draw annotated image if requested
    if annotated_output_path and ULTRALYTICS_AVAILABLE:
        import cv2
        img = cv2.imread(image_path)
        if img is not None and result.masks is not None:
            overlay = img.copy()
            for i, mask in enumerate(result.masks.data.cpu().numpy()):
                class_id = int(result.boxes.cls[i].item())
                color = CLASS_COLORS[class_id % len(CLASS_COLORS)]
                h, w = img.shape[:2]
                mask_resized = cv2.resize(mask, (w, h))
                binary_mask = (mask_resized > 0.5).astype(np.uint8)
                overlay[binary_mask == 1] = color
            cv2.addWeighted(overlay, 0.4, img, 0.6, 0, img)
            # Draw bounding boxes + labels
            if result.boxes is not None:
                for box in result.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    cls_id = int(box.cls[0].item())
                    conf_val = float(box.conf[0].item())
                    label = f"{CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else str(cls_id)} {conf_val:.2f}"
                    color = CLASS_COLORS[cls_id % len(CLASS_COLORS)]
                    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(img, label, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            cv2.imwrite(annotated_output_path, img)

    # Parse detections
    if result.boxes is not None:
        masks_data = result.masks.data.cpu().numpy() if result.masks is not None else None
        for i, box in enumerate(result.boxes):
            cls_id = int(box.cls[0].item())
            conf_val = float(box.conf[0].item())
            name = CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else f"class_{cls_id}"
            mask_area = 0.0
            if masks_data is not None and i < len(masks_data):
                mask_area = float(np.sum(masks_data[i] > 0.5))
            detections.append(DetectionResult(
                class_id=cls_id,
                class_name=name,
                confidence=conf_val,
                mask_area=mask_area,
                bbox=box.xyxy[0].tolist(),
            ))

    return detections, inference_ms


def mock_inference(image_path: str) -> tuple[List[DetectionResult], int]:
    """
    Returns mock detections for development without a trained model.
    Used when YOLO weights are not available.
    """
    import random
    mock_classes = [
        (0, "plastic_pet_bottle", 0.92),
        (6, "paper_cardboard", 0.78),
        (19, "mixed_waste", 0.65),
    ]
    detections = [
        DetectionResult(class_id=c, class_name=n, confidence=conf, mask_area=5000.0)
        for c, n, conf in random.choices(mock_classes, k=random.randint(1, 3))
    ]
    return detections, 120  # 120ms mock latency
