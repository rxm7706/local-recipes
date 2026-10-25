---
title: "104.1: The .mcp.json marshal renders never makes a loop home dirty"
type: 'fix'
created: '2026-10-25'
status: 'in-progress'
baseline_revision: 'b0753539a36f349d608c80bfac9e62fdb3ffd485'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/templates/files/model-ignores.gitignore.j2
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/templates/manifest.yaml
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/init.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/refresh.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py
  - src/shared/packages/pyforge-marshal/tests/integration/test_init_worktree.py
  - .gitignore
  - .marshal/seed-state.yml
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `marshal refresh` refuses the `pyforge-marshal` loop home for a file marshal itself wrote there. Line
numbers are at `d287eceb0a`.

- **The refusal.** On 2026-10-25 every loop home was 180 commits behind `main`. `marshal refresh` fast-forwarded
  seven and refused `pyforge-marshal` with `MRS-REFRESH-003` ("dirty working tree -- refusing fast-forward (FR-134)")
  for one untracked file, `~/.bmad-loops/pyforge-marshal/.mcp.json`. The operator's session moved it aside, refreshed
  and put it back, so the next refresh refuses again.
- **Who wrote it.** `marshal init` (`cli/init.py::_render_mcp_json`, `:468`) renders `<home>/.mcp.json` from the
  policy's `mcp_servers` (Story 6.9 / 18.1, AD-43), copy-when-absent. `marshal-policy.toml` declares
  `[mcp_servers.marshal]`; no other station declares a server, so no other home has the file. It was written on
  2026-10-04 04:19:07, during a re-init of all eight homes. A second writer can put the same file there: preflight's
  adapter seed-file step (Story 1.7, `cli/init.py:1781-1825`) copies a main-checkout `.mcp.json` into a home. The rule
  covers both.
- **Why it counts.** The refresh probe, `adapters/vcs_git.py::has_uncommitted_changes` (`:621-644`), runs `git -c
  status.showUntrackedFiles=normal status --porcelain`, so untracked files count on purpose (`cli/refresh.py:265-322`).
  bmad-loop's own `verify.worktree_clean` uses `git status --porcelain` too and prints `?? .mcp.json` for the home, so
  `bmad-loop run` and `validate` would refuse it as well, and so would `marshal teardown` (FR-6, the same probe at
  `cli/init.py:2446`).
- **What the rest of the system already assumes.** bmad-loop's Claude profile (`bmad_loop/data/profiles/claude.toml`)
  lists `.mcp.json` among the gitignored configs it seeds into run worktrees. `docs/dreams/pyforge-marshal.md` says
  there is deliberately no `.mcp.json` in the repo, and `git ls-files` lists none anywhere. Nothing ignores it.
- **Precedents.** `.bmad-loop/profiles/` (`af15fa011a`, in the seeded template) and
  `.bmad-loop/marshal-model-cost-catalog.json` (`.gitignore`, outside the region) were ignored for the same refusal.
- **Rejected remedies.** Deleting the file makes `marshal preflight pyforge-marshal` report `MRS-PREFLIGHT-012`
  (ERROR) and the next `marshal init` renders it again. The shared `$GIT_COMMON_DIR/info/exclude` would work at once
  but is invisible, unreviewed and per-clone, and this repo has removed rules from it thirteen times. A refresh
  allowlist fixes refresh alone, leaves bmad-loop's gate refusing, and loosens FR-134.

**Approach:**
- **The rule.** `seed/templates/files/model-ignores.gitignore.j2` gains `/.mcp.json`, anchored to the repository
  root, under a comment that names `marshal init`'s render (AD-43) and bmad-loop's seeded configs. Anchoring keeps a
  nested `.mcp.json` (under `recipes/` or a package) visible to git.
- **The region is re-rendered, not hand-edited, in this order.** The `.gitignore` `model-ignores` region is a seed
  `hybrid-managed-region` (`seed/templates/manifest.yaml`) whose body hash `.marshal/seed-state.yml` records
  (`6dfa035c`). `marshal seed update --run` refuses a dirty tree (`seed/verbs/preconditions.py`, rung 2, `_is_dirty`:
  `git status --porcelain --untracked-files=normal`; only a dry run skips it, and `--force` skips rung 6 only). So:
  (1) commit the template change, the tests and any spec status change, leaving the tree clean; (2) run `marshal seed
  update --dry-run` and confirm it plans only the `model-ignores` region; (3) run `marshal seed update --run --yes`;
  (4) commit `.gitignore` and `.marshal/seed-state.yml` together. `model_version` stays `1.0.0`: a hybrid region whose
  body differs from its template is re-rendered without a bump (Story 97.2).
- **The test that proves the refusal is gone.** No integration test covers `_render_mcp_json` today
  (`tests/integration/test_init_worktree.py:250-313` is Story 1.7's preflight seed-copy test; the render has unit
  tests only, in `test_init.py` and `test_mcp_registration.py`). A new case in `tests/integration/test_init_worktree.py`
  is the first: a real git home whose `.gitignore` is built from the packaged `files/model-ignores.gitignore.j2`
  template, a declared `mcp_servers` entry, `marshal init`; then `GitVcs().has_uncommitted_changes(home)` is `False`
  and `git status --porcelain` is empty. Every existing case in that file is `@pytest.mark.slow`, and
  `pyforge-marshal-test` runs `-m "not slow"`, so the new cases carry no slow marker; they stay fast (one `git init`,
  no network). A second case puts `.mcp.json` inside a tracked subdirectory and asserts `git check-ignore` exits 1 for
  it, proving the anchor.
- **What does not change.** The refresh probe, `marshal init`'s render and its copy-when-absent rule, the home's file
  and the shared `info/exclude`.
- **`type: fix`, no flag.** The refresh and the render are both meant to work together; this restores that. Under
  `spec-feature-flag-governance` Q1 a fix carries no flag.

**After landing (not a dispatch gate):** a home that refuses to fast-forward never receives the new `.gitignore`. The
marshal home therefore needs one fast-forward by MRS-PREFLIGHT-014's own remedy, `git -C ~/.bmad-loops/pyforge-marshal
merge --ff-only refs/remotes/origin/main` (git allows it: `main` tracks no `.mcp.json`, so the untracked file is never
overwritten). After that its checkout carries the rule, and `marshal refresh` reads the home clean and does the push
and policy re-render itself.

Ledger key: `104-1-the-mcp-json-marshal-renders-never-makes-a-loop-home-dirty`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **`spec-pyforge-marshal` CAP-133** (← `spec-loop-home-fleet-refresh` CAP-2, FR-134): automated fast-forward and
  push, with a clean-worktree safety check. The check stays as strict; marshal's own render stops tripping it.
- **`spec-pyforge-marshal` CAP-1** (loop homes and isolation, FR-5): a home marshal provisions reads clean to marshal's
  own tools.
- **`spec-pyforge-marshal` CAP-14 / CAP-15** (seed init and seed update): the `.gitignore` model region carries the
  rule to every repo the seed installs or updates.
- **AD-43:** the tool surface is policy-declared and home-rendered; the render is unchanged. This story mints no CAP and
  changes no `SPEC.md` text.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, the 2026-10-25 (the marshal home is dirty with
  marshal's own file) entry; the operator's direction of 2026-10-25.

## Acceptance Criteria

- **AC1 — The rule.** The template carries `/.mcp.json` with its comment, and this repo's `.gitignore` region carries
  it after the re-render. From the repo root, `git check-ignore -v .mcp.json` names the rule inside the
  `marshal-seed:begin region=model-ignores` block.
- **AC2 — The seed stays green.** `marshal seed check` exits 0 for this repo. A `marshal seed update --dry-run`
  afterwards plans zero actions (its listed skips do not count). The local-recipes seed oracle
  (`tests/integration/test_local_recipes_empty_plan.py`, whose update leg catches a missed re-render) passes.
- **AC3 — A rendered home is clean.** The new integration case: after `marshal init` renders `.mcp.json` into a git
  home whose checkout carries the region, `has_uncommitted_changes` is `False` and `git status --porcelain` is empty.
- **AC4 — The anchor.** For a `.mcp.json` inside a tracked subdirectory of the same home, `git check-ignore` exits 1
  and `git status --porcelain` lists the file.
- **AC5 — Mutation.** Removing the rule from the template alone (the test builds its `.gitignore` from the template,
  so no re-render or seed-state change is needed) fails AC3's test. Restore it.
- **AC6 — The suites.** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` and `pixi run --frozen -e pyforge-ci
  pyforge-deps-test` are green.

## Boundaries & Constraints

**Always:**
- Change the region through `marshal seed`, and commit `.gitignore` and `.marshal/seed-state.yml` together.
- Reconcile every governed path on the memlogs of every Spec `spec-surface-check` names, then stamp each scoped
  (AGENTS.md pre-PR item 5): today `spec-pyforge-marshal` (`.marshal/seed-state.yml`), `spec-pyforge-core` (the
  template, and station `src/`) and `pyforge-herald/spec-pyforge-pages` (`.gitignore`; Story 86.2's precedent).

**Ask first:**
- A `model_version` bump, or any other seeded region or file the update plans to change.

**Never:**
- Never weaken `has_uncommitted_changes` or `bmad-loop`'s clean check, and never add a path allowlist to refresh.
- Never delete or move a loop home's `.mcp.json` as part of the story, and never write `$GIT_COMMON_DIR/info/exclude`.
- Never ignore `.mcp.json` below the root (no unanchored rule).
- Never run `marshal refresh` against the fleet as part of the story; the after-landing step is the operator's or the
  landing agent's.

**Residual risk:**
- A repo the seed installs that wants a team-shared, tracked root `.mcp.json` must `git add -f` it once; a tracked file
  is never hidden by an ignore rule.

## I/O & Edge-Case Matrix

| Case | Before | After |
|---|---|---|
| home with marshal's rendered `/.mcp.json`, checkout carries the region | `?? .mcp.json`, refresh refuses | clean, refresh fast-forwards |
| home whose checkout predates the region change | `?? .mcp.json`, refresh refuses | unchanged until one `merge --ff-only` (the after-landing step) |
| `marshal teardown` of a home holding the rendered file | refuses (dirty) | proceeds past the dirt check |
| `.mcp.json` in a subdirectory | untracked | untracked (anchor) |
| a tracked `.mcp.json` in another repo | tracked | tracked (ignore never hides a tracked file) |
| policy declares no `mcp_servers` | no file, clean | no file, clean |

</intent-contract>

## Binding

- Parent Spec capabilities: `spec-pyforge-marshal` CAP-133 (FR-134), CAP-1 (FR-5), CAP-14 and CAP-15. No CAP is minted,
  and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-25 (the marshal home is dirty with
  marshal's own file) entry.
- Epic: Epic 104 (new), minted with this story, because Epics 6, 15 and 18 are done and Epic 103 is a different
  concern. `epic-104` and `epic-104-retrospective` are minted with it.
- Ledger key: `104-1-the-mcp-json-marshal-renders-never-makes-a-loop-home-dirty`.
- Deps: —.
- Surface: `marshal-policy.toml` `[epic_surfaces]."104"`, added with this mint.
- Minted 2026-10-25 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, with AC3–AC5's tests, which carry no slow marker (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `git check-ignore -v .mcp.json` — expected: exit 0, naming the `.gitignore` line inside the `model-ignores` region (AC1).
- `pixi run -e pyforge-guild marshal seed check` — expected: exit 0 (AC2).
- `pixi run -e pyforge-guild marshal seed update --dry-run` — expected: zero actions (AC2).
- `pixi run --frozen -e pyforge-marshal marshal-local-recipes-seed-oracle` — expected: pass (AC2).
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python3 scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps.
- The mutation of AC5 — expected: AC3's test fails. Restore it.
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.

**After landing (not a gate):** `git -C ~/.bmad-loops/pyforge-marshal merge --ff-only refs/remotes/origin/main`, then
`git -C ~/.bmad-loops/pyforge-marshal status --porcelain` is empty and `pixi run -e pyforge-guild marshal refresh
--project pyforge-marshal` reports the home current, not refused.

## Spec Change Log

- 2026-10-25: minted from the Dream entry of 2026-10-25 (the marshal home is dirty with marshal's own file) at the
  operator's direction "fix / include / resolve the gaps identified autonomously". `type: fix`, no flag, no CAP.
- 2026-10-25: chain review round 1 (independent reviewer, PASS, 0 blockers). Applied: the seed's clean-tree rung and
  the commit order around `seed update --run`; no slow marker on the new tests; the test-file citation corrected and
  the preflight seed copy named as a second writer; `pyforge-herald/spec-pyforge-pages` added to the reconcile list;
  the test builds its ignore file from the template; AC2 and AC4 made checkable; the after-landing step uses
  MRS-PREFLIGHT-014's remedy instead of moving the file; teardown named.

## Review Triage Log

- **Round 1, 2026-10-25 (chain review of `4ecadbd3be`, independent reviewer): PASS, 0 blockers, 4 should-fix, 7 nits;
  all in scope applied.**
  - should-fix: `seed update --run` refuses a dirty tree (rung 2) — commit order spelled out.
  - should-fix: every `test_init_worktree.py` case is `slow` and the gate runs `-m "not slow"` — new cases carry no
    marker.
  - should-fix: `:272-313` is the preflight seed-copy test, not the render — citation corrected.
  - should-fix: `.gitignore` is governed by `pyforge-herald/spec-pyforge-pages` — added to the reconcile list.
  - nits applied: template-built ignore file; after-landing via `merge --ff-only`; AC2 "zero actions"; AC4 via
    `git check-ignore`; the Dream's "fixed the same way" corrected; teardown named.
  - nit not applied here: the PRD's FR-133..FR-135 arrows (`← CAP-91..93`) are pre-fold ids, part of a PRD-wide
    FR→CAP re-map proposed as its own task.

