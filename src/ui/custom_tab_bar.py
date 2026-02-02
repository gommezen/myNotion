"""
Custom tab bar with styled close buttons.
"""

import contextlib

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QPushButton, QTabBar


class CloseButton(QPushButton):
    """Custom close button with white X."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: #E81123;
            }
        """)

    def paintEvent(self, event):
        """Draw the X icon."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(QColor("#CCCCCC"))
        pen.setWidth(2)
        painter.setPen(pen)

        margin = 4
        size = self.width()
        painter.drawLine(margin, margin, size - margin, size - margin)
        painter.drawLine(size - margin, margin, margin, size - margin)


class CustomTabBar(QTabBar):
    """Tab bar with custom close buttons."""

    tab_close_requested = pyqtSignal(int)
    new_tab_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(True)
        self.setExpanding(False)
        self.setDrawBase(False)

    def tabInserted(self, index: int):
        """Add close button when tab is inserted."""
        super().tabInserted(index)

        close_btn = CloseButton(self)
        self.setTabButton(index, QTabBar.ButtonPosition.RightSide, close_btn)

        self._update_close_buttons()

    def tabRemoved(self, index: int):
        """Update after tab is removed."""
        super().tabRemoved(index)
        self._update_close_buttons()

    def _update_close_buttons(self):
        """Update close button connections after tab changes."""
        for i in range(self.count()):
            btn = self.tabButton(i, QTabBar.ButtonPosition.RightSide)
            if btn:
                with contextlib.suppress(TypeError):
                    btn.clicked.disconnect()
                btn.clicked.connect(lambda checked, idx=i: self.tab_close_requested.emit(idx))

    def mouseDoubleClickEvent(self, event):
        """Double-click on empty area creates new tab."""
        for i in range(self.count()):
            if self.tabRect(i).contains(event.pos()):
                super().mouseDoubleClickEvent(event)
                return
        self.new_tab_requested.emit()
