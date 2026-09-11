---
spec: regenerable-factory
status: shipped
owner-dream: docs/dreams/regenerable-factory.md
companions:
  - waves.md
sources:
  - ../../../../../../docs/dreams/regenerable-factory.md
surface: []          # retired 2026-08-09 (Story 6.9) — the four chain-integrity
  # detectors this practice governed all moved into src/shared/packages/pyforge-doctor/**,
  # already governed by spec-pyforge-doctor's own blanket glob; see this spec's memlog
  # for the hand-off. This Spec's governance role over them ends here.
assumptions:
  - Backfilled specs can carry machine-checkable success signals grounded in
    existing behavior (the surfaces already work; the spec states the contract
    they satisfy).
open_questions: []
---

# SPEC — regenerable-factory program

## Why

Doctrine (user decision, 2026-07-23): realized work is not exempt from the
chain. Every realized surface gets Dream → PRD/spec backfilled so the factory
and personas own everything in the repo, any change flows idea → spec → BMAD,
and drift checks bind every file to its contract. The proven local-recipes
sync loop (deterministic detector + BMAD reconciler skills) generalizes
repo-wide. Wave 0 — the multi-loop isolation harness — already shipped
(`spec-multi-loop-isolation`), so this program's loop can run concurrently
with other loops (e.g. Warden 6.3).

## Capabilities

- **CAP-1 — surface-manifest convention.**
  Intent: every SPEC.md declares `surface:` — the repo paths/globs it
  governs; existing kernels (multi-loop-isolation, design-code-bridge) are
  retrofitted.
  Success: the checker (CAP-3) can enumerate every spec's surface; no spec
  without one.
  **Verified:** 2026-09-11 — mechanical re-verification (operator-directed capability-effect sweep), PARTIAL: `scripts/spec_surface_check.py::parse_surface` correctly enumerates every spec's `surface:` globs when present (confirmed live via CAP-3's own run below), but "no spec without one" does NOT currently hold — 22 `SPEC.md` files fleet-wide have no `surface:` frontmatter key at all (a scripted count against every `_bmad-output/projects/*/planning-artifacts/specs/spec-*/SPEC.md`), and the checker silently contributes zero coverage for them rather than flagging the omission. Real, current gap — not fixed here (which of the 22 legitimately need one is a per-spec judgment call, not a mechanical fix).

- **CAP-2 — backfill waves.**
  Intent: brownfield-`bmad-spec` each realized Dream per the wave order in
  `waves.md` (pilot first; `bmad-document-project` grounding for the two
  deep surfaces; chain-verify only where chains exist).
  Success: every realized Dream traces to a validated kernel with a surface
  manifest; each wave's spec self-validates with zero unresolved
  contradictions.
  **Verified:** 2026-09-11 — mechanical re-verification (operator-directed capability-effect sweep): the program itself completed (`.memlog.md`: "PROGRAM COMPLETE 2026-07-23: all 14 stories done" across CAP-1/2/3/4). Re-ran `dream-chain-check` for the CURRENT fleet-wide state (not the historical claim alone): 1 outstanding `dream-without-spec` gap (`marshal-launch-environment-integrity`, unrelated to this program's own backfill targets) plus 2 `spec-without-dream-link` findings. The waves this program executed are complete; the broader chain-completeness invariant they feed is not presently 100% clean fleet-wide — a known, separately-tracked gap, not something this CAP's own scope reopens.

- **CAP-3 — repo-wide surface checker.**
  Intent: a deterministic script reporting (a) coverage — every tracked
  source file maps to ≥1 spec surface or an explicit allowlist entry, and
  (b) drift — a governed file changed since its spec's recorded baseline
  without the spec/memlog moving.
  Success: exit 0 on a clean repo, non-zero with named findings otherwise;
  runs as a pixi task and joins the CI detector family.
  **Verified:** 2026-09-11 — mechanical re-verification (operator-directed capability-effect sweep): `pixi run -e local-recipes spec-surface-check` run live this pass — exit 2 (non-zero) with 47 named drift findings against the repo's current, actively-changing state (concurrent fleet work mid-flight), each naming the exact spec + changed/added path. Exactly the claimed coverage+drift behavior, exercised live, not a synthetic fixture.

- **CAP-4 — regeneration drill.**
  Intent: prove regenerability — delete a governed module (pilot:
  `pyforge.doctor.sources.fleet_scan`), rebuild it from its spec alone, pass the
  same verification the original passed.
  Success: one documented drill with a green outcome; the drill procedure
  recorded so it can be repeated on any governed surface.
  **Verified:** 2026-09-11 — mechanical re-verification (operator-directed capability-effect sweep): `spec-factory-console/drill-evidence.md` (dated 2026-07-23) documents a clean-room subagent rebuild of `pyforge.doctor.sources.fleet_scan` from `console-contract.md` alone — verdict PASS, both scripts' outputs byte-identical after timestamp normalization, `--source git` mode ran green (25 dreams scanned, correct tallies), procedure recorded (back up → install rebuild → run both modes → normalized diff → restore). Durable, dated evidence — not re-run this pass, since CAP-4 asks for one documented drill, not perpetual re-execution.

## Constraints

- The checker is a deterministic harness, not a skill (Marshal doctrine);
  it never false-greens (Warden temperament); the allowlist is explicit and
  logged — no silent exemptions.
- Backfilled specs describe what IS. The program does not rewrite shipped
  code to match aspiration; behavior changes are new stories under the spec.
- Execution is loop-driven on the Wave-0 harness. Waves touching CFE
  territory bind Rule 1 (invoke `conda-forge-expert`) and Rule 2 (closeout
  retro against the skill).

## Non-goals

- Decks for backfilled Dreams (Herald's backlog — a communication decision).
- Upstream bmad-method changes (tracked separately).
- 100% line-level formal verification — the contract is spec-per-surface,
  not proofs.

## Success signal

`spec_surface_check` green over the whole repo (every tracked source file
governed or allowlisted) with all realized Dreams carrying validated kernels;
plus one passed regeneration drill. Program-level: a subsequent behavior
change lands via spec-edit → loop story with the checker staying green.
