# -*- coding: utf-8 -*-

"""

    Module :mod:`core.business.leads`

    Create/update the lead attached to a conversation's contact.

"""

# ----------- START: Third Party Imports ---------- #
from sqlalchemy.orm import Session
# ----------- END: Third Party Imports ---------- #

# ----------- START: In-App Imports ---------- #
from core.db.models import Conversation, Lead
from core.db.statements import stmt_query_lead
from core.utils.constants import LEAD_STAGE_ORDER, LeadStage
# ----------- END: In-App Imports ---------- #

__all__ = ["LEAD_FIELDS", "upsert_lead", "advance_stage"]

LEAD_FIELDS = ("name", "phone", "interest", "budget", "timeline", "location")


def upsert_lead(session: Session, conversation: Conversation, details: dict, source: str) -> Lead:
    """Merge ``details`` into the lead. Empty values never erase what's already known."""
    lead = session.scalar(stmt_query_lead(conversation.contact_id))
    if lead is None:
        lead = Lead(
            tenant_id=conversation.tenant_id,
            contact_id=conversation.contact_id,
            conversation_id=conversation.id,
            source=source,
            stage=LeadStage.NEW,
        )
        session.add(lead)

    for field in LEAD_FIELDS:
        value = details.get(field)
        if value and str(value).strip():
            setattr(lead, field, str(value).strip())
    if notes := (details.get("notes") or "").strip():
        lead.notes = f"{lead.notes}\n{notes}" if lead.notes else notes

    advance_stage(lead, details.get("stage"))
    if lead.stage == LeadStage.NEW and lead.phone and lead.interest:
        lead.stage = LeadStage.QUALIFIED

    contact = conversation.contact
    contact.name = contact.name or lead.name
    contact.phone = contact.phone or lead.phone
    session.flush()
    return lead


def advance_stage(lead: Lead, stage: str | None) -> None:
    """Move the lead forward only; a lead never goes back a stage automatically."""
    if stage in LEAD_STAGE_ORDER and LEAD_STAGE_ORDER.index(stage) > LEAD_STAGE_ORDER.index(lead.stage):
        lead.stage = stage
