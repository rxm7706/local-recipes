---
title: 'Implement Claim Data Model & Local Storage (Scaled Down)'
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

**Problem:** Epic 9's original Story 9.1 (`epics-with-stories.md` lines 577-612) specs a
`Claims` database table (PostgreSQL or SQLite) reached via SQLAlchemy + Alembic migrations,
with a version-numbered thesis history and a `ClaimEvidence` table/JSON column with an
audit trail. Nothing in this package -- or anywhere else in Herald's architecture (a
stateless CLI + a static web dashboard) -- has ever hosted a database or a server. Per the
2026-08-08 scope decision (`docs/dreams/herald-moments-2-4-live-backend.md`), this story
instead delivers the same *data shape* over local JSON storage: no server, no ORM, no
migrations.

**Approach:** A new `claims.py` module: `Claim`/`Evidence`/`ThesisVersion` frozen
dataclasses, persisted as one JSON array file (`.herald/claims.json`,
`DEFAULT_CLAIMS_PATH`), written atomically (temp file + `os.replace`) -- the same
crash-safety convention `state.py` already uses for `.herald/bridge-state.json`. `create`,
`read_all`/`read_one`, `list_claims`, `publish`, `revalidate`/`revalidate_all`, `to_dict`,
and `snapshot` (Story 9.4's web-export shape) are the module's public surface; Stories
9.2/9.3/9.5 wire the CLI on top of it.

## Boundaries & Constraints

**Always:**
- `Claim(id, project_name, status, thesis, shipped_date, created_at, published_at,
  closed_at, updated_at, evidence: tuple[Evidence, ...], edit_history:
  tuple[ThesisVersion, ...])`. `Evidence(type, url, label, validated=False,
  validated_at=None)`. `type` is one of `EVIDENCE_TYPES = ("test_results", "metrics",
  "adoption", "other")`; `status` one of `CLAIM_STATUSES = ("draft", "published",
  "closed")`.
- One JSON **array** file, not a slug-keyed object (unlike `state.py`'s document): a claim
  has no caller-known stable key before `create` mints its `id`, so there is no natural
  keying dimension the way a deck slug is one for bridge state.
- Atomic write: temp file in the same directory as `claims_path`, then `os.replace` --
  mirrors `state.write`'s discipline exactly, including its limit (no `fsync`).
- Structural-failure discipline (AD-6): malformed JSON, a non-list top level, a duplicated
  key anywhere in the document, or an unknown field on any claim/evidence/edit_history
  entry all raise `errors.HeraldError` naming `claims_path`, never leak a bare
  `json.JSONDecodeError`/`KeyError`.
- `read_one`/`publish`/`revalidate` raise `errors.ClaimNotFoundError` (new) for an unknown
  claim id; `publish` raises `errors.ClaimStateError` (new) when the claim is not currently
  `draft`.

**Block If:** N/A -- no spike, no live gate; every function accepts an injectable
`validate`/`now`/`today`/`id_factory` callable so every test runs deterministically offline
(the package's `deny_network` autouse fixture would fail any test that forgot to inject
one where a real evidence check would otherwise fire).

**Never:**
- No database, no ORM, no migrations -- see Design Notes.
- No version-numbered thesis history with a `current: true` marker -- see Design Notes'
  scoped-down interpretation (`edit_history: list[ThesisVersion]`).
- No persisted `is_stale` flag on `Evidence` -- computed from `validated_at` at read time
  (`is_stale`/`to_dict`), never stored, so it can never drift out of sync with the clock.
- `claims.py`'s `publish`/`revalidate`/`revalidate_all` never bind
  `evidence.validate_for_publish`/`evidence.validate_link` as a **parameter default** --
  each resolves its validator inside the function body when `validate is None`. A
  parameter default is bound once at import time, which would freeze in the
  pre-monkeypatch function object and make `evidence.validate_for_publish` unpatchable
  from a test -- caught live while writing Story 9.3's CLI-level tests (see that story's
  spec Dev Notes) and fixed here, since the bug is this module's, not the CLI's.

## I/O & Edge-Case Matrix

| Scenario | Input | Expected | Notes |
|---|---|---|---|
| `create`, minimal | project_name only | draft claim, `shipped_date` defaults to today | |
| `create`, empty project_name | `""` | `HeraldError` | |
| `create`, unknown evidence type | `type="bogus"` | `HeraldError` | |
| `read_one`, missing id | any | `ClaimNotFoundError` | |
| `read_all`, missing file | no `claims.json` yet | `[]` | mirrors `state.read`'s "no state yet" |
| `read_all`, malformed JSON | truncated/invalid | `HeraldError` | |
| `read_all`, non-list top level | `{"not": "a list"}` | `HeraldError` | |
| `read_all`, unknown field on a claim | extra key | `HeraldError` | |
| `publish`, no thesis anywhere | `thesis=None`, claim.thesis `None` | `HeraldError` | |
| `publish`, broken evidence link | `validate` raises `EvidenceLinkError` | propagates; nothing written | claim stays `draft` on disk |
| `publish`, already published | second `publish` call | `ClaimStateError` | |
| `publish`, thesis changes | claim already had a thesis | old thesis appended to `edit_history` | |
| `list_claims`, date_range | some claims unset `shipped_date` | unset-date claims excluded | can't range-test an unknown date |
| `revalidate`/`revalidate_all` | broken + valid links | never raises; `validated`/`validated_at` updated in place | |
| `is_stale` | `validated_at=None` | `True` | never validated = always stale |
| `to_dict` | any claim | every evidence entry carries computed `is_stale` | |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/claims.py` -- create -- `Claim`,
  `Evidence`, `ThesisVersion`, `create`, `read_all`, `read_one`, `list_claims`, `publish`,
  `revalidate`, `revalidate_all`, `is_stale`, `to_dict`, `snapshot` (Story 9.4's export
  shape), `DEFAULT_CLAIMS_PATH`, `EVIDENCE_TYPES`, `CLAIM_STATUSES`.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/errors.py` -- edit --
  `ClaimNotFoundError`, `ClaimStateError` (both fall through to exit 1).
- `src/shared/packages/pyforge-herald/tests/test_claims.py` -- create -- the I/O matrix's
  rows plus `snapshot` coverage.
- `src/shared/packages/pyforge-herald/tests/test_bridge.py` -- edit -- sweeps `claims` into
  `_BRIDGE_CORE_MODULES` (the bridge-core-vs-CLI-vs-transport module inventory pin).

## Design Notes

**Judgment call: local JSON storage, not SQLAlchemy/Alembic/PostgreSQL.** The originating
scope decision, recorded in `docs/dreams/herald-moments-2-4-live-backend.md`: nothing in
this repo's Herald architecture has ever hosted a persistent service, and inventing one
silently -- with no answer for where it deploys, what triggers CI to call it, or who
operates it -- would be exactly the kind of scope invention this repo's behavioral
principles warn against. The full-spec live-backend version (real DB, migrations, indexes)
is deliberately deferred to that Dream; this module's data-access surface (`create`/
`read_*`/`publish`/`list_claims`) is the seam a future swap to a real database slots
behind without reshaping the CLI/web-tab contract built on top of it.

**Judgment call: JSON array, not a `Claims`-table-shaped keyed document.** `state.py`'s
document is keyed by deck slug because a slug is a stable, caller-known key that exists
*before* the first read (an operator always knows which deck they mean). A claim has no
equivalent pre-existing key -- its `id` is minted by `create` itself -- so a plain JSON
array is the simpler, equally-safe shape; keying by `id` after the fact would add an
indirection with no caller who benefits from it yet.

**Judgment call: `edit_history: list[ThesisVersion]`, not version-numbered rows with a
`current: true` marker.** The original AC describes a full version sequence. There is
exactly one "current" value in this scaled-down model (the `thesis` field itself) and a
flat list of what it used to be (`edit_history`) -- a reasonable scoped interpretation that
still satisfies "old version preserved" without inventing a version-number sequence no
caller yet needs (Simplicity First).

**Judgment call: evidence staleness computed, never stored.** `Evidence` carries
`validated`/`validated_at` but no persisted `is_stale` field. Staleness is a function of
"how old is `validated_at` relative to now" (AD-15's 7-day `evidence.STALE_AFTER` window)
-- computing it at read time (`is_stale`, used by `to_dict`) means it can never silently
drift out of sync with the clock the way a second stored field could.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 611 passed, 2 skipped
  (whole-package total after all five Epic 9 stories land; this story alone: 30 new tests
  in `test_claims.py`).
- `ruff format --check` / `ruff check` -- clean.

**Manual checks:**
- `python -c "from pyforge.herald import claims; print(claims.DEFAULT_CLAIMS_PATH)"` --
  resolves to `.herald/claims.json`.

## Spec Change Log

## Review Triage Log

### 2026-08-08 -- Adversarial review pass (Blind Hunter + Edge Case Hunter, no shared context)

- `[medium]` `[patch]` **`create`'s empty-project-name guard only caught falsy strings, not
  whitespace.** `not project_name` let `"   "` through (truthy in Python), creating a claim
  visually unidentifiable in `list` output (blank padding where the project name should be),
  distinguishable only by its UUID. Fixed: `create` now checks `not project_name.strip()`.
  New regression test: `test_create_rejects_a_whitespace_only_project_name`.
- `[medium]` `[patch]` **One malformed claim entry anywhere in `claims.json` blocked
  `read_one`'s lookup of an unrelated, perfectly healthy claim by its exact id.** The flat
  JSON-array design means `read_one` went through `read_all`, which eagerly decodes every
  entry -- a single corrupt row anywhere poisoned every lookup, not just requests for that
  row. Fixed: `read_one` now iterates the raw document directly, matching on the `id` field
  cheaply before doing a full validated decode, and only raises if the MATCHED entry is
  itself malformed. `read_all`/`list_claims`/every write path (which genuinely can't safely
  rewrite a file it can't fully parse) are unchanged and still fail loud on any corruption,
  per AD-6. New regression test:
  `test_read_one_is_not_blocked_by_an_unrelated_malformed_entry`.
- `addressed_findings`: 2 (both medium). No `intent_gap`, no `bad_spec`, no `defer`, no
  `reject`.
- **Noted, not fixed (dead-code gap, not a defect against a stated AC):** the Edge Case
  Hunter found that `edit_history`/re-publish-with-a-new-thesis is structurally unreachable
  from any real CLI sequence -- `publish` rejects any claim whose `status != "draft"`, and
  no command sets an initial `thesis` on a still-draft claim, so `edit_history` can never
  populate outside of a hand-constructed test fixture (`test_claims.py`'s own
  `test_publish_with_a_new_thesis_preserves_the_old_one_in_edit_history` has to bypass every
  public entry point to exercise it, with a comment admitting the scenario isn't supported).
  This is a genuine scope gap distinct from the documented scaled-down tradeoffs -- an
  `edit`/republish command would need to be added for this to ever fire in production use --
  but building that command is new scope, not a patch to existing behavior; left as an open
  follow-up rather than expanded here.

**Re-verification (2026-08-08, after this patch):** `pixi run --frozen -e pyforge-herald
pyforge-herald-test` -- 614 passed, 2 skipped; `ruff format --check`/`ruff check` clean.

**Follow-up review recommendation:** the `edit_history` dead-code gap noted above, if this
Moment ever gains an edit/republish command.
