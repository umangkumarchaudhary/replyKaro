# -*- coding: utf-8 -*-

"""

    Module :mod:`core.ai.guardrails`

    Checks on the assistant's reply before it's stored. Problems are flagged
    on the message so the owner can review them in the dashboard.

"""

# ----------- START: In-App Imports ---------- #
from core.business.knowledge import known_prices
from core.db.models import KBItem
from core.utils.money import extract_prices
# ----------- END: In-App Imports ---------- #

__all__ = ["check_reply", "unknown_prices"]


def unknown_prices(reply: str, known: set[int], tolerance: float = 0.01) -> list[int]:
    """Prices in the reply that don't match any known price (±1%)."""
    return [p for p in extract_prices(reply) if not any(abs(p - k) <= max(1, k * tolerance) for k in known)]


def check_reply(reply: str, items: list[KBItem]) -> list[dict]:
    flags = []
    if bad := unknown_prices(reply, known_prices(items)):
        flags.append({"type": "unknown_price", "values": bad})
    return flags
