---
spec: feature-flag-governance
status: ready   # 2026-09-28 — seeded `draft` from the intake triage (docs/dreams/feature-flag-governance.md)
                # and ruled the same day. Four scope rulings (memlog 3) and the seven open questions
                # (memlog 23) are all settled, so downstream may bind. The rule date is 2026-09-28.
                # Lives under docs/governance/ because its Dream is guild-owned (chain.py
                # `_expected_spec_dir`: guild -> docs/governance/spec-<slug>/). This is the third
                # instance of the Charter §5 shape, after coverage-gate-independence and
                # one-chain-per-station.
created: "2026-09-28"
updated: "2026-09-28"
owner-dream: docs/dreams/feature-flag-governance.md
fold-exemption: governance   # a gate over every Smith's stories (Charter §5, the 2026-09-14 shape); chain-sprawl-check reads it here too
surface: []     # Deliberately empty until the mechanism stories land. The gate will be a scripts/
                # check, declared here when it exists, the way coverage-gate-independence declares
                # its evaluator. The flag platform (CAP-5) stays under spec-pyforge-steward's surface,
                # and the testing-kit fixture (CAP-4) under spec-pyforge-testing-charter's.
companions: []
sources:
  - ../../../docs/dreams/feature-flag-governance.md
  - ../../../archive/docs/intake/bmad_feature_flag_governance_prompt.md
open_questions: []
  # RAISED 2026-09-28 (seed) AND CLOSED 2026-09-28 (operator ruling, same session; memlog 23):
  #   what-the-gate-reads-as-a-capability    -> a post-rule-date story spec of type: feature; fix/chore/docs need no flag
  #   the-closed-exemption-list              -> flag-infrastructure, docs-only, recipe-build, planning-ledger-only, detector-or-gate
  #   cli-verb-behaviour-with-its-flag-off   -> listed in --help as disabled; refuses with the station's usage code and a 'flag off' message
  #   cleanup-policy                         -> 90 days after ON in every environment; the owning station files the removal story
  #   scope-global-or-targeted               -> global only in v1; targeting rules are a later CAP
  #   retrofit-granularity                   -> one retrofit flag per CAP
  #   ci-red-timing                          -> the same day: detectors-ci reds and marshal refuses from the rule date
---

> **Canonical contract.** Seeded 2026-09-28 from `.memlog.md`, the decision of record, and from the
> Dream in `sources:`. It was ruled the same session and is now the complete contract for what to
> build, test and validate. The Dream in the frontmatter is for traceability only.

# SPEC — every capability ships behind a flag, and a gate no station owns checks that it does

## Why

The estate can already flip behaviour without a redeploy. Steward Epic 26 realized
`spec-pyforge-unifying-strategy` CAP-13 with an OpenFeature FILE provider over one JSON tree
(canopy:AD-11: *"Two trees is a review-blocking finding. No egress."*). Almost nothing uses it,
though. The tree holds two flags: a demonstration and the cutover root. No story spec names a flag,
no check reads one, no flag carries an owner or a cleanup date, and a second tree has grown in
steward (`.steward/flags.json`, Story 65.1).

The operator ruled on 2026-09-28 that every capability ships behind a flag and that a gate enforces
it. That gate refuses stories from all eight Smiths. No Smith can own a rule that refuses its own
stories, so the rule is the Guild's (Charter §5 as amended 2026-09-14). Its evaluator ships outside
every station package (Charter §6).

## Operator rulings (2026-09-28)

Scope (memlog 3):

1. **Every capability, blocking.**
2. **A closed exemption list, plus a retrofit** of existing capabilities.
3. **Backlog warns, new work is refused.** Story specs minted on or after the rule date are
   refused without a flag block or an exemption. Stories already in backlog warn until they are
   retrofitted.
4. **The Guild owns the rule.** Doctor owns the mechanism stories. Each Smith owns its own retrofit
   stories.

The seven open questions (memlog 23):

- **Q1:** a *capability* is a post-rule-date story spec of `type: feature`. `fix`, `chore` and
  `docs` stories need no flag, because a fix restores intended behaviour and flagging it would keep
  the bug reachable.
- **Q2:** the closed exemption list is `flag-infrastructure`, `docs-only`, `recipe-build`,
  `planning-ledger-only` and `detector-or-gate`.
- **Q3:** a CLI verb whose flag is OFF stays **listed** in `--help`, marked disabled. It refuses
  with its station's usage exit code and a "flag off" message.
- **Q4:** a flag may live **90 days** after it is ON in every environment. The owning station files
  the removal story.
- **Q5:** flags are global only in v1. Targeting rules (user, tenant) are a later CAP.
- **Q6:** the retrofit uses one flag per CAP.
- **Q7:** from the rule date, `detectors-ci` reds and Marshal refuses on the same day.

## Capabilities — chosen 2026-09-28

- **CAP-1 — the rule and its block.**
  - *intent:* Every story spec of `type: feature` minted on or after 2026-09-28 carries one of two
    things. The first is a `flag:` block: the key, the provider (the one OpenFeature tree), the
    default per environment, the scope (`global` in v1), the fallback (the legacy behaviour) and a
    cleanup date. The second is a `flag-exempt:` value from a closed list in
    `docs/governance/guild-roster.json`.
  - *success:*
    - The roster carries `flag_exemptions` holding exactly `flag-infrastructure`, `docs-only`,
      `recipe-build`, `planning-ledger-only` and `detector-or-gate`, with a "governance act"
      `$comment`.
    - The block's shape is documented where `bmad-build` and Marshal read story specs.
    - A machine can identify a post-rule-date `type: feature` spec that carries neither.
- **CAP-2 — the gate ships outside every station.**
  - *intent:* A check in `scripts/`, in the `scripts/coverage_gate.py` shape, reds five cases:
    - a post-rule-date `type: feature` story spec with neither a block nor an exemption;
    - an exemption value not on the closed list;
    - a flag key that is not in the tree;
    - a key in the tree that no code reads;
    - a flag still in the tree 90 days after it went ON in every environment.

    It warns, and never reds, on stories minted before the rule date.
  - *success:* `detectors-ci` runs the gate from the rule date. No `pyforge.<station>` module hosts
    it, and a meta-test or import-linter contract pins that. *Mechanism stories: Doctor's.*
- **CAP-3 — dispatch refuses before the session, not after.**
  - *intent:* Marshal consults the CAP-2 gate during dispatch preflight and refuses a story the gate
    would red, with a named MRS code, before any session starts. MRS-GATE-010 refuses only after
    the work is done.
  - *success:* Dispatching a post-rule-date `type: feature` story that has no flag block exits with
    the refusal and zero changed paths. A pre-rule-date story dispatches with a warning. The refusal
    starts the same day CAP-2 reds in CI. *Stories: Marshal's.*
- **CAP-4 — both states are tested through one fixture.**
  - *intent:* `pyforge-testing-kit` ships a flag fixture and an ON/OFF parametrize helper. The
    fixture uses OpenFeature's `InMemoryProvider` for unit tests, and a temporary flagd FILE tree
    for integration tests and for Playwright against a started server. A flagged story's
    Verification names such a test. For a CLI verb, the OFF case asserts that the verb is listed as
    disabled and that it refuses with the station's usage code.
  - *success:* The kit's own tests exercise both states. The CAP-2 gate can tell when a story's
    Verification names no two-state test. *Stories: Marshal's (the kit is Marshal's cross-station
    seam).*
- **CAP-5 — the tree can say what the rule needs.**
  - *intent:*
    - Per-environment overlays make "off in production" a value.
    - Each flag carries its owner, story key, created date, ON-everywhere date and cleanup date in
      flagd `metadata`.
    - Steward's `.steward/flags.json` folds into the one tree, fixing AD-11's review-blocking shape
      now.
  - *success:* There is one tree with per-environment values, and the CAP-2 gate reads its metadata,
    including the 90-day clock. `sprint_ledger_query` evaluates through OpenFeature. *Stories:
    Steward's.*
- **CAP-6 — every harness hears the mandate.**
  - *intent:* `_bmad/custom/bmad-spec.toml`, `bmad-build.toml` and `bmad-tea.toml` carry the
    Architect, Builder and TEA mandates (declare the flag, wrap the logic, test both states) as
    persistent facts or review layers. No installer-owned `SKILL.md` is edited.
  - *success:* A fresh `bmad-build` session on a flagged story names the flag key and the two-state
    test without being prompted. `bmad-method update` preserves the overrides. *Stories: Marshal's.*
- **CAP-7 — the retrofit.**
  - *intent:*
    - Doctor inventories each station's existing CAPs whose code is reachable at runtime (portal,
      REST, MCP tools and CLI verbs) against the tree.
    - Each Smith then mints its own retrofit stories, one flag per CAP, defaulting ON so each flag
      works as a kill switch.
    - Every pre-rule-date backlog story gains a block or an exemption.
  - *success:* The inventory is a checked-in report per station. The CAP-2 warnings reach zero. No
    station's exit-code domain changes. *Inventory: Doctor's. Retrofit stories: each Smith's, minted
    after the inventory lands.*

## Constraints

- **One tree, one provider, no egress** (canopy:AD-11). No flagd daemon, no hosted service, no
  second format.
- **The hand that builds is never the gate that judges** (Charter §6). The evaluator ships outside
  every `pyforge.<station>` package, and the exemption list sits beside `guild-roster.json`.
- **Frozen exit-code domains hold in both flag states.** Examples: atlas's `{0,1,2,130}` and each
  station's `verdict.py`. An OFF verb refuses with the station's existing usage code; it mints no
  new code.
- **A flag-OFF check is never a silent green** (fidelity-enforcement). A gated detector reports
  `skipped (flag off)`, and gates themselves are exempt (`detector-or-gate`).
- **The exemption list is closed.** Changing it is a governance act, not a code change.
- **Isolation holds.** `src/platform/` never imports `pyforge.*`, and station code reads flags only
  through `pyforge.core` or `django_pyforge.flags`.
- **"Off in production" waits for CAP-5.** It cannot be required until per-environment overlays
  exist, so CAP-5 is a prerequisite of CAP-2's `default per environment` check, not a waiver of it.

## Non-goals

- A flag service, a flagd daemon, or any SaaS flag provider (LaunchDarkly, Waffle, environment
  variables as a provider).
- Targeting rules (user, tenant) in v1 (Q5), and experimentation analytics or percentage-rollout
  statistics.
- Flags for `fix`, `chore` or `docs` stories (Q1).
- A second PR verdict. The gate is one detector inside the one merge gate (`detectors-ci`), and
  `warden scan` stays the sole dependency verdict.
- Editing installer-owned BMAD `SKILL.md` files. The mandate travels through `_bmad/custom/`
  overrides.

## Success signal

- A `type: feature` story spec minted on or after 2026-09-28, with no flag block and no exemption,
  is refused twice: once at `marshal factory dispatch` before any session starts, and once by
  `detectors-ci` on its PR.
- A flagged story ships with a test that runs both states.
- The tree names that flag's owner, story and cleanup date, and the gate reds the flag 90 days
  after it went ON everywhere.
- After the retrofit, every station's runtime CAPs sit behind default-ON flags. The gate's backlog
  warnings read zero.

## Open Questions

None. All seven were ruled on 2026-09-28 (memlog 23). The answers are in § Operator rulings and in
the frontmatter comment.

## Who does the work

| CAP | Smith | Where the stories go |
|---|---|---|
| CAP-1, CAP-2, CAP-7 (inventory) | doctor | doctor `epics.md` and ledger; the code goes in `scripts/` and `docs/governance/` |
| CAP-3, CAP-4, CAP-6 | marshal | marshal `epics.md` and ledger |
| CAP-5 | steward | steward `epics.md` and ledger |
| CAP-7 (retrofit) | each of the eight | each station's `epics.md`, minted after the inventory lands |
