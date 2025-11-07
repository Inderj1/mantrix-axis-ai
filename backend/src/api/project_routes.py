"""
Project API Routes
Handles project management endpoints
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional
import time
import secrets
from datetime import datetime, timezone
from src.models.project import Project, ProjectCreate, ProjectUpdate, ProjectSummary
from src.db.mongodb_client import mongodb_client as mongo_client
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


def generate_project_id() -> str:
    """Generate a unique project ID"""
    timestamp = int(time.time())
    random_suffix = secrets.token_hex(4)
    return f"proj-{timestamp}-{random_suffix}"


@router.post("", response_model=Project)
async def create_project(
    user_id: str = Query(..., description="User ID"),
    project_data: ProjectCreate = Body(...)
):
    """Create a new project"""
    try:
        project_id = generate_project_id()

        project = Project(
            project_id=project_id,
            user_id=user_id,
            name=project_data.name,
            description=project_data.description,
            color=project_data.color or "#0a6ed1",
            icon=project_data.icon or "folder",
            conversation_count=0
        )

        # Insert into MongoDB
        result = await mongo_client.db.projects.insert_one(project.model_dump())

        if result.inserted_id:
            logger.info("Created new project", project_id=project_id, user_id=user_id, name=project.name)
            return project
        else:
            raise HTTPException(status_code=500, detail="Failed to create project")

    except Exception as e:
        logger.error("Error creating project", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error creating project: {str(e)}")


@router.get("", response_model=List[ProjectSummary])
async def get_projects(
    user_id: str = Query(..., description="User ID"),
    include_archived: bool = Query(False, description="Include archived projects"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
):
    """Get all projects for a user"""
    try:
        query = {"user_id": user_id}

        if not include_archived:
            query["is_archived"] = False

        projects = []
        async for project in mongo_client.db.projects.find(query).sort("updated_at", -1).skip(skip).limit(limit):
            project.pop("_id", None)
            projects.append(project)

        logger.info("Retrieved projects", user_id=user_id, count=len(projects))
        return [ProjectSummary(**project) for project in projects]

    except Exception as e:
        logger.error("Error retrieving projects", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error retrieving projects: {str(e)}")


@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str):
    """Get a specific project"""
    try:
        project = await mongo_client.db.projects.find_one({"project_id": project_id})

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        project.pop("_id", None)
        return Project(**project)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving project", error=str(e), project_id=project_id)
        raise HTTPException(status_code=500, detail=f"Error retrieving project: {str(e)}")


@router.put("/{project_id}", response_model=Project)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate
):
    """Update a project"""
    try:
        # Get existing project
        existing = await mongo_client.db.projects.find_one({"project_id": project_id})
        if not existing:
            raise HTTPException(status_code=404, detail="Project not found")

        # Build update dict
        update_dict = {}
        if project_data.name is not None:
            update_dict["name"] = project_data.name
        if project_data.description is not None:
            update_dict["description"] = project_data.description
        if project_data.color is not None:
            update_dict["color"] = project_data.color
        if project_data.icon is not None:
            update_dict["icon"] = project_data.icon
        if project_data.is_archived is not None:
            update_dict["is_archived"] = project_data.is_archived

        update_dict["updated_at"] = datetime.now(timezone.utc)

        # Update in MongoDB
        result = await mongo_client.db.projects.update_one(
            {"project_id": project_id},
            {"$set": update_dict}
        )

        if result.modified_count > 0:
            # Get updated project
            updated = await mongo_client.db.projects.find_one({"project_id": project_id})
            updated.pop("_id", None)
            logger.info("Updated project", project_id=project_id)
            return Project(**updated)
        else:
            # No changes made, return existing
            existing.pop("_id", None)
            return Project(**existing)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating project", error=str(e), project_id=project_id)
        raise HTTPException(status_code=500, detail=f"Error updating project: {str(e)}")


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete a project (and optionally its conversations)"""
    try:
        # Check if project exists
        project = await mongo_client.db.projects.find_one({"project_id": project_id})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Delete the project
        result = await mongo_client.db.projects.delete_one({"project_id": project_id})

        if result.deleted_count > 0:
            # Update conversations to remove project_id
            await mongo_client.db.conversations.update_many(
                {"project_id": project_id},
                {"$unset": {"project_id": ""}}
            )

            logger.info("Deleted project", project_id=project_id)
            return {"message": "Project deleted successfully", "project_id": project_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete project")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting project", error=str(e), project_id=project_id)
        raise HTTPException(status_code=500, detail=f"Error deleting project: {str(e)}")


@router.get("/{project_id}/conversations")
async def get_project_conversations(
    project_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """Get all conversations in a project"""
    try:
        conversations = []
        async for conv in mongo_client.db.conversations.find({"project_id": project_id}).sort("updated_at", -1).skip(skip).limit(limit):
            # Remove MongoDB _id field
            conv.pop("_id", None)
            conversations.append(conv)

        logger.info("Retrieved project conversations", project_id=project_id, count=len(conversations))
        return conversations

    except Exception as e:
        logger.error("Error retrieving project conversations", error=str(e), project_id=project_id)
        raise HTTPException(status_code=500, detail=f"Error retrieving conversations: {str(e)}")
