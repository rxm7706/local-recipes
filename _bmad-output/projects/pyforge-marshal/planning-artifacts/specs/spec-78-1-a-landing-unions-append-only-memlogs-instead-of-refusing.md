---
title: '78.1: A landing unions append-only memlogs instead of refusing'
type: 'feature'
created: '2026-09-30'
status: 'in-progress'
baseline_revision: '70d6e11a515a75838b7d6c5c9a5e24a96641204d'
flag-exempt: detector-or-gate   # the heal decides whether a landing merges: part of marshal's landing gate (spec-feature-flag-governance Q2; Story 74.2's precedent)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-59-1-a-ledger-only-conflict-is-healed-by-a-merge-of-origin-main-not-a-union-commit.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_heal.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_landing.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/vcs.py
  - _bmad/scripts/memlog.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** when a landing's forge merge fails, `dispatch land` runs `try_heal_dispatch_land_merge`
(`dispatch_land_heal.py`, CAP-4 / CAP-269). It measures conflicts against `refs/remotes/origin/main` and resolves exactly
one path mechanically, the landing project's own sprint ledger (`core/dispatch_landing.py::unknown_conflict_paths`).
Every other conflicted path escalates, and the landing is refused (MRS-DISP-038).

Every story's surface reconcile appends entries to Spec `.memlog.md` files: its own Spec's, and the co-governors'
(`spec-pyforge-core`, `spec-pyforge-unifying-strategy`). When two stories run at once, both append to the same memlogs,
and each append rewrites the frontmatter's `updated:`. The second to land conflicts on those files and is refused,
however clean its code. On 2026-09-30 that refused steward 74.1 (#1679), doctor 35.1 (#1682), steward 76.1 (#1683) and
doctor 36.2 (#1692, twice). Every one was landed by hand.

**Approach:** a conflicted `.memlog.md` joins the mechanical set when both sides only appended to it since the merge
base.

- A pure resolver in `core/dispatch_landing.py` takes the base, `main` and branch texts. It parses each the way
  `_bmad/scripts/memlog.py` writes them: a `---` frontmatter of `key: value` lines, then a body of lines.
  - If either side's body does not start with the base body line for line, the path is not append-only: return no
    resolution.
  - Otherwise the result body is `main`'s body, then each line the branch appended after the base, in order, skipping
    any line `main` already appended.
  - Frontmatter: `main`'s fields in `main`'s order. A field only the branch changed takes the branch's value.
    `updated:` takes the later stamp (ISO text compares correctly). Any other field both sides changed differently
    returns no resolution.
  - Render in `memlog.py`'s shape: `---`, the fields, `---`, a blank line, the body, one trailing newline.
- A classifier names a path a memlog when its basename is `.memlog.md`, in any project: co-governor memlogs live under
  other projects, and an append-only union is safe wherever it sits.
- `try_heal_dispatch_land_merge` stops escalating memlog paths up front. It reads the three texts through
  `VcsPort.file_text_at_ref`, as the ledger heal does, and resolves every conflicted memlog. Any memlog with no
  resolution escalates by name. The ledger's resolution and every memlog's go into the one `merge_ref_resolving` map, so
  one real merge of `origin/main` heals them all. Any other path still aborts that merge before a commit or push.
- `dispatch_land.py` records the healed memlog paths in the landing's data beside `ledger_union_heal`.

Ledger key: `78-1-a-landing-unions-append-only-memlogs-instead-of-refusing`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-283 (FR-230), which extends CAP-269 (FR-215) for this one path class.
- `spec-feature-flag-governance` Q2: `flag-exempt: detector-or-gate`. The heal decides whether a landing merges.

## Acceptance Criteria

- Given base, `main` and branch memlog texts where both sides appended entries and restamped `updated:` When the resolver runs Then it returns `main`'s frontmatter with the later `updated:`, `main`'s body, then the branch's appended lines in order, with no line twice
- Given a branch whose body rewrote, dropped or reordered a base line (or `main`'s did) When the resolver runs Then it returns no resolution
- Given a `topic:` (or any field other than `updated:`) both sides changed to different values When the resolver runs Then it returns no resolution; a field only one side changed takes that side's value
- Given a line both sides appended When the resolver runs Then it appears once, in `main`'s position
- Given a dispatch branch and `origin/main` in a bare-remote fixture whose only conflicts are two `.memlog.md` files both appended to When `dispatch land`'s heal runs Then the pushed head is a merge commit whose second parent is `origin/main`, each memlog holds every entry once, and the retried forge merge succeeds
- Given memlog and ledger conflicts together When the heal runs Then both resolve in the same merge commit
- Given a memlog with no resolution, or a memlog plus any other conflicted file When the heal runs Then the landing escalates naming the unresolved path, with nothing committed or pushed
- Given a healed landing When its record is written Then it names the healed memlog paths
- Given the memlog branch removed from the classifier When the bare-remote test runs Then it fails (mutation)

## Tasks

1. Read `dispatch_land_heal.py`, `core/dispatch_landing.py`'s ledger helpers, `ports/vcs.py::merge_ref_resolving`, and
   Story 59.1's heal tests in `tests/unit/test_dispatch_landing.py` (their bare-remote and forge-fake fixtures).
2. Add the pure resolver and the memlog classifier to `core/dispatch_landing.py`, with a table test covering every
   criterion above that names the resolver.
3. Rework the heal so the ledger and every conflicted memlog resolve into one `merge_ref_resolving` map; an unresolved
   memlog escalates by name.
4. Record the healed paths in `dispatch_land.py`'s landing data.
5. Add bare-remote heal tests beside Story 59.1's: memlogs only, memlogs plus ledger, an edited memlog, a memlog plus
   another file. Run the mutation by hand.
6. Run both `verify_commands`, then reconcile every Spec `spec-surface-check` names for the changed files: memlog first,
   `git add`, then a scoped `--write-baseline --spec` for each.

## Boundaries & Constraints

**Always:**
- Keep every entry from both sides, none twice. A resolution never drops a line to make a merge clean.
- Keep CAP-269's guarantees: the probe is `refs/remotes/origin/main`, one unresolvable path aborts the merge before any
  commit or push, a refused retry leaves remote `main` untouched.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not add any other file class to the mechanical set: not `scripts/.spec-surface-baseline.json`, not another
  project's ledger.
- Do not add a `VcsPort` method or change `merge_ref_resolving`'s contract.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| both appended | base + 2 on main, base + 1 on branch | main's body + the branch's line; later `updated:` | — |
| one side appended | only the branch appended | the branch's text; `updated:` the branch's | — |
| same line both sides | identical appended line | appears once | — |
| rewritten base line | branch edits an existing entry | no resolution | escalate by name |
| truncated body | a side drops trailing base lines | no resolution | escalate by name |
| other field both sides | `topic:` differs on both | no resolution | escalate by name |
| no frontmatter | a text without `---` | no resolution | escalate by name |
| memlog + ledger | both conflicted | one merge resolves both | — |
| memlog + other file | e.g. a `.py` file | — | escalate the other file, nothing committed |

</intent-contract>

## Code Map

Investigated 2026-09-30 (step 2). Paths are under `src/shared/packages/pyforge-marshal/`.

- `src/pyforge/marshal/core/dispatch_landing.py` -- pure home of the ledger helpers (`three_way_ledger_statuses`, `is_mechanical_conflict_path`, `unknown_conflict_paths`). Add `MEMLOG_BASENAME`, `is_memlog_path`, and the resolver `union_memlog_texts(base, main, branch) -> str | None` here. `core/` may not import `adapters` (AD-4), and `_bmad/scripts/memlog.py` is a script outside the package: mirror its `split` (first line `---`, closing fence the first later line that is exactly `---`, `key: value` lines split on the first `:` and stripped, body `lstrip("\n")`) and `render` (`---\n<fields>\n---\n\n<body rstripped>\n`) in the resolver; do not import it.
- `src/pyforge/marshal/dispatch_land_heal.py` -- `try_heal_dispatch_land_merge` (line 47) computes `unknown = unknown_conflict_paths(conflict_paths, ...)` up front and only enters the union heal when every conflicted path is the ledger. `_try_ledger_union_heal` (line 131) reads base/main/branch ledger text with `vcs.file_text_at_ref(git_repo_root, base_sha | probe | head_ref, rel)`, then one `vcs.merge_ref_resolving(worktree, probe, resolutions={ledger_rel: resolved}, message=...)`, `push`, retried `forge.merge_pr`. Rework: drop memlog paths from the `unknown` set, resolve the ledger only when it conflicted, resolve every conflicted memlog, and put all of them in the one `resolutions` map. `DispatchLandHealResult` gains `healed_memlog_paths: tuple[str, ...] = ()` (defaulted, so Story 59.1's `DispatchLandHealResult(healed=True, retried_forge_merge=True)` assertions still hold for a ledger-only heal).
- `src/pyforge/marshal/adapters/vcs_git.py:1171` -- `merge_ref_resolving` (read-only here, contract unchanged). It writes only the paths git left conflicted and ignores extra `resolutions` keys; a conflicted path with no resolution aborts the merge before any commit.
- `src/pyforge/marshal/dispatch_land.py:972-1043` -- the heal call and the landing record: `data["ledger_union_heal"] = True` when `heal.retried_forge_merge`. Add `data["memlog_union_heal"]` (the healed paths, as a list) beside it when non-empty. `ledger_union_heal` keeps its meaning "the union merge ran"; only `tests/unit/test_dispatch_landing.py:1129` reads it.
- `tests/meta/test_local_branch_refs_are_full_refnames.py` -- AST scan that every `vcs.file_text_at_ref` ref is a full ref or sha; keep the heal's variable names `probe`, `head_ref`, `base_sha` so the new reads stay inside it.
- `tests/unit/test_dispatch_land_heal.py:350-600` -- Story 59.1's bare-remote fixtures (`_landing`, `_HonestForge`, `_heal`, `_generated_ledger`). Task 1 names `tests/unit/test_dispatch_landing.py`; the heal fixtures are here, and `test_dispatch_landing.py:1129` is the landing-record test. Add the resolver table test and the bare-remote memlog tests in this file; add the record test beside line 1129.
- `_bmad/scripts/memlog.py:90-113` -- the file shape the resolver parses and renders.

## Binding

Parent capability: `spec-pyforge-marshal` CAP-283 (FR-230).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-09-30 entry.
Ledger key: `78-1-a-landing-unions-append-only-memlogs-instead-of-refusing`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: none; `flag-exempt: detector-or-gate`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- The mutation in Task 5 — expected: the bare-remote memlog test fails with the classifier's memlog branch removed.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
