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
`docs/dreams/presenton-pixi-image.md` for the full account.

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
  there, `docs/specs/feedstock-refresh.md`, is carried into Mason's chain before its file moves. That
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

## One-chain fold — 2026-09-17

Station Dream status is `specified` (Spec `spec-pyforge-mason` is `ready`). Mason-owned satellite Dreams archive in place with Consolidated-into banners. Practice Dream `packaging-factory` is archived into this station Dream (CHAIN-STANDARD precedence; no new station Dream minted). Recipe work stays `conda-forge-expert`; this fold is planning-chain only.
