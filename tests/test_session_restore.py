# =============================================================================
# tests/test_session_restore.py — Tests for session restore functionality
# =============================================================================

from core.settings import SettingsManager


class TestSessionSettings:
    """Tests for session restore settings in SettingsManager."""

    def test_session_tabs_default_empty(self, qapp, isolated_settings):
        """Session tabs default to empty list."""
        sm = SettingsManager()
        assert sm.get_session_tabs() == []

    def test_session_tabs_roundtrip(self, qapp, isolated_settings):
        """Session tab data round-trips through SettingsManager."""
        sm = SettingsManager()
        tabs = [
            {"filepath": "C:/test/file.py", "cursor_line": 5, "cursor_col": 10, "scroll_pos": 100},
            {"filepath": "C:/test/other.txt", "cursor_line": 0, "cursor_col": 0, "scroll_pos": 0},
        ]
        sm.set_session_tabs(tabs)
        result = sm.get_session_tabs()
        assert len(result) == 2
        assert result[0]["filepath"] == "C:/test/file.py"
        assert result[1]["cursor_line"] == 0

    def test_session_active_tab_default(self, qapp, isolated_settings):
        """Active tab defaults to 0."""
        sm = SettingsManager()
        assert sm.get_session_active_tab() == 0

    def test_session_active_tab_roundtrip(self, qapp, isolated_settings):
        """Active tab index round-trips through SettingsManager."""
        sm = SettingsManager()
        sm.set_session_active_tab(3)
        assert sm.get_session_active_tab() == 3


class TestSessionSaveRestore:
    """Tests for session save and restore in MainWindow."""

    def test_save_session_stores_filepaths(self, qapp, qtbot, tmp_path):
        """Saving session persists open file paths."""
        from ui.main_window import MainWindow

        # Create a temp file
        test_file = tmp_path / "hello.py"
        test_file.write_text("print('hello')", encoding="utf-8")

        window = MainWindow()
        qtbot.addWidget(window)

        # Open the file
        window._open_file_path(str(test_file))
        window._save_session()

        sm = SettingsManager()
        tabs = sm.get_session_tabs()
        filepaths = [t["filepath"] for t in tabs]
        assert str(test_file) in filepaths

    def test_save_session_skips_untitled(self, qapp, qtbot):
        """Untitled tabs (no filepath) are not saved in session."""
        from ui.main_window import MainWindow

        # Clear any leftover session data from previous tests
        sm = SettingsManager()
        sm.set_session_tabs([])

        window = MainWindow()
        qtbot.addWidget(window)

        # Only untitled tabs exist
        window._save_session()

        tabs = sm.get_session_tabs()
        assert len(tabs) == 0

    def test_restore_session_opens_files(self, qapp, qtbot, tmp_path):
        """Restoring session opens previously saved files."""
        from ui.main_window import MainWindow

        # Create temp files
        file1 = tmp_path / "file1.txt"
        file1.write_text("content1", encoding="utf-8")
        file2 = tmp_path / "file2.txt"
        file2.write_text("content2", encoding="utf-8")

        # Seed session settings
        sm = SettingsManager()
        sm.set_session_tabs([
            {"filepath": str(file1), "cursor_line": 0, "cursor_col": 0, "scroll_pos": 0},
            {"filepath": str(file2), "cursor_line": 0, "cursor_col": 0, "scroll_pos": 0},
        ])

        # Create window (will auto-restore)
        window = MainWindow()
        qtbot.addWidget(window)

        # Should have restored the 2 files (no extra untitled tab)
        assert window.tab_widget.count() == 2

    def test_restore_session_handles_missing_file(self, qapp, qtbot, tmp_path):
        """Missing files are skipped without error."""
        from ui.main_window import MainWindow

        # Seed with a non-existent file
        sm = SettingsManager()
        sm.set_session_tabs([
            {"filepath": str(tmp_path / "gone.txt"), "cursor_line": 0, "cursor_col": 0, "scroll_pos": 0},
        ])

        # Should fall back to blank tab since restore finds no valid files
        window = MainWindow()
        qtbot.addWidget(window)

        assert window.tab_widget.count() == 1
        editor = window.tab_widget.widget(0)
        assert editor.filepath is None  # Untitled fallback

    def test_restore_session_empty_returns_false(self, qapp, qtbot):
        """Empty session causes fallback to new blank tab."""
        from ui.main_window import MainWindow

        # No session data saved
        window = MainWindow()
        qtbot.addWidget(window)

        # Should have one untitled tab
        assert window.tab_widget.count() == 1
