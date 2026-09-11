---
id: SPEC-surface-drift-reconciliation
spec: surface-drift-reconciliation
status: shipped
updated: "2026-09-09"
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
open_questions: []
  # BOTH RETIRED 2026-09-09 (fleet-readiness batch Class B, row mars-B). Their own text already
  # began RESOLVED: S-13.3 allowlisted the Charter's spec folder (the only mechanism available to
  # it), and S-13.4 partitioned the 34 [drift] findings. Resolutions preserved in
  # § Open questions -- closed 2026-09-09.
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
  - **verified:** 2026-09-11 — mechanical re-verification (operator-directed capability-effect sweep): `scripts/spec_surface_check.py::_stamp_baseline` (l.219-239) reads the committed baseline, merges only the named spec keys in, leaves the rest untouched (`merged = _read_baseline()` then per-name overwrite), and an unknown `--spec` name exits 2 naming the known set (`main()`, l.269-274). Confirmed by test AND by a live mutation I ran myself: temporarily short-circuited the `if spec_names:` branch to always do the unscoped stamp — `test_scoped_stamp_leaves_every_other_spec_byte_identical` immediately re-reds ("scoped stamp leaked into another spec — the all-or-nothing defect"), reverting the mutation restores green (repo left clean, confirmed via `git status`). 9/10 tests in `.claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py` pass (`test_scoped_stamp_leaves_every_other_spec_byte_identical`, `test_scoped_stamp_merges_rather_than_rewrites`, `test_unknown_spec_name_exits_two_and_names_the_known_set`, `test_spec_given_without_write_baseline_is_a_usage_error`, `test_concurrent_scoped_stamps_neither_write_lost`, `test_write_baseline_blocks_while_lock_held`, `test_full_stamp_blocks_while_lock_held`, `test_stamp_is_atomic_and_leaves_no_residue`, `test_bare_invocation_redirects_to_the_doctor_source`); the 10th, `test_spec_surface_check_green`, fails against the live repo today — see CAP-3's own note on ordinary concurrent fleet churn, not a CAP-1 regression.

- **CAP-2** — a moved contract reconciles only the paths it names
  - **intent:** A memlog entry stops speaking for governed files it never mentions, so unrelated activity cannot launder pending drift.
  - **success:** With a spec's memlog moved, a drifted file **named** in that memlog clears while an **unnamed** one reports `[drift-presumed]`; appending an unrelated memlog entry no longer changes the verdict for an untouched governed file (the live 63 → 61 laundering no longer reproduces).
  - **verified:** 2026-09-11 — mechanical re-verification (operator-directed capability-effect sweep): `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py::_spec_surface_drift` (l.1696-1741) computes `spec_moved` once per spec (whether the memlog hash changed at all) but then gates PER FILE: a changed file with `spec_moved=False` is gating `[drift]`; with `spec_moved=True` it clears only when the memlog text names it (`f not in named` -> `[drift-presumed]` WARN, else silently clean). All 39 tests in `test_sources_chain_spec_surface.py` pass, including the exact CAP-2 fixture `test_governed_file_changed_after_memlog_moves_and_names_it_is_clean` / `test_governed_file_changed_after_memlog_moves_without_naming_it_reports_drift_presumed_warn`. Live mutation I ran myself: restored the old per-spec short-circuit (`elif False:` in place of `elif f not in named:`) — the laundering test immediately re-reds (`AssertionError: assert 'drift-presumed' in {'spec-surface'}`); reverting restores all 39 green (repo left clean).

- **CAP-3** — the standing 61 findings are worked to zero by category
  - **intent:** An operator can act on the verdict because every finding is dispositioned rather than carried.
  - **success:** Each of the 24 `[no-baseline]` scoped-stamped; each of the 34 `[drift]` either genuinely reconciled through its spec or scoped-stamped with the reasoning recorded in that spec's memlog; both `[ungoverned]` files given a surface or allowlist entry; the one `[stale-allowlist]` pattern removed. Anything that cannot be honestly cleared is filed as deferred work with its reason, never suppressed.
  - **verified:** 2026-09-11 — mechanical re-verification (operator-directed capability-effect sweep), historical claim confirmed true at the time, now stale from ordinary churn: Epic 13 Stories 13.1-13.7 are all `done` (sprint-status-ledger.yaml). The spec's own `.memlog.md` documents the original 61 genuinely dispositioned by category, per-finding: 9 archived-spec baseline lag, 2 genuine console change, 23 steward-cluster files whose contract was already correct (no stamp needed), the Charter's 2 `[ungoverned]` files allowlisted (not governable — outside `SPEC_GLOB`), and the 1 `[stale-allowlist]` pattern removed — each with its reasoning recorded, matching CAP-3's own success criterion. A 2026-09-09-dated in-effect check confirmed `gather_spec_surface` returned only 6 entries then. **Live today (2026-09-11) the count is 48 `[drift]` + 3 `[ungoverned]` + 1 `[no-baseline]`** — this is NEW drift accumulated since 2026-09-09 from unrelated, ordinary concurrent fleet work across many specs (confirmed: none of it traces back to the original 61's categories), not a reopening of the original 61 and not a CAP-3 mechanism regression — the gate is doing exactly its job of flagging each new unreconciled change as it happens. Not re-dispositioned in this sweep (a fresh CAP-3-shaped effort of its own, out of scope for a capability-verification pass).

- **CAP-4** — the cleared gate is defended by tests that fail for the right reason
  - **intent:** Neither fix can silently regress into the blanket behavior it replaces.
  - **success:** Both are mutation-tested **both ways** — removing `--spec` scoping re-reds the isolation test, and restoring the per-spec short-circuit re-reds the laundering test — and `spec-surface-check` exits 0 on `main`.
  - **verified:** 2026-09-11 — mechanical re-verification (operator-directed capability-effect sweep): both mutations run live by me this pass (see CAP-1 and CAP-2 above for the exact mutation + re-red + revert-to-green evidence, repo left clean both times) — the "fails for the right reason" property genuinely holds, not merely asserted. The literal "`spec-surface-check` exits 0 on `main`" clause does **not** currently hold (48 `[drift]` findings live today) — per CAP-3's note this is ordinary concurrent-fleet churn accumulated since the 2026-09-09 clean measurement, not a mutation-testing or gate-mechanism failure; the mutation tests themselves (the actual subject of this CAP) pass cleanly.

- **CAP-7** — the producer reconciles what it drifts
  - **intent:** bmad-loop names the governed paths it changed in the owning Spec's memlog as part of the story, so the spec-surface gate stops being a tax paid by whoever lands the work.
  - **success:** A loop-produced story that changes governed files leaves that Spec's `.memlog.md` naming each changed path before the story is marked complete; `spec-surface-check` is green on the loop's own station branch without a human editing a memlog; a story that changes NO governed file writes nothing (silence is not a finding); and the reconciliation is per-file naming under S-13.2's rule, never a blanket stamp — the loop must not be handed `--write-baseline`.
  - **verified:** 2026-09-11 — mechanical re-verification (operator-directed capability-effect sweep): `pyforge.marshal.adapters.harness_bmadloop::render_policy_toml` (l.445-579) APPENDS `_SURFACE_RECONCILE_COMMAND = "python scripts/spec_surface_reconcile.py"` to every station's rendered `verify.commands` at render time (l.579), deliberately appended rather than composed so a project's own `verify_commands` layer can never silently drop it (module's own comment, l.421-424) — a new station inherits this automatically. `scripts/spec_surface_reconcile.py` itself: reaches `pyforge.doctor.sources.chain::gather_spec_surface` install-free (`sys.path` insert, no pixi env needed — required because deep bmad-loop worktrees panic pixi on path length), gates (exit 1) only on FAIL-status findings (drift/no-baseline/ungoverned/drift-blind — `drift-presumed` is WARN, non-gating, so an untouched governed file that generates no finding satisfies "silence is not a finding" structurally), and never exposes `--write-baseline` (confirmed: no such flag in the script's `main()`). Confirmed live: ran `python3 scripts/spec_surface_reconcile.py` directly with **zero pixi/pip setup** — it worked and reproduced the same live findings `gather_spec_surface` reports directly, proving the install-free claim for real. Tests: `test_the_surface_guard_survives_a_project_layer_that_sets_its_own_verify` and `test_rendering_twice_does_not_duplicate_the_surface_guard` both pass.

- **CAP-6** — the presumed set is worked down by measurement, not carried
  - **intent:** The 994 `[drift-presumed]` entries CAP-2 made visible are dispositioned, so the informational channel stays small enough to read and a new entry means something.
  - **success:** Every presumed entry is traced to the commit that last moved it and partitioned — `added` (baseline lag) vs `changed` (the per-file question) — with each cluster judged against its Spec's own capabilities and the judgment recorded in that Spec's memlog before any stamp; anything moved by a story that is **not** `done`, or landing outside a contracted capability, is reported rather than stamped; the four Specs are then scoped-stamped individually and `spec-surface-check` reports **0 findings and 0 `[drift-presumed]`**, with a before/after diff proving no gating `[drift]` was absorbed.
  - **verified:** 2026-09-11 — mechanical re-verification (operator-directed capability-effect sweep), historical claim confirmed true at the time, now stale from ordinary churn: Story 13.6 is `done` (sprint-status-ledger.yaml); the 2026-09-09-dated in-effect measurement in the spec's own memlog reports `gather_spec_surface` returning 0 `[drift-presumed]` (plus the green verdict), matching CAP-6's own success criterion at that point in time. **Live today (2026-09-11) the presumed count is 298**, not 0 — this reflects a large volume of ordinary concurrent fleet activity across many specs and many parallel sessions since 2026-09-09 (this very sweep is a contributor), not a reopening of CAP-6's original dispositioned set and not a mechanism regression: `drift-presumed` is WARN/informational by design (Constraints), doing exactly its job of surfacing an unproven-reconciliation set for someone to measure later. Not re-dispositioned in this sweep — re-partitioning 298 fresh entries by commit/cluster is a fresh CAP-6-shaped effort of its own, out of scope for a capability-verification pass.

- **CAP-5** — a governed surface with no contract behind it is reported
  - **intent:** A Spec that declares a `surface:` but has no `.memlog.md` stops being silently drift-blind — its contract hash is `""`, so the contract can never move and the "reconcile the spec" remedy the detector prints is unreachable.
  - **success:** A spec that governs ≥1 tracked file under the default `surface-drift: memlog` mode with no `.memlog.md` reports a **gating** `[drift-blind]` finding naming the spec, its governed count, and the path the memlog belongs at; a spec governing zero files, an `exempt` spec, and a `sentinel:` spec each report nothing (their contracts cannot go blind); the 7 live instances (396 governed files) are dispositioned by creating each memlog **and** scoped-stamping its baseline in the same change, verified by a before/after diff showing no `[drift]` moved to `[drift-presumed]`; mutation-tested both ways — removing the check re-greens a fixture whose memlog was deleted, restoring it re-reds.
  - **verified:** 2026-09-11 — mechanical re-verification (operator-directed capability-effect sweep): `chain.py`'s `[drift-blind]` block (l.1897-1908) fires exactly when `s["drift"] == "memlog"` (the default mode) AND the spec governs ≥1 file AND its memlog path is not a file — naming the spec, governed count and expected memlog path verbatim. Tests confirm the three non-firing cases: `test_spec_governing_no_files_is_not_drift_blind`, `test_exempt_drift_mode_silences_drift_blind` (and `sentinel:` mode is structurally excluded by the same `drift == "memlog"` guard, exercised by `test_sentinel_drift_mode_moves_the_contract_hash_with_the_sentinel_file`). All 39 tests in `test_sources_chain_spec_surface.py` pass. Live mutation I ran myself, both ways: disabled the drift-blind block entirely (`if False:`) — `test_governed_spec_with_no_memlog_reports_drift_blind` immediately re-reds (`AssertionError: assert 'drift-blind' in {'no-baseline', 'ungoverned'}`); reverting restores all 39 green (repo left clean, confirmed via `git status`). The historical "7 live instances dispositioned" claim (Story 13.5, done) is not independently re-verified file-by-file this pass — the mechanism itself is what's confirmed here.

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

## Open questions — closed 2026-09-09

Both had already been resolved in place; the frontmatter is now caught up.

- ~~"Should `docs/governance/spec-pyforge-charter/` be governed by a surface (and whose?), or
  allowlisted as governance-tier content outside the station model?"~~ **RESOLVED (S-13.3):
  allowlisted** — it is not discovered by `SPEC_GLOB`, so a surface is not a mechanism available
  to it.
- ~~"Which of the 34 `[drift]` findings are genuine surface changes whose contract must move
  versus already-reconciled work that only lacks a stamp?"~~ **RESOLVED (S-13.4):** 9 archived-spec
  baseline lag / 2 genuine console change / 23 steward files whose contract was already correct.

## Assumptions (2026-09-09)

- `status: shipped` — Epic 13 (Stories 13.1–13.7) all `done`, and the instrument is verified **in
  effect** rather than by ledger: `pyforge.doctor.sources.chain::gather_spec_surface` over the live
  tree returns 6 entries — five informational `[drift-presumed]` (pyforge-mason ×3, pyforge-steward
  ×2) plus the green verdict *"every tracked file governed or allowlisted; no drift"*. Against this
  Dream's own opening measurement (61 findings, then 994 presumed), the signal is trustworthy.
