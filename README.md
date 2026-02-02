# MyNotion

A lightweight text and code editor built with Python and PyQt6, featuring syntax highlighting, multiple themes, and planned local AI integration.

## Features

- **Multi-tab editing** — Open and edit multiple files simultaneously
- **Syntax highlighting** — Python, JavaScript, JSON, HTML, CSS, Markdown
- **Color themes** — Dark (default), Monokai, Dracula, Light, Nord
- **Customizable fonts** — Choose font family and size (Consolas 12 by default)
- **Line numbers** — With current line highlighting
- **Recent files** — Quick access to recently opened files
- **Zoom** — Ctrl+Plus/Minus to adjust font size

## Screenshots

*Coming soon*

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
| Ctrl+Plus | Zoom in |
| Ctrl+Minus | Zoom out |
| Ctrl+, | Settings |

### Changing Theme

Go to **Edit > Settings** or press `Ctrl+,` to open the settings dialog. Select your preferred theme and font settings.

## Project Structure

```
src/
├── main.py              # Entry point
├── app.py               # QApplication setup
├── ui/                  # UI components
│   ├── main_window.py   # Main window with tabs, menus, toolbar
│   ├── editor_tab.py    # Individual editor tab widget
│   ├── custom_tab_bar.py # Styled tab bar with close buttons
│   └── settings_dialog.py # Settings UI
├── core/                # Core functionality
│   ├── settings.py      # App settings (QSettings wrapper)
│   └── recent_files.py  # Recent files tracking
├── ai/                  # Local AI integration (planned)
└── syntax/              # Syntax highlighting
    └── highlighter.py   # QSyntaxHighlighter implementations
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

### Tools used

- **ruff** — Linting and formatting
- **mypy** — Type checking
- **pytest** — Testing with pytest-qt for widget tests

## Roadmap

- [ ] Find & Replace functionality
- [ ] Unsaved changes warning on close
- [ ] Local AI integration (Ollama)
- [ ] File tree sidebar
- [ ] Split view editing

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
