# Marshal — token-economy enablement readiness (2026-09-09)

> **Authored by hand at the physical path under the parallel-agents HARD rule; skill not invoked.**
> `bmad-sprint-planning` was not run — this is one of seven concurrent station applies and the
> readiness gate resolves through the per-tree `_bmad-output/planning-artifacts` symlink. Ledger keys
> were minted with `sprint_plan.py generate` (dry-run first, diffed, then `--set` for the one
> `blocked` row); **no `sprint-ledger-sync` of any form was run.**

Gate of `spec-marshal-token-economy` **Epic 33** after the 2026-09-09 correct-course
(`sprint-change-proposal-2026-09-09-token-economy-enablement.md`, operator-approved as fleet-readiness
decision batch § 0 rows **C5** and **C6**) bound the Dream's 2026-09-09 addendum — Epic 28 is 24/24
`done` and every layer is off — plus five sibling built-but-inert capabilities, as ten stories.

**Question:** could a developer implement each story without inventing decisions?

**Verdict: READY — proceed. Dispatch 33.1 first and alone.**

## Concerns (do not invent; do not block the rest)

| Concern | Where | Why it does not block |
|---|---|---|
| 33.4 is minted `blocked` while steward 49.8 is *also* `blocked` on it — a mutual gate that nothing resolves on its own | ledger `33-4-…: blocked`; steward `sprint-status-ledger.yaml:368` | **Deliberate and symmetrical.** Marshal `Deps:` edges are station-local, so a cross-project gate can only be expressed as ledger state. The pair dispatches together by an explicit operator act, and lands as **one publisher**. Either row flipping alone would produce the two writers CAP-18 exists to prevent |
| 33.3 may prove impossible — spin has no argv to prefix (`DW-FU-28-2`) | 33.3 story text | The story is written as **decision+feature**: "the wire layer acts on spin, **or** spin is declared a two-layer engine on the record". The decision is the deliverable; no developer invents it. Either branch still folds `read_repo_policy_defaults()` on both engines, which is the part that must not be skipped |
| 33.1 blocks nine stories, so a stall there stalls the epic | Deps graph | Correct and intended — it is the Dream's own measurement-first gate, which Epic 28 bypassed and this epic restores. 33.7, 33.9 and 33.10 carry `Deps: —` and can drain in parallel with 33.1 if the operator wants throughput; 33.2–33.6 and 33.8 genuinely cannot be judged without a baseline |
| `[epic_surfaces] "33"` is declared but the spec-surface baseline is **not** re-stamped | `marshal-policy.toml`; `scripts/.spec-surface-baseline.json` | By instruction. `marshal-policy.toml` is governed by `spec-marshal-parallel-dispatch-fanout`'s `surface:`; the reconciling memlog line is written, the scoped `--write-baseline --spec pyforge-marshal/spec-marshal-parallel-dispatch-fanout` is left to the lead after the `bmad-spec` re-derives (batch apply-order step 8). **Expect exactly one `drift` finding on this path until then** |
| Twelve marshal Specs changed status in this same pass, by memlog only | the `.memlog.md` files listed in § Trace | `SPEC.md` is never hand-edited under this rule. Every status flip, capability and closure is a memlog entry, which is the documented input to the lead's `bmad-spec` re-derive. Until that re-derive runs, the frontmatter still reads the old value — that is a known, bounded lag, not a contradiction |
| `spec-marshal-token-economy` has `open_questions: []` and gains CAP-18 without gaining a question | that Spec's frontmatter | Correct: CAP-18 is a *decided* capability (batch C5), not an open question. The Dream's two gates are already closed in its own § Addendum — one answered in the negative (cross-engine comparison is meaningless), one restored as Story 33.1 |
| The Tier-3 feed now lags the tracked twin by twelve keys | `implementation-artifacts/sprint-status.yaml` | By design and fleet-wide today: a bare sync silently drops twin-only keys and un-blocks `blocked` rows (`promote_sprint_status.py:91` guards only `done`). **No sync on any project until steward Story 48.1 lands its `STICKY_STATUSES` guard.** Marshal owns the regression test 48.1 rewrites; steward owns the fix — one writer |
| Story 31.4's scope grew (seven files → eleven) without a new story | `epics.md` Story 31.4 | 31.4 is `backlog`, so its AC text is amended rather than re-minted (batch § 2.4 **D9**). No `done` key is touched and no ledger key changes |
| Epic 33's stories touch six Specs, only one of which is its nominal chain | 33.5–33.9 `FR/AD:` lines | Each names its own Spec and CAP explicitly, and each of those Specs took a memlog decision in this same pass recording that the enablement lands here. The epic's HARD boundary forbids re-minting any of them |

## Trace

| Intent | Story | Spec / batch row |
|---|---|---|
| The baseline the Dream's § Gates demanded and Epic 28 never produced; five stub savings getters made real | 33.1 | token-economy CAP-7/CAP-9; `DW-FU-3-6-6` |
| A `[context]` block that actually acts, on the live engine | 33.2 | token-economy CAP-1/2/5/6 |
| Spin folds repo defaults and gets the wire layer — or is declared two-layer on the record | 33.3 | token-economy CAP-1; `DW-FU-28-2`, `DW-FU-28-2-3` |
| One publisher: run state + savings telemetry reach `django_pyforge.supervisor` | 33.4 | token-economy **CAP-18** (new) + CAP-7; **Unifying CAP-17** (qualified); **`hub:CAP-3`**; batch **C5** |
| `classify_review_tier` gets a producer and a caller | 33.5 | `spec-risk-tiered-review-depth`; `DW-FU-2-8-2`, `DW-FU-2-8-4`; batch **C5** |
| Six more stations get a tier map; the retry floor-raise reaches `factory dispatch` | 33.6 | `spec-adaptive-model-tiering` CAP-2 (FR-51, Story 3.12); batch **C6** |
| Two watchdogs stop greening over an empty plane | 33.7 | baseline-drift CAP-1..3 + intent-gap CAP-1..2; batch **C6** |
| The first live fan-out wave, on a real `dispatch.max_parallel` key | 33.8 | `spec-marshal-parallel-dispatch-fanout` **CAP-6** (new) + CAP-1..5; `DW-FU-28-2-2`; batch **C6**/**C10** |
| `verify_scope` guards the one boundary every parallel BMAD write passes through | 33.9 | `spec-bmad-switch-scope-enforcement` CAP-1/2; batch **C10** |
| The CFE pin is derived from `SKILL.md:10`, never stamped | 33.10 | batch § 2.4 **D6**; SYNC-RUNBOOK row 84 |

**Spec memlogs written this pass** (the lead's `bmad-spec` re-derive reads these):
`spec-marshal-token-economy` (CAP-18 + the epic decision + the CAP-axis qualification),
`spec-marshal-parallel-dispatch-fanout` (CAP-6 + oq1/oq2 + `ready → shipped` + residual + the
`[epic_surfaces]` surface touch), `spec-risk-tiered-review-depth` (`shipped → in-progress` + one new
open question), `spec-marshal-single-story-dispatch` (all five OQs + the fork Constraint +
`in-progress → shipped`), `spec-marshal-verify-fail-terminalization`,
`spec-marshal-drain-self-resolution`, `spec-landing-evidence-grammar`,
`spec-fleet-consistency-standard`, `spec-agent-tool-surface`, `spec-bmad-loop-liveness-footgun`,
`spec-bmad-switch-scope-enforcement`, `spec-bmad-cursor-interactive-routing`,
`spec-agentic-sdlc-autonomy`, `spec-bmad-loop-baseline-drift`,
`spec-bmad-loop-intent-gap-work-preservation`, `spec-artifact-chain-reconciliation`,
`spec-dashboard-velocity-captures-hand-driven-work`, `spec-surface-drift-reconciliation`,
`spec-quick-dev-reconciliation`, `spec-bmad-611-era-alignment`, `spec-factory-console`,
`spec-pyforge-marshal`, `spec-marshal-land-cross-project-story-key-collision`,
`spec-marshal-status-harness-run-id-poisoning`.

## Dispatch order

1. **33.1 alone.** No layer is enabled on any engine before its artifact exists. If a getter's source
   is genuinely absent, it returns a **named unavailable reason** — that still satisfies 33.1; a
   `None` does not.
2. 33.2 → 33.3 (33.3 needs a working dispatch leg to compare against).
3. 33.7, 33.9, 33.10 may run any time — they carry `Deps: —` and touch no layer.
4. 33.5, 33.6 in parallel after 33.1.
5. **33.8 after 33.2** — a first live wave should not also be the first thing a newly-enabled wire
   layer meets, and 33.8 closes `DW-FU-28-2-2` (two concurrent wrapped dispatches sharing one CCR
   store), which only exists once the wire layer is on.
6. **33.4 last, jointly with steward 49.8.** Both rows are `blocked`; the operator flips both and
   dispatches them as one landing. Doctor records its incoming surface claim in
   `spec-pyforge-doctor`'s memlog **before** 33.4's code lands, or `spec-surface-check` reds the merge.

**Marshal readiness (2026-09-09):** `[epic_surfaces]` `"33"` declared in `marshal-policy.toml`
(the `"31"` list plus this epic's own globs, 22 in total); the file parses as TOML; every `Deps:`
field on the ten stories parses; ledger diff is **+12 keys, 0 changed, 0 dropped, 0 illegal**;
`sprint_plan.py generate` reports `epics: 33, stories: 227`, matching the 227 `### Story` headings in
`epics.md` exactly.

`BMAD_ACTIVE_PROJECT=pyforge-marshal` per invocation. Physical paths only. `scripts/bmad-switch` was
not run by this apply and must not be run by any parallel agent.

## Dispatch sequence — operator ruling 2026-09-09

Weighted on speed-to-market, token cost, wall clock, strategic alignment and unblocking other
stations: **33.1 → 33.5 → 33.4 → 33.2/33.3 → 33.6 / 33.7 / 33.9 / 33.10 → 33.8 last**;
33.11 (attribution) is `blocked` on its trigger and never enters this queue on its own. 33.1
stays first and alone (the Spec's measurement-first gate). 33.5 (review tiering) is the cheapest
throughput win — review is where reviewer-lens token cost concentrates and the mechanism has zero
callers. 33.4 precedes the layer enablement because it is the only story that unblocks another
station (steward 49.8). 33.8 is last because within-station fan-out is gated on story specs
declaring their own `surface:` (fanout CAP-16 auto-derivation), an uncosted template change.
No measured baseline exists yet, so this order is the hypothesis 33.1 is built to confirm or
overturn.
