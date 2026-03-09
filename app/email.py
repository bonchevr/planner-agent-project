"""Transactional email helpers.

Uses stdlib smtplib (STARTTLS on port 587 by default) so no extra
dependencies are needed.  The send is dispatched as a FastAPI
BackgroundTask so it never blocks the HTTP response.

Configuration (all via env vars / fly secrets):
    SMTP_HOST       e.g. smtp.sendgrid.net
    SMTP_PORT       default 587
    SMTP_USER       e.g. apikey  (SendGrid) or your full email address
    SMTP_PASSWORD   your SMTP password / API key
    SMTP_FROM       e.g. "Planner Agent <noreply@yourdomain.com>"
"""

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from loguru import logger

from app.config import settings


def _is_configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_user and settings.smtp_password)


def send_password_reset_email(to_email: str, reset_url: str) -> None:
    """Send a password-reset email.  Designed to run in a background task."""
    if not _is_configured():
        # Graceful fallback: log the link so admins can retrieve it
        logger.warning(
            "SMTP not configured — falling back to log. "
            "[PASSWORD RESET] {} → {}",
            to_email,
            reset_url,
        )
        return

    subject = "Reset your Planner Agent password"
    text_body = (
        f"Hi,\n\n"
        f"Someone requested a password reset for your Planner Agent account.\n\n"
        f"Click the link below to choose a new password (expires in 1 hour):\n"
        f"{reset_url}\n\n"
        f"If you did not request this, you can safely ignore this email.\n"
    )
    html_body = f"""\
<html><body>
<p>Hi,</p>
<p>Someone requested a password reset for your <strong>Planner Agent</strong> account.</p>
<p><a href="{reset_url}" style="font-size:1.1em">Reset my password</a></p>
<p>This link expires in <strong>1 hour</strong>.<br>
If you did not request this you can safely ignore this email.</p>
</body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.sendmail(msg["From"], [to_email], msg.as_string())
        logger.info("[PASSWORD RESET EMAIL] sent to {}", to_email)
    except Exception:
        logger.exception("[PASSWORD RESET EMAIL] failed to send to {}", to_email)
