"""
Heatmap Service - aggregates scan data into KDE heatmap points.
Member 5 (Research & Analytics Lead) owns this file.
"""

import sys
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from app.models.scan import Scan

sys.path.insert(
    0,
    os.environ.get(
        "ML_MODELS_PATH",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../ml-models")),
    ),
)


def get_heatmap_points(
    db: Session,
    city: str,
    ward: str | None,
    start_date: datetime,
    end_date: datetime,
) -> list[dict]:
    """
    Query scans with location data and return heatmap input points.
    """
    query = db.query(
        Scan.latitude,
        Scan.longitude,
        Scan.urgency_score,
        Scan.created_at,
    ).filter(
        Scan.latitude.isnot(None),
        Scan.longitude.isnot(None),
        Scan.scan_status == "done",
        Scan.created_at >= start_date,
        Scan.created_at <= end_date,
    )

    scans = query.all()
    now = datetime.utcnow()

    points = []
    for s in scans:
        age_hours = max(0.0, (now - s.created_at.replace(tzinfo=None)).total_seconds() / 3600)
        points.append({
            "lat": s.latitude,
            "lon": s.longitude,
            "urgency_score": s.urgency_score or 1.0,
            "age_hours": age_hours,
        })
    return points


def generate_kde_response(
    db: Session,
    city: str,
    ward: str | None = None,
    days: int = 7,
) -> list:
    """Generate KDE heatmap array for Leaflet.heat plugin."""
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    raw_points = get_heatmap_points(db, city, ward, start, end)

    if not raw_points:
        return []

    try:
        from analytics.kde_generator import generate_heatmap_points
        return generate_heatmap_points(raw_points)
    except Exception:
        # Fallback: raw points with urgency as intensity
        return [[p["lat"], p["lon"], min(p["urgency_score"] / 5.0, 1.0)] for p in raw_points]
