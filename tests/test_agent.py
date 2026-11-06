import anthropic

from core.ai.client import UnconfiguredClient
from core.ai.agent import FALLBACK_REPLY, HANDOFF_REPLY, build_history, handle_message
from core.ai.prompt import build_system
from core.business.knowledge import list_items
from core.db.models import Lead, Message, UsageEvent
from core.utils.constants import ConversationStatus, LeadStage, Role
from tests.helpers import FakeLLM, lead_args, refusal_response, text_response, tool_response


def chat(session, tenant, text, llm, visitor="v1"):
    return handle_message(session, tenant, "web", visitor, text, client=llm)


def test_reply_and_lead_saved(session, dealer):
    llm = FakeLLM(
        tool_response("save_lead", lead_args(name="Ravi", phone="9876543210", interest="MG Hector")),
        text_response("Thanks Ravi! MG Hector starts at ₹14.49 Lakh*. Test drive kab karna chahenge?"),
    )
    result = chat(session, dealer, "Hector ka price? Main Ravi, 9876543210", llm)

    assert "₹14.49 Lakh" in result.reply and result.flagged == []
    lead = session.query(Lead).one()
    assert (lead.name, lead.phone, lead.stage) == ("Ravi", "9876543210", LeadStage.QUALIFIED)
    assert lead.contact_id and session.query(UsageEvent).count() == 2
    assert [m.role for m in session.query(Message).order_by(Message.id)] == [Role.CUSTOMER, Role.BOT]
    # 2nd call carried the tool result back to the model
    assert llm.calls[1]["messages"][-1]["content"][0]["type"] == "tool_result"


def test_lead_never_moves_backwards(session, dealer):
    llm = FakeLLM(
        tool_response("save_lead", lead_args(phone="98", interest="Astor", stage="booked")), text_response("Booked!"),
        tool_response("save_lead", lead_args(stage="new", name="Asha")), text_response("Noted"),
    )
    chat(session, dealer, "book test drive", llm)
    chat(session, dealer, "my name is Asha", llm)
    lead = session.query(Lead).one()
    assert lead.stage == LeadStage.BOOKED and lead.name == "Asha" and lead.phone == "98"


def test_bot_cannot_mark_won(session, dealer):
    llm = FakeLLM(tool_response("save_lead", lead_args(interest="Gloster", stage="won")), text_response("ok"))
    chat(session, dealer, "hi", llm)
    assert session.query(Lead).one().stage == LeadStage.NEW


def test_handoff_then_bot_stays_quiet(session, dealer):
    llm = FakeLLM(
        tool_response("handoff_to_human", {"reason": "Customer wants to negotiate"}),
        text_response("Our team will reply shortly."),
    )
    first = chat(session, dealer, "best discount do warna nahi lunga", llm)
    assert first.status == ConversationStatus.HUMAN

    second = chat(session, dealer, "hello??", FakeLLM())  # FakeLLM() raises if the AI is called
    assert second.reply is None and second.status == ConversationStatus.HUMAN


def test_refusal_hands_off(session, dealer):
    result = chat(session, dealer, "something odd", FakeLLM(refusal_response()))
    assert result.reply == HANDOFF_REPLY and result.status == ConversationStatus.HUMAN


def test_api_error_falls_back_politely(session, dealer):
    result = chat(session, dealer, "hi", FakeLLM(anthropic.AnthropicError("network down")))
    assert result.reply == FALLBACK_REPLY and result.status == ConversationStatus.BOT


def test_missing_api_key_falls_back_politely(session, dealer):
    result = chat(session, dealer, "hi", UnconfiguredClient())
    assert result.reply == FALLBACK_REPLY


def test_invented_price_is_flagged(session, dealer):
    result = chat(session, dealer, "Hector price?", FakeLLM(text_response("Hector is just ₹12 Lakh!")))
    assert result.flagged == [{"type": "unknown_price", "values": [1_200_000]}]
    assert session.query(Message).filter_by(role=Role.BOT).one().flagged == result.flagged


def test_prompt_follows_the_vertical(session, dealer, clinic):
    dealer_prompt = build_system(dealer, list_items(session, dealer.id), "web")
    clinic_prompt = build_system(clinic, list_items(session, clinic.id), "web")

    assert "test drive" in dealer_prompt and "ex-showroom" in dealer_prompt
    assert "MG Hector" in dealer_prompt and "Banjara Hills" in dealer_prompt
    assert "appointment" in clinic_prompt and "Never diagnose" in clinic_prompt
    for word in ("test drive", "ex-showroom", "MG", "showroom"):
        assert word not in clinic_prompt


def test_history_is_clean():
    msgs = [Message(role=Role.BOT, content="hi"), Message(role=Role.CUSTOMER, content="a"),
            Message(role=Role.CUSTOMER, content="b"), Message(role=Role.HUMAN, content="c")]
    assert build_history(msgs, limit=20) == [
        {"role": "user", "content": "a\nb"},
        {"role": "assistant", "content": "[Team member]: c"},
    ]
