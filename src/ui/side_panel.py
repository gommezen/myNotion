"""
AI Chat Panel with Metropolis Art Deco design.
Based on ai-panel-redesign-v2_1.jsx — exact 1:1 implementation.
"""

import html
import re
import textwrap
from enum import Enum

from PyQt6.QtCore import QEvent, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ai.worker import AIManager
from core.settings import SettingsManager
from ui.theme_engine import hex_to_rgba


class LayoutMode(Enum):
    """Layout modes for the side panel AI prompts."""

    CODING = "coding"
    WRITING = "writing"


# ─── Data ───
MODELS = [
    {"id": "qwen2.5:7b-instruct-q4_0", "name": "Qwen 2.5", "tag": "7B"},
    {"id": "deepseek-coder:1.3b", "name": "DeepSeek Coder", "tag": "1.3B"},
    {"id": "llama3.2:latest", "name": "Llama 3.2", "tag": "3B"},
    {"id": "gemma3:4b", "name": "Gemma 3", "tag": "4B"},
    {"id": "mistral:7b-instruct-q4_0", "name": "Mistral", "tag": "7B"},
    {"id": "llama3.1:8b-instruct-q4_0", "name": "Llama 3.1", "tag": "8B Q4"},
    {"id": "llama3.1:8b-instruct-q8_0", "name": "Llama 3.1", "tag": "8B Q8"},
    {"id": "claude-haiku", "name": "Claude 3", "tag": "Haiku", "provider": "anthropic"},
]

# ─── Default Models by Mode ───
# Set default model when switching layout modes
# Edit these to match your installed Ollama models
DEFAULT_MODE_MODELS = {
    "coding": "qwen2.5:7b-instruct-q4_0",  # Good for code tasks
    "writing": "qwen2.5:7b-instruct-q4_0",  # Good for prose tasks (use larger model)
}

# ─── Auto-Model Routing ───
# Maps prompt labels to preferred models for automatic selection
# Edit model_id values to match your installed Ollama models
MODEL_ROUTING = {
    # Quick tasks → lightweight model (fast responses)
    "quick": {
        "model_id": "llama3.2:latest",
        "prompts": [
            "Explain",
            "Docstring",
            "Summarize",
            "Examples",
            "Transfer",
            "Expand",
            "Shorten",
        ],
    },
    # Deep review → heavier model (thorough analysis)
    "deep": {
        "model_id": "qwen2.5:7b-instruct-q4_0",
        "prompts": ["Debug", "Fix", "Improve", "Refactor", "Test", "Translate", "Tone"],
    },
}

# AI prompts (card-style layout)
# Special actions: "transfer", "examples", "custom" have action handlers instead of prompts
# Each prompt has a "modes" field: ["coding"], ["writing"], or ["coding", "writing"] for shared
AI_PROMPTS: list[dict[str, str | list[str] | None]] = [
    # Coding-only prompts
    {
        "label": "Explain",
        "prompt": "Explain this code in 2-3 sentences. What does it do and why?",
        "tip": "Describe what the code does",
        "modes": ["coding"],
    },
    {
        "label": "Docstring",
        "prompt": "Add docstrings to all functions and classes. Do not add, remove, or modify any code. Return only the original code with docstrings inserted.",
        "tip": "Add documentation to functions/classes",
        "modes": ["coding"],
    },
    {
        "label": "Debug",
        "prompt": "List bugs or issues in this code. Format: `line N: issue`. Be concise.",
        "tip": "Find bugs and issues",
        "modes": ["coding"],
    },
    {
        "label": "Fix",
        "prompt": "Fix all errors. Return only the corrected code, no explanation.",
        "tip": "Correct errors in code",
        "modes": ["coding"],
    },
    {
        "label": "Refactor",
        "prompt": "Refactor for clarity and maintainability. Return only the code.",
        "tip": "Clean up without changing behavior",
        "modes": ["coding"],
    },
    {
        "label": "Test",
        "prompt": "Generate unit tests using pytest. Return only the test code.",
        "tip": "Generate unit tests",
        "modes": ["coding"],
    },
    # Writing-only prompts
    {
        "label": "Summarize",
        "prompt": "Summarize in 2-3 sentences. One sentence per line.",
        "tip": "Brief overview",
        "modes": ["writing"],
    },
    {
        "label": "Improve",
        "prompt": "Improve clarity and grammar. Keep same length and structure. Return only the text.",
        "tip": "Enhance readability",
        "modes": ["writing"],
    },
    {
        "label": "Translate",
        "prompt": None,
        "action": "translate",
        "tip": "Convert to another language",
        "modes": ["writing"],
    },
    {
        "label": "Expand",
        "prompt": "Expand with more detail and examples. ~2x length. Return only the text.",
        "tip": "Add depth and detail",
        "modes": ["writing"],
    },
    {
        "label": "Tone",
        "prompt": None,
        "action": "tone",
        "tip": "Change writing style",
        "modes": ["writing"],
    },
    {
        "label": "Shorten",
        "prompt": "Cut to ~50% length. Keep essential points only. Return only the text.",
        "tip": "Make concise",
        "modes": ["writing"],
    },
    # Shared prompts (appear in both modes)
    {
        "label": "Custom",
        "prompt": None,
        "action": "custom",
        "tip": "Your own instruction",
        "modes": ["coding", "writing"],
    },
    {
        "label": "Examples",
        "prompt": None,
        "action": "examples",
        "tip": "More variations",
        "modes": ["coding", "writing"],
    },
    {
        "label": "Transfer",
        "prompt": None,
        "action": "transfer",
        "tip": "Insert into editor",
        "modes": ["coding", "writing"],
    },
]


class SidePanel(QWidget):
    """AI Chat Panel with Metropolis Art Deco aesthetic."""

    message_sent = pyqtSignal(str, str, str)  # message, model_id, context_mode
    quick_action_triggered = pyqtSignal(str)  # prompt - requests context from main window
    settings_requested = pyqtSignal()
    collapse_requested = pyqtSignal()
    transfer_to_editor_requested = pyqtSignal(str)  # code content
    new_tab_with_code_requested = pyqtSignal(str, str)  # code content, language
    context_requested = pyqtSignal(str)  # prompt - emitted when AI prompt needs editor context
    chat_context_requested = pyqtSignal(str)  # message - emitted when chat needs editor context
    replace_selection_requested = pyqtSignal(str)  # new code - replaces selected text in editor
    layout_mode_changed = pyqtSignal(str)  # emitted when layout mode changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_manager = SettingsManager()
        self.current_model = MODELS[0]
        self.context_mode = "selection"
        self._current_ai_response = ""  # Buffer for streaming response
        self._chat_html_before_response = ""  # HTML state before AI response
        self._code_blocks: list[tuple[str, str]] = []  # [(code, language), ...]
        self._has_selection_to_replace = False  # True when AI response can replace editor selection
        self._manual_model_selection = False  # True when user manually picks a model
        self._layout_mode = LayoutMode.CODING  # Default to coding mode
        self._setup_ui()
        self._apply_theme()
        self._setup_ai()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ─── AI Assistant title bar ───
        self.title_bar = QWidget()
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(6, 3, 6, 3)
        title_layout.setSpacing(0)

        self.title_label = QLabel("AI Assistant")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        self.collapse_btn = QToolButton()
        self.collapse_btn.setText("\u2212")  # minus sign
        self.collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.collapse_btn.setFixedSize(20, 20)
        self.collapse_btn.clicked.connect(self.collapse_requested.emit)
        title_layout.addWidget(self.collapse_btn)

        layout.addWidget(self.title_bar)

        # ─── Chat area ───
        self.chat_container = QWidget()
        chat_container_layout = QVBoxLayout(self.chat_container)
        chat_container_layout.setContentsMargins(6, 4, 6, 6)
        chat_container_layout.setSpacing(0)

        self.chat_area = QTextBrowser()
        self.chat_area.setFrameShape(QFrame.Shape.NoFrame)
        self.chat_area.setOpenExternalLinks(False)  # Handle links ourselves
        self.chat_area.anchorClicked.connect(self._on_anchor_clicked)
        self.chat_area.setPlaceholderText("Start a conversation...")
        chat_container_layout.addWidget(self.chat_area)

        layout.addWidget(self.chat_container, stretch=1)

        # ─── AI Prompts section (collapsible) ───
        prompts_section = QWidget()
        prompts_layout = QVBoxLayout(prompts_section)
        prompts_layout.setContentsMargins(6, 2, 6, 4)
        prompts_layout.setSpacing(4)

        # Section label
        self.prompts_label = QLabel("AI Prompts")
        prompts_layout.addWidget(self.prompts_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # Prompts grid container (3 columns, flat text chips)
        self.prompts_container = QWidget()
        self._prompts_grid_layout = QGridLayout(self.prompts_container)
        self._prompts_grid_layout.setContentsMargins(0, 4, 0, 0)
        self._prompts_grid_layout.setSpacing(2)

        # Build prompts for the current mode
        self.prompt_buttons: list[QPushButton] = []
        self._rebuild_prompts_grid()

        prompts_layout.addWidget(self.prompts_container)
        layout.addWidget(prompts_section)

        # ─── Input area ───
        input_section = QWidget()
        input_layout = QVBoxLayout(input_section)
        input_layout.setContentsMargins(6, 0, 6, 10)
        input_layout.setSpacing(5)

        # Model selector row
        model_row = QHBoxLayout()
        model_row.setSpacing(5)

        self.model_btn = QToolButton()
        self.model_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._update_model_button()

        model_menu = QMenu(self)
        for model in MODELS:
            action = model_menu.addAction(f"{model['name']}  {model['tag']}")
            action.triggered.connect(lambda checked, m=model: self._set_model(m))
        self.model_btn.setMenu(model_menu)
        model_row.addWidget(self.model_btn)

        model_row.addStretch()

        # Context inclusion state (used by options menu)
        self._include_context = True  # Default: include context
        self._research_mode = False  # When enabled, uses Haiku for research

        input_layout.addLayout(model_row)

        # Input container with text area and buttons (matches design mockup)
        input_row_widget = QWidget()
        input_container = QVBoxLayout(input_row_widget)
        input_container.setContentsMargins(10, 8, 10, 8)
        input_container.setSpacing(4)

        # Multi-line text input area
        self.input_field = QPlainTextEdit()
        self.input_field.setPlaceholderText("Ask anything...")
        self.input_field.setFixedHeight(50)  # Room for ~2 lines
        self.input_field.installEventFilter(self)
        input_container.addWidget(self.input_field)

        # Bottom row: + button on left, send/stop on right
        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(6)

        # Options button with popup menu (+ button)
        self.options_btn = QPushButton("+")
        self.options_btn.setFixedSize(24, 24)
        self.options_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.options_btn.setToolTip("Options")
        self.options_btn.clicked.connect(self._show_options_menu)
        button_row.addWidget(self.options_btn)

        button_row.addStretch()  # Push send button to right

        self.send_btn = QPushButton("Send")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.clicked.connect(self._send_message)
        button_row.addWidget(self.send_btn)

        # Stop button (hidden by default, shown during generation)
        self.stop_btn = QPushButton("■")
        self.stop_btn.setFixedSize(24, 24)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setToolTip("Stop generating")
        self.stop_btn.clicked.connect(self._stop_generation)
        self.stop_btn.hide()
        button_row.addWidget(self.stop_btn)

        input_container.addLayout(button_row)
        input_layout.addWidget(input_row_widget)
        self.input_row_widget = input_row_widget  # Store for styling
        layout.addWidget(input_section)

    def _update_model_button(self):
        m = self.current_model
        self.model_btn.setText(f"{m['name']} {m['tag']} ▾")

    def eventFilter(self, obj, event):
        """Handle focus events on the input field to show gold border."""
        if obj == self.input_field:
            if event.type() == QEvent.Type.FocusIn:
                self._set_input_focus_border(True)
            elif event.type() == QEvent.Type.FocusOut:
                self._set_input_focus_border(False)
        return super().eventFilter(obj, event)

    def _set_input_focus_border(self, focused: bool):
        """Update input container border based on focus state."""
        theme = self.settings_manager.get_current_theme()
        fg = theme.foreground
        if theme.is_beveled:
            input_well_bg = theme._darken(theme.chrome_bg, 8)
            self.input_row_widget.setStyleSheet(f"""
                QWidget {{
                    background: {input_well_bg};
                    {theme.bevel_sunken}
                    border-radius: 0px;
                }}
            """)
        elif focused:
            self.input_row_widget.setStyleSheet(f"""
                QWidget {{
                    background: {hex_to_rgba(fg, 0.02)};
                    border: 1px solid {theme.keyword};
                    border-radius: 6px;
                }}
            """)
        else:
            self.input_row_widget.setStyleSheet(f"""
                QWidget {{
                    background: {hex_to_rgba(fg, 0.02)};
                    border: 1px solid {theme.chrome_border};
                    border-radius: 6px;
                }}
            """)

    def _set_model(self, model: dict, manual: bool = True):
        """Set the current model. manual=True when user explicitly selects."""
        self.current_model = model
        if manual:
            self._manual_model_selection = True
        self._update_model_button()

    def _get_routed_model(self, prompt_label: str) -> dict | None:
        """Get the auto-routed model for a prompt label, or None if not found."""
        for category in MODEL_ROUTING.values():
            if prompt_label in category["prompts"]:
                model_id = category["model_id"]
                # Find the model dict by ID
                for model in MODELS:
                    if model["id"] == model_id:
                        return model
        return None

    def _set_context(self, mode: str):
        self.context_mode = mode

    def set_layout_mode(self, mode: LayoutMode):
        """Set the layout mode and rebuild the prompts grid.

        Args:
            mode: LayoutMode.CODING or LayoutMode.WRITING
        """
        if self._layout_mode != mode:
            self._layout_mode = mode
            self._rebuild_prompts_grid()
            # Switch to default model for this mode (unless user manually selected)
            if not self._manual_model_selection:
                self._set_default_model_for_mode(mode)
            self.layout_mode_changed.emit(mode.value)

    def _set_default_model_for_mode(self, mode: LayoutMode):
        """Set the default model for the given layout mode."""
        model_id = DEFAULT_MODE_MODELS.get(mode.value)
        if model_id:
            for model in MODELS:
                if model["id"] == model_id:
                    self._set_model(model, manual=False)
                    break

    def get_layout_mode(self) -> LayoutMode:
        """Get the current layout mode."""
        return self._layout_mode

    def _rebuild_prompts_grid(self):
        """Rebuild the prompts grid based on current layout mode."""
        # Clear existing buttons
        for btn in self.prompt_buttons:
            btn.deleteLater()
        self.prompt_buttons.clear()

        # Clear the grid layout
        while self._prompts_grid_layout.count():
            item = self._prompts_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Filter prompts for the current mode
        mode_value = self._layout_mode.value
        filtered_prompts = [
            p for p in AI_PROMPTS if mode_value in (p.get("modes") or ["coding", "writing"])
        ]

        # Create buttons for filtered prompts
        for i, prompt in enumerate(filtered_prompts):
            label = prompt["label"]
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(prompt.get("tip", ""))
            btn.clicked.connect(lambda checked, p=prompt: self._on_prompt_click(p))
            self.prompt_buttons.append(btn)
            row, col = i // 3, i % 3  # 3 columns
            self._prompts_grid_layout.addWidget(btn, row, col)

        # Re-apply theme to new buttons
        self._apply_prompt_button_styles()

    def _on_prompt_click(self, prompt: dict):
        # Handle special actions (e.g., Transfer, Examples, Custom, Translate, Tone)
        action = prompt.get("action")
        if action == "transfer":
            self._transfer_to_editor()
            return
        if action == "examples":
            self._generate_more_examples()
            return
        if action == "custom":
            self._show_custom_prompt_dialog()
            return
        if action == "translate":
            self._show_translate_dialog()
            return
        if action == "tone":
            self._show_tone_dialog()
            return

        # Auto-route model based on prompt type (unless user manually selected)
        if not self._manual_model_selection:
            routed_model = self._get_routed_model(prompt["label"])
            if routed_model:
                self._set_model(routed_model, manual=False)

        # Request context from main window - it will call execute_prompt_with_context
        self.context_requested.emit(prompt["prompt"])

    def _generate_more_examples(self):
        """Generate more examples based on code/text in the last AI response."""
        if not self._current_ai_response:
            self.append_message("system", "[No AI response to generate examples from]")
            return

        code = self._extract_code_blocks(self._current_ai_response)
        if code:
            prompt = (
                f"Here is some code:\n\n```\n{code}\n```\n\n"
                f"Please give me 2-3 more examples or variations of this code. "
                f"Show different approaches or use cases."
            )
            self.append_message("user", "[More examples...]")
            self._start_ai_generation(prompt)
        elif self._layout_mode == LayoutMode.WRITING:
            # Writing mode: generate alternative versions of the text
            prompt = (
                f"Here is the original text:\n\n{self._current_ai_response}\n\n"
                f"Write 2-3 alternative versions with different wording or structure. "
                f"Separate each version with a blank line. Return only the alternatives."
            )
            self.append_message("user", "[Alternative versions...]")
            self._start_ai_generation(prompt)
        else:
            # Coding mode with no code blocks — generic examples
            prompt = (
                f"Based on this:\n\n{self._current_ai_response}\n\n"
                f"Please give me 2-3 more code examples or variations."
            )
            self.append_message("user", "[More examples...]")
            self._start_ai_generation(prompt)

    def _show_custom_prompt_dialog(self):
        """Show dialog for entering a custom prompt."""
        text, ok = QInputDialog.getText(
            self,
            "Custom Prompt",
            "Enter your prompt for the selected code/text:",
            QLineEdit.EchoMode.Normal,
            "",
        )
        if ok and text.strip():
            user_instruction = text.strip()
            # Wrap with action-oriented instructions so AI modifies code/text
            if self._layout_mode == LayoutMode.CODING:
                prompt = f"{user_instruction}\n\nReturn only the modified code, no explanation."
            else:
                prompt = f"{user_instruction}\n\nReturn only the modified text, no explanation."
            # Request context from main window - it will call execute_prompt_with_context
            self.context_requested.emit(prompt)

    def _show_translate_dialog(self):
        """Show dialog for selecting target language for translation."""
        languages = [
            "Spanish",
            "French",
            "German",
            "Italian",
            "Portuguese",
            "Chinese",
            "Japanese",
            "Korean",
            "Russian",
            "Arabic",
            "Hindi",
            "Dutch",
            "Polish",
            "Swedish",
            "Other...",
        ]
        language, ok = QInputDialog.getItem(
            self,
            "Translate",
            "Select target language:",
            languages,
            0,
            False,
        )
        if ok and language:
            if language == "Other...":
                language, ok = QInputDialog.getText(
                    self,
                    "Translate",
                    "Enter target language:",
                    QLineEdit.EchoMode.Normal,
                    "",
                )
                if not ok or not language.strip():
                    return
                language = language.strip()
            prompt = f"Translate to {language}. Preserve formatting. Return only the translation."
            self.context_requested.emit(prompt)

    def _show_tone_dialog(self):
        """Show dialog for selecting tone adjustment."""
        tones = [
            "Professional",
            "Casual",
            "Friendly",
            "Formal",
            "Academic",
            "Persuasive",
            "Humorous",
            "Empathetic",
            "Concise",
            "Other...",
        ]
        tone, ok = QInputDialog.getItem(
            self,
            "Adjust Tone",
            "Select desired tone:",
            tones,
            0,
            False,
        )
        if ok and tone:
            if tone == "Other...":
                tone, ok = QInputDialog.getText(
                    self,
                    "Adjust Tone",
                    "Describe the desired tone:",
                    QLineEdit.EchoMode.Normal,
                    "",
                )
                if not ok or not tone.strip():
                    return
                tone = tone.strip()
            prompt = f"Rewrite in a {tone.lower()} tone. Preserve structure. Return only the text."
            self.context_requested.emit(prompt)

    def _transfer_to_editor(self):
        """Extract content from last AI response and emit signal to insert in editor.

        In coding mode: extracts code blocks.
        In writing mode: uses full response text if no code blocks found.
        """
        if not self._current_ai_response:
            self.append_message("system", "[No AI response to transfer]")
            return

        code = self._extract_code_blocks(self._current_ai_response)
        if code:
            self.transfer_to_editor_requested.emit(code)
            self.append_message("system", "[Code transferred to editor]")
        elif self._layout_mode == LayoutMode.WRITING:
            # In writing mode, transfer the full response text (wrapped)
            wrapped = self._wrap_text_for_editor(self._current_ai_response)
            self.transfer_to_editor_requested.emit(wrapped)
            self.append_message("system", "[Text transferred to editor]")
        else:
            self.append_message("system", "[No code blocks found in response]")

    def _extract_code_blocks(self, text: str) -> str:
        """Extract raw code from markdown code blocks in AI response."""
        # Pattern matches ```language\ncode\n``` blocks (handles \r\n and \n)
        # Also handles optional language identifier
        pattern = r"```\w*\r?\n(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            # Join all code blocks with newlines
            return "\n\n".join(block.strip() for block in matches)

        # Fallback: try pattern with optional whitespace/newline after language
        # This handles cases like ```python print("hi")``` (space instead of newline)
        pattern_alt = r"```\w*[\s\r\n]+(.*?)```"
        matches = re.findall(pattern_alt, text, re.DOTALL)
        if matches:
            return "\n\n".join(block.strip() for block in matches if block.strip())

        return ""

    def _wrap_text_for_editor(self, text: str, width: int = 60) -> str:
        """Wrap long AI response text into lines suitable for the editor.

        Preserves paragraph breaks, code-like lines, and list items.
        Only wraps plain prose lines that exceed the width limit.
        """
        # Strip markdown code block fences if present
        text = re.sub(r"```\w*\r?\n?", "", text)

        paragraphs = text.split("\n\n")
        wrapped = []
        for para in paragraphs:
            lines = para.split("\n")
            out_lines = []
            for line in lines:
                # Skip wrapping for lines that look like code, lists, or headings
                if line.startswith(("  ", "\t", "- ", "* ", "| ", "#", ">", "```")):
                    out_lines.append(line)
                elif len(line) > width:
                    out_lines.append(textwrap.fill(line, width=width))
                else:
                    out_lines.append(line)
            wrapped.append("\n".join(out_lines))
        return "\n\n".join(wrapped)

    def _on_anchor_clicked(self, url: QUrl):
        """Handle clicks on links in the chat area."""
        url_str = url.toString()

        # Handle code block actions (code:action:index format)
        if url_str.startswith("code:"):
            parts = url_str.split(":")
            if len(parts) >= 3:
                action = parts[1]
                try:
                    index = int(parts[2])
                    if 0 <= index < len(self._code_blocks):
                        code, language = self._code_blocks[index]
                        self._handle_code_action(action, code, language)
                except (ValueError, IndexError):
                    pass
            return

        # Handle action links (action:name format)
        if url_str.startswith("action:"):
            action = url_str.split(":")[1]
            if action == "continue":
                self._continue_generation()
            elif action == "clear":
                self._clear_chat()
            elif action == "copy_text":
                self._handle_text_action("copy")
            elif action == "insert_text":
                self._handle_text_action("insert")
            elif action == "newtab_text":
                self._handle_text_action("newtab")
            elif action == "replace_text":
                self._handle_text_action("replace")
            return

        # Handle external URLs (http/https)
        if url_str.startswith(("http://", "https://")):
            QDesktopServices.openUrl(url)

    def _handle_code_action(self, action: str, code: str, language: str):
        """Handle code block action (copy, insert, newtab, replace)."""
        if action == "copy":
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(code)
                self.append_message("system", "[Code copied to clipboard]")
        elif action == "insert":
            self.transfer_to_editor_requested.emit(code)
            self.append_message("system", "[Code inserted at cursor]")
        elif action == "newtab":
            self.new_tab_with_code_requested.emit(code, language)
            self.append_message("system", "[Code opened in new tab]")
        elif action == "replace":
            self.replace_selection_requested.emit(code)
            self.append_message("system", "[Selection replaced with new code]")
            # Clear the flag after replacement
            self._has_selection_to_replace = False

    def _handle_text_action(self, action: str):
        """Handle text action for writing mode responses (copy, insert, newtab, replace)."""
        if not self._current_ai_response:
            self.append_message("system", "[No text to transfer]")
            return

        text = self._current_ai_response
        wrapped = self._wrap_text_for_editor(text)
        if action == "copy":
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(wrapped)
                self.append_message("system", "[Text copied to clipboard]")
        elif action == "insert":
            self.transfer_to_editor_requested.emit(wrapped)
            self.append_message("system", "[Text inserted at cursor]")
        elif action == "newtab":
            self.new_tab_with_code_requested.emit(wrapped, "text")
            self.append_message("system", "[Text opened in new tab]")
        elif action == "replace":
            self.replace_selection_requested.emit(wrapped)
            self.append_message("system", "[Selection replaced with new text]")
            self._has_selection_to_replace = False

    def _continue_generation(self):
        """Continue generating from the last AI response."""
        if self._current_ai_response:
            # Include previous response as context so AI knows what to continue
            prompt = (
                f"Here is what you wrote previously:\n\n"
                f"{self._current_ai_response}\n\n"
                f"Please continue from where you left off. Add more content, examples, or details."
            )
            self.append_message("user", "[Continue...]")
            self._start_ai_generation(prompt)

    def _clear_chat(self):
        """Clear the chat area and reset response state."""
        self.chat_area.clear()
        self._current_ai_response = ""
        self._chat_html_before_response = ""
        self._code_blocks = []

    def execute_prompt_with_context(
        self, prompt: str, context: str | None, is_selection: bool = False
    ):
        """Execute an AI prompt with editor context.

        Called by main window after context_requested signal is emitted.

        Args:
            prompt: The prompt template (e.g., "Explain this code")
            context: Selected text or file content from editor, or None
            is_selection: True if context is selected text (enables Replace action)
        """
        # Track if we can offer "Replace" action for code blocks
        self._has_selection_to_replace = is_selection and bool(context)

        # Show prompt in chat
        self.append_message("user", prompt)

        if context:
            # Combine prompt with context
            full_prompt = f"{prompt}:\n\n```\n{context}\n```"
        else:
            # No context available - just use the prompt
            full_prompt = prompt
            self.append_message("system", "[No text selected - using prompt only]")

        self._start_ai_generation(full_prompt)

    def _show_options_menu(self):
        """Show the options popup menu above the + button."""
        menu = QMenu(self)
        menu.setStyleSheet(self._get_options_menu_style())

        # Active Tab toggle - use bullet for active state
        if self._include_context:
            context_action = menu.addAction("● 📄 Active Tab")
        else:
            context_action = menu.addAction("○ 📄 Active Tab")
        context_action.triggered.connect(
            lambda: self._toggle_context_inclusion(not self._include_context)
        )

        # Add to project submenu
        project_menu = menu.addMenu("○ 📁 Add to project")
        project_menu.setStyleSheet(self._get_options_menu_style())
        active_tab_action = project_menu.addAction("Active tab only")
        active_tab_action.triggered.connect(lambda: self._add_to_project_folder("active"))
        all_tabs_action = project_menu.addAction("All open tabs")
        all_tabs_action.triggered.connect(lambda: self._add_to_project_folder("all"))

        menu.addSeparator()

        # Research option - switches to Haiku model
        if self._research_mode:
            research_action = menu.addAction("● 🔍 Research")
        else:
            research_action = menu.addAction("○ 🔍 Research")
        research_action.triggered.connect(self._toggle_research_mode)

        # Show menu above the button
        pos = self.options_btn.mapToGlobal(self.options_btn.rect().topLeft())
        menu_height = menu.sizeHint().height()
        pos.setY(pos.y() - menu_height)
        menu.popup(pos)

    def _toggle_context_inclusion(self, checked: bool):
        """Toggle whether to include active tab content as context."""
        self._include_context = checked
        # Update the options button to indicate context state
        self._update_options_button_state()

    def _toggle_research_mode(self):
        """Toggle research mode - switches to Haiku model for web research."""
        self._research_mode = not self._research_mode
        if self._research_mode:
            # Find and set Haiku model
            for model in MODELS:
                if "haiku" in model["id"].lower():
                    self._set_model(model, manual=False)
                    self.append_message("system", "[Research mode: Using Claude 3 Haiku]")
                    break
        self._update_options_button_state()

    def _add_to_project_folder(self, mode: str = "active"):
        """Open folder picker to add content to a project folder.

        Args:
            mode: "active" for current tab only, "all" for all open tabs
        """
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Project Folder",
            "",
            QFileDialog.Option.ShowDirsOnly,
        )
        if folder:
            if mode == "all":
                self.append_message("system", f"[Adding all tabs to: {folder}]")
            else:
                self.append_message("system", f"[Adding active tab to: {folder}]")
            # TODO: Implement actual file saving logic here

    def _send_message(self):
        text = self.input_field.toPlainText().strip()
        if text:
            self.append_message("user", text)
            self.message_sent.emit(text, self.current_model["id"], self.context_mode)
            self.input_field.clear()
            # Request context from editor if toggle is enabled
            if self._include_context:
                self.chat_context_requested.emit(text)
            else:
                # Send without context
                self._start_ai_generation(text)

    def execute_chat_with_context(self, message: str, context: str | None):
        """Execute a chat message with editor context.

        Called by main window after chat_context_requested signal is emitted.

        Args:
            message: The user's chat message
            context: Text content from the active editor, or None
        """
        if context:
            # Include editor content as context
            full_prompt = f"The user is working on this text:\n\n```\n{context}\n```\n\nUser question: {message}"
        else:
            full_prompt = message

        self._start_ai_generation(full_prompt)

    def append_message(self, role: str, text: str):
        if role == "user":
            marker = '<span style="color: #7fbf8f; font-size: 7px;">◆</span>'
            color = "#c8e0ce"
        else:
            marker = '<span style="color: rgba(180,210,190,0.35); font-size: 7px;">◇</span>'
            color = "rgba(180,210,190,0.6)"

        # Escape HTML entities so code/HTML in responses displays as text
        escaped_text = html.escape(text)
        msg_html = f'<p style="margin: 5px 0; line-height: 1.5;">{marker} <span style="color: {color}; font-size: 10px;">{escaped_text}</span></p>'
        self.chat_area.append(msg_html)

    def _setup_ai(self):
        """Initialize AI manager and connect signals."""
        self.ai_manager = AIManager(self)
        self.ai_manager.token_received.connect(self._on_ai_token)
        self.ai_manager.generation_finished.connect(self._on_ai_finished)
        self.ai_manager.generation_error.connect(self._on_ai_error)

    def _start_ai_generation(self, prompt: str):
        """Start AI generation with the current model."""
        self._current_ai_response = ""
        # Store current HTML so we can rebuild with streaming updates
        self._chat_html_before_response = self.chat_area.toHtml()
        # Show stop button, hide send button
        self.send_btn.hide()
        self.stop_btn.show()
        # Get context based on mode (placeholder - main window will provide actual context)
        context = None
        # Pass layout mode to AI manager for system prompt selection
        self.ai_manager.generate(self.current_model["id"], prompt, context, self._layout_mode.value)

    def _stop_generation(self):
        """Stop the current AI generation."""
        self.ai_manager.stop()
        self._on_generation_stopped()
        # Add indicator that generation was stopped
        self.chat_area.append(
            '<p style="margin: 5px 0; color: rgba(180,210,190,0.4); font-size: 10px;">'
            "[Generation stopped]</p>"
        )

    def _on_generation_stopped(self):
        """Handle generation stopped (either finished, error, or user stopped)."""
        self.stop_btn.hide()
        self.send_btn.show()

    def _on_ai_token(self, token: str):
        """Handle incoming token from AI."""
        self._current_ai_response += token
        # Update the last message with accumulated response
        self._update_ai_response(self._current_ai_response)

    def _on_ai_finished(self):
        """Handle AI generation complete."""
        self._on_generation_stopped()
        # Final update to ensure complete response is shown
        if self._current_ai_response:
            self._update_ai_response(self._current_ai_response)

            # In writing mode, add text action buttons if no code blocks
            if self._layout_mode == LayoutMode.WRITING and not self._code_blocks:
                link_style = "color: #7fbf8f; text-decoration: none;"
                text_actions_html = (
                    '<p style="margin: 8px 0 5px 0; padding: 6px 10px; '
                    'background: rgba(0,0,0,0.2); border-radius: 4px;">'
                    f'<span style="color: rgba(180,210,190,0.5); font-size: 10px;">text</span>'
                    f"&nbsp;&nbsp;—&nbsp;&nbsp;"
                    f'<a href="action:copy_text" style="{link_style}; font-size: 10px;">Copy</a>'
                    f"&nbsp;&nbsp;|&nbsp;&nbsp;"
                    f'<a href="action:insert_text" style="{link_style}; font-size: 10px;">Insert</a>'
                    f"&nbsp;&nbsp;|&nbsp;&nbsp;"
                    f'<a href="action:newtab_text" style="{link_style}; font-size: 10px;">New Tab</a>'
                )
                # Add Replace if we have a selection
                if self._has_selection_to_replace:
                    text_actions_html += (
                        f"&nbsp;&nbsp;|&nbsp;&nbsp;"
                        f'<a href="action:replace_text" style="{link_style}; '
                        f'font-size: 10px; font-weight: bold;">Replace</a>'
                    )
                text_actions_html += "</p>"
                self.chat_area.append(text_actions_html)

            # Add "Continue" and "Clear" links after response
            footer_html = (
                '<p style="margin: 8px 0 5px 0;">'
                '<a href="action:continue" style="color: #7fbf8f; text-decoration: none; '
                'font-size: 10px;">▶ Continue</a>'
                "&nbsp;&nbsp;&nbsp;"
                '<a href="action:clear" style="color: rgba(180,210,190,0.35); '
                'text-decoration: none; font-size: 10px;">✕ Clear</a></p>'
            )
            self.chat_area.append(footer_html)

    def _on_ai_error(self, error: str):
        """Handle AI generation error."""
        self._on_generation_stopped()
        self._update_ai_response(f"[Error: {error}]")

    def _format_response_text(self, text: str) -> str:
        """Format AI response with styled code blocks and action buttons."""
        # Clear previous code blocks
        self._code_blocks = []

        # Pattern for ```language\ncode\n``` (handles \r\n and \n)
        code_block_pattern = r"```(\w*)\r?\n(.*?)```"

        # Link style for action buttons (QTextBrowser compatible)
        link_style = "color: #7fbf8f; text-decoration: none;"

        def format_code_block(match: re.Match[str], index: int) -> str:
            language = match.group(1) or "code"
            raw_code = match.group(2).strip()
            escaped_code = html.escape(raw_code)

            # Store raw code for later retrieval
            self._code_blocks.append((raw_code, language))

            # Action links with pipe separators (QTextBrowser doesn't support margin)
            actions_html = (
                f'<a href="code:copy:{index}" style="{link_style}">Copy</a>'
                f"&nbsp;&nbsp;|&nbsp;&nbsp;"
                f'<a href="code:insert:{index}" style="{link_style}">Insert</a>'
                f"&nbsp;&nbsp;|&nbsp;&nbsp;"
                f'<a href="code:newtab:{index}" style="{link_style}">New Tab</a>'
            )

            # Add "Replace" action if we have a selection to replace
            if self._has_selection_to_replace:
                actions_html += (
                    f"&nbsp;&nbsp;|&nbsp;&nbsp;"
                    f'<a href="code:replace:{index}" style="{link_style}; '
                    f'font-weight: bold;">Replace</a>'
                )

            return (
                f'<div style="background: rgba(0,0,0,0.3); border-radius: 4px; '
                f'padding: 10px; margin: 8px 0;">'
                f'<p style="margin: 0 0 6px 0; color: rgba(180,210,190,0.5); '
                f'font-size: 10px;">{language} &nbsp;&nbsp;—&nbsp;&nbsp; {actions_html}</p>'
                f'<pre style="margin: 0; white-space: pre-wrap; '
                f"font-family: Consolas, 'SF Mono', monospace; font-size: 12px; "
                f'color: #c8e0ce; line-height: 1.4;">{escaped_code}</pre></div>'
            )

        # Split text by code blocks, process each part
        result_parts = []
        last_end = 0

        for block_index, match in enumerate(re.finditer(code_block_pattern, text, re.DOTALL)):
            # Add escaped text before this code block (with line breaks)
            before_text = text[last_end : match.start()]
            if before_text:
                result_parts.append(self._format_plain_text(before_text))

            # Add formatted code block with actions
            result_parts.append(format_code_block(match, block_index))
            last_end = match.end()

        # Add remaining text after last code block (with line breaks)
        remaining = text[last_end:]
        if remaining:
            result_parts.append(self._format_plain_text(remaining))

        return "".join(result_parts)

    @staticmethod
    def _format_plain_text(text: str) -> str:
        """Escape HTML and convert newlines to <br> for readable display."""
        escaped = html.escape(text)
        return escaped.replace("\n", "<br>")

    def _update_ai_response(self, text: str):
        """Update the current AI response in the chat area."""
        color = "rgba(180,210,190,0.6)"

        # Format response with styled code blocks
        formatted_text = self._format_response_text(text)

        # Build the AI response HTML
        ai_response_html = (
            f'<p style="margin: 5px 0; line-height: 1.5;">'
            f'<span style="color: rgba(180,210,190,0.35); font-size: 7px;">◇</span> '
            f'<span style="color: {color}; font-size: 10px;">{formatted_text}</span></p>'
        )

        # Restore saved HTML and append the current AI response
        if hasattr(self, "_chat_html_before_response"):
            self.chat_area.setHtml(self._chat_html_before_response)
            self.chat_area.append(ai_response_html)

        # Scroll to bottom
        self.chat_area.verticalScrollBar().setValue(self.chat_area.verticalScrollBar().maximum())

    def apply_theme(self):
        """Public method for external theme updates."""
        self._apply_theme()

    def _apply_prompt_button_styles(self):
        """Apply styles to prompt buttons (called from _apply_theme and _rebuild_prompts_grid)."""
        theme = self.settings_manager.get_current_theme()
        fg = theme.foreground
        accent = theme.keyword
        if theme.is_beveled:
            # Win95: raised beveled prompt buttons
            for btn in self.prompt_buttons:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {theme.chrome_hover};
                        {theme.bevel_raised}
                        color: {hex_to_rgba(fg, 0.5)};
                        font-family: 'Consolas', 'SF Mono', monospace;
                        font-size: 11px;
                        padding: 5px 2px;
                        text-align: center;
                    }}
                    QPushButton:hover {{
                        color: {hex_to_rgba(fg, 0.8)};
                    }}
                    QPushButton:pressed {{
                        background: {theme.chrome_bg};
                        {theme.bevel_sunken}
                        color: {accent};
                    }}
                """)
        else:
            pressed_bg = hex_to_rgba(accent, 0.15)
            for btn in self.prompt_buttons:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {hex_to_rgba(fg, 0.04)};
                        border: 1px solid {hex_to_rgba(fg, 0.12)};
                        border-radius: 6px;
                        color: {hex_to_rgba(fg, 0.55)};
                        font-family: 'Consolas', 'SF Mono', monospace;
                        font-size: 11px;
                        padding: 5px 2px;
                        text-align: center;
                    }}
                    QPushButton:hover {{
                        background: {hex_to_rgba(fg, 0.1)};
                        border: 1px solid {hex_to_rgba(fg, 0.2)};
                        color: {hex_to_rgba(fg, 0.85)};
                    }}
                    QPushButton:pressed {{
                        background: {pressed_bg};
                        border: 1px solid {accent};
                        color: {accent};
                    }}
                """)

    def _get_options_menu_style(self, has_active_item: bool = False) -> str:
        """Get stylesheet for the options popup menu, themed to current theme."""
        theme = self.settings_manager.get_current_theme()
        bg = theme.chrome_bg
        fg = theme.foreground
        accent = theme.function

        menu_border = (
            theme.bevel_raised
            if theme.is_beveled
            else f"border: 1px solid {hex_to_rgba(fg, 0.15)};"
        )

        return f"""
            QMenu {{
                background-color: {bg};
                {menu_border}
                border-radius: {theme.radius_large};
                padding: 6px 4px;
                min-width: 160px;
                max-width: 180px;
            }}
            QMenu::item {{
                background-color: transparent;
                color: {hex_to_rgba(fg, 0.6)};
                padding: 7px 12px;
                border-radius: {theme.radius};
                font-size: 11px;
                margin: 1px 4px;
            }}
            QMenu::item:selected {{
                background-color: {hex_to_rgba(fg, 0.08)};
                color: {accent};
            }}
            QMenu::separator {{
                height: 1px;
                background: {hex_to_rgba(fg, 0.1)};
                margin: 5px 10px;
            }}
            QMenu::right-arrow {{
                width: 8px;
                height: 8px;
            }}
        """

    def _update_options_button_state(self):
        """Update options button appearance based on context state."""
        theme = self.settings_manager.get_current_theme()
        fg = theme.foreground
        accent = theme.function
        if self._include_context:
            # Context active - accent color
            self.options_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    color: {accent};
                    font-size: 16px;
                    font-weight: bold;
                }}
            """)
        else:
            # Context off - dimmed
            self.options_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    color: {hex_to_rgba(fg, 0.4)};
                    font-size: 16px;
                    font-weight: bold;
                }}
            """)

    def _apply_theme(self):
        """Apply current theme colors to the side panel."""
        theme = self.settings_manager.get_current_theme()
        chrome_bg = theme.chrome_bg
        fg = theme.foreground

        # Panel background matches chrome_bg (same as menu/tab bar)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {chrome_bg};
                color: {hex_to_rgba(fg, 0.65)};
                font-family: 'Consolas', 'SF Mono', monospace;
            }}
        """)

        # AI Assistant title bar
        if hasattr(self, "title_bar"):
            if theme.is_beveled:
                title_bg = chrome_bg
                title_border = ""
            else:
                title_bg = (
                    f"qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                    f"stop:0 {theme._darken(chrome_bg, 10)},"
                    f"stop:0.5 {hex_to_rgba(theme.keyword, 0.09)},"
                    f"stop:1 {chrome_bg})"
                )
                title_border = f"border-bottom: 1px solid {hex_to_rgba(fg, 0.08)};"
            self.title_bar.setStyleSheet(f"""
                QWidget {{
                    background: {title_bg};
                    {title_border}
                }}
                QLabel {{
                    color: {fg};
                    font-size: 11px;
                    font-weight: bold;
                    background: transparent;
                    border: none;
                }}
            """)
            self.collapse_btn.setStyleSheet(f"""
                QToolButton {{
                    background: transparent;
                    border: none;
                    color: {hex_to_rgba(fg, 0.3)};
                    font-size: 14px;
                }}
                QToolButton:hover {{
                    color: {hex_to_rgba(fg, 0.7)};
                }}
            """)

        # Chat area — sunken well with darker bg (matches playground)
        # Bevel/border applied to container widget (QTextBrowser ignores QSS borders)
        chat_bg = theme._darken(chrome_bg, 8)
        if theme.is_beveled:
            chat_border = theme.bevel_sunken
        else:
            chat_border = f"border: 1px solid {theme.chrome_border};border-radius: 6px;"
        self.chat_container.setObjectName("chat_container")
        self.chat_container.setStyleSheet(f"""
            QWidget#chat_container {{
                background-color: {chat_bg};
                {chat_border}
            }}
        """)
        chat_radius = "0px" if theme.is_beveled else "6px"
        self.chat_area.setStyleSheet(f"""
            QTextBrowser {{
                background-color: transparent;
                color: {fg};
                border: none;
                border-radius: {chat_radius};
                padding: 8px;
                font-size: 11px;
            }}
        """)

        # Prompts label
        self.prompts_label.setStyleSheet(f"""
            QLabel {{
                background: transparent;
                color: {hex_to_rgba(fg, 0.4)};
                font-size: 10px;
                font-weight: 600;
                padding: 2px 0;
                margin: 0;
            }}
        """)

        # Prompt chips (flat text, no borders)
        self._apply_prompt_button_styles()

        # Model button — Win95 gets sunken dropdown look
        accent = theme.keyword
        if theme.is_beveled:
            model_bg = theme._darken(theme.chrome_bg, 8)
            self.model_btn.setStyleSheet(f"""
                QToolButton {{
                    background: {model_bg};
                    {theme.bevel_sunken}
                    color: {fg};
                    font-size: 11px;
                    padding: 3px 6px;
                    text-align: left;
                }}
                QToolButton:hover {{
                    color: {hex_to_rgba(fg, 0.8)};
                }}
                QToolButton:pressed {{
                    background: {theme.chrome_bg};
                    color: {accent};
                }}
                QToolButton::menu-indicator {{
                    image: none;
                    width: 0px;
                }}
            """)
        else:
            pressed_bg = hex_to_rgba(accent, 0.15)
            self.model_btn.setStyleSheet(f"""
                QToolButton {{
                    background: {hex_to_rgba(fg, 0.04)};
                    border: 1px solid {hex_to_rgba(fg, 0.12)};
                    border-radius: 6px;
                    color: {hex_to_rgba(fg, 0.55)};
                    font-size: 11px;
                    padding: 3px 8px;
                    text-align: left;
                }}
                QToolButton:hover {{
                    border: 1px solid {hex_to_rgba(fg, 0.2)};
                    color: {hex_to_rgba(fg, 0.8)};
                }}
                QToolButton:pressed {{
                    background: {pressed_bg};
                    border: 1px solid {accent};
                    color: {accent};
                }}
                QToolButton::menu-indicator {{
                    image: none;
                    width: 0px;
                }}
            """)

        # Model menu
        model_menu_border = (
            theme.bevel_raised if theme.is_beveled else f"border: 1px solid {hex_to_rgba(fg, 0.1)};"
        )
        menu_style = f"""
            QMenu {{
                background-color: {chrome_bg};
                {model_menu_border}
                border-radius: {theme.radius};
                padding: 4px 0;
                font-size: 10px;
            }}
            QMenu::item {{
                color: {hex_to_rgba(fg, 0.6)};
                padding: 6px 12px;
                font-size: 10px;
            }}
            QMenu::item:selected {{
                color: {hex_to_rgba(fg, 0.8)};
                background: {hex_to_rgba(fg, 0.08)};
            }}
        """
        if self.model_btn.menu():
            self.model_btn.menu().setStyleSheet(menu_style)

        # Options button (+ button in input row)
        self._update_options_button_state()

        # Input container — Win95 gets sunken well with darker bg
        if theme.is_beveled:
            input_well_bg = theme._darken(theme.chrome_bg, 8)
            self.input_row_widget.setStyleSheet(f"""
                QWidget {{
                    background: {input_well_bg};
                    {theme.bevel_sunken}
                    border-radius: 0px;
                }}
            """)
        else:
            self.input_row_widget.setStyleSheet(f"""
                QWidget {{
                    background: {hex_to_rgba(fg, 0.02)};
                    border: 1px solid {theme.chrome_border};
                    border-radius: 6px;
                }}
            """)

        # Input field (multi-line text area)
        self.input_field.setStyleSheet(f"""
            QPlainTextEdit {{
                background: transparent;
                border: none;
                color: {fg};
                font-size: 10px;
                padding: 0;
            }}
        """)

        # Send button — visible button with accent flash on press
        accent = theme.keyword
        fg_mid = hex_to_rgba(fg, 0.55)
        pressed_bg = hex_to_rgba(accent, 0.25)
        if theme.is_beveled:
            self.send_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {theme.chrome_hover};
                    {theme.bevel_raised}
                    color: {fg_mid};
                    font-size: 11px;
                    font-weight: bold;
                    padding: 5px 12px;
                }}
                QPushButton:hover {{
                    background: {hex_to_rgba(accent, 0.1)};
                    color: {accent};
                }}
                QPushButton:pressed {{
                    background: {theme.chrome_bg};
                    {theme.bevel_sunken}
                    color: {accent};
                }}
            """)
        else:
            self.send_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {theme.chrome_hover};
                    border: 1px solid {theme.chrome_border};
                    border-radius: 6px;
                    color: {fg_mid};
                    font-size: 11px;
                    font-weight: bold;
                    padding: 5px 12px;
                }}
                QPushButton:hover {{
                    background: {hex_to_rgba(accent, 0.12)};
                    border: 1px solid {accent};
                    color: {accent};
                }}
                QPushButton:pressed {{
                    background: {pressed_bg};
                    border: 1px solid {accent};
                    color: {fg};
                }}
            """)

        # Stop button (red accent for visibility)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #e07070;
                font-size: 12px;
            }
            QPushButton:hover {
                color: #ff9090;
            }
        """)
