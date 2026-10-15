"""
agents/asset_discovery.py — Parse bank statement CSV/PDF and find possible hidden assets.

Rules engine + optional LLM refinement. All findings are labelled "possible" and
require user approval. Includes a "could not tell" section for honesty.
"""
from __future__ import annotations
import io
import logging
import re
import uuid
from collections import defaultdict

import pandas as pd

from models import (
    AssetFinding, ConfidenceLevel, DiscoveryResult, EvidenceRow, ApprovalStatus
)
from llm_provider import call_llm
from utils.masking import mask_all

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# Rules — keyword patterns that hint at asset categories
# ──────────────────────────────────────────────────────────────────────
RULES: list[dict] = [
    {
        "id": "insurance_premium",
        "label": "Possible Life / Health Insurance Premium",
        "asset_type": "insurance",
        "patterns": [r"INS(URANCE)?[\s_-]?(PREMIUM|POLICY|PREM)", r"LIC\b", r"LIFE\s*INS", r"IRDAI"],
        "cr_dr": "DR",
        "monthly": True,
        "confirm_via": "Contact the insurer directly or check the policy document for the insurer name.",
        "confidence": ConfidenceLevel.HIGH,
    },
    {
        "id": "sip",
        "label": "Possible Mutual Fund SIP",
        "asset_type": "sip",
        "patterns": [r"\bSIP\b", r"NACH.*SIP", r"NACH.*AMC", r"MUTUAL\s*FUND"],
        "cr_dr": "DR",
        "monthly": True,
        "confirm_via": "Check CAMS (camsonline.com) or KFintech (kfintech.com) using the deceased's PAN for consolidated account statement.",
        "confidence": ConfidenceLevel.HIGH,
    },
    {
        "id": "salary",
        "label": "Possible Employer Salary (EPF may exist)",
        "asset_type": "salary",
        "patterns": [r"SALARY", r"NEFT.*SALARY", r"PAY\s*CREDIT", r"PAYROLL"],
        "cr_dr": "CR",
        "monthly": True,
        "confirm_via": "Contact the employer's HR department and check EPFO portal (epfindia.gov.in) using the UAN.",
        "confidence": ConfidenceLevel.HIGH,
    },
    {
        "id": "epf",
        "label": "Possible EPF / PF Contribution",
        "asset_type": "epf",
        "patterns": [r"\bEPF\b", r"\bPF\b", r"PROVIDENT\s*FUND"],
        "cr_dr": "DR",
        "monthly": True,
        "confirm_via": "Check EPFO portal (epfindia.gov.in) with the UAN.",
        "confidence": ConfidenceLevel.HIGH,
    },
    {
        "id": "fd_interest",
        "label": "Possible Fixed Deposit Interest",
        "asset_type": "fd",
        "patterns": [r"FD\s*INT(EREST)?", r"FIXED\s*DEP", r"TDR\s*INT"],
        "cr_dr": "CR",
        "monthly": False,
        "confirm_via": "Check with the bank for all FD accounts linked to the deceased's account.",
        "confidence": ConfidenceLevel.MEDIUM,
    },
    {
        "id": "loan_emi",
        "label": "Possible Loan EMI (liability + possible credit-life insurance)",
        "asset_type": "loan",
        "patterns": [r"\bEMI\b", r"LOAN\s*EMI", r"HOME\s*LOAN", r"NACH.*LOAN"],
        "cr_dr": "DR",
        "monthly": True,
        "confirm_via": "Contact the lender to confirm balance and check if a credit-life insurance policy was attached.",
        "confidence": ConfidenceLevel.MEDIUM,
    },
]

# Decoy patterns — these should NOT be flagged as assets
DECOY_PATTERNS = [
    r"ELECTRICITY", r"WATER\s*BILL", r"GAS\s*BILL", r"GROCERY", r"SUPERMARKET",
    r"SWIGGY", r"ZOMATO", r"AMAZON", r"FLIPKART", r"OTT", r"NETFLIX", r"HOTSTAR",
    r"STREAMFLIX", r"SUBSCRIPTION",
    r"CLUB\s*MEMBERSHIP", r"FITNESS", r"GYM", r"PETROL", r"FUEL", r"MOBILE\s*RECHARGE",
    r"RECHARGE", r"DTH", r"BROADBAND",
]
_DECOY_RE = re.compile("|".join(DECOY_PATTERNS), re.IGNORECASE)


def _mask_row_ref(desc: str) -> str:
    """Mask any identifier-like substrings in a transaction description."""
    return mask_all(desc)


def _is_decoy(description: str) -> bool:
    return bool(_DECOY_RE.search(description))


def _match_rules(df: pd.DataFrame) -> list[AssetFinding]:
    findings: list[AssetFinding] = []

    for rule in RULES:
        # Use non-capturing groups to avoid pandas UserWarning on groups
        combined = "|".join(f"(?:{p})" for p in rule["patterns"])
        pattern_re = re.compile(combined, re.IGNORECASE)
        mask = df["Description"].str.contains(pattern_re, regex=True, na=False)
        if rule["cr_dr"]:
            mask &= df["CR/DR"].str.upper() == rule["cr_dr"]

        matched = df[mask].copy()
        if matched.empty:
            continue

        # Skip if all matched rows look like decoys
        non_decoy = matched[~matched["Description"].apply(_is_decoy)]
        if non_decoy.empty:
            continue

        evidence = [
            EvidenceRow(
                date=str(row["Date"]),
                description=_mask_row_ref(str(row["Description"])),
                amount=float(row["Amount"]),
                credit_debit=str(row["CR/DR"]),
            )
            for _, row in non_decoy.iterrows()
        ]

        # Infer monthly amount
        amounts = non_decoy["Amount"].tolist()
        monthly_amt = round(sum(amounts) / len(amounts), 2) if amounts else None

        # Downgrade confidence if only 1 occurrence
        confidence = rule["confidence"]
        if len(evidence) == 1:
            confidence = ConfidenceLevel.LOW

        findings.append(AssetFinding(
            finding_id=f"{rule['id']}_{uuid.uuid4().hex[:6]}",
            label=rule["label"],
            asset_type=rule["asset_type"],
            confidence=confidence,
            evidence_rows=evidence,
            monthly_amount=monthly_amt,
            annual_amount=round(monthly_amt * 12, 2) if monthly_amt else None,
            institution_hint="",
            confirm_via=rule["confirm_via"],
            approval_status=ApprovalStatus.PENDING,
        ))

    return findings


def _could_not_tell_section(df: pd.DataFrame, findings: list[AssetFinding]) -> list[str]:
    """Honest section about what couldn't be determined."""
    notes = [
        "Shares, demat holdings or bonds: not visible in bank statements — check with CDSL/NSDL or the broker.",
        "PPF or NSC: cannot be detected from transactions alone — verify with the bank or post office.",
        "Real estate / property: outside scope of statement analysis.",
        "Cash or physical valuables: outside scope of statement analysis.",
    ]
    # If salary found but EPF not seen, add a note
    salary_found = any(f.asset_type == "salary" for f in findings)
    epf_found = any(f.asset_type == "epf" for f in findings)
    if salary_found and not epf_found:
        notes.append(
            "EPF: Salary credits were found but no explicit EPF debit was visible. "
            "The employer may have deducted EPF directly. Verify at epfindia.gov.in."
        )
    return notes


def load_statement(file_source) -> pd.DataFrame:
    """
    Accept a file path string, BytesIO, or UploadedFile.
    Returns a normalised DataFrame with columns: Date, Description, Amount, CR/DR, Balance.
    """
    if isinstance(file_source, str):
        df = pd.read_csv(file_source)
    else:
        # Streamlit UploadedFile or BytesIO
        content = file_source.read() if hasattr(file_source, "read") else file_source
        df = pd.read_csv(io.BytesIO(content))

    # Normalise column names
    df.columns = [c.strip() for c in df.columns]
    required = {"Date", "Description", "Amount", "CR/DR"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
    df["Description"] = df["Description"].fillna("").astype(str)
    df["CR/DR"] = df["CR/DR"].fillna("").str.upper()
    return df


def run_asset_discovery(file_source, case_id: str = "") -> DiscoveryResult:
    """Main entry point for Asset Discovery agent."""
    logger.info("AssetDiscovery: loading statement for case %s", case_id)
    df = load_statement(file_source)
    logger.info("AssetDiscovery: %d rows loaded", len(df))

    findings = _match_rules(df)
    could_not_tell = _could_not_tell_section(df, findings)

    logger.info("AssetDiscovery: %d findings, %d could-not-tell notes", len(findings), len(could_not_tell))

    return DiscoveryResult(
        findings=findings,
        could_not_tell=could_not_tell,
        rows_analysed=len(df),
    )
