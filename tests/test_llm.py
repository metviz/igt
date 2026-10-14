import pytest

from igt.errors import ApiError, ConfigError
from igt.llm import AnthropicIdeaWriter
from igt.models import Segment, Transcript

T = Transcript("instagram", "Gemma", "w", "en", (Segment(0, 1, "tiny embedding model"),))


class Block:
    def __init__(self, text):
        self.type, self.text = "text", text


class FakeClient:
    def __init__(self, text="analysis", raises=None):
        self.text, self.raises, self.kw = text, raises, None
        self.messages = self

    def create(self, **kw):
        self.kw = kw
        if self.raises:
            raise self.raises
        return type("R", (), {"content": [Block(self.text)]})()


def writer(client, env=None):
    return AnthropicIdeaWriter(
        "m1", {"ANTHROPIC_API_KEY": "k"} if env is None else env, lambda key: client
    )


def test_write_sends_material_and_returns_text():
    c = FakeClient("## Reqs\n- x")
    assert writer(c).write(T) == "## Reqs\n- x"
    assert c.kw["model"] == "m1"
    assert "tiny embedding model" in c.kw["messages"][0]["content"]
    assert c.kw["max_tokens"] > 0


def test_check_needs_api_key():
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        writer(FakeClient(), env={}).check()


def test_check_passes_with_key():
    writer(FakeClient()).check()


def test_missing_package_gives_install_hint():
    def boom(key):
        raise ImportError("anthropic")

    with pytest.raises(ConfigError, match=r"igt\[llm\]"):
        AnthropicIdeaWriter("m", {"ANTHROPIC_API_KEY": "k"}, boom).check()


def test_api_failure_is_api_error_without_leaking_key():
    with pytest.raises(ApiError, match="boom") as e:
        writer(FakeClient(raises=RuntimeError("boom"))).write(T)
    assert "k" != str(e.value)


def test_empty_response_is_api_error():
    with pytest.raises(ApiError, match="empty"):
        writer(FakeClient("  ")).write(T)
