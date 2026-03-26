"""
Scan Service - core pipeline orchestrator.
Member 3 (Backend Architect) owns this file; coordinates with Member 1 and 2.

Pipeline:
  image save → YOLO inference → urgency scoring → RAG lookup → DB persist
"""

import os
import sys
import time
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import settings
from app.models.scan import Scan
from app.models.waste_category import WasteCategory
from app.services.rag_service import get_disposal_advice
from app.utils.image_utils import save_upload, annotated_path

# Add ml-models to path — ML_MODELS_PATH env var takes priority (set in docker-compose)
sys.path.insert(
    0,
    os.environ.get(
        "ML_MODELS_PATH",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../ml-models")),
    ),
)

# Urgency weights matching dataset.yaml
_DEFAULT_URGENCY = {
    "plastic_pet_bottle": 1.0, "plastic_bag": 1.2, "plastic_wrapper": 1.0,
    "glass_bottle": 0.8, "glass_broken": 1.5, "paper_newspaper": 0.6,
    "paper_cardboard": 0.7, "metal_can": 0.9, "metal_scrap": 1.0,
    "organic_food_waste": 1.3, "organic_leaves": 0.5, "e_waste_phone": 3.0,
    "e_waste_battery": 4.0, "textile_cloth": 0.7, "rubber_tire": 1.4,
    "construction_debris": 1.6, "medical_waste_mask": 5.0, "thermocol": 1.1,
    "tetra_pak": 0.9, "mixed_waste": 2.0,
}


def _compute_urgency(detections: list) -> float:
    if not detections:
        return 0.0
    total = sum(
        _DEFAULT_URGENCY.get(d.class_name, 1.0) * d.confidence
        for d in detections
    )
    return min(total / len(detections), 10.0)  # normalize


def _find_dominant_category(detections: list, db: Session) -> int | None:
    if not detections:
        return None
    top = max(detections, key=lambda d: d.confidence)
    cat = db.query(WasteCategory).filter(WasteCategory.slug == top.class_name).first()
    return cat.id if cat else None


async def process_scan(scan_id: UUID, db: Session):
    """
    Background task: run YOLO + RAG pipeline and update scan record.
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        return

    scan.scan_status = "processing"
    db.commit()

    try:
        # Step 1: Run YOLO inference
        try:
            from yolo.inference import run_inference
            ann_path = annotated_path(scan.image_path)
            detections, yolo_ms = run_inference(
                image_path=scan.image_path,
                model_path=settings.yolo_model_path,
                conf=settings.yolo_conf_threshold,
                iou=settings.yolo_iou_threshold,
                annotated_output_path=ann_path,
            )
        except (FileNotFoundError, RuntimeError):
            # Model not trained yet - use mock
            from yolo.inference import mock_inference
            detections, yolo_ms = mock_inference(scan.image_path)
            ann_path = scan.image_path

        # Step 2: Compute urgency
        urgency = _compute_urgency(detections)

        # Step 3: Get RAG disposal advice
        class_names = list({d.class_name for d in detections})
        city = "Unknown"
        if scan.user_id:
            from app.models.user import User
            user = db.query(User).filter(User.id == scan.user_id).first()
            if user and user.city:
                city = user.city

        advice, sources = get_disposal_advice(class_names, city)

        # Step 4: Persist results
        scan.detected_classes = [
            {
                "class_id": d.class_id,
                "class_name": d.class_name,
                "confidence": round(d.confidence, 4),
                "mask_area": d.mask_area,
            }
            for d in detections
        ]
        scan.dominant_category = _find_dominant_category(detections, db)
        scan.yolo_inference_ms = yolo_ms
        scan.rag_response = advice
        scan.rag_sources = sources
        scan.urgency_score = round(urgency, 4)
        scan.scan_status = "done"

        # Update image path to annotated version if it exists
        if os.path.exists(ann_path):
            scan.image_path = ann_path

    except Exception as e:
        scan.scan_status = "failed"
        scan.rag_response = f"Processing failed: {str(e)[:200]}"

    db.commit()
