from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app.adapters.help.anthropic import AnthropicHelpAdapter
from app.api.v1.help import get_help_provider, get_help_rate_limiter
from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError
from app.main import app
from app.schemas.help import HelpChatRequest, HelpHistoryMessage
from app.services.help_service import (
    SECRET_REFUSAL,
    InMemoryRateLimiter,
    answer_help_question,
    load_help_document,
)


class RecordingProvider:
    def __init__(self, reply: str = "Use the six-digit code from your email.") -> None:
        self.reply = reply
        self.calls: list[dict] = []

    async def complete(self, **kwargs) -> str:
        self.calls.append(kwargs)
        return self.reply


@pytest.fixture(autouse=True)
def _reset_help_dependencies():
    app.dependency_overrides.clear()
    load_help_document.cache_clear()
    yield
    app.dependency_overrides.clear()
    load_help_document.cache_clear()


def _unlimited_limiter() -> InMemoryRateLimiter:
    return InMemoryRateLimiter(max_requests=100, window_seconds=60)


def test_public_chat_returns_grounded_provider_reply(
    client: TestClient, tmp_path, monkeypatch
) -> None:
    (tmp_path / "student-help.md").write_text(
        "Students verify with a six-digit email code.", encoding="utf-8"
    )
    monkeypatch.setattr(settings, "help_docs_root", str(tmp_path))
    provider = RecordingProvider()
    app.dependency_overrides[get_help_provider] = lambda: provider
    app.dependency_overrides[get_help_rate_limiter] = _unlimited_limiter

    response = client.post(
        "/api/help/chat",
        json={
            "message": "How do I verify?",
            "history": [
                {"role": "user", "content": "I signed up."},
                {"role": "assistant", "content": "Check your email."},
            ],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Use the six-digit code from your email."
    }
    assert len(provider.calls) == 1
    assert "Students verify with a six-digit email code." in provider.calls[0][
        "system_prompt"
    ]
    assert provider.calls[0]["messages"][-1] == {
        "role": "user",
        "content": "How do I verify?",
    }


def test_missing_api_key_returns_structured_503(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    app.dependency_overrides[get_help_rate_limiter] = _unlimited_limiter

    response = client.post("/api/help/chat", json={"message": "How do I sign in?"})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "HELP_UNAVAILABLE"
    assert "temporarily unavailable" in response.json()["detail"]["message"]


@pytest.mark.asyncio
async def test_provider_timeout_maps_to_structured_app_error() -> None:
    async def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("provider timed out", request=request)

    client = httpx.AsyncClient(
        base_url="https://api.anthropic.com",
        transport=httpx.MockTransport(timeout),
    )
    provider = AnthropicHelpAdapter(
        api_key="test-key",
        model="test-model",
        timeout_s=0.1,
        client=client,
    )

    with pytest.raises(ServiceUnavailableError) as exc_info:
        await provider.complete(
            system_prompt="Reference only",
            messages=[{"role": "user", "content": "Help"}],
            max_tokens=20,
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "HELP_UNAVAILABLE"
    assert "provider timed out" not in exc_info.value.detail["message"]
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "secret",
    [
        "My password is hunter2",
        "https://example.test/confirm?token_hash=secret-value&type=signup",
        "https://project.supabase.co/auth/v1/verify?token=secret&type=signup",
        "My verification code is 123456",
        "eyJabcdefghijk.abcdefghijklmnop.abcdefghijklmnop",
    ],
)
async def test_secrets_are_refused_without_provider_call(tmp_path, secret: str) -> None:
    (tmp_path / "student-help.md").write_text("Safe help.", encoding="utf-8")
    provider = RecordingProvider()

    answer = await answer_help_question(
        HelpChatRequest(message=secret),
        provider=provider,
        docs_root=str(tmp_path),
        max_message_chars=1000,
        max_history_messages=6,
        max_output_tokens=100,
    )

    assert answer == SECRET_REFUSAL
    assert provider.calls == []


def test_oversize_history_returns_bad_request(client: TestClient) -> None:
    provider = RecordingProvider()
    app.dependency_overrides[get_help_provider] = lambda: provider
    app.dependency_overrides[get_help_rate_limiter] = _unlimited_limiter

    response = client.post(
        "/api/help/chat",
        json={
            "message": "Help",
            "history": [
                {"role": "user", "content": f"message {index}"}
                for index in range(settings.help_max_history_messages + 1)
            ],
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "HELP_HISTORY_TOO_LONG"
    assert provider.calls == []


def test_public_route_rate_limit_returns_429(client: TestClient) -> None:
    provider = RecordingProvider()
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)
    app.dependency_overrides[get_help_provider] = lambda: provider
    app.dependency_overrides[get_help_rate_limiter] = lambda: limiter

    first = client.post("/api/help/chat", json={"message": "First question"})
    second = client.post("/api/help/chat", json={"message": "Second question"})

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"]["code"] == "RATE_LIMITED"
    assert "try again" in second.json()["detail"]["message"].lower()
