"""
Lightweight bias-mitigation utilities.

Scope & honesty note (read this before relying on it for anything real):
This is a portfolio-grade illustration of the *pattern* used in fairness-
aware hiring pipelines — redact-before-score, then aggregate-level parity
monitoring — not a certified, legally-compliant fairness system. A real
deployment would need: validated NER for PII, legal review of protected
categories in each jurisdiction, audited fairness metrics (e.g. four-fifths
rule), and mandatory human sign-off on every rejection.
"""
import re
from typing import List, Tuple

# Patterns for common PII / demographic proxies found on resumes.
_PATTERNS = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"(\+?\d[\d\-\s()]{8,}\d)"),
    "age_or_dob": re.compile(r"\b(age[d]?\s*:?\s*\d{1,2}|\b(19|20)\d{2}\b\s*-\s*(19|20)\d{2})\b", re.I),
    "gender_pronoun": re.compile(r"\b(he/him|she/her|they/them|mr\.|mrs\.|ms\.)\b", re.I),
    "marital_status": re.compile(r"\b(married|single|divorced|widowed)\b", re.I),
    "nationality_hint": re.compile(r"\b(nationality|citizenship)\s*:\s*\w+", re.I),
}


def redact_pii(resume_text: str) -> Tuple[str, List[str]]:
    """
    Strip PII / demographic-proxy signals from resume text before it is
    scored, so the screening agent evaluates substance rather than identity.

    Returns (redacted_text, flags) where flags lists which categories were
    found and removed.
    """
    redacted = resume_text
    flags: List[str] = []

    for label, pattern in _PATTERNS.items():
        if pattern.search(redacted):
            flags.append(label)
            redacted = pattern.sub("[REDACTED]", redacted)

    return redacted, flags


def check_group_parity(pass_rates_by_group: dict, threshold: float = 0.8) -> str | None:
    """
    Aggregate-level fairness check (the "four-fifths rule" commonly used as
    a rule-of-thumb screen): if any group's pass rate is below `threshold`
    times the highest group's pass rate, flag it for human review.

    This must only ever be run on aggregated statistics across many
    candidates — never used to make or justify a per-candidate decision.
    """
    if not pass_rates_by_group or len(pass_rates_by_group) < 2:
        return None

    best = max(pass_rates_by_group.values())
    if best == 0:
        return None

    for group, rate in pass_rates_by_group.items():
        if rate / best < threshold:
            return (
                f"Pass rate for '{group}' ({rate:.0%}) is below the four-fifths "
                f"threshold relative to the highest-passing group ({best:.0%}). "
                f"Flagging for human fairness review — do not act on this "
                f"automatically."
            )
    return None
