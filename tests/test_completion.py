"""Tests for AI code completion (FIM prompt building, response cleaning, manager)."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from ai.completion import (
    CompletionManager,
    _clean_completion,
    build_fim_prompt,
    extract_context,
)
from ai.providers.ollama import OllamaClient

# ---------------------------------------------------------------------------
# build_fim_prompt()
# ---------------------------------------------------------------------------


class TestBuildFimPrompt:
    """Test FIM prompt construction."""

    def test_basic_prompt(self):
        """Should wrap prefix/suffix with FIM tokens."""
        result = build_fim_prompt("def hello():", "\n    pass")
        assert "def hello():" in result
        assert "\n    pass" in result
        assert result.startswith("<")
        assert "fim" in result

    def test_empty_suffix(self):
        """Should handle empty suffix (cursor at end of file)."""
        result = build_fim_prompt("x = 1\n", "")
        assert "x = 1\n" in result

    def test_empty_prefix(self):
        """Should handle empty prefix (cursor at start of file)."""
        result = build_fim_prompt("", "x = 1")
        assert "x = 1" in result


# ---------------------------------------------------------------------------
# extract_context()
# ---------------------------------------------------------------------------


class TestExtractContext:
    """Test prefix/suffix extraction from document text."""

    def test_cursor_mid_line(self):
        """Should split current line at cursor column."""
        text = "hello world\nsecond line"
        prefix, suffix = extract_context(text, cursor_line=0, cursor_col=5)
        assert prefix == "hello"
        assert suffix.startswith(" world")

    def test_cursor_at_line_start(self):
        """Prefix ends with previous lines, suffix starts with current line."""
        text = "line one\nline two\nline three"
        prefix, suffix = extract_context(text, cursor_line=1, cursor_col=0)
        assert prefix == "line one\n"
        assert suffix.startswith("line two")

    def test_cursor_at_end_of_file(self):
        """Suffix should be empty when cursor is at end."""
        text = "only line"
        prefix, suffix = extract_context(text, cursor_line=0, cursor_col=9)
        assert prefix == "only line"
        assert suffix == ""

    def test_limits_prefix_lines(self):
        """Prefix should be capped at PREFIX_MAX_LINES."""
        lines = [f"line {i}" for i in range(200)]
        text = "\n".join(lines)
        prefix, _suffix = extract_context(text, cursor_line=199, cursor_col=0)
        prefix_lines = prefix.split("\n")
        # 100 lines above + empty current-line prefix = 101
        assert len(prefix_lines) <= 101

    def test_limits_suffix_lines(self):
        """Suffix should be capped at SUFFIX_MAX_LINES."""
        lines = [f"line {i}" for i in range(200)]
        text = "\n".join(lines)
        _prefix, suffix = extract_context(text, cursor_line=50, cursor_col=0)
        suffix_lines = suffix.split("\n")
        # rest of current line + 20 below = at most 21
        assert len(suffix_lines) <= 21

    def test_single_line_document(self):
        """Should work with a single-line document."""
        text = "x = 42"
        prefix, suffix = extract_context(text, cursor_line=0, cursor_col=3)
        assert prefix == "x ="
        assert suffix == " 42"


# ---------------------------------------------------------------------------
# _clean_completion()
# ---------------------------------------------------------------------------


class TestCleanCompletion:
    """Test response cleaning and trimming."""

    def test_trims_to_max_lines(self):
        """Should cap output at max_lines."""
        response = "line1\nline2\nline3\nline4\nline5"
        result = _clean_completion(response, max_lines=2)
        assert result.count("\n") <= 1  # At most 2 lines = 1 newline

    def test_strips_endoftext_token(self):
        """Should remove <|endoftext|> artifacts."""
        response = "return x + 1<|endoftext|>\nmore stuff"
        result = _clean_completion(response, max_lines=5)
        assert "<|endoftext|>" not in result
        assert "return x + 1" in result

    def test_strips_fim_end_token(self):
        """Should remove <|fim... artifacts."""
        response = "result = 42<|fim"
        result = _clean_completion(response, max_lines=5)
        assert "result = 42" in result
        assert "<|fim" not in result

    def test_cuts_at_double_newline(self):
        """Should stop at natural code boundary (blank line)."""
        response = "    return x\n\ndef other_func():\n    pass"
        result = _clean_completion(response, max_lines=10)
        assert "    return x" in result
        assert "def other_func" not in result

    def test_cuts_at_new_def(self):
        """Should stop before a new function definition."""
        response = "    x = 1\n    return x\ndef new_func():\n    pass"
        result = _clean_completion(response, max_lines=10)
        assert "def new_func" not in result

    def test_caps_total_characters(self):
        """Should not exceed MAX_SUGGESTION_CHARS."""
        response = "a" * 1000
        result = _clean_completion(response, max_lines=100)
        assert len(result) <= 500

    def test_empty_response(self):
        """Should return empty string for whitespace-only input."""
        assert _clean_completion("   \n  \n", max_lines=3) == ""

    def test_preserves_indentation(self):
        """Should keep leading whitespace (indentation matters in code)."""
        response = "    if True:\n        print('yes')"
        result = _clean_completion(response, max_lines=5)
        assert result.startswith("    if True:")


# ---------------------------------------------------------------------------
# OllamaClient.generate_fim()
# ---------------------------------------------------------------------------


class TestOllamaGenerateFim:
    """Test the FIM generation endpoint."""

    @pytest.mark.asyncio
    async def test_returns_response_text(self):
        """generate_fim() should return the response string."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "    return x + 1"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("ai.providers.ollama.httpx.AsyncClient", return_value=mock_client):
            client = OllamaClient()
            result = await client.generate_fim(model="deepseek-coder:1.3b", prompt="test")

        assert result == "    return x + 1"

    @pytest.mark.asyncio
    async def test_sends_raw_true(self):
        """Payload should include raw=True for FIM format."""
        captured_payload = {}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "ok"}

        mock_client = AsyncMock()

        async def capture_post(url, json=None):
            captured_payload.update(json or {})
            return mock_response

        mock_client.post = AsyncMock(side_effect=capture_post)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("ai.providers.ollama.httpx.AsyncClient", return_value=mock_client):
            client = OllamaClient()
            await client.generate_fim(model="test", prompt="prompt")

        assert captured_payload["raw"] is True
        assert captured_payload["stream"] is False

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self):
        """Should return empty string on HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("ai.providers.ollama.httpx.AsyncClient", return_value=mock_client):
            client = OllamaClient()
            result = await client.generate_fim(model="test", prompt="prompt")

        assert result == ""

    @pytest.mark.asyncio
    async def test_returns_empty_on_connect_error(self):
        """Should return empty string when Ollama is not running."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("ai.providers.ollama.httpx.AsyncClient", return_value=mock_client):
            client = OllamaClient()
            result = await client.generate_fim(model="test", prompt="prompt")

        assert result == ""

    @pytest.mark.asyncio
    async def test_returns_empty_on_timeout(self):
        """Should return empty string on timeout."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("ai.providers.ollama.httpx.AsyncClient", return_value=mock_client):
            client = OllamaClient()
            result = await client.generate_fim(model="test", prompt="prompt")

        assert result == ""


# ---------------------------------------------------------------------------
# CompletionManager
# ---------------------------------------------------------------------------


class TestCompletionManager:
    """Test CompletionManager enable/disable and cancel logic."""

    def test_default_disabled(self, qapp):
        """Manager should start disabled."""
        manager = CompletionManager()
        assert manager.is_enabled() is False

    def test_enable_disable(self, qapp):
        """set_enabled should toggle state."""
        manager = CompletionManager()
        manager.set_enabled(True)
        assert manager.is_enabled() is True
        manager.set_enabled(False)
        assert manager.is_enabled() is False

    def test_request_ignored_when_disabled(self, qapp):
        """request_completion should do nothing when disabled."""
        manager = CompletionManager()
        manager.set_enabled(False)
        # Should not raise or create a task
        manager.request_completion("prefix", "suffix", "model")
        assert manager._current_task is None

    def test_cancel_clears_task(self, qapp):
        """cancel() should clear the current task reference."""
        manager = CompletionManager()
        manager._current_task = MagicMock()
        manager._current_task.done.return_value = False
        manager.cancel()
        assert manager._current_task is None

    def test_set_max_lines_clamps(self, qapp):
        """set_max_lines should clamp to 1-10 range."""
        manager = CompletionManager()
        manager.set_max_lines(0)
        assert manager._max_lines == 1
        manager.set_max_lines(20)
        assert manager._max_lines == 10
        manager.set_max_lines(5)
        assert manager._max_lines == 5
