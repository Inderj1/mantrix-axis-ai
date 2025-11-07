"""Pydantic models for conversation management"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class Message(BaseModel):
    """Individual message in a conversation"""
    id: str = Field(..., description="Unique message ID")
    type: str = Field(..., description="Message type: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Assistant-specific fields
    sql: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None
    result_count: Optional[int] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ConversationMetadata(BaseModel):
    """Metadata for a conversation"""
    message_count: int = 0
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    starred: bool = False
    tags: List[str] = Field(default_factory=list)


class Conversation(BaseModel):
    """Complete conversation model"""
    model_config = ConfigDict(populate_by_name=True, by_alias=True)

    conversation_id: str = Field(..., alias="conversationId", serialization_alias="conversation_id")
    user_id: str = Field(default="default", alias="userId", serialization_alias="user_id")
    title: str = "New Conversation"
    project_id: Optional[str] = Field(None, alias="projectId", serialization_alias="project_id", description="Project ID this conversation belongs to")
    messages: List[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt", serialization_alias="created_at")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updatedAt", serialization_alias="updated_at")
    metadata: ConversationMetadata = Field(default_factory=ConversationMetadata)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation"""
    conversation_id: Optional[str] = None
    user_id: Optional[str] = "default"
    title: Optional[str] = "New Conversation"
    project_id: Optional[str] = None


class CreateConversationResponse(BaseModel):
    """Response after creating a conversation"""
    conversation_id: str
    created_at: datetime


class AddMessageRequest(BaseModel):
    """Request to add a message to a conversation"""
    message: Message


class UpdateConversationRequest(BaseModel):
    """Request to update conversation metadata"""
    title: Optional[str] = None
    project_id: Optional[str] = None
    starred: Optional[bool] = None
    tags: Optional[List[str]] = None


class ConversationListResponse(BaseModel):
    """Response for listing conversations"""
    conversations: List[Conversation]
    total: int
    limit: int
    skip: int


class SearchConversationsRequest(BaseModel):
    """Request to search conversations"""
    query: str
    user_id: Optional[str] = "default"
    limit: Optional[int] = 20