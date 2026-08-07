---
title: 'Landing rules as declared policy'
type: 'feature'
created: '2026-08-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: []
baseline_revision: '9c048a9c2dafef805648a055e60f1eb5e9835976'
---

<intent-contract>

## Intent

**Problem:** landing rules — required checks, merge strategy, labels, branch retirement, resync, repo-specific triggers (AD-40's own enumeration) — exist today only as a memorized habit and a `CLAUDE.md` prose paragraph (this repo's own two real rules: the `maintenance` label for any change outside `recipes/`, and the ungated `environment.yaml` sync check). Story 4.3's `land-story` and the later `marshal land`/`marshal deploy`/branch-retirement stories (4.8, 4.10) all need one governed source for these facts; without it, each would either hard-code them or invent its own reading.

**Approach:** four new STATIC policy keys — `landing_rules` (a unified list covering required checks, labels, and repo-specific triggers, each with explicit gating), `landing_merge_strategy`, `landing_branch_retirement`, `landing_resync` — composed through the exact same layered-provenance machinery (AD-10, AD-16) every existing policy key already uses. `core/landing.py` holds the structured value types and any landing-specific pure logic (rule matching against a changed-paths set); `core/policy.py` gains the validators and closed-vocabulary registration, matching Story 2.3's own `epic_surfaces` precedent exactly.

## Boundaries & Constraints

**Always:**
- **`landing_rules: tuple[LandingRule, ...]`** — one unified rule shape covering AD-40's "labels" and "repo-specific triggers" categories together (a label IS a repo-specific trigger's typical consequence; splitting them into two parallel lists would let them drift). `LandingRule` (new frozen dataclass in `core/landing.py`): `name: str` (non-empty, unique within the tuple), `trigger_path_glob: str` (a glob), `trigger_mode: Literal["exclude", "include"]` (**corrected in review, 2026-08-06** — the original single-mode design was wrong: this repo's own two real rules need OPPOSITE match semantics, not one. `"exclude"` fires when at least one changed path does NOT match the glob — `maintenance-label`'s own shape: "any change outside `recipes/**`". `"include"` fires when at least one changed path DOES match the glob — `environment-yaml-sync`'s own shape: "`pixi.toml` changed". A single unparameterized match direction cannot represent both of this story's own worked examples correctly; `trigger_mode` is required, no default, so every rule states its own direction explicitly rather than inheriting an assumption), `label: str | None`, `required_check: str | None` (at least one of `label`/`required_check` must be set — a rule that does neither is meaningless), `ungated: bool` (default `False`; `True` means this rule applies regardless of any label another rule would add — the literal shape of this repo's own `environment.yaml` sync check, which is explicitly UNGATED, i.e. the `maintenance` label does not suppress it. `ungated=True` requires `required_check` to be set — "ungated" describes a check that can't be suppressed by a label; it is meaningless on a label-only rule, and is rejected as a malformed combination).
- **`landing_merge_strategy: str`** — one of `{"merge", "squash", "rebase"}` (a closed vocabulary, validated). Default `"merge"` — matches this repo's own observed real practice (`git log --merges` shows real, non-squash merge commits throughout).
- **`landing_branch_retirement: bool`** — default `True`. A pure declaration this story defines and validates; Story 4.10 is the one that reads and acts on it. This story does NOT implement retirement logic.
- **`landing_resync: bool`** — default `True`. Same shape: declared and validated here, consumed by Stories 4.5/4.9.
- **This repo's own two real rules are seeded into `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml`** as the worked, live example the AC itself names: `maintenance-label` (`trigger_path_glob = "recipes/**"`, `trigger_mode = "exclude"`, `label = "maintenance"`, `ungated = false`) and `environment-yaml-sync` (`trigger_path_glob = "pixi.toml"`, `trigger_mode = "include"`, `required_check = "environment-yaml-sync"`, `ungated = true`) — matching `CLAUDE.md`'s own prose exactly, now as governed, machine-readable policy instead of a paragraph a human has to remember.
- **Glob matching is case-sensitive and platform-independent** (`fnmatch.fnmatchcase`, never bare `fnmatch.fnmatch`) — repository paths are case-sensitive on the git level regardless of the host OS; using the platform-normalizing form would make the same policy match differently on Linux CI versus a case-insensitive filesystem.
- **Invalid landing policy is a preflight finding naming the layer that introduced each bad key** — reuses the EXACT provenance-reporting shape every other malformed-policy-value finding already uses in this codebase (check `_merge_field`'s own finding-emission pattern before writing a new one).
- **`marshal config` prints the effective landing policy with each key's winning layer, secrets redacted** — this is the SAME `marshal config` command every other policy key already prints through; no new rendering path, just new keys flowing through the existing one. Verify by reading `cli/config.py`'s current rendering loop rather than assuming a new code path is needed.

**Never:**
- No enforcement logic here — this story declares and validates the policy shape; it does not check labels, run checks, retire branches, or resync anything. That is Stories 4.4/4.8/4.10's own surface.
- No second rule-matching implementation — if `core/landing.py` needs a "does this rule fire against a changed-paths set" pure function for its own tests to exercise the shape meaningfully, that same function is what a LATER story (4.4/4.8) must import and reuse, never reimplement.
- Do not touch `cli/land.py` (doesn't exist yet, Story 4.8's own surface) or `cli/deploy.py`'s `land-story` action (Story 4.3, already shipped — this story adds no new CLI action at all, purely policy plumbing).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Valid `landing_rules` with both label and required_check set | A rule declaring both | Composes cleanly, both fields carried | No error |
| A rule with neither `label` nor `required_check` | Meaningless rule | Rejected at composition, finding names the layer and the rule's `name` | Registered finding |
| A rule with a duplicate `name` in the same tuple | Two rules, same `name` | Rejected, finding names the collision | Registered finding |
| `landing_merge_strategy` outside the closed vocabulary | e.g. `"fast-forward"` | Rejected, finding names the layer | Registered finding |
| No landing keys declared at any layer | Defaults apply | `landing_rules: ()`, `landing_merge_strategy: "merge"`, `landing_branch_retirement: True`, `landing_resync: True` | No error |
| This project's own `marshal-policy.toml` (seeded rules) | The two real rules | Composes cleanly; `marshal config` prints both with their winning layer | No error |
| `marshal config` with a secret-shaped value in a rule field | (Hypothetical — rule fields are names/globs, not typically secrets) | Redaction still applies per the existing secret-suffix convention if a field name matches `SECRET_KEY_SUFFIXES` | No error, matches existing behavior |

</intent-contract>

## Code Map

- `src/pyforge/marshal/core/landing.py` — NEW. `LandingRule` frozen dataclass; a pure `rule_applies(rule: LandingRule, changed_paths: tuple[str, ...]) -> bool` (glob-exclusion match, for later stories to reuse — not wired to anything in THIS story beyond its own tests proving the shape is meaningful).
- `src/pyforge/marshal/core/policy.py` — EDIT. Four new STATIC keys (`landing_rules`, `landing_merge_strategy`, `landing_branch_retirement`, `landing_resync`) in `_STATIC_KEYS`/`DEFAULT_POLICY`/`compose()`; validators `_valid_landing_rules`, `_valid_merge_strategy` (mirror `_valid_epic_surfaces`'s shape-checking pattern).
- `src/pyforge/marshal/schemas/policy.json` — EDIT. Four new `policyField`-wrapped properties, added to `required`.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml` — EDIT. Seed this repo's own two real landing rules.
- `tests/unit/test_landing.py` — NEW. `LandingRule`/`rule_applies` matrix.
- `tests/unit/test_policy.py` — EDIT. Validator tests for all four new keys, provenance/composition tests.

## Tasks & Acceptance

**Execution:**
- [x] `core/landing.py` — `LandingRule`, `rule_applies`.
- [x] `core/policy.py` — four new STATIC keys, validators, `compose()` wiring.
- [x] `schemas/policy.json` — four new properties.
- [x] `marshal-policy.toml` — seed this repo's own two real rules.
- [x] Unit tests for every new/edited module, including the full I/O matrix above.
- [x] `deferred-work.md` — log any scope narrowed during implementation. (No scope was narrowed; every Task and AC below was implemented in full, so no new entry was needed.)

**Acceptance Criteria:**
*(Story 4.7's ACs from `epics.md`, preserved as the contract of record.)*
- Given a project whose repository demands checks, labels, a merge strategy, and retirement behaviour, when policy composes, then the landing surface appears as governed keys with per-key provenance — including repo-specific triggers such as this repository's `maintenance` label and its ungated `environment.yaml` sync check
- And an invalid landing policy is a preflight finding naming the layer that introduced each bad key
- And the effective landing policy prints with each key's winning layer, secrets redacted

## Design Notes

**Why `landing_rules` unifies labels and repo-specific triggers into one list, not two.** AD-40 names "labels" and "repo-specific triggers" as separate categories in its enumeration, but this repo's own two real examples (`CLAUDE.md`'s own PR CI gates section) show a label IS the typical action a repo-specific trigger takes — splitting them risks a future rule needing "half" of each shape and having nowhere clean to live. One shape, with `label`/`required_check` each optional but at least one required, covers both AD-40 categories without forcing an artificial split.

**Why `ungated` defaults to `False`.** This repo's own `CLAUDE.md` describes ONE ungated rule (`environment.yaml` sync) out of TWO total — the exception, not the norm. A rule silently defaulting to ungated would mean every future rule bypasses the `maintenance`-label gate unless explicitly told not to, inverting the intended default.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: all green, new tests included, zero regressions.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` — expected: all import-linter contracts hold.

**Manual checks (if no CLI):**
- `marshal config --format json` against this project and confirm `landing_rules` includes both seeded rules with `project` as their winning layer. Verified live 2026-08-06: `BMAD_ACTIVE_PROJECT=pyforge-marshal marshal config --format json` prints `landing_rules.layer == "project"` with both `maintenance-label` (`trigger_path_glob: "recipes/**"`, `trigger_mode: "exclude"`, `label: "maintenance"`, `ungated: false`) and `environment-yaml-sync` (`trigger_path_glob: "pixi.toml"`, `trigger_mode: "include"`, `required_check: "environment-yaml-sync"`, `ungated: true`) present in `landing_rules.value`, matching `CLAUDE.md`'s prose exactly. The other 3 landing keys default cleanly (`landing_merge_strategy: "merge"`, `landing_branch_retirement: true`, `landing_resync: true`, all `layer: "default"`), since this project's `marshal-policy.toml` seeds only `landing_rules`.

## Spec Change Log

**1. `landing_rules`' `EffectivePolicy` representation — a tuple of real `LandingRule` dataclass instances, with explicit serialization support added, not a plain tuple-of-dict mirroring `epic_surfaces`' shape.** The Code Map's own phrasing left this open ("or however this codebase's existing pattern represents structured tuples in `EffectivePolicy` — check `epic_surfaces`'s own representation first"). `epic_surfaces`' actual representation (`Mapping[str, tuple[str, ...]]`) is built entirely from types `core/policy.py`'s existing `_freeze_raw`/`_to_plain` already natively handle (`Mapping`, `list`/`tuple`, `str`). A `LandingRule` is not one of those — storing `landing_rules` as a tuple of real `LandingRule` instances (so later stories, per the spec's own Never clause, can consume `tuple[LandingRule, ...]` directly rather than re-parsing dicts) meant `_to_plain` (in `core/policy.py`, for `content_hash`) and `_json_safe` (in `cli/config.py`, for the wire payload) both needed one new `isinstance(value, LandingRule)` branch each, converting a rule to its plain-dict field mapping. `_freeze_raw` needed no change: a `LandingRule` is already fully immutable (frozen dataclass over `str`/`bool`/`None` fields), so it passes through unchanged like any other already-immutable scalar. Verified live: `test_content_hash_handles_a_nonempty_landing_rules` and the manual `marshal config --format json` check above both exercise this path — `content_hash` computes without raising and the JSON payload renders each rule as `{name, trigger_path_glob, label, required_check, ungated}`.

**2. `cli/config.py`'s `--set`/`_FIELD_ORDER` bookkeeping — extended, not left as "verify, don't assume."** The story's own Always bullet says the four new keys must flow through `marshal config`'s EXISTING rendering path with "zero new rendering code." That held for `_render_text`/`_policy_fields_payload`/`_iter_fields` (all already loop generically over `_FIELD_ORDER`) — but `_FIELD_ORDER`, `_UNSETTABLE_KEYS`, and `_PROJECT_POLICY_ONLY_KEYS` are closed, enumerated frozensets/tuples with no generic fallback, and `test_field_order_matches_the_closed_policy_vocabulary` (pre-existing, `tests/unit/test_cli.py`) asserts `_FIELD_ORDER` equals `policy._ALL_KEYS` exactly. Omitting the four new keys from `_FIELD_ORDER` would have made them silently invisible to `marshal config`'s output despite composing correctly and being hashed — the same "vanishing from output while still being hashed" failure mode that test's own docstring exists to catch. All four were added to `_FIELD_ORDER` (after `epic_surfaces`, matching the spec's own Code Map order); `landing_rules` joined `_UNSETTABLE_KEYS` (list/mapping-typed, no string value could satisfy `_valid_landing_rules`) and the other three joined both `_UNSETTABLE_KEYS` and `_PROJECT_POLICY_ONLY_KEYS` (plain scalars excluded from `--set` because no AC asks for a CLI override surface for any of them — the same reason `idle_threshold_minutes` and the 4 budget ceilings are already excluded). This is additive bookkeeping to the same existing mechanism, not a new rendering path.

## Review Triage Log

### 2026-08-06 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel)

- intent_gap: 0
- bad_spec: 1 (the trigger-direction design flaw, resolved same-session by amending this spec's own `LandingRule` Always bullet — not a full re-plan, since only `rule_applies`/`LandingRule`/the seeded `marshal-policy.toml`/one validator needed re-deriving)
- patch: 5 (medium 3, low 2)
- defer: 0
- reject: 3 (low 3)
- addressed_findings:
  - `[critical]` `[bad_spec]` **`rule_applies` implemented only ONE match direction, and the shipped code's own test proved it backwards for the rule it exists to protect.** The original `LandingRule`/`rule_applies` shape had a single, unparameterized glob-exclusion match — correct for `maintenance-label` ("fires on any change outside `recipes/**`") but the OPPOSITE of what `environment-yaml-sync` needs ("fires when `pixi.toml` itself changes"). The shipped `rule_applies` therefore fired on almost every PR EXCEPT the one case it exists to catch, and `test_environment_yaml_sync_rule_fires_only_on_pixi_toml` asserted exactly that inverted behavior under a docstring name that claimed the opposite. Independently confirmed by both reviewers as their top finding, each citing the same test as the smoking gun. Fixed by amending the Always bullet: `LandingRule` gained a new REQUIRED `trigger_mode: Literal["exclude", "include"]` field (no default), `rule_applies` branches on it, the seeded `marshal-policy.toml` rules were corrected (`maintenance-label` = `"exclude"`, `environment-yaml-sync` = `"include"`), `_valid_landing_rule` gained a closed-vocabulary check for it (same shape as `landing_merge_strategy`'s own), and `test_environment_yaml_sync_rule_fires_only_on_pixi_toml` was rewritten so its assertions finally match its own name. Verified live: `marshal config --format json` now shows `environment-yaml-sync.trigger_mode == "include"` and `rule_applies` fires `True` on a changeset containing `pixi.toml`, `False` on a `recipes/`-only changeset.
  - `[medium]` `[patch]` **`rule_applies` used `fnmatch.fnmatch`, which normalizes case per the host OS, instead of `fnmatch.fnmatchcase`.** Repository paths are case-sensitive at the git level regardless of host OS, so the same policy could match differently on Linux CI versus a case-insensitive filesystem. Fixed: `core/landing.py` now imports and uses `fnmatch.fnmatchcase` exclusively, matching the amended spec's explicit "case-sensitive and platform-independent" bullet. New test: `test_rule_applies_matches_case_sensitively_regardless_of_host_os` (both `trigger_mode`s, an uppercase glob against a lowercase path and vice versa).
  - `[medium]` `[patch]` **`_valid_landing_rule` accepted `ungated=True` on a rule with no `required_check` set — a nonsensical combination.** "Ungated" describes a check that can't be suppressed by a label; it is meaningless on a label-only rule. Fixed: `_valid_landing_rule` now rejects `ungated=True` when `required_check` is `None`, reported through the same `MRS-POLICY-002` path every other malformed-rule case already uses. New tests: `test_landing_rules_rejects_ungated_without_required_check`, `test_landing_rules_accepts_ungated_with_required_check`.
  - `[medium]` `[patch]` **`cli/config.py::_json_safe` and `core/policy.py::_to_plain` hand-rolled the SAME `LandingRule -> dict` conversion independently**, with the diff's own comment admitting one "mirrors" the other — a duplicate serialization with no single owner, so a future `LandingRule` field addition would have had two call sites to remember in lockstep. Fixed: factored into one shared `core/landing.py::landing_rule_to_dict`; both `_json_safe` and `_to_plain` now call it instead of duplicating the field list. No new test needed beyond the existing serialization coverage (`test_content_hash_handles_a_nonempty_landing_rules`, the new P5 CLI test below), since both call sites now provably run the same code.
  - `[low]` `[patch]` **No test exercised `marshal config --format json` with a NON-EMPTY `landing_rules`** — prior test changes only bumped generic key-count assertions against the empty-tuple default, so `_json_safe`'s `LandingRule` branch never actually executed in the test suite. Fixed: new `test_config_format_json_renders_a_nonempty_landing_rule` (`tests/unit/test_cli.py`) composes a real `--project-policy` TOML layer with one rule (including `trigger_mode`) and asserts the JSON payload renders it correctly, including the winning layer.
  - `[low]` `[patch]` **The malformed-`landing_rules` finding dumped the ENTIRE raw layer value rather than naming the specific offending rule**, burying the one bad entry among any number of valid siblings once a project declares more than a couple of rules — a literal reading of the AC's own "an invalid landing policy is a preflight finding naming the layer that introduced each bad key" (and the I/O matrix's more specific "finding names the layer and the rule's `name`" row) wants a direct pointer, not a transcript. Fixed: new `_identify_bad_landing_rule`/`_malformed_landing_rules_finding` helpers (`core/policy.py`) locate the first invalid entry and name it by its own `name` field (or its index, if `name` itself is what's malformed/missing); `compose()` now calls a dedicated `_merge_landing_rules` for this key instead of the generic `_merge_field`. New test: `test_landing_rules_malformed_finding_names_the_specific_bad_rule` (3-rule list, only the bad one's name appears in the message). Incidentally caught a real crash while writing the `trigger_mode` closed-vocabulary test: an unhashable raw value (e.g. `trigger_mode: ["exclude"]`) hit `value not in _TRIGGER_MODES` directly and raised `TypeError` instead of returning `None`, breaking `compose()`'s "never raises on malformed content" contract — fixed alongside with an `isinstance(value, str)` guard first, mirroring `_valid_merge_strategy`'s own pattern.
- rejected (matches existing precedent or already accepted, no action needed):
  - `[low]` "A single malformed `landing_rules` entry wipes the whole list rather than just the bad entry." Matches Story 2.3's own `_valid_epic_surfaces` precedent (whole-key rejection on any bad entry) — this codebase's established fail-safe pattern for structured policy values, not a regression to fix here.
  - `[low]` Docstring readability / external-doc-reference nits. Cosmetic, not correctness.
  - `[low]` The JSON Schema's stated-but-unenforceable "names are unique" note. A known, accepted JSON Schema limitation (no cross-item uniqueness check); Python-side validation already enforces it. No action needed.

</intent-contract>

## Suggested Review Order

**The bad_spec fix — start here**

- `LandingRule`, `rule_applies` (now branching on `trigger_mode`), and `landing_rule_to_dict` — the corrected trigger-direction design.
  [`landing.py:35`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/landing.py#L35)

**Validation**

- `_valid_landing_rule`, including the P3 `ungated`-requires-`required_check` guard and the crash fix for an unhashable `trigger_mode`.
  [`policy.py:504`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py#L504)

- `_merge_landing_rules` — the P6 fix naming the specific offending rule in a malformed-list finding.
  [`policy.py:863`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py#L863)

**Seeded policy (this repo's own two real rules, now with correct trigger_mode)**

- [`marshal-policy.toml:1`](../../../../_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml#L1)

**Tests (peripherals)**

- `LandingRule`/`rule_applies` matrix, including the corrected (previously-inverted) `environment-yaml-sync` test.
  [`test_landing.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_landing.py#L1)

- Validator + composition tests for all four new policy keys.
  [`test_policy.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_policy.py#L1)

- `marshal config --format json` with a non-empty `landing_rules` (P5).
  [`test_cli.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_cli.py#L1)
