# 🏛️ Museum Chatbot Ticketing System

An AI-powered chatbot-based ticketing system for museums. Book gate entries, exhibitions, shows, and guided tours through natural conversation — in 8+ languages.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![MongoDB](https://img.shields.io/badge/MongoDB-7.0-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

- **🤖 AI-Powered Chatbot** — Natural language ticket booking via conversational AI
- **🌍 Multilingual Support** — English, Hindi, Spanish, French, German, Japanese, Chinese, Arabic
- **🎫 QR Code Tickets** — Instant digital tickets with QR codes
- **💳 Payment Integration** — Stripe-powered secure payments
- **📊 Analytics Dashboard** — Real-time booking insights, demographics, revenue tracking
- **🎨 Exhibition Management** — Admin CRUD for exhibitions and shows
- **⚡ Real-time Chat** — Responsive chatbot with typing indicators and quick actions
- **📱 Responsive Design** — Works on desktop, tablet, and mobile

## 🏗️ Architecture

```
museum-ticketing-bot/
├── app/
│   ├── main.py                    # FastAPI entry point
│   ├── api/                       # REST API routers
│   │   ├── chat.py                # Chat messaging endpoints
│   │   ├── auth.py                # Authentication (JWT)
│   │   ├── tickets.py             # Ticket & booking endpoints
│   │   ├── payment.py             # Stripe payment webhooks
│   │   └── admin.py               # Admin dashboard & analytics
│   ├── core/
│   │   ├── config.py              # Environment config (Pydantic)
│   │   └── security.py            # JWT & bcrypt auth
│   ├── database/
│   │   └── connection.py          # MongoDB async driver (Motor)
│   ├── models/
│   │   └── schemas.py             # Pydantic models & enums
│   ├── services/
│   │   ├── ticket_service.py      # Booking logic, pricing, QR codes
│   │   ├── payment_service.py     # Stripe integration
│   │   └── analytics_service.py   # MongoDB aggregations
│   └── ai/
│       ├── agent.py               # Conversational AI agent (state machine)
│       ├── prompts.py             # LLM system prompts & templates
│       └── nlp_processor.py       # Entity extraction (dates, names, etc.)
├── static/
│   ├── index.html                 # Landing page + chat widget
│   ├── styles.css                 # Design system (dark glassmorphism)
│   ├── app.js                     # Chat widget logic
│   ├── admin.html                 # Admin dashboard
│   ├── admin.css                  # Admin styles
│   ├── admin.js                   # Dashboard logic & charts
│   ├── payment-demo.html          # Demo payment page
│   └── payment-success.html       # Payment success page
├── scripts/
│   └── seed_database.py           # Database seeder
├── .env                           # Environment variables
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Container config
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **MongoDB 6.0+** (running locally or via MongoDB Atlas)
- **pip** (Python package manager)

### 1. Clone & Setup

```bash
cd museum-ticketing-bot
```

### 2. Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate    # Windows
# source venv/bin/activate  # Linux/Mac
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Edit `.env` with your actual keys:

```env
MONGODB_URL=mongodb://localhost:27017
GOOGLE_API_KEY=your_gemini_api_key       # Optional: enables LLM responses
STRIPE_SECRET_KEY=sk_test_your_key       # Optional: enables real payments
```

> **Note:** The system works without API keys! It uses a rule-based fallback for conversations and a demo payment page.

### 5. Seed Database

```bash
python -m scripts.seed_database
```

This creates:
- Admin user: `admin@museum.com` / `admin123`
- 5 sample exhibitions

### 6. Start the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Open in Browser

| Page | URL |
|------|-----|
| 🏛️ Museum + Chat Widget | http://localhost:8000 |
| 📊 Admin Dashboard | http://localhost:8000/admin |
| 📚 API Documentation | http://localhost:8000/docs |
| 📖 ReDoc | http://localhost:8000/redoc |

## 💬 How the Chatbot Works

The chatbot follows a guided booking flow:

```
Greeting → Ticket Type → Date → Quantity → Category
    → (Exhibition Selection) → Name → Email → Phone
    → Booking Summary → Payment → QR Ticket
```

### Conversation Examples

```
User: "I want to book tickets"
Bot: Shows ticket type options (Gate Entry, Exhibition, Show, Tour, Combo)

User: "2 adult tickets for tomorrow"
Bot: Extracts entities: quantity=2, category=adult, date=tomorrow

User: "¿Puedo reservar entradas?" (Spanish)
Bot: Detects language and responds accordingly

User: "combo package"
Bot: Applies 15% combo discount automatically
```

## 💰 Pricing Structure

| Category | Gate Entry | Guided Tour | Exhibition |
|----------|-----------|-------------|------------|
| Adult | ₹50 | ₹150 | ₹50 + exhibition price |
| Child (<12) | ₹20 | ₹120 | ₹20 + exhibition price |
| Student | ₹30 | ₹130 | ₹30 + exhibition price |
| Senior (60+) | ₹25 | ₹125 | ₹25 + exhibition price |
| Foreign Tourist | ₹200 | ₹300 | ₹200 + exhibition price |

**Combo Package** = Gate + Exhibition + Tour at **15% discount**

## 📊 Admin Dashboard

The admin dashboard provides:
- **Real-time metrics**: Total bookings, revenue, active chat sessions
- **Booking management**: View, track, and manage all bookings
- **Exhibition CRUD**: Create, update, deactivate exhibitions
- **Analytics**: Ticket type distribution, visitor demographics, daily trends
- **Language insights**: Chat language distribution
- **Hourly traffic**: Peak booking times

## 🔌 API Endpoints

### Chat
- `POST /api/chat/message` — Send a chat message
- `GET /api/chat/session/{session_id}` — Get session history

### Tickets
- `GET /api/tickets/availability` — Check date availability
- `GET /api/tickets/exhibitions` — List exhibitions
- `GET /api/tickets/booking/{id}` — Get booking details
- `POST /api/tickets/booking/{id}/cancel` — Cancel booking
- `GET /api/tickets/pricing` — Get pricing info

### Payment
- `POST /api/payment/webhook` — Stripe webhook
- `POST /api/payment/confirm/{id}` — Manual confirm (demo)
- `GET /api/payment/status/{id}` — Payment status

### Admin
- `GET /api/admin/dashboard` — Dashboard summary
- `GET /api/admin/analytics/*` — Various analytics
- `GET /api/admin/bookings/recent` — Recent bookings
- `POST /api/admin/exhibitions` — Create exhibition

### Auth
- `POST /api/auth/register` — User registration
- `POST /api/auth/login` — User login

## 🐳 Docker Deployment

```bash
docker build -t museum-ticketing-bot .
docker run -p 8000:8000 --env-file .env museum-ticketing-bot
```

## 🔧 Technology Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python + FastAPI |
| Database | MongoDB (Motor async driver) |
| AI/NLP | Google Gemini + Custom NLP |
| Payment | Stripe |
| Auth | JWT + bcrypt |
| QR Codes | qrcode + Pillow |
| Frontend | HTML/CSS/JS (Vanilla) |
| Design | Dark Glassmorphism Theme |

## 📝 License

MIT License - See [LICENSE](LICENSE) for details.
