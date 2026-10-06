"""Bounded Anthropic Messages API adapter for public authentication help."""

from __future__ import annotations

import httpx

from app.core.exceptions import ServiceUnavailableError


class AnthropicHelpAdapter:
    """Call Anthropic without exposing provider details to API clients."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_s: float,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url="https://api.anthropic.com",
            timeout=httpx.Timeout(timeout_s),
        )

    async def complete(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, str]],
        max_tokens: int,
    ) -> str:
        if not self._api_key:
            raise ServiceUnavailableError()

        try:
            response = await self._client.post(
                "/v1/messages",
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self._model,
                    "max_tokens": max_tokens,
                    "system": system_prompt,
                    "messages": messages,
                },
            )
            response.raise_for_status()
            body = response.json()
            content = body.get("content")
            if not isinstance(content, list):
                raise ValueError("Missing response content")
            text = "".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict)
                and block.get("type") == "text"
                and isinstance(block.get("text"), str)
            ).strip()
            if not text:
                raise ValueError("Empty response content")
            return text
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise ServiceUnavailableError() from exc

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()
