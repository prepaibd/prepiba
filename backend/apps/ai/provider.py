"""LLM providers behind one small interface so the rest of the app never imports an SDK.

- MockProvider: deterministic canned output for dev and tests.
- GeminiProvider: Google Gemini via google-genai (same family Prep uses).
"""
import json
import logging
import random
import time
from collections.abc import Callable, Iterator

from django.conf import settings

log = logging.getLogger(__name__)


class ProviderError(Exception):
    """The model could not be reached or refused. Safe to show a generic message to the user."""


class NotConfigured(ProviderError):
    pass


class Provider:
    name = "base"
    model = ""

    def stream(self, system: str, messages: list[dict]) -> Iterator[str]:
        """Yield text chunks. `messages` is [{"role": "user"|"assistant", "content": str}]."""
        raise NotImplementedError

    def generate_json(self, system: str, prompt: str) -> str:
        """Return the raw model text of a JSON answer."""
        raise NotImplementedError


class MockProvider(Provider):
    name = "mock"
    model = "mock"

    def stream(self, system, messages):
        last = messages[-1]["content"] if messages else ""
        for word in f"(mock tutor) You asked: {last[:120]}. Work through it step by step.".split(" "):
            yield word + " "

    def generate_json(self, system, prompt):
        return json.dumps({
            "overall": 6, "content": 6, "structure": 5, "language": 7,
            "summary": "A clear attempt with a sensible central idea. (mock feedback)",
            "strengths": ["Clear position", "Readable sentences"],
            "improvements": ["Add a concrete example", "Strengthen the conclusion"],
            "corrections": [{"original": "peoples", "suggestion": "people", "reason": "'People' is already plural."}],
        })


class GeminiProvider(Provider):
    name = "gemini"

    def __init__(self, client=None):
        if not settings.GEMINI_API_KEY and client is None:
            raise NotConfigured("GEMINI_API_KEY is not set")
        self.model = settings.GEMINI_MODEL
        self._client = client

    @property
    def client(self):
        if self._client is None:
            from google import genai
            from google.genai import types

            # Bound every call. Without this a slow upstream response can hold a gunicorn worker until its own
            # 120 s limit kills it, instead of failing cleanly into the "saved, try again" path.
            self._client = genai.Client(
                api_key=settings.GEMINI_API_KEY,
                http_options=types.HttpOptions(timeout=settings.AI_TIMEOUT_SECONDS * 1000),
            )
        return self._client

    @staticmethod
    def _contents(messages):
        return [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                for m in messages]

    def _config(self, system, **extra):
        from google.genai import types

        return types.GenerateContentConfig(system_instruction=system, temperature=0.3, max_output_tokens=2048, **extra)

    RETRIES = 2  # extra attempts after the first, for transient upstream failures only

    @staticmethod
    def _transient(exc: Exception) -> bool:
        """5xx and 429 from Google are usually momentary; 4xx (bad request, auth) will not fix themselves."""
        code = getattr(exc, "code", None)
        return isinstance(code, int) and (code >= 500 or code == 429)

    def _attempts(self, call: Callable, what: str):
        """Run `call()`, retrying transient failures with short jittered backoff while the time budget allows."""
        started = time.monotonic()
        for attempt in range(self.RETRIES + 1):
            try:
                return call()
            except Exception as e:  # the SDK raises several error types; only the status code matters here
                last = attempt == self.RETRIES
                out_of_time = time.monotonic() - started >= settings.AI_TIMEOUT_SECONDS
                log.warning("Gemini %s failed (attempt %d): %s %s", what, attempt + 1, type(e).__name__,
                            getattr(e, "code", ""))
                if last or out_of_time or not self._transient(e):
                    raise ProviderError("The AI service is unavailable right now.") from e
                time.sleep(0.5 * (3 ** attempt) + random.uniform(0, 0.3))  # ~0.5s, ~1.5s

    def stream(self, system, messages):
        contents, config = self._contents(messages), self._config(system)
        started = time.monotonic()
        for attempt in range(self.RETRIES + 1):
            sent_any = False
            try:
                for chunk in self.client.models.generate_content_stream(
                    model=self.model, contents=contents, config=config
                ):
                    if chunk.text:
                        sent_any = True
                        yield chunk.text
                return
            except Exception as e:
                last = attempt == self.RETRIES
                out_of_time = time.monotonic() - started >= settings.AI_TIMEOUT_SECONDS
                log.warning("Gemini stream failed (attempt %d): %s %s", attempt + 1, type(e).__name__,
                            getattr(e, "code", ""))
                # Once text has reached the student a retry would repeat it, so only retry before the first chunk.
                if sent_any or last or out_of_time or not self._transient(e):
                    raise ProviderError("The AI service is unavailable right now.") from e
                time.sleep(0.5 * (3 ** attempt) + random.uniform(0, 0.3))

    def generate_json(self, system, prompt):
        def call():
            resp = self.client.models.generate_content(
                model=self.model, contents=prompt,
                config=self._config(system, response_mime_type="application/json"),
            )
            return resp.text or ""

        return self._attempts(call, "call")


def get_provider() -> Provider:
    name = settings.AI_PROVIDER
    if name == "mock":
        return MockProvider()
    if name == "gemini":
        return GeminiProvider()
    raise NotConfigured(f"Unknown AI_PROVIDER {name!r}")
