# MyNotion — TODO

## Next Up

- [ ] **Win95 Dark theme review** — Run `python src/main.py`, switch to Win95 Dark, compare against the playground (`mynotion-theme-playground.html`)


## Refactoring

- [ ] **Split `main_window.py` (~2300 lines)** — Extract into separate classes:
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