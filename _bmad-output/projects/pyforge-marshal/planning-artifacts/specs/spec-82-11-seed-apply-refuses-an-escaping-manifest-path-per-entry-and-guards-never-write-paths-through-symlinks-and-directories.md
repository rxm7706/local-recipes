---
title: '82.11: Seed apply refuses an escaping manifest path per entry and guards never-write paths through symlinks and directories'
type: 'fix'
created: '2026-10-02'
status: 'in-review'
baseline_revision: 'dfddcecdaf9ec0e9dfcd602e4f2bab9a066cef23'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/templates/manifest.yaml
warnings: [oversized]
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The seed's containment and never-write guards each have a hole. Re-verified at HEAD a7cdb91fe4:

- `seed/model/manifest.py::ManifestEntry.__post_init__` validates `path` only as non-blank text (`:294`), so
  `path: "/etc/passwd"` or `path: "../../../etc/cron.d/pwn"` loads as a valid entry; the manifest is the one input that can
  name a location outside the repository being seeded (DW-FU-7-4).
- `seed/detect/inventory.py::_resolve_within_repo` (`:536-559`) returns `None` for such a path and for an in-repo symlink
  pointing outside, and `_classify_entry` treats `None` as `ABSENT` (`:574-575`); `build_plan` then emits an ordinary
  action with the escaping path, and `seed/apply/run.py` refuses the whole plan (`escaping-target`, `:332`, `:358`). One bad
  entry blocks apply for every artifact, and re-planning reproduces the same plan (DW-10-3-9).
- `seed/fs.py::_guard` resolves both the path and the repo root before matching (`:281-293`), and
  `seed/verbs/preconditions.py::_relative_within` does the same for rung 4 (`:288-315`). With `docs -> real/`, a write to
  `docs/dreams/x.md` is matched as `real/dreams/x.md` and `docs/dreams/*.md` never fires, at the precondition and the write
  primitive alike (DW-10-4-1).
- `seed/fs.py::_matches` (`:199-234`) uses `fnmatch.fnmatchcase`, and the manifest's `**/planning-artifacts/**` and
  `**/implementation-artifacts/**` (`seed/templates/manifest.yaml:39-40`) need a segment after the directory, so the
  directory node itself (`_bmad-output/projects/<slug>/planning-artifacts`, and `_bmad-output/planning-artifacts`, AD-61's
  own worked example) passes the guard: a rename, removal or re-point of the Tier-2/Tier-3 tree is not refused. The
  manifest's `planning-artifacts-symlink` / `implementation-artifacts-symlink` entries (`:264-273`) stay writable only
  because the pattern misses (DW-FU-7-5-5).

**Approach:**

- `ManifestEntry` rejects an absolute `path` or one with a `..` segment at load, a manifest error naming the entry id.
- An entry that still resolves outside the repository (an in-repo symlink pointing out) is classified as its own refusal,
  not `ABSENT`: `build_plan` emits no action for it, and the verb reports a per-entry finding naming the entry and the path
  it resolves to, while every other action applies.
- Never-write matching checks the repo-relative path as written and the resolved one; a match on either refuses, in
  `_guard` and in rung 4 alike (one helper, so the two cannot disagree).
- A directory target is matched with its trailing separator as well, so `dir/**` covers the directory node; the two
  manifest-declared symlink entries stay writable through `NeverWrite.exempt` by declaration, never by a silent miss.

Ledger key: `82-11-seed-apply-refuses-an-escaping-manifest-path-per-entry-and-guards-never-write-paths-through-symlinks-and-directories`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-12 (adopt onto a living repo) and CAP-15 (an attempted write to any never-write path is a hard
  error), with Story 7.4 (FR-66 to FR-71; AD-55), Story 7.3 (FR-71, FR-100; AD-61), Story 7.5 (FR-66, FR-71, FR-118),
  Story 10.3 (FR-83) and Story 10.4 (FR-85, FR-86, FR-87). Defects of shipped behaviour, so no new CAP; no flag.

## Acceptance Criteria

- Given a manifest entry with `path: "/etc/passwd"`, or with `path: "../outside.txt"` When the manifest loads Then loading fails with an error naming that entry's id
- Given an in-repo symlink entry that resolves outside the repository and one ordinary absent entry When `adopt` plans and applies Then the plan holds no action for the escaping entry, a finding names it, and the ordinary entry is written
- Given `docs -> real/` and `never_write = ("docs/dreams/*.md",)` When a write targets `docs/dreams/x.md` through `seed.fs` or rung 4 Then it is refused
- Given the shipped never-write patterns When `seed.fs` is asked to replace, remove or re-point `_bmad-output/projects/demo/planning-artifacts` Then it is refused
- Given `seed init` into a fresh directory When it runs Then both BMAD artifact symlinks are still created
- Given each fix reverted in turn When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** The never-write set only gains coverage. `seed check` stays read-only. Close DW-10-3-9, DW-FU-7-4, DW-10-4-1
and DW-FU-7-5-5 in `deferred-work-ledger.md` when the story lands (status `closed`, a `resolved:` line naming this story).

**Never:** Do not change the shipped patterns' text or the manifest's entries, classes or `model_version`. Do not resolve a
symlinked ancestor away silently. Do not touch the plan fingerprint, rung 5 or `--skip` (Story 82.12's surface).

</intent-contract>

## Binding

Parent: Stories 7.3, 7.4, 7.5, 10.3 and 10.4, `spec-pyforge-marshal` CAP-12 and CAP-15; a defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 entry.
Ledger key: `82-11-seed-apply-refuses-an-escaping-manifest-path-per-entry-and-guards-never-write-paths-through-symlinks-and-directories`.
Ledger status at mint: `backlog`.
Deps: —.
Closes: DW-10-3-9, DW-FU-7-4, DW-10-4-1, DW-FU-7-5-5.

## Code Map

All paths under `src/shared/packages/pyforge-marshal/` (tests in `tests/unit/`).

- `src/pyforge/marshal/seed/model/manifest.py` -- `ManifestEntry.__post_init__` (`:294`) validates `path` as non-blank only; `load_manifest` wraps a `ValueError` as `ManifestError("manifest: ...")`, so a message naming the entry id reaches the caller.
- `src/pyforge/marshal/seed/fs.py` -- `_matches` (`:199`), `_guard` (`:237`), `check_never_write`, `symlink` (`resolve_leaf=False`). Match is on the resolved path only, `fnmatchcase`, no trailing-separator form. The one place the never-write decision is made.
- `src/pyforge/marshal/seed/verbs/preconditions.py` -- rung 4 (`:599-633`) re-derives the decision with `skips.first_match` on `_relative_within`'s resolved string; `_relative_within` (`:288`) serves rung 3 containment too. Module docstring "stated bounds" and the rung 4 comment describe the symlinked-ancestor gap this story closes.
- `src/pyforge/marshal/seed/verbs/skips.py` -- `first_match` stays for `--skip` globs; rung 4 stops using it.
- `src/pyforge/marshal/seed/detect/inventory.py` -- `ArtifactState` (`:207`), `Inventory` (`:259`), `_resolve_within_repo` (`:536`), `_classify_entry` (`:562`), `classify`, `legacy_findings` (the pattern `escape_findings` mirrors), `writable_exemptions` (`:640`, class-keyed: the two symlink entries are `generated-derived`, so absent today).
- `src/pyforge/marshal/seed/detect/findings.py` -- `FindingType`, `REMEDIES`; a member needs a `REMEDIES` row.
- `src/pyforge/marshal/seed/plan/build.py` -- `_ACTIONABLE_STATES` is `{ABSENT, PRESENT_DIVERGENT}`: a new `ESCAPING` state yields no action with no edit here.
- `src/pyforge/marshal/seed/verbs/adopt.py` -- `AdoptResult` (`:327`), `run_adopt` (`:960`), three return sites; `verbs/check.py:386` loop (needs an `ESCAPING` branch, else it reads the escaped path); `verbs/update.py` `UpdateResult` (`:227`) already carries `referenced_dep_findings`.
- `src/pyforge/marshal/cli/seed.py` -- `run_adopt` (`:550`) renders `AdoptResult` as text and `--json`.
- `src/pyforge/marshal/seed/apply/run.py:332,358` -- `escaping-target` whole-plan refusal; read-only here (it stays the backstop for a hand-edited `plan.json`).
- `src/pyforge/marshal/seed/derive/projects_index.py` -- `ensure_symlinks` -> `fs.symlink`; no verb calls it yet, so AC "both symlinks still created" is proven at that seam with the shipped patterns and `writable_exemptions`.
- `src/pyforge/marshal/seed/templates/manifest.yaml` -- read-only (Never): `never_write` `:39-40`, symlink entries `:264-273`.
- Reuse: `Finding.new`, the `LegacyRecord`/`legacy_findings` shape, `object.__setattr__` forcing in existing tests to reach otherwise-unreachable branches.
- Baseline: `pixi run --frozen -e pyforge-marshal marshal seed init` into a fresh git dir exits 2 at HEAD (`materialize() staged path(s) outside the manifest boundary`, the packaged template's known limitation) -- unrelated and not touched.

## Tasks & Acceptance

**Execution:**
- `seed/model/manifest.py` -- reject an absolute `path` (POSIX or drive-letter) and any `..` segment (either separator) in `ManifestEntry.__post_init__`, `ValueError` naming `id` -- DW-FU-7-4
- `seed/fs.py` -- add public `never_write_match(path, *, repo_root, never_write, resolve_leaf=True)` returning `(pattern, matched_form)` or `None`: forms are the repo-relative path as written and the resolved one, each also with a trailing `/` when it is a directory; exempt is per form; `_guard` calls it -- DW-10-4-1, DW-FU-7-5-5
- `seed/verbs/preconditions.py` -- rung 4 calls `fs.never_write_match`; drop the `first_match` import and the duplicated exempt branch; correct the docstring/comment that call the symlinked-ancestor gap a stated bound -- DW-10-4-1
- `seed/detect/inventory.py` -- `ArtifactState.ESCAPING`, `EscapeRecord`, `Inventory.escaping` (default `()`), `classify` fills them, `escape_findings`; `writable_exemptions` adds the two manifest-declared symlink entries by id -- DW-10-3-9, DW-FU-7-5-5
- `seed/detect/findings.py` -- `FindingType.TARGET_ESCAPES_REPO` (`target-escapes-repo`, HARD) and its `REMEDIES` row
- `seed/verbs/adopt.py`, `seed/verbs/update.py`, `seed/verbs/check.py`, `cli/seed.py` -- carry `escape_findings(inventory)` on `AdoptResult`/`UpdateResult`, report them from `check`, render them in the adopt/update text and `--json`
- `tests/unit/test_seed_*.py` -- one new test per fix (manifest, fs, preconditions parity, inventory, plan build, adopt, check, symlink-through-`ensure_symlinks`), each failing when its fix is reverted; update the pins the new enum members move
- `deferred-work-ledger.md` -- close DW-10-3-9, DW-FU-7-4, DW-10-4-1, DW-FU-7-5-5 (`status: closed`, `resolved:` names 82.11)

**Acceptance Criteria:**
- Given the intent-contract Acceptance Criteria above, when `pyforge-marshal-test` and `pyforge-deps-test` run, then every one holds and the suite is green
- Given each of the four fixes reverted in turn, when its new test runs, then it fails (mutation, run in one command that restores the file)

## Spec Change Log

## Review Triage Log

- No review has run yet.

## Design Notes

One helper, two callers: rung 4 and `_guard` cannot disagree because rung 4 holds no match logic. A refusal on *either* form (as written, resolved) wins; `exempt` is judged per form, so a manifest-declared writable path stays writable under a symlinked ancestor (`docs -> real/`, exempt `docs/dreams/README.md`) and a path that only resolves into the protected set still refuses.

```
docs -> real/ ; never_write ("docs/dreams/*.md",)
write docs/dreams/x.md   written form "docs/dreams/x.md" matches -> refused (resolved "real/dreams/x.md" alone missed)
```

Directory node: when a form names a directory, `form + "/"` is matched too, so `**/planning-artifacts/**` covers `_bmad-output/projects/demo/planning-artifacts` and `_bmad-output/planning-artifacts`. The two manifest symlink entries would then refuse, so they join `writable_exemptions` by id (`planning-artifacts-symlink`, `implementation-artifacts-symlink`); the manifest itself is unchanged.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
