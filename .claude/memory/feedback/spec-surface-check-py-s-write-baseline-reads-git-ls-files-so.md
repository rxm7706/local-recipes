---
name: "spec-surface-check-py-s-write-baseline-reads-git-ls-files-so"
description: "spec_surface_check.py's --write-baseline reads git ls-files, so new files must be git add'ed BEFORE stamping or the bas…"
metadata:
  type: feedback
---

spec_surface_check.py's --write-baseline reads git ls-files, so new files must be git add'ed BEFORE stamping or the baseline silently omits them despite reporting success. Found via PR #486 (2026-08-14): a new file's baseline entry went missing for two PRs before a later spec-surface-check run caught it. Always git add new files before running --write-baseline; when reviewing a stamp, spot-check that new files actually appear in scripts/.spec-surface-baseline.json.
