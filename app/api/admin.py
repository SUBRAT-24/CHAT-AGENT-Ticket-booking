"""Admin and analytics API router."""

from fastapi import APIRouter, Depends, HTTPException
from app.services.analytics_service import AnalyticsService
from app.core.security import get_admin_user
from app.database.connection import get_collection
from app.models.schemas import ExhibitionCreate, ExhibitionInDB
from datetime import datetime

router = APIRouter(prefix="/api/admin", tags=["Admin & Analytics"])


@router.get("/dashboard")
async def dashboard_summary():
    """Get dashboard summary with key metrics."""
    summary = await AnalyticsService.get_dashboard_summary()
    return summary


@router.get("/analytics/ticket-types")
async def ticket_type_distribution():
    """Get ticket type distribution."""
    return await AnalyticsService.get_ticket_type_distribution()


@router.get("/analytics/demographics")
async def visitor_demographics():
    """Get visitor category demographics."""
    return await AnalyticsService.get_visitor_demographics()


@router.get("/analytics/trends")
async def daily_trends(days: int = 30):
    """Get daily booking trends."""
    return await AnalyticsService.get_daily_trends(days)


@router.get("/analytics/languages")
async def language_distribution():
    """Get chat language distribution."""
    return await AnalyticsService.get_language_distribution()


@router.get("/analytics/hourly")
async def hourly_traffic(date: str = None):
    """Get hourly booking traffic."""
    return await AnalyticsService.get_hourly_traffic(date)


@router.get("/analytics/exhibitions")
async def exhibition_popularity():
    """Get exhibition popularity rankings."""
    return await AnalyticsService.get_exhibition_popularity()


@router.get("/bookings/recent")
async def recent_bookings(limit: int = 20):
    """Get recent bookings."""
    return await AnalyticsService.get_recent_bookings(limit)


@router.post("/exhibitions")
async def create_exhibition(exhibition: ExhibitionCreate):
    """Create a new exhibition."""
    exhibitions_col = get_collection("exhibitions")

    ex_data = ExhibitionInDB(
        name=exhibition.name,
        description=exhibition.description,
        start_date=exhibition.start_date.isoformat(),
        end_date=exhibition.end_date.isoformat(),
        daily_capacity=exhibition.daily_capacity,
        ticket_price=exhibition.ticket_price,
        show_times=exhibition.show_times,
        image_url=exhibition.image_url,
        is_special=exhibition.is_special,
    )

    await exhibitions_col.insert_one(ex_data.dict())
    return {"message": "Exhibition created", "exhibition_id": ex_data.exhibition_id}


@router.put("/exhibitions/{exhibition_id}")
async def update_exhibition(exhibition_id: str, exhibition: ExhibitionCreate):
    """Update an exhibition."""
    exhibitions_col = get_collection("exhibitions")

    result = await exhibitions_col.update_one(
        {"exhibition_id": exhibition_id},
        {
            "$set": {
                "name": exhibition.name,
                "description": exhibition.description,
                "start_date": exhibition.start_date.isoformat(),
                "end_date": exhibition.end_date.isoformat(),
                "daily_capacity": exhibition.daily_capacity,
                "ticket_price": exhibition.ticket_price,
                "show_times": exhibition.show_times,
                "image_url": exhibition.image_url,
                "is_special": exhibition.is_special,
            }
        },
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Exhibition not found")
    return {"message": "Exhibition updated"}


@router.delete("/exhibitions/{exhibition_id}")
async def delete_exhibition(exhibition_id: str):
    """Deactivate an exhibition."""
    exhibitions_col = get_collection("exhibitions")
    result = await exhibitions_col.update_one(
        {"exhibition_id": exhibition_id},
        {"$set": {"is_active": False}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Exhibition not found")
    return {"message": "Exhibition deactivated"}
