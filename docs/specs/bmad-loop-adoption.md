---
status: in-progress
spec_updated: 2026-07-12
---
# Tech Spec: BMAD 6.10 upgrade + bmad-loop adoption

> **Intake spec** (executed directly, 2026-07-12). Upgrade the repo's BMAD
> Method install 6.6.0 → 6.10.0 (gains the `bmad-dev-auto` unattended
> implementation skill) and adopt **bmad-loop** (the deterministic
> dev-orchestration companion) so the `python-deptry-osv-scanner`
> implementation can run loop-driven with code-based gates ("Option B",
> user-selected 2026-07-12). Enables graduated autonomy:
> `per-story-spec-approval` gates for the contract-freeze stories
> (1.1a/1.1b), relaxing to `per-epic`/`none` once the conformance harness
> polices the loop.

## Grounding (verified 2026-07-12)

| Fact | Evidence |
|---|---|
| Installed BMAD: **6.6.0** (2026-04-30; modules core+bmm) | `_bmad/_config/manifest.yaml` |
| `bmad-method` **6.10.0 on conda-forge** (noarch: generic, MIT, 2026-07-04) | `pixi search` |
| `bmad-dev-auto` ships in upstream `src/bmm-skills/4-implementation/` (v6.10.0): clarify-route → plan → implement → review; spec-driven ("Ready for Development" criteria); reviewer subagents vs ACs | raw SKILL.md |
| **bmad-loop v0.8.1** (`bmad-code-org/bmad-loop`, MIT, 20 releases): deterministic Python orchestrator — DEV→VERIFY→REVIEW→VERIFY→COMMIT in fresh tmux agent sessions; `[verify] commands` (pytest/ruff-class), `[gates] mode ∈ {none, per-epic, per-story-spec-approval}`, CRITICAL-escalation + `resolve`, plateau-defer, resumable state machine | README |
| bmad-loop is **git-only** (not on PyPI, not on conda-forge) | pypi.org JSON 404; pixi search empty |
| `tmux` on conda-forge (3.7b); absent from the host system | `pixi search`; `tmux: command not found` |
| Neither dev-auto nor bmad-loop appears in `docs.bmad-method.org/llms-full.txt` — docs lag source | live fetch |

## Provisioning decisions (pixi-first, per user directive)

- **`bmad-method >=6.10.0,<7`** — conda-forge dep in `[feature.local-recipes.dependencies]` (was: npx-era install; the conda package provides the installer CLI).
- **`tmux >=3.4`** — conda-forge dep (bmad-loop requirement).
- **`bmad-loop`** — pixi **pypi git dependency** pinned to tag `v0.8.1` with the `tui` extra (git-only upstream). *Follow-on candidate: package `bmad-loop` for conda-forge via the CFE factory (it is exactly this repo's job); revisit post-adoption.*

## Waves

- **W1 — upgrade BMAD 6.6.0 → 6.10.0.** Add pins → `pixi install` → run the installer's update flow (`bmad-method install`, non-interactive where possible) → **verify the repo-custom surfaces survived**: (a) `_bmad/scripts/resolve_config.py` — carries the repo-custom **multi-project layers 5/6** (`--project` / `BMAD_ACTIVE_PROJECT` / `.active-project` marker); if regenerated, restore the custom merge; (b) `_bmad/custom/*.toml` (team/user overlays — designed to survive); (c) `scripts/bmad-switch` (repo-root, untouched by installer); (d) `.claude/skills/bmad-*` regenerate — confirm `bmad-dev-auto` (+ any new 6.10 skills) appear and existing skill customize.tomls still resolve. Gate: `bmad-drift-check` integrity + the skill meta-tests green; re-stamp baseline if surface-changed.
- **W2 — install + init bmad-loop.** Env-resident via the git pypi dep; `bmad-loop init` (installs its hooks/policy + bundled skills `bmad-loop-resolve/-sweep/-setup`); configure `[verify] commands` = this repo's pixi test tasks (scanner: `python-deptry-osv-scanner-test`), `[gates] mode = "per-story-spec-approval"`, review trigger `recommended`, claude CLI profile. Gate: `bmad-loop --help` + a dry `bmad-loop tui`/`run --story` smoke on a no-op.
- **W3 — wire the scanner pilot.** Generate the story feed for `python-deptry-osv-scanner` (sprint-status via `bmad-sprint-planning`, or a typed `stories.yaml` pointing at the 20 epics.md stories); verify dev-auto's config resolution honors the **multi-project** `planning_artifacts` path (the likeliest friction — fix via its `customize.toml` layer if not); pilot on **Story 1.1a** with per-story gates. Gate: the loop runs 1.1a to a spec-approval halt with a valid spec artifact.

## Risks

1. **`resolve_config.py` clobber** — the multi-project pattern (layers 5/6) is repo-custom; the 6.10 installer may regenerate the script. Mitigation: git diff post-upgrade; restore/re-apply the custom merge; the meta-test + `bmad-switch --current` verify.
2. **Skill regeneration vs local conventions** — 42 skills refresh; per-skill `customize.toml`s under `_bmad/custom/` survive by design, but verify the two agent overlays (`bmad-agent-dev/pm.toml`).
3. **dev-auto path assumptions** — upstream expects the standard `{output_folder}`; this repo resolves per-project. Fix belongs in customize layers, never by forking the skill.
4. **bmad-loop maturity (v0.8.x)** — mitigated by the per-story gate mode for the pilot + the deterministic verify commands.

## Definition of Done

- [ ] W1: manifest reads 6.10.0; `bmad-dev-auto` present; custom layers verified; drift-check green (+ baseline restamp if needed).
- [ ] W2: `bmad-loop` runs from the pixi env; init complete; config committed.
- [ ] W3: pilot reaches the 1.1a spec-approval gate.
- [ ] `status: shipped` with `shipped_ref`.

*CFE Rules 1/2: N/A (no recipe work) — unless the bmad-loop conda-forge packaging follow-on is taken up, which would engage them.*
