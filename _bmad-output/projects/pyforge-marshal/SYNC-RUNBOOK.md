# SYNC-RUNBOOK — keeping `_bmad-output/projects/local-recipes` accurate

**Goal:** everything BMAD Quick Dev / BMAD-Method reads from this project always accurately
portrays the live `local-recipes` repo, and can be **caught up after _any_ out-of-band change**
(Claude, a human, a direct commit — anything that bypassed BMAD).

**Recurring owner (living factory docs):** **marshal** (CAP-7 decision **2026-08-24**).
After every CFE MINOR / `surface-changed` detector trip, and at least once per BMAD core minor
bump, marshal re-grounds `architecture-bmad-infra.md`'s `source_pin` and audits the root
`AGENTS.md` `bmad:context` managed block (the shared project-context surface since Story 30.2,
2026-09-06 — it replaced the eight per-station rulebook files this duty used to also re-ground).
Stations do **not** each own a relay — this is factory-governance surface, not a per-station
chore.

## The guarantee — and its honest limit

No static script can *prove* prose docs are semantically correct against an evolving repo. The
achievable guarantee is a **closed loop**:

1. **Baseline** — `.sync-baseline.json` records the exact factory surface + git HEAD the artifacts
   were last reconciled against.
2. **Detector** — `pyforge.doctor.sources.factory::gather` fires on *any* divergence from that
   baseline, so out-of-band work can never *silently* leave the docs stale; the canary always
   trips. (Story 6.9 ported the read-only verdict off `scripts/bmad_drift_check.py` into that
   Doctor source; the script survives only as a mutation-only residual — see Step 0 and Step 3.)
3. **Reconciler** — the **BMAD skills themselves** re-ground the artifacts against the live repo;
   then you re-stamp the baseline.

So the guarantee is: **“accurate as of the last reconciliation, and you are always told — with a
bounded catch-up procedure — when reality has moved.”** The detector is cheap and deterministic
(run it constantly); the reconciler is the expensive, correctness-restoring step (run it when the
detector trips).

## Two layers

| Layer | What | Tool |
|---|---|---|
| **Detector** | pins, counts, coverage completeness, baseline-vs-live surface, filing conventions, known-stale rules | `pixi run -e local-recipes bmad-drift-check` |
| **Reconciler** | re-ground the docs against the live repo, then re-pin | the BMAD skills (below) |

## When to run

- **Every CFE retro / skill MINOR bump** (CLAUDE.md Rule 2 — every conda-forge effort ends with a
  retro that bumps the skill; that bump is the re-sync trigger).
- **After any out-of-band change** to the source-of-truth surface (`recipes/`, `.claude/skills/`,
  `.claude/tools/`, `pixi.toml`, `docs/specs/`) — the baseline check (`surface-changed`) detects it.
- **At least once per BMAD core minor bump** (e.g. 6.10 → 6.11) — marshal re-grounds living factory
  docs even if the detector has not yet tripped on a skill pin.
- **Living-doc cadence (marshal-owned, 2026-08-24):** when any of the triggers above fire,
  marshal re-grounds `_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture-bmad-infra.md`
  (bump `source_pin` and `last_synced_skill_version`) and audits the root `AGENTS.md`
  `bmad:context` managed block via `bmad-project-context`. Story 30.2 (2026-09-06) retired the
  eight per-station rulebook files this cadence used to also re-ground — do **not** reintroduce
  a per-station relay.
- **In the test suite** — `tests/meta/test_bmad_artifacts_in_sync.py` enforces *integrity* (not
  currency) so a corrupt pin / misplaced file / uncovered doc fails fast.

---

## Step 0 — Detect

```bash
pixi run -e local-recipes bmad-drift-check          # full report (exits non-zero on drift)
pixi run -e local-recipes bmad-groundtruth          # live facts as JSON
python scripts/bmad_drift_check.py --fix            # auto-remediate the mechanical classes
```

The first two route through `python -m pyforge.doctor.sources bmad-drift` (the ported, read-only
verdict). `--fix` is a mutation, not a verdict, so it never moved into Doctor (Charter §6) — it
survives directly on `scripts/bmad_drift_check.py`, run with plain `python`, not a pixi task.

If `surface-changed` appears, see what moved out-of-band since the last reconciliation:

```bash
BASE=$(python -c "import json;print(json.load(open('_bmad-output/projects/local-recipes/.sync-baseline.json'))['git_head'])")
git diff --stat "$BASE"..HEAD -- recipes .claude pixi.toml docs/specs
```

## Step 1 — Reconcile, by finding type

| Detector finding | Doc(s) | Reconciler |
|---|---|---|
| `archive-misplaced`, `stray-file` | planning / impl | `python scripts/bmad_drift_check.py --fix` (auto: moves SCPs→`change-history/`, retros→`retros/`, deletes stray `.patch`) |
| `tracked-impl-artifact` | impl-artifacts | A git-tracked file under `implementation-artifacts/` (gitignored/local-only) is misfiled. If it's an **intake spec**, `git mv` it to `docs/specs/` (Tier 1); if it's a Tier-3 output, `git rm --cached` it. (This is the tier model — see CLAUDE.md "three tiers" + `AGENTS.md`.) |
| `docs-specs-nonmd` | docs/specs | `docs/specs/` holds Tier-1 markdown intake specs only — move the non-`.md` file out. |
| `pin-missing`, `baseline-corrupt` | any | restore the frontmatter `source_pin`/`last_synced_skill_version`. (Neither this covers nor `factory.py`/`bmad_drift_check.py` track the AGENTS.md `bmad:context` block — that surface carries no `source_pin`, and its own freshness proof is `bmad-project-context`'s "Verified `<date>` against `<commit>`" stamp, checked by `bmad-project-context audit`, not by this detector.) |
| `pin-behind` / `count-stale` / `phase-list-stale` (living: `architecture-*`, `source-tree-analysis`, `project-overview`, `integration-architecture`, `*-guide`, `project-parts.json`) | living | **marshal** re-grounds living docs by hand or with a plain read-only agent, then bumps each `source_pin` — **6.11 removed `bmad-document-project`** and its successor `bmad-project-context` does NOT produce brownfield docs (the deeper capability is promised upstream, not shipped). Cadence: after CFE MINOR / `surface-changed` / BMAD core minor (see When to run). Separately (no shared detector finding, since it isn't `source_pin`-tracked): run **`bmad-project-context`** in refresh/audit mode against the AGENTS.md `bmad:context` block on the same cadence — **not** a per-station relay (Story 30.2, 2026-09-06, retired the eight per-station rulebook files this cadence used to also re-ground) |
| `pin-behind` (plan) | `PRD.md`, `epics.md` | **`bmad-correct-course`** → **`bmad-edit-prd`** / **`bmad-create-epics-and-stories`** (structural: new epics/stories for net-new capabilities, not a number swap) |
| `pin-behind` (snapshot) | `validation-report-PRD.md`, `implementation-readiness-report.md` | regenerate fresh: **`bmad-prd`** (validate intent), **`bmad-sprint-planning`** readiness gate (6.11 absorbed `bmad-check-implementation-readiness`; PASS/CONCERNS/FAIL, finds artifacts by content not filename globs) (a gate is only meaningful re-run against current artifacts — never number-patch a dated snapshot) |
| `stale-rule` | any | hand-fix the rule, then add the bad pattern to `STALE_RULE_PATTERNS` in `sources/factory.py` (the ported verdict's own copy — `scripts/bmad_drift_check.py` no longer carries this constant) so it can never silently return |
| `spec-status-stale` | `implementation-artifacts/spec-*.md` | flip the spec's `status:` to its terminal value (it shipped — a matching retro exists) |
| `deferred-stale` | `implementation-artifacts/deferred-work.md` | reconcile each item vs the CHANGELOG / live code, then refresh the `**Last reconciled:** … vX.Y.Z` stamp |
| `index.md` after any move/refresh | `index.md` | hand-edit — **6.11 removed `bmad-index-docs` with no replacement** |
| `uncovered` | a new file | add a classification rule in `sources/factory.py` (`TRACKED` or `classify()` — the ported verdict's own copy; `scripts/bmad_drift_check.py` keeps an unused reference copy of `classify()` only, documented there as the extension pointer for anyone editing the script directly) so coverage stays complete |

The index (`index.md`) is refreshed **last**, after all moves and refreshes — by hand since 6.11 removed `bmad-index-docs`.

## Step 2 — Re-ground deep correctness (the part a script can't do)

The detector catches *mechanically extractable* drift. Semantic correctness (a rule that's wrong,
a claim that's false, a plan missing whole capability clusters) is re-grounded by **running the
appropriate BMAD skills — or, for brownfield living docs, a plain re-ground agent under marshal
ownership**:

```
# 6.11: bmad-document-project is removed and bmad-project-context does NOT
# re-derive brownfield docs. Marshal owns living-doc re-ground of
# architecture-bmad-infra.md's source_pin (CAP-7, 2026-08-24) via plain
# read-only agents grounded in the live repo. Story 30.2 (2026-09-06)
# retired the eight per-station rulebook files that pin used to also cover;
# the shared surface is now the AGENTS.md bmad:context managed block.
bmad-project-context         # refresh/audit the AGENTS.md bmad:context block
```

For high-stakes reconciliations, follow with an adversarial pass (`bmad-review` — 6.11 consolidates the adversarial / edge-case-hunter / verification-gap lenses) or a fan-out of read-only verification agents that check each
doc's claims against live code — the same method used in the 2026-06-20 audit.

## Step 3 — Re-stamp the baseline

Once the docs are reconciled and `bmad-drift-check` shows only acceptable findings:

```bash
python scripts/bmad_drift_check.py --write-baseline
git add _bmad-output/projects/local-recipes -- ':!*/implementation-artifacts/*'   # impl-artifacts is gitignored
git commit -m "docs(bmad): reconcile local-recipes artifacts to <skill version>"
```

`--write-baseline` is a mutation, not a verdict, so — same as `--fix` — it survives only on
`scripts/bmad_drift_check.py` (plain `python`, no pixi task); it records the current factory
fingerprint + git HEAD into `.sync-baseline.json`. The next out-of-band change will diff against
this new anchor via the read-only verdict (`pixi run -e local-recipes bmad-drift-check`).

---

## Coverage guarantee

`bmad-drift-check` classifies **every** file under the project (currently 67) and HARD-fails on any
it can't classify — so a new doc can never silently escape the sync loop. Classes: `tracked:*`
(pin-synced living/plan/context/deferred/spec), `archive:*` (frozen change-history + retros),
`snapshot` (dated gate outputs), `config`, `baseline`, `runbook`. Add new files to `TRACKED` /
`classify()` in `sources/factory.py` when the `uncovered` finding appears.

## Issue classes from the 2026-06-20 audit (now all detector-covered)

*The per-station `project-context` rulebook file class named in two rows below was retired
2026-09-06 (Story 30.2) — that content is now covered by the AGENTS.md `bmad:context` managed
block. The rows remain as a historical record of the 2026-06-20 audit.*

| Session issue | Detector finding that now catches it |
|---|---|
| 3 junk files (verbatim-dup spec, `review-diff.patch`, superseded spec) | `stray-file` (+ `--fix`) / manual |
| 30 historical files unarchived (SCPs, retros) | `archive-misplaced` (+ `--fix`) |
| `index.md` 3 conflicting pins + stale counts | `pin-behind`, `count-stale` |
| architecture/overview stale schema/tool/phase counts | `count-stale`, `phase-list-stale` |
| per-station `project-context` rulebook corrupt `span` frontmatter | `pin-missing` (HARD; integrity-gated) |
| per-station `project-context` rulebook stale rules (8 envs, 17 lint, missing O–S, branch convention) | `phase-list-stale`, `stale-rule`, `count-stale` |
| `spec-phase-k-hang-fix.md` shipped but still `in-flight` | `spec-status-stale` |
| `deferred-work.md` ~85% shipped, stale | `deferred-stale` |
| any out-of-band repo change since last sync | `surface-changed` (baseline) |
| a brand-new doc nobody wired into sync | `uncovered` (HARD) |

What the detector intentionally does **not** gate on: churny recipe counts (they move constantly
during the v0→v1 migration — reported, never failed), and semantic correctness of prose (that's the
reconciler's job).
