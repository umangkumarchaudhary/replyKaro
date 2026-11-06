import pytest
from fastapi.testclient import TestClient

from tests.helpers import FakeLLM, lead_args, text_response, tool_response
from web.application import common
from web.application.routes import app


@pytest.fixture
def api(session_factory, dealer):
    llm = FakeLLM()

    def session_override():
        with session_factory() as s:
            yield s

    app.dependency_overrides[common.get_session] = session_override
    app.dependency_overrides[common.get_llm] = lambda: llm
    yield TestClient(app), llm
    app.dependency_overrides.clear()


def test_chat_flow(api):
    client, llm = api
    llm.responses += [
        tool_response("save_lead", lead_args(name="Ravi", phone="98765", interest="Windsor EV")),
        text_response("Windsor EV starts at ₹13.50 Lakh*."),
    ]
    r = client.post("/api/raam-mg/chat", json={"visitor_id": "web-1", "text": "Windsor price? Ravi 98765"})
    assert r.status_code == 200 and "₹13.50 Lakh" in r.json()["reply"]

    leads = client.get("/api/raam-mg/leads").json()
    assert leads[0]["name"] == "Ravi" and leads[0]["stage"] == "qualified"

    conv_id = r.json()["conversation_id"]
    assert client.post(f"/api/raam-mg/conversations/{conv_id}/reply", json={"text": "Hi Ravi!"}).json()["status"] == "human"
    assert client.post("/api/raam-mg/chat", json={"visitor_id": "web-1", "text": "ok"}).json()["reply"] is None
    assert client.post(f"/api/raam-mg/conversations/{conv_id}/release").json()["status"] == "bot"

    detail = client.get(f"/api/raam-mg/conversations/{conv_id}").json()
    assert [m["role"] for m in detail["messages"]] == ["customer", "bot", "human", "customer"]
    assert client.get("/api/raam-mg/usage").json()["api_calls"] == 2


def test_create_business_and_edit_kb(api):
    client, _ = api
    spec = {"slug": "zen-gym", "name": "Zen Gym", "products": [{"title": "Monthly plan", "price": "₹2,000"}]}
    assert client.post("/api/businesses", json=spec).status_code == 201
    assert client.get("/api/zen-gym/profile").json()["vertical"] == "generic"

    item = client.post("/api/zen-gym/kb", json={"type": "faq", "title": "Trial?", "content": "Free 1-day trial"}).json()
    assert len(client.get("/api/zen-gym/kb").json()) == 2
    assert client.delete(f"/api/zen-gym/kb/{item['id']}").status_code == 204


def test_tenant_isolation_and_404s(api):
    client, _ = api
    assert client.get("/api/nope/profile").status_code == 404
    client.post("/api/businesses", json={"slug": "other-biz", "name": "Other"})
    dealer_item = client.get("/api/raam-mg/kb").json()[0]
    # another business can't touch Raam MG's items
    assert client.delete(f"/api/other-biz/kb/{dealer_item['id']}").status_code == 404
    assert "automotive" in client.get("/api/businesses/verticals").json()
