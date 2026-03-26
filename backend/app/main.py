import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers import auth, scans, rag, analytics, heatmap, routes
from app.database import engine
from app.models import User, WasteCategory, Location, Scan, Route  # noqa: ensure models registered

app = FastAPI(
    title="EcoStream AI API",
    description="Software-Only Smart Waste Management Platform for Indian Cities",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://frontend:80",
        "http://frontend",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploaded/annotated images
upload_dir = os.environ.get("UPLOAD_DIR", "data/uploads")
os.makedirs(upload_dir, exist_ok=True)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(scans.router, prefix="/api/scans", tags=["Scans"])
app.include_router(rag.router, prefix="/api/rag", tags=["RAG / LLM"])
app.include_router(heatmap.router, prefix="/api/heatmap", tags=["Heatmap"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(routes.router, prefix="/api/routes", tags=["Routes"])


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": "EcoStream AI Backend"}


@app.on_event("startup")
async def seed_waste_categories():
    """Seed the 20 waste categories on first startup."""
    from sqlalchemy.orm import Session
    from app.database import SessionLocal

    CATEGORIES = [
        ("plastic_pet_bottle", "Plastic PET Bottle", "dry", 1.0, "#2196F3"),
        ("plastic_bag", "Plastic Bag", "dry", 1.2, "#03A9F4"),
        ("plastic_wrapper", "Plastic Wrapper", "dry", 1.0, "#00BCD4"),
        ("glass_bottle", "Glass Bottle", "dry", 0.8, "#9C27B0"),
        ("glass_broken", "Broken Glass", "dry", 1.5, "#673AB7"),
        ("paper_newspaper", "Newspaper", "dry", 0.6, "#795548"),
        ("paper_cardboard", "Cardboard", "dry", 0.7, "#FF9800"),
        ("metal_can", "Metal Can", "dry", 0.9, "#607D8B"),
        ("metal_scrap", "Metal Scrap", "dry", 1.0, "#546E7A"),
        ("organic_food_waste", "Food Waste", "wet", 1.3, "#4CAF50"),
        ("organic_leaves", "Leaves / Garden Waste", "wet", 0.5, "#8BC34A"),
        ("e_waste_phone", "E-Waste: Phone", "e-waste", 3.0, "#F44336"),
        ("e_waste_battery", "E-Waste: Battery", "hazardous", 4.0, "#D32F2F"),
        ("textile_cloth", "Textile / Cloth", "dry", 0.7, "#FF5722"),
        ("rubber_tire", "Rubber Tire", "dry", 1.4, "#212121"),
        ("construction_debris", "Construction Debris", "dry", 1.6, "#9E9E9E"),
        ("medical_waste_mask", "Medical Waste / Mask", "hazardous", 5.0, "#B71C1C"),
        ("thermocol", "Thermocol / Styrofoam", "dry", 1.1, "#E3F2FD"),
        ("tetra_pak", "Tetra Pak / Carton", "dry", 0.9, "#FFF9C4"),
        ("mixed_waste", "Mixed Waste", "mixed", 2.0, "#757575"),
    ]

    db: Session = SessionLocal()
    try:
        existing = db.query(WasteCategory).count()
        if existing == 0:
            for slug, name, group, weight, color in CATEGORIES:
                db.add(WasteCategory(
                    slug=slug, name=name,
                    category_group=group,
                    urgency_weight=weight,
                    color_hex=color,
                ))
            db.commit()
    finally:
        db.close()
