"""
Application settings and theme management.
"""

from dataclasses import dataclass

from PyQt6.QtCore import QSettings


@dataclass
class EditorTheme:
    """Theme colors for the editor."""

    name: str
    background: str
    foreground: str
    line_number_bg: str
    line_number_fg: str
    current_line: str
    selection: str
    # Syntax colors
    keyword: str
    string: str
    comment: str
    number: str
    function: str
    class_name: str
    decorator: str
    # UI chrome colors (optional - derived from background if not set)
    chrome_bg: str = ""
    chrome_hover: str = ""
    chrome_border: str = ""
    # Style variant: "modern" (rounded corners) or "win95" (sharp + beveled)
    style_variant: str = "modern"
    # Win95 bevel edge colors (only used when style_variant == "win95")
    bevel_light: str = ""
    bevel_dark: str = ""

    @property
    def is_beveled(self) -> bool:
        """True when the theme uses Win95-style 3D beveled borders."""
        return self.style_variant == "win95"

    @property
    def radius(self) -> str:
        """Small border-radius: 0px for Win95, 3px for modern."""
        return "0px" if self.is_beveled else "3px"

    @property
    def radius_large(self) -> str:
        """Large border-radius: 0px for Win95, 8px for modern."""
        return "0px" if self.is_beveled else "8px"

    @property
    def bevel_raised(self) -> str:
        """QSS for a Win95-style raised (3D outward) border."""
        return (
            f"border-top: 2px solid {self.bevel_light}; "
            f"border-left: 2px solid {self.bevel_light}; "
            f"border-bottom: 2px solid {self.bevel_dark}; "
            f"border-right: 2px solid {self.bevel_dark};"
        )

    @property
    def bevel_sunken(self) -> str:
        """QSS for a Win95-style sunken (3D inward) border."""
        return (
            f"border-top: 2px solid {self.bevel_dark}; "
            f"border-left: 2px solid {self.bevel_dark}; "
            f"border-bottom: 2px solid {self.bevel_light}; "
            f"border-right: 2px solid {self.bevel_light};"
        )

    @property
    def bevel_flat(self) -> str:
        """QSS for a Win95-style flat (subtle 3D) border for group boxes."""
        return (
            f"border: 1px solid {self.bevel_light}; "
            f"border-top: 1px solid {self.bevel_dark}; "
            f"border-left: 1px solid {self.bevel_dark};"
        )

    def __post_init__(self):
        """Derive chrome colors from background if not explicitly set."""
        if not self.chrome_bg:
            self.chrome_bg = self._lighten(self.background, 15)
        if not self.chrome_hover:
            self.chrome_hover = self._lighten(self.background, 25)
        if not self.chrome_border:
            self.chrome_border = self._lighten(self.background, 20)

    @staticmethod
    def _lighten(hex_color: str, amount: int) -> str:
        """Lighten a hex color by amount (0-255)."""
        hex_color = hex_color.lstrip("#")
        r = min(255, int(hex_color[0:2], 16) + amount)
        g = min(255, int(hex_color[2:4], 16) + amount)
        b = min(255, int(hex_color[4:6], 16) + amount)
        return f"#{r:02X}{g:02X}{b:02X}"

    @staticmethod
    def _darken(hex_color: str, amount: int) -> str:
        """Darken a hex color by amount (0-255)."""
        hex_color = hex_color.lstrip("#")
        r = max(0, int(hex_color[0:2], 16) - amount)
        g = max(0, int(hex_color[2:4], 16) - amount)
        b = max(0, int(hex_color[4:6], 16) - amount)
        return f"#{r:02X}{g:02X}{b:02X}"


# Built-in themes
THEMES: dict[str, EditorTheme] = {
    "Dark (Default)": EditorTheme(
        name="Dark (Default)",
        background="#1E1E1E",
        foreground="#D4D4D4",
        line_number_bg="#252526",
        line_number_fg="#858585",
        current_line="#2D2D30",
        selection="#1A5050",
        keyword="#569CD6",
        string="#CE9178",
        comment="#6A9955",
        number="#B5CEA8",
        function="#DCDCAA",
        class_name="#4EC9B0",
        decorator="#C586C0",
    ),
    "Monokai": EditorTheme(
        name="Monokai",
        background="#272822",
        foreground="#F8F8F2",
        line_number_bg="#272822",
        line_number_fg="#75715E",
        current_line="#3E3D32",
        selection="#1A5050",
        keyword="#F92672",
        string="#E6DB74",
        comment="#75715E",
        number="#AE81FF",
        function="#A6E22E",
        class_name="#66D9EF",
        decorator="#F92672",
    ),
    "Dracula": EditorTheme(
        name="Dracula",
        background="#282A36",
        foreground="#F8F8F2",
        line_number_bg="#282A36",
        line_number_fg="#6272A4",
        current_line="#44475A",
        selection="#1A5050",
        keyword="#FF79C6",
        string="#F1FA8C",
        comment="#6272A4",
        number="#BD93F9",
        function="#50FA7B",
        class_name="#8BE9FD",
        decorator="#FF79C6",
    ),
    "Light": EditorTheme(
        name="Light",
        background="#FFFFFF",
        foreground="#333333",
        line_number_bg="#F5F5F5",
        line_number_fg="#999999",
        current_line="#FFFBDD",
        selection="#1A5050",
        keyword="#0000FF",
        string="#A31515",
        comment="#008000",
        number="#098658",
        function="#795E26",
        class_name="#267F99",
        decorator="#AF00DB",
    ),
    "Nord": EditorTheme(
        name="Nord",
        background="#2E3440",
        foreground="#D8DEE9",
        line_number_bg="#2E3440",
        line_number_fg="#4C566A",
        current_line="#3B4252",
        selection="#1A5050",
        keyword="#81A1C1",
        string="#A3BE8C",
        comment="#616E88",
        number="#B48EAD",
        function="#88C0D0",
        class_name="#8FBCBB",
        decorator="#B48EAD",
    ),
    "Metropolis": EditorTheme(
        name="Metropolis",
        background="#1a2a2a",  # editor bg, active tab (MUST match)
        foreground="#E8E4D9",  # main text color
        line_number_bg="#1a2a2a",  # line number gutter bg (same as editor/active tab)
        line_number_fg="#4a6a6a",  # line number text (dimmer)
        current_line="#1A3333",  # current line highlight
        selection="#1A5050",  # text selection
        keyword="#D4A84B",  # keywords (if, for, def)
        string="#A8D8D0",  # string literals
        comment="#4A8080",  # code comments
        number="#E8C547",  # number literals
        function="#7FBFB5",  # function names
        class_name="#D4A84B",  # class names
        decorator="#C45C5C",  # decorators (@)
        chrome_bg="#121f1f",  # tab bar, status bar bg
        chrome_hover="#10191b",  # tab hover
        chrome_border="#1A3333",  # borders
    ),
    "Win95 Dark": EditorTheme(
        name="Win95 Dark",
        background="#1a2a2a",
        foreground="#c8e0ce",
        line_number_bg="#0a1212",
        line_number_fg="#4a6a5a",
        current_line="#243636",
        selection="#2d4242",
        keyword="#d4a84b",
        string="#a8d8d0",
        comment="#4a8080",
        number="#e8c547",
        function="#7fbfb5",
        class_name="#d4a84b",
        decorator="#a67c35",
        chrome_bg="#0f1a1a",
        chrome_hover="#243636",
        chrome_border="#3a5252",
        style_variant="win95",
        bevel_light="#3a5252",
        bevel_dark="#0a1414",
    ),
}


class SettingsManager:
    """Manages application settings including themes."""

    def __init__(self):
        self.settings = QSettings("MyNotion", "Editor")

    def get_current_theme_name(self) -> str:
        """Get the name of the current theme."""
        return self.settings.value("theme", "Dark (Default)")

    def set_current_theme(self, theme_name: str):
        """Set the current theme by name."""
        if theme_name in THEMES:
            self.settings.setValue("theme", theme_name)

    def get_current_theme(self) -> EditorTheme:
        """Get the current theme object."""
        theme_name = self.get_current_theme_name()
        return THEMES.get(theme_name, THEMES["Dark (Default)"])

    def get_available_themes(self) -> list[str]:
        """Get list of available theme names."""
        return list(THEMES.keys())

    def get_font_family(self) -> str:
        """Get the editor font family."""
        return self.settings.value("font_family", "Consolas")

    def set_font_family(self, family: str):
        """Set the editor font family."""
        self.settings.setValue("font_family", family)

    def get_font_size(self) -> int:
        """Get the editor font size."""
        try:
            size = self.settings.value("font_size", 12)
            if size is None:
                return 12
            size = int(size)
            if size <= 0 or size > 100:
                return 12
            return size
        except (ValueError, TypeError):
            return 12

    def set_font_size(self, size: int):
        """Set the editor font size."""
        size = max(8, min(72, int(size)))
        self.settings.setValue("font_size", size)

    # Side panel settings
    def get_side_panel_visible(self) -> bool:
        """Get side panel visibility state."""
        return self.settings.value("side_panel_visible", True, type=bool)

    def set_side_panel_visible(self, visible: bool):
        """Save side panel visibility state."""
        self.settings.setValue("side_panel_visible", visible)

    def get_layout_mode(self) -> str:
        """Get the current layout mode (coding or writing)."""
        return self.settings.value("layout_mode", "coding")

    def set_layout_mode(self, mode: str):
        """Set the layout mode (coding or writing)."""
        if mode in ("coding", "writing"):
            self.settings.setValue("layout_mode", mode)

    # API Keys
    def get_anthropic_api_key(self) -> str:
        """Get the Anthropic API key for Haiku/Claude models."""
        return self.settings.value("anthropic_api_key", "")

    def set_anthropic_api_key(self, key: str):
        """Set the Anthropic API key."""
        self.settings.setValue("anthropic_api_key", key)

    # Session restore settings
    def get_session_tabs(self) -> list[dict]:
        """Get saved session tab data."""
        value = self.settings.value("session_tabs")
        if value is None:
            return []
        return value

    def set_session_tabs(self, tabs: list[dict]):
        """Save session tab data."""
        self.settings.setValue("session_tabs", tabs)

    def get_session_active_tab(self) -> int:
        """Get the active tab index from last session."""
        return self.settings.value("session_active_tab", 0, type=int)

    def set_session_active_tab(self, index: int):
        """Save the active tab index."""
        self.settings.setValue("session_active_tab", index)

    # Auto-save settings
    def get_auto_save_enabled(self) -> bool:
        """Get whether auto-save is enabled."""
        return self.settings.value("auto_save_enabled", True, type=bool)

    def set_auto_save_enabled(self, enabled: bool):
        """Set whether auto-save is enabled."""
        self.settings.setValue("auto_save_enabled", enabled)

    def get_auto_save_interval(self) -> int:
        """Get auto-save interval in seconds."""
        try:
            interval = self.settings.value("auto_save_interval", 30, type=int)
            return max(5, min(300, interval))
        except (ValueError, TypeError):
            return 30

    def set_auto_save_interval(self, seconds: int):
        """Set auto-save interval in seconds."""
        self.settings.setValue("auto_save_interval", max(5, min(300, seconds)))

    # Code completion settings
    def get_completion_enabled(self) -> bool:
        """Get whether AI code completion is enabled."""
        return self.settings.value("completion_enabled", False, type=bool)

    def set_completion_enabled(self, enabled: bool):
        """Set whether AI code completion is enabled."""
        self.settings.setValue("completion_enabled", enabled)

    def get_completion_model(self) -> str:
        """Get the model used for code completion."""
        return self.settings.value("completion_model", "deepseek-coder:1.3b")

    def set_completion_model(self, model: str):
        """Set the model used for code completion."""
        self.settings.setValue("completion_model", model)

    def get_completion_delay(self) -> int:
        """Get completion trigger delay in milliseconds."""
        try:
            delay = self.settings.value("completion_delay", 600, type=int)
            return max(200, min(1000, delay))
        except (ValueError, TypeError):
            return 600

    def set_completion_delay(self, delay: int):
        """Set completion trigger delay in milliseconds."""
        self.settings.setValue("completion_delay", max(200, min(1000, delay)))

    def get_completion_max_lines(self) -> int:
        """Get maximum lines for completion suggestions."""
        try:
            lines = self.settings.value("completion_max_lines", 3, type=int)
            return max(1, min(10, lines))
        except (ValueError, TypeError):
            return 3

    def set_completion_max_lines(self, lines: int):
        """Set maximum lines for completion suggestions."""
        self.settings.setValue("completion_max_lines", max(1, min(10, lines)))
