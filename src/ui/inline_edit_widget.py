"""
Inline AI Edit bar widget — floating instruction input for Ctrl+K edit.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)


class _InlineLineEdit(QLineEdit):
    """QLineEdit that intercepts Enter, Tab, and Escape for the inline edit bar."""

    enter_pressed = pyqtSignal()
    tab_pressed = pyqtSignal()
    escape_pressed = pyqtSignal()

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.enter_pressed.emit()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Tab:
            self.tab_pressed.emit()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape:
            self.escape_pressed.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class InlineEditBar(QWidget):
    """Floating bar for inline AI code editing instructions."""

    edit_requested = pyqtSignal(str)  # User submitted an instruction
    cancelled = pyqtSignal()  # User pressed Escape
    accepted = pyqtSignal()  # User accepted the completed edit

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._edit_complete = False
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Top row: label
        prompt_label = QLabel("Edit:")
        layout.addWidget(prompt_label)

        # Instruction input — tall single-line field
        self.instruction_input = _InlineLineEdit()
        self.instruction_input.setPlaceholderText(
            "Type instruction, Enter to send — Enter/Tab to accept, Esc to undo"
        )
        self.instruction_input.setMinimumHeight(38)
        self.instruction_input.enter_pressed.connect(self._on_submit)
        self.instruction_input.tab_pressed.connect(self._on_tab)
        self.instruction_input.escape_pressed.connect(self._on_cancel)
        layout.addWidget(self.instruction_input)

        # Status label (hints + generating state)
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

    def _apply_style(self) -> None:
        """Apply a high-contrast style so the bar stands out from the editor."""
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a2e;
                color: #e0e0e0;
                font-size: 12px;
                border: 2px solid #d4a84b;
                border-radius: 6px;
            }
            QLabel {
                background-color: transparent;
                color: #d4a84b;
                border: none;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #0f0f1a;
                color: #f0f0f0;
                border: 1px solid #444466;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 13px;
                selection-background-color: #d4a84b;
                selection-color: #1a1a2e;
            }
            QLineEdit:focus {
                border: 2px solid #d4a84b;
            }
        """)

    def show_bar(self) -> None:
        """Show the bar and focus the instruction input."""
        self._edit_complete = False
        self.status_label.setText("")
        self.instruction_input.clear()
        self.instruction_input.setEnabled(True)
        self.show()
        self.instruction_input.setFocus()

    def hide_bar(self) -> None:
        """Hide the bar and return focus to parent."""
        self.hide()
        if self.parent():
            self.parent().setFocus()

    def set_status(self, text: str) -> None:
        """Update the status label text."""
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            "background: transparent; color: rgba(180, 210, 190, 0.6); border: none;"
        )

    def set_generating(self, generating: bool) -> None:
        """Toggle between generating and done state."""
        self.instruction_input.setEnabled(not generating)
        if generating:
            self._edit_complete = False
            self.set_status("Generating...")
        else:
            self._edit_complete = True
            # Re-focus the input so Enter/Tab/Escape work immediately
            self.instruction_input.setFocus()

    def set_error(self, message: str) -> None:
        """Show error message in red."""
        self.status_label.setText(f"Error: {message}")
        self.status_label.setStyleSheet("background: transparent; color: #c45c5c; border: none;")
        self.set_generating(False)

    def _on_submit(self) -> None:
        """Handle Enter key."""
        if self._edit_complete:
            self.accepted.emit()
        else:
            instruction = self.instruction_input.text().strip()
            if instruction:
                self.edit_requested.emit(instruction)

    def _on_tab(self) -> None:
        """Handle Tab key — accept if edit is complete."""
        if self._edit_complete:
            self.accepted.emit()

    def _on_cancel(self) -> None:
        """Handle Escape key."""
        self.cancelled.emit()
