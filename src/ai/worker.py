"""
AI Worker for running AI requests in background thread.
Supports Ollama (local) and Anthropic (cloud) providers.
"""

import asyncio
import contextlib

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from ai.providers.anthropic import AnthropicClient
from ai.providers.ollama import OllamaClient


class AIWorker(QObject):
    """Worker that runs AI requests and emits results via signals."""

    # Signals for streaming response
    token_received = pyqtSignal(str)  # Individual token
    generation_finished = pyqtSignal()  # Generation complete
    generation_error = pyqtSignal(str)  # Error message

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ollama_client = OllamaClient()
        self.anthropic_client = AnthropicClient()
        self._model = "llama3.1"
        self._prompt = ""
        self._context = None
        self._mode = "coding"
        self._cancelled = False

    def set_request(
        self, model: str, prompt: str, context: str | None = None, mode: str = "coding"
    ):
        """Set the request parameters before starting.

        Args:
            model: Ollama model name
            prompt: User prompt
            context: Optional context (code selection, file content)
            mode: Layout mode ("coding" or "writing")
        """
        self._model = model
        self._prompt = prompt
        self._context = context
        self._mode = mode
        self._cancelled = False

    def cancel(self):
        """Request cancellation of the current generation."""
        self._cancelled = True

    def run(self):
        """Run the generation (called from thread)."""
        try:
            asyncio.run(self._async_generate())
        except asyncio.CancelledError:
            pass  # Expected when cancelled
        except Exception as e:
            if not self._cancelled:
                self.generation_error.emit(str(e))

    def _is_anthropic_model(self, model: str) -> bool:
        """Check if the model is an Anthropic/Claude model."""
        return "claude" in model.lower() or "haiku" in model.lower()

    async def _async_generate(self):
        """Async generation with streaming."""
        try:
            # Choose provider based on model
            if self._is_anthropic_model(self._model):
                # Use Anthropic API - map model ID to actual API model
                api_model = "claude-3-haiku-20240307"  # Default to Haiku
                client = self.anthropic_client
            else:
                # Use Ollama for local models
                api_model = self._model
                client = self.ollama_client

            async for token in client.generate(
                model=api_model,
                prompt=self._prompt,
                context=self._context,
                mode=self._mode,
            ):
                if self._cancelled:
                    break
                self.token_received.emit(token)
            if not self._cancelled:
                self.generation_finished.emit()
        except Exception as e:
            if not self._cancelled:
                self.generation_error.emit(str(e))


class _WorkerThread(QThread):
    """QThread that runs an AIWorker directly, without a Qt event loop.

    The default QThread.run() calls exec() which starts an event loop that
    never exits. By overriding run() to call worker.run() directly, the
    thread exits naturally when the worker finishes, and the 'finished'
    signal fires reliably.
    """

    def __init__(self, worker: AIWorker):
        super().__init__()
        self._worker = worker

    def run(self):
        """Execute the worker and exit — no event loop needed."""
        self._worker.run()


class AIManager(QObject):
    """
    Manages AI requests with proper thread handling.

    Usage:
        manager = AIManager()
        manager.token_received.connect(on_token)
        manager.generation_finished.connect(on_done)
        manager.generate("llama3.1", "Explain this code", context="def foo(): pass")
    """

    # Forward signals from worker
    token_received = pyqtSignal(str)
    generation_finished = pyqtSignal()
    generation_error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread: _WorkerThread | None = None
        self._worker: AIWorker | None = None

    def generate(self, model: str, prompt: str, context: str | None = None, mode: str = "coding"):
        """
        Start an AI generation request.

        Args:
            model: Ollama model name
            prompt: User prompt
            context: Optional context (code selection, file content)
            mode: Layout mode ("coding" or "writing")
        """
        # Stop any existing generation
        self.stop()

        # Create worker and thread
        self._worker = AIWorker()
        self._thread = _WorkerThread(self._worker)

        # Set request parameters
        self._worker.set_request(model, prompt, context, mode)

        # Connect worker signals — forward to manager
        self._worker.token_received.connect(self.token_received.emit)
        self._worker.generation_finished.connect(self.generation_finished.emit)
        self._worker.generation_error.connect(self.generation_error.emit)

        # Clear references when thread finishes naturally
        self._thread.finished.connect(self._clear_refs)

        # Start the thread (calls _WorkerThread.run → worker.run)
        self._thread.start()

    def stop(self):
        """Stop current generation."""
        # Signal the worker to cancel — this makes the async loop exit early
        if self._worker:
            self._worker.cancel()

        thread = self._thread

        # Disconnect finished signal so old thread won't clear new refs
        if thread:
            with contextlib.suppress(TypeError):
                thread.finished.disconnect(self._clear_refs)

        # Wait for thread to finish naturally (asyncio.run exits after cancel)
        if thread and thread.isRunning() and not thread.wait(5000):
            thread.terminate()
            thread.wait(2000)

        self._clear_refs()

    def _clear_refs(self):
        """Clear references to thread and worker (Qt handles actual deletion)."""
        self._worker = None
        self._thread = None
