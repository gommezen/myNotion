"""
AI code completion controller — manages ghost text suggestions.

Owns the CompletionManager, wires editor signals, handles the toggle
button styling, and model selection popup.
"""

import contextlib
from collections.abc import Callable

from PyQt6.QtCore import QObject, Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QMainWindow, QMenu, QToolButton

from ai.completion import CompletionManager
from core.settings import SettingsManager
from ui.editor_tab import EditorTab
from ui.theme_engine import hex_to_rgba

# Models available for code completion (small, fast FIM models)
COMPLETION_MODELS = [
    {"id": "deepseek-coder:1.3b", "name": "DeepSeek Coder 1.3B"},
    {"id": "qwen2.5-coder:1.5b", "name": "Qwen 2.5 Coder 1.5B"},
    {"id": "codegemma:2b", "name": "CodeGemma 2B"},
]


class CompletionController(QObject):
    """Manages AI code completion lifecycle and UI state.

    Owns the CompletionManager, handles toggle/model selection,
    and wires/unwires editor completion signals on tab changes.
    """

    def __init__(
        self,
        parent: QMainWindow,
        get_editor: Callable[[], EditorTab | None],
        settings_manager: SettingsManager,
        completion_btn: QToolButton,
    ):
        super().__init__(parent)
        self._window = parent
        self._get_editor = get_editor
        self._settings = settings_manager
        self._btn = completion_btn

        # Completion backend
        self._manager = CompletionManager(parent)
        self._manager.suggestion_ready.connect(self._on_suggestion_ready)

        # Wire button
        self._btn.clicked.connect(self._toggle)
        self._btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._btn.customContextMenuRequested.connect(self._on_context_menu)

    def setup(self, window: QMainWindow) -> None:
        """Register shortcut and load saved state."""
        action = QAction(window.tr("Toggle Code Completion"), window)
        action.setShortcut(QKeySequence("Ctrl+Shift+Space"))
        action.triggered.connect(self._toggle)
        window.addAction(action)

        # Load saved state
        enabled = self._settings.get_completion_enabled()
        self._manager.set_enabled(enabled)
        self._manager.set_max_lines(self._settings.get_completion_max_lines())
        self.update_indicator()

    def connect_editor(self, editor: EditorTab) -> None:
        """Wire completion signals for a newly active editor."""
        enabled = self._manager.is_enabled()
        editor.set_completion_enabled(enabled)
        if enabled:
            editor.set_completion_delay(self._settings.get_completion_delay())
        editor.completion_requested.connect(self._on_editor_requested)

    def disconnect_editor(self, editor: EditorTab) -> None:
        """Disconnect completion signals from an editor."""
        with contextlib.suppress(TypeError):
            editor.completion_requested.disconnect(self._on_editor_requested)
        editor.clear_ghost_text()
        editor.set_completion_enabled(False)

    def cancel(self) -> None:
        """Cancel any pending completion request."""
        self._manager.cancel()

    def refresh_settings(self) -> None:
        """Re-read completion settings after settings dialog closes."""
        enabled = self._settings.get_completion_enabled()
        self._manager.set_enabled(enabled)
        self._manager.set_max_lines(self._settings.get_completion_max_lines())
        editor = self._get_editor()
        if editor:
            editor.set_completion_enabled(enabled)
            editor.set_completion_delay(self._settings.get_completion_delay())
        self.update_indicator()

    def update_indicator(self) -> None:
        """Update the AI button style and tooltip."""
        theme = self._settings.get_current_theme()
        enabled = self._manager.is_enabled()
        model = self._settings.get_completion_model()

        fg = theme.foreground
        if theme.is_beveled:
            border = theme.bevel_raised
        else:
            border = f"border: 1px solid {theme.chrome_border};border-radius: {theme.radius};"
        pressed_bg = hex_to_rgba(theme.keyword, 0.15)
        if theme.is_beveled:
            pressed_style = (
                f"QToolButton:pressed {{ background: {theme.chrome_bg};"
                f" {theme.bevel_sunken} color: {theme.keyword}; }}"
            )
        else:
            pressed_style = (
                f"QToolButton:pressed {{ background: {pressed_bg};"
                f" border: 1px solid {theme.keyword}; color: {theme.keyword}; }}"
            )
        hover_border = "" if theme.is_beveled else f" border: 1px solid {hex_to_rgba(fg, 0.3)};"
        if enabled:
            self._btn.setText("\u25c9 AI")
            self._btn.setToolTip(self._window.tr(f"AI Code Completion: ON \u2014 {model}"))
            self._btn.setStyleSheet(
                f"QToolButton {{ background: {theme.chrome_hover};"
                f" color: {theme.keyword}; font-size: 11px;"
                f" font-weight: bold; {border} padding: 0 8px; }}"
                f"QToolButton:hover {{ color: {fg};{hover_border} }}"
                f" {pressed_style}"
            )
        else:
            self._btn.setText("\u25c9 AI")
            self._btn.setToolTip(self._window.tr("AI Code Completion (Ctrl+Shift+Space)"))
            self._btn.setStyleSheet(
                f"QToolButton {{ background: {theme.chrome_hover};"
                f" color: {hex_to_rgba(fg, 0.55)}; font-size: 11px;"
                f" font-weight: bold; {border} padding: 0 8px; }}"
                f"QToolButton:hover {{ color: {fg};{hover_border} }}"
                f" {pressed_style}"
            )

    # ─── Internal handlers ───

    def _toggle(self) -> None:
        """Toggle AI code completion on/off."""
        enabled = not self._manager.is_enabled()
        self._manager.set_enabled(enabled)
        self._settings.set_completion_enabled(enabled)

        editor = self._get_editor()
        if editor:
            editor.set_completion_enabled(enabled)
            if enabled:
                delay = self._settings.get_completion_delay()
                editor.set_completion_delay(delay)

        self.update_indicator()

    def _on_context_menu(self, pos) -> None:
        """Show a popup menu to select the completion model."""
        menu = QMenu(self._window)
        current_model = self._settings.get_completion_model()

        for model_info in COMPLETION_MODELS:
            action = QAction(model_info["name"], self._window)
            action.setCheckable(True)
            action.setChecked(model_info["id"] == current_model)
            action.setData(model_info["id"])
            action.triggered.connect(self._on_model_selected)
            menu.addAction(action)

        menu.exec(self._btn.mapToGlobal(pos))

    def _on_model_selected(self) -> None:
        """Handle completion model selection from popup menu."""
        action = self.sender()
        if action:
            model_id = action.data()
            self._settings.set_completion_model(model_id)
            self.update_indicator()

    def _on_suggestion_ready(self, text: str) -> None:
        """Handle a completion suggestion from the CompletionManager."""
        editor = self._get_editor()
        if editor and self._manager.is_enabled():
            editor.set_ghost_text(text)

    def _on_editor_requested(self, prefix: str, suffix: str) -> None:
        """Forward editor's completion request to the CompletionManager."""
        model = self._settings.get_completion_model()
        self._manager.request_completion(prefix, suffix, model)
