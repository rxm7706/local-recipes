# The story-spec flag block

Every capability ships behind a flag, and a check no station owns refuses a story that does not
say so (`docs/governance/spec-feature-flag-governance/SPEC.md`, CAP-1; Dream:
`docs/dreams/feature-flag-governance.md`). This page writes the one shape a story spec uses to
say so. A story author copies it; `bmad-build` and Marshal read the same shape. The Qn numbers
below (Q1, Q3, Q4, Q5) are the operator rulings listed in
`docs/governance/spec-feature-flag-governance/SPEC.md`.

## The rule

- **Who:** a story spec of `type: feature`. `fix`, `chore` and `docs` stories need no flag (Q1):
  a fix restores intended behaviour, and flagging it would keep the bug reachable.
- **When:** a story spec minted on or after the rule date, **2026-09-28**. Specs that existed at
  that date are pre-rule: they warn and join the retrofit; they are never refused.
- **What:** the spec's frontmatter carries exactly one of two things, a `flag:` block or a
  `flag-exempt:` value. Carrying both is a defect, and so is carrying neither.

### Pre-rule and post-rule

The line is drawn by `docs/governance/flag-rule-baseline.json`, never by the spec's own
`created:` string. The baseline lists every story spec in the git tree at the merge of PR #1654
(the commit where the Spec reached `ready`; the SHA is in the file). A spec is post-rule exactly
when it is absent from that list. Several `type: feature` specs minted on 2026-09-28 before the
Spec was `ready` are therefore pre-rule, and a spec cannot move itself across the line by
editing its date. The baseline is stamped by `scripts/flag_rule_baseline.py` and only ever
shrinks.

Only a spec named `spec-<epic>-<story>-*.md` is a story spec under the rule; that naming is what
puts a spec in the baseline population, and a legacy-named spec (for example
`spec-land-promote-isolation.md`) is outside it.

## Registering a flag

When a story ships a new flag, register it in all four places before verification passes:

1. **`src/platform/config/flags.json`** — add the flag key, variants, default variant, and metadata.
2. **`src/platform/config/flag-overlays.json`** — set per-environment variant values; they must follow the
   story spec's `flag.default` mapping (`production`, `staging`, `dev`).
3. **`src/shared/packages/pyforge-core/tests/unit/test_flags.py`** — extend `_SHIPPED_CLOCKS`, `expected`, or
   `per_environment` so core's flag contract covers the new key.
4. **`src/platform/tests/test_openfeature_file_flags.py`** — extend `_SHIPPED_BOOLEANS` so the platform file
   provider contract covers the new key.

Marshal's fix-turn prompt points here when verification or the story spec signals flag work; the first dev
session should use the same checklist.

## The `flag:` block

Six fields, all present and non-empty:

| Field | Holds |
|---|---|
| `key` | The flag's key in the one OpenFeature tree, `pyforge.<station>.<capability>`. |
| `provider` | `openfeature-file`, the one provider (canopy:AD-11: one tree, no egress). |
| `default` | The default per environment, as a mapping (`production`, `staging`, `dev`). A retrofit flag defaults ON, so it works as a kill switch. |
| `scope` | `global`. Targeting rules (user, tenant) are a later CAP (Q5). |
| `fallback` | One line: the legacy behaviour that holds while the flag is OFF. |
| `cleanup` | When the flag is removed: 90 days after it is ON in every environment (Q4). The owning station files the removal story. |

A flagged story:

```yaml
---
title: 'A story that adds behaviour'
type: 'feature'
flag:
  key: pyforge.atlas.dependency_history
  provider: openfeature-file
  default: {production: off, staging: on, dev: on}
  scope: global
  fallback: "the legacy behaviour"
  cleanup: 90 days after ON in every environment (Q4)
---
```

The checker reads that a field is there, not what it holds: the value checks (a key that is not
in the tree, a flag past its cleanup date) belong to the gate, not to the story author. An
unquoted `off` is a value; YAML reads it as false, and the checker does not treat it as empty.

## The `flag-exempt:` value

A story with no behaviour to flag names why, with one value from the closed list in
`docs/governance/guild-roster.json` (key `flag_exemptions`; its `$comment_flag_exemptions` says
what each value means). The list is the roster's alone: this page does not copy it, so it cannot
drift, and adding, renaming or removing a value is a governance act. To read it:

```bash
python -c "import json; print(*json.load(open('docs/governance/guild-roster.json'))['flag_exemptions'], sep='\n')"
```

An exempt story:

```yaml
---
title: 'A story that changes the rule and not the product'
type: 'feature'
flag-exempt: detector-or-gate
---
```

A value that is not on the list is a defect that names the value.

## A CLI verb whose flag is OFF

A verb behind an OFF flag stays **listed** in `--help`, marked disabled (Q3). Invoked, it
refuses with its station's own usage exit code and a "flag off" message. It mints no new exit
code: every station's frozen exit-code domain holds in both flag states. The story's
`## Verification` names a test that runs both states and, for such a verb, asserts the listing
and the refusal.

## How a machine reads it

`scripts/flag_rule.py` is the pure reader: `classify(path)` returns `flag`, `exempt` or
`neither` with one reason per missing field or unknown value; `is_post_rule(path)` reads the
baseline; `in_scope(spec)` is `type: feature`. It lives outside every station package and reads
the exemption list from the roster at run time. It judges nothing itself: `scripts/flag_gate_check.py`
turns a verdict into a finding. It is a repo-scope detector, so `detectors-ci` runs it, and
`pixi run -e pyforge-guild flag-gate-check` runs it alone (exit 0 clean, 1 findings, 2 when the
roster, baseline or tree cannot be read). `python scripts/flag_gate_check.py --spec <path>` judges
one story spec and prints one JSON object: `verdict` (`pass`, `warn` or `red`), `findings` and
`rule_date`, exiting 0, 0 or 1 (2 when it cannot judge).

`bmad-build` does not carry its own copy of the shape: marshal Story 74.3 adds a persistent fact
under `_bmad/custom/` that points here.
