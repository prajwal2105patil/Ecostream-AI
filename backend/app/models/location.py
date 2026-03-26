from sqlalchemy import Column, Integer, String, Float, Text, CheckConstraint
from app.database import Base


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    city = Column(String(100), nullable=False, index=True)
    ward_number = Column(String(20), index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address_text = Column(Text)

    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="valid_lat"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="valid_lon"),
    )
