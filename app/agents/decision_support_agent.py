import json
from typing import Dict, Any, Optional

from app.agents.base_agent import BaseAgent
from app.services.llm_client import chat


class DecisionSupportAgent(BaseAgent):
    """
    Aggregates scores from every prior stage into a single recommendation.
    Deliberately rule-based at the top level (weights are explicit and
    inspectable) with the LLM used only to write the human-readable
    rationale — the *decision* itself is not left to free-form LLM
    judgement, which keeps it auditable and consistent across candidates.
    """

    name = "decision_support_agent"

    WEIGHTS = {"screening": 0.35, "prescreen": 0.25, "assessment": 0.40}

    def run(
        self,
        candidate_id: int,
        screening_score: float,
        prescreen_signals: Optional[Dict[str, float]],
        assessment_score: Optional[float],
        bias_flags: list[str],
    ) -> Dict[str, Any]:
        prescreen_score = (
            (prescreen_signals.get("communication", 0) + prescreen_signals.get("role_motivation", 0)) / 2
            if prescreen_signals
            else 0.0
        )
        assessment_score = assessment_score or 0.0

        weighted = (
            self.WEIGHTS["screening"] * screening_score
            + self.WEIGHTS["prescreen"] * prescreen_score
            + self.WEIGHTS["assessment"] * assessment_score
        )

        if weighted >= 0.75:
            recommendation = "hire"
        elif weighted >= 0.55:
            recommendation = "advance"
        else:
            recommendation = "reject"

        raw = chat(
            system_prompt="Write a one-paragraph hiring rationale given component scores.",
            user_prompt=(
                f"screening={screening_score}, prescreen={prescreen_score}, "
                f"assessment={assessment_score}, weighted={weighted:.2f}, "
                f"recommendation={recommendation}"
            ),
            mock_key="decision_rationale",
        )
        rationale = json.loads(raw)["rationale"]

        bias_warning = (
            f"Note: bias-flag categories were redacted during screening: {', '.join(bias_flags)}."
            if bias_flags
            else None
        )

        result = {
            "recommendation": recommendation,
            "confidence": round(weighted, 4),
            "rationale": rationale,
            "bias_warning": bias_warning,
        }
        self.trace(action="make_decision", candidate_id=candidate_id, result=result)
        return result
