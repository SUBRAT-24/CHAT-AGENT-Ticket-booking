"""Ticket booking, pricing, and QR code generation service."""

import qrcode
import io
import base64
import uuid
from datetime import datetime, date
from typing import Optional, List
from app.database.connection import get_collection
from app.models.schemas import (
    TicketType,
    TicketStatus,
    PaymentStatus,
    VisitorCategory,
    TicketInDB,
    TicketBookingRequest,
    TicketResponse,
    DEFAULT_PRICING,
)


class TicketService:
    """Handles all ticket-related operations."""

    @staticmethod
    def calculate_price(
        ticket_type: TicketType,
        visitor_category: VisitorCategory,
        num_tickets: int,
        exhibition_price: float = 0.0,
    ) -> dict:
        """Calculate ticket price based on type and visitor category."""
        pricing = DEFAULT_PRICING
        unit_price = 0.0
        discount = 0.0

        # Base gate entry price by category
        category_prices = {
            VisitorCategory.ADULT: pricing.gate_entry_adult,
            VisitorCategory.CHILD: pricing.gate_entry_child,
            VisitorCategory.STUDENT: pricing.gate_entry_student,
            VisitorCategory.SENIOR: pricing.gate_entry_senior,
            VisitorCategory.FOREIGN_TOURIST: pricing.gate_entry_foreign,
        }

        base_price = category_prices.get(visitor_category, pricing.gate_entry_adult)

        if ticket_type == TicketType.GATE_ENTRY:
            unit_price = base_price
        elif ticket_type == TicketType.EXHIBITION:
            unit_price = base_price + exhibition_price
        elif ticket_type == TicketType.SHOW:
            unit_price = base_price + exhibition_price
        elif ticket_type == TicketType.GUIDED_TOUR:
            unit_price = base_price + pricing.guided_tour_addon
        elif ticket_type == TicketType.COMBO:
            unit_price = base_price + exhibition_price + pricing.guided_tour_addon
            discount = unit_price * (pricing.combo_discount_percent / 100)
            unit_price -= discount

        total_price = unit_price * num_tickets

        return {
            "unit_price": round(unit_price, 2),
            "total_price": round(total_price, 2),
            "discount_applied": round(discount * num_tickets, 2),
        }

    @staticmethod
    def generate_qr_code(booking_id: str, visit_date: str, num_tickets: int) -> str:
        """Generate a QR code for the ticket as a base64 string."""
        qr_data = f"MUSEUM-TICKET|{booking_id}|{visit_date}|{num_tickets}|VALID"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#1a1a2e", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    @staticmethod
    async def check_availability(visit_date: str, ticket_type: str, exhibition_id: Optional[str] = None) -> dict:
        """Check ticket availability for a given date."""
        tickets_col = get_collection("tickets")

        query = {
            "visit_date": visit_date,
            "status": {"$in": ["confirmed", "pending"]},
        }
        if exhibition_id:
            query["exhibition_id"] = exhibition_id

        booked_count = 0
        async for ticket in tickets_col.find(query):
            booked_count += ticket.get("num_tickets", 0)

        # Default daily capacity
        daily_capacity = 1000
        if exhibition_id:
            exhibitions_col = get_collection("exhibitions")
            exhibition = await exhibitions_col.find_one({"exhibition_id": exhibition_id})
            if exhibition:
                daily_capacity = exhibition.get("daily_capacity", 500)

        available = daily_capacity - booked_count

        return {
            "date": visit_date,
            "total_capacity": daily_capacity,
            "booked": booked_count,
            "available": max(0, available),
            "is_available": available > 0,
        }

    @staticmethod
    async def create_booking(
        booking_data: dict,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> dict:
        """Create a new ticket booking."""
        tickets_col = get_collection("tickets")

        # Get exhibition price if needed
        exhibition_price = 0.0
        exhibition_name = None
        if booking_data.get("exhibition_id"):
            exhibitions_col = get_collection("exhibitions")
            exhibition = await exhibitions_col.find_one(
                {"exhibition_id": booking_data["exhibition_id"]}
            )
            if exhibition:
                exhibition_price = exhibition.get("ticket_price", 0.0)
                exhibition_name = exhibition.get("name")

        # Calculate pricing
        pricing = TicketService.calculate_price(
            ticket_type=booking_data.get("ticket_type", TicketType.GATE_ENTRY),
            visitor_category=booking_data.get("visitor_category", VisitorCategory.ADULT),
            num_tickets=booking_data.get("num_tickets", 1),
            exhibition_price=exhibition_price,
        )

        booking_id = str(uuid.uuid4())[:12].upper()

        ticket = {
            "booking_id": booking_id,
            "user_id": user_id,
            "session_id": session_id,
            "ticket_type": booking_data.get("ticket_type", "gate_entry"),
            "visit_date": booking_data.get("visit_date"),
            "num_tickets": booking_data.get("num_tickets", 1),
            "visitor_category": booking_data.get("visitor_category", "adult"),
            "exhibition_id": booking_data.get("exhibition_id"),
            "exhibition_name": exhibition_name,
            "show_time": booking_data.get("show_time"),
            "visitor_name": booking_data.get("visitor_name", "Guest"),
            "visitor_email": booking_data.get("visitor_email", ""),
            "visitor_phone": booking_data.get("visitor_phone"),
            "unit_price": pricing["unit_price"],
            "total_price": pricing["total_price"],
            "discount_applied": pricing["discount_applied"],
            "status": TicketStatus.PENDING.value,
            "payment_status": PaymentStatus.PENDING.value,
            "qr_code_data": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        await tickets_col.insert_one(ticket)
        return ticket

    @staticmethod
    async def confirm_booking(booking_id: str, transaction_id: str) -> dict:
        """Confirm a booking after successful payment."""
        tickets_col = get_collection("tickets")

        # Generate QR code
        ticket = await tickets_col.find_one({"booking_id": booking_id})
        if not ticket:
            return None

        qr_code = TicketService.generate_qr_code(
            booking_id, ticket["visit_date"], ticket["num_tickets"]
        )

        result = await tickets_col.update_one(
            {"booking_id": booking_id},
            {
                "$set": {
                    "status": TicketStatus.CONFIRMED.value,
                    "payment_status": PaymentStatus.COMPLETED.value,
                    "transaction_id": transaction_id,
                    "qr_code_data": qr_code,
                    "updated_at": datetime.utcnow(),
                }
            },
        )

        updated = await tickets_col.find_one({"booking_id": booking_id})
        return updated

    @staticmethod
    async def get_booking(booking_id: str) -> Optional[dict]:
        """Retrieve a booking by its ID."""
        tickets_col = get_collection("tickets")
        return await tickets_col.find_one(
            {"booking_id": booking_id}, {"_id": 0}
        )

    @staticmethod
    async def get_user_bookings(user_id: str) -> List[dict]:
        """Get all bookings for a user."""
        tickets_col = get_collection("tickets")
        bookings = []
        async for ticket in tickets_col.find(
            {"user_id": user_id}, {"_id": 0}
        ).sort("created_at", -1):
            bookings.append(ticket)
        return bookings

    @staticmethod
    async def cancel_booking(booking_id: str) -> Optional[dict]:
        """Cancel a booking."""
        tickets_col = get_collection("tickets")

        result = await tickets_col.update_one(
            {"booking_id": booking_id, "status": {"$ne": "used"}},
            {
                "$set": {
                    "status": TicketStatus.CANCELLED.value,
                    "payment_status": PaymentStatus.REFUNDED.value,
                    "updated_at": datetime.utcnow(),
                }
            },
        )

        if result.modified_count > 0:
            return await tickets_col.find_one(
                {"booking_id": booking_id}, {"_id": 0}
            )
        return None

    @staticmethod
    async def get_exhibitions(active_only: bool = True) -> List[dict]:
        """Get all exhibitions."""
        exhibitions_col = get_collection("exhibitions")
        query = {"is_active": True} if active_only else {}
        exhibitions = []
        async for ex in exhibitions_col.find(query, {"_id": 0}):
            exhibitions.append(ex)
        return exhibitions

    @staticmethod
    async def get_exhibition(exhibition_id: str) -> Optional[dict]:
        """Get a single exhibition by ID."""
        exhibitions_col = get_collection("exhibitions")
        return await exhibitions_col.find_one(
            {"exhibition_id": exhibition_id}, {"_id": 0}
        )
