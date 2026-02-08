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

from core.settings import SettingsManager


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
        self._settings = SettingsManager()

        self.setObjectName("IEBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._setup_ui()
        self._apply_style()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Top row: label
        self.prompt_label = QLabel("Edit:")
        self.prompt_label.setObjectName("IEPrompt")
        layout.addWidget(self.prompt_label)

        # Instruction input — tall single-line field
        self.instruction_input = _InlineLineEdit()
        self.instruction_input.setObjectName("IEInput")
        self.instruction_input.setPlaceholderText(
            "Type instruction, Enter to send \u2014 Enter/Tab to accept, Esc to undo"
        )
        self.instruction_input.setMinimumHeight(38)
        self.instruction_input.enter_pressed.connect(self._on_submit)
        self.instruction_input.tab_pressed.connect(self._on_tab)
        self.instruction_input.escape_pressed.connect(self._on_cancel)
        layout.addWidget(self.instruction_input)

        # Status label (hints + generating state)
        self.status_label = QLabel("")
        self.status_label.setObjectName("IEStatus")
        layout.addWidget(self.status_label)

    def _apply_style(self) -> None:
        """Apply a high-contrast style so the bar stands out from the editor."""
        theme = self._settings.get_current_theme()
        accent = theme.keyword
        bg = theme.chrome_bg
        input_bg = theme.background
        fg = theme.foreground
        border = theme.chrome_border
        radius_large = theme.radius_large
        radius = theme.radius

        # Win95: explicit per-side beveled borders
        if theme.is_beveled:
            outer_border = theme.bevel_raised
            input_border = theme.bevel_sunken
            input_border_focus = theme.bevel_sunken
        else:
            outer_border = f"border: 2px solid {accent};"
            input_border = f"border: 1px solid {border};"
            input_border_focus = f"border: 2px solid {accent};"

        self.setStyleSheet(f"""
            QWidget#IEBar {{
                background-color: {bg};
                color: {fg};
                font-size: 12px;
                {outer_border}
                border-radius: {radius_large};
            }}
            QLabel#IEPrompt {{
                background-color: transparent;
                color: {accent};
                border: none;
                font-weight: bold;
            }}
            QLabel#IEStatus {{
                background-color: transparent;
                border: none;
                font-size: 11px;
            }}
            QLineEdit#IEInput {{
                background-color: {input_bg};
                color: {fg};
                {input_border}
                border-radius: {radius};
                padding: 6px 10px;
                font-size: 13px;
                selection-background-color: {accent};
                selection-color: {bg};
            }}
            QLineEdit#IEInput:focus {{
                {input_border_focus}
            }}
        """)

        self._status_color = f"rgba({self._hex_components(fg)}, 0.6)"
        self._error_color = "#c45c5c"

    @staticmethod
    def _hex_components(hex_color: str) -> str:
        """Convert #RRGGBB to 'R, G, B' for use in rgba()."""
        h = hex_color.lstrip("#")
        return f"{int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}"

    def apply_theme(self) -> None:
        """Public method for external theme updates."""
        self._settings = SettingsManager()
        self._apply_style()

    def show_bar(self) -> None:
        """Show the bar and focus the instruction input."""
        self._edit_complete = False
        self.status_label.setText("")
        self.instruction_input.clear()
        self.instruction_input.setEnabled(True)
        self.show()
        self.raise_()
        self.instruction_input.setFocus()

    def hide_bar(self) -> None:
        """Hide the bar and return focus to parent."""
        self.hide()
        if self.parent():
            self.parent().setFocus()

    def set_status(self, text: str) -> None:
        """Update the status label text."""
        self.status_label.setText(text)
        color = getattr(self, "_status_color", "rgba(180, 210, 190, 0.6)")
        self.status_label.setStyleSheet(
            f"background: transparent; color: {color}; border: none; font-size: 11px;"
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
        color = getattr(self, "_error_color", "#c45c5c")
        self.status_label.setText(f"Error: {message}")
        self.status_label.setStyleSheet(
            f"background: transparent; color: {color}; border: none; font-size: 11px;"
        )
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
