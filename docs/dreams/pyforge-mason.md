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

## One-chain fold — 2026-09-17

Station Dream status is `specified` (Spec `spec-pyforge-mason` is `ready`). Mason-owned satellite Dreams archive in place with Consolidated-into banners. Practice Dream `packaging-factory` is archived into this station Dream (CHAIN-STANDARD precedence; no new station Dream minted). Recipe work stays `conda-forge-expert`; this fold is planning-chain only.
