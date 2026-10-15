"""
llm_provider.py — Thin provider interface for LLM calls.
LLM_MODE=mock  → returns deterministic fixture JSON (no key needed)
LLM_MODE=live  → calls Gemini via google-genai SDK
"""
from __future__ import annotations
import json
import logging
import os
import time
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

LLM_MODE = os.environ.get("LLM_MODE", "mock").lower()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

_client = None


def _get_client():
    global _client
    if _client is None and LLM_MODE == "live":
        try:
            from google import genai
            _client = genai.Client(api_key=GEMINI_API_KEY)
        except Exception as e:
            logger.error("Failed to initialise Gemini client: %s", e)
            raise
    return _client


def call_llm(
    prompt: str,
    system: str = "",
    fixture: dict | None = None,
    max_retries: int = 3,
    temperature: float = 0.2,
) -> dict[str, Any]:
    """
    Call the LLM and return validated JSON dict.
    In mock mode, returns the fixture immediately.
    In live mode, calls Gemini with retry on invalid JSON.
    """
    if LLM_MODE == "mock":
        logger.debug("LLM mock mode — returning fixture")
        return fixture or {}

    client = _get_client()
    full_prompt = f"{system}\n\n{prompt}" if system else prompt

    for attempt in range(1, max_retries + 1):
        try:
            from google.genai import types
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    response_mime_type="application/json",
                ),
            )
            text = response.text.strip()
            # Strip markdown fences if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            result = json.loads(text)
            return result
        except json.JSONDecodeError as e:
            logger.warning("Attempt %d/%d: invalid JSON from LLM: %s", attempt, max_retries, e)
            if attempt == max_retries:
                raise ValueError(f"LLM returned invalid JSON after {max_retries} attempts") from e
            time.sleep(1)
        except Exception as e:
            logger.error("LLM call failed on attempt %d: %s", attempt, e)
            if attempt == max_retries:
                raise
            time.sleep(2)

    return {}
