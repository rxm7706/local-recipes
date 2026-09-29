---
title: 'Copier engine wrapper — the single seam'
type: 'feature'
created: '2026-08-14'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
difficulty: 'heavy'
baseline_revision: '26102ea12c6d079a2651d36e12d2d39ea296c46e'
---

<intent-contract>

## Intent

**Problem:** Genesis (the `marshal seed` installer) needs Copier to materialize templated
artifacts, but nothing in the codebase may import `copier` directly or see its `Worker`
internals — and `fs` (Story 7.3, the target-repo write primitive) and the apply runner (Story
10.3) don't exist yet, so this module cannot write to a live repo at all.

**Approach:** Build `seed/engine/copier.py` as the ONLY module that imports `copier`. It exposes
`materialize(MaterializeRequest) -> MaterializeResult`, which always renders into an EPHEMERAL
staging location (never the live target repo), reconciles the staged output against the
manifest's declared paths, and returns the staged tree as data. Story 10.3's future apply runner
reads that result and commits it through `fs`.

## Boundaries & Constraints

**Always:**
- `copier` is imported nowhere in the codebase except `seed/engine/copier.py` (P-02) — proven by
  a meta test.
- `materialize()` calls only `copier.run_copy` / `run_update` / `run_recopy` (the public API) —
  never a `Worker` attribute, never a private `copier._*` module.
- Every `run_copy`/`run_update`/`run_recopy` call passes `answers_file=".marshal/.copier-answers.yml"`
  explicitly (Spike-0 finding: `run_update` does not auto-discover it from the template and
  raises `TypeError: Template not found` if omitted; treat `run_recopy` the same way and verify
  empirically since Spike-0 only exercised `run_copy`/`run_update`).
- `materialize()` NEVER targets the caller-supplied `dst_path` directly. It renders into a
  private staging location it owns for the duration of the call, then validates the result
  before returning it — nothing is "committed" by this module.
- The default `template_path` (when the request omits one) resolves to the in-package
  `seed/templates/` directory; an explicit `template_path` (path or URL) overrides it.
  `--unsafe` on the CLI maps to `unsafe=True`; omitted/false is Copier's own safe default.
  `MaterializeVerb.RECOPY` requires `confirm=True` on the request or `materialize()` raises
  before calling Copier at all (FR-101's "explicit confirmation").
- Every path Copier writes into staging is checked against an allow-list before being included
  in the result: the loaded manifest's entries whose class is `copied-managed`,
  `copied-seeded`, `generated-derived`, or `hybrid-managed-region` (`load_manifest(...).entries`,
  filtered by `applies_to`), UNION the fixed Genesis-owned set (`.marshal/seed-state.yml`,
  `.marshal/.copier-answers.yml`, `.marshal/plan.json`, `.bmad-config.user.toml` — these have no
  manifest entry per a known deferred-work gap, so they're allow-listed here explicitly). A path
  matching the manifest's `never_write` globs is rejected UNLESS the manifest itself declares
  that path as one of the allow-listed entries above — `never_write` protects already-materialized
  content from being clobbered on a *later* run, not the manifest's own one-time, explicitly-declared
  seeding (a `copied-seeded` entry such as `starter-dream` at `docs/dreams/{{ slug }}.md` is exactly
  this case: it collides with the `docs/dreams/*.md` `never_write` glob and must still materialize
  once, per FR-74).
  A path failing either check raises `TemplateBoundaryError` naming every offending path, and
  nothing is returned.
- Exceptions raised by the underlying `copier` calls never reach the caller as `copier` types —
  they're caught and re-raised as `CopierEngineError` (`raise ... from err`), except boundary
  violations, which raise the more specific `TemplateBoundaryError`.

**Block If:** `copier==9.17.x` cannot be imported in this environment (e.g. not resolvable via
conda-forge/pip for the pinned range) — HALT rather than loosening the pin without an
architecture amendment.

**Never:**
- Never make `seed/templates/` itself a fully populated, Copier-renderable template tree in this
  story — that's separate, later work. This story's tests build their own throwaway fixture
  templates (mirroring Spike-0's method), not the real in-package content.
- Never accept a `Plan` (Story 9.6) as input — it doesn't exist yet and isn't this story's
  dependency; the boundary check reconciles against the manifest only. Story 10.3 upgrades this
  to full plan-based reconciliation when it wires `apply` together.
- Never read or hand-edit the Copier answers file directly — it's opaque (AD-52); answers are
  always supplied via `data=` from the caller's request.
- Never build the general "no `Worker` attribute / no private-module import" AST meta-test here
  — that's Story 12.4's named surface (`S-12.4's import test`). This story only proves P-02
  (sole import site for `copier` itself).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fresh copy | `verb=COPY`, empty/no-existing dst, default template | `MaterializeResult` with staged file list + extracted answers | No error expected |
| Update | `verb=UPDATE`, dst already has `.marshal/.copier-answers.yml` | Staged result reflects the merged update; `answers_file=` passed explicitly | No error expected |
| Recopy without confirm | `verb=RECOPY`, `confirm=False` | Nothing staged, no Copier call made | Raises before invoking Copier, naming the missing confirmation |
| Unsafe feature, `unsafe=False` | Template uses a code-executing feature | No staged result returned | `CopierEngineError` wrapping Copier's own refusal |
| Out-of-manifest write | Template writes a path with no manifest entry and not in the tool-owned set | Nothing returned; staging discarded | `TemplateBoundaryError` naming every offending path |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/engine/copier.py` -- NEW, the
  single seam: `MaterializeVerb`, `MaterializeRequest`, `MaterializeResult`, `CopierEngineError`,
  `TemplateBoundaryError`, `materialize()`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/engine/__init__.py` -- currently
  empty; re-export the public symbols above.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/model/manifest.py` -- existing;
  `load_manifest(path) -> Manifest` (`.entries`, `.never_write`) is reused unmodified for the
  boundary check.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/templates/manifest.yaml` --
  existing; the packaged manifest instance loaded at runtime via `importlib.resources`.
- `src/shared/packages/pyforge-core/src/pyforge/core/errors.py` -- existing; `PyforgeError` is
  the base every new exception here subclasses alongside `Exception`.
- `src/shared/packages/pyforge-marshal/pyproject.toml` -- add `copier` to `dependencies`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_engine_copier.py` -- NEW.
- `src/shared/packages/pyforge-marshal/tests/meta/test_p02_copier_sole_ownership.py` -- NEW,
  mirrors `tests/meta/test_ad7_verdict_sole_ownership.py`'s AST-scan-excluding-target-module
  technique, scoped to `import copier` / `from copier import ...` only.

## Tasks & Acceptance

**Execution:**
- [ ] `pyproject.toml` -- add `"copier>=9.17,<10"` to `dependencies` -- matches the architecture
  Stack table pin; nothing imports `copier` before this lands.
- [ ] `seed/engine/copier.py` -- define `MaterializeVerb` (StrEnum: `COPY`/`UPDATE`/`RECOPY`),
  `MaterializeRequest` (frozen dataclass: `verb`, `dst_path: Path`, `template_path: Path | str |
  None = None`, `data: Mapping[str, Any] = {}`, `unsafe: bool = False`, `confirm: bool = False`),
  `MaterializeResult` (frozen dataclass: `staged_paths: tuple[Path, ...]`, `answers: Mapping[str,
  Any]`) -- the Genesis-internal request/result API callers use instead of touching `copier`.
- [ ] `seed/engine/copier.py` -- implement `materialize(request) -> MaterializeResult`: stage
  into an ephemeral location (a fresh tmp dir for `COPY`; a local git clone of `dst_path` for
  `UPDATE`/`RECOPY`, so Copier's own git-based diffing has real history to work against without
  ever touching the live repo), dispatch to the matching `copier.run_*` call with
  `answers_file=".marshal/.copier-answers.yml"`, `unsafe=request.unsafe`, `data=request.data`,
  and for `RECOPY` require `request.confirm` before calling Copier at all.
- [ ] `seed/engine/copier.py` -- implement the manifest-boundary check: load the packaged
  manifest, build the allow-list (manifest entries ∪ the fixed `.marshal/`/`.bmad-config.user.toml`
  set), reject any staged path outside it or matching `never_write`, raising
  `TemplateBoundaryError` with every offending path named.
- [ ] `seed/engine/__init__.py` -- export `materialize`, `MaterializeRequest`,
  `MaterializeResult`, `MaterializeVerb`, `CopierEngineError`, `TemplateBoundaryError`.
- [ ] `tests/unit/test_seed_engine_copier.py` -- cover the I/O matrix above using throwaway
  fixture templates built in `tmp_path` (mirror Spike-0's method): fresh copy, update against an
  existing answers file, recopy without confirm raises pre-call, unsafe feature without
  `unsafe=True` raises `CopierEngineError`, out-of-manifest write raises `TemplateBoundaryError`
  naming the path, and a plain assertion that `import copier` only appears in
  `seed/engine/copier.py` (belt-and-suspenders alongside the dedicated meta test below).
- [ ] `tests/meta/test_p02_copier_sole_ownership.py` -- AST-scan every installed
  `pyforge.marshal` module except `seed/engine/copier.py` and fail on any `import copier` / `from
  copier import ...` (any alias), with a positive check that the guard fires on a synthetic
  violation so it isn't vacuous.

**Acceptance Criteria:**
- Given a fresh (non-existent) destination, when `materialize()` is called with `verb=COPY`,
  then the live destination is untouched and the returned `MaterializeResult` lists every staged
  path plus the extracted answers.
- Given a destination with an existing `.marshal/.copier-answers.yml`, when `materialize()` is
  called with `verb=UPDATE` and no explicit `answers_file` override, then the call succeeds
  (Spike-0's `TypeError: Template not found` failure mode does not occur) because
  `answers_file=".marshal/.copier-answers.yml"` was passed explicitly.
- Given `verb=RECOPY` and `confirm=False`, when `materialize()` is called, then no `copier.run_*`
  function is invoked and a clear error names the missing confirmation.
- Given a template whose rendered output includes a path with no covering manifest entry and not
  in the Genesis-owned set, when `materialize()` reconciles the staged output, then it raises
  `TemplateBoundaryError` before returning anything, naming the offending path.
- Given any module in the installed `pyforge.marshal` package other than `seed/engine/copier.py`,
  when the sole-ownership meta test scans it, then it contains no `copier` import.

## Spec Change Log

<!-- Append-only. Populated by step-04 during review loops. Do not modify or delete existing entries.
     Each entry records: what finding triggered the change, what was amended, what known-bad state
     the amendment avoids, and any KEEP instructions (what worked well and must survive re-derivation).
     Empty until the first bad_spec loopback. -->

## Review Triage Log

### 2026-08-14 — Review pass
- intent_gap: 1: (high 1)
- bad_spec: 0
- patch: 10: (high 1, medium 4, low 5)
- defer: 2: (medium 1, low 1)
- reject: 6: (medium 1, low 5)
- addressed_findings:
  - none

**Intent-gap finding (blocking, root cause inside `<intent-contract>`):** the Boundaries &
Constraints bullet "Any path also matching the manifest's `never_write` globs is rejected even if
otherwise allow-listed" is self-contradictory against already-shipped, already-tested manifest
data (Story 7.5, `seed/templates/manifest.yaml`), not a hypothetical: at least two real,
`copied-seeded`-class entries collide directly with a `never_write` glob —
`starter-dream` (`docs/dreams/{{ slug }}.md`) collides with `never_write`'s `docs/dreams/*.md`,
and `specs-readme` (`_bmad-output/projects/{{ slug }}/planning-artifacts/specs/README.md`)
collides with `never_write`'s `**/planning-artifacts/**`. Under the rule as literally written,
`materialize()` can never successfully stage either artifact — making it impossible to satisfy
FR-74 ("`docs/dreams/<slug>.md` is seeded... it is the only Dream written"), a requirement from
elsewhere in the same architecture chain this story is gated on. The rule's own docstring
rationale for `copied-seeded` ("materialized once, then repo-owned forever") implies
`never_write`'s actual purpose is protecting content from being clobbered on *later* runs, not
vetoing the manifest's own one-time, explicitly-declared seeding — i.e. an allow-listed
(manifest-declared) path should be exempt from the `never_write` veto; `never_write` should only
catch paths the manifest itself does *not* declare. This reading is the only one consistent with
the shipped manifest and FR-74, but the fix changes normative Boundaries text inside
`<intent-contract>`, which this workflow may not silently amend — hence intent_gap, not bad_spec
or patch, per the root-cause-location test in `step-04-review.md`.

A full, real-Copier-tested implementation was built and reviewed in this pass before this
contradiction surfaced (`seed/engine/copier.py` + two test files, `3646 passed` on the full
`pyforge-marshal` suite) and has been reverted per the intent_gap protocol — reference this
transcript/run when re-driving the story rather than re-investigating from scratch. The other 9
patch-classified findings and 2 defer-classified findings below are recorded for completeness
(cascading order makes them moot for this pass; none were applied) and should be re-triaged
against whatever implementation comes out of the corrected contract:

- **patch** (moot this pass): (1, high) `materialize()` compared `request.verb` to
  `MaterializeVerb` members with `is`, not `==`/normalization — a caller passing a plain `str`
  (e.g. `verb="recopy"`) instead of the enum member silently bypassed the RECOPY
  `confirm=True` gate (FR-101) rather than raising. (2, medium) `MaterializeResult` exposed no
  way to locate the staging directory when `staged_paths` was empty (e.g. a no-op `UPDATE`),
  leaking the tempdir. (3, medium) the `{{ slug }}` → `*` translation in the allow-list pattern
  used `fnmatch`'s slash-crossing `*`, so a manifest entry like `docs/dreams/{{ slug }}.md` also
  matched an unintended nested path (`docs/dreams/x/y.md`) — should not cross `/`. (4, medium)
  the Jinja-placeholder and trailing-slash-directory allow-list mechanisms had no direct test
  coverage against the real packaged manifest. (5, medium) `_git_changed_paths`'s own
  `subprocess.run` call, unlike `_git_clone_local`'s, was not wrapped, letting a raw
  `CalledProcessError`/`TimeoutExpired` escape the documented `CopierEngineError` contract. (6,
  low) `_git_clone_local`'s error message dropped the underlying git stderr detail. (7, low) the
  module docstring's "cheap via hardlinks" claim doesn't hold when the tmp staging dir and
  `dst_path` are on different filesystems. (8, low) the `unsafe=True` + caller-controlled
  `template_path` composition (arbitrary code execution, by design) wasn't called out in the
  docstring. (9, low) a manifest load/validation failure inside the boundary check would
  propagate untyped rather than as `CopierEngineError`. (10, low) no test exercised the
  `never_write` deny-list at all.
- **defer** (moot this pass): (1, medium) for `UPDATE`/`RECOPY`, staging via `git clone --local`
  only clones committed history, so uncommitted local edits in `dst_path` are silently invisible
  to Copier's diff — expected to be covered by Story 10.4's dirty-worktree-refusal precondition
  at the CLI layer, but `materialize()` itself doesn't enforce it. (2, low) `_git_changed_paths`
  parses `git status --porcelain` with fixed-offset slicing, not `-z`, so a staged filename
  containing a space or non-ASCII character (git's default quoting) would be mis-parsed.
- **reject** (noise / by-design, not real defects): no verb/state validation against `dst_path`'s
  actual materialization state (belongs to the precondition/detect layer, not this seam); the
  blanket `except Exception` → `CopierEngineError` in `_stage_and_render` (matches this story's
  own explicit Boundaries intent); no caching of the re-parsed packaged manifest (non-issue at
  expected call frequency); the `>=9.17,<10` pin permitting drift past the empirically-verified
  `9.17.1` (matches this repo's existing pinning convention, out of this story's scope); a
  `--template` override still being checked against the packaged manifest (correct by design —
  NFR-S3 applies regardless of template source, distinguishing "which template renders content"
  from "what Genesis may write"); empty directories absent from `staged_paths` (git and this
  system's manifest model don't track empty directories as artifacts).

## Design Notes

Staging strategy is verb-dependent, stated as a rule not left implicit: `COPY` targets a brand
new location, so an empty tmp dir is sufficient staging. `UPDATE`/`RECOPY` rely on Copier's own
git-based diff-and-merge algorithm, which needs real commit history to reason about — so staging
for those two verbs is a **local git clone of `dst_path`** (`git clone --local`, cheap via
hardlinks), never the live working tree itself. Either way, `dst_path` is only ever read by this
module (to seed the clone), never opened for writing by it or by Copier.

This module reconciles against the **manifest**, not a `Plan` (Story 9.6 doesn't exist yet and
isn't in this story's Deps). Story 10.3's apply runner, which does depend on 9.6, is expected to
run a second, stricter reconciliation against the actual computed `Plan` before committing
through `fs` — this module's manifest-only check is a first filter, not the final word.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done
Reconciled 2026-09-20: the `blocked` verdict below is the session's own record at halt time; the story was landed afterwards and the ledger row promoted to `done` by `5290c9bcd2 2026-08-14 recover marshal 10-1 (Copier engine wrapper — the single seam)` — that promotion is the ruling this record now reflects.

Blocking condition: `intent gap in intent contract`

**What happened:** implementation was completed in full (`seed/engine/copier.py`, two test
files, `pyproject.toml`/`pixi.toml`/`pixi.lock` updates) and passed the entire `pyforge-marshal`
suite (3646 passed) plus both parallel reviews (Blind Hunter adversarial + Edge Case Hunter).
Triage of the combined findings surfaced one **intent_gap**: the `<intent-contract>` Boundaries
bullet "Any path also matching the manifest's `never_write` globs is rejected even if otherwise
allow-listed" directly contradicts two already-shipped manifest entries (`starter-dream` at
`docs/dreams/{{ slug }}.md`, `specs-readme` at
`_bmad-output/projects/{{ slug }}/planning-artifacts/specs/README.md`, both `copied-seeded`
class) — under the rule as written, `materialize()` can never successfully stage either, which
would make FR-74's Dream-seeding requirement permanently unsatisfiable. Full detail, including
the recommended fix (allow-listed/manifest-declared paths should be exempt from the `never_write`
veto — `never_write` should only catch paths the manifest does *not* declare), is in the Review
Triage Log above.

Per the intent_gap protocol, all code changes were reverted (working tree confirmed clean,
matching `baseline_revision`); nothing was committed. No `deferred-work.md` entries were written
(processing stopped at intent_gap; the 2 defer-classified findings recorded in the triage log are
informational only, not yet promoted).

**Recommended resolution path:** run `bmad-loop-resolve` (or a human edit) to amend the
`<intent-contract>` Boundaries bullet along the lines of "a path matching the manifest's
`never_write` globs is rejected UNLESS the manifest itself declares that path as a materialized
entry" — then re-run `bmad-dev-auto` on this spec (status `blocked` with a recognized frontmatter
`status` routes back through `step-01`'s intent check, but `blocked` currently routes to an
immediate HALT per `step-01-clarify-and-route.md`'s intent check table — the resolving human/
process should set `status: draft` after amending, so the next `bmad-dev-auto` invocation re-plans
against the corrected contract). The reverted implementation in this run's transcript
(`/home/rxm7706/.bmad-loops/pyforge-marshal/.bmad-loop/runs/20260813-094919-bfcb/`) is a working
reference — re-implementing from scratch should not be necessary; the design (ephemeral staging,
verb-dependent staging strategy, manifest-based boundary reconciliation) held up under full
real-Copier testing and two independent adversarial reviews, modulo the one contract defect above
and the 9 patch-classified / 2 defer-classified findings also recorded in the Review Triage Log.

Follow-up review recommendation: not applicable (no review-driven changes were kept).

Residual risks: none beyond the intent-gap itself — the working tree is clean and no partial
state was left behind.

**2026-08-14 manual recovery note:** the intent_gap protocol's revert left no recoverable git
artifact (no `attempt-preserve/*` branch, no `failed/*/changes.patch`, clean reflog) — unlike a
deferred-story timeout, an intent-gap revert does not currently preserve the attempt. The
`<intent-contract>` Boundaries bullet was amended per this file's own recommended fix (a
manifest-declared path is now exempt from the `never_write` veto). Rather than re-implementing
from scratch, the operator recovered the reviewed implementation by reconstructing it from the
dev session's own Claude Code transcript (`22bd98b0-b2b6-4340-9ed1-c95bd67f0b75.jsonl`) — the
adversarial-review Agent-tool prompts (Blind Hunter / Edge Case Hunter, both invoked with the full
diff embedded) contained the complete tracked-file diff plus full content of every new file,
byte-identical to what the session actually produced and tested (3646 passed at review time; 4181
passed after landing on top of intervening stories). Landed by hand via a `land/marshal-10-1-
recovery` PR, mirroring the established recovery pattern for this run's earlier stuck-baseline
incidents. `status` set to `done` here (not re-driven through `bmad-dev-auto`) since the recovered
code is the same, real, already-reviewed work — a fresh drive would duplicate it. This gap (no
preserved artifact on an intent-gap revert) is tracked as its own Dream:
`docs/dreams/bmad-loop-intent-gap-work-preservation.md`.

## Status reconcile 2026-09-20

- Auto Run Result `Status: blocked` → `done` (see the reconcile line under it).
