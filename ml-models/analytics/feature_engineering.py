"""
Feature Engineering for Hotspot Prediction
Member 5 (Research & Analytics Lead) owns this file.
"""

from datetime import datetime, timedelta
from typing import List, Optional


# Major Indian festivals (approximate fixed dates for simplicity)
# Real implementation should use lunar calendar
INDIAN_FESTIVALS = [
    (1, 14),   # Makar Sankranti
    (3, 25),   # Holi (approximate)
    (4, 14),   # Baisakhi
    (8, 15),   # Independence Day
    (10, 2),   # Gandhi Jayanti
    (10, 24),  # Dussehra (approximate)
    (11, 1),   # Diwali (approximate)
    (12, 25),  # Christmas
]


def days_to_next_festival(dt: datetime) -> int:
    """Return days until next major Indian festival."""
    today = dt.date()
    year = today.year
    min_days = 365
    for month, day in INDIAN_FESTIVALS:
        for y in [year, year + 1]:
            try:
                festival = datetime(y, month, day).date()
                delta = (festival - today).days
                if delta >= 0:
                    min_days = min(min_days, delta)
            except ValueError:
                pass
    return min(min_days, 30)  # cap at 30


def build_ward_features(
    ward_number: str,
    city: str,
    lat: float,
    lon: float,
    recent_scans: List[dict],
    now: Optional[datetime] = None,
) -> dict:
    """
    Build feature dict for a ward from recent scan records.
    recent_scans: list of {created_at: datetime, urgency_score, dominant_category}
    """
    now = now or datetime.utcnow()
    cutoff_24h = now - timedelta(hours=24)
    cutoff_7d = now - timedelta(days=7)

    scans_24h = [s for s in recent_scans if s["created_at"] >= cutoff_24h]
    scans_7d = [s for s in recent_scans if s["created_at"] >= cutoff_7d]

    hazardous_categories = {"e_waste_phone", "e_waste_battery", "medical_waste_mask", "glass_broken"}
    hazardous_count_7d = sum(
        1 for s in scans_7d
        if s.get("dominant_category") in hazardous_categories
    )
    pct_hazardous = hazardous_count_7d / len(scans_7d) if scans_7d else 0.0
    avg_urgency = (
        sum(s.get("urgency_score", 0) for s in scans_7d) / len(scans_7d)
        if scans_7d else 0.0
    )

    return {
        "ward_number": ward_number,
        "city": city,
        "lat": lat,
        "lon": lon,
        "day_of_week": now.weekday(),
        "hour_of_day": now.hour,
        "week_of_year": now.isocalendar()[1],
        "is_weekend": 1 if now.weekday() >= 5 else 0,
        "scan_count_24h": len(scans_24h),
        "scan_count_7d": len(scans_7d),
        "avg_urgency_7d": round(avg_urgency, 4),
        "pct_hazardous_7d": round(pct_hazardous, 4),
        "festival_proximity": days_to_next_festival(now),
    }
