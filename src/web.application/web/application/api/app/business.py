# -*- coding: utf-8 -*-

"""

    Module :mod:`web.application.api.app.business`

    Set up businesses (import a full spec) and edit a business's profile and knowledge base.

"""

# ----------- START: Third Party Imports ---------- #
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
# ----------- END: Third Party Imports ---------- #

# ----------- START: In-App Imports ---------- #
from core.business.spec import BusinessSpec, import_business
from core.business.verticals import available_verticals
from core.db.models import KBItem, Tenant
from core.db.statements import stmt_list_kb_items
from web.application.api.inputs import KBItemIn, ProfileIn
from web.application.api.types import kb_item_out, profile_out
from web.application.common import get_owned, get_session, get_tenant
# ----------- END: In-App Imports ---------- #

setup_router = APIRouter(prefix="/api/businesses", tags=["businesses"])
router = APIRouter(prefix="/api/{slug}", tags=["business"])


# ---------- setup ----------


@setup_router.post("", status_code=201)
def create_or_update_business(spec: BusinessSpec, session: Session = Depends(get_session)):
    """Create or update a whole business from one spec (same format as the example .toml files)."""
    tenant = import_business(session, spec)
    return {**profile_out(tenant), "kb_items": len(spec.products) + len(spec.faqs) + len(spec.offers)}


@setup_router.get("/verticals")
def list_verticals():
    return available_verticals()


# ---------- profile ----------


@router.get("/profile")
def get_profile(tenant: Tenant = Depends(get_tenant)):
    return profile_out(tenant)


@router.put("/profile")
def update_profile(body: ProfileIn, tenant: Tenant = Depends(get_tenant), session: Session = Depends(get_session)):
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(tenant.profile, field, value)
    session.commit()
    return profile_out(tenant)


# ---------- knowledge base ----------


@router.get("/kb")
def list_kb(tenant: Tenant = Depends(get_tenant), session: Session = Depends(get_session)):
    return [kb_item_out(i) for i in session.scalars(stmt_list_kb_items(tenant.id, active_only=False))]


@router.post("/kb", status_code=201)
def create_kb_item(body: KBItemIn, tenant: Tenant = Depends(get_tenant), session: Session = Depends(get_session)):
    item = KBItem(tenant_id=tenant.id, **body.model_dump())
    session.add(item)
    session.commit()
    return kb_item_out(item)


@router.put("/kb/{item_id}")
def update_kb_item(item_id: int, body: KBItemIn, tenant: Tenant = Depends(get_tenant),
                   session: Session = Depends(get_session)):
    item = get_owned(session, KBItem, item_id, tenant)
    for field, value in body.model_dump().items():
        setattr(item, field, value)
    session.commit()
    return kb_item_out(item)


@router.delete("/kb/{item_id}", status_code=204)
def delete_kb_item(item_id: int, tenant: Tenant = Depends(get_tenant), session: Session = Depends(get_session)):
    session.delete(get_owned(session, KBItem, item_id, tenant))
    session.commit()
