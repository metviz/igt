import json
import urllib.error
import urllib.request
from typing import Any, Callable, Mapping, Protocol

from igt.errors import ApiError, ConfigError
from igt.idea import material
from igt.models import Transcript

LLM_FORMATS = ("summary", "chapters", "social")

DEFAULT_MODEL = "claude-sonnet-5-5"
OLLAMA_DEFAULT_MODEL = "llama3.1:8b"
PROVIDERS = ("anthropic", "ollama")
_OLLAMA_TIMEOUT = 300  # local models can be slow
_SYSTEM = (
    "You turn a short social-video's extracted content into a project brief. "
    "Use only what the material supports and tie each requirement to something "
    "the material says; tag anything it does not state as [ASSUMPTION]. "
    "A limitation or complaint in the material is not a requirement. "
    "Be specific: no vague phrases such as 'handles errors properly'. "
    "Reply in markdown with these ### sections: Summary, Potential requirements "
    "(functional, non-functional, data; add Given/When/Then acceptance criteria "
    "for the core feature), Risks and unknowns, Follow-up questions (grouped as "
    "core functionality, technical stack, scale and security, scope and phasing), "
    "Suggested first experiment, Brainstorm prompts. Use ### headings only: "
    "never use # or ##, and add no title. Do not repeat the material."
)
_FORMAT_RULES = (
    "Use only what the material says; invent nothing. Reply in markdown with no "
    "title, using ### headings if you need any."
)
PROMPTS = {
    "idea": _SYSTEM,
    "summary": (
        "Summarise a short video's extracted content. Give a one-sentence gist, "
        "then 3-7 bullet points of the key facts or steps. " + _FORMAT_RULES
    ),
    "chapters": (
        "Split a video into chapters from its timestamped transcript. Reply with "
        "one line per chapter: `mm:ss Title` (3-6 words), the first at 00:00, "
        "using only timestamps that appear in the material. " + _FORMAT_RULES
    ),
    "social": (
        "Draft social posts from a video's content: one X/Twitter post (max 280 "
        "characters), one LinkedIn post (under 120 words), each with at most 3 "
        "hashtags. " + _FORMAT_RULES
    ),
}


def _content(t: Transcript, kind: str) -> str:
    if kind != "chapters":
        return material(t)
    return "\n".join(
        f"[{int(s.start) // 60:02}:{int(s.start) % 60:02}] {s.text.strip()}"
        for s in t.segments
        if s.text.strip()
    )


class IdeaWriter(Protocol):
    def write(self, transcript: Transcript, kind: str = "idea") -> str: ...


def _anthropic_client(api_key: str) -> Any:
    import anthropic  # optional extra: igt[llm]

    return anthropic.Anthropic(api_key=api_key)


class AnthropicIdeaWriter:
    """The key is read from the environment, never from argv."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        env: Mapping[str, str] | None = None,
        client_factory: Callable[[str], Any] = _anthropic_client,
    ) -> None:
        self._model = model
        self._env = {} if env is None else env
        self._factory = client_factory

    def _key(self) -> str:
        key = self._env.get("ANTHROPIC_API_KEY", "").strip()
        if not key:
            raise ConfigError("--idea-llm needs ANTHROPIC_API_KEY in the environment")
        return key

    def check(self) -> None:
        key = self._key()
        try:
            self._factory(key)
        except ImportError as exc:
            raise ConfigError(
                "--idea-llm needs the anthropic package: pip install 'igt[llm]'"
            ) from exc

    def write(self, transcript: Transcript, kind: str = "idea") -> str:
        client = self._factory(self._key())
        try:
            resp = client.messages.create(
                model=self._model,
                max_tokens=2000,
                system=PROMPTS[kind],
                messages=[{"role": "user", "content": _content(transcript, kind)}],
            )
        except Exception as exc:  # SDK errors vary; never echo the key
            raise ApiError(f"LLM request failed: {exc}") from exc
        text = "".join(
            b.text for b in resp.content if getattr(b, "type", "") == "text"
        ).strip()
        if not text:
            raise ApiError("LLM returned an empty response")
        return text


def _http_json(url: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=_OLLAMA_TIMEOUT) as resp:  # noqa: S310
        return json.load(resp)


class OllamaIdeaWriter:
    """Local model via Ollama's REST API (stdlib only). Host: $OLLAMA_HOST."""

    def __init__(
        self,
        model: str = OLLAMA_DEFAULT_MODEL,
        env: Mapping[str, str] | None = None,
        http: Callable[..., dict] = _http_json,
    ) -> None:
        self._model = model
        host = (env or {}).get("OLLAMA_HOST", "").strip() or "localhost:11434"
        if "://" not in host:
            host = f"http://{host}"
        self._base = host.rstrip("/")
        self._http = http

    def check(self) -> None:
        try:
            names = {m["name"] for m in self._http(f"{self._base}/api/tags")["models"]}
        except (OSError, urllib.error.URLError, KeyError, ValueError) as exc:
            raise ConfigError(
                f"cannot reach Ollama at {self._base} (is `ollama serve` running?): {exc}"
            ) from exc
        if self._model not in names and f"{self._model}:latest" not in names:
            raise ConfigError(
                f"Ollama model {self._model!r} not found: ollama pull {self._model}"
            )

    def write(self, transcript: Transcript, kind: str = "idea") -> str:
        try:
            resp = self._http(
                f"{self._base}/api/chat",
                {
                    "model": self._model,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": PROMPTS[kind]},
                        {"role": "user", "content": _content(transcript, kind)},
                    ],
                },
            )
            text = resp["message"]["content"].strip()
        except Exception as exc:
            raise ApiError(f"Ollama request failed: {exc}") from exc
        if not text:
            raise ApiError("LLM returned an empty response")
        return text


def make_writer(provider: str, model: str | None, env: Mapping[str, str]) -> IdeaWriter:
    if provider == "ollama":
        return OllamaIdeaWriter(model or OLLAMA_DEFAULT_MODEL, env)
    return AnthropicIdeaWriter(model or DEFAULT_MODEL, env)
