import os
import hashlib
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.scan import Scan
from app.models.user import User
from app.schemas.scan import ScanUploadResponse, ScanResult, ScanListItem
from app.services.scan_service import process_scan
from app.utils.image_utils import save_upload
from app.config import settings

router = APIRouter()

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/upload", response_model=ScanUploadResponse, status_code=202)
async def upload_scan(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    latitude: float = Form(None),
    longitude: float = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Only JPEG/PNG/WebP images accepted")

    raw = await file.read()
    if len(raw) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large (max {settings.max_upload_size_mb}MB)")

    image_path, image_hash = save_upload(raw, settings.upload_dir)

    scan = Scan(
        user_id=current_user.id,
        image_path=image_path,
        image_hash=image_hash,
        scan_status="pending",
        latitude=latitude,
        longitude=longitude,
        urgency_score=0.0,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    background_tasks.add_task(process_scan, scan.id, db)

    return ScanUploadResponse(
        scan_id=scan.id,
        status="pending",
        message="Scan queued for processing. Poll GET /api/scans/{scan_id} for results.",
    )


@router.get("/", response_model=List[ScanListItem])
def list_scans(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scans = (
        db.query(Scan)
        .filter(Scan.user_id == current_user.id)
        .order_by(Scan.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return scans


@router.get("/{scan_id}", response_model=ScanResult)
def get_scan(
    scan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if scan.user_id != current_user.id and current_user.role not in ("admin", "government"):
        raise HTTPException(status_code=403, detail="Access denied")
    return scan


@router.get("/{scan_id}/image")
def get_scan_image(
    scan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if not scan.image_path or not os.path.exists(scan.image_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(scan.image_path, media_type="image/jpeg")
