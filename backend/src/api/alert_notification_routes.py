"""
Alert Notification Routes - API for managing notification preferences and scheduled reports.

Endpoints:
- PUT /api/v1/notifications/preferences - Update notification preferences
- GET /api/v1/notifications/preferences - Get notification preferences
- POST /api/v1/notifications/test-email - Send test email
- POST /api/v1/reports/schedule - Create scheduled report
- GET /api/v1/reports/schedules - List scheduled reports
- DELETE /api/v1/reports/schedules/{id} - Delete scheduled report
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field, EmailStr
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, time
from enum import Enum
import uuid
import structlog

from src.db.mongodb_client import get_mongodb_client, MongoDBClient
from src.api.middleware.cognito_auth import get_current_user
from src.core.email_service import get_email_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["notifications"])


# Enums
class ReportFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class DeliveryDay(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class ReportFormat(str, Enum):
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"


# Request/Response Models
class QuietHoursConfig(BaseModel):
    """Configuration for quiet hours when no notifications are sent."""
    enabled: bool = False
    start: int = Field(default=22, ge=0, le=23, description="Start hour (0-23)")
    end: int = Field(default=7, ge=0, le=23, description="End hour (0-23)")
    timezone: str = Field(default="UTC")


class NotificationPreferences(BaseModel):
    """User notification preferences."""
    email: Optional[EmailStr] = None
    email_enabled: bool = True
    severity_filter: List[str] = Field(default=["warning", "critical"])
    quiet_hours: Optional[QuietHoursConfig] = None
    digest_mode: bool = Field(default=False, description="Batch notifications into digest")
    digest_frequency: str = Field(default="daily", description="daily or weekly")


class NotificationPreferencesResponse(BaseModel):
    """Response for notification preferences."""
    user_id: str
    email: Optional[str]
    email_enabled: bool
    severity_filter: List[str]
    quiet_hours: Optional[QuietHoursConfig]
    digest_mode: bool
    digest_frequency: str
    updated_at: datetime


class ScheduledReportCreate(BaseModel):
    """Request to create a scheduled report."""
    name: str = Field(..., min_length=1, max_length=200)
    dashboard_id: str
    frequency: ReportFrequency
    delivery_day: Optional[DeliveryDay] = None  # For weekly reports
    delivery_time: str = Field(default="09:00", description="HH:MM format")
    format: ReportFormat = ReportFormat.PDF
    recipients: List[EmailStr] = Field(default_factory=list)
    include_summary: bool = True
    active: bool = True


class ScheduledReportResponse(BaseModel):
    """Response for a scheduled report."""
    id: str
    name: str
    dashboard_id: str
    dashboard_name: Optional[str]
    frequency: str
    delivery_day: Optional[str]
    delivery_time: str
    format: str
    recipients: List[str]
    include_summary: bool
    active: bool
    last_sent: Optional[datetime]
    next_run: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class TestEmailRequest(BaseModel):
    """Request to send a test email."""
    email: EmailStr


# Endpoints

@router.get("/notifications/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """Get the current user's notification preferences."""
    user_id = current_user.get("sub", current_user.get("username", "anonymous"))

    prefs = await mongodb.notification_preferences.find_one({"user_id": user_id})

    if not prefs:
        # Return defaults
        return NotificationPreferencesResponse(
            user_id=user_id,
            email=current_user.get("email"),
            email_enabled=True,
            severity_filter=["warning", "critical"],
            quiet_hours=None,
            digest_mode=False,
            digest_frequency="daily",
            updated_at=datetime.now(timezone.utc)
        )

    return NotificationPreferencesResponse(
        user_id=user_id,
        email=prefs.get("email"),
        email_enabled=prefs.get("email_enabled", True),
        severity_filter=prefs.get("severity_filter", ["warning", "critical"]),
        quiet_hours=QuietHoursConfig(**prefs["quiet_hours"]) if prefs.get("quiet_hours") else None,
        digest_mode=prefs.get("digest_mode", False),
        digest_frequency=prefs.get("digest_frequency", "daily"),
        updated_at=prefs.get("updated_at", datetime.now(timezone.utc))
    )


@router.put("/notifications/preferences", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    preferences: NotificationPreferences,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """Update the current user's notification preferences."""
    user_id = current_user.get("sub", current_user.get("username", "anonymous"))
    now = datetime.now(timezone.utc)

    update_doc = {
        "user_id": user_id,
        "email": preferences.email,
        "email_enabled": preferences.email_enabled,
        "severity_filter": preferences.severity_filter,
        "quiet_hours": preferences.quiet_hours.dict() if preferences.quiet_hours else None,
        "digest_mode": preferences.digest_mode,
        "digest_frequency": preferences.digest_frequency,
        "updated_at": now
    }

    await mongodb.notification_preferences.update_one(
        {"user_id": user_id},
        {"$set": update_doc},
        upsert=True
    )

    logger.info("notification_preferences_updated", user_id=user_id)

    return NotificationPreferencesResponse(
        user_id=user_id,
        email=preferences.email,
        email_enabled=preferences.email_enabled,
        severity_filter=preferences.severity_filter,
        quiet_hours=preferences.quiet_hours,
        digest_mode=preferences.digest_mode,
        digest_frequency=preferences.digest_frequency,
        updated_at=now
    )


@router.post("/notifications/test-email")
async def send_test_email(
    request: TestEmailRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Send a test email to verify configuration."""
    email_service = get_email_service()

    if not email_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Email service is not configured. Contact your administrator."
        )

    result = await email_service.send_test_email(request.email)

    if not result.success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send test email: {result.error}"
        )

    logger.info(
        "test_email_sent",
        user_id=current_user.get("sub"),
        email=request.email
    )

    return {
        "success": True,
        "message": f"Test email sent to {request.email}",
        "message_id": result.message_id
    }


@router.post("/reports/schedule", response_model=ScheduledReportResponse)
async def create_scheduled_report(
    report: ScheduledReportCreate,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """Create a new scheduled report."""
    user_id = current_user.get("sub", current_user.get("username", "anonymous"))
    org_id = current_user.get("custom:organization_id", "default")
    now = datetime.now(timezone.utc)

    # Verify dashboard exists
    dashboard = await mongodb.dashboards.find_one({"_id": report.dashboard_id})
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    # Calculate next run
    next_run = _calculate_next_run(report.frequency, report.delivery_day, report.delivery_time)

    report_doc = {
        "_id": str(uuid.uuid4()),
        "name": report.name,
        "dashboard_id": report.dashboard_id,
        "user_id": user_id,
        "organization_id": org_id,
        "frequency": report.frequency.value,
        "delivery_day": report.delivery_day.value if report.delivery_day else None,
        "delivery_time": report.delivery_time,
        "format": report.format.value,
        "recipients": report.recipients,
        "include_summary": report.include_summary,
        "active": report.active,
        "last_sent": None,
        "next_run": next_run,
        "created_at": now,
        "updated_at": now
    }

    await mongodb.scheduled_reports.insert_one(report_doc)

    logger.info(
        "scheduled_report_created",
        report_id=report_doc["_id"],
        user_id=user_id,
        dashboard_id=report.dashboard_id
    )

    return ScheduledReportResponse(
        id=report_doc["_id"],
        name=report.name,
        dashboard_id=report.dashboard_id,
        dashboard_name=dashboard.get("name"),
        frequency=report.frequency.value,
        delivery_day=report.delivery_day.value if report.delivery_day else None,
        delivery_time=report.delivery_time,
        format=report.format.value,
        recipients=report.recipients,
        include_summary=report.include_summary,
        active=report.active,
        last_sent=None,
        next_run=next_run,
        created_at=now,
        updated_at=now
    )


@router.get("/reports/schedules", response_model=List[ScheduledReportResponse])
async def list_scheduled_reports(
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """List all scheduled reports for the current user."""
    user_id = current_user.get("sub", current_user.get("username", "anonymous"))

    reports = await mongodb.scheduled_reports.find(
        {"user_id": user_id}
    ).to_list(length=100)

    # Get dashboard names
    dashboard_ids = list(set(r.get("dashboard_id") for r in reports if r.get("dashboard_id")))
    dashboards = {}
    if dashboard_ids:
        dashboard_docs = await mongodb.dashboards.find(
            {"_id": {"$in": dashboard_ids}}
        ).to_list(length=100)
        dashboards = {d["_id"]: d.get("name") for d in dashboard_docs}

    result = []
    for r in reports:
        result.append(ScheduledReportResponse(
            id=r["_id"],
            name=r["name"],
            dashboard_id=r["dashboard_id"],
            dashboard_name=dashboards.get(r["dashboard_id"]),
            frequency=r["frequency"],
            delivery_day=r.get("delivery_day"),
            delivery_time=r["delivery_time"],
            format=r["format"],
            recipients=r.get("recipients", []),
            include_summary=r.get("include_summary", True),
            active=r.get("active", True),
            last_sent=r.get("last_sent"),
            next_run=r.get("next_run"),
            created_at=r["created_at"],
            updated_at=r["updated_at"]
        ))

    return result


@router.delete("/reports/schedules/{report_id}")
async def delete_scheduled_report(
    report_id: str,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """Delete a scheduled report."""
    user_id = current_user.get("sub", current_user.get("username", "anonymous"))

    result = await mongodb.scheduled_reports.delete_one({
        "_id": report_id,
        "user_id": user_id
    })

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Scheduled report not found")

    logger.info("scheduled_report_deleted", report_id=report_id, user_id=user_id)

    return {"message": "Scheduled report deleted", "id": report_id}


@router.patch("/reports/schedules/{report_id}/toggle")
async def toggle_scheduled_report(
    report_id: str,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """Toggle a scheduled report's active status."""
    user_id = current_user.get("sub", current_user.get("username", "anonymous"))

    report = await mongodb.scheduled_reports.find_one({
        "_id": report_id,
        "user_id": user_id
    })

    if not report:
        raise HTTPException(status_code=404, detail="Scheduled report not found")

    new_status = not report.get("active", True)

    await mongodb.scheduled_reports.update_one(
        {"_id": report_id},
        {"$set": {"active": new_status, "updated_at": datetime.now(timezone.utc)}}
    )

    return {"id": report_id, "active": new_status}


# Helper functions

def _calculate_next_run(
    frequency: ReportFrequency,
    delivery_day: Optional[DeliveryDay],
    delivery_time: str
) -> datetime:
    """Calculate the next run time for a scheduled report."""
    from datetime import timedelta

    now = datetime.now(timezone.utc)

    # Parse delivery time
    hour, minute = map(int, delivery_time.split(":"))

    if frequency == ReportFrequency.DAILY:
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)

    elif frequency == ReportFrequency.WEEKLY:
        day_map = {
            DeliveryDay.MONDAY: 0,
            DeliveryDay.TUESDAY: 1,
            DeliveryDay.WEDNESDAY: 2,
            DeliveryDay.THURSDAY: 3,
            DeliveryDay.FRIDAY: 4,
            DeliveryDay.SATURDAY: 5,
            DeliveryDay.SUNDAY: 6
        }
        target_day = day_map.get(delivery_day, 0)
        days_ahead = target_day - now.weekday()
        if days_ahead < 0:
            days_ahead += 7

        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        next_run += timedelta(days=days_ahead)

        if next_run <= now:
            next_run += timedelta(weeks=1)

    elif frequency == ReportFrequency.MONTHLY:
        next_run = now.replace(day=1, hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            # Move to next month
            if now.month == 12:
                next_run = next_run.replace(year=now.year + 1, month=1)
            else:
                next_run = next_run.replace(month=now.month + 1)

    else:
        next_run = now + timedelta(days=1)

    return next_run
