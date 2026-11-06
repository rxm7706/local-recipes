---
name: "2026-11-05-operator-ruling-on-n1-dw-steward-egm-2026-11-05-1"
description: "2026-11-05 operator ruling on N1 (DW-steward-egm-2026-11-05-1): 'honest runner first then wire to cli'. First half is s…"
metadata:
  type: project
---

2026-11-05 operator ruling on N1 (DW-steward-egm-2026-11-05-1): 'honest runner first then wire to cli'. First half is steward Story 21.6, PR #2368: the seven start runners raise RunnerNotWiredError, so the run ends FAILED and says nothing ran. The worker records that refusal and does not re-raise it, because CELERY_TASK_EAGER_PROPAGATES would otherwise cost the caller the handle. Second half is DW-steward-21-6-2: it needs a capability, an allowlist of verbs per face and a check of what the host image can run, because a worker subprocess sits outside the session hook. Story 29.5 recompiles the skills after 21.6 lands.
