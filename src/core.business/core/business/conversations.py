# -*- coding: utf-8 -*-

"""

    Module :mod:`core.business.conversations`

    Channel-agnostic conversation handling: find/start a conversation,
    record messages, and move ownership between the assistant and the team.

"""

# ----------- START: Third Party Imports ---------- #
from sqlalchemy.orm import Session
# ----------- END: Third Party Imports ---------- #

# ----------- START: In-App Imports ---------- #
from core.db.models import Contact, Conversation, Message, Tenant, utcnow
from core.db.statements import stmt_query_contact, stmt_query_open_conversation
from core.utils.constants import ConversationStatus, Role
# ----------- END: In-App Imports ---------- #

__all__ = ["get_or_create_conversation", "add_message", "hand_off", "release_to_bot"]


def get_or_create_conversation(session: Session, tenant: Tenant, channel: str, external_id: str) -> Conversation:
    contact = session.scalar(stmt_query_contact(tenant.id, channel, external_id))
    if contact is None:
        contact = Contact(tenant_id=tenant.id, channel=channel, external_id=external_id)
        session.add(contact)
        session.flush()
    conversation = session.scalar(stmt_query_open_conversation(contact.id))
    if conversation is None:
        conversation = Conversation(tenant_id=tenant.id, contact_id=contact.id, status=ConversationStatus.BOT)
        session.add(conversation)
        session.flush()
    return conversation


def add_message(
    session: Session,
    conversation: Conversation,
    role: Role,
    content: str,
    *,
    tool_calls: list | None = None,
    flagged: list | None = None,
) -> Message:
    message = Message(role=role, content=content, tool_calls=tool_calls or [], flagged=flagged or [])
    conversation.messages.append(message)
    conversation.last_message_at = utcnow()
    session.flush()
    return message


def hand_off(session: Session, conversation: Conversation, reason: str) -> None:
    """A team member takes over; the assistant stops replying."""
    conversation.status = ConversationStatus.HUMAN
    conversation.handoff_reason = reason
    session.flush()


def release_to_bot(session: Session, conversation: Conversation) -> None:
    conversation.status = ConversationStatus.BOT
    conversation.handoff_reason = None
    session.flush()
