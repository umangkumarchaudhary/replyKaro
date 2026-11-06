# -*- coding: utf-8 -*-

"""

    Module :mod:`web.application.api.types`

    How database rows are shaped into API responses.

"""

# ----------- START: In-App Imports ---------- #
from core.db.models import Conversation, KBItem, Lead, Tenant
# ----------- END: In-App Imports ---------- #

__all__ = ["profile_out", "kb_item_out", "lead_out", "conversation_summary", "conversation_detail"]

PROFILE_FIELDS = ("about", "contact", "hours", "locations", "rules", "tone", "booking_type")
KB_FIELDS = ("id", "type", "title", "content", "price_min", "price_max", "meta", "active", "updated_at")
LEAD_FIELDS = ("id", "name", "phone", "interest", "budget", "timeline", "location", "notes", "stage",
               "source", "conversation_id", "created_at", "updated_at")


def profile_out(tenant: Tenant) -> dict:
    return {"slug": tenant.slug, "name": tenant.name, "vertical": tenant.vertical,
            **{f: getattr(tenant.profile, f) for f in PROFILE_FIELDS}}


def kb_item_out(item: KBItem) -> dict:
    return {f: getattr(item, f) for f in KB_FIELDS}


def lead_out(lead: Lead) -> dict:
    return {f: getattr(lead, f) for f in LEAD_FIELDS}


def conversation_summary(c: Conversation) -> dict:
    last = c.messages[-1] if c.messages else None
    return {
        "id": c.id,
        "status": c.status,
        "handoff_reason": c.handoff_reason,
        "contact": {"name": c.contact.name, "phone": c.contact.phone, "channel": c.contact.channel},
        "last_message": last.content if last else None,
        "last_message_at": c.last_message_at,
    }


def conversation_detail(c: Conversation) -> dict:
    return {
        "id": c.id,
        "status": c.status,
        "handoff_reason": c.handoff_reason,
        "messages": [
            {"role": m.role, "content": m.content, "tool_calls": m.tool_calls, "flagged": m.flagged,
             "created_at": m.created_at}
            for m in c.messages
        ],
    }
