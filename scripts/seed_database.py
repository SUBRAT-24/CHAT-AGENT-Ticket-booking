"""Database seeder script - populates initial data for demos."""

import asyncio
import uuid
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.core.security import get_password_hash


async def seed_database():
    """Seed the database with initial exhibition and admin data."""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    print("🌱 Seeding database...")

    # ── Create Admin User ────────────────────────────────────────────
    users_col = db["users"]
    admin_exists = await users_col.find_one({"email": "admin@museum.com"})
    if not admin_exists:
        admin_user = {
            "user_id": str(uuid.uuid4()),
            "email": "admin@museum.com",
            "hashed_password": get_password_hash("admin123"),
            "full_name": "Museum Admin",
            "phone": "+91-9876543210",
            "role": "admin",
            "preferred_language": "en",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        await users_col.insert_one(admin_user)
        print("  ✅ Admin user created (admin@museum.com / admin123)")
    else:
        print("  ℹ️ Admin user already exists")

    # ── Create Exhibitions ───────────────────────────────────────────
    exhibitions_col = db["exhibitions"]
    existing_count = await exhibitions_col.count_documents({})

    if existing_count == 0:
        today = datetime.utcnow().date()
        exhibitions = [
            {
                "exhibition_id": str(uuid.uuid4()),
                "name": "Ancient Egyptian Treasures",
                "description": "Explore the mysteries of ancient Egypt through a stunning collection of artifacts, mummies, and hieroglyphic tablets dating back over 4,000 years. Features the famous Golden Mask of Pharaoh Amenhotep III.",
                "start_date": today.isoformat(),
                "end_date": (today + timedelta(days=90)).isoformat(),
                "daily_capacity": 300,
                "ticket_price": 150.0,
                "show_times": None,
                "image_url": None,
                "is_special": True,
                "is_active": True,
                "created_at": datetime.utcnow(),
            },
            {
                "exhibition_id": str(uuid.uuid4()),
                "name": "Digital Art Revolution",
                "description": "An immersive digital art experience featuring interactive installations, AI-generated artwork, and holographic displays. Walk through virtual worlds created by leading digital artists.",
                "start_date": today.isoformat(),
                "end_date": (today + timedelta(days=60)).isoformat(),
                "daily_capacity": 200,
                "ticket_price": 200.0,
                "show_times": ["10:00 AM", "1:00 PM", "4:00 PM", "7:00 PM"],
                "image_url": None,
                "is_special": True,
                "is_active": True,
                "created_at": datetime.utcnow(),
            },
            {
                "exhibition_id": str(uuid.uuid4()),
                "name": "Wildlife Photography Exhibition",
                "description": "Award-winning wildlife photographs from around the globe. From the savannas of Africa to the Arctic tundra, witness nature's most breathtaking moments captured by world-renowned photographers.",
                "start_date": today.isoformat(),
                "end_date": (today + timedelta(days=45)).isoformat(),
                "daily_capacity": 500,
                "ticket_price": 100.0,
                "show_times": None,
                "image_url": None,
                "is_special": False,
                "is_active": True,
                "created_at": datetime.utcnow(),
            },
            {
                "exhibition_id": str(uuid.uuid4()),
                "name": "Space & Cosmos Planetarium Show",
                "description": "Journey through the cosmos in our state-of-the-art planetarium. Explore distant galaxies, witness star formations, and learn about our solar system in a stunning 360-degree immersive dome experience.",
                "start_date": today.isoformat(),
                "end_date": (today + timedelta(days=180)).isoformat(),
                "daily_capacity": 150,
                "ticket_price": 250.0,
                "show_times": ["11:00 AM", "2:00 PM", "5:00 PM", "8:00 PM"],
                "image_url": None,
                "is_special": True,
                "is_active": True,
                "created_at": datetime.utcnow(),
            },
            {
                "exhibition_id": str(uuid.uuid4()),
                "name": "Indian Heritage Gallery",
                "description": "A permanent exhibition showcasing India's rich cultural heritage. Features ancient sculptures, Mughal miniature paintings, traditional textiles, and artifacts from the Indus Valley Civilization.",
                "start_date": today.isoformat(),
                "end_date": (today + timedelta(days=365)).isoformat(),
                "daily_capacity": 1000,
                "ticket_price": 75.0,
                "show_times": None,
                "image_url": None,
                "is_special": False,
                "is_active": True,
                "created_at": datetime.utcnow(),
            },
        ]

        await exhibitions_col.insert_many(exhibitions)
        print(f"  ✅ {len(exhibitions)} exhibitions created")
    else:
        print(f"  ℹ️ {existing_count} exhibitions already exist")

    # ── Create Indexes ───────────────────────────────────────────────
    await users_col.create_index("email", unique=True)
    await db["tickets"].create_index("booking_id", unique=True)
    await db["tickets"].create_index("user_id")
    await db["transactions"].create_index("transaction_id", unique=True)
    await db["chat_logs"].create_index("session_id")
    print("  ✅ Database indexes created")

    client.close()
    print("🎉 Database seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_database())
