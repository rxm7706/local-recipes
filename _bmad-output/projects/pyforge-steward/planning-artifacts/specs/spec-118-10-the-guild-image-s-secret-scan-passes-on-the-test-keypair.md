---
title: '118.10: The guild image''s secret scan passes on the test keypair'
type: 'fix'
created: '2026-11-27'
status: 'done'
story: 118-10-the-guild-image-s-secret-scan-passes-on-the-test-keypair
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/django-pyforge/src/django_pyforge/assertion/golden.py'
  - 'src/shared/packages/pyforge-warden/src/pyforge/warden/hygiene.py'
  - 'src/shared/packages/pyforge-warden/src/pyforge/warden/vuln.py'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py'
  - 'tests/scripts/test_guild_image_package_sources_scan_clean.py'
  - 'tests/scripts/scripts-lib-test.txt'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-118-9-the-gitops-branch-is-guarded-before-any-cloud-run.md
  - docs/dreams/pyforge-steward.md
  - scripts/container-gates
  - Containerfile
  - .dockerignore
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** since PR #2425 (Story 118.9) merged, every push to `main` reds both `guild-container` jobs of `pyforge-station-tests` (docker and podman; runs 46066453883 to 46089619632). The image's build gate, `container-gates secrets-scan` in the `Containerfile`, runs `steward keys audit --secrets` over `/pyforge` and finds lines 14, 20, 28, 44, 46 and 47 of django-pyforge's `assertion/golden.py`, the test RSA keypair, matching Story 118.9's `hetzner-api-token` shape: exactly 64 alphanumerics with both cases, not bordered by `+`, `/` or a trailing `=`. The keypair's base64 is wrapped at 64 characters, as PEM is, so each line is a run of its own, and a line with no `+` or `/` (about one in eight) matches. The table's comment says a run inside a base64 string never matches; a wrapped line is the exception it does not name. `guild-container` does not run on a pull request, so PR #2425's checks never ran the gate.

Behind that gate is a second one. The job's post-build scan reads the image after its container has run, `__pycache__/` included, and a run dispatched on this branch (46096009355) failed there on warden's compiled `hygiene.py`. Its token set `frozenset("ABC…xyz0123456789._-")` is 65 characters; marshal writes it as the type byte `z`, the length byte `A` (65) and the string, so `zA` and the 62 letters and digits make a 64-character run. The source is clean. `vuln.py` holds the same literal and passed only because marshal flagged its string as shared, a byte that depends on context. Compiling every shipped package module found one more: `golden.py`'s `"-----BEGIN " + "PRIVATE KEY-----\n"`, which the compiler folds into one constant, matches `pem-private-key-header` in its bytecode (the container's run never imports it today).

**Approach:** hold the keypair's base64 at 76 characters a line and wrap it at 64 when the module loads, so `GOLDEN_PRIVATE_PEM` and `GOLDEN_PUBLIC_PEM` stay byte-identical and no source line is a 64-character run. Name the wrapped-line exception in the table's comment. Add `tests/scripts/test_guild_image_package_sources_scan_clean.py`, which scans every tracked file under a package's `src/` (what the image ships; `.dockerignore` drops `**/tests/`) with the same table, and each module's compiled code (`marshal.dumps` of `compile`, as a `.pyc` holds it), in the Detectors scripts suite that runs on every pull request; it also shows the keypair at 64 a line holds six Hetzner-shaped lines and the former token set matches only once compiled. Build warden's two token sets from `string.ascii_letters + string.digits + "._-"`, and format `golden.py`'s private header at load from a name, which the compiler does not fold.

Ledger key: `118-10-the-guild-image-s-secret-scan-passes-on-the-test-keypair`.

### Living CAP citations

- spec-pyforge-steward CAP-129 (credentials never enter image layers: the image's build gate finds nothing; realized, no text change) and CAP-178 / FR-52 (the secret scans' pattern table; realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- The two PEM strings stay byte-identical, and the keypair still loads as a matching pair; warden's two token sets stay the same set.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never loosen or change the pattern table.
- Never add a flag, a capability or an architecture decision.

## Acceptance Criteria

**Given** the image's build gate finds six Hetzner-shaped lines in `assertion/golden.py`, its post-build scan finds one in warden's compiled `hygiene.py`, and no pull request runs either
**When** the keypair's base64 is held at 76 characters a line and wrapped at 64 when the module loads, and a scripts test scans every tracked file under a package's `src/` with the table
**Then** the PEM strings and token sets are unchanged, the sources and their compiled code scan clean, and the new test passes here and fails on `main`'s `golden.py` and on `main`'s `hygiene.py`
**And** the pattern table does not change

- **AC1 — The new test passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_guild_image_package_sources_scan_clean.py -q
  ```

- **AC2 — The secret audit over the module is clean.** Expected: exit 0. (The module, not its directory: a local
  `__pycache__/` is untracked, the image drops it, and a compiled copy holds the PEM header Python folds together.)

  ```bash
  pixi run --frozen -e pyforge-guild steward keys audit --secrets src/shared/packages/django-pyforge/src/django_pyforge/assertion/golden.py
  ```

- **AC3 — The scripts suite's library list holds the new test, and the stdlib lane skips it.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_pyforge_ci_is_stdlib_only.py tests/scripts/test_detectors_task_match.py -q
  ```

</intent-contract>

## Result (2026-11-27)

- `GOLDEN_PRIVATE_PEM` and `GOLDEN_PUBLIC_PEM` compare equal to `main`'s, and `cryptography` loads them as a matching pair.
- `keys.scan_file_for_secrets` finds nothing in the new module. With `main`'s `golden.py` swapped in place, the new test fails on the six lines; restored, it passes.
- Compiled, the 793 shipped package modules held two matches (`hygiene.py`, Hetzner; `golden.py`, the folded private header) and now hold none; the 582 other tracked modules outside `tests/` held none. With `main`'s `hygiene.py` swapped in place, the compiled-code test fails on it; restored, the file's four tests pass in 1.8 s.
- `hygiene._SAFE_TOKEN_CHARS` and `vuln._SAFE_TOKEN_CHARS` equal the former literal's set.
- On run 46096009355, dispatched on the first commit, the build gate read `clean (3 root(s))`; the post-build scan's one finding is the `hygiene.py` match above.
