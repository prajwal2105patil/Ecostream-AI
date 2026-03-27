"""
Analytics Service - trends, hotspot predictions, category stats.
Member 5 (Research & Analytics Lead) owns this file.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)

from app.models.scan import Scan
from app.models.waste_category import WasteCategory

sys.path.insert(
    0,
    os.environ.get(
        "ML_MODELS_PATH",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../ml-models")),
    ),
)


def get_scan_trends(
    db: Session,
    city: str,
    days: int = 30,
    category_filter: str | None = None,
) -> list[dict]:
    """Return daily scan counts grouped by date."""
    from app.services.heatmap_service import _city_bbox
    start = datetime.utcnow() - timedelta(days=days)
    bbox = _city_bbox(city)
    filters = [Scan.scan_status == "done", Scan.created_at >= start]
    if bbox:
        filters += [
            Scan.latitude  >= bbox["lat_min"], Scan.latitude  <= bbox["lat_max"],
            Scan.longitude >= bbox["lon_min"], Scan.longitude <= bbox["lon_max"],
        ]
    scans = (
        db.query(Scan.created_at, Scan.dominant_category)
        .filter(*filters)
        .all()
    )

    daily: dict[str, int] = defaultdict(int)
    for s in scans:
        day_str = s.created_at.strftime("%Y-%m-%d")
        daily[day_str] += 1

    return [{"date": d, "count": c} for d, c in sorted(daily.items())]


def get_category_distribution(db: Session, days: int = 30) -> list[dict]:
    """Return waste category breakdown."""
    start = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(WasteCategory.name, WasteCategory.color_hex, func.count(Scan.id))
        .join(Scan, Scan.dominant_category == WasteCategory.id, isouter=True)
        .filter(Scan.scan_status == "done", Scan.created_at >= start)
        .group_by(WasteCategory.id)
        .all()
    )

    total = sum(r[2] for r in rows) or 1
    return [
        {
            "category": r[0],
            "count": r[2],
            "percentage": round(r[2] / total * 100, 1),
            "color_hex": r[1],
        }
        for r in rows
        if r[2] > 0
    ]


def get_predicted_hotspots(db: Session, city: str) -> list[dict]:
    """Generate predicted hotspot data per ward using SQL aggregation (O(1) Python loop)."""
    try:
        from analytics.hotspot_predictor import predict_hotspots
        from analytics.feature_engineering import days_to_next_festival
        from app.services.heatmap_service import _city_bbox
        from sqlalchemy import case, cast
        from sqlalchemy.dialects.postgresql import NUMERIC

        bbox = _city_bbox(city)
        now = datetime.utcnow()
        cutoff_7d = now - timedelta(days=7)
        cutoff_24h = now - timedelta(hours=24)

        # City-scoped base filters — only last 7 days
        base_filters = [
            Scan.scan_status == "done",
            Scan.latitude.isnot(None),
            Scan.longitude.isnot(None),
            Scan.created_at >= cutoff_7d,
        ]
        if bbox:
            base_filters += [
                Scan.latitude  >= bbox["lat_min"], Scan.latitude  <= bbox["lat_max"],
                Scan.longitude >= bbox["lon_min"], Scan.longitude <= bbox["lon_max"],
            ]

        # Round to 2 d.p. (~1 km grid) as ward proxy — cast needed because PostgreSQL
        # ROUND(float8, int) requires numeric
        lat_bucket = func.round(cast(Scan.latitude,  NUMERIC(10, 4)), 2)
        lon_bucket = func.round(cast(Scan.longitude, NUMERIC(10, 4)), 2)

        ward_stats = (
            db.query(
                lat_bucket.label("lat"),
                lon_bucket.label("lon"),
                func.count(Scan.id).label("count_7d"),
                func.sum(
                    case((Scan.created_at >= cutoff_24h, 1), else_=0)
                ).label("count_24h"),
                func.avg(Scan.urgency_score).label("avg_urgency"),
            )
            .filter(*base_filters)
            .group_by(lat_bucket, lon_bucket)
            .order_by(func.count(Scan.id).desc())
            .limit(20)
            .all()
        )

        if not ward_stats:
            return _mock_hotspots(city)

        festival_prox = days_to_next_festival(now)
        features = [
            {
                "ward_number": f"W-{i+1:03d}",
                "city": city,
                "lat": float(row.lat),
                "lon": float(row.lon),
                "day_of_week": now.weekday(),
                "hour_of_day": now.hour,
                "week_of_year": now.isocalendar()[1],
                "is_weekend": 1 if now.weekday() >= 5 else 0,
                "scan_count_24h": int(row.count_24h or 0),
                "scan_count_7d": int(row.count_7d or 0),
                "avg_urgency_7d": round(float(row.avg_urgency or 0), 4),
                "pct_hazardous_7d": 0.0,
                "festival_proximity": festival_prox,
            }
            for i, row in enumerate(ward_stats)
        ]

        return predict_hotspots(features)
    except Exception as e:
        logger.warning("get_predicted_hotspots fell back to mock: %s", e)
        return _mock_hotspots(city)


def _mock_hotspots(city: str) -> list[dict]:
    """Return demonstration hotspot data when model not trained."""
    base_coords = {
        "Bangalore": (12.97, 77.59),
        "Delhi": (28.61, 77.20),
        "Mumbai": (19.07, 72.87),
    }
    lat, lon = base_coords.get(city, (12.97, 77.59))
    return [
        {"ward_number": "W-001", "city": city, "predicted_count": 42.5,
         "urgency_level": "critical", "latitude": lat + 0.01, "longitude": lon + 0.01},
        {"ward_number": "W-002", "city": city, "predicted_count": 28.1,
         "urgency_level": "high", "latitude": lat - 0.01, "longitude": lon + 0.02},
        {"ward_number": "W-003", "city": city, "predicted_count": 12.3,
         "urgency_level": "medium", "latitude": lat + 0.02, "longitude": lon - 0.01},
        {"ward_number": "W-004", "city": city, "predicted_count": 4.0,
         "urgency_level": "low", "latitude": lat - 0.02, "longitude": lon - 0.02},
    ]
