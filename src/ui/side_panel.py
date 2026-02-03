"""
AI Chat Panel with Metropolis Art Deco design.
Based on ai-panel-redesign-v2_1.jsx — exact 1:1 implementation.
"""

import html
import re

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
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

# ─── Data ───
MODELS = [
    {"id": "llama3.2:latest", "name": "Llama 3.2", "tag": "3B"},
    {"id": "phi3:latest", "name": "Phi 3", "tag": "3.8B"},
    {"id": "qwen2:1.5b", "name": "Qwen 2", "tag": "1.5B"},
    {"id": "gemma2:2b", "name": "Gemma 2", "tag": "2B"},
    {"id": "mistral", "name": "Mistral", "tag": "7B"},
    {"id": "llama3.1", "name": "Llama 3.1", "tag": "8B"},
    {"id": "codellama", "name": "Code Llama", "tag": "7B"},
    {"id": "deepseek-coder", "name": "DeepSeek", "tag": "6.7B"},
]

# Grid slots: assigned actions + empty placeholders
# "type" key: "app" for shortcuts, "prompt" for AI actions, None for empty
INITIAL_GRID = [
    {"id": 1, "type": "app", "label": "gmail", "icon": "✉", "url": "https://mail.google.com"},
    {"id": 2, "type": "app", "label": "claude", "icon": "◈", "url": "https://claude.ai"},
    {"id": 3, "type": "prompt", "label": "explain", "icon": "✦", "prompt": "Explain this code"},
    {"id": 4, "type": None, "label": None, "icon": None},
    {"id": 5, "type": None, "label": None, "icon": None},
    {"id": 6, "type": None, "label": None, "icon": None},
]

# AI-specific quick prompts (inline row above grid)
# "Transfer" and "Examples" are special actions
AI_PROMPTS = [
    {"label": "Explain", "prompt": "Explain this code"},
    {"label": "Docstring", "prompt": "Add docstrings"},
    {"label": "Simplify", "prompt": "Simplify this"},
    {"label": "Debug", "prompt": "Find bugs"},
    {"label": "Examples", "prompt": None, "action": "examples"},
    {"label": "Transfer", "prompt": None, "action": "transfer"},
]

CONTEXT_MODES = [
    {"id": "selection", "label": "Selection"},
    {"id": "file", "label": "Full file"},
    {"id": "project", "label": "Project"},
]


class CollapsedPanel(QWidget):
    """Collapsed state: thin vertical strip with door button only."""

    expand_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(36)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        # Door button (open direction) - only element
        self.door_btn = QToolButton()
        self.door_btn.setText("◨")
        self.door_btn.setToolTip("Open AI panel")
        self.door_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.door_btn.clicked.connect(self.expand_requested.emit)
        layout.addWidget(self.door_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()

        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1a2a2a;
            }
        """)

        self.door_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
                color: rgba(180,210,190,0.45);
                font-size: 22px;
                padding: 6px;
            }
            QToolButton:hover {
                color: #b4d2be;
            }
        """)


class SidePanel(QWidget):
    """AI Chat Panel with Metropolis Art Deco aesthetic."""

    message_sent = pyqtSignal(str, str, str)  # message, model_id, context_mode
    quick_action_triggered = pyqtSignal(str)  # prompt
    settings_requested = pyqtSignal()
    collapse_requested = pyqtSignal()
    transfer_to_editor_requested = pyqtSignal(str)  # code content
    new_tab_with_code_requested = pyqtSignal(str, str)  # code content, language

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_manager = SettingsManager()
        self.current_model = MODELS[0]
        self.context_mode = "selection"
        self.prompts_visible = True
        self._current_ai_response = ""  # Buffer for streaming response
        self._chat_html_before_response = ""  # HTML state before AI response
        self._code_blocks: list[tuple[str, str]] = []  # [(code, language), ...]
        self._setup_ui()
        self._apply_theme()
        self._setup_ai()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ─── Header accent (zigzag pattern) ───
        self.header_accent = QLabel("/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\")
        self.header_accent.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.header_accent)

        # ─── Header: context toggle left, door icon right ───
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 6)
        header_layout.setSpacing(2)

        # Context mode toggle
        self.context_buttons: list[QPushButton] = []
        for mode in CONTEXT_MODES:
            btn = QPushButton(mode["label"])
            btn.setCheckable(True)
            btn.setChecked(mode["id"] == self.context_mode)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, m=mode["id"]: self._set_context(m))
            self.context_buttons.append(btn)
            header_layout.addWidget(btn)

        header_layout.addStretch()

        # Door button (close direction)
        self.door_btn = QToolButton()
        self.door_btn.setText("◧")  # Door icon pointing right
        self.door_btn.setToolTip("Close panel")
        self.door_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.door_btn.clicked.connect(self.collapse_requested.emit)
        header_layout.addWidget(self.door_btn)

        layout.addWidget(header)

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

        # Prompts grid (collapsible) - 3 columns to fit in panel
        self.prompts_container = QWidget()
        prompts_grid = QGridLayout(self.prompts_container)
        prompts_grid.setContentsMargins(0, 4, 0, 0)
        prompts_grid.setSpacing(2)

        self.prompt_buttons: list[QPushButton] = []
        for i, prompt in enumerate(AI_PROMPTS):
            btn = QPushButton(prompt["label"])
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, p=prompt: self._on_prompt_click(p))
            self.prompt_buttons.append(btn)
            row, col = i // 3, i % 3
            prompts_grid.addWidget(btn, row, col)

        prompts_layout.addWidget(self.prompts_container)
        layout.addWidget(prompts_section)

        # ─── Quick Actions Grid ───
        grid_section = QWidget()
        grid_layout = QVBoxLayout(grid_section)
        grid_layout.setContentsMargins(16, 6, 16, 8)
        grid_layout.setSpacing(8)

        self.grid_label = QLabel("Quick Actions")
        grid_layout.addWidget(self.grid_label)

        # 3x2 grid
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)

        self.grid_buttons: list[QPushButton] = []
        for i, slot in enumerate(INITIAL_GRID):
            row, col = i // 3, i % 3
            btn = QPushButton()
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(42)

            if slot["type"]:
                btn.setText(f"{slot['icon']}\n{slot['label']}")
                btn.setProperty("filled", True)
                btn.clicked.connect(lambda checked, s=slot: self._on_grid_click(s))
            else:
                btn.setText("+")
                btn.setProperty("filled", False)
                btn.setToolTip("Add shortcut")

            self.grid_buttons.append(btn)
            grid.addWidget(btn, row, col)

        grid_layout.addWidget(grid_widget)
        layout.addWidget(grid_section)

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

    def _set_model(self, model: dict):
        self.current_model = model
        self._update_model_button()

    def _set_context(self, mode: str):
        self.context_mode = mode
        for btn, m in zip(self.context_buttons, CONTEXT_MODES, strict=False):
            btn.setChecked(m["id"] == mode)

    def _toggle_prompts(self):
        self.prompts_visible = not self.prompts_visible
        self.prompts_container.setVisible(self.prompts_visible)
        self.prompts_toggle.setText(f"AI Prompts {'▾' if self.prompts_visible else '▸'}")

    def _on_prompt_click(self, prompt: dict):
        # Handle special actions (e.g., Transfer, Examples)
        action = prompt.get("action")
        if action == "transfer":
            self._transfer_to_editor()
            return
        if action == "examples":
            self._generate_more_examples()
            return

        self.append_message("user", prompt["prompt"])
        self.quick_action_triggered.emit(prompt["prompt"])
        self._start_ai_generation(prompt["prompt"])

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

    def _transfer_to_editor(self):
        """Extract code from last AI response and emit signal to insert in editor."""
        if not self._current_ai_response:
            self.append_message("system", "[No AI response to transfer]")
            return

        code = self._extract_code_blocks(self._current_ai_response)
        if code:
            self.transfer_to_editor_requested.emit(code)
            self.append_message("system", "[Code transferred to editor]")
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
            return

        # Handle external URLs (http/https)
        if url_str.startswith(("http://", "https://")):
            QDesktopServices.openUrl(url)

    def _handle_code_action(self, action: str, code: str, language: str):
        """Handle code block action (copy, insert, newtab)."""
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

    def _on_grid_click(self, slot: dict):
        if slot["type"] == "app" and "url" in slot:
            QDesktopServices.openUrl(QUrl(slot["url"]))
        elif slot["type"] == "prompt" and "prompt" in slot:
            self._on_prompt_click(slot)

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
        msg_html = f'<p style="margin: 5px 0; line-height: 1.5;">{marker} <span style="color: {color}; font-size: 11px;">{escaped_text}</span></p>'
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
        self.ai_manager.generate(self.current_model["id"], prompt, context)

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
            # Add "Continue" link after response
            continue_html = (
                '<p style="margin: 8px 0 5px 0;">'
                '<a href="action:continue" style="color: #7fbf8f; text-decoration: none; '
                'font-size: 11px;">▶ Continue generating...</a></p>'
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
            f'<span style="color: {color}; font-size: 11px;">{formatted_text}</span></p>'
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

    def _apply_theme(self):
        """Apply Metropolis Art Deco theme."""
        bg = "#1a2a2a"
        text_main = "#b4d2be"
        text_dim = "rgba(180,210,190,0.45)"
        text_dimmer = "rgba(180,210,190,0.35)"
        accent = "#7fbf8f"

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg};
                color: {text_main};
                font-family: 'Consolas', 'SF Mono', monospace;
            }}
        """)

        # Header accent (zigzag pattern)
        self.header_accent.setStyleSheet("""
            QLabel {
                color: rgba(180,210,190,0.35);
                font-size: 14px;
                font-weight: bold;
                padding: 8px 12px 0;
                letter-spacing: 0px;
                background: transparent;
            }
        """)

        # Door button (larger)
        self.door_btn.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                border: none;
                color: {text_dim};
                font-size: 22px;
                padding: 4px;
            }}
            QToolButton:hover {{
                color: {text_main};
            }}
        """)

        # Context buttons
        for btn in self.context_buttons:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    color: {text_dimmer};
                    font-size: 11px;
                    padding: 3px 8px;
                    border-radius: 2px;
                    letter-spacing: 0.05em;
                }}
                QPushButton:checked {{
                    color: {text_main};
                    background: rgba(180,210,190,0.08);
                }}
                QPushButton:hover {{
                    color: {text_main};
                }}
            """)

        # Chat area
        self.chat_area.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {bg};
                color: {text_main};
                border: none;
                padding: 8px 16px;
                font-size: 11px;
            }}
        """)

        # Prompts toggle
        self.prompts_toggle.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: rgba(180,210,190,0.4);
                font-size: 11px;
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

        # Prompt chips
        for btn in self.prompt_buttons:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    color: {text_dim};
                    font-size: 11px;
                    padding: 3px 7px;
                    border-radius: 2px;
                    letter-spacing: 0.02em;
                }}
                QPushButton:hover {{
                    color: {text_main};
                    background: rgba(180,210,190,0.08);
                }}
            """)

        # Grid label
        self.grid_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.1em;
                text-transform: uppercase;
                color: rgba(180,210,190,0.4);
                background: transparent;
            }
        """)

        # Grid buttons
        for btn in self.grid_buttons:
            if btn.property("filled"):
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        border: 1px solid rgba(180,210,190,0.1);
                        border-radius: 3px;
                        color: rgba(180,210,190,0.6);
                        font-size: 11px;
                        padding: 4px;
                    }}
                    QPushButton:hover {{
                        color: {text_main};
                        background: rgba(180,210,190,0.08);
                    }}
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: 1px dashed rgba(180,210,190,0.12);
                        border-radius: 3px;
                        color: rgba(180,210,190,0.18);
                        font-size: 16px;
                        font-weight: 300;
                        padding: 4px;
                    }
                    QPushButton:hover {
                        border-color: rgba(180,210,190,0.25);
                        color: rgba(180,210,190,0.35);
                    }
                """)

        # Model button
        self.model_btn.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                border: none;
                color: rgba(180,210,190,0.4);
                font-size: 11px;
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
                font-size: 11px;
            }}
            QMenu::item {{
                color: rgba(180,210,190,0.6);
                padding: 6px 12px;
                font-size: 11px;
            }}
            QMenu::item:selected {{
                color: {text_main};
                background: rgba(180,210,190,0.08);
            }}
        """
        if self.model_btn.menu():
            self.model_btn.menu().setStyleSheet(menu_style)

        # Input row background
        self.input_row_widget.setStyleSheet("""
            QWidget {
                background: rgba(180,210,190,0.04);
                border-radius: 3px;
            }
        """)

        # Input field
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #c8e0ce;
                font-size: 11px;
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
