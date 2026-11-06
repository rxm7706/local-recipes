---
name: "2026-11-05-operator-ruling-mason-story-25-23-dw-mason-25-22"
description: "2026-11-05 operator ruling (mason Story 25.23, DW-mason-25-22-3): 'Retire reactpy-django'. The identity mirror replaced…"
metadata:
  type: project
---

2026-11-05 operator ruling (mason Story 25.23, DW-mason-25-22-3): 'Retire reactpy-django'. The identity mirror replaced the local-only reactpy 2.0.0b13 with the feedstock's 1.1.0, so reactpy-django 6.0.0b1, which pins reactpy >=2.0.0b13 and has no feedstock, could not solve. recipes/reactpy-django and the reactpy v2 patch are gone, in git history; reactpy stays at the published version. The ruling covers that one recipe: reactpy-router 3.0.0b1 stays and is deferred.
