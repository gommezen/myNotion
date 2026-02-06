# MyNotion - TODO & Changelog

## Next Up (Priority)

- [ ] **Create GitHub release for v0.2.0** - Publish release notes on GitHub
  - Use `gh release create v0.2.0` with changelog (packaging, editor fixes, AI tests)

- [ ] **Align AI prompts with model selector** - Fine-tune left-alignment of "AI Prompts" toggle and model selector text
  - See design_decisions.pdf page 3 for reference layout
  - Reduced input_layout left margin from 16→12 to compensate for QToolButton internal padding
  - May need further pixel adjustment after visual review

## Recently Completed

- [x] **Startup theme flash fixed** - Editor panel no longer flashes wrong background on launch
  - Moved `_apply_theme()` to after all UI widgets are constructed
  - Added `_apply_child_themes()` for explicit theme cascade to all widgets
  - Added QDockWidget and QMainWindow::separator styling

- [x] **Session restore** - Reopens tabs from last session on launch
  - Saves file paths, cursor positions, and scroll state on exit
  - Restores tabs automatically on startup
  - Handles missing files gracefully

- [x] **Auto-save** - Periodic automatic saving with settings UI
  - Configurable interval (10s–300s) in Settings dialog
  - Saves on window focus loss
  - Status bar notification on auto-save
  - Themed checkbox with X mark indicator

- [x] **Font size increase** - Menu bar and toolbar text bumped +2px
  - Menu bar (File, Edit, View): 11px → 13px
  - Menu dropdowns: 11px → 13px
  - Formatting toolbar (H1, B, I, etc.): 10px → 12px

- [x] **Writing mode font consistency** - Prompt buttons now use explicit Consolas font
  - Fixed font inheritance issue when switching layout modes

- [x] **Centered formatting toolbar** - Notepad-style toolbar inline with menu bar
  - H1 dropdown, Lists dropdown, Bold, Italic, Link, Table, Clear formatting
  - Centered between File/Edit/View menus using custom header layout
  - All buttons insert markdown syntax, clear button strips it

- [x] **Theme-aware UI panels** - All panels update when switching themes
  - Side panel, file browser, activity bar, tab bar read from current theme
  - Settings dialog styled to match current theme
  - Windows title bar color via DWM API
  - Header bar background matches menu bar across themes

- [x] **Unified selection color** - Teal (#1A5050) across all six themes
  - Clear, consistent text selection highlight in all modes

- [x] **AI text wrapping** - Word-wrap AI responses at 60 chars before inserting
  - Preserves code, lists, headings; only wraps prose lines
  - Applied to Insert, New Tab, Copy, and Replace text actions

- [x] **Theme menu styling** - Settings dialog matches current theme
  - Buttons, combos, inputs all use theme colors
  - Preview border uses theme chrome border

- [x] **Chat Options Menu** - "+" button in chat input with popup menu
  - Active Tab context toggle (include/exclude editor content)
  - Add to project folder (active tab / all tabs)
  - Research mode (switches to Claude 3 Haiku)
  - Metropolis themed dropdown styling

- [x] **Anthropic API Integration** - Claude 3 Haiku support
  - New provider: src/ai/providers/anthropic.py
  - API key storage in Settings dialog
  - Auto-routing based on model selection
  - Streaming responses

- [x] **Open Folder** - Project folder selection
  - File menu → Open Folder (Ctrl+Shift+O)
  - 📁 button in file browser header
  - Sets root path for file tree

- [x] **Layout Modes** - Coding Mode and Writing Mode for different workflows
  - **Coding Mode**: Code-focused prompts (Explain, Docstring, Simplify, Debug, Fix, Refactor, Test)
  - **Writing Mode**: Prose-focused prompts (Summarize, Improve, Translate, Expand, Tone, Shorten)
  - Translate shows language picker dialog (15+ languages)
  - Tone shows tone picker dialog (Professional, Casual, Friendly, etc.)
  - Text action buttons (Copy | Insert | New Tab | Replace) for writing responses
  - Auto-switch to default model per mode
  - Different system prompts for coding vs writing
  - View menu → Layout Mode submenu
  - Ctrl+Shift+M to toggle between modes
  - Mode persists across sessions

- [x] **Beacon Logo** - New Art Deco beacon icon (concept F)
  - Radiating diamond with geometric rays
  - Updated SVG and ICO files

- [x] **Menu Hover Colors** - Improved visibility
  - Menu items use visible teal hover
  - AI prompt buttons match model menu style

- [x] **Auto-Model Routing** - Smart model selection for AI prompts
  - Quick tasks (Explain, Docstring, Simplify) → lightweight model
  - Deep tasks (Debug, Refactor, Fix) → heavier model
  - Manual model selection overrides auto-routing
  - Configurable routing table in side_panel.py

- [x] **Find & Replace** - Search and replace bar (Ctrl+F)
  - Match count, navigation, replace all
  - Match case option
  - Metropolis themed

- [x] **Unsaved Changes Warning** - Themed prompts before losing work
  - Tab title shows `*` when modified
  - Warning on tab close / window close
  - Save / Discard / Cancel options
  - Styled dialog matching Metropolis theme

- [x] **File Tree Sidebar** - VS Code-style activity bar
  - Activity bar with AI and Files icons
  - File browser panel with tree view
  - Collapse/expand with background color change
  - Gold focus border on AI chat input

- [x] **UI Polish**
  - Status bar text color aligned with theme
  - Separator lines around line numbers
  - Simplified README

- [x] **AI Panel Redesign** - Card-style prompts with icons
  - Removed Quick Actions grid (not needed)
  - Added unique icons to each AI prompt (◎ ☰ ◇ ⚡ etc.)
  - 2-column card layout with teal borders
  - Updated model list to installed Ollama models
  - Qwen 2.5 set as default model

- [x] **Tab Styling Improvements**
  - Gold top accent on active tab
  - Better contrast: inactive tabs darker and dimmer
  - Clean Notepad-style cursor (no line highlight)

- [x] **Font Size Updates**
  - Menu bar, tabs, status bar: 11px
  - AI prompt cards: 12px

- [x] **AI Prompts work on editor selection** - Prompts now use selected text from editor
  - Context flows from editor → main window → side panel → AI
  - Falls back to full file content if no selection
  - Code-modifying prompts (Improve, Fix, Simplify, etc.) show "Replace" button
  - "Replace" replaces the original selection with AI-generated code
  - Tooltips on hover explain each prompt's function
  - Concise system prompt for shorter AI responses

## Bugs to Fix

### High Priority
- [x] ~~**Font size -1 error**~~ - Fixed via Qt message handler to suppress cosmetic warning
  - Root cause: Qt internal font handling, not our code
  - Solution: `qInstallMessageHandler()` in `src/app.py` filters the warning

## Planned Features

### AI prompts
- [x] **AI Prompts** - Add AI prompts to the AI panel
  - [x] **Explain** - Explain the selected text
  - [x] **Docstring** - Add docstrings to code
  - [x] **Simplify** - Simplify the code
  - [x] **Debug** - Find bugs in the code
  - [x] **Examples** - Generate more code examples
  - [x] **Transfer** - Transfer code to editor
  - [x] **Summarize** - Summarize the selected text
  - [x] **Fix** - Fix the selected text
  - [x] **Improve** - Improve the selected text
  - [x] **Translate** - Translate code to another language
  - [x] **Refactor** - Refactor the selected text
  - [x] **Test** - Generate tests for the selected text
  - [x] **Custom** - Custom prompt via dialog

### Core Features
- [x] **Find & Replace** - Search and replace functionality
  - Ctrl+F / Ctrl+H opens find bar
  - Match count display
  - Previous/Next navigation
  - Replace / Replace All
  - Match case option
  - Themed to match Metropolis style

- [x] **Unsaved Changes Warning** - Prompt before losing work
  - Track document modified state
  - Warn on tab close with unsaved changes
  - Warn on window close with any unsaved tabs
  - Option to save all / discard all
  - Themed dialog matching Metropolis style

### AI Integration
- [x] **Local AI Assistant** - Connect to local AI models
  - [x] Ollama integration with streaming responses
  - [x] Code block formatting with syntax highlighting
  - [x] Copy/Insert/New Tab actions on code blocks
  - [x] Continue generating feature
  - [x] Stop generation button
  - [x] Default system prompt for better responses
  - [ ] Text completion/suggestions

- [x] **Layout Modes** - Coding Mode and Writing Mode with different AI prompts
  - Coding Mode: Explain, Docstring, Simplify, Debug, Fix, Refactor, Test
  - Writing Mode: Summarize, Improve, Translate, Expand, Tone, Shorten
  - Ctrl+Shift+M toggle, View menu, persisted settings

### UI/UX Improvements
- [x] Default font Consolas size 12
- [x] Dropdown for font-size (replaced spinbox)
- [x] Metropolis theme (Art Deco inspired)
- [x] Clean tab bar styling (gold accent on active, dimmer inactive)
- [x] Tab fade transition on switch
- [x] Removed zigzag header and context buttons from AI panel
- [x] AI prompts with icons (card-style layout)
- [x] Removed Quick Actions grid
- [X] Tab reordering - Drag tabs to reorder

### Nice to Have
- [x] GitHub repository setup (https://github.com/gommezen/myNotion)
- [x] **Auto-save** - Periodic automatic saving
- [x] **Session restore** - Reopen tabs from last session
- [ ] **Split view** - View two files side by side
- [ ] **Minimap** - Code overview on the side
- [x] **File tree sidebar** - Browse project files (VS Code-style activity bar)
- [ ] **Multiple cursors** - Edit multiple locations at once
- [ ] **Code folding** - Collapse code blocks
- [ ] **Bracket matching** - Highlight matching brackets
- [ ] **Auto-indent** - Smart indentation
- [ ] **Line operations** - Move/duplicate/delete lines

## Completed Features

### v0.1.0 (Current)

**Editor Features:**
- [x] Tabbed interface with close buttons (X)
- [x] New tab button (+) positioned inline with tabs
- [x] File menu (New, Open, Save, Save As, Recent Files, Exit)
- [x] Edit menu (Undo, Redo, Cut, Copy, Paste)
- [x] View menu (Zoom In/Out, Language selection, Settings)
- [x] Syntax highlighting (Python, JavaScript, HTML, CSS, JSON, Markdown)
- [x] Dark theme matching Windows Notepad
- [x] Settings dialog (theme selection, font family, font size)
- [x] Line numbers in editor
- [x] Status bar (position, character count, language, zoom, line ending, encoding)
- [x] Bold/Italic toolbar buttons (markdown syntax insertion)
- [x] Recent files tracking (up to 10 files)
- [x] Window geometry persistence
- [x] Multiple color themes (Dark, Monokai, Dracula, Light, Nord, Metropolis)
- [x] Custom styled tab bar with close buttons
- [x] Keyboard shortcuts for common operations
- [x] Default font Consolas 12pt
- [x] Font size dropdown in settings

**Development Infrastructure:**
- [x] Project documentation (.claude/ folder)
- [x] pyproject.toml with ruff, mypy, pytest config
- [x] requirements-dev.txt for dev dependencies
- [x] Quality check scripts (Windows batch + bash)
- [x] Test infrastructure with pytest-qt fixtures
- [x] Mock AI client fixtures for future testing
- [x] Isolated settings for tests (don't touch real config)
- [x] GitHub repository with README
- [x] Theme test file (examples/theme_test.py)
