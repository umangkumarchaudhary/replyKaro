# -*- coding: utf-8 -*-

"""

    Module :mod:`core.ai.prompt`

    Builds the system prompt from three layers:
      1. core rules        — prompt_templates/sales_assistant.txt (same for everyone)
      2. industry rules    — the business's vertical (core/business/verticals/*.toml)
      3. business details  — that business's profile + knowledge base

    The stable part is cached by Claude; the volatile part (date, what we know
    about this customer) is built separately so it doesn't break the cache.

"""

# ----------- START: Native Imports ---------- #
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo
# ----------- END: Native Imports ---------- #

# ----------- START: In-App Imports ---------- #
from core.business.knowledge import item_to_text
from core.business.verticals import get_vertical
from core.db.models import KBItem, Lead, Tenant
from core.utils.constants import KBType
# ----------- END: In-App Imports ---------- #

__all__ = ["FULL_CATALOG_LIMIT", "booking_type", "build_system", "build_context"]

FULL_CATALOG_LIMIT = 100  # above this many items, the model must use search_catalog
_TEMPLATES = Path(__file__).parent / "prompt_templates"


@lru_cache
def _template(name: str) -> str:
    return (_TEMPLATES / name).read_text(encoding="utf-8")


def booking_type(tenant: Tenant) -> str:
    return tenant.profile.booking_type or get_vertical(tenant.vertical).booking_type


def _bullets(title: str, lines) -> str:
    return f"## {title}\n" + "\n".join(f"- {line}" for line in lines)


def build_system(tenant: Tenant, items: list[KBItem], channel: str) -> str:
    profile = tenant.profile
    vertical = get_vertical(tenant.vertical)
    sections = [
        _template("sales_assistant.txt").format(
            name=tenant.name,
            channel=channel,
            booking_type=booking_type(tenant),
            tone=profile.tone,
            collect=", ".join(vertical.collect),
        )
    ]
    if vertical.rules:
        sections.append(_bullets(f"Rules for {vertical.label.lower()}", vertical.rules))
    if profile.about:
        sections.append(f"## About the business\n{profile.about.strip()}")
    if profile.contact:
        sections.append(_bullets("Contact", (f"{k}: {v}" for k, v in profile.contact.items())))
    if profile.hours:
        sections.append(_bullets("Timings", (f"{k}: {v}" for k, v in profile.hours.items())))
    if profile.locations:
        sections.append(_bullets("Locations", (f"{l['name']}: {l.get('address', '')}" for l in profile.locations)))
    if profile.rules:
        sections.append(_bullets("Owner's instructions", profile.rules))

    if len(items) <= FULL_CATALOG_LIMIT:
        for kb_type in KBType:
            lines = [item_to_text(i) for i in items if i.type == kb_type]
            if lines:
                sections.append(_bullets(f"{kb_type.title()}s", lines))
    else:
        sections.append(
            f"## Catalog\nThere are {len(items)} items. Always use search_catalog to look up "
            "products, prices and FAQs before answering."
        )
    return "\n\n".join(sections)


def build_context(tenant: Tenant, lead: Lead | None) -> str:
    now = datetime.now(ZoneInfo(tenant.timezone))
    lines = [f"Current date/time: {now:%A, %d %B %Y, %I:%M %p} ({tenant.timezone})"]
    if lead:
        fields = ("name", "phone", "interest", "budget", "timeline", "location", "stage")
        known = {f: getattr(lead, f) for f in fields if getattr(lead, f)}
        if known:
            lines.append("Already known about this customer: " + ", ".join(f"{k}={v}" for k, v in known.items()))
    return "\n".join(lines)
