# 🏛️ How to Run Museum Ticketing Bot

This guide walks you through running the **Museum AI Ticketing Chatbot & Admin Dashboard** locally, with Docker, and deploying to Vercel.

---

## ⚡ Quick Start (Local Development)

### 1. Prerequisites
- **Python 3.10 to 3.13** installed
- **MongoDB** running locally (`mongodb://localhost:27017`) or a free [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) cloud cluster
- **Google Gemini API Key** (optional: rule-based responses work without an API key)

---

### 2. Setup Steps

#### Step A: Open Terminal in the Project Directory
```bash
cd d:\CHAGENT\museum-ticketing-bot
```

#### Step B: Create and Activate Virtual Environment
- **Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **macOS / Linux (Bash):**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

#### Step C: Install Dependencies
```bash
pip install -r requirements.txt
```

#### Step D: Configure Environment Variables
Copy `.env.example` to `.env` if not already present:
```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```
Ensure the key settings are configured in `.env`:
```ini
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=museum_ticketing
GOOGLE_API_KEY=your_gemini_api_key_here
SECRET_KEY=museum-ticketing-bot-secret-key-2024
```

#### Step E: Seed the Database
Populates initial sample exhibitions and the default admin account:
```powershell
# Windows
$env:PYTHONIOENCODING="utf-8"; python scripts/seed_database.py

# macOS / Linux
python scripts/seed_database.py
```
> **Default Admin Credentials:**
> - **Email:** `admin@museum.com`
> - **Password:** `admin123`

---

### 3. Start the Server

#### Windows (PowerShell):
```powershell
$env:PYTHONIOENCODING="utf-8"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

#### macOS / Linux:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The application is now live! 🚀

---

## 🌐 Application URLs

| Interface | URL | Description |
| :--- | :--- | :--- |
| **💬 Chatbot Visitor Interface** | [http://localhost:8000](http://localhost:8000) | Interactive AI chat to book gate tickets, exhibitions, shows, and guided tours |
| **📊 Admin Dashboard** | [http://localhost:8000/admin](http://localhost:8000/admin) | Analytics, real-time ticket sales, visitor category breakdowns, revenue charts |
| **📚 Interactive API Docs (Swagger)** | [http://localhost:8000/docs](http://localhost:8000/docs) | Test all REST endpoints with Swagger UI |
| **📖 Alternative API Docs (ReDoc)** | [http://localhost:8000/redoc](http://localhost:8000/redoc) | Clean API documentation schema |
| **❤️ Health Check** | [http://localhost:8000/health](http://localhost:8000/health) | Verifies server status & version |

---

## 🐳 Running with Docker

If you prefer to run using Docker:

```bash
# 1. Build the Docker image
docker build -t museum-ticketing-bot .

# 2. Run the container
docker run -d -p 8000:8000 --name museum-bot --env-file .env museum-ticketing-bot
```

---

## ☁️ Deploying on Vercel

The project includes built-in Vercel configuration (`vercel.json` and `api/index.py`):

1. **Push your code to GitHub**:
   ```bash
   git add .
   git commit -m "Deploy update"
   git push origin main
   ```
2. **Configure Environment Variables in Vercel**:
   Go to your Vercel Project → **Settings** → **Environment Variables**:
   - `MONGODB_URL`: Your MongoDB Atlas URI (`mongodb+srv://username:password@cluster.mongodb.net/`)
   - `DATABASE_NAME`: `museum_ticketing`
   - `GOOGLE_API_KEY`: Your Google Gemini API Key
   - `SECRET_KEY`: Any secure random string (e.g., `production-secret-key-xyz`)
   - `STRIPE_SECRET_KEY`: (Optional) Stripe test secret key
   - `STRIPE_PUBLISHABLE_KEY`: (Optional) Stripe publishable key

3. **Deploy / Redeploy**:
   - Pushing to GitHub automatically triggers a build.
   - Or click **Redeploy** on the Vercel dashboard.

---

## 🛠️ Common Troubleshooting

### 1. Windows Emoji / Character Map Error (`UnicodeEncodeError`)
If you see `'charmap' codec can't encode character` in Windows PowerShell, set the encoding before running:
```powershell
$env:PYTHONIOENCODING="utf-8"
```

### 2. MongoDB Connection Timeout
- Verify MongoDB is running locally (`Get-Service MongoDB` in PowerShell, or `mongod`).
- If deploying to Vercel, localhost MongoDB will not work; use [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) and whitelist `0.0.0.0/0` (all IPs) in Network Access.

### 3. Vercel 500 MB Bundle Size Limit
- Only keep necessary dependencies in `requirements.txt`. Unused heavy packages like `spacy` and `pandas` were removed to keep the bundle under ~60 MB.
