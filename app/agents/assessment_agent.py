import json
from typing import Dict, Any, List

from app.agents.base_agent import BaseAgent
from app.services.llm_client import chat
from app.config import settings


class AssessmentAgent(BaseAgent):
    """
    Administers and grades a technical assessment. Question generation and
    grading are separate methods so the same rubric-based grader can be
    reused for take-home submissions that didn't come through this system.
    """

    name = "assessment_agent"

    def generate_assessment(self, required_skills: List[str]) -> List[str]:
        # In production this would pull from a question bank tagged by
        # skill, or generate+validate novel questions with an LLM.
        return [f"Describe a real project where you used {skill}." for skill in required_skills[:3]]

    def run(self, candidate_id: int, questions: List[str], answers: List[str]) -> Dict[str, Any]:
        per_question_scores = []
        for q, a in zip(questions, answers):
            raw = chat(
                system_prompt=(
                    "You grade a candidate's technical answer 0-1 against "
                    "the question, and give one sentence of feedback. "
                    "Respond as JSON: {score, feedback}."
                ),
                user_prompt=f"Question: {q}\nAnswer: {a}",
                mock_key="assessment_grade",
            )
            per_question_scores.append(json.loads(raw))

        overall_score = (
            sum(item["score"] for item in per_question_scores) / len(per_question_scores)
            if per_question_scores
            else 0.0
        )
        passed = overall_score >= settings.assessment_pass_threshold

        result = {
            "per_question_scores": per_question_scores,
            "overall_score": round(overall_score, 4),
            "passed": passed,
        }
        self.trace(action="grade_assessment", candidate_id=candidate_id, result=result)
        return result
