---
chain: pyforge-marshal
created: 2026-10-04
updated: 2026-10-04
status: draft
type: research-drafts
title: "Preserved-work refs: drafts (Dream entry, Spec delta, AD amendments, stories)"
companion: preserved-work-refs-2026-10-04.md
---

# Preserved-work refs: drafts

These are drafts of candidate B from `preserved-work-refs-2026-10-04.md` § 7, and nothing in them is
applied. Each draft names the surface it would land on. Applying them follows the Dream-first chain
(AGENTS.md § Dream-first workflow):
1. Append the Dream entry.
2. `bmad-spec` mints the CAP. Its memlog lines are appended with `uv run _bmad/scripts/memlog.py`;
   `SPEC.md` is never hand-edited.
3. Run the PRD and spine currency cascade.
4. Add the stories to `epics.md` with their ledger rows (Tier-3 feed, then `sprint-ledger-sync`).
5. Write a tracked story spec per story.

Numbers assume the state measured on 2026-10-04. Marshal's highest CAP is 286, its PRD's highest FR
is FR-233, and its highest AD is AD-80. Steward's highest CAP is 164. Marshal Epic 87 / Story 87.1
and steward Epic 85 / Story 85.1 exist only on the unmerged branch `chain-sweeper-protected-refs`.
Renumber if anything lands first.

---

## (a) Dream entries

### `docs/dreams/pyforge-marshal.md` § Realization log

Insert directly above the `2026-10-04 (later)` entry, which is the newest:

```markdown
- **2026-10-04 (later, research)** — **Found: preserved work has nine names and no definition, and
  most of it is not durable.** The repo keeps "preserved" work under `attempt-preserve/*`,
  `refs/attempt-preserve-dirty/*`, 698 `rescue/*` tags, 45 `archive/*` tags, `bmad-loop-preserve/*`,
  `backup/*`, `recover/*`, gitignored `failed/<story>/changes.patch` files, steward tarballs and the
  sweeper's patch directories. Every protection is a name list, but survival depends on reachability
  from `origin`. Measured: 16 of 17 dirty snapshot refs and 3 local tags hold commits on no `origin`
  ref; 8 of the 30 retired tips and 98 of the tips deleted today are reachable from nothing.
  bmad-loop prunes `attempt-preserve/*` at every run start, while this repo parks durable work under
  that prefix. Tags are unprotected server-side. The unpushed-work detector reports 0 dangling
  commits because `git fsck` exits 1, while 20,135 exist, 19,412 of them marshal's own merged-check
  objects. `marshal land` and Story 87.1's `--retire` both delete refs the new ruleset protects.
  **What it looks like when fixed:** one rule in every mode (spin, dispatch on every harness, drain,
  bare bmad-loop, bmad-build, bmad-build-auto, hand `land/*` rebuilds, steward workspaces, Claude
  Code and Cursor agent worktrees). Work outlives its working copy only as a commit reachable from an
  annotated `preserve/` tag on `origin`. Nothing removes a working copy whose unique content has no
  such tag. Retirement adds an `archive/<ref path>` twin and never removes reachability. One declared
  list drives the rulesets, the hook and every in-code deleter. **Constraints:** upstream names stay;
  marshal promotes them and renders `preserve_keep = 0`. Any upstream PR needs an explicit operator
  ask. Legacy `rescue/*` and `archive/*` tags are frozen, not migrated. Nothing is deleted without an
  operator ruling. Owner `spec-pyforge-marshal` (co-governors `spec-pyforge-steward`; `spec-pyforge-core`
  if the grammar is a kernel module). → CAP-287, AD-81, Stories 87.2–87.12 (87.1 amended),
  steward 85.2–85.3 (85.1 amended). Research:
  `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04.md`.
```

### `docs/dreams/pyforge-steward.md` § Realization log (twin)

```markdown
- **2026-10-04 (later) — Found: the protected-ref list is branch-only and nowhere declared.** The
  hook rule Story 85.1 adds covers branch deletion only. Tag deletion, `update-ref -d`,
  `fetch --prune-tags`, `push --mirror` and `rm` of a loop home pass. The GitHub ruleset that holds
  the same list lives only in repo settings, and `steward workspace clean` keeps unlanded work as a
  host-local tarball. **What it looks like when fixed:** the roster declares the protected refs once,
  as full refnames, branches and tags. The hook, marshal's sweeper and the live rulesets all match
  it, and a runtime check proves the rulesets do. `workspace clean` parks unlanded commits as a
  `preserve/` tag before it removes a worktree. **Constraints:** changing the list is a governance
  act; creating the tag ruleset is the operator's settings change. → CAP-165, Stories 85.2–85.3,
  85.1 amended; marshal twin CAP-287.
```

---

## (b) Spec delta — `spec-pyforge-marshal` CAP-287

### House-format bullet (for `bmad-spec` to derive into SPEC.md § Capabilities)

```markdown
- **CAP-287 — preserved work is an annotated tag on origin, and nothing destroys a working copy it
  does not yet hold** ← spec-pyforge-marshal CAP-287 (draft 2026-10-04)
  - **intent:** every execution mode that can lose work preserves it the same way: a commit
    reachable from an annotated tag
    `preserve/<project-slug>/<story-key>/<producer>-<YYYY-MM-DD>-<sha8>` (or
    `preserve/unbound/<producer>-<YYYY-MM-DD>-<sha8>`), pushed to `origin`, that carries its
    provenance in trailers. Producers (closed vocabulary `bmad-loop`, `intent-gap`, `dispatch`,
    `build`, `sweep`, `workspace`, `dangling`, `hand`) write it at failure, stop, block, revert,
    re-drive, orphan reclaim and before any removal. Upstream bmad-loop's `attempt-preserve/*` and
    `refs/attempt-preserve-dirty/*` stay as named; marshal promotes them on sight and renders
    `preserve_keep = 0`. A `preserve/` tag is append-only. It retires by gaining an annotated twin
    at `archive/<its ref path>`. No marshal command, script or rendered policy removes a branch,
    worktree, run directory or patch whose unique content no `preserve/` or `archive/` tag on
    `origin` holds, and none ever deletes a tag. (Operator ask 2026-10-04, after a hand-rolled
    cleanup deleted the loop homes, `loop/*` and 33 `attempt-preserve/*` on `origin`, and the
    research measured 98 deleted tips reachable from nothing.)
  - **success:** against real git repositories with a bare `origin` and harness fakes, no network:
    - each producer (spin intent gap, bmad-loop promotion, dispatch failed / stopped / blocked,
      drain cycle, sweeper, the `build` fact) yields exactly one well-formed annotated tag on
      `origin` per preserved commit, with every trailer;
    - a dirty tree is snapshotted with its untracked files and no branch moves;
    - each guarded deleter refuses on an unpreserved working copy: teardown, the sweeper's
      PRESERVE-THEN-DELETE and `--retire`, and retire;
    - `marshal land` never deletes a `loop/*` head;
    - `retire` and the sweeper never touch `refs/tags/**`;
    - the rendered policy has `preserve_keep = 0`;
    - the unpushed-work detector exits could-not-observe on a git error;
    - every preserve reader accepts `preserve/` tags and `origin`-only refs;
    - the grammar has one parser that every consumer imports;
    - `pyforge-marshal-test` and `scripts-suite` are green.
```

### Five fields (the neutral contract `bmad-spec` distils)

**1. Intent.** Make "is this work saved?" a reachability fact with one answer in every mode, and stop
every tool, skill and hand path from creating a preserve that is not durable or deleting one that
is. The tools covered are marshal spin, dispatch and drain, bare bmad-loop under marshal's rendered
policy, the sweeper, the detectors, and status. The skills are bmad-build and bmad-build-auto. The
hand paths are `land/*` rebuilds and agent worktrees. Steward's hook, roster, rulesets and workspace
clean are the co-governed half.

**2. Acceptance criteria.** Each is machine-checkable; the oracle for each is in field 4.

| # | Criterion |
|---|---|
| AC-1 | `preserve_refs.parse(name)` round-trips every name `preserve_refs.render(...)` emits, for both shapes and every producer. It rejects any other name under `refs/tags/preserve/`. No module outside the grammar module matches the string `preserve/` with a regex (a meta-test greps `src/` and `scripts/`). |
| AC-2 | `marshal preserve tag` on a dirty worktree creates one annotated tag whose commit's tree equals the working tree, including untracked non-ignored files. No branch moves, and `origin` holds the tag. Offline, the tag exists locally and the command exits with the "pending push" finding, never success-and-silent. Re-running on the same object is a no-op; the same name on a different object is refused. |
| AC-3 | The tag message carries `Preserve-Producer`, `Preserve-Provenance`, `Preserve-Reason`, `Preserve-Source`, `Preserve-Run`, `Preserve-Journal` and `Preserve-Commit`. `marshal preserve list --json` returns them parsed, filterable by station, story, producer and state (`open`, or `retired` when an `archive/` twin exists). |
| AC-4 | **Spin.** For each bmad-loop journal event `attempt-commits-preserved`, `attempt-worktree-preserved`, `worktree-kept` or `story-deferred` naming work, the supervisor writes the matching `preserve/…/bmad-loop-…` tag and pushes it at the next stage boundary. The intent-gap path writes `preserve/…/intent-gap-…` and never creates an `attempt-preserve/*` ref. The rendered `[scm]` has `preserve_keep = 0`. |
| AC-5 | **Dispatch.** A run that ends `failed`, `stopped_externally` or `blocked` with git progress yields a `preserve/…/dispatch-…` tag on `origin`, on every harness profile in `harness_preference`. The `dispatch-preserve` outcome payload names it, and `marshal status` shows it in the row. |
| AC-6 | **Drain.** A campaign cycle that holds, blocks or stops a story records that story's preserve tag in the `dispatch-fleet-cycle` entry, or a finding naming the story when none exists. |
| AC-7 | **Teardown** refuses while the home holds a `failed/*/changes.patch`, a kept-failed unit branch, an unpromoted scratch ref, or an unpushed `loop/<slug>` with unique content, unless each is named in `--abandon`. **Retire** excludes `refs/tags/**` and every protected prefix structurally. **Land** never passes `--delete-branch` for a `loop/*` head, and journals `branch_retired` from a post-merge remote fact. |
| AC-8 | **Sweeper.** PRESERVE-THEN-DELETE writes a `sweep` tag on `origin` before it removes the worktree. `--retire` writes an `archive/` twin and refuses a delete the declared list forbids. A worktree locked by a dead pid is reported `stale-lock`. An empty, unregistered directory under `.claude/worktrees/`, `.cursor/worktrees/` or `~/.cursor/worktrees/` is DELETE; a non-empty one is INSPECT; `~/.bmad-loops/` is never touched. |
| AC-9 | **Detectors.** `unpushed_work_check.py` exits 2 (could-not-observe) when any git call it depends on fails. It reports local-only tags and custom refs whose commits are on no `origin` ref, and its remedy names `marshal preserve tag`. `missing_preserve_check.py`, `bmad_loop_baseline_drift_check.py` and `fleet_picture.py` count a `preserve/` tag, or an `origin`-only ref, as present. |
| AC-10 | **Status (AD-48).** A row reports preserve debt: local-only preserve tags, unpromoted scratch refs, patches with no tag. An unpushed ref that matches no row is reported fleet-wide, never discarded. |
| AC-11 | `adapters/vcs_git.py`'s merged-check and merge-tree preview objects are written to a temporary object directory. A run of `is_branch_merged` leaves `git count-objects` unchanged. |
| AC-12 | Every new rule has a test that fails when the rule is removed (mutation). |

**3. Boundaries.**
- **Always:**
  - Dry run by default for anything that deletes.
  - Write before acting (AD-6): journal the preserve before reporting success.
  - Use full refnames everywhere (Story 61.1).
  - Dates are `YYYY-MM-DD`.
  - One grammar module.
  - Test with real git and a bare remote.
- **Never:**
  - Rename or patch bmad-loop (AD-2).
  - Delete a `preserve/` or `archive/` tag.
  - Push a branch that the declared list forbids updating.
  - Call GitHub in tests.
  - Treat a name as proof of durability.

**4. Verification oracle.**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`, exit 0.
- `pixi run --frozen -e pyforge-guild scripts-suite`, exit 0.
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_unpushed_work_check_full_ref.py tests/scripts/test_unpushed_work_check.py tests/scripts/test_missing_preserve_check.py tests/scripts/test_worktree_sweep.py -q`, exit 0.
- The grammar meta-test (AC-1) and the object-count test (AC-11) are part of those suites.
- Live read-only checks, run by the operator after landing:
  - `git for-each-ref refs/tags/preserve/ --format='%(objecttype)'` prints only `tag`;
  - `python scripts/unpushed_work_check.py --json` exits non-zero while `git fsck` is unhealthy.

**5. Out of scope.**
- Any upstream bmad-loop change (Option D; operator ask only).
- Re-tagging the 698 `rescue/*` and 45 `archive/*` legacy tags. They stay frozen; a purge is a
  separate operator act.
- AD-29's "declared durable local ref" for spec promotions. A preserve tag could serve it, but
  that is not claimed here.
- Server settings changes. Steward's CAP-165 declares them; the operator applies them.
- `main`'s own server protection.
- Repairing the two empty loose objects.

**Co-governing Specs.**
- `spec-pyforge-steward`, CAP-165 (new) and CAP-155 (amended): the hook, the roster, the declared
  rulesets with their parity check, and `workspace clean`.
- `spec-pyforge-core`, CAP-12 (new): only if the operator puts the grammar in
  `pyforge.core.preserve_refs`, on the AD-73 precedent. Otherwise the grammar lives in
  `M/core/preserve_refs.py`, and steward reaches it through the `marshal preserve` CLI.
- Doctor is not a co-governor. No detector moves into `pyforge.doctor.sources` unless the operator
  chooses doctor for the parity check (research Q8).

**Feature flag (`spec-feature-flag-governance` Q1/Q2).**
- `type: feature` stories under CAP-287 carry the flag `pyforge.marshal.preserve_refs` (owner
  marshal) in `src/platform/config/flags.json`.
- Detector stories use the Q2 exemption `detector-or-gate`.
- `fix` stories need no flag.

### Steward CAP-165 (house format)

```markdown
- **CAP-165 — the protected refs are declared once, and the live rulesets are proven to match** ←
  spec-pyforge-steward CAP-165 (draft 2026-10-04; extends CAP-5)
  - **intent:** `docs/governance/guild-roster.json` gains `protected_refs`: full refnames with a
    `kind` (`operational-branch`, `preserve-tag`, `archive-tag`, `legacy`) and the server rules each
    needs. The session hook, marshal's sweeper and in-code deleters read only this list. A declared
    ruleset document under `docs/governance/` renders the list into GitHub ruleset JSON (branch and
    tag). A runtime detector compares that document with the live rulesets through an authenticated
    `gh api`, and fails closed when unauthenticated or rate-limited. Applying a ruleset is the
    operator's act; the detector only reports drift.
  - **success:** the hook denies every deletion form listed in Story 85.1 (amended) for each list
    entry, and allows the same forms for an unlisted ref. The detector exits 0 on a matching
    fixture, 1 naming each missing or extra pattern and rule, and 2 when `gh api rate_limit` shows
    no authenticated quota. `pyforge-steward-test` and `detectors-ci` are green.
```

CAP-155 amendment (one line appended to its intent): "*An unlanded worktree's commits are parked as
a `preserve/<slug>/<key>/workspace-<date>-<sha8>` tag on `origin` (or `preserve/unbound/…`) before
the worktree is removed. The tarball keeps only gitignored and untracked bytes and is reported as
host-local.*"

### PRD delta — `prd-pyforge-marshal-2026-07-25/prd.md`

```markdown
#### FR-234: Preserved work is a protected tag on origin, in every mode *(added 2026-10-04 — research `preserved-work-refs-2026-10-04.md`)* ← CAP-287
Every mode that can lose work preserves it as an annotated `preserve/` tag on `origin`; nothing
removes a working copy whose unique content no such tag holds; retirement adds an `archive/` twin.
**Consequences:**
- Upstream `attempt-preserve/*` and `refs/attempt-preserve-dirty/*` are scratch: promoted on sight,
  never pushed, never treated as the record; `preserve_keep = 0` is rendered.
- `marshal land` never deletes a `loop/*` head; teardown refuses unpreserved runtime work; retire
  and the sweeper never touch tags.
- Detectors fail closed and read tags, custom refs and `origin`, not only local `refs/heads`.
- *Motivating evidence: measured 2026-10-04: 494 branch deletions in one hour, 98 tips left
  reachable from nothing, 8 of them from an operator retirement; 20,135 dangling commits reported
  as 0 by the durability detector.*
```

### Memlog lines (append with `uv run _bmad/scripts/memlog.py append --workspace <spec-folder> …`)

- `spec-pyforge-marshal`, decision: *"2026-10-04 (research): candidate B of
  preserved-work-refs-2026-10-04.md — one rule (annotated `preserve/` tag on origin; `archive/` twin
  retirement; promotion of upstream scratch; `preserve_keep = 0`). Pending operator ruling on Q1–Q12."*
- `spec-pyforge-marshal`, capability: the CAP-287 bullet above, once ruled.
- `spec-pyforge-steward`, capability: the CAP-165 bullet above, and the CAP-155 amendment.

---

## (c) Architecture amendments — `ARCHITECTURE-SPINE.md`

### New: AD-81 — Preserved work is a protected, annotated tag on origin; a name is not durability

- **Binds:**
  - FR-234 / CAP-287.
  - It extends AD-29 (durability is reachability), AD-46 (stage-bound push), AD-47 (retirement),
    AD-48 (durability in status) and AD-74 (detect → preserve → defer-loud).
  - It carries CAP-11's `archive/<original path>` from files to refs.
- **Prevents:**
  - A "preserved" commit that exists only on one disk.
  - A preserve under a prefix whose owner prunes it.
  - A retirement or cleanup that leaves commits reachable from nothing.
  - The 2026-10-04 shape: 464 branches deleted in one hour, 98 tips orphaned, 8 of them by a ruling
    meant only to retire.
- **Rule:**
  - Work outlives its working copy only as a commit reachable from an annotated tag
    `refs/tags/preserve/<project-slug>/<story-key>/<producer>-<YYYY-MM-DD>-<sha8>` (or
    `…/preserve/unbound/…`) that exists on `origin`. A working copy is a branch, worktree, run
    directory, patch file or tarball.
  - **One module** renders and parses the name. Every consumer imports it, as with AD-73.
  - The producer vocabulary is closed. The trailers carry provenance, including `machine|human`.
  - No process removes a working copy whose unique content no `preserve/` or `archive/` tag on
    `origin` holds. "Unique" is judged by ancestry, then patch-id, then tree, never by name.
  - `preserve/` tags are append-only: never moved, never deleted. A preserve retires by gaining an
    annotated twin `refs/tags/archive/<its ref path>`, carrying `Archive-From`, `Archive-Reason`
    and `Archive-Evidence`. A retired working branch is deleted only after its archive twin exists
    on `origin`.
  - Deleting a `preserve/` or `archive/` tag is a **purge**: an operator act by explicit name,
    after a manifest is committed to git, needing a deliberate ruleset change.
  - Upstream engine refs (`attempt-preserve/*`, `refs/attempt-preserve-dirty/*`) are **scratch**.
    Marshal promotes them when the engine journals them, renders `preserve_keep = 0`, and never
    pushes them.
  - The protected list is declared once, in steward's roster, as full refnames. The server
    rulesets, the session hook and every in-code deleter enforce that same list.
  - Durable must not require the network (AD-29 F-14). An offline preserve is a local tag reported
    *pending* until pushed.

### AD-47 — as amended in place (changes marked **[2026-10-04]**)

- **Binds:**
  - FR-63, and **[2026-10-04]** FR-234 / AD-81.
  - It extends AD-27 (an allowlist only narrows), and FR-8's teardown refusal semantics.
- **Prevents:**
  - A retirement sweep silently deleting a branch on a heuristic diff.
  - **[2026-10-04]** A retirement that removes reachability.
  - **[2026-10-04]** Two retirement paths disagreeing about an operational branch.
- **Rule:**
  - A branch retires only when three independently-provable facts hold: content reachable in the
    integration branch **by patch-id**, its run concluded, and its story `done` with a recorded
    merge sha.
  - **[2026-10-04]** Retirement first writes an annotated `archive/<branch path>` twin on `origin`
    (AD-81), then deletes the branch.
  - `loop/*` is a **structural** exclusion, never policy-configurable.
  - **[2026-10-04]** So is all of `refs/tags/**`: tags are never candidates. The old wording
    "`rescue/*` tags" is subsumed. So is every entry of the declared protected list.
  - **[2026-10-04]** The same exclusion binds FR-59's per-landing retirement (AD-40). A landing
    never deletes a `loop/*` head, and only `marshal teardown` removes one, under AD-81's preserve
    precondition. So the two paths cannot disagree on a station branch's fate.
  - Dry run by default. A proposed retirement with unproven evidence is refused, never defaulted to
    delete.

### AD-48 — as amended in place (changes marked **[2026-10-04]**)

- **Binds:**
  - FR-62, and **[2026-10-04]** FR-234 / AD-81.
  - It extends AD-38 and AD-39.
- **Prevents:**
  - "Is the fleet's work saved?" ever again requiring a command outside `marshal status`.
  - **[2026-10-04]** A status that reads clean because its detector could not look.
- **Rule:**
  - The fleet-status envelope carries an unpushed-work finding per row, **read from** the same
    evidence the unpushed-work detector already computes, never re-implemented against git directly.
  - **[2026-10-04]** It also carries a per-row **preserve-debt** finding: local-only `preserve/`
    tags, unpromoted engine scratch refs, and patches or tarballs with no tag.
  - **[2026-10-04]** Any unpushed ref that matches no row is reported fleet-wide, never discarded.
  - **[2026-10-04]** A detector that cannot observe is could-not-observe in the envelope, never
    zero findings.
  - A row with unpushed content or preserve debt is never reported clean.

### One-line amendments

- **AD-40** (append to the Rule): *"Landing never deletes an operational branch (`loop/*`); see
  AD-47 as amended 2026-10-04."*
- **AD-74** (append to the Rule): *"Since 2026-10-04 the preserve step means AD-81's `preserve/`
  tag; the patch file and the engine's scratch ref are conveniences, not the record."*

---

## (d) Stories

Conventions follow marshal's `epics.md`:
- **Type • Effort • Deps • FR/AD**, then **Surface**, then Given/When/Then criteria.
- Every story also carries the station's verification commands: `pyforge-marshal-test`,
  `pyforge-deps-test`, and `scripts-suite` for scripts.
- Execution order: the urgent `fix` stories (87.2, 87.6, 87.10) and steward 85.1 can land first.
  87.3 gates the producer stories. 87.12 is operator-gated.

### Story 87.1 (chained) — required changes before it lands

1. **Read `protected_refs` (full refnames, both kinds) from the roster**, not
   `protected_ref_prefixes`. The fallback constant becomes
   `("refs/heads/loop/", "refs/heads/attempt-preserve/", "refs/tags/preserve/", "refs/tags/archive/", "refs/tags/rescue/")`.
2. **`--retire <branch>`:**
   - First write an annotated `archive/<branch path>` tag at the branch tip, push it, and verify it
     with `ls-remote`.
   - Delete the branch only when the declared list allows deletion of that ref. For a
     ruleset-protected branch (`loop/*`, and `attempt-preserve/*` until Q3 is ruled), refuse with a
     finding naming the ruleset and the operator act it needs.
   - A GitHub refusal is a reported outcome, never a crash.

   The current AC ("Then the named branches are deleted") cannot pass against ruleset 24451573,
   which has no bypass.
3. **Never touch `refs/tags/**`**, in either mode.
4. **The manifest becomes a tracked file.** It stays under `--preserve-dir`, and its rows also carry
   the archive tag name.
5. **Add the AC:**

   **Given** a remote branch whose tip's unique content no tag holds,
   **When** `--remote --execute` would DELETE it,
   **Then** it first writes an `archive/<path>` twin and the manifest names it.

Everything else in 87.1 stands.

### Story 87.2 — The unpushed-work detector fails closed and sees tags and custom refs

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** FR-62, AD-48 • flag-exempt `detector-or-gate`

**Surface:** `scripts/unpushed_work_check.py` (`:65-71`, `:105-170`), `tests/scripts/test_unpushed_work_check_full_ref.py` (existing) and a new `tests/scripts/test_unpushed_work_check.py`

**Acceptance criteria:**
- **Given** a repository where `git fsck --no-reflogs` exits non-zero
  **When** the detector runs without `--branches-only`
  **Then** it exits 2 (could-not-observe) and names the failing command; it never reports 0 dangling commits.
- **Given** a local-only tag, and a `refs/<custom>/*` ref, each holding a commit on no `origin` ref
  **When** the detector runs
  **Then** each is a finding of kind `unpushed-ref` with its full refname.
- **Given** a dangling-commit finding
  **When** the remedy prints
  **Then** it names `marshal preserve tag --producer dangling <sha>`, not `git tag rescue/dangling-…`
  (until 87.3 lands, the old remedy stays behind the flag check).
- **Given** each rule removed
  **When** the tests run
  **Then** they fail.

### Story 87.3 — Preserved work has one grammar and one verb

**Type:** feature (CAP-287, flag `pyforge.marshal.preserve_refs`) • **Effort:** M • **Deps:** — • **FR/AD:** FR-234, AD-81

**Surface:**
- `M/core/preserve_refs.py` (new; or `C/preserve_refs.py` per research Q13);
- `M/cli/preserve.py` (new verb `marshal preserve tag|list|retire|promote`);
- `M/cli/main.py` (registration);
- `M/ports/vcs.py`, `M/adapters/vcs_git.py` (annotated tag create and push; snapshot commit with untracked files and no branch move);
- the marshal MCP face (CLI⇄tool parity, Epic 18);
- `tests/unit/test_preserve_refs.py`, `tests/integration/test_preserve_cli.py`.

**Acceptance criteria:**
- **Given** every producer and both shapes
  **When** a name is rendered then parsed
  **Then** it round-trips; any other name under `refs/tags/preserve/` is rejected. A meta-test fails
  if a module outside the grammar module matches `preserve/` by regex.
- **Given** a dirty worktree with an untracked file
  **When** `marshal preserve tag --story <slug> <N.M> --producer hand --from <worktree>` runs
  **Then** one annotated tag exists on the bare `origin`; its commit's tree includes the untracked
  file; no branch moved; all seven trailers are present.
- **Given** no network
  **When** it runs
  **Then** the tag exists locally and the envelope carries a `pending-push` finding.
- **Given** the same name on the same object
  **Then** it is a no-op; on a different object it is refused.
- **Given** a tag with an `archive/` twin
  **When** `marshal preserve list --json --state open` runs
  **Then** the tag is absent; with `--state retired` it is present.
- **Given** `marshal preserve retire <tag>`
  **Then** it writes the annotated `archive/<tag path>` twin on `origin` and never deletes anything.
- **Given** the flag off
  **Then** the verb is listed disabled and refuses with the usage exit code (flag governance Q3).

### Story 87.4 — Spin parks every attempt as a preserve tag before bmad-loop can prune it

**Type:** feature (CAP-287, flag) • **Effort:** M • **Deps:** 87.3 • **FR/AD:** FR-234, FR-189, AD-81, AD-74

**Surface:**
- `M/adapters/harness_bmadloop.py:392` (`preserve_keep = 0`; the pin tests of AD-78);
- `M/supervisor/__main__.py:1798-1813` (stage-boundary loop), `:3137-3215` (intent gap);
- `M/supervisor/intent_gap_preserve.py:123-169, 291-295`;
- `M/supervisor/durability.py:73-77`;
- `M/core/status.py:906-909` (`escalated_preserve_ref`);
- tests `tests/unit/test_intent_gap_preserve.py`, `tests/unit/test_supervisor.py`, `tests/unit/test_harness_bmadloop*.py`.

**Acceptance criteria:**
- **Given** a rendered home policy
  **Then** `[scm] preserve_keep = 0`, and the policy still passes `bmad-loop validate` with zero warnings.
- **Given** a bmad-loop journal line `attempt-commits-preserved` (`ref=attempt-preserve/<run>-<sha8>`), `attempt-worktree-preserved` (`ref=refs/attempt-preserve-dirty/…`), `worktree-kept` or `story-deferred` with a `preserve_ref`
  **When** the supervisor reaches the next stage boundary
  **Then** a `preserve/<slug>/<key>/bmad-loop-<date>-<sha8>` tag exists on `origin`, with `Preserve-Source` naming the engine ref, and a `stage-push` journal entry records it.
- **Given** an intent-gap escalation with an empty `preserve_ref`
  **When** the supervisor parks the attempt
  **Then** it writes `preserve/…/intent-gap-…`, creates no `attempt-preserve/*` ref, and the spec notice and the `escalation-detected` payload name the tag.
- **Given** a park that cannot push (offline)
  **Then** the escalation still names the local tag, and status shows preserve debt.

### Story 87.5 — Dispatch and drain preserve a stopped story's work as a tag on origin

**Type:** feature (CAP-287, flag) • **Effort:** M • **Deps:** 87.3 • **FR/AD:** FR-234, FR-193, AD-75, AD-81

**Surface:**
- `M/dispatch_supervisor/__main__.py:287-347` (`_journal_dispatch_preserve`), `:2735-2746` (call condition);
- `M/core/dispatch_preserve.py`;
- `M/adapters/vcs_git.py:815-848` (`worktree_unified_patch` excludes untracked files);
- `M/cli/dispatch.py:1437-1441` (journal facts), `:2480` (`dispatch_once`), `:5572` (`run_fleet_drain`);
- `M/core/dispatch_fleet.py:35, 52-53`;
- `M/core/status.py:1241-1242`;
- tests `tests/unit/test_dispatch_supervisor_main_loop.py`, `tests/unit/test_dispatch_survival.py`, `tests/unit/test_dispatch_fleet*.py`.

**Acceptance criteria:**
- **Given** a dispatch run whose terminal verdict is `failed`, `stopped_externally` or `blocked` and whose worktree has commits or uncommitted changes (including untracked files) above baseline
  **When** the supervisor concludes
  **Then** a `preserve/<slug>/<key>/dispatch-<date>-<sha8>` tag exists on `origin`; the `dispatch-preserve` outcome payload carries `preserve_tag`; the patch file is still written.
- **Given** each profile in `harness_preference` (`claude`, `cursor`, `copilot`, `gemini`, `devin`), run through the harness fake
  **Then** the same tag results; no profile branches the preserve path.
- **Given** a campaign (`--stories`, `--campaign`, `--max-in-flight`) whose cycle holds, blocks or stops a story
  **When** the `dispatch-fleet-cycle` entry is written
  **Then** it names that story's preserve tag, or carries a finding naming the story when none exists.
- **Given** `marshal status` for that station
  **Then** the row shows `dispatch_preserve_tag`.

### Story 87.6 — Land, retire and the station branch never fight the protected list

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** FR-59, FR-63, AD-40, AD-47 (as amended)

**Surface:** `M/cli/land.py:438, 507, 979-1088`; `M/adapters/forge_gh.py:375-387`; `M/core/retire.py:53, 97-105`; `M/cli/retire.py:274-432`; tests `tests/unit/test_land.py`, `tests/unit/test_forge_gh.py`, `tests/unit/test_retire.py`

**Acceptance criteria:**
- **Given** `landing_branch_retirement = true` and a `loop/<slug>` head
  **When** `marshal land` merges
  **Then** `gh pr merge` is called without `--delete-branch`, and a WARN finding names AD-47.
- **Given** a merge that requested a branch delete
  **When** the journal entry is written
  **Then** `branch_retired` comes from a post-merge `ls-remote` fact, never from the request.
- **Given** a candidate named `refs/tags/…`, `preserve/…`, `archive/…`, `rescue/…` or any declared protected ref
  **When** `marshal retire` evaluates it
  **Then** it is structurally excluded before evidence-gathering, with no policy key.
- **Given** each rule removed
  **Then** a test fails.

### Story 87.7 — Teardown refuses to remove a loop home that holds unpreserved work

**Type:** feature (CAP-287, flag) • **Effort:** M • **Deps:** 87.3, 87.4 • **FR/AD:** FR-8, FR-234, AD-29, AD-81

**Surface:** `M/cli/init.py:2292-2702` (`run_teardown`, removal at `:2662`, `-D` at `:2682`); tests `tests/unit/test_init.py`, `tests/integration/test_init_worktree.py`

**Acceptance criteria:**
- **Given** a home holding any of the following:
  - a non-empty `.bmad-loop/runs/*/failed/*/changes.patch`;
  - a kept-failed `bmad-loop/<run>/<story>` branch or worktree with commits on no `origin` ref;
  - an unpromoted `attempt-preserve/*` or `refs/attempt-preserve-dirty/*` ref;
  - a `loop/<slug>` ahead of `origin`

  **When** `marshal teardown` runs
  **Then** it refuses with `MRS-TEARDOWN-*` findings naming each item. `--force --abandon <item>…` must name every one; a partial list is refused.
- **Given** every such item already held by a `preserve/` tag on `origin`
  **Then** teardown proceeds as today.

### Story 87.8 — The sweeper preserves to tags and retires agent and orphan worktrees

**Type:** feature (CAP-287, flag) • **Effort:** M • **Deps:** 87.1, 87.3 • **FR/AD:** FR-234, AD-81

**Surface:** `scripts/worktree_sweep.py:63, 113-133, 191, 244-261, 276-288`; `tests/scripts/test_worktree_sweep.py`; `docs/how-to/manage-worktrees-with-bmad.md:39-46`

**Acceptance criteria:**
- **Given** a PRESERVE-THEN-DELETE verdict
  **When** `--execute` runs
  **Then** a `sweep` preserve tag exists on `origin` before `git worktree remove`; nothing is written to `~/.local/state/pyforge-marshal/worktree-preserve` any more.
- **Given** a worktree locked as `claude agent <id> (pid N start T)` whose pid is dead, or whose `/proc/<pid>/stat` start time differs (pid reuse)
  **Then** the verdict is `STALE-LOCK`, with the usual merged/unmerged evidence; a live lock stays KEEP.
- **Given** an unregistered directory under `.claude/worktrees/`, `.cursor/worktrees/` or `~/.cursor/worktrees/`
  **Then** it is `ORPHAN-DIR`: DELETE when empty, INSPECT otherwise. Nothing under `~/.bmad-loops/` is ever listed.
- **Given** `--delete-merged-local-branches`
  **Then** a merged local branch whose tip is not an ancestor of `main`, but is patch-id-equivalent, is reported, not deleted.

### Story 87.9 — Every preserve reader sees preserve tags and origin

**Type:** feature (CAP-287), flag-exempt `detector-or-gate` • **Effort:** S • **Deps:** 87.3 • **FR/AD:** FR-62, FR-176, FR-189, AD-48 (as amended)

**Surface:**
- `scripts/missing_preserve_check.py:78, 146-224`;
- `scripts/bmad_loop_baseline_drift_check.py:111-118`;
- `scripts/fleet_picture.py:790-795`;
- `M/cli/status.py:1198, 1226-1251, 1255`;
- `M/core/status.py:1110-1128`;
- tests `tests/scripts/test_missing_preserve_check.py`, `tests/scripts/test_bmad_loop_baseline_drift_check.py`, `tests/unit/test_status.py`.

**Acceptance criteria:**
- **Given** an intent-gap halt whose `preserve_ref` names a `preserve/` tag, or an `attempt-preserve/*` branch that exists only on `origin`
  **When** `missing-preserve-check` runs
  **Then** there is no finding. A ref that exists nowhere is still a finding.
- **Given** a baseline-drift defer whose work survives as a `preserve/…/bmad-loop-…` tag
  **Then** the check and `fleet_picture` name that tag as the recovery source.
- **Given** an unpushed ref matching no status row
  **Then** `marshal status` reports it fleet-wide.
- **Given** local-only preserve tags or unpromoted scratch
  **Then** the row carries preserve debt and is never clean.

### Story 87.10 — Merged-check objects never enter the object store

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** AD-47, AD-81

**Surface:** `M/adapters/vcs_git.py:490-512` (merged-check `commit-tree`), `:1347-1375` (merge-tree preview); `tests/unit/test_vcs_git*.py`, `tests/integration/*`

**Acceptance criteria:**
- **Given** `is_branch_merged` on an unmerged, squash-equivalent branch
  **When** it runs
  **Then** its verdict is unchanged, and `git count-objects -v` (loose and packed) is identical before and after: the synthetic commit was written to a temporary object directory reached through `GIT_ALTERNATE_OBJECT_DIRECTORIES`.
- **Given** the preview path
  **Then** the same holds.
- **Given** the change reverted
  **Then** the object-count test fails.

### Story 87.11 — The build skills and the recovery recipes preserve before they revert or rebuild

**Type:** feature (CAP-287; the facts call the flag-gated verb) • **Effort:** S • **Deps:** 87.3 • **FR/AD:** FR-234, AD-81

**Surface:**
- `_bmad/custom/bmad-build-auto.toml` (`persistent_facts`);
- `_bmad/custom/bmad-build.toml` (new). The installed step files are never edited; they are installer-owned (AGENTS.md § Known pitfalls). Behaviour lands at `.claude/skills/bmad-build-auto/step-04-review.md:71-72` and `.claude/skills/bmad-build/step-04-review.md:63-64`;
- `C/landing_evidence.py:172-181` (convention text);
- `scripts/bmad_loop_baseline_drift_check.py:28-31, 309-313`;
- `docs/how-to/pixi-tasks.md:64`, `docs/how-to/troubleshoot-bmad-agent-loops.md:38`;
- `.claude/memory/reference/bmad-loop-escalation-and-landing-traps.md:10-14`, via a `scribe capture` correction, not a hand edit.

**Acceptance criteria:**
- **Given** the rendered `bmad-build-auto` and `bmad-build` skills
  **When** `render_skill.py` resolves their customization
  **Then** the persistent facts say: before any `intent_gap` or `bad_spec` revert, run
  `marshal preserve tag --producer build --story <slug> <N.M> --from .`, and cite the tag in the
  triage log.
- **Given** the recovery-landing convention and the baseline-drift remedy text
  **Then** step 1 is "preserve the source (`--producer hand`) before cutting `land/…`".
- **Given** the troubleshooting doc
  **Then** it states that `--restore-patch` is refused for worktree-isolation runs, matching
  `bmad-loop-resolve/SKILL.md:200-206`.
- `governance-currency` and the instruction-parity meta-test stay green.

### Story 87.12 — Legacy refs are promoted and the orphaned tips re-preserved (operator-gated)

**Type:** chore • **Effort:** M • **Deps:** 87.3; operator rulings Q1, Q3–Q5 • **FR/AD:** FR-234, AD-81

**Surface:** a one-off, dry-run-default script under `scripts/` that writes a tracked manifest. Execution is the operator's act: outward writes need confirmation.

**Acceptance criteria:**
- **Given** the 2026-10-04 deletion activity (`before` shas), and the 87.1 retirement manifest
  **When** the script runs dry
  **Then** it lists every tip reachable from no ref (98 and 8 at research time, overlapping) with
  the archive tag it would write. With `--execute` it writes annotated `archive/<original branch path>`
  tags and pushes them, after the manifest is committed.
- **Given** the 17 `refs/attempt-preserve-dirty/*`, the 3 local-only tags, the 3 `origin` `attempt-preserve/*`, and the `backup/*` and `archive/crewai-…` branches
  **Then** each gets a `preserve/` or `archive/` twin, per the operator's rulings. Nothing is deleted.
- **Given** the 682 `rescue/dangling-*` tags
  **Then** the manifest carries the classification (synthetic / stash / merge / patch-equivalent / unresolved), and no tag changes.

### Story 85.1 (chained) — required changes before it lands

1. **Roster key.** Replace `protected_ref_prefixes: ["loop/", "attempt-preserve/", "recover/", "rescue/"]`
   with `protected_refs`. It holds full refnames and kinds, and it is the § 7.3 list:
   - `refs/heads/loop/` (operational);
   - `refs/heads/attempt-preserve/` (legacy, pending Q3);
   - `refs/tags/preserve/`, `refs/tags/archive/`, `refs/tags/rescue/`.

   Marshal 87.1 reads the same key. Drop `recover/`/`rescue/` branches unless Q6 says otherwise.
2. **Matcher forms added:**
   - `git tag -d`;
   - `git push <remote> :refs/tags/<name>` and `git push --delete <remote> <tag>`;
   - `gh api -X DELETE …/git/refs/tags/<name>`;
   - `git update-ref -d <protected>`;
   - `git push --mirror`, and `git push --prune` with a refspec covering a protected prefix;
   - `git fetch --prune-tags` (it deletes local-only tags);
   - `rm -r[f]` of a path that resolves under `~/.bmad-loops/`;
   - `gh pr merge --delete-branch` whose PR head is a protected branch (the head is unknown to a
     pure matcher, so deny only when `--delete-branch` appears together with an explicit `loop/`
     head argument, and otherwise leave it to marshal 87.6).
3. **Reasons name the sanctioned verbs:** `marshal preserve retire <tag>` (archive twin) and
   `python scripts/worktree_sweep.py --retire <branch>`. A purge is "an operator act after a
   committed manifest".
4. **AC additions:**
   - **Given** `git tag -d archive/x`, `git push origin :refs/tags/preserve/a/b/c` or `git fetch --prune-tags`,
     **When** the hook runs,
     **Then** it denies.
   - **Given** `git tag -d feature-tag`,
     **Then** it allows.

### Story 85.2 — The protected-ref list is declared once and the live rulesets are proven to match it

**Type:** feature (CAP-165), flag-exempt `detector-or-gate` • **Effort:** M • **Deps:** 85.1 • **FR/AD:** steward CAP-5 / CAP-165

**Surface:**
- `docs/governance/guild-roster.json` (`protected_refs`);
- a new `docs/governance/rulesets/protected-refs.json` (the declared branch and tag rulesets, rendered from the roster);
- a new `scripts/protected_refs_ruleset_check.py` (scope `runtime`; authenticated `gh api`);
- `pixi.toml` task (with `environment.yaml` regenerated in the same PR, per AGENTS.md § Policy);
- `scripts/detectors.py` registry;
- `tests/scripts/test_protected_refs_ruleset_check.py`.

**Acceptance criteria:**
- **Given** a roster and a live-ruleset fixture that match
  **Then** the check exits 0.
- **Given** a missing pattern, an extra pattern, a missing rule (`deletion`, `update`, `non_fast_forward`), or a non-empty `bypass_actors` on a preserve or archive tag ruleset
  **Then** it exits 1 and names each difference.
- **Given** `gh api rate_limit` showing no authenticated quota, or any API error
  **Then** it exits 2; it never passes.
- **Given** the declared document
  **When** it is regenerated from the roster
  **Then** the result is byte-identical (derived, never hand-edited, AD-12).
- Applying the rulesets stays an operator act. The detector only reports.

### Story 85.3 — Workspace clean parks unlanded commits as a preserve tag before removing the worktree

**Type:** feature (CAP-155 amended) • **Effort:** S • **Deps:** marshal 87.3 (through the `marshal preserve` CLI, or `pyforge.core.preserve_refs` if the operator puts the grammar in core) • **FR/AD:** CAP-155, CAP-157

**Surface:** `src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py:866-945, 929-940`; `tests/unit/test_workspace*.py`

**Acceptance criteria:**
- **Given** a recorded scratch worktree with commits that are not on its source
  **When** `steward workspace clean` removes it
  **Then** a `preserve/<slug>/<key>/workspace-<date>-<sha8>` tag (or `preserve/unbound/workspace-…`) exists on `origin` first, and the result names it.
- **Given** the push fails
  **Then** the worktree is kept, and the record is reported `branch_kept` with the reason.
- **Given** a worktree whose commits are all on its source
  **Then** the `.landed.txt` note path is unchanged.
- **Given** gitignored or untracked bytes
  **Then** the tarball still captures them, and is reported as host-local.
- Station code does not import `pyforge.marshal`; `test_no_station_assumes_local_recipes.py` stays green.

### Ledger keys (for the Tier-3 feed, then `sprint-ledger-sync`)

```
pyforge-marshal:
  87-2-the-unpushed-work-detector-fails-closed-and-sees-tags-and-custom-refs
  87-3-preserved-work-has-one-grammar-and-one-verb
  87-4-spin-parks-every-attempt-as-a-preserve-tag-before-bmad-loop-can-prune-it
  87-5-dispatch-and-drain-preserve-a-stopped-storys-work-as-a-tag-on-origin
  87-6-land-retire-and-the-station-branch-never-fight-the-protected-list
  87-7-teardown-refuses-to-remove-a-loop-home-that-holds-unpreserved-work
  87-8-the-sweeper-preserves-to-tags-and-retires-agent-and-orphan-worktrees
  87-9-every-preserve-reader-sees-preserve-tags-and-origin
  87-10-merged-check-objects-never-enter-the-object-store
  87-11-the-build-skills-and-recovery-recipes-preserve-before-they-revert-or-rebuild
  87-12-legacy-refs-are-promoted-and-the-orphaned-tips-re-preserved
pyforge-steward:
  85-2-the-protected-ref-list-is-declared-once-and-the-live-rulesets-are-proven-to-match-it
  85-3-workspace-clean-parks-unlanded-commits-as-a-preserve-tag-before-removing-the-worktree
```

The Epic 87 heading on the chained branch reads *"Branch and worktree cleanup never destroys
protected state"*. Widen it in the same commit as the new stories, for example to *"Preserved work
is a protected tag, and no cleanup destroys it"*. Keep the `epic-87` key, so chain-completeness
INV-B holds. Do the same for steward Epic 85.
