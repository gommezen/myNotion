"""
Editor tab widget - handles individual document editing.
"""

from PyQt6.QtCore import QRect, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QPainter, QTextFormat
from PyQt6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

from core.settings import EditorTheme, SettingsManager
from syntax.highlighter import (
    Language,
    create_highlighter,
    get_language_from_extension,
)


class LineNumberArea(QWidget):
    """Widget for displaying line numbers alongside the editor."""

    def __init__(self, editor: "EditorTab"):
        super().__init__(editor)
        self.editor = editor
        # Ensure this widget has a valid font from the start
        self.setFont(editor.font())

    def sizeHint(self) -> QSize:
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class EditorTab(QPlainTextEdit):
    """A single editor tab for text/code editing with syntax highlighting."""

    # Emitted when the editor wants a completion (prefix, suffix)
    completion_requested = pyqtSignal(str, str)
    # Emitted when the user requests an inline AI edit (carries instruction text)
    inline_edit_requested = pyqtSignal(str)
    # Emitted when inline edit is cancelled (Escape or Cancel button)
    inline_edit_cancelled = pyqtSignal()
    # Emitted when inline edit result is accepted (Enter after generation done)
    inline_edit_accepted = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Immediately set a valid font to prevent Qt -1 point size issues
        # This must happen before any other operations that might use font metrics
        initial_font = QFont("Consolas", 12)
        if initial_font.pointSize() <= 0:
            initial_font.setPointSize(12)
        super().setFont(initial_font)

        self.filepath: str | None = None
        self.language: Language = Language.PLAIN
        self._zoom_level = 0
        self._highlighter = None
        self._settings = SettingsManager()
        self._theme: EditorTheme = self._settings.get_current_theme()
        self._highlight_line = False  # Notepad-style: no line highlight, just cursor

        # Ghost text (inline completion suggestions)
        self._ghost_text: str = ""
        self._ghost_text_line: int = -1
        self._ghost_text_col: int = -1
        self._completion_enabled = False

        # Debounce timer for triggering completion requests
        self._completion_timer = QTimer(self)
        self._completion_timer.setSingleShot(True)
        self._completion_timer.setInterval(600)
        self._completion_timer.timeout.connect(self._request_completion)

        # Inline AI edit state
        self._inline_edit_bar = None  # Lazy-created InlineEditBar
        self._has_edit_highlights = False

        self._setup_editor()
        self._setup_line_numbers()

    def _setup_editor(self):
        """Configure the editor appearance and behavior."""
        # Load font from settings or use default
        font_family = self._settings.get_font_family()
        font_size = self._settings.get_font_size()

        # Ensure valid font size (must be positive)
        try:
            font_size = int(font_size) if font_size else 12
        except (ValueError, TypeError):
            font_size = 12
        if font_size <= 0:
            font_size = 12

        # Create font with explicit size to avoid -1 issues
        if font_family:
            # Use two-argument constructor to set size immediately
            font = QFont(font_family, font_size)
        else:
            font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)

        # Always explicitly set point size after creation to ensure it's valid
        if font.pointSize() <= 0:
            font.setPointSize(font_size)

        self.setFont(font)

        # Also set font on the document to prevent Qt internal -1 point size issues
        self.document().setDefaultFont(font)

        # Tab settings (4 spaces)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)

        # Line wrapping off for code
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        # Apply theme colors
        self._apply_theme_style()

        # Initialize highlighter for plain text
        self._set_language(Language.PLAIN)

    def _apply_theme_style(self):
        """Apply the current theme colors to the editor."""
        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {self._theme.background};
                color: {self._theme.foreground};
                selection-background-color: {self._theme.selection};
                border: none;
            }}
            QPlainTextEdit:focus {{
                background-color: {self._theme.background};
                border: none;
                outline: none;
            }}
        """)

    def _setup_line_numbers(self):
        """Set up line number display."""
        self.line_number_area = LineNumberArea(self)

        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)

        self._update_line_number_area_width(0)
        self._highlight_current_line()

    def line_number_area_width(self) -> int:
        """Calculate the width needed for line numbers."""
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        space = 3 + self.fontMetrics().horizontalAdvance("9") * digits + 10
        return space

    def _update_line_number_area_width(self, _):
        """Update viewport margins for line number area."""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect: QRect, dy: int):
        """Update line number area on scroll or edit."""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def resizeEvent(self, event):
        """Handle resize to update line number area."""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def line_number_area_paint_event(self, event):
        """Paint line numbers."""
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(self._theme.line_number_bg))

        # Line color for separators
        line_color = QColor(self._theme.chrome_border)

        # Draw line on LEFT edge - separates panel from line numbers
        painter.setPen(line_color)
        painter.drawLine(
            0,
            event.rect().top(),
            0,
            event.rect().bottom(),
        )

        # Draw line on RIGHT edge - separates line numbers from code
        painter.drawLine(
            self.line_number_area.width() - 1,
            event.rect().top(),
            self.line_number_area.width() - 1,
            event.rect().bottom(),
        )

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor(self._theme.line_number_fg))
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 8,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    number,
                )

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def _highlight_current_line(self):
        """Highlight the line where the cursor is.

        Disabled by default for cleaner Notepad-like appearance.
        Set self._highlight_line = True to enable.
        """
        # Notepad-style: no current line highlighting, just cursor
        if not getattr(self, "_highlight_line", False):
            self.setExtraSelections([])
            return

        extra_selections = []

        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor(self._theme.current_line)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)

        self.setExtraSelections(extra_selections)

    def _set_language(self, language: Language):
        """Set the syntax highlighting language."""
        self.language = language
        # Create new highlighter with theme colors
        self._highlighter = create_highlighter(language, self.document(), self._theme)

    def apply_theme(self):
        """Reload and apply the current theme from settings."""
        self._settings = SettingsManager()
        self._theme = self._settings.get_current_theme()

        # Update font
        font_family = self._settings.get_font_family()
        font_size = self._settings.get_font_size()

        # Ensure valid font size
        try:
            font_size = int(font_size) if font_size else 12
        except (ValueError, TypeError):
            font_size = 12
        if font_size <= 0:
            font_size = 12

        # Use two-argument constructor to set size immediately
        font = QFont(font_family, font_size) if font_family else QFont("Consolas", font_size)

        # Always explicitly set point size after creation to ensure it's valid
        if font.pointSize() <= 0:
            font.setPointSize(font_size)

        # Preserve zoom level
        self.setFont(font)

        # Also set font on the document to prevent Qt internal -1 point size issues
        self.document().setDefaultFont(font)

        if self._zoom_level > 0:
            self.zoomIn(self._zoom_level)
        elif self._zoom_level < 0:
            self.zoomOut(abs(self._zoom_level))

        # Update tab stops
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)

        # Apply theme style
        self._apply_theme_style()

        # Recreate highlighter with new theme
        self._set_language(self.language)

        # Refresh line numbers and current line
        self.line_number_area.update()
        self._highlight_current_line()

    def load_file(self, filepath: str):
        """Load content from a file."""
        self.filepath = filepath

        # Detect language from extension
        language = get_language_from_extension(filepath)
        self._set_language(language)

        try:
            with open(filepath, encoding="utf-8") as f:
                self.setPlainText(f.read())
        except UnicodeDecodeError:
            # Try with system default encoding
            with open(filepath) as f:
                self.setPlainText(f.read())

        # Mark as unmodified after loading
        self.document().setModified(False)

    def save_file(self, filepath: str | None = None):
        """Save content to a file."""
        if filepath:
            self.filepath = filepath
            # Update highlighting for new extension
            language = get_language_from_extension(filepath)
            self._set_language(language)

        if self.filepath:
            with open(self.filepath, "w", encoding="utf-8") as f:
                f.write(self.toPlainText())
            # Mark document as unmodified after successful save
            self.document().setModified(False)

    def set_language(self, language: Language):
        """Manually set the syntax highlighting language."""
        self._set_language(language)

    def setFont(self, font: QFont):
        """Override setFont to ensure valid point size."""
        if font.pointSize() <= 0:
            font.setPointSize(12)
        super().setFont(font)
        # Also update line number area if it exists
        if hasattr(self, "line_number_area"):
            self.line_number_area.setFont(font)

    def zoom_in(self):
        """Increase font size."""
        self._zoom_level += 1
        self.zoomIn(1)

    def zoom_out(self):
        """Decrease font size."""
        self._zoom_level -= 1
        self.zoomOut(1)

    def get_language_name(self) -> str:
        """Get the current language name for display."""
        return self.language.name.capitalize()

    # ─── Ghost text (inline completion) ───

    def set_completion_enabled(self, enabled: bool) -> None:
        """Enable or disable the completion trigger timer."""
        self._completion_enabled = enabled
        if not enabled:
            self._completion_timer.stop()
            self.clear_ghost_text()

    def set_completion_delay(self, delay_ms: int) -> None:
        """Set the debounce delay for completion requests."""
        self._completion_timer.setInterval(delay_ms)

    def set_ghost_text(self, text: str) -> None:
        """Show ghost text at the current cursor position."""
        if not text:
            self.clear_ghost_text()
            return
        cursor = self.textCursor()
        self._ghost_text = text
        self._ghost_text_line = cursor.blockNumber()
        self._ghost_text_col = cursor.columnNumber()
        self.viewport().update()

    def clear_ghost_text(self) -> None:
        """Remove any visible ghost text."""
        if self._ghost_text:
            self._ghost_text = ""
            self._ghost_text_line = -1
            self._ghost_text_col = -1
            self.viewport().update()

    def has_ghost_text(self) -> bool:
        """Check if ghost text is currently displayed."""
        return bool(self._ghost_text)

    def _accept_ghost_text(self, first_line_only: bool = False) -> None:
        """Insert ghost text into the document."""
        if not self._ghost_text:
            return

        text_to_insert = self._ghost_text
        if first_line_only:
            text_to_insert = self._ghost_text.split("\n")[0]

        cursor = self.textCursor()
        cursor.insertText(text_to_insert)
        self.setTextCursor(cursor)
        self.clear_ghost_text()

    def _request_completion(self) -> None:
        """Build prefix/suffix from cursor position and emit completion_requested."""
        if not self._completion_enabled:
            return

        from ai.completion import extract_context

        cursor = self.textCursor()
        text = self.toPlainText()
        prefix, suffix = extract_context(text, cursor.blockNumber(), cursor.columnNumber())

        # Only request if there's meaningful prefix content
        if prefix.strip():
            self.completion_requested.emit(prefix, suffix)

    def keyPressEvent(self, event) -> None:
        """Handle key presses for ghost text accept/dismiss and completion triggers."""
        # If the inline edit bar is visible, don't intercept keys here
        if self._inline_edit_bar and self._inline_edit_bar.isVisible():
            super().keyPressEvent(event)
            return

        # Tab: accept ghost text
        if event.key() == Qt.Key.Key_Tab and self.has_ghost_text():
            self._accept_ghost_text()
            return

        # Ctrl+Right: accept first line of ghost text
        if (
            event.key() == Qt.Key.Key_Right
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
            and self.has_ghost_text()
        ):
            self._accept_ghost_text(first_line_only=True)
            return

        # Escape: dismiss ghost text
        if event.key() == Qt.Key.Key_Escape and self.has_ghost_text():
            self.clear_ghost_text()
            return

        # Any other key clears ghost text and restarts the timer
        if self.has_ghost_text():
            self.clear_ghost_text()

        # Let the default handler process the key
        super().keyPressEvent(event)

        # Restart completion timer on text-modifying keys
        if self._completion_enabled and event.text():
            self._completion_timer.start()

    def paintEvent(self, event) -> None:
        """Paint the editor, then overlay ghost text if present."""
        super().paintEvent(event)

        if not self._ghost_text or self._ghost_text_line < 0:
            return

        # Find the block where ghost text should appear
        block = self.document().findBlockByNumber(self._ghost_text_line)
        if not block.isValid():
            return

        # Get block geometry in viewport coordinates
        geom = self.blockBoundingGeometry(block).translated(self.contentOffset())
        block_top = int(geom.top())
        line_height = int(self.blockBoundingRect(block).height())

        # Calculate x position: after the ghost_text_col characters
        block_text = block.text()
        prefix_on_line = block_text[: self._ghost_text_col]
        x_offset = self.fontMetrics().horizontalAdvance(prefix_on_line)

        # Account for document margin
        x_offset += int(self.document().documentMargin())

        painter = QPainter(self.viewport())
        ghost_color = QColor(180, 210, 190, 90)  # rgba(180,210,190,0.35)
        painter.setPen(ghost_color)
        painter.setFont(self.font())

        ghost_lines = self._ghost_text.split("\n")
        for i, line in enumerate(ghost_lines):
            y = block_top + (i * line_height) + self.fontMetrics().ascent()
            if i == 0:
                # First line: draw after cursor position
                painter.drawText(x_offset, y, line)
            else:
                # Subsequent lines: draw from left margin
                x = int(self.document().documentMargin())
                painter.drawText(x, y, line)

        painter.end()

    # ─── Inline AI edit (Ctrl+K) ───

    def show_inline_edit(self) -> None:
        """Show the inline edit bar below the current selection."""
        from ui.inline_edit_widget import InlineEditBar

        # Pause code completions while inline edit is active
        self._completion_timer.stop()
        self.clear_ghost_text()

        if not self._inline_edit_bar:
            self._inline_edit_bar = InlineEditBar(self.viewport())
            self._inline_edit_bar.edit_requested.connect(
                lambda instr: self.inline_edit_requested.emit(instr)
            )
            self._inline_edit_bar.cancelled.connect(self.inline_edit_cancelled.emit)
            self._inline_edit_bar.accepted.connect(self.inline_edit_accepted.emit)
        self._position_inline_edit_bar()
        self._inline_edit_bar.show_bar()

    def hide_inline_edit(self) -> None:
        """Hide the inline edit bar and clear highlights."""
        if self._inline_edit_bar:
            self._inline_edit_bar.hide_bar()
        self.clear_edit_highlights()

    def get_inline_edit_bar(self):
        """Return the inline edit bar widget (or None if not created)."""
        return self._inline_edit_bar

    def _position_inline_edit_bar(self) -> None:
        """Position the inline edit bar at the center of the viewport."""
        if not self._inline_edit_bar:
            return

        viewport = self.viewport()

        # Reduced width: ~60% of viewport, clamped between 400-700px
        bar_width = max(400, min(700, int(viewport.width() * 0.6)))
        self._inline_edit_bar.setFixedWidth(bar_width)

        bar_height = self._inline_edit_bar.sizeHint().height()

        # Center horizontally and vertically
        bar_x = (viewport.width() - bar_width) // 2
        bar_y = (viewport.height() - bar_height) // 2

        self._inline_edit_bar.move(bar_x, bar_y)

    def highlight_edited_region(self, start_pos: int, end_pos: int) -> None:
        """Apply a green highlight to the edited region."""
        selection = QTextEdit.ExtraSelection()
        highlight_color = QColor(40, 80, 60, 50)
        selection.format.setBackground(highlight_color)

        cursor = self.textCursor()
        cursor.setPosition(start_pos)
        cursor.setPosition(end_pos, cursor.MoveMode.KeepAnchor)
        selection.cursor = cursor

        self.setExtraSelections([selection])
        self._has_edit_highlights = True

        # Watch for document changes to auto-clear highlights
        self.document().contentsChanged.connect(self._on_document_changed_for_highlights)

    def clear_edit_highlights(self) -> None:
        """Remove the green edit highlights."""
        import contextlib

        if self._has_edit_highlights:
            self.setExtraSelections([])
            self._has_edit_highlights = False
            # Disconnect the watcher
            with contextlib.suppress(TypeError):
                self.document().contentsChanged.disconnect(self._on_document_changed_for_highlights)

    def _on_document_changed_for_highlights(self) -> None:
        """Auto-clear edit highlights when document changes (undo or manual edit)."""
        self.clear_edit_highlights()
