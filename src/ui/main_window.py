"""
Main application window with tabs, menus, and toolbar.
"""

import time
from pathlib import Path

from PyQt6.QtCore import (
    QEasingCurve,
    QEvent,
    QPropertyAnimation,
    QSettings,
    Qt,
    QTimer,
)
from PyQt6.QtGui import (
    QAction,
    QActionGroup,
    QKeySequence,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.recent_files import RecentFilesManager
from core.settings import SettingsManager
from syntax.highlighter import Language
from ui.activity_bar import ActivityBar
from ui.completion_controller import CompletionController
from ui.custom_tab_bar import CustomTabBar
from ui.editor_tab import EditorTab
from ui.file_browser import FileBrowserPanel
from ui.find_replace import FindReplaceBar
from ui.inline_edit_controller import InlineEditController
from ui.settings_dialog import SettingsDialog
from ui.side_panel import LayoutMode, SidePanel
from ui.status_bar_manager import StatusBarManager
from ui.theme_engine import ThemeEngine, hex_to_rgba
from ui.title_bar import TitleBarController
from ui.toolbar_widgets import FormattingToolbar


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("MyNotion", "Editor")
        self.settings_manager = SettingsManager()
        self.recent_files = RecentFilesManager(self)
        self._title_bar_ctrl = TitleBarController(self)

        self._setup_ui()
        self._setup_side_panel()
        self._status_bar_mgr = StatusBarManager(self, self.current_editor)
        self._setup_menus()
        self._status_bar_mgr.set_language_actions(self.language_actions)
        self._status_bar_mgr.setup()
        self._setup_toolbar()
        self._title_bar_ctrl.setup_resize_grips()
        self._completion_ctrl = CompletionController(
            self, self.current_editor, self.settings_manager, self.completion_btn
        )
        self._completion_ctrl.setup(self)
        self._inline_edit_ctrl = InlineEditController(
            self,
            self.current_editor,
            lambda: self.side_panel.current_model["id"],
            self.side_panel.get_layout_mode,
        )
        self._inline_edit_ctrl.setup(self)
        self._theme_engine = ThemeEngine(self, self.settings_manager)
        self._theme_engine.apply_theme()
        self._theme_engine.apply_child_themes()
        self._restore_geometry()

        # Track manual layout mode switches (30s cooldown for auto-switch)
        self._last_manual_mode_switch: float = 0.0

        # Connect recent files changes
        self.recent_files.files_changed.connect(self._update_recent_menu)

        # Restore previous session or create a blank tab
        if not self._restore_session():
            self.new_tab()

        # Auto-save timer
        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.timeout.connect(self._auto_save)
        self._start_auto_save_timer()

    def _update_window_title(self):
        """Update window title to show current filename."""
        editor = self.current_editor()
        if editor and editor.filepath:
            filename = Path(editor.filepath).name
            title = f"MyNotion - {filename}"
        else:
            title = "MyNotion"
        self.setWindowTitle(title)  # Taskbar / Alt+Tab
        self._title_bar_ctrl.update_title(title)

    def _setup_ui(self):
        """Initialize the main UI components."""
        self.setWindowTitle("MyNotion")
        self.setMinimumSize(300, 200)  # Allow small window like Notepad

        # Frameless window + native snapping + taskbar icon
        self._title_bar_ctrl.setup_frameless()

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

        # Create + button on the tab widget, positioned over the tab bar area
        self.new_tab_btn = QToolButton(self.tab_widget)
        self.new_tab_btn.setText("+")
        self.new_tab_btn.setFixedWidth(28)
        self.new_tab_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_tab_btn.clicked.connect(self.new_tab)

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
        """Position the + button right after the last tab, flush with tab bar."""
        bar_height = self.custom_tab_bar.height()
        self.new_tab_btn.setFixedHeight(bar_height)
        if self.custom_tab_bar.count() > 0:
            last_rect = self.custom_tab_bar.tabRect(self.custom_tab_bar.count() - 1)
            x = last_rect.right() + 4
            self.new_tab_btn.move(x, 0)
        else:
            self.new_tab_btn.move(8, 0)
        self.new_tab_btn.raise_()
        self.new_tab_btn.show()

    def resizeEvent(self, event):
        """Handle resize to update + button position and resize grips."""
        super().resizeEvent(event)
        if hasattr(self, "new_tab_btn"):
            QTimer.singleShot(10, self._update_new_tab_button_position)
        self._title_bar_ctrl.position_resize_grips()

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
        self.side_panel.chat_context_requested.connect(self._on_chat_context_requested)
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

    def _on_chat_context_requested(self, message: str):
        """Handle chat message that needs editor context.

        Gets full file content from the current editor and passes it
        to the side panel along with the user's message.
        """
        context = None
        editor = self.current_editor()

        if editor:
            # For chat, always use full file content as context
            context = editor.toPlainText()

        self.side_panel.execute_chat_with_context(message, context)

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
            self._status_bar_mgr.update_language(lang)

        # Update tab title
        self.tab_widget.setTabText(self.tab_widget.currentIndex(), f"AI: {language or 'code'}")

    def _on_new_tab_requested(self):
        """Handle new tab request from tab bar double-click."""
        self.new_tab()

    def _setup_menus(self):
        """Create the menu bar and menus."""
        from PyQt6.QtWidgets import QMenuBar

        menubar = QMenuBar(self)
        self._menu_bar = menubar

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

        open_folder_action = QAction(self.tr("Open Folder"), self)
        open_folder_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        open_folder_action.triggered.connect(self.open_folder)
        file_menu.addAction(open_folder_action)

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
            action.triggered.connect(self._status_bar_mgr.on_language_selected)
            self.language_actions.addAction(action)
            self.language_menu.addAction(action)

        view_menu.addSeparator()

        # Layout Mode submenu
        self.layout_mode_menu = view_menu.addMenu(self.tr("Layout Mode"))
        self.layout_mode_actions = QActionGroup(self)
        self.layout_mode_actions.setExclusive(True)

        # Coding Mode action
        self.coding_mode_action = QAction(self.tr("Coding Mode"), self)
        self.coding_mode_action.setCheckable(True)
        self.coding_mode_action.setData(LayoutMode.CODING)
        self.coding_mode_action.triggered.connect(self._on_layout_mode_selected)
        self.layout_mode_actions.addAction(self.coding_mode_action)
        self.layout_mode_menu.addAction(self.coding_mode_action)

        # Writing Mode action
        self.writing_mode_action = QAction(self.tr("Writing Mode"), self)
        self.writing_mode_action.setCheckable(True)
        self.writing_mode_action.setData(LayoutMode.WRITING)
        self.writing_mode_action.triggered.connect(self._on_layout_mode_selected)
        self.layout_mode_actions.addAction(self.writing_mode_action)
        self.layout_mode_menu.addAction(self.writing_mode_action)

        # Toggle shortcut (Ctrl+Shift+M to toggle between modes)
        self.toggle_layout_mode_action = QAction(self.tr("Toggle Layout Mode"), self)
        self.toggle_layout_mode_action.setShortcut(QKeySequence("Ctrl+Shift+M"))
        self.toggle_layout_mode_action.triggered.connect(self._toggle_layout_mode)
        self.addAction(self.toggle_layout_mode_action)  # Add to window for shortcut to work

        # Load saved mode and apply
        self._load_layout_mode()

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

        # Help menu
        help_menu = menubar.addMenu(self.tr("&Help"))

        shortcuts_action = QAction(self.tr("Keyboard Shortcuts"), self)
        shortcuts_action.setShortcut(QKeySequence("F1"))
        shortcuts_action.triggered.connect(self._show_keyboard_shortcuts)
        help_menu.addAction(shortcuts_action)

        help_menu.addSeparator()

        about_action = QAction(self.tr("About MyNotion"), self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

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
        """Create custom title bar and formatting toolbar."""
        from PyQt6.QtWidgets import QHBoxLayout

        self.formatting_toolbar = FormattingToolbar(self)

        # Header: [Title bar row] + [Menu/toolbar row]
        self._header_widget = QWidget(self)
        header_vlayout = QVBoxLayout(self._header_widget)
        header_vlayout.setContentsMargins(0, 0, 0, 0)
        header_vlayout.setSpacing(0)

        # Custom title bar (created by controller)
        self._title_bar_ctrl.create_title_bar(header_vlayout)

        # ── Menu/toolbar row ──
        toolbar_row = QWidget()
        toolbar_layout = QHBoxLayout(toolbar_row)
        toolbar_layout.setContentsMargins(0, 0, 8, 0)
        toolbar_layout.setSpacing(0)

        toolbar_layout.addWidget(self._menu_bar)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self.formatting_toolbar)

        # AI completion toggle button (behavior wired by CompletionController)
        self.completion_btn = QToolButton()
        self.completion_btn.setText("\u25c9 AI")
        self.completion_btn.setToolTip(self.tr("AI Code Completion (Ctrl+Shift+Space)"))
        self.completion_btn.setFixedHeight(22)
        self.completion_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        toolbar_layout.addWidget(self.completion_btn)

        header_vlayout.addWidget(toolbar_row)

        self.setMenuWidget(self._header_widget)

        # Connect signals
        self.formatting_toolbar.heading_selected.connect(self._insert_heading)
        self.formatting_toolbar.bold_clicked.connect(self._toggle_bold)
        self.formatting_toolbar.italic_clicked.connect(self._toggle_italic)
        self.formatting_toolbar.clear_format_clicked.connect(self._clear_formatting)

        # Apply theme
        self.formatting_toolbar.apply_theme(self.settings_manager.get_current_theme())

    def keyPressEvent(self, event):
        """Handle Win+Arrow window snapping, then default behavior."""
        if self._title_bar_ctrl.handle_key_press(event):
            return
        super().keyPressEvent(event)

    def eventFilter(self, obj: object, event: QEvent) -> bool:
        """Delegate title bar drag and resize grip events to controller."""
        if self._title_bar_ctrl.handle_event_filter(obj, event):
            return True
        return super().eventFilter(obj, event)

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

    def _save_session(self):
        """Save current tab state for session restore."""
        session_tabs = []
        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            if not isinstance(editor, EditorTab):
                continue
            if not editor.filepath:
                continue
            cursor = editor.textCursor()
            session_tabs.append(
                {
                    "filepath": editor.filepath,
                    "cursor_line": cursor.blockNumber(),
                    "cursor_col": cursor.columnNumber(),
                    "scroll_pos": editor.verticalScrollBar().value(),
                }
            )

        self.settings_manager.set_session_tabs(session_tabs)
        self.settings_manager.set_session_active_tab(self.tab_widget.currentIndex())

    def _restore_session(self) -> bool:
        """Restore tabs from previous session.

        Returns True if any tabs were restored.
        """
        session_tabs = self.settings_manager.get_session_tabs()
        if not session_tabs:
            return False

        restored_any = False
        for tab_data in session_tabs:
            filepath = tab_data.get("filepath", "")
            if not filepath or not Path(filepath).exists():
                continue

            self._open_file_path(filepath)
            editor = self.current_editor()
            if not editor:
                continue

            # Restore cursor position
            cursor_line = tab_data.get("cursor_line", 0)
            cursor_col = tab_data.get("cursor_col", 0)
            cursor = editor.textCursor()
            block = editor.document().findBlockByNumber(cursor_line)
            if block.isValid():
                pos = block.position() + min(cursor_col, max(0, block.length() - 1))
                cursor.setPosition(pos)
                editor.setTextCursor(cursor)

            # Defer scroll restore so layout computes first
            scroll_pos = tab_data.get("scroll_pos", 0)
            QTimer.singleShot(
                0,
                lambda sp=scroll_pos, e=editor: e.verticalScrollBar().setValue(sp),
            )

            restored_any = True

        # Restore active tab index
        if restored_any:
            active_index = self.settings_manager.get_session_active_tab()
            if 0 <= active_index < self.tab_widget.count():
                self.tab_widget.setCurrentIndex(active_index)

        return restored_any

    def _start_auto_save_timer(self):
        """Start or restart the auto-save timer based on settings."""
        if self.settings_manager.get_auto_save_enabled():
            interval_ms = self.settings_manager.get_auto_save_interval() * 1000
            self._auto_save_timer.start(interval_ms)
        else:
            self._auto_save_timer.stop()

    def _auto_save(self):
        """Auto-save all modified tabs that have a file path."""
        saved_count = 0
        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            if isinstance(editor, EditorTab) and editor.filepath and editor.document().isModified():
                error = editor.save_file()
                if not error:
                    saved_count += 1

        if saved_count > 0:
            msg = f"Auto-saved {saved_count} file{'s' if saved_count > 1 else ''}"
            self._status_bar_mgr.show_message(msg, 3000)

    def changeEvent(self, event):
        """Handle window state changes (focus loss triggers auto-save)."""
        super().changeEvent(event)
        if (
            event.type() == event.Type.WindowDeactivate
            and self.settings_manager.get_auto_save_enabled()
        ):
            self._auto_save()

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
                        error = editor.save_file()
                        if error:
                            QMessageBox.warning(self, self.tr("Save File"), error)
                            event.ignore()
                            return
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

        # Stop all running AI threads before closing
        if hasattr(self, "_inline_edit_ctrl"):
            self._inline_edit_ctrl.stop_manager()
        if hasattr(self, "side_panel") and hasattr(self.side_panel, "ai_manager"):
            self.side_panel.ai_manager.stop()

        self._save_session()
        self.settings.setValue("geometry", self.saveGeometry())
        event.accept()

    def _on_tab_changed(self, index: int):
        """Handle tab change to update status bar with fade transition."""
        # Disconnect previous editor's inline edit signals
        if hasattr(self, "_inline_edit_ctrl"):
            self._inline_edit_ctrl.disconnect_previous()

        # Cancel any pending completion from previous tab
        if hasattr(self, "_completion_ctrl"):
            self._completion_ctrl.cancel()

        # Cancel any in-progress inline edit
        if hasattr(self, "_inline_edit_ctrl"):
            self._inline_edit_ctrl.cancel_active()

        editor = self.current_editor()
        if editor:
            self._status_bar_mgr.update_language(editor.language)
            self._status_bar_mgr.connect_editor(editor)
            # Wire completion to new tab
            if hasattr(self, "_completion_ctrl"):
                self._completion_ctrl.connect_editor(editor)
            # Wire inline edit to new tab
            if hasattr(self, "_inline_edit_ctrl"):
                self._inline_edit_ctrl.connect_editor(editor)
            # Update find bar's editor reference
            self.find_bar.set_editor(editor)
            # Update window title with current filename
            self._update_window_title()
            # Auto-switch layout mode based on language (with 30s cooldown)
            self._auto_switch_layout_mode(editor)
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

    # Status bar update methods moved to StatusBarManager

    def _load_layout_mode(self):
        """Load saved layout mode and apply to side panel."""
        saved_mode = self.settings_manager.get_layout_mode()
        mode = LayoutMode.WRITING if saved_mode == "writing" else LayoutMode.CODING

        # Update menu checkmarks
        if mode == LayoutMode.CODING:
            self.coding_mode_action.setChecked(True)
        else:
            self.writing_mode_action.setChecked(True)

        # Apply to side panel
        self.side_panel.set_layout_mode(mode)

    def _on_layout_mode_selected(self):
        """Handle layout mode selection from menu."""
        action = self.layout_mode_actions.checkedAction()
        if action:
            mode = action.data()
            self._apply_layout_mode(mode)

    def _toggle_layout_mode(self):
        """Toggle between Coding and Writing modes."""
        current_mode = self.side_panel.get_layout_mode()
        new_mode = LayoutMode.WRITING if current_mode == LayoutMode.CODING else LayoutMode.CODING
        self._apply_layout_mode(new_mode)

        # Update menu checkmarks
        if new_mode == LayoutMode.CODING:
            self.coding_mode_action.setChecked(True)
        else:
            self.writing_mode_action.setChecked(True)

    def _apply_layout_mode(self, mode: LayoutMode, manual: bool = True):
        """Apply layout mode to settings and side panel.

        Args:
            mode: The layout mode to apply.
            manual: If True, records a cooldown to prevent auto-switching.
        """
        if manual:
            self._last_manual_mode_switch = time.monotonic()
        self.settings_manager.set_layout_mode(mode.value)
        self.side_panel.set_layout_mode(mode)

    def _auto_switch_layout_mode(self, editor: EditorTab) -> None:
        """Auto-switch layout mode based on the editor's language.

        Skips if the user manually toggled mode in the last 30 seconds.
        """
        # Don't auto-switch if user recently manually changed mode
        if time.monotonic() - self._last_manual_mode_switch < 30:
            return

        target_mode = self._get_layout_mode_for_language(editor.language)
        current_mode = self.side_panel.get_layout_mode()

        if target_mode != current_mode:
            self._apply_layout_mode(target_mode, manual=False)
            # Update menu checkmarks
            if target_mode == LayoutMode.CODING:
                self.coding_mode_action.setChecked(True)
            else:
                self.writing_mode_action.setChecked(True)

    @staticmethod
    def _get_layout_mode_for_language(language: Language) -> LayoutMode:
        """Return the appropriate layout mode for a file language."""
        code_languages = {
            Language.PYTHON,
            Language.JAVASCRIPT,
            Language.HTML,
            Language.CSS,
            Language.JSON,
        }
        if language in code_languages:
            return LayoutMode.CODING
        return LayoutMode.WRITING

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
        error = editor.load_file(filepath)
        if error:
            # Close the tab we just created and show error
            idx = self.tab_widget.currentIndex()
            self.tab_widget.removeTab(idx)
            editor.deleteLater()
            QMessageBox.warning(self, self.tr("Open File"), error)
            return
        self.tab_widget.setTabText(self.tab_widget.currentIndex(), Path(filepath).name)
        self._status_bar_mgr.update_language(editor.language)
        self._update_window_title()
        self.recent_files.add_file(filepath)

    # Tab management
    def new_tab(self):
        """Create a new editor tab."""
        editor = EditorTab(parent=self.tab_widget)
        index = self.tab_widget.addTab(editor, self.tr("Untitled"))
        self.tab_widget.setCurrentIndex(index)
        self._status_bar_mgr.connect_editor(editor)
        # Wire completion for new tab
        if hasattr(self, "_completion_ctrl"):
            self._completion_ctrl.connect_editor(editor)
        # Wire inline edit for new tab
        if hasattr(self, "_inline_edit_ctrl"):
            self._inline_edit_ctrl.connect_editor(editor)
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
                error = editor.save_file()
                if error:
                    QMessageBox.warning(self, self.tr("Save File"), error)
                    return False
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

    def open_folder(self):
        """Open a folder dialog to select project folder for file browser."""
        self.file_browser.open_folder_dialog()

    def save_file(self):
        """Save the current file."""
        editor = self.current_editor()
        if editor and editor.filepath:
            error = editor.save_file()
            if error:
                QMessageBox.warning(self, self.tr("Save File"), error)
                return
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
            error = editor.save_file(filepath)
            if error:
                QMessageBox.warning(self, self.tr("Save File"), error)
                return
            self.tab_widget.setTabText(self.tab_widget.currentIndex(), Path(filepath).name)
            self._status_bar_mgr.update_language(editor.language)
            self._update_window_title()
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
            self._status_bar_mgr.update()

    def _zoom_out(self):
        if editor := self.current_editor():
            editor.zoom_out()
            self._status_bar_mgr.update()

    def _show_settings(self):
        """Show the settings dialog."""
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self._apply_settings_to_editors)
        dialog.exec()

    def _show_about(self):
        """Show the About MyNotion dialog with the decorative logo."""
        about_box = QMessageBox(self)
        about_box.setWindowTitle(self.tr("About MyNotion"))
        about_box.setText(
            self.tr(
                "<h3>MyNotion</h3>"
                "<p>A lightweight text and code editor with local AI integration.</p>"
                "<p>Built with Python + PyQt6.</p>"
            )
        )

        # Load the decorative SVG logo
        from PyQt6.QtGui import QImage, QPainter
        from PyQt6.QtSvg import QSvgRenderer

        svg_path = TitleBarController._get_resource_path("mynotion_about.svg")
        if svg_path.exists():
            renderer = QSvgRenderer(str(svg_path))
            image = QImage(64, 64, QImage.Format.Format_ARGB32)
            image.fill(0)
            painter = QPainter(image)
            renderer.render(painter)
            painter.end()
            about_box.setIconPixmap(QPixmap.fromImage(image))

        about_box.exec()

    def _show_keyboard_shortcuts(self):
        """Show a themed dialog listing all keyboard shortcuts."""
        from PyQt6.QtWidgets import QDialog, QTextBrowser, QVBoxLayout

        theme = self.settings_manager.get_current_theme()

        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("Keyboard Shortcuts"))
        dialog.setMinimumSize(420, 500)

        dlg_layout = QVBoxLayout(dialog)
        dlg_layout.setContentsMargins(0, 0, 0, 0)

        browser = QTextBrowser()
        browser.setFrameShape(QFrame.Shape.NoFrame)
        browser.setOpenExternalLinks(False)

        accent = theme.keyword
        fg = theme.foreground
        bg = theme.background
        dim = hex_to_rgba(fg, 0.55)
        kbd_bg = hex_to_rgba(fg, 0.08)
        kbd_border = hex_to_rgba(fg, 0.15)

        shortcuts_html = f"""
        <style>
            body {{ background: {bg}; color: {fg}; font-family: Consolas, monospace; font-size: 9px; padding: 12px; }}
            h2 {{ color: {accent}; font-size: 10px; margin: 14px 0 6px 0; border-bottom: 1px solid {kbd_border}; padding-bottom: 3px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            td {{ padding: 3px 6px; vertical-align: top; font-size: 9px; }}
            td:first-child {{ color: {dim}; width: 55%; }}
            .kbd {{ background: {kbd_bg}; border: 1px solid {kbd_border}; border-radius: 3px; padding: 1px 5px; font-size: 8px; }}
        </style>
        <h2>File</h2>
        <table>
        <tr><td>New tab</td><td><span class="kbd">Ctrl+N</span></td></tr>
        <tr><td>Open file</td><td><span class="kbd">Ctrl+O</span></td></tr>
        <tr><td>Open folder</td><td><span class="kbd">Ctrl+Shift+O</span></td></tr>
        <tr><td>Save</td><td><span class="kbd">Ctrl+S</span></td></tr>
        <tr><td>Save as</td><td><span class="kbd">Ctrl+Shift+S</span></td></tr>
        </table>

        <h2>Edit</h2>
        <table>
        <tr><td>Undo</td><td><span class="kbd">Ctrl+Z</span></td></tr>
        <tr><td>Redo</td><td><span class="kbd">Ctrl+Y</span></td></tr>
        <tr><td>Cut / Copy / Paste</td><td><span class="kbd">Ctrl+X/C/V</span></td></tr>
        <tr><td>Find</td><td><span class="kbd">Ctrl+F</span></td></tr>
        <tr><td>Replace</td><td><span class="kbd">Ctrl+H</span></td></tr>
        </table>

        <h2>AI</h2>
        <table>
        <tr><td>Inline AI edit</td><td><span class="kbd">Ctrl+K</span></td></tr>
        <tr><td>Toggle AI completion</td><td><span class="kbd">Ctrl+Shift+Space</span></td></tr>
        <tr><td>Toggle side panel</td><td><span class="kbd">Ctrl+Shift+A</span></td></tr>
        </table>

        <h2>View</h2>
        <table>
        <tr><td>Zoom in</td><td><span class="kbd">Ctrl++</span></td></tr>
        <tr><td>Zoom out</td><td><span class="kbd">Ctrl+-</span></td></tr>
        <tr><td>Toggle layout mode</td><td><span class="kbd">Ctrl+Shift+M</span></td></tr>
        <tr><td>Settings</td><td><span class="kbd">Ctrl+,</span></td></tr>
        <tr><td>Keyboard shortcuts</td><td><span class="kbd">F1</span></td></tr>
        </table>

        <h2>Completion</h2>
        <table>
        <tr><td>Accept suggestion</td><td><span class="kbd">Tab</span></td></tr>
        <tr><td>Accept first line</td><td><span class="kbd">Ctrl+Right</span></td></tr>
        <tr><td>Dismiss suggestion</td><td><span class="kbd">Esc</span></td></tr>
        </table>
        """

        browser.setHtml(shortcuts_html)

        browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {bg};
                color: {fg};
                border: none;
            }}
        """)

        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
            }}
        """)

        dlg_layout.addWidget(browser)
        dialog.exec()

    def _apply_settings_to_editors(self):
        """Apply changed settings to all editor tabs and window chrome."""
        self._theme_engine.apply_theme()
        self._theme_engine.apply_child_themes()
        self._status_bar_mgr.update()
        self._start_auto_save_timer()

        # Refresh completion settings
        if hasattr(self, "_completion_ctrl"):
            self._completion_ctrl.refresh_settings()

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
        """Insert list marker at cursor or on each selected line."""
        editor = self.current_editor()
        if not editor:
            return

        cursor = editor.textCursor()
        selected = cursor.selectedText()
        marker = "- " if list_type == "bullet" else "1. "

        if selected and "\u2029" in selected:
            # Multi-line selection: prepend marker to each line
            lines = selected.split("\u2029")
            if list_type == "bullet":
                new_text = "\n".join("- " + line for line in lines)
            else:
                new_text = "\n".join(f"{i}. {line}" for i, line in enumerate(lines, 1))
            cursor.insertText(new_text)
        else:
            # Single line: move to start and insert marker
            cursor.movePosition(cursor.MoveOperation.StartOfBlock)
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

    def _clear_formatting(self):
        """Strip markdown formatting from selected text."""
        import re

        editor = self.current_editor()
        if not editor:
            return

        cursor = editor.textCursor()
        selected = cursor.selectedText()
        if not selected:
            return

        # Strip markdown syntax: bold, italic, headings, links, images
        cleaned = selected
        cleaned = re.sub(r"\*\*(.+?)\*\*", r"\1", cleaned)  # **bold**
        cleaned = re.sub(r"\*(.+?)\*", r"\1", cleaned)  # *italic*
        cleaned = re.sub(r"^#{1,6}\s+", "", cleaned, flags=re.MULTILINE)  # headings
        cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)  # [text](url)
        cleaned = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", cleaned)  # ![alt](img)
        cleaned = re.sub(r"~~(.+?)~~", r"\1", cleaned)  # ~~strikethrough~~
        cleaned = re.sub(r"`(.+?)`", r"\1", cleaned)  # `inline code`

        if cleaned != selected:
            cursor.insertText(cleaned)
