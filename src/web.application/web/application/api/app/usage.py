# -*- coding: utf-8 -*-

"""

    Module :mod:`web.application.api.app.usage`

    AI usage and cost for a business.

"""

# ----------- START: Third Party Imports ---------- #
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
# ----------- END: Third Party Imports ---------- #

# ----------- START: In-App Imports ---------- #
from core.db.models import Tenant
from core.db.statements import stmt_count_conversations, stmt_usage_summary
from web.application.common import get_session, get_tenant
# ----------- END: In-App Imports ---------- #

router = APIRouter(prefix="/api/{slug}/usage", tags=["usage"])


@router.get("")
def usage(tenant: Tenant = Depends(get_tenant), session: Session = Depends(get_session)):
    row = session.execute(stmt_usage_summary(tenant.id)).one()._asdict()
    conversations = session.scalar(stmt_count_conversations(tenant.id)) or 0
    row["cost_usd"] = round(row["cost_usd"], 4)
    row["conversations"] = conversations
    row["cost_per_conversation_usd"] = round(row["cost_usd"] / conversations, 5) if conversations else 0.0
    return row
