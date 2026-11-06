# -*- coding: utf-8 -*-

"""

    Module :mod:`core.utils.constants`

    Named values shared across packages, so no layer hard-codes magic strings.

"""

# ----------- START: Native Imports ---------- #
from enum import StrEnum
# ----------- END: Native Imports ---------- #

__all__ = [
    "Channel",
    "Role",
    "ConversationStatus",
    "LeadStage",
    "LEAD_STAGE_ORDER",
    "BOT_SETTABLE_STAGES",
    "KBType",
    "DEFAULT_VERTICAL",
    "RESERVED_SLUGS",
]


class Channel(StrEnum):
    WEB = "web"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"


class Role(StrEnum):
    """Who wrote a message."""

    CUSTOMER = "customer"
    BOT = "bot"
    HUMAN = "human"  # a team member of the business


class ConversationStatus(StrEnum):
    BOT = "bot"  # the assistant replies
    HUMAN = "human"  # a team member owns the chat; the assistant stays quiet
    CLOSED = "closed"


class LeadStage(StrEnum):
    NEW = "new"
    QUALIFIED = "qualified"
    BOOKED = "booked"
    WON = "won"
    LOST = "lost"


LEAD_STAGE_ORDER = list(LeadStage)
BOT_SETTABLE_STAGES = (LeadStage.NEW, LeadStage.QUALIFIED, LeadStage.BOOKED)


class KBType(StrEnum):
    """Kinds of knowledge-base item."""

    PRODUCT = "product"
    FAQ = "faq"
    OFFER = "offer"
    DOC = "doc"


DEFAULT_VERTICAL = "generic"
RESERVED_SLUGS = frozenset({"businesses"})  # would collide with /api/businesses
