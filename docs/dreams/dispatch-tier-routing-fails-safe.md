---
title: 'A cost-tier dispatch override that cannot resolve its harness must never launch'
type: dream
owner: marshal
status: archived   # 2026-09-16 — folded into [[marshal-token-economy]] (operator-ruled
                   # token-savings consolidation: one starting point). Was `realized`.
---

# A cost-tier dispatch override that cannot resolve its harness must never launch

> **Consolidated into [[marshal-token-economy]] on 2026-09-16** (§ *Fold
> (2026-09-16) — the token-savings Dreams come home*). This file is archived in
> place: its **Spec stays live and remains the contract** — archiving the Dream
> tier never retires the chain below it. Kept, not deleted, so the reasoning
> that produced the Spec is still readable.

## The Dream

Marshal's FR-51 model-tier-batching feature picks a difficulty-tiered model per
dispatch, but the resolver can silently produce a hybrid, broken launch: a real,
working adapter binary paired with another provider's model string it was never
meant to receive. When that happens, the CLI crashes on startup with zero tokens
spent, tmux's `pipe-pane` races the dying window and is tolerated as non-fatal,
and bmad-loop reports the story merely "deferred" — with no signal anywhere that
the actual cause was a policy misconfiguration, not a story-content problem. A
dispatch policy that cannot resolve its own configured harness should never
partially apply; it should fall through to the full, guaranteed-safe baseline,
or fail loudly and specifically.

> The tier map should make dispatch cheaper when the alternative is real —
> never quietly break it when the alternative is not.

## Why now — measured, not feared

Found 2026-09-12 chasing three identical, silent dispatch failures for
pyforge-marshal Story 28.29 (0 tokens spent, empty logs, no surviving tmux
server, "1 deferred" every time). Root-caused by direct execution of marshal's
own resolution code: `model_tier_map.heavy.dev = "composer-2.5-fast"` (a
Cursor-only model, present in **all eight** stations' `marshal-policy.toml`)
resolves to `harness=None` (the bare-string entry carries no explicit harness
key), so `spin.py` falls back to the base `claude` adapter — but still writes
the Cursor model string into `[adapter.dev].model`. The resulting
`claude --model composer-2.5-fast` launch is invalid and crashes instantly.

Compounding this: Cursor is independently, permanently confirmed dead for
headless dispatch fleet-wide (`spec-28-29-wire-is-dead-for-cursor-...`,
shipped 2026-09-10 — "there is no headless integration path, full stop"). So
the tier map has been pointing every heavy/medium/easy-tier dispatch at a
target that can never work, for as long as it has been configured this way
(traced to at least commit `5e7f8cac4b`, well before this session — not a new
regression, a long-standing latent one this dispatch happened to trip).

The resolver already supports an explicit `{harness = "...", model = "..."}`
inline-table form (`tier_routing.py::parse_stage_entry`, `allowed = {"harness",
"model", "pool"}`) — every station's config just used the bare-string
shorthand instead, which is exactly what let the mismatch happen unnoticed.
This is a config-authoring gap plus a missing fail-safe, not a missing
capability.

## What it looks like when real

- A `model_tier_map` entry whose harness cannot be resolved to something
  actually dispatchable in the current loop home never reaches a real launch —
  it falls through to the full baseline (`[adapter]`/`[adapter.review]`),
  never a mix of one candidate's adapter and another's model.
- The default state of `model_tier_map`, fleet-wide, is the same models the
  baseline already uses — a cost-tier override exists only once a second
  harness is verified live in that loop home, not merely configured on paper.
- Enabling a real second harness (Copilot, or whatever is next) always uses
  the explicit `{harness, model}` form, never the bare-string shorthand — and
  rolls out one station at a time, proven across real dispatches, never
  flipped fleet-wide in a single config change (the way Cursor's was).
- A misconfigured or dead-harness tier entry produces a loud, attributable
  finding (an `MRS-SPIN-01x`-class code) the very first time it is hit — never
  a silent "deferred" outcome that reads as a story-content problem.

## Constraints / Non-goals

- **Not a redesign of the token-economy cost-tracking layers**
  (`model_cost_catalog`, pricing, the `context.*` compression layers) — those
  stay untouched; this is scoped to the dev/review model-tier ROUTING resolver
  and its current default values.
- **Not a decision on Copilot.** Whether and when Copilot becomes the second
  harness (its quota history and wrap-composition rework cost are already
  recorded in spec-28-29) stays a separate, explicit operator call — this
  Dream only ensures that whenever that call is made, the resolver cannot
  silently half-apply it the way it did for Cursor.
- **Marshal owns the resolver code and the config format**; the eight
  per-station `marshal-policy.toml` files are data, corrected by the same
  mechanical change once the resolver-side contract is settled.

## Kinships

[[pyforge-marshal]] (owns `core/tier_routing.py`, `cli/spin.py`,
`adapters/harness_bmadloop.py`, and every station's `marshal-policy.toml`) ·
the shipped `spec-28-29-wire-is-dead-for-cursor-specifically-copilot-is-a-real-
but-uncertain-alternative-documented-either-way.md` (2026-09-10 — the
permanent, live-verified cursor-is-dead finding this Dream's fix must respect,
never re-litigate) · [[spec-surface-overlap-tolerance]] (the same-day sibling
precedent: a gap found while chasing an unrelated failure, closed the same day
with a new, narrowly-scoped Dream rather than reopening a shipped one).

## Realization log

- **2026-09-12** — Seeded (operator-authorized: "yes go ahead, dream to code").
  Found investigating three identical silent dispatch failures for
  pyforge-marshal Story 28.29 — itself a phantom-duplicate ledger key from a
  retitle-without-reconcile, fixed separately in commit `0fc84301f2`.
  Root-caused by direct execution of `resolve_tier_launch` /
  `render_policy_toml` against the live pyforge-marshal policy, confirming the
  hybrid claude-adapter / cursor-model launch byte-for-byte. Next act:
  `bmad-spec` derives the Spec under `pyforge-marshal`.
- **2026-09-12** — Realized, same day. `resolve_stage_candidate` no longer
  fabricates an answer when nothing is genuinely available (returns `None`
  instead of "never block"); `render_policy_toml` cross-checks each
  tier-mapped stage's model against the declared `model_cost_catalog`
  (`provider_declaring_model`, new in `core/model_cost.py`) against the
  REAL, final resolved `[adapter].name`, skipping the override on a
  mismatch. Fleet-wide, all eight stations' `model_tier_map.{heavy,medium,
  easy}.{dev,review}` reverted from Cursor's `composer-2.5`/`-fast` to
  `sonnet`/`opus` — the same models the plain baseline already uses.
  Verified by re-running the exact bug-finding probe against the live
  policy (no more `[adapter.dev]` override for any tier) and the full
  `pyforge-marshal-test` suite (7919 passed). One residual, documented gap:
  `marshal factory dispatch`'s own model-resolution path doesn't route
  through the new guard (protected today only because the config no longer
  contains a cross-provider model) — `cli/dispatch.py`'s own live
  binary+authcheck preflight is a separate, already-hardened defense this
  effort did not need to duplicate. Story spec:
  `planning-artifacts/specs/spec-dispatch-tier-routing-fails-safe.md`.
- **2026-09-12** — Residual gap closed, same day, on operator request.
  `cli/dispatch.py`'s own model-resolution path (`resolve_dispatch_model_
  with_retry_escalation`) now carries the identical `provider_declaring_
  model` cross-check, applied right after the live binary+authcheck
  walk's real `resolution.profile` is known — the dispatch engine's own
  "real, final adapter" moment, the counterpart to `render_policy_toml`'s
  `doc["adapter"]["name"]`. A mismatch drops the model override to `None`
  and records a new `MRS-DISP-043` (WARN) rather than launch a
  live-verified harness with a model it was never meant to receive. Both
  dispatch engines now carry the identical guarantee; no known gap
  remains.
- **2026-09-16** — Folded into [[marshal-token-economy]] (operator-ruled token-savings
  consolidation) and archived in place. Prior status: `realized`. The Spec
  (`spec-dispatch-tier-routing-fails-safe`) stays live and remains the contract;
  the narrative continues in the parent's § Fold (2026-09-16).
