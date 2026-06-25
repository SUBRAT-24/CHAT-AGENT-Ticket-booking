"""Pydantic models for the museum ticketing system."""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime, date
from enum import Enum
import uuid


# ─── Enums ───────────────────────────────────────────────────────────

class TicketType(str, Enum):
    GATE_ENTRY = "gate_entry"
    EXHIBITION = "exhibition"
    SHOW = "show"
    COMBO = "combo"
    GUIDED_TOUR = "guided_tour"


class TicketStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    USED = "used"
    EXPIRED = "expired"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class VisitorCategory(str, Enum):
    ADULT = "adult"
    CHILD = "child"
    STUDENT = "student"
    SENIOR = "senior"
    FOREIGN_TOURIST = "foreign_tourist"


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


# ─── User Models ─────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = Field(min_length=2)
    phone: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserInDB(BaseModel):
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    hashed_password: str
    full_name: str
    phone: Optional[str] = None
    role: UserRole = UserRole.USER
    preferred_language: str = "en"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    phone: Optional[str] = None
    role: str
    preferred_language: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ─── Exhibition Models ───────────────────────────────────────────────

class ExhibitionCreate(BaseModel):
    name: str
    description: str
    start_date: date
    end_date: date
    daily_capacity: int = 500
    ticket_price: float
    show_times: Optional[List[str]] = None
    image_url: Optional[str] = None
    is_special: bool = False


class ExhibitionInDB(BaseModel):
    exhibition_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    start_date: str
    end_date: str
    daily_capacity: int = 500
    ticket_price: float
    show_times: Optional[List[str]] = None
    image_url: Optional[str] = None
    is_special: bool = False
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExhibitionResponse(BaseModel):
    exhibition_id: str
    name: str
    description: str
    start_date: str
    end_date: str
    daily_capacity: int
    ticket_price: float
    show_times: Optional[List[str]] = None
    image_url: Optional[str] = None
    is_special: bool
    is_active: bool


# ─── Ticket / Booking Models ────────────────────────────────────────

class TicketBookingRequest(BaseModel):
    ticket_type: TicketType
    visit_date: str
    num_tickets: int = Field(ge=1, le=20)
    visitor_category: VisitorCategory = VisitorCategory.ADULT
    exhibition_id: Optional[str] = None
    show_time: Optional[str] = None
    visitor_name: str
    visitor_email: EmailStr
    visitor_phone: Optional[str] = None


class TicketInDB(BaseModel):
    booking_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12].upper())
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ticket_type: TicketType
    visit_date: str
    num_tickets: int
    visitor_category: VisitorCategory
    exhibition_id: Optional[str] = None
    show_time: Optional[str] = None
    visitor_name: str
    visitor_email: str
    visitor_phone: Optional[str] = None
    unit_price: float
    total_price: float
    discount_applied: float = 0.0
    status: TicketStatus = TicketStatus.PENDING
    payment_status: PaymentStatus = PaymentStatus.PENDING
    transaction_id: Optional[str] = None
    qr_code_data: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TicketResponse(BaseModel):
    booking_id: str
    ticket_type: str
    visit_date: str
    num_tickets: int
    visitor_category: str
    visitor_name: str
    visitor_email: str
    unit_price: float
    total_price: float
    discount_applied: float
    status: str
    payment_status: str
    qr_code_data: Optional[str] = None
    exhibition_name: Optional[str] = None
    show_time: Optional[str] = None
    created_at: datetime


# ─── Transaction Models ─────────────────────────────────────────────

class TransactionInDB(BaseModel):
    transaction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    booking_id: str
    stripe_session_id: Optional[str] = None
    stripe_payment_intent: Optional[str] = None
    amount: float
    currency: str = "INR"
    status: PaymentStatus = PaymentStatus.PENDING
    payment_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


# ─── Chat Models ─────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[dict] = None


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    language: Optional[str] = "en"


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    action: Optional[str] = None
    data: Optional[dict] = None


class ChatLogInDB(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    messages: List[dict] = []
    language: str = "en"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    booking_context: Optional[dict] = None


# ─── Analytics Models ────────────────────────────────────────────────

class AnalyticsSummary(BaseModel):
    total_bookings: int = 0
    total_revenue: float = 0.0
    tickets_today: int = 0
    revenue_today: float = 0.0
    active_sessions: int = 0
    popular_ticket_type: Optional[str] = None
    popular_exhibition: Optional[str] = None
    visitor_demographics: dict = {}
    daily_trends: List[dict] = []
    language_distribution: dict = {}


# ─── Pricing Models ─────────────────────────────────────────────────

class PricingConfig(BaseModel):
    gate_entry_adult: float = 50.0
    gate_entry_child: float = 20.0
    gate_entry_student: float = 30.0
    gate_entry_senior: float = 25.0
    gate_entry_foreign: float = 200.0
    guided_tour_addon: float = 100.0
    combo_discount_percent: float = 15.0


# Default pricing configuration
DEFAULT_PRICING = PricingConfig()
