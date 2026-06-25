"""Stripe payment gateway integration service."""

import stripe
import uuid
from datetime import datetime
from typing import Optional
from app.core.config import settings
from app.database.connection import get_collection

stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentService:
    """Handles payment processing via Stripe."""

    @staticmethod
    async def create_payment_session(
        booking_id: str,
        amount: float,
        currency: str = "inr",
        customer_email: str = "",
        description: str = "Museum Ticket Booking",
        success_url: str = "http://localhost:8000/payment/success",
        cancel_url: str = "http://localhost:8000/payment/cancel",
    ) -> dict:
        """Create a Stripe Checkout Session and store the transaction."""
        try:
            # Create Stripe Checkout Session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": currency,
                            "product_data": {
                                "name": f"Museum Ticket - {booking_id}",
                                "description": description,
                            },
                            "unit_amount": int(amount * 100),  # Stripe uses cents/paise
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=success_url + f"?booking_id={booking_id}&session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=cancel_url + f"?booking_id={booking_id}",
                customer_email=customer_email,
                metadata={"booking_id": booking_id},
            )

            # Store transaction
            transaction_id = str(uuid.uuid4())
            transaction = {
                "transaction_id": transaction_id,
                "booking_id": booking_id,
                "stripe_session_id": checkout_session.id,
                "amount": amount,
                "currency": currency.upper(),
                "status": "pending",
                "payment_url": checkout_session.url,
                "created_at": datetime.utcnow(),
            }

            transactions_col = get_collection("transactions")
            await transactions_col.insert_one(transaction)

            return {
                "success": True,
                "payment_url": checkout_session.url,
                "session_id": checkout_session.id,
                "transaction_id": transaction_id,
            }

        except Exception as e:
            # Fallback to demo mode for development/testing or invalid Stripe keys
            print(f"⚠️ Stripe unavailable ({type(e).__name__}), using demo payment mode")
            transaction_id = str(uuid.uuid4())
            demo_payment_url = f"http://localhost:8000/static/payment-demo.html?booking_id={booking_id}&amount={amount}"

            transaction = {
                "transaction_id": transaction_id,
                "booking_id": booking_id,
                "stripe_session_id": f"demo_{transaction_id}",
                "amount": amount,
                "currency": currency.upper(),
                "status": "pending",
                "payment_url": demo_payment_url,
                "created_at": datetime.utcnow(),
            }

            transactions_col = get_collection("transactions")
            await transactions_col.insert_one(transaction)

            return {
                "success": True,
                "payment_url": demo_payment_url,
                "session_id": f"demo_{transaction_id}",
                "transaction_id": transaction_id,
                "demo_mode": True,
            }

    @staticmethod
    async def handle_payment_success(booking_id: str, session_id: str = None) -> dict:
        """Handle a successful payment - confirm the booking."""
        from app.services.ticket_service import TicketService

        transactions_col = get_collection("transactions")

        # Find the transaction
        query = {"booking_id": booking_id}
        if session_id:
            query["stripe_session_id"] = session_id

        transaction = await transactions_col.find_one(query)
        if not transaction:
            return {"success": False, "error": "Transaction not found"}

        # Update transaction status
        await transactions_col.update_one(
            {"transaction_id": transaction["transaction_id"]},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": datetime.utcnow(),
                }
            },
        )

        # Confirm the booking and generate QR code
        confirmed_ticket = await TicketService.confirm_booking(
            booking_id, transaction["transaction_id"]
        )

        if confirmed_ticket:
            return {
                "success": True,
                "booking_id": booking_id,
                "transaction_id": transaction["transaction_id"],
                "qr_code": confirmed_ticket.get("qr_code_data"),
                "message": "Payment successful! Your ticket has been confirmed.",
            }
        else:
            return {"success": False, "error": "Booking not found"}

    @staticmethod
    async def handle_webhook(payload: bytes, sig_header: str) -> dict:
        """Handle Stripe webhook events."""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError):
            return {"success": False, "error": "Invalid webhook signature"}

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            booking_id = session.get("metadata", {}).get("booking_id")
            if booking_id:
                return await PaymentService.handle_payment_success(
                    booking_id, session.get("id")
                )

        return {"success": True, "message": f"Event {event['type']} received"}

    @staticmethod
    async def get_transaction(booking_id: str) -> Optional[dict]:
        """Get transaction details for a booking."""
        transactions_col = get_collection("transactions")
        transaction = await transactions_col.find_one(
            {"booking_id": booking_id}, {"_id": 0}
        )
        if transaction:
            from datetime import datetime
            for key, value in list(transaction.items()):
                if isinstance(value, datetime):
                    transaction[key] = value.isoformat()
        return transaction
