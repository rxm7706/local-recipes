---
title: 'Cross-Moment Evidence Linking: Success Claims Cite Operations Notices'
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

**Problem:** Epic 11's original Story 11.3 (`epics-with-stories.md` lines 961-967) specs
"Success claims can link to Operations notices (bidirectional). Links validated weekly.
Backlinks visible in both directions." Unlike Story 11.2's AC, this one has an honest
scaled-down form: `claims.py`'s `Evidence` already models "this claim cites an external
thing," and `notices.py`'s `Notice` already exists as a citable target -- the only gap is
wiring a reference between them and a computed reverse view. "Validated weekly" scales down
the same way Story 9.5 already scaled down claim-evidence validation generally (an
operator-run check, not a cron); this story does not re-invent that machinery, it reuses it.

**Approach:** A claim's evidence can cite a Notice by giving it `type="notice"`, reusing the
existing `Evidence.url` field to hold the Notice's `component` name rather than an HTTP URL
(documented in `claims.py`'s module docstring, not a second field for what is still "the one
thing this evidence entry points at"). `claims.publish`/`revalidate`/`revalidate_all` all
skip HTTP validation for `type="notice"` entries (there is no URL to `HEAD`) and treat them
as trivially valid. The reverse direction -- "which claims cite this notice" -- is a
computed, un-persisted view (`claims.referenced_by_claims`), not a new field on `Notice`:
recomputed from `claims.json` at read time, so the two files can never drift out of sync
with each other the way a second stored copy of the same fact could. Wired into `herald
success create --evidence-notice <component>` (verifies the notice exists before citing it)
and `herald notice get`'s output (shows the backlink, both `--json` and plain text).

## Boundaries & Constraints

**Always:**
- `claims.EVIDENCE_TYPES` gains `"notice"` as a fifth member.
- `--evidence-notice <component>` on `herald success create` calls `notices.get_notice(repo_root,
  component)` *before* constructing the `Evidence` entry -- an unknown component raises
  `errors.HeraldError` (propagated by `dispatch`, exit 1) naming the problem, rather than
  silently storing a dangling reference.
- `claims.publish`'s per-entry validation loop, and the new `_revalidated_entry` helper
  shared by `revalidate`/`revalidate_all`, both skip `type="notice"` entries entirely (never
  call `validate(e.url)` on a component name) and mark them `validated=True` unconditionally
  -- "trivially valid," mirrored exactly across all three call sites so a `notice`-type
  evidence entry's validation status is never inconsistent depending on which command
  touched it last.
- `claims.referenced_by_claims(claims_path, component)` returns every claim (any status --
  a draft can already cite a notice before either side publishes) whose evidence contains a
  `type="notice"` entry with `url == component`, sorted by `created_at` for a deterministic
  order.
- `herald notice get`'s output (both `--json`'s `referenced_by_claims` array and the
  plain-text `referenced by claims:` block) is computed via `claims.referenced_by_claims`
  against `component` *after* redirect resolution (Story 10.3) -- a renamed notice's
  backlinks follow the rename the same way its other fields already do.
- `notices.py` is unmodified -- no new field on `Notice`, no new stored index key. The
  backlink lives entirely in `claims.py` (computed) and `cli.py` (composition), keeping the
  one-directional `cli.py -> {claims.py, notices.py}` import shape unchanged (neither storage
  module imports the other).

**Block If:** N/A -- no network call is added; `--evidence-notice`'s existence check is a
local index lookup (`notices.get_notice`), same cost as any other `notice get`.

**Never:**
- No weekly-cron re-validation of notice links specifically -- they piggyback on the
  existing `herald success validate <id>|--all` command (Story 9.5's own scaled-down
  cron-replacement), which already re-runs `_revalidated_entry` (thus already "revalidating"
  a `notice`-type entry, trivially, alongside every real URL).
- No new storage file. `claims.json` and `.herald/notices-index.json` are the only two files
  this story touches, both by extending code that already reads/writes them.

## I/O & Edge-Case Matrix

| Scenario | Input | Expected | Notes |
|---|---|---|---|
| Create evidence type | `Evidence(type="notice", url="auth-api-v1", ...)` | valid, stored | |
| `publish` with a notice-type entry | a broken-HTTP-would-fail stub `validate` | claim still publishes; entry `validated=True` | proves `publish` never calls `validate` on it |
| `revalidate`/`revalidate_all` with a notice-type entry | mixed real-URL + notice entries | notice entry always `validated=True`; real URL entry follows `validate`'s result | proves the shared helper's branch |
| `success create --evidence-notice <known component>` | notice already exists | claim created with a `type="notice"` evidence entry | |
| `success create --evidence-notice <unknown component>` | no such notice | exit 1, `"no notice found"`, nothing written | |
| `notice get --json <cited component>` | one claim cites it | `referenced_by_claims: [{"id", "project_name", "status"}]` | |
| `notice get --json <uncited component>` | no claim cites it | `referenced_by_claims: []` | |
| `notice get` after a rename redirect | old name cited by a claim, notice renamed | backlink still resolves (queried by the *new*, resolved component) | |
| `referenced_by_claims` on a missing `claims.json` | no file at all | `[]`, no raise | |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/claims.py` -- edit -- module
  docstring (documents the `type="notice"` convention and the computed-backlink design);
  `EVIDENCE_TYPES` gains `"notice"`; `publish`'s validation loop skips `type="notice"`
  entries; new `_revalidated_entry` helper (shared by `revalidate`/`revalidate_all`, both
  refactored to use it) skips HTTP validation the same way; new
  `referenced_by_claims(claims_path, component) -> list[Claim]`.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- edit -- new
  `--evidence-notice <component>` flag on the `success create` subparser;
  `_run_success_create` validates it via `notices.get_notice` before appending the evidence
  entry; `_notice_to_json` gains a `referenced_by=()` parameter and a
  `"referenced_by_claims"` output key; `_run_notice_get` computes the backlink via
  `claims.referenced_by_claims` and passes it through to both the `--json` and plain-text
  output paths.
- `src/shared/packages/pyforge-herald/tests/test_claims.py` -- edit -- evidence-type
  validity, `publish`/`revalidate` never-HTTP-validates-notice-type coverage,
  `referenced_by_claims` (finds a citing claim, empty when none cite it, empty on a missing
  file).
- `src/shared/packages/pyforge-herald/tests/test_cli_success.py` -- edit --
  `--evidence-notice` happy path and unknown-component exit-1 path.
- `src/shared/packages/pyforge-herald/tests/test_cli_notice_epic10.py` -- edit -- `notice
  get`'s backlink, both `--json` and plain text, plus the empty case.

## Design Notes

**Judgment call: reuse `Evidence.url` for the notice's component name, rather than a new
field.** Adding a dedicated `notice_component: str | None` field to `Evidence` would need to
be mutually exclusive with `url` for every other type, doubling the validation surface
(`_evidence_from_dict` would need "exactly one of `url`/`notice_component` set, depending on
`type`") for no behavioral gain over "the field this type already has, holding a different
kind of string." `label` already carries a human-readable description regardless of type, so
nothing is lost by this reuse -- it is documented explicitly in `claims.py`'s module
docstring so a future reader is not left guessing why a `notice`-type evidence entry's `url`
is not a URL.

**Judgment call: `referenced_by_claims` lives in `claims.py`, not `notices.py`.** The
alternative (a `notices.referenced_by_claims` helper) would require `notices.py` to import
`claims.py`, while `claims.py` (for `--evidence-notice`'s existence check) already needs
`cli.py` to call `notices.get_notice` -- keeping the backlink computation in `claims.py`
(which already owns the forward reference's shape) means neither storage module ever needs
to import the other; `cli.py` remains the sole composition point over both, consistent with
its existing role gluing `progress.py`/`claims.py`/`notices.py` together.

**Judgment call: `--evidence-notice` resolves against `success create`'s own `--repo-root`
(default cwd), not a separately-flagged notices root.** Every other `notice` subcommand in
`cli.py` resolves notices storage against `Path.cwd()` directly; `success`'s subcommands
already resolve claims storage against `--repo-root` (default cwd too). Using the same
`--repo-root` value for both lookups inside one `create` call keeps "the repo root an
operator is working in" a single concept for that invocation, rather than introducing a
second, usually-redundant flag.

**Judgment call: any-status backlink, not published-only.** `referenced_by_claims` returns a
citing claim regardless of its own `status` (draft/published/closed) -- a draft claim can
already reference a notice's component before either side is published, and hiding that from
`notice get`'s output would make the backlink lag behind reality for no stated reason in the
AC ("backlinks visible in both directions," not "only published backlinks").

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 717 passed, 2 skipped
  (whole-package total, immediately after this story landed).
- `ruff format --check` / `ruff check` -- clean (on every file this story touched).

**Manual checks:**
- `herald success create warden --evidence-notice auth-api-v1` against a scratch repo with
  an existing published `auth-api-v1` notice -- creates a draft claim with a `notice`-type
  evidence entry; `herald notice get auth-api-v1 --json` on the same repo shows
  `referenced_by_claims` naming that claim's id/project_name/status.
- Same against an unknown component -- exits 1, `"no notice found"`, no claim written.

## Spec Change Log

## Review Triage Log
