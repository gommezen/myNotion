# =============================================================================
# tests/test_file_browser.py — Tests for FileBrowserPanel
# =============================================================================

from unittest.mock import patch

import pytest

from ui.file_browser import FileBrowserPanel

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def browser(qapp, qtbot):
    """Create a FileBrowserPanel widget."""
    panel = FileBrowserPanel()
    qtbot.addWidget(panel)
    return panel


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestFileBrowserInit:
    """Tests for FileBrowserPanel initialization."""

    def test_creates_successfully(self, browser):
        assert browser is not None

    def test_has_tree_view(self, browser):
        assert browser.tree_view is not None

    def test_has_file_system_model(self, browser):
        assert browser.model is not None

    def test_has_title_label(self, browser):
        assert browser.title_label.text() == "FILES"

    def test_has_open_folder_button(self, browser):
        assert browser.open_folder_btn is not None

    def test_tree_header_hidden(self, browser):
        assert browser.tree_view.isHeaderHidden()

    def test_extra_columns_hidden(self, browser):
        """Columns 1-3 (size, type, date) should be hidden."""
        assert browser.tree_view.isColumnHidden(1)
        assert browser.tree_view.isColumnHidden(2)
        assert browser.tree_view.isColumnHidden(3)


# ---------------------------------------------------------------------------
# set_root_path
# ---------------------------------------------------------------------------


class TestFileBrowserRootPath:
    """Tests for set_root_path."""

    def test_set_root_path_valid(self, browser, tmp_project_dir):
        """Setting a valid path should update the model root."""
        browser.set_root_path(str(tmp_project_dir))

        # Qt normalizes paths to forward slashes on Windows
        root_path = browser.model.rootPath().replace("/", "\\")
        assert str(tmp_project_dir) == root_path

    def test_set_root_path_invalid(self, browser):
        """Setting a nonexistent path should be ignored."""
        old_root = browser.model.rootPath()
        browser.set_root_path("/nonexistent/path/that/does/not/exist")
        assert browser.model.rootPath() == old_root

    def test_set_root_path_updates_tree_root_index(self, browser, tmp_project_dir):
        """Tree view root index should match the model's root index."""
        browser.set_root_path(str(tmp_project_dir))

        expected_index = browser.model.index(browser.model.rootPath())
        actual_index = browser.tree_view.rootIndex()
        # Both should point to the same path
        assert browser.model.filePath(actual_index) == browser.model.filePath(expected_index)


# ---------------------------------------------------------------------------
# open_folder_dialog
# ---------------------------------------------------------------------------


class TestFileBrowserDialog:
    """Tests for folder picker dialog."""

    def test_open_folder_dialog_sets_path(self, browser, tmp_project_dir):
        """Selecting a folder should update the root path."""
        with patch(
            "ui.file_browser.QFileDialog.getExistingDirectory",
            return_value=str(tmp_project_dir),
        ):
            browser.open_folder_dialog()

        # Qt normalizes paths to forward slashes on Windows
        root_path = browser.model.rootPath().replace("/", "\\")
        assert str(tmp_project_dir) == root_path

    def test_open_folder_dialog_cancel(self, browser):
        """Cancelling the dialog should not change root path."""
        old_root = browser.model.rootPath()
        with patch(
            "ui.file_browser.QFileDialog.getExistingDirectory",
            return_value="",
        ):
            browser.open_folder_dialog()

        assert browser.model.rootPath() == old_root


# ---------------------------------------------------------------------------
# Signal emission
# ---------------------------------------------------------------------------


class TestFileBrowserSignals:
    """Tests for file_selected signal."""

    def test_double_click_file_emits_signal(self, browser, tmp_project_dir, qtbot):
        """Double-clicking a file should emit file_selected with the path."""
        browser.set_root_path(str(tmp_project_dir))

        file_path = str(tmp_project_dir / "src" / "main.py")
        index = browser.model.index(file_path)

        # QFileSystemModel indexes asynchronously; use fetchMore to force it
        browser.model.fetchMore(browser.model.index(str(tmp_project_dir / "src")))

        # Verify model resolves the path (normalized to forward slashes)
        resolved = browser.model.filePath(index).replace("/", "\\")
        assert resolved == file_path

        with qtbot.waitSignal(browser.file_selected, timeout=2000) as sig:
            browser._on_item_double_clicked(index)

        assert sig.args[0].replace("/", "\\") == file_path

    def test_double_click_directory_no_signal(self, browser, tmp_project_dir, qtbot):
        """Double-clicking a directory should NOT emit file_selected."""
        browser.set_root_path(str(tmp_project_dir))

        dir_path = str(tmp_project_dir / "src")
        index = browser.model.index(dir_path)

        # Signal should NOT fire — use a flag to track
        signal_fired = []
        browser.file_selected.connect(lambda p: signal_fired.append(p))
        browser._on_item_double_clicked(index)

        assert signal_fired == []


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------


class TestFileBrowserTheme:
    """Tests for theme application."""

    def test_apply_theme_does_not_crash(self, browser):
        """apply_theme should run without errors."""
        browser.apply_theme()

    def test_apply_theme_sets_stylesheet(self, browser):
        """After apply_theme, widget should have a stylesheet."""
        browser.apply_theme()
        assert browser.styleSheet() != ""
