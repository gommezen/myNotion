"""
Inline AI edit controller — manages the Ctrl+K inline editing lifecycle.

Handles instruction submission, AI streaming, selection replacement,
and accept/cancel flows. Communicates with editors via signals.
"""

import contextlib
from collections.abc import Callable

from PyQt6.QtCore import QObject
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QMainWindow

from ai.worker import AIManager
from ui.editor_tab import EditorTab
from ui.side_panel import LayoutMode


class InlineEditController(QObject):
    """Manages Ctrl+K inline AI editing lifecycle.

    Owns the AIManager for inline edits, tracks streaming state,
    and wires/unwires editor signals on tab changes.
    """

    def __init__(
        self,
        parent: QMainWindow,
        get_editor: Callable[[], EditorTab | None],
        get_model_id: Callable[[], str],
        get_layout_mode: Callable[[], LayoutMode],
    ):
        super().__init__(parent)
        self._get_editor = get_editor
        self._get_model_id = get_model_id
        self._get_layout_mode = get_layout_mode

        # AI backend
        self._manager = AIManager(parent)
        self._manager.token_received.connect(self._on_token)
        self._manager.generation_finished.connect(self._on_finished)
        self._manager.generation_error.connect(self._on_error)

        # Streaming state
        self._buffer = ""
        self._selection_start = -1
        self._selection_end = -1
        self._active = False
        self._prev_editor: EditorTab | None = None

    def setup(self, window: QMainWindow) -> None:
        """Register Ctrl+K shortcut on the window."""
        action = QAction(window.tr("Inline AI Edit"), window)
        action.setShortcut(QKeySequence("Ctrl+K"))
        action.triggered.connect(self._on_shortcut)
        window.addAction(action)

    @property
    def is_active(self) -> bool:
        """Whether an inline edit generation is in progress."""
        return self._active

    def connect_editor(self, editor: EditorTab) -> None:
        """Wire inline edit signals for a newly active editor."""
        editor.inline_edit_requested.connect(self._on_requested)
        editor.inline_edit_cancelled.connect(self._on_cancelled)
        editor.inline_edit_accepted.connect(self._on_accepted)
        self._prev_editor = editor

    def disconnect_editor(self, editor: EditorTab) -> None:
        """Disconnect inline edit signals from previous editor."""
        with contextlib.suppress(TypeError):
            editor.inline_edit_requested.disconnect(self._on_requested)
        with contextlib.suppress(TypeError):
            editor.inline_edit_cancelled.disconnect(self._on_cancelled)
        with contextlib.suppress(TypeError):
            editor.inline_edit_accepted.disconnect(self._on_accepted)

    def disconnect_previous(self) -> None:
        """Disconnect the previously wired editor, if any."""
        if self._prev_editor:
            self.disconnect_editor(self._prev_editor)

    def stop(self) -> None:
        """Stop any active generation."""
        if self._active:
            self._manager.stop()
            self._buffer = ""
            self._active = False

    def stop_manager(self) -> None:
        """Stop the AI manager thread (for app shutdown)."""
        self._manager.stop()

    def cancel_active(self) -> None:
        """Cancel in-progress edit and reset state."""
        self.stop()

    # ─── Internal handlers ───

    def _on_shortcut(self) -> None:
        """Handle Ctrl+K: show inline edit bar for current selection."""
        editor = self._get_editor()
        if not editor:
            return

        # Cancel any in-progress inline edit
        self.stop()

        cursor = editor.textCursor()

        # Auto-select current line if no selection
        if not cursor.hasSelection():
            cursor.select(cursor.SelectionType.LineUnderCursor)
            editor.setTextCursor(cursor)

        # Guard: require at least 2 non-whitespace characters
        if len(cursor.selectedText().strip()) < 2:
            return

        editor.show_inline_edit()

    def _on_requested(self, instruction: str) -> None:
        """Handle instruction submission from inline edit bar."""
        editor = self._get_editor()
        if not editor:
            return

        cursor = editor.textCursor()
        selected_text = cursor.selectedText().replace("\u2029", "\n")

        # Save selection positions for later replacement
        self._selection_start = cursor.selectionStart()
        self._selection_end = cursor.selectionEnd()
        self._buffer = ""
        self._active = True

        # Update bar status
        bar = editor.get_inline_edit_bar()
        if bar:
            bar.set_generating(True)

        # Build mode-aware prompt
        is_writing = self._get_layout_mode() == LayoutMode.WRITING

        if is_writing:
            prompt = f"Instruction: {instruction}\n\nText:\n{selected_text}\n\nEdited text:"
            system_prompt = (
                "You are a text editor. Edit the text according to the instruction.\n"
                "Return ONLY the edited text. No explanations, no markdown fences, no commentary."
            )
        else:
            prompt = f"Instruction: {instruction}\n\nCode:\n{selected_text}\n\nEdited code:"
            system_prompt = (
                "You are a code editor. Edit the code according to the instruction.\n"
                "Return ONLY the edited code. No explanations, no markdown fences, no commentary."
            )

        model = self._get_model_id()

        self._manager.generate(
            model=model,
            prompt=prompt,
            context=system_prompt,
            mode="writing" if is_writing else "coding",
        )

    def _on_token(self, token: str) -> None:
        """Collect streamed tokens into the buffer."""
        self._buffer += token

    def _on_finished(self) -> None:
        """Handle AI generation complete — replace selection with result."""
        editor = self._get_editor()
        if not editor:
            return

        code = self._strip_code_fences(self._buffer)
        self._active = False

        if not code.strip():
            bar = editor.get_inline_edit_bar()
            if bar:
                bar.set_error("AI returned empty response")
            return

        # Replace selection as a single undo operation
        cursor = editor.textCursor()
        cursor.setPosition(self._selection_start)
        cursor.setPosition(self._selection_end, cursor.MoveMode.KeepAnchor)

        cursor.beginEditBlock()
        cursor.insertText(code)
        cursor.endEditBlock()

        # Calculate the end position of inserted text
        insert_end = self._selection_start + len(code)

        # Highlight the replaced region
        editor.highlight_edited_region(self._selection_start, insert_end)

        # Update bar status
        bar = editor.get_inline_edit_bar()
        if bar:
            bar.set_status("Enter/Tab = accept, Esc = undo")
            bar.set_generating(False)

    def _on_error(self, error: str) -> None:
        """Handle AI generation error."""
        self._active = False
        editor = self._get_editor()
        if editor:
            bar = editor.get_inline_edit_bar()
            if bar:
                bar.set_error(error)

    def _on_cancelled(self) -> None:
        """Handle cancel: stop generation, undo if edit was made, hide bar."""
        self.stop()

        editor = self._get_editor()
        if not editor:
            return

        # If an edit was applied, undo it
        if editor._has_edit_highlights:
            editor.document().undo()

        editor.hide_inline_edit()
        editor.setFocus()

    def _on_accepted(self) -> None:
        """Handle accept: clear highlights, hide bar, keep the edit."""
        editor = self._get_editor()
        if editor:
            editor.hide_inline_edit()
            editor.setFocus()

    @staticmethod
    def _strip_code_fences(code: str) -> str:
        """Strip markdown code fences from AI response."""
        lines = code.strip().split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines)
