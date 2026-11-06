# -*- coding: utf-8 -*-

"""

    Module :mod:`core.ai.tools`

    Tool definitions the assistant can call, and a dispatcher that maps each
    call to ``core.business``. No business logic lives here.

"""

# ----------- START: Native Imports ---------- #
import json
from dataclasses import dataclass, field
# ----------- END: Native Imports ---------- #

# ----------- START: Third Party Imports ---------- #
from sqlalchemy.orm import Session
# ----------- END: Third Party Imports ---------- #

# ----------- START: In-App Imports ---------- #
from core.business.conversations import hand_off
from core.business.knowledge import item_to_text, search
from core.business.leads import upsert_lead
from core.db.models import Conversation, KBItem
from core.utils.constants import BOT_SETTABLE_STAGES
# ----------- END: In-App Imports ---------- #

__all__ = ["TOOLS", "ToolContext", "run_tool"]


def _nullable(description: str) -> dict:
    return {"type": ["string", "null"], "description": description}


TOOLS = [
    {
        "name": "search_catalog",
        "description": "Search this business's products/services, prices, offers and FAQs. "
        "Use it whenever you need a fact that isn't already in your instructions.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "What to look up, e.g. a product name"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "save_lead",
        "description": "Save what you've learned about this customer. Call it as soon as you learn any "
        "detail; pass null for anything unknown (values already saved are kept).",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "name": _nullable("Customer's name"),
                "phone": _nullable("Phone number as given, with country code if they gave one"),
                "interest": _nullable("The product(s) or service(s) they want"),
                "budget": _nullable("Budget in the customer's words"),
                "timeline": _nullable("When they plan to buy or visit"),
                "location": _nullable("Preferred branch/outlet or their area"),
                "notes": _nullable("Anything else useful, e.g. requested day/time for the booking"),
                "stage": _nullable(
                    "One of: 'new'; 'qualified' (interest + phone known); 'booked' (agreed to a booking)"
                ),
            },
            "required": ["name", "phone", "interest", "budget", "timeline", "location", "notes", "stage"],
            "additionalProperties": False,
        },
    },
    {
        "name": "handoff_to_human",
        "description": "Hand the conversation to a human team member. You stop replying and the team is "
        "notified. Tell the customer someone will reply shortly.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"reason": {"type": "string", "description": "Why a human is needed"}},
            "required": ["reason"],
            "additionalProperties": False,
        },
    },
]


@dataclass
class ToolContext:
    session: Session
    conversation: Conversation
    channel: str
    looked_up: list[KBItem] = field(default_factory=list)  # items surfaced this turn (for guardrails)


def run_tool(ctx: ToolContext, name: str, args: dict) -> str:
    """Run one tool call and return the text result for the model."""
    match name:
        case "search_catalog":
            hits = search(ctx.session, ctx.conversation.tenant_id, args["query"])
            ctx.looked_up.extend(hits)
            if not hits:
                return "No matching items found. Don't guess; offer to check with the team."
            return "\n".join(item_to_text(h) for h in hits)

        case "save_lead":
            details = dict(args)
            if details.get("stage") not in BOT_SETTABLE_STAGES:
                details["stage"] = None
            lead = upsert_lead(ctx.session, ctx.conversation, details, source=ctx.channel)
            return json.dumps({"saved": True, "lead_id": lead.id, "stage": lead.stage})

        case "handoff_to_human":
            hand_off(ctx.session, ctx.conversation, args["reason"])
            return "Handed off. Tell the customer a team member will reply shortly; don't ask more questions."

        case _:
            return f"Unknown tool: {name}"
