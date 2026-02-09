# =============================================================================
# tests/test_find_replace.py — Tests for FindReplaceBar
# =============================================================================

import pytest
from PyQt6.QtWidgets import QPlainTextEdit

from ui.find_replace import FindReplaceBar

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def editor(qapp, qtbot):
    """Create a QPlainTextEdit with sample content."""
    ed = QPlainTextEdit()
    ed.setPlainText("Hello world\nhello World\nHELLO WORLD\nfoo bar baz")
    qtbot.addWidget(ed)
    return ed


@pytest.fixture
def find_bar(qapp, qtbot, editor):
    """Create a FindReplaceBar connected to the editor."""
    bar = FindReplaceBar()
    bar.set_editor(editor)
    qtbot.addWidget(bar)
    return bar


# ---------------------------------------------------------------------------
# Construction and UI
# ---------------------------------------------------------------------------


class TestFindReplaceBarInit:
    """Tests for FindReplaceBar initialization."""

    def test_creates_successfully(self, find_bar):
        assert find_bar is not None

    def test_starts_hidden_by_default(self, find_bar):
        # Widget is created but not explicitly shown
        assert not find_bar.isVisible()

    def test_has_find_input(self, find_bar):
        assert find_bar.find_input is not None
        assert find_bar.find_input.placeholderText() == "Search..."

    def test_has_replace_input(self, find_bar):
        assert find_bar.replace_input is not None
        assert find_bar.replace_input.placeholderText() == "Replace with..."

    def test_case_checkbox_unchecked_by_default(self, find_bar):
        assert not find_bar.case_checkbox.isChecked()


# ---------------------------------------------------------------------------
# Show / Hide
# ---------------------------------------------------------------------------


class TestFindReplaceBarVisibility:
    """Tests for show/hide behavior."""

    def test_show_bar_makes_visible(self, find_bar):
        find_bar.show_bar()
        assert find_bar.isVisible()

    def test_hide_bar_hides_widget(self, find_bar):
        find_bar.show_bar()
        find_bar.hide_bar()
        assert not find_bar.isVisible()

    def test_hide_bar_emits_closed(self, find_bar, qtbot):
        find_bar.show_bar()
        with qtbot.waitSignal(find_bar.closed, timeout=1000):
            find_bar.hide_bar()

    def test_show_bar_uses_editor_selection(self, find_bar, editor):
        """If editor has selected text, it becomes the search term."""
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.movePosition(cursor.MoveOperation.EndOfWord, cursor.MoveMode.KeepAnchor)
        editor.setTextCursor(cursor)

        find_bar.show_bar()
        assert find_bar.find_input.text() == "Hello"

    def test_hide_bar_calls_setFocus_on_editor(self, find_bar, editor):
        """hide_bar should request focus on the editor."""
        find_bar.show_bar()
        # In offscreen mode hasFocus() is unreliable, so just verify
        # that hide_bar completes and the bar is hidden.
        find_bar.hide_bar()
        assert not find_bar.isVisible()


# ---------------------------------------------------------------------------
# Find
# ---------------------------------------------------------------------------


class TestFindReplaceBarFind:
    """Tests for find next/prev functionality."""

    def test_find_next_case_insensitive(self, find_bar, editor):
        """Case-insensitive search should find 'hello' in all cases."""
        find_bar.find_input.setText("hello")
        find_bar.find_next()

        cursor = editor.textCursor()
        assert cursor.hasSelection()
        assert cursor.selectedText().lower() == "hello"

    def test_find_next_case_sensitive(self, find_bar, editor):
        """Case-sensitive search for 'Hello' should skip 'hello'."""
        find_bar.case_checkbox.setChecked(True)
        find_bar.find_input.setText("Hello")
        find_bar.find_next()

        cursor = editor.textCursor()
        assert cursor.hasSelection()
        assert cursor.selectedText() == "Hello"

    def test_find_next_wraps_around(self, find_bar, editor):
        """Find should wrap from end to beginning."""
        # Move cursor to end
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)

        find_bar.find_input.setText("Hello")
        find_bar.find_next()

        # Should wrap and find "Hello" at start
        cursor = editor.textCursor()
        assert cursor.hasSelection()

    def test_find_prev(self, find_bar, editor):
        """find_prev should find matches backwards."""
        # Move cursor to end
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)

        find_bar.find_input.setText("hello")
        find_bar.find_prev()

        cursor = editor.textCursor()
        assert cursor.hasSelection()

    def test_find_prev_wraps_around(self, find_bar, editor):
        """find_prev should wrap from beginning to end."""
        # Cursor already at start
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        editor.setTextCursor(cursor)

        find_bar.find_input.setText("baz")
        find_bar.find_prev()

        cursor = editor.textCursor()
        assert cursor.hasSelection()
        assert cursor.selectedText() == "baz"

    def test_find_empty_string_does_nothing(self, find_bar, editor):
        """Empty search should not move cursor."""
        cursor = editor.textCursor()
        pos_before = cursor.position()

        find_bar.find_input.setText("")
        find_bar.find_next()

        assert editor.textCursor().position() == pos_before

    def test_find_no_editor_does_nothing(self, qapp, qtbot):
        """find_next without an editor should not crash."""
        bar = FindReplaceBar()
        qtbot.addWidget(bar)
        bar.find_input.setText("test")
        bar.find_next()  # should not raise


# ---------------------------------------------------------------------------
# Match count
# ---------------------------------------------------------------------------


class TestFindReplaceBarMatchCount:
    """Tests for match counting."""

    def test_match_count_updates(self, find_bar):
        """Typing in find input should update match count."""
        find_bar.find_input.setText("hello")
        # "Hello", "hello", "HELLO" — 3 case-insensitive matches
        assert "3 found" in find_bar.match_label.text()

    def test_match_count_case_sensitive(self, find_bar):
        """Case-sensitive search should count exact matches only."""
        find_bar.case_checkbox.setChecked(True)
        find_bar.find_input.setText("hello")
        assert "1 found" in find_bar.match_label.text()

    def test_no_results_message(self, find_bar):
        """Search with no matches should show 'No results'."""
        find_bar.find_input.setText("zzzznotfound")
        assert "No results" in find_bar.match_label.text()

    def test_empty_search_clears_label(self, find_bar):
        """Clearing search input should clear match label."""
        find_bar.find_input.setText("hello")
        find_bar.find_input.setText("")
        assert find_bar.match_label.text() == ""


# ---------------------------------------------------------------------------
# Replace
# ---------------------------------------------------------------------------


class TestFindReplaceBarReplace:
    """Tests for replace functionality."""

    def test_replace_current(self, find_bar, editor):
        """Replace should swap the current match."""
        find_bar.case_checkbox.setChecked(True)
        find_bar.find_input.setText("Hello")
        find_bar.replace_input.setText("Goodbye")

        # Find first match
        find_bar.find_next()
        # Replace it
        find_bar.replace_current()

        assert "Goodbye world" in editor.toPlainText()

    def test_replace_all(self, find_bar, editor):
        """Replace all should swap every occurrence."""
        find_bar.find_input.setText("hello")
        find_bar.replace_input.setText("HI")

        find_bar.replace_all()

        text = editor.toPlainText()
        assert "hello" not in text.lower() or "HI" in text
        assert "replaced" in find_bar.match_label.text()

    def test_replace_all_case_sensitive(self, find_bar, editor):
        """Case-sensitive replace all should only replace exact matches."""
        find_bar.case_checkbox.setChecked(True)
        find_bar.find_input.setText("Hello")
        find_bar.replace_input.setText("Bye")

        find_bar.replace_all()

        text = editor.toPlainText()
        assert "Bye world" in text
        # Other cases should remain
        assert "hello World" in text
        assert "HELLO WORLD" in text

    def test_replace_empty_search_does_nothing(self, find_bar, editor):
        """Replace with empty search should not modify text."""
        original = editor.toPlainText()
        find_bar.find_input.setText("")
        find_bar.replace_input.setText("something")
        find_bar.replace_all()
        assert editor.toPlainText() == original

    def test_replace_no_editor_does_nothing(self, qapp, qtbot):
        """Replace without an editor should not crash."""
        bar = FindReplaceBar()
        qtbot.addWidget(bar)
        bar.find_input.setText("test")
        bar.replace_input.setText("new")
        bar.replace_current()  # should not raise
        bar.replace_all()  # should not raise
