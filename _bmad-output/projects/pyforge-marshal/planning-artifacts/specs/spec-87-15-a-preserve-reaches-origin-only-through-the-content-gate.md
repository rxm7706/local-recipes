---
title: "87.15: A preserve reaches origin only through the content gate"
type: 'feature'
created: '2026-10-04'
status: 'done'
baseline_revision: '1ea679cd82a2aa474fa5e2c6e6a25997a570c19b'
review_loop_iteration: 0
followup_review_recommended: false
flag:
  key: pyforge.marshal.preserve_refs
  provider: openfeature-file
  default: {production: off, staging: off, dev: off}
  scope: global
  fallback: "`marshal preserve push` and `marshal preserve retire` are listed disabled and refuse with the usage exit code; preserve tags stay local and are reported as debt"
  cleanup: 90 days after ON in every environment (Q4)
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04-review.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-87-3-preserved-work-has-one-grammar-and-one-verb.md
  - src/shared/packages/pyforge-core/src/pyforge/core/preserve_refs.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/preserve.py
  - scripts/pre_push_preflight.sh
  - .github/workflows/copilot-setup-steps.yml
  - docs/governance/guild-roster.json
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The repository is public, and a `preserve/` or `archive/` tag cannot be deleted once it is on `origin`: the namespace is append-only, and a purge needs a deliberate ruleset change. Three things can go wrong on a push:
- **Purged history.** The unpushed-work detector's printed remedy re-preserved the history the 2026-07-24 purge removed, in 23 public tags. They were deleted on 2026-10-04, but the GitHub cache purge request is still pending.
- **Unscanned content.** A snapshot includes untracked files. Secret scanning push protection is on, but non-provider patterns are off.
- **Runaway volume.** A looping producer minted 19,412 synthetic objects in five days.

Nothing pushes a preserve today, and nothing stops a bad one. Separately, a tag push may start `copilot-setup-steps.yml`: GitHub does not evaluate path filters for tag pushes (review minor 13).

**Approach:**
- **The gate.** Extend `pyforge.core.preserve_refs` with a content gate that runs before every push of a `preserve/` or `archive/` tag. It refuses a commit that descends from a purge-listed sha or carries a purge-listed path, read from a new tracked governance file `docs/governance/preserve-purge-list.json`. It refuses a blob the secret scan flags (the patterns the repo declares; a planted `sk-ant-…`, `ghp_…` or private-key header is caught). It refuses a file over the per-file size cap (default 5 MB, on bmad-loop's `failed_diff_max_mb` precedent).
- **Refusal.** A refused tag stays local, with a finding naming the reason.
- **Push.** A clean tag is pushed by one explicit refspec, never `--tags`, verified with `git ls-remote`. It carries the proof steward's pre-push gate accepts (steward Story 85.3).
- **Caps.** A per-run and a per-story cap turn excess into a HARD finding, and the tags stay local.
- **Verbs.** `marshal preserve push [<tag>…|--pending]` pushes through the gate. `marshal preserve retire <tag> --evidence …` appends a row to the tracked retirement ledger (`docs/governance/preserve-retirements.yaml` in this repo; its path is a policy key) and never writes or deletes a tag. `list` gains `--state retired`. The MCP face carries both verbs.
- **Runbook.** `docs/how-to/purge-preserved-refs.md` (indexed in `docs/MAP.md`) is the purge runbook. A purge is an operator act by explicit name after a committed manifest. It has a secret-incident fast path: a temporary ruleset edit, the delete, a GitHub cache purge request.
- **Workflow.** `copilot-setup-steps.yml`'s `push` trigger gains `branches: ['**']`, so a tag push starts no workflow.

Ledger key: `87-15-a-preserve-reaches-origin-only-through-the-content-gate`.
Type / Effort / Deps: feature / M / S-87.3.

### Living CAP citations

- `spec-pyforge-marshal` CAP-287 (FR-234, AD-81; AD-11 as amended). Co-governed by `spec-pyforge-core` (the module) and `spec-pyforge-steward:CAP-165` (the pre-push proof). Flag `pyforge.marshal.preserve_refs`.

## Acceptance Criteria

- Given preserves whose commit (a) descends from a purge-listed sha, (b) carries a purge-listed path, (c) adds a blob with a planted credential, or (d) adds a file over the cap When `marshal preserve push` runs Then each tag stays local with a finding naming (a)–(d), and `ls-remote` against the bare `origin` lists none of them.
- Given a clean preserve When it is pushed Then exactly one refspec names it, `ls-remote` lists it, and no other local tag reaches `origin`.
- Given more tags for one run or one story than the cap When they are pushed Then the excess is a HARD finding and those tags stay local.
- Given `marshal preserve retire <tag> --evidence "story <slug> <N.M> done <sha>"` When it runs Then the retirement ledger gains one row, no tag is written or deleted, and `list --state retired` shows the tag.
- Given every workflow under `.github/workflows/` with a `push` trigger When a scripts test reads them Then each filters `branches` or `tags`, so a push of `refs/tags/preserve/…` starts none.
- Given the flag off When `push` or `retire` runs Then each is listed disabled and refuses with the usage code; one test file runs both states; removing any gate rule fails a test (mutation).
- **Operator-gated (not a dispatch step), each waiting for the operator's explicit confirmation:** (1) file the GitHub cache purge request for the history the 2026-07-24 purge removed, and re-confirm the key rotation. (2) Decide whether the purge list carries those commit ids in clear or as digests until the cache purge is confirmed, and add its first rows. (3) Enable non-provider secret-scanning patterns in the repository settings. A dispatched session does none of these.

## Boundaries & Constraints

**Always:** Gate before every push, archive twins included. One refspec per tag. Real git and a bare remote in tests; no GitHub call.

**Ask First:** Every change to the purge list, and each operator-gated step above.

**Never:** Never push with `--tags`. Never delete or move a tag. Never change a GitHub setting from a session. Never print a secret the scan found.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal` CAP-287 (FR-234, AD-81).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (preserved-work refs) entry.
Research: review B1 (gate, row-by-row review, purge runbook and fast path), M1 (one refspec; the hook's proof), M7 (caps), minor 13 (tag-push workflows), minor 15 (derived retirement); Q1 done the same day (the 23 tags deleted).
Ledger key: `87-15-a-preserve-reaches-origin-only-through-the-content-gate`.
Ledger status at mint: `backlog`.
Deps: S-87.3.
Minted 2026-10-04 under the operator's ruling of the same day.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e pyforge-core pyforge-core-test` — expected: pass (the gate lives in pyforge-core).
- The two-state flag test: `src/shared/packages/pyforge-marshal/tests/unit/test_preserve_cli.py` (`push`, `retire`).
- The workflow trigger test under `tests/scripts/` — expected: pass; `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass.
- `pixi run --frozen -e pyforge-guild flag-gate-check` and `governance-currency` — expected: exit 0.

## Spec Change Log

- 2026-10-09: Story 87.15 implemented — content gate, push/retire verbs, retirement ledger, workflow tag filter, purge runbook.

## Review Triage Log

### 2026-10-09 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none)

## Auto Run Result

Status: done

Summary: Shipped the preserve content gate in `pyforge.core.preserve_refs`, `marshal preserve push|retire`, `list --state retired`, MCP push/retire, governance purge/retirement files, tag-push workflow guard, and operator purge runbook.

Verification: `pyforge-core-test`, `pyforge-marshal-test`, `pyforge-guild lint-types`, `tests/scripts/test_workflow_push_tag_filters.py`, and `python scripts/spec_surface_reconcile.py` (exit 0).

Follow-up review recommended: false
