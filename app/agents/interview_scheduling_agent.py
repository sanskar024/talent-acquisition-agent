from typing import Dict, Any

from app.agents.base_agent import BaseAgent
from app.services.calendar_service import find_next_available_slot
from app.services.email_service import send_email


class InterviewSchedulingAgent(BaseAgent):
    """
    Coordinates calendars and sends the invite. Kept deliberately simple:
    finding-a-slot and sending-an-invite are separated into their own
    service calls so a reschedule flow (candidate declines -> find next
    slot -> re-send) is just calling `run` again.
    """

    name = "interview_scheduling_agent"

    def run(self, candidate_id: int, candidate_email: str, job_title: str) -> Dict[str, Any]:
        slot = find_next_available_slot(candidate_id)

        send_email(
            to=candidate_email or "candidate@example.com",
            subject=f"Interview scheduled: {job_title}",
            body=(
                f"Thanks for your interest in the {job_title} role. "
                f"We'd like to schedule your pre-screening interview for "
                f"{slot.strftime('%A, %B %d at %H:%M UTC')}. Reply to this "
                f"email if you need to reschedule."
            ),
        )

        result = {"scheduled_time": slot.isoformat(), "status": "scheduled"}
        self.trace(action="schedule_interview", candidate_id=candidate_id, result=result)
        return result
