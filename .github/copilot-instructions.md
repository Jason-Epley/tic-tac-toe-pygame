The repo is a small Pygame Tic-Tac-Toe project implemented as a single Python script and an assets directory. This file gives focused, actionable guidance for AI coding agents working here.

Key facts
- The primary gameplay code lives in `TicTacToe_Python_Capstone_Project_1.py` (monolithic script).
- Game assets are under `assets/sounds/` (sound files) and referenced by sound keys in the script.
- README.md mentions `main.py`, but the actual runnable script in this workspace is `TicTacToe_Python_Capstone_Project_1.py`. Use that as the entry point unless the repo is reorganized.

Run / debug quickly (Windows PowerShell)
```powershell
# Run the game from the repo root
python TicTacToe_Python_Capstone_Project_1.py
```

Important patterns and places to look (quick links)
- Sound initialization: `init_sounds()`, `safe_load_sound_by_name()`, `play_sound(key, rel_volume)` — search for these names to trace audio flow.
  - Expected sound keys in the code: move, move_ai, win, draw, menu_select, lose, bgm (the code also supports a 'click' key but it is mapped to `menu_select` at runtime).
  - Note: `assets/sounds/` contains: bgm.ogg, draw.wav, lose.wav, menu_select.wav, move.wav, move_ai.wav, win.wav — there is no separate `click.wav`. The runtime maps `SOUNDS['click']` to `SOUNDS['menu']` so agents can safely use `menu_select`.
- Settings persistence and UI: `load_settings()`, `save_settings()`, `settings_screen()` — these manage color presets, volume sliders and saving state.
- Main loops and screens: `menu_loop()`, `play_one_game()` — these contain the Pygame event loops and are the best places to change flow or add telemetry.
- AI logic: `ai_move_easy()`, `ai_move_hard()`, `minimax()`, `evaluate()` — contained in the same file; edits here affect game difficulty directly.
- Win detection: `get_winning_line(player_mark)`, `check_win()` and visual helpers `draw_winning_line()` / `draw_pulsing_circles()`.

Project-specific conventions (do not assume typical multi-module layout)
- Single-file implementation: prefer minimal, local edits and avoid large-scale reorganization unless asked. The codebase expects constants (WIDTH, HEIGHT, BOARD_ROWS, etc.) defined near the top — reference them rather than hard-coding numbers.
- Sounds are referenced by a short key string (e.g. `play_sound('menu_select')`). Update the `SOUNDS` dict via `init_sounds()` when adding/removing keys.
- Volume slider logic throttles the click sound: `_VOLUME_CLICK_THROTTLE_MS` and `_last_volume_click_time` are used to ensure a single click sound while dragging. Keep changes compatible with that pattern if modifying the settings UI.
- Settings UI uses relative slider positions and `rgb_to_rels()` / `rels_to_rgb()` helpers; mutations update globals like `X_COLOR`, `O_COLOR`, `BG_COLOR`, `EFFECT_VOLUME`, `MUSIC_VOLUME` directly.

Safe edit guidance
- Preserve Pygame event loop timing; the project uses `clock.tick(60)` in screens — keep 60 FPS logic unless changing the whole UI.
- When adding files (new modules), update README and prefer adding a small runner that imports the new module rather than renaming the existing script.
- Avoid large stylistic reformatting; changes should be minimal and behavior-preserving.

Useful examples to reference in edits
- Volume click throttle (do not duplicate): see `_VOLUME_CLICK_THROTTLE_MS = 140` and the related checks around `play_sound('menu_select')` inside the settings screen.
 - Sound key list used for verification: the code sets `expected_files = ["move", "move_ai", "win", "draw", "menu_select", "lose", "bgm"]` — update this list if you add or remove sound assets. The code also maps `SOUNDS['click'] = SOUNDS.get('menu')` for backwards compatibility.
- AI: `ai_move_easy()` chooses a random empty cell; `ai_move_hard()` uses `minimax()` and `evaluate()` (look for the `best_score` loop when modifying difficulty behavior).

Notes for PRs and tests
- There are no automated tests in the repo. For changes that alter UI or game rules, provide a short manual test checklist in the PR description (entry command, expected behavior, how to exercise the change).
- If you add a new sound file, place it in `assets/sounds/` and add its key to the expected list used by `init_sounds()`.

If anything is unclear or you want the repository refactored into modules (e.g., `game.py`, `ui.py`, `ai.py`), ask before performing a big rewrite — I can help split it safely and wire up a small test harness.

Ask me which part of the file to cite if you need in-line examples (e.g. the volume slider handling or minimax search loop).
