"""
AI Worker for running AI requests in background thread.
Supports Ollama (local) and Anthropic (cloud) providers.
"""

import asyncio

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
        self._thread: QThread | None = None
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
        self._thread = QThread()
        self._worker = AIWorker()
        self._worker.moveToThread(self._thread)

        # Set request parameters
        self._worker.set_request(model, prompt, context, mode)

        # Connect signals
        self._worker.token_received.connect(self.token_received.emit)
        self._worker.generation_finished.connect(self._on_finished)
        self._worker.generation_error.connect(self._on_error)

        # Start when thread starts
        self._thread.started.connect(self._worker.run)

        # Start the thread
        self._thread.start()

    def stop(self):
        """Stop current generation."""
        # Signal the worker to cancel
        if self._worker:
            self._worker.cancel()

        # Wait for thread to finish (with timeout)
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            if not self._thread.wait(2000):  # 2 second timeout
                # Force terminate if it doesn't stop gracefully
                self._thread.terminate()
                self._thread.wait(1000)

        self._cleanup()

    def _on_finished(self):
        """Handle generation complete."""
        self.generation_finished.emit()
        self._cleanup()

    def _on_error(self, error: str):
        """Handle generation error."""
        self.generation_error.emit(error)
        self._cleanup()

    def _cleanup(self):
        """Clean up thread and worker."""
        if self._thread:
            if self._thread.isRunning():
                self._thread.quit()
                self._thread.wait(1000)
            self._thread.deleteLater()
            self._thread = None

        if self._worker:
            self._worker.deleteLater()
            self._worker = None
