# =============================================================================
# tests/test_auto_save.py — Tests for auto-save functionality
# =============================================================================

import pytest

from core.settings import SettingsManager


@pytest.fixture(autouse=True)
def _clear_session(qapp, isolated_settings):
    """Reset session and auto-save settings before each test."""
    sm = SettingsManager()
    sm.set_session_tabs([])
    sm.set_auto_save_enabled(True)
    sm.set_auto_save_interval(30)


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


class TestAutoSaveSettings:
    """Tests for auto-save settings in SettingsManager."""

    def test_auto_save_enabled_default(self):
        """Auto-save is enabled by default when key is absent."""
        sm = SettingsManager()
        sm.settings.remove("auto_save_enabled")
        assert sm.get_auto_save_enabled() is True

    def test_auto_save_enabled_roundtrip(self):
        """Auto-save enabled flag round-trips."""
        sm = SettingsManager()
        sm.set_auto_save_enabled(False)
        assert sm.get_auto_save_enabled() is False

    def test_auto_save_interval_default(self):
        """Auto-save interval defaults to 30 seconds when key is absent."""
        sm = SettingsManager()
        sm.settings.remove("auto_save_interval")
        assert sm.get_auto_save_interval() == 30

    def test_auto_save_interval_clamped(self):
        """Interval is clamped between 5 and 300 seconds."""
        sm = SettingsManager()
        sm.set_auto_save_interval(1)
        assert sm.get_auto_save_interval() == 5
        sm.set_auto_save_interval(999)
        assert sm.get_auto_save_interval() == 300


class TestAutoSave:
    """Tests for auto-save behavior in MainWindow."""

    def test_auto_save_saves_modified_file(self, main_window, tmp_path):
        """Auto-save writes modified files with a filepath."""
        test_file = tmp_path / "auto.txt"
        test_file.write_text("original", encoding="utf-8")

        main_window._open_file_path(str(test_file))
        editor = main_window.current_editor()

        # Modify the editor content
        editor.setPlainText("modified content")
        editor.document().setModified(True)

        # Trigger auto-save
        main_window._auto_save()

        # File should be updated on disk
        assert test_file.read_text(encoding="utf-8") == "modified content"
        assert not editor.document().isModified()

    def test_auto_save_skips_untitled(self, main_window):
        """Auto-save skips tabs without a filepath."""
        editor = main_window.current_editor()
        # Insert text via cursor to trigger modification state
        cursor = editor.textCursor()
        cursor.insertText("some text")
        assert editor.document().isModified()

        # Should not raise or crash
        main_window._auto_save()

        # Document still marked as modified (was not saved — no filepath)
        assert editor.document().isModified()

    def test_auto_save_skips_unmodified(self, main_window, tmp_path):
        """Auto-save skips tabs that are not modified."""
        test_file = tmp_path / "clean.txt"
        test_file.write_text("original", encoding="utf-8")

        main_window._open_file_path(str(test_file))

        # Not modified — auto-save should be a no-op
        main_window._auto_save()

        assert test_file.read_text(encoding="utf-8") == "original"

    def test_auto_save_timer_active_when_enabled(self, main_window):
        """Timer is active when auto-save is enabled."""
        assert main_window._auto_save_timer.isActive()
        assert main_window._auto_save_timer.interval() == 30000

    def test_auto_save_timer_inactive_when_disabled(self):
        """Timer is inactive when auto-save is disabled."""
        from ui.main_window import MainWindow

        sm = SettingsManager()
        sm.set_auto_save_enabled(False)

        window = MainWindow()

        assert not window._auto_save_timer.isActive()
        _destroy_window(window)
