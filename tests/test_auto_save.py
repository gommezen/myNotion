# =============================================================================
# tests/test_auto_save.py — Tests for auto-save functionality
# =============================================================================

from core.settings import SettingsManager


class TestAutoSaveSettings:
    """Tests for auto-save settings in SettingsManager."""

    def test_auto_save_enabled_default(self, qapp, isolated_settings):
        """Auto-save is enabled by default."""
        sm = SettingsManager()
        assert sm.get_auto_save_enabled() is True

    def test_auto_save_enabled_roundtrip(self, qapp, isolated_settings):
        """Auto-save enabled flag round-trips."""
        sm = SettingsManager()
        sm.set_auto_save_enabled(False)
        assert sm.get_auto_save_enabled() is False

    def test_auto_save_interval_default(self, qapp, isolated_settings):
        """Auto-save interval defaults to 30 seconds."""
        sm = SettingsManager()
        assert sm.get_auto_save_interval() == 30

    def test_auto_save_interval_clamped(self, qapp, isolated_settings):
        """Interval is clamped between 5 and 300 seconds."""
        sm = SettingsManager()
        sm.set_auto_save_interval(1)
        assert sm.get_auto_save_interval() == 5
        sm.set_auto_save_interval(999)
        assert sm.get_auto_save_interval() == 300


class TestAutoSave:
    """Tests for auto-save behavior in MainWindow."""

    def test_auto_save_saves_modified_file(self, qapp, qtbot, tmp_path):
        """Auto-save writes modified files with a filepath."""
        from ui.main_window import MainWindow

        test_file = tmp_path / "auto.txt"
        test_file.write_text("original", encoding="utf-8")

        window = MainWindow()
        qtbot.addWidget(window)

        window._open_file_path(str(test_file))
        editor = window.current_editor()

        # Modify the editor content
        editor.setPlainText("modified content")
        editor.document().setModified(True)

        # Trigger auto-save
        window._auto_save()

        # File should be updated on disk
        assert test_file.read_text(encoding="utf-8") == "modified content"
        assert not editor.document().isModified()

    def test_auto_save_skips_untitled(self, qapp, qtbot):
        """Auto-save skips tabs without a filepath."""
        from ui.main_window import MainWindow

        # Ensure no session restore interferes
        sm = SettingsManager()
        sm.set_session_tabs([])

        window = MainWindow()
        qtbot.addWidget(window)

        editor = window.current_editor()
        # Type via qtbot to trigger real modification state
        qtbot.keyClicks(editor, "some text")
        assert editor.document().isModified()

        # Should not raise or crash
        window._auto_save()

        # Document still marked as modified (was not saved — no filepath)
        assert editor.document().isModified()

    def test_auto_save_skips_unmodified(self, qapp, qtbot, tmp_path):
        """Auto-save skips tabs that are not modified."""
        from ui.main_window import MainWindow

        test_file = tmp_path / "clean.txt"
        test_file.write_text("original", encoding="utf-8")

        window = MainWindow()
        qtbot.addWidget(window)

        window._open_file_path(str(test_file))

        # Not modified — auto-save should be a no-op
        window._auto_save()

        assert test_file.read_text(encoding="utf-8") == "original"

    def test_auto_save_timer_active_when_enabled(self, qapp, qtbot):
        """Timer is active when auto-save is enabled."""
        from ui.main_window import MainWindow

        sm = SettingsManager()
        sm.set_auto_save_enabled(True)
        sm.set_auto_save_interval(30)

        window = MainWindow()
        qtbot.addWidget(window)

        assert window._auto_save_timer.isActive()
        assert window._auto_save_timer.interval() == 30000

    def test_auto_save_timer_inactive_when_disabled(self, qapp, qtbot):
        """Timer is inactive when auto-save is disabled."""
        from ui.main_window import MainWindow

        sm = SettingsManager()
        sm.set_auto_save_enabled(False)

        window = MainWindow()
        qtbot.addWidget(window)

        assert not window._auto_save_timer.isActive()
