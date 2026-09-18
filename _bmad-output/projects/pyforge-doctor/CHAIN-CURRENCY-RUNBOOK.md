# Chain-Currency Runbook — the planning-spine reconciler sweep

Dream: `docs/dreams/chain-currency-sweep.md` (owner: doctor). Detector side: the
chain-layers audit (`pixi run -e local-recipes chain-layers-audit-check -- --project
<slug>`, Stories 17-3/21-1, FR-150/FR-192 CAP-3). This runbook is the reconciler side —
the marshal `SYNC-RUNBOOK.md` two-layer pattern generalized to the fleet's planning
spines. First validation run: the 2026-08-26 26-finding clearance (Worked Example 1,
complete — see § Worked Examples).

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
   `code→retro`. (`prd→gates` and, since 2026-09-04, `epics→sprint` deliberately
   excluded: the tracked ledger is a generated twin dated by git last-touch, which cannot
   move on an idle station; chain-completeness INV-B answers "did the ledger follow the
   epics?" by content instead.)
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
| layer gap (missing stage artifact) | Produce the artifact via its BMAD skill, or declare the stage n/a for that chain class — a policy decision, not a per-chain patch. **Deck ruling (operator, 2026-08-27, from the pyforge-unifying-strategy pilot): deck-on-demand** — the deck stage is n/a for any non-flagship chain without one (derived in `scripts/fleet_scan.py`; a chain gaining `presentations/<slug>/` is measured again automatically); a satellite deck is produced only when the chain has a rich SPEC pack and an audience |

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
   then bump. (`epics→sprint` is no longer a feeds edge — there is no daily ledger stamp;
   run `sprint-ledger-sync -- --project <slug> --repair-feed` and let INV-B judge the
   ledger.)
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
- **Append the run to § Worked Examples before the Land step is done.** Run 1 is the
  validation narrative; every later run appends *at least a one-line entry* — date,
  findings cleared, deviations. **A run that appends nothing has not completed its Land
  step.** (`spec-chain-currency-sweep` CAP-6, narrowed 2026-09-09: three sweeps —
  2026-08-29 / 09-04 / 09-07 — skipped the append because the old wording asked each run
  for a Run-1-sized narrative, which is not proportionate to a 2-finding sweep.)

## Worked Examples

- **Run 1 (2026-08-26) — COMPLETE, board cleared.** 26 staleness findings across the 8
  station flagships (research-wave→brief ×8, spec-re-stamp→prd ×8, code→retro ×6,
  marshal prd→arch, mason behind-code ×3) + 1 overtaken
  (`spec-pyforge-unifying-strategy`) → `chain-currency-sweep-check` **exit 0 fleet-wide**.
  Executed exactly per this runbook: Phase 0 operator session answered the strategy spec's
  three residual OQs (both-faces-one-boot-script / named-new-pipeline / dual-write); then
  eight parallel single-story station agents (physical paths, no bmad-switch, no agent
  commits), each cascade brief→PRD→arch(→epics note)→retro, one commit per station.
  Wall-clock ≈15 min for all eight in parallel (7–15 min each); every station green on its
  FIRST detector iteration. Mason ran the behind-code remedy's realized-flip path: as-built
  truth-up + close-out retro + Dream `specified`→`realized`, hygiene clean.
  **Deviations/lessons:** (1) the audit reads the working tree — verify on the branch that
  carries your edits, not main (a false "overtaken still red" cost one diagnosis cycle);
  (2) genuine reconciliation surfaces real defects beyond the findings — atlas's brief
  carried four shipped-reality overclaims, steward's arch spine had an unparseable
  frontmatter (unescaped apostrophe), herald found two `dashboard-check` remnants the
  30.2 retirement missed, mason's chain counts had drifted 5/38→11/50, marshal registered
  FR-192..195 with two numbering defects filed; (3) keep the shared files (dreams README)
  to exactly one writer — the mason agent owned it, the parent did the chain-currency row
  after. Landed via the sweep/run-1 branch (stacked on PR #877).

- **Run 2026-09-14 — 8 of 9 findings cleared; 1 documented residual, not stamped over.**
  Entry state: 8 × `staleness` (all eight stations) + 1 × `coherence` (warden), tracked as
  `DW-VOCAB-2026-09-14-15`. Exit state: `chain-currency-sweep-check` exit 1 with **one**
  finding — warden `coherence`. Executed by a single agent, serially, **not** the runbook's
  eight-parallel dispatch: the operator was working the same checkout concurrently with
  staged work on a PR branch, so the agent was barred from every git operation, and serial
  editing removed the shared-state risk the parallel pattern exists to manage. Per station:
  **atlas** (`code→retro`) → a real retro for 2026-08-26 → 09-14 (Epics 20–24 closed, Epic
  25 at 3-of-4, `views/` deleted, `DW-B2-3` closed); **doctor / herald / marshal / mason /
  scribe / steward / warden** (`spec→prd`) → PRD + spine cascades, plus epics validation
  notes where `arch→epics` would have fired next (doctor, mason, warden); **steward** also
  `research→brief` (the two 2026-09-14 vocabulary passes — chain-scoped to
  `vocabulary-one-name-one-job`, no charter change).

  **Deviations / lessons:**

  1. **Genuine reconciliation found six real defects the findings themselves did not name.**
     doctor's spine listed 12 `sources/` modules and "14 dispatcher entries" against a live
     20/22; mason's FR-14 (diff-before-apply) and NFR-9 (dry-run by default) are both false
     for `mason recipe update` (`cli.py:711-715`, `recipe.py:797-799`); scribe's UJ-1 writes
     `--type decision`, which `models.py:34` does not allow, and SM-4 still names a crontab
     that Story 8.1 replaced with a checked-in systemd-user timer; warden's
     `review_required` — promised by FR9 and the acceptance matrix — occurs **zero** times
     in shipped `src/`/`tests/`; and marshal's PRD still carried four questions (its
     Q-4..Q-7) that the Spec's 2026-09-09 operator pass had already answered. A sweep that
     only re-stamped would have found none of them.
  2. **Number translation between a Spec and its PRD is a real hazard.** marshal's Spec
     Q-11..Q-14 are the PRD's Q-4..Q-7. The mapping is now a table in that PRD's § 19;
     without it the next sweep re-derives it or misses the answers entirely.
  3. **`updated:` must be an explicit frontmatter key to verify pre-commit.** The audit reads
     the working tree, but a stage whose date falls through to git last-touch cannot move on
     an *uncommitted* edit. Every artifact touched here already carried `updated:`; one that
     does not must have the key added, not rely on the commit to move it.
  4. **Quote `currency_review:` values, and re-validate with a real YAML parser after every
     frontmatter edit.** `fleet_scan._frontmatter_scalars` is a deliberately naive line
     reader, so a frontmatter block can be invalid YAML and still feed the board correctly.
     steward's PRD was **already broken at HEAD** this way (unquoted scalar containing
     `: `) and was repaired in passing; one edit here broke mason's the same way and was
     caught only because a `yaml.safe_load` check ran immediately after. Check after each
     edit, not at the end of the pass.
  5. **A documented residual beats a stamp.** warden's `coherence` is `overtaken` on three
     **operator-owned** questions (is v1 released or story-complete; what becomes of the
     legacy Tier-1 spec; four-axis or six-axis until provenance/maintenance are promoted).
     The runbook's own remedy is "resolve with the operator," so the checkpoint was left red
     and the reason written into warden's PRD rather than answered unilaterally to reach
     exit 0.
  6. **Three findings were recorded as owing a Dream/Spec, not repaired.** mason's
     FR-14/NFR-9 default, scribe's SM-4 trigger wording, and warden's `review_required`
     field are all behaviour or schema changes. Under Dream-first they enter through
     `docs/dreams/<slug>.md` → `bmad-spec` → a Story; a currency sweep records them and
     stops.

- **Run 2026-09-18 — 1 finding cleared, single station.** Entry state: pyforge-atlas
  `chain-audit-checkpoint-staleness` fail (two paired findings: `prd→arch` feeds, PRD
  re-cut 2026-09-17 by the atlas-fold rekey landing ahead of the arch spine's
  2026-09-07 stamp; and `behind-code`, the spine trailing the 2026-09-10 Story 24.4
  live-Artifactory-transport commit). Exit state: `chain-layers-audit-check --project
  pyforge-atlas` verdict `ok`, all four checkpoints pass. Remedy: the PRD's fold was
  citation-only (CAP provenance tags, no FR semantics changed) plus the Epic 12–25 →
  11–24 rekey, so the arch spine's AD-3 *(Amended 2026-08-26 …)* parenthetical — a
  live rule, not dated narrative — was corrected in place from old Epic 13/15 to
  post-rekey Epic 12/14; the 2026-08-26 dated section's own Epic citations were left
  as written per the historical-prose convention. A new `## Currency reconciliation —
  2026-09-18` section documents both the fold and Story 24.4's
  `tools/live_artifactory_transport.py` (as-built confirmation of the already-charted
  `artifactory_downloads` pipeline, no new AD). `updated:`/`currency_review:` bumped.
