---
title: "87.19: The content gate judges only what a push sends"
type: 'fix'
created: '2026-10-25'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-87-15-a-preserve-reaches-origin-only-through-the-content-gate.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-87-12-legacy-refs-are-promoted-and-attempt-preserve-leaves-the-protected-list.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-87-9-every-preserve-reader-sees-preserve-tags-and-origin.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/preserve-manifests/legacy-preserve-promote-2026-10-22.json
  - docs/dreams/pyforge-marshal.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/governance/preserve-purge-list.json
  - src/shared/packages/pyforge-core/src/pyforge/core/preserve_refs.py
  - src/shared/packages/pyforge-core/tests/unit/test_preserve_refs.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/preserve.py
  - scripts/legacy_preserve_promote.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the content gate refuses almost every preserve that would reach `origin`, and it never reads a blob that
an earlier commit added. Line numbers are at `d287eceb0a`.

- **What it reads.** `run_content_gate` (`pyforge-core/src/pyforge/core/preserve_refs.py:578`) lists every blob in the
  tagged commit's tree (`git ls-tree -r`). It runs the size cap and the secret scan on each one, starting
  `git cat-file -s` and `git cat-file -p` per blob (`_blob_size`, `:571`; `_scan_blob_for_secrets`, `:557`).
- **What it should read.** Story 87.15's acceptance criteria refuse a preserve that *adds* a blob with a planted
  credential, or *adds* a file over the cap. A push sends only the objects `origin` does not already reach, so those
  are the objects that need judging.
- **The effect.** Run read-only on `origin/main`, the gate returns 13 findings: three slide decks under
  `presentations/` over the 5 MB cap, and synthetic `sk-ant-`, `ghp_` and private-key strings in test fixtures, all
  already public. So any preserve built on today's `main` is refused. On 2026-10-25 it refused 25 of the 29
  preserve and archive tags that exist only locally. Every refusal named a file that is on `origin/main` or in its
  history. Turning `pyforge.marshal.preserve_refs` on would push 4 and refuse the rest, and every dispatch, spin and
  sweep preserve would be refused the same way.
- **The gap.** A blob that an intermediate unpushed commit added and a later commit removed is never read, although
  the push sends it.
- **The cost.** Two processes per blob is about 80 s per tag on this repository: about 21,000 blobs per tree.
- **The remedy text.** `MRS-STATUS-016` (`pyforge-marshal/src/pyforge/marshal/cli/status.py:1311`) says "push each
  with `marshal preserve push`", a verb that refuses while the flag is off.

**Approach:**
1. **The sent set.** `run_content_gate` gains `remote` (default `ORIGIN_REMOTE`). It reads the remote once with
   `git ls-remote <remote>`, then judges the objects `git rev-list --objects <commit> --not <listed shas>` names. Only
   listed shas present in the local object store are passed; a listed sha missing locally is left out, so the gate
   reads more objects, never fewer. Local remote-tracking refs are not trusted (Story 87.9: `ls-remote`, never local
   presence).
2. **An unreadable remote** is a refusal with a new `ContentGateReason` (additive), never a pass and never a fall back
   to the whole tree.
3. **One batched read.** The sizes and contents of the sent blobs are read through `git cat-file --batch-check` and
   `git cat-file --batch`, one process each per gate run. Each blob is read once, with no extra process per blob.
4. **The rules.**
   - The secret scan (`_SECRET_PATTERNS`, unchanged) and the size cap run on every sent blob, intermediate commits
     included.
   - The purge rules hold. A commit that matches or descends from a purge-listed sha is refused. So is a tip tree
     that carries a purge-listed path, or a sent blob that carries one.
   - A secret finding names the blob's path and short sha, never the matched text.
5. **Callers.** `push_preserve_ref` passes its `remote` through. Its caps, its one-refspec push and its `ls-remote`
   verification do not change. Every other caller (`marshal preserve push`, the dispatch and spin supervisors,
   `scripts/worktree_sweep.py`, `scripts/legacy_preserve_promote.py --push-reviewed`) gains the fix with no change of
   its own.
6. **The remedy.** `MRS-STATUS-016` names both push paths: `marshal preserve push` once `pyforge.marshal.preserve_refs`
   is on, and `scripts/legacy_preserve_promote.py --push-reviewed` for a reviewed legacy twin. Status reads no flag.

Ledger key: `87-19-the-content-gate-judges-only-what-a-push-sends`.
Type / Effort / Deps: fix / S / S-87.15.

### Living CAP citations

- `spec-pyforge-marshal` CAP-287 (FR-234; AD-81): nothing reaches `origin` past the content gate. This story makes
  the gate judge what Story 87.15's acceptance criteria already say, so no new CAP. It is a fix, so no flag
  (`spec-feature-flag-governance` Q1). `spec-pyforge-core` co-governs `pyforge.core.preserve_refs`.

## Acceptance Criteria

- **AC1 — Public content passes.** In a test repository with a bare `origin`, `origin/main` carries a file over the
  cap and a synthetic `sk-ant-` string. A preserve commit on top of it adds one clean file. `run_content_gate` returns
  no finding, and `push_preserve_ref` pushes the tag; `ls-remote` lists it.
- **AC2 — The intermediate blob.** In the same setup, one unpushed commit adds a planted `sk-ant-` string and the next
  removes it. A preserve of the second commit is refused with a `secret-scan` finding naming the file's path. The tag
  stays local.
- **AC3 — New content is still judged.** A sent blob over the cap is refused with `size-cap`. A sent blob with a
  planted credential is refused with `secret-scan`. A commit that matches or descends from a purge-listed sha is
  refused with `purge-listed-sha`. A tip tree or sent blob that carries a purge-listed path is refused with
  `purge-listed-path`. Story 87.15's existing tests in `test_preserve_refs.py` pass unchanged.
- **AC4 — Unreadable remote.** When `git ls-remote` fails, the gate returns the new finding and nothing is pushed.
- **AC5 — One batched read.** A test counts the `git` processes one gate run starts over a commit that adds many
  blobs. The count does not grow with the number of blobs.
- **AC6 — Mutation.** Each of these fails a named test: judging the whole tree again instead of the sent set, dropping
  the `--not` exclusion, treating an unreadable remote as a pass, or dropping the secret scan.
- **AC7 — Remedy text.** `MRS-STATUS-016`'s message names `marshal preserve push` with the flag it needs, and
  `scripts/legacy_preserve_promote.py --push-reviewed`. A test in `tests/unit/test_status.py` asserts both. Today's
  tests there assert only the code.
- **AC8 — Live, read-only.** In this repository's primary checkout, one script calls `run_content_gate` over each of
  the 29 local-only preserve and archive tags and over `origin/main`, and pushes nothing. It refuses none of them,
  where the old gate refused 25 of the tags and `origin/main` itself. The whole run takes under 120 s. The Run results
  record each tag's verdict and the total time.

## Boundaries & Constraints

**Always:**
- Real git with a bare remote in tests, and no GitHub call.
- One refspec per tag, never `--tags`.
- Read every verdict from its exit code.

**Ask First:** any change to the purge list or to `_SECRET_PATTERNS`.

**Never:**
- Push a tag, even in AC8.
- Turn on `pyforge.marshal.preserve_refs` in any environment.
- Delete or move a ref, or change a GitHub setting.
- Print a secret the scan matched.
- Mark a row of the preserve manifest `reviewed`. That review is the operator's.

**Residual risk:**
- The gate trusts that what `ls-remote` lists is public. An object that a listed ref reaches is not read again. A
  secret already on `origin` is the purge runbook's case (`docs/how-to/purge-preserved-refs.md`), not the gate's.
- The secret scan has three patterns. Non-provider patterns are off in the repository settings, which is a separate
  operator step under Story 87.15.

## I/O & Edge-Case Matrix

| Scenario | Input | Expected |
|----------|-------|----------|
| preserve adds a clean file on top of `main` | tip tree carries public oversize and fixture files | pass, tag pushed |
| intermediate commit adds a secret, the tip removes it | unpushed two-commit chain | refused, `secret-scan`, path named |
| preserve adds a file over the cap | sent blob over 5 MB | refused, `size-cap` |
| preserve descends from a purge-listed sha | purge list names an ancestor | refused, `purge-listed-sha` |
| `ls-remote` fails | remote unreachable | refused, the new reason |
| listed sha missing locally | `ls-remote` lists an object not fetched | left out of `--not`; more objects read |
| preserve of a commit already on `origin` | sent set empty | pass, tag object pushed |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-marshal` CAP-287 (FR-234; AD-81). No CAP is minted, and no `SPEC.md` text
  changes. `spec-pyforge-core` co-governs `preserve_refs.py`: its memlog takes the surface reconcile when the code
  lands.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-25 entry (the content gate refuses what
  origin already holds).
- Epic: Epic 87 (done). Operator rule 2026-10-04: a fix story joins its done epic. This backlog story reopens
  `epic-87` to `in-progress` through doctor Story 41.5's `epic_reopened_by_new_story`.
- Ledger key: `87-19-the-content-gate-judges-only-what-a-push-sends`; status at mint `backlog`.
- Deps: S-87.15.
- Surface: `marshal-policy.toml` `[epic_surfaces]."87"` already lists `pyforge-core/src/pyforge/core/preserve_refs.py`,
  `pyforge-core/tests/**`, the marshal package and the Spec memlogs. No policy change.
- After it lands (operator steps, not this story): mark the manifest rows `reviewed`, then run
  `pixi run -e pyforge-guild python scripts/legacy_preserve_promote.py --manifest-date 2026-10-22 --push-reviewed`
  twice. The per-run cap is 20, and the manifest has 27 promotion rows.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, with AC7's tests (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-core pyforge-core-test` — expected: pass, with AC1–AC6's tests (the gate lives in pyforge-core).
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_legacy_preserve_promote.py tests/scripts/test_worktree_sweep.py -q` — expected: pass (callers of `push_preserve_ref`).
- AC6's four mutations — expected: each fails its named test. Restore each.
- AC8's read-only script in the primary checkout — expected: exit 0, 0 refused, under 120 s.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0 (`pyforge-core` is mypy strict).
- `python3 scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries on `spec-pyforge-marshal` and `spec-pyforge-core` and the scoped stamps.
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.

## Spec Change Log

- 2026-10-25: minted from the Dream entry of 2026-10-25 (the content gate refuses what origin already holds) at the
  operator's ruling "start the option 2 chain here". `type: fix`, no flag, no CAP.

## Review Triage Log

- 2026-10-25: the chain review runs as a separate pass and records its findings here.
