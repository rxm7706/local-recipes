---
name: "2026-11-21-operator-ruling-on-dw-steward-126-3-1-steward-s-c"
description: "2026-11-21 operator ruling on DW-steward-126-3-1 (steward's corridor duties load/passport/quarantine/glass have no conf…"
metadata:
  type: project
---

2026-11-21 operator ruling on DW-steward-126-3-1 (steward's corridor duties load/passport/quarantine/glass have no configured Django project): 'Platform host'. The django-steward portal package installs pyforge.steward.dashboard into the platform host, so the corridor tables migrate into the platform's PostgreSQL 17 (the Dream's 'existing Postgres app', CAP-141); src/platform still never imports pyforge.* -- the portal package reaches station code, as django-mason's does. Rejected: a settings module in the pyforge-steward env (a second migration owner or a database apart from the platform). Same day: the operator files the pixi global-trampoline non-UTF-8 panic upstream (prefix-dev/pixi) from their own terminal; agents never write to other repositories.
