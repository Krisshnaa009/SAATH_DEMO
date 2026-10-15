"""
tests/test_masking.py — Verify masking rules work correctly.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.masking import mask_all, mask_aadhaar, mask_pan, mask_phone, mask_account


class TestAadhaarMasking:
    def test_12_digit_aadhaar(self):
        result = mask_all("Aadhaar: 1234 5678 9012")
        assert "1234 5678" not in result
        assert "9012" in result   # last 4 preserved

    def test_compact_aadhaar(self):
        result = mask_all("ID: 123456789012")
        assert "12345678" not in result
        assert "9012" in result


class TestPANMasking:
    def test_pan_format(self):
        result = mask_all("PAN: ABCDE1234F")
        assert "ABCDE" not in result
        assert "1234F" in result  # last 5 preserved

    def test_pan_in_sentence(self):
        result = mask_all("His PAN card number is XYZPQ9876K and he filed taxes.")
        assert "XYZPQ" not in result


class TestPhoneMasking:
    def test_indian_phone(self):
        result = mask_all("+91-9876543210")
        assert "987654" not in result
        assert "3210" in result

    def test_phone_in_text(self):
        result = mask_all("Please call 9876543210 for assistance.")
        assert "98765" not in result


class TestAccountMasking:
    def test_account_number(self):
        result = mask_all("Account 123456789012 is active")
        assert "12345678" not in result
        assert "9012" in result

    def test_short_number_not_over_masked(self):
        # A 3-digit number should NOT be masked
        result = mask_all("You owe ₹500 today")
        assert "500" in result


class TestNoFalsePositives:
    def test_year_not_masked(self):
        result = mask_all("He was born in 1958 and died in 2025.")
        assert "1958" in result
        assert "2025" in result

    def test_currency_amount_not_masked(self):
        result = mask_all("The balance is ₹67500.")
        assert "67500" in result

    def test_regular_text_unchanged(self):
        text = "Please contact the bank branch."
        result = mask_all(text)
        assert result == text
