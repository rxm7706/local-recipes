---
title: 'Story 7.3: Credentials never enter image layers'
type: 'feature'
created: '2026-08-09'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: '08d763989aabd045e954c381ee024883ed7026b2'
final_revision: 'e63ea1e7dcf504d16cf8497929d52d82a20d4726'
---

<intent-contract>

## Intent

**Problem:** Nothing proves the one-container Guild image (Story 7.1's `Containerfile`) is free of plaintext secrets — a scanner exists (`steward keys audit --secrets`) but nothing runs it against the image, and naively pointing it at the image today would ALWAYS red: `pyforge-steward`'s own conformance tests ship into the image (no `.dockerignore` rule strips `tests/`) and deliberately contain secret-shaped literals to prove the scanner works, and the vendored `age-keygen` binary itself embeds a literal `AGE-SECRET-KEY-1...` string (an upstream compiled-in test vector) — confirmed live, not assumed (see Design Notes).

**Approach:** Add `scripts/container-gates secrets-scan`, a new script that delegates to the existing `steward keys audit --secrets <path>` primitive (AD-2 — no second scanner) once per top-level entry of `/pyforge` (skipping `.pixi/`, the vendored env) plus the two generated glue files, wired as a `RUN` step in the Containerfile's final stage so a finding fails the `docker build`/`podman build` itself. `.dockerignore` gains a `**/tests/` rule so test suites — never needed to run a station CLI — stop shipping into the image and stop producing the false positive above.

## Boundaries & Constraints

**Always:**
- The scan reuses `steward keys audit --secrets` verbatim (AD-2) — `scripts/container-gates` contains no regex or scanning logic of its own, only path selection and subprocess dispatch.
- The gate runs as a Containerfile `RUN` instruction, not a separate post-build CI script — a finding must fail the `docker build`/`podman build` command itself (a nonzero `RUN` exit aborts the build natively), matching the AC's "the build FAILS" literally.
- `.pixi/` (the builder stage's materialized `pyforge-container` env, including the `age`/`age-keygen` binaries themselves) is excluded from what the gate hands the scanner — documented in both the script's docstring and the Containerfile comment, with the concrete evidence (age-keygen's baked-in test key) cited, not asserted.
- No `age` identity file, token, or enterprise URL is added to the build context or written by any `COPY`/`RUN` in the Containerfile by this story — credentials continue to reach a running container only at run time through the existing `keys` surface (nothing new is built for that; it already works this way per AD-3).

**Block If:** N/A — every decision below (the `.pixi/` exclusion, the `**/tests/` dockerignore rule, embedding the gate as a `RUN` step) is resolved by delegation precedent (AD-1/AD-2/AD-3) and by live evidence gathered before writing this spec, not by a judgment call needing human input.

**Never:**
- No new secret-scanning logic — `scripts/container-gates` must not reimplement `_SECRET_PATTERNS` or `scan_directory_for_secrets`/`scan_file_for_secrets` in any form.
- No modification to `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py` — the false-positive problem is solved entirely by controlling what the existing scanner is pointed at (path selection + `.dockerignore`), not by changing the scanner's own behavior (that is deferred item DW-1-3-13's general fix, out of this story's surface).
- No CI workflow wiring — no `.github/workflows/*` file builds this image yet; that is Story 7.5's concern (or later), not this one's.
- No run-time secret-injection mechanism (Podman secrets, `--env-file`, etc.) — Story 7.3's AC covers the BUILD-time absence of secrets; how a real deployment later mounts an `age` identity is unchanged by this story.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean directory root, `.pixi/` present with a known false-positive string inside it | `container-gates secrets-scan <dir>` where `<dir>` has ordinary clean files plus a `.pixi/` child containing a secret-shaped string | `.pixi/` is never scanned; exit 0 | No error |
| A genuine secret-shaped string outside `.pixi/` | Same `<dir>`, plus a non-`.pixi` file containing e.g. `sk-ant-...` | Exit non-zero; `steward keys audit --secrets`'s own finding line is printed | Propagated via `steward`'s exit code (`EXIT_FAILED`) |
| A file root (not a directory) | `container-gates secrets-scan <file>` | The file is scanned directly (no `.pixi/`-exclusion logic applies) | Same as above per outcome |
| A root that does not exist | `container-gates secrets-scan <missing-path>` | Clear stderr message naming the missing path; exit non-zero | Never silently treated as clean |
| Multiple roots, only one dirty | `container-gates secrets-scan <clean-dir> <dirty-file>` | Every root is scanned (no short-circuit); overall exit non-zero because at least one root was dirty | All findings across all roots are printed, not just the first |

</intent-contract>

## Code Map

- `scripts/container-gates` -- NEW: executable script (no extension, mirrors `scripts/bmad-loop-worktree`'s convention), `secrets-scan <root> [<root> ...]` subcommand
- `Containerfile` -- EDIT: final stage, add a `RUN` gate step after the existing `RUN printf ... /entrypoint.sh` block (line ~119-120) and before `ENTRYPOINT`/`CMD`
- `.dockerignore` -- EDIT: add a `**/tests/` rule (new section, placed near the existing "Python build/test artifacts" section)
- `pixi.toml` -- EDIT: add `[feature.pyforge-steward.tasks.pyforge-steward-container-gates-test]` running the new test file in an env where `steward` is actually on PATH (mirrors why `pyforge-doctor-scripts-test` lives under `pyforge-ci` rather than `pyforge-doctor` — the env choice follows what the test under `tests/scripts/` actually needs, here a real `steward` binary)
- `tests/scripts/test_container_gates.py` -- NEW: full I/O matrix, real `steward` subprocess (no mocks), against synthetic fixture trees

## Tasks & Acceptance

**Execution:**
- [x] `scripts/container-gates` -- new script, `secrets-scan` subcommand: per-root dispatch, `.pixi/` exclusion for directory roots, subprocess to `steward keys audit --secrets`, aggregate non-zero exit across all roots -- delegates, never reimplements the scanner
- [x] `.dockerignore` -- add `**/tests/` with a comment naming the false-positive it closes
- [x] `Containerfile` -- add the `RUN source /shell-hook.sh && python3 /pyforge/scripts/container-gates secrets-scan /pyforge /shell-hook.sh /entrypoint.sh` gate step in the final stage (landed as `RUN bash -c "source /shell-hook.sh && python3 ..."` -- see Verification note on the `/bin/sh` deviation)
- [x] `pixi.toml` -- new `pyforge-steward-container-gates-test` task
- [x] `tests/scripts/test_container_gates.py` -- full I/O matrix incl. the `.pixi/`-exclusion proof (a real secret-shaped string placed inside a fixture `.pixi/` child must NOT fail the scan; the same string outside `.pixi/` must)

**Acceptance Criteria:**
- Given the Containerfile as it exists after Stories 7.1/7.2, when `docker build -f Containerfile .` is run with no injected secret, then the build completes (the gate step exits 0) — proven by an actual local build, not by inspection.
- Given the same build, when a plaintext secret-shaped string is deliberately placed somewhere under `/pyforge` outside `.pixi/` (e.g. a temporary test file added to the build context), then the gate `RUN` step exits non-zero and `docker build` itself fails, not a later `docker run`.
- Given a running container built from a clean image, then no `age` identity, API token, or enterprise URL is present anywhere under `/pyforge` or `.pixi/`'s non-excluded scan targets — credentials arrive only via the existing `keys` surface at run time (unchanged by this story, verified by absence — nothing added `COPY`s or bakes one in).

## Spec Change Log

<!-- Append-only. Populated by step-04 during review loops. Do not modify or delete existing entries.
     Each entry records: what finding triggered the change, what was amended, what known-bad state
     the amendment avoids, and any KEEP instructions (what worked well and must survive re-derivation).
     Empty until the first bad_spec loopback. -->

## Review Triage Log

<!-- Append-only. Populated by step-04 on EVERY review pass, including loopbacks and blocked exits.
     Each entry records triage decision counts for intent_gap, bad_spec, patch, defer, and reject,
     with per-category severity breakdowns using low/medium/high, plus the findings addressed in
     that pass. Empty until the first review pass. -->

### 2026-08-09 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 2, low 3)
- defer: 2: (high 0, medium 0, low 2)
- reject: 11: (high 1, medium 2, low 8)
- addressed_findings:
  - `medium` `patch` No `timeout=` on `_scan_target`'s `subprocess.run` — a hung `steward` invocation would hang the whole `docker build` with no recovery. Fixed: added `_SCAN_TIMEOUT_SECONDS = 300` and a `subprocess.TimeoutExpired` handler that fails the gate cleanly instead of hanging.
  - `medium` `patch` `steward` missing from PATH crashed `_scan_target` with an unhandled `FileNotFoundError` traceback. Fixed: caught explicitly, prints `` container-gates: secrets-scan: `steward` not found on PATH `` and fails the gate cleanly; added `test_steward_missing_from_path_fails_cleanly_not_with_a_traceback`, which exercises the real PATH-lookup failure (stripped `env=`) rather than mocking.
  - `low` `patch` `_scan_root`'s `root.iterdir()` had no exception handling — a `PermissionError` or similar on a scanned directory's children would crash with a raw traceback instead of a controlled gate failure. Fixed: wrapped in `try/except OSError`, reports and fails cleanly.
  - `low` `patch` Two reviewers independently raised "does `.pixi/` exclusion miss a nested `.pixi/` below a scanned root's direct child?" without a documented answer. Verified live (`find . -iname pixi.toml`): the only 9 pixi workspaces in this repo (`recipes/insightforge/` + the 8 `src/shared/packages/*` members) are already stripped from the Docker build context by Story 7.1's pre-existing `recipes/*/.pixi/` and `src/**/.pixi/` `.dockerignore` rules, so no nested `.pixi/` can ever reach `/pyforge` — the only one that exists in the image is the single top-level one the builder stage creates. Fixed: added this evidence to `scripts/container-gates`'s own docstring so the question doesn't recur unanswered.
  - `low` `patch` `.dockerignore`'s new comment cited `steward keys audit --secrets` findings scoped to one package (`pyforge-steward`) without stating the underlying grep for the three secret patterns was repo-wide. Fixed: reworded to state the repo-wide grep explicitly, and added a note that a real `docker build` + all 8 station CLIs' `--version` were independently re-verified clean after the `**/tests/` exclusion (Story 7.1's own AC re-checked, not just assumed unaffected).
  - `low` `defer` `container-gates`'s aggregate summary doesn't distinguish a real `steward` finding (exit 1) from a crash/usage/interrupt exit (70/2/130) — both print the same "FAILED" banner. Logged to `deferred-work.md`; not fixed now because `steward`'s own traceback-on-crash output is already visible in the inherited log for a human to distinguish, so this is a diagnostics polish, not a correctness gap.
  - `low` `defer` The gate's three hardcoded roots (`/pyforge`, `/shell-hook.sh`, `/entrypoint.sh`) cover everything the Containerfile's final stage adds today, but nothing enforces a future addition also extends the gate. Logged to `deferred-work.md`; not fixed now because it's a forward-looking maintenance note, not a defect in the current diff, and the gate step sits in the same file a future editor would be changing.
  - `reject` "`.pixi/` nested-exclusion is unrecursive" (would-be `medium`) — refuted by the same live evidence as the patch above: nested `.pixi/` never reaches the build context.
  - `reject` "`.git/` inside `/pyforge` could ship the still-unpurged historical secret from the 2026-07-24 incident" (would-be `high`) — refuted: `.dockerignore` line 33 (`.git/`, pre-existing, unmodified by this story) strips it from the build context entirely; confirmed by reading the file.
  - `reject` "`**/tests/` could silently drop content a station CLI needs at runtime" (would-be `medium`) — refuted empirically: a real `docker build` + `docker run <img> <cli> --version` for all 8 station CLIs (marshal, steward, pyforge-atlas, warden, doctor, mason, herald, scribe) passed after the exclusion.
  - `reject` "Per-child `steward` subprocess dispatch is needlessly slow" — refuted: the real gate step (3 roots, `/pyforge`'s many top-level children) completes in ~4.5s, measured live.
  - `reject` "Per-child dispatch duplicates exclusion semantics `steward` already supports" — factually wrong: `steward keys audit --secrets` has no exclude flag (that's exactly why DW-1-3-13 is still open); the `.dockerignore` comment correctly cites it as a NOT-yet-built alternative, not an existing one.
  - `reject` "Aggregate summary doesn't attribute findings to a specific root" — `steward`'s own finding lines already carry the full absolute path + line number, so a human reading the log can already attribute every finding.
  - `reject` "New pixi task isn't CI-wired; blanket `skipif` silently no-ops elsewhere" — CI wiring is explicitly out of this story's scope (spec `Never` list); pytest's skip is visible in the terminal summary, not silent; matches this repo's established real-execution-over-mocks testing convention (a real `steward` binary can't be faked without mocking).
  - `reject` "Executable bit/shebang on `scripts/container-gates` are decorative since every caller invokes it via `python3`/`sys.executable`" — true but harmless; matches the pre-existing `scripts/bmad-loop-worktree` convention; no functional consequence either way.
  - `reject` "Containerfile comment asserts `steward` is on PATH after sourcing the hook with no sanity check" — no plausible trigger (the base image ships nothing else named `steward`); independently proven by five successful real builds in this pass alone.
  - `reject` "`source /shell-hook.sh` failing before `&&` would let the scan silently never run while `RUN` still fails for an unrelated reason" — misreads `bash -c "a && b"` semantics: if `a` fails, `bash -c` itself returns `a`'s nonzero status, so `RUN` (and the build) still fails — never a silent skip.

## Design Notes

**Why `.pixi/` is excluded from the scan, with evidence, not assumption.** Running `steward keys audit --secrets` against the real, installed `pyforge-steward` env (`pixi run -e pyforge-steward steward keys audit --secrets .pixi/envs/pyforge-steward/bin`) produced exactly one finding: `.pixi/envs/pyforge-steward/bin/age-keygen:2204 matches the 'age-identity' plaintext-secret pattern`. `strings .pixi/envs/pyforge-steward/bin/age-keygen | grep AGE-SECRET-KEY-1` confirms a literal `AGE-SECRET-KEY-1N9JEPW6DWJ0ZQUDX63F5A03GX8QUW7PXDE39N8UYF82VZ9PC8UFS3M7XA9` compiled into the binary — an upstream test vector, not a real identity, not anything this repo or image produced. `age`/`age-keygen` are required, externally-declared run-dependencies (AD-3) that ship in every build of this image (the `keys` duty needs them to function at all), so this finding is unavoidable and permanent for any image containing them — excluding `.pixi/` from the scan target is the only way this gate is ever green on a clean build.

**Why `**/tests/` is excluded from the build context, with evidence.** `steward keys audit --secrets src/shared/packages/pyforge-steward` (run against the real checkout) found 7 findings, all inside `tests/` — `tests/conformance/test_keys_plaintext_secret_scan.py`, `tests/conformance/fixtures/plaintext_secret_candidate/leaked_key.txt`, and `tests/meta/test_invariants.py` — each a deliberate, word-marked synthetic fixture (`SYNTHETIC`, `TEST`, `PLACEHOLDER`, `NOTREAL` embedded in the literal itself) proving the scanner works, not a real leak. A repo-wide unrestricted grep for the same three patterns found no matches anywhere outside this one package's `tests/` tree. This is deferred item DW-1-3-13's exact scenario ("Story 1.6 needs a fixture/allowlist policy before the audit verb can gate anything") — this story resolves it for the container-gate consumer specifically by never shipping `tests/` into the image at all (a legitimate, independently-justified exclusion — a runtime image doesn't need test suites), not by adding an allowlist to the shared scanner. DW-1-3-13 stays open for the general-purpose primitive; note the resolution against it during review.

**Why the gate is a `RUN` step, not an external wrapper script.** At the point `COPY --from=builder /pyforge /pyforge` and `COPY --from=builder /shell-hook.sh /shell-hook.sh` have run, the final stage already has `steward` on PATH once `/shell-hook.sh` is sourced (the builder stage's `pixi install --frozen -e pyforge-container` materialized it under `/pyforge/.pixi/envs/pyforge-container/`, which the COPY brought along). A `RUN` that sources the hook and calls `scripts/container-gates secrets-scan` therefore runs the exact scanner the image ships, over the exact content the image ships, and a nonzero exit aborts `docker build`/`podman build` natively — no second script has to be kept in sync with what the Containerfile actually produces.

## Verification

**Commands:**
- `pixi run -e pyforge-steward pyforge-steward-container-gates-test` -- expected: all new tests pass
- `docker build -f Containerfile -t pyforge-guild-gate-check .` -- expected: succeeds (gate step reports clean); this is the direct proof of the AC and must be run for real, not simulated
- Injected-secret variant: temporarily add a file with a secret-shaped literal under a path that ships into `/pyforge` (outside `.pixi/`/`tests/`), rebuild, confirm the `RUN` gate step fails the build, then remove the temporary file before finishing

**Manual checks (if no CLI):**
- Confirm no `age` identity, token, or enterprise URL appears in `docker history --no-trunc pyforge-guild-gate-check` or in `docker run --rm --entrypoint find pyforge-guild-gate-check /pyforge -iname '*.age' -o -iname '*secret*'` (should list only the `keys.py`/tests source referencing the concept, never a real key file).

### Results (2026-08-09, executed live in this worktree)

1. **Unit tests** -- `pixi run -e pyforge-steward pyforge-steward-container-gates-test`: `7 passed in 0.82s` (all five I/O-matrix rows, split into 7 tests: the `.pixi/`-exclusion proof is two tests -- clean-with-`.pixi/`-secret, and `.pixi/`-secret-excluded-but-sibling-secret-still-fails -- plus explicit clean-file-root and clean-multi-root cases alongside the matrix's dirty ones).
2. **Full pyforge-steward suite (regression check)** -- `pixi run -e pyforge-steward pyforge-steward-test`: `264 passed in 2.25s`. No regressions.
3. **Clean real build** -- `docker build -f Containerfile -t pyforge-guild-gate-check .` from the repo root at HEAD (Stories 7.1/7.2 state + this story's 4 file edits): **succeeded**. The gate `RUN` step's tail:
   ```
   #16 4.343 [secrets] clean: /shell-hook.sh
   #16 4.419 [secrets] clean: /entrypoint.sh
   #16 4.430 container-gates: secrets-scan: clean (3 root(s))
   #16 DONE 4.5s
   ```
   Every top-level child of `/pyforge` (`.git`/`.pixi` etc. already excluded by `.dockerignore`/the gate itself) reported `[secrets] clean: ...`, and the two glue files scanned clean directly. Full `docker build` exit code 0.
4. **Negative-path build** -- added `_secret_probe_DELETE_ME.txt` at the repo root containing `sk-ant-api03-FAKE0000000000000000000000TEST`, ran `docker build -f Containerfile -t pyforge-guild-gate-check-negative .`: the gate step reported
   ```
   #16 2.773 [secrets] /pyforge/_secret_probe_DELETE_ME.txt:1 matches the 'anthropic-api-key' plaintext-secret pattern
   ...
   #16 4.420 container-gates: secrets-scan: FAILED -- see findings above
   #16 ERROR: process "...python3 /pyforge/scripts/container-gates secrets-scan ..." did not complete successfully: exit code: 1
   ```
   and `docker build` itself exited **1** -- no image was tagged (`docker rmi pyforge-guild-gate-check-negative` afterward confirmed "No such image"). The probe file was deleted immediately after; `git status --short` afterward showed only this story's intended edits (`.dockerignore`, `Containerfile`, `pixi.toml` modified; `scripts/container-gates` + `tests/scripts/test_container_gates.py` untracked) -- the probe never landed in git.
5. **Manual absence check** -- `docker history --no-trunc pyforge-guild-gate-check | grep -iE 'AGE-SECRET-KEY|sk-ant-|BEGIN.*PRIVATE KEY'`: no matches. `docker run --rm --entrypoint find pyforge-guild-gate-check /pyforge -iname '*.age' -o -iname '*secret*'`: every hit is either (a) library/SDK source code that uses "secret"/"Secret" as an API concept (Python stdlib `secrets.py`, AWS `aws-cpp-sdk-secretsmanager`, `pydantic_settings`, `dagster`, Azure identity headers, `jedi`'s vendored typeshed stubs), (b) this repo's own tracked spec files whose names mention "secret" as a topic (`spec-1-3-secrets-steward-stores-...`, `spec-1-5-...-never-a-secret-value.md`), or (c) unrelated `recipes/` feedstock names (`datasette-secrets`, `wagtail-secret-sharing`, `django-secret-sharing`). Zero `.age` files, zero real key material.

**Deviation from the spec's literal `RUN` line:** the Tasks & Acceptance line names `RUN source /shell-hook.sh && python3 ...` verbatim; BuildKit's default `RUN` shell is `/bin/sh` (dash on `ubuntu:24.04`), which has no `source` builtin -- confirmed live (`/bin/sh: 1: source: not found`, exit 127) on the first build attempt. Landed as `RUN bash -c "source /shell-hook.sh && python3 ..."` instead, which invokes bash explicitly and reaches the exact same effect the spec's Design Notes describe (source the hook, then run the gate with `steward` on PATH). Documented inline in the Containerfile comment. No other deviations.

### Post-review-pass re-verification (2026-08-09, after the 5 patches above)

1. **Unit tests (patched)** -- `pixi run -e pyforge-steward pyforge-steward-container-gates-test`: `8 passed in 1.30s` (7 original + the new `test_steward_missing_from_path_fails_cleanly_not_with_a_traceback`).
2. **Full regression** -- `pixi run -e pyforge-steward pyforge-steward-test`: `264 passed in 2.17s`. Still no regressions.
3. **8-CLI regression check for the `**/tests/` exclusion** (targeted re-verification of a review finding, not simulated): built the image and ran `docker run --rm --entrypoint /entrypoint.sh <img> <cli> --version` for all 8 station CLIs -- `marshal 0.1.0` / `bmad-loop 0.9.0`, `steward 0.1.0`, `pyforge-atlas 0.1.0`, `warden 0.1.0`, `doctor 0.1.0`, `mason 0.1.0`, `herald 0.1.0`, `scribe 0.1.0` -- all answered, matching Story 7.1's own AC unchanged by this story's `.dockerignore` edit.
4. **Clean real build with the patched script** -- `docker build -f Containerfile -t pyforge-guild-final-check .`: succeeded. Directly verified the patched content was actually what got scanned (not a stale cache): `docker run --rm --entrypoint cat <img> /pyforge/scripts/container-gates | grep _SCAN_TIMEOUT_SECONDS` found the new constant, and `docker run --rm --entrypoint /entrypoint.sh <img> steward keys audit --secrets /pyforge/scripts/container-gates` reported `[secrets] clean: ...` for the gate script itself.
5. **Negative-path re-check with the patched script** -- re-added the same probe file, ran `docker build` again: failed with exit 1 at the gate `RUN` step, same as the pre-patch run. Probe file removed immediately; `git status --short` confirmed only this story's intended files remain modified/untracked.
6. All locally-built/tagged images from every build in both verification passes were removed (`docker rmi`) after each check; none were pushed anywhere.

## Auto Run Result

Status: done
Commits: `bc0eb4e2ff7665398dedae53ad124db60c636bca` (implementation) + `e63ea1e7dcf504d16cf8497929d52d82a20d4726` (spec-surface memlog reconciliation) on `bmad-loop/20260809-114839-7af9/7-3-credentials-never-enter-image-layers` (baseline `08d763989aabd045e954c381ee024883ed7026b2`). Not pushed.

**Post-HALT correction:** after first marking this run done, the loop's own configured verify gate `python scripts/spec_surface_check.py` was found red (checked proactively, not by re-invocation) — `spec-unified-container`'s `.memlog.md` hadn't been updated to acknowledge this story's changes to `.dockerignore`/`Containerfile`/`pixi.toml`/`scripts/container-gates`, so the drift detector correctly flagged it. Added a story-7.3 reconciliation entry to the memlog (matching the narrative density of every prior story's entry there) and re-stamped the baseline with `--write-baseline --spec pyforge-steward/spec-unified-container`. Both of the loop's configured verify commands (`pyforge-steward-test`, `spec_surface_check.py`) are now green; re-ran both to confirm after the fix.

**Summary.** Story 7.3 ("Credentials never enter image layers") adds a build-time secrets gate to the one-container Guild image. `scripts/container-gates secrets-scan` delegates entirely to the existing `steward keys audit --secrets` primitive (AD-2 — no second scanner) and is wired as a `RUN` step in the Containerfile's final stage, so a finding fails `docker build`/`podman build` itself, not a later `docker run`. Two real, pre-existing false-positive blockers were discovered and resolved before any code was written: `age-keygen`'s own compiled binary carries a baked-in `AGE-SECRET-KEY-1...` test vector (worked around by excluding `.pixi/`, the vendored env, from the scan target), and `pyforge-steward`'s own conformance tests deliberately contain secret-shaped literals to prove the scanner works (worked around by adding `**/tests/` to `.dockerignore`, closing DW-1-3-13's exact scenario for this consumer).

**Files changed:**
- `scripts/container-gates` (new, executable) — `secrets-scan <root> [<root> ...]` subcommand; per-root/per-child dispatch to `steward keys audit --secrets`, `.pixi/` skipped for directory roots, timeout + `FileNotFoundError`/`OSError` handling added in review.
- `.dockerignore` — `**/tests/` exclusion, with cited live evidence (repo-wide grep, 3 files, all synthetic) and an 8-CLI regression re-check note.
- `Containerfile` — new `RUN` gate step in the final stage, invoking `bash -c "source /shell-hook.sh && python3 /pyforge/scripts/container-gates secrets-scan /pyforge /shell-hook.sh /entrypoint.sh"` (deviated from the spec's literal `RUN source ...` — BuildKit's default `/bin/sh` has no `source` builtin).
- `pixi.toml` — new `pyforge-steward-container-gates-test` task (needs a real `steward` binary, so it lives under `pyforge-steward`, not the dep-free `pyforge-ci`).
- `tests/scripts/test_container_gates.py` (new) — 8 real, non-mocked subprocess tests covering the full I/O matrix plus the review-added PATH-missing case.

**Review findings breakdown** (Blind Hunter + Edge Case Hunter, run in parallel with no shared context): 18 deduplicated findings — 0 intent_gap, 0 bad_spec, 5 patch (2 medium: missing subprocess timeout, unhandled `FileNotFoundError`; 3 low: unhandled `iterdir()` OSError, undocumented `.pixi/`-exclusion rationale, imprecise `.dockerignore` audit-scope comment), 2 defer (both low: no exit-code differentiation in the aggregate summary, hardcoded root list needs future-maintenance discipline), 11 reject (each refuted with concrete evidence — see the Review Triage Log entry — including a live re-check that `.git/` cannot reach the image and that the `**/tests/` exclusion doesn't break any of the 8 station CLIs). All 5 patches were applied and re-verified live (unit tests, full regression suite, a fresh real `docker build`, and a repeat negative-path build) before this pass closed.

**Follow-up review recommendation: false.** The patches are narrowly scoped (one script's error handling, two doc comments), don't change the gate's core detection/exclusion behavior, and were independently re-verified end-to-end (build + tests + all 8 CLIs) after applying — not just re-inspected.

**Verification performed:** `pyforge-steward-container-gates-test` (8/8 passed, pre- and post-patch), `pyforge-steward-test` full regression (264/264 passed, pre- and post-patch), a real clean `docker build` (pre- and post-patch, both succeeded with the gate reporting clean), a real negative-path `docker build` with an injected secret (pre- and post-patch, both failed the build at the gate step, no image tagged, probe file never committed), a real 8-station-CLI `--version` check inside the built image (all 8 answered), and a manual absence check (`docker history` + `find` for `.age`/secret-named files — zero real key material). All commands and outputs are recorded in this file's `## Verification` section.

**Residual risks:** the two deferred items above (exit-code differentiation, hardcoded root-list maintenance) are low-severity and logged to `deferred-work.md` for later attention, not blocking. DW-1-3-13 (the shared scanner's general lack of an allowlist mechanism) remains open — this story worked around it for the container-gate consumer specifically, by controlling what gets scanned rather than changing the scanner.

**Finalized:** 2026-08-09. All HALT-protocol steps complete (status `done`, `final_revision` recorded, `workflow.on_complete` resolved empty). No further action pending in this run.

**Post-finalization recovery (2026-08-09, later re-invocation of this workflow):** on re-invocation for the same intent, the worktree's tracked branch state was found reset to the pre-story baseline (`08d763989a`) — `git reflog` showed `reset: moving to 08d763989a...` immediately after both of this story's commits, with no working-tree changes and a clean `git status`. Both commits (`bc0eb4e2ff`/`e63ea1e7dc`) had survived only as dangling objects, preserved by a `attempt-preserve/20260809-114839-7af9-e63ea1e7` safety branch (bmad-loop's own crash/timeout safety net, not created by this run). Recovered via `git merge --ff-only e63ea1e7dcf504d16cf8497929d52d82a20d4726` (a clean fast-forward — the baseline matched current `HEAD` exactly, so nothing else could have diverged). Re-ran all three verification commands against the recovered state with no changes: `pyforge-steward-container-gates-test` (8/8 passed), `pyforge-steward-test` full regression (264/264 passed), `python scripts/spec_surface_check.py` (`OK: every tracked file governed or allowlisted; no drift.`). Separately, this worktree's `_bmad-output/projects/pyforge-steward/{planning,implementation}-artifacts` had never had the Tier-3 backlink established (real local directories, not symlinks) — `scripts/bmad-switch pyforge-steward` initially refused (local `implementation-artifacts` was real and non-empty). Merged the two locally-drafted `deferred-work.md` entries and this spec file into the main checkout's canonical Tier-3 store, discarded the local (superseded) `epic-7-context.md` in favor of the canonical copy, then cleared the local directory and re-ran `bmad-switch pyforge-steward` successfully. No redo of any implementation or review work was needed or performed — the recovered commits are byte-for-byte what the original pass reviewed, patched, and verified.
