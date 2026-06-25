"""Main FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.core.config import settings
from app.database.connection import connect_to_mongo, close_mongo_connection
from app.api import chat, auth, tickets, payment, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events."""
    # Startup
    await connect_to_mongo()
    print(f"🏛️ {settings.APP_NAME} v{settings.APP_VERSION} started!")
    print(f"📊 Dashboard: http://localhost:8000/admin")
    print(f"💬 Chat Widget: http://localhost:8000")
    print(f"📚 API Docs: http://localhost:8000/docs")
    yield
    # Shutdown
    await close_mongo_connection()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered chatbot ticketing system for museums. Book gate entries, exhibitions, shows, and guided tours through natural conversation.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include API routers
app.include_router(chat.router)
app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(payment.router)
app.include_router(admin.router)


@app.get("/", response_class=HTMLResponse)
async def serve_chat():
    """Serve the main chat widget page."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>Museum Ticketing Bot</h1><p>Static files not found. Run the setup script.</p>")


@app.get("/admin", response_class=HTMLResponse)
async def serve_admin():
    """Serve the admin dashboard."""
    admin_path = os.path.join(static_dir, "admin.html")
    if os.path.exists(admin_path):
        return FileResponse(admin_path)
    return HTMLResponse("<h1>Admin Dashboard</h1><p>Static files not found.</p>")


@app.get("/payment/success")
async def payment_success(booking_id: str = None, session_id: str = None):
    """Payment success redirect page."""
    success_path = os.path.join(static_dir, "payment-success.html")
    if os.path.exists(success_path):
        return FileResponse(success_path)
    return HTMLResponse(f"<h1>Payment Successful!</h1><p>Booking ID: {booking_id}</p>")


@app.get("/payment/cancel")
async def payment_cancel(booking_id: str = None):
    """Payment cancel redirect page."""
    return HTMLResponse(f"<h1>Payment Cancelled</h1><p>Booking {booking_id} was not completed.</p>")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.APP_NAME, "version": settings.APP_VERSION}
