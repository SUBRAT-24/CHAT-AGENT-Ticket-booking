"""MongoDB connection manager using Motor async driver."""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

_client: AsyncIOMotorClient = None
_database: AsyncIOMotorDatabase = None


async def connect_to_mongo():
    """Establish connection to MongoDB."""
    global _client, _database
    _client = AsyncIOMotorClient(settings.MONGODB_URL)
    _database = _client[settings.DATABASE_NAME]

    # Create indexes
    await _database.users.create_index("email", unique=True)
    await _database.tickets.create_index("booking_id", unique=True)
    await _database.tickets.create_index("user_id")
    await _database.exhibitions.create_index("exhibition_id", unique=True)
    await _database.transactions.create_index("transaction_id", unique=True)
    await _database.chat_logs.create_index("session_id")
    await _database.chat_logs.create_index("user_id")

    print(f"✅ Connected to MongoDB: {settings.DATABASE_NAME}")


async def close_mongo_connection():
    """Close the MongoDB connection."""
    global _client
    if _client:
        _client.close()
        print("🔌 MongoDB connection closed.")


def get_database() -> AsyncIOMotorDatabase:
    """Get the current database instance."""
    return _database


def get_collection(collection_name: str):
    """Get a specific collection from the database."""
    return _database[collection_name]
