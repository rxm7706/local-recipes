---
name: "2026-11-05-operator-ruling-mason-story-25-19-spec-pyforge-ma"
description: "2026-11-05 operator ruling (mason Story 25.19, spec-pyforge-mason CAP-35): 'Exempt it by name'. recipes/ydata-quality k…"
metadata:
  type: project
---

2026-11-05 operator ruling (mason Story 25.19, spec-pyforge-mason CAP-35): 'Exempt it by name'. recipes/ydata-quality keeps its true cfe-local-build-status: failed and is exempt by name from CAP-35's grep, because upstream requires python <3.9, pip refuses it on the 3.11 floor, rules 4 and 5 of the python version policy forbid a lower python_min, and the field is never hand-written. It names one recipe and sets no class: any other in-scope failed record still breaks the clause.
