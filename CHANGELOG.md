# Changelog

All notable changes to MyNotion are documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [1.0.0] - 2026-02-09

### Added
- Copilot-style inline code completion with FIM support (Tab to accept, Esc to dismiss)
- Ctrl+K inline AI editing with live diff preview
- DeepSeek Coder 1.3B added to model menu
- Test coverage for theme engine, find/replace, and file browser (58 new tests)
- File I/O error handling with user-friendly messages
- Configurable Ollama host address
- Large file guard (syntax highlighting disabled for files over 1 MB)
- GitHub Actions CI (lint, type check, tests) and release workflow
- CHANGELOG, LICENSE, and README badges

### Changed
- Refactored main_window.py: extracted 5 focused controllers (2515 to 1415 lines)
- Redesigned inline edit bar (Beacon Pulse style)
- Polished UI: button feedback, tab shape, border-radius consistency
- Improved Anthropic error messages and status bar feedback
- Updated AI prompts

### Fixed
- Unicode handling in tests
- Mypy type errors in ai/ module and side_panel

## [0.2.0] - 2026-02-07

### Added
- Session restore on startup (reopens previous tabs)
- Auto-save with configurable interval and save-on-focus-loss
- Windows packaging with PyInstaller (build and install scripts)
- Comprehensive AI test suite (74 tests across 5 files)
- Tests for session restore and auto-save features
- Theme-aware Windows title bar color via DWM API
- Chat context toggle to include editor content in messages
- Chat options menu with Anthropic Claude API support
- Folder selection for file browser
- Layout modes: Coding Mode and Writing Mode
- Find & Replace with match highlighting (Ctrl+F)
- Unsaved changes warning on close
- Auto-model routing based on selected mode

### Changed
- Centered formatting toolbar
- Unified selection color across themes
- Settings dialog with theme preview
- Improved markdown rendering in AI chat
- Cleaned up toolbar layout

## [0.1.0] - 2026-02-02

### Added
- Multi-tab text and code editor built with PyQt6
- Syntax highlighting for Python, JavaScript, JSON, HTML, CSS, Markdown
- 7 color themes: Dark, Monokai, Dracula, Light, Nord, Metropolis, Win95 Dark
- Metropolis Art Deco theme as primary design language
- AI chat panel with Ollama integration (local models)
- Code block formatting with transfer-to-editor feature
- AI prompt buttons: Explain, Docstring, Debug, Fix, Refactor, Test
- Collapsible AI side panel
- Custom tab bar with close buttons
- Line numbers with current line highlighting
- File browser side panel
- Custom Beacon logo and icon
- Zoom controls (Ctrl+Plus/Minus)
- Recent files tracking

[Unreleased]: https://github.com/gommezen/myNotion/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/gommezen/myNotion/compare/v0.2.0...v1.0.0
[0.2.0]: https://github.com/gommezen/myNotion/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/gommezen/myNotion/releases/tag/v0.1.0
