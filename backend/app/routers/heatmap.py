from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.dependencies import get_db, require_admin
from app.services.heatmap_service import generate_kde_response

router = APIRouter()


@router.get("/data")
def get_heatmap_data(
    city: str = Query(...),
    ward: str = Query(None),
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    """Returns [{lat, lon, intensity}] list for Leaflet.heat plugin."""
    points = generate_kde_response(db, city, ward, days)
    return {"points": points, "count": len(points)}


@router.get("/summary")
def heatmap_summary(
    city: str = Query(...),
    days: int = Query(7),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    from app.models.scan import Scan
    from sqlalchemy import func
    start = datetime.utcnow() - timedelta(days=days)
    total = db.query(func.count(Scan.id)).filter(
        Scan.scan_status == "done", Scan.created_at >= start
    ).scalar()
    avg_urgency = db.query(func.avg(Scan.urgency_score)).filter(
        Scan.scan_status == "done", Scan.created_at >= start
    ).scalar()
    return {
        "city": city,
        "days": days,
        "total_scans": total or 0,
        "avg_urgency": round(avg_urgency or 0, 3),
    }
