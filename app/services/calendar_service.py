"""
Calendar integration behind a simple interface. Swap `_mock_next_slot` for a
real Google Calendar / Outlook API call and nothing else in the codebase
needs to change.
"""
from datetime import datetime, timedelta
from app.config import settings


def find_next_available_slot(candidate_id: int, interviewer_ids: list[int] | None = None) -> datetime:
    if settings.use_mock_calendar:
        return _mock_next_slot()

    # TODO: real implementation — call Google Calendar freebusy API for
    # each interviewer, intersect with candidate-provided availability,
    # return the earliest mutual slot.
    raise NotImplementedError("Real calendar integration not configured")


def _mock_next_slot() -> datetime:
    # Pretend the next available mutual slot is 3 business days out at 2pm.
    slot = datetime.utcnow() + timedelta(days=3)
    return slot.replace(hour=14, minute=0, second=0, microsecond=0)
