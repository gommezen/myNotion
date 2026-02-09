"""
Status bar manager — creates and updates all status bar indicators.
"""

import contextlib
from collections.abc import Callable

from PyQt6.QtGui import QActionGroup
from PyQt6.QtWidgets import QLabel, QMainWindow, QStatusBar

from syntax.highlighter import Language
from ui.editor_tab import EditorTab


class StatusBarManager:
    """Manages the status bar and its indicator labels.

    Reads editor state via a callable accessor and updates position,
    character count, language, zoom, line ending, and encoding labels.
    """

    def __init__(
        self,
        window: QMainWindow,
        get_editor: Callable[[], EditorTab | None],
    ):
        self._window = window
        self._get_editor = get_editor
        self._language_actions: QActionGroup | None = None

        # Labels — created in setup()
        self.statusbar: QStatusBar | None = None
        self.position_label: QLabel | None = None
        self.chars_label: QLabel | None = None
        self.language_label: QLabel | None = None
        self.zoom_label: QLabel | None = None
        self.line_ending_label: QLabel | None = None
        self.encoding_label: QLabel | None = None

    def set_language_actions(self, language_actions: QActionGroup) -> None:
        """Set the language action group (created during menu setup)."""
        self._language_actions = language_actions

    def setup(self) -> QStatusBar:
        """Create the status bar with all indicators.

        Returns:
            The QStatusBar instance (also set on the window).
        """
        self.statusbar = QStatusBar(self._window)
        self._window.setStatusBar(self.statusbar)

        self.position_label = QLabel("Ln 1, Col 1")
        self.statusbar.addPermanentWidget(self.position_label)

        self.chars_label = QLabel("0 characters")
        self.statusbar.addPermanentWidget(self.chars_label)

        self.language_label = QLabel("Plain text")
        self.statusbar.addPermanentWidget(self.language_label)

        self.zoom_label = QLabel("100%")
        self.statusbar.addPermanentWidget(self.zoom_label)

        self.line_ending_label = QLabel("CRLF")
        self.statusbar.addPermanentWidget(self.line_ending_label)

        self.encoding_label = QLabel("UTF-8")
        self.statusbar.addPermanentWidget(self.encoding_label)

        return self.statusbar

    def connect_editor(self, editor: EditorTab) -> None:
        """Connect editor signals for status bar updates.

        Safely disconnects any previous connections first.
        """
        with contextlib.suppress(TypeError):
            editor.cursorPositionChanged.disconnect(self.update)
        with contextlib.suppress(TypeError):
            editor.textChanged.disconnect(self.update)

        editor.cursorPositionChanged.connect(self.update)
        editor.textChanged.connect(self.update)
        self.update()

    def update(self) -> None:
        """Update all status bar indicators from the current editor."""
        editor = self._get_editor()
        if not editor:
            return

        # Position
        cursor = editor.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        self.position_label.setText(f"Ln {line}, Col {col}")

        # Character count
        text = editor.toPlainText()
        char_count = len(text)
        if char_count == 1:
            self.chars_label.setText("1 character")
        else:
            self.chars_label.setText(f"{char_count:,} characters")

        # Zoom level
        zoom = 100 + (editor._zoom_level * 10)
        self.zoom_label.setText(f"{zoom}%")

        # Line ending detection
        if "\r\n" in text:
            self.line_ending_label.setText("CRLF")
        elif "\n" in text:
            self.line_ending_label.setText("LF")
        else:
            self.line_ending_label.setText("CRLF")  # Default for Windows

    def update_language(self, language: Language) -> None:
        """Update the language indicator label and menu checkmark."""
        self.language_label.setText(language.name.capitalize())

        for action in self._language_actions.actions():
            if action.data() == language:
                action.setChecked(True)
                break

    def on_language_selected(self) -> None:
        """Handle language selection from the View > Language menu."""
        action = self._language_actions.checkedAction()
        if action and (editor := self._get_editor()):
            language = action.data()
            editor.set_language(language)
            self.update_language(language)

    def show_message(self, msg: str, timeout_ms: int = 3000) -> None:
        """Show a temporary message in the status bar."""
        if self.statusbar:
            self.statusbar.showMessage(msg, timeout_ms)
