# -*- coding: utf-8 -*-

"""

    Module :mod:`web.application.api.app.chat`

    The web channel: a customer on the website chat sends a message.

"""

# ----------- START: Third Party Imports ---------- #
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
# ----------- END: Third Party Imports ---------- #

# ----------- START: In-App Imports ---------- #
from core.ai.agent import handle_message
from core.ai.client import LLMClient
from core.db.models import Tenant
from core.utils.constants import Channel
from web.application.api.inputs import ChatIn
from web.application.common import get_llm, get_session, get_tenant
# ----------- END: In-App Imports ---------- #

router = APIRouter(prefix="/api/{slug}", tags=["chat"])


@router.post("/chat")
def chat(
    body: ChatIn,
    tenant: Tenant = Depends(get_tenant),
    session: Session = Depends(get_session),
    llm: LLMClient = Depends(get_llm),
):
    result = handle_message(session, tenant, Channel.WEB, body.visitor_id, body.text.strip(), client=llm)
    return {
        "reply": result.reply,
        "conversation_id": result.conversation_id,
        "status": result.status,
        "tool_calls": result.tool_calls,
    }
