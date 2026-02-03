"""
AI Chat Panel with Metropolis Art Deco design.
Based on ai-panel-redesign-v2_1.jsx — exact 1:1 implementation.
"""

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
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

from core.settings import SettingsManager

# ─── Data ───
MODELS = [
    {"id": "glm-4.7-flash:latest", "name": "GLM 4.7 Flash", "tag": "19GB"},
    {"id": "llama3.1", "name": "Llama 3.1", "tag": "8B"},
    {"id": "codellama", "name": "Code Llama", "tag": "7B"},
    {"id": "mistral", "name": "Mistral", "tag": "7B"},
    {"id": "gemma2", "name": "Gemma 2", "tag": "9B"},
    {"id": "deepseek-coder", "name": "DeepSeek", "tag": "6.7B"},
    {"id": "bge-m3:latest", "name": "BGE M3", "tag": "1.2GB"},
    {"id": "mxbai-embed-large:latest", "name": "MxBAI Embed", "tag": "Large"},
]

# Grid slots: assigned actions + empty placeholders
# type: "app" for shortcuts, "prompt" for AI actions, None for empty
INITIAL_GRID = [
    {"id": 1, "type": "app", "label": "gmail", "icon": "✉", "url": "https://mail.google.com"},
    {"id": 2, "type": "app", "label": "claude", "icon": "◈", "url": "https://claude.ai"},
    {"id": 3, "type": "prompt", "label": "explain", "icon": "✦", "prompt": "Explain this code"},
    {"id": 4, "type": None, "label": None, "icon": None},
    {"id": 5, "type": None, "label": None, "icon": None},
    {"id": 6, "type": None, "label": None, "icon": None},
]

# AI-specific quick prompts (inline row above grid)
AI_PROMPTS = [
    {"label": "Explain", "prompt": "Explain this code"},
    {"label": "Docstring", "prompt": "Add docstrings"},
    {"label": "Simplify", "prompt": "Simplify this"},
    {"label": "Debug", "prompt": "Find bugs"},
    {"label": "Summarize", "prompt": "Summarize"},
    {"label": "Refactor", "prompt": "Refactor this"},
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_manager = SettingsManager()
        self.current_model = MODELS[0]
        self.context_mode = "selection"
        self.prompts_visible = True
        self._setup_ui()
        self._apply_theme()

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
        self.chat_area.setOpenExternalLinks(True)
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
        self.append_message("user", prompt["prompt"])
        self.quick_action_triggered.emit(prompt["prompt"])
        self.append_message("ai", f"Processing with {self.current_model['name']}...")

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
            self.append_message("ai", f"Processing with {self.current_model['name']}...")

    def append_message(self, role: str, text: str):
        if role == "user":
            marker = '<span style="color: #7fbf8f; font-size: 7px;">◆</span>'
            color = "#c8e0ce"
        else:
            marker = '<span style="color: rgba(180,210,190,0.35); font-size: 7px;">◇</span>'
            color = "rgba(180,210,190,0.6)"

        html = f'<p style="margin: 5px 0; line-height: 1.5;">{marker} <span style="color: {color}; font-size: 11px;">{text}</span></p>'
        self.chat_area.append(html)

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

