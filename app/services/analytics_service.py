"""Analytics service for dashboard insights and reporting."""

from datetime import datetime, timedelta
from typing import List, Optional
from app.database.connection import get_collection


class AnalyticsService:
    """Generates analytics and insights from booking data."""

    @staticmethod
    async def get_dashboard_summary() -> dict:
        """Get the main dashboard summary with key metrics."""
        tickets_col = get_collection("tickets")
        transactions_col = get_collection("transactions")
        chat_col = get_collection("chat_logs")

        today = datetime.utcnow().strftime("%Y-%m-%d")

        # Total bookings
        total_bookings = await tickets_col.count_documents({})

        # Today's bookings
        tickets_today = await tickets_col.count_documents({"visit_date": today})

        # Total revenue
        total_revenue = 0.0
        async for t in transactions_col.find({"status": "completed"}):
            total_revenue += t.get("amount", 0)

        # Today's revenue
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        revenue_today = 0.0
        async for t in transactions_col.find(
            {"status": "completed", "completed_at": {"$gte": today_start}}
        ):
            revenue_today += t.get("amount", 0)

        # Active chat sessions (last 30 min)
        thirty_min_ago = datetime.utcnow() - timedelta(minutes=30)
        active_sessions = await chat_col.count_documents(
            {"last_activity": {"$gte": thirty_min_ago}}
        )

        # Confirmed bookings count
        confirmed_bookings = await tickets_col.count_documents(
            {"status": "confirmed"}
        )

        # Cancelled bookings count
        cancelled_bookings = await tickets_col.count_documents(
            {"status": "cancelled"}
        )

        # Pending bookings count
        pending_bookings = await tickets_col.count_documents(
            {"status": "pending"}
        )

        return {
            "total_bookings": total_bookings,
            "confirmed_bookings": confirmed_bookings,
            "cancelled_bookings": cancelled_bookings,
            "pending_bookings": pending_bookings,
            "tickets_today": tickets_today,
            "total_revenue": round(total_revenue, 2),
            "revenue_today": round(revenue_today, 2),
            "active_sessions": active_sessions,
        }

    @staticmethod
    async def get_ticket_type_distribution() -> List[dict]:
        """Get distribution of ticket types."""
        tickets_col = get_collection("tickets")
        pipeline = [
            {"$match": {"status": {"$in": ["confirmed", "pending"]}}},
            {"$group": {"_id": "$ticket_type", "count": {"$sum": "$num_tickets"}}},
            {"$sort": {"count": -1}},
        ]
        results = []
        async for doc in tickets_col.aggregate(pipeline):
            results.append({"ticket_type": doc["_id"], "count": doc["count"]})
        return results

    @staticmethod
    async def get_visitor_demographics() -> List[dict]:
        """Get visitor category distribution."""
        tickets_col = get_collection("tickets")
        pipeline = [
            {"$match": {"status": {"$in": ["confirmed", "pending"]}}},
            {
                "$group": {
                    "_id": "$visitor_category",
                    "count": {"$sum": "$num_tickets"},
                }
            },
            {"$sort": {"count": -1}},
        ]
        results = []
        async for doc in tickets_col.aggregate(pipeline):
            results.append({"category": doc["_id"], "count": doc["count"]})
        return results

    @staticmethod
    async def get_daily_trends(days: int = 30) -> List[dict]:
        """Get daily booking trends for the last N days."""
        tickets_col = get_collection("tickets")
        cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

        pipeline = [
            {"$match": {"visit_date": {"$gte": cutoff}}},
            {
                "$group": {
                    "_id": "$visit_date",
                    "bookings": {"$sum": 1},
                    "tickets": {"$sum": "$num_tickets"},
                    "revenue": {"$sum": "$total_price"},
                }
            },
            {"$sort": {"_id": 1}},
        ]

        results = []
        async for doc in tickets_col.aggregate(pipeline):
            results.append(
                {
                    "date": doc["_id"],
                    "bookings": doc["bookings"],
                    "tickets": doc["tickets"],
                    "revenue": round(doc["revenue"], 2),
                }
            )
        return results

    @staticmethod
    async def get_language_distribution() -> List[dict]:
        """Get distribution of chat languages."""
        chat_col = get_collection("chat_logs")
        pipeline = [
            {"$group": {"_id": "$language", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]
        results = []
        async for doc in chat_col.aggregate(pipeline):
            results.append({"language": doc["_id"] or "en", "count": doc["count"]})
        return results

    @staticmethod
    async def get_hourly_traffic(date_str: Optional[str] = None) -> List[dict]:
        """Get hourly booking traffic for a specific date."""
        tickets_col = get_collection("tickets")
        if not date_str:
            date_str = datetime.utcnow().strftime("%Y-%m-%d")

        pipeline = [
            {"$match": {"visit_date": date_str}},
            {
                "$group": {
                    "_id": {"$hour": "$created_at"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id": 1}},
        ]

        results = []
        async for doc in tickets_col.aggregate(pipeline):
            results.append({"hour": doc["_id"], "bookings": doc["count"]})
        return results

    @staticmethod
    async def get_recent_bookings(limit: int = 20) -> List[dict]:
        """Get the most recent bookings."""
        tickets_col = get_collection("tickets")
        bookings = []
        async for ticket in tickets_col.find(
            {}, {"_id": 0}
        ).sort("created_at", -1).limit(limit):
            # Convert ALL datetime fields for JSON serialization
            for key, value in list(ticket.items()):
                if isinstance(value, datetime):
                    ticket[key] = value.isoformat()
            bookings.append(ticket)
        return bookings

    @staticmethod
    async def get_exhibition_popularity() -> List[dict]:
        """Get exhibition popularity based on bookings."""
        tickets_col = get_collection("tickets")
        pipeline = [
            {
                "$match": {
                    "exhibition_id": {"$ne": None},
                    "status": {"$in": ["confirmed", "pending"]},
                }
            },
            {
                "$group": {
                    "_id": {
                        "exhibition_id": "$exhibition_id",
                        "exhibition_name": "$exhibition_name",
                    },
                    "bookings": {"$sum": 1},
                    "tickets": {"$sum": "$num_tickets"},
                    "revenue": {"$sum": "$total_price"},
                }
            },
            {"$sort": {"tickets": -1}},
        ]

        results = []
        async for doc in tickets_col.aggregate(pipeline):
            results.append(
                {
                    "exhibition_id": doc["_id"].get("exhibition_id"),
                    "exhibition_name": doc["_id"].get("exhibition_name", "Unknown"),
                    "bookings": doc["bookings"],
                    "tickets": doc["tickets"],
                    "revenue": round(doc["revenue"], 2),
                }
            )
        return results
