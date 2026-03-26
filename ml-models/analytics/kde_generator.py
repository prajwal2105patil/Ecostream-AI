"""
Gaussian KDE Heatmap Generator
Member 5 (Research & Analytics Lead) owns this file.

Generates a spatiotemporal probability heatmap from scan data.
Uses weighted Gaussian Kernel Density Estimation with time decay.
"""

import math
import numpy as np
from typing import List


# Half-life ~35 hours for waste urgency decay
DECAY_LAMBDA = 0.02


def generate_heatmap_points(
    scan_points: List[dict],
    grid_resolution: int = 80,
    intensity_threshold: float = 0.05,
) -> List[List[float]]:
    """
    Args:
        scan_points: list of {lat, lon, urgency_score, age_hours}
        grid_resolution: grid size (N x N)
        intensity_threshold: minimum intensity to include in output

    Returns:
        List of [lat, lon, intensity] for Leaflet.heat plugin
    """
    if not scan_points:
        return []

    try:
        from scipy.stats import gaussian_kde
    except ImportError:
        return _simple_heatmap(scan_points)

    lats = np.array([p["lat"] for p in scan_points])
    lons = np.array([p["lon"] for p in scan_points])

    # Time-decayed urgency weights
    weights = np.array([
        p.get("urgency_score", 1.0) * math.exp(-DECAY_LAMBDA * p.get("age_hours", 0))
        for p in scan_points
    ])
    weights = np.clip(weights, 1e-6, None)

    if len(scan_points) < 2:
        return [[float(lats[0]), float(lons[0]), 1.0]]

    kde = gaussian_kde(
        np.vstack([lons, lats]),
        weights=weights,
        bw_method="scott",
    )

    lat_min = lats.min() - 0.005
    lat_max = lats.max() + 0.005
    lon_min = lons.min() - 0.005
    lon_max = lons.max() + 0.005

    lon_grid = np.linspace(lon_min, lon_max, grid_resolution)
    lat_grid = np.linspace(lat_min, lat_max, grid_resolution)
    lon_mesh, lat_mesh = np.meshgrid(lon_grid, lat_grid)

    density = kde(np.vstack([lon_mesh.ravel(), lat_mesh.ravel()]))
    density = density.reshape(grid_resolution, grid_resolution)

    # Normalize to [0, 1]
    d_min, d_max = density.min(), density.max()
    if d_max > d_min:
        density = (density - d_min) / (d_max - d_min)
    else:
        density = np.ones_like(density)

    points = []
    for i in range(len(lat_grid)):
        for j in range(len(lon_grid)):
            val = float(density[i, j])
            if val >= intensity_threshold:
                points.append([float(lat_grid[i]), float(lon_grid[j]), val])

    return points


def _simple_heatmap(scan_points: List[dict]) -> List[List[float]]:
    """Fallback when scipy not available: raw point intensities."""
    result = []
    for p in scan_points:
        w = p.get("urgency_score", 1.0) * math.exp(-DECAY_LAMBDA * p.get("age_hours", 0))
        result.append([p["lat"], p["lon"], min(w / 5.0, 1.0)])
    return result


def compute_ward_summary(
    scan_points: List[dict],
    ward_groups: dict,
) -> List[dict]:
    """
    Aggregate scan stats per ward for the summary panel.
    ward_groups: {ward_number: [scan_point, ...]}
    Returns list of {ward, scan_count, avg_urgency, dominant_category}
    """
    summary = []
    for ward, points in ward_groups.items():
        if not points:
            continue
        avg_urgency = sum(p.get("urgency_score", 0) for p in points) / len(points)
        categories = [p.get("category") for p in points if p.get("category")]
        dominant = max(set(categories), key=categories.count) if categories else "unknown"
        summary.append({
            "ward": ward,
            "scan_count": len(points),
            "avg_urgency": round(avg_urgency, 3),
            "dominant_category": dominant,
        })
    return sorted(summary, key=lambda x: x["avg_urgency"], reverse=True)
