---
title: 'Story 7.4: State outlives the container'
type: 'feature'
created: '2026-08-09'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: '73621a604959740b8f0b4d3ebcd041757b5d0f33'
final_revision: 'a48e6df6ec6fd07a6c20bebd6afb6e1870bc7097'
---

<intent-contract>

## Intent

**Problem:** The Containerfile declares no mount contract for the three durable-state roots FR-25/CAP-4 name (loop homes, `.steward/`, `.claude/data/conda-forge-expert/`), and nothing proves a container restart actually preserves them — a naive "the Containerfile looks right" inspection cannot catch a broken mount.

**Approach:** Add `VOLUME` declarations at the three fixed in-container paths, and a new generic `container-gates volumes-roundtrip` subcommand that writes a marker into each given mount, destroys the container, recreates it with the same docker volume attached, and reads the marker back — proving persistence by real container replacement, not inspection. A live pass additionally exercises `steward budget set`/`show` across a replacement to prove the duty-level claim, not just raw bytes.

## Boundaries & Constraints

**Always:**
- `container-gates volumes-roundtrip` stays duty-agnostic (AD-2 delegation-purity, matching `secrets-scan`): it knows how to write/read a marker file through `docker run`/`docker volume`, never anything about `steward`'s own commands. It must work against any image with a shell, proven in tests against the already-locally-cached `ubuntu:24.04` (no network pull).
- The round trip is POST-BUILD verification (`docker run` sequences against an already-built, already-tagged image), never a Containerfile `RUN` gate — a single `docker build` has no "replace this container and reattach the same volume" concept, so build-time gating (Story 7.3's pattern) cannot prove this AC; this is a structural difference from 7.3, not an oversight.
- Every docker subprocess call gets an explicit timeout and clean stderr reporting on `FileNotFoundError`(docker missing)/`CalledProcessError`/timeout — never a raw traceback, mirroring `secrets-scan`'s established error-handling doctrine in this same script.
- The docker volume created for each mount is always removed in a `finally`, whether the round trip passed or failed — no leaked test volumes.
- In-container paths: `/pyforge/.steward` (keys inventory + budget ceilings), `/pyforge/.claude/data/conda-forge-expert` (mutable runtime cache), `/root/.bmad-loops` (loop homes — `HOME=/root` in this image, confirmed live: no `USER` directive is set anywhere in the Containerfile, so the runtime stage runs as root by ubuntu:24.04's own default).

**Block If:** if a live `docker build`/`docker run` shows the assumed named-volume persistence semantics do not hold as designed for the installed docker version (e.g., a `VOLUME` declared after Story 7.3's secrets-scan `RUN` gate somehow gets populated with unexpected build-time content) — HALT and report the discrepancy rather than reworking the mechanism unattended.

**Never:**
- No change to `keys.py`/`budget.py`/`provision.py` — this story ships the mount contract and its proof, not new duty behavior. `budget set`/`show` are invoked as-is.
- No CI wiring — matches Story 7.3's precedent (no `.github/workflows/*` builds this image yet).
- No attempt to make loop-home functionality actually RUN in-container — Story 7.1's SCOPE comment already documents that `git`/`gh`/`pixi`/`tmux` are absent from the runtime stage, so `steward provision --runner bmad-loop` cannot materialize a worktree in this image; that gap is unchanged and stays logged to deferred-work.md. This story only proves the MOUNT POINT itself preserves whatever bytes land there.
- No shared/NFS multi-instance volume design (SPEC.md's own non-goal; `keys.py`'s `flock` is not NFS-safe — out of scope here).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path, one mount | `volumes-roundtrip --image ubuntu:24.04 --mount /data` | Marker token written, container replaced, same token read back; exit 0 | No error |
| Happy path, multiple mounts | Same image, three `--mount` flags | Every mount round-trips independently; exit 0 only if ALL pass | Per-mount diagnostics on any failure |
| Nonexistent image | `--image does-not-exist:latest` | `docker run` fails on the write step | Clean stderr naming the image; exit 1; never a raw docker traceback |
| `docker` missing from PATH | `PATH` stripped of docker | `FileNotFoundError` caught | `` container-gates: volumes-roundtrip: `docker` not found on PATH ``; exit 1 |
| One of several mounts fails, others pass | Three `--mount`, one against an unwritable path | All three still attempted (no short-circuit) | Aggregate exit 1; each mount's own pass/fail line printed |
| Read-back mismatch (simulated volume-not-reused bug) | Second container attached to a DIFFERENT volume than the first | Read returns empty/missing marker, not the written token | Reported as a failure, not silently treated as a pass |

</intent-contract>

## Code Map

- `scripts/container-gates` -- EDIT: add `volumes-roundtrip` subcommand — generic per-mount write→destroy→recreate→read proof via real `docker run`/`docker volume`, no steward-specific logic
- `Containerfile` -- EDIT: add `VOLUME ["/pyforge/.steward", "/pyforge/.claude/data/conda-forge-expert", "/root/.bmad-loops"]` after the Story 7.3 secrets-scan gate, before `ENTRYPOINT`/`CMD`, with a comment mapping each path to FR-25/CAP-4 and noting the loop-home in-container functional gap (unchanged from 7.1)
- `pixi.toml` -- EDIT: new `[feature.pyforge-steward.tasks.pyforge-steward-container-volumes-test]`, mirrors the placement/rationale of `pyforge-steward-container-gates-test` (needs a real `docker` binary)
- `tests/scripts/test_container_volumes_roundtrip.py` -- NEW: full I/O matrix, real `docker` subprocess calls against the locally-cached `ubuntu:24.04` fixture image, `pytest.mark.skipif(shutil.which("docker") is None, ...)`

## Tasks & Acceptance

**Execution:**
- [x] `scripts/container-gates` -- `volumes-roundtrip` subcommand: `--image IMAGE --mount PATH [--mount PATH ...]`; per mount, create a fresh uuid-suffixed named docker volume, `docker run --rm -v <vol>:<mount> <image> sh -c "echo <token> > <mount>/.container-gates-roundtrip-marker"`, then a second `docker run --rm -v <vol>:<mount> <image> sh -c "cat <mount>/.container-gates-roundtrip-marker"` and compare stdout to `<token>`; timeout + `FileNotFoundError`/`CalledProcessError` handling; `docker volume rm <vol>` in a `finally` regardless of outcome; never short-circuits across multiple `--mount`s
- [x] `Containerfile` -- add the three-path `VOLUME` declaration + mapping comment
- [x] `pixi.toml` -- new `pyforge-steward-container-volumes-test` task running the new test file
- [x] `tests/scripts/test_container_volumes_roundtrip.py` -- one test per I/O-matrix row against `ubuntu:24.04`, including the "read-back from a different volume must NOT report a false pass" case

**Acceptance Criteria:**
- Given the built guild image with the three `VOLUME`s declared, when `container-gates volumes-roundtrip --image <tag> --mount /pyforge/.steward --mount /pyforge/.claude/data/conda-forge-expert --mount /root/.bmad-loops` runs for real, then all three report a clean round trip and the command exits 0 — proven live, not simulated.
- Given the same image, when `steward budget set --cap 1500usd/month` runs in one container instance with `.steward` volume-mounted, the container is removed, and a fresh container starts with the SAME volume attached, then `steward budget show` in the new container reports the same declared ceiling — the duty-level proof behind CAP-4's specific claim, not just raw-byte persistence.
- Given `volumes-roundtrip` invoked against a nonexistent image tag, then it fails cleanly (clear stderr, non-zero exit) — never a raw docker CLI traceback.

## Spec Change Log

<!-- Append-only. Populated by step-04 during review loops. -->

## Review Triage Log

<!-- Append-only. Populated by step-04 on EVERY review pass. -->

### 2026-08-09 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 0, medium 1, low 7)
- defer: 0
- reject: 6
- addressed_findings:
  - `medium` `patch` `--mount`'s value was interpolated unescaped into the docker `-v SRC:DST` flag (a `:` in the value would corrupt it) and into an in-container `sh -c` string (shell metacharacters would execute inside the ephemeral container) -- both flagged independently by both reviewers. Fixed: added `_validate_mount`/`_MOUNT_PATH_RE` (absolute path, no `:`/NUL, rejected upfront with a clean CLI error) plus `shlex.quote()` around the marker path used in both `sh -c` commands. Verified live: a colon/relative-path value is now rejected cleanly; a semicolon-containing value is accepted by the path regex but the shell metacharacter is neutralized by `shlex.quote` (confirmed no command executed via a `touch`-marker probe).
  - `low` `patch` `test_no_volume_is_leaked_after_a_run` diffed the FULL `docker volume ls -q` output before/after, vulnerable to false pass/fail from unrelated concurrent docker activity on a shared host (this repo runs several bmad-loop worktrees against the same daemon). Fixed: scoped to `--filter name=container-gates-roundtrip-` via a new `_our_volumes()` helper.
  - `low` `patch` The test suite's `skipif` only checked `docker` was on PATH, never that `ubuntu:24.04` was actually cached -- the module docstring's "no network pull needed" claim wasn't actually enforced. Fixed: added `_image_cached()` (uses `docker image inspect`, which never pulls) and skip on that instead.
  - `low` `patch` On a nonexistent-image failure, `_remove_volume` still attempted `docker volume rm` on a volume that was never created (image resolution fails before container/volume creation), printing a spurious "failed to remove volume ...: no such volume" line alongside the real diagnostic -- confirmed live before the fix. Fixed: "no such volume" in the removal error is now treated as an expected, silent outcome; re-verified live, the spurious line is gone.
  - `low` `patch` `_remove_volume`'s cleanup only caught `FileNotFoundError`/`CalledProcessError`/`TimeoutExpired`; any other `OSError` (e.g. a permissions problem invoking `docker`) would have escaped the `finally` and masked the already-decided pass/fail verdict with an unhandled traceback. Fixed: added a general `except OSError` fallback.
  - `low` `patch` A `docker run --rm` timeout only kills the local `docker` CLI client (via `subprocess`'s `timeout=`), not the container itself, which can be orphaned server-side still holding the volume -- also making `_remove_volume`'s own cleanup fail (a volume can't be removed while a container holds it), compounding the leak on the rare timeout path. Fixed: `_docker_run` now passes an explicit `--name`, and the `TimeoutExpired` handler best-effort `docker rm -f`s both possible names (`_kill_orphan`).
  - `low` `patch` Only a single simultaneous mount failure was exercised; the "never short-circuit, aggregate across every mount" claim was unverified for 2+ concurrent failures. Fixed: added `test_two_of_three_mounts_fail_still_all_attempted`.
  - `low` `patch` The Containerfile's new `VOLUME` comment didn't warn future editors that a LATER `RUN` step writing into one of the three declared paths would silently fail to persist into the image layer (the classic Docker `VOLUME` gotcha). Fixed: added an explicit "add new RUN/COPY steps ABOVE this line" warning sentence.
  - `reject` "The permanent test suite never round-trips the real `/pyforge/.steward` etc. paths against the real guild image" -- by design, per the spec's own Design Notes (fast synthetic tests prove the mechanism; the story's own live Verification separately proves it against the real image with real `steward budget set/show`) -- independently re-confirmed live in this pass against a freshly rebuilt image, all three real mounts clean.
  - `reject` "`VOLUME` causes anonymous-volume accumulation on any bare `docker run` without explicit mounts" -- standard, universally-understood Docker `VOLUME` semantics, not a defect introduced by this story's design; volume-pruning is an ops-runbook concern out of this story's scope.
  - `reject` "The docker-missing test replaces the whole child env (`env={'PATH': ...}`) instead of overriding PATH on top of the inherited env, risking a false result from a missing HOME/LANG" -- copies Story 7.3's own pre-existing, already-accepted `test_steward_missing_from_path_...` pattern verbatim; no observed flakiness in either suite.
  - `reject` "`test_multiple_mounts_one_fails_others_still_attempted` depends on `/etc/hostname` being a regular file, an engine/base-image-specific detail" -- already transparently documented in the test's own docstring; this repo pins `docker` + `ubuntu:24.04` exactly, no podman/rootless variance in evidence.
  - `reject` "The Containerfile comment's FR-25/CAP-4/Story-7.1 citations aren't drift-detector-covered" -- out of this story's scope; matches how every existing Containerfile/container-gates comment in this repo already cites specs without drift-check wiring.
  - `reject` "docker-daemon-unreachable isn't explicitly tested" -- the code path is already exercised by the existing `test_nonexistent_image_fails_cleanly` test (same `write.returncode != 0` branch, no Python exception involved either way); testing the daemon-down case directly would require destructively stopping the shared docker daemon.

### 2026-08-09 — Review pass (repair)

- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 0, medium 1, low 3)
- defer: 3
- reject: 7
- addressed_findings:
  - `medium` `patch` `_roundtrip_mount`'s `try`/`except` around the two `_docker_run` calls only caught `FileNotFoundError` and `subprocess.TimeoutExpired` -- a `docker` binary present on `PATH` but not executable (`PermissionError`, or any other `OSError` subclass) would raise uncaught, producing a raw traceback and violating the story's own "Always" constraint ("never a raw traceback"). Independently flagged by both reviewers. Fixed: added `except (OSError, ValueError)` after the existing specific handlers, mirroring `_remove_volume`'s own general-`OSError` fallback; `FileNotFoundError`/`TimeoutExpired` still match their more specific clauses first since except-clause order is preserved. Verified live: `pyforge-steward-container-volumes-test` (9 passed) and `pyforge-steward-container-gates-test` (8 passed, unaffected) both green after the change; `python3 -m py_compile scripts/container-gates` clean.
  - `low` `patch` The same gap covers `--image`: unlike `--mount`, it was never validated, so a value `subprocess.run` itself rejects (e.g. an embedded NUL byte) would raise an uncaught `ValueError`. Fixed by the same `except (OSError, ValueError)` clause above -- no separate upfront validation added, since the failure is still reported cleanly rather than as a raw traceback.
  - `low` `patch` `_image_cached()` in `tests/scripts/test_container_volumes_roundtrip.py` runs its `docker image inspect` `subprocess.run` call at `pytestmark` evaluation time (module collection), with no exception handling -- a transient docker-daemon hiccup there (this repo routinely runs several bmad-loop worktrees against the same daemon) would crash collection of the entire test module instead of cleanly skipping it. Fixed: wrapped the call in `except (OSError, subprocess.TimeoutExpired): return False`, treating any such failure the same as "not cached."
  - `low` `patch` The Containerfile's new `/pyforge/.steward` comment cited it as "architecture-spine-documented as 'repo-root, tracked... survives bmad-switch'" without noting that `.dockerignore` (line 121, unchanged by this diff) excludes `.steward/` from the build context like every other secret-shaped path -- the "tracked" framing, read on its own, could mislead a future reader into thinking host content ships into the image at that mount point. Confirmed live via `grep -n '\.steward' .dockerignore`. Fixed: the comment now states explicitly that no tracked content from the host ever ships in a layer and every fresh volume starts empty.
  - `defer` "`tests/scripts/test_container_volumes_roundtrip.py` isn't governed by `SPEC.md`'s `surface:`/baseline, only coverage-allowlisted under the generic `tests/**` entry whose stated reason doesn't match this story-specific suite" -- real, but a pre-existing repo-wide pattern (Story 7.2's `test_containerfile_checkout_path.py` already ships the identical gap, by its own memlog's own admission), not something this story introduced or that a story-scoped patch can fix. Logged to `deferred-work.md`, owner `pyforge-marshal/spec-surface-drift-reconciliation`.
  - `defer` "`_MOUNT_PATH_RE` accepts a bare `/` and `..`-containing values as valid `--mount` targets, uncovered by any test" -- real, low practical risk given `volumes-roundtrip` is only ever invoked today against the three fixed CAP-4 paths by a trusted operator. Logged to `deferred-work.md`.
  - `defer` "`test_no_volume_is_leaked_after_a_run`'s prefix-scoped `docker volume ls` filter still isn't immune to a concurrently-running invocation of the SAME test file under `pytest-xdist` (a repo-wide pinned dependency), even though it fixes the daemon-wide false-positive this story's first review pass already caught" -- real but not hit by this story's own task (`pyforge-steward-container-volumes-test` doesn't pass `-n`); only reachable via a manual xdist-parallel invocation nobody currently makes. Logged to `deferred-work.md`.
  - `reject` "Neither `test_multiple_mounts_one_fails_others_still_attempted` nor `test_two_of_three_mounts_fail_still_all_attempted` has a docstring" -- FALSE: both carry full docstrings in the actual committed file (confirmed via `grep -B1 -A3` against `tests/scripts/test_container_volumes_roundtrip.py`); this finding was an artifact of a truncated diff excerpt handed to the reviewing subagent during this review pass's own construction, not a defect in the shipped code.
  - `reject` "No test round-trips the real production paths (`/pyforge/.steward` etc.) or the real guild image" -- already explicitly triaged and rejected in this exact story's prior review pass (by-design, per the spec's own Design Notes: fast synthetic tests prove the mechanism, the story's own live Verification proves it against the real image); restated with a "future typo could ship silently" framing but the underlying design decision is unchanged and already adjudicated.
  - `reject` "CAP-4's duty-level AC (`steward budget set`/`show` surviving a replacement) is a one-time manual check, never converted into an automated regression test" -- litigates a decision the frozen intent contract itself already makes ("proven live, not simulated"; "Never: No CI wiring -- matches Story 7.3's precedent"); amending this would mean expanding the intent contract, which a repair pass may not do.
  - `reject` "None of the shipped tests depend on the new `VOLUME` instruction -- they'd pass identically if it were deleted" -- true but by design (AD-2 delegation-purity: `volumes-roundtrip` is deliberately image/duty-agnostic; the story's own Verification section separately proves the `VOLUME` declaration itself via a real `docker build` + `docker inspect` + live `volumes-roundtrip` run against the actual guild image).
  - `reject` "`_remove_volume`'s case-insensitive 'no such volume' substring match could over-match a compound error mentioning that phrase for an unrelated reason" -- theoretical; no observed instance, and no practical fix without parsing structured docker error output the CLI doesn't expose.
  - `reject` "'Verified live' claims (docker build, volumes-roundtrip, `steward budget set`/`show`) carry no captured-log artifact, only prose, given no CI wiring" -- matches this whole spec's established, previously-accepted verification convention across every prior story's memlog entry; not a new or story-specific gap.
  - `reject` "`cmd_volumes_roundtrip`'s aggregate result is free text, not structured/machine-readable output" -- speculative; no current consumer needs to parse it programmatically, and adding structure now would be premature engineering with no requirement behind it.

## Design Notes

**Resolving "the Tier-3 store" (FR-25/epics.md's exact phrase) against CAP-4's concrete list.** FR-25 in the PRD reads "loop homes, the Tier-3 store and mutable runtime caches resolve to mounted volumes" — CLAUDE.md's own Tier-3 definition is `_bmad-output/projects/<slug>/implementation-artifacts/` (gitignored BMAD execution output), but that tree is already stripped from the Docker build context entirely by Story 7.1 (`.dockerignore` explicitly excludes `_bmad-output/projects/*/implementation-artifacts`) and has no runtime relevance inside a station image. SPEC.md's CAP-4 — the authoritative Tier-2 contract this epic decomposes — lists exactly three items instead: `.steward/` (keys inventory, budget ceilings), `.claude/data/conda-forge-expert/`, and loop homes, with success measured by `steward keys list`/`budget check` answering from the surviving volume. The three items in FR-25's prose and CAP-4's list correspond 1:1 in the same relative order (loop homes / Tier-3 store / mutable caches ↔ loop homes / `.steward/` / `.claude/data/conda-forge-expert/`) once "loop homes" is matched first — confirming "the Tier-3 store" is PRD-author shorthand for Steward's own durable credential+budget store (`.steward/`, architecture-spine-documented as "repo-root, tracked... survives bmad-switch"), not a citation of CLAUDE.md's BMAD-artifact tiering vocabulary. This story targets `.steward/` accordingly, not `implementation-artifacts/`.

**Why the round trip can't be a build-time `RUN` gate like Story 7.3's.** A `docker build` layer is not a running container with an attachable named volume — there is no "stop this RUN step's container, restart it with the same volume" operation inside one build. Proving the AC (a *restart* preserves state) inherently requires a post-build `docker run` → `docker rm` → `docker run` sequence against the tagged image, which is why `volumes-roundtrip` is a separate, manually-invoked verification tool rather than another line in the Containerfile.

**Why the generic tool uses `ubuntu:24.04` for its own tests, not the guild image.** Building the full `pyforge-guild` image just to unit-test `container-gates`' own write/destroy/recreate/read logic would make routine test runs slow and network-dependent. `ubuntu:24.04` is already the guild image's own runtime base and is already cached locally (confirmed via `docker images`), so the fast test suite proves the *mechanism* (docker volumes really do survive container replacement, the script's error handling is correct) without needing a slow custom build. The story's own `## Verification` section separately proves the mechanism against the real guild image, including the `steward`-specific duty-level claim.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks (if no CLI):**
- Confirm `Containerfile`'s `VOLUME` line lists exactly the three CAP-4 paths and sits after the Story 7.3 secrets-scan gate, before `ENTRYPOINT`.

## Auto Run Result

Status: done

Commits: `2a97d16c9cd921eed36529711d5cb23f00e74b82` (implementation + first review pass, prior session) + `a48e6df6ec6fd07a6c20bebd6afb6e1870bc7097` (spec-surface memlog reconciliation + repair-pass review patches, this session) on `bmad-loop/20260809-114839-7af9/7-4-state-outlives-the-container` (baseline `73621a604959740b8f0b4d3ebcd041757b5d0f33`). Not pushed.

**This session resumed after a failed deterministic verification.** A prior session implemented Story 7.4, ran its own review pass (8 patches applied, 6 rejects — logged as the first `## Review Triage Log` entry), and committed at `2a97d16c9c`, but never reconciled `spec-unified-container`'s `.memlog.md` for the changed `Containerfile`/`pixi.toml`/`scripts/container-gates` — the repo-wide `python scripts/spec_surface_check.py` gate (a repo-wide drift detector, unrelated to this story's own `## Verification` section) caught it and failed with 3 `[drift]` findings, per the feedback file `.bmad-loop/runs/20260809-114839-7af9/feedback/7-4-state-outlives-the-container-1.md`. Fixed by appending a name-citing memlog entry (`RECONCILED BY NAME`) and running `--write-baseline --spec pyforge-steward/spec-unified-container`; verified clean before proceeding. No content inside `<intent-contract>` was touched, and none of the four already-reviewed implementation files (`Containerfile`, `scripts/container-gates`, `pixi.toml`, `tests/scripts/test_container_volumes_roundtrip.py`) were modified by the reconciliation itself.

Per this workflow's own step-01 routing (`status: in-progress` → step-03), an implementation subagent independently re-verified the reconciliation (re-ran the failing detector, cross-checked the new memlog entry against the actual `git diff`, confirmed no other files were dirty, and re-ran both the story's own test suite and a live `docker build` + `volumes-roundtrip` + `docker inspect` smoke check) before the workflow proceeded to a full step-04 review pass over the whole story diff (baseline → current), per the mechanical process — not merely the repair diff.

**Review findings breakdown** (Blind Hunter + Edge Case Hunter, run independently with no shared context): 14 deduplicated findings — 0 intent_gap, 0 bad_spec, 4 patch (1 medium: `_roundtrip_mount` didn't catch general `OSError`/`ValueError` around its two `docker run` calls, an unhandled-traceback path independently flagged by both reviewers; 3 low: same gap for the `--image` argument specifically, `_image_cached()`'s collection-time crash risk, and a Containerfile comment implying tracked `.steward/` content ships into the image when `.dockerignore` already excludes it), 3 defer (this test file's non-governance under `SPEC.md`'s `surface:` — a pre-existing pattern matching Story 7.2's identical gap; `_MOUNT_PATH_RE`'s acceptance of `/` and `..`-containing values; a residual `pytest-xdist`-parallel race in the volume-leak guard, not hit by this story's own task), 7 reject (one — a claimed missing docstring — was a false positive caused by this session's own truncated diff excerpt sent to the reviewing subagent, verified against the actual file and corrected in the triage log; the other six either restate or extend findings this exact story's prior review pass already adjudicated by design, or are speculative with no current consumer). All 4 patches applied and re-verified live (`pyforge-steward-container-volumes-test` 9/9, `pyforge-steward-container-gates-test` 8/8 unaffected, `py_compile` clean) before this pass closed; `spec_surface_check.py` re-stamped and re-confirmed clean after the patches re-drifted the memlog a second time.

**Follow-up review recommendation: false.** All four patches are narrowly scoped (broadened exception handling in one function, a test-collection robustness fix, a doc-comment clarification) and don't change any detection/validation/mounting behavior; each was independently re-verified end-to-end (both real test suites plus a syntax check) after applying, not just re-inspected.

**Verification performed:** `pixi run -e pyforge-steward pyforge-steward-container-volumes-test` (9/9 passed, both before and after the repair-pass patches), `pyforge-steward-container-gates-test` (8/8 passed, confirming the shared `scripts/container-gates` file's unrelated `secrets-scan` subcommand was unaffected), `python3 scripts/spec_surface_check.py` (clean both immediately after the initial reconciliation and again after the repair-pass patches re-touched the governed files), `pixi run -e local-recipes spec-surface-check` (the actual pixi-task invocation path, clean), `python3 -m py_compile scripts/container-gates` (clean), and — by the implementation-verification subagent, independently — a real `docker build`, `docker inspect --format '{{json .Config.Volumes}}'` confirming all three CAP-4 paths, and a real `container-gates volumes-roundtrip` run against the built image (all three mounts OK, exit 0), with the throwaway image removed afterward.

**Residual risks:** the three deferred findings above are low-severity and logged to `deferred-work.md`; none are blocking. The story's own already-accepted design choice not to wire CI or convert the CAP-4 duty-level AC (`steward budget set`/`show` across a replacement) into an automated regression test remains unchanged — matches Story 7.3's precedent, litigated and rejected again in this pass's triage log as out of scope for a repair session that may not amend the frozen intent contract.

**Finalized:** 2026-08-09. All HALT-protocol steps complete (status `done`, `final_revision` recorded).

