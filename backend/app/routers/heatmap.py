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
    from app.services.heatmap_service import _city_bbox
    from sqlalchemy import func
    start = datetime.utcnow() - timedelta(days=days)
    bbox = _city_bbox(city)
    filters = [Scan.scan_status == "done", Scan.created_at >= start]
    if bbox:
        filters += [
            Scan.latitude  >= bbox["lat_min"], Scan.latitude  <= bbox["lat_max"],
            Scan.longitude >= bbox["lon_min"], Scan.longitude <= bbox["lon_max"],
        ]
    base = db.query(Scan).filter(*filters)
    total = base.with_entities(func.count(Scan.id)).scalar()
    avg_urgency = base.with_entities(func.avg(Scan.urgency_score)).scalar()
    return {
        "city": city,
        "days": days,
        "total_scans": total or 0,
        "avg_urgency": round(avg_urgency or 0, 3),
    }
