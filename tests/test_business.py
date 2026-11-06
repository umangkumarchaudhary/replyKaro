from core.business.knowledge import list_items, search
from core.business.spec import BusinessSpec, import_business, load_spec_file
from core.business.verticals import available_verticals, get_vertical
from tests.conftest import EXAMPLES

import pytest
from pydantic import ValidationError


def test_example_files_load(dealer, clinic, session):
    assert dealer.vertical == "automotive" and clinic.vertical == "clinic"
    assert len(dealer.profile.locations) == 8
    comet = next(i for i in list_items(session, dealer.id) if i.title == "MG Comet EV")
    assert comet.price_min == 798_000
    root_canal = next(i for i in list_items(session, clinic.id) if i.title == "Root canal treatment")
    assert (root_canal.price_min, root_canal.price_max) == (4000, 8000)


def test_reimport_replaces_knowledge(dealer, session):
    before = len(list_items(session, dealer.id))
    import_business(session, load_spec_file(EXAMPLES / "raam-mg.toml"))
    assert len(list_items(session, dealer.id)) == before


def test_businesses_are_isolated(dealer, clinic, session):
    assert search(session, clinic.id, "Hector") == []
    assert search(session, dealer.id, "Hector ka price kya hai")[0].title == "MG Hector"
    assert search(session, clinic.id, "root canal")[0].title == "Root canal treatment"


def test_verticals():
    assert {"generic", "automotive", "clinic"} <= set(available_verticals())
    assert get_vertical("automotive").booking_type == "test drive"
    assert get_vertical("no-such-industry").key == "generic"  # unknown → generic fallback


def test_spec_validation():
    with pytest.raises(ValidationError):
        BusinessSpec(slug="Bad Slug!", name="x")
    with pytest.raises(ValidationError):
        BusinessSpec(slug="businesses", name="x")  # reserved
