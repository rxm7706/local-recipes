---
title: 'Notice Lifecycle'
type: 'feature'
created: '2026-08-08'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** Epic 10's AC calls for a draft -> published -> closed state machine: drafts
invisible by default (visible via an explicit filter), published notices the normal visible
state, closed notices staying archived/visible but flagged no-longer-current, with an audit trail
(`created_at`/`published_at`/`closed_at`/`closed_by`).

**Approach:** `status: Literal["draft", "published", "closed"]` on `Notice` (and its index/
markdown mirrors), one-way transitions only -- no un-publish, no re-opening a closed notice.
`publish_notice` requires `status == "draft"`; `close_notice` requires `status == "published"`.
`list_notices(status=None)` (the default, used by bare `herald notice`/`notice list` and the web
snapshot) shows `published` + `closed`, excluding `draft`; `status="draft"` shows only drafts
(mirroring Success/Epic 9's own draft/published distinction, per the task's explicit
cross-reference); `status="all"` shows every status.

**Judgment call: `closed_by` is a best-effort `role:source` string, not a real operator
identity.** `auth.AuthContext` (Story 6.3) carries only a `role`/`source` pair -- there is no
operator name, email, or user id concept anywhere in this package yet (`auth.py`'s own module
docstring draws this exact scope boundary: "does not verify a Herald web session ... does not
implement any Moment's actual write logic"). `close_notice` accepts whatever `closed_by` string
its caller passes and falls back to `notices.UNKNOWN_OPERATOR` ("unknown-operator") when none is
given; the CLI's `_run_notice_close` passes `f"{context.role}:{context.source}"` (e.g.
`"operator:env:HERALD_TOKEN"`) as the best available substitute. This is a documented gap, not a
silent omission -- both `notices.py`'s module docstring and this spec name it explicitly, so a
future story introducing real operator identity has a clear seam to land in (`close_notice`'s
`closed_by` parameter already exists; only the CLI's call site needs to change).

## Boundaries & Constraints

**Always:**
- `publish_notice` on a component with no notice at all: `HeraldError("no notice found for
  component ...")`.
- `publish_notice` on an already-published or closed notice: `HeraldError` naming the current
  status (`"already published"` / `"is closed; cannot publish"`).
- `close_notice` on a draft: `HeraldError("... is still a draft; publish it before closing")` --
  closing is not a shortcut around publishing.
- `close_notice` on an already-closed notice: `HeraldError("... is already closed")`.
- Every transition appends one entry to the index's `revisions` list (Story 10.1's edit-history
  mechanism) with a summary naming the transition (`"published"`/`"closed"`).
- `list_notices`'s default excludes drafts; the CLI's `notice list --status draft`/`--status all`
  flags are the only way to see them, mirrored by the identical `status=` keyword on
  `notices.list_notices` itself.

**Block If:** N/A -- pure state-machine logic over local storage, no spike gate.

**Never:**
- No un-publish (`published -> draft`) and no re-opening (`closed -> published`) -- the AC
  describes a one-way lifecycle; adding a reverse transition would be scope no story asked for.
- A closed notice is never hidden from `list`/`get` by default -- "archived, flagged
  no-longer-current" per the AC, not removed.

## I/O & Edge-Case Matrix

| Scenario | Expected |
|---|---|
| `publish_notice` on a fresh draft | `status="published"`, `published_at` set, one new revision |
| `publish_notice` on an unknown component | `HeraldError("no notice found ...")` |
| `publish_notice` twice | second call: `HeraldError("... already published")` |
| `close_notice` on a draft | `HeraldError("... still a draft ...")` |
| `close_notice` on a published notice | `status="closed"`, `closed_at`/`closed_by`/`close_reason` set |
| `close_notice` with no `closed_by` passed | falls back to `notices.UNKNOWN_OPERATOR` |
| `close_notice` twice | second call: `HeraldError("... already closed")` |
| `list_notices()` (default) | drafts excluded; published + closed included |
| `list_notices(status="draft")` | only drafts |
| `list_notices(status="all")` | every status |
| `list_notices(status="bogus")` | `HeraldError("invalid status ...")` |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/notices.py` -- (Story 10.1's module) --
  `publish_notice`, `close_notice`, `list_notices`'s `status=` filtering, `UNKNOWN_OPERATOR`.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- (Story 10.4's wiring) --
  `notice publish <component>`, `notice close <component> [--reason ...]`, `notice list
  --status`, `_run_notice_close`'s `closed_by=f"{context.role}:{context.source}"` composition.
- `src/shared/packages/pyforge-herald/tests/test_notices.py` -- lifecycle test block: publish/
  close happy paths, every refusal row in the I/O matrix, `list_notices` status filtering
  (default/draft/all/closed-stays-visible).
- `src/shared/packages/pyforge-herald/tests/test_cli_notice_epic10.py` -- CLI-level lifecycle
  round trip (author -> publish -> list -> close -> get), `--status draft` flag coverage.

## Design Notes

**Why is `close_notice`'s `reason` optional but the transition itself always logged?** The AC
names an audit trail (`closed_at`/`closed_by`) as unconditional, but a *reason* is operator
context that may not always exist (e.g. a routine, expected close vs. one needing explanation) --
`close_reason: str | None` follows the same optional-content-vs-mandatory-audit-fact split
`deadline`/`reason_link` already establish for authoring (Story 10.1/10.2).

**Follow-up (deferred, not this story's scope):** a real operator-identity concept (name/email
beyond `role:source`) would let `closed_by` (and, by the same seam, a future `authored_by`) carry
genuine attribution. `auth.py`'s own scope boundary (Story 6.3) explicitly defers this; no part
of Epic 10 attempts to close that gap itself.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 595 passed, 2 skipped.
- `ruff format --check` / `ruff check` -- clean.

## Spec Change Log

## Review Triage Log
