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

- **4 of 38 stories shipped (~11%)**, all in Epic 1 (`S-1.1` workspace-member
  scaffold and dual-artifact build, `S-1.2` CLI noun-verb structure and global
  flags, `S-1.3` error taxonomy and exit-code contract, `S-1.4` dual output
  format with stream discipline). The installable shell and its output contract
  exist; Epic 1's remaining six stories (CFE root resolution, interpreter
  selection, degradation-when-CFE-is-absent, `mason doctor`, the fake-CFE-root
  test harness, configuration/logging) are backlog, and Epics 2–5 — the whole
  recipe lifecycle, the dual-ship motion, environment locking, and the seam
  proof — have not started.
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
[[enterprise-airgap]] (every artifact must resolve behind a firewall).

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
