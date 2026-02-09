"""
Find and Replace bar widget.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut, QTextDocument
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from core.settings import SettingsManager
from ui.theme_engine import hex_to_rgba


class FindReplaceBar(QWidget):
    """Horizontal bar for find and replace functionality."""

    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._editor = None
        self._last_search = ""
        self._settings = SettingsManager()
        self._setup_ui()
        self._apply_style()

        # Escape key closes the bar
        self._escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._escape_shortcut.activated.connect(self.hide_bar)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        # Find section
        find_label = QLabel("Find:")
        find_label.setFixedWidth(45)
        layout.addWidget(find_label)

        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Search...")
        self.find_input.setFixedWidth(200)
        self.find_input.textChanged.connect(self._on_search_changed)
        self.find_input.returnPressed.connect(self.find_next)
        layout.addWidget(self.find_input)

        # Match count label
        self.match_label = QLabel("")
        self.match_label.setFixedWidth(70)
        layout.addWidget(self.match_label)

        # Navigation buttons
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setFixedSize(28, 28)
        self.prev_btn.setToolTip("Previous match (Shift+Enter)")
        self.prev_btn.clicked.connect(self.find_prev)
        layout.addWidget(self.prev_btn)

        self.next_btn = QPushButton("▶")
        self.next_btn.setFixedSize(28, 28)
        self.next_btn.setToolTip("Next match (Enter)")
        self.next_btn.clicked.connect(self.find_next)
        layout.addWidget(self.next_btn)

        # Separator
        separator = QWidget()
        separator.setFixedWidth(1)
        separator.setStyleSheet("background-color: #2a4a4a;")
        layout.addWidget(separator)

        # Replace section
        replace_label = QLabel("Replace:")
        replace_label.setFixedWidth(55)
        layout.addWidget(replace_label)

        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace with...")
        self.replace_input.setFixedWidth(200)
        layout.addWidget(self.replace_input)

        self.replace_btn = QPushButton("Replace")
        self.replace_btn.setToolTip("Replace current match")
        self.replace_btn.clicked.connect(self.replace_current)
        layout.addWidget(self.replace_btn)

        self.replace_all_btn = QPushButton("All")
        self.replace_all_btn.setToolTip("Replace all matches")
        self.replace_all_btn.clicked.connect(self.replace_all)
        layout.addWidget(self.replace_all_btn)

        # Options
        self.case_checkbox = QCheckBox("Aa")
        self.case_checkbox.setToolTip("Match case")
        self.case_checkbox.toggled.connect(self._on_search_changed)
        layout.addWidget(self.case_checkbox)

        layout.addStretch()

        # Close button
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("closeBtn")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setToolTip("Close (Escape)")
        self.close_btn.clicked.connect(self.hide_bar)
        layout.addWidget(self.close_btn)

    def _apply_style(self):
        """Apply current theme styling."""
        theme = self._settings.get_current_theme()
        bg = theme.chrome_bg
        text = theme.foreground
        text_dim = hex_to_rgba(theme.foreground, 0.6)
        border = theme.chrome_border
        input_bg = theme.background
        accent = theme.keyword
        radius = theme.radius

        # Win95: explicit per-side beveled borders
        if theme.is_beveled:
            input_border = theme.bevel_sunken
            input_border_focus = theme.bevel_sunken
            btn_border = theme.bevel_raised
        else:
            input_border = f"border: 1px solid {border};"
            input_border_focus = f"border: 1px solid {accent};"
            btn_border = f"border: 1px solid {border};"

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg};
                color: {text};
                font-size: 11px;
            }}
            QLabel {{
                background-color: transparent;
                color: {text_dim};
            }}
            QLineEdit {{
                background-color: {input_bg};
                color: {text};
                {input_border}
                border-radius: {radius};
                padding: 4px 8px;
            }}
            QLineEdit:focus {{
                {input_border_focus}
            }}
            QPushButton {{
                background-color: transparent;
                color: {text_dim};
                {btn_border}
                border-radius: {radius};
                padding: 4px 10px;
            }}
            QPushButton:hover {{
                background-color: {input_bg};
                color: {text};
            }}
            QPushButton:pressed {{
                background-color: {theme.selection};
            }}
            QCheckBox {{
                color: {text_dim};
                spacing: 4px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                {input_border}
                border-radius: {radius};
                background-color: {input_bg};
            }}
            QCheckBox::indicator:checked {{
                background-color: {accent};
                border-color: {accent};
            }}
            QPushButton#closeBtn {{
                background-color: transparent;
                color: {text_dim};
                border: none;
                border-radius: {radius};
            }}
            QPushButton#closeBtn:hover {{
                color: {text};
                border: 1px solid {text_dim};
            }}
            QPushButton#closeBtn:pressed {{
                background-color: {accent};
                color: {bg};
                border: 1px solid {accent};
            }}
        """)

    def apply_theme(self):
        """Public method for external theme updates."""
        self._settings = SettingsManager()
        self._apply_style()

    def set_editor(self, editor):
        """Set the editor to search in."""
        self._editor = editor

    def show_bar(self, replace_mode: bool = False):
        """Show the find bar and focus the search input."""
        self.show()
        self.find_input.setFocus()
        self.find_input.selectAll()

        # If there's a selection, use it as search term
        if self._editor:
            cursor = self._editor.textCursor()
            if cursor.hasSelection():
                self.find_input.setText(cursor.selectedText())
                self.find_input.selectAll()

    def hide_bar(self):
        """Hide the bar and clear highlights."""
        self.hide()
        self._clear_highlights()
        self.closed.emit()
        # Return focus to editor
        if self._editor:
            self._editor.setFocus()

    def _on_search_changed(self):
        """Handle search text changes."""
        self._highlight_all_matches()

    def _get_find_flags(self) -> QTextDocument.FindFlag:
        """Get search flags based on options."""
        flags = QTextDocument.FindFlag(0)
        if self.case_checkbox.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        return flags

    def _highlight_all_matches(self):
        """Highlight all matches in the editor."""
        if not self._editor:
            return

        search_text = self.find_input.text()
        self._clear_highlights()

        if not search_text:
            self.match_label.setText("")
            return

        # Count matches
        document = self._editor.document()
        cursor = document.find(search_text, 0, self._get_find_flags())
        count = 0

        while not cursor.isNull():
            count += 1
            cursor = document.find(search_text, cursor, self._get_find_flags())

        if count > 0:
            self.match_label.setText(f"{count} found")
            self.match_label.setStyleSheet("background: transparent; color: #c8e0ce;")
        else:
            self.match_label.setText("No results")
            self.match_label.setStyleSheet("background: transparent; color: #e07070;")

    def _clear_highlights(self):
        """Clear all search highlights."""
        if self._editor:
            # Reset any extra selections (future: implement highlight)
            pass

    def find_next(self):
        """Find the next occurrence."""
        if not self._editor:
            return

        search_text = self.find_input.text()
        if not search_text:
            return

        flags = self._get_find_flags()
        found = self._editor.find(search_text, flags)

        # Wrap around to beginning
        if not found:
            cursor = self._editor.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            self._editor.setTextCursor(cursor)
            self._editor.find(search_text, flags)

    def find_prev(self):
        """Find the previous occurrence."""
        if not self._editor:
            return

        search_text = self.find_input.text()
        if not search_text:
            return

        flags = self._get_find_flags() | QTextDocument.FindFlag.FindBackward
        found = self._editor.find(search_text, flags)

        # Wrap around to end
        if not found:
            cursor = self._editor.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self._editor.setTextCursor(cursor)
            self._editor.find(search_text, flags)

    def replace_current(self):
        """Replace the current selection if it matches."""
        if not self._editor:
            return

        search_text = self.find_input.text()
        replace_text = self.replace_input.text()

        if not search_text:
            return

        cursor = self._editor.textCursor()
        if cursor.hasSelection():
            selected = cursor.selectedText()
            # Check if selection matches search
            if self.case_checkbox.isChecked():
                matches = selected == search_text
            else:
                matches = selected.lower() == search_text.lower()

            if matches:
                cursor.insertText(replace_text)
                self._highlight_all_matches()

        # Find next match
        self.find_next()

    def replace_all(self):
        """Replace all occurrences."""
        if not self._editor:
            return

        search_text = self.find_input.text()
        replace_text = self.replace_input.text()

        if not search_text:
            return

        # Start from beginning
        cursor = self._editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        self._editor.setTextCursor(cursor)

        # Replace all
        count = 0
        flags = self._get_find_flags()

        # Use document-level find for efficiency
        cursor.beginEditBlock()
        while self._editor.find(search_text, flags):
            tc = self._editor.textCursor()
            tc.insertText(replace_text)
            count += 1
        cursor.endEditBlock()

        # Update match count
        self._highlight_all_matches()

        if count > 0:
            self.match_label.setText(f"{count} replaced")
