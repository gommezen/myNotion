"""
Main application window with tabs, menus, and toolbar.
"""

import contextlib
from pathlib import Path

from PyQt6.QtCore import QSettings, Qt, QTimer
from PyQt6.QtGui import (
    QAction,
    QActionGroup,
    QIcon,
    QKeySequence,
)
from PyQt6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QToolButton,
)

from core.recent_files import RecentFilesManager
from core.settings import SettingsManager
from syntax.highlighter import Language
from ui.custom_tab_bar import CustomTabBar
from ui.editor_tab import EditorTab
from ui.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("MyNotion", "Editor")
        self.settings_manager = SettingsManager()
        self.recent_files = RecentFilesManager(self)

        self._apply_theme()
        self._setup_ui()
        self._setup_menus()
        self._setup_toolbar()
        self._setup_statusbar()
        self._restore_geometry()

        # Connect recent files changes
        self.recent_files.files_changed.connect(self._update_recent_menu)

        # Create initial tab
        self.new_tab()

    def _apply_theme(self):
        """Apply current theme to the entire application."""
        theme = self.settings_manager.get_current_theme()

        # Use theme's chrome colors
        bg = theme.background
        chrome_bg = theme.chrome_bg
        chrome_hover = theme.chrome_hover
        chrome_border = theme.chrome_border
        fg = theme.foreground
        selection = theme.selection

        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {bg};
            }}
            QMenuBar {{
                background-color: {chrome_bg};
                color: {fg};
                border: none;
                padding: 2px;
            }}
            QMenuBar::item {{
                padding: 4px 8px;
                background-color: transparent;
            }}
            QMenuBar::item:selected {{
                background-color: {chrome_hover};
            }}
            QMenu {{
                background-color: {chrome_bg};
                color: {fg};
                border: 1px solid {chrome_border};
                padding: 4px 0px;
            }}
            QMenu::item {{
                padding: 6px 30px 6px 20px;
            }}
            QMenu::item:selected {{
                background-color: {selection};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {chrome_border};
                margin: 4px 10px;
            }}
            QToolBar {{
                background-color: {chrome_bg};
                border: none;
                border-bottom: 1px solid {chrome_border};
                spacing: 2px;
                padding: 4px 8px;
            }}
            QToolBar QToolButton {{
                background-color: transparent;
                color: {fg};
                border: none;
                border-radius: 3px;
                padding: 4px 10px;
                font-weight: bold;
                font-size: 12px;
            }}
            QToolBar QToolButton:hover {{
                background-color: {chrome_hover};
            }}
            QToolBar QToolButton:pressed {{
                background-color: {selection};
            }}
            QTabWidget::pane {{
                border: none;
                background-color: {bg};
            }}
            QTabBar {{
                background-color: {chrome_bg};
            }}
            QTabBar::tab {{
                background-color: {chrome_bg};
                color: {fg};
                padding: 8px 20px;
                border: none;
                border-right: 1px solid {chrome_border};
                min-width: 100px;
            }}
            QTabBar::tab:selected {{
                background-color: {bg};
                color: {fg};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {chrome_hover};
            }}
            QStatusBar {{
                background-color: {chrome_bg};
                color: {fg};
                border-top: 1px solid {chrome_border};
            }}
            QStatusBar::item {{
                border: none;
            }}
            QStatusBar QLabel {{
                color: {fg};
                padding: 2px 12px;
                font-size: 12px;
            }}
            QStatusBar QLabel:hover {{
                background-color: {chrome_hover};
            }}
        """)

    def _setup_ui(self):
        """Initialize the main UI components."""
        self.setWindowTitle("MyNotion")
        self.setMinimumSize(300, 200)  # Allow small window like Notepad

        # Set Moloch icon (Metropolis theme)
        icon_path = Path(__file__).parent.parent.parent / "resources" / "moloch.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Tab widget for multiple documents
        self.tab_widget = QTabWidget(self)

        # Use custom tab bar with styled close buttons
        self.custom_tab_bar = CustomTabBar(self.tab_widget)
        self.custom_tab_bar.new_tab_requested.connect(self._on_new_tab_requested)
        self.tab_widget.setTabBar(self.custom_tab_bar)
        self.custom_tab_bar.tab_close_requested.connect(self.close_tab)

        self.tab_widget.setTabsClosable(False)  # We handle close buttons ourselves
        self.tab_widget.setMovable(True)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self.tab_widget)

        # Create + button on the tab widget (not tab bar) so it's always visible
        self.new_tab_btn = QToolButton(self.tab_widget)
        self.new_tab_btn.setText("+")
        self.new_tab_btn.setFixedSize(28, 28)
        self.new_tab_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_tab_btn.clicked.connect(self.new_tab)
        self._update_new_tab_button_style()

        # Connect tab changes to update + button position
        self.custom_tab_bar.tabInserted = self._wrap_tab_inserted(self.custom_tab_bar.tabInserted)
        self.custom_tab_bar.tabRemoved = self._wrap_tab_removed(self.custom_tab_bar.tabRemoved)

        # Initial position update
        self._update_new_tab_button_position()

    def _wrap_tab_inserted(self, original_func):
        """Wrap tabInserted to update + button position."""

        def wrapper(index):
            original_func(index)
            QTimer.singleShot(20, self._update_new_tab_button_position)

        return wrapper

    def _wrap_tab_removed(self, original_func):
        """Wrap tabRemoved to update + button position."""

        def wrapper(index):
            original_func(index)
            QTimer.singleShot(20, self._update_new_tab_button_position)

        return wrapper

    def _update_new_tab_button_position(self):
        """Position the + button right after the last tab."""
        if self.custom_tab_bar.count() > 0:
            last_rect = self.custom_tab_bar.tabRect(self.custom_tab_bar.count() - 1)
            # Map to tab widget coordinates
            x = last_rect.right() + 8
            y = last_rect.top() + (last_rect.height() - self.new_tab_btn.height()) // 2
            self.new_tab_btn.move(x, y)
        else:
            self.new_tab_btn.move(8, 4)
        self.new_tab_btn.raise_()
        self.new_tab_btn.show()

    def _update_new_tab_button_style(self):
        """Update + button style to match current theme."""
        theme = self.settings_manager.get_current_theme()
        self.new_tab_btn.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                color: {theme.foreground};
                border: none;
                font-size: 18px;
                font-weight: bold;
            }}
            QToolButton:hover {{
                background-color: {theme.chrome_hover};
                border-radius: 3px;
            }}
        """)

    def resizeEvent(self, event):
        """Handle resize to update + button position."""
        super().resizeEvent(event)
        if hasattr(self, "new_tab_btn"):
            QTimer.singleShot(10, self._update_new_tab_button_position)

    def _on_new_tab_requested(self):
        """Handle new tab request from tab bar double-click."""
        self.new_tab()

    def _setup_menus(self):
        """Create the menu bar and menus."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu(self.tr("&File"))

        new_action = QAction(self.tr("New tab"), self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_tab)
        file_menu.addAction(new_action)

        open_action = QAction(self.tr("Open"), self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        # Recent files submenu
        self.recent_menu = file_menu.addMenu(self.tr("Recent"))
        self._update_recent_menu()

        file_menu.addSeparator()

        save_action = QAction(self.tr("Save"), self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        save_as_action = QAction(self.tr("Save as"), self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        exit_action = QAction(self.tr("Exit"), self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu(self.tr("&Edit"))

        undo_action = QAction(self.tr("Undo"), self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self._undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction(self.tr("Redo"), self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self._redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        cut_action = QAction(self.tr("Cut"), self)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        cut_action.triggered.connect(self._cut)
        edit_menu.addAction(cut_action)

        copy_action = QAction(self.tr("Copy"), self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.triggered.connect(self._copy)
        edit_menu.addAction(copy_action)

        paste_action = QAction(self.tr("Paste"), self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.triggered.connect(self._paste)
        edit_menu.addAction(paste_action)

        # View menu
        view_menu = menubar.addMenu(self.tr("&View"))

        zoom_in_action = QAction(self.tr("Zoom in"), self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(self._zoom_in)
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction(self.tr("Zoom out"), self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.triggered.connect(self._zoom_out)
        view_menu.addAction(zoom_out_action)

        view_menu.addSeparator()

        # Language submenu
        self.language_menu = view_menu.addMenu(self.tr("Language"))
        self.language_actions = QActionGroup(self)
        self.language_actions.setExclusive(True)

        for lang in Language:
            action = QAction(lang.name.capitalize(), self)
            action.setCheckable(True)
            action.setData(lang)
            action.triggered.connect(self._on_language_selected)
            self.language_actions.addAction(action)
            self.language_menu.addAction(action)

        view_menu.addSeparator()

        # Settings
        settings_action = QAction(self.tr("Settings..."), self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._show_settings)
        view_menu.addAction(settings_action)

    def _setup_toolbar(self):
        """Create the formatting toolbar."""
        toolbar = QToolBar(self.tr("Formatting"), self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Bold
        bold_action = QAction(self.tr("B"), self)
        bold_action.setToolTip(self.tr("Bold"))
        bold_action.setShortcut(QKeySequence.StandardKey.Bold)
        bold_action.triggered.connect(self._toggle_bold)
        toolbar.addAction(bold_action)

        # Italic
        italic_action = QAction(self.tr("I"), self)
        italic_action.setToolTip(self.tr("Italic"))
        italic_action.setShortcut(QKeySequence.StandardKey.Italic)
        italic_action.triggered.connect(self._toggle_italic)
        toolbar.addAction(italic_action)

    def _setup_statusbar(self):
        """Create the status bar with multiple indicators."""
        self.statusbar = QStatusBar(self)
        self.setStatusBar(self.statusbar)

        # Line/column indicator (leftmost)
        self.position_label = QLabel("Ln 1, Col 1")
        self.statusbar.addPermanentWidget(self.position_label)

        # Character count
        self.chars_label = QLabel("0 characters")
        self.statusbar.addPermanentWidget(self.chars_label)

        # Language indicator
        self.language_label = QLabel("Plain text")
        self.statusbar.addPermanentWidget(self.language_label)

        # Zoom indicator
        self.zoom_label = QLabel("100%")
        self.statusbar.addPermanentWidget(self.zoom_label)

        # Line ending indicator
        self.line_ending_label = QLabel("CRLF")
        self.statusbar.addPermanentWidget(self.line_ending_label)

        # Encoding indicator
        self.encoding_label = QLabel("UTF-8")
        self.statusbar.addPermanentWidget(self.encoding_label)

    def _restore_geometry(self):
        """Restore window geometry from settings."""
        geometry = self.settings.value("geometry")
        if geometry:
            success = self.restoreGeometry(geometry)
            if not success:
                # If restore fails, use default size
                self.resize(1000, 700)
        else:
            # No saved geometry, use default size
            self.resize(1000, 700)

    def closeEvent(self, event):
        """Save geometry and handle unsaved changes on close."""
        self.settings.setValue("geometry", self.saveGeometry())
        # TODO: Check for unsaved changes in all tabs
        event.accept()

    def _on_tab_changed(self, index: int):
        """Handle tab change to update status bar."""
        editor = self.current_editor()
        if editor:
            self._update_language_indicator(editor.language)
            self._connect_editor_signals(editor)

    def _connect_editor_signals(self, editor: EditorTab):
        """Connect editor signals for status bar updates."""
        # Disconnect previous connections if any
        with contextlib.suppress(TypeError):
            editor.cursorPositionChanged.disconnect(self._update_status_bar)
        with contextlib.suppress(TypeError):
            editor.textChanged.disconnect(self._update_status_bar)

        # Connect new signals
        editor.cursorPositionChanged.connect(self._update_status_bar)
        editor.textChanged.connect(self._update_status_bar)
        self._update_status_bar()

    def _update_status_bar(self):
        """Update all status bar indicators."""
        editor = self.current_editor()
        if not editor:
            return

        # Position
        cursor = editor.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        self.position_label.setText(f"Ln {line}, Col {col}")

        # Character count
        text = editor.toPlainText()
        char_count = len(text)
        if char_count == 1:
            self.chars_label.setText("1 character")
        else:
            self.chars_label.setText(f"{char_count:,} characters")

        # Zoom level
        zoom = 100 + (editor._zoom_level * 10)
        self.zoom_label.setText(f"{zoom}%")

        # Line ending detection
        if "\r\n" in text:
            self.line_ending_label.setText("CRLF")
        elif "\n" in text:
            self.line_ending_label.setText("LF")
        else:
            self.line_ending_label.setText("CRLF")  # Default for Windows

    def _update_language_indicator(self, language: Language):
        """Update the language indicator in status bar."""
        self.language_label.setText(language.name.capitalize())

        # Update the checked state in menu
        for action in self.language_actions.actions():
            if action.data() == language:
                action.setChecked(True)
                break

    def _on_language_selected(self):
        """Handle language selection from menu."""
        action = self.language_actions.checkedAction()
        if action and (editor := self.current_editor()):
            language = action.data()
            editor.set_language(language)
            self._update_language_indicator(language)

    def _update_recent_menu(self):
        """Update the recent files menu."""
        self.recent_menu.clear()

        files = self.recent_files.get_files()
        if files:
            for i, filepath in enumerate(files):
                display_name = self.recent_files.get_display_name(filepath)
                # Add number shortcut for first 9 files
                if i < 9:
                    display_name = f"&{i + 1}  {display_name}"

                action = QAction(display_name, self)
                action.setData(filepath)
                action.triggered.connect(self._open_recent_file)
                self.recent_menu.addAction(action)

            self.recent_menu.addSeparator()

            clear_action = QAction(self.tr("Clear Recent"), self)
            clear_action.triggered.connect(self._clear_recent_files)
            self.recent_menu.addAction(clear_action)
        else:
            no_recent = QAction(self.tr("No recent files"), self)
            no_recent.setEnabled(False)
            self.recent_menu.addAction(no_recent)

    def _open_recent_file(self):
        """Open a file from the recent files menu."""
        action = self.sender()
        if action:
            filepath = action.data()
            if Path(filepath).exists():
                self._open_file_path(filepath)
            else:
                # File no longer exists, remove from recent
                self.recent_files.remove_file(filepath)
                QMessageBox.warning(
                    self,
                    self.tr("File Not Found"),
                    self.tr(f"The file no longer exists:\n{filepath}"),
                )

    def _clear_recent_files(self):
        """Clear the recent files list."""
        self.recent_files.clear()

    def _open_file_path(self, filepath: str):
        """Open a specific file path in a new tab."""
        editor = self.new_tab()
        editor.load_file(filepath)
        self.tab_widget.setTabText(self.tab_widget.currentIndex(), Path(filepath).name)
        self._update_language_indicator(editor.language)
        self.recent_files.add_file(filepath)

    # Tab management
    def new_tab(self):
        """Create a new editor tab."""
        editor = EditorTab(parent=self.tab_widget)
        index = self.tab_widget.addTab(editor, self.tr("Untitled"))
        self.tab_widget.setCurrentIndex(index)
        self._connect_editor_signals(editor)
        return editor

    def close_tab(self, index: int):
        """Close the tab at the given index."""
        # TODO: Check for unsaved changes
        widget = self.tab_widget.widget(index)
        self.tab_widget.removeTab(index)
        widget.deleteLater()

        # Create new tab if all tabs closed
        if self.tab_widget.count() == 0:
            self.new_tab()

    def current_editor(self) -> EditorTab | None:
        """Get the current editor tab."""
        return self.tab_widget.currentWidget()

    # File operations
    def open_file(self):
        """Open a file dialog and load the selected file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Open File"),
            "",
            self.tr(
                "All Files (*);;Text Files (*.txt);;Python (*.py);;JavaScript (*.js);;HTML (*.html);;CSS (*.css);;JSON (*.json);;Markdown (*.md)"
            ),
        )
        if filepath:
            self._open_file_path(filepath)

    def save_file(self):
        """Save the current file."""
        editor = self.current_editor()
        if editor and editor.filepath:
            editor.save_file()
            self.recent_files.add_file(editor.filepath)
        else:
            self.save_file_as()

    def save_file_as(self):
        """Save the current file with a new name."""
        editor = self.current_editor()
        if not editor:
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save File"),
            "",
            self.tr(
                "All Files (*);;Text Files (*.txt);;Python (*.py);;JavaScript (*.js);;HTML (*.html);;CSS (*.css);;JSON (*.json);;Markdown (*.md)"
            ),
        )
        if filepath:
            editor.save_file(filepath)
            self.tab_widget.setTabText(self.tab_widget.currentIndex(), Path(filepath).name)
            self._update_language_indicator(editor.language)
            self.recent_files.add_file(filepath)

    # Edit operations (delegate to current editor)
    def _undo(self):
        if editor := self.current_editor():
            editor.undo()

    def _redo(self):
        if editor := self.current_editor():
            editor.redo()

    def _cut(self):
        if editor := self.current_editor():
            editor.cut()

    def _copy(self):
        if editor := self.current_editor():
            editor.copy()

    def _paste(self):
        if editor := self.current_editor():
            editor.paste()

    # View operations
    def _zoom_in(self):
        if editor := self.current_editor():
            editor.zoom_in()
            self._update_status_bar()

    def _zoom_out(self):
        if editor := self.current_editor():
            editor.zoom_out()
            self._update_status_bar()

    def _show_settings(self):
        """Show the settings dialog."""
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self._apply_settings_to_editors)
        dialog.exec()

    def _apply_settings_to_editors(self):
        """Apply changed settings to all editor tabs and window chrome."""
        # Re-apply window theme (menu bar, toolbar, tabs, status bar)
        self._apply_theme()
        self._update_new_tab_button_style()

        # Apply to all editor tabs
        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            if isinstance(editor, EditorTab):
                editor.apply_theme()
        self._update_status_bar()

    # Formatting - inserts markdown syntax for plain text
    def _toggle_bold(self):
        """Wrap selected text with bold markdown syntax (**)."""
        editor = self.current_editor()
        if not editor:
            return

        cursor = editor.textCursor()
        selected_text = cursor.selectedText()

        if selected_text:
            # Wrap selection with **
            cursor.insertText(f"**{selected_text}**")
        else:
            # Insert ** and place cursor in middle
            pos = cursor.position()
            cursor.insertText("****")
            cursor.setPosition(pos + 2)
            editor.setTextCursor(cursor)

    def _toggle_italic(self):
        """Wrap selected text with italic markdown syntax (*)."""
        editor = self.current_editor()
        if not editor:
            return

        cursor = editor.textCursor()
        selected_text = cursor.selectedText()

        if selected_text:
            # Wrap selection with *
            cursor.insertText(f"*{selected_text}*")
        else:
            # Insert ** and place cursor in middle
            pos = cursor.position()
            cursor.insertText("**")
            cursor.setPosition(pos + 1)
            editor.setTextCursor(cursor)
