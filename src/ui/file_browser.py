"""
File browser panel - Tree view for browsing project files.
"""

import os
from pathlib import Path

from PyQt6.QtCore import QDir, QModelIndex, pyqtSignal
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from core.settings import SettingsManager


class FileBrowserPanel(QWidget):
    """File tree sidebar for browsing project files."""

    file_selected = pyqtSignal(str)  # filepath to open

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 6)

        self.title_label = QLabel("FILES")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        # Open folder button
        self.open_folder_btn = QPushButton("📁")
        self.open_folder_btn.setFixedSize(20, 20)
        self.open_folder_btn.setToolTip("Open project folder")
        self.open_folder_btn.clicked.connect(self.open_folder_dialog)
        header_layout.addWidget(self.open_folder_btn)

        layout.addWidget(header)

        # File tree
        self.tree_view = QTreeView()
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setAnimated(True)
        self.tree_view.setIndentation(16)
        self.tree_view.doubleClicked.connect(self._on_item_double_clicked)

        # File system model
        self.model = QFileSystemModel()
        self.model.setRootPath("")

        # Filter out common non-essential directories and files
        self.model.setNameFilterDisables(False)
        filters = QDir.Filter.NoDotAndDotDot | QDir.Filter.AllDirs | QDir.Filter.Files
        self.model.setFilter(filters)

        self.tree_view.setModel(self.model)

        # Hide size, type, date columns - show only name
        self.tree_view.setColumnHidden(1, True)
        self.tree_view.setColumnHidden(2, True)
        self.tree_view.setColumnHidden(3, True)

        # Set root to current working directory
        self.set_root_path(os.getcwd())

        layout.addWidget(self.tree_view, stretch=1)

    def set_root_path(self, path: str):
        """Set the root directory for the file browser."""
        if Path(path).exists():
            root_index = self.model.setRootPath(path)
            self.tree_view.setRootIndex(root_index)

    def open_folder_dialog(self):
        """Open a folder picker to select project root."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Project Folder",
            self.model.rootPath(),
            QFileDialog.Option.ShowDirsOnly,
        )
        if folder:
            self.set_root_path(folder)

    def _on_item_double_clicked(self, index: QModelIndex):
        """Handle double-click on a file item."""
        filepath = self.model.filePath(index)
        if Path(filepath).is_file():
            self.file_selected.emit(filepath)

    @staticmethod
    def _hex_to_rgba(hex_color: str, alpha: float) -> str:
        """Convert hex color to rgba() CSS string."""
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    def _apply_style(self):
        """Apply current theme styling."""
        theme = SettingsManager().get_current_theme()
        bg = theme.background
        fg = theme.foreground
        text_main = self._hex_to_rgba(fg, 0.65)
        text_dim = self._hex_to_rgba(fg, 0.5)
        selection_bg = self._hex_to_rgba(fg, 0.15)
        hover_bg = self._hex_to_rgba(fg, 0.08)

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg};
                color: {text_main};
                font-family: 'Consolas', 'SF Mono', monospace;
            }}
        """)

        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {text_dim};
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 0.1em;
                text-transform: uppercase;
            }}
        """)

        self.open_folder_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {hover_bg};
                border-radius: 3px;
            }}
        """)

        self.tree_view.setStyleSheet(f"""
            QTreeView {{
                background-color: {bg};
                color: {text_main};
                border: none;
                padding: 4px 8px;
                font-size: 11px;
            }}
            QTreeView::item {{
                padding: 4px 8px;
                border-radius: 3px;
            }}
            QTreeView::item:hover {{
                background-color: {hover_bg};
            }}
            QTreeView::item:selected {{
                background-color: {selection_bg};
                color: {fg};
            }}
            QTreeView::branch {{
                background-color: {bg};
            }}
            QTreeView::branch:has-siblings:!adjoins-item {{
                border-image: none;
            }}
            QTreeView::branch:has-siblings:adjoins-item {{
                border-image: none;
            }}
            QTreeView::branch:!has-children:!has-siblings:adjoins-item {{
                border-image: none;
            }}
            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {{
                image: none;
                border-image: none;
            }}
            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {{
                image: none;
                border-image: none;
            }}
            QScrollBar:vertical {{
                background: {bg};
                width: 8px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {self._hex_to_rgba(fg, 0.2)};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {self._hex_to_rgba(fg, 0.3)};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)

    def apply_theme(self):
        """Public method for external theme updates."""
        self._apply_style()
