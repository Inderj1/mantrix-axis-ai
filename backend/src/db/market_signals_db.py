"""
MongoDB storage layer for market signals
Handles persistence, querying, and updates of market intelligence signals
"""
from typing import List, Optional, Dict
from datetime import datetime
from pymongo import MongoClient, DESCENDING
from pymongo.errors import DuplicateKeyError
import structlog

from ..models.market_signal import (
    MarketSignal,
    MarketSignalCreate,
    MarketSignalUpdate,
    SignalCategory,
    SeverityLevel
)
from ..config import settings

logger = structlog.get_logger()


class MarketSignalsDB:
    """MongoDB storage for market signals"""

    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or settings.mongodb_url
        self.client = None
        self.db = None
        self.signals_collection = None
        self.logger = logger.bind(component="MarketSignalsDB")

    def connect(self):
        """Establish connection to MongoDB"""
        try:
            self.client = MongoClient(self.connection_string)
            self.db = self.client.nlp_sql_db
            self.signals_collection = self.db.market_signals

            # Create indexes
            self.signals_collection.create_index("id", unique=True)
            self.signals_collection.create_index("category")
            self.signals_collection.create_index("severityScore")
            self.signals_collection.create_index("isActive")
            self.signals_collection.create_index("detectedAt")
            self.signals_collection.create_index([("category", 1), ("isActive", 1)])

            self.logger.info("connected_to_mongodb", database="nlp_sql_db")
        except Exception as e:
            self.logger.error("mongodb_connection_error", error=str(e), exc_info=True)
            raise

    def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            self.logger.info("disconnected_from_mongodb")

    def insert_signal(self, signal: MarketSignal) -> bool:
        """
        Insert a new signal into the database
        Returns True if inserted, False if duplicate
        """
        try:
            signal_dict = signal.dict()
            # Convert datetime objects to ISO strings for storage
            if isinstance(signal_dict.get("detectedAt"), datetime):
                signal_dict["detectedAt"] = signal_dict["detectedAt"].isoformat()
            if signal_dict.get("dismissedAt") and isinstance(signal_dict["dismissedAt"], datetime):
                signal_dict["dismissedAt"] = signal_dict["dismissedAt"].isoformat()
            if signal_dict.get("resolvedAt") and isinstance(signal_dict["resolvedAt"], datetime):
                signal_dict["resolvedAt"] = signal_dict["resolvedAt"].isoformat()

            self.signals_collection.insert_one(signal_dict)
            self.logger.info("signal_inserted", signal_id=signal.id, category=signal.category.value)
            return True
        except DuplicateKeyError:
            self.logger.warning("duplicate_signal", signal_id=signal.id)
            return False
        except Exception as e:
            self.logger.error("signal_insert_error", signal_id=signal.id, error=str(e), exc_info=True)
            raise

    def insert_signals_bulk(self, signals: List[MarketSignal]) -> Dict[str, int]:
        """
        Insert multiple signals in bulk
        Returns dict with counts of inserted and duplicate signals
        """
        inserted = 0
        duplicates = 0
        errors = 0

        for signal in signals:
            try:
                if self.insert_signal(signal):
                    inserted += 1
                else:
                    duplicates += 1
            except Exception:
                errors += 1

        self.logger.info(
            "bulk_insert_complete",
            total=len(signals),
            inserted=inserted,
            duplicates=duplicates,
            errors=errors
        )

        return {
            "total": len(signals),
            "inserted": inserted,
            "duplicates": duplicates,
            "errors": errors
        }

    def get_signal_by_id(self, signal_id: str) -> Optional[MarketSignal]:
        """Get a signal by its ID"""
        try:
            doc = self.signals_collection.find_one({"id": signal_id})
            if doc:
                doc.pop("_id", None)  # Remove MongoDB internal ID
                return MarketSignal(**doc)
            return None
        except Exception as e:
            self.logger.error("signal_fetch_error", signal_id=signal_id, error=str(e), exc_info=True)
            return None

    def get_signals_by_category(
        self,
        category: SignalCategory,
        active_only: bool = True,
        limit: int = 100
    ) -> List[MarketSignal]:
        """Get all signals for a specific category"""
        try:
            query = {"category": category.value}
            if active_only:
                query["isActive"] = True

            docs = self.signals_collection.find(query).sort("severityScore", DESCENDING).limit(limit)
            signals = []
            for doc in docs:
                doc.pop("_id", None)
                signals.append(MarketSignal(**doc))

            return signals
        except Exception as e:
            self.logger.error(
                "category_fetch_error",
                category=category.value,
                error=str(e),
                exc_info=True
            )
            return []

    def get_all_signals(
        self,
        active_only: bool = True,
        min_severity: Optional[int] = None,
        categories: Optional[List[SignalCategory]] = None,
        limit: int = 500
    ) -> List[MarketSignal]:
        """
        Get all signals with optional filters
        """
        try:
            query = {}

            if active_only:
                query["isActive"] = True

            if min_severity is not None:
                query["severityScore"] = {"$gte": min_severity}

            if categories:
                query["category"] = {"$in": [cat.value for cat in categories]}

            docs = self.signals_collection.find(query).sort("severityScore", DESCENDING).limit(limit)
            signals = []
            for doc in docs:
                doc.pop("_id", None)
                signals.append(MarketSignal(**doc))

            return signals
        except Exception as e:
            self.logger.error("signals_fetch_error", error=str(e), exc_info=True)
            return []

    def update_signal(self, signal_id: str, update: MarketSignalUpdate) -> bool:
        """Update a signal (e.g., dismiss, resolve, change severity)"""
        try:
            update_dict = update.dict(exclude_unset=True)

            # Convert datetime objects to ISO strings
            for key in ["dismissedAt", "resolvedAt"]:
                if key in update_dict and isinstance(update_dict[key], datetime):
                    update_dict[key] = update_dict[key].isoformat()

            result = self.signals_collection.update_one(
                {"id": signal_id},
                {"$set": update_dict}
            )

            if result.modified_count > 0:
                self.logger.info("signal_updated", signal_id=signal_id, updates=list(update_dict.keys()))
                return True
            else:
                self.logger.warning("signal_not_found_for_update", signal_id=signal_id)
                return False

        except Exception as e:
            self.logger.error("signal_update_error", signal_id=signal_id, error=str(e), exc_info=True)
            return False

    def delete_signal(self, signal_id: str) -> bool:
        """Delete a signal from the database"""
        try:
            result = self.signals_collection.delete_one({"id": signal_id})
            if result.deleted_count > 0:
                self.logger.info("signal_deleted", signal_id=signal_id)
                return True
            else:
                self.logger.warning("signal_not_found_for_delete", signal_id=signal_id)
                return False
        except Exception as e:
            self.logger.error("signal_delete_error", signal_id=signal_id, error=str(e), exc_info=True)
            return False

    def get_summary_stats(self, active_only: bool = True) -> Dict:
        """Get summary statistics for all signals"""
        try:
            match_stage = {}
            if active_only:
                match_stage["isActive"] = True

            pipeline = [
                {"$match": match_stage} if match_stage else {"$match": {}},
                {
                    "$group": {
                        "_id": "$category",
                        "count": {"$sum": 1},
                        "total_impact": {"$sum": "$impactValue"},
                        "avg_severity": {"$avg": "$severityScore"},
                        "critical_count": {
                            "$sum": {"$cond": [{"$gte": ["$severityScore", 80]}, 1, 0]}
                        }
                    }
                }
            ]

            results = list(self.signals_collection.aggregate(pipeline))

            # Calculate totals
            total_signals = sum(r["count"] for r in results)
            total_impact = sum(r.get("total_impact", 0) for r in results)
            total_critical = sum(r.get("critical_count", 0) for r in results)

            category_breakdown = {
                r["_id"]: {
                    "count": r["count"],
                    "total_impact": r.get("total_impact", 0),
                    "avg_severity": round(r["avg_severity"], 1),
                    "critical_count": r.get("critical_count", 0)
                }
                for r in results
            }

            return {
                "total_signals": total_signals,
                "total_impact": total_impact,
                "critical_count": total_critical,
                "active_categories": len(results),
                "categories": category_breakdown
            }

        except Exception as e:
            self.logger.error("summary_stats_error", error=str(e), exc_info=True)
            return {
                "total_signals": 0,
                "total_impact": 0,
                "critical_count": 0,
                "active_categories": 0,
                "categories": {}
            }

    def cleanup_old_signals(self, days_old: int = 30) -> int:
        """
        Delete inactive signals older than specified days
        Returns count of deleted signals
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            cutoff_iso = cutoff_date.isoformat()

            result = self.signals_collection.delete_many({
                "isActive": False,
                "detectedAt": {"$lt": cutoff_iso}
            })

            deleted = result.deleted_count
            self.logger.info("old_signals_cleaned_up", deleted_count=deleted, days_old=days_old)
            return deleted

        except Exception as e:
            self.logger.error("cleanup_error", error=str(e), exc_info=True)
            return 0


# Singleton instance
_db_instance: Optional[MarketSignalsDB] = None


def get_market_signals_db() -> Optional[MarketSignalsDB]:
    """
    Get or create the singleton MarketSignalsDB instance.
    Returns None if MongoDB is not available or configured.
    """
    global _db_instance
    if _db_instance is None:
        # Check if MongoDB URL is configured
        if not settings.mongodb_url or settings.mongodb_url.strip() == '':
            logger.warning("mongodb_not_configured", message="MongoDB URL not configured, market signals DB unavailable")
            return None
        try:
            _db_instance = MarketSignalsDB()
            _db_instance.connect()
        except Exception as e:
            logger.warning("mongodb_connection_failed", error=str(e), message="Market signals DB unavailable")
            return None
    return _db_instance
