# -*- coding: utf-8 -*-

"""

    Module :mod:`core.ai.agent`

    The sales-assistant loop: customer message in → reply out, with leads saved,
    hand-offs applied and every AI call's cost logged.

"""

# ----------- START: Native Imports ---------- #
from dataclasses import dataclass, field
# ----------- END: Native Imports ---------- #

# ----------- START: Third Party Imports ---------- #
import anthropic
from loguru import logger
from sqlalchemy.orm import Session
# ----------- END: Third Party Imports ---------- #

# ----------- START: In-App Imports ---------- #
from core.ai.client import AINotConfiguredError, LLMClient, usage_cost
from core.ai.guardrails import check_reply
from core.ai.prompt import build_context, build_system
from core.ai.tools import TOOLS, ToolContext, run_tool
from core.business.conversations import add_message, get_or_create_conversation, hand_off
from core.business.knowledge import list_items
from core.db.models import Conversation, Message, Tenant, UsageEvent
from core.db.statements import stmt_query_lead
from core.utils.config import Settings, get_settings
from core.utils.constants import ConversationStatus, Role
# ----------- END: In-App Imports ---------- #

__all__ = ["TurnResult", "handle_message", "build_history", "FALLBACK_REPLY", "HANDOFF_REPLY"]

FALLBACK_REPLY = "Thanks for your message! Our team will get back to you shortly. 🙏"
HANDOFF_REPLY = "I've passed this to our team. Someone will reply to you shortly. 🙏"


@dataclass
class TurnResult:
    reply: str | None  # None when a team member owns the conversation
    conversation_id: int
    status: str
    tool_calls: list = field(default_factory=list)
    flagged: list = field(default_factory=list)
    cost_usd: float = 0.0


def build_history(messages: list[Message], limit: int) -> list[dict]:
    """Chat history as plain-text turns. Same text every time → prompt-cache hits."""
    history: list[dict] = []
    for m in messages[-limit:]:
        role = "user" if m.role == Role.CUSTOMER else "assistant"
        text = f"[Team member]: {m.content}" if m.role == Role.HUMAN else m.content
        if history and history[-1]["role"] == role:
            history[-1]["content"] += "\n" + text
        else:
            history.append({"role": role, "content": text})
    while history and history[0]["role"] != "user":
        history.pop(0)
    return history


def _log_usage(session: Session, conversation: Conversation, model: str, usage) -> float:
    tokens, cost = usage_cost(model, usage)
    session.add(UsageEvent(tenant_id=conversation.tenant_id, conversation_id=conversation.id,
                           model=model, cost_usd=cost, **tokens))
    return cost


def handle_message(
    session: Session,
    tenant: Tenant,
    channel: str,
    external_id: str,
    text: str,
    *,
    client: LLMClient,
    settings: Settings | None = None,
) -> TurnResult:
    """Process one customer message from any channel and return the assistant's reply."""
    settings = settings or get_settings()
    conversation = get_or_create_conversation(session, tenant, channel, external_id)
    add_message(session, conversation, Role.CUSTOMER, text)

    if conversation.status == ConversationStatus.HUMAN:  # a team member owns this chat
        session.commit()
        return TurnResult(reply=None, conversation_id=conversation.id, status=conversation.status)

    items = list_items(session, tenant.id)
    lead = session.scalar(stmt_query_lead(conversation.contact_id))
    system = [
        {"type": "text", "text": build_system(tenant, items, channel), "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": build_context(tenant, lead)},
    ]
    messages = build_history(conversation.messages, settings.history_limit)
    ctx = ToolContext(session=session, conversation=conversation, channel=channel)
    tool_log: list[dict] = []
    cost = 0.0
    reply: str | None = None

    for _ in range(settings.max_tool_rounds):
        try:
            response = client.create(
                model=settings.chat_model,
                max_tokens=settings.max_tokens,
                system=system,
                tools=TOOLS,
                messages=messages,
                output_config={"effort": settings.chat_effort},
            )
        except AINotConfiguredError as e:
            logger.critical("{}", e)
            break
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as e:
            logger.critical("Claude API key missing or invalid: {}", e)
            break
        except anthropic.BadRequestError as e:
            logger.error("Claude rejected the request (conversation {}): {}", conversation.id, e.message)
            break
        except anthropic.AnthropicError as e:  # rate limit, overload, network (SDK already retried), no credentials
            logger.warning("Claude unavailable (conversation {}): {!r}", conversation.id, e)
            break
        cost += _log_usage(session, conversation, settings.chat_model, response.usage)

        if response.stop_reason == "refusal":
            hand_off(session, conversation, "Assistant declined to answer")
            break

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if response.stop_reason != "tool_use" or not tool_uses:
            reply = "\n".join(b.text.strip() for b in response.content if b.type == "text" and b.text.strip())
            break

        # Send the assistant's content back unchanged (incl. thinking blocks), then all results in one message.
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for call in tool_uses:
            try:
                output = run_tool(ctx, call.name, call.input)
                results.append({"type": "tool_result", "tool_use_id": call.id, "content": output})
            except Exception as e:  # a failing tool must never break the chat
                logger.exception("Tool {} failed", call.name)
                results.append({"type": "tool_result", "tool_use_id": call.id, "content": f"Error: {e}",
                                "is_error": True})
            tool_log.append({"name": call.name, "input": call.input})
        messages.append({"role": "user", "content": results})

    if not reply:
        reply = HANDOFF_REPLY if conversation.status == ConversationStatus.HUMAN else FALLBACK_REPLY

    flagged = check_reply(reply, items + ctx.looked_up)
    if flagged:
        logger.warning("Conversation {}: reply flagged {}", conversation.id, flagged)
    add_message(session, conversation, Role.BOT, reply, tool_calls=tool_log, flagged=flagged)
    session.commit()
    return TurnResult(reply=reply, conversation_id=conversation.id, status=conversation.status,
                      tool_calls=tool_log, flagged=flagged, cost_usd=cost)
