# -*- coding: utf-8 -*-

"""

    Module :mod:`core.business.spec`

    One format that describes ANY business. Used by the ``replykaro-load``
    command, the ``POST /api/businesses`` endpoint and, later, the onboarding wizard.

"""

# ----------- START: Native Imports ---------- #
import json
import tomllib
from pathlib import Path
# ----------- END: Native Imports ---------- #

# ----------- START: Third Party Imports ---------- #
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
# ----------- END: Third Party Imports ---------- #

# ----------- START: In-App Imports ---------- #
from core.db.models import BusinessProfile, KBItem, Tenant
from core.db.statements import stmt_delete_kb_items, stmt_query_tenant
from core.utils.constants import DEFAULT_VERTICAL, RESERVED_SLUGS, KBType
from core.utils.money import parse_price
# ----------- END: In-App Imports ---------- #

__all__ = ["BusinessSpec", "ProductSpec", "FAQSpec", "OfferSpec", "LocationSpec", "load_spec_file", "import_business"]


class ProductSpec(BaseModel):
    title: str
    price: float | None = None  # rupees; "₹7.98 Lakh" style text is accepted too
    price_max: float | None = None
    description: str = ""

    @field_validator("price", "price_max", mode="before")
    @classmethod
    def read_price(cls, value):
        return parse_price(value)


class FAQSpec(BaseModel):
    q: str
    a: str


class OfferSpec(BaseModel):
    title: str
    description: str


class LocationSpec(BaseModel):
    name: str
    address: str = ""


class BusinessSpec(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,62}$")
    name: str
    vertical: str = DEFAULT_VERTICAL  # a file in core/business/verticals/
    about: str = ""
    tone: str | None = None
    booking_type: str | None = None  # overrides the vertical's default
    contact: dict[str, str] = {}
    hours: dict[str, str] = {}
    locations: list[LocationSpec] = []
    rules: list[str] = []  # the owner's own instructions for the assistant
    products: list[ProductSpec] = []
    faqs: list[FAQSpec] = []
    offers: list[OfferSpec] = []

    @field_validator("slug")
    @classmethod
    def not_reserved(cls, slug: str) -> str:
        if slug in RESERVED_SLUGS:
            raise ValueError(f"'{slug}' is reserved")
        return slug


def load_spec_file(path: str | Path) -> BusinessSpec:
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    data = tomllib.loads(raw) if path.suffix == ".toml" else json.loads(raw)
    return BusinessSpec.model_validate(data)


def import_business(session: Session, spec: BusinessSpec) -> Tenant:
    """Create or update a business. Its knowledge base is replaced by the spec's items."""
    tenant = session.scalar(stmt_query_tenant(spec.slug))
    if tenant is None:
        tenant = Tenant(slug=spec.slug, name=spec.name)
        tenant.profile = BusinessProfile()
        session.add(tenant)
    tenant.name, tenant.vertical = spec.name, spec.vertical

    profile = tenant.profile
    profile.about, profile.contact, profile.hours, profile.rules = spec.about, spec.contact, spec.hours, spec.rules
    profile.locations = [loc.model_dump() for loc in spec.locations]
    profile.booking_type = spec.booking_type
    if spec.tone:
        profile.tone = spec.tone
    session.flush()

    session.execute(stmt_delete_kb_items(tenant.id))
    for p in spec.products:
        session.add(KBItem(tenant_id=tenant.id, type=KBType.PRODUCT, title=p.title, content=p.description,
                           price_min=p.price, price_max=p.price_max))
    for f in spec.faqs:
        session.add(KBItem(tenant_id=tenant.id, type=KBType.FAQ, title=f.q, content=f.a))
    for o in spec.offers:
        session.add(KBItem(tenant_id=tenant.id, type=KBType.OFFER, title=o.title, content=o.description))
    session.commit()
    return tenant
