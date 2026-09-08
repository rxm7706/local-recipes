---
title: "PRD Addendum — mechanisms, and why they were chosen"
chain: "bmad-suite-lifecycle"
created: "2026-09-06"
updated: "2026-09-06"
---

# PRD Addendum

The PRD states capabilities. This states mechanisms — the technical-how it keeps out — and the
rationale behind decisions already made, so the architecture pass confirms them.

## Provisioning paths (suite:FR-2, suite:FR-5, suite:FR-6)

- `steward provision --module {utility-skills,tea,bmb,cis}` → `provision.py` `_SUPPORTED_MODULES`:
  `CondaInstallBackend(installer="bmad-<x>-install", …)` for utility-skills/TEA/CIS,
  `SetupSkillBackend` for bmb. Re-provision of an installed module is idempotent; skill-name
  collisions are checked before first wire. The bmb backend deliberately never passes
  `--legacy-dir` and never invokes `cleanup-legacy.py` (it would `rmtree` this repo's
  `_bmad/core/config.yaml`); suite:FR-2's acceptance test pins that.
- Manticore: `steward provision --module manticore` exists but installs into the repo; the studio
  path is the documented native one — `npx bmad-method install --custom-source
  https://github.com/bmad-code-org/bmad-manticore` run from the studio root, `[modules.manticore]`
  written by `mc-setup` into the studio's `_bmad/custom/config.toml`. A `--studio <dir>` flag on
  steward is a later story only if the native path proves clumsy.
- labs: `npx skills add bmad-labs/skills --skill <name>` per consented skill; never the marketplace.

## The TEA equivalence check (suite:FR-4)

Before deleting `_bmad/scripts/bmad_tea_playwright.py`: run the generator once more (`--all`),
keep its eight outputs; run TEA's `bmad-testarch-test-design` / `-framework` per station; diff
section-by-section (story-id coverage, test-inventory rows, the `TBD`-free invariant). The check
passes when every story id and test path the generator emitted is present in the TEA output.
If it fails, suite:FR-4 narrows to the review lens and the generator stays (Spec assumption 1).

## The `--no-shims` apply (suite:FR-10)

Steward Story 14.9 adds `--no-shims` to `steward upgrade bmad-core --apply`: one argv element
after `--modules …`, a report line naming the shims the CAP-1 pre-flight lists, an argv assertion
in `test_upgrade_apply.py`. The retirement run is a same-version apply (`--target 6.12.0`,
installed 6.12.0 — accepted with a note, `upgrade.py:1284`) on a named review branch, with both
`--package-root` and `--installed-package-root` pointing at the cached 6.12.0 package so CAP-8
re-applies the seven local customizations by three-way merge. Order: harness flip + 8 re-renders +
caller gloss first (Story 30.5), then the apply, then `prove-landed`.

## The `@next` rehearsal (suite:FR-8)

Throwaway worktree; `--installer` pointed at `npx bmad-method@next` (`6.12.1-next.0` on
2026-09-06); one planted conflicting edit in an installer-owned skill file; `PATH` without `node`.
Report only; findings appended to the core-upgrade memlog; the worktree deleted. It answers the
`@next` open question and exercises CAP-8's conflict path and CAP-6's pixi-bin fallback, which the
same-version apply cannot.

## Rejected alternatives

- **skf as the sole authoring path (BMB skipped).** Rejected by the operator 2026-09-06: BMB's
  agent/workflow builders cover persona authoring that skf's domain-skill compiler does not.
- **TEA as a review lens only, generator kept.** Rejected: the operator chose full adoption; the
  equivalence check is the safety net.
- **Shims stay until v7 (the era-alignment constraint).** Rejected: v7 has no date, the cutover
  assumes no shims, and the same-version apply is the cheapest live exercise of CAP-6/7/8.
- **A new `DEFERRED_SPECS` registration for the Spec.** Not needed: the Spec lands `ready` and
  decomposed in the same PR, so INV-A is satisfied without touching `board.py`.

## Sizing (for the epic pass)

Era tail (session 2): five marshal stories + two steward stories + the apply ≈ 4–6 h agent time.
Adoption: steward Epic 46 (10 stories, S–M), Epic 47 (5, S–M), marshal Epic 31 (6, one L for the
TEA migration), doctor Epic 20 (5), warden 11 (2), herald 18 (3), scribe 7 (1), atlas 24 (1),
mason 14 (1) ≈ 3–4 further sessions drained by Marshal.
