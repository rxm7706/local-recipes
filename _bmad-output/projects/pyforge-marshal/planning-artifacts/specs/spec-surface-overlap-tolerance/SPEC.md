---
spec: spec-surface-overlap-tolerance
status: ready   # 2026-09-14 — open question answered against chain.py; decomposed into marshal Epic 42.
created: "2026-09-12"
updated: "2026-09-12"
owner-dream: docs/dreams/spec-surface-overlap-tolerance.md
surface:
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py
companions: []
sources:
  - ../../../../../../docs/dreams/spec-surface-overlap-tolerance.md
open_questions: []   # the one question below was answered 2026-09-14 — see § Open Questions.
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for
> what to build, test, and validate. `owner-dream` carries the narrative rationale this
> contract intentionally omits.

# SPEC — spec-surface-check tolerates governed overlap between specs

## Why

**A pain to solve.** `spec-regenerable-factory` CAP-3 (shipped) checks every governing
spec of a changed file independently: each spec must show its own memlog moved and
names the file, or it gets flagged — with no awareness that another spec governing the
*same* file may already have reconciled it cleanly. This is not an edge case:
`pyforge.doctor.sources.chain._governed_and_ungoverned` explicitly assigns a changed
file to *every* matching spec's governed list, and multi-owner files are routine (a
station's broad kernel spec and a narrower, actively-worked spec both matching the same
path). When the kernel spec's memlog stops moving for routine story work — the normal
shape once a station decomposes into many narrower specs — it accumulates permanent,
un-clearable noise for files the narrower spec already handles correctly. Found and
fixed at data-scale 2026-09-12 (178 findings across 17 specs, PR #1288, a per-file
`surface-drift-exclude:` workaround); this Spec is the root-cause fix so the same class
of noise stops recurring as new narrow specs get minted under existing kernel specs.

## Capabilities

- **CAP-1**
  - **intent:** A file governed by multiple specs is `drift-presumed`/`drift` only when
    NONE of its co-governing specs' memlogs account for the change — not whenever any
    single co-governing spec's memlog doesn't.
  - **success:** A synthetic fixture with two specs governing the same file, where one
    spec's memlog explicitly names the changed file (today's existing clean-pass bar),
    produces zero finding against EITHER spec for that file.
- **CAP-2**
  - **intent:** A genuinely unreconciled change is still caught exactly as today — this
    Spec narrows a false positive, it does not widen what counts as accounted-for.
  - **success:** The existing `spec-surface-check` test suite's single-owner drift/
    drift-presumed fixtures all pass unchanged; a new multi-owner fixture where NEITHER
    co-governing spec's memlog names the file still produces a finding (against at least
    one of them, matching today's behavior for that spec).

## Constraints

- Never weakens the coverage half (`ungoverned` check) — every tracked file still needs
  ≥1 governing spec or an allowlist entry. Only the DRIFT half's per-spec independence
  changes.
- `pyforge-doctor` owns the code (`pyforge.doctor.sources.chain`); `pyforge-marshal`
  owns the contract (`spec-regenerable-factory` CAP-3, shipped, this Spec's extension
  point). Cross-station surface claim — doctor records the incoming claim in its own
  memlog before code lands, per established convention.

## Non-goals

- Retroactively removing the 17 `surface-drift-exclude:` entries `PR #1288` already
  landed. They stay as a correctness fallback and a record of what was found; this Spec
  does not require touching them once the detector itself improves.
- Redesigning `spec-surface-check`'s coverage half or its allowlist mechanism.

## Success signal

The next time a new, narrow story spec is minted under an existing station kernel spec
and correctly reconciles a file it shares with that kernel spec, `spec-surface-check`
produces zero finding against the kernel spec for that file — automatically, with no
manual `surface-drift-exclude:` entry ever required.

## Open Questions

**ANSWERED 2026-09-14** by reading `pyforge.doctor.sources.chain._drift_findings`
(`chain.py:1662-1742`), as this question itself required. None remain.

**The Dream's assumption holds: the existing per-spec clean-pass bar is the right
predicate to OR across co-governors, and no new bar is needed.** The bar is already the
two-part conjunction at `chain.py:1719-1740` — `spec_moved` (the spec's baseline memlog
hash differs from current) AND `f in named` (the memlog's text names that path). That
conjunction is exactly the "this spec reconciled *this* path" predicate, as distinct
from "this spec's memlog moved for something else", so ORing it across co-governors is
well-defined.

**What must change is the loop shape, not the bar.** `_drift_findings` iterates
`for name, cur in current.items()` and emits per spec, with no cross-spec awareness —
that independence *is* the defect. The implementation inverts to group by path first,
then asks whether ANY co-governing spec passes the bar for it.

**One subtlety the question did not anticipate, recorded so implementation does not lose
it:** the per-spec outcome is not binary. A co-governor that never moved yields `drift`
(FAIL); one that moved but does not name the path yields `drift-presumed` (WARN). So the
OR clears the group only on a fully clean co-governor, and where none is clean the
residual finding must keep the *strongest* severity among co-governors — otherwise a
genuinely unreconciled file could be downgraded FAIL→WARN merely by gaining a second
governing spec, which would violate CAP-2's "does not widen what counts as
accounted-for".
