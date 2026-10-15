"""
utils/masking.py — Mask sensitive identifiers before display or LLM calls.
Keeps last 4 digits for account numbers.
"""
import re

# Aadhaar-like: 12 digits (possibly spaced as 4-4-4)
_AADHAAR_RE = re.compile(r'\b(\d{4}[\s-]?\d{4}[\s-]?)(\d{4})\b')

# PAN-like: 5 letters, 4 digits, 1 letter  e.g. ABCDE1234F
_PAN_RE = re.compile(r'\b([A-Z]{5})([0-9]{4}[A-Z])\b')

# Account number: 9-18 digits standalone (not already a PAN/Aadhaar)
_ACCT_RE = re.compile(r'\b(\d{5,14})(\d{4})\b')

# Phone: Indian 10-digit (possibly prefixed with +91)
_PHONE_RE = re.compile(r'(\+91[\s-]?)(\d{6})(\d{4})\b')


def mask_aadhaar(text: str) -> str:
    return _AADHAAR_RE.sub(r'XXXX-XXXX-\2', text)

def mask_pan(text: str) -> str:
    return _PAN_RE.sub(r'XXXXX\2', text)

def mask_account(text: str) -> str:
    return _ACCT_RE.sub(r'XXXXXXXX\2', text)

def mask_phone(text: str) -> str:
    return _PHONE_RE.sub(r'\1XXXXXX\3', text)

def mask_all(text: str) -> str:
    """Apply all masking rules in order."""
    text = mask_aadhaar(text)
    text = mask_pan(text)
    text = mask_phone(text)
    text = mask_account(text)
    return text
