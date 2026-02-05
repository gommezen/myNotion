"""
Main application window with tabs, menus, and toolbar.
"""

import contextlib
from pathlib import Path

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QSettings,
    Qt,
    QTimer,
)
from PyQt6.QtGui import (
    QAction,
    QActionGroup,
    QIcon,
    QKeySequence,
)
from PyQt6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QGraphicsOpacityEffect,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from core.recent_files import RecentFilesManager
from core.settings import SettingsManager
from syntax.highlighter import Language
from ui.activity_bar import ActivityBar
from ui.custom_tab_bar import CustomTabBar
from ui.editor_tab import EditorTab
from ui.file_browser import FileBrowserPanel
from ui.find_replace import FindReplaceBar
from ui.settings_dialog import SettingsDialog
from ui.side_panel import SidePanel
from ui.toolbar_widgets import FormattingToolbar


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("MyNotion", "Editor")
        self.settings_manager = SettingsManager()
        self.recent_files = RecentFilesManager(self)

        self._apply_theme()
        self._setup_ui()
        self._setup_side_panel()
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
                font-size: 10px;
            }}
            QMenuBar {{
                background-color: {chrome_bg};
                color: {fg};
                border: none;
                padding: 2px;
                font-size: 11px;
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
                font-size: 11px;
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
                font-size: 10px;
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
                background-color: #121f1f;
                font-size: 11px;
            }}
            QTabBar::tab {{
                background-color: #121f1f;
                color: rgba(180, 210, 190, 0.5);
                padding: 8px 12px 8px 10px;
                border: none;
                border-top: 2px solid transparent;
                min-width: 80px;
                margin-right: 0px;
            }}
            QTabBar::tab:selected {{
                background-color: #1a2a2a;
                color: #c8e0ce;
                border-top: 2px solid #d4a84b;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: #1a2a2a;
                color: rgba(180, 210, 190, 0.7);
            }}
            QStatusBar {{
                background-color: {chrome_bg};
                color: rgba(180, 210, 190, 0.6);
                border-top: 1px solid {chrome_border};
                font-size: 11px;
            }}
            QStatusBar::item {{
                border: none;
            }}
            QStatusBar QLabel {{
                color: rgba(180, 210, 190, 0.6);
                padding: 2px 12px;
                font-size: 10px;
            }}
            QStatusBar QLabel:hover {{
                color: #c8e0ce;
                background-color: {chrome_hover};
            }}
            QMessageBox {{
                background-color: {bg};
                color: {fg};
            }}
            QMessageBox QLabel {{
                color: {fg};
                font-size: 11px;
            }}
            QMessageBox QPushButton {{
                background-color: {chrome_bg};
                color: {fg};
                border: 1px solid {chrome_border};
                border-radius: 3px;
                padding: 6px 16px;
                min-width: 70px;
                font-size: 11px;
            }}
            QMessageBox QPushButton:hover {{
                background-color: {chrome_hover};
            }}
            QMessageBox QPushButton:pressed {{
                background-color: {selection};
            }}
            QMessageBox QPushButton:default {{
                border: 1px solid #d4a84b;
            }}
        """)

    def _setup_ui(self):
        """Initialize the main UI components."""
        self.setWindowTitle("MyNotion")
        self.setMinimumSize(300, 200)  # Allow small window like Notepad

        # Set MyNotion icon (Art Deco / Metropolis theme)
        icon_path = Path(__file__).parent.parent.parent / "resources" / "mynotion.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Central container with find bar and tab widget
        central_container = QWidget(self)
        central_layout = QVBoxLayout(central_container)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        # Find/Replace bar (hidden by default)
        self.find_bar = FindReplaceBar(self)
        self.find_bar.hide()
        self.find_bar.closed.connect(self._on_find_bar_closed)
        central_layout.addWidget(self.find_bar)

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
        central_layout.addWidget(self.tab_widget)

        self.setCentralWidget(central_container)

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

    def _setup_side_panel(self):
        """Create the side panel with activity bar and content panels."""
        from PyQt6.QtWidgets import QHBoxLayout

        # Activity bar (always visible on left edge)
        self.activity_bar = ActivityBar(self)

        # Content panels
        self.side_panel = SidePanel(self)
        self.file_browser = FileBrowserPanel(self)

        # Stack for content (switches between AI and Files)
        self.panel_content = QStackedWidget()
        self.panel_content.addWidget(self.side_panel)  # Index 0: AI panel
        self.panel_content.addWidget(self.file_browser)  # Index 1: File browser

        # Container with horizontal layout: [ActivityBar | ContentStack]
        panel_container = QWidget()
        container_layout = QHBoxLayout(panel_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.addWidget(self.activity_bar)
        container_layout.addWidget(self.panel_content)

        # Dock widget
        self.side_dock = QDockWidget(self)
        self.side_dock.setWidget(panel_container)
        self.side_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.side_dock.setTitleBarWidget(QWidget())  # Hide title bar
        self.side_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)

        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.side_dock)

        # Connect activity bar signals
        self.activity_bar.panel_selected.connect(self._on_panel_selected)

        # Connect AI panel signals
        self.side_panel.settings_requested.connect(self._show_settings)
        self.side_panel.collapse_requested.connect(self._collapse_side_panel)
        self.side_panel.transfer_to_editor_requested.connect(self._insert_code_to_editor)
        self.side_panel.new_tab_with_code_requested.connect(self._new_tab_with_code)
        self.side_panel.context_requested.connect(self._on_context_requested)
        self.side_panel.replace_selection_requested.connect(self._replace_selection)

        # Connect file browser signals
        self.file_browser.file_selected.connect(self._open_file_path)

        # Track current active panel
        self._active_panel = "ai"

        # Restore state from settings
        visible = self.settings_manager.get_side_panel_visible()
        if visible:
            self._expand_side_panel()
        else:
            self._collapse_side_panel()

    def _on_context_requested(self, prompt: str):
        """Handle AI prompt that needs editor context.

        Gets selected text (or full file if no selection) from the current
        editor and passes it to the side panel for AI generation.
        """
        context = None
        is_selection = False
        editor = self.current_editor()

        if editor:
            # Try to get selected text first
            cursor = editor.textCursor()
            selected_text = cursor.selectedText()

            if selected_text:
                # QTextCursor uses Unicode paragraph separator, replace with newline
                context = selected_text.replace("\u2029", "\n")
                is_selection = True
            else:
                # No selection - use full file content
                context = editor.toPlainText()

        self.side_panel.execute_prompt_with_context(prompt, context, is_selection)

    def _replace_selection(self, new_code: str):
        """Replace the current selection in the editor with new code.

        Called when user clicks "Replace" on an AI-generated code block.
        """
        editor = self.current_editor()
        if editor:
            cursor = editor.textCursor()
            if cursor.hasSelection():
                # Replace the selected text with new code
                cursor.insertText(new_code)
                editor.setTextCursor(cursor)

    def _insert_code_to_editor(self, code: str):
        """Insert code at cursor position in current editor."""
        editor = self.current_editor()
        if editor:
            cursor = editor.textCursor()
            cursor.insertText(code)
            editor.setTextCursor(cursor)

    def _new_tab_with_code(self, code: str, language: str):
        """Create a new tab with the given code content."""
        editor = self.new_tab()
        editor.setPlainText(code)

        # Try to set language based on the code block language
        language_map = {
            "python": Language.PYTHON,
            "py": Language.PYTHON,
            "javascript": Language.JAVASCRIPT,
            "js": Language.JAVASCRIPT,
            "html": Language.HTML,
            "css": Language.CSS,
            "json": Language.JSON,
            "markdown": Language.MARKDOWN,
            "md": Language.MARKDOWN,
        }
        if language.lower() in language_map:
            lang = language_map[language.lower()]
            editor.set_language(lang)
            self._update_language_indicator(lang)

        # Update tab title
        self.tab_widget.setTabText(self.tab_widget.currentIndex(), f"AI: {language or 'code'}")

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
        exit_action.setShortcut(QKeySequence("Alt+F4"))
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

        edit_menu.addSeparator()

        find_action = QAction(self.tr("Find..."), self)
        find_action.setShortcut(QKeySequence.StandardKey.Find)
        find_action.triggered.connect(self._show_find_bar)
        edit_menu.addAction(find_action)

        replace_action = QAction(self.tr("Replace..."), self)
        replace_action.setShortcut(QKeySequence.StandardKey.Replace)
        replace_action.triggered.connect(self._show_find_bar)
        edit_menu.addAction(replace_action)

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

        # Side panel toggle
        self.toggle_panel_action = QAction(self.tr("Side Panel"), self)
        self.toggle_panel_action.setCheckable(True)
        self.toggle_panel_action.setChecked(self.panel_content.isVisible())
        self.toggle_panel_action.setShortcut(QKeySequence("Ctrl+Shift+A"))
        self.toggle_panel_action.toggled.connect(self._toggle_side_panel)
        view_menu.addAction(self.toggle_panel_action)

        view_menu.addSeparator()

        # Settings
        settings_action = QAction(self.tr("Settings..."), self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._show_settings)
        view_menu.addAction(settings_action)

    def _on_panel_selected(self, panel_id: str):
        """Switch to selected panel in activity bar."""
        # If clicking the already-active panel, toggle collapse
        if panel_id == self._active_panel and self.panel_content.isVisible():
            self._collapse_side_panel()
            return

        # Switch to the selected panel
        self._active_panel = panel_id
        if panel_id == "ai":
            self.panel_content.setCurrentIndex(0)
        elif panel_id == "files":
            self.panel_content.setCurrentIndex(1)

        self._expand_side_panel()
        self.activity_bar.set_active(panel_id)

    def _collapse_side_panel(self):
        """Collapse to activity bar only."""
        self.panel_content.hide()
        self.side_dock.setFixedWidth(36)
        self.activity_bar.set_collapsed(True)
        self.settings_manager.set_side_panel_visible(False)
        if hasattr(self, "toggle_panel_action"):
            self.toggle_panel_action.setChecked(False)

    def _expand_side_panel(self):
        """Expand to show content panel."""
        self.panel_content.show()
        self.side_dock.setMinimumWidth(320)
        self.side_dock.setMaximumWidth(500)
        self.activity_bar.set_collapsed(False)
        self.settings_manager.set_side_panel_visible(True)
        self.activity_bar.set_active(self._active_panel)
        if hasattr(self, "toggle_panel_action"):
            self.toggle_panel_action.setChecked(True)

    def _toggle_side_panel(self, visible: bool):
        """Toggle side panel between expanded and collapsed."""
        if visible:
            self._expand_side_panel()
        else:
            self._collapse_side_panel()

    def _setup_toolbar(self):
        """Create the formatting toolbar inline with menu bar."""
        self.formatting_toolbar = FormattingToolbar(self)

        # Add as widget action to menu bar (appears after menus)
        toolbar_action = QWidgetAction(self)
        toolbar_action.setDefaultWidget(self.formatting_toolbar)
        self.menuBar().addAction(toolbar_action)

        # Connect signals
        self.formatting_toolbar.heading_selected.connect(self._insert_heading)
        self.formatting_toolbar.list_selected.connect(self._insert_list)
        self.formatting_toolbar.bold_clicked.connect(self._toggle_bold)
        self.formatting_toolbar.italic_clicked.connect(self._toggle_italic)
        self.formatting_toolbar.link_clicked.connect(self._insert_link)
        self.formatting_toolbar.table_clicked.connect(self._insert_table)

        # Apply theme
        self.formatting_toolbar.apply_theme(self.settings_manager.get_current_theme())

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
        # Check for unsaved changes in all tabs
        unsaved_tabs = []
        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            if self._has_unsaved_changes(editor):
                tab_name = self.tab_widget.tabText(i).rstrip("*")
                unsaved_tabs.append((i, tab_name, editor))

        if unsaved_tabs:
            # Build list of unsaved file names
            names = "\n".join(f"  • {name}" for _, name, _ in unsaved_tabs)
            result = QMessageBox.warning(
                self,
                self.tr("Unsaved Changes"),
                self.tr(f"You have unsaved changes in:\n\n{names}\n\nSave before closing?"),
                QMessageBox.StandardButton.SaveAll
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.SaveAll,
            )

            if result == QMessageBox.StandardButton.SaveAll:
                # Save all unsaved tabs
                for i, _, editor in unsaved_tabs:
                    if editor.filepath:
                        editor.save_file()
                    else:
                        self.tab_widget.setCurrentIndex(i)
                        self.save_file_as()
                        if editor.document().isModified():
                            event.ignore()  # Save was cancelled
                            return
            elif result == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            # Discard: just continue closing

        self.settings.setValue("geometry", self.saveGeometry())
        event.accept()

    def _on_tab_changed(self, index: int):
        """Handle tab change to update status bar with fade transition."""
        editor = self.current_editor()
        if editor:
            self._update_language_indicator(editor.language)
            self._connect_editor_signals(editor)
            # Update find bar's editor reference
            self.find_bar.set_editor(editor)
            # Apply fade-in transition
            self._animate_tab_transition(editor)

    def _animate_tab_transition(self, editor: EditorTab):
        """Apply a subtle fade-in animation when switching tabs."""
        # Create opacity effect if not exists
        effect = editor.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(editor)
            editor.setGraphicsEffect(effect)

        # Create and start fade-in animation
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(150)  # 150ms for subtle transition
        animation.setStartValue(0.7)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.start()

        # Store reference to prevent garbage collection
        self._tab_animation = animation

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
        # Track document modifications for unsaved indicator
        editor.document().modificationChanged.connect(
            lambda modified: self._on_document_modified(editor, modified)
        )
        return editor

    def _on_document_modified(self, editor: EditorTab, modified: bool):
        """Update tab title to show unsaved indicator."""
        index = self.tab_widget.indexOf(editor)
        if index == -1:
            return

        current_title = self.tab_widget.tabText(index)
        if modified and not current_title.endswith("*"):
            self.tab_widget.setTabText(index, current_title + "*")
        elif not modified and current_title.endswith("*"):
            self.tab_widget.setTabText(index, current_title[:-1])

    def _has_unsaved_changes(self, editor: EditorTab) -> bool:
        """Check if an editor has unsaved changes."""
        return editor.document().isModified()

    def _prompt_save_changes(self, editor: EditorTab, tab_name: str) -> bool:
        """Prompt user to save changes. Returns True if okay to close."""
        result = QMessageBox.warning(
            self,
            self.tr("Unsaved Changes"),
            self.tr(f"'{tab_name}' has unsaved changes.\n\nDo you want to save before closing?"),
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )

        if result == QMessageBox.StandardButton.Save:
            # Save the file
            if editor.filepath:
                editor.save_file()
            else:
                # No filepath, need Save As
                index = self.tab_widget.indexOf(editor)
                self.tab_widget.setCurrentIndex(index)
                self.save_file_as()
            return not editor.document().isModified()  # Check if save succeeded

        # Discard returns True (ok to close), Cancel returns False
        return result == QMessageBox.StandardButton.Discard

    def close_tab(self, index: int):
        """Close the tab at the given index."""
        editor = self.tab_widget.widget(index)

        # Check for unsaved changes
        if self._has_unsaved_changes(editor):
            tab_name = self.tab_widget.tabText(index).rstrip("*")
            if not self._prompt_save_changes(editor, tab_name):
                return  # User cancelled

        self.tab_widget.removeTab(index)
        editor.deleteLater()

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

    def _show_find_bar(self):
        """Show the find/replace bar."""
        editor = self.current_editor()
        if editor:
            self.find_bar.set_editor(editor)
            self.find_bar.show_bar()

    def _on_find_bar_closed(self):
        """Handle find bar closed."""
        # Return focus to editor
        if editor := self.current_editor():
            editor.setFocus()

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
        theme = self.settings_manager.get_current_theme()

        # Re-apply window theme (menu bar, toolbar, tabs, status bar)
        self._apply_theme()
        self._update_new_tab_button_style()

        # Apply to side panel, file browser, and formatting toolbar
        self.side_panel.apply_theme()
        self.file_browser.apply_theme()
        self.formatting_toolbar.apply_theme(theme)

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

    def _insert_heading(self, level: int):
        """Insert markdown heading at cursor."""
        editor = self.current_editor()
        if not editor:
            return

        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.StartOfBlock)
        cursor.insertText("#" * level + " ")
        editor.setTextCursor(cursor)

    def _insert_list(self, list_type: str):
        """Insert list marker at cursor."""
        editor = self.current_editor()
        if not editor:
            return

        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.StartOfBlock)
        marker = "- " if list_type == "bullet" else "1. "
        cursor.insertText(marker)
        editor.setTextCursor(cursor)

    def _insert_link(self):
        """Insert markdown link syntax."""
        editor = self.current_editor()
        if not editor:
            return

        cursor = editor.textCursor()
        selected = cursor.selectedText()
        if selected:
            cursor.insertText(f"[{selected}](url)")
        else:
            pos = cursor.position()
            cursor.insertText("[text](url)")
            cursor.setPosition(pos + 1)
            cursor.setPosition(pos + 5, cursor.MoveMode.KeepAnchor)
            editor.setTextCursor(cursor)

    def _insert_table(self):
        """Insert markdown table template."""
        editor = self.current_editor()
        if not editor:
            return

        table = "| Header 1 | Header 2 |\n|----------|----------|\n| Cell 1   | Cell 2   |\n"
        editor.textCursor().insertText(table)
