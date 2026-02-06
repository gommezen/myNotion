"""
Anthropic API client for Claude models (Haiku, Sonnet, Opus).
"""

import asyncio
from collections.abc import AsyncGenerator

import httpx

from core.settings import SettingsManager


class AnthropicClient:
    """Client for Anthropic Claude API with streaming support."""

    BASE_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"

    def __init__(self):
        self.settings = SettingsManager()

    def _get_api_key(self) -> str:
        """Get API key from settings."""
        return self.settings.get_anthropic_api_key()

    async def generate(
        self,
        model: str = "claude-3-haiku-20240307",
        prompt: str = "",
        context: str | None = None,
        mode: str = "coding",
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from Anthropic API.

        Args:
            model: Model ID (e.g., claude-3-haiku-20240307)
            prompt: User prompt
            context: Optional context
            mode: Layout mode (coding or writing)

        Yields:
            Text tokens as they arrive
        """
        api_key = self._get_api_key()
        if not api_key:
            yield "[Error: Anthropic API key not set. Go to Edit → Settings to add your API key.]"
            return

        # Build the message content
        if context:
            user_content = f"Context:\n```\n{context}\n```\n\nUser request: {prompt}"
        else:
            user_content = prompt

        # System prompt based on mode
        if mode == "coding":
            system = "You are a helpful coding assistant. Be concise and provide working code examples when appropriate."
        else:
            system = "You are a helpful writing assistant. Be clear, concise, and helpful."

        headers = {
            "x-api-key": api_key,
            "anthropic-version": self.API_VERSION,
            "content-type": "application/json",
        }

        payload = {
            "model": model,
            "max_tokens": 4096,
            "system": system,
            "messages": [{"role": "user", "content": user_content}],
            "stream": True,
        }

        try:
            async with (
                httpx.AsyncClient(timeout=60.0) as client,
                client.stream("POST", self.BASE_URL, headers=headers, json=payload) as response,
            ):
                if response.status_code == 401:
                    yield "[Error: Invalid API key. Check your Anthropic API key in Settings.]"
                    return
                elif response.status_code == 429:
                    yield "[Error: Rate limited. Please wait and try again.]"
                    return
                elif response.status_code != 200:
                    yield f"[Error: API returned status {response.status_code}]"
                    return

                # Process SSE stream
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    data = line[6:]  # Remove "data: " prefix
                    if data == "[DONE]":
                        break

                    try:
                        import json

                        event = json.loads(data)
                        event_type = event.get("type", "")

                        if event_type == "content_block_delta":
                            delta = event.get("delta", {})
                            if delta.get("type") == "text_delta":
                                text = delta.get("text", "")
                                if text:
                                    yield text
                    except json.JSONDecodeError:
                        continue

        except httpx.TimeoutException:
            yield "[Error: Request timed out. Please try again.]"
        except httpx.ConnectError:
            yield "[Error: Could not connect to Anthropic API. Check your internet connection.]"
        except asyncio.CancelledError:
            raise
        except Exception as e:
            yield f"[Error: {e!s}]"
