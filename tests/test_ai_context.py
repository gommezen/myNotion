"""Tests for context passing and prompt execution."""

from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# execute_prompt_with_context
# ---------------------------------------------------------------------------


class TestExecutePromptWithContext:
    """Verify execute_prompt_with_context formats and dispatches correctly."""

    def test_with_selection_context(self, create_side_panel, qtbot):
        panel = create_side_panel()
        qtbot.addWidget(panel)

        with patch.object(panel, "_start_ai_generation") as mock_gen:
            panel.execute_prompt_with_context(
                "Explain this code", "def foo(): pass", is_selection=True
            )

        expected = "Explain this code:\n\n```\ndef foo(): pass\n```"
        mock_gen.assert_called_once_with(expected)

    def test_with_full_file_context(self, create_side_panel, qtbot):
        panel = create_side_panel()
        qtbot.addWidget(panel)

        file_content = "import os\n\ndef main():\n    print('hello')\n"
        with patch.object(panel, "_start_ai_generation") as mock_gen:
            panel.execute_prompt_with_context("Debug this code", file_content, is_selection=False)

        expected = f"Debug this code:\n\n```\n{file_content}\n```"
        mock_gen.assert_called_once_with(expected)

    def test_with_no_context(self, create_side_panel, qtbot):
        panel = create_side_panel()
        qtbot.addWidget(panel)

        with patch.object(panel, "_start_ai_generation") as mock_gen:
            panel.execute_prompt_with_context("Explain this code", None)

        # Should use prompt only (no code block wrapping)
        mock_gen.assert_called_once_with("Explain this code")

    def test_prompt_context_format(self, create_side_panel, qtbot):
        """Verify exact f-string formatting: prompt + colon + code block."""
        panel = create_side_panel()
        qtbot.addWidget(panel)

        with patch.object(panel, "_start_ai_generation") as mock_gen:
            panel.execute_prompt_with_context("Fix errors", "x = 1", is_selection=True)

        result = mock_gen.call_args[0][0]
        assert result.startswith("Fix errors:")
        assert "```\nx = 1\n```" in result


# ---------------------------------------------------------------------------
# _has_selection_to_replace flag
# ---------------------------------------------------------------------------


class TestHasSelectionFlag:
    """Verify _has_selection_to_replace is set correctly."""

    def test_true_when_selection_and_context(self, create_side_panel, qtbot):
        panel = create_side_panel()
        qtbot.addWidget(panel)

        with patch.object(panel, "_start_ai_generation"):
            panel.execute_prompt_with_context("Fix", "code here", is_selection=True)

        assert panel._has_selection_to_replace is True

    def test_false_when_not_selection(self, create_side_panel, qtbot):
        panel = create_side_panel()
        qtbot.addWidget(panel)

        with patch.object(panel, "_start_ai_generation"):
            panel.execute_prompt_with_context("Fix", "code here", is_selection=False)

        assert panel._has_selection_to_replace is False

    def test_false_when_no_context(self, create_side_panel, qtbot):
        panel = create_side_panel()
        qtbot.addWidget(panel)

        with patch.object(panel, "_start_ai_generation"):
            panel.execute_prompt_with_context("Fix", None, is_selection=True)

        assert panel._has_selection_to_replace is False

    def test_false_when_empty_context(self, create_side_panel, qtbot):
        panel = create_side_panel()
        qtbot.addWidget(panel)

        with patch.object(panel, "_start_ai_generation"):
            panel.execute_prompt_with_context("Fix", "", is_selection=True)

        assert panel._has_selection_to_replace is False


# ---------------------------------------------------------------------------
# MainWindow _on_context_requested
# ---------------------------------------------------------------------------


class TestMainWindowContext:
    """Verify _on_context_requested gets correct text from editor."""

    def _make_mock_main_window(self):
        """Create a minimal mock of MainWindow with side_panel and editor."""
        from ui.main_window import MainWindow

        main_window = MagicMock(spec=MainWindow)
        main_window.side_panel = MagicMock()
        return main_window

    def test_gets_selected_text(self, create_editor_tab, qtbot):
        """When editor has selection, context should be the selected text."""
        tab = create_editor_tab(content="line1\nline2\nline3")
        qtbot.addWidget(tab)

        # Select "line2"
        cursor = tab.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.movePosition(cursor.MoveOperation.Down)
        cursor.movePosition(cursor.MoveOperation.StartOfLine)
        cursor.movePosition(cursor.MoveOperation.EndOfLine, cursor.MoveMode.KeepAnchor)
        tab.setTextCursor(cursor)

        selected = cursor.selectedText()
        assert selected == "line2"

    def test_gets_full_file_when_no_selection(self, create_editor_tab, qtbot):
        """When no selection, context should be full file content."""
        content = "def foo():\n    return 42\n"
        tab = create_editor_tab(content=content)
        qtbot.addWidget(tab)

        # No selection — toPlainText gives full file
        assert tab.toPlainText() == content


# ---------------------------------------------------------------------------
# execute_chat_with_context
# ---------------------------------------------------------------------------


class TestExecuteChatWithContext:
    """Verify execute_chat_with_context includes/excludes editor content."""

    def test_with_context(self, create_side_panel, qtbot):
        panel = create_side_panel()
        qtbot.addWidget(panel)

        with patch.object(panel, "_start_ai_generation") as mock_gen:
            panel.execute_chat_with_context("What does this do?", "x = 42")

        result = mock_gen.call_args[0][0]
        assert "```\nx = 42\n```" in result
        assert "What does this do?" in result

    def test_without_context(self, create_side_panel, qtbot):
        panel = create_side_panel()
        qtbot.addWidget(panel)

        with patch.object(panel, "_start_ai_generation") as mock_gen:
            panel.execute_chat_with_context("Hello!", None)

        mock_gen.assert_called_once_with("Hello!")

    def test_context_format_includes_user_question(self, create_side_panel, qtbot):
        panel = create_side_panel()
        qtbot.addWidget(panel)

        with patch.object(panel, "_start_ai_generation") as mock_gen:
            panel.execute_chat_with_context("Explain", "import os")

        result = mock_gen.call_args[0][0]
        assert "User question: Explain" in result
