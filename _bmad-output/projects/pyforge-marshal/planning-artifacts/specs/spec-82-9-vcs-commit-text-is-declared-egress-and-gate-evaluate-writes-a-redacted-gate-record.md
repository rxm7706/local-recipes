---
title: '82.9: VCS commit text is declared egress and gate evaluate writes a redacted gate record'
type: 'fix'
created: '2026-10-02'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** AD-34's egress boundary and FR-25's gate evidence are both incomplete. Re-verified at HEAD a7cdb91fe4:

- `core/egress.py::EGRESS_PORTS` (`:193-209`) classifies `"VcsPort": False` on the rationale that nothing leaves the local
  repository, but AD-34 names "VCS commit and PR text" as egress. `VcsPort` now writes commit text as a bare `str`:
  `commit_paths(..., message: str)` (`ports/vcs.py:368`), `merge_ref_resolving(..., message: str)` (`:490`) and
  `commit_paths_onto_remote_tip` (`:539`). The AD-34 meta-test
  (`tests/meta/test_ad34_egress_registry_completeness.py`) checks bare-`str` parameters only on ports classified egress, so
  an unredacted credential can reach a commit message with no test failing. `LocalFs` also serves both
  `RecordPort.write_redacted_atomic` and `FsPort.write_text_atomic` on the same sink, so a gate record could be written
  unredacted in one line (DW-FU-2-6-4).
- `build_gate_record` (`core/egress.py:504`) has no caller anywhere: `marshal gate evaluate` prints its envelope and writes no
  durable record. Both blockers DW-FU-2-6-2 named are gone (`VcsPort.worktree_head_sha`, `ports/vcs.py:432`, gives the tree
  revision; Story 2.3's scope check has shipped), yet the wiring was never done. The spine places gate records "under the
  loop home's run directory" and gives run-less evaluations the AD-25 `sessions/` namespace (F-25), which
  `core/journal.py:57` records as unimplemented.

**Approach:**

- The three commit-writing methods move onto their own port classified `True` in `EGRESS_PORTS`, taking the message as
  `Redacted` and every other text parameter as a typed reference (the `ForgeRef` precedent, `ports/forge.py:63`);
  `VcsPort` keeps its read and ref operations, stays non-egress, and its docstring stops claiming nothing leaves the repo;
  `GitVcs` implements both; every caller wraps its message with `to_redacted`. The existing meta-test then covers commit
  text unchanged.
- The gate record's file name is one constant beside `build_gate_record`; a meta-test fails any call site that writes it
  through anything but `RecordPort.write_redacted_atomic`.
- `evaluate_gate`, given `--story`, builds the record from facts it already holds (the commands and exit codes, the scope
  verdict, `worktree_head_sha` of the evaluated root, a UTC timestamp) and writes it into the `--run` directory when one
  resolves, else into the project loop home's `sessions/` namespace, carrying `run_id` when bound; `data` names the
  path. No destination (no loop home) or a failed write is one WARN and the verdict stands.

Ledger key: `82-9-vcs-commit-text-is-declared-egress-and-gate-evaluate-writes-a-redacted-gate-record`.
Type / Effort / Deps: fix / L / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-3 (gates you can run) with Story 2.6 (FR-25; NFR-8, NFR-11; AD-34) and AD-25 (F-25,
  session-namespace gate records). Defects of shipped behaviour, so no new CAP; no flag.

## Acceptance Criteria

- Given the egress registry When the AD-34 meta-test runs Then the port carrying commit text is classified egress and none of its methods accepts a bare-`str` message
- Given a commit-writing call site handed a message containing a token-shaped credential When the commit is made Then the stored message carries the redacted form
- Given `marshal gate evaluate --story <key> --run <id>` with a resolvable run When the gate runs Then a schema-valid gate record (`schemas/gate-record.json`) with the commands, exit codes, scope verdict, tree revision and timestamp is written in that run's directory and named in `data`
- Given `gate evaluate --story <key>` with no `--run` and a provisioned loop home When the gate runs Then the record lands in the home's `sessions/` namespace
- Given no loop home When the gate runs Then one WARN says no record was written and the verdict and exit code are unchanged
- Given a call site writing the gate-record file through `FsPort` When the meta-test runs Then it fails
- Given either fix reverted When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** One redacting serializer (`core/egress.py`); no call site redacts on its own. The gate verdict never depends on
the record write. Close DW-FU-2-6-4 and DW-FU-2-6-2 in `deferred-work-ledger.md` when the story lands (status `closed`, a
`resolved:` line naming this story).

**Never:** Do not classify `FsPort` as egress (its general writes are not records). Do not change the gate's repository
anchor (Story 82.1's surface). Do not let a gate record write change the exit-code domain.

</intent-contract>

## Binding

Parent: Story 2.6, `spec-pyforge-marshal` CAP-3; a defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 entry.
Ledger key: `82-9-vcs-commit-text-is-declared-egress-and-gate-evaluate-writes-a-redacted-gate-record`.
Ledger status at mint: `backlog`.
Deps: —.
Closes: DW-FU-2-6-4, DW-FU-2-6-2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

## Review Triage Log

- No review has run yet.
