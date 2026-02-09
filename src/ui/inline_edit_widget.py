"""
Inline AI Edit bar widget — floating instruction input for Ctrl+K edit.

Beacon Pulse design: single horizontal bar with icon | input | status hint.
Pulses gold border during generation, turns green on completion.
"""

from enum import Enum, auto

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QWidget,
)

from core.settings import EditorTheme, SettingsManager


class _BarState(Enum):
    """Visual states for the inline edit bar."""

    IDLE = auto()
    GENERATING = auto()
    COMPLETE = auto()
    ERROR = auto()


class _InlineLineEdit(QLineEdit):
    """QLineEdit that intercepts Enter, Tab, and Escape for the inline edit bar."""

    enter_pressed = pyqtSignal()
    tab_pressed = pyqtSignal()
    escape_pressed = pyqtSignal()

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
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


# -- Color constants ---------------------------------------------------------
_GOLD_BRIGHT = "#E8C547"
_GOLD_DIM = "#9A7D2E"
_GREEN = "#5CB85C"
_RED = "#C45C5C"


class InlineEditBar(QWidget):
    """Floating bar for inline AI code editing instructions.

    Beacon Pulse design — single-row layout:
      ◈  |  input field  |  status hint
    """

    edit_requested = pyqtSignal(str)  # User submitted an instruction
    cancelled = pyqtSignal()  # User pressed Escape
    accepted = pyqtSignal()  # User accepted the completed edit

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._edit_complete = False
        self._settings = SettingsManager()
        self._state = _BarState.IDLE
        self._pulse_on = False
        self._error_msg = ""

        self.setObjectName("IEBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Pulse timer for generating state
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(750)
        self._pulse_timer.timeout.connect(self._on_pulse_tick)

        self._setup_ui()
        self._apply_style()

    # -- Layout ---------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 14, 8)
        layout.setSpacing(8)

        # Left: diamond icon
        self._icon_label = QLabel("\u25c8")
        self._icon_label.setObjectName("IEIcon")
        self._icon_label.setFixedWidth(20)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._icon_label)

        # Center: instruction input (stretch)
        self.instruction_input = _InlineLineEdit()
        self.instruction_input.setObjectName("IEInput")
        self.instruction_input.setPlaceholderText("Type instruction\u2026")
        self.instruction_input.setMinimumHeight(28)
        self.instruction_input.enter_pressed.connect(self._on_submit)
        self.instruction_input.tab_pressed.connect(self._on_tab)
        self.instruction_input.escape_pressed.connect(self._on_cancel)
        layout.addWidget(self.instruction_input, stretch=1)

        # Right: status hint
        self._status_label = QLabel("")
        self._status_label.setObjectName("IEHint")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._status_label)

    # -- Styling --------------------------------------------------------------

    def _apply_style(self) -> None:
        """Apply base styling from current theme, then update visual state."""
        theme = self._settings.get_current_theme()
        bg = EditorTheme._darken(theme.chrome_bg, 8)
        fg = theme.foreground

        # Store theme values for border updates
        self._fg = fg
        self._theme_bg = bg
        self._is_beveled = theme.is_beveled
        self._theme = theme

        # Child widget styles (stable, don't change with state)
        self._child_qss = f"""
            QLineEdit#IEInput {{
                background-color: transparent;
                color: {fg};
                border: none;
                padding: 4px 6px;
                font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
                font-size: 13px;
                selection-background-color: {_GOLD_DIM};
                selection-color: {theme.background};
            }}
            QLabel#IEIcon {{
                background: transparent;
                border: none;
                font-size: 14px;
            }}
            QLabel#IEHint {{
                background: transparent;
                border: none;
                font-size: 11px;
            }}
        """

        # Build initial bar border
        if theme.is_beveled:
            self._bar_border_qss = theme.bevel_raised
        else:
            self._bar_border_qss = f"border: 1px solid {_GOLD_DIM};"

        self._rebuild_stylesheet()
        self._update_visual_state()

    def _update_visual_state(self) -> None:
        """Update icon, hint text, and border color based on current state."""
        if self._state == _BarState.IDLE:
            self._set_icon("\u25c8", _GOLD_DIM)
            self._set_hint("Enter \u21b5", _GOLD_DIM)
            self._set_border(_GOLD_DIM)
        elif self._state == _BarState.GENERATING:
            self._set_icon("\u25c8", _GOLD_BRIGHT)
            self._set_hint("Generating\u2026", _GOLD_BRIGHT)
            border = _GOLD_BRIGHT if self._pulse_on else _GOLD_DIM
            self._set_border(border)
        elif self._state == _BarState.COMPLETE:
            self._set_icon("\u2713", _GREEN)
            self._set_hint("Enter \u2713 \u00b7 Esc \u2717", _GOLD_DIM)
            self._set_border(_GREEN)
        elif self._state == _BarState.ERROR:
            self._set_icon("\u2717", _RED)
            self._set_hint(f"Error: {self._error_msg}", _RED)
            self._set_border(_RED)

    def _set_icon(self, char: str, color: str) -> None:
        self._icon_label.setText(char)
        self._icon_label.setStyleSheet(
            f"color: {color}; background: transparent; border: none; font-size: 14px;"
        )

    def _set_hint(self, text: str, color: str) -> None:
        self._status_label.setText(text)
        self._status_label.setStyleSheet(
            f"color: {color}; background: transparent; border: none; font-size: 11px;"
        )

    def _set_border(self, color: str) -> None:
        """Update the outer border color by rebuilding the stylesheet."""
        if self._is_beveled:
            return  # Win95 uses bevel borders, don't override
        self._bar_border_qss = f"border: 1px solid {color};"
        self._rebuild_stylesheet()

    def _rebuild_stylesheet(self) -> None:
        """Rebuild the full stylesheet from stored parts."""
        radius = self._theme.radius_large
        self.setStyleSheet(
            f"""
            QWidget#IEBar {{
                background-color: {self._theme_bg};
                {self._bar_border_qss}
                border-radius: {radius};
            }}
            {self._child_qss}
        """
        )

    # -- Pulse animation ------------------------------------------------------

    def _on_pulse_tick(self) -> None:
        """Toggle pulse state and update border."""
        self._pulse_on = not self._pulse_on
        self._update_visual_state()

    # -- Public API -----------------------------------------------------------

    def apply_theme(self) -> None:
        """Public method for external theme updates."""
        self._settings = SettingsManager()
        self._apply_style()

    def show_bar(self) -> None:
        """Show the bar and focus the instruction input."""
        self._edit_complete = False
        self._error_msg = ""
        self._state = _BarState.IDLE
        self.instruction_input.clear()
        self.instruction_input.setEnabled(True)
        self._update_visual_state()
        self.show()
        self.raise_()
        self.instruction_input.setFocus()

    def hide_bar(self) -> None:
        """Hide the bar and return focus to parent."""
        self._pulse_timer.stop()
        self._pulse_on = False
        self.hide()
        if self.parent():
            self.parent().setFocus()

    def set_status(self, text: str) -> None:
        """Update the status hint text (used externally for custom messages)."""
        self._set_hint(text, _GOLD_DIM)

    def set_generating(self, generating: bool) -> None:
        """Toggle between generating and done state."""
        self.instruction_input.setEnabled(not generating)
        if generating:
            self._edit_complete = False
            self._state = _BarState.GENERATING
            self._pulse_on = False
            self._pulse_timer.start()
        else:
            self._edit_complete = True
            self._pulse_timer.stop()
            self._pulse_on = False
            self._state = _BarState.COMPLETE
            self.instruction_input.setFocus()
        self._update_visual_state()

    def set_error(self, message: str) -> None:
        """Show error message in red."""
        self._error_msg = message
        self._state = _BarState.ERROR
        self._pulse_timer.stop()
        self._pulse_on = False
        self.instruction_input.setEnabled(True)
        self._edit_complete = False
        self._update_visual_state()

    # -- Key handlers ---------------------------------------------------------

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

    # -- Backward compat for status_label access ------------------------------

    @property
    def status_label(self) -> QLabel:
        """Backward-compatible access to the status/hint label."""
        return self._status_label
