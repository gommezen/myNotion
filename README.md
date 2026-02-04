# MyNotion

A lightweight text and code editor built with Python and PyQt6, featuring syntax highlighting, multiple themes, and local AI integration via Ollama.

## Features

- **Multi-tab editing** with syntax highlighting (Python, JavaScript, JSON, HTML, CSS, Markdown)
- **Color themes** — Dark, Monokai, Dracula, Light, Nord, Metropolis
- **AI Assistant** — Local AI via Ollama with prompts for code explanation, debugging, refactoring, and more
- **File browser** — VS Code-style sidebar for navigating project files
- **Customizable** — Fonts, themes, and editor settings

## Installation

**Requirements:** Python 3.10+

```bash
git clone https://github.com/gommezen/myNotion.git
cd myNotion
pip install -r requirements.txt
python src/main.py
```

### Build executable (Windows)

```bash
pip install pyinstaller
pyinstaller --windowed --onefile --name MyNotion src/main.py
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New file |
| Ctrl+O | Open file |
| Ctrl+S | Save |
| Ctrl+Shift+S | Save As |
| Ctrl+W | Close tab |
| Ctrl+Plus/Minus | Zoom in/out |
| Ctrl+, | Settings |

## License

MIT License
