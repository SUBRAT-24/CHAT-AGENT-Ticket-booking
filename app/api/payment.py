"""Payment webhook and status API router."""

from fastapi import APIRouter, Request, HTTPException
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/api/payment", tags=["Payment"])


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    result = await PaymentService.handle_webhook(payload, sig_header)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/confirm/{booking_id}")
async def confirm_payment(booking_id: str, session_id: str = None):
    """Manually confirm a payment (for demo/testing)."""
    result = await PaymentService.handle_payment_success(booking_id, session_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/status/{booking_id}")
async def payment_status(booking_id: str):
    """Check payment status for a booking."""
    transaction = await PaymentService.get_transaction(booking_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction
