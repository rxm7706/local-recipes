<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-04 -->
---
title: 'Story 1.3: Secrets Steward stores live encrypted in Git, never as plaintext'
type: 'feature'
created: '2026-07-30'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: 'a932a3a786413180ce40651bde391df132f42ff4'
final_revision: '891d3fdecb4e0bea2d3464f4347b138051019c2e'
---

<intent-contract>

## Intent

**Problem:** Steward has no way to keep a secret committed to Git without it being plaintext — the exact gap that forced a git-history rewrite for a leaked `sk-ant` key. There is also no distinct signal for "this committed file looks like an unencrypted secret," separate from Story 1.2's host-gating drift finding.

**Approach:** Add `keys.py`'s `encrypt_file`/`decrypt_file` primitives, thin subprocess wraps of the `age` CLI (AD-1/AD-3 — never vendored), wired as real `steward keys encrypt <file>`/`steward keys decrypt <file>` CLI verbs via a new `KeysDuty` (replacing `NullDuty` for the `keys` slot only; the other three duties are untouched). Extend the same module with a `PlaintextSecretFinding` scan — a small, fixed pattern table distinct from Story 1.2's `DriftFinding` — that flags file content plausibly matching a known secret shape (this story's slice of the audit primitive; Story 1.6 wires the CLI verb). Declare `age` as a real `[package.run-dependencies]` entry on `pyforge-steward`'s own `pixi.toml`, range-pinned to the version already locked in this repo's `pixi.lock` (1.3.1), mirroring `pyforge-warden`'s deptry/osv-scanner NFR-C1 precedent.

## Boundaries & Constraints

**Always:**
- `encrypt_file`/`decrypt_file` are subprocess calls to the real `age` CLI (`age --encrypt --recipient ... --output ...` / `age --decrypt --identity ... --output ...`) — no vendored/reimplemented crypto (AD-1, AD-3).
- `age = ">=1.3.1,<1.4"` goes in `src/shared/packages/pyforge-steward/pixi.toml`'s `[package.run-dependencies]` (the package's OWN manifest — matches where `pyforge-warden` declares `deptry`/`osv-scanner`; NOT the repo-root `[feature.pyforge-steward.dependencies]` table, which carries only the path-dependency + build tooling).
- `cli.py`'s `resolve_duty("keys")` returns a new `KeysDuty` (defined in `keys.py`); `deploy`/`provision`/`budget` keep returning `NullDuty`.
- `steward keys` with no verb, or a verb this story doesn't implement, returns `DutyResult(ok=True, ...)` naming the available verbs (AD-7 — degrades, never crashes dispatch).
- `KeysDuty.run` catches `subprocess.CalledProcessError` from `age` and reports `DutyResult(ok=False, ...)` — an `age` failure (bad identity, bad file) is a duty-level failure (`EXIT_FAILED`), never conflated with an internal crash (`EXIT_INTERNAL`, AD-8).
- The plaintext-secret pattern table is small, fixed, and named (mirrors 1.2's single-defect-shape restraint) — not a pluggable/extensible rule engine.
- No real secret value anywhere in a fixture — synthetic placeholder strings only (inherited from Story 1.2).

**Block If:** none — self-contained CLI + library work, no ambiguous external decision points.

**Never:**
- No identity generation (`age-keygen` wrapping) and no `.steward/` inventory read/write — Cross-Story Dependencies assigns identity generation + inventory writes to Story 1.4 onward; this story's tests generate a throwaway identity directly via `age-keygen` in test setup, not through a Steward primitive.
- No `steward keys audit` CLI verb — the plaintext-secret scan is a primitive-level extension only (mirrors how 1.2 framed its own `audit --drift`-equivalent logic); Story 1.6 exposes the full CLI verb for both findings.
- No key rotation, revocation, or `keys list` — Stories 1.4/1.5/1.7.
- No general-purpose secret-scanning framework (entropy analysis, arbitrary provider catalog) — the pattern table targets known shapes only (an Anthropic `sk-ant-`-style key, a plaintext `age` identity, a PEM private-key header).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Round-trip | fixture bytes, a freshly generated `age` identity | `encrypt` then `decrypt` reproduces the original bytes exactly | No error expected |
| Encrypted output is real ciphertext | the encrypted file | starts with `age`'s binary magic header (`age-encryption.org/v1`); does not contain the plaintext | No error expected |
| Decrypt with wrong identity | correct ciphertext, an unrelated identity | `age` exits non-zero | `CalledProcessError` at the primitive; `DutyResult(ok=False, ...)` / `EXIT_FAILED` via the CLI |
| `steward keys` bare / unimplemented verb | no verb, or a verb not yet built | `DutyResult(ok=True, ...)` naming the available verbs | No error expected |
| Plaintext-secret candidate | a directory containing a file matching the pattern table | one `PlaintextSecretFinding`, a type distinct from `DriftFinding` | No error expected |
| Clean directory | a directory with no secret-shaped content | `[]` | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py` -- add `encrypt_file`/`decrypt_file` (subprocess wraps of `age`), `PlaintextSecretFinding`, the pattern table, `scan_file_for_secrets`/`scan_directory_for_secrets`, and `KeysDuty` (Duty-protocol conforming)
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- extend `build_parser()` with `keys encrypt <file> --recipient --output` / `keys decrypt <file> --identity --output` subparsers; `resolve_duty("keys")` returns `KeysDuty()`
- `src/shared/packages/pyforge-steward/pixi.toml` -- add `age = ">=1.3.1,<1.4"` to `[package.run-dependencies]`
- `src/shared/packages/pyforge-steward/tests/conformance/test_keys_encrypt_decrypt.py` -- NEW: round-trip + wrong-identity + CLI dispatch tests
- `src/shared/packages/pyforge-steward/tests/conformance/test_keys_plaintext_secret_scan.py` -- NEW: pattern-table finding tests
- `src/shared/packages/pyforge-steward/tests/conformance/fixtures/plaintext_secret_candidate/leaked_key.txt` -- NEW: synthetic fixture (fake `sk-ant-`-shaped string, never real)
- `src/shared/packages/pyforge-steward/tests/unit/test_cli.py` -- READ-ONLY reference: `test_each_duty_dispatches_and_succeeds` must keep passing once `keys` returns a real `KeysDuty`
- `src/shared/packages/pyforge-warden/pixi.toml` -- READ-ONLY reference: confirms the run-dependency-declaration location precedent (`deptry`/`osv-scanner` live in `[package.run-dependencies]`, not the repo-root feature block)

## Tasks & Acceptance

**Execution:**
- [x] `pixi.toml` (package) -- add `age = ">=1.3.1,<1.4"` to `[package.run-dependencies]` -- declares the real external tool this story wraps (AD-3), range-pinned to the version already locked repo-wide (empirically verified: `age --version` reports `(devel)`, so the conda package version 1.3.1 from `pixi.lock`/`conda list` is the pin evidence, not the binary's own `--version` output)
- [x] `keys.py` -- add `encrypt_file`/`decrypt_file` -- the FR-2 primitive slice; let `subprocess.CalledProcessError` propagate (not swallowed), matching `scan_source`'s `SyntaxError` precedent
- [x] `keys.py` -- add `PlaintextSecretFinding`, the pattern table, `scan_file_for_secrets`/`scan_directory_for_secrets` -- extends Story 1.2's audit primitive per this story's second AC; reads raw bytes (not `tokenize.open` text) so a binary `.age` file in the same directory doesn't crash the scan
- [x] `keys.py` -- add `KeysDuty` -- the `Duty`-conforming adapter dispatching `encrypt`/`decrypt`, catching `CalledProcessError` at this boundary only
- [x] `cli.py` -- wire `keys encrypt`/`keys decrypt` subparsers and `resolve_duty("keys")` -- the only CLI surface this story adds (AD-7/AD-8 unaffected: `main()` still owns exit codes)
- [x] `tests/conformance/test_keys_encrypt_decrypt.py` -- cover the I/O matrix's encrypt/decrypt rows, both at the primitive level and via `main(["keys", "encrypt"/"decrypt", ...])`
- [x] `tests/conformance/fixtures/plaintext_secret_candidate/leaked_key.txt` + `test_keys_plaintext_secret_scan.py` -- cover the plaintext-secret rows, asserting the finding type is `PlaintextSecretFinding`, never `DriftFinding`

**Acceptance Criteria:**
- Given `age`/`age-keygen` declared as a `pyforge-steward` run-dependency, when `steward keys encrypt <file> --recipient <pubkey> --output <out>` runs against a fixture with a freshly generated `age` identity, then `<out>` is `age`-encrypted and unreadable without the identity, and `steward keys decrypt <out> --identity <keyfile> --output <back>` reproduces the original bytes exactly.
- Given a file that plausibly looks like an unencrypted secret (matches the pattern table), when the directory-scan primitive runs against a directory containing it, then it returns a `PlaintextSecretFinding` distinct from `DriftFinding`.
- Given `pixi run -e pyforge-steward pyforge-steward-test`, when the suite runs, then all of Stories 1.1/1.2's existing tests plus this story's new tests pass, and `steward --help`/`--version` are unchanged.

## Spec Change Log

## Review Triage Log

### 2026-07-30 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3 (medium 2, low 1)
- defer: 9 (medium 3, low 6)
- reject: 7
- addressed_findings:
  - `[medium]` `[patch]` The new `tests/conformance/fixtures/plaintext_secret_candidate/leaked_key.txt` fixture used a realistic-length `sk-ant-api03-`-shaped string, risking a false-positive block/alert from GitHub push protection or a similar real secret scanner on this exact security-focused epic — shortened and word-marked (`TEST00FAKE00PLACEHOLDER00NOTREAL`) so it satisfies this story's own narrow test regex without plausibly matching a real provider's format.
  - `[medium]` `[patch]` `scan_directory_for_secrets` silently returned `[]` for a nonexistent/non-directory path (confirmed by execution) — indistinguishable from a genuinely clean, fully-scanned directory, undermining the audit primitive's core trustworthiness. Now raises `NotADirectoryError`; regression test added.
  - `[low]` `[patch]` Ruff reported 5 real issues on this story's two new test files (2 unsorted-import blocks, 3 unused-unpacked `key_path` variables) — auto-fixed / renamed to `_key_path`. Pre-existing lint issues on `cli.py`/`keys.py` from Stories 1.1/1.2 (confirmed present in the baseline before this diff) were explicitly left untouched — out of this story's scope, and an incidental `--fix` side-effect on Story 1.2's pre-existing `_http` import noqa comment was reverted to keep the diff surgical.

### 2026-07-30 — Review pass (follow-up, post-done fresh pass)
- intent_gap: 0
- bad_spec: 0
- patch: 6 (medium 3, low 3)
- defer: 6 (medium 2, low 4)
- reject: 12
- addressed_findings:
  - `[medium]` `[patch]` The `AGE-SECRET-KEY-1...` literal in `test_keys_plaintext_secret_scan.py` was a REAL, parseable age identity (confirmed: `age-keygen -y` derived its public key) — a direct violation of the spec's "synthetic placeholder strings only" Never clause, in the story whose title is "never as plaintext in Git". Inert (its public key appears nowhere; it encrypts nothing), so patched rather than spec-looped: replaced with a word-marked placeholder containing `O` (outside the Bech32 charset, so provably unparseable — verified `age-keygen -y` now rejects it) that still matches the scanner's `[A-Z0-9]{20,}` tail.
  - `[medium]` `[patch]` `cli.py`'s new top-level `from .keys import KeysDuty` coupled every `steward` invocation to Story 1.2's import-time `_http.py` bridge, which raises `RuntimeError` outside a local-recipes checkout — verified: importing the package from outside the repo crashed before argparse, taking `--help`/`--version` and all NullDuty duties down. Patched to a lazy import inside `resolve_duty("keys")` + a conformance test asserting `import pyforge.steward.cli` does not import `keys`; verified `main(["--version"])` now works outside a checkout. Deeper bridge laziness deferred (1.2-scoped).
  - `[medium]` `[patch]` An unreadable subdirectory silently scanned as "clean" — `Path.rglob` swallows `PermissionError` (verified: chmod-000 subtree containing a secret returned `[]`), defeating the same fail-loud invariant the previous pass's `NotADirectoryError` patch established, while a file-level `PermissionError` inconsistently crashed the whole scan. Rewrote the walk on `Path.walk(on_error=propagate, follow_symlinks=False)`: any unreadable entry now raises (consistent primitive-level propagate posture), and symlink/3.12-vs-3.13 `rglob` semantics are pinned uniformly. Regression test added.
  - `[low]` `[patch]` `age` invocation hardening in both primitives: `--` separator so a flag-shaped filename (`-r`) can't be parsed as an `age` flag (verified `age` accepts `--`), and `stdin=subprocess.DEVNULL` so `age`'s stdin fallback (e.g. input `-`) can't hang an unattended run.
  - `[low]` `[patch]` `KeysDuty`'s docstring claimed unimplemented verbs "degrade to ok=True" via the CLI, but argparse rejects unknown verbs with a usage error (exit 2) before dispatch — the degrade branch is CLI-reachable only for bare `steward keys`. Docstring now states the actual reachability (guards programmatic namespaces).
  - `[low]` `[patch]` The test identity helper took `age-keygen`'s entire stderr as the public key — any extra stderr line (e.g. a permissions warning) would corrupt every encrypt test confusingly. Now parses the `Public key: ` line specifically.
  - Notable rejects (spec-conformant or disproved by execution): same input/output destruction claim DISPROVED (`age` refuses: "input and output file are the same", exit 1, file intact → already a clean duty failure); missing-`age`-binary → `EXIT_INTERNAL` is correct per the spec's Always clause scoping the duty-level catch to `CalledProcessError` (broken env is internal, AD-8); `--output` overwrite and output-file umask are inherited thin-wrap `age` semantics (AD-1); `ENCRYPTED PRIVATE KEY` matching the PEM pattern is safe-direction over-flagging of the spec-named shape; `age-keygen` rides the declared conda-forge `age` package, which ships both binaries.

### 2026-07-30 — Review pass (second follow-up, post-done fresh pass)
- intent_gap: 0
- bad_spec: 0
- patch: 7 (medium 3, low 4)
- defer: 1 (low 1)
- reject: 9
- addressed_findings:
  - `[medium]` `[patch]` `age`'s `-` stdin/stdout sentinel survived the `--` separator: `--output -` reported success (`wrote -`, exit 0) while the payload vanished into the discarded `capture_output` capture, input `-` "encrypted" the empty DEVNULL stream, and encrypt-to-`-` crashed with `UnicodeDecodeError`/exit 70 (all three confirmed by execution). Both primitives now refuse `-` paths with `ValueError`, which `KeysDuty` reports as a clean duty-level failure (`EXIT_FAILED`); regression tests at primitive and CLI level.
  - `[medium]` `[patch]` The scan walk's `path.is_file()` swallowed `OSError`, so a dangling symlink or a symlink into an unreadable tree silently scanned as "clean" (confirmed by execution) — a third hole in the same fail-loud contract the two prior passes hardened. Now `stat.S_ISREG(path.stat().st_mode)`: unresolvable entries raise, non-regular files (FIFOs/sockets) are still skipped, and `follow_symlinks=False` is pinned explicitly on the walk. File-symlink follow policy itself deliberately unchanged — that decision stays with the existing Story-1.6 ledger entry. Regression test added.
  - `[medium]` `[patch]` A UTF-16-encoded secret file scanned as clean (confirmed by execution — interleaved NULs defeat every pattern; a routine PowerShell-redirection artifact on the win-64 platform this story's lock adds `age` for). `scan_file_for_secrets` now strips NUL bytes before matching, closing both UTF-16 endiannesses with or without BOM; other encodings documented as out of scope. Regression test added. (Resolves the code side of the prior pass's UTF-16 ledger deferral; the ledger entry's status stays the orchestrator's.)
  - `[low]` `[patch]` `subprocess.run(text=True)` used strict decoding, so any non-UTF-8 byte on `age`'s stdout/stderr (e.g. an echoed non-UTF-8 filename) raised `UnicodeDecodeError` inside the wrapper, escaping the `CalledProcessError` handler as an internal crash — now `errors="replace"` on both primitives.
  - `[low]` `[patch]` `str.splitlines()` also splits on form feed/NEL/LS/PS, drifting reported finding line numbers off `grep -n`/editor numbering (confirmed by execution) — now splits on `\n` only.
  - `[low]` `[patch]` The unreadable-subdirectory regression test fails as root (chmod 000 does not restrict uid 0 — routine in containerized CI) and on Windows — added `skipif` guards for both.
  - `[low]` `[patch]` `steward keys --help` still described the duty as "issue, rotate, revoke, audit" — four verbs that don't exist — while omitting the two that do; reworded to name encrypt/decrypt and defer the rest to later stories.
  - Notable rejects: partial-output-on-failed-decrypt, file-symlinks-scan-outside-tree, `finditer` undercount, keys-verbs-dead-outside-checkout, fixture false-positives for 1.6, missing-`age`-binary → `EXIT_INTERNAL`, and no-timeout/FIFO-hang are all duplicates of existing deferred-work ledger entries (or, for missing-binary, additionally spec-conformant per the Always clause) — the orchestrator owns those entries, so they were not re-appended; encrypt-side failure-projection coverage and the programmatic-namespace `AttributeError` docstring reading were judged noise.

## Design Notes

Argument names deliberately mirror `age`'s own flags (`--recipient`/`-r`, `--identity`/`-i`, `--output`/`-o`) rather than inventing Steward-specific ones — AD-1's "thin wrap" reads most literally when the CLI surface maps 1:1 onto the tool it wraps. `--output` is required on both verbs; inventing a default-name convention (`<file>.age`, stripping `.age` on decrypt) is complexity no AC calls for.

Empirically verified `age` CLI shape (real binary, this repo's locked 1.3.1): `age-keygen -o key.txt` writes `Public key: age1...` to stderr and the file `# created:`/`# public key: age1...`/`AGE-SECRET-KEY-1...`; encrypted output starts with the literal bytes `age-encryption.org/v1`; decrypting with a non-matching identity exits 1 with `age: error: no identity matched any of the recipients` on stderr.

## Verification

**Commands:**
- `pixi install -e pyforge-steward` -- expected: resolves cleanly; `age`/`age-keygen` land in the env (the exact 1.3.1 build is already fetched/cached from the pre-existing repo-wide `age` dependency, so this should not need network access)
- `pixi run -e pyforge-steward pyforge-steward-test` -- expected: all tests pass (Stories 1.1/1.2's existing suite + this story's new tests)
- `pixi run -e pyforge-steward steward keys encrypt --help` -- expected: shows `--recipient`/`--output`


## Auto Run Result

**Run 3 (2026-07-30, second follow-up review pass — fresh adversarial + edge-case review of the full story diff `a932a3a786..HEAD`):**

**Summary:** No intent gaps, no spec deviations. Seven review findings patched (3 medium, 4 low), one new entry appended to the deferred-work ledger, nine rejected (mostly duplicates of existing ledger entries from the prior passes). All patches are narrow hardening of this story's own surfaces; no API or contract change beyond refusing `age`'s `-` stdin/stdout sentinel, which previously caused silent data loss.

**Files changed this pass:**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py` — `-` sentinel guard (`_reject_stdio_sentinel`) on both primitives; `errors="replace"` on subprocess capture decode; NUL-strip + `\n`-only line split in `scan_file_for_secrets`; `stat.S_ISREG(path.stat())` walk (fail-loud on unresolvable symlinks) with `follow_symlinks=False` pinned explicitly; `KeysDuty` catches `ValueError` as a duty-level failure.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — `_HELP["keys"]` now names the verbs that exist.
- `tests/conformance/test_keys_encrypt_decrypt.py` — sentinel-rejection tests (primitive + CLI).
- `tests/conformance/test_keys_plaintext_secret_scan.py` — UTF-16 detection + dangling-symlink regression tests; root/Windows `skipif` guards on the chmod test.

**Review findings breakdown:** patch 7 (medium 3, low 4) — all fixed and regression-tested; defer 1 (new ledger entry: unbounded whole-file read → OOM risk at Story 1.6 scan scale); reject 9 (seven were duplicates of existing deferred-work ledger entries owned by the orchestrator — not re-appended — plus one coverage-beyond-spec-matrix and one docstring misreading). Full detail in the Review Triage Log entry for this pass.

**Follow-up review recommendation:** false. Three consecutive adversarial passes have converged: this pass's fixes are localized one-to-few-line hardening edits, each pinned by a regression test and re-verified by executing the reviewers' own repro cases (dash-sentinel exit codes, symlink-into-unreadable-tree PermissionError, UTF-16 detection). Remaining known work is all recorded in the deferred-work ledger for Stories 1.2/1.4/1.6.

**Verification performed:**
- `pixi run -e pyforge-steward pyforge-steward-test` — 56 passed (52 prior + 4 new), 0 failed.
- Direct execution of the reviewers' repro cases post-patch: `decrypt --output -` → EXIT_FAILED with a clear message (was: exit 0 + vanished plaintext); `encrypt --output -` → EXIT_FAILED (was: UnicodeDecodeError/exit 70); symlink into chmod-000 tree → PermissionError (was: silent `[]`); readable file-symlink target still scanned (1.6-deferred policy unchanged).
- `steward --version`, `steward keys --help`, `steward keys encrypt --help` — correct surfaces.
- `ruff check` on all four changed files: only the three pre-existing Stories-1.1/1.2 findings remain (confirmed present at baseline via stash-check); zero new lint findings introduced.

**Residual risks:** file-symlink follow policy, scan scalability (size cap/streaming + `.git` exclusion), `age` output atomicity/permissions, and the keys-verbs-outside-checkout bridge coupling are all consciously deferred with ledger entries; the plaintext-secret pattern table remains deliberately narrow (three shapes) per the spec's Never clause.
