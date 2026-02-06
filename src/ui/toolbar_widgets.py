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
    list_selected = pyqtSignal(str)  # "bullet" or "numbered"
    bold_clicked = pyqtSignal()
    italic_clicked = pyqtSignal()
    link_clicked = pyqtSignal()
    clear_format_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 8, 0)
        layout.setSpacing(2)

        # Headings dropdown
        self.headings_btn = QToolButton()
        self.headings_btn.setText("H1")
        self.headings_btn.setToolTip("Insert Heading")
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

        # Lists dropdown
        self.lists_btn = QToolButton()
        self.lists_btn.setText("\u2261")  # ≡ symbol for list
        self.lists_btn.setToolTip("Insert List")
        self.lists_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        lists_menu = QMenu(self)
        lists_menu.addAction("Bullet List").triggered.connect(
            lambda: self.list_selected.emit("bullet")
        )
        lists_menu.addAction("Numbered List").triggered.connect(
            lambda: self.list_selected.emit("numbered")
        )
        self.lists_btn.setMenu(lists_menu)
        layout.addWidget(self.lists_btn)

        # Separator
        layout.addSpacing(12)

        # Bold
        self.bold_btn = QToolButton()
        self.bold_btn.setText("B")
        self.bold_btn.setToolTip("Bold (Ctrl+B)")
        self.bold_btn.clicked.connect(self.bold_clicked.emit)
        layout.addWidget(self.bold_btn)

        # Italic
        self.italic_btn = QToolButton()
        self.italic_btn.setText("I")
        self.italic_btn.setToolTip("Italic (Ctrl+I)")
        self.italic_btn.clicked.connect(self.italic_clicked.emit)
        layout.addWidget(self.italic_btn)

        # Separator
        layout.addSpacing(12)

        # Link
        self.link_btn = QToolButton()
        self.link_btn.setText("\U0001f517")  # Link emoji
        self.link_btn.setToolTip("Insert Link (Ctrl+K)")
        self.link_btn.clicked.connect(self.link_clicked.emit)
        layout.addWidget(self.link_btn)

        # Separator
        layout.addSpacing(12)

        # Clear formatting
        self.clear_btn = QToolButton()
        self.clear_btn.setText("A\u0338")  # A with combining slash
        self.clear_btn.setToolTip("Clear Formatting")
        self.clear_btn.clicked.connect(self.clear_format_clicked.emit)
        layout.addWidget(self.clear_btn)

    def apply_theme(self, theme: Any):
        """Apply theme colors to all buttons."""
        button_style = f"""
            QToolButton {{
                background-color: transparent;
                color: {theme.foreground};
                border: none;
                border-radius: 3px;
                padding: 4px 10px;
                font-weight: bold;
                font-size: 10px;
            }}
            QToolButton:hover {{
                background-color: {theme.chrome_hover};
            }}
            QToolButton:pressed {{
                background-color: {theme.selection};
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
            self.lists_btn,
            self.bold_btn,
            self.italic_btn,
            self.link_btn,
            self.clear_btn,
        ]:
            btn.setStyleSheet(button_style)

        # Style the menus
        if self.headings_btn.menu():
            self.headings_btn.menu().setStyleSheet(menu_style)
        if self.lists_btn.menu():
            self.lists_btn.menu().setStyleSheet(menu_style)
