"""
Theme engine — generates and applies QSS stylesheets for the application.

Centralizes all theme/QSS logic. Other modules import ``hex_to_rgba``
from here instead of duplicating the helper.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QMainWindow, QToolButton

    from core.settings import EditorTheme, SettingsManager


# ── Public color utility ────────────────────────────────────────────


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convert a hex color string to an ``rgba()`` CSS value."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ── Theme engine ────────────────────────────────────────────────────


class ThemeEngine:
    """Stateless helper that builds and applies QSS to the main window.

    Not a QObject — instantiated once by MainWindow and called when the
    theme changes.
    """

    def __init__(self, window: QMainWindow, settings_manager: SettingsManager) -> None:
        self._win = window
        self._settings = settings_manager

    # ─── public API ─────────────────────────────────────────────────

    def apply_theme(self) -> None:
        """Generate and apply the full application stylesheet."""
        theme = self._settings.get_current_theme()
        self._apply_main_qss(theme)
        self._apply_title_bar_qss(theme)

    def apply_child_themes(self) -> None:
        """Propagate the current theme to all child widgets."""
        theme = self._settings.get_current_theme()
        win = self._win

        if hasattr(win, "side_panel"):
            win.side_panel.apply_theme()
        if hasattr(win, "file_browser"):
            win.file_browser.apply_theme()
        if hasattr(win, "activity_bar"):
            win.activity_bar.apply_theme()
        if hasattr(win, "formatting_toolbar"):
            win.formatting_toolbar.apply_theme(theme)
        if hasattr(win, "tab_widget"):
            from PyQt6.QtGui import QColor, QPalette

            palette = win.tab_widget.palette()
            palette.setColor(QPalette.ColorRole.Window, QColor(theme.chrome_bg))
            win.tab_widget.setPalette(palette)
            win.tab_widget.setAutoFillBackground(True)
        if hasattr(win, "new_tab_btn"):
            self.update_new_tab_button_style()
        if hasattr(win, "custom_tab_bar"):
            win.custom_tab_bar.apply_theme(theme)
        if hasattr(win, "find_bar"):
            win.find_bar.apply_theme()

        # Editors + inline edit bars
        from ui.editor_tab import EditorTab

        for i in range(win.tab_widget.count()):
            editor = win.tab_widget.widget(i)
            if isinstance(editor, EditorTab):
                editor.apply_theme()
                bar = editor.get_inline_edit_bar()
                if bar:
                    bar.apply_theme()

    def update_new_tab_button_style(self) -> None:
        """Update the ``+`` tab button to match the current theme."""
        theme = self._settings.get_current_theme()
        btn: QToolButton = self._win.new_tab_btn  # type: ignore[attr-defined]
        if theme.is_beveled:
            btn.setStyleSheet(f"""
                QToolButton {{
                    background-color: {theme.chrome_hover};
                    color: {hex_to_rgba(theme.foreground, 0.5)};
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
            btn.setStyleSheet(f"""
                QToolButton {{
                    background-color: transparent;
                    color: {hex_to_rgba(fg, 0.35)};
                    border: none;
                    border-radius: 6px;
                    font-size: 18px;
                    font-weight: bold;
                }}
                QToolButton:hover {{
                    color: {fg};
                }}
            """)

    # ─── private helpers ────────────────────────────────────────────

    def _apply_main_qss(self, theme: EditorTheme) -> None:
        """Build and set the main QSS stylesheet on the window."""
        bg = theme.background
        chrome_bg = theme.chrome_bg
        chrome_hover = theme.chrome_hover
        chrome_border = theme.chrome_border
        fg = theme.foreground
        selection = theme.selection

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
                color: {hex_to_rgba(fg, 0.5)};
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
                color: {hex_to_rgba(fg, 0.7)};
            }}"""

            pane_qss = f"""
            QTabWidget::pane {{
                {theme.bevel_sunken}
                background-color: {bg};
            }}"""

            status_qss = f"""
            QStatusBar {{
                background-color: {chrome_bg};
                color: {hex_to_rgba(fg, 0.6)};
                {theme.bevel_raised}
                font-size: 11px;
                padding: 2px 4px;
            }}
            QStatusBar::item {{
                border: none;
            }}
            QStatusBar QLabel {{
                color: {hex_to_rgba(fg, 0.6)};
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
                color: {hex_to_rgba(fg, 0.5)};
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
                background-color: {hex_to_rgba(fg, 0.05)};
                color: {hex_to_rgba(fg, 0.7)};
            }}"""

            pane_qss = f"""
            QTabWidget::pane {{
                border-top: 1px solid {chrome_border};
                background-color: {bg};
            }}"""

            status_qss = f"""
            QStatusBar {{
                background-color: {chrome_bg};
                color: {hex_to_rgba(fg, 0.6)};
                border-top: 1px solid {chrome_border};
                font-size: 11px;
                padding: 2px 4px;
            }}
            QStatusBar::item {{
                border: none;
            }}
            QStatusBar QLabel {{
                color: {hex_to_rgba(fg, 0.6)};
                background-color: {hex_to_rgba(fg, 0.04)};
                border: 1px solid {hex_to_rgba(fg, 0.08)};
                border-radius: 6px;
                padding: 2px 10px;
                margin: 1px 2px;
                font-size: 10px;
            }}
            QStatusBar QLabel:hover {{
                color: {fg};
                background-color: {hex_to_rgba(fg, 0.1)};
                border: 1px solid {hex_to_rgba(fg, 0.15)};
            }}"""

        self._win.setStyleSheet(f"""
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
                background-color: {hex_to_rgba(fg, 0.15)};
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
                background-color: {hex_to_rgba(fg, 0.15)};
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

    def _apply_title_bar_qss(self, theme: EditorTheme) -> None:
        """Style the custom title bar and its buttons."""
        win = self._win
        if not hasattr(win, "_custom_title_bar"):
            return

        fg = theme.foreground
        chrome_bg = theme.chrome_bg
        chrome_hover = theme.chrome_hover
        chrome_border = theme.chrome_border

        if theme.is_beveled:
            win._custom_title_bar.setStyleSheet(f"""
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
            win._custom_title_bar.setStyleSheet(f"""
                QWidget {{
                    background-color: {chrome_bg};
                    border-bottom: 1px solid {chrome_border};
                }}
            """)
            wctrl_style = f"""
                QToolButton {{
                    background: transparent;
                    border: none;
                    color: {hex_to_rgba(fg, 0.5)};
                    font-size: 11px;
                }}
                QToolButton:hover {{
                    color: {fg};
                    background: {chrome_hover};
                }}
            """

        win._title_text_label.setStyleSheet(f"""
            QLabel {{
                color: {fg};
                font-size: 11px;
                font-weight: bold;
                background: transparent;
                border: none;
            }}
        """)
        win._title_icon_label.setStyleSheet("QLabel { background: transparent; border: none; }")

        for btn in [win._min_btn, win._max_btn]:
            btn.setStyleSheet(wctrl_style)

        # Close button uses keyword/gold color
        close_color = theme.keyword
        if theme.is_beveled:
            win._close_btn.setStyleSheet(f"""
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
            win._close_btn.setStyleSheet(f"""
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

        # Header widget background
        if hasattr(win, "_header_widget"):
            win._header_widget.setStyleSheet(f"QWidget {{ background-color: {chrome_bg}; }}")
