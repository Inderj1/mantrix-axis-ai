"""
DEPRECATED: This service is deprecated. Use mongodb_client.py instead.

This service uses sync pymongo with snake_case field names (conversation_id, user_id, etc.)
which is incompatible with mongodb_client.py that uses async motor with camelCase fields
(conversationId, userId, etc.). Both write to the same MongoDB collection, causing
data consistency issues.

All conversation routes have been migrated to use mongodb_client.py.
This file is kept for reference only and should not be used.

Migration Date: December 2024
"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pymongo import MongoClient, DESCENDING
from pymongo.errors import PyMongoError
import structlog
from ..models.conversation import (
    Conversation, Message, ConversationMetadata,
    CreateConversationRequest, CreateConversationResponse,
    UpdateConversationRequest, ConversationListResponse
)
from ..config import settings

logger = structlog.get_logger()


class ConversationService:
    """Service for managing conversations with MongoDB backend."""
    
    def __init__(self):
        """Initialize MongoDB connection and collections."""
        try:
            # Connect to MongoDB
            self.client = MongoClient(settings.mongodb_url)
            self.db = self.client[settings.mongodb_db_name]
            self.conversations_collection = self.db["conversations"]
            
            # Create indexes for better performance
            self._create_indexes()
            
            logger.info("ConversationService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ConversationService: {e}")
            raise
    
    def _create_indexes(self):
        """Create database indexes for better query performance."""
        try:
            # Index on user_id and updated_at for listing conversations
            self.conversations_collection.create_index([
                ("user_id", 1),
                ("updated_at", DESCENDING)
            ])
            
            # Index on conversation_id for fast lookups
            self.conversations_collection.create_index("conversation_id", unique=True)
            
            # Text index for search functionality
            self.conversations_collection.create_index([
                ("title", "text"),
                ("messages.content", "text")
            ])
            
            logger.info("MongoDB indexes created successfully")
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
    
    def create_conversation(self, request: CreateConversationRequest) -> CreateConversationResponse:
        """Create a new conversation."""
        try:
            # Generate conversation ID if not provided
            conversation_id = request.conversation_id or f"conv-{uuid.uuid4()}"
            
            # Create conversation document
            conversation = {
                "conversation_id": conversation_id,
                "user_id": request.user_id or "default",
                "title": request.title or "New Conversation",
                "messages": [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "metadata": {
                    "message_count": 0,
                    "last_activity": datetime.utcnow(),
                    "starred": False,
                    "tags": []
                }
            }
            
            # Insert into MongoDB
            self.conversations_collection.insert_one(conversation)
            
            logger.info(f"Created conversation: {conversation_id}")
            return CreateConversationResponse(
                conversation_id=conversation_id,
                created_at=conversation["created_at"]
            )
            
        except Exception as e:
            logger.error(f"Failed to create conversation: {e}")
            raise
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        try:
            doc = self.conversations_collection.find_one({"conversation_id": conversation_id})
            if not doc:
                return None
            
            # Convert MongoDB document to Pydantic model
            return self._doc_to_conversation(doc)
            
        except Exception as e:
            logger.error(f"Failed to get conversation {conversation_id}: {e}")
            raise
    
    def list_conversations(
        self, 
        user_id: str = "default", 
        limit: int = 50, 
        skip: int = 0
    ) -> ConversationListResponse:
        """List conversations for a user."""
        try:
            # Query conversations
            cursor = self.conversations_collection.find(
                {"user_id": user_id}
            ).sort("updated_at", DESCENDING).skip(skip).limit(limit)
            
            # Convert to list
            conversations = []
            for doc in cursor:
                conv = self._doc_to_conversation(doc)
                conversations.append(conv)
            
            # Get total count
            total = self.conversations_collection.count_documents({"user_id": user_id})
            
            return ConversationListResponse(
                conversations=conversations,
                total=total,
                limit=limit,
                skip=skip
            )
            
        except Exception as e:
            logger.error(f"Failed to list conversations: {e}")
            raise
    
    def add_message(self, conversation_id: str, message: Message) -> bool:
        """Add a message to a conversation."""
        try:
            # Prepare message document
            message_doc = {
                "id": message.id or str(uuid.uuid4()),
                "type": message.type,
                "content": message.content,
                "timestamp": message.timestamp or datetime.utcnow(),
                "sql": message.sql,
                "results": message.results,
                "result_count": message.result_count,
                "error": message.error,
                "metadata": message.metadata
            }
            
            # Update conversation
            result = self.conversations_collection.update_one(
                {"conversation_id": conversation_id},
                {
                    "$push": {"messages": message_doc},
                    "$set": {
                        "updated_at": datetime.utcnow(),
                        "metadata.last_activity": datetime.utcnow()
                    },
                    "$inc": {"metadata.message_count": 1}
                }
            )
            
            # Auto-update title based on first user message if still default
            if message.type == "user" and result.modified_count > 0:
                self._auto_update_title(conversation_id, message.content)
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to add message to conversation {conversation_id}: {e}")
            raise
    
    def update_conversation(
        self, 
        conversation_id: str, 
        updates: UpdateConversationRequest
    ) -> bool:
        """Update conversation metadata."""
        try:
            update_doc = {"$set": {"updated_at": datetime.utcnow()}}
            
            if updates.title is not None:
                update_doc["$set"]["title"] = updates.title
            
            if updates.starred is not None:
                update_doc["$set"]["metadata.starred"] = updates.starred
            
            if updates.tags is not None:
                update_doc["$set"]["metadata.tags"] = updates.tags
            
            result = self.conversations_collection.update_one(
                {"conversation_id": conversation_id},
                update_doc
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to update conversation {conversation_id}: {e}")
            raise
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        try:
            result = self.conversations_collection.delete_one(
                {"conversation_id": conversation_id}
            )
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Failed to delete conversation {conversation_id}: {e}")
            raise
    
    def search_conversations(
        self, 
        user_id: str, 
        query: str, 
        limit: int = 20
    ) -> List[Conversation]:
        """Search conversations by text."""
        try:
            cursor = self.conversations_collection.find(
                {
                    "user_id": user_id,
                    "$text": {"$search": query}
                },
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(limit)
            
            conversations = []
            for doc in cursor:
                conv = self._doc_to_conversation(doc)
                conversations.append(conv)
            
            return conversations
            
        except Exception as e:
            logger.error(f"Failed to search conversations: {e}")
            raise
    
    def delete_all_conversations(self, user_id: str) -> int:
        """Delete all conversations for a user."""
        try:
            result = self.conversations_collection.delete_many({"user_id": user_id})
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete all conversations for user {user_id}: {e}")
            raise
    
    def _auto_update_title(self, conversation_id: str, first_message: str):
        """Auto-update conversation title based on first user message."""
        try:
            # Check if title is still default
            conv = self.conversations_collection.find_one(
                {"conversation_id": conversation_id},
                {"title": 1}
            )
            
            if conv and conv.get("title", "").lower() in ["new conversation", "untitled"]:
                # Create title from first message (max 50 chars)
                new_title = first_message[:50]
                if len(first_message) > 50:
                    new_title += "..."
                
                self.conversations_collection.update_one(
                    {"conversation_id": conversation_id},
                    {"$set": {"title": new_title}}
                )
                
                logger.info(f"Auto-updated title for conversation {conversation_id}")
                
        except Exception as e:
            logger.error(f"Failed to auto-update title: {e}")
    
    def _doc_to_conversation(self, doc: Dict[str, Any]) -> Conversation:
        """Convert MongoDB document to Conversation model."""
        # Convert messages
        messages = []
        for msg_doc in doc.get("messages", []):
            messages.append(Message(
                id=msg_doc.get("id"),
                type=msg_doc.get("type"),
                content=msg_doc.get("content"),
                timestamp=msg_doc.get("timestamp"),
                sql=msg_doc.get("sql"),
                results=msg_doc.get("results"),
                result_count=msg_doc.get("result_count"),
                error=msg_doc.get("error"),
                metadata=msg_doc.get("metadata")
            ))
        
        # Convert metadata
        metadata_doc = doc.get("metadata", {})
        metadata = ConversationMetadata(
            message_count=metadata_doc.get("message_count", 0),
            last_activity=metadata_doc.get("last_activity", datetime.utcnow()),
            starred=metadata_doc.get("starred", False),
            tags=metadata_doc.get("tags", [])
        )
        
        return Conversation(
            conversation_id=doc.get("conversation_id"),
            user_id=doc.get("user_id", "default"),
            title=doc.get("title", "New Conversation"),
            messages=messages,
            created_at=doc.get("created_at", datetime.utcnow()),
            updated_at=doc.get("updated_at", datetime.utcnow()),
            metadata=metadata
        )