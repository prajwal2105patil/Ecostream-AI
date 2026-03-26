from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class TrendPoint(BaseModel):
    date: str
    count: int
    category: Optional[str] = None


class CategoryStat(BaseModel):
    category: str
    count: int
    percentage: float
    color_hex: Optional[str] = None


class HotspotPrediction(BaseModel):
    ward_number: str
    city: str
    predicted_count: float
    urgency_level: str  # low, medium, high, critical
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class HeatmapPoint(BaseModel):
    lat: float
    lon: float
    intensity: float


class RouteWaypoint(BaseModel):
    lat: float
    lon: float
    location_id: Optional[int] = None
    priority: int
    address: Optional[str] = None


class RouteResponse(BaseModel):
    id: int
    city: str
    ward_number: Optional[str]
    route_date: date
    waypoints: List[RouteWaypoint]
    total_distance_km: Optional[float]
    estimated_duration_min: Optional[int]
    status: str

    class Config:
        from_attributes = True


class RouteGenerateRequest(BaseModel):
    city: str
    ward_number: Optional[str] = None
    route_date: date
