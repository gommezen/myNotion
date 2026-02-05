"""
AI Chat Panel with Metropolis Art Deco design.
Based on ai-panel-redesign-v2_1.jsx — exact 1:1 implementation.
"""

import html
import re
from enum import Enum

from PyQt6.QtCore import QEvent, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMenu,
    QPushButton,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ai.worker import AIManager
from core.settings import SettingsManager


class LayoutMode(Enum):
    """Layout modes for the side panel AI prompts."""

    CODING = "coding"
    WRITING = "writing"


# ─── Data ───
MODELS = [
    {"id": "qwen2.5:7b-instruct-q4_0", "name": "Qwen 2.5", "tag": "7B"},
    {"id": "llama3.2:latest", "name": "Llama 3.2", "tag": "3B"},
    {"id": "gemma3:4b", "name": "Gemma 3", "tag": "4B"},
    {"id": "mistral:7b-instruct-q4_0", "name": "Mistral", "tag": "7B"},
    {"id": "llama3.1:8b-instruct-q4_0", "name": "Llama 3.1", "tag": "8B Q4"},
    {"id": "llama3.1:8b-instruct-q8_0", "name": "Llama 3.1", "tag": "8B Q8"},
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
            "Simplify",
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

# AI prompts with icons (card-style layout)
# Special actions: "transfer", "examples", "custom" have action handlers instead of prompts
# Each prompt has a "modes" field: ["coding"], ["writing"], or ["coding", "writing"] for shared
AI_PROMPTS = [
    # Coding-only prompts
    {
        "label": "Explain",
        "icon": "◎",
        "prompt": "Explain this code in detail",
        "tip": "Describe what the code does and how it works",
        "modes": ["coding"],
    },
    {
        "label": "Docstring",
        "icon": "☰",
        "prompt": "Add Google-style docstrings to this code. Return the complete code with docstrings added",
        "tip": "Add documentation strings to functions/classes",
        "modes": ["coding"],
    },
    {
        "label": "Simplify",
        "icon": "◇",
        "prompt": "Simplify this code while keeping the same behavior. Return the simplified code",
        "tip": "Make code shorter and easier to read",
        "modes": ["coding"],
    },
    {
        "label": "Debug",
        "icon": "⚡",
        "prompt": "Find bugs and potential issues in this code",
        "tip": "Find bugs and potential issues",
        "modes": ["coding"],
    },
    {
        "label": "Fix",
        "icon": "✓",
        "prompt": "Fix any errors or issues in this code. Return the corrected code",
        "tip": "Correct errors and issues in code",
        "modes": ["coding"],
    },
    {
        "label": "Refactor",
        "icon": "⟳",
        "prompt": "Refactor this code to be cleaner and more maintainable. Return the refactored code",
        "tip": "Restructure code without changing behavior",
        "modes": ["coding"],
    },
    {
        "label": "Test",
        "icon": "▣",
        "prompt": "Generate unit tests for this code",
        "tip": "Generate unit tests for the code",
        "modes": ["coding"],
    },
    # Writing-only prompts
    {
        "label": "Summarize",
        "icon": "≡",
        "prompt": "Summarize this text in 2-3 sentences maximum. Put each sentence on its own line. Be extremely concise",
        "tip": "Brief overview of the text",
        "modes": ["writing"],
    },
    {
        "label": "Improve",
        "icon": "▲",
        "prompt": "Improve this text's clarity, grammar, and readability. Keep the same length and preserve line breaks. Return only the improved text",
        "tip": "Enhance writing quality and readability",
        "modes": ["writing"],
    },
    {
        "label": "Translate",
        "icon": "⇄",
        "prompt": None,
        "action": "translate",
        "tip": "Convert text to a different language",
        "modes": ["writing"],
    },
    {
        "label": "Expand",
        "icon": "+",
        "prompt": "Expand this text with more detail, examples, or explanations. Make it about 2x longer. Return only the expanded text",
        "tip": "Add more depth and detail",
        "modes": ["writing"],
    },
    {
        "label": "Tone",
        "icon": "~",
        "prompt": None,
        "action": "tone",
        "tip": "Change writing tone",
        "modes": ["writing"],
    },
    {
        "label": "Shorten",
        "icon": "-",
        "prompt": "Shorten this text to about half its length or less. Remove redundancy, keep only essential points. Return only the shortened text, no explanations",
        "tip": "Make more concise",
        "modes": ["writing"],
    },
    # Shared prompts (appear in both modes)
    {
        "label": "Custom",
        "icon": "✎",
        "prompt": None,
        "action": "custom",
        "tip": "Enter your own prompt",
        "modes": ["coding", "writing"],
    },
    {
        "label": "Examples",
        "icon": "⊕",
        "prompt": None,
        "action": "examples",
        "tip": "Generate more examples from last response",
        "modes": ["coding", "writing"],
    },
    {
        "label": "Transfer",
        "icon": "↳",
        "prompt": None,
        "action": "transfer",
        "tip": "Insert last code block into editor",
        "modes": ["coding", "writing"],
    },
]

CONTEXT_MODES = [
    {"id": "selection", "label": "Selection"},
    {"id": "file", "label": "Full file"},
    {"id": "project", "label": "Project"},
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
    replace_selection_requested = pyqtSignal(str)  # new code - replaces selected text in editor
    layout_mode_changed = pyqtSignal(str)  # emitted when layout mode changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_manager = SettingsManager()
        self.current_model = MODELS[0]
        self.context_mode = "selection"
        self.prompts_visible = True
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

        # Keep context_buttons as empty list for compatibility
        self.context_buttons: list[QPushButton] = []

        # ─── Chat area ───
        self.chat_area = QTextBrowser()
        self.chat_area.setOpenExternalLinks(False)  # Handle links ourselves
        self.chat_area.anchorClicked.connect(self._on_anchor_clicked)
        self.chat_area.setPlaceholderText("Start a conversation...")
        layout.addWidget(self.chat_area, stretch=1)

        # ─── AI Prompts section (collapsible) ───
        prompts_section = QWidget()
        prompts_layout = QVBoxLayout(prompts_section)
        prompts_layout.setContentsMargins(16, 2, 16, 4)
        prompts_layout.setSpacing(4)

        # Toggle button
        self.prompts_toggle = QPushButton("AI Prompts ▾")
        self.prompts_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prompts_toggle.clicked.connect(self._toggle_prompts)
        prompts_layout.addWidget(self.prompts_toggle, alignment=Qt.AlignmentFlag.AlignLeft)

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
        input_layout.setContentsMargins(16, 0, 16, 10)
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

        input_layout.addLayout(model_row)

        # Input row with background
        input_row_widget = QWidget()
        input_row = QHBoxLayout(input_row_widget)
        input_row.setContentsMargins(8, 6, 8, 6)
        input_row.setSpacing(6)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask anything...")
        self.input_field.returnPressed.connect(self._send_message)
        # Track focus for gold border effect
        self.input_field.installEventFilter(self)
        input_row.addWidget(self.input_field)

        self.send_btn = QPushButton("▶")
        self.send_btn.setFixedSize(24, 24)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.clicked.connect(self._send_message)
        input_row.addWidget(self.send_btn)

        # Stop button (hidden by default, shown during generation)
        self.stop_btn = QPushButton("■")
        self.stop_btn.setFixedSize(24, 24)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setToolTip("Stop generating")
        self.stop_btn.clicked.connect(self._stop_generation)
        self.stop_btn.hide()
        input_row.addWidget(self.stop_btn)

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
        """Update input row border based on focus state."""
        if focused:
            self.input_row_widget.setStyleSheet("""
                QWidget {
                    background: rgba(180,210,190,0.04);
                    border: 1px solid #d4a84b;
                    border-radius: 3px;
                }
            """)
        else:
            self.input_row_widget.setStyleSheet("""
                QWidget {
                    background: rgba(180,210,190,0.04);
                    border: 1px solid transparent;
                    border-radius: 3px;
                }
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
            p for p in AI_PROMPTS if mode_value in p.get("modes", ["coding", "writing"])
        ]

        # Create buttons for filtered prompts
        for i, prompt in enumerate(filtered_prompts):
            icon = prompt.get("icon", "")
            label = prompt["label"]
            btn = QPushButton(f"{icon} {label}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(prompt.get("tip", ""))
            btn.clicked.connect(lambda checked, p=prompt: self._on_prompt_click(p))
            self.prompt_buttons.append(btn)
            row, col = i // 3, i % 3  # 3 columns
            self._prompts_grid_layout.addWidget(btn, row, col)

        # Re-apply theme to new buttons
        self._apply_prompt_button_styles()

    def _toggle_prompts(self):
        self.prompts_visible = not self.prompts_visible
        self.prompts_container.setVisible(self.prompts_visible)
        self.prompts_toggle.setText(f"AI Prompts {'▾' if self.prompts_visible else '▸'}")

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
        """Generate more examples based on code in the last AI response."""
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
        else:
            # No code blocks, use the full response
            prompt = (
                f"Based on this:\n\n{self._current_ai_response}\n\n"
                f"Please give me more examples or variations."
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
            prompt = text.strip()
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
            prompt = f"Translate this text to {language}. Preserve all line breaks and paragraph structure. Return only the translated text."
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
            prompt = f"Rewrite this text in a {tone.lower()} tone. Preserve line breaks and paragraph structure. Return only the rewritten text."
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
            # In writing mode, transfer the full response text
            self.transfer_to_editor_requested.emit(self._current_ai_response)
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
        if action == "copy":
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(text)
                self.append_message("system", "[Text copied to clipboard]")
        elif action == "insert":
            self.transfer_to_editor_requested.emit(text)
            self.append_message("system", "[Text inserted at cursor]")
        elif action == "newtab":
            self.new_tab_with_code_requested.emit(text, "text")
            self.append_message("system", "[Text opened in new tab]")
        elif action == "replace":
            self.replace_selection_requested.emit(text)
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

    def _send_message(self):
        text = self.input_field.text().strip()
        if text:
            self.append_message("user", text)
            self.message_sent.emit(text, self.current_model["id"], self.context_mode)
            self.input_field.clear()
            self._start_ai_generation(text)

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

            # Add "Continue" link after response
            continue_html = (
                '<p style="margin: 8px 0 5px 0;">'
                '<a href="action:continue" style="color: #7fbf8f; text-decoration: none; '
                'font-size: 10px;">▶ Continue generating...</a></p>'
            )
            self.chat_area.append(continue_html)

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
            # Add escaped text before this code block
            before_text = text[last_end : match.start()]
            if before_text:
                result_parts.append(html.escape(before_text))

            # Add formatted code block with actions
            result_parts.append(format_code_block(match, block_index))
            last_end = match.end()

        # Add remaining text after last code block
        remaining = text[last_end:]
        if remaining:
            result_parts.append(html.escape(remaining))

        return "".join(result_parts)

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
        text_main = "#8aa898"
        for btn in self.prompt_buttons:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    border-radius: 3px;
                    color: rgba(127, 191, 181, 0.6);
                    font-size: 11px;
                    padding: 6px 4px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background: rgba(180,210,190,0.08);
                    color: {text_main};
                }}
            """)

    def _apply_theme(self):
        """Apply Metropolis Art Deco theme."""
        bg = "#1a2a2a"
        text_main = "#8aa898"
        accent = "#7fbf8f"

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg};
                color: {text_main};
                font-family: 'Consolas', 'SF Mono', monospace;
            }}
        """)

        # Chat area
        self.chat_area.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {bg};
                color: {text_main};
                border: none;
                padding: 8px 16px;
                font-size: 10px;
            }}
        """)

        # Prompts toggle
        self.prompts_toggle.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: rgba(180,210,190,0.4);
                font-size: 10px;
                font-weight: 600;
                padding: 2px 0;
                letter-spacing: 0.1em;
                text-transform: uppercase;
                text-align: left;
            }}
            QPushButton:hover {{
                color: {text_main};
            }}
        """)

        # Prompt chips (flat text, no borders)
        self._apply_prompt_button_styles()

        # Model button
        self.model_btn.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                border: none;
                color: rgba(180,210,190,0.4);
                font-size: 10px;
                font-weight: 600;
                padding: 2px 0;
                letter-spacing: 0.1em;
                text-transform: uppercase;
            }}
            QToolButton:hover {{
                color: {text_main};
            }}
            QToolButton::menu-indicator {{
                image: none;
                width: 0px;
            }}
        """)

        # Model menu
        menu_style = f"""
            QMenu {{
                background-color: {bg};
                border: 1px solid rgba(180,210,190,0.1);
                border-radius: 3px;
                padding: 4px 0;
                font-size: 10px;
            }}
            QMenu::item {{
                color: rgba(180,210,190,0.6);
                padding: 6px 12px;
                font-size: 10px;
            }}
            QMenu::item:selected {{
                color: {text_main};
                background: rgba(180,210,190,0.08);
            }}
        """
        if self.model_btn.menu():
            self.model_btn.menu().setStyleSheet(menu_style)

        # Input row background (transparent border reserves space for focus border)
        self.input_row_widget.setStyleSheet("""
            QWidget {
                background: rgba(180,210,190,0.04);
                border: 1px solid transparent;
                border-radius: 3px;
            }
        """)

        # Input field
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #c8e0ce;
                font-size: 10px;
                padding: 0;
            }
        """)

        # Send button
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {accent};
                font-size: 12px;
            }}
            QPushButton:hover {{
                color: {text_main};
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
