# -*- coding: utf-8 -*-

"""

    Module :mod:`web.application.common`

    Dependencies and helpers shared by every API module.

"""

# ----------- START: Native Imports ---------- #
from typing import TypeVar
# ----------- END: Native Imports ---------- #

# ----------- START: Third Party Imports ---------- #
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
# ----------- END: Third Party Imports ---------- #

# ----------- START: In-App Imports ---------- #
from core.ai.client import LLMClient, default_client
from core.db.models import Tenant
from core.db.session import get_session
from core.db.statements import stmt_query_tenant
# ----------- END: In-App Imports ---------- #

__all__ = ["get_session", "get_tenant", "get_llm", "get_owned"]

T = TypeVar("T")


def get_tenant(slug: str, session: Session = Depends(get_session)) -> Tenant:
    """The business named by the ``{slug}`` in the URL, or 404."""
    tenant = session.scalar(stmt_query_tenant(slug))
    if tenant is None:
        raise HTTPException(404, f"Business '{slug}' not found")
    return tenant


def get_llm() -> LLMClient:
    return default_client()


def get_owned(session: Session, model: type[T], row_id: int, tenant: Tenant, label: str = "Item") -> T:
    """Fetch a row by id, making sure it belongs to this business (else 404)."""
    row = session.get(model, row_id)
    if row is None or row.tenant_id != tenant.id:
        raise HTTPException(404, f"{label} not found")
    return row
