from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone
from google.genai import errors as genai_errors

from apps.accounts.models import User
from apps.ai import quota
from apps.ai.models import AIUsageLog
from apps.ai.provider import GeminiProvider, MockProvider, NotConfigured, ProviderError, get_provider
from tests.helpers import V1, client_for

pytestmark = pytest.mark.django_db


class FakeModels:
    def __init__(self, chunks=(), text="{}", fail=False):
        self.calls, self.chunks, self.text, self.fail = [], chunks, text, fail

    def generate_content_stream(self, **kw):
        self.calls.append(kw)
        if self.fail:
            raise RuntimeError("boom")
        yield from (SimpleNamespace(text=c) for c in self.chunks)

    def generate_content(self, **kw):
        self.calls.append(kw)
        if self.fail:
            raise RuntimeError("boom")
        return SimpleNamespace(text=self.text)


def fake_client(**kw):
    return SimpleNamespace(models=FakeModels(**kw))


# ---- Gemini adapter (verified against a fake SDK client; no live call is made) ---------------------------------

def test_gemini_stream_maps_roles_and_passes_system_prompt(settings):
    settings.GEMINI_MODEL = "test-model"
    client = fake_client(chunks=["Hel", "lo", ""])
    p = GeminiProvider(client=client)
    out = list(p.stream("SYS", [{"role": "user", "content": "q1"}, {"role": "assistant", "content": "a1"},
                                {"role": "user", "content": "q2"}]))
    assert out == ["Hel", "lo"]
    call = client.models.calls[0]
    assert call["model"] == "test-model"
    assert [c["role"] for c in call["contents"]] == ["user", "model", "user"]
    assert call["contents"][2]["parts"][0]["text"] == "q2"
    assert call["config"].system_instruction == "SYS"


def test_gemini_json_requests_json_mime_type():
    client = fake_client(text='{"a": 1}')
    assert GeminiProvider(client=client).generate_json("SYS", "prompt") == '{"a": 1}'
    assert client.models.calls[0]["config"].response_mime_type == "application/json"


def test_gemini_errors_become_provider_error():
    p = GeminiProvider(client=fake_client(fail=True))
    with pytest.raises(ProviderError):
        list(p.stream("s", [{"role": "user", "content": "x"}]))
    with pytest.raises(ProviderError):
        p.generate_json("s", "x")


def test_gemini_without_key_is_not_configured(settings):
    settings.GEMINI_API_KEY = ""
    with pytest.raises(NotConfigured):
        GeminiProvider()


def test_get_provider_selection(settings):
    settings.AI_PROVIDER = "mock"
    assert isinstance(get_provider(), MockProvider)
    settings.AI_PROVIDER = "gemini"
    settings.GEMINI_API_KEY = ""
    with pytest.raises(NotConfigured):
        get_provider()
    settings.AI_PROVIDER = "nope"
    with pytest.raises(NotConfigured):
        get_provider()


# ---- quota ----------------------------------------------------------------------------------------------------

@pytest.fixture
def user():
    return User.objects.create_user("q@example.com")


def test_reserve_until_limit_then_refuse(user, settings):
    settings.AI_DAILY_LIMITS = {"free": {"chat": 2, "writing": 1}, "paid": {"chat": 5, "writing": 5}}
    quota.reserve(user, "chat")
    quota.reserve(user, "chat")
    with pytest.raises(quota.QuotaExceeded) as e:
        quota.reserve(user, "chat")
    assert e.value.limit == 2 and e.value.resets_at > timezone.now()
    quota.reserve(user, "writing")  # separate allowance per kind


def test_failed_calls_are_released_and_not_charged(user, settings):
    settings.AI_DAILY_LIMITS = {"free": {"chat": 1, "writing": 1}, "paid": {"chat": 1, "writing": 1}}
    log = quota.reserve(user, "chat")
    quota.release(log, "x")
    assert quota.allowance(user, "chat").used == 0
    quota.reserve(user, "chat")  # allowed again


def test_yesterdays_usage_does_not_count(user, settings):
    settings.AI_DAILY_LIMITS = {"free": {"chat": 1, "writing": 1}, "paid": {"chat": 1, "writing": 1}}
    old = quota.reserve(user, "chat")
    AIUsageLog.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=1, hours=1))
    quota.reserve(user, "chat")


def test_paid_plan_gets_larger_allowance(user, settings):
    settings.AI_DAILY_LIMITS = {"free": {"chat": 1, "writing": 1}, "paid": {"chat": 3, "writing": 1}}
    user.plan = "paid"
    assert quota.allowance(user, "chat").limit == 3


def test_usage_endpoint(settings):
    settings.AI_DAILY_LIMITS = {"free": {"chat": 4, "writing": 2}, "paid": {"chat": 9, "writing": 9}}
    c = client_for("u@example.com")
    data = c.get(f"{V1}/ai/usage/").data
    assert data["chat"]["limit"] == 4 and data["chat"]["remaining"] == 4 and data["writing"]["limit"] == 2


def test_gemini_client_is_built_with_the_configured_timeout(settings, monkeypatch):
    settings.GEMINI_API_KEY = "k"
    settings.AI_TIMEOUT_SECONDS = 7
    seen = {}

    class FakeClient:
        def __init__(self, **kw):
            seen.update(kw)

    monkeypatch.setattr("google.genai.Client", FakeClient)
    GeminiProvider().client  # noqa: B018 - building the client is the behaviour under test
    assert seen["api_key"] == "k" and seen["http_options"].timeout == 7000


# ---- retries on transient upstream failures ----------------------------------------------------------------------

def server_error(code=503):
    return genai_errors.ServerError(code, {"error": {"message": "overloaded", "status": "UNAVAILABLE"}})


class Flaky(FakeModels):
    """Raises the queued errors first, then behaves normally."""

    def __init__(self, errors_first=(), **kw):
        super().__init__(**kw)
        self.errors_first = list(errors_first)

    def _maybe_fail(self):
        if self.errors_first:
            raise self.errors_first.pop(0)

    def generate_content(self, **kw):
        self.calls.append(kw)
        self._maybe_fail()
        return SimpleNamespace(text=self.text)

    def generate_content_stream(self, **kw):
        self.calls.append(kw)
        self._maybe_fail()
        yield from (SimpleNamespace(text=c) for c in self.chunks)


@pytest.fixture
def no_sleep(monkeypatch):
    slept = []
    monkeypatch.setattr("apps.ai.provider.time.sleep", slept.append)
    return slept


def test_json_call_retries_transient_errors_then_succeeds(no_sleep):
    client = SimpleNamespace(models=Flaky([server_error(503), server_error(500)], text='{"a": 1}'))
    assert GeminiProvider(client=client).generate_json("s", "p") == '{"a": 1}'
    assert len(client.models.calls) == 3 and len(no_sleep) == 2 and no_sleep[1] > no_sleep[0]


def test_429_is_retried_but_bad_requests_are_not(no_sleep):
    rate = genai_errors.ClientError(429, {"error": {"message": "slow down", "status": "RESOURCE_EXHAUSTED"}})
    ok = SimpleNamespace(models=Flaky([rate], text="{}"))
    assert GeminiProvider(client=ok).generate_json("s", "p") == "{}"
    bad = genai_errors.ClientError(400, {"error": {"message": "bad", "status": "INVALID_ARGUMENT"}})
    client = SimpleNamespace(models=Flaky([bad], text="{}"))
    with pytest.raises(ProviderError):
        GeminiProvider(client=client).generate_json("s", "p")
    assert len(client.models.calls) == 1 and not no_sleep[1:]  # gave up immediately


def test_retries_are_bounded(no_sleep):
    client = SimpleNamespace(models=Flaky([server_error()] * 5))
    with pytest.raises(ProviderError):
        GeminiProvider(client=client).generate_json("s", "p")
    assert len(client.models.calls) == 3  # first try + 2 retries


def test_stream_retries_only_before_any_text_was_sent(no_sleep):
    client = SimpleNamespace(models=Flaky([server_error()], chunks=["Hi ", "there"]))
    assert "".join(GeminiProvider(client=client).stream("s", [{"role": "user", "content": "x"}])) == "Hi there"
    assert len(client.models.calls) == 2

    class DiesMidStream(FakeModels):
        def generate_content_stream(self, **kw):
            self.calls.append(kw)
            yield SimpleNamespace(text="partial ")
            raise server_error()

    mid = SimpleNamespace(models=DiesMidStream())
    seen = []
    with pytest.raises(ProviderError):
        for chunk in GeminiProvider(client=mid).stream("s", [{"role": "user", "content": "x"}]):
            seen.append(chunk)
    assert seen == ["partial "] and len(mid.models.calls) == 1  # no retry: it would repeat text the student saw


def test_no_retry_once_the_time_budget_is_spent(no_sleep, settings, monkeypatch):
    settings.AI_TIMEOUT_SECONDS = 0
    client = SimpleNamespace(models=Flaky([server_error()] * 3))
    with pytest.raises(ProviderError):
        GeminiProvider(client=client).generate_json("s", "p")
    assert len(client.models.calls) == 1
