"""
Project Model
Represents a project that groups related conversations
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone


class Project(BaseModel):
    """Project model for grouping conversations"""
    project_id: str = Field(..., description="Unique project identifier")
    user_id: str = Field(..., description="User ID who owns the project")
    name: str = Field(..., description="Project name", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="Project description", max_length=500)
    color: Optional[str] = Field("#0a6ed1", description="Project color for UI")
    icon: Optional[str] = Field("folder", description="Project icon name")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")
    is_archived: bool = Field(default=False, description="Whether the project is archived")
    conversation_count: int = Field(default=0, description="Number of conversations in project")

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "proj-1762390846-abc123",
                "user_id": "user_123",
                "name": "Marketing Analytics",
                "description": "Analysis for Q4 marketing campaigns",
                "color": "#0a6ed1",
                "icon": "trending_up",
                "created_at": "2024-11-06T00:00:00Z",
                "updated_at": "2024-11-06T00:00:00Z",
                "is_archived": False,
                "conversation_count": 5
            }
        }


class ProjectCreate(BaseModel):
    """Request model for creating a project"""
    name: str = Field(..., description="Project name", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="Project description", max_length=500)
    color: Optional[str] = Field("#0a6ed1", description="Project color for UI")
    icon: Optional[str] = Field("folder", description="Project icon name")


class ProjectUpdate(BaseModel):
    """Request model for updating a project"""
    name: Optional[str] = Field(None, description="Project name", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="Project description", max_length=500)
    color: Optional[str] = Field(None, description="Project color for UI")
    icon: Optional[str] = Field(None, description="Project icon name")
    is_archived: Optional[bool] = Field(None, description="Whether the project is archived")


class ProjectSummary(BaseModel):
    """Summary model for project listing"""
    project_id: str
    name: str
    description: Optional[str]
    color: str
    icon: str
    conversation_count: int
    created_at: datetime
    updated_at: datetime
    is_archived: bool
