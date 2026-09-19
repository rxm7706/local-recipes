# Detector incident log

Tracked record of every occasion a Doctor detector's output was found wrong in
production. Each entry names the pinning fixture that now guards against
regression.

## Mandatory-entry rule

**Any change that fixes a detector wrong-claim MUST add a row to this log in
the same commit** — date, detector, wrong claim, true value, root cause, fixing
commit, and pinning fixture. A detector fix without a log entry is incomplete.

## Schema

| Field | Content |
|---|---|
| **date** | ISO date the wrong output was discovered |
| **detector** | Source module (`dream-chain`, `bmad-drift`, …) |
| **wrong claim** | What the detector reported |
| **true value** | What was actually true |
| **root cause** | Why the detector lied |
| **fixing commit** | Full git SHA that corrected the detector |
| **pinning fixture** | Test that fails if the bug returns |

## Entries

### 2026-07-28 — dream-chain INV-0 inflation via swallowed frontmatter

| Field | Value |
|---|---|
| date | 2026-07-28 |
| detector | `pyforge.doctor.sources.chain` (`dream-chain`) |
| wrong claim | 21 Dreams without a Spec (INV-0/INV-1 backlog) |
| true value | 11 — ten Specs lacked `owner-dream:`; one Spec had unparseable frontmatter silently treated as absent |
| root cause | `frontmatter()` used `except Exception: return {}`, converting parse failures into "no metadata" |
| fixing commit | `208093926d3` (PR #661) |
| pinning fixture | `tests/unit/test_sources_chain_dream_chain.py::test_spec_unparseable_frontmatter_does_not_report_spec_without_owner_dream` |

### 2026-08-02 — bmad-drift coverage gap (PR #181)

| Field | Value |
|---|---|
| date | 2026-08-02 |
| detector | `pyforge.doctor.sources.factory` (`bmad-drift`) |
| wrong claim | Silent pass on archive hygiene / pin drift the live tree had |
| true value | Misplaced archive artifacts and missing pins should FAIL |
| root cause | Only live-repo smoke tests; no fixture pins for deterministic finding kinds |
| fixing commit | Story 6.8 port (`sources/factory.py`) |
| pinning fixture | `tests/unit/test_sources_factory.py::{test_pin_missing_reports_fail,test_archive_misplaced_and_stray_file_are_flagged,test_spec_status_stale_reports_warn_when_a_matching_retro_exists}` |

### 2026-08-08 — dream-chain satellite-consolidation blind spot

| Field | Value |
|---|---|
| date | 2026-08-08 |
| detector | `pyforge.doctor.sources.chain` (`dream-chain`) |
| wrong claim | 16 Dreams without a Spec (INV-1) |
| true value | 10 — six Dreams were covered via `covers-dreams:` / `## Satellite:` consolidation |
| root cause | INV-1 ignored the 2026-08-02 satellite-consolidation convention until `covers-dreams:` landed |
| fixing commit | `e3171bdcc6` |
| pinning fixture | `tests/unit/test_sources_chain_dream_chain.py::test_satellite_consolidation_via_covers_dreams_frontmatter_covers_the_dream` |

### 2026-08-23 — dream-chain body-embedded fence silent degrade (FR-144 residual)

| Field | Value |
|---|---|
| date | 2026-08-23 |
| detector | `pyforge.doctor.sources.chain` (`dream-chain`) |
| wrong claim | `dream-without-spec` with `owner: (none)` for a Dream whose metadata sat behind a body-embedded `---` fence |
| true value | Malformed frontmatter — metadata never readable from a non-leading fence |
| root cause | `_frontmatter` returned `{}` when `text.startswith("---")` was false, even if a fence existed later in the body |
| fixing commit | `208093926d3` (PR #661) |
| pinning fixture | `tests/unit/test_sources_chain_dream_chain.py::test_markdown_without_a_leading_frontmatter_fence_surfaces_unparseable` |

Superseded 2026-09-19 for the displaced-block shape by Story 28.1 (next entry): a complete `---`/YAML/`---` block below prose is absent metadata, so the verdict is now `dream-without-spec` with owner `(none)` — a finding, not silence; the fixture is renamed `…_is_absent_not_unparseable`. The refusal semantics survive for an unclosed fence and for an attempted-but-unbounded opener (glued `---title:`, ` ---`, `----`).

### 2026-09-19 — chain frontmatter reader split at the first dashes, not the fence (CAP-81 / Story 28.1)

| Field | Value |
|---|---|
| date | 2026-09-19 |
| detector | `pyforge.doctor.sources.chain` (`deferred-work`, `dream-chain`, `dreams-hygiene`) |
| wrong claim | One deferral with no `location:` (fingerprint `fdd6bce25c09`) where marshal's 50.5 spec declares two, so `deferred_work_intake.py` reported "all 118 already in tracked ledger" while DW-FU-50-6 (high) was invisible; and any prose file with a `---` thematic break was reported `unparseable-frontmatter` |
| true value | Two deferrals — `3bc3d91bdf95` with `location:`, `5434eca8c9e5` high — and a prose rule is absent metadata |
| root cause | `text.split("---", 2)` + `"---" in text` — the first `---` substring, not line-anchored fences |
| fixing commit | `dispatch/pyforge-doctor/28.1` (PR number assigned at landing) |
| pinning fixture | `tests/unit/test_sources_chain_deferred_work.py::test_marshal_50_5_fixture_parses_both_deferrals` and `tests/unit/test_sources_chain_frontmatter_parse.py::test_prose_file_with_a_rule_and_no_leading_fence_is_absent_not_unparseable` |
