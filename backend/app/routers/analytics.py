from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.dependencies import get_db, require_admin
from app.services.analytics_service import (
    get_scan_trends,
    get_category_distribution,
    get_predicted_hotspots,
)

router = APIRouter()


@router.get("/trends")
def scan_trends(
    city: str = Query(...),
    days: int = Query(30, ge=1, le=365),
    category: str = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return get_scan_trends(db, city, days, category)


@router.get("/categories")
def category_stats(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return get_category_distribution(db, days)


@router.get("/hotspots")
def predicted_hotspots(
    city: str = Query(...),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return get_predicted_hotspots(db, city)


@router.get("/volume")
def waste_volume(
    city: str = Query(...),
    days: int = Query(7),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    from app.models.scan import Scan
    from datetime import datetime, timedelta
    from sqlalchemy import func

    start = datetime.utcnow() - timedelta(days=days)
    total = db.query(func.count(Scan.id)).filter(
        Scan.scan_status == "done",
        Scan.created_at >= start,
    ).scalar()
    return {"city": city, "days": days, "estimated_scan_count": total or 0}
