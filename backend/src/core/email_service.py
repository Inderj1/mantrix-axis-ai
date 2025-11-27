"""
Email Service - SMTP email sending for alerts and notifications.

Supports:
- Alert notifications (threshold triggers)
- Scheduled report delivery
- Dashboard sharing invitations
- Test emails
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
import structlog
from dataclasses import dataclass

from src.config import settings

logger = structlog.get_logger()


@dataclass
class EmailResult:
    """Result of an email send attempt."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class EmailService:
    """
    Email service for sending notifications via SMTP.

    Usage:
        email_service = EmailService()
        result = await email_service.send_alert_email(
            recipient="user@example.com",
            alert_name="Revenue Alert",
            alert_message="Revenue dropped below threshold",
            dashboard_url="https://app.mantrix.ai/dashboards/123"
        )
    """

    def __init__(self):
        self.enabled = settings.smtp_enabled
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.user = settings.smtp_user
        self.password = settings.smtp_password
        self.from_email = settings.smtp_from_email
        self.from_name = settings.smtp_from_name
        self.use_tls = settings.smtp_use_tls
        self.use_ssl = settings.smtp_use_ssl

    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return (
            self.enabled and
            self.host and
            self.user and
            self.password
        )

    async def send_email(
        self,
        to: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> EmailResult:
        """
        Send an email via SMTP.

        Args:
            to: Recipient email address
            subject: Email subject
            html_content: HTML body content
            text_content: Plain text fallback (auto-generated if not provided)
            cc: Carbon copy recipients
            bcc: Blind carbon copy recipients
            attachments: List of dicts with 'filename', 'content', 'content_type'

        Returns:
            EmailResult with success status and any error message
        """
        if not self.is_configured():
            logger.warning("email_service_not_configured")
            return EmailResult(
                success=False,
                error="Email service is not configured. Set SMTP_ENABLED=true and configure SMTP settings."
            )

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to

            if cc:
                msg["Cc"] = ", ".join(cc)

            # Add text content (plain text fallback)
            if text_content:
                text_part = MIMEText(text_content, "plain")
                msg.attach(text_part)

            # Add HTML content
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)

            # Add attachments
            if attachments:
                for attachment in attachments:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment["content"])
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={attachment['filename']}"
                    )
                    msg.attach(part)

            # Build recipient list
            recipients = [to]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)

            # Send email in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            message_id = await loop.run_in_executor(
                None,
                self._send_smtp,
                recipients,
                msg.as_string()
            )

            logger.info(
                "email_sent_successfully",
                to=to,
                subject=subject,
                message_id=message_id
            )

            return EmailResult(success=True, message_id=message_id)

        except Exception as e:
            logger.error(
                "email_send_failed",
                to=to,
                subject=subject,
                error=str(e)
            )
            return EmailResult(success=False, error=str(e))

    def _send_smtp(self, recipients: List[str], message: str) -> str:
        """Synchronous SMTP send (called in thread pool)."""
        context = ssl.create_default_context()

        if self.use_ssl:
            server = smtplib.SMTP_SSL(self.host, self.port, context=context)
        else:
            server = smtplib.SMTP(self.host, self.port)
            if self.use_tls:
                server.starttls(context=context)

        try:
            server.login(self.user, self.password)
            server.sendmail(self.from_email, recipients, message)
            return f"{datetime.utcnow().timestamp()}"
        finally:
            server.quit()

    async def send_alert_email(
        self,
        recipient: str,
        alert_name: str,
        alert_message: str,
        alert_data: Optional[Dict[str, Any]] = None,
        dashboard_url: Optional[str] = None,
        severity: str = "warning"
    ) -> EmailResult:
        """
        Send an alert notification email.

        Args:
            recipient: Email address
            alert_name: Name of the alert
            alert_message: Alert description/message
            alert_data: Optional data snapshot that triggered the alert
            dashboard_url: Link to the relevant dashboard
            severity: Alert severity (info, warning, critical)
        """
        severity_colors = {
            "info": "#3498db",
            "warning": "#f39c12",
            "critical": "#e74c3c"
        }
        severity_icons = {
            "info": "&#9432;",  # info circle
            "warning": "&#9888;",  # warning triangle
            "critical": "&#10071;"  # exclamation mark
        }

        color = severity_colors.get(severity, severity_colors["warning"])
        icon = severity_icons.get(severity, severity_icons["warning"])

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: {color}; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 8px 8px; }}
                .alert-name {{ font-size: 24px; margin-bottom: 10px; }}
                .alert-message {{ font-size: 16px; margin-bottom: 20px; }}
                .data-table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                .data-table th, .data-table td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                .data-table th {{ background-color: #f0f0f0; }}
                .button {{ display: inline-block; background-color: #3498db; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; margin-top: 15px; }}
                .footer {{ text-align: center; color: #888; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div style="font-size: 36px;">{icon}</div>
                    <div class="alert-name">{alert_name}</div>
                </div>
                <div class="content">
                    <p class="alert-message">{alert_message}</p>
        """

        # Add data table if provided
        if alert_data:
            html_content += """
                    <table class="data-table">
                        <thead>
                            <tr><th>Metric</th><th>Value</th></tr>
                        </thead>
                        <tbody>
            """
            for key, value in alert_data.items():
                html_content += f"<tr><td>{key}</td><td>{value}</td></tr>"
            html_content += """
                        </tbody>
                    </table>
            """

        # Add dashboard link
        if dashboard_url:
            html_content += f"""
                    <a href="{dashboard_url}" class="button">View Dashboard</a>
            """

        html_content += f"""
                </div>
                <div class="footer">
                    <p>This is an automated alert from Mantrix Axis AI.</p>
                    <p>To manage your alert preferences, visit your account settings.</p>
                </div>
            </div>
        </body>
        </html>
        """

        subject = f"[{severity.upper()}] {alert_name}"

        return await self.send_email(
            to=recipient,
            subject=subject,
            html_content=html_content,
            text_content=f"Alert: {alert_name}\n\n{alert_message}"
        )

    async def send_scheduled_report(
        self,
        recipient: str,
        report_name: str,
        report_format: str = "pdf",
        report_content: bytes = None,
        dashboard_url: Optional[str] = None
    ) -> EmailResult:
        """
        Send a scheduled report via email.

        Args:
            recipient: Email address
            report_name: Name of the report
            report_format: Format (pdf, excel, csv)
            report_content: Binary content of the report file
            dashboard_url: Link to view online
        """
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 8px 8px; }}
                .button {{ display: inline-block; background-color: #3498db; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; margin-top: 15px; }}
                .footer {{ text-align: center; color: #888; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div style="font-size: 36px;">&#128202;</div>
                    <h2 style="margin: 0;">Scheduled Report</h2>
                </div>
                <div class="content">
                    <h3>{report_name}</h3>
                    <p>Your scheduled report is ready. The {report_format.upper()} file is attached to this email.</p>
        """

        if dashboard_url:
            html_content += f"""
                    <p>You can also view the live dashboard:</p>
                    <a href="{dashboard_url}" class="button">View Dashboard</a>
            """

        html_content += """
                </div>
                <div class="footer">
                    <p>This is a scheduled report from Mantrix Axis AI.</p>
                    <p>To manage your report schedule, visit your account settings.</p>
                </div>
            </div>
        </body>
        </html>
        """

        attachments = []
        if report_content:
            attachments.append({
                "filename": f"{report_name}.{report_format}",
                "content": report_content,
                "content_type": f"application/{report_format}"
            })

        return await self.send_email(
            to=recipient,
            subject=f"Scheduled Report: {report_name}",
            html_content=html_content,
            text_content=f"Your scheduled report '{report_name}' is attached.",
            attachments=attachments
        )

    async def send_share_invitation(
        self,
        recipient: str,
        dashboard_name: str,
        shared_by: str,
        permission: str,
        dashboard_url: str,
        message: Optional[str] = None
    ) -> EmailResult:
        """
        Send a dashboard sharing invitation email.

        Args:
            recipient: Email of person being invited
            dashboard_name: Name of the shared dashboard
            shared_by: Name/email of person sharing
            permission: Permission level (view, edit, admin)
            dashboard_url: Link to the dashboard
            message: Optional personal message
        """
        permission_desc = {
            "view": "view",
            "edit": "view and edit",
            "admin": "view, edit, and manage"
        }.get(permission, "view")

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #9b59b6; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 8px 8px; }}
                .message-box {{ background-color: white; padding: 15px; border-left: 4px solid #9b59b6; margin: 15px 0; }}
                .button {{ display: inline-block; background-color: #9b59b6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; margin-top: 15px; }}
                .footer {{ text-align: center; color: #888; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div style="font-size: 36px;">&#128202;</div>
                    <h2 style="margin: 0;">Dashboard Shared With You</h2>
                </div>
                <div class="content">
                    <p><strong>{shared_by}</strong> has shared a dashboard with you.</p>
                    <h3 style="color: #9b59b6;">{dashboard_name}</h3>
                    <p>You have been granted <strong>{permission_desc}</strong> access.</p>
        """

        if message:
            html_content += f"""
                    <div class="message-box">
                        <p style="margin: 0; font-style: italic;">"{message}"</p>
                    </div>
            """

        html_content += f"""
                    <a href="{dashboard_url}" class="button">Open Dashboard</a>
                </div>
                <div class="footer">
                    <p>If you weren't expecting this invitation, you can safely ignore this email.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return await self.send_email(
            to=recipient,
            subject=f"{shared_by} shared a dashboard with you: {dashboard_name}",
            html_content=html_content,
            text_content=f"{shared_by} has shared '{dashboard_name}' with you. View it at: {dashboard_url}"
        )

    async def send_test_email(self, recipient: str) -> EmailResult:
        """Send a test email to verify configuration."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #27ae60; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
                .content { background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 8px 8px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div style="font-size: 36px;">&#10004;</div>
                    <h2 style="margin: 0;">Email Configuration Test</h2>
                </div>
                <div class="content">
                    <p>Congratulations! Your email configuration is working correctly.</p>
                    <p>You will now receive alert notifications and scheduled reports at this address.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return await self.send_email(
            to=recipient,
            subject="Mantrix Axis AI - Email Configuration Test",
            html_content=html_content,
            text_content="Your email configuration is working correctly!"
        )


# Singleton instance
_email_service_instance: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create the singleton email service instance."""
    global _email_service_instance
    if _email_service_instance is None:
        _email_service_instance = EmailService()
    return _email_service_instance
