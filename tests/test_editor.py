"""Tests for the editor tab widget."""

import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from pytestqt.qtbot import QtBot

from syntax.highlighter import Language, get_language_from_extension
from ui.editor_tab import EditorTab


@pytest.fixture
def editor(qtbot: QtBot) -> EditorTab:
    """Create an EditorTab instance for testing."""
    widget = EditorTab()
    qtbot.addWidget(widget)
    return widget


def test_editor_initial_state(editor: EditorTab):
    """Editor should start with no filepath and empty content."""
    assert editor.filepath is None
    assert editor.toPlainText() == ""
    assert editor.language == Language.PLAIN


def test_editor_set_text(editor: EditorTab):
    """Editor should accept and return text."""
    editor.setPlainText("Hello, World!")
    assert editor.toPlainText() == "Hello, World!"


def test_editor_zoom(editor: EditorTab):
    """Zoom should adjust the zoom level."""
    initial_level = editor._zoom_level
    editor.zoom_in()
    assert editor._zoom_level == initial_level + 1
    editor.zoom_out()
    assert editor._zoom_level == initial_level


def test_editor_set_language(editor: EditorTab):
    """Setting language should update highlighter."""
    editor.set_language(Language.PYTHON)
    assert editor.language == Language.PYTHON


def test_language_detection_python():
    """Python files should be detected correctly."""
    assert get_language_from_extension("test.py") == Language.PYTHON
    assert get_language_from_extension("script.pyw") == Language.PYTHON


def test_language_detection_javascript():
    """JavaScript files should be detected correctly."""
    assert get_language_from_extension("app.js") == Language.JAVASCRIPT
    assert get_language_from_extension("component.tsx") == Language.JAVASCRIPT


def test_language_detection_html():
    """HTML files should be detected correctly."""
    assert get_language_from_extension("index.html") == Language.HTML
    assert get_language_from_extension("page.htm") == Language.HTML


def test_language_detection_css():
    """CSS files should be detected correctly."""
    assert get_language_from_extension("styles.css") == Language.CSS


def test_language_detection_json():
    """JSON files should be detected correctly."""
    assert get_language_from_extension("config.json") == Language.JSON


def test_language_detection_markdown():
    """Markdown files should be detected correctly."""
    assert get_language_from_extension("README.md") == Language.MARKDOWN


def test_language_detection_plain():
    """Unknown extensions should default to plain text."""
    assert get_language_from_extension("file.xyz") == Language.PLAIN
    assert get_language_from_extension("") == Language.PLAIN
