"""
Main application window with tabs, menus, and toolbar.
"""

import contextlib
import ctypes
import sys
from pathlib import Path

from PyQt6.QtCore import (
    QEasingCurve,
    QEvent,
    QPoint,
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
    QPixmap,
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
)

from ai.completion import CompletionManager
from ai.worker import AIManager
from core.recent_files import RecentFilesManager
from core.settings import SettingsManager
from syntax.highlighter import Language
from ui.activity_bar import ActivityBar
from ui.custom_tab_bar import CustomTabBar
from ui.editor_tab import EditorTab
from ui.file_browser import FileBrowserPanel
from ui.find_replace import FindReplaceBar
from ui.settings_dialog import SettingsDialog
from ui.side_panel import LayoutMode, SidePanel
from ui.toolbar_widgets import FormattingToolbar

# Models available for code completion (small, fast FIM models)
COMPLETION_MODELS = [
    {"id": "deepseek-coder:1.3b", "name": "DeepSeek Coder 1.3B"},
    {"id": "qwen2.5-coder:1.5b", "name": "Qwen 2.5 Coder 1.5B"},
    {"id": "codegemma:2b", "name": "CodeGemma 2B"},
]


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("MyNotion", "Editor")
        self.settings_manager = SettingsManager()
        self.recent_files = RecentFilesManager(self)

        self._setup_ui()
        self._setup_side_panel()
        self._setup_menus()
        self._setup_toolbar()
        self._setup_resize_grips()
        self._setup_statusbar()
        self._setup_completion()
        self._setup_inline_edit()
        self._apply_theme()
        self._apply_child_themes()
        self._restore_geometry()

        # Connect recent files changes
        self.recent_files.files_changed.connect(self._update_recent_menu)

        # Restore previous session or create a blank tab
        if not self._restore_session():
            self.new_tab()

        # Auto-save timer
        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.timeout.connect(self._auto_save)
        self._start_auto_save_timer()

    @staticmethod
    def _hex_to_rgba(hex_color: str, alpha: float) -> str:
        """Convert hex color to rgba() CSS string."""
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    def _apply_title_bar_color(self, hex_color: str):
        """Set the Windows title bar color using the DWM API."""
        if sys.platform != "win32":
            return
        try:
            hwnd = int(self.winId())
            h = hex_color.lstrip("#")
            # DWM expects COLORREF: 0x00BBGGRR
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            color = ctypes.c_int(r | (g << 8) | (b << 16))
            # DWMWA_CAPTION_COLOR = 35 (Windows 11 / Windows 10 22H2+)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 35, ctypes.byref(color), ctypes.sizeof(color)
            )
        except Exception:
            pass  # Silently ignore on unsupported Windows versions

    def _apply_title_bar_text_color(self, hex_color: str):
        """Set the Windows title bar text color using the DWM API."""
        if sys.platform != "win32":
            return
        try:
            hwnd = int(self.winId())
            h = hex_color.lstrip("#")
            # DWM expects COLORREF: 0x00BBGGRR
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            color = ctypes.c_int(r | (g << 8) | (b << 16))
            # DWMWA_TEXT_COLOR = 36 (Windows 11+)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 36, ctypes.byref(color), ctypes.sizeof(color)
            )
        except Exception:
            pass  # Silently ignore on unsupported Windows versions

    def _update_window_title(self):
        """Update window title to show current filename."""
        editor = self.current_editor()
        if editor and editor.filepath:
            filename = Path(editor.filepath).name
            title = f"MyNotion - {filename}"
        else:
            title = "MyNotion"
        self.setWindowTitle(title)  # Taskbar / Alt+Tab
        if hasattr(self, "_title_text_label"):
            self._title_text_label.setText(title)

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

        # Win95: explicit per-side beveled borders on buttons/menus
        if theme.is_beveled:
            toolbar_btn_border = theme.bevel_raised
            menu_border = theme.bevel_raised
            msgbox_btn_border = theme.bevel_raised
            msgbox_btn_default_border = theme.bevel_raised
            well_bg = theme._darken(chrome_bg, 6)

            tab_qss = f"""
            QTabBar {{
                background-color: {chrome_bg};
                font-size: 11px;
            }}
            QTabBar::tab {{
                background-color: {chrome_hover};
                color: {self._hex_to_rgba(fg, 0.5)};
                padding: 5px 12px;
                {theme.bevel_raised}
                min-width: 80px;
                margin-right: 0px;
            }}
            QTabBar::tab:selected {{
                background-color: {bg};
                color: {fg};
                border-top: 2px solid {theme.keyword};
                border-left: 2px solid {theme.bevel_light};
                border-right: 2px solid {theme.bevel_dark};
                border-bottom: none;
                margin-bottom: -2px;
                padding: 5px 12px 7px;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {chrome_hover};
                color: {self._hex_to_rgba(fg, 0.7)};
            }}"""

            pane_qss = f"""
            QTabWidget::pane {{
                {theme.bevel_sunken}
                background-color: {bg};
            }}"""

            status_qss = f"""
            QStatusBar {{
                background-color: {chrome_bg};
                color: {self._hex_to_rgba(fg, 0.6)};
                {theme.bevel_raised}
                font-size: 11px;
                padding: 2px 4px;
            }}
            QStatusBar::item {{
                border: none;
            }}
            QStatusBar QLabel {{
                color: {self._hex_to_rgba(fg, 0.6)};
                padding: 3px 10px;
                font-size: 10px;
                background-color: {well_bg};
                {theme.bevel_sunken}
            }}
            QStatusBar QLabel:hover {{
                color: {fg};
            }}"""
        else:
            toolbar_btn_border = "border: none;"
            menu_border = f"border: 1px solid {chrome_border};"
            msgbox_btn_border = f"border: 1px solid {chrome_border};"
            msgbox_btn_default_border = f"border: 1px solid {theme.keyword};"

            tab_qss = f"""
            QTabBar {{
                background-color: {chrome_bg};
                font-size: 11px;
            }}
            QTabBar::tab {{
                background-color: {chrome_bg};
                color: {self._hex_to_rgba(fg, 0.5)};
                padding: 6px 12px 6px 10px;
                border: 1px solid {chrome_border};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                min-width: 80px;
                margin-right: 2px;
                margin-top: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {chrome_border};
                border-bottom: 1px solid {bg};
                border-top: 2px solid {theme.keyword};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {self._hex_to_rgba(fg, 0.05)};
                color: {self._hex_to_rgba(fg, 0.7)};
            }}"""

            pane_qss = f"""
            QTabWidget::pane {{
                border-top: 1px solid {chrome_border};
                background-color: {bg};
            }}"""

            status_qss = f"""
            QStatusBar {{
                background-color: {chrome_bg};
                color: {self._hex_to_rgba(fg, 0.6)};
                border-top: 1px solid {chrome_border};
                font-size: 11px;
                padding: 2px 4px;
            }}
            QStatusBar::item {{
                border: none;
            }}
            QStatusBar QLabel {{
                color: {self._hex_to_rgba(fg, 0.6)};
                background-color: {self._hex_to_rgba(fg, 0.04)};
                border: 1px solid {self._hex_to_rgba(fg, 0.08)};
                border-radius: 6px;
                padding: 2px 10px;
                margin: 1px 2px;
                font-size: 10px;
            }}
            QStatusBar QLabel:hover {{
                color: {fg};
                background-color: {self._hex_to_rgba(fg, 0.1)};
                border: 1px solid {self._hex_to_rgba(fg, 0.15)};
            }}"""

        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {bg};
                font-size: 10px;
                {theme.bevel_raised if theme.is_beveled else f"border: 1px solid {chrome_border}; border-radius: 6px;"}
            }}
            QMenuBar {{
                background-color: {chrome_bg};
                color: {fg};
                border: none;
                padding: 2px;
                font-size: 13px;
            }}
            QMenuBar::item {{
                padding: 4px 8px;
                background-color: transparent;
            }}
            QMenuBar::item:selected {{
                background-color: {self._hex_to_rgba(fg, 0.15)};
            }}
            QMenu {{
                background-color: {chrome_bg};
                color: {fg};
                {menu_border}
                padding: 4px 0px;
                font-size: 13px;
            }}
            QMenu::item {{
                padding: 6px 30px 6px 20px;
            }}
            QMenu::item:selected {{
                background-color: {self._hex_to_rgba(fg, 0.15)};
                color: {fg};
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
                background-color: {chrome_hover if theme.is_beveled else "transparent"};
                color: {fg};
                {toolbar_btn_border}
                border-radius: {theme.radius};
                padding: 4px 10px;
                font-weight: bold;
                font-size: 12px;
            }}
            QToolBar QToolButton:hover {{
                background-color: {chrome_hover};
            }}
            QToolBar QToolButton:pressed {{
                background-color: {chrome_hover if theme.is_beveled else selection};
                {theme.bevel_sunken if theme.is_beveled else ""}
            }}
            {pane_qss}
            {tab_qss}
            {status_qss}
            QMessageBox {{
                background-color: {bg};
                color: {fg};
            }}
            QMessageBox QLabel {{
                color: {fg};
                font-size: 11px;
            }}
            QMessageBox QPushButton {{
                background-color: {chrome_hover if theme.is_beveled else chrome_bg};
                color: {fg};
                {msgbox_btn_border}
                border-radius: {theme.radius};
                padding: 6px 16px;
                min-width: 70px;
                font-size: 11px;
            }}
            QMessageBox QPushButton:hover {{
                background-color: {chrome_hover};
            }}
            QMessageBox QPushButton:pressed {{
                background-color: {chrome_hover if theme.is_beveled else selection};
                {theme.bevel_sunken if theme.is_beveled else ""}
            }}
            QMessageBox QPushButton:default {{
                {msgbox_btn_default_border}
            }}
            QDockWidget {{
                background-color: {bg};
                border: none;
            }}
            QMainWindow::separator {{
                background-color: {theme.bevel_dark if theme.is_beveled else chrome_border};
                width: {"2px" if theme.is_beveled else "1px"};
                height: {"2px" if theme.is_beveled else "1px"};
            }}
        """)

        # Style the custom title bar
        if hasattr(self, "_custom_title_bar"):
            if theme.is_beveled:
                self._custom_title_bar.setStyleSheet(f"""
                    QWidget {{
                        background-color: {chrome_bg};
                        {theme.bevel_raised}
                    }}
                """)
                wctrl_style = f"""
                    QToolButton {{
                        background: {chrome_hover};
                        {theme.bevel_raised}
                        color: {fg};
                        font-size: 11px;
                    }}
                    QToolButton:hover {{
                        color: {fg};
                    }}
                    QToolButton:pressed {{
                        {theme.bevel_sunken}
                    }}
                """
            else:
                self._custom_title_bar.setStyleSheet(f"""
                    QWidget {{
                        background-color: {chrome_bg};
                        border-bottom: 1px solid {chrome_border};
                    }}
                """)
                wctrl_style = f"""
                    QToolButton {{
                        background: transparent;
                        border: none;
                        color: {self._hex_to_rgba(fg, 0.5)};
                        font-size: 11px;
                    }}
                    QToolButton:hover {{
                        color: {fg};
                        background: {chrome_hover};
                    }}
                """
            self._title_text_label.setStyleSheet(f"""
                QLabel {{
                    color: {fg};
                    font-size: 11px;
                    font-weight: bold;
                    background: transparent;
                    border: none;
                }}
            """)
            self._title_icon_label.setStyleSheet(
                "QLabel { background: transparent; border: none; }"
            )
            for btn in [self._min_btn, self._max_btn]:
                btn.setStyleSheet(wctrl_style)
            # Close button uses keyword/gold color
            close_color = theme.keyword
            if theme.is_beveled:
                self._close_btn.setStyleSheet(f"""
                    QToolButton {{
                        background: {chrome_hover};
                        {theme.bevel_raised}
                        color: {close_color};
                        font-size: 11px;
                        font-weight: bold;
                    }}
                    QToolButton:hover {{
                        color: {fg};
                        background: {close_color};
                    }}
                    QToolButton:pressed {{
                        {theme.bevel_sunken}
                        background: {close_color};
                    }}
                """)
            else:
                self._close_btn.setStyleSheet(f"""
                    QToolButton {{
                        background: transparent;
                        border: none;
                        color: {close_color};
                        font-size: 11px;
                        font-weight: bold;
                    }}
                    QToolButton:hover {{
                        color: {fg};
                        background: {close_color};
                    }}
                """)

        # Set header widget background to match menu bar
        if hasattr(self, "_header_widget"):
            self._header_widget.setStyleSheet(f"QWidget {{ background-color: {chrome_bg}; }}")

    def _apply_child_themes(self):
        """Apply theme to all child widgets after UI is fully constructed."""
        theme = self.settings_manager.get_current_theme()
        if hasattr(self, "side_panel"):
            self.side_panel.apply_theme()
        if hasattr(self, "file_browser"):
            self.file_browser.apply_theme()
        if hasattr(self, "activity_bar"):
            self.activity_bar.apply_theme()
        if hasattr(self, "formatting_toolbar"):
            self.formatting_toolbar.apply_theme(theme)
        if hasattr(self, "tab_widget"):
            from PyQt6.QtGui import QColor, QPalette

            palette = self.tab_widget.palette()
            palette.setColor(QPalette.ColorRole.Window, QColor(theme.chrome_bg))
            self.tab_widget.setPalette(palette)
            self.tab_widget.setAutoFillBackground(True)
        if hasattr(self, "new_tab_btn"):
            self._update_new_tab_button_style()
        if hasattr(self, "custom_tab_bar"):
            self.custom_tab_bar.apply_theme(theme)
        if hasattr(self, "find_bar"):
            self.find_bar.apply_theme()
        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            if isinstance(editor, EditorTab):
                editor.apply_theme()
                # Propagate theme to inline edit bar if it exists
                bar = editor.get_inline_edit_bar()
                if bar:
                    bar.apply_theme()

    def _setup_ui(self):
        """Initialize the main UI components."""
        self.setWindowTitle("MyNotion")
        self.setMinimumSize(300, 200)  # Allow small window like Notepad

        # Frameless window for custom Win95-style title bar
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self._drag_pos = None
        self._resize_edge = ""
        self._resize_origin = QPoint()
        self._resize_geo = self.geometry()

        # Set MyNotion icon for taskbar
        icon_path = self._get_resource_path("mynotion.ico")
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

        # Create + button on the tab widget, positioned over the tab bar area
        self.new_tab_btn = QToolButton(self.tab_widget)
        self.new_tab_btn.setText("+")
        self.new_tab_btn.setFixedWidth(28)
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

    def _update_new_tab_button_style(self):
        """Update + button style to match current theme."""
        theme = self.settings_manager.get_current_theme()
        if theme.is_beveled:
            self.new_tab_btn.setStyleSheet(f"""
                QToolButton {{
                    background-color: {theme.chrome_hover};
                    color: {self._hex_to_rgba(theme.foreground, 0.5)};
                    {theme.bevel_raised}
                    font-size: 14px;
                    font-weight: bold;
                }}
                QToolButton:hover {{
                    color: {theme.foreground};
                }}
            """)
        else:
            fg = theme.foreground
            self.new_tab_btn.setStyleSheet(f"""
                QToolButton {{
                    background-color: transparent;
                    color: {self._hex_to_rgba(fg, 0.35)};
                    border: none;
                    border-radius: 6px;
                    font-size: 18px;
                    font-weight: bold;
                }}
                QToolButton:hover {{
                    color: {fg};
                }}
            """)

    def resizeEvent(self, event):
        """Handle resize to update + button position and resize grips."""
        super().resizeEvent(event)
        if hasattr(self, "new_tab_btn"):
            QTimer.singleShot(10, self._update_new_tab_button_position)
        if hasattr(self, "_resize_grips"):
            self._position_resize_grips()

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
            self._update_language_indicator(lang)

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
            action.triggered.connect(self._on_language_selected)
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

        # ── Custom title bar ──
        self._custom_title_bar = QWidget()
        self._custom_title_bar.setFixedHeight(26)
        tb_layout = QHBoxLayout(self._custom_title_bar)
        tb_layout.setContentsMargins(4, 2, 2, 2)
        tb_layout.setSpacing(4)

        # App icon (16x16)
        self._title_icon_label = QLabel()
        self._title_icon_label.setFixedSize(16, 16)
        self._title_icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        icon_path = self._get_resource_path("mynotion.ico")
        if icon_path.exists():
            icon = QIcon(str(icon_path))
            self._title_icon_label.setPixmap(icon.pixmap(16, 16))
        tb_layout.addWidget(self._title_icon_label)

        # Title text
        self._title_text_label = QLabel("MyNotion")
        self._title_text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        tb_layout.addWidget(self._title_text_label)
        tb_layout.addStretch()

        # Window control buttons: minimize, maximize, close
        self._min_btn = QToolButton()
        self._min_btn.setText("\u2500")
        self._min_btn.setFixedSize(22, 18)
        self._min_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._min_btn.clicked.connect(self.showMinimized)
        tb_layout.addWidget(self._min_btn)

        self._max_btn = QToolButton()
        self._max_btn.setText("\u25a1")
        self._max_btn.setFixedSize(22, 18)
        self._max_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._max_btn.clicked.connect(self._toggle_maximize)
        tb_layout.addWidget(self._max_btn)

        self._close_btn = QToolButton()
        self._close_btn.setText("\u00d7")
        self._close_btn.setFixedSize(22, 18)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.clicked.connect(self.close)
        tb_layout.addWidget(self._close_btn)

        header_vlayout.addWidget(self._custom_title_bar)

        # Install event filter for title bar dragging
        self._custom_title_bar.installEventFilter(self)

        # ── Menu/toolbar row ──
        toolbar_row = QWidget()
        toolbar_layout = QHBoxLayout(toolbar_row)
        toolbar_layout.setContentsMargins(0, 0, 8, 0)
        toolbar_layout.setSpacing(0)

        toolbar_layout.addWidget(self._menu_bar)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self.formatting_toolbar)

        # AI completion toggle button
        self.completion_btn = QToolButton()
        self.completion_btn.setText("\u25c9 AI")
        self.completion_btn.setToolTip(self.tr("AI Code Completion (Ctrl+Shift+Space)"))
        self.completion_btn.setFixedHeight(22)
        self.completion_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.completion_btn.clicked.connect(self._toggle_completion)
        self.completion_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.completion_btn.customContextMenuRequested.connect(self._on_completion_btn_context_menu)
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

    def _get_resource_path(self, filename: str) -> Path:
        """Get path to a resource file, supporting both dev and PyInstaller."""
        if getattr(sys, "frozen", False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent.parent.parent
        return base_path / "resources" / filename

    def _toggle_maximize(self):
        """Toggle between maximized and normal window state."""
        if self.isMaximized():
            self.showNormal()
            self._max_btn.setText("\u25a1")
        else:
            self.showMaximized()
            self._max_btn.setText("\u2750")

    def keyPressEvent(self, event):
        """Handle Win+Arrow window snapping for frameless window."""
        if event.modifiers() == Qt.KeyboardModifier.MetaModifier:
            screen = self.screen().availableGeometry()
            key = event.key()
            if key == Qt.Key.Key_Left:
                self.showNormal()
                self._max_btn.setText("\u25a1")
                self.setGeometry(screen.x(), screen.y(), screen.width() // 2, screen.height())
                return
            if key == Qt.Key.Key_Right:
                self.showNormal()
                self._max_btn.setText("\u25a1")
                self.setGeometry(
                    screen.x() + screen.width() // 2,
                    screen.y(),
                    screen.width() // 2,
                    screen.height(),
                )
                return
            if key == Qt.Key.Key_Up:
                self.showMaximized()
                self._max_btn.setText("\u2750")
                return
            if key == Qt.Key.Key_Down:
                if self.isMaximized():
                    self.showNormal()
                    self._max_btn.setText("\u25a1")
                else:
                    self.showMinimized()
                return
        super().keyPressEvent(event)

    _EDGE_CURSORS = {
        "top": Qt.CursorShape.SizeVerCursor,
        "bottom": Qt.CursorShape.SizeVerCursor,
        "left": Qt.CursorShape.SizeHorCursor,
        "right": Qt.CursorShape.SizeHorCursor,
        "top_left": Qt.CursorShape.SizeFDiagCursor,
        "bottom_right": Qt.CursorShape.SizeFDiagCursor,
        "top_right": Qt.CursorShape.SizeBDiagCursor,
        "bottom_left": Qt.CursorShape.SizeBDiagCursor,
    }

    def _setup_resize_grips(self):
        """Create invisible overlay widgets at window edges for resize."""
        self._resize_grips = {}
        for edge, cursor in self._EDGE_CURSORS.items():
            grip = QWidget(self)
            grip.setCursor(cursor)
            grip.setStyleSheet("background: transparent;")
            grip.setProperty("resize_edge", edge)
            grip.installEventFilter(self)
            self._resize_grips[edge] = grip
        self._position_resize_grips()

    def _position_resize_grips(self):
        """Position resize grips at window edges and corners."""
        g = 6
        w, h = self.width(), self.height()
        gr = self._resize_grips
        gr["top"].setGeometry(g, 0, w - 2 * g, g)
        gr["bottom"].setGeometry(g, h - g, w - 2 * g, g)
        gr["left"].setGeometry(0, g, g, h - 2 * g)
        gr["right"].setGeometry(w - g, g, g, h - 2 * g)
        gr["top_left"].setGeometry(0, 0, g, g)
        gr["top_right"].setGeometry(w - g, 0, g, g)
        gr["bottom_left"].setGeometry(0, h - g, g, g)
        gr["bottom_right"].setGeometry(w - g, h - g, g, g)
        for grip in gr.values():
            grip.raise_()

    def eventFilter(self, obj: object, event: QEvent) -> bool:
        """Handle title bar dragging and resize grip events."""
        # ── Title bar dragging ──
        if hasattr(self, "_custom_title_bar") and obj == self._custom_title_bar:
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._drag_pos = event.globalPosition().toPoint()
                    return True
            elif event.type() == QEvent.Type.MouseMove:
                if self._drag_pos is not None:
                    if self.isMaximized():
                        ratio = event.position().x() / self.width()
                        self.showNormal()
                        self._max_btn.setText("\u25a1")
                        new_x = int(event.globalPosition().x() - self.width() * ratio)
                        new_y = int(event.globalPosition().y() - 13)
                        self.move(new_x, new_y)
                        self._drag_pos = event.globalPosition().toPoint()
                    else:
                        delta = event.globalPosition().toPoint() - self._drag_pos
                        self.move(self.pos() + delta)
                        self._drag_pos = event.globalPosition().toPoint()
                    return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                self._drag_pos = None
                return True
            elif (
                event.type() == QEvent.Type.MouseButtonDblClick
                and event.button() == Qt.MouseButton.LeftButton
            ):
                self._toggle_maximize()
                return True

        # ── Resize grip handling ──
        edge = obj.property("resize_edge") if hasattr(obj, "property") else None
        if edge and not self.isMaximized():
            if (
                event.type() == QEvent.Type.MouseButtonPress
                and event.button() == Qt.MouseButton.LeftButton
            ):
                self._resize_edge = edge
                self._resize_origin = event.globalPosition().toPoint()
                self._resize_geo = self.geometry()
                return True
            if event.type() == QEvent.Type.MouseMove and self._resize_edge:
                delta = event.globalPosition().toPoint() - self._resize_origin
                geo = self._resize_geo
                new_geo = geo.__class__(geo)
                if "left" in self._resize_edge:
                    new_geo.setLeft(geo.left() + delta.x())
                if "right" in self._resize_edge:
                    new_geo.setRight(geo.right() + delta.x())
                if "top" in self._resize_edge:
                    new_geo.setTop(geo.top() + delta.y())
                if "bottom" in self._resize_edge:
                    new_geo.setBottom(geo.bottom() + delta.y())
                if (
                    new_geo.width() >= self.minimumWidth()
                    and new_geo.height() >= self.minimumHeight()
                ):
                    self.setGeometry(new_geo)
                return True
            if event.type() == QEvent.Type.MouseButtonRelease:
                self._resize_edge = ""
                return True

        return super().eventFilter(obj, event)

    def _setup_statusbar(self):
        """Create the status bar with all indicators."""
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

    def _setup_completion(self):
        """Initialize the AI code completion system."""
        self._completion_manager = CompletionManager(self)
        self._completion_manager.suggestion_ready.connect(self._on_suggestion_ready)

        # Shortcut: Ctrl+Shift+Space to toggle completion
        toggle_completion = QAction(self.tr("Toggle Code Completion"), self)
        toggle_completion.setShortcut(QKeySequence("Ctrl+Shift+Space"))
        toggle_completion.triggered.connect(self._toggle_completion)
        self.addAction(toggle_completion)

        # Load saved state
        enabled = self.settings_manager.get_completion_enabled()
        self._completion_manager.set_enabled(enabled)
        self._completion_manager.set_max_lines(self.settings_manager.get_completion_max_lines())
        self._update_completion_indicator()

    def _toggle_completion(self):
        """Toggle AI code completion on/off."""
        enabled = not self._completion_manager.is_enabled()
        self._completion_manager.set_enabled(enabled)
        self.settings_manager.set_completion_enabled(enabled)

        # Update current editor
        editor = self.current_editor()
        if editor:
            editor.set_completion_enabled(enabled)
            if enabled:
                delay = self.settings_manager.get_completion_delay()
                editor.set_completion_delay(delay)

        self._update_completion_indicator()

    def _update_completion_indicator(self):
        """Update the AI button style and tooltip."""
        if not hasattr(self, "completion_btn"):
            return
        theme = self.settings_manager.get_current_theme()
        enabled = self._completion_manager.is_enabled()
        model = self.settings_manager.get_completion_model()

        fg = theme.foreground
        if theme.is_beveled:
            border = theme.bevel_raised
        else:
            border = f"border: 1px solid {theme.chrome_border};border-radius: {theme.radius};"
        pressed_bg = self._hex_to_rgba(theme.keyword, 0.15)
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
        hover_border = (
            "" if theme.is_beveled else f" border: 1px solid {self._hex_to_rgba(fg, 0.3)};"
        )
        if enabled:
            self.completion_btn.setText("\u25c9 AI")
            self.completion_btn.setToolTip(self.tr(f"AI Code Completion: ON \u2014 {model}"))
            self.completion_btn.setStyleSheet(
                f"QToolButton {{ background: {theme.chrome_hover};"
                f" color: {theme.keyword}; font-size: 11px;"
                f" font-weight: bold; {border} padding: 0 8px; }}"
                f"QToolButton:hover {{ color: {fg};{hover_border} }}"
                f" {pressed_style}"
            )
        else:
            self.completion_btn.setText("\u25c9 AI")
            self.completion_btn.setToolTip(self.tr("AI Code Completion (Ctrl+Shift+Space)"))
            self.completion_btn.setStyleSheet(
                f"QToolButton {{ background: {theme.chrome_hover};"
                f" color: {self._hex_to_rgba(fg, 0.55)}; font-size: 11px;"
                f" font-weight: bold; {border} padding: 0 8px; }}"
                f"QToolButton:hover {{ color: {fg};{hover_border} }}"
                f" {pressed_style}"
            )

    def _on_completion_btn_context_menu(self, pos):
        """Show a popup menu to select the completion model."""
        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self)
        current_model = self.settings_manager.get_completion_model()

        for model_info in COMPLETION_MODELS:
            action = QAction(model_info["name"], self)
            action.setCheckable(True)
            action.setChecked(model_info["id"] == current_model)
            action.setData(model_info["id"])
            action.triggered.connect(self._on_completion_model_selected)
            menu.addAction(action)

        menu.exec(self.completion_btn.mapToGlobal(pos))

    def _on_completion_model_selected(self):
        """Handle completion model selection from popup menu."""
        action = self.sender()
        if action:
            model_id = action.data()
            self.settings_manager.set_completion_model(model_id)
            self._update_completion_indicator()

    def _on_suggestion_ready(self, text: str):
        """Handle a completion suggestion from the CompletionManager."""
        editor = self.current_editor()
        if editor and self._completion_manager.is_enabled():
            editor.set_ghost_text(text)

    def _connect_completion_to_editor(self, editor: EditorTab):
        """Wire completion signals for the given editor."""
        enabled = self._completion_manager.is_enabled()
        editor.set_completion_enabled(enabled)
        if enabled:
            editor.set_completion_delay(self.settings_manager.get_completion_delay())
        editor.completion_requested.connect(self._on_editor_completion_requested)

    def _disconnect_completion_from_editor(self, editor: EditorTab):
        """Disconnect completion signals from an editor."""
        import contextlib

        with contextlib.suppress(TypeError):
            editor.completion_requested.disconnect(self._on_editor_completion_requested)
        editor.clear_ghost_text()
        editor.set_completion_enabled(False)

    def _on_editor_completion_requested(self, prefix: str, suffix: str):
        """Forward editor's completion request to the CompletionManager."""
        model = self.settings_manager.get_completion_model()
        self._completion_manager.request_completion(prefix, suffix, model)

    # ─── Inline AI Edit (Ctrl+K) ───

    def _setup_inline_edit(self):
        """Initialize the inline AI edit system."""
        self._inline_edit_manager = AIManager(self)
        self._inline_edit_buffer = ""
        self._inline_edit_selection_start = -1
        self._inline_edit_selection_end = -1
        self._inline_edit_active = False
        self._prev_inline_edit_editor = None

        self._inline_edit_manager.token_received.connect(self._on_inline_edit_token)
        self._inline_edit_manager.generation_finished.connect(self._on_inline_edit_finished)
        self._inline_edit_manager.generation_error.connect(self._on_inline_edit_error)

        # Shortcut: Ctrl+K to trigger inline edit
        inline_edit_action = QAction(self.tr("Inline AI Edit"), self)
        inline_edit_action.setShortcut(QKeySequence("Ctrl+K"))
        inline_edit_action.triggered.connect(self._on_inline_edit_shortcut)
        self.addAction(inline_edit_action)

    def _on_inline_edit_shortcut(self):
        """Handle Ctrl+K: show inline edit bar for current selection."""
        editor = self.current_editor()
        if not editor:
            return

        # Cancel any in-progress inline edit
        if self._inline_edit_active:
            self._inline_edit_manager.stop()
            self._inline_edit_buffer = ""
            self._inline_edit_active = False

        cursor = editor.textCursor()

        # Auto-select current line if no selection
        if not cursor.hasSelection():
            cursor.select(cursor.SelectionType.LineUnderCursor)
            editor.setTextCursor(cursor)

        # Guard: require at least 2 non-whitespace characters
        if len(cursor.selectedText().strip()) < 2:
            return

        editor.show_inline_edit()

    def _connect_inline_edit_to_editor(self, editor):
        """Wire inline edit signals for the given editor."""
        editor.inline_edit_requested.connect(self._on_inline_edit_requested)
        editor.inline_edit_cancelled.connect(self._on_inline_edit_cancelled)
        editor.inline_edit_accepted.connect(self._on_inline_edit_accepted)

    def _disconnect_inline_edit_from_editor(self, editor):
        """Disconnect inline edit signals from an editor."""
        with contextlib.suppress(TypeError):
            editor.inline_edit_requested.disconnect(self._on_inline_edit_requested)
        with contextlib.suppress(TypeError):
            editor.inline_edit_cancelled.disconnect(self._on_inline_edit_cancelled)
        with contextlib.suppress(TypeError):
            editor.inline_edit_accepted.disconnect(self._on_inline_edit_accepted)

    def _on_inline_edit_requested(self, instruction: str):
        """Handle instruction submission from inline edit bar."""
        editor = self.current_editor()
        if not editor:
            return

        cursor = editor.textCursor()
        selected_text = cursor.selectedText().replace("\u2029", "\n")

        # Save selection positions for later replacement
        self._inline_edit_selection_start = cursor.selectionStart()
        self._inline_edit_selection_end = cursor.selectionEnd()
        self._inline_edit_buffer = ""
        self._inline_edit_active = True

        # Update bar status
        bar = editor.get_inline_edit_bar()
        if bar:
            bar.set_generating(True)

        # Build mode-aware prompt
        is_writing = self.side_panel.get_layout_mode() == LayoutMode.WRITING

        if is_writing:
            prompt = f"Instruction: {instruction}\n\nText:\n{selected_text}\n\nEdited text:"
            system_prompt = (
                "You are a text editor. Edit the text according to the instruction.\n"
                "Return ONLY the edited text. No explanations, no markdown fences, no commentary."
            )
        else:
            prompt = f"Instruction: {instruction}\n\nCode:\n{selected_text}\n\nEdited code:"
            system_prompt = (
                "You are a code editor. Edit the code according to the instruction.\n"
                "Return ONLY the edited code. No explanations, no markdown fences, no commentary."
            )

        # Use the side panel's current model
        model = self.side_panel.current_model["id"]

        self._inline_edit_manager.generate(
            model=model,
            prompt=prompt,
            context=system_prompt,
            mode="writing" if is_writing else "coding",
        )

    def _on_inline_edit_token(self, token: str):
        """Collect streamed tokens into the buffer."""
        self._inline_edit_buffer += token

    def _on_inline_edit_finished(self):
        """Handle AI generation complete — replace selection with result."""
        editor = self.current_editor()
        if not editor:
            return

        code = self._strip_code_fences(self._inline_edit_buffer)
        self._inline_edit_active = False

        if not code.strip():
            bar = editor.get_inline_edit_bar()
            if bar:
                bar.set_error("AI returned empty response")
            return

        # Replace selection as a single undo operation
        cursor = editor.textCursor()
        cursor.setPosition(self._inline_edit_selection_start)
        cursor.setPosition(self._inline_edit_selection_end, cursor.MoveMode.KeepAnchor)

        cursor.beginEditBlock()
        cursor.insertText(code)
        cursor.endEditBlock()

        # Calculate the end position of inserted text
        insert_end = self._inline_edit_selection_start + len(code)

        # Highlight the replaced region
        editor.highlight_edited_region(self._inline_edit_selection_start, insert_end)

        # Update bar status
        bar = editor.get_inline_edit_bar()
        if bar:
            bar.set_status("Enter/Tab = accept, Esc = undo")
            bar.set_generating(False)

    def _on_inline_edit_error(self, error: str):
        """Handle AI generation error."""
        self._inline_edit_active = False
        editor = self.current_editor()
        if editor:
            bar = editor.get_inline_edit_bar()
            if bar:
                bar.set_error(error)

    def _on_inline_edit_cancelled(self):
        """Handle cancel: stop generation, undo if edit was made, hide bar."""
        # Stop generation if running
        if self._inline_edit_active:
            self._inline_edit_manager.stop()
            self._inline_edit_buffer = ""
            self._inline_edit_active = False

        editor = self.current_editor()
        if not editor:
            return

        # If an edit was applied, undo it
        if editor._has_edit_highlights:
            editor.document().undo()

        editor.hide_inline_edit()
        editor.setFocus()

    def _on_inline_edit_accepted(self):
        """Handle accept: clear highlights, hide bar, keep the edit."""
        editor = self.current_editor()
        if editor:
            editor.hide_inline_edit()
            editor.setFocus()

    @staticmethod
    def _strip_code_fences(code: str) -> str:
        """Strip markdown code fences from AI response."""
        lines = code.strip().split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines)

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
                try:
                    editor.save_file()
                    saved_count += 1
                except OSError:
                    pass  # Silently skip files that fail to save

        if saved_count > 0:
            msg = f"Auto-saved {saved_count} file{'s' if saved_count > 1 else ''}"
            self.statusbar.showMessage(msg, 3000)

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

        # Stop all running AI threads before closing
        if hasattr(self, "_inline_edit_manager"):
            self._inline_edit_manager.stop()
        if hasattr(self, "side_panel") and hasattr(self.side_panel, "ai_manager"):
            self.side_panel.ai_manager.stop()

        self._save_session()
        self.settings.setValue("geometry", self.saveGeometry())
        event.accept()

    def _on_tab_changed(self, index: int):
        """Handle tab change to update status bar with fade transition."""
        # Disconnect previous editor's inline edit signals
        if hasattr(self, "_prev_inline_edit_editor") and self._prev_inline_edit_editor:
            self._disconnect_inline_edit_from_editor(self._prev_inline_edit_editor)

        # Cancel any pending completion from previous tab
        if hasattr(self, "_completion_manager"):
            self._completion_manager.cancel()

        # Cancel any in-progress inline edit
        if hasattr(self, "_inline_edit_manager") and self._inline_edit_active:
            self._inline_edit_manager.stop()
            self._inline_edit_buffer = ""
            self._inline_edit_active = False

        editor = self.current_editor()
        if editor:
            self._update_language_indicator(editor.language)
            self._connect_editor_signals(editor)
            # Wire completion to new tab
            if hasattr(self, "_completion_manager"):
                self._connect_completion_to_editor(editor)
            # Wire inline edit to new tab
            if hasattr(self, "_inline_edit_manager"):
                self._connect_inline_edit_to_editor(editor)
                self._prev_inline_edit_editor = editor
            # Update find bar's editor reference
            self.find_bar.set_editor(editor)
            # Update window title with current filename
            self._update_window_title()
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

    def _apply_layout_mode(self, mode: LayoutMode):
        """Apply layout mode to settings and side panel."""
        self.settings_manager.set_layout_mode(mode.value)
        self.side_panel.set_layout_mode(mode)

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
        self._update_window_title()
        self.recent_files.add_file(filepath)

    # Tab management
    def new_tab(self):
        """Create a new editor tab."""
        editor = EditorTab(parent=self.tab_widget)
        index = self.tab_widget.addTab(editor, self.tr("Untitled"))
        self.tab_widget.setCurrentIndex(index)
        self._connect_editor_signals(editor)
        # Wire completion for new tab
        if hasattr(self, "_completion_manager"):
            self._connect_completion_to_editor(editor)
        # Wire inline edit for new tab
        if hasattr(self, "_inline_edit_manager"):
            self._connect_inline_edit_to_editor(editor)
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

    def open_folder(self):
        """Open a folder dialog to select project folder for file browser."""
        self.file_browser.open_folder_dialog()

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

        svg_path = self._get_resource_path("mynotion_about.svg")
        if svg_path.exists():
            renderer = QSvgRenderer(str(svg_path))
            image = QImage(64, 64, QImage.Format.Format_ARGB32)
            image.fill(0)
            painter = QPainter(image)
            renderer.render(painter)
            painter.end()
            about_box.setIconPixmap(QPixmap.fromImage(image))

        about_box.exec()

    def _apply_settings_to_editors(self):
        """Apply changed settings to all editor tabs and window chrome."""
        self._apply_theme()
        self._apply_child_themes()
        self._update_status_bar()
        self._start_auto_save_timer()

        # Refresh completion settings
        if hasattr(self, "_completion_manager"):
            enabled = self.settings_manager.get_completion_enabled()
            self._completion_manager.set_enabled(enabled)
            self._completion_manager.set_max_lines(self.settings_manager.get_completion_max_lines())
            editor = self.current_editor()
            if editor:
                editor.set_completion_enabled(enabled)
                editor.set_completion_delay(self.settings_manager.get_completion_delay())
            self._update_completion_indicator()

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
