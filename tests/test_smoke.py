"""
Smoke tests - verify basic imports and instantiation work.

These tests catch runtime errors that static analysis misses:
- Wrong import modules (e.g., QFileSystemModel from wrong PyQt6 submodule)
- Undefined attributes (e.g., referencing renamed variables)
- Missing dependencies
"""


class TestImports:
    """Verify all modules can be imported without errors."""

    def test_import_main_window(self):
        """Import MainWindow - catches import errors in UI module chain."""
        from ui.main_window import MainWindow

        assert MainWindow is not None

    def test_import_activity_bar(self):
        """Import ActivityBar."""
        from ui.activity_bar import ActivityBar

        assert ActivityBar is not None

    def test_import_file_browser(self):
        """Import FileBrowserPanel."""
        from ui.file_browser import FileBrowserPanel

        assert FileBrowserPanel is not None

    def test_import_side_panel(self):
        """Import SidePanel."""
        from ui.side_panel import SidePanel

        assert SidePanel is not None

    def test_import_editor_tab(self):
        """Import EditorTab."""
        from ui.editor_tab import EditorTab

        assert EditorTab is not None

    def test_import_ai_modules(self):
        """Import AI-related modules."""
        from ai.worker import AIManager

        assert AIManager is not None


class TestInstantiation:
    """Verify main components can be instantiated."""

    def test_main_window_creates(self, qtbot):
        """MainWindow instantiates without error - catches attribute errors."""
        from ui.main_window import MainWindow

        window = MainWindow()
        qtbot.addWidget(window)

        # Basic sanity checks
        assert window.tab_widget is not None
        assert window.side_panel is not None
        assert window.activity_bar is not None
        assert window.file_browser is not None

    def test_activity_bar_creates(self, qtbot):
        """ActivityBar instantiates and has expected buttons."""
        from ui.activity_bar import ActivityBar

        bar = ActivityBar()
        qtbot.addWidget(bar)

        assert bar.ai_btn is not None
        assert bar.files_btn is not None

    def test_file_browser_creates(self, qtbot):
        """FileBrowserPanel instantiates with tree view."""
        from ui.file_browser import FileBrowserPanel

        browser = FileBrowserPanel()
        qtbot.addWidget(browser)

        assert browser.tree_view is not None
        assert browser.model is not None
