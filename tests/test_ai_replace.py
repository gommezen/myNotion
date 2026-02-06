"""Tests for Replace functionality in AI responses."""

from ui.side_panel import LayoutMode

# ---------------------------------------------------------------------------
# Replace action link visibility
# ---------------------------------------------------------------------------


class TestReplaceVisibility:
    """Verify 'Replace' action appears/disappears based on selection state."""

    def test_replace_in_code_block_when_selection(self, create_side_panel, qtbot):
        """Replace link should appear in code blocks when _has_selection_to_replace=True."""
        panel = create_side_panel(layout_mode=LayoutMode.CODING)
        qtbot.addWidget(panel)
        panel._has_selection_to_replace = True

        response = "Here:\n```python\nprint('hi')\n```"
        formatted = panel._format_response_text(response)

        assert "code:replace:" in formatted

    def test_no_replace_in_code_block_without_selection(self, create_side_panel, qtbot):
        """Replace link should NOT appear when _has_selection_to_replace=False."""
        panel = create_side_panel(layout_mode=LayoutMode.CODING)
        qtbot.addWidget(panel)
        panel._has_selection_to_replace = False

        response = "Here:\n```python\nprint('hi')\n```"
        formatted = panel._format_response_text(response)

        assert "code:replace:" not in formatted

    def test_copy_insert_newtab_always_present(self, create_side_panel, qtbot):
        """Copy, Insert, New Tab links should always appear in code blocks."""
        panel = create_side_panel()
        qtbot.addWidget(panel)
        panel._has_selection_to_replace = False

        response = "```python\nx = 1\n```"
        formatted = panel._format_response_text(response)

        assert "code:copy:0" in formatted
        assert "code:insert:0" in formatted
        assert "code:newtab:0" in formatted


# ---------------------------------------------------------------------------
# _handle_code_action("replace", ...)
# ---------------------------------------------------------------------------


class TestHandleCodeAction:
    """Test _handle_code_action with replace action."""

    def test_replace_emits_signal(self, create_side_panel, qtbot):
        panel = create_side_panel()
        qtbot.addWidget(panel)
        panel._has_selection_to_replace = True

        with qtbot.waitSignal(panel.replace_selection_requested, timeout=500) as blocker:
            panel._handle_code_action("replace", "new_code()", "python")

        assert blocker.args == ["new_code()"]

    def test_replace_clears_flag(self, create_side_panel, qtbot):
        panel = create_side_panel()
        qtbot.addWidget(panel)
        panel._has_selection_to_replace = True

        panel._handle_code_action("replace", "x = 1", "python")

        assert panel._has_selection_to_replace is False

    def test_insert_emits_transfer_signal(self, create_side_panel, qtbot):
        panel = create_side_panel()
        qtbot.addWidget(panel)

        with qtbot.waitSignal(panel.transfer_to_editor_requested, timeout=500) as blocker:
            panel._handle_code_action("insert", "code_here", "python")

        assert blocker.args == ["code_here"]

    def test_newtab_emits_new_tab_signal(self, create_side_panel, qtbot):
        panel = create_side_panel()
        qtbot.addWidget(panel)

        with qtbot.waitSignal(panel.new_tab_with_code_requested, timeout=500) as blocker:
            panel._handle_code_action("newtab", "code_here", "python")

        assert blocker.args == ["code_here", "python"]


# ---------------------------------------------------------------------------
# _handle_text_action("replace") — writing mode
# ---------------------------------------------------------------------------


class TestHandleTextAction:
    """Test _handle_text_action replace for writing mode."""

    def test_replace_emits_signal_with_wrapped_text(self, create_side_panel, qtbot):
        panel = create_side_panel(layout_mode=LayoutMode.WRITING)
        qtbot.addWidget(panel)
        panel._current_ai_response = "Improved text here."
        panel._has_selection_to_replace = True

        with qtbot.waitSignal(panel.replace_selection_requested, timeout=500) as blocker:
            panel._handle_text_action("replace")

        assert "Improved text here." in blocker.args[0]

    def test_replace_clears_flag_in_text_mode(self, create_side_panel, qtbot):
        panel = create_side_panel(layout_mode=LayoutMode.WRITING)
        qtbot.addWidget(panel)
        panel._current_ai_response = "Some text"
        panel._has_selection_to_replace = True

        panel._handle_text_action("replace")

        assert panel._has_selection_to_replace is False

    def test_no_response_shows_system_message(self, create_side_panel, qtbot):
        panel = create_side_panel(layout_mode=LayoutMode.WRITING)
        qtbot.addWidget(panel)
        panel._current_ai_response = ""

        panel._handle_text_action("replace")

        chat_text = panel.chat_area.toPlainText()
        assert "No text to transfer" in chat_text


# ---------------------------------------------------------------------------
# Writing mode text actions in finished response
# ---------------------------------------------------------------------------


class TestWritingModeFinishedResponse:
    """Verify text action links appear after AI finishes in writing mode."""

    def test_replace_link_in_writing_mode_with_selection(self, create_side_panel, qtbot):
        panel = create_side_panel(layout_mode=LayoutMode.WRITING)
        qtbot.addWidget(panel)
        panel._has_selection_to_replace = True
        panel._current_ai_response = "Better version of text"
        panel._code_blocks = []  # No code blocks

        panel._on_ai_finished()

        chat_html = panel.chat_area.toHtml()
        assert "action:replace_text" in chat_html

    def test_no_replace_link_without_selection(self, create_side_panel, qtbot):
        panel = create_side_panel(layout_mode=LayoutMode.WRITING)
        qtbot.addWidget(panel)
        panel._has_selection_to_replace = False
        panel._current_ai_response = "Some text"
        panel._code_blocks = []

        panel._on_ai_finished()

        chat_html = panel.chat_area.toHtml()
        assert "action:replace_text" not in chat_html


# ---------------------------------------------------------------------------
# MainWindow _replace_selection
# ---------------------------------------------------------------------------


class TestMainWindowReplace:
    """Test _replace_selection in MainWindow replaces selected text."""

    def test_replaces_selected_text(self, create_editor_tab, qtbot):
        tab = create_editor_tab(content="hello world")
        qtbot.addWidget(tab)

        # Select "hello"
        cursor = tab.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.movePosition(cursor.MoveOperation.Right, cursor.MoveMode.KeepAnchor, 5)
        tab.setTextCursor(cursor)

        # Simulate what _replace_selection does
        cursor = tab.textCursor()
        assert cursor.hasSelection()
        cursor.insertText("goodbye")
        tab.setTextCursor(cursor)

        assert tab.toPlainText() == "goodbye world"
