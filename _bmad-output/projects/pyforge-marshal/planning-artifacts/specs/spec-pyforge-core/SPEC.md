---
id: SPEC-pyforge-core
spec: pyforge-core
status: ready
owner-dream: docs/dreams/pyforge-core.md
surface:
  - src/shared/packages/pyforge-core/**            # net-new, not yet created
  # DW-FU-20-2 fix (2026-09-07): the prior single-line brace-expansion glob
  # (pyforge-{atlas,doctor,...}/src/**) never matched any real path --
  # chain.py::_glob_to_re has no {a,b,c} expansion support, so the literal
  # brace text could never appear in a scanned path. One real glob per
  # station below, matching each package's actual src/ tree.
  - src/shared/packages/pyforge-atlas/src/**        # the copies each extraction retires
  - src/shared/packages/pyforge-doctor/src/**       # the copies each extraction retires
  - src/shared/packages/pyforge-herald/src/**       # the copies each extraction retires
  - src/shared/packages/pyforge-marshal/src/**      # the copies each extraction retires
  - src/shared/packages/pyforge-mason/src/**        # the copies each extraction retires
  - src/shared/packages/pyforge-scribe/src/**       # the copies each extraction retires
  - src/shared/packages/pyforge-steward/src/**      # the copies each extraction retires
  - src/shared/packages/pyforge-warden/src/**       # the copies each extraction retires
  - pixi.toml                                       # the new workspace member + its per-station dep edges
surface-drift-exclude:
  # 2026-09-12: also governed by the spec(s) named below, which already
  # reconciles each of these files cleanly -- this kernel spec's own
  # memlog does not move for routine story work anymore, so double-
  # claiming them only produced permanent drift-presumed noise here.
  # Coverage is unchanged (still listed under `surface:` above); only
  # this spec's own drift tracking for these specific files is off.
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/publisher_host.py   # also governed by pyforge-marshal/spec-run-state-one-publisher
  - src/shared/packages/pyforge-core/src/pyforge/core/client.py   # also governed by pyforge-steward/spec-pyforge-unifying-strategy
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py   # also governed by pyforge-marshal/spec-dispatch-tier-routing-fails-safe
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py   # also governed by pyforge-marshal/spec-dispatch-tier-routing-fails-safe
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py   # also governed by pyforge-marshal/spec-dispatch-tier-routing-fails-safe
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/model_cost.py   # also governed by pyforge-marshal/spec-dispatch-tier-routing-fails-safe
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/tier_routing.py   # also governed by pyforge-marshal/spec-dispatch-tier-routing-fails-safe
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py   # also governed by pyforge-marshal/spec-dispatch-tier-routing-fails-safe
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py   # also governed by pyforge-steward/spec-pyforge-steward (Story 59.2)
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py   # also governed by pyforge-steward/spec-pyforge-steward (Story 59.2)
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/status_body_consistency.py   # also governed by pyforge-steward/spec-pyforge-steward (Story 59.2)
sources:
  - ../../../../../../docs/dreams/pyforge-core.md
  - ../../research/technical-pyforge-unification-2026-08-08.md   # § 7 duplication census — figures superseded, see Assumptions
open_questions:
  - "Q1 — does the station roster belong in pyforge-core at all? It is the one census entry whose canonical home already exists (bmad_drift_check.STATIONS, imported rather than mirrored by generate.py). Moving it into a package that ships to conda would give a stdlib-only detector a package dependency it does not have today. Decide before CAP-4, not during."
  - "Q2 — is pyforge-testing-kit (the testing charter's unbuilt CAP-3) a second leaf package or a module of this one? Both are stdlib-only shared floors with the same leaf constraint; shipping two may be splitting one thing, shipping one may couple test-only fixtures into a runtime dependency."
  - "Q3 — the subprocess guard (CAP-6) is a design reconciliation, not an extraction: doctor's cli_bridge.run_cli_json and marshal's ProcessPort/process_posix are two genuinely different designs, and steward deliberately propagates raw CalledProcessError. Which design wins, and does steward's deliberate divergence become a sanctioned opt-out or get folded in?"
fold-exemption: cross-station-seam
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for
> what to build, test and validate. `docs/dreams/pyforge-core.md` carries the narrative
> and the measured census; the research document in `sources:` is traceability only and
> its § 7 figures are **superseded** by the Dream's own measurement (see § Assumptions).

# SPEC — pyforge-core

## Why

Eight stations share one namespace and no floor. Five primitives are written between
three and twenty times each, and the copies are self-aware: their docstrings say
*"mirrors `state.write`"* and *"identical shape,"* and doctor's `verdict.py` describes
itself as *"a subset of `pyforge.warden`'s frozen `{0, 1, 2, 130}`"* — a dependency
asserted in prose because there is no package in which to express it.

This is not neglect. It is a doctrine that was right about what it protected and silent
about what it didn't: stations are independently conda-installable and deliberately do
not import each other, so every station needing an atomic write wrote one. The doctrine
still holds; what it never said is that a **leaf** — pure stdlib, imported by every
station, importing none — is not the coupling it forbids.

The timing is not incidental. Marshal's Epic 7 stories **7.2** (error taxonomy and exit
codes) and **7.3** (the fs-write primitive and the never-write guard) are in backlog
right now and would mint copy #21 of atomic write and copy #6 of the verdict lattice —
inside the very planning rewrite convened to consolidate. Deciding this after S-7.1 opens
costs two stories of rework; deciding it now costs an epic ordering.

## Capabilities

- **CAP-1 — the leaf exists and is provably a leaf.**
  - **intent:** One package under `src/shared/packages/` that any station may depend on
    and that depends on no station.
  - **success:** `pyforge-core` builds, installs from a clean environment, and imports
    with stdlib only; a meta-test fails the build if any module under it imports from
    `pyforge.<station>` for any of the eight; every station remains independently
    conda-installable with `pyforge-core` as its only new run-dependency.
- **CAP-2 — atomic write has one implementation and twenty fewer copies.**
  - **intent:** The tmp-in-dir + `os.replace` primitive is written once.
  - **success:** One implementation in `pyforge-core`; **all 20 measured copies across the
    6 stations that have them** (herald 6, atlas 5, marshal 5, steward 2, scribe 1,
    warden 1) are removed in the same story that extracts the primitive, not deprecated in
    place; a grep for a second tmp-in-dir + `os.replace` pair outside `pyforge-core`
    returns nothing; the durability semantics each copy relied on are preserved, verified
    per call site rather than assumed uniform.
- **CAP-3 — the verdict lattice is declared once, and narrowing is expressed, not asserted.**
  - **intent:** Exit-code domains stop being redeclared per station, and a station whose
    domain is a subset of another's says so in types.
  - **success:** One lattice in `pyforge-core` with per-station domain restriction; doctor's
    `{0, 2, 130}` is a real, enforced narrowing of warden's `{0, 1, 2, 130}` rather than a
    docstring claim; the five existing declarations (atlas, doctor, herald, marshal, warden)
    are retired; each station's frozen exit contract is unchanged observably — a test asserts
    the same inputs still yield the same process exit codes.
- **CAP-4 — one report envelope, extended rather than rivalled.**
  - **intent:** The `{tool, status, exit_code, findings[]}` shape has one schema.
  - **success:** One envelope schema in `pyforge-core`; warden's 22 KB schema is expressed
    as an extension of it and doctor's 4.5 KB and marshal's `envelope.v1.json` resolve to
    it; existing published report payloads validate unchanged against the composed schema
    (no consumer breakage), proven by validating a captured real report from each station.
- **CAP-5 — one exception root.**
  - **intent:** `except PyforgeError` is a sentence any station's caller can write.
  - **success:** A single base exception in `pyforge-core`; herald's and mason's
    independently invented roots re-parent to it; the 12–13 scattered `*Error` classes in
    warden, marshal and atlas gain it as an ancestor without changing any existing
    `except` clause's behaviour — asserted by test, since re-parenting can silently widen
    a catch.
- **CAP-6 — the subprocess seam is reconciled, and the reconciliation is honest about Marshal.**
  - **intent:** One sanctioned way to invoke a subprocess, chosen between two real designs
    rather than merged by copy count.
  - **success:** One guard in `pyforge-core` chosen deliberately between doctor's
    `cli_bridge.run_cli_json` and marshal's `ProcessPort`/`process_posix`, with the
    rationale recorded; **Marshal's own 7 importing modules** — the widest ungated surface
    in the fleet — route through it; steward's deliberate raw-`CalledProcessError`
    propagation is either folded in or recorded as a sanctioned, tested opt-out, never
    silently overridden; warden's existing single seam (`engines.py`, already annotated
    *"the sole seam"*) is confirmed conforming rather than "fixed."
- **CAP-7 — a second implementation cannot appear unnoticed.**
  - **intent:** The floor stays a floor.
  - **success:** One sole-ownership meta-test per extracted primitive, following the
    pattern marshal and warden already use; each fails the build when a second
    implementation of that primitive appears anywhere under `src/shared/packages/`.
- **CAP-8 — the floor is enforced where the build happens.** *(minted 2026-09-19)*
  - **intent:** The conformance suite — the whole `pyforge-core` `tests/` tree, the four
    sole-ownership meta-tests included — runs on every PR that touches
    `src/shared/packages/**` and inside `pr-preflight`, so a CAP-5/CAP-7 violation reds the
    PR that introduces it instead of accumulating on `main`.
  - **success:** A `core-test` job beside the eight station jobs (same shared-surface
    triggers) runs `pixi run --frozen -e pyforge-core pyforge-core-test`; `pr-preflight`
    depends on it; a fixture PR introducing a second `subprocess.run` implementation under
    `src/shared/packages/` reds the lane; the lane is green on `main` at the story's merge.
    Evidence for the gap: #1086's retirement of `pyforge-core.yml` was coverage-neutral —
    it and `pyforge-pip-install.yml` run the same enumerated subset, and
    `tests/meta/*_sole_ownership.py` were never wired into any workflow; no workflow
    invokes the `pyforge-core-test` task at all.
- **CAP-9 — the six accumulated violations are cleared.** *(minted 2026-09-19)*
  - **intent:** The six CAP-5/CAP-7 conformance failures on `main` are cleared the way
    CAP-5 and CAP-6 prescribe, so the suite is green before CAP-8's lane is born.
  - **success:** `pixi run --frozen -e pyforge-core pyforge-core-test` → 0 failed (2026-09-19:
    6 failed / 1855 passed — exception root: marshal `adapters/oidc_pkce.py`, `cli/watch.py`,
    warden `tea_advisory.py`; second subprocess implementation: marshal `cli/login.py`,
    `cli/refresh.py`, testing-kit `branch_diff_guard.py`); each re-parent widens no `except`
    clause (the CAP-5 test); marshal's two subprocess sites route through the core guard, and
    the kit's file — outside this Spec's scope (Non-goals; Q2) and a stdlib leaf by Q-26 — is
    cleared as CAP-6's recorded, tested opt-out: a file-level guard exemption pinned to the
    kit's `dependencies == []` so it self-retires if Q2 changes the declaration (corrected
    2026-09-19 at Story 52.1's review); the touched stations' own suites stay green.

## Constraints

- **The CI lane runs the pixi task, never a hand-enumerated file list** *(2026-09-19, CAP-8)*:
  enumeration is how the meta-tests were lost the first time. **CAP-9 lands before CAP-8** — a
  gate born red is a gate nobody trusts.

- **Leaf or nothing.** Pure stdlib; no module in `pyforge-core` may import from any
  `pyforge.<station>`. If a primitive needs a station's type, the extraction was wrong and
  the primitive stays where it is.
- **Retire the copy in the story that extracts it.** Never a parallel path, never a
  deprecation window. The Atlas Kedro migration is the precedent on record: ~29 k LOC
  merged and marked `shipped` while the 8,902-LOC legacy module remained the live runtime,
  because the rebuild had no migration step. An extraction that leaves copies standing has
  changed nothing and claimed something.
- **Stations stay independently conda-installable.** `pyforge-core` is a run-dependency,
  never a build-time coupling, and never a reason two stations must ship together.
- **Extraction order follows the census** — atomic write → verdict lattice → report
  envelope → roster (pending Q1) → exceptions → subprocess guard. Subprocess is last
  because it is the only entry that is a design reconciliation rather than a
  de-duplication.
- **Observable behaviour is frozen across every extraction.** Exit codes, report payloads
  and exception-catch semantics are contracts other things already depend on; each
  extraction proves preservation by test rather than by review.
- **No new primitive earns a place on one caller.** Two or more existing copies, measured,
  or it does not belong here.

## Non-goals

- **Not a framework, plugin system, or service.** Six primitives, each with a measured
  copy count.
- **Not a ninth station.** It holds no Dream, delivers no outcome, and casts no verdict;
  Charter §5's roster stays at eight. It is a dependency, not a post.
- **Not a fleet-wide test rewrite.** Stations adopt the floor as the extracting story
  retires their copy; nothing else is migrated on a schedule.
- **Not `pyforge-testing-kit`.** That is the testing charter's CAP-3 and stays there until
  Q2 decides whether the two are one package.
- **Not the station roster, yet.** Q1 may keep it in `bmad_drift_check.py`, which is
  already its single canonical home.

## Success signal

A bug in the atomic-write primitive is fixed in one file, and no station is still running
the old code — because there is no old code left to run. A new station is added without
re-deriving a single primitive. And the sole-ownership meta-tests make the second copy
impossible to land quietly, which is the only durable form the guarantee can take: the
20 copies did not appear because anyone decided to duplicate, they appeared because
nothing objected.

## Assumptions

- **The census figures in this Spec are this session's own measurement, not the research
  document's.** Three of that document's § 7 figures were wrong when re-counted:
  atomic write is 6/8 stations (not 8/8 — doctor and mason have none), the report
  envelope is 3 schemas (not 2 — marshal's `envelope.v1.json` was uncounted), and most
  materially, **its claim that "warden is the outlier: ~20 modules import `subprocess`
  with no sole-site guard" is inverted** — that counted mentions, not imports; warden has
  exactly one importing module carrying an explicit *"the sole seam"* annotation, while
  Marshal has 7. The research called fixing warden *"the one item worth doing even if
  nothing else is."* It is not; Marshal's own surface is. Treat § 7's remaining
  un-recounted rows (`pixi.toml` parsing ×2, exception roots) as unverified.
- **The 20 atomic-write copies are semantically identical**, per their own docstrings.
  Assumed, not proven per call site — CAP-2's success criterion requires proving it
  during extraction rather than trusting the docstrings, because a copy that quietly
  added an `fsync` is a durability regression that no grep would surface.
- **Adding one conda run-dependency to all eight stations is acceptable** to the
  independently-installable doctrine. Consistent with how the two existing cross-station
  edges are handled (pixi feature level, optional), but this one is different in kind —
  it is mandatory and universal, and has not been separately confirmed against the
  packaging story.

## Open Questions

- Q1 — does the station roster belong here at all? It is the one census entry whose
  canonical home already exists (`bmad_drift_check.STATIONS`, imported rather than
  mirrored by `generate.py`), and moving it into a shipped package would give a
  deliberately stdlib-only, bare-CI detector a package dependency it does not have today.
  Decide before CAP-4, not during.
- Q2 — is `pyforge-testing-kit` a second leaf or a module of this one? Both are
  stdlib-only shared floors under the same leaf constraint; two packages may be splitting
  one thing, one package may couple test-only fixtures into a runtime dependency.
- Q3 — which subprocess design wins, and what happens to steward's deliberate divergence?
  Two real designs (doctor's `cli_bridge.run_cli_json`, marshal's `ProcessPort`) plus one
  intentional non-participant. CAP-6 requires the choice to be made and recorded; this
  Spec does not make it.
