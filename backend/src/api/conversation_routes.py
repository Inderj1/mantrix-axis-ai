"""API routes for conversation management - Using async MongoDB client."""
import uuid
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query
import structlog
from ..models.conversation import (
    CreateConversationRequest,
    CreateConversationResponse,
    ConversationListResponse,
    Conversation,
    Message,
    ConversationMetadata,
    UpdateConversationRequest,
    AddMessageRequest,
    SearchConversationsRequest
)
from ..db.mongodb_client import MongoDBClient, get_mongodb_client

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


def _doc_to_conversation(doc: dict) -> Conversation:
    """Convert MongoDB document (camelCase) to Conversation model."""
    if not doc:
        return None

    # Convert messages
    messages = []
    for msg_doc in doc.get("messages", []):
        messages.append(Message(
            id=msg_doc.get("id", str(uuid.uuid4())),
            type=msg_doc.get("type", "user"),
            content=msg_doc.get("content", ""),
            timestamp=msg_doc.get("timestamp", datetime.now(timezone.utc)),
            sql=msg_doc.get("sql"),
            results=msg_doc.get("results"),
            result_count=msg_doc.get("result_count") or msg_doc.get("resultCount"),
            error=msg_doc.get("error"),
            metadata=msg_doc.get("metadata")
        ))

    # Convert metadata
    metadata_doc = doc.get("metadata", {})
    metadata = ConversationMetadata(
        message_count=metadata_doc.get("messageCount", metadata_doc.get("message_count", 0)),
        last_activity=metadata_doc.get("lastActivity", metadata_doc.get("last_activity", datetime.now(timezone.utc))),
        starred=metadata_doc.get("starred", False),
        tags=metadata_doc.get("tags", [])
    )

    return Conversation(
        conversation_id=doc.get("conversationId", doc.get("conversation_id", "")),
        user_id=doc.get("userId", doc.get("user_id", "default")),
        title=doc.get("title", "New Conversation"),
        project_id=doc.get("projectId", doc.get("project_id")),
        messages=messages,
        created_at=doc.get("createdAt", doc.get("created_at", datetime.now(timezone.utc))),
        updated_at=doc.get("updatedAt", doc.get("updated_at", datetime.now(timezone.utc))),
        metadata=metadata
    )


@router.post("", response_model=CreateConversationResponse)
async def create_conversation(
    request: CreateConversationRequest = CreateConversationRequest(),
    db: MongoDBClient = Depends(get_mongodb_client)
):
    """Create a new conversation."""
    try:
        logger.info(f"Creating conversation for user: {request.user_id}")

        # Generate conversation ID if not provided
        conversation_id = request.conversation_id or f"conv-{uuid.uuid4()}"

        # Create conversation using async mongodb_client
        conversation = await db.create_conversation(
            conversation_id=conversation_id,
            user_id=request.user_id
        )

        # Update title if provided
        if request.title and request.title != "New Conversation":
            await db.update_conversation(conversation_id, {"title": request.title})

        # Update project_id if provided
        if request.project_id:
            await db.update_conversation(conversation_id, {"projectId": request.project_id})

        return CreateConversationResponse(
            conversation_id=conversation_id,
            created_at=conversation.get("createdAt", datetime.now(timezone.utc))
        )
    except Exception as e:
        logger.error(f"Failed to create conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    user_id: str = Query(default="default", description="User ID"),
    limit: int = Query(default=50, le=100, description="Maximum number of conversations to return"),
    skip: int = Query(default=0, ge=0, description="Number of conversations to skip"),
    db: MongoDBClient = Depends(get_mongodb_client)
):
    """List conversations for a user."""
    try:
        logger.info(f"Listing conversations for user: {user_id}")

        # Get conversations using async mongodb_client
        conversation_docs = await db.list_conversations(user_id, limit, skip)

        # Convert to Conversation models
        conversations = [_doc_to_conversation(doc) for doc in conversation_docs]

        # Get total count
        total = len(conversations)  # For now, use returned count

        return ConversationListResponse(
            conversations=conversations,
            total=total,
            limit=limit,
            skip=skip
        )
    except Exception as e:
        logger.error(f"Failed to list conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{conversation_id}", response_model=Conversation)
async def get_conversation(
    conversation_id: str,
    db: MongoDBClient = Depends(get_mongodb_client)
):
    """Get a specific conversation by ID."""
    try:
        logger.info(f"Getting conversation: {conversation_id}")

        # Get conversation using async mongodb_client
        doc = await db.get_conversation(conversation_id)

        if not doc:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")

        conversation = _doc_to_conversation(doc)
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{conversation_id}/messages")
async def add_message_to_conversation(
    conversation_id: str,
    request: AddMessageRequest,
    db: MongoDBClient = Depends(get_mongodb_client)
):
    """Add a message to a conversation."""
    try:
        logger.info(f"Adding message to conversation: {conversation_id}")

        # Prepare message document (camelCase for mongodb_client)
        message_doc = {
            "id": request.message.id or str(uuid.uuid4()),
            "type": request.message.type,
            "content": request.message.content,
            "timestamp": request.message.timestamp or datetime.now(timezone.utc),
            "sql": request.message.sql,
            "results": request.message.results,
            "resultCount": request.message.result_count,
            "error": request.message.error,
            "metadata": request.message.metadata
        }

        # Add message using async mongodb_client
        success = await db.add_message(conversation_id, message_doc)

        if not success:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")

        return {"success": True, "message": "Message added successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    request: UpdateConversationRequest,
    db: MongoDBClient = Depends(get_mongodb_client)
):
    """Update conversation metadata."""
    try:
        logger.info(f"Updating conversation: {conversation_id}")

        # Build update dict (camelCase for mongodb_client)
        updates = {}
        if request.title is not None:
            updates["title"] = request.title
        if request.project_id is not None:
            updates["projectId"] = request.project_id
        if request.starred is not None:
            updates["metadata.starred"] = request.starred
        if request.tags is not None:
            updates["metadata.tags"] = request.tags

        if not updates:
            return {"success": True, "message": "No updates provided"}

        # Update using async mongodb_client
        success = await db.update_conversation(conversation_id, updates)

        if not success:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")

        return {"success": True, "message": "Conversation updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: MongoDBClient = Depends(get_mongodb_client)
):
    """Delete a conversation."""
    try:
        logger.info(f"Deleting conversation: {conversation_id}")

        # Delete using async mongodb_client
        success = await db.delete_conversation(conversation_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")

        return {"success": True, "message": "Conversation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_conversations(
    request: SearchConversationsRequest,
    db: MongoDBClient = Depends(get_mongodb_client)
):
    """Search conversations by text."""
    try:
        logger.info(f"Searching conversations for user: {request.user_id}")

        # Search using async mongodb_client
        conversation_docs = await db.search_conversations(
            request.user_id,
            request.query,
            request.limit
        )

        # Convert to Conversation models
        conversations = [_doc_to_conversation(doc) for doc in conversation_docs]

        return {
            "conversations": conversations,
            "total": len(conversations),
            "query": request.query
        }
    except Exception as e:
        logger.error(f"Failed to search conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/user/{user_id}/all")
async def delete_all_user_conversations(
    user_id: str,
    db: MongoDBClient = Depends(get_mongodb_client)
):
    """Delete all conversations for a user."""
    try:
        logger.info(f"Deleting all conversations for user: {user_id}")

        # Get all user conversations first
        conversations = await db.list_conversations(user_id, limit=1000)

        # Delete each one
        deleted_count = 0
        for conv in conversations:
            conv_id = conv.get("conversationId", conv.get("conversation_id"))
            if conv_id:
                success = await db.delete_conversation(conv_id)
                if success:
                    deleted_count += 1

        return {
            "success": True,
            "message": f"Deleted {deleted_count} conversations",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"Failed to delete all conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))
