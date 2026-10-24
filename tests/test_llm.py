import pytest

from igt.errors import ApiError, ConfigError
from igt.llm import AnthropicIdeaWriter
from igt.models import Segment, Transcript

T = Transcript(
    "instagram", "Gemma", "w", "en", (Segment(0, 1, "tiny embedding model"),)
)


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


def test_system_prompt_asks_for_level_3_headings_only():
    from igt.llm import _SYSTEM

    assert "###" in _SYSTEM and "never use # or ##" in _SYSTEM


def test_kinds_use_their_own_prompt():
    from igt.llm import PROMPTS

    assert set(PROMPTS) == {"idea", "summary", "chapters", "social"}
    c = FakeClient()
    writer(c).write(T, "summary")
    assert c.kw["system"] == PROMPTS["summary"] != PROMPTS["idea"]


def test_chapters_sends_timestamped_cues():
    c = FakeClient()
    writer(c).write(
        Transcript("y", "t", "w", "en", (Segment(65, 70, "second"),)), "chapters"
    )
    assert "[01:05] second" in c.kw["messages"][0]["content"]


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


# --- Ollama ---------------------------------------------------------------
import urllib.error  # noqa: E402

from igt.llm import OLLAMA_DEFAULT_MODEL, OllamaIdeaWriter, make_writer  # noqa: E402


class FakeHttp:
    def __init__(self, tags=("m2:latest",), chat="local analysis", fail=None):
        self.tags, self.chat, self.fail, self.calls = tags, chat, fail, []

    def __call__(self, url, payload=None):
        self.calls.append((url, payload))
        if self.fail:
            raise self.fail
        if url.endswith("/api/tags"):
            return {"models": [{"name": n} for n in self.tags]}
        return {"message": {"content": self.chat}}


def ollama(http, env=None, model="m2"):
    return OllamaIdeaWriter(model, {} if env is None else env, http)


def test_ollama_write_posts_chat_to_default_host():
    h = FakeHttp()
    assert ollama(h).write(T) == "local analysis"
    url, payload = h.calls[0]
    assert url == "http://localhost:11434/api/chat"
    assert payload["model"] == "m2" and payload["stream"] is False
    assert "tiny embedding model" in payload["messages"][-1]["content"]


def test_ollama_host_from_env_with_trailing_slash():
    h = FakeHttp()
    ollama(h, {"OLLAMA_HOST": "http://box:1234/"}).write(T)
    assert h.calls[0][0] == "http://box:1234/api/chat"


def test_ollama_host_without_scheme_gets_http():
    h = FakeHttp()
    ollama(h, {"OLLAMA_HOST": "box:1234"}).write(T)
    assert h.calls[0][0] == "http://box:1234/api/chat"


def test_ollama_check_ok_when_model_present_with_or_without_tag():
    ollama(FakeHttp(tags=("m2:latest",))).check()
    ollama(FakeHttp(tags=("m2:7b",)), model="m2:7b").check()


def test_ollama_check_missing_model_hints_pull():
    with pytest.raises(ConfigError, match="ollama pull m2"):
        ollama(FakeHttp(tags=("other:1b",))).check()


def test_ollama_check_unreachable_is_config_error():
    h = FakeHttp(fail=urllib.error.URLError("refused"))
    with pytest.raises(ConfigError, match="cannot reach Ollama"):
        ollama(h).check()


def test_ollama_request_failure_is_api_error():
    with pytest.raises(ApiError, match="boom"):
        ollama(FakeHttp(fail=RuntimeError("boom"))).write(T)


def test_ollama_empty_response_is_api_error():
    with pytest.raises(ApiError, match="empty"):
        ollama(FakeHttp(chat=" ")).write(T)


def test_make_writer_picks_provider_and_default_model():
    assert isinstance(make_writer("ollama", None, {}), OllamaIdeaWriter)
    assert make_writer("ollama", None, {})._model == OLLAMA_DEFAULT_MODEL
    assert isinstance(make_writer("anthropic", "x", {}), AnthropicIdeaWriter)
    assert make_writer("anthropic", "x", {})._model == "x"


def test_system_prompt_demands_traceability_and_follow_up_questions():
    from igt.llm import _SYSTEM

    assert "[ASSUMPTION]" in _SYSTEM
    assert "Follow-up questions" in _SYSTEM
    assert "Given/When/Then" in _SYSTEM
    assert "handles errors properly" in _SYSTEM


def test_http_json_round_trips_against_a_real_local_server():
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    from igt.llm import _http_json

    class Echo(BaseHTTPRequestHandler):
        def _reply(self, body):
            data = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self._reply({"method": "GET"})

        def do_POST(self):
            size = int(self.headers["Content-Length"])
            self._reply({"method": "POST", "got": json.loads(self.rfile.read(size))})

        def log_message(self, *_a):
            pass

    server = HTTPServer(("127.0.0.1", 0), Echo)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        assert _http_json(base) == {"method": "GET"}
        assert _http_json(base, {"a": 1}) == {"method": "POST", "got": {"a": 1}}
    finally:
        server.shutdown()
        server.server_close()
