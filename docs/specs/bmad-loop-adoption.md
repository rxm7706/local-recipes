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
> (1.1/1.2), relaxing to `per-epic`/`none` once the conformance harness
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
- **W4 — official BMad Method UI dashboards (added 2026-07-12, user request).** Leverage
  `bmad-code-org/bmad-method-ui` via the **consume-not-submit** pattern (G58/db-gpt
  precedent): staged-recipes **PR #33513** (OPEN, author killua156) ships two recipes —
  `bmad-dashboard` (noarch: the VS Code extension .vsix + `bmad-dashboard-install` CLI)
  and `mybmad-dashboard` (arch-specific: the Next.js web dashboard + `mybmad` launcher
  managing a per-user PostgreSQL; skip win). Mirror both into `recipes/` (faithful body,
  cfe metadata appended, `cfe-submission-pr` → #33513), build locally (rattler-build,
  linux-64), and consume from the local channel via a lean `bmad-ui` pixi env
  (`pixi run bmad-dashboard-install` / `pixi run mybmad up`). **Rule-2 flip:** this wave
  touches `recipes/` — the effort's closeout now REQUIRES a CFE-skill retro (previously
  N/A). Never submit or compete with #33513; when it merges + the packages land on the
  channel (G66), swap the local-channel deps for conda-forge ones + re-stamp cfe-status.
- **W3 — wire the scanner pilot.** Generate the story feed for `python-deptry-osv-scanner` (sprint-status via `bmad-sprint-planning`, or a typed `stories.yaml` pointing at the 20 epics.md stories); verify dev-auto's config resolution honors the **multi-project** `planning_artifacts` path (the likeliest friction — fix via its `customize.toml` layer if not); pilot on **Story 1.1** with per-story gates. Gate: the loop runs 1.1 to a spec-approval halt with a valid spec artifact.

## Risks

1. **`resolve_config.py` clobber** — the multi-project pattern (layers 5/6) is repo-custom; the 6.10 installer may regenerate the script. Mitigation: git diff post-upgrade; restore/re-apply the custom merge; the meta-test + `bmad-switch --current` verify.
2. **Skill regeneration vs local conventions** — 42 skills refresh; per-skill `customize.toml`s under `_bmad/custom/` survive by design, but verify the two agent overlays (`bmad-agent-dev/pm.toml`).
3. **dev-auto path assumptions** — upstream expects the standard `{output_folder}`; this repo resolves per-project. Fix belongs in customize layers, never by forking the skill.
4. **bmad-loop maturity (v0.8.x)** — mitigated by the per-story gate mode for the pilot + the deterministic verify commands.

## Execution log (2026-07-12)

- **W1 DONE** (`792597d0d0` + provisioning `73f6d9a77b`): core+bmm 6.6.0→6.10.0; 46 skills
  (new: `bmad-dev-auto`, `bmad-architecture`, `bmad-prd`, `bmad-spec`, `bmad-ux`,
  `bmad-forge-idea`; old create-prd/-architecture/-ux/-validate-prd now DEPRECATED thin
  wrappers — **update CLAUDE.md's skill table + the skill-disambiguation memory at the
  next sync pass**). Risk #1 materialized exactly as predicted: the 6.10 stock
  `resolve_config.py` drops the multi-project layers — **restored the repo-custom
  version** (verified: `bmad-switch --current`, agents resolution, customization merge);
  kept the new `resolve_customization.py` (upstream utf-8 fix). Custom overlays survived
  (hash-verified). Drift-check: 0 integrity.
- **W2 DONE** (`5da9175431`): init (hook + hooks in `.claude/settings.json` + 3 bundled
  skills + policy); policy = per-story-spec-approval gates + the scanner pytest task as
  the `[verify]` command. **Multi-project seam resolved via local symlinks**: root
  `_bmad-output/{planning,implementation}-artifacts` → the active project's dirs
  (gitignored; re-point when `bmad-switch`ing — follow-on: teach `scripts/bmad-switch`
  to manage them). `bmad-loop validate`: all OK except the W3 sprint-status feed.
- **W3 feed DONE** (`0ab9308d3f` + sprint-status): stories renumbered pure-numeric
  (bmad-loop's parser ignores letter suffixes — 12/20 → 20/20 actionable);
  `bmad-loop validate` **9/9 OK**. Remaining W3: the human hooks-approval + the 1.1
  pilot run.
- **W4 DONE (2026-07-12).** Both #33513 recipes mirrored (13 files, faithful body +
  cfe blocks + schema headers), validated (conda-smithy lint clean), and **built
  GREEN locally** (rattler-build, linux-64): `bmad-dashboard 1.2.2.dev0` (noarch,
  3.8 MiB, ✔ all tests) + `mybmad-dashboard 0.1.0.dev0` (4 py-variants ~48 MiB,
  4× ✔ all tests; `version_independent` lets any-python installs use one build).
  Consumed via the new lean **`bmad-ui` pixi env** (linux-64-only feature; local
  `./build_artifacts/linux64` channel + conda-forge): `pixi run -e bmad-ui
  bmad-dashboard-install` (vsix resolves) and `mybmad --help`/`info` smoke-tested
  GREEN. Parse-audit meta-test 5/5. **Rule-2 now ENGAGED** (recipes/ touched).
- **One-time human step before any run:** launch `claude` once in the repo to accept
  the newly-registered hooks (a pending approval dialog reads as a session timeout to
  the loop).

### Windows-without-WSL note (recorded 2026-07-12, user question)

bmad-loop hard-depends on **tmux** (`TmuxMultiplexer` + `PosixProcessHost`) — no native
Windows path exists upstream (declared support: Linux/macOS, "Windows via WSL"), and
tmux has no win-64 build anywhere (it is fundamentally POSIX). Native-Windows
contributors therefore: **(a)** run the *attended* flows, which are OS-agnostic —
`bmad-dev-story` / `bmad-quick-dev` / even `bmad-dev-auto` invoked inline in a Claude
Code session (it is the *orchestrator*, not the skills, that needs tmux); **(b)** use
WSL2 (the upstream-supported path) or the pixi-docker/devcontainer route; **(c)** a
tmux-free Windows adapter (e.g. a plain subprocess host) would be an upstream
bmad-loop contribution — filed as a watch item, not this effort's scope. Note the
distinction: this constrains only *dev-time orchestration in this factory* (linux-64 +
osx-arm64 hosts); the **scanner product's** own Windows support is a separate question
owned by its NFR-C1 OS-matrix decision.

## Adjacent-skills survey: `bmad-labs/skills` (2026-07-12, user question)

**Verdict: nothing to include.** `bmad-labs/skills` is a **community skills
marketplace** (MIT, unversioned, no stated relationship to `bmad-code-org` —
a different trust/lifecycle tier than the installer-managed 6.10 skill set),
carrying ~17 general-purpose Claude Code skills (TypeScript unit/e2e testing,
slides, EPUB conversion, Jira/Confluence, Gemini multimodal, release-please,
RCA reports, …). Screened against this effort: **zero overlap with the
loop/dev-auto orchestration need**, and every near-candidate duplicates
something the estate already has stronger in-method (`bmad-technical-research`
/ `bmad-domain-research` over `software-research`; BMAD elicitation/party-mode
over `trade-off-analysis`; the repo's own presentation-deck workflow over the
slide skills; the FastMCP server over `mcp-builder`). Installing unmanaged
third-party skills into `.claude/skills/` would also sit outside the
installer/`customize.toml` lifecycle this effort just carefully preserved
through the upgrade. **Watch item only:** `software-research`'s version-aware
primary-source verification pattern rhymes with the CFE quantitative-claims
discipline — revisit if the estate ever wants a general research-hardening
skill; and note `npx skills add` as an install channel should a curated
third-party skill ever be adopted deliberately.

**Second survey (same day, user question): "bmad-pro-skills" on
claudepluginhub.com → the listing is a phantom.** No `bmad-pro-skills` repo
exists in `bmad-code-org` (verified: full org enumeration + the official
`bmad-plugins-marketplace` registry, which carries exactly 3 modules); the
403-walled third-party directory entry is almost certainly a scraped
repackaging of the official BMM skills — **already installed here at 6.10.0
via the conda-forge `bmad-method` installer**. Rule recorded: third-party
directory repackagings of BMAD content are untrusted duplicates; the
installer is this repo's only skills channel. The survey's real find,
**`bmad-code-org/bmad-utility-skills`** (BMad Certified, 10 maintainer
skills), screens to **nothing-to-install**: `bmad-os-review-pr` duplicates
the installed `bmad-code-review` layers; `bmad-os-audit-file-refs` is a
generic `bmad-drift-check`; changelog/gh-triage/RCA lose to the CFE retro
protocol, the FLAKE/REAL_FIX/BLOCKED remediation taxonomy, and the Build
Failure Protocol respectively; Diataxis/translation N/A. **Two watch
items:** `bmad-os-findings-triage` (if the post-loop review→triage flow
feels thin) and `bmad-os-skill-to-bundle` (the day `conda-forge-expert` or
team skills are distributed — `claude-team-memory` territory).

**Third survey (same day, user question): "bmad-autopilot" on
mcpmarket.com → an independent community *precursor*, no relationship.**
The listing maps to `martin-janci/autopilot` (a thin skill shelling out to
a bash orchestrator, epic-granular, created 2025-12-23 / dormant since
2025-12-24; the name is crowded — ≥8 unrelated community repos, none from
`bmad-code-org`). It uses **neither** `bmad-dev-auto` nor `bmad-loop` — it
predates both; the officially-adopted stack is its architectural successor
(deterministic Python gates vs bash+trust; fresh sessions per story vs one
long session; story- vs epic-granular). **The one delta worth keeping —
PR-lifecycle automation:** bmad-autopilot's loop covered
create-PR → watch-CI → respond-to-review-comments → auto-merge, where
`bmad-loop` deliberately stops at local commit/merge-back (its `[scm]`
block does worktree/branch merging; no PR creation or CI monitoring).
**Follow-on candidate (not this effort's scope):** if PR-per-epic
automation is ever wanted on top of the loop, that is a real gap to fill —
a small wrapper around `gh pr create` triggered at the existing
`[gates] per-epic` boundary (plus CI-watch/auto-merge via `gh pr checks`
/ `gh pr merge --auto`), or an upstream `bmad-loop` feature request.
Revisit when the fleet-scale phase (or multi-epic parallel work) makes
single-branch flow limiting.

## Definition of Done

- [x] W1: manifest reads 6.10.0; `bmad-dev-auto` present; custom layers verified; drift-check green.
- [x] W2: `bmad-loop` runs from the pixi env; init complete; policy committed; validate green modulo the W3 feed.
- [x] W3 (feed): sprint-status generated (20/20 actionable); `bmad-loop validate` 9/9 OK.
- [ ] W3 (pilot): human hooks-approval + the Story-1.1 run reaches the spec-approval gate.
- [x] W4: both staged-recipes **#33513** recipes mirrored + built GREEN locally + consumable via the `bmad-ui` pixi env (`bmad-dashboard-install`, `mybmad`).
- [ ] Rule-2 CFE-skill retro at closeout (engaged by W4).
- [ ] `status: shipped` with `shipped_ref`.

*CFE Rules 1/2: N/A (no recipe work) — unless the bmad-loop conda-forge packaging follow-on is taken up, which would engage them.*
