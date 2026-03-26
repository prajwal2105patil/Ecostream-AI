from sqlalchemy import Column, Integer, String, Float, Date, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    city = Column(String(100), nullable=False, index=True)
    ward_number = Column(String(20))
    route_date = Column(Date, nullable=False, index=True)
    waypoints = Column(JSONB, nullable=False)  # [{lat, lon, location_id, priority}]
    total_distance_km = Column(Float)
    estimated_duration_min = Column(Integer)
    status = Column(String(20), default="planned")  # planned, active, completed
    vehicle_id = Column(String(50))
    generated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
