# -*- coding: utf-8 -*-

"""

    Module :mod:`web.application.api.app.leads`

    Leads captured by the assistant.

"""

# ----------- START: Third Party Imports ---------- #
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
# ----------- END: Third Party Imports ---------- #

# ----------- START: In-App Imports ---------- #
from core.db.models import Tenant
from core.db.statements import stmt_list_leads
from web.application.api.types import lead_out
from web.application.common import get_session, get_tenant
# ----------- END: In-App Imports ---------- #

router = APIRouter(prefix="/api/{slug}/leads", tags=["leads"])


@router.get("")
def list_leads(tenant: Tenant = Depends(get_tenant), session: Session = Depends(get_session)):
    return [lead_out(lead) for lead in session.scalars(stmt_list_leads(tenant.id))]
