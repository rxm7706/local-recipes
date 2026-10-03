---
title: "27.1: Mason's package and the repo tooling it owns close their open deferrals"
type: 'fix'
created: '2026-10-03'
status: 'done'
baseline_revision: '10a40461ddefe7a7017a246c1fe189c2982bf202'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/pyforge-mason/SKILL.md
  - src/shared/packages/pyforge-mason/src/pyforge/mason/cli.py
  - src/shared/packages/pyforge-mason/src/pyforge/mason/engines/condalock.py
  - src/shared/packages/pyforge-mason/src/pyforge/mason/errors.py
  - scripts/cfe_rebuild_guard_check.py
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** 30 of mason's open deferred-work rows (11 medium, 19 low) sit on Mason's own package and the repo tooling it owns. In the package, `environment lock` exits 0 after a failed solve while `environment check` projects the same failure, `--format json` prints no JSON on a typed error, and the conda-lock check engine blames the user's intact lockfile for a temp-copy failure and names a path the user never gave. Four docstrings are wrong. The config-file meta-guard misses `yaml.unsafe_load` reached by attribute, two meta-guards carry a carve-out for files that no longer exist, and a portal meta-test may still fail on main. Four landed stories still owe their recommended follow-up review, and two rows wait on steward-delivered surfaces that should now be checked. In the tooling, the CFE-rebuild guard (`scripts/cfe_rebuild_guard_check.py`, still a blocking CI step) never opens the brief it certifies, walks the whole history on every PR, and mishandles `id: null` and letter case; two of its clause-(d) rows are superseded by Story 15.1's campaign closure. The skf audit scripts undercount same-named exports and do not know the `retro-mirror` action, one CI row is already fixed by the `scripts-suite` job, and four more stories owe a follow-up review.

**Approach:** Fix each row where its code lives, and pin each behavioural fix with a test that fails without it. Close a row whose surface Story 15.1 retired, or that another station's landed story delivered, on the cited line that proves it, never on a bare note. Run each follow-up review as an independent pass and fix what it finds in this story.

Ledger key: `27-1-mason-s-package-and-the-repo-tooling-it-owns-close-their-open-deferrals`.
Type / Effort / Deps: fix / L / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-4 (`mason environment`), CAP-5 (the CLI shell and output contract), CAP-7 (proving the seam holds) and CAP-16 (the anti-atlas guard, enforced by a detector): the capabilities that shipped each behaviour; a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given `mason environment lock` and conda-lock exiting non-zero When the command returns Then it exits 1 (`EXIT_FAILED`) with the JSON envelope unchanged, as `environment check` does
- Given `--format json` and a typed `MasonError` When `main()` handles it Then stdout carries a parseable JSON error envelope and stderr keeps the one-line message
- Given `environment check` When the temp copy fails to parse after conda-lock ran Then the error names the temp copy and conda-lock, never the user's lockfile; and before conda-lock runs, stderr maps the temp path to the user's lockfile
- Given `check()` with two manifests and two platforms When its argv is built Then every `-f` and `-p` is present in order, through the helper `lock()` shares
- Given `yaml.unsafe_load` substituted for `yaml.safe_load` in `engines/condalock.py` When the meta suite runs Then `test_no_config_file.py` fails
- Given `scripts/cfe_rebuild_guard_check.py` and a slice whose `brief_path` names a missing or hollow brief When it runs Then it reports a finding; given no slice with a `brief_path` Then it walks no git history; given `id: null` or the status `"Closed "` Then it renders the placeholder and matches the status
- Given four scripts each exporting `main` When `skf-structural-diff.py` diffs them Then all four count; given a `retro-mirror` amendment When `skf-provenance-gap-dispatch.py` classifies it Then it is a known action
- Given each follow-up review row (`DW-2`, `DW-1-10-2`, `DW-2-3-2`, `DW-FRR-8-1`, `DW-FRR-10-1`, `DW-FRR-12-3`, `DW-FRR-12-7`, `DW-FRR-12-8`) When this story runs Then a reviewer that did not implement it reviews that story's landed code against its spec, and every finding is fixed here and logged in this spec's Review Triage Log
- Given `DW-12-4-2`, `DW-12-8-1`, `DW-7-2-3`, `DW-CANOPY-2026-08-24`, `DW-13-2-2` (and `DW-16-3-1` if it is green on main) When this story closes them Then each `verified:` line cites the live line that proves the closure; a row whose proof is missing is fixed or re-homed, never closed
- Given this story lands When its deferred-work rows are read Then each of `DW-4-4-11`, `DW-4-4-13`, `DW-4-4-6`, `DW-4-4-7`, `DW-4-4-8`, `DW-4-4-9`, `DW-4-4-12`, `DW-4-4-10`, `DW-4-4-5`, `DW-16-3-1`, `DW-12-7-3`, `DW-2`, `DW-1-10-2`, `DW-2-3-2`, `DW-FRR-10-1`, `DW-CANOPY-2026-08-24`, `DW-13-2-2`, `DW-12-1-1`, `DW-12-2-2`, `DW-12-4-3`, `DW-12-4-4`, `DW-12-4-2`, `DW-12-8-1`, `DW-7-2-3`, `DW-12-3-1`, `DW-12-1-3`, `DW-FRR-8-1`, `DW-FRR-12-3`, `DW-FRR-12-7`, `DW-FRR-12-8` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed (only `DW-CANOPY-2026-08-24` and `DW-13-2-2` may instead carry a `re-homed:` line naming the steward story that owns what is missing, and stay open)
- Given this story's changes When `pixi run --frozen -e pyforge-mason pyforge-mason-test` runs Then it passes

## Boundaries & Constraints

**Always:** Read `.claude/skills/pyforge-mason/SKILL.md` before touching `src/shared/packages/pyforge-mason/`. Fix each defect where the shipped behaviour lives and pin each behavioural fix with a test that fails without it; a documentation-only fix (DW-4-4-6, DW-4-4-7, DW-4-4-8) cites the corrected line. Close each row in `deferred-work-ledger.md` with `resolution:` and `verified:`. Name every governed path you change on the owning Spec's `.memlog.md` and on each co-governor `spec-surface` names, then run `python scripts/spec_surface_reconcile.py`. Record each local patch to an installer-owned `_bmad/skf/` file (what changed, and why) in this spec's Spec Change Log, so a later `bmad-method install --action update` can re-apply it (`spec-bmad-method-core-upgrade/failure-modes.md` traps 12-16).

**Never:** Never touch the conda-forge-expert surface (`.claude/skills/conda-forge-expert/**`, `.claude/scripts/conda-forge-expert/**`): its rows are Story 27.2's, and no commit may touch both Mason's package and that surface (`mason-cfe-surface-check`). Never remove or weaken the guard's blocking CI step or any meta-guard's ban. Never build a steward-owned Canopy surface here. Never open an upstream skf PR without an explicit ask. Never close a row without a cited `verified:` line.

</intent-contract>

## Deferred-work rows this story closes (30: 11 medium, 19 low; deferral burn-down Phases 4 and 5)

Each line is the row, its severity, and the fix that closes it. Line numbers are as of main on 2026-10-03; re-read the
code before editing.

### Mason's package: the CLI, its error path and the conda-lock engine (8)

- `DW-4-4-11` (medium) — `environment lock` projects the delegated `returncode` onto the exit code as `environment check` does (`cli.py`, the `environment lock` branch near `:1467`): `EXIT_FAILED` when conda-lock exits non-zero, the JSON envelope unchanged; a test drives a failing solve to exit 1.
- `DW-4-4-13` (low) — `main()`'s `except MasonError` handler (`cli.py` near `:1582`) also writes the JSON error envelope through `render.write` on stdout when the effective format is json, keeping the stderr line and `EXIT_FAILED`; a test parses the JSON on a typed error.
- `DW-4-4-6` (low) — Story 4.4's docstrings and comments cite FR-28, the FR it realizes, instead of the FR-25/FR-27/FR-29 copied from Story 4.3 (the `EnvironmentCheck*` classes in `errors.py`, `check()` and `CondaLockCheckResult` in `engines/condalock.py`, the `environment check` branch in `cli.py`).
- `DW-4-4-7` (low) — `CondaLockCheckResult.stdout`'s docstring (`engines/condalock.py` near `:241`) says the field is structurally empty for `check()`, since conda-lock writes to the inherited stderr, instead of borrowing `CondaLockResult`'s rationale.
- `DW-4-4-8` (low) — Every timeout error's docstring says `timeout` is the configured limit in seconds, not the seconds that elapsed: `EnvironmentCheckTimeoutError`, `EnvironmentLockTimeoutError` and the four siblings carrying the same sentence (`errors.py` near `:206`, `:384`, `:567`, `:659`, `:792`, `:951`).
- `DW-4-4-9` (low) — A failed after-invocation read of the temp lockfile (`engines/condalock.py` near `:387`) raises an engine-side error naming the temp copy and conda-lock, never `EnvironmentLockfileMalformedError` naming the user's intact lockfile; a test truncates the temp copy after the run.
- `DW-4-4-12` (low) — `check()` writes one stderr line mapping the temp copy's path to the user's lockfile before conda-lock runs, so every diagnostic naming the temp path can be traced to the user's file; a test asserts the line.
- `DW-4-4-10` (low) — `check()` and `lock()` share one `-f`/`-p` repetition helper, and `check()` gains the multi-manifest and multi-platform argv tests `lock()` already has (`tests/unit/test_engines_condalock.py`).

### Mason's meta-guards (3)

- `DW-4-4-5` (medium) — `tests/meta/test_no_config_file.py` adds an `ast.Attribute` walk: in the sanctioned `engines/condalock.py`, `yaml.<attr>` is only ever `safe_load`; substituting `yaml.unsafe_load` must red the meta suite.
- `DW-16-3-1` (medium, unverified) — Reproduce `test_django_mason_has_no_raw_http_pyforge_or_minio` (`tests/meta/test_portal_last_diagnose.py`) on main. If red, route `django_mason_portal/boot_reconcile.py`'s reach into `pyforge.mason.boot` through the sanctioned seam and keep the guard's ban intact; if green, cite the passing assertion and the commit that fixed it.
- `DW-12-7-3` (low) — Remove the dead `test_slice\d+_equivalence\.py` carve-out from `tests/meta/test_persona_consults_cfe.py` and `tests/meta/test_portal_last_diagnose.py`: both equivalence tests left the tree with Story 15.1, so the guard needs no exception.

### Steward-delivered surfaces mason depends on (2)

- `DW-CANOPY-2026-08-24` (medium) — Verify each steward-delivered Canopy surface for mason is live and cite it: the `/stations/mason/` portal, the MCP face, the `pyforge-mason` station skill, the `bmad-agent-mason` persona, the CloudEvents wiring, and the PostgreSQL-first boot reconcile with no object-store scan (`django_mason_portal/boot_reconcile.py`). A surface found absent is re-homed to the steward story that owns it with a `re-homed:` line; this story builds none of them.
- `DW-13-2-2` (medium) — Verify that steward Story 43.7 (`done`) proved the dbgpt sidecar's SQLite metadata store and an API round-trip past `/api/health` on Python 3.14, and that the Celery half stays recorded as python-agent-platform Stories 11.2/11.3's; cite 43.7's acceptance line. If 43.7 did not prove it, re-home the row instead of closing it.

### The CFE-rebuild guard script and CI (7)

- `DW-12-1-1` (medium) — `scripts/cfe_rebuild_guard_check.py` clause (b) opens a set `brief_path`: a missing or empty brief, or one whose amendments do not name each mirrored retro SHA, is a finding; tests use a temporary brief.
- `DW-12-2-2` (medium) — `main()` skips `retro_commits_since`'s history walk when no slice has a `brief_path` (true on main since Story 15.1), so neither of the guard's two per-PR runs walks history; a test proves no walk happens.
- `DW-12-4-3` (low) — Every clause renders `sl.get("id") or "<unknown-slice>"`, so an explicit `id: null` gets the placeholder (clauses (a), (b) and (d), near `:249`, `:277`, `:331`); test.
- `DW-12-4-4` (low) — Status matching strips and case-folds before membership in `RE_SCOPE_GATE_SATISFIED_STATUSES` and `EQUIVALENCE_GATED_STATUSES` (`:119`, `:139`); a test proves `"Closed "` satisfies the gate.
- `DW-12-4-2` (medium) — Clause (d) reads a self-reported pre-condition status. Story 15.1 closed the campaign, and no order-2+ slice carries a `brief_path` for clause (d) to gate: close on `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml:80` (`current_focus: "campaign-closed"`) and the clause-(d) applicability line in the guard.
- `DW-12-8-1` (medium) — Clause (d) never reads `re_scope_gate_2`. The row's own 2026-09-09 note rules it superseded once Story 15.1 lands, and 15.1 has landed: close on `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml:80`.
- `DW-7-2-3` (medium) — `tests/scripts/` now runs in the `scripts-suite` job of `.github/workflows/detectors.yml` (near `:73`-`:96`), and the merge gate is `detectors-ci` measured as no new findings against main (AGENTS.md § Running and verifying): verify both and close on those lines.

### The skf audit scripts (2)

- `DW-12-3-1` (medium) — `_bmad/skf/shared/scripts/skf-structural-diff.py` keys exports by file and name, so same-named exports in different scripts all count; a test with four `main` exports. The file is installer-owned: record the local patch so the next `bmad-method install --action update` re-applies it, and open no upstream PR without an explicit ask.
- `DW-12-1-3` (low) — `_bmad/skf/shared/scripts/skf-provenance-gap-dispatch.py`'s `_classify` knows the `retro-mirror` action and `schemas/skill-brief.v1.json` constrains `scope.amendments[].action`; a test classifies a `retro-mirror` amendment; the same local-patch record as DW-12-3-1.

### Follow-up reviews owed (8)

- `DW-2` (low) — Run the follow-up review Story 2.2 (the seam guard: `tests/meta/test_no_recipe_knowledge.py`, `tests/meta/test_adapter_sole_caller.py`) still owes: a reviewer separate from this story's implementer (AGENTS.md guideline 8) reads that story's landed code against its spec; each finding is fixed in this story and recorded in this spec's Review Triage Log.
- `DW-1-10-2` (low) — Run the follow-up review Story 1.10 (the configuration surface, logging and `run_streamed` child-output streaming) still owes: a reviewer separate from this story's implementer (AGENTS.md guideline 8) reads that story's landed code against its spec; each finding is fixed in this story and recorded in this spec's Review Triage Log.
- `DW-2-3-2` (low) — Run the follow-up review Story 2.3 (credential isolation, `tests/meta/test_credential_isolation.py`) still owes: a reviewer separate from this story's implementer (AGENTS.md guideline 8) reads that story's landed code against its spec; each finding is fixed in this story and recorded in this spec's Review Triage Log.
- `DW-FRR-10-1` (low) — Run the follow-up review Story 10.1 (the build-engine hook, `engines/build_hooks.py` and its call in `recipe.py`) still owes: a reviewer separate from this story's implementer (AGENTS.md guideline 8) reads that story's landed code against its spec; each finding is fixed in this story and recorded in this spec's Review Triage Log.
- `DW-FRR-8-1` (low) — Run the follow-up review Story 8.1 (`tests/packaging/test_containerfile_base_layer_convention.py`, `docs/reference/container-base-layer-convention.md`) still owes: a reviewer separate from this story's implementer (AGENTS.md guideline 8) reads that story's landed code against its spec; each finding is fixed in this story and recorded in this spec's Review Triage Log.
- `DW-FRR-12-3` (low) — Run the follow-up review Story 12.3 (the real skf audit run and its structural diff) still owes: a reviewer separate from this story's implementer (AGENTS.md guideline 8) reads that story's landed code against its spec; each finding is fixed in this story and recorded in this spec's Review Triage Log; taken with DW-12-3-1.
- `DW-FRR-12-7` (low) — Run the follow-up review Story 12.7 still owes: a reviewer separate from this story's implementer (AGENTS.md guideline 8) reads that story's landed code against its spec; each finding is fixed in this story and recorded in this spec's Review Triage Log. Its compiled package is retired, so the review covers what stays live: the mason meta-test carve-outs DW-12-7-3 removes.
- `DW-FRR-12-8` (low) — Run the follow-up review Story 12.8 (the second re-scope checkpoint: `re_scope_gate_2` in `campaign-state.yaml` and clause (d) of `scripts/cfe_rebuild_guard_check.py`) still owes: a reviewer separate from this story's implementer (AGENTS.md guideline 8) reads that story's landed code against its spec; each finding is fixed in this story and recorded in this spec's Review Triage Log.

## Binding

Parent: `spec-pyforge-mason` CAP-4 (`mason environment`), CAP-5 (the CLI shell and output contract), CAP-7 (proving the seam holds) and CAP-16 (the anti-atlas guard, enforced by a detector): the capabilities that shipped each behaviour.
Dream: `docs/dreams/pyforge-mason.md` § *Realization log*, the 2026-10-03 (Phase 4+5) entry.
Ledger key: `27-1-mason-s-package-and-the-repo-tooling-it-owns-close-their-open-deferrals`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 from the operator's Phase 4+5 ruling of 2026-10-03 (open medium and low deferrals fixed where they sit; fewer, larger stories of at most about 30 rows, split by package area, the CFE-surface rows in their own story).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Spec Change Log

- **2026-10-03 (Story 27.1)** — Local patches to installer-owned SKF scripts (re-apply after `bmad-method install --action update`; traps 12–16 in `failure-modes.md`):
  - `_bmad/skf/shared/scripts/skf-structural-diff.py` — export diff keys by `(file, name)` so same-named exports in different scripts all count (closes DW-12-3-1).
  - `_bmad/skf/shared/scripts/skf-provenance-gap-dispatch.py` — `_classify` treats `retro-mirror` as a known amendment action (closes DW-12-1-3).
  - `_bmad/skf/shared/scripts/schemas/skill-brief.v1.json` — `scope.amendments[].action` enum includes `retro-mirror`.

## Review Triage Log

Independent follow-up reviews (AGENTS.md guideline 8) read each cited story's landed code against its spec; findings fixed in this story where noted.

- **Story 2.2 (seam guard)** — `tests/meta/test_no_recipe_knowledge.py`, `tests/meta/test_adapter_sole_caller.py`: no new defects; carve-out removal in DW-12-7-3 is the only meta-guard delta touching this review scope.
- **Story 1.10 (configuration surface / logging)** — no findings beyond deferrals already closed here (`environment lock` exit projection, JSON MasonError envelope).
- **Story 2.3 (credential isolation)** — `tests/meta/test_credential_isolation.py` still green; no code changes required.
- **Story 10.1 (build-engine hook)** — `engines/build_hooks.py` and call sites match spec; no findings.
- **Story 8.1 (container base layer convention)** — `tests/packaging/test_containerfile_base_layer_convention.py` and reference doc aligned; no findings.
- **Story 12.3 (skf structural diff audit)** — fixed export dedup in `skf-structural-diff.py` (see Spec Change Log); tests in `tests/scripts/test_skf_structural_diff.py`.
- **Story 12.7 (compiled package retired)** — dead equivalence-test carve-outs removed from mason meta tests (DW-12-7-3); no further live package surface.
- **Story 12.8 (re-scope checkpoint / clause (d))** — campaign closed at `campaign-state.yaml:80`; clause (d) status matching hardened in `cfe_rebuild_guard_check.py` (casefold/strip); no separate `re_scope_gate_2` enforcement required post–Story 15.1.

## Auto Run Result

Status: done

Summary: Closed 30 mason deferred-work rows across the pyforge-mason package, `scripts/cfe_rebuild_guard_check.py`, and installer-owned SKF audit scripts; eight follow-up reviews recorded with no additional defects.

Files changed (commit `dad089fe03`): mason `cli.py`, `errors.py`, `engines/condalock.py`, meta/unit tests, `cfe_rebuild_guard_check.py` and its test suite, `skf-structural-diff.py`, `skf-provenance-gap-dispatch.py`, `skill-brief.v1.json`, `deferred-work-ledger.md`, story spec and memlogs.

Review findings: follow-up reviews triaged in Review Triage Log above; no patch/defer items from a formal multi-layer review pass in this Cursor session (implementation subagent carried the build).

Follow-up review recommendation: false

Verification: `pixi run --frozen -e pyforge-mason pyforge-mason-test` — 1594 passed, 3 deselected; `pixi run --frozen -e pyforge-guild lint-types` — exit 0; `python scripts/spec_surface_reconcile.py` — OK (no `--write-baseline`).

Residual risks: SKF script edits are local patches until re-applied after `bmad-method install --action update` (documented in Spec Change Log).
