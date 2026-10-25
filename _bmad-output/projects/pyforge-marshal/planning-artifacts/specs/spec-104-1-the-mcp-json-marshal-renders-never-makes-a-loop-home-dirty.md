---
title: "104.1: The .mcp.json marshal renders never makes a loop home dirty"
type: 'fix'
created: '2026-10-25'
status: 'ready-for-dev'
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
  2026-10-04 04:19:07, during a re-init of all eight homes.
- **Why it counts.** The refresh probe, `adapters/vcs_git.py::has_uncommitted_changes` (`:621-644`), runs `git -c
  status.showUntrackedFiles=normal status --porcelain`, so untracked files count on purpose (`cli/refresh.py:265-322`).
  bmad-loop's own `verify.worktree_clean` uses `git status --porcelain` too and prints `?? .mcp.json` for the home, so
  `bmad-loop run` and `validate` would refuse it as well.
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
- **The region is re-rendered, not hand-edited.** The `.gitignore` `model-ignores` region is a seed
  `hybrid-managed-region` (`seed/templates/manifest.yaml`) whose body hash `.marshal/seed-state.yml` records
  (`6dfa035c`). `marshal seed update` re-renders it in this repo: a dry run first (it must plan only this region), then
  `--run --yes`. The new region header hash and the seed state land together. `model_version` stays `1.0.0` unless
  the seed's own rules require a bump for a template change; the implementer follows what `marshal seed update` and
  the seed tests demand and records which.
- **The test that proves the refusal is gone.** `tests/integration/test_init_worktree.py` (`:272-313` renders
  `.mcp.json` today) gains a case: a real git home whose checkout carries the re-rendered `.gitignore`, a declared
  `mcp_servers` entry, `marshal init`; then `GitVcs().has_uncommitted_changes(home)` is `False` and `git status
  --porcelain` is empty. A second case puts a `.mcp.json` in a subdirectory and shows it untracked, proving the anchor.
- **What does not change.** The refresh probe, `marshal init`'s render and its copy-when-absent rule, the home's file
  and the shared `info/exclude`.
- **`type: fix`, no flag.** The refresh and the render are both meant to work together; this restores that. Under
  `spec-feature-flag-governance` Q1 a fix carries no flag.

**After landing (not a dispatch gate):** a home that refuses to fast-forward never receives the new `.gitignore`. The
marshal home therefore needs one last refresh with `.mcp.json` set aside and put back, after which its checkout
carries the rule and later refreshes read it clean.

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
- **AC2 — The seed stays green.** `marshal seed check` exits 0 for this repo and reports the region current. A `marshal
  seed update` dry run afterwards plans nothing. The local-recipes seed oracle task passes (an adopt dry run of this
  repo plans nothing outside the deferred artifacts).
- **AC3 — A rendered home is clean.** The new integration case: after `marshal init` renders `.mcp.json` into a git
  home whose checkout carries the region, `has_uncommitted_changes` is `False` and `git status --porcelain` is empty.
- **AC4 — The anchor.** A `.mcp.json` in a subdirectory of the same home is reported untracked (`git status
  --porcelain` lists it).
- **AC5 — Mutation.** Removing the rule from the template (and re-rendering) fails AC3's test. Restore it.
- **AC6 — The suites.** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` and `pixi run --frozen -e pyforge-ci
  pyforge-deps-test` are green.

## Boundaries & Constraints

**Always:**
- Change the region through `marshal seed`, and commit `.gitignore` and `.marshal/seed-state.yml` together.
- Reconcile every governed path on the memlogs of the Specs that govern it (`spec-pyforge-marshal`, and
  `spec-pyforge-core`, which co-governs station `src/`), then stamp scoped (AGENTS.md pre-PR item 5).

**Ask first:**
- A `model_version` bump, or any other seeded region or file the update plans to change.

**Never:**
- Never weaken `has_uncommitted_changes` or `bmad-loop`'s clean check, and never add a path allowlist to refresh.
- Never delete or move a loop home's `.mcp.json`, and never write `$GIT_COMMON_DIR/info/exclude`.
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
| home whose checkout predates the region change | `?? .mcp.json`, refresh refuses | unchanged until one refresh with the file set aside |
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
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, with AC3–AC5's tests (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `git check-ignore -v .mcp.json` — expected: exit 0, naming the `.gitignore` line inside the `model-ignores` region (AC1).
- `pixi run -e pyforge-guild marshal seed check` — expected: exit 0 (AC2).
- `pixi run -e pyforge-guild marshal seed update --dry-run` — expected: an empty plan (AC2).
- `pixi run --frozen -e pyforge-marshal marshal-local-recipes-seed-oracle` — expected: pass (AC2).
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python3 scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps.
- The mutation of AC5 — expected: AC3's test fails. Restore it.
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.

**After landing (not a gate):** with `~/.bmad-loops/pyforge-marshal/.mcp.json` set aside, `pixi run -e pyforge-guild
marshal refresh --project pyforge-marshal` fast-forwards the home; put the file back unchanged; `git -C
~/.bmad-loops/pyforge-marshal status --porcelain` is then empty.

## Spec Change Log

- 2026-10-25: minted from the Dream entry of 2026-10-25 (the marshal home is dirty with marshal's own file) at the
  operator's direction "fix / include / resolve the gaps identified autonomously". `type: fix`, no flag, no CAP.

## Review Triage Log

- No review has run yet.
