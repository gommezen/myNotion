# =============================================================================
# tests/test_editor_tab.py — Tests for EditorTab widget
# =============================================================================


class TestEditorTab:
    """Tests for the EditorTab widget."""

    def test_create_editor_tab(self, create_editor_tab, qtbot):
        """Test that EditorTab can be created."""
        tab = create_editor_tab()
        qtbot.addWidget(tab)
        assert tab is not None

    def test_set_content(self, create_editor_tab, qtbot):
        """Test setting text content."""
        tab = create_editor_tab(content="Hello, World!")
        qtbot.addWidget(tab)
        assert tab.toPlainText() == "Hello, World!"

    def test_empty_tab(self, create_editor_tab, qtbot):
        """Test empty tab has no content."""
        tab = create_editor_tab()
        qtbot.addWidget(tab)
        assert tab.toPlainText() == ""

    def test_filepath_initially_none(self, create_editor_tab, qtbot):
        """Test that filepath is None for new tabs."""
        tab = create_editor_tab()
        qtbot.addWidget(tab)
        assert tab.filepath is None

    def test_load_file(self, create_editor_tab, qtbot, tmp_file):
        """Test loading a file into the editor."""
        tab = create_editor_tab()
        qtbot.addWidget(tab)

        tab.load_file(str(tmp_file))

        assert "sample content" in tab.toPlainText()
        assert tab.filepath == str(tmp_file)

    def test_load_python_file_sets_language(self, create_editor_tab, qtbot, tmp_python_file):
        """Test that loading a .py file sets Python language."""
        tab = create_editor_tab()
        qtbot.addWidget(tab)

        tab.load_file(str(tmp_python_file))

        from syntax.highlighter import Language

        assert tab.language == Language.PYTHON

    def test_zoom_in(self, create_editor_tab, qtbot):
        """Test zoom in increases zoom level."""
        tab = create_editor_tab()
        qtbot.addWidget(tab)

        initial_zoom = tab._zoom_level
        tab.zoom_in()

        assert tab._zoom_level == initial_zoom + 1

    def test_zoom_out(self, create_editor_tab, qtbot):
        """Test zoom out decreases zoom level."""
        tab = create_editor_tab()
        qtbot.addWidget(tab)

        initial_zoom = tab._zoom_level
        tab.zoom_out()

        assert tab._zoom_level == initial_zoom - 1


class TestEditorTabSave:
    """Tests for EditorTab save functionality."""

    def test_save_file(self, create_editor_tab, qtbot, tmp_path):
        """Test saving content to a file."""
        tab = create_editor_tab(content="Test content to save")
        qtbot.addWidget(tab)

        save_path = tmp_path / "saved_file.txt"
        tab.save_file(str(save_path))

        assert save_path.exists()
        assert save_path.read_text() == "Test content to save"

    def test_save_updates_filepath(self, create_editor_tab, qtbot, tmp_path):
        """Test that save updates the filepath."""
        tab = create_editor_tab(content="Content")
        qtbot.addWidget(tab)

        save_path = tmp_path / "new_file.txt"
        tab.save_file(str(save_path))

        assert tab.filepath == str(save_path)


class TestEditorTabLanguage:
    """Tests for language detection and setting."""

    def test_set_language(self, create_editor_tab, qtbot):
        """Setting language should update highlighter."""
        from syntax.highlighter import Language

        tab = create_editor_tab()
        qtbot.addWidget(tab)
        tab.set_language(Language.PYTHON)
        assert tab.language == Language.PYTHON

    def test_language_detection_python(self):
        from syntax.highlighter import Language, get_language_from_extension

        assert get_language_from_extension("test.py") == Language.PYTHON
        assert get_language_from_extension("script.pyw") == Language.PYTHON

    def test_language_detection_javascript(self):
        from syntax.highlighter import Language, get_language_from_extension

        assert get_language_from_extension("app.js") == Language.JAVASCRIPT
        assert get_language_from_extension("component.tsx") == Language.JAVASCRIPT

    def test_language_detection_html(self):
        from syntax.highlighter import Language, get_language_from_extension

        assert get_language_from_extension("index.html") == Language.HTML
        assert get_language_from_extension("page.htm") == Language.HTML

    def test_language_detection_css(self):
        from syntax.highlighter import Language, get_language_from_extension

        assert get_language_from_extension("styles.css") == Language.CSS

    def test_language_detection_json(self):
        from syntax.highlighter import Language, get_language_from_extension

        assert get_language_from_extension("config.json") == Language.JSON

    def test_language_detection_markdown(self):
        from syntax.highlighter import Language, get_language_from_extension

        assert get_language_from_extension("README.md") == Language.MARKDOWN

    def test_language_detection_plain(self):
        from syntax.highlighter import Language, get_language_from_extension

        assert get_language_from_extension("file.xyz") == Language.PLAIN
        assert get_language_from_extension("") == Language.PLAIN
