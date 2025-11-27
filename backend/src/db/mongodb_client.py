"""MongoDB client for managing conversations"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import motor.motor_asyncio
from pymongo import DESCENDING
from bson import ObjectId
from pydantic import BaseModel
import structlog

from src.config import settings

logger = structlog.get_logger()


class MongoDBClient:
    """Async MongoDB client for conversation and dashboard management"""

    def __init__(self):
        self.client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
        self.db = None
        self.conversations_collection = None
        self.dashboards_collection = None
        # Alert & Notification collections
        self.notification_preferences_collection = None
        self.scheduled_reports_collection = None
        # Collaboration collections
        self.dashboard_permissions_collection = None
        self.dashboard_comments_collection = None
        
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongodb_url)
            self.db = self.client[settings.mongodb_database]
            self.conversations_collection = self.db[settings.mongodb_conversations_collection]
            self.dashboards_collection = self.db["dashboards"]
            # Alert & Notification collections
            self.notification_preferences_collection = self.db["notification_preferences"]
            self.scheduled_reports_collection = self.db["scheduled_reports"]
            # Collaboration collections
            self.dashboard_permissions_collection = self.db["dashboard_permissions"]
            self.dashboard_comments_collection = self.db["dashboard_comments"]

            # Create indexes
            await self._create_indexes()
            await self._create_dashboard_indexes()
            await self._create_notification_indexes()
            await self._create_collaboration_indexes()

            # Test connection
            await self.client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")

        except Exception as e:
            logger.error("Failed to connect to MongoDB", error=str(e))
            raise
            
    async def _create_indexes(self):
        """Create necessary indexes for performance"""
        try:
            # Index on conversationId for fast lookups
            await self.conversations_collection.create_index("conversationId", unique=True)
            
            # Index on userId and updatedAt for listing conversations
            await self.conversations_collection.create_index([
                ("userId", 1),
                ("updatedAt", DESCENDING)
            ])
            
            # Text index for search functionality
            await self.conversations_collection.create_index([
                ("title", "text"),
                ("messages.content", "text")
            ])
            
            logger.info("MongoDB indexes created successfully")

        except Exception as e:
            logger.warning("Error creating indexes", error=str(e))

    async def _create_dashboard_indexes(self):
        """Create indexes for dashboards collection"""
        try:
            # Index on organization_id for listing dashboards
            await self.dashboards_collection.create_index("organization_id")

            # Index on owner_id for filtering by owner
            await self.dashboards_collection.create_index("owner_id")

            # Fix share_token index - must be sparse to allow multiple docs without share_token
            # First, try to drop old non-sparse index if it exists
            try:
                # Check if index exists and is not sparse
                indexes = await self.dashboards_collection.index_information()
                if "share_token_1" in indexes:
                    index_info = indexes["share_token_1"]
                    if not index_info.get("sparse", False):
                        logger.info("Dropping old non-sparse share_token index")
                        await self.dashboards_collection.drop_index("share_token_1")
                        # Clean up null share_token values
                        await self.dashboards_collection.update_many(
                            {"share_token": None},
                            {"$unset": {"share_token": ""}}
                        )
            except Exception as e:
                logger.warning(f"Error checking/dropping share_token index: {e}")

            # Index on share_token for shared dashboard lookup (unique, sparse)
            await self.dashboards_collection.create_index(
                "share_token",
                unique=True,
                sparse=True
            )

            # Compound index for listing user's dashboards
            await self.dashboards_collection.create_index([
                ("owner_id", 1),
                ("updated_at", DESCENDING)
            ])

            # Index for public dashboards within an organization
            await self.dashboards_collection.create_index([
                ("organization_id", 1),
                ("is_public", 1)
            ])

            logger.info("Dashboard indexes created successfully")

        except Exception as e:
            logger.warning("Error creating dashboard indexes", error=str(e))

    async def _create_notification_indexes(self):
        """Create indexes for notification collections"""
        try:
            # Notification preferences - unique user_id
            await self.notification_preferences_collection.create_index(
                "user_id",
                unique=True
            )

            # Scheduled reports - user_id and next_run for scheduling
            await self.scheduled_reports_collection.create_index("user_id")
            await self.scheduled_reports_collection.create_index([
                ("active", 1),
                ("next_run", 1)
            ])
            await self.scheduled_reports_collection.create_index("dashboard_id")

            logger.info("Notification indexes created successfully")

        except Exception as e:
            logger.warning("Error creating notification indexes", error=str(e))

    async def _create_collaboration_indexes(self):
        """Create indexes for collaboration collections"""
        try:
            # Dashboard permissions - unique per dashboard
            await self.dashboard_permissions_collection.create_index(
                "dashboard_id",
                unique=True
            )
            await self.dashboard_permissions_collection.create_index("share_token", sparse=True)

            # Dashboard comments - by dashboard and widget
            await self.dashboard_comments_collection.create_index("dashboard_id")
            await self.dashboard_comments_collection.create_index([
                ("dashboard_id", 1),
                ("widget_id", 1)
            ])
            await self.dashboard_comments_collection.create_index("thread_id")
            await self.dashboard_comments_collection.create_index([
                ("dashboard_id", 1),
                ("created_at", DESCENDING)
            ])

            logger.info("Collaboration indexes created successfully")

        except Exception as e:
            logger.warning("Error creating collaboration indexes", error=str(e))

    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
            
    async def create_conversation(self, conversation_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new conversation"""
        try:
            conversation = {
                "conversationId": conversation_id,
                "userId": user_id or "default",
                "title": "New Conversation",
                "messages": [],
                "createdAt": datetime.now(timezone.utc),
                "updatedAt": datetime.now(timezone.utc),
                "metadata": {
                    "messageCount": 0,
                    "lastActivity": datetime.now(timezone.utc),
                    "starred": False,
                    "tags": []
                }
            }
            
            result = await self.conversations_collection.insert_one(conversation)
            conversation["_id"] = str(result.inserted_id)
            
            logger.info("Created new conversation", conversation_id=conversation_id)
            return conversation
            
        except Exception as e:
            logger.error("Error creating conversation", error=str(e))
            raise
            
    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a conversation by ID"""
        try:
            conversation = await self.conversations_collection.find_one(
                {"conversationId": conversation_id}
            )
            
            if conversation:
                conversation["_id"] = str(conversation["_id"])
                
            return conversation
            
        except Exception as e:
            logger.error("Error getting conversation", error=str(e))
            raise
            
    async def list_conversations(
        self, 
        user_id: str = "default", 
        limit: int = 50, 
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """List conversations for a user"""
        try:
            cursor = self.conversations_collection.find(
                {"userId": user_id}
            ).sort("updatedAt", DESCENDING).skip(skip).limit(limit)
            
            conversations = []
            async for conversation in cursor:
                conversation["_id"] = str(conversation["_id"])
                conversations.append(conversation)
                
            return conversations
            
        except Exception as e:
            logger.error("Error listing conversations", error=str(e))
            raise
            
    async def add_message(
        self, 
        conversation_id: str, 
        message: Dict[str, Any]
    ) -> bool:
        """Add a message to a conversation"""
        try:
            # Update conversation summary if it's the first user message
            update_data = {
                "$push": {"messages": message},
                "$set": {
                    "updatedAt": datetime.now(timezone.utc),
                    "metadata.lastActivity": datetime.now(timezone.utc)
                },
                "$inc": {"metadata.messageCount": 1}
            }
            
            # If it's the first user message, update title and summary
            if message.get("type") == "user":
                conversation = await self.get_conversation(conversation_id)
                if conversation and not any(m.get("type") == "user" for m in conversation.get("messages", [])):
                    content = message.get("content", "")
                    update_data["$set"]["title"] = content[:50] + ("..." if len(content) > 50 else "")
            
            result = await self.conversations_collection.update_one(
                {"conversationId": conversation_id},
                update_data
            )
            
            if result.modified_count == 0:
                # Conversation doesn't exist, create it
                await self.create_conversation(conversation_id)
                result = await self.conversations_collection.update_one(
                    {"conversationId": conversation_id},
                    update_data
                )
            
            logger.info("Added message to conversation", conversation_id=conversation_id)
            return result.modified_count > 0
            
        except Exception as e:
            logger.error("Error adding message", error=str(e))
            raise
            
    async def update_conversation(
        self, 
        conversation_id: str, 
        updates: Dict[str, Any]
    ) -> bool:
        """Update conversation metadata"""
        try:
            updates["updatedAt"] = datetime.now(timezone.utc)
            
            result = await self.conversations_collection.update_one(
                {"conversationId": conversation_id},
                {"$set": updates}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error("Error updating conversation", error=str(e))
            raise
            
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        try:
            result = await self.conversations_collection.delete_one(
                {"conversationId": conversation_id}
            )
            
            logger.info("Deleted conversation", conversation_id=conversation_id)
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error("Error deleting conversation", error=str(e))
            raise
            
    async def search_conversations(
        self,
        user_id: str,
        query: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search conversations by text"""
        try:
            cursor = self.conversations_collection.find(
                {
                    "userId": user_id,
                    "$text": {"$search": query}
                }
            ).sort("updatedAt", DESCENDING).limit(limit)

            conversations = []
            async for conversation in cursor:
                conversation["_id"] = str(conversation["_id"])
                conversations.append(conversation)

            return conversations

        except Exception as e:
            logger.error("Error searching conversations", error=str(e))
            raise

    # Property accessors for collections (shorthand)
    @property
    def dashboards(self):
        """Access dashboards collection"""
        return self.dashboards_collection

    @property
    def notification_preferences(self):
        """Access notification preferences collection"""
        return self.notification_preferences_collection

    @property
    def scheduled_reports(self):
        """Access scheduled reports collection"""
        return self.scheduled_reports_collection

    @property
    def dashboard_permissions(self):
        """Access dashboard permissions collection"""
        return self.dashboard_permissions_collection

    @property
    def dashboard_comments(self):
        """Access dashboard comments collection"""
        return self.dashboard_comments_collection


# Global instance
mongodb_client = MongoDBClient()


async def get_mongodb_client() -> MongoDBClient:
    """Get MongoDB client instance"""
    if not mongodb_client.client:
        await mongodb_client.connect()
    return mongodb_client