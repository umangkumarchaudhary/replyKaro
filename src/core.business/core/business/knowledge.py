# -*- coding: utf-8 -*-

"""

    Module :mod:`core.business.knowledge`

    A business's knowledge base: listing, search and formatting.
    Search is keyword-based for now; pgvector RAG replaces ``search`` later
    without changing its callers.

"""

# ----------- START: Third Party Imports ---------- #
from sqlalchemy.orm import Session
# ----------- END: Third Party Imports ---------- #

# ----------- START: In-App Imports ---------- #
from core.db.models import KBItem
from core.db.statements import stmt_list_kb_items
from core.utils.money import extract_prices, format_price
from core.utils.text import tokens
# ----------- END: In-App Imports ---------- #

__all__ = ["list_items", "search", "item_to_text", "known_prices"]


def list_items(session: Session, tenant_id: int) -> list[KBItem]:
    return list(session.scalars(stmt_list_kb_items(tenant_id)))


def search(session: Session, tenant_id: int, query: str, limit: int = 5) -> list[KBItem]:
    """Best keyword matches; a hit in the title counts 3× a hit in the body."""
    wanted = tokens(query)
    if not wanted:
        return []
    scored = []
    for item in list_items(session, tenant_id):
        score = 3 * len(wanted & tokens(item.title)) + len(wanted & tokens(item.content))
        if score:
            scored.append((score, item.id, item))
    scored.sort(key=lambda s: (-s[0], s[1]))
    return [item for _, _, item in scored[:limit]]


def item_to_text(item: KBItem) -> str:
    parts = [f"[{item.type}] {item.title}"]
    if item.price_min is not None:
        price = format_price(item.price_min)
        if item.price_max and item.price_max != item.price_min:
            price += f" – {format_price(item.price_max)}"
        parts.append(f"Price: {price}")
    if item.content:
        parts.append(item.content)
    return " | ".join(parts)


def known_prices(items: list[KBItem]) -> set[int]:
    """Every rupee amount the knowledge base mentions (fields and text)."""
    known: set[int] = set()
    for item in items:
        known.update(round(p) for p in (item.price_min, item.price_max) if p is not None)
        known.update(extract_prices(item.title))
        known.update(extract_prices(item.content))
    return known
