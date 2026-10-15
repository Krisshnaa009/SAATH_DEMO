"""
utils/kb_loader.py — Load knowledge-base YAML procedure cards.
"""
import os
import yaml
from typing import Any

PROCEDURES_DIR = os.path.join(os.path.dirname(__file__), "..", "procedures")


def load_all_cards() -> list[dict[str, Any]]:
    cards = []
    for fname in sorted(os.listdir(PROCEDURES_DIR)):
        if fname.endswith(".yaml") or fname.endswith(".yml"):
            fpath = os.path.join(PROCEDURES_DIR, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                card = yaml.safe_load(f)
                if card:
                    cards.append(card)
    return cards


def get_card(card_id: str) -> dict[str, Any] | None:
    for card in load_all_cards():
        if card.get("id") == card_id:
            return card
    return None
