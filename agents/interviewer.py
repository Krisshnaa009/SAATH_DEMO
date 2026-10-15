"""
agents/interviewer.py — Extract case profile from free-form text.
Uses LLM (mock or live) with structured JSON output + Pydantic validation.
"""
from __future__ import annotations
import logging
import uuid

from models import CaseProfile, Language
from llm_provider import call_llm
from utils.masking import mask_all

logger = logging.getLogger(__name__)

# ── Mock fixture ───────────────────────────────────────────────────────
_MOCK_PROFILE = {
    "deceased_name": "Mr. Ramesh Sharma",
    "deceased_dob": "1958-03-15",
    "date_of_death": "2025-09-20",
    "state": "Maharashtra",
    "claimant_name": "Mrs. Sunita Sharma",
    "claimant_relationship": "spouse",
    "known_institutions": [
        "Demo Bank – Shivaji Nagar Branch",
        "Example Life Insurance Co."
    ],
    "nominee_known": True,
    "will_present": False,
    "missing_fields": ["deceased_aadhaar", "insurance_policy_number"],
    "follow_up_questions": [
        "Do you have the EPF / UAN number of the deceased?",
        "Do you know the name of the mutual fund house for the SIP mentioned in his phone?",
        "Was the deceased's demat / broking account with a specific broker?"
    ],
    "language": "English"
}

_SYSTEM_PROMPT = """
You are Saath, a compassionate assistant helping an Indian family after a bereavement.
Extract the case profile from the text and return ONLY valid JSON with these fields:
{
  "deceased_name": str,
  "deceased_dob": str | null,       # ISO date YYYY-MM-DD
  "date_of_death": str | null,      # ISO date YYYY-MM-DD
  "state": str,                     # Indian state name
  "claimant_name": str,
  "claimant_relationship": str,
  "known_institutions": [str],
  "nominee_known": bool | null,
  "will_present": bool | null,
  "missing_fields": [str],          # field names that are missing or unclear
  "follow_up_questions": [str],     # 3-5 questions for missing info
  "language": "English" | "Hindi" | "Marathi"
}
Important: never guess legal heir rights or succession. Flag legal questions as out of scope.
Mask any real PAN, Aadhaar, or account numbers in output.
"""


def run_interviewer(raw_text: str, language: Language = Language.ENGLISH) -> CaseProfile:
    """Parse free-text and return a validated CaseProfile."""
    masked_input = mask_all(raw_text)
    logger.info("Interviewer: processing %d chars of input", len(masked_input))

    prompt = f"Language preference: {language.value}\n\nCase description:\n{masked_input}"

    result = call_llm(
        prompt=prompt,
        system=_SYSTEM_PROMPT,
        fixture=_MOCK_PROFILE,
    )

    # Merge with defaults and validate
    # Exclude 'language' and 'case_id' from the fixture spread to avoid duplicate kwarg
    excluded = {"language", "case_id", "raw_input"}
    extra = {k: v for k, v in result.items() if k in CaseProfile.model_fields and k not in excluded}
    profile = CaseProfile(
        case_id=str(uuid.uuid4())[:8],
        raw_input=masked_input,
        language=language,
        **extra,
    )
    logger.info("Interviewer: profile extracted for %s", profile.deceased_name)
    return profile
