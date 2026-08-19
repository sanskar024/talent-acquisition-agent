"""
Thin wrapper around the chat-completion call so every agent goes through one
place. Uses Google Gemini (matches the resume's Gemini-API project
experience) instead of GPT-4/OpenAI.

When USE_MOCK_LLM=true (the default, so the project runs with zero API
keys) it returns deterministic, structured mock responses keyed off the
prompt content — good enough to demo the full pipeline end-to-end.

Flip USE_MOCK_LLM=false and set GEMINI_API_KEY to use real Gemini.
"""
import json
from app.config import settings


def chat(system_prompt: str, user_prompt: str, mock_key: str = "") -> str:
    if settings.use_mock_llm:
        return _mock_response(mock_key, user_prompt)

    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(
        model_name=settings.llm_model,
        system_instruction=system_prompt,
    )
    response = model.generate_content(user_prompt)
    return response.text


def _mock_response(mock_key: str, user_prompt: str) -> str:
    """Deterministic canned responses so the pipeline is fully runnable offline."""
    mocks = {
        "prescreen_questions": json.dumps([
            "Walk me through a project you're most proud of.",
            "Tell me about a time you disagreed with a technical decision.",
            "Why are you interested in this role?",
        ]),
        "prescreen_score": json.dumps({
            "communication": 0.8,
            "role_motivation": 0.75,
            "notes": "Clear communicator, gave concrete examples, motivation is credible.",
        }),
        "assessment_grade": json.dumps({
            "score": 0.78,
            "feedback": "Solid grasp of core concepts; minor gaps in edge-case handling.",
        }),
        "decision_rationale": json.dumps({
            "rationale": (
                "Strong technical alignment and consistent scores across "
                "screening, pre-screen, and assessment stages support "
                "advancing this candidate."
            )
        }),
    }
    return mocks.get(mock_key, json.dumps({"note": "mock response", "prompt_echo": user_prompt[:120]}))
