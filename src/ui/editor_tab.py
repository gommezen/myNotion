"""
Editor tab widget - handles individual document editing.
"""

from PyQt6.QtCore import QRect, QSize, Qt
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
        line_color = QColor("#2a4a4a")

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
