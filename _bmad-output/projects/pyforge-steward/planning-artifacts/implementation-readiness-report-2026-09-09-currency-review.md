# Steward — currency review readiness (2026-09-09)

Gate of `spec-pyforge-unifying-strategy` Epics 48–49 after the 2026-09-09 correct-course
(`sprint-change-proposal-2026-09-09-currency-review.md`, operator-approved: "Approve; Unifying now,
re-home later; merge now before any 44.x flip") bound the currency review's residue as Epic 48 and
the realization gate as Epic 49 — sixteen stories, ledger keys minted by `sprint_plan.py generate`.

**Question:** could a developer implement each story without inventing decisions?

**Verdict: READY — proceed. Dispatch 48.1 first and alone.**

## Concerns (do not invent; do not block the rest)

| Concern | Where | Why it does not block |
|---|---|---|
| ~~49.8 minted `backlog` while its own `Deps:` line says ledger `blocked` until marshal Epic 33's Track story exists~~ | `epics.md` 49.8; ledger | **Fixed at this gate** via `sprint_plan.py generate --set …=blocked` (the sanctioned path; no sync). 15 `blocked` rows now: 14 Epic 44 + 49.8. |
| `AGENTS.md:49` still mandates `sprint-ledger-sync --repair-feed` before any ledger write — the instruction the Dream and Spec now forbid | `AGENTS.md` managed block | Assigned to 48.1 via `bmad-project-context` refresh; the Dream's Order line and the Spec's Constraints already carry the correct rule. Until 48.1 lands, **no sync of any form on this project** |
| The Tier-3 feed lags the tracked twin by all 20 new keys | `implementation-artifacts/sprint-status.yaml` | By design: a bare sync today silently drops twin-only keys and un-blocks Epic 44 (main() acts on `missing` only under `--repair-feed`; only 47.5's `done`/`blocked` divergence makes `lost` non-empty). 48.1 restores the feed as its last task |
| `open_questions` now carries two entries on a `ready` Spec | `SPEC.md` frontmatter | Both are answered in-text by the operator on 2026-09-09; `realization-gate-home` is a re-homing trigger (Epic 49 moves to `hub:` by memlog when `spec-intelligence-hub` reaches `ready`), not an unmade decision. `chain-currency` coherence is green |
| 48.6, 49.4, 49.7 are decision stories ("implement, or rewrite the criterion / delete the pillar") | their story text | Each records that the decision is the deliverable, with a dated ruling either way; no developer invents it — the operator makes it inside the story |
| 49.2 adds a doctor source and a `detectors` membership | `pyforge-doctor` sources, `pixi.toml` | Doctor's advisory doctrine (never a second PR verdict; exit-code domain unchanged) is recorded in `AGENTS.md` and the doctor SKILL; `report-schema.json` changes are additive |
| 48.2 (HPA/PDB) and 49.5 (eviction test) both touch chart autoscaling | `values.yaml`, `hpa.yaml` | 49.5's text says "HPA if 48.2 has not landed it"; dispatch 48.2 before 49.5 or accept the conditional |
| Epic 49's binding home may move to `spec-intelligence-hub` | SPEC `open_questions` | Story text does not change on re-home; only the memlog and the epic's Spec-binding line do |

## Trace

| Intent | Story |
|---|---|
| Syncer guards `blocked` + missing keys (review § 0; Spec Constraints 2026-09-09) | 48.1 |
| R-18 sizing (`DW-RT-2026-09-02-2`) | 48.2 |
| R-19 network baseline (`-3`) | 48.3 |
| R-20 secrets profile (`-4`) | 48.4 |
| R-21 observability contract (`-5`) | 48.5 |
| R-22 live streaming or delete the pillar (`-6`) | 48.6 |
| CAP-axis namespace pass (review § 1.3; Spec Constraints 2026-09-09) | 48.7 |
| Single-Spec merge (Dream Grounding "parked"; operator: now) | 48.8 |
| `verified:` line per CAP (Spec Constraints 2026-09-09) | 49.1 |
| Doctor effect check (advisory) | 49.2 |
| CAP-4 criterion `SPEC.md` "multi-minute op across a simulated ingress disconnect" | 49.3 |
| CAP-7 criterion "two users … provably different row sets" against the real board | 49.4 |
| CAP-11 criterion "filling the cache to its eviction limit loses no queued task" | 49.5 |
| CAP-12 criterion "removes portal access on the user's next request" | 49.6 |
| CAP-14 criterion "semantic recall returns what lexical overlap does not" + dual-write | 49.7 |
| CAP-17 criterion "front door shows live run state … timing survives the workstation" | 49.8 |

## Dispatch order

1. **48.1 alone.** Nothing else on this project may sync until it lands; its last task restores the
   feed and corrects `AGENTS.md:49`.
2. 49.1 → 49.2 (they define the gate) ∥ 48.7 ∥ 48.2, 48.3, 48.4, 48.5, 48.6 in parallel.
3. 48.8 before any Epic 44 story is flipped off `blocked` (the regeneration drill must not consume
   an unmerged `extends:` chain).
4. 49.3, 49.4, 49.5, 49.6, 49.7 in parallel after 49.2; 48.2 before 49.5 where possible.
5. 49.8 stays ledger `blocked` until marshal Epic 33's Track story exists (Marshal `Deps:` edges are
   station-local, so the cross-project gate is the ledger state); then flip to `backlog` and land it
   jointly with that story — one publisher, not two.

**Marshal readiness (2026-09-09):** `[epic_surfaces]` "48" and "49" declared in
`marshal-policy.toml` (the "47" list plus each epic's own globs); every `Deps:` field parses
(`forward-dependency` green in the 28/28 suite); `marshal factory drain --station pyforge-steward`
reads the tracked ledger in the order above. Steward's `verify_commands` runs the steward package
suite; 48.1 additionally runs marshal's `test_promote_sprint_status_regressions.py`.

`BMAD_ACTIVE_PROJECT=pyforge-steward` (the switch is on steward as of this session). Physical
paths only. Detectors: 28/28 green at this gate.
