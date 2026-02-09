# =============================================================================
# tests/test_theme_engine.py — Tests for ThemeEngine and hex_to_rgba
# =============================================================================

from unittest.mock import MagicMock

from core.settings import EditorTheme
from ui.theme_engine import ThemeEngine, hex_to_rgba

# ---------------------------------------------------------------------------
# hex_to_rgba — pure function tests
# ---------------------------------------------------------------------------


class TestHexToRgba:
    """Tests for the hex_to_rgba utility function."""

    def test_basic_black(self):
        assert hex_to_rgba("#000000", 1.0) == "rgba(0,0,0,1.0)"

    def test_basic_white(self):
        assert hex_to_rgba("#FFFFFF", 1.0) == "rgba(255,255,255,1.0)"

    def test_red(self):
        assert hex_to_rgba("#FF0000", 0.5) == "rgba(255,0,0,0.5)"

    def test_mixed_color(self):
        assert hex_to_rgba("#1E2A3B", 0.8) == "rgba(30,42,59,0.8)"

    def test_alpha_zero(self):
        assert hex_to_rgba("#AABBCC", 0) == "rgba(170,187,204,0)"

    def test_no_hash_prefix(self):
        """hex_to_rgba should handle colors without the # prefix."""
        assert hex_to_rgba("FF8800", 1.0) == "rgba(255,136,0,1.0)"

    def test_lowercase_hex(self):
        assert hex_to_rgba("#aabbcc", 0.5) == "rgba(170,187,204,0.5)"


# ---------------------------------------------------------------------------
# ThemeEngine — stylesheet application tests
# ---------------------------------------------------------------------------


def _make_theme(*, beveled: bool = False) -> EditorTheme:
    """Create a minimal EditorTheme for testing."""
    kwargs = dict(
        name="test",
        background="#1E1E1E",
        foreground="#D4D4D4",
        line_number_bg="#1E1E1E",
        line_number_fg="#858585",
        current_line="#282828",
        selection="#264F78",
        keyword="#C586C0",
        string="#CE9178",
        comment="#6A9955",
        number="#B5CEA8",
        function="#DCDCAA",
        class_name="#4EC9B0",
        decorator="#D7BA7D",
        chrome_bg="#252526",
        chrome_hover="#2A2D2E",
        chrome_border="#3E3E3E",
    )
    if beveled:
        kwargs.update(
            style_variant="win95",
            bevel_light="#808080",
            bevel_dark="#404040",
        )
    return EditorTheme(**kwargs)


class TestThemeEngine:
    """Tests for ThemeEngine stylesheet application."""

    def test_apply_theme_sets_stylesheet(self, qapp):
        """apply_theme should call setStyleSheet on the window."""
        window = MagicMock()
        settings = MagicMock()
        settings.get_current_theme.return_value = _make_theme()

        engine = ThemeEngine(window, settings)
        engine.apply_theme()

        window.setStyleSheet.assert_called_once()
        qss = window.setStyleSheet.call_args[0][0]
        assert "QMainWindow" in qss
        assert "QMenuBar" in qss

    def test_apply_theme_beveled(self, qapp):
        """Beveled theme should produce bevel-style borders."""
        window = MagicMock()
        settings = MagicMock()
        settings.get_current_theme.return_value = _make_theme(beveled=True)

        engine = ThemeEngine(window, settings)
        engine.apply_theme()

        qss = window.setStyleSheet.call_args[0][0]
        assert "border-top: 2px solid" in qss

    def test_apply_theme_modern(self, qapp):
        """Modern theme should produce rounded borders."""
        window = MagicMock()
        settings = MagicMock()
        settings.get_current_theme.return_value = _make_theme(beveled=False)

        engine = ThemeEngine(window, settings)
        engine.apply_theme()

        qss = window.setStyleSheet.call_args[0][0]
        assert "border-radius: 6px" in qss

    def test_apply_child_themes_propagates(self, qapp):
        """apply_child_themes should call apply_theme on child widgets."""
        theme = _make_theme()
        window = MagicMock()
        window.tab_widget.count.return_value = 0
        settings = MagicMock()
        settings.get_current_theme.return_value = theme

        engine = ThemeEngine(window, settings)
        engine.apply_child_themes()

        window.side_panel.apply_theme.assert_called_once()
        window.file_browser.apply_theme.assert_called_once()
        window.activity_bar.apply_theme.assert_called_once()
        window.find_bar.apply_theme.assert_called_once()

    def test_apply_child_themes_skips_missing(self, qapp):
        """apply_child_themes should skip widgets that don't exist."""
        theme = _make_theme()

        # Build a window that only has tab_widget (required) but
        # none of the optional child widgets.
        class BareWindow:
            pass

        window = BareWindow()
        window.tab_widget = MagicMock()
        window.tab_widget.count.return_value = 0

        settings = MagicMock()
        settings.get_current_theme.return_value = theme

        engine = ThemeEngine(window, settings)
        # Should not raise even though window has no side_panel etc.
        engine.apply_child_themes()

    def test_title_bar_qss_skips_when_missing(self, qapp):
        """_apply_title_bar_qss should do nothing if no title bar."""
        window = MagicMock(spec=[])  # no _custom_title_bar
        settings = MagicMock()
        settings.get_current_theme.return_value = _make_theme()

        engine = ThemeEngine(window, settings)
        # Access private method for targeted test
        engine._apply_title_bar_qss(_make_theme())
        # No assertions needed — just verifying no AttributeError

    def test_title_bar_qss_applies_when_present(self, qapp):
        """_apply_title_bar_qss should style title bar components."""
        window = MagicMock()
        settings = MagicMock()
        theme = _make_theme()

        engine = ThemeEngine(window, settings)
        engine._apply_title_bar_qss(theme)

        window._custom_title_bar.setStyleSheet.assert_called_once()
        window._title_text_label.setStyleSheet.assert_called_once()
        window._min_btn.setStyleSheet.assert_called_once()
        window._close_btn.setStyleSheet.assert_called_once()

    def test_update_new_tab_button_modern(self, qapp):
        """New tab button should get modern styling."""
        window = MagicMock()
        settings = MagicMock()
        settings.get_current_theme.return_value = _make_theme(beveled=False)

        engine = ThemeEngine(window, settings)
        engine.update_new_tab_button_style()

        qss = window.new_tab_btn.setStyleSheet.call_args[0][0]
        assert "border-radius: 6px" in qss
        assert "transparent" in qss

    def test_update_new_tab_button_beveled(self, qapp):
        """New tab button should get beveled styling."""
        window = MagicMock()
        settings = MagicMock()
        settings.get_current_theme.return_value = _make_theme(beveled=True)

        engine = ThemeEngine(window, settings)
        engine.update_new_tab_button_style()

        qss = window.new_tab_btn.setStyleSheet.call_args[0][0]
        assert "border-top: 2px solid" in qss
