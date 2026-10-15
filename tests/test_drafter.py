"""
tests/test_drafter.py — Verify draft invariants: is_draft always True, sent always False.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["LLM_MODE"] = "mock"

from models import Language, ApprovalStatus
from agents.interviewer import run_interviewer
from agents.asset_discovery import run_asset_discovery
from agents.planner import run_planner
from agents.drafter import run_drafter

SAMPLE_CSV = os.path.join(os.path.dirname(__file__), "..", "sample_data", "sharma_bank_statement.csv")
SAMPLE_TXT = os.path.join(os.path.dirname(__file__), "..", "sample_data", "case_description.txt")


@pytest.fixture(scope="module")
def full_pipeline():
    with open(SAMPLE_TXT) as f:
        raw = f.read()
    profile = run_interviewer(raw, Language.ENGLISH)
    discovery = run_asset_discovery(SAMPLE_CSV, profile.case_id)
    # Approve all findings
    for f in discovery.findings:
        f.approval_status = ApprovalStatus.APPROVED
    plan = run_planner(profile, discovery)
    kits = run_drafter(profile, plan.tasks)
    return profile, discovery, plan, kits


def test_kits_produced(full_pipeline):
    _, _, _, kits = full_pipeline
    assert len(kits) > 0, "Drafter produced no claim kits"


def test_all_kits_are_draft(full_pipeline):
    """is_draft must always be True — invariant."""
    _, _, _, kits = full_pipeline
    for kit in kits:
        assert kit.is_draft is True, (
            f"Kit for {kit.institution} has is_draft=False — invariant violated"
        )


def test_no_kit_is_sent(full_pipeline):
    """sent must always be False — Saath never sends anything."""
    _, _, _, kits = full_pipeline
    for kit in kits:
        assert kit.sent is False, (
            f"Kit for {kit.institution} has sent=True — CRITICAL invariant violated"
        )


def test_draft_label_in_letter(full_pipeline):
    """Every letter must contain the DRAFT warning."""
    _, _, _, kits = full_pipeline
    for kit in kits:
        assert "DRAFT" in kit.letter_text.upper(), (
            f"Letter for {kit.institution} is missing DRAFT label"
        )


def test_checklist_not_empty(full_pipeline):
    """Every kit must have at least one checklist item."""
    _, _, _, kits = full_pipeline
    for kit in kits:
        assert len(kit.checklist.items) > 0, (
            f"Checklist for {kit.institution} is empty"
        )


def test_kits_default_pending(full_pipeline):
    """Newly generated kits must be PENDING approval."""
    _, _, _, kits = full_pipeline
    for kit in kits:
        assert kit.approval_status == ApprovalStatus.PENDING, (
            f"Kit for {kit.institution} has unexpected status: {kit.approval_status}"
        )
