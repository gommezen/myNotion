# =============================================================================
# tests/test_session_restore.py — Tests for session restore functionality
# =============================================================================

import pytest

from core.settings import SettingsManager


@pytest.fixture(autouse=True)
def _clear_session(qapp, isolated_settings):
    """Clear session data before each test to prevent MainWindow from restoring real files."""
    sm = SettingsManager()
    sm.set_session_tabs([])


def _destroy_window(window):
    """Safely destroy a MainWindow without triggering unsaved-changes dialog."""
    window._auto_save_timer.stop()
    while window.tab_widget.count() > 0:
        editor = window.tab_widget.widget(0)
        if hasattr(editor, "document"):
            editor.document().setModified(False)
        window.tab_widget.removeTab(0)
    window.hide()
    window.deleteLater()


@pytest.fixture()
def main_window():
    """Create a MainWindow and ensure proper cleanup after the test."""

    from ui.main_window import MainWindow

    window = MainWindow()
    yield window
    _destroy_window(window)


class TestSessionSettings:
    """Tests for session restore settings in SettingsManager."""

    def test_session_tabs_default_empty(self):
        """Session tabs default to empty list when key is absent."""
        sm = SettingsManager()
        sm.settings.remove("session_tabs")
        assert sm.get_session_tabs() == []

    def test_session_tabs_roundtrip(self):
        """Session tab data round-trips through SettingsManager."""
        sm = SettingsManager()
        tabs = [
            {
                "filepath": "C:/test/file.py",
                "cursor_line": 5,
                "cursor_col": 10,
                "scroll_pos": 100,
            },
            {
                "filepath": "C:/test/other.txt",
                "cursor_line": 0,
                "cursor_col": 0,
                "scroll_pos": 0,
            },
        ]
        sm.set_session_tabs(tabs)
        result = sm.get_session_tabs()
        assert len(result) == 2
        assert result[0]["filepath"] == "C:/test/file.py"
        assert result[1]["cursor_line"] == 0

    def test_session_active_tab_default(self):
        """Active tab defaults to 0 when key is absent."""
        sm = SettingsManager()
        sm.settings.remove("session_active_tab")
        assert sm.get_session_active_tab() == 0

    def test_session_active_tab_roundtrip(self):
        """Active tab index round-trips through SettingsManager."""
        sm = SettingsManager()
        sm.set_session_active_tab(3)
        assert sm.get_session_active_tab() == 3


class TestSessionSaveRestore:
    """Tests for session save and restore in MainWindow."""

    def test_save_session_stores_filepaths(self, main_window, tmp_path):
        """Saving session persists open file paths."""
        test_file = tmp_path / "hello.py"
        test_file.write_text("print('hello')", encoding="utf-8")

        main_window._open_file_path(str(test_file))
        main_window._save_session()

        sm = SettingsManager()
        tabs = sm.get_session_tabs()
        filepaths = [t["filepath"] for t in tabs]
        assert str(test_file) in filepaths

    def test_save_session_skips_untitled(self, main_window):
        """Untitled tabs (no filepath) are not saved in session."""
        main_window._save_session()

        sm = SettingsManager()
        tabs = sm.get_session_tabs()
        assert len(tabs) == 0

    def test_restore_session_opens_files(self, tmp_path):
        """Restoring session opens previously saved files."""
        from ui.main_window import MainWindow

        file1 = tmp_path / "file1.txt"
        file1.write_text("content1", encoding="utf-8")
        file2 = tmp_path / "file2.txt"
        file2.write_text("content2", encoding="utf-8")

        sm = SettingsManager()
        sm.set_session_tabs(
            [
                {"filepath": str(file1), "cursor_line": 0, "cursor_col": 0, "scroll_pos": 0},
                {"filepath": str(file2), "cursor_line": 0, "cursor_col": 0, "scroll_pos": 0},
            ]
        )

        window = MainWindow()
        assert window.tab_widget.count() == 2
        _destroy_window(window)

    def test_restore_session_handles_missing_file(self, tmp_path):
        """Missing files are skipped without error."""
        from ui.main_window import MainWindow

        sm = SettingsManager()
        sm.set_session_tabs(
            [
                {
                    "filepath": str(tmp_path / "gone.txt"),
                    "cursor_line": 0,
                    "cursor_col": 0,
                    "scroll_pos": 0,
                },
            ]
        )

        window = MainWindow()
        assert window.tab_widget.count() == 1
        editor = window.tab_widget.widget(0)
        assert editor.filepath is None
        _destroy_window(window)

    def test_restore_session_empty_creates_blank_tab(self, main_window):
        """Empty session causes fallback to new blank tab."""
        assert main_window.tab_widget.count() == 1
