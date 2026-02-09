# MyNotion


MyNotion a lightweight text and code editor with AI integration. Think notepad but with syntax highlighting, multiple themes, and local AI assistance via Ollama.


## Features

- **Multi-tab editing** — Open and edit multiple files with session restore
- **Syntax highlighting** — Python, JavaScript, JSON, HTML, CSS, Markdown, and more
- **7 color themes** — Dark (default), Monokai, Dracula, Light, Nord, Metropolis, Win95 Dark
- **Customizable fonts** — Choose font family and size (Consolas 12 by default)
- **Line numbers** — With current line highlighting
- **File browser** — Side panel for navigating project folders
- **Find & Replace** — Ctrl+F with match highlighting
- **Recent files** — Quick access to recently opened files
- **Auto-save** — Configurable interval, also saves on focus loss
- **Zoom** — Ctrl+Plus/Minus to adjust font size
- **Large file support** — Files over 1 MB open with syntax highlighting disabled for performance
- **AI Assistant** — Ollama (local) and Anthropic Claude (cloud)
  - Chat panel with streaming responses and code block actions
  - **Inline AI editing** (Ctrl+K) — Select code, describe the change, see a live diff
  - **Code completion** — Copilot-style ghost text via Ollama FIM models
  - Coding and writing modes with mode-aware prompts
  - Context toggle to include active editor content in chat

## Screenshots
![MyNotion Screenshot](docs/screenshot.png) 

## Installation

### Requirements

- Python 3.10+
- PyQt6

### Install from source

```bash
# Clone the repository
git clone https://github.com/gommezen/myNotion.git
cd myNotion

# Install dependencies
pip install -r requirements.txt

# Run the application
python src/main.py
```

### Build standalone executable (Windows)

```bash
pip install pyinstaller
pyinstaller --windowed --onefile --name MyNotion src/main.py
```

The executable will be in the `dist/` folder.

## Usage

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New file |
| Ctrl+O | Open file |
| Ctrl+S | Save |
| Ctrl+Shift+S | Save As |
| Ctrl+W | Close tab |
| Ctrl+F | Find & Replace |
| Ctrl+K | Inline AI edit |
| Ctrl+Plus | Zoom in |
| Ctrl+Minus | Zoom out |
| Ctrl+, | Settings |
| Tab | Accept ghost text completion |
| Escape | Dismiss ghost text / cancel inline edit |

### Changing Theme

Go to **Edit > Settings** or press `Ctrl+,` to open the settings dialog. Select your preferred theme and font settings.

### Theme Colors (Metropolis)

The Metropolis theme uses these green shades (lightest to darkest):

| Element | Variable | Hex |
|---------|----------|-----|
| Selection highlight | `selection` | `#1A5050` |
| Current line | `current_line` | `#1A3333` |
| Active tab / editor | `background` | `#1a2a2a` |
| Menu bar / toolbar | `chrome_bg` | `#121f1f` |

Theme colors can be customized in `src/core/settings.py`.

## Project Structure

```
src/
├── main.py                  # Entry point
├── app.py                   # QApplication setup, qasync event loop
├── ui/                      # UI components
│   ├── main_window.py       # Main window orchestrator
│   ├── editor_tab.py        # Editor widget with line numbers, ghost text
│   ├── side_panel.py        # AI chat panel (coding & writing modes)
│   ├── file_browser.py      # Project folder navigation
│   ├── activity_bar.py      # Left sidebar icon strip
│   ├── find_replace.py      # Find & Replace bar
│   ├── theme_engine.py      # QSS generation and theme application
│   ├── title_bar.py         # Custom frameless title bar
│   ├── status_bar_manager.py    # Status bar indicators
│   ├── inline_edit_controller.py # Ctrl+K inline AI edit lifecycle
│   ├── completion_controller.py  # Ghost text completion manager
│   ├── custom_tab_bar.py    # Styled tab bar with close buttons
│   ├── settings_dialog.py   # Settings UI
│   └── toolbar_widgets.py   # Toolbar button helpers
├── core/                    # Non-UI logic
│   ├── settings.py          # QSettings wrapper, theme definitions
│   └── recent_files.py      # Recent files tracking
├── ai/                      # AI integration
│   ├── worker.py            # Thread-safe AI manager
│   ├── completion.py        # FIM prompt builder for code completion
│   └── providers/
│       ├── ollama.py        # Ollama API client (local models)
│       └── anthropic.py     # Anthropic API client (Claude)
└── syntax/
    └── highlighter.py       # QSyntaxHighlighter per language
```

## Development

### Setup development environment

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Run tests

```bash
pytest tests/
```

### Quality checks

```bash
# Windows
scripts\quality_check.bat

# Git Bash / WSL / Linux / macOS
./scripts/quality_check.sh
```
