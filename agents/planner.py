"""
agents/planner.py — Build a task graph with dependencies from case profile + findings.
Uses procedure KB cards as the sole source of procedure content.
Outputs a TaskPlan with Kanban status (Blocked / Ready / Done).
"""
from __future__ import annotations
import logging
import uuid
from datetime import date, timedelta

from models import (
    CaseProfile, DiscoveryResult, TaskItem, TaskPlan, TaskStatus,
    ApprovalStatus, ProcedureSource
)
from utils.kb_loader import get_card, load_all_cards

logger = logging.getLogger(__name__)


def _source(card_id: str) -> ProcedureSource | None:
    card = get_card(card_id)
    if not card:
        return None
    return ProcedureSource(
        card_id=card["id"],
        title=card["title"],
        source_url=card.get("source_url", "TODO"),
        verified=card.get("verified", False),
    )


def _make_task(
    title: str,
    description: str,
    institution: str,
    card_id: str,
    depends_on: list[str] | None = None,
    required_docs: list[str] | None = None,
    deadline_days: int | None = None,
    priority: int = 5,
    legal_flag: bool = False,
) -> TaskItem:
    tid = f"T{uuid.uuid4().hex[:6].upper()}"
    card = get_card(card_id)
    docs = required_docs or (card.get("required_documents", []) if card else [])

    if legal_flag:
        description = (
            "⚠️ NEEDS A LAWYER OR LEGAL-AID CHECK — this task involves inheritance "
            "or succession rights that Saath cannot advise on.\n\n" + description
        )

    deadline_date = None
    if deadline_days is not None:
        deadline_date = (date.today() + timedelta(days=deadline_days)).isoformat()

    return TaskItem(
        task_id=tid,
        title=title,
        description=description,
        institution=institution,
        status=TaskStatus.READY if not depends_on else TaskStatus.BLOCKED,
        depends_on=depends_on or [],
        required_documents=docs,
        deadline_days=deadline_days,
        deadline_date=deadline_date,
        source=_source(card_id),
        approval_status=ApprovalStatus.PENDING,
        priority=priority,
    )


def run_planner(profile: CaseProfile, discovery: DiscoveryResult) -> TaskPlan:
    """Build the full task plan from profile + approved findings."""
    logger.info("Planner: building task graph for %s", profile.deceased_name)
    tasks: list[TaskItem] = []

    # ── Step 1: Death Certificate (always first, priority 1) ──────────
    dc_task = _make_task(
        title="Obtain Death Certificate",
        description=(
            "Register the death at the local Municipal Corporation or Gram Panchayat "
            "and obtain multiple certified copies of the death certificate. "
            "Every other institution will need one. Do this first."
        ),
        institution="Municipal Corporation / Gram Panchayat",
        card_id="death_certificate",
        deadline_days=7,
        priority=1,
    )
    tasks.append(dc_task)

    # ── Step 2: Unclaimed deposit search (early, independent) ──────────
    udgam_task = _make_task(
        title="Search for Unclaimed Deposits (UDGAM)",
        description=(
            "Use the RBI UDGAM portal to search for any unclaimed deposits "
            "linked to the deceased's name and date of birth."
        ),
        institution="RBI UDGAM Portal",
        card_id="unclaimed_deposit_search",
        priority=2,
    )
    tasks.append(udgam_task)

    # ── Step 3: Bank account claim ────────────────────────────────────
    bank_task = _make_task(
        title="Notify Bank and Initiate Account Settlement",
        description=(
            "Visit the home branch of the deceased to notify them of the death, "
            "freeze the account, and submit the claim application. "
            "As a joint account holder you may have a simpler process — confirm with the branch."
        ),
        institution=next(
            (i for i in profile.known_institutions if "bank" in i.lower() or "demo bank" in i.lower()),
            "Demo Bank"
        ),
        card_id="bank_account_claim",
        depends_on=[dc_task.task_id],
        priority=2,
    )
    tasks.append(bank_task)

    # ── Step 4: Assets from discovery ────────────────────────────────
    approved_findings = [
        f for f in discovery.findings
        if f.approval_status in (ApprovalStatus.APPROVED, ApprovalStatus.PENDING)
    ]

    for finding in approved_findings:
        if finding.asset_type == "insurance":
            ins_task = _make_task(
                title="Notify Life Insurance Company & File Claim",
                description=(
                    f"A possible insurance premium payment was identified "
                    f"(~₹{finding.monthly_amount:,.0f}/month). "
                    f"Notify the insurer and submit the claim intimation form. "
                    f"Verify: {finding.confirm_via}"
                ),
                institution=next(
                    (i for i in profile.known_institutions if "insurance" in i.lower()),
                    "Example Life Insurance Co."
                ),
                card_id="life_insurance_claim",
                depends_on=[dc_task.task_id],
                priority=2,
            )
            tasks.append(ins_task)

        elif finding.asset_type == "sip":
            mf_task = _make_task(
                title="Trace & Transmit Mutual Fund Units (Possible SIP)",
                description=(
                    f"A possible SIP debit was identified (~₹{finding.monthly_amount:,.0f}/month). "
                    f"Locate the AMC folio using the consolidated account statement (CAMS/KFintech). "
                    f"Submit a Transmission Request Form. Verify: {finding.confirm_via}"
                ),
                institution="Sample AMC / CAMS / KFintech",
                card_id="mutual_fund_transmission",
                depends_on=[dc_task.task_id],
                priority=3,
            )
            tasks.append(mf_task)

        elif finding.asset_type == "salary":
            epf_task = _make_task(
                title="Claim EPF / EPS Pension (Employer Salary Found)",
                description=(
                    f"Salary credits from Demo Tech Pvt Ltd were identified. "
                    f"The deceased likely had an EPF account. "
                    f"Obtain the UAN from salary slips and file Forms 20 and 10-D with EPFO. "
                    f"Verify: {finding.confirm_via}"
                ),
                institution="EPFO / Demo Tech Pvt Ltd HR",
                card_id="epf_pension_claim",
                depends_on=[dc_task.task_id],
                priority=3,
            )
            tasks.append(epf_task)

    # ── Step 5: Succession/legal heir (if no nominee or will unclear) ──
    if profile.will_present is False and profile.nominee_known is not True:
        legal_task = _make_task(
            title="Obtain Legal Heir Certificate or Succession Certificate",
            description=(
                "No will is present and nominee status is unclear. "
                "Some institutions may require a legal heir or succession certificate. "
                "Consult a lawyer or legal-aid clinic before proceeding."
            ),
            institution="Tehsildar Office / Civil Court",
            card_id="legal_heir_succession_certificate",
            depends_on=[dc_task.task_id],
            priority=4,
            legal_flag=True,
        )
        tasks.append(legal_task)

    logger.info("Planner: %d tasks created", len(tasks))
    return TaskPlan(tasks=tasks)
