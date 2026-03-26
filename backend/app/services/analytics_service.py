"""
Analytics Service - trends, hotspot predictions, category stats.
Member 5 (Research & Analytics Lead) owns this file.
"""

import sys
import os
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func

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
    start = datetime.utcnow() - timedelta(days=days)
    scans = (
        db.query(Scan.created_at, Scan.dominant_category)
        .filter(Scan.scan_status == "done", Scan.created_at >= start)
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
    """Generate predicted hotspot data per ward."""
    try:
        from analytics.hotspot_predictor import predict_hotspots
        from analytics.feature_engineering import build_ward_features

        # Get distinct wards with scan data
        ward_rows = (
            db.query(
                func.coalesce(Scan.latitude, 12.97),
                func.coalesce(Scan.longitude, 77.59),
            )
            .filter(Scan.scan_status == "done", Scan.latitude.isnot(None))
            .distinct()
            .limit(20)
            .all()
        )

        if not ward_rows:
            return _mock_hotspots(city)

        recent_scans = (
            db.query(Scan.created_at, Scan.urgency_score, Scan.dominant_category)
            .filter(
                Scan.scan_status == "done",
                Scan.created_at >= datetime.utcnow() - timedelta(days=7),
            )
            .all()
        )
        recent_list = [
            {"created_at": s.created_at, "urgency_score": s.urgency_score}
            for s in recent_scans
        ]

        features = []
        for i, (lat, lon) in enumerate(ward_rows):
            f = build_ward_features(
                ward_number=f"W-{i+1:03d}",
                city=city,
                lat=lat,
                lon=lon,
                recent_scans=recent_list,
            )
            features.append(f)

        return predict_hotspots(features)
    except Exception:
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
