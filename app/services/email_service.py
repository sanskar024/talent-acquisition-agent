"""
Candidate messaging behind a simple interface. Swap `_send_mock` for a real
SMTP / SendGrid / SES call and nothing else needs to change.
"""
import logging
from app.config import settings

logger = logging.getLogger("talentflow.email")


def send_email(to: str, subject: str, body: str) -> bool:
    if settings.use_mock_email:
        return _send_mock(to, subject, body)

    # TODO: real implementation via SendGrid/SES/SMTP
    raise NotImplementedError("Real email integration not configured")


def _send_mock(to: str, subject: str, body: str) -> bool:
    logger.info("MOCK EMAIL -> %s | subject=%r | body=%r", to, subject, body[:200])
    return True
