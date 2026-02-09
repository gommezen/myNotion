# MyNotion — TODO

## Next Up

- [x] **Refactor `main_window.py` (2515 → 1415 lines)** — Extracted 5 focused classes:
  1. [x] `StatusBarManager` — status bar setup and updates (~80 lines)
  2. [x] `InlineEditController` — Ctrl+K inline AI edit system (~190 lines)
  3. [x] `CompletionController` — AI code completion toggle, model selection (~130 lines)
  4. [x] `ThemeEngine` — all QSS generation and theme application (~410 lines) + centralized `hex_to_rgba`
  5. [x] `TitleBarController` — custom title bar, min/max/close, drag, resize grips (~270 lines)

- [ ] **Review `side_panel.py` (1537 lines)** — Identify extraction candidates after main_window is done

## Planned Features