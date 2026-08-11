"""pyforge.steward.dashboard — Epic 9's secure-live-dashboards foundation.

Story 9.1: identity extraction at the ASGI boundary (`middleware.py`), the
declaration schema an adopter fills in instead of hand-writing filtering
(`declarations.py`), and the single-flight cache invariant over Django's own
cache framework (`cache.py`) — see the story spec's `<intent-contract>` for
the full contract (
``_bmad-output/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant.md``).

Ships ONLY behind the `pyforge-steward[dashboard]` optional extra, never a
base dependency. This module deliberately imports nothing from `django` or
`channels` at package level — only `apps.py`, `middleware.py`, and `cache.py`
do, each import-time-optional in step with the extra. No other module in
`pyforge.steward` may import this package, `django`, or `channels`; pinned by
`tests/meta/test_invariants.py`.
"""

from __future__ import annotations
