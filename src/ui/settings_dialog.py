"""
Settings dialog for theme and font customization.
"""

import tempfile

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)

from core.settings import THEMES, SettingsManager

# Models available for code completion
COMPLETION_MODELS = [
    {"id": "deepseek-coder:1.3b", "name": "DeepSeek Coder 1.3B"},
    {"id": "qwen2.5-coder:1.5b", "name": "Qwen 2.5 Coder 1.5B"},
    {"id": "codegemma:2b", "name": "CodeGemma 2B"},
]

# Common font sizes for the dropdown (starting at 10)
FONT_SIZES = [10, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 32, 36, 42, 48, 56, 64, 72]

# Good monospace fonts that work well on Windows
SAFE_MONOSPACE_FONTS = [
    "Consolas",
    "Courier New",
    "Lucida Console",
    "Cascadia Code",
    "Cascadia Mono",
    "Source Code Pro",
    "Fira Code",
    "JetBrains Mono",
    "Monaco",
    "Menlo",
    "DejaVu Sans Mono",
    "Liberation Mono",
    "Ubuntu Mono",
]


def get_available_monospace_fonts() -> list[str]:
    """Get list of available monospace fonts, filtering problematic ones."""
    available = []
    # PyQt6 uses static methods for QFontDatabase
    all_families = QFontDatabase.families()

    # First add safe fonts that are available
    for font_name in SAFE_MONOSPACE_FONTS:
        if font_name in all_families:
            available.append(font_name)

    # Add system fixed font if not already in list
    system_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    system_family = system_font.family()
    if system_family and system_family not in available:
        available.insert(0, system_family)

    # If no fonts found, add Consolas as fallback (common on Windows)
    if not available:
        available = ["Consolas", "Courier New"]

    return available


class SettingsDialog(QDialog):
    """Dialog for application settings."""

    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = SettingsManager()
        self.setWindowTitle("Settings")
        self.setMinimumSize(500, 400)
        self._updating = False  # Prevent recursive updates

        self._setup_ui()
        self._apply_dark_style()
        self._load_settings()

    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Theme group
        theme_group = QGroupBox("Theme")
        theme_layout = QFormLayout(theme_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(self.settings.get_available_themes())
        self.theme_combo.currentTextChanged.connect(self._on_settings_changed)
        theme_layout.addRow("Color theme:", self.theme_combo)

        layout.addWidget(theme_group)

        # Font group
        font_group = QGroupBox("Font")
        font_layout = QFormLayout(font_group)

        # Use regular combo box with filtered font list
        self.font_combo = QComboBox()
        self.font_combo.addItems(get_available_monospace_fonts())
        self.font_combo.currentTextChanged.connect(self._on_settings_changed)
        font_layout.addRow("Font family:", self.font_combo)

        self.size_combo = QComboBox()
        self.size_combo.addItems([str(s) for s in FONT_SIZES])
        self.size_combo.setCurrentText("12")
        self.size_combo.currentTextChanged.connect(self._on_settings_changed)
        font_layout.addRow("Font size:", self.size_combo)

        layout.addWidget(font_group)

        # API Keys group
        api_group = QGroupBox("API Keys")
        api_layout = QFormLayout(api_group)

        self.anthropic_key_edit = QLineEdit()
        self.anthropic_key_edit.setPlaceholderText("Enter your Anthropic API key...")
        self.anthropic_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addRow("Anthropic (Haiku):", self.anthropic_key_edit)

        layout.addWidget(api_group)

        # Auto-Save group
        autosave_group = QGroupBox("Auto-Save")
        autosave_layout = QFormLayout(autosave_group)

        self.autosave_checkbox = QCheckBox("Enable auto-save")
        autosave_layout.addRow(self.autosave_checkbox)

        self.autosave_interval_combo = QComboBox()
        self.autosave_interval_combo.addItems(["10", "15", "30", "60", "120", "300"])
        autosave_layout.addRow("Interval (seconds):", self.autosave_interval_combo)

        layout.addWidget(autosave_group)

        # Code Completion group
        completion_group = QGroupBox("Code Completion")
        completion_layout = QFormLayout(completion_group)

        self.completion_checkbox = QCheckBox("Enable AI code suggestions")
        completion_layout.addRow(self.completion_checkbox)

        self.completion_model_combo = QComboBox()
        for model in COMPLETION_MODELS:
            self.completion_model_combo.addItem(model["name"], model["id"])
        completion_layout.addRow("Model:", self.completion_model_combo)

        self.completion_delay_combo = QComboBox()
        self.completion_delay_combo.addItems(["200", "400", "600", "800", "1000"])
        completion_layout.addRow("Delay (ms):", self.completion_delay_combo)

        self.completion_max_lines_combo = QComboBox()
        self.completion_max_lines_combo.addItems([str(i) for i in range(1, 11)])
        completion_layout.addRow("Max lines:", self.completion_max_lines_combo)

        layout.addWidget(completion_group)

        # Preview
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)

        self.preview_edit = QPlainTextEdit()
        self.preview_edit.setReadOnly(True)
        self.preview_edit.setPlainText(
            "# Sample code preview\n"
            "def hello_world():\n"
            '    """A simple function."""\n'
            '    message = "Hello, World!"\n'
            "    count = 42\n"
            "    print(message)\n"
            "    return True\n"
        )
        self.preview_edit.setMaximumHeight(150)
        preview_layout.addWidget(self.preview_edit)

        layout.addWidget(preview_group)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        button_box.accepted.connect(self._save_and_close)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(
            self._apply_settings
        )

        layout.addWidget(button_box)

    @staticmethod
    def _create_x_icon(color: str) -> str:
        """Create a small X mark icon and return the file path."""
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color))
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(4, 4, 11, 11)
        painter.drawLine(11, 4, 4, 11)
        painter.end()
        path = tempfile.gettempdir() + "/mynotion_check_x.png"
        pixmap.save(path)
        return path.replace("\\", "/")

    @staticmethod
    def _hex_to_rgba(hex_color: str, alpha: float) -> str:
        """Convert hex color to rgba() CSS string."""
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    def _apply_dark_style(self):
        """Apply current theme styling to the dialog."""
        theme = self.settings.get_current_theme()
        bg = theme.background
        fg = theme.foreground
        chrome_bg = theme.chrome_bg
        chrome_border = theme.chrome_border
        accent = theme.keyword
        selection = theme.selection
        radius = theme.radius

        # Win95: explicit per-side beveled borders
        if theme.is_beveled:
            group_border = theme.bevel_flat
            input_border = theme.bevel_sunken
            btn_border = theme.bevel_raised
            check_border = theme.bevel_sunken
        else:
            group_border = f"border: 1px solid {chrome_border};"
            input_border = f"border: 1px solid {chrome_border};"
            btn_border = "border: none;"
            check_border = f"border: 1px solid {chrome_border};"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {chrome_bg};
                color: {fg};
            }}
            QGroupBox {{
                color: {fg};
                {group_border}
                border-radius: {radius};
                margin-top: 8px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            QComboBox {{
                background-color: {bg};
                color: {fg};
                {input_border}
                border-radius: {radius};
                padding: 4px 8px;
                min-height: 20px;
                min-width: 150px;
            }}
            QComboBox:hover {{
                border-color: {accent};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {bg};
                color: {fg};
                selection-background-color: {selection};
                outline: none;
            }}
            QLabel {{
                color: {fg};
            }}
            QLineEdit {{
                background-color: {bg};
                color: {fg};
                {input_border}
                border-radius: {radius};
                padding: 4px 8px;
                min-height: 20px;
            }}
            QLineEdit:hover {{
                border-color: {accent};
            }}
            QLineEdit:focus {{
                border-color: {accent};
            }}
            QPushButton {{
                background-color: {self._hex_to_rgba(accent, 0.8)};
                color: {fg};
                {btn_border}
                border-radius: {radius};
                padding: 6px 16px;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {accent};
            }}
            QPushButton:pressed {{
                background-color: {selection};
            }}
            QDialogButtonBox QPushButton {{
                min-width: 70px;
            }}
            QCheckBox {{
                color: {fg};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                {check_border}
                border-radius: {radius};
                background-color: {bg};
            }}
            QCheckBox::indicator:hover {{
                border-color: {accent};
            }}
            QCheckBox::indicator:checked {{
                background-color: {bg};
                border-color: {accent};
                image: url({self._create_x_icon(accent)});
            }}
        """)

    def _load_settings(self):
        """Load current settings into the dialog."""
        self._updating = True

        # Theme
        current_theme = self.settings.get_current_theme_name()
        index = self.theme_combo.findText(current_theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)

        # Font family
        font_family = self.settings.get_font_family()
        if font_family:
            index = self.font_combo.findText(font_family)
            if index >= 0:
                self.font_combo.setCurrentIndex(index)
            else:
                # Font not in list, use first available
                self.font_combo.setCurrentIndex(0)
        else:
            self.font_combo.setCurrentIndex(0)

        # Font size
        font_size = self.settings.get_font_size()
        if font_size <= 0:
            font_size = 12
        self.size_combo.setCurrentText(str(font_size))

        # API Keys
        self.anthropic_key_edit.setText(self.settings.get_anthropic_api_key())

        # Auto-Save
        self.autosave_checkbox.setChecked(self.settings.get_auto_save_enabled())
        interval = str(self.settings.get_auto_save_interval())
        idx = self.autosave_interval_combo.findText(interval)
        if idx >= 0:
            self.autosave_interval_combo.setCurrentIndex(idx)

        # Code Completion
        self.completion_checkbox.setChecked(self.settings.get_completion_enabled())
        model_id = self.settings.get_completion_model()
        for i in range(self.completion_model_combo.count()):
            if self.completion_model_combo.itemData(i) == model_id:
                self.completion_model_combo.setCurrentIndex(i)
                break
        self.completion_delay_combo.setCurrentText(str(self.settings.get_completion_delay()))
        self.completion_max_lines_combo.setCurrentText(
            str(self.settings.get_completion_max_lines())
        )

        self._updating = False
        self._update_preview()

    def _on_settings_changed(self):
        """Handle any settings change."""
        if not self._updating:
            self._update_preview()

    def _update_preview(self):
        """Update the preview with current settings."""
        theme_name = self.theme_combo.currentText()
        theme = THEMES.get(theme_name, THEMES["Dark (Default)"])

        font_family = self.font_combo.currentText()
        size_text = self.size_combo.currentText()

        # Ensure valid values
        try:
            size = int(size_text) if size_text else 12
        except (ValueError, TypeError):
            size = 12
        if size <= 0:
            size = 12
        if not font_family:
            font_family = "Consolas"

        font = QFont(font_family, size)
        # Ensure font has valid point size
        if font.pointSize() <= 0:
            font.setPointSize(size)
        self.preview_edit.setFont(font)

        preview_border = (
            theme.bevel_sunken if theme.is_beveled else f"border: 1px solid {theme.chrome_border};"
        )
        self.preview_edit.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {theme.background};
                color: {theme.foreground};
                selection-background-color: {theme.selection};
                {preview_border}
                border-radius: {theme.radius};
            }}
        """)

    def _apply_settings(self):
        """Apply settings without closing."""
        self.settings.set_current_theme(self.theme_combo.currentText())
        self.settings.set_font_family(self.font_combo.currentText())

        try:
            size = int(self.size_combo.currentText())
        except (ValueError, TypeError):
            size = 12
        if size <= 0:
            size = 12
        self.settings.set_font_size(size)

        # Save API keys
        self.settings.set_anthropic_api_key(self.anthropic_key_edit.text())

        # Save auto-save settings
        self.settings.set_auto_save_enabled(self.autosave_checkbox.isChecked())
        try:
            interval = int(self.autosave_interval_combo.currentText())
        except (ValueError, TypeError):
            interval = 30
        self.settings.set_auto_save_interval(interval)

        # Save code completion settings
        self.settings.set_completion_enabled(self.completion_checkbox.isChecked())
        model_id = self.completion_model_combo.currentData()
        if model_id:
            self.settings.set_completion_model(model_id)
        try:
            delay = int(self.completion_delay_combo.currentText())
        except (ValueError, TypeError):
            delay = 600
        self.settings.set_completion_delay(delay)
        try:
            max_lines = int(self.completion_max_lines_combo.currentText())
        except (ValueError, TypeError):
            max_lines = 3
        self.settings.set_completion_max_lines(max_lines)

        self.settings_changed.emit()

    def _save_and_close(self):
        """Save settings and close dialog."""
        self._apply_settings()
        self.accept()
