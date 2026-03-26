from sqlalchemy import Column, Integer, String, Float, Text
from app.database import Base


class WasteCategory(Base):
    __tablename__ = "waste_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    category_group = Column(String(50))  # dry, wet, hazardous, e-waste
    urgency_weight = Column(Float, default=1.0)
    color_hex = Column(String(7))
    description = Column(Text)
