---
id: SPEC-token-economy-claude-session-path
spec: token-economy-claude-session-path
status: superseded
updated: "2026-09-16"
superseded_by: _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md#cap-19
owner-dream: docs/dreams/token-economy-claude-session-path.md
covers-dreams:
  - docs/dreams/token-economy-claude-session-path.md
companions: []
surface: []
sources:
  - ../../../../../../docs/dreams/token-economy-claude-session-path.md
  - ../../../../../../docs/dreams/marshal-token-economy.md
open_questions: []
---

> **Superseded 2026-09-16, same day it was seeded.** Operator ruling: no
> satellite Specs — the token-savings chain has one Dream and one Spec. The
> capabilities minted here (three open questions answered in the memlog, then
> re-derived) folded into `spec-marshal-token-economy` as **CAP-19..CAP-24**;
> the dispatch home is marshal Epic 46. This folder is kept, not deleted: its
> `.memlog.md` (eleven entries) is the decision record — the OQ answers, the
> multi-harness matrix, the adversarial review, and the substrate-primary
> reordering — and `owner-dream` keeps the archived Dream's chain link
> resolving. Do not re-derive this Spec; append to the parent's memlog and
> re-derive `spec-marshal-token-economy` instead.

# SPEC — Claude spends the tokens the factory already learned to save

## Why

Epic 28 and Epic 33 built and enabled a context pipeline so an iteration reads
less, says less, and re-learns nothing — and the session that costs money never
used it: always-on repo docs, Cursor-first `harness_preference` on every
station (so `headroom wrap claude` never launches), wire structurally
unavailable on Cursor (28.29). The 2026-09-16 deep analysis widened the
finding: the five layers are two economies (shared substrate primary,
per-harness wire secondary), and token savings is not one currency. The
contract for closing that gap now lives in `spec-marshal-token-economy`
CAP-19..CAP-24; the narrative lives in `docs/dreams/marshal-token-economy.md`
§ Fold (2026-09-16).
