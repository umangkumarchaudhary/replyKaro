"""Fake Claude client + response builders, so tests never call the real API."""

import copy
from types import SimpleNamespace

USAGE = SimpleNamespace(input_tokens=1000, output_tokens=100, cache_read_input_tokens=0,
                        cache_creation_input_tokens=0)


def text_response(text: str):
    return SimpleNamespace(stop_reason="end_turn", usage=USAGE,
                           content=[SimpleNamespace(type="text", text=text)])


def tool_response(name: str, args: dict, call_id: str = "toolu_1", text: str = ""):
    content = [SimpleNamespace(type="text", text=text)] if text else []
    content.append(SimpleNamespace(type="tool_use", id=call_id, name=name, input=args))
    return SimpleNamespace(stop_reason="tool_use", usage=USAGE, content=content)


def refusal_response():
    return SimpleNamespace(stop_reason="refusal", usage=USAGE, content=[])


def lead_args(**fields) -> dict:
    base = dict.fromkeys(("name", "phone", "interest", "budget", "timeline", "location", "notes", "stage"))
    return {**base, **fields}


class FakeLLM:
    """Returns scripted responses in order; raises if called more often than scripted."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        if not self.responses:
            raise AssertionError("The AI was called more times than the test expected")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response
