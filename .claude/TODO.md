# MyNotion — TODO

## Next Up

- [ ] **Refactor `main_window.py` (2515 lines)** — Extract one piece at a time:
  1. [ ] `ThemeApplicator` — all QSS generation and theme application
  2. [ ] `TitleBarWidget` — custom title bar, min/max/close, drag handling
  3. [ ] `TabManager` — tab creation, `+` button positioning, session restore
  4. [ ] `StatusBarManager` — status bar setup and updates
  5. [ ] `InlineEditController` — Ctrl+K inline AI edit system
  6. [ ] `CompletionController` — AI code completion toggle, model selection
  7. [ ] Keep `MainWindow` as orchestrator wiring these together

- [ ] **Review `side_panel.py` (1537 lines)** — Identify extraction candidates after main_window is done

## Planned Features