from pydantic import BaseModel
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime


class DetectionResult(BaseModel):
    class_id: int
    class_name: str
    confidence: float
    mask_area: Optional[float] = None


class ScanUploadResponse(BaseModel):
    scan_id: UUID
    status: str
    message: str


class ScanResult(BaseModel):
    id: UUID
    scan_status: str
    detected_classes: Optional[List[DetectionResult]] = None
    dominant_category: Optional[int] = None
    rag_response: Optional[str] = None
    rag_sources: Optional[List[Any]] = None
    urgency_score: float
    yolo_inference_ms: Optional[int] = None
    image_path: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ScanListItem(BaseModel):
    id: UUID
    scan_status: str
    dominant_category: Optional[int]
    urgency_score: float
    created_at: datetime

    class Config:
        from_attributes = True
