# =============================================================================
# tests/conftest.py — Shared pytest fixtures for MyNotion
# =============================================================================
#
# This file is auto-loaded by pytest before any test module runs.
# It provides:
#   - QApplication lifecycle management (one instance per session)
#   - qtbot fixture via pytest-qt for widget interaction testing
#   - Async event loop integration via qasync
#   - Mock AI client that returns predictable responses
#   - Temporary file/directory helpers for file I/O tests
#
# Usage in tests:
#   def test_something(qtbot, mock_ai_client):
#       ...
#
# =============================================================================

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# QApplication singleton — PyQt6 requires exactly one per process
# ---------------------------------------------------------------------------
# The "session" scope means this fixture runs once for the entire test suite.
# If you use pytest-qt, it handles QApplication creation via its own
# `qapp` fixture, but this gives us explicit control over lifecycle.


@pytest.fixture(scope="session")
def qapp():
    """
    Create or reuse a QApplication instance for the test session.

    PyQt6 enforces a single QApplication per process. If one already
    exists (e.g., from pytest-qt), we reuse it. Otherwise, we create
    a new one with test-appropriate settings.
    """
    from PyQt6.QtWidgets import QApplication

    # Check if QApplication already exists (pytest-qt may have created one)
    app = QApplication.instance()
    if app is None:
        # Create with minimal args — no actual window system needed
        # for headless testing (use QT_QPA_PLATFORM=offscreen)
        app = QApplication([*sys.argv, "--platform", "offscreen"])
        app.setApplicationName("MyNotion-Tests")

    yield app

    # Note: We do NOT call app.quit() here. Destroying QApplication
    # in a session fixture can cause segfaults if other fixtures
    # still hold QObject references. Let the process exit handle it.


# ---------------------------------------------------------------------------
# Async event loop — integrates asyncio with Qt's event loop
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def event_loop(qapp):
    """
    Provide a qasync event loop that bridges asyncio and Qt.

    This replaces the default asyncio loop with one that processes
    Qt events alongside asyncio tasks — critical for testing code
    that uses @asyncSlot() or emits signals from async contexts.
    """
    try:
        import qasync

        loop = qasync.QEventLoop(qapp)
    except ImportError:
        # Fallback: if qasync isn't installed, use standard asyncio loop.
        # Async-Qt integration tests will fail, but pure async tests work.
        loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Mock AI client — predictable responses without network calls
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_ai_client():
    """
    A mock AI client that mimics the interface of ai/client.py.

    Returns predictable responses so tests don't depend on a running
    Ollama instance. Tracks calls for assertion in tests.

    Usage:
        def test_completion(mock_ai_client):
            mock_ai_client.complete.return_value = "Hello, world!"
            result = await mock_ai_client.complete("Say hello")
            mock_ai_client.complete.assert_called_once()
    """
    client = MagicMock()

    # Async methods need AsyncMock to be awaitable
    client.complete = AsyncMock(return_value="Mock AI response")
    client.stream = AsyncMock(return_value=iter(["Mock ", "streaming ", "response"]))
    client.is_available = AsyncMock(return_value=True)

    # Sync properties for configuration inspection
    client.model = "mock-model"
    client.endpoint = "http://localhost:11434"
    client.temperature = 0.7

    # Track connection state
    client.connected = True

    return client


@pytest.fixture
def mock_ai_client_offline():
    """
    A mock AI client simulating connection failure (Ollama not running).

    Useful for testing error handling and graceful degradation in the UI
    when the AI backend is unreachable.
    """
    client = MagicMock()

    client.complete = AsyncMock(side_effect=ConnectionError("Connection refused"))
    client.stream = AsyncMock(side_effect=ConnectionError("Connection refused"))
    client.is_available = AsyncMock(return_value=False)
    client.connected = False
    client.model = "mock-model"
    client.endpoint = "http://localhost:11434"

    return client


# ---------------------------------------------------------------------------
# Temporary files — isolated file system for I/O tests
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_file(tmp_path):
    """
    Create a temporary text file with sample content.

    Returns a Path object. The file is auto-cleaned after the test.

    Usage:
        def test_open_file(tmp_file):
            content = tmp_file.read_text()
            assert "sample" in content
    """
    file = tmp_path / "test_document.txt"
    file.write_text("This is sample content for testing.\nLine two.\n", encoding="utf-8")
    return file


@pytest.fixture
def tmp_python_file(tmp_path):
    """
    Create a temporary Python file for syntax highlighting tests.
    """
    file = tmp_path / "test_script.py"
    file.write_text(
        '"""A sample Python file."""\n'
        "\n"
        "def hello(name: str) -> str:\n"
        '    return f"Hello, {name}!"\n'
        "\n"
        "\n"
        'if __name__ == "__main__":\n'
        '    print(hello("world"))\n',
        encoding="utf-8",
    )
    return file


@pytest.fixture
def tmp_project_dir(tmp_path):
    """
    Create a temporary project directory with multiple file types.

    Useful for testing the file browser / tree view if you add one,
    or for batch file operation tests.
    """
    # Create subdirectories
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "docs").mkdir()

    # Populate with sample files
    (tmp_path / "src" / "main.py").write_text("# main\n", encoding="utf-8")
    (tmp_path / "src" / "utils.py").write_text("# utils\n", encoding="utf-8")
    (tmp_path / "tests" / "test_main.py").write_text("# test\n", encoding="utf-8")
    (tmp_path / "docs" / "README.md").write_text("# Docs\n", encoding="utf-8")

    return tmp_path


# ---------------------------------------------------------------------------
# Settings isolation — prevent tests from reading/writing real settings
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    """
    Redirect QSettings to a temp directory so tests never touch real config.

    This runs automatically for every test (autouse=True). Tests that
    exercise settings will write to an isolated location that's cleaned
    up after the test.
    """
    from PyQt6.QtCore import QSettings

    # Use IniFormat in a temp directory instead of system registry/plist
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path / "settings"),
    )


# ---------------------------------------------------------------------------
# Widget helpers — common patterns for UI testing with qtbot
# ---------------------------------------------------------------------------


@pytest.fixture
def create_editor_tab(qapp):
    """
    Factory fixture that creates EditorTab widgets for testing.

    Usage:
        def test_editor(create_editor_tab, qtbot):
            tab = create_editor_tab(content="Hello")
            qtbot.addWidget(tab)
            assert tab.toPlainText() == "Hello"
    """
    tabs = []  # Track created tabs for cleanup

    def _factory(content: str = "", file_path: str | None = None):
        # Import here to avoid import errors if src isn't on path yet
        try:
            # Add src to path if needed
            import sys
            from pathlib import Path

            src_path = Path(__file__).parent.parent / "src"
            if str(src_path) not in sys.path:
                sys.path.insert(0, str(src_path))

            from ui.editor_tab import EditorTab

            tab = EditorTab()
            if content:
                tab.setPlainText(content)
            if file_path:
                tab.filepath = file_path
            tabs.append(tab)
            return tab
        except ImportError as e:
            pytest.skip(f"EditorTab not yet implemented: {e}")

    yield _factory

    # Clean up: schedule deletion for all created tabs
    for tab in tabs:
        tab.deleteLater()
