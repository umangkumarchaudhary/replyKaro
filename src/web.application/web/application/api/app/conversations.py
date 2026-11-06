# -*- coding: utf-8 -*-

"""

    Module :mod:`web.application.api.app.conversations`

    The owner's inbox: list chats, read one, reply as a team member, hand back to the assistant.

"""

# ----------- START: Third Party Imports ---------- #
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
# ----------- END: Third Party Imports ---------- #

# ----------- START: In-App Imports ---------- #
from core.business.conversations import add_message, hand_off, release_to_bot
from core.db.models import Conversation, Tenant
from core.db.statements import stmt_list_conversations
from core.utils.constants import Role
from web.application.api.inputs import HumanReplyIn
from web.application.api.types import conversation_detail, conversation_summary
from web.application.common import get_owned, get_session, get_tenant
# ----------- END: In-App Imports ---------- #

router = APIRouter(prefix="/api/{slug}/conversations", tags=["conversations"])


@router.get("")
def list_conversations(tenant: Tenant = Depends(get_tenant), session: Session = Depends(get_session)):
    return [conversation_summary(c) for c in session.scalars(stmt_list_conversations(tenant.id))]


@router.get("/{conversation_id}")
def get_conversation(conversation_id: int, tenant: Tenant = Depends(get_tenant),
                     session: Session = Depends(get_session)):
    return conversation_detail(get_owned(session, Conversation, conversation_id, tenant, "Conversation"))


@router.post("/{conversation_id}/reply")
def reply_as_team(conversation_id: int, body: HumanReplyIn, tenant: Tenant = Depends(get_tenant),
                  session: Session = Depends(get_session)):
    """A team member replies; this also takes the conversation over from the assistant."""
    conversation = get_owned(session, Conversation, conversation_id, tenant, "Conversation")
    hand_off(session, conversation, conversation.handoff_reason or "Team member took over")
    add_message(session, conversation, Role.HUMAN, body.text)
    session.commit()
    # Delivering the reply on Telegram/WhatsApp is wired in Phase 2 (channel adapters).
    return {"ok": True, "status": conversation.status}


@router.post("/{conversation_id}/release")
def release(conversation_id: int, tenant: Tenant = Depends(get_tenant), session: Session = Depends(get_session)):
    conversation = get_owned(session, Conversation, conversation_id, tenant, "Conversation")
    release_to_bot(session, conversation)
    session.commit()
    return {"ok": True, "status": conversation.status}
