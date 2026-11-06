# -*- coding: utf-8 -*-

"""

    Module :mod:`web.application.api.inputs`

    Request bodies accepted by the API.

"""

# ----------- START: Third Party Imports ---------- #
from pydantic import BaseModel, Field
# ----------- END: Third Party Imports ---------- #

# ----------- START: In-App Imports ---------- #
from core.utils.constants import KBType
# ----------- END: In-App Imports ---------- #

__all__ = ["ChatIn", "ProfileIn", "KBItemIn", "HumanReplyIn"]


class ChatIn(BaseModel):
    visitor_id: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=4000)


class ProfileIn(BaseModel):
    """Partial update: only the fields you send are changed."""

    about: str | None = None
    contact: dict[str, str] | None = None
    hours: dict[str, str] | None = None
    locations: list[dict] | None = None
    rules: list[str] | None = None
    tone: str | None = None
    booking_type: str | None = None


class KBItemIn(BaseModel):
    type: KBType
    title: str = Field(min_length=1, max_length=300)
    content: str = ""
    price_min: float | None = None
    price_max: float | None = None
    meta: dict = {}
    active: bool = True


class HumanReplyIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
