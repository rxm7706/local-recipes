---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/research/technical-pyforge-doctor-cli-architecture-research-2026-07-25.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/retros/retro-doctor-2026-08-08.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/atlas.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/warden.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/prescribe.py
research_type: 'technical'
research_topic: 'Doctor CLI architecture — post-ship refresh: pattern track record, recurring bug classes, cross-station layering audit, technical-debt register'
research_goals: 'The 2026-07-25 technical report recommended shapes before any code existed. This refresh audits them against the shipped build and the 2026-08-08 whole-build retro: (a) the MCP-first/CLI-fallback pattern''s real 3-reuse track record, (b) the two genuinely recurring bug classes the retro surfaced (AST-guard widening, clean-finding-treated-as-actionable) mined as concrete technical debt, (c) whether the Warden/Atlas layering shipped clean or duplicated logic, (d) a prioritized debt register for any future Doctor work.'
user_name: Rxm7706
date: '2026-08-08'
web_research_enabled: false
source_verification: true
scope_note: 'REFRESH — the 2026-07-25 report keeps its external pattern survey (facade, SARIF, remediation-ordering); this document is the post-ship audit and debt register. Every claim here cites shipped code or the retro, not plans.'
---

# Research Report: Technical Refresh — Doctor CLI Architecture (Post-Ship Audit)

**Date:** 2026-08-08
**Author:** Rxm7706
**Research Type:** Technical (refresh — audit of the shipped build)

---

## 1. The 07-25 recommendations: scorecard

| 07-25 recommendation | Shipped outcome |
|---|---|
| Warden via library import, not subprocess reimplementation | **Shipped exactly** — `sources/warden.py` imports only `pyforge.warden.engines.run_doctor_checks`, lazily, at the ONE sanctioned import site (AD-1), enforced by `test_no_warden_import.py` + `test_sources_warden_no_subprocess.py`. The open question ("subprocess vs. library?") resolved to library, with the degrade contract as the extra: warden absent / installed-but-unimportable / raising are three distinct FAIL messages, never conflated (2026-07-30 review findings). |
| One thin Doctor-native envelope, SARIF discipline not SARIF | **Shipped** — `DoctorReport` {schema_version, verb, generated_at, findings[, prescriptions][, grade][, axis_scores]}, source-tagged findings, presence-not-null discipline enforced in `__post_init__`. |
| Own taxonomy vs. importing warden's `ErrorKind` (open question) | **Resolved: own taxonomy, deliberately** — models.py's docstring argues importing `ErrorKind` would stretch a scan-engine-failure vocabulary over Doctor's broader domain and create "a shared, driftable vocabulary neither package fully owns." Post-ship verdict: correct call; zero cross-package vocabulary drift occurred in four epics. |
| One subprocess seam | **Shipped** — `cli_bridge.run_cli_json` is AD-5's sole subprocess site; the MCP leg's stdio child is the SDK's own transport, explicitly reasoned as not a Doctor subprocess call. |
| Prescription = partition → rank → explain, topological sort reserved | **Shipped** — prescribe.py; no graph resolver was ever needed, confirming the report's "most findings are independent, ranking not ordering" prediction. FR-13's single-hop `recommend_safe_upgrade` stayed inside the drawn boundary. |
| Exit codes: "operability, not policy" | **Shipped** — adopted wholesale from warden's `--doctor` contract. |

Net: the 07-25 report's reuse-don't-invent program was executed with unusual fidelity.
The refresh value below is in what it could *not* have predicted: the two bug classes
that recurred, and the fine texture of the atlas coupling.

## 2. The MCP-first/CLI-fallback pattern — real reuse track record (AD-6)

Three independent reuses of one reviewed shape, verifiable in `sources/atlas.py`:

1. **Story 2.1 (staleness)** established `_fetch_rows` (one shared MCP-then-CLI fetch),
   `_FetchFailed` (the only exception, caught at the axis and turned into exactly one
   Source-tagged FAIL Finding), and the injectable seams (`mcp_caller`/`cli_runner`).
   Its two review findings hardened the transport for everyone downstream: (a) the whole
   stdio session lifecycle is bounded by `asyncio.wait_for` (a stalled local server
   previously hung `gather()` regardless of the timeout argument), and (b) the fallback
   catches `Exception`, never `BaseException` (Ctrl-C/`SystemExit` must propagate, never
   be absorbed as "no MCP client" and re-routed into a fresh subprocess spawn).
2. **Story 2.2 (cve + abandonment)** parameterized `tool_name` (was hardcoded
   `"staleness_report"`) and added the composite-axis discipline: `_gather_abandonment`
   runs three sub-calls (feedstock_health ×2 filters + release_cadence), each with its own
   independent degrade — partial, never all-or-nothing.
3. **Story 4.3 (adoption, Epic 4)** reused the identical machinery with **zero new
   exception classes and zero new swallow sites** (its own self-review: "a mechanical,
   well-precedented extension of Story 2.1/2.2's already-reviewed machinery") — the
   retro's headline example of an architectural decision paying for itself three times.

**Costs worth naming (not defects, but real):**
- **Per-call session spawn.** Every MCP-leg call `asyncio.run`s a fresh stdio session that
  spawns the whole FastMCP server (`conda_forge_server.py`) as a child process. For a
  multi-axis `monitor --fleet` run that is one server boot per tool call. Deliberate
  (Herald's "no session continuity needed" reasoning, documented in the module docstring),
  but if fleet-pulse latency ever matters, session reuse across one `gather()` batch is
  the first knob — a scoped change since all calls already flow through `_fetch_rows`.
- **The two transports are one implementation wearing two coats.** The MCP tools are thin
  `_run_script` shims over the exact scripts the CLI fallback calls, so AD-6's "never
  diverge" equivalence holds largely by construction. Good for correctness; it also means
  the MCP leg buys process-isolation and protocol uniformity, not independent data — worth
  remembering before anyone cites "two independent paths" as redundancy.

## 3. Recurring bug class #1 — hand-written AST guards need repeated widening (3 independent occurrences)

The retro's clearest systemic pattern, all in Epic 1's meta-test guards:

- **Story 1.1** — the NFR-1 read-only guard detected `Name`-form `open(...)` but not
  attribute-form `Path(...).open("w")`; widened in its first review pass.
- **Story 1.2** — the no-warden-reimplementation guard took **three review passes on one
  story**: pass 1 caught `from pyforge import warden` + bare `os.system`/`os.popen`;
  pass 2 added relative-import resolution (`from .. import warden` — the package's own
  house style); pass 3 found module-granular checking laundered forbidden symbols through
  sanctioned modules (`from pyforge.warden.engines import subprocess as sp`) and finally
  closed it with a positive allowlist (`_SANCTIONED_IMPORTS`) replacing the denylist.
- **Story 1.4** — the env-hygiene scanner hard-coded literal `"os"`/`"environ"`/`"getenv"`
  and needed alias resolution (`import os as o`, `from os import environ`,
  `from os import *`) added after the fact.

**Debt reading:** each patch was locally correct; the *class* keeps recurring because
every new guard re-derives alias/import resolution from scratch and starts as a
literal-name denylist. The retro's open action item is the right fix and this refresh
seconds it as the top technical-debt entry: **a shared, tested AST alias-resolution
helper** (relative-import resolution + `import X as Y` + `from X import *` tracking +
symbol-granular allowlist support), consumable by Doctor's guards and any sibling
package writing warden/doctor-style meta-tests. Expected yield per the retro: 2–3
avoided widening cycles per future guard. Companion pattern, same family: **guard-polarity
blindness** (Story 1.4's host-guard applied to both `if`/`else` branches; the fix then
handled only one polarity direction — two independent adversarial passes each found a
live false-negative in the same function). Standing rule now filed: any
conditional-suppression logic proves both TRUE-branch and FALSE-branch leak scenarios.

## 4. Recurring bug class #2 — "clean finding treated as actionable" shipped in two independent consumers

Story 3.1's partition deliberately classifies a clean (`DoctorStatus.OK`) Finding as
`ACTIONABLE` ("every Finding lands somewhere"; reason `"clean -- no remediation needed"` —
prescribe.py `_partition_one`). Both downstream consumers then independently failed to
special-case it:

- Story 3.2's `rank()` gave clean Findings a real 1-based rank + `rank_factors` as if they
  needed prioritizing;
- Story 3.4's `_action_text` unconditionally rendered "address {check} ({source})",
  discarding the finding's own clean reason.

Neither story's self-review caught it; a fresh context-free adversarial pass across
*both files together* (2026-08-07, fixed in PR #299) did. The shipped code now carries the
special-casing with review-finding comments at prescribe.py:254–263.

**Debt reading:** the root cause is semantic overload — "actionable" means "no further gate
blocks it," but every consumer read it as "needs action." The durable fix is procedural and
already filed as a retro action item: **when a classification value has 2+ independent
consumers, each consumer needs an explicit edge-case test for every non-obvious value.**
The architectural alternative (a fourth partition, e.g. `CLEAN`) was implicitly rejected by
keeping the closed three-member `Partition` enum; if a *third* consumer of the partition
ever appears, revisit that choice before writing the consumer — two-consumers-bitten is
the empirical threshold this build established.

## 5. Cross-station layering audit — clean, with three named coupling debts

**Warden layering: clean.** One sanctioned lazy import site; independent taxonomy (no
`ErrorKind` import — models.py documents why); degrade-to-Finding on every warden failure
shape; strict `check.ok is True` identity so a shape-drifted truthy non-bool fails safe
(2026-07-30 review finding). No warden logic is reimplemented anywhere in Doctor —
the AD-4 purity boundary (no subprocess/MCP imports in `prescribe`/`score`) was re-verified
every review pass with zero findings across the whole build (retro §went-well).

**Atlas layering: clean in structure, coupled in vocabulary and shape.** No atlas logic is
reimplemented, but three couplings are contracts-by-convention, not contracts-by-schema:

1. **Classification-label coupling.** `_ABANDONMENT_CADENCE_TRENDS = {"decelerating",
   "silent"}` client-side-filters labels emitted by `release_cadence`'s own `_classify`
   (the tool has no `--trend` flag); `_ADOPTION_DECLINING_STAGES`/`_ADOPTION_SILENT_STAGES`
   mirror `adoption_stage`'s `_classify` labels the same way. If a skill-side retro renames
   or adds a trend/stage label, Doctor silently stops matching — no error, rows just fall
   through the filter. Cheapest guard: a live smoke test asserting the label sets Doctor
   filters on are a subset of the labels the scripts can emit.
2. **JSON-shape coupling.** `_extract_cve_rows` encodes cve_watcher's `{"meta", "rows"}`
   envelope (read from the live script, "confirmed 2026-08-07"); the other tools' bare-list
   shape is encoded in `_extract_list_rows`. Shape drift degrades gracefully (a
   `ValueError` folds into the normal `_FetchFailed` path → one FAIL Finding), which is the
   right failure mode — but it means an atlas-side output change presents as "instrument
   unavailable," not "contract broken." Same remedy: shape assertions in the live
   equivalence smoke test, which already exists for transport equivalence.
3. **Default-value mirroring.** `DEFAULT_CVE_SEVERITY = "C"` and the severity band set
   `{"C","H","K","T"}` mirror cve_watcher's CLI; deliberately not re-validated Doctor-side
   (unknown values forwarded and rejected upstream) — acceptable, documented in
   `gather()`'s docstring, listed here only for completeness.

One smaller in-package smell: `_default_repo_root()` walks parents for `.git`/`_bmad-output`
with a `parents[8]` positional fallback — fine in the source tree, fragile in any installed
layout that lacks both markers. Low priority; becomes real only if Doctor is ever consumed
outside the repo checkout.

## 6. Technical-debt register (prioritized)

| # | Debt | Occurrences / evidence | Remedy | Owner-shaped as |
|---|---|---|---|---|
| 1 | Per-guard re-derivation of AST alias/import resolution | 3 stories (1.1, 1.2×3 passes, 1.4); retro action item `[new, open]` | Shared tested helper for AST meta-test guards, symbol-granular allowlist support | Small shared-package story (Doctor or a `pyforge-testkit` sibling) |
| 2 | Classification values with multiple consumers lack per-consumer edge-case tests | 2 consumers bitten in one pass (3.2 `rank()`, 3.4 `_action_text`); retro action item `[new, open]` | Standing review checklist rule + backfill tests exist post-#299; apply rule to any new Partition/Status consumer | Review-process rule (Marshal policy / review prompt) |
| 3 | Atlas label + JSON-shape coupling is convention, not contract | §5 items 1–2; live confirmation dated 2026-08-07 in code comments | Extend the existing live equivalence smoke test with label-subset + shape assertions | One test-only story |
| 4 | Per-call MCP session spawn (server boot per tool call) | sources/atlas.py module docstring (deliberate) | Only if fleet-pulse latency becomes a complaint: batch-scoped session reuse inside `gather()`; all calls already route through `_fetch_rows` | Deferred until measured |
| 5 | Guard-polarity blindness in conditional-suppression logic | 2 independent findings, same function (Story 1.4) | Standing review prompt: prove both polarity directions; filed in retro | Review-process rule |
| 6 | `_default_repo_root` `parents[8]` fallback | sources/atlas.py | Revisit only if Doctor is installed outside the repo checkout | Deferred |
| 7 | Process risks: deferred-story recovery (1.4 "review budget, not merit"; 1.1 worktree-rollback loss) | Retro §corrections | Not Doctor debt — flagged to Marshal/bmad-loop stewardship, recorded here so it is not re-attributed to Doctor's architecture | Marshal |

## Assumptions

- The 07-25 report's external pattern survey (facade, SARIF, topological-sort/ranking
  literature) is not re-fetched; nothing shipped contradicted it.
- Retro findings are taken at face value where they cite on-disk Review Triage Logs; the
  one evidence gap (Story 2.1's spec is a Tier-3 recovery with no dev narrative) is noted
  in the retro itself and does not weaken the reuse claims, which are grounded in
  2.2/4.3's own reviewed reuse of 2.1's machinery.

## Open Questions

- Where does the shared AST alias-resolution helper (debt #1) live — inside pyforge-doctor
  (first consumer), pyforge-warden (has parallel guards), or a new shared test-utility
  package? Cross-station decision; both existing packages have the recurrence evidence.
- Should the live equivalence smoke test's scope (debt #3) be Doctor-owned, or does the
  conda-forge-expert skill's own test suite want the inverse assertion (scripts promise
  not to change `_classify` labels/JSON shapes without bumping something Doctor can pin)?
- Is `monitor --fleet` latency actually felt in practice (debt #4)? Measure before
  optimizing — no complaint is on record as of 2026-08-08.

## Sources

- `_bmad-output/projects/pyforge-doctor/planning-artifacts/retros/retro-doctor-2026-08-08.md` (bug-class evidence, PR map, action items)
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/research/technical-pyforge-doctor-cli-architecture-research-2026-07-25.md` (base report)
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/atlas.py` (`_fetch_rows`, `_FetchFailed`, label sets, extractors, `_default_repo_root`)
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/warden.py` (sole import site, three-shape degrade, `check.ok is True`)
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` (independent-taxonomy rationale, envelope validation)
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/prescribe.py` (`_partition_one` clean case, `rank()`/`_action_text` review-finding comments, `recommend_safe_upgrade`)
