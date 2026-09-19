"""pyforge.steward.dashboard — Epic 9's secure-live-dashboards foundation.

Story 9.1: identity extraction at the ASGI boundary (`middleware.py`), the
declaration schema an adopter fills in instead of hand-writing filtering
(`declarations.py`), and the single-flight cache invariant over Django's own
cache framework (`cache.py`) — see the story spec's `<intent-contract>` for
the full contract (
``_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md``,
the tracked source of record the run-local implementation-artifacts draft is
promoted into once the story merges).

Ships ONLY behind the `pyforge-steward[dashboard]` optional extra, never a
base dependency. This module deliberately imports nothing from `django` or
`channels` at package level. Its submodules split two ways: `admin.py`, `apps.py`,
`cache.py`, — since Story 9.3 — `models.py`, `audit.py` and `migrations/`,
and — since Story 9.2 — `views.py`, and — since Story 48.6 — `consumers.py`,
`routing.py`, `asgi.py` import `django`/`channels` at module level; — since
Story 65.1 — `passport_sync.py` and `views_htmx.py` import `django` LAZILY,
inside their functions (the module imports cleanly without the extra, calling
it does not), so the base package's `sprint_ledger_query.sync_to_postgres` can
reach `passport_sync` by dynamic import (one of the sanctioned base→dashboard
reaches, pinned in `tests/meta/test_invariants.py`) — and since Story 61.1 —
`corridor_load.py` does the same, reached by `corridor.load_extract`;
`declarations.py`,
`middleware.py`, — since Story 9.4 — `export.py` (`ExportPolicy` +
`authorize_export`/`maybe_encrypt_export`), and — since Story 9.2 —
`navigation.py`/`filtering.py` are plain Python (the ASGI3 callable shape
is protocol, not framework, per AD-8) and import cleanly with or without
the extra. Story 9.3's review pass 3 restated this split: it had been
written as "only `apps.py` and `cache.py`", which that story's three new
django-importing modules made false, and this docstring is the package's
load-bearing statement of which modules an adopter without the extra may
touch. No other module in
`pyforge.steward` may import this package, `django`, or `channels`; pinned by
`tests/meta/test_invariants.py`, which since review pass 3 also pins the
narrower claim above — that `middleware.py`, `declarations.py`,
`export.py`, `navigation.py`, `filtering.py`, and this `__init__` itself
stay django-free (this file was added to that guard in review pass 4: it
executes on EVERY import of the package, so a `django` import here would
turn every framework-free test module into a collection error with
nothing failing first to say why) — rather than leaving it to these
docstrings.

**Where the deferrals live.** Several docstrings in this package defer a
question to "the deferred-work ledger". That ledger follows the same
two-stage path as this story's spec: entries are drafted into the run-local,
gitignored ``_bmad-output/…/implementation-artifacts/deferred-work.md`` while
the story is in flight, and are promoted into the tracked
``_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md``
when the story lands. Review pass 3 repointed those docstrings from the
run-local path (absent from every clone) to the tracked one; review pass 4
found the tracked ledger carries no Story 9.1 entries *yet*, so naming it
alone stated something a reader could check and find false. Both halves are
named here instead, and the promotion is itself recorded on the ledger.
"""

from __future__ import annotations
