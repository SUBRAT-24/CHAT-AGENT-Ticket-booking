"""Ticket and booking management API router."""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from app.services.ticket_service import TicketService
from app.services.payment_service import PaymentService
from app.core.security import get_current_user

router = APIRouter(prefix="/api/tickets", tags=["Tickets"])


@router.get("/availability")
async def check_availability(
    date: str, ticket_type: str = "gate_entry", exhibition_id: Optional[str] = None
):
    """Check ticket availability for a specific date."""
    result = await TicketService.check_availability(date, ticket_type, exhibition_id)
    return result


@router.get("/exhibitions")
async def list_exhibitions(active_only: bool = True):
    """List all exhibitions."""
    exhibitions = await TicketService.get_exhibitions(active_only)
    return {"exhibitions": exhibitions}


@router.get("/exhibitions/{exhibition_id}")
async def get_exhibition(exhibition_id: str):
    """Get a specific exhibition."""
    exhibition = await TicketService.get_exhibition(exhibition_id)
    if not exhibition:
        raise HTTPException(status_code=404, detail="Exhibition not found")
    return exhibition


@router.get("/booking/{booking_id}")
async def get_booking(booking_id: str):
    """Get booking details by ID."""
    booking = await TicketService.get_booking(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.post("/booking/{booking_id}/cancel")
async def cancel_booking(booking_id: str):
    """Cancel a booking."""
    result = await TicketService.cancel_booking(booking_id)
    if not result:
        raise HTTPException(
            status_code=400,
            detail="Booking not found or already used",
        )
    return {"message": "Booking cancelled", "booking": result}


@router.get("/my-bookings")
async def my_bookings(current_user: dict = Depends(get_current_user)):
    """Get all bookings for the authenticated user."""
    bookings = await TicketService.get_user_bookings(current_user["user_id"])
    return {"bookings": bookings}


@router.get("/pricing")
async def get_pricing():
    """Get the current pricing information."""
    from app.models.schemas import DEFAULT_PRICING
    return {
        "gate_entry": {
            "adult": DEFAULT_PRICING.gate_entry_adult,
            "child": DEFAULT_PRICING.gate_entry_child,
            "student": DEFAULT_PRICING.gate_entry_student,
            "senior": DEFAULT_PRICING.gate_entry_senior,
            "foreign_tourist": DEFAULT_PRICING.gate_entry_foreign,
        },
        "guided_tour_addon": DEFAULT_PRICING.guided_tour_addon,
        "combo_discount_percent": DEFAULT_PRICING.combo_discount_percent,
        "currency": "INR",
    }
