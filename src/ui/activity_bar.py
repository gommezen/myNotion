"""
Activity bar - VS Code style vertical icon bar for panel switching.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QToolButton, QVBoxLayout, QWidget

from core.settings import SettingsManager
from ui.theme_engine import hex_to_rgba


class ActivityBar(QWidget):
    """Vertical icon bar for switching between panels."""

    panel_selected = pyqtSignal(str)  # "ai" or "files"

    # Icons (using Unicode symbols)
    AI_ICON = "◈"
    FILES_ICON = "☰"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(36)
        self._active_panel = "ai"
        self._collapsed = False
        self._setup_ui()
        self._update_background()
        self._apply_style()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        # AI panel button
        self.ai_btn = QToolButton()
        self.ai_btn.setText(self.AI_ICON)
        self.ai_btn.setToolTip("AI Assistant")
        self.ai_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ai_btn.setFixedSize(32, 32)
        self.ai_btn.clicked.connect(lambda: self._on_button_clicked("ai"))
        layout.addWidget(self.ai_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Files panel button
        self.files_btn = QToolButton()
        self.files_btn.setText(self.FILES_ICON)
        self.files_btn.setToolTip("File Browser")
        self.files_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.files_btn.setFixedSize(32, 32)
        self.files_btn.clicked.connect(lambda: self._on_button_clicked("files"))
        layout.addWidget(self.files_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()

    def _on_button_clicked(self, panel_id: str):
        """Handle button click - emit signal to switch panel."""
        self.panel_selected.emit(panel_id)

    def set_active(self, panel_id: str):
        """Set the active panel and update button styles."""
        self._active_panel = panel_id
        self._apply_style()

    def set_collapsed(self, collapsed: bool):
        """Set collapsed state and update background color."""
        self._collapsed = collapsed
        self._update_background()
        self._apply_style()

    def _update_background(self):
        """Update background color based on collapsed state."""
        theme = SettingsManager().get_current_theme()
        bg = theme.background if self._collapsed else theme.chrome_bg
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(bg))
        self.setPalette(palette)

    def _apply_style(self):
        """Apply styles with active/inactive states."""
        theme = SettingsManager().get_current_theme()
        fg = theme.foreground
        active_color = theme.function
        inactive_color = hex_to_rgba(fg, 0.4)
        hover_color = hex_to_rgba(fg, 0.65)

        # AI button style - active has left border indicator
        ai_color = active_color if self._active_panel == "ai" else inactive_color
        ai_border = f"border-left: 2px solid {active_color};" if self._active_panel == "ai" else ""
        self.ai_btn.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                border: none;
                {ai_border}
                color: {ai_color};
                font-size: 18px;
                padding: 4px;
            }}
            QToolButton:hover {{
                color: {hover_color if self._active_panel != "ai" else active_color};
            }}
        """)

        # Files button style - active has left border indicator
        files_color = active_color if self._active_panel == "files" else inactive_color
        files_border = (
            f"border-left: 2px solid {active_color};" if self._active_panel == "files" else ""
        )
        self.files_btn.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                border: none;
                {files_border}
                color: {files_color};
                font-size: 18px;
                padding: 4px;
            }}
            QToolButton:hover {{
                color: {hover_color if self._active_panel != "files" else active_color};
            }}
        """)

    def apply_theme(self):
        """Public method for external theme updates."""
        self._update_background()
        self._apply_style()
