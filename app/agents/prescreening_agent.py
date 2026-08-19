import json
from typing import Dict, Any, List

from app.agents.base_agent import BaseAgent
from app.services.llm_client import chat


class PrescreeningAgent(BaseAgent):
    """
    Conducts the initial pre-screen as a text-based agentic conversation
    (chat transcript in, structured signals out) — the same shape as a
    RAG/chatbot conversation loop, just applied to interviewing instead of
    document Q&A. This keeps the agent runnable with just an LLM call, no
    telephony/audio integration required.

    To wire this up to a real voice/video interview, add a speech-to-text
    step upstream (e.g. Gemini's audio input, or any STT API) that produces
    the `transcript` string this agent already expects — the scoring logic
    below doesn't need to change.
    """

    name = "prescreening_agent"

    def generate_questions(self, job_title: str, job_description: str) -> List[str]:
        raw = chat(
            system_prompt="You generate 3 concise, role-relevant pre-screening interview questions.",
            user_prompt=f"Role: {job_title}\nDescription: {job_description}",
            mock_key="prescreen_questions",
        )
        return json.loads(raw)

    def run(self, candidate_id: int, transcript: str | None, job_title: str) -> Dict[str, Any]:
        # In the demo, a transcript is synthesized if the candidate hasn't
        # actually chatted yet (see orchestrator.py). In a live deployment
        # this would be the real chat/call transcript.
        transcript = transcript or (
            "I led the migration of our monolith to microservices, which cut "
            "deploy time from 40 minutes to under 5. I'm drawn to this role "
            "because of the scale of systems your team works on."
        )

        raw = chat(
            system_prompt=(
                "You evaluate a pre-screening interview transcript for "
                "communication clarity and role motivation, on a 0-1 scale. "
                "Respond as JSON: {communication, role_motivation, notes}."
            ),
            user_prompt=f"Role: {job_title}\nTranscript: {transcript}",
            mock_key="prescreen_score",
        )
        signals = json.loads(raw)

        result = {
            "transcript": transcript,
            "signals": signals,
            "status": "completed",
        }
        self.trace(action="prescreen_candidate", candidate_id=candidate_id, signals=signals)
        return result
