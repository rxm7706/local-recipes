---
name: "2026-11-27-landed-the-estate-s-python-and-pixi-are-declared"
description: "2026-11-27 LANDED: the estate's Python and pixi are declared once and used everywhere. PR #2415 merged as e30f4cfa38 (M…"
metadata:
  type: project
---

2026-11-27 LANDED: the estate's Python and pixi are declared once and used everywhere. PR #2415 merged as e30f4cfa38 (Merge pyforge-steward/148-1 into main; steward Stories 148.1 to 148.3, warden 34.1). pixi.toml declares Python once, [feature.interpreter.dependencies] python = "3.14.10.*", and all 36 environments compose it; the lock holds 3.14.10 in all 87 environment-platform pairs (pyforge-marshal is off 3.15.0). Every pixi pin site is 0.85.0, mason's engine floor is a registered site, all 41 setup-pixi steps are v0.11.3, and the osx-arm64 entry uses subdir. Workflows set Python up only through .github/actions/setup-estate-python, which reads the declaration (CI ran CPython 3.14.10). target-version-check holds the declaration, the environments, the lock and the workflows. pin-policy.yaml holds python once, on the interpreter feature; nodejs keeps its LTS pin and pyforge-steward carries it. Warden's fix-PR pixi range is >=0.85.0,<0.86. The operator's pixi is 0.85.0. To move Python: change the one line in pixi.toml and re-lock with the pinned pixi. To move pixi: run bump-pixi-version under the new pixi, re-lock, then move warden's PIXI_VERSION_RANGE ceiling and its contract row by hand.
