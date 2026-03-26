"""
Route Service - greedy nearest-neighbor truck route optimization.
Member 5 (Research & Analytics Lead) owns this file.
"""

import math
from datetime import date
from typing import List
from sqlalchemy.orm import Session
from app.models.route import Route
from app.utils.geo_utils import haversine_km


def _nearest_neighbor_route(waypoints: List[dict]) -> List[dict]:
    """
    Greedy nearest-neighbor TSP approximation.
    Sorts waypoints by priority (urgency) first, then by distance.
    """
    if len(waypoints) <= 1:
        return waypoints

    # Sort by urgency priority descending to start at most urgent
    wp = sorted(waypoints, key=lambda x: x.get("priority", 0), reverse=True)
    start = wp[0]
    ordered = [start]
    remaining = wp[1:]

    current = start
    while remaining:
        nearest = min(
            remaining,
            key=lambda p: haversine_km(current["lat"], current["lon"], p["lat"], p["lon"])
        )
        ordered.append(nearest)
        remaining.remove(nearest)
        current = nearest

    return ordered


def _total_distance(ordered: List[dict]) -> float:
    total = 0.0
    for i in range(1, len(ordered)):
        total += haversine_km(
            ordered[i-1]["lat"], ordered[i-1]["lon"],
            ordered[i]["lat"], ordered[i]["lon"]
        )
    return round(total, 2)


def generate_route(
    db: Session,
    city: str,
    route_date: date,
    hotspots: List[dict],
    ward: str | None = None,
) -> Route:
    """
    Generate an optimized collection route from predicted hotspot locations.
    """
    if not hotspots:
        # Fallback: generate demo route for city
        hotspots = _demo_hotspots(city)

    waypoints_raw = [
        {
            "lat": h["latitude"] or 12.97,
            "lon": h["longitude"] or 77.59,
            "priority": {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(
                h.get("urgency_level", "low"), 1
            ),
            "ward": h.get("ward_number", ""),
        }
        for h in hotspots
        if h.get("latitude") and h.get("longitude")
    ]

    ordered = _nearest_neighbor_route(waypoints_raw)
    dist_km = _total_distance(ordered)
    est_min = int(dist_km / 0.5) + len(ordered) * 5  # ~30 km/h + 5min per stop

    waypoints_out = [
        {"lat": w["lat"], "lon": w["lon"],
         "priority": w["priority"], "address": w.get("ward", "")}
        for w in ordered
    ]

    route = Route(
        city=city,
        ward_number=ward,
        route_date=route_date,
        waypoints=waypoints_out,
        total_distance_km=dist_km,
        estimated_duration_min=est_min,
        status="planned",
    )
    db.add(route)
    db.commit()
    db.refresh(route)
    return route


def _demo_hotspots(city: str) -> List[dict]:
    lat, lon = {"Bangalore": (12.97, 77.59), "Delhi": (28.61, 77.20)}.get(city, (12.97, 77.59))
    return [
        {"latitude": lat + 0.01, "longitude": lon + 0.01, "urgency_level": "critical", "ward_number": "W-001"},
        {"latitude": lat - 0.01, "longitude": lon + 0.02, "urgency_level": "high", "ward_number": "W-002"},
        {"latitude": lat + 0.02, "longitude": lon - 0.01, "urgency_level": "medium", "ward_number": "W-003"},
    ]
