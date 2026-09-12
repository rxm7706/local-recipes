---
title: "Technical research — the BMAD estate as an agent knowledge surface (2026-09-12)"
chain: "bmad-suite-lifecycle"
created: "2026-09-12"
type: research
owner: steward
head: b978aa9b2a
---

# Technical research — the BMAD estate as an agent knowledge surface

**Trigger.** Operator request (2026-09-12): update `CLAUDE.md` and `AGENTS.md` so every
agent and session on this repo has a full understanding of BMAD-METHOD (bmadcode.com,
docs.bmad-method.org, github.com/bmad-code-org/BMAD-METHOD), the related tooling in
`OpenTeams-WFT-CDO/bmad-suite-package`, and how the Marshal station uses it today — with the
goal that any session can leverage the bmad-suite to build, operate and deploy with PyForge.

**Scope.** Two questions, kept apart: (1) *what is true* about the upstream ecosystem and about
this repo's use of it, and (2) *what actually reaches a session* when it starts. The first is
mostly already answered inside this repo; the second is where the gap is.

**Method.** Two independent read-only audits run in parallel, then re-verified by the
reviewing session: a repo inventory (install layer, the six bmad-suite specs, dreams, station
code for steward/doctor/marshal, pixi pins and tasks, detectors, root instruction files) and a
live upstream fetch (bmadcode.com, docs.bmad-method.org, the BMAD-METHOD repo/CHANGELOG/npm
registry, bmad-loop, the bmad-code-org org listing). Nothing was edited; `scripts/bmad-switch`
was not run; this file was written to its physical path.

**Not reachable.** `https://github.com/OpenTeams-WFT-CDO/bmad-suite-package` returns 404 to
an unauthenticated fetch, the org page shows no public repositories, the GitHub API is blocked
by the session proxy, and the session's `add_repo` refuses a cross-owner attach ("cross-tier
adds are not supported in v1"). Everything about that repo below is therefore inferred from
this repo's own artifacts (which package a 13-member "bmad-suite" onto the SelfExplainML /
PrivateChannel conda channel) and marked as such. See § 6, question 1.

## Verdict

1. **The repo already knows almost everything the operator asked for.** The 13 suite members,
   their install classes, wielding stations, provisioning paths, hazards, the nine-step
   release cadence, the sixteen upgrade traps, the customization inventory, and the
   marshal↔bmad-loop harness contract are all written down — in Tier-2 steward specs
   (`spec-bmad-suite-lifecycle`, `-channel-product`, `-metapackage`,
   `-install-class-wiring`, `spec-bmad-method-core-upgrade`, `spec-bmad-module-provisioning`),
   seventeen `docs/dreams/bmad-*.md` files, station code, and `_bmad/_config/bmad-help.csv`.
2. **Almost none of it reaches a session.** `CLAUDE.md` does not import `AGENTS.md`, so a
   Claude Code session never loads the verified `bmad:context` block (policy, gates,
   pitfalls). `CLAUDE.md` itself names no installed BMAD version, none of the suite
   apparatus (`steward suite` / `provision --module` / `upgrade bmad-core`, the cadence,
   the metapackage), and still leads its skill table with names retired in 6.11/6.12. The
   only machine-readable upstream docs snapshot (`.claude/docs/bmad-method-llms-full.txt`) is
   the 6.11-era file upstream stopped publishing.
3. **The fix is a knowledge-surface problem, not a research problem.** The recommended shape
   is (a) one *derived* catalog with a drift detector, modelled on
   `docs/reference/library-llms-full.md` + `llms-full-check`; (b) a load-path fix so the
   verified `AGENTS.md` block is what Claude Code reads; (c) a handful of surgical
   `CLAUDE.md` corrections. Under Dream-first, (a) and (b) enter through a Dream seed
   (draft in § 5); (c) is Quick-Flow maintenance.

## 1. Upstream facts (fetched 2026-09-12)

### 1.1 BMAD-METHOD

- Latest release **v6.12.0** (GitHub release 2026-09-04 02:31 UTC; CHANGELOG dated
  2026-09-03; npm 6.12.0 published 2026-09-04). npm dist-tags: `latest` 6.12.0, `next`
  6.12.1-next.0 (2026-09-05), `rollback` 4.39.0. **No 6.13.x, no 7.x.** Prior: 6.11.0
  (2026-08-09/10), 6.10.0 (2026-07-03).
- Install: `npx bmad-method install` (prerelease `npx bmad-method@next install`; headless
  `npx bmad-method install --yes --modules bmm --tools claude-code`). Prereqs: Node 20.12+,
  `uv` (required by `bmad-build` / `bmad-build-auto`), Git only for custom modules. Upgrade =
  rerun the installer from the directory holding `_bmad`. Also distributed as Claude Code /
  Codex plugins via `bmad-code-org/bmad-plugins` (`bmad-method` + `bmad-toolbox`).
- Modules on the Add-Modules page: `core` (always), `bmm` (bundled in `bmad-method`),
  `bmb` (npm `bmad-builder`), `cis` (npm `bmad-creative-intelligence-suite`), `gds` (npm
  `bmad-game-dev-studio`), `tea` (npm `bmad-method-test-architecture-enterprise`), plus
  `--custom-source`. **Skill Forge (skf) is third-party** (armelhbobdad), not bmad-code-org;
  utility-skills and labs are not modules on that page.
- Skill catalog 6.12: 8 core (`bmad-help`, `-advanced-elicitation`, `-review`, `-customize`,
  `-brainstorming`, `-deep-recon`, `-forge-idea`, `-party-mode`); 16 BMM workflow skills
  (`-product-brief`, `-prfaq`, `-prd`, `-spec`, `-ux`, `-architecture`,
  `-create-epics-and-stories`, `-sprint-planning`, `-correct-course`, `-project-context`,
  `-build`, `-build-auto`, `-code-review`, `-walkthrough`, `-qa-generate-e2e-tests`,
  `-retrospective`); 5 personas (Mary/John/Winston/Amelia/Sally). Old IDs forward.
- Three planning paths (`/plan/choose-a-planning-path/`): **Quick Flow** (obvious low-risk
  edit → `bmad-build`, no planning), **Spec-First** (`bmad-spec` → `stories.yaml` →
  `bmad-build` per story → `bmad-retrospective`), **Full Chain** (brief/PRD/UX/architecture →
  `bmad-spec` per epic → epics+stories → sprint planning → build).
- Customization: per-skill `_bmad/custom/<skill>.user.toml` > `_bmad/custom/<skill>.toml` >
  the skill's shipped `customize.toml`; central config `_bmad/custom/config.user.toml` >
  `_bmad/custom/config.toml` > `_bmad/config.user.toml` > `_bmad/config.toml`. Tables
  deep-merge, keyed arrays merge by `code`/`id`, "an override cannot delete a base item".
  Scripts: `_bmad/scripts/render_skill.py`, `resolve_customization.py`. There is **no
  sanctioned way to patch a skill's step-file prose** (this repo's
  `.claude/docs/bmad-skill-customization-mechanics.md`, 2026-09-10).
- `bmad-project-context` (replaces `bmad-document-project` + `bmad-generate-project-context`)
  writes a small verified block between XML markers in `AGENTS.md`; intents Setup / Adopt /
  Refresh / Record / Audit; never commits; 6.12 adopts a handwritten `AGENTS.md` instead of
  rewriting it. Its Adoption flow explicitly proposes "a `CLAUDE.md` reduced to `@AGENTS.md`".
- **`llms.txt` / `llms-full.txt` are no longer published** (6.12.0 CHANGELOG;
  `docs.bmad-method.org/llms.txt` → 404).
- 6.12 integrator notes: `bmad-checkpoint-preview` → `bmad-walkthrough`; shims opt-in on
  fresh installs (`--shims`); `persistent_facts` ships empty; `{diff_output}` → `{diff_file}`;
  Build no longer auto-triggers on interactive edits / git bookkeeping / formatting.
- 6.11 integrator notes: `bmad-quick-dev` → `bmad-build`, `bmad-dev-auto` → `bmad-build-auto`;
  `bmad-create-story` / `bmad-dev-story` → `v6-shims/` ("removal rides the v7 cut"); three
  research skills → `bmad-deep-recon`; six review skills → `bmad-review` lenses;
  `bmad-sprint-status` → `bmad-sprint-planning`; `bmad-check-implementation-readiness`
  removed; Paige (tech-writer) retired; layered TOML config introduced ("the migration, not
  the cutover" — `_bmad/bmm/config.yaml` still ships); renderers halt on missing keys; every
  script runs via `uv run`.
- Not found upstream: any sentence about `bmad-index-docs` removal (asserted in `CLAUDE.md`);
  a standalone v7 roadmap page.

### 1.2 bmad-loop

- bmad-code-org, MIT, Python 3.11+, "early open beta". Latest **v0.11.1** (2026-08-24);
  v0.11.0 (08-19); v0.10.0 (08-14). **Not on PyPI or npm**: `uv tool install
  "bmad-loop[tui] @ git+https://github.com/bmad-code-org/bmad-loop.git@v<tag>"`.
- Profiles `claude` (default), `codex`, `gemini`, `copilot`, `antigravity`, `opencode-http`
  via custom; per-stage `[adapter.dev|review|triage]`; out-of-tree adapter classes since
  0.10.0. Policy in `.bmad-loop/policy.toml`. Subcommands: `init validate run sweep resume
  resolve list status stop delete archive cleanup clean tui attach mux adapters decisions
  confirm diagnose probe-adapter relay`. Needs git 2.34+, tmux 3.2+, Linux/macOS/WSL.
- Drives `bmad-build-auto` plus review lenses; bundles `bmad-loop-setup` / `-resolve` /
  `-sweep`. v0.8.0 renamed `bmad-auto` → `bmad-loop`; BMAD 6.10 made it a selectable module.

### 1.3 bmadcode.com and the org

- bmadcode.com = BMad Code, LLC: The Method (free, MIT), Consulting, Certification ("coming
  soon"); no courses; links to the repo, docs, Discord, YouTube, blog.bmadcode.com. Blog
  2026-07-04 "BMad Method Has Three Flows Now" (Full / Quick Dev / Loop; the
  create/dev/review-story split "folded into this single dev-agent shape for v7").
- bmad-code-org repos (18): BMAD-METHOD, bmad-loop, bmad-builder, bmad-method-test-architecture-
  enterprise, bmad-module-creative-intelligence-suite, bmad-module-game-dev-studio,
  bmad-eval-quality (Apache-2.0; `compile/seal/preflight/score`), bmad-utility-skills (not on
  npm; `/plugin marketplace add`), bmad-plugins, bmad-plugins-marketplace, bmad-manticore
  (v3.0.0), bmad-method-ui, bmad-method-wds-expansion (deprecated → `bmad-ux`),
  bmad-module-template, bmad-method-sample-data, cis-skills (test mirror), bmad-automator
  (archived), `.github`.
- npm: `bmad-builder` 1.1.0 and `bmad-creative-intelligence-suite` 0.1.9 are **stale on npm**
  vs GitHub tags 2.2.2 / 0.3.2 — GitHub is the channel of record for both (matches this
  repo's `install-matrix.md` hazards). TEA npm latest 1.26.0.

### 1.4 `OpenTeams-WFT-CDO/bmad-suite-package` — inaccessible; what this repo implies

**Operator confirmation (2026-09-12, same day).** The operator pasted the suite's population
verbatim; it is byte-identical to `recipes/bmad-suite/suite-members.yaml` at `b978aa9b2a`:
the 13 active members listed in § 2.2 plus four `deprecated: true` rows
(`bmad-method-wds-expansion`, `bmad-autopilot`, `bmad-dashboard-extension`, `bmalph`) and
one retired-without-recipe note (`bmad-story-automator`, deleted 2026-08-21). The manifest's
own `bmad-eval-quality` note ("tag-sourced since 1.3.0, 2026-09-09 — left the 0.2.0.dev0
commit pin per CFE G109") confirms § 3.6: the adoption-register row is the stale one.
What remains unverified about the OpenTeams repo is only its role (publishing home vs
mirror) and its own layout — § 6 Q1 narrows to that.


Everything in this repo treats "bmad-suite" as **13 conda packages on the SelfExplainML /
"PrivateChannel" channel**, recipe-built from `recipes/bmad-*` here, plus a `bmad-suite`
noarch metapackage (`recipes/bmad-suite/`, CalVer `2026.9.11`, manifest
`suite-members.yaml`). The most likely reading is that the OpenTeams repo is the
channel-side packaging/publishing home (or a downstream mirror) of those same recipes. That
is an inference, not a verified fact — § 6 Q1.

## 2. How this repo wields BMAD today (verified against `b978aa9b2a`)

### 2.1 Install layer

- `_bmad/_config/manifest.yaml`: core 6.12.0, bmm 6.12.0, skf `main`/custom
  (armelhbobdad, channel `next`), `installShims: false`, `ides: [claude-code]`;
  `skf-manifest.yaml` 2.1.0 (2026-09-07).
- `.claude/skills/`: **127** skill dirs — `bmad-agent-*` 14, `skf-*` 16, `bmad-cis-*` 10,
  `bmad-os-*` 10, `bmad-testarch-*` 8, `bmad-loop-*` 3, `bmad-bmb-setup`, the 8 core + 16
  BMM skills, the four labs consent skills, the seven `pyforge-*` station skills. Both
  `v6-shims/` dirs hold only a README; every retired shim dir is absent.
- Config: installer `_bmad/config.toml` (read-only), `_bmad/custom/config.toml` (team pins:
  `[core] communication_language`, `[modules.bmm] user_skill_level`, `[modules.skf]`,
  steward-written `[modules.utility-skills|tea|labs]`), `_bmad/config.yaml` (steward's
  non-installer module registry: cis, bmb), per-project
  `_bmad-output/projects/<slug>/.bmad-config[.user].toml` (six-layer merge, repo extension
  C1 in `resolve_config.py`).
- `_bmad/scripts/`: `render_skill.py`, `resolve_config.py` (repo-customized), 
  `resolve_customization.py`, `memlog.py`, `config_utils.py`, `bmad_tea_playwright.py`
  (slated for retirement under CAP-4 TEA adoption).

### 2.2 The 13 members (adoption register, condensed)

| Member | Class | Verdict / wielder | Provisioning |
|---|---|---|---|
| bmad-method 6.12.0 | installer-tree | substrate, all stations | `steward upgrade bmad-core` |
| bmad-loop 0.11.1 | runner-home | marshal wraps, never absorbs | `marshal init <slug>` (runner report-only in steward) |
| bmad-module-skill-forge 2.1.0 | own-installer | all stations (16 `skf-*`) | its own installer; `--module skf` refused |
| bmad-creative-intelligence-suite 0.3.2 | module | herald, scribe | `steward provision --module cis` |
| bmad-eval-quality (pixi ≥1.4.1) | cli | warden, marshal (pilot) | pixi pin + 3 `eval-quality-*` tasks |
| bmad-method-test-architecture-enterprise (pixi ≥1.26.0) | module | marshal, warden — full adoption | `steward provision --module tea` |
| bmad-builder 2.2.2 | module | steward, mason — beside skf | `steward provision --module bmb` (never `--legacy-dir`, never `cleanup-legacy.py`) |
| bmad-utility-skills 2.0.0 | module | six stations (`bmad-os-*`) | `steward provision --module utility-skills` |
| bmad-manticore 3.1.0.dev0 | studio module | herald (dedicated studio) | `npx bmad-method install --directory $PYFORGE_STUDIO_ROOT --custom-source …` |
| bmad-labs-skills 1.0.0.dev0 | plugin-path (consent) | 4 skills, 4 stations | `steward provision --plugin labs --skill <name>` |
| bmad-module-template 0.1.0 | scaffold | skip (catalog row) | — |
| bmad-dashboard 1.2.2.dev0 | vscode-extension | marshal, opt-in | `bmad-dashboard-install` task |
| mybmad-dashboard 0.1.0.dev0 | web app | skip (operator view) | `mybmad` (env `bmad-ui`) |

Source of record: `spec-bmad-suite-lifecycle/adoption-register.md` (AD-2 — the one durable
home; routing restated only in each `bmad-agent-<station>` persona skill). Deprecated catalog
rows: wds-expansion, bmad-autopilot, bmad-dashboard-extension, bmalph.

### 2.3 Station roles

- **Steward** owns the estate: `steward suite pipeline-truth` (13/13, six stages recipe →
  channel → installed → wired → native, fail-open probes) and `suite advance --package`
  (autotick → build → test → publish → listing → reviewable PR, never auto-merged);
  `steward provision --list | --list-modules | --module {bmb,tea,cis,utility-skills,manticore}
  | --plugin labs --skill <name> | --prove-class-path`; `steward upgrade bmad-core --target
  <v> [--apply --branch … --no-shims] | pin-fan-out | prove-landed | verify`. Code:
  `src/shared/packages/pyforge-steward/src/pyforge/steward/{suite,suite_advance,provision,upgrade}.py`.
- **Doctor** detects, never gates: `bmad-method-version-drift` (pixi floor vs manifest),
  `bmad-method-upstream-drift` (installed vs npm), `bmad-channel-drift`,
  `bmad-recipe-upstream-drift`, `bmad-suite-upstream-drift` (roster-derived from
  `suite-members.yaml`, GitHub-release fallback for npm-invisible members); plus the
  marshal factory-doc drift (`bmad-drift-check`, 18 finding kinds) and
  `bmad-render-config-ambiguity-check`.
- **Marshal** wraps bmad-loop through exactly one module,
  `adapters/harness_bmadloop.py` (import-linter enforced), rendering `.bmad-loop/policy.toml`
  as a derived gitignored artifact from a four-layer policy fold (`DEFAULT_POLICY` →
  `_bmad-output/policy-defaults.toml` → `marshal-policy.toml` → `--set`; closed 34-key
  schema `policy.json`). Harness range `>=0.11.0,<0.12`. `[dev] skill = "bmad-dev-auto"` is a
  **permanent adapter discriminator**, never the invoked skill name. Marshal verbs:
  `adapters benchmark chain check checkpoint config context deploy dispatch gate init land
  planning refresh retire seed spin status upstream`.
- **Mason** refreshes the suite recipes (`generate-bmad-suite`, `build-bmad-suite`).
  **Herald / Scribe / Warden / Atlas** wield adopted skills per the register.

### 2.4 The release cadence (CAP-8, `release-cadence.md`)

Trigger: `bmad-method-version-drift-check` warns or `pipeline-truth` names a member behind →
(1) doctor detect → (2) steward catalog from the unpacked conda package → (3) pre-flight
report-only → (4) `upgrade bmad-core --apply --branch steward/bmad-core-upgrade-<v>` →
(5) `prove-landed` (8 loop homes) → (6) marshal era round → (7) mason suite refresh →
(8) steward status flips → (9) record traps. The `@next` rehearsal is fixture proof, not
live proof (2026-09-10).

### 2.5 Where the knowledge lives today

| Layer | Loaded at session start? | Currency |
|---|---|---|
| `CLAUDE.md` (46 KB) + `@.claude/memory/MEMORY.md` | **yes** (Claude Code) | hand-maintained; stale in places (§ 3) |
| `AGENTS.md` verified block (26 KB file) | **no** for Claude Code; yes for Codex/Devin; Copilot/Gemini/Cursor point at it | verified 2026-09-06 |
| `_bmad/_config/bmad-help.csv` (45 rows) | on demand via `bmad-help` | installer-generated, current |
| Steward specs + companions | on demand | current, detailed |
| `docs/dreams/bmad-*.md` (17) | on demand | current |
| `.claude/docs/bmad-method-llms-full.txt` (257 KB) | on demand | **6.11-era, discontinued** |
| `.claude/docs/bmad-skill-customization-mechanics.md` | on demand | 2026-09-10 |
| `docs/reference/library-llms-full.md` | on demand, detector-guarded | pins current |
| Prior research (`technical-bmad-ecosystem-verification-research-2026-07-31.md`) | on demand | July; superseded here |

## 3. Gap analysis — what a session actually gets

1. **Load path.** `CLAUDE.md` has no `@AGENTS.md` import; the verified block (policy, gates,
   pitfalls incl. the shim/`DevPolicy.skill`/config-pin traps) never enters a Claude Code
   session. Two live contradictions follow: `AGENTS.md` says "commit messages carry no
   Co-Authored-By line"; `CLAUDE.md` is silent, so the harness default applies. The SKF
   block is duplicated verbatim in both files (paid twice where both load).
2. **Stale skill names in `CLAUDE.md`.** The Skill Reference (lines ~140–145, ~219) leads
   with `bmad-quick-dev`, `bmad-dev-auto`, `bmad-create-prd/-architecture/-story`,
   `bmad-dev-story`, `bmad-document-project`, `bmad-generate-project-context` — all absent
   from disk (`installShims: false`), deliberately hidden from `governance-currency` by
   ignore markers. `open-items-register.md` row "AGENTS.md shim pitfall line" is still `S`.
3. **No installed-version statement anywhere agent-facing.** `CLAUDE.md` never says "core
   is 6.12.0"; `EXEMPLAR-STANDARD.md` says "≥ 6.12"; `PROJECTS.md` says "≥ 6.10".
4. **The suite apparatus is invisible.** Zero hits in `CLAUDE.md` for `bmad-suite`,
   `adoption-register`, `release-cadence`, `steward suite`, `provision --module`,
   `upgrade bmad-core`, the metapackage, the studio. `AGENTS.md` carries one pointer line
   (by CAP-3 design for routing) but no verbs, and its "Running and verifying" list omits
   `bmad-method-version-drift-check`, `bmad-drift-check`, `tea-test-review`.
5. **No current machine-readable upstream reference.** Upstream discontinued llms-full; the
   local snapshot is a version behind; the docs are task-organised HTML only.
6. **Pin/register disagreements** (a currency smell, not a break): TEA 1.24.0 (register,
   matrix) vs 1.25.0 (channel-product SPEC frontmatter, citing a wrong line) vs
   `pixi.toml` ≥1.26.0; eval-quality "0.2.0.dev0 @3172162f, commit pin load-bearing"
   (register) vs "commit pin retired" (matrix) vs `pixi.toml` ≥1.4.1; `bmad-suite` ≥2026.9.5
   (pixi) vs 2026.9.11 (recipe).
7. **Station skill under-documents steward.** `.claude/skills/pyforge-steward/.../SKILL.md`
   omits `upgrade` and lists `suite` bare; the skill was forged before Epics 14/15/31/39/46.
8. **Small doc debris.** Two manticore-studio docs (`docs/reference/` and `docs/how-to/`);
   `PROJECTS.md` names `docs/governance/spec-pyforge-genesis/`, which does not exist.
9. **Cutover-readiness residue** the root files never mention: P7 violated (customization
   pool 11), P13 four ungoverned installer-owned edits, marshal 31.4/31.5 and steward 46.10
   open; `spec-bmad-method-core-upgrade` holds `in-progress` until the *next* upstream
   release applies cleanly.

## 4. Options

Non-options first: copying upstream docs into `CLAUDE.md` (46 KB is already ~12k tokens per
session; the whole 6.12 skill catalog is discoverable under `.claude/skills/` and
`bmad-help.csv`); hand-maintaining a member/version table in `CLAUDE.md` (it would be the
fourth place the same numbers drift, see § 3.6).

**A. A derived "BMAD estate" catalog with a drift detector — recommended.**
`docs/reference/bmad-estate-llms-full.md`, generated (not hand-written) from live sources:
`_bmad/_config/manifest.yaml` + `skf-manifest.yaml` (installed core/modules), the frontmatter
`description:` of every `.claude/skills/*/SKILL.md` (the 127-dir catalog by family),
`_bmad/_config/bmad-help.csv` (phase/sequence), `recipes/bmad-suite/suite-members.yaml` +
`steward suite pipeline-truth --json` (13 members, six stages), `adoption-register.md` § 1–2
(verdict, wielder, provisioning path, hazards), the marshal harness constants
(`HARNESS_VERSION_RANGE_TEXT`, policy keys), and the release-cadence step list. One
detector (`bmad-estate-check`, mirroring `llms-full-check`) exits non-zero when any of those
sources moves. Referenced by **one line** each in `CLAUDE.md` and `AGENTS.md`
(`governance-currency` then guarantees the path resolves). This is the "llms-full for this
repo's BMAD" that upstream stopped shipping, scoped to what is actually installed and wired
here. Effort: one spec, roughly three stories (generator, detector, first render + root
pointers).

**B. Fix the load path via `bmad-project-context` (adopt/refresh) — recommended, operator-
driven.** Upstream's own Adoption flow reduces `CLAUDE.md` to `@AGENTS.md` after verifying
the import for every harness in use; each existing `CLAUDE.md` instruction is ledgered
(retain / rewrite / relocate / delete) with the operator approving every write. Outcome: one
loaded rulebook, the verified block reaches Claude Code, the duplicated SKF block is kept
once, the attribution contradiction is settled. The conda-forge-expert lifecycle and the
multi-project switch text can stay in `CLAUDE.md` outside the import if the operator prefers
a Claude-specific tail. Effort: one interactive session; no code.

**C. Surgical `CLAUDE.md` corrections now (Quick Flow, `maintenance` label).** Replace the
retired shim names with the 6.12 names (keep one dated "renamed in 6.11/6.12" note inside the
existing ignore markers); state the installed core version once with a pointer to the
manifest; add the three missing detector names to the verify list. Reversible, low-risk,
does not need a Dream.

**D. Re-forge `pyforge-steward`'s SKF skill** (`skf-update-skill`) so `steward suite` /
`upgrade` verbs and the release cadence are in the station skill that agents are told to
read first. Steward-owned; one story.

**E. Per-tool pointers.** `GEMINI.md`, `.cursor/rules/specs.mdc`,
`.github/copilot-instructions.md` already point at `AGENTS.md`; after B they need no change.
If A lands, add its one-line pointer to each.

Recommended order: **C** (today, trivial) → **B** (one operator session) → **A + D** (one
Dream, one spec, ~4 stories, Marshal-drainable).

## 5. Proposed Dream seed (draft — not minted; needs owner decision, § 6 Q2)

```markdown
---
title: Every session knows the BMAD estate it stands on
type: dream
owner: scribe        # recommended — knowledge surfaces; steward supplies the facts
status: dreamt
---

# Every session knows the BMAD estate it stands on

## The Dream
Any agent that opens this repo — Claude Code, Cursor, Copilot, Codex, a bmad-loop
session — starts with one current, derived picture of the BMAD estate: which core and
modules are installed, which of the thirteen bmad-suite members are wielded and by whom,
how a member is provisioned, how a release rolls through the fleet, and how Marshal
drives bmad-loop. It never reads a retired skill name, a stale version, or a table that
is hand-maintained in four places.

## Grounding
Research 2026-09-12: `_bmad-output/projects/pyforge-steward/planning-artifacts/research/
technical-bmad-suite-lifecycle-agent-knowledge-surface-research-2026-09-12.md` (§ 3 is the
gap list; § 4 A/B/D the shape).

## What it looks like when real
- `docs/reference/bmad-estate-llms-full.md` is generated from the manifest, the skill
  frontmatter, `bmad-help.csv`, `suite-members.yaml`, `pipeline-truth --json`, the
  adoption register and the marshal harness constants; `bmad-estate-check` fails on drift.
- `CLAUDE.md` loads the verified `AGENTS.md` block (`bmad-project-context` adoption); each
  root file carries one pointer line to the catalog.
- The `pyforge-steward` station skill names its `suite` and `upgrade` verbs.

## Kinships
[[bmad-suite-lifecycle]] (the register is the source of record) ·
[[bmad-method-core-upgrade]] (the cadence) · [[bmad-611-era-alignment]] (retired names) ·
[[pyforge-scribe]] (knowledge surfaces) · [[pyforge-marshal]] (AGENTS.md family via genesis)
```

## 6. Open questions for the operator

1. **Role of `OpenTeams-WFT-CDO/bmad-suite-package`** — population confirmed (§ 1.4); still
   open: is it the channel-side publishing home of these 13 recipes, a mirror of
   `recipes/bmad-*`, or the consumer-facing install/README package? To read it from a session
   it must be the session's initial source (cross-owner attach is refused).
2. **Who owns the Dream in § 5** — scribe (knowledge surface; recommended), steward (owns
   the facts and the register), or marshal (owns the AGENTS.md family through genesis)?
3. **Load path (option B):** fold `CLAUDE.md` into the `AGENTS.md` block via
   `bmad-project-context` adoption (recommended), or only add `@AGENTS.md` and dedupe by
   hand, or keep them separate?
4. **Catalog shape (option A):** a new `bmad-estate-llms-full.md` with its own detector
   (recommended), or a section inside `library-llms-full.md`, or rely on pointers to
   `bmad-help.csv` + the adoption register only?
5. **May the option-C corrections land now** as a `maintenance`-labelled PR, ahead of the
   Dream?
6. **Attribution rule:** `AGENTS.md` forbids `Co-Authored-By` lines; the Claude Code harness
   adds them by default. Confirm the `AGENTS.md` rule is the intended one (this research
   commit follows it).

## 7. Sources

Upstream (fetched 2026-09-12): https://bmadcode.com/ · https://docs.bmad-method.org/ ·
https://docs.bmad-method.org/start/install-bmad/ · https://docs.bmad-method.org/customize/customize-bmad/ ·
https://docs.bmad-method.org/customize/add-modules/ · https://docs.bmad-method.org/reference/skills-and-agents/ ·
https://docs.bmad-method.org/plan/choose-a-planning-path/ ·
https://docs.bmad-method.org/existing-codebases/set-and-maintain-project-context/ ·
https://docs.bmad-method.org/build/autonomous-development-loops/ ·
https://github.com/bmad-code-org/BMAD-METHOD (releases, CHANGELOG.md, README.md) ·
https://registry.npmjs.org/bmad-method · https://github.com/bmad-code-org/bmad-loop (README, releases) ·
https://github.com/orgs/bmad-code-org/repositories · https://raw.githubusercontent.com/bmad-code-org/bmad-utility-skills/main/README.md ·
https://blog.bmadcode.com/bmad-method-has-three-flows-now-heres-what-actually-changes-between-them/

Repo (at `b978aa9b2a`): `_bmad/_config/manifest.yaml`, `_bmad/custom/config.toml`,
`_bmad/config.yaml`, `_bmad/_config/bmad-help.csv`, `recipes/bmad-suite/{recipe.yaml,suite-members.yaml}`,
`pixi.toml` (bmad pins :41, :1677–1691, :1922, :2000; tasks :919–1117, :1337–1342),
`_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/{SPEC.md,adoption-register.md,release-cadence.md,open-items-register.md,cutover-readiness.md}`,
`…/spec-bmad-suite-channel-product/{SPEC.md,install-matrix.md}`, `…/spec-bmad-method-core-upgrade/{SPEC.md,failure-modes.md,customization-inventory.md}`,
`…/spec-bmad-suite-install-class-wiring/SPEC.md`, `docs/dreams/bmad-*.md`,
`src/shared/packages/pyforge-steward/src/pyforge/steward/{cli,suite,suite_advance,provision,upgrade}.py`,
`src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/{bmad_method,factory}.py`,
`src/shared/packages/pyforge-marshal/src/pyforge/marshal/{adapters/harness_bmadloop.py,core/policy.py,schemas/policy.json}`,
`.claude/skills/{pyforge-steward,pyforge-marshal,bmad-agent-steward,bmad-agent-marshal,bmad-project-context,bmad-help}/**/SKILL.md`,
`.claude/docs/bmad-skill-customization-mechanics.md`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`,
`.cursor/rules/specs.mdc`, `.github/copilot-instructions.md`, `_bmad-output/PROJECTS.md`,
`_bmad-output/EXEMPLAR-STANDARD.md`, `docs/reference/library-llms-full.md`, `docs/MAP.md`.
