"""
Async code completion manager for inline AI suggestions.

Uses FIM (fill-in-middle) prompts via Ollama for Copilot-style ghost text.
Runs on the qasync event loop — no threads needed.
"""

import asyncio
import logging

from PyQt6.QtCore import QObject, pyqtSignal

from ai.providers.ollama import OllamaClient

logger = logging.getLogger(__name__)

# FIM special tokens (DeepSeek Coder format, also works with CodeGemma/Qwen)
FIM_BEGIN = "<\uff5cfim\u2581begin\uff5c>"
FIM_HOLE = "<\uff5cfim\u2581hole\uff5c>"
FIM_END = "<\uff5cfim\u2581end\uff5c>"

# Context window sizes
PREFIX_MAX_LINES = 100
SUFFIX_MAX_LINES = 20


def build_fim_prompt(prefix: str, suffix: str) -> str:
    """Build a FIM prompt from code before and after the cursor.

    Args:
        prefix: Code before the cursor (up to 100 lines)
        suffix: Code after the cursor (up to 20 lines)

    Returns:
        Formatted FIM prompt string.
    """
    return f"{FIM_BEGIN}{prefix}{FIM_HOLE}{suffix}{FIM_END}"


def extract_context(text: str, cursor_line: int, cursor_col: int) -> tuple[str, str]:
    """Extract prefix and suffix from document text around the cursor.

    Args:
        text: Full document text
        cursor_line: 0-based line number of cursor
        cursor_col: 0-based column number of cursor

    Returns:
        Tuple of (prefix, suffix) strings.
    """
    lines = text.split("\n")

    # Prefix: up to PREFIX_MAX_LINES lines above + current line up to cursor
    start_line = max(0, cursor_line - PREFIX_MAX_LINES)
    prefix_lines = lines[start_line:cursor_line]
    if cursor_line < len(lines):
        prefix_lines.append(lines[cursor_line][:cursor_col])
    prefix = "\n".join(prefix_lines)

    # Suffix: rest of current line after cursor + up to SUFFIX_MAX_LINES lines below
    suffix_parts = []
    if cursor_line < len(lines):
        suffix_parts.append(lines[cursor_line][cursor_col:])
    end_line = min(len(lines), cursor_line + 1 + SUFFIX_MAX_LINES)
    suffix_parts.extend(lines[cursor_line + 1 : end_line])
    suffix = "\n".join(suffix_parts)

    return prefix, suffix


# Maximum characters in a single suggestion
MAX_SUGGESTION_CHARS = 500

# Stop tokens that indicate end of a logical code block
_STOP_PATTERNS = ("\n\n", "\ndef ", "\nclass ", "\n# ", "\nif __name__")


def _clean_completion(response: str, max_lines: int) -> str:
    """Clean and trim a raw FIM response to a reasonable suggestion.

    Args:
        response: Raw model output
        max_lines: Maximum lines to keep

    Returns:
        Cleaned suggestion text, or empty string.
    """
    text = response

    # Strip common FIM end-of-sequence artifacts
    for marker in ("<|endoftext|>", "<|fim", "</s>", "<|end"):
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx]

    # Cut at natural code boundaries (double newline, new top-level def/class)
    for pattern in _STOP_PATTERNS:
        idx = text.find(pattern)
        if idx > 0:
            text = text[:idx]
            break

    # Trim to max lines
    lines = text.split("\n")
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    text = "\n".join(lines)

    # Cap total characters
    if len(text) > MAX_SUGGESTION_CHARS:
        text = text[:MAX_SUGGESTION_CHARS]
        # Don't cut mid-line — trim back to last newline
        last_nl = text.rfind("\n")
        if last_nl > 0:
            text = text[:last_nl]

    return text.rstrip()


class CompletionManager(QObject):
    """Manages async code completion requests.

    Sends FIM prompts to Ollama and emits suggestions as ghost text.
    Only one request runs at a time — new requests cancel the previous one.
    """

    suggestion_ready = pyqtSignal(str)  # Ghost text to display
    suggestion_cleared = pyqtSignal()  # Clear ghost text

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._client = OllamaClient()
        self._enabled = False
        self._current_task: asyncio.Task | None = None
        self._max_lines = 3

    def is_enabled(self) -> bool:
        """Check if completion is enabled."""
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable completion."""
        self._enabled = enabled
        if not enabled:
            self.cancel()

    def set_max_lines(self, lines: int) -> None:
        """Set the maximum number of suggestion lines."""
        self._max_lines = max(1, min(10, lines))

    def cancel(self) -> None:
        """Cancel any in-flight completion request."""
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            self._current_task = None
        self.suggestion_cleared.emit()

    def request_completion(self, prefix: str, suffix: str, model: str) -> None:
        """Request a code completion from Ollama.

        Cancels any previous pending request before starting a new one.

        Args:
            prefix: Code before cursor
            suffix: Code after cursor
            model: Ollama model name (e.g., "deepseek-coder:1.3b")
        """
        if not self._enabled:
            return

        # Cancel previous request
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()

        prompt = build_fim_prompt(prefix, suffix)

        try:
            loop = asyncio.get_event_loop()
            self._current_task = loop.create_task(self._run_completion(model, prompt))
        except RuntimeError:
            logger.debug("No event loop available for completion request")

    async def _run_completion(self, model: str, prompt: str) -> None:
        """Run a single completion request."""
        try:
            response = await self._client.generate_fim(model=model, prompt=prompt)

            if not response or not response.strip():
                return

            trimmed = _clean_completion(response, self._max_lines)

            if trimmed:
                self.suggestion_ready.emit(trimmed)
        except asyncio.CancelledError:
            pass  # Expected when a new request supersedes this one
        except Exception:
            logger.debug("Completion request failed", exc_info=True)
