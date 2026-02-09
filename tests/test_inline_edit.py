"""Tests for Inline AI Edit (Ctrl+K) feature."""

from ui.inline_edit_widget import InlineEditBar

# ---------------------------------------------------------------------------
# InlineEditBar widget tests
# ---------------------------------------------------------------------------


class TestInlineEditBarWidget:
    """Test the InlineEditBar widget UI and signals."""

    def test_creation(self, qapp):
        """Bar should create without errors."""
        bar = InlineEditBar()
        assert bar is not None
        bar.deleteLater()

    def test_show_bar_focuses_input(self, qapp):
        """show_bar() should show the widget and clear previous input."""
        bar = InlineEditBar()
        bar.instruction_input.setText("old text")
        bar.show_bar()
        assert bar.isVisible()
        assert bar.instruction_input.text() == ""
        bar.deleteLater()

    def test_hide_bar(self, qapp):
        """hide_bar() should hide the widget."""
        bar = InlineEditBar()
        bar.show()
        bar.hide_bar()
        assert not bar.isVisible()
        bar.deleteLater()

    def test_edit_requested_signal(self, qapp):
        """Submitting instruction should emit edit_requested with text."""
        bar = InlineEditBar()
        received = []
        bar.edit_requested.connect(received.append)

        bar.instruction_input.setText("add error handling")
        bar._on_submit()

        assert received == ["add error handling"]
        bar.deleteLater()

    def test_empty_instruction_not_emitted(self, qapp):
        """Empty instruction should not emit edit_requested."""
        bar = InlineEditBar()
        received = []
        bar.edit_requested.connect(received.append)

        bar.instruction_input.setText("")
        bar._on_submit()

        assert received == []
        bar.deleteLater()

    def test_cancelled_signal(self, qapp):
        """Cancel should emit cancelled signal."""
        bar = InlineEditBar()
        received = []
        bar.cancelled.connect(lambda: received.append(True))

        bar._on_cancel()
        assert received == [True]
        bar.deleteLater()

    def test_accepted_signal_after_complete(self, qapp):
        """Enter after edit complete should emit accepted signal."""
        bar = InlineEditBar()
        received = []
        bar.accepted.connect(lambda: received.append(True))

        # Simulate generation complete
        bar._edit_complete = True
        bar._on_submit()

        assert received == [True]
        bar.deleteLater()

    def test_enter_before_complete_submits_instruction(self, qapp):
        """Enter before edit complete should emit edit_requested, not accepted."""
        bar = InlineEditBar()
        edit_received = []
        accept_received = []
        bar.edit_requested.connect(edit_received.append)
        bar.accepted.connect(lambda: accept_received.append(True))

        bar._edit_complete = False
        bar.instruction_input.setText("fix this")
        bar._on_submit()

        assert edit_received == ["fix this"]
        assert accept_received == []
        bar.deleteLater()

    def test_tab_accepts_after_complete(self, qapp):
        """Tab after edit complete should emit accepted signal."""
        bar = InlineEditBar()
        received = []
        bar.accepted.connect(lambda: received.append(True))

        bar._edit_complete = True
        bar._on_tab()

        assert received == [True]
        bar.deleteLater()

    def test_tab_before_complete_does_nothing(self, qapp):
        """Tab before edit complete should not emit accepted."""
        bar = InlineEditBar()
        received = []
        bar.accepted.connect(lambda: received.append(True))

        bar._edit_complete = False
        bar._on_tab()

        assert received == []
        bar.deleteLater()

    def test_set_generating_disables_input(self, qapp):
        """set_generating(True) should disable the input."""
        bar = InlineEditBar()
        bar.set_generating(True)
        assert not bar.instruction_input.isEnabled()
        assert bar.status_label.text() == "Generating\u2026"
        bar.deleteLater()

    def test_set_generating_false_enables_input(self, qapp):
        """set_generating(False) should enable the input and mark complete."""
        bar = InlineEditBar()
        bar.set_generating(True)
        bar.set_generating(False)
        assert bar.instruction_input.isEnabled()
        assert bar._edit_complete is True
        bar.deleteLater()

    def test_set_error(self, qapp):
        """set_error() should show error text and re-enable input."""
        bar = InlineEditBar()
        bar.set_generating(True)
        bar.set_error("Connection failed")
        assert "Error: Connection failed" in bar.status_label.text()
        assert bar.instruction_input.isEnabled()
        bar.deleteLater()

    def test_set_status(self, qapp):
        """set_status() should update the status label."""
        bar = InlineEditBar()
        bar.set_status("Done — Enter to accept")
        assert bar.status_label.text() == "Done — Enter to accept"
        bar.deleteLater()


# ---------------------------------------------------------------------------
# EditorTab inline edit integration tests
# ---------------------------------------------------------------------------


class TestEditorInlineEdit:
    """Test EditorTab inline edit methods."""

    def test_show_inline_edit_creates_bar(self, qapp):
        """show_inline_edit() should create the bar widget."""
        from ui.editor_tab import EditorTab

        editor = EditorTab()
        editor.setPlainText("hello world")

        # Select some text
        cursor = editor.textCursor()
        cursor.select(cursor.SelectionType.LineUnderCursor)
        editor.setTextCursor(cursor)

        editor.show_inline_edit()
        assert editor._inline_edit_bar is not None
        # Bar is created as child of viewport; in offscreen mode it may not
        # report isVisible(), so we check that show() was called
        assert not editor._inline_edit_bar.isHidden()
        editor.deleteLater()

    def test_hide_inline_edit(self, qapp):
        """hide_inline_edit() should hide bar and clear highlights."""
        from ui.editor_tab import EditorTab

        editor = EditorTab()
        editor.setPlainText("hello world")
        editor.show_inline_edit()
        editor.hide_inline_edit()
        assert not editor._inline_edit_bar.isVisible()
        editor.deleteLater()

    def test_signal_forwarding(self, qapp):
        """InlineEditBar.edit_requested should forward to EditorTab.inline_edit_requested."""
        from ui.editor_tab import EditorTab

        editor = EditorTab()
        editor.setPlainText("hello world")
        received = []
        editor.inline_edit_requested.connect(received.append)

        editor.show_inline_edit()
        editor._inline_edit_bar.instruction_input.setText("make async")
        editor._inline_edit_bar._on_submit()

        assert received == ["make async"]
        editor.deleteLater()

    def test_highlight_edited_region(self, qapp):
        """highlight_edited_region should set extra selections."""
        from ui.editor_tab import EditorTab

        editor = EditorTab()
        editor.setPlainText("hello world\nsecond line")

        editor.highlight_edited_region(0, 5)
        assert editor._has_edit_highlights is True
        assert len(editor.extraSelections()) == 1
        editor.deleteLater()

    def test_clear_edit_highlights(self, qapp):
        """clear_edit_highlights should remove extra selections."""
        from ui.editor_tab import EditorTab

        editor = EditorTab()
        editor.setPlainText("hello world")
        editor.highlight_edited_region(0, 5)

        editor.clear_edit_highlights()
        assert editor._has_edit_highlights is False
        assert len(editor.extraSelections()) == 0
        editor.deleteLater()

    def test_document_change_clears_highlights(self, qapp):
        """Editing the document should auto-clear highlights."""
        from ui.editor_tab import EditorTab

        editor = EditorTab()
        editor.setPlainText("hello world")
        editor.highlight_edited_region(0, 5)

        # Simulate a document change (like typing)
        cursor = editor.textCursor()
        cursor.insertText("x")

        assert editor._has_edit_highlights is False
        editor.deleteLater()


# ---------------------------------------------------------------------------
# Code fence stripping tests
# ---------------------------------------------------------------------------


class TestStripCodeFences:
    """Test markdown code fence stripping from AI responses."""

    def test_strips_opening_and_closing_fences(self):
        """Should remove ```python and ``` wrappers."""
        from ui.inline_edit_controller import InlineEditController

        code = "```python\ndef hello():\n    return 'hi'\n```"
        result = InlineEditController._strip_code_fences(code)
        assert result == "def hello():\n    return 'hi'"

    def test_strips_plain_fences(self):
        """Should remove plain ``` fences."""
        from ui.inline_edit_controller import InlineEditController

        code = "```\nx = 1\n```"
        result = InlineEditController._strip_code_fences(code)
        assert result == "x = 1"

    def test_no_fences_unchanged(self):
        """Code without fences should be returned as-is."""
        from ui.inline_edit_controller import InlineEditController

        code = "x = 1\ny = 2"
        result = InlineEditController._strip_code_fences(code)
        assert result == "x = 1\ny = 2"

    def test_empty_string(self):
        """Empty string should return empty."""
        from ui.inline_edit_controller import InlineEditController

        result = InlineEditController._strip_code_fences("")
        assert result == ""

    def test_only_fences(self):
        """Response with only fences should return empty."""
        from ui.inline_edit_controller import InlineEditController

        result = InlineEditController._strip_code_fences("```\n```")
        assert result == ""

    def test_preserves_internal_backticks(self):
        """Internal backticks (not fences) should be preserved."""
        from ui.inline_edit_controller import InlineEditController

        code = "```python\nprint(`x`)\n```"
        result = InlineEditController._strip_code_fences(code)
        assert "print(`x`)" in result
