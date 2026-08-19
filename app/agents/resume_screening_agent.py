import re
from typing import Dict, Any, List

from app.agents.base_agent import BaseAgent
from app.services.embeddings import cosine_similarity
from app.services.bias_detection import redact_pii
from app.config import settings


class ResumeScreeningAgent(BaseAgent):
    """
    Scores a resume against a job description using:
      1. Semantic similarity (embedding cosine similarity, resume vs JD)
      2. Explicit required-skill matching (keyword/phrase presence)
    combined into a weighted overall score. PII is redacted before either
    score is computed, so scoring is blind to name/age/gender/etc.
    """

    name = "resume_screening_agent"

    SIMILARITY_WEIGHT = 0.5
    SKILL_MATCH_WEIGHT = 0.5

    def run(self, resume_text: str, job_description: str, required_skills: List[str]) -> Dict[str, Any]:
        redacted_resume, bias_flags = redact_pii(resume_text)

        similarity_score = cosine_similarity(redacted_resume, job_description)
        matched, missing = self._match_skills(redacted_resume, required_skills)
        skill_match_score = len(matched) / len(required_skills) if required_skills else 1.0

        overall_score = (
            self.SIMILARITY_WEIGHT * similarity_score
            + self.SKILL_MATCH_WEIGHT * skill_match_score
        )
        passed = overall_score >= settings.resume_pass_threshold

        result = {
            "similarity_score": round(similarity_score, 4),
            "skill_match_score": round(skill_match_score, 4),
            "overall_score": round(overall_score, 4),
            "matched_skills": matched,
            "missing_skills": missing,
            "bias_flags": bias_flags,
            "passed": passed,
        }

        self.trace(action="screen_resume", result=result)
        return result

    @staticmethod
    def _match_skills(resume_text: str, required_skills: List[str]) -> tuple[List[str], List[str]]:
        text_lower = resume_text.lower()
        matched, missing = [], []
        for skill in required_skills:
            # simple but effective: word-boundary match, case-insensitive
            pattern = r"\b" + re.escape(skill.lower()) + r"\b"
            if re.search(pattern, text_lower):
                matched.append(skill)
            else:
                missing.append(skill)
        return matched, missing
