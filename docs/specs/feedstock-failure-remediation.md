# Tech Spec: Feedstock Failure Remediation (parameterized)

> BMAD-consumable tech-spec for taking one or more **failing conda-forge
> feedstock PRs** — almost always `[bot-automerge]` autotick version
> bumps — and driving each to **green-and-merged**, **fix-pushed-pending-CI**,
> or **explicitly deferred-as-blocked** (with the blocker named). Every
> recipe edit is built + tested locally before it is pushed.
>
> This is a *timeless workflow* spec, parameterized per case. The procedural
> detail lives in the `conda-forge-expert` skill (SKILL.md diagnostic chain +
> gotchas G10/G14/G19/G24/G26/G31–G34); this spec is the orchestration layer
> on top. New cases append to "Worked Examples"; the body stays stable.
>
> Run via `bmad-quick-dev` with the failing PR(s) named in the prompt.

---

## How to use this spec

1. **Fill the Parameters block** with the failing PR(s) and mode.
2. **Resolve the Open Questions** (all are pre-resolved with defaults; only
   override per case).
3. **Execute the Waves** — Wave A (triage) always runs first; B/C/D run per the
   classification of each PR; E always closes the effort.
4. **Append a new "Worked Example"** recording the PR set, each PR's
   classification + outcome, and any novel finding (which then feeds the
   Wave E skill retro).

---

## Parameters (fill these per case)

| Parameter | Value | Notes |
|---|---|---|
| `<pr_refs>` | | One or more failing feedstock PRs (URL, or `conda-forge/<name>-feedstock#<N>`). |
| `<mode>` | `single` \| `batch` | `batch` parallelizes Wave A diagnosis across subagents. |
| `<fork_owner>` | `rxm7706` | The maintainer account pushing fixes (must maintain each feedstock). |
| `<local_test_subdir>` | `linux_64` | Platform for the local verify build (noarch builds once here). |
| `<bot_fork>` | `regro-cf-autotick-bot` | Head-repo owner of autotick PRs (maintainer-edit push target). |

---

## Status

| | |
|---|---|
| Status | **Active** — workflow proven end-to-end; parameterized for reuse |
| First worked example | 2026-06-17/18 batch — 12 PRs (10 merged, 2 deferred) |
| Skill version at authoring | conda-forge-expert v8.30.0 (gotchas G31–G34 landed from the first worked example) |
| Predecessor specs | `feedstock-platform-expansion.md` (platform widening), `cfe-pr-artifact-downloader.md` (artifact smoke-tests) |

---

## Background and Context

### The problem

A maintainer with many feedstocks accrues a steady stream of red autotick-bot
version-bump PRs. Each red PR is one of three things, and the costly mistake is
treating them uniformly:

- **Transient CI flake** — env-provisioning / source-fetch died on
  infrastructure (CDN drop, Windows entropy, mid-download `IncompleteRead`). The
  recipe is correct; a restart clears it. *Editing the recipe here is wasted
  work.*
- **Real recipe defect** — the upstream bump introduced a Python-floor bump, a
  dependency-pin mismatch, a build-backend switch, a missing/renamed dep, or a
  linter trip. *Restarting here just reproduces red.*
- **Blocked on a prerequisite feedstock** — the version upstream now pins isn't
  on conda-forge yet (a dep feedstock or sibling is behind). *Neither restart nor
  a local edit can fix it; the prerequisite must land first.*

The remediation loop must (a) classify fast and cheaply, (b) never push an
unverified recipe, and (c) surface blocked PRs rather than force a risky fix.

### What's been ruled out

- **Blind restart-ci** — burns a full CI matrix re-run on every real defect.
- **Blind push of an edit** — an unverified recipe means CI discovers the
  failure; with `[bot-automerge]` it also risks merging a half-right recipe.
- **Editing only the fork PR branch** — the local-recipes `recipes/<name>/`
  mirror is the source of truth; the fork checkout is downstream of it
  (`feedback_local_mirror_first_then_verify_then_push`).
- **Loosening a blocked dep pin to "just make it green"** — when `pip_check:
  true` is in the test block, the wheel METADATA still enforces the upstream
  pin (G24/G26); loosening the conda dep alone fails, and patching the source
  to loosen ships a different dep set than upstream intends (runtime risk).

### What's available to leverage

- **`conda-forge-expert` skill** — the diagnostic chain for feedstock CI test
  failures, the flake-vs-fix taxonomy (G32), and the per-class fix gotchas
  (G10 name divergence, G14 version float-parse, G19 Windows UTF-8, G24/G26 pin
  mirroring, G31 python_min override, G34 setuptools/pkg_resources).
- **`gh` CLI** — `pr view --json statusCheckRollup`, `run view --log-failed`,
  the Azure timeline REST API, and maintainer-edit push.
- **Local build** — `rattler-build` (v1) / `conda-build` (v0) in the
  `local-recipes` pixi env, with `conda-forge-pinning` for `${{ python_min }}`.
- **Parallel subagents** — Wave A diagnosis fans out cleanly (read-only, one
  agent per PR) with an inline playbook distilled from the skill.

### Empirical state (verified `<YYYY-MM-DD>` per case)

Record per case: how many PRs, the format split (v0 meta.yaml vs v1
recipe.yaml), and any feedstocks where `<fork_owner>` is **not** a maintainer
(blocks the maintainer-edit push). The 2026-06-17/18 worked example: 12 PRs,
mixed v0/v1, all `<fork_owner>`-maintained except the *prerequisite* feedstocks
(sqlglot) that caused the two blocks.

---

## Goals

1. **Every targeted PR reaches a terminal state**: MERGED-green, fix-pushed-and-
   CI-pending, or deferred-as-blocked **with the named blocker**.
2. **Zero unverified pushes** — every recipe edit is built + tested locally
   (import + `pip check` green on the intended Python) before it is pushed.
3. **Flakes get a restart, not an edit** — classification precedes action.
4. **Blocked PRs are surfaced, not force-fixed** — the prerequisite (dep
   feedstock / sibling) is identified and the operator decides land-vs-defer.
5. **The skill gets better** — any novel signature or fix mechanic discovered
   lands in the CFE skill at closeout (Wave E).

### Non-goals

- Submitting **new** recipes (that's the staged-recipes authoring loop). *Review-
  comment remediation on a staged-recipes PR is a sibling case — see "Adjacent
  case" below — but new-recipe authoring is out of scope.*
- Bumping prerequisite feedstocks the operator hasn't approved (Wave D defers).
- Platform expansion / rerender-only refreshes (`feedstock-platform-expansion.md`).

---

## Load-bearing workflow rules (apply to every story)

1. **Invoke `conda-forge-expert` for all recipe triage/edit/build** (CLAUDE.md
   BMAD↔CFE Rule 1). The skill's gotchas are authoritative over this spec's
   prose when they conflict.
2. **Test locally first** — never push a recipe edit that hasn't built + tested
   green locally (`feedback_test_locally_before_push`). For a *structural no-op*
   edit (e.g. collapsing identical script branches) a `rattler-build
   --render-only` that proves the rendered script is unchanged is the
   proportionate verification; a full rebuild is optional.
3. **Local mirror is the source of truth** — apply fixes to
   `recipes/<feedstock>/` first, then mirror to the fork checkout
   (`feedback_local_mirror_first_then_verify_then_push`).
4. **Update the PR via maintainer-edit push** — a `gh pr checkout` clone's
   `origin` is the upstream feedstock, not the bot fork; push to
   `https://github.com/<bot_fork>/<feedstock>.git HEAD:<pr-head-branch>` (G32),
   then `@conda-forge-admin, please rerender`
   (`feedback_always_request_rerender_after_feedstock_push`).

---

## Stories — Wave A: Triage & classify (read-only, parallelizable)

### S1. Enumerate failing checks per PR
For each `<pr_refs>`: `gh pr view <N> --repo conda-forge/<fs> --json
title,state,headRefName,statusCheckRollup`. Record the PR title (version),
head-ref branch, and every check with conclusion `FAILURE`/`ERROR` + its
`detailsUrl`. **AC**: a per-PR list of failed legs with detail URLs.

### S2. Fetch the real error from each failed leg
- **GitHub Actions** (`/actions/runs/<id>`): `gh run view --repo … <id>
  --log-failed`, strip ANSI (`sed 's/\x1b\[[0-9;]*m//g'`), grep for the root
  error (`Traceback|ImportError|pip check|× error|requirement|no candidates|
  BackendUnavailable|floating-point|dispatch task|random numbers|IncompleteRead`).
- **Azure** (`dev.azure.com/…buildId=<id>`): fetch the timeline JSON
  (`…/build/builds/<id>/timeline?api-version=7.0`), find `result==failed`
  records with a `log.url`, curl the log.
- In `batch` mode, **fan out one read-only diagnostic subagent per PR** with the
  inline playbook (the skill's flake/fix signatures); each returns a structured
  verdict. **AC**: the verbatim root-cause line for every failed leg.

### S3. Classify each PR — FLAKE | REAL_FIX | BLOCKED
Apply the **triage taxonomy** (below). For dep / python-floor cases, cross-check
upstream's `pyproject.toml` (`curl pypi.org/pypi/<pkg>/<ver>/json` →
`requires_python`, `requires_dist`) per the skill's diagnostic chain. **AC**:
each PR labelled, with the minimal proposed action.

#### Triage taxonomy (CFE skill G32)

| Class | Signature (verbatim) | Action |
|---|---|---|
| **FLAKE** | `dispatch task is gone` / `runtime dropped the dispatch task` (pixi/CDN); `_Py_HashRandomization_Init: failed to get random numbers` (Win entropy); `IncompleteRead`/`Connection broken` mid-download; `HTTP 503`/`error sending request` during provisioning/fetch — **and other platforms/Pythons of the same run pass** | Wave B: restart ci |
| **REAL_FIX** | `ImportError: cannot import name 'X'` on a stdlib name → python floor (G31); `pip check` `<pkg> requires B==X, but you have Y` → pin (G24/G26); `BackendUnavailable: Cannot import 'hatchling.build'` → host build-backend; linter `interpreted as a floating-point number` → quote version (G14); `ModuleNotFoundError: No module named 'pkg_resources'` → setuptools cap (G34); dep absent under expected name → name swap (G10) | Wave C |
| **BLOCKED** | `<pkg> does not exist` / `<dep> ==<X>, for which no candidates were found` where `<dep>` is genuinely behind/absent on conda-forge (re-verify max version; beware the `conda search` not-found-listing misread, G33) | Wave D |

---

## Stories — Wave B: Flake remediation

### S4. Restart CI on FLAKE PRs
For each FLAKE: post `@conda-forge-admin, please restart ci`. **No recipe edit,
no local build** (the recipe is correct; there is nothing to test). **AC**: the
restart comment posted; (optional) the re-run goes green and the PR
auto-merges.

---

## Stories — Wave C: Real-fix remediation (per REAL_FIX PR)

### S5. Apply the minimal fix to the local mirror
Edit `recipes/<feedstock>/recipe.yaml` (or `meta.yaml`) — the source of truth.
Pick the fix by class:
- **Python floor (G31)**: v1 → add `recipe/conda_build_config.yaml` with
  `python_min: ["X.Y"]` (rerender propagates it; `context.python_min` does
  **not**). v0 → `{% set python_min = "X.Y" %}` (shadows the variant directly).
- **Dep pin (G24/G26)**: mirror upstream's bound. If upstream hard-pins `==Z`,
  pin `==Z` when `Z` is on conda-forge; if it isn't, this is actually a Wave D
  block. Loosening an upstream `==` needs a source-pyproject `sed` (G26).
- **Build-backend swap**: change the host backend dep to match upstream
  `[build-system].requires` (e.g. `poetry-core` → `hatchling`).
- **setuptools/pkg_resources (G34)**: add `setuptools <81` to `run`.
- **Version float-parse (G14)**: quote `version: "{{ version }}"`.
- **Renamed/absent dep (G10)**: swap to the conda-forge spelling, or loosen to
  an available equivalent + TODO (`feedback_loosen_pins`).
**AC**: a minimal, single-purpose diff; unrelated lines untouched.

### S6. Build + test the fix locally
- v1: `rattler-build build --recipe recipe/recipe.yaml --variant-config
  .pixi/envs/local-recipes/conda_build_config.yaml --output-dir <out>` — **do
  not** pass `.ci_support` (its strict `channel_sources` excludes the just-built
  package from its own test, G33).
- v0: `conda-build recipe/ -m .ci_support/<local_test_subdir>.yaml -c
  conda-forge --no-anaconda-upload`.
- **AC**: build EXIT=0 **and** `python imports test passed` + `pip check passed`
  on the intended Python (confirm the python the test actually ran on, esp.
  after a G31 floor change).

### S7. Mirror to the fork branch, push, rerender
`git -C <fork-checkout> checkout <pr-head-branch>`, copy the fixed recipe over,
commit (descriptive message + Co-Authored-By trailer), then **maintainer-edit
push**: `git push https://github.com/<bot_fork>/<feedstock>.git
HEAD:<pr-head-branch>`. Delete any stray branch a mistaken `origin` push created
(`git push origin --delete <branch>`). Then `@conda-forge-admin, please
rerender`. **AC**: the PR shows the fix commit; rerender requested.

---

## Stories — Wave D: Blocked-PR handling

### S8. Identify the prerequisite and decide land-vs-defer
For each BLOCKED PR: name the missing prerequisite (a dep feedstock behind the
pinned version, or N sibling feedstocks). Check the prerequisite's state
(`conda search -c conda-forge "<dep>==<X>"`; `gh pr list` on its feedstock; is
`<fork_owner>` a maintainer there?). Present to the operator:
- **(a)** land the prerequisite first (bump the dep/sibling feedstocks), then
  return to Wave C for the blocked PR;
- **(b)** defer (park the PR; the fix edit stays staged locally);
- **(c)** G26 source-patch loosen — only with the operator's explicit OK, noting
  the runtime-compat risk.
**Never** silently loosen. **AC**: each BLOCKED PR has a named blocker and an
operator-chosen disposition (default: defer).

---

## Stories — Wave E: Verify & retro

### S9. Verify merges
Re-check each pushed PR: did rerender + CI go green and (with `bot-automerge`)
merge? Catch any re-failure and loop back to Wave C. **AC**: a final
per-PR status table (MERGED / pending / deferred).

### S10. CFE skill closeout retro (BMAD↔CFE Rule 2 — always-on)
Run `bmad-retrospective` focused on `conda-forge-expert`. Land any **novel**
signature, fix mechanic, or trap as a new gotcha in `SKILL.md`, a CHANGELOG
entry, and a semver version bump; save a cross-skill auto-memory only if the
finding crosses skill boundaries. **AC**: a CHANGELOG entry (even if "no
changes; existing guidance held"). *The first worked example produced G31–G34 +
v8.30.0 + `feedback_test_locally_before_push`.*

---

## Open Questions (pre-resolved; override only per case)

- **Q1 — Restart flakes without a local build?** **Yes.** A FLAKE has no recipe
  change; the restart *is* the fix, so the test-locally-first rule doesn't apply.
- **Q2 — Rerender after every push, even dep-only changes?** **Yes** — per the
  standing rule (`feedback_always_request_rerender_after_feedstock_push`, "any
  file type"). Override only if the operator says dep-only changes may skip it.
- **Q3 — How to update a bot PR?** **Maintainer-edit push** to the
  `<bot_fork>` fork branch (G32); a plain `git push` from a `gh pr checkout`
  clone lands a stray branch on the canonical repo.
- **Q4 — Loosen a pin to unblock a blocked dep?** **No, by default** — land the
  prerequisite first; G26 source-patch is the fallback and needs an explicit
  operator OK (runtime risk). Deferring is the safe default.
- **Q5 — v1 vs v0 `python_min` override mechanism?** v1 → recipe-local
  `conda_build_config.yaml` + rerender; v0 → `{% set python_min %}` (G31).
- **Q6 — Full rebuild for a structural no-op edit?** A `--render-only` proving
  the rendered build script is unchanged is sufficient; a full rebuild is
  optional (the recipe already passed CI with the identical commands).

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Unverified push → red CI churn / bad automerge | Rule 2 (test locally first); S6 gate. |
| Plain `git push` lands a stray branch on the canonical repo | Rule 4 maintainer-edit push (G32); delete stray branch. |
| `conda search` not-found listing misread as available → wrong "fix" | G33 — a real hit prints a full `<name> <ver> <build> <channel>` row; `  - <dep>==<X>` is a `PackagesNotFoundError` line. |
| `<fork_owner>` not a maintainer of the prerequisite feedstock | Surface in S8; the maintainer-edit push won't work there — defer or escalate. |
| Disproportionate full rebuild for a one-line no-op | Q6 — render-validate instead. |
| python_min "fixed" in `context:` on v1 but CI still 3.10 | G31 — must use the recipe CBC + rerender. |

---

## Acceptance criteria (whole effort)

- [ ] Every `<pr_refs>` PR is classified (Wave A) and reaches a terminal state.
- [ ] No recipe edit was pushed without a green local build/test (or a
      render-validate for a structural no-op).
- [ ] Every FLAKE got a restart; no FLAKE got a needless edit.
- [ ] Every BLOCKED PR names its prerequisite and has an operator disposition.
- [ ] A final per-PR status table is produced (Wave E S9).
- [ ] The CFE skill closeout retro landed a CHANGELOG entry (Wave E S10).

---

## Adjacent case: staged-recipes review-comment remediation

A reviewer comment on a **staged-recipes** PR (new-recipe submission) is *not* an
autotick failure, but the same spine applies: read the comment → fix the local
mirror `recipes/<name>/` (source of truth) → verify locally (render or build) →
sync to the fork branch. The differences: the PR head is usually the maintainer's
*own* fork (so a plain `git push origin <branch>` updates it — no maintainer-edit
indirection), and the operator may choose to handle the push/reply themselves.
*First instance: lyric-py staged-recipes #33764 (collapse a redundant identical
`if: unix` block) — fixed + render+build-verified in the local mirror; operator
handled the PR push.*

---

## Reference

- **`conda-forge-expert` SKILL.md** — "Diagnostic chain for feedstock CI test
  failures"; gotchas G10, G14, G19, G24, G26, **G31–G34** (this spec's first
  worked example authored G31–G34).
- **Auto-memories** — `feedback_test_locally_before_push`,
  `feedback_local_mirror_first_then_verify_then_push`,
  `feedback_always_request_rerender_after_feedstock_push`,
  `feedback_loosen_pins`, `feedback_bump_build_number_on_feedstock_pr_update`,
  `feedback_omit_python_min_at_default_floor`.
- **Sibling specs** — `feedstock-platform-expansion.md`,
  `cfe-pr-artifact-downloader.md`.

---

# Worked Examples

> Each case records the PR set, per-PR classification + outcome, and any novel
> finding (which feeds the Wave E skill retro).

## Worked Example: 2026-06-17/18 batch — 12 PRs (first run of this workflow)

| Parameter | Resolved value |
|---|---|
| `<pr_refs>` | 12 PRs (11 feedstock autotick + 1 staged-recipes review comment) |
| `<mode>` | `batch` (6 parallel diagnostic subagents in Wave A) |
| `<fork_owner>` | `rxm7706` |
| `<local_test_subdir>` | `linux_64` |

**Empirical state (verified 2026-06-17/18)**: mixed format (v0 meta.yaml +
v1 recipe.yaml); all feedstocks `rxm7706`-maintained except the prerequisite
`sqlglot-feedstock` (caused the collate block).

### Per-PR classification + outcome

| PR | Class | Root cause | Fix | Outcome |
|---|---|---|---|---|
| cocoindex #12 | FLAKE | win pixi-provision `dispatch task is gone` (`attrs` fetch) | restart ci | **MERGED** |
| html-to-markdown #110 | FLAKE | win-py3.12 `dispatch task gone` (`m2-libintl`) | restart ci | **MERGED** |
| dlt #65 | FLAKE | win `_Py_HashRandomization_Init: failed to get random numbers` | restart ci | **MERGED** |
| selectolax #29 | FLAKE | osx-arm64-py3.13 `IncompleteRead` mid build-env download | restart ci | **MERGED** |
| llms-py #39 | REAL_FIX | `datetime.UTC` (py3.11+); 3.10 floor failed import | python_min 3.11 via **recipe CBC** (v1, G31) | **MERGED** |
| copilotkit #20 | REAL_FIX | pip_check: `ag-ui-langgraph>=0.0.35` needed, recipe capped `<0.0.32` | bump run dep `>=0.0.35` | **MERGED** |
| okta-jwt-verifier #8 | REAL_FIX | `retry2>=0.9.5` not on conda-forge | swap → `retry` (loosen + TODO, G10) | **MERGED** |
| fs.googledrivefs #7 | REAL_FIX | `import fs` → `No module named 'pkg_resources'` (setuptools 82) | `setuptools <81` in run (G34) | **MERGED** |
| wagtail-nav-menus #8 | REAL_FIX | `BackendUnavailable: hatchling.build` (upstream switched backend) | host `poetry-core` → `hatchling` | **MERGED** |
| wagtail-sharing #5 | REAL_FIX | `requires-python >=3.12` + linter float-parse | `{% set python_min = "3.12" %}` (v0, G31) + quote version (G14) | **MERGED** |
| microsoft-kiota-bundle #2 | BLOCKED | 5 sibling feedstocks at 1.10.1, recipe pins `1.10.3.*`; no sibling PRs | **deferred** (operator) | parked |
| collate-sqllineage #33 | BLOCKED | upstream pins `sqlglot==29.0.1`; conda-forge max 28.10.1; bump PR conflicting + not `<fork_owner>`'s feedstock | **deferred** (operator) | parked |
| lyric-py (staged-recipes) #33764 | adjacent | reviewer: redundant identical `if: unix` branches | collapse to single content entry; render+build-verified | operator-handled |

**Tally**: 10 merged (6 real fixes + 4 flake-restarts), 2 deferred-as-blocked,
1 adjacent review-comment fix (operator pushed).

### Novel findings → Wave E retro (CFE v8.30.0)
- **G31** — python_min override differs by format (v1 CBC+rerender; v0
  `{% set %}`); `context.python_min` is silently ignored on v1 feedstocks.
- **G32** — flake-vs-fix triage signature catalog + maintainer-edit push (the
  `gh pr checkout` → upstream-`origin` stray-branch trap).
- **G33** — local v1 build must not pass `.ci_support` (strict `channel_sources`
  excludes the just-built package from its own test); the `conda search`
  not-found-listing misread trap.
- **G34** — `pkg_resources.declare_namespace` deps break under setuptools 81+.
- **Auto-memory** — `feedback_test_locally_before_push`.

### Per-case decisions
- Both BLOCKED PRs deferred (operator chose skip/hold over bumping the
  prerequisite feedstocks or G26-loosening).
- lyric-py verified with a full 4-variant local build (all green) even though
  the change was a structural no-op, because the operator's "test locally first"
  directive was explicit; render-only would have sufficed per Q6.
