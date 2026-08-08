# Technical research — PyForge fleet unification, 2026-08-08

> **Scope (operator ask):** the cross-cutting unification vision across all 8
> PyForge stations — one container, local-zero-infrastructure vs an optional
> UI-backed mode, agent portability beyond Claude, the BMAD-METHOD ecosystem
> posture, the Kedro question, and architecture consolidation. Marshal
> carries this research because it already owns the cross-station dreams
> (`agent-tool-surface`, `one-front-door`, `agent-portability`,
> `regenerable-factory`, and the archived console pair). Everything below is
> grounded in a same-day survey of the shipped tree; external-tool framing
> defers to `market-marshal-orchestration-refresh-2026-08-08.md`.
>
> Fleet ground truth (measured): 8 station packages under
> `src/shared/packages/pyforge-*`, ≈83k src LOC / 218 files; marshal 34.2k,
> warden 16.6k, atlas 15.8k, herald 7.8k, doctor 3.7k, steward 2.7k, scribe
> 1.7k, mason 0.5k (skeleton). One `pyforge.*` namespace, hatchling +
> pixi-build-python throughout, every station wired into `pixi.toml` as a
> **conda path-dependency** (zero editable installs anywhere).

## 1. The integration surface today is the filesystem — and that is the finding

Before designing unification, name what exists. Across 8 stations there are
exactly **two Python cross-imports** (doctor→warden
`sources/warden.py:81`; atlas→warden `pipelines/universal_sbom/gate.py`),
**one MCP edge** (doctor spawns atlas's FastMCP server over stdio,
`doctor/sources/atlas.py`, with a CLI-bridge fallback), and **zero**
station-shelling-a-sibling-CLI calls. Both import edges are supplied at the
pixi *feature* level, not as package run-deps (`pixi.toml:1432,1508`), so
standalone conda installs keep warden optional. Everything else the fleet
"integrates" through is paths: `_bmad-output/projects/<slug>/…`,
`docs/dreams/*.md` frontmatter, `~/.bmad-loops`, `git log`, `tmux ls` —
which is exactly what `docs/dashboard/generate.py` reads (its
`PROJECT_SOURCES` dict at :45 hardcodes the 9 keys, with a live TODO to
derive them; the `dashboard-project-path-derivation` Dream documents the two
bug shapes this already produced).

Two implications: (a) the stations are *loosely coupled by design* — good
for the container story, since there is no daemon mesh to replicate; (b) the
coupling that does exist is **conventions nobody owns as code**: the station
roster is hardcoded in at least three places (`generate.py:621`,
`herald/progress.py:56`, `herald/web/src/components/Sidebar.jsx`), the
report envelope exists as two divergent JSON Schemas (warden 22 KB, doctor
4.5 KB), and where stations should touch (Marshal's landing feed → Herald's
dashboard) the hand-off is a remembered script (`sprint-status-auto-promote`
Dream). Unification's first target is these conventions, not a new runtime.

## 2. One container, eight stations

The Dream exists: `docs/dreams/unified-container.md` — **owner: steward**
(with an explicit reconsider-clause), **status: dreamt**, "Nothing built
yet," captured 2026-08-02 with the key argument that a single deployable
boundary is a *forcing function* for coherent architecture (citing the
2026-08-02 one-chain-per-station consolidation as its precursor). Marshal's
role is entrypoint, not owner: the Dream itself nominates `marshal` as the
single in-container front door per one-front-door.

**What containerizing actually takes, from the measured tree:**

- **Dependency resolution is already holistic and already solved by pixi.**
  The repo mixes ecosystems exactly three places: `[feature.vuln-db.
  pypi-dependencies]`, `[feature.local-recipes.pypi-dependencies]`
  (`boring-semantic-layer`, `kedro-mcp`), and `[feature.pyforge-atlas.
  pypi-dependencies]` (`boring-semantic-layer` only, with the AUD-ATLAS-010
  audit note explaining why it cannot be a conda run-dep). Everything else —
  including the entire BMAD stack — is conda, much of it **self-packaged: 16
  `recipes/bmad-*` directories** mean the factory builds its own
  orchestration toolchain (`recipes/bmad-loop/recipe.yaml` at 0.9.0 is what
  `pixi.toml:985` now consumes as a plain dep). A container build is
  therefore `FROM` a pixi-capable base + `pixi install --frozen` per env —
  no bespoke pip/conda reconciliation layer is needed; pixi.lock *is* the
  holistic resolution.
- **Pick envs, not "the env."** `pixi.toml` defines 20 environments. The
  default `local-recipes` env is **~1,102 packages / ~9.8 GB** (it blew the
  10 GB Actions cache, which is why the lean `pyforge-ci` env exists). The
  8 per-station envs are deliberately lean (`no-default-feature = true`,
  one built package + run-deps + pytest each). The natural image strategy is
  two tiers: **`pyforge-factory-core`** (the 8 station envs + `pyforge-ci`
  tooling — small, the "all 8 stations as one unit" ask) and
  **`pyforge-factory-full`** (adds `local-recipes` with the CFE skill,
  conda-smithy, grayskull, rattler-build — the packaging half). Shipping
  only the fat env would make the container a 10 GB artifact for users who
  want `marshal status`.
- **The real blockers are state and credentials, not packages** — each with
  a named home: loop homes live *outside* the repo at `~/.bmad-loops`
  (volume mount or in-image path convention); `tmux` is a hard bmad-loop dep
  (fine on linux-64; this is also why Windows is WSL2-only per
  `bmad-loop-adoption.md`); MCP registration for the legacy CFE server is
  **manual, machine-absolute, in `~/.claude.json`**
  (`agent-tool-surface.md`) — but Marshal already shipped the portable
  pattern: `marshal init` renders a per-home `.mcp.json` and AD-43 forbids
  touching `~/.claude.json`, so the container should standardize on the
  per-home render; `gh`/agent credentials and the age-encrypted key
  lifecycle are Steward's existing surface (`steward/keys.py`); mutable
  runtime state (`.claude/data/conda-forge-expert/` — cf_atlas.db, caches)
  is gitignored and needs a volume.
- **The dream's own acceptance test is right**: everything assuming a full
  git checkout + pixi env (loop homes, the detector suite — which
  `generate.py` runs stdlib-only on purpose — the dashboard) needs a
  containerized equivalent *or a named reason it doesn't*. The
  `enterprise-airgap` practice (realized) makes this stronger: a container
  built from the repo's own channel + JFrog routing is the offline bundle
  format `pyforge-genesis`-behind-a-firewall has been missing. One caveat to
  fix first: the known `JFROG_API_KEY` unconditional-injection leak in
  `_http.py` (auto-memory; "fix before wider enterprise rollout") becomes
  more exposed, not less, once the factory ships as an image people run.

**Recommendation:** treat the container as Steward-owned build work with a
Marshal-owned entrypoint contract, sequenced *after* the § 7 consolidation
decision — the Dream's forcing-function argument cuts both ways: baking
today's seven subprocess-guard variants into an image forces nothing, it
freezes them.

## 3. Zero-infrastructure local (today) vs a "with infrastructure" mode

**Today's reality is genuinely zero-server and should stay the default.**
The whole factory runs from: local pixi envs + git + tmux + gitignored local
state + a *static* GitHub Pages console. That console is real prior art for
the unified-UI ask and is more sophisticated than it looks:
`docs/dashboard/generate.py` (2,630 lines) reads nine sprint feeds, the
tracked ledger twin, epics files, dream frontmatter, `git log` merge
subjects, live tmux/`~/.bmad-loops` run state, and the detector registry;
`data.js` (13.8k lines) is a hand-curated narrative *seed* that git-mode
only ever upgrades (never downgrades); `index.html` is a self-contained
1,757-line shell; two detectors (`check_render.js`, `check_layout.py`)
gate it; `.github/workflows/dashboard.yml` republishes on push + daily cron
from the lean env. Coverage is all 8 stations + `regen`. The lineage of the
three console dreams is instructive: `artifact-console` (chat artifact) was
**retired** for being unregenerable; `factory-console` (this Pages console)
**shipped** and was absorbed; `one-front-door` became `marshal check`. The
factory has already run the experiment and the zero-infra, derived-from-repo
answer won.

**What a "with infrastructure" mode would actually add** (from the
Backstage/Port comparison in the market doc): write actions from the UI
(run a story, approve an escalation), event-driven freshness (vs 120 s
meta-refresh + daily cron + the three same-session staleness incidents in
`sprint-status-auto-promote`), auth for multi-operator use, and per-entity
drill-through (already named as `spec-factory-console`'s unbuilt frontier).
None of that requires Backstage: the container from § 2 is the natural
delivery vehicle — an optional `marshal serve`-style process (or simply the
existing pieces co-hosted: the dashboard, atlas's kedro-viz, herald's
`web/` React SPA — which today is a *separate, third* UI with its own copy
of the station roster) serving locally with the static Pages build remaining
the tracked, public source of record. Decision rule worth writing into any
future spec: **the static console is the contract; any live UI is a cache
over the same generators** — otherwise the artifact-console failure mode
(state that exists only in the running thing) returns.

## 4. Agent portability — with and without Claude

**What is real (shipped this week):** Marshal Epic 6, 9/9 done — profile-
driven adapter selection, skill-tree projection (`.claude/skills` as the
declared canonical tree, symlink-projected per adapter), projection-drift
detection that can genuinely fail (AD-31 meta-test), adapter probe with
machine-scoped records, conformance smoke in an ephemeral home
(read/change/verify/commit stages), the tracked per-host conformance
matrix, entry-file family drift check, the upstream-contribution register
(`upstream-register.json`), and tool-surface rendering. Upstream met it
halfway: bmad-loop 0.9.0 ships an OpenCode adapter, a Windows psmux
backend, and a **sanctioned Copilot profile**, and GitHub's `copilot --acp`
is in public preview (07-25 domain research).

**What is dead, honestly recorded:** both bridge specs are
`status: superseded`. `docs/specs/copilot-bridge-vscode-extension.md`'s
HTTP-proxy premise (stories 1–12, `copilot-api` on localhost:4141) is
obsolete — nothing was ever built (no `vscode-extension/` dir exists; the
referenced `copilot-to-api.md` reference was removed 2026-07-24) and the
07-25 research had independently concluded "do not build on a Copilot HTTP
proxy" and "do not build on `vscode.lm`" before upstream shipped the
sanctioned path. `docs/specs/bmad-copilot-adapter-upstream.md` (the `@bmad`
Copilot-Chat participant, upstream PR `bmad-code-org/bmad-method-ui#2`,
still unmerged) is deferred and **re-owned to Herald** as a comms-face item.
The rule of thumb both specs recorded survives: *chat adapter for humans in
the IDE; the harness profile for headless loops.*

**The honest gap:** portability is *proven as machinery, not as a run*.
Nothing in the ledger or memory shows a non-Claude adapter having driven a
real story end-to-end here — the conformance matrix exists precisely to
accumulate that evidence per host, and it starts empty. The Claude couplings
that remain are known and single-owned (`CANONICAL_SKILL_TREE_REL =
".claude/skills"`, the `claude` default profile in the vendored policy
template, the `("claude", ("CLAUDE.md","AGENTS.md"))` entry-file baseline) —
each is data, not scattered logic, which is what makes a second profile a
config change rather than a port. **Next verifiable step:** run
`marshal adapters probe` + `adapters smoke` against the copilot and
opencode profiles on this host and commit the first real matrix rows; that
single artifact converts CAP-6 from "proven, not claimed" aspiration into
its own evidence.

## 5. The BMAD-METHOD ecosystem — upstream, extension, and fork risk

Layered accounting, from the survey of `pixi.toml` + `docs/specs/
bmad-loop-adoption.md` + the 07-31 upstream verification:

- **Upstream consumed as-is:** `bmad-method >=6.10.0,<7` (conda-forge,
  51 skills installed; v6 current, no v7; roadmap names *Dev Loop
  Automation* — the standing convergence watch), plus the module set (BMB
  2.1.0, TEA 1.19.1, CIS 0.2.1, manticore, labs/utility/wds/template),
  every one consumed as a conda package, several via this repo's own
  staged-recipes PRs (#33123/#33124/#33126/#33127/#33129/#33292/#33513).
- **Upstream, self-packaged:** `bmad-loop = ">=0.9.0"` is now a plain conda
  dep built from `recipes/bmad-loop/recipe.yaml` — the spec-era git pin
  (`v0.8.1`, `tui` extra) is history. **16 `recipes/bmad-*` directories**:
  the factory packages its own method stack, which is both the distribution
  moat (07-31 market finding: no competitor has a package-manager-native
  story) and a standing maintenance duty (every upstream release needs a
  recipe bump — Mason/CFE work, on the tiered-packaging path).
- **This repo's own extensions — the real fork surface:** the multi-project
  machinery (`scripts/bmad-switch`, the six-layer config merge, the custom
  layers in `_bmad/scripts/resolve_config.py`) is *repo-custom code layered
  onto installer-regenerated files* — and the risk already materialized
  once: the 6.10 installer **dropped the custom multi-project layers**
  during W1 and they were restored by hand (`bmad-loop-adoption.md`).
  Second instance of the same class: Marshal's vendored 115-line
  `_POLICY_TEMPLATE` reproducing bmad-loop's policy schema (rot-on-bump —
  marshal technical doc § 3.2). Third: `bmad-dashboard 1.2.2.dev0` +
  `mybmad-dashboard` consumed as locally-built mirrors of an *unmerged*
  upstream state, with the `@bmad` adapter (`bmad-method-ui#2`) also
  unmerged upstream.
- **Mitigation that exists:** Marshal's Epic-6 upstream-contribution
  register (FR-58, `marshal upstream`) is the right ledger for exactly
  these three exposures; the forward-dependency detector's upstream
  contribution (bmad-loop lacks `depends_on`) belongs on it too. **The
  maintenance-risk verdict: acceptable and actively managed, with one
  process gap — nothing re-runs the "did the installer clobber our custom
  layers?" check after an upgrade; that belongs in `marshal check` /
  `bmad-preflight` as a detector, not in a runbook.**

## 6. The Kedro question — should other stations adopt Atlas's stack?

**No — and Atlas itself is the evidence.** The Kedro/Dagster/DuckDB
migration (`docs/specs/cfe-atlas-datapipeline-kedro-migration.md`,
`status: shipped`, 32 stories, PRs #58–#105 merged) produced ~29k LOC of
`pyforge.atlas` (7 Kedro pipelines, MCP server, DuckDB engine) — and the
legacy `conda_forge_atlas.py` (8,902 LOC) **is still the live runtime**:
every `build-cf-atlas`/`atlas-phase`/`query-cf-atlas` task and every atlas
MCP tool still shells to the old path; nothing routes to `pyforge.atlas`
(`docs/dreams/conda-forge-expert-rebuild.md` names this as its own
cautionary precedent — "the rebuild had no migration step"). `status:
shipped` here means *code merged*, not *runtime replaced* — a false-green of
exactly the class this factory's detectors exist to catch, and it should be
recorded on the spec. Added risk since: **Prefect announced acquisition of
Dagster Labs (2026-07-13)**, `kedro-dagster` bus-factor ≈ 1 — the spec
itself classifies these as replaceable glue with exit ramps.

Why the other stations don't fit the stack: they are CLIs and governance
surfaces, not batch data pipelines — Marshal's unit of work is a supervised
run, Warden's a compliance evaluation, Herald's a design round-trip; none
has the DAG-of-datasets shape Kedro models. The two places the *pattern*
(not the stack) genuinely applies: (a) `spec-fleet-chain-completeness` —
regenerating Dream→Spec→PRD→Architecture→Epics is an asset-materialization
graph over markdown, and Dagster's staleness model is the design to steal
(market doc § 2.2); (b) the dashboard generator, whose nine inputs and
derived outputs are a small static DAG. Neither justifies importing a
pipeline framework into 500–3,700-LOC stations. Meanwhile the fresh
`kedro-org-tooling-adoption` Dream (atlas-owned, 2026-08-07) correctly
keeps Kedro-tooling judgment with Atlas while routing install mechanics to
Steward's `bmad-module-provisioning` — the ownership pattern any future
shared-stack question should copy. **Fleet recommendation: finish (or
formally re-scope) the Atlas cutover before any station considers the
stack; the migration-step lesson is the transferable asset, not the stack.**

## 7. Architecture consolidation — the measured duplication census

Ranked by copy count (full file-level evidence gathered this session):

| # | Duplicated primitive | Copies | Notes |
|---|---|---|---|
| 1 | **Atomic write** (tmp-in-dir + `os.replace`) | ~20 across **8/8 stations** | Self-aware: docstrings say "mirrors `state.write`", "identical shape". Zero semantic divergence — trivially extractable. |
| 2 | **Subprocess guard / CLI bridge** | 7+ across 2 designs | doctor's `cli_bridge.run_cli_json` (AD-5, sole-site meta-test) vs marshal's `ProcessPort`/`process_posix`; herald's `TransportCallError` shape ×4; **warden is the outlier: ~20 modules import `subprocess` with no sole-site guard**; steward deliberately propagates raw `CalledProcessError`. |
| 3 | **Verdict / exit-code lattice** | 5 | warden's 7-rung lattice is documented canonical; doctor already self-describes as "a subset of `pyforge.warden`'s frozen `{0,1,2,130}`"; marshal, mason, steward redeclare. `130` is defined five times. |
| 4 | **Station roster** | 3–4 | `generate.py:621` + `PROJECT_SOURCES:45`, `herald/progress.py:56`, `Sidebar.jsx`. |
| 5 | **Report envelope** | 2 schemas + 2 `TOOL_NAME` consts | warden 22 KB vs doctor 4.5 KB JSON Schema for the same `{tool, status, exit_code, findings[]}` shape. |
| 6 | **`pixi.toml` parsing** | 2 | warden `extract/pixi.py` vs steward `provision.py`, same file. |
| 7 | **Base exception root** | 0 shared | herald and mason each invented one; warden/marshal/atlas scatter 12–13 `*Error` classes with no common root. |

**The consolidation case, stated carefully.** A small `pyforge-core` (or
`pyforge-kit`) package — atomic write, subprocess guard, verdict lattice
with per-station domain restriction, roster-as-data, one report-envelope
schema, one exception root — is a mechanical extraction with the copies
already self-documenting their sameness, and it has **three consumers
already scheduled**: genesis Epic 7 (stories 7.2/7.3 would otherwise mint
copies #6 and #21), the testing charter's unbuilt CAP-3
(`pyforge-testing-kit`), and the container's forcing function (§ 2). The
counterweight is the fleet's real doctrine: stations are independently
conda-installable and the two existing cross-deps are deliberately
env-level-optional — a shared package must be a leaf dependency (pure
stdlib, no station imports it *from* another station) or it becomes the
coupling the architecture has so far refused. Warden's ungated ~20-module
subprocess surface is the one item worth doing even if nothing else is:
it is a compliance tool whose own execution discipline is below the
fleet's floor.

**Sequencing recommendation (the doc's bottom line):**
1. Decide `pyforge-core` scope now, **before S-7.1 opens** (it changes two
   Epic-7 stories), folding it into the planning-chain pass the
   `genesis-installer-name-retirement` Dream already requires.
2. Extract in the order of the census (atomic write → verdict → subprocess
   guard), each with the sole-ownership meta-test pattern marshal/warden
   already use; retire the copies in the same story (the Atlas
   no-migration-step lesson, § 6).
3. Container (§ 2) after the extraction lands; live-UI mode (§ 3) only as a
   cache over the static generators; portability's next step (§ 4) is
   evidence rows, not new machinery.
