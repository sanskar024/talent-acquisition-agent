from app.agents.resume_screening_agent import ResumeScreeningAgent
from app.services.bias_detection import redact_pii, check_group_parity


def test_skill_matching_finds_exact_and_missing_skills():
    agent = ResumeScreeningAgent()
    matched, missing = agent._match_skills(
        "5 years of Python and FastAPI experience, plus Docker.",
        ["python", "fastapi", "kubernetes"],
    )
    assert matched == ["python", "fastapi"]
    assert missing == ["kubernetes"]


def test_redact_pii_flags_and_strips_email_and_phone():
    text = "Contact me at jane@example.com or 555-123-4567. Married, age 29."
    redacted, flags = redact_pii(text)
    assert "email" in flags
    assert "phone" in flags
    assert "jane@example.com" not in redacted


def test_group_parity_flags_disproportionate_pass_rate():
    warning = check_group_parity({"group_a": 0.9, "group_b": 0.3})
    assert warning is not None
    assert "group_b" in warning


def test_group_parity_returns_none_when_balanced():
    warning = check_group_parity({"group_a": 0.7, "group_b": 0.68})
    assert warning is None


def test_full_screening_run_end_to_end():
    agent = ResumeScreeningAgent()
    result = agent.run(
        resume_text="Senior backend engineer. 6 years Python, FastAPI, PostgreSQL, distributed systems.",
        job_description="Looking for a backend engineer strong in Python, FastAPI, PostgreSQL.",
        required_skills=["python", "fastapi", "postgresql"],
    )
    assert result["skill_match_score"] == 1.0
    assert 0.0 <= result["overall_score"] <= 1.0
    assert result["passed"] is True
