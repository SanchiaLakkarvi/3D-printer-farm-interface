"""Provider-independent boundary for grounded help-chat completion."""

from __future__ import annotations

from typing import Protocol


class HelpProviderPort(Protocol):
    async def complete(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, str]],
        max_tokens: int,
    ) -> str:
        """Return one assistant reply for the supplied grounded conversation."""
