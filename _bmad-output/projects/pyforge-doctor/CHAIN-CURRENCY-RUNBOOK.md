# Chain-Currency Runbook — the planning-spine reconciler sweep

Dream: `docs/dreams/chain-currency-sweep.md` (owner: doctor). Detector side: the
chain-layers audit (`pixi run -e local-recipes chain-layers-audit-check -- --project
<slug>`, Stories 17-3/21-1, FR-150/FR-192 CAP-3). This runbook is the reconciler side —
the marshal `SYNC-RUNBOOK.md` two-layer pattern generalized to the fleet's planning
spines. First validation run: the 2026-08-26 26-finding clearance (Worked Example 1,
pending).

## When to run

Event-driven, with the detector as backstop:

- after a fleet research wave (a `research/` refresh across stations),
- after a spec re-stamp campaign (bulk `updated:` motion on SPEC.md files),
- after an epic close that lands substantial code,
- whenever `chain-currency-sweep` (or a per-project `chain-layers-audit-check`) reds.

## The audit mechanics you must not fight

These are the detector's actual rules (source of truth:
`pyforge.doctor.sources.fleet_scan` currency logic; mirrored in the retired Guildhall
generator). Get them wrong and the sweep mints findings instead of clearing them.

1. **Feeds graph** — upstream dated after downstream = finding:
   `research→brief`, `brief→prd`, `prd→arch`, `spec→prd`, `arch→epics`,
   `epics→sprint`, `code→retro`. (`prd→gates` deliberately excluded.)
2. **2-day grace window** — a feeds pair only fires when the gap exceeds 2 days. This
   is what makes a per-station cascade safe *if it lands together*: touch a brief and
   the PRD/arch/epics must follow within the window, or the pass itself goes red.
3. **Strict date precedence** — frontmatter `updated:` beats path-date beats git
   last-touch, never `max()`. A re-commit moves nothing; the reconcile must bump
   `updated:`. Conversely: **a stamp without a genuine reconcile is lying to the
   board** — forbidden.
4. **`behind-code`** (spec/PRD/arch older than last code motion) is **suppressed once
   the Dream is `realized`** — that flag is aimed at chains still being built.
5. **`overtaken`** = the spec's `open_questions` list is non-empty while its PRD and
   arch already exist. Only emptying the list clears it.
6. **Shelf life** — 90 days default per stage (dream/spec/context/tea/retro exempt);
   the sweep's cadence above keeps this from ever firing alone.

## Finding → remedy map

| Finding | Remedy |
|---|---|
| `feeds` (research→brief, spec→prd, …) | Per-station cascade (below), top-down, one commit |
| `feeds` code→retro | Retro for that station (`bmad-retrospective`, `-H` supported), landed in `planning-artifacts/retros/` |
| `behind-code` | Truth-up spec/PRD/arch against as-built code; if the station has genuinely shipped, close out (retro) and flip its Dream to `realized` — suppression is then by design, not evasion |
| `overtaken` | Resolve the spec's residual `open_questions` with the operator; record dated answers in § Open Questions; empty the frontmatter list |
| layer gap (missing stage artifact) | Produce the artifact via its BMAD skill, or declare the stage n/a for that chain class — a policy decision, not a per-chain patch |

## The grounding triple (every artifact touched, no exceptions)

1. **The upstream artifact that fired** — fold its content in, don't just cite it.
2. **The Unifying Strategy** — `_bmad-output/projects/pyforge-steward/planning-artifacts/
   specs/spec-pyforge-unifying-strategy/` (SPEC + stack.md + console-parity-inventory.md +
   architecture-diagrams.md + resilience-invariants.md). Each station's contract states its
   hub-and-spoke role in the Canopy estate. If the strategy spec itself is `overtaken`,
   resolve that **first** — you cannot ground eight chains on an unsettled source.
3. **The as-built code** — `src/shared/packages/pyforge-<station>/` (+ `src/platform/`
   for steward/Canopy), its SKILL.md and tests. Contract-vs-code divergence is written
   into the artifact or filed as a finding — never papered over.

## Per-station cascade (the unit of dispatch)

One station, one agent, one commit, inside one grace window:

1. **Brief** — `bmad-product-brief` (update): fold the newer research; bump `updated:`.
2. **PRD** — `bmad-prd` (update/validate): re-derive from refreshed brief + current
   spec; bump `updated:`.
3. **Arch** — `bmad-architecture` (update): required for **every** station whose PRD
   moved (the `prd→arch` edge fires the moment the PRD is re-cut). Bump `updated:`.
4. **Epics** — validate against the new arch (`arch→epics`); a genuine validation note,
   then bump. `epics→sprint` self-heals (the ledger stamps daily).
5. **Retro** (if code→retro fired) — `bmad-retrospective` covering everything since the
   last retro, strategy-convergence note included.

After every file edit: **verify the frontmatter survived** (a stray unquoted `:`
collapses it, and the stage date then silently falls back to git).

## Dispatch discipline (8 stations in parallel)

- Single-story dispatch: one agent per station cascade. Never one orchestrator holding
  the whole backlog.
- **Physical paths only** — write to
  `_bmad-output/projects/pyforge-<slug>/planning-artifacts/…` literally. Never through
  the `_bmad-output/planning-artifacts` symlink; never `scripts/bmad-switch` from a
  parallel agent. Pass `BMAD_ACTIVE_PROJECT=<slug>` per invocation when a skill needs
  the active project.
- Verify placement after writing (`readlink -f`, or check the file landed under the
  intended slug) — the failure mode is silent.

## Verify

Per station, with the real detector — never a hand regex, never the board alone:

```
pixi run -e local-recipes chain-layers-audit-check -- --project pyforge-<slug>
```

All eight green (plus dreams-hygiene if any Dream status moved) = the sweep is clear.
Regenerating a board view is optional confirmation, not the measure.

## Land

- One branch for the sweep; one commit per station cascade plus one for retros.
- PR to `rxm7706/local-recipes` with the **`maintenance` label** (all paths outside
  `recipes/`). Merge with `--merge`, never squash. No courtesy preambles, no AI
  attribution.
- If `pixi.toml` was touched (it normally is not): regenerate + commit
  `environment.yaml` — that sync gate is ungated by the label.
- Post-land: `pixi run -e local-recipes bmad-drift-check`; if it reports
  surface-changed for the marshal artifact set, reconcile per its own runbook and
  re-stamp with `python scripts/bmad_drift_check.py --write-baseline` — **after**
  `git add` of any new files.

## Worked Examples

- **Run 1 (pending)** — the 2026-08-26 clearance: 26 staleness findings across the 8
  station flagships (research-wave→brief ×8, spec-re-stamp→prd ×8, code→retro ×6,
  marshal prd→arch, mason behind-code ×3) + 1 overtaken
  (`spec-pyforge-unifying-strategy`). Append the outcome, deviations, and timings here
  when it lands.
