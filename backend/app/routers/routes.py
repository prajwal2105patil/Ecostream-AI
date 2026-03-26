from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.dependencies import get_db, require_admin
from app.schemas.analytics import RouteGenerateRequest, RouteResponse
from app.services.analytics_service import get_predicted_hotspots
from app.services.route_service import generate_route
from app.models.route import Route

router = APIRouter()


@router.post("/generate", response_model=RouteResponse, status_code=201)
def generate_route_endpoint(
    body: RouteGenerateRequest,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    hotspots = get_predicted_hotspots(db, body.city)
    route = generate_route(db, body.city, body.route_date, hotspots, body.ward_number)
    return route


@router.get("/{route_id}", response_model=RouteResponse)
def get_route(
    route_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route


@router.get("/")
def list_routes(
    city: str,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    routes = (
        db.query(Route)
        .filter(Route.city == city)
        .order_by(Route.generated_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return routes
