"""Public student troubleshooting chat endpoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.adapters.help.anthropic import AnthropicHelpAdapter
from app.adapters.help.port import HelpProviderPort
from app.core.config import settings
from app.schemas.help import HelpChatRequest, HelpChatResponse
from app.services.help_service import InMemoryRateLimiter, answer_help_question

router = APIRouter(prefix="/help", tags=["help"])

_rate_limiter = InMemoryRateLimiter(
    max_requests=settings.help_rate_limit_requests,
    window_seconds=settings.help_rate_limit_window_seconds,
)


async def get_help_provider() -> AsyncIterator[HelpProviderPort]:
    provider = AnthropicHelpAdapter(
        api_key=settings.anthropic_api_key,
        model=settings.anthropic_model,
        timeout_s=settings.help_provider_timeout_s,
    )
    try:
        yield provider
    finally:
        await provider.close()


def get_help_rate_limiter() -> InMemoryRateLimiter:
    return _rate_limiter


@router.post("/chat", response_model=HelpChatResponse)
async def chat(
    body: HelpChatRequest,
    request: Request,
    provider: Annotated[HelpProviderPort, Depends(get_help_provider)],
    rate_limiter: Annotated[InMemoryRateLimiter, Depends(get_help_rate_limiter)],
) -> HelpChatResponse:
    """Answer student troubleshooting questions without requiring a session."""
    client_ip = request.client.host if request.client else "unknown"
    rate_limiter.check(client_ip)
    message = await answer_help_question(
        body,
        provider=provider,
        docs_root=settings.help_docs_root,
        max_message_chars=settings.help_max_message_chars,
        max_history_messages=settings.help_max_history_messages,
        max_output_tokens=settings.help_max_output_tokens,
    )
    return HelpChatResponse(message=message)
