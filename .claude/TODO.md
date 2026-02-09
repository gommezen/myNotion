# MyNotion — TODO

## Next Up

- [ ] **Split `main_window.py` (~2300 lines)** — Extract into separate classes (see Refactoring)

## Done

- [x] **Beacon Pulse inline edit bar** — Ctrl+K bar redesigned: horizontal layout with ◈ icon, pulse animation during generation, green/red state indicators
- [x] **Inline Edit UI Concepts** - C:\Users\ITSMARTSOLUTIONS\Downloads\mynotion-inline-edit-concepts.jsx
- [x] **Polish settings menu** — Apply consistent border-radius (6px), button pressed states (gold accent), and theme-aware styling to the settings dialog
- [x] **Win95 Dark theme review** — Run `python src/main.py`, switch to Win95 Dark, compare against the playground (`mynotion-theme-playground.html`)

## finish (done)
- [x] **Fix ctrl+k** — Removed "Edit:" label, placeholder text is enough
- [x] **Fix closing the window** — Inline edit bar auto-closes when selection is lost
- [x] **Snap to screen** — Win+Arrow snapping via WS_THICKFRAME window style
- [x] **Help → Keyboard Shortcuts** — F1 shows themed shortcuts dialog
- [x] **Find/Replace close button styling** — Hover/pressed states on close button
- [x] **Settings collapsing** — Wrapped in QScrollArea, no more collapsing
- [x] **Settings button styling** — Gold accent on pressed state
- [x] **Language auto-switches layout mode** — .py/.js → Coding, .txt/.md → Writing (30s cooldown)
- [x] **AI prompts conciseness** — Explain (2-3 sentences), Docstring (code only), Debug (line refs), Fix (code only)

## Open items
- [x] **Settings dialog polish** — Font sizes set to 11px, buttons refined (subtle bg, border, gold press)
- [x] **AI response formatting** — `_format_plain_text()` converts `\n` → `<br>` for readable display
- [x] Ctrl+K still usable when AI completion is off — **By design**: Ctrl+K uses side panel model, independent of completion toggle
- [x] Examples button not useful for plain text — Writing mode now generates "alternative versions"; added Clear Chat action link
- [x] Custom mode returns text walls instead of acting on code — Wrapped with "Apply this instruction... Return ONLY the modified code/text"


## Refactoring


- [ ] **Split `main_window.py` (~2300 lines)** — Extract into separate classes (future):
  - `TitleBarWidget` — custom title bar, min/max/close, drag handling
  - `TabManager` — tab creation, `+` button positioning, session restore
  - `StatusBarManager` — status bar setup and updates
  - `InlineEditController` — Ctrl+K inline AI edit system
  - `CompletionController` — AI code completion toggle, model selection
  - `ThemeApplicator` — all QSS generation and theme application
  - Keep `MainWindow` as orchestrator wiring these together

## Planned Features

- [ ] Split view — View two files side by side
- [ ] Minimap — Code overview on the side
- [ ] Multiple cursors — Edit multiple locations at once
- [ ] Code folding — Collapse code blocks
- [ ] Bracket matching — Highlight matching brackets
- [ ] Auto-indent — Smart indentation
- [ ] Line operations — Move/duplicate/delete lines