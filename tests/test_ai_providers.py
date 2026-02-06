"""Tests for Ollama and Anthropic provider streaming."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from ai.providers.anthropic import AnthropicClient
from ai.providers.ollama import (
    CODING_SYSTEM_PROMPT,
    WRITING_SYSTEM_PROMPT,
    OllamaClient,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ollama_lines(*tokens: str, done: bool = True) -> list[str]:
    """Build Ollama NDJSON response lines."""
    lines = [json.dumps({"response": t, "done": False}) for t in tokens]
    if done:
        lines.append(json.dumps({"response": "", "done": True}))
    return lines


def _make_anthropic_lines(*tokens: str) -> list[str]:
    """Build Anthropic SSE response lines."""
    lines = []
    for t in tokens:
        event = {"type": "content_block_delta", "delta": {"type": "text_delta", "text": t}}
        lines.append(f"data: {json.dumps(event)}")
    lines.append("data: [DONE]")
    return lines


# ---------------------------------------------------------------------------
# OllamaClient.generate()
# ---------------------------------------------------------------------------


class TestOllamaGenerate:
    """Test OllamaClient streaming generation."""

    @pytest.mark.asyncio
    async def test_streams_tokens(self):
        """generate() should yield tokens from mocked HTTP response."""
        lines = _make_ollama_lines("Hello", " world")

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.aiter_lines = AsyncMock(
            return_value=AsyncMock(__aiter__=lambda s: s, __anext__=None)
        )

        # Build a proper async iterator for lines
        async def aiter_lines():
            for line in lines:
                yield line

        mock_response.aiter_lines = aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("ai.providers.ollama.httpx.AsyncClient", return_value=mock_client):
            client = OllamaClient()
            tokens = []
            async for token in client.generate(model="llama3.2", prompt="Hello"):
                tokens.append(token)

        assert "Hello" in tokens
        assert " world" in tokens

    @pytest.mark.asyncio
    async def test_coding_mode_uses_coding_prompt(self):
        """Coding mode should use CODING_SYSTEM_PROMPT."""
        captured_payload = {}

        async def aiter_lines():
            for line in _make_ollama_lines("ok"):
                yield line

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.aiter_lines = aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()

        def capture_stream(method, url, json=None):
            captured_payload.update(json or {})
            return mock_response

        mock_client.stream = MagicMock(side_effect=capture_stream)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("ai.providers.ollama.httpx.AsyncClient", return_value=mock_client):
            client = OllamaClient()
            async for _ in client.generate(model="test", prompt="hi", mode="coding"):
                pass

        assert captured_payload["system"] == CODING_SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_writing_mode_uses_writing_prompt(self):
        """Writing mode should use WRITING_SYSTEM_PROMPT."""
        captured_payload = {}

        async def aiter_lines():
            for line in _make_ollama_lines("ok"):
                yield line

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.aiter_lines = aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()

        def capture_stream(method, url, json=None):
            captured_payload.update(json or {})
            return mock_response

        mock_client.stream = MagicMock(side_effect=capture_stream)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("ai.providers.ollama.httpx.AsyncClient", return_value=mock_client):
            client = OllamaClient()
            async for _ in client.generate(model="test", prompt="hi", mode="writing"):
                pass

        assert captured_payload["system"] == WRITING_SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_context_injection_format(self):
        """Context should be formatted as Context:\\n```\\ncode\\n```."""
        captured_payload = {}

        async def aiter_lines():
            for line in _make_ollama_lines("ok"):
                yield line

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.aiter_lines = aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()

        def capture_stream(method, url, json=None):
            captured_payload.update(json or {})
            return mock_response

        mock_client.stream = MagicMock(side_effect=capture_stream)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("ai.providers.ollama.httpx.AsyncClient", return_value=mock_client):
            client = OllamaClient()
            async for _ in client.generate(model="test", prompt="explain", context="x = 1"):
                pass

        prompt = captured_payload["prompt"]
        assert "Context:\n```\nx = 1\n```" in prompt
        assert "User request: explain" in prompt

    @pytest.mark.asyncio
    async def test_connect_error(self):
        """ConnectError should yield a user-friendly error message."""
        with patch(
            "ai.providers.ollama.httpx.AsyncClient",
            side_effect=httpx.ConnectError("refused"),
        ):
            client = OllamaClient()
            tokens = []
            async for token in client.generate(model="test", prompt="hi"):
                tokens.append(token)

        assert any("Cannot connect to Ollama" in t for t in tokens)

    @pytest.mark.asyncio
    async def test_timeout_error(self):
        """TimeoutException should yield a timeout error message."""
        with patch(
            "ai.providers.ollama.httpx.AsyncClient",
            side_effect=httpx.TimeoutException("timeout"),
        ):
            client = OllamaClient()
            tokens = []
            async for token in client.generate(model="test", prompt="hi"):
                tokens.append(token)

        assert any("timed out" in t for t in tokens)

    @pytest.mark.asyncio
    async def test_http_400_model_not_found(self):
        """HTTP 400 should yield model not found message."""

        mock_response = AsyncMock()
        mock_response.status_code = 400
        mock_response.aread = AsyncMock()
        mock_response.json = MagicMock(return_value={"error": "model not found"})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("ai.providers.ollama.httpx.AsyncClient", return_value=mock_client):
            client = OllamaClient()
            tokens = []
            async for token in client.generate(model="bad-model", prompt="hi"):
                tokens.append(token)

        assert any("model not found" in t for t in tokens)


# ---------------------------------------------------------------------------
# OllamaClient.is_available()
# ---------------------------------------------------------------------------


class TestOllamaAvailability:
    """Test is_available() health check."""

    @pytest.mark.asyncio
    async def test_available_when_server_running(self):
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("ai.providers.ollama.httpx.AsyncClient", return_value=mock_client):
            client = OllamaClient()
            assert await client.is_available() is True

    @pytest.mark.asyncio
    async def test_unavailable_when_server_down(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("ai.providers.ollama.httpx.AsyncClient", return_value=mock_client):
            client = OllamaClient()
            assert await client.is_available() is False


# ---------------------------------------------------------------------------
# AnthropicClient.generate()
# ---------------------------------------------------------------------------


class TestAnthropicGenerate:
    """Test AnthropicClient streaming generation."""

    @pytest.mark.asyncio
    async def test_streams_tokens(self):
        """generate() should yield tokens from mocked SSE response."""
        lines = _make_anthropic_lines("Hello", " world")

        async def aiter_lines():
            for line in lines:
                yield line

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.aiter_lines = aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("ai.providers.anthropic.httpx.AsyncClient", return_value=mock_client),
            patch.object(AnthropicClient, "_get_api_key", return_value="sk-test-key"),
        ):
            client = AnthropicClient()
            tokens = []
            async for token in client.generate(prompt="Hello"):
                tokens.append(token)

        assert "Hello" in tokens
        assert " world" in tokens

    @pytest.mark.asyncio
    async def test_system_prompt_coding_mode(self):
        """Coding mode should use coding system prompt."""
        captured_payload = {}
        lines = _make_anthropic_lines("ok")

        async def aiter_lines():
            for line in lines:
                yield line

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.aiter_lines = aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()

        def capture_stream(method, url, headers=None, json=None):
            captured_payload.update(json or {})
            return mock_response

        mock_client.stream = MagicMock(side_effect=capture_stream)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("ai.providers.anthropic.httpx.AsyncClient", return_value=mock_client),
            patch.object(AnthropicClient, "_get_api_key", return_value="sk-test-key"),
        ):
            client = AnthropicClient()
            async for _ in client.generate(prompt="hi", mode="coding"):
                pass

        assert "coding" in captured_payload["system"].lower()

    @pytest.mark.asyncio
    async def test_missing_api_key(self):
        """Missing API key should yield an error message."""
        with patch.object(AnthropicClient, "_get_api_key", return_value=""):
            client = AnthropicClient()
            tokens = []
            async for token in client.generate(prompt="hi"):
                tokens.append(token)

        assert any("API key not set" in t for t in tokens)

    @pytest.mark.asyncio
    async def test_401_invalid_key(self):
        """HTTP 401 should yield invalid key error."""
        mock_response = AsyncMock()
        mock_response.status_code = 401
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("ai.providers.anthropic.httpx.AsyncClient", return_value=mock_client),
            patch.object(AnthropicClient, "_get_api_key", return_value="sk-bad"),
        ):
            client = AnthropicClient()
            tokens = []
            async for token in client.generate(prompt="hi"):
                tokens.append(token)

        assert any("Invalid API key" in t for t in tokens)

    @pytest.mark.asyncio
    async def test_429_rate_limited(self):
        """HTTP 429 should yield rate limited error."""
        mock_response = AsyncMock()
        mock_response.status_code = 429
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("ai.providers.anthropic.httpx.AsyncClient", return_value=mock_client),
            patch.object(AnthropicClient, "_get_api_key", return_value="sk-key"),
        ):
            client = AnthropicClient()
            tokens = []
            async for token in client.generate(prompt="hi"):
                tokens.append(token)

        assert any("Rate limited" in t for t in tokens)

    @pytest.mark.asyncio
    async def test_connect_error(self):
        """ConnectError should yield a connection error message."""
        with (
            patch(
                "ai.providers.anthropic.httpx.AsyncClient",
                side_effect=httpx.ConnectError("refused"),
            ),
            patch.object(AnthropicClient, "_get_api_key", return_value="sk-key"),
        ):
            client = AnthropicClient()
            tokens = []
            async for token in client.generate(prompt="hi"):
                tokens.append(token)

        assert any("connect" in t.lower() for t in tokens)

    @pytest.mark.asyncio
    async def test_timeout_error(self):
        """TimeoutException should yield a timeout error message."""
        with (
            patch(
                "ai.providers.anthropic.httpx.AsyncClient",
                side_effect=httpx.TimeoutException("timeout"),
            ),
            patch.object(AnthropicClient, "_get_api_key", return_value="sk-key"),
        ):
            client = AnthropicClient()
            tokens = []
            async for token in client.generate(prompt="hi"):
                tokens.append(token)

        assert any("timed out" in t for t in tokens)
