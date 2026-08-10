---
id: SPEC-surface-drift-reconciliation
spec: surface-drift-reconciliation
status: in-progress
owner-dream: docs/dreams/surface-drift-reconciliation.md
companions: []
sources:
  - ../../../../../../docs/dreams/surface-drift-reconciliation.md
surface:
  # The instrument this Spec repairs. `scripts/spec_surface_check.py`'s own
  # EXISTENCE-contract line retired 2026-08-09 (Story 6.9) — the detector moved into
  # src/shared/packages/pyforge-doctor/**, already governed by spec-pyforge-doctor's
  # blanket glob. The baseline stays: its PATH did not move, only the tool reading it.
  - scripts/.spec-surface-baseline.json
surface-drift-exclude:
  # The baseline is a stamped artifact of the tool it belongs to — its hash moves on
  # every sanctioned reconciliation, so hashing it here would report drift on every
  # correct use of the feature this Spec adds.
  - scripts/.spec-surface-baseline.json
assumptions:
  - "RETIRED 2026-08-09 — the assumption that the two `[ungoverned]` Charter files
    wanted a real surface was wrong on a fact. `docs/governance/spec-pyforge-charter/`
    is not discovered by `SPEC_GLOB`, so it cannot declare one. Allowlisted."
open_questions:
  - "RESOLVED (S-13.3) — the Charter's spec folder is allowlisted, the only
    mechanism available to it."
  - "RESOLVED (S-13.4) — the 34 `[drift]` split 9 archived-spec baseline lag /
    2 genuine console change / 23 steward files whose contract was already correct."
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what to build, test, and validate. The source document in frontmatter is for traceability only.

# Surface drift reconciliation — a gate that can be cleared, a signal that can be trusted

## Why

A pain, and an unusual one: **the instrument is the thing that is broken.**

`scripts/spec_surface_check.py` is what makes the regenerable factory real — it
proves every tracked file is governed by a spec surface and that no governed file
drifted out from under its contract. It has carried **61 findings on `main`** for
weeks. The repo is not 61 kinds of broken; the detector has two defects that make
its verdict unactionable in one direction and untrustworthy in the other.

**It cannot be cleared honestly.** `--write-baseline` stamps *every* spec in one
write, so the sanctioned fix for a single `[no-baseline]` finding necessarily
accepts every other spec's pending drift as correct. Settling one spec destroys
the evidence for ~34 others, so the honest move is to leave the finding standing —
which is precisely why the red persists. A gate nobody can safely clear stops
being a gate.

**It cannot be trusted either.** The drift pass short-circuits per *spec*, not per
*file* (`if b["memlog"] != cur["memlog"]: continue  # spec moved — code changes are
presumed reconciled`). Appending **any** memlog entry therefore marks every governed
file in that surface reconciled, including files the author never touched. This was
reproduced live: one unrelated allowlist note dropped findings 63 → 61, clearing two
detectors nobody had reconciled. The disappearance is indistinguishable from a real
fix in the count the dashboard renders, and the larger a surface's governed set the
more it launders — this one governs four detectors.

Both are the same disease at two granularities: **the reconciliation claim is made
at the wrong level.** Baselines stamp all-or-nothing when they should be per-spec;
drift clears per-spec when it should be per-file. Behind it is a rule this repo
already holds everywhere else — never claim green you did not measure. "Presumed
reconciled" is a claim nobody measured.

Affected: every operator who reads this gate, and every future out-of-band edit it
is supposed to catch but currently cannot be trusted to report.

## Capabilities

- **CAP-1** — baseline stamping is scopeable
  - **intent:** An operator settles one spec's baseline without accepting any other spec's pending drift.
  - **success:** `--write-baseline --spec NAME` merges only that spec's entry into the committed baseline and leaves every other entry byte-identical; an unknown spec name exits 2 with the known names listed; unscoped `--write-baseline` still works and states in its own help text that it accepts every other spec's pending drift.

- **CAP-2** — a moved contract reconciles only the paths it names
  - **intent:** A memlog entry stops speaking for governed files it never mentions, so unrelated activity cannot launder pending drift.
  - **success:** With a spec's memlog moved, a drifted file **named** in that memlog clears while an **unnamed** one reports `[drift-presumed]`; appending an unrelated memlog entry no longer changes the verdict for an untouched governed file (the live 63 → 61 laundering no longer reproduces).

- **CAP-3** — the standing 61 findings are worked to zero by category
  - **intent:** An operator can act on the verdict because every finding is dispositioned rather than carried.
  - **success:** Each of the 24 `[no-baseline]` scoped-stamped; each of the 34 `[drift]` either genuinely reconciled through its spec or scoped-stamped with the reasoning recorded in that spec's memlog; both `[ungoverned]` files given a surface or allowlist entry; the one `[stale-allowlist]` pattern removed. Anything that cannot be honestly cleared is filed as deferred work with its reason, never suppressed.

- **CAP-4** — the cleared gate is defended by tests that fail for the right reason
  - **intent:** Neither fix can silently regress into the blanket behavior it replaces.
  - **success:** Both are mutation-tested **both ways** — removing `--spec` scoping re-reds the isolation test, and restoring the per-spec short-circuit re-reds the laundering test — and `spec-surface-check` exits 0 on `main`.

- **CAP-7** — the producer reconciles what it drifts
  - **intent:** bmad-loop names the governed paths it changed in the owning Spec's memlog as part of the story, so the spec-surface gate stops being a tax paid by whoever lands the work.
  - **success:** A loop-produced story that changes governed files leaves that Spec's `.memlog.md` naming each changed path before the story is marked complete; `spec-surface-check` is green on the loop's own station branch without a human editing a memlog; a story that changes NO governed file writes nothing (silence is not a finding); and the reconciliation is per-file naming under S-13.2's rule, never a blanket stamp — the loop must not be handed `--write-baseline`.

- **CAP-6** — the presumed set is worked down by measurement, not carried
  - **intent:** The 994 `[drift-presumed]` entries CAP-2 made visible are dispositioned, so the informational channel stays small enough to read and a new entry means something.
  - **success:** Every presumed entry is traced to the commit that last moved it and partitioned — `added` (baseline lag) vs `changed` (the per-file question) — with each cluster judged against its Spec's own capabilities and the judgment recorded in that Spec's memlog before any stamp; anything moved by a story that is **not** `done`, or landing outside a contracted capability, is reported rather than stamped; the four Specs are then scoped-stamped individually and `spec-surface-check` reports **0 findings and 0 `[drift-presumed]`**, with a before/after diff proving no gating `[drift]` was absorbed.

- **CAP-5** — a governed surface with no contract behind it is reported
  - **intent:** A Spec that declares a `surface:` but has no `.memlog.md` stops being silently drift-blind — its contract hash is `""`, so the contract can never move and the "reconcile the spec" remedy the detector prints is unreachable.
  - **success:** A spec that governs ≥1 tracked file under the default `surface-drift: memlog` mode with no `.memlog.md` reports a **gating** `[drift-blind]` finding naming the spec, its governed count, and the path the memlog belongs at; a spec governing zero files, an `exempt` spec, and a `sentinel:` spec each report nothing (their contracts cannot go blind); the 7 live instances (396 governed files) are dispositioned by creating each memlog **and** scoped-stamping its baseline in the same change, verified by a before/after diff showing no `[drift]` moved to `[drift-presumed]`; mutation-tested both ways — removing the check re-greens a fixture whose memlog was deleted, restoring it re-reds.

## Constraints

- **Fix the granularity; do not weaken the gate.** Widening a threshold, allowlisting the noisy specs, or making drift non-gating clears the red without making the signal true. Charter §6 forbids meeting a gate by relaxing it.
- **`.memlog.md` history is append-only and never rewritten.** The per-file rule *reads* memlog text; it may not edit, reorder, or normalize any memlog to make matching easier.
- **A memlog that names no paths is not an error.** Most existing entries predate any naming convention, so the per-file rule degrades to a visible `[drift-presumed]` — a hard failure would red the gate for every historical entry, reproducing the unclearable red in a new shape.
- **`[drift-presumed]` is informational and never gates.** Its purpose is making an unproven set visible; a gating variant is the same unclearable red renamed.
- **A scoped stamp merges into the committed baseline.** Rewriting from the in-memory current set would silently drop every spec not named on that invocation.
- **Path matching is literal substring on the repo-relative path** — the form these entries already cite files in. Inferring intent from prose reintroduces the presumed-reconciled blanket this replaces.
- **`[drift-blind]` gates, unlike `[drift-presumed]`.** The two are not the same class: `[drift-presumed]` is *unproven* reconciliation and must stay informational, while `[drift-blind]` is a *structurally impossible* one. It is also trivially clearable — create the file — so it can gate without becoming an unclearable red.
- **Creating a memlog and stamping its baseline are one change.** A new memlog moves the contract hash off `""`, downgrading that spec's next drift from gating `[drift]` to informational `[drift-presumed]`. Fixing blindness without stamping in the same move trades a false green for a quiet one.
- **The detector may not create the missing memlog.** Writing the file it is checking for would make the finding self-clearing and would author a decision record nobody decided.
- **A stamp is honest only after the judgment.** Working the presumed set down by stamping *first* and reasoning later is the laundering this Spec exists to end; measuring first and stamping second is reconciliation. The difference is invisible in the resulting number, which is exactly why the measurement has to be recorded in the memlog.
- **Do not clear a presumed entry by naming 994 literal paths.** The matcher would be satisfied and nothing would be recorded. Cluster judgments plus a scoped stamp say what was actually decided; a wall of paths says only that someone knew how the matcher works.

## Non-goals

- **Not re-homing this detector to Doctor.** That is Charter §6 work already scoped as Doctor's Epic 6 (S-6.1 → S-6.10). This Spec fixes the instrument where it lives; Marshal keeps the operational guard either way — only the *verdict* moves, later.
- **Not a general dependency or provenance graph.** The reconciliation claim is "does the memlog name this path", deliberately literal.
- **Not a rewrite of the coverage half.** Coverage works; the two `[ungoverned]` files are a missing entry, not a design flaw.
- **Not requiring a memlog of every Spec.** A Spec governing zero files cannot drift, and `exempt`/`sentinel:` contracts are declared, printed, and able to move. CAP-5 covers exactly the default mode over a non-empty governed set.
- **Not bulk-reconciling the 23-file steward cluster by stamping it.** If that surface genuinely changed, its contract moves — stamping it would be the laundering this Spec exists to end.
- **Not settling whether the detector suite should gate CI.** It already runs on every PR and push (`.github/workflows/detectors.yml`, `scope=repo` registry subset) but is deliberately **advisory** — an operator decision of 2026-07-31 that `docs/dreams/fidelity-enforcement.md` records as still open. This Spec makes the signal true; whether a true signal should block a merge is that Dream's call, not this one's.

## Success signal

`pixi run -e local-recipes spec-surface-check` exits **0** on `main` with every one
of the 61 findings dispositioned — reconciled, scoped-stamped with recorded
reasoning, or filed as deferred work — and the two defects proven fixed by mutation:
re-introducing the all-or-nothing stamp re-reds the isolation test, and
re-introducing the per-spec short-circuit re-reds the laundering test that replays
the live 63 → 61 incident.

And (CAP-5, added 2026-08-09) **no Spec can declare a surface it has no contract
for**: a governed spec with no `.memlog.md` reds the gate by name instead of
passing silently, the 7 live instances covering 396 files are dispositioned with a
memlog *and* a scoped stamp, and deleting any memlog from a governed spec re-reds
the gate.

## Assumptions

- The two `[ungoverned]` Charter files want a real surface rather than an allowlist exemption, since the Charter defines the chain the detector polices. Unconfirmed with the operator; an allowlist entry would also clear the finding.

## Open Questions

- Should `docs/governance/spec-pyforge-charter/` be governed by a surface (and whose?), or allowlisted as governance-tier content outside the station model?
- Which of the 34 `[drift]` findings are genuine surface changes whose contract must move (steward's Epic-2/3 delivery looks like one), versus already-reconciled work that only lacks a stamp? This partition is the bulk of CAP-3's work.
