from typing import Dict, Any

from app.agents.base_agent import BaseAgent
from app.services.email_service import send_email

_TEMPLATES = {
    "screening_rejected": (
        "Thank you for applying for {job_title}. After reviewing your "
        "application, we won't be moving forward at this time. We "
        "appreciate your interest and encourage you to apply for future "
        "roles that match your background."
    ),
    "advance": (
        "Great news — you've cleared the initial review for {job_title}! "
        "Our scheduling agent will be in touch shortly with next steps."
    ),
    "hire": (
        "Congratulations! We'd like to move forward with an offer for "
        "{job_title}. A member of our team will reach out with details."
    ),
    "reject": (
        "Thank you for the time you invested throughout our process for "
        "{job_title}. We've decided to move forward with other candidates, "
        "but we were impressed by your background and encourage future "
        "applications."
    ),
}


class CommunicationAgent(BaseAgent):
    """Stage-aware candidate messaging. One method per lifecycle event keeps
    templates easy to find and edit independently of pipeline logic."""

    name = "communication_agent"

    def notify(self, candidate_email: str, event: str, job_title: str) -> Dict[str, Any]:
        template = _TEMPLATES.get(event, "Update on your application for {job_title}.")
        body = template.format(job_title=job_title)

        send_email(to=candidate_email or "candidate@example.com", subject=f"Update: {job_title}", body=body)

        result = {"event": event, "sent": True}
        self.trace(action="notify_candidate", event=event)
        return result

    def run(self, candidate_email: str, event: str, job_title: str) -> Dict[str, Any]:
        return self.notify(candidate_email, event, job_title)
