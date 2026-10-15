"""
Saath — Pydantic models for all typed data structures.
Synthetic demo only. No real personal data.
"""
from __future__ import annotations
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class TaskStatus(str, Enum):
    BLOCKED = "Blocked"
    READY = "Ready"
    DONE = "Done"
    APPROVED = "Approved"
    REJECTED = "Rejected"

class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Language(str, Enum):
    ENGLISH = "English"
    HINDI = "Hindi"
    MARATHI = "Marathi"


# ──────────────────────────────────────────────
# Case Profile
# ──────────────────────────────────────────────

class CaseProfile(BaseModel):
    """Extracted profile from the interviewer agent."""
    case_id: str = Field(default="")
    deceased_name: str = Field(default="[Unknown]")
    deceased_dob: Optional[str] = None
    date_of_death: Optional[str] = None
    state: str = Field(default="Maharashtra")
    claimant_name: str = Field(default="[Claimant]")
    claimant_relationship: str = Field(default="[Relationship]")
    known_institutions: list[str] = Field(default_factory=list)
    nominee_known: Optional[bool] = None
    will_present: Optional[bool] = None
    missing_fields: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    language: Language = Language.ENGLISH
    raw_input: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ──────────────────────────────────────────────
# Asset Discovery
# ──────────────────────────────────────────────

class EvidenceRow(BaseModel):
    date: str
    description: str
    amount: float
    credit_debit: str  # "CR" | "DR"
    masked_ref: str = ""

class AssetFinding(BaseModel):
    """A possible hidden asset discovered from transaction analysis."""
    finding_id: str
    label: str              # e.g. "Possible Life Insurance Premium"
    asset_type: str         # e.g. "insurance", "sip", "epf", "salary", "fd", "loan"
    confidence: ConfidenceLevel
    evidence_rows: list[EvidenceRow]
    monthly_amount: Optional[float] = None
    annual_amount: Optional[float] = None
    institution_hint: str = ""
    confirm_via: str = ""   # official channel to verify
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    notes: str = ""

class DiscoveryResult(BaseModel):
    findings: list[AssetFinding] = Field(default_factory=list)
    could_not_tell: list[str] = Field(default_factory=list)
    rows_analysed: int = 0
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)


# ──────────────────────────────────────────────
# Task Plan
# ──────────────────────────────────────────────

class ProcedureSource(BaseModel):
    card_id: str
    title: str
    source_url: str
    verified: bool

class TaskItem(BaseModel):
    task_id: str
    title: str
    description: str
    institution: str
    status: TaskStatus = TaskStatus.READY
    depends_on: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    deadline_days: Optional[int] = None
    deadline_date: Optional[str] = None
    source: Optional[ProcedureSource] = None
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    priority: int = 5   # 1 = highest
    notes: str = ""

class TaskPlan(BaseModel):
    tasks: list[TaskItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ──────────────────────────────────────────────
# Claim Kit / Drafter
# ──────────────────────────────────────────────

class DocumentChecklist(BaseModel):
    institution: str
    items: list[str]
    optional_items: list[str] = Field(default_factory=list)

class ClaimKit(BaseModel):
    kit_id: str
    institution: str
    asset_type: str
    letter_filename: str
    letter_text: str        # editable draft text
    checklist: DocumentChecklist
    is_draft: bool = True   # ALWAYS true — never filed
    sent: bool = False      # ALWAYS false — never sent
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ──────────────────────────────────────────────
# Tracker
# ──────────────────────────────────────────────

class Reminder(BaseModel):
    reminder_id: str
    task_id: str
    title: str
    due_date: str
    follow_up_draft: str = ""
    exported_ics: bool = False

class TrackerState(BaseModel):
    reminders: list[Reminder] = Field(default_factory=list)
    ics_filename: Optional[str] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ──────────────────────────────────────────────
# Whole Case State
# ──────────────────────────────────────────────

class CaseState(BaseModel):
    case_id: str
    profile: Optional[CaseProfile] = None
    discovery: Optional[DiscoveryResult] = None
    plan: Optional[TaskPlan] = None
    claim_kits: list[ClaimKit] = Field(default_factory=list)
    tracker: Optional[TrackerState] = None
    active_step: int = 1      # 1-6 UI step
    language: Language = Language.ENGLISH
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
