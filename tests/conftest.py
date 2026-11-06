from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.business.spec import import_business, load_spec_file
from core.db.session import init_db

EXAMPLES = Path(__file__).parents[1] / "examples"


@pytest.fixture
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(eng)
    return eng


@pytest.fixture
def session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def session(session_factory):
    with session_factory() as s:
        yield s


@pytest.fixture
def dealer(session):
    return import_business(session, load_spec_file(EXAMPLES / "raam-mg.toml"))


@pytest.fixture
def clinic(session):
    return import_business(session, load_spec_file(EXAMPLES / "demo-clinic.toml"))
