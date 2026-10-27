---
title: Mason — forge the blocks, bind the environment, ship the structure
type: dream
owner: mason
status: specified
---


# Mason — the craft of shipping, made a command

## The Dream

The Artisan Builder's dream: **packaging stops being archaeology and becomes a
craft anyone can command.** Atlas maps the terrain, Warden clears the perimeter —
then Mason takes raw ingredients and binds them into structures that install
correctly on every platform a user might bring. Recipes authored, environments
resolved into strict lockfiles, wheels and conda packages shipped from one pass.
A human states intent; Mason handles syntax, selectors, pins, and the hundred
gotchas that turn an afternoon into a week.

The station exists because *the hand that builds must not be the gate that
judges*: Mason ships, Warden decides whether shipping was allowed.

## What it looks like when real

```bash
mason recipe build ./recipes/recipe.yaml      # author + build a v1 conda recipe
mason package ship --to pypi,conda-forge      # one pass, both ecosystems
mason environment lock                        # conflicting worlds -> one lockfile
```

- **dist** `pyforge-mason` · **module** `pyforge.mason` · **CLI** `mason` — the
  Smith's craft as an installable product, mirroring the Warden pattern.
- **The seam is by capability** (D-1, "Option C"): `mason recipe` **wraps** the
  conda-forge-expert craft by subprocess through a single port (`cfe.py`) — the
  skill stays canonical for recipe semantics and keeps improving through the
  Rule-2 retro loop — while `package` (build + ship to PyPI/channel/conda-forge)
  and `environment` (lockfile binding) are **built natively**, because no
  wheel-build, upload path, or lock orchestration exists anywhere in the wrapped
  machinery to wrap.
- **Never fork the craft.** A fork is structurally adversarial: Rule 2 mandates
  that every conda-forge effort *edits the skill*, so a fork is invalidated by
  the loop that governs its own domain. The in-repo cautionary precedent is
  [[pyforge-atlas]], which chose full rebuild and whose legacy orchestrator is
  still the live runtime. Mason's own **Epic 5** exists to prove the seam holds
  with tests, not documentation — a knowledge deny-list with planted-violation
  fixtures, a sole-caller test, a CFE-independence allow-list of exactly one
  entry, and a closing Rule-2 retrospective are all specced, not yet built.

## What is real

- **Updated 2026-09-12 (superseding the 2026-09-11 snapshot below, which
  itself superseded the original Epic-1-only snapshot).** 67 of 67 tracked
  stories shipped across all 16 epics, per `fleet-picture` (mason reads
  `complete`) — the installable shell, its output contract, the full recipe
  lifecycle, the dual-ship motion, environment locking, and the
  CFE-independence seam (Epic 5) are all built; the scope also grew past the
  original 5 epics / 38 stories as later work (the recipe-build MCP surface,
  the CLI⇄tool parity gate, the CFE rebuild-campaign retirement, and more)
  was decomposed in. See `spec-pyforge-mason` and `sprint-status-ledger.yaml`
  directly for the current story-by-story state rather than this bullet.
- Superseded reading, kept for the record: *"66 of 67 tracked stories shipped
  across 15 of 16 epics (2026-09-11) — the installable shell, its output
  contract, the full recipe lifecycle, the dual-ship motion, environment
  locking, and the CFE-independence seam (Epic 5) are all built."* The one
  remaining story (15.1, closing the CFE rebuild-campaign mirrors) shipped
  2026-09-12.
- Superseded reading, kept for the record: *"4 of 38 stories shipped (~11%),
  all in Epic 1 (`S-1.1` workspace-member scaffold and dual-artifact build,
  `S-1.2` CLI noun-verb structure and global flags, `S-1.3` error taxonomy and
  exit-code contract, `S-1.4` dual output format with stream discipline)...
  Epics 2–5 — the whole recipe lifecycle, the dual-ship motion, environment
  locking, and the seam proof — have not started."*
- Full planning chain landed 2026-07-25: brief → PRD (50 FRs / 16 NFRs / 13
  D-records) → architecture (16 ADs) → epics (5 epics / 38 stories). Spec:
  `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md`.
- **2026-08-02** — a same-day sibling Dream,
  [[pyforge-mason-recipe-validator]], proposed a native ~50-rule linting engine
  inside Mason. It was retired the day it was created: D-1 had already decided
  this exact question (wrap, don't fork), and Mason's own Story 2.5/2.8 already
  cover CFE-verbatim validate/optimize/scan. No scope was lost — the seam
  decision just held under a direct test.

## Related but out of scope

Mason is also the station registered to eventually repackage
[[presenton-pixi-image]] (an air-gapped, conda-native rebuild of the Presenton
AI deck-generation app for OpenShift) — that Dream stays archived separately
(blocked on its own unresolved Phase-0 decision gate) and shares no
architecture, code, or timeline with the `mason` CLI described above. **This
Dream-level narrative is the only thing that stays separate** — as of
2026-08-02, `presenton-pixi-image`'s brief/PRD/architecture/Spec were
consolidated into this station's own single planning-chain documents (each
carries a "Satellite: Presenton" section) per explicit user override of the
earlier separation decision; the Dream itself, its epics, and its
blocked-status were deliberately left untouched. See
`archive/docs/dreams/presenton-pixi-image.md` for the full account.

## The frontier

- Epics 2–5 of the `mason` CLI: the recipe lifecycle through Mason's verbs,
  the dual-ship motion (PyPI + conda channel + conda-forge in one command),
  environment lockfile binding, and the seam-holds proof + closing retro.
- Multi-ecosystem autotick + scaffolders (CRAN/npm/cargo) — explicitly out of
  v1 (PRD non-goals); the factory is still Python-first
  ([[packaging-factory]]'s standing frontier).
- The smart test extractor; the static dependency-version checker — named in
  the origin Dream, deferred past v1.
- The standalone question: `mason recipe` is inert without a co-located craft
  root — bought deliberately, in exchange for zero knowledge duplication.
- **Mason ships Mason** (Story 3.8) is the success signal's master switch: not
  reachable until Epic 3 lands.

## Kinships

[[pyforge-charter]] (§5, the station's charter) · [[packaging-factory]] (the
practice he tends) · [[pyforge-atlas]] (maps before he builds; the rebuild
cautionary tale) · [[pyforge-warden]] (judges what he ships) ·
[[fleet-stewardship]] (the estate, tended with Doctor) ·
[[enterprise-airgap]] (every artifact must resolve behind a firewall) ·
**steward Epic 44** (the python-foundry cutover carries two of Mason's own capabilities:
`fnd:CAP-3` → S-44.6 *"CFE comes home"* and `fnd:CAP-6` → S-44.9 *"Mason submits to
conda-forge"* — both carry Mason's Rule 1/2 ACs, both read `blocked`, and mason's chain
has no counterpart story for either; noted 2026-09-09, decision-batch D11).

## Realization log

- **2026-07-25** — persona Dream authored, closing the last asymmetry among the
  eight Smiths: Mason was the only station whose charter lived inside a practice
  Dream. Grounded in the planning chain landed the same day (research → brief →
  PRD → architecture → 5 epics / 38 stories) and its D-1 seam decision.
- **2026-08-02** — first implementation slice shipped: Epic 1 Stories 1.1–1.4
  (workspace scaffold, CLI shell, error taxonomy, output contract) — 4/38
  stories done. Same day, the [[pyforge-mason-recipe-validator]] sibling Dream
  was authored and retired as a direct conflict with D-1, and
  [[presenton-pixi-image]] was archived separately (blocked, not absorbed —
  it is genuinely unrelated subject matter to this Dream). Dream refreshed to
  current state.
- **2026-08-26** — **realized.** The station is complete per the fleet ledger
  (2026-08-21): all 50 stories across 11 epics `done` — the backlog grew past
  the original 5/38 through Epics 6–11 (CFE-rebuild pilot + re-scope gate,
  machine-checked recipe knowledge, pixi base-layer convention, external
  integration seams, the build-engine hook, and the station persona +
  `/stations/mason/` portal slice, the last landing 2026-08-25/26). The three
  verb families exist as dreamed (`recipe` ×8 wrapped through the one CFE port,
  `package build/ship` with asymmetric receipts, `environment lock/check`), the
  seam-holds proof suite is green, and "Mason ships Mason" is proven at the
  dry-run/TestPyPI-rehearsal tier. The 2026-08-02 "What is real" snapshot above
  (4/38, Epics 2–5 not started) is superseded by this entry. Close-out retro:
  `_bmad-output/projects/pyforge-mason/planning-artifacts/retros/retro-pyforge-mason-2026-08-26.md`;
  as-built truth-ups landed the same day in the Spec/PRD/architecture-spine/brief
  § Currency reconciliation sections. With this flip the chain-layers audit's
  `behind-code` flag for mason is suppressed **by design** — the chain is no
  longer being built; the artifacts are maintained as the as-built record.

- **2026-09-09 (realization-gate re-read)** — `realized` is **retained**, with a caveat. The CLI
  shell, the seam-holds proof suite and the `/stations/mason/` portal all genuinely run. Two
  claims in the 2026-08-26 entry do **not** hold under the exercised-in-the-estate gate
  (operator ruling,
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`
  § 2.2 row **mason-B5**): (1) the **`recipe` verb family is unavailable in mason's own pixi
  env** — `mason doctor` reports `unavailable_verbs: ('recipe',)` and
  `cfe_import_floor_missing: ('truststore', 'conda-forge-metadata')`, because
  `[feature.pyforge-mason.dependencies]` (`pixi.toml:281-283`) declares neither package while
  `cfe.py:180-186`'s `CFE_IMPORT_FLOOR` requires both; CAP-5's graceful degradation is working
  exactly as designed, but CAP-2 — the station's differentiator — is unexercised in the estate
  that built it. (2) **Nothing in the estate routes through `mason recipe`** — one comment at
  `pixi.toml:797`, zero call sites; all recipe work still goes through
  `pixi run -e local-recipes recipe-build`. "Mason ships Mason" remains **rehearsal-tier**: there
  is no `recipes/pyforge-mason` recipe and no public publish. Two effect stories were minted on
  mason's own epics to close the loop — **Story 16.1** (mason's env satisfies the CFE import
  floor) and **Story 16.2** (a first estate caller of `mason recipe`, outside mason's own test
  tree). Separately, the two Mason capabilities that live on steward's chain —
  **S-44.6** (`fnd:CAP-3`, "CFE comes home") and **S-44.9** (`fnd:CAP-6`, "Mason submits to
  conda-forge") — both carry Mason Rule 1/2 ACs and read `blocked` in steward's ledger; they are
  now named in Kinships above so mason's decomposition is not silently incomplete against the
  greenfield spine.
- **2026-09-27 (night) — Proposed: the recipe CI picks changed recipes from the remote-tracking
  ref.** The four recipe build workflows (`.github/workflows/test-{all,linux,macos,windows}.yml`)
  choose which recipes to build with `git diff --name-only origin/${{ github.base_ref }}...HEAD --
  'recipes/*'`. Their checkout fetches tags (`fetch-depth: 0`), so a pushed tag named `origin/main`
  wins over `refs/remotes/origin/main` and the changed-recipe set would come out empty. The branch is
  dormant today — no recipe workflow runs on `pull_request` (`test-all` is dispatch-only and calls the
  other three) — so this is hardening, found by doctor Story 32.1 fixing the coverage gate's identical base
  (`DW-mason-recipe-ci-short-base-ref-2026-09-27`). **What it looks like when real:** all four diff
  from `refs/remotes/origin/${{ github.base_ref }}`; a stray ref changes no recipe selection.
  **Constraints:** the manual `workflow_dispatch` `recipes` input is untouched; no recipe and no CFE
  surface changes (`scripts/mason_cfe_surface_check.py` does not cover `.github/`). Kinships:
  `spec-coverage-gate-independence` CAP-4, `spec-pyforge-core` CAP-10 (its workflow test covers these
  four). Owner: mason.
- **2026-09-27 — Proposed: Mason has its own skills, and `conda-forge-expert` is one of them.**
  Operator direction, 2026-09-26: *Mason should have its own skills, with conda-forge-expert as
  one of them* (team memory `2026-09-26-operator-direction-not-started-mason-should-have`, which
  also says it enters here before any Spec, Story or code). Today every other station has a
  station skill (`.claude/skills/pyforge-<station>/`, SKF-compiled) and a persona
  (`bmad-agent-<station>`). Mason has the persona, and its skill tier is CFE itself. Recipe work
  is only one of the three crafts this Dream names: recipes, environments and shipping.
  **What the rules say today** (each one moves if this is accepted):
  - `AGENTS.md` § Policy: *never mint a lasting `src/shared/packages/` or
    `.claude/skills/pyforge-mason/` path*. Its `governance-currency:ignore` marker gives the
    reason: *mason's skill tier is conda-forge-expert per five_tier.py*.
  - `src/shared/packages/pyforge-steward/src/pyforge/steward/five_tier.py:104-106` counts Mason's
    `skill` cell as present only when `conda-forge-expert/SKILL.md` exists ("Mason 11.1: CFE is
    the domain skill. Do not require pyforge-mason/").
  - Mason Epic 11 (`epics.md` ~1552, ~1581): *`conda-forge-expert` is not replaced (no mason SKF
    that supersedes CFE)*; the Domain-skill row reads *CFE never replaced*.
  - `docs/reference/agent-instruction-notes.md:134`: *Mason … deliberately has no SKF skill*.
  - The Mason Frame, `docs/foundry/frames/stations/mason.frame.md:18`: *Do not SKF-compile
    `.claude/skills/pyforge-mason/`*. Frames are B's to write under the writer lock, so a change
    there lands on B, not here.
  **What does not move:** CFE is never replaced, forked or demoted. The direction keeps it as one
  of Mason's skills, which honours Epic 11's rule, since nothing supersedes CFE. Every conda-forge
  effort still closes with the CFE retro and its `CHANGELOG.md` semver bump.
  **Where it fits:** the foundry target tree already separates the two kinds of skill,
  `skills/{stations,personas,domain}/`. CFE is a domain skill; a Mason station skill sits
  beside it, the same way the other seven stations' do. On B this is the tree's intended shape.
  On A it collides with the Policy line above.
  **Questions for the operator, before `bmad-spec`:**
  1. **Root.** Does this land on A (an `A-only` mode with an expiry, since the Policy line
     forbids a lasting path) or only on B (`B-only`, named on a Spec before `done`)? The mode
     table is B's `docs/foundry/modes.md`.
  2. **Which skills.** Recipe work stays in CFE. The candidates for Mason's own skills are the
     other two crafts, environments (`mason environment lock`) and shipping (`mason package
     ship`), plus the station grammar every other station's skill documents (the `mason` CLI
     and `POST /stations/mason/mcp`). Which ones? And do the two feedstock workflows now written
     as how-tos (`docs/how-to/feedstock-platform-expansion.md`,
     `docs/how-to/feedstock-failure-remediation.md`) become Mason skills?
  3. **SKF.** Is Mason's station skill SKF-compiled like the other seven? That reverses
     `agent-instruction-notes.md:134` and the Frame line, and adds an eighth entry to the SKF
     block in `CLAUDE.md`.
  4. **The five-tier check.** Should `five_tier.py` require Mason's own station skill, keep CFE
     as its `skill` cell, or require both?
  **What it looks like when real:** Mason's station skill documents the Mason grammar the way
  `pyforge-steward` documents steward's. CFE stays the recipe skill and is linked from it.
  `five_tier.py` and the Policy line say the same thing. No recipe workflow is duplicated
  between the two.
  Kinships: mason Epic 11 (persona + CFE), steward's five-tier check (`canopy AD-14`),
  `spec-bmad-suite-lifecycle`'s adoption register (bmad-builder is already wielded by steward
  and mason for skill authoring), the cutover's `S-44.6` "CFE comes home" (`fnd:CAP-3`).
  **The operator's answers, 2026-09-28:**
  1. **Root: A now, expiring at the cutover.** `A-only` until `pyforge.cutover_root` flips to
     `foundry`; B rebuilds the skills under `skills/stations/`. The `AGENTS.md` Policy line gains a
     dated, expiring exception for `.claude/skills/pyforge-mason/`, and its `governance-currency:ignore`
     marker is corrected to match (landed with the Spec, before any story).
  2. **Skills: all four.** The station grammar skill `pyforge-mason` (the `mason` grammar and
     `POST /stations/mason/mcp`, linking CFE for all recipe work), a package craft skill (`mason
     package build|ship`), an environment craft skill (`mason environment lock|check`), and the two
     feedstock how-tos as Mason skills. Recipe work stays in CFE; CFE is never replaced, forked or
     demoted, and every conda-forge effort still closes with the CFE retro and its semver bump.
  3. **SKF: yes, like the other seven.** An eighth entry in the SKF block; `agent-instruction-notes.md:134`
     reverses. The Frame lines (`mason.frame.md:18`, and `pyforge.frame.md:21`'s matching clause) are
     B's to write under the writer lock: an operator-owned B-side follow-up, not edited here.
  4. **Five-tier: both.** `five_tier.py` requires `pyforge-mason` and CFE for Mason's skill cell.
  Found the same day: in `-e pyforge-guild`, `pyforge mason --help` answers `unknown station 'mason'`
  and `mason` is not on `PATH`, though the persona may act only through `pyforge mason …`. The front
  door works as built; the Guild environment never installed `pyforge-mason` (`spec-pyforge-steward:CAP-5`).
  Owner: mason. → `spec-pyforge-mason` CAP-29 / Epic 19 / Stories 19.1–19.5 (FR-51), specced
  2026-09-28: the SKF station skill and the persona consulting it (19.1), the package craft skill
  (19.2), the environment craft skill (19.3), the two feedstock campaigns as skills (19.4), and the
  closing Rule-2 retro (19.5). On steward's chain: `spec-pyforge-steward:CAP-161` / Story 72.1 (the Guild
  environment answers `pyforge mason`) and `spec-pyforge-steward:CAP-160` / Story 72.2 (the five-tier
  rule, gated on 19.1).
- **2026-09-28 — Proposed: no station or environment caps pixi.** Operator ruling, 2026-09-28:
  *"we should loosen pyforge-mason to be >=0.80.0 with no cap -- we don't need to cap pixi in any
  station / environment"*. Mason's `[package.run-dependencies]` pin `pixi = ">=0.80.0,<0.81"`
  (`src/shared/packages/pyforge-mason/pixi.toml:40`) is the only pixi ceiling in the repo; the root
  `pixi.toml`'s three `pixi = ">=0.80.0"` pins are floors. The ceiling kept its place on 2026-09-20,
  when the other engine ceilings came off under the ruling *never cap without a reason*; its written
  reason was that an in-env pixi above `requires-pixi` parses a manifest the workspace has not
  tested. It has already broken Mason's self-hosting build twice by lagging `requires-pixi`
  (2026-08-21, 2026-09-11). Today it holds every environment that carries `pyforge-mason`
  (`pyforge-mason`, `pyforge-container`, `pyforge-foundry-full`, `pyforge-foundry-full-stack`) at pixi
  0.80.0 while the rest of the workspace resolves 0.81.0, and adding Mason to the Guild would move the
  Guild's pixi 0.81.0 → 0.80.0 (found by steward Story 72.1's planning). Nothing checks the rule
  either: `pixi-version-check` compares pin sites with the `requires-pixi` floor, and this run-dep
  is not one of its registered sites.
  **What it looks like when real:** Mason pins `pixi = ">=0.80.0"`, a floor that tracks
  `requires-pixi` as a registered site of `scripts/pixi_version_registry.py` (so
  `bump-pixi-version` moves it too); `engines/__init__.py`'s `PIXI_VERSION_RANGE` mirrors it; and
  `pixi-version-check` reds any pixi dependency spec with an upper bound (`<`, `<=`, `==`, `~=`, a
  bare or wildcard pin) in the root `pixi.toml` or any `src/shared/packages/*/pixi.toml` /
  `pyproject.toml`. The four environments resolve pixi 0.81.x.
  **Constraints:** the root `pixi.toml` does not change (its pins are already floors); conda-lock's own
  upstream `virtualenv <21` cap is out of scope (a note, not a change); steward Story 72.1 is amended
  separately. Kinships: the 2026-09-20 ruling (*never cap without a reason*), `spec-pyforge-steward:CAP-161`
  (Story 72.1, the Guild environment that answers `pyforge mason`), `spec-pixi-candidate-currency`
  (governs `pixi.lock`). Owner: mason. → `spec-pyforge-mason` CAP-30 / Epic 20 / Story 20.1
  (FR-52), specced 2026-09-28.
- **2026-09-28 (night) — Proposed: Mason packages the intake toolchain: `git-pkgs`, `forge`,
  `gitgres`, `opengrep` and `pptxgenjs-plus-jsx`.** Operator ruling 2026-09-28, at the triage of
  three intakes (archived under `archive/docs/intake/`): package all five. Packaging is not
  adopting. Warden adopts `git-pkgs`, `forge` and `opengrep`, Atlas adopts `git-pkgs`, and Herald
  adopts `pptxgenjs-plus-jsx`. `gitgres` stays a design reference that nothing in the platform
  loads. None of the five is on conda-forge (checked 2026-09-28).
  **Upstream facts** (checked 2026-09-28):
  - `git-pkgs` CLI v0.20.0 and `forge` v0.10.0: MIT, Go, `github.com/git-pkgs`, pre-1.0, one
    maintainer.
  - `gitgres`: MIT, `github.com/andrew/gitgres`. It has no releases or tags. It is a PostgreSQL
    extension plus a libgit2 ODB/refdb backend, built `FROM postgres:17`, and it needs pgcrypto,
    libgit2 and libpq.
  - `opengrep` v1.30.0: LGPL-2.1, published as GitHub binaries only.
  - `pptxgenjs-plus-jsx`: the JSX companion that `recipes/pptxgenjs-plus` does not include.
  **What it looks like when real:**
  - Five `recipe.yaml` recipes under `recipes/`.
  - Each is a green local build on linux-64. `gitgres` builds against host
    `postgresql >=17.11,<18`, from a pinned commit until upstream tags a release.
  - Each carries a test that runs the binary or loads the extension.
  **Constraints:**
  - A green local build ends each story. There is no staged-recipes PR without an explicit ask.
  - `gitgres` builds against PostgreSQL 17 only (fnd:CAP-12).
  - The `conda-forge-expert` skill is invoked, and the effort closes with its retro and a
    CHANGELOG bump.
  - Where only a binary repack is possible (`opengrep`), the recipe stays local and records why.
  **Kinships:** [[pyforge-warden]], [[pyforge-atlas]] and [[pyforge-herald]] (same day). Owner:
  mason.
  **Amended 2026-09-28 (specced):** upstream was re-verified the same night, and two facts widen the
  work. `pptxgenjs-plus-jsx` pins `pptxgenjs-plus` at exactly 4.3.4 while `recipes/pptxgenjs-plus` is
  at 4.2.1, so its story moves the sibling too. conda-forge pins PostgreSQL 18 globally, so the
  `gitgres` recipe pins 17 explicitly.
  → `spec-pyforge-mason` CAP-31 / Epic 21 / Stories 21.1–21.5 (FR-53), specced 2026-09-28.
- **2026-09-28 (night) — Proposed: twelve recipes lose a converter's leaked sentinel key, and CFE refuses the next
  one.** Found by the session coordinator and verified the same night on `main` (`0c8c07e6fc`). Twelve `recipe.yaml`
  files carry a YAML mapping key that is literally `<conda_recipe_manager.types.SentinelType object at 0x…>`: `semgrep`,
  `boost`, `pyautogui`, `pyobjc-framework-systemconfiguration`, `psycopg2-yugabytedb`, `vc`, `django-pygwalker`,
  `ctng-compilers`, `StringZilla`, `lerc`, `amundsen-databuilder` and `shodan`. All came in with `20b2f459fa`
  (2026-08-16), a bulk conda-recipe-manager v0→v1 conversion of feedstock mirrors whose `meta.yaml` stays beside them.
  Wherever the `meta.yaml` had a construct crm could not translate, it wrote its sentinel's repr as a key. There are
  five shapes: a commented-out key (`#patches:`, `#host:`); a test with only `requires:` left once its commands were
  commented out; an `imports:` list split from its key by comments; `test.requires` orphaned at the top level after
  commented `pytest` lines; and jinja `{% for %}` / `{% if %}` blocks inside test commands. All twelve fail
  rattler-build's parse, and several hide more conversion defects behind the first. CFE's `validate_recipe` passes six
  of them: the key reads as a plain string, and conda-smithy flags it only at the top level. The current crm (0.10.6)
  still writes the sentinel and exits 100 ("warnings"), so re-converting does not repair them.
  **What it looks like when real:**
  - Each file says in v1 what its `meta.yaml` says and renders, validates and lints clean, with the cheap ones built on
    linux-64.
  - CFE's `validate_recipe` reds any `recipe.yaml` whose parsed tree has a non-string mapping key or a Python object's
    repr, so the next converter leak fails at the first gate.
  **Constraints:** `meta.yaml` stays, because the feedstocks are still v0. No feedstock or staged-recipes PR is opened.
  Both stories close with a CFE retro and a CHANGELOG bump. No Mason code changes. Kinships: CFE G92 (a re-serialization
  corrupts recipes), G93 (conda-recipe-manager crashes on column-0 comments), G84 (`migrate_to_v1` is a remote tool),
  and `spec-fleet-stewardship` (governs `recipes/**`). Owner: mason. → `spec-pyforge-mason` CAP-32 / Epic 22 / Stories
  22.1–22.2 (FR-54), specced 2026-09-28.
- **2026-09-29 — Proposed: CFE takes the three checks auto-recipe had and Mason lacked, and auto-recipe retires.**
  Operator ruling, 2026-09-29, after a capability-by-capability comparison of `OpenTeams-WFT-CDO/auto-recipe`
  (`8b53eda`; its last commit, 2026-08-13, made both workflows manual-only) against the `pyforge-mason` package and CFE.
  The operator owns that GitHub org, so its code may be ported, with a provenance line. Most of what auto-recipe does
  is already here: preflight and source resolution, the dependency audit against repodata rather than the package
  API, scaffolding, the eight recipe decisions, the hard rules (the optimizer's 20 check codes), the verify loop, the
  staged-recipes branch, and the failure catalog with `enforced_by` pointers (Epic 7, taken from auto-recipe in
  August). Three things are not:
  - **A Decided/Ambiguous contract.** `recipe-generator.py` guesses at six points: the `setuptools` backend default,
    the import-name fallback, the classifier-only noarch call, the licence (the first matching classifier, or
    `REPLACE_LICENSE`), `license_file: LICENSE`, and the `python_min` floor used when `python_requires` does not parse.
    auto-recipe returns a question at each of them instead of a guess.
  - **A licence-semantics check.** A GPL-family `-only` identifier whose LICENSE grants "any later version" passes
    every SPDX check, because both identifiers are valid. `license-checker.py` never reads the LICENSE text.
  - **A negative corpus.** Recipes that must stay rejected, each pinned to the rule that rejects it. CFE has one
    `v1-broken` fixture; auto-recipe keeps two grayskull outputs carrying three defects that passed conda-forge's
    linter.
  **What it looks like when real:**
  - The generator records every choice it could not settle as a question, on stdout and in the recipe's bottom CFE
    block, and `--strict` exits non-zero with the questions instead of writing the recipe.
  - `license-checker.py --check-source` reds a GPL-family `-only` licence whose LICENSE grants any later version, and
    names the `-or-later` identifier to use.
  - A fixture that passes every check fails the suite.
  **Constraints:** CFE code only, and no Mason source change: `mason recipe new` and `mason recipe validate` reach the
  checks by subprocess (AD-1). Each story closes with a `retro(cfe):` commit and a CHANGELOG bump. The unattended half
  of auto-recipe (issue to draft staged-recipes PR, the PR watcher, the LLM fix loop and its five-attempt cap) is a
  non-goal, because this repo opens no staged-recipes PR without an explicit ask. The MCP `generate_recipe_from_pypi`
  tool runs grayskull, not `recipe-generator.py`, and is out of scope. Archiving the auto-recipe repo is the
  operator's act. Kinships: CFE Operating Principle 1 (present the interpretations, don't pick silently), G7 (import
  names), G55 (build backends), G90 (generator emission gaps), and `machine-checked-recipe-knowledge` (Epic 7).
  Owner: mason. → `spec-pyforge-mason` CAP-33 / Epic 23 / Stories 23.1–23.3 (FR-55), specced 2026-09-29.
- **2026-09-29 (later) — Proposed: the CFE host-gate tests give the same verdict in any developer shell.**
  A local `pr-preflight` failed 1 of 9152 tests and the pre-push hook blocked the push, while CI stayed green. The
  failing test asserts the exact host allowlist that `inventory_channel.py`'s fallback builds, and that allowlist, like
  `_http.py`'s and `dependency-checker.py`'s, is derived from every `*_BASE_URL` env var the shell exports, plus npm's
  registry vars. A Claude Code shell exports `ANTHROPIC_BASE_URL`, so `api.anthropic.com` joined the set. Only one of
  the six test modules that exercise the gate cleared all of those vars; two cleared none, and three cleared a
  subset. So any agent session, or any operator with a mirror var of their own, could red a test that CI
  never sees.
  **What it looks like when real:**
  - Every host-gate test starts from no ambient `*_BASE_URL` or npm mirror var, through one shared fixture that reads
    the npm names from `_http` rather than restating them.
  - The same tests pass with `ANTHROPIC_BASE_URL` set and without it, and `pr-preflight` passes from an agent shell.
  - A test that plants a stray var before the fixture runs keeps the fixture honest in CI, which has no such var.
  **Constraints:** tests only. `_http.py` and `inventory_channel.py` keep their behaviour, and Mason reaches none of it
  (AD-1). The fixture is opt-in, so `network`-marked tests keep an operator's real mirror routing. The change lands in
  one `retro(cfe):` commit with a CHANGELOG bump (AD-15). The operator ruled on 2026-09-29 that this test-only fix
  takes the whole chain before it merges, rather than landing as a bare `retro(cfe):` commit as PR #1091's
  merge-guard fix did. Kinships: `_http.py`'s host gate (the SKILL.md constraint on JFrog credentials), CFE G99
  (fixture-scale tests hide validator behaviour), and `spec-packaging-factory` (governs the CFE surface).
  Owner: mason. → `spec-pyforge-mason` CAP-34 / Epic 24 / Story 24.1 (FR-56), specced 2026-09-29; landed in PR #1669.
- **2026-09-29 (evening) — Proposed: the feedstock refresh campaign joins Mason's chain.** Operator ruling,
  2026-09-29: `docs/specs/` retires (`spec-one-chain-per-station` CAP-11), and the one unfinished effort
  there, `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/feedstock-refresh.md`, is carried into Mason's chain before its file moves. That
  file is a legacy intake spec with two tracks, covering every conda-forge feedstock `rxm7706` can
  modify (769 at its 2026-06-19 count):
  - **Track A, sole-maintainer (537 feedstocks).** Waves B to F shipped on 2026-06-21 for the 252
    recipes then behind (`363537dd43`, `1fe1848b43`). It was reopened the same day for Wave H, the
    179 recipes the behind-only scope had missed, and paused at a weekly usage limit.
  - **Track B, co-maintained (232 feedstocks; 190 with a local recipe and 42 without).** Scoped, and
    never started. Its extra rule is to preserve every other maintainer's work.
  Both tracks regenerate each recipe through CFE (diff-apply), fold in platform expansion where the
  recipe is compiled, and never push without an explicit instruction. Its counts are from June;
  the July punch-list and bump waves have changed many of them since.
  **What it looks like when real:** each track is a Mason story that re-counts its scope live from
  the atlas before it starts, refreshes each local recipe to its feedstock's published version, and
  ends at a green local build. The legacy file becomes a companion of Mason's Spec, so its waves,
  landmines and parameters stay live.
  **Constraints:** recipe work goes through `conda-forge-expert` (Rule 1); no feedstock or
  staged-recipes PR opens without an explicit ask; each story closes with a CFE Rule-2 retro. The two
  campaign skills Story 19.4 builds (platform expansion, failure remediation) are its tools, not its
  scope. Kinships: [[one-chain-per-station]] (CAP-11, the same day), CFE G53 (re-merge co-maintainers)
  and G96 (a bump's dependency authority is the feedstock). Owner: mason. → `spec-pyforge-mason`
  CAP-35 / Epic 25 / Stories 25.1–25.2 (FR-57), specced 2026-09-29.
- **2026-10-02 — Proposed: CFE's tests never ask GitHub whether a recipe maintainer exists.** The CFE
  regression lane (`cfe-regression-net`) failed twice on one PR and passed on a re-run, in a different test each time.
  `tests/integration/test_workflow_npm.py` validates recipes through conda-smithy's linter, whose maintainer check
  (`lint_recipe._maintainer_exists`, and `_team_exists` for a team) asks github.com whether the maintainer exists.
  With no `GH_TOKEN` in that lane it asks unauthenticated, from a runner, and when the answer is not a 200 the lint
  reports `Recipe maintainer "rxm7706" does not exist`. The same request from a workstation returns 200.
  **What it looks like when real:** CFE's tests answer the maintainer and team lookups locally unless a test is marked
  `network`, so the lane's verdict no longer depends on how GitHub treats an unauthenticated runner.
  **Constraints:** tests only; CFE's validator keeps calling conda-smithy's real lint at runtime. The change lands in
  one `retro(cfe):` commit with a CHANGELOG bump (AD-15). Same class as Story 24.1 (a test whose verdict depends on
  its environment). Owner: mason. → `spec-pyforge-mason` CAP-34 / Epic 26 / Story 26.1 (FR-56), specced 2026-10-02.
- **2026-10-03 (Phase 4+5) — Ruled: mason's open medium and low deferrals are fixed where they sit.** Operator ruling,
  2026-10-03: Phases 4 (open medium deferrals) and 5 (open low deferrals) of the deferral burn-down run together on the
  idle station lanes, and, by a second ruling the same day, as fewer, larger stories of at most about 30 rows each, split by
  package area, with the CFE-surface rows in their own story so its `retro(cfe):` landing stays separate. Mason's ledger
  holds 20 open medium and 42 open low rows, counted with a parser over its `DW-` entries. **What it looks like when
  fixed:** two fix stories close 61 of them. One covers Mason's package and the repo tooling it owns: the environment
  verbs' exit codes and JSON error path, the conda-lock check engine, the meta-guards, the CFE-rebuild guard script and
  the skf audit scripts. The other covers conda-forge-expert, its failure catalog and the closed CFE-rebuild campaign's
  records. Each row closes with a `resolution:` naming its story and a `verified:` line citing the line that fixed it; a
  row whose surface Story 15.1 retired closes on the line that records the retirement. **Constraints:** `fix` stories, no
  CAP, no flag (`spec-feature-flag-governance` Q1). The CFE story goes through `conda-forge-expert` and lands its CFE edits
  in a `retro(cfe):` commit with a CHANGELOG semver entry (AD-15). No commit touches both Mason's package and the CFE
  surface (`mason-cfe-surface-check`). DW-PRESENTON-PHASE0-1 stays open: its exits wait on decisions and access outside
  this repo. The 71 open rows that carry no severity, and the one open high row, are outside these two phases. Owner:
  mason (`spec-pyforge-mason`, no new CAP). → Epic 27 / Stories 27.1–27.2, specced 2026-10-03.
- **2026-10-09 — Ruled: Story 22.1 lands for eleven recipes, and ctng-compilers waits for rattler-build.** Operator
  ruling, 2026-10-09. The 22.1 dispatch repaired all twelve sentinel keys. Eleven of the twelve then render, validate and
  lint clean on a platform each builds. `ctng-compilers` does not: once its sentinel and its output-level `run_exports`
  are repaired, `rattler-build build --render-only` 0.76.1 (`.ci_support/linux64.yaml` plus the local pinning) still
  exits 1 with `Cycle detected in recipe outputs` across the gcc stack. rattler-build #2531 (a false cycle from
  `pin_subpackage` in `run_constraints`) closed on 2026-07-03 and 0.76.1 carries its fix, so this is a case that fix did
  not cover. **What it looks like when real:** 22.1 lands its eleven (ten after the second ruling below).
  `ctng-compilers/recipe.yaml` stays as `main` has it, sentinel included, and 22.1's corpus check allowlists that one
  leak by file and location. A new story repairs it once a rattler-build release, or a feedstock-faithful variant set,
  renders the gcc output graph, and it removes the allowlist entry. **Constraints:** a `fix` story under CAP-32, no new CAP, no flag (`flag-exempt: recipe-build`). It stays
  `blocked` until the operator flips it. Reporting the cycle upstream is outward work and waits for the operator.
  Owner: mason. → `spec-pyforge-mason` CAP-32 / Epic 22 / Story 22.3 (FR-54), specced 2026-10-09.
- **2026-10-09 (later) — Ruled: Story 22.1 lands for ten recipes, and vc waits for a named track feature.** Second
  operator ruling, 2026-10-09, after the independent review of the 22.1 landing failed it. The run's v1 port of
  `recipes/vc/recipe.yaml` renders, but it does not say what `meta.yaml` says. `meta.yaml` gives the `vc`,
  `vs<year>_<platform>` and `vs_<platform>` packages `track_features: [vc14]`, a feature they share. rattler-build 0.76.1 rejects
  `build.track_features`, and its `variant.down_prioritize_variant` writes a per-package `<name>-p-0` instead. The port
  also hardcoded the VS 2026 win-64 values in `context` in place of the feedstock's five-entry variant matrix. It left
  out `vc_repack.py`, `activate.bat`, `LICENSE.TXT` and `conda_build_config.yaml`. Its inheriting outputs called
  `python` with no `python` build requirement. And it compared the string `vsver` with an integer; minijinja answers
  `true` for `"9" >= 17` as well as for `"18" >= 17`. **What it looks like when real:** 22.1 lands its ten. `vc/recipe.yaml` stays as `main`
  has it, sentinel included, and 22.1's corpus check allowlists that one leak by file and location. A new story ports vc
  once a rattler-build release can emit a named track feature, and it removes the allowlist entry. **Constraints:** a
  `fix` story under CAP-32, no new CAP, no flag (`flag-exempt: recipe-build`). It stays `blocked` until the operator
  flips it. Asking rattler-build for the feature is outward work and waits for the operator. Owner: mason.
  → `spec-pyforge-mason` CAP-32 / Epic 22 / Story 22.4 (FR-54), specced 2026-10-09.
- **2026-10-09 — Ruled: CFE gains a tracked bulk refresh driver, so Track B can continue.** Operator ruling, 2026-10-09:
  mint a driver story so Story 25.2 can continue. Story 25.1 refreshed 92 sole-maintainer recipes with scripts it never
  committed (`.cursor/wave_h_*` in its dispatch worktree). Story 25.2 stopped `blocked` after Wave A, with 96
  co-maintained recipes queued and no batch driver in the repo. Its pilot through CFE's autotick failed on a recipe with
  no `context.name`. Those uncommitted scripts also left four defects in 25.1's landing:
  - `recipes/wasmtime-py/meta.yaml` was renamed to `.meta.yaml.wave_h_hold`, although that feedstock is still v0. An
    early exit skipped the restore.
  - 56 recipes lost their templated `pypi.org/packages/source` URL to a hashed `files.pythonhosted.org` one.
  - 78 of the 92 recipe diffs re-indent lists.
  - The CFE version carriers broke lockstep at 8.97.1. Story 22.1's landing restores it at 8.98.0.

  **What it looks like when real:** one tracked CFE script, `refresh-wave`, takes a wave manifest. It refreshes each
  recipe to its feedstock's published version through CFE's own edit path, and keeps a v0 feedstock's `meta.yaml` in
  place. It re-merges every co-maintainer, reports a dependency or pin difference instead of applying it, and records
  each outcome in the recipe's CFE comments and in a wave report. It is dry-run by default, resumable, and idempotent.
  Stories 25.1 and 25.2's waves run through it, not through a session's scratch scripts.
  **Constraints:**
  - Everything the driver does with these recipes stays local. It never runs `git push`, `gh pr create`,
    `gh repo fork`, a `gh api` write, `mason recipe submit` or `mason package ship`, or CFE's `submit_pr` or
    `prepare_submission_branch`.
  - It only reads feedstocks (raw files, or `gh api` GETs), and writes only under `recipes/` and its own report path.
    No PR, issue or comment reaches conda-forge, a feedstock, staged-recipes, or any repository other than
    `rxm7706/local-recipes`.
  - The work goes through `conda-forge-expert` (Rule 1), and its CFE edits land in one `retro(cfe):` commit with a
    CHANGELOG semver entry (AD-15).
  - The story repairs none of the four landing defects in `recipes/`: they are context, and the driver stops them
    recurring.

  Owner: mason (`spec-pyforge-mason`, no new CAP: CAP-35 is the campaign, CAP-20 the parameterized wave, CAP-23 the CFE
  machinery). → Epic 25 / Story 25.3 (FR-57), specced 2026-10-09; Story 25.2 now depends on it.
- **2026-10-09 (later) — Ruled: Story 25.2's first wave repairs what Story 25.1's landing damaged.** Second operator
  ruling, 2026-10-09: 25.2's first wave runs the new driver over the recipes 25.1's landing damaged, to repair them.
  **What it looks like when real:** the driver gains a `--repair` mode, separate from its refresh path, which still never
  rewrites a URL. Repair does three things and nothing else:
  - it puts a hashed `files.pythonhosted.org` sdist URL back in the canonical `pypi.org/packages/source` form, with the
    sha256 unchanged and verified;
  - it re-indents list items to CFE's canonical style, whitespace-only;
  - it restores a v0 feedstock's `meta.yaml`, from the feedstock or else from the hold file, and removes the hold file.

  It moves no version, build number, dependency or maintainer. Story 25.2's Wave 0 runs it, before any Track B wave,
  over 79 recipes:
  - the 56 in 25.1's landing with a hashed URL;
  - the 78 whose lists it re-indented;
  - `recipes/wasmtime-py`.

  **Constraints:** local only, like every wave: no push, PR, fork, issue or comment outside `rxm7706/local-recipes`.
  Wave 0 is the one place Story 25.2 touches Track A's recipes. Owner: mason (no new CAP). → Story 25.3's repair mode
  and Story 25.2's Wave 0, specced 2026-10-09.
- **2026-10-09 — Ruled: the CFE-rebuild guard reads a SHA field whatever type YAML gives it.** Operator ruling,
  2026-10-09 ("yes mint both stories and keep going"). On PR #2031 the `scripts-suite` job failed
  `test_brief_must_name_every_retro_at_or_older_than_the_pointer` (Detectors run 37990293221). The guard reported a
  `brief-defect` for a brief that does name its retro: `has no retro-mirror amendment naming 4139357790`. PyYAML's
  `safe_load` reads an unquoted all-digit token such as `commit: 4139357790` as an `int`, and
  `scripts/cfe_rebuild_guard_check.py` keeps only `str` values as SHA candidates. The test makes real commits, so it
  fails whenever the older retro's 10-character prefix is all digits and loads as an int. All-digit prefixes come up in
  (10/16)^10 of runs, about 0.9%, and most of them load as an int. A brief written by hand hits the same false finding.
  Checked the same day against PyYAML 6.0.3:
  - `0123456789` stays a string. A leading `0` followed only by the digits 0 to 7 (`0123456701`) loads as an octal
    `int`, and `0b` followed by 0s and 1s (`0b10110101`) loads as a binary one. The value's decimal string matches
    neither.
  - An `int` `brief_mirrored_through` is skipped by the brief check, and the history check reports it
    `unmirrored-retro` even when it names the newest retro.
  - The history check compares the pointer to the newest retro by full-SHA equality, but its own remedy says to set a
    10-character prefix, so following the remedy keeps the finding.

  **What it looks like when real:** every SHA the guard reads from YAML is read as the scalar was written, whether
  YAML loaded it as a string or an int. That covers a `retro-mirror` amendment's fields and list items, and a slice's
  `brief_mirrored_through`. A bool, float or null is never a SHA. Every SHA comparison uses one rule: two hex tokens
  of at least ten characters name the same commit when one is a prefix of the other. Deterministic tests pin each form
  without making commits. **Constraints:** a `fix` story under CAP-16, with no new CAP and no flag
  (`spec-feature-flag-governance` Q1). It touches only the guard script and its test. That script is repo tooling, not
  the CFE surface, so the story has no `retro(cfe):` commit. A new Epic 28 carries it, because Epics 6 and 12, the
  guard's own epics, are done. Owner: mason. → `spec-pyforge-mason` CAP-16 / Epic 28 / Story 28.1, specced
  2026-10-09.
- **2026-10-09 (night) — Ruled: Story 25.2 lands with Wave 0 and its pilots, and Track B continues in batch
  stories.** Operator ruling, 2026-10-09, the option "Land 25.2 now, split rest": "Re-scope 25.2 to Wave 0 + the
  pilots (14 leftovers recorded needs-review with reasons) and land it, so the repairs reach main. Mint 25.4+ for
  Track B in batch stories, each small enough for one dispatch." Story 25.2's three passes on
  `dispatch/pyforge-mason/25.2` stopped `blocked` with this record:
  - Wave A counted 288 co-maintained feedstocks live: 268 with a local recipe and 20 without. 96 are behind their
    feedstock's published version (the v1-refresh bucket).
  - Wave 0 ran `refresh-wave --repair --apply --gates` over a 78-recipe manifest: 62 repaired, 2 already clean, 10
    needs-review and 4 failed. None of the 14 leftovers carries a CFE metadata block, and the driver's checks require
    exactly one.
  - Four Track B pilots were refreshed and built green on linux-64: assemblyai 1.0.0 → 1.3.0, bmad-method 6.12.0 →
    6.12.1, cron-descriptor 2.1.0 → 2.1.1 and cssselect2 0.9.0 → 0.10.1. Two dry-runs left six more needs-review:
    airflow-code-editor, avro, azure-monitor-opentelemetry-exporter, azure-storage-file-share, billiard and
    cachetools.

  That leaves 92 v1-refresh recipes. Reading the driver at mint found four gaps behind its refusals:
  - It renders only a bare `${{ var }}`, so a `${{ name[0] }}` URL is refused.
  - It calls a URL templated through a `context` variable derived from the version "version-baked".
  - Its repair check reports "count changed" for a recipe that has no CFE block at all.
  - It compares dependency names, never an uncommented version pin. That matters for the OpenTelemetry family's exact
    pins on one another.
  **What it looks like when real:** Story 25.2 lands with Wave A, Wave 0, the four pilots and its 14 leftovers
  recorded with reasons, so Wave 0's 62 repairs reach `main`. Story 25.4 takes the 14 leftovers: it stamps each missing
  CFE block, re-runs the repair, and records the four driver gaps. Stories 25.5 to 25.12 split the 92 into eight
  batches of 11 or 12 named recipes. Each batch is one wave through the driver and one dispatch, and clears in the
  recipe, through `conda-forge-expert`, any refusal it can. The 20 missing mirrors (Wave F) stay a recorded deferral,
  because Track B's Q2 (`<create_missing>`) has no ruling. A mint-time read finds 18 of them are outputs of
  `recipes/db-gpt` and `recipes/langflow`, so Wave F may be two recipes, not 20.
  **Constraints:** every Epic 25 line stands. The work stays local, goes through `conda-forge-expert`, keeps each
  maintainer list a superset of the deployed one (G53), ends each recipe with a linux-64 build or a recorded reason,
  and closes each story with its own `retro(cfe):` commit. No new CAP. Owner: mason. → Epic 25 / Story 25.2
  re-scoped and Stories 25.4 to 25.12, specced 2026-10-09.
- **2026-10-09 (night, later) — Ruled: Wave F creates the missing mirrors, and the 18 outputs stay in their
  feedstock's mirror.** Operator ruling, 2026-10-09, answering Track B's Q2 (`<create_missing>`): "create them". A
  read of the 20 against the atlas's `packages.feedstock_name` and conda-forge's `feedstock-outputs` registry finds
  four feedstocks, not 20:
  - `dbt-snowflake` and `zxing-cpp-python` are feedstocks with no local recipe in any directory.
  - The 16 `dbgpt-*` are outputs of `db-gpt-feedstock`, and `langflow-base` and `langflow-sdk` of
    `langflow-feedstock`. Both already have their local mirror, `recipes/db-gpt` and `recipes/langflow`.
    `conda-forge/<name>-feedstock` is a 404 for each of the 18.

  The investigation behind the choice:
  - No repo check refuses two recipes that declare one package name. `main` carries six directories that declare
    `langflow-suite`'s eight outputs, at two versions, and `recipes/dbt` and `recipes/dbt-core` both build `dbt-core`.
  - What a duplicate breaks is the mirror. A standalone `recipes/dbgpt-app` would mirror no feedstock, could never be
    submitted (the registry lets one feedstock claim each name), and would shadow the multi-output build in the shared
    local channel.
  - Dropping the outputs from the multi-output mirrors instead would break both mirrors' fidelity, and reverse G72.

  The same read found more:
  - Wave A's name-matching also misread four `langflow-suite` bundles (`lfx-*`) as ahead, from those duplicate
    directories; they are behind.
  - The driver moves `context.version` only, so a suite's per-output versions stay behind (gap 5).
  - conda-forge repurposed `zxing-cpp-feedstock` from the Python bindings to the C++ library on 2026-09-08, which makes
    Story 25.9's version bump of `recipes/zxing-cpp` wrong.

  **What it looks like when real:** Story 25.13 mirrors `dbt-snowflake` and `zxing-cpp-python` from their feedstocks,
  with every maintainer kept, and builds both on linux-64. Story 25.14 creates no directory. After Story 25.7, it
  brings each of the 18 and the four bundles to its published version in `recipes/db-gpt` or `recipes/langflow`,
  corrects `recipes/db-gpt`'s stale CFE block, and records the corrected mapping and every duplicate directory. It also
  closes Wave F's deferral. Story 25.9 re-mirrors `recipes/zxing-cpp` from the repurposed feedstock (its AC 13). Two
  questions go back to the operator: whether "create them" meant 20 directories (recommended: no), and whether to
  retire the duplicate directories (recommended: yes, in a fix story of their own).
  **Constraints:** every Epic 25 line stands: local only, through `conda-forge-expert`, maintainers a superset of the
  deployed list (G53), a linux-64 build or a recorded reason, and a `retro(cfe):` commit per story. No new CAP. Owner:
  mason. → Epic 25 / Stories 25.13 and 25.14, and a note on Story 25.9, specced 2026-10-09.
- **2026-10-09 (night, latest) — Ruled: Wave F stays inside the mirrors, and five duplicate directories retire.** Two
  operator rulings answer the questions the Wave F mint left on Story 25.14's spec:
  - On Wave F's 18 output packages, "Yes, inside the mirrors". Stories 25.13 and 25.14 stand. The 18 reach their
    published versions inside `recipes/db-gpt` and `recipes/langflow`, and no standalone directory is created.
  - On the duplicate directories, "Retire in a fix story": "Mint a mason fix story that removes the six duplicate dirs
    (folded into recipes/langflow and recipes/dbt-core) and drops recipes/lfx from 25.7's batch."

  The mint verified ownership before scoping, against conda-forge's `feedstock-outputs` registry, the atlas and the
  feedstock repos (read-only GETs):
  - The five `lfx*` copies mirror no feedstock. `conda-forge/<dir>-feedstock` is a 404 for each, and the registry gives
    every name they declare to `langflow`. Each copy is `langflow-suite` at 1.11.3 with no `patches/` directory, so
    none builds. `recipes/langflow` already has everything they carry, except older pins it loosened on purpose.
  - `recipes/dbt` is not a duplicate in that sense. `conda-forge/dbt-feedstock` exists and publishes `dbt-core`, and
    `recipes/dbt` is its `recipes/<feedstock>/` mirror; its CFE block names that feedstock. `recipes/dbt-core` has no
    feedstock of its own name and no CFE block, and still carries a 1.8.9 `meta.yaml`. Retiring `recipes/dbt` would
    delete the mirror and keep the misnamed copy.

  The same read found more. Three dbt adapter recipes (`dbt-bigquery`, `dbt-postgres`, `dbt-redshift`) carry
  `dbt-core`'s recipe, written by the 2026-08-16 identity snapshot. Two staged-recipes PRs for the bundles, #33977 and
  #33978, are still open, though `langflow-feedstock` now publishes both. No repo check refuses two directories that
  declare one package name, and 110 names have two or more declarers today.
  **What it looks like when real:** Story 25.15 retires the five `lfx*` copies in one commit, after checking each
  against the registry again and recording what `recipes/langflow` already has. A parse then finds every
  `langflow-suite` output declared by `recipes/langflow` alone, and the suite builds all eight outputs on linux-64.
  `recipes/dbt` and `recipes/dbt-core` stay until the operator says which one mirrors `dbt-feedstock`. The adapters,
  the open PRs and the missing duplicate guard are recorded, not acted on. Story 25.7's batch drops `recipes/lfx`, and
  Story 25.14 runs after Story 25.15.
  **Constraints:** every Epic 25 line stands: local only, through `conda-forge-expert`, and a `retro(cfe):` commit.
  The story is a fix and carries no flag. No new CAP. Owner: mason. → Epic 25 / Story 25.15, with amendments to Stories
  25.7 and 25.14, specced 2026-10-09.
- **2026-10-10 — Ruled: recipes/dbt-core retires into recipes/dbt, and the three dbt adapters are re-mirrored.** Two
  operator rulings of 2026-10-09 answer the questions Story 25.15's mint left:
  - On which directory mirrors `dbt-feedstock`, "Retire recipes/dbt-core": "Keep recipes/dbt as the dbt-feedstock
    mirror, retire recipes/dbt-core, and re-point batch 25.5's dbt-core row to recipes/dbt. Added to Story 25.15."
  - On the three dbt adapter recipes, "Fix in a story": "Mint a mason fix story that re-mirrors the three adapter
    recipes from dbt-bigquery/postgres/redshift-feedstock (dbt-bigquery-feedstock is now v1 at 1.12.1), and correct
    batch 25.5's table."

  A live read (read-only GETs) shaped both:
  - `recipes/dbt-core` carries nothing `recipes/dbt` lacks. Both list the feedstock's patch file, and neither has it,
    so neither builds. The patch has not changed in `dbt-feedstock` since the commit `recipes/dbt` mirrors.
  - Each adapter has its own feedstock: `dbt-bigquery` v1 at 1.12.1 since 2026-09-19, `dbt-postgres` v0 at 1.11.0,
    `dbt-redshift` v0 at 1.11.1. Each local `recipe.yaml` is `dbt-core`'s instead, so a version refresh would move the
    wrong package. Each adapter's build resolves `dbt-core` from conda-forge, so the fix waits for nothing.
  - `langflow-feedstock` replaced its five patches with a `patch_deps.py` script on 2026-09-25, so Story 25.7's plan to
    re-base three patches no longer mirrors the feedstock.

  **What it looks like when real:** Story 25.15 restores `recipes/dbt`'s patch file from its feedstock and retires six
  directories: the five `lfx*` copies, and `recipes/dbt-core`. `recipes/langflow` alone then builds the suite's eight
  outputs, and `recipes/dbt` builds `dbt-core`. Story 25.16 re-mirrors `recipes/dbt-bigquery`, `recipes/dbt-postgres`
  and `recipes/dbt-redshift` from their own feedstocks, each built on linux-64 or recorded `needs-review` with its
  reason. After both, `dbt-core` has one local recipe. Story 25.5 refreshes `recipes/dbt` after Story 25.15, and holds
  11 recipes. Story 25.7 takes `langflow-feedstock`'s `patch_deps.py`. The two staged-recipes PRs for the bundles,
  #33977 and #33978, stay the operator's to close.
  **Constraints:** every Epic 25 line stands: local only, through `conda-forge-expert`, maintainers a superset of each
  feedstock's own list (G53), and a `retro(cfe):` commit per story. Both stories are fixes and carry no flag. No new
  CAP. Owner: mason. → Epic 25 / Story 25.16, with Story 25.15 re-scoped and amendments to Stories 25.5, 25.7 and
  25.13, specced 2026-10-10.

- **2026-10-12 — Ruled: a local pwntools carries the upstream unicorn fix, so pwndbg's pip check holds.** Two
  operator rulings of 2026-10-12, at the follow-up to the REA recipes (PR #2168): "Fix the unicorn conflict", then, on
  how, "Backport #2721 locally (Recommended)".

  A live read (read-only GETs) shaped both:
  - `recipes/pwndbg` (2026.09.15) requires `unicorn>=2.1.4,<3`. pwndbg raised that floor to 2.1.3 and then to 2.1.4
    (pwndbg `d98f0b708`, #3292).
  - pwntools 4.15.0, its latest release, requires `unicorn>=2.0.1, !=2.1.3, !=2.1.4`, because both versions segfault
    when pwntools emulates a MIPS PLT (unicorn-engine/unicorn#2134). conda-forge's newest `python-unicorn` is 2.1.4, so
    no version satisfies both, and `recipes/pwndbg` ships with `pip_check: false`.
  - pwntools fixed it on its `stable` branch in `7e5e79d00f` (Gallopsled/pwntools#2721, 2026-04-27). The dependency
    becomes `unicorn>=2.0.1`, and `pwnlib/elf/plt.py` raises an `OSError` for MIPS on 2.1.3 and 2.1.4 instead of
    crashing. No release carries it yet.
  - `recipes/pwndbg` lists conda-forge `unicorn`, which is the C library. The Python bindings (`import unicorn`) are
    `python-unicorn`, which pwndbg gets only through pwntools.

  **What it looks like when real:** `recipes/pwntools` mirrors `conda-forge/pwntools-feedstock`: its `meta.yaml`
  verbatim, and a v1 `recipe.yaml` beside it that applies #2721 as a source patch at build number 1. `recipes/pwndbg`
  depends on `python-unicorn` and runs `pip check` again. Both build green on linux-64. Any solve that sees the local
  channel or SelfExplainML takes the local pwntools over conda-forge's until a pwntools release carries #2721; the
  mirror then drops the patch.
  **Constraints:** local only, with no feedstock PR unless the operator asks; through `conda-forge-expert`; the story
  closes with a `retro(cfe):` commit. It is a fix: no flag and no new CAP. It binds CAP-18 (the local mirror as source
  of truth) and CAP-23 (recipe lifecycle machinery). Owner: mason. → Epic 29 / Story 29.1, specced 2026-10-12.

- **2026-10-12 (later) — Ruled: the recipes that import playwright depend on its bindings.** Operator ask of
  2026-10-12, verbatim: "Do this task here: Audit 16 recipes that depend on conda playwright". Story 29.1's G107 check
  (`test_split_distribution_run_deps.py`) declares the `playwright` / `playwright-python` pair but does not lint it.
  Run unlinted, it flags 16 `noarch: python` recipes that list conda `playwright` and not `playwright-python`.

  A live read (read-only GETs) settled each one:
  - conda-forge `playwright` is the Node CLI and browser driver, with no Python module. `playwright-python` is the
    bindings (`import playwright`, PyPI distribution `playwright`), and it depends on the CLI.
  - Fifteen of the 16 upstreams list PyPI `playwright` in `requires_dist`, so each imports the bindings. The sixteenth,
    `recipes/playwright-python`, is the bindings recipe itself, and its dependency on the CLI is correct.
  - Every pin those 15 carry (`>=1.18` to `>=1.59.0`, plus `==1.49.1` and `==1.58.0`) has a `playwright-python` build on conda-forge (1.44.0 to
    1.62.0).
  - Fourteen of the 15 recipes have never been built locally (12 `cfe-local-build-status: not-attempted`, 2 with no
    CFE block).

  **What it looks like when real:** each of the 15 recipes lists `playwright-python` with its upstream spec in place of
  `playwright`. The G107 check lints the pair, exempting only the bindings' own recipe. Each recipe whose other
  dependencies resolve builds green on linux-64 with `pip check`; any that cannot build records the blocker in its CFE
  block.
  **Constraints:** local only, through `conda-forge-expert`, with a `retro(cfe):` commit. It is a fix: no flag and no
  new CAP. It binds CAP-18 and CAP-23, as Story 29.1 does. Owner: mason. → Epic 30 / Story 30.1, specced 2026-10-12.

- **2026-10-14 — Fixed: CFE's fleet-picture ATTENTION test stubs the CI-pause probe.** Measured on clean `main`
  on 2026-10-14: `tests/meta/test_fleet_picture_main_attention.py` fails all three of its tests, and so does the
  `cfe-regression-net` lane (`test-ci`) on any PR that touches its paths. Doctor Story 45.1
  (`pyforge-doctor:CAP-89`, merge `7c6dac8c07`) added `ci_pause_drift_findings()` to `scripts/fleet_picture.py`'s
  `main()`. The test stubs every probe it lists in `_PROBES`, and that list did not name the new one, so the probe read
  the test's fake `subprocess.run`, could not parse it, and added `could not check CI pauses` to every `watch` list.
  The lane never ran on Story 45.1's PR, because its path filter covers the CFE tree and the pixi files, not
  `scripts/fleet_picture.py`.

  **What it looks like when real:** the test lists `ci_pause_drift_findings` with the other probes, stubs it with one
  `ci-pause-drift` finding, and expects its `watch` line and its `could not check CI pauses` line in `main()`'s order.
  All three tests pass, and the CFE meta suite is green.
  **Constraints:** tests only: `scripts/fleet_picture.py` and every CFE script stay unchanged. No assertion is skipped
  or weakened. The change lands in one `retro(cfe):` commit with a CHANGELOG PATCH bump (AD-15). It is a fix: no flag
  and no new CAP. It binds CAP-23 (the skill's own meta-test suite is green), as Stories 29.1 and 30.1 do. Owner:
  mason. → Epic 31 / Story 31.1, specced 2026-10-14.
- **2026-10-22 — Fixed: CFE's tests never fetch conda-smithy's remote lint data.** On 2026-10-22 a local `pr-preflight`
  failed 1 of 9,391 `test-ci` tests: `tests/integration/test_workflow_npm.py::test_canonical_chain_with_deps`, where
  conda-smithy's lint could not resolve `raw.githubusercontent.com`. The same test passed minutes later. Story 26.1
  stubbed the two GitHub lookups conda-smithy's linter makes, but its lint (3.62.0) reads two more files from GitHub:
  - `validate_schema.validate_json_schema` resolves the `bot` property of a recipe's `conda-forge.yml` through a
    `$ref` to `regro/cf-scripts`' `cf_tick_schema.json`, with `requests.get` and no timeout. Every generated recipe
    carries a `bot:` block (CFE v8.61.0).
  - `linter.utils.load_linter_toml_metdata_internal` fetches conda-forge-pinning's `linter_hints/hints.toml` for every
    recipe it lints. It catches only `Timeout`, so a DNS failure raises out of the lint.

  With the network blocked (`unshare -rn`), four tests fail, including Story 26.1's own regression test. That test's
  trap matches `github.com` only, so it missed `raw.githubusercontent.com`.
  **What it looks like when real:** every CFE test not marked `network` answers both reads locally, in the pytest
  process and in the conda-smithy child `validate_recipe` starts. The `bot` schema comes from a vendored copy of
  `cf_tick_schema.json`, through conda-smithy's own `CONDA_SMITHY_BOT_SCHEMA_URI` override. The hints lookup returns
  an empty hints table. It cannot return `None`, conda-smithy's own answer when the fetch fails: 3.62.0 then reads
  `{}.get("hints", [])` and raises `AttributeError` for any recipe with requirements. The suite passes with the network
  blocked. The trap matches `githubusercontent.com` too, and a `network`-marked test compares the vendored schema with
  upstream.
  **Constraints:** tests only: CFE's validator keeps calling conda-smithy's real lint at runtime, against the live
  schema. Validation against the vendored copy still rejects a malformed `bot` block. The change lands in one
  `retro(cfe):` commit with a CHANGELOG PATCH bump (AD-15). It is a fix: no flag and no new CAP. Same class as Story
  26.1, under CAP-34. Owner: mason. → Epic 26 / Story 26.2, specced 2026-10-22.
- **2026-10-25 (the PRD's section 4.7 arrows were mapped by section, not traced) — Found: three of the mason
  PRD's FR arrows name the wrong capability.** A fleet audit of every station PRD's `FR-n ← CAP-m` arrows, run after
  marshal Story 105.1 found marshal's counted rather than traced, read all 57 mason arrows. The 2026-09-17 fold
  (`e062c19c9d`) gave every FR in § 4.7 "Seam enforcement" the arrow `← CAP-7`. That is right for FR-42..FR-47 and
  wrong for FR-48 (the configuration surface), FR-49 (logging and child output) and FR-50 (rehearsal before an
  irreversible publish), which PRD revision 2 added to that section. Doctor's `fr-without-cap` only checks that a cited
  CAP exists, so nothing noticed. **What it looks like when fixed:** FR-48 reads CAP-5, CAP-1 (the CLI shell; the CFE
  root, interpreter and timeout knobs); FR-49 reads CAP-5, CAP-2 (stdout carries one JSON document; a build streams its
  child output); FR-50 reads CAP-3 (a rehearsal publish must pass before the irreversible one). **Constraints:** a
  chore under `spec-one-chain-per-station` CAP-5 (FRs derive from CAPs) and CAP-3 (the station fold procedure); no CAP,
  no flag, no `SPEC.md` change; no detector rule changes. Operator ruling, 2026-10-25: "Do rows 1-5 in one PR". Owner
  `spec-pyforge-mason`. → Epic 32 / Story 32.1, specced 2026-10-25.

## One-chain fold — 2026-09-17

Station Dream status is `specified` (Spec `spec-pyforge-mason` is `ready`). Mason-owned satellite Dreams archive in place with Consolidated-into banners. Practice Dream `packaging-factory` is archived into this station Dream (CHAIN-STANDARD precedence; no new station Dream minted). Recipe work stays `conda-forge-expert`; this fold is planning-chain only.
- **2026-10-26 (every requirement derives from a capability) — Found:** the 2026-09-17 fold cut 8 of the Spec's intent and success bullets at their first line, and none of the 16 NFR lines cites a capability. **Ruled** (2026-10-26, operator, fleet-wide: "yes forbid it" — a requirement cites one or more defined capabilities and nothing else; `spec-one-chain-per-station` CAP-5 as amended, CHAIN-STANDARD § 12). **For mason:** the text is restored by script from `e062c19c9d^` with every id stable; the NFR backfill is minted `backlog` as Story 33.2 (ruling (c)) so the detector baseline has an owner for every mason row it carries. Epic 33 / Story 33.1, built in the one-PR effort with the other seven stations; no mason CAP minted, no requirement changes.
- **2026-10-26 — Fixed: the atlas's dependency graph and bot health read the conda-forge bot's split repos again.**
  A local `pr-preflight` failed `test_atlas_clis_smoke.py::test_whodepends_reverse_json`, and the same test failed in a
  second worktree the same day: `whodepends python --reverse` returned no rows. Every local `cf_atlas.db` had 0 rows in
  `dependencies`, although the build metadata listed every phase as run. The cause is upstream. GitHub now
  301-redirects `regro/cf-graph-countyfair`, the repo the atlas downloads, to `conda-forge/conda-forge-bot-data`, and
  that archive holds none of the bot's graph. cf-scripts publishes the graph as four repos:
  `conda-forge/conda-forge-bot-data-node_attrs`, `-pr_info`, `-version_pr_info` and `-pr_json`. The download still
  succeeded, so nothing failed. Phase J, the writer of `dependencies`, wiped the table and committed 0 edges without a
  warning. Phases E and M and Phase H's cf-graph mode read nothing. pyforge-atlas ported its own reader on 2026-10-18
  (atlas Story 34.3); CFE's `conda_forge_atlas.py` was never ported. Phase J also never wrote a `test` edge: the bot
  keeps test requirements in the recipe's test section (v0 `test.requires`, v1 `tests[].requirements`), and the phase
  read `requirements.test`.
  **What it looks like when real:** Phase E fetches the four split archives and checks each one's top directory
  before it replaces the cache, so a redirect to another repo cannot replace it. Phases E, H, J and M read the split
  records, and Phase M resolves live bot PRs through `-pr_json`. A source with no record never replaces data: Phase J
  keeps its table and the others write nothing, and each says why. Phase M also writes nothing from a partial set of
  its three sources. `whodepends --reverse` answers again, `--type test`
  answers for the first time, and the smoke test skips, naming the rebuild, on a checkout whose table is still empty.
  **Constraints:** `.claude/skills/conda-forge-expert/` only: CFE scripts, tests and docs, in one `retro(cfe):` commit
  with a CHANGELOG MINOR bump (AD-15), because the change adds gotcha G123. No pyforge-atlas, `pixi.toml` or `recipes/**`
  change. A fix under CAP-24 (atlas intelligence: "what depends on it"): no flag and no new CAP. Owner: mason.
  → Epic 34 / Story 34.1, specced 2026-10-26.

## 2026-10-26 — Rebuild conda-forge-expert as a Skill-Forge-authored skill, slice by slice (folded from conda-forge-expert-rebuild)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 35.1). The body below is `docs/dreams/conda-forge-expert-rebuild.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/conda-forge-expert-rebuild.md`.*

## Rebuild conda-forge-expert as a Skill-Forge-authored skill, slice by slice

### The Dream

`conda-forge-expert` — the ~41,410-LOC skill that has carried this repo's entire recipe
lifecycle (generate → validate → build → submit) since it began, encoding 106 gotchas and 10
hard constraints earned the hard way, one build failure at a time — gets rebuilt, not wrapped.
Not the whole thing at once, and not by hand: `skf-*` (Skill Forge, already installed in this
repo's `.claude/skills/`) does the compiling, slice by slice, along the skill's own existing
3-tier seams (recipe-authoring, atlas-intelligence, project-scanning), with `skf-campaign`
orchestrating the sequence and `skf-audit-skill` proving each slice is drift-free once it lands.

This explicitly reopens [[pyforge-mason]]'s D-1 ("wrap, never fork the craft") — but only for
CFE itself, not for Mason. Mason's own wrap decision doesn't need to change: `mason recipe`
shells out through `cfe.py` to whatever lives at the CFE root, and as long as this rebuild
preserves compatible entry points, Mason keeps working through the transition unmodified.
This is a standalone effort, motivated by the same underlying wish Mason's D-1 already weighed
and rejected once — and the user chose to reopen it anyway, with eyes open about why it was
rejected the first time.

**The precedent this Dream has to answer to, explicitly:** `pyforge-atlas` took the "extract
and re-implement" path once already, in this exact repo. 80 files / 14,461 src LOC + 110 files
/ 14,682 test LOC, 32 stories, PRs #58–#105 all merged — and the legacy `conda_forge_atlas.py`
(8,902 LOC) is *still the live runtime*. Every `build-cf-atlas` / `atlas-phase` /
`query-cf-atlas` task and every atlas MCP tool still shells out to the old path. Nothing routes
to `pyforge.atlas`. ~29,000 lines did not displace the original, because the rebuild had no
migration step — Mason's own D-1 rationale names this as reason #2 of three independent,
each-sufficient reasons not to rebuild CFE the same way.

This Dream exists specifically to not repeat that outcome: the user chose full scope (rebuild
all 30+ MCP tools and scripts, not a narrow pilot) but paired it with **hard cutover per
slice** — every rebuilt capability retires its old CFE path, redirects every caller (pixi
tasks, the MCP tool registration, Mason's own `cfe.py` port), in the *same* migration story
*(historical framing — the cutover shape was re-decided 2026-08-10 to parallel-run with a
detector-enforced end cutover; see the Realization log)*
that builds it, never a separate future effort. That pairing is the whole bet: broad scope,
but no slice is allowed to become a second, unused ~29,000 lines.

### What it looks like when real

- CFE's existing 3-tier architecture (recipe-authoring, atlas-intelligence,
  project-scanning/MCP layer — see `.claude/skills/conda-forge-expert/SKILL.md`) is sliced
  into Skill-Forge-sized units, each with a Brief.
- `skf-analyze-source` run against the existing skill confirms or corrects the slicing before
  any Brief is written — the boundaries come from what's actually there, not a guess.
- Per slice: `skf-create-skill` compiles the replacement → a migration story in the *same*
  epic redirects every caller (pixi tasks, `.claude/tools/conda_forge_server.py`'s MCP tool
  registrations, Rule-1/Rule-2 references, Mason's `cfe.py` port) from the old path to the
  new one → the slice is equivalence-proven against the live original (removal happens at the campaign-end cutover) → `skf-audit-skill`
  confirms zero drift.
- `skf-campaign` tracks the whole multi-slice sequence with file-based state and resume, so
  the effort survives across sessions the way `bmad-loop` runs do for other stations.
- At the end: no `.claude/skills/conda-forge-expert/` code path is dead weight sitting next to
  a newer, unused replacement — every parallel slice is continuously equivalence-checked, and the end cutover is detector-enforced, never hoped for.
  The 106 gotchas and 10 constraints are carried forward into the new skill's own briefs, not
  re-derived from scratch and not lost.
- Rule 1 (SKILL.md is authoritative) and Rule 2 (every conda-forge effort ends with a retro
  that improves the skill) continue to apply to whatever replaces CFE — this Dream does not
  reopen *those* rules, only the wrap-vs-build seam for CFE's own implementation.

### What is real

Specified 2026-08-10 (Spec ready, Epic 6 decomposed to the re-scope gate). Originally a `dreamt`-stage placeholder, captured at the moment the decision
to reopen D-1 was made explicitly, with the scope and cutover-discipline questions already
answered (see Realization log) — the next step was a Spec — now in place; the pilot slice is the next code.

### Constraints

- **Parallel-run with a detector-enforced end cutover (re-shaped 2026-08-10, operator override; was: hard cutover per slice).** No slice's migration story may be deferred to
  "later" — this is the one discipline atlas's rebuild lacked, and it is the entire reason
  this Dream is structured the way it is.
- **Mason's own D-1 is untouched.** `mason recipe`'s wrap-by-subprocess design does not change;
  this rebuild only changes what's *at* the CFE root, not how Mason reaches it. If entry
  points drift incompatibly, that's a defect in this Dream's execution, not a license to also
  reopen Mason's architecture.
- **No knowledge loss.** The 106 gotchas and 10 constraints currently living in CFE's
  `SKILL.md`/`reference/`/`guides/` are inputs to each slice's Brief, not something
  Skill Forge re-discovers from scratch.
- **Rule 1 / Rule 2 continue to bind** whatever skill(s) replace CFE.

### Non-goals

- Not a change to Mason's PRD, architecture, or Epic 5 ("Prove the seam holds") — those stay
  exactly as specified; Epic 5 keeps proving Mason's wrap against whichever CFE is live.
- Not a big-bang single cutover — full scope was chosen, but delivered as a sequence of
  independently-complete slices, each with its own proof.

### Kinships

[[pyforge-mason]] (the D-1 decision this Dream reopens, for CFE only — not for Mason itself) ·
[[packaging-factory]] (the practice CFE has always served; this Dream rebuilds the tool, not
the practice) · [[pyforge-atlas]] (the rebuild-with-no-migration cautionary tale this Dream is
structured specifically to not repeat).

### Realization log

- **2026-08-07** — Dream captured. User asked whether Mason should rebuild conda-forge-expert
  via `bmad-builder`/Skill Forge; clarified that Mason's own D-1 explicitly decided the
  opposite (wrap, never fork) for exactly this reason, citing the atlas precedent (~29,000
  rebuilt lines never displaced the original 8,902-line legacy runtime) and CFE's own moat (106
  gotchas, 10 constraints) as the cost of forking. User confirmed they want to reopen D-1
  anyway, for CFE specifically (not Mason). Asked to choose rebuild scope and cutover
  discipline before any plan was drafted: user chose **full scope** (all 30+ MCP tools and
  scripts, not a narrow pilot) paired with **hard cutover per slice** (every slice's migration
  lands in the same epic that builds it — explicitly rejecting the "build everything, migrate
  later" shape that produced atlas's outcome). This Dream captures that decision *(the cutover half re-decided
  2026-08-10 — parallel-run, enforced endgame; see the Realization log)*; the Spec now
  exists and Epic 6 decomposes the pilot.

- **2026-08-10** — Specified, by operator directive during the mason correct-course
  session: *"the current conda-forge-expert skill is unsustainable — we rebuild and shift
  to using the mason rebuilt version."* AD-15 amended to sanction the rebuild as the CFE
  surface's writer under this Spec's gates; mason Epic 6 decomposes the pilot slice through
  the re-scope gate (6.1-6.4) and no further — the remaining slices decompose only from
  6.4's recorded decision.
- **2026-08-10 (later)** — Cutover shape decided by the operator, concern raised and
  overridden: **parallel-run both, cut over at the end** (not per-slice cutover). The atlas
  precedent was on the table; the decision is survivable only with the three CAP-3
  mitigations (equivalence harness, dual-landing, detector-enforced endgame), now the
  Spec's contract. This Dream cannot read `realized` until the end cutover completes.

- **2026-09-09** — **Endgame declared over slices 1–2; the campaign closes there** (operator
  ruling, `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`
  § 2.3 **C2**). The re-scope gate CAP-4 exists for finally got its price tag, and the answer
  was *stop*: the cost is **recurring**, not one-time — every CFE release became a byte-re-port
  obligation into two mirrors (23 qualifying retro commits in the campaign range; both re-scope
  gates returned `adjust`, never `go`) for **zero** behavioural change (no caller had flipped,
  both slices still `compiled`). The premise moved too: `skf-create-skill` compiles the
  **knowledge layer** — both compiled slices are sha256-identical copies of the live scripts, and
  every drift was closed by porting live source in, never by re-compiling — so "Skill-Forge-authored"
  describes a Forge-authored brief + audit harness around an unmodified code copy, and the
  unbriefed slices would buy briefs, not better code. Slice 3 (atlas-owned under Story 12.5,
  12.3× slice 1) and slice 4 are **not briefed and will not be**. Deprecation posture for the long
  tail: **delete-on-cutover, no stubs** — Mason reaches CFE by filesystem path, not by import, so a
  stub module cannot serve a path resolver and CAP-5's degradation path already handles a missing
  root. `campaign-state.yaml` now reads `endgame_declared: true`; mason **Epic 15 / Story 15.1** is
  the closing story (cut the two slices' callers over or retire the mirrors, keep
  `cfe-rebuild-guard-check` clean), and it must land **before** steward S-44.6 moves the CFE cell to
  `skills/domain/conda-forge-expert/`. This Dream still cannot read `realized` — the end cutover has
  not completed; what changed is its **scope**, from five slices to two.

## 2026-10-26 — copilot-cli on conda-forge — blocked at the license (folded from copilot-cli-packaging)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 35.1). The body below is `docs/dreams/copilot-cli-packaging.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/copilot-cli-packaging.md`.*

## copilot-cli on conda-forge

### The Dream

Package GitHub's **Copilot CLI** for conda-forge so the agent tooling the
factory itself leans on could be installed the same way everything else is.

### Why it was archived

**Blocked, and not by anything we can fix.** `LICENSE.md` §2 forbids standalone
redistribution — precisely what a conda package is. staged-recipes **#32522** was
rejected on that clause. No recipe change resolves it; only an upstream
relicense would, and that is not ours to make.

`recipes/copilot-cli/` remains on disk as a **local-only** recipe: it builds and
installs here, and it must never be submitted. The archive entry exists so the
next person to notice the directory does not re-litigate a settled rejection.

### Kinships

[[packaging-factory]] (the practice) · [[enterprise-airgap]] (the class of
license constraint that decides what may be mirrored at all).

### Realization log

- **2026** — staged-recipes #32522 rejected on the LICENSE.md §2 clause.
- **2026-07-25** — **ARCHIVED (blocked)** during the Dream-lifecycle
  reconciliation; formerly a hardcoded console entry with no Dream file behind it.

## 2026-10-26 — DB-GPT on conda-forge — the multi-output agent stack (folded from db-gpt-packaging)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 35.1). The body below is `docs/dreams/db-gpt-packaging.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/db-gpt-packaging.md`.*

## DB-GPT on conda-forge

### The Dream

Get **DB-GPT** — an agentic data application framework with a large native
dependency closure — installable from conda-forge, along with the five
prerequisites it needed that nobody had packaged.

### Why it was archived

**Terminal: delivered, but not by us.** All five prerequisites we authored
merged. DB-GPT itself arrived through an *independent* submission
(staged-recipes **#33883**, 8 outputs including `dbgpt-acc-flash-attn`) that
consumed our patches — so the outcome landed while our own submission became
redundant. Per the consume-not-submit rule (CFE **G58**: check
`lookup_feedstock` before submitting), the correct move was to stand down rather
than open a competing PR. `recipes/db-gpt/` mirrors the merged shape (v0.8.1,
green 8/8) for local use.

This is a **success recorded as an archive** — the dream was realized, the
effort was not.

### Kinships

[[packaging-factory]] (the practice) · [[pyforge-mason]] (the station).
Spec: `docs/specs/db-gpt-conda-forge.md` (TERMINAL — do not re-run BMAD on it).

### Realization log

- **2026-07-01** — all 5 prerequisites merged; db-gpt delivered via #33883.
- **2026-07-25** — **ARCHIVED (terminal)** during the Dream-lifecycle
  reconciliation; formerly a hardcoded console entry with no Dream file behind it.

## 2026-10-26 — A Django-service scaffolding engine, if this repo ever births new Django-based stations (folded from django-accelerator-framework)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 35.1). The body below is `docs/dreams/django-accelerator-framework.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/django-accelerator-framework.md`.*

## A Django-service scaffolding engine, if this repo ever births new Django-based stations

### The Dream

The source dream's actual subject — a FreeMarker-templated, three-repo pipeline stamping out
production-ready Django services (OIDC, DRF, Celery, Helm/CD) from a continuously-maintained
sample app — solves "teams keep hand-building the same Django scaffolding." This repo has exactly
one Django-backed surface today (Steward's dashboard app, Story 9.1+), hand-built once, not
repeatedly re-scaffolded across many services. There is no current pattern of "a new Django
service is needed" recurring often enough to justify a dedicated stamping-out engine. Captured
for parity, not because a real gap exists.

### What it looks like when real

Left thin — no scoped feature, because the premise (repeated Django service scaffolding) doesn't
recur here yet:

- IF this repo ever needs a second, third, or Nth Django-backed station beyond Steward's
  dashboard, revisit whether a scaffolding engine earns its keep at that point — one hand-built
  Django app doesn't justify a templating pipeline; three or four might.
- The one concretely useful idea independent of that premise: whatever Steward's dashboard app
  already got right (OIDC-equivalent identity-at-the-boundary via `middleware.py`, the
  adopter-declaration schema in `declarations.py`) is the reference a second Django surface should
  copy from directly, not from this WF source's own FreeMarker templates.

### What is real

Nothing — this repo has one Django surface (Steward's dashboard), hand-built, no scaffolding
engine, no recurring pain from lacking one.

### Constraints

- **Not to be built until a second Django-backed station is actually planned.** One data point
  (Steward's dashboard) is not evidence of a recurring pattern.

### Non-goals

- **Not FreeMarker or a three-repo template pipeline** — no evidence this repo's own scaffolding
  needs, if they ever exist, would look like WF's specific tooling choice.
- **Not runtime application logic** — carried from the source dream's own non-goals unchanged
  (moot, but recorded for parity).

### Full feature audit against `django-accelerator-framework`

| Source feature | Disposition | Why |
|---|---|---|
| Three-repo FreeMarker template pipeline | **Omitted, no target** | No recurring Django-scaffolding need exists to justify a templating engine. |
| OIDC auth, group-based RBAC, 15-min session idle timeout | **Pattern noted, partially already-realized differently** | Steward's dashboard already solved the adjacent "identity at the boundary" problem (`middleware.py`) with its own, narrower design — not this source's OIDC-specific shape, but covering the same underlying concern for the one Django surface that exists. |
| DRF + JSON:API, FastAPI demo mount | **Omitted, no target** | Nothing currently needs a second API surface. |
| Celery + Redis, django-health-check | **Omitted, no target** | No background-job or health-check need identified beyond what Doctor's own fleet-health role already covers differently. |
| structlog/django-structlog + OpenTelemetry | **Omitted, no target** | This repo has its own structured-logging conventions already, unrelated to Django specifically. |
| pytest + behave-django, Ruff/MyPy/pre-commit | **Already this repo's own convention** | Not something to port — pytest + Ruff + pre-commit discipline already applies repo-wide, Django-backed or not. |
| Dockerfile + Helm + Harness CD | **Omitted, no target** | See [[pixi-container-image]] and [[reusable-cicd-workflows]] — no containers, no Harness. |

### Kinships

[[pyforge-steward]] (owns the one real Django surface this Dream would draw its actual local
precedent from, not the source's own FreeMarker sample app) · [[pixi-container-image]] and
[[reusable-cicd-workflows]] (siblings sharing the same "no current target" disposition) ·
[[pyforge-mason]] (nominal owner by the source label; genuinely unclaimed)

### Realization log

- **2026-08-14** — Dream captured while porting a sibling org's dream catalog for PyForge fit.
  Checked this repo's actual Django footprint before drafting — exactly one hand-built surface
  (Steward's dashboard, Story 9.1+), not a recurring scaffolding pain. Kept intentionally thin;
  noted that Steward's own `middleware.py`/`declarations.py` design is the real local reference a
  second Django surface should copy, not this source dream's FreeMarker tooling.
- **2026-08-14** — **Activation trigger recorded (operator direction):** the Django/Langflow/DB-GPT family is to build on a cookiecutter-django Django service WITH FastAPI integration **based on this dream** — the engines joining as pluggable Django applications ([[langflow-django-plugin]] / [[db-gpt-django-plugin]]), on PostgreSQL + Redis + Kubernetes. This is the concrete second-Django-surface signal this dream's own Constraint was waiting for, affirmed by the operator rather than inferred. Stays `dreamt` only until the family's subject project is named; at that intake this dream is the basis and should be spec'd with (not after) the family.
- **2026-08-14** — **Air-gapped realization requirements (operator, from the source original
  django-accelerator-framework.md):** the source accelerator treats the private network as ground
  truth — Artifactory coordinates are first-class template substitutions stamped into
  `pyproject.toml`, `pixi.toml`, Helm charts, CI workflows, and the conda recipe of every
  rendered service, and the pipeline publishes to Artifactory and deploys to OpenShift. The
  cookiecutter-django + FastAPI host recorded above must carry the same posture from its first
  render: (1) template renders parameterize the mirror endpoints so every pip/conda/pixi install
  in a generated service resolves from Artifactory-mirrored indexes only (pixi channels swappable
  to internal mirrors, as this repo already practices); (2) frontend assets follow the source's
  Bootstrap 5.3 + HTMX + Django Compressor shape — vendored and bundled locally, served
  WhiteNoise/`collectstatic`-style, zero CDN `<script>`/`<link>` references in base templates
  (the CAP-4 CDN-rewrite precedent from spec-atlas-query-dashboards applies at template-authoring
  time, not as a later patch); (3) all runtime config flows through the source's
  `env()`-helper/split-settings pattern — DB, Redis broker, OIDC endpoints, and secret keys via
  env/secret mounts, never committed, matching `_http.py`'s env-only enterprise routing;
  (4) auth binds to an internal OIDC IdP (the source uses PINGi via django-allauth; form login
  only in DEBUG) — no external identity callbacks; (5) deployment per the
  K8s/OCP+PostgreSQL+Redis decision: images pulled from an internal registry, `/ht/`
  django-health-check endpoints wired to K8s liveness/readiness probes, Celery's Redis broker
  in-cluster. Python 3.14 compatibility is orthogonal but constrains which mirrored package
  versions the template may pin.
- **2026-08-14** — **Subject project NAMED: [[python-agent-platform]]** (operator). The family's last precondition is met — the subject Dream and its family Spec (spec-python-agent-platform, pyforge-steward) consolidate all four same-day operator decisions plus the spike evidence; this dream's remaining role is the decision trail and its named pattern contracts.
- **2026-08-14** — Spec authored (spec-django-accelerator-framework, pyforge-mason) closing the "spec'd with the family" obligation: CAP-1 = the accelerator contract (first realization: python-agent-platform's src/platform render, Story 10.1; second reference: steward's dashboard); CAP-2 = the templating engine, explicitly parked on the dream's own third-surface trigger.
- **2026-09-09** — **Archived, absorbed** (operator ruling,
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`
  § 2.3 **C3**). CAP-2's third-surface trigger is **retired**, not scoped: the estate reached
  **nine** Django faces and never repeated the hand-copy the trigger watched for. Instead of a
  FreeMarker-style stamping engine it factored a declarative base class —
  `django_pyforge.portals.PortalConfig` (`src/shared/packages/django-pyforge/`), subclassed by
  eight station portals with ~10 declarative fields each
  (`src/shared/packages/django-mason/src/django_mason_portal/apps.py:6-21`) and mounted into the
  **one** project at `src/platform/config/settings/base.py:27-41,165-183`. The surface count never
  passed two (`find src -name manage.py` → `src/platform/manage.py` only); steward's dashboard is a
  Django *app* on its own daphne/nginx perimeter, not a second render. Counting surfaces —
  repo-wide or estate-wide — measured the wrong thing. CAP-1's accelerator contract moves to
  **`spec-pyforge-unifying-strategy`**'s Lane-2 section, where the living exemplar it must not
  drift from actually lives (not `spec-python-agent-platform`, which steward Story 48.8
  supersedes); CAP-1's evidence was in any case already stale in the mason copy (`SPEC.md:35`
  cites `config/urls.py:26 include("health_check.urls")`, while the live route is
  `src/platform/config/urls.py:98` via an explicit `HealthCheckView`, with `:50-55` recording the
  `include(...)` form as **deprecated**). This Dream's residual value is its decision trail. The
  Unifying Dream's "Lane 2 portal scaffolding" Kinship (`pyforge-unifying-strategy.md:669`) is
  satisfied by the shipped portals. The Spec's `src/platform/**` surface glob is dropped —
  it dual-governed `src/platform/deploy/DR.md` with a steward spec (an INV-2 smell
  `spec-surface-check` reported under both). Mason never had an epic or a story for this Dream;
  the Dream's own Kinships called mason *"nominal … genuinely unclaimed."*

## 2026-10-26 — Fleet stewardship — tend every feedstock we can touch (folded from fleet-stewardship)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 35.1). The body below is `docs/dreams/fleet-stewardship.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/fleet-stewardship.md`.*

## Fleet stewardship — 769 feedstocks, none left behind

### The Dream

*(Naming: this practice Dream — feedstock tending under Mason + Doctor — is
distinct from the **Steward persona**, the platform/ops station:
[[pyforge-steward]].)*

Maintainership as a *practice*, not a backlog: every feedstock this factory can
modify is kept current with upstream, on the modern recipe format, built for
every platform its users need — and when CI goes red anywhere in the fleet, a
disciplined remediation loop turns it green again. A **perpetual** dream:
realized as recurring waves, never finished.

### What is real (the three workflow engines)

- **`feedstock-refresh`** — the two-track bulk refresh of ALL 769 modifiable
  feedstocks: Track A (sole-maintainer, 537; waves B–F shipped, Wave H
  total-coverage open) and Track B (co-maintainer, 232; adds etiquette rules).
- **`feedstock-platform-expansion`** — the per-feedstock dual-goal workflow:
  latest CFE shape at latest upstream + widened build matrix (osx-arm64,
  linux-aarch64) in one PR.
- **`feedstock-failure-remediation`** — the red-PR loop: triage
  FLAKE / REAL_FIX / BLOCKED, execute-locally-first, maintainer-edit push,
  rerender-after-push.
- The sibling **conda-forge-tracker** repo (markdown-first personal tracker) and
  the atlas-derived maintainer lists on `rxm7706/about`.

### The frontier

- Track A Wave H (179 feedstocks remaining); Track B execution.
- Signal-driven scheduling: let [[pyforge-doctor]]'s pulse (staleness, CVE,
  abandonment) *order* the waves instead of alphabetical sweeps.

### Realization log

- **2026-06 → 07** — waves B–F shipped; the 12-PR remediation batch (G31–G34)
  became the workflow's worked example.
- **2026-07-23** — Dream retro-seeded; engines live as timeless workflow specs
  (legacy tier), powered by [[packaging-factory]] intelligence from [[pyforge-atlas]].
- **2026-09-09 (realization-gate re-read)** — `realized` **holds**, with a dated dormancy note
  (operator ruling,
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`
  § 2.2). CAP-1 (local-mirror-first) and CAP-2 (`cfe-*` metadata) are exercised **continuously**:
  70 commits touching `recipes/` since 2026-08-10 across a 7,873-directory tree. **CAP-3 — the
  recurring campaigns — is dormant.** All three engine specs are untouched since 2026-06/07
  (`feedstock-refresh.md` last commit `1aeaf12cee` 2026-07-02; `feedstock-platform-expansion.md`
  `1bdd5a2f02` 2026-06-28; `feedstock-failure-remediation.md` `1aeaf12cee`), Track A Wave H still
  lists **179** remaining and Track B (**232**) is unstarted. Recorded so "recurring waves" is not
  read as live — the status is defensible, the narrative was not. **Greenfield note:** steward
  S-44.8 moves only in-flight and sole-maintainer recipes to `factory/recipes/`; every other
  `recipes/**` row reads `stays` and is **archived with `local-recipes`**. This Dream's CAP-1
  surface is `recipes/**` (`surface-drift: exempt`), so after the cutover most of that surface
  lives in an archived repo — which changes what "every feedstock we can touch" can mean. Neither
  this Dream nor its Spec anticipated it; consult at 44.8, not after.

## 2026-10-26 — The CFE failure catalog is generated from the skill spec, every row lint-verified against its enforcing check (folded from machine-checked-recipe-knowledge)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 35.1). The body below is `docs/dreams/machine-checked-recipe-knowledge.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/machine-checked-recipe-knowledge.md`.*

## Machine-checked recipe knowledge

### The Dream

The conda-forge-expert skill's largest asset — 110+ numbered gotchas and the
Build Failure Protocol — is prose. Nothing links a gotcha to the check that
enforces it, so knowledge and enforcement drift silently. The dream: a
failure catalog GENERATED from the skill's own text, one row per failure
class, each carrying greppable symptom signatures and an `enforced_by:`
pointer lint-resolved against the real check surface — with
`enforced_by: null` an explicit, machine-readable automation backlog, and
catalog↔spec drift failing CI.

### Grounding

Proven in the wild by OpenTeams auto-recipe (2026-08-22 seven-repo analysis,
`archive/docs/intake/external-repos-analysis-2026-08-22/`): 45-row
`failure-catalog.yaml` generated from its 980-line spec, lint-resolved
against `verify --list-checks`, "when the two disagree, the spec wins and
the code is wrong." That repo is unlicensed/private — the PATTERN is
adopted; no text or YAML is copied. Locally the fit is exact: the G-corpus
lives in SKILL.md, the check surface in the CFE verify/test machinery, and
the bmad-drift-check philosophy (detector + reconciler + baseline) is the
same shape one level up.

### What it looks like when real

`catalog.yaml` derives from SKILL.md's gotchas; every row names symptom
tokens + its enforcing check (or null); a lint resolves each pointer against
the live check registry; CI reds on drift either way; the null-rows report
IS the prioritized backlog for new checks.

### Constraints / Non-goals

Doctor supplies the drift-lint surface (detector convention), mason owns the
catalog + generation; no verbatim import from auto-recipe (no license);
not a rewrite of the G-corpus — the prose stays authoritative, the catalog
derives. Rule 1/2 apply (CFE surface).

### Kinships

CFE SKILL.md G-corpus · bmad-drift-check (the detector philosophy) ·
`spec-conda-forge-expert-rebuild` (mason's CFE campaign) · the intake report.

### Realization log

- **2026-08-22** — Seeded from the seven-repo external analysis (`f0c695758c`);
  `spec-machine-checked-recipe-knowledge` derived under pyforge-mason and decomposed into the
  station backlog the same day (`a20192dd84`). Spec status `ready`.
- **2026-09-09** — **Realized, and exercised** (operator ruling,
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`
  § 2.2). `config/failure-catalog.yaml` (117 rows) derives from `SKILL.md`'s gotcha corpus via
  `scripts/failure_catalog_generator.py`, is guarded for freshness by
  `tests/meta/test_failure_catalog_freshness.py` (green), and is independently re-resolved by
  `scripts/failure_catalog_check.py` (`DETECTOR = {"scope": "repo"}` at `:41`, auto-discovered by
  `scripts/detectors.py`) — `pixi run -e local-recipes failure-catalog-check` reports **clean**.
  The Spec flips `ready → shipped` and finally declares its own detector in `surface:`. The
  null-rows backlog is real and large: **115 of 117 rows carry `enforced_by: null` — coverage
  1.7 %**. That number is *emitted on every run* and nobody watches it; raising it is the
  backlog's job, not this Dream's — the Dream's contract was that the number exist and that
  drift be impossible to land silently, and both hold. The Dream's own open question (catalog
  home: `config/` vs `data/`) is settled exactly as it predicted — it landed in `config/`,
  because the artifact is derived-and-tracked.

## 2026-10-26 — A custom-branded Python distributable, if this repo ever needs one (folded from miniforge-installer)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 35.1). The body below is `docs/dreams/miniforge-installer.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/miniforge-installer.md`.*

## A custom-branded Python distributable, if this repo ever needs one

### The Dream

The source dream's actual problem — developers and CI agents getting Python from three divergent
per-platform paths, none of them locked to an org's own Artifactory-only conda channels — doesn't
exist here. This repo's own `pixi.toml` already declares public channels directly
(`conda-forge`, `SelfExplainML`), with no Artifactory-only constraint to route around and no
divergent per-platform install story to unify — every contributor and every CI runner already
gets Python the same way, through pixi, from the same public channels. Captured for parity, not
because a real gap exists.

### What it looks like when real

Left thin — no scoped feature, because the premise (an org needing to lock its own custom Python
distributable to a private channel) doesn't hold here:

- IF this repo (or a future enterprise deployment of it, per [[enterprise-airgap]]) ever needs a
  Python distribution locked to a private/mirrored channel set, the source dream's
  Conda-Constructor-based build shape is a reasonable pattern to reach for — but that's
  [[enterprise-airgap]]'s own concern to raise if it ever becomes real, not something to
  pre-build here speculatively.

### What is real

Nothing built or missing. `pixi` itself, installed directly per this repo's own
[[developer-machine-bootstrap]] (also just captured, also aspirational), already serves the role
a custom Miniforge distributable would serve here — one consistent way to get a working Python
environment, for every contributor and every CI runner alike.

### Constraints

- **Not to be built until a private-channel-locking need is real.** [[enterprise-airgap]] is the
  Dream that would surface that need if it ever materializes; this Dream should not get ahead of it.

### Non-goals

- **Not an alternative to `pixi`** — this repo's existing Python-provisioning story (pixi itself)
  already solves what this Dream's source solves differently.
- **Not multi-platform installer engineering** (Docker+QEMU cross-builds, Gradle orchestration)
  — no target to build for.

### Full feature audit against `miniforge-installer`

| Source feature | Disposition | Why |
|---|---|---|
| Custom-branded `Miniforge3_WF` installer | **Omitted, no target** | `pixi` already serves this repo's equivalent role; no private-channel-locking need exists. |
| `construct.yaml` (Conda Constructor blueprint) | **Pattern noted, no target** | Reasonable IF a private-channel need ever materializes via [[enterprise-airgap]]; not built speculatively. |
| CVE-pinned package patching | **Omitted, no target** | Nothing to patch without a distributable to patch. |
| Multi-platform build matrix (Linux x86_64/aarch64, macOS x86_64/arm64, Windows) | **Omitted, no target** | Same. |
| Gradle build system + dual CI (Jenkins + GitHub Actions) | **Omitted, WF-infrastructure-specific** | No Jenkins presence in this repo. |

### Kinships

[[enterprise-airgap]] (the Dream that would actually surface a private-channel-locking need, if
one ever becomes real) · [[developer-machine-bootstrap]] (the sibling Dream this one's role
already substantially overlaps with, via plain `pixi`) · [[pyforge-mason]] (nominal owner by the
source label; genuinely unclaimed)

### Realization log

- **2026-08-14** — Dream captured while porting a sibling org's dream catalog for PyForge fit.
  Checked `pixi.toml`'s own channel declaration directly before drafting — confirmed public,
  unlocked conda-forge channels with no Artifactory-only constraint this dream's source solves
  for. Kept intentionally thin; the more honest home for this concern, if it ever becomes real, is
  [[enterprise-airgap]], not a new standalone Dream.

## 2026-10-26 — The Packaging Factory (folded from packaging-factory)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 35.1). The body below is `docs/dreams/packaging-factory.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/packaging-factory.md`.*

## The Packaging Factory — every library, packaged before you ask

> **Scope note (2026-07-25):** this is the **practice** Dream — the perpetual
> conda-forge factory and its craft-skill. Mason **the station** (the Smith and the
> `mason` CLI) now has his own charter: [[pyforge-mason]].

### The Dream

**The origin dream of this repository**: an AI-assisted, semi-autonomous packaging
factory for conda-forge — Mason's domain. A machine that takes any upstream
(PyPI, npm, CRAN, CPAN, LuaRocks, GitHub) and carries it through the entire
recipe lifecycle — generate, security-scan, build, debug, submit, maintain —
with a human steering intent, not syntax. Where packaging a library stops being
an afternoon of YAML archaeology and becomes a sentence.

This is a **perpetual** dream: realized as a running factory, never "done."

### What is real

- The **`conda-forge-expert` skill** (v8.90.1): the 9-step autonomous lifecycle
  loop, build-failure protocol, **117 gotchas (G1–G117)**, the retro system that
  makes every effort improve the skill (CLAUDE.md Rule 2).
- **769 feedstocks** under maintenance; the staged-recipes campaign machinery
  (langflow suite, db-gpt, flyte, mindroom chains).
- The **FastMCP tool surface** (**46 tools**; `docs/reference/mcp-server-architecture.md`) and
  the atlas intelligence layer feeding it ([[pyforge-atlas]]).
- Shipped intelligence releases: `lts-registry-gap`, `seed-gap-suggesters`,
  `cyclonedx-universe-inventory`, the `cfe-shipped-releases` archive.

### The frontier (unrealized aspirations, from the 2026-04-25 roadmap)

- **Multi-ecosystem autotick + scaffolders** — CRAN/npm/cargo updaters and
  `generate_recipe_from_{cran,cratesio,npm}`; the factory is still Python-first.
- **Smart test extractor** — re-run recipe tests against an existing artifact
  without rebuilding (huge for slow C++ packages).
- **Static dependency version checker** — validate version ranges, not existence.

### Graveyard (recorded so it is never re-dreamed ignorantly)

- **copilot-cli** — cannot ship to conda-forge; staged-recipes#32522 rejected on
  LICENSE.md §2 standalone-redistribution. The recipe lives on locally only.

### Kinships

[[pyforge-mason]] (the station that tends this practice) · [[fleet-stewardship]]
(the estate the factory keeps) · [[pyforge-atlas]] (the intelligence that feeds it) ·
[[conda-forge-expert-rebuild]] (the campaign over the factory's own machinery — endgame
declared 2026-09-09 over slices 1–2) ·
**steward Epic 44** (the python-foundry cutover moves this practice's machinery:
`fnd:CAP-3` → S-44.6 *"CFE comes home"* relocates the whole CFE cell to
`skills/domain/conda-forge-expert/`, and `fnd:CAP-6` → S-44.9 *"Mason submits to
conda-forge"* — both carry Mason's Rule 1/2 ACs, both read `blocked` in steward's ledger,
and mason's chain has no counterpart story for either; noted 2026-09-09, decision-batch
D11).

### Realization log

- **2025→2026** — the factory built and operated across hundreds of sessions;
  history lives in the CFE CHANGELOG, the spec archives, and git.
- **2026-07-23** — Dream retro-seeded under the Dream-first model; roadmap
  aspirations folded in as the frontier. Chapters: [[pyforge-atlas]],
  [[pyforge-warden]], [[fleet-stewardship]], [[upstream-discovery]].
- **2026-07-23 (gist audit)** — grounding: the SelfExplainML 36-package channel drop (third-party-channel publishing!) + the rattler-build macOS codesign-stub cross-compile trick (`docs/intake/gists/`).
- **2026-09-09 (currency re-read)** — the practice is the **most actively exercised thing in the
  fleet**, and this Dream's own body had drifted eleven minor versions behind it. Verified live
  against `.claude/skills/conda-forge-expert/` (`conda-forge-expert` invoked per CLAUDE.md Rule 1):
  **v8.90.1** — with *five* releases landing on 2026-09-09 alone — **G1–G117** gotchas, **46**
  FastMCP tools, and **7,873** `recipes/` directories. The "What is real" block above is corrected
  in place (was v8.79.x / ~90 gotchas / 30+ tools). Status stays `realized`; the Spec stays
  `shipped`. Recorded alongside a standing hazard the pass named fleet-wide: stamped literal
  version numbers in companion comments and downstream artifacts cannot keep pace with a skill
  that ships several releases a day — a **derived** pin (read `SKILL.md`'s own `version:`) is the
  durable shape.

## 2026-10-26 — A shared base container image with pixi already installed, if this repo ever ships one (folded from pixi-container-image)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 35.1). The body below is `docs/dreams/pixi-container-image.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/pixi-container-image.md`.*

## A shared base container image with pixi already installed, if this repo ever ships one

### The Dream

The source dream's actual value — every containerized project inheriting one consistent,
credential-safe pixi installation layer instead of each team hand-rolling its own — presupposes
an organization shipping many containers that all need pixi. This repo now ships three (see "What
is real" below), and all three independently converged on the same pixi-materialization discipline
rather than actually inheriting one shared pre-built layer — that convergence is what's real today,
not the shared-layer artifact itself. Mason's own `docker`-mode build path (`cfe.py`'s
`build_docker`) uses Docker as a RECIPE cross-compilation isolation mechanism, not as a shipped
application container — a genuinely different concern this Dream must not be confused with.
Captured for parity originally; partially realized now (see "What is real" and "Constraints") in
the discipline, not yet in a shared base image.

### What it looks like when real

Left thin originally, since no PyForge artifact shipped as a container at the time this Dream was
captured. Three now do (see "What is real"), so the "IF" below has partly resolved — not into a
shared pre-built base image, but into three independently-built images that converged on the same
pixi-materialization discipline and are now held to it explicitly:

- A shared base layer with pixi pre-installed is still the right pattern to reach for IF a fourth
  Containerfile, or a real divergence between the three that exist, ever makes hand-rolling the
  same builder stage three-plus times worth consolidating — this Dream is where that design would
  live; it hasn't been built because it hasn't been needed (see "Constraints").
- Credential handling (build-time secret mount, never baked into a layer) is the one piece that
  didn't wait for a shared base image to become real — it's already true today across all three
  Containerfiles, documented and guarded by
  `docs/reference/container-base-layer-convention.md`, since it's a security discipline, not an
  implementation detail specific to a shared base layer or WF's own Artifactory.

### What is real

The trigger fired. **Four** Containerfiles now ship in this repo's own tracked source:
`Containerfile` (root, Story 7.1), `src/platform/Containerfile` (Story 10.3),
`src/platform/compose/dbgpt/Containerfile` (Story 10.5), and
`src/platform/compose/mcp-host/Containerfile` (spec-mcp-era-isolation slice 1 —
`ghcr.io/prefix-dev/pixi:0.80.0` builder + `registry.access.redhat.com/ubi9/ubi-minimal:9.6`
runtime, no `ENV` credential). All four converged independently on the
same base-layer pattern — a registry-pinned `ghcr.io/prefix-dev/pixi` builder stage plus a minimal
runtime stage, no credential ever baked into a layer or `ENV`. That convergence is now written down
as policy in `docs/reference/container-base-layer-convention.md` and enforced by
`tests/packaging/test_containerfile_base_layer_convention.py` (which sweeps every `FROM`/`ENV` line
across the files it enumerates — three of the four today; see the 2026-09-09 log entry), alongside the pre-existing `scripts/pixi_version_registry.py` (which keeps
the pixi builder-stage tag in sync with `pixi.toml`'s `requires-pixi` floor). Mason's `build_docker`
mode remains the separate recipe cross-compilation concern this Dream never covers — confirmed by
reading `models.py`'s own Story 2.6 documentation before drafting this, specifically to avoid
mistaking the two for overlap.

### Constraints

- **The discipline is real; a repo-owned base image still is not.** The three Containerfiles above
  all build directly `FROM` the upstream `ghcr.io/prefix-dev/pixi` image — none of them, and nothing
  else in this repo, builds or publishes a custom pixi-preinstalled base image.
  `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pixi-container-image/SPEC.md`
  (the spec this Dream produced) keeps it that way deliberately: the official pixi image stays the
  base, and a shipped repo-owned base image stays out of scope until at least two Containerfiles
  diverge for reasons a shared custom base would actually solve — not true today, since all three
  still follow one documented pattern. This Dream's original "not to be built until a real
  containerized artifact exists" premise has therefore only partially resolved: the artifacts exist
  and the pattern they converged on is now documented and guarded, but the larger ask this Dream
  captures — an actual shared, repo-owned base image — remains speculative until a real divergence
  makes one worth building.

### Non-goals

- **Not multi-architecture support** — moot until a target exists; source dream's own v1 was
  x86_64-only anyway.
- **Not confused with mason's `build_docker` recipe-build mode** — genuinely different concern,
  called out explicitly so a future reader doesn't conflate them.

### Full feature audit against `pixi-container-image`

| Source feature | Disposition | Why |
|---|---|---|
| UBI8-minimal base + pixi pre-install | **Omitted, no target** | No PyForge artifact builds or publishes a shared, repo-owned, pixi-preinstalled base image — the three Containerfiles that now exist (see "What is real") each materialize pixi independently in their own builder stage rather than inheriting one. |
| BuildKit `--mount=type=secret` credential handling | **Pattern retained** | The one piece worth keeping regardless of timing — a security discipline, not WF-specific. |
| Jenkins + `SharedLibrary_cicd` CI/CD, weekly rebuild cron | **Omitted, WF-infrastructure-specific** | This repo runs plain GitHub Actions; no Jenkins presence anywhere. |
| Prisma scan, OCI labels, `microdnf` hardening | **Omitted, no target** | Container-hardening detail with nothing to harden yet. |

### Kinships

[[pyforge-mason]] (nominal owner by the source label; genuinely unclaimed until a container
artifact exists) · [[reusable-cicd-workflows]] and [[miniforge-installer]] (siblings in the same
source org's Tier-3 batch, sharing the same "no current PyForge target" disposition)

### Realization log

- **2026-08-14** — Dream captured while porting a sibling org's dream catalog for PyForge fit.
  Checked directly for any existing container artifact or Docker-shipping concern before drafting
  (none found; mason's `build_docker` mode is a recipe cross-compilation mechanism, not an
  application-container concern, confirmed by reading its own source docstring). Kept
  intentionally thin — the credential-handling discipline is the only piece worth retaining
  independent of timing.
- **2026-08-14** — **Air-gapped realization requirements (operator, from the source original
  pixi-container-image.md):** the source Dockerfile is itself the airgap mechanism; its specifics
  should transfer intact if this is ever built: (1) the base is an internally-certified
  UBI8-minimal pulled from the enterprise registry, never public Docker Hub, and the produced
  image publishes back to that registry so K8s/OCP pulls (per today's operator decision) never
  leave the perimeter; (2) the pixi binary downloads from an Artifactory generic-repo mirror
  (`ARTIFACTORY_URL` + `ARTIFACTORY_REPO_PATH`, with a `${PIXI_VERSION%%.*}.x` major-version
  subdirectory) — direct prefix.dev download is an explicit source non-goal; (3) credentials
  cross the build boundary only via BuildKit `--mount=type=secret` read inline as
  `$(cat /run/secrets/...)` — never ENV, never COPY, never persisted in any layer — the
  build-time twin of `_http.py`'s env-only runtime posture, followed by `.pem`/`.enc` cleanup;
  (4) TLS to the mirror trusts the internal CA via a `CA_PATH` build arg, the image-build analog
  of the truststore half of `_http.py`'s runtime chain; (5) OS updates run `microdnf update`
  against internal `rpm-OraLinux*` repos only (credentials via `--setopt` from the same mounted
  secrets, `tsflags=nodocs`, caches cleaned), on a weekly rebuild cron so patching continues with
  no container ever reaching the public net; (6) downstream layers that later run `pixi install`
  resolve their channels from the same Artifactory conda mirrors this repo's pixi channels
  already swap to.
- **2026-08-22** — **Correction: the "nothing exists yet" premise is stale.** Story
  `spec-8-1-the-convention-is-written-and-guarded` (from `spec-pixi-container-image`) found the
  repo now ships three Containerfiles (root `Containerfile`, `src/platform/Containerfile`,
  `src/platform/compose/dbgpt/Containerfile` — Stories 7.1, 10.3, 10.5), all three already
  base-tag-pinned to `ghcr.io/prefix-dev/pixi` and free of any `ENV`-baked credential. Corrected
  "What is real" and "Constraints" above in place (prior entries left untouched) to state that,
  added `docs/reference/container-base-layer-convention.md` naming the three pillars (base-tag
  pinning, the multi-stage pixi-materialization shape, and the `--mount=type=secret`-only
  credential rule this Dream's own air-gapped requirements entry above already named as the piece
  worth retaining), and added `tests/packaging/test_containerfile_base_layer_convention.py` to
  statically guard against a future unpinned base or `ENV`-declared credential across all three
  files. No repo-owned base image was built or published — the upstream `ghcr.io/prefix-dev/pixi`
  image stays the base for every builder stage, per `spec-pixi-container-image`'s own Constraints.
- **2026-09-09** — **Realized, with a coverage gap named** (operator ruling,
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`
  § 2.2). A **fourth** Containerfile — `src/platform/compose/mcp-host/Containerfile`
  (spec-mcp-era-isolation slice 1) — now ships and follows the same convention, so the
  "three Containerfiles, one pattern" reading above was one behind; corrected in place. The Spec
  flips `ready → shipped`. The gap: the two enumerations in the repo **disagree**.
  `scripts/pixi_version_registry.py:79-87` already covers all four, but
  `tests/packaging/test_containerfile_base_layer_convention.py:50-52` hard-codes only three, so
  the fourth file is **ungoverned by the convention guard**. It is compliant today; the finding is
  that nothing would notice if it stopped being. The fix is to **derive** the list (glob
  `Containerfile*`), not to append a fourth literal — a declared list where a derived one was
  needed. That fix is a code change and needs a story; it is not applied by this documentation
  pass.

## 2026-10-26 — Presenton, conda-native — AI decks inside the regulated enterprise (folded from presenton-pixi-image)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 35.1). The body below is `docs/dreams/presenton-pixi-image.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/presenton-pixi-image.md`.*

## Presenton for the air-gapped enterprise

### The Dream

Bring the Presenton AI deck-generation app to places SaaS cannot go: an
**air-gapped, conda-forge-native repackaging** deployable on OpenShift Container
Platform in regulated-enterprise environments. Every dependency resolved from
governed channels, every image reproducible, no call home — AI deck generation
as an internal platform service.

### What it looks like when real

- Presenton repackaged with conda-forge primitives (pixi-locked image,
  OpenShift-ready), passing [[pyforge-warden]]-grade dependency gates.
- Distribution through the [[enterprise-airgap]] machinery (Artifactory
  routing, offline bundles).
- Division of labor with [[pyforge-herald|deckcraft]]: presenton = the repackaged *app*;
  deckcraft = the from-primitives *pipeline*. Complementary, not competing.
- Stations: [[packaging-factory]] (Mason) repackages; **[[pyforge-steward]]
  deploys and operates** the OpenShift service.

### What is real

- The BMAD project `presenton-pixi-image` (registered, active). Planning not yet
  run under the Dream-first flow.

### Realization log

- **2026-07** — project registered in PROJECTS.md.
- **2026-07-23** — Dream retro-seeded; awaits `bmad-spec`.
- **2026-08-02** — **ARCHIVED (blocked)** during dream consolidation: the full
  planning chain landed 2026-07-25 (7 epics / 30 stories) and has not moved
  since — no story has entered implementation, and the Phase-0 exit criteria
  remain unresolved. See `spec-presenton-pixi-image`'s retirement record for
  the full account.
- **2026-08-02 (same day, later)** — the brief/PRD/architecture/Spec
  planning-chain tier (only) was consolidated into `pyforge-mason`'s own
  single documents per explicit user override; this Dream's own narrative and
  the epics/blocked-status were deliberately left as archived above. Originals
  moved to `archive/_bmad-output/projects/pyforge-mason/planning-artifacts/`.
- **2026-09-08** — **the load-bearing unknown is answered; the Dream stays
  archived.** The archive note above singles out Phase-0 exit 6(a) — whether
  Microsoft's disconnected stack already ships a Copilot-for-PowerPoint
  equivalent — as bearing directly on whether the core differentiator holds.
  It does hold. Microsoft 365 Local's own capability list names exactly three
  on-premises *server* products (Exchange Server, SharePoint Server, Skype for
  Business Server); the Office client apps, and with them any Copilot deck
  generation, are absent, and Foundry Local is positioned explicitly as the AI
  layer and not the application layer. Risk R3 resolves to `infrastructure-only`,
  the third of the PRD's three named outcomes. **Caveat, and the reason the
  status does not move:** this is documentary evidence, whereas Story 1.6's
  acceptance criteria require a Microsoft licensing/product conversation or
  hands-on access to a disconnected deployment — neither of which happened, and
  neither of which this repo can perform. The exit is ANSWERED, not formally
  CLOSED, and the other five exits are untouched. Full finding, the contradictory
  third-party source it corrects, and a per-exit state table:
  `_bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md`
  entries `DW-PRESENTON-1-6-1` and `DW-PRESENTON-PHASE0-1` — the first tracked
  record this gate has ever had.

## 2026-10-26 — Dream — PyForge Mason: Recipe Validator (folded from pyforge-mason-recipe-validator)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 35.1). The body below is `docs/dreams/pyforge-mason-recipe-validator.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/pyforge-mason-recipe-validator.md`.*

## PyForge Mason — Recipe Validator

### Vision

**Mason** validates conda-forge recipes against linting rules, schema, and best practices — enforcing recipe.yaml/meta.yaml conformance, selector syntax, pinning policy, and cross-platform compatibility.

**The ask**: Build a recipe validator that catches every recipe defect before it hits staged-recipes CI, enforcing the factory's standards and speeding merge times.

### Problem

- **Linting feedback loops are slow.** Recipe lands on staged-recipes; CI fails; author waits days for re-trigger. Three rounds of feedback for small issues.
- **Standards drift.** Each reviewer has their own mental model of "correct." No canonical enforcement; bike-shedding wastes time.
- **Cross-platform breaks quietly.** Recipe works on linux-64; breaks on osx-arm64 silently. CI catches it; deployment is blocked.
- **Selectors are fragile.** `# [win]` typo means it's never validated on Windows. Policy-violating pins hide in selectors. No visibility.
- **Schema evolution breaks old recipes.** New schema version drops; old recipes suddenly invalid. No migration path.

### Realization

**Mason** delivers:

1. **Comprehensive Linting** — 50+ rules covering: naming, versioning, pinning policy, selectors, noarch, dependencies, licensing, build scripts.

2. **Schema Validation** — Recipes validated against recipe.yaml v1.0.0 and v0 meta.yaml. Drift detection warns of format mismatches.

3. **Pinning Policy Enforcement** — Operators define pinning rules (e.g., "python >= 3.9", "numpy < 2.0"). Mason checks every pin against the factory's policy.

4. **Cross-platform Coverage** — Validates selectors are present for all declared platforms. Warns on untested combos.

5. **Upstream Conformance** — Checks recipe against upstream source: does the version match? Are patches still applicable? Are dependencies accurate?

6. **Actionable Findings** — Every linting error includes: the problem, why it matters, the remediation, and a link to the policy doc.

### Success Criteria

- ✅ **Coverage**: 50+ linting rules, all with documented rationale
- ✅ **Speed**: Full recipe validation <1 sec; 100-recipe batch <2 min
- ✅ **Accuracy**: 0 false positives on canonical recipes; 95%+ catch rate on real defects
- ✅ **Integration**: Works in CI, local pre-commit hooks, and automated batch scanning
- ✅ **Feedback**: Every finding includes remediation guidance; authors fix issues without back-and-forth
- ✅ **Evolution**: Policy changes auto-apply to batch scans; old recipes validated against current policy

### Acceptance

Mason is done when:
1. All 50 linting rules implemented and documented
2. Validates 1000+ canonical conda-forge recipes with 0 false positives
3. Local `mason lint` speeds up feedback loop: catches CI issues before push
4. Automated batch scanning of all 769 feedstocks complete; defects cataloged
5. Integration with staged-recipes CI proven: PRs that pass Mason merge cleanly
6. Policy changes auto-apply: 769 feedstocks re-validated and reported in 5 min

## 2026-10-26 — A centrally-maintained CI/CD workflow family, if this repo ever needs more than plain Actions (folded from reusable-cicd-workflows)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 35.1). The body below is `docs/dreams/reusable-cicd-workflows.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/reusable-cicd-workflows.md`.*

## A centrally-maintained CI/CD workflow family, if this repo ever needs more than plain Actions

### The Dream

The source dream's actual subject — a 63-family EPLX system of reusable GitHub Actions workflows
built on Jenkins/Harness/Vault/Kaniko/FCD-governance/ThreadFix, letting any pixi project reach
production with zero custom CI logic — solves a problem this repo doesn't have: this repo has
ONE consuming project (itself), running on plain GitHub Actions (`detectors.yml`,
`staged-recipes-linter.yml`, `dashboard.yml`), with no Jenkins, no Harness CD, no enterprise
governance gate, and nothing else to centrally maintain workflows FOR. Captured for parity, not
because a real gap exists.

### What it looks like when real

Left thin — no scoped feature, because the premise (multiple consuming repos needing shared,
centrally-maintained CI) doesn't hold here yet:

- IF this repo's workflows ever need to be shared across multiple consuming repos (a genuine
  multi-repo estate, unlike today's single mono-repo), the source dream's two-tier architecture
  (step workflows + flattened entry points) is a reasonable pattern to reach for.
- The one concretely transferable idea, independent of that premise: this repo's own
  `detectors.yml`/`staged-recipes-linter.yml` could plausibly run some of their own steps in
  parallel rather than serially, the way the source dream's build engine does (documented 53%
  speedup from parallel lint/test/build/typecheck in one job) — but no specific current bottleneck
  was found to justify this as more than a speculative future optimization; checked both existing
  CI workflow files directly and found neither an obvious serial-that-should-be-parallel
  structure nor evidence either is currently slow enough to warrant it.

### What is real

Nothing built or missing — this repo's existing `detectors.yml` and `staged-recipes-linter.yml`
already do what this repo needs, on plain GitHub Actions, with no shared-workflow-family problem
to solve.

### Constraints

- **Not to be built until a second consuming repo exists.** The entire premise of a "reusable
  workflow family" requires more than one consumer; building one for a single mono-repo would be
  pure ceremony.

### Non-goals

- **Not Jenkins, Harness, Vault, Kaniko, or FCD governance** — none of this repo's infrastructure.
- **Not GitLab CI** — this repo uses GitHub Actions exclusively.

### Full feature audit against `reusable-cicd-workflows`

| Source feature | Disposition | Why |
|---|---|---|
| Two-tier reusable workflow architecture (step workflows + entry points) | **Pattern noted, no target** | Reasonable pattern IF a multi-repo estate ever exists here; premise doesn't hold today. |
| Parallel lint/test/build/typecheck in one job | **Noted as a possible future optimization, not scoped** | No specific current CI bottleneck identified to justify building this now. |
| `PIXI_FROZEN: true` frozen installs | **Already this repo's own convention** | Not something to port — this repo already runs pixi tasks with frozen lockfiles as standard practice. |
| Kaniko in-cluster container builds | **Omitted, no target** | No containers ship from this repo (see [[pixi-container-image]]). |
| Prisma/Checkmarx/BlackDuck scanning, FCD governance gate, ThreadFix | **Omitted, WF-infrastructure-specific** | No equivalent enterprise scanning/governance infrastructure exists or is planned here. |
| `vault-action`, HPOS Object Storage, Kafka-triggered Harness CD | **Omitted, WF-infrastructure-specific** | Same. |

### Kinships

[[pyforge-mason]] (nominal owner by the source label; genuinely unclaimed until a multi-repo
estate or a real CI bottleneck exists) · [[pixi-container-image]] and [[miniforge-installer]]
(siblings in the same source batch, same "no current PyForge target" disposition)

### Realization log

- **2026-08-14** — Dream captured while porting a sibling org's dream catalog for PyForge fit.
  Checked this repo's actual CI workflows (`detectors.yml`, `test-all.yml` and siblings) directly
  before drafting rather than assuming the source dream's premise applies — found no multi-repo
  estate, no Jenkins/Harness presence, and no obvious serial-CI bottleneck the source dream's
  parallel-job pattern would concretely fix. Kept thin and honest about the mismatch rather than
  manufacturing a scoped feature set with no real target.
- **2026-08-14** — **Air-gapped realization requirements (operator, from the source original
  reusable-cicd-workflows.md):** the source family is a complete worked example of disconnected
  CI, recorded here against the day a second consuming repo exists: (1) toolchain bootstrap never
  touches the public internet — Miniforge downloads from internal object storage (HPOS), not
  GitHub releases, and every build runs `PIXI_FROZEN: true` against `pixi.lock`; (2) channel
  topology is committed, credentials are not — consumer repos carry a `.condarc-cicd` naming the
  enterprise conda channels (the mirror-URL analog of this repo's swappable pixi channels), while
  secrets inject per-job via `vault-action` (HashiCorp Vault), the CI counterpart of `_http.py`'s
  env-vars-only rule; (3) container builds are in-cluster Kaniko (no Docker daemon) with separate
  `builder_base_image`/`runtime_base_image` inputs, both pulled from the internal registry and
  published to Artifactory docker-local — composing with [[pixi-container-image]]'s base layer
  and today's K8s/OCP deployment decision; (4) artifacts publish to Artifactory
  conda-local/pypi-local with checksum verification, and inter-job data moves through internal
  object storage rather than GitHub-hosted artifact storage; (5) the scanning/governance slots
  (Prisma, Checkmarx/BlackDuck, ThreadFix, FCD gate) all run against internal services — a
  PyForge equivalent would fill them with Warden's registry-perimeter gates on Artifactory
  ([[enterprise-airgap]]'s frontier), not WF's own scanners.
