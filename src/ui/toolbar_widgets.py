"""
Custom toolbar widgets for formatting options.
"""

from typing import Any

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QMenu,
    QToolButton,
    QWidget,
)


class FormattingToolbar(QWidget):
    """Inline formatting toolbar containing all format buttons."""

    heading_selected = pyqtSignal(int)  # H1=1, H2=2, etc.
    bold_clicked = pyqtSignal()
    italic_clicked = pyqtSignal()
    clear_format_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(2)

        # Headings dropdown
        self.headings_btn = QToolButton()
        self.headings_btn.setText("H1")
        self.headings_btn.setToolTip("Insert Heading")
        self.headings_btn.setFixedHeight(22)
        self.headings_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        headings_menu = QMenu(self)
        heading_names = {
            1: "Title",
            2: "Subtitle",
            3: "Heading",
            4: "Subheading",
            5: "Body",
            6: "Caption",
        }
        for i in range(1, 7):
            action = headings_menu.addAction(heading_names[i])
            action.triggered.connect(lambda checked, level=i: self.heading_selected.emit(level))
        self.headings_btn.setMenu(headings_menu)
        layout.addWidget(self.headings_btn)

        # Bold
        self.bold_btn = QToolButton()
        self.bold_btn.setText("B")
        self.bold_btn.setToolTip("Bold (Ctrl+B)")
        self.bold_btn.setFixedHeight(22)
        self.bold_btn.clicked.connect(self.bold_clicked.emit)
        layout.addWidget(self.bold_btn)

        # Italic
        self.italic_btn = QToolButton()
        self.italic_btn.setText("I")
        self.italic_btn.setToolTip("Italic (Ctrl+I)")
        self.italic_btn.setFixedHeight(22)
        self.italic_btn.clicked.connect(self.italic_clicked.emit)
        layout.addWidget(self.italic_btn)

        # Clear formatting
        self.clear_btn = QToolButton()
        self.clear_btn.setText("A\u0336")  # Strikethrough A
        self.clear_btn.setToolTip("Clear Formatting")
        self.clear_btn.setFixedHeight(22)
        self.clear_btn.clicked.connect(self.clear_format_clicked.emit)
        layout.addWidget(self.clear_btn)

    @staticmethod
    def _hex_to_rgba(hex_color: str, alpha: float) -> str:
        """Convert hex color to rgba() CSS string."""
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    def apply_theme(self, theme: Any):
        """Apply theme colors to all buttons."""
        fg_mid = self._hex_to_rgba(theme.foreground, 0.55)
        if theme.is_beveled:
            button_style = f"""
                QToolButton {{
                    background-color: {theme.chrome_hover};
                    color: {fg_mid};
                    {theme.bevel_raised}
                    padding: 4px 10px;
                    font-weight: bold;
                    font-size: 11px;
                }}
                QToolButton:hover {{
                    color: {theme.foreground};
                }}
                QToolButton:pressed {{
                    background-color: {theme.chrome_bg};
                    {theme.bevel_sunken}
                    color: {theme.keyword};
                }}
                QToolButton::menu-indicator {{
                    image: none;
                    width: 8px;
                }}
            """
        else:
            pressed_bg = self._hex_to_rgba(theme.keyword, 0.15)
            button_style = f"""
                QToolButton {{
                    background-color: {theme.chrome_hover};
                    color: {fg_mid};
                    border: 1px solid {theme.chrome_border};
                    border-radius: {theme.radius};
                    padding: 4px 10px;
                    font-weight: bold;
                    font-size: 11px;
                }}
                QToolButton:hover {{
                    color: {theme.foreground};
                    border: 1px solid {self._hex_to_rgba(theme.foreground, 0.3)};
                }}
                QToolButton:pressed {{
                    background-color: {pressed_bg};
                    border: 1px solid {theme.keyword};
                    color: {theme.keyword};
                }}
                QToolButton::menu-indicator {{
                    image: none;
                    width: 8px;
                }}
            """

        menu_style = f"""
            QMenu {{
                background-color: {theme.chrome_bg};
                color: {theme.foreground};
                border: 1px solid {theme.chrome_border};
                padding: 4px 0px;
            }}
            QMenu::item {{
                padding: 6px 20px;
            }}
            QMenu::item:selected {{
                background-color: {theme.selection};
            }}
        """

        for btn in [
            self.headings_btn,
            self.bold_btn,
            self.italic_btn,
            self.clear_btn,
        ]:
            btn.setStyleSheet(button_style)

        # Style the menus
        if self.headings_btn.menu():
            self.headings_btn.menu().setStyleSheet(menu_style)
