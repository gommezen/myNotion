"""
AI Worker for running Ollama requests in background thread.
"""

import asyncio

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from ai.providers.ollama import OllamaClient


class AIWorker(QObject):
    """Worker that runs Ollama requests and emits results via signals."""

    # Signals for streaming response
    token_received = pyqtSignal(str)  # Individual token
    generation_finished = pyqtSignal()  # Generation complete
    generation_error = pyqtSignal(str)  # Error message

    def __init__(self, parent=None):
        super().__init__(parent)
        self.client = OllamaClient()
        self._model = "llama3.1"
        self._prompt = ""
        self._context = None

    def set_request(self, model: str, prompt: str, context: str | None = None):
        """Set the request parameters before starting."""
        self._model = model
        self._prompt = prompt
        self._context = context

    def run(self):
        """Run the generation (called from thread)."""
        try:
            asyncio.run(self._async_generate())
        except Exception as e:
            self.generation_error.emit(str(e))

    async def _async_generate(self):
        """Async generation with streaming."""
        try:
            async for token in self.client.generate(
                model=self._model,
                prompt=self._prompt,
                context=self._context,
            ):
                self.token_received.emit(token)
            self.generation_finished.emit()
        except Exception as e:
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

    def generate(self, model: str, prompt: str, context: str | None = None):
        """
        Start an AI generation request.

        Args:
            model: Ollama model name
            prompt: User prompt
            context: Optional context (code selection, file content)
        """
        # Stop any existing generation
        self.stop()

        # Create worker and thread
        self._thread = QThread()
        self._worker = AIWorker()
        self._worker.moveToThread(self._thread)

        # Set request parameters
        self._worker.set_request(model, prompt, context)

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
        if self._thread and self._thread.isRunning():
            self._thread.quit()
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
