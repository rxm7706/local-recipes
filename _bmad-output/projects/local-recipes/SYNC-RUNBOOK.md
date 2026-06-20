# SYNC-RUNBOOK — keeping `_bmad-output/projects/local-recipes` accurate

**Goal:** everything BMAD Quick Dev / BMAD-Method reads from this project always accurately
portrays the live `local-recipes` repo, and can be **caught up after _any_ out-of-band change**
(Claude, a human, a direct commit — anything that bypassed BMAD).

## The guarantee — and its honest limit

No static script can *prove* prose docs are semantically correct against an evolving repo. The
achievable guarantee is a **closed loop**:

1. **Baseline** — `.sync-baseline.json` records the exact factory surface + git HEAD the artifacts
   were last reconciled against.
2. **Detector** — `scripts/bmad_drift_check.py` fires on *any* divergence from that baseline, so
   out-of-band work can never *silently* leave the docs stale; the canary always trips.
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
- **In the test suite** — `tests/meta/test_bmad_artifacts_in_sync.py` enforces *integrity* (not
  currency) so a corrupt pin / misplaced file / uncovered doc fails fast.

---

## Step 0 — Detect

```bash
pixi run -e local-recipes bmad-drift-check          # full report (exits non-zero on drift)
pixi run -e local-recipes bmad-groundtruth          # live facts as JSON
pixi run -e local-recipes bmad-drift-check -- --fix # auto-remediate the mechanical classes
```

If `surface-changed` appears, see what moved out-of-band since the last reconciliation:

```bash
BASE=$(python -c "import json;print(json.load(open('_bmad-output/projects/local-recipes/.sync-baseline.json'))['git_head'])")
git diff --stat "$BASE"..HEAD -- recipes .claude pixi.toml docs/specs
```

## Step 1 — Reconcile, by finding type

| Detector finding | Doc(s) | Reconciler |
|---|---|---|
| `archive-misplaced`, `stray-file` | planning / impl | `bmad-drift-check -- --fix` (auto: moves SCPs→`change-history/`, retros→`retros/`, deletes stray `.patch`) |
| `pin-missing`, `baseline-corrupt` | any | restore the frontmatter `source_pin`/`last_synced_skill_version`; for `project-context.md` regenerate with **`bmad-generate-project-context`** |
| `pin-behind` / `count-stale` / `phase-list-stale` (living: `architecture-*`, `source-tree-analysis`, `project-overview`, `integration-architecture`, `*-guide`, `project-parts.json`) | living | **`bmad-document-project`** — re-grounds these from the live repo; then bump each `source_pin` |
| `pin-behind` (context) | `project-context.md` | **`bmad-generate-project-context`** |
| `pin-behind` (plan) | `PRD.md`, `epics.md` | **`bmad-correct-course`** → **`bmad-edit-prd`** / **`bmad-create-epics-and-stories`** (structural: new epics/stories for net-new capabilities, not a number swap) |
| `pin-behind` (snapshot) | `validation-report-PRD.md`, `implementation-readiness-report.md` | regenerate fresh: **`bmad-validate-prd`**, **`bmad-check-implementation-readiness`** (a gate is only meaningful re-run against current artifacts — never number-patch a dated snapshot) |
| `stale-rule` | any | hand-fix the rule, then add the bad pattern to `STALE_RULE_PATTERNS` in `bmad_drift_check.py` so it can never silently return |
| `spec-status-stale` | `implementation-artifacts/spec-*.md` | flip the spec's `status:` to its terminal value (it shipped — a matching retro exists) |
| `deferred-stale` | `implementation-artifacts/deferred-work.md` | reconcile each item vs the CHANGELOG / live code, then refresh the `**Last reconciled:** … vX.Y.Z` stamp |
| `index.md` after any move/refresh | `index.md` | **`bmad-index-docs`** |
| `uncovered` | a new file | add a classification rule in `bmad_drift_check.py` (`TRACKED` or `classify()`) so coverage stays complete |

The index (`index.md`) is regenerated **last**, after all moves and refreshes, via `bmad-index-docs`.

## Step 2 — Re-ground deep correctness (the part a script can't do)

The detector catches *mechanically extractable* drift. Semantic correctness (a rule that's wrong,
a claim that's false, a plan missing whole capability clusters) is re-grounded by **running the
BMAD brownfield skill against the live repo**:

```
bmad-document-project        # re-derive architecture-*, source-tree-analysis, project-overview, project-parts
bmad-generate-project-context# re-derive the spawn rulebook (project-context.md)
```

For high-stakes reconciliations, follow with an adversarial pass (`bmad-review-adversarial-general`
/ `bmad-review-edge-case-hunter`) or a fan-out of read-only verification agents that check each
doc's claims against live code — the same method used in the 2026-06-20 audit.

## Step 3 — Re-stamp the baseline

Once the docs are reconciled and `bmad-drift-check` shows only acceptable findings:

```bash
pixi run -e local-recipes bmad-drift-check -- --write-baseline
git add _bmad-output/projects/local-recipes -- ':!*/implementation-artifacts/*'   # impl-artifacts is gitignored
git commit -m "docs(bmad): reconcile local-recipes artifacts to <skill version>"
```

`--write-baseline` records the current factory fingerprint + git HEAD into `.sync-baseline.json`.
The next out-of-band change will diff against this new anchor.

---

## Coverage guarantee

`bmad-drift-check` classifies **every** file under the project (currently 67) and HARD-fails on any
it can't classify — so a new doc can never silently escape the sync loop. Classes: `tracked:*`
(pin-synced living/plan/context/deferred/spec), `archive:*` (frozen change-history + retros),
`snapshot` (dated gate outputs), `config`, `baseline`, `runbook`. Add new files to `TRACKED` /
`classify()` when the `uncovered` finding appears.

## Issue classes from the 2026-06-20 audit (now all detector-covered)

| Session issue | Detector finding that now catches it |
|---|---|
| 3 junk files (verbatim-dup spec, `review-diff.patch`, superseded spec) | `stray-file` (+ `--fix`) / manual |
| 30 historical files unarchived (SCPs, retros) | `archive-misplaced` (+ `--fix`) |
| `index.md` 3 conflicting pins + stale counts | `pin-behind`, `count-stale` |
| architecture/overview stale schema/tool/phase counts | `count-stale`, `phase-list-stale` |
| `project-context.md` corrupt `span` frontmatter | `pin-missing` (HARD; integrity-gated) |
| `project-context.md` stale rules (8 envs, 17 lint, missing O–S, branch convention) | `phase-list-stale`, `stale-rule`, `count-stale` |
| `spec-phase-k-hang-fix.md` shipped but still `in-flight` | `spec-status-stale` |
| `deferred-work.md` ~85% shipped, stale | `deferred-stale` |
| any out-of-band repo change since last sync | `surface-changed` (baseline) |
| a brand-new doc nobody wired into sync | `uncovered` (HARD) |

What the detector intentionally does **not** gate on: churny recipe counts (they move constantly
during the v0→v1 migration — reported, never failed), and semantic correctness of prose (that's the
reconciler's job).
