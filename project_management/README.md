# Project Management — PACMAN42

Evidence for how the project was driven (subject §VIII). Team: `jreibel`, `tbelard`.

## Method

- **Git flow:** one short-lived branch per feature or fix (`feat/…`, `fix/…`),
  merged into `main` through pull requests. Small, focused commits.
- **Tracking:** GitHub issues + the PR list act as the backlog and the changelog.
- **Definition of done:** `make lint-strict` clean, the feature demoed in the
  running game, and reviewed by the other member on the PR.

## Task split

| Area | Owner |
|---|---|
| Maze loader + `Convert` (A-Maze-ing integration) | `tbelard` |
| Ghost AI, state machine, speed tables | `jreibel` |
| Rendering, menus, HUD, animations | shared |
| Config parser, highscores | `tbelard` |
| Packaging (PyInstaller / itch.io), LAN mode | `jreibel` |

_(Adjust to match reality before the defense.)_

## Timeline

| Phase | Target | Status |
|---|---|---|
| Maze generation + display | week 1 | done |
| Player + ghosts + collisions | week 2 | done |
| Levels, scoring, UI (menus / HUD / game-over / victory) | week 3 | done |
| Config, highscores, cheat mode, polish | week 4 | done |
| Packaging + itch.io deployment | week 4 | packaging done, upload pending |

## Risk analysis

| Risk | Impact | Mitigation |
|---|---|---|
| Assigned A-Maze-ing package changes / is reinstalled at review | high | Loader only touches the public `.maze` interface; failures wrapped in `MazeGenError`, the game exits with a clear message |
| Config format differs at the defense | high | Parser accepts standard JSON + comments + trailing commas; every bad value falls back to a default, never a traceback |
| 42-VM network isolates the two machines (LAN mode) | medium | `can_reach_host` pre-check; LAN is a bonus, solo is unaffected |
| PyInstaller build ships without assets / wrong paths | medium | `pacman.spec` bundles the asset trees; `pac-man.py` `chdir()`s into the bundle; verified with a smoke run |
| Window close crashing a menu (`no crash!`) | high | `GameExit` raised from every event loop, caught in `Game.monitor` |

## Acceptance test plan

| Feature | How tested | Result |
|---|---|---|
| Faulty config: missing file, bad type, out-of-range, unknown key, `//` comments | crafted `.json` files | defaults / clamp / ignore, no traceback |
| Highscore persistence, name validation, top-10 trim | play → enter name → restart; 12+ entries | keeps best per name, file capped at 10 |
| Level progression 1→10 and victory screen | cheat mode `Space` to skip each level | 10 levels playable, victory on level 10 |
| Game over (0 lives / timeout) shows final score + name prompt | lose on purpose / wait out the timer | score shown, prompt shown, back to menu |
| Ghost states (scatter / chase / frightened / eyes / Elroy) | observe after a super-pac-gum and late-level | matches the arcade behaviour |
| Window close from every screen | click the ✕ on menu / pause / highscores / name entry | clean exit, no traceback |
| Packaged build launches with all assets | `make package` then run `dist/PACMAN42/PACMAN42` | menu + gameplay OK |

## Blocking points

- **Parser too strict** — the first version only accepted one exact file layout
  and Python-literal booleans. Rewritten around `json.loads` + a comment/trailing
  comma pre-pass.
- **Merge regression** — a lint cleanup on `main` changed two function
  signatures without updating every caller, breaking gameplay and
  `make lint-strict`. Fixed and covered by a headless smoke test.
- **`update_tile` signature** — adding a forced-direction parameter for the
  intermission broke the per-frame callers; resolved with a default value.
