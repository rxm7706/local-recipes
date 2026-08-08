# Retrospective — pyforge-warden Epics 1 & 2

- **Date:** 2026-07-17
- **Facilitated by:** Rxm7706 (solo operator) + Claude, grounded in first-hand bmad-loop execution
- **Scope:** Epic 1 "Spine + PyPI engine (walking skeleton)" (1.1–1.9) + Epic 2 "The conda/pixi source-manifest wedge" (2.1–2.6)
- **Status:** 15/15 stories done & merged · 999/999 tests green · built interleaved via bmad-loop (Epic 2 first, then the Epic-1 tail 1.7–1.9)

> Note on format: the `bmad-retrospective` skill scripts a fictional multi-person team.
> This is a solo, AI-driven bmad-loop effort, so this retro is written grounded in what
> actually happened — no fabricated team dialogue or invented conflicts.

## Delivery snapshot

| Metric | Value |
|---|---|
| Stories completed | 15 / 15 (Epic 1: 9/9, Epic 2: 6/6) |
| Tests at close | 999 passing (grew 616 → 938 → 999; never a red landing) |
| Manual merge interventions | 3 of 9 stories this session (2.6, 2.2, 1.7) |
| Multi-cycle reviews | 2 stories (2.1, 2.2); 2.2 hit the 3-cycle cap |
| Heaviest / lightest active-compute | 2.2 ≈194 min / 1.8 ≈35 min |

## What went well

- **Never a red landing.** Test count grew monotonically 616 → 938 → 999; every story merged green. The false-green backstop + corpus-conformance gate held as designed — the whole point of a fail-closed compliance tool, proven on itself.
- **The contract stayed frozen and honored.** The `ComplianceReport` schema / verdict-lattice / exit-code contract from Story 1.1 survived all 15 stories. Even 1.9's "resolved scan set" schema addition was backward-compatible.
- **Adversarial review earned its keep where it fired.** Story 2.2's review cycles caught **two genuine bugs live** — a deptry front-door PEP-440 crash and a YAML billion-laughs amplification — plus ~7 correctly-forward-scoped deferrals. External Gemini review on the pushed batches caught two more real defects (the 5-path `stale_findings` propagation gap; the CRLF brace-neutralization bug).
- **A deterministic velocity signal emerged.** Deep edge-case / IO-matrix stories (2.2 ≈194, 2.3 ≈148, 1.9 ≈137 min) ran ~2–3× the identity / lockfile / renderer stories (1.8 ≈35, 1.6 ≈49, 2.5 & 1.7 ≈67 min). Predictable by *story shape*, not epic label.

## What was harder than it should have been

- **The merge/cleanup phase is the fragile part, not dev.** 3 of 9 stories this session needed manual merge intervention:
  - **2.6** — a power-loss crash killed the run mid-dev; the worktree survived with complete, green work that had to be landed by hand.
  - **2.2** — deferred at the 3-review-cycle cap despite being sound (999-adjacent green, every finding forward-scoped); landed manually.
  - **1.7** — escalation: an uncommitted `pixi.toml`/`pixi.lock` in the target tree blocked the auto-merge; committed separately, then cherry-picked the story.
- **pixi.lock contamination.** Running `pixi install` inside a bmad-loop worktree baked worktree-local absolute paths into `pixi.lock` (2.6 + the general pattern). Fix each time: re-resolve from the repo root, not the worktree.
- **The gitignored paper-trail gap (recurring).** `implementation-artifacts/` is Tier-3 gitignored, so story spec-docs and `deferred-work.md` appends vanish when a worktree auto-cleans after a clean merge. Story 1.9's spec was actually lost this way. Flagged repeatedly across the session; still unaddressed at the orchestrator level. **→ tracked action item.**

## Cross-epic lessons

1. The bmad-loop **dev** phase is reliable; the **merge / cleanup** phase is where the real friction lives — every manual intervention this session was at merge time, never in the code.
2. Heavy IO-matrix stories deserve either a planning-time split or a higher `max_review_cycles` — the 3-cap deferred a sound Story 2.2.
3. The deferred-work ledger accumulated real, correctly-owned findings; several are owned by **Epic 3's ConfigLoader (3.1)** (freeze the mutable policy dicts, the coverage-floor gate), so 3.1 must consciously pick them up.

## Readiness assessment — clear to proceed to Epic 3

| Dimension | State |
|---|---|
| Tests / quality | 999 green, no red landings; false-green backstop + conformance gate are the teeth |
| Contract stability | `ComplianceReport` frozen since 1.1, honored through 1.9's additive schema change |
| Prerequisite gaps for Epic 3 | None — Epics 1&2 self-contained; 3.1 `ConfigLoader` hooks already stubbed throughout |
| Deployment / publication | Not published — **correct**, gated behind Epic 6.6 (release gate) by design |
| Stakeholder acceptance | N/A (solo operator) |

## Action items

### Tracked (recorded in sprint-status.yaml)

- **Fix the bmad-loop paper-trail gap** — sync gitignored `implementation-artifacts/` (specs + `deferred-work.md`) back to the main checkout before a worktree is torn down after a clean merge. Recurring loss (1.9's spec vanished this way); affects every future story.

### Recommendations (noted, not tracked — surfaced but de-prioritized by the operator)

- Pre-launch clean-tree guard so an uncommitted file can't block an auto-merge with an escalation (the 1.7 class).
- Split or raise `max_review_cycles` for heavy IO-matrix / extraction stories (the 2.2 class).
- Ensure Story 3.1 (ConfigLoader) explicitly picks up its owned deferrals: freeze the mutable policy dicts (e.g. `MappingProxyType`) + the coverage-floor gate.

## Next epic — Epic 3: Policy control + auditable waivers + warn-only

Stories 3.1 (Configurable policy / the ConfigLoader), 3.2 (Auditable expiring waivers), 3.3 (Waiver expiry + warn-only adoption on-ramp). No significant discoveries in Epics 1&2 that invalidate the Epic 3 plan — the direction is sound; 3.1 is the natural next wedge (it has accumulated hooks waiting throughout the shipped code).
