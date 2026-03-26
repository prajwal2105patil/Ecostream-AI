import uuid
from sqlalchemy import Column, String, Float, Integer, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.database import Base


class Scan(Base):
    __tablename__ = "scans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    image_path = Column(String(500))
    image_hash = Column(String(64), index=True)
    scan_status = Column(String(20), default="pending")  # pending, processing, done, failed
    detected_classes = Column(JSONB)  # [{class_id, class_name, confidence, mask_area}]
    dominant_category = Column(Integer, ForeignKey("waste_categories.id"), nullable=True)
    yolo_inference_ms = Column(Integer)
    rag_response = Column(Text)
    rag_sources = Column(JSONB)
    urgency_score = Column(Float, default=0.0)
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
