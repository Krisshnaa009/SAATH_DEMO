"""
tests/test_asset_discovery.py
Assert: all 3 planted assets found, decoys never flagged certain, masking works.
"""
import os
import sys
import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["LLM_MODE"] = "mock"

from agents.asset_discovery import run_asset_discovery, _is_decoy
from models import ConfidenceLevel, ApprovalStatus

SAMPLE_CSV = os.path.join(os.path.dirname(__file__), "..", "sample_data", "sharma_bank_statement.csv")


@pytest.fixture
def discovery():
    return run_asset_discovery(SAMPLE_CSV, "test_case")


# ──────────────────────────────────────────────────────────────────────
# Core planted-asset tests
# ──────────────────────────────────────────────────────────────────────

def test_insurance_premium_found(discovery):
    """Planted insurance premium debit must be detected."""
    types = [f.asset_type for f in discovery.findings]
    assert "insurance" in types, (
        f"Insurance finding not found. Found types: {types}"
    )


def test_sip_found(discovery):
    """Planted SIP (mutual fund) debit must be detected."""
    types = [f.asset_type for f in discovery.findings]
    assert "sip" in types, (
        f"SIP finding not found. Found types: {types}"
    )


def test_salary_found(discovery):
    """Planted employer salary credit must be detected."""
    types = [f.asset_type for f in discovery.findings]
    assert "salary" in types, (
        f"Salary finding not found. Found types: {types}"
    )


def test_all_three_planted_assets_found(discovery):
    """All 3 planted assets must be found in one call."""
    types = {f.asset_type for f in discovery.findings}
    assert {"insurance", "sip", "salary"}.issubset(types), (
        f"Missing planted assets. Found: {types}"
    )


# ──────────────────────────────────────────────────────────────────────
# Decoy tests — must not be flagged as assets
# ──────────────────────────────────────────────────────────────────────

DECOY_DESCRIPTIONS = [
    "AUTOPAY CITY ELECTRICITY BOARD BILL",
    "UPI-FRESH MART GROCERY STORE",
    "AUTOPAY FITNESS FIRST CLUB MEMBERSHIP",
    "AUTOPAY STREAMFLIX SUBSCRIPTION",
]


@pytest.mark.parametrize("desc", DECOY_DESCRIPTIONS)
def test_decoy_is_identified(desc):
    """Decoy patterns must be recognised as decoys."""
    assert _is_decoy(desc), f"Expected decoy but not recognised: {desc}"


def test_decoys_not_in_findings(discovery):
    """Decoy descriptions must not appear in any finding's evidence rows."""
    decoy_keywords = ["electricity", "grocery", "club membership", "streamflix", "fitness"]
    for finding in discovery.findings:
        for ev in finding.evidence_rows:
            desc_lower = ev.description.lower()
            for kw in decoy_keywords:
                assert kw not in desc_lower, (
                    f"Decoy row appeared in finding '{finding.label}': {ev.description}"
                )


# ──────────────────────────────────────────────────────────────────────
# Confidence / certainty tests
# ──────────────────────────────────────────────────────────────────────

def test_no_finding_claims_certainty(discovery):
    """
    All finding labels must use 'possible', 'likely', or 'may'.
    No finding may claim definite existence.
    """
    forbidden_absolute = ["definitely", "confirmed", "entitled", "legally entitled"]
    for finding in discovery.findings:
        label_lower = finding.label.lower()
        for word in forbidden_absolute:
            assert word not in label_lower, (
                f"Finding label uses forbidden absolute word '{word}': {finding.label}"
            )


def test_could_not_tell_is_not_empty(discovery):
    """The 'could not tell' section must always have at least one entry."""
    assert len(discovery.could_not_tell) > 0, (
        "could_not_tell section is empty — agent must always include honesty notes"
    )


def test_findings_default_pending(discovery):
    """Newly discovered findings must default to PENDING approval."""
    for finding in discovery.findings:
        assert finding.approval_status == ApprovalStatus.PENDING, (
            f"Finding '{finding.label}' has non-PENDING status: {finding.approval_status}"
        )


def test_rows_analysed_count(discovery):
    """rows_analysed must be positive and roughly match the CSV size."""
    assert discovery.rows_analysed >= 100, (
        f"Expected at least 100 rows analysed, got {discovery.rows_analysed}"
    )
