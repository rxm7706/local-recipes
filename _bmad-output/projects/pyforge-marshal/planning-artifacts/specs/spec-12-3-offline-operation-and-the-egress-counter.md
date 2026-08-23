---
title: Offline operation and the egress counter
type: test
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: b3e069981e
---

<intent-contract>

## Intent

**Problem:** Air-gapped adopters need proof Genesis makes no network calls (NFR-A1, NFR-A2, NFR-S2, AD-65, P-09, SC-06).

**Approach:** Add integration/meta tests under pyforge-marshal: import scan forbidding network stacks; egress-counter asserting zero calls across seed CLI verbs; Linux `unshare -n` path; assert default template path never constructs remote source.

## Acceptance Criteria

- No module imports `requests`, `httpx`, `urllib.request`, or `socket` (AD-65, P-09).
- Egress-counter test: zero network calls across `init`, `adopt --dry-run`, `adopt --apply`, `check`, `update --run` (SC-06, NFR-A1).
- Same suite passes under `unshare -n` on Linux.
- Lean env builds from conda-forge only (NFR-A2).
- Only network path is Copier git fetch via `--template <url>`; test confirms default path never constructs remote source.

## Boundaries & Constraints

**Never:** Add runtime network dependencies. Copier remote fetch only via explicit `--template`.

</intent-contract>

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`

## Auto Run Result

Status: done

**Summary:** Added AD-65 meta guards (forbidden network-stack imports, default in-package template path, lean conda-forge env) and a slow strace/unshare egress-counter integration test covering all five seed CLI verbs. Replaced `socket.gethostname()` with `platform.node()` in `cli/adapters.py` so the import scan holds.

**Verification:** `pyforge-marshal-test` green; slow egress strace pass (unshare skips without CAP_SYS_ADMIN).
