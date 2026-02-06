"""Tests for AIWorker and AIManager signal flow."""

from unittest.mock import MagicMock, patch

from ai.worker import AIManager, AIWorker

# ---------------------------------------------------------------------------
# AIWorker._is_anthropic_model()
# ---------------------------------------------------------------------------


class TestIsAnthropicModel:
    """Verify model detection for Anthropic/Claude models."""

    def test_claude_detected(self):
        worker = AIWorker()
        assert worker._is_anthropic_model("claude-3-haiku-20240307") is True

    def test_haiku_detected(self):
        worker = AIWorker()
        assert worker._is_anthropic_model("claude-haiku") is True

    def test_haiku_case_insensitive(self):
        worker = AIWorker()
        assert worker._is_anthropic_model("Claude-Haiku") is True

    def test_ollama_model_not_detected(self):
        worker = AIWorker()
        assert worker._is_anthropic_model("llama3.2:latest") is False

    def test_qwen_not_detected(self):
        worker = AIWorker()
        assert worker._is_anthropic_model("qwen2.5:7b-instruct-q4_0") is False

    def test_gemma_not_detected(self):
        worker = AIWorker()
        assert worker._is_anthropic_model("gemma3:4b") is False


# ---------------------------------------------------------------------------
# AIWorker.set_request() and cancel()
# ---------------------------------------------------------------------------


class TestAIWorkerSetup:
    """Test AIWorker request configuration and cancellation."""

    def test_set_request(self):
        worker = AIWorker()
        worker.set_request("llama3.2", "Explain this", "code_context", "coding")

        assert worker._model == "llama3.2"
        assert worker._prompt == "Explain this"
        assert worker._context == "code_context"
        assert worker._mode == "coding"
        assert worker._cancelled is False

    def test_cancel_sets_flag(self):
        worker = AIWorker()
        worker.cancel()
        assert worker._cancelled is True

    def test_set_request_resets_cancelled(self):
        worker = AIWorker()
        worker.cancel()
        assert worker._cancelled is True

        worker.set_request("model", "prompt")
        assert worker._cancelled is False


# ---------------------------------------------------------------------------
# AIManager.generate() and stop()
# ---------------------------------------------------------------------------


class TestAIManagerLifecycle:
    """Test AIManager thread/worker lifecycle."""

    def test_generate_creates_thread_and_worker(self, qapp):
        manager = AIManager()

        with patch.object(AIWorker, "run"):
            manager.generate("llama3.2", "Hello")

        assert manager._thread is not None
        assert manager._worker is not None

        # Cleanup
        manager.stop()

    def test_stop_cleans_up(self, qapp):
        manager = AIManager()

        with patch.object(AIWorker, "run"):
            manager.generate("llama3.2", "Hello")

        manager.stop()

        assert manager._thread is None
        assert manager._worker is None

    def test_generate_stops_previous(self, qapp):
        """Calling generate() again should stop the previous generation."""
        manager = AIManager()

        with patch.object(AIWorker, "run"):
            manager.generate("llama3.2", "First")
            first_thread = manager._thread

            manager.generate("llama3.2", "Second")

        # First thread should have been cleaned up
        assert manager._thread is not first_thread

        manager.stop()


# ---------------------------------------------------------------------------
# Signal forwarding
# ---------------------------------------------------------------------------


class TestSignalForwarding:
    """Test that worker signals are forwarded through manager."""

    def test_token_signal_forwarded(self, qapp, qtbot):
        manager = AIManager()

        with qtbot.waitSignal(manager.token_received, timeout=2000) as blocker:
            # Directly emit from a worker to test forwarding
            manager._thread = MagicMock()
            manager._worker = AIWorker()
            manager._worker.token_received.connect(manager.token_received.emit)
            manager._worker.token_received.emit("hello")

        assert blocker.args == ["hello"]

        # Cleanup
        manager._worker.deleteLater()
        manager._thread = None
        manager._worker = None

    def test_finished_signal_forwarded(self, qapp, qtbot):
        manager = AIManager()

        with qtbot.waitSignal(manager.generation_finished, timeout=2000):
            manager._thread = MagicMock()
            manager._thread.isRunning = MagicMock(return_value=False)
            manager._worker = AIWorker()
            manager._worker.generation_finished.connect(manager._on_finished)
            manager._worker.generation_finished.emit()

        # After finished, cleanup should have run
        assert manager._worker is None

    def test_error_signal_forwarded(self, qapp, qtbot):
        manager = AIManager()

        with qtbot.waitSignal(manager.generation_error, timeout=2000) as blocker:
            manager._thread = MagicMock()
            manager._thread.isRunning = MagicMock(return_value=False)
            manager._worker = AIWorker()
            manager._worker.generation_error.connect(manager._on_error)
            manager._worker.generation_error.emit("Something went wrong")

        assert blocker.args == ["Something went wrong"]
        assert manager._worker is None
