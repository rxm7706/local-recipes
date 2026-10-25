---
name: "a-generated-page-that-captures-a-cli-s-help-is-not-determini"
description: "A generated page that captures a CLI's --help is not deterministic under harness environment variables: typer forces ri…"
metadata:
  type: feedback
---

A generated page that captures a CLI's --help is not deterministic under harness environment variables: typer forces rich's console whenever FORCE_COLOR, PY_COLORS or GITHUB_ACTIONS is set, and rich then returns 80 columns when TERM is dumb/unknown (ignoring COLUMNS) or, with any other TERM, keeps COLUMNS but writes ANSI styling into the capture (NO_COLOR removes colour, not bold/dim); on Python 3.14 PYTHON_COLORS=1 also colours argparse's own --help and outranks NO_COLOR. A generator must build the child env itself: scrub FORCE_COLOR, PY_COLORS, PYTHON_COLORS, CLICOLOR_FORCE, GITHUB_ACTIONS, TTY_COMPATIBLE and TERMINAL_WIDTH, pin COLUMNS and NO_COLOR (scripts/docs_station_cli.py::_help_env, marshal Story 103.1). Why: three dispatch passes committed an 80-column docs/reference/station-cheat-sheet.md that docs-station-cli --check from a plain shell read as stale, and the review sent the story back each time. How to apply: when a --check reds a generated page that was just regenerated, compare the rendering environments before re-rendering; assert the scrub by literal variable name in the generator's test.
