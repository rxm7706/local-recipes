# Policy Composition Chain (as of 2026-08-01)

> **Archived 2026-09-14** from `_bmad-output/POLICY_COMPOSITION_README.md`. The live
> layer-2 file is still `_bmad-output/policy-defaults.toml`; composition lives in
> `pyforge.marshal.core.policy`.

**Refreshed 2026-08-15** — Story 1.10's wiring shipped (§ *Story 1.10 Wiring* below is now a
historical plan, not a to-do: `core/policy.compose()` already takes `repo_defaults`, wired
from `adapters/harness_bmadloop.py`, not `cli/config.py` as originally planned — verified
`cli/config.py` has zero references to `policy-defaults.toml`). Also corrected: this doc's
"9 stations"/"9 policy keys" counts are stale — `pyforge-genesis` was dissolved 2026-08-02
(see `EXEMPLAR-STANDARD.md` § INV-2), leaving **8** stations/loop homes, and Marshal's policy
vocabulary has grown to **23** keys (per `core/policy.compose()`'s own docstring), not 9. The
composition *model* (4-layer precedence, file locations, design principles) is unchanged and
still accurate.

## Overview

Marshal's policy composition follows a 4-layer precedence chain (last wins):

```
DEFAULT_POLICY (code in core/policy.py)
    ↓
policy-defaults.toml (repo-wide, tracked)
    ↓
marshal-policy.toml (per-station, tracked)
    ↓
invocation flags (--set, transient)
    ↓
EffectivePolicy (composed, immutable)
```

## Layers

### Layer 1: DEFAULT_POLICY (code)
**Location**: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py`

Marshal's built-in defaults for all 23 policy keys (grown from 9 at authoring time — see
`core/policy.compose()`'s own docstring for the current closed vocabulary). These are
conservative-safe values chosen where the spec doesn't mandate a specific literal. Example: `gate_mode` defaults to `"per-story-spec-approval"` (strictest oversight) rather than `"none"` (unattended).

**When to use**: For out-of-the-box, zero-config behavior. New stations automatically inherit these unless overridden.

### Layer 2: policy-defaults.toml (repo-wide)
**Location**: `_bmad-output/policy-defaults.toml`

Repo-wide policy decisions that apply uniformly to all loop homes unless explicitly overridden. Example: `max_followup_reviews = 2` is a repo-wide decision (not station-scoped) with full reasoning documented.

**When to use**: For decisions that are repo-scale (affect all 8 stations equally) and that benefit from being explicit and documented in tracked TOML.

**Why this layer exists**: The original `max_followup_reviews=2` lived only in code (DEFAULT_POLICY) with reasoning. The incident it prevented (DW-AD23-3, deferred-work-check) made it clear this decision should be explicit and tracked, not buried in code. But putting it in every station's marshal-policy.toml (9 copies at authoring time) would violate the design principle "no project layer needs to restate it". So a new Layer 2 was created.

**Wiring (Story 1.10) — shipped.** `core/policy.compose()` takes `repo_defaults: Mapping[str, object] | None = None` (its own docstring: "The `repo_defaults` parameter was added in Story 1.10"), inserted between code defaults and the project layer. The actual read of `policy-defaults.toml` happens in `adapters/harness_bmadloop.py`, not `cli/config.py` as originally planned below (§ *Story 1.10 Wiring*, kept as a historical plan) — `cli/config.py` never gained that responsibility.

### Layer 3: marshal-policy.toml (per-station)
**Location**: `_bmad-output/projects/pyforge-{slug}/planning-artifacts/marshal-policy.toml`

Per-station policy overrides. Each of the **8** projects (atlas, doctor, herald, marshal, mason, scribe, steward, warden — `genesis` dissolved 2026-08-02, see `EXEMPLAR-STANDARD.md` § INV-2) has one. Typically contains:
- `gate_mode` — almost always `"none"` (unattended) by operator direction (2026-07-26)
- `verify_commands` — station-specific test suite(s)

These files document what differs from the defaults. Keys absent from this file inherit from Layer 2 (repo-defaults) or Layer 1 (code defaults).

### Layer 4: Invocation flags (--set)
**Location**: Command-line invocation

One-off overrides via `marshal config --set <key> <value>`. Example: `marshal config --set gate_mode per-epic` temporarily tightens oversight for a specific run.

## Key Design Principles

1. **Single source per scope**: Repo-wide decisions live once (Layer 2); per-station decisions live once (Layer 3). No duplication across 8 files.

2. **Explicit, not buried**: Values that matter are documented in tracked TOML, not hidden in code defaults or upstream `bmad_loop` baselines.

3. **Backwards compatible**: Layer 2 (repo_defaults) is optional. If omitted, composition falls through to Layer 1 (code defaults). This allows Story 1.10 to wire it in gradually.

4. **Transparent precedence**: Every `PolicyField` records not just the value but the layer that won it (`.layer`), so `marshal config` can answer "why is this value what it is?"

## Current Entries

### policy-defaults.toml

- **`max_followup_reviews = 2`** — Repo-wide. Prevents the default (1) from capping follow-up reviews (happened 5 times across 3 projects before this was set). See the incident history in the file itself.

Future entries might include per-station attempt counts, session timeouts, or other repo-wide decisions.

### marshal-policy.toml (all stations)

Currently only: `gate_mode = "none"` and station-specific `verify_commands`.

No station currently overrides repo-wide settings like `max_followup_reviews` — they all inherit from Layer 2.

## Story 1.10 Wiring (SHIPPED — kept below as the original plan, see the refresh note at top)

Story 1.10 (policy rendering) planned to:

1. Update `cli/config.py` to read `_bmad-output/policy-defaults.toml` at CLI initialization time and pass it to `compose()` as the `repo_defaults` parameter.

2. Update the `compose()` function signature in `core/policy.py` from:
   ```python
   def compose(*, project_slug: str, project: Mapping[str, object], flags: Mapping[str, object])
   ```
   to:
   ```python
   def compose(*, project_slug: str, repo_defaults: Mapping[str, object] | None = None, project: Mapping[str, object], flags: Mapping[str, object])
   ```

3. Update the `_merge_field()` call pattern to insert `repo_defaults` between code defaults and project-layer overrides.

4. Run the existing test suite to verify the composition chain still works end-to-end.

This wiring activates the new Layer 2 without changing any other behavior — new stations inherit repo-wide policy, and existing behavior is unchanged.

## Testing

- `tests/unit/test_harness_policy_render.py` exercises the template rendering + composition fold. Add test cases for repo_defaults composition here.
- `tests/meta/test_ad26_seed_field_access_guard.py` verifies the SEED field access guard. No changes needed.
- `tests/unit/test_policy.py` (if exists) exercises composition. Verify it still passes.

## See Also

- `_bmad-output/policy-defaults.toml` — the canonical repo-wide policy source
- `_bmad-output/projects/pyforge-*/planning-artifacts/marshal-policy.toml` — per-station overrides
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` — the composition logic
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` — rendering into .bmad-loop/policy.toml