# Failure modes — the three live BMAD core upgrades

Trap catalog from the three upgrades performed so far: 6.6.0→6.10.0
(bmad-loop-adoption W1, 2026-07-12) and 6.10.0→6.11.0 (2026-08-21, branch
`bmad-method-v6.11.0-update`) and 6.11.0→6.12.0 (2026-09-06, the first
steward-driven apply, branch `steward/bmad-core-upgrade-6.12.0`). Every row was hit live. CAP-1 must detect the
detectable ones; CAP-3/CAP-5 must catch the rest.

## Traps

| # | Trap | Hit in | What happened live | Owning CAP |
|---|---|---|---|---|
| 1 | Installer clobbers `_bmad/scripts/resolve_config.py`, dropping the repo-custom multi-project layers 5/6 (`--project` / `BMAD_ACTIVE_PROJECT` / `.active-project`) | BOTH | 6.11 rewrote it as a four-layer script delegating to new `config_utils.py`; zero references to the marker survived; custom merge re-applied by hand onto the new structure (one `.bak` left by installer) | CAP-3 |
| 2 | Legacy-name customization files halt the deprecation shims | 6.11 (latent) | `_bmad/custom/bmad-dev-auto.toml`, if present, makes the shim refuse to forward — unattended sessions halt with nothing on disk. Repo was clean; loop homes audited clean. Never author overrides under old names | CAP-1 |
| 3 | `removals.txt` deletes retired skills outright on update | 6.11 | `bmad-check-implementation-readiness`, `bmad-agent-tech-writer`, `bmad-shard-doc`, `bmad-index-docs` vanished from `.claude/skills/` — docs naming them (CLAUDE.md, SYNC-RUNBOOK) had to move to successors by hand | CAP-1 |
| 4 | New hard prerequisite appears (uv ≥ 6.11 for build/build-auto; Python ≥ 3.11) | 6.11 | Satisfied via pixi env (`uv 0.12.5`); anything invoking skills outside the env PATH halts | CAP-1 |
| 5 | Downstream pin fan-out: one tool's floor lives in MANY sites that don't auto-propagate | 6.11 | bmad-loop's floor lived in **4 code sites**: root `pixi.toml`, marshal `pyproject.toml`, marshal package `pixi.toml` (the one that actually feeds the conda build), `HARNESS_VERSION_RANGE_TEXT` in `harness_bmadloop.py` — plus the seed template manifest (8 pins) and its drift-test expected map, plus 10 test fixtures with version literals | CAP-4 |
| 6 | pixi does not re-solve when a path-dep's own metadata changes | 6.11 | After editing marshal's pyproject/pixi.toml pins, `pixi update -e pyforge-marshal` reported "already up-to-date" three times; fix was evicting the env blocks from `pixi.lock` and re-solving (`pyforge-container` too) | CAP-4 (report), operator applies |
| 7 | Loop-home hook relays go stale on a bmad-loop upgrade | 6.11 | All 8 homes warned `hooks.relay-stale`; `bmad-loop init` per home refreshed them; validate then 8/8 clean, zero warnings | CAP-5 |
| 8 | Old git-add shield lines linger in `.git/info/exclude` after a bmad-loop ≤0.9.1 → 0.10+ upgrade | 6.11 | 7 lines removed by hand — every one first verified redundant with `.gitignore` (they were interleaved with load-bearing comment history; a grep-delete would have been wrong) | CAP-5 |
| 9 | Upstream behavior changes ride the forwarders — old orchestrators break subtly | 6.11 | The `bmad-dev-auto` shim forwards to the NEW build-auto contract (`final_revision` gone, Tier-3 `deferred-work.md` gone, halt strings changed); bmad-loop 0.9.0 hardcoded `/bmad-dev-auto` and would stall unattended — its 0.9.1 was an emergency hotfix for exactly this. Coordinated suite waves followed (uv-run conversion, `persistent_facts` emptied for AGENTS.md) | CAP-1 (min-version report) |
| 10 | Per-module `--set` keys not declared in `module.yaml` are dropped on the next install | 6.11 (latent) | "The manifest writer's schema-strict partition" — undeclared keys land once in config.toml, then vanish on the next install | CAP-3 |
| 11 | Config-format migration is staged across releases | 6.11 (latent) | Four-layer TOML is "the migration, not the cutover"; `_bmad/bmm/config.yaml` (which the planning-artifacts symlink pattern depends on) still ships but is slated to go — the cutover release must be flagged loudly | CAP-1 |
| 12 | `-y` does not skip the installer's **directory prompt**; with stdin closed (any non-TTY driver, incl. steward's `subprocess.run`) clack cancels and the installer exits **0 having written nothing** — a silent no-op apply | 6.12 | First steward `--apply` reported exit 0 / "installer produced no working-tree changes"; the truncated stdout hid the `Installation directory:` prompt. Fix: pass `--directory <repo>` (via the `--installer` wrapper) | CAP-2 (apply must refuse a zero-diff exit 0) |
| 13 | `--action update -y` **deletes an installed custom module** whose source is cached under `~/.bmad/cache/custom-modules`: `getDefaultModules` never selects it and `_retainUnavailableInstalledModules` only preserves modules with NO source, so it lands in `_removeDeselectedModules` | 6.12 | skf (skill-forge) vanished: 335 `_bmad/skf/**` files + 16 `.claude/skills/skf-*` dirs + its manifest rows; the installer even refreshed the skf cache to `main` first. 6.11's `-y` reinstalled it instead. Fix: select explicitly (`--modules core,bmm,skf`) | CAP-1 (catalog must name installed custom modules) / CAP-2 |
| 14 | A custom module's **`marketplace.json` skill list is now authoritative**: skill dirs it does not declare are not installed to the IDE, and the module's `config.yaml` is regenerated from `module.yaml` defaults (hand-set keys dropped; `prompt: false` keys render a literal `{project-root}/{value}`) | 6.12 | `skf-campaign` (shipped in `src/`, undeclared) dropped; `_bmad/skf/config.yaml` lost `ides` / `skills_output_folder: .claude/skills` / `snippet_skill_root_override` and gained `sidecar_path: "{project-root}/{value}"`; `_bmad/config.toml` grew a `[modules.skf]` block of defaults. Recovery: the module's OWN installer (`bmad-module-skill-forge update`) rebuilds a coherent tree with all 16 skills and preserves config.yaml verbatim — restore config.yaml first | CAP-3 (extend "clobbered custom surfaces" beyond resolve_config.py) |
| 15 | CAP-5 runs in the `pyforge-steward` env, which has **no `pyforge.doctor`** — the bmad-drift-integrity gate FAILs on import even when `bmad-drift-check` (local-recipes env) is all-ok; the uv-from-git spot-check hardcodes `uv tool install --dry-run` (no such flag in uv 0.12.10) and cites `@v0.11.0` while the matrix says `@v0.11.1` | 6.12 | prove-landed verdict FAIL for env reasons only; 8/8 relays refreshed, 7/8 homes clean (marshal home dirty from a pre-existing untracked `marshal-model-cost-catalog.json`, 2026-09-02) | CAP-5 |

## The 2026-08-21 verification worked example (CAP-5's target)

1. `pixi run -e local-recipes bmad-method-version-drift-check` → ok/ok
2. `bmad-drift-check` integrity findings only pre-existing (uncovered rule added)
3. CFE skill meta-tests: `test_bmad_artifacts_in_sync` green
4. Marshal full suite after pin fan-out: 5152 passed; smoke `marshal --version` → `bmad-loop 0.11.0`
5. Per loop home: `bmad-loop init` (relay refresh) → `bmad-loop validate` → 8/8 clean, zero warnings; strict `limits.*` typing passed on every rendered policy
6. `environment.yaml` regenerated after the pixi.toml floor bumps (ungated sync check)

## Suite orbit (non-goal here, recorded for the boundary)

The bmad-suite conda recipes (SelfExplainML channel: bmad-loop, TEA, builder,
CIS, skill-forge, manticore) were bumped the same day through the CFE factory
flow — recipes → local green builds → `anaconda upload` → pixi floor bumps.
That flow already exists and is owned by the packaging factory, not steward.
The gap worth relaying: nothing ambient reported the suite lag (bmad-loop sat
two minors behind); see SPEC open question on extending doctor's drift.
