---
title: Every capability ships behind a flag, and a gate no station owns checks that it does
type: dream
owner: guild
status: specified
# status: 2026-09-28 — seeded `dreamt` from the intake triage and ruled the same session: all seven
# open questions answered, so the Spec (docs/governance/spec-feature-flag-governance/) is `ready`.
fold-exemption: governance   # a gate over every Smith's stories: Charter §5 as amended 2026-09-14
                             # (the coverage-gate-independence shape, third instance). No Smith can
                             # own a rule that refuses its own stories.
---

# Every capability ships behind a flag

> **Seed Dream.** Triaged on 2026-09-28 from the intake
> `archive/docs/intake/bmad_feature_flag_governance_prompt.md`, under four operator rulings made the
> same day. The intake is a system prompt for BMAD's Architect, Builder and Test Architect (TEA). It
> says every new capability must go behind a feature flag, with no exceptions, and it gives a spec
> section, an implementation rule and an ON/OFF test pattern for each role.

## The Dream

A capability reaches `main` switched off. The operator turns it on, or off again, without a
redeploy. Every story that adds behaviour names its flag before any code is written. With the flag
off, the old behaviour holds. The story is tested in both states, and it says when the flag will be
removed. A gate that belongs to no station refuses any story that skips one of these steps. So
"is this new thing safe to ship?" always has the same answer: yes, because it is off until someone
turns it on.

## What is real

Measured on 2026-09-28 at `306d7563fd`.

- **The flag platform exists.** Steward Epic 26 is done (26.1–26.5), realizing
  `spec-pyforge-unifying-strategy` CAP-13, "Behaviour flips without a redeploy". canopy:AD-11,
  "Flags are OpenFeature FILE, in-process", describes it:
  - There is one JSON tree at `src/platform/config/flags.json`, mounted as a ConfigMap and watched
    in-process.
  - AD-11 says "Two trees is a review-blocking finding. No egress."
  - The evaluator is `django_pyforge/flags.py`, covering `evaluate_boolean`, the views, MCP
    `get_flag` and `python -m django_pyforge.flags`.
  - Story 48.5 added `doctor flags kill-switch`.
- **The tree holds two flags.** `pyforge.three_surfaces` is a demonstration flag with
  `defaultVariant: "on"`. `pyforge.cutover_root` is a string flag (fnd:AD-17).
- **A second tree already exists.** Steward's `sprint_ledger_query` (Story 65.1) resolves
  `--flag`, then `FLAGS_<NAME>`, then `.steward/flags.json`. That is the shape AD-11 calls
  review-blocking.
- **Per-environment overlays are deferred.** The steward spine's deferral table has the row "FILE
  flag env promotion overlays … overlay *values* per env are ops", deferred to the first CAP-13
  import story. So "off in production" cannot be expressed as a value today.
- **No test fixture exists.** `pyforge-testing-kit` has four mock families and no flag fixture. The
  only ON/OFF tests write two flagd trees by hand (`src/platform/tests/test_openfeature_file_flags.py`).
- **No story spec names a flag, and no check reads one.** The nearest precedent for a required
  story-spec section is marshal's `gate.check_spec_binding` (MRS-GATE-010/011). It runs at verify
  time, after the session.
- **No flag carries an owner, a story or a cleanup date, and nothing removes flags.**
- **Most tracked story specs are features.** 125 declare `type: feature`, 12 `chore`, 4 `docs`
  and 2 `fix`. The count comes from `grep -l '^type: <t>'` over
  `_bmad-output/projects/*/planning-artifacts/specs/spec-[0-9]*.md`.

## Operator rulings (2026-09-28)

1. **Every capability, blocking.** The operator chose this over "runtime surfaces only,
   advisory".
2. **A closed exemption list, plus a retrofit** that puts existing capabilities behind flags.
3. **Backlog stories warn until they are retrofitted.** A story spec minted after this Spec
   reaches `ready` is refused without a flag block or an exemption. A story already in backlog
   warns and joins the retrofit inventory, so dispatch keeps flowing.
4. **The Guild owns it.** The gate judges all eight Smiths, which is the Charter §5 shape of
   2026-09-14. Doctor owns the mechanism stories. Each Smith owns its own retrofit stories, as
   with `one-chain-per-station`'s per-station fold stories.

## What the intake gets right, and what does not transfer

The intake gets these right:

- The three mandates: the Architect declares the flag, the Builder wraps the new logic in it, and
  TEA tests both states.
- "Fallback behavior (flag OFF) perfectly mirrors current legacy behavior."
- Cleanup criteria belong in the spec.

These parts do not transfer to this estate:

- **Its providers.** Django-Waffle, LaunchDarkly and environment variables, with the mock target
  `waffle.flag_is_active`, all break AD-11 (one provider, one tree, no egress). The seam is
  OpenFeature. Its `InMemoryProvider` (`openfeature.provider.in_memory_provider`) is the test
  double.
- **Its Playwright pattern.** It injects flags through `sessionStorage`, but flags here are
  evaluated on the server. A browser test sets the tree before the server starts.
- **A repo-root `tests/conftest.py`.** There isn't one. The fixture belongs in
  `pyforge-testing-kit`, the seam every station already imports.
- **"Default State in Production: FALSE".** This cannot be expressed until per-environment
  overlays exist.
- **The `bmad-spec.md` file.** The contracts here are `SPEC.md` (five fields) and per-story specs.
  The Pre-Build Gate becomes a story-spec block, and the CAP names the flag it realizes.

## What it looks like when real

- Every story spec that adds behaviour carries either a `flag:` block or a `flag-exempt:` value.
  - The `flag:` block holds the key, the provider (always the one OpenFeature tree), the default
    per environment, the scope, the fallback and a cleanup date.
  - `flag-exempt:` takes a value from a closed list in `docs/governance/guild-roster.json`, the
    way `fold_exemptions` does.
- A gate outside every station package lives in `scripts/`, like `scripts/coverage_gate.py`. It
  reds four things:
  - a story spec that has neither a flag block nor an exemption;
  - a flag key the spec names that is not in the tree;
  - a key in the tree that no code reads;
  - a flag past its cleanup date.

  `detectors-ci` runs the gate. Marshal consults it at dispatch and refuses a story it would red,
  before a session starts.
- A story's `## Verification` names a test that runs both states through the testing kit's flag
  fixture.
- The tree records each flag's owner, story and cleanup date in flagd `metadata`. Per-environment
  overlays make "off in production" a value. `.steward/flags.json` folds into the one tree.
- `bmad-spec`, `bmad-build` and `bmad-tea` carry the mandate through `_bmad/custom/*.toml`, so every
  harness gets it and no installer-owned `SKILL.md` is edited.
- A CLI verb behind an OFF flag keeps its station's frozen exit codes. A detector behind an OFF
  flag reports `skipped (flag off)` and never a pass.
- The retrofit runs in two steps. First, an inventory of each station's existing capabilities.
  Then per-station stories put them behind flags that default ON, so each one becomes a kill switch.

## Constraints

- **One tree, one provider, no egress** (canopy:AD-11). No flagd daemon, no hosted service.
- **The hand that builds is never the gate that judges** (Charter §6). The gate ships outside every
  `pyforge.<station>` package, and its exemption list sits beside `guild-roster.json`.
- **Frozen exit-code domains hold in both states.** Examples: atlas's `{0,1,2,130}` and each
  station's `verdict.py`.
- **A flag-OFF check is never a silent green** ([[fidelity-enforcement]]).
- **The exemption list is closed.** Adding a value is a governance act, not a code change.
- **Isolation rules stand.** `src/platform/` never imports `pyforge.*`, and station code reads flags
  only through `pyforge.core` or `django_pyforge.flags`.

## Non-goals

- A flag service, a flagd daemon, or any SaaS flag provider.
- Experimentation analytics or percentage-rollout statistics.
- A second PR verdict. The gate is a detector inside the one merge gate (`detectors-ci`), and
  `warden scan` stays the sole dependency verdict.

## Open questions for the Spec — all seven ruled 2026-09-28

1. **What the gate reads as "a capability".** *Ruled:* a story spec of `type: feature` minted on or
   after the rule date. `fix`, `chore` and `docs` stories need no flag, because a fix restores
   intended behaviour and flagging it would keep the bug reachable.
2. **What the closed exemption list contains.** *Ruled:* `flag-infrastructure`, `docs-only`,
   `recipe-build`, `planning-ledger-only` and `detector-or-gate`. The last one exists because a
   gated gate reports a silent green.
3. **How a CLI verb behaves with its flag OFF.** *Ruled:* it stays listed in `--help`, marked
   disabled, and refuses with its station's usage exit code and a "flag off" message. The operator
   chose this over "absent, argparse exit 2".
4. **The cleanup policy.** *Ruled:* **90 days** after the flag is ON in every environment. The
   owning station files the removal story. The operator chose this over the recommended 30 days.
5. **Scope.** *Ruled:* global only in v1. Targeting rules (user and tenant) are a later CAP.
6. **Retrofit granularity.** *Ruled:* one flag per CAP.
7. **Timing.** *Ruled:* the same day. From the rule date, `detectors-ci` reds and Marshal refuses
   at once. The rule looks forward only, so it hits new stories only.

## Kinships

- [[pyforge-charter]]: §5 (the Guild shape) and §6 (the hand that builds is never the gate that
  judges).
- [[coverage-gate-independence]] and [[one-chain-per-station]]: the two earlier gates of this shape.
  Both keep their mechanism stories with Doctor.
- [[pyforge-steward]]: Epic 26, `spec-pyforge-unifying-strategy` CAP-13, canopy:AD-11, Story 48.5
  (the kill switch), and Story 65.1's second tree.
- [[pyforge-marshal]]: `gate.check_spec_binding`, `pyforge-testing-kit`,
  `spec-pyforge-testing-charter`, and the `_bmad/custom/` overrides.
- [[pyforge-doctor]]: the mechanism Smith.
- [[fidelity-enforcement]]: a skipped check is not a pass.
- The same-day seeds in [[pyforge-herald]], [[pyforge-steward]], [[pyforge-warden]],
  [[pyforge-atlas]] and [[pyforge-mason]] each carry a flag block from their first story.

## Realization log

- **2026-09-28** — Seeded from the intake during the triage of three intakes (the other two became
  station-Dream entries the same day). Four operator rulings are recorded above. The Spec is seeded
  `draft` at `docs/governance/spec-feature-flag-governance/`.
- **2026-09-28 (same session)** — The operator ruled all seven open questions (Spec memlog 23), so
  the Spec is `ready` and this Dream is `specified`. The rule date is 2026-09-28. CAP-1..7 are
  chosen. The mechanism stories go to Doctor (CAP-1, CAP-2, the CAP-7 inventory), Marshal (CAP-3,
  CAP-4, CAP-6) and Steward (CAP-5). The retrofit stories are minted by each Smith after the
  inventory lands. Status: **next, mint the mechanism stories**.
- **2026-09-28 (night)** — The mechanism stories are minted (Spec memlog 26–27).
  - **Doctor Epic 34:** 34.1 (CAP-1: the roster's closed list, the rule-date baseline, the block's
    one shape), 34.2 (CAP-2: the gate in `scripts/`, run by `detectors-ci`), 34.3 (CAP-2's
    metadata checks, `blocked` on steward 76.1 and 76.2), 34.4 (CAP-7's inventory) and 34.5
    (CAP-4's gate clause, `blocked` on marshal 74.1).
  - **Marshal Epic 74:** 74.1 (CAP-4: the testing kit's flag fixture), 74.2 (CAP-3: dispatch refuses
    before the session, `blocked` on doctor 34.2) and 74.3 (CAP-6: the `_bmad/custom/` mandate).
  - **Steward Epic 76** (CAP-5): 76.1 per-environment overlays, 76.2 the flag metadata, 76.3 the
    `.steward/flags.json` fold.

  Every mechanism story is itself `flag-exempt`. CAP-7's retrofit stories are each Smith's, minted
  after 34.4's inventory lands. Next: dispatch 34.1 and 74.1.
